// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Mississippi Stud browser module for GitHub issue #143 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/mississippi_stud';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/mississippi-stud';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: DOMAIN, requestPrefix: 'ms', stylesheet: { id: 'mississippi-stud-styles', href: '/games/mississippi_stud.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Preserve the paytable order independently of object insertion behavior.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'pair_jacks_plus'];
// Offer the three documented street bet sizes.
const BET_MULTIPLIERS = [1, 2, 3];

// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for paytable displays.
let rules = {};
// Store the configured ante wager before the next round.
let ante = 5;
// Retain the last committed ante so one click can repeat the same round.
let lastBet = null;
// Retain one mount-specific token so a late action response cannot contaminate a later remount of the shared outlet.
let routeSession = null;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealId = null;
// Bind the unresolved deal retry id to one ante.
let pendingDealAnte = null;
// Retain one unresolved decision retry id per street so retries stay stable.
let pendingDecisionId = null;
// Bind the unresolved decision retry id to one round, street, and choice.
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
  const bounded = Math.min(parsed, 10000);
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
function cardRow(titleKey, cards) {
  // Render each card through the shared renderer.
  const rendered = (cards || []).map(card => renderCard(card)).join('');
  // Return one titled card row.
  return `<div class="ms-row"><h4>${safe(tx(titleKey))}</h4><div class="ms-cards">${rendered}</div></div>`;
}

// Render the paytable rows for the to-one hand table.
function paytableRows() {
  // Build one row per listed hand tier present in the authoritative table.
  return PAYTABLE_ORDER.filter(name => rules.paytable && rules.paytable[name] !== undefined).map(name => `<div><span>${safe(tx('hand.' + name))}</span><span>${rules.paytable[name]}:1</span></div>`).join('');
}

// Render the complete Mississippi Stud route into the outlet.
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
  // Hide the duplicate wager card once the settled stage already offers Deal again.
  const panel = sidePanel(deciding || round?.phase === 'settled');
  // Paint the whole route.
  root.innerHTML = `<section class="msstud" data-testid="mississippi-stud"><div class="ms-stage">${stage}</div><div class="ms-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set the ante and deal.
  return `<p class="ms-result" data-testid="mississippi-stud-result">${safe(tx('result.idle'))}</p>`;
}

// Build the decision stage showing the hole cards, revealed community, and bet or fold controls.
function decisionStage(round) {
  // Render the two hole cards.
  const hole = cardRow('label.hole_cards', round.hole_cards);
  // Render the community cards revealed so far.
  const community = cardRow('label.community_cards', round.community_revealed);
  // Build one bet button per multiplier.
  const bets = BET_MULTIPLIERS.map(multiplier => `<button class="ms-btn bet" data-bet="${multiplier}" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.bet', { multiplier }))}</button>`).join('');
  // Return the cards, the street label, and the decision controls.
  return `${hole}${community}<p class="ms-street">${safe(tx('label.street', { street: round.street }))}</p><div class="ms-actions"><button class="ms-btn fold" data-fold="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.fold'))}</button>${bets}</div>`;
}

// Build the secondary one-click repeat control that opens a new round with the last committed ante.
function repeatButton() {
  // Disable repeat while busy, without a stored ante, or while a round is still active.
  const disabled = lifecycle.isBusy() || !lastBet || Boolean(state?.active_round);
  // Return the secondary repeat control rendered after the primary deal button.
  return `<button class="ms-btn ms-repeat" data-repeat="1" type="button" ${disabled ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button>`;
}

// Build the settled stage revealing the completed hand and the result.
function settledStage(round) {
  // Render the two hole cards.
  const hole = cardRow('label.hole_cards', round.hole_cards);
  // Render every revealed community card.
  const community = cardRow('label.community_cards', round.community_revealed);
  // Read the settled net movement.
  const net = round.net || 0;
  // Compose the outcome and hand tier line.
  const tier = round.hand_tier ? safe(tx('hand.' + round.hand_tier)) : '';
  // Build the outcome result line with a signed net amount.
  const line = `${safe(tx('outcome.' + round.outcome))} ${tier} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Return the revealed hand, the result, and a deal-again control with a one-click repeat.
  return `${hole}${community}<p class="ms-result" data-testid="mississippi-stud-result">${line}</p><div class="ms-actions"><button class="ms-btn deal" data-deal="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.deal_again'))}</button>${repeatButton()}</div>`;
}

// Build the side panel with the ante input and the paytable.
function sidePanel(hideWager) {
  // Hide the ante input while a decision is pending or the settled stage owns the replay action.
  const wagerCard = hideWager ? '' : `<div class="ms-card"><h3>${safe(tx('label.ante'))}</h3><div class="ms-field"><label for="ms-ante">${safe(tx('label.ante'))}</label><input id="ms-ante" data-ante type="number" min="1" step="1" value="${ante}"></div><button class="ms-btn deal" data-deal="1" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(tx('action.deal'))}</button>${repeatButton()}</div>`;
  // Build the paytable card.
  const paytable = `<div class="ms-card"><h3>${safe(tx('label.paytable'))}</h3><div class="ms-pays">${paytableRows()}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${paytable}`;
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
  if (anteInput) anteInput.onchange = () => { ante = normalizedAnte(anteInput.value); };
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the one-click repeat control to reopen a round with the last committed ante.
  const repeatBtn = root.querySelector('[data-repeat]');
  // Attach the repeat handler when the control is present.
  if (repeatBtn) repeatBtn.onclick = repeat;
  // Bind the fold control to a fold decision.
  const foldButton = root.querySelector('[data-fold]');
  // Attach the fold handler.
  if (foldButton) foldButton.onclick = () => decide('fold', 1);
  // Bind every bet control to a bet decision at its multiplier.
  root.querySelectorAll('[data-bet]').forEach(button => { button.onclick = () => decide('bet', Number(button.dataset.bet)); });
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
    // Capture the committed ante after a successful settle so one click can repeat the same round.
    const settledRound = currentRound();
    // Remember the ante only when the newest round has settled, never during an open decision.
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
    // Adopt the returned state and reveal the first street only for the current mount.
    adoptPayload(payload);
  });
}

// Re-apply the last committed ante and open one identical round without replaying any street decision.
async function repeat() {
  // Ignore repeat while busy, mid-retry, without a stored ante, or during an active round.
  if (lifecycle.isBusy() || pendingDealId || pendingDecisionId || !lastBet || state?.active_round) return;
  // Restore the committed ante so the shared deal path reads the repeated stake.
  ante = normalizedAnte(lastBet.ante);
  // Open one identical round through the shared deal action, never replaying a bet or fold.
  await deal();
}

// Apply one bet or fold decision to the active round's current street.
function decide(decision, multiplier) {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore decisions when no active round awaits one.
  if (!round || round.phase !== 'decision') return;
  // Perform the decision as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved decision id or mint one bound to this exact street decision.
    if (!pendingDecisionId || pendingDecisionContext?.round_id !== round.round_id || pendingDecisionContext?.street !== round.street || pendingDecisionContext?.decision !== decision || pendingDecisionContext?.multiplier !== multiplier) {
      // Mint a fresh decision retry id.
      pendingDecisionId = lifecycle.nextRequestId('decision');
      // Bind the retry id to the exact round, street, and decision.
      pendingDecisionContext = { round_id: round.round_id, street: round.street, decision, multiplier };
    }
    // Post the exactly-once decision to the round-scoped route.
    return post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionId, decision, multiplier }));
  }, payload => {
    // Adopt the advanced or settled result only for the current mount.
    adoptPayload(payload);
    // Release the resolved decision retry binding so the next street mints a new id.
    pendingDecisionId = null;
    // Release the resolved decision context.
    pendingDecisionContext = null;
  });
}

// Export the isolated Mississippi Stud game for the shared shell.
export const MississippiStudGame = {
  // Expose the stable catalog identifier.
  id: 'mississippi_stud',
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
    // Read reload-safe state so a pending street or settled result is restored.
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
