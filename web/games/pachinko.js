// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Pachinko route for GitHub issue #142, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, style, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/pachinko';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'pk', stylesheet: { id: 'pachinko-styles', href: '/games/pachinko.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend's twelve pin rows.
export const ROWS = 12;
// Mirror the backend's thirteen pocket multipliers in pocket order.
export const POCKETS = Object.freeze([100, 15, 4, 2, 1, 0.5, 0.3, 0.5, 1, 2, 4, 15, 100]);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative per-row fall step; the outcome is already server-authoritative.
const STEP_MS = 70;

// Store the chosen stake while the shared lifecycle owns route and busy state.
let stake = 5;
// Retain the last landed pocket so a repaint after the drop keeps highlighting it.
let landedPocket = null;
// Retain the last committed stake so one click can repeat the same drop.
let lastBet = null;

// Choose a compact CSS class for a pocket by how richly it pays.
function pocketClass(multiplier) {
  // Mark jackpot, winning, even, and losing pockets so the board reads at a glance.
  return multiplier >= 15 ? 'jackpot' : multiplier > 1 ? 'win' : multiplier === 1 ? 'even' : 'low';
}

// Build the decorative pin field markup as evenly spaced dots per row.
function pins() {
  // Accumulate one row of pins per pin row.
  const dots = [];
  // Place a triangular pin lattice so the ball visibly bounces between pins.
  for (let row = 0; row < ROWS; row++) {
    // Compute this row's vertical position as a percentage of the board height.
    const top = 8 + (row / ROWS) * 78;
    // Place one more pin than the row index, centred horizontally.
    for (let i = 0; i <= row + 1; i++) {
      // Compute this pin's horizontal position centred around the middle.
      const left = 50 + (i - (row + 1) / 2) * (74 / (ROWS + 1));
      // Append one positioned pin.
      dots.push(`<span class="pk-pin" style="top:${top}%;left:${left}%;"></span>`);
    }
  }
  // Return the full pin lattice.
  return dots.join('');
}

// Render the complete Pachinko route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the thirteen pockets, marking the last landed pocket.
  const pockets = POCKETS.map((mult, index) => `<div class="pk-pocket ${pocketClass(mult)} ${landedPocket === index ? 'hit' : ''}" data-testid="pachinko-pocket-${index}">${mult}x</div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="pk-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route with the ball parked at the top centre.
  root.innerHTML = `<section class="pachinko" data-testid="pachinko"><div class="pk-stage"><div class="pk-board" data-testid="pachinko-board">${pins()}<div class="pk-ball" data-testid="pachinko-ball" style="top:2%;left:50%;"></div></div><div class="pk-pockets">${pockets}</div><p class="pk-result" data-testid="pachinko-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="pk-panel"><div class="pk-card"><h3>${safe(tx('stake.title'))}</h3><div class="pk-chips">${chips}</div></div><button class="pk-drop" data-testid="pachinko-drop" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.dropping') : tx('action.drop'))}</button><button class="pk-repeat" data-testid="pachinko-repeat" type="button" ${lifecycle.isBusy() || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the drop action.
  const dropBtn = root.querySelector('[data-testid="pachinko-drop"]');
  // Attach the drop handler only when a drop is not already running.
  if (dropBtn) dropBtn.onclick = drop;
  // Read the secondary one-click repeat control.
  const repeatBtn = root.querySelector('[data-testid="pachinko-repeat"]');
  // Attach the repeat handler only when a prior stake can be re-fired.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Animate the ball down the committed path so the visible landing matches the server pocket.
async function animate(path) {
  // Read the ball element to move down the board.
  const ball = lifecycle.root()?.querySelector('[data-testid="pachinko-ball"]');
  // Skip the animation when the ball is not present.
  if (!ball) return;
  // Track the running horizontal offset in pin steps from centre.
  let offset = 0;
  // Step the ball down one pin row at a time following the committed bounces.
  for (let row = 0; row < path.length; row++) {
    // Move right or left by half a pin spacing per bounce.
    offset += path[row] === 'R' ? 0.5 : -0.5;
    // Position the ball at this row's height and accumulated offset.
    ball.style.top = `${8 + (row / ROWS) * 82}%`;
    ball.style.left = `${50 + offset * (74 / (ROWS + 1))}%`;
    // Wait one step so each bounce is visible.
    await new Promise(resolve => setTimeout(resolve, STEP_MS));
  }
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const payload = await api('/api/v1/games/pachinko/state');
    // Recover a repeatable stake from the newest settled drop so repeat survives a reload.
    const restored = payload?.state?.recent_rounds?.[0]?.public;
    // Restore the repeatable stake only when a settled drop is present.
    if (restored?.wager?.stake) lastBet = { stake: restored.wager.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, drop, and settlement.
async function drop() {
  // Ignore repeated clicks while a drop is resolving.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Clear any previous landed pocket and mark the drop busy before the request.
  landedPocket = null;
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once drop with a caller-stable retry id.
    const response = await post('/api/v1/games/pachinko/drops', { request_id: lifecycle.nextRequestId(), stake });
    // Show the committed debit before the ball reaches its authoritative pocket. (LEDGER-031, issue #597)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Animate the ball down the committed path so the visible landing is honest.
    await animate(round.detail.path);
    // Reveal the authoritative landed pocket.
    landedPocket = round.detail.pocket;
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Remember the settled stake so the next drop can repeat it with one click.
    lastBet = { stake };
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from authoritative values only.
    const text = `${safe(tx('result.landed', { mult: round.detail.multiplier }))} <span class="net">${net > 0 ? '+' + net : net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the landed pocket highlighted and the result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.drop'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last committed stake and re-fire one drop without a timer.
async function repeat() {
  // Ignore repeat while a drop is resolving or before any settled drop exists.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared drop action with the restored stake.
  await drop();
}

// Export the isolated Pachinko game for the shared shell.
export const PachinkoGame = {
  // Expose the stable catalog identifier.
  id: 'pachinko',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable stake so another session never inherits it.
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
