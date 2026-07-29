// Implement the isolated Over/Under 7 route for GitHub issue #135.
// Import standard API helpers so requests use the shared envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared #97 motion scope so dice reveal timers are route-owned.
import { createMotionTimerScope } from '../core/motion.js';
// Import game-domain localization and locale-change helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/over_under_7';
// Store the route-local style id so remounts never duplicate CSS.
const STYLE_ID = 'over-under-7-styles';
// Store the decorative dice reveal duration.
export const ROLL_DURATION_MS = 900;
// Store stable wager targets in the same order as the backend.
export const OUTCOME_IDS = Object.freeze(['under', 'seven', 'over']);
// Define compact game-owned styles without touching shared CSS.
const ROUTE_CSS = [
  '.over-under-7{display:grid;gap:12px;min-height:100%;color:var(--text,#f5ead6);}', // Establish a stable route-local surface.
  '.ou7-header{display:flex;align-items:end;justify-content:space-between;gap:16px;padding:4px 2px;}', // Keep title and phase compact.
  '.ou7-header h1{margin:0;color:var(--gold,#f2c55c);font-size:clamp(30px,4vw,52px);}', // Make the game title the first visual level.
  '.ou7-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;background:var(--panel-strong);}', // Reserve a concise phase chip.
  '.ou7-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(420px,1.8fr) minmax(220px,.72fr);gap:14px;min-height:0;}', // Keep dice stage visually dominant.
  '.ou7-panel{padding:16px;border:1px solid var(--gold);border-radius:18px;background:var(--panel-strong);}', // Separate controls, stage, and data.
  '.ou7-controls{display:grid;align-content:start;gap:12px;}', // Keep wager actions in one rail.
  '.ou7-bet{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:8px;align-items:center;}', // Align labels and wager amounts.
  '.ou7-bet input{min-height:44px;min-width:0;}', // Preserve keyboard and touch target size.
  '.ou7-play{min-height:46px;border:0;border-radius:12px;color:white;background:#a71922;font-weight:800;}', // Use shared red primary-action convention.
  '.ou7-play:disabled{opacity:.58;cursor:not-allowed;}', // Keep unavailable action state readable.
  '.ou7-repeat{min-height:46px;border:1px solid var(--gold);border-radius:12px;background:transparent;color:var(--gold);font-weight:700;}', // Offer a secondary one-click repeat action.
  '.ou7-repeat:disabled{opacity:.5;cursor:not-allowed;}', // Keep the repeat action state readable.
  '.ou7-stage{display:grid;grid-template-rows:auto minmax(0,1fr) auto;place-items:center;gap:16px;overflow:hidden;}', // Reserve a stable dice stage.
  '.ou7-dice{display:flex;align-items:center;justify-content:center;gap:18px;width:100%;min-height:240px;}', // Keep dice central and stable.
  '.ou7-die{display:grid;place-items:center;width:min(30vw,150px);aspect-ratio:1;border:3px solid #f0cf74;border-radius:18px;background:linear-gradient(145deg,#f9f1d5,#d7ba70);color:#10271d;font-size:clamp(44px,8vw,84px);font-weight:1000;box-shadow:0 16px 36px rgba(0,0,0,.38);}', // Render reliable code-native dice.
  '.ou7-die.rolling{animation:ou7Roll .18s linear infinite;}', // Use transform-only decorative motion.
  '.ou7-result{display:grid;gap:4px;min-height:70px;text-align:center;}', // Reserve result space so layout does not shift.
  '.ou7-total{font-size:clamp(34px,6vw,64px);font-weight:1000;color:var(--text);}', // Emphasize the rolled total.
  '.ou7-data{display:grid;align-content:start;gap:12px;}', // Keep paytable and history distinct.
  '.ou7-payrow,.ou7-history-row{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.08);}', // Align compact rows.
  '.ou7-history{max-height:260px;overflow:auto;scrollbar-width:thin;}', // Give data rail one focusable scroll region.
  '.ou7-error{min-height:20px;color:#ffb9b9;}', // Reserve validation and API feedback.
  '@keyframes ou7Roll{from{transform:translateY(-3px) rotate(-2deg)}to{transform:translateY(3px) rotate(2deg)}}', // Keep dice motion decorative and transform-only.
  '@media(max-width:1200px){.ou7-layout{grid-template-columns:1fr}.ou7-controls{order:1}.ou7-stage{order:2}.ou7-data{order:3}.ou7-dice{min-height:210px}}', // Stack control, stage, then data.
  '@media(max-width:560px){.ou7-header{align-items:start;flex-direction:column}.ou7-panel{padding:12px}.ou7-bet{grid-template-columns:minmax(0,1fr) 84px}.ou7-die{border-radius:14px}.ou7-dice{gap:10px;min-height:170px}}', // Preserve mobile containment.
  '@media(prefers-reduced-motion:reduce){.over-under-7 *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}', // Respect platform reduced motion.
].join(''); // Combine CSS chunks into one injected payload.

// Store the current route outlet while mounted.
let root = null;
// Store the latest backend state payload.
let gameState = { rules: { paytable: [] }, state: { recent_rounds: [] } };
// Store locally edited wagers before submission.
let wagers = {};
// Store the latest settled round for the stage.
let latestRound = null;
// Store whether an action request or reveal is active.
let playPending = false;
// Store the last committed wager map so one click can repeat the same bet.
let lastBet = null;
// Store the current player-facing phase key.
let phase = 'phase.ready';
// Store the disposable timer scope for this mount.
let motionScope = null;
// Store whether the current reveal used reduced motion.
let reducedMotionActive = false;
// Store the locale subscription cleanup callback.
let localeUnsubscribe = null;

// Resolve one game-owned string from the active locale.
const tx = (key, params = {}) => t(key, params, GAME_DOMAIN);
// Escape one localized string before markup insertion.
const text = (key, params = {}) => safe(tx(key, params));

// Create one retry-safe client action identity.
export function createActionId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require a secure UUID provider so accidental duplicate submissions do not collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Over/Under 7 plays');
  // Prefix the UUID for readable action diagnostics without player data.
  return `ou7-${randomUUID()}`;
}

// Retain one unresolved idempotency identity across an ambiguous request failure. (issue #261)
let pendingRequestId = null;
// Retain the exact immutable wager payload paired with the unresolved identity so a retry cannot resend a different body. (issue #261)
let pendingPayload = null;
// Retain the authenticated player that owned the unresolved identity so a later session cannot inherit it. (issue #261)
let pendingPlayerId = null;

// Read the authenticated player id from the shared shell session without trusting caller-controlled fields.
function sessionPlayerId() {
  // Return the current-user player id published by the shell, or null before authentication resolves.
  return globalThis.CasinoCurrentUser?.player?.player_id || null;
}

// Return a stable canonical signature for one wager map so changed intent is detectable.
function wagerSignature(source = {}) {
  // Sort keys so equivalent wager maps always produce one identical signature.
  return JSON.stringify(Object.keys(source || {}).sort().map(key => [key, source[key]]));
}

// Report whether a structured API error definitively resolves the pending action so it is safe to discard.
function isDefinitiveRejection(error) {
  // Treat validation, balance, auth, route, and conflict errors as non-ambiguous server responses.
  return ['VALIDATION_ERROR', 'INSUFFICIENT_FUNDS', 'UNAUTHORIZED', 'FORBIDDEN', 'NOT_FOUND', 'CONFLICT'].includes(error?.code);
}

// Clear the unresolved request only after the backend proves its outcome or ownership changes.
function clearPendingRequest() {
  // Release the browser action identity.
  pendingRequestId = null;
  // Release the immutable wager snapshot.
  pendingPayload = null;
  // Release the authenticated owner paired with the action.
  pendingPlayerId = null;
}

// Resolve the idempotency payload for one play, reusing the retained identity only for the identical player and wagers. (issue #261)
function resolvePlayPayload(wagerMap) {
  // Read the authenticated player that would own this action.
  const playerId = sessionPlayerId();
  // Reuse the frozen identity only when the same player resubmits the exact same immutable wager map after an ambiguous failure.
  if (pendingPayload && pendingPlayerId && pendingPlayerId === playerId && wagerSignature(pendingPayload.wagers) === wagerSignature(wagerMap)) {
    // Return the retained frozen payload for a safe exactly-once replay.
    return pendingPayload;
  }
  // Mint a fresh identity for a new intent before any network work.
  pendingRequestId = createActionId();
  // Bind the authenticated owner so a later session cannot inherit this identity.
  pendingPlayerId = playerId;
  // Freeze the exact request body so a retry can never resend a different wager map.
  pendingPayload = Object.freeze({ action_id: pendingRequestId, wagers: Object.freeze({ ...wagerMap }) });
  // Return the frozen payload for the request.
  return pendingPayload;
}

// Reconcile an unresolved identity against authoritative history and current ownership. (issue #261)
function reconcilePendingRequest() {
  // Read only authoritative recent settlements echoed with their action id from the current state payload.
  const recentRounds = gameState.state?.recent_rounds || [];
  // Clear a pending identity already proven settled by server history.
  if (pendingRequestId && recentRounds.some(round => round?.action_id === pendingRequestId)) {
    // Treat authoritative reconciliation as acknowledgement of the committed play.
    clearPendingRequest();
    // Stop after clearing the resolved identity.
    return;
  }
  // Clear a pending identity that belongs to a different authenticated player in this tab.
  if (pendingPlayerId && sessionPlayerId() && pendingPlayerId !== sessionPlayerId()) {
    // Remove cross-session retry ownership without resending it.
    clearPendingRequest();
  }
}

// Return the wager map currently in effect, locking to the immutable pending snapshot after an ambiguous failure. (issue #261)
function activeWagers() {
  // Prefer the frozen pending payload so a retry cannot submit a changed intent under the same identity.
  return pendingPayload?.wagers || wagers;
}

// Schedule dice settlement through a lifecycle-owned motion scope.
export function scheduleDiceReveal({ timerScope, onSettled, duration = ROLL_DURATION_MS }) {
  // Require the shared timer-scope interface.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require an explicit callback owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Schedule through the route scope so unmount and reduced motion are honored.
  return timerScope.schedule(onSettled, duration);
}

// Install the game-owned style block once per document.
function ensureStyles() {
  // Reuse an existing style node on remount.
  if (document.getElementById(STYLE_ID)) return;
  // Create a style node through DOM APIs.
  const style = document.createElement('style');
  // Assign the stable node id.
  style.id = STYLE_ID;
  // Apply the route-local CSS.
  style.textContent = ROUTE_CSS;
  // Attach before first route paint.
  document.head.append(style);
}

// Format play-token amounts without currency symbols.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale at ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit.
  return translate('units.playTokens', { amount: number });
}

// Return localized wager controls.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend paytable metadata.
  return (gameState.rules?.paytable || []).map(row => `<label class="ou7-bet"><span>${safe(translate(`outcome.${row.id}`))} <small>${safe(translate('odds.net', { odds: row.net_odds }))}</small></span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(row.id)}" value="${safe(activeWagers()[row.id] || '')}" aria-label="${safe(translate('wager.input', { outcome: translate(`outcome.${row.id}`) }))}"></label>`).join('');
}

// Return localized paytable disclosure rows.
function paytableHtml(translate = tx) {
  // Show winning totals and net odds so the wager list and return table use one convention. (issue #255)
  return (gameState.rules?.paytable || []).map(row => `<div class="ou7-payrow"><span>${safe(translate(`outcome.${row.id}`))}</span><span>${safe(translate('paytable.row', { totals: row.winning_totals.join(', '), odds: row.net_odds }))}</span></div>`).join('');
}

// Return bounded recent-round history.
function historyHtml(translate = tx) {
  // Read newest results first for the data rail.
  const rows = [...(gameState.state?.recent_rounds || [])].reverse();
  // Return a localized empty state before the first play.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render one compact row per settled play.
  return rows.map(round => `<div class="ou7-history-row"><span>${safe(translate('history.roll', { total: round.total, dice: round.dice.join(' + ') }))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return one die pip or placeholder.
function dieValue(index) {
  // Use the authoritative latest round when present.
  if (latestRound?.dice?.[index]) return latestRound.dice[index];
  // Use a neutral placeholder before the first roll.
  return '–';
}

// Return the complete route markup.
export function viewMarkup({ translate = tx } = {}) {
  // Escape localized text through an injected translator for tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Resolve the latest outcome label or waiting copy.
  const outcome = latestRound ? translated(`outcome.${latestRound.outcome}`) : translated('result.waiting');
  // Resolve the result detail without creating fake totals.
  const detail = latestRound ? translated('result.detail', { total: latestRound.total, net: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Enable the one-click repeat only when a prior committed bet exists and no request or retry is active.
  const repeatDisabled = playPending || Boolean(pendingRequestId) || !lastBet;
  // Return the governed three-zone layout.
  return `<section class="over-under-7" data-testid="over-under-7"><header class="ou7-header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="ou7-phase" data-testid="over-under-7-phase">${translated(phase)}</span></header><div class="ou7-layout"><section class="ou7-panel ou7-controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="ou7-play" data-play type="button"${playPending ? ' disabled' : ''}>${translated(playPending ? 'action.rolling' : 'action.play')}</button><button class="ou7-repeat" data-action="repeat" type="button"${repeatDisabled ? ' disabled' : ''}>${translated('controls.repeat')}</button><p class="ou7-error" data-error aria-live="polite"></p></section><section class="ou7-panel ou7-stage" aria-label="${translated('stage.aria')}"><div class="ou7-dice" aria-label="${translated('stage.diceAria')}"><span class="ou7-die${playPending && !reducedMotionActive ? ' rolling' : ''}" data-testid="ou7-die-1">${safe(dieValue(0))}</span><span class="ou7-die${playPending && !reducedMotionActive ? ' rolling' : ''}" data-testid="ou7-die-2">${safe(dieValue(1))}</span></div><div class="ou7-result" aria-live="polite"><strong class="ou7-total">${latestRound ? safe(latestRound.total) : translated('result.totalPlaceholder')}</strong><span>${outcome}</span><span>${detail}</span></div></section><aside class="ou7-panel ou7-data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="ou7-history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
}

// Render the route and reconnect inputs after DOM replacement.
function render() {
  // Ignore late renders after route teardown.
  if (!root) return;
  // Replace route markup atomically.
  root.innerHTML = viewMarkup();
  // Wire each wager input into local unsent state.
  root.querySelectorAll('[data-wager]').forEach(input => { input.oninput = () => { const amount = Number(input.value); if (Number.isFinite(amount) && amount > 0) wagers[input.dataset.wager] = amount; else delete wagers[input.dataset.wager]; }; });
  // Wire the one atomic play action.
  root.querySelector('[data-play]').onclick = play;
  // Wire the one-click repeat that re-fires the previous wager map.
  root.querySelector('[data-action="repeat"]').onclick = repeat;
}

// Re-apply the last committed wager map and re-fire one roll without a timer.
async function repeat() {
  // Ignore repeat while a request or reveal is active, holding an unresolved retry, or without a prior committed bet.
  if (playPending || pendingRequestId || !lastBet) return;
  // Restore the previous wager map into the local unsent controls.
  wagers = { ...lastBet.wagers };
  // Fire the shared exactly-once play action with the restored wagers.
  await play();
}

// Load session-bound state from the additive endpoint.
async function load() {
  // Fetch only the authenticated player's game state.
  gameState = await api('/api/v1/games/over-under-7/state');
  // Reconcile any unresolved retry identity against authoritative history and current ownership before rendering. (issue #261)
  reconcilePendingRequest();
  // Restore the latest result from player-owned history.
  latestRound = gameState.state?.recent_rounds?.length ? gameState.state.recent_rounds[gameState.state.recent_rounds.length - 1] : null;
  // Recover a repeatable wager map from the newest settled round so repeat survives a reload.
  if (latestRound?.wagers) lastBet = { wagers: { ...latestRound.wagers } };
  // Render after rules and history are available.
  render();
}

// Submit one complete wager map and present the settled result.
async function play() {
  // Ignore duplicate clicks while one action is active.
  if (playPending) return;
  // Require at least one positive wager before contacting the ledger endpoint.
  if (!Object.keys(activeWagers()).length) {
    // Show localized guidance in the reserved error region.
    root.querySelector('[data-error]').textContent = tx('error.wagerRequired');
    // Stop without creating an action identity.
    return;
  }
  // Guard controls before sending the atomic request.
  playPending = true;
  // Move the phase to player-facing roll language.
  phase = 'phase.rolling';
  // Cancel prior reveal callbacks.
  motionScope.cancelAll();
  // Detect reduced motion for CSS evidence.
  reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
  // Render the rolling state.
  render();
  // Capture current route ownership.
  const mountedRoot = root;
  // Capture current timer ownership.
  const activeScope = motionScope;
  // Protect API and reveal work.
  try {
    // Resolve the frozen idempotency payload so a retry replays the exact same identity and immutable body. (issue #261)
    const command = resolvePlayPayload(activeWagers());
    // Submit the retained action id with its frozen wager snapshot, never the live mutable controls.
    const response = await post('/api/v1/games/over-under-7/plays', { action_id: command.action_id, wagers: command.wagers });
    // Clear the retained identity only after the server has confirmed this play.
    clearPendingRequest();
    // Stop if navigation replaced the route.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Store the authoritative settled round.
    latestRound = response.round;
    // Remember the settled wager map so the next roll can repeat the same bet with one click.
    if (latestRound?.wagers) lastBet = { wagers: { ...latestRound.wagers } };
    // Schedule the final reveal through the shared motion primitive.
    scheduleDiceReveal({ timerScope: activeScope, onSettled: async () => { phase = 'phase.settled'; playPending = false; gameState = await api('/api/v1/games/over-under-7/state'); render(); await refreshBalance(); } });
    // Render dice values while the reveal timer owns phase completion.
    render();
  // Handle API failures with localized feedback.
  } catch (error) {
    // Ignore late failures after route teardown.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Discard the pending identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearPendingRequest();
    // Restore the ready phase.
    phase = 'phase.ready';
    // Re-enable controls.
    playPending = false;
    // Render before writing into the reserved error node.
    render();
    // Show localized failure copy.
    root.querySelector('[data-error]').textContent = tx('error.playFailed');
    // Also use shared feedback.
    toast(tx('error.playFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #77 integration.
export const OverUnder7Game = {
  // Expose the stable catalog identifier.
  id: 'over_under_7',
  // Mount the isolated route into the shared outlet.
  async mount(node) {
    // Store route ownership before async initialization.
    root = node;
    // Reset the repeatable bet so another session never inherits it before state loads.
    lastBet = null;
    // Install game-owned CSS.
    ensureStyles();
    // Create one lifecycle-bound timer scope.
    motionScope = createMotionTimerScope();
    // Load game-owned locale dictionaries before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint on locale changes without losing state.
    localeUnsubscribe = onLocaleChange(() => render());
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release timers and subscriptions on route exit.
  unmount() {
    // Cancel all pending dice reveal callbacks.
    motionScope?.dispose();
    // Clear the disposed scope reference.
    motionScope = null;
    // Remove the locale subscription.
    localeUnsubscribe?.();
    // Clear the subscription reference.
    localeUnsubscribe = null;
    // Clear route ownership for late async guards.
    root = null;
    // Reset in-flight state for the next mount.
    playPending = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
    // Release any unresolved retry identity so a later mount or a different session cannot inherit it; remount reloads authoritative state. (issue #261)
    clearPendingRequest();
  },
};
