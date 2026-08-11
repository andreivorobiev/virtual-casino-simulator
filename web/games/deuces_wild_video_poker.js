// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Implement the isolated issue #92 Deuces Wild Video Poker browser module.

// Import session-aware API helpers so the authenticated router remains authoritative.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback and escaping without creating game-owned global resources.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared accessible card renderer instead of duplicating card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/deuces_wild_video_poker';
// Store the additive frozen-v1 API root once for every public game action.
const API_ROOT = '/api/v1/games/deuces-wild-video-poker';
// Store the smallest ledger-compatible play-token wager accepted by this game.
const MIN_WAGER = 0.01;
// Store the game-owned upper wager boundary shared with the additive contract.
const MAX_WAGER = 100000;
// Preserve the full-pay Deuces Wild display order independently of object insertion behavior.
const PAYTABLE_ORDER = ['natural_royal_flush', 'four_deuces', 'wild_royal_flush', 'five_of_a_kind', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind'];
// Provide the documented full-pay return schedule until the authoritative state payload arrives.
const FULL_PAY_RETURNS = Object.freeze({ natural_royal_flush: 800, four_deuces: 200, wild_royal_flush: 25, five_of_a_kind: 15, straight_flush: 9, four_of_a_kind: 5, full_house: 3, flush: 2, straight: 2, three_of_a_kind: 1 });
// Recognize only player-facing paytable outcomes when normalizing result payloads.
const PAYTABLE_OUTCOMES = new Set(PAYTABLE_ORDER);
// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest player-scoped state payload for reload-safe rendering.
let state = null;
// Store the server paytable while retaining a complete full-pay initial rail.
let paytable = { ...FULL_PAY_RETURNS };
// Store the configured play-token wager for the next deal.
let wager = 1;
// Store the in-flight action flag so atomic controls cannot overlap.
let busy = false;
// Store the locale cleanup callback so unmount releases the subscription.
let unsubscribeLocale = null;
// Store a fallback action-id counter for browsers without randomUUID support.
let actionCounter = 0;
// Retain an unresolved deal action id so a lost response cannot duplicate the wager.
let pendingDealActionId = null;
// Retain the wager paired with an unresolved deal action id so retries cannot conflict.
let pendingDealWager = null;
// Retain the last settled deal's wager so one click can repeat an identical hand.
let lastBet = null;
// Retain unresolved hold action ids by round and desired selection.
const pendingHoldActionIds = new Map();
// Retain unresolved draw action ids by round so payout retries remain exactly-once.
const pendingDrawActionIds = new Map();


// Resolve one owned localized string without a player-visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every player-visible label to the paired EN/RU resource domain.
  return t(key, params, DOMAIN);
}


// Format one fake-money amount without a currency symbol or replacement glyph.
function tokenAmount(value) {
  // Normalize missing values before locale-aware fixed-precision formatting.
  const amount = Number(value || 0);
  // Append localized fake-token terminology to the formatted amount.
  return `${formatNumber(amount, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${text('units.playTokens')}`;
}


// Create one bounded URL-safe client action id for retry-safe public actions.
function nextActionId(kind) {
  // Use the browser cryptographic UUID source when it is available.
  if (globalThis.crypto?.randomUUID) return `dwvp-${kind}-${globalThis.crypto.randomUUID()}`;
  // Increment the fallback counter to disambiguate actions created in one millisecond.
  actionCounter += 1;
  // Combine a timestamp and counter without claiming cryptographic randomness.
  return `dwvp-${kind}-${Date.now().toString(36)}-${actionCounter.toString(36)}`;
}


// Render a shared card while replacing its accessible name with owned locale copy.
function localizedCard(card, options = {}) {
  // Normalize the compact rank from every character except the final suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Select the wild-card label only for a deuce.
  const labelKey = rank === '2' ? 'cards.cardLabelWild' : 'cards.cardLabel';
  // Build the complete accessible label from localized rank and suit values.
  const label = text(labelKey, { rank: text(`ranks.${rank}`), suit: text(`suits.${suit}`) });
  // Reuse the shared semantic renderer and replace only its locale-neutral label.
  return renderCard(card, options).replace(/aria-label="[^"]*"/, `aria-label="${safe(label)}"`);
}


// Return the active round or the newest settled round for one stable stage.
function currentRound() {
  // Prefer the actionable hand before the bounded recent-round collection.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}


// Normalize one optional nested result into the game surface's stable view model.
function roundResult(roundItem) {
  // Prefer the explicit single-hand result object when the backend supplies it.
  if (roundItem?.result && typeof roundItem.result === 'object') return roundItem.result;
  // Normalize the engine's compact top-level result key when no nested object is present.
  if (typeof roundItem?.result === 'string') return { cards: roundItem.final_hand || [], outcome: roundItem.result, multiplier: roundItem.multiplier, payout: roundItem.payout };
  // Accept a one-item results collection for compatibility with shared poker adapters.
  if (Array.isArray(roundItem?.results) && roundItem.results.length) return roundItem.results[0];
  // Build a compatible result view from top-level settled-round fields.
  return { cards: roundItem?.final_hand || [], outcome: roundItem?.hand_outcome || roundItem?.outcome, multiplier: roundItem?.multiplier, payout: roundItem?.total_payout ?? roundItem?.payout };
}


// Resolve the game-specific paytable outcome without exposing internal phase values.
function resultOutcome(roundItem) {
  // Read the normalized result's machine-readable outcome key.
  const outcome = roundResult(roundItem).outcome;
  // Return only a known localized paytable key or the localized losing key.
  return PAYTABLE_OUTCOMES.has(outcome) ? outcome : 'no_win';
}


// Resolve the final or initial cards appropriate to the current round phase.
function displayedCards(roundItem) {
  // Read the normalized settled result once for compatibility handling.
  const result = roundResult(roundItem);
  // Prefer final cards only after settlement has completed.
  if (roundItem?.phase === 'settled' && Array.isArray(result.cards) && result.cards.length) return result.cards;
  // Return the reload-safe source hand while hold choices remain actionable.
  return roundItem?.initial_hand || roundItem?.cards || [];
}


// Resolve the committed round wager across compatible response field names.
function roundWager(roundItem) {
  // Prefer the aggregate field while accepting the single-hand wager field.
  return Number(roundItem?.total_wager ?? roundItem?.wager ?? roundItem?.wager_amount ?? 0);
}


// Resolve the settled payout across compatible response field names.
function roundPayout(roundItem) {
  // Prefer the normalized result payout before top-level settlement aliases.
  return Number(roundResult(roundItem).payout ?? roundItem?.total_payout ?? roundItem?.payout ?? 0);
}


// Resolve the settled net movement without relying on a server alias.
function roundNet(roundItem) {
  // Prefer the server audit value when it is present.
  if (roundItem?.net !== undefined && roundItem?.net !== null) return Number(roundItem.net);
  // Derive net returned credits from payout minus the committed wager.
  return roundPayout(roundItem) - roundWager(roundItem);
}


// Translate one round phase into concise player-facing status copy.
function phaseLabel(roundItem) {
  // Show the idle phase before any hand has been dealt.
  if (!roundItem) return text('phases.ready');
  // Show the hold decision while source cards remain selectable.
  if (roundItem.phase === 'hold') return text('phases.chooseHolds');
  // Classify a positive net result as a localized win phase.
  if (roundNet(roundItem) > 0) return text('phases.win');
  // Classify a zero net result as a localized returned-wager phase.
  if (roundNet(roundItem) === 0) return text('phases.push');
  // Classify every remaining settled result as a localized completed loss.
  return text('phases.loss');
}


// Render one selectable source-card position through the shared card renderer.
function handCard(card, position, held, interactive, disabled) {
  // Render settled cards as non-interactive content without misleading hold actions.
  if (!interactive) return `<div class="dwvp-card-button dwvp-final-card">${localizedCard(card)}${String(card).startsWith('2') ? `<span class="dwvp-wild-label">${safe(text('cards.wild'))}</span>` : ''}</div>`;
  // Resolve the action label from the current selected state.
  const actionLabel = held ? text('cards.release', { position: position + 1 }) : text('cards.hold', { position: position + 1 });
  // Render a semantic pressed-state button whose selection is visible beyond color.
  return `<button type="button" class="dwvp-card-button${held ? ' is-held' : ''}" data-hold-position="${position}" aria-pressed="${held}" aria-label="${safe(actionLabel)}"${disabled ? ' disabled' : ''}>${localizedCard(card, { selected: held })}${held ? `<span class="dwvp-held-label">${safe(text('cards.held'))}</span>` : ''}${String(card).startsWith('2') ? `<span class="dwvp-wild-label">${safe(text('cards.wild'))}</span>` : ''}</button>`;
}


// Render the dominant five-card source or final hand.
function handHtml(roundItem) {
  // Build a set so persisted hold positions can be checked without order assumptions.
  const held = new Set(roundItem.holds || []);
  // Track whether the displayed source hand still accepts hold changes.
  const interactive = roundItem.phase === 'hold';
  // Disable hold actions while an atomic request is in progress.
  const disabled = busy;
  // Render every current card with localized accessible action text.
  const cards = displayedCards(roundItem).map((card, position) => handCard(card, position, held.has(position), interactive, disabled)).join('');
  // Choose a localized region name appropriate to source or final cards.
  const label = roundItem.phase === 'settled' ? text('stage.finalHand') : text('stage.sourceHand');
  // Return the five-card region with a stable focused-test hook.
  return `<section class="dwvp-hand" aria-label="${safe(label)}" data-testid="dwvp-hand"><div class="dwvp-card-row">${cards}</div></section>`;
}


// Render the settlement summary from the reload-safe round result.
function summaryHtml(roundItem) {
  // Omit settlement details while the player is still choosing holds.
  if (roundItem.phase !== 'settled') return '';
  // Resolve the localized paytable outcome for the completed hand.
  const outcome = text(`outcomes.${resultOutcome(roundItem)}`);
  // Resolve the credited multiplier from result state or the authoritative paytable.
  const multiplier = Number(roundResult(roundItem).multiplier ?? paytable[resultOutcome(roundItem)] ?? 0);
  // Return aligned outcome, wager, payout, net, and multiplier facts.
  return `<section class="dwvp-summary" data-testid="dwvp-summary" aria-label="${safe(text('summary.title'))}"><span>${safe(text('summary.outcome'))}: <strong>${safe(outcome)}</strong></span><span>${safe(text('summary.wager'))}: <strong>${safe(tokenAmount(roundWager(roundItem)))}</strong></span><span>${safe(text('summary.payout'))}: <strong>${safe(tokenAmount(roundPayout(roundItem)))}</strong></span><span>${safe(text('summary.net'))}: <strong>${safe(tokenAmount(roundNet(roundItem)))}</strong></span><span>${safe(text('summary.multiplier'))}: <strong>${safe(text('paytable.multiplier', { value: multiplier }))}</strong></span></section>`;
}


// Render the dominant game stage for idle, hold, and settled states.
function stageHtml(roundItem) {
  // Render localized guidance before the first wager.
  if (!roundItem) return `<section class="dwvp-empty" data-testid="dwvp-empty"><h2>${safe(text('stage.readyTitle'))}</h2><p>${safe(text('stage.readyBody'))}</p></section>`;
  // Render the current five-card hand and optional settlement summary.
  return `${handHtml(roundItem)}${summaryHtml(roundItem)}<p class="dwvp-stage-help">${safe(roundItem.phase === 'hold' ? text('stage.holdPrompt') : text('stage.settledPrompt'))}</p>`;
}


// Render wager and atomic public-action controls.
function controlsHtml(roundItem) {
  // Treat an unresolved deal as a fixed-parameter retry until the server confirms it.
  const wagerDisabled = Boolean(state?.active_round) || busy || Boolean(pendingDealActionId);
  // Enable a deal only when no hand is active and no request is currently running.
  const dealDisabled = Boolean(state?.active_round) || busy;
  // Enable draw only while the active hand awaits hold decisions.
  const drawDisabled = !roundItem || roundItem.phase !== 'hold' || busy;
  // Enable the one-click repeat only outside a mid-hand and after a prior settled wager exists.
  const repeatDisabled = wagerDisabled || !lastBet;
  // Return the complete stable control rail with fake-money language.
  return `<aside class="dwvp-panel dwvp-controls" aria-label="${safe(text('controls.title'))}"><h2>${safe(text('controls.title'))}</h2><label for="dwvp-wager">${safe(text('controls.wager'))}</label><input id="dwvp-wager" type="number" min="${MIN_WAGER}" max="${MAX_WAGER}" step="0.01" value="${safe(wager)}"${wagerDisabled ? ' disabled' : ''}><p class="dwvp-total">${safe(text('controls.totalWager'))}: <strong>${safe(tokenAmount(wager))}</strong></p><button type="button" class="dwvp-primary" data-action="deal"${dealDisabled ? ' disabled' : ''}>${safe(text('controls.deal'))}</button><button type="button" class="dwvp-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(text('controls.repeat'))}</button><button type="button" data-action="draw"${drawDisabled ? ' disabled' : ''}>${safe(text('controls.draw'))}</button><p class="dwvp-help">${safe(text('controls.holdHelp'))}</p></aside>`;
}


// Render the full-pay Deuces Wild table in the data rail.
function paytableHtml() {
  // Render every required outcome in canonical strength order.
  const rows = PAYTABLE_ORDER.map(outcome => `<tr><th scope="row">${safe(text(`outcomes.${outcome}`))}</th><td>${safe(text('paytable.multiplier', { value: paytable[outcome] ?? FULL_PAY_RETURNS[outcome] }))}</td></tr>`).join('');
  // Return one keyboard-readable table without a nested scroll container.
  return `<aside class="dwvp-panel dwvp-data" aria-label="${safe(text('paytable.title'))}"><h2>${safe(text('paytable.title'))}</h2><table><thead><tr><th>${safe(text('paytable.result'))}</th><th>${safe(text('paytable.return'))}</th></tr></thead><tbody>${rows}</tbody></table><p>${safe(text('paytable.note'))}</p></aside>`;
}


// Return all game-owned presentation inside the lazy module.
function stylesHtml() {
  // Keep the card stage dominant at desktop and stack controls first when narrow.
  return `<style>
    /* Load the shared #96 responsive card presentation for renderCard output. */
    @import url('/core/cards.css');
    /* Scope the issue #92 three-zone layout and component presentation to this game. */
    .dwvp-shell{display:grid;gap:18px;min-width:0}.dwvp-header{display:flex;align-items:end;justify-content:space-between;gap:12px}.dwvp-header h1{margin:0}.dwvp-phase{padding:7px 12px;border:1px solid var(--gold);border-radius:999px}.dwvp-layout{display:grid;grid-template-columns:minmax(210px,.72fr) minmax(520px,2.4fr) minmax(230px,.8fr);gap:16px;align-items:start}.dwvp-panel,.dwvp-stage{border:1px solid var(--border);border-radius:16px;background:rgba(20,10,34,.82);padding:16px}.dwvp-controls{display:grid;gap:12px}.dwvp-shell button,.dwvp-shell input{min-height:42px}.dwvp-primary{background:#a51f2d;color:#fff}.dwvp-help,.dwvp-total,.dwvp-data p,.dwvp-stage-help{color:var(--muted,#b8c8c1)}.dwvp-stage{display:grid;gap:16px;min-width:0}.dwvp-card-row{display:flex;flex-wrap:wrap;justify-content:center;gap:10px}.dwvp-card-button{position:relative;min-width:72px;min-height:104px;padding:3px;border:2px solid transparent;background:transparent}.dwvp-card-button.is-held{border-color:var(--gold);border-radius:10px}.dwvp-held-label,.dwvp-wild-label{position:absolute;padding:2px 6px;border-radius:999px;background:var(--felt);color:var(--metal-gold);font-size:10px}.dwvp-held-label{inset:auto 3px 3px}.dwvp-wild-label{inset:3px 3px auto auto}.dwvp-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.dwvp-summary span{padding:10px;border-radius:10px;background:rgba(255,255,255,.04)}.dwvp-data table{width:100%;border-collapse:collapse}.dwvp-data th,.dwvp-data td{padding:7px 4px;border-bottom:1px solid rgba(255,255,255,.1);text-align:left}.dwvp-empty{min-height:340px;display:grid;place-content:center;text-align:center}.dwvp-stage-help{text-align:center}.dwvp-card-button:focus-visible,.dwvp-shell button:focus-visible,.dwvp-shell input:focus-visible{outline:3px solid var(--gold);outline-offset:2px}@media(max-width:1100px){.dwvp-layout{grid-template-columns:1fr}.dwvp-controls{order:1}.dwvp-stage{order:2}.dwvp-data{order:3}}@media(max-width:520px){.dwvp-header{align-items:start;flex-direction:column}.dwvp-panel,.dwvp-stage{padding:12px}.dwvp-summary{grid-template-columns:1fr}.dwvp-card-button{min-width:52px;min-height:78px}.dwvp-card-row{gap:5px}}@media(prefers-reduced-motion:reduce){.dwvp-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}.dwvp-repeat{min-height:44px;background:transparent;color:var(--gold);border:1px solid var(--gold)}.dwvp-repeat:disabled{opacity:.5}
    /* End the game-owned style block without timers or global listeners. */
  </style>`;
}


// Render the complete localized three-zone game surface from cached state.
function render() {
  // Stop when an asynchronous completion arrives after unmount.
  if (!root) return;
  // Read the active or newest completed round once per render.
  const roundItem = currentRound();
  // Name the nested game region without introducing a second main landmark.
  const stageLabel = roundItem?.phase === 'settled' ? text('stage.finalHand') : roundItem ? text('stage.sourceHand') : text('stage.readyTitle');
  // Replace the route outlet atomically so stage and controls cannot drift.
  root.innerHTML = `${stylesHtml()}<section class="dwvp-shell" data-testid="deuces-wild-video-poker"><header class="dwvp-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="dwvp-phase" role="status">${safe(phaseLabel(roundItem))}</span></header><div class="dwvp-layout">${controlsHtml(roundItem)}<section class="dwvp-stage" aria-label="${safe(stageLabel)}">${stageHtml(roundItem)}</section>${paytableHtml()}</div></section>`;
  // Attach handlers to the newly rendered semantic controls.
  bindEvents();
}


// Adopt one public API payload without retaining caller-controlled identity data.
function adoptPayload(payload) {
  // Replace cached game state only when the response provides it.
  if (payload?.state) state = payload.state;
  // Merge the server's authoritative paytable over the documented full-pay defaults.
  if (payload?.paytable) paytable = { ...FULL_PAY_RETURNS, ...payload.paytable };
}


// Execute one atomic browser action with generic localized error feedback.
async function runAction(action) {
  // Ignore overlapping button events while an API request is in flight.
  if (busy) return;
  // Disable controls before beginning the public action.
  busy = true;
  // Render the stable disabled control state.
  render();
  // Start protected handling so network and API errors never leak hard-coded copy.
  try {
    // Execute the supplied public game action.
    await action();
  // Convert every failure into the same safe localized toast.
  } catch (_error) {
    // Avoid exposing server diagnostics or untranslated text in the game surface.
    toast(text('errors.actionFailed'));
  // Always restore controls after success or failure.
  } finally {
    // Release the atomic action lock.
    busy = false;
    // Rerender only when the route remains mounted.
    render();
  }
}


// Start or safely replay one wagered Deuces Wild hand.
async function deal(inputValue = wager) {
  // Preserve the caller-captured input value across the busy-state rerender.
  const rawWager = inputValue;
  // Parse the configured wager before allocating any persistent retry identity.
  const candidateWager = Number(rawWager);
  // Reject non-finite and out-of-range values without pinning an unusable action id.
  if (!Number.isFinite(candidateWager) || candidateWager < MIN_WAGER || candidateWager > MAX_WAGER) {
    // Explain the correct fake-money boundary through paired game-owned copy.
    toast(text('errors.invalidWager'));
    // Leave the wager editable so the player can correct it without reloading.
    return;
  }
  // Normalize accepted input to the same two-decimal precision as the ledger.
  const requestedWager = Math.round(candidateWager * 100) / 100;
  // Create one persistent action id when no unresolved deal exists.
  if (!pendingDealActionId) pendingDealActionId = nextActionId('deal');
  // Bind the first attempted wager to that action id for conflict-free retries.
  if (pendingDealWager === null) pendingDealWager = requestedWager;
  // Keep the displayed wager aligned with the retry-safe committed parameters.
  wager = pendingDealWager;
  // Post only the wager and retry-safe action through the public session-bound API.
  const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealActionId, wager }));
  // Adopt reload-safe state after the server confirms the action.
  adoptPayload(payload);
  // Clear the deal retry id only after a confirming server response.
  pendingDealActionId = null;
  // Clear its pinned wager after the corresponding response is confirmed.
  pendingDealWager = null;
  // Refresh the shared authenticated wallet after ledger movement.
  await refreshBalance();
}


// Persist one changed hold selection with its own retry-safe action id.
async function toggleHold(position) {
  // Read the active source hand before constructing the next selection.
  const roundItem = state?.active_round;
  // Stop stale clicks when no hold-phase round remains active.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Build a mutable selection set from server-owned state.
  const holds = new Set(roundItem.holds || []);
  // Toggle the requested source-card position.
  if (holds.has(position)) holds.delete(position); else holds.add(position);
  // Sort the selection so state and action retry keys remain deterministic.
  const desiredHolds = [...holds].sort((left, right) => left - right);
  // Correlate one action id with the round and exact desired selection.
  const retryKey = `${roundItem.round_id}:${desiredHolds.join(',')}`;
  // Reuse the same action id after a lost hold response.
  const actionId = pendingHoldActionIds.get(retryKey) || nextActionId('holds');
  // Retain the unresolved action before starting the network request.
  pendingHoldActionIds.set(retryKey, actionId);
  // Persist the selection through the public session-bound endpoint.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/holds`, withCurrentPlayer({ action_id: actionId, holds: desiredHolds }));
  // Adopt the server's reload-safe selection state.
  adoptPayload(payload);
  // Clear the retry id only after the server confirms this exact selection.
  pendingHoldActionIds.delete(retryKey);
}


// Draw and settle the active hand with one persistent payout action id.
async function draw() {
  // Read the active source hand before settlement archives it.
  const roundItem = state?.active_round;
  // Stop stale clicks when no hold-phase round remains active.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Reuse one draw action id until the server confirms settlement.
  const actionId = pendingDrawActionIds.get(roundItem.round_id) || nextActionId('draw');
  // Retain the unresolved draw id before starting the network request.
  pendingDrawActionIds.set(roundItem.round_id, actionId);
  // Complete and settle the hand through the public session-bound endpoint.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/draw`, withCurrentPlayer({ action_id: actionId }));
  // Adopt the completed reload-safe state.
  adoptPayload(payload);
  // Clear the draw retry id only after a confirming server response.
  pendingDrawActionIds.delete(roundItem.round_id);
  // Capture the just-settled deal's committed wager so one click can repeat an identical hand.
  const settledRound = currentRound();
  // Remember the repeatable wager only once settlement archived a positive committed stake.
  if (settledRound?.phase === 'settled' && roundWager(settledRound)) lastBet = { wager: roundWager(settledRound) };
  // Refresh the shared authenticated wallet after payout settlement.
  await refreshBalance();
}


// Re-apply the last settled wager and start one identical new deal without replaying holds.
async function repeat() {
  // Ignore repeat while any request, unresolved deal, mid-hand, or absent prior wager blocks a fresh deal.
  if (busy || pendingDealActionId || state?.active_round || !lastBet) return;
  // Restore the remembered wager so the preview and next deal use the repeated stake.
  wager = lastBet.wager;
  // Align the editable input with the restored wager before the shared busy render replaces it.
  const wagerInput = root?.querySelector('#dwvp-wager');
  // Apply the stored wager only when the enabled input is present.
  if (wagerInput) wagerInput.value = String(lastBet.wager);
  // Start one new deal with the restored wager through shared busy handling, never replaying holds.
  await runAction(() => deal(lastBet.wager));
}


// Attach semantic control handlers after every deterministic render.
function bindEvents() {
  // Preserve valid wager edits before a deal action is created.
  const wagerInput = root.querySelector('#dwvp-wager');
  // Update the preview without replacing the focused input or issuing token movement.
  if (wagerInput) wagerInput.oninput = () => {
    // Preserve the exact numeric candidate for later local validation.
    wager = Number(wagerInput.value);
    // Resolve the current total preview without rerendering the control tree.
    const total = root.querySelector('.dwvp-total strong');
    // Refresh only the text preview while the player edits the wager.
    if (total) total.textContent = tokenAmount(wager);
  };
  // Wire the primary deal action through shared busy handling.
  const dealButton = root.querySelector('[data-action="deal"]');
  // Start or replay one deal when its mounted control is available.
  if (dealButton) dealButton.onclick = () => {
    // Capture the editable input before shared busy handling replaces the control DOM.
    const requestedValue = wagerInput?.value ?? wager;
    // Validate and submit that exact captured value inside the atomic action wrapper.
    return runAction(() => deal(requestedValue));
  };
  // Wire the one-click repeat that opens a new deal with the last settled wager.
  const repeatButton = root.querySelector('[data-action="repeat"]');
  // Guard and start a repeated deal when its mounted control is available.
  if (repeatButton) repeatButton.onclick = () => repeat();
  // Wire the draw action through shared busy handling.
  const drawButton = root.querySelector('[data-action="draw"]');
  // Complete the current hand when its mounted control is available.
  if (drawButton) drawButton.onclick = () => runAction(draw);
  // Wire every source card to reload-safe hold persistence.
  root.querySelectorAll('[data-hold-position]').forEach(button => {
    // Toggle the selected position through its public API action.
    button.onclick = () => runAction(() => toggleHold(Number(button.dataset.holdPosition)));
  });
}


// Export the descriptor-owned lazy game module contract.
export const DeucesWildVideoPokerGame = {
  // Expose the stable module id used by catalog navigation.
  id: 'deuces_wild_video_poker',
  // Leave presentation labels to the descriptor and locale domain.
  label: '',
  // Load locale and authenticated state before rendering visible text.
  async mount(node) {
    // Store the route outlet for deterministic subsequent renders.
    root = node;
    // Reset the repeatable wager so a new session never inherits a prior deal.
    lastBet = null;
    // Load the paired game-owned locale resources.
    await loadI18nDomain(DOMAIN);
    // Subscribe to locale changes without remounting or losing hold state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read the authenticated player's reload-safe state.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Adopt state and the authoritative paytable from the public response.
    adoptPayload(payload);
    // Restore the active round's wager when reloading a hold decision.
    wager = Number(state?.active_round?.total_wager ?? state?.active_round?.wager ?? state?.active_round?.wager_amount ?? wager);
    // Recover a repeatable wager from the newest settled round so repeat survives a reload.
    const recovered = state?.recent_rounds?.slice(-1)[0];
    // Restore the repeatable wager only when a settled round exposes its committed stake.
    if (recovered?.phase === 'settled' && roundWager(recovered)) lastBet = { wager: roundWager(recovered) };
    // Render the complete issue #92 surface.
    render();
    // Refresh the shared wallet without rendering game-owned balance text.
    await refreshBalance();
  },
  // Release every external lifecycle resource when the shell changes route.
  unmount() {
    // Unsubscribe the locale callback when it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated unmounts remain safe.
    unsubscribeLocale = null;
    // Clear cached player state from the inactive route.
    state = null;
    // Clear the repeatable wager so the next session starts fresh.
    lastBet = null;
    // Clear the mount node so late promises cannot render into another route.
    root = null;
    // Preserve only unresolved action ids so later retries remain exactly-once safe.
  },
};
