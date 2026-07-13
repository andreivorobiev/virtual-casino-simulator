// Statically verify the isolated issue #94 browser module without global registration.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import JSON and source file reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text.
const source = await readFile(path.join(root, 'web', 'games', 'multi_hand_video_poker.js'), 'utf8');
// Read the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'multi_hand_video_poker.json'), 'utf8'));
// Read the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'multi_hand_video_poker.json'), 'utf8'));

// Verify both required locales expose exactly the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify the catalog-owned export is statically discoverable by #110.
assert.match(source, /export const MultiHandVideoPokerGame\b/);
// Verify the stable browser readiness selector exists in production markup.
assert.match(source, /data-testid="multi-hand-video-poker"/);
// Verify the frontend consumes the shared #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify shared card labels are localized through the game-owned domain.
assert.match(source, /function localizedCard\b/);
// Verify every required mode is represented in one canonical array.
assert.match(source, /const HAND_COUNTS = \[3, 5, 10\]/);
// Verify unresolved deal requests retain one idempotency key for safe browser retry.
assert.match(source, /pendingRequestId = pendingRequestId \|\| nextRequestId\(\)/);
// Verify this module owns no timer that could survive unmount.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify visible titles and actions resolve through resource keys.
for (const key of ['title', 'controls.deal', 'controls.draw', 'controls.wagerPerHand', 'stage.readyTitle', 'paytable.title']) {
  // Require non-empty English copy for every probed visible key.
  assert.equal(typeof english[key], 'string');
  // Require non-empty Russian copy for every probed visible key.
  assert.equal(typeof russian[key], 'string');
  // Reject blank strings that would expose layout-only controls.
  assert.ok(english[key].trim() && russian[key].trim());
}
