// Statically verify the isolated issue #130 browser module without global registration.

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
const source = await readFile(path.join(root, 'web', 'games', 'joker_poker.js'), 'utf8');
// Read the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'joker_poker.json'), 'utf8'));
// Read the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'joker_poker.json'), 'utf8'));

// Verify both required locales expose exactly the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify the future catalog-owned export is statically discoverable by #77.
assert.match(source, /export const JokerPokerGame\b/);
// Verify the stable browser readiness selector exists in production markup.
assert.match(source, /data-testid="joker-poker"/);
// Verify the frontend consumes the shared #96 accessible natural-card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify the joker card remains game-owned instead of changing shared primitives.
assert.match(source, /function renderJokerCard\b/);
// Verify unresolved deal requests retain one idempotency key for safe browser retry.
assert.match(source, /pendingDeal = pendingDeal \|\| \{ actionId: nextActionId\(\), wager \}/);
// Verify unresolved draw requests retain one idempotency key for safe browser retry.
assert.match(source, /pendingDraw = pendingDraw \|\| \{ actionId: nextActionId\(\), roundId: activeRound\.round_id, holds:/);
// Verify the retained draw request snapshots the active held positions.
assert.ok(source.includes('holds: [...(activeRound.holds || [])]'));
// Verify this module owns no timer that could survive unmount.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify visible titles and actions resolve through resource keys.
for (const key of ['title', 'controls.deal', 'controls.draw', 'controls.wager', 'stage.readyTitle', 'paytable.title', 'cards.jokerLabel']) {
  // Require non-empty English copy for every probed visible key.
  assert.equal(typeof english[key], 'string');
  // Require non-empty Russian copy for every probed visible key.
  assert.equal(typeof russian[key], 'string');
  // Reject blank strings that would expose layout-only controls.
  assert.ok(english[key].trim() && russian[key].trim());
}
