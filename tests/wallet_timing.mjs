// Verify consistent committed-wager wallet timing without opening a listener or browser. (LEDGER-031, TEST-151)
// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import source reads for catalog-wide wiring checks.
import { readFile } from 'node:fs/promises';
// Import the dependency-free Node test runner.
import test from 'node:test';
// Import portable path resolution for the repository root.
import path from 'node:path';
// Import URL conversion for this tracked test file.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from tests/wallet_timing.mjs.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Retain shell events so authoritative intermediate wallet publication is observable.
const events = [];
// Store fake DOM nodes by stable id.
const nodes = new Map();
// Install the minimal browser storage read by the shared player-identity helper.
globalThis.localStorage = { getItem: () => null };
// Install inert session storage because importing the API helper must not create guest state.
globalThis.sessionStorage = { getItem: () => null };
// Install the wallet DOM surface consumed by the shared renderer.
globalThis.document = { cookie: '', getElementById(id) { if (!nodes.has(id)) nodes.set(id, { textContent: '' }); return nodes.get(id); } };
// Install a bounded custom event implementation for shell-cache synchronization.
globalThis.CustomEvent = class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } };
// Install the authenticated current-player surface before importing production helpers.
globalThis.window = { CasinoCurrentUser: { user: { user_id: 'user-1' }, player: { player_id: 'human', token_balance: 1000 } }, CustomEvent: globalThis.CustomEvent, dispatchEvent(event) { events.push(event); return true; } };
// Import the real production renderer only after its browser dependencies exist.
const { renderCommittedWagerBalance } = await import('../web/core/ui.js');

// Prove one matching storage-authored debit synchronously updates shell state and visible wallet.
test('matching committed wager debit publishes its authoritative balance_after', () => {
  // Capture the prior session object so immutable replacement can be verified.
  const prior = window.CasinoCurrentUser;
  // Apply one exact ledger debit event returned by a game action.
  const accepted = renderCommittedWagerBalance({ player_id: 'human', amount: -25, balance_after: 975 });
  // Require a successful render, immutable session replacement, and exact amount.
  assert.equal(accepted, true); assert.notEqual(window.CasinoCurrentUser, prior); assert.equal(window.CasinoCurrentUser.player.token_balance, 975);
  // Require the persistent amount node and shell event to carry the same server-owned value.
  assert.equal(nodes.get('balance').textContent, '975.00'); assert.equal(events.at(-1).detail.player.token_balance, 975);
});

// Prove credits, malformed values, and foreign-player rows can never overwrite the shared wallet.
test('non-wager and foreign ledger evidence fails closed', () => {
  // Capture the last accepted session and visible text before invalid evidence.
  const prior = window.CasinoCurrentUser; const priorText = nodes.get('balance').textContent; const priorEvents = events.length;
  // Reject a settlement credit, a malformed balance, and another player's debit.
  assert.equal(renderCommittedWagerBalance({ player_id: 'human', amount: 50, balance_after: 1025 }), false);
  // Reject non-finite intermediate evidence.
  assert.equal(renderCommittedWagerBalance({ player_id: 'human', amount: -5, balance_after: 'not-a-number' }), false);
  // Reject a correctly shaped but foreign player event.
  assert.equal(renderCommittedWagerBalance({ player_id: 'other', amount: -5, balance_after: 970 }), false);
  // Require all shared state to remain byte-for-byte equivalent at the observable boundary.
  assert.equal(window.CasinoCurrentUser, prior); assert.equal(nodes.get('balance').textContent, priorText); assert.equal(events.length, priorEvents);
});

// Enumerate every response-driven result presentation corrected by the cross-game requirement.
const affectedGames = Object.freeze([
  ['slots.js', "await post('/api/v1/games/slots/spin'", 'refreshBalanceForCompletion('],
  ['big_six_wheel.js', "await post('/api/v1/games/big-six-wheel/spins'", 'refreshBalance('],
  ['sic_bo.js', 'await post(`${API_ROOT}/rounds`', 'refreshBalance('],
  ['chuck_a_luck.js', 'await post(`${API_ROOT}/rolls`', 'refreshBalance('],
  ['crown_and_anchor.js', "await post('/api/v1/games/crown-and-anchor/rounds'", 'refreshBalance('],
  ['over_under_7.js', "await post('/api/v1/games/over-under-7/plays'", 'refreshBalance('],
  ['fan_tan.js', "await post('/api/v1/games/fan-tan/rounds'", 'refreshBalance('],
  ['boule.js', "await post('/api/v1/games/boule/spins'", 'refreshBalance('],
  ['coin_pusher.js', "await post('/api/v1/games/coin-pusher/drops'", 'refreshBalance('],
  ['color_wheel.js', "await post('/api/v1/games/color-wheel/spins'", 'refreshBalance('],
  ['daily_draw_lab.js', "await post('/api/v1/games/daily-draw-lab/draws'", 'refreshBalance('],
  ['faro.js', "await post('/api/v1/games/faro/deals'", 'refreshBalance('],
  ['lucky_grid.js', "await post('/api/v1/games/lucky-grid/reveals'", 'refreshBalance('],
  ['marble_race.js', "await post('/api/v1/games/marble-race/races'", 'refreshBalance('],
  ['pachinko.js', "await post('/api/v1/games/pachinko/drops'", 'refreshBalance('],
  ['pattern_draw.js', "await post('/api/v1/games/pattern-draw/draws'", 'refreshBalance('],
  ['poker_dice.js', "await post('/api/v1/games/poker-dice/rolls'", 'refreshBalance('],
  ['trente_et_quarante.js', "await post('/api/v1/games/trente-et-quarante/coups'", 'refreshBalance('],
]);

// Prove all eighteen response-driven games render the committed debit before their final wallet refresh.
test('every affected response-driven game uses the shared committed-wager renderer', async () => {
  // Inspect each exact frontend source independently so one missing game identifies itself.
  for (const [filename, requestMarker, settlementMarker] of affectedGames) {
    // Read only the tracked game module.
    const source = await readFile(path.join(ROOT, 'web', 'games', filename), 'utf8');
    // Locate the authoritative request that begins the corrected lifecycle.
    const requestIndex = source.indexOf(requestMarker);
    // Locate the shared intermediate renderer after that exact request.
    const committedIndex = source.indexOf('renderCommittedWagerBalance(', requestIndex);
    // Locate the later authoritative settlement refresh.
    const settlementIndex = source.indexOf(settlementMarker, committedIndex);
    // Require request, committed debit, and final refresh in strict presentation order.
    assert.ok(requestIndex >= 0 && committedIndex > requestIndex && settlementIndex > committedIndex, `${filename} wallet timing order is incomplete`);
  }
});

// Prove Baccarat retains its placement debit and defers only the settlement refresh to visible reveal completion.
test('Baccarat publishes settlement only from the reveal-completion callback', async () => {
  // Read the exact Baccarat frontend source.
  const source = await readFile(path.join(ROOT, 'web', 'games', 'baccarat.js'), 'utf8');
  // Isolate the reveal-completion function from the later deal function.
  const finishStart = source.indexOf('function finishRevealLater(show)'); const dealStart = source.indexOf('async function dealNow(show = true)');
  // Isolate the deal implementation before the queue wrapper.
  const dealEnd = source.indexOf('// Define deal to queue one coup', dealStart);
  // Require final refresh in the reveal callback and no early settlement refresh in dealNow.
  assert.ok(source.slice(finishStart, dealStart).includes('refreshBalance().catch')); assert.equal(source.slice(dealStart, dealEnd).includes('await refreshBalance()'), false);
});

// Prove wallet success clears and closes before any secondary refresh can race another click. (TOKEN-007)
test('wallet top-up clears and closes before secondary shell refresh', async () => {
  // Read the extracted application lifecycle source that owns persistent wallet controls.
  const source = await readFile(path.join(ROOT, 'web', 'core', 'app_bootstrap.js'), 'utf8');
  // Isolate the top-up handler before logout wiring.
  const start = source.indexOf('addButton.onclick = async () =>'); const handler = source.slice(start, source.indexOf('// Read the logout button', start));
  // Locate the committed render, local clear, popover close, and secondary refresh.
  const committed = handler.indexOf('updateCurrentUserShell()'); const cleared = handler.indexOf("amountInput.value = ''"); const closed = handler.indexOf("querySelector('.wallet-menu')?.removeAttribute('open')"); const refreshed = handler.indexOf('await refreshShellState({ quiet: true })');
  // Require all four boundaries in the exact safe order.
  assert.ok(committed >= 0 && cleared > committed && closed > cleared && refreshed > closed);
});
