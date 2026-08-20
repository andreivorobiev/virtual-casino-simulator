// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Lucky Grid route for GitHub issue #153, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/lucky_grid';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'lg', stylesheet: { id: 'lucky-grid-styles', href: '/games/lucky_grid.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend board size and required pick count.
export const CELLS = 9;
// Require exactly this many picks before a reveal is allowed.
export const PICKS = 3;
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative reveal duration; the outcome is already server-authoritative.
const REVEAL_MS = 600;

// Store the chosen cells and stake while the shared lifecycle owns route state.
let picks = [];
let stake = 5;
// Retain the last settled reveal so a repaint keeps showing prizes and matches.
let shownReveal = null;
// Retain the last committed picks and stake so one click can repeat the same reveal.
let lastBet = null;

// Toggle a cell in or out of the current picks, bounded to the pick count.
function togglePick(cell) {
  // Remove a cell that is already picked.
  if (picks.includes(cell)) picks = picks.filter(c => c !== cell);
  // Add a new cell only while fewer than the required picks are chosen.
  else if (picks.length < PICKS) picks = [...picks, cell];
  // Clear any prior reveal so re-picking starts a fresh grid.
  shownReveal = null;
  // Repaint the updated selection.
  render();
}

// Compute the visual class for one cell from picks and any settled reveal.
function cellClass(cell) {
  // Highlight a matched prize on the settled grid.
  if (shownReveal && shownReveal.matched.includes(cell)) return 'matched';
  // Show a revealed prize the player missed.
  if (shownReveal && shownReveal.prizes.includes(cell)) return 'prize';
  // Show the player's current pick before a reveal.
  return '';
}

// Render the complete Lucky Grid route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the nine cells, marking picks, prizes, and matches.
  const cells = Array.from({ length: CELLS }, (unused, cell) => `<button class="lg-cell ${cellClass(cell)}" data-cell="${cell}" type="button" aria-pressed="${picks.includes(cell)}">${shownReveal && (shownReveal.prizes.includes(cell)) ? '&#9733;' : ''}</button>`).join('');
  // Build the payout rows.
  const pays = [[3, 25], [2, 3]].map(([m, mult]) => `<div><span>${safe(tx('pay.matches', { count: m }))}</span><span>${mult}x</span></div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="lg-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Report the picks-remaining hint.
  const hint = tx('pick.remaining', { count: PICKS - picks.length });
  // Paint the whole route.
  root.innerHTML = `<section class="lucky" data-testid="lucky-grid"><div class="lg-stage"><div class="lg-grid" data-testid="lucky-grid-board">${cells}</div><p class="lg-result" data-testid="lucky-grid-result" role="status">${resultText || safe(picks.length < PICKS ? hint : tx('result.ready'))}</p></div><div class="lg-panel"><div class="lg-card"><h3>${safe(tx('pay.title'))}</h3><div class="lg-pays">${pays}</div></div><div class="lg-card"><h3>${safe(tx('stake.title'))}</h3><div class="lg-chips">${chips}</div></div><button class="lg-go" data-testid="lucky-grid-go" type="button" ${lifecycle.isBusy() || picks.length !== PICKS ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.revealing') : tx('action.reveal'))}</button><button class="lg-repeat" data-testid="lucky-grid-repeat" type="button" ${lifecycle.isBusy() || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the cell pick buttons.
  root.querySelectorAll('[data-cell]').forEach(btn => { btn.onclick = () => { if (!lifecycle.isBusy()) togglePick(Number(btn.dataset.cell)); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the reveal action.
  const goBtn = root.querySelector('[data-testid="lucky-grid-go"]');
  // Attach the reveal handler only when a reveal is allowed.
  if (goBtn) goBtn.onclick = reveal;
  // Wire the one-click repeat that re-fires the last committed picks and stake.
  const repeatBtn = root.querySelector('[data-testid="lucky-grid-repeat"]');
  // Attach the repeat handler; the button stays disabled until a prior reveal settles.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const data = await api('/api/v1/games/lucky-grid/state');
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

// Execute one atomic wager, reveal, and settlement.
async function reveal() {
  // Ignore repeated clicks or an incomplete pick set.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || picks.length !== PICKS) return;
  // Mark the reveal busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once reveal with a caller-stable retry id and the chosen picks.
    const response = await post('/api/v1/games/lucky-grid/reveals', { request_id: lifecycle.nextRequestId(), picks: [...picks], stake });
    // Show the committed debit before the selected prize cells reveal. (LEDGER-031, issue #595)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Reveal the authoritative committed prizes and matches.
    shownReveal = round.detail;
    // Remember the exact committed picks and stake so one click can repeat the same reveal.
    lastBet = { picks: [...round.wager.picks], stake: round.wager.stake };
    // Repaint immediately so the prizes and matches show during the reveal.
    render();
    // Wait for the decorative reveal to finish before announcing the result.
    await new Promise(resolve => setTimeout(resolve, REVEAL_MS));
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the reveal paid.
    const win = round.total_return > 0;
    // Compose the localized result copy from the authoritative match count and net.
    const text = win
      ? `${safe(tx('result.win', { count: round.detail.match_count }))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.lose', { count: round.detail.match_count }))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the revealed grid and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.reveal'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last committed picks and stake and re-fire one reveal without a timer.
async function repeat() {
  // Ignore repeat while a reveal is active, after teardown, or before any prior reveal has settled.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous picks into the local selection.
  picks = [...lastBet.picks];
  // Restore the previous stake into the local selection.
  stake = lastBet.stake;
  // Fire the shared exactly-once reveal action with the restored picks and stake.
  await reveal();
}

// Export the isolated Lucky Grid game for the shared shell.
export const LuckyGridGame = {
  // Expose the stable catalog identifier.
  id: 'lucky_grid',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the picks for a fresh mount.
    picks = [];
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
