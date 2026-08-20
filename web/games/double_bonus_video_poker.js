// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Double Bonus Video Poker browser module for GitHub issue #131 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import the shared controller for route, locale, style, busy, and request ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/double_bonus_video_poker';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/double-bonus-video-poker';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the paytable order independently of object insertion behavior.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_aces', 'four_2s_4s', 'four_5s_ks', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'jacks_or_better'];
// Delegate route-local lifecycle ownership to the shared bounded controller.
const lifecycle = createGameLifecycle({
  // Bind every translation to the existing game-owned domain.
  domain: DOMAIN,
  // Scope fallback request identities without player or round data.
  requestPrefix: 'dbvp',
  // Install the formatted route stylesheet exactly once across remounts.
  stylesheet: { id: 'double-bonus-video-poker-styles', href: '/games/double_bonus_video_poker.css' },
});
// Read localized copy directly through the shared domain owner.
const tx = lifecycle.tx;

// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for the paytable display.
let rules = {};
// Store the configured bet before the next round.
let bet = 5;
// Track which dealt positions the player has toggled to hold during the draw phase.
let held = new Set();
// Identify the exact mount that may adopt asynchronous responses into the shared outlet.
let routeSession = null;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealId = null;
// Bind the unresolved deal retry id to one bet.
let pendingDealBet = null;
// Retain an unresolved draw retry id bound to one round and hold selection.
let pendingDrawId = null;
// Bind the unresolved draw retry id to one round and its held positions.
let pendingDrawContext = null;
// Retain the last settled bet so one click can start an identical new deal.
let lastBet = null;

// Install the shared card stylesheet without changing the global shell files.
function ensureSharedCardStyles() {
  // Reuse a stylesheet already installed by another card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create one standard stylesheet link for the shared renderer.
  const link = document.createElement('link');
  // Mark the link so future mounts remain idempotent.
  link.id = CARD_STYLE_ID;
  // Declare a normal stylesheet relationship for browser loading.
  link.rel = 'stylesheet';
  // Load the shared presentation hooks from the public core path.
  link.href = '/core/cards.css';
  // Add the shared stylesheet to document metadata once.
  document.head.append(link);
}

// Normalize a bet to the ledger-compatible bounds.
function normalizedBet(value) {
  // Convert browser input text to a numeric wager.
  const parsed = Number(value);
  // Return the lower bound for invalid or undersized values.
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  // Clamp oversized browser values to the public contract maximum.
  const bounded = Math.min(parsed, 100000);
  // Round to cents so previews match ledger-compatible request values.
  return Math.round(bounded * 100) / 100;
}

// Read the newest actionable or completed round from reload-safe server state.
function currentRound() {
  // Prefer the active draw round over retained history.
  if (state?.active_round) return state.active_round;
  // Read the bounded recent-round collection returned by the game API.
  const recent = state?.recent_rounds || [];
  // Return the newest completed round, which the engine appends last.
  return recent.length ? recent[recent.length - 1] : null;
}

// Adopt one state-bearing API response and clear resolved retry ids.
function adoptPayload(payload) {
  // Replace cached player state only when the response includes it.
  if (payload?.state) state = payload.state;
  // Replace cached rules only when the response includes authoritative values.
  if (payload?.rules) rules = payload.rules;
  // Clear the pending deal id once the server confirms the round.
  if (payload?.round) {
    // Release the resolved deal retry binding.
    pendingDealId = null;
    // Release the resolved deal bet.
    pendingDealBet = null;
  }
}

// Render the paytable rows for the total-return hand table.
function paytableRows() {
  // Build one row per listed hand tier present in the authoritative table.
  return PAYTABLE_ORDER.filter(name => rules.paytable && rules.paytable[name] !== undefined).map(name => `<div><span>${safe(tx('hand.' + name))}</span><span>${rules.paytable[name]}</span></div>`).join('');
}

// Render the complete Double Bonus route into the outlet.
function render() {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the newest round to decide which stage to present.
  const round = currentRound();
  // Determine whether a draw is awaited.
  const drawing = round && round.phase === 'draw';
  // Determine whether a terminal hand is available for the next-deal presentation.
  const settled = round && round.phase === 'settled';
  // Select one localized phase label for the current authoritative state.
  const phaseKey = drawing ? 'draw' : settled ? 'settled' : 'idle';
  // Build the stage markup for the current phase.
  const stage = drawing ? drawStage(round) : settled ? settledStage(round) : idleStage();
  // Build the side panel with the bet input and the paytable.
  const panel = sidePanel(drawing, settled);
  // Paint the whole route.
  root.innerHTML = `<section class="dbvp" data-testid="double-bonus-video-poker"><header class="db-header"><h1>${safe(tx('title'))}</h1><p class="db-phase" data-testid="double-bonus-video-poker-phase" aria-live="polite">${safe(tx('phase.' + phaseKey))}</p></header><div class="db-stage">${stage}</div><div class="db-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set the bet and deal.
  return `<p class="db-result" data-testid="double-bonus-video-poker-result">${safe(tx('result.idle'))}</p>`;
}

// Build the draw stage with each dealt card tappable to hold.
function drawStage(round) {
  // Build one tappable held-card slot per dealt card.
  const cards = round.hand.map((card, index) => `<div class="db-slot"><button class="db-holdbtn" data-hold="${index}" type="button" aria-pressed="${held.has(index)}" ${lifecycle.isBusy() ? 'disabled' : ''}>${renderCard(card)}</button><span class="db-tag">${held.has(index) ? safe(tx('label.held')) : ''}</span></div>`).join('');
  // Return the hand, the prompt, and the draw control.
  return `<div class="db-hand" data-testid="double-bonus-video-poker-hand">${cards}</div><p class="db-result">${safe(tx('result.draw'))}</p><div class="db-actions"><button class="db-btn draw" data-draw="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.draw'))}</button></div>`;
}

// Build the settled stage revealing the final hand and the result.
function settledStage(round) {
  // Render the final five-card hand.
  const cards = (round.final_hand || round.hand).map(card => renderCard(card)).join('');
  // Read the settled net movement.
  const net = round.net || 0;
  // Compose the outcome and hand tier line.
  const tier = round.hand_tier ? safe(tx('hand.' + round.hand_tier)) : '';
  // Build the outcome result line with a signed net amount.
  const line = `${safe(tx('outcome.' + round.outcome))} ${tier} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Return the revealed hand, the result, and a deal-again control.
  return `<div class="db-hand">${cards}</div><p class="db-result" data-testid="double-bonus-video-poker-result">${line}</p>`;
}

// Build the side panel with the bet input and the paytable.
function sidePanel(drawing, settled) {
  // Select a next-round label only after a completed hand exists.
  const dealLabel = settled ? tx('action.deal_again') : tx('action.deal');
  // Enable the one-click repeat only when a prior bet exists and no request or retry is active.
  const repeatDisabled = lifecycle.isBusy() || Boolean(pendingDealId) || Boolean(pendingDrawId) || !lastBet;
  // Hide the bet input while a draw is pending.
  const wagerCard = drawing ? '' : `<div class="db-card"><h3>${safe(tx('label.bet'))}</h3><div class="db-field"><label for="db-bet">${safe(tx('label.bet'))}</label><input id="db-bet" data-bet type="number" min="1" step="1" value="${bet}"></div><button class="db-btn deal" data-deal="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(dealLabel)}</button><button type="button" class="db-repeat" data-action="repeat" ${repeatDisabled ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div>`;
  // Build the paytable card.
  const paytable = `<div class="db-card db-paytable"><h3>${safe(tx('label.paytable'))}</h3><div class="db-pays">${paytableRows()}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${paytable}`;
}

// Attach event handlers to the current stage controls.
function bindEvents() {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Stop when teardown released the outlet between render and binding.
  if (!root) return;
  // Bind the bet input to the cached wager.
  const betInput = root.querySelector('[data-bet]');
  // Update the cached bet on input.
  if (betInput) betInput.onchange = () => { bet = normalizedBet(betInput.value); };
  // Bind each held-card toggle.
  root.querySelectorAll('[data-hold]').forEach(button => { button.onclick = () => toggleHold(Number(button.dataset.hold)); });
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the one-click repeat control to a fresh same-bet deal.
  const repeatButton = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler when the control is present.
  if (repeatButton) repeatButton.onclick = repeat;
  // Bind the draw control to the draw action.
  const drawButton = root.querySelector('[data-draw]');
  // Attach the draw handler.
  if (drawButton) drawButton.onclick = draw;
}

// Toggle one dealt card position in or out of the held set.
function toggleHold(index) {
  // Ignore toggles while an action is resolving.
  if (lifecycle.isBusy()) return;
  // Remove a held position or add a new one.
  if (held.has(index)) held.delete(index);
  // Add the newly held position.
  else held.add(index);
  // Repaint the updated hold selection.
  render();
}

// Report whether one asynchronous action still belongs to the exact mounted route session.
function ownsAction(session, root) {
  // Require both the game-specific session token and lifecycle-owned outlet to remain unchanged.
  return routeSession === session && lifecycle.root() === root;
}

// Run one guarded atomic action while blocking overlaps and adopting only current-mount responses.
async function runAction(worker, adopter) {
  // Capture the lifecycle-owned route outlet before any asynchronous boundary.
  const ownedRoot = lifecycle.root();
  // Capture the mount-specific token because the shell reuses one persistent outlet across routes.
  const ownedSession = routeSession;
  // Ignore repeated actions while one is already resolving.
  if (lifecycle.isBusy() || !ownedRoot || !ownedSession) return;
  // Mark the route busy and disable controls.
  lifecycle.setBusy(true);
  render();
  // Execute the protected worker and always release the guard.
  try {
    // Perform only the network request before route ownership is checked again.
    const payload = await worker();
    // Ignore a response that completed after teardown or a later remount of the persistent outlet.
    if (!ownsAction(ownedSession, ownedRoot)) return;
    // Adopt the response only after proving it belongs to this exact mount.
    adopter(payload);
  } catch (error) {
    // Surface a bounded error to the player.
    if (ownsAction(ownedSession, ownedRoot)) toast(error?.message || tx('error.action'), 'error');
  } finally {
    // Release the guard only for the still-mounted route.
    if (ownsAction(ownedSession, ownedRoot)) {
      // Clear the busy flag.
      lifecycle.setBusy(false);
      // Repaint the refreshed state.
      render();
      // Refresh the shell wallet after any movement.
      await refreshBalance();
    }
  }
}

// Deal one new round after committing the bet.
function deal() {
  // Perform the deal as one guarded action.
  return runAction(async () => {
    // Reset the held selection for the fresh hand.
    held = new Set();
    // Reuse an unresolved deal id or mint a fresh one bound to the current bet.
    if (!pendingDealId || pendingDealBet !== bet) {
      // Mint a fresh deal retry id.
      pendingDealId = lifecycle.nextRequestId('deal');
      // Bind the retry id to the exact bet.
      pendingDealBet = bet;
    }
    // Post the exactly-once deal with the current bet.
    return post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, bet }));
  }, payload => {
    // Adopt the returned state and reveal the dealt hand only for the current mount.
    adoptPayload(payload);
  });
}

// Draw replacements for the unheld cards and settle the paytable.
function draw() {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore draws when no active round awaits one.
  if (!round || round.phase !== 'draw') return;
  // Snapshot the sorted held positions for the request and fingerprint.
  const hold = [...held].sort((left, right) => left - right);
  // Perform the draw as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved draw id or mint one bound to this exact round and hold.
    const holdKey = hold.join(',');
    // Rebind the retry id when the round or hold selection changes.
    if (!pendingDrawId || pendingDrawContext?.round_id !== round.round_id || pendingDrawContext?.hold !== holdKey) {
      // Mint a fresh draw retry id.
      pendingDrawId = lifecycle.nextRequestId('draw');
      // Bind the retry id to the exact round and hold selection.
      pendingDrawContext = { round_id: round.round_id, hold: holdKey };
    }
    // Post the exactly-once draw with the held positions.
    return post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDrawId, hold }));
  }, payload => {
    // Adopt the settled result only for the current mount.
    adoptPayload(payload);
    // Release the resolved draw retry binding.
    pendingDrawId = null;
    // Release the resolved draw context.
    pendingDrawContext = null;
    // Read the newly settled round to capture its committed wager.
    const settled = currentRound();
    // Remember the settled bet so the next deal can repeat the same wager with one click.
    if (settled && settled.phase === 'settled') lastBet = { bet: settled.bet };
  });
}

// Start one new deal with the previous bet without replaying the hold or draw.
async function repeat() {
  // Read the current round to block a repeat during an unsettled hand.
  const round = currentRound();
  // Ignore repeat while busy, holding an unresolved retry, mid-hand, or without a prior bet.
  if (lifecycle.isBusy() || pendingDealId || pendingDrawId || !lastBet || (round && round.phase === 'draw')) return;
  // Restore the previous bet so the fresh deal commits the same wager.
  bet = lastBet.bet;
  // Fire the shared exactly-once deal action with the restored bet.
  await deal();
}

// Export the isolated Double Bonus Video Poker game for the shared shell.
export const DoubleBonusVideoPokerGame = {
  // Expose the stable catalog identifier.
  id: 'double_bonus_video_poker',
  // Expose an empty label because the shell provides the localized catalog label.
  label: '',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable bet so another session never inherits a prior wager.
    lastBet = null;
    // Install the shared semantic card stylesheet independently from route-local presentation.
    ensureSharedCardStyles();
    // Establish route, stylesheet, locale, and repaint ownership through the shared controller.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation released this route during asynchronous locale loading.
    if (!mounted) return;
    // Create one mount-specific token so later remounts of the persistent shell outlet reject stale responses.
    const session = Object.freeze({});
    // Publish the token only after the shared lifecycle owns the route completely.
    routeSession = session;
    // Read reload-safe state so a pending draw or settled result is restored.
    try {
      // Fetch the current player's game state.
      const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
      // Stop when navigation replaced this mount while state was loading.
      if (!ownsAction(session, node)) return;
      // Adopt the loaded state.
      adoptPayload(payload);
      // Read the newest reload-safe round to recover a repeatable bet.
      const restored = currentRound();
      // Restore the repeatable bet only when a settled round exposes its committed wager.
      if (restored && restored.phase === 'settled') lastBet = { bet: restored.bet };
    } catch (error) {
      // Surface a load failure without breaking the shell.
      if (ownsAction(session, node)) toast(tx('error.load'), 'error');
    }
    // Stop when the route was replaced during the state load or error handling.
    if (!ownsAction(session, node)) return;
    // Render the first frame.
    render();
    // Refresh the shell wallet after mounting.
    await refreshBalance();
  },
  // Release subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Invalidate game-specific state adoption before releasing the shared route owner.
    routeSession = null;
    // Release route, locale, and busy ownership idempotently.
    lifecycle.unmount();
    // Clear cached state.
    state = null;
    // Clear cached rules.
    rules = {};
    // Reset the held selection.
    held = new Set();
    // Clear any pending retry ids so a later mount starts clean.
    pendingDealId = null;
    // Clear the pending deal context with its retry id.
    pendingDealBet = null;
    // Clear the pending draw id.
    pendingDrawId = null;
    // Clear the pending draw context with its retry id.
    pendingDrawContext = null;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
