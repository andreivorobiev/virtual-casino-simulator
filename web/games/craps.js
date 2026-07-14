// Implement the isolated Craps browser route for GitHub issue #90.

// Import the standard API helpers for session-bound game requests.
import { api, post } from '../core/api.js';
// Import shared presentation helpers for safe markup and wallet refreshes.
import { refreshBalance, safe } from '../core/ui.js';
// Import the merged #97 dice helpers only for deterministic cosmetic frames.
import { createSeededRandom, rollDice } from '../core/dice.js';
// Import the merged #97 lifecycle scope so no game timer survives route teardown.
import { createMotionTimerScope, prefersReducedMotion } from '../core/motion.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned resource domain used by every visible and accessible string.
const DOMAIN = 'games/craps';
// Store the additive frozen-v1 API root once so endpoint construction cannot drift.
const API_ROOT = '/api/v1/games/craps';
// Store the route-local style id so repeated mounts never duplicate the style node.
const STYLE_ID = 'craps-game-styles';
// Store the number of decorative frames shown before the authoritative server dice.
export const COSMETIC_FRAME_COUNT = 4;
// Store the spacing between cosmetic frames for normal-motion presentation.
export const ROLL_FRAME_DELAY_MS = 110;
// Store the compatibility bet list used until the state endpoint returns metadata.
const DEFAULT_BET_TYPES = Object.freeze(['pass_line', 'dont_pass']);
// Store CSS-grid positions for code-native die pips without special-font glyphs.
const PIP_POSITIONS = Object.freeze({ 1: ['mc'], 2: ['tr', 'bl'], 3: ['tr', 'mc', 'bl'], 4: ['tl', 'tr', 'bl', 'br'], 5: ['tl', 'tr', 'mc', 'bl', 'br'], 6: ['tl', 'ml', 'bl', 'tr', 'mr', 'br'] });
// Store route-owned responsive styling without changing the shared stylesheet.
const ROUTE_CSS = [
  '.craps-shell{display:grid;grid-template-rows:auto minmax(0,1fr);gap:14px;height:100%;min-width:0;min-height:0;color:var(--text,#f7edda);}', // Keep the title compact above one stable game composition.
  '.craps-header{display:flex;align-items:end;justify-content:space-between;gap:16px;min-width:0;padding:2px;}', // Place title and actionable phase in the first hierarchy level.
  '.craps-header h1{margin:0;color:var(--gold,#ffd978);font-family:var(--font-display);font-size:clamp(34px,4vw,54px);line-height:1;}', // Give the game a strong localized title without consuming stage height.
  '.craps-header p{max-width:760px;margin:5px 0 0;color:var(--muted,#b8c8c1);}', // Keep the localized explanation subordinate to the title.
  '.craps-eyebrow{color:#fff2c2!important;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.09em;}', // Present the table family as a restrained casino eyebrow.
  '.craps-phase{flex:0 0 auto;padding:8px 13px;border:1px solid rgba(255,217,120,.45);border-radius:999px;background:rgba(4,27,19,.92);color:#fff2c2;font-weight:900;}', // Reserve a stable concise phase chip across every round state.
  '.craps-layout{grid-template-columns:minmax(225px,.68fr) minmax(620px,2.55fr) minmax(245px,.74fr);gap:14px;}', // Keep the felt wider and visually stronger than both support rails combined.
  '.craps-control,.craps-data{display:grid;align-content:start;gap:13px;padding:15px;}', // Separate controls and data into clear subordinate rail regions.
  '.craps-control h2,.craps-data h2,.craps-data h3{margin:0;color:#ffe7a6;}', // Give every support region an explicit readable heading.
  '.craps-field{display:grid;gap:6px;min-width:0;}', // Keep labels visibly connected to their semantic fields.
  '.craps-field span{color:var(--muted,#b8c8c1);font-size:12px;font-weight:900;}', // Present configuration labels without debug-tool styling.
  '.craps-field input,.craps-field select{width:100%;min-width:0;min-height:42px;}', // Preserve governed keyboard and touch target dimensions.
  '.craps-primary{width:100%;min-height:48px;border-color:#e5b74f;background:linear-gradient(180deg,#c72b38,#861620);color:#fff;font-weight:1000;}', // Use the governed red treatment for the one primary action.
  '.craps-primary:disabled{opacity:.62;cursor:not-allowed;}', // Keep disabled controls readable while the phase explains why.
  '.craps-retry-hint,.craps-rule-list{margin:0;color:var(--muted,#b8c8c1);font-size:12px;}', // Keep retry and rules guidance present but visually secondary.
  '.craps-error{min-height:38px;margin:0;color:#ffbcbc;}', // Reserve error space so failures never resize the stage.
  '.craps-stage{display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:14px;padding:15px;overflow:hidden;background:radial-gradient(circle at 50% 45%,rgba(37,128,82,.38),transparent 58%),linear-gradient(155deg,#073d29,#031b13);}', // Make the code-native felt the dominant game surface.
  '.craps-stage-head{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:48px;}', // Keep table identity and point puck stable above the dice.
  '.craps-stage-head h2{margin:0;color:#fff0b8;font-family:var(--font-display);font-size:30px;}', // Emphasize the localized table label within the dominant stage.
  '.craps-point{min-width:112px;padding:9px 12px;border:2px solid #efe8d8;border-radius:999px;background:#131816;color:#fff;text-align:center;font-weight:1000;}', // Use a text-bearing puck so point state never depends on color alone.
  '.craps-point.is-on{background:#f1e8d0;color:#16120b;box-shadow:0 0 24px rgba(255,230,160,.34);}', // Reinforce an active point while preserving its visible text.
  '.craps-felt{position:relative;display:grid;grid-template-rows:auto minmax(190px,1fr);gap:18px;min-height:420px;padding:24px;border:2px solid rgba(255,217,120,.58);border-radius:22px;background:linear-gradient(145deg,rgba(17,105,69,.94),rgba(5,55,36,.98));box-shadow:inset 0 0 70px rgba(0,0,0,.24);}', // Build one complete responsive table without a nested scroll surface.
  '.craps-bet-zones{display:grid;grid-template-columns:1fr 1fr;gap:13px;}', // Keep the two supported contract bets equally discoverable.
  '.craps-bet-zone{display:grid;place-items:center;min-height:86px;padding:12px;border:2px solid rgba(255,255,255,.22);border-radius:14px;color:#fff4d5;font-weight:1000;text-align:center;}', // Present wager areas as table furniture rather than raw fields.
  '.craps-bet-zone.is-selected{border-color:#ffe18a;outline:3px solid rgba(255,225,138,.28);outline-offset:2px;background:rgba(255,217,120,.13);}', // Show the active wager with outline and text beyond color alone.
  '.craps-zone-marker{display:block;margin-top:5px;color:#fff7d8;font-size:11px;font-weight:800;}', // Add a readable active-wager marker for non-color selection evidence.
  '.craps-dice-bay{display:grid;place-items:center;align-content:center;gap:14px;min-height:220px;border:1px solid rgba(255,255,255,.15);border-radius:18px;background:rgba(0,0,0,.16);}', // Reserve a fixed dice area through ready, rolling, and settled phases.
  '.craps-dice{display:flex;justify-content:center;gap:22px;min-height:112px;}', // Keep the authoritative pair centered and stable.
  '.craps-die{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);width:104px;height:104px;padding:14px;border:3px solid #f3e9d2;border-radius:18px;background:linear-gradient(145deg,#fffdf5,#dbcda9);box-shadow:0 16px 28px rgba(0,0,0,.38);}', // Draw reliable dice through CSS and semantic markup.
  '.craps-die.is-empty{border-style:dashed;background:rgba(255,255,255,.08);box-shadow:none;}', // Show a neutral waiting state without inventing a result.
  '.craps-die.is-rolling{animation:crapsDieTumble .22s ease-in-out;}', // Animate only decorative transform and opacity during presentation.
  '.craps-pip{align-self:center;justify-self:center;width:16px;height:16px;border-radius:50%;background:#16130f;box-shadow:inset 0 2px 2px rgba(255,255,255,.18);}', // Render each pip as a code-native circle.
  '.craps-pip.tl{grid-area:1/1}.craps-pip.tc{grid-area:1/2}.craps-pip.tr{grid-area:1/3}.craps-pip.ml{grid-area:2/1}.craps-pip.mc{grid-area:2/2}.craps-pip.mr{grid-area:2/3}.craps-pip.bl{grid-area:3/1}.craps-pip.bc{grid-area:3/2}.craps-pip.br{grid-area:3/3}', // Map named pip positions onto the die grid.
  '.craps-result{display:grid;place-items:center;gap:5px;min-height:74px;text-align:center;}', // Reserve one polite live result region without shifting the felt.
  '.craps-result strong{color:#fff0b8;font-size:22px;}', // Make the actionable result immediately scannable.
  '.craps-settlement{display:grid;gap:4px;min-height:74px;padding:12px;border:1px solid rgba(255,217,120,.28);border-radius:14px;background:rgba(0,0,0,.18);}', // Keep the lower result summary fixed across phase changes.
  '.craps-data-section{display:grid;gap:9px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,.1);}', // Separate current wager, history, and rules without nested panels.
  '.craps-data-section:last-child{padding-bottom:0;border-bottom:0;}', // Avoid an unnecessary terminal divider.
  '.craps-metrics{display:grid;gap:7px;}', // Align current wager values in predictable rows.
  '.craps-metric,.craps-history-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.08);}', // Align labels and values without creating another scroll container.
  '.craps-metric:last-child,.craps-history-row:last-child{border-bottom:0;}', // Keep the final row visually clean.
  '.craps-history{display:grid;gap:2px;}', // Let the parent data rail own all intentional scrolling.
  '.craps-history-row span small{display:block;margin-top:3px;color:var(--muted,#b8c8c1);}', // Keep wager detail subordinate to the localized outcome.
  '.craps-rule-list{display:grid;gap:8px;padding-left:18px;}', // Present the compact game rule summary as readable prose.
  '.craps-shell button:focus-visible,.craps-shell input:focus-visible,.craps-shell select:focus-visible,.craps-control:focus-visible,.craps-data:focus-visible{outline:3px solid #ffd978;outline-offset:2px;}', // Preserve clear keyboard focus on controls and scroll rails.
  '@keyframes crapsDieTumble{0%{opacity:.62;transform:rotate(-7deg) scale(.92)}100%{opacity:1;transform:rotate(0) scale(1)}}', // Animate only transform and opacity to avoid layout movement.
  '@media(max-width:1200px){.craps-shell{height:auto}.craps-layout{grid-template-columns:1fr;grid-template-rows:auto;height:auto;overflow:visible;contain:none}.craps-control{order:1}.craps-stage{order:2;min-height:620px}.craps-data{order:3}.craps-control,.craps-data{overflow:visible}}', // Switch to document scrolling in the governed control-stage-data order.
  '@media(max-width:560px){.craps-header{align-items:start;flex-direction:column}.craps-layout{gap:12px}.craps-stage,.craps-control,.craps-data{padding:12px}.craps-felt{min-height:390px;padding:14px}.craps-bet-zones{grid-template-columns:1fr}.craps-die{width:82px;height:82px;padding:11px}.craps-pip{width:12px;height:12px}.craps-dice{gap:13px}.craps-stage-head{align-items:start;flex-direction:column}}', // Fit all essential controls and dice inside the required mobile viewport.
  '@media(prefers-reduced-motion:reduce){.craps-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}.craps-die.is-rolling{transform:none!important}}', // Remove decorative motion while preserving asynchronous result semantics.
  '.craps-shell[data-reduced-motion="true"] .craps-die{animation:none!important;transition:none!important;}', // Expose and enforce the runtime reduced-motion state for focused evidence.
].join(''); // Combine scoped CSS fragments into one route-owned stylesheet.

// Store the shared route outlet while this lazy module is mounted.
let root = null;
// Store the latest session-bound backend state for reload-safe rendering.
let gameState = { active_round: null, recent_rounds: [] };
// Store API-provided wager types while retaining a compatible initial control list.
let betTypes = [...DEFAULT_BET_TYPES];
// Store the locally selected wager type before the next round starts.
let selectedBetType = DEFAULT_BET_TYPES[0];
// Store the locally entered play-token wager before the next round starts.
let wager = 5;
// Store the most recently returned round even after settlement archives it.
let displayedRound = null;
// Store the most recently returned roll for authoritative presentation.
let displayedRoll = null;
// Store temporary cosmetic faces shown before the authoritative pair.
let visibleDice = null;
// Store the currently running action so controls cannot overlap atomic requests.
let busyAction = null;
// Store the temporary presentation phase without mutating backend state.
let presentationPhase = null;
// Store the localized error resource key shown in the reserved control region.
let errorKey = null;
// Store whether the current presentation follows the reduced-motion preference.
let reducedMotionActive = false;
// Store one disposable scope that owns every route timer and lifecycle listener.
let motionScope = null;
// Store the locale subscription cleanup callback for route teardown.
let localeUnsubscribe = null;
// Retain an unresolved start identity so an ambiguous retry cannot duplicate a wager.
let pendingStartRequestId = null;
// Retain an unresolved roll identity so an ambiguous retry cannot roll twice.
let pendingRollRequestId = null;

// Resolve one game-owned localized string after the domain has loaded.
function tx(key, params = {}) {
  // Delegate interpolation and fallback handling to the shared i18n runtime.
  return t(key, params, DOMAIN);
}

// Return one stable retry identity through an injectable UUID source.
export function createClientRequestId(action, randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Restrict identities to the two public atomic action families.
  if (!['start', 'roll'].includes(action)) throw new RangeError('action must be start or roll');
  // Require a secure UUID source in production while permitting deterministic tests.
  if (typeof randomUUID !== 'function') throw new Error('a secure UUID generator is required');
  // Prefix the opaque UUID without embedding player information.
  return `craps-${action}-${randomUUID()}`;
}

// Report whether one normalized wager satisfies the frozen OpenAPI amount domain.
export function isValidWager(value) {
  // Reject non-numeric and non-finite values before range or precision checks.
  if (typeof value !== 'number' || !Number.isFinite(value)) return false;
  // Enforce the inclusive public-contract minimum and maximum.
  if (value < 0.01 || value > 100000) return false;
  // Require a value representable as an exact whole number of cents.
  return Math.round(value * 100) / 100 === value;
}

// Normalize one authoritative or cosmetic pair before it reaches presentation code.
function normalizedDice(dice) {
  // Require exactly two integer faces inside standard six-sided bounds.
  if (!Array.isArray(dice) || dice.length !== 2 || dice.some(face => !Number.isInteger(face) || face < 1 || face > 6)) throw new RangeError('dice must contain two faces from 1 through 6');
  // Copy the pair so later caller mutation cannot change a scheduled frame.
  return [...dice];
}

// Build deterministic cosmetic pairs without deciding or replacing the server result.
export function createCosmeticDiceFrames(seed, frameCount = COSMETIC_FRAME_COUNT) {
  // Require a bounded positive frame count so animations cannot create runaway work.
  if (!Number.isSafeInteger(frameCount) || frameCount < 1 || frameCount > 12) throw new RangeError('frameCount must be between 1 and 12');
  // Create the merged #97 seeded source from the server-owned round/action identity.
  const random = createSeededRandom(seed);
  // Allocate the exact number of cosmetic frames requested by presentation.
  const frames = [];
  // Generate two decorative six-sided faces for every transient frame.
  for (let index = 0; index < frameCount; index += 1) frames.push(rollDice({ count: 2, sides: 6, random }));
  // Return frames that callers must discard when the authoritative pair arrives.
  return frames;
}

// Schedule cosmetic frames followed by one authoritative server result.
export function scheduleRollPresentation({ timerScope, frames, finalDice, onFrame, onSettled, frameDelay = ROLL_FRAME_DELAY_MS }) {
  // Require the merged #97 timer-scope interface rather than unmanaged timers.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require explicit callbacks so presentation ownership remains testable.
  if (typeof onFrame !== 'function' || typeof onSettled !== 'function') throw new TypeError('presentation callbacks must be callable');
  // Require a finite non-negative interval accepted by the shared motion helper.
  if (!Number.isFinite(frameDelay) || frameDelay < 0) throw new RangeError('frameDelay must be non-negative');
  // Snapshot every decorative frame before scheduling lifecycle-owned callbacks.
  const safeFrames = frames.map(normalizedDice);
  // Snapshot the authoritative pair separately so cosmetic data can never replace it.
  const safeFinalDice = normalizedDice(finalDice);
  // Schedule each transient pair in deterministic source order.
  safeFrames.forEach((frame, index) => timerScope.schedule(() => onFrame([...frame], index), (index + 1) * frameDelay));
  // Calculate the final deadline after every cosmetic frame.
  const finalDelay = (safeFrames.length + 1) * frameDelay;
  // Schedule the authoritative pair through the same disposable scope.
  const token = timerScope.schedule(() => onSettled([...safeFinalDice]), finalDelay);
  // Return deterministic timing evidence and the final cancellation token.
  return { finalDelay, token };
}

// Select one persisted terminal roll whose ledger settlement still needs recovery.
export function pendingSettlementRecovery(state) {
  // Combine active and archived state because recovery must tolerate storage migrations.
  const rounds = [state?.active_round, ...(state?.recent_rounds || [])].filter(Boolean);
  // Keep only settled rounds whose terminal ledger movement is not complete.
  const pendingRounds = rounds.filter(roundItem => roundItem.phase === 'settled' && roundItem.settlement_status === 'pending');
  // Select the newest retained pending round for one bounded recovery action.
  const roundItem = pendingRounds.slice(-1)[0];
  // Return no work when reload state contains no interrupted settlement.
  if (!roundItem) return null;
  // Read the persisted terminal roll whose request identity drives exact replay.
  const roll = roundItem.rolls?.slice(-1)[0];
  // Refuse to invent a new identity when persisted recovery metadata is incomplete.
  if (!roll?.request_id) return null;
  // Return only the route and request fields needed by the public roll endpoint.
  return { round_id: roundItem.round_id, request_id: roll.request_id };
}

// Install the game-owned stylesheet once without touching shared CSS ownership.
function ensureStyles() {
  // Reuse the existing style node after route remounts.
  if (document.getElementById(STYLE_ID)) return;
  // Create one standard style element for scoped Craps selectors.
  const style = document.createElement('style');
  // Assign the stable id used by duplicate-mount protection.
  style.id = STYLE_ID;
  // Attach the complete route-owned CSS payload.
  style.textContent = ROUTE_CSS;
  // Install styles before the first visible render.
  document.head.append(style);
}

// Format a play-token value without currency or special-font glyphs.
function tokenAmount(value, translate = tx) {
  // Format ledger precision through the active locale.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append localized fake-token terminology through the game domain.
  return translate('units.playTokens', { amount });
}

// Return every known round that can prove a pending retry already committed.
function knownRounds() {
  // Combine the active round and archived player history while dropping absent values.
  return [gameState.active_round, ...(gameState.recent_rounds || [])].filter(Boolean);
}

// Clear retry identities only after session state proves their action exists.
function reconcilePendingRequestIds() {
  // Clear a start identity when the corresponding player-scoped round is visible.
  if (pendingStartRequestId && knownRounds().some(roundItem => roundItem.start_request_id === pendingStartRequestId)) pendingStartRequestId = null;
  // Clear a roll identity when any player-scoped round contains that exact roll.
  if (pendingRollRequestId && knownRounds().some(roundItem => (roundItem.rolls || []).some(roll => roll.request_id === pendingRollRequestId))) pendingRollRequestId = null;
}

// Apply one standard state-bearing response without assuming action-only fields exist.
function applyPayload(payload) {
  // Replace cached state only when the standard payload includes it.
  if (payload?.state) gameState = payload.state;
  // Adopt API-provided bet metadata while preserving the supported fallback list.
  if (Array.isArray(payload?.bet_types) && payload.bet_types.length) betTypes = [...payload.bet_types];
  // Keep the direct action round visible after settlement removes active_round.
  if (payload?.round) displayedRound = payload.round;
  // Keep only the authoritative direct action roll for dice presentation.
  if (payload?.roll) displayedRoll = payload.roll;
  // Reconcile unresolved browser identities against authoritative reload-safe state.
  reconcilePendingRequestIds();
}

// Return the active round or most recently displayed/history round for one stable stage.
function currentRound(model) {
  // Prefer the actionable round before a newly settled or archived round.
  return model.state.active_round || model.displayedRound || model.state.recent_rounds?.slice(-1)[0] || null;
}

// Return the latest authoritative roll belonging to the selected round.
function currentRoll(model, roundItem) {
  // Prefer the direct response only when it belongs to the same displayed round.
  if (model.displayedRoll && model.displayedRound?.round_id === roundItem?.round_id) return model.displayedRoll;
  // Fall back to the latest persisted roll restored through state.
  return roundItem?.rolls?.slice(-1)[0] || null;
}

// Snapshot mutable module state for deterministic pure markup generation.
function currentModel() {
  // Return one shallow presentation snapshot without exposing mutation helpers.
  return { state: gameState, betTypes, selectedBetType, wager, displayedRound, displayedRoll, visibleDice, busyAction, presentationPhase, errorKey, reducedMotionActive };
}

// Render one semantic die from code-native pips and a localized accessible name.
function dieHtml(face, index, rolling, translate) {
  // Render a neutral placeholder when no authoritative or cosmetic face exists.
  if (!Number.isInteger(face)) return `<div class="craps-die is-empty" role="img" aria-label="${safe(translate('dice.waiting'))}"></div>`;
  // Render only the pip positions required by the validated face.
  const pips = PIP_POSITIONS[face].map(position => `<span class="craps-pip ${position}" aria-hidden="true"></span>`).join('');
  // Return one accessible die whose decorative pips remain hidden from narration.
  return `<div class="craps-die${rolling ? ' is-rolling' : ''}" role="img" aria-label="${safe(translate('dice.dieLabel', { index, value: face }))}">${pips}</div>`;
}

// Return localized controls for starting a round or rolling its active point state.
function controlsHtml(model, translate) {
  // Read the active session-bound round to determine the one legal primary action.
  const activeRound = model.state.active_round;
  // Use the active wager configuration while a round is in progress.
  const selected = activeRound?.bet_type || model.selectedBetType;
  // Use the committed wager while a round is in progress.
  const amount = activeRound?.wager ?? model.wager;
  // Disable configuration after debit or while any request is in flight.
  const configurationDisabled = Boolean(activeRound || model.busyAction);
  // Render every API-supported bet type through the owned locale domain.
  const options = model.betTypes.map(betType => `<option value="${safe(betType)}"${selected === betType ? ' selected' : ''}>${safe(translate(`bet.${betType}`))}</option>`).join('');
  // Choose the roll action only while an active round exists.
  const action = activeRound ? 'roll' : 'start';
  // Choose localized pending or ready action copy without exposing internal state.
  const actionKey = model.busyAction === action ? `controls.${action}Pending` : `controls.${action}`;
  // Return the keyboard-readable control rail with one stable primary action.
  return `<section class="panel control-rail craps-control" tabindex="0" role="region" aria-label="${safe(translate('controls.aria'))}"><h2>${safe(translate('controls.title'))}</h2><label class="craps-field" for="craps-bet-type"><span>${safe(translate('controls.betType'))}</span><select id="craps-bet-type" data-testid="craps-bet-type"${configurationDisabled ? ' disabled' : ''}>${options}</select></label><label class="craps-field" for="craps-wager"><span>${safe(translate('controls.wager'))}</span><input id="craps-wager" data-testid="craps-wager" type="number" min="0.01" max="100000" step="0.01" inputmode="decimal" value="${safe(amount)}"${configurationDisabled ? ' disabled' : ''}></label><button type="button" class="craps-primary" data-action="${action}" data-testid="craps-${action}"${model.busyAction ? ' disabled' : ''}>${safe(translate(actionKey))}</button><p class="craps-retry-hint">${safe(translate('controls.retryHint'))}</p><p class="craps-error" data-testid="craps-error" aria-live="polite">${model.errorKey ? safe(translate(model.errorKey)) : ''}</p></section>`;
}

// Return the dominant felt, authoritative dice, point puck, and stable result region.
function stageHtml(model, translate) {
  // Select the current actionable or latest completed round.
  const roundItem = currentRound(model);
  // Select the latest authoritative roll for result copy.
  const roll = currentRoll(model, roundItem);
  // Prefer cosmetic faces only while the presentation phase is rolling.
  const dice = model.presentationPhase === 'rolling' && model.visibleDice ? model.visibleDice : (roll?.dice || null);
  // Compute the displayed total only from the visible pair.
  const total = dice ? dice[0] + dice[1] : null;
  // Resolve the player-facing phase key without exposing backend enum text.
  const phase = model.presentationPhase === 'rolling' ? 'rolling' : (roundItem?.phase || 'ready');
  // Resolve point text from the committed server round.
  const pointLabel = roundItem?.point ? translate('stage.pointOn', { point: roundItem.point }) : translate('stage.pointOff');
  // Resolve the stage live-title for ready, rolling, or authoritative resolution.
  const resultTitle = phase === 'ready' ? translate('result.readyTitle') : phase === 'rolling' ? translate('result.rollingTitle') : roll ? translate(`resolution.${roll.resolution}`, { point: roll.point_after || roundItem?.point || '' }) : translate('resolution.pending');
  // Resolve the stage live-detail without announcing cosmetic frame values.
  const resultBody = phase === 'ready' ? translate('result.readyBody') : phase === 'rolling' ? translate('result.rollingBody') : roll ? translate('result.total', { total: roll.total }) : translate('resolution.pending');
  // Resolve the pair's accessible name only when faces exist.
  const pairLabel = dice ? translate('dice.pairLabel', { first: dice[0], second: dice[1], total }) : translate('dice.waiting');
  // Mark the active committed wager with readable text in addition to styling.
  const activeBet = roundItem?.phase !== 'settled' ? roundItem?.bet_type : null;
  // Render both supported felt zones from locale keys and committed selection state.
  const zones = model.betTypes.map(betType => `<div class="craps-bet-zone${activeBet === betType ? ' is-selected' : ''}"${activeBet === betType ? ' aria-current="true"' : ''}>${safe(translate(`bet.${betType}`))}${activeBet === betType ? `<span class="craps-zone-marker">${safe(translate('current.title'))}</span>` : ''}</div>`).join('');
  // Return the complete dominant stage with one polite authoritative result region.
  return `<main class="panel game-stage craps-stage" aria-label="${safe(translate('stage.aria'))}"><div class="craps-stage-head"><h2>${safe(translate('stage.tableLabel'))}</h2><span class="craps-point${roundItem?.point ? ' is-on' : ''}" data-testid="craps-point">${safe(pointLabel)}</span></div><section class="craps-felt"><div class="craps-bet-zones">${zones}</div><div class="craps-dice-bay"><div class="craps-dice" role="group" aria-label="${safe(pairLabel)}" data-testid="craps-dice">${dieHtml(dice?.[0], 1, phase === 'rolling', translate)}${dieHtml(dice?.[1], 2, phase === 'rolling', translate)}</div><div class="craps-result" role="status" aria-live="polite" aria-atomic="true"><strong>${safe(resultTitle)}</strong><span>${safe(resultBody)}</span></div></div></section><div class="craps-settlement"><strong>${safe(translate(`phase.${phase}`))}</strong><span>${safe(roundItem?.outcome ? translate(`outcome.${roundItem.outcome}`) : translate('outcome.pending'))}</span></div></main>`;
}

// Return the current wager, recent settlements, and compact table rules.
function dataHtml(model, translate) {
  // Select the active or most recently displayed round for summary metrics.
  const roundItem = currentRound(model);
  // Render current wager rows only when a round exists.
  const current = roundItem ? `<div class="craps-metrics"><div class="craps-metric"><span>${safe(translate('current.betType'))}</span><strong>${safe(translate(`bet.${roundItem.bet_type}`))}</strong></div><div class="craps-metric"><span>${safe(translate('current.wager'))}</span><strong>${safe(tokenAmount(roundItem.wager, translate))}</strong></div><div class="craps-metric"><span>${safe(translate('current.point'))}</span><strong>${safe(roundItem.point || translate('stage.pointOff'))}</strong></div><div class="craps-metric"><span>${safe(translate('current.rolls'))}</span><strong>${safe(formatNumber(roundItem.rolls?.length || 0))}</strong></div></div>` : `<p>${safe(translate('current.empty'))}</p>`;
  // Read newest settled rounds first while bounding route markup.
  const rounds = [...(model.state.recent_rounds || [])].reverse().slice(0, 8);
  // Render localized settlement rows without exposing player ids or internal request ids.
  const history = rounds.length ? rounds.map(item => `<div class="craps-history-row"><span><strong>${safe(translate('history.row', { betType: translate(`bet.${item.bet_type}`), outcome: translate(`outcome.${item.outcome || 'pending'}`) }))}</strong><small>${safe(translate('history.wager', { amount: tokenAmount(item.wager, translate) }))}</small></span><strong>${safe(formatNumber(item.rolls?.length || 0))}</strong></div>`).join('') : `<p>${safe(translate('history.empty'))}</p>`;
  // Return one keyboard-focusable data rail with no nested scroll owner.
  return `<aside class="panel details-drawer craps-data" tabindex="0" role="region" aria-label="${safe(translate('data.aria'))}"><section class="craps-data-section"><h2>${safe(translate('current.title'))}</h2>${current}</section><section class="craps-data-section"><h3>${safe(translate('history.title'))}</h3><div class="craps-history" aria-label="${safe(translate('history.aria'))}">${history}</div></section><section class="craps-data-section"><h3>${safe(translate('rules.title'))}</h3><ul class="craps-rule-list"><li>${safe(translate('rules.comeOut'))}</li><li>${safe(translate('rules.point'))}</li><li>${safe(translate('rules.dontPush'))}</li></ul></section></aside>`;
}

// Return the complete localized route for production and injected-translation tests.
export function viewMarkup({ translate = tx, model = currentModel() } = {}) {
  // Resolve the current phase once for the stable header chip.
  const roundItem = currentRound(model);
  // Prefer the temporary rolling phase before the committed backend phase.
  const phase = model.presentationPhase === 'rolling' ? 'rolling' : (roundItem?.phase || 'ready');
  // Return the governed header and control-stage-data composition.
  return `<section class="craps-shell" data-testid="craps" data-reduced-motion="${model.reducedMotionActive}"><header class="craps-header"><div><p class="craps-eyebrow">${safe(translate('eyebrow'))}</p><h1>${safe(translate('title'))}</h1><p>${safe(translate('subtitle'))}</p></div><span class="craps-phase" role="status" data-testid="craps-phase">${safe(translate(`phase.${phase}`))}</span></header><div class="game-layout three-col stable-game craps-layout">${controlsHtml(model, translate)}${stageHtml(model, translate)}${dataHtml(model, translate)}</div></section>`;
}

// Replace the route atomically and reconnect semantic event handlers.
function render() {
  // Ignore async completions after route teardown.
  if (!root) return;
  // Render every visible string from the active game-owned dictionary.
  root.innerHTML = viewMarkup();
  // Read the wager-type field created by this render.
  const betTypeField = root.querySelector('#craps-bet-type');
  // Clear the unresolved start identity when the user intentionally changes its payload.
  if (betTypeField) betTypeField.onchange = () => { selectedBetType = betTypeField.value; pendingStartRequestId = null; render(); };
  // Read the wager field created by this render.
  const wagerField = root.querySelector('#craps-wager');
  // Cache valid wager edits and clear the old payload identity before the next action.
  if (wagerField) wagerField.onchange = () => { wager = Number(wagerField.value); pendingStartRequestId = null; render(); };
  // Wire the one mounted primary action through its public endpoint.
  root.querySelector('[data-action="start"]')?.addEventListener('click', startRound);
  // Wire active-round rolls through the public session-bound action.
  root.querySelector('[data-action="roll"]')?.addEventListener('click', rollRound);
}

// Load reload-safe state for the authenticated session and repaint the route.
async function load() {
  // Fetch the standard state payload without sending any caller-selected player id.
  let payload = await api(`${API_ROOT}/state`);
  // Apply player-scoped state and contract metadata.
  applyPayload(payload);
  // Select an interrupted settlement using only persisted server state.
  const recovery = pendingSettlementRecovery(gameState);
  // Replay the exact terminal roll identity without cosmetic motion or a new UUID.
  if (recovery) {
    // Capture route ownership across the recovery request.
    const mountedRoot = root;
    // Capture lifecycle ownership across the recovery request.
    const activeScope = motionScope;
    // Start protected recovery so a transient failure does not hide reload-safe state.
    try {
      // Ask the public roll action to complete or replay the pending settlement.
      payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(recovery.round_id)}/rolls`, { request_id: recovery.request_id });
      // Stop when navigation or remount replaced this recovery owner.
      if (root !== mountedRoot || motionScope !== activeScope) return;
      // Apply the recovered settlement and standard state payload.
      applyPayload(payload);
    // Preserve the stored round and expose localized retry guidance on recovery failure.
    } catch (error) {
      // Stop when navigation or remount already released route ownership.
      if (root !== mountedRoot || motionScope !== activeScope) return;
      // Show owned guidance while leaving the persisted identity available on reload.
      errorKey = 'errors.rollFailed';
    }
  }
  // Prefer the active or latest archived server round after reload.
  displayedRound = payload?.round || gameState.active_round || gameState.recent_rounds?.slice(-1)[0] || null;
  // Restore the latest persisted roll as the authoritative visible pair.
  displayedRoll = payload?.roll || displayedRound?.rolls?.slice(-1)[0] || null;
  // Align pre-round controls to an active restored wager when present.
  selectedBetType = gameState.active_round?.bet_type || selectedBetType;
  // Align the wager field to an active restored debit when present.
  wager = gameState.active_round?.wager || wager;
  // Render only after state and locale resources are ready.
  render();
}

// Start one wagered round with a retry identity retained across ambiguous failures.
async function startRound() {
  // Ignore overlapping or stale start events.
  if (busyAction || gameState.active_round) return;
  // Read the latest form values before rerender replaces the controls.
  selectedBetType = root.querySelector('#craps-bet-type')?.value || selectedBetType;
  // Normalize the current wager from the semantic number input without accepting a stale fallback.
  const candidateWager = Number(root.querySelector('#craps-wager')?.value);
  // Reject out-of-contract range or precision before creating an action identity.
  if (!isValidWager(candidateWager)) { errorKey = 'errors.wagerRequired'; render(); return; }
  // Commit the validated payload value only after all OpenAPI amount checks pass.
  wager = candidateWager;
  // Reuse an unresolved identity until the server confirms or recovers the debit.
  pendingStartRequestId = pendingStartRequestId || createClientRequestId('start');
  // Capture this mount and scope so late responses cannot repaint another route.
  const mountedRoot = root;
  // Capture the active scope identity for the same late-response guard.
  const activeScope = motionScope;
  // Lock controls in their stable positions while the request is in flight.
  busyAction = 'start';
  // Clear prior localized feedback before the new attempt.
  errorKey = null;
  // Render the disabled primary action and understandable phase.
  render();
  // Start protected API handling so failures keep the retry identity.
  try {
    // Submit only the contract fields; session middleware owns player resolution.
    const payload = await post(`${API_ROOT}/rounds`, { request_id: pendingStartRequestId, bet_type: selectedBetType, wager });
    // Discard a response that completed after route or scope replacement.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Apply the committed player-scoped round and state payload.
    applyPayload(payload);
    // Clear the identity only after the server response proves recovery.
    pendingStartRequestId = null;
    // Reset stale dice before the new come-out roll.
    displayedRoll = null;
    // Clear transient presentation faces from the prior round.
    visibleDice = null;
    // Release the action lock after the wager is confirmed.
    busyAction = null;
    // Render the active come-out round.
    render();
    // Refresh the shared wallet without turning a confirmed debit into an action failure.
    await refreshBalance().catch(() => {});
  // Convert failures into localized route-owned guidance without losing retry safety.
  } catch (error) {
    // Ignore failures delivered after this route lost ownership.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Release the action lock while retaining pendingStartRequestId.
    busyAction = null;
    // Show owned localized retry guidance in the reserved region.
    errorKey = 'errors.startFailed';
    // Repaint the recovered controls without starting shared feedback timing.
    render();
  }
}

// Roll the active round and present only the server-authoritative final pair.
async function rollRound() {
  // Read the current player-scoped active round once.
  const activeRound = gameState.active_round;
  // Ignore overlapping, settled, or stale roll events.
  if (busyAction || !activeRound || activeRound.phase === 'settled') return;
  // Reuse an unresolved identity until the server confirms this exact roll.
  pendingRollRequestId = pendingRollRequestId || createClientRequestId('roll');
  // Capture this route outlet so late network work cannot repaint another screen.
  const mountedRoot = root;
  // Capture the current disposable scope so remounts invalidate this action.
  const activeScope = motionScope;
  // Cancel any abandoned decorative callbacks from an earlier presentation.
  activeScope.cancelAll();
  // Lock the one atomic action before contacting the ledger-backed endpoint.
  busyAction = 'roll';
  // Show a player-facing rolling phase while preserving stage dimensions.
  presentationPhase = 'rolling';
  // Read the platform preference through the merged #97 helper.
  reducedMotionActive = prefersReducedMotion();
  // Clear prior localized feedback before the new attempt.
  errorKey = null;
  // Render the stable in-progress surface.
  render();
  // Start protected API handling so failures retain the same roll identity.
  try {
    // Submit only the roll retry identity to the active round endpoint.
    const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(activeRound.round_id)}/rolls`, { request_id: pendingRollRequestId });
    // Discard a result delivered after navigation or remount.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Snapshot the confirmed request identity before state reconciliation clears it.
    const confirmedRequestId = pendingRollRequestId;
    // Apply the authoritative round, roll, settlement, and reload-safe state.
    applyPayload(payload);
    // Clear the pending identity because this response proves the action committed.
    pendingRollRequestId = null;
    // Build deterministic cosmetic pairs from server-owned round and roll identities.
    const frames = createCosmeticDiceFrames(`${payload.round.round_id}:${confirmedRequestId}:${payload.roll.roll_index}`);
    // Schedule all decorative work through the captured disposable scope.
    scheduleRollPresentation({
      timerScope: activeScope, // Bind every callback to the current route lifecycle.
      frames, // Supply deterministic decorative pairs that never affect settlement.
      finalDice: payload.roll.dice, // Supply the authoritative server result separately.
      onFrame: frame => { // Repaint one transient pair only while this mount still owns the route.
        if (root !== mountedRoot || motionScope !== activeScope) return; // Ignore callbacks after teardown or remount.
        visibleDice = frame; // Store the current decorative pair for presentation only.
        render(); // Repaint without changing backend-owned round state.
      },
      onSettled: finalDice => { // Reveal and announce the authoritative pair at the final deadline.
        if (root !== mountedRoot || motionScope !== activeScope) return; // Ignore settlement presentation after route exit.
        visibleDice = finalDice; // Store only the validated server pair at completion.
        presentationPhase = null; // Return phase ownership to committed backend state.
        busyAction = null; // Unlock the next legal action after presentation settles.
        render(); // Announce the authoritative result through the stable live region.
        refreshBalance().catch(() => {}); // Refresh wallet settlement while containing noncritical shell failures.
      },
    });
  // Convert API failures into localized route-owned guidance without starting another roll.
  } catch (error) {
    // Ignore a failure delivered after route ownership changed.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Cancel decorative work associated with the failed presentation.
    activeScope.cancelAll();
    // Release controls while retaining pendingRollRequestId for exact replay.
    busyAction = null;
    // Return phase ownership to the last committed backend state.
    presentationPhase = null;
    // Show localized recovery guidance in the reserved control region.
    errorKey = 'errors.rollFailed';
    // Restore the stable route without starting shared feedback timing.
    render();
  }
}

// Export the catalog-declared lazy game contract for shared integration owner #77.
export const CrapsGame = {
  // Expose the stable internal game id without hard-coded visible copy.
  id: 'craps',
  // Leave presentation labels to the owned descriptor and locale domain.
  label: '',
  // Mount the route, locale resources, lifecycle scope, and reload-safe state.
  async mount(node) {
    // Store the current shared-shell route outlet.
    root = node;
    // Install route-owned styling before first paint.
    ensureStyles();
    // Dispose a defensive stale scope before creating this mount's owner.
    motionScope?.dispose();
    // Create one lifecycle-bound scope for every game-owned callback.
    motionScope = createMotionTimerScope();
    // Capture the mount identity across asynchronous locale loading.
    const mountedRoot = root;
    // Capture the scope identity across asynchronous initialization.
    const activeScope = motionScope;
    // Load active and fallback Craps dictionaries before visible rendering.
    await loadI18nDomain(DOMAIN);
    // Stop initialization when navigation replaced this mount.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Subscribe to locale changes without resetting point or wager state.
    localeUnsubscribe = onLocaleChange(() => render());
    // Read reduced-motion state for the first rendered frame.
    reducedMotionActive = prefersReducedMotion();
    // Load the authenticated player's reload-safe round state.
    await load();
    // Stop wallet work when route ownership changed during state loading.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Refresh the shared wallet without rejecting an otherwise successful mount.
    await refreshBalance().catch(() => {});
  },
  // Release every game-owned lifecycle resource when navigation leaves Craps.
  unmount() {
    // Permanently cancel pending callbacks and lifecycle listeners.
    motionScope?.dispose();
    // Clear the disposed scope reference for the next mount.
    motionScope = null;
    // Remove the locale callback when initialization completed.
    localeUnsubscribe?.();
    // Clear the subscription reference for repeated teardown safety.
    localeUnsubscribe = null;
    // Clear the outlet first so late promises become inert.
    root = null;
    // Release the local action lock without discarding unresolved retry identities.
    busyAction = null;
    // Clear decorative presentation state owned by the inactive route.
    presentationPhase = null;
    // Clear cosmetic dice so remount restores only server state.
    visibleDice = null;
  },
};
