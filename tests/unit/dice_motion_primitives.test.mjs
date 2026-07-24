// Import strict assertions for deterministic primitive verification.
import assert from "node:assert/strict";
// Import the built-in dependency-free Node test runner.
import test from "node:test";
// Import the isolated dice primitives under test.
import { createSeededRandom, rollDie, rollDice } from "../../web/core/dice.js";
// Import the isolated motion primitives under test.
import { MOTION_PHASES, createMotionLifecycle, createMotionTimerScope, createMotionTimingProfile, prefersReducedMotion, resolveMotionDuration } from "../../web/core/motion.js";
// Import reusable fake clock, lifecycle, and reduced-motion test helpers.
import { createFakeClock, createLifecycleTarget, createMatchMedia } from "../helpers/motion_test_helpers.mjs";

// Verify DICE-001 seeded hooks reproduce the same valid dice sequence.
test("DICE-001 seeded dice rolls are deterministic and bounded", () => {
  const firstRandom = createSeededRandom("sic-bo-round-17"); // Create the first deterministic sequence.
  const secondRandom = createSeededRandom("sic-bo-round-17"); // Recreate the same deterministic sequence.
  const firstRolls = rollDice({ count: 12, sides: 6, random: firstRandom }); // Roll a representative dice-game sequence.
  const secondRolls = rollDice({ count: 12, sides: 6, random: secondRandom }); // Repeat from the same seed.
  assert.deepEqual(firstRolls, secondRolls); // Prove identical seeds reproduce every face.
  assert.ok(firstRolls.every((face) => face >= 1 && face <= 6)); // Prove every generated face respects die bounds.
});

// Verify DICE-001 supports exact injected samples and validates invalid generators.
test("DICE-001 roll helpers honor injected random samples", () => {
  const samples = [0, 0.49, 0.999999]; // Define samples spanning the accepted random interval.
  const random = () => samples.shift(); // Supply samples in deterministic order.
  assert.deepEqual(rollDice({ count: 3, sides: 6, random }), [1, 3, 6]); // Prove sample-to-face mapping is one-based and bounded.
  assert.equal(rollDie({ sides: 20, random: () => 0.5 }), 11); // Prove non-six-sided dice use the same mapping.
  assert.throws(() => rollDie({ random: () => 1 }), /\[0, 1\)/); // Reject an out-of-contract generator result.
});

// Verify MOTION-001 reads platform preferences and collapses reduced-motion delays.
test("MOTION-001 duration resolution respects reduced motion", () => {
  const reducedMatchMedia = createMatchMedia(true); // Simulate a reduced-motion browser preference.
  assert.equal(prefersReducedMotion(reducedMatchMedia), true); // Prove the standard media query is consulted.
  assert.equal(resolveMotionDuration(450, { matchMedia: reducedMatchMedia }), 0); // Collapse decorative motion to an asynchronous zero-delay task.
  assert.equal(resolveMotionDuration(450, { reducedMotion: false, matchMedia: reducedMatchMedia }), 450); // Let an explicit test or product override win.
});

// Verify MOTION-003 deterministic timer hooks execute only at the injected deadline.
test("MOTION-003 injected timing hooks control callback execution", () => {
  const clock = createFakeClock(); // Create a deterministic timer environment.
  const calls = []; // Record callback execution without real time.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: false }); // Build a detached deterministic scope.
  scope.schedule(() => calls.push("done"), 20); // Schedule one motion callback.
  clock.advance(19); // Stop immediately before its deadline.
  assert.deepEqual(calls, []); // Prove the callback has not fired early.
  assert.equal(scope.activeCount, 1); // Prove the scope still owns the pending callback.
  clock.advance(1); // Reach the exact injected deadline.
  assert.deepEqual(calls, ["done"]); // Prove deterministic execution at the deadline.
  assert.equal(scope.activeCount, 0); // Prove completed callbacks release their scope ownership.
});

// Verify MOTION-001 reduced motion still schedules asynchronously and remains cancellable.
test("MOTION-001 reduced motion uses a cancellable zero-delay timer", () => {
  const clock = createFakeClock(); // Create a deterministic timer environment.
  let called = false; // Track callback execution.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: true }); // Force reduced motion for the scope.
  scope.schedule(() => { called = true; }, 800); // Schedule a normally long animation step.
  assert.equal(called, false); // Preserve asynchronous callback semantics before the clock advances.
  clock.advance(0); // Run zero-delay fake timers.
  assert.equal(called, true); // Prove reduced motion removes the wait without running inline.
});

// Verify MOTION-002 explicit teardown cancels callbacks and releases listeners.
test("MOTION-002 dispose prevents stale callbacks after teardown", () => {
  const clock = createFakeClock(); // Create deterministic pending timers.
  const lifecycleTarget = createLifecycleTarget(); // Track browser lifecycle listener ownership.
  let called = false; // Detect any stale callback execution.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget }); // Bind the timer scope to lifecycle events.
  scope.schedule(() => { called = true; }, 50); // Schedule work that must not outlive the route.
  assert.equal(scope.dispose(), 1); // Prove teardown reports one cancelled callback.
  assert.equal(scope.disposed, true); // Prove the scope cannot accept new animation work.
  assert.equal(scope.activeCount, 0); // Prove no callback remains owned by the scope.
  assert.equal(lifecycleTarget.listenerCount(), 0); // Prove teardown releases lifecycle listeners.
  clock.advance(100); // Advance beyond the original callback deadline.
  assert.equal(called, false); // Prove the stale callback never runs.
  assert.throws(() => scope.schedule(() => {}, 1), /disposed/); // Prove disposed routes cannot schedule replacement timers.
});

// Verify MOTION-002 navigation and reload events automatically dispose timer scopes.
test("MOTION-002 route and reload lifecycle events cancel pending timers", () => {
  // Exercise both SPA history navigation and full-page reload teardown signals.
  for (const eventName of ["popstate", "pagehide"]) {
    const clock = createFakeClock(); // Isolate deterministic timers for this lifecycle event.
    const lifecycleTarget = createLifecycleTarget(); // Isolate listeners for this lifecycle event.
    let called = false; // Detect stale work after lifecycle exit.
    const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget }); // Bind automatic cleanup.
    scope.schedule(() => { called = true; }, 75); // Schedule work owned by the current route.
    lifecycleTarget.dispatch(eventName); // Simulate navigation or reload teardown.
    clock.advance(100); // Advance past the abandoned deadline.
    assert.equal(scope.disposed, true, `${eventName} should dispose the scope`); // Prove lifecycle exit permanently tears down the scope.
    assert.equal(called, false, `${eventName} should prevent stale callbacks`); // Prove no abandoned callback executes.
    assert.equal(clock.pendingCount(), 0, `${eventName} should clear platform timers`); // Prove the underlying timer was cancelled.
  }
});

// Verify MOTION-005 timing profiles preserve named budgets and live comfort preferences.
test("MOTION-005 named timing profiles resolve normal, fast, and reduced budgets", () => {
  const profile = createMotionTimingProfile({ normal: 1800, fast: 900, reduced: 120 }); // Freeze one representative game timing contract.
  assert.deepEqual({ normal: profile.normal, fast: profile.fast, reduced: profile.reduced }, { normal: 1800, fast: 900, reduced: 120 }); // Preserve reviewed budgets exactly.
  assert.equal(profile.resolve("normal", { reducedMotion: false }), 1800); // Resolve the normal presentation budget.
  assert.equal(profile.resolve("fast", { reducedMotion: false }), 900); // Resolve the explicit shortened presentation budget.
  assert.equal(profile.resolve("normal", { matchMedia: createMatchMedia(true) }), 120); // Honor the live reduced-motion preference.
  assert.throws(() => createMotionTimingProfile({ normal: 100, fast: 200 }), /must not exceed/); // Reject a mislabeled fast path.
  assert.throws(() => profile.resolve("turbo", { reducedMotion: false }), /unknown motion timing mode/); // Reject unreviewed timing modes.
});

// Verify MOTION-004 publishes the complete explicit lifecycle and preserves server-result identity.
test("MOTION-004 lifecycle binds one authoritative result through settlement", () => {
  const transitions = []; // Record immutable transition snapshots in order.
  const lifecycle = createMotionLifecycle({ onTransition: (state) => transitions.push(state) }); // Create one observed presentation lifecycle.
  const result = Object.freeze({ round_id: "round-17", pocket: "00" }); // Model an already-authoritative immutable server result.
  const token = lifecycle.begin(); // Lock one action and obtain its opaque owner identity.
  assert.equal(lifecycle.run(token), true); // Enter visible motion for the owned action.
  assert.equal(lifecycle.commit(token, result), true); // Bind the exact server result before reveal.
  assert.equal(lifecycle.snapshot().authoritativeResult, result); // Preserve result object identity without client derivation.
  assert.equal(lifecycle.settle(token), true); // Complete settlement once.
  assert.deepEqual(transitions.map((state) => state.phase), ["locking", "running", "settling", "settled"]); // Require every reviewed phase in order.
  assert.equal(transitions.at(-1).active, false); // Publish terminal settlement without stale action ownership.
  assert.equal(lifecycle.snapshot().active, false); // Release action ownership after settlement.
  assert.ok(MOTION_PHASES.every((phase) => typeof phase === "string")); // Keep the public phase vocabulary stable and enumerable.
});

// Verify MOTION-004 rejects overlap and ignores stale callbacks after recovery.
test("MOTION-004 lifecycle rejects overlap, skips, and stale generations", () => {
  const lifecycle = createMotionLifecycle(); // Create one detached presentation lifecycle.
  const firstToken = lifecycle.begin(); // Start the first action generation.
  assert.throws(() => lifecycle.begin(), /already has an active action/); // Reject overlapping atomic actions.
  assert.throws(() => lifecycle.commit(firstToken, { result: 1 }), /during locking/); // Reject a result reveal that skips running.
  assert.equal(lifecycle.abort(firstToken), true); // Cancel the first action through the explicit terminal phase.
  assert.throws(() => lifecycle.begin(), /must reset after aborted/); // Require explicit recovery before a replacement action.
  assert.equal(lifecycle.reset(), true); // Recover the cancelled lifecycle to idle.
  const secondToken = lifecycle.begin(); // Start a distinct replacement generation.
  assert.equal(lifecycle.run(firstToken), false); // Ignore a stale callback owned by the cancelled generation.
  assert.equal(lifecycle.run(secondToken), true); // Advance only the current generation.
  assert.equal(lifecycle.fail(secondToken), true); // Enter the explicit recoverable failure phase.
  assert.equal(lifecycle.reset(), true); // Recover the failed lifecycle.
  assert.equal(lifecycle.snapshot().phase, "idle"); // Return to the single actionable baseline.
});

// Verify MOTION-004 disposal invalidates active work and future action starts.
test("MOTION-004 lifecycle disposal aborts active presentation ownership", () => {
  const transitions = []; // Record the teardown transition for proof.
  const lifecycle = createMotionLifecycle({ onTransition: (state) => transitions.push(state.phase) }); // Observe one lifecycle through disposal.
  const token = lifecycle.begin(); // Start an action that will be abandoned with its route.
  assert.equal(lifecycle.run(token), true); // Enter its active motion phase.
  assert.equal(lifecycle.dispose(), true); // Abort and dispose the owning route lifecycle.
  assert.equal(lifecycle.commit(token, Object.freeze({ result: 7 })), false); // Ignore a late server callback after disposal.
  assert.deepEqual(transitions, ["locking", "running", "aborted"]); // Publish the explicit cancellation terminal state.
  assert.throws(() => lifecycle.reset(), /disposed/); // Prevent recovery callbacks from mutating disposed presentation state.
  assert.throws(() => lifecycle.begin(), /disposed/); // Prevent route-abandoned lifecycle reuse.
});
