// Implement the isolated Over/Under 7 route for GitHub issue #135.
// Import standard API helpers so requests use the shared envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared #97 motion scope so dice reveal timers are route-owned.
import { createMotionTimerScope } from '../core/motion.js';
// Import game-domain localization and locale-change helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/over_under_7';
// Store the route-local style id so remounts never duplicate CSS.
const STYLE_ID = 'over-under-7-styles';
// Store the decorative dice reveal duration.
export const ROLL_DURATION_MS = 900;
// Store stable wager targets in the same order as the backend.
export const OUTCOME_IDS = Object.freeze(['under', 'seven', 'over']);
// Define compact game-owned styles without touching shared CSS.
const ROUTE_CSS = [
  '.over-under-7{display:grid;gap:12px;min-height:100%;color:var(--text,#f5ead6);}', // Establish a stable route-local surface.
  '.ou7-header{display:flex;align-items:end;justify-content:space-between;gap:16px;padding:4px 2px;}', // Keep title and phase compact.
  '.ou7-header h1{margin:0;color:var(--gold,#f2c55c);font-size:clamp(30px,4vw,52px);}', // Make the game title the first visual level.
  '.ou7-phase{padding:7px 12px;border:1px solid rgba(242,197,92,.42);border-radius:999px;background:rgba(5,29,20,.9);}', // Reserve a concise phase chip.
  '.ou7-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(420px,1.8fr) minmax(220px,.72fr);gap:14px;min-height:0;}', // Keep dice stage visually dominant.
  '.ou7-panel{padding:16px;border:1px solid rgba(242,197,92,.28);border-radius:18px;background:rgba(3,24,17,.9);}', // Separate controls, stage, and data.
  '.ou7-controls{display:grid;align-content:start;gap:12px;}', // Keep wager actions in one rail.
  '.ou7-bet{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:8px;align-items:center;}', // Align labels and wager amounts.
  '.ou7-bet input{min-height:44px;min-width:0;}', // Preserve keyboard and touch target size.
  '.ou7-play{min-height:46px;border:0;border-radius:12px;color:white;background:#a71922;font-weight:800;}', // Use shared red primary-action convention.
  '.ou7-play:disabled{opacity:.58;cursor:not-allowed;}', // Keep unavailable action state readable.
  '.ou7-stage{display:grid;grid-template-rows:auto minmax(0,1fr) auto;place-items:center;gap:16px;overflow:hidden;}', // Reserve a stable dice stage.
  '.ou7-dice{display:flex;align-items:center;justify-content:center;gap:18px;width:100%;min-height:240px;}', // Keep dice central and stable.
  '.ou7-die{display:grid;place-items:center;width:min(30vw,150px);aspect-ratio:1;border:3px solid #f0cf74;border-radius:18px;background:linear-gradient(145deg,#f9f1d5,#d7ba70);color:#10271d;font-size:clamp(44px,8vw,84px);font-weight:1000;box-shadow:0 16px 36px rgba(0,0,0,.38);}', // Render reliable code-native dice.
  '.ou7-die.rolling{animation:ou7Roll .18s linear infinite;}', // Use transform-only decorative motion.
  '.ou7-result{display:grid;gap:4px;min-height:70px;text-align:center;}', // Reserve result space so layout does not shift.
  '.ou7-total{font-size:clamp(34px,6vw,64px);font-weight:1000;color:#ffe8a4;}', // Emphasize the rolled total.
  '.ou7-data{display:grid;align-content:start;gap:12px;}', // Keep paytable and history distinct.
  '.ou7-payrow,.ou7-history-row{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.08);}', // Align compact rows.
  '.ou7-history{max-height:260px;overflow:auto;scrollbar-width:thin;}', // Give data rail one focusable scroll region.
  '.ou7-error{min-height:20px;color:#ffb9b9;}', // Reserve validation and API feedback.
  '@keyframes ou7Roll{from{transform:translateY(-3px) rotate(-2deg)}to{transform:translateY(3px) rotate(2deg)}}', // Keep dice motion decorative and transform-only.
  '@media(max-width:1200px){.ou7-layout{grid-template-columns:1fr}.ou7-controls{order:1}.ou7-stage{order:2}.ou7-data{order:3}.ou7-dice{min-height:210px}}', // Stack control, stage, then data.
  '@media(max-width:560px){.ou7-header{align-items:start;flex-direction:column}.ou7-panel{padding:12px}.ou7-bet{grid-template-columns:minmax(0,1fr) 84px}.ou7-die{border-radius:14px}.ou7-dice{gap:10px;min-height:170px}}', // Preserve mobile containment.
  '@media(prefers-reduced-motion:reduce){.over-under-7 *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}', // Respect platform reduced motion.
].join(''); // Combine CSS chunks into one injected payload.

// Store the current route outlet while mounted.
let root = null;
// Store the latest backend state payload.
let gameState = { rules: { paytable: [] }, state: { recent_rounds: [] } };
// Store locally edited wagers before submission.
let wagers = {};
// Store the latest settled round for the stage.
let latestRound = null;
// Store whether an action request or reveal is active.
let playPending = false;
// Store the current player-facing phase key.
let phase = 'phase.ready';
// Store the disposable timer scope for this mount.
let motionScope = null;
// Store whether the current reveal used reduced motion.
let reducedMotionActive = false;
// Store the locale subscription cleanup callback.
let localeUnsubscribe = null;

// Resolve one game-owned string from the active locale.
const tx = (key, params = {}) => t(key, params, GAME_DOMAIN);
// Escape one localized string before markup insertion.
const text = (key, params = {}) => safe(tx(key, params));

// Create one retry-safe client action identity.
export function createActionId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require a secure UUID provider so accidental duplicate submissions do not collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Over/Under 7 plays');
  // Prefix the UUID for readable action diagnostics without player data.
  return `ou7-${randomUUID()}`;
}

// Schedule dice settlement through a lifecycle-owned motion scope.
export function scheduleDiceReveal({ timerScope, onSettled, duration = ROLL_DURATION_MS }) {
  // Require the shared timer-scope interface.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require an explicit callback owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Schedule through the route scope so unmount and reduced motion are honored.
  return timerScope.schedule(onSettled, duration);
}

// Install the game-owned style block once per document.
function ensureStyles() {
  // Reuse an existing style node on remount.
  if (document.getElementById(STYLE_ID)) return;
  // Create a style node through DOM APIs.
  const style = document.createElement('style');
  // Assign the stable node id.
  style.id = STYLE_ID;
  // Apply the route-local CSS.
  style.textContent = ROUTE_CSS;
  // Attach before first route paint.
  document.head.append(style);
}

// Format play-token amounts without currency symbols.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale at ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit.
  return translate('units.playTokens', { amount: number });
}

// Return localized wager controls.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend paytable metadata.
  return (gameState.rules?.paytable || []).map(row => `<label class="ou7-bet"><span>${safe(translate(`outcome.${row.id}`))} <small>${safe(translate('odds.net', { odds: row.net_odds }))}</small></span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(row.id)}" value="${safe(wagers[row.id] || '')}" aria-label="${safe(translate('wager.input', { outcome: translate(`outcome.${row.id}`) }))}"></label>`).join('');
}

// Return localized paytable disclosure rows.
function paytableHtml(translate = tx) {
  // Show winning totals and total return so rules are transparent.
  return (gameState.rules?.paytable || []).map(row => `<div class="ou7-payrow"><span>${safe(translate(`outcome.${row.id}`))}</span><span>${safe(translate('paytable.row', { totals: row.winning_totals.join(', '), return: row.total_return_multiplier }))}</span></div>`).join('');
}

// Return bounded recent-round history.
function historyHtml(translate = tx) {
  // Read newest results first for the data rail.
  const rows = [...(gameState.state?.recent_rounds || [])].reverse();
  // Return a localized empty state before the first play.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render one compact row per settled play.
  return rows.map(round => `<div class="ou7-history-row"><span>${safe(translate('history.roll', { total: round.total, dice: round.dice.join(' + ') }))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return one die pip or placeholder.
function dieValue(index) {
  // Use the authoritative latest round when present.
  if (latestRound?.dice?.[index]) return latestRound.dice[index];
  // Use a neutral placeholder before the first roll.
  return '–';
}

// Return the complete route markup.
export function viewMarkup({ translate = tx } = {}) {
  // Escape localized text through an injected translator for tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Resolve the latest outcome label or waiting copy.
  const outcome = latestRound ? translated(`outcome.${latestRound.outcome}`) : translated('result.waiting');
  // Resolve the result detail without creating fake totals.
  const detail = latestRound ? translated('result.detail', { total: latestRound.total, net: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Return the governed three-zone layout.
  return `<section class="over-under-7" data-testid="over-under-7"><header class="ou7-header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="ou7-phase" data-testid="over-under-7-phase">${translated(phase)}</span></header><div class="ou7-layout"><section class="ou7-panel ou7-controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="ou7-play" data-play type="button"${playPending ? ' disabled' : ''}>${translated(playPending ? 'action.rolling' : 'action.play')}</button><p class="ou7-error" data-error aria-live="polite"></p></section><section class="ou7-panel ou7-stage" aria-label="${translated('stage.aria')}"><div class="ou7-dice" aria-label="${translated('stage.diceAria')}"><span class="ou7-die${playPending && !reducedMotionActive ? ' rolling' : ''}" data-testid="ou7-die-1">${safe(dieValue(0))}</span><span class="ou7-die${playPending && !reducedMotionActive ? ' rolling' : ''}" data-testid="ou7-die-2">${safe(dieValue(1))}</span></div><div class="ou7-result" aria-live="polite"><strong class="ou7-total">${latestRound ? safe(latestRound.total) : translated('result.totalPlaceholder')}</strong><span>${outcome}</span><span>${detail}</span></div></section><aside class="ou7-panel ou7-data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="ou7-history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
}

// Render the route and reconnect inputs after DOM replacement.
function render() {
  // Ignore late renders after route teardown.
  if (!root) return;
  // Replace route markup atomically.
  root.innerHTML = viewMarkup();
  // Wire each wager input into local unsent state.
  root.querySelectorAll('[data-wager]').forEach(input => { input.oninput = () => { const amount = Number(input.value); if (Number.isFinite(amount) && amount > 0) wagers[input.dataset.wager] = amount; else delete wagers[input.dataset.wager]; }; });
  // Wire the one atomic play action.
  root.querySelector('[data-play]').onclick = play;
}

// Load session-bound state from the additive endpoint.
async function load() {
  // Fetch only the authenticated player's game state.
  gameState = await api('/api/v1/games/over-under-7/state');
  // Restore the latest result from player-owned history.
  latestRound = gameState.state?.recent_rounds?.length ? gameState.state.recent_rounds[gameState.state.recent_rounds.length - 1] : null;
  // Render after rules and history are available.
  render();
}

// Submit one complete wager map and present the settled result.
async function play() {
  // Ignore duplicate clicks while one action is active.
  if (playPending) return;
  // Require at least one positive wager before contacting the ledger endpoint.
  if (!Object.keys(wagers).length) {
    // Show localized guidance in the reserved error region.
    root.querySelector('[data-error]').textContent = tx('error.wagerRequired');
    // Stop without creating an action identity.
    return;
  }
  // Guard controls before sending the atomic request.
  playPending = true;
  // Move the phase to player-facing roll language.
  phase = 'phase.rolling';
  // Cancel prior reveal callbacks.
  motionScope.cancelAll();
  // Detect reduced motion for CSS evidence.
  reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
  // Render the rolling state.
  render();
  // Capture current route ownership.
  const mountedRoot = root;
  // Capture current timer ownership.
  const activeScope = motionScope;
  // Protect API and reveal work.
  try {
    // Submit one action id and complete wager map without caller player identity.
    const response = await post('/api/v1/games/over-under-7/plays', { action_id: createActionId(), wagers });
    // Stop if navigation replaced the route.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Store the authoritative settled round.
    latestRound = response.round;
    // Schedule the final reveal through the shared motion primitive.
    scheduleDiceReveal({ timerScope: activeScope, onSettled: async () => { phase = 'phase.settled'; playPending = false; gameState = await api('/api/v1/games/over-under-7/state'); render(); await refreshBalance(); } });
    // Render dice values while the reveal timer owns phase completion.
    render();
  // Handle API failures with localized feedback.
  } catch (error) {
    // Ignore late failures after route teardown.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Restore the ready phase.
    phase = 'phase.ready';
    // Re-enable controls.
    playPending = false;
    // Render before writing into the reserved error node.
    render();
    // Show localized failure copy.
    root.querySelector('[data-error]').textContent = tx('error.playFailed');
    // Also use shared feedback.
    toast(tx('error.playFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #77 integration.
export const OverUnder7Game = {
  // Expose the stable catalog identifier.
  id: 'over_under_7',
  // Mount the isolated route into the shared outlet.
  async mount(node) {
    // Store route ownership before async initialization.
    root = node;
    // Install game-owned CSS.
    ensureStyles();
    // Create one lifecycle-bound timer scope.
    motionScope = createMotionTimerScope();
    // Load game-owned locale dictionaries before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint on locale changes without losing state.
    localeUnsubscribe = onLocaleChange(() => render());
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release timers and subscriptions on route exit.
  unmount() {
    // Cancel all pending dice reveal callbacks.
    motionScope?.dispose();
    // Clear the disposed scope reference.
    motionScope = null;
    // Remove the locale subscription.
    localeUnsubscribe?.();
    // Clear the subscription reference.
    localeUnsubscribe = null;
    // Clear route ownership for late async guards.
    root = null;
    // Reset in-flight state for the next mount.
    playPending = false;
  },
};
