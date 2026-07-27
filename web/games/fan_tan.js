// Implement the catalog-integrated Fan-Tan route for GitHub issue #137.
// Import the standard API helpers so requests retain the shared success/error envelope.
import { api, post } from '../core/api.js';
// Import shared UI helpers for safe markup, feedback, and wallet refresh.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the merged motion scope so every counting timer has lifecycle cleanup.
import { createMotionTimerScope } from '../core/motion.js';
// Import game-domain localization and locale-change subscription helpers.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';

// Store the lazy-loaded resource domain owned by this game.
const GAME_DOMAIN = 'games/fan_tan';
// Store the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'fan-tan-styles';
// Store the decorative counting duration resolved through the shared motion scope.
export const COUNT_DURATION_MS = 900;
// Define compact game-owned styles without modifying the shared stylesheet.
const ROUTE_CSS = [
  '.fan-tan{display:grid;gap:12px;min-height:100%;color:var(--text,#f5ead6);}', // Establish a stable route-local surface.
  '.fan-tan__header{display:flex;align-items:end;justify-content:space-between;gap:16px;padding:4px 2px;}', // Keep title and phase compact above the stage.
  '.fan-tan__header h1{margin:0;color:var(--gold,#f2c55c);font-size:clamp(30px,4vw,52px);}', // Make the game title the first hierarchy level.
  '.fan-tan__phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;background:var(--panel-strong);}', // Reserve a concise player-facing phase chip.
  '.fan-tan__layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(420px,1.8fr) minmax(220px,.72fr);gap:14px;min-height:0;}', // Keep the counting stage visually dominant on desktop.
  '.fan-tan__panel{padding:16px;border:1px solid var(--gold);border-radius:18px;background:var(--panel-strong);}', // Separate controls, stage, and results with governed surfaces.
  '.fan-tan__controls{display:grid;align-content:start;gap:12px;}', // Keep wagering actions in one predictable control rail.
  '.fan-tan__bet{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:8px;align-items:center;}', // Align each localized residue with its wager amount.
  '.fan-tan__bet input{min-height:44px;min-width:0;}', // Preserve keyboard and touch usability for amount inputs.
  '.fan-tan__play{min-height:46px;border:0;border-radius:12px;color:white;background:#a71922;font-weight:800;}', // Use the shared red primary-action convention.
  '.fan-tan__play:disabled{opacity:.58;cursor:not-allowed;}', // Keep unavailable action state readable.
  '.fan-tan__stage{display:grid;place-items:center;gap:14px;overflow:hidden;}', // Center the counting pile without nested scroll.
  '.fan-tan__tray{width:min(64vh,540px);max-width:100%;aspect-ratio:1.4;display:grid;place-items:center;border:2px solid var(--gold);border-radius:18px;background:radial-gradient(circle at center,var(--felt2),var(--bg));}', // Draw the count tray as the dominant stage.
  '.fan-tan__beans{display:grid;grid-template-columns:repeat(8,18px);gap:8px;justify-content:center;align-content:center;}', // Render a compact code-native counted pile.
  '.fan-tan__bean{width:18px;height:18px;border-radius:50%;background:#f2c55c;box-shadow:0 2px 0 #8d681f;}', // Draw one reliable count marker without image assets.
  '.fan-tan__bean[data-residue="true"]{background:#ffefad;outline:3px solid #a71922;}', // Mark the final residue beyond color alone through outline.
  '.fan-tan__result{display:grid;gap:5px;text-align:center;min-height:64px;}', // Reserve result space so settlement never shifts the stage.
  '.fan-tan__data{display:grid;align-content:start;gap:12px;}', // Keep paytable and recent results distinct from controls.
  '.fan-tan__payrow,.fan-tan__history-row{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.08);}', // Align compact game data rows.
  '.fan-tan__history{max-height:260px;overflow:auto;scrollbar-width:thin;}', // Give the data rail one intentional keyboard-focusable scroll region.
  '.fan-tan__error{min-height:20px;color:var(--bad);}', // Reserve localized validation and API error feedback.
  '@media(prefers-reduced-motion:reduce){.fan-tan__bean{transition:none;}}', // Respect platform reduced-motion preferences for counting presentation.
  '@media(max-width:1200px){.fan-tan__layout{grid-template-columns:1fr;}.fan-tan__controls{order:1}.fan-tan__stage{order:2}.fan-tan__data{order:3}.fan-tan__tray{width:min(80vw,520px);}}', // Stack control, stage, then data at the shared responsive transition.
  '@media(max-width:560px){.fan-tan__header{align-items:start;flex-direction:column}.fan-tan__panel{padding:12px}.fan-tan__bet{grid-template-columns:minmax(0,1fr) 84px}.fan-tan__beans{grid-template-columns:repeat(6,16px);gap:7px}.fan-tan__bean{width:16px;height:16px;}}', // Preserve complete controls and no horizontal overflow on mobile.
].join(''); // Combine route-local CSS chunks into one injected style payload.

// Store the current route outlet while this lazy game is mounted.
let root = null;
// Store the latest backend-owned state payload.
let gameState = { outcomes: [], state: { recent_rounds: [] }, rules: {} };
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
// Store whether the current count presentation used reduced motion.
let reducedMotionActive = false;
// Store the locale subscription cleanup callback.
let localeUnsubscribe = null;

// Resolve one game-owned string from the active locale dictionary.
const tx = (key, params = {}) => t(key, params, GAME_DOMAIN);
// Escape one localized string before inserting it into route markup.
const text = (key, params = {}) => safe(tx(key, params));

// Generate one retry-safe action identity using the browser cryptographic UUID provider.
export function createActionId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require cryptographic UUID support so accidental double-submission identities never collide.
  if (typeof randomUUID !== 'function') throw new Error('A secure UUID generator is required for Fan-Tan rounds');
  // Prefix the UUID for readable action diagnostics without including player information.
  return `ft-${randomUUID()}`;
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
  // Release the browser action identity.
  pendingRequestId = null;
  // Release the immutable wager snapshot.
  pendingPayload = null;
  // Release the authenticated owner paired with the action.
  pendingPlayerId = null;
}

// Resolve the idempotency payload for one play, reusing the retained identity only for the identical player and wagers. (issue #261)
function resolvePlayPayload(wagerMap) {
  // Read the authenticated player that would own this action.
  const playerId = sessionPlayerId();
  // Reuse the frozen identity only when the same player resubmits the exact same immutable wager map after an ambiguous failure.
  if (pendingPayload && pendingPlayerId && pendingPlayerId === playerId && wagerSignature(pendingPayload.wagers) === wagerSignature(wagerMap)) {
    // Return the retained frozen payload for a safe exactly-once replay.
    return pendingPayload;
  }
  // Mint a fresh identity for a new intent before any network work.
  pendingRequestId = createActionId();
  // Bind the authenticated owner so a later session cannot inherit this identity.
  pendingPlayerId = playerId;
  // Freeze the exact request body so a retry can never resend a different wager map.
  pendingPayload = Object.freeze({ action_id: pendingRequestId, wagers: Object.freeze({ ...wagerMap }) });
  // Return the frozen payload for the request.
  return pendingPayload;
}

// Reconcile an unresolved identity against authoritative history and current ownership. (issue #261)
function reconcilePendingRequest() {
  // Read only authoritative recent settlements echoed with their action id from the current state payload.
  const recentRounds = gameState.state?.recent_rounds || [];
  // Clear a pending identity already proven settled by server history.
  if (pendingRequestId && recentRounds.some(round => round?.action_id === pendingRequestId)) {
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

// Schedule the counting reveal through a caller-owned reduced-motion timer scope.
export function scheduleCount({ timerScope, onSettled, duration = COUNT_DURATION_MS }) {
  // Require the shared timer-scope interface rather than allocating an unmanaged timer.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require a callback so animation completion has an explicit owner.
  if (typeof onSettled !== 'function') throw new TypeError('onSettled must be callable');
  // Schedule through the scope so route exit and reduced motion retain lifecycle semantics.
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

// Format a play-token amount without any real-money or currency symbol.
function tokenAmount(value, translate = tx) {
  // Format through the active document locale while keeping two-decimal ledger precision.
  const number = Number(value || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Append the localized play-token unit owned by this game domain.
  return translate('units.playTokens', { amount: number });
}

// Return localized markup for every residue wager input.
function wagerControlsHtml(translate = tx) {
  // Render controls from backend metadata while retaining stable residue ordering.
  return (gameState.outcomes || []).map(outcome => `<label class="fan-tan__bet"><span>${safe(translate('residue.label', { residue: outcome.residue }))} <small>${safe(translate('odds.net', { odds: outcome.net_odds }))}</small></span><input type="number" min="0" step="1" inputmode="decimal" data-wager="${safe(outcome.id)}" value="${safe(activeWagers()[outcome.id] || '')}" aria-label="${safe(translate('wager.input', { residue: outcome.residue }))}"></label>`).join('');
}

// Return localized paytable rows from the immutable backend catalog.
function paytableHtml(translate = tx) {
  // Show net odds and return multiplier so the simulator profile is explicit.
  return (gameState.outcomes || []).map(outcome => `<div class="fan-tan__payrow"><span>${safe(translate('residue.label', { residue: outcome.residue }))}</span><span>${safe(translate('paytable.row', { odds: outcome.net_odds, multiplier: outcome.return_multiplier }))}</span></div>`).join('');
}

// Return bounded recent-round rows with no nested controls.
function historyHtml(translate = tx) {
  // Read newest history first for the player-owned data rail.
  const rows = [...(gameState.state?.recent_rounds || [])].reverse();
  // Return the localized empty state until a real settlement exists.
  if (!rows.length) return `<p>${safe(translate('history.empty'))}</p>`;
  // Render stable residue and net values for each settled round.
  return rows.map(round => `<div class="fan-tan__history-row"><span>${safe(translate('history.residue', { residue: round.residue }))}</span><span>${safe(translate('history.net', { amount: tokenAmount(round.net, translate) }))}</span></div>`).join('');
}

// Return code-native beans for the visible pile and final residue.
function beanHtml() {
  // Use a compact preview count so the stage remains dense at all viewports.
  const count = latestRound ? Math.min(latestRound.pile_count, 48) : 32;
  // Resolve the highlighted residue count only after a settlement exists.
  const residue = latestRound ? Number(latestRound.residue) : 0;
  // Render beans with the final visible residue markers highlighted.
  return Array.from({ length: count }, (_, index) => `<span class="fan-tan__bean" data-residue="${latestRound && index >= count - residue}" aria-hidden="true"></span>`).join('');
}

// Return the complete route markup using only localized visible strings.
export function viewMarkup({ translate = tx } = {}) {
  // Resolve and escape through an injected translator for deterministic locale tests.
  const translated = (key, params = {}) => safe(translate(key, params));
  // Resolve the visible settled residue or a localized waiting label.
  const residueLabel = latestRound ? translated('result.residue', { residue: latestRound.residue }) : translated('result.waiting');
  // Resolve net result detail only when a backend settlement exists.
  const resultDetail = latestRound ? translated('result.net', { amount: tokenAmount(latestRound.net, translate) }) : translated('result.hint');
  // Return a three-zone layout aligned with the visual-design standard.
  return `<section class="fan-tan" data-testid="fan-tan"><header class="fan-tan__header"><div><h1>${translated('title')}</h1><p>${translated('subtitle')}</p></div><span class="fan-tan__phase" data-testid="fan-tan-phase">${translated(phase)}</span></header><div class="fan-tan__layout"><section class="fan-tan__panel fan-tan__controls" aria-label="${translated('controls.aria')}"><h2>${translated('controls.title')}</h2><p>${translated('controls.help')}</p>${wagerControlsHtml(translate)}<button class="fan-tan__play" data-play type="button"${playPending ? ' disabled' : ''}>${translated(playPending ? 'action.counting' : 'action.play')}</button><p class="fan-tan__error" data-error aria-live="polite"></p></section><section class="fan-tan__panel fan-tan__stage" aria-label="${translated('stage.aria')}"><div class="fan-tan__tray" data-reduced-motion="${reducedMotionActive}"><div class="fan-tan__beans">${beanHtml()}</div></div><div class="fan-tan__result" aria-live="polite"><strong>${residueLabel}</strong><span>${resultDetail}</span></div></section><aside class="fan-tan__panel fan-tan__data" aria-label="${translated('data.aria')}"><section><h2>${translated('paytable.title')}</h2>${paytableHtml(translate)}</section><section><h2>${translated('history.title')}</h2><div class="fan-tan__history" tabindex="0" aria-label="${translated('history.aria')}">${historyHtml(translate)}</div></section></aside></div></section>`;
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
  root.querySelector('[data-play]').onclick = play;
}

// Load session-bound state from the additive v1 game endpoint.
// Return the wager map currently in effect, locking to the immutable pending snapshot after an ambiguous failure. (issue #261)
function activeWagers() {
  // Prefer the frozen pending payload so a retry cannot submit a changed intent under the same identity.
  return pendingPayload?.wagers || wagers;
}

async function load() {
  // Fetch only the authenticated player's state; shared routing supplies the binding.
  gameState = await api('/api/v1/games/fan-tan/state');
  // Reconcile any unresolved retry identity against authoritative history and current ownership before rendering. (issue #261)
  reconcilePendingRequest();
  // Restore the latest real result without inventing a default residue.
  latestRound = gameState.state?.recent_rounds?.length ? gameState.state.recent_rounds[gameState.state.recent_rounds.length - 1] : null;
  // Render after rules and history resources are available.
  render();
}

// Submit one complete wager map and present the settled backend result.
async function play() {
  // Ignore duplicate clicks while the existing action identity is in flight.
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
  phase = 'phase.counting';
  // Cancel any prior presentation callback before scheduling a new result.
  motionScope.cancelAll();
  // Render the disabled action and stable counting phase.
  render();
  // Capture the current mount so a completed request cannot repaint a later route.
  const mountedRoot = root;
  // Capture the current timer scope so teardown can invalidate this presentation path.
  const activeScope = motionScope;
  // Start protected API work so failures restore controls without leaked timers.
  try {
    // Resolve the frozen idempotency payload so a retry replays the exact same identity and immutable body. (issue #261)
    const command = resolvePlayPayload(activeWagers());
    // Send the retained action identity with its frozen wager snapshot, never the live mutable controls.
    const response = await post('/api/v1/games/fan-tan/rounds', { action_id: command.action_id, wagers: command.wagers });
    // Clear the retained identity only after the server has confirmed this round.
    clearPendingRequest();
    // Stop presentation when shell navigation unmounted or replaced this route during the request.
    if (root !== mountedRoot || motionScope !== activeScope) return;
    // Store the authoritative settlement before starting decorative presentation.
    latestRound = response.round;
    // Treat a platform reduced-motion preference as immediate counting evidence.
    reducedMotionActive = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
    // Schedule the final reveal through the shared motion scope.
    scheduleCount({ timerScope: activeScope, onSettled: async () => { phase = 'phase.settled'; playPending = false; gameState = await api('/api/v1/games/fan-tan/state'); render(); await refreshBalance(); } });
    // Rerender the highlighted residue while keeping result text reserved.
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
    // Rerender before writing into the reserved error region.
    render();
    // Show a localized game-specific failure message.
    root.querySelector('[data-error]').textContent = tx('error.playFailed');
    // Also use the shared non-blocking feedback surface.
    toast(tx('error.playFailed'), 'error');
  }
}

// Export the catalog-declared game module interface consumed after #77 integration.
export const FanTanGame = {
  // Expose the stable catalog identifier without hard-coded visible copy.
  id: 'fan_tan',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the current route outlet before asynchronous initialization.
    root = node;
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
    // Permanently cancel all pending count callbacks and lifecycle listeners.
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
    // Release any unresolved retry identity so a later mount or a different session cannot inherit it; remount reloads authoritative state. (issue #261)
    clearPendingRequest();
  },
};
