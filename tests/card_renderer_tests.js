// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Exercise CARD-002 without requiring a browser or third-party JavaScript test runner.

// Import strict assertions for deterministic unit failures.
const assert = require('node:assert/strict');
// Import base64 support used to load the browser ES module as a data URL.
const { Buffer } = require('node:buffer');
// Import file reading so the production renderer is tested directly.
const { readFile } = require('node:fs/promises');
// Import URL helpers so the renderer path is stable on Windows and POSIX.
const { fileURLToPath } = require('node:url');
// Import path helpers so the repository-relative module path is explicit.
const path = require('node:path');

// Run focused renderer assertions and surface failures through Node's exit code.
async function main() {
  // Resolve the repository root from this dedicated test file.
  const root = path.resolve(path.dirname(fileURLToPath(`file:///${__filename.replace(/\\/g, '/')}`)), '..');
  // Read the production ES module without changing repository-wide module settings.
  const source = await readFile(path.join(root, 'web', 'core', 'cards.js'), 'utf8');
  // Import the production source through a standards-compliant JavaScript data URL.
  const renderer = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  // Normalize compact and object cards through the public renderer boundary.
  assert.deepEqual(renderer.normalizeCard('AS'), renderer.normalizeCard({ rank: 'A', suit: 'spades' }));
  // Render a selected visible card for accessibility and state checks.
  const visible = renderer.renderCard('AH', { selected: true });
  // Verify the visible card exposes one stable accessible label.
  assert.match(visible, /aria-label="Ace of hearts"/);
  // Verify selection is communicated independently of color.
  assert.match(visible, /aria-current="true"/);
  // Verify suit color remains available as a presentation hook.
  assert.match(visible, /playing-card--red/);
  // Render a hidden card while passing an unsafe class name.
  const hidden = renderer.renderCard('??', { className: 'safe bad\" onclick=alert(1)' });
  // Verify hidden identity is never exposed in accessible output.
  assert.match(hidden, /aria-label="Face-down playing card"/);
  // Verify safe class tokens survive while injection-shaped values do not.
  assert.match(hidden, / safe"/);
  // Verify the unsafe handler text is absent.
  assert.doesNotMatch(hidden, /onclick/);
  // Simulate a platform that requests reduced motion.
  const reduced = renderer.prefersReducedMotion(query => ({ matches: query.includes('reduce') }));
  // Verify the media-query adapter reports the preference.
  assert.equal(reduced, true);
  // Verify absent browser APIs produce the safe no-preference default.
  assert.equal(renderer.prefersReducedMotion(undefined), false);
}

// Execute the async suite and preserve useful stack output on failure.
main().catch(error => {
  // Print the focused unit failure for worker and CI diagnostics.
  console.error(error);
  // Set a failing process code without hiding asynchronous cleanup.
  process.exitCode = 1;
});
