// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the isolated Big Six Wheel route for GitHub issue #86.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import the merged #97 motion scope so every spin timer has lifecycle cleanup.
import { createMotionTimerScope } from '../core/motion.js';
// Import shared route, locale, stylesheet, and busy-state ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/big_six_wheel';
// Create the route controller with the external stylesheet and established diagnostic prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'bsw', stylesheet: { id: 'big-six-wheel-styles', href: '/games/big_six_wheel.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Store the canonical wheel size shared with the backend profile.
export const WHEEL_SIZE = 54;
// Store stable outcome order for controls and deterministic test fixtures.
export const OUTCOME_IDS = Object.freeze(['one', 'two', 'five', 'ten', 'twenty', 'joker', 'crest']);
// Store the normal decorative spin duration resolved by the shared motion scope.
export const SPIN_DURATION_MS = 1400;
// Require each normal spin to advance through enough complete turns to remain visibly unambiguous.
export const MIN_SPIN_REVOLUTIONS = 6;
// Store the latest backend-owned state payload.
let gameState = { outcomes: [], recent_rounds: [] };
// Store locally edited wagers until one atomic spin is submitted.
let wagers = {};
// Store the current player-facing phase key.
let phase = 'phase.ready';
// Store the latest settled round for the stage result.
let latestRound = null;
// Store the authoritative response that remains hidden until wheel motion finishes.
let pendingRound = null;
// Store the disposable timer scope owned by the current route mount.
let motionScope = null;
// Store the current wheel transform in degrees across rerenders.
let wheelAngle = 0;
// Store whether the current animation collapsed to reduced motion for CSS evidence.
let reducedMotionActive = false;
// Retain the last committed wager map so one click can repeat the same spin.
let lastBet = null;
// Calculate a deterministic landing angle that centers one wheel segment below the pointer.
export function rotationForIndex(resultIndex, revolutions = MIN_SPIN_REVOLUTIONS, currentAngle = 0) {
  // Reject invalid indices so broken API data cannot produce misleading wheel motion.
  if (!Number.isInteger(resultIndex) || resultIndex < 0 || resultIndex >= WHEEL_SIZE) throw new RangeError('resultIndex must identify one Big Six wheel segment');
  // Reject invalid turn counts supplied by tests or future animation settings.
  if (!Number.isFinite(revolutions) || revolutions < 0) throw new RangeError('revolutions must be a finite non-negative number');
  // Reject an invalid prior transform before it can reverse or freeze later wheel motion.
  if (!Number.isFinite(currentAngle)) throw new RangeError('currentAngle must be a finite number');
  // Calculate the selected segment's equivalent clockwise landing orientation.
  const landingAngle = (360 - ((resultIndex + 0.5) * (360 / WHEEL_SIZE))) % 360;
  // Require the new target to advance by at least the configured number of complete turns.
  const minimumTarget = currentAngle + (revolutions * 360);
  // Select the first equivalent landing transform at or beyond the minimum forward target.
  const completeTurns = Math.ceil((minimumTarget - landingAngle) / 360);
  // Return one monotonically forward target whose normalized angle centers the server-selected segment.
  return landingAngle + (completeTurns * 360);
}

// Schedule settlement presentation through a caller-owned reduced-motion timer scope.
export function scheduleSettlement({ timerScope, resultIndex, onSettled, duration = SPIN_DURATION_MS, currentAngle = 0 }) {
  // Require the shared timer-scope interface rather than allocating an unmanaged timer.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require a callback so animation completion has an explicit owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Calculate the target transform before scheduling the reveal.
  const angle = rotationForIndex(resultIndex, MIN_SPIN_REVOLUTIONS, currentAngle);
  // Schedule through the scope so route exit and reduced motion retain the same lifecycle semantics.
  const token = timerScope.schedule(onSettled, duration);
  // Return both presentation data and a cancellation handle for focused tests and callers.
  return { angle, token };
}

// Generate one retry-safe client identity using the browser cryptographic UUID provider.
export function createClientRequestId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require cryptographic UUID support so accidental double-submission identities never collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Big Six spins');
  // Prefix the UUID for readable action diagnostics without including player information.
  return `bsw-${randomUUID()}`;
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
  // Release the browser request identity.
  pendingRequestId = null;
  // Release the immutable wager snapshot.
  pendingPayload = null;
  // Release the authenticated owner paired with the request.
  pendingPlayerId = null;
}

// Resolve the idempotency payload for one spin, reusing the retained identity only for the identical player and wagers. (issue #261)
function resolveSpinPayload(wagerMap) {
  // Read the authenticated player that would own this request.
  const playerId = sessionPlayerId();
  // Reuse the frozen identity only when the same player resubmits the exact same immutable wager map after an ambiguous failure.
  if (pendingPayload && pendingPlayerId && pendingPlayerId === playerId && wagerSignature(pendingPayload.wagers) === wagerSignature(wagerMap)) {
    // Return the retained frozen payload for a safe exactly-once replay.
    return pendingPayload;
  }
  // Mint a fresh identity for a new intent before any network work.
  pendingRequestId = createClientRequestId();
  // Bind the authenticated owner so a later session cannot inherit this identity.
  pendingPlayerId = playerId;
  // Freeze the exact request body so a retry can never resend a different wager map.
  pendingPayload = Object.freeze({ client_request_id: pendingRequestId, wagers: Object.freeze({ ...wagerMap }) });
  // Return the frozen payload for the request.
  return pendingPayload;
}

// Reconcile an unresolved identity against authoritative history and current ownership. (issue #261)
function reconcilePendingRequest() {
  // Read only authoritative recent settlements echoed with their client request id from the current state payload.
  const recentRounds = gameState.recent_rounds || [];
  // Clear a pending identity already proven settled by server history.
  if (pendingRequestId && recentRounds.some(round => round?.client_request_id === pendingRequestId)) {
    // Treat authoritative reconciliation as acknowledgement of the committed spin.
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

// Format a play-token amount without any real-money or currency symbol.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale while keeping two-decimal ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit owned by this game domain.
  return translate('units.playTokens', { amount: number });
}

// Return localized markup for every wager input.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend metadata while retaining stable catalog ordering.
  return (gameState.outcomes || []).map(outcome => `<label class="big-six-wheel__bet"><span>${safe(translate(`outcome.${outcome.id}`))} <small>${safe(translate('odds.net', { odds: outcome.net_odds }))}</small></span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(outcome.id)}" value="${safe(activeWagers()[outcome.id] || '')}" aria-label="${safe(translate('wager.input', { outcome: translate(`outcome.${outcome.id}`) }))}"${lifecycle.isBusy() ? ' disabled' : ''}></label>`).join('');
}

// Return localized paytable rows from the immutable backend catalog.
function paytableHtml(translate = tx) {
  // Show both frequency and net odds so the simulator profile is explicit.
  return (gameState.outcomes || []).map(outcome => `<div class="big-six-wheel__payrow"><span>${safe(translate(`outcome.${outcome.id}`))}</span><span>${safe(translate('paytable.row', { segments: outcome.segment_count, odds: outcome.net_odds }))}</span></div>`).join('');
}

// Return bounded recent-round rows with no nested controls.
function historyHtml(translate = tx) {
  // Read newest history first for the player-owned data rail.
  const rows = [...(gameState.recent_rounds || [])].reverse();
  // Return the localized empty state until a real settlement exists.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render stable outcome and net values for each settled round.
  return rows.map(round => `<div class="big-six-wheel__history-row"><span>${safe(translate(`outcome.${round.outcome}`))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return the complete route markup using only localized visible strings.
export function viewMarkup({ translate = tx } = {}) {
  // Resolve and escape through an injected translator for deterministic locale tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Resolve the visible settled outcome or a localized waiting label.
  const outcomeLabel = lifecycle.isBusy() ? translated('action.spinning') : latestRound ? translated(`outcome.${latestRound.outcome}`) : translated('result.waiting');
  // Resolve net result detail only when a backend settlement exists.
  const resultDetail = lifecycle.isBusy() ? translated('result.hint') : latestRound ? translated('result.net', { amount: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Enable the one-click repeat only when a prior wager map exists and no spin or unresolved retry is active.
  const repeatDisabled = lifecycle.isBusy() || Boolean(pendingRequestId) || !lastBet;
  // Return a three-zone layout aligned with the visual-design standard.
  return `<section class="big-six-wheel" data-testid="big-six-wheel"><header class="big-six-wheel__header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="big-six-wheel__phase" data-testid="big-six-wheel-phase">${translated(phase)}</span></header><div class="big-six-wheel__layout"><section class="big-six-wheel__panel big-six-wheel__controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="big-six-wheel__spin" data-spin type="button"${lifecycle.isBusy() ? ' disabled' : ''}>${translated(lifecycle.isBusy() ? 'action.spinning' : 'action.spin')}</button><button type="button" class="big-six-wheel__repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${translated('controls.repeat')}</button><p class="big-six-wheel__error" data-error aria-live="polite"></p></section><section class="big-six-wheel__panel big-six-wheel__stage" aria-label="${translated('stage.aria')}"><div class="big-six-wheel__wheel-shell"><span class="big-six-wheel__pointer" aria-hidden="true"></span><div class="big-six-wheel__wheel" data-wheel data-reduced-motion="${reducedMotionActive}" style="--wheel-angle:${wheelAngle}deg" aria-hidden="true"></div><div class="big-six-wheel__hub"><span>${outcomeLabel}</span></div></div><div class="big-six-wheel__result" aria-live="polite"><strong>${outcomeLabel}</strong><span>${resultDetail}</span></div></section><aside class="big-six-wheel__panel big-six-wheel__data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="big-six-wheel__history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
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
  // Wire the one atomic spin action.
  root.querySelector('[data-spin]').onclick = spin;
  // Wire the one-click repeat that re-fires the previous wager map.
  root.querySelector('[data-action="repeat"]').onclick = repeat;
}

// Re-apply the last committed wager map and re-fire one spin without a timer.
async function repeat() {
  // Ignore repeat while spinning, holding an unresolved retry, or without a prior wager map.
  if (lifecycle.isBusy() || pendingRequestId || !lastBet) return;
  // Restore the previous wager map into the local control state.
  wagers = { ...lastBet.wagers };
  // Fire the shared exactly-once spin action with the restored wagers.
  await spin();
}

// Load session-bound state from the additive v1 game endpoint.
async function load() {
  // Fetch only the authenticated player's state; #81 supplies the route-level binding.
  gameState = await api('/api/v1/games/big-six-wheel/state');
  // Reconcile any unresolved retry identity against authoritative history and current ownership before rendering. (issue #261)
  reconcilePendingRequest();
  // Restore the latest real result without inventing a default wheel outcome.
  latestRound = gameState.recent_rounds?.length ? gameState.recent_rounds[gameState.recent_rounds.length - 1] : null;
  // Recover a repeatable wager map from the newest settled round so repeat survives a reload.
  lastBet = latestRound?.wagers ? { wagers: { ...latestRound.wagers } } : null;
  // Align a restored settled outcome without animating or losing cumulative orientation history.
  if (latestRound) wheelAngle = rotationForIndex(latestRound.result_index, 0, wheelAngle);
  // Restore a non-busy player-facing phase after navigation or reload reconciliation.
  phase = 'phase.ready';
  // Clear transient presentation state because persisted history is authoritative on mount.
  pendingRound = null;
  // Clear the action guard before the reconciled route becomes interactive.
  lifecycle.setBusy(false);
  // Render restored state without claiming that a new reduced-motion action is active.
  reducedMotionActive = false;
  // Render after rules and history resources are available.
  render();
}

// Submit one complete wager map and present the settled backend result.
async function spin() {
  // Ignore duplicate clicks while the existing client identity is in flight.
  if (lifecycle.isBusy()) return;
  // Read the currently owned route before validation or request work.
  const root = lifecycle.root();
  // Ignore a stale action after shell navigation released this game.
  if (!root) return;
  // Require at least one positive local wager before contacting the ledger endpoint.
  if (!Object.keys(activeWagers()).length) {
    // Show localized player guidance in the reserved error region.
    root.querySelector('[data-error]').textContent = tx('error.wagerRequired');
    // Stop without creating an idempotency identity or ledger request.
    return;
  }
  // Guard controls before generating and sending one atomic action.
  lifecycle.setBusy(true);
  // Move the phase to an understandable in-progress state.
  phase = 'phase.spinning';
  // Cancel any prior presentation callback before scheduling a new result.
  motionScope.cancelAll();
  // Render the disabled action and stable spinning phase.
  render();
  // Capture the current mount so a completed request cannot repaint a later route.
  const mountedRoot = lifecycle.root();
  // Capture the current timer scope so teardown can invalidate this presentation path.
  const activeScope = motionScope;
  // Start protected API work so failures restore controls without leaked timers.
  try {
    // Resolve the frozen idempotency payload so a retry replays the exact same identity and immutable body. (issue #261)
    const command = resolveSpinPayload(activeWagers());
    // Send the retained client identity with its frozen wager snapshot, never the live mutable controls.
    const response = await post('/api/v1/games/big-six-wheel/spins', { client_request_id: command.client_request_id, wagers: command.wagers });
    // Clear the retained identity only after the server has confirmed this spin.
    clearPendingRequest();
    // Stop presentation when shell navigation unmounted or replaced this route during the request.
    if (lifecycle.root() !== mountedRoot || motionScope !== activeScope) return;
    // Show the committed debit while the wheel still conceals its authoritative result. (LEDGER-031, issue #584)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Hold the authoritative settlement out of visible result regions until motion completes.
    pendingRound = response.round;
    // Remember the settled wager map so one click can repeat the same spin next round.
    lastBet = { wagers: { ...(response.round?.wagers || command.wagers) } };
    // Capture the existing transform so the next target always advances instead of resetting absolutely.
    const startingAngle = wheelAngle;
    // Define one settlement callback that publishes the result only after presentation completes.
    const revealSettlement = async () => {
      // Ignore a cancelled, replaced, or stale presentation callback after route ownership changes.
      if (lifecycle.root() !== mountedRoot || motionScope !== activeScope || pendingRound !== response.round) return;
      // Publish the server-authoritative outcome only after the wheel reaches its target.
      latestRound = pendingRound;
      // Clear hidden response state before controls become available for another spin.
      pendingRound = null;
      // Move the visible phase to its completed state.
      phase = 'phase.settled';
      // Release the atomic-action guard after both server settlement and presentation finish.
      lifecycle.setBusy(false);
      // Append the authoritative response to in-memory history without another fallible state request.
      gameState = { ...gameState, recent_rounds: [...(gameState.recent_rounds || []).filter(round => round.round_id !== latestRound.round_id), latestRound].slice(-100) };
      // Repaint result, history, locale, and enabled controls at the same final wheel orientation.
      render();
      // Refresh the shared wallet only after the authoritative round becomes visible.
      await refreshBalance();
    };
    // Calculate and schedule the cumulative final reveal through the lifecycle-owned timer scope.
    const presentation = scheduleSettlement({ timerScope: activeScope, resultIndex: pendingRound.result_index, currentAngle: startingAngle, onSettled: revealSettlement });
    // Preserve the cumulative target across resize-safe DOM state and the next spin.
    wheelAngle = presentation.angle;
    // Treat a zero-delay scheduled reveal as reduced motion for route CSS evidence.
    reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
    // Resolve the already-painted wheel element that still owns the starting transform.
    const wheel = mountedRoot.querySelector('[data-wheel]');
    // Expose reduced-motion state before changing transform so CSS applies the correct transition policy.
    wheel.dataset.reducedMotion = String(reducedMotionActive);
    // Force the browser to commit the starting frame before receiving the cumulative target.
    wheel.getBoundingClientRect();
    // Mutate only the persistent wheel transform so DOM replacement cannot erase interpolation.
    wheel.style.setProperty('--wheel-angle', `${wheelAngle}deg`);
  // Handle API or validation failures with localized feedback and restored controls.
  } catch (error) {
    // Ignore late failures after navigation because teardown already restored route ownership.
    if (lifecycle.root() !== mountedRoot || motionScope !== activeScope) return;
    // Discard the pending identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearPendingRequest();
    // Restore the ready phase after a failed atomic request.
    phase = 'phase.ready';
    // Remove any response that failed presentation validation before it can leak into a later spin.
    pendingRound = null;
    // Re-enable controls for a corrected request.
    lifecycle.setBusy(false);
    // Rerender before writing into the reserved error region.
    render();
    // Show a localized game-specific failure message.
    mountedRoot.querySelector('[data-error]').textContent = tx('error.spinFailed');
    // Also use the shared non-blocking feedback surface.
    toast(tx('error.spinFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #110/#77 integration.
export const BigSixWheelGame = {
  // Expose the stable catalog identifier without hard-coded visible copy.
  id: 'big_six_wheel',
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
    // Permanently cancel all pending spin callbacks and lifecycle listeners.
    motionScope?.dispose();
    // Clear the disposed scope reference for the next mount.
    motionScope = null;
    // Release route, locale-subscription, and in-flight lifecycle ownership.
    lifecycle.unmount();
    // Restore the initial phase so remount never inherits an abandoned spinning label.
    phase = 'phase.ready';
    // Drop any hidden response because remount will reconcile it from server-owned history.
    pendingRound = null;
    // Clear the repeatable wager map so the next session starts fresh.
    lastBet = null;
    // Clear the presentation marker until a new mount reads the active media preference.
    reducedMotionActive = false;
    // Release any unresolved retry identity so a later mount or a different session cannot inherit it; remount reloads authoritative state. (issue #261)
    clearPendingRequest();
  },
};
