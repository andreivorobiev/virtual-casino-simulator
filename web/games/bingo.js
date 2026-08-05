// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import the frozen API helpers used by the Bingo browser module.
import { api, post, currentPlayerId, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared premium UI helpers for balance refreshes, escaping, tags, and shell metrics.
import { refreshBalance, safe, renderPremiumTag, renderShellMetric, toast, captureGameFocus, restoreGameFocus, syncGameLiveStatus } from '../core/ui.js';
// Import the shared autoplay controller so Bingo remains a control-plane loop.
import { renderAutoplay, stopAutoplay } from '../core/autoplay.js';
// Import shared sound helpers for the same call feedback used by the legacy Bingo UI.
import { speak, clickSound } from '../core/voice.js';
// Import shared bot helpers so bot cards still use public controller actions.
import { botPanelHtml, playBotRound } from '../core/bots.js';
// Import the i18n runtime so Bingo-owned visible strings live in locale resources.
import { initI18n, t, onLocaleChange, formatMoney, formatNumber } from '../core/i18n.js';

// Store the i18n domain used by this module's resource files.
const I18N_DOMAIN = 'games/bingo';
// Store the fixed Bingo column order required by the 75-ball rules.
const COLUMNS = ['B', 'I', 'N', 'G', 'O'];
// Store the total ball count so call progress is calculated in one place.
const TOTAL_BALLS = 75;
// Store supported pattern ids so the select stays aligned with the API contract.
const PATTERNS = ['line', 'four_corners', 'postage_stamp', 'blackout'];
// Store the style element id so scoped CSS is injected only once.
const STYLE_ID = 'premium-bingo-styles';
// Store scoped CSS for the premium Bingo module without touching shared stylesheet ownership.
const BINGO_CSS = '.premium-bingo{display:grid;grid-template-rows:auto minmax(0,1fr);gap:14px;height:100%;min-height:0}.premium-bingo-hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(460px,0.78fr);gap:18px;align-items:end}.premium-bingo-kicker{margin:0 0 4px;color:var(--gold);font-weight:900}.premium-bingo-title{margin:0;color:var(--text);font-family:var(--font-display);font-size:46px;line-height:1}.premium-bingo-subtitle{max-width:760px;margin:8px 0 0;color:var(--muted)}.premium-bingo-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.premium-bingo-grid{min-height:0}.premium-bingo .control-rail,.premium-bingo .details-drawer{display:grid;align-content:start;gap:12px}.premium-bingo .game-stage{display:grid;grid-template-rows:auto minmax(0,1fr) 138px;gap:12px;padding:16px}.premium-bingo-config{display:grid;grid-template-columns:1fr 1fr;gap:10px}.premium-bingo-field{display:grid;gap:6px;padding:12px;border:1px solid var(--border-soft);border-radius:13px;background:rgba(255,255,255,.04)}.premium-bingo-field span{color:var(--muted);font-size:12px;font-weight:800}.premium-bingo-field input,.premium-bingo-field select{width:100%;min-width:0}.premium-bingo-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}.premium-bingo [data-testid="bingo-control-rail"][aria-busy="true"] button:disabled,.premium-bingo [data-testid="bingo-control-rail"][aria-busy="true"] input:disabled,.premium-bingo [data-testid="bingo-control-rail"][aria-busy="true"] select:disabled{opacity:.55;cursor:wait}.premium-bingo-status-card{display:grid;gap:10px;padding:12px;border:1px solid var(--border-soft);border-radius:14px;background:rgba(0,0,0,.18)}.premium-bingo-status-row{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center}.premium-bingo-dot{width:10px;height:10px;border-radius:50%;background:var(--ok);box-shadow:0 0 18px var(--ok)}.premium-bingo-dot.is-won{background:#ff6670;box-shadow:0 0 18px #ff6670}.premium-bingo-progress{height:12px;overflow:hidden;border-radius:99px;background:rgba(255,255,255,.09)}.premium-bingo-progress span{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--brand-strong),var(--gold),var(--accent));transition:width .22s ease}.premium-bingo-stage-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.premium-bingo-stage-title{margin:0;color:var(--text);font-family:var(--font-display);font-size:30px}.premium-bingo-card-wrap{display:grid;place-items:center;min-height:0}.premium-bingo .bingo-card{width:min(100%,760px);max-width:760px;min-height:500px;display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:74px repeat(5,minmax(64px,1fr));gap:8px;margin:0 auto;padding:14px;border:1px solid var(--gold);border-radius:18px;background:rgba(0,0,0,.2);box-shadow:inset 0 0 32px rgba(255,199,83,.08)}.premium-bingo .bingo-head,.premium-bingo .bingo-cell{min-height:0;border-radius:12px}.premium-bingo .bingo-head{color:#1d1100;background:linear-gradient(180deg,var(--metal-gold),var(--metal-gold-deep));font-family:var(--font-display);font-size:30px}.premium-bingo .bingo-cell{position:relative;overflow:hidden;color:var(--text);background:linear-gradient(180deg,rgba(255,255,255,.08),rgba(255,255,255,.025));font-size:24px}.premium-bingo .bingo-cell.marked{color:var(--text);background:linear-gradient(180deg,rgba(255,255,255,.09),rgba(255,255,255,.03))}.premium-bingo .bingo-cell.latest{box-shadow:inset 0 0 0 2px rgba(255,59,107,.5)}.premium-bingo .bingo-cell.win{outline:4px solid var(--accent);box-shadow:0 0 22px rgba(34,224,195,.72),inset 0 0 24px rgba(34,224,195,.2)}.premium-bingo-cell-value{position:relative;z-index:2}.bingo-daub{position:absolute;inset:50% auto auto 50%;z-index:1;width:48px;height:48px;border:4px solid rgba(255,113,122,.34);border-radius:50%;background:radial-gradient(circle at 35% 30%,rgba(255,105,115,.92),rgba(157,18,31,.88));box-shadow:0 6px 18px rgba(0,0,0,.32);opacity:.78;transform:translate(-50%,-50%) scale(.92);animation:bingoDaubIn .18s ease-out}.premium-bingo-call-bay{display:flex;align-items:center;gap:22px;min-height:138px;padding:16px;border:1px solid var(--border-soft);border-radius:16px;background:rgba(0,0,0,.18)}.premium-bingo-orb{display:grid;place-items:center;flex:0 0 96px;width:96px;height:96px;border-radius:50%;color:#3a1600;background:radial-gradient(circle at 35% 25%,#fff7cf,#e7c45f 70%,#a36f16);box-shadow:0 0 28px rgba(255,220,130,.5);font-size:27px;font-weight:1000}.premium-bingo-orb.is-calling{animation:bingoLatestPulse .8s ease-in-out infinite}.premium-bingo-call-copy{min-width:0}.premium-bingo-call-copy strong{display:block;color:var(--text)}.premium-bingo-chip-row{display:flex;flex-wrap:wrap;gap:6px;max-height:118px;overflow:auto}.premium-bingo-called-chip{min-width:auto;min-height:28px;padding:4px 10px;border-radius:999px;color:var(--text);background:rgba(255,199,83,.11)}.premium-bingo-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;margin:8px 0;padding:11px 12px;border:1px solid var(--border-soft);border-radius:12px;background:rgba(255,255,255,.035)}.premium-bingo-row.is-active{border-color:var(--gold);background:rgba(255,199,83,.1)}.premium-bingo-row b{color:var(--text)}.premium-bingo-row small{display:block;color:var(--muted)}.premium-bingo-result-grid{display:grid;gap:6px}.premium-bingo-empty{display:grid;place-items:center;min-height:160px;color:var(--muted);text-align:center}.premium-bingo .tag-row{margin-top:10px}@keyframes bingoDaubIn{from{opacity:0;transform:translate(-50%,-50%) scale(.35)}to{opacity:.78;transform:translate(-50%,-50%) scale(.92)}}@keyframes bingoLatestPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}} @media (prefers-reduced-motion:reduce){[class*="bingo"]{animation:none!important;transition:none!important;}}@media (max-width:1100px){.premium-bingo-hero{grid-template-columns:1fr}.premium-bingo-metrics{grid-template-columns:repeat(4,minmax(0,1fr))}.premium-bingo .game-stage{grid-template-rows:auto auto 138px}.premium-bingo .bingo-card{min-height:430px}}@media (max-width:760px){.premium-bingo{height:auto}.premium-bingo-title{font-size:34px}.premium-bingo-metrics{grid-template-columns:1fr 1fr}.premium-bingo-config,.premium-bingo-actions{grid-template-columns:1fr}.premium-bingo .bingo-card{min-height:330px;grid-template-rows:52px repeat(5,52px);gap:5px;padding:8px}.premium-bingo .bingo-head{font-size:22px}.premium-bingo .bingo-cell{font-size:18px}.bingo-daub{width:36px;height:36px}.premium-bingo-call-bay{align-items:flex-start;min-height:132px}.premium-bingo-orb{flex-basis:72px;width:72px;height:72px;font-size:20px}}.premium-bingo-repeat{background:transparent;color:var(--gold);border:1px solid var(--gold);min-height:44px}.premium-bingo-repeat:disabled{opacity:.5}';

// Store the root node supplied by the shell mount contract.
let root = null;
// Store the latest full Bingo state returned by the API.
let state = null;
// Store the current autoplay widget so unmount can stop its session.
let autoBox = null;
// Store the current human card amount between rerenders.
let amount = 5;
// Store the current selected pattern between rerenders.
let pattern = 'line';
// Store the last purchased amount and pattern so one click can repeat the buy.
let lastBet = null;
// Store the bot panel markup because the core bot helper renders asynchronously.
let botPanelCache = '';
// Store whether a call request is in flight so the layout can show a fixed busy state.
let callBusy = false;
// Store whether a human card purchase is unresolved so duplicate clicks cannot debit twice.
let purchaseBusy = false;
// Store the last session returned by a call so won sessions remain visible after active_session clears.
let displayedSession = null;
// Store the latest B/I/N/G/O label for the fixed call display.
let lastLabel = '';
// Store the latest called number for daub emphasis on the card.
let lastNumber = null;
// Store the active locale subscription cleanup function.
let unsubscribeLocale = null;

// Define tr so every Bingo-owned string lookup uses the same domain.
function tr(key, params = {}) {
  // Return the localized string from the Bingo resource file.
  return t(key, params, I18N_DOMAIN);
}

// Define ensureStyles so module-owned premium CSS stays scoped to Bingo.
function ensureStyles() {
  // Stop when this module has already installed its scoped style element.
  if (document.getElementById(STYLE_ID)) return;
  // Create a style element for this module's scoped selectors.
  const style = document.createElement('style');
  // Mark the style element so repeated mounts do not duplicate CSS.
  style.id = STYLE_ID;
  // Attach the scoped CSS text for the premium Bingo layout.
  style.textContent = BINGO_CSS;
  // Add the style element to the document head.
  document.head.append(style);
}

// Define patternLabel so API pattern ids become localized visible labels.
function patternLabel(value) {
  // Return the localized pattern label or the escaped raw id as a fallback.
  return tr(`patterns.${value || 'line'}`) || safe(value || 'line');
}

// Define latestCompletedSession to recover the newest completed session from state.
function latestCompletedSession() {
  // Store the immutable session list returned by the API.
  const sessions = state?.last_sessions || [];
  // Return the newest completed session or null when no history exists.
  return sessions.length ? sessions[sessions.length - 1] : null;
}

// Define currentSession so render can choose active, just-won, or recent session data.
function currentSession() {
  // Prefer the active API session while a round is still in progress.
  return state?.active_session || displayedSession || latestCompletedSession();
}

// Define calledNumbers so null sessions still produce a stable empty array.
function calledNumbers(session) {
  // Return the called-ball list from the selected session.
  return session?.called || [];
}

// Define calledCount so labels and progress bars share one calculation.
function calledCount(session) {
  // Return the number of called balls for the selected session.
  return calledNumbers(session).length;
}

// Define latestCalledNumber so the UI can emphasize the newest daub.
function latestCalledNumber(session) {
  // Store the called balls for this session.
  const called = calledNumbers(session);
  // Return the last called number or null before the first call.
  return called.length ? called[called.length - 1] : null;
}

// Define label so called numbers use the frozen B/I/N/G/O presentation.
function label(value) {
  // Preserve the free-space label when rendering the center cell.
  if (value === 'FREE') return tr('card.free');
  // Normalize the value to a number before applying Bingo column ranges.
  const n = Number(value);
  // Return a safe fallback if the value is not numeric.
  if (!Number.isFinite(n)) return safe(value);
  // Return the B-column label for 1 through 15.
  if (n <= 15) return `B-${n}`;
  // Return the I-column label for 16 through 30.
  if (n <= 30) return `I-${n}`;
  // Return the N-column label for 31 through 45.
  if (n <= 45) return `N-${n}`;
  // Return the G-column label for 46 through 60.
  if (n <= 60) return `G-${n}`;
  // Return the O-column label for 61 through 75.
  return `O-${n}`;
}

// Define loadingBotsHtml so the initial bot panel has localized Bingo-owned text.
function loadingBotsHtml() {
  // Return a stable placeholder while the shared bot panel loads.
  return `<div class="bot-panel"><p class="muted">${safe(tr('bots.loading'))}</p></div>`;
}

// Define humanCardRecord to find the human card without relying on display order.
function humanCardRecord(session) {
  // Return null when there is no session to inspect.
  if (!session) return null;
  // Return the explicit current-player card record when cards are present.
  return (session.cards || []).find(card => card.player_id === currentPlayerId()) || (session.card ? { card_id: 'current-player-card', player_id: currentPlayerId(), amount: session.amount, card: session.card, status: session.status, payout: session.payout || 0 } : null);
}

// Define stageCardRecord so completed sessions can highlight the actual winning card.
function stageCardRecord(session) {
  // Show the winning card after settlement so pattern highlights are always visible.
  if (session?.status === 'won' && session?.winner_card) return session.winner_card;
  // Otherwise show the human card during purchase and ball-call states.
  return humanCardRecord(session);
}

// Define winningCoordSet so cell rendering can use constant-time highlight checks.
function winningCoordSet(record, session) {
  // Store explicit coordinates from the card record when available.
  const coords = record?.winning_coords || (record?.card_id === session?.winner_card?.card_id ? session?.winner_card?.winning_coords : []) || [];
  // Return the coordinates as a string set keyed by row and column index.
  return new Set(coords.map(coord => coord.join(',')));
}

// Define countMarks so the cards-in-play drawer can summarize daub progress.
function countMarks(record, session) {
  // Return zero when the card record is missing.
  if (!record?.card) return 0;
  // Store called numbers as a set for quick card checks.
  const called = new Set(calledNumbers(session));
  // Store the running mark count for the card.
  let count = 0;
  // Iterate through each Bingo column in rule order.
  for (const column of COLUMNS) {
    // Iterate through each value in the current card column.
    for (const value of record.card[column] || []) {
      // Count free space and called values as marked cells.
      if (value === 'FREE' || called.has(value)) count += 1;
    }
  }
  // Return the total marked-cell count for this card.
  return count;
}

// Define sessionCards so drawer rendering has a stable card collection.
function sessionCards(session) {
  // Return the explicit cards list or synthesize the legacy human card shape.
  return session?.cards?.length ? session.cards : (humanCardRecord(session) ? [humanCardRecord(session)] : []);
}

// Define statusKey so status rendering has one state classification.
function statusKey(session) {
  // Show the in-flight state while the call endpoint is pending.
  if (callBusy) return 'calling';
  // Show complete when the selected session has settled.
  if (session?.status === 'won') return 'complete';
  // Show running while the API has an active session.
  if (state?.active_session) return 'running';
  // Fall back to ready before card purchase.
  return 'ready';
}

// Define progressPercent so the progress bar never changes layout.
function progressPercent(session) {
  // Return bounded progress through the 75-ball draw.
  return Math.max(0, Math.min(100, Math.round((calledCount(session) / TOTAL_BALLS) * 100)));
}

// Define heroHtml to render the premium Bingo header above the fixed game grid.
function heroHtml(session) {
  // Store current cards so card and bot metrics reflect the displayed session.
  const cards = sessionCards(session);
  // Store bot card count separately from the human card.
  const botCount = cards.filter(card => card.player_id !== currentPlayerId()).length;
  // Render premium capability tags with the shared UI helper.
  const tags = [tr('tags.fakeMoney'), tr('tags.ledger'), tr('tags.autoplay')].map(renderPremiumTag).join('');
  // Render shell metrics with the shared helper so Bingo follows the foundation contract.
  const metrics = [renderShellMetric(tr('metric.rules.label'), tr('metric.rules.value')), renderShellMetric(tr('metric.pattern.label'), patternLabel(session?.pattern || pattern)), renderShellMetric(tr('metric.calls.label'), `${formatNumber(calledCount(session))}/${formatNumber(TOTAL_BALLS)}`), renderShellMetric(tr('metric.bots.label'), formatNumber(botCount))].join('');
  // Return the complete premium Bingo header.
  return `<header class="premium-bingo-hero"><div><p class="premium-bingo-kicker">${safe(tr('kicker'))}</p><h1 class="premium-bingo-title">${safe(tr('title'))}</h1><p class="premium-bingo-subtitle">${safe(tr('subtitle'))}</p><div class="tag-row">${tags}</div></div><div class="premium-bingo-metrics">${metrics}</div></header>`;
}

// Define statusCardHtml to render the reserved autoplay and call-state summary.
function statusCardHtml(session) {
  // Store the current state key for localized labels and styling.
  const key = statusKey(session);
  // Store the progress value for the fixed progress bar.
  const progress = progressPercent(session);
  // Store a localized right-side status value.
  const right = key === 'running' ? `${formatNumber(calledCount(session))}/${formatNumber(TOTAL_BALLS)}` : tr(`status.right.${key}`);
  // Return the status panel that stays the same size across ready, calling, and won states.
  return `<div class="premium-bingo-status-card" data-testid="bingo-status-card"><div class="premium-bingo-status-row"><span class="premium-bingo-dot ${key === 'complete' ? 'is-won' : ''}"></span><b>${safe(tr(`status.${key}`))}</b><strong>${safe(right)}</strong></div><div class="premium-bingo-progress" aria-label="${safe(tr('status.progress'))}"><span style="width:${progress}%"></span></div><p class="muted">${safe(tr(`status.description.${key}`))}</p></div>`;
}

// Define botSummaryHtml to keep bot-card context near the controls.
function botSummaryHtml(session) {
  // Store the number of bot cards currently attached to the session.
  const botCount = sessionCards(session).filter(card => card.player_id !== currentPlayerId()).length;
  // Store the state-specific summary key.
  const key = session?.status === 'won' ? 'settled' : (botCount ? 'tracking' : 'available');
  // Return a compact localized bot-card summary.
  return `<div class="premium-bingo-status-card"><div class="premium-bingo-status-row"><span class="premium-bingo-dot"></span><b>${safe(tr('botSummary.title'))}</b><strong>${safe(tr(`botSummary.${key}`, { count: formatNumber(botCount) }))}</strong></div><p class="muted">${safe(tr(`botSummary.${key}Text`))}</p></div>`;
}

// Define controlsHtml to render the left Bingo command rail.
function controlsHtml(session) {
  // Store whether the call button can start a new atomic call.
  const canCall = Boolean(state?.active_session) && !callBusy && !purchaseBusy;
  // Store whether a new card can be purchased without conflicting with an active session.
  const canBuy = !state?.active_session && !callBusy && !purchaseBusy;
  // Disable purchase configuration while its submitted values are being committed.
  const purchaseDisabled = purchaseBusy ? 'disabled' : '';
  // Store the localized buy button label for first and follow-up cards.
  const buyLabel = purchaseBusy ? `${tr('control.buy')}…` : (session?.status === 'won' ? tr('control.buyNext') : tr('control.buy'));
  // Render all supported pattern options from the frozen pattern list.
  const options = PATTERNS.map(value => `<option value="${safe(value)}">${safe(patternLabel(value))}</option>`).join('');
  // Return the complete control rail with fixed sections for status, autoplay, and bots.
  return `<section class="panel control-rail" data-testid="bingo-control-rail" aria-busy="${purchaseBusy ? 'true' : 'false'}"><h2>${safe(tr('control.title'))}</h2><div class="premium-bingo-config"><label class="premium-bingo-field"><span>${safe(tr('control.amount'))}</span><input id="bingoAmount" type="number" min="1" value="${safe(amount)}" data-testid="bingo-amount" ${purchaseDisabled}></label><label class="premium-bingo-field"><span>${safe(tr('control.pattern'))}</span><select id="bingoPattern" data-testid="bingo-pattern" ${purchaseDisabled}>${options}</select></label></div><div class="premium-bingo-actions action-row"><button id="buy" data-testid="bingo-buy" class="gold" ${canBuy ? '' : 'disabled'}>${safe(buyLabel)}</button><button id="call" data-testid="bingo-call" class="primary" ${canCall ? '' : 'disabled'}>${safe(callBusy ? tr('control.calling') : tr('control.call'))}</button></div><button id="bingoRepeat" data-testid="bingo-repeat" class="premium-bingo-repeat" ${canBuy && lastBet ? '' : 'disabled'}>${safe(tr('controls.repeat'))}</button><button id="reset" data-testid="bingo-reset" ${purchaseDisabled}>${safe(tr('control.reset'))}</button>${statusCardHtml(session)}${botSummaryHtml(session)}<div id="auto"></div><div id="botPanel">${botPanelCache || loadingBotsHtml()}</div></section>`;
}

// Define placeholderCardHtml so the game stage keeps its footprint before purchase.
function placeholderCardHtml() {
  // Render stable headers for the empty card state.
  const heads = COLUMNS.map(column => `<div class="bingo-head">${safe(column)}</div>`).join('');
  // Render muted placeholder cells while no session is active.
  const cells = Array.from({ length: 25 }, (_, index) => `<div class="bingo-cell ${index === 12 ? 'marked' : ''}"><span class="premium-bingo-cell-value">${index === 12 ? safe(tr('card.free')) : '&nbsp;'}</span>${index === 12 ? '<span class="bingo-daub" aria-hidden="true"></span>' : ''}</div>`).join('');
  // Return the complete placeholder card.
  return `<div class="bingo-card" data-testid="bingo-card">${heads}${cells}</div>`;
}

// Define cardHtml to render the fixed-size Bingo card with daubs and win overlay classes.
function cardHtml(session) {
  // Store the card record selected for the stage.
  const record = stageCardRecord(session);
  // Return a stable placeholder card before purchase.
  if (!record?.card) return placeholderCardHtml();
  // Store called numbers as a set for daub checks.
  const called = new Set(calledNumbers(session));
  // Store winning coordinates for highlight checks.
  const winCoords = winningCoordSet(record, session);
  // Render column headers in B/I/N/G/O order.
  const heads = COLUMNS.map(column => `<div class="bingo-head">${safe(column)}</div>`).join('');
  // Store generated cell markup for every row and column.
  const cells = [];
  // Iterate through the five Bingo card rows.
  for (let row = 0; row < 5; row += 1) {
    // Iterate through each Bingo column for the current row.
    for (const column of COLUMNS) {
      // Store the column index for coordinate comparisons.
      const colIndex = COLUMNS.indexOf(column);
      // Store the raw card value at this row and column.
      const value = record.card[column][row];
      // Store whether the cell has been marked by the free space or a called ball.
      const marked = value === 'FREE' || called.has(value);
      // Store whether this cell belongs to the winning coordinate set.
      const win = winCoords.has(`${row},${colIndex}`);
      // Store whether this cell matches the latest called ball.
      const latest = Number(value) === Number(lastNumber);
      // Store class names without changing the card grid footprint.
      const classes = ['bingo-cell', marked ? 'marked' : '', win ? 'win' : '', latest ? 'latest' : ''].filter(Boolean).join(' ');
      // Append the cell with an overlay daub that does not affect layout.
      cells.push(`<div class="${classes}" data-testid="bingo-cell-${row}-${column}" ${win ? 'data-winning-cell="true"' : ''}><span class="premium-bingo-cell-value">${safe(value === 'FREE' ? tr('card.free') : value)}</span>${marked ? '<span class="bingo-daub" aria-hidden="true"></span>' : ''}</div>`);
    }
  }
  // Return the complete fixed Bingo card grid.
  return `<div class="bingo-card" data-testid="bingo-card">${heads}${cells.join('')}</div>`;
}

// Define stageTitleHtml so the center card label reflects active and completed sessions.
function stageTitleHtml(session) {
  // Store the stage card record to identify human versus bot winner cards.
  const record = stageCardRecord(session);
  // Store the title for the current card state.
  const title = session?.status === 'won' ? tr('stage.winningCard', { player: record?.player_id || session?.winner || 'unknown' }) : tr('stage.humanCard');
  // Return the title row with the current pattern tag.
  return `<div class="premium-bingo-stage-head"><h2 class="premium-bingo-stage-title">${safe(title)}</h2>${renderPremiumTag(patternLabel(session?.pattern || pattern))}</div>`;
}

// Define callBayHtml to render the fixed result and latest-call display.
function callBayHtml(session) {
  // Store the latest visible label from direct call response or session state.
  const visibleLabel = lastLabel || session?.last_ball_label || (latestCalledNumber(session) ? label(latestCalledNumber(session)) : '');
  // Store the call bay state for localized copy.
  const key = callBusy ? 'calling' : (session?.status === 'won' ? 'bingo' : (visibleLabel ? 'latest' : 'ready'));
  // Store the orb text while preserving a stable orb footprint.
  const orb = visibleLabel || (callBusy ? '...' : 'B');
  // Store localized descriptive text for the current call bay state.
  const text = key === 'bingo' ? tr('callBay.bingoText', { winner: session?.winner || tr('drawer.noWin'), payout: formatMoney(session?.payout || 0) }) : tr(`callBay.${key}Text`, { label: visibleLabel || tr('callBay.none') });
  // Return the fixed call/result bay below the card.
  return `<div class="premium-bingo-call-bay fixed-result" data-testid="bingo-call-bay"><div class="premium-bingo-orb ${callBusy ? 'is-calling' : ''}">${safe(orb)}</div><div class="premium-bingo-call-copy" data-game-live-status><strong>${safe(tr(`callBay.${key}Title`))}</strong><p>${safe(text)}</p></div></div>`;
}

// Define stageHtml to render the center premium Bingo card and call bay.
function stageHtml(session) {
  // Return the fixed center stage with the same rows for ready, running, and win states.
  return `<section class="panel game-stage premium-bingo-stage">${stageTitleHtml(session)}<div class="premium-bingo-card-wrap">${cardHtml(session)}</div>${callBayHtml(session)}</section>`;
}

// Define calledBallsHtml to render called balls without resizing the card.
function calledBallsHtml(session) {
  // Store called numbers for this session.
  const called = calledNumbers(session);
  // Return an empty drawer message when no calls have occurred.
  if (!called.length) return `<p class="muted">${safe(tr('drawer.noCalls'))}</p>`;
  // Return each called ball as a compact chip in call order.
  return `<div class="premium-bingo-chip-row called-balls">${called.map(n => `<span class="ball premium-bingo-called-chip" data-testid="bingo-called-ball">${safe(label(n))}</span>`).join('')}</div>`;
}

// Define cardsDrawerHtml to render cards in play and their current mark totals.
function cardsDrawerHtml(session) {
  // Store cards for the selected session.
  const cards = sessionCards(session);
  // Return a stable empty state if no cards exist.
  if (!cards.length) return `<p class="muted">${safe(tr('drawer.noCards'))}</p>`;
  // Render each card row with player, source, marks, and stake/payout context.
  return `<div class="premium-bingo-result-grid" data-testid="bingo-cards-drawer">${cards.map(card => { const active = card.card_id === session?.winning_card_id || card.winner; const result = session?.status === 'won' ? (active ? formatMoney(card.payout || session?.payout || 0) : tr('drawer.noWin')) : tr('drawer.marks', { count: formatNumber(countMarks(card, session)) }); return `<div class="premium-bingo-row ${active ? 'is-active' : ''}"><span><b>${safe(card.player_id)}</b><small>${safe(card.source || 'manual')} | ${safe(patternLabel(session?.pattern || pattern))}</small></span><strong>${safe(result)}</strong></div>`; }).join('')}</div>`;
}

// Define recentSessionsHtml to render the newest completed Bingo sessions.
function recentSessionsHtml() {
  // Store recent sessions in newest-first order.
  const sessions = [...(state?.last_sessions || [])].slice(-8).reverse();
  // Return an empty state when no sessions have finished.
  if (!sessions.length) return `<p class="muted">${safe(tr('drawer.noSessions'))}</p>`;
  // Return compact session history rows for the details drawer.
  return `<div class="premium-bingo-result-grid" data-testid="bingo-recent-sessions">${sessions.map(session => `<div class="premium-bingo-row"><span><b>${safe(patternLabel(session.pattern))}</b><small>${safe(tr('drawer.callsText', { count: formatNumber(calledCount(session)) }))}</small></span><strong>${safe(session.winner || tr('drawer.noWin'))}</strong></div>`).join('')}</div>`;
}

// Define drawerHtml to render the right premium details drawer.
function drawerHtml(session) {
  // Store whether the drawer should lead with results or live calls.
  const title = session?.status === 'won' ? tr('drawer.resultTitle') : tr('drawer.calledTitle');
  // Return the details drawer with fixed internal scroll regions.
  return `<section class="panel details-drawer"><h2>${safe(title)}</h2>${session?.status === 'won' ? `<h3>${safe(tr('drawer.cardsTitle'))}</h3>${cardsDrawerHtml(session)}<h3>${safe(tr('drawer.calledTitle'))}</h3>${calledBallsHtml(session)}` : `${calledBallsHtml(session)}<h3>${safe(tr('drawer.cardsTitle'))}</h3>${cardsDrawerHtml(session)}`}<h3>${safe(tr('drawer.recentTitle'))}</h3><div class="scrollbox">${recentSessionsHtml()}</div></section>`;
}

// Define updateBotPanel to refresh shared bot controller markup after state changes.
async function updateBotPanel() {
  // Load the shared bot controller panel for Bingo.
  botPanelCache = await botPanelHtml('bingo');
  // Find the mounted bot panel target after the latest render.
  const element = root?.querySelector('#botPanel');
  // Replace the loading placeholder only when the module is still mounted.
  if (element) element.innerHTML = botPanelCache;
}

// Define load to initialize Bingo state from the frozen state endpoint.
async function load() {
  // Load the latest Bingo state through the v1 API envelope.
  const data = await api(currentPlayerPath('/api/v1/games/bingo/state'));
  // Store the game state for all render helpers.
  state = data.state;
  // Display the active session or the latest completed session on initial mount.
  displayedSession = state.active_session || latestCompletedSession();
  // Recover a repeatable buy from the newest completed session so repeat survives a reload.
  const recovered = latestCompletedSession();
  // Restore the repeatable amount and pattern only when a completed session records them.
  if (recovered && recovered.amount) lastBet = { amount: recovered.amount, pattern: recovered.pattern || pattern };
  // Store latest number and label for the fixed call bay.
  lastNumber = latestCalledNumber(displayedSession);
  // Store latest label from the displayed session if one exists.
  lastLabel = displayedSession?.last_ball_label || (lastNumber ? label(lastNumber) : '');
  // Render immediately so the shell shows stable Bingo layout before async bot markup arrives.
  render();
  // Refresh bot panel rows after the base layout is mounted.
  await updateBotPanel();
  // Refresh the premium shell wallet after Bingo state loads.
  await refreshBalance();
}

// Define syncPurchaseControls to publish purchase state without remounting shared autoplay.
function syncPurchaseControls() {
  // Stop when Bingo has been unmounted while a request was still resolving.
  if (!root) return;
  // Keep the current Buy control disabled while pending or after a session becomes active.
  const buyButton = root.querySelector('#buy');
  // Apply the authoritative purchase availability to the stable current control.
  if (buyButton) {
    // Keep the submitted action visible as an in-progress localized label.
    buyButton.textContent = purchaseBusy ? `${tr('control.buy')}…` : tr('control.buy');
    // Apply the authoritative purchase availability to the stable current control.
    buyButton.disabled = purchaseBusy || Boolean(state?.active_session) || callBusy;
  }
  // Read the current Call control because a purchase render creates it in a disabled busy state.
  const callButton = root.querySelector('#call');
  // Enable Call only after the purchase has resolved into an active authoritative session.
  if (callButton) callButton.disabled = purchaseBusy || !state?.active_session || callBusy;
  // Lock the submitted amount and pattern until their request is fully applied.
  root.querySelectorAll('#bingoAmount, #bingoPattern').forEach(control => { control.disabled = purchaseBusy; });
  // Prevent a concurrent reset from racing a committed purchase whose response is delayed.
  const resetButton = root.querySelector('#reset');
  // Apply the same purchase boundary to the current reset control.
  if (resetButton) resetButton.disabled = purchaseBusy;
  // Publish the purchase boundary for assistive technology and deterministic browser tests.
  root.querySelector('[data-testid="bingo-control-rail"]')?.setAttribute('aria-busy', purchaseBusy ? 'true' : 'false');
}

// Define repeat to buy one fresh card with the previous amount and pattern.
async function repeat() {
  // Ignore repeat while a purchase is pending, a session is active, calling, or before any prior buy.
  if (purchaseBusy || Boolean(state?.active_session) || callBusy || !lastBet) return;
  // Restore the previous amount into both the module state and the visible input.
  amount = lastBet.amount;
  // Restore the previous pattern into both the module state and the visible select.
  pattern = lastBet.pattern;
  // Reflect the restored amount on the mounted control so buy() re-reads it.
  const amountInput = root?.querySelector('#bingoAmount');
  // Apply the restored amount value when the control is present.
  if (amountInput) amountInput.value = amount;
  // Reflect the restored pattern on the mounted control so buy() re-reads it.
  const patternInput = root?.querySelector('#bingoPattern');
  // Apply the restored pattern value when the control is present.
  if (patternInput) patternInput.value = pattern;
  // Fire the shared purchase path with the restored configuration.
  await buy();
}

// Define buy to purchase one human card and then let compatible bots buy cards.
async function buy() {
  // Ignore duplicate manual clicks or autoplay ticks while one purchase remains unresolved.
  if (purchaseBusy) return;
  // Read the amount from the current input and keep it bounded for the API validator.
  amount = Math.max(1, Number(root.querySelector('#bingoAmount')?.value || amount || 5));
  // Read the pattern from the current select before posting the card purchase.
  pattern = root.querySelector('#bingoPattern')?.value || pattern;
  // Reserve the purchase boundary synchronously before the first request can yield.
  purchaseBusy = true;
  // Disable the stable current controls without recreating autoplay or bot widgets.
  syncPurchaseControls();
  // Start protected purchase work so the busy boundary always recovers.
  try {
    // Purchase the human card through the frozen v1 Bingo API.
    const data = await post('/api/v1/games/bingo/cards', withCurrentPlayer({ amount, pattern }));
    // Remember the committed amount and pattern so the next buy can repeat with one click.
    lastBet = { amount, pattern };
    // Store the immediate state so the human card appears without waiting for bots.
    state = data.state;
    // Store the returned active session for rendering.
    displayedSession = data.session;
    // Clear the latest call label because a new card has no called balls.
    lastLabel = '';
    // Clear latest number so no stale daub is emphasized.
    lastNumber = null;
    // Render the purchased card before bot card updates arrive.
    render();
    // Let eligible bot controllers purchase cards through their public controller endpoint.
    await playBotRound('bingo');
    // Reload state so bot cards appear in the cards-in-play drawer.
    const refreshed = await api(currentPlayerPath('/api/v1/games/bingo/state'));
    // Store the refreshed state after bot controller actions.
    state = refreshed.state;
    // Keep the active session visible after bot cards are attached.
    displayedSession = state.active_session || displayedSession;
    // Render the full session with bot cards and fixed layout.
    render();
    // Refresh the shared bot panel after controller actions.
    await updateBotPanel();
    // Refresh the wallet after human and bot card purchases settle.
    await refreshBalance();
    // Play a short confirmation sound for the purchase action.
    clickSound(500, .05);
  // Surface a failed purchase and let autoplay stop through its existing error path.
  } catch (error) {
    // Show the API failure without changing wallet or game state locally.
    toast(error.message);
    // Re-throw after the visible toast so control-plane callers observe the failure.
    throw error;
  // Always release the purchase boundary after response application and refreshes finish.
  } finally {
    // Mark the purchase as resolved before restoring current control availability.
    purchaseBusy = false;
    // Restore controls in place without remounting the shared autoplay widget.
    syncPurchaseControls();
  }
}

// Define call to perform one atomic Bingo ball call.
async function call(showVoice = true) {
  // Avoid overlapping call actions because each call mutates session state.
  if (callBusy) return;
  // Mark the fixed call bay busy before the API request starts.
  callBusy = true;
  // Render the busy state without changing the card layout.
  render();
  // Start protected logic so API errors show as toasts and preserve state.
  try {
    // Call the frozen v1 endpoint for a single ball.
    const data = await post('/api/v1/games/bingo/call', withCurrentPlayer());
    // Store the returned state, which may clear active_session after a win.
    state = data.state;
    // Retain the returned session so a completed winning card remains visible.
    displayedSession = data.session;
    // Store the latest numeric call for daub emphasis.
    lastNumber = data.called;
    // Store the latest label for the fixed call bay.
    lastLabel = data.label;
    // Stop the control-plane autoplay loop after a winner is settled.
    if (data.session?.status === 'won') stopAutoplay('bingo');
    // Render the new call, daubs, drawer rows, and possible win highlight.
    render();
    // Refresh bot panel rows after call state changes.
    await updateBotPanel();
    // Refresh the wallet after a possible payout credit.
    await refreshBalance();
    // Play a short call sound for manual and autoplay calls.
    clickSound(300, .05);
    // Announce the called ball when this is a user-visible manual call.
    if (showVoice) speak(tr('voice.ball', { label: data.label }), 'bingo');
  // Handle call failures with the shared toast surface.
  } catch (error) {
    // Show the API error without mutating game behavior.
    toast(error.message);
    // Re-throw so autoplay can stop through the shared controller.
    throw error;
  // Always clear the busy flag and restore button state.
  } finally {
    // Clear the busy state after the call request finishes.
    callBusy = false;
    // Render once more so buttons and status text settle.
    render();
  }
}

// Define reset to clear or abandon the current Bingo session through the API.
async function reset() {
  // Capture the authoritative active session before reset can remove it from state. (BINGO-027)
  const active = state?.active_session;
  // Read the number of committed calls that make the reset an abandonment rather than a refund.
  const calls = calledCount(active);
  // Read the human card stake for explicit destructive-action copy.
  const stake = Number(humanCardRecord(active)?.amount || active?.amount || 0);
  // Require explicit confirmation before abandoning a called session and its non-refundable stake. (BINGO-027)
  if (active && calls > 0 && !window.confirm(tr('reset.confirmAbandon', { amount: formatMoney(stake), calls: formatNumber(calls) }))) return;
  // Reset the Bingo table through the frozen v1 endpoint.
  const data = await post('/api/v1/games/bingo/reset', withCurrentPlayer());
  // Store the reset state returned by the API.
  state = data.state;
  // Show the latest completed session if one exists after reset.
  displayedSession = latestCompletedSession();
  // Clear stale latest call text after a reset.
  lastLabel = '';
  // Clear stale latest number after a reset.
  lastNumber = null;
  // Render the reset table state.
  render();
  // Refresh bot panel rows after the reset.
  await updateBotPanel();
  // Refresh the wallet after possible pre-call refunds.
  await refreshBalance();
  // Explain whether reset refunded an uncalled card or abandoned a started session. (BINGO-027)
  // Select the truthful outcome key from server refund evidence and the pre-reset call count.
  const resetKey = (data.refunds || []).length ? 'reset.refunded' : (calls > 0 ? 'reset.abandoned' : 'reset.cleared');
  // Use the failure palette for a knowingly abandoned stake and positive feedback otherwise.
  toast(tr(resetKey, { amount: formatMoney(stake) }), calls === 0 || (data.refunds || []).length > 0);
}

// Define autoTick so autoplay performs one public call per controller tick.
async function autoTick() {
  // Stop doing work once the retained session has already reached a winner.
  if (!state?.active_session && displayedSession?.status === 'won') return;
  // Buy a card when no active Bingo session exists yet.
  if (!state?.active_session) await buy();
  // Call exactly one ball when a session is active so Stop is honored between calls.
  if (state?.active_session) await call(false);
}

// Define wireControls to attach event handlers after each render.
function wireControls() {
  // Keep amount state synchronized when the input changes.
  root.querySelector('#bingoAmount').onchange = event => { amount = Math.max(1, Number(event.target.value || amount || 5)); };
  // Keep pattern state synchronized when the select changes.
  root.querySelector('#bingoPattern').onchange = event => { pattern = event.target.value; };
  // Wire the buy-card command while preventing a handled failure from becoming an unhandled promise.
  root.querySelector('#buy').onclick = () => buy().catch(() => undefined);
  // Wire the one-click repeat that re-buys the previous amount and pattern.
  root.querySelector('#bingoRepeat')?.addEventListener('click', () => repeat().catch(() => undefined));
  // Wire the call command to one public ball call.
  root.querySelector('#call').onclick = () => call(true);
  // Wire reset to the public reset endpoint.
  root.querySelector('#reset').onclick = reset;
  // Render the shared autoplay controller with the Bingo stepwise plan.
  autoBox = renderAutoplay({ id: 'bingo', plan: { type: 'auto_call_stepwise' }, defaultRounds: TOTAL_BALLS, roundsLabel: tr('autoplay.calls'), onTick: autoTick });
  // Mount autoplay inside the reserved control rail panel.
  root.querySelector('#auto').append(autoBox);
}

// Define render to mount the complete premium Bingo view.
function render() {
  // Stop rendering when the module has already been unmounted.
  if (!root) return;
  // Ensure scoped CSS is present before markup is inserted.
  ensureStyles();
  // Store the session selected for display.
  const session = currentSession();
  // Preserve the same control through the full-root rerender. (UX-025)
  const focus = captureGameFocus(root);
  // Render the premium Bingo shell inside the shared #view outlet.
  root.innerHTML = `<div class="premium-bingo" data-testid="premium-bingo">${heroHtml(session)}<div class="game-layout three-col stable-game premium-bingo-grid">${controlsHtml(session)}${stageHtml(session)}${drawerHtml(session)}</div></div>`;
  // Restore the selected pattern after the select is recreated.
  root.querySelector('#bingoPattern').value = pattern;
  // Attach all event handlers and shared widgets for the new DOM.
  wireControls();
  // Restore the prior control without scrolling the fixed game board. (UX-025)
  restoreGameFocus(root, focus);
  // Mirror the call/result copy into the persistent live region. (UX-025)
  syncGameLiveStatus(root);
}

// Export the Bingo game module through the shell's game mount contract.
export const BingoGame = {
  // Provide the route id used by the shell registry.
  id: 'bingo',
  // Provide the human-readable label used by diagnostics.
  label: 'Bingo',
  // Mount the Bingo view into the shared shell outlet.
  async mount(node) {
    // Store the root node for all render and event helpers.
    root = node;
    // Clear any repeatable buy so a new session never inherits another player's configuration.
    lastBet = null;
    // Load the Bingo i18n domain and locale settings before rendering visible text.
    await initI18n({ domains: [I18N_DOMAIN] });
    // Seed the localized bot placeholder before async bot markup is available.
    botPanelCache = loadingBotsHtml();
    // Subscribe to locale changes so card state survives language switches.
    unsubscribeLocale = onLocaleChange(() => render());
    // Load state and render the premium Bingo view.
    await load();
  },
  // Unmount the Bingo view and stop active control-plane widgets.
  unmount() {
    // Stop any active Bingo autoplay session when leaving the route.
    if (autoBox?._stop) autoBox._stop();
    // Remove the locale listener when the route is unmounted.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the locale unsubscribe reference.
    unsubscribeLocale = null;
    // Clear the root so pending async work cannot render into a stale node.
    root = null;
    // Clear the repeatable buy so the next session starts fresh.
    lastBet = null;
  },
};
