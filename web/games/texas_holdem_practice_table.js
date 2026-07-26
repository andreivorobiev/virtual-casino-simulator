// Provide the isolated issue #95 browser module without shared shell edits.
// Requirements: CARD-002, I18N-001, I18N-002, CORE-008, and MOTION-002.

// Import session-aware API helpers used by catalog-discovered game modules.
import { api, currentPlayerPath, post, withCurrentPlayer } from '../core/api.js';
// Import shared wallet refresh, safe markup, and toast presentation helpers.
import { refreshBalance, safe, toast } from '../core/ui.js';
// Import the accessible #96 card renderer instead of creating card markup.
import { renderCard } from '../core/cards.js';
// Import locale loading, numeric formatting, and live-switch subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';

// Address every additive practice-table endpoint from one stable root.
const API_ROOT = '/api/v1/games/texas-holdem-practice-table';
// Address the paired game-owned EN/RU resource domain.
const DOMAIN = 'games/texas_holdem_practice_table';
// Identify the shared #96 stylesheet so it is installed at most once.
const CARD_STYLE_ID = 'casino-shared-card-styles';
// Mirror the server's one-ante plus four-call escrow multiplier.
const RESERVED_BET_UNITS = 5;
// Keep the supported error-code mapping finite so raw server prose never leaks.
const ERROR_KEYS = { VALIDATION_ERROR: 'errors.validation', CONFLICT: 'errors.conflict', NOT_FOUND: 'errors.notFound', INSUFFICIENT_FUNDS: 'errors.insufficientFunds', UNAUTHORIZED: 'errors.unauthorized', FORBIDDEN: 'errors.forbidden' };

// Retain the mounted route node for deterministic full rerenders.
let root = null;
// Retain the latest authoritative player-scoped API state.
let state = null;
// Retain the selected fixed-limit unit before the next hand.
let baseWager = 1;
// Prevent overlapping atomic browser actions.
let busy = false;
// Retain the locale unsubscribe callback for leak-free unmount.
let unsubscribeLocale = null;
// Retain one complete start command until the server confirms its escrow debit response.
let pendingStart = null;
// Retain one decision id until the server confirms the exact transition.
let pendingDecision = null;
// Retain a bounded fallback counter when randomUUID is unavailable.
let actionCounter = 0;


// Resolve one game-owned localized string without visible hard-coded fallbacks.
function text(key, params = {}) {
  // Delegate every visible and accessible label to the active locale domain.
  return t(key, params, DOMAIN);
}


// Format a play-token amount without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Insert the locale-formatted number into explicit fake-token language.
  return text('tokens.amount', { amount: formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) });
}


// Cache one finite wager edit and refresh its reserve preview without replacing controls.
function cacheWager(value) {
  // Convert the number-input value while preserving the prior value for malformed edits.
  const parsed = Number(value);
  // Clamp finite browser input to the same public server range.
  if (Number.isFinite(parsed)) baseWager = Math.min(20000, Math.max(0.01, parsed));
  // Resolve the existing preview without rerendering the clicked button.
  const preview = root?.querySelector('[data-testid="thpt-reserve-amount"]');
  // Refresh localized preview text when the surface remains mounted.
  if (preview) preview.textContent = tokenAmount(baseWager * RESERVED_BET_UNITS);
}


// Translate known API failures without exposing English server messages in Russian.
function errorText(error) {
  // Map the stable public error code to one owned resource key.
  const key = ERROR_KEYS[String(error?.code || '').toUpperCase()] || 'errors.actionFailed';
  // Return only localized copy from the game domain.
  return text(key);
}


// Install the shared CARD-002 presentation hooks without editing global CSS.
function ensureSharedCardStyles() {
  // Reuse a stylesheet already installed by this or another card game.
  if (document.getElementById(CARD_STYLE_ID)) return;
  // Create one standard stylesheet link for the shared renderer.
  const link = document.createElement('link');
  // Mark the link so later mounts remain idempotent.
  link.id = CARD_STYLE_ID;
  // Declare the external resource as a stylesheet.
  link.rel = 'stylesheet';
  // Load the merged #96 styles from the public web root.
  link.href = '/core/cards.css';
  // Append the shared stylesheet to document metadata once.
  document.head.append(link);
}


// Generate one bounded client action id for retry-safe commands.
function nextActionId() {
  // Prefer the browser-native cryptographic UUID source when available.
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  // Increment the fallback counter to disambiguate same-millisecond actions.
  actionCounter += 1;
  // Combine a timestamp and counter without claiming fairness or secrecy.
  return `browser-${Date.now().toString(36)}-${actionCounter.toString(36)}`;
}


// Return the actionable hand or newest settled hand for one stable stage.
function currentHand() {
  // Prefer the active slot before newest-first settled history.
  return state?.active_hand || state?.recent_hands?.[0] || null;
}


// Return one localized table-seat label from its server-owned resource key.
function seatLabel(seatOrId, hand = currentHand()) {
  // Resolve an id into the current public seat collection when necessary.
  const seat = typeof seatOrId === 'string' ? hand?.seats?.find(item => item.seat_id === seatOrId) : seatOrId;
  // Use a neutral localized fallback only for absent historical data.
  return seat?.label_key ? text(seat.label_key) : text('seats.unknown');
}


// Translate one internal phase into concise player-facing status language.
function phaseLabel(hand) {
  // Show the ready state before the first hand.
  if (!hand) return text('phases.ready');
  // Show the terminal human result after settlement.
  if (hand.phase === 'settled') return text(`results.${hand.result?.human_outcome || 'complete'}`);
  // Translate every documented active or recovery phase through owned copy.
  return text(`phases.${hand.phase}`);
}


// Build a localized accessible name for one compact card code.
function cardLabel(card) {
  // Normalize the compact rank from every character except the suit code.
  const rank = String(card).slice(0, -1);
  // Normalize the compact suit from the final character.
  const suit = String(card).slice(-1);
  // Build the label entirely from paired EN/RU resources.
  return text('cards.cardLabel', { rank: text(`ranks.${rank}`), suit: text(`suits.${suit}`) });
}


// Render one shared #96 card while localizing visible and hidden ARIA names.
function localizedCard(card) {
  // Render a server-redacted opponent card through the shared hidden-card path.
  if (card === '??') return renderCard(card, { hidden: true }).replace(/aria-label="[^"]*"/, `aria-label="${safe(text('cards.faceDown'))}"`);
  // Render one visible compact card through the shared semantic primitive.
  return renderCard(card).replace(/aria-label="[^"]*"/, `aria-label="${safe(cardLabel(card))}"`);
}


// Render one reserved community slot without implying a dealt hidden card.
function emptyCardSlot(position) {
  // Return a stable accessible placeholder for a future board card.
  return `<span class="thpt-card-slot" role="img" aria-label="${safe(text('cards.waitingPosition', { position }))}"></span>`;
}


// Render one human or server-managed table seat with localized state cues.
function seatHtml(seat, hand) {
  // Determine whether this seat currently owns the decision.
  const acting = hand.current_actor === seat.seat_id;
  // Determine whether this seat appears in the fully reconciled winner list.
  const winner = hand.phase === 'settled' && hand.result?.winner_seat_ids?.includes(seat.seat_id);
  // Render both public hole-card values through localized shared cards.
  const cards = (seat.hole_cards || []).map(localizedCard).join('');
  // Select a concise localized state badge beyond color alone.
  const status = seat.folded ? text('seats.folded') : winner ? text('seats.winner') : acting ? text('seats.acting') : text('seats.inHand');
  // Build semantic classes without exposing backend enum text.
  const classes = `thpt-seat${seat.kind === 'human' ? ' is-human' : ''}${seat.folded ? ' is-folded' : ''}${acting ? ' is-acting' : ''}${winner ? ' is-winner' : ''}`;
  // Return the complete seat with stable browser-test hooks.
  return `<article class="${classes}" data-testid="thpt-seat-${safe(seat.seat_id)}" aria-label="${safe(text('seats.seatLabel', { name: seatLabel(seat), status }))}"><header><h3>${safe(seatLabel(seat))}</h3><span>${safe(status)}</span></header><div class="thpt-card-row" role="group" aria-label="${safe(text('cards.seatCards', { name: seatLabel(seat) }))}">${cards}</div><dl><div><dt>${safe(text('table.stack'))}</dt><dd>${safe(tokenAmount(seat.stack))}</dd></div><div><dt>${safe(text('table.contributed'))}</dt><dd>${safe(tokenAmount(seat.contributed))}</dd></div></dl></article>`;
}


// Render the five-card community board with reserved fixed geometry.
function communityHtml(hand) {
  // Copy only server-revealed community cards.
  const visible = hand.community_cards || [];
  // Fill all five stable positions with visible cards or localized empty slots.
  const cards = Array.from({ length: 5 }, (_, index) => visible[index] ? localizedCard(visible[index]) : emptyCardSlot(index + 1)).join('');
  // Return one labeled board region for keyboard and screen-reader navigation.
  return `<section class="thpt-community" data-testid="thpt-community-cards" aria-label="${safe(text('table.communityCards'))}"><h3>${safe(text('table.communityCards'))}</h3><div class="thpt-card-row" role="group" aria-label="${safe(text('cards.communityGroup'))}">${cards}</div></section>`;
}


// Render a terminal human summary after every ledger movement reconciles.
function resultHtml(hand) {
  // Omit result space until the hand is fully settled.
  if (hand.phase !== 'settled' || !hand.result) return '';
  // Resolve the localized outcome heading from the documented result enum.
  const outcome = text(`results.${hand.result.human_outcome}`);
  // Resolve the human showdown rank only when the human reached comparison.
  const rankName = hand.result.hand_ranks?.human?.name;
  // Render optional localized hand-rank detail without exposing the enum.
  const rank = rankName ? `<p>${safe(text('result.handRank'))}: <strong>${safe(text(`poker.${rankName}`))}</strong></p>` : '';
  // Return refund, pot share, and net in one reserved result region.
  return `<section class="thpt-result" data-testid="thpt-result" role="status"><h2>${safe(outcome)}</h2>${rank}<div class="thpt-result-grid"><span>${safe(text('result.refund'))}<strong>${safe(tokenAmount(hand.result.human_refund))}</strong></span><span>${safe(text('result.payout'))}<strong>${safe(tokenAmount(hand.result.human_payout))}</strong></span><span>${safe(text('result.net'))}<strong>${safe(tokenAmount(hand.result.human_net))}</strong></span></div></section>`;
}


// Render the dominant table stage for ready, active, and terminal states.
function stageHtml(hand) {
  // Render localized guidance before any hand has been played.
  if (!hand) return `<section class="thpt-stage thpt-ready" data-testid="thpt-table"><div><h2>${safe(text('stage.readyTitle'))}</h2><p>${safe(text('stage.readyBody'))}</p></div></section>`;
  // Separate the three server-managed opponents from the authenticated human.
  const opponents = hand.seats.filter(seat => seat.kind === 'server_bot').map(seat => seatHtml(seat, hand)).join('');
  // Resolve the authenticated human seat from the stable server shape.
  const human = hand.seats.find(seat => seat.kind === 'human');
  // Render the complete table with a dominant pot and fixed community board.
  return `<section class="thpt-stage" data-testid="thpt-table" aria-label="${safe(text('stage.tableLabel'))}"><section class="thpt-opponents" aria-label="${safe(text('stage.opponents'))}">${opponents}</section><section class="thpt-table-center"><div class="thpt-pot" data-testid="thpt-pot"><span>${safe(text('table.pot'))}</span><strong>${safe(tokenAmount(hand.pot))}</strong></div>${communityHtml(hand)}</section>${human ? `<section class="thpt-human" data-testid="thpt-hole-cards">${seatHtml(human, hand)}</section>` : ''}${resultHtml(hand)}</section>`;
}


// Render stable fixed-limit controls for every table phase.
function controlsHtml(hand) {
  // Keep configuration editable only when no active hand exists.
  const startDisabled = Boolean(state?.active_hand) || busy;
  // Read server-authoritative legal actions for this human turn.
  const legal = new Set(hand?.legal_actions || []);
  // Enable call only when the server currently permits it.
  const callDisabled = busy || !legal.has('call');
  // Enable fold only when the server currently permits it.
  const foldDisabled = busy || !legal.has('fold');
  // Return wager configuration, escrow explanation, and stable action placement.
  return `<aside class="thpt-panel thpt-controls" aria-label="${safe(text('controls.title'))}"><h2>${safe(text('controls.title'))}</h2><label for="thpt-wager">${safe(text('controls.baseWager'))}</label><input id="thpt-wager" type="number" min="0.01" max="20000" step="0.01" value="${safe(baseWager)}"${startDisabled ? ' disabled' : ''}><p class="thpt-reserve">${safe(text('controls.reserved'))}: <strong data-testid="thpt-reserve-amount">${safe(tokenAmount(baseWager * RESERVED_BET_UNITS))}</strong></p><button type="button" class="thpt-primary" data-action="start-hand"${startDisabled ? ' disabled' : ''}>${safe(text('controls.startHand'))}</button><div class="thpt-decision"><button type="button" class="thpt-primary" data-action="call"${callDisabled ? ' disabled' : ''}>${safe(text('controls.call'))}</button><button type="button" data-action="fold"${foldDisabled ? ' disabled' : ''}>${safe(text('controls.fold'))}</button></div><p>${safe(text('controls.help'))}</p></aside>`;
}


// Render a bounded localized action log without a competing scroll container.
function historyHtml(hand) {
  // Keep only the newest eight actions so the desktop rail remains viewport-fit.
  const actions = (hand?.action_log || []).slice(-8).reverse();
  // Render one localized row per human or server-managed decision.
  const rows = actions.map(item => {
    // Resolve the actor name from the current public seat collection.
    const actor = seatLabel(item.seat_id, hand);
    // Resolve action and phase enums through the owned resource domain.
    const description = item.action === 'call' ? text('history.call', { actor, amount: tokenAmount(item.amount), phase: text(`phases.${item.phase}`) }) : text('history.fold', { actor, phase: text(`phases.${item.phase}`) });
    // Return one plain row without internal ids or timestamps as debug labels.
    return `<li><span>${safe(description)}</span></li>`;
  }).join(''); // Collapse the bounded history rows into one list fragment.
  // Show a localized empty state before the first table decision.
  const content = rows || `<li class="thpt-muted">${safe(text('history.empty'))}</li>`;
  // Return the data rail with rules and the bounded action history.
  return `<aside class="thpt-panel thpt-data" aria-label="${safe(text('history.title'))}"><h2>${safe(text('history.title'))}</h2><ul class="thpt-history" data-testid="thpt-action-log">${content}</ul><section class="thpt-rules"><h3>${safe(text('rules.title'))}</h3><ul><li>${safe(text('rules.escrow'))}</li><li>${safe(text('rules.actions'))}</li><li>${safe(text('rules.showdown'))}</li></ul></section></aside>`;
}


// Return scoped styles that keep the table dominant and stack cleanly.
function stylesHtml() {
  // Keep the desktop center stage wider than both support rails combined.
  const desktop = '.thpt-shell{display:grid;gap:16px;min-width:0}.thpt-header{display:flex;align-items:end;justify-content:space-between;gap:16px}.thpt-header h1{margin:0}.thpt-phase{min-width:150px;padding:7px 12px;border:1px solid var(--gold);border-radius:999px;text-align:center;color:var(--gold,#f6d47a)}.thpt-layout{display:grid;grid-template-columns:minmax(205px,.6fr) minmax(570px,2.4fr) minmax(220px,.65fr);gap:15px;align-items:start;min-width:0}.thpt-panel,.thpt-stage{border:1px solid var(--border);border-radius:16px;background:var(--panel-strong);padding:15px;min-width:0}.thpt-controls{display:grid;align-content:start;gap:12px}.thpt-controls input,.thpt-controls button{min-height:44px}.thpt-primary{background:var(--red,#a92a38);color:#fff}.thpt-decision{display:grid;grid-template-columns:1fr 1fr;gap:9px}.thpt-reserve,.thpt-controls p,.thpt-muted{color:var(--muted,#b8c7c0)}.thpt-stage{display:grid;gap:14px;background:radial-gradient(circle at 50% 45%,rgba(35,17,61,.42),rgba(21,10,36,.96) 72%)}.thpt-opponents{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.thpt-seat{display:grid;gap:8px;padding:10px;border:1px solid rgba(255,255,255,.13);border-radius:12px;background:rgba(0,0,0,.16)}.thpt-seat.is-acting{outline:2px solid var(--gold);outline-offset:2px}.thpt-seat.is-folded{opacity:.58}.thpt-seat.is-winner{box-shadow:0 0 0 3px var(--gold)}.thpt-seat header{display:flex;justify-content:space-between;gap:7px;align-items:center}.thpt-seat h3{margin:0;font-size:.95rem}.thpt-seat header span{font-size:.72rem;color:var(--muted,#b8c7c0)}.thpt-card-row{display:flex;flex-wrap:nowrap;justify-content:center;gap:7px;min-width:0}.thpt-seat .playing-card,.thpt-card-slot{flex:0 1 clamp(2.65rem,5vw,4.6rem);min-width:2.65rem}.thpt-card-slot{display:inline-flex;aspect-ratio:5/7;border:2px dashed rgba(255,255,255,.24);border-radius:.65rem;background:rgba(0,0,0,.12)}.thpt-seat dl{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:0}.thpt-seat dl div{min-width:0}.thpt-seat dt{color:var(--muted,#b8c7c0);font-size:.68rem}.thpt-seat dd{margin:2px 0 0;font-size:.78rem;overflow-wrap:anywhere}.thpt-table-center{display:grid;place-items:center;gap:13px;min-height:220px;padding:14px;border-radius:48%;background:rgba(35,17,61,.58);border:2px solid var(--border)}.thpt-pot{display:grid;justify-items:center}.thpt-pot strong{font-size:clamp(1.1rem,2vw,1.55rem)}.thpt-community{display:grid;justify-items:center;gap:8px;width:100%}.thpt-community h3{margin:0}.thpt-community .playing-card,.thpt-community .thpt-card-slot{flex-basis:clamp(3rem,7vw,5.2rem)}.thpt-human{display:grid;place-items:center}.thpt-human .thpt-seat{width:min(420px,100%)}.thpt-result{display:grid;gap:10px;padding:12px;border-radius:12px;background:rgba(255,215,128,.1);text-align:center}.thpt-result h2,.thpt-result p{margin:0}.thpt-result-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.thpt-result-grid span{display:grid;gap:3px}.thpt-history,.thpt-rules ul{display:grid;gap:8px;margin:0;padding-left:1.1rem}.thpt-history li{padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.1)}.thpt-rules{margin-top:18px}.thpt-ready{min-height:520px;place-content:center;text-align:center}.thpt-shell button:focus-visible,.thpt-shell input:focus-visible{outline:3px solid var(--gold);outline-offset:2px}';
  // Compress cards and supporting panels when desktop shell height is constrained.
  const compactHeight = '@media(max-height:950px) and (min-width:1101px){.thpt-shell{gap:8px}.thpt-header p{margin:0}.thpt-layout{gap:10px}.thpt-panel,.thpt-stage{padding:8px}.thpt-controls,.thpt-stage{gap:7px}.thpt-opponents{gap:6px}.thpt-seat{gap:4px;padding:6px}.thpt-seat .playing-card,.thpt-card-slot{flex-basis:2.25rem;min-width:2.1rem}.thpt-seat dt{font-size:.62rem}.thpt-seat dd{font-size:.7rem}.thpt-table-center{min-height:100px;padding:6px;gap:5px}.thpt-community{gap:4px}.thpt-community h3{font-size:.88rem}.thpt-community .playing-card,.thpt-community .thpt-card-slot{flex-basis:2.6rem;min-width:2.35rem}.thpt-result{gap:4px;padding:6px}.thpt-result h2{font-size:1rem}.thpt-result p,.thpt-result-grid{font-size:.75rem}.thpt-history,.thpt-rules ul{gap:5px;font-size:.78rem}.thpt-history li{padding-bottom:4px}.thpt-rules{margin-top:10px}.thpt-ready{min-height:360px}}';
  // Stack controls, stage, and data using document scrolling on tablet widths.
  const tablet = '@media(max-width:1100px){.thpt-layout{grid-template-columns:1fr}.thpt-controls{order:1}.thpt-stage{order:2}.thpt-data{order:3}.thpt-ready{min-height:300px}}';
  // Prevent card and result clipping on the governed mobile viewport.
  const mobile = '@media(max-width:560px){.thpt-header{align-items:start;flex-direction:column}.thpt-phase{min-width:0}.thpt-panel,.thpt-stage{padding:12px}.thpt-opponents{grid-template-columns:1fr}.thpt-table-center{border-radius:24px;min-height:190px}.thpt-result-grid,.thpt-decision{grid-template-columns:1fr}.thpt-card-row{gap:4px}.thpt-community .playing-card,.thpt-community .thpt-card-slot{min-width:2.55rem}}';
  // Remove all decorative transitions when reduced motion is requested.
  const reduced = '@media(prefers-reduced-motion:reduce){.thpt-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}';
  // Return one game-owned style block without global selectors.
  return `<style>${desktop}${compactHeight}${tablet}${mobile}${reduced}</style>`;
}


// Render the complete three-zone surface from cached authoritative state.
function render() {
  // Stop when an async completion arrives after route unmount.
  if (!root) return;
  // Read the active or newest completed hand once per render.
  const hand = currentHand();
  // Replace the route outlet atomically so controls and stage cannot drift.
  root.innerHTML = `${stylesHtml()}<section class="thpt-shell" data-testid="texas-holdem-practice-table"><header class="thpt-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="thpt-phase" role="status">${safe(phaseLabel(hand))}</span></header><div class="thpt-layout">${controlsHtml(hand)}${stageHtml(hand)}${historyHtml(hand)}</div></section>`;
  // Attach semantic control handlers to the newly rendered elements.
  bindEvents();
}


// Execute one atomic browser action with stable disabled-state cleanup.
async function runAction(action) {
  // Ignore overlapping controls while an API request is in flight.
  if (busy) return;
  // Disable controls before beginning the action.
  busy = true;
  // Preserve action placement while showing disabled state.
  render();
  // Start protected handling so failures use localized shell feedback.
  try {
    // Execute the supplied public API action.
    await action();
  // Translate all API failures through the active game domain.
  } catch (error) {
    // Show localized copy instead of raw server prose.
    toast(errorText(error));
  // Always restore controls after success or failure.
  } finally {
    // Release the action lock.
    busy = false;
    // Rerender only when the route remains mounted.
    render();
  }
}


// Start one replay-safe escrow-backed practice hand.
async function startHand(requestedWager) {
  // Normalize the captured finite fixed-limit unit before preserving a retry payload.
  const normalizedWager = Number.isFinite(Number(requestedWager)) ? Math.min(20000, Math.max(0.01, Number(requestedWager))) : 1;
  // Reuse both id and wager after an ambiguous failure so retries cannot conflict or change exposure.
  pendingStart = pendingStart || { actionId: nextActionId(), baseWager: normalizedWager };
  // Keep the visible preview aligned with the exact command retained for retry.
  baseWager = pendingStart.baseWager;
  // Post the preserved fixed-limit unit and unique action id through the public endpoint.
  const payload = await post(`${API_ROOT}/hands`, withCurrentPlayer({ action_id: pendingStart.actionId, base_wager: pendingStart.baseWager }));
  // Store returned reload-safe state after committed escrow reservation.
  state = payload.state;
  // Clear the retry key only after the server proves the logical hand exists.
  pendingStart = null;
  // Refresh the authenticated shared wallet after the ledger debit.
  await refreshBalance();
}


// Apply one human call or fold with a stable per-decision retry id.
async function decide(action) {
  // Read the active hand before constructing its action route.
  const hand = state?.active_hand;
  // Stop stale events after settlement or route state replacement.
  if (!hand || !hand.legal_actions?.includes(action)) return;
  // Reuse the unresolved id only for the same hand and decision payload.
  pendingDecision = pendingDecision?.handId === hand.hand_id && pendingDecision?.phase === hand.phase && pendingDecision?.action === action ? pendingDecision : { handId: hand.hand_id, phase: hand.phase, action, actionId: nextActionId() };
  // Post the action through the one documented human-decision endpoint.
  const payload = await post(`${API_ROOT}/hands/${encodeURIComponent(hand.hand_id)}/actions`, withCurrentPlayer({ action_id: pendingDecision.actionId, action, expected_phase: pendingDecision.phase }));
  // Store the server's complete human and opponent transition sequence.
  state = payload.state;
  // Clear the decision retry record only after a confirmed response.
  pendingDecision = null;
  // Refresh the wallet when terminal refund or payout may have occurred.
  await refreshBalance();
}


// Attach semantic control handlers after each deterministic full render.
function bindEvents() {
  // Preserve valid wager edits in cached pre-hand configuration.
  const wagerInput = root.querySelector('#thpt-wager');
  // Update the escrow preview in place so blur cannot replace a pending clicked button.
  if (wagerInput) wagerInput.oninput = () => cacheWager(wagerInput.value);
  // Wire the primary start action through shared busy handling.
  const startButton = root.querySelector('[data-action="start-hand"]');
  // Start one retry-safe hand when the button exists.
  if (startButton) startButton.onclick = () => runAction(() => startHand(baseWager));
  // Wire the fixed-limit call action.
  const callButton = root.querySelector('[data-action="call"]');
  // Apply one call only when server state permits it.
  if (callButton) callButton.onclick = () => runAction(() => decide('call'));
  // Wire the terminal fold action.
  const foldButton = root.querySelector('[data-action="fold"]');
  // Apply one fold only when server state permits it.
  if (foldButton) foldButton.onclick = () => runAction(() => decide('fold'));
}


// Export the catalog-owned lazy game module contract proposed for #77.
export const TexasHoldemPracticeTableGame = {
  // Expose the stable module id used by catalog navigation.
  id: 'texas_holdem_practice_table',
  // Leave player-facing labels to descriptor and locale resources.
  label: '',
  // Load locale and authenticated state before rendering visible text.
  async mount(node) {
    // Store the route outlet for subsequent deterministic renders.
    root = node;
    // Capture mount identity so late promises cannot repaint another route.
    const mountedRoot = node;
    // Install the shared card stylesheet idempotently.
    ensureSharedCardStyles();
    // Load both active and fallback game-owned dictionaries.
    await loadI18nDomain(DOMAIN);
    // Stop when locale loading completed after unmount.
    if (root !== mountedRoot) return;
    // Subscribe to locale changes without losing active hand state.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read the authenticated player's reload-safe private state.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Stop when the state request completed after route teardown.
    if (root !== mountedRoot) return;
    // Cache the authoritative state used by every panel.
    state = payload.state;
    // Restore the active hand's wager unit after direct navigation or reload.
    baseWager = state?.active_hand?.base_wager || baseWager;
    // Render the complete issue #95 surface.
    render();
    // Refresh the shared authenticated wallet without game-owned balance text.
    await refreshBalance();
  },
  // Release every game-owned lifecycle resource on route change.
  unmount() {
    // Unsubscribe the locale callback when it exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the callback reference so repeated teardown remains safe.
    unsubscribeLocale = null;
    // Clear cached player state from the inactive module.
    state = null;
    // Release unresolved browser retry records with the inactive view.
    pendingStart = null;
    // Release any unresolved decision record with the inactive view.
    pendingDecision = null;
    // Release the busy flag so a later mount starts cleanly.
    busy = false;
    // Clear the route node so late promises cannot render another screen.
    root = null;
    // No timers remain because this module owns none.
  },
};
