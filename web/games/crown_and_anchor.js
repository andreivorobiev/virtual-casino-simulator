// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the isolated Crown and Anchor route for GitHub issue #133.
// Import the frozen API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import issue #97 dice primitives for deterministic reduced-motion presentation.
import { createSeededRandom, rollDice } from '../core/dice.js';
// Import issue #97 motion scope so every dice reveal timer has lifecycle cleanup.
import { createMotionTimerScope } from '../core/motion.js';
// Import shared route, locale, stylesheet, and busy-state ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/crown_and_anchor';
// Create the route controller with the external stylesheet and established diagnostic prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'caa', stylesheet: { id: 'crown-and-anchor-styles', href: '/games/crown_and_anchor.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Store stable symbol order matching the backend rules profile.
export const SYMBOL_IDS = Object.freeze(['crown', 'anchor', 'heart', 'diamond', 'club', 'spade']);
// Store decorative dice reveal duration resolved by the shared motion scope.
export const DICE_REVEAL_MS = 900;
// Store the latest backend-owned state payload.
let gameState = { symbols: [], recent_rounds: [] };
// Store locally edited wagers until one atomic round is submitted.
let wagers = {};
// Store the current player-facing phase key.
let phase = 'phase.ready';
// Store the latest settled round for the stage result.
let latestRound = null;
// Store the disposable timer scope owned by the current route mount.
let motionScope = null;
// Store one opaque generation token so stale asynchronous work cannot adopt a later mount.
let routeSession = null;
// Store whether the current reveal collapsed to reduced motion for CSS evidence.
let reducedMotionActive = false;
// Store whether dice are currently in the decorative reveal state.
let diceRolling = false;
// Store the last committed multi-symbol wager map so one click can repeat the identical bet.
let lastBet = null;

// Generate one deterministic three-die preview from issue #97 primitives.
export function previewFaces(seed) {
  // Create a repeatable random source from the supplied action or round seed.
  const random = createSeededRandom(seed);
  // Roll three six-sided dice through the shared primitive.
  return rollDice({ count: 3, sides: 6, random });
}

// Generate one retry-safe client identity using the browser cryptographic UUID provider.
export function createClientRequestId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require cryptographic UUID support so accidental double-submission identities do not collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Crown and Anchor rounds');
  // Prefix the UUID for readable action diagnostics without including player information.
  return `caa-${randomUUID()}`;
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

// Resolve the idempotency payload for one round, reusing the retained identity only for the identical player and wagers. (issue #261)
function resolveRoundPayload(wagerMap) {
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

// Return the wager map currently in effect, locking to the immutable pending snapshot after an ambiguous failure. (issue #261)
function activeWagers() {
  // Prefer the frozen pending payload so a retry cannot submit a changed intent under the same identity.
  return pendingPayload?.wagers || wagers;
}

// Schedule the dice reveal through a caller-owned reduced-motion timer scope.
export function scheduleDiceReveal({ timerScope, onSettled, duration = DICE_REVEAL_MS }) {
  // Require the shared timer-scope interface rather than allocating unmanaged timers.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require a callback so animation completion has an explicit owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Schedule through the scope so route exit and reduced motion share lifecycle cleanup.
  return timerScope.schedule(onSettled, duration);
}

// Format a play-token amount without a real-money or currency symbol.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale while keeping two-decimal ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit owned by this game domain.
  return translate('units.playTokens', { amount: number });
}

// Resolve the symbol shown on one die face.
function symbolForFace(face, translate = tx) {
  // Convert the one-based die face into the canonical symbol id.
  const symbol = SYMBOL_IDS[Number(face) - 1] || 'crown';
  // Return the localized symbol label.
  return translate(`symbol.${symbol}`);
}

// Return localized markup for every wager input.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend metadata while retaining canonical table ordering.
  return (gameState.symbols || []).map(symbol => `<label class="crown-anchor__bet"><span>${safe(translate(`symbol.${symbol.id}`))}</span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(symbol.id)}" value="${safe(activeWagers()[symbol.id] || '')}" aria-label="${safe(translate('wager.input', { symbol: translate(`symbol.${symbol.id}`) }))}"></label>`).join('');
}

// Return localized paytable rows from the fixed hit-count profile.
function paytableHtml(translate = tx) {
  // Show the transparent return table for one, two, and three matching dice.
  return [1, 2, 3].map(hits => `<div class="crown-anchor__payrow"><span>${safe(translate('paytable.hits', { hits }))}</span><span>${safe(translate('paytable.odds', { odds: hits }))}</span></div>`).join('');
}

// Return a compact symbol table with current hit counts.
function symbolTableHtml(translate = tx) {
  // Read latest hit counts or default every symbol to zero.
  const counts = latestRound?.hit_counts || {};
  // Render all six symbols as keyboard-scannable table cells.
  return SYMBOL_IDS.map(symbol => `<div class="crown-anchor__cell" data-symbol="${safe(symbol)}"><strong>${safe(translate(`symbol.${symbol}`))}</strong><span>${safe(translate('table.hits', { hits: counts[symbol] || 0 }))}</span></div>`).join('');
}

// Return bounded recent-round rows with no nested controls.
function historyHtml(translate = tx) {
  // Read newest history first for the player-owned data rail.
  const rows = [...(gameState.recent_rounds || [])].reverse();
  // Return the localized empty state until a real settlement exists.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render stable dice symbols and net values for each settled round.
  return rows.map(round => `<div class="crown-anchor__history-row"><span>${safe(round.symbols.map(symbol => translate(`symbol.${symbol}`)).join(' / '))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return the complete route markup using only localized visible strings.
export function viewMarkup({ translate = tx, repeatable = lastBet } = {}) {
  // Resolve and escape through an injected translator for deterministic locale tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Disable the one-click repeat until a prior settled bet exists and no request or retry is active.
  const repeatDisabled = lifecycle.isBusy() || Boolean(pendingRequestId) || !repeatable;
  // Resolve the visible dice faces or deterministic placeholder preview.
  const faces = latestRound?.faces || previewFaces('crown-and-anchor-waiting');
  // Resolve net result detail only when a backend settlement exists.
  const resultDetail = latestRound ? translated('result.net', { amount: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Render the three fixed dice slots with accessible labels.
  const diceHtml = faces.map((face, index) => `<div class="crown-anchor__die" data-die="${index}" data-rolling="${diceRolling}" data-reduced-motion="${reducedMotionActive}" aria-label="${safe(translate('die.aria', { index: index + 1, symbol: symbolForFace(face, translate) }))}">${safe(symbolForFace(face, translate))}</div>`).join('');
  // Return a three-zone layout aligned with the visual design standard.
  return `<section class="crown-anchor" data-testid="crown-and-anchor"><header class="crown-anchor__header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="crown-anchor__phase" data-testid="crown-and-anchor-phase">${translated(phase)}</span></header><div class="crown-anchor__layout"><section class="crown-anchor__panel crown-anchor__controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="crown-anchor__play" data-play type="button"${lifecycle.isBusy() ? ' disabled' : ''}>${translated(lifecycle.isBusy() ? 'action.rolling' : 'action.play')}</button><button class="crown-anchor__repeat" data-action="repeat" type="button"${repeatDisabled ? ' disabled' : ''}>${translated('controls.repeat')}</button><p class="crown-anchor__error" data-error aria-live="polite"></p></section><section class="crown-anchor__panel crown-anchor__stage" aria-label="${translated('stage.aria')}"><div class="crown-anchor__dice" aria-live="polite">${diceHtml}</div><div class="crown-anchor__table">${symbolTableHtml(translate)}</div><div class="crown-anchor__result" aria-live="polite"><strong>${translated(latestRound ? 'result.settled' : 'result.waiting')}</strong><span>${resultDetail}</span></div></section><aside class="crown-anchor__panel crown-anchor__data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="crown-anchor__history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
}

// Report whether asynchronous work still belongs to the exact mounted route and timer scope that started it.
function ownsRoute(session, root, scope) {
  // Require every owner identity so a later remount cannot adopt a stale response even when it reuses the same outlet.
  return Boolean(session) && routeSession === session && lifecycle.root() === root && motionScope === scope;
}

// Render the route and reconnect its game-owned inputs after DOM replacement.
function render() {
  // Resolve the currently owned shell outlet from the shared lifecycle controller.
  const root = lifecycle.root();
  // Stop stale async callbacks after route unmount.
  if (!root) return;
  // Replace the isolated route atomically so phase and stage regions stay stable.
  root.innerHTML = viewMarkup();
  // Wire every wager input to local unsent state.
  root.querySelectorAll('[data-wager]').forEach(input => { input.oninput = () => { const amount = Number(input.value); if (Number.isFinite(amount) && amount > 0) wagers[input.dataset.wager] = amount; else delete wagers[input.dataset.wager]; }; });
  // Wire the one atomic play action.
  root.querySelector('[data-play]').onclick = playRound;
  // Wire the one-click repeat that re-fires the previous multi-symbol bet.
  root.querySelector('[data-action="repeat"]').onclick = repeat;
}

// Re-apply the last committed wager map and re-fire one round without a timer.
async function repeat() {
  // Ignore repeat while a request is in flight, an ambiguous retry is unresolved, or no prior bet exists.
  if (lifecycle.isBusy() || pendingRequestId || !lastBet) return;
  // Restore the entire previous multi-symbol wager map into the local controls.
  wagers = { ...lastBet.wagers };
  // Fire the shared exactly-once play action with the restored bet.
  await playRound();
}

// Load session-bound state from the additive v1 game endpoint.
async function load(session, mountedRoot, activeScope) {
  // Fetch only the authenticated player's state; shared request binding owns identity.
  const loadedState = await api('/api/v1/games/crown-and-anchor/state');
  // Ignore a response whose route was released or replaced while the request was in flight.
  if (!ownsRoute(session, mountedRoot, activeScope)) return false;
  // Adopt the authoritative state only after exact route ownership is revalidated.
  gameState = loadedState;
  // Reconcile any unresolved retry identity against authoritative history and current ownership before rendering. (issue #261)
  reconcilePendingRequest();
  // Restore the latest real result without inventing a settled round.
  latestRound = gameState.recent_rounds?.length ? gameState.recent_rounds[gameState.recent_rounds.length - 1] : null;
  // Recover a repeatable wager map from the newest settled round so repeat survives a reload.
  lastBet = latestRound?.wagers && Object.keys(latestRound.wagers).length ? { wagers: { ...latestRound.wagers } } : null;
  // Render after rules and history resources are available.
  render();
  // Confirm that this mount adopted the requested state.
  return true;
}

// Submit one complete wager map and present the settled backend result.
async function playRound() {
  // Ignore duplicate clicks while the existing client identity is in flight.
  if (lifecycle.isBusy()) return;
  // Capture the current route identities before validation or request work.
  const mountedRoot = lifecycle.root();
  // Capture the current timer scope so teardown can invalidate this presentation path.
  const activeScope = motionScope;
  // Capture the opaque mount generation so remounting the same outlet cannot adopt stale work.
  const activeSession = routeSession;
  // Ignore a stale action after shell navigation released this game.
  if (!ownsRoute(activeSession, mountedRoot, activeScope)) return;
  // Require at least one positive wager (locked to the pending snapshot after an ambiguous failure) before contacting the ledger endpoint. (issue #261)
  if (!Object.keys(activeWagers()).length) {
    // Show localized player guidance in the reserved error region.
    mountedRoot.querySelector('[data-error]').textContent = tx('error.wagerRequired');
    // Stop without creating an idempotency identity or ledger request.
    return;
  }
  // Guard controls before generating and sending one atomic action.
  lifecycle.setBusy(true);
  // Move the phase to an understandable in-progress state.
  phase = 'phase.rolling';
  // Mark dice as rolling for a small decorative transition.
  diceRolling = true;
  // Cancel any prior presentation callback before scheduling a new result.
  activeScope.cancelAll();
  // Render the disabled action and stable rolling phase.
  render();
  // Start protected API work so failures restore controls without leaked timers.
  try {
    // Resolve the frozen idempotency payload so a retry replays the exact same identity and immutable body. (issue #261)
    const command = resolveRoundPayload(activeWagers());
    // Send the retained client identity with its frozen wager snapshot, never the live mutable controls.
    const response = await post('/api/v1/games/crown-and-anchor/rounds', { client_request_id: command.client_request_id, wagers: command.wagers });
    // Stop before touching shared retry or presentation state when navigation replaced this mount.
    if (!ownsRoute(activeSession, mountedRoot, activeScope)) return;
    // Clear the retained identity only after the server has confirmed this round.
    clearPendingRequest();
    // Show the committed debit before the authoritative dice symbols are revealed. (LEDGER-031, issue #587)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Store the authoritative settlement before starting decorative presentation.
    latestRound = response.round;
    // Remember the exact settled multi-symbol wager map so the next round can repeat it with one click.
    if (latestRound?.wagers && Object.keys(latestRound.wagers).length) lastBet = { wagers: { ...latestRound.wagers } };
    // Treat platform reduced motion as route-local CSS evidence.
    reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
    // Schedule the final reveal through the shared motion scope.
    scheduleDiceReveal({ timerScope: activeScope, onSettled: async () => {
      // Ignore a cancelled, replaced, or stale callback before any follow-up request begins.
      if (!ownsRoute(activeSession, mountedRoot, activeScope)) return;
      // Read authoritative history after the decorative reveal finishes.
      const settledState = await api('/api/v1/games/crown-and-anchor/state');
      // Ignore the state response when navigation released or remounted this route during the request.
      if (!ownsRoute(activeSession, mountedRoot, activeScope)) return;
      // Adopt the authoritative settled history only for the exact initiating mount.
      gameState = settledState;
      // Move the visible phase to its completed state.
      phase = 'phase.settled';
      // Release the atomic-action guard after settlement presentation and history reconciliation finish.
      lifecycle.setBusy(false);
      // Stop the decorative dice state after the reveal finishes.
      diceRolling = false;
      // Repaint settled state and enabled controls.
      render();
      // Refresh the shared wallet only after the authoritative round becomes visible.
      await refreshBalance();
    } });
    // Render the committed dice while the reveal state owns the timing.
    render();
  // Handle API or validation failures with localized feedback and restored controls.
  } catch (error) {
    // Ignore late failures after navigation because teardown already restored route ownership.
    if (!ownsRoute(activeSession, mountedRoot, activeScope)) return;
    // Discard the pending identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearPendingRequest();
    // Restore the ready phase after a failed atomic request.
    phase = 'phase.ready';
    // Re-enable controls for a corrected request.
    lifecycle.setBusy(false);
    // Stop the decorative dice state after failure.
    diceRolling = false;
    // Rerender before writing into the reserved error region.
    render();
    // Show a localized game-specific failure message.
    mountedRoot.querySelector('[data-error]').textContent = tx('error.playFailed');
    // Also use the shared non-blocking feedback surface.
    toast(tx('error.playFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #77 integration.
export const CrownAndAnchorGame = {
  // Expose the stable catalog identifier without hard-coded visible copy.
  id: 'crown_and_anchor',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable bet so a fresh mount never inherits a prior session's wager map.
    lastBet = null;
    // Establish shared route, stylesheet, localization, and locale-subscription ownership.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation released the route during asynchronous locale initialization.
    if (!mounted) return;
    // Create one lifecycle-bound timer scope after the route owns its locale resources.
    motionScope = createMotionTimerScope();
    // Create an opaque identity that distinguishes this mount from a later reuse of the same outlet.
    routeSession = Object.freeze({});
    // Load session-bound state and render the first frame.
    await load(routeSession, node, motionScope);
  },
  // Release timers and subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Invalidate asynchronous work before releasing any concrete route resources.
    routeSession = null;
    // Permanently cancel all pending dice callbacks and lifecycle listeners.
    motionScope?.dispose();
    // Clear the disposed scope reference for the next mount.
    motionScope = null;
    // Release route, locale-subscription, and in-flight lifecycle ownership.
    lifecycle.unmount();
    // Restore the initial phase so remount never inherits an abandoned rolling label.
    phase = 'phase.ready';
    // Reset dice reveal state for the next mount.
    diceRolling = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
    // Clear the presentation marker until a new action reads the active media preference.
    reducedMotionActive = false;
    // Release any unresolved retry identity so a later mount or a different session cannot inherit it; remount reloads authoritative state. (issue #261)
    clearPendingRequest();
  },
};
