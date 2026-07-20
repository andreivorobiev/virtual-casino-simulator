// Implement the isolated Casino Hold'em browser module for GitHub issue #139.

// Import authenticated envelope-aware API helpers without sending caller-owned player ids.
import { api, post } from '../core/api.js';
// Import the shared accessible card renderer allocated by issue #96.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the game-owned locale domain.
const DOMAIN = 'games/casino_holdem';
// Address the additive frozen-v1 Casino Hold'em API through one stable root.
const API_ROOT = '/api/v1/games/casino-holdem';
// Identify the shared card stylesheet so repeated route mounts install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the two documented decisions in stable control order.
const DECISIONS = ['call', 'fold'];

// Retain the current shell outlet for deterministic rerenders and stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published rule metadata for reload-safe presentation.
let rules = {};
// Retain the configured ante until a round starts or the player changes it.
let wager = 5;
// Prevent overlapping atomic deal or decision actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain an unresolved deal identity and immutable ante for safe retry.
let pendingDeal = null;
// Retain an unresolved decision identity, round, and decision for safe retry.
let pendingDecision = null;
// Retain a localized error resource key for the reserved route error region.
let lastErrorKey = null;
// Allocate stable fallback identities when randomUUID is unavailable.
let actionCounter = 0;

// Resolve one game-owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every visible and accessible label to the active EN/RU dictionary.
  return t(key, params, DOMAIN);
}

// Format one play-token amount without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Format ledger precision through the active locale.
  const amount = formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Wrap the number in explicit localized play-token terminology.
  return text('tokens.amount', { amount });
}

// Create one bounded client action identity for exactly-once network retries.
function nextActionId() {
  // Prefer the browser cryptographic UUID source when available.
  if (globalThis.crypto?.randomUUID) return 'casino-holdem-' + globalThis.crypto.randomUUID();
  // Advance a per-module counter before building the fallback identity.
  actionCounter += 1;
  // Combine a timestamp and counter without presenting the value to the player.
  return 'casino-holdem-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
}

// Map public API diagnostics to owned localized feedback.
function errorKey(error) {
  // Normalize the optional envelope code without exposing server text.
  const code = String(error?.code || '').toUpperCase();
  // Explain an insufficient play-token balance through local copy.
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

// Render a shared visible or hidden card with a fully localized accessible name.
function localizedCard(card, options = {}) {
  // Read explicit hidden state while treating a missing card as protected.
  const hidden = options.hidden === true || !card;
  // Render a localized face-down card without exposing its future identity.
  if (hidden) {
    // Replace the primitive English compatibility label with owned EN/RU copy.
    return renderCard('??', { hidden: true }).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(text('cards.faceDown')) + '"');
  }
  // Normalize the compact rank from every character before the suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build the semantic card name entirely from localized rank and suit resources.
  const label = text('cards.cardLabel', { rank: text('ranks.' + rank), suit: text('suits.' + suit) });
  // Replace the primitive default English label while retaining accessible markup.
  return renderCard(card).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(label) + '"');
}

// Return the active decision round or newest terminal round for one stable stage.
function currentRound() {
  // Prefer the actionable round before bounded chronological history.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}

// Translate internal round state into concise player-facing status.
function phaseLabel(roundItem) {
  // Show the ready phase before the first ante.
  if (!roundItem) return text('phases.ready');
  // Show the active call-or-fold decision phase.
  if (roundItem.phase === 'decision') return text('phases.decision');
  // Show an in-between call commitment phase only during retry recovery.
  if (roundItem.phase === 'called') return text('phases.called');
  // Show a localized terminal outcome without exposing the API enum.
  return text('phases.' + (roundItem.outcome || 'ready'));
}

// Normalize the ante input into the documented ledger-compatible range.
function wagerValue(value) {
  // Convert the browser value while preserving the prior selection after malformed input.
  const parsed = Number(value);
  // Reuse the prior wager when the browser value is not finite.
  if (!Number.isFinite(parsed)) return wager;
  // Clamp the configured amount to the public API boundary.
  return Math.min(100000, Math.max(0.01, Math.round(parsed * 100) / 100));
}

// Render one labeled card row while preserving hidden slots.
function cardRow(labelKey, cards, options = {}) {
  // Build the fixed number of slots requested by the table area.
  const slots = Array.from({ length: options.slots || cards.length }, (_, index) => localizedCard(cards[index], { hidden: options.hidden || !cards[index] })).join('');
  // Return one accessible group with localized label text.
  return '<section class="choldem-card-row" aria-label="' + safe(text(labelKey + '.aria')) + '"><h3>' + safe(text(labelKey + '.title')) + '</h3><div class="choldem-cards">' + slots + '</div></section>';
}

// Render the control rail for ante deal and call/fold decisions.
function controlsHtml() {
  // Read the only actionable round from authenticated server state.
  const activeRound = state?.active_round;
  // Allow decisions only while the flop is waiting for the player.
  const canDecide = activeRound?.phase === 'decision';
  // Lock ante configuration while a round or ambiguous deal retry owns its wager.
  const wagerDisabled = Boolean(activeRound) || busy || Boolean(pendingDeal);
  // Keep the deal action available for the exact same unresolved retry.
  const dealDisabled = Boolean(activeRound) || busy;
  // Read the unresolved decision so the opposite semantic action stays disabled.
  const pendingChoice = pendingDecision?.decision || null;
  // Build both accessible decision controls from one canonical value list.
  const decisionButtons = DECISIONS.map(decision => {
    // Disable stale, overlapping, or opposite-decision commands.
    const disabled = !canDecide || busy || Boolean(pendingChoice && pendingChoice !== decision);
    // Return one semantic action button with a stable hook.
    return '<button type="button" class="choldem-decision choldem-decision-' + decision + '" data-decision="' + decision + '"' + (disabled ? ' disabled' : '') + '>' + safe(text('controls.' + decision)) + '</button>';
  // Join the two controls without adding decorative text nodes.
  }).join('');
  // Explain why configuration remains locked after an ambiguous response.
  const retryHelp = pendingDeal || pendingDecision ? '<p class="choldem-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Change the deal label when the same unresolved action can be retried.
  const dealLabel = pendingDeal ? text('controls.retryDeal') : text('controls.deal');
  // Return a stable control rail whose primary actions never move between phases.
  return '<aside class="choldem-panel choldem-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="choldem-wager">' + safe(text('controls.ante')) + '</label><input id="choldem-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (wagerDisabled ? ' disabled' : '') + '><button type="button" class="choldem-primary" data-action="deal"' + (dealDisabled ? ' disabled' : '') + '>' + safe(dealLabel) + '</button><fieldset' + (canDecide ? '' : ' disabled') + '><legend>' + safe(text('controls.decision')) + '</legend><div class="choldem-decisions">' + decisionButtons + '</div></fieldset><p class="choldem-help">' + safe(text('controls.decisionHelp')) + '</p>' + retryHelp + '<p class="choldem-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render the player hand, community board, and protected dealer hand.
function stageHtml(roundItem) {
  // Read public player cards after a round starts.
  const playerCards = roundItem?.player_cards || [];
  // Read the public board, using hidden slots for unrevealed turn and river.
  const communityCards = roundItem?.community_cards || [];
  // Reveal dealer cards only after a called showdown.
  const dealerCards = roundItem?.dealer_cards || [];
  // Explain the current stage without exposing internal state names.
  const message = !roundItem ? text('stage.readyBody') : roundItem.phase === 'decision' ? text('stage.decisionBody') : text('results.' + (roundItem.outcome || 'dealer_not_qualified'));
  // Return fixed card rows so the stage does not resize during settlement.
  return '<div class="choldem-table-felt">' + cardRow('dealer', dealerCards, { slots: 2, hidden: !dealerCards.length }) + cardRow('board', communityCards, { slots: 5 }) + cardRow('player', playerCards, { slots: 2 }) + '</div><p class="choldem-result" role="status" aria-live="polite">' + safe(message) + '</p>';
}

// Render wager and settlement facts in one reserved summary region.
function summaryHtml(roundItem) {
  // Show a localized placeholder before values become available.
  const pending = text('summary.pending');
  // Format the committed ante when a round exists.
  const ante = roundItem ? tokenAmount(roundItem.wager) : pending;
  // Format the required call wager after a call is prepared or settled.
  const call = roundItem?.call_wager ? tokenAmount(roundItem.call_wager) : pending;
  // Translate dealer qualification when it is known.
  const qualifies = typeof roundItem?.dealer_qualifies === 'boolean' ? text(roundItem.dealer_qualifies ? 'summary.qualifiesYes' : 'summary.qualifiesNo') : pending;
  // Format returned tokens only for a terminal round.
  const payout = roundItem?.phase === 'settled' ? tokenAmount(roundItem.payout) : pending;
  // Format the signed net result only for a terminal round.
  const net = roundItem?.phase === 'settled' ? tokenAmount(roundItem.net) : pending;
  // Return aligned facts that retain the same positions through every phase.
  return '<section class="choldem-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.ante')) + '<strong>' + safe(ante) + '</strong></span><span>' + safe(text('summary.call')) + '<strong>' + safe(call) + '</strong></span><span>' + safe(text('summary.dealer')) + '<strong>' + safe(qualifies) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(payout) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(net) + '</strong></span></section>';
}

// Render bounded reload-safe history with localized results and accessible row names.
function historyHtml() {
  // Copy newest terminal rounds first without mutating authenticated state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show an explicit localized empty state before the first settlement.
  if (!rounds.length) return '<p class="choldem-empty">' + safe(text('history.empty')) + '</p>';
  // Render every bounded server-owned round as one concise result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the retained outcome without exposing its API value.
    const outcome = text('outcomes.' + roundItem.outcome);
    // Translate the retained player rank or fold placeholder.
    const rank = roundItem.player_rank ? text('ranksMade.' + roundItem.player_rank) : text('history.foldRank');
    // Build a localized accessible row name with a stable newest-first number.
    const label = text('history.roundAria', { number: rounds.length - index, outcome, rank });
    // Return one aligned history row with explicit returned-token wording.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(text('history.result', { outcome, rank })) + '</span><strong>' + safe(tokenAmount(roundItem.payout)) + '</strong></li>';
  // Join bounded rows into the single intentional history scroll surface.
  }).join('');
  // Return one intentional keyboard-focusable scroll region without nested scrolling.
  return '<ol class="choldem-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render the rules and recent results in the supporting data rail.
// Render the server-owned ante payout schedule so the raise/bonus economics are player-visible. (issue #253)
function paytableHtml() {
  // Fix the display order from the strongest to the weakest paying category.
  const rankOrder = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'one_pair', 'high_card'];
  // Read the published returned-credit multipliers straight from the authoritative rules payload.
  const multipliers = rules.ante_return_multipliers || {};
  // Build one localized row per published category showing its net odds.
  const rows = rankOrder.filter(rank => multipliers[rank]).map(rank => '<li><span>' + safe(text('paytable.rank.' + rank)) + '</span><strong>' + safe(text('paytable.net', { net: multipliers[rank] - 1 })) + '</strong></li>').join('');
  // Return the disclosure section only when the server has published the schedule.
  return rows ? '<section data-testid="choldem-paytable"><h2>' + safe(text('paytable.title')) + '</h2><ul class="choldem-paytable">' + rows + '</ul></section>' : '';
}

function dataHtml() {
  // Read server rule values while preserving documented defaults during initial loading.
  const callMultiplier = rules.call_multiplier || 2;
  // Return distinct rule, payout-schedule, and history regions in one supporting rail.
  return '<aside class="choldem-panel choldem-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul class="choldem-rules"><li>' + safe(text('rules.callMultiplier', { multiplier: callMultiplier })) + '</li><li>' + safe(text('rules.dealerQualifies')) + '</li><li>' + safe(text('rules.noValue')) + '</li></ul></section>' + paytableHtml() + '<section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive styles without modifying the shared application stylesheet.
function stylesHtml() {
  // Define the dominant stage, stable controls, responsive stack, focus, and reduced-motion rules.
  return '<style>/* Establish the game header and desktop control-stage-data hierarchy. */.choldem-shell{display:grid;gap:16px;min-width:0}.choldem-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.choldem-header h1{margin:0}.choldem-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.choldem-phase{padding:7px 12px;border:1px solid rgba(255,215,128,.45);border-radius:999px;color:var(--gold,#f6d47a)}.choldem-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(560px,2.5fr) minmax(240px,.82fr);gap:16px;align-items:start}.choldem-panel,.choldem-stage{border:1px solid rgba(255,215,128,.24);border-radius:16px;background:rgba(3,29,20,.86);padding:16px}.choldem-controls,.choldem-data{display:grid;align-content:start;gap:13px}.choldem-controls h2,.choldem-data h2{margin:0}.choldem-controls fieldset{margin:0;padding:0;border:0}.choldem-controls legend{margin-bottom:8px}.choldem-controls input,.choldem-controls button{min-height:44px}.choldem-primary{background:var(--red,#a51f2d);color:#fff}.choldem-decisions{display:grid;grid-template-columns:1fr 1fr;gap:10px}.choldem-help,.choldem-retry,.choldem-empty{color:var(--muted,#b8c8c1)}.choldem-error{min-height:1.4em;margin:0;color:#ffd1d1}.choldem-stage{display:grid;align-content:center;gap:18px;min-width:0;min-height:500px;background:radial-gradient(circle at 50% 44%,rgba(35,130,82,.45),rgba(3,24,17,.98) 70%)}.choldem-table-felt{display:grid;gap:18px}.choldem-card-row{display:grid;justify-items:center;gap:10px}.choldem-card-row h3{margin:0}.choldem-cards{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;min-height:96px}.choldem-cards .playing-card{flex:none;width:clamp(4.2rem,7vw,6.6rem);font-size:clamp(1rem,2vw,1.55rem)}.choldem-result{min-height:2.8em;margin:0;text-align:center}.choldem-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.choldem-summary span{display:grid;gap:5px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.choldem-summary strong{overflow-wrap:anywhere}.choldem-data section{display:grid;gap:10px}.choldem-rules{margin:0;padding-left:1.1rem}.choldem-rules li+li{margin-top:7px}.choldem-paytable{margin:0;padding:0;list-style:none;display:grid;gap:6px}.choldem-paytable li{display:grid;grid-template-columns:1fr auto;gap:8px;margin:0;padding:7px 9px;border-radius:8px;background:rgba(0,0,0,.18)}.choldem-paytable strong{color:var(--gold,#f6d47a)}.choldem-history-list{display:grid;gap:8px;max-height:285px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.choldem-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:9px;background:rgba(0,0,0,.2)}.choldem-shell button:focus-visible,.choldem-shell input:focus-visible,.choldem-history-list:focus-visible{outline:3px solid #ffd780;outline-offset:2px}/* Stack controls, stage, and data on compact screens. */@media(max-width:1120px){.choldem-layout{grid-template-columns:1fr}.choldem-controls{order:1}.choldem-stage{order:2;min-height:420px}.choldem-data{order:3}}/* Prevent cards, summary, and actions from clipping on mobile. */@media(max-width:560px){.choldem-header{align-items:start;flex-direction:column}.choldem-panel,.choldem-stage{padding:12px}.choldem-stage{min-height:380px}.choldem-cards{gap:7px;min-height:82px}.choldem-cards .playing-card{width:clamp(3.4rem,18vw,4.9rem)}.choldem-summary{grid-template-columns:1fr 1fr}.choldem-decisions{grid-template-columns:1fr}.choldem-history-list li{grid-template-columns:1fr}}/* Remove decorative motion for reduced-motion users. */@media(prefers-reduced-motion:reduce){.choldem-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}</style>';
}

// Bind semantic controls after each deterministic route render.
function bindEvents() {
  // Read the ante control once from the newly rendered rail.
  const wagerInput = root?.querySelector('#choldem-wager');
  // Preserve valid ante edits without moving play tokens.
  if (wagerInput) wagerInput.onchange = () => { wager = wagerValue(wagerInput.value); render(); };
  // Read the stable deal action control.
  const dealButton = root?.querySelector('[data-action="deal"]');
  // Prepare or retry the exact same deal identity and immutable ante.
  if (dealButton) dealButton.onclick = () => {
    // Capture the configured ante before the busy render replaces the input.
    wager = wagerValue(wagerInput?.value ?? wager);
    // Preserve an unresolved action rather than charging a new identity after a lost response.
    pendingDeal = pendingDeal || { actionId: nextActionId(), wager };
    // Execute the prepared request through shared busy and error handling.
    runAction(deal);
  };
  // Bind both decision actions through one public decision path.
  root?.querySelectorAll('[data-decision]').forEach(button => {
    // Prepare or retry only the same round and decision after an ambiguous response.
    button.onclick = () => {
      // Read the current authenticated active round before preparing an action.
      const activeRound = state?.active_round;
      // Ignore stale clicks after settlement or route-state replacement.
      if (!activeRound || activeRound.phase !== 'decision') return;
      // Read the canonical decision from the semantic data attribute.
      const decision = button.dataset.decision;
      // Preserve an unresolved action rather than generating another settlement identity.
      pendingDecision = pendingDecision || { actionId: nextActionId(), roundId: activeRound.round_id, decision };
      // Ignore an opposite-decision click while the original semantic request is unresolved.
      if (pendingDecision.roundId !== activeRound.round_id || pendingDecision.decision !== decision) return;
      // Execute the prepared decision through shared busy and error handling.
      runAction(submitDecision);
    };
  });
}

// Render all game-owned regions from authenticated server state and locale resources.
function render() {
  // Stop late callbacks after the shell unmounts this route.
  if (!root) return;
  // Read the active or newest terminal round once for a consistent frame.
  const roundItem = currentRound();
  // Build the translated game header before combining layout regions.
  const header = '<header class="choldem-header"><div><p class="choldem-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="choldem-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the control-stage-data layout in responsive reading order.
  const layout = '<div class="choldem-layout">' + controlsHtml() + '<main class="choldem-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + summaryHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = stylesHtml() + '<section class="choldem-shell" data-testid="casino-holdem">' + header + layout + '</section>';
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

// Start or replay one idempotent ante deal.
async function deal() {
  // Capture the route node so late responses cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the prepared immutable action created by the click handler.
  const request = pendingDeal;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Post exactly the documented action identity and ante without a caller player id.
  const payload = await post(API_ROOT + '/rounds', { action_id: request.actionId, wager: request.wager });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the authoritative reload-safe player state.
  state = payload.state;
  // Store server-published fixed rules for the data rail.
  rules = payload.rules || rules;
  // Adopt the committed ante from the returned round.
  wager = payload.round?.wager || request.wager;
  // Clear the retry identity only after a successful response proves the deal.
  pendingDeal = null;
  // Clear any stale decision preparation after a new round starts.
  pendingDecision = null;
  // Refresh the persistent authenticated wallet after the ante debit.
  await refreshBalance();
}

// Submit or replay one call-or-fold decision action.
async function submitDecision() {
  // Capture the route node so late settlement cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the immutable prepared decision created by the action handler.
  const request = pendingDecision;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Encode the server-owned round id before building the public route.
  const roundId = encodeURIComponent(request.roundId);
  // Post exactly the documented action identity and decision without a caller player id.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/decision', { action_id: request.actionId, decision: request.decision });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the terminal reload-safe state and bounded history.
  state = payload.state;
  // Refresh fixed rules when the response includes them.
  rules = payload.rules || rules;
  // Clear the retry identity only after the terminal response is available.
  pendingDecision = null;
  // Clear any obsolete deal identity after terminal settlement.
  pendingDeal = null;
  // Refresh the persistent authenticated wallet after call, fold, payout, push, or loss.
  await refreshBalance();
}

// Export the catalog-owned lazy game module contract.
export const CasinoHoldemGame = {
  // Expose the stable descriptor identifier without player-visible copy.
  id: 'casino_holdem',
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
    // Clear any prior decision identity before reading current server state.
    pendingDecision = null;
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
    // Restore the active round ante into the locked control when present.
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
    // Forget the route-local decision identity after teardown.
    pendingDecision = null;
    // Clear the reserved localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this game.
  },
};
