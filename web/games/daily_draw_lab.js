// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Daily Draw Lab route for GitHub issue #144, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, style, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/daily_draw_lab';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'dd', stylesheet: { id: 'daily-draw-lab-styles', href: '/games/daily_draw_lab.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend number pool size.
export const POOL = 30;
// Mirror the backend maximum pick count.
export const MAX_PICKS = 5;
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative reveal duration; the outcome is already server-authoritative.
const DRAW_MS = 700;

// Store the marked numbers and chosen stake while the shared lifecycle owns route and busy state.
let picks = [];
let stake = 5;
// Retain the last settled draw so a repaint keeps showing drawn numbers and hits.
let shownDraw = null;
// Retain the last committed picks and stake so one click can repeat the same draw.
let lastBet = null;

// Toggle a number in or out of the current marks, bounded to the maximum pick count.
function toggleMark(number) {
  // Remove a number that is already marked.
  if (picks.includes(number)) picks = picks.filter(n => n !== number);
  // Add a new number only while fewer than the maximum are marked.
  else if (picks.length < MAX_PICKS) picks = [...picks, number];
  // Clear any prior draw so re-marking starts a fresh board.
  shownDraw = null;
  // Repaint the updated selection.
  render();
}

// Compute the visual class for one number cell from marks and any settled draw.
function numClass(number) {
  // Highlight a marked number the draw hit.
  if (shownDraw && shownDraw.hit.includes(number)) return 'hit';
  // Show a drawn number the player did not mark.
  if (shownDraw && shownDraw.drawn.includes(number)) return 'drawn';
  // Otherwise leave the cell to its pressed-mark styling.
  return '';
}

// Render the current pick count's paytable rows.
function paytableRows() {
  // Read the paytable for the current pick count, or an empty prompt before any mark.
  const table = { 1: [[1, 5.5]], 2: [[2, 15], [1, 2]], 3: [[3, 100], [2, 8], [1, 0.5]], 4: [[4, 600], [3, 40], [2, 4]], 5: [[5, 10000], [4, 200], [3, 18], [2, 2]] }[picks.length] || [];
  // Build one row per paying hit count.
  return table.map(([hits, mult]) => `<div><span>${safe(tx('pay.hits', { count: hits }))}</span><span>${mult}x</span></div>`).join('') || `<div>${safe(tx('pay.empty'))}</div>`;
}

// Render the complete Daily Draw Lab route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the thirty number cells, marking picks, draws, and hits.
  const nums = Array.from({ length: POOL }, (unused, index) => index + 1).map(number => `<button class="dd-num ${numClass(number)}" data-number="${number}" type="button" aria-pressed="${picks.includes(number)}">${number}</button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="dd-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Report the mark hint.
  const hint = tx('pick.hint', { count: picks.length });
  // Paint the whole route.
  root.innerHTML = `<section class="daily" data-testid="daily-draw-lab"><div class="dd-stage"><div class="dd-board" data-testid="daily-draw-lab-board">${nums}</div><p class="dd-result" data-testid="daily-draw-lab-result" role="status">${resultText || safe(hint)}</p></div><div class="dd-panel"><div class="dd-card"><h3>${safe(tx('pay.title'))}</h3><div class="dd-pays">${paytableRows()}</div></div><div class="dd-card"><h3>${safe(tx('stake.title'))}</h3><div class="dd-chips">${chips}</div></div><button class="dd-go" data-testid="daily-draw-lab-go" type="button" ${lifecycle.isBusy() || picks.length < 1 ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.drawing') : tx('action.draw'))}</button><button class="dd-repeat" data-testid="daily-draw-lab-repeat" type="button" ${lifecycle.isBusy() || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the number mark buttons.
  root.querySelectorAll('[data-number]').forEach(btn => { btn.onclick = () => { if (!lifecycle.isBusy()) toggleMark(Number(btn.dataset.number)); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the draw action.
  const goBtn = root.querySelector('[data-testid="daily-draw-lab-go"]');
  // Attach the draw handler only when at least one number is marked.
  if (goBtn) goBtn.onclick = run;
  // Wire the one-click repeat that re-fires the last committed picks and stake.
  const repeatBtn = root.querySelector('[data-testid="daily-draw-lab-repeat"]');
  // Attach the repeat handler; the button stays disabled until a prior draw settles.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const data = await api('/api/v1/games/daily-draw-lab/state');
    // Read the compact newest-first recent-round history retained per player.
    const rounds = data?.state?.recent_rounds || [];
    // Recover a repeatable bet from the newest settled round so repeat survives a reload.
    if (rounds.length && rounds[0]?.public?.wager) lastBet = { picks: [...rounds[0].public.wager.picks], stake: rounds[0].public.wager.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, draw, and settlement.
async function run() {
  // Ignore repeated clicks, teardown, or an empty mark set through shared lifecycle state.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || picks.length < 1) return;
  // Mark the draw busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once draw with a caller-stable retry id and the marked numbers.
    const response = await post('/api/v1/games/daily-draw-lab/draws', { request_id: lifecycle.nextRequestId(), picks: [...picks], stake });
    // Show the committed debit before the draw exposes its authoritative numbers. (LEDGER-031, issue #593)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Reveal the authoritative committed draw and hits.
    shownDraw = round.detail;
    // Remember the exact committed picks and stake so one click can repeat the same draw.
    lastBet = { picks: [...round.wager.picks], stake: round.wager.stake };
    // Repaint immediately so the drawn numbers and hits show during the reveal.
    render();
    // Wait for the decorative reveal to finish before announcing the result.
    await new Promise(resolve => setTimeout(resolve, DRAW_MS));
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Treat only a net profit as a win; a small consolation that returns less than the stake still nets a loss.
    const netPositive = round.net > 0;
    // Format the net with an explicit sign so a consolation never renders a double sign.
    const netText = round.net >= 0 ? '+' + round.net : String(round.net);
    // Compose the localized result copy from the authoritative hit count and signed net.
    const text = netPositive
      ? `${safe(tx('result.win', { count: round.detail.hit_count }))} <span class="net">${netText}</span>`
      : `${safe(tx('result.lose', { count: round.detail.hit_count }))} <span class="net">${netText}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the drawn board and result.
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

// Re-apply the last committed picks and stake and re-fire one draw without a timer.
async function repeat() {
  // Ignore repeat while a draw is active, after teardown, or before any prior draw has settled.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous marks into the local selection.
  picks = [...lastBet.picks];
  // Restore the previous stake into the local selection.
  stake = lastBet.stake;
  // Fire the shared exactly-once draw action with the restored picks and stake.
  await run();
}

// Export the isolated Daily Draw Lab game for the shared shell.
export const DailyDrawLabGame = {
  // Expose the stable catalog identifier.
  id: 'daily_draw_lab',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the marks for a fresh mount.
    picks = [];
    // Reset the repeatable bet so a new mount never inherits a stale one before load reconciles history.
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
