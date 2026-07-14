// Implement the isolated issue #91 Jacks-or-Better browser module without shared shell edits.

// Import session-aware API helpers so the shared router remains the player-identity authority.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback and escaping without creating game-owned global resources.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the accessible shared card renderer from the completed #96 primitive lane.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/jacks_or_better_video_poker';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/jacks-or-better-video-poker';
// Preserve the conventional one-through-five coin choices in display order.
const COIN_CHOICES = [1, 2, 3, 4, 5];
// Preserve the fixed 9/6 Jacks-or-Better paytable order from strongest to weakest.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'jacks_or_better'];
// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated-player state for reload-safe rendering.
let state = null;
// Store the server-owned credit table rather than duplicating game rules in the browser.
let paytable = {};
// Store the selected coin count for the next deal.
let selectedCoins = 1;
// Store the play-token value of one selected coin.
let coinValue = 1;
// Block overlapping atomic actions while one request is in flight.
let busy = false;
// Store the locale cleanup callback so unmount releases its subscription.
let unsubscribeLocale = null;
// Store a fallback action counter for browsers without random UUID support.
let actionCounter = 0;
// Retain an unresolved deal action id so a lost response cannot duplicate the wager.
let pendingDealActionId = null;
// Retain an unresolved draw action id so a lost response cannot duplicate the payout.
let pendingDrawActionId = null;


// Resolve one game-owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every visible or ARIA label to the paired EN/RU resource domain.
  return t(key, params, DOMAIN);
}


// Format a play-token amount without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Return a locale-formatted value followed by localized fake-token terminology.
  return `${formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${text('units.playTokens')}`;
}


// Format integer paytable credits with localized unit terminology.
function creditAmount(value) {
  // Return a locale-formatted integer followed by the game-owned credit label.
  return `${formatNumber(value, { maximumFractionDigits: 0 })} ${text('units.credits')}`;
}


// Render one shared card while replacing its English primitive ARIA name with game i18n.
function localizedCard(card, options = {}) {
  // Normalize the compact rank from every character except the final suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build the accessible name entirely from the paired game-owned resources.
  const label = text('cards.cardLabel', { rank: text(`ranks.${rank}`), suit: text(`suits.${suit}`) });
  // Reuse shared semantic markup while replacing only its locale-neutral accessible label.
  return renderCard(card, options).replace(/aria-label="[^"]*"/, `aria-label="${safe(label)}"`);
}


// Return the active round or newest settled round for one stable stage.
function currentRound() {
  // Prefer actionable state, then fall back to the newest reload-safe history entry.
  return state?.active_round || state?.recent_rounds?.slice(-1)[0] || null;
}


// Clear browser retry keys only when authoritative reload-safe state proves they committed.
function reconcilePendingActions() {
  // Search the active slot and bounded history for committed action ownership.
  const rounds = [state?.active_round, ...(state?.recent_rounds || [])].filter(Boolean);
  // Clear a deal key after state confirms the matching round exists.
  if (pendingDealActionId && rounds.some(roundItem => roundItem.deal_action_id === pendingDealActionId)) pendingDealActionId = null;
  // Clear a draw key after state confirms the matching settlement exists.
  if (pendingDrawActionId && rounds.some(roundItem => roundItem.draw_action_id === pendingDrawActionId)) pendingDrawActionId = null;
}


// Create one bounded retry key for exactly-once deal or draw actions.
function nextActionId(kind) {
  // Use the browser cryptographic UUID source when available.
  if (globalThis.crypto?.randomUUID) return `${kind}-${globalThis.crypto.randomUUID()}`;
  // Increment the local fallback counter to disambiguate actions in one millisecond.
  actionCounter += 1;
  // Combine a non-secret timestamp and counter without claiming fairness entropy.
  return `${kind}-${Date.now().toString(36)}-${actionCounter.toString(36)}`;
}


// Translate internal round state into concise player-facing phase language.
function phaseLabel(roundItem) {
  // Show the idle phase before the first deal.
  if (!roundItem) return text('phases.ready');
  // Show the hold decision while the initial hand remains actionable.
  if (roundItem.phase === 'hold') return text('phases.chooseHolds');
  // Show a localized net result after settlement.
  return text(`phases.${roundItem.net_result || 'complete'}`);
}


// Render one selectable initial-hand card through the accessible shared renderer.
function selectableCard(card, position, held, disabled) {
  // Describe the action according to the current held state.
  const actionLabel = held ? text('cards.release', { position: position + 1 }) : text('cards.hold', { position: position + 1 });
  // Return a semantic pressed-state button with a non-color held badge.
  return `<button type="button" class="jobvp-card-button${held ? ' is-held' : ''}" data-hold-position="${position}" aria-pressed="${held}" aria-label="${safe(actionLabel)}"${disabled ? ' disabled' : ''}>${localizedCard(card, { selected: held })}${held ? `<span class="jobvp-held-label">${safe(text('cards.held'))}</span>` : ''}</button>`;
}


// Render the current five-card hand in hold or settled form.
function handHtml(roundItem) {
  // Build a set so selected positions can be checked independently of ordering.
  const held = new Set(roundItem.holds || []);
  // Read final cards after settlement and initial cards while holds remain open.
  const cards = roundItem.phase === 'settled' ? (roundItem.final_hand || []) : (roundItem.initial_hand || []);
  // Disable all hold controls outside the actionable phase or during a request.
  const disabled = roundItem.phase !== 'hold' || busy;
  // Prepare one markup slot for either static final cards or actionable source cards.
  let rendered = '';
  // Render settled cards as static accessible elements.
  if (roundItem.phase === 'settled') {
    // Join the final cards without interactive hold controls.
    rendered = cards.map(card => localizedCard(card)).join('');
  // Render the initial hand as localized pressed-state buttons.
  } else {
    // Join every selectable source card with its persisted held state.
    rendered = cards.map((card, position) => selectableCard(card, position, held.has(position), disabled)).join('');
  }
  // Choose a localized accessible group name for the current hand phase.
  const label = roundItem.phase === 'settled' ? text('cards.finalHandLabel') : text('cards.initialHandLabel');
  // Return the dominant hand region with a stable browser-test hook.
  return `<section class="jobvp-hand" aria-label="${safe(label)}" data-testid="jobvp-hand"><div class="jobvp-card-row">${rendered}</div></section>`;
}


// Render settlement details after the single draw completes.
function resultHtml(roundItem) {
  // Render no settlement panel until the server reports a completed round.
  if (roundItem.phase !== 'settled') return '';
  // Translate the game-owned paytable result key.
  const outcome = text(`outcomes.${roundItem.outcome || 'no_win'}`);
  // Return a reserved result region whose values do not resize the primary controls.
  return `<section class="jobvp-result" data-testid="jobvp-result" aria-label="${safe(text('summary.title'))}"><h2>${safe(outcome)}</h2><div class="jobvp-summary"><span>${safe(text('summary.wager'))}<strong>${safe(tokenAmount(roundItem.total_wager))}</strong></span><span>${safe(text('summary.payoutCredits'))}<strong>${safe(creditAmount(roundItem.payout_credits || 0))}</strong></span><span>${safe(text('summary.payout'))}<strong>${safe(tokenAmount(roundItem.total_payout || 0))}</strong></span><span>${safe(text('summary.net'))}<strong>${safe(tokenAmount(roundItem.net || 0))}</strong></span></div></section>`;
}


// Render the dominant game stage for ready, hold, and settled states.
function stageHtml(roundItem) {
  // Render localized player guidance before the first wager.
  if (!roundItem) return `<section class="jobvp-empty" data-testid="jobvp-ready"><h2>${safe(text('stage.readyTitle'))}</h2><p>${safe(text('stage.readyBody'))}</p></section>`;
  // Describe the actionable or settled stage without exposing internal phase keys.
  const guidance = roundItem.phase === 'hold' ? text('stage.holdGuidance') : text('stage.settledGuidance');
  // Return the guidance, five-card hand, and optional settlement summary.
  return `<p class="jobvp-stage-guidance" role="status">${safe(guidance)}</p>${handHtml(roundItem)}${resultHtml(roundItem)}`;
}


// Render one pressed-state coin-count selector.
function coinButton(count, disabled) {
  // Describe the numeric choice through a localized accessible label.
  const label = text('controls.coinChoice', { count });
  // Return a touch-sized selector whose state is communicated beyond color.
  return `<button type="button" class="jobvp-coin${selectedCoins === count ? ' is-selected' : ''}" data-coin-count="${count}" aria-pressed="${selectedCoins === count}" aria-label="${safe(label)}"${disabled ? ' disabled' : ''}>${safe(formatNumber(count))}</button>`;
}


// Render coin configuration and the two atomic gameplay actions.
function controlsHtml(roundItem) {
  // Disable configuration while a dealt hand remains active or any request is in flight.
  const configurationDisabled = Boolean(state?.active_round) || busy;
  // Render exactly the conventional one-through-five coin choices.
  const coinButtons = COIN_CHOICES.map(count => coinButton(count, configurationDisabled)).join('');
  // Enable deal only when no active hand exists.
  const dealDisabled = Boolean(state?.active_round) || busy;
  // Enable draw only while the initial hand awaits hold choices.
  const drawDisabled = !roundItem || roundItem.phase !== 'hold' || busy;
  // Calculate the preview from the same coin count and value submitted to the server.
  const totalWager = selectedCoins * coinValue;
  // Return the complete control rail with stable primary-action placement.
  return `<aside class="jobvp-panel jobvp-controls" aria-label="${safe(text('controls.title'))}"><h2>${safe(text('controls.title'))}</h2><fieldset${configurationDisabled ? ' disabled' : ''}><legend>${safe(text('controls.coinCount'))}</legend><div class="jobvp-coins">${coinButtons}</div></fieldset><label for="jobvp-coin-value">${safe(text('controls.coinValue'))}</label><input id="jobvp-coin-value" type="number" min="0.01" max="20000" step="0.01" value="${safe(coinValue)}"${configurationDisabled ? ' disabled' : ''}><p class="jobvp-total">${safe(text('controls.totalWager'))}<strong>${safe(tokenAmount(totalWager))}</strong></p><button type="button" class="jobvp-primary" data-action="deal"${dealDisabled ? ' disabled' : ''}>${safe(text('controls.deal'))}</button><button type="button" data-action="draw"${drawDisabled ? ' disabled' : ''}>${safe(text('controls.draw'))}</button><p class="jobvp-help">${safe(text('controls.holdHelp'))}</p></aside>`;
}


// Render the fixed credit schedule supplied by the backend.
function paytableHtml() {
  // Render localized coin-count headers for the five conventional columns.
  const headers = COIN_CHOICES.map(count => `<th scope="col" class="${selectedCoins === count ? 'is-selected' : ''}" aria-label="${safe(text('paytable.coinHeader', { count }))}">${safe(formatNumber(count))}</th>`).join('');
  // Render every qualifying hand and its one-through-five coin credit schedule.
  const rows = PAYTABLE_ORDER.map(outcome => {
    // Read a complete server row or a safe zero row before rendering.
    const values = Array.isArray(paytable[outcome]) ? paytable[outcome] : COIN_CHOICES.map(() => 0);
    // Highlight the selected coin column while preserving textual values.
    const cells = COIN_CHOICES.map((count, index) => `<td class="${selectedCoins === count ? 'is-selected' : ''}">${safe(formatNumber(values[index] || 0))}</td>`).join('');
    // Return one table row with a localized result label.
    return `<tr><th scope="row">${safe(text(`outcomes.${outcome}`))}</th>${cells}</tr>`;
  // Join completed rows only after every callback returns localized markup.
  }).join('');
  // Return one keyboard-readable data rail without nested scrolling containers.
  return `<aside class="jobvp-panel jobvp-data" aria-label="${safe(text('paytable.title'))}"><h2>${safe(text('paytable.title'))}</h2><table><thead><tr><th scope="col">${safe(text('paytable.result'))}</th>${headers}</tr></thead><tbody>${rows}</tbody></table><p>${safe(text('paytable.note'))}</p></aside>`;
}


// Return game-owned styles inside the lazy module so no shared stylesheet is touched.
function stylesHtml() {
  // Keep the five-card stage dominant at desktop and stack controls first on narrow screens.
  return `<style>
    /* Keep responsive issue #91 presentation isolated inside the lazy game module. */
    .jobvp-shell{display:grid;gap:18px;min-width:0}.jobvp-header{display:flex;align-items:end;justify-content:space-between;gap:12px}.jobvp-header p,.jobvp-header h1{margin:0}.jobvp-header p{color:#ffd780;font-weight:800}.jobvp-phase{padding:7px 12px;border:1px solid rgba(255,215,128,.48);border-radius:999px;background:rgba(255,215,128,.08)}.jobvp-layout{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(520px,2.5fr) minmax(280px,1fr);gap:16px;align-items:start}.jobvp-panel,.jobvp-stage{min-width:0;padding:16px;border:1px solid rgba(255,215,128,.25);border-radius:16px;background:rgba(3,29,20,.84)}.jobvp-controls{display:grid;gap:12px}.jobvp-controls fieldset{margin:0;padding:0;border:0}.jobvp-coins{display:grid;grid-template-columns:repeat(5,1fr);gap:7px}.jobvp-coin{min-width:42px;min-height:44px}.jobvp-coin.is-selected{outline:3px solid #ffd780;outline-offset:2px}.jobvp-total{display:grid;gap:3px;margin:0;color:var(--muted,#b8c8c1)}.jobvp-total strong{color:#fff2c2;font-size:1.15rem}.jobvp-primary{min-height:48px;background:#a51f2d;color:#fff}.jobvp-help,.jobvp-data p,.jobvp-stage-guidance{color:var(--muted,#b8c8c1)}.jobvp-stage{display:grid;align-content:start;gap:18px;min-height:480px}.jobvp-stage-guidance{min-height:24px;margin:0;text-align:center}.jobvp-hand{display:grid;place-items:center;min-height:220px;padding:22px 12px;border:1px solid rgba(255,215,128,.2);border-radius:14px;background:radial-gradient(circle at 50% 40%,rgba(29,105,72,.48),rgba(3,29,20,.18))}.jobvp-card-row{display:flex;flex-wrap:nowrap;justify-content:center;gap:10px;max-width:100%}.jobvp-card-button{position:relative;min-width:64px;min-height:94px;padding:3px;border:2px solid transparent;background:transparent}.jobvp-card-button.is-held{border-color:#ffd780;border-radius:10px}.jobvp-held-label{position:absolute;inset:auto 3px 3px;padding:2px 5px;border-radius:999px;background:#07150f;color:#ffd780;font-size:10px;font-weight:800}.jobvp-result{display:grid;gap:12px;padding:16px;border:1px solid rgba(255,215,128,.36);border-radius:14px;background:rgba(255,215,128,.07)}.jobvp-result h2{margin:0;text-align:center}.jobvp-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.jobvp-summary span{display:grid;gap:4px;padding:10px;border-radius:10px;background:rgba(255,255,255,.04)}.jobvp-summary strong{color:#fff2c2}.jobvp-empty{min-height:400px;display:grid;place-content:center;text-align:center}.jobvp-data table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:.82rem}.jobvp-data th,.jobvp-data td{padding:7px 3px;border-bottom:1px solid rgba(255,255,255,.1);text-align:center;overflow-wrap:anywhere}.jobvp-data th:first-child{width:45%;text-align:left}.jobvp-data .is-selected{color:#211600;background:#ffd780;font-weight:900}.jobvp-card-button:focus-visible,.jobvp-shell button:focus-visible,.jobvp-shell input:focus-visible{outline:3px solid #ffd780;outline-offset:2px}@media(max-width:1180px){.jobvp-layout{grid-template-columns:1fr}.jobvp-controls{order:1}.jobvp-stage{order:2;min-height:0}.jobvp-data{order:3}.jobvp-summary{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.jobvp-header{align-items:start;flex-direction:column}.jobvp-panel,.jobvp-stage{padding:12px}.jobvp-card-row{gap:4px}.jobvp-card-button{min-width:50px;min-height:76px}.jobvp-hand{min-height:170px;padding:14px 4px}.jobvp-summary{grid-template-columns:1fr}.jobvp-data table{font-size:.72rem}.jobvp-data th,.jobvp-data td{padding:6px 2px}}@media(prefers-reduced-motion:reduce){.jobvp-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
    /* End the isolated style block without creating runtime resources. */
  </style>`;
}


// Render the complete three-zone game surface from cached state.
function render() {
  // Stop when an asynchronous completion arrives after unmount.
  if (!root) return;
  // Read the active or newest completed round once per render.
  const roundItem = currentRound();
  // Replace the route outlet atomically so controls, stage, and data cannot drift.
  root.innerHTML = `${stylesHtml()}<section class="jobvp-shell" data-testid="jacks-or-better-video-poker"><header class="jobvp-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="jobvp-phase" role="status">${safe(phaseLabel(roundItem))}</span></header><div class="jobvp-layout">${controlsHtml(roundItem)}<main class="jobvp-stage">${stageHtml(roundItem)}</main>${paytableHtml()}</div></section>`;
  // Attach handlers to the newly rendered semantic controls.
  bindEvents();
}


// Execute one atomic browser action with stable disabled-state cleanup.
async function runAction(action) {
  // Ignore overlapping button events while an API request is in flight.
  if (busy) return;
  // Disable controls before beginning the action.
  busy = true;
  // Render disabled controls in their stable positions.
  render();
  // Start protected action handling so API errors become shared shell feedback.
  try {
    // Execute the supplied public API action.
    await action();
  // Translate request failures into the existing shared toast surface.
  } catch (_error) {
    // Show localized game-owned feedback so server diagnostics cannot leak English in Russian UI.
    toast(text('errors.actionFailed'));
  // Always restore controls after success or failure.
  } finally {
    // Release the action lock.
    busy = false;
    // Rerender only when the route remains mounted.
    render();
  }
}


// Start one exactly-once single-hand wager through the public endpoint.
async function deal() {
  // Read the coin-value input before rerender removes its current value.
  const input = root?.querySelector('#jobvp-coin-value');
  // Normalize the cached value used by this request and later previews.
  coinValue = Math.min(20000, Math.max(0.01, Number(input?.value || coinValue || 1)));
  // Reuse an unresolved action key so retry cannot create a second debit.
  pendingDealActionId = pendingDealActionId || nextActionId('deal');
  // Submit only public game settings and the retry-safe action id.
  const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealActionId, coins: selectedCoins, coin_value: coinValue }));
  // Store returned reload-safe state after the committed wager.
  state = payload.state;
  // Store the authoritative server paytable in case this was the first request.
  paytable = payload.paytable || paytable;
  // Clear the deal key only after the response proves state was recovered.
  pendingDealActionId = null;
  // Clear any stale draw key before a new round becomes actionable.
  pendingDrawActionId = null;
  // Refresh the authenticated shared wallet after the ledger debit.
  await refreshBalance();
}


// Persist one changed hold position for reload-safe continuation.
async function toggleHold(position) {
  // Read the active initial hand before constructing the next selection.
  const roundItem = state?.active_round;
  // Stop stale clicks when the active round has already settled.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Build a mutable selection set from server-owned state.
  const holds = new Set(roundItem.holds || []);
  // Remove an already-held position or add a newly held position.
  if (holds.has(position)) holds.delete(position); else holds.add(position);
  // Persist the canonical sorted selection through the game API.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/holds`, withCurrentPlayer({ holds: [...holds].sort((left, right) => left - right) }));
  // Store the returned reload-safe state.
  state = payload.state;
}


// Draw the unheld cards and settle the single payout exactly once.
async function draw() {
  // Read the active hand before settlement archives it.
  const roundItem = state?.active_round;
  // Stop stale clicks when no active hold-phase round exists.
  if (!roundItem || roundItem.phase !== 'hold') return;
  // Reuse an unresolved action key so retry cannot duplicate settlement.
  pendingDrawActionId = pendingDrawActionId || nextActionId('draw');
  // Complete and settle the deterministic server-owned hand.
  const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(roundItem.round_id)}/draw`, withCurrentPlayer({ action_id: pendingDrawActionId }));
  // Store the completed reload-safe state.
  state = payload.state;
  // Clear the draw key only after the response proves settlement was recovered.
  pendingDrawActionId = null;
  // Refresh the shared wallet after any payout credit.
  await refreshBalance();
}


// Attach semantic control handlers after every atomic render.
function bindEvents() {
  // Wire coin buttons to cached pre-deal configuration.
  root.querySelectorAll('[data-coin-count]').forEach(button => {
    // Change the selected coin count and rerender its pressed state.
    button.onclick = () => {
      // Store the selected conventional coin count.
      selectedCoins = Number(button.dataset.coinCount);
      // Refresh previews and the highlighted paytable column.
      render();
    };
  });
  // Preserve valid coin-value edits in cached configuration.
  const valueInput = root.querySelector('#jobvp-coin-value');
  // Update the total-wager preview without issuing token movement.
  if (valueInput) valueInput.onchange = () => {
    // Bound the preview to the same server contract range.
    coinValue = Math.min(20000, Math.max(0.01, Number(valueInput.value || 1)));
    // Refresh the formatted preview.
    render();
  };
  // Wire the primary deal action through shared busy handling.
  const dealButton = root.querySelector('[data-action="deal"]');
  // Start one idempotent deal when the mounted button exists.
  if (dealButton) dealButton.onclick = () => runAction(deal);
  // Wire the draw action through shared busy handling.
  const drawButton = root.querySelector('[data-action="draw"]');
  // Settle the current hand when the mounted button exists.
  if (drawButton) drawButton.onclick = () => runAction(draw);
  // Wire every initial card to reload-safe hold persistence.
  root.querySelectorAll('[data-hold-position]').forEach(button => {
    // Toggle the selected position through the public API.
    button.onclick = () => runAction(() => toggleHold(Number(button.dataset.holdPosition)));
  });
}


// Export the catalog-owned lazy game module contract expected by the Wave 0 loader.
export const JacksOrBetterVideoPokerGame = {
  // Expose the stable module id used by catalog navigation.
  id: 'jacks_or_better_video_poker',
  // Leave catalog presentation labels to the owned descriptor and locale domain.
  label: '',
  // Load locale and authenticated-player state before rendering visible text.
  async mount(node) {
    // Store the route outlet for subsequent deterministic renders.
    root = node;
    // Load active and fallback game-owned resources.
    await loadI18nDomain(DOMAIN);
    // Subscribe to locale changes without remounting or losing game state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read the authenticated player's reload-safe state.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Cache the state used by stage and controls.
    state = payload.state;
    // Reconcile any response-lost retry keys against authoritative persisted state.
    reconcilePendingActions();
    // Cache the authoritative server credit schedule.
    paytable = payload.paytable || {};
    // Read the active or newest round for configuration restoration.
    const restoredRound = currentRound();
    // Restore the round's coin count when direct navigation or reload finds state.
    selectedCoins = restoredRound?.coins || selectedCoins;
    // Restore the round's coin value when direct navigation or reload finds state.
    coinValue = restoredRound?.coin_value || coinValue;
    // Render the complete issue #91 surface.
    render();
    // Refresh the shared wallet without duplicating balance presentation.
    await refreshBalance();
  },
  // Release every game-owned lifecycle resource when the shell changes route.
  unmount() {
    // Unsubscribe the locale callback when it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated unmounts remain safe.
    unsubscribeLocale = null;
    // Clear cached player state from the inactive module.
    state = null;
    // Clear the mount node so late promises cannot render into another route.
    root = null;
    // No timers or global listeners remain because this module creates none.
  },
};
