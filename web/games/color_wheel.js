// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Color Wheel route for GitHub issue #152, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, stylesheet, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/color_wheel';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'cw', stylesheet: { id: 'color-wheel-styles', href: '/games/color_wheel.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Mirror the backend's fixed twenty-segment colour layout so the render and the result agree exactly.
export const SEGMENTS = Object.freeze(['red', 'black', 'red', 'black', 'green', 'red', 'black', 'red', 'black', 'gold', 'red', 'black', 'red', 'black', 'green', 'red', 'black', 'red', 'black', 'green']);
// Publish the selectable colour bets in stable order.
export const COLORS = Object.freeze(['red', 'black', 'green', 'gold']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative spin duration; the outcome is already server-authoritative.
const SPIN_MS = 3200;
// Require the wheel to complete several full turns before settling for an unambiguous spin.
const MIN_TURNS = 5;
// Map each segment colour to its rendered fill.
const FILLS = { red: '#b41b29', black: '#161616', green: '#0a7d3c', gold: '#e7bd58' };

// Store the selected bet and chosen stake while the shared lifecycle owns route state.
let selectedColor = 'red';
let stake = 5;
// Track the wheel's current angle so each spin continues from where the last one stopped.
let wheelAngle = 0;
// Retain the last committed colour and stake so one click can repeat the same spin.
let lastBet = null;

// Build the CSS conic-gradient that paints the twenty segments in order.
function wheelGradient() {
  // Compute the angular width of one segment.
  const step = 360 / SEGMENTS.length;
  // Build one colour stop per segment so the wheel matches the backend layout exactly.
  const stops = SEGMENTS.map((color, index) => `${FILLS[color]} ${index * step}deg ${(index + 1) * step}deg`);
  // Return the full conic-gradient background.
  return `conic-gradient(from -${step / 2}deg, ${stops.join(', ')})`;
}

// Compute the rotation that lands the pointer on a given segment after several full turns.
function rotationForSegment(index) {
  // Compute one segment's angular width.
  const step = 360 / SEGMENTS.length;
  // Target the centre of the winning segment under the fixed top pointer.
  const target = 360 - (index * step + step / 2);
  // Advance from the current angle through whole turns to the target so the spin only ever moves forward.
  const base = wheelAngle - (wheelAngle % 360);
  // Return the absolute angle including the minimum decorative turns.
  return base + MIN_TURNS * 360 + target;
}

// Render the complete Color Wheel route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the bet buttons with localized labels and payout hints.
  const bets = COLORS.map(color => {
    // Count this colour's segments for an honest odds hint.
    const count = SEGMENTS.filter(c => c === color).length;
    // Read the payout multiplier for the hint.
    const mult = { red: 2, black: 2, green: 6, gold: 16 }[color];
    // Return one pressable bet button.
    return `<button class="cw-bet ${color}" data-color="${color}" type="button" aria-pressed="${selectedColor === color}"><span>${safe(tx('bet.' + color))}</span><small>${count}/20 · ${mult}x</small></button>`;
  }).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="cw-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="color-wheel" data-testid="color-wheel"><div class="cw-stage"><div class="cw-wheel-wrap"><div class="cw-pointer"></div><div class="cw-wheel" data-testid="color-wheel-disc" style="background:${wheelGradient()};transform:rotate(${wheelAngle}deg);"></div><div class="cw-hub"></div></div><p class="cw-result" data-testid="color-wheel-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="cw-panel"><div class="cw-card"><h3>${safe(tx('bet.title'))}</h3><div class="cw-bets">${bets}</div></div><div class="cw-card"><h3>${safe(tx('stake.title'))}</h3><div class="cw-chips">${chips}</div></div><button class="cw-spin" data-testid="color-wheel-spin" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.spinning') : tx('action.spin'))}</button><button class="cw-repeat" data-testid="color-wheel-repeat" type="button" ${(lifecycle.isBusy() || !lastBet) ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the bet colour buttons.
  root.querySelectorAll('[data-color]').forEach(btn => { btn.onclick = () => { selectedColor = btn.dataset.color; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the spin action.
  const spinBtn = root.querySelector('[data-testid="color-wheel-spin"]');
  // Attach the spin handler only when a spin is not already running.
  if (spinBtn) spinBtn.onclick = spin;
  // Wire the one-click repeat that re-places the previous colour and stake.
  const repeatBtn = root.querySelector('[data-testid="color-wheel-repeat"]');
  // Attach the repeat handler; its disabled state already gates busy and empty-bet cases.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const snapshot = await api('/api/v1/games/color-wheel/state');
    // Read the newest persisted round so a reload can recover its repeatable bet.
    const latest = snapshot?.state?.recent_rounds?.[0]?.public;
    // Restore the repeatable colour and stake only from a persisted round's authoritative wager.
    lastBet = latest?.wager ? { color: latest.wager.color, stake: latest.wager.stake } : null;
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Re-place the previous colour and stake and re-fire one spin without a timer.
async function repeat() {
  // Ignore repeat while a spin is resolving, after teardown, or without a prior bet.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous colour into the local configuration.
  selectedColor = lastBet.color;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once spin action with the restored bet.
  await spin();
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
    // Post the exactly-once spin with a caller-stable retry id.
    const response = await post('/api/v1/games/color-wheel/spins', { request_id: lifecycle.nextRequestId(), color: selectedColor, stake });
    // Show the committed debit before the wheel exposes its landed color. (LEDGER-031, issue #592)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative landed segment and outcome.
    const round = response.round;
    // Remember the settled colour and stake so one click can repeat the same bet next spin.
    lastBet = { color: round.wager?.color ?? selectedColor, stake: round.wager?.stake ?? stake };
    // Animate the wheel to the winning segment.
    wheelAngle = rotationForSegment(round.detail.segment);
    // Apply the rotation to the disc immediately for the CSS transition.
    const disc = lifecycle.root()?.querySelector('[data-testid="color-wheel-disc"]');
    // Rotate the disc when it is present.
    if (disc) disc.style.transform = `rotate(${wheelAngle}deg)`;
    // Wait for the decorative spin to finish before revealing the outcome.
    await new Promise(resolve => setTimeout(resolve, SPIN_MS));
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Build the localized result copy from authoritative values only.
    const win = round.total_return > 0;
    // Compose the result line with the landed colour and the net.
    const text = `${safe(tx('result.landed', { color: tx('bet.' + round.detail.color) }))} <span class="net">${win ? '+' + (round.total_return - round.wager_total) : round.net}</span>`;
    // Announce the result via voice-neutral status copy.
    lifecycle.setBusy(false);
    // Repaint with the result.
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

// Export the isolated Color Wheel game for the shared shell.
export const ColorWheelGame = {
  // Expose the stable catalog identifier.
  id: 'color_wheel',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Reset any repeatable bet so a new mount never inherits a stale one before load reconciles history.
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
