// Implement the isolated Plinko browser module for GitHub issue #136.

// Import authenticated envelope-aware API helpers without caller-owned player ids.
import { api, post } from '../core/api.js';
// Import locale loading, formatting, translation, and subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Import safe markup, wallet refresh, and localized feedback helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';

// Address every browser-visible string through the game-owned locale domain.
const DOMAIN = 'games/plinko';
// Address the additive frozen-v1 Plinko proposal API through one stable root.
const API_ROOT = '/api/v1/games/plinko';
// Preserve the fixed row count used by the proposed backend profile.
const ROW_COUNT = 8;

// Retain the current shell outlet for deterministic rerenders and stale-response guards.
let root = null;
// Retain the latest authenticated player-scoped public state.
let state = null;
// Retain server-published rule metadata for reload-safe presentation.
let rules = { rows: ROW_COUNT, multipliers: [] };
// Retain the configured wager until the player changes it.
let wager = 5;
// Prevent overlapping atomic drop actions.
let busy = false;
// Retain the locale unsubscribe callback for route cleanup.
let unsubscribeLocale = null;
// Retain an unresolved drop identity and immutable wager for safe retry.
let pendingDrop = null;
// Retain the drop currently replayed by the stage.
let currentDrop = null;
// Retain the last committed wager so one click can repeat the same drop.
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
  if (globalThis.crypto?.randomUUID) return 'plinko-' + globalThis.crypto.randomUUID();
  // Advance a per-module counter before building the fallback identity.
  actionCounter += 1;
  // Combine a timestamp and counter without presenting the value to the player.
  return 'plinko-' + Date.now().toString(36) + '-' + actionCounter.toString(36);
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

// Normalize the wager input into the documented ledger-compatible range.
function wagerValue(value) {
  // Convert the browser value while preserving the prior selection after malformed input.
  const parsed = Number(value);
  // Reuse the prior wager when the browser value is not finite.
  if (!Number.isFinite(parsed)) return wager;
  // Clamp the configured amount to the public API boundary.
  return Math.min(100000, Math.max(0.01, Math.round(parsed * 100) / 100));
}

// Return the newest committed drop for the stage and history.
function latestDrop() {
  // Prefer the explicit replay target before bounded server history.
  return currentDrop || state?.recent_drops?.slice(-1)[0] || null;
}

// Translate internal drop state into concise player-facing status.
function phaseLabel(drop) {
  // Show the ready phase before the first drop.
  if (!drop) return text('phases.ready');
  // Show the committed result without exposing internal enum values.
  return text('phases.settled', { bucket: Number(drop.bucket) + 1, multiplier: drop.multiplier });
}

// Compute a display coordinate for one committed path step.
function pathPoint(path, row) {
  // Count right decisions up to this row to place the puck.
  const rights = path.slice(0, row).filter(step => step === 'R').length;
  // Center each row within the triangular board.
  const x = 50 + (rights - row / 2) * 9;
  // Space rows evenly from top to buckets.
  const y = 8 + row * 9;
  // Return percent coordinates used by CSS custom properties.
  return { x, y };
}

// Render the peg field as deterministic, non-random client markup.
function pegsHtml() {
  // Build each peg row from the fixed row count.
  const rows = Array.from({ length: ROW_COUNT }, (_, row) => {
    // Render one more peg than the zero-based row index.
    const pegs = Array.from({ length: row + 1 }, (_, column) => '<span class="plinko-peg" style="--peg-x:' + (50 + (column - row / 2) * 9) + '%;--peg-y:' + (16 + row * 8) + '%"></span>').join('');
    // Return row-owned peg markup without visible text.
    return pegs;
  // Join all rows into one board layer.
  }).join('');
  // Return every peg as a presentational marker.
  return '<div class="plinko-pegs" aria-hidden="true">' + rows + '</div>';
}

// Render transparent bucket multipliers from server rules.
function bucketsHtml(drop) {
  // Read server-provided multipliers or a placeholder profile.
  const multipliers = rules.multipliers?.length ? rules.multipliers : Array.from({ length: ROW_COUNT + 1 }, () => 0);
  // Build every bucket in stable left-to-right order.
  return multipliers.map((multiplier, index) => {
    // Mark the committed result bucket without relying on color alone.
    const selected = drop && Number(drop.bucket) === index;
    // Build a localized accessible bucket label.
    const label = text('stage.bucketAria', { bucket: index + 1, multiplier });
    // Return one bucket cell with visible multiplier disclosure.
    return '<span class="plinko-bucket' + (selected ? ' is-hit' : '') + '" aria-label="' + safe(label) + '">' + safe(text('stage.multiplier', { multiplier })) + '</span>';
  // Join bucket cells into the stage rail.
  }).join('');
}

// Render the replay puck from the committed backend path.
function puckHtml(drop) {
  // Hide the puck until the server commits an outcome.
  if (!drop?.path?.length) return '';
  // Calculate final position from the committed path.
  const finalPoint = pathPoint(drop.path, drop.path.length);
  // Serialize intermediate points for static frontend verification.
  const route = drop.path.map((_, index) => pathPoint(drop.path, index + 1));
  // Return one animated or instant replay marker whose route is data, not RNG.
  return '<span class="plinko-puck" data-path="' + safe(drop.path.join('')) + '" data-route="' + safe(JSON.stringify(route)) + '" style="--puck-x:' + finalPoint.x + '%;--puck-y:' + finalPoint.y + '%"></span>';
}

// Render the dominant committed-outcome stage.
function stageHtml(drop) {
  // Choose localized stage guidance based on whether a drop exists.
  const message = drop ? text('results.settled', { bucket: Number(drop.bucket) + 1, multiplier: drop.multiplier, payout: tokenAmount(drop.payout) }) : text('stage.readyBody');
  // Return pegboard, replay puck, bucket row, and live status in reserved regions.
  return '<main class="plinko-stage" aria-label="' + safe(text('stage.title')) + '">' + pegsHtml() + puckHtml(drop) + '<div class="plinko-buckets" role="list" aria-label="' + safe(text('stage.bucketsAria')) + '">' + bucketsHtml(drop) + '</div><p class="plinko-result" role="status" aria-live="polite">' + safe(message) + '</p></main>';
}

// Render the control rail for one atomic drop action.
function controlsHtml() {
  // Lock configuration while a request is busy or retryable.
  const locked = busy || Boolean(pendingDrop);
  // Enable the one-click repeat only when a prior drop exists and no request or retry is active.
  const repeatDisabled = busy || Boolean(pendingDrop) || !lastBet;
  // Change the drop label when the same unresolved action can be retried.
  const dropLabel = pendingDrop ? text('controls.retryDrop') : text('controls.drop');
  // Explain why configuration remains locked after an ambiguous response.
  const retryHelp = pendingDrop ? '<p class="plinko-retry" role="status">' + safe(text('controls.retryHelp')) + '</p>' : '';
  // Return a stable control rail whose primary action never moves between phases.
  return '<aside class="plinko-panel plinko-controls" aria-label="' + safe(text('controls.title')) + '"><h2>' + safe(text('controls.title')) + '</h2><label for="plinko-wager">' + safe(text('controls.wager')) + '</label><input id="plinko-wager" type="number" min="0.01" max="100000" step="0.01" value="' + safe(wager) + '"' + (locked ? ' disabled' : '') + '><button type="button" class="plinko-primary" data-action="drop"' + (busy ? ' disabled' : '') + '>' + safe(dropLabel) + '</button><button type="button" class="plinko-repeat" data-action="repeat"' + (repeatDisabled ? ' disabled' : '') + '>' + safe(text('controls.repeat')) + '</button>' + retryHelp + '<p class="plinko-help">' + safe(text('controls.help')) + '</p><p class="plinko-error" role="alert" data-error>' + (lastErrorKey ? safe(text(lastErrorKey)) : '') + '</p></aside>';
}

// Render wager and settlement facts in one reserved summary region.
function summaryHtml(drop) {
  // Show a localized placeholder before values become available.
  const pending = text('summary.pending');
  // Format every fact only after the server commits a drop.
  const values = {
    // Show the committed play-token wager or the placeholder.
    wager: drop ? tokenAmount(drop.wager) : pending,
    // Show one-based bucket numbers to players.
    bucket: drop ? String(Number(drop.bucket) + 1) : pending,
    // Show the transparent multiplier using localized copy.
    multiplier: drop ? text('stage.multiplier', { multiplier: drop.multiplier }) : pending,
    // Show the returned tokens after settlement.
    payout: drop ? tokenAmount(drop.payout) : pending,
    // Show the net result after the original wager.
    net: drop ? tokenAmount(drop.net) : pending,
  };
  // Return aligned facts that retain the same positions through every phase.
  return '<section class="plinko-summary" aria-label="' + safe(text('summary.title')) + '"><span>' + safe(text('summary.wager')) + '<strong>' + safe(values.wager) + '</strong></span><span>' + safe(text('summary.bucket')) + '<strong>' + safe(values.bucket) + '</strong></span><span>' + safe(text('summary.multiplier')) + '<strong>' + safe(values.multiplier) + '</strong></span><span>' + safe(text('summary.payout')) + '<strong>' + safe(values.payout) + '</strong></span><span>' + safe(text('summary.net')) + '<strong>' + safe(values.net) + '</strong></span></section>';
}

// Render bounded reload-safe history with localized results and accessible row names.
function historyHtml() {
  // Copy newest settled drops first without mutating authenticated state.
  const drops = [...(state?.recent_drops || [])].reverse();
  // Show an explicit localized empty state before the first settlement.
  if (!drops.length) return '<p class="plinko-empty">' + safe(text('history.empty')) + '</p>';
  // Render every bounded server-owned drop as one concise result row.
  const rows = drops.map((drop, index) => {
    // Build a localized accessible row name with a stable newest-first number.
    const label = text('history.dropAria', { number: drops.length - index, bucket: Number(drop.bucket) + 1, multiplier: drop.multiplier });
    // Return one aligned history row with explicit returned-token wording.
    return '<li aria-label="' + safe(label) + '"><span>' + safe(text('history.result', { bucket: Number(drop.bucket) + 1, multiplier: drop.multiplier })) + '</span><strong>' + safe(tokenAmount(drop.payout)) + '</strong></li>';
  // Join bounded rows into the single intentional history scroll surface.
  }).join('');
  // Return one intentional keyboard-focusable scroll region without nested scrolling.
  return '<ol class="plinko-history-list" tabindex="0" aria-label="' + safe(text('history.listAria')) + '">' + rows + '</ol>';
}

// Render rules and recent results in the supporting data rail.
function dataHtml(drop) {
  // Read server rule values while preserving documented defaults during initial loading.
  const rows = rules.rows || ROW_COUNT;
  // Return distinct rule, summary, and history regions in one supporting rail.
  return '<aside class="plinko-panel plinko-data" aria-label="' + safe(text('data.title')) + '"><section><h2>' + safe(text('rules.title')) + '</h2><ul class="plinko-rules"><li>' + safe(text('rules.serverPath')) + '</li><li>' + safe(text('rules.rows', { rows })) + '</li><li>' + safe(text('rules.multipliers')) + '</li></ul></section>' + summaryHtml(drop) + '<section><h2>' + safe(text('history.title')) + '</h2>' + historyHtml() + '</section></aside>';
}

// Return scoped responsive styles without modifying the shared application stylesheet.
function stylesHtml() {
  // Define dominant stage, stable controls, responsive stack, focus, and reduced-motion rules.
  return '<style>/* Establish the Plinko control-stage-data hierarchy. */.plinko-shell{display:grid;gap:16px;min-width:0}.plinko-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.plinko-header h1{margin:0}.plinko-eyebrow{margin:0 0 4px;color:var(--muted,#b8c8c1)}.plinko-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px;color:var(--gold,#f6d47a)}.plinko-layout{display:grid;grid-template-columns:minmax(210px,.7fr) minmax(540px,2.4fr) minmax(250px,.85fr);gap:16px;align-items:start}.plinko-panel,.plinko-stage{border:1px solid var(--gold);border-radius:16px;background:rgba(20,10,34,.88);padding:16px}.plinko-controls,.plinko-data{display:grid;align-content:start;gap:13px}.plinko-controls h2,.plinko-data h2{margin:0}.plinko-controls input,.plinko-controls button{min-height:44px}.plinko-primary{background:var(--red,#a51f2d);color:#fff}.plinko-help,.plinko-retry,.plinko-empty{color:var(--muted,#b8c8c1)}.plinko-error{min-height:1.4em;margin:0;color:var(--bad)}.plinko-stage{position:relative;display:grid;grid-template-rows:1fr auto auto;gap:16px;min-height:470px;overflow:hidden;background:radial-gradient(circle at 50% 18%,rgba(20,10,34,.45),rgba(20,10,34,.96) 68%)}.plinko-pegs{position:relative;min-height:330px}.plinko-peg{position:absolute;left:var(--peg-x);top:var(--peg-y);width:10px;height:10px;border-radius:50%;background:#f6d47a;box-shadow:0 0 0 3px rgba(246,212,122,.12)}.plinko-puck{position:absolute;left:var(--puck-x);top:var(--puck-y);width:22px;height:22px;border-radius:50%;background:#e94057;box-shadow:0 0 18px rgba(233,64,87,.8);transform:translate(-50%,-50%);animation:plinko-drop .8s ease-out both}.plinko-buckets{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:6px}.plinko-bucket{display:grid;place-items:center;min-height:42px;border:1px solid rgba(255,255,255,.16);border-radius:8px;background:rgba(255,255,255,.06);font-weight:700}.plinko-bucket.is-hit{outline:3px solid var(--gold);background:rgba(165,31,45,.65)}.plinko-result{min-height:2.8em;margin:0;text-align:center}.plinko-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.plinko-summary span{display:grid;gap:5px;padding:10px;border-radius:10px;background:rgba(255,255,255,.05)}.plinko-summary strong{overflow-wrap:anywhere}.plinko-rules{margin:0;padding-left:1.1rem}.plinko-rules li+li{margin-top:7px}.plinko-history-list{display:grid;gap:8px;max-height:245px;margin:0;padding:0;overflow:auto;list-style:none;scrollbar-width:thin}.plinko-history-list li{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px;border-radius:9px;background:rgba(0,0,0,.2)}.plinko-shell button:focus-visible,.plinko-shell input:focus-visible,.plinko-history-list:focus-visible{outline:3px solid var(--gold);outline-offset:2px}@keyframes plinko-drop{from{left:50%;top:7%;opacity:.75}to{left:var(--puck-x);top:var(--puck-y);opacity:1}}/* Stack controls, stage, and data on compact screens. */@media(max-width:1100px){.plinko-layout{grid-template-columns:1fr}.plinko-controls{order:1}.plinko-stage{order:2;min-height:390px}.plinko-data{order:3}}/* Prevent bucket and summary clipping on mobile. */@media(max-width:520px){.plinko-header{align-items:start;flex-direction:column}.plinko-panel,.plinko-stage{padding:12px}.plinko-stage{min-height:340px}.plinko-pegs{min-height:250px}.plinko-buckets{gap:3px}.plinko-bucket{font-size:.78rem;min-height:36px}.plinko-summary{grid-template-columns:1fr}.plinko-history-list li{grid-template-columns:1fr}}/* Make replay instant for reduced-motion users. */@media(prefers-reduced-motion:reduce){.plinko-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}.plinko-puck{animation:none!important}}</style>.plinko-repeat{background:transparent;color:var(--gold);border:1px solid var(--gold)}.plinko-repeat:disabled{opacity:.5}';
}

// Return repeat-aware styles without exposing CSS text after the style element.
function repeatSafeStylesHtml() {
  // Move the additive repeat rules ahead of the closing style tag.
  const scoped = stylesHtml().replace('</style>.plinko-repeat', '.plinko-repeat');
  // Close the corrected style element after every scoped repeat rule.
  return scoped + '</style>';
}

// Bind semantic controls after each deterministic route render.
function bindEvents() {
  // Read the wager control once from the newly rendered rail.
  const wagerInput = root?.querySelector('#plinko-wager');
  // Preserve valid wager edits without moving fake tokens.
  if (wagerInput) wagerInput.onchange = () => { wager = wagerValue(wagerInput.value); };
  // Read the stable drop action control.
  const dropButton = root?.querySelector('[data-action="drop"]');
  // Prepare or retry the exact same drop identity and immutable wager.
  if (dropButton) dropButton.onclick = () => {
    // Capture the configured wager before the busy render replaces the input.
    wager = wagerValue(wagerInput?.value ?? wager);
    // Preserve an unresolved action rather than charging a new identity after a lost response.
    pendingDrop = pendingDrop || { actionId: nextActionId(), wager };
    // Execute the prepared request through shared busy and error handling.
    runAction(drop);
  };
  // Read the secondary one-click repeat control.
  const repeatButton = root?.querySelector('[data-action="repeat"]');
  // Re-fire the previous drop with the same committed wager.
  if (repeatButton) repeatButton.onclick = () => repeat();
}

// Re-apply the last committed wager and re-fire one idempotent drop without a timer.
function repeat() {
  // Ignore repeat while busy, holding an unresolved retry, or without a prior drop.
  if (busy || pendingDrop || !lastBet) return;
  // Restore the previous stake into the local configuration.
  wager = lastBet.wager;
  // Prepare a fresh exactly-once identity for the restored wager.
  pendingDrop = { actionId: nextActionId(), wager };
  // Execute the prepared request through shared busy and error handling.
  runAction(drop);
}

// Render all game-owned regions from authenticated server state and locale resources.
function render() {
  // Stop late callbacks after the shell unmounts this route.
  if (!root) return;
  // Read the committed drop once for a consistent frame.
  const drop = latestDrop();
  // Build the translated game header before combining layout regions.
  const header = '<header class="plinko-header"><div><p class="plinko-eyebrow">' + safe(text('eyebrow')) + '</p><h1>' + safe(text('title')) + '</h1></div><span class="plinko-phase" role="status">' + safe(phaseLabel(drop)) + '</span></header>';
  // Build the control-stage-data layout in responsive reading order.
  const layout = '<div class="plinko-layout">' + controlsHtml() + stageHtml(drop) + dataHtml(drop) + '</div>';
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = repeatSafeStylesHtml() + '<section class="plinko-shell" data-testid="plinko">' + header + layout + '</section>';
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

// Start or replay one idempotent server-authoritative Plinko drop.
async function drop() {
  // Capture the route node so late responses cannot overwrite a later mount.
  const mountedRoot = root;
  // Require the prepared immutable action created by the click handler.
  const request = pendingDrop;
  // Stop if route state changed before the action began.
  if (!request || !mountedRoot) return;
  // Post exactly the documented action identity and wager without a caller player id.
  const payload = await post(API_ROOT + '/drops', { action_id: request.actionId, wager: request.wager });
  // Ignore a response that belongs to an unmounted or replaced route.
  if (root !== mountedRoot) return;
  // Store the authoritative reload-safe player state.
  state = payload.state;
  // Store server-published fixed rules for the data rail.
  rules = payload.rules || rules;
  // Store the committed path for client-only replay.
  currentDrop = payload.drop;
  // Adopt the committed wager from the returned drop.
  wager = payload.drop?.wager || request.wager;
  // Remember the settled wager so the next round can repeat with one click.
  if (payload.drop) lastBet = { wager: payload.drop.wager };
  // Clear the retry identity only after a successful response proves the drop.
  pendingDrop = null;
  // Refresh the persistent authenticated wallet after debit and settlement.
  await refreshBalance();
}

// Export the catalog-owned lazy game module contract.
export const PlinkoGame = {
  // Expose the stable descriptor identifier without player-visible copy.
  id: 'plinko',
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
    // Clear retry identity because reload-safe server state reconciles committed actions.
    pendingDrop = null;
    // Clear the replay target until state loads.
    currentDrop = null;
    // Clear the repeatable wager so another session never inherits it.
    lastBet = null;
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
    rules = payload.rules || rules;
    // Recover a repeatable wager from the newest settled drop so repeat survives a reload.
    const restored = latestDrop();
    // Restore the repeatable configuration only when a settled drop is present.
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
    rules = { rows: ROW_COUNT, multipliers: [] };
    // Release the in-flight presentation lock.
    busy = false;
    // Forget route-local retry identity after server state becomes the recovery source.
    pendingDrop = null;
    // Clear the committed replay target after teardown.
    currentDrop = null;
    // Clear the repeatable wager so the next session starts fresh.
    lastBet = null;
    // Clear the reserved localized error state.
    lastErrorKey = null;
    // No timers or global event listeners are owned by this game.
  },
};
