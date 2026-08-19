// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Trente et Quarante route for GitHub issue #147, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import shared route, locale, style, busy-state, and request-identity ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/trente_et_quarante';
// Create the route controller with the external game stylesheet and established request prefix.
const lifecycle = createGameLifecycle({ domain: GAME_DOMAIN, requestPrefix: 'teq', stylesheet: { id: 'teq-styles', href: '/games/trente_et_quarante.css' } });
// Reuse the shared domain translator without defining a game-local wrapper.
const { tx } = lifecycle;
// Publish the four selectable bets in stable order.
export const BETS = Object.freeze(['rouge', 'noir', 'couleur', 'inverse']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative deal duration; the outcome is already server-authoritative.
const DEAL_MS = 800;

// Store the chosen bet and stake while the shared lifecycle owns route and busy state.
let selectedBet = 'rouge';
let stake = 5;
// Retain the last settled deal so a repaint after the coup keeps showing the rows.
let shownDeal = null;
// Retain the last settled bet target and stake so one click can repeat the same coup.
let lastBet = null;

// Build the card chips for one dealt row.
function rowCards(cards) {
  // Render each committed card with its rank and colour, or a placeholder before the first deal.
  return (cards || [{ rank: '?', color: 'red' }, { rank: '?', color: 'black' }]).map(card => `<div class="teq-card ${card.color === 'red' ? 'red' : 'black'}">${safe(card.rank)}</div>`).join('');
}

// Render the complete Trente et Quarante route into the outlet.
function render(resultText) {
  // Read the current route outlet through the shared teardown guard.
  const root = lifecycle.root();
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the settled winner so the winning row can be highlighted.
  const winner = shownDeal ? shownDeal.winner : null;
  // Build the Noir and Rouge rows with their totals and cards.
  const noir = `<div class="teq-row noir ${winner === 'noir' ? 'win' : ''}"><div class="teq-row-head"><span>${safe(tx('row.noir'))}</span><span class="total">${shownDeal ? shownDeal.noir_total : '—'}</span></div><div class="teq-cards">${rowCards(shownDeal && shownDeal.noir)}</div></div>`;
  // Build the Rouge row similarly.
  const rouge = `<div class="teq-row rouge ${winner === 'rouge' ? 'win' : ''}"><div class="teq-row-head"><span>${safe(tx('row.rouge'))}</span><span class="total">${shownDeal ? shownDeal.rouge_total : '—'}</span></div><div class="teq-cards">${rowCards(shownDeal && shownDeal.rouge)}</div></div>`;
  // Build the four bet buttons with localized labels and hints.
  const bets = BETS.map(bet => `<button class="teq-bet" data-bet="${bet}" type="button" aria-pressed="${selectedBet === bet}"><span>${safe(tx('bet.' + bet))}</span><small>${safe(tx('bet.' + bet + '.hint'))}</small></button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="teq-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="teq" data-testid="trente-et-quarante"><div class="teq-stage">${noir}${rouge}<p class="teq-result" data-testid="teq-result" role="status">${resultText || safe(tx('result.idle'))}</p></div><div class="teq-panel"><div class="teq-card-box"><h3>${safe(tx('bet.title'))}</h3><div class="teq-bets">${bets}</div></div><div class="teq-card-box"><h3>${safe(tx('stake.title'))}</h3><div class="teq-chips">${chips}</div></div><button class="teq-deal" data-testid="teq-deal" type="button" ${lifecycle.isBusy() ? 'disabled' : ''}>${safe(lifecycle.isBusy() ? tx('action.dealing') : tx('action.deal'))}</button><button class="teq-repeat" data-testid="teq-repeat" data-action="repeat" type="button" ${lifecycle.isBusy() || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the bet buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = btn.dataset.bet; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the deal action.
  const dealBtn = root.querySelector('[data-testid="teq-deal"]');
  // Attach the deal handler only when a deal is not already running.
  if (dealBtn) dealBtn.onclick = deal;
  // Wire the one-click repeat that re-fires the previous bet.
  const repeatBtn = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler so a single click re-places the last bet.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Re-apply the last settled bet and re-fire one coup without a timer.
async function repeat() {
  // Ignore repeat while a coup is resolving or before any settled bet exists.
  if (lifecycle.isBusy() || !lifecycle.isMounted() || !lastBet) return;
  // Restore the previous bet target into the local configuration.
  selectedBet = lastBet.bet;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once coup with the restored bet.
  await deal();
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const data = await api('/api/v1/games/trente-et-quarante/state');
    // Read the authoritative bounded recent-round history, newest first.
    const recent = data && data.state && data.state.recent_rounds;
    // Recover a repeatable bet from the newest settled round so repeat survives a reload.
    if (recent && recent.length && recent[0].public && recent[0].public.wager) lastBet = { bet: recent[0].public.wager.bet, stake: recent[0].public.wager.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, deal, and settlement.
async function deal() {
  // Ignore repeated clicks while a coup is resolving.
  if (lifecycle.isBusy() || !lifecycle.isMounted()) return;
  // Mark the deal busy and disable the control before the request.
  lifecycle.setBusy(true);
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once coup with a caller-stable retry id and the chosen bet.
    const response = await post('/api/v1/games/trente-et-quarante/coups', { request_id: lifecycle.nextRequestId(), bet: selectedBet, stake });
    // Show the committed debit before both authoritative rows reveal. (LEDGER-031, issue #600)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative deal to finish before revealing the rows.
    await new Promise(resolve => setTimeout(resolve, DEAL_MS));
    // Reveal the authoritative dealt rows and winner.
    shownDeal = round.detail;
    // Remember the settled bet and stake so one click can repeat the same coup.
    lastBet = { bet: round.wager.bet, stake: round.wager.stake };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from the authoritative outcome and net.
    const text = `${safe(tx('outcome.' + round.outcome))} <span class="net">${net > 0 ? '+' + net : net}</span>`;
    // Release the guard before the final repaint.
    lifecycle.setBusy(false);
    // Repaint with the dealt rows and result.
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

// Export the isolated Trente et Quarante game for the shared shell.
export const TrenteEtQuaranteGame = {
  // Expose the stable catalog identifier.
  id: 'trente_et_quarante',
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
