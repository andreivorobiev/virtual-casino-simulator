// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Teen Patti Practice browser module for GitHub issue #150 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/teen_patti';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/teen-patti';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: DOMAIN, requestPrefix: 'tp', stylesheet: { id: 'teen-patti-styles', href: '/games/teen_patti.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Preserve the Bonus paytable order independently of object insertion behavior.
const BONUS_ORDER = ['trail', 'pure_sequence', 'sequence'];
// Preserve the strongest-first hand ranking for the reference display.
const RANK_ORDER = ['trail', 'pure_sequence', 'sequence', 'color', 'pair', 'high_card'];

// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for the paytable displays.
let rules = {};
// Store the configured ante before the next round.
let ante = 5;
// Retain the last committed ante so one click can repeat the same round.
let lastBet = null;
// Retain one mount-specific token so a late action response cannot contaminate a later remount of the shared outlet.
let routeSession = null;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealId = null;
// Bind the unresolved deal retry id to one ante.
let pendingDealAnte = null;
// Retain an unresolved decision retry id bound to one round and choice.
let pendingDecisionId = null;
// Bind the unresolved decision retry id to one round and its decision.
let pendingDecisionContext = null;

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

// Normalize an ante to the ledger-compatible bounds.
function normalizedAnte(value) {
  // Convert browser input text to a numeric wager.
  const parsed = Number(value);
  // Return the lower bound for invalid or undersized values.
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  // Clamp oversized browser values to the public contract maximum.
  const bounded = Math.min(parsed, 50000);
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
    // Release the resolved deal ante.
    pendingDealAnte = null;
  }
}

// Build the markup for one labelled row of cards.
function cardRow(titleKey, cards, win = false) {
  // Render each card through the shared renderer.
  const rendered = (cards || []).map(card => renderCard(card)).join('');
  // Return one titled card row.
  return `<div class="tp-row"><h4>${safe(tx(titleKey))}</h4><div class="tp-cards ${win ? 'win' : ''}">${rendered}</div></div>`;
}

// Render the Bonus paytable rows.
function bonusRows() {
  // Build one row per listed Bonus tier present in the authoritative table.
  return BONUS_ORDER.filter(name => rules.bonus_multipliers && rules.bonus_multipliers[name] !== undefined).map(name => `<div><span>${safe(tx('hand.' + name))}</span><span>${rules.bonus_multipliers[name]}:1</span></div>`).join('');
}

// Render the strongest-first hand ranking reference.
function rankingRows() {
  // Join the localized ranking names in strongest-first order.
  return RANK_ORDER.map((name, index) => `${index + 1}. ${safe(tx('hand.' + name))}`).join('<br>');
}

// Render the complete Teen Patti route into the outlet.
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
  // Build the side panel with wager input and paytables.
  const panel = sidePanel(deciding);
  // Paint the whole route.
  root.innerHTML = `<section class="teenp" data-testid="teen-patti"><div class="tp-stage">${stage}</div><div class="tp-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set the ante and deal.
  return `<p class="tp-result" data-testid="teen-patti-result" role="status" aria-live="polite">${safe(tx('result.idle'))}</p>`;
}

// Build the decision stage showing the player's three cards and the play or fold controls.
function decisionStage(round) {
  // Render the three player cards.
  const cards = cardRow('label.your_cards', round.player_cards);
  // Return the cards, the prompt, and the decision controls.
  return `${cards}<p class="tp-result" role="status" aria-live="polite">${safe(tx('result.decide'))}</p><div class="tp-actions"><button class="tp-btn fold" data-fold="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.fold'))}</button><button class="tp-btn play" data-play="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.play'))}</button></div>`;
}

// Build the settled stage revealing both hands and the result.
function settledStage(round) {
  // Render the player's revealed hand, highlighting a win.
  const win = round.outcome === 'player_win' || round.outcome === 'dealer_not_qualified';
  // Render the player's three cards.
  const player = cardRow('label.your_cards', round.player_cards, win);
  // Render the dealer's revealed cards when a showdown happened.
  const dealer = round.dealer_cards ? cardRow('label.dealer_cards', round.dealer_cards) : '';
  // Read the settled net movement.
  const net = round.net || 0;
  // Read the localized hand tier for the player.
  const tier = round.player_hand ? safe(tx('hand.' + round.player_hand.name)) : '';
  // Build the outcome result line with a signed net amount.
  const line = `${safe(tx('outcome.' + round.outcome))} ${tier} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Return the revealed hands and result while the single wager-panel deal action remains authoritative.
  return `${player}${dealer}<p class="tp-result" data-testid="teen-patti-result" role="status" aria-live="polite">${line}</p>`;
}

// Build the side panel with the ante input and paytables.
function sidePanel(deciding) {
  // Enable the one-click repeat only outside a decision with a stored ante and nothing in flight.
  const repeatDisabled = lifecycle.isBusy() || !lastBet || Boolean(state?.active_round);
  // Hide the ante input while a decision is pending.
  const wagerCard = deciding ? '' : `<div class="tp-card"><h3>${safe(tx('label.ante'))}</h3><div class="tp-field"><label for="tp-ante">${safe(tx('label.ante'))}</label><input id="tp-ante" data-ante type="number" min="1" step="1" value="${ante}"></div><button class="tp-btn deal" data-deal="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.deal'))}</button><button class="tp-btn tp-repeat" data-repeat="1" type="button" ${repeatDisabled ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div>`;
  // Build the Bonus paytable card.
  const bonus = `<div class="tp-card"><h3>${safe(tx('label.bonus'))}</h3><div class="tp-pays">${bonusRows()}</div></div>`;
  // Build the ranking reference card.
  const ranking = `<div class="tp-card"><h3>${safe(tx('label.ranking'))}</h3><div class="tp-rank">${rankingRows()}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${bonus}${ranking}`;
}

// Attach event handlers to the current stage controls.
function bindEvents() {
  // Read the current outlet because teardown may run between render and binding.
  const root = lifecycle.root();
  // Stop when teardown already released the route.
  if (!root) return;
  // Bind the ante input to the cached wager.
  const anteInput = root.querySelector('[data-ante]');
  // Update the cached ante on input.
  if (anteInput) anteInput.onchange = () => { ante = normalizedAnte(anteInput.value); };
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the one-click repeat that re-opens a round with the previous ante.
  const repeatButton = root.querySelector('[data-repeat]');
  // Attach the repeat handler when the non-decision control is present.
  if (repeatButton) repeatButton.onclick = repeat;
  // Bind the fold control to a fold decision.
  const foldButton = root.querySelector('[data-fold]');
  // Attach the fold handler.
  if (foldButton) foldButton.onclick = () => decide('fold');
  // Bind the play control to a play decision.
  const playButton = root.querySelector('[data-play]');
  // Attach the play handler.
  if (playButton) playButton.onclick = () => decide('play');
}

// Report whether one asynchronous action still belongs to the exact mounted route session.
function ownsAction(session, root) {
  // Require both the game-specific session token and lifecycle-owned outlet to remain unchanged.
  return routeSession === session && lifecycle.root() === root;
}

// Run one guarded atomic action while blocking overlapping requests and deferring response adoption until ownership is rechecked.
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
    // Read the round the completed action produced.
    const settledRound = currentRound();
    // Remember the committed ante only after a round reaches settlement so one click can repeat it.
    if (settledRound && settledRound.phase === 'settled') lastBet = { ante: settledRound.ante };
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

// Deal one new round after committing the ante.
function deal() {
  // Perform the deal as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved deal id or mint a fresh one bound to the current ante.
    if (!pendingDealId || pendingDealAnte !== ante) {
      // Mint a fresh deal retry id.
      pendingDealId = lifecycle.nextRequestId('deal');
      // Bind the retry id to the exact ante.
      pendingDealAnte = ante;
    }
    // Post the exactly-once deal with the current ante.
    return post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, ante }));
  }, payload => {
    // Adopt the returned state and reveal the decision stage only for the current mount.
    adoptPayload(payload);
  });
}

// Re-apply the last committed ante and open one identical round without a timer.
async function repeat() {
  // Ignore repeat while busy, mid deal or decision retry, without a stored ante, or during an active round.
  if (lifecycle.isBusy() || pendingDealId || pendingDecisionId || !lastBet || state?.active_round) return;
  // Restore the previous ante so the shared deal path reads the repeated stake.
  ante = normalizedAnte(lastBet.ante);
  // Read the ante input from the current frame to mirror the restored stake.
  const anteInput = lifecycle.root()?.querySelector('[data-ante]');
  // Reflect the restored ante in the enabled control before dealing.
  if (anteInput) anteInput.value = String(ante);
  // Open one identical round through the shared deal action, never replaying play or fold.
  await deal();
}

// Apply one play or fold decision to the active round.
function decide(decision) {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore decisions when no active round awaits one.
  if (!round || round.phase !== 'decision') return;
  // Perform the decision as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved decision id or mint one bound to this exact decision.
    if (!pendingDecisionId || pendingDecisionContext?.round_id !== round.round_id || pendingDecisionContext?.decision !== decision) {
      // Mint a fresh decision retry id.
      pendingDecisionId = lifecycle.nextRequestId('decision');
      // Bind the retry id to the exact round and decision.
      pendingDecisionContext = { round_id: round.round_id, decision };
    }
    // Post the exactly-once decision to the round-scoped route.
    return post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionId, decision }));
  }, payload => {
    // Adopt the settled result only for the current mount.
    adoptPayload(payload);
    // Release the resolved decision retry binding.
    pendingDecisionId = null;
    // Release the resolved decision context.
    pendingDecisionContext = null;
  });
}

// Export the isolated Teen Patti game for the shared shell.
export const TeenPattiGame = {
  // Expose the stable catalog identifier.
  id: 'teen_patti',
  // Expose an empty label because the shell provides the localized catalog label.
  label: '',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable ante so a new session never inherits a prior bet.
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
      // Recover a repeatable ante from the newest settled round so repeat survives a reload.
      const recovered = state?.recent_rounds?.slice(-1)[0];
      // Restore the repeatable ante only when a prior settled round exposes its committed ante.
      if (recovered?.phase === 'settled' && recovered.ante != null) lastBet = { ante: Number(recovered.ante) };
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
    // Clear the repeatable ante so the next session starts fresh.
    lastBet = null;
    // Clear any pending retry ids so a later mount starts clean.
    pendingDealId = null;
    // Clear the pending deal context with its retry id.
    pendingDealAnte = null;
    // Clear the pending decision id.
    pendingDecisionId = null;
    // Clear the pending decision context with its retry id.
    pendingDecisionContext = null;
  },
};
