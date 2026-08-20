// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the isolated Dragon Tiger browser module for GitHub issue #83.

// Import session-bound API helpers without sending a caller-selected player id.
import { api, post } from '../core/api.js';
// Import shared safe-markup, feedback, and authenticated-wallet helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the merged #96 accessible card renderer.
import { renderCard } from '../core/cards.js';
// Import number formatting independently from route lifecycle ownership.
import { formatNumber } from '../core/i18n.js';
// Import the shared controller for route, locale, style, busy, and request ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Address the additive frozen-v1 API through one stable root.
const API_ROOT = '/api/v1/games/dragon-tiger';
// Address the game-owned EN/RU resource domain.
const DOMAIN = 'games/dragon_tiger';
// Identify shared card styles so repeated mounts install them once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve canonical wager ordering across renders and locales.
export const BETS = Object.freeze(['dragon', 'tiger', 'tie']);

// Retain the latest session-bound backend state for reload and locale rendering.
let gameState = { shoe: {}, rules: {}, recent_rounds: [] };
// Retain the locally selected wager target.
let selectedBet = 'dragon';
// Retain the locally selected play-token amount.
let wager = 5;
// Block player actions until the initial session-bound snapshot resolves.
let initialLoading = false;
// Retain the complete unresolved request so retries reuse its action id and payload.
let pendingAction = null;
// Retain the last committed bet target and stake so one click can repeat it.
let lastBet = null;

// Generate one replay-safe action id through an injectable deterministic seam.
export function createActionId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require UUID support rather than risk a colliding ledger action identity.
  if (typeof randomUUID !== 'function') throw new Error('secure action identity unavailable');
  // Prefix the opaque UUID for readable game-local diagnostics.
  return `dt-${randomUUID()}`;
}

// Delegate route-local lifecycle ownership to the shared bounded controller.
const lifecycle = createGameLifecycle({
  // Bind every translation to the existing game-owned domain.
  domain: DOMAIN,
  // Scope the fallback identity without player, bet, wager, or shoe data.
  requestPrefix: 'dt',
  // Preserve the frozen production dt-UUID identity through the shared allocator.
  uuidFactory: () => createActionId(),
  // Install the formatted route stylesheet exactly once across remounts.
  stylesheet: { id: 'dragon-tiger-styles', href: '/games/dragon_tiger.css' },
});
// Read localized copy directly through the shared domain owner.
const tx = lifecycle.tx;
// Identify the exact mount that may adopt asynchronous responses into the shared outlet.
let routeSession = null;

// Merge GET and POST payloads into the route's stable render state.
export function normalizeStatePayload(payload = {}) {
  // Copy the documented state object without mutating the API response.
  const next = payload.state && typeof payload.state === 'object' ? { ...payload.state } : {};
  // Preserve the top-level immutable rules alongside reload-safe state.
  next.rules = payload.rules || next.rules || {};
  // Preserve the documented shoe shape when an early payload omits it.
  next.shoe = next.shoe || {};
  // Copy recent rounds before optionally adding the POST result.
  const rounds = Array.isArray(next.recent_rounds) ? [...next.recent_rounds] : [];
  // Add a returned round only when state did not already include it.
  if (payload.round && !rounds.some(round => round.round_id === payload.round.round_id)) rounds.push(payload.round);
  // Keep a bounded history so the data rail never needs nested scrolling.
  next.recent_rounds = rounds.slice(-8);
  // Return one renderer-ready state object.
  return next;
}

// Install the shared #96 card stylesheet without copying its rules.
function ensureCardStyles() {
  // Reuse a stylesheet installed by this or another card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create the standard stylesheet link through the DOM API.
  const link = document.createElement('link');
  // Assign its stable cross-game identity.
  link.id = CARD_STYLE_ID;
  // Declare the linked resource as CSS.
  link.rel = 'stylesheet';
  // Load the merged primitive styles from the web root.
  link.href = '/core/cards.css';
  // Install shared presentation before the first rendered cards.
  document.head.append(link);
}

// Format one ledger amount with localized play-token terminology.
function tokenAmount(value, translate = tx) {
  // Format the numeric portion without a currency or replacement-looking glyph.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Interpolate the amount into game-owned fake-token copy.
  return translate('units.playTokens', { amount });
}

// Render a shared card while replacing every default English accessible label.
export function localizedCard(card, { hidden = false, translate = tx } = {}) {
  // Render a localized face-down primitive for empty or request-bound card bays.
  if (hidden || !card) return renderCard('??', { hidden: true }).replace(/aria-label="[^"]*"/, `aria-label="${safe(translate('cards.faceDown'))}"`);
  // Read the compact rank from every character except the suit code.
  const rank = String(card).slice(0, -1);
  // Read the compact canonical suit code from the final character.
  const suit = String(card).slice(-1);
  // Build the complete accessible card name from localized rank and suit values.
  const label = translate('cards.label', { rank: translate(`ranks.${rank}`), suit: translate(`suits.${suit}`) });
  // Replace only the primitive's locale-neutral accessible label.
  return renderCard(card).replace(/aria-label="[^"]*"/, `aria-label="${safe(label)}"`);
}

// Return the newest reload-safe settled round.
function currentRound(snapshot = gameState) {
  // Read the bounded history supplied by the backend.
  const rounds = snapshot?.recent_rounds || [];
  // Return the newest entry or no round before first play.
  return rounds.length ? rounds[rounds.length - 1] : null;
}

// Map documented winners to stable locale keys without exposing API identifiers.
function winnerKey(round) {
  // Return the known winner or the pending presentation state.
  return BETS.includes(round?.winner) ? round.winner : 'pending';
}

// Render all route markup through an injectable translation seam.
export function viewMarkup({ snapshot = gameState, translate = tx, selected = selectedBet, wagerValue = wager, isDealing = lifecycle.isBusy(), isLoading = initialLoading, pending = pendingAction, repeatable = lastBet } = {}) {
  // Resolve the newest completed round once for a consistent frame.
  const round = currentRound(snapshot);
  // Resolve the request-bound or settled player-facing phase.
  const phase = translate(isLoading ? 'phases.loading' : isDealing ? 'phases.dealing' : round ? 'phases.settled' : 'phases.ready');
  // Resolve the current winner without exposing its internal enum.
  const result = translate(`outcomes.${winnerKey(round)}`);
  // Disable configuration while a request or unresolved retry owns its payload.
  const configurationDisabled = isLoading || isDealing || Boolean(pending);
  // Keep a saved retry actionable while blocking initial-load and in-flight clicks.
  const actionDisabled = isLoading || isDealing;
  // Enable the one-click repeat only when a prior bet exists and no request or retry is active.
  const repeatDisabled = actionDisabled || Boolean(pending) || !repeatable;
  // Render semantic pressed-state wager buttons with visible selected copy.
  const bets = BETS.map(bet => `<button type="button" class="dt-bet${selected === bet ? ' is-selected' : ''}" data-bet="${bet}" aria-pressed="${selected === bet}"${configurationDisabled ? ' disabled' : ''}>${safe(translate(`bets.${bet}`))}${selected === bet ? `<span class="dt-selected">${safe(translate('bets.selected'))}</span>` : ''}</button>`).join('');
  // Resolve the primary action label for normal, request, and retry states.
  const actionLabel = translate(isLoading ? 'controls.loading' : isDealing ? 'controls.dealing' : pending ? 'controls.retry' : round ? 'controls.dealNext' : 'controls.deal');
  // Render the two visible cards or localized face-down placeholders.
  const dragonCard = localizedCard(round?.dragon_card, { hidden: isDealing || !round, translate });
  // Render the opposing card through the same localized primitive adapter.
  const tigerCard = localizedCard(round?.tiger_card, { hidden: isDealing || !round, translate });
  // Resolve recent history in newest-first display order.
  const recent = [...(snapshot?.recent_rounds || [])].reverse().slice(0, 6);
  // Render each bounded history row with localized winner, bet, and net result.
  const history = recent.map(item => `<article class="dt-history-row"><span>${safe(translate(`outcomes.${winnerKey(item)}`))}<small class="dt-muted">${safe(translate('history.bet', { bet: translate(`bets.${item.bet}`) }))}</small></span><strong>${safe(tokenAmount(item.net, translate))}</strong></article>`).join('');
  // Read server-owned rules and shoe telemetry without inventing values.
  const rules = snapshot?.rules || {};
  // Read the contract's nested main-bet payout definitions.
  const betRules = rules.bets || {};
  // Read server-owned shoe state for the data rail.
  const shoe = snapshot?.shoe || {};
  // Return the complete responsive three-zone route.
  return `<section class="dragon-tiger" data-testid="dragon-tiger"><header class="dt-header"><div><p class="dt-muted">${safe(translate('eyebrow'))}</p><h1>${safe(translate('title'))}</h1></div><span class="dt-phase" role="status" aria-live="polite">${safe(phase)}</span></header><div class="dt-layout"><section class="dt-panel dt-controls" aria-label="${safe(translate('controls.region'))}"><h2>${safe(translate('controls.title'))}</h2><div class="dt-bets">${bets}</div><label for="dt-wager">${safe(translate('controls.wager'))}</label><input id="dt-wager" type="number" min="0.01" max="1000000" step="0.01" value="${safe(wagerValue)}"${configurationDisabled ? ' disabled' : ''}><button type="button" class="dt-deal" data-action="deal"${actionDisabled ? ' disabled' : ''}>${safe(actionLabel)}</button><button type="button" class="dt-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(translate('controls.repeat'))}</button><p class="dt-muted">${safe(translate(pending ? 'controls.retryHelp' : 'controls.help'))}</p></section><main class="dt-panel dt-stage" data-testid="dragon-tiger-table" aria-label="${safe(translate('stage.region'))}"><div class="dt-stage-head"><div><p class="dt-muted">${safe(translate('stage.selectedBet', { bet: translate(`bets.${pending?.bet || round?.bet || selected}`) }))}</p><h2>${safe(result)}</h2></div><strong>${safe(phase)}</strong></div><div class="dt-hands"><section class="dt-hand" aria-label="${safe(translate('stage.dragonHand'))}"><h3>${safe(translate('bets.dragon'))}</h3>${dragonCard}</section><section class="dt-hand" aria-label="${safe(translate('stage.tigerHand'))}"><h3>${safe(translate('bets.tiger'))}</h3>${tigerCard}</section></div><div class="dt-summary"><div class="dt-stat"><span>${safe(translate('summary.wager'))}</span><strong>${safe(tokenAmount(round?.wager || 0, translate))}</strong></div><div class="dt-stat"><span>${safe(translate('summary.return'))}</span><strong>${safe(tokenAmount(round?.total_return || 0, translate))}</strong></div><div class="dt-stat"><span>${safe(translate('summary.net'))}</span><strong>${safe(tokenAmount(round?.net || 0, translate))}</strong></div></div></main><aside class="dt-panel dt-data" aria-label="${safe(translate('data.region'))}"><h2>${safe(translate('data.title'))}</h2><div class="dt-stat"><span>${safe(translate('data.cardsRemaining'))}</span><strong>${safe(formatNumber(shoe.cards_remaining || 0))}</strong></div><div class="dt-stat"><span>${safe(translate('data.deckCount'))}</span><strong>${safe(formatNumber(rules.deck_count || 0))}</strong></div><p class="dt-muted">${safe(translate('data.rule', { dragon: betRules.dragon?.net_odds ?? 1, tiger: betRules.tiger?.net_odds ?? 1, tie: betRules.tie?.net_odds ?? 11 }))}</p><h3>${safe(translate('history.title'))}</h3><div class="dt-history">${history || `<p class="dt-muted">${safe(translate('history.empty'))}</p>`}</div></aside></div></section>`;
}

// Render current state and reconnect semantic controls.
function render() {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Ignore locale callbacks and promises after route teardown.
  if (!root) return;
  // Replace the isolated route atomically.
  root.innerHTML = viewMarkup();
  // Bind each wager target to local unsent configuration.
  root.querySelectorAll('[data-bet]').forEach(button => { button.onclick = () => { if (!initialLoading && !lifecycle.isBusy() && !pendingAction) { selectedBet = button.dataset.bet; render(); } }; });
  // Read and bind the wager input created by this render.
  const wagerInput = root.querySelector('#dt-wager');
  // Preserve a positive normalized wager without moving tokens.
  if (wagerInput) wagerInput.onchange = () => { if (!initialLoading && !pendingAction) { wager = Math.min(1000000, Math.max(0.01, Math.round(Number(wagerInput.value || wager || 5) * 100) / 100)); render(); } };
  // Bind the one atomic deal action.
  root.querySelector('[data-action="deal"]')?.addEventListener('click', deal);
  // Bind the one-click repeat that re-fires the previous bet.
  root.querySelector('[data-action="repeat"]')?.addEventListener('click', repeat);
}

// Report whether one asynchronous operation still belongs to the exact mounted route session.
function ownsAction(session, root) {
  // Require both the game-specific session token and lifecycle-owned outlet to remain unchanged.
  return routeSession === session && lifecycle.root() === root;
}

// Re-apply the last committed bet and re-fire one deal without a timer.
async function repeat() {
  // Ignore repeat while loading, dealing, or holding an unresolved retry, or without a prior bet.
  if (initialLoading || lifecycle.isBusy() || pendingAction || !lastBet) return;
  // Restore the previous bet target into the local configuration.
  selectedBet = lastBet.bet;
  // Restore the previous stake into the local configuration.
  wager = lastBet.wager;
  // Fire the shared exactly-once deal action with the restored bet.
  await deal();
}

// Submit or retry one exactly-once Dragon Tiger round.
async function deal() {
  // Ignore overlapping clicks while the POST request is active.
  if (initialLoading || lifecycle.isBusy()) return;
  // Capture the lifecycle-owned route outlet before any asynchronous boundary.
  const ownedRoot = lifecycle.root();
  // Capture the mount-specific token because the shell reuses one persistent outlet across routes.
  const ownedSession = routeSession;
  // Refuse synthetic actions after teardown or before the shared mount completes.
  if (!ownedRoot || !ownedSession) return;
  // Capture one immutable request and retain it through any failed response.
  pendingAction = pendingAction || { action_id: lifecycle.nextRequestId('round'), bet: selectedBet, wager };
  // Enter request-bound dealing state without starting a timer.
  lifecycle.setBusy(true);
  // Render face-down cards and disabled controls during the request.
  render();
  // Run the action while preserving the retry payload on errors.
  try {
    // Post only the documented session-bound action fields.
    const payload = await post(`${API_ROOT}/rounds`, pendingAction);
    // Stop if navigation replaced this route while the request completed.
    if (!ownsAction(ownedSession, ownedRoot)) return;
    // Merge returned state, rules, and round for immediate and reload-consistent rendering.
    gameState = normalizeStatePayload(payload);
    // Remember the settled bet and stake so the next round can repeat with one click.
    const settled = currentRound(gameState);
    // Capture the repeatable configuration only from a fully settled round.
    if (settled) lastBet = { bet: settled.bet, wager: settled.wager };
    // Clear the action only after a successful server response.
    pendingAction = null;
    // Refresh the authenticated wallet without reclassifying a committed round as a failed deal.
    try {
      // Ask the shared shell for the now-authoritative ledger balance.
      await refreshBalance();
    // Keep the settled round while reporting only the secondary wallet refresh failure.
    } catch (_) {
      // Notify only while this mount still owns the route.
      if (ownsAction(ownedSession, ownedRoot)) toast(tx('errors.balanceRefreshFailed'));
    }
  // Translate request failures instead of exposing server English in the route.
  } catch (_) {
    // Show localized retry guidance only while this mount still owns the route.
    if (ownsAction(ownedSession, ownedRoot)) toast(tx('errors.dealFailed'));
  // Always leave request-bound dealing state for the active mount.
  } finally {
    // Stop when teardown already cleared route ownership.
    if (!ownsAction(ownedSession, ownedRoot)) return;
    // Release the request guard while preserving any unresolved retry payload.
    lifecycle.setBusy(false);
    // Render either the settled round or localized retry action.
    render();
  }
}

// Export the catalog-loadable lazy game contract.
export const DragonTigerGame = {
  // Expose the descriptor-facing stable game id.
  id: 'dragon_tiger',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset player-local transient state before loading session data.
    gameState = { shoe: {}, rules: {}, recent_rounds: [] };
    // Reset request state so another user never inherits an action id.
    pendingAction = null;
    // Reset the repeatable bet so another session never inherits it.
    lastBet = null;
    // Hold every player action until the session-bound GET finishes.
    initialLoading = true;
    // Install the shared semantic card stylesheet independently from route-local presentation.
    ensureCardStyles();
    // Establish route, stylesheet, locale, and repaint ownership through the shared controller.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation released this route during asynchronous locale loading.
    if (!mounted) return;
    // Create one mount-specific token so later remounts of the persistent shell outlet reject stale responses.
    const session = Object.freeze({});
    // Publish the token only after the shared lifecycle owns the route completely.
    routeSession = session;
    // Render a localized inert loading frame while backend state loads.
    render();
    // Load the authenticated player's reload-safe state.
    try {
      // Fetch state without a caller-selected player identity.
      const payload = await api(`${API_ROOT}/state`);
      // Stop if navigation replaced this route during the request.
      if (!ownsAction(session, node)) return;
      // Store the documented state and top-level rules.
      gameState = normalizeStatePayload(payload);
      // Recover a repeatable bet from the newest settled round so repeat survives a reload.
      const restored = currentRound(gameState);
      // Restore the repeatable configuration only when a settled round is present.
      if (restored) lastBet = { bet: restored.bet, wager: restored.wager };
      // Release the initial action guard only after the snapshot is authoritative.
      initialLoading = false;
      // Render recovered shoe and round history.
      render();
      // Align the shared wallet without misclassifying an already loaded game state.
      try {
        // Ask the shared shell for the authenticated player's current ledger balance.
        await refreshBalance();
      // Report only the secondary wallet refresh failure.
      } catch (_) {
        // Notify only while this mount still owns the route.
        if (ownsAction(session, node)) toast(tx('errors.balanceRefreshFailed'));
      }
    // Surface a localized load failure while leaving a retry-safe ready frame.
    } catch (_) {
      // Stop a late rejection from releasing a newer mount's initial-load guard.
      if (!ownsAction(session, node)) return;
      // Release the guard because the failed GET can no longer overwrite a later action.
      initialLoading = false;
      // Re-render one actionable retry-safe frame after the failed snapshot request.
      render();
      // Notify only while this mount still owns the route.
      if (ownsAction(session, node)) toast(tx('errors.loadFailed'));
    }
  },
  // Release every game-owned lifecycle resource on route exit.
  unmount() {
    // Invalidate game-specific state adoption before releasing the shared route owner.
    routeSession = null;
    // Release route, locale, and busy ownership idempotently.
    lifecycle.unmount();
    // Clear player state so another session cannot inherit it.
    gameState = { shoe: {}, rules: {}, recent_rounds: [] };
    // Clear any unresolved action identity at the session boundary.
    pendingAction = null;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
    // Release initial-load presentation state at the session boundary.
    initialLoading = false;
  },
};
