// Isolated Teen Patti Practice browser module for GitHub issue #150 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading and lifecycle subscription helpers.
import { loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/teen_patti';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/teen-patti';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'teen-patti-styles';
// Preserve the Bonus paytable order independently of object insertion behavior.
const BONUS_ORDER = ['trail', 'pure_sequence', 'sequence'];
// Preserve the strongest-first hand ranking for the reference display.
const RANK_ORDER = ['trail', 'pure_sequence', 'sequence', 'color', 'pair', 'high_card'];

// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for the paytable displays.
let rules = {};
// Store the configured ante before the next round.
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
// Retain an unresolved decision retry id bound to one round and choice.
let pendingDecisionId = null;
// Bind the unresolved decision retry id to one round and its decision.
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
  style.textContent = '.teenp{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .tp-stage{display:grid;gap:16px;padding:12px;min-width:0;} .tp-row{display:grid;gap:6px;} .tp-row h4{margin:0;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .tp-cards{display:flex;gap:6px;flex-wrap:wrap;min-width:0;} .tp-cards.win{outline:2px solid #f2d77d;outline-offset:3px;border-radius:8px;} .tp-actions{display:flex;flex-wrap:wrap;gap:8px;} .tp-btn{min-height:44px;padding:0 18px;border:none;border-radius:12px;font-weight:900;font-size:15px;cursor:pointer;} .tp-btn.play{background:linear-gradient(180deg,#0f9c4c,#0a5f2e);color:#fff;} .tp-btn.fold{background:linear-gradient(180deg,#6b6b76,#3a3a42);color:#fff;} .tp-btn.deal{background:linear-gradient(180deg,#d6323d,#8e1822);color:#fff;width:100%;} .tp-btn:disabled{opacity:.55;cursor:not-allowed;} .tp-btn:focus-visible,.tp-field input:focus-visible{outline:3px solid #ffd780;outline-offset:2px;} .tp-panel{display:grid;gap:12px;min-width:0;} .tp-card{padding:14px;border:1px solid rgba(255,217,120,.42);border-radius:16px;background:rgba(0,0,0,.22);} .tp-card h3{margin:0 0 10px;color:#e7bc52;text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .tp-field{display:grid;gap:4px;margin-bottom:10px;} .tp-field label{font-size:12px;font-weight:700;} .tp-field input{min-height:40px;border-radius:10px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.05);color:#f5ead6;padding:0 10px;font-weight:800;} .tp-pays{display:grid;gap:4px;font-size:12px;font-weight:700;} .tp-pays div{display:flex;justify-content:space-between;} .tp-pays span:last-child{color:#f2d77d;} .tp-rank{font-size:12px;font-weight:700;line-height:1.6;} .tp-result{min-height:24px;font-size:15px;color:#fff2c2;font-weight:800;} .tp-result .net{font-weight:900;} @media (max-width:900px){.teenp{grid-template-columns:1fr;}} @media (max-width:640px){.tp-stage{gap:10px;padding:8px;} .tp-panel{gap:8px;} .tp-card{padding:10px;} .tp-card h3{margin-bottom:6px;} .tp-field{margin-bottom:6px;} .tp-pays,.tp-rank{width:calc(100% - 160px);max-width:calc(100% - 160px);gap:2px;line-height:1.15;} .tp-pays div{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px;min-width:0;} .tp-pays span{min-width:0;overflow-wrap:anywhere;} body:has(.teenp) .report-problem-fab{width:144px;max-width:144px;white-space:normal;line-height:1.1;}} @media(prefers-reduced-motion:reduce){.teenp *{scroll-behavior:auto!important;transition:none!important;animation:none!important;}}';
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
  const bounded = Math.min(parsed, 50000);
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
function cardRow(titleKey, cards, win = false) {
  // Render each card through the shared renderer.
  const rendered = (cards || []).map(card => renderCard(card)).join('');
  // Return one titled card row.
  return `<div class="tp-row"><h4>${safe(text(titleKey))}</h4><div class="tp-cards ${win ? 'win' : ''}">${rendered}</div></div>`;
}

// Render the Bonus paytable rows.
function bonusRows() {
  // Build one row per listed Bonus tier present in the authoritative table.
  return BONUS_ORDER.filter(name => rules.bonus_multipliers && rules.bonus_multipliers[name] !== undefined).map(name => `<div><span>${safe(text('hand.' + name))}</span><span>${rules.bonus_multipliers[name]}:1</span></div>`).join('');
}

// Render the strongest-first hand ranking reference.
function rankingRows() {
  // Join the localized ranking names in strongest-first order.
  return RANK_ORDER.map((name, index) => `${index + 1}. ${safe(text('hand.' + name))}`).join('<br>');
}

// Render the complete Teen Patti route into the outlet.
function render() {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the newest round to decide which stage to present.
  const round = currentRound();
  // Determine whether a decision is awaited.
  const deciding = round && round.phase === 'decision';
  // Build the stage markup for the current phase.
  const stage = deciding ? decisionStage(round) : round && round.phase === 'settled' ? settledStage(round) : idleStage();
  // Build the side panel with wager input and paytables.
  const panel = sidePanel(deciding);
  // Paint the whole route.
  root.innerHTML = `<section class="teenp" data-testid="teen-patti"><div class="tp-stage">${stage}</div><div class="tp-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set the ante and deal.
  return `<p class="tp-result" data-testid="teen-patti-result" role="status" aria-live="polite">${safe(text('result.idle'))}</p>`;
}

// Build the decision stage showing the player's three cards and the play or fold controls.
function decisionStage(round) {
  // Render the three player cards.
  const cards = cardRow('label.your_cards', round.player_cards);
  // Return the cards, the prompt, and the decision controls.
  return `${cards}<p class="tp-result" role="status" aria-live="polite">${safe(text('result.decide'))}</p><div class="tp-actions"><button class="tp-btn fold" data-fold="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.fold'))}</button><button class="tp-btn play" data-play="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.play'))}</button></div>`;
}

// Build the settled stage revealing both hands and the result.
function settledStage(round) {
  // Render the player's revealed hand, highlighting a win.
  const win = round.outcome === 'player_win' || round.outcome === 'dealer_not_qualified';
  // Render the player's three cards.
  const player = cardRow('label.your_cards', round.player_cards, win);
  // Render the dealer's revealed cards when a showdown happened.
  const dealer = round.dealer_cards ? cardRow('label.dealer_cards', round.dealer_cards) : '';
  // Read the settled net movement.
  const net = round.net || 0;
  // Read the localized hand tier for the player.
  const tier = round.player_hand ? safe(text('hand.' + round.player_hand.name)) : '';
  // Build the outcome result line with a signed net amount.
  const line = `${safe(text('outcome.' + round.outcome))} ${tier} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Return the revealed hands and result while the single wager-panel deal action remains authoritative.
  return `${player}${dealer}<p class="tp-result" data-testid="teen-patti-result" role="status" aria-live="polite">${line}</p>`;
}

// Build the side panel with the ante input and paytables.
function sidePanel(deciding) {
  // Hide the ante input while a decision is pending.
  const wagerCard = deciding ? '' : `<div class="tp-card"><h3>${safe(text('label.ante'))}</h3><div class="tp-field"><label for="tp-ante">${safe(text('label.ante'))}</label><input id="tp-ante" data-ante type="number" min="1" step="1" value="${ante}"></div><button class="tp-btn deal" data-deal="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.deal'))}</button></div>`;
  // Build the Bonus paytable card.
  const bonus = `<div class="tp-card"><h3>${safe(text('label.bonus'))}</h3><div class="tp-pays">${bonusRows()}</div></div>`;
  // Build the ranking reference card.
  const ranking = `<div class="tp-card"><h3>${safe(text('label.ranking'))}</h3><div class="tp-rank">${rankingRows()}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${bonus}${ranking}`;
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
  if (foldButton) foldButton.onclick = () => decide('fold');
  // Bind the play control to a play decision.
  const playButton = root.querySelector('[data-play]');
  // Attach the play handler.
  if (playButton) playButton.onclick = () => decide('play');
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
      pendingDealId = nextActionId('tp-deal');
      // Bind the retry id to the exact ante.
      pendingDealAnte = ante;
    }
    // Post the exactly-once deal with the current ante.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, ante }));
    // Adopt the returned state and reveal the decision stage.
    adoptPayload(payload);
  });
}

// Apply one play or fold decision to the active round.
function decide(decision) {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore decisions when no active round awaits one.
  if (!round || round.phase !== 'decision') return;
  // Perform the decision as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved decision id or mint one bound to this exact decision.
    if (!pendingDecisionId || pendingDecisionContext?.round_id !== round.round_id || pendingDecisionContext?.decision !== decision) {
      // Mint a fresh decision retry id.
      pendingDecisionId = nextActionId('tp-decision');
      // Bind the retry id to the exact round and decision.
      pendingDecisionContext = { round_id: round.round_id, decision };
    }
    // Post the exactly-once decision to the round-scoped route.
    const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDecisionId, decision }));
    // Adopt the settled result.
    adoptPayload(payload);
    // Release the resolved decision retry binding.
    pendingDecisionId = null;
    // Release the resolved decision context.
    pendingDecisionContext = null;
  });
}

// Export the isolated Teen Patti game for the shared shell.
export const TeenPattiGame = {
  // Expose the stable catalog identifier.
  id: 'teen_patti',
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
    // Read reload-safe state so a pending decision or settled result is restored.
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
