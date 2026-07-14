// Implement the isolated Dragon Tiger browser module for GitHub issue #83.

// Import session-bound API helpers without sending a caller-selected player id.
import { api, post } from '../core/api.js';
// Import shared safe-markup, feedback, and authenticated-wallet helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the merged #96 accessible card renderer.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, lookup, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Address the additive frozen-v1 API through one stable root.
const API_ROOT = '/api/v1/games/dragon-tiger';
// Address the game-owned EN/RU resource domain.
const DOMAIN = 'games/dragon_tiger';
// Identify shared card styles so repeated mounts install them once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Identify game-owned styles so repeated mounts remain idempotent.
const GAME_STYLE_ID = 'dragon-tiger-styles';
// Preserve canonical wager ordering across renders and locales.
export const BETS = Object.freeze(['dragon', 'tiger', 'tie']);

// Retain the active route outlet without owning shared shell state.
let root = null;
// Retain a mount identity so late promises cannot repaint another route.
let mountIdentity = null;
// Retain the latest session-bound backend state for reload and locale rendering.
let gameState = { shoe: {}, rules: {}, recent_rounds: [] };
// Retain the locally selected wager target.
let selectedBet = 'dragon';
// Retain the locally selected play-token amount.
let wager = 5;
// Retain request-bound dealing state without allocating a presentation timer.
let dealing = false;
// Block player actions until the initial session-bound snapshot resolves.
let initialLoading = false;
// Retain the complete unresolved request so retries reuse its action id and payload.
let pendingAction = null;
// Retain locale cleanup so unmount releases its subscription.
let unsubscribeLocale = null;

// Resolve one game-owned localized string.
function text(key, params = {}) {
  // Delegate every visible and accessible label to the active game domain.
  return t(key, params, DOMAIN);
}

// Generate one replay-safe action id through an injectable deterministic seam.
export function createActionId(randomUUID = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Require UUID support rather than risk a colliding ledger action identity.
  if (typeof randomUUID !== 'function') throw new Error('secure action identity unavailable');
  // Prefix the opaque UUID for readable game-local diagnostics.
  return `dt-${randomUUID()}`;
}

// Merge GET and POST payloads into the route's stable render state.
export function normalizeStatePayload(payload = {}) {
  // Copy the documented state object without mutating the API response.
  const next = payload.state && typeof payload.state === 'object' ? { ...payload.state } : {};
  // Preserve the top-level immutable rules alongside reload-safe state.
  next.rules = payload.rules || next.rules || {};
  // Preserve the documented shoe shape when an early payload omits it.
  next.shoe = next.shoe || {};
  // Copy recent rounds before optionally adding the POST result.
  const rounds = Array.isArray(next.recent_rounds) ? [...next.recent_rounds] : [];
  // Add a returned round only when state did not already include it.
  if (payload.round && !rounds.some(round => round.round_id === payload.round.round_id)) rounds.push(payload.round);
  // Keep a bounded history so the data rail never needs nested scrolling.
  next.recent_rounds = rounds.slice(-8);
  // Return one renderer-ready state object.
  return next;
}

// Install the shared #96 card stylesheet without copying its rules.
function ensureCardStyles() {
  // Reuse a stylesheet installed by this or another card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create the standard stylesheet link through the DOM API.
  const link = document.createElement('link');
  // Assign its stable cross-game identity.
  link.id = CARD_STYLE_ID;
  // Declare the linked resource as CSS.
  link.rel = 'stylesheet';
  // Load the merged primitive styles from the web root.
  link.href = '/core/cards.css';
  // Install shared presentation before the first rendered cards.
  document.head.append(link);
}

// Store compact game-owned CSS without editing the shared stylesheet.
const GAME_CSS = [
  '.dragon-tiger{display:grid;gap:14px;min-width:0}', // Establish one stable route surface.
  '.dt-header{display:flex;align-items:end;justify-content:space-between;gap:14px}.dt-header h1{margin:0}', // Keep title and phase compact.
  '.dt-phase{min-height:38px;padding:8px 12px;border:1px solid rgba(255,215,128,.45);border-radius:999px}', // Reserve status space.
  '.dt-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(520px,2.25fr) minmax(230px,.72fr);gap:16px;align-items:start}', // Make the stage wider than both rails.
  '.dt-panel{min-width:0;padding:16px;border:1px solid rgba(255,215,128,.25);border-radius:16px;background:rgba(3,29,20,.86)}', // Distinguish each zone.
  '.dt-controls,.dt-data{display:grid;align-content:start;gap:12px}.dt-bets{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}', // Organize control and data rails.
  '.dt-bet,.dt-deal{min-height:46px}.dt-bet.is-selected{outline:3px solid #ffd780;outline-offset:2px}.dt-deal{background:#a51f2d;color:#fff}', // Preserve touch size and non-color selection.
  '.dt-stage{display:grid;gap:18px;min-height:430px;background:radial-gradient(circle at 50% 45%,rgba(22,112,72,.5),rgba(3,28,19,.96) 70%)}', // Provide a dominant table stage.
  '.dt-stage-head{display:flex;align-items:start;justify-content:space-between;gap:12px}.dt-stage-head h2{margin:0}', // Keep result and bet context aligned.
  '.dt-hands{display:grid;grid-template-columns:1fr 1fr;gap:clamp(18px,5vw,70px);align-items:center;min-height:250px}', // Balance both card sides.
  '.dt-hand{display:grid;justify-items:center;gap:12px;padding:18px;border:1px solid rgba(255,255,255,.14);border-radius:14px}.dt-hand h3{margin:0}', // Give each side a labeled card bay.
  '.dt-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.dt-stat{padding:10px;border-radius:10px;background:rgba(0,0,0,.2)}.dt-stat span{display:block;color:var(--muted,#b8c8c1);font-size:.78rem}', // Align wager results.
  '.dt-history{display:grid;gap:8px}.dt-history-row{display:grid;grid-template-columns:1fr auto;gap:5px;padding:9px;border-radius:9px;background:rgba(0,0,0,.18)}.dt-history-row small{display:block}', // Keep bounded history readable.
  '.dt-muted{color:var(--muted,#b8c8c1)}.dt-selected{display:block;font-size:.72rem}', // Style secondary localized copy.
  '.dragon-tiger button:focus-visible,.dragon-tiger input:focus-visible{outline:3px solid #ffd780;outline-offset:2px}', // Preserve keyboard focus.
  '@media(max-width:1200px){.dt-layout{grid-template-columns:1fr}.dt-controls{order:1}.dt-stage{order:2}.dt-data{order:3}.dt-stage{min-height:auto}}', // Stack control, stage, then data.
  '@media(max-width:520px){.dt-header{align-items:start;flex-direction:column}.dt-panel{padding:12px}.dt-hands,.dt-summary{grid-template-columns:1fr}.dt-bets{grid-template-columns:1fr}.dt-stage{min-height:0}}', // Prevent mobile clipping.
  '@media(prefers-reduced-motion:reduce){.dragon-tiger *{animation:none!important;scroll-behavior:auto!important;transition:none!important}}', // Remove decorative motion.
].join(''); // Combine the documented route-local rules into one style payload.

// Install game-owned CSS once per document.
function ensureGameStyles() {
  // Reuse the existing route style node after remount.
  if (document.getElementById(GAME_STYLE_ID)) return;
  // Create one scoped style node.
  const style = document.createElement('style');
  // Assign its stable route-local identity.
  style.id = GAME_STYLE_ID;
  // Apply the documented responsive CSS.
  style.textContent = GAME_CSS;
  // Install styles before rendering the route.
  document.head.append(style);
}

// Format one ledger amount with localized play-token terminology.
function tokenAmount(value, translate = text) {
  // Format the numeric portion without a currency or replacement-looking glyph.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Interpolate the amount into game-owned fake-token copy.
  return translate('units.playTokens', { amount });
}

// Render a shared card while replacing every default English accessible label.
export function localizedCard(card, { hidden = false, translate = text } = {}) {
  // Render a localized face-down primitive for empty or request-bound card bays.
  if (hidden || !card) return renderCard('??', { hidden: true }).replace(/aria-label="[^"]*"/, `aria-label="${safe(translate('cards.faceDown'))}"`);
  // Read the compact rank from every character except the suit code.
  const rank = String(card).slice(0, -1);
  // Read the compact canonical suit code from the final character.
  const suit = String(card).slice(-1);
  // Build the complete accessible card name from localized rank and suit values.
  const label = translate('cards.label', { rank: translate(`ranks.${rank}`), suit: translate(`suits.${suit}`) });
  // Replace only the primitive's locale-neutral accessible label.
  return renderCard(card).replace(/aria-label="[^"]*"/, `aria-label="${safe(label)}"`);
}

// Return the newest reload-safe settled round.
function currentRound(snapshot = gameState) {
  // Read the bounded history supplied by the backend.
  const rounds = snapshot?.recent_rounds || [];
  // Return the newest entry or no round before first play.
  return rounds.length ? rounds[rounds.length - 1] : null;
}

// Map documented winners to stable locale keys without exposing API identifiers.
function winnerKey(round) {
  // Return the known winner or the pending presentation state.
  return BETS.includes(round?.winner) ? round.winner : 'pending';
}

// Render all route markup through an injectable translation seam.
export function viewMarkup({ snapshot = gameState, translate = text, selected = selectedBet, wagerValue = wager, isDealing = dealing, isLoading = initialLoading, pending = pendingAction } = {}) {
  // Resolve the newest completed round once for a consistent frame.
  const round = currentRound(snapshot);
  // Resolve the request-bound or settled player-facing phase.
  const phase = translate(isLoading ? 'phases.loading' : isDealing ? 'phases.dealing' : round ? 'phases.settled' : 'phases.ready');
  // Resolve the current winner without exposing its internal enum.
  const result = translate(`outcomes.${winnerKey(round)}`);
  // Disable configuration while a request or unresolved retry owns its payload.
  const configurationDisabled = isLoading || isDealing || Boolean(pending);
  // Keep a saved retry actionable while blocking initial-load and in-flight clicks.
  const actionDisabled = isLoading || isDealing;
  // Render semantic pressed-state wager buttons with visible selected copy.
  const bets = BETS.map(bet => `<button type="button" class="dt-bet${selected === bet ? ' is-selected' : ''}" data-bet="${bet}" aria-pressed="${selected === bet}"${configurationDisabled ? ' disabled' : ''}>${safe(translate(`bets.${bet}`))}${selected === bet ? `<span class="dt-selected">${safe(translate('bets.selected'))}</span>` : ''}</button>`).join('');
  // Resolve the primary action label for normal, request, and retry states.
  const actionLabel = translate(isLoading ? 'controls.loading' : isDealing ? 'controls.dealing' : pending ? 'controls.retry' : round ? 'controls.dealNext' : 'controls.deal');
  // Render the two visible cards or localized face-down placeholders.
  const dragonCard = localizedCard(round?.dragon_card, { hidden: isDealing || !round, translate });
  // Render the opposing card through the same localized primitive adapter.
  const tigerCard = localizedCard(round?.tiger_card, { hidden: isDealing || !round, translate });
  // Resolve recent history in newest-first display order.
  const recent = [...(snapshot?.recent_rounds || [])].reverse().slice(0, 6);
  // Render each bounded history row with localized winner, bet, and net result.
  const history = recent.map(item => `<article class="dt-history-row"><span>${safe(translate(`outcomes.${winnerKey(item)}`))}<small class="dt-muted">${safe(translate('history.bet', { bet: translate(`bets.${item.bet}`) }))}</small></span><strong>${safe(tokenAmount(item.net, translate))}</strong></article>`).join('');
  // Read server-owned rules and shoe telemetry without inventing values.
  const rules = snapshot?.rules || {};
  // Read the contract's nested main-bet payout definitions.
  const betRules = rules.bets || {};
  // Read server-owned shoe state for the data rail.
  const shoe = snapshot?.shoe || {};
  // Return the complete responsive three-zone route.
  return `<section class="dragon-tiger" data-testid="dragon-tiger"><header class="dt-header"><div><p class="dt-muted">${safe(translate('eyebrow'))}</p><h1>${safe(translate('title'))}</h1></div><span class="dt-phase" role="status" aria-live="polite">${safe(phase)}</span></header><div class="dt-layout"><section class="dt-panel dt-controls" aria-label="${safe(translate('controls.region'))}"><h2>${safe(translate('controls.title'))}</h2><div class="dt-bets">${bets}</div><label for="dt-wager">${safe(translate('controls.wager'))}</label><input id="dt-wager" type="number" min="0.01" max="1000000" step="0.01" value="${safe(wagerValue)}"${configurationDisabled ? ' disabled' : ''}><button type="button" class="dt-deal" data-action="deal"${actionDisabled ? ' disabled' : ''}>${safe(actionLabel)}</button><p class="dt-muted">${safe(translate(pending ? 'controls.retryHelp' : 'controls.help'))}</p></section><main class="dt-panel dt-stage" data-testid="dragon-tiger-table" aria-label="${safe(translate('stage.region'))}"><div class="dt-stage-head"><div><p class="dt-muted">${safe(translate('stage.selectedBet', { bet: translate(`bets.${pending?.bet || round?.bet || selected}`) }))}</p><h2>${safe(result)}</h2></div><strong>${safe(phase)}</strong></div><div class="dt-hands"><section class="dt-hand" aria-label="${safe(translate('stage.dragonHand'))}"><h3>${safe(translate('bets.dragon'))}</h3>${dragonCard}</section><section class="dt-hand" aria-label="${safe(translate('stage.tigerHand'))}"><h3>${safe(translate('bets.tiger'))}</h3>${tigerCard}</section></div><div class="dt-summary"><div class="dt-stat"><span>${safe(translate('summary.wager'))}</span><strong>${safe(tokenAmount(round?.wager || 0, translate))}</strong></div><div class="dt-stat"><span>${safe(translate('summary.return'))}</span><strong>${safe(tokenAmount(round?.total_return || 0, translate))}</strong></div><div class="dt-stat"><span>${safe(translate('summary.net'))}</span><strong>${safe(tokenAmount(round?.net || 0, translate))}</strong></div></div></main><aside class="dt-panel dt-data" aria-label="${safe(translate('data.region'))}"><h2>${safe(translate('data.title'))}</h2><div class="dt-stat"><span>${safe(translate('data.cardsRemaining'))}</span><strong>${safe(formatNumber(shoe.cards_remaining || 0))}</strong></div><div class="dt-stat"><span>${safe(translate('data.deckCount'))}</span><strong>${safe(formatNumber(rules.deck_count || 0))}</strong></div><p class="dt-muted">${safe(translate('data.rule', { dragon: betRules.dragon?.net_odds ?? 1, tiger: betRules.tiger?.net_odds ?? 1, tie: betRules.tie?.net_odds ?? 11 }))}</p><h3>${safe(translate('history.title'))}</h3><div class="dt-history">${history || `<p class="dt-muted">${safe(translate('history.empty'))}</p>`}</div></aside></div></section>`;
}

// Render current state and reconnect semantic controls.
function render() {
  // Ignore locale callbacks and promises after route teardown.
  if (!root) return;
  // Replace the isolated route atomically.
  root.innerHTML = viewMarkup();
  // Bind each wager target to local unsent configuration.
  root.querySelectorAll('[data-bet]').forEach(button => { button.onclick = () => { if (!initialLoading && !dealing && !pendingAction) { selectedBet = button.dataset.bet; render(); } }; });
  // Read and bind the wager input created by this render.
  const wagerInput = root.querySelector('#dt-wager');
  // Preserve a positive normalized wager without moving tokens.
  if (wagerInput) wagerInput.onchange = () => { if (!initialLoading && !pendingAction) { wager = Math.min(1000000, Math.max(0.01, Math.round(Number(wagerInput.value || wager || 5) * 100) / 100)); render(); } };
  // Bind the one atomic deal action.
  root.querySelector('[data-action="deal"]')?.addEventListener('click', deal);
}

// Submit or retry one exactly-once Dragon Tiger round.
async function deal() {
  // Ignore overlapping clicks while the POST request is active.
  if (initialLoading || dealing) return;
  // Capture one immutable request and retain it through any failed response.
  pendingAction = pendingAction || { action_id: createActionId(), bet: selectedBet, wager };
  // Capture route identity so late completions remain inert.
  const identity = mountIdentity;
  // Enter request-bound dealing state without starting a timer.
  dealing = true;
  // Render face-down cards and disabled controls during the request.
  render();
  // Run the action while preserving the retry payload on errors.
  try {
    // Post only the documented session-bound action fields.
    const payload = await post(`${API_ROOT}/rounds`, pendingAction);
    // Stop if navigation replaced this route while the request completed.
    if (!root || identity !== mountIdentity) return;
    // Merge returned state, rules, and round for immediate and reload-consistent rendering.
    gameState = normalizeStatePayload(payload);
    // Clear the action only after a successful server response.
    pendingAction = null;
    // Refresh the authenticated wallet without reclassifying a committed round as a failed deal.
    try {
      // Ask the shared shell for the now-authoritative ledger balance.
      await refreshBalance();
    // Keep the settled round while reporting only the secondary wallet refresh failure.
    } catch (_) {
      // Notify only while this mount still owns the route.
      if (root && identity === mountIdentity) toast(text('errors.balanceRefreshFailed'));
    }
  // Translate request failures instead of exposing server English in the route.
  } catch (_) {
    // Show localized retry guidance only while this mount still owns the route.
    if (root && identity === mountIdentity) toast(text('errors.dealFailed'));
  // Always leave request-bound dealing state for the active mount.
  } finally {
    // Stop when teardown already cleared route ownership.
    if (!root || identity !== mountIdentity) return;
    // Release the request guard while preserving any unresolved retry payload.
    dealing = false;
    // Render either the settled round or localized retry action.
    render();
  }
}

// Export the catalog-loadable lazy game contract.
export const DragonTigerGame = {
  // Expose the descriptor-facing stable game id.
  id: 'dragon_tiger',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Store the route outlet before asynchronous initialization.
    root = node;
    // Create a unique identity for late-promise protection.
    mountIdentity = {};
    // Capture this mount identity for the initial state request.
    const identity = mountIdentity;
    // Reset player-local transient state before loading session data.
    gameState = { shoe: {}, rules: {}, recent_rounds: [] };
    // Reset request state so another user never inherits an action id.
    pendingAction = null;
    // Reset the request-bound phase.
    dealing = false;
    // Hold every player action until the session-bound GET finishes.
    initialLoading = true;
    // Install shared and route-local presentation once.
    ensureCardStyles();
    // Install the responsive game presentation.
    ensureGameStyles();
    // Load active and fallback game resources before visible text.
    await loadI18nDomain(DOMAIN);
    // Stop if navigation replaced this mount during locale loading.
    if (!root || identity !== mountIdentity) return;
    // Subscribe to live locale changes without losing backend state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Render a localized inert loading frame while backend state loads.
    render();
    // Load the authenticated player's reload-safe state.
    try {
      // Fetch state without a caller-selected player identity.
      const payload = await api(`${API_ROOT}/state`);
      // Stop if navigation replaced this route during the request.
      if (!root || identity !== mountIdentity) return;
      // Store the documented state and top-level rules.
      gameState = normalizeStatePayload(payload);
      // Release the initial action guard only after the snapshot is authoritative.
      initialLoading = false;
      // Render recovered shoe and round history.
      render();
      // Align the shared wallet without misclassifying an already loaded game state.
      try {
        // Ask the shared shell for the authenticated player's current ledger balance.
        await refreshBalance();
      // Report only the secondary wallet refresh failure.
      } catch (_) {
        // Notify only while this mount still owns the route.
        if (root && identity === mountIdentity) toast(text('errors.balanceRefreshFailed'));
      }
    // Surface a localized load failure while leaving a retry-safe ready frame.
    } catch (_) {
      // Stop a late rejection from releasing a newer mount's initial-load guard.
      if (!root || identity !== mountIdentity) return;
      // Release the guard because the failed GET can no longer overwrite a later action.
      initialLoading = false;
      // Re-render one actionable retry-safe frame after the failed snapshot request.
      render();
      // Notify only while this mount still owns the route.
      if (root && identity === mountIdentity) toast(text('errors.loadFailed'));
    }
  },
  // Release every game-owned lifecycle resource on route exit.
  unmount() {
    // Release the locale subscription when it exists.
    unsubscribeLocale?.();
    // Clear the callback reference for a future mount.
    unsubscribeLocale = null;
    // Invalidate every in-flight async completion.
    mountIdentity = null;
    // Release the DOM outlet before any late promise settles.
    root = null;
    // Clear player state so another session cannot inherit it.
    gameState = { shoe: {}, rules: {}, recent_rounds: [] };
    // Clear any unresolved action identity at the session boundary.
    pendingAction = null;
    // Release request-bound presentation state; this module owns no timers.
    dealing = false;
    // Release initial-load presentation state at the session boundary.
    initialLoading = false;
  },
};
