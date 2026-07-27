// Provide the isolated Red Dog browser module for GitHub issue #84.
// Requirements: CARD-002, CORE-008, I18N-001, I18N-002, UX-001, UX-002, UX-003, UX-006.

// Import the standard authenticated API helpers used by lazy game modules.
import { api, post } from '../core/api.js';
// Import safe markup, localized error presentation, and shared wallet refresh support.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the merged accessible card primitive instead of creating game-owned cards.
import { renderCard } from '../core/cards.js';
// Import locale loading, number formatting, lookup, and live-switch subscriptions.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Address every additive Red Dog route from one stable API root.
const API_ROOT = '/api/v1/games/red-dog';
// Address the paired game-owned EN/RU resource domain.
const DOMAIN = 'games/red_dog';
// Identify the shared card stylesheet so only one link is installed.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Offer bounded wager choices without embedding visible labels in JavaScript.
const WAGERS = [5, 25, 100, 500];

// Retain the active mount node without creating shared shell state.
let root = null;
// Retain the latest session-scoped API state for locale-only rerenders.
let state = null;
// Prevent overlapping atomic commands from repeated clicks.
let busy = false;
// Retain retry keys after uncertain failures so a retry cannot duplicate settlement.
let retryActionIds = new Map();
// Retain the locale unsubscribe callback for leak-free route changes.
let unsubscribeLocale = null;
// Retain only a stylesheet link created by this mount so cleanup is ownership-safe.
let ownedCardStyleLink = null;

// Read one localized Red Dog string after the game domain has loaded.
function text(key, params = {}) {
  // Delegate all visible and accessible copy to the paired dictionaries.
  return t(key, params, DOMAIN);
}

// Format a play-token amount without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Format the numeric component through the active locale.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Wrap the number in explicit localized play-token language.
  return text('tokens.amount', { amount });
}

// Install the merged CARD-002 stylesheet without editing shared shell files.
function ensureSharedCardStyles() {
  // Reuse a stylesheet already installed by another card-game mount.
  if (document.getElementById(CARD_STYLE_ID)) {
    // Record that this mount does not own the shared link.
    ownedCardStyleLink = null;
    // Stop before installing a duplicate resource.
    return;
  }
  // Create one link to the merged responsive card stylesheet.
  const link = document.createElement('link');
  // Mark the resource so future mounts can reuse it.
  link.id = CARD_STYLE_ID;
  // Load the file as a standard stylesheet.
  link.rel = 'stylesheet';
  // Point to the shared CARD-002 presentation without copying its rules.
  link.href = '/core/cards.css';
  // Install the resource in document metadata.
  document.head.append(link);
  // Record ownership so this mount can remove only what it created.
  ownedCardStyleLink = link;
}

// Generate one bounded client action id for exactly-once API commands.
function newActionId() {
  // Prefer a browser-native UUID when the platform provides one.
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  // Build a conservative fallback from time and a random suffix for older local browsers.
  return `browser-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

// Reuse one id for the same logical command until the server confirms success.
function actionIdFor(commandKey) {
  // Return the retained id when an earlier response was uncertain.
  if (retryActionIds.has(commandKey)) return retryActionIds.get(commandKey);
  // Create a fresh id only for a command that has never been attempted.
  const actionId = newActionId();
  // Retain the id before any network work begins.
  retryActionIds.set(commandKey, actionId);
  // Return the stable command id to the caller.
  return actionId;
}

// Return the newest actionable or settled round for the table stage.
function currentRound() {
  // Prefer the explicit active round and then the newest retained history row.
  return state?.active_round || state?.rounds?.[0] || null;
}

// Translate one internal phase into concise player-facing copy.
function phaseLabel(roundItem = currentRound()) {
  // Show the ready phase before any opening has been dealt.
  if (!roundItem) return text('phase.ready');
  // Resolve the documented phase through owned locale resources.
  return text(`phase.${roundItem.phase}`);
}

// Translate one internal outcome without exposing raw API identifiers.
function outcomeLabel(roundItem) {
  // Show a localized ready result before a round exists.
  if (!roundItem) return text('outcome.pending');
  // Resolve every documented outcome through the game domain.
  return text(`outcome.${roundItem.outcome}`);
}

// Translate one API card into a complete accessible name.
function cardLabel(card) {
  // Use the localized placeholder label before a card exists.
  if (!card) return text('card.waiting');
  // Resolve rank and suit names without inheriting CARD-002 English labels.
  return text('card.label', { rank: text(`rank.${card.rank}`), suit: text(`suit.${card.suit}`) });
}

// Render one shared card primitive with game-owned EN/RU accessibility copy.
function localizedCard(card) {
  // Reserve a labeled card slot before the API exposes a card.
  if (!card) return `<div class="rd-card-empty" role="img" aria-label="${safe(cardLabel(null))}"></div>`;
  // Render the validated card through the merged primitive.
  const markup = renderCard(card);
  // Replace the primitive's default English label with the active game locale.
  return markup.replace(/aria-label="[^"]*"/, `aria-label="${safe(cardLabel(card))}"`);
}

// Return scoped layout rules that keep the card stage visually dominant.
function styleHtml() {
  // Define desktop hierarchy, accessible scroll treatment, and stable reserved regions.
  const desktop = '.red-dog{display:grid;gap:14px;min-width:0;min-height:0}.rd-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.rd-header h1,.rd-panel h2,.rd-panel h3{margin:0}.rd-phase{min-height:34px;padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.rd-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(500px,2.25fr) minmax(210px,.72fr);gap:14px;min-width:0;min-height:0}.rd-panel{min-width:0;border:1px solid var(--border);border-radius:16px;background:var(--panel-strong);padding:16px}.rd-controls,.rd-data{display:grid;align-content:start;gap:14px}.rd-controls label{display:grid;gap:7px}.rd-controls select,.rd-controls button{min-height:44px}.rd-actions{display:grid;gap:10px}.rd-actions--decision{grid-template-columns:1fr 1fr}.rd-primary{background:var(--red,#a92a38);color:#fff}.rd-stage{display:grid;grid-template-rows:auto minmax(310px,1fr) auto;gap:18px;background:radial-gradient(circle at 50% 38%,rgba(35,17,61,.42),rgba(21,10,36,.96) 70%)}.rd-stage-head{display:flex;align-items:start;justify-content:space-between;gap:12px;min-height:58px}.rd-stage-head p{margin:0}.rd-spread{display:grid;place-items:center;min-width:72px;min-height:52px;padding:7px;border:1px solid var(--gold);border-radius:12px;text-align:center}.rd-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:center;justify-items:center;gap:clamp(12px,3vw,34px)}.rd-card-slot{display:grid;justify-items:center;align-content:center;gap:10px;min-width:0}.rd-card-slot h3{font-size:.9rem;text-align:center}.rd-card-empty{width:clamp(3.25rem,8vw,6.5rem);aspect-ratio:5/7;border:2px dashed rgba(255,255,255,.26);border-radius:.65rem}.rd-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;min-height:76px}.rd-stat{min-width:0;padding:10px;border-radius:10px;background:rgba(0,0,0,.2)}.rd-stat span,.rd-history-wager{display:block;color:var(--muted,#b8c7c0);font-size:.78rem}.rd-stat strong{overflow-wrap:anywhere}.rd-data-scroll{display:grid;gap:14px;max-height:475px;overflow:auto;overscroll-behavior:contain;scrollbar-width:thin;touch-action:pan-y}.rd-data-scroll:focus-visible{outline:3px solid var(--gold,#f6d47a);outline-offset:3px}.rd-paytable{width:100%;border-collapse:collapse}.rd-paytable th,.rd-paytable td{padding:7px 5px;border-bottom:1px solid rgba(255,255,255,.1);text-align:left}.rd-history-list{display:grid;gap:9px}.rd-history-row{display:grid;grid-template-columns:1fr auto;gap:5px;padding:10px;border-radius:10px;background:rgba(0,0,0,.18)}.rd-rules{margin:0;padding-left:1.1rem}.rd-rules li+li{margin-top:8px}.rd-muted{color:var(--muted,#b8c7c0)}.rd-busy{min-height:22px}';
  // Stack controls, stage, and data for tablet-width interaction.
  const tablet = '@media (max-width:1100px){.rd-layout{grid-template-columns:1fr}.rd-controls{order:1}.rd-stage{order:2}.rd-data{order:3}.rd-stage{grid-template-rows:auto minmax(260px,1fr) auto}.rd-data-scroll{max-height:none;overflow:visible}}';
  // Prevent clipped controls, cards, and summaries on the mobile viewport.
  const mobile = '@media (max-width:520px){.rd-header{align-items:start;flex-direction:column}.rd-panel{padding:13px}.rd-actions--decision,.rd-summary{grid-template-columns:1fr}.rd-cards{gap:8px}.rd-stage{grid-template-rows:auto minmax(220px,1fr) auto}.rd-card-slot h3{font-size:.78rem}}';
  // Remove decorative motion whenever the platform requests reduced motion.
  const reducedMotion = '@media (prefers-reduced-motion:reduce){.red-dog *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}';
  // Return one game-scoped stylesheet without changing shared shell CSS.
  return `<style>${desktop}${tablet}${mobile}${reducedMotion}</style>`;
}

// Render the control rail for ready, decision, and settled phases.
function controlsHtml(roundItem) {
  // Detect the only phase where call and raise choices are available.
  const decision = roundItem?.phase === 'raise_decision';
  // Build localized wager options without hard-coded visible units.
  const options = WAGERS.map(value => `<option value="${value}">${safe(tokenAmount(value))}</option>`).join('');
  // Render the phase-appropriate primary actions in a stable reserved region.
  const actions = decision
    // Offer call and matching raise together after a valid spread.
    ? `<div class="rd-actions rd-actions--decision"><button type="button" data-action="call" ${busy ? 'disabled' : ''}>${safe(text('controls.call'))}</button><button type="button" class="rd-primary" data-action="raise" ${busy ? 'disabled' : ''}>${safe(text('controls.raise'))}</button></div>`
    // Offer the next opening outside the decision phase.
    : `<div class="rd-actions"><button type="button" class="rd-primary" data-action="deal" ${busy ? 'disabled' : ''}>${safe(roundItem ? text('controls.dealNext') : text('controls.deal'))}</button></div>`;
  // Return accessible controls and concise table rules above the rail fold.
  return `<section class="rd-panel rd-controls" aria-label="${safe(text('controls.region'))}"><h2>${safe(text('controls.title'))}</h2><label>${safe(text('controls.wager'))}<select data-testid="red-dog-wager" ${decision || busy ? 'disabled' : ''}>${options}</select></label>${actions}<p class="rd-muted">${safe(decision ? text('controls.decisionHelp') : text('controls.readyHelp'))}</p><p class="rd-muted rd-busy" role="status" aria-live="polite">${busy ? safe(text('controls.busy')) : ''}</p><h3>${safe(text('rules.title'))}</h3><ul class="rd-rules"><li>${safe(text('rules.objective'))}</li><li>${safe(text('rules.consecutive'))}</li><li>${safe(text('rules.pair'))}</li><li>${safe(text('rules.raise'))}</li></ul></section>`;
}

// Render one labeled card slot using only localized accessible names.
function cardSlot(labelKey, card) {
  // Resolve the localized slot heading and group label.
  const label = text(labelKey);
  // Return a stable slot whose geometry does not change when the card arrives.
  return `<section class="rd-card-slot" aria-label="${safe(label)}"><h3>${safe(label)}</h3>${localizedCard(card)}</section>`;
}

// Render the dominant three-card table and settlement summary.
function stageHtml(roundItem) {
  // Read numeric fields through zero-safe fallbacks for the ready state.
  const wager = Number(roundItem?.wager || 0);
  // Read the optional matching raise amount.
  const raiseWager = Number(roundItem?.raise_wager || 0);
  // Read total committed stakes from the public round.
  const totalWager = Number(roundItem?.total_wager || 0);
  // Read the returned credit after settlement.
  const payout = Number(roundItem?.payout || 0);
  // Read the final net result only when the round exposes it.
  const net = Number(roundItem?.net || 0);
  // Translate missing odds instead of leaking a null or internal marker.
  const odds = roundItem?.odds ? `${formatNumber(roundItem.odds)}:1` : text('summary.notAvailable');
  // Translate the spread marker or ready-table state.
  const spread = roundItem?.spread ? text('stage.spread', { spread: formatNumber(roundItem.spread) }) : text('stage.noRound');
  // Return the fixed stage with all three card slots and two stable summary rows.
  return `<section class="rd-panel rd-stage" data-testid="red-dog-table" aria-label="${safe(text('stage.region'))}"><div class="rd-stage-head"><div><p class="rd-muted">${safe(roundItem?.third_card ? text('stage.thirdCard') : roundItem?.phase === 'raise_decision' ? text('stage.thirdWaiting') : text('stage.noRound'))}</p><h2>${safe(outcomeLabel(roundItem))}</h2></div><strong class="rd-spread">${safe(spread)}</strong></div><div class="rd-cards">${cardSlot('stage.firstCard', roundItem?.first_card)}${cardSlot('stage.thirdCard', roundItem?.third_card)}${cardSlot('stage.secondCard', roundItem?.second_card)}</div><div class="rd-summary"><div class="rd-stat"><span>${safe(text('summary.ante'))}</span><strong>${safe(tokenAmount(wager))}</strong></div><div class="rd-stat"><span>${safe(text('summary.raise'))}</span><strong>${safe(tokenAmount(raiseWager))}</strong></div><div class="rd-stat"><span>${safe(text('summary.total'))}</span><strong>${safe(tokenAmount(totalWager))}</strong></div><div class="rd-stat"><span>${safe(text('summary.odds'))}</span><strong>${safe(odds)}</strong></div><div class="rd-stat"><span>${safe(text('summary.payout'))}</span><strong>${safe(tokenAmount(payout))}</strong></div><div class="rd-stat"><span>${safe(text('summary.net'))}</span><strong>${safe(tokenAmount(net))}</strong></div></div></section>`;
}

// Render the regulated spread and pair payout schedule.
function paytableHtml() {
  // Define owned resource suffixes so every row remains localized.
  const rows = [['spread1', 'value1'], ['spread2', 'value2'], ['spread3', 'value3'], ['spread4', 'value4'], ['threeKind', 'valueThreeKind']];
  // Build semantic rows with scope attributes for screen-reader navigation.
  const body = rows.map(([spreadKey, valueKey]) => `<tr><th scope="row">${safe(text(`paytable.${spreadKey}`))}</th><td>${safe(text(`paytable.${valueKey}`))}</td></tr>`).join('');
  // Return one compact table above the bounded history list.
  return `<section><h2>${safe(text('paytable.title'))}</h2><table class="rd-paytable" aria-label="${safe(text('paytable.title'))}"><thead><tr><th scope="col">${safe(text('paytable.spread'))}</th><th scope="col">${safe(text('paytable.odds'))}</th></tr></thead><tbody>${body}</tbody></table></section>`;
}

// Render bounded reload-safe history and shoe telemetry in one data rail.
function dataHtml() {
  // Read retained rounds in the newest-first API order.
  const rounds = state?.rounds || [];
  // Build localized history rows without raw phase, outcome, or round identifiers.
  const rows = rounds.map(roundItem => `<article class="rd-history-row"><div><strong>${safe(outcomeLabel(roundItem))}</strong><span class="rd-history-wager">${safe(tokenAmount(roundItem.total_wager))}</span></div><span>${safe(tokenAmount(roundItem.payout))}</span></article>`).join('');
  // Return one intentional keyboard-focusable scroll surface for paytable and history.
  return `<aside class="rd-panel rd-data" aria-label="${safe(text('history.region'))}"><div class="rd-summary"><div class="rd-stat"><span>${safe(text('history.cards'))}</span><strong>${safe(formatNumber(state?.shoe_count || 0))}</strong></div><div class="rd-stat"><span>${safe(text('history.shoes'))}</span><strong>${safe(formatNumber(state?.shoes_dealt || 0))}</strong></div></div><div class="rd-data-scroll" tabindex="0" aria-label="${safe(text('history.region'))}">${paytableHtml()}<section><h2>${safe(text('history.title'))}</h2><div class="rd-history-list" aria-label="${safe(text('history.list'))}">${rows || `<p class="rd-muted">${safe(text('history.empty'))}</p>`}</div></section></div></aside>`;
}

// Replace the mounted view while preserving API state and retry identifiers.
function render() {
  // Ignore late asynchronous work after route unmount.
  if (!root) return;
  // Read one current round so every panel renders the same state snapshot.
  const roundItem = currentRound();
  // Render the localized title, live phase, and responsive three-zone hierarchy.
  root.innerHTML = `${styleHtml()}<main class="red-dog"><header class="rd-header"><div><p class="rd-muted">${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="rd-phase" role="status" aria-live="polite">${safe(phaseLabel(roundItem))}</span></header><div class="rd-layout">${controlsHtml(roundItem)}${stageHtml(roundItem)}${dataHtml()}</div></main>`;
  // Bind controls created by the latest safe markup replacement.
  bindEvents();
}

// Execute one replay-safe command while retaining its id after uncertain failure.
async function runCommand(commandKey, path, body) {
  // Ignore duplicate clicks while one atomic command is in flight.
  if (busy) return;
  // Capture the mount so a late response cannot populate a later route.
  const commandRoot = root;
  // Lock controls before starting network work.
  busy = true;
  // Reflect the localized busy state without starting a timer.
  render();
  // Submit the command and retain the id only when success is unknown.
  try {
    // Send no caller player identifier; the authenticated router owns identity.
    const payload = await post(path, { ...body, action_id: actionIdFor(commandKey) });
    // Remove the retry id only after the API confirms this command.
    retryActionIds.delete(commandKey);
    // Ignore state assignment when this mount was replaced during the request.
    if (root !== commandRoot) return;
    // Store the returned session-scoped state.
    state = payload.state;
    // Refresh the shell wallet after any ledger debit, refund, or payout.
    await refreshBalance();
  // Replace server English or transport diagnostics with owned localized copy.
  } catch (_) {
    // Show one stable localized failure while keeping the command id for retry.
    toast(text('errors.action'));
  // Always release the visual click lock for the surviving mount.
  } finally {
    // Clear the lock only when this command still belongs to the current mount.
    if (root === commandRoot) busy = false;
    // Render preserved or updated state without any delayed callback.
    render();
  }
}

// Deal one new opening through the replay-safe public route.
async function deal() {
  // Read the selected wager before the busy render disables the control.
  const wager = Number(root?.querySelector('[data-testid="red-dog-wager"]')?.value || WAGERS[0]);
  // Scope the retained action id to both the command and its money payload.
  const commandKey = `deal:${wager}`;
  // Submit only wager and idempotency data; session identity is implicit.
  await runCommand(commandKey, `${API_ROOT}/rounds`, { wager });
}

// Complete one spread decision with or without a matching raise.
async function decide(decision) {
  // Read the current actionable round before disabling controls.
  const roundItem = currentRound();
  // Ignore stale controls after settlement or route changes.
  if (!roundItem || roundItem.phase !== 'raise_decision') return;
  // Scope the retained id to this round and exact decision.
  const commandKey = `${roundItem.round_id}:${decision}`;
  // Submit the decision without a caller-controlled player identifier.
  await runCommand(commandKey, `${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/${decision}`, {});
}

// Bind semantic controls created by the latest render.
function bindEvents() {
  // Bind the opening action when the table is not awaiting a decision.
  root?.querySelector('[data-action="deal"]')?.addEventListener('click', deal);
  // Bind call to the public no-raise decision endpoint.
  root?.querySelector('[data-action="call"]')?.addEventListener('click', () => decide('call'));
  // Bind raise to the matching-wager decision endpoint.
  root?.querySelector('[data-action="raise"]')?.addEventListener('click', () => decide('raise'));
}

// Export the catalog-loadable game contract expected by the shared integration lane.
export const RedDogGame = {
  // Identify the module consistently with its proposed descriptor.
  id: 'red_dog',
  // Mount session-scoped state without touching shared shell registration.
  async mount(node) {
    // Retain the shell-provided mount node before asynchronous loading.
    root = node;
    // Install shared card presentation exactly once for this route.
    ensureSharedCardStyles();
    // Load active and fallback Red Dog dictionaries before rendering copy.
    await loadI18nDomain(DOMAIN);
    // Stop when this route was replaced while locale resources loaded.
    if (root !== node) return;
    // Rerender strings in place on locale changes without discarding game state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read and recover authenticated player state without a player query override.
    const payload = await api(`${API_ROOT}/state`);
    // Stop when this route was replaced while state loaded.
    if (root !== node) return;
    // Store the public state for initial rendering.
    state = payload.state;
    // Render only after localized copy and recovered state are both ready.
    render();
    // Align the shared wallet with any recovered ledger movement.
    await refreshBalance();
  },
  // Release every game-owned resource when the shell changes route.
  unmount() {
    // Remove the locale callback before releasing the DOM node.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference for a future mount.
    unsubscribeLocale = null;
    // Remove only the shared stylesheet link created by this mount.
    if (ownedCardStyleLink?.isConnected) ownedCardStyleLink.remove();
    // Clear stylesheet ownership for a future route.
    ownedCardStyleLink = null;
    // Clear uncertain retry keys; reload recovery reads authoritative server state.
    retryActionIds.clear();
    // Replace the map so late references cannot affect a future mount.
    retryActionIds = new Map();
    // Clear state so another authenticated user cannot reuse prior data.
    state = null;
    // Release the DOM reference; this module owns no timers to cancel.
    root = null;
    // Release the in-flight visual lock for a future mount.
    busy = false;
  },
};
