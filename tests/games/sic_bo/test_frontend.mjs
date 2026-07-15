// Verify issue #88 localization, retry identity, and #97 timer cleanup without shared registration.

// Import strict assertions for deterministic focused failures.
import assert from 'node:assert/strict';
// Import UTF-8 source and locale reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import cross-platform path resolution for this game-owned test.
import path from 'node:path';
// Import URL conversion so the repository root does not depend on the process directory.
import { fileURLToPath } from 'node:url';
// Import the deterministic #97 fake clock and lifecycle target.
import { createFakeClock, createLifecycleTarget } from '../../helpers/motion_test_helpers.mjs';
// Import the production #97 motion scope used by the Sic Bo module.
import { createMotionTimerScope } from '../../../web/core/motion.js';

// Provide the browser global required by the shared i18n module during static import.
globalThis.window = {};
// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text for policy assertions.
const source = await readFile(path.join(root, 'web', 'games', 'sic_bo.js'), 'utf8');
// Read the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'sic_bo.json'), 'utf8'));
// Read the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'sic_bo.json'), 'utf8'));
// Import only the game-owned public seams after the browser global exists.
const { SicBoGame, betLabel, isRecoveryRound, nextActionId, parseWagerAmount, scheduleReveal } = await import('../../../web/games/sic_bo.js');

// Return sorted placeholder names so paired strings must interpolate the same data.
function placeholders(value) {
  // Extract every simple i18n placeholder without relying on translation order.
  return [...value.matchAll(/\{([^}]+)\}/g)].map(match => match[1]).sort();
}

// Verify both required locales expose exactly the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every paired resource is non-empty and preserves interpolation fields.
for (const key of Object.keys(english)) {
  // Require every English entry to be player-readable text.
  assert.ok(typeof english[key] === 'string' && english[key].trim(), `blank English resource: ${key}`);
  // Require every Russian entry to be player-readable text.
  assert.ok(typeof russian[key] === 'string' && russian[key].trim(), `blank Russian resource: ${key}`);
  // Keep placeholder contracts identical across locale switches.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), `placeholder mismatch: ${key}`);
}
// Reject common encoding-corruption markers from the committed paired resources.
assert.doesNotMatch(JSON.stringify({ english, russian }), /�|Ã|Â|Ð|Ñ/);
// Require every directly referenced literal resource key in production to exist.
for (const [, key] of source.matchAll(/\btext\('([^']+)'/g)) {
  // Verify the English domain owns the referenced visible or accessible string.
  assert.ok(Object.hasOwn(english, key), `missing localized key: ${key}`);
}
// Cover resource keys referenced through dynamic group, result, phase, and error maps.
for (const key of [
  'bets.small', 'bets.big', 'bets.any_triple', 'bets.total', 'bets.single', 'bets.double', 'bets.triple', 'bets.combo',
  'groups.ranges', 'groups.totals', 'groups.singles', 'groups.doubles', 'groups.triples', 'groups.combinations',
  'phases.win', 'phases.push', 'phases.loss', 'result.winTitle', 'result.pushTitle', 'result.lossTitle',
  'errors.validation', 'errors.insufficientFunds', 'errors.conflict', 'errors.unauthorized', 'errors.generic',
]) {
  // Require each indirectly selected key in both paired domains.
  assert.ok(Object.hasOwn(english, key) && Object.hasOwn(russian, key), `missing dynamic localized key: ${key}`);
}

// Verify the descriptor-owned export and stable readiness selector.
assert.equal(SicBoGame.id, 'sic_bo');
// Verify the catalog integration hook exists in production markup.
assert.match(source, /data-testid="sic-bo-table"/);
// Verify one injected UUID creates a stable, game-prefixed action identity.
assert.equal(nextActionId(() => '00000000-0000-4000-8000-000000000088'), 'sb-00000000-0000-4000-8000-000000000088');
// Verify dynamic labels consume only the provided translator seam.
assert.equal(betLabel({ kind: 'combo', values: [2, 5] }, (key, values) => `${key}:${values.left}-${values.right}`), 'bets.combo:2-5');
// Accept exact cent notation without changing the caller's value.
assert.equal(parseWagerAmount('1.05'), 1.05);
// Reject excess precision instead of silently rounding it to a different wager.
assert.equal(parseWagerAmount('1.005'), null);
// Honor native number-input step mismatch as an additional validation signal.
assert.equal(parseWagerAmount('1.05', { stepMismatch: true }), null);
// Keep a post-debit settling row in recovery even when committed dice are visible.
assert.equal(isRecoveryRound({ phase: 'settling' }, { phase: 'settling', dice: [3, 3, 3] }), true);
// Allow result rendering only after the server reports terminal settlement.
assert.equal(isRecoveryRound(null, { phase: 'settled', dice: [3, 3, 3], outcome: 'win' }), false);
// Verify the complete server catalog remains the only source of board positions.
assert.match(source, /betCatalog\.filter\(bet => bet\.group === group\)/);
// Verify ambiguous requests retain both action identity and exact wager snapshot.
assert.match(source, /pendingActionId = gameState\?\.active_round\?\.action_id \|\| pendingActionId \|\| nextActionId\(\)/);
// Verify the frozen snapshot is sent without rebuilding from editable controls.
assert.match(source, /action_id: pendingActionId, wagers: pendingWagers/);
// Verify authoritative dice arrive only from the API payload.
assert.doesNotMatch(source, /Math\.random|rollDice|rollDie/);
// Verify every reveal uses the merged #97 lifecycle owner.
assert.match(source, /import \{ createMotionTimerScope \} from '\.\.\/core\/motion\.js'/);
// Verify the module owns no raw timer or animation-frame lifecycle.
assert.doesNotMatch(source, /\bsetTimeout\b|\bsetInterval\b|\brequestAnimationFrame\b/);
// Verify route teardown disposes motion and locale resources.
assert.match(source, /motionScope\.dispose\(\)/);
// Verify route teardown releases the locale subscription.
assert.match(source, /unsubscribeLocale\(\)/);
// Isolate the mount body so generation ownership ordering can be checked directly.
const mountSource = source.slice(source.indexOf('async mount(node)'), source.indexOf('// Release every game-owned lifecycle resource'));
// Capture generation ownership before the first localization await.
assert.ok(mountSource.indexOf('const generation = mountGeneration') < mountSource.indexOf('await loadI18nDomain(DOMAIN)'));
// Require both awaited fetch stages to reject stale or replacement route outlets.
assert.equal((mountSource.match(/root !== node \|\| generation !== mountGeneration/g) || []).length, 3);
// Verify reduced-motion styling remains available even before timer scheduling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify desktop-primary compression preserves the standard 42px position floor.
assert.match(source, /min-height:42px/);
// Verify compact desktop explicitly replaces clipping with one themed game-screen scroll.
assert.match(source, /max-height:950px[\s\S]*game-screen:has\(\.sb-shell\)[\s\S]*overflow-y:auto/);
// Verify API errors are never rendered from server-owned English messages.
assert.doesNotMatch(source, /toast\s*\(\s*error\.message/);

// Create a deterministic ordinary-motion scope for exact reveal timing.
const clock = createFakeClock();
// Create a lifecycle target so listener cleanup can be asserted.
const lifecycle = createLifecycleTarget();
// Bind the production #97 scope to the deterministic clock.
const timerScope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: lifecycle, reducedMotion: false });
// Count completed authoritative reveals.
let revealCount = 0;
// Schedule one normal reveal through the exported Sic Bo seam.
scheduleReveal({ timerScope, duration: 650, onReveal: () => { revealCount += 1; } });
// Verify one callback and all default lifecycle listeners are owned.
assert.equal(clock.pendingCount(), 1);
// Advance just before the requested duration.
clock.advance(649);
// Verify no early authoritative result appears.
assert.equal(revealCount, 0);
// Reach the exact reveal deadline.
clock.advance(1);
// Verify the result reveals exactly once.
assert.equal(revealCount, 1);
// Schedule another reveal to exercise navigation cleanup.
scheduleReveal({ timerScope, duration: 650, onReveal: () => { revealCount += 1; } });
// Trigger the shared reload/navigation cleanup path.
lifecycle.dispatch('pagehide');
// Verify the pending callback and all lifecycle listeners were released.
assert.equal(clock.pendingCount(), 0);
// Advance beyond the cancelled deadline.
clock.advance(1000);
// Verify route exit prevented stale UI mutation.
assert.equal(revealCount, 1);
// Verify the production scope reached its terminal disposed state.
assert.equal(timerScope.disposed, true);

// Create a second deterministic scope with reduced motion requested.
const reducedClock = createFakeClock();
// Bind reduced motion to a detached lifecycle target for one exact assertion.
const reducedScope = createMotionTimerScope({ setTimeoutFn: reducedClock.setTimeoutFn, clearTimeoutFn: reducedClock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: true });
// Track the reduced-motion reveal callback.
let reducedRevealCount = 0;
// Schedule the same decorative reveal duration under reduced motion.
scheduleReveal({ timerScope: reducedScope, duration: 650, onReveal: () => { reducedRevealCount += 1; } });
// Drain the zero-duration asynchronous callback.
reducedClock.advance(0);
// Verify reduced motion preserves the state transition without delay.
assert.equal(reducedRevealCount, 1);
// Dispose the completed reduced-motion owner for repeated-test hygiene.
reducedScope.dispose();
