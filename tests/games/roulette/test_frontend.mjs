// Verify the PR-526 honest-landing presentation math and cleanup guards for the premium Roulette wheel.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import source reads from the standard library for boundary assertions.
import { readFile } from 'node:fs/promises';
// Import the dependency-free Node test runner.
import test from 'node:test';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';
// Import the seeded generator the game uses for decorative landing scatter.
import { createSeededRandom } from '../../../web/core/dice.js';
// Import the real route-owned timer scope so teardown tests exercise production disposal.
import { createMotionTimerScope } from '../../../web/core/motion.js';

// Create one externally controlled promise for API and wallet cancellation tests.
function deferred() {
  // Retain the resolver outside promise construction.
  let resolve = null;
  // Retain the rejecter so hostile late failures can exercise the actual guarded route.
  let reject = null;
  // Create the promise whose completion is owned by the test.
  const promise = new Promise((done, fail) => { resolve = done; reject = fail; });
  // Return the paired promise controls without exposing mutable wrapper state.
  return Object.freeze({ promise, resolve, reject });
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
  // Build one style object with the property setter used by Roulette wrappers.
  const style = { setProperty(name, value) { this[name] = value; } };
  // Build the minimal browser element surface exercised by real mount, render, spin, and unmount.
  const element = {
    selector,
    dataset: {},
    style,
    classList: { add: (...names) => names.forEach(name => classes.add(name)), remove: (...names) => names.forEach(name => classes.delete(name)), contains: name => classes.has(name), toggle: (name, force) => { if (force === false) classes.delete(name); else classes.add(name); } },
    value: selector.includes('#mode') ? 'single' : selector.includes('#zero') ? 'normal' : selector.includes('.rounds') ? '1' : selector.includes('.speed') ? 'medium' : '',
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
    getBoundingClientRect() { return { left: 0, top: selector.includes('slot-cell-1-') ? 100 : 0, right: 100, bottom: 100, width: 100, height: 100 }; },
  };
  // Return the stable fake element.
  return element;
}

// Install a deterministic browser seam used by actual RouletteGame mount and unmount calls.
function installFakeBrowser() {
  // Create one clock before mount so the real scope captures these exact timer functions.
  const clock = createFakeClock();
  // Track document-owned nodes used by style and wallet publication.
  const documentNodes = new Map();
  // Track dispatched shell events so stale wallet publication is observable.
  const dispatched = [];
  // Retain one optional delayed Roulette spin response.
  let delayedSpin = null;
  // Retain one optional delayed authenticated-wallet response.
  let delayedWallet = null;
  // Retain one optional delayed final bot-panel response.
  let delayedBot = null;
  // Count authoritative spin requests independently from render activity.
  let spinRequests = 0;
  // Count authenticated wallet reads so the second awaited boundary can be located.
  let walletRequests = 0;
  // Count bot-panel reads independently from bot action execution.
  let botRequests = 0;
  // Count client telemetry posts so stale rejected work is observable.
  let logRequests = 0;
  // Count unmount clear requests so a stale committed spin cannot create a duplicate refund.
  let clearRequests = 0;
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
  globalThis.location = { search: '', href: 'https://casino.test/games/roulette', origin: 'https://casino.test', pathname: '/games/roulette' };
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
  // Build the state envelope consumed by each actual Roulette mount.
  const rouletteState = roundId => ({ state: { mode: 'single', zero_rule: 'normal', open_round: { bets: [] }, last_bet_template: [], last_results: [] }, catalog: [], players: [], stats: { roll_count: 0, colors: {}, frequency: {}, hot: [], cold: [], latest: [] }, round: { round_id: roundId, result: '17', result_color: 'black' }, settlements: [] });
  // Route every fetch through exact public paths used by the game and shared modules.
  globalThis.fetch = async input => {
    // Normalize the requested URL without retaining options or credentials.
    const url = String(input);
    // Return a deterministic locale manifest and empty dictionaries.
    if (url.startsWith('/i18n/')) return response(url.endsWith('manifest.json') ? { schemaVersion: 1, defaultLocale: 'en-US', fallbackLocale: 'en-US', aliases: {}, locales: [], domains: ['common'] } : {});
    // Return the actual mounted Roulette state.
    if (url.startsWith('/api/v1/games/roulette/state')) return response(rouletteState('state-round'));
    // Control bot-panel capability reads independently from bot action execution.
    if (url.includes('/eligible-bots')) { botRequests += 1; const gate = delayedBot; delayedBot = null; return response(gate ? await gate.promise : { bots: [], capabilities: { supports_bots: false, strategies: [] } }); }
    // Keep the bot action on the same immediate public seam.
    if (url.includes('/bots/play-round')) return response({ actions: [] });
    // Control the exact Roulette action response for API-pending teardown proof.
    if (url === '/api/v1/games/roulette/spin') { spinRequests += 1; const gate = delayedSpin; delayedSpin = null; return response(gate ? await gate.promise : rouletteState(`spin-${spinRequests}`)); }
    // Return a harmless clear acknowledgement if a regression attempts an unmount refund.
    if (url === '/api/v1/games/roulette/clear') { clearRequests += 1; return response({}); }
    // Control the shared wallet's second await independently from the game response.
    if (url === '/api/v2/me') { walletRequests += 1; const gate = delayedWallet; delayedWallet = null; return response(gate ? await gate.promise : { user: { user_id: 'user-1' }, player: { player_id: 'human', token_balance: 1000 + walletRequests } }); }
    // Return a legacy wallet shape for completeness when current-user state is deliberately absent.
    if (url.startsWith('/api/v1/players/')) return response({ player: { player_id: 'human', balance: 1000 } });
    // Accept bounded client telemetry while counting any stale error report.
    if (url === '/api/v1/log/client') { logRequests += 1; return response({}); }
    // Fail loudly when real game code reaches a route the focused harness did not review.
    throw new Error(`unexpected Roulette test request: ${url}`);
  };
  // Return controller hooks without exposing mutable internals to the game.
  return { clock, dispatched, documentNodes, delaySpin() { delayedSpin = deferred(); return delayedSpin; }, delayWallet() { delayedWallet = deferred(); return delayedWallet; }, delayBot() { delayedBot = deferred(); return delayedBot; }, get spinRequests() { return spinRequests; }, get walletRequests() { return walletRequests; }, get botRequests() { return botRequests; }, get logRequests() { return logRequests; }, get clearRequests() { return clearRequests; } };
}

// Install the browser seam before shared frontend modules read global state.
const browser = installFakeBrowser();
// Import the tested game exports only after installing the minimal browser global.
const { RouletteGame, computeLandingPlan, pocketBaseAngle, norm360, createRouletteSpinCompletion, createRouletteMotionWait, SPIN_REVEAL_MS, AUTOPLAY_REVEAL_MS, REDUCED_REVEAL_MS, MIN_LANDING_MS, WHEEL_EXTRA_TURNS, BALL_EXTRA_TURNS } = await import('../../../web/games/roulette.js');
// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text for guard-wiring assertions.
const source = await readFile(path.join(root, 'web', 'games', 'roulette.js'), 'utf8');

// Compare two angles for congruence modulo one full turn within a small numeric tolerance.
function congruent(a, b) {
  // Fold the difference into [0, 360) and accept either boundary of the fold.
  const difference = norm360(a - b);
  // Return true when the angles describe the same visual orientation.
  return difference < 1e-6 || 360 - difference < 1e-6;
}

// Wait until one asynchronous production boundary becomes observable without using a timer.
async function waitFor(predicate, message) {
  // Give chained promises a bounded number of microtask turns to reach the expected boundary.
  for (let attempt = 0; attempt < 100; attempt += 1) { if (predicate()) return; await Promise.resolve(); }
  // Fail with one stable diagnostic when production code never reached the boundary.
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
  assert.equal(settled, true, 'actual Roulette action must terminate under the fake clock');
  // Return the original resolved value for callers that need it.
  return promise;
}

// Verify ROU-053 the landing plan parks the ball exactly over the committed pocket on both wheels.
test('ROU-053 landing plan is pocket-congruent for every pocket on both wheel modes', () => {
  // Exercise the European 37-pocket and American 38-pocket wheels.
  for (const pocketCount of [37, 38]) {
    // Exercise every pocket index including the zero and double-zero edges.
    for (let pocketIndex = 0; pocketIndex < pocketCount; pocketIndex += 1) {
      const plan = computeLandingPlan({ wheelAngle: 121.29, ballAngle: 324.97, pocketIndex, pocketCount, random: createSeededRandom(`rou-${pocketCount}-${pocketIndex}`), revealMs: SPIN_REVEAL_MS, elapsedMs: 300 }); // Compute one deterministic plan.
      assert.ok(plan, `plan must exist for pocket ${pocketIndex}/${pocketCount}`); // Require a plan for every legal pocket.
      assert.ok(congruent(plan.ballTarget, pocketBaseAngle(pocketIndex, pocketCount) + plan.wheelTarget), `ball must rest over pocket ${pocketIndex}/${pocketCount}`); // Prove the ball ends over the winning pocket at the new rest orientation.
    }
  }
});

// Verify ROU-051 the plan refuses an off-wheel pocket instead of inventing a landing.
test('ROU-051 landing plan rejects pockets that are not on the rendered wheel', () => {
  // Reject a negative index such as a failed indexOf lookup.
  assert.equal(computeLandingPlan({ wheelAngle: 0, ballAngle: 0, pocketIndex: -1, pocketCount: 37, random: createSeededRandom('rou-reject'), revealMs: SPIN_REVEAL_MS, elapsedMs: 0 }), null);
  // Reject an index beyond the wheel such as a double-zero lookup on a single-zero wheel.
  assert.equal(computeLandingPlan({ wheelAngle: 0, ballAngle: 0, pocketIndex: 37, pocketCount: 37, random: createSeededRandom('rou-reject'), revealMs: SPIN_REVEAL_MS, elapsedMs: 0 }), null);
  // Reject a fractional index so type drift can never mis-target a pocket.
  assert.equal(computeLandingPlan({ wheelAngle: 0, ballAngle: 0, pocketIndex: 1.5, pocketCount: 37, random: createSeededRandom('rou-reject'), revealMs: SPIN_REVEAL_MS, elapsedMs: 0 }), null);
});

// Verify ROU-070 the wrappers travel whole extra circuits in opposite directions without teleporting.
test('ROU-070 wrapper travel adds bounded whole-turn circuits in opposite directions', () => {
  const plan = computeLandingPlan({ wheelAngle: 45, ballAngle: 200, pocketIndex: 17, pocketCount: 38, random: createSeededRandom('rou-turns'), revealMs: SPIN_REVEAL_MS, elapsedMs: 250 }); // Compute one representative plan.
  const wheelTravel = plan.wheelTarget - 45; // Measure the rotor wrapper's clockwise travel.
  assert.ok(wheelTravel >= WHEEL_EXTRA_TURNS * 360 && wheelTravel < (WHEEL_EXTRA_TURNS + 1) * 360, 'rotor travels its extra turns plus bounded scatter'); // Prove the rotor always advances forward through its governed extra turns.
  const ballTravel = 200 - plan.ballTarget; // Measure the ball wrapper's counter-clockwise travel.
  assert.ok(ballTravel >= BALL_EXTRA_TURNS * 360 && ballTravel < (BALL_EXTRA_TURNS + 1) * 360, 'ball counter-travels its extra circuits plus pocket alignment'); // Prove the ball always counter-rotates through its governed circuits.
});

// Verify ROU-054 the travel budget absorbs backend latency without ever teleporting the landing.
test('ROU-054 travel budget floors at the minimum landing time under slow round-trips', () => {
  const fast = computeLandingPlan({ wheelAngle: 0, ballAngle: 0, pocketIndex: 5, pocketCount: 37, random: createSeededRandom('rou-fast'), revealMs: SPIN_REVEAL_MS, elapsedMs: 200 }); // Compute a plan with a fast backend.
  assert.equal(fast.travelMs, SPIN_REVEAL_MS - 200); // Prove a fast round-trip uses the remaining reveal budget exactly.
  const slow = computeLandingPlan({ wheelAngle: 0, ballAngle: 0, pocketIndex: 5, pocketCount: 37, random: createSeededRandom('rou-slow'), revealMs: SPIN_REVEAL_MS, elapsedMs: 3500 }); // Compute a plan with a slow backend.
  assert.equal(slow.travelMs, MIN_LANDING_MS); // Prove the landing keeps its minimum travel instead of snapping.
});

// Verify DICE-001 one committed round id always replays the identical decorative trajectory.
test('DICE-001 seeded landing scatter is deterministic per round identity', () => {
  const first = computeLandingPlan({ wheelAngle: 10, ballAngle: 20, pocketIndex: 9, pocketCount: 37, random: createSeededRandom('rou_round_777'), revealMs: SPIN_REVEAL_MS, elapsedMs: 100 }); // Compute the plan once.
  const second = computeLandingPlan({ wheelAngle: 10, ballAngle: 20, pocketIndex: 9, pocketCount: 37, random: createSeededRandom('rou_round_777'), revealMs: SPIN_REVEAL_MS, elapsedMs: 100 }); // Recompute from the same round identity.
  assert.deepEqual(first, second); // Prove the same round identity never lands differently.
  assert.equal(Object.isFrozen(first), true); // Prevent callers from mutating an accepted trajectory.
});

// Verify MOTION-005 the reduced-motion reveal stays inside the governed 400-800 ms comfort band.
test('MOTION-005 reveal budgets keep their governed ordering and comfort band', () => {
  assert.ok(REDUCED_REVEAL_MS >= 400 && REDUCED_REVEAL_MS <= 800); // Prove the comfort reveal honors the governed band.
  assert.ok(AUTOPLAY_REVEAL_MS < REDUCED_REVEAL_MS && REDUCED_REVEAL_MS < SPIN_REVEAL_MS); // Prove the three reveal modes stay strictly ordered.
});

// Verify MOTION-002 every landing timer runs through the guarded route-owned scope.
test('MOTION-002 landing timers are guarded against a disposed route scope', () => {
  assert.match(source, /if \(motionScope && !motionScope\.disposed\) \{\s*\n\s*\/\/[^\n]*\n\s*motionScope\.schedule\(/, 'descent scheduling must check the disposed scope'); // Pin the bfcache-safe descent guard.
  assert.match(source, /if \(!motionScope \|\| motionScope\.disposed\) return Promise\.resolve\(\);/, 'waitMotion must degrade on a disposed scope'); // Pin the reveal-wait guard.
  assert.match(source, /if \(motionScope\) motionScope\.dispose\(\);/, 'unmount must dispose the route scope'); // Pin route-teardown timer cleanup.
  assert.match(source, /releaseMotionWaiters\(\);/, 'unmount must release promises whose scoped timers were cancelled'); // Pin deadlock-free waiter cleanup.
  assert.match(source, /if \(activeSpinCompletion\) activeSpinCompletion\.abort\(\);/, 'unmount must terminalize the active presentation once'); // Pin exactly-once abort wiring.
  assert.doesNotMatch(source, /setTimeout\(\(\) => clickSound\(760/, 'follow-up result sound must not escape the route-owned scope'); // Reject the old raw sound timer.
});

// Verify ROU-059 the unmount refund guard still suppresses the mid-spin clear race.
test('ROU-059 unmount refund keeps its committed-spin suppression', () => {
  assert.match(source, /const wasSpinning = spinBusy;/, 'unmount must capture the live spin state before releasing it'); // Pin the pre-reset capture.
  assert.match(source, /if \(humanBets\(\)\.length && !wasSpinning\) \{/, 'the refund must consult the captured spin state'); // Pin the live guard so the issue-246 race cannot return.
});

// Verify the production timer primitive cancels real scheduled callbacks on disposal.
test('ROU-072 real createMotionTimerScope disposal cancels its callback exactly once', () => {
  // Create a dedicated deterministic clock independent from the mounted game scope.
  const clock = createFakeClock();
  // Instantiate the real shared motion timer scope with that clock.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null });
  // Count any callback that incorrectly survives disposal.
  let callbacks = 0;
  // Schedule one real scope-owned callback.
  scope.schedule(() => { callbacks += 1; }, 3600, { reducedMotion: false });
  // Dispose the real scope and require exactly one pending timer to be cancelled.
  assert.equal(scope.dispose(), 1);
  // Repeated disposal must remain a no-op.
  assert.equal(scope.dispose(), 0);
  // Advancing the fake clock cannot revive the cancelled callback.
  clock.runAll(); assert.equal(callbacks, 0); assert.equal(scope.disposed, true);
});

// Verify an actual RouletteGame API-pending unmount aborts once and a real remount settles cleanly.
test('ROU-072 actual game API-pending unmount and remount prevent stale continuation', async () => {
  // Capture the bounded completion probe emitted by the real spin path.
  const completions = [];
  // Install the optional production probe without changing game behavior.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Create the first actual route root.
  const firstRoot = createFakeElement('roulette-root-one');
  // Mount the exported game object through its production lifecycle.
  await RouletteGame.mount(firstRoot);
  // Delay only the authoritative spin response.
  const spinGate = browser.delaySpin();
  // Record the request count before the controlled action starts.
  const spinCount = browser.spinRequests;
  // Start the real click-wired action.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Wait until the real public POST is pending.
  await waitFor(() => browser.spinRequests === spinCount + 1, 'actual Roulette spin did not reach its POST');
  // Record refund attempts before actual teardown.
  const clearsBefore = browser.clearRequests;
  // Unmount the exported game object while its POST is pending.
  RouletteGame.unmount();
  // Mount a distinct actual route before the stale POST returns.
  const secondRoot = createFakeElement('roulette-root-two');
  // Re-enter the production mount lifecycle on the new root.
  await RouletteGame.mount(secondRoot);
  // Snapshot the remounted DOM before releasing the stale response.
  const remountedMarkup = secondRoot.innerHTML;
  // Release the old backend response after a new route owns the game.
  spinGate.resolve(undefined);
  // Require the old click promise to terminate instead of hanging or resuming.
  await oldAction;
  // Prove the abandoned action emitted one abort and no settlement.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'aborted' }]);
  // Prove the stale continuation neither repainted the remount nor requested a refund.
  assert.equal(secondRoot.innerHTML, remountedMarkup); assert.equal(browser.clearRequests, clearsBefore);
  // Start a fresh action through the remounted production control.
  const freshAction = secondRoot.querySelector('#spin').onclick();
  // Drive the real route-owned scope to completion.
  await settleWithClock(freshAction);
  // Prove the remounted action independently settled exactly once.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'aborted' }, { game: 'roulette', outcome: 'settled' }]);
  // Tear down the remounted route through the actual game boundary.
  RouletteGame.unmount(); browser.clock.runAll();
  // Remove the optional probe so later tests start isolated.
  delete window.__casinoPresentationProbe;
});

// Verify a rejected POST that returns after teardown cannot reach the generic toast or telemetry wrapper.
test('ROU-072 late rejected POST after remount suppresses stale feedback and telemetry', async () => {
  // Capture terminal outcomes emitted by the actual mounted spin.
  const completions = [];
  // Install the bounded production completion observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount the first actual route generation.
  const firstRoot = createFakeElement('roulette-rejected-post-root');
  // Enter the real game lifecycle before delaying its public action.
  await RouletteGame.mount(firstRoot);
  // Delay the authoritative spin request so teardown can win ownership.
  const spinGate = browser.delaySpin();
  // Record the exact request and telemetry baselines.
  const spinCount = browser.spinRequests; const logsBefore = browser.logRequests;
  // Start the real click-wired action through its generic guarded wrapper.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Wait until the public POST is the only blocked boundary.
  await waitFor(() => browser.spinRequests === spinCount + 1, 'actual Roulette rejected spin did not reach its POST');
  // Dispose the captured generation before the backend rejection exists.
  RouletteGame.unmount();
  // Mount a distinct actual route and retain its rendered identity.
  const secondRoot = createFakeElement('roulette-rejected-post-remount');
  // Complete the new route lifecycle before releasing the old rejection.
  await RouletteGame.mount(secondRoot);
  // Snapshot the remounted game and untouched toast outlet.
  const remountedMarkup = secondRoot.innerHTML; const toastBefore = browser.documentNodes.get('toast');
  // Reject with secret-like text that must never reach stale player or telemetry side effects.
  spinGate.reject(Object.assign(new Error('stale-secret-path'), { code: 'STALE_SECRET' }));
  // Require the real guarded click promise to terminate without rejecting or hanging.
  await oldAction;
  // Let any incorrectly fire-and-forget telemetry attempt reach the fake fetch seam.
  await Promise.resolve();
  // Prove no old route markup, toast creation, or client log reached the remounted generation.
  assert.equal(secondRoot.innerHTML, remountedMarkup); assert.equal(browser.documentNodes.get('toast'), toastBefore); assert.equal(browser.logRequests, logsBefore);
  // Prove teardown emitted one abort and no late settlement.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'aborted' }]);
  // Clean up through the actual route boundary.
  RouletteGame.unmount(); browser.clock.runAll(); delete window.__casinoPresentationProbe;
});

// Verify the same rejected POST remains visible and observable when its original route still owns the action.
test('ROU-072 live rejected POST preserves localized feedback and telemetry', async () => {
  // Mount one actual route that will remain current through rejection handling.
  const currentRoot = createFakeElement('roulette-live-rejection-root');
  // Enter the production lifecycle before controlling the public response.
  await RouletteGame.mount(currentRoot);
  // Delay the next spin while retaining this route generation.
  const spinGate = browser.delaySpin();
  // Record request and telemetry baselines.
  const spinCount = browser.spinRequests; const logsBefore = browser.logRequests;
  // Start the actual guarded click action.
  const action = currentRoot.querySelector('#spin').onclick();
  // Wait until the public POST is pending.
  await waitFor(() => browser.spinRequests === spinCount + 1, 'actual Roulette live rejection did not reach its POST');
  // Reject with text that the player-facing toast must not expose.
  spinGate.reject(Object.assign(new Error('live-secret-path'), { code: 'LIVE_FAILURE' }));
  // Require the guarded action to convert the live rejection into bounded feedback.
  await action;
  // Wait for the intentionally fire-and-forget telemetry request to reach the fake seam.
  await waitFor(() => browser.logRequests === logsBefore + 1, 'live Roulette failure did not emit its bounded telemetry');
  // Read the shared toast created by the live-route error boundary.
  const toastNode = browser.documentNodes.get('toast');
  // Prove the live route still receives sanitized localized feedback without exception text.
  assert.ok(toastNode?.textContent); assert.doesNotMatch(toastNode.textContent, /live-secret-path/);
  // Clean up the still-current route and any toast timer.
  RouletteGame.unmount(); browser.clock.runAll();
});

// Verify actual game unmount disposes an awaited real motion scope without deadlocking.
test('ROU-072 actual timer-pending unmount terminalizes one action with no stale DOM', async () => {
  // Capture real completion outcomes from the mounted game.
  const completions = [];
  // Install the bounded observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount a fresh real game root.
  const firstRoot = createFakeElement('roulette-timer-root');
  // Enter the actual production mount lifecycle.
  await RouletteGame.mount(firstRoot);
  // Start one immediate-response real spin.
  const action = firstRoot.querySelector('#spin').onclick();
  // Wait until the landing and reveal timers are owned by the actual motion scope.
  await waitFor(() => browser.clock.pending >= 1, 'actual Roulette motion scope never received a reveal timer');
  // Capture the rendered in-progress root before teardown.
  const oldMarkup = firstRoot.innerHTML;
  // Invoke actual game unmount so scope.dispose and waiter release execute together.
  RouletteGame.unmount();
  // Advance every remaining non-scope cleanup callback.
  browser.clock.runAll();
  // Require the actual spin promise to terminate after disposal.
  await action;
  // Prove only one abort was emitted and the detached root received no late settlement render.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'aborted' }]); assert.equal(firstRoot.innerHTML, oldMarkup);
  // Mount and unmount once more to prove teardown did not poison a clean route generation.
  const secondRoot = createFakeElement('roulette-timer-remount');
  // Use the actual remount path rather than a synthetic completion helper.
  await RouletteGame.mount(secondRoot); RouletteGame.unmount(); browser.clock.runAll();
  // Remove the optional completion observer.
  delete window.__casinoPresentationProbe;
});

// Verify final bot markup cannot cross from a completed old action into a remounted route.
test('ROU-072 delayed final bot refresh cannot repaint a remounted route', async () => {
  // Capture the exact terminal outcome from the real spin.
  const completions = [];
  // Install the bounded production completion observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount one actual Roulette route with an immediate initial bot panel.
  const firstRoot = createFakeElement('roulette-bot-root');
  // Enter the production mount lifecycle.
  await RouletteGame.mount(firstRoot);
  // Delay only the next eligible-bot read, which belongs to final spin cleanup.
  const botGate = browser.delayBot();
  // Record the bot-read count before the action starts.
  const botCount = browser.botRequests;
  // Start an immediate-response public spin.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Wait for the production landing timer and advance it to final cleanup.
  await waitFor(() => browser.clock.pending >= 1, 'Roulette did not reach its bot-refresh landing wait'); browser.clock.runAll();
  // Wait until the old action is blocked on the delayed final bot-panel read.
  await waitFor(() => browser.botRequests === botCount + 1, 'Roulette did not reach its delayed final bot refresh');
  // Dispose the old route while its already-settled action still awaits bot markup.
  RouletteGame.unmount(); browser.clock.runAll();
  // Mount a new generation whose immediate bot response owns its panel.
  const secondRoot = createFakeElement('roulette-bot-remount');
  // Complete the actual remount before old markup returns.
  await RouletteGame.mount(secondRoot);
  // Snapshot both the new route and its currently owned bot panel.
  const remountedMarkup = secondRoot.innerHTML; const remountedBotMarkup = secondRoot.querySelector('#botPanel').innerHTML;
  // Return a distinctive stale bot row from the old action.
  botGate.resolve({ bots: [{ bot_id: 'stale-bot', display_name: 'STALE BOT', strategy_id: 'stale-strategy', stake: 1, balance: 1 }], capabilities: { supports_bots: true, strategies: ['stale-strategy'] } });
  // Require the old click promise to finish after the ownership-aware bot refresh declines publication.
  await oldAction;
  // Prove neither the new route nor its captured panel accepted stale markup.
  assert.equal(secondRoot.innerHTML, remountedMarkup); assert.equal(secondRoot.querySelector('#botPanel').innerHTML, remountedBotMarkup); assert.doesNotMatch(secondRoot.querySelector('#botPanel').innerHTML, /STALE BOT/);
  // Prove the action had already settled exactly once before its delayed cleanup was abandoned.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'settled' }]);
  // Clean up the remounted route and observer.
  RouletteGame.unmount(); browser.clock.runAll(); delete window.__casinoPresentationProbe;
});

// Verify a delayed final bot failure cannot escape stale cleanup into player feedback or telemetry.
test('ROU-072 rejected final bot refresh after remount has no stale side effect', async () => {
  // Capture the exact terminal outcome from the real spin.
  const completions = [];
  // Install the bounded production completion observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount one actual route with an immediate initial bot panel.
  const firstRoot = createFakeElement('roulette-bot-rejection-root');
  // Enter the production mount lifecycle before delaying cleanup.
  await RouletteGame.mount(firstRoot);
  // Delay only the final bot-panel response.
  const botGate = browser.delayBot();
  // Record bot, telemetry, and toast baselines.
  const botCount = browser.botRequests; const logsBefore = browser.logRequests; const toastBefore = browser.documentNodes.get('toast');
  // Start one immediate-response public spin.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Advance the actual landing so the action reaches final bot cleanup.
  await waitFor(() => browser.clock.pending >= 1, 'Roulette did not reach its rejected bot-refresh landing wait'); browser.clock.runAll();
  // Wait until the old action is blocked on its final bot-panel read.
  await waitFor(() => browser.botRequests === botCount + 1, 'Roulette did not reach its rejected final bot refresh');
  // Dispose the old route while final cleanup still owns the pending read.
  RouletteGame.unmount(); browser.clock.runAll();
  // Mount a distinct route whose immediate bot response owns its presentation.
  const secondRoot = createFakeElement('roulette-bot-rejection-remount');
  // Complete the actual remount before the old cleanup fails.
  await RouletteGame.mount(secondRoot);
  // Snapshot the new route and its owned bot panel.
  const remountedMarkup = secondRoot.innerHTML; const remountedBotMarkup = secondRoot.querySelector('#botPanel').innerHTML;
  // Build a hostile response whose first bot-markup read rejects outside the network fallback.
  const rejectedBotData = new Proxy({}, { get(target, property) { if (property === 'capabilities') throw new Error('stale-bot-secret'); return Reflect.get(target, property); } });
  // Release the old request into the real updateBotPanel rejection path.
  botGate.resolve(rejectedBotData);
  // Require stale final cleanup to terminate without reaching the generic wrapper.
  await oldAction; await Promise.resolve();
  // Prove the remounted route, bot panel, toast, and telemetry remain unchanged.
  assert.equal(secondRoot.innerHTML, remountedMarkup); assert.equal(secondRoot.querySelector('#botPanel').innerHTML, remountedBotMarkup); assert.equal(browser.documentNodes.get('toast'), toastBefore); assert.equal(browser.logRequests, logsBefore);
  // Prove the public action settled exactly once before its stale cleanup failure was suppressed.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'settled' }]);
  // Clean up the remounted route and observer.
  RouletteGame.unmount(); browser.clock.runAll(); delete window.__casinoPresentationProbe;
});

// Verify the same final bot failure retains ordinary feedback when the route still owns cleanup.
test('ROU-072 current final bot refresh failure preserves live feedback', async () => {
  // Capture one terminal result from the real spin.
  const completions = [];
  // Install the bounded production completion observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount the route that will remain current through final cleanup.
  const currentRoot = createFakeElement('roulette-current-bot-failure-root');
  // Enter the production lifecycle before delaying the bot response.
  await RouletteGame.mount(currentRoot);
  // Delay only this action's final bot-panel read.
  const botGate = browser.delayBot();
  // Record the bot and telemetry baselines.
  const botCount = browser.botRequests; const logsBefore = browser.logRequests;
  // Clear prior toast copy so current failure feedback is independently observable.
  const toastNode = browser.documentNodes.get('toast'); if (toastNode) toastNode.textContent = '';
  // Start one immediate-response public spin.
  const action = currentRoot.querySelector('#spin').onclick();
  // Advance the actual landing so current cleanup reaches the delayed bot read.
  await waitFor(() => browser.clock.pending >= 1, 'Roulette did not reach its live bot-refresh landing wait'); browser.clock.runAll();
  // Wait until final bot cleanup is pending on the current route.
  await waitFor(() => browser.botRequests === botCount + 1, 'Roulette did not reach its live final bot refresh');
  // Build a hostile response that rejects bot markup construction.
  const rejectedBotData = new Proxy({}, { get(target, property) { if (property === 'capabilities') throw new Error('live-bot-secret'); return Reflect.get(target, property); } });
  // Release the current request into updateBotPanel's rethrow path.
  botGate.resolve(rejectedBotData);
  // Require the outer guarded handler to convert the live error into bounded feedback.
  await action;
  // Wait for the intentionally fire-and-forget telemetry request.
  await waitFor(() => browser.logRequests === logsBefore + 1, 'live final bot failure did not emit telemetry');
  // Read the player-facing toast after the current-route failure.
  const currentToast = browser.documentNodes.get('toast');
  // Prove the live route received sanitized feedback while the completed game action stayed exactly once.
  assert.ok(currentToast?.textContent); assert.doesNotMatch(currentToast.textContent, /live-bot-secret/); assert.deepEqual(completions, [{ game: 'roulette', outcome: 'settled' }]);
  // Clean up the current route and observer.
  RouletteGame.unmount(); browser.clock.runAll(); delete window.__casinoPresentationProbe;
});

// Verify a delayed shared-wallet response cannot publish after actual teardown and remount.
test('ROU-072 delayed wallet refresh cannot mutate a remounted shell', async () => {
  // Capture actual completion outcomes.
  const completions = [];
  // Install the bounded production observer.
  window.__casinoPresentationProbe = event => completions.push(event);
  // Mount one real route and let its initial wallet refresh complete.
  const firstRoot = createFakeElement('roulette-wallet-root');
  // Enter the actual mount lifecycle.
  await RouletteGame.mount(firstRoot);
  // Delay the next authenticated wallet response only.
  const walletGate = browser.delayWallet();
  // Record the current wallet request count.
  const walletCount = browser.walletRequests;
  // Start an immediate-response real spin.
  const oldAction = firstRoot.querySelector('#spin').onclick();
  // Wait until real motion timers are scheduled, then advance the landing.
  await waitFor(() => browser.clock.pending >= 1, 'Roulette did not reach its real landing wait'); browser.clock.runAll();
  // Wait until the old action is blocked inside its side-effect-free wallet fetch.
  await waitFor(() => browser.walletRequests === walletCount + 1, 'Roulette did not reach the delayed wallet fetch');
  // Tear down the old route while that second await is pending.
  RouletteGame.unmount(); browser.clock.runAll();
  // Mount a distinct root whose immediate wallet refresh now owns shell state.
  const secondRoot = createFakeElement('roulette-wallet-remount');
  // Complete the actual remount before the stale wallet returns.
  await RouletteGame.mount(secondRoot);
  // Snapshot every shared side effect the stale response must preserve.
  const currentUserBefore = window.CasinoCurrentUser; const eventsBefore = browser.dispatched.length; const balanceBefore = browser.documentNodes.get('balance')?.textContent; const remountedMarkup = secondRoot.innerHTML;
  // Release a conspicuously stale wallet payload.
  walletGate.resolve({ user: { user_id: 'stale-user' }, player: { player_id: 'human', token_balance: 999999 } });
  // Require the old action to finish through its stale-ownership guard.
  await oldAction;
  // Prove stale data did not enter session state, events, visible wallet, or the remounted route.
  assert.equal(window.CasinoCurrentUser, currentUserBefore); assert.equal(browser.dispatched.length, eventsBefore); assert.equal(browser.documentNodes.get('balance')?.textContent, balanceBefore); assert.equal(secondRoot.innerHTML, remountedMarkup);
  // Prove the disposed action emitted one abort and no settlement.
  assert.deepEqual(completions, [{ game: 'roulette', outcome: 'aborted' }]);
  // Clean up through the actual game boundary.
  RouletteGame.unmount(); browser.clock.runAll(); delete window.__casinoPresentationProbe;
});

// Verify ROU-072 a POST-pending action aborts once and cannot target a later remount.
test('ROU-072 API-pending disposal blocks stale state, DOM, wallet, sound, bot, and refund continuation', async () => {
  // Model the immutable route generation captured by one in-flight spin.
  let generation = 1;
  // Retain terminal notifications so duplicate settle-versus-abort completion is observable.
  const completions = [];
  // Count every side effect that an abandoned continuation must skip.
  const effects = { state: 0, dom: 0, wallet: 0, sound: 0, bot: 0, refund: 0 };
  // Create one externally controlled backend response.
  const api = deferred();
  // Bind the production completion guard to the first route generation.
  const action = createRouletteSpinCompletion({ isCurrent: () => generation === 1, onComplete: outcome => completions.push(outcome) });
  // Start a production-shaped continuation that checks ownership immediately after the API await.
  const flow = (async () => {
    // Wait for the authoritative response exactly where route teardown can occur.
    await api.promise;
    // Return the terminal outcome before any old action can touch a remounted route.
    if (!action.isCurrent()) return action.outcome;
    // Model state adoption, DOM render, wallet refresh, sounds, bot repaint, and unmount refund.
    effects.state += 1; effects.dom += 1; effects.wallet += 1; effects.sound += 1; effects.bot += 1; effects.refund += 1;
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
  // Prove no stale presentation, wallet, sound, bot, or refund side effect ran.
  assert.deepEqual(effects, { state: 0, dom: 0, wallet: 0, sound: 0, bot: 0, refund: 0 });
  // Prove only one terminal notification escaped.
  assert.deepEqual(completions, ['aborted']);
  // Bind a fresh action to the new route generation.
  const remountCompletions = [];
  // Create the production guard used by the clean remount.
  const remount = createRouletteSpinCompletion({ isCurrent: () => generation === 2, onComplete: outcome => remountCompletions.push(outcome) });
  // Require the new route to settle normally and independently.
  assert.equal(remount.isCurrent(), true); assert.equal(remount.settle(), true); assert.equal(remount.abort(), false);
  // Prove the fresh route has one clean completion.
  assert.deepEqual(remountCompletions, ['settled']);
});

// Verify ROU-072 a canceled reveal timer releases its await without allowing stale continuation.
test('ROU-072 timer-pending disposal resolves once and skips stale continuation', async () => {
  // Keep the old route current until its fake timer is registered.
  let current = true;
  // Capture the fake-clock callback without advancing it.
  let fireTimer = null;
  // Count terminal completion and every forbidden post-wait effect.
  const completions = []; const effects = { dom: 0, wallet: 0, sound: 0 };
  // Bind one production completion guard to the current route.
  const action = createRouletteSpinCompletion({ isCurrent: () => current, onComplete: outcome => completions.push(outcome) });
  // Create the exact cancel-releasable wait used by Roulette.
  const wait = createRouletteMotionWait(resolve => { fireTimer = resolve; });
  // Start the continuation at its reveal-await boundary.
  const flow = (async () => {
    // Wait on the fake-clock-owned reveal.
    await wait.promise;
    // Reject teardown-released continuation before DOM, wallet, or sound.
    if (!action.isCurrent()) return action.outcome;
    // Model the post-reveal effects that only a current action owns.
    effects.dom += 1; effects.wallet += 1; effects.sound += 1;
    // Complete the visible result exactly once.
    action.settle();
    // Return the terminal result for deterministic assertion.
    return action.outcome;
  })();
  // Dispose the route while the reveal is still pending.
  current = false;
  // Abort the active action before releasing the canceled timer wait.
  assert.equal(action.abort(), true);
  // Release the awaiting promise exactly once through the production cancellation seam.
  assert.equal(wait.cancel(), true); assert.equal(wait.cancel(), false);
  // Simulate a late fake-clock callback and prove it cannot complete twice.
  assert.equal(fireTimer(), false);
  // Require terminal aborted completion rather than a deadlocked promise.
  assert.equal(await flow, 'aborted');
  // Prove no post-wait presentation effect ran.
  assert.deepEqual(effects, { dom: 0, wallet: 0, sound: 0 });
  // Prove only one abort was observed.
  assert.deepEqual(completions, ['aborted']);
});
