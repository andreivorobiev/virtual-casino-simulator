// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Isolated Daily Draw Lab route for GitHub issue #144, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/daily_draw_lab';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'daily-draw-lab-styles';
// Mirror the backend number pool size.
export const POOL = 30;
// Mirror the backend maximum pick count.
export const MAX_PICKS = 5;
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative reveal duration; the outcome is already server-authoritative.
const DRAW_MS = 700;

// Store the current route outlet, marked numbers, chosen stake, and in-flight guard.
let root = null;
let picks = [];
let stake = 5;
let drawBusy = false;
let localeUnsubscribe = null;
// Retain the last settled draw so a repaint keeps showing drawn numbers and hits.
let shownDraw = null;
// Retain the last committed picks and stake so one click can repeat the same draw.
let lastBet = null;

// Translate one game-domain key through the shared installed-locale fallback chain.
const tx = (key, params = {}) => t(key, params, GAME_DOMAIN);

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.daily{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .dd-stage{display:grid;justify-items:center;gap:12px;padding:12px;min-width:0;} .dd-board{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;width:min(420px,100%);} .dd-num{aspect-ratio:1;border-radius:10px;background:rgba(255,255,255,.06);border:2px solid rgba(255,255,255,.1);color:var(--text);font-weight:900;font-size:14px;cursor:pointer;display:grid;place-items:center;} .dd-num[aria-pressed="true"]{border-color:var(--gold);background:rgba(255,59,107,.16);color:var(--text);} .dd-num.drawn{background:rgba(34,224,195,.20);border-color:var(--accent);} .dd-num.hit{background:radial-gradient(circle at 40% 34%,#bff0cf,#0f9c4c);color:#052312;border-color:var(--metal-gold);} .dd-panel{display:grid;gap:12px;min-width:0;} .dd-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .dd-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .dd-pays{display:grid;gap:4px;font-size:12px;font-weight:700;} .dd-pays div{display:flex;justify-content:space-between;} .dd-pays span:last-child{color:var(--gold);} .dd-chips{display:flex;flex-wrap:wrap;gap:8px;} .dd-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .dd-chip[aria-pressed="true"]{border-color:var(--gold);background:rgba(255,59,107,.16);color:var(--text);} .dd-go{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,var(--brand),var(--brand-strong));color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .dd-go:disabled{opacity:.55;cursor:not-allowed;} .dd-result{min-height:24px;font-size:15px;color:var(--text);text-align:center;} .dd-result .net{font-weight:900;} @media (max-width:900px){.daily{grid-template-columns:1fr;}}.dd-repeat{width:100%;min-height:46px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;cursor:pointer;}.dd-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `dd-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

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
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the thirty number cells, marking picks, draws, and hits.
  const nums = Array.from({ length: POOL }, (unused, index) => index + 1).map(number => `<button class="dd-num ${numClass(number)}" data-number="${number}" type="button" aria-pressed="${picks.includes(number)}">${number}</button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="dd-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Report the mark hint.
  const hint = tx('pick.hint', { count: picks.length });
  // Paint the whole route.
  root.innerHTML = `<section class="daily" data-testid="daily-draw-lab"><div class="dd-stage"><div class="dd-board" data-testid="daily-draw-lab-board">${nums}</div><p class="dd-result" data-testid="daily-draw-lab-result" role="status">${resultText || safe(hint)}</p></div><div class="dd-panel"><div class="dd-card"><h3>${safe(tx('pay.title'))}</h3><div class="dd-pays">${paytableRows()}</div></div><div class="dd-card"><h3>${safe(tx('stake.title'))}</h3><div class="dd-chips">${chips}</div></div><button class="dd-go" data-testid="daily-draw-lab-go" type="button" ${drawBusy || picks.length < 1 ? 'disabled' : ''}>${safe(drawBusy ? tx('action.drawing') : tx('action.draw'))}</button><button class="dd-repeat" data-testid="daily-draw-lab-repeat" type="button" ${drawBusy || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat'))}</button></div></section>`;
  // Wire the number mark buttons.
  root.querySelectorAll('[data-number]').forEach(btn => { btn.onclick = () => { if (!drawBusy) toggleMark(Number(btn.dataset.number)); }; });
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
  // Ignore repeated clicks or an empty mark set.
  if (drawBusy || !root || picks.length < 1) return;
  // Mark the draw busy and disable the control before the request.
  drawBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once draw with a caller-stable retry id and the marked numbers.
    const response = await post('/api/v1/games/daily-draw-lab/draws', { request_id: newRequestId(), picks: [...picks], stake });
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
    drawBusy = false;
    // Repaint with the drawn board and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    drawBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.draw'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last committed picks and stake and re-fire one draw without a timer.
async function repeat() {
  // Ignore repeat while a draw is active, after teardown, or before any prior draw has settled.
  if (drawBusy || !root || !lastBet) return;
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
    // Store the current route outlet.
    root = node;
    // Reset the marks for a fresh mount.
    picks = [];
    // Reset the repeatable bet so a new mount never inherits a stale one before load reconciles history.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a draw owns the board.
    localeUnsubscribe = onLocaleChange(() => { if (!drawBusy) render(); });
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
    drawBusy = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
