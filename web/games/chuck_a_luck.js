// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the isolated Chuck-a-Luck browser route for GitHub issue #89.
// Import the standard envelope-aware API helpers so session cookies own every request.
import { api, post } from '../core/api.js';
// Import the #97 deterministic dice helpers for decorative, non-authoritative preview faces.
import { createSeededRandom, rollDice } from '../core/dice.js';
// Import locale-aware number formatting while shared lifecycle owns route translations.
import { formatNumber } from '../core/i18n.js';
// Import the shared frontend lifecycle for mount, locale, action, and stylesheet ownership.
import { createGameLifecycle } from '../core/game_lifecycle.js';
// Import the #97 lifecycle timer scope and platform reduced-motion query.
import { createMotionTimerScope, prefersReducedMotion } from '../core/motion.js';
// Import shared escaping, feedback, and authenticated-wallet refresh helpers.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';

// Store the game-owned lazy locale domain used by every visible string.
const DOMAIN = 'games/chuck_a_luck';
// Store the frozen-v1 additive API root once for state and roll actions.
const API_ROOT = '/api/v1/games/chuck-a-luck';
// Store one tab-scoped retry record so an ambiguous response can survive reload.
const PENDING_STORAGE_KEY = 'casino.chuck_a_luck.pending.v1';
// Store the normal decorative reveal duration consumed by the shared timer scope.
export const ROLL_REVEAL_MS = 720;
// Store the smallest wager accepted by the two-decimal play-token ledger.
const MIN_WAGER = 0.01;
// Store the game-engine upper bound for one face wager.
const MAX_WAGER = 1_000_000;
// Store the six canonical backend wager identifiers in stable face order.
export const BET_IDS = Object.freeze(['one', 'two', 'three', 'four', 'five', 'six']);
// Store a neutral initial dice tray that does not claim an authoritative result.
const INITIAL_DICE = Object.freeze([1, 1, 1]);
// Map each die face to code-native pip grid positions.
const PIP_POSITIONS = Object.freeze({
  1: Object.freeze([5]), // Center the single pip.
  2: Object.freeze([1, 9]), // Place two pips on opposing corners.
  3: Object.freeze([1, 5, 9]), // Add the center pip to the diagonal pair.
  4: Object.freeze([1, 3, 7, 9]), // Fill every corner for four.
  5: Object.freeze([1, 3, 5, 7, 9]), // Add a center pip to the four corners.
  6: Object.freeze([1, 3, 4, 6, 7, 9]), // Fill two vertical columns for six.
});
// Store the latest server-owned game state for reload-safe rendering.
let gameState = { recent_rounds: [] };
// Store the current authenticated player summary only for local retry-record scoping.
let player = null;
// Store the server-authored six-face payout catalog.
let betCatalog = [];
// Store the latest authoritative settled round.
let latestRound = null;
// Store locally edited wager amounts until an atomic roll is submitted.
let wagers = {};
// Retain the last settled wager map so one click can re-place the identical roll.
let lastBet = null;
// Store the current machine-readable UI phase independently of localization.
let phase = 'ready';
// Store decorative faces separately from authoritative server dice.
let previewDice = [...INITIAL_DICE];
// Store the current reduced-motion preference for evidence attributes.
let reducedMotionActive = false;
// Store one unresolved idempotency identity across an ambiguous request failure.
let pendingRequestId = null;
// Store the exact immutable retry payload paired with the unresolved identity.
let pendingPayload = null;
// Store the authenticated player that owned the unresolved retry identity.
let pendingPlayerId = null;
// Store one localized error key for the reserved feedback region.
let errorKey = null;
// Store the disposable #97 timer scope owned by this route mount.
let motionScope = null;
// Store a fallback sequence only for environments without cryptographic UUID support.
let requestCounter = 0;

// Generate one retry-safe browser action identity through an injectable UUID seam.
export function createRequestId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Prefer the platform cryptographic UUID implementation when available.
  if (typeof randomUUID === 'function') return `cal-${randomUUID()}`;
  // Advance the fallback counter so same-millisecond requests remain distinct.
  requestCounter += 1;
  // Return a readable game-prefixed fallback identity for constrained test browsers.
  return `cal-${Date.now().toString(36)}-${requestCounter.toString(36)}`;
}

// Centralize route, locale, stylesheet, and action ownership while preserving exact request identities.
const lifecycle = createGameLifecycle({
  domain: DOMAIN, // Load only the Chuck-a-Luck locale domain for each mount.
  requestPrefix: 'cal', // Preserve a stable lifecycle namespace for action diagnostics.
  stylesheet: { id: 'chuck-a-luck-styles', href: '/games/chuck_a_luck.css' }, // Own one external stylesheet across remounts.
  uuidFactory: () => createRequestId(), // Preserve the frozen cal-prefixed UUID and fallback format.
});
// Reuse lifecycle-owned translation lookup throughout markup and feedback.
const { tx } = lifecycle;
// Bind late async work to the exact active route session.
let routeSession = null;

// Produce deterministic non-authoritative preview dice from one stable action seed.
export function createDecorativeDice(seed) {
  // Reject an empty seed so decorative frames cannot become accidentally nondeterministic.
  if (seed === undefined || seed === null || String(seed).length === 0) throw new TypeError('seed is required');
  // Build the #97 deterministic random source from the request or round identity.
  const random = createSeededRandom(String(seed));
  // Return exactly three bounded decorative faces without affecting server settlement.
  return Object.freeze(rollDice({ count: 3, sides: 6, random }));
}

// Schedule the authoritative reveal through a caller-owned #97 timer scope.
export function scheduleReveal({ timerScope, onReveal, duration = ROLL_REVEAL_MS }) {
  // Require the shared scope interface so no unmanaged timer can survive navigation.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require an explicit reveal callback before allocating timer ownership.
  if (typeof onReveal !== 'function') throw new TypeError('onReveal must be callable');
  // Delegate reduced-motion duration resolution and cancellation to the shared primitive.
  return timerScope.schedule(onReveal, duration);
}

// Normalize one possible wager amount into a positive finite number or zero.
function positiveAmount(value) {
  // Coerce the input exactly once for predictable validation.
  const amount = Number(value);
  // Reject non-finite values before ledger-precision normalization.
  if (!Number.isFinite(amount)) return 0;
  // Match the backend's two-decimal half-up play-token precision.
  const normalized = Math.round((amount + Number.EPSILON) * 100) / 100;
  // Preserve only wagers inside the documented game-engine range.
  return normalized >= MIN_WAGER && normalized <= MAX_WAGER ? normalized : 0;
}

// Report whether a structured API response proves the pending action is safe to release.
export function isDefinitiveRollRejection(error) {
  // Treat client, authentication, balance, route, and conflict errors as non-ambiguous responses.
  return ['VALIDATION_ERROR', 'INSUFFICIENT_FUNDS', 'UNAUTHORIZED', 'FORBIDDEN', 'NOT_FOUND', 'CONFLICT'].includes(error?.code);
}

// Return a canonical wager map containing only the six known positive targets.
function normalizeWagers(source = {}) {
  const normalized = {}; // Build a new object so pending payloads never share mutable state.
  // Inspect every canonical target in stable face order.
  for (const id of BET_IDS) {
    const amount = positiveAmount(source?.[id]); // Normalize the candidate wager once.
    if (amount > 0) normalized[id] = amount; // Retain only valid positive amounts.
  }
  return normalized; // Return the safe request and rendering shape.
}

// Return the wager map currently represented by controls or an unresolved retry.
function activeWagers() {
  // Freeze UI configuration to the exact pending payload after an ambiguous failure.
  return pendingPayload?.wagers || wagers;
}

// Calculate the aggregate wager represented by the active controls.
function activeWagerTotal() {
  // Sum only normalized values so invalid input text cannot affect the preview.
  return Object.values(normalizeWagers(activeWagers())).reduce((total, amount) => total + amount, 0);
}

// Return a valid three-face array or the neutral initial tray.
function normalizedDice(candidate) {
  // Normalize only exact three-die arrays with bounded integer faces.
  if (Array.isArray(candidate) && candidate.length === 3 && candidate.every(face => Number.isInteger(Number(face)) && Number(face) >= 1 && Number(face) <= 6)) return candidate.map(Number);
  // Avoid showing malformed API values as a claimed result.
  return [...INITIAL_DICE];
}

// Return the faces appropriate for the current presentation phase.
function visibleDice() {
  // Show deterministic decorative values only while the authoritative result is concealed.
  if (phase === 'rolling') return normalizedDice(previewDice);
  // Show the server-owned final dice after settlement or route restoration.
  if (latestRound) return normalizedDice(latestRound.dice);
  // Show a neutral tray before the first roll.
  return [...INITIAL_DICE];
}

// Return one server catalog entry with a stable local fallback.
function catalogEntry(id) {
  // Find the server-authored entry for this canonical wager id.
  const found = betCatalog.find(entry => entry?.id === id);
  // Return server metadata when available.
  if (found) return found;
  // Build the documented 1x/2x/3x fallback for pre-state and focused markup tests.
  return { id, face: BET_IDS.indexOf(id) + 1, payouts: [{ matches: 1, net_multiplier: 1 }, { matches: 2, net_multiplier: 2 }, { matches: 3, net_multiplier: 3 }] };
}

// Format a play-token value through the active locale without a currency glyph.
function tokenAmount(value, translate = tx, { signed = false } = {}) {
  const numeric = Number(value || 0); // Normalize ledger decimals before formatting.
  const prefix = signed && numeric > 0 ? '+' : ''; // Add an explicit positive sign only for net results.
  const amount = `${prefix}${formatNumber(numeric, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; // Format exact display precision.
  return translate('units.playTokens', { amount }); // Attach localized fake-token terminology.
}

// Read a tab-scoped pending request without letting storage failures break gameplay.
function readPendingRecord() {
  // Start protected access because privacy modes can disable session storage.
  try {
    const raw = globalThis.sessionStorage?.getItem(PENDING_STORAGE_KEY); // Read only the game-owned retry key.
    return raw ? JSON.parse(raw) : null; // Parse an existing record or report no pending work.
  } catch (_) { // Handle unavailable or malformed tab storage without affecting gameplay.
    return null; // Continue without persistence when storage is unavailable or malformed.
  }
}

// Persist the unresolved request identity and immutable wagers for safe reload retry.
function writePendingRecord() {
  // Skip storage when no unresolved payload exists.
  if (!pendingPayload) return;
  // Start protected access because storage availability is not a gameplay requirement.
  try {
    const record = { request_id: pendingPayload.request_id, wagers: pendingPayload.wagers, player_id: pendingPlayerId }; // Scope retry metadata without sending identity to the API.
    globalThis.sessionStorage?.setItem(PENDING_STORAGE_KEY, JSON.stringify(record)); // Store only retry metadata, never balance or authoritative game state.
  } catch (_) { // Ignore disabled tab storage because in-memory retry ownership remains active.
    // Continue with the retained in-memory pending action.
  }
}

// Remove persisted retry metadata after acknowledgement or safe reconciliation.
function removePendingRecord() {
  // Start protected access so cleanup remains harmless in restricted browsers.
  try {
    globalThis.sessionStorage?.removeItem(PENDING_STORAGE_KEY); // Delete only this game's retry record.
  } catch (_) { // Ignore disabled tab storage after clearing in-memory retry ownership.
    // Continue because storage cleanup is a best-effort privacy safeguard.
  }
}

// Clear the unresolved request only after the backend proves its outcome.
function clearPendingRequest() {
  pendingRequestId = null; // Release the browser action identity.
  pendingPayload = null; // Release the immutable wager snapshot.
  pendingPlayerId = null; // Release the authenticated owner paired with the action.
  removePendingRecord(); // Remove the reload retry copy.
}

// Restore or reconcile an unresolved request against authenticated server history.
function restorePendingRequest() {
  const recentRounds = Array.isArray(gameState.recent_rounds) ? gameState.recent_rounds : []; // Read only authoritative recent settlements.
  const persisted = readPendingRecord(); // Read the player-scoped tab record once for consistent reconciliation.
  const currentId = pendingRequestId || persisted?.request_id; // Resolve the in-memory or persisted candidate identity.
  // Clear a pending identity already proven settled by server history.
  if (currentId && recentRounds.some(round => round?.request_id === currentId)) {
    clearPendingRequest(); // Treat state reconciliation as acknowledgement.
    return; // Stop before restoring stale wagers.
  }
  const stored = pendingPayload ? { request_id: pendingPayload.request_id, wagers: pendingPayload.wagers, player_id: pendingPlayerId || persisted?.player_id || null } : persisted; // Prefer live immutable action data while retaining its original owner.
  // Stop when no structurally valid retry record exists.
  if (!stored || typeof stored.request_id !== 'string' || !stored.request_id || !Object.keys(normalizeWagers(stored.wagers)).length) return;
  // Reject a record belonging to a different authenticated player in the same tab.
  if (stored.player_id && player?.player_id && stored.player_id !== player.player_id) {
    clearPendingRequest(); // Remove cross-session retry metadata without sending it.
    return; // Leave the new player's controls empty.
  }
  pendingRequestId = stored.request_id; // Restore the exact unresolved identity.
  pendingPlayerId = stored.player_id || player?.player_id || null; // Retain the original owner for future session checks.
  const restoredWagers = Object.freeze(normalizeWagers(stored.wagers)); // Freeze a new canonical wager snapshot.
  pendingPayload = Object.freeze({ request_id: pendingRequestId, wagers: restoredWagers }); // Restore the exact retry body.
  wagers = { ...restoredWagers }; // Mirror the locked values into visible controls.
}

// Return localized match-payout copy for one catalog entry.
function payoutSequence(entry, translate = tx) {
  const payouts = Array.isArray(entry?.payouts) ? entry.payouts : []; // Read the backend-authored match profile.
  // Resolve every payout through game-owned visible copy.
  return payouts.map(payout => translate('paytable.payout', { matches: payout.matches, multiplier: payout.net_multiplier })).join(' / ');
}

// Return the six stable wager controls backed by the server catalog.
function wagerControlsHtml(translate = tx) {
  const locked = lifecycle.isBusy() || Boolean(pendingPayload); // Lock amounts while committed or awaiting exact retry.
  const values = activeWagers(); // Read one stable wager snapshot for this render.
  // Render every canonical wager target with the required focused-test selector.
  return BET_IDS.map(id => {
    const entry = catalogEntry(id); // Resolve face and payouts from the server catalog.
    const face = Number(entry.face || BET_IDS.indexOf(id) + 1); // Preserve canonical face order when metadata is incomplete.
    const label = translate('wager.target', { face }); // Resolve the visible target label.
    const payout = payoutSequence(entry, translate); // Resolve localized match odds.
    const value = values[id] ?? ''; // Preserve the active amount across rerenders.
    return `<label class="cal-wager"><span class="cal-wager-copy"><strong>${safe(label)}</strong><small>${safe(payout)}</small></span><input type="number" min="${MIN_WAGER}" max="${MAX_WAGER}" step="0.01" inputmode="decimal" data-wager="${safe(id)}" value="${safe(value)}" aria-label="${safe(translate('wager.input', { face }))}"${locked ? ' disabled' : ''}></label>`; // Return semantic localized input markup.
  }).join(''); // Combine the six canonical controls into one stable fieldset payload.
}

// Return code-native accessible markup for one die face.
function dieHtml(face, index, translate = tx) {
  const validFace = normalizedDice([face, face, face])[0]; // Reuse bounded face normalization.
  const pips = PIP_POSITIONS[validFace].map(position => `<span class="cal-pip cal-pip--${position}" aria-hidden="true"></span>`).join(''); // Draw only the required pips.
  const rollingClass = phase === 'rolling' ? ' is-rolling' : ''; // Mark decorative motion without changing semantics.
  const labelKey = phase === 'rolling' ? 'dice.previewLabel' : 'dice.faceLabel'; // Distinguish preview and authoritative accessible names.
  const label = translate(labelKey, { position: index + 1, face: validFace }); // Resolve the complete accessible label.
  return `<div class="cal-die${rollingClass}" data-die data-face="${validFace}" role="img" aria-label="${safe(label)}">${pips}</div>`; // Expose the required stable die selector and server/preview face.
}

// Return the dominant dice tray for the current phase.
function diceTrayHtml(translate = tx) {
  const dice = visibleDice(); // Read either deterministic preview or authoritative final faces.
  const items = dice.map((face, index) => dieHtml(face, index, translate)).join(''); // Render exactly three accessible dice.
  return `<div class="cal-dice-tray" role="group" aria-label="${safe(translate('dice.group'))}">${items}</div>`; // Group the dice under one localized accessible name.
}

// Return the current player-facing result summary in a fixed region.
function resultHtml(translate = tx) {
  // Describe the untouched table before the first roll.
  if (!latestRound && phase === 'ready') return `<div class="cal-result" role="status" aria-live="polite"><strong>${safe(translate('result.readyTitle'))}</strong><span>${safe(translate('result.readyBody'))}</span></div>`;
  // Keep authoritative dice concealed while decorative motion runs.
  if (phase === 'rolling') return `<div class="cal-result" role="status" aria-live="polite"><strong>${safe(translate('result.rollingTitle'))}</strong><span>${safe(translate('result.rollingBody'))}</span></div>`;
  const net = Number(latestRound?.net || 0); // Read the server-settled aggregate net result.
  const hasMatch = Array.isArray(latestRound?.settlements) && latestRound.settlements.some(row => row?.won); // Distinguish a matched face from aggregate profit or loss.
  const titleKey = !hasMatch ? 'result.lossTitle' : net === 0 ? 'result.pushTitle' : 'result.winTitle'; // Keep matched-face copy truthful even when other face wagers create an aggregate loss.
  const triple = latestRound?.is_triple ? `<span>${safe(translate('result.triple'))}</span>` : ''; // Call out a triple without changing payout semantics.
  return `<div class="cal-result" role="status" aria-live="polite"><strong>${safe(translate(titleKey))}</strong><span>${safe(translate('result.net', { amount: tokenAmount(net, translate, { signed: true }) }))}</span>${triple}</div>`; // Present the authoritative settlement only after reveal.
}

// Return semantic paytable rows from the backend-authored catalog.
function paytableHtml(translate = tx) {
  // Render all six canonical targets in face order.
  const rows = BET_IDS.map(id => {
    const entry = catalogEntry(id); // Resolve the server profile for this face.
    return `<tr><th scope="row">${safe(translate('wager.target', { face: entry.face }))}</th><td>${safe(payoutSequence(entry, translate))}</td></tr>`; // Keep each payout sequence localized.
  }).join(''); // Combine every canonical face into the complete table body.
  return `<table class="cal-paytable"><thead><tr><th>${safe(translate('paytable.face'))}</th><th>${safe(translate('paytable.returns'))}</th></tr></thead><tbody>${rows}</tbody></table>`; // Return the complete accessible table.
}

// Return bounded authoritative recent-round rows without exposing internal ids.
function historyHtml(translate = tx) {
  const rounds = Array.isArray(gameState.recent_rounds) ? [...gameState.recent_rounds].reverse().slice(0, 10) : []; // Show newest settlements first.
  // Return localized empty-state copy before any settled round exists.
  if (!rounds.length) return `<p class="cal-help">${safe(translate('history.empty'))}</p>`;
  // Render server dice and signed net values without a nested scroll surface.
  return rounds.map(round => {
    const dice = normalizedDice(round.dice).join(' · '); // Format the three authoritative faces compactly.
    const net = tokenAmount(round.net, translate, { signed: true }); // Format signed fake-token outcome copy.
    const label = translate('history.rowLabel', { dice, net }); // Resolve an accessible row summary.
    return `<div class="cal-history-row" aria-label="${safe(label)}"><span>${safe(translate('history.dice', { dice }))}</span><span>${safe(net)}</span></div>`; // Return one localized history item.
  }).join(''); // Combine the bounded newest-first history into one data-rail payload.
}

// Return the complete localized three-zone route markup for rendering and focused tests.
export function viewMarkup({ translate = tx } = {}) {
  const rolling = lifecycle.isBusy(); // Read shared action ownership once for consistent control state.
  const faces = visibleDice(); // Read the current tray once for total display.
  const displayedTotal = latestRound && phase !== 'rolling' ? Number(latestRound.total ?? faces.reduce((sum, face) => sum + face, 0)) : null; // Show only an authoritative total.
  const totalText = displayedTotal === null ? translate('stage.totalWaiting') : translate('stage.total', { total: displayedTotal }); // Reserve the total chip in every phase.
  const wagerTotal = tokenAmount(activeWagerTotal(), translate); // Format the current aggregate wager.
  const rollDisabled = rolling || activeWagerTotal() <= 0; // Disable duplicate or empty actions.
  const repeatDisabled = rolling || Boolean(pendingPayload) || !lastBet; // Enable one-click repeat only with a prior wager map and no in-flight or unresolved retry.
  const actionKey = rolling ? 'action.rolling' : pendingPayload ? 'action.retry' : 'action.roll'; // Keep retry state explicit after ambiguity.
  const retryNote = pendingPayload ? `<p class="cal-retry-note">${safe(translate('retry.saved'))}</p>` : '<p class="cal-retry-note">&nbsp;</p>'; // Reserve retry guidance without moving controls.
  const visibleError = errorKey ? translate(errorKey) : ''; // Resolve only game-owned failure copy.
  return `<section class="cal-shell" data-testid="chuck-a-luck" data-phase="${safe(phase)}" data-reduced-motion="${reducedMotionActive}"><header class="cal-header"><div><h1>${safe(translate('title'))}</h1><p>${safe(translate('subtitle'))}</p></div><span class="cal-phase" data-testid="chuck-a-luck-phase" role="status" aria-live="polite">${safe(translate(`phase.${phase}`))}</span></header><div class="cal-layout"><aside class="panel control-rail cal-panel cal-controls" aria-label="${safe(translate('controls.aria'))}"><h2>${safe(translate('controls.title'))}</h2><p id="cal-help" class="cal-help">${safe(translate('controls.help'))}</p><fieldset aria-describedby="cal-help"><legend>${safe(translate('controls.wagers'))}</legend>${wagerControlsHtml(translate)}</fieldset><div class="cal-wager-total"><span>${safe(translate('controls.total'))}</span><strong data-wager-total>${safe(wagerTotal)}</strong></div><button type="button" class="cal-roll" data-roll${rollDisabled ? ' disabled' : ''}>${safe(translate(actionKey))}</button><button type="button" class="cal-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(translate('controls.repeat'))}</button>${retryNote}<p class="cal-error" data-error aria-live="polite">${safe(visibleError)}</p></aside><main class="panel game-stage cal-panel cal-stage" aria-label="${safe(translate('stage.aria'))}"><div class="cal-stage-heading"><h2>${safe(translate('stage.title'))}</h2><span class="cal-total-chip">${safe(totalText)}</span></div>${diceTrayHtml(translate)}${resultHtml(translate)}</main><aside class="panel details-drawer cal-panel cal-data" aria-label="${safe(translate('data.aria'))}"><section><h2>${safe(translate('paytable.title'))}</h2><p class="cal-help">${safe(translate('paytable.help'))}</p>${paytableHtml(translate)}</section><section><h2>${safe(translate('history.title'))}</h2><div class="cal-history">${historyHtml(translate)}</div></section></aside></div></section>`; // Return the complete browser surface.
}

// Update one rendered wager total and primary-action availability without replacing focused inputs.
function updateControlPreview() {
  const root = lifecycle.root(); // Resolve the currently owned outlet at event time.
  // Stop when an event fires after route teardown.
  if (!root) return;
  const totalNode = root.querySelector('[data-wager-total]'); // Find the reserved aggregate amount node.
  if (totalNode) totalNode.textContent = tokenAmount(activeWagerTotal()); // Refresh localized fake-token total copy.
  const rollButton = root.querySelector('[data-roll]'); // Find the stable primary action.
  if (rollButton) rollButton.disabled = lifecycle.isBusy() || activeWagerTotal() <= 0; // Enable only valid non-overlapping actions.
}

// Render the route atomically and reconnect game-owned semantic controls.
function render() {
  const root = lifecycle.root(); // Resolve the currently owned outlet before painting.
  // Stop stale async completions after unmount.
  if (!root) return;
  reducedMotionActive = prefersReducedMotion(); // Refresh the platform preference for evidence and CSS state.
  root.innerHTML = viewMarkup(); // Replace only the isolated route outlet.
  // Wire all six focused-test wager inputs to local unsent state.
  root.querySelectorAll('[data-wager]').forEach(input => {
    // Preserve edits without rerendering and disrupting keyboard focus.
    input.oninput = () => {
      const amount = positiveAmount(input.value); // Normalize the current control value.
      if (amount > 0) wagers[input.dataset.wager] = amount; else delete wagers[input.dataset.wager]; // Update only valid canonical local wagers.
      errorKey = null; // Clear stale validation after a corrective edit.
      const errorNode = lifecycle.root()?.querySelector('[data-error]'); // Resolve the current reserved error node.
      if (errorNode) errorNode.textContent = ''; // Clear visible error copy in place.
      updateControlPreview(); // Refresh total and button state without replacing inputs.
    };
  });
  const rollButton = root.querySelector('[data-roll]'); // Resolve the current primary action.
  if (rollButton) rollButton.onclick = roll; // Submit through the one retry-safe public action.
  const repeatButton = root.querySelector('[data-action="repeat"]'); // Resolve the secondary repeat action.
  if (repeatButton) repeatButton.onclick = repeat; // Re-place the last settled wager map with one click.
}

// Apply one authoritative state payload while preserving local unsent wagers.
function applyStatePayload(payload) {
  gameState = payload?.state && typeof payload.state === 'object' ? payload.state : { recent_rounds: [] }; // Store reload-safe server history.
  player = payload?.player || null; // Store authenticated summary only for retry-record scoping.
  betCatalog = Array.isArray(payload?.bet_catalog) ? payload.bet_catalog : []; // Store the six server payout entries.
  const rounds = Array.isArray(gameState.recent_rounds) ? gameState.recent_rounds : []; // Normalize recent history once.
  latestRound = rounds.length ? rounds[rounds.length - 1] : null; // Restore the newest authoritative settlement.
  lastBet = latestRound?.wagers ? { wagers: { ...latestRound.wagers } } : null; // Recover a repeatable wager map so repeat survives a reload.
  phase = latestRound ? 'settled' : 'ready'; // Restore a player-facing phase without replaying animation.
  previewDice = latestRound ? normalizedDice(latestRound.dice) : [...INITIAL_DICE]; // Keep the tray aligned with restored server state.
}

// Load authenticated session-owned state from the additive v1 endpoint.
function ownsRoute(session, mountedRoot, activeScope) {
  // Require the same lifecycle session, outlet, and timer scope before accepting late work.
  return routeSession === session && lifecycle.root() === mountedRoot && motionScope === activeScope;
}

// Load authenticated session-owned state from the additive v1 endpoint.
async function loadState(session, mountedRoot, activeScope) {
  const payload = await api(`${API_ROOT}/state`); // Read state without any caller-selected player id.
  // Stop a late response from repainting a different route or mount.
  if (!ownsRoute(session, mountedRoot, activeScope)) return false;
  applyStatePayload(payload); // Store server game, player, catalog, and history data.
  restorePendingRequest(); // Reconcile any ambiguous tab-scoped action against server history.
  render(); // Paint the complete localized route after resources and state exist.
  return true; // Report that this mount accepted the response.
}

// Submit one complete six-target wager map through a retained idempotency identity.
async function roll() {
  // Ignore duplicate events while one atomic request or reveal is active.
  if (lifecycle.isBusy()) return;
  const mountedRoot = lifecycle.root(); // Capture the active outlet before validating or mutating action state.
  const activeScope = motionScope; // Capture timer ownership before the request starts.
  const session = routeSession; // Capture exact route-session ownership across every asynchronous boundary.
  // Ignore stale control events after navigation or mount replacement.
  if (!mountedRoot || !activeScope || !ownsRoute(session, mountedRoot, activeScope)) return;
  const requestWagers = normalizeWagers(pendingPayload?.wagers || wagers); // Reuse an immutable retry wager map or snapshot current controls.
  // Reject an empty action without creating a request identity.
  if (!Object.keys(requestWagers).length) {
    errorKey = 'error.wagerRequired'; // Store localized validation copy.
    render(); // Show feedback in the reserved region.
    return; // Avoid contacting the ledger endpoint.
  }
  // Retain one identity across every retry until the backend acknowledges it.
  pendingRequestId = pendingRequestId || lifecycle.nextRequestId();
  // Pair the retry identity with the authenticated state owner before the request starts.
  pendingPlayerId = pendingPlayerId || player?.player_id || null;
  // Retain the exact immutable wager payload paired with that identity.
  pendingPayload = pendingPayload || Object.freeze({ request_id: pendingRequestId, wagers: Object.freeze({ ...requestWagers }) });
  writePendingRecord(); // Preserve ambiguous-response recovery across a full-page reload.
  lifecycle.setBusy(true); // Lock duplicate input before starting the request.
  phase = 'rolling'; // Publish machine-readable and localized rolling state.
  errorKey = null; // Clear earlier validation or request failures.
  previewDice = [...createDecorativeDice(pendingRequestId)]; // Show only deterministic non-authoritative preview faces.
  activeScope.cancelAll(); // Cancel any abandoned presentation callback from this mount.
  render(); // Paint disabled controls and decorative dice before awaiting I/O.
  // Start protected request handling so ambiguity preserves the exact retry payload.
  try {
    const response = await post(`${API_ROOT}/rolls`, pendingPayload); // Send no caller player id and rely on the standard envelope.
    // Stop presentation when navigation replaced or disposed this mount during I/O.
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
    clearPendingRequest(); // Treat an owned parsed success envelope, including replay, as acknowledgement.
    renderCommittedWagerBalance(response.ledger?.wager); // Show the committed debit before the dice reveal. (LEDGER-031, issue #586)
    gameState = response?.state && typeof response.state === 'object' ? response.state : gameState; // Adopt returned reload-safe history.
    player = response?.player || player; // Adopt the returned authenticated player summary.
    betCatalog = Array.isArray(response?.bet_catalog) ? response.bet_catalog : betCatalog; // Adopt the returned payout catalog.
    latestRound = response?.round || null; // Store the authoritative settled round before reveal.
    lastBet = { wagers: { ...(latestRound?.wagers || requestWagers) } }; // Remember the settled wager map so one click can repeat the same roll.
    const finalDice = normalizedDice(latestRound?.dice); // Read only the three server-authored final faces.
    // Schedule final presentation through reduced-motion-aware route ownership.
    scheduleReveal({ timerScope: activeScope, onReveal: () => {
      // Stop an unusual late callback after mount replacement.
      if (!ownsRoute(session, mountedRoot, activeScope)) return;
      previewDice = finalDice; // Replace decorative faces with authoritative server dice.
      phase = 'settled'; // Publish the final machine-readable phase.
      lifecycle.setBusy(false); // Re-enable a new atomic roll only after reveal.
      render(); // Paint authoritative dice, result, paytable, and history.
      // Refresh the shared authenticated wallet without making it game-owned state.
      refreshBalance().catch(() => {}); // Let a later shell refresh recover without changing the settled game result.
    } }); // Finish the lifecycle-owned authoritative reveal callback.
  // Preserve the exact request identity and payload after any ambiguous failure.
  } catch (error) {
    // Stop a late failure from repainting a different route.
    if (!ownsRoute(session, mountedRoot, activeScope)) return;
    phase = 'ready'; // Return controls to an understandable retry-ready phase.
    lifecycle.setBusy(false); // Allow the exact retained payload to be retried.
    const definitiveRejection = isDefinitiveRollRejection(error); // Separate confirmed rejection from an ambiguous interrupted response.
    if (definitiveRejection) clearPendingRequest(); // Unlock wagers only when the server proves no retry of this action should occur.
    errorKey = definitiveRejection ? 'error.rollRejected' : 'error.rollFailed'; // Use localized copy that accurately describes retry ownership.
    render(); // Show locked wagers, retry action, and reserved feedback.
    toast(tx(errorKey)); // Mirror the localized error in shared non-blocking feedback.
  }
}

// Re-place the last settled wager map and re-fire one roll without a timer.
async function repeat() {
  // Ignore repeat while rolling, holding an unresolved retry, or without a prior wager map.
  if (lifecycle.isBusy() || pendingPayload || !lastBet) return;
  // Restore the full previous wager map into the local control state.
  wagers = { ...lastBet.wagers };
  // Fire the shared retry-safe roll action with the restored wagers.
  await roll();
}

// Export the catalog-discovered lazy module contract expected by shared integration.
export const ChuckALuckGame = {
  id: 'chuck_a_luck', // Expose the stable module identifier without visible hard-coded copy.
  label: '', // Leave presentation labels to the game descriptor and locale domain.
  // Mount resources and authenticated state into the shared route outlet.
  async mount(node) {
    lastBet = null; // Reset the repeatable wager map so a new mount never inherits a stale one before load reconciles history.
    const mounted = await lifecycle.mount(node, render); // Acquire route, locale, and external stylesheet ownership.
    // Stop when navigation replaced this mount during shared initialization.
    if (!mounted) return;
    motionScope = createMotionTimerScope(); // Create lifecycle-bound reduced-motion timer ownership.
    routeSession = Object.freeze({}); // Create an exact identity for this route session.
    const session = routeSession; // Capture the session across state loading.
    const mountedRoot = lifecycle.root(); // Capture this mount across state loading.
    const activeScope = motionScope; // Capture this timer scope across locale and state loading.
    // Load state while retaining a localized route if the endpoint is temporarily unavailable.
    try {
      await loadState(session, mountedRoot, activeScope); // Restore recent rounds, player, and payout catalog.
    } catch (_) { // Convert state-load failures into owned localized route feedback.
      // Stop a late failure from repainting a different route.
      if (!ownsRoute(session, mountedRoot, activeScope)) return;
      phase = 'ready'; // Keep the route in an understandable non-action phase.
      lifecycle.setBusy(false); // Ensure controls are not left as in-flight.
      errorKey = 'error.stateFailed'; // Resolve failure through owned EN/RU copy.
      restorePendingRequest(); // Preserve any exact retry record even while state is unavailable.
      render(); // Render a recoverable localized surface.
      toast(tx('error.stateFailed')); // Mirror the localized load error through shared feedback.
    }
  },
  // Release all game-owned lifecycle resources whenever navigation leaves the route.
  unmount() {
    routeSession = null; // Invalidate late async work before disposing route resources.
    motionScope?.dispose(); // Cancel pending reveal callbacks and lifecycle listeners.
    motionScope = null; // Clear the disposed scope for a future mount.
    lifecycle.unmount(); // Release outlet, locale, stylesheet, and shared busy ownership.
    phase = 'ready'; // Reset transient presentation before the next authoritative load.
    errorKey = null; // Clear route-local visible feedback.
    gameState = { recent_rounds: [] }; // Drop stale server state while inactive.
    player = null; // Drop the inactive authenticated summary.
    betCatalog = []; // Drop the inactive payout catalog.
    latestRound = null; // Require the next mount to restore authoritative state.
    lastBet = null; // Clear the repeatable wager map so the next session starts fresh.
    previewDice = [...INITIAL_DICE]; // Reset decorative presentation only.
  },
};
