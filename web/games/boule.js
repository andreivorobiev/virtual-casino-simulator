// Isolated Boule route for GitHub issue #148, built on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/boule';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'boule-styles';
// Mirror the backend's nine drawable numbers in ascending order.
export const NUMBERS = Object.freeze([1, 2, 3, 4, 5, 6, 7, 8, 9]);
// Name the house number so the board can mark it distinctly.
const HOUSE_NUMBER = 5;
// Mirror the backend even-money groups and the numbers each covers.
export const EVEN_MONEY = Object.freeze({ low: [1, 2, 3, 4], high: [6, 7, 8, 9], odd: [1, 3, 7, 9], even: [2, 4, 6, 8] });
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative draw duration; the outcome is already server-authoritative.
const DRAW_MS = 800;

// Store the current route outlet, selected bet, chosen stake, and in-flight guard.
let root = null;
let selectedBet = { bet: 'even' };
let stake = 5;
let spinBusy = false;
let localeUnsubscribe = null;
// Retain the last drawn number so a repaint after the draw keeps showing the result.
let shownNumber = null;
// Retain the last settled bet config so one click can re-place and re-spin it.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/boule') || fallback || key;

// Compare the active selection against a candidate bet for pressed state.
function isSelected(bet, number) {
  // A named even-money selection matches on its family with no number.
  if (number === undefined) return selectedBet.bet === bet && selectedBet.number === undefined;
  // A straight selection matches on the number.
  return selectedBet.bet === 'number' && selectedBet.number === number;
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
  style.textContent = '.boule{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .bl-stage{display:grid;justify-items:center;gap:16px;padding:12px;min-width:0;} .bl-drum{width:120px;height:120px;border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at 38% 32%,#14622f,#062713);border:6px solid #e7bd58;box-shadow:0 12px 34px rgba(0,0,0,.45);font-size:48px;font-weight:900;color:#fff2c2;} .bl-drum.rolling{animation:bl-pulse .3s linear infinite;} @keyframes bl-pulse{0%,100%{transform:scale(1);}50%{transform:scale(1.06);}} .bl-numbers{display:grid;grid-template-columns:repeat(9,1fr);gap:6px;width:100%;max-width:420px;min-width:0;} .bl-num{min-height:44px;border:2px solid transparent;border-radius:10px;background:rgba(255,255,255,.06);color:var(--text);font-weight:900;cursor:pointer;} .bl-num.house{background:rgba(231,189,88,.16);color:#f2d77d;} .bl-num[aria-pressed="true"]{border-color:var(--text);box-shadow:0 0 0 2px rgba(255,242,194,.5);} .bl-panel{display:grid;gap:12px;min-width:0;} .bl-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .bl-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .bl-bets{display:grid;grid-template-columns:1fr 1fr;gap:8px;} .bl-bet{display:grid;gap:2px;padding:10px;border:2px solid transparent;border-radius:12px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;text-align:left;} .bl-bet small{font-weight:700;opacity:.8;font-size:11px;} .bl-bet[aria-pressed="true"]{border-color:var(--text);box-shadow:0 0 0 2px rgba(255,242,194,.5);} .bl-chips{display:flex;flex-wrap:wrap;gap:8px;} .bl-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .bl-chip[aria-pressed="true"]{border-color:var(--gold);background:rgba(231,189,88,.16);color:var(--text);} .bl-spin{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,#0f9c4c,#0a5f2e);color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .bl-spin:disabled{opacity:.55;cursor:not-allowed;} .bl-result{min-height:44px;font-size:15px;color:var(--text);text-align:center;} .bl-result .net{font-weight:900;} @media (prefers-reduced-motion:reduce){.bl-drum.rolling{animation:none;}} @media (max-width:900px){.boule{grid-template-columns:1fr;}}.bl-repeat{width:100%;min-height:46px;margin-top:8px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.bl-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `bl-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Boule route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Build the drum face showing the last drawn number or a neutral placeholder.
  const drum = shownNumber === null ? '&middot;' : String(shownNumber);
  // Build the nine straight-number cells, marking the house number.
  const numbers = NUMBERS.map(n => `<button class="bl-num${n === HOUSE_NUMBER ? ' house' : ''}" data-number="${n}" type="button" aria-pressed="${isSelected('number', n)}">${n}</button>`).join('');
  // Build the four even-money bet buttons with honest coverage and payout hints.
  const bets = ['low', 'high', 'odd', 'even'].map(name => `<button class="bl-bet" data-bet="${name}" type="button" aria-pressed="${isSelected(name)}"><span>${safe(tx('bet.' + name, null, name))}</span><small>${EVEN_MONEY[name].join(' ')} &middot; 2x</small></button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="bl-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Enable the one-click repeat only when a prior settled bet exists and no spin is running.
  const repeatDisabled = spinBusy || !lastBet;
  // Paint the whole route.
  root.innerHTML = `<section class="boule" data-testid="boule"><div class="bl-stage"><div class="bl-drum${spinBusy ? ' rolling' : ''}" data-testid="boule-drum">${drum}</div><div class="bl-numbers">${numbers}</div><p class="bl-result" data-testid="boule-result" role="status">${resultText || safe(tx('result.idle', null, 'Pick a bet and spin.'))}</p></div><div class="bl-panel"><div class="bl-card"><h3>${safe(tx('bet.title', null, 'Even-money bets'))}</h3><div class="bl-bets">${bets}</div></div><div class="bl-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="bl-chips">${chips}</div></div><button class="bl-spin" data-testid="boule-spin" type="button" ${spinBusy ? 'disabled' : ''}>${safe(spinBusy ? tx('action.spinning', null, 'Spinning…') : tx('action.spin', null, 'Spin the boule'))}</button><button type="button" class="bl-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
  // Wire the even-money bet buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = { bet: btn.dataset.bet }; render(); }; });
  // Wire the straight-number cells.
  root.querySelectorAll('[data-number]').forEach(btn => { btn.onclick = () => { selectedBet = { bet: 'number', number: Number(btn.dataset.number) }; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the spin action.
  const spinBtn = root.querySelector('[data-testid="boule-spin"]');
  // Attach the spin handler only when a spin is not already running.
  if (spinBtn) spinBtn.onclick = spin;
  // Wire the one-click repeat that re-places the previous bet.
  const repeatBtn = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler so a settled bet can be replayed with one click.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Re-place the last settled bet and re-fire one spin without a timer.
async function repeat() {
  // Ignore repeat while a spin is resolving or before any settled bet exists.
  if (spinBusy || !root || !lastBet) return;
  // Restore the previous even-money family or straight-number selection.
  selectedBet = lastBet.number === undefined ? { bet: lastBet.bet } : { bet: lastBet.bet, number: lastBet.number };
  // Restore the previous stake.
  stake = lastBet.stake;
  // Re-fire the shared exactly-once spin with the restored bet.
  await spin();
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const payload = await api('/api/v1/games/boule/state');
    // Recover the repeatable bet from the newest settled round so repeat survives a reload.
    const recovered = payload?.state?.recent_rounds?.[0]?.public?.wager;
    // Restore the repeatable config only when a settled round is present.
    if (recovered) lastBet = { ...recovered };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Boule.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
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
    // Post the exactly-once spin with a caller-stable retry id and the current selection.
    const response = await post('/api/v1/games/boule/spins', { request_id: newRequestId(), ...selectedBet, stake });
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative draw to finish before revealing the number.
    await new Promise(resolve => setTimeout(resolve, DRAW_MS));
    // Reveal the authoritative drawn number.
    shownNumber = round.detail.number;
    // Remember the authoritative settled bet config so one click can repeat it.
    lastBet = { ...round.wager };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the round paid.
    const win = round.total_return > 0;
    // Compose the localized result copy from authoritative values only.
    const text = win
      ? `${safe(tx('result.win', { number: shownNumber }, 'Number ' + shownNumber + ' wins'))} <span class="net">+${round.total_return - round.wager_total}</span>`
      : `${safe(tx('result.lose', { number: shownNumber }, 'Number ' + shownNumber))} <span class="net">${round.net}</span>`;
    // Release the guard before the final repaint.
    spinBusy = false;
    // Repaint with the drawn number and result.
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

// Export the isolated Boule game for the shared shell.
export const BouleGame = {
  // Expose the stable catalog identifier.
  id: 'boule',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Reset the repeatable bet so another session never inherits it before recovery.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a spin owns the drum.
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
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
    // Reset the in-flight guard because teardown cancelled any presentation.
    spinBusy = false;
  },
};
