// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use the frozen v1 Baccarat API.
import { api, post, del, currentPlayerId, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import required dependency so this module can render safe HTML and refresh the shared wallet.
import { refreshBalance, safe, toast, captureGameFocus, restoreGameFocus, syncGameLiveStatus } from '../core/ui.js';
// Import required dependency so this module can mount the shared autoplay control plane.
import { renderAutoplay } from '../core/autoplay.js';
// Import required dependency so this module can keep voice and click feedback consistent.
import { speak, clickSound } from '../core/voice.js';
// Import required dependency so Baccarat bots stay outside the game module boundary.
import { botPanelHtml, playBotRound } from '../core/bots.js';
// Import required dependency so visible Baccarat-owned strings come from locale resources.
import { formatMoney, formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the i18n domain so every Baccarat resource lookup uses one contract.
const DOMAIN = 'games/baccarat';
// Store chip values so wager controls stay stable across setup, reveal, and result states.
const CHIP_VALUES = [5, 25, 100, 500];
// Store supported wager types so rendering and event binding cannot drift from the v1 API.
const BET_TYPES = ['player', 'banker', 'tie'];
// Store table-zone order so the felt matches the approved Player/Tie/Banker geometry.
const TABLE_BET_TYPES = ['player', 'tie', 'banker'];
// Store suit metadata so mojibake backend card strings can render as clean card symbols.
const SUITS = { '\u2665': { entity: '&hearts;', red: true, key: 'suit.hearts' }, '\u2666': { entity: '&diams;', red: true, key: 'suit.diamonds' }, '\u2663': { entity: '&clubs;', red: false, key: 'suit.clubs' }, '\u2660': { entity: '&spades;', red: false, key: 'suit.spades' } };
// Store the mount node so event handlers can rerender the current game view.
let root = null;
// Store the latest public Baccarat state returned by the frozen API.
let state = null;
// Store the active chip amount for the next manual or repeat wager.
let chip = 25;
// Store the selected standing wager used by Deal and autoplay when no bet is open.
let repeatBet = 'banker';
// Store the shared autoplay widget so unmount can stop outstanding timers.
let autoBox = null;
// Store the last coup shown in the reveal and settlement theater.
let lastCoup = null;
// Store the last settlement payload so result rows can show human net without API changes.
let lastSettlements = [];
// Store the current visual phase so the fixed layout can swap content without moving controls.
let phase = 'setup';
// Store bot panel markup so rerenders do not flash empty bot content.
let botPanelCache = '';
// Serialize every wallet-affecting browser mutation so responses cannot overwrite newer state.
let mutationQueue = Promise.resolve();
// Count queued or active mutations so all related controls share one truthful busy boundary.
let pendingMutationCount = 0;
// Track whether one deal is already queued so rapid clicks cannot schedule another coup.
let dealQueued = false;
// Store the reveal timeout so unmount or another deal can clear pending visual work.
let revealTimer = null;
// Store the locale unsubscribe callback so language switching does not leak listeners.
let unsubscribeLocale = null;

// Define text to read Baccarat-owned localized strings synchronously after mount.
function text(key, params = {}) {
  // Return the translated string from the Baccarat domain.
  return t(key, params, DOMAIN);
}

// Define amountText to format fake-money amounts with the active locale.
function amountText(value) {
  // Return a localized USD display string without changing ledger semantics.
  return formatMoney(value);
}

// Define wholeNumber to format counts with the active locale.
function wholeNumber(value) {
  // Return an integer-style localized number for shoe and coup metrics.
  return formatNumber(value, { maximumFractionDigits: 0 });
}

// Define signedAmount to show settlement net values with an explicit sign.
function signedAmount(value) {
  // Store the normalized number so sign and absolute value are stable.
  const amount = Number(value || 0);
  // Return the signed localized money string for the settlement drawer.
  return `${amount >= 0 ? '+' : '-'}${amountText(Math.abs(amount))}`;
}

// Define betLabel to convert v1 bet ids into localized display labels.
function betLabel(type) {
  // Return the localized wager label or a safe fallback for unexpected data.
  return text(`bet.${type}`) || safe(type);
}

// Define setPlayers to cache the scoreboard payload returned by the API.
function setPlayers(payload) {
  // Update the shared Baccarat player cache only when the response includes players.
  if (payload.players) window._lastBaccaratPlayers = payload.players;
}

// Define currentPlayers to read the cached scoreboard rows.
function currentPlayers() {
  // Return the last player list or an empty list before the first state payload.
  return window._lastBaccaratPlayers || [];
}

// Define humanBets to isolate current-player wagers from bot wagers.
function humanBets(source = []) {
  // Return only active-player bets from the supplied v1 bet collection.
  return (source || []).filter(bet => bet.player_id === currentPlayerId());
}

// Define activeBets to return the bets relevant to the current phase.
function activeBets() {
  // Return locked coup bets during reveal/result and open bets during setup.
  return phase === 'setup' ? humanBets(state?.open_bets || []) : humanBets(lastCoup?.bets || []);
}

// Define betTotal to sum wagers, optionally filtered by bet type.
function betTotal(bets, type = null) {
  // Return the summed amount for matching bet rows.
  return (bets || []).filter(bet => !type || bet.type === type).reduce((total, bet) => total + Number(bet.amount || 0), 0);
}

// Define displayCoup to hide old cards while the next wager setup is active.
function displayCoup() {
  // Return the live theater coup only when setup should not show blank card bays.
  return phase === 'setup' ? null : lastCoup;
}

// Define normalizeCard to repair older mojibake suit strings before rendering.
function normalizeCard(card) {
  // Store the raw card as a string for safe replacement.
  const raw = String(card || '');
  // Return a normalized rank+suit string for card rendering and reveal logs.
  return raw.replace(/\u00e2\u2122\u00a5/g, '\u2665').replace(/\u00e2\u2122\u00a6/g, '\u2666').replace(/\u00e2\u2122\u00a3/g, '\u2663').replace(/\u00e2\u2122[\u00a0 ]/g, '\u2660');
}

// Define cardParts to split a card into rank and suit metadata.
function cardParts(card) {
  // Store the normalized card so rank and suit parsing handles legacy data.
  const normalized = normalizeCard(card);
  // Store the final character as the suit glyph.
  const suit = normalized.slice(-1);
  // Store the leading characters as the rank.
  const rank = normalized.slice(0, -1);
  // Store the suit metadata when the glyph is recognized.
  const suitInfo = SUITS[suit] || { entity: safe(suit), red: false, key: 'suit.unknown' };
  // Return the parsed display fields for cards and logs.
  return { rank, suit, ...suitInfo };
}

// Define cardLabel to render a card as readable text in the reveal log.
function cardLabel(card) {
  // Return a localized placeholder when no card exists.
  if (!card) return text('card.placeholder');
  // Store parsed card fields so the suit name can be localized.
  const parts = cardParts(card);
  // Return the localized rank and suit text for the reveal log.
  return `${safe(parts.rank)} ${text(parts.key)}`;
}

// Define playingCardHtml to render a real card or a reserved card bay.
function playingCardHtml(card, index, side) {
  // Return a stable placeholder bay when the card has not been dealt.
  if (!card) return `<div class="playing-card bac-card placeholder" data-testid="baccarat-${side}-card-empty-${index}" aria-label="${safe(text('card.placeholder'))}"></div>`;
  // Store parsed card fields so color and suit entity stay consistent.
  const parts = cardParts(card);
  // Store the reveal class so animation uses transform and opacity only.
  const revealClass = phase === 'revealing' ? ' revealing' : '';
  // Store the staggered delay style so cards peel in without changing layout.
  const delay = phase === 'revealing' ? ` style="animation-delay:${index * 80}ms"` : '';
  // Return the formatted playing-card element for the table theater.
  return `<div class="playing-card bac-card ${parts.red ? 'red' : ''}${revealClass}" data-testid="baccarat-${side}-card-${index}"${delay}><span>${safe(parts.rank)}</span><span>${parts.entity}</span></div>`;
}

// Define payoutText to render current rules without changing API contracts.
function payoutText(type) {
  // Return the player payout label for even-money Player wagers.
  if (type === 'player') return text('payout.player');
  // Return the tie payout label from current rules when available.
  if (type === 'tie') return text('payout.tie', { payout: wholeNumber(state?.rules?.tie_payout || 8) });
  // Store banker commission so the visible payout matches the existing rule.
  const commission = Number(state?.rules?.banker_commission ?? 0.05);
  // Return the banker payout after commission as an odds label.
  return text('payout.banker', { payout: (1 - commission).toFixed(2) });
}

// Define statusPillsHtml to render the fixed state badges above the table.
function statusPillsHtml() {
  // Store phase-specific labels so the rail mirrors setup, reveal, and result states.
  const keys = phase === 'result' ? ['status.resultWinner', 'status.settlementPosted', 'status.roadUpdated', 'status.nextReady'] : phase === 'revealing' ? ['status.cardsRevealing', 'status.naturalCheck', 'status.tableauPending', 'status.roadPending'] : ['status.puntoBanco', 'status.standingWagers', 'status.burnVisible', 'status.roadReserved'];
  // Return all status cells with stable dimensions.
  return `<div class="bac-status-rail">${keys.map(key => `<span>${safe(text(key, { winner: betLabel(lastCoup?.winner || 'player') }))}</span>`).join('')}</div>`;
}

// Define styleHtml to keep Baccarat-specific production styling inside the owned module file.
function styleHtml() {
  // Return scoped CSS that builds on the premium shell without editing shared styles.
  return `<style data-baccarat-style>.bac-shell{display:grid;grid-template-rows:auto minmax(0,1fr);gap:14px;height:100%;min-height:0}.bac-header{display:grid;grid-template-columns:minmax(260px,1fr) minmax(420px,48%);gap:14px;align-items:end;min-height:90px}.bac-kicker{margin:0 0 5px;color:var(--muted);font-size:13px}.bac-title{margin:0;color:var(--gold);font-family:var(--font-display);font-size:54px;line-height:1}.bac-status-rail{display:grid;grid-template-columns:repeat(4,1fr);overflow:hidden;border:1px solid var(--gold);border-radius:8px;background:rgba(20,10,34,.86)}.bac-status-rail span{display:grid;place-items:center;min-height:62px;padding:0 10px;border-left:1px solid var(--border);color:var(--text);font-weight:900;text-align:center}.bac-status-rail span:first-child{border-left:0}.bac-rail-card{margin:8px 0;padding:10px;border:1px solid var(--border-soft);border-radius:8px;background:rgba(255,255,255,.04)}.bac-rail-card label{font-size:12px;font-weight:900;text-transform:uppercase}.bac-rail-card select{min-height:44px}.bac-chip-row{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:10px}.bac-chip-row .chip{width:54px;height:54px}.bac-repeat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.bac-repeat-grid button{min-height:44px;padding:0 6px}.bac-deal-button{width:100%;min-height:48px;margin-top:8px}#botPanel.bac-rail-card{max-height:58px;overflow:auto}#auto.bac-rail-card{max-height:132px;overflow:auto}.bac-stage-head{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-bottom:10px}.bac-coup-label{color:var(--muted);font-size:12px}.bac-stage-title{margin:2px 0 0;color:var(--text);font-family:var(--font-display);font-size:31px}.bac-stage-badge{min-width:120px;padding:12px;border:1px solid var(--border-soft);border-radius:8px;background:rgba(255,255,255,.08);color:var(--text);font-weight:900;text-align:center}.bac-board{display:grid;grid-template-rows:minmax(160px,auto) minmax(180px,1fr);gap:14px;min-height:470px;padding:24px 30px;border:2px solid var(--gold);border-radius:8px;background:radial-gradient(circle at 50% 62%,rgba(20,10,34,.72),rgba(20,10,34,.96) 52%,rgba(20,10,34,.98));box-shadow:inset 0 0 70px rgba(255,217,120,.05)}.bac-hand-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.bac-hand-panel{min-height:154px;padding:14px;border:1px solid var(--gold);border-radius:8px;background:rgba(20,10,34,.48)}.bac-hand-top{display:flex;justify-content:space-between;gap:8px;color:var(--text);font-weight:900}.bac-card-row{display:flex;gap:12px;align-items:center;min-height:104px;margin-top:12px}.bac-card{width:72px;height:104px;font-size:30px;line-height:1.15}.bac-card span:last-child{font-size:25px}.bac-card.placeholder{border:1px dashed rgba(255,255,255,.14);background:rgba(255,255,255,.04);box-shadow:none}.bac-card.revealing{animation:bacReveal .62s cubic-bezier(.2,.8,.22,1) both}@keyframes bacReveal{from{opacity:.2;transform:translateY(22px) rotate(-7deg)}to{opacity:1;transform:translateY(0) rotate(0)}} @media (prefers-reduced-motion:reduce){.bac-card.revealing{animation:none;transform:none;opacity:1;}}.bac-wager-grid{display:grid;grid-template-columns:1.4fr 1fr 1.4fr;gap:14px;align-items:stretch}.bac-wager-zone{position:relative;display:grid;place-items:center;min-height:180px;border:2px solid rgba(255,255,255,.18);border-radius:8px;color:var(--text);font-family:var(--font-display);font-size:31px;font-weight:900;text-align:center;box-shadow:inset 0 0 34px rgba(255,255,255,.04)}.bac-wager-zone.player{background:linear-gradient(135deg,rgba(14,92,116,.86),rgba(9,60,77,.88))}.bac-wager-zone.tie{background:linear-gradient(135deg,rgba(48,65,101,.86),rgba(35,44,69,.9))}.bac-wager-zone.banker{background:linear-gradient(135deg,rgba(116,55,45,.88),rgba(77,36,31,.9))}.bac-wager-zone.winner{border-color:var(--gold);box-shadow:0 0 0 1px var(--gold),inset 0 0 44px rgba(255,217,120,.16)}.bac-wager-zone.lost{opacity:.48}.bac-zone-chip{position:absolute;top:-14px;right:-10px;display:grid;place-items:center;width:48px;height:48px;border:5px dashed rgba(255,255,255,.82);border-radius:50%;color:#211600;background:radial-gradient(circle,#fff 0 28%,#e4b12f 29% 56%,#9b6800 57%);font-family:var(--font-body);font-size:12px}.bac-drawer-total{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;margin-bottom:8px;padding:11px;border:1px solid var(--gold);border-radius:8px;background:rgba(255,217,120,.07);color:var(--text);font-weight:900}.bac-road-grid{display:grid;grid-template-columns:repeat(6,34px);gap:8px;min-height:118px;padding:11px;border:1px solid var(--border-soft);border-radius:8px;background:rgba(0,0,0,.14)}.bac-road-cell{display:grid;place-items:center;width:34px;height:34px;border:1px dashed rgba(255,255,255,.12);border-radius:50%;color:#fff;font-size:12px;font-weight:1000}.bac-road-cell.player{border:0;background:#1e65b7}.bac-road-cell.banker{border:0;background:#bf2634}.bac-road-cell.tie{border:0;background:#6b3c9c}.bac-road-cell.latest{outline:3px solid var(--gold);outline-offset:2px}.bac-log{display:grid;gap:8px}.bac-log-row{padding:9px 10px;border:1px solid var(--border-soft);border-radius:8px;background:rgba(0,0,0,.14)}.bac-shoe-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.bac-shoe-grid .stat{min-height:52px;margin:0;padding:8px;border-radius:8px}.bac-score{max-height:120px;overflow:auto}.bac-disabled-note{opacity:.64}.bac-drawer-section{margin-top:12px}@media(max-width:1200px){.bac-shell{height:auto}.bac-header{grid-template-columns:1fr}.bac-title{font-size:42px}.bac-status-rail{grid-template-columns:repeat(2,1fr)}.bac-board{min-height:auto;padding:18px}.bac-hand-grid,.bac-wager-grid,.bac-shoe-grid{grid-template-columns:1fr}.bac-wager-zone{min-height:150px}.bac-card{width:64px;height:92px;font-size:25px}.bac-road-grid{grid-template-columns:repeat(6,30px)}.bac-road-cell{width:30px;height:30px}}</style>`;
}

// Define headerHtml to render the Baccarat first-viewport identity and status rail.
function headerHtml() {
  // Return the premium Baccarat header mounted inside the shared shell view.
  return `<div class="bac-header"><div><p class="bac-kicker">${safe(text('kicker'))}</p><h2 class="bac-title">${safe(text('title'))}</h2></div>${statusPillsHtml()}</div>`;
}

// Define mutationsBusy to expose one truthful in-flight state to all Baccarat controls.
function mutationsBusy() {
  // Return true while any queued or active wallet-affecting operation remains unresolved.
  return pendingMutationCount > 0;
}

// Define syncMutationControls to update only stable controls without remounting autoplay.
function syncMutationControls() {
  // Stop when the Baccarat surface is not currently mounted.
  if (!root) return;
  // Read the serialized mutation state once for every stable control update.
  const busy = mutationsBusy();
  // Lock wager, clear, and deal actions during mutations or reveal theater.
  root.querySelectorAll('[data-bet], [data-clear], #deal').forEach(control => { control.disabled = busy || phase === 'revealing'; });
  // Lock configuration controls only while a wallet-affecting mutation is unresolved.
  root.querySelectorAll('[data-chip], #repeatBet').forEach(control => { control.disabled = busy; });
  // Publish the shared busy state on the control rail for assistive technology.
  root.querySelector('[data-testid="baccarat-control-rail"]')?.setAttribute('aria-busy', busy ? 'true' : 'false');
  // Publish the same busy state on the central game stage.
  root.querySelector('[data-testid="baccarat-table"]')?.setAttribute('aria-busy', busy ? 'true' : 'false');
  // Read the stable Deal control so its localized label matches its actual availability.
  const dealButton = root.querySelector('#deal');
  // Update the Deal label without replacing the control or its event handler.
  if (dealButton) dealButton.textContent = busy || phase === 'revealing' ? text('controls.dealLocked') : phase === 'result' ? text('controls.dealNext') : text('controls.deal');
}

// Define enqueueMutation to serialize wager, refund, and deal responses in invocation order.
function enqueueMutation(operation) {
  // Count the operation before synchronizing controls so a second action cannot race it.
  pendingMutationCount += 1;
  // Update stable controls synchronously without recreating the shared autoplay widget.
  syncMutationControls();
  // Start this operation only after every earlier mutation has fully applied its response.
  const scheduled = mutationQueue.then(operation);
  // Keep the private queue usable after an operation rejects while preserving caller errors.
  mutationQueue = scheduled.catch(() => undefined);
  // Return the caller-visible result with guaranteed busy-state cleanup.
  return scheduled.finally(() => {
    // Release exactly this queued mutation from the shared busy count.
    pendingMutationCount = Math.max(0, pendingMutationCount - 1);
    // Restore mounted control availability without replacing autoplay or bot nodes.
    syncMutationControls();
  });
}

// Define chipControlsHtml to render stable chip buttons.
function chipControlsHtml() {
  // Disable chip changes while a wager, clear, or deal mutation is unresolved.
  const disabled = mutationsBusy() ? ' disabled' : '';
  // Return chip buttons using the shared chip visual primitive.
  return `<div class="bac-chip-row">${CHIP_VALUES.map(value => `<button class="chip ${chip === value ? 'active' : ''}" data-chip="${value}" data-testid="baccarat-chip-${value}" aria-label="${safe(text('controls.chip', { amount: amountText(value) }))}"${disabled}>${amountText(value).replace('.00', '')}</button>`).join('')}</div>`;
}

// Define repeatSelectHtml to render the standing wager selector.
function repeatSelectHtml() {
  // Disable standing-wager changes while the current mutation sequence is unresolved.
  const disabled = mutationsBusy() ? ' disabled' : '';
  // Return the repeat bet menu used by Deal and autoplay.
  return `<label>${safe(text('controls.repeatBet'))}<select id="repeatBet" data-testid="baccarat-repeat-bet"${disabled}>${BET_TYPES.map(type => `<option value="${type}" ${repeatBet === type ? 'selected' : ''}>${safe(betLabel(type))}</option>`).join('')}</select></label>`;
}

// Define railHtml to render the fixed left action rail.
function railHtml() {
  // Read the shared mutation boundary once for labels, accessibility, and disabled controls.
  const busy = mutationsBusy();
  // Store the deal button label based on the current visual phase.
  const dealLabel = busy ? text('controls.dealLocked') : phase === 'result' ? text('controls.dealNext') : phase === 'revealing' ? text('controls.dealLocked') : text('controls.deal');
  // Store disabled state so reveal animation cannot start another deal.
  const disabled = phase === 'revealing' || busy ? ' disabled' : '';
  // Return the control rail with chips, bet zones, autoplay, and bots in fixed slots.
  return `<section class="panel control-rail" data-testid="baccarat-control-rail" aria-busy="${busy ? 'true' : 'false'}"><h2 class="game-title">${safe(text('rail.title'))}</h2><h3>${safe(text('rail.chips'))}</h3>${chipControlsHtml()}<div class="bac-rail-card"><h3>${safe(text('controls.wagerZones'))}</h3><div class="bac-repeat-grid">${BET_TYPES.map(type => `<button data-bet="${type}" data-testid="baccarat-${type}" class="gold"${disabled}>${safe(betLabel(type))}</button>`).join('')}</div>${repeatSelectHtml()}<button id="deal" data-testid="baccarat-deal" class="primary bac-deal-button"${disabled}>${safe(dealLabel)}</button></div><div class="bac-rail-card" id="botPanel">${botPanelCache || `<p class="muted">${safe(text('bot.loading'))}</p>`}</div><div class="bac-rail-card" id="auto"></div></section>`;
}

// Define handPanelHtml to render one side of the Baccarat tableau.
function handPanelHtml(side) {
  // Store the current visible coup so setup can reserve empty card bays.
  const coup = displayCoup();
  // Store dealt cards for the requested side.
  const cards = coup?.[`${side}_cards`] || [];
  // Store total text for dealt cards or pending setup wagers.
  const total = coup ? text('stage.total', { total: wholeNumber(coup[`${side}_total`] || 0) }) : text('stage.totalPending');
  // Store card row HTML with three reserved card bays.
  const cardRow = [0, 1, 2].map(index => playingCardHtml(cards[index], index, side)).join('');
  // Return the hand panel with fixed total and card regions.
  return `<div class="bac-hand-panel" data-testid="baccarat-${side}-hand"><div class="bac-hand-top"><span>${safe(betLabel(side))}</span><span>${safe(total)}</span></div><div class="bac-card-row" data-testid="baccarat-${side}-cards">${cardRow}</div></div>`;
}

// Define wagerZoneTitle to render result-sensitive wager zone text.
function wagerZoneTitle(type) {
  // Return a winning zone label when the last coup matches this wager.
  if (phase === 'result' && lastCoup?.winner === type) return text('zone.pays', { bet: betLabel(type), payout: payoutText(type) });
  // Return a dimmed losing zone label after a nonmatching result.
  if (phase === 'result' && lastCoup) return text('zone.lost', { bet: betLabel(type) });
  // Return the normal wager label and payout before settlement.
  return `${betLabel(type)} ${payoutText(type)}`;
}

// Define wagerZoneHtml to render one large stable betting zone.
function wagerZoneHtml(type) {
  // Store the phase-relevant bets so chip badges match setup or locked coup state.
  const bets = activeBets();
  // Store the amount on this zone for the chip badge.
  const total = betTotal(bets, type);
  // Store the winner class after settlement.
  const winnerClass = phase === 'result' && lastCoup?.winner === type ? ' winner' : '';
  // Store the lost class after settlement.
  const lostClass = phase === 'result' && lastCoup && lastCoup.winner !== type ? ' lost' : '';
  // Store disabled state while reveal is running.
  const disabled = phase === 'revealing' || mutationsBusy() ? ' disabled' : '';
  // Return the large wager zone with a stable chip badge slot.
  return `<button class="bac-wager-zone ${type}${winnerClass}${lostClass}" data-bet="${type}" data-testid="baccarat-zone-${type}"${disabled}><span>${safe(wagerZoneTitle(type))}</span>${total > 0 ? `<span class="bac-zone-chip" data-testid="baccarat-zone-amount-${type}">${amountText(total).replace('.00', '')}</span>` : ''}</button>`;
}

// Define stageTitle to render the current central theater headline.
function stageTitle() {
  // Return a localized winner headline after settlement.
  if (phase === 'result' && lastCoup) return text('stage.winnerTitle', { winner: betLabel(lastCoup.winner) });
  // Return the reveal headline during the card theater phase.
  if (phase === 'revealing') return text('stage.reveal');
  // Return the setup headline before a coup is dealt.
  return text('stage.placeWagers');
}

// Define coupLabel to render either the actual round id or the next coup number.
function coupLabel() {
  // Return the actual v1 round id when a coup is visible.
  if (displayCoup()?.round_id) return text('stage.coupId', { id: displayCoup().round_id });
  // Store the next coup number from public state.
  const next = Number(state?.coup_number || 0) + 1;
  // Return a stable next-coup label during setup.
  return text('stage.coupNumber', { number: wholeNumber(next) });
}

// Define stageBadge to render shoe or result summary in the fixed header slot.
function stageBadge() {
  // Return human net after settlement when available.
  if (phase === 'result') return text('stage.net', { amount: signedAmount(humanNet()) });
  // Return draw status while the reveal theater is active.
  if (phase === 'revealing') return lastCoup?.natural ? text('stage.natural') : text('stage.tableauPending');
  // Return the active deck count during wager setup.
  return text('stage.deckShoe', { decks: wholeNumber(state?.rules?.decks || 8) });
}

// Define boardHtml to render the fixed center table.
function boardHtml() {
  // Return the card theater and wager zones without changing their layout between phases.
  return `<section class="panel game-stage" data-testid="baccarat-table" aria-busy="${mutationsBusy() ? 'true' : 'false'}"><div class="bac-stage-head"><div><div class="bac-coup-label">${safe(coupLabel())}</div><h2 class="bac-stage-title" data-game-live-status>${safe(stageTitle())} ${safe(stageBadge())}</h2></div><div class="bac-stage-badge">${safe(stageBadge())}</div></div><div class="bac-board" data-testid="${phase === 'revealing' ? 'baccarat-card-reveal' : phase === 'result' ? 'baccarat-result' : 'baccarat-wager-setup'}"><div class="bac-hand-grid">${handPanelHtml('player')}${handPanelHtml('banker')}</div><div class="bac-wager-grid">${TABLE_BET_TYPES.map(type => wagerZoneHtml(type)).join('')}</div></div></section>`;
}

// Define betRowsHtml to render wager rows in the drawer.
function betRowsHtml(bets, locked = false) {
  // Return an empty state when there are no human wagers for this phase.
  if (!bets.length) return `<p class="muted">${safe(text('bets.empty'))}</p>`;
  // Return each wager with cancel controls only while bets remain open.
  return bets.map(bet => `<div class="bet-item"><span>${safe(betLabel(bet.type))}</span><b class="money">${amountText(bet.amount)}</b>${locked ? `<span class="badge">${safe(text('bets.locked'))}</span>` : `<button class="danger" data-clear="${safe(bet.bet_id)}" aria-label="${safe(text('controls.clearBet', { bet: betLabel(bet.type) }))}"${mutationsBusy() ? ' disabled' : ''}>&times;</button>`}</div>`).join('');
}

// Define revealEntries to render the existing dealt cards as a reveal log.
function revealEntries() {
  // Store the current coup so missing cards produce an empty log.
  const coup = lastCoup;
  // Return no entries when there is no coup yet.
  if (!coup) return [];
  // Store entries in the actual initial deal order.
  const entries = [];
  // Add the first player card when present.
  if (coup.player_cards?.[0]) entries.push(text('log.card', { side: betLabel('player'), card: cardLabel(coup.player_cards[0]) }));
  // Add the first banker card when present.
  if (coup.banker_cards?.[0]) entries.push(text('log.card', { side: betLabel('banker'), card: cardLabel(coup.banker_cards[0]) }));
  // Add the second player card when present.
  if (coup.player_cards?.[1]) entries.push(text('log.card', { side: betLabel('player'), card: cardLabel(coup.player_cards[1]) }));
  // Add the second banker card when present.
  if (coup.banker_cards?.[1]) entries.push(text('log.card', { side: betLabel('banker'), card: cardLabel(coup.banker_cards[1]) }));
  // Add the player third card when present.
  if (coup.player_cards?.[2]) entries.push(text('log.thirdCard', { side: betLabel('player'), card: cardLabel(coup.player_cards[2]) }));
  // Add the banker third card when present.
  if (coup.banker_cards?.[2]) entries.push(text('log.thirdCard', { side: betLabel('banker'), card: cardLabel(coup.banker_cards[2]) }));
  // Return the ordered reveal log entries.
  return entries;
}

// Define revealLogHtml to render the drawer reveal log.
function revealLogHtml() {
  // Store reveal entries for compact rendering.
  const entries = revealEntries();
  // Return the reveal log region with stable row heights.
  return `<div class="bac-drawer-section"><h3>${safe(text('drawer.reveal'))}</h3><div class="bac-log">${entries.map(entry => `<div class="bac-log-row">${safe(entry)}</div>`).join('') || `<p class="muted">${safe(text('log.pending'))}</p>`}</div></div>`;
}

// Define outcomeLabel to localize settlement outcomes.
function outcomeLabel(outcome) {
  // Return a localized settlement outcome label.
  return text(`outcome.${outcome || 'pending'}`);
}

// Define humanSettlementRows to read settlement rows for the human player.
function humanSettlementRows() {
  // Return only settlements attached to the human player.
  return (lastSettlements || []).filter(row => row.bet?.player_id === currentPlayerId());
}

// Define humanNet to calculate displayed settlement net from the existing payload.
function humanNet() {
  // Return the sum of credits minus original debited wager amounts.
  return humanSettlementRows().reduce((total, row) => total + Number(row.settlement?.credit || 0) - Number(row.bet?.amount || 0), 0);
}

// Define settlementRowsHtml to render the result drawer.
function settlementRowsHtml() {
  // Store human settlement rows so the drawer ignores bot outcomes.
  const rows = humanSettlementRows();
  // Return a fallback when the visible coup came from history without settlement payload.
  if (!rows.length) return `<p class="muted">${safe(text('settlement.empty'))}</p>`;
  // Return settlement rows with outcome and net values.
  return rows.map(row => { const net = Number(row.settlement?.credit || 0) - Number(row.bet?.amount || 0); return `<div class="bet-item"><span>${safe(betLabel(row.bet.type))} ${amountText(row.bet.amount)}</span><b>${safe(outcomeLabel(row.settlement?.outcome))}</b><span class="money">${signedAmount(net)}</span></div>`; }).join('');
}

// Define shoeHtml to render shoe, burn, and cut-card details.
function shoeHtml() {
  // Store burn information from public state or the visible coup.
  const burn = state?.burn || lastCoup?.burn || {};
  // Store the nominal full shoe so a fresh, not-yet-built (lazily dealt) shoe reads its true capacity instead of 0. (issue #249)
  const fullShoe = (state?.rules?.decks || 8) * 52;
  // Store remaining card count from the visible coup, the live state, or the full fresh shoe before the first deal.
  const remaining = displayCoup()?.shoe_remaining ?? (state?.shoe_count || fullShoe);
  // Store cut threshold from rules when available.
  const cut = state?.rules?.cut_cards_remaining || 14;
  // Return the shoe summary with no hidden gameplay behavior.
  return `<div class="bac-drawer-section" data-testid="baccarat-shoe-summary"><h3>${safe(text('drawer.shoe'))}</h3><div class="bac-shoe-grid"><div class="stat"><span>${safe(text('shoe.id'))}</span><br><b>${safe(state?.shoe_id || lastCoup?.shoe_id || text('shoe.new'))}</b></div><div class="stat"><span>${safe(text('shoe.burn'))}</span><br><b>${safe(burn.first_card ? cardLabel(burn.first_card) : text('shoe.pending'))}</b> · ${safe(text('shoe.burnCount', { count: wholeNumber(burn.burn_count || 0) }))}</div><div class="stat"><span>${safe(text('shoe.remaining'))}</span><br><b>${safe(text('shoe.cards', { count: wholeNumber(remaining) }))}</b></div><div class="stat"><span>${safe(text('shoe.cutCard'))}</span><br><b>${safe(text('shoe.cutSafe', { count: wholeNumber(cut) }))}</b></div></div></div>`;
}

// Define roadCellHtml to render one bead-road cell.
function roadCellHtml(coup, index, latestIndex) {
  // Return an empty reserved cell when no coup exists for this slot.
  if (!coup) return '<span class="bac-road-cell empty" aria-hidden="true"></span>';
  // Store the winner id for class and label generation.
  const winner = coup.winner || 'tie';
  // Store the localized first-letter bead label.
  const label = text(`road.${winner}`);
  // Store a latest marker when this cell is the newest coup.
  const latest = index === latestIndex ? ' latest' : '';
  // Return the bead-road cell.
  return `<span class="bac-road-cell ${safe(winner)}${latest}" title="${safe(betLabel(winner))}">${safe(label)}</span>`;
}

// Define roadHtml to render the reserved road-history grid.
function roadHtml() {
  // Store the latest coups shown in the right drawer.
  const coups = (state?.last_coups || []).slice(-24);
  // Store padded road cells so the drawer dimensions do not change with history length.
  const cells = Array.from({ length: 24 }, (_, index) => roadCellHtml(coups[index], index, coups.length - 1)).join('');
  // Return the road history region.
  return `<div class="bac-drawer-section"><h3>${safe(text('drawer.road'))}</h3><div class="bac-road-grid" data-testid="baccarat-road-history">${cells}</div></div>`;
}

// Define scoreboardHtml to render cached player balances in the drawer.
function scoreboardHtml() {
  // Store player rows for compact scoreboard rendering.
  const rows = currentPlayers().map(player => `<tr><td>${safe(player.display_name)}</td><td>${amountText(player.balance)}</td></tr>`).join('');
  // Return the scoreboard table with a fixed scroll area.
  return `<div class="bac-drawer-section bac-score"><h3>${safe(text('drawer.scoreboard'))}</h3><table class="mini-table"><tr><th>${safe(text('score.player'))}</th><th>${safe(text('score.balance'))}</th></tr>${rows}</table></div>`;
}

// Define drawerHtml to render phase-specific right drawer content.
function drawerHtml() {
  // Store phase-relevant bets for the drawer.
  const bets = activeBets();
  // Store the drawer title based on current phase.
  const title = phase === 'result' ? text('drawer.settlement') : text('drawer.openBets');
  // Store the top total label for open or locked wagers.
  const totalLabel = phase === 'setup' ? text('bets.total') : phase === 'result' ? text('settlement.humanNet') : text('bets.lockedTotal');
  // Store the total amount shown in the highlighted drawer row.
  const totalValue = phase === 'result' ? signedAmount(humanNet()) : amountText(betTotal(bets));
  // Store the primary content for setup/reveal/result.
  const primary = phase === 'result' ? settlementRowsHtml() : betRowsHtml(bets, phase !== 'setup');
  // Return the full right drawer with shoe and road always mounted.
  return `<section class="panel details-drawer"><h2>${safe(title)}</h2><div class="bac-drawer-total"><span>${safe(totalLabel)}</span><b>${safe(totalValue)}</b></div><div class="bet-list stable-list">${primary}</div>${phase === 'revealing' ? revealLogHtml() : ''}${shoeHtml()}${roadHtml()}${scoreboardHtml()}</section>`;
}

// Define render to replace the Baccarat view with the current premium phase.
function render() {
  // Stop rendering if the game has been unmounted.
  if (!root) return;
  // Preserve the focused Baccarat control through the full-root render. (UX-025)
  const focus = captureGameFocus(root);
  // Replace the view with scoped styling and the fixed premium Baccarat shell.
  root.innerHTML = `${styleHtml()}<div class="bac-shell">${headerHtml()}<div class="game-layout three-col stable-game">${railHtml()}${boardHtml()}${drawerHtml()}</div></div>`;
  // Wire the new DOM controls after the HTML replacement.
  bindEvents();
  // Recreate the shared autoplay widget in its reserved rail slot.
  autoBox = renderAutoplay({ id: 'baccarat', plan: { type: 'repeat_standing_bet' }, onTick: async () => deal(false) });
  // Append autoplay controls into the rail after the shared widget is created.
  root.querySelector('#auto')?.append(autoBox);
  // Restore focus and announce the current coup/result status. (UX-025)
  restoreGameFocus(root, focus); syncGameLiveStatus(root);
}

// Define updateBotPanel to refresh bot rows without moving the reserved panel.
async function updateBotPanel() {
  // Stop if the game has been unmounted.
  if (!root) return;
  // Load bot panel markup through the public bot controller helper.
  botPanelCache = await botPanelHtml('baccarat');
  // Store the current bot panel node after async work completes.
  const panel = root?.querySelector('#botPanel');
  // Update the panel only if the view is still mounted.
  if (panel) panel.innerHTML = botPanelCache;
}

// Define placeBetNow to add one v1 Baccarat wager inside the serialized mutation boundary.
async function placeBetNow(type, { rerender = true } = {}) {
  // Store the repeat bet so Deal and autoplay reuse the latest intentional wager.
  repeatBet = type;
  // Post the bet through the existing v1 endpoint.
  const payload = await post('/api/v1/games/baccarat/bets', withCurrentPlayer({ amount: chip, bet_type: type }));
  // Store the updated public state returned by the API.
  state = payload.state;
  // Cache player balances for the drawer scoreboard.
  setPlayers(payload);
  // Return to wager setup so new bets do not display old cards.
  phase = 'setup';
  // Clear settlement rows because the next coup is now being built.
  lastSettlements = [];
  // Rerender the view for user-initiated bets.
  if (rerender) render();
  // Refresh bot rows after the wager changes.
  if (rerender) await updateBotPanel();
  // Refresh the shared wallet because bet placement debits immediately.
  await refreshBalance();
  // Play a short chip sound for user feedback.
  clickSound(520, .05);
}

// Define placeBet to queue a manual wager behind any earlier wallet-affecting operation.
function placeBet(type, options = {}) {
  // Serialize the real request and its state application so later Deal logic sees the result.
  return enqueueMutation(() => placeBetNow(type, options));
}

// Define clearBetNow to refund one open wager inside the serialized mutation boundary.
async function clearBetNow(id) {
  // Delete the open bet through the existing v1 endpoint.
  const payload = await del(`/api/v1/games/baccarat/bets/${id}`, withCurrentPlayer());
  // Store the updated public state returned by the API.
  state = payload.state;
  // Cache player balances for the drawer scoreboard.
  setPlayers(payload);
  // Keep the table in setup because only open wagers can be cleared.
  phase = 'setup';
  // Rerender the wager setup.
  render();
  // Refresh bot rows after the refund changes visible balances.
  await updateBotPanel();
  // Refresh the shared wallet because cancellation credits immediately.
  await refreshBalance();
}

// Define clearBet to queue a refund behind any earlier wager or deal mutation.
function clearBet(id) {
  // Serialize the refund request so its response cannot resurrect superseded state.
  return enqueueMutation(() => clearBetNow(id));
}

// Define finishRevealLater to transition from reveal theater to result state.
function finishRevealLater(show) {
  // Clear any previous reveal timer before starting a new one.
  clearTimeout(revealTimer);
  // Store the timer that switches the stable table from reveal to result.
  revealTimer = setTimeout(() => {
    // Keep the callback inert if the view was unmounted.
    if (!root) return;
    // Switch the visual phase to result after cards have peeled in.
    phase = 'result';
    // Rerender the settlement and updated road drawer.
    render();
    // Restore cached bot panel content in the new render tree.
    updateBotPanel();
    // Publish the settled wallet only after the cards and result are visible. (LEDGER-031, issue #601)
    refreshBalance().catch(() => {});
  }, show ? 1050 : 280); // Use a shorter reveal delay during autoplay ticks.
}

// Define dealNow to run one Baccarat coup after every earlier mutation has applied.
async function dealNow(show = true) {
  // Start protected logic so the button recovers after API errors.
  try {
    // Place the selected standing wager when the human has no open bet.
    if (humanBets(state?.open_bets || []).length === 0) await placeBetNow(repeatBet, { rerender: false });
    // Let eligible bot controllers act through their public control plane.
    await playBotRound('baccarat');
    // Deal the coup through the frozen v1 Baccarat endpoint.
    const payload = await post('/api/v1/games/baccarat/deal', withCurrentPlayer());
    // Store the updated public state returned by the API.
    state = payload.state;
    // Cache player balances for the drawer scoreboard.
    setPlayers(payload);
    // Store the coup for card theater and result display.
    lastCoup = payload.coup;
    // Store settlements so result rows can show human net.
    lastSettlements = payload.settlements || [];
    // Switch to reveal phase before the result drawer appears.
    phase = 'revealing';
    // Render the card reveal theater.
    render();
    // Refresh bot rows after bot and human actions settle.
    await updateBotPanel();
    // Play a reveal sound for manual deals.
    clickSound(760, .08);
    // Speak the result for manual deals only.
    if (show) speak(text('speech.winner', { winner: betLabel(payload.coup.winner) }), 'baccarat');
    // Schedule the result phase after the card reveal animation.
    finishRevealLater(show);
  // Handle failed wagers or deals by showing the shared toast.
  } catch (error) {
    // Display the API error while preserving the mounted Baccarat view.
    toast(error.message || text('errors.dealFailed'));
  }
}

// Define deal to queue one coup and reject duplicate scheduling until it finishes.
function deal(show = true) {
  // Ignore a second Deal or autoplay tick while the first coup is queued or active.
  if (dealQueued) return Promise.resolve();
  // Reserve the deal slot before enqueueing so rapid invocations cannot append another coup.
  dealQueued = true;
  // Serialize Deal behind pending manual wagers, then always release its duplicate guard.
  return enqueueMutation(() => dealNow(show)).finally(() => {
    // Allow the next coup only after this queued deal and its response have completed.
    dealQueued = false;
  });
}

// Define bindEvents to attach handlers after every render.
function bindEvents() {
  // Attach chip selection handlers.
  root.querySelectorAll('[data-chip]').forEach(button => {
    // Update the active chip and rerender stable controls.
    button.onclick = () => { chip = Number(button.dataset.chip); render(); updateBotPanel(); };
  });
  // Attach bet placement handlers to rail buttons and large table zones.
  root.querySelectorAll('[data-bet]').forEach(button => {
    // Place the selected bet unless the reveal phase has disabled the button.
    button.onclick = () => placeBet(button.dataset.bet).catch(error => toast(error.message));
  });
  // Attach clear handlers for open human wagers.
  root.querySelectorAll('[data-clear]').forEach(button => {
    // Clear the selected bet through the public endpoint.
    button.onclick = () => clearBet(button.dataset.clear).catch(error => toast(error.message));
  });
  // Attach deal handler to the fixed rail button.
  root.querySelector('#deal').onclick = () => deal(true);
  // Attach repeat wager selection handler.
  root.querySelector('#repeatBet').onchange = event => { repeatBet = event.target.value; };
}

// Export this symbol so the shared shell can mount Baccarat through the module contract.
export const BaccaratGame = {
  // Expose the game id used by the shared shell.
  id: 'baccarat',
  // Expose the localized-capable label fallback used by old callers.
  label: 'Baccarat',
  // Define mount to initialize i18n, load state, and render the premium table.
  async mount(node) {
    // Store the mount node for subsequent renders.
    root = node;
    // Load Baccarat strings before any visible text renders.
    await loadI18nDomain(DOMAIN);
    // Subscribe to locale changes so text refreshes without remounting gameplay state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Load public Baccarat state through the frozen v1 endpoint.
    const payload = await api(currentPlayerPath('/api/v1/games/baccarat/state'));
    // Store the public state for rendering.
    state = payload.state;
    // Cache player balances for the drawer scoreboard.
    setPlayers(payload);
    // Keep the initial view in setup while still showing road history in the drawer.
    phase = 'setup';
    // Clear previous theater-only payloads on fresh mount.
    lastSettlements = [];
    // Render the premium Baccarat table.
    render();
    // Refresh bot rows after the DOM exists.
    await updateBotPanel();
    // Refresh the shared wallet in the premium shell.
    await refreshBalance();
  },
  // Define unmount to stop timers, autoplay, and locale subscriptions.
  unmount() {
    // Stop pending reveal timers when leaving Baccarat.
    clearTimeout(revealTimer);
    // Stop shared autoplay if it is active.
    if (autoBox?._stop) autoBox._stop();
    // Unsubscribe from locale changes when the module is no longer mounted.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the locale unsubscribe callback.
    unsubscribeLocale = null;
    // Clear the mount node so async callbacks become inert.
    root = null;
  }
};
