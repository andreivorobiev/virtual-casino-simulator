// Implement the isolated issue #93 browser module without shared shell edits.

// Import session-aware API helpers so compatibility player ids remain subordinate to the authenticated session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the #96 semantic card renderer instead of creating game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/three_card_poker';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/three-card-poker';
// Identify the reusable #96 stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve Three Card Poker hand-strength order for localized displays.
const HAND_RANK_ORDER = ['straight_flush', 'three_of_a_kind', 'straight', 'flush', 'pair', 'high_card'];
// Preserve Pair Plus paytable order independently of object insertion behavior.
const PAIR_PLUS_ORDER = ['straight_flush', 'three_of_a_kind', 'straight', 'flush', 'pair'];
// Preserve Ante Bonus paytable order independently of object insertion behavior.
const ANTE_BONUS_ORDER = ['straight_flush', 'three_of_a_kind', 'straight'];
// Map accepted suit spellings to the owned locale keys used by card labels.
const SUIT_KEYS = Object.freeze({ C: 'clubs', CLUBS: 'clubs', D: 'diamonds', DIAMONDS: 'diamonds', H: 'hearts', HEARTS: 'hearts', S: 'spades', SPADES: 'spades' });

// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for paytable and qualification displays.
let rules = {};
// Store the configured Ante wager before the next round.
let ante = 5;
// Store the optional Pair Plus wager before the next round.
let pairPlus = 0;
// Prevent overlapping atomic browser actions.
let busy = false;
// Store the locale cleanup callback so unmount releases subscriptions.
let unsubscribeLocale = null;
// Track mount generations so late network responses cannot revive an old route.
let mountGeneration = 0;
// Store a fallback retry-id counter for browsers without randomUUID support.
let requestCounter = 0;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealRequestId = null;
// Bind the unresolved deal retry id to one Ante and Pair Plus payload.
let pendingDealContext = null;
// Retain an unresolved decision retry id independently from deal retries.
let pendingDecisionActionId = null;
// Bind the unresolved decision retry id to one round and one selected decision.
let pendingDecisionContext = null;


// Resolve one owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every player-visible and accessible label to the EN/RU domain.
  return t(key, params, DOMAIN);
}


// Format play-token values without a currency or replacement-looking glyph.
function tokenAmount(value) {
  // Interpolate a locale-formatted number into explicit fake-token terminology.
  return text('tokens.amount', { amount: formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) });
}


// Install the shared CARD-002 stylesheet without changing the global shell files.
function ensureSharedCardStyles() {
  // Reuse a stylesheet already installed by another card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create one standard stylesheet link for the shared renderer.
  const link = document.createElement('link');
  // Mark the link so future mounts remain idempotent.
  link.id = CARD_STYLE_ID;
  // Declare a normal stylesheet relationship for browser loading.
  link.rel = 'stylesheet';
  // Load the merged #96 presentation hooks from the public core path.
  link.href = '/core/cards.css';
  // Add the shared stylesheet to document metadata once.
  document.head.append(link);
}


// Create one bounded client retry id for exactly-once public actions.
function nextActionId(prefix) {
  // Prefer the browser cryptographic UUID source when available.
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  // Increment the fallback counter so same-millisecond actions remain distinct.
  requestCounter += 1;
  // Combine a namespaced prefix, timestamp, and counter without exposing it to players.
  return `${prefix}-${Date.now().toString(36)}-${requestCounter.toString(36)}`;
}


// Normalize a wager while preserving the allowed zero value for Pair Plus.
function normalizedWager(value, minimum) {
  // Convert browser input text to a numeric wager.
  const parsed = Number(value);
  // Return the lower bound for invalid or undersized values.
  if (!Number.isFinite(parsed) || parsed < minimum) return minimum;
  // Clamp oversized browser values to the public contract maximum.
  const bounded = Math.min(parsed, 100000);
  // Round to cents so previews match ledger-compatible request values.
  return Math.round(bounded * 100) / 100;
}


// Read the newest actionable or completed round from reload-safe server state.
function currentRound() {
  // Prefer the active decision round over retained history.
  if (state?.active_round) return state.active_round;
  // Read the bounded recent-round collection returned by the game API.
  const recent = state?.recent_rounds || [];
  // Return the newest-first completed round when one exists.
  return recent.length ? recent[0] : null;
}


// Adopt one state-bearing API response without assuming action-specific fields.
function adoptPayload(payload) {
  // Replace cached player state only when the response includes it.
  if (payload?.state) state = payload.state;
  // Replace cached rules only when the response includes authoritative values.
  if (payload?.rules) rules = payload.rules;
  // Read the active round after applying the response.
  const active = state?.active_round;
  // Clear an ambiguous deal id once the server proves an active round exists.
  if (active) {
    // Release the confirmed request id.
    pendingDealRequestId = null;
    // Release the confirmed wager binding.
    pendingDealContext = null;
  }
  // Build the only decision context that can still be retried safely.
  const activeContextPrefix = active?.phase === 'decision' ? `${active.round_id}:` : null;
  // Clear stale decision ids after settlement or a different round becomes active.
  if (!activeContextPrefix || !pendingDecisionContext?.startsWith(activeContextPrefix)) {
    // Release the no-longer-actionable decision id.
    pendingDecisionActionId = null;
    // Release its round-and-decision binding.
    pendingDecisionContext = null;
  }
}


// Translate one documented phase into concise player-facing language.
function phaseLabel(roundItem = currentRound()) {
  // Show in-flight feedback while controls are atomically locked.
  if (busy) return text('phases.working');
  // Show the idle phase when no round has been dealt.
  if (!roundItem) return text('phases.ready');
  // Show the Play-or-Fold prompt while the dealer hand remains hidden.
  if (roundItem.phase === 'decision') return text('phases.decision');
  // Show recovery-safe settlement feedback for prepared ledger work.
  if (roundItem.phase === 'ledger_pending') return text('phases.settling');
  // Show the terminal phase without exposing internal state names.
  return text('phases.settled');
}


// Translate one documented settlement outcome without displaying API enums.
function outcomeLabel(roundItem = currentRound()) {
  // Show ready guidance before the first round.
  if (!roundItem) return text('outcomes.ready');
  // Show decision guidance before a player commits Play or Fold.
  if (roundItem.phase === 'decision') return text('outcomes.choose');
  // Show localized settlement feedback while prepared ledger work recovers.
  if (roundItem.phase === 'ledger_pending') return text('outcomes.settling');
  // Map stable backend outcomes to owned resource keys.
  const keyByOutcome = {
    player_win: 'outcomes.playerWin', // Translate a stronger player hand.
    dealer_win: 'outcomes.dealerWin', // Translate a stronger qualifying dealer hand.
    dealer_not_qualified: 'outcomes.dealerNotQualified', // Translate the dealer qualification outcome.
    fold: 'outcomes.folded', // Translate the canonical Fold outcome.
    folded: 'outcomes.folded', // Translate a compatibility Fold spelling.
    push: 'outcomes.push', // Translate an additive returned-wager outcome.
    tie: 'outcomes.push', // Translate the canonical tied-hand outcome.
  };
  // Resolve known outcomes and use a localized complete state for future additive values.
  return text(keyByOutcome[roundItem.outcome] || 'outcomes.complete');
}


// Translate one documented three-card hand rank without exposing raw enum text.
function handRankLabel(rank) {
  // Read a rank name from the API object or compatibility string.
  const name = typeof rank === 'string' ? rank : rank?.name;
  // Normalize the one-pair compatibility spelling used by five-card evaluators.
  const normalized = name === 'one_pair' ? 'pair' : name;
  // Return the pending label until a public hand rank exists.
  if (!HAND_RANK_ORDER.includes(normalized)) return text('handRanks.pending');
  // Translate the canonical rank through paired game resources.
  return text(`handRanks.${normalized}`);
}


// Normalize one API card to rank and suit resource identifiers.
function cardParts(card) {
  // Read object-shaped cards without converting them to display text first.
  if (card && typeof card === 'object') {
    // Normalize the rank to the shared uppercase compact form.
    const rank = String(card.rank || '').toUpperCase();
    // Normalize the canonical suit name or compact suit code to a resource suffix.
    const suit = SUIT_KEYS[String(card.suit || '').toUpperCase()];
    // Return stable resource identifiers for accessible copy.
    return { rank, suit };
  }
  // Normalize compact cards such as AS or 10H.
  const compact = String(card || '').trim();
  // Read every character except the final suit code as the rank.
  const rank = compact.slice(0, -1).toUpperCase();
  // Resolve the final compact suit code to the canonical locale suffix.
  const suit = SUIT_KEYS[compact.slice(-1).toUpperCase()];
  // Return stable resource identifiers for accessible copy.
  return { rank, suit };
}


// Render one #96 card with a fully localized accessible name.
function localizedCard(card, { hidden = false, waiting = false } = {}) {
  // Render a reserved empty slot before cards are dealt.
  if (waiting) return `<span class="tcp-card-waiting" role="img" aria-label="${safe(text('cards.waiting'))}"></span>`;
  // Treat explicit hidden state and the compatibility marker as face-down cards.
  const isHidden = hidden || card === '??';
  // Render a shared face-down card without exposing its identity.
  if (isHidden) return renderCard('??', { hidden: true }).replace(/aria-label="[^"]*"/, `aria-label="${safe(text('cards.faceDown'))}"`);
  // Resolve locale resource identifiers for the visible card.
  const parts = cardParts(card);
  // Build the complete localized screen-reader label.
  const label = text('cards.label', { rank: text(`ranks.${parts.rank}`), suit: text(`suits.${parts.suit}`) });
  // Render the shared visible card and replace its locale-neutral accessible label.
  return renderCard(card).replace(/aria-label="[^"]*"/, `aria-label="${safe(label)}"`);
}


// Return exactly three stable card slots for one side of the table.
function cardRow(cards, { hidden = false, waiting = false } = {}) {
  // Normalize the API collection without mutating server state.
  const source = Array.isArray(cards) ? cards.slice(0, 3) : [];
  // Fill missing positions so the dominant stage never changes size between phases.
  while (source.length < 3) source.push(hidden ? '??' : null);
  // Render every slot through localized shared-card or waiting markup.
  return source.map(card => localizedCard(card, { hidden, waiting: waiting && !card })).join('');
}


// Render one labeled player or dealer hand on the central table.
function handHtml(side, roundItem) {
  // Determine whether this side is the dealer.
  const dealer = side === 'dealer';
  // Keep the dealer hand hidden throughout the decision phase.
  const hidden = dealer && roundItem?.phase === 'decision';
  // Read public cards from the exact backend round field.
  const cards = roundItem?.[`${side}_hand`] || [];
  // Read the corresponding public rank object.
  const rank = roundItem?.[`${side}_rank`];
  // Translate the hand-region label for visible and accessible use.
  const sideLabel = text(`hands.${side}`);
  // Hide dealer rank copy until settlement reveals the hand.
  const rankLabel = hidden ? text('handRanks.hidden') : handRankLabel(rank);
  // Return a stable semantic hand region with exactly three card slots.
  return `<section class="tcp-hand tcp-hand-${side}" role="group" aria-label="${safe(text('aria.hand', { side: sideLabel }))}"><header><h3>${safe(sideLabel)}</h3><span>${safe(rankLabel)}</span></header><div class="tcp-card-row">${cardRow(cards, { hidden, waiting: !roundItem })}</div></section>`;
}


// Read a numeric rule value from authoritative server paytables.
function ruleValue(tableName, rankName) {
  // Read the named paytable when it is a plain object.
  const table = rules?.[tableName] || {};
  // Normalize absent values to zero without inventing a payout.
  return Number(table?.[rankName] ?? 0);
}


// Render one compact localized paytable.
function paytableRows(order, tableName) {
  // Render canonical ranks in the table's documented strength order.
  return order.map(rank => `<tr><th scope="row">${safe(handRankLabel(rank))}</th><td>${safe(text('paytable.toOne', { value: formatNumber(ruleValue(tableName, rank)) }))}</td></tr>`).join('');
}


// Render the control rail for wager setup and the Play-or-Fold decision.
function controlsHtml(roundItem) {
  // Lock configuration while any round is active or a request is in flight.
  const configurationDisabled = Boolean(roundItem && roundItem.phase !== 'settled') || busy;
  // Enable Play and Fold only for the active decision phase.
  const decisionEnabled = roundItem?.phase === 'decision' && !busy;
  // Keep the total initial debit preview beside its wager controls.
  const initialTotal = ante + pairPlus;
  // Return stable controls with primary actions in one reserved region.
  return `<aside class="tcp-panel tcp-controls" aria-label="${safe(text('aria.controls'))}"><h2>${safe(text('controls.title'))}</h2><label for="tcp-ante">${safe(text('controls.ante'))}</label><input id="tcp-ante" data-testid="three-card-poker-ante" type="number" min="0.01" max="100000" step="0.01" value="${safe(ante)}"${configurationDisabled ? ' disabled' : ''}><label for="tcp-pair-plus">${safe(text('controls.pairPlus'))}</label><input id="tcp-pair-plus" data-testid="three-card-poker-pair-plus" type="number" min="0" max="100000" step="0.01" value="${safe(pairPlus)}"${configurationDisabled ? ' disabled' : ''}><p class="tcp-total">${safe(text('controls.initialTotal'))}: <strong>${safe(tokenAmount(initialTotal))}</strong></p><div class="tcp-action-slot"><button type="button" class="tcp-primary" data-action="deal"${configurationDisabled ? ' disabled' : ''}>${safe(roundItem?.phase === 'settled' ? text('controls.dealNext') : text('controls.deal'))}</button><div class="tcp-decision-actions"><button type="button" class="tcp-primary" data-action="play"${decisionEnabled ? '' : ' disabled'}>${safe(text('controls.play'))}</button><button type="button" data-action="fold"${decisionEnabled ? '' : ' disabled'}>${safe(text('controls.fold'))}</button></div></div><p class="tcp-help">${safe(roundItem?.phase === 'decision' ? text('controls.decisionHelp') : text('controls.readyHelp'))}</p></aside>`;
}


// Render one localized numeric settlement metric.
function metricHtml(label, value) {
  // Return an aligned label and value without currency symbols.
  return `<div class="tcp-metric"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`;
}


// Render the dominant three-card table for ready, decision, and settled states.
function stageHtml(roundItem) {
  // Read the committed wager fields through numeric fallbacks.
  const anteValue = Number(roundItem?.ante || 0);
  // Read the optional Pair Plus wager through a numeric fallback.
  const pairPlusValue = Number(roundItem?.pair_plus || 0);
  // Read the optional Play wager through a numeric fallback.
  const playValue = Number(roundItem?.play_wager || 0);
  // Read the settled payout through a numeric fallback.
  const payoutValue = Number(roundItem?.total_payout || 0);
  // Read the settled net value only when the API has published it.
  const netValue = roundItem?.net === null || roundItem?.net === undefined ? text('summary.pending') : tokenAmount(roundItem.net);
  // Resolve dealer qualification only after the dealer hand is revealed.
  const qualification = roundItem?.phase !== 'settled' ? text('dealer.pending') : roundItem.dealer_qualifies ? text('dealer.qualifies') : text('dealer.notQualified');
  // Describe the public round state without exposing an internal round identifier.
  const stageContext = !roundItem ? text('stage.ready') : roundItem.phase === 'decision' ? text('stage.inProgress') : text('stage.completed');
  // Return the stable dominant stage with one live localized phase region.
  return `<main class="tcp-panel tcp-stage" aria-label="${safe(text('aria.stage'))}"><div class="tcp-stage-head"><div><p>${safe(stageContext)}</p><h2>${safe(outcomeLabel(roundItem))}</h2></div><span class="tcp-phase" role="status" aria-live="polite">${safe(phaseLabel(roundItem))}</span></div><div class="tcp-table" data-testid="three-card-poker-table">${handHtml('dealer', roundItem)}<div class="tcp-table-mark"><span>${safe(text('stage.tableMark'))}</span><strong>${safe(qualification)}</strong></div>${handHtml('player', roundItem)}</div><section class="tcp-summary" aria-label="${safe(text('aria.summary'))}">${metricHtml(text('summary.ante'), tokenAmount(anteValue))}${metricHtml(text('summary.pairPlus'), tokenAmount(pairPlusValue))}${metricHtml(text('summary.play'), tokenAmount(playValue))}${metricHtml(text('summary.payout'), tokenAmount(payoutValue))}${metricHtml(text('summary.net'), netValue)}</section></main>`;
}


// Return completed rounds newest-first for a bounded data-rail history.
function recentRounds() {
  // Copy retained rounds so UI ordering never mutates server state.
  const rounds = [...(state?.recent_rounds || [])];
  // Keep the backend's newest-first ordering and bound the rail length.
  return rounds.slice(0, 4);
}


// Render the localized data rail with paytables and bounded history.
function dataHtml() {
  // Render recent result rows without raw outcome or phase identifiers.
  const history = recentRounds().map(roundItem => `<article class="tcp-history-row" role="listitem"><div><strong>${safe(outcomeLabel(roundItem))}</strong><span>${safe(text('history.completed'))}</span></div><span>${safe(tokenAmount(roundItem.total_payout || 0))}</span></article>`).join('');
  // Return two compact tables and history without a nested primary scroll area.
  return `<aside class="tcp-panel tcp-data" aria-label="${safe(text('aria.data'))}"><section><h2>${safe(text('paytable.pairPlus'))}</h2><table><thead><tr><th>${safe(text('paytable.hand'))}</th><th>${safe(text('paytable.return'))}</th></tr></thead><tbody>${paytableRows(PAIR_PLUS_ORDER, 'pair_plus')}</tbody></table></section><section><h2>${safe(text('paytable.anteBonus'))}</h2><table><thead><tr><th>${safe(text('paytable.hand'))}</th><th>${safe(text('paytable.return'))}</th></tr></thead><tbody>${paytableRows(ANTE_BONUS_ORDER, 'ante_bonus')}</tbody></table></section><section><h2>${safe(text('history.title'))}</h2><div class="tcp-history-list" role="list" aria-label="${safe(text('aria.history'))}">${history || `<p>${safe(text('history.empty'))}</p>`}</div></section></aside>`;
}


// Return game-owned styles so no forbidden shared stylesheet needs editing.
function stylesHtml() {
  // Keep the card stage dominant on desktop, stack controls first on narrow screens, and disable decorative motion when requested.
  return `<style>
    /* Keep all issue #93 presentation scoped to the lazy game module. */
    .tcp-shell{display:grid;gap:16px;min-width:0}.tcp-header{display:flex;align-items:end;justify-content:space-between;gap:14px}.tcp-header h1{margin:0}.tcp-header p{margin:0 0 4px;color:var(--gold,#f6d47a)}.tcp-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(520px,2.35fr) minmax(230px,.82fr);gap:16px;align-items:start;min-width:0}.tcp-panel{min-width:0;padding:16px;border:1px solid var(--gold);border-radius:16px;background:var(--panel-strong)}.tcp-controls{display:grid;gap:10px}.tcp-controls input,.tcp-controls button{min-height:44px}.tcp-total,.tcp-help{margin:0;color:var(--muted,#b8c8c1)}.tcp-action-slot{display:grid;gap:9px}.tcp-decision-actions{display:grid;grid-template-columns:1fr 1fr;gap:9px}.tcp-primary{color:#fff;background:#a51f2d}.tcp-stage{display:grid;gap:14px;background:radial-gradient(circle at 50% 44%,rgba(35,17,61,.58),rgba(20,10,34,.96) 70%)}.tcp-stage-head{display:flex;align-items:start;justify-content:space-between;gap:12px}.tcp-stage-head p,.tcp-stage-head h2{margin:0}.tcp-phase{padding:7px 11px;border:1px solid var(--gold);border-radius:999px;color:var(--gold)}.tcp-table{display:grid;grid-template-rows:auto auto auto;gap:14px;place-items:center;min-height:510px;padding:20px;border:2px solid var(--gold);border-radius:18px;background:radial-gradient(circle,rgba(35,17,61,.38),rgba(20,10,34,.62))}.tcp-hand{display:grid;gap:8px;justify-items:center;width:100%}.tcp-hand header{display:flex;justify-content:space-between;gap:12px;width:min(100%,360px)}.tcp-hand h3{margin:0}.tcp-card-row{display:flex;flex-wrap:nowrap;justify-content:center;gap:clamp(7px,1.4vw,14px);min-height:92px}.tcp-card-waiting{display:inline-block;flex:0 1 clamp(3.25rem,10vw,6.5rem);min-width:3.25rem;aspect-ratio:5/7;border:2px dashed rgba(255,255,255,.25);border-radius:.65rem}.tcp-table-mark{display:grid;gap:4px;text-align:center;color:var(--gold)}.tcp-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.tcp-metric{min-width:0;padding:9px;border-radius:10px;background:rgba(0,0,0,.22)}.tcp-metric span{display:block;color:var(--muted,#b8c8c1);font-size:.78rem}.tcp-metric strong{display:block;overflow-wrap:anywhere}.tcp-data{display:grid;gap:16px}.tcp-data h2{margin:0 0 8px;font-size:1rem}.tcp-data table{width:100%;border-collapse:collapse}.tcp-data th,.tcp-data td{padding:5px 3px;border-bottom:1px solid rgba(255,255,255,.1);text-align:left}.tcp-data td{text-align:right}.tcp-history-list{display:grid;gap:7px}.tcp-history-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;padding:8px;border-radius:9px;background:rgba(0,0,0,.18)}.tcp-history-row span{display:block;color:var(--muted,#b8c8c1);font-size:.78rem}.tcp-shell button:focus-visible,.tcp-shell input:focus-visible{outline:3px solid var(--gold);outline-offset:2px}@media(max-width:1100px){.tcp-layout{grid-template-columns:1fr}.tcp-controls{order:1}.tcp-stage{order:2}.tcp-data{order:3}.tcp-table{min-height:430px}.tcp-summary{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:520px){.tcp-header{align-items:start;flex-direction:column}.tcp-panel{padding:12px}.tcp-stage-head{flex-direction:column}.tcp-table{min-height:390px;padding:12px}.tcp-summary{grid-template-columns:1fr 1fr}.tcp-card-row{gap:5px}.tcp-card-row .playing-card{min-width:2.85rem}.tcp-decision-actions{grid-template-columns:1fr}}@media(prefers-reduced-motion:reduce){.tcp-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important;transform:none!important}}
    /* End the game-owned style block without allocating runtime timers. */
  </style>`;
}


// Render the complete localized three-zone game surface from cached state.
function render() {
  // Stop when async work completes after route teardown.
  if (!root) return;
  // Read the active or newest settled round once for a consistent render.
  const roundItem = currentRound();
  // Replace the route outlet atomically so controls, stage, and data cannot drift.
  root.innerHTML = `${stylesHtml()}<section class="tcp-shell" data-testid="three-card-poker" aria-label="${safe(text('aria.game'))}" aria-busy="${busy}"><header class="tcp-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span>${safe(text('stage.fakeMoney'))}</span></header><div class="tcp-layout">${controlsHtml(roundItem)}${stageHtml(roundItem)}${dataHtml()}</div></section>`;
  // Attach phase-appropriate handlers to the newly rendered controls.
  bindEvents();
}


// Translate API failures without leaking backend English into the Russian UI.
function errorText(error) {
  // Normalize the standard API error code for finite resource mapping.
  const code = String(error?.code || '').toUpperCase();
  // Explain insufficient play tokens through paired game resources.
  if (code === 'INSUFFICIENT_FUNDS') return text('errors.insufficientFunds');
  // Explain retry conflicts through paired game resources.
  if (code.includes('CONFLICT') || code.includes('IDEMPOT')) return text('errors.retryConflict');
  // Use a localized safe fallback for every other server diagnostic.
  return text('errors.generic');
}


// Execute one atomic browser action with stable disabled-state cleanup.
async function runAction(action) {
  // Ignore overlapping button events while another request is in flight.
  if (busy) return;
  // Capture the current mount so late completions cannot affect another route.
  const generation = mountGeneration;
  // Disable controls before beginning the action.
  busy = true;
  // Render stable disabled controls in their reserved positions.
  render();
  // Start protected action handling so failures become localized shell feedback.
  try {
    // Execute the supplied public API action.
    await action();
  // Translate API failures without inserting raw backend copy.
  } catch (error) {
    // Suppress a late failure after navigation so another route never receives this game's toast.
    if (generation !== mountGeneration || !root) return;
    // Show one localized player-facing diagnostic.
    toast(errorText(error));
  // Always restore controls on the still-current mount.
  } finally {
    // Stop when navigation or reload invalidated this action's mount.
    if (generation !== mountGeneration || !root) return;
    // Release the atomic action lock.
    busy = false;
    // Rerender the latest successful or preserved state.
    render();
  }
}


// Capture wager inputs before a busy render replaces their DOM nodes.
function captureWagers() {
  // Read and normalize the required Ante wager.
  ante = normalizedWager(root?.querySelector('#tcp-ante')?.value ?? ante, 0.01);
  // Read and normalize the optional Pair Plus wager.
  pairPlus = normalizedWager(root?.querySelector('#tcp-pair-plus')?.value ?? pairPlus, 0);
}


// Start one retry-safe Ante and optional Pair Plus wager.
async function deal() {
  // Capture this route generation so a late response cannot revive unmounted state.
  const generation = mountGeneration;
  // Bind retries to the exact normalized wager payload.
  const context = `${ante}:${pairPlus}`;
  // Replace a pending id when the user intentionally changes either wager.
  if (pendingDealContext !== context) pendingDealRequestId = null;
  // Store the current wager context before issuing the request.
  pendingDealContext = context;
  // Retain one request id across failed retries until state is confirmed.
  pendingDealRequestId = pendingDealRequestId || nextActionId('tcp-deal');
  // Post only the documented additive action fields.
  const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ request_id: pendingDealRequestId, ante, pair_plus: pairPlus }));
  // Ignore a response that completed after navigation or a later remount.
  if (generation !== mountGeneration || !root) return;
  // Adopt reload-safe state and authoritative rules from the response.
  adoptPayload(payload);
  // Clear the request id only after the backend confirms the response.
  pendingDealRequestId = null;
  // Clear the wager binding after successful confirmation.
  pendingDealContext = null;
  // Refresh the shared authenticated wallet after the initial ledger debit.
  await refreshBalance();
}


// Resolve the active round through one retry-safe Play or Fold decision.
async function decide(decision) {
  // Capture this route generation so a late settlement cannot revive unmounted state.
  const generation = mountGeneration;
  // Read the active decision round before constructing its public endpoint.
  const roundItem = state?.active_round;
  // Stop stale clicks after settlement or state recovery.
  if (!roundItem || roundItem.phase !== 'decision') return;
  // Bind retries to this exact round and selected decision.
  const context = `${roundItem.round_id}:${decision}`;
  // Replace a pending id only when the user intentionally changes context.
  if (pendingDecisionContext !== context) pendingDecisionActionId = null;
  // Store the current context before issuing the request.
  pendingDecisionContext = context;
  // Retain one action id across failed retries independently of deal retries.
  pendingDecisionActionId = pendingDecisionActionId || nextActionId('tcp-decision');
  // Post only the documented decision and retry-safe action id.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionActionId, decision }));
  // Ignore a response that completed after navigation or a later remount.
  if (generation !== mountGeneration || !root) return;
  // Adopt the settled reload-safe state returned by the backend.
  adoptPayload(payload);
  // Clear the decision id after the backend confirms settlement or replay.
  pendingDecisionActionId = null;
  // Clear the decision context after successful confirmation.
  pendingDecisionContext = null;
  // Refresh the shared wallet after Play debit, Fold, and settlement credits.
  await refreshBalance();
}


// Attach semantic control handlers after every atomic render.
function bindEvents() {
  // Read the Ante input created by the latest render.
  const anteInput = root?.querySelector('#tcp-ante');
  // Preserve Ante edits in cached pre-deal configuration.
  if (anteInput) anteInput.onchange = () => { captureWagers(); render(); };
  // Read the Pair Plus input created by the latest render.
  const pairPlusInput = root?.querySelector('#tcp-pair-plus');
  // Preserve optional Pair Plus edits in cached pre-deal configuration.
  if (pairPlusInput) pairPlusInput.onchange = () => { captureWagers(); render(); };
  // Read the primary Deal control created by the latest render.
  const dealButton = root?.querySelector('[data-action="deal"]');
  // Capture current inputs and start one retry-safe deal when enabled.
  if (dealButton) dealButton.onclick = () => { captureWagers(); runAction(deal); };
  // Read the Play decision control created by the latest render.
  const playButton = root?.querySelector('[data-action="play"]');
  // Commit the matching Play wager through the public decision endpoint.
  if (playButton) playButton.onclick = () => runAction(() => decide('play'));
  // Read the Fold decision control created by the latest render.
  const foldButton = root?.querySelector('[data-action="fold"]');
  // Resolve Fold through the same public decision endpoint.
  if (foldButton) foldButton.onclick = () => runAction(() => decide('fold'));
}


// Export the catalog-owned lazy game module contract expected by issue #81.
export const ThreeCardPokerGame = {
  // Expose the stable module id used by catalog navigation.
  id: 'three_card_poker',
  // Leave presentation labels to the owned descriptor and locale resources.
  label: '',
  // Load locale and authenticated-player state before rendering visible text.
  async mount(node) {
    // Advance the generation so earlier async completions become stale.
    const generation = ++mountGeneration;
    // Store the route outlet for subsequent deterministic renders.
    root = node;
    // Reset the visual action lock for a fresh mount.
    busy = false;
    // Install the shared responsive card presentation once.
    ensureSharedCardStyles();
    // Load active and fallback game-owned resources before rendering.
    await loadI18nDomain(DOMAIN);
    // Stop if navigation invalidated this mount during resource loading.
    if (generation !== mountGeneration || root !== node) return;
    // Release a stale subscription if a consumer remounts without unmounting.
    if (unsubscribeLocale) unsubscribeLocale();
    // Subscribe to locale changes without remounting or losing round state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read the authenticated player's reload-safe state.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Stop if navigation invalidated this mount during state loading.
    if (generation !== mountGeneration || root !== node) return;
    // Cache state and authoritative paytables for the first render.
    adoptPayload(payload);
    // Restore wager controls from an active decision round after reload.
    ante = state?.active_round?.ante ?? ante;
    // Restore optional Pair Plus configuration from the active round.
    pairPlus = state?.active_round?.pair_plus ?? pairPlus;
    // Render the complete issue #93 surface.
    render();
    // Align the persistent shell wallet with recovered ledger state.
    await refreshBalance();
  },
  // Release every game-owned lifecycle resource when the shell changes route.
  unmount() {
    // Advance the generation before clearing state so late promises become inert.
    mountGeneration += 1;
    // Unsubscribe the locale callback when it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated unmounts remain safe.
    unsubscribeLocale = null;
    // Clear cached player state so another session cannot reuse it.
    state = null;
    // Clear authoritative rule state for the inactive route.
    rules = {};
    // Release the visual action lock for a future mount.
    busy = false;
    // Discard unresolved deal retry state because remount recovery reads the server first.
    pendingDealRequestId = null;
    // Discard the deal fingerprint together with its request id.
    pendingDealContext = null;
    // Discard unresolved decision retry state because remount recovery reads the server first.
    pendingDecisionActionId = null;
    // Discard the decision fingerprint together with its action id.
    pendingDecisionContext = null;
    // Clear the mount node so late work cannot render into another route.
    root = null;
    // No timers remain because this module creates none.
  },
};
