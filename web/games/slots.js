// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use the frozen Slots API envelope.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import required dependency so this module can show shared shell feedback and escape API text.
import { toast, refreshBalance, safe } from '../core/ui.js';
// Import required dependency so Slots autoplay remains a control-plane feature.
import { renderAutoplay } from '../core/autoplay.js';
// Import required dependency so this module can expose true bot capability state.
import { eligibleBots } from '../core/bots.js';
// Import required dependency so visible Slots copy comes from locale resources.
import { initI18n, loadI18nDomain, t, formatMoney, formatNumber, onLocaleChange } from '../core/i18n.js';
// Import required dependency so existing Slots sound behavior is preserved.
import { speak, clickSound, reelSound } from '../core/voice.js';
// Import shared motion helpers so reel timers honor reduced motion and route-teardown cleanup. (MOTION-001, MOTION-002)
import { prefersReducedMotion, createMotionTimerScope } from '../core/motion.js';
// Import the seeded generator so decorative reel filler stays deterministic per spin.
import { createSeededRandom } from '../core/dice.js';

// Store DOMAIN so all localized Slots strings resolve through one resource namespace.
const DOMAIN = 'games/slots';
// Store PAYLINE_OPTIONS so the UI exposes exactly the engine-supported line counts.
const PAYLINE_OPTIONS = [1, 3, 5, 9, 20];
// Preserve the frozen v1 two-decimal minimum so browser and public API accept the same stake domain.
const MIN_LINE_BET = 0.01;
// Preserve the frozen v1 maximum so the visible control cannot advertise values the API rejects.
const MAX_LINE_BET = 1000000;
// Store PAYLINE_DASHES so simultaneous paths remain distinguishable without relying on color alone.
const PAYLINE_DASHES = ['none', '8 3', '2 3', '10 3 2 3', '1 3'];
// Store DEFAULT_GRID so the cabinet remains populated before the first API result.
const DEFAULT_GRID = [['BELL', 'CHERRY', 'SEVEN', 'BAR', 'WILD'], ['BAR', 'WILD', 'CHERRY', 'BELL', 'SEVEN'], ['LEMON', 'BAR', 'SCATTER', 'CHERRY', 'BELL']];
// Store SYMBOL_POOL echoing the engine's 14-stop strip distribution so decorative filler reads authentic.
const SYMBOL_POOL = ['CHERRY', 'LEMON', 'BAR', 'CHERRY', 'BELL', 'LEMON', 'WILD', 'BAR', 'CHERRY', 'SEVEN', 'LEMON', 'SCATTER', 'BELL', 'BAR'];
// Store the first reel's deceleration budget inside the governed fast stop band. (SLOT-032 vocabulary)
const REEL_BASE_STOP_MS = 1050;
// Store the adjacent-reel stop stagger inside the governed 140-240 ms band.
const REEL_STAGGER_MS = 170;
// Store the bounce-back time each reel takes to recover its landing overshoot.
const REEL_SETTLE_MS = 210;
// Store the extra travel in device pixels a landing reel overshoots before snapping back.
const REEL_OVERSHOOT_PX = 14;
// Store the last-reel tension extension used when early scatters tease the free-spin feature.
const REEL_ANTICIPATION_MS = 900;
// Store the short hold between the final reel stop and the settled reveal render.
const REEL_HOLD_MS = 200;
// Store the bounded non-animated reveal used when the player asks for reduced motion.
const REDUCED_HOLD_MS = 520;
// Store the fast unattended reveal so autoplay keeps its existing cadence.
const AUTOPLAY_HOLD_MS = 180;
// Store the count of decorative filler tiles rendered above the launch window before travel begins.
const REEL_LAUNCH_FILLER = 6;
// Store the base travel rows each landing strip scrolls through before its authoritative rows arrive.
const REEL_TRAVEL_BASE_ROWS = 12;
// Store the per-column travel growth so later reels visibly spin farther than earlier ones.
const REEL_TRAVEL_STEP_ROWS = 4;
// Store root so route lifecycle methods can mount and unmount the Slots view.
let root = null;
// Store state so rendering can reuse the latest Slots state payload.
let state = null;
// Store config so paytable and available line settings stay API-backed.
let config = null;
// Store autoBox so unmount can stop the shared autoplay control safely.
let autoBox = null;
// Store lastSpin so win reveals and result summaries survive rerenders.
let lastSpin = null;
// Store lastBet so one click can repeat the exact line setup of the most recent settled spin.
let lastBet = null;
// Store spinning so the cabinet can show a fixed in-progress state while the API settles.
let spinning = false;
// Store selectedLines so rerenders do not reset the visible line setup.
let selectedLines = 20;
// Store selectedLineBet so rerenders do not reset the visible line-bet setup.
let selectedLineBet = 1;
// Store lineBetFeedbackKey so localized validation feedback survives locale and layout rerenders.
let lineBetFeedbackKey = '';
// Store autoplayPlan by reference so input edits update the plan already owned by the control plane.
const autoplayPlan = { type: 'repeat_current_spin', active_lines: selectedLines, line_bet: selectedLineBet };
// Store botInfo so the panel can truthfully reserve Slots bot capability space.
let botInfo = null;
// Store localeUnsubscribe so the module can detach its i18n listener on route unmount.
let localeUnsubscribe = null;
// Store paylineResizeObserver so responsive, locale, and zoom changes realign every authoritative path.
let paylineResizeObserver = null;
// Store paylineFrame so repeated geometry notifications collapse into one animation-frame update.
let paylineFrame = null;
// Store the route-owned motion timer scope so reel timers cancel on navigation and reload. (MOTION-002)
let motionScope = null;
// Store whether the decorative reel-strip overlay is mounted for the current spin.
let reelMotionActive = false;
// Store a deferred repaint request raised while a reel animation owns the live DOM.
let pendingRender = false;
// Store the round whose settled render is fresh so win choreography plays once and never on restore.
let revealRoundId = null;
// Store a per-mount spin counter that seeds varied decorative launch filler.
let spinSequence = 0;

// Define tx to resolve a localized Slots string with the shared i18n runtime.
function tx(key, params = {}) { return t(key, params, DOMAIN); }
// Define fm to format fake-money values with the current locale.
function fm(value) { return formatMoney(Number(value || 0)); }
// Define fn to format plain numbers with the current locale.
function fn(value) { return formatNumber(Number(value || 0)); }
// Define economics to read the additive server-owned paytable feature configuration.
function economics() { return config?.economics || {}; }
// Define lineBetDomain to prefer authoritative browser bounds while retaining old-server compatibility.
function lineBetDomain() { const rules = economics().line_bet || {}; return { minimum: Number(rules.ui_minimum ?? rules.api_minimum ?? MIN_LINE_BET), maximum: Number(rules.ui_maximum ?? rules.api_maximum ?? MAX_LINE_BET), step: Number(rules.ui_step ?? 0.01) }; }
// Define progressiveQualifier to read the one exact server-owned line/stake requirement.
function progressiveQualifier() { const rules = economics(); return { lines: Number(rules.progressive_qualifying_lines ?? 20), lineBet: Number(rules.progressive_qualifying_line_bet ?? 1) }; }
// Define progressiveSeed to expose the one constant-size fallback meter without stake scaling.
function progressiveSeed() { return Number(economics().progressive_seed ?? 200); }
// Define currentProgressive to show the one retained meter without creating control-derived identities.
function currentProgressive() { return Number(state?.progressive ?? progressiveSeed()); }
// Define progressiveEligible to make free actions and every nonqualifying control setup visibly ineligible.
function progressiveEligible() { const qualifier = progressiveQualifier(); return freeSpinCount() === 0 && selectedLines === qualifier.lines && Number(selectedLineBet) === qualifier.lineBet; }
// Define progressiveCopyParams to keep exact qualifier values consistent across every localized surface.
function progressiveCopyParams() { const qualifier = progressiveQualifier(); return { amount: fm(currentProgressive()), lines: fn(qualifier.lines), lineBet: qualifier.lineBet.toFixed(2) }; }
// Define progressiveStatusText to expose eligibility independently from settled result and history copy.
function progressiveStatusText() { const copy = progressiveCopyParams(); return progressiveEligible() ? tx('feature.progressive', copy) : tx('feature.progressiveIneligible', copy); }
// Define latestStoredSpin to read the most recent persisted spin from game state.
function latestStoredSpin() { return state?.last_spins?.slice(-1)[0] || null; }
// Define currentGrid to keep the visible reel matrix stable across every state.
function currentGrid() { return lastSpin?.grid || latestStoredSpin()?.grid || DEFAULT_GRID; }
// Define freeSpinCount to normalize the persistent free-spin bank for display.
function freeSpinCount() { return Number(state?.free_spins || lastSpin?.free_spins_remaining || 0); }
// Define roundCost to show the exact cost implied by the current visible controls.
function roundCost() { return freeSpinCount() > 0 ? 0 : selectedLines * selectedLineBet; }
// Define syncAutoplayPlan to keep control-plane configuration aligned with visible Slots controls.
function syncAutoplayPlan() { autoplayPlan.active_lines = selectedLines; autoplayPlan.line_bet = selectedLineBet; }
// Define updateRoundCost to refresh the mounted cost without replacing the focused input.
function updateRoundCost() { const output = root?.querySelector('[data-testid="slots-round-cost"]'); if (output) output.textContent = fm(roundCost()); }
// Define updateProgressiveDisplay to change dedicated eligibility text without erasing a settled result.
function updateProgressiveDisplay() { const copy = progressiveCopyParams(); const headline = root?.querySelector('[data-testid="slots-progressive-headline"]'); const status = root?.querySelector('[data-testid="slots-progressive-status"]'); const idleHeadline = !spinning && !lastSpin?.progressive_hit && !(Number(lastSpin?.payout || 0) > 0) && freeSpinCount() === 0; if (idleHeadline && headline) headline.textContent = progressiveEligible() ? tx('cabinet.progressive', copy) : tx('cabinet.progressiveIneligible', copy); if (status) status.textContent = progressiveStatusText(); }
// Define renderLineBetFeedback to expose validation state to sighted and assistive-technology users.
function renderLineBetFeedback(input, invalid) { const feedback = root?.querySelector('[data-testid="slots-line-bet-feedback"]'); input?.setAttribute('aria-invalid', invalid ? 'true' : 'false'); if (feedback) { feedback.textContent = lineBetFeedbackKey ? tx(lineBetFeedbackKey) : ''; feedback.classList.toggle('error', invalid); } }
// Define acceptLineBetInput to reject unsafe spellings immediately and synchronize every consumer.
function acceptLineBetInput(input) { const candidate = Number(input?.value); const domain = lineBetDomain(); const normalized = Number(candidate.toFixed(2)); const invalid = !input || input.value === '' || !Number.isFinite(candidate) || normalized < domain.minimum || normalized > domain.maximum; selectedLineBet = invalid ? domain.minimum : normalized; lineBetFeedbackKey = invalid ? 'errors.lineBetRange' : ''; if (input) input.value = Number(selectedLineBet).toFixed(2); syncAutoplayPlan(); updateRoundCost(); updateProgressiveDisplay(); renderLineBetFeedback(input, invalid); return !invalid; }
// Define lineWins to retain every authoritative payline result instead of hiding later simultaneous wins.
function lineWins() { return (lastSpin?.wins || []).filter(win => Array.isArray(win.line) && win.line.length === 5); }
// Define firstLineWin to retain the existing primary-symbol treatment while the overlay renders every line.
function firstLineWin() { return lineWins()[0] || null; }
// Define scatterWin to find a scatter/free-spin result when present.
function scatterWin() { return (lastSpin?.wins || []).find(win => win.kind === 'scatter') || null; }
// Define activeSymbol to identify the paytable row tied to the latest result.
function activeSymbol() { return firstLineWin()?.symbol || scatterWin()?.symbol || null; }
// Define isBonusContext so the right rail can switch to feature summary without moving the cabinet.
function isBonusContext() { return Boolean(scatterWin() || lastSpin?.free_spin || freeSpinCount() > 0 || lastSpin?.progressive_hit); }
// Define cellWin to highlight any authoritative winning cell without altering reel layout.
function cellWin(row, col) { return Boolean(lineWins().some(win => win.line[col] === row) || (scatterWin() && (lastSpin?.grid || [])[row]?.[col] === 'SCATTER')); }
// Define symbolLabel to map engine symbols to localized visible copy.
function symbolLabel(symbol) { return tx(`symbol.${symbol}`); }
// Define symbolShort to map engine symbols to compact reel text.
function symbolShort(symbol) { return tx(`symbolShort.${symbol}`); }
// Define winHeadline to summarize the current premium cabinet state.
function winHeadline() { if (spinning) return tx('cabinet.evaluating'); if (lastSpin?.progressive_hit) return tx('cabinet.progressiveHit', { amount: fm(lastSpin.progressive_hit) }); if (lastSpin?.payout > 0) return tx('cabinet.payout', { amount: fm(lastSpin.payout) }); if (freeSpinCount() > 0) return tx('cabinet.freeSpins', { count: fn(freeSpinCount()) }); return progressiveEligible() ? tx('cabinet.progressive', progressiveCopyParams()) : tx('cabinet.progressiveIneligible', progressiveCopyParams()); }
// Define spinButtonLabel to keep the primary command specific to the active state.
function spinButtonLabel() { if (spinning) return tx('controls.wait'); if (freeSpinCount() > 0) return tx('controls.useFreeSpin'); if (lastSpin) return tx('controls.spinAgain'); return tx('controls.spin'); }
// Define cabinetNote to explain state without changing the reserved result region height.
function cabinetNote() { if (spinning) return tx('cabinet.noteSpinning'); if (scatterWin()) return tx('cabinet.noteBonus'); if (lastSpin?.payout > 0) return tx('cabinet.noteWin'); return tx('cabinet.noteReady'); }
// Define primaryStatus to fill the control-panel status reservation.
function primaryStatus() { if (spinning) return tx('status.spinning'); if (scatterWin()) return tx('status.bonusReady', { count: fn(freeSpinCount()) }); if (lastSpin?.payout > 0) return tx('status.win'); return tx('status.ready'); }
// Define resultSummary to render a fixed-height summary below the cabinet.
function resultSummary() { if (spinning) return `<b>${safe(tx('result.accepted'))}</b> ${safe(tx('result.acceptedDetail', { cost: fm(roundCost()) }))}`; if (!lastSpin) return `<b>${safe(tx('result.ready'))}</b> ${safe(tx('result.readyDetail'))}`; const wins = (lastSpin.wins || []).map(win => win.kind === 'scatter' ? tx('result.scatterWin', { count: fn(win.scatter_count), amount: fm(win.payout) }) : tx('result.lineWin', { line: fn(Number(win.line_index || 0) + 1), count: fn(win.count), symbol: symbolLabel(win.symbol), amount: fm(win.payout) })); const visibleWins = wins.slice(0, 3).map(item => safe(item)).join('<br>'); const moreWins = wins.length > 3 ? `<br>${safe(tx('result.moreWins', { count: fn(wins.length - 3) }))}` : ''; const detail = wins.length ? `${visibleWins}${moreWins}` : safe(tx('result.noWin')); return `<b>${safe(tx('result.complete'))}</b> ${safe(tx('result.costPayout', { cost: fm(lastSpin.cost), payout: fm(lastSpin.payout) }))}<br>${detail}`; }
// Define styleHtml to scope Slots-only premium styling without touching shared CSS.
function styleHtml() { return `<style>.slots-premium{--slots-gold:var(--gold);--slots-red:#c82032;--slots-ink:var(--bg);gap:14px}.slots-control,.slots-stage,.slots-drawer{border-color:var(--gold);background:linear-gradient(150deg,rgba(20,10,34,.94),rgba(20,10,34,.88))}.slots-title{display:grid;gap:4px;margin-bottom:14px}.slots-title .eyebrow{color:var(--slots-gold);font-weight:900}.slots-title h2{font-size:34px;margin:0}.slots-metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}.slots-metric{min-height:78px;padding:12px;border:1px solid var(--border-soft);border-radius:12px;background:rgba(255,255,255,.04)}.slots-metric span{display:block;color:var(--muted);font-size:12px;font-weight:800}.slots-metric b{display:block;margin-top:6px;color:#fff2c2;font-size:22px}.slots-spin-button{width:100%;min-height:52px;margin-bottom:14px}.slots-repeat{width:100%;min-height:46px;margin-bottom:14px;border:1px solid var(--gold);border-radius:12px;color:var(--gold);background:transparent;font-weight:900}.slots-repeat:disabled{opacity:.5}.slots-plan{display:grid;gap:10px;min-height:186px;padding:12px;border:1px solid var(--gold);border-radius:14px;background:rgba(255,217,120,.06)}.slots-status-row{display:flex;justify-content:space-between;gap:10px;align-items:center}.slots-dot{width:11px;height:11px;border-radius:50%;background:#86f2aa;box-shadow:0 0 16px #86f2aa}.slots-auto-mount .autoplay{margin:0;border-radius:12px;background:rgba(0,0,0,.12)}.slots-stage{display:grid;grid-template-rows:auto minmax(0,1fr) 122px;gap:14px;overflow:hidden}.slots-stage-top{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;min-height:54px;padding:12px 18px;border:1px solid var(--gold);border-radius:14px;background:rgba(255,217,120,.08)}.slots-chip-row{display:flex;gap:10px;flex-wrap:wrap}.slots-chip{min-width:128px;padding:9px 12px;border:1px solid var(--gold);border-radius:12px;background:rgba(0,0,0,.22)}.slots-chip b{display:block;color:#fff2c2}.slots-cabinet{position:relative;display:grid;grid-template-rows:minmax(0,1fr) auto;min-height:550px;padding:28px 40px;border:2px solid var(--gold);border-radius:24px;background:linear-gradient(180deg,rgba(20,10,34,.96),rgba(20,10,34,.96));box-shadow:inset 0 0 0 8px rgba(255,217,120,.08),0 24px 70px rgba(0,0,0,.4)}.slots-reel-window{--slots-cell-h:96px;--slots-cell-gap:10px;position:relative;align-self:center;min-height:340px;padding:18px;border:2px solid var(--gold);border-radius:18px;background:var(--bg);overflow:hidden}.slots-reel-grid{position:relative;display:grid;grid-template-columns:repeat(5,minmax(72px,1fr));grid-template-rows:repeat(3,var(--slots-cell-h));gap:var(--slots-cell-gap);height:100%}.slots-symbol{position:relative;z-index:1;display:grid;place-items:center;min-width:0;border:1px solid rgba(113,77,18,.42);border-radius:12px;color:#2a1300;background:linear-gradient(180deg,#fff9e9,#f1d990);font-family:var(--font-display);font-size:34px;font-weight:1000;line-height:1;text-align:center;box-shadow:inset 0 -8px 18px rgba(113,77,18,.14);transition:box-shadow .2s,transform .2s}.slots-symbol.symbol-SEVEN,.slots-reel-tile.symbol-SEVEN{color:#a70e1d}.slots-symbol.symbol-BELL,.slots-symbol.symbol-BAR,.slots-reel-tile.symbol-BELL,.slots-reel-tile.symbol-BAR{color:#9c6500}.slots-premium .slot-symbol.spinning{animation:none}.slots-symbol.spinning{opacity:.35;filter:saturate(.55)}.slots-symbol.win{outline:3px solid #fff1a5;box-shadow:0 0 0 5px rgba(255,217,120,.24),0 0 28px rgba(255,217,120,.76),inset 0 -8px 18px rgba(113,77,18,.16)}.slots-symbol.win.just-won{animation:slotsWinPop .6s cubic-bezier(.2,.8,.2,1)}.slots-reel-motion{position:absolute;inset:18px;z-index:2;display:grid;grid-template-columns:repeat(5,minmax(72px,1fr));gap:var(--slots-cell-gap);pointer-events:none}.slots-reel{position:relative;overflow:hidden;border-radius:12px}.slots-reel.priming{animation:slotsReelPrime .34s cubic-bezier(.45,0,.55,1) infinite alternate}.slots-reel.anticipating::after{content:"";position:absolute;inset:0;border:2px solid var(--gold);border-radius:12px;animation:slotsAnticipate .5s ease-in-out infinite alternate;pointer-events:none}.slots-reel-strip{position:absolute;left:0;right:0;bottom:0;display:grid;grid-auto-rows:var(--slots-cell-h);gap:var(--slots-cell-gap);will-change:transform}.slots-reel-strip.is-flying{filter:blur(1px)}.slots-reel-tile{display:grid;place-items:center;min-width:0;height:var(--slots-cell-h);border:1px solid rgba(113,77,18,.42);border-radius:12px;color:#2a1300;background:linear-gradient(180deg,#fff9e9,#f1d990);font-family:var(--font-display);font-size:34px;font-weight:1000;line-height:1;text-align:center;box-shadow:inset 0 -8px 18px rgba(113,77,18,.14)}.slots-payline{position:absolute;inset:0;width:100%;height:100%;z-index:3;overflow:visible;pointer-events:none}.slots-payline polyline{opacity:.82;vector-effect:non-scaling-stroke}.slots-payline.just-revealed polyline{animation:slotsLineReveal .55s ease-out backwards}.slots-payline[data-reduced-motion="true"] polyline{animation:none;transition:none}.slots-lever{position:absolute;right:26px;bottom:32px;width:42px;height:128px;border-radius:999px;background:linear-gradient(180deg,#ffd978,#b47a20);box-shadow:0 10px 24px rgba(0,0,0,.38)}.slots-cabinet-footer{display:grid;grid-template-columns:1fr 150px;gap:16px;align-items:center;min-height:82px;padding-right:72px}.slots-state-pill{display:grid;place-items:center;min-height:44px;padding:0 14px;border:1px solid var(--gold);border-radius:12px;color:#fff2c2;font-weight:900;font-size:13px;letter-spacing:.04em;text-transform:uppercase;background:rgba(0,0,0,.22)}.slots-state-pill.win{border-color:var(--slots-gold);color:var(--slots-gold);background:rgba(255,217,120,.14)}.slots-result{min-height:122px;padding:18px;border:1px solid rgba(255,255,255,.12);border-radius:14px;background:rgba(0,0,0,.22);overflow:auto}.slots-drawer{display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;gap:12px}.slots-card-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.slots-card{min-height:76px;padding:11px;border:1px solid rgba(255,255,255,.14);border-radius:12px;background:rgba(255,255,255,.04)}.slots-card.active{border-color:var(--slots-gold);background:rgba(255,217,120,.1)}.slots-card b{display:block;color:var(--slots-gold)}.slots-history{display:grid;gap:8px;min-height:220px;max-height:280px;overflow:auto}.slots-history-row{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;min-height:48px;padding:10px 12px;border:1px solid rgba(255,255,255,.14);border-radius:12px;background:rgba(0,0,0,.17)}.slots-history-row.active{border-color:var(--slots-gold);background:rgba(255,217,120,.1)}.slots-bot-panel{min-height:88px;padding:12px;border:1px solid var(--gold);border-radius:12px;background:rgba(0,0,0,.16)}@keyframes slotsReelPrime{from{transform:translateY(-2px)}to{transform:translateY(2px)}}@keyframes slotsAnticipate{from{opacity:.25}to{opacity:1}}@keyframes slotsWinPop{0%{transform:scale(1)}45%{transform:scale(1.12)}100%{transform:scale(1)}}@keyframes slotsLineReveal{from{opacity:0}to{opacity:.82}}@media(prefers-reduced-motion:reduce){.slots-premium *{animation:none!important;transition:none!important;scroll-behavior:auto!important}.slots-payline polyline{animation:none;transition:none}}@media(max-width:1180px){.slots-premium.three-col{grid-template-columns:1fr;overflow:auto}.slots-stage{min-height:790px}.slots-cabinet{min-height:520px}.slots-reel-window{--slots-cell-h:82px}}@media(max-width:640px){.slots-cabinet{padding:18px 16px}.slots-reel-window{--slots-cell-h:64px;--slots-cell-gap:7px}.slots-reel-grid{grid-template-columns:repeat(5,minmax(48px,1fr))}.slots-reel-motion{grid-template-columns:repeat(5,minmax(48px,1fr))}.slots-symbol{font-size:18px;letter-spacing:-.01em;overflow:hidden}.slots-reel-tile{font-size:18px;letter-spacing:-.01em;overflow:hidden}.slots-stage{min-height:690px}.slots-cabinet-footer{grid-template-columns:1fr;padding-right:0}.slots-lever{display:none}.slots-card-grid,.slots-metric-grid{grid-template-columns:1fr}}</style>`; }
// Define validationStyleHtml to reserve readable inline validation feedback without shifting controls.
function validationStyleHtml() { return `<style>.slots-field-message{display:block;min-height:28px;padding-top:4px;color:var(--muted);font-size:11px;font-weight:800;line-height:1.25}.slots-field-message.error{color:var(--bad)}</style>`; }
// Define paylineOverlayHtml to render every authoritative line with non-color identification and geometry hooks.
function paylineOverlayHtml() {
  // Read all line wins so simultaneous outcomes remain visible and traceable to the backend result.
  const wins = lineWins();
  // Omit the overlay while no line win exists or the committed spin is still moving.
  if (!wins.length || spinning) return '';
  // Build the localized line-number summary used by the SVG's accessible name.
  const lineNumbers = wins.map(win => fn(Number(win.line_index) + 1));
  // Render one independently labelled path per authoritative win with a unique hue, a non-color dash cue, and a staggered reveal delay.
  const paths = wins.map((win, index) => { const lineNumber = Number(win.line_index) + 1; const rows = win.line.map(row => Number(row)); const hue = Math.round((index * 137.508) % 360); const dash = PAYLINE_DASHES[index % PAYLINE_DASHES.length]; return `<g data-line-number="${safe(lineNumber)}" data-line-rows="${safe(rows.join(','))}" aria-label="${safe(tx('payline.pathLabel', { line: fn(lineNumber) }))}"><title>${safe(tx('payline.pathLabel', { line: fn(lineNumber) }))}</title><polyline data-line-number="${safe(lineNumber)}" data-line-rows="${safe(rows.join(','))}" points="0,0 0,0 0,0 0,0 0,0" fill="none" stroke="hsl(${safe(hue)} 92% 72%)" stroke-width="1.8" stroke-dasharray="${safe(dash)}" stroke-linecap="round" stroke-linejoin="round" style="animation-delay:${index * 90}ms"/></g>`; }).join('');
  // Play the staggered line reveal only on the freshly settled round, never on restore or locale repaints.
  const revealClass = lastSpin?.round_id && lastSpin.round_id === revealRoundId ? ' just-revealed' : '';
  // Expose the exact round and payout beside the localized accessible description for outcome-to-overlay auditing.
  return `<svg class="slots-payline${revealClass}" preserveAspectRatio="none" role="img" aria-label="${safe(tx('payline.overlayLabel', { lines: lineNumbers.join(', ') }))}" data-testid="slots-payline" data-round-id="${safe(lastSpin?.round_id || '')}" data-payout="${safe(lastSpin?.payout || 0)}" data-reduced-motion="${window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'true' : 'false'}"><title>${safe(tx('payline.overlayLabel', { lines: lineNumbers.join(', ') }))}</title>${paths}</svg>`;
}
// Define alignPaylineOverlay to map each SVG point to the measured center of its authoritative reel cell.
function alignPaylineOverlay() {
  // Resolve the currently mounted grid and overlay; idle and spinning states intentionally have no overlay.
  const grid = root?.querySelector('[data-testid="slot-grid"]'); const overlay = root?.querySelector('[data-testid="slots-payline"]');
  // Stop safely when a rerender or route transition removed either geometry owner.
  if (!grid || !overlay) return;
  // Size the SVG coordinate system in visual CSS pixels so grid gaps, zoom, and responsive row sizes remain exact.
  const overlayBox = overlay.getBoundingClientRect(); overlay.setAttribute('viewBox', `0 0 ${overlayBox.width} ${overlayBox.height}`);
  // Rebuild every line from the five live cell centers represented by its backend-provided row vector.
  overlay.querySelectorAll('polyline[data-line-rows]').forEach(path => { const rows = String(path.dataset.lineRows || '').split(',').map(Number); const points = rows.map((row, column) => { const cell = grid.querySelector(`[data-testid="slot-cell-${row}-${column}"]`); const box = cell?.getBoundingClientRect(); return box ? `${(box.left + box.width / 2 - overlayBox.left).toFixed(3)},${(box.top + box.height / 2 - overlayBox.top).toFixed(3)}` : '0,0'; }); path.setAttribute('points', points.join(' ')); });
}
// Define schedulePaylineAlignment to collapse resize notifications into one post-layout geometry update.
function schedulePaylineAlignment() { if (paylineFrame !== null) window.cancelAnimationFrame(paylineFrame); paylineFrame = window.requestAnimationFrame(() => { paylineFrame = null; alignPaylineOverlay(); }); }
// Define mountPaylineGeometry to observe the exact grid that owns the current overlay coordinate space.
function mountPaylineGeometry() { if (paylineResizeObserver) paylineResizeObserver.disconnect(); const grid = root?.querySelector('[data-testid="slot-grid"]'); if (!grid || !root?.querySelector('[data-testid="slots-payline"]')) return; paylineResizeObserver = new ResizeObserver(schedulePaylineAlignment); paylineResizeObserver.observe(grid); schedulePaylineAlignment(); }
// Define tileHtml to render one decorative reel-strip tile that mirrors authoritative symbol styling.
function tileHtml(symbol) { return `<div class="slots-reel-tile symbol-${safe(symbol)}">${safe(symbolShort(symbol))}</div>`; }
// Define reelMotionHtml to mount the decorative five-strip overlay only while a full-motion spin runs.
function reelMotionHtml() {
  // Omit the overlay outside a committed full-motion spin so settled geometry checks see only real cells.
  if (!(spinning && reelMotionActive)) return '';
  // Read the last settled grid so each strip launches showing exactly the symbols already on the cabinet.
  const shown = currentGrid();
  // Seed decorative launch filler from the spin counter so repeated renders of one spin stay identical.
  const random = createSeededRandom(`slots-launch-${spinSequence}`);
  // Build one clipped reel window per column with its launch strip anchored to the cabinet floor.
  const reels = Array.from({ length: 5 }, (_, column) => {
    // Compose decorative filler above the launch window so the strip has somewhere to travel from.
    const filler = Array.from({ length: REEL_LAUNCH_FILLER }, () => SYMBOL_POOL[Math.floor(random() * SYMBOL_POOL.length)]);
    // Stack filler above the three currently visible symbols for a seamless launch frame.
    const tiles = [...filler, shown[0][column], shown[1][column], shown[2][column]];
    // Render the clipped reel with its priming shiver while the backend result is still in flight.
    return `<div class="slots-reel priming" data-reel="${column}"><div class="slots-reel-strip">${tiles.map(tileHtml).join('')}</div></div>`;
  }).join('');
  // Return the pointer-transparent overlay aligned to the authoritative reel grid.
  return `<div class="slots-reel-motion" data-testid="slots-reel-motion" aria-hidden="true">${reels}</div>`;
}
// Define reelGridHtml to render exactly five reels by three rows in every state.
function reelGridHtml() { const grid = currentGrid(); return `<div class="slots-reel-window"><div class="slots-reel-grid slot-grid" data-testid="slot-grid">${grid.map((row, r) => row.map((symbol, c) => `<div class="slots-symbol slot-symbol symbol-${safe(symbol)} ${spinning ? 'spinning' : ''} ${cellWin(r, c) && !spinning ? 'win' : ''} ${cellWin(r, c) && !spinning && lastSpin?.round_id === revealRoundId ? 'just-won' : ''}" data-testid="slot-cell-${r}-${c}" style="animation-delay:${c * 70}ms">${safe(symbolShort(symbol))}</div>`).join('')).join('')}${paylineOverlayHtml()}</div>${reelMotionHtml()}</div>`; }
// Define paytableHtml to render the API paytable and highlight the latest winning family.
function paytableHtml() { const active = activeSymbol(); const rules = economics(); const qualifier = progressiveQualifier(); const scatterPays = rules.scatter_pays || { 4: 1, 5: 5 }; const scatterCopy = tx('paytable.scatter', { threshold: fn(rules.free_spin_scatter_threshold ?? 3), four: fn(scatterPays[4] ?? 1), five: fn(scatterPays[5] ?? 5), freeSpins: fn(rules.free_spins_awarded ?? 4) }); const rows = Object.entries(config?.paytable || {}).map(([symbol, table]) => `<div class="slots-card ${active === symbol ? 'active' : ''}" data-testid="slots-pay-${safe(symbol.toLowerCase())}"><b>${safe(symbolLabel(symbol))}</b><span>${Object.entries(table).map(([count, multiplier]) => `${safe(count)}=${safe(multiplier)}x`).join(', ')}</span></div>`).join(''); return `<h3>${safe(tx('paytable.title'))}</h3><div class="slots-card-grid slots-paytable" data-testid="slots-paytable">${rows}<div class="slots-card ${active === 'SCATTER' ? 'active' : ''}" data-testid="slots-pay-scatter"><b>${safe(symbolLabel('SCATTER'))}</b><span>${safe(scatterCopy)}</span></div><div class="slots-card" data-testid="slots-pay-progressive"><b>${safe(tx('paytable.progressiveTitle'))}</b><span>${safe(tx('paytable.progressive', { seed: fm(rules.progressive_seed ?? 200), contribution: fn(Number(rules.progressive_rate ?? .01) * 100), lines: fn(qualifier.lines), lineBet: qualifier.lineBet.toFixed(2) }))}</span></div></div>`; }
// Define featureSummaryHtml to render free-spin and progressive context in the same drawer footprint.
function featureSummaryHtml() { return `<h3>${safe(tx('feature.title'))}</h3><div class="slots-card-grid" data-testid="slots-feature-summary"><div class="slots-card active"><b>${safe(symbolLabel('SCATTER'))}</b><span>${safe(tx('feature.scatter', { count: fn(scatterWin()?.scatter_count || 0) }))}</span></div><div class="slots-card"><b>${safe(tx('feature.freeSpinsTitle'))}</b><span>${safe(tx('feature.freeSpins', { count: fn(freeSpinCount()) }))}</span></div><div class="slots-card"><b>${safe(tx('feature.progressiveTitle'))}</b><span data-testid="slots-progressive-feature-status">${safe(progressiveStatusText())}</span></div><div class="slots-card"><b>${safe(tx('feature.historyTitle'))}</b><span>${safe(tx('feature.history'))}</span></div></div>`; }
// Define recentSpinsHtml to show a fixed recent-spin drawer with an optional in-progress row.
function recentSpinsHtml() { const pending = spinning ? `<div class="slots-history-row active"><span>${safe(tx('history.inProgress'))}</span><b>...</b></div>` : ''; const rows = (state?.last_spins || []).slice(-8).reverse().map((spin, index) => `<div class="slots-history-row ${index === 0 && !spinning ? 'active' : ''}"><span>${safe(tx('history.row', { id: spin.round_id, lines: fn(spin.active_lines) }))}</span><b>${safe(spin.free_spins_awarded ? tx('history.free', { count: fn(spin.free_spins_awarded) }) : fm(spin.payout))}</b></div>`).join(''); return `<h3>${safe(tx('history.title'))}</h3><div class="slots-history" data-testid="slots-recent-spins">${pending}${rows || `<p class="muted">${safe(tx('history.empty'))}</p>`}</div>`; }
// Define botPanelHtml to reserve bot status without enabling unsupported Slots bot actions.
function botPanelHtml() { if (!botInfo) return `<div class="slots-bot-panel" data-testid="slots-bot-panel"><b>${safe(tx('bots.title'))}</b><p class="muted">${safe(tx('bots.loading'))}</p></div>`; if (!botInfo.capabilities?.supports_bots) return `<div class="slots-bot-panel" data-testid="slots-bot-panel"><b>${safe(tx('bots.title'))}</b><p class="muted">${safe(tx('bots.unavailable'))}</p></div>`; const rows = (botInfo.bots || []).map(bot => `<div class="slots-history-row"><span>${safe(bot.display_name || bot.bot_id)}</span><b>${safe(bot.strategy_id || tx('bots.noStrategy'))}</b></div>`).join(''); return `<div class="slots-bot-panel" data-testid="slots-bot-panel"><b>${safe(tx('bots.title'))}</b>${rows || `<p class="muted">${safe(tx('bots.empty'))}</p>`}</div>`; }
// Define controlRailHtml to render controls, status, autoplay, and bot context.
function controlRailHtml() {
  // Build the supported line-count options from the module-owned catalog.
  const lineOptions = PAYLINE_OPTIONS.map(count => `<option value="${count}" ${selectedLines === count ? 'selected' : ''}>${safe(fn(count))}</option>`).join('');
  // Resolve the current localized validation message for the reserved live region.
  const lineBetFeedback = lineBetFeedbackKey ? tx(lineBetFeedbackKey) : '';
  // Disable the one-click repeat while a spin is committed or before any bet has been captured.
  const repeatDisabled = spinning || !lastBet;
  // Read the exact accepted runtime amount range for visible native validation attributes.
  const lineBetRules = lineBetDomain();
  // Render controls with an explicit validation relationship and synchronized round-cost output.
  return `<section class="panel slots-control"><div class="slots-title"><span class="eyebrow">${safe(tx('kicker'))}</span><h2>${safe(tx('title'))}</h2></div><div class="slots-metric-grid"><label class="slots-metric">${safe(tx('controls.paylines'))}<select id="lines" data-testid="slots-lines"${spinning ? ' disabled' : ''}>${lineOptions}</select></label><label class="slots-metric">${safe(tx('controls.lineBet'))}<input id="lineBet" data-testid="slots-line-bet" type="number" min="${safe(lineBetRules.minimum)}" max="${safe(lineBetRules.maximum)}" step="${safe(lineBetRules.step)}" value="${safe(selectedLineBet)}"${spinning ? ' disabled' : ''} aria-invalid="${lineBetFeedbackKey ? 'true' : 'false'}" aria-describedby="slots-line-bet-feedback"><span id="slots-line-bet-feedback" class="slots-field-message ${lineBetFeedbackKey ? 'error' : ''}" role="status" aria-live="polite" data-testid="slots-line-bet-feedback">${safe(lineBetFeedback)}</span></label></div><button id="spin" data-testid="slots-spin" class="primary slots-spin-button" ${spinning ? 'disabled' : ''}>${safe(spinButtonLabel())}</button><button type="button" class="slots-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(tx('controls.repeat'))}</button><div class="slots-plan"><div class="slots-status-row"><span class="slots-dot"></span><b>${safe(primaryStatus())}</b></div><p class="muted">${safe(tx('autoplay.description'))}</p><div id="auto" class="slots-auto-mount"></div></div><div class="slots-metric-grid"><div class="slots-metric"><span>${safe(tx('metrics.roundCost'))}</span><b data-testid="slots-round-cost">${safe(fm(roundCost()))}</b></div><div class="slots-metric"><span>${safe(tx('metrics.freeSpins'))}</span><b>${safe(fn(freeSpinCount()))}</b></div><div class="slots-metric"><span>${safe(tx('feature.progressiveTitle'))}</span><b data-testid="slots-progressive-status">${safe(progressiveStatusText())}</b></div></div>${botPanelHtml()}</section>`;
}
// Define stageHtml to render the fixed cabinet, payline overlay, and result reservation.
function stageHtml() { return `<section class="panel slots-stage"><div class="slots-stage-top"><div><b>${safe(tx('cabinet.name'))}</b><p class="muted">${safe(tx('cabinet.subtitle'))}</p></div><strong data-testid="slots-progressive-headline">${safe(winHeadline())}</strong></div><div class="slots-cabinet" data-testid="slots-cabinet">${reelGridHtml()}<div class="slots-cabinet-footer"><p class="muted">${safe(cabinetNote())}</p><div class="slots-state-pill${!spinning && lastSpin?.payout > 0 ? ' win' : ''}" role="status">${safe(spinning ? tx('controls.wait') : (lastSpin?.payout > 0 ? tx('controls.winState') : tx('controls.readyState')))}</div></div><div class="slots-lever" aria-hidden="true"></div></div><div class="slots-result result-box" data-testid="slots-result">${resultSummary()}</div></section>`; }
// Define drawerHtml to render paytable/recent-spin details without affecting cabinet size.
function drawerHtml() { return `<section class="panel slots-drawer">${isBonusContext() ? featureSummaryHtml() : paytableHtml()}${recentSpinsHtml()}</section>`; }
// Define render to replace the Slots view atomically with the premium layout.
function render() { if (!root) return; root.innerHTML = `${styleHtml()}${validationStyleHtml()}<div class="game-layout three-col stable-game slots-premium" data-testid="slots-premium">${controlRailHtml()}${stageHtml()}${drawerHtml()}</div>`; bindControls(); mountPaylineGeometry(); }
// Define bindControls to wire the freshly-rendered controls to current state.
function bindControls() {
  // Rebuild the view after a supported payline count changes so all cost summaries stay aligned.
  root.querySelector('#lines').onchange = event => { selectedLines = Number(event.target.value || selectedLines); syncAutoplayPlan(); render(); };
  // Validate every typed line-bet edit immediately instead of waiting for Spin.
  root.querySelector('#lineBet').oninput = event => { acceptLineBetInput(event.target); };
  // Recheck committed edits for keyboard and assistive-technology change events.
  root.querySelector('#lineBet').onchange = event => { acceptLineBetInput(event.target); };
  // Start one manual spin through the same guarded public action used before this fix.
  root.querySelector('#spin').onclick = () => spin(true);
  // Re-fire the previous line setup with one click through the guarded repeat action.
  root.querySelector('[data-action="repeat"]')?.addEventListener('click', repeat);
  // Mount autoplay with the shared plan reference updated by every visible control edit.
  autoBox = renderAutoplay({ id: 'slots', plan: autoplayPlan, onTick: async () => spin(false) });
  // Attach the shared autoplay control plane to its reserved Slots panel.
  root.querySelector('#auto').append(autoBox);
}
// Define updateBotPanel to load bot capabilities through the documented bot API.
async function updateBotPanel() { botInfo = await eligibleBots('slots'); if (root && !spinning) render(); else if (root) pendingRender = true; }
// Define waitMotion to wait one bounded interval through the route-owned scope instead of a raw timer. (MOTION-002)
function waitMotion(ms) {
  // Resolve immediately when the route scope is gone so continuation semantics match the legacy timer path.
  if (!motionScope || motionScope.disposed) return Promise.resolve();
  // Schedule through the shared scope so navigation and reload cancel the pending reveal cleanly.
  return new Promise(resolve => { motionScope.schedule(resolve, ms, { reducedMotion: false }); });
}
// Define countEarlyScatters to detect a live free-spin tease across the first four authoritative reels.
function countEarlyScatters(grid) {
  // Accumulate scatter symbols across rows zero to two and columns zero to three only.
  let count = 0;
  // Walk each visible row of the committed grid.
  for (let row = 0; row < 3; row += 1) {
    // Walk only the columns that stop before the final reel.
    for (let column = 0; column < 4; column += 1) {
      // Count each scatter that will already be visible when the last reel is still travelling.
      if (grid?.[row]?.[column] === 'SCATTER') count += 1;
    }
  }
  // Return the tease-relevant scatter count.
  return count;
}
// Define runReelLanding to decelerate each decorative strip onto the authoritative grid with staggered stops. (SLOT-020, SLOT-021)
function runReelLanding(spin) {
  // Wrap the choreography in one promise so the spin flow can await the final stop plus hold.
  return new Promise(resolve => {
    // Read the committed grid whose rows every strip must finish on.
    const grid = spin?.grid;
    // Find the decorative overlay installed by the spinning render.
    const motionLayer = root?.querySelector('[data-testid="slots-reel-motion"]');
    // Measure two vertically adjacent authoritative cells so strip travel matches live geometry.
    const cellA = root?.querySelector('[data-testid="slot-cell-0-0"]');
    // Measure the second cell of the same column for the row stride.
    const cellB = root?.querySelector('[data-testid="slot-cell-1-0"]');
    // Skip choreography safely when the overlay, cells, scope, or grid are unavailable.
    if (!grid || !motionLayer || !cellA || !cellB || !motionScope || motionScope.disposed) { resolve(); return; }
    // Compute the live row stride in device pixels from measured cell tops.
    const stride = Math.max(24, cellB.getBoundingClientRect().top - cellA.getBoundingClientRect().top);
    // Seed decorative travel filler from the committed round id so one round always replays identically.
    const random = createSeededRandom(String(spin.round_id || 'slots-round'));
    // Detect the free-spin tease that slows the final reel with an anticipation glow.
    const anticipation = countEarlyScatters(grid) >= 2;
    // Track when the slowest reel finishes so the hold and reveal can follow it.
    let latestStopMs = 0;
    // Land every column through its own staggered deceleration.
    for (let column = 0; column < 5; column += 1) {
      // Find the clipped reel window for this column.
      const reel = motionLayer.querySelector(`[data-reel="${column}"]`);
      // Find the translating strip inside that window.
      const strip = reel?.querySelector('.slots-reel-strip');
      // Skip a column whose overlay was removed rather than failing the whole landing.
      if (!reel || !strip) continue;
      // Grow travel distance per column so later reels visibly spin farther before stopping.
      const travelRows = REEL_TRAVEL_BASE_ROWS + column * REEL_TRAVEL_STEP_ROWS;
      // Start the landing strip with the three authoritative rows that must finish on top.
      const tiles = [grid[0][column], grid[1][column], grid[2][column]];
      // Fill the travel span with seeded decorative symbols drawn from the engine-shaped pool.
      for (let filler = 0; filler < travelRows; filler += 1) tiles.push(SYMBOL_POOL[Math.floor(random() * SYMBOL_POOL.length)]);
      // Close the strip with the launch window so the first frame matches the tiles already on screen.
      const shown = currentGrid();
      // Append the three currently visible symbols of this column at the strip bottom.
      tiles.push(shown[0][column], shown[1][column], shown[2][column]);
      // Replace the launch strip content with the composed landing sequence.
      strip.innerHTML = tiles.map(tileHtml).join('');
      // Stop the priming shiver now that the real travel is starting.
      reel.classList.remove('priming');
      // Pin the strip at its launch offset without any transition.
      strip.style.transition = 'none';
      // Anchor the launch frame at zero so the bottom launch window stays visible.
      strip.style.transform = 'translateY(0px)';
      // Compute the total downward travel that puts the authoritative rows into the window.
      const travelPx = (tiles.length - 3) * stride;
      // Compute this column's deceleration budget including its stop stagger and any tease extension.
      const durationMs = REEL_BASE_STOP_MS + column * REEL_STAGGER_MS + (anticipation && column === 4 ? REEL_ANTICIPATION_MS : 0);
      // Light the anticipation glow on the final reel while early scatters tease the feature.
      if (anticipation && column === 4) reel.classList.add('anticipating');
      // Force one layout read so the browser commits the launch frame before the target changes. (PR #311 pattern)
      strip.getBoundingClientRect();
      // Apply the motion blur that reads as full reel speed.
      strip.classList.add('is-flying');
      // Coast the strip down past its landing point with one heavy ease-out plus a small overshoot.
      strip.style.transition = `transform ${durationMs}ms cubic-bezier(.24,.9,.34,1), filter .2s linear`;
      // Commit the overshoot target so the landing carries visible momentum.
      strip.style.transform = `translateY(${travelPx + REEL_OVERSHOOT_PX}px)`;
      // Lift the motion blur shortly before this reel lands.
      motionScope.schedule(() => strip.classList.remove('is-flying'), Math.max(0, durationMs - 260), { reducedMotion: false });
      // Snap the strip back from its overshoot exactly when its deceleration ends.
      motionScope.schedule(() => {
        // Recover the overshoot with one short bounce transition.
        strip.style.transition = `transform ${REEL_SETTLE_MS}ms cubic-bezier(.2,.8,.3,1)`;
        // Land the authoritative rows precisely on the cell geometry.
        strip.style.transform = `translateY(${travelPx}px)`;
        // Drop the tease glow the moment the final reel commits its stop.
        reel.classList.remove('anticipating');
        // Tick one landing click per reel with a rising pitch across the cabinet.
        clickSound(430 + column * 60, .05, .03);
      }, durationMs, { reducedMotion: false });
      // Extend the reveal deadline to cover this column's stop and bounce.
      latestStopMs = Math.max(latestStopMs, durationMs + REEL_SETTLE_MS);
    }
    // Reveal shortly after the slowest reel has bounced to rest; the caller re-checks the mounted root.
    motionScope.schedule(resolve, latestStopMs + REEL_HOLD_MS, { reducedMotion: false });
  });
}
// Define load to initialize resources, state, bot status, and the first render.
async function load() { await initI18n({ domains: [DOMAIN] }); await loadI18nDomain(DOMAIN); const data = await api(currentPlayerPath('/api/v1/games/slots/state')); state = data.state; config = data.config; lastSpin = latestStoredSpin(); if (lastSpin?.active_lines) selectedLines = Number(lastSpin.active_lines); if (lastSpin?.line_bet) selectedLineBet = Number(lastSpin.line_bet); if (lastSpin) lastBet = { active_lines: Number(lastSpin.active_lines), line_bet: Number(lastSpin.line_bet) }; syncAutoplayPlan(); render(); updateBotPanel(); await refreshBalance(); }
// Define spin to run one Slots action through the existing public endpoint.
async function spin(show = true) {
  // Ignore duplicate manual or autoplay starts while the current spin is committed.
  if (spinning) return;
  // Read the supported payline count from the mounted control before building the payload.
  selectedLines = Number(root.querySelector('#lines')?.value || selectedLines);
  // Reuse the immediate validator so a stale or scripted invalid spelling cannot reach the API.
  acceptLineBetInput(root.querySelector('#lineBet'));
  // Synchronize the shared autoplay plan before the public action begins.
  syncAutoplayPlan();
  // Enter the committed in-progress cabinet state only after controls are safe.
  spinning = true;
  // Read the live reduced-motion preference once at this atomic action boundary. (MOTION-005)
  const reducedMotion = prefersReducedMotion();
  // Run the full reel choreography only for attended spins without a comfort preference.
  const animate = show && !reducedMotion;
  // Mount the decorative strip overlay only when the full choreography will drive it.
  reelMotionActive = animate;
  // Advance the spin counter that seeds this round's decorative launch filler.
  spinSequence += 1;
  // Play the bounded reel sound matched to the expected travel of this spin mode.
  reelSound(animate ? 1600 : show ? 420 : 240);
  // Render the committed in-progress state before waiting on the backend.
  render();
  // Capture the mounted root so every continuation can reject a stale route. (house stale-async pattern)
  const mountedRoot = root;
  // Start protected API handling so failures restore an actionable screen.
  try {
    // Submit exactly the corrected values currently represented by the visible controls.
    const data = await post('/api/v1/games/slots/spin', withCurrentPlayer({ active_lines: selectedLines, line_bet: selectedLineBet }));
    // Land the decorative strips on the authoritative grid, or hold briefly for comfort and autoplay modes.
    if (animate && root === mountedRoot) await runReelLanding(data.spin);
    // Use the bounded non-animated reveal for reduced-motion and unattended spins.
    else await waitMotion(show ? REDUCED_HOLD_MS : AUTOPLAY_HOLD_MS);
    // Adopt authoritative game state returned by the frozen Slots API envelope.
    state = data.state;
    // Adopt the matching configuration returned by the backend.
    config = data.config;
    // Store the completed spin for result, win, and history presentation.
    lastSpin = data.spin;
    // Mark this settled render as fresh so win choreography plays exactly once. (SLOT-021)
    revealRoundId = data.spin?.round_id || null;
    // Remember the settled line setup so the next round can repeat it with one click.
    if (lastSpin) lastBet = { active_lines: Number(lastSpin.active_lines), line_bet: Number(lastSpin.line_bet) };
    // Leave the in-progress state before the settled rerender.
    spinning = false;
    // Drop the decorative overlay now that authoritative cells own the cabinet again.
    reelMotionActive = false;
    // Clear any repaint deferred during the animation because the settled render below applies it.
    pendingRender = false;
    // Render the authoritative result with corrected controls retained.
    render();
    // Reconcile the shared current-user wallet after settlement.
    await refreshBalance();
    // Preserve the existing result sound treatment.
    clickSound(data.spin.payout > 0 ? 860 : 260, .08);
    // Announce a human-visible payout through the existing voice policy.
    if (show && data.spin.payout > 0) speak(tx('voice.paid', { amount: fn(data.spin.payout) }), 'slots');
  // Handle the documented public-action failure path.
  } catch (error) {
    // Restore actionable controls after a failed spin.
    spinning = false;
    // Drop the decorative overlay so the failure state shows only authoritative cells.
    reelMotionActive = false;
    // Rerender the safe corrected input state.
    render();
    // Show localized fallback feedback without exposing backend internals.
    toast(error.message || tx('errors.spinFailed'));
  }
}
// Define repeat to re-fire the previous line setup with one click and no timer.
async function repeat() {
  // Ignore repeat while a spin is committed or before any bet has been captured.
  if (spinning || !lastBet) return;
  // Restore the previous active-line count into the visible control state.
  selectedLines = Number(lastBet.active_lines);
  // Restore the previous line bet into the visible control state.
  selectedLineBet = Number(lastBet.line_bet);
  // Align the shared autoplay plan with the restored configuration.
  syncAutoplayPlan();
  // Repaint the controls so the mounted inputs carry the restored setup before the spin reads them.
  render();
  // Fire one manual spin through the same guarded public action.
  await spin(true);
}
// Export this symbol so the shared app shell can mount the Slots route.
export const SlotsGame = { id: 'slots', label: 'Slots', async mount(node) { root = node; lastBet = null; spinning = false; reelMotionActive = false; pendingRender = false; revealRoundId = null; motionScope = createMotionTimerScope(); localeUnsubscribe = onLocaleChange(() => { if (spinning) { pendingRender = true; return; } render(); }); await load(); }, unmount() { if (autoBox?._stop) autoBox._stop(); if (localeUnsubscribe) localeUnsubscribe(); if (paylineResizeObserver) paylineResizeObserver.disconnect(); if (paylineFrame !== null) window.cancelAnimationFrame(paylineFrame); if (motionScope) motionScope.dispose(); motionScope = null; spinning = false; reelMotionActive = false; pendingRender = false; localeUnsubscribe = null; paylineResizeObserver = null; paylineFrame = null; lastBet = null; root = null; } };
