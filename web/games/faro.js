// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Faro route for GitHub issue #146, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, style, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/faro';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'fr', stylesheet: { id: 'faro-styles', href: '/games/faro.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend's thirteen ranks in ascending faro order.
export const RANKS = Object.freeze(['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative deal duration; the outcome is already server-authoritative.
const DEAL_MS = 700;

// Store the chosen rank and stake while the shared lifecycle owns route and busy state.
let selectedRank = 1;
let stake = 5;
// Retain the last dealt cards so a repaint after the deal keeps showing the result.
let shownCards = null;
// Retain the last settled rank and stake so one click can repeat the same bet.
let lastBet = null;

// Render the complete Faro route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the dealt card faces or neutral placeholders before the first deal.
  const banker = shownCards ? shownCards.banker : '?';
  const player = shownCards ? shownCards.player : '?';
  // Build the thirteen rank cells.
  const ranks = RANKS.map((label, index) => `<button class="fr-rank" data-rank="${index + 1}" type="button" aria-pressed="${selectedRank === index + 1}">${safe(label)}</button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="fr-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="faro" data-testid="faro"><div class="fr-stage"><div class="fr-cards"><div class="fr-slot"><span>${safe(tx('card.banker'))}</span><div class="fr-card${lifecycle.isBusy() ? ' dealing' : ''}" data-testid="faro-banker">${safe(banker)}</div></div><div class="fr-slot"><span>${safe(tx('card.player'))}</span><div class="fr-card${lifecycle.isBusy() ? ' dealing' : ''}" data-testid="faro-player">${safe(player)}</div></div></div><div class="fr-ranks">${ranks}</div><p class="fr-result" data-testid="faro-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="fr-panel"><div class="fr-card-box"><h3>${safe(tx('odds.title'))}</h3><div class="fr-odds"><div><span>${safe(tx('odds.win'))}</span><span>2x</span></div><div><span>${safe(tx('odds.push'))}</span><span>1x</span></div><div><span>${safe(tx('odds.split'))}</span><span>0.5x</span></div><div><span>${safe(tx('odds.lose'))}</span><span>0x</span></div></div></div><div class="fr-card-box"><h3>${safe(tx('stake.title'))}</h3><div class="fr-chips">${chips}</div></div><button class="fr-deal" data-testid="faro-deal" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.dealing') : tx('action.deal'))}</button><button class="fr-repeat" data-testid="faro-repeat" type="button" ${lifecycle.isBusy() || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the rank cells.
  root.querySelectorAll('[data-rank]').forEach(btn => { btn.onclick = () => { selectedRank = Number(btn.dataset.rank); render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the deal action.
  const dealBtn = root.querySelector('[data-testid="faro-deal"]');
  // Attach the deal handler only when a deal is not already running.
  if (dealBtn) dealBtn.onclick = deal;
  // Wire the one-click repeat that re-fires the previous bet.
  const repeatBtn = root.querySelector('[data-testid="faro-repeat"]');
  // Attach the repeat handler; the disabled attribute already gates busy and no-prior-bet states.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const payload = await api('/api/v1/games/faro/state');
    // Read the newest-first retained rounds so a repeatable bet can survive a reload.
    const restored = payload?.state?.recent_rounds?.[0]?.public?.wager;
    // Recover the repeatable rank and stake only when a settled round is present.
    if (restored) lastBet = { rank: restored.rank, stake: restored.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, deal, and settlement.
async function deal() {
  // Ignore repeated clicks or teardown through shared lifecycle state.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Mark the deal busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once deal with a caller-stable retry id and the chosen rank.
    const response = await post('/api/v1/games/faro/deals', { request_id: lifecycle.nextRequestId(), rank: selectedRank, stake });
    // Show the committed debit before the banker and player cards are revealed. (LEDGER-031, issue #594)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative deal to finish before revealing the cards.
    await new Promise(resolve => setTimeout(resolve, DEAL_MS));
    // Reveal the authoritative dealt cards.
    shownCards = { banker: round.detail.banker, player: round.detail.player };
    // Remember the settled rank and stake so one click can repeat the same bet.
    lastBet = { rank: selectedRank, stake };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from the authoritative outcome and net.
    const text = `${safe(tx('outcome.' + round.outcome))} <span class="net">${net > 0 ? '+' + net : net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the dealt cards and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.deal'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last settled bet and re-fire one deal without a timer.
async function repeat() {
  // Ignore repeat while a deal resolves, after teardown, or before any settled bet.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previously settled rank into the local configuration.
  selectedRank = lastBet.rank;
  // Restore the previously settled stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once deal action with the restored bet.
  await deal();
}

// Export the isolated Faro game for the shared shell.
export const FaroGame = {
  // Expose the stable catalog identifier.
  id: 'faro',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset any repeatable bet so a new mount never inherits a stale one before load recovers history.
    lastBet = null;
    // Establish shared route, stylesheet, localization, and locale-subscription ownership.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation released the route during asynchronous locale initialization.
    if (!mounted) return;
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Release route, locale-subscription, and in-flight lifecycle ownership.
    lifecycle.unmount();
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
