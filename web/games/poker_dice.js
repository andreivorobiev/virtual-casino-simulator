// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Poker Dice route for GitHub issue #151, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, style, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/poker_dice';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'pd', stylesheet: { id: 'poker-dice-styles', href: '/games/poker_dice.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend's six poker-rank faces in ascending order for display.
export const FACES = Object.freeze(['9', '10', 'J', 'Q', 'K', 'A']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Mirror the backend paytable in descending hand order for an honest render.
export const PAYTABLE = Object.freeze([['five_of_a_kind', 80], ['four_of_a_kind', 15], ['full_house', 5], ['straight', 4], ['three_of_a_kind', 2]]);
// Fix the decorative roll duration; the outcome is already server-authoritative.
const ROLL_MS = 900;

// Store the chosen stake while the shared lifecycle owns route and busy state.
let stake = 5;
// Retain the last settled faces so a repaint after the roll keeps showing the result.
let shownFaces = ['9', '9', '9', '9', '9'];
// Retain the last committed stake so one click can repeat the same wager.
let lastBet = null;

// Render the complete Poker Dice route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the five dice faces, tumbling while a roll is resolving.
  const dice = shownFaces.map(face => `<div class="pd-die${lifecycle.isBusy() ? ' rolling' : ''}" data-testid="poker-dice-die">${safe(face)}</div>`).join('');
  // Build the honest paytable rows from the mirrored backend table.
  const pays = PAYTABLE.map(([hand, mult]) => `<div class="pd-payrow"><span>${safe(tx('hand.' + hand))}</span><span>${mult}x</span></div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="pd-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Enable the one-click repeat only when a prior stake exists and no roll is resolving.
  const repeatDisabled = lifecycle.isBusy() || !lastBet;
  // Paint the whole route.
  root.innerHTML = `<section class="poker-dice" data-testid="poker-dice"><div class="pd-stage"><div class="pd-dice">${dice}</div><p class="pd-result" data-testid="poker-dice-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="pd-panel"><div class="pd-card"><h3>${safe(tx('paytable.title'))}</h3><div class="pd-paytable">${pays}</div></div><div class="pd-card"><h3>${safe(tx('stake.title'))}</h3><div class="pd-chips">${chips}</div></div><button class="pd-roll" data-testid="poker-dice-roll" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.rolling') : tx('action.roll'))}</button><button class="pd-repeat" data-testid="poker-dice-repeat" type="button" ${repeatDisabled ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the roll action.
  const rollBtn = root.querySelector('[data-testid="poker-dice-roll"]');
  // Attach the roll handler only when a roll is not already running.
  if (rollBtn) rollBtn.onclick = roll;
  // Wire the one-click repeat that re-fires the previous stake.
  const repeatBtn = root.querySelector('[data-testid="poker-dice-repeat"]');
  // Attach the repeat handler; it self-guards on busy state and a missing prior stake.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const response = await api('/api/v1/games/poker-dice/state');
    // Recover the newest settled round so repeat survives a reload.
    const recovered = response?.state?.recent_rounds?.[0]?.public;
    // Restore the repeatable stake only when a prior round exposes its committed total.
    if (recovered?.wager_total) lastBet = { stake: Number(recovered.wager_total) };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, roll, and settlement.
async function roll() {
  // Ignore repeated clicks or teardown through shared lifecycle state.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Mark the roll busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once roll with a caller-stable retry id.
    const response = await post('/api/v1/games/poker-dice/rolls', { request_id: lifecycle.nextRequestId(), stake });
    // Show the committed debit before the authoritative dice hand appears. (LEDGER-031, issue #599)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative tumble to finish before revealing the faces.
    await new Promise(resolve => setTimeout(resolve, ROLL_MS));
    // Reveal the authoritative faces.
    shownFaces = round.detail.faces;
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the round paid.
    const win = round.total_return > 0;
    // Compose the localized result copy from authoritative values only.
    const handName = tx('hand.' + round.detail.hand);
    // Build the result line naming the hand and the net.
    const text = win
      ? `${safe(tx('result.win', { hand: handName }))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.lose'))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Remember the settled stake so the next roll can repeat it with one click.
    lastBet = { stake };
    // Repaint with the settled faces and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.roll'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last committed stake and re-fire one roll without a timer.
async function repeat() {
  // Ignore repeat while a roll is resolving, after teardown, or before any stake has been committed.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once roll action with the restored stake.
  await roll();
}

// Export the isolated Poker Dice game for the shared shell.
export const PokerDiceGame = {
  // Expose the stable catalog identifier.
  id: 'poker_dice',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable stake so a new session never inherits a prior bet.
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
    // Clear the repeatable stake so the next session starts fresh.
    lastBet = null;
  },
};
