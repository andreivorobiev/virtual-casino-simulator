// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import the frozen API helpers used by this frontend module.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared shell/UI helpers so formatting, cards, toasts, and wallet refreshes stay consistent.
import { toast, refreshBalance, cardHtml, safe, captureGameFocus, restoreGameFocus, syncGameLiveStatus } from '../core/ui.js';
// Import the i18n runtime so Blackjack text can refresh without remounting gameplay state.
import { initI18n, loadI18nDomain, onLocaleChange, t, formatMoney, formatNumber } from '../core/i18n.js';
// Import voice helpers so existing Blackjack audio behavior is preserved.
import { speak, clickSound } from '../core/voice.js';
// Import the bot capability reader without coupling Blackjack to bot strategies.
import { eligibleBots } from '../core/bots.js';

// Store the i18n domain name once so every lookup uses the owned resource file.
const I18N_DOMAIN = 'games/blackjack';
// Store the public API root once so endpoint construction cannot drift.
const API_ROOT = '/api/v1/games/blackjack';
// Store the maximum number of visible hand lanes supported by the current engine.
const FALLBACK_MAX_HANDS = 4;
// Store the standard action metadata so buttons stay mounted in a stable order.
const ACTIONS = [
  // Define Hit as the first high-frequency player action.
  { id: 'hit', endpoint: 'hit', testid: 'blackjack-hit', label: 'controls.hit' },
  // Define Stand as the second high-frequency player action.
  { id: 'stand', endpoint: 'stand', testid: 'blackjack-stand', label: 'controls.stand' },
  // Define Double as a premium wager action whose legality is derived client-side.
  { id: 'double', endpoint: 'double', testid: 'blackjack-double', label: 'controls.double' },
  // Define Split as a mounted affordance even when the current hand cannot split.
  { id: 'split', endpoint: 'split', testid: 'blackjack-split', label: 'controls.split' },
  // Define Surrender as a mounted affordance controlled by the table rules.
  { id: 'surrender', endpoint: 'surrender', testid: 'blackjack-surrender', label: 'controls.surrender' },
  // Define Insurance as a mounted affordance controlled by the dealer up-card.
  { id: 'insurance', endpoint: 'insurance', testid: 'blackjack-insurance', label: 'controls.insurance' },
  // Define Even Money as a mounted affordance for the natural-blackjack edge case.
  { id: 'evenMoney', endpoint: 'even-money', testid: 'blackjack-even-money', label: 'controls.evenMoney' },
];
// Store root so later code can render into the mounted route outlet.
let root = null;
// Store state so locale changes can rerender without reloading or resetting gameplay.
let state = null;
// Store betAmount so the bet input survives rerenders and locale changes.
let betAmount = 25;
// Store activeRoundId so the user keeps the same visible round between state refreshes.
let activeRoundId = null;
// Store actionBusy so controls remain stable while a request is in flight.
let actionBusy = false;
// Store botCapabilities so the bot panel can rerender from cache during locale changes.
let botCapabilities = { bots: [], capabilities: { supports_bots: false, strategies: [] } };
// Store unsubscribeLocale so unmount can release the i18n listener.
let unsubscribeLocale = null;

// Define T as a short local wrapper around the Blackjack resource domain.
function T(key, params = {}) {
  // Return the localized string for this module.
  return t(key, params, I18N_DOMAIN);
}

// Define localMoney so fake-money display follows the active format locale.
function localMoney(value) {
  // Return a localized USD fake-money string without changing ledger semantics.
  return formatMoney(value);
}

// Define signedLocalMoney so settlement rows can show net movement clearly.
function signedLocalMoney(value) {
  // Store amount so sign handling is consistent for strings and numbers.
  const amount = Number(value || 0);
  // Return a signed localized fake-money string.
  return `${amount >= 0 ? '+' : '-'}${localMoney(Math.abs(amount))}`;
}

// Define load so Blackjack reads i18n resources and current API state before rendering.
async function load() {
  // Initialize locale settings so saved Admin language choices apply before rendering.
  await initI18n({ domains: [I18N_DOMAIN] });
  // Load the owned Blackjack resource bundle before visible strings are generated.
  await loadI18nDomain(I18N_DOMAIN);
  // Read current Blackjack state through the frozen v1 endpoint.
  const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
  // Store the module state payload for all render helpers.
  state = payload.state;
  // Prefer any active round but keep the newest settled round visible when no active hand exists.
  activeRoundId = findActiveRoundId();
  // Render immediately so the user is not blocked by bot capability loading.
  render();
  // Refresh the bot panel through the public control-plane capability endpoint.
  await refreshBotCapabilities();
  // Refresh the shared wallet after loading the game state.
  await refreshBalance();
}

// Define refreshBotCapabilities so the bot panel reflects compatible controller availability.
async function refreshBotCapabilities() {
  // Start protected capability loading so bot API failures never break Blackjack play.
  try {
    // Read eligible bot controllers through the shared public helper.
    botCapabilities = await eligibleBots('blackjack');
  // Handle capability failures with an empty panel model.
  } catch (_) {
    // Keep a safe empty capability payload when the control plane cannot be reached.
    botCapabilities = { bots: [], capabilities: { supports_bots: false, strategies: [] } };
  }
  // Render the panel from cached data if Blackjack is still mounted.
  if (root) renderBotPanelIntoDom();
}

// Define rounds so helpers can work with the object-backed API payload.
function rounds() {
  // Return rounds in insertion order as supplied by the JSON object.
  return Object.values(state?.rounds || {});
}

// Define latestRound so an inactive table still shows the most recent settled result.
function latestRound() {
  // Return the newest known round or null when the player has not dealt yet.
  return rounds().slice(-1)[0] || null;
}

// Define findActiveRoundId so the mounted UI follows active play first.
function findActiveRoundId() {
  // Store candidates so active-state selection is isolated from rendering.
  const candidates = rounds();
  // Store active so player decisions and pending credits remain visible.
  const active = candidates.find(roundItem => ['player_turn', 'settled_pending_credit'].includes(roundItem.status));
  // Return the active id or the latest id if every round is already settled.
  return (active || candidates.slice(-1)[0] || {}).round_id || null;
}

// Define currentRound so callers do not duplicate fallback lookup logic.
function currentRound() {
  // Return the selected round, the newest round, or null for an idle table.
  return state?.rounds?.[activeRoundId] || latestRound();
}

// Define activeHand so action legality reads the same hand the engine will use.
function activeHand(roundItem = currentRound()) {
  // Return null when no player-turn hand exists.
  if (!roundItem || roundItem.status !== 'player_turn') return null;
  // Store index so malformed payloads cannot throw in the renderer.
  const index = Number(roundItem.active_hand_index || 0);
  // Return the indexed hand only when it is still active.
  return roundItem.hands?.[index]?.status === 'active' ? roundItem.hands[index] : null;
}

// Define readBetAmount so the current input value is persisted before actions rerender.
function readBetAmount() {
  // Read the bet input if it exists in the current DOM.
  const input = root?.querySelector('#bjBet');
  // Update the cached bet amount from the input while preserving the previous fallback.
  betAmount = Number(input?.value || betAmount || 25);
  // Return a positive number for API calls.
  return Math.max(1, betAmount);
}

// Define deal so the initial wager always goes through the public Blackjack endpoint.
async function deal() {
  // Store the requested bet amount before the request rerenders the page.
  const amount = readBetAmount();
  // Mark the UI busy while the public action resolves.
  actionBusy = true;
  // Render stable disabled controls during the request.
  render();
  // Start protected action handling so validation errors become toasts.
  try {
    // Deal a new round through the frozen v1 route.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ bet_amount: amount }));
    // Store the returned state snapshot.
    state = payload.state;
    // Select the newly dealt round in the visible table.
    activeRoundId = payload.round.round_id;
    // Render the new cards and action state.
    render();
    // Refresh bot capability presentation without touching gameplay state.
    await refreshBotCapabilities();
    // Refresh the shared wallet after the ledger debit.
    await refreshBalance();
    // Play the existing short click sound for successful actions.
    clickSound(500, .05);
  // Handle public API validation or conflict errors.
  } catch (error) {
    // Show the API-provided message in the shell toast.
    toast(error.message);
  // Run cleanup after success or failure.
  } finally {
    // Clear the busy flag so controls recover after the request.
    actionBusy = false;
    // Rerender after failures as well so disabled states match current state.
    render();
  }
}

// Define actionBody so special Blackjack actions keep their existing payloads.
function actionBody(actionId) {
  // Branch when Insurance needs an amount body.
  if (actionId === 'insurance') return { amount: insuranceAmount(currentRound()) };
  // Return an empty body for all other public actions.
  return {};
}

// Define act so every player decision goes through the same public action endpoint.
async function act(actionId) {
  // Store the selected round before the request starts.
  const roundItem = currentRound();
  // Branch when the player tries to act before dealing.
  if (!roundItem) {
    // Show a localized prompt without mutating state.
    toast(T('toast.dealFirst'));
    // Stop because there is no round id for the endpoint.
    return;
  }
  // Store metadata so endpoint names remain centralized.
  const meta = ACTIONS.find(action => action.id === actionId);
  // Branch when a malformed button requests an unknown action.
  if (!meta) return;
  // Mark the UI busy while the action is in flight.
  actionBusy = true;
  // Render stable disabled controls during the request.
  render();
  // Start protected action handling so validation errors become toasts.
  try {
    // Post to the existing Blackjack action route without changing payload contracts.
    const payload = await post(`${API_ROOT}/rounds/${roundItem.round_id}/${meta.endpoint}`, withCurrentPlayer(actionBody(actionId)));
    // Store the returned state snapshot.
    state = payload.state;
    // Keep the same round visible after the action.
    activeRoundId = payload.round.round_id;
    // Render the changed hand or settlement state.
    render();
    // Refresh bot capability presentation without touching gameplay state.
    await refreshBotCapabilities();
    // Refresh the shared wallet after any ledger debit or credit.
    await refreshBalance();
    // Play the existing short click sound for successful actions.
    clickSound(640, .05);
    // Announce settlement using the existing voice pathway.
    if (payload.round.status === 'settled') speak(T('voice.settled'), 'blackjack');
  // Handle public API validation or conflict errors.
  } catch (error) {
    // Show the API-provided message in the shell toast.
    toast(error.message);
  // Run cleanup after success or failure.
  } finally {
    // Clear the busy flag so controls recover after the request.
    actionBusy = false;
    // Rerender after failures as well so disabled states match current state.
    render();
  }
}

// Define settings so table rule changes still use the existing settings endpoint.
async function settings() {
  // Read all current table controls from the mounted rail.
  const body = {
    // Preserve the existing deck-count setting contract.
    decks: Number(root.querySelector('#decks').value),
    // Preserve the existing dealer soft-17 setting contract.
    dealer_hits_soft_17: root.querySelector('#h17').checked,
    // Preserve the existing blackjack payout setting contract.
    blackjack_payout: Number(root.querySelector('#bjPay').value),
    // Preserve the existing max split hands setting contract.
    max_split_hands: Number(root.querySelector('#maxSplitHands').value),
    // Preserve the existing double-after-split setting contract.
    double_after_split: root.querySelector('#das').checked,
    // Preserve the existing late-surrender setting contract.
    late_surrender: root.querySelector('#surrenderRule').checked,
    // Preserve the existing split-aces setting contract.
    split_aces_one_card: root.querySelector('#splitAces').checked,
  };
  // Mark the UI busy while the settings request is in flight.
  actionBusy = true;
  // Render stable disabled controls during the request.
  render();
  // Start protected settings handling so conflicts become toasts.
  try {
    // Post rule changes through the frozen v1 settings endpoint.
    const payload = await post(`${API_ROOT}/settings`, withCurrentPlayer(body));
    // Store the returned state snapshot.
    state = payload.state;
    // Keep the selected or latest round visible after rule changes.
    activeRoundId = findActiveRoundId();
    // Render the updated rules.
    render();
    // Show localized success feedback.
    toast(T('toast.rulesSaved'), true);
  // Handle public API validation or conflict errors.
  } catch (error) {
    // Show the API-provided message in the shell toast.
    toast(error.message);
  // Run cleanup after success or failure.
  } finally {
    // Clear the busy flag so controls recover after the request.
    actionBusy = false;
    // Rerender after failures as well so disabled states match current state.
    render();
  }
}

// Define cardRank so UI legality mirrors engine card-value rules.
function cardRank(card) {
  // Return the hidden marker for absent or hidden cards.
  if (!card || card === '??') return '??';
  // Return object cards defensively for future payload compatibility.
  if (typeof card === 'object') return card.rank || '??';
  // Return every character except the suit.
  return String(card).slice(0, -1);
}

// Define cardValue so split legality can be shown before the API validates it.
function cardValue(card) {
  // Store rank so face-card and ace handling stays in one place.
  const rank = cardRank(card);
  // Branch when an ace has blackjack value eleven for split comparisons.
  if (rank === 'A') return 11;
  // Branch when a face card has blackjack value ten.
  if (['J', 'Q', 'K'].includes(rank)) return 10;
  // Return the numeric value or zero for hidden cards.
  return Number(rank) || 0;
}

// Define handTotal so the UI can label hard, soft, blackjack, and bust hands.
function handTotal(cards = []) {
  // Store visible cards so hidden dealer cards do not affect player-visible totals.
  const visible = cards.filter(card => card && card !== '??');
  // Store raw values before ace adjustment.
  const values = visible.map(cardValue);
  // Store total so ace adjustments can lower it.
  let total = values.reduce((sum, value) => sum + value, 0);
  // Store ace count for blackjack soft-total adjustment.
  let aces = visible.filter(card => cardRank(card) === 'A').length;
  // Reduce aces from eleven to one while the hand is over twenty-one.
  while (total > 21 && aces) {
    // Lower the total by ten for one ace.
    total -= 10;
    // Mark one ace as adjusted.
    aces -= 1;
  }
  // Store hard total so soft status can be identified after adjustments.
  const hardTotal = visible.reduce((sum, card) => sum + (cardRank(card) === 'A' ? 1 : cardValue(card)), 0);
  // Store soft so the rendered hint matches Blackjack convention.
  const soft = visible.some(card => cardRank(card) === 'A') && hardTotal + 10 <= 21;
  // Return the display total metadata.
  return { total, soft, blackjack: visible.length === 2 && total === 21, bust: total > 21 };
}

// Define visibleActionCount so action history can ignore split setup markers.
function visibleActionCount(hand = {}) {
  // Return the count of player decisions after removing engine split markers.
  return (hand.actions || []).filter(action => action !== 'split').length;
}

// Define canDouble so the button affordance mirrors the engine rules.
function canDouble(roundItem, hand, rules) {
  // Branch when no active two-card hand exists.
  if (!roundItem || !hand || hand.cards?.length !== 2) return false;
  // Branch when the player already acted on this hand.
  if (visibleActionCount(hand)) return false;
  // Branch when double-after-split is disabled for split hands.
  if (hand.is_split_hand && !rules.double_after_split) return false;
  // Branch when split aces are locked by table rule.
  if (hand.split_aces_locked) return false;
  // Return true when all public engine preconditions are represented.
  return true;
}

// Define canSplit so the button affordance mirrors the engine rules.
function canSplit(roundItem, hand, rules) {
  // Branch when no active two-card hand exists.
  if (!roundItem || !hand || hand.cards?.length !== 2) return false;
  // Branch when equal blackjack values are not present.
  if (cardValue(hand.cards[0]) !== cardValue(hand.cards[1])) return false;
  // Branch when max split hands has already been reached.
  if ((roundItem.hands || []).length >= Number(rules.max_split_hands || FALLBACK_MAX_HANDS)) return false;
  // Return true when all public engine preconditions are represented.
  return true;
}

// Define canSurrender so the button affordance mirrors the engine rules.
function canSurrender(roundItem, hand, rules) {
  // Branch when surrender is disabled at the table.
  if (!rules.late_surrender) return false;
  // Branch when no active two-card hand exists.
  if (!roundItem || !hand || hand.cards?.length !== 2) return false;
  // Return true only before a non-split player action is taken.
  return visibleActionCount(hand) === 0;
}

// Define canInsurance so the button affordance mirrors the public API validation.
function canInsurance(roundItem) {
  // Branch when no active round exists.
  if (!roundItem || roundItem.status !== 'player_turn') return false;
  // Branch when insurance has already been purchased.
  if (roundItem.insurance) return false;
  // Return true only when the dealer shows an Ace.
  return cardRank(roundItem.dealer?.cards?.[0]) === 'A';
}

// Define canEvenMoney so the button affordance mirrors the public API validation.
function canEvenMoney(roundItem) {
  // Branch when no active round exists.
  if (!roundItem || roundItem.status !== 'player_turn') return false;
  // Branch when even money has already been taken.
  if (roundItem.even_money) return false;
  // Store the first hand total because even money is tied to a natural blackjack.
  const firstHand = roundItem.hands?.[0];
  // Return true only for player blackjack against a dealer Ace.
  return handTotal(firstHand?.cards || []).blackjack && cardRank(roundItem.dealer?.cards?.[0]) === 'A';
}

// Define actionState so action buttons stay mounted with correct enabled styling.
function actionState(roundItem = currentRound()) {
  // Store rules so action legality can use table settings.
  const rules = state?.rules || {};
  // Store hand so legal checks refer to one active hand.
  const hand = activeHand(roundItem);
  // Store active so hit/stand do not enable outside player turns.
  const active = Boolean(roundItem && hand && roundItem.status === 'player_turn');
  // Return a normalized legality map for all mounted controls.
  return {
    // Hit is legal for active hands that are not split-ace locked.
    hit: active && !hand.split_aces_locked,
    // Stand is legal for every active hand.
    stand: active,
    // Double follows the engine's first-action and split-rule constraints.
    double: active && canDouble(roundItem, hand, rules),
    // Split follows equal-value and max-hand constraints.
    split: active && canSplit(roundItem, hand, rules),
    // Surrender follows the late-surrender rule and first-action constraint.
    surrender: active && canSurrender(roundItem, hand, rules),
    // Insurance follows dealer-Ace and one-purchase constraints.
    insurance: canInsurance(roundItem),
    // Even money follows natural-blackjack and dealer-Ace constraints.
    evenMoney: canEvenMoney(roundItem),
  };
}

// Define insuranceAmount so the API body never exceeds the public maximum.
function insuranceAmount(roundItem = currentRound()) {
  // Store first hand bet as the source wager for insurance.
  const bet = Number(roundItem?.hands?.[0]?.bet || betAmount || 0);
  // Return half the original wager with a minimum positive amount for the endpoint.
  return Math.max(1, Math.round((bet / 2) * 100) / 100);
}

// Define rulesLocked so table settings match the backend conflict behavior.
function rulesLocked(roundItem = currentRound()) {
  // Return true while a player-turn or pending-credit round still exists.
  return Boolean(roundItem && ['player_turn', 'settled_pending_credit'].includes(roundItem.status));
}

// Define canDeal so the Deal button remains mounted but disabled during active rounds.
function canDeal(roundItem = currentRound()) {
  // Return false while an unfinished round is visible.
  return !roundItem || !['player_turn', 'settled_pending_credit'].includes(roundItem.status);
}

// Define payoutLabel so payout settings render as casino table shorthand.
function payoutLabel(value) {
  // Store numeric payout so string comparisons are not brittle.
  const payout = Number(value || 1.5);
  // Branch for the standard three-to-two payout.
  if (payout === 1.5) return '3:2';
  // Branch for the six-to-five payout.
  if (payout === 1.2) return '6:5';
  // Branch for the even-money payout.
  if (payout === 1) return '1:1';
  // Return the raw configured payout when a future value appears.
  return formatNumber(payout, { maximumFractionDigits: 2 });
}

// Define statusLabel so backend status tokens become localized display text.
function statusLabel(status) {
  // Return a localized status string or the raw token fallback.
  return T(`status.${status || 'none'}`);
}

// Define outcomeLabel so backend outcome tokens become localized display text.
function outcomeLabel(outcome) {
  // Return a localized outcome string or pending text when none is present.
  return outcome ? T(`outcome.${outcome}`) : T('outcome.pending');
}

// Define totalLabel so hard, soft, blackjack, and bust states are easy to scan.
function totalLabel(cards = []) {
  // Store computed hand metadata.
  const total = handTotal(cards);
  // Branch when the hand is a natural blackjack.
  if (total.blackjack) return T('hand.blackjack');
  // Branch when the hand is bust.
  if (total.bust) return T('hand.bust', { total: total.total });
  // Branch when the hand is soft.
  if (total.soft) return T('hand.soft', { total: total.total });
  // Return a hard-total label for all other hands.
  return T('hand.hard', { total: total.total });
}

// Define dealerLabel so hidden hole cards do not expose hidden totals.
function dealerLabel(roundItem) {
  // Branch when no round has been dealt.
  if (!roundItem) return T('dealer.waiting');
  // Store dealer cards defensively.
  const cards = roundItem.dealer?.cards || [];
  // Branch when the hole card is hidden by the public API payload.
  if (cards.includes('??')) return T('dealer.shows', { rank: cardRank(cards[0]) });
  // Return the visible dealer total after settlement.
  return totalLabel(cards);
}

// Define roundTitle so the central stage mirrors the current game phase.
function roundTitle(roundItem) {
  // Branch when the table is waiting for a deal.
  if (!roundItem) return T('stage.ready');
  // Branch when a settled round is visible.
  if (roundItem.status === 'settled') return T('stage.settled');
  // Branch when split or resplit hands are visible.
  if ((roundItem.hands || []).length > 1) return T('stage.splitHands');
  // Branch when insurance or even-money affordances are available.
  if (canInsurance(roundItem) || canEvenMoney(roundItem)) return T('stage.activeDecision');
  // Return the initial-deal title for the normal player-turn state.
  return T('stage.initialDeal');
}

// Define tableLogoText so the felt center reflects the current special state.
function tableLogoText(roundItem) {
  // Branch when insurance is currently available.
  if (canInsurance(roundItem)) return [T('felt.insurance'), T('felt.available')];
  // Branch when the visible round is settled.
  if (roundItem?.status === 'settled') return [T('felt.settlement'), T('felt.complete')];
  // Return the standard Blackjack table logo.
  return [T('felt.blackjack'), T('felt.pays', { payout: payoutLabel(state?.rules?.blackjack_payout) })];
}

// Define totalWager so the drawer can summarize split and double wagers.
function totalWager(roundItem) {
  // Return the sum of all visible hand bets.
  return (roundItem?.hands || []).reduce((sum, hand) => sum + Number(hand.bet || 0), 0);
}

// Define handReturn so settlement rows can show the credited amount.
function handReturn(hand) {
  // Return payout due when present, otherwise zero for pending hands.
  return Number(hand?.payout_due || 0);
}

// Define insuranceNet so settlement reflects the insurance side bet's stake and payout. (issue #260)
function insuranceNet(roundItem) {
  // Read the settled insurance side bet, absent on rounds where insurance was not taken.
  const insurance = roundItem?.insurance;
  // Return no movement when the round carried no insurance wager.
  if (!insurance) return 0;
  // Return the credited insurance payout minus the debited insurance stake.
  return Number(insurance.payout || 0) - Number(insurance.amount || 0);
}

// Define netSettlement so the drawer can show a compact settled outcome.
function netSettlement(roundItem) {
  // Store total returns from all hands.
  const returns = (roundItem?.hands || []).reduce((sum, hand) => sum + handReturn(hand), 0);
  // Return net against visible hand wagers plus the insurance side bet net so the row matches the wallet. (issue #260)
  return returns - totalWager(roundItem) + insuranceNet(roundItem);
}

// Define actionButtonHtml so the action rail always uses one stable button grid.
function actionButtonHtml(action, legal) {
  // Store enabled so busy requests and inactive rounds disable controls without unmounting them.
  const enabled = Boolean(legal[action.id] && !actionBusy);
  // Store classes so enabled premium controls receive the gold treatment.
  const classes = enabled ? 'gold' : '';
  // Return a mounted action button with stable selector coverage.
  return `<button class="${classes}" data-action="${action.id}" data-testid="${action.testid}" ${enabled ? '' : 'disabled'}>${safe(T(action.label))}</button>`;
}

// Define metricHtml so rail and drawer metrics share consistent markup.
function metricHtml(label, value, extraClass = '') {
  // Return a compact two-column metric row.
  return `<div class="mini-stat ${extraClass}"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`;
}

// Define ruleSummaryHtml so important table rules stay visible even while controls scroll.
function ruleSummaryHtml(rules) {
  // Store rules text in the same order as the prerender.
  const items = [
    // Show deck count.
    T('rules.decksValue', { decks: formatNumber(rules.decks || 6) }),
    // Show blackjack payout.
    T('rules.payoutValue', { payout: payoutLabel(rules.blackjack_payout) }),
    // Show double-after-split state.
    rules.double_after_split ? T('rules.dasOn') : T('rules.dasOff'),
    // Show late-surrender state.
    rules.late_surrender ? T('rules.surrenderOn') : T('rules.surrenderOff'),
  ];
  // Return a compact stable vertical list so control-plane panels remain reachable.
  return `<div class="result-box" style="display:grid;gap:6px;">${items.map(item => `<span class="badge" style="display:block;text-align:center;">${safe(item)}</span>`).join('')}</div>`;
}

// Define autoplayPanelHtml so Blackjack explicitly remains manual per AUTO-014.
function autoplayPanelHtml(roundItem) {
  // Store current text from the visible table phase.
  const detail = roundItem?.status === 'settled' ? T('autoplay.settled') : T('autoplay.disabled');
  // Return a disabled control-plane panel without registering an autoplay session.
  return `<div class="autoplay" data-testid="blackjack-autoplay-panel"><div class="row"><h3>${safe(T('autoplay.title'))}</h3><span class="badge">${safe(T('autoplay.off'))}</span></div><p class="muted">${safe(detail)}</p></div>`;
}

// Define supportPanelHtml so the player can see stateful table support without layout churn.
function supportPanelHtml(roundItem) {
  // Store rules lock text from the actual backend conflict state.
  const lockText = rulesLocked(roundItem) ? T('support.rulesLocked') : T('support.rulesOpen');
  // Store active hand text for split queues.
  const handText = roundItem ? T('support.activeHand', { active: formatNumber((roundItem.active_hand_index || 0) + 1), total: formatNumber((roundItem.hands || []).length || 1) }) : T('support.noRound');
  // Return a stable support panel with shoe and rule status.
  return `<div class="result-box" data-testid="blackjack-support-panel"><h3>${safe(T('support.title'))}</h3>${metricHtml(T('drawer.shoe'), T('drawer.cards', { count: formatNumber(state?.shoe_count || 0) }))}${metricHtml(T('support.rules'), lockText)}${metricHtml(T('drawer.activeHand'), handText)}</div>`;
}

// Define botPanelHtml so Blackjack shows compatible bot state without importing strategies.
function botPanelHtml() {
  // Store capabilities defensively from the cached public payload.
  const capabilities = botCapabilities?.capabilities || {};
  // Branch when Blackjack has no compatible bot controller.
  if (!capabilities.supports_bots) return `<div class="bot-panel" data-testid="blackjack-bot-panel"><h3>${safe(T('bots.title'))}</h3><p class="muted">${safe(T('bots.none'))}</p></div>`;
  // Store rows for eligible bot controllers if the server later enables a strategy.
  const rows = (botCapabilities.bots || []).map(bot => `<tr><td>${safe(bot.display_name || bot.bot_id)}</td><td>${safe(bot.strategy_id || T('bots.noStrategy'))}</td><td>${localMoney(bot.stake || 0)}</td><td>${localMoney(bot.balance || 0)}</td></tr>`).join('');
  // Return the compatible bot table with stable selectors.
  return `<div class="bot-panel" data-testid="blackjack-bot-panel"><h3>${safe(T('bots.title'))}</h3><table class="mini-table"><tr><th>${safe(T('bots.bot'))}</th><th>${safe(T('bots.strategy'))}</th><th>${safe(T('bots.stake'))}</th><th>${safe(T('bots.balance'))}</th></tr>${rows || `<tr><td colspan="4">${safe(T('bots.empty'))}</td></tr>`}</table></div>`;
}

// Define renderBotPanelIntoDom so async bot loading does not rerender the whole game.
function renderBotPanelIntoDom() {
  // Read the current bot panel host from the rail.
  const host = root?.querySelector('#botPanel');
  // Replace only the bot panel contents when the host exists.
  if (host) host.innerHTML = botPanelHtml();
}

// Define renderControls so betting, rules, actions, bot, autoplay, and support stay in one rail.
function renderControls(roundItem) {
  // Store rules with defaults so controls always have values.
  const rules = state?.rules || {};
  // Store legality for all mounted action buttons.
  const legal = actionState(roundItem);
  // Store lock state so rules controls match backend behavior.
  const locked = rulesLocked(roundItem) || actionBusy;
  // Return the complete left control rail.
  return `<section class="panel control-rail" data-testid="blackjack-control-rail"><h2 class="game-title">${safe(T('title'))}</h2><label>${safe(T('bet.amount'))}<input id="bjBet" data-testid="blackjack-bet" type="number" min="1" value="${safe(betAmount)}" ${canDeal(roundItem) ? '' : 'disabled'}></label><button id="deal" data-testid="blackjack-deal" class="primary" ${canDeal(roundItem) && !actionBusy ? '' : 'disabled'}>${safe(roundItem?.status === 'settled' ? T('controls.dealNext') : T('controls.deal'))}</button><h3>${safe(T('controls.actions'))}</h3><div class="grid2 action-row" data-testid="blackjack-action-rail">${ACTIONS.map(action => actionButtonHtml(action, legal)).join('')}</div><h3>${safe(T('rules.title'))}</h3>${ruleSummaryHtml(rules)}<details ${locked ? '' : 'open'}><summary>${safe(T('rules.configure'))}</summary><div class="grid2"><label>${safe(T('rules.decks'))}<input id="decks" type="number" min="1" max="8" value="${safe(rules.decks || 6)}" ${locked ? 'disabled' : ''}></label><label>${safe(T('rules.maxHands'))}<input id="maxSplitHands" type="number" min="1" max="4" value="${safe(rules.max_split_hands || FALLBACK_MAX_HANDS)}" ${locked ? 'disabled' : ''}></label><label>${safe(T('rules.payout'))}<select id="bjPay" ${locked ? 'disabled' : ''}><option value="1.5">3:2</option><option value="1.2">6:5</option><option value="1">1:1</option></select></label></div><label><input id="h17" type="checkbox" ${rules.dealer_hits_soft_17 ? 'checked' : ''} ${locked ? 'disabled' : ''}> ${safe(T('rules.h17'))}</label><label><input id="das" type="checkbox" ${rules.double_after_split ? 'checked' : ''} ${locked ? 'disabled' : ''}> ${safe(T('rules.das'))}</label><label><input id="surrenderRule" type="checkbox" ${rules.late_surrender ? 'checked' : ''} ${locked ? 'disabled' : ''}> ${safe(T('rules.lateSurrender'))}</label><label><input id="splitAces" type="checkbox" ${rules.split_aces_one_card ? 'checked' : ''} ${locked ? 'disabled' : ''}> ${safe(T('rules.splitAces'))}</label><button id="saveRules" ${locked ? 'disabled' : ''}>${safe(T('rules.save'))}</button></details>${autoplayPanelHtml(roundItem)}<div id="botPanel">${botPanelHtml()}</div>${supportPanelHtml(roundItem)}</section>`;
}

// Define renderDealer so dealer cards stay in a fixed top lane.
function renderDealer(roundItem) {
  // Store dealer cards or placeholders for the idle state.
  const cards = roundItem?.dealer?.cards || [];
  // Store rendered card markup with a fixed minimum lane height.
  const renderedCards = cards.length ? cards.map(cardHtml).join('') : '<div class="playing-card placeholder">?</div><div class="playing-card placeholder">?</div>';
  // Return the dealer lane.
  return `<div class="hand" data-testid="blackjack-dealer" style="max-width:440px;margin:0 auto;min-height:138px;"><div class="row"><b>${safe(T('dealer.title'))}</b><span class="badge">${safe(dealerLabel(roundItem))}</span>${roundItem?.dealer?.cards?.includes('??') ? `<span class="badge">${safe(T('dealer.hidden'))}</span>` : ''}</div><div class="cards card-row-fixed">${renderedCards}</div></div>`;
}

// Define handClasses so active and settled hands have consistent visual emphasis.
function handClasses(roundItem, hand, index) {
  // Store class names in an array for safe joining.
  const classes = ['hand'];
  // Add active styling to the current actionable hand.
  if (roundItem?.active_hand_index === index && hand.status === 'active' && roundItem.status === 'player_turn') classes.push('active');
  // Add a semantic class for winning settled hands.
  if (['win', 'blackjack'].includes(hand.outcome)) classes.push('won-hand');
  // Add a semantic class for resolved non-active hands.
  if (hand.status !== 'active') classes.push('resolved-hand');
  // Return the class list.
  return classes.join(' ');
}

// Define handBadgeText so each lane shows phase, total, or settlement at a glance.
function handBadgeText(hand) {
  // Branch when a hand has a final outcome.
  if (hand.outcome) return outcomeLabel(hand.outcome);
  // Branch when the hand status is no longer active.
  if (hand.status && hand.status !== 'active') return statusLabel(hand.status);
  // Return the live hand total for active decisions.
  return totalLabel(hand.cards || []);
}

// Define renderHand so player hands use a stable lane with cards, status, and wager.
function renderHand(roundItem, hand, index) {
  // Store return text for settled hands.
  const returnText = hand.payout_due === undefined ? '' : `<span class="badge">${safe(T('hand.return', { amount: localMoney(handReturn(hand)) }))}</span>`;
  // Store active hand label.
  const handLabel = T('hand.label', { number: formatNumber(index + 1) });
  // Return one player hand lane.
  return `<div class="${handClasses(roundItem, hand, index)}" data-testid="blackjack-hand-${index}" style="min-height:176px;"><div class="row"><b>${safe(handLabel)}</b><span class="badge">${safe(handBadgeText(hand))}</span><span class="badge">${safe(T('hand.bet', { amount: localMoney(hand.bet || 0) }))}</span>${returnText}</div><div class="cards card-row-fixed">${(hand.cards || []).map(cardHtml).join('')}</div></div>`;
}

// Define renderHandGrid so split hands can expand inside a reserved stage area.
function renderHandGrid(roundItem) {
  // Store hands from the current round or an empty list for the idle state.
  const hands = roundItem?.hands || [];
  // Branch when the player has not dealt yet.
  if (!hands.length) return `<div class="result-box fixed-result" data-testid="blackjack-empty-hands">${safe(T('stage.dealPrompt'))}</div>`;
  // Store responsive columns so many hands fit inside the stage without moving rails.
  const columns = hands.length > 1 ? 'repeat(auto-fit, minmax(210px, 1fr))' : 'minmax(260px, 430px)';
  // Return the stable hand grid.
  return `<div data-testid="blackjack-hand-grid" style="display:grid;grid-template-columns:${columns};gap:12px;justify-content:center;align-items:stretch;min-height:198px;">${hands.map((hand, index) => renderHand(roundItem, hand, index)).join('')}</div>`;
}

// Define renderFelt so the central stage mirrors the approved premium table geometry.
function renderFelt(roundItem) {
  // Store felt logo text for current phase.
  const [logo, sublogo] = tableLogoText(roundItem);
  // Return the fixed central play stage.
  return `<section class="panel game-stage" data-testid="blackjack-stage"><div class="row action-row"><div style="margin-right:auto"><span class="badge" data-testid="blackjack-round-id" data-round-id="${safe(roundItem?.round_id || '')}">${safe(roundItem ? T('stage.round', { id: roundItem.round_id }) : T('stage.noRound'))}</span><h2 style="margin:8px 0 0">${safe(roundTitle(roundItem))}</h2></div><span class="badge" data-game-live-status data-testid="blackjack-stage-status">${safe(statusLabel(roundItem?.status))}</span></div><div class="result-box" data-testid="blackjack-felt" style="display:grid;grid-template-rows:auto 1fr auto;gap:16px;min-height:560px;padding:16px;background:linear-gradient(135deg, rgba(35,17,61,.82), rgba(21,10,36,.9));border-color:var(--gold);">${renderDealer(roundItem)}<div style="display:grid;place-items:center;min-height:118px;"><div class="result-box" style="display:grid;place-items:center;width:min(70%,310px);min-height:96px;border-radius:50%;text-align:center;color:var(--text);"><b>${safe(logo)}</b><span class="muted">${safe(sublogo)}</span></div></div>${renderHandGrid(roundItem)}</div></section>`;
}

// Define decisionRowsHtml so the drawer exposes legal action affordances in text form.
function decisionRowsHtml(roundItem) {
  // Store legal action map.
  const legal = actionState(roundItem);
  // Return rows in the same order as mounted controls.
  return ACTIONS.map(action => `<div class="bet-item"><span>${safe(T(action.label))}</span><b>${safe(legal[action.id] ? T('decision.available') : T('decision.blocked'))}</b><span>${safe(action.id === 'insurance' ? localMoney(insuranceAmount(roundItem)) : '')}</span></div>`).join('');
}

// Define settlementRowsHtml so hand outcomes stay pinned in the drawer after settlement.
function settlementRowsHtml(roundItem) {
  // Store hands from the visible round.
  const hands = roundItem?.hands || [];
  // Branch when there are no hands to summarize.
  if (!hands.length) return `<p class="muted">${safe(T('drawer.noSettlements'))}</p>`;
  // Return one settlement row per hand.
  return hands.map((hand, index) => `<div class="bet-item"><span>${safe(T('hand.label', { number: formatNumber(index + 1) }))}</span><b>${safe(outcomeLabel(hand.outcome))}</b><span>${safe(localMoney(handReturn(hand)))}</span></div>`).join('');
}

// Define recentRoundsHtml so the drawer history can scroll without moving the table.
function recentRoundsHtml() {
  // Store recent rounds newest-first.
  const recent = rounds().slice(-10).reverse();
  // Branch when no rounds have been played.
  if (!recent.length) return `<p class="muted">${safe(T('history.empty'))}</p>`;
  // Return recent round rows.
  return recent.map(roundItem => `<div class="bet-item"><span>${safe(roundItem.round_id)}</span><b>${safe(statusLabel(roundItem.status))}</b><span>${safe(T('history.hands', { count: formatNumber((roundItem.hands || []).length) }))}</span></div>`).join('');
}

// Define renderDrawer so shoe, decisions, settlement, and history stay in a fixed drawer.
function renderDrawer(roundItem) {
  // Store active hand position for split queues.
  const activeText = roundItem ? T('support.activeHand', { active: formatNumber((roundItem.active_hand_index || 0) + 1), total: formatNumber((roundItem.hands || []).length || 1) }) : T('support.noRound');
  // Store net text only when a settled round is visible.
  const netText = roundItem?.status === 'settled' ? signedLocalMoney(netSettlement(roundItem)) : T('drawer.pending');
  // Return the full drawer content.
  return `<section class="panel details-drawer" data-testid="blackjack-drawer"><h2 class="game-title">${safe(roundItem?.status === 'settled' ? T('drawer.settlement') : T('drawer.round'))}</h2>${metricHtml(T('drawer.status'), statusLabel(roundItem?.status))}${metricHtml(T('drawer.shoe'), T('drawer.cards', { count: formatNumber(state?.shoe_count || 0) }))}${metricHtml(T('drawer.activeHand'), activeText)}${metricHtml(T('drawer.totalWager'), localMoney(totalWager(roundItem)))}${metricHtml(T('drawer.net'), netText)}<h3>${safe(roundItem?.status === 'settled' ? T('drawer.settlement') : T('decision.title'))}</h3><div class="stable-list">${roundItem?.status === 'settled' ? settlementRowsHtml(roundItem) : decisionRowsHtml(roundItem)}</div><h3>${safe(T('history.title'))}</h3><div class="scrollbox">${recentRoundsHtml()}</div></section>`;
}

// Define bindControls so the latest render wires controls without duplicating markup logic.
function bindControls() {
  // Store payout select so it can reflect the current rule.
  const payoutSelect = root.querySelector('#bjPay');
  // Set payout select value when the control is present.
  if (payoutSelect) payoutSelect.value = String(state?.rules?.blackjack_payout || 1.5);
  // Store bet input so user edits update cached state before rerenders.
  const betInput = root.querySelector('#bjBet');
  // Wire bet input changes into the cached bet amount.
  if (betInput) betInput.oninput = () => { betAmount = Number(betInput.value || betAmount || 25); };
  // Wire the Deal button through the public deal endpoint.
  root.querySelector('#deal')?.addEventListener('click', deal);
  // Wire every mounted action button through the public action endpoint.
  root.querySelectorAll('[data-action]').forEach(button => { button.onclick = () => act(button.dataset.action); });
  // Wire the Save Rules button through the public settings endpoint.
  root.querySelector('#saveRules')?.addEventListener('click', settings);
}

// Define render so every visible Blackjack surface is generated from current state only.
function render() {
  // Stop when the route has unmounted.
  if (!root) return;
  // Store the selected round for this render.
  const roundItem = currentRound();
  // Preserve the focused Blackjack control through the full-root render. (UX-025)
  const focus = captureGameFocus(root);
  // Replace the full Blackjack surface atomically so rails and drawers stay aligned.
  root.innerHTML = `<div class="game-layout three-col stable-game" data-testid="blackjack-premium">${renderControls(roundItem)}${renderFelt(roundItem)}${renderDrawer(roundItem)}</div>`;
  // Wire controls after markup is present.
  bindControls();
  // Restore focus and announce the authoritative round status. (UX-025)
  restoreGameFocus(root, focus); syncGameLiveStatus(root);
}

// Export this symbol so the app shell can mount Blackjack through the route registry.
export const BlackjackGame = {
  // Identify this game module for route diagnostics.
  id: 'blackjack',
  // Provide the shell label for this module.
  label: 'Blackjack',
  // Mount the module into the shared #view route outlet.
  async mount(node) {
    // Store the route outlet for later renders.
    root = node;
    // Subscribe to locale changes without reloading game state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Load resources and state before first interaction.
    await load();
  },
  // Unmount the module when the shell navigates away.
  unmount() {
    // Release the locale subscription if it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the subscription handle.
    unsubscribeLocale = null;
    // Drop the route outlet reference.
    root = null;
  },
};
