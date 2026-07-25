// Isolated Pattern Draw route for GitHub issue #155, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/pattern_draw';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'pattern-draw-styles';
// Mirror the backend pattern bets and their multipliers in stable order.
export const BETS = Object.freeze([['line', 1.75], ['cross', 30], ['full', 480]]);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative reveal duration; the outcome is already server-authoritative.
const DRAW_MS = 600;

// Store the current route outlet, chosen bet, chosen stake, and in-flight guard.
let root = null;
let selectedBet = 'line';
let stake = 5;
let drawBusy = false;
let localeUnsubscribe = null;
// Retain the last settled grid so a repaint after the draw keeps showing the pattern.
let shownGrid = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/pattern_draw') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.pattern{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .pd-stage{display:grid;justify-items:center;gap:14px;padding:12px;min-width:0;} .pd-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;width:min(280px,72vw);} .pd-cell{aspect-ratio:1;border-radius:12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);transition:background .2s ease,box-shadow .2s ease;} .pd-cell.on{background:radial-gradient(circle at 40% 34%,#fff3bd,#e7bd58);box-shadow:0 0 12px rgba(231,189,88,.6);} .pd-panel{display:grid;gap:12px;min-width:0;} .pd-card{padding:14px;border:1px solid rgba(255,217,120,.42);border-radius:16px;background:rgba(0,0,0,.22);} .pd-card h3{margin:0 0 10px;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .pd-bets{display:grid;gap:8px;} .pd-bet{display:flex;justify-content:space-between;padding:10px;border:2px solid transparent;border-radius:12px;background:rgba(255,255,255,.05);color:#f5ead6;font-weight:900;cursor:pointer;text-transform:capitalize;} .pd-bet small{font-weight:700;color:#f2d77d;} .pd-bet[aria-pressed="true"]{border-color:#fff2c2;box-shadow:0 0 0 2px rgba(255,242,194,.5);} .pd-chips{display:flex;flex-wrap:wrap;gap:8px;} .pd-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:#f5ead6;font-weight:900;cursor:pointer;} .pd-chip[aria-pressed="true"]{border-color:#e7bd58;background:rgba(231,189,88,.16);color:#fff2c2;} .pd-draw{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,#9b59b6,#6c3483);color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .pd-draw:disabled{opacity:.55;cursor:not-allowed;} .pd-result{min-height:24px;font-size:15px;color:#fff2c2;text-align:center;} .pd-result .net{font-weight:900;} @media (max-width:900px){.pattern{grid-template-columns:1fr;}}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `pd-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Pattern Draw route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the nine grid cells, lighting the ones the committed grid turned on.
  const cells = Array.from({ length: 9 }, (unused, index) => `<div class="pd-cell ${shownGrid && shownGrid[index] ? 'on' : ''}" data-testid="pattern-draw-cell-${index}"></div>`).join('');
  // Build the three pattern bet buttons with honest multipliers.
  const bets = BETS.map(([bet, mult]) => `<button class="pd-bet" data-bet="${bet}" type="button" aria-pressed="${selectedBet === bet}"><span>${safe(tx('bet.' + bet, null, bet))}</span><small>${mult}x</small></button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="pd-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="pattern" data-testid="pattern-draw"><div class="pd-stage"><div class="pd-grid" data-testid="pattern-draw-grid">${cells}</div><p class="pd-result" data-testid="pattern-draw-result" role="status">${resultText || safe(tx('result.idle', null, 'Pick a pattern and draw.'))}</p></div><div class="pd-panel"><div class="pd-card"><h3>${safe(tx('bet.title', null, 'Pattern'))}</h3><div class="pd-bets">${bets}</div></div><div class="pd-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="pd-chips">${chips}</div></div><button class="pd-draw" data-testid="pattern-draw-draw" type="button" ${drawBusy ? 'disabled' : ''}>${safe(drawBusy ? tx('action.drawing', null, 'Drawing…') : tx('action.draw', null, 'Draw the grid'))}</button></div></section>`;
  // Wire the pattern bet buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = btn.dataset.bet; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the draw action.
  const drawBtn = root.querySelector('[data-testid="pattern-draw-draw"]');
  // Attach the draw handler only when a draw is not already running.
  if (drawBtn) drawBtn.onclick = draw;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    await api('/api/v1/games/pattern-draw/state');
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Pattern Draw.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, draw, and settlement.
async function draw() {
  // Ignore repeated clicks while a draw is resolving.
  if (drawBusy || !root) return;
  // Mark the draw busy and disable the control before the request.
  drawBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once draw with a caller-stable retry id and the chosen pattern.
    const response = await post('/api/v1/games/pattern-draw/draws', { request_id: newRequestId(), bet: selectedBet, stake });
    // Read the authoritative settled round.
    const round = response.round;
    // Reveal the authoritative committed grid so the cells light up.
    shownGrid = round.detail.grid;
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
      ? `${safe(tx('result.hit', { bet: tx('bet.' + round.detail.bet, null, round.detail.bet) }, 'Pattern hit'))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.miss', null, 'No pattern.'))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    drawBusy = false;
    // Repaint with the drawn grid and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    drawBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.draw', null, 'Draw could not be completed.'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Export the isolated Pattern Draw game for the shared shell.
export const PatternDrawGame = {
  // Expose the stable catalog identifier.
  id: 'pattern_draw',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a draw owns the grid.
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
  },
};
