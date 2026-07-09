// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can call frozen Roulette API endpoints.
import { api, post, del } from '../core/api.js';
// Import shared UI helpers so the Roulette surface matches the premium shell contract.
import { money, signedMoney, toast, refreshBalance, safe } from '../core/ui.js';
// Import autoplay renderer so Roulette keeps using the shared control-plane session behavior.
import { renderAutoplay } from '../core/autoplay.js';
// Import voice helpers so spin sounds and announcements preserve existing behavior.
import { speak, clickSound, rouletteRollSound } from '../core/voice.js';
// Import bot helpers so bots continue to act through the documented controller path.
import { botPanelHtml, playBotRound } from '../core/bots.js';
// Import i18n helpers so visible Roulette-owned strings refresh without remounting gameplay state.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the i18n resource domain owned by this game module.
const GAME_DOMAIN = 'games/roulette';
// Store the local style element id so repeated mounts do not duplicate Roulette-only CSS.
const PREMIUM_STYLE_ID = 'roulette-premium-style';
// Store chip denominations so the control rail remains stable across rerenders.
const CHIP_VALUES = [1, 5, 25, 100, 500, 1000];
// Store red pockets so wheel, table, and history pills share the same color logic.
const RED_NUMBERS = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
// Store board geometry so click targets and placed chips remain aligned on the fixed table.
const BOARD = { width: 760, height: 560, x0: 170, y0: 82, cw: 132, ch: 34 };
// Store premium Roulette CSS inside the owned module so shared foundation styles stay untouched.
const PREMIUM_STYLE = [
  '.roulette-premium{display:grid;grid-template-rows:auto minmax(0,1fr);gap:10px;height:100%;min-height:0;}', // Keep the route mounted inside the shared #view shell without page-level overflow.
  '.roulette-premium .roulette-header{display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,auto);gap:14px;align-items:end;min-height:92px;}', // Reserve a stable proposal-style heading and status ribbon band.
  '.roulette-premium .roulette-kicker{margin:0 0 4px;color:var(--muted);font-size:13px;}', // Match the small prerender kicker without adding explanatory UI text.
  '.roulette-premium h1{margin:0;color:#fff0b8;font-family:var(--font-display);font-size:52px;line-height:.95;text-shadow:0 2px 18px rgba(255,217,120,.16);}', // Make Roulette the first-viewport signal inside the game route.
  '.roulette-status-ribbon{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));overflow:hidden;border:1px solid rgba(255,217,120,.45);border-radius:8px;background:rgba(7,40,27,.76);}', // Mirror the approved four-cell state ribbon.
  '.roulette-status-ribbon span{display:grid;place-items:center;min-height:62px;padding:8px 10px;border-left:1px solid rgba(255,217,120,.18);color:#ffe9ad;font-size:12px;font-weight:900;text-align:center;}', // Keep ribbon text centered and contained.
  '.roulette-status-ribbon span:first-child{border-left:0;}', // Avoid double borders on the first ribbon cell.
  '.roulette-premium .game-layout{height:100%;min-height:0;}', // Keep the three-zone game grid stable inside the route body.
  '.roulette-premium .control-rail,.roulette-premium .details-drawer{background:linear-gradient(145deg,rgba(12,38,28,.94),rgba(3,17,12,.92));}', // Give side rails the darker premium table framing from the prerenders.
  '.roulette-control-section{margin-top:10px;}', // Space control groups without resizing the main stage.
  '.roulette-control-section h3{margin-bottom:6px;text-transform:uppercase;font-size:14px;letter-spacing:0;}', // Match compact rail labels while respecting the no-negative-letter-spacing rule.
  '.roulette-settings{display:grid;grid-template-columns:1fr;gap:8px;}', // Stack settings so localized labels fit inside the rail.
  '.roulette-settings label{display:grid;grid-template-columns:1fr;gap:5px;min-height:58px;padding:8px;border:1px solid var(--border-soft);border-radius:8px;background:rgba(255,255,255,.04);color:var(--muted);font-size:12px;}', // Keep select controls framed and scannable.
  '.roulette-settings select,.roulette-call-input{width:100%;min-height:34px;}', // Ensure form controls keep a predictable rail footprint.
  '.roulette-fast-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;}', // Arrange fast outside bets like the approved segmented rail.
  '.roulette-call-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;}', // Keep call-bet controls compact and balanced.
  '.roulette-fast-grid button,.roulette-call-grid button,.roulette-secondary-actions button{min-height:31px;padding:6px 8px;border-color:rgba(255,255,255,.16);border-radius:8px;background:rgba(255,255,255,.06);font-size:12px;}', // Make secondary controls polished without touching global buttons.
  '.roulette-secondary-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;}', // Keep rebet and spot toggles mounted in the same lane.
  '.roulette-control-plane{margin-top:8px;padding:10px;border:1px solid rgba(255,217,120,.35);border-radius:8px;background:rgba(255,217,120,.07);}', // Reuse the prerender control-plane treatment for custom panels.
  '.roulette-control-plane b{display:block;color:#ffe9ad;}', // Keep control-plane headings readable in both locales.
  '.roulette-control-plane span{display:block;margin-top:4px;color:var(--muted);font-size:12px;}', // Keep panel details fixed-size and muted.
  '.roulette-meter{height:7px;margin-top:8px;overflow:hidden;border-radius:999px;background:rgba(0,0,0,.35);}', // Reserve the meter track used by prerender status cards.
  '.roulette-meter i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#b62530,#ffd978);}', // Draw progress using transform-free paint only.
  '.roulette-premium .game-stage{padding:16px;background:linear-gradient(145deg,rgba(14,45,32,.94),rgba(3,18,13,.9));}', // Match the central premium stage surface.
  '.roulette-stage-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:64px;margin-bottom:10px;}', // Reserve toolbar space across betting, spinning, and settled states.
  '.roulette-stage-toolbar .eyebrow{margin:0;color:var(--muted);font-size:12px;}', // Keep round metadata compact.
  '.roulette-stage-toolbar h2{margin:2px 0 0;color:#fff0b8;font-family:var(--font-display);font-size:32px;}', // Use stage-scale type without crowding controls.
  '.roulette-stage-toolbar button{min-width:126px;min-height:44px;}', // Stabilize the primary action button.
  '.roulette-premium .roulette-stage{min-height:0;}', // Let the existing responsive grid control wheel/table placement.
  '.roulette-premium .wheel-card{position:relative;border-radius:8px;background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(0,0,0,.22)),#091811;}', // Bring the wheel panel closer to the approved mockup.
  '.roulette-premium .wheel-card.reveal-glow,.roulette-premium .wheel-card.result-glow{box-shadow:inset 0 0 45px rgba(243,199,102,.16),0 16px 34px rgba(0,0,0,.32);}', // Add state glow without changing layout.
  '.roulette-premium .roulette-wheel{filter:drop-shadow(0 18px 28px rgba(0,0,0,.46));}', // Give the vector wheel table depth.
  '.roulette-premium .fixed-result{display:grid;align-content:center;min-height:96px;border-radius:8px;}', // Keep the result region fixed through all spin states.
  '.roulette-premium .fixed-result.win{border-color:rgba(255,217,120,.66);background:linear-gradient(135deg,rgba(255,217,120,.12),rgba(116,24,28,.18));color:#ffe9ad;}', // Highlight settled results while staying within the rail palette.
  '.roulette-premium .roulette-table-board{height:590px;border-color:rgba(243,199,102,.62);border-radius:8px;background:linear-gradient(135deg,rgba(255,255,255,.04),rgba(0,0,0,.18)),linear-gradient(145deg,#0a5b35,#07301f);}', // Match the approved felt and gold trim while leaving room for the outside row.
  '.roulette-table-board.roulette-board-dimmed{filter:saturate(.86);}', // Dim the table during the spin/reveal state without resizing it.
  '.roulette-premium .table-cell,.roulette-premium .outside-cell{border-color:rgba(255,255,255,.58);border-radius:6px;}', // Polish existing table cells while preserving absolute hit areas.
  '.roulette-premium .table-cell.result-cell,.roulette-premium .outside-cell.result-cell{outline:3px solid #ffd978;box-shadow:inset 0 0 24px rgba(255,217,120,.36),0 0 18px rgba(255,217,120,.24);}', // Lock settled-result marker to the winning table area.
  '.roulette-result-marker{position:absolute;right:5px;bottom:3px;color:#ffd978;font-size:9px;font-weight:1000;}', // Keep the WIN marker small enough for table cells.
  '.roulette-premium .spot{width:16px;height:16px;border-width:1px;background:rgba(255,217,120,.36);opacity:.28;}', // Keep inside-bet hotspots discoverable without cluttering the premium felt.
  '.roulette-premium .spot:hover{opacity:1;}', // Make inside-bet hotspots clear on hover.
  '.roulette-premium .bet-chip{animation:rouletteChipPop .18s ease-out;}', // Make placed chips feel responsive without layout motion.
  '@keyframes rouletteChipPop{from{transform:scale(.82);opacity:.5;}to{transform:scale(1);opacity:1;}}', // Animate only transform and opacity per UX requirements.
  '.roulette-drawer-title{display:flex;align-items:center;justify-content:space-between;gap:8px;}', // Keep drawer headings and phase badges aligned.
  '.roulette-settlement-card{min-height:86px;margin:8px 0;padding:12px;border:1px solid rgba(255,217,120,.42);border-radius:8px;background:rgba(255,217,120,.08);}', // Reserve settlement space during spins and after results.
  '.roulette-settlement-card b{display:block;color:#ffe9ad;}', // Keep settlement card heading readable.
  '.roulette-settlement-card span{display:block;margin-top:6px;color:var(--muted);font-size:12px;}', // Keep settlement card detail compact.
  '.roulette-spark-bars{display:grid;grid-template-columns:repeat(8,1fr);align-items:end;gap:7px;height:72px;margin:8px 0;padding:10px;border:1px solid var(--border-soft);border-radius:8px;background:rgba(0,0,0,.16);}', // Reserve the recent-stats chart from the approved drawer.
  '.roulette-spark-bars i{display:block;min-height:10px;border-radius:6px 6px 2px 2px;background:linear-gradient(180deg,#ffd978,#b62530);}', // Draw simple stat bars from live frequency data.
  '.roulette-history-pills{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}', // Keep latest-result pills in a stable wrapping row.
  '.roulette-history-pills span{display:grid;place-items:center;width:32px;height:32px;border:1px solid var(--border-soft);border-radius:50%;background:rgba(0,0,0,.2);color:#f7e3bf;font-size:12px;}', // Render recent pockets as compact chips.
  '.roulette-history-pills span.result-cell{border-color:#ffd978;background:#ffd978;color:#1f1400;font-weight:1000;}', // Highlight the latest settled pocket.
  '.roulette-premium .stats-grid{grid-template-columns:repeat(5,1fr);}', // Keep dense frequency tiles from crowding the drawer.
  '.roulette-phase-badge{padding:4px 8px;border:1px solid var(--border-soft);border-radius:999px;color:var(--muted);font-size:12px;}', // Add a compact phase badge without expanding the drawer.
  '.roulette-premium .danger{min-width:72px;}', // Replace symbol-only remove controls with explicit text that localizes.
  '@media (max-width:1200px){.roulette-premium{height:auto;}.roulette-premium .roulette-header{grid-template-columns:1fr;}.roulette-status-ribbon{grid-template-columns:1fr 1fr;}.roulette-premium h1{font-size:40px;}}', // Preserve narrow viewport usability without shared CSS changes.
  '@media (max-width:560px){.roulette-status-ribbon{grid-template-columns:1fr;}.roulette-premium h1{font-size:34px;}.roulette-fast-grid,.roulette-call-grid,.roulette-secondary-actions{grid-template-columns:1fr;}}', // Keep all text inside controls on very narrow screens.
].join(''); // Combine Roulette-only CSS chunks into one style payload.

// Store the route root so async callbacks can rerender the currently mounted view.
let root = null;
// Store the latest Roulette state payload from the frozen API.
let state = null;
// Store the active bet catalog so click handlers can place documented bet types.
let catalog = [];
// Store the selected chip amount independently of locale and route rerenders.
let chip = 5;
// Store the mounted autoplay element so unmount can stop any local loop.
let autoBox = null;
// Store the spot-overlay preference across rerenders and locale changes.
let showSpots = false;
// Store bot panel markup so route rerenders do not flash an empty bot region.
let botPanelCache = '';
// Store the latest stats payload so locale-only rerenders do not call game APIs.
let lastStats = {};
// Store the latest actual spin result without ever inventing a zero fallback.
let lastSpinResult = null;
// Store the latest result color for result narration and styling.
let lastSpinColor = null;
// Store the latest settled round id for the stage toolbar.
let lastRoundId = null;
// Store the current visual phase so betting, spinning, and settlement regions stay stable.
let uiPhase = 'betting';
// Store human settlement rows from the latest spin for presentation-only settlement rendering.
let lastSettlements = [];
// Store the latest human net based on existing debits plus settlement credits.
let lastHumanNet = 0;
// Store the current spin guard so duplicate spin requests cannot start.
let spinBusy = false;
// Store the i18n unsubscribe callback so unmount does not leak locale listeners.
let localeUnsubscribe = null;

// Resolve a Roulette-owned localized string from the game domain.
const rt = (key, params = {}) => t(key, params, GAME_DOMAIN);
// Resolve and escape a localized string before inserting it into HTML.
const text = (key, params = {}) => safe(rt(key, params));
// Return a disabled attribute while a spin is in progress.
const disabledWhenSpinning = () => (spinBusy ? ' disabled' : '');
// Return a display-safe short money string for chip faces and table chips.
const chipMoney = amount => money(amount).replace('.00', '');

// Ensure the local premium CSS is available exactly once per document.
function ensurePremiumStyle() {
  // Branch when another mount already installed the Roulette style block.
  if (document.getElementById(PREMIUM_STYLE_ID)) return;
  // Create a style node owned by this module.
  const style = document.createElement('style');
  // Set the id so future mounts can find the existing style block.
  style.id = PREMIUM_STYLE_ID;
  // Set the CSS text without touching the shared stylesheet.
  style.textContent = PREMIUM_STYLE;
  // Attach the style block to the document head before the first render.
  document.head.append(style);
}

// Render the localized placeholder shown while bot controller data loads.
function loadingBotPanelHtml() {
  // Return the control-plane placeholder using Roulette-owned resources.
  return `<div class="roulette-control-plane"><b>${text('bots.loadingTitle')}</b><span>${text('bots.loading')}</span></div>`;
}

// Return the latest actual result entry recorded by the backend state.
function latestResultEntry() {
  // Store the history array so missing state falls back safely.
  const history = state?.last_results || [];
  // Return the final history entry or null when no real spin has occurred.
  return history.length ? history[history.length - 1] : null;
}

// Apply a frozen API payload to local render state without changing contracts.
function applyPayload(payload) {
  // Update game state when the endpoint returned one.
  if (payload?.state) state = payload.state;
  // Update bet catalog when the endpoint returned one.
  if (payload?.catalog) catalog = payload.catalog;
  // Cache shell-visible player rows when the endpoint returned them.
  if (payload?.players) window._lastPlayers = payload.players;
  // Cache stats when the endpoint returned them.
  if (payload?.stats) lastStats = payload.stats;
  // Store the latest real result entry after state has been updated.
  const latest = latestResultEntry();
  // Branch only when a backend result exists so the wheel never defaults to fake zero.
  if (latest) {
    // Store the actual result number from backend history.
    lastSpinResult = latest.result;
    // Store the actual result color from backend history.
    lastSpinColor = latest.color;
    // Store the actual round id from backend history.
    lastRoundId = latest.round_id;
  }
}

// Fetch state, catalog, stats, players, and bot presentation for the initial mount.
async function load() {
  // Initialize the localized bot placeholder before the first visible render.
  botPanelCache = loadingBotPanelHtml();
  // Load the current Roulette state through the frozen v1 endpoint.
  const payload = await api('/api/v1/games/roulette/state');
  // Apply the response to local render caches.
  applyPayload(payload);
  // Render the game before slower bot markup resolves.
  render();
  // Refresh bot panel markup through the shared bot controller helper.
  await updateBotPanel();
  // Refresh the shared shell wallet after game state loads.
  await refreshBalance();
}

// Refresh the bot panel inside the control rail without remounting the whole game.
async function updateBotPanel() {
  // Load bot markup through the shared controller contract.
  botPanelCache = await botPanelHtml('roulette');
  // Find the currently mounted bot panel region.
  const panel = root?.querySelector('#botPanel');
  // Replace bot markup only when Roulette is still mounted.
  if (panel) panel.innerHTML = botPanelCache;
}

// Return the current human-owned open-round bets.
function humanBets() {
  // Filter open bets to the human player while tolerating unloaded state.
  return state?.open_round?.bets?.filter(bet => bet.player_id === 'human') || [];
}

// Return the total human stake for a supplied or current bet list.
function humanBetTotal(bets = humanBets()) {
  // Sum numeric bet amounts for total and settlement displays.
  return bets.reduce((total, bet) => total + Number(bet.amount || 0), 0);
}

// Find a bet catalog entry by predicate.
function betBy(predicate) {
  // Return the matching catalog entry or undefined when the bet is unavailable.
  return catalog.find(predicate);
}

// Reset settlement drawer state when the player starts editing a new open round.
function markBettingPhase() {
  // Put the UI back into betting mode while preserving the last real result.
  uiPhase = 'betting';
}

// Place one documented Roulette bet using the existing public API.
async function placeBet(bet, amount = chip) {
  // Branch when a click target no longer maps to a legal catalog bet.
  if (!bet) {
    // Show a localized error without touching wallet or game state.
    toast(rt('errors.betUnavailable'));
    // Stop after reporting the unavailable bet.
    return;
  }
  // Post the bet through the frozen v1 endpoint.
  const payload = await post('/api/v1/games/roulette/bets', { player_id: 'human', amount, bet_type: bet.type, covered_numbers: bet.covered_numbers, label: bet.label });
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the premium table and drawer.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because bets debit immediately through the ledger.
  await refreshBalance();
  // Play the existing chip feedback sound.
  clickSound(540, .05);
}

// Place a racetrack or call bet through the documented API.
async function placeCall(type) {
  // Read the optional call/final number from the current control rail.
  const number = root.querySelector('#callNumber')?.value || undefined;
  // Post the call bet using the existing v1 payload shape.
  const payload = await post('/api/v1/games/roulette/call-bet', { player_id: 'human', amount: chip, call_type: type, number });
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the premium table and drawer.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because call bets debit immediately through the ledger.
  await refreshBalance();
  // Play the existing call-bet feedback sound.
  clickSound(650, .05);
}

// Clear one human bet by id through the documented refund endpoint.
async function clearBet(id) {
  // Delete the bet through the frozen v1 endpoint.
  const payload = await del(`/api/v1/games/roulette/bets/${id}`, { player_id: 'human' });
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the table and bet slip after the refund.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because clearing a bet credits the player.
  await refreshBalance();
}

// Clear all human bets through the documented refund endpoint.
async function clearAll() {
  // Post the clear request through the frozen v1 endpoint.
  const payload = await post('/api/v1/games/roulette/clear', { player_id: 'human' });
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the table and empty bet slip.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because clearing bets credits the player.
  await refreshBalance();
}

// Rebuild the previous human bet template through the documented endpoint.
async function rebet() {
  // Post the rebet request through the frozen v1 endpoint.
  const payload = await post('/api/v1/games/roulette/rebet', { player_id: 'human' });
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the table and bet slip.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because rebet debits immediately through the ledger.
  await refreshBalance();
  // Play the existing rebet feedback sound.
  clickSound(620, .06);
}

// Persist Roulette mode and zero-rule settings through the documented endpoint.
async function settings() {
  // Read the selected wheel mode from the control rail.
  const mode = root.querySelector('#mode')?.value;
  // Read the selected zero rule from the control rail.
  const zeroRule = root.querySelector('#zero')?.value;
  // Post settings without adding or changing any payload fields.
  const payload = await post('/api/v1/games/roulette/settings', { mode, zero_rule: zeroRule });
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender settings, table geometry, and bet targets.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
}

// Ensure autoplay has an open bet template before starting an automatic spin.
async function ensureBetForAuto() {
  // Branch when no open bet exists but the backend has a saved template.
  if (humanBets().length === 0 && (state.last_bet_template || []).length) await rebet();
}

// Spin the Roulette wheel using the existing engine, bot, ledger, and settlement path.
async function spin(show = true) {
  // Branch when a spin is already in progress.
  if (spinBusy) return;
  // Store the pre-spin stake after any autoplay rebet completes.
  let stakeBeforeSpin = 0;
  // Mark the spin as busy before rerendering disabled controls.
  spinBusy = true;
  // Start protected spin flow so the busy flag is always released.
  try {
    // Recreate a saved template for autoplay when needed.
    if (show) await ensureBetForAuto();
    // Store the human stake after any automatic rebet is in the open round.
    stakeBeforeSpin = humanBetTotal();
    // Move the UI into the spinning phase before the backend result is displayed.
    uiPhase = 'spinning';
    // Clear previous settlement rows while the new spin is resolving.
    lastSettlements = [];
    // Rerender immediately so animation starts before settlement display.
    render();
    // Let compatible bots commit their public Roulette actions before the human spin.
    await playBotRound('roulette');
    // Play the existing wheel rolling sound with shorter timing for autoplay.
    rouletteRollSound(show ? 2600 : 700);
    // Post the spin request through the frozen v1 endpoint without changing payloads.
    const payload = await post('/api/v1/games/roulette/spin', {});
    // Wait for the visual reveal lock before showing settlement.
    await new Promise(resolve => setTimeout(resolve, show ? 2600 : 250));
    // Apply returned state, catalog, players, and stats.
    applyPayload(payload);
    // Store the authoritative result from this spin response.
    lastSpinResult = payload.round.result;
    // Store the authoritative color from this spin response.
    lastSpinColor = payload.round.result_color;
    // Store the authoritative round id from this spin response.
    lastRoundId = payload.round.round_id;
    // Filter settlement rows to the human player for the drawer.
    const human = (payload.settlements || []).filter(row => row.bet.player_id === 'human');
    // Cache settlement row presentation using existing API values only.
    lastSettlements = human.map(row => ({ label: row.bet.label, amount: Number(row.bet.amount || 0), outcome: row.settlement.outcome, credit: Number(row.settlement.credit || 0) }));
    // Compute a presentation-only human net from already-debited stake and returned credits.
    lastHumanNet = human.reduce((total, row) => total + Number(row.settlement.credit || 0), 0) - stakeBeforeSpin;
    // Move the UI into the settled phase after animation lock-in.
    uiPhase = 'settled';
    // Rerender the table, result panel, stats, and settlement drawer.
    render();
    // Refresh the wallet after settlement credits are applied.
    await refreshBalance();
    // Play the existing result feedback sound.
    clickSound(240, .08);
    // Play the existing follow-up feedback sound after a short delay.
    setTimeout(() => clickSound(760, .08), 120);
    // Speak the result only for visible human spins.
    if (show) speak(rt('voice.rolled', { number: payload.round.result }), 'roulette');
  // Always release the spin guard and settle disabled controls.
  } finally {
    // Release the busy flag even if the API or animation flow fails.
    spinBusy = false;
    // Branch when a failed spin left the UI in the temporary spinning phase.
    if (uiPhase === 'spinning') {
      // Return to betting mode so controls are usable again.
      uiPhase = 'betting';
    }
    // Rerender the unlocked controls after both success and failure.
    render();
    // Refresh the bot panel after the final rerender.
    await updateBotPanel();
  }
}

// Return the color class for one Roulette number.
function numberColorClass(number) {
  // Treat zero pockets as green cells.
  if (String(number) === '0' || String(number) === '00') return 'green';
  // Return red or black based on the canonical red pocket set.
  return RED_NUMBERS.has(Number(number)) ? 'red' : 'black';
}

// Return the wheel pocket color for SVG rendering.
function pocketFill(number) {
  // Return green for zero pockets.
  if (String(number) === '0' || String(number) === '00') return '#087a43';
  // Return premium red or near-black for numbered pockets.
  return RED_NUMBERS.has(Number(number)) ? '#a91622' : '#050505';
}

// Convert polar coordinates into an SVG point.
function polar(cx, cy, radius, angle) {
  // Return the cartesian point for one polar coordinate.
  return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
}

// Build one SVG annular wedge path for a Roulette pocket.
function wedgePath(index, count) {
  // Store the wedge start angle.
  const start = (index / count) * Math.PI * 2 - Math.PI / 2;
  // Store the wedge end angle.
  const end = ((index + 1) / count) * Math.PI * 2 - Math.PI / 2;
  // Store the outer start point.
  const outerStart = polar(150, 150, 144, start);
  // Store the outer end point.
  const outerEnd = polar(150, 150, 144, end);
  // Store the inner end point.
  const innerEnd = polar(150, 150, 92, end);
  // Store the inner start point.
  const innerStart = polar(150, 150, 92, start);
  // Return the closed annular path for this pocket.
  return `M ${outerStart.x} ${outerStart.y} A 144 144 0 0 1 ${outerEnd.x} ${outerEnd.y} L ${innerEnd.x} ${innerEnd.y} A 92 92 0 0 0 ${innerStart.x} ${innerStart.y} Z`;
}

// Return the table-center coordinate for a straight-up number.
function cellCenter(number) {
  // Normalize the input to the string shape used by the catalog.
  const normalized = String(number);
  // Return the single-zero location.
  if (normalized === '0') return state.mode === 'double' ? { x: BOARD.x0 + BOARD.cw * .75, y: BOARD.y0 - 42 } : { x: BOARD.x0 + BOARD.cw * 1.5, y: BOARD.y0 - 42 };
  // Return the double-zero location.
  if (normalized === '00') return { x: BOARD.x0 + BOARD.cw * 2.25, y: BOARD.y0 - 42 };
  // Store numeric number for row and column math.
  const value = Number(normalized);
  // Store the row used by the existing fixed board geometry.
  const row = Math.floor((value - 1) / 3);
  // Store the column used by the existing fixed board geometry.
  const col = (value - 1) % 3;
  // Return the center point for this table cell.
  return { x: BOARD.x0 + col * BOARD.cw + BOARD.cw / 2, y: BOARD.y0 + row * BOARD.ch + BOARD.ch / 2 };
}

// Return the fixed board coordinate for outside bets.
function outsidePos(bet) {
  // Branch for dozen bets that sit under the number grid.
  if (bet.type === 'dozen') {
    // Find the dozen index from the catalog label.
    const idx = ['1st 12', '2nd 12', '3rd 12'].indexOf(bet.label);
    // Return the center of the matching dozen cell.
    return { x: BOARD.x0 + idx * BOARD.cw + BOARD.cw / 2, y: BOARD.y0 + 12 * BOARD.ch + 28 };
  }
  // Branch for column bets that sit under the dozen row.
  if (bet.type === 'column') {
    // Find the column index from the catalog label.
    const idx = ['Column 1', 'Column 2', 'Column 3'].indexOf(bet.label);
    // Return the center of the matching column cell.
    return { x: BOARD.x0 + idx * BOARD.cw + BOARD.cw / 2, y: BOARD.y0 + 12 * BOARD.ch + 78 };
  }
  // Store fixed side-rail locations for even-money outside bets.
  const map = { red: { x: 90, y: 290 }, black: { x: 90, y: 340 }, odd: { x: 90, y: 390 }, even: { x: 90, y: 240 }, low: { x: 90, y: 190 }, high: { x: 90, y: 440 } };
  // Return the outside position or a safe fallback.
  return map[bet.type] || { x: 50, y: 50 };
}

// Return the fixed board coordinate for a catalog bet.
function posForBet(bet) {
  // Store covered numbers so position math can average their cell centers.
  const nums = bet.covered_numbers || [];
  // Return outside layout positions directly.
  if (bet.layout_kind === 'outside') return outsidePos(bet);
  // Return the street marker location.
  if (bet.type === 'street') {
    // Store the street row from the first covered number.
    const row = Math.floor((Number(nums[0]) - 1) / 3);
    // Return the street marker point.
    return { x: BOARD.x0 - 22, y: BOARD.y0 + row * BOARD.ch + BOARD.ch / 2 };
  }
  // Return the line marker location.
  if (bet.type === 'line') {
    // Store the line row from the first covered number.
    const row = Math.floor((Number(nums[0]) - 1) / 3);
    // Return the line marker point.
    return { x: BOARD.x0 - 22, y: BOARD.y0 + (row + 1) * BOARD.ch };
  }
  // Return the top-line region for special zero-adjacent inside bets.
  if (['trio', 'first_four', 'top_line'].includes(bet.type)) return { x: BOARD.x0 + BOARD.cw * 1.5, y: BOARD.y0 - 15 };
  // Return the snake marker location.
  if (bet.type === 'snake') return { x: BOARD.x0 + BOARD.cw * 2.9, y: BOARD.y0 + 12 * BOARD.ch + 40 };
  // Store centers for all covered numbers.
  const centers = nums.map(cellCenter);
  // Return the average center for split, corner, and similar bets.
  return { x: centers.reduce((sum, point) => sum + point.x, 0) / centers.length, y: centers.reduce((sum, point) => sum + point.y, 0) / centers.length };
}

// Aggregate open human bets so stacked chips show one amount per table spot.
function aggregateBets() {
  // Store aggregate rows by type and covered-number set.
  const grouped = new Map();
  // Iterate through open human bets.
  for (const bet of humanBets()) {
    // Store the stable aggregate key.
    const key = `${bet.type}|${bet.covered_numbers.join('/')}`;
    // Read any existing aggregate row.
    const old = grouped.get(key) || { ...bet, amount: 0 };
    // Add this bet amount to the aggregate row.
    old.amount += Number(bet.amount || 0);
    // Store the updated aggregate row.
    grouped.set(key, old);
  }
  // Return the aggregate rows for chip rendering.
  return [...grouped.values()];
}

// Return the correct wheel number order for the selected table mode.
function wheelNums() {
  // Return the American wheel when double-zero mode is active.
  if (state.mode === 'double') return ['0', '28', '9', '26', '30', '11', '7', '20', '32', '17', '5', '22', '34', '15', '3', '24', '36', '13', '1', '00', '27', '10', '25', '29', '12', '8', '19', '31', '18', '6', '21', '33', '16', '4', '23', '35', '14', '2'];
  // Return the European wheel for single-zero mode.
  return ['0', '32', '15', '19', '4', '21', '2', '25', '17', '34', '6', '27', '13', '36', '11', '30', '8', '23', '10', '5', '24', '16', '33', '1', '20', '14', '31', '9', '22', '18', '29', '7', '28', '12', '35', '3', '26'];
}

// Render the premium vector wheel while preserving result accuracy.
function wheelSvg() {
  // Store wheel numbers for the selected table mode.
  const nums = wheelNums();
  // Store the selected result only when a real spin result exists.
  const selected = lastSpinResult || latestResultEntry()?.result || null;
  // Store the selected pocket index.
  const selectedIndex = selected ? nums.indexOf(String(selected)) : -1;
  // Store the selected angle for the ball indicator.
  const selectedAngle = selectedIndex >= 0 ? ((selectedIndex + .5) / nums.length) * Math.PI * 2 - Math.PI / 2 : null;
  // Store the ball x coordinate without defaulting to a fake result.
  const ballX = selectedAngle == null ? 108 : 150 + Math.cos(selectedAngle) * 121;
  // Store the ball y coordinate without defaulting to a fake result.
  const ballY = selectedAngle == null ? 245 : 150 + Math.sin(selectedAngle) * 121;
  // Build colored pocket wedges for the vector wheel.
  const wedges = nums.map((number, index) => `<path d="${wedgePath(index, nums.length)}" fill="${pocketFill(number)}" stroke="rgba(255,245,211,.34)" stroke-width=".8"></path>`).join('');
  // Build pocket labels and selected marker circles.
  const labels = nums.map((number, index) => { const angle = ((index + .5) / nums.length) * Math.PI * 2 - Math.PI / 2; const point = polar(150, 150, 119, angle); const fill = String(number) === '0' || String(number) === '00' ? '#d8ffe8' : '#fff4df'; const marker = String(number) === String(selected) ? `<circle cx="${point.x}" cy="${point.y}" r="13" fill="#ffd978" opacity=".28"></circle>` : ''; return `${marker}<text x="${point.x}" y="${point.y}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="${fill}" transform="rotate(${angle * 180 / Math.PI + 90} ${point.x} ${point.y})">${safe(number)}</text>`; }).join('');
  // Store the spinning class for transform-only animation.
  const spinClass = uiPhase === 'spinning' ? ' spinning' : '';
  // Return the complete wheel SVG with a data attribute for browser assertions.
  return `<svg class="roulette-wheel" viewBox="0 0 300 300" data-testid="roulette-wheel" data-selected-result="${safe(selected || 'none')}"><circle cx="150" cy="150" r="148" fill="#8d651f"></circle><g class="wheel-ring${spinClass}">${wedges}${labels}<circle cx="150" cy="150" r="88" fill="#51290a" stroke="rgba(255,245,211,.66)" stroke-width="2"></circle><circle cx="150" cy="150" r="53" fill="url(#rouletteHub)" stroke="rgba(255,255,255,.42)" stroke-width="2"></circle></g><defs><radialGradient id="rouletteHub"><stop offset="0" stop-color="#fff1ba"></stop><stop offset=".48" stop-color="#c88b2c"></stop><stop offset="1" stop-color="#351604"></stop></radialGradient></defs><g class="ball-dot${spinClass}"><circle cx="${ballX}" cy="${ballY}" r="7" fill="#fff8e9" stroke="#c7bca1" stroke-width="1.5"></circle></g></svg>`;
}

// Render one absolute-positioned number cell.
function numberCellHtml(number, x, y, width, height) {
  // Store result marker state for real settled results only.
  const isResult = uiPhase === 'settled' && String(number) === String(lastSpinResult);
  // Store the premium result class when this cell matches the actual result.
  const resultClass = isResult ? ' result-cell' : '';
  // Store a compact result marker for the winning number.
  const marker = isResult ? `<i class="roulette-result-marker">${text('table.winMarker')}</i>` : '';
  // Return the absolute table cell with the existing test id and data contract.
  return `<div class="table-cell ${numberColorClass(number)}${resultClass}" style="left:${x}px;top:${y}px;width:${width}px;height:${height}px"><button type="button" data-testid="roulette-num-${safe(number)}" data-num="${safe(number)}"${disabledWhenSpinning()}>${safe(number)}${marker}</button></div>`;
}

// Render the fixed Roulette betting table with inside spots and chips.
function tableHtml() {
  // Store rendered cell markup.
  const cells = [];
  // Branch for the double-zero header layout.
  if (state.mode === 'double') {
    // Add the 0 cell.
    cells.push(numberCellHtml('0', BOARD.x0, BOARD.y0 - 62, BOARD.cw * 1.5, 45));
    // Add the 00 cell.
    cells.push(numberCellHtml('00', BOARD.x0 + BOARD.cw * 1.5, BOARD.y0 - 62, BOARD.cw * 1.5, 45));
  // Render the single-zero header layout.
  } else {
    // Add the single 0 cell.
    cells.push(numberCellHtml('0', BOARD.x0, BOARD.y0 - 62, BOARD.cw * 3, 45));
  }
  // Iterate through the fixed number grid.
  for (let row = 0; row < 12; row += 1) {
    // Iterate through the three fixed number columns.
    for (let col = 0; col < 3; col += 1) {
      // Store the table number at this coordinate.
      const number = row * 3 + col + 1;
      // Add the number cell to the board.
      cells.push(numberCellHtml(number, BOARD.x0 + col * BOARD.cw, BOARD.y0 + row * BOARD.ch, BOARD.cw, BOARD.ch));
    }
  }
  // Store even-money outside cells with localized labels.
  const outside = [['low', text('bets.low'), 30, 180, 115, 42], ['even', text('bets.even'), 30, 228, 115, 42], ['red', text('bets.red'), 30, 276, 115, 42], ['black', text('bets.black'), 30, 324, 115, 42], ['odd', text('bets.odd'), 30, 372, 115, 42], ['high', text('bets.high'), 30, 420, 115, 42]];
  // Add each outside cell to the board.
  outside.forEach(([type, label, x, y, width, height]) => { const isResult = uiPhase === 'settled' && type === lastSpinColor; const resultClass = isResult ? ' result-cell' : ''; cells.push(`<div class="outside-cell${resultClass}" style="left:${x}px;top:${y}px;width:${width}px;height:${height}px"><button type="button" data-outside="${type}" data-testid="roulette-outside-${type}"${disabledWhenSpinning()}>${label}</button></div>`); });
  // Add dozen cells below the inside grid.
  ['1st 12', '2nd 12', '3rd 12'].forEach((label, index) => cells.push(`<div class="outside-cell" style="left:${BOARD.x0 + index * BOARD.cw}px;top:${BOARD.y0 + 12 * BOARD.ch + 8}px;width:${BOARD.cw}px;height:36px"><button type="button" data-dozen="${safe(label)}" data-testid="roulette-dozen-${index + 1}"${disabledWhenSpinning()}>${text(`bets.dozen${index + 1}`)}</button></div>`));
  // Add column cells below the dozen row.
  ['Column 1', 'Column 2', 'Column 3'].forEach((label, index) => cells.push(`<div class="outside-cell" style="left:${BOARD.x0 + index * BOARD.cw}px;top:${BOARD.y0 + 12 * BOARD.ch + 50}px;width:${BOARD.cw}px;height:36px"><button type="button" data-column="${safe(label)}" data-testid="roulette-column-${index + 1}"${disabledWhenSpinning()}>${text('bets.column')}</button></div>`));
  // Build inside-bet hotspots from the catalog.
  const hotspots = catalog.filter(bet => bet.layout_kind !== 'outside' && bet.type !== 'straight').map(bet => { const point = posForBet(bet); return `<button type="button" class="spot" style="left:${point.x - 12}px;top:${point.y - 12}px" title="${safe(bet.label)} ${safe(bet.net_payout)}:1" data-betid="${safe(bet.id)}" data-testid="roulette-spot-${safe(bet.id)}"${disabledWhenSpinning()}></button>`; }).join('');
  // Build visible table chips from aggregate human bets.
  const chips = aggregateBets().map(bet => { const point = posForBet(bet); return `<div class="bet-chip" style="left:${point.x - 19}px;top:${point.y - 19}px" title="${safe(bet.label)}">${chipMoney(bet.amount)}</div>`; }).join('');
  // Store dimmed state for spin/reveal.
  const dimmed = uiPhase === 'spinning' ? ' roulette-board-dimmed' : '';
  // Return the full fixed board.
  return `<div class="roulette-table-board${showSpots ? '' : ' hide-spots'}${dimmed}" data-testid="roulette-table">${cells.join('')}${hotspots}${chips}</div>`;
}

// Return the localized label for a backend settlement outcome.
function outcomeLabel(outcome) {
  // Store the resource key for the backend outcome.
  const key = `outcomes.${String(outcome || 'none')}`;
  // Resolve the localized outcome label.
  const label = rt(key);
  // Return the backend value when a specific resource key is not defined.
  return label === key ? String(outcome || '') : label;
}

// Return a localized display label for backend result colors.
function colorLabel(color) {
  // Store the resource key for the backend color value.
  const key = `colors.${String(color || 'none')}`;
  // Resolve the localized color label.
  const label = rt(key);
  // Return the backend value when a specific resource key is not defined.
  return label === key ? String(color || '') : label;
}

// Render the result panel under the wheel.
function resultHtml() {
  // Branch while the animation is intentionally hiding the result.
  if (uiPhase === 'spinning') return `<div id="result" class="result-box fixed-result muted" data-testid="roulette-result-region" data-phase="spinning">${text('result.spinning')}</div>`;
  // Branch for a settled spin with an actual backend result.
  if (uiPhase === 'settled' && lastSpinResult !== null) {
    // Store the settlement detail text.
    const details = lastSettlements.map(row => `${safe(row.label)}: ${safe(outcomeLabel(row.outcome))}, ${text('settlement.credit')} ${money(row.credit)}`).join('<br>');
    // Return the settled result region.
    return `<div id="result" class="result-box fixed-result win" data-testid="roulette-result-region" data-phase="settled" data-result-number="${safe(lastSpinResult)}"><b>${text('result.rolled', { number: lastSpinResult })}</b> ${safe(colorLabel(lastSpinColor))}<br>${details || text('result.noHumanBets')}</div>`;
  }
  // Branch for a loaded state with a real previous result.
  if (lastSpinResult !== null) return `<div id="result" class="result-box fixed-result muted" data-testid="roulette-result-region" data-phase="betting" data-result-number="${safe(lastSpinResult)}">${text('result.lastResult', { number: lastSpinResult })}</div>`;
  // Return the no-spin state without any fake result.
  return `<div id="result" class="result-box fixed-result muted" data-testid="roulette-result-region" data-phase="betting" data-result-number="none">${text('result.noSpinYet')}</div>`;
}

// Render the premium header and status ribbon.
function headerHtml() {
  // Store the four status keys for the current visual phase.
  const statusKeys = uiPhase === 'spinning' ? ['status.spinning', 'status.resultReserved', 'status.actionLocked', 'status.botIncluded'] : uiPhase === 'settled' ? ['status.resultLocked', 'status.slipUpdated', 'status.statsUpdated', 'status.voiceQueued'] : ['status.tableMode', 'status.zeroReady', 'status.statsReserved', 'status.ledgerDebits'];
  // Return the premium route heading and phase ribbon.
  return `<section class="roulette-header" aria-label="${text('aria.header')}"><div><p class="roulette-kicker">${text('header.kicker')}</p><h1>${text('title')}</h1></div><div class="roulette-status-ribbon">${statusKeys.map(key => `<span>${text(key)}</span>`).join('')}</div></section>`;
}

// Render the control rail with settings, chips, fast bets, autoplay, and bots.
function controlRailHtml() {
  // Store the template availability state for the rebet button.
  const canRebet = (state.last_bet_template || []).length > 0 && !spinBusy;
  // Store the spot toggle label.
  const spotLabel = showSpots ? text('controls.hideSpots') : text('controls.showSpots');
  // Return the complete left rail.
  return `<section class="panel control-rail" data-testid="roulette-control-rail"><h2 class="game-title">${text('controls.title')}</h2><div class="roulette-settings"><label>${text('controls.wheel')}<select id="mode" data-testid="roulette-mode"${disabledWhenSpinning()}><option value="single">${text('settings.wheel.single')}</option><option value="double">${text('settings.wheel.double')}</option></select></label><label>${text('controls.zeroRule')}<select id="zero" data-testid="roulette-zero"${disabledWhenSpinning()}><option value="normal">${text('settings.zeroRule.normal')}</option><option value="la_partage">${text('settings.zeroRule.laPartage')}</option><option value="en_prison">${text('settings.zeroRule.enPrison')}</option></select></label></div><div class="roulette-control-section"><h3>${text('controls.chipStack')}</h3><div class="chip-row">${CHIP_VALUES.map(value => `<button type="button" class="chip ${value === chip ? 'active' : ''}" data-chip="${value}" data-testid="chip-${value}"${disabledWhenSpinning()}>${chipMoney(value)}</button>`).join('')}</div></div><div class="roulette-control-section"><h3>${text('controls.fastBets')}</h3><div class="roulette-fast-grid">${['red', 'black', 'odd', 'even', 'low', 'high'].map(type => `<button type="button" data-outbtn="${type}"${disabledWhenSpinning()}>${text(`bets.${type}`)}</button>`).join('')}</div></div><div class="roulette-control-section"><h3>${text('controls.racetrack')}</h3><div class="roulette-call-grid">${['snake', 'voisins', 'tiers', 'orphelins', 'jeu_zero', 'neighbors', 'final', 'complete'].map(type => `<button type="button" data-call="${type}"${disabledWhenSpinning()}>${text(`callBets.${type}`)}</button>`).join('')}</div></div><label class="roulette-settings roulette-control-section">${text('controls.callNumber')}<input id="callNumber" class="roulette-call-input" type="text" value="17"${disabledWhenSpinning()}></label><div class="roulette-secondary-actions"><button type="button" id="toggleSpots"${disabledWhenSpinning()}>${spotLabel}</button><button type="button" id="rebet"${canRebet ? '' : ' disabled'}>${text('controls.rebet')}</button></div><div id="auto"></div><div class="roulette-control-section"><div class="roulette-control-plane"><b>${text('controls.soundTitle')}</b><span>${text('controls.soundAdmin')}</span></div></div><div id="botPanel" class="roulette-control-section">${botPanelCache}</div></section>`;
}

// Render the central wheel and table stage.
function stageHtml() {
  // Store a compact round label from the open round or latest settled round.
  const round = lastRoundId || state.open_round?.round_id || 'rou';
  // Store the current phase title.
  const phaseTitle = uiPhase === 'spinning' ? text('stage.spinning') : uiPhase === 'settled' ? text('stage.settled') : text('stage.placeBets');
  // Store the primary button label.
  const primaryLabel = spinBusy ? text('controls.resolving') : text('controls.spin');
  // Store the wheel panel state class.
  const wheelState = uiPhase === 'spinning' ? ' reveal-glow' : uiPhase === 'settled' ? ' result-glow' : '';
  // Store the clear disabled state.
  const clearDisabled = humanBets().length === 0 || spinBusy ? ' disabled' : '';
  // Return the complete central game stage.
  return `<section class="panel game-stage" data-testid="roulette-premium-stage"><div class="roulette-stage-toolbar"><div><p class="eyebrow">${text('stage.round', { round })}</p><h2>${phaseTitle}</h2></div><div class="row"><button type="button" id="clear"${clearDisabled}>${text('controls.clearBets')}</button><button type="button" id="spin" data-testid="roulette-spin" class="primary"${disabledWhenSpinning()}>${primaryLabel}</button></div></div><div class="roulette-stage"><div class="wheel-card${wheelState}">${wheelSvg()}${resultHtml()}</div>${tableHtml()}</div></section>`;
}

// Render the player balance table for the right drawer.
function scoreboardHtml() {
  // Store player rows from the latest state payload.
  const players = window._lastPlayers || [];
  // Return a compact scoreboard table.
  return `<table class="mini-table" data-testid="roulette-scoreboard"><tr><th>${text('scoreboard.player')}</th><th>${text('scoreboard.balance')}</th></tr>${players.map(player => `<tr><td>${safe(player.display_name)}</td><td>${money(player.balance)}</td></tr>`).join('')}</table>`;
}

// Render stat spark bars from live stats data.
function sparkBarsHtml(stats) {
  // Store frequency values from the stats payload.
  const values = Object.values(stats.frequency || {}).map(value => Number(value || 0)).slice(0, 8);
  // Store a fallback sequence when no stats exist yet.
  const bars = values.length ? values : [1, 2, 1, 2, 1, 3, 2, 1];
  // Store the max value so heights can scale safely.
  const max = Math.max(1, ...bars);
  // Return the spark bar row.
  return `<div class="roulette-spark-bars" data-testid="roulette-stats-spark">${bars.map(value => `<i style="height:${Math.max(14, Math.round((value / max) * 54))}px"></i>`).join('')}</div>`;
}

// Render latest-result history pills from stats or state.
function historyPillsHtml(stats) {
  // Store recent results from stats first and backend state as a fallback.
  const latest = (stats.latest || state.last_results || []).slice(-12);
  // Return the latest-result pill row.
  return `<div class="roulette-history-pills" data-testid="roulette-recent-results">${latest.map(entry => { const result = entry.result ?? entry; const resultClass = uiPhase === 'settled' && String(result) === String(lastSpinResult) ? ' result-cell' : ''; return `<span class="${numberColorClass(result)}${resultClass}">${safe(result)}</span>`; }).join('')}</div>`;
}

// Render the settlement or pending drawer card.
function settlementCardHtml() {
  // Branch while a spin is waiting for the pocket reveal.
  if (uiPhase === 'spinning') return `<div class="roulette-settlement-card" data-testid="roulette-settlement-card"><b>${text('settlement.waiting')}</b><span>${text('settlement.noResize')}</span></div>`;
  // Branch after a settled spin.
  if (uiPhase === 'settled') return `<div class="roulette-settlement-card" data-testid="roulette-settlement-card"><b>${text('settlement.humanNet')}</b><span>${signedMoney(lastHumanNet)}</span></div>`;
  // Return an empty string when the bet slip owns the drawer.
  return '';
}

// Render the right drawer with bet slip, settlement, scoreboard, and stats.
function drawerHtml() {
  // Store human open bets for slip rendering.
  const bets = humanBets();
  // Store the open total for the drawer metric.
  const total = humanBetTotal(bets);
  // Store whether settlement mode owns the drawer heading.
  const settlementMode = uiPhase === 'settled';
  // Store the drawer title.
  const title = settlementMode ? text('settlement.title') : text('betSlip.title');
  // Store the phase badge.
  const badge = uiPhase === 'spinning' ? text('phase.spinning') : uiPhase === 'settled' ? text('phase.settled') : text('phase.betting');
  // Store the slip rows for open bets or settlement rows for settled results.
  const rows = settlementMode ? lastSettlements.map(row => `<div class="bet-item"><span>${safe(row.label)}</span><b>${safe(outcomeLabel(row.outcome))}</b></div>`).join('') : bets.map(bet => `<div class="bet-item"><span>${safe(bet.label)}</span><b class="money">${money(bet.amount)}</b><button type="button" class="danger" data-clear="${safe(bet.bet_id)}"${disabledWhenSpinning()}>${text('controls.remove')}</button></div>`).join('');
  // Store the metric label.
  const metricLabel = uiPhase === 'spinning' ? text('betSlip.lockedTotal') : settlementMode ? text('settlement.humanNet') : text('betSlip.openTotal');
  // Store the metric value.
  const metricValue = settlementMode ? signedMoney(lastHumanNet) : money(total);
  // Return the complete right drawer.
  return `<section class="panel details-drawer" data-testid="roulette-bet-slip"><div class="roulette-drawer-title"><h3>${title}</h3><span class="roulette-phase-badge">${badge}</span></div><div class="stat"><span>${metricLabel}</span> <b class="money">${metricValue}</b></div><div class="bet-list stable-list">${rows || `<p class="muted">${text('betSlip.empty')}</p>`}</div>${settlementCardHtml()}<h3>${text('scoreboard.title')}</h3>${scoreboardHtml()}<h3>${text('stats.title')}</h3><div class="row"><span class="badge">${text('stats.rolls', { count: statsCount(lastStats.roll_count) })}</span><span class="badge">${text('stats.red', { count: statsCount(lastStats.colors?.red) })}</span><span class="badge">${text('stats.black', { count: statsCount(lastStats.colors?.black) })}</span><span class="badge">${text('stats.green', { count: statsCount(lastStats.colors?.green) })}</span></div>${sparkBarsHtml(lastStats)}${historyPillsHtml(lastStats)}<h4>${text('stats.hot')}</h4><div class="stat-bars">${(lastStats.hot || []).map(([number, count]) => `<div class="stat-bar"><b>${safe(number)}</b><div class="stat-fill" style="width:${Math.max(5, count / Math.max(1, ...Object.values(lastStats.frequency || {})) * 100)}%"></div><span>${safe(count)}</span></div>`).join('')}</div><h4>${text('stats.cold')}</h4><div class="row">${(lastStats.cold || []).map(([number, count]) => `<span class="badge">${safe(number)}: ${safe(count)}</span>`).join('')}</div></section>`;
}

// Return a stable stat count string for localized stat badges.
function statsCount(value) {
  // Return a numeric count with a zero fallback.
  return String(Number(value || 0));
}

// Wire all event handlers after a full rerender.
function wireControls() {
  // Set the mode select to the current backend state value.
  root.querySelector('#mode').value = state.mode;
  // Set the zero-rule select to the current backend state value.
  root.querySelector('#zero').value = state.zero_rule;
  // Wire mode changes to the existing settings endpoint.
  root.querySelector('#mode').onchange = settings;
  // Wire zero-rule changes to the existing settings endpoint.
  root.querySelector('#zero').onchange = settings;
  // Wire chip buttons while preserving selected chip state.
  root.querySelectorAll('[data-chip]').forEach(button => { button.onclick = () => { chip = Number(button.dataset.chip); render(); updateBotPanel(); }; });
  // Wire straight-up number cells to catalog bets.
  root.querySelectorAll('[data-num]').forEach(button => { button.onclick = () => placeBet(betBy(bet => bet.type === 'straight' && bet.covered_numbers[0] === String(button.dataset.num))); });
  // Wire inside bet hotspots to catalog bets.
  root.querySelectorAll('[data-betid]').forEach(button => { button.onclick = () => placeBet(betBy(bet => bet.id === button.dataset.betid)); });
  // Wire table outside cells to catalog bets.
  root.querySelectorAll('[data-outside]').forEach(button => { button.onclick = () => placeBet(betBy(bet => bet.type === button.dataset.outside)); });
  // Wire fast outside bet buttons to catalog bets.
  root.querySelectorAll('[data-outbtn]').forEach(button => { button.onclick = () => placeBet(betBy(bet => bet.type === button.dataset.outbtn)); });
  // Wire dozen cells to catalog bets.
  root.querySelectorAll('[data-dozen]').forEach(button => { button.onclick = () => placeBet(betBy(bet => bet.type === 'dozen' && bet.label === button.dataset.dozen)); });
  // Wire column cells to catalog bets.
  root.querySelectorAll('[data-column]').forEach(button => { button.onclick = () => placeBet(betBy(bet => bet.type === 'column' && bet.label === button.dataset.column)); });
  // Wire racetrack and call-bet controls to the call-bet endpoint.
  root.querySelectorAll('[data-call]').forEach(button => { button.onclick = () => placeCall(button.dataset.call); });
  // Wire individual bet removal buttons to the clear endpoint.
  root.querySelectorAll('[data-clear]').forEach(button => { button.onclick = () => clearBet(button.dataset.clear); });
  // Wire clear-all to the clear endpoint.
  root.querySelector('#clear').onclick = clearAll;
  // Wire rebet to the rebet endpoint.
  root.querySelector('#rebet').onclick = rebet;
  // Wire spin to the spin endpoint.
  root.querySelector('#spin').onclick = () => spin(true);
  // Wire spot visibility without touching game state.
  root.querySelector('#toggleSpots').onclick = () => { showSpots = !showSpots; render(); updateBotPanel(); };
  // Render shared autoplay controls through the shared control-plane helper.
  autoBox = renderAutoplay({ id: 'roulette', plan: { type: 'repeat_bet_template' }, onTick: async () => { await ensureBetForAuto(); await spin(false); } });
  // Append autoplay controls into the reserved rail slot.
  root.querySelector('#auto').append(autoBox);
}

// Render the full premium Roulette route without reloading state.
function render() {
  // Stop when the module has not mounted yet.
  if (!root || !state) return;
  // Replace the route body while preserving JS state caches.
  root.innerHTML = `<section class="roulette-premium" data-testid="roulette-premium">${headerHtml()}<div class="game-layout three-col stable-game" data-testid="roulette-premium-layout">${controlRailHtml()}${stageHtml()}${drawerHtml()}</div></section>`;
  // Wire controls after the DOM has been replaced.
  wireControls();
}

// Export this symbol so the app shell can mount the Roulette game route.
export const RouletteGame = {
  // Store the game id used by the shell route registry.
  id: 'roulette',
  // Store the visible label used by route metadata.
  label: 'Roulette',
  // Mount Roulette into the shared #view route outlet.
  async mount(node) {
    // Store the route root for future renders.
    root = node;
    // Install Roulette-only premium styles.
    ensurePremiumStyle();
    // Initialize the Roulette resource domain before rendering visible strings.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Subscribe to locale changes so text refreshes without losing bets or spin state.
    localeUnsubscribe = onLocaleChange(() => render());
    // Load backend state and render the premium Roulette surface.
    await load();
  },
  // Unmount Roulette and clean up local loops/listeners.
  unmount() {
    // Stop autoplay when the route is leaving.
    if (autoBox?._stop) autoBox._stop();
    // Remove the locale listener when mounted.
    if (localeUnsubscribe) localeUnsubscribe();
    // Clear the locale unsubscribe handle.
    localeUnsubscribe = null;
    // Clear the route root to prevent async rerenders after unmount.
    root = null;
  },
};
