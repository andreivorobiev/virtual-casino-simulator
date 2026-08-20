// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Four Card Poker browser module for GitHub issue #141 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import number formatting independently from route lifecycle ownership.
import { formatNumber } from '../core/i18n.js';
// Import the shared controller for route, locale, style, busy, and request ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/four_card_poker';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/four-card-poker';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the Ante Bonus paytable order independently of object insertion behavior.
const ANTE_BONUS_ORDER = ['four_of_a_kind', 'straight_flush', 'three_of_a_kind'];
// Preserve the Aces Up paytable order independently of object insertion behavior.
const ACES_UP_ORDER = ['four_of_a_kind', 'straight_flush', 'three_of_a_kind', 'flush', 'straight', 'two_pair', 'pair_of_aces'];
// Offer the three documented play raise sizes.
const PLAY_MULTIPLIERS = [1, 2, 3];
// Delegate route-local lifecycle ownership to the shared bounded controller.
const lifecycle = createGameLifecycle({
  // Bind every translation to the existing game-owned domain.
  domain: DOMAIN,
  // Scope fallback request identities without player or round data.
  requestPrefix: 'fcp',
  // Install the formatted route stylesheet exactly once across remounts.
  stylesheet: { id: 'four-card-poker-styles', href: '/games/four_card_poker.css' },
});
// Read localized copy directly through the shared domain owner.
const tx = lifecycle.tx;

// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for paytable displays.
let rules = {};
// Store the configured ante wager before the next round.
let ante = 5;
// Store the optional Aces Up wager before the next round.
let acesUp = 0;
// Retain the last committed ante and Aces Up bet so one click can repeat the same wagers.
let lastBet = null;
// Identify the exact mount that may adopt asynchronous responses into the shared outlet.
let routeSession = null;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealId = null;
// Bind the unresolved deal retry id to one ante and Aces Up payload.
let pendingDealContext = null;
// Retain an unresolved decision retry id independently from deal retries.
let pendingDecisionId = null;
// Bind the unresolved decision retry id to one round and selected decision.
let pendingDecisionContext = null;

// Format play-token values without a currency or replacement-looking glyph.
function tokenAmount(value) {
  // Interpolate a locale-formatted number into explicit fake-token terminology.
  return tx('tokens.amount', { amount: formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) });
}

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

// Normalize a wager while preserving the allowed zero value for Aces Up.
function normalizedWager(value, minimum) {
  // Convert browser input text to a numeric wager.
  const parsed = Number(value);
  // Return the lower bound for invalid or undersized values.
  if (!Number.isFinite(parsed) || parsed < minimum) return minimum;
  // Clamp oversized browser values to the public contract maximum.
  const bounded = Math.min(parsed, 100000);
  // Round to cents so previews match ledger-compatible request values.
  return Math.round(bounded * 100) / 100;
}

// Read the newest actionable or completed round from reload-safe server state.
function currentRound() {
  // Prefer the active decision round over retained history.
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
    // Release the resolved deal context.
    pendingDealContext = null;
  }
}

// Localize one card while keeping the shared renderer's structure.
function localizedCard(card, options = {}) {
  // Render face-down cards through the shared placeholder.
  return renderCard(card, options);
}

// Build the markup for one labelled row of cards.
function cardRow(titleKey, cards, options = {}) {
  // Render each card through the shared renderer.
  const rendered = (cards || []).map(card => localizedCard(card, options)).join('');
  // Return one titled card row.
  return `<div class="fcp-row"><h4>${safe(tx(titleKey))}</h4><div class="fcp-cards ${options.hand ? 'fcp-hand' : ''}">${rendered}</div></div>`;
}

// Render the paytable rows for one to-one multiplier table.
function paytableRows(order, table) {
  // Build one row per listed category present in the authoritative table.
  return order.filter(name => table && table[name] !== undefined).map(name => `<div><span>${safe(tx('hand.' + name))}</span><span>${table[name]}:1</span></div>`).join('');
}

// Render the complete Four Card Poker route into the outlet.
function render() {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the newest round to decide which stage to present.
  const round = currentRound();
  // Determine whether a decision is awaited.
  const deciding = round && round.phase === 'decision';
  // Build the stage markup for the current phase.
  const stage = deciding ? decisionStage(round) : round && round.phase === 'settled' ? settledStage(round) : idleStage();
  // Build the locale-owned route heading required for accessible page identification.
  const heading = `<h1 class="fcp-heading">${safe(tx('title'))}</h1>`;
  // Build the side panel with wager inputs and paytables.
  const panel = sidePanel(deciding);
  // Paint the whole route.
  root.innerHTML = `<section class="fourcp" data-testid="four-card-poker"><div class="fcp-stage">${heading}${stage}</div><div class="fcp-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set wagers and deal.
  return `<p class="fcp-result" data-testid="four-card-poker-result">${safe(tx('result.idle'))}</p>`;
}

// Build the decision stage showing the player's five cards and the play or fold controls.
function decisionStage(round) {
  // Render the five player cards for the pending decision.
  const cards = cardRow('label.your_cards', round.player_cards);
  // Build one play button per raise multiplier.
  const plays = PLAY_MULTIPLIERS.map(multiplier => `<button class="fcp-btn play" data-play="${multiplier}" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.play', { multiplier }))}</button>`).join('');
  // Return the cards, the fold control, and the play controls.
  return `${cards}<p class="fcp-result">${safe(tx('result.decide'))}</p><div class="fcp-actions"><button class="fcp-btn fold" data-fold="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.fold'))}</button>${plays}</div>`;
}

// Build the settled stage revealing both hands and the result.
function settledStage(round) {
  // Render the player's revealed best-four hand.
  const player = cardRow('label.your_cards', (round.player_hand && round.player_hand.cards) || round.player_cards, { hand: true });
  // Render the dealer's revealed cards when a showdown happened.
  const dealer = round.dealer_cards ? cardRow('label.dealer_cards', round.dealer_cards) : '';
  // Compose the localized outcome and net line.
  const net = round.net || 0;
  // Build the outcome result line with a signed net amount.
  const line = `${safe(tx('outcome.' + round.outcome))} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Enable the one-click repeat only when a prior bet exists and nothing is in flight.
  const repeatDisabled = lifecycle.isBusy() || !lastBet;
  // Return the revealed hands, the result, a deal-again control, and a one-click repeat.
  return `${player}${dealer}<p class="fcp-result" data-testid="four-card-poker-result">${line}</p><div class="fcp-actions"><button class="fcp-btn deal" data-deal="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.deal_again'))}</button><button type="button" class="fcp-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(tx('controls.repeat'))}</button></div>`;
}

// Build the side panel with wager inputs and paytables.
function sidePanel(deciding) {
  // Hide the wager inputs while a decision is pending.
  const wagerCard = deciding ? '' : `<div class="fcp-card"><h3>${safe(tx('label.wagers'))}</h3><div class="fcp-field"><label for="fcp-ante">${safe(tx('label.ante'))}</label><input id="fcp-ante" data-ante type="number" min="1" step="1" value="${ante}"></div><div class="fcp-field"><label for="fcp-aces">${safe(tx('label.aces_up'))}</label><input id="fcp-aces" data-aces type="number" min="0" step="1" value="${acesUp}"></div><button class="fcp-btn deal" data-deal="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.deal'))}</button></div>`;
  // Build the Ante Bonus paytable card.
  const anteBonus = `<div class="fcp-card"><h3>${safe(tx('label.ante_bonus'))}</h3><div class="fcp-pays">${paytableRows(ANTE_BONUS_ORDER, rules.ante_bonus_multipliers)}</div></div>`;
  // Build the Aces Up paytable card.
  const acesTable = `<div class="fcp-card"><h3>${safe(tx('label.aces_up'))}</h3><div class="fcp-pays">${paytableRows(ACES_UP_ORDER, rules.aces_up_multipliers)}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${anteBonus}${acesTable}`;
}

// Attach event handlers to the current stage controls.
function bindEvents() {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Stop when teardown released the outlet between render and binding.
  if (!root) return;
  // Bind the ante input to the cached wager.
  const anteInput = root.querySelector('[data-ante]');
  // Update the cached ante on input.
  if (anteInput) anteInput.onchange = () => { ante = normalizedWager(anteInput.value, 1); };
  // Bind the Aces Up input to the cached side bet.
  const acesInput = root.querySelector('[data-aces]');
  // Update the cached Aces Up bet on input, allowing zero.
  if (acesInput) acesInput.onchange = () => { acesUp = normalizedWager(acesInput.value, 0); };
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the one-click repeat that re-opens a round with the previous wagers.
  const repeatButton = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler when the control is present.
  if (repeatButton) repeatButton.onclick = repeat;
  // Bind the fold control to a fold decision.
  const foldButton = root.querySelector('[data-fold]');
  // Attach the fold handler.
  if (foldButton) foldButton.onclick = () => decide('fold', 1);
  // Bind every play control to a play decision at its multiplier.
  root.querySelectorAll('[data-play]').forEach(button => { button.onclick = () => decide('play', Number(button.dataset.play)); });
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
      // Refresh the shell wallet after any settlement.
      await refreshBalance();
    }
  }
}

// Deal one new round after committing the ante and Aces Up wagers.
function deal() {
  // Perform the deal as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved deal id or mint a fresh one bound to the current wagers.
    if (!pendingDealId || pendingDealContext?.ante !== ante || pendingDealContext?.aces_up !== acesUp) {
      // Mint a fresh deal retry id.
      pendingDealId = lifecycle.nextRequestId('deal');
      // Bind the retry id to the exact wagers.
      pendingDealContext = { ante, aces_up: acesUp };
    }
    // Post the exactly-once deal with the current wagers.
    return post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, ante, aces_up: acesUp }));
  }, payload => {
    // Adopt the returned state and reveal the decision stage only for the current mount.
    adoptPayload(payload);
  });
}

// Re-apply the last committed wagers and open one identical round without a timer.
async function repeat() {
  // Read the newest round so an active decision blocks the repeat.
  const round = currentRound();
  // Ignore repeat while busy, unmounted, before any bet exists, or during a pending decision.
  if (lifecycle.isBusy() || !lifecycle.root() || !lastBet || (round && round.phase === 'decision')) return;
  // Restore the committed ante into the cached wager the deal reads.
  ante = lastBet.ante;
  // Restore the committed Aces Up side bet into the cached wager the deal reads.
  acesUp = lastBet.aces_up;
  // Fire the shared deal action with the restored wagers, never replaying a decision.
  await deal();
}

// Apply one play or fold decision to the active round.
function decide(decision, multiplier) {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore decisions when no active round awaits one.
  if (!round || round.phase !== 'decision') return;
  // Perform the decision as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved decision id or mint one bound to this exact decision.
    if (!pendingDecisionId || pendingDecisionContext?.round_id !== round.round_id || pendingDecisionContext?.decision !== decision || pendingDecisionContext?.multiplier !== multiplier) {
      // Mint a fresh decision retry id.
      pendingDecisionId = lifecycle.nextRequestId('decision');
      // Bind the retry id to the exact round and decision.
      pendingDecisionContext = { round_id: round.round_id, decision, multiplier };
    }
    // Post the exactly-once decision to the round-scoped route.
    return post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionId, decision, multiplier }));
  }, payload => {
    // Adopt the settled result only for the current mount.
    adoptPayload(payload);
    // Capture the committed wagers from the settled round so one click can repeat them.
    const settled = currentRound();
    // Remember the ante and Aces Up bet only when the round exposes its committed wagers.
    if (settled && settled.ante !== undefined) lastBet = { ante: settled.ante, aces_up: settled.aces_up };
    // Release the resolved decision retry binding.
    pendingDecisionId = null;
    // Release the resolved decision context.
    pendingDecisionContext = null;
  });
}

// Export the isolated Four Card Poker game for the shared shell.
export const FourCardPokerGame = {
  // Expose the stable catalog identifier.
  id: 'four_card_poker',
  // Expose an empty label because the shell provides the localized catalog label.
  label: '',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable wagers so a new session never inherits a prior bet.
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
    // Read reload-safe state so a pending decision or settled result is restored.
    try {
      // Fetch the current player's game state.
      const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
      // Stop when navigation replaced this mount while state was loading.
      if (!ownsAction(session, node)) return;
      // Adopt the loaded state.
      adoptPayload(payload);
      // Recover the repeatable wagers from the newest round so repeat survives a reload.
      const recovered = currentRound();
      // Restore the committed ante and Aces Up bet only when a prior round exposes them.
      if (recovered && recovered.ante !== undefined) lastBet = { ante: recovered.ante, aces_up: recovered.aces_up };
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
    // Clear the repeatable wagers so the next session starts fresh.
    lastBet = null;
    // Clear any pending retry ids so a later mount starts clean.
    pendingDealId = null;
    // Clear the pending deal context with its retry id.
    pendingDealContext = null;
    // Clear the pending decision id.
    pendingDecisionId = null;
    // Clear the pending decision context with its retry id.
    pendingDecisionContext = null;
  },
};
