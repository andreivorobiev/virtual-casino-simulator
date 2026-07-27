// Isolated Four Card Poker browser module for GitHub issue #141 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/four_card_poker';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/four-card-poker';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'four-card-poker-styles';
// Preserve the Ante Bonus paytable order independently of object insertion behavior.
const ANTE_BONUS_ORDER = ['four_of_a_kind', 'straight_flush', 'three_of_a_kind'];
// Preserve the Aces Up paytable order independently of object insertion behavior.
const ACES_UP_ORDER = ['four_of_a_kind', 'straight_flush', 'three_of_a_kind', 'flush', 'straight', 'two_pair', 'pair_of_aces'];
// Offer the three documented play raise sizes.
const PLAY_MULTIPLIERS = [1, 2, 3];

// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for paytable displays.
let rules = {};
// Store the configured ante wager before the next round.
let ante = 5;
// Store the optional Aces Up wager before the next round.
let acesUp = 0;
// Prevent overlapping atomic browser actions.
let busy = false;
// Retain the last committed ante and Aces Up bet so one click can repeat the same wagers.
let lastBet = null;
// Store the locale cleanup callback so unmount releases subscriptions.
let unsubscribeLocale = null;
// Track mount generations so late network responses cannot revive an old route.
let mountGeneration = 0;
// Store a fallback retry-id counter for browsers without randomUUID support.
let requestCounter = 0;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealId = null;
// Bind the unresolved deal retry id to one ante and Aces Up payload.
let pendingDealContext = null;
// Retain an unresolved decision retry id independently from deal retries.
let pendingDecisionId = null;
// Bind the unresolved decision retry id to one round and selected decision.
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

// Install the shared card stylesheet without changing the global shell files.
function ensureSharedCardStyles() {
  // Reuse a stylesheet already installed by another card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create one standard stylesheet link for the shared renderer.
  const link = document.createElement('link');
  // Mark the link so future mounts remain idempotent.
  link.id = CARD_STYLE_ID;
  // Declare a normal stylesheet relationship for browser loading.
  link.rel = 'stylesheet';
  // Load the shared presentation hooks from the public core path.
  link.href = '/core/cards.css';
  // Add the shared stylesheet to document metadata once.
  document.head.append(link);
}

// Install compact route-local styles without modifying the shared stylesheet.
function ensureStyles() {
  // Skip installation when this route's styles are already present.
  if (document.getElementById(STYLE_ID)) return;
  // Create one style element scoped to this game.
  const style = document.createElement('style');
  // Tag the element so repeated mounts detect and reuse it.
  style.id = STYLE_ID;
  // Render only route-local selectors so no shared class is affected.
  style.textContent = '.fourcp{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .fcp-stage{display:grid;gap:16px;padding:12px;min-width:0;} .fcp-heading{margin:0;color:var(--gold);font-size:clamp(24px,3vw,38px);line-height:1.1;} .fcp-row{display:grid;gap:6px;} .fcp-row h4{margin:0;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .fcp-cards{display:flex;gap:6px;flex-wrap:wrap;min-width:0;} .fcp-hand{outline:2px solid var(--gold);outline-offset:3px;border-radius:8px;} .fcp-actions{display:flex;flex-wrap:wrap;gap:8px;} .fcp-btn{min-height:44px;padding:0 16px;border:none;border-radius:12px;font-weight:900;font-size:15px;cursor:pointer;} .fcp-btn.play{background:linear-gradient(180deg,#0f9c4c,#0a5f2e);color:#fff;} .fcp-btn.fold{background:linear-gradient(180deg,#6b6b76,#3a3a42);color:#fff;} .fcp-btn.deal{background:linear-gradient(180deg,#d6323d,#8e1822);color:#fff;width:100%;} .fcp-btn:disabled{opacity:.55;cursor:not-allowed;} .fcp-panel{display:grid;gap:12px;min-width:0;} .fcp-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .fcp-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .fcp-field{display:grid;gap:4px;margin-bottom:10px;} .fcp-field label{font-size:12px;font-weight:700;} .fcp-field input{min-height:40px;border-radius:10px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.05);color:var(--text);padding:0 10px;font-weight:800;} .fcp-pays{display:grid;gap:4px;font-size:12px;font-weight:700;} .fcp-pays div{display:flex;justify-content:space-between;} .fcp-pays span:last-child{color:var(--gold);} .fcp-result{min-height:24px;font-size:15px;color:var(--text);font-weight:800;} .fcp-result .net{font-weight:900;} @media (max-width:900px){.fourcp{grid-template-columns:1fr;}}.fcp-repeat{min-height:44px;padding:0 16px;border:1px solid var(--gold);border-radius:12px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.fcp-repeat:disabled{opacity:.5;cursor:not-allowed;}';
  // Attach the game-owned styles to the document head.
  document.head.append(style);
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

// Normalize a wager while preserving the allowed zero value for Aces Up.
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
  // Return the newest completed round, which the engine appends last.
  return recent.length ? recent[recent.length - 1] : null;
}

// Adopt one state-bearing API response and clear resolved retry ids.
function adoptPayload(payload) {
  // Replace cached player state only when the response includes it.
  if (payload?.state) state = payload.state;
  // Replace cached rules only when the response includes authoritative values.
  if (payload?.rules) rules = payload.rules;
  // Clear the pending deal id once the server confirms the round.
  if (payload?.round) {
    // Release the resolved deal retry binding.
    pendingDealId = null;
    // Release the resolved deal context.
    pendingDealContext = null;
  }
}

// Localize one card while keeping the shared renderer's structure.
function localizedCard(card, options = {}) {
  // Render face-down cards through the shared placeholder.
  return renderCard(card, options);
}

// Build the markup for one labelled row of cards.
function cardRow(titleKey, cards, options = {}) {
  // Render each card through the shared renderer.
  const rendered = (cards || []).map(card => localizedCard(card, options)).join('');
  // Return one titled card row.
  return `<div class="fcp-row"><h4>${safe(text(titleKey))}</h4><div class="fcp-cards ${options.hand ? 'fcp-hand' : ''}">${rendered}</div></div>`;
}

// Render the paytable rows for one to-one multiplier table.
function paytableRows(order, table) {
  // Build one row per listed category present in the authoritative table.
  return order.filter(name => table && table[name] !== undefined).map(name => `<div><span>${safe(text('hand.' + name))}</span><span>${table[name]}:1</span></div>`).join('');
}

// Render the complete Four Card Poker route into the outlet.
function render() {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the newest round to decide which stage to present.
  const round = currentRound();
  // Determine whether a decision is awaited.
  const deciding = round && round.phase === 'decision';
  // Build the stage markup for the current phase.
  const stage = deciding ? decisionStage(round) : round && round.phase === 'settled' ? settledStage(round) : idleStage();
  // Build the locale-owned route heading required for accessible page identification.
  const heading = `<h1 class="fcp-heading">${safe(text('title'))}</h1>`;
  // Build the side panel with wager inputs and paytables.
  const panel = sidePanel(deciding);
  // Paint the whole route.
  root.innerHTML = `<section class="fourcp" data-testid="four-card-poker"><div class="fcp-stage">${heading}${stage}</div><div class="fcp-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set wagers and deal.
  return `<p class="fcp-result" data-testid="four-card-poker-result">${safe(text('result.idle'))}</p>`;
}

// Build the decision stage showing the player's five cards and the play or fold controls.
function decisionStage(round) {
  // Render the five player cards for the pending decision.
  const cards = cardRow('label.your_cards', round.player_cards);
  // Build one play button per raise multiplier.
  const plays = PLAY_MULTIPLIERS.map(multiplier => `<button class="fcp-btn play" data-play="${multiplier}" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.play', { multiplier }))}</button>`).join('');
  // Return the cards, the fold control, and the play controls.
  return `${cards}<p class="fcp-result">${safe(text('result.decide'))}</p><div class="fcp-actions"><button class="fcp-btn fold" data-fold="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.fold'))}</button>${plays}</div>`;
}

// Build the settled stage revealing both hands and the result.
function settledStage(round) {
  // Render the player's revealed best-four hand.
  const player = cardRow('label.your_cards', (round.player_hand && round.player_hand.cards) || round.player_cards, { hand: true });
  // Render the dealer's revealed cards when a showdown happened.
  const dealer = round.dealer_cards ? cardRow('label.dealer_cards', round.dealer_cards) : '';
  // Compose the localized outcome and net line.
  const net = round.net || 0;
  // Build the outcome result line with a signed net amount.
  const line = `${safe(text('outcome.' + round.outcome))} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Enable the one-click repeat only when a prior bet exists and nothing is in flight.
  const repeatDisabled = busy || !lastBet;
  // Return the revealed hands, the result, a deal-again control, and a one-click repeat.
  return `${player}${dealer}<p class="fcp-result" data-testid="four-card-poker-result">${line}</p><div class="fcp-actions"><button class="fcp-btn deal" data-deal="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.deal_again'))}</button><button type="button" class="fcp-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(text('controls.repeat'))}</button></div>`;
}

// Build the side panel with wager inputs and paytables.
function sidePanel(deciding) {
  // Hide the wager inputs while a decision is pending.
  const wagerCard = deciding ? '' : `<div class="fcp-card"><h3>${safe(text('label.wagers'))}</h3><div class="fcp-field"><label for="fcp-ante">${safe(text('label.ante'))}</label><input id="fcp-ante" data-ante type="number" min="1" step="1" value="${ante}"></div><div class="fcp-field"><label for="fcp-aces">${safe(text('label.aces_up'))}</label><input id="fcp-aces" data-aces type="number" min="0" step="1" value="${acesUp}"></div><button class="fcp-btn deal" data-deal="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.deal'))}</button></div>`;
  // Build the Ante Bonus paytable card.
  const anteBonus = `<div class="fcp-card"><h3>${safe(text('label.ante_bonus'))}</h3><div class="fcp-pays">${paytableRows(ANTE_BONUS_ORDER, rules.ante_bonus_multipliers)}</div></div>`;
  // Build the Aces Up paytable card.
  const acesTable = `<div class="fcp-card"><h3>${safe(text('label.aces_up'))}</h3><div class="fcp-pays">${paytableRows(ACES_UP_ORDER, rules.aces_up_multipliers)}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${anteBonus}${acesTable}`;
}

// Attach event handlers to the current stage controls.
function bindEvents() {
  // Bind the ante input to the cached wager.
  const anteInput = root.querySelector('[data-ante]');
  // Update the cached ante on input.
  if (anteInput) anteInput.onchange = () => { ante = normalizedWager(anteInput.value, 1); };
  // Bind the Aces Up input to the cached side bet.
  const acesInput = root.querySelector('[data-aces]');
  // Update the cached Aces Up bet on input, allowing zero.
  if (acesInput) acesInput.onchange = () => { acesUp = normalizedWager(acesInput.value, 0); };
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the one-click repeat that re-opens a round with the previous wagers.
  const repeatButton = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler when the control is present.
  if (repeatButton) repeatButton.onclick = repeat;
  // Bind the fold control to a fold decision.
  const foldButton = root.querySelector('[data-fold]');
  // Attach the fold handler.
  if (foldButton) foldButton.onclick = () => decide('fold', 1);
  // Bind every play control to a play decision at its multiplier.
  root.querySelectorAll('[data-play]').forEach(button => { button.onclick = () => decide('play', Number(button.dataset.play)); });
}

// Run one guarded atomic action while blocking overlapping requests.
async function runAction(worker) {
  // Ignore repeated actions while one is already resolving.
  if (busy || !root) return;
  // Capture the mount generation so a stale response cannot revive the route.
  const generation = mountGeneration;
  // Mark the route busy and disable controls.
  busy = true;
  render();
  // Execute the protected worker and always release the guard.
  try {
    // Perform the network action.
    await worker();
  } catch (error) {
    // Surface a bounded error to the player.
    if (generation === mountGeneration) toast(error?.message || text('error.action'), 'error');
  } finally {
    // Release the guard only for the still-mounted route.
    if (generation === mountGeneration) {
      // Clear the busy flag.
      busy = false;
      // Repaint the refreshed state.
      render();
      // Refresh the shell wallet after any settlement.
      await refreshBalance();
    }
  }
}

// Deal one new round after committing the ante and Aces Up wagers.
function deal() {
  // Perform the deal as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved deal id or mint a fresh one bound to the current wagers.
    if (!pendingDealId || pendingDealContext?.ante !== ante || pendingDealContext?.aces_up !== acesUp) {
      // Mint a fresh deal retry id.
      pendingDealId = nextActionId('fcp-deal');
      // Bind the retry id to the exact wagers.
      pendingDealContext = { ante, aces_up: acesUp };
    }
    // Post the exactly-once deal with the current wagers.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, ante, aces_up: acesUp }));
    // Adopt the returned state and reveal the decision stage.
    adoptPayload(payload);
  });
}

// Re-apply the last committed wagers and open one identical round without a timer.
async function repeat() {
  // Read the newest round so an active decision blocks the repeat.
  const round = currentRound();
  // Ignore repeat while busy, unmounted, before any bet exists, or during a pending decision.
  if (busy || !root || !lastBet || (round && round.phase === 'decision')) return;
  // Restore the committed ante into the cached wager the deal reads.
  ante = lastBet.ante;
  // Restore the committed Aces Up side bet into the cached wager the deal reads.
  acesUp = lastBet.aces_up;
  // Fire the shared deal action with the restored wagers, never replaying a decision.
  await deal();
}

// Apply one play or fold decision to the active round.
function decide(decision, multiplier) {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore decisions when no active round awaits one.
  if (!round || round.phase !== 'decision') return;
  // Perform the decision as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved decision id or mint one bound to this exact decision.
    if (!pendingDecisionId || pendingDecisionContext?.round_id !== round.round_id || pendingDecisionContext?.decision !== decision || pendingDecisionContext?.multiplier !== multiplier) {
      // Mint a fresh decision retry id.
      pendingDecisionId = nextActionId('fcp-decision');
      // Bind the retry id to the exact round and decision.
      pendingDecisionContext = { round_id: round.round_id, decision, multiplier };
    }
    // Post the exactly-once decision to the round-scoped route.
    const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionId, decision, multiplier }));
    // Adopt the settled result.
    adoptPayload(payload);
    // Capture the committed wagers from the settled round so one click can repeat them.
    const settled = currentRound();
    // Remember the ante and Aces Up bet only when the round exposes its committed wagers.
    if (settled && settled.ante !== undefined) lastBet = { ante: settled.ante, aces_up: settled.aces_up };
    // Release the resolved decision retry binding.
    pendingDecisionId = null;
    // Release the resolved decision context.
    pendingDecisionContext = null;
  });
}

// Export the isolated Four Card Poker game for the shared shell.
export const FourCardPokerGame = {
  // Expose the stable catalog identifier.
  id: 'four_card_poker',
  // Expose an empty label because the shell provides the localized catalog label.
  label: '',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Advance the mount generation so late responses from a prior mount are ignored.
    mountGeneration += 1;
    // Store the current route outlet.
    root = node;
    // Reset the repeatable wagers so a new session never inherits a prior bet.
    lastBet = null;
    // Install shared and route-local styles.
    ensureSharedCardStyles();
    // Install the compact route-local styles.
    ensureStyles();
    // Capture the generation for guarding the async load.
    const generation = mountGeneration;
    // Load both locales through the game-owned lazy domain before visible render.
    await loadI18nDomain(DOMAIN);
    // Stop when the route was replaced during locale loading.
    if (generation !== mountGeneration) return;
    // Repaint localized strings on a locale change unless an action owns the table.
    unsubscribeLocale = onLocaleChange(() => { if (!busy) render(); });
    // Read reload-safe state so a pending decision or settled result is restored.
    try {
      // Fetch the current player's game state.
      const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
      // Adopt the loaded state.
      adoptPayload(payload);
      // Recover the repeatable wagers from the newest round so repeat survives a reload.
      const recovered = currentRound();
      // Restore the committed ante and Aces Up bet only when a prior round exposes them.
      if (recovered && recovered.ante !== undefined) lastBet = { ante: recovered.ante, aces_up: recovered.aces_up };
    } catch (error) {
      // Surface a load failure without breaking the shell.
      if (generation === mountGeneration) toast(text('error.load'), 'error');
    }
    // Stop when the route was replaced during the state load.
    if (generation !== mountGeneration) return;
    // Render the first frame.
    render();
    // Refresh the shell wallet after mounting.
    await refreshBalance();
  },
  // Release subscriptions whenever shell navigation leaves the game.
  unmount() {
    // Advance the generation so in-flight responses cannot repaint another route.
    mountGeneration += 1;
    // Remove the locale subscription when it was registered.
    unsubscribeLocale?.();
    // Clear the subscription reference for the next mount.
    unsubscribeLocale = null;
    // Clear cached state and the outlet.
    state = null;
    // Clear cached rules.
    rules = {};
    // Clear the outlet so stale async work cannot repaint another route.
    root = null;
    // Reset the in-flight guard because teardown cancelled any presentation.
    busy = false;
    // Clear the repeatable wagers so the next session starts fresh.
    lastBet = null;
    // Clear any pending retry ids so a later mount starts clean.
    pendingDealId = null;
    // Clear the pending decision id.
    pendingDecisionId = null;
  },
};
