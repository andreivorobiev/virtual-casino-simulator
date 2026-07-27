// Implement the isolated Joker Poker browser module for GitHub issue #130.

// Import authenticated envelope-aware API helpers without sending caller-owned player ids.
import { api, post } from '../core/api.js';
// Import the shared accessible natural-card renderer allocated by issue #96.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the game-owned locale domain.
const DOMAIN = 'games/joker_poker';
// Address the additive frozen-v1 Joker Poker API through one stable root.
const API_ROOT = '/api/v1/games/joker-poker';
// Identify the shared card stylesheet so repeated card-game mounts install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the game-owned joker code from the frozen rules profile.
const JOKER_CODE = 'JK';

// Retain the current shell outlet for deterministic rerenders and stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published rule metadata for reload-safe presentation.
let rules = {};
// Retain the configured wager until a round starts or the player changes it.
let wager = 5;
// Prevent overlapping atomic deal, hold, or draw actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain an unresolved deal identity and immutable wager for safe retry.
let pendingDeal = null;
// Retain an unresolved draw identity, round, and hold set for safe retry.
let pendingDraw = null;
// Retain a localized error resource key for the reserved route error region.
let lastErrorKey = null;
// Allocate stable fallback identities when randomUUID is unavailable.
let actionCounter = 0;


// Resolve one game-owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every visible and accessible label to the active EN/RU dictionary.
  return t(key, params, DOMAIN);
}


// Format one fake-token amount without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Format ledger precision through the active locale.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Wrap the number in explicit localized play-token terminology.
  return text('tokens.amount', { amount });
}


// Create one bounded client action identity for exactly-once network retries.
function nextActionId() {
  // Prefer the browser cryptographic UUID source when available.
  if (globalThis.crypto?.randomUUID) return 'joker-poker-' + globalThis.crypto.randomUUID();
  // Advance a per-module counter before building the fallback identity.
  actionCounter += 1;
  // Combine a timestamp and counter without presenting the value to the player.
  return 'joker-poker-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
}


// Map public API diagnostics to owned localized feedback.
function errorKey(error) {
  // Normalize the optional envelope code without exposing server text.
  const code = String(error?.code || '').toUpperCase();
  // Explain an insufficient fake-token balance through local copy.
  if (code.includes('INSUFFICIENT')) return 'errors.insufficientTokens';
  // Explain stale or conflicting actions without showing implementation details.
  if (code.includes('CONFLICT')) return 'errors.conflict';
  // Explain a missing or cross-session round through one neutral message.
  if (code.includes('NOT_FOUND')) return 'errors.notFound';
  // Fall back to one localized retry-safe action message.
  return 'errors.actionFailed';
}


// Install the shared CARD-002 presentation stylesheet without touching global CSS.
function ensureSharedCardStyles() {
  // Reuse the stylesheet installed by an earlier card-game mount.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create one standard stylesheet link owned by the shared card primitive.
  const link = document.createElement('link');
  // Mark the link so future mounts remain idempotent.
  link.id = CARD_STYLE_ID;
  // Declare the linked resource as a stylesheet.
  link.rel = 'stylesheet';
  // Load the shared responsive card presentation from the public core path.
  link.href = '/core/cards.css';
  // Keep the reusable stylesheet available across later card-game routes.
  document.head.append(link);
}


// Render the game-owned joker card without changing the shared natural-card renderer.
function renderJokerCard(options = {}) {
  // Read the selected state for held-card styling.
  const selected = options.selected === true;
  // Build a stable localized accessible label.
  const label = text('cards.jokerLabel');
  // Return semantic joker markup using only game-owned CSS hooks.
  return '<span class="jp-joker-card' + (selected ? ' jp-joker-card--selected' : '') + '" role="img" aria-label="' + safe(label) + '"' + (selected ? ' aria-current="true"' : '') + '><span aria-hidden="true">' + safe(text('cards.jokerShort')) + '</span></span>';
}


// Render a natural or joker card with a fully localized accessible name.
function localizedCard(card, options = {}) {
  // Route the single joker through game-owned markup because the shared primitive models standard decks.
  if (card === JOKER_CODE) return renderJokerCard(options);
  // Normalize the compact rank from every character before the suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build the semantic card name entirely from localized rank and suit resources.
  const label = text('cards.cardLabel', { rank: text('ranks.' + rank), suit: text('suits.' + suit) });
  // Replace the primitive default English label while retaining accessible markup.
  return renderCard(card, options).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(label) + '"');
}


// Return the active hold round or newest settled round for one stable stage.
function currentRound() {
  // Prefer the actionable round before bounded chronological history.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}


// Translate internal round state into concise player-facing status.
function phaseLabel(roundItem) {
  // Show the ready phase before the first deal.
  if (!roundItem) return text('phases.ready');
  // Show the active hold decision phase.
  if (roundItem.phase === 'hold') return text('phases.hold');
  // Show a localized terminal outcome without exposing the API enum.
  return text('phases.' + (roundItem.result?.outcome || 'settled'));
}


// Normalize the wager input into the documented ledger-compatible range.
function wagerValue(value) {
  // Convert the browser value while preserving the prior selection after malformed input.
  const parsed = Number(value);
  // Reuse the prior wager when the browser value is not finite.
  if (!Number.isFinite(parsed)) return wager;
  // Clamp the configured amount to the public API boundary.
  return Math.min(100000, Math.max(0.01, Math.round(parsed * 100) / 100));
}


// Translate one compact card code into a localized short display string.
function cardShortLabel(card) {
  // Return the localized joker name for the special game-owned card.
  if (card === JOKER_CODE) return text('cards.jokerShort');
  // Normalize the compact rank from every character before the suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Return a compact localized card code for joker-substitution context.
  return text('cards.shortLabel', { rank: text('ranks.' + rank), suit: text('suitsShort.' + suit) });
}


// Render one selectable source card through the accessible renderer.
function sourceCard(card, position, held, disabled) {
  // Resolve the action label from the current selection state.
  const actionLabel = held ? text('cards.release', { position: position + 1 }) : text('cards.hold', { position: position + 1 });
  // Render a semantic button whose selected state is communicated beyond color.
  return '<button type="button" class="jp-card-button' + (held ? ' is-held' : '') + '" data-hold-position="' + position + '" aria-pressed="' + held + '" aria-label="' + safe(actionLabel) + '"' + (disabled ? ' disabled' : '') + '>' + localizedCard(card, { selected: held }) + (held ? '<span class="jp-held-label">' + safe(text('cards.held')) + '</span>' : '') + '</button>';
}


// Render the five-card source hand used for hold decisions.
function sourceHand(roundItem) {
  // Build a set so selected positions can be checked without order assumptions.
  const held = new Set(roundItem.holds || []);
  // Disable selection outside the hold phase or during an atomic request.
  const disabled = roundItem.phase !== 'hold' || busy || Boolean(pendingDraw);
  // Render all five source positions with localized group semantics.
  const cards = (roundItem.initial_hand || []).map((card, position) => sourceCard(card, position, held.has(position), disabled)).join('');
  // Return the dominant source-hand region with a stable browser-test hook.
  return '<section class="jp-source" aria-label="' + safe(text('stage.sourceHand')) + '" data-testid="joker-poker-source-hand"><p class="jp-stage-kicker">' + safe(text('stage.deckProfile')) + '</p><div class="jp-card-row">' + cards + '</div></section>';
}


// Render the completed final hand and return summary.
function resultHtml(result) {
  // Render final cards as non-interactive accessible elements.
  const cards = (result?.cards || []).map(card => localizedCard(card)).join('');
  // Translate the game-owned outcome key through the active locale.
  const outcome = result ? text('outcomes.' + result.outcome) : text('summary.pending');
  // Build optional joker-substitution copy when the engine publishes it.
  const jokerAs = result?.joker_as ? '<p class="jp-joker-as">' + safe(text('results.jokerAs', { card: cardShortLabel(result.joker_as) })) + '</p>' : '';
  // Return one stable final-hand region with payout facts.
  return '<section class="jp-result" data-testid="joker-poker-result"><header><h2>' + safe(text('results.title')) + '</h2><strong>' + safe(outcome) + '</strong></header><div class="jp-card-row" role="group" aria-label="' + safe(text('results.finalCards')) + '">' + cards + '</div>' + jokerAs + '<p>' + safe(text('summary.payout')) + ': <strong>' + safe(tokenAmount(result?.payout || 0)) + '</strong></p></section>';
}


// Render the dominant game stage for idle, hold, and settled states.
function stageHtml(roundItem) {
  // Render localized readiness copy before the first wager.
  if (!roundItem) return '<section class="jp-empty" data-testid="joker-poker-empty"><h2>' + safe(text('stage.readyTitle')) + '</h2><p>' + safe(text('stage.readyBody')) + '</p></section>';
  // Build the aggregate settlement summary only after a draw.
  const summary = roundItem.phase === 'settled' ? '<section class="jp-summary" data-testid="joker-poker-summary"><span>' + safe(text('summary.wager')) + '<strong>' + safe(tokenAmount(roundItem.wager)) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(tokenAmount(roundItem.total_payout)) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(tokenAmount(roundItem.net)) + '</strong></span></section>' : '';
  // Return source cards, optional summary, and optional final hand.
  return sourceHand(roundItem) + summary + (roundItem.result ? resultHtml(roundItem.result) : '');
}


// Render the control rail for dealing and drawing one hand.
function controlsHtml(roundItem) {
  // Lock configuration while a round or ambiguous deal retry owns its wager.
  const wagerDisabled = Boolean(state?.active_round) || busy || Boolean(pendingDeal);
  // Keep the deal action available for the exact same unresolved retry.
  const dealDisabled = Boolean(state?.active_round) || busy;
  // Enable draw only while the source hand awaits held-card decisions.
  const drawDisabled = !roundItem || roundItem.phase !== 'hold' || busy || Boolean(pendingDeal);
  // Explain why configuration remains locked after an ambiguous response.
  const retryHelp = pendingDeal || pendingDraw ? '<p class="jp-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Change the deal label when the same unresolved action can be retried.
  const dealLabel = pendingDeal ? text('controls.retryDeal') : text('controls.deal');
  // Change the draw label when the same unresolved action can be retried.
  const drawLabel = pendingDraw ? text('controls.retryDraw') : text('controls.draw');
  // Return a stable control rail whose primary actions never move between phases.
  return '<aside class="jp-panel jp-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="jp-wager">' + safe(text('controls.wager')) + '</label><input id="jp-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (wagerDisabled ? ' disabled' : '') + '><p class="jp-total">' + safe(text('controls.singleHand')) + ': <strong>' + safe(tokenAmount(wager)) + '</strong></p><button type="button" class="jp-primary" data-action="deal"' + (dealDisabled ? ' disabled' : '') + '>' + safe(dealLabel) + '</button><button type="button" data-action="draw"' + (drawDisabled ? ' disabled' : '') + '>' + safe(drawLabel) + '</button><p class="jp-help">' + safe(text('controls.holdHelp')) + '</p>' + retryHelp + '<p class="jp-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}


// Render the Joker Poker paytable in the data rail.
function paytableHtml() {
  // Read the server-published paytable while preserving an empty fallback during loading.
  const paytable = rules.paytable || {};
  // Read the server-published order so frontend copy follows the API contract.
  const order = rules.outcome_order || [];
  // Render every qualifying outcome in canonical strength order.
  const rows = order.filter(outcome => outcome !== 'no_win').map(outcome => '<tr><th scope="row">' + safe(text('outcomes.' + outcome)) + '</th><td>' + safe(text('paytable.multiplier', { value: paytable[outcome] ?? 0 })) + '</td></tr>').join('');
  // Return one keyboard-readable table without nested scrolling containers.
  return '<section><h2>' + safe(text('paytable.title')) + '</h2><table><thead><tr><th>' + safe(text('paytable.result')) + '</th><th>' + safe(text('paytable.return')) + '</th></tr></thead><tbody>' + rows + '</tbody></table><p>' + safe(text('paytable.note')) + '</p></section>';
}


// Render bounded reload-safe history with localized results and accessible row names.
function historyHtml() {
  // Copy newest settled rounds first without mutating authenticated state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show an explicit localized empty state before the first settlement.
  if (!rounds.length) return '<p class="jp-empty-history">' + safe(text('history.empty')) + '</p>';
  // Render every bounded server-owned round as one concise result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the retained outcome without exposing its API value.
    const outcome = text('outcomes.' + roundItem.result.outcome);
    // Build a localized accessible row name with a stable newest-first number.
    const label = text('history.roundAria', { number: rounds.length - index, outcome });
    // Return one aligned history row with explicit returned-token wording.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(outcome) + '</span><strong>' + safe(tokenAmount(roundItem.total_payout)) + '</strong></li>';
  // Join bounded rows into the single intentional history scroll surface.
  }).join('');
  // Return one intentional keyboard-focusable scroll region without nested scrolling.
  return '<ol class="jp-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}


// Render rules and recent results in the supporting data rail.
function dataHtml() {
  // Return distinct paytable and history regions in one supporting rail.
  return '<aside class="jp-panel jp-data" aria-label="' + safe(text('data.title')) + '">' + paytableHtml() + '<section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}


// Return scoped responsive styles without modifying the shared application stylesheet.
function stylesHtml() {
  // Define the dominant stage, stable controls, responsive stack, focus, and reduced-motion rules.
  return '<style>/* Establish the Joker Poker header and desktop control-stage-data hierarchy. */.jp-shell{display:grid;gap:16px;min-width:0}.jp-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.jp-header h1{margin:0}.jp-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.jp-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.jp-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(540px,2.4fr) minmax(250px,.88fr);gap:16px;align-items:start}.jp-panel,.jp-stage{border:1px solid var(--border);border-radius:16px;background:rgba(20,10,34,.86);padding:16px}.jp-controls,.jp-data{display:grid;align-content:start;gap:13px}.jp-controls h2,.jp-data h2{margin:0}.jp-controls input,.jp-controls button{min-height:44px}.jp-primary{background:var(--red,#a51f2d);color:#fff}.jp-help,.jp-retry,.jp-total,.jp-empty-history,.jp-data p{color:var(--muted,#b8c8c1)}.jp-error{min-height:1.4em;margin:0;color:var(--bad)}.jp-stage{display:grid;align-content:center;gap:18px;min-width:0;min-height:430px;background:radial-gradient(circle at 50% 35%,rgba(20,10,34,.42),rgba(20,10,34,.96) 70%)}.jp-stage-kicker{margin:0 0 10px;text-align:center}.jp-card-row{display:flex;flex-wrap:wrap;justify-content:center;gap:9px}.jp-card-button{position:relative;min-width:58px;min-height:86px;padding:2px;border:2px solid transparent;background:transparent}.jp-card-button.is-held{border-color:var(--gold);border-radius:10px}.jp-held-label{position:absolute;inset:auto 3px 3px;padding:2px 5px;border-radius:999px;background:var(--felt);color:var(--gold);font-size:10px}.jp-joker-card{display:inline-grid;place-items:center;min-width:3.7rem;aspect-ratio:2.5/3.5;border:1px solid rgba(255,255,255,.82);border-radius:8px;background:linear-gradient(145deg,#fcf8e8,#d8f3ef);color:#13261f;font-weight:800;letter-spacing:0}.jp-joker-card--selected{box-shadow:0 0 0 3px var(--gold)}.jp-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.jp-summary span{display:grid;gap:5px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.jp-summary strong{overflow-wrap:anywhere}.jp-result{display:grid;gap:10px;padding:12px;border:1px solid rgba(255,255,255,.12);border-radius:12px;background:rgba(0,0,0,.16)}.jp-result header{display:flex;justify-content:space-between;gap:8px}.jp-result h2,.jp-result p{margin:0}.jp-joker-as{text-align:center;color:var(--gold,#f6d47a)}.jp-empty{min-height:330px;display:grid;place-content:center;text-align:center}.jp-data section{display:grid;gap:10px}.jp-data table{width:100%;border-collapse:collapse}.jp-data th,.jp-data td{padding:7px 4px;border-bottom:1px solid rgba(255,255,255,.1);text-align:left}.jp-history-list{display:grid;gap:8px;max-height:260px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.jp-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:9px;background:rgba(0,0,0,.2)}.jp-shell button:focus-visible,.jp-shell input:focus-visible,.jp-history-list:focus-visible{outline:3px solid var(--gold);outline-offset:2px}/* Stack controls, stage, and data on compact screens. */@media(max-width:1100px){.jp-layout{grid-template-columns:1fr}.jp-controls{order:1}.jp-stage{order:2;min-height:360px}.jp-data{order:3}}/* Prevent card, summary, and action clipping on mobile. */@media(max-width:520px){.jp-header{align-items:start;flex-direction:column}.jp-panel,.jp-stage{padding:12px}.jp-stage{min-height:320px}.jp-card-button{min-width:48px;min-height:72px}.jp-joker-card{min-width:3rem}.jp-summary{grid-template-columns:1fr}.jp-history-list li{grid-template-columns:1fr}}/* Remove decorative motion for reduced-motion users. */@media(prefers-reduced-motion:reduce){.jp-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}</style>';
}


// Bind semantic controls after each deterministic route render.
function bindEvents() {
  // Read the wager control once from the newly rendered rail.
  const wagerInput = root?.querySelector('#jp-wager');
  // Preserve valid wager edits without moving fake tokens.
  if (wagerInput) wagerInput.onchange = () => { wager = wagerValue(wagerInput.value); render(); };
  // Read the stable deal action control.
  const dealButton = root?.querySelector('[data-action="deal"]');
  // Prepare or retry the exact same deal identity and immutable wager.
  if (dealButton) dealButton.onclick = () => {
    // Capture the configured wager before the busy render replaces the input.
    wager = wagerValue(wagerInput?.value ?? wager);
    // Preserve an unresolved action rather than charging a new identity after a lost response.
    pendingDeal = pendingDeal || { actionId: nextActionId(), wager };
    // Execute the prepared request through shared busy and error handling.
    runAction(deal);
  };
  // Wire every source card to reload-safe hold persistence.
  root?.querySelectorAll('[data-hold-position]').forEach(button => {
    // Toggle the selected position through the public API.
    button.onclick = () => runAction(() => toggleHold(Number(button.dataset.holdPosition)));
  });
  // Read the stable draw action control.
  const drawButton = root?.querySelector('[data-action="draw"]');
  // Prepare or retry the exact same draw identity and held positions.
  if (drawButton) drawButton.onclick = () => {
    // Read the current authenticated active round before preparing an action.
    const activeRound = state?.active_round;
    // Ignore stale clicks after settlement or route-state replacement.
    if (!activeRound || activeRound.phase !== 'hold') return;
    // Preserve an unresolved draw rather than generating another settlement identity.
    pendingDraw = pendingDraw || { actionId: nextActionId(), roundId: activeRound.round_id, holds: [...(activeRound.holds || [])] };
    // Execute the prepared draw through shared busy and error handling.
    runAction(draw);
  };
}


// Render all game-owned regions from authenticated server state and locale resources.
function render() {
  // Stop late callbacks after the shell unmounts this route.
  if (!root) return;
  // Read the active or newest settled round once for a consistent frame.
  const roundItem = currentRound();
  // Build the translated game header before combining layout regions.
  const header = '<header class="jp-header"><div><p class="jp-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="jp-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the control-stage-data layout in responsive reading order.
  const layout = '<div class="jp-layout">' + controlsHtml(roundItem) + '<main class="jp-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = stylesHtml() + '<section class="jp-shell" data-testid="joker-poker">' + header + layout + '</section>';
  // Attach handlers to the newly rendered semantic controls.
  bindEvents();
}


// Execute one atomic browser action with stable disabled-state and localized cleanup.
async function runAction(action) {
  // Ignore overlapping or detached action requests.
  if (busy || !root) return;
  // Lock controls before the network action starts.
  busy = true;
  // Clear stale feedback while preserving unresolved action identities.
  lastErrorKey = null;
  // Render the stable pending frame.
  render();
  // Start protected handling so API failures remain localized.
  try {
    // Execute the prepared public game action.
    await action();
  // Translate failures without displaying server-owned English.
  } catch (error) {
    // Store the owned localized error key for the route region.
    lastErrorKey = errorKey(error);
    // Use the shared feedback surface only while this route remains mounted.
    if (root) toast(text(lastErrorKey));
  // Always release the control lock after success or failure.
  } finally {
    // Allow an exact unresolved retry or the next server-approved action.
    busy = false;
    // Rerender only when the route remains mounted.
    render();
  }
}


// Start or replay one idempotent wagered Joker Poker deal.
async function deal() {
  // Capture the route node so late responses cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the prepared immutable action created by the click handler.
  const request = pendingDeal;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Post exactly the documented action identity and wager without a caller player id.
  const payload = await post(API_ROOT + '/rounds', { action_id: request.actionId, wager: request.wager });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the authoritative reload-safe player state.
  state = payload.state;
  // Store server-published fixed rules for the data rail.
  rules = payload.rules || rules;
  // Adopt the committed wager from the returned round.
  wager = payload.round?.wager || request.wager;
  // Clear the retry identity only after a successful response proves the deal.
  pendingDeal = null;
  // Clear any stale draw preparation after a new round starts.
  pendingDraw = null;
  // Refresh the persistent authenticated wallet after the ledger debit.
  await refreshBalance();
}


// Persist one changed hold position for reload-safe continuation.
async function toggleHold(position) {
  // Capture the route node so late responses cannot overwrite a later mount.
  const mountedRoot = root;
  // Read the active source hand before constructing the next selection.
  const roundItem = state?.active_round;
  // Stop stale clicks when the active round has already settled.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Build a mutable selection set from server state.
  const holds = new Set(roundItem.holds || []);
  // Remove an already-held position or add a newly held one.
  if (holds.has(position)) holds.delete(position); else holds.add(position);
  // Persist the canonical selection through the game API.
  const payload = await post(API_ROOT + '/rounds/' + encodeURIComponent(roundItem.round_id) + '/holds', { holds: [...holds].sort((left, right) => left - right) });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the returned reload-safe state.
  state = payload.state;
}


// Submit or replay one draw and settlement action.
async function draw() {
  // Capture the route node so late settlement cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the immutable prepared draw created by the action handler.
  const request = pendingDraw;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Encode the server-owned round id before building the public route.
  const roundId = encodeURIComponent(request.roundId);
  // Post exactly the documented action identity and held positions without a caller player id.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/draw', { action_id: request.actionId, holds: request.holds });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the terminal reload-safe state and bounded history.
  state = payload.state;
  // Refresh fixed rules when the response includes them.
  rules = payload.rules || rules;
  // Clear the retry identity only after the settled response is available.
  pendingDraw = null;
  // Clear any obsolete deal identity after terminal settlement.
  pendingDeal = null;
  // Refresh the persistent authenticated wallet after payout or loss.
  await refreshBalance();
}


// Export the catalog-owned lazy game module contract.
export const JokerPokerGame = {
  // Expose the stable descriptor identifier without player-visible copy.
  id: 'joker_poker',
  // Leave navigation labels to module-owned catalog metadata and translations.
  label: '',
  // Load locale and authenticated state before showing the game.
  async mount(node) {
    // Store the shell-provided route outlet immediately.
    root = node;
    // Reset route-owned transient state for a clean mount.
    busy = false;
    // Clear stale localized feedback from a prior mount.
    lastErrorKey = null;
    // Clear retry identities because reload-safe server state reconciles committed actions.
    pendingDeal = null;
    // Clear any prior draw identity before reading current server state.
    pendingDraw = null;
    // Install shared accessible card presentation once.
    ensureSharedCardStyles();
    // Capture this mount node for asynchronous route replacement guards.
    const mountedRoot = root;
    // Load active and fallback game dictionaries before rendering visible copy.
    await loadI18nDomain(DOMAIN);
    // Stop when locale loading completed after this route was replaced.
    if (root !== mountedRoot) return;
    // Rerender locale copy in place without discarding authenticated game state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read reload-safe state through the authenticated session.
    const payload = await api(API_ROOT + '/state');
    // Stop when state loading completed after this route was replaced.
    if (root !== mountedRoot) return;
    // Cache the current player sanitized game state.
    state = payload.state;
    // Cache the documented fixed rule metadata.
    rules = payload.rules || {};
    // Restore the active round wager into the locked control when present.
    wager = state?.active_round?.wager || wager;
    // Render the complete game-owned browser surface.
    render();
    // Align the persistent wallet with any recovered ledger marker.
    await refreshBalance();
  },
  // Release every game-owned lifecycle reference on route change.
  unmount() {
    // Remove the locale callback when initialization reached subscription.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated teardown stays harmless.
    unsubscribeLocale = null;
    // Clear the outlet before late promises can render into another route.
    root = null;
    // Clear authenticated state from the inactive singleton module.
    state = null;
    // Clear server rules so the next mount reloads authoritative metadata.
    rules = {};
    // Release the in-flight presentation lock.
    busy = false;
    // Forget route-local retry identities after server state becomes the recovery source.
    pendingDeal = null;
    // Forget the route-local draw identity after teardown.
    pendingDraw = null;
    // Clear the reserved localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this game.
  },
};
