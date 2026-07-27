// Isolated Double Bonus Video Poker browser module for GitHub issue #131 without shared shell edits.

// Import session-aware API helpers so compatibility player ids stay subordinate to the session.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the shared semantic card renderer instead of game-owned card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/double_bonus_video_poker';
// Store the additive frozen-v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/double-bonus-video-poker';
// Identify the reusable shared stylesheet so card games install it only once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Preserve the route-local style id so repeated mounts never duplicate CSS.
const STYLE_ID = 'double-bonus-video-poker-styles';
// Preserve the paytable order independently of object insertion behavior.
const PAYTABLE_ORDER = ['royal_flush', 'straight_flush', 'four_aces', 'four_2s_4s', 'four_5s_ks', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'jacks_or_better'];

// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated-player state returned by the backend.
let state = null;
// Store authoritative game rules for the paytable display.
let rules = {};
// Store the configured bet before the next round.
let bet = 5;
// Track which dealt positions the player has toggled to hold during the draw phase.
let held = new Set();
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
// Bind the unresolved deal retry id to one bet.
let pendingDealBet = null;
// Retain an unresolved draw retry id bound to one round and hold selection.
let pendingDrawId = null;
// Bind the unresolved draw retry id to one round and its held positions.
let pendingDrawContext = null;
// Retain the last settled bet so one click can start an identical new deal.
let lastBet = null;

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
  style.textContent = '.dbvp{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;width:100%;min-width:0;min-height:100%;color:var(--text,#f5ead6);align-items:start;} .db-header{grid-column:1/-1;display:flex;align-items:end;justify-content:space-between;gap:12px;padding:0 12px;min-width:0;} .db-header h1{margin:0;font-size:clamp(24px,3vw,38px);line-height:1.05;} .db-phase{margin:0;padding:6px 10px;border:1px solid var(--gold);border-radius:999px;color:var(--text);font-size:12px;font-weight:800;} .db-stage{display:grid;gap:16px;padding:12px;min-width:0;justify-items:start;} .db-hand{display:flex;gap:8px;flex-wrap:wrap;min-width:0;} .db-slot{display:grid;justify-items:center;gap:4px;} .db-holdbtn{background:none;border:none;cursor:pointer;padding:0;border-radius:10px;} .db-holdbtn[aria-pressed="true"]{outline:2px solid var(--gold);outline-offset:3px;} .db-tag{font-size:11px;font-weight:900;color:var(--gold);text-transform:uppercase;min-height:14px;} .db-actions{display:flex;flex-wrap:wrap;gap:8px;} .db-btn{min-height:44px;padding:0 18px;border:none;border-radius:12px;font-weight:900;font-size:15px;cursor:pointer;} .db-btn.draw{background:linear-gradient(180deg,#0f9c4c,#0a5f2e);color:#fff;} .db-btn.deal{background:linear-gradient(180deg,#d6323d,#8e1822);color:#fff;width:100%;} .db-btn:disabled{opacity:.55;cursor:not-allowed;} .db-panel{display:grid;gap:12px;min-width:0;} .db-card{padding:14px;border:1px solid var(--gold);border-radius:16px;background:rgba(0,0,0,.22);} .db-card h3{margin:0 0 10px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;} .db-field{display:grid;gap:4px;margin-bottom:10px;} .db-field label{font-size:12px;font-weight:700;} .db-field input{width:100%;max-width:100%;min-width:0;min-height:40px;border-radius:10px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.05);color:var(--text);padding:0 10px;font-weight:800;} .db-pays{display:grid;max-width:100%;min-width:0;gap:3px;font-size:12px;font-weight:700;} .db-pays div{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px;min-width:0;} .db-pays span{min-width:0;overflow-wrap:anywhere;} .db-pays span:last-child{color:var(--gold);} .db-result{min-height:24px;font-size:15px;color:var(--text);font-weight:800;} .db-result .net{font-weight:900;} @media (max-width:1200px){.db-card>h3,.db-card>.db-field,.db-card>.db-btn,.db-card>.db-pays{width:calc(100% - 160px);max-width:calc(100% - 160px);} body:has(.dbvp) .report-problem-fab{width:144px;max-width:144px;white-space:normal;line-height:1.1;}} @media (max-width:900px){.dbvp{grid-template-columns:1fr;}.db-header{align-items:start;flex-direction:column;}.db-header,.db-stage{padding-inline:0;}}.db-repeat{width:100%;margin-top:8px;min-height:44px;padding:0 18px;border:1px solid var(--gold);border-radius:12px;background:transparent;color:var(--gold);font-weight:900;font-size:15px;cursor:pointer;}.db-repeat:disabled{opacity:.5;cursor:not-allowed;}';
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

// Normalize a bet to the ledger-compatible bounds.
function normalizedBet(value) {
  // Convert browser input text to a numeric wager.
  const parsed = Number(value);
  // Return the lower bound for invalid or undersized values.
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  // Clamp oversized browser values to the public contract maximum.
  const bounded = Math.min(parsed, 100000);
  // Round to cents so previews match ledger-compatible request values.
  return Math.round(bounded * 100) / 100;
}

// Read the newest actionable or completed round from reload-safe server state.
function currentRound() {
  // Prefer the active draw round over retained history.
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
    // Release the resolved deal bet.
    pendingDealBet = null;
  }
}

// Render the paytable rows for the total-return hand table.
function paytableRows() {
  // Build one row per listed hand tier present in the authoritative table.
  return PAYTABLE_ORDER.filter(name => rules.paytable && rules.paytable[name] !== undefined).map(name => `<div><span>${safe(text('hand.' + name))}</span><span>${rules.paytable[name]}</span></div>`).join('');
}

// Render the complete Double Bonus route into the outlet.
function render() {
  // Do nothing when the route was already torn down.
  if (!root) return;
  // Read the newest round to decide which stage to present.
  const round = currentRound();
  // Determine whether a draw is awaited.
  const drawing = round && round.phase === 'draw';
  // Determine whether a terminal hand is available for the next-deal presentation.
  const settled = round && round.phase === 'settled';
  // Select one localized phase label for the current authoritative state.
  const phaseKey = drawing ? 'draw' : settled ? 'settled' : 'idle';
  // Build the stage markup for the current phase.
  const stage = drawing ? drawStage(round) : settled ? settledStage(round) : idleStage();
  // Build the side panel with the bet input and the paytable.
  const panel = sidePanel(drawing, settled);
  // Paint the whole route.
  root.innerHTML = `<section class="dbvp" data-testid="double-bonus-video-poker"><header class="db-header"><h1>${safe(text('title'))}</h1><p class="db-phase" data-testid="double-bonus-video-poker-phase" aria-live="polite">${safe(text('phase.' + phaseKey))}</p></header><div class="db-stage">${stage}</div><div class="db-panel">${panel}</div></section>`;
  // Wire the interactive controls for the current stage.
  bindEvents();
}

// Build the idle stage shown before the first deal.
function idleStage() {
  // Prompt the player to set the bet and deal.
  return `<p class="db-result" data-testid="double-bonus-video-poker-result">${safe(text('result.idle'))}</p>`;
}

// Build the draw stage with each dealt card tappable to hold.
function drawStage(round) {
  // Build one tappable held-card slot per dealt card.
  const cards = round.hand.map((card, index) => `<div class="db-slot"><button class="db-holdbtn" data-hold="${index}" type="button" aria-pressed="${held.has(index)}" ${busy ? 'disabled' : ''}>${renderCard(card)}</button><span class="db-tag">${held.has(index) ? safe(text('label.held')) : ''}</span></div>`).join('');
  // Return the hand, the prompt, and the draw control.
  return `<div class="db-hand" data-testid="double-bonus-video-poker-hand">${cards}</div><p class="db-result">${safe(text('result.draw'))}</p><div class="db-actions"><button class="db-btn draw" data-draw="1" type="button" ${busy ? 'disabled' : ''}>${safe(text('action.draw'))}</button></div>`;
}

// Build the settled stage revealing the final hand and the result.
function settledStage(round) {
  // Render the final five-card hand.
  const cards = (round.final_hand || round.hand).map(card => renderCard(card)).join('');
  // Read the settled net movement.
  const net = round.net || 0;
  // Compose the outcome and hand tier line.
  const tier = round.hand_tier ? safe(text('hand.' + round.hand_tier)) : '';
  // Build the outcome result line with a signed net amount.
  const line = `${safe(text('outcome.' + round.outcome))} ${tier} <span class="net">${net >= 0 ? '+' + net : net}</span>`;
  // Return the revealed hand, the result, and a deal-again control.
  return `<div class="db-hand">${cards}</div><p class="db-result" data-testid="double-bonus-video-poker-result">${line}</p>`;
}

// Build the side panel with the bet input and the paytable.
function sidePanel(drawing, settled) {
  // Select a next-round label only after a completed hand exists.
  const dealLabel = settled ? text('action.deal_again') : text('action.deal');
  // Enable the one-click repeat only when a prior bet exists and no request or retry is active.
  const repeatDisabled = busy || Boolean(pendingDealId) || Boolean(pendingDrawId) || !lastBet;
  // Hide the bet input while a draw is pending.
  const wagerCard = drawing ? '' : `<div class="db-card"><h3>${safe(text('label.bet'))}</h3><div class="db-field"><label for="db-bet">${safe(text('label.bet'))}</label><input id="db-bet" data-bet type="number" min="1" step="1" value="${bet}"></div><button class="db-btn deal" data-deal="1" type="button" ${busy ? 'disabled' : ''}>${safe(dealLabel)}</button><button type="button" class="db-repeat" data-action="repeat" ${repeatDisabled ? 'disabled' : ''}>${safe(text('controls.repeat'))}</button></div>`;
  // Build the paytable card.
  const paytable = `<div class="db-card db-paytable"><h3>${safe(text('label.paytable'))}</h3><div class="db-pays">${paytableRows()}</div></div>`;
  // Return the stacked side panel.
  return `${wagerCard}${paytable}`;
}

// Attach event handlers to the current stage controls.
function bindEvents() {
  // Bind the bet input to the cached wager.
  const betInput = root.querySelector('[data-bet]');
  // Update the cached bet on input.
  if (betInput) betInput.onchange = () => { bet = normalizedBet(betInput.value); };
  // Bind each held-card toggle.
  root.querySelectorAll('[data-hold]').forEach(button => { button.onclick = () => toggleHold(Number(button.dataset.hold)); });
  // Bind every deal control to the deal action.
  root.querySelectorAll('[data-deal]').forEach(button => { button.onclick = deal; });
  // Bind the one-click repeat control to a fresh same-bet deal.
  const repeatButton = root.querySelector('[data-action="repeat"]');
  // Attach the repeat handler when the control is present.
  if (repeatButton) repeatButton.onclick = repeat;
  // Bind the draw control to the draw action.
  const drawButton = root.querySelector('[data-draw]');
  // Attach the draw handler.
  if (drawButton) drawButton.onclick = draw;
}

// Toggle one dealt card position in or out of the held set.
function toggleHold(index) {
  // Ignore toggles while an action is resolving.
  if (busy) return;
  // Remove a held position or add a new one.
  if (held.has(index)) held.delete(index);
  // Add the newly held position.
  else held.add(index);
  // Repaint the updated hold selection.
  render();
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

// Deal one new round after committing the bet.
function deal() {
  // Perform the deal as one guarded action.
  return runAction(async () => {
    // Reset the held selection for the fresh hand.
    held = new Set();
    // Reuse an unresolved deal id or mint a fresh one bound to the current bet.
    if (!pendingDealId || pendingDealBet !== bet) {
      // Mint a fresh deal retry id.
      pendingDealId = nextActionId('db-deal');
      // Bind the retry id to the exact bet.
      pendingDealBet = bet;
    }
    // Post the exactly-once deal with the current bet.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingDealId, bet }));
    // Adopt the returned state and reveal the dealt hand.
    adoptPayload(payload);
  });
}

// Draw replacements for the unheld cards and settle the paytable.
function draw() {
  // Read the active round before acting.
  const round = currentRound();
  // Ignore draws when no active round awaits one.
  if (!round || round.phase !== 'draw') return;
  // Snapshot the sorted held positions for the request and fingerprint.
  const hold = [...held].sort((left, right) => left - right);
  // Perform the draw as one guarded action.
  return runAction(async () => {
    // Reuse an unresolved draw id or mint one bound to this exact round and hold.
    const holdKey = hold.join(',');
    // Rebind the retry id when the round or hold selection changes.
    if (!pendingDrawId || pendingDrawContext?.round_id !== round.round_id || pendingDrawContext?.hold !== holdKey) {
      // Mint a fresh draw retry id.
      pendingDrawId = nextActionId('db-draw');
      // Bind the retry id to the exact round and hold selection.
      pendingDrawContext = { round_id: round.round_id, hold: holdKey };
    }
    // Post the exactly-once draw with the held positions.
    const payload = await post(`${API_ROOT}/rounds/${encodeURIComponent(round.round_id)}/decisions`, withCurrentPlayer({ action_id: pendingDrawId, hold }));
    // Adopt the settled result.
    adoptPayload(payload);
    // Release the resolved draw retry binding.
    pendingDrawId = null;
    // Release the resolved draw context.
    pendingDrawContext = null;
    // Read the newly settled round to capture its committed wager.
    const settled = currentRound();
    // Remember the settled bet so the next deal can repeat the same wager with one click.
    if (settled && settled.phase === 'settled') lastBet = { bet: settled.bet };
  });
}

// Start one new deal with the previous bet without replaying the hold or draw.
async function repeat() {
  // Read the current round to block a repeat during an unsettled hand.
  const round = currentRound();
  // Ignore repeat while busy, holding an unresolved retry, mid-hand, or without a prior bet.
  if (busy || pendingDealId || pendingDrawId || !lastBet || (round && round.phase === 'draw')) return;
  // Restore the previous bet so the fresh deal commits the same wager.
  bet = lastBet.bet;
  // Fire the shared exactly-once deal action with the restored bet.
  await deal();
}

// Export the isolated Double Bonus Video Poker game for the shared shell.
export const DoubleBonusVideoPokerGame = {
  // Expose the stable catalog identifier.
  id: 'double_bonus_video_poker',
  // Expose an empty label because the shell provides the localized catalog label.
  label: '',
  // Mount the isolated route into the shared shell outlet.
  async mount(node) {
    // Advance the mount generation so late responses from a prior mount are ignored.
    mountGeneration += 1;
    // Store the current route outlet.
    root = node;
    // Reset the repeatable bet so another session never inherits a prior wager.
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
    // Read reload-safe state so a pending draw or settled result is restored.
    try {
      // Fetch the current player's game state.
      const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
      // Adopt the loaded state.
      adoptPayload(payload);
      // Read the newest reload-safe round to recover a repeatable bet.
      const restored = currentRound();
      // Restore the repeatable bet only when a settled round exposes its committed wager.
      if (restored && restored.phase === 'settled') lastBet = { bet: restored.bet };
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
    // Reset the held selection.
    held = new Set();
    // Clear any pending retry ids so a later mount starts clean.
    pendingDealId = null;
    // Clear the pending draw id.
    pendingDrawId = null;
    // Clear the repeatable bet so the next session starts fresh.
    lastBet = null;
  },
};
