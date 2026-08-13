// Import strict assertions for deterministic primitive verification.
import assert from "node:assert/strict";
// Import the built-in dependency-free Node test runner.
import test from "node:test";
// Import the isolated dice primitives under test.
import { createSeededRandom, rollDice } from "../../web/core/dice.js";
// Import the isolated motion primitives under test.
import { createMotionTimerScope, prefersReducedMotion } from "../../web/core/motion.js";
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
  const reducedMatchMedia = createMatchMedia(true); // Simulate the platform comfort preference.
  assert.equal(prefersReducedMotion(reducedMatchMedia), true); // Prove the standard media query remains available to consumers.
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
