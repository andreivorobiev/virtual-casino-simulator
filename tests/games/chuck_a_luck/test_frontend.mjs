// Verify the isolated issue #89 browser module and its shared #97 primitive usage.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import JSON and source reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import the dependency-free Node test runner.
import test from 'node:test';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';
// Import the shared motion primitive for game-owned scheduling tests.
import { createMotionTimerScope } from '../../../web/core/motion.js';
// Import reusable deterministic timer and lifecycle helpers.
import { createFakeClock, createLifecycleTarget } from '../../helpers/motion_test_helpers.mjs';

// Provide the minimal browser global required by the shared i18n module at import time.
globalThis.window = {};
// Import the game exports only after installing the minimal browser global.
const { BET_IDS, ROLL_REVEAL_MS, createDecorativeDice, isDefinitiveRollRejection, scheduleReveal, viewMarkup } = await import('../../../web/games/chuck_a_luck.js');
// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text for boundary assertions.
const source = await readFile(path.join(root, 'web', 'games', 'chuck_a_luck.js'), 'utf8');
// Read the extracted game stylesheet for representative selector preservation.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'chuck_a_luck.css'), 'utf8');
// Read the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'chuck_a_luck.json'), 'utf8'));
// Read the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'chuck_a_luck.json'), 'utf8'));

// Verify DICE-001 deterministic previews remain bounded and non-authoritative.
test('DICE-001 Chuck-a-Luck previews are deterministic and bounded', () => {
  const first = createDecorativeDice('cal-focused-seed'); // Generate one decorative three-die sequence.
  const second = createDecorativeDice('cal-focused-seed'); // Recreate the sequence from the same action identity.
  assert.deepEqual(first, second); // Prove the same retry identity never changes preview faces.
  assert.equal(first.length, 3); // Prove the game consumes exactly three shared dice.
  assert.ok(first.every(face => Number.isInteger(face) && face >= 1 && face <= 6)); // Prove every decorative face is valid.
  assert.equal(Object.isFrozen(first), true); // Prevent callers from mutating a returned preview sequence.
  assert.throws(() => createDecorativeDice(''), /seed is required/); // Reject accidental ambient-random preview seeds.
});

// Verify MOTION-003 the reveal uses only a caller-owned deterministic timer scope.
test('MOTION-003 authoritative reveal honors the injected deadline', () => {
  const clock = createFakeClock(); // Create deterministic timer ownership.
  const calls = []; // Record reveal execution without real time.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: false }); // Create a detached normal-motion scope.
  scheduleReveal({ timerScope: scope, onReveal: () => calls.push('revealed') }); // Schedule the game reveal through the shared primitive.
  clock.advance(ROLL_REVEAL_MS - 1); // Stop immediately before the configured reveal deadline.
  assert.deepEqual(calls, []); // Prove authoritative dice are not revealed early.
  assert.equal(scope.activeCount, 1); // Prove the route still owns exactly one callback.
  clock.advance(1); // Reach the configured reveal deadline.
  assert.deepEqual(calls, ['revealed']); // Prove the callback runs exactly at the injected deadline.
  assert.equal(scope.activeCount, 0); // Prove completion releases timer ownership.
});

// Verify MOTION-001 reduced motion removes decorative delay but remains asynchronous.
test('MOTION-001 reduced motion collapses the reveal duration', () => {
  const clock = createFakeClock(); // Create deterministic zero-delay timer execution.
  let revealed = false; // Track whether the callback has executed.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: true }); // Force reduced motion for this route scope.
  scheduleReveal({ timerScope: scope, onReveal: () => { revealed = true; } }); // Schedule the same game reveal path.
  assert.equal(revealed, false); // Preserve asynchronous semantics before fake time advances.
  clock.advance(0); // Execute reduced-motion zero-delay work.
  assert.equal(revealed, true); // Prove reduced motion removes the decorative wait.
});

// Verify MOTION-002 navigation cleanup prevents a stale authoritative reveal.
test('MOTION-002 route lifecycle cleanup cancels the Chuck-a-Luck reveal', () => {
  const clock = createFakeClock(); // Create deterministic pending timer state.
  const lifecycleTarget = createLifecycleTarget(); // Create a browser-like lifecycle event target.
  let revealed = false; // Detect callbacks that outlive their route.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget }); // Bind cleanup to shared route events.
  scheduleReveal({ timerScope: scope, onReveal: () => { revealed = true; } }); // Schedule one game-owned reveal.
  lifecycleTarget.dispatch('popstate'); // Simulate navigation away from the route.
  clock.advance(ROLL_REVEAL_MS); // Advance beyond the abandoned deadline.
  assert.equal(revealed, false); // Prove the stale callback never runs.
  assert.equal(scope.disposed, true); // Prove navigation permanently disposes the scope.
  assert.equal(clock.pendingCount(), 0); // Prove the underlying timer handle was cleared.
  assert.equal(lifecycleTarget.listenerCount(), 0); // Prove lifecycle listeners were released.
});

// Verify known server rejections unlock invalid actions while ambiguous failures retain retry ownership.
test('retry classification keeps only ambiguous responses pending', () => {
  assert.equal(isDefinitiveRollRejection({ code: 'VALIDATION_ERROR' }), true); // Release a wager the server explicitly rejected.
  assert.equal(isDefinitiveRollRejection({ code: 'INSUFFICIENT_FUNDS' }), true); // Release a debit the ledger explicitly refused.
  assert.equal(isDefinitiveRollRejection({ code: 'CONFLICT' }), true); // Release a conflicting id that cannot be retried unchanged.
  assert.equal(isDefinitiveRollRejection(new TypeError('network interrupted')), false); // Retain an action whose response is unknown.
  assert.equal(isDefinitiveRollRejection({}), false); // Retain an unstructured failure conservatively.
});

// Verify the game markup exposes stable responsive, locale, wager, and dice evidence hooks.
test('issue #89 markup exposes the isolated visual contract', () => {
  const translate = (key, params = {}) => `${key}${params.face ? `-${params.face}` : ''}`; // Provide a deterministic translation seam without loading the DOM runtime.
  const markup = viewMarkup({ translate }); // Render the untouched ready state through production markup.
  assert.match(markup, /data-testid="chuck-a-luck"/); // Expose the visual-matrix readiness selector.
  assert.match(markup, /data-phase="ready"/); // Expose the machine-readable initial phase.
  assert.match(markup, /data-reduced-motion="false"/); // Expose reduced-motion evidence state.
  assert.equal((markup.match(/data-wager="/g) || []).length, 6); // Render exactly six face-wager controls.
  assert.equal((markup.match(/data-die/g) || []).length, 3); // Render exactly three code-native dice.
  assert.match(markup, /min="0\.01" max="1000000" step="0\.01"/); // Align controls with backend token precision and bounds.
  assert.deepEqual(BET_IDS, ['one', 'two', 'three', 'four', 'five', 'six']); // Preserve the frozen canonical wager order.
});

// Verify the one-click repeat control renders, stays disabled without a prior roll, and is localized in both domains.
test('repeat bet control renders localized and disabled before any settled roll', () => {
  const translate = (key, params = {}) => `${key}${params.face ? `-${params.face}` : ''}`; // Reuse a deterministic translation seam without the DOM runtime.
  const markup = viewMarkup({ translate }); // Render the untouched ready state through production markup.
  assert.match(markup, /class="cal-repeat" data-action="repeat"/); // Expose the secondary repeat action with a stable selector.
  assert.match(markup, /data-action="repeat" disabled/); // Keep repeat disabled before a repeatable wager map exists.
  assert.ok(english['controls.repeat']?.trim()); // Require non-empty English repeat copy.
  assert.ok(russian['controls.repeat']?.trim()); // Require non-empty Russian repeat copy.
  assert.match(russian['controls.repeat'], /[А-Яа-яЁё]/); // Prove the Russian repeat copy is real Cyrillic text.
});

// Verify paired game-owned resources remain complete, readable, and free of shell copy.
test('I18N-001 and I18N-002 EN/RU resources have exact parity', () => {
  assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort()); // Require identical resource coverage in both locales.
  // Probe copy needed in ready, rolling, rejection, retry, and settlement states.
  for (const key of ['title', 'action.roll', 'action.retry', 'error.rollFailed', 'error.rollRejected', 'phase.ready', 'phase.rolling', 'phase.settled', 'result.rollingBody']) {
    assert.ok(english[key]?.trim()); // Require non-empty English copy for the visible state.
    assert.ok(russian[key]?.trim()); // Require non-empty Russian copy for the visible state.
  }
  assert.match(russian.title, /[А-Яа-яЁё]/); // Prove the Russian title contains real Cyrillic text.
  assert.doesNotMatch(JSON.stringify(russian), /(?:Ã|Â|Ð|Ñ|�)/); // Reject common UTF-8 mojibake markers.
});

// Verify the isolated module consumes shared primitives without another game or unmanaged timers.
test('module boundary remains game-local and primitive-backed', () => {
  assert.match(source, /from '\.\.\/core\/dice\.js'/); // Consume shared #97 dice primitives.
  assert.match(source, /from '\.\.\/core\/motion\.js'/); // Consume shared #97 motion primitives.
  assert.doesNotMatch(source, /from '\.\/|from '\.\.\/games\//); // Avoid importing another game package.
  assert.doesNotMatch(source, /\bsetTimeout\s*\(|\bsetInterval\s*\(|\brequestAnimationFrame\s*\(/); // Prohibit unmanaged route timers.
  assert.match(source, /post\(`\$\{API_ROOT\}\/rolls`, pendingPayload\)/); // Send the immutable retry payload without caller-selected identity.
  assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath/); // Keep authenticated identity owned by the session-bound router.
});

// Verify issue #718 delegates route ownership without changing the strict retry identity contract.
test('CORE-034 shared lifecycle owns the Chuck-a-Luck route', () => {
  // Require shared mount, busy, locale, external-style, identity, motion, and stale-session ownership.
  for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "requestPrefix: 'cal'", "href: '/games/chuck_a_luck.css'", 'export function createRequestId', 'createMotionTimerScope', 'routeSession']) assert.ok(source.includes(marker), marker);
  // Reject migrated route, busy, locale-subscription, and opaque inline-style owners.
  for (const duplicate of ['let root =', 'let rolling =', 'unsubscribeLocale', 'function ensureStyles', 'const ROUTE_CSS', 'style.textContent', 'onLocaleChange', 'loadI18nDomain']) assert.equal(source.includes(duplicate), false, duplicate);
  // Require representative controls, stage, dice, data, responsive, and reduced-motion rules in external CSS.
  for (const selector of ['.cal-shell {', '.cal-layout {', '.cal-roll {', '.cal-repeat {', '.cal-stage {', '.cal-dice-tray {', '.cal-die.is-rolling {', '.cal-data {', '.cal-paytable {', '.cal-history-row {', '@media (max-width: 1200px)', '@media (max-width: 560px)', '@media (prefers-reduced-motion: reduce)']) assert.ok(stylesheet.includes(selector), selector);
});
