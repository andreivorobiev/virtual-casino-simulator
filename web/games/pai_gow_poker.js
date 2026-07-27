// Implement the isolated Pai Gow Poker browser module for GitHub issue #138.

// Import authenticated envelope-aware API helpers without sending caller-owned player ids.
import { api, post } from '../core/api.js';
// Import the shared accessible card renderer allocated by issue #96.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the game-owned locale domain.
const DOMAIN = 'games/pai_gow_poker';
// Address the additive frozen-v1 Pai Gow Poker API through one stable root.
const API_ROOT = '/api/v1/games/pai-gow-poker';
// Identify the shared card stylesheet so repeated route mounts install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Encode the persistence-safe joker sentinel shared with the server engine.
const JOKER_CODE = 'XJ';

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
// Retain an unresolved set identity, round, and low-hand indices for safe retry.
let pendingDecision = null;
// Retain the last committed ante so one click can repeat the same round.
let lastBet = null;
// Retain the low-hand card positions the player has selected while setting.
let lowSelection = [];
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
  if (globalThis.crypto?.randomUUID) return 'pai-gow-poker-' + globalThis.crypto.randomUUID();
  // Advance a per-module counter before building the fallback identity.
  actionCounter += 1;
  // Combine a timestamp and counter without presenting the value to the player.
  return 'pai-gow-poker-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
}

// Map public API diagnostics to owned localized feedback.
function errorKey(error) {
  // Normalize the optional envelope code without exposing server text.
  const code = String(error?.code || '').toUpperCase();
  // Explain an insufficient play-token balance through local copy.
  if (code.includes('INSUFFICIENT')) return 'errors.insufficientTokens';
  // Explain an illegal arrangement without exposing implementation details.
  if (code.includes('VALIDATION')) return 'errors.illegalSet';
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
  // Render the semi-wild joker with its own localized accessible name.
  if (String(card).toUpperCase() === JOKER_CODE) {
    // Present the joker face using a stable glyph and localized label.
    return renderCard('??', {}).replace('??', '★J').replace(/aria-label="[^"]*"/, 'aria-label="' + safe(text('cards.joker')) + '"');
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

// Return the active setting round or newest terminal round for one stable stage.
function currentRound() {
  // Prefer the actionable round before bounded chronological history.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}

// Translate internal round state into concise player-facing status.
function phaseLabel(roundItem) {
  // Show the ready phase before the first ante.
  if (!roundItem) return text('phases.ready');
  // Show the active setting phase while the player arranges the hand.
  if (roundItem.phase === 'setting') return text('phases.setting');
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

// Render the seven dealt player cards as selectable setting tiles.
function settingCardsHtml(roundItem) {
  // Read the seven public player cards from the active setting round.
  const cards = roundItem?.player_cards || [];
  // Build one accessible toggle button per dealt card position.
  const tiles = cards.map((card, index) => {
    // Mark the two positions the player has assigned to the low hand.
    const selected = lowSelection.includes(index);
    // Compose the localized accessible name that includes selection state.
    const label = text(selected ? 'setting.deselect' : 'setting.select', { card: text('cards.cardLabel', { rank: text('ranks.' + String(card).slice(0, -1)), suit: text('suits.' + String(card).slice(-1)) }) });
    // Return one card tile whose pressed state drives the low-hand assignment.
    return '<button type="button" class="pgp-tile' + (selected ? ' pgp-tile-selected' : '') + '" data-card-index="' + index + '" aria-pressed="' + (selected ? 'true' : 'false') + '" aria-label="' + safe(label) + '">' + localizedCard(card) + '</button>';
  // Join the seven tiles without decorative separators.
  }).join('');
  // Return the selectable hand region with a localized group name.
  return '<section class="pgp-card-row" aria-label="' + safe(text('setting.handAria')) + '"><h3>' + safe(text('setting.handTitle')) + '</h3><div class="pgp-tiles">' + tiles + '</div></section>';
}

// Render one labeled static card row for settled hands.
function staticRow(labelKey, cards, options = {}) {
  // Build the requested number of slots, hiding protected positions.
  const slots = Array.from({ length: options.slots || cards.length }, (_, index) => localizedCard(cards[index], { hidden: options.hidden || !cards[index] })).join('');
  // Return one accessible labeled group.
  return '<section class="pgp-card-row" aria-label="' + safe(text(labelKey + '.aria')) + '"><h3>' + safe(text(labelKey + '.title')) + '</h3><div class="pgp-cards">' + slots + '</div></section>';
}

// Render the control rail for the ante deal and the hand-setting decision.
function controlsHtml() {
  // Read the only actionable round from authenticated server state.
  const activeRound = state?.active_round;
  // Allow setting only while a dealt hand is waiting for the player.
  const canSet = activeRound?.phase === 'setting';
  // Lock ante configuration while a round or ambiguous deal retry owns its wager.
  const wagerDisabled = Boolean(activeRound) || busy || Boolean(pendingDeal);
  // Keep the deal action available for the exact same unresolved retry.
  const dealDisabled = Boolean(activeRound) || busy;
  // Enable the explicit set only when exactly two low cards are chosen.
  const setDisabled = !canSet || busy || lowSelection.length !== 2 || Boolean(pendingDecision);
  // Enable the house-way auto-set whenever the hand is awaiting a decision.
  const houseWayDisabled = !canSet || busy || Boolean(pendingDecision);
  // Explain why configuration remains locked after an ambiguous response.
  const retryHelp = pendingDeal || pendingDecision ? '<p class="pgp-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Change the deal label when the same unresolved action can be retried.
  const dealLabel = pendingDeal ? text('controls.retryDeal') : text('controls.deal');
  // Enable the one-click repeat only outside the setting phase with a stored ante and nothing in flight.
  const repeatDisabled = Boolean(activeRound) || busy || Boolean(pendingDeal) || Boolean(pendingDecision) || !lastBet;
  // Offer the one-click repeat only outside the open setting phase so the hand-setting decision stays unobstructed.
  const repeatButton = canSet ? '' : '<button type="button" class="pgp-repeat" data-action="repeat"' + (repeatDisabled ? ' disabled' : '') + '>' + safe(text('controls.repeat')) + '</button>';
  // Return a stable control rail whose primary actions never move between phases.
  return '<aside class="pgp-panel pgp-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="pgp-wager">' + safe(text('controls.ante')) + '</label><input id="pgp-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (wagerDisabled ? ' disabled' : '') + '><button type="button" class="pgp-primary" data-action="deal"' + (dealDisabled ? ' disabled' : '') + '>' + safe(dealLabel) + '</button>' + repeatButton + '<fieldset' + (canSet ? '' : ' disabled') + '><legend>' + safe(text('controls.setLegend')) + '</legend><button type="button" class="pgp-set" data-action="set"' + (setDisabled ? ' disabled' : '') + '>' + safe(text('controls.set')) + '</button><button type="button" class="pgp-houseway" data-action="house-way"' + (houseWayDisabled ? ' disabled' : '') + '>' + safe(text('controls.houseWay')) + '</button></fieldset><p class="pgp-help">' + safe(text('controls.setHelp')) + '</p>' + retryHelp + '<p class="pgp-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render the player hand, settled arrangement, and protected dealer hand.
function stageHtml(roundItem) {
  // Show a localized empty stage before the first deal.
  if (!roundItem) return '<div class="pgp-table-felt"><p class="pgp-result" role="status">' + safe(text('stage.readyBody')) + '</p></div>';
  // Present the selectable hand while the player is still setting.
  if (roundItem.phase === 'setting') {
    // Return the dealer placeholder above the selectable seven-card hand.
    return '<div class="pgp-table-felt">' + staticRow('dealer', [], { slots: 7, hidden: true }) + settingCardsHtml(roundItem) + '</div><p class="pgp-result" role="status" aria-live="polite">' + safe(text('stage.settingBody')) + '</p>';
  }
  // Read the settled player high and low arrangement.
  const playerHigh = roundItem.player_high || [];
  // Read the settled player low arrangement.
  const playerLow = roundItem.player_low || [];
  // Reveal the dealer high hand only after settlement.
  const dealerHigh = roundItem.dealer_high || [];
  // Reveal the dealer low hand only after settlement.
  const dealerLow = roundItem.dealer_low || [];
  // Translate the terminal outcome into player-facing copy.
  const message = text('results.' + (roundItem.outcome || 'push'));
  // Return the paired dealer and player five-plus-two arrangement.
  return '<div class="pgp-table-felt">' + staticRow('dealerHigh', dealerHigh, { slots: 5 }) + staticRow('dealerLow', dealerLow, { slots: 2 }) + staticRow('playerHigh', playerHigh, { slots: 5 }) + staticRow('playerLow', playerLow, { slots: 2 }) + '</div><p class="pgp-result" role="status" aria-live="polite">' + safe(message) + '</p>';
}

// Render wager and settlement facts in one reserved summary region.
function summaryHtml(roundItem) {
  // Show a localized placeholder before values become available.
  const pending = text('summary.pending');
  // Format the committed ante when a round exists.
  const ante = roundItem ? tokenAmount(roundItem.wager) : pending;
  // Translate the high-hand result only after settlement.
  const high = roundItem?.phase === 'settled' ? text(roundItem.high_win ? 'summary.won' : 'summary.lost') : pending;
  // Translate the low-hand result only after settlement.
  const low = roundItem?.phase === 'settled' ? text(roundItem.low_win ? 'summary.won' : 'summary.lost') : pending;
  // Format returned tokens only for a terminal round.
  const payout = roundItem?.phase === 'settled' ? tokenAmount(roundItem.payout) : pending;
  // Return aligned facts that retain the same positions through every phase.
  return '<section class="pgp-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.ante')) + '<strong>' + safe(ante) + '</strong></span><span>' + safe(text('summary.high')) + '<strong>' + safe(high) + '</strong></span><span>' + safe(text('summary.low')) + '<strong>' + safe(low) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(payout) + '</strong></span></section>';
}

// Render bounded reload-safe history with localized results and accessible row names.
function historyHtml() {
  // Copy newest terminal rounds first without mutating authenticated state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show an explicit localized empty state before the first settlement.
  if (!rounds.length) return '<p class="pgp-empty">' + safe(text('history.empty')) + '</p>';
  // Render every bounded server-owned round as one concise result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the retained outcome without exposing its API value.
    const outcome = text('outcomes.' + roundItem.outcome);
    // Build a localized accessible row name with a stable newest-first number.
    const label = text('history.roundAria', { number: rounds.length - index, outcome });
    // Return one aligned history row with explicit returned-token wording.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(outcome) + '</span><strong>' + safe(tokenAmount(roundItem.payout)) + '</strong></li>';
  // Join bounded rows into the single intentional history scroll surface.
  }).join('');
  // Return one intentional keyboard-focusable scroll region without nested scrolling.
  return '<ol class="pgp-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render the rules and recent results in the supporting data rail.
function dataHtml() {
  // Read the published commission rate while preserving the documented default.
  const commission = Math.round((rules.commission_rate ?? 0.05) * 100);
  // Return distinct rule and history regions in one supporting rail.
  return '<aside class="pgp-panel pgp-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul class="pgp-rules"><li>' + safe(text('rules.beatBoth')) + '</li><li>' + safe(text('rules.commission', { percent: commission })) + '</li><li>' + safe(text('rules.copiesDealer')) + '</li><li>' + safe(text('rules.joker')) + '</li><li>' + safe(text('rules.noValue')) + '</li></ul></section><section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive styles without modifying the shared application stylesheet.
function baseStylesHtml() {
  // Define the dominant stage, stable controls, responsive stack, focus, and reduced-motion rules.
  return '<style>.pgp-shell{display:grid;gap:16px;min-width:0}.pgp-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.pgp-header h1{margin:0}.pgp-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.pgp-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.pgp-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(560px,2.5fr) minmax(240px,.82fr);gap:16px;align-items:start}.pgp-panel,.pgp-stage{border:1px solid var(--gold);border-radius:16px;background:var(--panel-strong);padding:16px}.pgp-controls,.pgp-data{display:grid;align-content:start;gap:13px}.pgp-controls h2,.pgp-data h2{margin:0}.pgp-controls fieldset{margin:0;padding:0;border:0;display:grid;gap:10px}.pgp-controls legend{margin-bottom:8px}.pgp-controls input,.pgp-controls button{min-height:44px}.pgp-primary{background:var(--red,#a51f2d);color:#fff}.pgp-set{background:var(--gold,#c99a3a);color:#1a1205}.pgp-help,.pgp-retry,.pgp-empty{color:var(--muted,#b8c8c1)}.pgp-error{min-height:1.4em;margin:0;color:#ffd1d1}.pgp-stage{display:grid;align-content:center;gap:18px;min-width:0;min-height:500px;background:radial-gradient(circle at 50% 44%,rgba(35,17,61,.45),rgba(20,10,34,.98) 70%)}.pgp-table-felt{display:grid;gap:16px}.pgp-card-row{display:grid;justify-items:center;gap:10px}.pgp-card-row h3{margin:0}.pgp-cards,.pgp-tiles{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;min-height:96px}.pgp-tile{padding:4px;border:2px solid transparent;border-radius:12px;background:transparent;cursor:pointer;line-height:0}.pgp-tile-selected{border-color:var(--gold);transform:translateY(-8px)}.pgp-cards .playing-card,.pgp-tiles .playing-card{flex:none;width:clamp(4.2rem,7vw,6.6rem);font-size:clamp(1rem,2vw,1.55rem)}.pgp-result{min-height:2.4em;margin:0;text-align:center}.pgp-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.pgp-summary span{display:grid;gap:5px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.pgp-summary strong{overflow-wrap:anywhere}.pgp-data section{display:grid;gap:10px;min-width:0}.pgp-rules{margin:0;padding-left:1.1rem}.pgp-rules li+li{margin-top:7px}.pgp-history-list{display:grid;gap:8px;max-height:285px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.pgp-history-list li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;min-width:0;padding:9px;border-radius:9px;background:rgba(0,0,0,.2)}.pgp-history-list li span,.pgp-history-list li strong{min-width:0;overflow-wrap:anywhere}.pgp-shell button:focus-visible,.pgp-shell input:focus-visible,.pgp-history-list:focus-visible{outline:3px solid var(--gold);outline-offset:2px}@media(min-width:561px) and (max-width:1600px){.pgp-shell{padding-right:176px}body:has(.pgp-shell) .report-problem-fab{width:144px;max-width:144px;white-space:normal;line-height:1.1}}@media(max-width:1120px){.pgp-layout{grid-template-columns:1fr}.pgp-controls{order:1}.pgp-stage{order:2;min-height:420px}.pgp-data{order:3}}@media(max-width:560px){.pgp-header{align-items:start;flex-direction:column}.pgp-panel,.pgp-stage{padding:12px}.pgp-stage{min-height:380px}.pgp-cards,.pgp-tiles{gap:7px;min-height:82px}.pgp-cards .playing-card,.pgp-tiles .playing-card{width:clamp(3.4rem,18vw,4.9rem)}.pgp-summary{grid-template-columns:1fr 1fr}.pgp-history-list li{grid-template-columns:1fr}.pgp-controls .pgp-help,.pgp-controls .pgp-error{width:calc(100% - 160px);max-width:calc(100% - 160px)}body:has(.pgp-shell) .report-problem-fab{width:144px;max-width:144px;white-space:normal;line-height:1.1}}@media(prefers-reduced-motion:reduce){.pgp-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}.pgp-tile-selected{transform:none}}</style>.pgp-repeat{min-height:44px;background:transparent;color:var(--gold);border:1px solid var(--gold)}.pgp-repeat:disabled{opacity:.5}';
}

// Return corrected scoped styles with the repeat rules inside the style element and a mobile feedback-control lane.
function stylesHtml() {
  // Move the additive repeat rules ahead of the closing style tag instead of emitting them as visible text.
  const scoped = baseStylesHtml().replace('</style>.pgp-repeat', '.pgp-repeat');
  // Reserve the feedback-control width beside both hand-setting actions on narrow phones.
  const mobileSafe = scoped.replace('@media(max-width:560px){', '@media(max-width:560px){.pgp-controls fieldset{padding-right:160px}');
  // Close the corrected scoped stylesheet after every base and repeat rule.
  return mobileSafe + '</style>';
}

// Bind semantic controls after each deterministic route render.
function bindEvents() {
  // Read the ante control once from the newly rendered rail.
  const wagerInput = root?.querySelector('#pgp-wager');
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
  // Read the optional repeat control from the current frame.
  const repeatButton = root?.querySelector('[data-action="repeat"]');
  // Bind repeat separately so it re-deals the stored ante without a decision replay.
  if (repeatButton) repeatButton.onclick = () => { repeat(); };
  // Bind each selectable card tile to the low-hand toggle.
  root?.querySelectorAll('[data-card-index]').forEach(button => {
    // Toggle one card position into or out of the two-card low hand.
    button.onclick = () => {
      // Read the numeric card position from the semantic attribute.
      const index = Number(button.dataset.cardIndex);
      // Remove an already-selected position to allow a correction.
      if (lowSelection.includes(index)) lowSelection = lowSelection.filter(item => item !== index);
      // Add a new position only while fewer than two are chosen.
      else if (lowSelection.length < 2) lowSelection = [...lowSelection, index];
      // Rerender so the pressed state and control availability stay consistent.
      render();
    };
  });
  // Bind the explicit set action to the chosen low-hand positions.
  const setButton = root?.querySelector('[data-action="set"]');
  // Prepare or retry only the same round and low-hand selection.
  if (setButton) setButton.onclick = () => prepareSet([...lowSelection].sort((a, b) => a - b));
  // Bind the house-way auto-set action.
  const houseWayButton = root?.querySelector('[data-action="house-way"]');
  // Prepare or retry the deterministic house-way arrangement.
  if (houseWayButton) houseWayButton.onclick = () => prepareSet('house_way');
}

// Prepare one immutable set decision from either explicit indices or the house way.
function prepareSet(choice) {
  // Read the current authenticated active round before preparing an action.
  const activeRound = state?.active_round;
  // Ignore stale clicks after settlement or route-state replacement.
  if (!activeRound || activeRound.phase !== 'setting') return;
  // Preserve an unresolved action rather than generating another settlement identity.
  pendingDecision = pendingDecision || { actionId: nextActionId(), roundId: activeRound.round_id, set: choice };
  // Ignore a changed selection while the original semantic request is unresolved.
  if (pendingDecision.roundId !== activeRound.round_id) return;
  // Execute the prepared set through shared busy and error handling.
  runAction(submitDecision);
}

// Render all game-owned regions from authenticated server state and locale resources.
function render() {
  // Stop late callbacks after the shell unmounts this route.
  if (!root) return;
  // Read the active or newest terminal round once for a consistent frame.
  const roundItem = currentRound();
  // Build the translated game header before combining layout regions.
  const header = '<header class="pgp-header"><div><p class="pgp-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="pgp-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the control-stage-data layout in responsive reading order.
  const layout = '<div class="pgp-layout">' + controlsHtml() + '<main class="pgp-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + summaryHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Extend the fixed-feedback clearance through desktop-primary so localized history rows never sit beneath the report control.
  const wideDesktopFeedbackClearance = '<style>@media(min-width:1601px) and (max-width:2200px){.pgp-shell{padding-right:176px}body:has(.pgp-shell) .report-problem-fab{width:144px;max-width:144px;white-space:normal;line-height:1.1}}</style>';
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = stylesHtml() + wideDesktopFeedbackClearance + '<section class="pgp-shell" data-testid="pai-gow-poker">' + header + layout + '</section>';
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
    // Read the round that the completed action produced.
    const settledRound = currentRound();
    // Remember the committed ante only after a round reaches terminal settlement so one click can repeat it.
    if (settledRound && settledRound.phase === 'settled') lastBet = { wager: settledRound.wager };
  // Translate failures without displaying server-owned English.
  } catch (error) {
    // Store the owned localized error key for the route region.
    lastErrorKey = errorKey(error);
    // Release an unresolved set identity after an illegal arrangement so a new set can be chosen.
    if (lastErrorKey === 'errors.illegalSet') pendingDecision = null;
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
  const payload = await post(API_ROOT + '/rounds', { action_id: request.actionId, ante: request.wager });
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
  // Reset the low-hand selection for the freshly dealt seven-card hand.
  lowSelection = [];
  // Clear any stale set preparation after a new round starts.
  pendingDecision = null;
  // Refresh the persistent authenticated wallet after the ante debit.
  await refreshBalance();
}

// Re-apply the last committed ante and open one identical round without a timer.
async function repeat() {
  // Ignore repeat while busy, mid-retry, without a stored ante, or during an active setting round.
  if (busy || pendingDeal || pendingDecision || !lastBet || state?.active_round) return;
  // Restore the previous ante so the shared deal path reads the repeated stake.
  wager = wagerValue(lastBet.wager);
  // Read the ante input from the current frame to mirror the restored stake.
  const wagerInput = root?.querySelector('#pgp-wager');
  // Reflect the restored ante in the enabled control before dealing.
  if (wagerInput) wagerInput.value = String(wager);
  // Prepare the exact deal identity exactly as the deal button does.
  pendingDeal = { actionId: nextActionId(), wager };
  // Open one identical round through the shared deal action, never replaying the hand-setting decision.
  await runAction(deal);
}

// Submit or replay one set decision action.
async function submitDecision() {
  // Capture the route node so late settlement cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the immutable prepared decision created by the action handler.
  const request = pendingDecision;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Encode the server-owned round id before building the public route.
  const roundId = encodeURIComponent(request.roundId);
  // Post exactly the documented action identity and set choice without a caller player id.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/decisions', { action_id: request.actionId, set: request.set });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the terminal reload-safe state and bounded history.
  state = payload.state;
  // Refresh fixed rules when the response includes them.
  rules = payload.rules || rules;
  // Clear the retry identity only after the terminal response is available.
  pendingDecision = null;
  // Reset the low-hand selection after terminal settlement.
  lowSelection = [];
  // Clear any obsolete deal identity after terminal settlement.
  pendingDeal = null;
  // Refresh the persistent authenticated wallet after the payout, push, or loss.
  await refreshBalance();
}

// Export the catalog-owned lazy game module contract.
export const PaiGowPokerGame = {
  // Expose the stable descriptor identifier without player-visible copy.
  id: 'pai_gow_poker',
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
    // Reset the repeatable ante so a new session never inherits a prior bet.
    lastBet = null;
    // Clear any prior low-hand selection before reading current server state.
    lowSelection = [];
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
    // Recover a repeatable ante from the newest terminal round so repeat survives a reload.
    const recovered = state?.recent_rounds?.slice(-1)[0];
    // Restore the repeatable ante only when a prior round exposes its committed ante.
    if (recovered?.wager) lastBet = { wager: Number(recovered.wager) };
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
    // Clear the repeatable ante so the next session starts fresh.
    lastBet = null;
    // Forget the route-local low-hand selection after teardown.
    lowSelection = [];
    // Clear the reserved localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this game.
  },
};
