// Implement the isolated issue #87 Scratch Cards browser module without shared shell edits.

// Import session-aware API helpers so the shared resolver can override every caller identity.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback and escaping without creating game-owned global resources.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import locale loading, number formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/scratch_cards';
// Store the isolated frozen-v1 API root once for every public action.
const API_ROOT = '/api/v1/games/scratch-cards';
// Mirror the server-authoritative wager menu for stable pre-action controls.
const WAGER_OPTIONS = [1, 2, 5, 10];
// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest masked player-scoped state payload.
let state = null;
// Store the selected wager before the next card starts.
let selectedWager = WAGER_OPTIONS[0];
// Store an in-flight flag so atomic controls cannot overlap.
let busy = false;
// Store the locale cleanup callback so unmount releases its subscription.
let unsubscribeLocale = null;
// Store a fallback retry-id counter for browsers without randomUUID support.
let requestCounter = 0;
// Retain an unresolved start identity so a lost response cannot duplicate a wager.
let pendingStartId = null;
// Retain an unresolved scratch action so a lost response cannot change its position set.
let pendingScratch = null;
// Increment the mount generation so late async work cannot render into another route.
let mountGeneration = 0;


// Resolve one owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every visible and ARIA label to the paired EN/RU resource domain.
  return t(key, params, DOMAIN);
}


// Format one value with localized fake-token terminology and no currency glyph.
function tokenAmount(value) {
  // Format two decimal places for wager, prize, payout, and net consistency.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit from the game-owned domain.
  return text('units.playTokens', { amount });
}


// Create one bounded browser action identity through an optional deterministic UUID seam.
export function createActionId(prefix, uuidSource) {
  // Read an injected UUID for tests or the browser cryptographic UUID when available.
  const uuid = typeof uuidSource === 'function' ? uuidSource() : globalThis.crypto?.randomUUID?.();
  // Return the readable game-specific identity when a UUID source exists.
  if (uuid) return `${prefix}-${uuid}`;
  // Increment the fallback counter to disambiguate actions in one millisecond.
  requestCounter += 1;
  // Combine a timestamp and counter without claiming cryptographic game fairness.
  return `${prefix}-${Date.now().toString(36)}-${requestCounter.toString(36)}`;
}


// Return the current masked card or null before the first wager.
function currentCard() {
  // Read only the server-provided player-owned current card.
  return state?.current_card || null;
}


// Return every still-covered position from the masked public card.
export function coveredPositions(card) {
  // Keep stable ascending order for action fingerprints and keyboard behavior.
  return (card?.cells || []).filter(cell => !cell.revealed).map(cell => cell.position);
}


// Translate API error codes without leaking hard-coded English into Russian UI.
function localizedError(error) {
  // Map stable server codes to game-owned player-facing copy.
  const errorKeys = { INSUFFICIENT_FUNDS: 'errors.insufficientFunds', CONFLICT: 'errors.conflict', NOT_FOUND: 'errors.notFound', VALIDATION_ERROR: 'errors.validation' };
  // Return the mapped copy or one localized generic action failure.
  return text(errorKeys[error?.code] || 'errors.generic');
}


// Translate internal card and request state into player-facing status copy.
function phaseLabel(card) {
  // Keep one stable busy phrase while an atomic action is unresolved.
  if (busy) return text('phase.working');
  // Show the idle phase before a card starts.
  if (!card) return text('phase.ready');
  // Show the covered-card phase before any cell is revealed.
  if (card.status === 'ready') return text('phase.cardReady');
  // Show a recoverable purchase intent as an in-progress atomic action.
  if (card.status === 'purchasing') return text('phase.working');
  // Show partial progress without exposing an internal state key.
  if (card.status === 'scratching') return text('phase.scratching');
  // Show crash-recovery settlement as a player-understandable phase.
  if (card.status === 'settling') return text('phase.settling');
  // Show one localized terminal result for a winning card.
  if (card.outcome === 'win') return text('phase.settledWin');
  // Show the non-winning terminal result without debug vocabulary.
  return text('phase.settledNoWin');
}


// Render one covered or server-authorized prize cell as a semantic button.
function cellHtml(cell) {
  // Build one-based position text for screen-reader labels.
  const position = cell.position + 1;
  // Branch when this exact server position may expose its prize.
  if (cell.revealed) {
    // Format the authorized visible prize through localized token terminology.
    const amount = tokenAmount(cell.prize);
    // Keep the revealed button in the grid while preventing duplicate actions.
    return `<button type="button" class="scratch-cell is-revealed" data-testid="scratch-cell-${cell.position}" data-scratch-position="${cell.position}" data-focus-id="cell-${cell.position}" aria-pressed="true" aria-label="${safe(text('stage.revealedAria', { position, amount }))}" disabled><span class="scratch-prize">${safe(amount)}</span><span class="scratch-cell-state">${safe(text('stage.revealed'))}</span></button>`;
  }
  // Allow reveals only after the server confirms the wager and before settlement begins.
  const canReveal = ['ready', 'scratching'].includes(currentCard()?.status);
  // Render a focusable foil cell whose value is absent from both markup and ARIA text.
  return `<button type="button" class="scratch-cell is-covered" data-testid="scratch-cell-${cell.position}" data-scratch-position="${cell.position}" data-focus-id="cell-${cell.position}" aria-pressed="false" aria-label="${safe(text('stage.coveredAria', { position }))}"${busy || !canReveal ? ' disabled' : ''}><span class="scratch-foil" aria-hidden="true"></span><span class="scratch-cell-state">${safe(text('stage.covered'))}</span></button>`;
}


// Render the control rail with stable wager and primary-action placement.
function controlsHtml(card) {
  // Disable wager changes while any funded card remains unfinished.
  const cardActive = Boolean(card && card.status !== 'settled');
  // Allow the same primary control to retry a persisted purchase identity after a failed resume.
  const canResumePurchase = Boolean(card?.status === 'purchasing' && card.pending_client_request_id);
  // Build localized wager labels without currency or special-font glyphs.
  const options = WAGER_OPTIONS.map(value => `<option value="${value}"${selectedWager === value ? ' selected' : ''}>${safe(tokenAmount(value))}</option>`).join('');
  // Enable starting before the first card, after settlement, or for the exact pending purchase.
  const startDisabled = busy || (cardActive && !canResumePurchase);
  // Read remaining positions once for reveal-all availability.
  const remaining = coveredPositions(card);
  // Enable reveal-all only while one or more funded cells remain covered.
  const revealDisabled = busy || !card || !['ready', 'scratching'].includes(card.status) || remaining.length === 0;
  // Select help copy that matches the actionable current phase.
  const help = canResumePurchase ? text('controls.pendingRetry') : (cardActive ? text('controls.scratchHelp') : text('controls.startHelp'));
  // Return a short keyboard-friendly rail without nested scrolling.
  return `<section class="panel control-rail scratch-controls" aria-label="${safe(text('controls.region'))}"><h2>${safe(text('controls.title'))}</h2><label for="scratch-wager">${safe(text('controls.wager'))}</label><select id="scratch-wager" data-focus-id="wager"${cardActive || busy ? ' disabled' : ''}>${options}</select><button type="button" class="scratch-primary" data-action="start" data-focus-id="start"${startDisabled ? ' disabled' : ''}>${safe(text('controls.start'))}</button><button type="button" data-action="reveal-all" data-focus-id="reveal-all"${revealDisabled ? ' disabled' : ''}>${safe(text('controls.revealAll'))}</button><p class="scratch-help">${safe(help)}</p>${pendingScratch ? `<p class="scratch-pending" role="status">${safe(text('controls.pendingRetry'))}</p>` : ''}</section>`;
}


// Render the dominant ticket stage for idle, partial, and settled states.
function stageHtml(card) {
  // Render localized guidance before any wager moves through the ledger.
  if (!card) return `<section class="panel game-stage scratch-stage is-empty" aria-label="${safe(text('stage.region'))}"><div class="scratch-empty-mark" aria-hidden="true"></div><h2>${safe(text('stage.readyTitle'))}</h2><p>${safe(text('stage.readyBody'))}</p></section>`;
  // Render all nine cells from the server-masked response in stable position order.
  const cells = (card.cells || []).map(cellHtml).join('');
  // Report progress outside the grid so reveal state is not color-only.
  const progress = text('stage.progress', { revealed: card.revealed_count, total: card.cell_count });
  // Build terminal result copy only after all prizes are authorized.
  const result = card.status === 'settled' ? (card.outcome === 'win' ? text('stage.resultWin', { amount: tokenAmount(card.payout) }) : text('stage.resultNoWin')) : '';
  // Build terminal wager, payout, and net rows without real-money language.
  const summary = card.status === 'settled' ? `<div class="scratch-summary"><span>${safe(text('stage.wager'))}<strong>${safe(tokenAmount(card.wager))}</strong></span><span>${safe(text('stage.payout'))}<strong>${safe(tokenAmount(card.payout))}</strong></span><span>${safe(text('stage.net'))}<strong>${safe(tokenAmount(card.net))}</strong></span></div>` : '';
  // Return the labeled ticket group and polite result region.
  return `<section class="panel game-stage scratch-stage" aria-label="${safe(text('stage.region'))}"><div class="scratch-stage-head"><div><p>${safe(text('stage.cardLabel'))}</p><h2>${safe(progress)}</h2></div><span class="scratch-ticket-id" aria-hidden="true">#${safe(card.card_id.slice(-6).toUpperCase())}</span></div><div class="scratch-grid" role="group" aria-label="${safe(text('stage.gridAria'))}">${cells}</div><p class="scratch-result" role="status" aria-live="polite" aria-atomic="true">${safe(result || text('stage.instruction'))}</p>${summary}</section>`;
}


// Render one sanitized settled history row from server public state.
function historyRow(card, index) {
  // Translate the stable public outcome key into current-locale copy.
  const outcome = card.outcome === 'win' ? text('history.win') : text('history.noWin');
  // Return a compact row without exposing card fingerprints or ledger details.
  return `<li aria-label="${safe(text('history.itemAria', { number: index + 1, outcome }))}"><span>${safe(outcome)}</span><strong>${safe(tokenAmount(card.payout))}</strong></li>`;
}


// Render rules, prize tiers, and bounded settled history in one data rail.
function detailsHtml() {
  // Read retained settled cards newest-first for recent-result context.
  const recent = [...(state?.recent_cards || [])].reverse();
  // Build localized history rows without raw outcome keys.
  const history = recent.map(historyRow).join('');
  // Build the documented prize tier list in stable ascending order.
  const tiers = [1, 2, 5, 10, 25].map(value => `<li>${safe(text('rules.multiplier', { value }))}</li>`).join('');
  // Return a short non-nested data rail with distinct rules and history sections.
  return `<aside class="panel details-drawer scratch-details" aria-label="${safe(text('details.region'))}"><section><h2>${safe(text('rules.title'))}</h2><p>${safe(text('rules.matchThree'))}</p><p>${safe(text('rules.profile'))}</p><h3>${safe(text('rules.prizesTitle'))}</h3><ul class="scratch-tiers">${tiers}</ul></section><section><h2>${safe(text('history.title'))}</h2><ul class="scratch-history">${history || `<li class="scratch-muted">${safe(text('history.empty'))}</li>`}</ul></section></aside>`;
}


// Return game-owned styles without editing the shared shell stylesheet.
function stylesHtml() {
  // Keep the ticket wider than both support rails at desktop and stack in DOM journey order.
  return `<style>
    /* Own the Scratch Cards visual hierarchy inside the lazy game module. */
    .scratch-shell{display:grid;grid-template-rows:auto minmax(0,1fr);gap:16px;height:100%;min-width:0}.scratch-header{display:flex;align-items:end;justify-content:space-between;gap:14px}.scratch-header h1,.scratch-header p{margin:0}.scratch-phase{max-width:42ch;padding:7px 12px;border:1px solid var(--gold);border-radius:999px;text-align:center}.scratch-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(500px,2.35fr) minmax(225px,.78fr);gap:16px;align-items:start;min-width:0}.scratch-controls,.scratch-details,.scratch-stage{border:1px solid var(--gold);border-radius:16px;background:rgba(20,10,34,.84);padding:16px}.scratch-controls{display:grid;gap:12px}.scratch-controls select,.scratch-controls button{min-height:42px}.scratch-primary{background:#a51f2d;color:#fff}.scratch-help,.scratch-pending,.scratch-muted,.scratch-stage-head p{color:var(--muted,#b8c8c1)}.scratch-stage{display:grid;gap:16px;min-width:0}.scratch-stage.is-empty{min-height:430px;place-content:center;text-align:center}.scratch-empty-mark{display:grid;place-items:center;width:112px;aspect-ratio:1;margin:auto;border:3px dashed rgba(255,215,128,.7);border-radius:24px;background:repeating-linear-gradient(135deg,rgba(255,215,128,.72) 0 8px,rgba(255,215,128,.12) 8px 16px)}.scratch-empty-mark::after{content:"";width:38%;aspect-ratio:1;border:5px solid #07150f;border-radius:50%;box-shadow:0 0 0 5px rgba(255,215,128,.8)}.scratch-stage-head{display:flex;align-items:start;justify-content:space-between;gap:12px}.scratch-stage-head h2{margin:.2rem 0 0}.scratch-ticket-id{padding:6px 9px;border-radius:8px;background:rgba(255,255,255,.05);font-size:.82rem}.scratch-grid{display:grid;grid-template-columns:repeat(3,minmax(90px,1fr));gap:12px;width:min(100%,620px);margin:auto}.scratch-cell{display:grid;place-content:center;gap:6px;aspect-ratio:1;min-height:90px;padding:10px;border:2px solid rgba(255,215,128,.32);border-radius:14px;background:linear-gradient(135deg,#8a774e,#d5c08b 45%,#786641);color:#10251c;transition:transform .16s ease,opacity .16s ease,border-color .16s ease}.scratch-cell.is-covered:not(:disabled):hover{transform:translateY(-2px);border-color:#fff1bd}.scratch-cell.is-revealed{background:linear-gradient(145deg,#f7edd0,#d8c38e);border-color:#ffd780;opacity:1}.scratch-foil{display:block;width:clamp(32px,5vw,54px);height:clamp(12px,2vw,20px);margin:auto;border-radius:999px;background:repeating-linear-gradient(90deg,#4f432c 0 5px,#d9c58f 5px 10px);box-shadow:0 0 0 3px rgba(16,37,28,.22)}.scratch-prize{font-size:clamp(.9rem,2vw,1.25rem);font-weight:800}.scratch-cell-state{font-size:.76rem;font-weight:700;text-transform:uppercase}.scratch-result{min-height:1.5em;margin:0;text-align:center;font-weight:700}.scratch-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.scratch-summary span{display:grid;gap:4px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.scratch-details{display:grid;gap:18px}.scratch-details h2,.scratch-details h3{margin-top:0}.scratch-tiers,.scratch-history{display:grid;gap:7px;margin:0;padding:0;list-style:none}.scratch-tiers li,.scratch-history li{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px;border-bottom:1px solid rgba(255,255,255,.1)}.scratch-shell button:focus-visible,.scratch-shell select:focus-visible{outline:3px solid var(--gold);outline-offset:3px}@media(max-width:1200px){.scratch-shell{height:auto}.scratch-layout{grid-template-columns:1fr}.scratch-controls{order:1}.scratch-stage{order:2}.scratch-details{order:3}.scratch-stage.is-empty{min-height:300px}}@media(max-width:520px){.scratch-header{align-items:start;flex-direction:column}.scratch-phase{max-width:100%}.scratch-controls,.scratch-details,.scratch-stage{padding:12px}.scratch-grid{gap:8px;grid-template-columns:repeat(3,minmax(0,1fr))}.scratch-cell{min-height:72px;padding:7px}.scratch-summary{grid-template-columns:1fr}.scratch-ticket-id{display:none}}@media(prefers-reduced-motion:reduce){.scratch-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
    /* Keep the complete three-by-three stage and instruction visible at the primary desktop viewport. */
    .scratch-grid{width:min(100%,480px)}
    /* End the scoped style block without creating a second primary scroll surface. */
  </style>`;
}


// Capture one focus identity before replacing route markup.
function focusedControlId() {
  // Read only game-owned stable focus metadata from the active element.
  return root?.contains(document.activeElement) ? document.activeElement?.dataset?.focusId || null : null;
}


// Restore focus after rerender or move to the next safe action when a cell settled.
function restoreFocus(focusId) {
  // Stop when no game-owned control held focus before the render.
  if (!focusId || !root) return;
  // Resolve the same enabled control first.
  const sameControl = root.querySelector(`[data-focus-id="${globalThis.CSS?.escape ? CSS.escape(focusId) : focusId}"]:not(:disabled)`);
  // Restore the exact control when it remains actionable.
  if (sameControl) { sameControl.focus(); return; }
  // Prefer the next covered cell regardless of its later DOM position after the control rail.
  const coveredCell = root.querySelector('[data-scratch-position]:not(:disabled)');
  // Fall back through the remaining safe actions only when no covered cell is available.
  const fallback = coveredCell || root.querySelector('[data-action="reveal-all"]:not(:disabled)') || root.querySelector('[data-action="start"]:not(:disabled)') || root.querySelector('#scratch-wager:not(:disabled)');
  // Keep keyboard users inside the active game journey when possible.
  fallback?.focus();
}


// Render the complete responsive game surface from cached masked state.
function render(preferredFocusId = null) {
  // Ignore late async work after route unmount.
  if (!root) return;
  // Preserve keyboard location across atomic markup replacement.
  const focusId = preferredFocusId || focusedControlId();
  // Read the current masked card once for consistent panel rendering.
  const card = currentCard();
  // Replace the route outlet with title, phase, and controls-stage-data hierarchy.
  root.innerHTML = `${stylesHtml()}<section class="scratch-shell" data-testid="scratch-cards"><header class="scratch-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="scratch-phase" role="status" aria-live="polite" aria-atomic="true">${safe(phaseLabel(card))}</span></header><div class="game-layout three-col stable-game scratch-layout">${controlsHtml(card)}${stageHtml(card)}${detailsHtml()}</div></section>`;
  // Bind semantic controls created by this render.
  bindEvents();
  // Restore focus without relying on a timer.
  restoreFocus(focusId);
}


// Confirm an async continuation still belongs to the same mounted route instance.
function ownsMount(generation) {
  // Require both the captured generation and a live route outlet.
  return Boolean(root && generation === mountGeneration);
}


// Refresh the shared wallet separately from game-action success or retry semantics.
async function refreshWalletSafely(generation) {
  // Start protected shell refresh handling after the game action is already committed.
  try {
    // Ask the shared shell to reload the authenticated wallet balance.
    await refreshBalance();
  // Report wallet staleness without mislabeling the completed game action as failed.
  } catch {
    // Show feedback only while the same game route still owns the outlet.
    if (ownsMount(generation)) toast(text('errors.walletRefresh'));
  }
}
// Execute one atomic browser action with stable disabled-state cleanup.
async function runAction(action) {
  // Ignore overlapping button or keyboard events.
  if (busy) return;
  // Capture route ownership so late responses cannot mutate a later player session.
  const generation = mountGeneration;
  // Preserve the initiating keyboard control across the temporary disabled render.
  const focusId = focusedControlId();
  // Disable controls before beginning the public action.
  busy = true;
  // Render disabled controls in their stable positions.
  render();
  // Start protected action handling so API errors become localized shell feedback.
  try {
    // Execute the supplied retry-safe public action.
    await action();
  // Translate failures without showing server English in another locale.
  } catch (error) {
    // Show game-owned localized diagnostic copy only on the originating route instance.
    if (ownsMount(generation)) toast(localizedError(error));
  // Always restore controls after success or failure.
  } finally {
    // Stop an old action from overwriting state owned by a later mount or session.
    if (!ownsMount(generation)) return;
    // Release the atomic action lock.
    busy = false;
    // Rerender and restore the initiating control or its next safe fallback.
    render(focusId);
  }
}


// Start one retry-safe card through the public ledger-backed endpoint.
async function startCard() {
  // Capture route ownership before the network action begins.
  const generation = mountGeneration;
  // Reuse an unresolved request identity so a lost response cannot debit twice.
  pendingStartId = pendingStartId || createActionId('scratch-start');
  // Capture the exact identity and wager so locale renders cannot change request meaning.
  const request = { clientRequestId: pendingStartId, wager: selectedWager };
  // Post only wager and retry identity plus the compatibility current-player field.
  const payload = await post(`${API_ROOT}/cards`, withCurrentPlayer({ client_request_id: request.clientRequestId, wager: request.wager }));
  // Ignore a response that belongs to an unmounted or replaced player session.
  if (!ownsMount(generation)) return;
  // Store returned reload-safe masked state after the committed wager.
  state = payload.state;
  // Clear the retry identity only after a committed response returns.
  pendingStartId = null;
  // Clear any stale reveal retry left from the prior settled card.
  pendingScratch = null;
  // Refresh the authenticated shared wallet without changing action success semantics.
  await refreshWalletSafely(generation);
}


// Persist one partial or complete position set through a stable scratch action id.
async function scratchPositions(positions) {
  // Capture route ownership before reading or posting player state.
  const generation = mountGeneration;
  // Read the current card before constructing a card-scoped URL.
  const card = currentCard();
  // Stop stale control events when no funded card exists.
  if (!card) return;
  // Preserve an unresolved prior action exactly, even if a later click requests another cell.
  pendingScratch = pendingScratch || { cardId: card.card_id, actionId: createActionId('scratch-reveal'), positions: [...positions] };
  // Capture the immutable request object so later lifecycle cleanup cannot alter the POST.
  const request = { cardId: pendingScratch.cardId, actionId: pendingScratch.actionId, positions: [...pendingScratch.positions] };
  // Post the retained action meaning so network retries cannot change revealed positions.
  const payload = await post(`${API_ROOT}/cards/${encodeURIComponent(request.cardId)}/scratches`, withCurrentPlayer({ action_id: request.actionId, positions: request.positions }));
  // Ignore a response that belongs to an unmounted or replaced player session.
  if (!ownsMount(generation)) return;
  // Store the returned masked partial or fully revealed state.
  state = payload.state;
  // Clear the retry record only after the server confirms persistence or settlement.
  pendingScratch = null;
  // Refresh the shared wallet separately when final reveal may have credited a prize.
  if (payload.card?.status === 'settled') await refreshWalletSafely(generation);
}


// Attach semantic control handlers after every deterministic render.
function bindEvents() {
  // Resolve the wager selector when the current phase allows changes.
  const wagerSelect = root?.querySelector('#scratch-wager');
  // Preserve normalized selection for the next start action.
  if (wagerSelect) wagerSelect.onchange = () => { selectedWager = Number(wagerSelect.value); render(); };
  // Resolve the stable start-card primary action.
  const startButton = root?.querySelector('[data-action="start"]');
  // Start one retry-safe card when the control is available.
  if (startButton) startButton.onclick = () => runAction(startCard);
  // Resolve the stable reveal-all action.
  const revealAllButton = root?.querySelector('[data-action="reveal-all"]');
  // Reveal every remaining cell through one persisted action.
  if (revealAllButton) revealAllButton.onclick = () => runAction(() => scratchPositions(coveredPositions(currentCard())));
  // Bind every covered semantic cell through the same public action path.
  root?.querySelectorAll('[data-scratch-position]:not(:disabled)').forEach(button => {
    // Reveal exactly the selected zero-based position.
    button.onclick = () => runAction(() => scratchPositions([Number(button.dataset.scratchPosition)]));
  });
}


// Resume a crash-interrupted purchase with the server-published request identity and wager.
async function resumePurchaseIfNeeded(generation) {
  // Read the restored current card after state loading.
  const card = currentCard();
  // Stop unless this exact mount owns a persisted purchase intent.
  if (!ownsMount(generation) || card?.status !== 'purchasing' || !card.pending_client_request_id) return false;
  // Reuse the original public identity so recovery cannot create another debit.
  pendingStartId = card.pending_client_request_id;
  // Restore the exact normalized wager paired with that identity.
  selectedWager = Number(card.wager);
  // Resume through normal busy, localized error, and wallet-refresh handling.
  await runAction(startCard);
  // Report that normal action handling already performed any required wallet refresh.
  return true;
}


// Resume a crash-interrupted final reveal using only server-published retry fields.
async function resumeSettlementIfNeeded(generation) {
  // Read the restored current card after state loading.
  const card = currentCard();
  // Stop unless this exact mount owns a persisted settlement intent.
  if (!root || generation !== mountGeneration || card?.status !== 'settling' || !card.pending_action_id) return;
  // Reconstruct the identical bounded action from public recovery metadata.
  pendingScratch = { cardId: card.card_id, actionId: card.pending_action_id, positions: [...(card.pending_positions || [])] };
  // Resume through normal busy, error, and wallet-refresh handling.
  await runAction(() => scratchPositions(pendingScratch.positions));
}


// Export the catalog-loadable lazy game contract expected by the shared descriptor loader.
export const ScratchCardsGame = {
  // Identify the module consistently with its descriptor and private API state.
  id: 'scratch_cards',
  // Leave presentation labels to the owned descriptor and locale resources.
  label: '',
  // Load locale and masked player state before rendering any visible copy.
  async mount(node) {
    // Advance and capture the active mount generation.
    const generation = ++mountGeneration;
    // Retain the shell-provided route outlet.
    root = node;
    // Start protected loading so a rejected mount cannot retain a locale callback or outlet.
    try {
      // Load both active and fallback Scratch Cards dictionaries before first render.
      await loadI18nDomain(DOMAIN);
      // Stop if navigation replaced this route during locale loading.
      if (!ownsMount(generation)) return;
      // Rerender copy in place only while this generation owns the game route.
      unsubscribeLocale = onLocaleChange(() => { if (ownsMount(generation)) render(); });
      // Read the authenticated player's masked reload-safe state.
      const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
      // Stop if navigation replaced this route during state loading.
      if (!ownsMount(generation)) return;
      // Cache only the public state used by controls, stage, and history.
      state = payload;
      // Render the complete issue #87 surface.
      render();
      // Resume a persisted purchase before exposing any reveal action.
      const resumedPurchase = await resumePurchaseIfNeeded(generation);
      // Align the shell wallet when purchase action handling did not already refresh it.
      if (!resumedPurchase) await refreshWalletSafely(generation);
      // Resume a persisted final reveal without a game-owned timer.
      await resumeSettlementIfNeeded(generation);
    // Release this failed mount before the shared shell renders its recovery panel.
    } catch (error) {
      // Ignore failures from a route instance that navigation already replaced.
      if (generation !== mountGeneration) return;
      // Unsubscribe the locale callback installed by this failed generation.
      if (unsubscribeLocale) unsubscribeLocale();
      // Clear the callback reference so later cleanup remains idempotent.
      unsubscribeLocale = null;
      // Clear player-owned state and retry identities from the failed mount.
      state = null;
      // Release the pending purchase identity from this route instance.
      pendingStartId = null;
      // Release the pending reveal identity from this route instance.
      pendingScratch = null;
      // Release the route outlet before the shared recovery UI takes ownership.
      root = null;
      // Release the local action flag without touching any global listener or timer.
      busy = false;
      // Re-throw so the shared shell can render its localized load failure state.
      throw error;
    }
  },
  // Release every game-owned lifecycle resource on route exit.
  unmount() {
    // Invalidate every late async continuation from this mount.
    mountGeneration += 1;
    // Unsubscribe the locale callback when it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated unmounts remain safe.
    unsubscribeLocale = null;
    // Clear masked player state so another session cannot reuse prior data.
    state = null;
    // Release unresolved browser retry records on route ownership change.
    pendingStartId = null;
    // Release unresolved scratch records; persisted server state remains authoritative on remount.
    pendingScratch = null;
    // Release the DOM reference so late promises cannot render into another route.
    root = null;
    // Release the local action flag; this module owns no timers or global listeners.
    busy = false;
  },
};
