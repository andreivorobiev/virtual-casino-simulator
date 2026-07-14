// Statically verify the isolated issue #134 browser module without global registration.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import JSON and source file reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';

// Provide the global expected by shared frontend modules during import.
globalThis.window = {};

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text.
const source = await readFile(path.join(root, 'web', 'games', 'let_it_ride.js'), 'utf8');
// Read the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'let_it_ride.json'), 'utf8'));
// Read the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'let_it_ride.json'), 'utf8'));
// Import the isolated frontend after installing its minimal shared-module global.
const gameModule = await import('../../../web/games/let_it_ride.js');
// Read the exported catalog contract.
const game = gameModule.LetItRideGame;

// Assert the game id matches the proposed module descriptor.
assert.equal(game.id, 'let_it_ride');
// Assert catalog mounting remains callable.
assert.equal(typeof game.mount, 'function');
// Assert route changes can release module resources.
assert.equal(typeof game.unmount, 'function');
// Verify both required locales expose exactly the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify the stable browser readiness selector exists in production markup.
assert.match(source, /data-testid="let-it-ride"/);
// Verify the frontend consumes the shared #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify shared card labels are localized through the game-owned domain.
assert.match(source, /function localizedCard\b/);
// Verify uncertain API actions retain retry-safe ids.
assert.match(source, /retryActionIds/);
// Verify this module owns no timer that could survive unmount.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify caller-controlled player compatibility helpers are not used by the browser module.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath/);
// Verify visible titles and actions resolve through resource keys.
for (const key of ['title', 'controls.deal', 'controls.pull', 'controls.ride', 'controls.wager', 'paytable.title']) {
  // Require non-empty English copy for every probed visible key.
  assert.equal(typeof english[key], 'string');
  // Require non-empty Russian copy for every probed visible key.
  assert.equal(typeof russian[key], 'string');
  // Reject blank strings that would expose layout-only controls.
  assert.ok(english[key].trim() && russian[key].trim());
}

// Report one concise success line for worker validation logs.
console.log('Let It Ride frontend module tests passed.');
