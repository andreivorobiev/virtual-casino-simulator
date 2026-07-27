// Isolated Coin Pusher route for GitHub issue #156, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/coin_pusher';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'coin-pusher-styles';
// Mirror the backend tipping threshold for the fill meter.
export const THRESHOLD = 12;
// Mirror the backend cascade multipliers by coin count.
export const CASCADES = Object.freeze([[1, 1.5], [2, 4], [3, 6], [4, 16]]);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative drop duration; the outcome is already server-authoritative.
const DROP_MS = 700;

// Store the current route outlet, chosen stake, and in-flight guard.
let root = null;
let stake = 5;
let dropBusy = false;
let localeUnsubscribe = null;
// Retain the last settled drop so a repaint after the drop keeps showing the shelf.
let shownDrop = null;
// Retain the last committed stake so one click can drop again at the same stake.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/coin_pusher') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.coinp{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .cp-stage{display:grid;justify-items:center;gap:14px;padding:12px;min-width:0;} .cp-machine{width:min(340px,80vw);display:grid;gap:10px;} .cp-tray{position:relative;height:120px;border-radius:14px 14px 8px 8px;background:linear-gradient(180deg,#1a2b3a,#0a1520);border:5px solid #e7bd58;overflow:hidden;box-shadow:inset 0 8px 24px rgba(0,0,0,.5);} .cp-fill{position:absolute;left:0;bottom:0;width:100%;background:linear-gradient(180deg,rgba(231,189,88,.35),rgba(231,189,88,.7));transition:height .4s ease;} .cp-coins{position:absolute;bottom:6px;width:100%;display:flex;justify-content:center;gap:4px;flex-wrap:wrap;padding:0 8px;} .cp-coin{width:22px;height:22px;border-radius:50%;background:radial-gradient(circle at 36% 32%,#fff3bd,#a9791f);box-shadow:0 2px 4px rgba(0,0,0,.4);} .cp-coin.drop{animation:cp-fall .5s ease forwards;} @keyframes cp-fall{to{transform:translateY(60px);opacity:0;}} .cp-edge{height:8px;border-radius:0 0 8px 8px;background:linear-gradient(180deg,#e7bd58,#a9791f);} .cp-meter{display:flex;justify-content:space-between;font-size:12px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:.06em;} .cp-panel{display:grid;gap:12px;min-width:0;} .cp-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .cp-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .cp-pays{display:grid;gap:6px;font-size:13px;font-weight:700;} .cp-pays div{display:flex;justify-content:space-between;} .cp-pays span:last-child{color:var(--gold);} .cp-chips{display:flex;flex-wrap:wrap;gap:8px;} .cp-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .cp-chip[aria-pressed="true"]{border-color:#e7bd58;background:rgba(231,189,88,.16);color:#fff2c2;} .cp-drop{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,var(--gold),var(--brand-strong));color:#241006;font-weight:900;font-size:16px;cursor:pointer;} .cp-drop:disabled{opacity:.55;cursor:not-allowed;} .cp-result{min-height:24px;font-size:15px;color:var(--text);text-align:center;} .cp-result .net{font-weight:900;} @media (prefers-reduced-motion:reduce){.cp-coin.drop{animation:none;opacity:0;}} @media (max-width:900px){.coinp{grid-template-columns:1fr;}}.cp-repeat{width:100%;min-height:46px;border:1px solid rgba(255,215,120,.55);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.cp-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `cp-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Coin Pusher route into the outlet.
function render(resultText) {
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
  const pays = CASCADES.map(([count, mult]) => `<div><span>${safe(tx('pay.coins', { count }, count + ' coins'))}</span><span>${mult}x</span></div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="cp-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="coinp" data-testid="coin-pusher"><div class="cp-stage"><div class="cp-machine"><div class="cp-tray" data-testid="coin-pusher-tray"><div class="cp-fill" style="height:${fillPct}%;"></div><div class="cp-coins">${cascade}</div></div><div class="cp-edge"></div><div class="cp-meter"><span>${safe(tx('meter.shelf', null, 'Shelf'))}</span><span>${filled}/${THRESHOLD}</span></div></div><p class="cp-result" data-testid="coin-pusher-result" role="status">${resultText || safe(tx('result.idle', null, 'Set a stake and drop a coin.'))}</p></div><div class="cp-panel"><div class="cp-card"><h3>${safe(tx('pay.title', null, 'Cascade payouts'))}</h3><div class="cp-pays">${pays}</div></div><div class="cp-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="cp-chips">${chips}</div></div><button class="cp-drop" data-testid="coin-pusher-drop" type="button" ${dropBusy ? 'disabled' : ''}>${safe(dropBusy ? tx('action.dropping', null, 'Dropping…') : tx('action.drop', null, 'Drop a coin'))}</button><button class="cp-repeat" data-testid="coin-pusher-repeat" type="button" ${(dropBusy || !lastBet) ? 'disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
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
    toast(tx('error.load', null, 'Could not load Coin Pusher.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, drop, and settlement.
async function drop() {
  // Ignore repeated clicks while a drop is resolving.
  if (dropBusy || !root) return;
  // Mark the drop busy and disable the control before the request.
  dropBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once drop with a caller-stable retry id.
    const response = await post('/api/v1/games/coin-pusher/drops', { request_id: newRequestId(), stake });
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
      ? `${safe(tx('result.cascade', { coins: round.detail.coins }, round.detail.coins + ' coins fell'))} <span class="net">+${net > 0 ? net : round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.hold', null, 'Nothing tipped over.'))} <span class="net">${net}</span>`;
    // Release the guard before the final repaint.
    dropBusy = false;
    // Repaint with the settled shelf and result.
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

// Re-apply the last committed stake and drop again without any timer.
async function repeat() {
  // Ignore repeat while a drop resolves, the route is gone, or no prior drop exists.
  if (dropBusy || !root || !lastBet) return;
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
    // Store the current route outlet.
    root = node;
    // Clear any repeatable stake so a new session never inherits the prior one.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a drop owns the machine.
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
