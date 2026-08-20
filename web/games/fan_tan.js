// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the catalog-integrated Fan-Tan route for GitHub issue #137.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import the merged motion scope so every counting timer has lifecycle cleanup.
import { createMotionTimerScope } from '../core/motion.js';
// Import shared route, locale, style, and busy-state ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/fan_tan';
// Create the route controller with the external game stylesheet and established action prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'ft', stylesheet: { id: 'fan-tan-styles', href: '/games/fan_tan.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Store the decorative counting duration resolved through the shared motion scope.
export const COUNT_DURATION_MS = 900;
// Store the latest backend-owned state payload.
let gameState = { outcomes: [], state: { recent_rounds: [] }, rules: {} };
// Store locally edited wagers until one atomic round is submitted.
let wagers = {};
// Store the current player-facing phase key.
let phase = 'phase.ready';
// Store the latest settled round for the stage result.
let latestRound = null;
// Store the disposable timer scope owned by the current route mount.
let motionScope = null;
// Store whether the current count presentation used reduced motion.
let reducedMotionActive = false;
// Retain the last committed wager map so one click can repeat the same round.
let lastBet = null;
// Escape one localized string before inserting it into route markup.
const text = (key, params = {}) => safe(tx(key, params));

// Generate one retry-safe action identity using the browser cryptographic UUID provider.
export function createActionId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require cryptographic UUID support so accidental double-submission identities never collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Fan-Tan rounds');
  // Prefix the UUID for readable action diagnostics without including player information.
  return `ft-${randomUUID()}`;
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
    // Treat authoritative reconciliation as acknowledgement of the committed round.
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

// Schedule the counting reveal through a caller-owned reduced-motion timer scope.
export function scheduleCount({ timerScope, onSettled, duration = COUNT_DURATION_MS }) {
  // Require the shared timer-scope interface rather than allocating an unmanaged timer.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require a callback so animation completion has an explicit owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Schedule through the scope so route exit and reduced motion retain lifecycle semantics.
  return timerScope.schedule(onSettled, duration);
}

// Format a play-token amount without any real-money or currency symbol.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale while keeping two-decimal ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit owned by this game domain.
  return translate('units.playTokens', { amount: number });
}

// Return localized markup for every residue wager input.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend metadata while retaining stable residue ordering.
  return (gameState.outcomes || []).map(outcome => `<label class="fan-tan__bet"><span>${safe(translate('residue.label', { residue: outcome.residue }))} <small>${safe(translate('odds.net', { odds: outcome.net_odds }))}</small></span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(outcome.id)}" value="${safe(activeWagers()[outcome.id] || '')}" aria-label="${safe(translate('wager.input', { residue: outcome.residue }))}"></label>`).join('');
}

// Return localized paytable rows from the immutable backend catalog.
function paytableHtml(translate = tx) {
  // Show net odds and return multiplier so the simulator profile is explicit.
  return (gameState.outcomes || []).map(outcome => `<div class="fan-tan__payrow"><span>${safe(translate('residue.label', { residue: outcome.residue }))}</span><span>${safe(translate('paytable.row', { odds: outcome.net_odds, multiplier: outcome.return_multiplier }))}</span></div>`).join('');
}

// Return bounded recent-round rows with no nested controls.
function historyHtml(translate = tx) {
  // Read newest history first for the player-owned data rail.
  const rows = [...(gameState.state?.recent_rounds || [])].reverse();
  // Return the localized empty state until a real settlement exists.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render stable residue and net values for each settled round.
  return rows.map(round => `<div class="fan-tan__history-row"><span>${safe(translate('history.residue', { residue: round.residue }))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return code-native beans for the visible pile and final residue.
function beanHtml() {
  // Use a compact preview count so the stage remains dense at all viewports.
  const count = latestRound ? Math.min(latestRound.pile_count, 48) : 32;
  // Resolve the highlighted residue count only after a settlement exists.
  const residue = latestRound ? Number(latestRound.residue) : 0;
  // Render beans with the final visible residue markers highlighted.
  return Array.from({ length: count }, (_, index) => `<span class="fan-tan__bean" data-residue="${latestRound && index >= count - residue}" aria-hidden="true"></span>`).join('');
}

// Return the complete route markup using only localized visible strings.
export function viewMarkup({ translate = tx } = {}) {
  // Resolve and escape through an injected translator for deterministic locale tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Resolve the visible settled residue or a localized waiting label.
  const residueLabel = latestRound ? translated('result.residue', { residue: latestRound.residue }) : translated('result.waiting');
  // Resolve net result detail only when a backend settlement exists.
  const resultDetail = latestRound ? translated('result.net', { amount: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Enable the one-click repeat only when a prior wager map exists and no round or unresolved retry is active.
  const repeatDisabled = lifecycle.isBusy() || Boolean(pendingRequestId) || !lastBet;
  // Return a three-zone layout aligned with the visual-design standard.
  return `<section class="fan-tan" data-testid="fan-tan"><header class="fan-tan__header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="fan-tan__phase" data-testid="fan-tan-phase">${translated(phase)}</span></header><div class="fan-tan__layout"><section class="fan-tan__panel fan-tan__controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="fan-tan__play" data-play type="button"${lifecycle.isBusy() ? ' disabled' : ''}>${translated(lifecycle.isBusy() ? 'action.counting' : 'action.play')}</button><button type="button" class="fan-tan__repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${translated('controls.repeat')}</button><p class="fan-tan__error" data-error aria-live="polite"></p></section><section class="fan-tan__panel fan-tan__stage" aria-label="${translated('stage.aria')}"><div class="fan-tan__tray" data-reduced-motion="${reducedMotionActive}"><div class="fan-tan__beans">${beanHtml()}</div></div><div class="fan-tan__result" aria-live="polite"><strong>${residueLabel}</strong><span>${resultDetail}</span></div></section><aside class="fan-tan__panel fan-tan__data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="fan-tan__history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
}

// Render the route and reconnect its game-owned inputs after DOM replacement.
function render() {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Stop stale async callbacks after route unmount.
  if (!root) return;
  // Replace the isolated route atomically so phase and stage regions stay stable.
  root.innerHTML = viewMarkup();
  // Wire every wager input to local unsent state.
  root.querySelectorAll('[data-wager]').forEach(input => { input.oninput = () => { const amount = Number(input.value); if (Number.isFinite(amount) && amount > 0) wagers[input.dataset.wager] = amount; else delete wagers[input.dataset.wager]; }; });
  // Wire the one atomic play action.
  root.querySelector('[data-play]').onclick = play;
  // Wire the one-click repeat that re-fires the previous wager map.
  root.querySelector('[data-action="repeat"]').onclick = repeat;
}

// Re-apply the last committed wager map and re-fire one round without a timer.
async function repeat() {
  // Ignore repeat while counting, holding an unresolved retry, or without a prior wager map.
  if (lifecycle.isBusy() || pendingRequestId || !lastBet) return;
  // Restore the previous wager map into the local control state.
  wagers = { ...lastBet.wagers };
  // Fire the shared exactly-once play action with the restored wagers.
  await play();
}

// Return the wager map currently in effect, locking to the immutable pending snapshot after an ambiguous failure. (issue #261)
function activeWagers() {
  // Prefer the frozen pending payload so a retry cannot submit a changed intent under the same identity.
  return pendingPayload?.wagers || wagers;
}

// Load session-bound state from the additive v1 game endpoint.
async function load() {
  // Fetch only the authenticated player's state; shared routing supplies the binding.
  gameState = await api('/api/v1/games/fan-tan/state');
  // Reconcile any unresolved retry identity against authoritative history and current ownership before rendering. (issue #261)
  reconcilePendingRequest();
  // Restore the latest real result without inventing a default residue.
  latestRound = gameState.state?.recent_rounds?.length ? gameState.state.recent_rounds[gameState.state.recent_rounds.length - 1] : null;
  // Recover a repeatable wager map from the newest settled round so repeat survives a reload.
  lastBet = latestRound?.wagers ? { wagers: { ...latestRound.wagers } } : null;
  // Render after rules and history resources are available.
  render();
}

// Submit one complete wager map and present the settled backend result.
async function play() {
  // Ignore duplicate clicks while the existing action identity is in flight.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Capture the current route outlet for validation and stale-response guards.
  const root = lifecycle.root();
  // Require at least one positive wager (locked to the pending snapshot after an ambiguous failure) before contacting the ledger endpoint. (issue #261)
  if (!Object.keys(activeWagers()).length) {
    // Show localized player guidance in the reserved error region.
    root.querySelector('[data-error]').textContent = tx('error.wagerRequired');
    // Stop without creating an idempotency identity or ledger request.
    return;
  }
  // Guard controls before generating and sending one atomic action.
  lifecycle.setBusy(true);
  // Move the phase to an understandable in-progress state.
  phase = 'phase.counting';
  // Cancel any prior presentation callback before scheduling a new result.
  motionScope.cancelAll();
  // Render the disabled action and stable counting phase.
  render();
  // Capture the current mount so a completed request cannot repaint a later route.
  const mountedRoot = lifecycle.root();
  // Capture the current timer scope so teardown can invalidate this presentation path.
  const activeScope = motionScope;
  // Start protected API work so failures restore controls without leaked timers.
  try {
    // Resolve the frozen idempotency payload so a retry replays the exact same identity and immutable body. (issue #261)
    const command = resolvePlayPayload(activeWagers());
    // Send the retained action identity with its frozen wager snapshot, never the live mutable controls.
    const response = await post('/api/v1/games/fan-tan/rounds', { action_id: command.action_id, wagers: command.wagers });
    // Clear the retained identity only after the server has confirmed this round.
    clearPendingRequest();
    // Stop presentation when shell navigation unmounted or replaced this route during the request.
    if (lifecycle.root() !== mountedRoot || motionScope !== activeScope) return;
    // Show the committed debit before the counted pile exposes its final residue. (LEDGER-031, issue #589)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Store the authoritative settlement before starting decorative presentation.
    latestRound = response.round;
    // Remember the settled wager map so one click can repeat the same round next time.
    lastBet = { wagers: { ...(response.round?.wagers || command.wagers) } };
    // Treat a platform reduced-motion preference as immediate counting evidence.
    reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
    // Schedule the final reveal through the shared motion scope.
    scheduleCount({ timerScope: activeScope, onSettled: async () => { phase = 'phase.settled'; lifecycle.setBusy(false); gameState = await api('/api/v1/games/fan-tan/state'); render(); await refreshBalance(); } });
    // Rerender the highlighted residue while keeping result text reserved.
    render();
  // Handle API or validation failures with localized feedback and restored controls.
  } catch (error) {
    // Ignore late failures after navigation because teardown already restored route ownership.
    if (lifecycle.root() !== mountedRoot || motionScope !== activeScope) return;
    // Discard the pending identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearPendingRequest();
    // Restore the ready phase after a failed atomic request.
    phase = 'phase.ready';
    // Re-enable controls for a corrected request.
    lifecycle.setBusy(false);
    // Rerender before writing into the reserved error region.
    render();
    // Show a localized game-specific failure message.
    mountedRoot.querySelector('[data-error]').textContent = tx('error.playFailed');
    // Also use the shared non-blocking feedback surface.
    toast(tx('error.playFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #77 integration.
export const FanTanGame = {
  // Expose the stable catalog identifier without hard-coded visible copy.
  id: 'fan_tan',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset any repeatable wager map so a new mount never inherits a stale one before load reconciles history.
    lastBet = null;
    // Establish shared route, stylesheet, localization, and locale-subscription ownership.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation released the route during asynchronous locale initialization.
    if (!mounted) return;
    // Create one lifecycle-bound timer scope after the route owns its locale resources.
    motionScope = createMotionTimerScope();
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release timers and subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Permanently cancel all pending count callbacks and lifecycle listeners.
    motionScope?.dispose();
    // Clear the disposed scope reference for the next mount.
    motionScope = null;
    // Release route, locale-subscription, and in-flight lifecycle ownership.
    lifecycle.unmount();
    // Clear the repeatable wager map so the next session starts fresh.
    lastBet = null;
    // Release any unresolved retry identity so a later mount or a different session cannot inherit it; remount reloads authoritative state. (issue #261)
    clearPendingRequest();
  },
};
