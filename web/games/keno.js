// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use the frozen Keno API contract.
import { api, post, del, currentPlayerId, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import required dependency so this module can reuse shared premium formatting and feedback helpers.
import { toast, refreshBalance, safe, renderShellMetric } from '../core/ui.js';
// Import required dependency so Keno autoplay stays inside the shared control plane.
import { renderAutoplay } from '../core/autoplay.js';
// Import required dependency so Keno can announce completed draw results without changing game state.
import { speak, clickSound } from '../core/voice.js';
// Import required dependency so Keno can show compatible bot controllers and trigger bot tickets through public actions.
import { eligibleBots, playBotRound } from '../core/bots.js';
// Import required dependency so all Keno-owned visible strings and number formats use shared i18n resources.
import { initI18n, loadI18nDomain, onLocaleChange, t, formatMoney, formatNumber } from '../core/i18n.js';

// Store the i18n domain that owns Keno frontend strings.
const KENO_DOMAIN = 'games/keno';
// Store the style element id so Keno-scoped premium styles are installed once.
const STYLE_ID = 'keno-premium-styles';
// Store the default human ticket amount shown before the first API response.
const DEFAULT_AMOUNT = 5;
// Store the maximum legal Keno spot count from KENO-002.
const MAX_SPOTS = 20;
// Store the total draw size from KENO-003.
const DRAW_TOTAL = 20;
// Store the animation delay so the reveal stays visible while controls remain fixed.
const DRAW_DELAY_MS = 65;

// Store the route outlet supplied by the shared shell.
let root = null;
// Store the latest Keno state payload from /api/v1/games/keno/state.
let state = null;
// Store the current Keno paytable from the API payload.
let paytable = {};
// Store the human player's selected spot set for the next ticket.
let selected = new Set();
// Store the human ticket amount input between renders.
let amount = DEFAULT_AMOUNT;
// Store the mounted autoplay box so unmount can stop the shared session.
let autoBox = null;
// Store the latest draw payload used by result, paytable, and history surfaces.
let lastDraw = null;
// Store the draw numbers currently revealed during animation.
let displayedDraw = [];
// Store eligible Keno bot controller metadata for the left rail.
let botData = { bots: [], capabilities: { supports_bots: false, strategies: [] } };
// Store the latest bot ticket actions triggered before a draw.
let lastBotActions = [];
// Store whether a draw request or reveal animation is active.
let drawBusy = false;
// Store the locale unsubscribe callback so remounts do not leak subscriptions.
let localeUnsubscribe = null;

// Define tx to resolve Keno strings from the game-specific resource file.
function tx(key, params = {}) {
  // Return the translated Keno string using the shared i18n fallback chain.
  return t(key, params, KENO_DOMAIN);
}

// Define moneyText to format fake-money values through the active locale.
function moneyText(value) {
  // Return a locale-aware fake-money string without changing ledger semantics.
  return formatMoney(value);
}

// Define numberText to format compact numeric values through the active locale.
function numberText(value, options = {}) {
  // Return a locale-aware numeric string for counts, multipliers, and metrics.
  return formatNumber(value, options);
}

// Define ensureStyles to install Keno-only premium layout styles without touching shared CSS.
function ensureStyles() {
  // Branch when this worker already installed the scoped style block.
  if (document.getElementById(STYLE_ID)) return;
  // Create a style element owned by the Keno game module.
  const style = document.createElement('style');
  // Tag the style block so later renders can detect it.
  style.id = STYLE_ID;
  // Define scoped CSS for premium Keno surfaces, stable board sizing, reveal motion, and responsive containment.
  style.textContent = '/* Keno premium layout: route-local wrapper, hero metrics, and fixed game stage. */ .keno-premium{display:grid;grid-template-rows:auto minmax(0,1fr);gap:10px;width:100%;max-width:100%;height:100%;min-width:0;min-height:0;} .keno-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:end;min-width:0;min-height:104px;padding:10px 2px 4px;} .keno-eyebrow{margin:0 0 4px;color:var(--gold);font-weight:900;text-transform:uppercase;letter-spacing:0;font-size:13px;} .keno-hero-title{margin:0;color:#fff2c2;font-family:var(--font-display);font-size:34px;line-height:1.05;letter-spacing:0;} .keno-metric-strip{display:grid;grid-template-columns:repeat(4,minmax(126px,1fr));gap:10px;min-width:min(720px,100%);} .keno-metric{min-height:74px;padding:12px 14px;border:1px solid rgba(255,217,120,.35);border-radius:16px;background:rgba(0,0,0,.24);box-shadow:inset 0 0 0 1px rgba(255,255,255,.03);} .keno-metric strong{display:block;color:#fff2c2;font-size:15px;} .keno-metric span{display:block;margin-top:7px;color:#f5f0d0;font-size:12px;} /* Keno premium panels: preserve the shared three-column shell while keeping internal scroll areas. */ .keno-layout{width:100%;max-width:100%;min-width:0;min-height:0;} .keno-control-panel,.keno-stage-panel,.keno-detail-panel{min-width:0;border-color:rgba(255,217,120,.46);} .keno-stage-panel{overflow:hidden;} .keno-control-panel{display:grid;align-content:start;gap:10px;} .keno-ticket-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;} .keno-command-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;} .keno-button-pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;} .keno-action-card{padding:10px;border:1px solid var(--border-soft);border-radius:14px;background:rgba(255,255,255,.045);} .keno-action-card .row{justify-content:space-between;} .keno-action-card strong{color:#fff2c2;} .keno-board-shell{width:100%;max-width:100%;min-width:0;padding:14px;overflow:hidden;border:1px solid rgba(255,217,120,.48);border-radius:18px;background:rgba(0,0,0,.18);} .keno-board-scroll{box-sizing:border-box;width:100%;max-width:100%;min-width:0;padding:32px;overflow-x:auto;overflow-y:hidden;overscroll-behavior-inline:contain;touch-action:pan-x pan-y;scroll-padding:32px;} .keno-premium-board{grid-template-columns:repeat(10,minmax(54px,1fr));gap:8px;min-width:620px;min-height:520px;} .keno-premium-board .keno-num{min-height:58px;font-size:20px;font-weight:1000;transition:transform .18s ease,box-shadow .18s ease,background .18s ease,outline-color .18s ease;} .keno-premium-board .keno-num:focus-visible{outline:3px solid #fff2c2;outline-offset:3px;} .keno-premium-board .keno-num:disabled{opacity:1;color:inherit;} .keno-premium-board .keno-num.selected:disabled{color:#1d1300;} .keno-premium-board .keno-num.catch:disabled{color:#00240e;} .keno-premium-board .keno-num.latest{transform:scale(1.05);box-shadow:0 0 22px rgba(255,238,179,.66);animation:kenoPop .55s ease;} .keno-ball-rail{display:flex;align-items:center;gap:8px;min-height:76px;margin:14px 0 0;padding:12px 14px;overflow:auto;border:1px solid var(--border-soft);border-radius:14px;background:rgba(0,0,0,.16);} .keno-ball-rail .ball{min-width:44px;min-height:44px;border-radius:999px;color:#1d1300;background:linear-gradient(160deg,#fff4bd,#d8a72d);font-weight:1000;} .keno-ball-rail .ball.latest{box-shadow:0 0 24px rgba(255,238,179,.82);transform:scale(1.12);} .keno-progress-track{height:12px;overflow:hidden;border-radius:999px;background:rgba(255,255,255,.08);} .keno-progress-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#b41b29,#ffd978);transition:width .2s ease;} .keno-ticket-chip-row,.keno-drawn-chip-row{display:flex;flex-wrap:wrap;gap:6px;} .keno-ticket-chip{display:inline-grid;place-items:center;min-width:32px;min-height:30px;padding:0 8px;border-radius:8px;color:#1d1300;background:var(--gold);font-weight:900;} .keno-drawn-chip{display:inline-grid;place-items:center;min-width:32px;min-height:30px;padding:0 8px;border-radius:8px;color:#fff2c2;background:rgba(255,217,120,.16);font-weight:900;} .keno-paytable-list,.keno-history-list{display:grid;gap:8px;} .keno-pay-row,.keno-history-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:10px;border:1px solid var(--border-soft);border-radius:12px;background:rgba(0,0,0,.14);} .keno-history-row>span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;} .keno-pay-row.active{border-color:var(--gold);background:rgba(255,217,120,.13);box-shadow:0 0 0 1px rgba(255,217,120,.16);} .keno-result-copy{min-height:82px;} @keyframes kenoPop{0%{transform:scale(.92);opacity:.55;}100%{transform:scale(1.05);opacity:1;}} @media (max-width:1200px){.keno-premium{height:auto;}.keno-hero{grid-template-columns:1fr;align-items:start;}.keno-metric-strip{grid-template-columns:repeat(2,minmax(0,1fr));min-width:0;}.keno-stage-panel{overflow:hidden!important;}.keno-premium-board{min-height:470px;}} @media (max-width:560px){.keno-hero-title{font-size:28px;}.keno-metric-strip,.keno-ticket-metrics,.keno-button-pair,.keno-command-grid{grid-template-columns:1fr;}.keno-board-shell{padding:10px;}.keno-premium-board{min-width:600px;min-height:452px;}}';
  // Append the style block to the document head for the mounted Keno route.
  document.head.append(style);
}

// Define delay to make draw reveal timing readable without blocking the browser event loop.
function delay(ms) {
  // Return a promise that resolves after the requested animation interval.
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Define sortedNumbers to normalize visible number collections for deterministic rendering.
function sortedNumbers(values) {
  // Return a sorted numeric array for Sets, arrays, and missing values.
  return [...(values || [])].map(Number).sort((a, b) => a - b);
}

// Define currentHumanTickets to read open current-player tickets from the latest Keno state.
function currentHumanTickets() {
  // Return only active-player tickets so bot tickets stay isolated in bot result surfaces.
  return (state?.open_tickets || []).filter(ticket => ticket.player_id === currentPlayerId());
}

// Define latestStoredDraw to read the most recent persisted draw from state history.
function latestStoredDraw() {
  // Store draws so empty or missing history can be handled safely.
  const draws = state?.last_draws || [];
  // Return the newest draw payload or null when no history exists.
  return draws.length ? draws[draws.length - 1] : null;
}

// Define humanResults to find every current-player result on the currently focused draw.
function humanResults() {
  // Return only active-player settlements from the draw payload.
  return (lastDraw?.results || []).filter(result => result.ticket?.player_id === currentPlayerId());
}

// Define primaryHumanResult to select the result that drives summary and paytable comparison.
function primaryHumanResult() {
  // Return the first human result, matching the single-ticket happy path.
  return humanResults()[0] || null;
}

// Define botResults to find non-human results on the currently focused draw.
function botResults() {
  // Return bot settlements so the details drawer can remain separate from the human ticket.
  return (lastDraw?.results || []).filter(result => result.ticket?.player_id !== currentPlayerId());
}

// Define activeDrawNumbers to expose only numbers that should currently be visible.
function activeDrawNumbers() {
  // Return partial reveal state during animation so the board never jumps to the final draw early.
  if (drawBusy) return displayedDraw;
  // Return explicitly displayed draw numbers when a completed draw has been revealed.
  if (displayedDraw.length) return displayedDraw;
  // Return persisted draw numbers for an already-completed draw loaded from state.
  return lastDraw?.drawn || [];
}

// Define latestDrawNumber to mark the newest revealed ball during animation.
function latestDrawNumber() {
  // Store visible numbers so the latest marker is based on rendered state.
  const numbers = activeDrawNumbers();
  // Return the newest visible number or null when no balls have appeared.
  return numbers.length ? numbers[numbers.length - 1] : null;
}

// Define visibleCatchSet to highlight only catches that have actually been drawn.
function visibleCatchSet() {
  // Store the primary human result for catch calculations.
  const result = primaryHumanResult();
  // Store drawn numbers so unrevealed catches do not glow during animation.
  const drawn = new Set(activeDrawNumbers());
  // Return the visible intersection of human catches and drawn balls.
  return new Set((result?.catches || []).filter(number => drawn.has(number)));
}

// Define selectedNumbers to read the current human selection in display order.
function selectedNumbers() {
  // Return the sorted human spot selection.
  return sortedNumbers(selected);
}

// Define activeTicketSpots to choose the ticket spots that should drive metrics.
function activeTicketSpots() {
  // Store the newest open human ticket when a ticket has already been bought.
  const ticket = currentHumanTickets().slice(-1)[0];
  // Return open-ticket spots before falling back to result spots.
  if (ticket) return sortedNumbers(ticket.spots);
  // Store the primary human result for completed draw displays.
  const result = primaryHumanResult();
  // Return completed ticket spots before falling back to the current draft selection.
  return result?.ticket?.spots ? sortedNumbers(result.ticket.spots) : selectedNumbers();
}

// Define activeSpotCount to choose the paytable row currently relevant to the human ticket.
function activeSpotCount() {
  // Return the active ticket spot count, falling back to one so lookup stays valid.
  return Math.max(1, activeTicketSpots().length || selected.size || 1);
}

// Define activePhase to identify the premium Keno view state.
function activePhase() {
  // Branch while the draw animation or request is still active.
  if (drawBusy) return 'drawing';
  // Branch when a completed human result is available for comparison.
  if (primaryHumanResult()) return 'result';
  // Return the spot-selection state for ticket setup.
  return 'selection';
}

// Define strategyLabel to resolve bot strategy names from the capability payload.
function strategyLabel(strategyId) {
  // Store known strategies so ids can be mapped to human-readable labels.
  const strategies = botData.capabilities?.strategies || [];
  // Store the matching strategy row when the API exposes one.
  const match = strategies.find(strategy => strategy.id === strategyId);
  // Return the strategy label or the raw id when no label exists.
  return match?.label || strategyId || tx('bot.none');
}

// Define readAmount to keep the amount input and internal amount value synchronized.
function readAmount() {
  // Store the current numeric input value if the amount control is mounted.
  const raw = Number(root?.querySelector('#kenoAmount')?.value || amount || DEFAULT_AMOUNT);
  // Store a valid positive amount while falling back to the default for invalid input.
  amount = Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_AMOUNT;
  // Return the normalized amount for API calls.
  return amount;
}

// Define applyKenoPayload to update local state from Keno API responses.
function applyKenoPayload(payload) {
  // Store the latest game state from the response.
  state = payload.state;
  // Store the latest paytable while preserving a previous table if absent.
  paytable = payload.paytable || paytable;
}

// Define syncSelectionFromState to initialize the draft ticket from open or recent human tickets.
function syncSelectionFromState() {
  // Store the newest open human ticket when one exists.
  const ticket = currentHumanTickets().slice(-1)[0];
  // Branch when an open ticket should control the visible ticket spots.
  if (ticket) selected = new Set(sortedNumbers(ticket.spots));
  // Store the newest persisted human result when no open ticket exists.
  const result = !ticket ? (latestStoredDraw()?.results || []).find(item => item.ticket?.player_id === currentPlayerId()) : null;
  // Branch when recent history can restore the last played human ticket.
  if (!ticket && result?.ticket?.spots) selected = new Set(sortedNumbers(result.ticket.spots));
}

// Define refreshBotData to load Keno-compatible bot controllers for the rail.
async function refreshBotData() {
  // Start protected bot metadata loading so bot API failures never break human Keno play.
  try {
    // Store eligible Keno bots and capability metadata from the public bot controller.
    botData = await eligibleBots('keno');
  // Handle bot metadata failures with an empty capability model.
  } catch (_) {
    // Store an empty bot model so the panel can render a stable fallback.
    botData = { bots: [], capabilities: { supports_bots: false, strategies: [] } };
  }
}

// Define load to bootstrap i18n, Keno state, bot metadata, and the first render.
async function load() {
  // Initialize the shared i18n runtime with the Keno domain.
  await initI18n({ domains: [KENO_DOMAIN] });
  // Ensure the Keno domain is loaded even if i18n was already initialized by another route.
  await loadI18nDomain(KENO_DOMAIN);
  // Load current Keno state through the frozen v1 endpoint.
  const data = await api(currentPlayerPath('/api/v1/games/keno/state'));
  // Apply the API payload to local render state.
  applyKenoPayload(data);
  // Store the latest draw so history and result reloads have an immediate focus.
  lastDraw = latestStoredDraw();
  // Store completed draw numbers when a previous draw exists.
  displayedDraw = lastDraw?.drawn ? [...lastDraw.drawn] : [];
  // Initialize selected spots from open tickets or the latest human result.
  syncSelectionFromState();
  // Load bot panel data before the first visible render.
  await refreshBotData();
  // Render the premium Keno route.
  render();
  // Refresh the shared wallet after route mount.
  await refreshBalance();
}

// Define buyTicket to purchase the current human ticket through the documented Keno API.
async function buyTicket({ renderAfter = true } = {}) {
  // Branch when the human has not selected a legal ticket.
  if (selected.size < 1) {
    // Show a localized validation toast without calling the API.
    toast(tx('toast.pickAtLeastOne'));
    // Return null so callers can stop chained draw work.
    return null;
  }
  // Read and normalize the current amount input.
  readAmount();
  // Start protected ticket purchase so API validation errors become toasts.
  try {
    // Purchase a ticket with the selected spots and human fake-money amount.
    const data = await post('/api/v1/games/keno/tickets', withCurrentPlayer({ amount, spots: selectedNumbers() }));
    // Apply the returned Keno state and paytable.
    applyKenoPayload(data);
    // Clear focused draw data when the user is preparing a fresh ticket.
    if (renderAfter) lastDraw = null;
    // Clear visible draw data when the user is preparing a fresh ticket.
    if (renderAfter) displayedDraw = [];
    // Render the updated ticket drawer when this is a standalone purchase.
    if (renderAfter) render();
    // Refresh bot metadata after balance-affecting game work.
    if (renderAfter) await refreshBotData();
    // Refresh the shared wallet after the ticket debit.
    await refreshBalance();
    // Play a light ticket-confirmation cue.
    clickSound(500, .05);
    // Return the purchased ticket for draw chaining.
    return data.ticket;
  // Handle ticket purchase errors without leaving the route.
  } catch (error) {
    // Show the API error message in the shared toast outlet.
    toast(error.message || tx('toast.ticketFailed'));
    // Return null so callers can stop chained draw work.
    return null;
  }
}

// Define clearTicket to refund an open human ticket through the documented Keno API.
async function clearTicket(ticketId) {
  // Start protected ticket clearing so missing-ticket errors become toasts.
  try {
    // Request the documented pre-draw ticket refund for the human player.
    const data = await del(`/api/v1/games/keno/tickets/${ticketId}`, withCurrentPlayer());
    // Apply the returned Keno state and paytable.
    applyKenoPayload(data);
    // Render the updated ticket drawer and controls.
    render();
    // Refresh the shared wallet after the refund.
    await refreshBalance();
  // Handle clear-ticket errors without interrupting the route.
  } catch (error) {
    // Show the API error message in the shared toast outlet.
    toast(error.message || tx('toast.clearFailed'));
  }
}

// Define draw to run one Keno draw while preserving API and ledger behavior.
async function draw(show = true) {
  // Branch when another draw is already active.
  if (drawBusy) return;
  // Mark the draw busy before any render so controls reserve their disabled state.
  drawBusy = true;
  // Clear old reveal state for the upcoming draw.
  displayedDraw = [];
  // Render the busy state immediately with fixed board dimensions.
  render();
  // Start protected draw work so failures restore controls.
  try {
    // Branch when no human ticket is open and the selected spots need to be purchased first.
    if (!currentHumanTickets().length) {
      // Purchase the selected ticket as the same atomic human action path used by manual play.
      const ticket = await buyTicket({ renderAfter: false });
      // Stop the draw when ticket purchase validation failed.
      if (!ticket) return;
    }
    // Trigger eligible Keno bots through the public bot controller before the shared draw.
    const botRound = await playBotRound('keno');
    // Store bot ticket actions for the reserved bot panel.
    lastBotActions = botRound.actions || [];
    // Run the documented Keno draw endpoint without changing payload shape.
    const data = await post('/api/v1/games/keno/draw', withCurrentPlayer());
    // Apply final state and paytable from the draw response.
    applyKenoPayload(data);
    // Store the draw payload for result and drawer surfaces.
    lastDraw = data.draw;
    // Clear reveal state before the first animated ball appears.
    displayedDraw = [];
    // Render the empty draw rail so the board size is locked before reveal.
    render();
    // Branch when the caller wants visible reveal animation.
    if (show) {
      // Iterate through drawn balls in API order and reveal one fixed-size chip at a time.
      for (const number of data.draw.drawn) {
        // Add the next ball to the rendered reveal list.
        displayedDraw.push(number);
        // Render the updated ball rail and board highlights.
        render();
        // Play a short pitch cue tied to the ball value.
        clickSound(280 + number * 8, .035);
        // Wait briefly so browser evidence can capture draw progress.
        await delay(DRAW_DELAY_MS);
      }
    // Handle autoplay and non-visual draws by showing the final draw immediately.
    } else {
      // Store the full draw without per-ball animation.
      displayedDraw = [...data.draw.drawn];
    }
    // Refresh bot metadata so balances in the bot panel reflect ticket debits and payouts.
    await refreshBotData();
    // Refresh the shared wallet after Keno settlements.
    await refreshBalance();
    // Store the primary human result for the optional voice announcement.
    const human = data.settlements.find(settlement => settlement.result.ticket.player_id === currentPlayerId());
    // Speak the completed Keno catch count only for visible human draws.
    if (show) speak(tx('voice.caught', { count: human?.result.catch_count || 0 }), 'keno');
  // Handle draw errors without losing the route.
  } catch (error) {
    // Show the API error message in the shared toast outlet.
    toast(error.message || tx('toast.drawFailed'));
  // Always restore controls and render the final state.
  } finally {
    // Mark draw work complete so buttons and board interactions can resume.
    drawBusy = false;
    // Render the completed or restored draw state.
    render();
  }
}

// Define toggleSpot to update the draft human ticket selection.
function toggleSpot(number) {
  // Branch while a draw is active so board clicks never mutate a running ticket.
  if (drawBusy) return;
  // Remove the spot when it is already selected.
  if (selected.has(number)) selected.delete(number);
  // Add the spot when the ticket remains within the Keno spot limit.
  else if (selected.size < MAX_SPOTS) selected.add(number);
  // Show a localized validation toast when the ticket is full.
  else toast(tx('toast.maxSpots', { max: MAX_SPOTS }));
  // Clear old result focus when the user changes the next ticket.
  lastDraw = null;
  // Clear old draw chips when the user changes the next ticket.
  displayedDraw = [];
  // Render the updated board and paytable preview.
  render();
}

// Define quickPick to choose a deterministic-size random ticket for the human player.
function quickPick(count) {
  // Branch while a draw is active so controls stay stable.
  if (drawBusy) return;
  // Replace selected spots with a unique random sample.
  selected = new Set(randomSpots(count));
  // Clear old result focus because the ticket draft changed.
  lastDraw = null;
  // Clear old draw chips because the ticket draft changed.
  displayedDraw = [];
  // Render the updated board and ticket drawer.
  render();
  // Play a compact click cue for the control action.
  clickSound(440, .04);
}

// Define clearSelection to reset the draft ticket without mutating open tickets.
function clearSelection() {
  // Branch while a draw is active so controls stay stable.
  if (drawBusy) return;
  // Remove all draft spots.
  selected.clear();
  // Clear old result focus because the ticket draft changed.
  lastDraw = null;
  // Clear old draw chips because the ticket draft changed.
  displayedDraw = [];
  // Render the empty spot-selection state.
  render();
}

// Define newTicket to return from result comparison to an empty spot-selection board.
function newTicket() {
  // Clear all draft spots for a fresh ticket.
  selected.clear();
  // Clear the focused result while preserving persisted API history.
  lastDraw = null;
  // Clear the visible draw rail.
  displayedDraw = [];
  // Render the fresh selection state.
  render();
}

// Define randomSpots to generate unique Keno numbers for quick picks.
function randomSpots(count) {
  // Store generated spots in insertion order before sorting.
  const spots = [];
  // Continue until the requested number of unique spots has been generated.
  while (spots.length < count) {
    // Generate a legal Keno number.
    const number = 1 + Math.floor(Math.random() * 80);
    // Add the number only if it has not already been chosen.
    if (!spots.includes(number)) spots.push(number);
  }
  // Return spots in board order for readability.
  return spots.sort((a, b) => a - b);
}

// Define multiplierText to format paytable multipliers compactly.
function multiplierText(multiplier) {
  // Branch when a very large payout row should use the premium major label.
  if (Number(multiplier) >= 100000) return tx('paytable.major');
  // Return the normal multiplier label for ordinary paytable rows.
  return tx('paytable.multiplier', { multiplier: numberText(multiplier, { maximumFractionDigits: 2 }) });
}

// Define heroMetricHtml to render one premium state metric.
function heroMetricHtml(label, detail) {
  // Return the scoped metric card markup.
  return `<div class="keno-metric"><strong>${safe(label)}</strong><span>${safe(detail)}</span></div>`;
}

// Define heroMetricsHtml to render state-aware premium metrics from live Keno data.
function heroMetricsHtml() {
  // Store the current phase for metric selection.
  const phase = activePhase();
  // Store the primary human result for result-state metrics.
  const result = primaryHumanResult();
  // Store the visible catch count for drawing and result states.
  const catchCount = visibleCatchSet().size || result?.catch_count || 0;
  // Store the active eligible bot count.
  const botCount = botData.bots?.length || 0;
  // Branch for the active draw reveal state.
  if (phase === 'drawing') return [heroMetricHtml(tx('metric.drawn.label', { count: activeDrawNumbers().length, total: DRAW_TOTAL }), tx('metric.drawn.detail')), heroMetricHtml(tx('metric.catches.label', { count: catchCount }), tx('metric.catches.detail')), heroMetricHtml(tx('metric.botRound.label'), tx('metric.botRound.detail')), heroMetricHtml(tx('metric.autoplaySafe.label'), tx('metric.autoplaySafe.detail'))].join('');
  // Branch for completed result comparison.
  if (phase === 'result') return [heroMetricHtml(tx('metric.finalDraw.label', { total: DRAW_TOTAL }), tx('metric.finalDraw.detail')), heroMetricHtml(tx('metric.catches.label', { count: catchCount }), tx('metric.resultCatches.detail', { spots: result?.ticket?.spots?.length || selected.size || 0 })), heroMetricHtml(tx('metric.payout.label', { amount: moneyText(result?.payout || 0) }), tx('metric.payout.detail', { multiplier: multiplierText(result?.multiplier || 0) })), heroMetricHtml(tx('metric.history.label'), tx('metric.history.detail'))].join('');
  // Return spot-selection metrics by default.
  return [heroMetricHtml(tx('metric.board.label'), tx('metric.board.detail')), heroMetricHtml(tx('metric.spots.label'), tx('metric.spots.detail', { count: selected.size, max: MAX_SPOTS })), heroMetricHtml(tx('metric.bots.label'), tx('metric.bots.detail', { count: botCount })), heroMetricHtml(tx('metric.autoplay.label'), tx('metric.autoplay.detail'))].join('');
}

// Define heroHtml to render the game-level premium Keno header.
function heroHtml() {
  // Store the active phase key for localized headline text.
  const phase = activePhase();
  // Return the premium header with phase title and metrics.
  return `<header class="keno-hero" data-testid="keno-premium-hero"><div><p class="keno-eyebrow">${safe(tx(`phase.${phase}.eyebrow`))}</p><h1 class="keno-hero-title">${safe(tx(`phase.${phase}.title`))}</h1></div><div class="keno-metric-strip">${heroMetricsHtml()}</div></header>`;
}

// Define statusCardHtml to render the left rail draw/autoplay status card.
function statusCardHtml() {
  // Store the active phase for localized status text.
  const phase = activePhase();
  // Store the progress percentage for the fixed-height progress bar.
  const progress = Math.round((activeDrawNumbers().length / DRAW_TOTAL) * 100);
  // Branch for drawing status with a progress bar.
  if (phase === 'drawing') return `<div class="keno-action-card" data-testid="keno-draw-status"><div class="row"><span class="badge">${safe(tx('status.running'))}</span><strong>${safe(tx('status.drawCount', { count: activeDrawNumbers().length, total: DRAW_TOTAL }))}</strong></div><div class="keno-progress-track" aria-hidden="true"><div class="keno-progress-fill" style="width:${progress}%"></div></div><p class="muted">${safe(tx('status.drawing'))}</p></div>`;
  // Branch for completed result status.
  if (phase === 'result') return `<div class="keno-action-card" data-testid="keno-draw-status"><div class="row"><span class="badge">${safe(tx('status.ready'))}</span><strong>${safe(tx('status.repeatTicket'))}</strong></div><p class="muted">${safe(tx('status.resultReady'))}</p></div>`;
  // Return ready status for ticket selection.
  return `<div class="keno-action-card" data-testid="keno-draw-status"><div class="row"><span class="badge">${safe(tx('status.ready'))}</span><strong>${safe(tx('status.repeatTicket'))}</strong></div><p class="muted">${safe(tx('status.selectionReady'))}</p></div>`;
}

// Define botPanelHtml to render Keno-compatible bot controllers with localized headings.
function botPanelHtml() {
  // Store bot rows for the stable controller table.
  const rows = (botData.bots || []).map(bot => `<tr><td>${safe(bot.display_name || bot.bot_id)}</td><td>${safe(strategyLabel(bot.strategy_id))}</td><td>${safe(moneyText(bot.stake || 0))}</td><td>${safe(moneyText(bot.balance || 0))}</td></tr>`).join('');
  // Branch when the bot controller does not support Keno.
  if (!botData.capabilities?.supports_bots) return `<div class="bot-panel" data-testid="keno-bot-panel"><h3>${safe(tx('bot.title'))}</h3><p class="muted">${safe(tx('bot.empty'))}</p></div>`;
  // Return the localized bot panel with the eligible bot table.
  return `<div class="bot-panel" data-testid="keno-bot-panel"><div class="row"><h3>${safe(tx('bot.title'))}</h3><span class="badge">${safe(tx('bot.count', { count: botData.bots?.length || 0 }))}</span></div><table class="mini-table"><tr><th>${safe(tx('bot.table.bot'))}</th><th>${safe(tx('bot.table.strategy'))}</th><th>${safe(tx('bot.table.stake'))}</th><th>${safe(tx('bot.table.balance'))}</th></tr>${rows || `<tr><td colspan="4">${safe(tx('bot.noEligible'))}</td></tr>`}</table></div>`;
}

// Define ticketMetricsHtml to render stable amount and spot/catch counters.
function ticketMetricsHtml() {
  // Store the primary result only after the reveal has completed.
  const result = activePhase() === 'result' ? primaryHumanResult() : null;
  // Store the amount shown in the ticket rail.
  const displayAmount = result?.ticket?.amount ?? amount;
  // Store the secondary metric label for selected or caught spots.
  const secondaryLabel = result ? tx('ticket.catches') : tx('ticket.spots');
  // Store the secondary metric value for selected or caught spots.
  const secondaryValue = result ? numberText(result.catch_count) : tx('ticket.selectedOfMax', { count: selected.size, max: MAX_SPOTS });
  // Return two shared shell metric cards for the ticket rail.
  return `<div class="keno-ticket-metrics">${renderShellMetric(tx('ticket.amount'), moneyText(displayAmount))}${renderShellMetric(secondaryLabel, secondaryValue)}</div>`;
}

// Define ticketControlsHtml to render phase-aware ticket action buttons.
function ticketControlsHtml() {
  // Store whether the completed result actions should be shown.
  const resultMode = activePhase() === 'result';
  // Branch for replay and new-ticket controls after a completed result.
  if (resultMode) return `<div class="keno-button-pair"><button id="draw" data-testid="keno-draw" type="button" class="gold">${safe(tx('controls.replay'))}</button><button id="newTicket" data-testid="keno-new-ticket" type="button" class="primary">${safe(tx('controls.newTicket'))}</button></div>`;
  // Store disabled markup for controls that cannot run during an active draw.
  const disabled = drawBusy ? 'disabled' : '';
  // Return spot-selection ticket controls.
  return `<div class="keno-command-grid"><button id="quick5" type="button" ${disabled}>${safe(tx('controls.quickPick5'))}</button><button id="quick10" type="button" ${disabled}>${safe(tx('controls.quickPick10'))}</button><button id="clearSel" type="button" ${disabled}>${safe(tx('controls.clear'))}</button></div><div class="keno-button-pair action-row"><button id="buy" data-testid="keno-buy" type="button" class="gold" ${disabled}>${safe(tx('controls.buy'))}</button><button id="draw" data-testid="keno-draw" type="button" class="primary" ${disabled}>${safe(drawBusy ? tx('controls.drawing') : tx('controls.draw'))}</button></div>`;
}

// Define ticketPanelHtml to render the left Keno control rail.
function ticketPanelHtml() {
  // Store disabled input markup while a draw is active.
  const disabled = drawBusy ? 'disabled' : '';
  // Return the complete control rail with ticket, status, autoplay, and bot panels.
  return `<section class="panel control-rail keno-control-panel" data-testid="keno-ticket-drawer"><h2>${safe(tx('ticket.title'))}</h2>${ticketMetricsHtml()}<label>${safe(tx('ticket.amount'))}<input id="kenoAmount" data-testid="keno-amount" type="number" min="1" value="${safe(amount)}" ${disabled}></label>${ticketControlsHtml()}${statusCardHtml()}<div data-keno-auto></div>${botPanelHtml()}</section>`;
}

// Define boardCellHtml to render one stable Keno number button.
function boardCellHtml(number, drawnSet, catchSet, latest) {
  // Store whether this number is part of the current human ticket selection.
  const isSelected = selected.has(number) || activeTicketSpots().includes(number);
  // Store whether this number has been drawn.
  const isDrawn = drawnSet.has(number);
  // Store whether this number is a visible human catch.
  const isCatch = catchSet.has(number);
  // Store all visual state classes for this cell.
  const classes = ['keno-num', isSelected ? 'selected' : '', isDrawn ? 'drawn' : '', isCatch ? 'catch' : '', latest === number ? 'latest' : ''].filter(Boolean).join(' ');
  // Return the fixed-size number button with its stable test id.
  return `<button type="button" class="${classes}" data-num="${number}" data-keno-num="${number}" data-testid="keno-num-${number}" aria-pressed="${isSelected ? 'true' : 'false'}" ${drawBusy ? 'disabled' : ''}>${number}</button>`;
}

// Define boardHtml to render the 1-80 Keno board.
function boardHtml() {
  // Store drawn numbers as a Set for efficient cell state checks.
  const drawnSet = new Set(activeDrawNumbers());
  // Store visible catches as a Set for efficient cell state checks.
  const catchSet = visibleCatchSet();
  // Store the latest draw number so the reveal animation can target one cell.
  const latest = latestDrawNumber();
  // Return the stable 10 x 8 board markup.
  return `<div class="keno-board-shell"><div class="keno-board-scroll" data-testid="keno-board-scroll" tabindex="0" role="region" aria-label="${safe(tx('board.scrollLabel'))}"><div class="keno-grid keno-premium-board" data-testid="keno-grid">${Array.from({ length: 80 }, (_, index) => boardCellHtml(index + 1, drawnSet, catchSet, latest)).join('')}</div></div></div>`;
}

// Define ballRailHtml to render drawn-ball chips in a reserved stage rail.
function ballRailHtml() {
  // Store visible draw numbers for rail chips.
  const numbers = activeDrawNumbers();
  // Store the latest draw number for chip emphasis.
  const latest = latestDrawNumber();
  // Store rendered ball chips or an empty-state label.
  const chips = numbers.length ? numbers.map(number => `<span class="ball ${latest === number ? 'latest' : ''}" data-testid="keno-drawn-ball">${number}</span>`).join('') : `<span class="muted">${safe(tx('drawn.empty'))}</span>`;
  // Return the fixed-height ball rail.
  return `<div class="keno-ball-rail" data-testid="keno-drawn-balls">${chips}</div>`;
}

// Define resultCopyHtml to render the fixed result summary below the board.
function resultCopyHtml() {
  // Store the active phase for summary selection.
  const phase = activePhase();
  // Store the primary human result for completed summaries.
  const result = primaryHumanResult();
  // Store selected spots for selection summaries.
  const spots = selectedNumbers();
  // Branch for drawing progress text.
  if (phase === 'drawing') return `<div class="result-box fixed-result keno-result-copy" data-testid="keno-result"><strong>${safe(tx('status.drawingLead', { count: activeDrawNumbers().length, total: DRAW_TOTAL }))}</strong> ${safe(tx('status.drawingSummary', { catches: visibleCatchSet().size }))}</div>`;
  // Branch for completed result text.
  if (result) {
    // Store net outcome after the already-debited ticket amount.
    const net = Number(result.payout || 0) - Number(result.ticket?.amount || 0);
    // Select the singular lead copy for a one-catch ticket so the count agrees with the noun. (issue #237)
    const leadKey = result.catch_count === 1 ? 'status.resultLeadOne' : 'status.resultLead';
    // Return the completed result summary.
    return `<div class="result-box fixed-result keno-result-copy" data-testid="keno-result"><strong>${safe(tx(leadKey, { catches: result.catch_count, spots: result.ticket.spots.length }))}</strong> ${safe(tx('status.resultSummary', { payout: moneyText(result.payout), net: moneyText(net) }))}</div>`;
  }
  // Return the selected-ticket summary or empty selection prompt.
  return `<div class="result-box fixed-result keno-result-copy" data-testid="keno-result"><strong>${safe(tx('status.selectedLead'))}</strong> ${safe(spots.length ? tx('status.selectedSummary', { spots: spots.join(', ') }) : tx('status.noSelection'))}</div>`;
}

// Define stageHtml to render the center Keno board and reveal surfaces.
function stageHtml() {
  // Store the active phase key for the stage title.
  const phase = activePhase();
  // Return the stage panel with fixed board, ball rail, and result region.
  return `<section class="panel game-stage keno-stage-panel"><h2>${safe(tx(`phase.${phase}.boardTitle`))}</h2>${boardHtml()}${ballRailHtml()}${resultCopyHtml()}</section>`;
}

// Define ticketChipRowHtml to render a set of Keno numbers as compact ticket chips.
function ticketChipRowHtml(numbers) {
  // Return sorted chip markup for selected, open, or historical ticket spots.
  return `<div class="keno-ticket-chip-row">${sortedNumbers(numbers).map(number => `<span class="keno-ticket-chip">${number}</span>`).join('')}</div>`;
}

// Define drawnChipRowHtml to render drawn balls as compact drawer chips.
function drawnChipRowHtml(numbers) {
  // Return sorted chip markup for drawn-ball drawer surfaces.
  return `<div class="keno-drawn-chip-row">${sortedNumbers(numbers).map(number => `<span class="keno-drawn-chip">${number}</span>`).join('')}</div>`;
}

// Define ticketDrawerHtml to render open ticket and selected-ticket surfaces.
function ticketDrawerHtml() {
  // Store open human tickets for the drawer.
  const tickets = currentHumanTickets();
  // Store selected spots for the draft ticket fallback.
  const draft = selectedNumbers();
  // Store rendered open ticket rows.
  const ticketRows = tickets.map(ticket => `<div class="bet-item" data-testid="keno-open-ticket"><span>${ticketChipRowHtml(ticket.spots)}</span><b>${safe(moneyText(ticket.amount))}</b><button type="button" class="danger" data-clear="${safe(ticket.ticket_id)}" data-testid="keno-clear-ticket">${safe(tx('ticket.cancel'))}</button></div>`).join('');
  // Store draft ticket markup when no purchased ticket exists.
  const draftRow = !tickets.length && draft.length ? `<div class="keno-action-card" data-testid="keno-selected-ticket"><div class="row"><strong>${safe(tx('ticket.selectedTicket'))}</strong><span class="badge">${safe(tx('ticket.selectedOfMax', { count: draft.length, max: MAX_SPOTS }))}</span></div>${ticketChipRowHtml(draft)}</div>` : '';
  // Store the empty fallback when neither open nor draft tickets exist.
  const empty = !ticketRows && !draftRow ? `<p class="muted">${safe(tx('ticket.none'))}</p>` : '';
  // Return the drawer section.
  return `<section data-testid="keno-ticket-detail-drawer"><h3>${safe(tx('drawer.openTicket'))}</h3><div class="bet-list stable-list">${ticketRows}${draftRow}${empty}</div></section>`;
}

// Define paytableEntries to return the current paytable row entries.
function paytableEntries(spots) {
  // Store the row using either numeric or string keys from the API payload.
  const row = paytable?.[spots] || paytable?.[String(spots)] || {};
  // Return catch-count and multiplier pairs sorted by catch count.
  return Object.entries(row).map(([catches, multiplier]) => [Number(catches), Number(multiplier)]).sort((a, b) => a[0] - b[0]);
}

// Define paytableRowsHtml to render a paytable preview or comparison list.
function paytableRowsHtml(spots, activeCatch = null) {
  // Store row entries for the selected spot count.
  const baseEntries = paytableEntries(spots);
  // Add the actual catch count as a zero-multiplier row when the paytable has no payout for it.
  const entries = activeCatch === null || baseEntries.some(([catches]) => catches === activeCatch) ? baseEntries : [...baseEntries, [activeCatch, 0]].sort((a, b) => a[0] - b[0]);
  // Branch when the API row is unavailable.
  if (!entries.length) return `<p class="muted">${safe(tx('paytable.empty'))}</p>`;
  // Return paytable row markup with the active catch highlighted when present.
  return entries.map(([catches, multiplier]) => `<div class="keno-pay-row ${activeCatch === catches ? 'active' : ''}" ${activeCatch === catches ? 'data-testid="keno-paytable-active"' : ''}><span>${safe(tx('paytable.row', { spots, catches }))}</span><strong>${safe(multiplierText(multiplier))}</strong></div>`).join('');
}

// Define paytablePreviewHtml to render the right drawer paytable preview.
function paytablePreviewHtml() {
  // Store the active spot count for preview.
  const spots = activeSpotCount();
  // Return the preview list for the current ticket size.
  return `<section data-testid="keno-paytable-preview"><h3>${safe(tx('paytable.preview'))}</h3><div class="keno-paytable-list">${paytableRowsHtml(spots)}</div></section>`;
}

// Define paytableComparisonHtml to render the completed result paytable comparison.
function paytableComparisonHtml() {
  // Store the primary result for comparison context.
  const result = primaryHumanResult();
  // Store the active spot count for comparison rows.
  const spots = result?.ticket?.spots?.length || activeSpotCount();
  // Return the comparison list with the caught row highlighted.
  return `<section data-testid="keno-paytable-comparison"><h3>${safe(tx('drawer.paytableComparison'))}</h3><div class="keno-paytable-list">${paytableRowsHtml(spots, result?.catch_count ?? null)}</div></section>`;
}

// Define drawnDrawerHtml to render the live drawn-ball drawer.
function drawnDrawerHtml() {
  // Store visible draw numbers for the drawer.
  const numbers = activeDrawNumbers();
  // Store content or fallback text for the drawer.
  const content = numbers.length ? drawnChipRowHtml(numbers) : `<p class="muted">${safe(tx('drawn.empty'))}</p>`;
  // Return the drawn-ball drawer section.
  return `<section><h3>${safe(tx('drawer.drawnBalls'))}</h3>${content}</section>`;
}

// Define botResultsHtml to render bot draw outcomes under the reserved drawer.
function botResultsHtml() {
  // Store current bot settlement results.
  const rows = botResults().map(result => `<tr><td>${safe(result.ticket.player_id)}</td><td>${safe(tx('bot.resultCatches', { count: result.catch_count }))}</td><td>${safe(moneyText(result.payout))}</td></tr>`).join('');
  // Store recent bot action count for draws still in progress.
  const actionNote = lastBotActions.length ? `<p class="muted">${safe(tx('bot.actions', { count: lastBotActions.length }))}</p>` : '';
  // Return the bot result table or stable empty state.
  return `<section><h3>${safe(tx('bot.resultsTitle'))}</h3>${actionNote}<table class="mini-table" data-testid="keno-bot-results"><tr><th>${safe(tx('bot.table.bot'))}</th><th>${safe(tx('bot.table.catches'))}</th><th>${safe(tx('bot.table.payout'))}</th></tr>${rows || `<tr><td colspan="3">${safe(tx('bot.resultsEmpty'))}</td></tr>`}</table></section>`;
}

// Define lastDrawHtml to render the completed draw chip set.
function lastDrawHtml() {
  // Store completed drawn numbers for the last draw panel.
  const numbers = lastDraw?.drawn || [];
  // Return the last draw panel with sorted chips.
  return `<section><h3>${safe(tx('drawer.lastDraw'))}</h3>${numbers.length ? drawnChipRowHtml(numbers) : `<p class="muted">${safe(tx('drawn.empty'))}</p>`}</section>`;
}

// Define historyHtml to render recent Keno history rows from persisted state.
function historyHtml() {
  // Store the newest persisted draws first.
  const draws = [...(state?.last_draws || [])].slice(-8).reverse();
  // Store rendered history rows.
  const rows = draws.map(drawItem => {
    // Store the human result for this historical draw.
    const result = (drawItem.results || []).find(item => item.ticket?.player_id === currentPlayerId());
    // Store the row summary text.
    const summary = result ? tx('history.row', { catches: result.catch_count, spots: result.ticket.spots.length, payout: moneyText(result.payout) }) : tx('history.noHuman');
    // Return one history row with a safe round id and summary.
    return `<div class="keno-history-row"><span>${safe(drawItem.round_id)}</span><strong>${safe(summary)}</strong></div>`;
  // Join all mapped history rows into one drawer fragment.
  }).join('');
  // Return the history list or empty state.
  return `<section data-testid="keno-history"><h3>${safe(tx('history.title'))}</h3><div class="keno-history-list scrollbox">${rows || `<p class="muted">${safe(tx('history.empty'))}</p>`}</div></section>`;
}

// Define drawerHtml to render the right details drawer for the active Keno state.
function drawerHtml() {
  // Store the active phase for drawer composition.
  const phase = activePhase();
  // Branch for live draw details.
  if (phase === 'drawing') return `<section class="panel details-drawer keno-detail-panel" data-testid="keno-detail-drawer">${drawnDrawerHtml()}${botResultsHtml()}</section>`;
  // Branch for result comparison details.
  if (phase === 'result') return `<section class="panel details-drawer keno-detail-panel" data-testid="keno-detail-drawer">${paytableComparisonHtml()}${lastDrawHtml()}${botResultsHtml()}${historyHtml()}</section>`;
  // Return selection details by default.
  return `<section class="panel details-drawer keno-detail-panel" data-testid="keno-detail-drawer">${ticketDrawerHtml()}${paytablePreviewHtml()}${historyHtml()}</section>`;
}

// Define bindEvents to wire controls after each route-local render.
function bindEvents() {
  // Wire every Keno number cell to spot selection.
  root.querySelectorAll('[data-keno-num]').forEach(button => { button.onclick = () => toggleSpot(Number(button.dataset.kenoNum)); });
  // Wire the amount input to local state.
  root.querySelector('#kenoAmount')?.addEventListener('change', () => { readAmount(); render(); });
  // Wire quick-pick controls when they are present.
  root.querySelector('#quick5')?.addEventListener('click', () => quickPick(5));
  // Wire the ten-spot quick-pick control when it is present.
  root.querySelector('#quick10')?.addEventListener('click', () => quickPick(10));
  // Wire the clear-selection control when it is present.
  root.querySelector('#clearSel')?.addEventListener('click', clearSelection);
  // Wire the buy-ticket control when it is present.
  root.querySelector('#buy')?.addEventListener('click', () => buyTicket());
  // Wire the draw or replay control when it is present.
  root.querySelector('#draw')?.addEventListener('click', () => draw(true));
  // Wire the new-ticket control when result mode is present.
  root.querySelector('#newTicket')?.addEventListener('click', newTicket);
  // Wire every cancel button to the ticket refund API.
  root.querySelectorAll('[data-clear]').forEach(button => { button.onclick = () => clearTicket(button.dataset.clear); });
  // Mount the shared autoplay control plane into the reserved Keno rail.
  autoBox = renderAutoplay({ id: 'keno', plan: { type: 'repeat_ticket' }, onTick: async () => draw(false) });
  // Append the shared autoplay panel into the current render.
  root.querySelector('[data-keno-auto]')?.append(autoBox);
}

// Define render to paint the premium Keno route into the shared shell outlet.
function render() {
  // Branch when the route has been unmounted.
  if (!root) return;
  // Set route markup using only the shared #view mount point.
  root.innerHTML = `<section class="keno-premium">${heroHtml()}<div class="game-layout three-col stable-game keno-layout">${ticketPanelHtml()}${stageHtml()}${drawerHtml()}</div></section>`;
  // Bind controls after the markup has been replaced.
  bindEvents();
}

// Export this symbol so the shared shell can mount and unmount the Keno route.
export const KenoGame = {
  // Expose the game id used by the shared shell and autoplay control plane.
  id: 'keno',
  // Expose the route label used by legacy module consumers.
  label: 'Keno',
  // Mount Keno into the supplied route outlet.
  async mount(node) {
    // Store the shared shell route outlet.
    root = node;
    // Install route-local premium styles before the first render.
    ensureStyles();
    // Subscribe to locale changes so Keno text updates without remounting gameplay state.
    localeUnsubscribe = onLocaleChange(() => render());
    // Load state, resources, and bot metadata before rendering.
    await load();
  },
  // Unmount Keno and release shared control-plane subscriptions.
  unmount() {
    // Stop Keno autoplay through the shared control-plane helper when mounted.
    if (autoBox?._stop) autoBox._stop();
    // Remove the locale subscription when one exists.
    if (localeUnsubscribe) localeUnsubscribe();
    // Clear the locale unsubscribe reference for the next mount.
    localeUnsubscribe = null;
    // Clear the route outlet reference.
    root = null;
  }
};
