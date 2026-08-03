// Isolated Pachinko route for GitHub issue #142, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/pachinko';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'pachinko-styles';
// Mirror the backend's twelve pin rows.
export const ROWS = 12;
// Mirror the backend's thirteen pocket multipliers in pocket order.
export const POCKETS = Object.freeze([100, 15, 4, 2, 1, 0.5, 0.3, 0.5, 1, 2, 4, 15, 100]);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative per-row fall step; the outcome is already server-authoritative.
const STEP_MS = 70;

// Store the current route outlet, chosen stake, and in-flight guard.
let root = null;
let stake = 5;
let dropBusy = false;
let localeUnsubscribe = null;
// Retain the last landed pocket so a repaint after the drop keeps highlighting it.
let landedPocket = null;
// Retain the last committed stake so one click can repeat the same drop.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/pachinko') || fallback || key;

// Choose a compact CSS class for a pocket by how richly it pays.
function pocketClass(multiplier) {
  // Mark jackpot, winning, even, and losing pockets so the board reads at a glance.
  return multiplier >= 15 ? 'jackpot' : multiplier > 1 ? 'win' : multiplier === 1 ? 'even' : 'low';
}

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.pachinko{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .pk-stage{display:grid;justify-items:center;gap:12px;padding:12px;min-width:0;} .pk-board{position:relative;width:min(360px,80vw);aspect-ratio:1/1.05;background:radial-gradient(circle at 50% 0%,var(--felt2),var(--bg));border:6px solid var(--gold);border-radius:16px;overflow:hidden;box-shadow:0 12px 34px rgba(0,0,0,.45);} .pk-pin{position:absolute;width:6px;height:6px;border-radius:50%;background:#8fb6d6;transform:translate(-50%,-50%);} .pk-ball{position:absolute;width:16px;height:16px;border-radius:50%;background:radial-gradient(circle at 36% 32%,#fff,#e7bd58);transform:translate(-50%,-50%);transition:top ' + (STEP_MS/1000) + 's linear,left ' + (STEP_MS/1000) + 's linear;box-shadow:0 0 8px rgba(231,189,88,.8);z-index:2;} .pk-pockets{display:grid;grid-template-columns:repeat(13,1fr);gap:2px;width:min(360px,80vw);min-width:0;} .pk-pocket{min-height:34px;display:grid;place-items:center;border-radius:6px;font-weight:900;font-size:11px;background:rgba(255,255,255,.06);color:var(--text);} .pk-pocket.low{background:rgba(120,120,140,.18);} .pk-pocket.even{background:rgba(255,255,255,.12);} .pk-pocket.win{background:rgba(15,156,76,.28);color:#bff0cf;} .pk-pocket.jackpot{background:linear-gradient(180deg,#f0c45d,#a9791f);color:#241006;} .pk-pocket.hit{outline:2px solid var(--accent);outline-offset:1px;box-shadow:0 0 0 2px rgba(34,224,195,.5);} .pk-panel{display:grid;gap:12px;min-width:0;} .pk-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .pk-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .pk-chips{display:flex;flex-wrap:wrap;gap:8px;} .pk-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .pk-chip[aria-pressed="true"]{border-color:var(--gold);background:rgba(231,189,88,.16);color:var(--text);} .pk-drop{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,var(--brand),var(--brand-strong));color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .pk-drop:disabled{opacity:.55;cursor:not-allowed;} .pk-result{min-height:24px;font-size:15px;color:var(--text);text-align:center;} .pk-result .net{font-weight:900;} @media (max-width:900px){.pachinko{grid-template-columns:1fr;}}.pk-repeat{width:100%;min-height:44px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.pk-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `pk-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Build the decorative pin field markup as evenly spaced dots per row.
function pins() {
  // Accumulate one row of pins per pin row.
  const dots = [];
  // Place a triangular pin lattice so the ball visibly bounces between pins.
  for (let row = 0; row < ROWS; row++) {
    // Compute this row's vertical position as a percentage of the board height.
    const top = 8 + (row / ROWS) * 78;
    // Place one more pin than the row index, centred horizontally.
    for (let i = 0; i <= row + 1; i++) {
      // Compute this pin's horizontal position centred around the middle.
      const left = 50 + (i - (row + 1) / 2) * (74 / (ROWS + 1));
      // Append one positioned pin.
      dots.push(`<span class="pk-pin" style="top:${top}%;left:${left}%;"></span>`);
    }
  }
  // Return the full pin lattice.
  return dots.join('');
}

// Render the complete Pachinko route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the thirteen pockets, marking the last landed pocket.
  const pockets = POCKETS.map((mult, index) => `<div class="pk-pocket ${pocketClass(mult)} ${landedPocket === index ? 'hit' : ''}" data-testid="pachinko-pocket-${index}">${mult}x</div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="pk-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route with the ball parked at the top centre.
  root.innerHTML = `<section class="pachinko" data-testid="pachinko"><div class="pk-stage"><div class="pk-board" data-testid="pachinko-board">${pins()}<div class="pk-ball" data-testid="pachinko-ball" style="top:2%;left:50%;"></div></div><div class="pk-pockets">${pockets}</div><p class="pk-result" data-testid="pachinko-result" role="status">${resultText || safe(tx('result.idle', null, 'Set a stake and drop the ball.'))}</p></div><div class="pk-panel"><div class="pk-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="pk-chips">${chips}</div></div><button class="pk-drop" data-testid="pachinko-drop" type="button" ${dropBusy ? 'disabled' : ''}>${safe(dropBusy ? tx('action.dropping', null, 'Dropping…') : tx('action.drop', null, 'Drop the ball'))}</button><button class="pk-repeat" data-testid="pachinko-repeat" type="button" ${dropBusy || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the drop action.
  const dropBtn = root.querySelector('[data-testid="pachinko-drop"]');
  // Attach the drop handler only when a drop is not already running.
  if (dropBtn) dropBtn.onclick = drop;
  // Read the secondary one-click repeat control.
  const repeatBtn = root.querySelector('[data-testid="pachinko-repeat"]');
  // Attach the repeat handler only when a prior stake can be re-fired.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Animate the ball down the committed path so the visible landing matches the server pocket.
async function animate(path) {
  // Read the ball element to move down the board.
  const ball = root && root.querySelector('[data-testid="pachinko-ball"]');
  // Skip the animation when the ball is not present.
  if (!ball) return;
  // Track the running horizontal offset in pin steps from centre.
  let offset = 0;
  // Step the ball down one pin row at a time following the committed bounces.
  for (let row = 0; row < path.length; row++) {
    // Move right or left by half a pin spacing per bounce.
    offset += path[row] === 'R' ? 0.5 : -0.5;
    // Position the ball at this row's height and accumulated offset.
    ball.style.top = `${8 + (row / ROWS) * 82}%`;
    ball.style.left = `${50 + offset * (74 / (ROWS + 1))}%`;
    // Wait one step so each bounce is visible.
    await new Promise(resolve => setTimeout(resolve, STEP_MS));
  }
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const payload = await api('/api/v1/games/pachinko/state');
    // Recover a repeatable stake from the newest settled drop so repeat survives a reload.
    const restored = payload?.state?.recent_rounds?.[0]?.public;
    // Restore the repeatable stake only when a settled drop is present.
    if (restored?.wager?.stake) lastBet = { stake: restored.wager.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Pachinko.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, drop, and settlement.
async function drop() {
  // Ignore repeated clicks while a drop is resolving.
  if (dropBusy || !root) return;
  // Clear any previous landed pocket and mark the drop busy before the request.
  landedPocket = null;
  dropBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once drop with a caller-stable retry id.
    const response = await post('/api/v1/games/pachinko/drops', { request_id: newRequestId(), stake });
    // Show the committed debit before the ball reaches its authoritative pocket. (LEDGER-031, issue #597)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Animate the ball down the committed path so the visible landing is honest.
    await animate(round.detail.path);
    // Reveal the authoritative landed pocket.
    landedPocket = round.detail.pocket;
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Remember the settled stake so the next drop can repeat it with one click.
    lastBet = { stake };
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from authoritative values only.
    const text = `${safe(tx('result.landed', { mult: round.detail.multiplier }, round.detail.multiplier + 'x'))} <span class="net">${net > 0 ? '+' + net : net}</span>`;
    // Release the guard before the final repaint.
    dropBusy = false;
    // Repaint with the landed pocket highlighted and the result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    dropBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.drop', null, 'Drop could not be completed.'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last committed stake and re-fire one drop without a timer.
async function repeat() {
  // Ignore repeat while a drop is resolving or before any settled drop exists.
  if (dropBusy || !lastBet || !root) return;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared drop action with the restored stake.
  await drop();
}

// Export the isolated Pachinko game for the shared shell.
export const PachinkoGame = {
  // Expose the stable catalog identifier.
  id: 'pachinko',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Reset the repeatable stake so another session never inherits it.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a drop owns the board.
    localeUnsubscribe = onLocaleChange(() => { if (!dropBusy) render(); });
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
    dropBusy = false;
    // Clear the repeatable stake so the next session starts fresh.
    lastBet = null;
  },
};
