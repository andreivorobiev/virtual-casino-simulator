// Provide the catalog-integrated Let It Ride browser module for GitHub issue #134.
// Requirements: CARD-002, CORE-008, I18N-001, I18N-002, UX-001, UX-002, UX-003, UX-006, and LIR-004.

// Import the standard authenticated API helpers used by lazy game modules.
import { api, post } from '../core/api.js';
// Import safe markup, localized error presentation, and shared wallet refresh support.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the merged accessible card primitive instead of creating game-owned cards.
import { renderCard } from '../core/cards.js';
// Import locale loading, number formatting, lookup, and live-switch subscriptions.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Address every additive Let It Ride route from one stable API root.
const API_ROOT = '/api/v1/games/let-it-ride';
// Address the paired game-owned EN/RU resource domain.
const DOMAIN = 'games/let_it_ride';
// Identify the shared card stylesheet so only one link is installed.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Offer bounded base-wager choices without embedding visible labels in JavaScript.
const WAGERS = [5, 25, 100, 500];
// Keep paytable display order independent of object insertion behavior.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'pair_of_tens_or_better'];

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

// Read one localized Let It Ride string after the game domain has loaded.
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
  // Use the localized placeholder label before a card is visible.
  if (!card) return text('card.waiting');
  // Resolve rank and suit names without inheriting CARD-002 English labels.
  return text('card.label', { rank: text(`rank.${card.rank}`), suit: text(`suit.${card.suit}`) });
}

// Render one shared card primitive with game-owned EN/RU accessibility copy.
function localizedCard(card) {
  // Reserve a labeled card slot before the API exposes a card.
  if (!card) return `<div class="lir-card-empty" role="img" aria-label="${safe(cardLabel(null))}"></div>`;
  // Render the validated card through the merged primitive.
  const markup = renderCard(card.code || card);
  // Replace the primitive's default English label with the active game locale.
  return markup.replace(/aria-label="[^"]*"/, `aria-label="${safe(cardLabel(card))}"`);
}

// Return scoped layout rules that keep the card stage visually dominant.
function styleHtml() {
  // Define desktop hierarchy, accessible scroll treatment, and stable reserved regions.
  const desktop = '.let-it-ride{display:grid;gap:14px;min-width:0;min-height:0}.let-it-ride *{box-sizing:border-box;max-width:100%}.lir-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.lir-header h1,.lir-panel h2,.lir-panel h3{margin:0}.lir-phase{min-height:34px;padding:7px 12px;border:1px solid rgba(255,215,128,.45);border-radius:999px;color:var(--gold,#f6d47a)}.lir-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(520px,2.3fr) minmax(230px,.78fr);gap:14px;min-width:0}.lir-panel{min-width:0;border:1px solid rgba(255,215,128,.24);border-radius:16px;background:rgba(5,32,23,.9);padding:16px}.lir-controls,.lir-data{display:grid;align-content:start;gap:14px}.lir-controls label{display:grid;gap:7px}.lir-controls select,.lir-controls button{min-height:44px}.lir-action-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.lir-primary{background:var(--red,#a92a38);color:#fff}.lir-stage{display:grid;grid-template-rows:auto minmax(300px,1fr) auto;gap:18px;background:radial-gradient(circle at 50% 38%,rgba(28,112,78,.38),rgba(3,24,17,.96) 70%)}.lir-stage-head{display:flex;align-items:start;justify-content:space-between;gap:12px;min-height:58px}.lir-stage-head p{margin:0}.lir-units{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;min-width:180px}.lir-unit{padding:9px;border:1px solid rgba(255,255,255,.14);border-radius:10px;text-align:center}.lir-unit--withdrawn{opacity:.65}.lir-cards{display:grid;gap:18px;align-content:center}.lir-card-row{display:flex;justify-content:center;flex-wrap:wrap;gap:clamp(10px,2vw,22px)}.lir-card-slot{display:grid;justify-items:center;align-content:center;gap:10px;min-width:0}.lir-card-slot h3{font-size:.9rem;text-align:center}.lir-card-empty{width:clamp(3.25rem,8vw,6.5rem);aspect-ratio:5/7;border:2px dashed rgba(255,255,255,.26);border-radius:.65rem}.lir-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;min-height:76px}.lir-stat{min-width:0;padding:10px;border-radius:10px;background:rgba(0,0,0,.2)}.lir-stat span,.lir-history-wager{display:block;color:var(--muted,#b8c7c0);font-size:.78rem}.lir-stat strong{overflow-wrap:anywhere}.lir-data-scroll{display:grid;gap:14px;max-height:475px;overflow:auto;overscroll-behavior:contain;scrollbar-width:thin;touch-action:pan-y}.lir-data-scroll:focus-visible{outline:3px solid var(--gold,#f6d47a);outline-offset:3px}.lir-paytable{width:100%;border-collapse:collapse;table-layout:fixed}.lir-paytable th,.lir-paytable td{padding:7px 5px;border-bottom:1px solid rgba(255,255,255,.1);text-align:left;overflow-wrap:anywhere}.lir-history-list{display:grid;gap:9px;min-width:0}.lir-history-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px;min-width:0;padding:10px;border-radius:10px;background:rgba(0,0,0,.18)}.lir-history-row>*{min-width:0;overflow-wrap:anywhere}.lir-rules{margin:0;padding-left:1.1rem}.lir-rules li+li{margin-top:8px}.lir-muted{color:var(--muted,#b8c7c0)}.lir-busy{min-height:22px}';
  // Stack controls, stage, and data for tablet-width interaction.
  const tablet = '@media (max-width:1100px){.lir-layout{grid-template-columns:1fr}.lir-controls{order:1}.lir-stage{order:2}.lir-data{order:3}.lir-stage{grid-template-rows:auto minmax(260px,1fr) auto}.lir-data-scroll{max-height:none;overflow:visible}}';
  // Prevent clipped controls, cards, and summaries on the mobile viewport.
  const mobile = '@media (max-width:520px){.lir-header,.lir-stage-head{align-items:start;flex-direction:column}.lir-panel{padding:13px}.lir-action-grid,.lir-summary,.lir-units,.lir-history-row{grid-template-columns:1fr}.lir-units{width:100%;min-width:0}.lir-stage{grid-template-rows:auto minmax(230px,1fr) auto}.lir-card-slot h3{font-size:.78rem}}';
  // Remove decorative motion whenever the platform requests reduced motion.
  const reducedMotion = '@media (prefers-reduced-motion:reduce){.let-it-ride *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}';
  // Return one game-scoped stylesheet without changing shared shell CSS.
  return `<style>${desktop}${tablet}${mobile}${reducedMotion}</style>`;
}

// Render the control rail for ready, first decision, second decision, and settled phases.
function controlsHtml(roundItem) {
  // Detect the active decision phase, if any.
  const decisionStage = roundItem?.phase === 'first_decision' ? 'first' : roundItem?.phase === 'second_decision' ? 'second' : null;
  // Build localized wager options without hard-coded visible units.
  const options = WAGERS.map(value => `<option value="${value}">${safe(tokenAmount(value))}</option>`).join('');
  // Render decision actions only while an eligible wager can be pulled back.
  const decisionActions = decisionStage ? `<div class="lir-action-grid"><button type="button" data-decision="pull" data-stage="${decisionStage}" ${busy ? 'disabled' : ''}>${safe(text('controls.pull'))}</button><button type="button" class="lir-primary" data-decision="ride" data-stage="${decisionStage}" ${busy ? 'disabled' : ''}>${safe(text('controls.ride'))}</button></div>` : '';
  // Render a new deal action when no round is awaiting decisions.
  const dealAction = decisionStage ? '' : `<button type="button" class="lir-primary" data-action="deal" ${busy ? 'disabled' : ''}>${safe(roundItem ? text('controls.dealNext') : text('controls.deal'))}</button>`;
  // Return accessible controls and concise table rules above the rail fold.
  return `<section class="lir-panel lir-controls" aria-label="${safe(text('controls.region'))}"><h2>${safe(text('controls.title'))}</h2><label>${safe(text('controls.wager'))}<select data-testid="let-it-ride-wager" ${decisionStage || busy ? 'disabled' : ''}>${options}</select></label>${decisionActions}${dealAction}<p class="lir-muted">${safe(decisionStage ? text(`controls.${decisionStage}Help`) : text('controls.readyHelp'))}</p><p class="lir-muted lir-busy" role="status" aria-live="polite">${busy ? safe(text('controls.busy')) : ''}</p><h3>${safe(text('rules.title'))}</h3><ul class="lir-rules"><li>${safe(text('rules.threeWagers'))}</li><li>${safe(text('rules.firstDecision'))}</li><li>${safe(text('rules.secondDecision'))}</li><li>${safe(text('rules.qualifier'))}</li></ul></section>`;
}

// Render one labeled card slot using only localized accessible names.
function cardSlot(labelKey, card) {
  // Resolve the localized slot heading and group label.
  const label = text(labelKey);
  // Return a stable slot whose geometry does not change when the card arrives.
  return `<section class="lir-card-slot" aria-label="${safe(label)}"><h3>${safe(label)}</h3>${localizedCard(card)}</section>`;
}

// Render the three wager units and their current ride or withdrawn status.
function wagerUnits(roundItem) {
  // Read how many wager units have already been withdrawn.
  const withdrawn = Number(roundItem?.withdrawn_units || 0);
  // Render all three base wager positions with non-color status copy.
  return [0, 1, 2].map(index => {
    // Treat earliest units as withdrawn because pull order is deterministic.
    const pulled = index < withdrawn;
    // Return one compact wager-unit tile.
    return `<span class="lir-unit${pulled ? ' lir-unit--withdrawn' : ''}">${safe(text(pulled ? 'stage.withdrawnUnit' : 'stage.ridingUnit', { number: index + 1 }))}</span>`;
  }).join(''); // Combine all wager-unit tiles into one stable status group.
}

// Render the dominant five-card table and settlement summary.
function stageHtml(roundItem) {
  // Read numeric fields through zero-safe fallbacks for the ready state.
  const baseWager = Number(roundItem?.wager || 0);
  // Read original three-unit exposure.
  const totalInitial = Number(roundItem?.total_initial_wager || 0);
  // Read how many units remain riding.
  const activeUnits = Number(roundItem?.active_units || 0);
  // Read returned withdrawn stakes.
  const refund = Number(roundItem?.refund || 0);
  // Read final returned credit after settlement.
  const payout = Number(roundItem?.payout || 0);
  // Read final net result only when the round exposes it.
  const net = Number(roundItem?.net || 0);
  // Render the three player cards in one accessible row.
  const playerCards = (roundItem?.player_cards || [null, null, null]).map((card, index) => cardSlot(`stage.playerCard${index + 1}`, card)).join('');
  // Render the two community slots with hidden-card placeholders before reveal.
  const communityCards = (roundItem?.community_cards || [null, null]).map((card, index) => cardSlot(`stage.communityCard${index + 1}`, card)).join('');
  // Return the fixed stage with all card slots and stable summary rows.
  return `<section class="lir-panel lir-stage" data-testid="let-it-ride" aria-label="${safe(text('stage.region'))}"><div class="lir-stage-head"><div><p class="lir-muted">${safe(roundItem ? text('stage.roundActive') : text('stage.noRound'))}</p><h2>${safe(outcomeLabel(roundItem))}</h2></div><div class="lir-units" aria-label="${safe(text('stage.wagerUnits'))}">${wagerUnits(roundItem)}</div></div><div class="lir-cards"><div class="lir-card-row" aria-label="${safe(text('stage.playerCards'))}">${playerCards}</div><div class="lir-card-row" aria-label="${safe(text('stage.communityCards'))}">${communityCards}</div></div><div class="lir-summary"><div class="lir-stat"><span>${safe(text('summary.base'))}</span><strong>${safe(tokenAmount(baseWager))}</strong></div><div class="lir-stat"><span>${safe(text('summary.initial'))}</span><strong>${safe(tokenAmount(totalInitial))}</strong></div><div class="lir-stat"><span>${safe(text('summary.activeUnits'))}</span><strong>${safe(formatNumber(activeUnits))}</strong></div><div class="lir-stat"><span>${safe(text('summary.refund'))}</span><strong>${safe(tokenAmount(refund))}</strong></div><div class="lir-stat"><span>${safe(text('summary.payout'))}</span><strong>${safe(tokenAmount(payout))}</strong></div><div class="lir-stat"><span>${safe(text('summary.net'))}</span><strong>${safe(tokenAmount(net))}</strong></div></div></section>`;
}

// Render the Let It Ride qualifying-hand payout schedule.
function paytableHtml() {
  // Build semantic rows with scope attributes for screen-reader navigation.
  const body = PAYTABLE_ORDER.map(key => `<tr><th scope="row">${safe(text(`paytable.${key}`))}</th><td>${safe(text('paytable.multiplier', { value: formatNumber(state?.rules?.paytable?.[key] || 0) }))}</td></tr>`).join('');
  // Return one compact table above the bounded history list.
  return `<section><h2>${safe(text('paytable.title'))}</h2><table class="lir-paytable" aria-label="${safe(text('paytable.title'))}"><thead><tr><th scope="col">${safe(text('paytable.hand'))}</th><th scope="col">${safe(text('paytable.return'))}</th></tr></thead><tbody>${body}</tbody></table></section>`;
}

// Render bounded reload-safe history and shoe telemetry in one data rail.
function dataHtml() {
  // Read retained rounds in the newest-first API order.
  const rounds = state?.rounds || [];
  // Build localized history rows without raw phase, outcome, or round identifiers.
  const rows = rounds.map(roundItem => `<article class="lir-history-row"><div><strong>${safe(outcomeLabel(roundItem))}</strong><span class="lir-history-wager">${safe(text('history.riding', { count: formatNumber(roundItem.active_units) }))}</span></div><span>${safe(tokenAmount(roundItem.refund + roundItem.payout))}</span></article>`).join('');
  // Return one intentional keyboard-focusable scroll surface for paytable and history.
  return `<aside class="lir-panel lir-data" aria-label="${safe(text('history.region'))}"><div class="lir-summary"><div class="lir-stat"><span>${safe(text('history.cards'))}</span><strong>${safe(formatNumber(state?.shoe_count || 0))}</strong></div><div class="lir-stat"><span>${safe(text('history.shoes'))}</span><strong>${safe(formatNumber(state?.shoes_dealt || 0))}</strong></div></div><div class="lir-data-scroll" tabindex="0" aria-label="${safe(text('history.region'))}">${paytableHtml()}<section><h2>${safe(text('history.title'))}</h2><div class="lir-history-list" aria-label="${safe(text('history.list'))}">${rows || `<p class="lir-muted">${safe(text('history.empty'))}</p>`}</div></section></div></aside>`;
}

// Replace the mounted view while preserving API state and retry identifiers.
function render() {
  // Ignore late asynchronous work after route unmount.
  if (!root) return;
  // Read one current round so every panel renders the same state snapshot.
  const roundItem = currentRound();
  // Render the localized title, live phase, and responsive three-zone hierarchy.
  root.innerHTML = `${styleHtml()}<main class="let-it-ride"><header class="lir-header"><div><p class="lir-muted">${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="lir-phase" role="status" aria-live="polite">${safe(phaseLabel(roundItem))}</span></header><div class="lir-layout">${controlsHtml(roundItem)}${stageHtml(roundItem)}${dataHtml()}</div></main>`;
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
    // Send no caller-controlled identity; the authenticated router owns identity.
    const payload = await post(path, { ...body, action_id: actionIdFor(commandKey) });
    // Remove the retry id only after the API confirms this command.
    retryActionIds.delete(commandKey);
    // Ignore state assignment when this mount was replaced during the request.
    if (root !== commandRoot) return;
    // Store the returned session-scoped state.
    state = payload.state;
    // Refresh the shell wallet after any ledger debit, refund, or payout.
    await refreshBalance();
  // Replace transport diagnostics with owned localized copy.
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
  // Read the selected base wager before the busy render disables the control.
  const wager = Number(root?.querySelector('[data-testid="let-it-ride-wager"]')?.value || WAGERS[0]);
  // Scope the retained action id to both the command and its money payload.
  const commandKey = `deal:${wager}`;
  // Submit only wager and idempotency data; session identity is implicit.
  await runCommand(commandKey, `${API_ROOT}/rounds`, { wager });
}

// Complete one staged ride-or-pull decision.
async function decide(stage, decision) {
  // Read the current actionable round before disabling controls.
  const roundItem = currentRound();
  // Ignore stale controls after settlement or route changes.
  if (!roundItem || !['first_decision', 'second_decision'].includes(roundItem.phase)) return;
  // Scope the retained id to this round, stage, and exact decision.
  const commandKey = `${roundItem.round_id}:${stage}:${decision}`;
  // Submit the decision without a caller-controlled identity.
  await runCommand(commandKey, `${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/${stage}-decision`, { decision });
}

// Bind semantic controls created by the latest render.
function bindEvents() {
  // Bind the opening action when the table is not awaiting a decision.
  root?.querySelector('[data-action="deal"]')?.addEventListener('click', deal);
  // Bind both ride and pull buttons for the active decision stage.
  root?.querySelectorAll('[data-decision]').forEach(button => {
    // Submit the selected staged decision through the public API.
    button.addEventListener('click', () => decide(button.dataset.stage, button.dataset.decision));
  });
}

// Export the catalog-loadable game contract expected by the shared integration lane.
export const LetItRideGame = {
  // Identify the module consistently with its canonical descriptor.
  id: 'let_it_ride',
  // Mount session-scoped state through catalog-owned shell registration.
  async mount(node) {
    // Retain the shell-provided mount node before asynchronous loading.
    root = node;
    // Install shared card presentation exactly once for this route.
    ensureSharedCardStyles();
    // Load active and fallback Let It Ride dictionaries before rendering copy.
    await loadI18nDomain(DOMAIN);
    // Stop when this route was replaced while locale resources loaded.
    if (root !== node) return;
    // Rerender strings in place on locale changes without discarding game state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read and recover authenticated player state without a compatibility override.
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
