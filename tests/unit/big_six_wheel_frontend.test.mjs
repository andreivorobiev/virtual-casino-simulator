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
const { BigSixWheelGame, createClientRequestId, rotationForIndex, scheduleSettlement, viewMarkup } = await import('../../web/games/big_six_wheel.js');

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
