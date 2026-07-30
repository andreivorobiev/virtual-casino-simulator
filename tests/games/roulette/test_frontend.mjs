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

// Provide the minimal browser global required by shared core modules at import time.
globalThis.window = {};
// Import the tested game exports only after installing the minimal browser global.
const { computeLandingPlan, pocketBaseAngle, norm360, SPIN_REVEAL_MS, AUTOPLAY_REVEAL_MS, REDUCED_REVEAL_MS, MIN_LANDING_MS, WHEEL_EXTRA_TURNS, BALL_EXTRA_TURNS } = await import('../../../web/games/roulette.js');
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
});

// Verify ROU-059 the unmount refund guard still suppresses the mid-spin clear race.
test('ROU-059 unmount refund keeps its committed-spin suppression', () => {
  assert.match(source, /const wasSpinning = spinBusy;/, 'unmount must capture the live spin state before releasing it'); // Pin the pre-reset capture.
  assert.match(source, /if \(humanBets\(\)\.length && !wasSpinning\) \{/, 'the refund must consult the captured spin state'); // Pin the live guard so the issue-246 race cannot return.
});
