// Isolated Marble Race route for GitHub issue #157, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/marble_race';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'marble-race-styles';
// Mirror the backend's six marbles and their display colours in index order.
export const MARBLES = Object.freeze(['red', 'blue', 'green', 'yellow', 'purple', 'orange']);
// Map each marble to a concrete rendered fill.
const FILLS = { red: '#d6323d', blue: '#3d7ad6', green: '#0f9c4c', yellow: '#e7bd58', purple: '#9b59b6', orange: '#e07b39' };
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative race duration; the outcome is already server-authoritative.
const RACE_MS = 1300;

// Store the current route outlet, chosen bet, chosen marble, chosen stake, and in-flight guard.
let root = null;
let selectedBet = 'win';
let selectedMarble = 0;
let stake = 5;
let raceBusy = false;
let localeUnsubscribe = null;
// Retain the last settled finishing order so a repaint after the race keeps the result.
let shownOrder = null;
// Retain the last settled bet so one click can repeat the same marble and stake.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/marble_race') || fallback || key;

// Read the localized display name for a marble index.
const marbleName = index => tx('marble.' + MARBLES[index], null, MARBLES[index]);

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.marble{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .mr-stage{display:grid;gap:10px;padding:12px;min-width:0;} .mr-track{display:grid;gap:6px;min-width:0;} .mr-lane{display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:10px;background:rgba(255,255,255,.05);min-width:0;} .mr-lane.win{outline:2px solid var(--gold);outline-offset:2px;} .mr-marble{width:26px;height:26px;border-radius:50%;flex:0 0 auto;box-shadow:inset -3px -3px 6px rgba(0,0,0,.4),0 2px 4px rgba(0,0,0,.35);} .mr-name{font-weight:900;text-transform:capitalize;min-width:64px;} .mr-place{margin-left:auto;font-weight:900;color:var(--gold);font-size:13px;} .mr-panel{display:grid;gap:12px;min-width:0;} .mr-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);min-width:0;} .mr-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .mr-bets{display:flex;gap:8px;} .mr-bet{flex:1;min-width:0;padding:10px;border:2px solid transparent;border-radius:12px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .mr-bet small{display:block;font-weight:700;opacity:.8;font-size:11px;} .mr-bet[aria-pressed="true"]{border-color:var(--brand);box-shadow:0 0 0 2px rgba(255,59,107,.5);} .mr-picks{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;} .mr-pick{display:flex;align-items:center;gap:6px;min-width:0;padding:8px;border:2px solid transparent;border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:800;cursor:pointer;text-transform:capitalize;overflow-wrap:anywhere;} .mr-pick .dot{width:16px;height:16px;border-radius:50%;flex:0 0 auto;} .mr-pick[aria-pressed="true"]{border-color:var(--brand);box-shadow:0 0 0 2px rgba(255,59,107,.5);} .mr-chips{display:flex;flex-wrap:wrap;gap:8px;} .mr-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .mr-chip[aria-pressed="true"]{border-color:#e7bd58;background:rgba(231,189,88,.16);color:var(--text);} .mr-go{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,var(--brand),#d21f4f);color:var(--text);font-weight:900;font-size:16px;cursor:pointer;} .mr-go:disabled{opacity:.55;cursor:not-allowed;} .mr-result{min-height:24px;font-size:15px;color:var(--text);} .mr-result .net{font-weight:900;} @media (max-width:900px){.marble{grid-template-columns:1fr;}}.mr-repeat{width:100%;min-height:44px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.mr-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `mr-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Render the complete Marble Race route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Compute each marble's finishing place from the settled order, if any.
  const placeOf = {};
  // Record one-based finishing places when a race has settled.
  if (shownOrder) shownOrder.forEach((marble, index) => { placeOf[marble] = index + 1; });
  // Build one lane per marble in marble-index order, highlighting the winner.
  const lanes = MARBLES.map((color, index) => `<div class="mr-lane ${shownOrder && shownOrder[0] === index ? 'win' : ''}"><span class="mr-marble" style="background:${FILLS[color]};"></span><span class="mr-name">${safe(marbleName(index))}</span><span class="mr-place">${placeOf[index] ? '#' + placeOf[index] : ''}</span></div>`).join('');
  // Build the two bet-market buttons with honest payout hints.
  const bets = [['win', '5.7x'], ['podium', '1.9x']].map(([bet, mult]) => `<button class="mr-bet" data-bet="${bet}" type="button" aria-pressed="${selectedBet === bet}"><span>${safe(tx('bet.' + bet, null, bet))}</span><small>${mult}</small></button>`).join('');
  // Build the six marble pick buttons.
  const picks = MARBLES.map((color, index) => `<button class="mr-pick" data-marble="${index}" type="button" aria-pressed="${selectedMarble === index}"><span class="dot" style="background:${FILLS[color]};"></span>${safe(marbleName(index))}</button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="mr-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="marble" data-testid="marble-race"><div class="mr-stage"><div class="mr-track" data-testid="marble-race-track">${lanes}</div><p class="mr-result" data-testid="marble-race-result" role="status">${resultText || safe(tx('result.idle', null, 'Pick a marble and race.'))}</p></div><div class="mr-panel"><div class="mr-card"><h3>${safe(tx('bet.title', null, 'Market'))}</h3><div class="mr-bets">${bets}</div></div><div class="mr-card"><h3>${safe(tx('pick.title', null, 'Your marble'))}</h3><div class="mr-picks">${picks}</div></div><div class="mr-card"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="mr-chips">${chips}</div></div><button class="mr-go" data-testid="marble-race-go" type="button" ${raceBusy ? 'disabled' : ''}>${safe(raceBusy ? tx('action.racing', null, 'Racing…') : tx('action.race', null, 'Start the race'))}</button><button class="mr-repeat" data-testid="marble-race-repeat" type="button" ${raceBusy || !lastBet ? 'disabled' : ''}>${safe(tx('action.repeat', null, 'Repeat bet'))}</button></div></section>`;
  // Wire the bet-market buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = btn.dataset.bet; render(); }; });
  // Wire the marble pick buttons.
  root.querySelectorAll('[data-marble]').forEach(btn => { btn.onclick = () => { selectedMarble = Number(btn.dataset.marble); render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the race action.
  const goBtn = root.querySelector('[data-testid="marble-race-go"]');
  // Attach the race handler only when a race is not already running.
  if (goBtn) goBtn.onclick = race;
  // Read the one-click repeat control created by this render.
  const repeatBtn = root.querySelector('[data-testid="marble-race-repeat"]');
  // Attach the repeat handler so one click replays the last settled bet.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const snapshot = await api('/api/v1/games/marble-race/state');
    // Recover a repeatable bet from the newest settled round so repeat survives a reload.
    const restored = snapshot?.state?.recent_rounds?.[0]?.public?.wager;
    // Restore the repeatable configuration only when a settled round is present.
    if (restored) lastBet = { bet: restored.bet, marble: restored.marble, stake: restored.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Marble Race.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Re-apply the last settled bet and re-race with one click, adding no timer.
async function repeat() {
  // Ignore repeat while a race is resolving, after teardown, or without a prior settled bet.
  if (raceBusy || !root || !lastBet) return;
  // Restore the previous bet market into the local configuration.
  selectedBet = lastBet.bet;
  // Restore the previous marble pick into the local configuration.
  selectedMarble = lastBet.marble;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once race with the restored configuration.
  await race();
}

// Execute one atomic wager, race, and settlement.
async function race() {
  // Ignore repeated clicks while a race is resolving.
  if (raceBusy || !root) return;
  // Mark the race busy and disable the control before the request.
  raceBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once race with a caller-stable retry id and the chosen bet.
    const response = await post('/api/v1/games/marble-race/races', { request_id: newRequestId(), bet: selectedBet, marble: selectedMarble, stake });
    // Show the committed debit before the finishing order becomes visible. (LEDGER-031, issue #596)
    renderCommittedWagerBalance(response.ledger?.wager);
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative race to finish before revealing the order.
    await new Promise(resolve => setTimeout(resolve, RACE_MS));
    // Reveal the authoritative finishing order.
    shownOrder = round.detail.order;
    // Remember the settled bet so one click can repeat the same marble and stake.
    lastBet = { bet: round.wager.bet, marble: round.wager.marble, stake: round.wager.stake };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read whether the bet won.
    const win = round.total_return > 0;
    // Compose the localized result copy naming the winning marble and the net.
    const text = `${safe(tx('result.finish', { winner: marbleName(round.detail.winner) }, marbleName(round.detail.winner) + ' wins'))} <span class="net">${win ? '+' + (round.total_return - round.wager_total) : round.net}</span>`;
    // Release the guard before the final repaint.
    raceBusy = false;
    // Repaint with the finishing order and result.
    render(text);
  } catch (err) {
    // Release the guard and report a bounded error.
    raceBusy = false;
    // Surface the failure without leaking internal detail.
    toast(err?.message || tx('error.race', null, 'Race could not be completed.'), 'error');
    // Repaint the unlocked controls.
    render();
  }
}

// Export the isolated Marble Race game for the shared shell.
export const MarbleRaceGame = {
  // Expose the stable catalog identifier.
  id: 'marble_race',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet.
    root = node;
    // Reset the repeatable bet so another session never inherits it before state loads.
    lastBet = null;
    // Install game-owned styles.
    ensureStyles();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings on a locale change unless a race owns the track.
    localeUnsubscribe = onLocaleChange(() => { if (!raceBusy) render(); });
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
    raceBusy = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
