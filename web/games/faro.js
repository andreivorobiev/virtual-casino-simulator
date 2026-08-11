// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Faro route for GitHub issue #146, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/faro';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'faro-styles';
// Mirror the backend's thirteen ranks in ascending faro order.
export const RANKS = Object.freeze(['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative deal duration; the outcome is already server-authoritative.
const DEAL_MS = 700;

// Store the current route outlet, chosen rank, chosen stake, and in-flight guard.
let root = null;
let selectedRank = 1;
let stake = 5;
let dealBusy = false;
let localeUnsubscribe = null;
// Retain the last dealt cards so a repaint after the deal keeps showing the result.
let shownCards = null;
// Retain the last settled rank and stake so one click can repeat the same bet.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/faro') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.faro{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .fr-stage{display:grid;justify-items:center;gap:18px;padding:12px;min-width:0;} .fr-cards{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;min-width:0;} .fr-slot{display:grid;justify-items:center;gap:6px;} .fr-slot span{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--gold);font-weight:700;} .fr-card{width:76px;height:104px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(160deg,#fbf3dd,#e2cf9d);color:#241006;font-weight:900;font-size:32px;box-shadow:0 8px 20px rgba(0,0,0,.4),inset 0 0 0 2px #a9791f;} .fr-card.dealing{animation:fr-flip .35s ease;} @keyframes fr-flip{from{transform:rotateY(90deg);}to{transform:rotateY(0);}} .fr-ranks{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;width:100%;max-width:420px;min-width:0;} .fr-rank{min-height:44px;min-width:0;padding:0;border:2px solid transparent;border-radius:10px;background:rgba(255,255,255,.06);color:var(--text);font-weight:900;cursor:pointer;} .fr-rank[aria-pressed="true"]{border-color:var(--text);box-shadow:0 0 0 2px rgba(255,59,107,.5);} .fr-panel{display:grid;gap:12px;min-width:0;} .fr-card-box{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .fr-card-box h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .fr-odds{display:grid;gap:6px;font-size:13px;font-weight:700;} .fr-odds div{display:flex;justify-content:space-between;} .fr-odds span:last-child{color:var(--gold);} .fr-chips{display:flex;flex-wrap:wrap;gap:8px;} .fr-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .fr-chip[aria-pressed="true"]{border-color:var(--gold);background:rgba(255,59,107,.16);color:var(--text);} .fr-deal{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,var(--brand),var(--brand-strong));color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .fr-deal:disabled{opacity:.55;cursor:not-allowed;} .fr-result{min-height:44px;font-size:15px;color:var(--text);text-align:center;} .fr-result .net{font-weight:900;} @media (prefers-reduced-motion:reduce){.fr-card.dealing{animation:none;}} @media (max-width:900px){.faro{grid-template-columns:1fr;}} @media (max-width:430px){.fr-ranks{grid-template-columns:repeat(5,minmax(0,1fr));}}.fr-repeat{width:100%;min-height:46px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:16px;cursor:pointer;}.fr-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `fr-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Faro route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the dealt card faces or neutral placeholders before the first deal.
  const banker = shownCards ? shownCards.banker : '?';
  const player = shownCards ? shownCards.player : '?';
  // Build the thirteen rank cells.
  const ranks = RANKS.map((label, index) => `<button class="fr-rank" data-rank="${index + 1}" type="button" aria-pressed="${selectedRank === index + 1}">${safe(label)}</button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="fr-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="faro" data-testid="faro"><div class="fr-stage"><div class="fr-cards"><div class="fr-slot"><span>${safe(tx('card.banker', null, 'Banker'))}</span><div class="fr-card${dealBusy ? ' dealing' : ''}" data-testid="faro-banker">${safe(banker)}</div></div><div class="fr-slot"><span>${safe(tx('card.player', null, 'Player'))}</span><div class="fr-card${dealBusy ? ' dealing' : ''}" data-testid="faro-player">${safe(player)}</div></div></div><div class="fr-ranks">${ranks}</div><p class="fr-result" data-testid="faro-result" role="status">${resultText || safe(tx('result.idle', null, 'Pick a rank and deal.'))}</p></div><div class="fr-panel"><div class="fr-card-box"><h3>${safe(tx('odds.title', null, 'How it settles'))}</h3><div class="fr-odds"><div><span>${safe(tx('odds.win', null, 'Player card matches'))}</span><span>2x</span></div><div><span>${safe(tx('odds.push', null, 'Neither matches'))}</span><span>1x</span></div><div><span>${safe(tx('odds.split', null, 'Both match (split)'))}</span><span>0.5x</span></div><div><span>${safe(tx('odds.lose', null, 'Banker card matches'))}</span><span>0x</span></div></div></div><div class="fr-card-box"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="fr-chips">${chips}</div></div><button class="fr-deal" data-testid="faro-deal" type="button" ${dealBusy ? 'disabled' : ''}>${safe(dealBusy ? tx('action.dealing', null, 'Dealing…') : tx('action.deal', null, 'Deal the cards'))}</button><button class="fr-repeat" data-testid="faro-repeat" type="button" ${dealBusy || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
  // Wire the rank cells.
  root.querySelectorAll('[data-rank]').forEach(btn => { btn.onclick = () => { selectedRank = Number(btn.dataset.rank); render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the deal action.
  const dealBtn = root.querySelector('[data-testid="faro-deal"]');
  // Attach the deal handler only when a deal is not already running.
  if (dealBtn) dealBtn.onclick = deal;
  // Wire the one-click repeat that re-fires the previous bet.
  const repeatBtn = root.querySelector('[data-testid="faro-repeat"]');
  // Attach the repeat handler; the disabled attribute already gates busy and no-prior-bet states.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const payload = await api('/api/v1/games/faro/state');
    // Read the newest-first retained rounds so a repeatable bet can survive a reload.
    const restored = payload?.state?.recent_rounds?.[0]?.public?.wager;
    // Recover the repeatable rank and stake only when a settled round is present.
    if (restored) lastBet = { rank: restored.rank, stake: restored.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Faro.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, deal, and settlement.
async function deal() {
  // Ignore repeated clicks while a deal is resolving.
  if (dealBusy || !root) return;
  // Mark the deal busy and disable the control before the request.
  dealBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once deal with a caller-stable retry id and the chosen rank.
    const response = await post('/api/v1/games/faro/deals', { request_id: newRequestId(), rank: selectedRank, stake });
    // Show the committed debit before the banker and player cards are revealed. (LEDGER-031, issue #594)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative deal to finish before revealing the cards.
    await new Promise(resolve => setTimeout(resolve, DEAL_MS));
    // Reveal the authoritative dealt cards.
    shownCards = { banker: round.detail.banker, player: round.detail.player };
    // Remember the settled rank and stake so one click can repeat the same bet.
    lastBet = { rank: selectedRank, stake };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from the authoritative outcome and net.
    const text = `${safe(tx('outcome.' + round.outcome, null, round.outcome))} <span class="net">${net > 0 ? '+' + net : net}</span>`;
    // Release the guard before the final repaint.
    dealBusy = false;
    // Repaint with the dealt cards and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    dealBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.deal', null, 'Deal could not be completed.'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last settled bet and re-fire one deal without a timer.
async function repeat() {
  // Ignore repeat while a deal resolves, after teardown, or before any settled bet.
  if (dealBusy || !root || !lastBet) return;
  // Restore the previously settled rank into the local configuration.
  selectedRank = lastBet.rank;
  // Restore the previously settled stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once deal action with the restored bet.
  await deal();
}

// Export the isolated Faro game for the shared shell.
export const FaroGame = {
  // Expose the stable catalog identifier.
  id: 'faro',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Reset any repeatable bet so a new mount never inherits a stale one before load recovers history.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a deal owns the table.
    localeUnsubscribe = onLocaleChange(() => { if (!dealBusy) render(); });
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Remove the locale subscription when the route was initialized.
    localeUnsubscribe?.();
    // Clear the subscription reference for the next mount.
    localeUnsubscribe = null;
    // Clear the outlet so stale async work cannot repaint another route.
    root = null;
    // Reset the in-flight guard because teardown cancelled any presentation.
    dealBusy = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
