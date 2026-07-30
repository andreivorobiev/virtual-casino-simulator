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

// Provide the minimal browser global required by shared core modules at import time.
globalThis.window = {};
// Import the tested game exports only after installing the minimal browser global.
const { composeLandingStrip, reelStopDuration, countEarlyScatters, REEL_BASE_STOP_MS, REEL_STAGGER_MS, REEL_ANTICIPATION_MS, REEL_TRAVEL_BASE_ROWS, REEL_TRAVEL_STEP_ROWS, REDUCED_HOLD_MS, AUTOPLAY_HOLD_MS } = await import('../../../web/games/slots.js');
// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text for guard-wiring assertions.
const source = await readFile(path.join(root, 'web', 'games', 'slots.js'), 'utf8');

// Store one committed result grid whose columns are all distinct for landing assertions.
const RESULT_GRID = [['SEVEN', 'CHERRY', 'BAR', 'BELL', 'WILD'], ['LEMON', 'SCATTER', 'SEVEN', 'CHERRY', 'BAR'], ['BELL', 'WILD', 'LEMON', 'SCATTER', 'CHERRY']];
// Store one distinct launch grid representing the symbols already visible on the cabinet.
const SHOWN_GRID = [['BAR', 'BELL', 'CHERRY', 'LEMON', 'SEVEN'], ['WILD', 'BAR', 'BELL', 'CHERRY', 'LEMON'], ['CHERRY', 'LEMON', 'BAR', 'WILD', 'BELL']];

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
  assert.equal(AUTOPLAY_HOLD_MS, 180); // Prove unattended cadence is unchanged from the pre-redesign contract.
});

// Verify MOTION-002 every reel timer runs through the guarded route-owned scope.
test('MOTION-002 reel timers are guarded against a disposed route scope', () => {
  assert.match(source, /if \(!grid \|\| !motionLayer \|\| !cellA \|\| !cellB \|\| !motionScope \|\| motionScope\.disposed\) \{ resolve\(\); return; \}/, 'the landing must degrade when the scope or overlay is gone'); // Pin the landing entry guard.
  assert.match(source, /if \(!motionScope \|\| motionScope\.disposed\) return Promise\.resolve\(\);/, 'waitMotion must degrade on a disposed scope'); // Pin the reveal-wait guard.
  assert.match(source, /if \(motionScope\) motionScope\.dispose\(\); motionScope = null;/, 'unmount must dispose and release the route scope'); // Pin route-teardown timer cleanup.
});

// Verify SLOT-028 the spinning render defers foreign repaints so live strips are never destroyed.
test('SLOT-028 locale and bot repaints defer while a spin owns the cabinet', () => {
  assert.match(source, /onLocaleChange\(\(\) => \{ if \(spinning\) \{ pendingRender = true; return; \} render\(\); \}\)/, 'locale changes must defer during a spin'); // Pin the locale deferral.
  assert.match(source, /if \(root && !spinning\) render\(\); else if \(root\) pendingRender = true;/, 'bot-panel refreshes must defer during a spin'); // Pin the bot-panel deferral.
});
