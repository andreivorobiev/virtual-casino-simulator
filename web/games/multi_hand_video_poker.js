// Implement the isolated issue #94 browser module without shared shell edits.

// Import session-aware API helpers so #81 can override every caller-provided identity.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback and escaping without owning global timers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the accessible #96 card renderer rather than creating game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the owned locale domain used by every player-visible string.
const DOMAIN = 'games/multi_hand_video_poker';
// Store the isolated frozen-v1 API root once for all action helpers.
const API_ROOT = '/api/v1/games/multi-hand-video-poker';
// Store exactly the three play modes required by issue #94.
const HAND_COUNTS = [3, 5, 10];
// Store paytable display order independently of object insertion behavior.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'jacks_or_better'];
// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest player-scoped state payload for reload-safe rendering.
let state = null;
// Store server-supplied paytable multipliers for the data rail.
let paytable = {};
// Store the selected hand mode before the next deal.
let handCount = 3;
// Store the selected per-hand wager before the next deal.
let wagerPerHand = 1;
// Store the in-flight action flag so atomic controls cannot overlap.
let busy = false;
// Store the locale cleanup callback so unmount releases subscriptions.
let unsubscribeLocale = null;
// Store a fallback retry-id counter for browsers without randomUUID support.
let requestCounter = 0;
// Retain an unresolved deal retry key so a lost response can replay the same wager.
let pendingRequestId = null;


// Resolve one owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every player-visible label to the EN/RU domain resource.
  return t(key, params, DOMAIN);
}


// Format play-token values without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Format two decimal places followed by localized fake-token terminology.
  return `${formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${text('units.playTokens')}`;
}


// Render a shared #96 card while localizing its accessible name for EN/RU parity.
function localizedCard(card, options = {}) {
  // Normalize the compact rank from every character except the final suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build the accessible label entirely from the owned locale domain.
  const label = text('cards.cardLabel', { rank: text(`ranks.${rank}`), suit: text(`suits.${suit}`) });
  // Use the shared semantic renderer and replace only its locale-neutral accessible label.
  return renderCard(card, options).replace(/aria-label="[^"]*"/, `aria-label="${safe(label)}"`);
}


// Return the active round or newest settled round for one stable stage.
function currentRound() {
  // Prefer the actionable common hand before the recent settled collection.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}


// Create one client retry key so network retries cannot duplicate a wager debit.
function nextRequestId() {
  // Use the browser cryptographic UUID source when it is available.
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  // Increment the fallback counter to disambiguate deals in one millisecond.
  requestCounter += 1;
  // Combine a timestamp and counter without claiming cryptographic fairness.
  return `browser-${Date.now().toString(36)}-${requestCounter.toString(36)}`;
}


// Translate one internal round phase into player-facing status copy.
function phaseLabel(roundItem) {
  // Show the idle phase when no round has been dealt.
  if (!roundItem) return text('phases.ready');
  // Show the common hold decision phase while cards are selectable.
  if (roundItem.phase === 'hold') return text('phases.chooseHolds');
  // Show a localized aggregate result after settlement.
  return text(`phases.${roundItem.outcome || 'complete'}`);
}


// Render one selectable source card through the accessible shared renderer.
function sourceCard(card, position, held, disabled) {
  // Resolve the action label from the current selection state.
  const actionLabel = held ? text('cards.release', { position: position + 1 }) : text('cards.hold', { position: position + 1 });
  // Render a semantic button whose selected state is communicated beyond color.
  return `<button type="button" class="mhvp-card-button${held ? ' is-held' : ''}" data-hold-position="${position}" aria-pressed="${held}" aria-label="${safe(actionLabel)}"${disabled ? ' disabled' : ''}>${localizedCard(card, { selected: held })}${held ? `<span class="mhvp-held-label">${safe(text('cards.held'))}</span>` : ''}</button>`;
}


// Render the common five-card source hand used by every selected lane.
function sourceHand(roundItem) {
  // Build a set so selected positions can be checked without order assumptions.
  const held = new Set(roundItem.holds || []);
  // Disable selection outside the hold phase or during an atomic request.
  const disabled = roundItem.phase !== 'hold' || busy;
  // Render all five common source positions with localized group semantics.
  const cards = (roundItem.initial_hand || []).map((card, position) => sourceCard(card, position, held.has(position), disabled)).join('');
  // Return the dominant source-hand region with a stable browser-test hook.
  return `<section class="mhvp-source" aria-label="${safe(text('stage.sourceHand'))}" data-testid="mhvp-source-hand"><p class="mhvp-stage-kicker">${safe(text('stage.sharedAcross', { count: roundItem.hand_count }))}</p><div class="mhvp-card-row">${cards}</div></section>`;
}


// Render one completed independent hand lane.
function resultHand(result) {
  // Render final cards as non-interactive accessible shared-card elements.
  const cards = (result.cards || []).map(card => localizedCard(card)).join('');
  // Translate the game-owned outcome key through the active locale.
  const outcome = text(`outcomes.${result.outcome}`);
  // Return a compact responsive lane with result and returned credits.
  return `<article class="mhvp-result" data-testid="mhvp-result-${result.hand_index}"><header><h3>${safe(text('hands.handNumber', { number: result.hand_index + 1 }))}</h3><span>${safe(outcome)}</span></header><div class="mhvp-card-row" role="group" aria-label="${safe(text('hands.finalCards', { number: result.hand_index + 1 }))}">${cards}</div><p>${safe(text('hands.payout'))}: <strong>${safe(tokenAmount(result.payout))}</strong></p></article>`;
}


// Render the dominant game stage for idle, hold, and settled states.
function stageHtml(roundItem) {
  // Render localized guidance before the first wager.
  if (!roundItem) return `<section class="mhvp-empty" data-testid="mhvp-empty"><h2>${safe(text('stage.readyTitle'))}</h2><p>${safe(text('stage.readyBody'))}</p></section>`;
  // Render both the shared source hand and every final lane when available.
  const results = (roundItem.results || []).map(resultHand).join('');
  // Build the aggregate settlement summary only after a draw.
  const summary = roundItem.phase === 'settled' ? `<section class="mhvp-summary" data-testid="mhvp-summary"><span>${safe(text('summary.wager'))}: <strong>${safe(tokenAmount(roundItem.total_wager))}</strong></span><span>${safe(text('summary.payout'))}: <strong>${safe(tokenAmount(roundItem.total_payout))}</strong></span><span>${safe(text('summary.net'))}: <strong>${safe(tokenAmount(roundItem.net))}</strong></span></section>` : '';
  // Return the source hand, optional summary, and responsive results grid.
  return `${sourceHand(roundItem)}${summary}${results ? `<section class="mhvp-results" aria-label="${safe(text('stage.finalHands'))}">${results}</section>` : ''}`;
}


// Render issue #94 mode, wager, and atomic action controls.
function controlsHtml(roundItem) {
  // Disable configuration while a round is active or any request is in flight.
  const configurationDisabled = Boolean(state?.active_round) || busy;
  // Render one pressed-state mode button per accepted hand count.
  const modes = HAND_COUNTS.map(count => `<button type="button" data-hand-count="${count}" aria-pressed="${handCount === count}" class="mhvp-mode${handCount === count ? ' is-selected' : ''}"${configurationDisabled ? ' disabled' : ''}>${safe(text('modes.handCount', { count }))}</button>`).join('');
  // Enable deal only when no common hand is active.
  const dealDisabled = Boolean(state?.active_round) || busy;
  // Enable draw only while the common hand awaits a decision.
  const drawDisabled = !roundItem || roundItem.phase !== 'hold' || busy;
  // Return the complete control rail with stable primary-action placement.
  return `<aside class="mhvp-panel mhvp-controls" aria-label="${safe(text('controls.title'))}"><h2>${safe(text('controls.title'))}</h2><fieldset${configurationDisabled ? ' disabled' : ''}><legend>${safe(text('controls.mode'))}</legend><div class="mhvp-modes">${modes}</div></fieldset><label for="mhvp-wager">${safe(text('controls.wagerPerHand'))}</label><input id="mhvp-wager" type="number" min="0.01" max="100000" step="0.01" value="${safe(wagerPerHand)}"${configurationDisabled ? ' disabled' : ''}><p class="mhvp-total">${safe(text('controls.totalWager'))}: <strong>${safe(tokenAmount(handCount * wagerPerHand))}</strong></p><button type="button" class="mhvp-primary" data-action="deal"${dealDisabled ? ' disabled' : ''}>${safe(text('controls.deal'))}</button><button type="button" data-action="draw"${drawDisabled ? ' disabled' : ''}>${safe(text('controls.draw'))}</button><p class="mhvp-help">${safe(text('controls.holdHelp'))}</p></aside>`;
}


// Render the game-owned Jacks-or-Better paytable in the data rail.
function paytableHtml() {
  // Render every qualifying outcome in canonical strength order.
  const rows = PAYTABLE_ORDER.map(outcome => `<tr><th scope="row">${safe(text(`outcomes.${outcome}`))}</th><td>${safe(text('paytable.multiplier', { value: paytable[outcome] ?? 0 }))}</td></tr>`).join('');
  // Return one keyboard-readable table without nested scrolling containers.
  return `<aside class="mhvp-panel mhvp-data" aria-label="${safe(text('paytable.title'))}"><h2>${safe(text('paytable.title'))}</h2><table><thead><tr><th>${safe(text('paytable.result'))}</th><th>${safe(text('paytable.return'))}</th></tr></thead><tbody>${rows}</tbody></table><p>${safe(text('paytable.note'))}</p></aside>`;
}


// Return game-owned styles inside the lazy module so no shared stylesheet is touched.
function stylesHtml() {
  // Keep the game stage dominant at desktop and stack controls first on narrow screens.
  return `<style>
    /* Keep all responsive presentation owned by the lazy issue #94 module. */
    .mhvp-shell{display:grid;gap:18px;min-width:0}.mhvp-header{display:flex;align-items:end;justify-content:space-between;gap:12px}.mhvp-header h1{margin:0}.mhvp-phase{padding:7px 12px;border:1px solid rgba(255,215,128,.45);border-radius:999px}.mhvp-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(540px,2.4fr) minmax(230px,.8fr);gap:16px;align-items:start}.mhvp-panel,.mhvp-stage{border:1px solid rgba(255,215,128,.24);border-radius:16px;background:rgba(3,29,20,.82);padding:16px}.mhvp-controls{display:grid;gap:12px}.mhvp-controls fieldset{margin:0;padding:0;border:0}.mhvp-modes{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.mhvp-mode.is-selected{outline:2px solid #ffd780;outline-offset:2px}.mhvp-primary{background:#a51f2d;color:#fff}.mhvp-help,.mhvp-total,.mhvp-data p{color:var(--muted,#b8c8c1)}.mhvp-stage{display:grid;gap:16px;min-width:0}.mhvp-stage-kicker{margin:0 0 10px;text-align:center}.mhvp-card-row{display:flex;flex-wrap:wrap;justify-content:center;gap:8px}.mhvp-card-button{position:relative;min-width:58px;min-height:86px;padding:2px;border:2px solid transparent;background:transparent}.mhvp-card-button.is-held{border-color:#ffd780;border-radius:10px}.mhvp-held-label{position:absolute;inset:auto 3px 3px;padding:2px 5px;border-radius:999px;background:#07150f;color:#ffd780;font-size:10px}.mhvp-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.mhvp-summary span{padding:10px;border-radius:10px;background:rgba(255,255,255,.04)}.mhvp-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.mhvp-result{display:grid;gap:8px;padding:12px;border:1px solid rgba(255,255,255,.12);border-radius:12px}.mhvp-result header{display:flex;justify-content:space-between;gap:8px}.mhvp-result h3,.mhvp-result p{margin:0}.mhvp-result .playing-card{font-size:clamp(.65rem,1vw,.9rem)}.mhvp-data table{width:100%;border-collapse:collapse}.mhvp-data th,.mhvp-data td{padding:7px 4px;border-bottom:1px solid rgba(255,255,255,.1);text-align:left}.mhvp-empty{min-height:330px;display:grid;place-content:center;text-align:center}.mhvp-card-button:focus-visible,.mhvp-shell button:focus-visible,.mhvp-shell input:focus-visible{outline:3px solid #ffd780;outline-offset:2px}@media(max-width:1100px){.mhvp-layout{grid-template-columns:1fr}.mhvp-controls{order:1}.mhvp-stage{order:2}.mhvp-data{order:3}.mhvp-results{grid-template-columns:1fr}}@media(max-width:520px){.mhvp-header{align-items:start;flex-direction:column}.mhvp-panel,.mhvp-stage{padding:12px}.mhvp-summary{grid-template-columns:1fr}.mhvp-card-button{min-width:48px;min-height:72px}}@media(prefers-reduced-motion:reduce){.mhvp-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
    /* End the game-owned style block without creating global runtime resources. */
  </style>`;
}


// Render the complete three-zone game surface from cached state.
function render() {
  // Stop when an async completion arrives after unmount.
  if (!root) return;
  // Read the current active or newest completed round once per render.
  const roundItem = currentRound();
  // Replace the route outlet atomically so controls and stage cannot drift.
  root.innerHTML = `${stylesHtml()}<section class="mhvp-shell" data-testid="multi-hand-video-poker"><header class="mhvp-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="mhvp-phase" role="status">${safe(phaseLabel(roundItem))}</span></header><div class="mhvp-layout">${controlsHtml(roundItem)}<main class="mhvp-stage">${stageHtml(roundItem)}</main>${paytableHtml()}</div></section>`;
  // Attach event handlers to the newly rendered semantic controls.
  bindEvents();
}


// Execute one atomic browser action with stable disabled-state cleanup.
async function runAction(action) {
  // Ignore overlapping button events while an API request is in flight.
  if (busy) return;
  // Disable controls before beginning the action.
  busy = true;
  // Render disabled controls in their stable positions.
  render();
  // Start protected action handling so API errors become shell feedback.
  try {
    // Execute the supplied public API action.
    await action();
  // Translate API failures into the existing shared toast surface.
  } catch (error) {
    // Show the server-provided diagnostic without inserting raw HTML.
    toast(error.message);
  // Always restore controls after success or failure.
  } finally {
    // Release the action lock.
    busy = false;
    // Rerender only when the route remains mounted.
    render();
  }
}


// Start one idempotent multi-hand wager through the public endpoint.
async function deal() {
  // Read the wager input before rerender removes its current value.
  const input = root?.querySelector('#mhvp-wager');
  // Normalize the cached wager used by this request and later renders.
  wagerPerHand = Math.max(0.01, Number(input?.value || wagerPerHand || 1));
  // Reuse an unresolved request key so retry cannot create a second wager.
  pendingRequestId = pendingRequestId || nextRequestId();
  // Post the selected mode, wager, and unique retry key for one aggregate debit.
  const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ request_id: pendingRequestId, hand_count: handCount, wager_per_hand: wagerPerHand }));
  // Store returned reload-safe state after the committed wager.
  state = payload.state;
  // Clear the retry key only after the server response proves state was recovered.
  pendingRequestId = null;
  // Store the server paytable in case catalog integration mounted before initial state loading.
  paytable = payload.paytable || paytable;
  // Refresh the shared authenticated wallet after ledger movement.
  await refreshBalance();
}


// Persist one changed hold position for reload-safe continuation.
async function toggleHold(position) {
  // Read the active common source hand before constructing the next selection.
  const roundItem = state?.active_round;
  // Stop stale clicks when the active round has already settled.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Build a mutable selection set from server state.
  const holds = new Set(roundItem.holds || []);
  // Remove an already-held position or add a newly held one.
  if (holds.has(position)) holds.delete(position); else holds.add(position);
  // Persist the canonical selection through the game API.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/holds`, withCurrentPlayer({ holds: [...holds].sort((left, right) => left - right) }));
  // Store the returned reload-safe state.
  state = payload.state;
}


// Draw every configured hand and request one aggregate ledger settlement.
async function draw() {
  // Read the active common hand before settlement archives it.
  const roundItem = state?.active_round;
  // Stop stale clicks when no active hold-phase round exists.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Complete and settle the deterministic server-owned hands.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/draw`, withCurrentPlayer({}));
  // Store the completed reload-safe state for all result lanes.
  state = payload.state;
  // Refresh the shared authenticated wallet after any payout credit.
  await refreshBalance();
}


// Attach semantic control handlers after every atomic render.
function bindEvents() {
  // Wire mode buttons to cached pre-deal configuration.
  root.querySelectorAll('[data-hand-count]').forEach(button => {
    // Change the selected mode and rerender its pressed state.
    button.onclick = () => { handCount = Number(button.dataset.handCount); render(); };
  });
  // Preserve valid wager edits in cached configuration.
  const wagerInput = root.querySelector('#mhvp-wager');
  // Update the preview without issuing any token movement.
  if (wagerInput) wagerInput.onchange = () => { wagerPerHand = Math.max(0.01, Number(wagerInput.value || 1)); render(); };
  // Wire the primary deal action through shared busy handling.
  const dealButton = root.querySelector('[data-action="deal"]');
  // Start one idempotent deal when the mounted button is available.
  if (dealButton) dealButton.onclick = () => runAction(deal);
  // Wire the primary draw action through shared busy handling.
  const drawButton = root.querySelector('[data-action="draw"]');
  // Complete every hand when the mounted button is available.
  if (drawButton) drawButton.onclick = () => runAction(draw);
  // Wire every source card to reload-safe hold persistence.
  root.querySelectorAll('[data-hold-position]').forEach(button => {
    // Toggle the selected position through the public API.
    button.onclick = () => runAction(() => toggleHold(Number(button.dataset.holdPosition)));
  });
}


// Export the catalog-owned lazy game module contract expected by #110.
export const MultiHandVideoPokerGame = {
  // Expose the stable module id used by catalog navigation.
  id: 'multi_hand_video_poker',
  // Leave presentation labels to the owned descriptor and locale domain.
  label: '',
  // Load locale and player state before rendering any visible text.
  async mount(node) {
    // Store the route outlet for subsequent deterministic renders.
    root = node;
    // Load both active and fallback game-owned resources.
    await loadI18nDomain(DOMAIN);
    // Subscribe to locale changes without remounting or losing hold state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read the authenticated player's reload-safe state.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Cache the state used by stage and controls.
    state = payload.state;
    // Cache the authoritative server paytable used by the data rail.
    paytable = payload.paytable || {};
    // Adopt the active round's mode when restoring a direct route or reload.
    handCount = state?.active_round?.hand_count || handCount;
    // Adopt the active round's wager when restoring a direct route or reload.
    wagerPerHand = state?.active_round?.wager_per_hand || wagerPerHand;
    // Render the complete issue #94 surface.
    render();
    // Refresh the shared wallet without game-owned balance text.
    await refreshBalance();
  },
  // Release every game-owned lifecycle resource when the shell changes route.
  unmount() {
    // Unsubscribe the locale callback when it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated unmounts remain safe.
    unsubscribeLocale = null;
    // Clear cached player state from the inactive module.
    state = null;
    // Clear the mount node so late promises cannot render into another route.
    root = null;
    // No timers or listeners remain because this module creates none outside the locale subscription.
  },
};
