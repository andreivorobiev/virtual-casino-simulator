// Isolated Trente et Quarante route for GitHub issue #147, on the shared exactly-once settlement core.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/trente_et_quarante';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'teq-styles';
// Publish the four selectable bets in stable order.
export const BETS = Object.freeze(['rouge', 'noir', 'couleur', 'inverse']);
// Publish the chip denominations offered for the stake.
const CHIPS = [1, 5, 25, 100];
// Fix the decorative deal duration; the outcome is already server-authoritative.
const DEAL_MS = 800;

// Store the current route outlet, chosen bet, chosen stake, and in-flight guard.
let root = null;
let selectedBet = 'rouge';
let stake = 5;
let dealBusy = false;
let localeUnsubscribe = null;
// Retain the last settled deal so a repaint after the coup keeps showing the rows.
let shownDeal = null;
// Retain the last settled bet target and stake so one click can repeat the same coup.
let lastBet = null;

// Translate one game-domain key with an optional fallback.
const tx = (key, params, fallback) => t(key, params || {}, 'games/trente_et_quarante') || fallback || key;

// Install compact game-owned styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.teq{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .teq-stage{display:grid;gap:14px;padding:12px;min-width:0;} .teq-row{display:grid;gap:6px;min-width:0;} .teq-row-head{display:flex;justify-content:space-between;align-items:baseline;font-weight:900;text-transform:uppercase;letter-spacing:.06em;font-size:12px;} .teq-row.noir .teq-row-head{color:#c9c9d4;} .teq-row.rouge .teq-row-head{color:#e0788a;} .teq-row-head .total{font-size:20px;} .teq-row.win{outline:2px solid var(--gold);outline-offset:4px;border-radius:10px;} .teq-cards{display:flex;gap:6px;flex-wrap:wrap;min-width:0;} .teq-card{width:40px;height:56px;display:grid;place-items:center;border-radius:8px;background:linear-gradient(160deg,#fbf3dd,#e2cf9d);font-weight:900;font-size:16px;box-shadow:0 4px 10px rgba(0,0,0,.35),inset 0 0 0 2px #a9791f;} .teq-card.red{color:#b41b29;} .teq-card.black{color:#161616;} .teq-panel{display:grid;gap:12px;min-width:0;} .teq-card-box{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .teq-card-box h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .teq-bets{display:grid;grid-template-columns:1fr 1fr;gap:8px;} .teq-bet{display:grid;gap:2px;padding:10px;border:2px solid transparent;border-radius:12px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;text-align:left;} .teq-bet small{font-weight:700;opacity:.8;font-size:11px;} .teq-bet[aria-pressed="true"]{border-color:var(--text);box-shadow:0 0 0 2px rgba(255,242,194,.5);} .teq-chips{display:flex;flex-wrap:wrap;gap:8px;} .teq-chip{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--border-soft,rgba(255,255,255,.18));border-radius:10px;background:rgba(255,255,255,.05);color:var(--text);font-weight:900;cursor:pointer;} .teq-chip[aria-pressed="true"]{border-color:var(--gold);background:rgba(231,189,88,.16);color:var(--text);} .teq-deal{width:100%;min-height:48px;border:none;border-radius:14px;background:linear-gradient(180deg,#b41b29,#7d1119);color:#fff;font-weight:900;font-size:16px;cursor:pointer;} .teq-deal:disabled{opacity:.55;cursor:not-allowed;} .teq-result{min-height:24px;font-size:15px;color:var(--text);} .teq-result .net{font-weight:900;} @media (max-width:900px){.teq{grid-template-columns:1fr;}}.teq-repeat{width:100%;min-height:46px;border:1px solid var(--gold);border-radius:14px;background:transparent;color:var(--gold);font-weight:900;font-size:16px;cursor:pointer;}.teq-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.appendChild(style);
}

// Generate one caller-stable retry identity for exactly-once settlement.
function newRequestId() {
  // Prefer a real UUID when the platform provides one.
  return (globalThis.crypto?.randomUUID?.() || `teq-${Date.now()}-${Math.floor(Math.random() * 1e9)}`);
}

// Build the card chips for one dealt row.
function rowCards(cards) {
  // Render each committed card with its rank and colour, or a placeholder before the first deal.
  return (cards || [{ rank: '?', color: 'red' }, { rank: '?', color: 'black' }]).map(card => `<div class="teq-card ${card.color === 'red' ? 'red' : 'black'}">${safe(card.rank)}</div>`).join('');
}

// Render the complete Trente et Quarante route into the outlet.
function render(resultText) {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the settled winner so the winning row can be highlighted.
  const winner = shownDeal ? shownDeal.winner : null;
  // Build the Noir and Rouge rows with their totals and cards.
  const noir = `<div class="teq-row noir ${winner === 'noir' ? 'win' : ''}"><div class="teq-row-head"><span>${safe(tx('row.noir', null, 'Noir'))}</span><span class="total">${shownDeal ? shownDeal.noir_total : '—'}</span></div><div class="teq-cards">${rowCards(shownDeal && shownDeal.noir)}</div></div>`;
  // Build the Rouge row similarly.
  const rouge = `<div class="teq-row rouge ${winner === 'rouge' ? 'win' : ''}"><div class="teq-row-head"><span>${safe(tx('row.rouge', null, 'Rouge'))}</span><span class="total">${shownDeal ? shownDeal.rouge_total : '—'}</span></div><div class="teq-cards">${rowCards(shownDeal && shownDeal.rouge)}</div></div>`;
  // Build the four bet buttons with localized labels and hints.
  const bets = BETS.map(bet => `<button class="teq-bet" data-bet="${bet}" type="button" aria-pressed="${selectedBet === bet}"><span>${safe(tx('bet.' + bet, null, bet))}</span><small>${safe(tx('bet.' + bet + '.hint', null, ''))}</small></button>`).join('');
  // Build the chip selector.
  const chips = CHIPS.map(value => `<button class="teq-chip" data-chip="${value}" type="button" aria-pressed="${stake === value}">${value}</button>`).join('');
  // Paint the whole route.
  root.innerHTML = `<section class="teq" data-testid="trente-et-quarante"><div class="teq-stage">${noir}${rouge}<p class="teq-result" data-testid="teq-result" role="status">${resultText || safe(tx('result.idle', null, 'Pick a bet and deal.'))}</p></div><div class="teq-panel"><div class="teq-card-box"><h3>${safe(tx('bet.title', null, 'Your bet'))}</h3><div class="teq-bets">${bets}</div></div><div class="teq-card-box"><h3>${safe(tx('stake.title', null, 'Stake'))}</h3><div class="teq-chips">${chips}</div></div><button class="teq-deal" data-testid="teq-deal" type="button" ${dealBusy ? 'disabled' : ''}>${safe(dealBusy ? tx('action.dealing', null, 'Dealing…') : tx('action.deal', null, 'Deal the coup'))}</button><button class="teq-repeat" data-testid="teq-repeat" data-action="repeat" type="button" ${dealBusy || !lastBet ? 'disabled' : ''}>${safe(tx('controls.repeat', null, 'Repeat bet'))}</button></div></section>`;
  // Wire the bet buttons.
  root.querySelectorAll('[data-bet]').forEach(btn => { btn.onclick = () => { selectedBet = btn.dataset.bet; render(); }; });
  // Wire the chip buttons.
  root.querySelectorAll('[data-chip]').forEach(btn => { btn.onclick = () => { stake = Number(btn.dataset.chip); render(); }; });
  // Wire the deal action.
  const dealBtn = root.querySelector('[data-testid="teq-deal"]');
  // Attach the deal handler only when a deal is not already running.
  if (dealBtn) dealBtn.onclick = deal;
  // Wire the one-click repeat that re-fires the previous bet.
  const repeatBtn = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler so a single click re-places the last bet.
  if (repeatBtn) repeatBtn.onclick = repeat;
}

// Re-apply the last settled bet and re-fire one coup without a timer.
async function repeat() {
  // Ignore repeat while a coup is resolving or before any settled bet exists.
  if (dealBusy || !lastBet) return;
  // Restore the previous bet target into the local configuration.
  selectedBet = lastBet.bet;
  // Restore the previous stake into the local configuration.
  stake = lastBet.stake;
  // Fire the shared exactly-once coup with the restored bet.
  await deal();
}

// Load session-bound state and render the first frame.
async function load() {
  // Read authoritative state so the render reflects the server, not client guesses.
  try {
    // Fetch the game state through the frozen v1 endpoint.
    const data = await api('/api/v1/games/trente-et-quarante/state');
    // Read the authoritative bounded recent-round history, newest first.
    const recent = data && data.state && data.state.recent_rounds;
    // Recover a repeatable bet from the newest settled round so repeat survives a reload.
    if (recent && recent.length && recent[0].public && recent[0].public.wager) lastBet = { bet: recent[0].public.wager.bet, stake: recent[0].public.wager.stake };
  } catch (err) {
    // Surface a load failure without breaking the shell.
    toast(tx('error.load', null, 'Could not load Trente et Quarante.'), 'error');
  }
  // Render the initial frame regardless so controls are usable.
  render();
}

// Execute one atomic wager, deal, and settlement.
async function deal() {
  // Ignore repeated clicks while a coup is resolving.
  if (dealBusy || !root) return;
  // Mark the deal busy and disable the control before the request.
  dealBusy = true;
  render();
  // Start protected settlement so the busy flag is always released.
  try {
    // Post the exactly-once coup with a caller-stable retry id and the chosen bet.
    const response = await post('/api/v1/games/trente-et-quarante/coups', { request_id: newRequestId(), bet: selectedBet, stake });
    // Read the authoritative settled round.
    const round = response.round;
    // Wait for the decorative deal to finish before revealing the rows.
    await new Promise(resolve => setTimeout(resolve, DEAL_MS));
    // Reveal the authoritative dealt rows and winner.
    shownDeal = round.detail;
    // Remember the settled bet and stake so one click can repeat the same coup.
    lastBet = { bet: round.wager.bet, stake: round.wager.stake };
    // Refresh the shell wallet after settlement credits are applied.
    await refreshBalance();
    // Read the settled net for the result line.
    const net = round.net;
    // Compose the localized result copy from the authoritative outcome and net.
    const text = `${safe(tx('outcome.' + round.outcome, null, round.outcome))} <span class="net">${net > 0 ? '+' + net : net}</span>`;
    // Release the guard before the final repaint.
    dealBusy = false;
    // Repaint with the dealt rows and result.
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

// Export the isolated Trente et Quarante game for the shared shell.
export const TrenteEtQuaranteGame = {
  // Expose the stable catalog identifier.
  id: 'trente_et_quarante',
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
    // Repaint localized strings on a locale change unless a coup owns the table.
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
