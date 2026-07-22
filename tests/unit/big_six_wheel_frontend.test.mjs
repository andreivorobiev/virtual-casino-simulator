// Import strict assertions for deterministic frontend verification.
import assert from 'node:assert/strict';
// Import filesystem helpers to compare complete EN/RU resource coverage.
import { readFile } from 'node:fs/promises';
// Import the dependency-free built-in test runner.
import test from 'node:test';
// Import merged #97 fake timer and lifecycle helpers.
import { createFakeClock, createLifecycleTarget } from '../helpers/motion_test_helpers.mjs';
// Import the shared reduced-motion timer scope used by the route.
import { createMotionTimerScope } from '../../web/core/motion.js';
// Provide the minimal browser global assigned by imported shared frontend helpers.
globalThis.window = {};
// Import pure Big Six presentation helpers after the browser global exists.
const { BigSixWheelGame, createClientRequestId, MIN_SPIN_REVOLUTIONS, rotationForIndex, scheduleSettlement, viewMarkup, WHEEL_SIZE } = await import('../../web/games/big_six_wheel.js');

// Verify the catalog-declared module export and deterministic rotation model.
test('issue 86 frontend exposes stable module and wheel geometry', () => {
  // Verify the descriptor-facing export owns the expected game id.
  assert.equal(BigSixWheelGame.id, 'big_six_wheel');
  // Verify identical results always produce identical landing transforms.
  assert.equal(rotationForIndex(17), rotationForIndex(17));
  // Verify adjacent indices differ by exactly one 54-segment angle.
  assert.ok(Math.abs((rotationForIndex(17) - rotationForIndex(18)) - (360 / 54)) < 1e-9);
  // Reject API data outside the canonical wheel.
  assert.throws(() => rotationForIndex(54), /resultIndex/);
});

// Verify repeated spins retain clockwise progress and exact server-selected alignment.
test('issue 223 repeated wheel targets never reverse, freeze, or misalign', () => {
  // Start from the same neutral transform used by a first-time route mount.
  let currentAngle = 0;
  // Exercise more than the issue's minimum consecutive-spin acceptance count.
  for (let spinIndex = 0; spinIndex < 120; spinIndex += 1) {
    // Walk a nontrivial deterministic result pattern across every wheel segment.
    const resultIndex = ((spinIndex * 17) + 11) % WHEEL_SIZE;
    // Calculate the next cumulative transform from the previous settled target.
    const targetAngle = rotationForIndex(resultIndex, MIN_SPIN_REVOLUTIONS, currentAngle);
    // Require at least the configured complete turns of forward progress on every spin.
    assert.ok(targetAngle - currentAngle >= (MIN_SPIN_REVOLUTIONS * 360) - 1e-9);
    // Calculate the canonical selected-segment orientation below the fixed pointer.
    const expectedLanding = (360 - ((resultIndex + 0.5) * (360 / WHEEL_SIZE))) % 360;
    // Normalize the cumulative transform without discarding its forward-motion history.
    const actualLanding = ((targetAngle % 360) + 360) % 360;
    // Require the final pointer orientation to match the server-selected segment center.
    assert.ok(Math.abs(actualLanding - expectedLanding) < 1e-8);
    // Carry the settled target into the next spin so absolute-reset regressions fail.
    currentAngle = targetAngle;
  }
});

// Verify scheduling calculates its target from the caller's current wheel transform.
test('issue 223 settlement scheduling preserves cumulative motion context', () => {
  // Create deterministic lifecycle-owned timing without a browser dependency.
  const clock = createFakeClock();
  // Build a normal-motion scope using the fake clock.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: false });
  // Seed the helper with a transform from an earlier settled spin.
  const currentAngle = rotationForIndex(7);
  // Track whether presentation remains hidden until its configured duration.
  let settled = false;
  // Schedule a different result from the prior cumulative target.
  const presentation = scheduleSettlement({ timerScope: scope, resultIndex: 41, currentAngle, onSettled: () => { settled = true; } });
  // Require another full forward presentation rather than an absolute-angle reset.
  assert.ok(presentation.angle - currentAngle >= (MIN_SPIN_REVOLUTIONS * 360) - 1e-9);
  // Keep the authoritative result hidden immediately after scheduling.
  assert.equal(settled, false);
  // Advance to just before the declared animation duration.
  clock.advance(1399);
  // Require result presentation to remain hidden while motion is active.
  assert.equal(settled, false);
  // Advance through the final millisecond of the animation contract.
  clock.advance(1);
  // Reveal the result only after the declared motion duration completes.
  assert.equal(settled, true);
});

// Verify secure client identities retain one readable game prefix.
test('issue 86 client request identity uses injected UUID source', () => {
  // Inject a deterministic UUID provider without ambient browser crypto.
  const requestId = createClientRequestId(() => '00000000-0000-4000-8000-000000000086');
  // Verify the public action identity is stable and game-specific.
  assert.equal(requestId, 'bsw-00000000-0000-4000-8000-000000000086');
});

// Verify reduced motion settles asynchronously at zero delay.
test('issue 86 reduced motion collapses presentation timing', () => {
  // Create deterministic timer ownership.
  const clock = createFakeClock();
  // Build a detached reduced-motion scope.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: true });
  // Track final result presentation.
  let settled = false;
  // Schedule the wheel reveal through the shared scope.
  const presentation = scheduleSettlement({ timerScope: scope, resultIndex: 0, onSettled: () => { settled = true; } });
  // Verify an angle was computed without running the callback inline.
  assert.equal(typeof presentation.angle, 'number');
  // Preserve asynchronous semantics before the zero-delay clock advances.
  assert.equal(settled, false);
  // Run reduced-motion work at its zero-delay deadline.
  clock.advance(0);
  // Verify settlement is now visible.
  assert.equal(settled, true);
});

// Verify navigation cleanup prevents abandoned spin callbacks.
test('issue 86 route lifecycle cleanup leaves no runaway timer', () => {
  // Create deterministic timer ownership.
  const clock = createFakeClock();
  // Create a browser-like lifecycle target.
  const lifecycle = createLifecycleTarget();
  // Build the same lifecycle-bound scope used by the mounted route.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: lifecycle, reducedMotion: false });
  // Track whether stale result presentation executes.
  let settled = false;
  // Schedule one normal wheel settlement.
  scheduleSettlement({ timerScope: scope, resultIndex: 12, onSettled: () => { settled = true; } });
  // Simulate leaving the route before the animation completes.
  lifecycle.dispatch('popstate');
  // Advance beyond the normal duration.
  clock.advance(2000);
  // Verify the abandoned callback never ran.
  assert.equal(settled, false);
  // Verify both scope and fake platform timers are empty.
  assert.equal(scope.activeCount, 0);
  // Verify the underlying scheduler has no runaway handles.
  assert.equal(clock.pendingCount(), 0);
});

// Verify complete locale key parity and injected translation rendering.
test('issue 86 EN and RU resources have exact clean coverage', async () => {
  // Read the English game-owned dictionary.
  const english = JSON.parse(await readFile(new URL('../../web/i18n/en-US/games/big_six_wheel.json', import.meta.url), 'utf8'));
  // Read the Russian game-owned dictionary.
  const russian = JSON.parse(await readFile(new URL('../../web/i18n/ru-RU/games/big_six_wheel.json', import.meta.url), 'utf8'));
  // Verify every visible key exists in both locales.
  assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
  // Build route markup through a translator that makes every key observable.
  const markup = viewMarkup({ translate: (key, params = {}) => `RU:${key}${params.amount ? `:${params.amount}` : ''}` });
  // Verify the title and primary action came through the injected locale seam.
  assert.match(markup, /RU:title/);
  // Verify no hard-coded visible English primary action leaked into markup.
  assert.doesNotMatch(markup, />Spin wheel</);
  // Verify the empty history state is localized through the same seam.
  assert.match(markup, /RU:history\.empty/);
});

// Verify responsive ownership aligns stacking with the shared document-scroll transition.
test('issue 227 Big Six keeps essential stage complete across compact and stacked layouts', async () => {
  // Read the game-owned source so the embedded route CSS remains observable without a browser.
  const source = await readFile(new URL('../../web/games/big_six_wheel.js', import.meta.url), 'utf8');
  // Keep desktop compact in the three-zone layout while shrinking only its wheel theater.
  assert.match(source, /@media\(max-width:1500px\) and \(min-width:1201px\).*wheel-shell\{width:min\(54vh,480px\)/);
  // Stack only at the same 1200-pixel boundary where the shared shell enables document scrolling.
  assert.match(source, /@media\(max-width:1200px\).*layout\{grid-template-columns:1fr/);
  // Make the stacked stage contribute complete intrinsic rows instead of clipping the pointer, wheel, or hub.
  assert.match(source, /stage\{order:2;grid-template-rows:auto auto;align-content:start;overflow:visible\}/);
});
