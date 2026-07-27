// Implement the isolated Hi-Lo browser module for GitHub issue #85.

// Import authenticated envelope-aware API helpers without sending caller-owned player ids.
import { api, post } from '../core/api.js';
// Import the shared accessible card renderer allocated by issue #96.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the game-owned locale domain.
const DOMAIN = 'games/hi_lo';
// Address the additive frozen-v1 Hi-Lo API through one stable root.
const API_ROOT = '/api/v1/games/hi-lo';
// Identify the shared card stylesheet so repeated route mounts install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the two documented guess values in stable control order.
const GUESSES = ['higher', 'lower'];

// Retain the current shell outlet for deterministic rerenders and stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published rule metadata for reload-safe presentation.
let rules = {};
// Retain the configured wager until a round starts or the player changes it.
let wager = 5;
// Prevent overlapping atomic deal or guess actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain an unresolved deal identity and immutable wager for safe retry.
let pendingDeal = null;
// Retain an unresolved guess identity, round, and direction for safe retry.
let pendingGuess = null;
// Retain the last settled wager so one click can repeat the same bet as a new round.
let lastBet = null;
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
  if (globalThis.crypto?.randomUUID) return 'hi-lo-' + globalThis.crypto.randomUUID();
  // Advance a per-module counter before building the fallback identity.
  actionCounter += 1;
  // Combine a timestamp and counter without presenting the value to the player.
  return 'hi-lo-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
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

// Return the active choice round or newest settled round for one stable stage.
function currentRound() {
  // Prefer the actionable round before bounded chronological history.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}

// Translate internal round state into concise player-facing status.
function phaseLabel(roundItem) {
  // Show the ready phase before the first deal.
  if (!roundItem) return text('phases.ready');
  // Show the active higher-or-lower decision phase.
  if (roundItem.phase === 'choose') return text('phases.choose');
  // Show a localized terminal outcome without exposing the API enum.
  return text('phases.' + (roundItem.outcome || 'ready'));
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

// Render the control rail for dealing and the two atomic guess actions.
function controlsHtml() {
  // Read the only actionable round from authenticated server state.
  const activeRound = state?.active_round;
  // Allow guesses only while that round remains in the choose phase.
  const canGuess = activeRound?.phase === 'choose';
  // Lock configuration while a round or ambiguous deal retry owns its wager.
  const wagerDisabled = Boolean(activeRound) || busy || Boolean(pendingDeal);
  // Keep the deal action available for the exact same unresolved retry.
  const dealDisabled = Boolean(activeRound) || busy;
  // Enable the one-click repeat only when a prior settled bet exists and a fresh round can start.
  const repeatDisabled = dealDisabled || Boolean(pendingDeal) || Boolean(pendingGuess) || !lastBet;
  // Read the unresolved direction so the opposite semantic action stays disabled.
  const pendingDirection = pendingGuess?.guess || null;
  // Build both accessible direction controls from one canonical value list.
  const guessButtons = GUESSES.map(guess => {
    // Disable stale, overlapping, or opposite-direction commands.
    const disabled = !canGuess || busy || Boolean(pendingDirection && pendingDirection !== guess);
    // Return one semantic action button with a stable test hook.
    return '<button type="button" class="hilo-guess hilo-guess-' + guess + '" data-guess="' + guess + '"' + (disabled ? ' disabled' : '') + '>' + safe(text('controls.' + guess)) + '</button>';
  // Join the two controls without adding decorative text nodes.
  }).join('');
  // Explain why configuration remains locked after an ambiguous response.
  const retryHelp = pendingDeal || pendingGuess ? '<p class="hilo-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Change the deal label when the same unresolved action can be retried.
  const dealLabel = pendingDeal ? text('controls.retryDeal') : text('controls.deal');
  // Return a stable control rail whose primary actions never move between phases.
  return '<aside class="hilo-panel hilo-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="hilo-wager">' + safe(text('controls.wager')) + '</label><input id="hilo-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (wagerDisabled ? ' disabled' : '') + '><button type="button" class="hilo-primary" data-action="deal"' + (dealDisabled ? ' disabled' : '') + '>' + safe(dealLabel) + '</button><button type="button" class="hilo-repeat" data-action="repeat"' + (repeatDisabled ? ' disabled' : '') + '>' + safe(text('controls.repeat')) + '</button><fieldset' + (canGuess ? '' : ' disabled') + '><legend>' + safe(text('controls.choose')) + '</legend><div class="hilo-guesses">' + guessButtons + '</div></fieldset><p class="hilo-help">' + safe(text('controls.chooseHelp')) + '</p>' + retryHelp + '<p class="hilo-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render the visible opening card and protected next-card reveal.
function stageHtml(roundItem) {
  // Reveal the opening card whenever a round exists.
  const currentCard = localizedCard(roundItem?.current_card, { hidden: !roundItem?.current_card });
  // Reveal the second card only after the server publishes a settled result.
  const nextCard = localizedCard(roundItem?.next_card, { hidden: roundItem?.phase !== 'settled' });
  // Explain the current stage without exposing internal state names.
  const message = !roundItem ? text('stage.readyBody') : roundItem.phase === 'choose' ? text('stage.chooseBody') : text('results.' + roundItem.outcome);
  // Return two reserved card slots so the stage does not resize during settlement.
  return '<section class="hilo-stage-cards" role="group" aria-label="' + safe(text('stage.cardsAria')) + '"><article class="hilo-card-slot"><h3>' + safe(text('stage.currentCard')) + '</h3>' + currentCard + '</article><span class="hilo-comparison" aria-hidden="true">?</span><article class="hilo-card-slot"><h3>' + safe(text('stage.nextCard')) + '</h3>' + nextCard + '</article></section><p class="hilo-result" role="status" aria-live="polite">' + safe(message) + '</p>';
}

// Render wager and settlement facts in one reserved summary region.
function summaryHtml(roundItem) {
  // Show a localized placeholder before values become available.
  const pending = text('summary.pending');
  // Format the committed wager when a round exists.
  const roundWager = roundItem ? tokenAmount(roundItem.wager) : pending;
  // Translate the selected direction only after the server publishes it.
  const guess = roundItem?.guess ? text('guesses.' + roundItem.guess) : pending;
  // Format returned tokens only for a settled round.
  const payout = roundItem?.phase === 'settled' ? tokenAmount(roundItem.payout) : pending;
  // Format the signed net result only for a settled round.
  const net = roundItem?.phase === 'settled' ? tokenAmount(roundItem.net) : pending;
  // Return aligned facts that retain the same positions through every phase.
  return '<section class="hilo-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.wager')) + '<strong>' + safe(roundWager) + '</strong></span><span>' + safe(text('summary.guess')) + '<strong>' + safe(guess) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(payout) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(net) + '</strong></span></section>';
}

// Render bounded reload-safe history with localized results and accessible row names.
function historyHtml() {
  // Copy newest settled rounds first without mutating authenticated state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show an explicit localized empty state before the first settlement.
  if (!rounds.length) return '<p class="hilo-empty">' + safe(text('history.empty')) + '</p>';
  // Render every bounded server-owned round as one concise result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the retained guess without exposing its API value.
    const guess = text('guesses.' + roundItem.guess);
    // Translate the retained outcome without exposing its API value.
    const outcome = text('outcomes.' + roundItem.outcome);
    // Build a localized accessible row name with a stable newest-first number.
    const label = text('history.roundAria', { number: rounds.length - index, guess, outcome });
    // Return one aligned history row with explicit returned-token wording.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(text('history.result', { guess, outcome })) + '</span><strong>' + safe(tokenAmount(roundItem.payout)) + '</strong></li>';
  // Join bounded rows into the single intentional history scroll surface.
  }).join('');
  // Return one intentional keyboard-focusable scroll region without nested scrolling.
  return '<ol class="hilo-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render the rules and recent results in the supporting data rail.
function dataHtml() {
  // Read server rule values while preserving documented defaults during initial loading.
  const correctMultiplier = rules.correct_return_multiplier || 2;
  // Read the tie multiplier for localized rule explanation.
  const tieMultiplier = rules.tie_return_multiplier || 1;
  // Return distinct rule and history regions in one supporting rail.
  return '<aside class="hilo-panel hilo-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul class="hilo-rules"><li>' + safe(text('rules.aceHigh')) + '</li><li>' + safe(text('rules.suitsIgnored')) + '</li><li>' + safe(text('rules.correctReturn', { multiplier: correctMultiplier })) + '</li><li>' + safe(text('rules.tieReturn', { multiplier: tieMultiplier })) + '</li></ul></section><section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive styles without modifying the shared application stylesheet.
function stylesHtml() {
  // Define the dominant stage, stable controls, responsive stack, focus, and reduced-motion rules.
  return '<style>/* Establish the game header and desktop control-stage-data hierarchy. */.hilo-shell{display:grid;gap:16px;min-width:0}.hilo-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.hilo-header h1{margin:0}.hilo-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.hilo-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.hilo-layout{display:grid;grid-template-columns:minmax(210px,.7fr) minmax(520px,2.4fr) minmax(230px,.8fr);gap:16px;align-items:start}.hilo-panel,.hilo-stage{border:1px solid var(--gold);border-radius:16px;background:var(--panel-strong);padding:16px}.hilo-controls,.hilo-data{display:grid;align-content:start;gap:13px}.hilo-controls h2,.hilo-data h2{margin:0}.hilo-controls fieldset{margin:0;padding:0;border:0}.hilo-controls legend{margin-bottom:8px}.hilo-controls input,.hilo-controls button{min-height:44px}.hilo-primary{background:var(--red,#a51f2d);color:#fff}.hilo-guesses{display:grid;grid-template-columns:1fr 1fr;gap:10px}.hilo-help,.hilo-retry,.hilo-empty{color:var(--muted,#b8c8c1)}.hilo-error{min-height:1.4em;margin:0;color:#ffd1d1}.hilo-stage{display:grid;align-content:center;gap:22px;min-width:0;min-height:430px;background:radial-gradient(circle at 50% 40%,rgba(35,17,61,.4),rgba(20,10,34,.96) 70%)}.hilo-stage-cards{display:grid;grid-template-columns:minmax(120px,1fr) auto minmax(120px,1fr);gap:clamp(14px,4vw,48px);align-items:center;justify-items:center}.hilo-card-slot{display:grid;justify-items:center;gap:12px}.hilo-card-slot h3{margin:0}.hilo-card-slot .playing-card{flex:none;width:clamp(4.5rem,9vw,7.5rem);font-size:clamp(1.1rem,2.5vw,1.8rem)}.hilo-comparison{display:grid;place-items:center;width:48px;height:48px;border:1px solid var(--gold);border-radius:50%;font-size:1.6rem;color:var(--gold,#f6d47a)}.hilo-result{min-height:2.8em;margin:0;text-align:center}.hilo-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.hilo-summary span{display:grid;gap:5px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.hilo-summary strong{overflow-wrap:anywhere}.hilo-data section{display:grid;gap:10px}.hilo-rules{margin:0;padding-left:1.1rem}.hilo-rules li+li{margin-top:7px}.hilo-history-list{display:grid;gap:8px;max-height:285px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.hilo-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:9px;background:rgba(0,0,0,.2)}.hilo-shell button:focus-visible,.hilo-shell input:focus-visible,.hilo-history-list:focus-visible{outline:3px solid var(--gold);outline-offset:2px}/* Stack controls, stage, and data on compact screens. */@media(max-width:1100px){.hilo-layout{grid-template-columns:1fr}.hilo-controls{order:1}.hilo-stage{order:2;min-height:360px}.hilo-data{order:3}}/* Prevent card, summary, and action clipping on mobile. */@media(max-width:520px){.hilo-header{align-items:start;flex-direction:column}.hilo-panel,.hilo-stage{padding:12px}.hilo-stage{min-height:320px}.hilo-stage-cards{grid-template-columns:1fr 40px 1fr;gap:8px}.hilo-card-slot .playing-card{width:clamp(3.8rem,22vw,5.5rem)}.hilo-summary{grid-template-columns:1fr 1fr}.hilo-guesses{grid-template-columns:1fr}.hilo-history-list li{grid-template-columns:1fr}}/* Remove decorative motion for reduced-motion users. */@media(prefers-reduced-motion:reduce){.hilo-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}</style>.hilo-repeat{min-height:44px;background:transparent;color:var(--gold);border:1px solid var(--gold)}.hilo-repeat:disabled{opacity:.5}';
}

// Bind semantic controls after each deterministic route render.
function bindEvents() {
  // Read the wager control once from the newly rendered rail.
  const wagerInput = root?.querySelector('#hilo-wager');
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
  // Read the secondary repeat action control rendered beside the deal button.
  const repeatButton = root?.querySelector('[data-action="repeat"]');
  // Re-fire the last committed wager as a fresh round through the shared repeat path.
  if (repeatButton) repeatButton.onclick = () => { repeat(); };
  // Bind both directional actions through one public guess path.
  root?.querySelectorAll('[data-guess]').forEach(button => {
    // Prepare or retry only the same round and direction after an ambiguous response.
    button.onclick = () => {
      // Read the current authenticated active round before preparing an action.
      const activeRound = state?.active_round;
      // Ignore stale clicks after settlement or route-state replacement.
      if (!activeRound || activeRound.phase !== 'choose') return;
      // Read the canonical direction from the semantic data attribute.
      const guess = button.dataset.guess;
      // Preserve an unresolved action rather than generating another settlement identity.
      pendingGuess = pendingGuess || { actionId: nextActionId(), roundId: activeRound.round_id, guess };
      // Ignore an opposite-direction click while the original semantic request is unresolved.
      if (pendingGuess.roundId !== activeRound.round_id || pendingGuess.guess !== guess) return;
      // Execute the prepared settlement through shared busy and error handling.
      runAction(submitGuess);
    };
  });
}

// Render all game-owned regions from authenticated server state and locale resources.
function render() {
  // Stop late callbacks after the shell unmounts this route.
  if (!root) return;
  // Read the active or newest settled round once for a consistent frame.
  const roundItem = currentRound();
  // Build the translated game header before combining layout regions.
  const header = '<header class="hilo-header"><div><p class="hilo-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="hilo-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the control-stage-data layout in responsive reading order.
  const layout = '<div class="hilo-layout">' + controlsHtml() + '<main class="hilo-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + summaryHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = stylesHtml() + '<section class="hilo-shell" data-testid="hi-lo">' + header + layout + '</section>';
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

// Start or replay one idempotent wagered opening-card deal.
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
  // Clear any stale guess preparation after a new round starts.
  pendingGuess = null;
  // Refresh the persistent authenticated wallet after the ledger debit.
  await refreshBalance();
}

// Submit or replay one higher-or-lower settlement action.
async function submitGuess() {
  // Capture the route node so late settlement cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the immutable prepared guess created by the action handler.
  const request = pendingGuess;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Encode the server-owned round id before building the public route.
  const roundId = encodeURIComponent(request.roundId);
  // Post exactly the documented action identity and direction without a caller player id.
  const payload = await post(API_ROOT + '/rounds/' + roundId + '/guesses', { action_id: request.actionId, guess: request.guess });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the terminal reload-safe state and bounded history.
  state = payload.state;
  // Refresh fixed rules when the response includes them.
  rules = payload.rules || rules;
  // Read the newest settled round so the next click can repeat the same wager.
  const settled = currentRound();
  // Remember the settled wager only after a fully settled round proves the bet.
  if (settled && settled.phase === 'settled') lastBet = { wager: settled.wager };
  // Clear the retry identity only after the settled response is available.
  pendingGuess = null;
  // Clear any obsolete deal identity after terminal settlement.
  pendingDeal = null;
  // Refresh the persistent authenticated wallet after payout, refund, or loss.
  await refreshBalance();
}

// Re-open one fresh round with the last settled wager through the shared deal path.
async function repeat() {
  // Ignore repeat while busy, mid-round, holding an unresolved retry, detached, or without a prior bet.
  if (busy || !root || state?.active_round || pendingDeal || pendingGuess || !lastBet) return;
  // Restore the previous stake into the local wager configuration.
  wager = wagerValue(lastBet.wager);
  // Prepare a fresh idempotent deal identity carrying the restored stake.
  pendingDeal = { actionId: nextActionId(), wager };
  // Execute the prepared deal through shared busy and error handling.
  await runAction(deal);
}

// Export the catalog-owned lazy game module contract.
export const HiLoGame = {
  // Expose the stable descriptor identifier without player-visible copy.
  id: 'hi_lo',
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
    // Clear any prior guess identity before reading current server state.
    pendingGuess = null;
    // Clear any repeatable bet so another session never inherits it before recovery.
    lastBet = null;
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
    // Recover a repeatable wager from the newest settled round so repeat survives a reload.
    const restored = state?.recent_rounds?.slice(-1)[0] || null;
    // Restore the repeatable configuration only when a prior settled round is present.
    if (restored) lastBet = { wager: restored.wager };
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
    // Forget the route-local guess identity after teardown.
    pendingGuess = null;
    // Forget the repeatable bet so the next session starts fresh.
    lastBet = null;
    // Clear the reserved localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this game.
  },
};
