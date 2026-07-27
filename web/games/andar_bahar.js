// Implement the catalog-integrated Andar Bahar browser module for GitHub issue #140.

// Import authenticated envelope-aware API helpers without caller-owned player ids.
import { api, post } from '../core/api.js';
// Import the shared accessible card renderer allocated by issue #96.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the game-owned locale domain.
const DOMAIN = 'games/andar_bahar';
// Address the additive frozen-v1 proposal API through one stable root.
const API_ROOT = '/api/v1/games/andar-bahar';
// Identify the shared card stylesheet so repeated route mounts install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the two documented side values in stable control order.
const SIDES = ['andar', 'bahar'];

// Retain the current shell outlet for deterministic rerenders and stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published rule metadata for reload-safe presentation.
let rules = {};
// Retain the configured wager until the player changes it.
let wager = 5;
// Retain the selected side until the player changes it.
let selectedSide = 'andar';
// Prevent overlapping atomic play actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain an unresolved play identity and immutable inputs for safe retry.
let pendingPlay = null;
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
  if (globalThis.crypto?.randomUUID) return 'andar-bahar-' + globalThis.crypto.randomUUID();
  // Advance a per-module counter before building the fallback identity.
  actionCounter += 1;
  // Combine a timestamp and counter without presenting the value to the player.
  return 'andar-bahar-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
}

// Map public API diagnostics to owned localized feedback.
function errorKey(error) {
  // Normalize the optional envelope code without exposing server text.
  const code = String(error?.code || '').toUpperCase();
  // Explain an insufficient fake-token balance through local copy.
  if (code.includes('INSUFFICIENT')) return 'errors.insufficientTokens';
  // Explain stale or conflicting actions without showing implementation details.
  if (code.includes('CONFLICT')) return 'errors.conflict';
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
  // Render a localized face-down card without exposing any future identity.
  if (hidden) return renderCard('??', { hidden: true }).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(text('cards.faceDown')) + '"');
  // Normalize the compact rank from every character before the suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build the semantic card name entirely from localized rank and suit resources.
  const label = text('cards.cardLabel', { rank: text('ranks.' + rank), suit: text('suits.' + suit) });
  // Replace the primitive default English label while retaining accessible markup.
  return renderCard(card).replace(/aria-label="[^"]*"/, 'aria-label="' + safe(label) + '"');
}

// Return the newest settled round for one stable stage.
function currentRound() {
  // Prefer the latest completed round because Andar Bahar plays atomically.
  return state?.recent_rounds?.slice(-1)[0] || null;
}

// Translate internal round state into concise player-facing status.
function phaseLabel(roundItem) {
  // Show the ready phase before the first play.
  if (!roundItem) return text('phases.ready');
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

// Render side controls and one atomic play action.
function controlsHtml() {
  // Lock configuration while an ambiguous play response owns its inputs.
  const inputDisabled = busy || Boolean(pendingPlay);
  // Build both accessible side controls from the canonical side list.
  const sideButtons = SIDES.map(side => {
    // Mark the selected side independently of color.
    const pressed = selectedSide === side ? ' aria-pressed="true"' : ' aria-pressed="false"';
    // Return one semantic side button with a stable test hook.
    return '<button type="button" class="andar-side andar-side-' + side + '" data-side="' + side + '"' + pressed + (inputDisabled ? ' disabled' : '') + '>' + safe(text('controls.' + side)) + '</button>';
  // Join the two controls without adding decorative text nodes.
  }).join('');
  // Explain why configuration remains locked after an ambiguous response.
  const retryHelp = pendingPlay ? '<p class="andar-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Change the play label when the same unresolved action can be retried.
  const playLabel = pendingPlay ? text('controls.retryPlay') : text('controls.play');
  // Return a stable control rail whose primary action never moves between phases.
  return '<aside class="andar-panel andar-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="andar-wager">' + safe(text('controls.wager')) + '</label><input id="andar-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (inputDisabled ? ' disabled' : '') + '><fieldset><legend>' + safe(text('controls.sideLegend')) + '</legend><div class="andar-sides">' + sideButtons + '</div></fieldset><button type="button" class="andar-primary" data-action="play"' + (busy ? ' disabled' : '') + '>' + safe(playLabel) + '</button><p class="andar-help">' + safe(text('controls.help')) + '</p>' + retryHelp + '<p class="andar-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render the match card and transparent alternating sequence.
function stageHtml(roundItem) {
  // Render the joker/match card or a protected placeholder.
  const matchCard = localizedCard(roundItem?.match_card, { hidden: !roundItem?.match_card });
  // Read the dealt cards while preserving an empty sequence before first play.
  const dealtCards = roundItem?.dealt_cards || [];
  // Render every reveal as a side-labeled card in server order.
  const sequence = dealtCards.map((item, index) => '<li class="andar-dealt-card andar-' + safe(item.side) + (item.matched ? ' andar-match' : '') + '"><span>' + safe(text('stage.dealLabel', { number: index + 1, side: text('sides.' + item.side) })) + '</span>' + localizedCard(item.card) + '</li>').join('');
  // Show an explicit localized empty state before first play.
  const sequenceBody = sequence || '<li class="andar-empty">' + safe(text('stage.readySequence')) + '</li>';
  // Explain the current stage without exposing internal state names.
  const message = !roundItem ? text('stage.readyBody') : text('results.' + roundItem.outcome, { side: text('sides.' + roundItem.winning_side) });
  // Return reserved regions so reduced-motion and normal paths share one stable layout.
  return '<section class="andar-match-card" role="group" aria-label="' + safe(text('stage.matchAria')) + '"><h3>' + safe(text('stage.matchCard')) + '</h3>' + matchCard + '</section><ol class="andar-sequence" aria-label="' + safe(text('stage.sequenceAria')) + '">' + sequenceBody + '</ol><p class="andar-result" role="status" aria-live="polite">' + safe(message) + '</p>';
}

// Render wager and settlement facts in one reserved summary region.
function summaryHtml(roundItem) {
  // Show a localized placeholder before values become available.
  const pending = text('summary.pending');
  // Format the committed wager when a round exists.
  const roundWager = roundItem ? tokenAmount(roundItem.wager) : pending;
  // Translate the selected side only after the server publishes it.
  const side = roundItem?.selected_side ? text('sides.' + roundItem.selected_side) : pending;
  // Translate the winning side only after settlement.
  const winner = roundItem?.winning_side ? text('sides.' + roundItem.winning_side) : pending;
  // Format returned tokens only after a round exists.
  const payout = roundItem ? tokenAmount(roundItem.payout) : pending;
  // Format the signed net result only after a round exists.
  const net = roundItem ? tokenAmount(roundItem.net) : pending;
  // Return aligned facts that retain the same positions through every phase.
  return '<section class="andar-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.wager')) + '<strong>' + safe(roundWager) + '</strong></span><span>' + safe(text('summary.choice')) + '<strong>' + safe(side) + '</strong></span><span>' + safe(text('summary.winner')) + '<strong>' + safe(winner) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(payout) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(net) + '</strong></span></section>';
}

// Render bounded reload-safe history with localized results and accessible row names.
function historyHtml() {
  // Copy newest settled rounds first without mutating authenticated state.
  const rounds = [...(state?.recent_rounds || [])].reverse();
  // Show an explicit localized empty state before the first settlement.
  if (!rounds.length) return '<p class="andar-empty">' + safe(text('history.empty')) + '</p>';
  // Render every bounded server-owned round as one concise result row.
  const rows = rounds.map((roundItem, index) => {
    // Translate the retained choice without exposing its API value.
    const choice = text('sides.' + roundItem.selected_side);
    // Translate the retained winning side without exposing its API value.
    const winner = text('sides.' + roundItem.winning_side);
    // Translate the outcome without exposing its API value.
    const outcome = text('outcomes.' + roundItem.outcome);
    // Build a localized accessible row name with a stable newest-first number.
    const label = text('history.roundAria', { number: rounds.length - index, choice, winner, outcome });
    // Return one aligned history row with explicit returned-token wording.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(text('history.result', { choice, winner, outcome })) + '</span><strong>' + safe(tokenAmount(roundItem.payout)) + '</strong></li>';
  // Join bounded rows into the single intentional history scroll surface.
  }).join('');
  // Return one intentional keyboard-focusable scroll region without nested scrolling.
  return '<ol class="andar-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render the rules and recent results in the supporting data rail.
function dataHtml() {
  // Read server rule values while preserving documented defaults during initial loading.
  const multiplier = rules.return_multiplier || 2;
  // Return distinct rule and history regions in one supporting rail.
  return '<aside class="andar-panel andar-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul class="andar-rules"><li>' + safe(text('rules.matchCard')) + '</li><li>' + safe(text('rules.alternating')) + '</li><li>' + safe(text('rules.rankOnly')) + '</li><li>' + safe(text('rules.return', { multiplier })) + '</li></ul></section><section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive styles without modifying the shared application stylesheet.
function stylesHtml() {
  // Define the dominant stage, stable controls, responsive stack, focus, and reduced-motion rules.
  return '<style>/* Establish the game header and desktop control-stage-data hierarchy. */.andar-shell{display:grid;gap:16px;min-width:0}.andar-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.andar-header h1{margin:0}.andar-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.andar-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.andar-layout{display:grid;grid-template-columns:minmax(210px,.7fr) minmax(560px,2.5fr) minmax(230px,.8fr);gap:16px;align-items:start}.andar-panel,.andar-stage{border:1px solid var(--gold);border-radius:16px;background:var(--panel-strong);padding:16px}.andar-controls,.andar-data{display:grid;align-content:start;gap:13px}.andar-controls h2,.andar-data h2{margin:0}.andar-controls fieldset{margin:0;padding:0;border:0}.andar-controls legend{margin-bottom:8px}.andar-controls input,.andar-controls button{min-height:44px}.andar-primary{background:var(--red,#a51f2d);color:#fff}.andar-sides{display:grid;grid-template-columns:1fr 1fr;gap:10px}.andar-sides [aria-pressed=true]{outline:2px solid var(--gold);background:rgba(255,215,128,.14)}.andar-help,.andar-retry,.andar-empty{color:var(--muted,#b8c8c1)}.andar-error{min-height:1.4em;margin:0;color:#ffd1d1}.andar-stage{display:grid;align-content:center;gap:18px;min-width:0;min-height:450px;background:radial-gradient(circle at 50% 35%,rgba(35,17,61,.42),rgba(20,10,34,.96) 72%)}.andar-match-card{display:grid;justify-items:center;gap:10px}.andar-match-card h3{margin:0}.andar-match-card .playing-card{flex:none;width:clamp(4.8rem,8vw,7.2rem);font-size:clamp(1.1rem,2.5vw,1.8rem)}.andar-sequence{display:flex;gap:10px;min-height:118px;margin:0;padding:8px;overflow-x:auto;list-style:none;scrollbar-width:thin}.andar-dealt-card{display:grid;flex:0 0 82px;justify-items:center;gap:6px;padding:8px;border:1px solid rgba(255,255,255,.12);border-radius:10px;background:rgba(0,0,0,.18)}.andar-dealt-card span{font-size:.82rem;text-align:center}.andar-dealt-card .playing-card{width:4.2rem;font-size:1rem}.andar-match{border-color:var(--gold);background:rgba(255,215,128,.14)}.andar-result{min-height:2.8em;margin:0;text-align:center}.andar-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.andar-summary span{display:grid;gap:5px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.andar-summary strong{overflow-wrap:anywhere}.andar-data section{display:grid;gap:10px}.andar-rules{margin:0;padding-left:1.1rem}.andar-rules li+li{margin-top:7px}.andar-history-list{display:grid;gap:8px;max-height:285px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.andar-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:9px;background:rgba(0,0,0,.2)}.andar-shell button:focus-visible,.andar-shell input:focus-visible,.andar-history-list:focus-visible,.andar-sequence:focus-visible{outline:3px solid var(--gold);outline-offset:2px}/* Stack controls, stage, and data on compact screens. */@media(max-width:1100px){.andar-layout{grid-template-columns:1fr}.andar-controls{order:1}.andar-stage{order:2;min-height:380px}.andar-data{order:3}}/* Prevent card, summary, and action clipping on mobile. */@media(max-width:560px){.andar-header{align-items:start;flex-direction:column}.andar-panel,.andar-stage{padding:12px}.andar-stage{min-height:340px}.andar-summary{grid-template-columns:1fr 1fr}.andar-sides{grid-template-columns:1fr}.andar-history-list li{grid-template-columns:1fr}.andar-dealt-card{flex-basis:74px}}/* Remove decorative motion for reduced-motion users. */@media(prefers-reduced-motion:reduce){.andar-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}</style>';
}

// Bind semantic controls after each deterministic route render.
function bindEvents() {
  // Read the wager control once from the newly rendered rail.
  const wagerInput = root?.querySelector('#andar-wager');
  // Preserve valid wager edits without moving fake tokens.
  if (wagerInput) wagerInput.onchange = () => { wager = wagerValue(wagerInput.value); render(); };
  // Bind both side selection controls through one public state variable.
  root?.querySelectorAll('[data-side]').forEach(button => {
    // Change the selected side only while no unresolved action owns inputs.
    button.onclick = () => { if (!busy && !pendingPlay) { selectedSide = button.dataset.side; render(); } };
  });
  // Read the stable play action control.
  const playButton = root?.querySelector('[data-action="play"]');
  // Prepare or retry the exact same play identity and immutable inputs.
  if (playButton) playButton.onclick = () => {
    // Capture the configured wager before the busy render replaces the input.
    wager = wagerValue(wagerInput?.value ?? wager);
    // Preserve an unresolved action rather than charging a new identity after a lost response.
    pendingPlay = pendingPlay || { actionId: nextActionId(), wager, side: selectedSide };
    // Execute the prepared request through shared busy and error handling.
    runAction(play);
  };
}

// Render all game-owned regions from authenticated server state and locale resources.
function render() {
  // Stop late callbacks after the shell unmounts this route.
  if (!root) return;
  // Read the newest settled round once for a consistent frame.
  const roundItem = currentRound();
  // Build the translated game header before combining layout regions.
  const header = '<header class="andar-header"><div><p class="andar-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="andar-phase" role="status">' + safe(phaseLabel(roundItem)) + '</span></header>';
  // Build the control-stage-data layout in responsive reading order.
  const layout = '<div class="andar-layout">' + controlsHtml() + '<main class="andar-stage" aria-label="' + safe(text('stage.title')) + '">' + stageHtml(roundItem) + summaryHtml(roundItem) + '</main>' + dataHtml() + '</div>';
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = stylesHtml() + '<section class="andar-shell" data-testid="andar-bahar">' + header + layout + '</section>';
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

// Start or replay one idempotent wagered Andar Bahar round.
async function play() {
  // Capture the route node so late responses cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the prepared immutable action created by the click handler.
  const request = pendingPlay;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Post exactly the documented action identity, wager, and side without a caller player id.
  const payload = await post(API_ROOT + '/rounds', { action_id: request.actionId, wager: request.wager, side: request.side });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the authoritative reload-safe player state.
  state = payload.state;
  // Store server-published fixed rules for the data rail.
  rules = payload.rules || rules;
  // Adopt the committed wager and side from the returned round.
  wager = payload.round?.wager || request.wager;
  // Adopt the selected side from the returned round.
  selectedSide = payload.round?.selected_side || request.side;
  // Clear the retry identity only after a successful response proves the play.
  pendingPlay = null;
  // Refresh the persistent authenticated wallet after the debit and optional payout.
  await refreshBalance();
}

// Export the catalog-owned lazy game module contract.
export const AndarBaharGame = {
  // Expose the stable descriptor identifier without player-visible copy.
  id: 'andar_bahar',
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
    pendingPlay = null;
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
    pendingPlay = null;
    // Clear the reserved localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this game.
  },
};
