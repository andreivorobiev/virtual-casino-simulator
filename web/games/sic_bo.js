// Implement the isolated issue #88 Sic Bo browser module without shared shell edits.

// Import session-aware API helpers so caller identity remains compatibility-only input.
import { api, post, currentPlayerPath, withCurrentPlayer } from '../core/api.js';
// Import shared shell feedback, escaping, and wallet refresh helpers.
import { refreshBalance, renderCommittedWagerBalance, safe, toast } from '../core/ui.js';
// Import locale loading, formatting, and lifecycle subscription helpers.
import { formatNumber, loadI18nDomain, onLocaleChange, t } from '../core/i18n.js';
// Reuse the merged #97 reduced-motion and route-cleanup timer primitive.
import { createMotionTimerScope } from '../core/motion.js';

// Store the game-owned locale domain used by every visible and accessible string.
const DOMAIN = 'games/sic_bo';
// Store the additive v1 API root once for all public actions.
const API_ROOT = '/api/v1/games/sic-bo';
// Preserve the server catalog's stable board group order.
const GROUP_ORDER = ['ranges', 'totals', 'singles', 'doubles', 'triples', 'combinations'];
// Define the normal decorative reveal delay consumed only through #97 motion scope.
const REVEAL_DURATION_MS = 650;
// Map public API error categories to paired localized copy.
const ERROR_KEYS = Object.freeze({ VALIDATION_ERROR: 'errors.validation', INSUFFICIENT_FUNDS: 'errors.insufficientFunds', CONFLICT: 'errors.conflict', UNAUTHORIZED: 'errors.unauthorized', FORBIDDEN: 'errors.unauthorized' });
// Map ordinary die faces to code-native pip grid cells.
const PIP_CELLS = Object.freeze({ 1: [5], 2: [1, 9], 3: [1, 5, 9], 4: [1, 3, 7, 9], 5: [1, 3, 5, 7, 9], 6: [1, 3, 4, 6, 7, 9] });
// Store the mounted route outlet for deterministic rerenders.
let root = null;
// Store the latest authenticated player-owned game state.
let gameState = null;
// Store server-supplied immutable table-position metadata.
let betCatalog = [];
// Store selected table positions and their fixed play-token amounts.
let selectedWagers = new Map();
// Store the amount assigned to each newly selected position.
let wagerAmount = 1;
// Prevent overlapping atomic actions while a request or reveal is active.
let busy = false;
// Mark the decorative reveal phase without inventing client-authoritative dice.
let rolling = false;
// Retain an unresolved action identity for safe ambiguous-response retry.
let pendingActionId = null;
// Retain the exact unresolved wager snapshot so retries cannot change semantics.
let pendingWagers = null;
// Retain the last committed wager map so one click can repeat the same shake.
let lastBet = null;
// Own one disposable #97 timer scope per mount.
let motionScope = null;
// Store the locale unsubscribe callback so route exit releases it.
let unsubscribeLocale = null;
// Increment mount generation so late async results cannot repaint another route.
let mountGeneration = 0;
// Provide a bounded action-id fallback counter when randomUUID is unavailable.
let actionCounter = 0;


// Resolve one game-owned localized string without a visible hard-coded fallback.
function text(key, params = {}) {
  // Delegate every player-facing string to the loaded EN/RU domain.
  return t(key, params, DOMAIN);
}


// Format play-token values without currency or replacement-looking glyphs.
function tokenAmount(value) {
  // Format at ledger precision and append localized play-token terminology.
  return `${formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${text('units.playTokens')}`;
}


// Create one bounded caller action identity through an injectable UUID seam.
export function nextActionId(uuidFactory = globalThis.crypto?.randomUUID?.bind(globalThis.crypto)) {
  // Prefer a cryptographic browser UUID while keeping a readable game prefix.
  if (typeof uuidFactory === 'function') return `sb-${uuidFactory()}`;
  // Advance the fallback counter to distinguish actions created in one millisecond.
  actionCounter += 1;
  // Combine timestamp and counter without using client randomness for game outcomes.
  return `sb-${Date.now().toString(36)}-${actionCounter.toString(36)}`;
}


// Translate a machine bet definition through parameterized game-owned keys.
export function betLabel(bet, translate = text) {
  // Translate range and any-triple positions without numeric parameters.
  if (['small', 'big', 'any_triple'].includes(bet.kind)) return translate(`bets.${bet.kind}`);
  // Translate exact totals and repeated-face positions through one selection parameter.
  if (['total', 'single', 'double', 'triple'].includes(bet.kind)) return translate(`bets.${bet.kind}`, { value: bet.selection });
  // Translate a two-number combination through both ordered face values.
  return translate('bets.combo', { left: bet.values?.[0], right: bet.values?.[1] });
}


// Translate fixed or occurrence-based payout odds without client settlement logic.
function oddsLabel(bet) {
  // Explain one-of-a-kind payouts that depend on face occurrence count.
  if (bet.kind === 'single') return text('bets.singleOdds');
  // Display all fixed net odds using the regulator's "to 1" convention.
  return text('bets.fixedOdds', { value: bet.net_odds });
}


// Return the active recovery round or newest settled history row.
function currentRound() {
  // Prefer an interrupted actionable round before bounded recent history.
  return gameState?.active_round || gameState?.recent_rounds?.slice(-1)[0] || null;
}


// Identify active nonterminal state that must render recovery copy even after dice commit.
export function isRecoveryRound(activeRound, round) {
  // Treat every active phase before settlement as incomplete result data.
  return Boolean(activeRound && round?.phase !== 'settled');
}


// Return whether selection controls must preserve an unresolved wager snapshot.
function selectionLocked() {
  // Lock edits during server work, prepared recovery, or ambiguous network retry.
  return busy || Boolean(gameState?.active_round) || Boolean(pendingActionId);
}


// Sum selected position amounts at two-decimal display precision.
function totalSelectedWager() {
  // Add fixed selected values and normalize ordinary floating-point display noise.
  return Math.round([...selectedWagers.values()].reduce((total, amount) => total + Number(amount || 0), 0) * 100) / 100;
}


// Translate internal lifecycle state into player-facing phase copy.
function phaseLabel() {
  // Announce the decorative reveal while the final server result is hidden.
  if (rolling) return text('phases.rolling');
  // Announce interrupted server settlement that can be resumed safely.
  if (gameState?.active_round) return text('phases.recovering');
  // Announce the newest aggregate result after settlement.
  const round = currentRound();
  // Translate the server-owned outcome when a settled round exists.
  if (round?.phase === 'settled') return text(`phases.${round.outcome}`);
  // Announce selected wagers before the first shake.
  if (selectedWagers.size) return text('phases.selected');
  // Default to the ready table phase.
  return text('phases.ready');
}


// Translate known API categories without exposing server English in Russian UI.
function errorText(error) {
  // Resolve a known code or the paired generic fallback key.
  return text(ERROR_KEYS[error?.code] || 'errors.generic');
}


// Render one code-native accessible die without special-font glyphs.
function dieHtml(face, index, animated = false) {
  // Read the pip cells only for one authoritative ordinary face.
  const activeCells = new Set(PIP_CELLS[face] || []);
  // Render nine stable grid cells so pip geometry never shifts stage layout.
  const pips = Array.from({ length: 9 }, (_, offset) => `<span class="sb-pip${activeCells.has(offset + 1) ? ' is-visible' : ''}" aria-hidden="true"></span>`).join('');
  // Use a localized accessible name for revealed dice and hide decorative blanks.
  const aria = face ? ` role="img" aria-label="${safe(text('dice.faceAria', { number: index + 1, value: face }))}"` : ' aria-hidden="true"';
  // Return the stable die shell with optional transform-only rolling treatment.
  return `<div class="sb-die${animated ? ' is-rolling' : ''}"${aria}>${pips}</div>`;
}


// Render the fixed dice tray for ready, rolling, recovering, and settled states.
function diceTrayHtml(round) {
  // Render three blank moving dice while awaiting the authoritative response.
  if (rolling) {
    // Preserve stable stage height and a localized live status region.
    return `<section class="sb-dice-tray is-rolling" role="status" aria-live="polite" aria-label="${safe(text('dice.rollingAria'))}">${[0, 1, 2].map((_, index) => dieHtml(null, index, true)).join('')}</section>`;
  }
  // Render authoritative server faces only after wager commitment.
  if (round?.dice?.length === 3) {
    // Preserve API reveal order and localized group semantics.
    return `<section class="sb-dice-tray" aria-label="${safe(text('dice.trayAria'))}">${round.dice.map((face, index) => dieHtml(face, index)).join('')}</section>`;
  }
  // Render stable blank dice for ready or pre-debit recovery without revealing private state.
  return `<section class="sb-dice-tray is-ready" aria-label="${safe(text('dice.readyAria'))}">${[0, 1, 2].map((_, index) => dieHtml(null, index)).join('')}</section>`;
}


// Render one semantic selectable table-position button.
function betButtonHtml(bet) {
  // Resolve whether this position is currently part of the fixed snapshot.
  const selected = selectedWagers.has(bet.id);
  // Read the selected amount only when this position is covered.
  const amount = selectedWagers.get(bet.id);
  // Disable edits while an atomic or recovery action owns the snapshot.
  const disabled = selectionLocked();
  // Build a localized accessible description beyond color alone.
  const ariaLabel = text(selected ? 'bets.selectedAria' : 'bets.availableAria', { label: betLabel(bet), odds: oddsLabel(bet), amount: selected ? tokenAmount(amount) : tokenAmount(wagerAmount) });
  // Render localized label, odds, and selected amount with a stable machine id.
  return `<button type="button" class="sb-bet${selected ? ' is-selected' : ''}" data-bet-id="${safe(bet.id)}" aria-pressed="${selected}" aria-label="${safe(ariaLabel)}"${disabled ? ' disabled' : ''}><span class="sb-bet-label">${safe(betLabel(bet))}</span><span class="sb-bet-odds">${safe(oddsLabel(bet))}</span>${selected ? `<span class="sb-bet-amount">${safe(tokenAmount(amount))}</span>` : ''}</button>`;
}


// Render one localized board group from server-owned position metadata.
function betGroupHtml(group) {
  // Select only positions assigned to this stable server group.
  const bets = betCatalog.filter(bet => bet.group === group);
  // Return nothing when integration metadata omits an unknown group.
  if (!bets.length) return '';
  // Render the semantic group heading and position grid.
  return `<section class="sb-bet-group" data-bet-group="${safe(group)}" aria-label="${safe(text('aria.betGroup', { group: text(`groups.${group}`) }))}"><h3>${safe(text(`groups.${group}`))}</h3><div class="sb-bet-grid">${bets.map(betButtonHtml).join('')}</div></section>`;
}


// Render all fifty positions beneath the dominant dice stage.
function boardHtml() {
  // Preserve canonical server order while using localized group headings.
  const groups = GROUP_ORDER.map(betGroupHtml).join('');
  // Return the complete selectable board with a stable browser hook.
  return `<section class="sb-board" aria-label="${safe(text('aria.betBoard'))}"><header><h2>${safe(text('board.title'))}</h2><p>${safe(text('board.help'))}</p></header>${groups}</section>`;
}


// Render the latest result summary without recomputing server settlement.
function resultHtml(round) {
  // Explain every active recovery before complete settlement fields are durable.
  if (isRecoveryRound(gameState?.active_round, round)) return `<section class="sb-result is-recovery" role="status"><h2>${safe(text('result.recoveryTitle'))}</h2><p>${safe(text('result.recoveryBody'))}</p></section>`;
  // Render ready guidance before any completed result exists.
  if (!round?.dice) return `<section class="sb-result is-ready"><h2>${safe(text('result.readyTitle'))}</h2><p>${safe(text('result.readyBody'))}</p></section>`;
  // Render aggregate values supplied by the authoritative server.
  return `<section class="sb-result" role="status" aria-live="polite" aria-label="${safe(text('aria.result'))}"><h2>${safe(text(`result.${round.outcome}Title`))}</h2><div class="sb-result-grid"><span>${safe(text('dice.total'))}<strong>${safe(round.total)}</strong></span><span>${safe(text('result.wager'))}<strong>${safe(tokenAmount(round.total_wager))}</strong></span><span>${safe(text('result.return'))}<strong>${safe(tokenAmount(round.total_return))}</strong></span><span>${safe(text('result.net'))}<strong>${safe(tokenAmount(round.net))}</strong></span></div><p>${safe(round.triple ? text('dice.triple') : text('dice.notTriple'))}</p></section>`;
}


// Render stake configuration, aggregate preview, and one stable primary action.
function controlsHtml() {
  // Read the active recovery record when an interrupted action exists.
  const active = gameState?.active_round;
  // Disable configuration while the exact snapshot must remain unchanged.
  const locked = selectionLocked();
  // Choose the localized primary action for normal play, recovery, or in-flight reveal.
  const actionLabel = rolling || busy ? text('controls.rolling') : active || pendingActionId ? text('controls.resume') : text('controls.shake');
  // Disable the action only when ready state has no selected positions or work is active.
  const actionDisabled = busy || (!active && !pendingActionId && selectedWagers.size === 0);
  // Enable the one-click repeat only when a prior wager map exists and no shake or unresolved retry is active.
  const repeatDisabled = busy || rolling || Boolean(pendingActionId) || !lastBet;
  // Return the stable control rail without moving its primary button between phases.
  return `<aside class="sb-panel sb-controls" aria-label="${safe(text('aria.controls'))}"><h2>${safe(text('controls.title'))}</h2><label for="sb-wager">${safe(text('controls.wager'))}</label><input id="sb-wager" type="number" min="0.01" max="10000" step="0.01" value="${safe(wagerAmount)}"${locked ? ' disabled' : ''}><p class="sb-help">${safe(locked ? text('controls.lockedHelp') : text('controls.wagerHelp'))}</p><div class="sb-control-metric"><span>${safe(text('controls.selectedCount'))}</span><strong>${safe(selectedWagers.size)}</strong></div><div class="sb-control-metric"><span>${safe(text('controls.totalWager'))}</span><strong>${safe(tokenAmount(totalSelectedWager()))}</strong></div><button type="button" class="sb-primary" data-action="shake"${actionDisabled ? ' disabled' : ''}>${safe(actionLabel)}</button><button type="button" class="sb-repeat" data-action="repeat"${repeatDisabled ? ' disabled' : ''}>${safe(text('controls.repeat'))}</button><button type="button" data-action="clear"${locked || !selectedWagers.size ? ' disabled' : ''}>${safe(text('controls.clear'))}</button></aside>`;
}


// Render one selected-bet slip row with localized removal semantics.
function slipRowHtml([betId, amount]) {
  // Resolve server metadata for localized label and odds display.
  const bet = betCatalog.find(item => item.id === betId);
  // Hide stale selection rows when metadata cannot describe them safely.
  if (!bet) return '';
  // Build a localized remove-button accessible name.
  const removeLabel = text('slip.removeAria', { label: betLabel(bet) });
  // Return one aligned selected position row.
  return `<li><div><strong>${safe(betLabel(bet))}</strong><span>${safe(oddsLabel(bet))}</span></div><span>${safe(tokenAmount(amount))}</span><button type="button" data-remove-bet="${safe(betId)}" aria-label="${safe(removeLabel)}"${selectionLocked() ? ' disabled' : ''}>${safe(text('slip.remove'))}</button></li>`;
}


// Render bounded result history through localized labels and numeric values.
function historyHtml() {
  // Read the newest eight settled rows for a compact data rail.
  const rows = (gameState?.recent_rounds || []).slice(-8).reverse();
  // Render a localized empty state before the first completed shake.
  if (!rows.length) return `<p class="sb-empty">${safe(text('history.empty'))}</p>`;
  // Render each round without exposing action IDs or debug phases.
  return `<ol class="sb-history">${rows.map((round, index) => `<li><span>${safe(text('history.round', { number: rows.length - index }))}</span><strong>${safe((round.dice || []).join(' - '))}</strong><span>${safe(text('history.net', { amount: tokenAmount(round.net) }))}</span></li>`).join('')}</ol>`;
}


// Render the single intentional scrolling data rail for slip and history.
function dataHtml() {
  // Build selected rows or paired empty guidance.
  const slip = selectedWagers.size ? `<ul class="sb-slip">${[...selectedWagers.entries()].map(slipRowHtml).join('')}</ul>` : `<p class="sb-empty">${safe(text('slip.empty'))}</p>`;
  // Return one keyboard-focusable themed scroll region with no nested scrollbars.
  return `<aside class="sb-panel sb-data" tabindex="0" aria-label="${safe(text('aria.dataRail'))}"><section aria-label="${safe(text('aria.betSlip'))}"><h2>${safe(text('slip.title'))}</h2>${slip}</section><section aria-label="${safe(text('aria.history'))}"><h2>${safe(text('history.title'))}</h2>${historyHtml()}</section><section><h2>${safe(text('paytable.title'))}</h2><p>${safe(text('paytable.note'))}</p></section></aside>`;
}


// Return game-owned responsive styles without touching the shared stylesheet.
function stylesHtml() {
  // Keep the center stage dominant at desktop and stack control, stage, data below the shared breakpoint.
  return `<style>
    /* Own the complete Sic Bo layout inside the lazy game module. */
    .sb-shell{display:grid;gap:16px;min-width:0}.sb-header{display:flex;align-items:end;justify-content:space-between;gap:12px}.sb-header h1,.sb-header p{margin:0}.sb-phase{min-height:36px;padding:8px 13px;border:1px solid var(--gold);border-radius:999px;display:inline-flex;align-items:center}.sb-layout{display:grid;grid-template-columns:minmax(220px,.7fr) minmax(0,2.5fr) minmax(235px,.78fr);gap:16px;align-items:start;min-width:0}.sb-panel,.sb-stage{border:1px solid var(--gold);border-radius:16px;background:rgba(20,10,34,.84);padding:16px;min-width:0}.sb-controls{display:grid;gap:12px}.sb-controls h2,.sb-data h2,.sb-board h2,.sb-bet-group h3{margin:0}.sb-controls input{min-height:44px}.sb-primary{min-height:46px;background:var(--brand);color:#fff}.sb-help,.sb-board header p,.sb-empty,.sb-bet-odds,.sb-slip span,.sb-result p{color:var(--muted,#b8c8c1)}.sb-control-metric{display:flex;justify-content:space-between;gap:8px;padding:10px;border-radius:10px;background:rgba(255,255,255,.045)}.sb-stage{display:grid;gap:14px}.sb-dice-tray{min-height:132px;display:flex;align-items:center;justify-content:center;gap:clamp(14px,3vw,32px);border-radius:14px;background:radial-gradient(circle at 50% 20%,rgba(255,59,107,.14),rgba(0,0,0,.18));overflow:hidden}.sb-die{width:96px;aspect-ratio:1;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);padding:12px;border:2px solid #f5ead0;border-radius:18px;background:#fff7e8;box-shadow:0 12px 24px rgba(0,0,0,.28)}.sb-pip{display:grid;place-items:center}.sb-pip.is-visible::after{content:"";width:15px;height:15px;border-radius:50%;background:#13231c}.sb-die.is-rolling{animation:sb-tumble .65s ease-in-out infinite alternate}.sb-result{min-height:116px;padding:14px;border:1px solid rgba(255,255,255,.12);border-radius:12px}.sb-result h2,.sb-result p{margin:0}.sb-result-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.sb-result-grid span{display:grid;gap:4px;padding:9px;border-radius:9px;background:rgba(255,255,255,.045)}.sb-board{display:grid;gap:10px}.sb-board header{display:flex;align-items:end;justify-content:space-between;gap:12px}.sb-board header p{margin:0;max-width:52ch}.sb-bet-group{display:grid;gap:6px}.sb-bet-group h3{font-size:.88rem;color:var(--gold)}.sb-bet-grid{display:grid;gap:6px}.sb-bet-group[data-bet-group="ranges"] .sb-bet-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sb-bet-group[data-bet-group="totals"] .sb-bet-grid{grid-template-columns:repeat(7,minmax(0,1fr))}.sb-bet-group[data-bet-group="singles"] .sb-bet-grid,.sb-bet-group[data-bet-group="doubles"] .sb-bet-grid{grid-template-columns:repeat(6,minmax(0,1fr))}.sb-bet-group[data-bet-group="triples"] .sb-bet-grid{grid-template-columns:repeat(7,minmax(0,1fr))}.sb-bet-group[data-bet-group="combinations"] .sb-bet-grid{grid-template-columns:repeat(5,minmax(0,1fr))}.sb-bet{min-height:46px;padding:6px;display:grid;place-items:center;gap:2px;border:1px solid rgba(255,255,255,.16);border-radius:9px;background:rgba(255,255,255,.045);line-height:1.08}.sb-bet.is-selected{border-color:var(--gold);box-shadow:inset 0 0 0 2px var(--gold)}.sb-bet-label{font-weight:700}.sb-bet-odds,.sb-bet-amount{font-size:.72rem}.sb-bet-amount{color:var(--gold)}.sb-data{max-height:720px;overflow-y:auto;display:grid;gap:18px;scrollbar-width:thin;scrollbar-color:var(--gold) rgba(255,255,255,.05)}.sb-data:focus-visible,.sb-shell button:focus-visible,.sb-shell input:focus-visible{outline:3px solid var(--gold);outline-offset:2px}.sb-data section{display:grid;gap:10px}.sb-slip,.sb-history{display:grid;gap:8px;margin:0;padding:0;list-style:none}.sb-slip li,.sb-history li{display:grid;gap:5px;padding:9px;border-radius:9px;background:rgba(255,255,255,.045)}.sb-slip li{grid-template-columns:minmax(0,1fr) auto}.sb-slip li div{display:grid}.sb-slip li button{grid-column:1/-1;min-height:42px}.sb-history li strong{letter-spacing:.12em}@keyframes sb-tumble{from{transform:translateY(-5px) rotate(-5deg);opacity:.72}to{transform:translateY(5px) rotate(5deg);opacity:1}}.sb-repeat{min-height:46px;background:transparent;color:var(--gold);border:1px solid var(--gold)}.sb-repeat:disabled{opacity:.5}
    /* Fit the complete stage inside desktop primary while preserving 42px table controls. */
    @media(min-width:1101px) and (min-height:951px){.sb-shell{gap:10px}.sb-header h1{font-size:2.25rem;line-height:1}.sb-layout{gap:12px}.sb-panel,.sb-stage{padding:12px}.sb-stage{gap:7px}.sb-dice-tray{min-height:96px}.sb-die{width:72px;padding:8px;border-radius:14px}.sb-pip.is-visible::after{width:11px;height:11px}.sb-result{min-height:72px;padding:8px}.sb-result-grid{gap:5px;margin:5px 0}.sb-result-grid span{gap:2px;padding:5px}.sb-board{gap:4px}.sb-board header p{font-size:.8rem}.sb-bet-group{gap:2px}.sb-bet-group h3{font-size:.76rem}.sb-bet-grid{gap:3px}.sb-bet{min-height:42px;padding:2px}.sb-bet-odds,.sb-bet-amount{font-size:.66rem}.sb-data{max-height:776px}}
    /* Let desktop compact use one themed game-screen scroll instead of clipped panels. */
    @media(max-height:950px) and (min-width:1101px){#view.game-screen:has(.sb-shell){overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--gold) rgba(255,255,255,.05)}#view.game-screen:has(.sb-shell) .sb-data{max-height:none;overflow:visible}}
    /* Stack control, stage, and data in the documented mobile journey. */
    @media(max-width:1100px){.sb-layout{grid-template-columns:1fr}.sb-controls{order:1}.sb-stage{order:2}.sb-data{order:3;max-height:none;overflow:visible}.sb-result-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    /* Preserve touch targets and prevent horizontal overflow on narrow phones. */
    @media(max-width:620px){.sb-header{align-items:start;flex-direction:column}.sb-panel,.sb-stage{padding:12px}.sb-die{width:74px;padding:9px}.sb-pip.is-visible::after{width:11px;height:11px}.sb-board header{align-items:start;flex-direction:column}.sb-bet-group[data-bet-group] .sb-bet-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sb-result-grid{grid-template-columns:1fr}.sb-slip li{grid-template-columns:1fr}}
    /* Collapse decorative motion while preserving asynchronous #97 callback semantics. */
    @media(prefers-reduced-motion:reduce){.sb-shell *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
  </style>`; // Close the game-owned style block returned to the route renderer.
}


// Render the complete localized three-zone surface from cached server state.
function render() {
  // Stop when an async completion arrives after route unmount.
  if (!root) return;
  // Read active recovery or newest settled round once per render.
  const round = currentRound();
  // Replace the route outlet atomically so stage, controls, and data never drift.
  root.innerHTML = `${stylesHtml()}<section class="sb-shell" data-testid="sic-bo-table" aria-label="${safe(text('aria.game'))}"><header class="sb-header"><div><p>${safe(text('eyebrow'))}</p><h1>${safe(text('title'))}</h1></div><span class="sb-phase" role="status" aria-label="${safe(text('aria.phase'))}">${safe(phaseLabel())}</span></header><div class="sb-layout">${controlsHtml()}<main class="sb-stage">${diceTrayHtml(round)}${resultHtml(round)}${boardHtml()}</main>${dataHtml()}</div></section>`;
  // Attach semantic event handlers to the newly rendered controls.
  bindEvents();
}


// Parse one UI wager without silently rounding values rejected by the API contract.
export function parseWagerAmount(rawValue, { stepMismatch = false } = {}) {
  // Reject browser-reported increments that do not align with the cent step.
  if (stepMismatch) return null;
  // Preserve the caller's decimal spelling so excess precision remains detectable.
  const normalized = String(rawValue ?? '').trim();
  // Accept unsigned decimal notation with no more than two fractional digits.
  if (!/^(?:\d+|\d*\.\d{1,2})$/.test(normalized)) return null;
  // Convert only after the precision contract has been enforced.
  const value = Number(normalized);
  // Reject non-finite values outside the server's per-position boundary.
  if (!Number.isFinite(value) || value < 0.01 || value > 10000) return null;
  // Return the already cent-aligned value without any client-side rounding.
  return value;
}


// Validate the current wager input without issuing token movement.
function readWagerInput() {
  // Read the mounted numeric input so native step validity can be enforced.
  const input = root?.querySelector('#sb-wager');
  // Parse the mounted spelling or cached value through the exact-cent seam.
  return parseWagerAmount(input?.value ?? wagerAmount, { stepMismatch: Boolean(input?.validity?.stepMismatch) });
}


// Toggle one table position while preserving the amount selected at that moment.
function toggleBet(betId) {
  // Ignore stale clicks while a fixed request snapshot is owned elsewhere.
  if (selectionLocked()) return;
  // Remove an already selected position without changing other amounts.
  if (selectedWagers.has(betId)) {
    // Delete only the requested position.
    selectedWagers.delete(betId);
    // Refresh pressed states and totals.
    render();
    // Stop after deselection.
    return;
  }
  // Validate the wager assigned to this new selection.
  const amount = readWagerInput();
  // Explain invalid input through paired localized copy.
  if (amount === null) {
    // Use the shared toast without exposing hard-coded English.
    toast(text('errors.invalidWager'));
    // Stop before changing selection state.
    return;
  }
  // Cache the normalized input for future position selections.
  wagerAmount = amount;
  // Store the fixed position amount in the next request snapshot.
  selectedWagers.set(betId, amount);
  // Refresh pressed state, slip, and aggregate preview.
  render();
}


// Restore a persisted active request into browser selection and retry state.
function restoreActiveRound() {
  // Read the server-owned recovery record when present.
  const active = gameState?.active_round;
  // Leave normal selection state unchanged when no recovery is active.
  if (!active) return;
  // Restore the exact canonical wagers required for safe resume.
  selectedWagers = new Map(Object.entries(active.wagers || {}).map(([betId, amount]) => [betId, Number(amount)]));
  // Preserve the same caller action identity across reload recovery.
  pendingActionId = active.action_id;
  // Freeze the exact snapshot used by every retry attempt.
  pendingWagers = Object.fromEntries(selectedWagers);
}


// Schedule one result reveal through the shared disposable motion scope.
export function scheduleReveal({ timerScope, onReveal, duration = REVEAL_DURATION_MS }) {
  // Require the exact #97 scheduling interface so no unmanaged timer is introduced.
  if (!timerScope || typeof timerScope.schedule !== 'function') throw new TypeError('timerScope must provide schedule');
  // Require a callback before allocating timer ownership.
  if (typeof onReveal !== 'function') throw new TypeError('onReveal must be a function');
  // Delegate reduced-motion timing and lifecycle cancellation to #97.
  return timerScope.schedule(onReveal, duration);
}


// Re-apply the last committed wager map and re-fire one shake without a timer.
async function repeat() {
  // Ignore repeat while an atomic action, reveal, or unresolved retry owns the snapshot, or without a prior wager map.
  if (busy || rolling || pendingActionId || !lastBet) return;
  // Restore the previous fixed wager map into the local selection state.
  selectedWagers = new Map(Object.entries(lastBet.wagers).map(([betId, amount]) => [betId, Number(amount)]));
  // Fire the shared exactly-once shake action with the restored wagers.
  await shake();
}


// Execute or safely resume one server-authoritative round.
async function shake() {
  // Ignore duplicate clicks while an atomic action or reveal remains active.
  if (busy) return;
  // Reuse active recovery, ambiguous retry, or create one new action identity.
  pendingActionId = gameState?.active_round?.action_id || pendingActionId || nextActionId();
  // Freeze the exact active, pending, or newly selected wager snapshot.
  pendingWagers = gameState?.active_round?.wagers || pendingWagers || Object.fromEntries(selectedWagers);
  // Require at least one selected position before beginning an action.
  if (!Object.keys(pendingWagers || {}).length) {
    // Clear an unused generated identity so selection remains editable.
    pendingActionId = null;
    // Clear the empty snapshot.
    pendingWagers = null;
    // Explain the required selection through paired localized copy.
    toast(text('errors.betRequired'));
    // Stop before server or timer work.
    return;
  }
  // Capture this mount generation so late responses cannot repaint a new route.
  const generation = mountGeneration;
  // Lock selection before beginning the atomic server action.
  busy = true;
  // Show the stable decorative rolling phase without choosing client dice.
  rolling = true;
  // Render disabled controls and fixed stage geometry.
  render();
  // Start protected API handling so known failures remain localized.
  try {
    // Submit only the exact stable action id and frozen wager snapshot.
    const payload = await post(`${API_ROOT}/rounds`, withCurrentPlayer({ action_id: pendingActionId, wagers: pendingWagers }));
    // Ignore a response delivered after unmount or a later mount generation.
    if (!root || generation !== mountGeneration) return;
    // Show the committed debit while the dice remain in their decorative rolling phase. (LEDGER-031, issue #585)
    renderCommittedWagerBalance(payload.ledger?.wager);
    // Schedule the authoritative result reveal through the owned #97 timer scope.
    scheduleReveal({ timerScope: motionScope, onReveal: () => {
      // Ignore a callback cancelled logically by a later route generation.
      if (!root || generation !== mountGeneration) return;
      // Replace cached state only with server-owned post-ledger state.
      gameState = payload.state;
      // Refresh immutable table metadata when supplied by the action response.
      betCatalog = payload.bets || betCatalog;
      // Remember the exact settled wager map so one click can repeat the same shake next round.
      lastBet = { wagers: { ...(payload.round?.wagers || pendingWagers || {}) } };
      // Release the action identity only after a successful authoritative response.
      pendingActionId = null;
      // Release the frozen retry snapshot after success.
      pendingWagers = null;
      // End the decorative rolling phase.
      rolling = false;
      // Re-enable controls for the next independent action.
      busy = false;
      // Render authoritative dice, settlement, and history.
      render();
      // Refresh the shared authenticated wallet without blocking the result stage.
      refreshBalance().catch(() => {});
    } }); // Close the reveal callback and its #97 scheduling request.
  // Convert API or network failures into game-owned localized feedback.
  } catch (error) {
    // Stop when the route was unmounted while the request failed.
    if (!root || generation !== mountGeneration) return;
    // Validation and insufficient-funds failures commit no action and may be edited safely.
    if (['VALIDATION_ERROR', 'INSUFFICIENT_FUNDS'].includes(error?.code)) {
      // Release the unused identity after a server-confirmed pre-commit rejection.
      pendingActionId = null;
      // Release the rejected snapshot so the player can edit it.
      pendingWagers = null;
    }
    // End decorative motion after every surfaced failure.
    rolling = false;
    // Re-enable retry or editing according to retained action state.
    busy = false;
    // Restore stable controls and board state.
    render();
    // Show paired localized copy instead of the server's English message.
    toast(errorText(error));
  }
}


// Attach semantic control handlers after every atomic render.
function bindEvents() {
  // Keep the wager input cache synchronized when configuration is editable.
  const wagerInput = root.querySelector('#sb-wager');
  // Validate and store changed input without selecting or moving tokens.
  if (wagerInput) wagerInput.onchange = () => {
    // Read one normalized candidate from the mounted field.
    const amount = readWagerInput();
    // Explain and restore the prior value when the candidate is invalid.
    if (amount === null) {
      // Show paired validation guidance.
      toast(text('errors.invalidWager'));
      // Rerender the last valid cached value.
      render();
      // Stop before updating cached configuration.
      return;
    }
    // Cache the normalized amount for new selections.
    wagerAmount = amount;
    // Rerender accessible bet descriptions with the new prospective amount.
    render();
  };
  // Wire every table position to semantic pressed-state selection.
  root.querySelectorAll('[data-bet-id]').forEach(button => {
    // Toggle only the position identified by server metadata.
    button.onclick = () => toggleBet(button.dataset.betId);
  });
  // Wire slip removal controls through the same position toggle path.
  root.querySelectorAll('[data-remove-bet]').forEach(button => {
    // Remove the selected position while configuration is editable.
    button.onclick = () => toggleBet(button.dataset.removeBet);
  });
  // Wire the stable primary action to new or recovery play.
  const shakeButton = root.querySelector('[data-action="shake"]');
  // Begin one action when the control exists.
  if (shakeButton) shakeButton.onclick = () => shake();
  // Wire the one-click repeat that re-fires the previous wager map.
  const repeatButton = root.querySelector('[data-action="repeat"]');
  // Re-apply and re-fire the last committed shake when the control exists.
  if (repeatButton) repeatButton.onclick = () => repeat();
  // Wire clear to selection-only state without any backend action.
  const clearButton = root.querySelector('[data-action="clear"]');
  // Clear every editable selection and refresh the preview.
  if (clearButton) clearButton.onclick = () => { selectedWagers.clear(); render(); };
}


// Export the catalog-owned lazy game module contract prepared for #77 integration.
export const SicBoGame = {
  // Expose the stable module id used by proposed catalog navigation.
  id: 'sic_bo',
  // Leave lobby presentation to the proposed descriptor and locale domain.
  label: '',
  // Load localization and authenticated state before rendering visible content.
  async mount(node) {
    // Advance generation and capture ownership for this async mount.
    mountGeneration += 1;
    // Capture ownership before the first await so an obsolete mount cannot adopt a successor.
    const generation = mountGeneration;
    // Store the new route outlet for deterministic rendering.
    root = node;
    // Reset the repeatable wager map so a new mount never inherits a stale one before state reconciles history.
    lastBet = null;
    // Create one disposable reduced-motion-aware timer owner for this route.
    motionScope = createMotionTimerScope();
    // Load both active and fallback game-owned resources before rendering.
    await loadI18nDomain(DOMAIN);
    // Stop when this mount was replaced during resource loading.
    if (!root || root !== node || generation !== mountGeneration) return;
    // Subscribe to in-place locale changes without remounting or losing selection.
    unsubscribeLocale = onLocaleChange(() => render());
    // Read reload-safe state for the authenticated current player.
    const payload = await api(currentPlayerPath(`${API_ROOT}/state`));
    // Ignore state delivered after route unmount or replacement.
    if (!root || root !== node || generation !== mountGeneration) return;
    // Cache the player-owned active and recent state.
    gameState = payload.state;
    // Cache the complete fifty-position rule metadata.
    betCatalog = payload.bets || [];
    // Restore any interrupted exact action without exposing private dice.
    restoreActiveRound();
    // Recover a repeatable wager map from the newest settled round so repeat survives a reload.
    const recovered = gameState?.recent_rounds?.slice(-1)[0];
    // Restore the repeatable configuration only when the newest settled round exposes its wager map.
    lastBet = recovered?.wagers ? { wagers: { ...recovered.wagers } } : null;
    // Render the complete localized surface.
    render();
    // Refresh the shared wallet without game-owned balance text.
    await refreshBalance();
    // Finish inertly when wallet refresh completed after this route lost ownership.
    if (!root || root !== node || generation !== mountGeneration) return;
  },
  // Release every game-owned lifecycle resource on route exit.
  unmount() {
    // Advance generation before cleanup so late promises become inert.
    mountGeneration += 1;
    // Dispose every pending reveal callback and lifecycle listener through #97.
    if (motionScope) motionScope.dispose();
    // Clear the timer-scope reference after disposal.
    motionScope = null;
    // Release the locale subscription when one exists.
    if (unsubscribeLocale) unsubscribeLocale();
    // Clear the subscription reference for repeated unmount safety.
    unsubscribeLocale = null;
    // Clear route-only server state from the inactive module.
    gameState = null;
    // Clear immutable metadata so a future mount reloads current rules.
    betCatalog = [];
    // Clear player selection from the inactive route.
    selectedWagers = new Map();
    // Release unresolved browser action state; backend recovery remains persisted.
    pendingActionId = null;
    // Release the frozen browser wager snapshot.
    pendingWagers = null;
    // Clear the repeatable wager map so the next session starts fresh.
    lastBet = null;
    // Reset atomic and decorative phase flags.
    busy = false;
    // Reset the decorative rolling phase.
    rolling = false;
    // Clear the outlet last so late callbacks fail their root guard.
    root = null;
  },
};
