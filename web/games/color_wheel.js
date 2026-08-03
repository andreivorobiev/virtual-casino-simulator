// Isolated Color Wheel route for GitHub issue #152, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/color_wheel';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'color-wheel-styles';
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

// Store the current route outlet, selected bet, chosen stake, and in-flight guard.
let root = null;
let selectedColor = 'red';
let stake = 5;
let spinBusy = false;
let localeUnsubscribe = null;
// Track the wheel's current angle so each spin continues from where the last one stopped.
let wheelAngle = 0;
// Retain the last committed colour and stake so one click can repeat the same spin.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/color_wheel') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.color-wheel{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .cw-stage{display:grid;justify-items:center;gap:14px;padding:12px;min-width:0;} .cw-wheel-wrap{position:relative;width:min(340px,72vw);aspect-ratio:1;} .cw-wheel{width:100%;height:100%;border-radius:50%;border:8px solid #e7bd58;box-shadow:0 12px 40px rgba(0,0,0,.45),inset 0 0 0 3px #4d2707;transition:transform ' + (SPIN_MS/1000) + 's cubic-bezier(.15,.6,.15,1);} .cw-pointer{position:absolute;top:-6px;left:50%;transform:translateX(-50%);width:0;height:0;border-left:12px solid transparent;border-right:12px solid transparent;border-top:22px solid #f1ca62;filter:drop-shadow(0 2px 3px rgba(0,0,0,.5));z-index:2;} .cw-hub{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:54px;height:54px;border-radius:50%;background:radial-gradient(circle at 38% 34%,#fff5bd,#6b350d);border:2px solid #f2d77d;} .cw-panel{display:grid;gap:12px;min-width:0;} .cw-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .cw-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .cw-bets{display:grid;grid-template-columns:1fr 1fr;gap:8px;} .cw-bet{display:grid;gap:2px;padding:10px;border:2px solid transparent;border-radius:12px;color:#fff;font-weight:900;cursor:pointer;text-align:left;} .cw-bet small{font-weight:700;opacity:.85;font-size:11px;} .cw-bet.red{background:linear-gradient(180deg,#d6323d,#8e1822);} .cw-bet.black{background:linear-gradient(180deg,#2a2a2a,#0e0e0e);} .cw-bet.green{background:linear-gradient(180deg,#0f9c4c,#0a5f2e);} .cw-bet.gold{background:linear-gradient(180deg,#f0c45d,#a9791f);color:#241006;} .cw-bet[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 2px rgba(34,224,195,.5);} .cw-chips{display:flex;flex-wrap:wrap;gap:8px;} .cw-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .cw-chip[aria-pressed="true"]{border-color:#e7bd58;background:rgba(231,189,88,.16);color:var(--text);} .cw-spin{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,#d6323d,#8e1822);color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .cw-spin:disabled{opacity:.55;cursor:not-allowed;} .cw-result{min-height:66px;font-size:15px;color:var(--text);} .cw-result .net{font-weight:900;} @media (max-width:900px){.color-wheel{grid-template-columns:1fr;}} @media (max-width:640px){.cw-panel{padding-right:160px;}body:has(.color-wheel) .report-problem-fab{width:144px;max-width:144px;white-space:normal;line-height:1.1;}}.cw-repeat{width:100%;min-height:46px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.cw-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

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

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `cw-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Color Wheel route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the bet buttons with localized labels and payout hints.
  const bets = COLORS.map(color => {
    // Count this colour's segments for an honest odds hint.
    const count = SEGMENTS.filter(c => c === color).length;
    // Read the payout multiplier for the hint.
    const mult = { red: 2, black: 2, green: 6, gold: 16 }[color];
    // Return one pressable bet button.
    return `<button class="cw-bet ${color}" data-color="${color}" type="button" aria-pressed="${selectedColor === color}"><span>${safe(tx('bet.' + color, null, color))}</span><small>${count}/20 · ${mult}x</small></button>`;
  }).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="cw-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="color-wheel" data-testid="color-wheel"><div class="cw-stage"><div class="cw-wheel-wrap"><div class="cw-pointer"></div><div class="cw-wheel" data-testid="color-wheel-disc" style="background:${wheelGradient()};transform:rotate(${wheelAngle}deg);"></div><div class="cw-hub"></div></div><p class="cw-result" data-testid="color-wheel-result" role="status">${resultText || safe(tx('result.idle', null, 'Choose a colour and spin.'))}</p></div><div class="cw-panel"><div class="cw-card"><h3>${safe(tx('bet.title', null, 'Your colour'))}</h3><div class="cw-bets">${bets}</div></div><div class="cw-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="cw-chips">${chips}</div></div><button class="cw-spin" data-testid="color-wheel-spin" type="button" ${spinBusy ? 'disabled' : ''}>${safe(spinBusy ? tx('action.spinning', null, 'Spinning…') : tx('action.spin', null, 'Spin the wheel'))}</button><button class="cw-repeat" data-testid="color-wheel-repeat" type="button" ${(spinBusy || !lastBet) ? 'disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
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
    toast(tx('error.load', null, 'Could not load Color Wheel.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Re-place the previous colour and stake and re-fire one spin without a timer.
async function repeat() {
  // Ignore repeat while a spin is resolving, after teardown, or without a prior bet.
  if (spinBusy || !root || !lastBet) return;
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
  if (spinBusy || !root) return;
  // Mark the spin busy and disable the control before the request.
  spinBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once spin with a caller-stable retry id.
    const response = await post('/api/v1/games/color-wheel/spins', { request_id: newRequestId(), color: selectedColor, stake });
    // Read the authoritative landed segment and outcome.
    const round = response.round;
    // Remember the settled colour and stake so one click can repeat the same bet next spin.
    lastBet = { color: round.wager?.color ?? selectedColor, stake: round.wager?.stake ?? stake };
    // Animate the wheel to the winning segment.
    wheelAngle = rotationForSegment(round.detail.segment);
    // Apply the rotation to the disc immediately for the CSS transition.
    const disc = root.querySelector('[data-testid="color-wheel-disc"]');
    // Rotate the disc when it is present.
    if (disc) disc.style.transform = `rotate(${wheelAngle}deg)`;
    // Wait for the decorative spin to finish before revealing the outcome.
    await new Promise(resolve => setTimeout(resolve, SPIN_MS));
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Build the localized result copy from authoritative values only.
    const win = round.total_return > 0;
    // Compose the result line with the landed colour and the net.
    const text = `${safe(tx('result.landed', { color: tx('bet.' + round.detail.color, null, round.detail.color) }, 'Landed on ' + round.detail.color))} <span class="net">${win ? '+' + (round.total_return - round.wager_total) : round.net}</span>`;
    // Announce the result via voice-neutral status copy.
    spinBusy = false;
    // Repaint with the result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    spinBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.spin', null, 'Spin could not be completed.'), 'error');
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
    // Store the current route outlet.
    root = node;
    // Reset any repeatable bet so a new mount never inherits a stale one before load reconciles history.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a spin owns the wheel.
    localeUnsubscribe = onLocaleChange(() => { if (!spinBusy) render(); });
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
    spinBusy = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
