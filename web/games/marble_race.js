// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Marble Race route for GitHub issue #157, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/marble_race';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'mr', stylesheet: { id: 'marble-race-styles', href: '/games/marble_race.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend's six marbles and their display colours in index order.
export const MARBLES = Object.freeze(['red', 'blue', 'green', 'yellow', 'purple', 'orange']);
// Map each marble to a concrete rendered fill.
const FILLS = { red: '#d6323d', blue: '#3d7ad6', green: '#0f9c4c', yellow: '#e7bd58', purple: '#9b59b6', orange: '#e07b39' };
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative race duration; the outcome is already server-authoritative.
const RACE_MS = 1300;

// Store the chosen bet, chosen marble, and chosen stake while the shared lifecycle owns route state.
let selectedBet = 'win';
let selectedMarble = 0;
let stake = 5;
// Retain the last settled finishing order so a repaint after the race keeps the result.
let shownOrder = null;
// Retain the last settled bet so one click can repeat the same marble and stake.
let lastBet = null;

// Read the localized display name for a marble index.
const marbleName = index => tx('marble.' + MARBLES[index]);

// Render the complete Marble Race route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Compute each marble's finishing place from the settled order, if any.
  const placeOf = {};
  // Record one-based finishing places when a race has settled.
  if (shownOrder) shownOrder.forEach((marble, index) => { placeOf[marble] = index + 1; });
  // Build one lane per marble in marble-index order, highlighting the winner.
  const lanes = MARBLES.map((color, index) => `<div class="mr-lane ${shownOrder && shownOrder[0] === index ? 'win' : ''}"><span class="mr-marble" style="background:${FILLS[color]};"></span><span class="mr-name">${safe(marbleName(index))}</span><span class="mr-place">${placeOf[index] ? '#' + placeOf[index] : ''}</span></div>`).join('');
  // Build the two bet-market buttons with honest payout hints.
  const bets = [['win', '5.7x'], ['podium', '1.9x']].map(([bet, mult]) => `<button class="mr-bet" data-bet="${bet}" type="button" aria-pressed="${selectedBet === bet}"><span>${safe(tx('bet.' + bet))}</span><small>${mult}</small></button>`).join('');
  // Build the six marble pick buttons.
  const picks = MARBLES.map((color, index) => `<button class="mr-pick" data-marble="${index}" type="button" aria-pressed="${selectedMarble === index}"><span class="dot" style="background:${FILLS[color]};"></span>${safe(marbleName(index))}</button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="mr-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="marble" data-testid="marble-race"><div class="mr-stage"><div class="mr-track" data-testid="marble-race-track">${lanes}</div><p class="mr-result" data-testid="marble-race-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="mr-panel"><div class="mr-card"><h3>${safe(tx('bet.title'))}</h3><div class="mr-bets">${bets}</div></div><div class="mr-card"><h3>${safe(tx('pick.title'))}</h3><div class="mr-picks">${picks}</div></div><div class="mr-card"><h3>${safe(tx('stake.title'))}</h3><div class="mr-chips">${chips}</div></div><button class="mr-go" data-testid="marble-race-go" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.racing') : tx('action.race'))}</button><button class="mr-repeat" data-testid="marble-race-repeat" type="button" ${(lifecycle.isBusy() || !lastBet) ? 'disabled' : ''}>${safe(tx('action.repeat'))}</button></div></section>`;
  // Wire the bet-market buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = btn.dataset.bet; render(); }; });
  // Wire the marble pick buttons.
  root.querySelectorAll('[data-marble]').forEach(btn => { btn.onclick = () => { selectedMarble = Number(btn.dataset.marble); render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the race action.
  const goBtn = root.querySelector('[data-testid="marble-race-go"]');
  // Attach the race handler only when a race is not already running.
  if (goBtn) goBtn.onclick = race;
  // Read the one-click repeat control created by this render.
  const repeatBtn = root.querySelector('[data-testid="marble-race-repeat"]');
  // Attach the repeat handler so one click replays the last settled bet.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const snapshot = await api('/api/v1/games/marble-race/state');
    // Recover a repeatable bet from the newest settled round so repeat survives a reload.
    const restored = snapshot?.state?.recent_rounds?.[0]?.public?.wager;
    // Restore the repeatable configuration only when a settled round is present.
    if (restored) lastBet = { bet: restored.bet, marble: restored.marble, stake: restored.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Re-apply the last settled bet and re-race with one click, adding no timer.
async function repeat() {
  // Ignore repeat while a race is resolving, after teardown, or without a prior settled bet.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous bet market into the local configuration.
  selectedBet = lastBet.bet;
  // Restore the previous marble pick into the local configuration.
  selectedMarble = lastBet.marble;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once race with the restored configuration.
  await race();
}

// Execute one atomic wager, race, and settlement.
async function race() {
  // Ignore repeated clicks while a race is resolving.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Mark the race busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once race with a caller-stable retry id and the chosen bet.
    const response = await post('/api/v1/games/marble-race/races', { request_id: lifecycle.nextRequestId(), bet: selectedBet, marble: selectedMarble, stake });
    // Show the committed debit before the finishing order becomes visible. (LEDGER-031, issue #596)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative race to finish before revealing the order.
    await new Promise(resolve => setTimeout(resolve, RACE_MS));
    // Reveal the authoritative finishing order.
    shownOrder = round.detail.order;
    // Remember the settled bet so one click can repeat the same marble and stake.
    lastBet = { bet: round.wager.bet, marble: round.wager.marble, stake: round.wager.stake };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the bet won.
    const win = round.total_return > 0;
    // Compose the localized result copy naming the winning marble and the net.
    const text = `${safe(tx('result.finish', { winner: marbleName(round.detail.winner) }))} <span class="net">${win ? '+' + (round.total_return - round.wager_total) : round.net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the finishing order and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.race'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Export the isolated Marble Race game for the shared shell.
export const MarbleRaceGame = {
  // Expose the stable catalog identifier.
  id: 'marble_race',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable bet so another session never inherits it before state loads.
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
