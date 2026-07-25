// Isolated Mississippi Stud browser module for GitHub issue #143 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/mississippi_stud';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/mississippi-stud';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'mississippi-stud-styles';
// Preserve the paytable order independently of object insertion behavior.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_of_a_kind', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'pair_jacks_plus'];
// Offer the three documented street bet sizes.
const BET_MULTIPLIERS = [1, 2, 3];

// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for paytable displays.
let rules = {};
// Store the configured ante wager before the next round.
let ante = 5;
// Prevent overlapping atomic browser actions.
let busy = false;
// Store the locale cleanup callback so unmount releases subscriptions.
let unsubscribeLocale = null;
// Track mount generations so late network responses cannot revive an old route.
let mountGeneration = 0;
// Store a fallback retry-id counter for browsers without randomUUID support.
let requestCounter = 0;
// Retain an unresolved deal retry id until the backend confirms its response.
let pendingDealId = null;
// Bind the unresolved deal retry id to one ante.
let pendingDealAnte = null;
// Retain one unresolved decision retry id per street so retries stay stable.
let pendingDecisionId = null;
// Bind the unresolved decision retry id to one round, street, and choice.
let pendingDecisionContext = null;

// Resolve one owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every player-visible and accessible label to the EN/RU domain.
  return t(key, params, DOMAIN);
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
  style.textContent = '.msstud{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .ms-stage{display:grid;gap:16px;padding:12px;min-width:0;} .ms-row{display:grid;gap:6px;} .ms-row h4{margin:0;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .ms-cards{display:flex;gap:6px;flex-wrap:wrap;min-width:0;} .ms-street{font-weight:900;color:#f2d77d;} .ms-actions{display:flex;flex-wrap:wrap;gap:8px;} .ms-btn{min-height:44px;padding:0 16px;border:none;border-radius:12px;font-weight:900;font-size:15px;cursor:pointer;} .ms-btn.bet{background:linear-gradient(180deg,#0f9c4c,#0a5f2e);color:#fff;} .ms-btn.fold{background:linear-gradient(180deg,#6b6b76,#3a3a42);color:#fff;} .ms-btn.deal{background:linear-gradient(180deg,#d6323d,#8e1822);color:#fff;width:100%;} .ms-btn:disabled{opacity:.55;cursor:not-allowed;} .ms-panel{display:grid;gap:12px;min-width:0;} .ms-card{padding:14px;border:1px solid rgba(255,217,120,.42);border-radius:16px;background:rgba(0,0,0,.22);} .ms-card h3{margin:0 0 10px;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .ms-field{display:grid;gap:4px;margin-bottom:10px;} .ms-field label{font-size:12px;font-weight:700;} .ms-field input{min-height:40px;border-radius:10px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.05);color:#f5ead6;padding:0 10px;font-weight:800;} .ms-pays{display:grid;gap:4px;font-size:12px;font-weight:700;} .ms-pays div{display:flex;justify-content:space-between;} .ms-pays span:last-child{color:#f2d77d;} .ms-result{min-height:24px;font-size:15px;color:#fff2c2;font-weight:800;} .ms-result .net{font-weight:900;} @media (max-width:900px){.msstud{grid-template-columns:1fr;}} @media (max-width:640px){.ms-stage{gap:10px;padding:8px;} .ms-panel{gap:8px;} .ms-card{padding:10px;} .ms-card h3{margin-bottom:6px;} .ms-field{margin-bottom:6px;} .ms-pays{gap:2px;line-height:1.15;}}';
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

// Normalize an ante to the ledger-compatible bounds.
function normalizedAnte(value) {
  // Convert browser input text to a numeric wager.
  const parsed = Number(value);
  // Return the lower bound for invalid or undersized values.
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  // Clamp oversized browser values to the public contract maximum.
  const bounded = Math.min(parsed, 10000);
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
    // Release the resolved deal ante.
    pendingDealAnte = null;
  }
}

// Build the markup for one labelled row of cards.
function cardRow(titleKey, cards) {
  // Render each card through the shared renderer.
  const rendered = (cards || []).map(card => renderCard(card)).join('');
  // Return one titled card row.
  return `<div class="ms-row"><h4>${safe(text(titleKey))}</h4><div class="ms-cards">${rendered}</div></div>`;
}

// Render the paytable rows for the to-one hand table.
function paytableRows() {
  // Build one row per listed hand tier present in the authoritative table.
  return PAYTABLE_ORDER.filter(name => rules.paytable && rules.paytable[name] !== undefined).map(name => `<div><span>${safe(text('hand.' + name))}</span><span>${rules.paytable[name]}:1</span></div>`).join('');
}

// Render the complete Mississippi Stud route into the outlet.
function render() {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the newest round to decide which stage to present.
  const round = currentRound();
  // Determine whether a decision is awaited.
  const deciding = round && round.phase === 'decision';
  // Build the stage markup for the current phase.
  const stage = deciding ? decisionStage(round) : round && round.phase === 'settled' ? settledStage(round) : idleStage();
  // Build the side panel with wager input and the paytable.
  const panel = sidePanel(deciding);
  // Paint the whole route.
  root.innerHTML = `<section class="msstud" data-testid="mississippi-stud"><div class="ms-stage">${stage}</div><div class="ms-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set the ante and deal.
  return `<p class="ms-result" data-testid="mississippi-stud-result">${safe(text('result.idle'))}</p>`;
}

// Build the decision stage showing the hole cards, revealed community, and bet or fold controls.
function decisionStage(round) {
  // Render the two hole cards.
  const hole = cardRow('label.hole_cards', round.hole_cards);
  // Render the community cards revealed so far.
  const community = cardRow('label.community_cards', round.community_revealed);
  // Build one bet button per multiplier.
  const bets = BET_MULTIPLIERS.map(multiplier => `<button class="ms-btn bet" data-bet="${multiplier}" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.bet', { multiplier }))}</button>`).join('');
  // Return the cards, the street label, and the decision controls.
  return `${hole}${community}<p class="ms-street">${safe(text('label.street', { street: round.street }))}</p><div class="ms-actions"><button class="ms-btn fold" data-fold="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.fold'))}</button>${bets}</div>`;
}

// Build the settled stage revealing the completed hand and the result.
function settledStage(round) {
  // Render the two hole cards.
  const hole = cardRow('label.hole_cards', round.hole_cards);
  // Render every revealed community card.
  const community = cardRow('label.community_cards', round.community_revealed);
  // Read the settled net movement.
  const net = round.net || 0;
  // Compose the outcome and hand tier line.
  const tier = round.hand_tier ? safe(text('hand.' + round.hand_tier)) : '';
  // Build the outcome result line with a signed net amount.
  const line = `${safe(text('outcome.' + round.outcome))} ${tier} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Return the revealed hand, the result, and a deal-again control.
  return `${hole}${community}<p class="ms-result" data-testid="mississippi-stud-result">${line}</p><div class="ms-actions"><button class="ms-btn deal" data-deal="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.deal_again'))}</button></div>`;
}

// Build the side panel with the ante input and the paytable.
function sidePanel(deciding) {
  // Hide the ante input while a decision is pending.
  const wagerCard = deciding ? '' : `<div class="ms-card"><h3>${safe(text('label.ante'))}</h3><div class="ms-field"><label for="ms-ante">${safe(text('label.ante'))}</label><input id="ms-ante" data-ante type="number" min="1" step="1" value="${ante}"></div><button class="ms-btn deal" data-deal="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.deal'))}</button></div>`;
  // Build the paytable card.
  const paytable = `<div class="ms-card"><h3>${safe(text('label.paytable'))}</h3><div class="ms-pays">${paytableRows()}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${paytable}`;
}

// Attach event handlers to the current stage controls.
function bindEvents() {
  // Bind the ante input to the cached wager.
  const anteInput = root.querySelector('[data-ante]');
  // Update the cached ante on input.
  if (anteInput) anteInput.onchange = () => { ante = normalizedAnte(anteInput.value); };
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the fold control to a fold decision.
  const foldButton = root.querySelector('[data-fold]');
  // Attach the fold handler.
  if (foldButton) foldButton.onclick = () => decide('fold', 1);
  // Bind every bet control to a bet decision at its multiplier.
  root.querySelectorAll('[data-bet]').forEach(button => { button.onclick = () => decide('bet', Number(button.dataset.bet)); });
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
      // Refresh the shell wallet after any movement.
      await refreshBalance();
    }
  }
}

// Deal one new round after committing the ante.
function deal() {
  // Perform the deal as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved deal id or mint a fresh one bound to the current ante.
    if (!pendingDealId || pendingDealAnte !== ante) {
      // Mint a fresh deal retry id.
      pendingDealId = nextActionId('ms-deal');
      // Bind the retry id to the exact ante.
      pendingDealAnte = ante;
    }
    // Post the exactly-once deal with the current ante.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, ante }));
    // Adopt the returned state and reveal the first street.
    adoptPayload(payload);
  });
}

// Apply one bet or fold decision to the active round's current street.
function decide(decision, multiplier) {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore decisions when no active round awaits one.
  if (!round || round.phase !== 'decision') return;
  // Perform the decision as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved decision id or mint one bound to this exact street decision.
    if (!pendingDecisionId || pendingDecisionContext?.round_id !== round.round_id || pendingDecisionContext?.street !== round.street || pendingDecisionContext?.decision !== decision || pendingDecisionContext?.multiplier !== multiplier) {
      // Mint a fresh decision retry id.
      pendingDecisionId = nextActionId('ms-decision');
      // Bind the retry id to the exact round, street, and decision.
      pendingDecisionContext = { round_id: round.round_id, street: round.street, decision, multiplier };
    }
    // Post the exactly-once decision to the round-scoped route.
    const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionId, decision, multiplier }));
    // Adopt the advanced or settled result.
    adoptPayload(payload);
    // Release the resolved decision retry binding so the next street mints a new id.
    pendingDecisionId = null;
    // Release the resolved decision context.
    pendingDecisionContext = null;
  });
}

// Export the isolated Mississippi Stud game for the shared shell.
export const MississippiStudGame = {
  // Expose the stable catalog identifier.
  id: 'mississippi_stud',
  // Expose an empty label because the shell provides the localized catalog label.
  label: '',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Advance the mount generation so late responses from a prior mount are ignored.
    mountGeneration += 1;
    // Store the current route outlet.
    root = node;
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
    // Read reload-safe state so a pending street or settled result is restored.
    try {
      // Fetch the current player's game state.
      const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
      // Adopt the loaded state.
      adoptPayload(payload);
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
    // Clear cached state.
    state = null;
    // Clear cached rules.
    rules = {};
    // Clear the outlet so stale async work cannot repaint another route.
    root = null;
    // Reset the in-flight guard because teardown cancelled any presentation.
    busy = false;
    // Clear any pending retry ids so a later mount starts clean.
    pendingDealId = null;
    // Clear the pending decision id.
    pendingDecisionId = null;
  },
};
