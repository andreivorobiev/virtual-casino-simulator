// Verify the PR-526 real-reel landing composition, stagger schedule, and cleanup guards for premium Slots.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import source reads from the standard library for guard-wiring assertions.
import { readFile } from 'node:fs/promises';
// Import the dependency-free Node test runner.
import test from 'node:test';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';
// Import the seeded generator the game uses for decorative reel filler.
import { createSeededRandom } from '../../../web/core/dice.js';
// Import the real route-owned timer scope so teardown tests exercise production disposal.
import { createMotionTimerScope } from '../../../web/core/motion.js';

// Create one externally controlled promise for API and wallet cancellation tests.
function deferred() {
  // Retain the resolver outside promise construction.
  let resolve = null;
  // Create the promise whose completion is owned by the test.
  const promise = new Promise(done => { resolve = done; });
  // Return the paired promise and resolver without exposing mutable wrapper state.
  return Object.freeze({ promise, resolve });
}

// Create one deterministic clock used by the real createMotionTimerScope implementation.
function createFakeClock() {
  // Allocate monotonically increasing handles so cancellation can be asserted exactly.
  let nextHandle = 1;
  // Retain pending one-shot callbacks by handle.
  const timers = new Map();
  // Retain interval handles without firing audio ticks in a dependency-free test.
  const intervals = new Set();
  // Register one pending callback and return its opaque numeric handle.
  const setTimeoutFn = callback => { const handle = nextHandle; nextHandle += 1; timers.set(handle, callback); return handle; };
  // Cancel one pending callback and report whether it was owned.
  const clearTimeoutFn = handle => timers.delete(handle);
  // Register a dormant interval token so game audio cleanup remains observable without a real clock loop.
  const setIntervalFn = () => { const handle = nextHandle; nextHandle += 1; intervals.add(handle); return handle; };
  // Cancel one dormant interval token.
  const clearIntervalFn = handle => intervals.delete(handle);
  // Run every currently pending one-shot callback, including callbacks scheduled by another callback.
  const runAll = () => { while (timers.size) { const batch = Array.from(timers.entries()); timers.clear(); for (const [, callback] of batch) callback(); } };
  // Return the exact fake-clock surface needed by the browser harness.
  return Object.freeze({ setTimeoutFn, clearTimeoutFn, setIntervalFn, clearIntervalFn, runAll, get pending() { return timers.size; } });
}

// Create one browser-like element with stable selector-owned children.
function createFakeElement(selector = 'element') {
  // Retain child identity across rerenders so old and remounted roots can be distinguished.
  const children = new Map();
  // Retain assigned attributes for focused ownership assertions.
  const attributes = new Map();
  // Retain applied classes without parsing HTML.
  const classes = new Set();
  // Build one style object with the property setter used by reel strips.
  const style = { setProperty(name, value) { this[name] = value; } };
  // Select the input value required by real Slots control wiring.
  const initialValue = selector.includes('#lines') ? '20' : selector.includes('#lineBet') ? '1.00' : selector.includes('.rounds') ? '1' : selector.includes('.speed') ? 'medium' : '';
  // Build the minimal browser element surface exercised by real mount, render, spin, and unmount.
  const element = {
    selector,
    dataset: {},
    style,
    classList: { add: (...names) => names.forEach(name => classes.add(name)), remove: (...names) => names.forEach(name => classes.delete(name)), contains: name => classes.has(name), toggle: (name, force) => { if (force === false) classes.delete(name); else classes.add(name); } },
    value: initialValue,
    innerHTML: '',
    textContent: '',
    hidden: false,
    disabled: false,
    open: false,
    append() {},
    addEventListener(type, handler) { this[`on${type}`] = handler; },
    removeEventListener() {},
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.get(name) ?? null; },
    querySelector(childSelector) { if (!children.has(childSelector)) children.set(childSelector, createFakeElement(childSelector)); return children.get(childSelector); },
    querySelectorAll() { return []; },
    getBoundingClientRect() { const top = selector.includes('slot-cell-1-') ? 100 : 0; return { left: 0, top, right: 100, bottom: top + 100, width: 100, height: 100 }; },
  };
  // Return the stable fake element.
  return element;
}

// Install a deterministic browser seam used by actual SlotsGame mount and unmount calls.
function installFakeBrowser() {
  // Create one clock before mount so the real scope captures these exact timer functions.
  const clock = createFakeClock();
  // Track document-owned nodes used by wallet publication.
  const documentNodes = new Map();
  // Track dispatched shell events so stale wallet publication is observable.
  const dispatched = [];
  // Retain one optional delayed Slots spin response.
  let delayedSpin = null;
  // Retain one optional delayed authenticated-wallet response.
  let delayedWallet = null;
  // Count authoritative spin requests independently from render activity.
  let spinRequests = 0;
  // Count authenticated wallet reads so the second awaited boundary can be located.
  let walletRequests = 0;
  // Build a storage shim for current-player and locale helpers.
  const storage = new Map();
  // Install browser storage without writing to disk.
  globalThis.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, String(value)), removeItem: key => storage.delete(key) };
  // Install session storage without retaining any guest proof.
  globalThis.sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
  // Install the fake document used by real game mount and wallet rendering.
  globalThis.document = { cookie: 'casino_csrf=test', documentElement: { lang: 'en-US', dir: 'ltr', dataset: {}, setAttribute() {} }, head: { append() {} }, createElement: tag => createFakeElement(tag), getElementById: id => { if (!documentNodes.has(id)) documentNodes.set(id, createFakeElement(`#${id}`)); return documentNodes.get(id); }, querySelectorAll() { return []; } };
  // Install a bounded custom event object used by shared wallet publication.
  globalThis.CustomEvent = class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } };
  // Install online navigator state so authoritative requests are permitted.
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { onLine: true, language: 'en-US' } });
  // Install a query-free route location for locale initialization and sanitized diagnostics.
  globalThis.location = { search: '', href: 'https://casino.test/games/slots', origin: 'https://casino.test', pathname: '/games/slots' };
  // Install the window surface read by i18n, motion, audio, and wallet helpers.
  globalThis.window = { CasinoCurrentUser: { user: { user_id: 'user-1' }, player: { player_id: 'human', token_balance: 1000 } }, CustomEvent: globalThis.CustomEvent, matchMedia: () => ({ matches: false }), addEventListener() {}, removeEventListener() {}, dispatchEvent(event) { dispatched.push(event); return true; }, requestAnimationFrame(callback) { callback(); return 1; }, cancelAnimationFrame() {} };
  // Expose the same media-query seam on globalThis for prefersReducedMotion.
  globalThis.matchMedia = query => globalThis.window.matchMedia(query);
  // Install the deterministic timers before actual game mount creates its production scope.
  globalThis.setTimeout = clock.setTimeoutFn; globalThis.clearTimeout = clock.clearTimeoutFn; globalThis.setInterval = clock.setIntervalFn; globalThis.clearInterval = clock.clearIntervalFn;
  // Install one inert resize observer for shared route rendering.
  globalThis.ResizeObserver = class { observe() {} disconnect() {} };
  // Build one standard successful JSON response.
  const response = data => ({ ok: true, status: 200, async json() { return { ok: true, data }; } });
  // Build the state envelope consumed by each actual Slots mount.
  const slotsState = roundId => ({ state: { last_spins: [], free_spins: 0, progressive: 200 }, config: { paytable: {}, economics: {} }, spin: { round_id: roundId, grid: RESULT_GRID, active_lines: 20, line_bet: 1, cost: 20, payout: 0, wins: [], free_spin: false, free_spins_remaining: 0, progressive: 200, progressive_hit: 0 } });
  // Route every fetch through exact public paths used by the game and shared modules.
  globalThis.fetch = async input => {
    // Normalize the requested URL without retaining options or credentials.
    const url = String(input);
    // Return a deterministic locale manifest and empty dictionaries.
    if (url.startsWith('/i18n/')) return response(url.endsWith('manifest.json') ? { schemaVersion: 1, defaultLocale: 'en-US', fallbackLocale: 'en-US', aliases: {}, locales: [], domains: ['common'] } : {});
    // Return the actual mounted Slots state.
    if (url.startsWith('/api/v1/games/slots/state')) return response(slotsState('state-spin'));
    // Return bounded bot capability responses.
    if (url.includes('/eligible-bots')) return response({ bots: [], capabilities: { supports_bots: false, strategies: [] } });
    // Control the exact Slots action response for API-pending teardown proof.
    if (url === '/api/v1/games/slots/spin') { spinRequests += 1; const gate = delayedSpin; delayedSpin = null; return response(gate ? await gate.promise : slotsState(`spin-${spinRequests}`)); }
    // Control the shared wallet's second await independently from the game response.
    if (url === '/api/v2/me') { walletRequests += 1; const gate = delayedWallet; delayedWallet = null; return response(gate ? await gate.promise : { user: { user_id: 'user-1' }, player: { player_id: 'human', token_balance: 1000 + walletRequests } }); }
    // Return a legacy wallet shape for completeness when current-user state is deliberately absent.
    if (url.startsWith('/api/v1/players/')) return response({ player: { player_id: 'human', balance: 1000 } });
    // Fail loudly when real game code reaches a route the focused harness did not review.
    throw new Error(`unexpected Slots test request: ${url}`);
  };
  // Return controller hooks without exposing mutable internals to the game.
  return { clock, dispatched, documentNodes, delaySpin() { delayedSpin = deferred(); return delayedSpin; }, delayWallet() { delayedWallet = deferred(); return delayedWallet; }, get spinRequests() { return spinRequests; }, get walletRequests() { return walletRequests; } };
}

// Install the browser seam before shared frontend modules read global state.
const browser = installFakeBrowser();
// Import the tested game exports only after installing the minimal browser global.
const { SlotsGame, composeLandingStrip, reelStopDuration, countEarlyScatters, createSlotsSpinCompletion, createSlotsMotionWait, REEL_BASE_STOP_MS, REEL_STAGGER_MS, REEL_SETTLE_MS, REEL_HOLD_MS, REEL_ANTICIPATION_MS, REEL_TRAVEL_BASE_ROWS, REEL_TRAVEL_STEP_ROWS, REDUCED_HOLD_MS, AUTOPLAY_HOLD_MS, SLOT_MOTION_PROFILES } = await import('../../../web/games/slots.js');
// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text for guard-wiring assertions.
const source = await readFile(path.join(root, 'web', 'games', 'slots.js'), 'utf8');

// Store one committed result grid whose columns are all distinct for landing assertions.
const RESULT_GRID = [['SEVEN', 'CHERRY', 'BAR', 'BELL', 'WILD'], ['LEMON', 'SCATTER', 'SEVEN', 'CHERRY', 'BAR'], ['BELL', 'WILD', 'LEMON', 'SCATTER', 'CHERRY']];
// Store one distinct launch grid representing the symbols already visible on the cabinet.
const SHOWN_GRID = [['BAR', 'BELL', 'CHERRY', 'LEMON', 'SEVEN'], ['WILD', 'BAR', 'BELL', 'CHERRY', 'LEMON'], ['CHERRY', 'LEMON', 'BAR', 'WILD', 'BELL']];

// Wait until one asynchronous production boundary becomes observable without using a timer.
async function waitFor(predicate, message) {
  // Give chained promises a bounded number of microtask turns to reach the expected boundary.
  for (let attempt = 0; attempt < 100; attempt += 1) { if (predicate()) return; await Promise.resolve(); }
  // Fail with one stable diagnostic when production code never reached the boundary.
  throw new Error(message);
}

// Advance staged production timers until the requested asynchronous boundary is observable.
async function advanceClockUntil(predicate, message) {
  // Alternate timer batches and promise continuations because each governed reel phase schedules the next stage after an await.
  for (let attempt = 0; attempt < 100; attempt += 1) { if (predicate()) return; browser.clock.runAll(); await Promise.resolve(); }
  // Fail with the same bounded diagnostic discipline as listener-free ordinary waits.
  throw new Error(message);
}

// Drive pending fake-clock callbacks and microtasks until one actual game action terminates.
async function settleWithClock(promise) {
  // Track whether the production action settled without racing an unbounded real timer.
  let settled = false;
  // Retain a rejection so it can be rethrown after deterministic clock progress.
  let failure = null;
  // Observe terminal completion without replacing the original promise.
  promise.then(() => { settled = true; }, error => { failure = error; settled = true; });
  // Alternate fake-clock batches with microtasks so awaited production stages can schedule later work.
  for (let attempt = 0; attempt < 100 && !settled; attempt += 1) { browser.clock.runAll(); await Promise.resolve(); }
  // Re-throw any production failure after all deterministic cleanup has run.
  if (failure) throw failure;
  // Require the game action to terminate rather than silently deadlock.
  assert.equal(settled, true, 'actual Slots action must terminate under the fake clock');
  // Return the original resolved value for callers that need it.
  return promise;
}

// Verify SLOT-021 every landing strip finishes on exactly the authoritative rows for its column.
test('SLOT-021 landing strips finish on the committed grid rows in order', () => {
  // Exercise all five reels.
  for (let column = 0; column < 5; column += 1) {
    const tiles = composeLandingStrip({ grid: RESULT_GRID, column, shownGrid: SHOWN_GRID, random: createSeededRandom(`slots-${column}`) }); // Compose one landing.
    assert.deepEqual(tiles.slice(0, 3), [RESULT_GRID[0][column], RESULT_GRID[1][column], RESULT_GRID[2][column]], `column ${column} must land on its authoritative rows`); // Prove the top of the strip is the committed result.
    assert.deepEqual(tiles.slice(-3), [SHOWN_GRID[0][column], SHOWN_GRID[1][column], SHOWN_GRID[2][column]], `column ${column} must launch from the visible symbols`); // Prove the launch frame is seamless with the cabinet.
    assert.equal(tiles.length, 3 + REEL_TRAVEL_BASE_ROWS + column * REEL_TRAVEL_STEP_ROWS + 3, `column ${column} travel length must follow the per-column schedule`); // Prove later reels travel farther.
  }
});

// Verify SLOT-001 strip composition is deterministic for one committed round identity.
test('SLOT-001 landing filler is deterministic per round identity and frozen', () => {
  const first = composeLandingStrip({ grid: RESULT_GRID, column: 2, shownGrid: SHOWN_GRID, random: createSeededRandom('slot_round_42') }); // Compose the strip once.
  const second = composeLandingStrip({ grid: RESULT_GRID, column: 2, shownGrid: SHOWN_GRID, random: createSeededRandom('slot_round_42') }); // Recompose from the same identity.
  assert.deepEqual(first, second); // Prove one committed round always replays identically.
  assert.equal(Object.isFrozen(first), true); // Prevent callers from mutating a composed landing.
});

// Verify SLOT-020 the stop schedule staggers left to right inside the governed band.
test('SLOT-020 reel stops stagger left to right within the 140-240 ms band', () => {
  // Compare every adjacent reel pair without anticipation.
  for (let column = 1; column < 5; column += 1) {
    const gap = reelStopDuration(column, false) - reelStopDuration(column - 1, false); // Measure one adjacent stop gap.
    assert.ok(gap >= 140 && gap <= 240, `adjacent stop gap ${gap} must stay inside the governed stagger band`); // Prove the stagger honors the governed band.
  }
  assert.equal(reelStopDuration(0, false), REEL_BASE_STOP_MS); // Prove the first reel owns the base budget.
  assert.equal(reelStopDuration(4, true) - reelStopDuration(4, false), REEL_ANTICIPATION_MS); // Prove anticipation extends only the final reel.
  assert.equal(reelStopDuration(3, true), reelStopDuration(3, false)); // Prove earlier reels never inherit the tease extension.
});

// Verify SLOT-032 every selectable profile lands its fifth reel inside the governed final-stop band.
test('SLOT-032 slow medium and fast profiles keep exact stop bands and stagger', () => {
  const bands = { slow: [3800, 4800], medium: [2800, 3600], fast: [1600, 2200] }; // Bind the permanent product bands.
  for (const [profile, [minimum, maximum]] of Object.entries(bands)) { const finalReveal = reelStopDuration(4, false, profile) + REEL_SETTLE_MS + REEL_HOLD_MS; assert.ok(finalReveal >= minimum && finalReveal <= maximum, `${profile} final reveal ${finalReveal}ms is outside its governed band`); for (let column = 1; column < 5; column += 1) { const gap = reelStopDuration(column, false, profile) - reelStopDuration(column - 1, false, profile); assert.ok(gap >= 140 && gap <= 240, `${profile} stagger ${gap}ms is outside the governed band`); } }
  assert.deepEqual(Object.keys(SLOT_MOTION_PROFILES), ['slow', 'medium', 'fast']); // Pin the complete public selector vocabulary.
});

// Verify SLOT-023 the anticipation tease triggers only from scatters visible before the final reel.
test('SLOT-023 early-scatter detection counts only the first four reels', () => {
  assert.equal(countEarlyScatters(RESULT_GRID), 2); // Count the two scatters landing before the final reel.
  assert.equal(countEarlyScatters(SHOWN_GRID), 0); // Prove a scatter-free grid never teases.
  const lastReelOnly = [['CHERRY', 'BAR', 'BELL', 'LEMON', 'SCATTER'], ['BAR', 'BELL', 'LEMON', 'CHERRY', 'SCATTER'], ['BELL', 'LEMON', 'CHERRY', 'BAR', 'SCATTER']]; // Build a grid whose scatters all sit on the final reel.
  assert.equal(countEarlyScatters(lastReelOnly), 0); // Prove final-reel scatters cannot tease their own reel.
});

// Verify MOTION-005 the comfort and autoplay reveals keep their governed budgets.
test('MOTION-005 reduced-motion and autoplay holds keep their governed budgets', () => {
  assert.ok(REDUCED_HOLD_MS >= 400 && REDUCED_HOLD_MS <= 800); // Prove the comfort reveal honors the governed band.
  assert.equal(AUTOPLAY_HOLD_MS, 180); // Preserve the legacy fallback constant without using it for full autoplay presentation.
  assert.match(source, /const motionProfile = show \? selectedSpeed : 'fast';/, 'autoplay must use the complete governed Fast profile'); // Prevent a return to the sub-second unattended shortcut.
});

// Verify MOTION-002 every reel timer runs through the guarded route-owned scope.
test('MOTION-002 reel timers are guarded against a disposed route scope', () => {
  assert.match(source, /if \(!grid \|\| !motionLayer \|\| !cellA \|\| !cellB \|\| !motionScope \|\| motionScope\.disposed\) \{ resolve\(\); return; \}/, 'the landing must degrade when the scope or overlay is gone'); // Pin the landing entry guard.
  assert.match(source, /if \(!motionScope \|\| motionScope\.disposed\) return Promise\.resolve\(\);/, 'waitMotion must degrade on a disposed scope'); // Pin the reveal-wait guard.
  assert.match(source, /if \(motionScope\) motionScope\.dispose\(\);/, 'unmount must dispose the route scope'); // Pin route-teardown timer cleanup.
  assert.match(source, /releaseMotionWaiters\(\); motionScope = null;/, 'unmount must release canceled waits before dropping the scope'); // Pin release-before-null ordering.
  assert.match(source, /releaseMotionWaiters\(\);/, 'unmount must release landing and hold promises whose timers were cancelled'); // Pin deadlock-free waiter cleanup.
  assert.match(source, /if \(activeSpinCompletion\) activeSpinCompletion\.abort\(\);/, 'unmount must terminalize the active presentation once'); // Pin exactly-once abort wiring.
});

// Verify SLOT-028 the spinning render defers foreign repaints so live strips are never destroyed.
test('SLOT-028 locale and bot repaints defer while a spin owns the cabinet', () => {
  assert.match(source, /onLocaleChange\(\(\) => \{ if \(spinning\) \{ pendingRender = true; return; \} render\(\); \}\)/, 'locale changes must defer during a spin'); // Pin the locale deferral.
  assert.match(source, /if \(root && !spinning\) render\(\); else if \(root\) pendingRender = true;/, 'bot-panel refreshes must defer during a spin'); // Pin the bot-panel deferral.
});

// Verify the production timer primitive cancels real scheduled callbacks on disposal.
test('SLOT-037 real createMotionTimerScope disposal cancels its callback exactly once', () => {
  // Create a dedicated deterministic clock independent from the mounted game scope.
  const clock = createFakeClock();
  // Instantiate the real shared motion timer scope with that clock.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null });
  // Count any callback that incorrectly survives disposal.
  let callbacks = 0;
  // Schedule one real scope-owned callback.
  scope.schedule(() => { callbacks += 1; }, REEL_BASE_STOP_MS, { reducedMotion: false });
  // Dispose the real scope and require exactly one pending timer to be cancelled.
  assert.equal(scope.dispose(), 1);
  // Repeated disposal must remain a no-op.
  assert.equal(scope.dispose(), 0);
  // Advancing the fake clock cannot revive the cancelled callback.
  clock.runAll(); assert.equal(callbacks, 0); assert.equal(scope.disposed, true);
});

// Verify an actual SlotsGame API-pending unmount aborts once and a real remount settles cleanly.
test('SLOT-037 actual game API-pending unmount and remount prevent stale continuation', async () => {
  // Capture the bounded completion probe emitted by the real spin path.
  const completions = [];
  // Install the optional production probe without changing game behavior.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Create the first actual route root.
  const firstRoot = createFakeElement('slots-root-one');
  // Mount the exported game object through its production lifecycle.
  await SlotsGame.mount(firstRoot);
  // Delay only the authoritative spin response.
  const spinGate = browser.delaySpin();
  // Record the request count before the controlled action starts.
  const spinCount = browser.spinRequests;
  // Start the real click-wired action.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Wait until the real public POST is pending.
  await waitFor(() => browser.spinRequests === spinCount + 1, 'actual Slots spin did not reach its POST');
  // Unmount the exported game object while its POST is pending.
  SlotsGame.unmount();
  // Mount a distinct actual route before the stale POST returns.
  const secondRoot = createFakeElement('slots-root-two');
  // Re-enter the production mount lifecycle on the new root.
  await SlotsGame.mount(secondRoot);
  // Snapshot the remounted DOM before releasing the stale response.
  const remountedMarkup = secondRoot.innerHTML;
  // Release the old backend response after a new route owns the game.
  spinGate.resolve(undefined);
  // Require the old click promise to terminate instead of hanging or resuming.
  await oldAction;
  // Prove the abandoned action emitted one abort and no settlement.
  assert.deepEqual(completions, [{ game: 'slots', outcome: 'aborted' }]);
  // Prove the stale continuation never repainted the remounted route.
  assert.equal(secondRoot.innerHTML, remountedMarkup);
  // Start a fresh action through the remounted production control.
  const freshAction = secondRoot.querySelector('#spin').onclick();
  // Drive the real route-owned scope to completion.
  await settleWithClock(freshAction);
  // Prove the remounted action independently settled exactly once.
  assert.deepEqual(completions, [{ game: 'slots', outcome: 'aborted' }, { game: 'slots', outcome: 'settled' }]);
  // Tear down the remounted route through the actual game boundary.
  SlotsGame.unmount(); browser.clock.runAll();
  // Remove the optional probe so later tests start isolated.
  delete window.__casinoPresentationProbe;
});

// Verify actual game unmount disposes an awaited real reel-landing scope without deadlocking.
test('SLOT-037 actual landing-pending unmount terminalizes one action with no stale DOM', async () => {
  // Capture real completion outcomes from the mounted game.
  const completions = [];
  // Install the bounded observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount a fresh real game root.
  const firstRoot = createFakeElement('slots-timer-root');
  // Enter the actual production mount lifecycle.
  await SlotsGame.mount(firstRoot);
  // Start one immediate-response real spin.
  const action = firstRoot.querySelector('#spin').onclick();
  // Wait until the landing owns more timers than the reel-sound cleanup alone.
  await waitFor(() => browser.clock.pending >= 2, 'actual Slots motion scope never received landing timers');
  // Capture the rendered in-progress root before teardown.
  const oldMarkup = firstRoot.innerHTML;
  // Invoke actual game unmount so scope.dispose and waiter release execute together.
  SlotsGame.unmount();
  // Advance every remaining non-scope cleanup callback.
  browser.clock.runAll();
  // Require the actual spin promise to terminate after disposal.
  await action;
  // Prove only one abort was emitted and the detached root received no late settlement render.
  assert.deepEqual(completions, [{ game: 'slots', outcome: 'aborted' }]); assert.equal(firstRoot.innerHTML, oldMarkup);
  // Mount and unmount once more to prove teardown did not poison a clean route generation.
  const secondRoot = createFakeElement('slots-timer-remount');
  // Use the actual remount path rather than a synthetic completion helper.
  await SlotsGame.mount(secondRoot); SlotsGame.unmount(); browser.clock.runAll();
  // Remove the optional completion observer.
  delete window.__casinoPresentationProbe;
});

// Verify a delayed shared-wallet response cannot publish after actual teardown and remount.
test('SLOT-037 delayed wallet refresh cannot mutate a remounted shell', async () => {
  // Capture actual completion outcomes.
  const completions = [];
  // Install the bounded production observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount one real route and let its initial wallet refresh complete.
  const firstRoot = createFakeElement('slots-wallet-root');
  // Enter the actual mount lifecycle.
  await SlotsGame.mount(firstRoot);
  // Delay the next authenticated wallet response only.
  const walletGate = browser.delayWallet();
  // Record the current wallet request count.
  const walletCount = browser.walletRequests;
  // Start an immediate-response real spin.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Wait until the real landing owns timers, then advance all reel stops and the hold.
  await waitFor(() => browser.clock.pending >= 2, 'Slots did not reach its real landing wait');
  // Drive every governed reel phase until the old action is blocked inside its side-effect-free wallet fetch.
  await advanceClockUntil(() => browser.walletRequests === walletCount + 1, 'Slots did not reach the delayed wallet fetch');
  // Tear down the old route while that second await is pending.
  SlotsGame.unmount(); browser.clock.runAll();
  // Mount a distinct root whose immediate wallet refresh now owns shell state.
  const secondRoot = createFakeElement('slots-wallet-remount');
  // Complete the actual remount before the stale wallet returns.
  await SlotsGame.mount(secondRoot);
  // Snapshot every shared side effect the stale response must preserve.
  const currentUserBefore = window.CasinoCurrentUser; const eventsBefore = browser.dispatched.length; const balanceBefore = browser.documentNodes.get('balance')?.textContent; const remountedMarkup = secondRoot.innerHTML;
  // Release a conspicuously stale wallet payload.
  walletGate.resolve({ user: { user_id: 'stale-user' }, player: { player_id: 'human', token_balance: 999999 } });
  // Require the old action to finish through its stale-ownership guard.
  await oldAction;
  // Prove stale data did not enter session state, events, visible wallet, or the remounted route.
  assert.equal(window.CasinoCurrentUser, currentUserBefore); assert.equal(browser.dispatched.length, eventsBefore); assert.equal(browser.documentNodes.get('balance')?.textContent, balanceBefore); assert.equal(secondRoot.innerHTML, remountedMarkup);
  // Prove the disposed action emitted one abort and no settlement.
  assert.deepEqual(completions, [{ game: 'slots', outcome: 'aborted' }]);
  // Clean up through the actual game boundary.
  SlotsGame.unmount(); browser.clock.runAll(); delete window.__casinoPresentationProbe;
});

// Verify SLOT-037 a POST-pending action aborts once and cannot target a later remount.
test('SLOT-037 API-pending disposal blocks stale state, DOM, wallet, sound, voice, and duplicate continuation', async () => {
  // Model the immutable route generation captured by one in-flight spin.
  let generation = 1;
  // Retain terminal notifications so duplicate settle-versus-abort completion is observable.
  const completions = [];
  // Count every side effect that an abandoned continuation must skip.
  const effects = { state: 0, dom: 0, wallet: 0, sound: 0, voice: 0 };
  // Create one externally controlled backend response.
  const api = deferred();
  // Bind the production completion guard to the first route generation.
  const action = createSlotsSpinCompletion({ isCurrent: () => generation === 1, onComplete: outcome => completions.push(outcome) });
  // Start a production-shaped continuation that checks ownership immediately after the API await.
  const flow = (async () => {
    // Wait for the authoritative response exactly where route teardown can occur.
    await api.promise;
    // Return the terminal outcome before any old action can touch a remounted route.
    if (!action.isCurrent()) return action.outcome;
    // Model state adoption, DOM render, wallet refresh, sound, and voice.
    effects.state += 1; effects.dom += 1; effects.wallet += 1; effects.sound += 1; effects.voice += 1;
    // Settle only a still-current action.
    action.settle();
    // Return the one terminal result for deterministic assertion.
    return action.outcome;
  })();
  // Dispose the old route and create a distinct remount generation.
  generation = 2;
  // Abort the abandoned action exactly once.
  assert.equal(action.abort(), true);
  // Reject repeated abort and cross-terminal settlement.
  assert.equal(action.abort(), false); assert.equal(action.settle(), false);
  // Release the late backend response after the remount already exists.
  api.resolve({ round_id: 'stale-round' });
  // Require prompt aborted completion rather than a pending async leak.
  assert.equal(await flow, 'aborted');
  // Prove no stale state, DOM, wallet, sound, or voice side effect ran.
  assert.deepEqual(effects, { state: 0, dom: 0, wallet: 0, sound: 0, voice: 0 });
  // Prove only one terminal notification escaped.
  assert.deepEqual(completions, ['aborted']);
  // Bind a fresh action to the new route generation.
  const remountCompletions = [];
  // Create the production guard used by the clean remount.
  const remount = createSlotsSpinCompletion({ isCurrent: () => generation === 2, onComplete: outcome => remountCompletions.push(outcome) });
  // Require the new route to settle normally and independently.
  assert.equal(remount.isCurrent(), true); assert.equal(remount.settle(), true); assert.equal(remount.abort(), false);
  // Prove the fresh route has one clean completion.
  assert.deepEqual(remountCompletions, ['settled']);
});

// Verify SLOT-037 a canceled reel landing releases its await without allowing stale continuation.
test('SLOT-037 landing-pending disposal resolves once and skips stale continuation', async () => {
  // Keep the old route current until its fake landing timer is registered.
  let current = true;
  // Capture the fake-clock callback without advancing it.
  let fireTimer = null;
  // Count terminal completion and every forbidden post-wait effect.
  const completions = []; const effects = { dom: 0, wallet: 0, sound: 0, voice: 0 };
  // Bind one production completion guard to the current route.
  const action = createSlotsSpinCompletion({ isCurrent: () => current, onComplete: outcome => completions.push(outcome) });
  // Create the exact cancel-releasable wait used by Slots holds and reel landings.
  const wait = createSlotsMotionWait(resolve => { fireTimer = resolve; });
  // Start the continuation at its landing-await boundary.
  const flow = (async () => {
    // Wait on the fake-clock-owned reel landing.
    await wait.promise;
    // Reject teardown-released continuation before DOM, wallet, sound, or voice.
    if (!action.isCurrent()) return action.outcome;
    // Model the post-landing effects that only a current action owns.
    effects.dom += 1; effects.wallet += 1; effects.sound += 1; effects.voice += 1;
    // Complete the visible result exactly once.
    action.settle();
    // Return the terminal result for deterministic assertion.
    return action.outcome;
  })();
  // Dispose the route while the reel landing is still pending.
  current = false;
  // Abort the active action before releasing the canceled landing wait.
  assert.equal(action.abort(), true);
  // Release the awaiting promise exactly once through the production cancellation seam.
  assert.equal(wait.cancel(), true); assert.equal(wait.cancel(), false);
  // Simulate a late fake-clock callback and prove it cannot complete twice.
  assert.equal(fireTimer(), false);
  // Require terminal aborted completion rather than a deadlocked promise.
  assert.equal(await flow, 'aborted');
  // Prove no post-wait presentation effect ran.
  assert.deepEqual(effects, { dom: 0, wallet: 0, sound: 0, voice: 0 });
  // Prove only one abort was observed.
  assert.deepEqual(completions, ['aborted']);
});
