// Implement the isolated Caribbean Stud browser module for GitHub issue #132.

// Import authenticated envelope-aware API helpers without caller-owned player ids.
import { api, post } from '../core/api.js';
// Import shared accessible card rendering from the #96 primitive lane.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the paired game-owned dictionaries.
const DOMAIN = 'games/caribbean_stud';
// Address the additive frozen-v1 proposal API through one stable root.
const API_ROOT = '/api/v1/games/caribbean-stud';
// Identify the shared card stylesheet so route mounts install it idempotently.
const CARD_STYLE_ID = 'casino-shared-card-styles';

// Retain the current route outlet for stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published fixed rule metadata.
let rules = {};
// Retain the configured ante between hands.
let ante = 5;
// Prevent overlapping atomic browser actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain unresolved action identities for exact network retries.
let pendingAction = null;
// Retain the last committed ante so one click can repeat the same round.
let lastBet = null;
// Retain one localized error key for the reserved alert region.
let lastErrorKey = null;
// Allocate fallback action identities when randomUUID is unavailable.
let actionCounter = 0;

// Resolve one localized string from the game-owned domain.
function text(key, params = {}) {
  // Delegate visible and accessible labels to the active locale resource.
  return t(key, params, DOMAIN);
}

// Format one play-token amount without currency semantics.
function tokenAmount(value) {
  // Format ledger precision through the active locale.
  const amount = formatNumber(value || 0, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Wrap the number in localized play-token wording.
  return text('tokens.amount', { amount });
}

// Create one bounded client action identity for exactly-once retries.
function nextActionId(kind) {
  // Prefer browser cryptographic UUIDs when available.
  if (globalThis.crypto?.randomUUID) return 'caribbean-stud-' + kind + '-' + globalThis.crypto.randomUUID();
  // Advance a route-local counter for fallback uniqueness.
  actionCounter += 1;
  // Combine kind, time, and counter without displaying the value.
  return 'caribbean-stud-' + kind + '-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
}

// Map public API diagnostics to owned localized feedback.
function errorKey(error) {
  // Normalize the optional envelope code.
  const code = String(error?.code || '').toUpperCase();
  // Explain insufficient play-token balance locally.
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

// Render one card with localized accessible text.
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

// Render one localized group of visible cards.
function localizedCardGroup(cards, label) {
  // Render every card with game-owned accessible labels.
  const rendered = cards.map(card => localizedCard(card)).join('');
  // Return the same group shape as the shared primitive with localized label text.
  return '<div class="playing-card-group" role="group" aria-label="' + safe(label) + '">' + rendered + '</div>';
}

// Return the active round or newest terminal round for stable rendering.
function currentRound() {
  // Prefer the open table hand before bounded history.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}

// Translate one internal phase or outcome into player-facing status.
function phaseLabel(roundItem) {
  // Show ready copy before the first deal.
  if (!roundItem) return text('phases.ready');
  // Show decision copy while the call-or-fold choice is open.
  if (roundItem.phase === 'decision') return text('phases.decision');
  // Show fold copy for an ante-forfeit terminal round.
  if (roundItem.outcome === 'fold') return text('phases.folded');
  // Show settled copy for terminal call results.
  return text('phases.settled');
}

// Normalize the ante input into the documented ledger-compatible range.
function anteValue(value) {
  // Convert the browser value to a number.
  const parsed = Number(value);
  // Reuse the prior value when the input is not finite.
  if (!Number.isFinite(parsed)) return ante;
  // Clamp and round the value to shared ledger precision.
  return Math.min(100000, Math.max(0.01, Math.round(parsed * 100) / 100));
}

// Render the control rail for ante, call, and fold.
function controlsHtml() {
  // Read the only actionable round from server state.
  const activeRound = state?.active_round;
  // Allow call and fold only during the decision phase.
  const canDecide = activeRound?.phase === 'decision';
  // Disable ante edits while a decision or pending action owns state.
  const anteDisabled = Boolean(activeRound) || busy || Boolean(pendingAction);
  // Disable dealing while an active round is open.
  const dealDisabled = Boolean(activeRound) || busy || Boolean(pendingAction && pendingAction.kind !== 'deal');
  // Disable call while no decision is open.
  const callDisabled = !canDecide || busy || Boolean(pendingAction && pendingAction.kind !== 'call');
  // Disable fold while no decision is open.
  const foldDisabled = !canDecide || busy || Boolean(pendingAction && pendingAction.kind !== 'fold');
  // Enable the one-click repeat only outside the decision phase with a stored ante and nothing in flight.
  const repeatDisabled = Boolean(activeRound) || busy || Boolean(pendingAction) || !lastBet;
  // Offer the one-click repeat only outside the open decision so call and fold stay unobstructed.
  const repeatButton = canDecide ? '' : '<button type="button" class="cs-repeat" data-action="repeat"' + (repeatDisabled ? ' disabled' : '') + '>' + safe(text('controls.repeat')) + '</button>';
  // Explain unresolved retry state when present.
  const retryHelp = pendingAction ? '<p class="cs-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Return stable controls whose positions do not change between phases.
  return '<aside class="cs-panel cs-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="cs-ante">' + safe(text('controls.ante')) + '</label><input id="cs-ante" type="number" min="0.01" max="100000" step="0.01" value="' + safe(ante) + '"' + (anteDisabled ? ' disabled' : '') + '><button type="button" data-action="deal"' + (dealDisabled ? ' disabled' : '') + '>' + safe(pendingAction?.kind === 'deal' ? text('controls.retryDeal') : text('controls.deal')) + '</button>' + repeatButton + '<button type="button" data-action="call"' + (callDisabled ? ' disabled' : '') + '>' + safe(pendingAction?.kind === 'call' ? text('controls.retryCall') : text('controls.call')) + '</button><button type="button" data-action="fold"' + (foldDisabled ? ' disabled' : '') + '>' + safe(pendingAction?.kind === 'fold' ? text('controls.retryFold') : text('controls.fold')) + '</button><p class="cs-help">' + safe(text('controls.help')) + '</p>' + retryHelp + '<p class="cs-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render player and dealer cards with dealer hole cards protected before call.
function stageHtml(roundItem) {
  // Render player cards when available.
  const playerCards = roundItem?.player_hand ? localizedCardGroup(roundItem.player_hand, text('hands.player')) : '<div class="cs-placeholder">' + safe(text('stage.readyBody')) + '</div>';
  // Render dealer cards after call, otherwise one upcard plus four protected cards.
  const dealerCards = roundItem?.dealer_hand ? localizedCardGroup(roundItem.dealer_hand, text('hands.dealer')) : '<div class="playing-card-group" role="group" aria-label="' + safe(text('hands.dealer')) + '">' + localizedCard(roundItem?.dealer_upcard, { hidden: !roundItem?.dealer_upcard }) + localizedCard(null, { hidden: true }) + localizedCard(null, { hidden: true }) + localizedCard(null, { hidden: true }) + localizedCard(null, { hidden: true }) + '</div>';
  // Select phase-specific stage copy.
  const message = !roundItem ? text('results.ready') : roundItem.phase === 'decision' ? text('results.decision') : text('results.' + (roundItem.outcome || 'ready'));
  // Return reserved hand regions so reduced-motion users see no layout jump.
  return '<section class="cs-hands" role="group" aria-label="' + safe(text('stage.cardsAria')) + '"><article><h3>' + safe(text('hands.player')) + '</h3>' + playerCards + '</article><article><h3>' + safe(text('hands.dealer')) + '</h3>' + dealerCards + '</article></section><p class="cs-result" role="status" aria-live="polite">' + safe(message) + '</p>';
}

// Render wager, return, and net facts in fixed positions.
function summaryHtml(roundItem) {
  // Use localized placeholder before facts exist.
  const pending = text('summary.pending');
  // Format the ante after a round exists.
  const roundAnte = roundItem?.ante ? tokenAmount(roundItem.ante) : pending;
  // Format the fixed call wager after call settlement.
  const call = roundItem?.call_wager ? tokenAmount(roundItem.call_wager) : pending;
  // Format the returned tokens only after terminal states.
  const payout = roundItem?.phase === 'settled' ? tokenAmount(roundItem.payout) : pending;
  // Format net result only after terminal states.
  const net = roundItem?.phase === 'settled' ? tokenAmount(roundItem.net) : pending;
  // Translate the terminal outcome when present.
  const outcome = roundItem?.outcome ? text('outcomes.' + roundItem.outcome) : pending;
  // Translate the player's evaluated hand when present.
  const rank = roundItem?.player_rank?.name ? text('handRanks.' + roundItem.player_rank.name) : pending;
  // Return aligned facts that stay stable across phases.
  return '<section class="cs-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.ante')) + '<strong>' + safe(roundAnte) + '</strong></span><span>' + safe(text('summary.call')) + '<strong>' + safe(call) + '</strong></span><span>' + safe(text('summary.rank')) + '<strong>' + safe(rank) + '</strong></span><span>' + safe(text('summary.outcome')) + '<strong>' + safe(outcome) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(payout) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(net) + '</strong></span></section>';
}

// Render bounded reload-safe history.
function historyHtml() {
  // Copy newest terminal rounds first without mutating state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show localized empty state before the first terminal round.
  if (!rounds.length) return '<p class="cs-empty">' + safe(text('history.empty')) + '</p>';
  // Render each retained result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the outcome for display and accessible labels.
    const outcome = text('outcomes.' + roundItem.outcome);
    // Format returned tokens for the row.
    const payout = tokenAmount(roundItem.payout);
    // Build one localized accessible row name.
    const label = text('history.roundAria', { number: rounds.length - index, outcome, payout });
    // Return the row with returned-token evidence.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(outcome) + '</span><strong>' + safe(payout) + '</strong></li>';
  // Join bounded rows.
  }).join('');
  // Return one intentional scroll region for history only.
  return '<ol class="cs-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render the raise payout schedule from the server-published call odds so players see hand values. (issue #253)
function paytableHtml() {
  // Read the published hand-to-odds map, tolerating an early state before rules load.
  const odds = rules.call_odds || {};
  // Order hands from strongest to weakest for a conventional payout table.
  const order = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'one_pair', 'high_card'];
  // Build one row per published hand using the existing localized rank labels.
  const rows = order.filter(name => name in odds).map(name => '<li><span>' + safe(text('handRanks.' + name)) + '</span><strong>' + safe(formatNumber(odds[name]) + ':1') + '</strong></li>').join('');
  // Skip the section entirely when no odds are available yet.
  if (!rows) return '';
  // Return the payout schedule section for the return table panel.
  return '<section><h2>' + safe(text('paytable.title')) + '</h2><ul class="cs-paytable">' + rows + '</ul></section>';
}

// Render rule and history support regions.
function dataHtml() {
  // Read the server-published call multiplier with proposal default.
  const callMultiplier = rules.call_multiplier || 2;
  // Return transparent return table and recent history.
  return '<aside class="cs-panel cs-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul><li>' + safe(text('rules.ante')) + '</li><li>' + safe(text('rules.call', { multiplier: callMultiplier })) + '</li><li>' + safe(text('rules.dealer')) + '</li><li>' + safe(text('rules.noRealValue')) + '</li><li>' + safe(text('rules.reducedMotion')) + '</li></ul></section>' + paytableHtml() + '<section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive and reduced-motion styles.
function stylesHtml() {
  // Define compact operational layout without editing shared CSS.
  return '<style>/* Define the Caribbean Stud game layout and responsive regions. */.cs-shell{display:grid;gap:16px;min-width:0}.cs-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.cs-header h1{margin:0}.cs-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.cs-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.cs-layout{display:grid;grid-template-columns:minmax(220px,.7fr) minmax(520px,2.15fr) minmax(250px,.85fr);gap:16px;align-items:start}.cs-panel,.cs-stage{border:1px solid var(--gold);border-radius:12px;background:var(--panel-strong);padding:16px}.cs-controls,.cs-data{display:grid;align-content:start;gap:12px}.cs-controls input,.cs-controls button{min-height:44px}.cs-controls button[data-action=call]{background:var(--red,#a51f2d);color:#fff}.cs-help,.cs-retry,.cs-empty{color:var(--muted,#b8c8c1)}.cs-error{min-height:1.4em;margin:0;color:#ffd1d1}.cs-stage{display:grid;align-content:center;gap:20px;min-width:0;min-height:430px;background:radial-gradient(circle at 50% 42%,rgba(35,17,61,.42),rgba(20,10,34,.96) 70%)}.cs-hands{display:grid;gap:24px}.cs-hands article{display:grid;gap:12px}.cs-hands h3{margin:0}.cs-hands .playing-card{flex:none;width:clamp(3.9rem,7vw,6.4rem);font-size:clamp(1rem,2vw,1.45rem)}.cs-placeholder{min-height:8rem;display:grid;place-items:center;border:1px dashed rgba(255,255,255,.22);border-radius:10px;color:var(--muted,#b8c8c1);text-align:center}.cs-result{min-height:2.8em;margin:0;text-align:center}.cs-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.cs-summary span{display:grid;gap:5px;padding:10px;border-radius:8px;background:rgba(255,255,255,.05)}.cs-summary strong{overflow-wrap:anywhere}.cs-data section{display:grid;gap:10px}.cs-data ul{margin:0;padding-left:1.1rem}.cs-data li+li{margin-top:7px}.cs-paytable{margin:0;padding:0;list-style:none;display:grid;gap:6px}.cs-paytable li{display:grid;grid-template-columns:1fr auto;gap:8px;margin:0;padding:7px 9px;border-radius:8px;background:rgba(0,0,0,.18)}.cs-paytable strong{color:var(--gold,#f6d47a)}.cs-history-list{display:grid;gap:8px;max-height:285px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.cs-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:8px;background:rgba(0,0,0,.2)}.cs-shell button:focus-visible,.cs-shell input:focus-visible,.cs-history-list:focus-visible{outline:3px solid var(--gold);outline-offset:2px}@media(max-width:1100px){.cs-layout{grid-template-columns:1fr}.cs-controls{order:1}.cs-stage{order:2;min-height:360px}.cs-data{order:3}}@media(max-width:560px){.cs-header{align-items:start;flex-direction:column}.cs-panel,.cs-stage{padding:12px}.cs-stage{min-height:330px}.cs-summary{grid-template-columns:1fr 1fr}.cs-hands .playing-card{width:clamp(3rem,17vw,4.8rem)}}@media(prefers-reduced-motion:reduce){.cs-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}</style>.cs-repeat{min-height:44px;background:transparent;color:var(--gold);border:1px solid var(--gold)}.cs-repeat:disabled{opacity:.5}';
}

// Return repeat-aware styles without exposing CSS text after the style element.
function repeatSafeStylesHtml() {
  // Move the additive repeat rules ahead of the closing style tag.
  const scoped = stylesHtml().replace('</style>.cs-repeat', '.cs-repeat');
  // Close the corrected style element after every scoped repeat rule.
  return scoped + '</style>';
}

// Bind semantic controls after each render.
function bindEvents() {
  // Read the ante input from the current frame.
  const anteInput = root?.querySelector('#cs-ante');
  // Preserve valid ante edits locally until deal.
  if (anteInput) anteInput.oninput = () => { ante = anteValue(anteInput.value); };
  // Bind deal, call, and fold controls through one action dispatcher.
  root?.querySelectorAll('[data-action]').forEach(button => {
    // Prepare the exact retry identity before executing the action.
    button.onclick = () => {
      // Read the semantic action kind.
      const kind = button.dataset.action;
      // Ignore synthetic call or fold clicks when no active round exists.
      if ((kind === 'call' || kind === 'fold') && !state?.active_round?.round_id) return;
      // Update the ante from the control before deal.
      ante = anteValue(anteInput?.value ?? ante);
      // Preserve unresolved identity for exact retry.
      pendingAction = pendingAction || { kind, actionId: nextActionId(kind), roundId: state?.active_round?.round_id, ante };
      // Ignore incompatible clicks while an unresolved action exists.
      if (pendingAction.kind !== kind) return;
      // Execute the selected action.
      runAction(kind === 'deal' ? deal : kind === 'call' ? callRound : foldRound);
    };
  });
  // Read the optional repeat control from the current frame.
  const repeatButton = root?.querySelector('[data-action="repeat"]');
  // Bind repeat separately so it re-deals the stored ante without a decision replay.
  if (repeatButton) repeatButton.onclick = () => { repeat(); };
}

// Render all game-owned regions from authenticated state.
function render() {
  // Stop late callbacks after unmount.
  if (!root) return;
  // Read the active or newest terminal round once.
  const roundItem = currentRound();
  // Build the localized header.
  const header = '<header class="cs-header"><div><p class="cs-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="cs-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the operational layout.
  const layout = '<div class="cs-layout">' + controlsHtml() + '<main class="cs-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + summaryHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Replace the outlet atomically.
  root.innerHTML = repeatSafeStylesHtml() + '<section class="cs-shell" data-testid="caribbean-stud">' + header + layout + '</section>';
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
    // Read the round that the completed action produced.
    const settledRound = currentRound();
    // Remember the committed ante only after a round reaches a terminal settle so one click can repeat it.
    if (settledRound && settledRound.phase !== 'decision') lastBet = { ante: settledRound.ante };
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

// Deal or replay one ante-first table hand.
async function deal() {
  // Capture the mounted outlet for stale-response protection.
  const mountedRoot = root;
  // Read the prepared retry action.
  const request = pendingAction;
  // Stop if route state changed.
  if (!request || !mountedRoot) return;
  // Post the ante deal without a caller-selected identity.
  const payload = await post(API_ROOT + '/rounds', { action_id: request.actionId, ante: request.ante });
  // Ignore late responses after unmount.
  if (root !== mountedRoot) return;
  // Store authoritative state.
  state = payload.state;
  // Store server-published rules.
  rules = payload.rules || rules;
  // Clear the retry identity after success.
  pendingAction = null;
  // Refresh the shared wallet after the ante debit.
  await refreshBalance();
}

// Re-apply the last committed ante and open one identical round without a timer.
async function repeat() {
  // Ignore repeat while busy, mid-retry, without a stored ante, or during an active round.
  if (busy || pendingAction || !lastBet || state?.active_round) return;
  // Restore the previous ante so the shared deal path reads the repeated stake.
  ante = anteValue(lastBet.ante);
  // Read the ante input from the current frame to mirror the restored stake.
  const anteInput = root?.querySelector('#cs-ante');
  // Reflect the restored ante in the enabled control before dealing.
  if (anteInput) anteInput.value = String(ante);
  // Prepare the exact deal identity exactly as the deal button does.
  pendingAction = { kind: 'deal', actionId: nextActionId('deal'), roundId: state?.active_round?.round_id, ante };
  // Open one identical round through the shared deal action, never replaying call or fold.
  await runAction(deal);
}

// Call or replay one fixed 2x ante reveal.
async function callRound() {
  // Capture the mounted outlet for stale-response protection.
  const mountedRoot = root;
  // Read the prepared retry action.
  const request = pendingAction;
  // Stop if route state changed.
  if (!request || !mountedRoot) return;
  // Encode the round id for the route path.
  const roundId = encodeURIComponent(request.roundId);
  // Post the call action without a caller-selected identity.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/call', { action_id: request.actionId });
  // Ignore late responses after unmount.
  if (root !== mountedRoot) return;
  // Store terminal state.
  state = payload.state;
  // Store server-published rules.
  rules = payload.rules || rules;
  // Clear the retry identity after success.
  pendingAction = null;
  // Refresh the shared wallet after debit and optional returned credit.
  await refreshBalance();
}

// Fold or replay one active table hand.
async function foldRound() {
  // Capture the mounted outlet for stale-response protection.
  const mountedRoot = root;
  // Read the prepared retry action.
  const request = pendingAction;
  // Stop if route state changed.
  if (!request || !mountedRoot) return;
  // Encode the round id for the route path.
  const roundId = encodeURIComponent(request.roundId);
  // Post the fold action without a caller-selected identity.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/fold', { action_id: request.actionId });
  // Ignore late responses after unmount.
  if (root !== mountedRoot) return;
  // Store folded state.
  state = payload.state;
  // Store server-published rules.
  rules = payload.rules || rules;
  // Clear the retry identity after success.
  pendingAction = null;
}

// Export the catalog-owned lazy game module contract.
export const CaribbeanStudGame = {
  // Expose the stable descriptor identifier.
  id: 'caribbean_stud',
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
    // Reset the repeatable ante so a new session never inherits a prior bet.
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
    // Recover a repeatable ante from the newest terminal round so repeat survives a reload.
    const recovered = state?.recent_rounds?.slice(-1)[0];
    // Restore the repeatable ante only when a prior round exposes its committed ante.
    if (recovered?.ante) lastBet = { ante: Number(recovered.ante) };
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
    // Clear the repeatable ante so the next session starts fresh.
    lastBet = null;
    // Clear localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this module.
  },
};
