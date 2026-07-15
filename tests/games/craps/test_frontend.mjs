// Verify the isolated Craps browser module, localization, and #97 lifecycle reuse.

// Import strict assertions for deterministic frontend failure output.
import assert from 'node:assert/strict';
// Import UTF-8 source and locale reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import the dependency-free Node test runner.
import test from 'node:test';
// Import reusable #97 fake time and lifecycle targets.
import { createFakeClock, createLifecycleTarget } from '../../helpers/motion_test_helpers.mjs';
// Import the shared disposable scope used by the production route.
import { createMotionTimerScope } from '../../../web/core/motion.js';

// Provide the minimal browser global assigned by the shared i18n module at import time.
globalThis.window = {};
// Import production helpers only after the browser-compatible global exists.
const { CrapsGame, createClientRequestId, createCosmeticDiceFrames, isValidWager, pendingSettlementRecovery, scheduleRollPresentation, viewMarkup } = await import('../../../web/games/craps.js');
// Read the production source for ownership and unmanaged-timer assertions.
const source = await readFile(new URL('../../../web/games/craps.js', import.meta.url), 'utf8');
// Read the complete English game-owned resource domain as UTF-8.
const english = JSON.parse(await readFile(new URL('../../../web/i18n/en-US/games/craps.json', import.meta.url), 'utf8'));
// Read the complete Russian game-owned resource domain as UTF-8.
const russian = JSON.parse(await readFile(new URL('../../../web/i18n/ru-RU/games/craps.json', import.meta.url), 'utf8'));

// Return sorted named interpolation placeholders from one localized value.
function placeholders(value) {
  // Match every supported shared-i18n named placeholder exactly once.
  return [...String(value).matchAll(/\{([A-Za-z0-9_]+)\}/g)].map(match => match[1]).sort();
}

// Build one complete point-round presentation model for pure markup assertions.
function pointModel(overrides = {}) {
  // Define one authoritative server roll with a settled display pair.
  const roll = { request_id: 'roll-1', roll_index: 1, dice: [6, 5], total: 11, point_before: 6, point_after: 6, resolution: 'no_decision', created_at: '2026-07-14T00:00:00Z' };
  // Define one reload-safe active round using the confirmed API contract.
  const roundItem = { round_id: 'round-1', start_request_id: 'start-1', player_id: 'session-player', bet_type: 'pass_line', wager: 5, phase: 'point', point: 6, rolls: [roll], outcome: null, wager_status: 'complete', settlement_status: 'not_ready' };
  // Return every field consumed by pure viewMarkup generation.
  return { state: { active_round: roundItem, recent_rounds: [] }, betTypes: ['pass_line', 'dont_pass'], selectedBetType: 'pass_line', wager: 5, displayedRound: roundItem, displayedRoll: roll, visibleDice: null, busyAction: null, presentationPhase: null, errorKey: null, reducedMotionActive: false, ...overrides };
}

// Verify catalog-facing module identity and secure deterministic request-id injection.
test('issue 90 exposes the Craps module contract and stable request prefixes', () => {
  // Require the exact catalog descriptor id.
  assert.equal(CrapsGame.id, 'craps');
  // Inject one deterministic UUID for a start identity.
  const startId = createClientRequestId('start', () => '00000000-0000-4000-8000-000000000090');
  // Require a readable game/action prefix without player information.
  assert.equal(startId, 'craps-start-00000000-0000-4000-8000-000000000090');
  // Inject one deterministic UUID for an independently retryable roll.
  const rollId = createClientRequestId('roll', () => '00000000-0000-4000-8000-000000000091');
  // Require the separate roll action family.
  assert.equal(rollId, 'craps-roll-00000000-0000-4000-8000-000000000091');
});

// Verify the client accepts only finite OpenAPI wager values expressed in exact cents.
test('issue 90 validates the complete OpenAPI wager amount domain', () => {
  // Accept both inclusive boundaries and ordinary whole-cent values.
  for (const value of [0.01, 0.29, 1, 99999.99, 100000]) assert.equal(isValidWager(value), true, `expected ${value} to be valid`);
  // Reject non-numeric, non-finite, out-of-range, and fractional-cent values.
  for (const value of ['5', null, Number.NaN, Number.NEGATIVE_INFINITY, Number.POSITIVE_INFINITY, 0, 0.009, 1.001, 100000.01]) assert.equal(isValidWager(value), false, `expected ${String(value)} to be invalid`);
});

// Verify cosmetic pairs use the merged #97 deterministic dice seam.
test('issue 90 cosmetic dice frames are deterministic and bounded', () => {
  // Generate the first cosmetic sequence from a server-owned identity seed.
  const first = createCosmeticDiceFrames('round-1:roll-1', 6);
  // Recreate the sequence from the same identity.
  const second = createCosmeticDiceFrames('round-1:roll-1', 6);
  // Prove reloads and tests reproduce the exact same cosmetic frames.
  assert.deepEqual(first, second);
  // Prove every decorative frame remains a standard pair of six-sided faces.
  assert.ok(first.every(pair => pair.length === 2 && pair.every(face => face >= 1 && face <= 6)));
});

// Verify normal-motion presentation orders cosmetics before authoritative dice.
test('issue 90 presentation reveals only the supplied server pair at completion', () => {
  // Create manually controlled platform timers.
  const clock = createFakeClock();
  // Create a detached normal-motion route scope.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: false });
  // Record every visible pair in execution order.
  const seen = [];
  // Schedule two cosmetic pairs followed by one separately supplied server pair.
  const presentation = scheduleRollPresentation({ timerScope: scope, frames: [[1, 2], [3, 4]], finalDice: [6, 6], frameDelay: 10, onFrame: frame => seen.push(['cosmetic', frame]), onSettled: dice => seen.push(['server', dice]) });
  // Verify the deterministic final deadline.
  assert.equal(presentation.finalDelay, 30);
  // Stop before the first decorative deadline.
  clock.advance(9);
  // Prove no callback executes early.
  assert.deepEqual(seen, []);
  // Reach the first cosmetic deadline.
  clock.advance(1);
  // Prove the first pair remains explicitly cosmetic.
  assert.deepEqual(seen, [['cosmetic', [1, 2]]]);
  // Advance through the remaining callbacks.
  clock.advance(20);
  // Prove the final announced pair is exactly the independent server pair.
  assert.deepEqual(seen.at(-1), ['server', [6, 6]]);
});

// Verify reduced motion preserves asynchronous semantics at zero delay.
test('issue 90 reduced motion collapses every game-owned delay', () => {
  // Create deterministic platform timers.
  const clock = createFakeClock();
  // Create the same detached reduced-motion scope used by focused consumers.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: null, reducedMotion: true });
  // Track authoritative settlement separately from cosmetic callbacks.
  let settled = false;
  // Schedule one decorative frame and one authoritative result.
  scheduleRollPresentation({ timerScope: scope, frames: [[2, 3]], finalDice: [4, 5], onFrame: () => {}, onSettled: () => { settled = true; } });
  // Preserve asynchronous behavior before the fake event loop advances.
  assert.equal(settled, false);
  // Drain every reduced zero-delay callback.
  clock.advance(0);
  // Prove the authoritative result settles without decorative waiting.
  assert.equal(settled, true);
  // Prove the scope releases completed callback ownership.
  assert.equal(scope.activeCount, 0);
});

// Verify route lifecycle teardown prevents abandoned result presentation.
test('issue 90 navigation disposal leaves no runaway timer', () => {
  // Create deterministic platform timers.
  const clock = createFakeClock();
  // Create a browser-like lifecycle target.
  const lifecycle = createLifecycleTarget();
  // Build the same lifecycle-bound scope created by CrapsGame.mount.
  const scope = createMotionTimerScope({ setTimeoutFn: clock.setTimeoutFn, clearTimeoutFn: clock.clearTimeoutFn, lifecycleTarget: lifecycle, reducedMotion: false });
  // Track any stale callback after navigation.
  let callbackCount = 0;
  // Schedule decorative and authoritative presentation work.
  scheduleRollPresentation({ timerScope: scope, frames: [[1, 1], [2, 2]], finalDice: [3, 3], onFrame: () => { callbackCount += 1; }, onSettled: () => { callbackCount += 1; } });
  // Simulate shell history navigation before the first deadline.
  lifecycle.dispatch('popstate');
  // Advance beyond every abandoned callback.
  clock.advance(2000);
  // Prove stale cosmetic and authoritative callbacks never execute.
  assert.equal(callbackCount, 0);
  // Prove the scope records permanent disposal.
  assert.equal(scope.disposed, true);
  // Prove underlying platform handles were cancelled.
  assert.equal(clock.pendingCount(), 0);
  // Prove lifecycle listener ownership was released.
  assert.equal(lifecycle.listenerCount(), 0);
});

// Verify hard reload selects only a persisted terminal request for settlement recovery.
test('issue 90 reload recovery reuses the terminal roll identity', () => {
  // Define one settled archived round whose ledger settlement was interrupted.
  const interrupted = { round_id: 'round-recovery', phase: 'settled', settlement_status: 'pending', rolls: [{ request_id: 'roll-recovery', roll_index: 2, dice: [6, 1], total: 7, resolution: 'seven_out' }] };
  // Require recovery to select the exact persisted round and roll identities.
  assert.deepEqual(pendingSettlementRecovery({ active_round: null, recent_rounds: [interrupted] }), { round_id: 'round-recovery', request_id: 'roll-recovery' });
  // Mark the same round complete to prove settled history is not replayed normally.
  const complete = { ...interrupted, settlement_status: 'complete' };
  // Require no recovery after ledger settlement completion.
  assert.equal(pendingSettlementRecovery({ active_round: null, recent_rounds: [complete] }), null);
  // Define an in-progress point round with a pending settlement marker.
  const active = { ...interrupted, phase: 'point' };
  // Require nonterminal gameplay never to replay a roll during mount.
  assert.equal(pendingSettlementRecovery({ active_round: active, recent_rounds: [] }), null);
});

// Verify exact EN/RU keys and named interpolation contracts.
test('issue 90 EN and RU domains have exact key and placeholder parity', () => {
  // Require every visible and ARIA key to exist in both required locales.
  assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
  // Compare placeholder names for every owned resource value.
  for (const key of Object.keys(english)) assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), key);
  // Require the descriptor probe in both locales.
  assert.ok(english['controls.roll'].trim() && russian['controls.roll'].trim());
  // Require every backend resolution enum to map to owned visible copy.
  for (const resolution of ['natural', 'craps', 'bar_twelve', 'point_hit', 'seven_out', 'no_decision']) assert.ok(english[`resolution.${resolution}`].trim() && russian[`resolution.${resolution}`].trim(), resolution);
});

// Verify pure markup routes visible and accessible copy through one translator.
test('issue 90 markup has localized visible and ARIA strings without English leakage', () => {
  // Make every requested key observable without relying on browser locale state.
  const translate = (key, params = {}) => `RU:${key}${Object.keys(params).length ? `:${Object.values(params).join('|')}` : ''}`;
  // Render a complete active point state through the injected translator.
  const markup = viewMarkup({ translate, model: pointModel() });
  // Require the title to come through the owned domain seam.
  assert.match(markup, /RU:title/);
  // Require the primary action to use the descriptor-probed key.
  assert.match(markup, /RU:controls\.roll/);
  // Require rail and stage accessible names to use localized keys.
  assert.match(markup, /aria-label="RU:controls\.aria"/);
  // Require each code-native die accessible name to use localized copy.
  assert.match(markup, /RU:dice\.dieLabel/);
  // Reject representative hard-coded English player copy.
  assert.doesNotMatch(markup, />Roll dice<|>Play controls<|Craps wager controls|Dice show/);
});

// Verify cosmetic state cannot replace authoritative dice outside the rolling phase.
test('issue 90 settled markup prefers server dice over cosmetic frames', () => {
  // Make key parameters observable inside accessible names.
  const translate = (key, params = {}) => `${key}:${Object.values(params).join('|')}`;
  // Supply conflicting decorative faces while the committed phase owns presentation.
  const markup = viewMarkup({ translate, model: pointModel({ visibleDice: [1, 1], presentationPhase: null }) });
  // Require the pair label to expose authoritative faces 6 and 5 with total 11.
  assert.match(markup, /dice\.pairLabel:6\|5\|11/);
  // Reject the conflicting cosmetic pair from the group label.
  assert.doesNotMatch(markup, /dice\.pairLabel:1\|1\|2/);
});

// Verify static ownership, shared primitive reuse, and timer discipline.
test('issue 90 source remains isolated, retry-safe, and free of raw timers', () => {
  // Require the exact catalog-facing export and readiness selector.
  assert.match(source, /export const CrapsGame\b/);
  // Require the exact visual readiness marker.
  assert.match(source, /data-testid="craps"/);
  // Require cosmetic generation through the merged #97 dice helper.
  assert.match(source, /createSeededRandom[\s\S]*rollDice/);
  // Require route timing through the merged #97 disposable scope.
  assert.match(source, /createMotionTimerScope/);
  // Reject unmanaged timer and animation-loop APIs from game-owned source.
  assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
  // Reject the legacy glyph-bearing formatter from game-owned token copy.
  assert.doesNotMatch(source, /formatMoney/);
  // Reject the shared toast helper because its global timer is outside the route scope.
  assert.doesNotMatch(source, /\btoast\b/);
  // Require unresolved action identities to be retained across exact retries.
  assert.match(source, /pendingStartRequestId = pendingStartRequestId \|\| createClientRequestId\('start'\)/);
  // Require contract validation to precede creation of a debit identity.
  assert.match(source, /if \(!isValidWager\(candidateWager\)\)[\s\S]*pendingStartRequestId = pendingStartRequestId \|\| createClientRequestId\('start'\)/);
  // Require the semantic input to expose the contract maximum alongside its minimum and step.
  assert.match(source, /min="0\.01" max="100000" step="0\.01"/);
  // Require unresolved roll identities to be retained across exact retries.
  assert.match(source, /pendingRollRequestId = pendingRollRequestId \|\| createClientRequestId\('roll'\)/);
  // Require wallet refresh failure containment after a confirmed start response.
  assert.match(source, /await refreshBalance\(\)\.catch\(\(\) => \{\}\)/);
  // Require reload recovery to replay the persisted terminal identity directly.
  assert.match(source, /request_id: recovery\.request_id/);
  // Reject caller-selected player fields from public action bodies.
  assert.doesNotMatch(source, /player_id\s*:/);
});
