// Isolated Poker Dice route for GitHub issue #151, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/poker_dice';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'poker-dice-styles';
// Mirror the backend's six poker-rank faces in ascending order for display.
export const FACES = Object.freeze(['9', '10', 'J', 'Q', 'K', 'A']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Mirror the backend paytable in descending hand order for an honest render.
export const PAYTABLE = Object.freeze([['five_of_a_kind', 80], ['four_of_a_kind', 15], ['full_house', 5], ['straight', 4], ['three_of_a_kind', 2]]);
// Fix the decorative roll duration; the outcome is already server-authoritative.
const ROLL_MS = 900;

// Store the current route outlet, chosen stake, and in-flight guard.
let root = null;
let stake = 5;
let rollBusy = false;
let localeUnsubscribe = null;
// Retain the last settled faces so a repaint after the roll keeps showing the result.
let shownFaces = ['9', '9', '9', '9', '9'];
// Retain the last committed stake so one click can repeat the same wager.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/poker_dice') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.poker-dice{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .pd-stage{display:grid;justify-items:center;gap:18px;padding:12px;min-width:0;} .pd-dice{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;min-width:0;} .pd-die{width:64px;height:64px;display:grid;place-items:center;border-radius:14px;background:linear-gradient(160deg,#fbf3dd,#d9c391);color:#241006;font-weight:900;font-size:26px;box-shadow:0 8px 18px rgba(0,0,0,.4),inset 0 0 0 2px #a9791f;} .pd-die.rolling{animation:pd-tumble .3s linear infinite;} @keyframes pd-tumble{0%{transform:translateY(0) rotate(0);}25%{transform:translateY(-8px) rotate(-8deg);}75%{transform:translateY(6px) rotate(8deg);}100%{transform:translateY(0) rotate(0);}} .pd-panel{display:grid;gap:12px;min-width:0;} .pd-card{padding:14px;border:1px solid rgba(255,217,120,.42);border-radius:16px;background:rgba(0,0,0,.22);} .pd-card h3{margin:0 0 10px;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .pd-paytable{display:grid;gap:6px;} .pd-payrow{display:flex;justify-content:space-between;font-weight:700;font-size:13px;} .pd-payrow span:last-child{color:#f2d77d;} .pd-chips{display:flex;flex-wrap:wrap;gap:8px;} .pd-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:#f5ead6;font-weight:900;cursor:pointer;} .pd-chip[aria-pressed="true"]{border-color:#e7bd58;background:rgba(231,189,88,.16);color:#fff2c2;} .pd-roll{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,#d6323d,#8e1822);color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .pd-roll:disabled{opacity:.55;cursor:not-allowed;} .pd-repeat{width:100%;min-height:46px;border:1px solid rgba(255,215,128,.55);border-radius:14px;background:transparent;color:#ffd780;font-weight:900;font-size:15px;cursor:pointer;} .pd-repeat:disabled{opacity:.5;cursor:not-allowed;} .pd-result{min-height:44px;font-size:15px;color:#fff2c2;text-align:center;} .pd-result .net{font-weight:900;} @media (prefers-reduced-motion:reduce){.pd-die.rolling{animation:none;}} @media (max-width:900px){.poker-dice{grid-template-columns:1fr;}}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `pd-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Poker Dice route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the five dice faces, tumbling while a roll is resolving.
  const dice = shownFaces.map(face => `<div class="pd-die${rollBusy ? ' rolling' : ''}" data-testid="poker-dice-die">${safe(face)}</div>`).join('');
  // Build the honest paytable rows from the mirrored backend table.
  const pays = PAYTABLE.map(([hand, mult]) => `<div class="pd-payrow"><span>${safe(tx('hand.' + hand, null, hand))}</span><span>${mult}x</span></div>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="pd-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Enable the one-click repeat only when a prior stake exists and no roll is resolving.
  const repeatDisabled = rollBusy || !lastBet;
  // Paint the whole route.
  root.innerHTML = `<section class="poker-dice" data-testid="poker-dice"><div class="pd-stage"><div class="pd-dice">${dice}</div><p class="pd-result" data-testid="poker-dice-result" role="status">${resultText || safe(tx('result.idle', null, 'Set a stake and roll the dice.'))}</p></div><div class="pd-panel"><div class="pd-card"><h3>${safe(tx('paytable.title', null, 'Paytable'))}</h3><div class="pd-paytable">${pays}</div></div><div class="pd-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="pd-chips">${chips}</div></div><button class="pd-roll" data-testid="poker-dice-roll" type="button" ${rollBusy ? 'disabled' : ''}>${safe(rollBusy ? tx('action.rolling', null, 'Rolling…') : tx('action.roll', null, 'Roll the dice'))}</button><button class="pd-repeat" data-testid="poker-dice-repeat" type="button" ${repeatDisabled ? 'disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the roll action.
  const rollBtn = root.querySelector('[data-testid="poker-dice-roll"]');
  // Attach the roll handler only when a roll is not already running.
  if (rollBtn) rollBtn.onclick = roll;
  // Wire the one-click repeat that re-fires the previous stake.
  const repeatBtn = root.querySelector('[data-testid="poker-dice-repeat"]');
  // Attach the repeat handler; it self-guards on busy state and a missing prior stake.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const response = await api('/api/v1/games/poker-dice/state');
    // Recover the newest settled round so repeat survives a reload.
    const recovered = response?.state?.recent_rounds?.[0]?.public;
    // Restore the repeatable stake only when a prior round exposes its committed total.
    if (recovered?.wager_total) lastBet = { stake: Number(recovered.wager_total) };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Poker Dice.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, roll, and settlement.
async function roll() {
  // Ignore repeated clicks while a roll is resolving.
  if (rollBusy || !root) return;
  // Mark the roll busy and disable the control before the request.
  rollBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once roll with a caller-stable retry id.
    const response = await post('/api/v1/games/poker-dice/rolls', { request_id: newRequestId(), stake });
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative tumble to finish before revealing the faces.
    await new Promise(resolve => setTimeout(resolve, ROLL_MS));
    // Reveal the authoritative faces.
    shownFaces = round.detail.faces;
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the round paid.
    const win = round.total_return > 0;
    // Compose the localized result copy from authoritative values only.
    const handName = tx('hand.' + round.detail.hand, null, round.detail.hand);
    // Build the result line naming the hand and the net.
    const text = win
      ? `${safe(tx('result.win', { hand: handName }, handName + '!'))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.lose', null, 'No paying hand.'))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    rollBusy = false;
    // Remember the settled stake so the next roll can repeat it with one click.
    lastBet = { stake };
    // Repaint with the settled faces and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    rollBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.roll', null, 'Roll could not be completed.'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Re-apply the last committed stake and re-fire one roll without a timer.
async function repeat() {
  // Ignore repeat while a roll is resolving, after teardown, or before any stake has been committed.
  if (rollBusy || !root || !lastBet) return;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once roll action with the restored stake.
  await roll();
}

// Export the isolated Poker Dice game for the shared shell.
export const PokerDiceGame = {
  // Expose the stable catalog identifier.
  id: 'poker_dice',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Reset the repeatable stake so a new session never inherits a prior bet.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a roll owns the dice.
    localeUnsubscribe = onLocaleChange(() => { if (!rollBusy) render(); });
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
    rollBusy = false;
    // Clear the repeatable stake so the next session starts fresh.
    lastBet = null;
  },
};
