// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Coin Pusher route for GitHub issue #156, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/coin_pusher';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'cp', stylesheet: { id: 'coin-pusher-styles', href: '/games/coin_pusher.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend tipping threshold for the fill meter.
export const THRESHOLD = 12;
// Mirror the backend cascade multipliers by coin count.
export const CASCADES = Object.freeze([[1, 1.5], [2, 4], [3, 6], [4, 16]]);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative drop duration; the outcome is already server-authoritative.
const DROP_MS = 700;

// Store the chosen stake while the shared lifecycle owns route and busy state.
let stake = 5;
// Retain the last settled drop so a repaint after the drop keeps showing the shelf.
let shownDrop = null;
// Retain the last committed stake so one click can drop again at the same stake.
let lastBet = null;

// Render the complete Coin Pusher route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the settled shelf fill, capped at the threshold height for the meter.
  const filled = shownDrop ? Math.min(shownDrop.filled, THRESHOLD) : 0;
  // Compute the fill height as a percentage of the tipping threshold.
  const fillPct = Math.round((filled / THRESHOLD) * 100);
  // Read how many coins cascaded for the cascade animation.
  const coins = shownDrop ? shownDrop.coins : 0;
  // Build the cascading coin markup for a winning drop.
  const cascade = coins > 0 ? Array.from({ length: coins }, () => '<div class="cp-coin drop"></div>').join('') : '';
  // Build the paytable rows.
  const pays = CASCADES.map(([count, mult]) => `<div><span>${safe(tx('pay.coins', { count }))}</span><span>${mult}x</span></div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="cp-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="coinp" data-testid="coin-pusher"><div class="cp-stage"><div class="cp-machine"><div class="cp-tray" data-testid="coin-pusher-tray"><div class="cp-fill" style="height:${fillPct}%;"></div><div class="cp-coins">${cascade}</div></div><div class="cp-edge"></div><div class="cp-meter"><span>${safe(tx('meter.shelf'))}</span><span>${filled}/${THRESHOLD}</span></div></div><p class="cp-result" data-testid="coin-pusher-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="cp-panel"><div class="cp-card"><h3>${safe(tx('pay.title'))}</h3><div class="cp-pays">${pays}</div></div><div class="cp-card"><h3>${safe(tx('stake.title'))}</h3><div class="cp-chips">${chips}</div></div><button class="cp-drop" data-testid="coin-pusher-drop" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.dropping') : tx('action.drop'))}</button><button class="cp-repeat" data-testid="coin-pusher-repeat" type="button" ${(lifecycle.isBusy() || !lastBet) ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the drop action.
  const dropBtn = root.querySelector('[data-testid="coin-pusher-drop"]');
  // Attach the drop handler only when a drop is not already running.
  if (dropBtn) dropBtn.onclick = drop;
  // Wire the one-click repeat action.
  const repeatBtn = root.querySelector('[data-testid="coin-pusher-repeat"]');
  // Attach the repeat handler so the same stake can drop again.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const data = await api('/api/v1/games/coin-pusher/state');
    // Recover the repeatable stake from the newest settled round so repeat survives a reload.
    const restored = data?.state?.recent_rounds?.[0]?.public?.wager?.stake;
    // Restore the repeatable stake only when a prior settled round exists.
    if (restored) lastBet = { stake: restored };
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
  // Mark the drop busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once drop with a caller-stable retry id.
    const response = await post('/api/v1/games/coin-pusher/drops', { request_id: lifecycle.nextRequestId(), stake });
    // Show the committed debit before the shelf cascade exposes its return. (LEDGER-031, issue #591)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Reveal the authoritative committed shelf so the fill and cascade animate.
    shownDrop = round.detail;
    // Remember the committed stake so the next round can drop again with one click.
    lastBet = { stake: round.wager?.stake ?? stake };
    // Repaint immediately so the shelf fills and any coins cascade.
    render();
    // Wait for the decorative cascade to finish before revealing the result.
    await new Promise(resolve => setTimeout(resolve, DROP_MS));
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from authoritative values only.
    const text = round.detail.coins > 0
      ? `${safe(tx('result.cascade', { coins: round.detail.coins }))} <span class="net">+${net > 0 ? net : round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.hold'))} <span class="net">${net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the settled shelf and result.
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

// Re-apply the last committed stake and drop again without any timer.
async function repeat() {
  // Ignore repeat while a drop resolves, the route is gone, or no prior drop exists.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous stake into the local selection.
  stake = lastBet.stake;
  // Fire the same primary drop action through the shared busy and error handling.
  await drop();
}

// Export the isolated Coin Pusher game for the shared shell.
export const CoinPusherGame = {
  // Expose the stable catalog identifier.
  id: 'coin_pusher',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable stake so a new mount never inherits a stale one before load reconciles history.
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
    // Clear the repeatable stake so the next session starts fresh.
    lastBet = null;
  },
};
