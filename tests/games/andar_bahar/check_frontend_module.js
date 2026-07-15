// Exercise the isolated Andar Bahar frontend module without a browser runner.

// Import strict assertions for deterministic unit failures.
const assert = require('node:assert/strict');
// Import base64 support used to load the browser ES module as a data URL.
const { Buffer } = require('node:buffer');
// Import file reading so the production module is checked directly.
const { readFile } = require('node:fs/promises');
// Import path helpers so the repository-relative module path is explicit.
const path = require('node:path');

// Run focused static module assertions and surface failures through Node's exit code.
async function main() {
  // Resolve the repository root from this dedicated test file.
  const root = path.resolve(__dirname, '..', '..', '..');
  // Read the production ES module source directly.
  const source = await readFile(path.join(root, 'web', 'games', 'andar_bahar.js'), 'utf8');
  // Verify the module exports the catalog-facing object expected by the descriptor proposal.
  assert.match(source, /export const AndarBaharGame/);
  // Verify no caller-controlled player_id is sent by the frontend action payloads.
  assert.doesNotMatch(source, /player_id/);
  // Verify the module includes the reduced-motion guard required by the issue packet.
  assert.match(source, /prefers-reduced-motion:reduce/);
  // Verify no timer APIs are owned by this game module.
  assert.doesNotMatch(source, /setTimeout|setInterval/);
  // Verify the source can be parsed as an ES module after replacing relative imports with inert data URLs.
  const parseable = source.replace(/import .*? from '..\/core\/.*?';/g, '');
  // Import the parseable source through a standards-compliant JavaScript data URL.
  await import(`data:text/javascript;base64,${Buffer.from(parseable).toString('base64')}`);
}

// Execute the async suite and preserve useful stack output on failure.
main().catch(error => {
  // Print the focused unit failure for worker and CI diagnostics.
  console.error(error);
  // Set a failing process code without hiding asynchronous cleanup.
  process.exitCode = 1;
});
