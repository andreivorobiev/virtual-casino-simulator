// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Boule route for GitHub issue #148, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/boule';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'bl', stylesheet: { id: 'boule-styles', href: '/games/boule.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend's nine drawable numbers in ascending order.
export const NUMBERS = Object.freeze([1, 2, 3, 4, 5, 6, 7, 8, 9]);
// Name the house number so the board can mark it distinctly.
const HOUSE_NUMBER = 5;
// Mirror the backend even-money groups and the numbers each covers.
export const EVEN_MONEY = Object.freeze({ low: [1, 2, 3, 4], high: [6, 7, 8, 9], odd: [1, 3, 7, 9], even: [2, 4, 6, 8] });
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative draw duration; the outcome is already server-authoritative.
const DRAW_MS = 800;

// Store the selected bet and chosen stake while the shared lifecycle owns route state.
let selectedBet = { bet: 'even' };
let stake = 5;
// Retain the last drawn number so a repaint after the draw keeps showing the result.
let shownNumber = null;
// Retain the last settled bet config so one click can re-place and re-spin it.
let lastBet = null;

// Compare the active selection against a candidate bet for pressed state.
function isSelected(bet, number) {
  // A named even-money selection matches on its family with no number.
  if (number === undefined) return selectedBet.bet === bet && selectedBet.number === undefined;
  // A straight selection matches on the number.
  return selectedBet.bet === 'number' && selectedBet.number === number;
}

// Render the complete Boule route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the drum face showing the last drawn number or a neutral placeholder.
  const drum = shownNumber === null ? '&middot;' : String(shownNumber);
  // Build the nine straight-number cells, marking the house number.
  const numbers = NUMBERS.map(n => `<button class="bl-num${n === HOUSE_NUMBER ? ' house' : ''}" data-number="${n}" type="button" aria-pressed="${isSelected('number', n)}">${n}</button>`).join('');
  // Build the four even-money bet buttons with honest coverage and payout hints.
  const bets = ['low', 'high', 'odd', 'even'].map(name => `<button class="bl-bet" data-bet="${name}" type="button" aria-pressed="${isSelected(name)}"><span>${safe(tx('bet.' + name))}</span><small>${EVEN_MONEY[name].join(' ')} &middot; 2x</small></button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="bl-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Enable the one-click repeat only when a prior settled bet exists and no spin is running.
  const repeatDisabled = lifecycle.isBusy() || !lastBet;
  // Paint the whole route.
  root.innerHTML = `<section class="boule" data-testid="boule"><div class="bl-stage"><div class="bl-drum${lifecycle.isBusy() ? ' rolling' : ''}" data-testid="boule-drum">${drum}</div><div class="bl-numbers">${numbers}</div><p class="bl-result" data-testid="boule-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="bl-panel"><div class="bl-card"><h3>${safe(tx('bet.title'))}</h3><div class="bl-bets">${bets}</div></div><div class="bl-card"><h3>${safe(tx('stake.title'))}</h3><div class="bl-chips">${chips}</div></div><button class="bl-spin" data-testid="boule-spin" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.spinning') : tx('action.spin'))}</button><button type="button" class="bl-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the even-money bet buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = { bet: btn.dataset.bet }; render(); }; });
  // Wire the straight-number cells.
  root.querySelectorAll('[data-number]').forEach(btn => { btn.onclick = () => { selectedBet = { bet: 'number', number: Number(btn.dataset.number) }; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the spin action.
  const spinBtn = root.querySelector('[data-testid="boule-spin"]');
  // Attach the spin handler only when a spin is not already running.
  if (spinBtn) spinBtn.onclick = spin;
  // Wire the one-click repeat that re-places the previous bet.
  const repeatBtn = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler so a settled bet can be replayed with one click.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Re-place the last settled bet and re-fire one spin without a timer.
async function repeat() {
  // Ignore repeat while a spin is resolving or before any settled bet exists.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous even-money family or straight-number selection.
  selectedBet = lastBet.number === undefined ? { bet: lastBet.bet } : { bet: lastBet.bet, number: lastBet.number };
  // Restore the previous stake.
  stake = lastBet.stake;
  // Re-fire the shared exactly-once spin with the restored bet.
  await spin();
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const payload = await api('/api/v1/games/boule/state');
    // Recover the repeatable bet from the newest settled round so repeat survives a reload.
    const recovered = payload?.state?.recent_rounds?.[0]?.public?.wager;
    // Restore the repeatable config only when a settled round is present.
    if (recovered) lastBet = { ...recovered };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, spin, and settlement.
async function spin() {
  // Ignore repeated clicks while a spin is resolving.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Mark the spin busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once spin with a caller-stable retry id and the current selection.
    const response = await post('/api/v1/games/boule/spins', { request_id: lifecycle.nextRequestId(), ...selectedBet, stake });
    // Show the committed debit before the ball exposes the winning number. (LEDGER-031, issue #590)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative draw to finish before revealing the number.
    await new Promise(resolve => setTimeout(resolve, DRAW_MS));
    // Reveal the authoritative drawn number.
    shownNumber = round.detail.number;
    // Remember the authoritative settled bet config so one click can repeat it.
    lastBet = { ...round.wager };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the round paid.
    const win = round.total_return > 0;
    // Compose the localized result copy from authoritative values only.
    const text = win
      ? `${safe(tx('result.win', { number: shownNumber }))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.lose', { number: shownNumber }))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the drawn number and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    lifecycle.setBusy(false);
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.spin'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Export the isolated Boule game for the shared shell.
export const BouleGame = {
  // Expose the stable catalog identifier.
  id: 'boule',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset the repeatable bet so another session never inherits it before recovery.
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
