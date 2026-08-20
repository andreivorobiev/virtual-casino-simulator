// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Pattern Draw route for GitHub issue #155, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/pattern_draw';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'pd', stylesheet: { id: 'pattern-draw-styles', href: '/games/pattern_draw.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend pattern bets and their multipliers in stable order.
export const BETS = Object.freeze([['line', 1.75], ['cross', 30], ['full', 480]]);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative reveal duration; the outcome is already server-authoritative.
const DRAW_MS = 600;

// Store the chosen bet and stake while the shared lifecycle owns route and busy state.
let selectedBet = 'line';
let stake = 5;
// Retain the last settled grid so a repaint after the draw keeps showing the pattern.
let shownGrid = null;
// Retain the last committed pattern and stake so one click can repeat the same draw.
let lastBet = null;

// Render the complete Pattern Draw route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the nine grid cells, lighting the ones the committed grid turned on.
  const cells = Array.from({ length: 9 }, (unused, index) => `<div class="pd-cell ${shownGrid && shownGrid[index] ? 'on' : ''}" data-testid="pattern-draw-cell-${index}"></div>`).join('');
  // Build the three pattern bet buttons with honest multipliers.
  const bets = BETS.map(([bet, mult]) => `<button class="pd-bet" data-bet="${bet}" type="button" aria-pressed="${selectedBet === bet}"><span>${safe(tx('bet.' + bet))}</span><small>${mult}x</small></button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="pd-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="pattern" data-testid="pattern-draw"><div class="pd-stage"><div class="pd-grid" data-testid="pattern-draw-grid">${cells}</div><p class="pd-result" data-testid="pattern-draw-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="pd-panel"><div class="pd-card"><h3>${safe(tx('bet.title'))}</h3><div class="pd-bets">${bets}</div></div><div class="pd-card"><h3>${safe(tx('stake.title'))}</h3><div class="pd-chips">${chips}</div></div><button class="pd-draw" data-testid="pattern-draw-draw" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.drawing') : tx('action.draw'))}</button><button class="pd-repeat" data-testid="pattern-draw-repeat" type="button" ${(lifecycle.isBusy() || !lastBet) ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the pattern bet buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = btn.dataset.bet; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the draw action.
  const drawBtn = root.querySelector('[data-testid="pattern-draw-draw"]');
  // Attach the draw handler only when a draw is not already running.
  if (drawBtn) drawBtn.onclick = draw;
  // Wire the one-click repeat that re-fires the last committed pattern and stake.
  const repeatBtn = root.querySelector('[data-testid="pattern-draw-repeat"]');
  // Attach the repeat handler so a settled bet can be replayed with one click.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const data = await api('/api/v1/games/pattern-draw/state');
    // Read the newest settled round so repeat can survive a reload.
    const restored = data?.state?.recent_rounds?.[0]?.public;
    // Recover the repeatable pattern and stake only when a settled round is present.
    lastBet = restored ? { bet: restored.detail.bet, stake: restored.wager_total } : null;
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, draw, and settlement.
async function draw() {
  // Ignore repeated clicks while a draw is resolving.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Mark the draw busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once draw with a caller-stable retry id and the chosen pattern.
    const response = await post('/api/v1/games/pattern-draw/draws', { request_id: lifecycle.nextRequestId(), bet: selectedBet, stake });
    // Show the committed debit before the completed grid becomes visible. (LEDGER-031, issue #598)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Reveal the authoritative committed grid so the cells light up.
    shownGrid = round.detail.grid;
    // Remember the exact settled pattern and stake so one click can repeat the same draw.
    lastBet = { bet: round.detail.bet, stake: round.wager_total };
    // Repaint immediately so the drawn grid is visible during the reveal.
    render();
    // Wait for the decorative reveal to finish before announcing the result.
    await new Promise(resolve => setTimeout(resolve, DRAW_MS));
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the pattern hit.
    const win = round.total_return > 0;
    // Compose the localized result copy from the authoritative outcome and net.
    const text = win
      ? `${safe(tx('result.hit', { bet: tx('bet.' + round.detail.bet) }))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.miss'))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the drawn grid and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.draw'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Replay the last committed pattern and stake with one click.
async function repeat() {
  // Ignore repeat while a draw is running or before any prior round has settled.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous pattern selection into the local control state.
  selectedBet = lastBet.bet;
  // Restore the previous stake into the local control state.
  stake = lastBet.stake;
  // Fire the shared draw action with the restored pattern and stake.
  await draw();
}

// Export the isolated Pattern Draw game for the shared shell.
export const PatternDrawGame = {
  // Expose the stable catalog identifier.
  id: 'pattern_draw',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable bet so a new mount never inherits a stale one before load reconciles history.
    lastBet = null;
    // Establish route, stylesheet, locale, and repaint ownership through the shared controller.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation released this route during asynchronous locale loading.
    if (!mounted) return;
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Release route, locale, and busy ownership idempotently.
    lifecycle.unmount();
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
