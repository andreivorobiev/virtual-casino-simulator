// Implement the catalog-integrated Acey-Deucey browser module for GitHub issue #149.

// Import authenticated envelope-aware API helpers without caller-owned player ids.
import { api, post } from '../core/api.js';
// Import shared accessible card rendering from the #96 primitive lane.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the paired game-owned dictionaries.
const DOMAIN = 'games/acey_deucey';
// Address the additive frozen-v1 proposal API through one stable root.
const API_ROOT = '/api/v1/games/acey-deucey';
// Identify the shared card stylesheet so route mounts install it idempotently.
const CARD_STYLE_ID = 'casino-shared-card-styles';

// Retain the current route outlet for stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published fixed rule metadata.
let rules = {};
// Retain the configured play wager between free deals.
let wager = 5;
// Prevent overlapping atomic browser actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain unresolved action identities for exact network retries.
let pendingAction = null;
// Retain one localized error key for the reserved alert region.
let lastErrorKey = null;
// Allocate fallback action identities when randomUUID is unavailable.
let actionCounter = 0;
// Retain the last settled wager so one click can repeat an identical opening bet.
let lastBet = null;

// Resolve one localized string from the game-owned domain.
function text(key, params = {}) {
  // Delegate visible and accessible labels to the active locale resource.
  return t(key, params, DOMAIN);
}

// Format one fake-token amount without currency semantics.
function tokenAmount(value) {
  // Format ledger precision through the active locale.
  const amount = formatNumber(value || 0, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Wrap the number in localized play-token wording.
  return text('tokens.amount', { amount });
}

// Create one bounded client action identity for exactly-once retries.
function nextActionId(kind) {
  // Prefer browser cryptographic UUIDs when available.
  if (globalThis.crypto?.randomUUID) return 'acey-deucey-' + kind + '-' + globalThis.crypto.randomUUID();
  // Advance a route-local counter for fallback uniqueness.
  actionCounter += 1;
  // Combine kind, time, and counter without displaying the value.
  return 'acey-deucey-' + kind + '-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
}

// Map public API diagnostics to owned localized feedback.
function errorKey(error) {
  // Normalize the optional envelope code.
  const code = String(error?.code || '').toUpperCase();
  // Explain insufficient fake-token balance locally.
  if (code.includes('INSUFFICIENT')) return 'errors.insufficientTokens';
  // Explain stale or conflicting actions locally.
  if (code.includes('CONFLICT')) return 'errors.conflict';
  // Explain missing or cross-session rounds locally.
  if (code.includes('NOT_FOUND')) return 'errors.notFound';
  // Fall back to one retry-safe localized action message.
  return 'errors.actionFailed';
}

// Install the shared card stylesheet once without editing global CSS.
function ensureSharedCardStyles() {
  // Reuse an existing link installed by another card-game mount.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create a stylesheet link owned by the reusable card primitive.
  const link = document.createElement('link');
  // Mark the link for idempotent future mounts.
  link.id = CARD_STYLE_ID;
  // Declare the linked resource as a stylesheet.
  link.rel = 'stylesheet';
  // Load the shared responsive card presentation.
  link.href = '/core/cards.css';
  // Append the reusable stylesheet to the document head.
  document.head.append(link);
}

// Render one visible or protected card with localized accessible text.
function localizedCard(card, options = {}) {
  // Treat explicit hidden state or missing data as protected.
  const hidden = options.hidden === true || !card;
  // Render a localized face-down card without exposing hidden identity.
  if (hidden) return renderCard('??', { hidden: true }).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(text('cards.faceDown')) + '"');
  // Extract the compact rank from every character before the suit code.
  const rank = String(card).slice(0, -1);
  // Extract the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build a localized accessible name from rank and suit resources.
  const label = text('cards.cardLabel', { rank: text('ranks.' + rank), suit: text('suits.' + suit) });
  // Replace the primitive English label while retaining accessible markup.
  return renderCard(card).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(label) + '"');
}

// Return the active round or newest terminal round for stable rendering.
function currentRound() {
  // Prefer the open boundary deal before bounded history.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}

// Translate one internal phase or outcome into player-facing status.
function phaseLabel(roundItem) {
  // Show ready copy before the first deal.
  if (!roundItem) return text('phases.ready');
  // Show wager decision copy while the boundaries are open.
  if (roundItem.phase === 'wager') return text('phases.wager');
  // Show pass copy for a closed no-wager round.
  if (roundItem.phase === 'passed') return text('phases.passed');
  // Show localized terminal outcome copy.
  return text('phases.' + (roundItem.outcome || 'ready'));
}

// Normalize the wager input into the documented ledger-compatible range.
function wagerValue(value) {
  // Convert the browser value to a number.
  const parsed = Number(value);
  // Reuse the prior value when the input is not finite.
  if (!Number.isFinite(parsed)) return wager;
  // Clamp and round the value to shared ledger precision.
  return Math.min(100000, Math.max(0.01, Math.round(parsed * 100) / 100));
}

// Render the control rail for free deal, play wager, and pass.
function controlsHtml() {
  // Read the only actionable round from server state.
  const activeRound = state?.active_round;
  // Allow play and pass only during the wager phase.
  const canDecide = activeRound?.phase === 'wager';
  // Require a positive server-published inside spread before exposing a play wager.
  const hasInsidePrice = canDecide && Number(activeRound?.inside_rank_count) > 0;
  // Disable wager edits when no priced play exists or a pending action owns state.
  const wagerDisabled = !hasInsidePrice || busy || Boolean(pendingAction);
  // Disable dealing while an active round is open.
  const dealDisabled = Boolean(activeRound) || busy || Boolean(pendingAction && pendingAction.kind !== 'deal');
  // Disable play while no priceable inside outcome exists.
  const playDisabled = !hasInsidePrice || busy || Boolean(pendingAction && pendingAction.kind !== 'play');
  // Disable pass while no boundary decision is open.
  const passDisabled = !canDecide || busy || Boolean(pendingAction && pendingAction.kind !== 'pass');
  // Enable one-click repeat only outside an open round when a prior settled wager exists and nothing is in flight.
  const repeatDisabled = busy || Boolean(activeRound) || Boolean(pendingAction) || !lastBet;
  // Explain unresolved retry state when present.
  const retryHelp = pendingAction ? '<p class="acey-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Explain why passing is the only valid decision for equal or adjacent boundaries.
  const decisionHelp = canDecide && !hasInsidePrice ? text('controls.noInside') : text('controls.help');
  // Return stable controls whose positions do not change between phases.
  return '<aside class="acey-panel acey-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="acey-wager">' + safe(text('controls.wager')) + '</label><input id="acey-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (wagerDisabled ? ' disabled' : '') + '><button type="button" data-action="deal"' + (dealDisabled ? ' disabled' : '') + '>' + safe(pendingAction?.kind === 'deal' ? text('controls.retryDeal') : text('controls.deal')) + '</button><button type="button" class="acey-repeat" data-action="repeat"' + (repeatDisabled ? ' disabled' : '') + '>' + safe(text('controls.repeat')) + '</button><button type="button" data-action="play"' + (playDisabled ? ' disabled' : '') + '>' + safe(pendingAction?.kind === 'play' ? text('controls.retryPlay') : text('controls.play')) + '</button><button type="button" data-action="pass"' + (passDisabled ? ' disabled' : '') + '>' + safe(pendingAction?.kind === 'pass' ? text('controls.retryPass') : text('controls.pass')) + '</button><p class="acey-help">' + safe(decisionHelp) + '</p>' + retryHelp + '<p class="acey-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render the three-card stage with a protected third card until play.
function stageHtml(roundItem) {
  // Render the left boundary when available.
  const leftCard = localizedCard(roundItem?.left_card, { hidden: !roundItem?.left_card });
  // Render the right boundary when available.
  const rightCard = localizedCard(roundItem?.right_card, { hidden: !roundItem?.right_card });
  // Reveal the third card only after a wagered play settled.
  const thirdCard = localizedCard(roundItem?.third_card, { hidden: roundItem?.phase !== 'settled' });
  // Select phase-specific stage copy.
  const message = !roundItem ? text('stage.readyBody') : roundItem.phase === 'wager' ? text('stage.wagerBody', { count: roundItem.inside_rank_count }) : roundItem.phase === 'passed' ? text('results.passed') : text('results.' + roundItem.outcome);
  // Return reserved card slots so reduced-motion users see no layout jump.
  return '<section class="acey-stage-cards" role="group" aria-label="' + safe(text('stage.cardsAria')) + '"><article><h3>' + safe(text('stage.leftBoundary')) + '</h3>' + leftCard + '</article><article><h3>' + safe(text('stage.thirdCard')) + '</h3>' + thirdCard + '</article><article><h3>' + safe(text('stage.rightBoundary')) + '</h3>' + rightCard + '</article></section><p class="acey-result" role="status" aria-live="polite">' + safe(message) + '</p>';
}

// Render wager, return, and net facts in fixed positions.
function summaryHtml(roundItem) {
  // Use localized placeholder before facts exist.
  const pending = text('summary.pending');
  // Format the wager only after play settled.
  const roundWager = roundItem?.wager ? tokenAmount(roundItem.wager) : pending;
  // Format the returned tokens only after play settled.
  const payout = roundItem?.phase === 'settled' ? tokenAmount(roundItem.payout) : pending;
  // Format net result only after play settled.
  const net = roundItem?.phase === 'settled' ? tokenAmount(roundItem.net) : pending;
  // Translate the terminal outcome when present.
  const outcome = roundItem?.outcome ? text('outcomes.' + roundItem.outcome) : pending;
  // Return aligned facts that stay stable across phases.
  return '<section class="acey-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.wager')) + '<strong>' + safe(roundWager) + '</strong></span><span>' + safe(text('summary.outcome')) + '<strong>' + safe(outcome) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(payout) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(net) + '</strong></span></section>';
}

// Render bounded reload-safe history.
function historyHtml() {
  // Copy newest terminal rounds first without mutating state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show localized empty state before the first terminal round.
  if (!rounds.length) return '<p class="acey-empty">' + safe(text('history.empty')) + '</p>';
  // Render each retained result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the outcome for display and accessible labels.
    const outcome = text('outcomes.' + roundItem.outcome);
    // Build one localized accessible row name.
    const label = text('history.roundAria', { number: rounds.length - index, outcome });
    // Return the row with returned-token evidence.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(outcome) + '</span><strong>' + safe(tokenAmount(roundItem.payout)) + '</strong></li>';
  // Join bounded rows.
  }).join('');
  // Return one intentional scroll region for history only.
  return '<ol class="acey-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render rule and history support regions.
function dataHtml() {
  // Read the server-published spread paytable; the inside price scales with the visible spread. (issue #408)
  const paytable = rules.inside_paytable || {};
  // Use the current round's spread so the player sees the price that actually applies to this deal.
  const currentSpread = currentRound()?.inside_rank_count;
  // Use no multiplier before a round or for pass-only zero spreads; active prices come only from the table.
  const insideMultiplier = currentSpread > 0 ? paytable[currentSpread] ?? paytable[String(currentSpread)] : null;
  // Read the server-published tie multiplier with proposal default.
  const tieMultiplier = rules.boundary_tie_return_multiplier ?? 0;
  // Return transparent return table and recent history.
  return '<aside class="acey-panel acey-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul><li>' + safe(text('rules.freeDeal')) + '</li><li>' + safe(insideMultiplier ? text('rules.insideReturn', { multiplier: insideMultiplier }) : text('rules.insideReturnScaled')) + '</li><li>' + safe(text('rules.boundaryTie', { multiplier: tieMultiplier })) + '</li><li>' + safe(text('rules.outsideReturn')) + '</li><li>' + safe(text('rules.reducedMotion')) + '</li></ul></section><section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive and reduced-motion styles.
function stylesHtml() {
  // Define compact operational layout without editing shared CSS.
  return '<style>/* Define the Acey-Deucey game layout and responsive regions. */.acey-shell{display:grid;gap:16px;min-width:0}.acey-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.acey-header h1{margin:0}.acey-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.acey-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.acey-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(520px,2.2fr) minmax(240px,.86fr);gap:16px;align-items:start}.acey-panel,.acey-stage{border:1px solid var(--border);border-radius:12px;background:var(--panel-strong);padding:16px}.acey-controls,.acey-data{display:grid;align-content:start;gap:12px}.acey-controls input,.acey-controls button{min-height:44px}.acey-controls button[data-action=play]{background:var(--red,#a51f2d);color:#fff}.acey-help,.acey-retry,.acey-empty{color:var(--muted,#b8c8c1)}.acey-error{min-height:1.4em;margin:0;color:#ffd1d1}.acey-stage{display:grid;align-content:center;gap:22px;min-width:0;min-height:430px;background:radial-gradient(circle at 50% 42%,rgba(35,17,61,.44),rgba(21,10,36,.96) 70%)}.acey-stage-cards{display:grid;grid-template-columns:minmax(120px,1fr) minmax(120px,1fr) minmax(120px,1fr);gap:clamp(12px,3vw,34px);align-items:center;justify-items:center}.acey-stage-cards article{display:grid;justify-items:center;gap:12px}.acey-stage-cards h3{margin:0}.acey-stage-cards .playing-card{flex:none;width:clamp(4.3rem,8vw,7.2rem);font-size:clamp(1rem,2.4vw,1.7rem)}.acey-result{min-height:2.8em;margin:0;text-align:center}.acey-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.acey-summary span{display:grid;gap:5px;padding:10px;border-radius:8px;background:rgba(255,255,255,.05)}.acey-summary strong{overflow-wrap:anywhere}.acey-data section{display:grid;gap:10px}.acey-data ul{margin:0;padding-left:1.1rem}.acey-data li+li{margin-top:7px}.acey-history-list{display:grid;gap:8px;max-height:285px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.acey-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:8px;background:rgba(0,0,0,.2)}.acey-shell button:focus-visible,.acey-shell input:focus-visible,.acey-history-list:focus-visible{outline:3px solid var(--gold);outline-offset:2px}@media(max-width:1100px){.acey-layout{grid-template-columns:1fr}.acey-controls{order:1}.acey-stage{order:2;min-height:360px}.acey-data{order:3}}@media(max-width:560px){.acey-header{align-items:start;flex-direction:column}.acey-panel,.acey-stage{padding:12px}.acey-stage{min-height:330px}.acey-stage-cards{grid-template-columns:1fr 1fr 1fr;gap:8px}.acey-stage-cards .playing-card{width:clamp(3.6rem,21vw,5.4rem)}.acey-summary{grid-template-columns:1fr 1fr}}@media(prefers-reduced-motion:reduce){.acey-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}</style>.acey-repeat{min-height:44px;background:transparent;color:var(--gold);border:1px solid var(--gold)}.acey-repeat:disabled{opacity:.5}';
}

// Return repeat-aware styles without exposing CSS text after the style element.
function repeatSafeStylesHtml() {
  // Move the additive repeat rules ahead of the closing style tag.
  const scoped = stylesHtml().replace('</style>.acey-repeat', '.acey-repeat');
  // Close the corrected style element after every scoped repeat rule.
  return scoped + '</style>';
}

// Bind semantic controls after each render.
function bindEvents() {
  // Read the wager input from the current frame.
  const wagerInput = root?.querySelector('#acey-wager');
  // Preserve valid wager edits without replacing the focused control before its action click.
  if (wagerInput) wagerInput.oninput = () => { wager = wagerValue(wagerInput.value); };
  // Bind deal, play, and pass controls through one action dispatcher.
  root?.querySelectorAll('[data-action]').forEach(button => {
    // Prepare the exact retry identity before executing the action.
    button.onclick = () => {
      // Read the semantic action kind.
      const kind = button.dataset.action;
      // Route the one-click repeat to its dedicated fresh-round handler.
      if (kind === 'repeat') { repeat(); return; }
      // Update the wager from the control before play.
      wager = wagerValue(wagerInput?.value ?? wager);
      // Preserve unresolved identity for exact retry.
      pendingAction = pendingAction || { kind, actionId: nextActionId(kind), roundId: state?.active_round?.round_id, wager };
      // Ignore incompatible clicks while an unresolved action exists.
      if (pendingAction.kind !== kind) return;
      // Execute the selected action.
      runAction(kind === 'deal' ? deal : kind === 'play' ? play : passRound);
    };
  });
}

// Render all game-owned regions from authenticated state.
function render() {
  // Stop late callbacks after unmount.
  if (!root) return;
  // Read the active or newest terminal round once.
  const roundItem = currentRound();
  // Build the localized header.
  const header = '<header class="acey-header"><div><p class="acey-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="acey-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the operational layout.
  const layout = '<div class="acey-layout">' + controlsHtml() + '<main class="acey-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + summaryHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Replace the outlet atomically.
  root.innerHTML = repeatSafeStylesHtml() + '<section class="acey-shell" data-testid="acey-deucey">' + header + layout + '</section>';
  // Attach handlers to the new controls.
  bindEvents();
}

// Execute one atomic browser action with localized error handling.
async function runAction(action) {
  // Ignore overlapping or detached requests.
  if (busy || !root) return;
  // Lock controls before the network call.
  busy = true;
  // Clear stale feedback.
  lastErrorKey = null;
  // Render pending state.
  render();
  // Execute protected action handling.
  try {
    // Await the selected game action.
    await action();
  // Translate failures locally.
  } catch (error) {
    // Store the localized error key.
    lastErrorKey = errorKey(error);
    // Show shared localized feedback while mounted.
    if (root) toast(text(lastErrorKey));
  // Always release the busy lock.
  } finally {
    // Allow retry or next action.
    busy = false;
    // Rerender if still mounted.
    render();
  }
}

// Deal or replay one free boundary-card round.
async function deal() {
  // Capture the mounted outlet for stale-response protection.
  const mountedRoot = root;
  // Read the prepared retry action.
  const request = pendingAction;
  // Stop if route state changed.
  if (!request || !mountedRoot) return;
  // Post the free deal without player_id.
  const payload = await post(API_ROOT + '/rounds', { action_id: request.actionId });
  // Ignore late responses after unmount.
  if (root !== mountedRoot) return;
  // Store authoritative state.
  state = payload.state;
  // Store server-published rules.
  rules = payload.rules || rules;
  // Clear the retry identity after success.
  pendingAction = null;
}

// Play or replay one wagered reveal.
async function play() {
  // Capture the mounted outlet for stale-response protection.
  const mountedRoot = root;
  // Read the prepared retry action.
  const request = pendingAction;
  // Stop if route state changed.
  if (!request || !mountedRoot) return;
  // Encode the round id for the route path.
  const roundId = encodeURIComponent(request.roundId);
  // Post the play wager without player_id.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/play', { action_id: request.actionId, wager: request.wager });
  // Ignore late responses after unmount.
  if (root !== mountedRoot) return;
  // Store terminal state.
  state = payload.state;
  // Store server-published rules.
  rules = payload.rules || rules;
  // Clear the retry identity after success.
  pendingAction = null;
  // Remember the committed wager so one click can repeat an identical opening bet.
  lastBet = { wager: request.wager };
  // Refresh the shared wallet after debit and optional payout.
  await refreshBalance();
}

// Open one fresh round with the previously settled wager without replaying play or pass.
async function repeat() {
  // Ignore repeat while an action is in flight or an unresolved retry owns state.
  if (busy || pendingAction) return;
  // Ignore repeat before any settled wager exists or while a round is still open.
  if (!lastBet || state?.active_round) return;
  // Restore the previous wager into module state so the next play reuses the same stake.
  wager = wagerValue(lastBet.wager);
  // Reflect the restored wager in the control when it is present.
  const wagerInput = root?.querySelector('#acey-wager');
  // Update the visible wager input only when the frame currently renders it.
  if (wagerInput) wagerInput.value = String(wager);
  // Prepare a fresh deal retry identity mirroring a deal click.
  pendingAction = { kind: 'deal', actionId: nextActionId('deal'), roundId: state?.active_round?.round_id, wager };
  // Execute the shared free-deal action to open the identical opening round.
  await runAction(deal);
}

// Pass or replay one no-wager close.
async function passRound() {
  // Capture the mounted outlet for stale-response protection.
  const mountedRoot = root;
  // Read the prepared retry action.
  const request = pendingAction;
  // Stop if route state changed.
  if (!request || !mountedRoot) return;
  // Encode the round id for the route path.
  const roundId = encodeURIComponent(request.roundId);
  // Post the pass action without player_id.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/pass', { action_id: request.actionId });
  // Ignore late responses after unmount.
  if (root !== mountedRoot) return;
  // Store passed state.
  state = payload.state;
  // Store server-published rules.
  rules = payload.rules || rules;
  // Clear the retry identity after success.
  pendingAction = null;
}

// Export the catalog-owned lazy game module contract.
export const AceyDeuceyGame = {
  // Expose the stable descriptor identifier.
  id: 'acey_deucey',
  // Leave navigation labels to module metadata and translations.
  label: '',
  // Load locale and authenticated state before rendering.
  async mount(node) {
    // Store the shell outlet.
    root = node;
    // Reset route-owned transient flags.
    busy = false;
    // Clear stale feedback.
    lastErrorKey = null;
    // Clear retry identity because server state is authoritative on mount.
    pendingAction = null;
    // Reset the repeatable wager so a new session never inherits a prior bet.
    lastBet = null;
    // Install shared card presentation.
    ensureSharedCardStyles();
    // Capture this mount for async guards.
    const mountedRoot = root;
    // Load game-owned dictionaries.
    await loadI18nDomain(DOMAIN);
    // Stop when route changed during locale loading.
    if (root !== mountedRoot) return;
    // Rerender localized copy on locale changes.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read authenticated state.
    const payload = await api(API_ROOT + '/state');
    // Stop when route changed during state loading.
    if (root !== mountedRoot) return;
    // Cache public game state.
    state = payload.state;
    // Cache fixed rule metadata.
    rules = payload.rules || {};
    // Recover a repeatable wager from the newest settled round so repeat survives a reload.
    const recovered = [...(state?.recent_rounds || [])].reverse().find(item => item?.phase === 'settled' && item?.wager);
    // Restore the repeatable wager only when a prior settled round exposes its committed stake.
    if (recovered?.wager) lastBet = { wager: Number(recovered.wager) };
    // Render the complete surface.
    render();
    // Align the wallet with any recovered ledger state.
    await refreshBalance();
  },
  // Release every game-owned lifecycle reference on route change.
  unmount() {
    // Remove the locale callback when present.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference for harmless repeated teardown.
    unsubscribeLocale = null;
    // Clear the route outlet before late promises can render.
    root = null;
    // Clear authenticated state from this singleton module.
    state = null;
    // Clear rule metadata so next mount reloads it.
    rules = {};
    // Release the busy lock.
    busy = false;
    // Forget route-local retry identity.
    pendingAction = null;
    // Clear localized error state.
    lastErrorKey = null;
    // Clear the repeatable wager so the next session starts fresh.
    lastBet = null;
    // No timers or global event listeners are owned by this module.
  },
};
