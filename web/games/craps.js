// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the isolated Craps browser route for GitHub issue #90.

// Import the standard API helpers for session-bound game requests.
import { api, post } from '../core/api.js';
// Import shared presentation helpers for safe markup and wallet refreshes.
import { refreshBalance, safe } from '../core/ui.js';
// Import the merged #97 dice helpers only for deterministic cosmetic frames.
import { createSeededRandom, rollDice } from '../core/dice.js';
// Import the merged #97 lifecycle scope so no game timer survives route teardown.
import { createMotionTimerScope, prefersReducedMotion } from '../core/motion.js';
// Import locale-aware number formatting while shared lifecycle owns translations.
import { formatNumber } from '../core/i18n.js';
// Import the shared frontend lifecycle for route, locale, busy, and stylesheet ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';

// Store the game-owned resource domain used by every visible and accessible string.
const DOMAIN = 'games/craps';
// Store the additive frozen-v1 API root once so endpoint construction cannot drift.
const API_ROOT = '/api/v1/games/craps';
// Store the number of decorative frames shown before the authoritative server dice.
export const COSMETIC_FRAME_COUNT = 4;
// Store the spacing between cosmetic frames for normal-motion presentation.
export const ROLL_FRAME_DELAY_MS = 110;
// Store the compatibility bet list used until the state endpoint returns metadata.
const DEFAULT_BET_TYPES = Object.freeze(['pass_line', 'dont_pass']);
// Store CSS-grid positions for code-native die pips without special-font glyphs.
const PIP_POSITIONS = Object.freeze({ 1: ['mc'], 2: ['tr', 'bl'], 3: ['tr', 'mc', 'bl'], 4: ['tl', 'tr', 'bl', 'br'], 5: ['tl', 'tr', 'mc', 'bl', 'br'], 6: ['tl', 'ml', 'bl', 'tr', 'mr', 'br'] });

// Store the latest session-bound backend state for reload-safe rendering.
let gameState = { active_round: null, recent_rounds: [] };
// Store API-provided wager types while retaining a compatible initial control list.
let betTypes = [...DEFAULT_BET_TYPES];
// Store the locally selected wager type before the next round starts.
let selectedBetType = DEFAULT_BET_TYPES[0];
// Store the locally entered play-token wager before the next round starts.
let wager = 5;
// Store the last committed bet type and wager so one click can repeat the opening bet.
let lastBet = null;
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
// Retain an unresolved start identity so an ambiguous retry cannot duplicate a wager.
let pendingStartRequestId = null;
// Retain an unresolved roll identity so an ambiguous retry cannot roll twice.
let pendingRollRequestId = null;

// Return one stable retry identity through an injectable UUID source.
export function createClientRequestId(action, randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Restrict identities to the two public atomic action families.
  if (!['start', 'roll'].includes(action)) throw new RangeError('action must be start or roll');
  // Require a secure UUID source in production while permitting deterministic tests.
  if (typeof randomUUID !== 'function') throw new Error('a secure UUID generator is required');
  // Prefix the opaque UUID without embedding player information.
  return `craps-${action}-${randomUUID()}`;
}

// Centralize route, locale, action, and external stylesheet ownership while preserving strict action ids.
const lifecycle = createGameLifecycle({
  domain: DOMAIN, // Load only the Craps locale domain for each mount.
  requestPrefix: 'craps', // Preserve a stable lifecycle namespace for diagnostics.
  stylesheet: { id: 'craps-game-styles', href: '/games/craps.css' }, // Reuse one external stylesheet across remounts.
});
// Reuse lifecycle-owned translation lookup throughout markup and feedback.
const { tx } = lifecycle;
// Bind late state, request, and timer work to the exact active route session.
let routeSession = null;

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
  return { state: gameState, betTypes, selectedBetType, wager, displayedRound, displayedRoll, visibleDice, busyAction, presentationPhase, errorKey, reducedMotionActive, repeatable: lastBet };
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
  return `<section class="panel control-rail craps-control" tabindex="0" role="region" aria-label="${safe(translate('controls.aria'))}"><h2>${safe(translate('controls.title'))}</h2><label class="craps-field" for="craps-bet-type"><span>${safe(translate('controls.betType'))}</span><select id="craps-bet-type" data-testid="craps-bet-type"${configurationDisabled ? ' disabled' : ''}>${options}</select></label><label class="craps-field" for="craps-wager"><span>${safe(translate('controls.wager'))}</span><input id="craps-wager" data-testid="craps-wager" type="number" min="0.01" max="100000" step="0.01" inputmode="decimal" value="${safe(amount)}"${configurationDisabled ? ' disabled' : ''}></label><button type="button" class="craps-primary" data-action="${action}" data-testid="craps-${action}"${model.busyAction ? ' disabled' : ''}>${safe(translate(actionKey))}</button>${action === 'start' ? `<button type="button" class="craps-repeat" data-action="repeat" data-testid="craps-repeat"${model.busyAction || !model.repeatable ? ' disabled' : ''}>${safe(translate('controls.repeat'))}</button>` : ''}<p class="craps-retry-hint">${safe(translate('controls.retryHint'))}</p><p class="craps-error" data-testid="craps-error" aria-live="polite">${model.errorKey ? safe(translate(model.errorKey)) : ''}</p></section>`;
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
  const root = lifecycle.root(); // Resolve the currently owned outlet before painting.
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
  // Bind the one-click repeat that re-starts a round with the previous bet.
  root.querySelector('[data-action="repeat"]')?.addEventListener('click', repeat);
}

// Require exact session, outlet, and timer ownership before accepting late work.
function ownsRoute(session, mountedRoot, activeScope) {
  // Compare every route-owned identity rather than trusting DOM presence alone.
  return routeSession === session && lifecycle.root() === mountedRoot && motionScope === activeScope;
}

// Load reload-safe state for the authenticated session and repaint the route.
async function load(session, mountedRoot, activeScope) {
  // Fetch the standard state payload without sending any caller-selected player id.
  let payload = await api(`${API_ROOT}/state`);
  // Stop a late initial-state response from repainting another route.
  if (!ownsRoute(session, mountedRoot, activeScope)) return false;
  // Apply player-scoped state and contract metadata.
  applyPayload(payload);
  // Select an interrupted settlement using only persisted server state.
  const recovery = pendingSettlementRecovery(gameState);
  // Replay the exact terminal roll identity without cosmetic motion or a new UUID.
  if (recovery) {
    // Start protected recovery so a transient failure does not hide reload-safe state.
    try {
      // Ask the public roll action to complete or replay the pending settlement.
      payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(recovery.round_id)}/rolls`, { request_id: recovery.request_id });
      // Stop when navigation or remount replaced this recovery owner.
      if (!ownsRoute(session, mountedRoot, activeScope)) return false;
      // Apply the recovered settlement and standard state payload.
      applyPayload(payload);
    // Preserve the stored round and expose localized retry guidance on recovery failure.
    } catch (error) {
      // Stop when navigation or remount already released route ownership.
      if (!ownsRoute(session, mountedRoot, activeScope)) return false;
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
  // Recover a repeatable opening bet from the newest round so repeat survives a reload.
  const recovered = gameState.recent_rounds?.slice(-1)[0];
  // Restore the repeatable bet type and wager only when a prior round records them.
  if (recovered && recovered.bet_type && recovered.wager) lastBet = { bet_type: recovered.bet_type, wager: recovered.wager };
  // Render only after state and locale resources are ready.
  render();
  return true; // Report that this route accepted the complete state load.
}

// Start one wagered round with a retry identity retained across ambiguous failures.
// Start a fresh round re-using the previous bet type and wager with one click.
async function repeat() {
  // Ignore repeat while an action is busy, a round is active, or no prior bet exists.
  if (lifecycle.isBusy() || gameState.active_round || !lastBet) return;
  // Restore the previous bet type into local state and the mounted control.
  selectedBetType = lastBet.bet_type;
  // Restore the previous wager into local state and the mounted control.
  wager = lastBet.wager;
  // Reflect the restored bet type on the select so startRound re-reads it.
  const betTypeField = lifecycle.root()?.querySelector('#craps-bet-type');
  // Apply the restored bet type value when the control is present.
  if (betTypeField) betTypeField.value = selectedBetType;
  // Reflect the restored wager on the input so startRound re-reads it.
  const wagerField = lifecycle.root()?.querySelector('#craps-wager');
  // Apply the restored wager value when the control is present.
  if (wagerField) wagerField.value = wager;
  // Fire the shared start path with the restored opening bet.
  await startRound();
}

async function startRound() {
  // Ignore overlapping or stale start events.
  if (lifecycle.isBusy() || gameState.active_round) return;
  const mountedRoot = lifecycle.root(); // Capture the active outlet before reading controls.
  const activeScope = motionScope; // Capture timer ownership across the request.
  const session = routeSession; // Capture exact route-session ownership across the request.
  // Ignore stale events after teardown or remount.
  if (!mountedRoot || !activeScope || !ownsRoute(session, mountedRoot, activeScope)) return;
  // Read the latest form values before rerender replaces the controls.
  selectedBetType = mountedRoot.querySelector('#craps-bet-type')?.value || selectedBetType;
  // Normalize the current wager from the semantic number input without accepting a stale fallback.
  const candidateWager = Number(mountedRoot.querySelector('#craps-wager')?.value);
  // Reject out-of-contract range or precision before creating an action identity.
  if (!isValidWager(candidateWager)) { errorKey = 'errors.wagerRequired'; render(); return; }
  // Commit the validated payload value only after all OpenAPI amount checks pass.
  wager = candidateWager;
  // Reuse an unresolved identity until the server confirms or recovers the debit.
  pendingStartRequestId = pendingStartRequestId || createClientRequestId('start');
  // Lock controls in their stable positions while the request is in flight.
  busyAction = 'start';
  // Reserve shared action ownership before contacting the endpoint.
  lifecycle.setBusy(true);
  // Clear prior localized feedback before the new attempt.
  errorKey = null;
  // Render the disabled primary action and understandable phase.
  render();
  // Start protected API handling so failures keep the retry identity.
  try {
    // Submit only the contract fields; session middleware owns player resolution.
    const payload = await post(`${API_ROOT}/rounds`, { request_id: pendingStartRequestId, bet_type: selectedBetType, wager });
    // Discard a response that completed after route or scope replacement.
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
    // Apply the committed player-scoped round and state payload.
    applyPayload(payload);
    // Remember the committed opening bet so the next round can repeat it with one click.
    lastBet = { bet_type: selectedBetType, wager };
    // Clear the identity only after the server response proves recovery.
    pendingStartRequestId = null;
    // Reset stale dice before the new come-out roll.
    displayedRoll = null;
    // Clear transient presentation faces from the prior round.
    visibleDice = null;
    // Release the action lock after the wager is confirmed.
    busyAction = null;
    // Release shared action ownership after acknowledgement.
    lifecycle.setBusy(false);
    // Render the active come-out round.
    render();
    // Refresh the shared wallet without turning a confirmed debit into an action failure.
    await refreshBalance().catch(() => {});
  // Convert failures into localized route-owned guidance without losing retry safety.
  } catch (error) {
    // Ignore failures delivered after this route lost ownership.
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
    // Release the action lock while retaining pendingStartRequestId.
    busyAction = null;
    // Release shared action ownership while retaining the retry identity.
    lifecycle.setBusy(false);
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
  if (lifecycle.isBusy() || !activeRound || activeRound.phase === 'settled') return;
  // Reuse an unresolved identity until the server confirms this exact roll.
  pendingRollRequestId = pendingRollRequestId || createClientRequestId('roll');
  // Capture this route outlet so late network work cannot repaint another screen.
  const mountedRoot = lifecycle.root();
  // Capture the current disposable scope so remounts invalidate this action.
  const activeScope = motionScope;
  // Capture exact route-session ownership across network and presentation callbacks.
  const session = routeSession;
  // Ignore stale events after teardown or remount.
  if (!mountedRoot || !activeScope || !ownsRoute(session, mountedRoot, activeScope)) return;
  // Cancel any abandoned decorative callbacks from an earlier presentation.
  activeScope.cancelAll();
  // Lock the one atomic action before contacting the ledger-backed endpoint.
  busyAction = 'roll';
  // Reserve shared atomic-action ownership.
  lifecycle.setBusy(true);
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
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
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
        if (!ownsRoute(session, mountedRoot, activeScope)) return; // Ignore callbacks after teardown or remount.
        visibleDice = frame; // Store the current decorative pair for presentation only.
        render(); // Repaint without changing backend-owned round state.
      },
      onSettled: finalDice => { // Reveal and announce the authoritative pair at the final deadline.
        if (!ownsRoute(session, mountedRoot, activeScope)) return; // Ignore settlement presentation after route exit.
        visibleDice = finalDice; // Store only the validated server pair at completion.
        presentationPhase = null; // Return phase ownership to committed backend state.
        busyAction = null; // Unlock the next legal action after presentation settles.
        lifecycle.setBusy(false); // Release shared action ownership after authoritative reveal.
        render(); // Announce the authoritative result through the stable live region.
        refreshBalance().catch(() => {}); // Refresh wallet settlement while containing noncritical shell failures.
      },
    });
  // Convert API failures into localized route-owned guidance without starting another roll.
  } catch (error) {
    // Ignore a failure delivered after route ownership changed.
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
    // Cancel decorative work associated with the failed presentation.
    activeScope.cancelAll();
    // Release controls while retaining pendingRollRequestId for exact replay.
    busyAction = null;
    // Release shared action ownership while retaining the retry identity.
    lifecycle.setBusy(false);
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
    // Clear any repeatable bet so a new session never inherits another player's opening bet.
    lastBet = null;
    // Acquire route, locale, action, and external stylesheet ownership.
    const mounted = await lifecycle.mount(node, render);
    // Stop when navigation replaced this mount during shared initialization.
    if (!mounted) return;
    // Dispose a defensive stale scope before creating this mount's owner.
    motionScope?.dispose();
    // Create one lifecycle-bound scope for every game-owned callback.
    motionScope = createMotionTimerScope();
    // Capture the mount identity across asynchronous locale loading.
    const mountedRoot = lifecycle.root();
    // Capture the scope identity across asynchronous initialization.
    const activeScope = motionScope;
    // Create an exact identity for this route session.
    routeSession = Object.freeze({});
    // Capture session ownership across state and wallet loading.
    const session = routeSession;
    // Read reduced-motion state for the first rendered frame.
    reducedMotionActive = prefersReducedMotion();
    // Load the authenticated player's reload-safe round state.
    await load(session, mountedRoot, activeScope);
    // Stop wallet work when route ownership changed during state loading.
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
    // Refresh the shared wallet without rejecting an otherwise successful mount.
    await refreshBalance().catch(() => {});
  },
  // Release every game-owned lifecycle resource when navigation leaves Craps.
  unmount() {
    // Invalidate late async work before disposing route resources.
    routeSession = null;
    // Permanently cancel pending callbacks and lifecycle listeners.
    motionScope?.dispose();
    // Clear the disposed scope reference for the next mount.
    motionScope = null;
    // Release outlet, locale, stylesheet, and shared action ownership.
    lifecycle.unmount();
    // Release the local action lock without discarding unresolved retry identities.
    busyAction = null;
    // Clear decorative presentation state owned by the inactive route.
    presentationPhase = null;
    // Clear cosmetic dice so remount restores only server state.
    visibleDice = null;
    // Clear the repeatable opening bet so the next session starts fresh.
    lastBet = null;
  },
};
