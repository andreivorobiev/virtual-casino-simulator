// Implement the isolated Crown and Anchor route for GitHub issue #133.
// Import the frozen API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';
// Import issue #97 dice primitives for deterministic reduced-motion presentation.
import { createSeededRandom, rollDice } from '../core/dice.js';
// Import issue #97 motion scope so every dice reveal timer has lifecycle cleanup.
import { createMotionTimerScope } from '../core/motion.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/crown_and_anchor';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'crown-and-anchor-styles';
// Store stable symbol order matching the backend rules profile.
export const SYMBOL_IDS = Object.freeze(['crown', 'anchor', 'heart', 'diamond', 'club', 'spade']);
// Store decorative dice reveal duration resolved by the shared motion scope.
export const DICE_REVEAL_MS = 900;
// Define compact game-owned styles without modifying the shared stylesheet.
const ROUTE_CSS = [
  '.crown-anchor{display:grid;gap:12px;min-height:100%;color:var(--text,#f5ead6);}', // Establish a stable route-local surface.
  '.crown-anchor__header{display:flex;align-items:end;justify-content:space-between;gap:16px;padding:4px 2px;}', // Keep title and phase compact.
  '.crown-anchor__header h1{margin:0;color:var(--gold,#f2c55c);font-size:clamp(30px,4vw,52px);}', // Make the title primary.
  '.crown-anchor__phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;background:rgba(20,10,34,.92);}', // Reserve a status chip.
  '.crown-anchor__layout{display:grid;grid-template-columns:minmax(240px,.76fr) minmax(420px,1.6fr) minmax(240px,.78fr);gap:14px;min-height:0;}', // Keep the dice table dominant.
  '.crown-anchor__panel{padding:16px;border:1px solid var(--border);border-radius:8px;background:rgba(20,10,34,.92);}', // Frame functional panels.
  '.crown-anchor__controls{display:grid;align-content:start;gap:12px;}', // Keep wagering actions in one rail.
  '.crown-anchor__bet{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:8px;align-items:center;}', // Align symbol and amount.
  '.crown-anchor__bet input{min-height:42px;min-width:0;}', // Preserve touch usability.
  '.crown-anchor__play{min-height:46px;border:0;border-radius:8px;color:white;background:#9f1f2e;font-weight:800;}', // Use a strong primary action.
  '.crown-anchor__play:disabled{opacity:.58;cursor:not-allowed;}', // Keep disabled state readable.
  '.crown-anchor__repeat{min-height:46px;border:1px solid #ffd780;border-radius:8px;color:#ffd780;background:transparent;font-weight:800;}', // Offer a secondary repeat action distinct from the primary play button.
  '.crown-anchor__repeat:disabled{opacity:.5;cursor:not-allowed;}', // Keep the repeat disabled state readable.
  '.crown-anchor__stage{display:grid;grid-template-rows:auto auto auto;align-content:center;gap:16px;min-width:0;overflow:hidden;}', // Center complete bounded theater rows without allowing intrinsic width to escape the panel.
  '.crown-anchor__dice{display:grid;grid-template-columns:repeat(3,minmax(74px,1fr));gap:12px;width:100%;min-width:0;}', // Reserve three stable dice slots inside the stage width.
  '.crown-anchor__die{display:grid;place-items:center;aspect-ratio:1;border:2px solid #f2c55c;border-radius:8px;background:#f8f0d5;color:#15211d;font-size:clamp(22px,4vw,44px);font-weight:900;transition:transform .9s ease;}', // Render symbol dice as text.
  '.crown-anchor__die[data-rolling="true"]{transform:rotate(14deg) scale(1.03);}', // Add small decorative motion.
  '.crown-anchor__die[data-reduced-motion="true"]{transition:none;transform:none;}', // Remove decorative motion when requested.
  '.crown-anchor__table{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;width:100%;min-width:0;}', // Show all six symbol cells inside the stage width.
  '.crown-anchor__cell{display:grid;gap:4px;min-height:88px;padding:10px;border:1px solid rgba(255,255,255,.14);border-radius:8px;background:rgba(255,255,255,.05);}', // Keep table cells scannable.
  '.crown-anchor__result{display:grid;gap:5px;width:100%;min-width:0;text-align:center;min-height:54px;}', // Reserve a bounded result row.
  '.crown-anchor__data{display:grid;align-content:start;gap:12px;}', // Keep data distinct.
  '.crown-anchor__payrow,.crown-anchor__history-row{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.08);}', // Align compact rows.
  '.crown-anchor__history{max-height:260px;overflow:auto;scrollbar-width:thin;}', // Provide one scroll region.
  '.crown-anchor__error{min-height:20px;color:#ffb9b9;}', // Reserve error text.
  '@media(max-width:1200px){.crown-anchor{min-height:0}.crown-anchor__layout{grid-template-columns:minmax(0,1fr);}.crown-anchor__controls{order:1}.crown-anchor__stage{order:2;align-content:start;overflow:visible}.crown-anchor__data{order:3}}', // Let tablet document flow size the complete stage instead of centering and clipping it inside a forced route track.
  '@media(max-width:560px){.crown-anchor__header{align-items:start;flex-direction:column}.crown-anchor__panel{padding:12px}.crown-anchor__bet{grid-template-columns:minmax(0,1fr) 84px}.crown-anchor__table{grid-template-columns:repeat(2,minmax(0,1fr));}.crown-anchor__dice{grid-template-columns:repeat(3,minmax(54px,1fr));}}', // Preserve mobile fit.
].join(''); // Combine route-local CSS.

// Store the current route outlet while this lazy game is mounted.
let root = null;
// Store the latest backend-owned state payload.
let gameState = { symbols: [], recent_rounds: [] };
// Store locally edited wagers until one atomic round is submitted.
let wagers = {};
// Store the current player-facing phase key.
let phase = 'phase.ready';
// Store the latest settled round for the stage result.
let latestRound = null;
// Store a request guard so duplicate clicks cannot create new action identities.
let playPending = false;
// Store the disposable timer scope owned by the current route mount.
let motionScope = null;
// Store whether the current reveal collapsed to reduced motion for CSS evidence.
let reducedMotionActive = false;
// Store whether dice are currently in the decorative reveal state.
let diceRolling = false;
// Store the last committed multi-symbol wager map so one click can repeat the identical bet.
let lastBet = null;
// Store the locale subscription cleanup callback.
let localeUnsubscribe = null;

// Resolve one game-owned string from the active locale dictionary.
const tx = (key, params = {}) => t(key, params, GAME_DOMAIN);

// Generate one deterministic three-die preview from issue #97 primitives.
export function previewFaces(seed) {
  // Create a repeatable random source from the supplied action or round seed.
  const random = createSeededRandom(seed);
  // Roll three six-sided dice through the shared primitive.
  return rollDice({ count: 3, sides: 6, random });
}

// Generate one retry-safe client identity using the browser cryptographic UUID provider.
export function createClientRequestId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require cryptographic UUID support so accidental double-submission identities do not collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Crown and Anchor rounds');
  // Prefix the UUID for readable action diagnostics without including player information.
  return `caa-${randomUUID()}`;
}

// Retain one unresolved idempotency identity across an ambiguous request failure. (issue #261)
let pendingRequestId = null;
// Retain the exact immutable wager payload paired with the unresolved identity so a retry cannot resend a different body. (issue #261)
let pendingPayload = null;
// Retain the authenticated player that owned the unresolved identity so a later session cannot inherit it. (issue #261)
let pendingPlayerId = null;

// Read the authenticated player id from the shared shell session without trusting caller-controlled fields.
function sessionPlayerId() {
  // Return the current-user player id published by the shell, or null before authentication resolves.
  return globalThis.CasinoCurrentUser?.player?.player_id || null;
}

// Return a stable canonical signature for one wager map so changed intent is detectable.
function wagerSignature(source = {}) {
  // Sort keys so equivalent wager maps always produce one identical signature.
  return JSON.stringify(Object.keys(source || {}).sort().map(key => [key, source[key]]));
}

// Report whether a structured API error definitively resolves the pending action so it is safe to discard.
function isDefinitiveRejection(error) {
  // Treat validation, balance, auth, route, and conflict errors as non-ambiguous server responses.
  return ['VALIDATION_ERROR', 'INSUFFICIENT_FUNDS', 'UNAUTHORIZED', 'FORBIDDEN', 'NOT_FOUND', 'CONFLICT'].includes(error?.code);
}

// Clear the unresolved request only after the backend proves its outcome or ownership changes.
function clearPendingRequest() {
  // Release the browser request identity.
  pendingRequestId = null;
  // Release the immutable wager snapshot.
  pendingPayload = null;
  // Release the authenticated owner paired with the request.
  pendingPlayerId = null;
}

// Resolve the idempotency payload for one round, reusing the retained identity only for the identical player and wagers. (issue #261)
function resolveRoundPayload(wagerMap) {
  // Read the authenticated player that would own this request.
  const playerId = sessionPlayerId();
  // Reuse the frozen identity only when the same player resubmits the exact same immutable wager map after an ambiguous failure.
  if (pendingPayload && pendingPlayerId && pendingPlayerId === playerId && wagerSignature(pendingPayload.wagers) === wagerSignature(wagerMap)) {
    // Return the retained frozen payload for a safe exactly-once replay.
    return pendingPayload;
  }
  // Mint a fresh identity for a new intent before any network work.
  pendingRequestId = createClientRequestId();
  // Bind the authenticated owner so a later session cannot inherit this identity.
  pendingPlayerId = playerId;
  // Freeze the exact request body so a retry can never resend a different wager map.
  pendingPayload = Object.freeze({ client_request_id: pendingRequestId, wagers: Object.freeze({ ...wagerMap }) });
  // Return the frozen payload for the request.
  return pendingPayload;
}

// Reconcile an unresolved identity against authoritative history and current ownership. (issue #261)
function reconcilePendingRequest() {
  // Read only authoritative recent settlements echoed with their client request id from the current state payload.
  const recentRounds = gameState.recent_rounds || [];
  // Clear a pending identity already proven settled by server history.
  if (pendingRequestId && recentRounds.some(round => round?.client_request_id === pendingRequestId)) {
    // Treat authoritative reconciliation as acknowledgement of the committed round.
    clearPendingRequest();
    // Stop after clearing the resolved identity.
    return;
  }
  // Clear a pending identity that belongs to a different authenticated player in this tab.
  if (pendingPlayerId && sessionPlayerId() && pendingPlayerId !== sessionPlayerId()) {
    // Remove cross-session retry ownership without resending it.
    clearPendingRequest();
  }
}

// Return the wager map currently in effect, locking to the immutable pending snapshot after an ambiguous failure. (issue #261)
function activeWagers() {
  // Prefer the frozen pending payload so a retry cannot submit a changed intent under the same identity.
  return pendingPayload?.wagers || wagers;
}

// Schedule the dice reveal through a caller-owned reduced-motion timer scope.
export function scheduleDiceReveal({ timerScope, onSettled, duration = DICE_REVEAL_MS }) {
  // Require the shared timer-scope interface rather than allocating unmanaged timers.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require a callback so animation completion has an explicit owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Schedule through the scope so route exit and reduced motion share lifecycle cleanup.
  return timerScope.schedule(onSettled, duration);
}

// Install the game-owned style block once per document.
function ensureStyles() {
  // Reuse an existing route-local style node after remount.
  if (document.getElementById(STYLE_ID)) return;
  // Create the style node through the platform DOM API.
  const style = document.createElement('style');
  // Assign the stable id used by later mounts.
  style.id = STYLE_ID;
  // Apply the game-owned CSS without touching the shared stylesheet.
  style.textContent = ROUTE_CSS;
  // Attach styles before first paint.
  document.head.append(style);
}

// Format a play-token amount without a real-money or currency symbol.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale while keeping two-decimal ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit owned by this game domain.
  return translate('units.playTokens', { amount: number });
}

// Resolve the symbol shown on one die face.
function symbolForFace(face, translate = tx) {
  // Convert the one-based die face into the canonical symbol id.
  const symbol = SYMBOL_IDS[Number(face) - 1] || 'crown';
  // Return the localized symbol label.
  return translate(`symbol.${symbol}`);
}

// Return localized markup for every wager input.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend metadata while retaining canonical table ordering.
  return (gameState.symbols || []).map(symbol => `<label class="crown-anchor__bet"><span>${safe(translate(`symbol.${symbol.id}`))}</span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(symbol.id)}" value="${safe(activeWagers()[symbol.id] || '')}" aria-label="${safe(translate('wager.input', { symbol: translate(`symbol.${symbol.id}`) }))}"></label>`).join('');
}

// Return localized paytable rows from the fixed hit-count profile.
function paytableHtml(translate = tx) {
  // Show the transparent return table for one, two, and three matching dice.
  return [1, 2, 3].map(hits => `<div class="crown-anchor__payrow"><span>${safe(translate('paytable.hits', { hits }))}</span><span>${safe(translate('paytable.odds', { odds: hits }))}</span></div>`).join('');
}

// Return a compact symbol table with current hit counts.
function symbolTableHtml(translate = tx) {
  // Read latest hit counts or default every symbol to zero.
  const counts = latestRound?.hit_counts || {};
  // Render all six symbols as keyboard-scannable table cells.
  return SYMBOL_IDS.map(symbol => `<div class="crown-anchor__cell" data-symbol="${safe(symbol)}"><strong>${safe(translate(`symbol.${symbol}`))}</strong><span>${safe(translate('table.hits', { hits: counts[symbol] || 0 }))}</span></div>`).join('');
}

// Return bounded recent-round rows with no nested controls.
function historyHtml(translate = tx) {
  // Read newest history first for the player-owned data rail.
  const rows = [...(gameState.recent_rounds || [])].reverse();
  // Return the localized empty state until a real settlement exists.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render stable dice symbols and net values for each settled round.
  return rows.map(round => `<div class="crown-anchor__history-row"><span>${safe(round.symbols.map(symbol => translate(`symbol.${symbol}`)).join(' / '))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return the complete route markup using only localized visible strings.
export function viewMarkup({ translate = tx, repeatable = lastBet } = {}) {
  // Resolve and escape through an injected translator for deterministic locale tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Disable the one-click repeat until a prior settled bet exists and no request or retry is active.
  const repeatDisabled = playPending || Boolean(pendingRequestId) || !repeatable;
  // Resolve the visible dice faces or deterministic placeholder preview.
  const faces = latestRound?.faces || previewFaces('crown-and-anchor-waiting');
  // Resolve net result detail only when a backend settlement exists.
  const resultDetail = latestRound ? translated('result.net', { amount: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Render the three fixed dice slots with accessible labels.
  const diceHtml = faces.map((face, index) => `<div class="crown-anchor__die" data-die="${index}" data-rolling="${diceRolling}" data-reduced-motion="${reducedMotionActive}" aria-label="${safe(translate('die.aria', { index: index + 1, symbol: symbolForFace(face, translate) }))}">${safe(symbolForFace(face, translate))}</div>`).join('');
  // Return a three-zone layout aligned with the visual design standard.
  return `<section class="crown-anchor" data-testid="crown-and-anchor"><header class="crown-anchor__header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="crown-anchor__phase" data-testid="crown-and-anchor-phase">${translated(phase)}</span></header><div class="crown-anchor__layout"><section class="crown-anchor__panel crown-anchor__controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="crown-anchor__play" data-play type="button"${playPending ? ' disabled' : ''}>${translated(playPending ? 'action.rolling' : 'action.play')}</button><button class="crown-anchor__repeat" data-action="repeat" type="button"${repeatDisabled ? ' disabled' : ''}>${translated('controls.repeat')}</button><p class="crown-anchor__error" data-error aria-live="polite"></p></section><section class="crown-anchor__panel crown-anchor__stage" aria-label="${translated('stage.aria')}"><div class="crown-anchor__dice" aria-live="polite">${diceHtml}</div><div class="crown-anchor__table">${symbolTableHtml(translate)}</div><div class="crown-anchor__result" aria-live="polite"><strong>${translated(latestRound ? 'result.settled' : 'result.waiting')}</strong><span>${resultDetail}</span></div></section><aside class="crown-anchor__panel crown-anchor__data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="crown-anchor__history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
}

// Render the route and reconnect its game-owned inputs after DOM replacement.
function render() {
  // Stop stale async callbacks after route unmount.
  if (!root) return;
  // Replace the isolated route atomically so phase and stage regions stay stable.
  root.innerHTML = viewMarkup();
  // Wire every wager input to local unsent state.
  root.querySelectorAll('[data-wager]').forEach(input => { input.oninput = () => { const amount = Number(input.value); if (Number.isFinite(amount) && amount > 0) wagers[input.dataset.wager] = amount; else delete wagers[input.dataset.wager]; }; });
  // Wire the one atomic play action.
  root.querySelector('[data-play]').onclick = playRound;
  // Wire the one-click repeat that re-fires the previous multi-symbol bet.
  root.querySelector('[data-action="repeat"]').onclick = repeat;
}

// Re-apply the last committed wager map and re-fire one round without a timer.
async function repeat() {
  // Ignore repeat while a request is in flight, an ambiguous retry is unresolved, or no prior bet exists.
  if (playPending || pendingRequestId || !lastBet) return;
  // Restore the entire previous multi-symbol wager map into the local controls.
  wagers = { ...lastBet.wagers };
  // Fire the shared exactly-once play action with the restored bet.
  await playRound();
}

// Load session-bound state from the additive v1 game endpoint.
async function load() {
  // Fetch only the authenticated player's state; shared request binding owns identity.
  gameState = await api('/api/v1/games/crown-and-anchor/state');
  // Reconcile any unresolved retry identity against authoritative history and current ownership before rendering. (issue #261)
  reconcilePendingRequest();
  // Restore the latest real result without inventing a settled round.
  latestRound = gameState.recent_rounds?.length ? gameState.recent_rounds[gameState.recent_rounds.length - 1] : null;
  // Recover a repeatable wager map from the newest settled round so repeat survives a reload.
  lastBet = latestRound?.wagers && Object.keys(latestRound.wagers).length ? { wagers: { ...latestRound.wagers } } : null;
  // Render after rules and history resources are available.
  render();
}

// Submit one complete wager map and present the settled backend result.
async function playRound() {
  // Ignore duplicate clicks while the existing client identity is in flight.
  if (playPending) return;
  // Require at least one positive wager (locked to the pending snapshot after an ambiguous failure) before contacting the ledger endpoint. (issue #261)
  if (!Object.keys(activeWagers()).length) {
    // Show localized player guidance in the reserved error region.
    root.querySelector('[data-error]').textContent = tx('error.wagerRequired');
    // Stop without creating an idempotency identity or ledger request.
    return;
  }
  // Guard controls before generating and sending one atomic action.
  playPending = true;
  // Move the phase to an understandable in-progress state.
  phase = 'phase.rolling';
  // Mark dice as rolling for a small decorative transition.
  diceRolling = true;
  // Cancel any prior presentation callback before scheduling a new result.
  motionScope.cancelAll();
  // Render the disabled action and stable rolling phase.
  render();
  // Capture the current mount so a completed request cannot repaint a later route.
  const mountedRoot = root;
  // Capture the current timer scope so teardown can invalidate this presentation path.
  const activeScope = motionScope;
  // Start protected API work so failures restore controls without leaked timers.
  try {
    // Resolve the frozen idempotency payload so a retry replays the exact same identity and immutable body. (issue #261)
    const command = resolveRoundPayload(activeWagers());
    // Send the retained client identity with its frozen wager snapshot, never the live mutable controls.
    const response = await post('/api/v1/games/crown-and-anchor/rounds', { client_request_id: command.client_request_id, wagers: command.wagers });
    // Clear the retained identity only after the server has confirmed this round.
    clearPendingRequest();
    // Stop presentation when shell navigation unmounted or replaced this route during the request.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Store the authoritative settlement before starting decorative presentation.
    latestRound = response.round;
    // Remember the exact settled multi-symbol wager map so the next round can repeat it with one click.
    if (latestRound?.wagers && Object.keys(latestRound.wagers).length) lastBet = { wagers: { ...latestRound.wagers } };
    // Treat platform reduced motion as route-local CSS evidence.
    reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
    // Schedule the final reveal through the shared motion scope.
    scheduleDiceReveal({ timerScope: activeScope, onSettled: async () => { phase = 'phase.settled'; playPending = false; diceRolling = false; gameState = await api('/api/v1/games/crown-and-anchor/state'); render(); await refreshBalance(); } });
    // Render the committed dice while the reveal state owns the timing.
    render();
  // Handle API or validation failures with localized feedback and restored controls.
  } catch (error) {
    // Ignore late failures after navigation because teardown already restored route ownership.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Discard the pending identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearPendingRequest();
    // Restore the ready phase after a failed atomic request.
    phase = 'phase.ready';
    // Re-enable controls for a corrected request.
    playPending = false;
    // Stop the decorative dice state after failure.
    diceRolling = false;
    // Rerender before writing into the reserved error region.
    render();
    // Show a localized game-specific failure message.
    root.querySelector('[data-error]').textContent = tx('error.playFailed');
    // Also use the shared non-blocking feedback surface.
    toast(tx('error.playFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #77 integration.
export const CrownAndAnchorGame = {
  // Expose the stable catalog identifier without hard-coded visible copy.
  id: 'crown_and_anchor',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet before asynchronous initialization.
    root = node;
    // Reset the repeatable bet so a fresh mount never inherits a prior session's wager map.
    lastBet = null;
    // Install game-owned styles without changing shared CSS.
    ensureStyles();
    // Create one lifecycle-bound timer scope for this mount.
    motionScope = createMotionTimerScope();
    // Load both locales through the game-owned lazy domain before visible render.
    await initI18n({ domains: [GAME_DOMAIN] });
    // Repaint localized strings without losing local wagers or backend state.
    localeUnsubscribe = onLocaleChange(() => render());
    // Load session-bound state and render the first frame.
    await load();
  },
  // Release timers and subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Permanently cancel all pending dice callbacks and lifecycle listeners.
    motionScope?.dispose();
    // Clear the disposed scope reference for the next mount.
    motionScope = null;
    // Remove the locale subscription when the route was initialized.
    localeUnsubscribe?.();
    // Clear the subscription reference for the next mount.
    localeUnsubscribe = null;
    // Clear the outlet so stale async work cannot repaint another route.
    root = null;
    // Reset the in-flight guard because teardown cancelled presentation.
    playPending = false;
    // Reset dice reveal state for the next mount.
    diceRolling = false;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
    // Release any unresolved retry identity so a later mount or a different session cannot inherit it; remount reloads authoritative state. (issue #261)
    clearPendingRequest();
  },
};
