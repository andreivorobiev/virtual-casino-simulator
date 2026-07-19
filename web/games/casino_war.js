// Provide the isolated Casino War browser module for GitHub issue #82.
// Requirements: CARD-002, CORE-008, I18N-001, I18N-002.

// Import the standard API helpers used by dynamically loaded game modules.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import safe markup, error presentation, and shared wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the merged accessible card primitive instead of creating game-owned cards.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and live-switch subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Address the additive Casino War API from one stable root.
const API_ROOT = '/api/v1/games/casino-war';
// Address the game-owned EN/RU resource domain.
const DOMAIN = 'games/casino_war';
// Identify the shared card stylesheet so it is installed at most once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Offer stable wager choices without hard-coded visible labels.
const WAGERS = [5, 25, 100, 500];

// Retain the active mount node without creating global shell state.
let root = null;
// Retain the latest player-scoped API state for locale-only rerenders.
let state = null;
// Prevent duplicate clicks from starting overlapping atomic actions.
let busy = false;
// Retain the locale unsubscribe callback for leak-free unmount.
let unsubscribeLocale = null;

// Read one localized Casino War string after the domain has loaded.
function text(key, params = {}) {
  // Delegate all visible copy to the game-owned resource domain.
  return t(key, params, DOMAIN);
}

// Format a play-token amount without a currency or replacement-looking glyph.
function tokenAmount(value) {
  // Wrap a locale-formatted number in explicit localized play-token language.
  return text('tokens.amount', { amount: formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) });
}

// Install the merged CARD-002 presentation hooks without editing the global shell.
function ensureSharedCardStyles() {
  // Reuse an existing stylesheet installed by this or a future card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create one standard stylesheet link for the shared card renderer.
  const link = document.createElement('link');
  // Mark the link so later mounts remain idempotent.
  link.id = CARD_STYLE_ID;
  // Load the merged shared card CSS from the public web root.
  link.rel = 'stylesheet';
  // Point to the CARD-002 stylesheet without copying it into this module.
  link.href = '/core/cards.css';
  // Append the stylesheet to document metadata once.
  document.head.append(link);
}

// Generate one bounded client action id for replay-safe API commands.
function newActionId() {
  // Prefer a browser-native UUID when available.
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  // Fall back to a namespaced timestamp and random suffix for older local browsers.
  return `browser-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

// Retain unresolved idempotency identities per command across ambiguous failures, each bound to its immutable payload and owner. (issue #261)
const pendingCommands = new Map();

// Read the authenticated player id from the shared shell session without trusting caller-controlled fields.
function sessionPlayerId() {
  // Return the current-user player id published by the shell, or null before authentication resolves.
  return globalThis.CasinoCurrentUser?.player?.player_id || null;
}

// Return a stable canonical signature for one command payload so changed intent is detectable.
function commandSignature(payload) {
  // Serialize sorted entries so equivalent payloads always produce one identical signature.
  return JSON.stringify(Object.keys(payload || {}).sort().map(key => [key, payload[key]]));
}

// Report whether a structured API error definitively resolves the pending command so it is safe to discard.
function isDefinitiveRejection(error) {
  // Treat validation, balance, auth, route, and conflict errors as non-ambiguous server responses.
  return ['VALIDATION_ERROR', 'INSUFFICIENT_FUNDS', 'UNAUTHORIZED', 'FORBIDDEN', 'NOT_FOUND', 'CONFLICT'].includes(error?.code);
}

// Resolve the frozen retry entry for one command, reusing its identity only for the identical player and immutable payload. (issue #261)
function resolveCommand(commandKey, payload) {
  // Read the authenticated player that would own this command.
  const playerId = sessionPlayerId();
  // Read any unresolved entry retained for this command key.
  const existing = pendingCommands.get(commandKey);
  // Reuse the retained identity only when the same player resubmits the exact same immutable payload after an ambiguous failure.
  if (existing && existing.playerId === playerId && commandSignature(existing.payload) === commandSignature(payload)) return existing;
  // Mint a fresh identity for a new intent bound to the immutable payload and owner before any network work.
  const entry = { actionId: newActionId(), payload: Object.freeze({ ...payload }), playerId };
  // Retain the entry so a retry after a lost response replays the identical identity and body.
  pendingCommands.set(commandKey, entry);
  // Return the frozen retry entry to the caller.
  return entry;
}

// Clear one command's unresolved identity after the backend proves its outcome.
function clearCommand(commandKey) {
  // Remove only the acknowledged command's retry entry.
  pendingCommands.delete(commandKey);
}

// Reconcile all unresolved command identities against the authoritative ledger and current ownership. (issue #261)
function reconcileCommands() {
  // Read the authoritative committed action ledger from the current public state.
  const ledgerActions = state?.ledger_actions || {};
  // Read the current authenticated player for ownership checks.
  const playerId = sessionPlayerId();
  // Inspect every retained command entry against authoritative state.
  for (const [key, entry] of [...pendingCommands.entries()]) {
    // Clear an identity already committed to the authoritative ledger.
    if (entry.actionId in ledgerActions) { pendingCommands.delete(key); continue; }
    // Clear an identity owned by a different authenticated player in this tab.
    if (entry.playerId && playerId && entry.playerId !== playerId) pendingCommands.delete(key);
  }
}

// Release every unresolved retry identity on teardown so a later mount or session cannot inherit one. (issue #261)
function clearAllCommands() {
  // Remove all retained command entries.
  pendingCommands.clear();
}

// Return the newest actionable or settled round for the center stage.
function currentRound() {
  // Prefer the explicit active round and then newest retained history.
  return state?.active_round || state?.rounds?.[0] || null;
}

// Translate one internal phase into concise player-facing language.
function phaseLabel(roundItem = currentRound()) {
  // Show the ready phase when no round has been dealt.
  if (!roundItem) return text('phase.ready');
  // Translate the stable API phase through owned resources.
  return text(`phase.${roundItem.phase}`);
}

// Translate one outcome without exposing internal API labels.
function outcomeLabel(roundItem) {
  // Show the localized pending label until a round exists.
  if (!roundItem) return text('outcome.pending');
  // Resolve every documented outcome through EN/RU resources.
  return text(`outcome.${roundItem.outcome || 'pending'}`);
}

// Translate one card into a localized accessible name.
function cardLabel(card) {
  // Return the localized empty-slot label before cards exist.
  if (!card) return text('card.waiting');
  // Resolve localized rank and suit names through game resources.
  return text('card.label', { rank: text(`rank.${card.rank}`), suit: text(`suit.${card.suit}`) });
}

// Render one CARD-002 primitive while localizing its accessible name.
function localizedCard(card) {
  // Render an accessible shared card or an empty reserved slot.
  if (!card) return `<div class="cw-card-empty" aria-label="${safe(text('card.waiting'))}"></div>`;
  // Create the merged primitive markup from the API card object.
  const markup = renderCard(card);
  // Replace the primitive's default English label with this module's active locale.
  return markup.replace(/aria-label="[^"]*"/, `aria-label="${safe(cardLabel(card))}"`);
}

// Return scoped styles that keep the center table visually dominant.
function styleHtml() {
  // Keep the desktop card stage visually stronger than both support rails.
  const desktop = '.casino-war{display:grid;gap:14px;min-height:0}.cw-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.cw-header h1{margin:0}.cw-phase{padding:7px 12px;border:1px solid rgba(255,215,128,.45);border-radius:999px;color:var(--gold,#f6d47a)}.cw-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(500px,2.2fr) minmax(210px,.72fr);gap:14px;min-height:0}.cw-panel{min-width:0;border:1px solid rgba(255,215,128,.24);border-radius:16px;background:rgba(5,32,23,.9);padding:16px}.cw-controls,.cw-history{display:grid;align-content:start;gap:14px}.cw-controls label{display:grid;gap:7px}.cw-controls select,.cw-controls button{min-height:44px}.cw-actions{display:grid;gap:10px}.cw-actions.dual{grid-template-columns:1fr 1fr}.cw-primary{background:var(--red,#a92a38);color:#fff}.cw-stage{display:grid;grid-template-rows:auto 1fr auto;gap:18px;min-width:0;background:radial-gradient(circle at 50% 35%,rgba(28,112,72,.38),rgba(3,24,17,.96) 68%)}.cw-stage-head{display:flex;justify-content:space-between;gap:12px}.cw-stage-head h2{margin:0}.cw-table{display:grid;grid-template-columns:1fr 1fr;gap:clamp(18px,5vw,64px);align-items:center;justify-items:center;min-height:310px}.cw-hand{display:grid;justify-items:center;gap:12px}.cw-hand h3{margin:0}.cw-card-empty{width:clamp(3.25rem,10vw,6.5rem);aspect-ratio:5/7;border:2px dashed rgba(255,255,255,.24);border-radius:.65rem}.cw-war-row{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding-top:14px;border-top:1px solid rgba(255,255,255,.12)}.cw-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.cw-stat{padding:10px;border-radius:10px;background:rgba(0,0,0,.2)}.cw-stat strong{overflow-wrap:anywhere}.cw-stat span,.cw-history time{display:block;color:var(--muted,#b8c7c0);font-size:.78rem}.cw-history-list{display:grid;gap:9px;max-height:420px;overflow:auto;scrollbar-width:thin}.cw-history-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,7.5rem);gap:5px;padding:10px;border-radius:10px;background:rgba(0,0,0,.18)}.cw-history-row>span{text-align:right;overflow-wrap:anywhere}.cw-rules{margin:0;padding-left:1.1rem}.cw-rules li+li{margin-top:8px}.cw-muted{color:var(--muted,#b8c7c0)}';
  // Stack controls, stage, and data on tablet widths.
  const tablet = '@media (max-width:1100px){.cw-layout{grid-template-columns:1fr}.cw-controls{order:1}.cw-stage{order:2}.cw-history{order:3}.cw-table{min-height:260px}}';
  // Prevent clipping and horizontal overflow on mobile.
  const mobile = '@media (max-width:520px){.cw-header{align-items:start;flex-direction:column}.cw-table{gap:12px;min-height:220px}.cw-summary,.cw-war-row{grid-template-columns:1fr}.cw-actions.dual{grid-template-columns:1fr}.cw-panel{padding:13px}}';
  // Remove decorative motion when the user requests reduced motion.
  const reducedMotion = '@media (prefers-reduced-motion:reduce){.casino-war *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}';
  // Return one scoped stylesheet without editing the shared shell CSS.
  return `<style>${desktop}${tablet}${mobile}${reducedMotion}</style>`;
}

// Render the fixed control rail for ready, decision, and settled phases.
function controlsHtml(roundItem) {
  // Determine whether the current phase requires a tie decision.
  const decision = roundItem?.phase === 'war_decision';
  // Build localized wager options without embedding visible English.
  const options = WAGERS.map(value => `<option value="${value}">${safe(tokenAmount(value))}</option>`).join('');
  // Render decision controls only while an initial tie is actionable.
  const actions = decision
    // Offer both allowed tie decisions together.
    ? `<div class="cw-actions dual"><button type="button" data-action="surrender" ${busy ? 'disabled' : ''}>${safe(text('controls.surrender'))}</button><button type="button" class="cw-primary" data-action="war" ${busy ? 'disabled' : ''}>${safe(text('controls.war'))}</button></div>`
    // Offer the next deal outside the tie-decision phase.
    : `<div class="cw-actions"><button type="button" class="cw-primary" data-action="deal" ${busy ? 'disabled' : ''}>${safe(roundItem ? text('controls.dealNext') : text('controls.deal'))}</button></div>`;
  // Return the stable control panel with wager and primary action above the fold.
  return `<section class="cw-panel cw-controls" aria-label="${safe(text('controls.region'))}"><h2>${safe(text('controls.title'))}</h2><label>${safe(text('controls.wager'))}<select data-testid="casino-war-wager" ${decision || busy ? 'disabled' : ''}>${options}</select></label>${actions}<p class="cw-muted">${safe(decision ? text('controls.tieHelp') : text('controls.readyHelp'))}</p><h3>${safe(text('rules.title'))}</h3><ul class="cw-rules"><li>${safe(text('rules.highCard'))}</li><li>${safe(text('rules.surrender'))}</li><li>${safe(text('rules.war'))}</li><li>${safe(text('rules.secondTie'))}</li></ul></section>`;
}

// Render one labeled hand with its initial and optional war card.
function handHtml(side, initialCard, warCard) {
  // Resolve the localized side label from owned resources.
  const sideLabel = text(`side.${side}`);
  // Render stable initial and war card slots without timer-driven reveals.
  return `<section class="cw-hand" aria-label="${safe(sideLabel)}"><h3>${safe(sideLabel)}</h3>${localizedCard(initialCard)}${warCard ? `<div><span class="cw-muted">${safe(text('stage.warCard'))}</span>${localizedCard(warCard)}</div>` : ''}</section>`;
}

// Render the dominant card table and settlement summary.
function stageHtml(roundItem) {
  // Read public values through zero-safe fallbacks.
  const wager = Number(roundItem?.wager || 0);
  // Read the optional matching war wager.
  const warWager = Number(roundItem?.war_wager || 0);
  // Read the total credited payout including returned stakes.
  const payout = Number(roundItem?.payout || 0);
  // Render the shared-card stage with no game-owned animation timers.
  return `<section class="cw-panel cw-stage" data-testid="casino-war-table"><div class="cw-stage-head"><div><p class="cw-muted">${safe(roundItem ? text('stage.round', { id: roundItem.round_id }) : text('stage.noRound'))}</p><h2>${safe(outcomeLabel(roundItem))}</h2></div><strong>${safe(phaseLabel(roundItem))}</strong></div><div class="cw-table"><div>${handHtml('player', roundItem?.player_card, roundItem?.war_player_card)}</div><div>${handHtml('dealer', roundItem?.dealer_card, roundItem?.war_dealer_card)}</div></div>${roundItem?.burn_cards?.length ? `<div class="cw-war-row"><span>${safe(text('stage.burned', { count: roundItem.burn_cards.length }))}</span><span>${safe(text('stage.tieRule'))}</span></div>` : ''}<div class="cw-summary"><div class="cw-stat"><span>${safe(text('summary.ante'))}</span><strong>${safe(tokenAmount(wager))}</strong></div><div class="cw-stat"><span>${safe(text('summary.warWager'))}</span><strong>${safe(tokenAmount(warWager))}</strong></div><div class="cw-stat"><span>${safe(text('summary.payout'))}</span><strong>${safe(tokenAmount(payout))}</strong></div></div></section>`;
}

// Render bounded reload-safe round history in the data rail.
function historyHtml() {
  // Read retained rounds from newest to oldest.
  const rounds = state?.rounds || [];
  // Build localized rows without exposing raw phase or outcome identifiers.
  const rows = rounds.map(roundItem => `<article class="cw-history-row"><div><strong>${safe(outcomeLabel(roundItem))}</strong><time>${safe(text('history.round', { id: roundItem.round_id }))}</time></div><span>${safe(tokenAmount(roundItem.payout))}</span></article>`).join('');
  // Return history and shoe telemetry in one intentional scroll rail.
  return `<aside class="cw-panel cw-history" aria-label="${safe(text('history.region'))}"><h2>${safe(text('history.title'))}</h2><div class="cw-summary"><div class="cw-stat"><span>${safe(text('history.shoe'))}</span><strong>${safe(state?.shoe_id || text('history.newShoe'))}</strong></div><div class="cw-stat"><span>${safe(text('history.cards'))}</span><strong>${safe(formatNumber(state?.shoe_count || 0))}</strong></div><div class="cw-stat"><span>${safe(text('history.shoes'))}</span><strong>${safe(formatNumber(state?.shoes_dealt || 0))}</strong></div></div><div class="cw-history-list" tabindex="0" aria-label="${safe(text('history.list'))}">${rows || `<p class="cw-muted">${safe(text('history.empty'))}</p>`}</div></aside>`;
}

// Replace the mounted view while preserving API state and locale subscriptions.
function render() {
  // Ignore late async work after unmount.
  if (!root) return;
  // Read the newest relevant round once for consistent panel rendering.
  const roundItem = currentRound();
  // Render title, phase, and the responsive three-zone hierarchy.
  root.innerHTML = `${styleHtml()}<main class="casino-war"><header class="cw-header"><div><p class="cw-muted">${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="cw-phase" aria-live="polite">${safe(phaseLabel(roundItem))}</span></header><div class="cw-layout">${controlsHtml(roundItem)}${stageHtml(roundItem)}${historyHtml()}</div></main>`;
  // Bind the phase-appropriate controls after replacing markup.
  bindEvents();
}

// Start a new round through the replay-safe API command.
async function deal() {
  // Ignore repeated clicks while a command is in flight.
  if (busy) return;
  // Read the selected wager, locking to the frozen pending snapshot after an ambiguous failure so a retry cannot change the charged amount. (issue #261)
  const wager = pendingCommands.get('deal')?.payload.wager ?? Number(root?.querySelector('[data-testid="casino-war-wager"]')?.value || WAGERS[0]);
  // Lock controls for the atomic request.
  busy = true;
  // Reflect the busy state without starting an animation timer.
  render();
  // Run the API command and restore controls on every path.
  try {
    // Resolve the frozen deal retry entry so a retry replays the exact same identity and wager. (issue #261)
    const command = resolveCommand('deal', { wager });
    // Send the current session player, the frozen wager, and the retained client idempotency key.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ wager: command.payload.wager, action_id: command.actionId }));
    // Clear the retained identity only after the server has confirmed this deal.
    clearCommand('deal');
    // Store the returned player-scoped public state.
    state = payload.state;
    // Refresh the shell wallet after ledger debit and optional credit.
    await refreshBalance();
  // Surface standard API failures through the shared toast outlet.
  } catch (error) {
    // Show the server-provided domain message without adding frontend fallback copy.
    toast(error.message);
    // Discard the pending deal identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearCommand('deal');
  // Always release the click lock.
  } finally {
    // Re-enable phase-appropriate controls.
    busy = false;
    // Render the latest successful or preserved state.
    render();
  }
}

// Resolve the current initial tie through surrender or war.
async function decide(decision) {
  // Ignore repeated clicks while a command is in flight.
  if (busy) return;
  // Read the current actionable round before disabling controls.
  const roundItem = currentRound();
  // Stop if stale markup has no tied round.
  if (!roundItem || roundItem.phase !== 'war_decision') return;
  // Lock both decision buttons for one atomic request.
  busy = true;
  // Reflect the busy state without timers.
  render();
  // Run the selected decision and restore controls on every path.
  try {
    // Key the retry entry per round and decision so distinct decisions never share an identity. (issue #261)
    const decisionKey = `${roundItem.round_id}:${decision}`;
    // Resolve the frozen decision retry entry bound to this exact round, decision, and player.
    const command = resolveCommand(decisionKey, { round_id: roundItem.round_id, decision });
    // Post the replay-safe decision to the round-specific endpoint with its retained identity.
    const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/${decision}`, withCurrentPlayer({ action_id: command.actionId }));
    // Clear the retained identity only after the server has confirmed this decision.
    clearCommand(decisionKey);
    // Store the terminal public state.
    state = payload.state;
    // Refresh the shared wallet after surrender credit or war settlement.
    await refreshBalance();
  // Surface standard API failures through the shared toast outlet.
  } catch (error) {
    // Show the server-provided domain message without hard-coded fallback copy.
    toast(error.message);
    // Discard the pending decision identity only when the server definitively resolved it; retain it after an ambiguous failure for a safe replay. (issue #261)
    if (isDefinitiveRejection(error)) clearCommand(`${roundItem.round_id}:${decision}`);
  // Always release the click lock.
  } finally {
    // Re-enable controls for the resulting phase.
    busy = false;
    // Render the latest successful or preserved state.
    render();
  }
}

// Bind controls created by the latest render.
function bindEvents() {
  // Bind the initial or next-round action when present.
  root?.querySelector('[data-action="deal"]')?.addEventListener('click', deal);
  // Bind surrender without creating a game-owned timer.
  root?.querySelector('[data-action="surrender"]')?.addEventListener('click', () => decide('surrender'));
  // Bind war through the matching-wager API action.
  root?.querySelector('[data-action="war"]')?.addEventListener('click', () => decide('war'));
}

// Export the catalog-loadable game contract expected by #81/#110.
export const CasinoWarGame = {
  // Identify the module consistently with its future descriptor.
  id: 'casino_war',
  // Mount player-scoped state without touching shared shell registration.
  async mount(node) {
    // Retain the shell-provided mount node.
    root = node;
    // Install shared card presentation once.
    ensureSharedCardStyles();
    // Load both active and fallback Casino War dictionaries before rendering.
    await loadI18nDomain(DOMAIN);
    // Rerender strings in place on locale changes without discarding game state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read and recover session-bound state through the additive v1 endpoint.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Store the public state for initial rendering.
    state = payload.state;
    // Reconcile any unresolved retry identities against the authoritative ledger and current ownership on mount. (issue #261)
    reconcileCommands();
    // Render the table only after localized copy is ready.
    render();
    // Align the persistent wallet with any recovered ledger action.
    await refreshBalance();
  },
  // Release subscriptions and local references when the shell changes route.
  unmount() {
    // Remove the locale callback to prevent detached rerenders.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference for a future mount.
    unsubscribeLocale = null;
    // Clear state so another user's later mount cannot reuse prior data.
    state = null;
    // Release every unresolved retry identity so a later mount or a different session cannot inherit one. (issue #261)
    clearAllCommands();
    // Release the DOM reference; this module owns no timers to cancel.
    root = null;
    // Release any in-flight visual lock for a future mount.
    busy = false;
  },
};
