// Isolated Lucky Grid route for GitHub issue #153, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/lucky_grid';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'lucky-grid-styles';
// Mirror the backend board size and required pick count.
export const CELLS = 9;
// Require exactly this many picks before a reveal is allowed.
export const PICKS = 3;
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative reveal duration; the outcome is already server-authoritative.
const REVEAL_MS = 600;

// Store the current route outlet, chosen cells, chosen stake, and in-flight guard.
let root = null;
let picks = [];
let stake = 5;
let revealBusy = false;
let localeUnsubscribe = null;
// Retain the last settled reveal so a repaint keeps showing prizes and matches.
let shownReveal = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/lucky_grid') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.lucky{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .lg-stage{display:grid;justify-items:center;gap:14px;padding:12px;min-width:0;} .lg-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;width:min(300px,74vw);} .lg-cell{aspect-ratio:1;border-radius:12px;background:rgba(255,255,255,.06);border:2px solid rgba(255,255,255,.12);display:grid;place-items:center;font-size:26px;font-weight:900;color:#f5ead6;cursor:pointer;} .lg-cell[aria-pressed="true"]{border-color:#fff2c2;box-shadow:0 0 0 2px rgba(255,242,194,.5);background:rgba(231,189,88,.14);} .lg-cell.prize{background:radial-gradient(circle at 40% 34%,#fff3bd,#e7bd58);color:#241006;} .lg-cell.matched{background:radial-gradient(circle at 40% 34%,#bff0cf,#0f9c4c);color:#052312;box-shadow:0 0 0 2px #fff2c2;} .lg-panel{display:grid;gap:12px;min-width:0;} .lg-card{padding:14px;border:1px solid rgba(255,217,120,.42);border-radius:16px;background:rgba(0,0,0,.22);} .lg-card h3{margin:0 0 10px;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .lg-pays{display:grid;gap:6px;font-size:13px;font-weight:700;} .lg-pays div{display:flex;justify-content:space-between;} .lg-pays span:last-child{color:#f2d77d;} .lg-chips{display:flex;flex-wrap:wrap;gap:8px;} .lg-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:#f5ead6;font-weight:900;cursor:pointer;} .lg-chip[aria-pressed="true"]{border-color:#e7bd58;background:rgba(231,189,88,.16);color:#fff2c2;} .lg-go{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,#e7bd58,#a9791f);color:#241006;font-weight:900;font-size:16px;cursor:pointer;} .lg-go:disabled{opacity:.55;cursor:not-allowed;} .lg-result{min-height:24px;font-size:15px;color:#fff2c2;text-align:center;} .lg-result .net{font-weight:900;} @media (max-width:900px){.lucky{grid-template-columns:1fr;}}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `lg-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

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
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the nine cells, marking picks, prizes, and matches.
  const cells = Array.from({ length: CELLS }, (unused, cell) => `<button class="lg-cell ${cellClass(cell)}" data-cell="${cell}" type="button" aria-pressed="${picks.includes(cell)}">${shownReveal && (shownReveal.prizes.includes(cell)) ? '&#9733;' : ''}</button>`).join('');
  // Build the payout rows.
  const pays = [[3, 25], [2, 3]].map(([m, mult]) => `<div><span>${safe(tx('pay.matches', { count: m }, m + ' matches'))}</span><span>${mult}x</span></div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="lg-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Report the picks-remaining hint.
  const hint = tx('pick.remaining', { count: PICKS - picks.length }, `Pick ${PICKS - picks.length} more`);
  // Paint the whole route.
  root.innerHTML = `<section class="lucky" data-testid="lucky-grid"><div class="lg-stage"><div class="lg-grid" data-testid="lucky-grid-board">${cells}</div><p class="lg-result" data-testid="lucky-grid-result" role="status">${resultText || safe(picks.length < PICKS ? hint : tx('result.ready', null, 'Reveal the prizes.'))}</p></div><div class="lg-panel"><div class="lg-card"><h3>${safe(tx('pay.title', null, 'Payouts'))}</h3><div class="lg-pays">${pays}</div></div><div class="lg-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="lg-chips">${chips}</div></div><button class="lg-go" data-testid="lucky-grid-go" type="button" ${revealBusy || picks.length !== PICKS ? 'disabled' : ''}>${safe(revealBusy ? tx('action.revealing', null, 'Revealing…') : tx('action.reveal', null, 'Reveal prizes'))}</button></div></section>`;
  // Wire the cell pick buttons.
  root.querySelectorAll('[data-cell]').forEach(btn => { btn.onclick = () => { if (!revealBusy) togglePick(Number(btn.dataset.cell)); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the reveal action.
  const goBtn = root.querySelector('[data-testid="lucky-grid-go"]');
  // Attach the reveal handler only when a reveal is allowed.
  if (goBtn) goBtn.onclick = reveal;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    await api('/api/v1/games/lucky-grid/state');
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Lucky Grid.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, reveal, and settlement.
async function reveal() {
  // Ignore repeated clicks or an incomplete pick set.
  if (revealBusy || !root || picks.length !== PICKS) return;
  // Mark the reveal busy and disable the control before the request.
  revealBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once reveal with a caller-stable retry id and the chosen picks.
    const response = await post('/api/v1/games/lucky-grid/reveals', { request_id: newRequestId(), picks: [...picks], stake });
    // Read the authoritative settled round.
    const round = response.round;
    // Reveal the authoritative committed prizes and matches.
    shownReveal = round.detail;
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
      ? `${safe(tx('result.win', { count: round.detail.match_count }, round.detail.match_count + ' matches'))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.lose', { count: round.detail.match_count }, round.detail.match_count + ' matches'))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    revealBusy = false;
    // Repaint with the revealed grid and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    revealBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.reveal', null, 'Reveal could not be completed.'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Export the isolated Lucky Grid game for the shared shell.
export const LuckyGridGame = {
  // Expose the stable catalog identifier.
  id: 'lucky_grid',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Reset the picks for a fresh mount.
    picks = [];
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a reveal owns the grid.
    localeUnsubscribe = onLocaleChange(() => { if (!revealBusy) render(); });
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
    revealBusy = false;
  },
};
