// Statically verify the isolated issue #95 browser module and paired locales.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import UTF-8 source and resource reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import portable path resolution for Windows and POSIX execution.
import path from 'node:path';
// Import URL conversion for one stable repository root.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-local test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');
// Read the production browser module as UTF-8 text.
const source = await readFile(path.join(root, 'web', 'games', 'texas_holdem_practice_table.js'), 'utf8');
// Parse the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'texas_holdem_practice_table.json'), 'utf8'));
// Parse the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'texas_holdem_practice_table.json'), 'utf8'));

// Extract named interpolation placeholders from one resource value.
function placeholders(value) {
  // Return a stable sorted list of every named placeholder.
  return [...String(value).matchAll(/\{([A-Za-z0-9_]+)\}/g)].map(match => match[1]).sort();
}

// Verify both required locales expose exactly the same resource keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every paired resource preserves the same placeholder contract.
for (const key of Object.keys(english)) {
  // Require exact named interpolation parity for this resource key.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), key);
  // Reject blank visible or accessible English copy.
  assert.ok(String(english[key]).trim(), key);
  // Reject blank visible or accessible Russian copy.
  assert.ok(String(russian[key]).trim(), key);
}
// Verify the proposed catalog export remains statically discoverable.
assert.match(source, /export const TexasHoldemPracticeTableGame\b/);
// Verify the stable browser readiness selector exists in production markup.
assert.match(source, /data-testid="texas-holdem-practice-table"/);
// Verify the frontend consumes the shared #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify hidden and visible card names are localized through the owned domain.
assert.match(source, /cards\.faceDown/);
// Verify every decision retains an unresolved action id until success.
assert.match(source, /pendingDecision = pendingDecision\?\.handId/);
// Verify an ambiguous start failure preserves both id and wallet exposure for exact retry.
assert.match(source, /pendingStart = pendingStart \|\| \{ actionId: nextActionId\(\), baseWager: normalizedWager \}/);
// Verify each decision sends the server-observed street as an optimistic precondition.
assert.match(source, /expected_phase: pendingDecision\.phase/);
// Verify wager edits update in place instead of replacing a button during blur/click dispatch.
assert.match(source, /wagerInput\.oninput = \(\) => cacheWager/);
// Reject the earlier blur-driven whole-surface rerender pattern.
assert.doesNotMatch(source, /wagerInput\.onchange/);
// Preserve the shell's single main landmark by keeping the game stage a section.
assert.doesNotMatch(source, /<main class="thpt-stage/);
// Verify raw game-owned timers cannot survive route unmount.
assert.doesNotMatch(source, /setTimeout\(|setInterval\(|requestAnimationFrame\(/);
// Verify API errors are mapped to localized copy instead of raw server prose.
assert.doesNotMatch(source, /toast\(error\.message\)/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify unmount releases locale subscriptions and cached route state.
assert.match(source, /if \(unsubscribeLocale\) unsubscribeLocale\(\)/);
// Verify visible control and ARIA probes exist in both locales.
for (const key of ['title', 'controls.startHand', 'controls.call', 'controls.fold', 'stage.tableLabel', 'cards.faceDown', 'result.payout']) {
  // Require canonical English copy for the probed key.
  assert.equal(typeof english[key], 'string');
  // Require paired Russian copy for the probed key.
  assert.equal(typeof russian[key], 'string');
}

// Report one concise success line for worker validation logs.
console.log("Texas Hold'em Practice Table frontend tests passed.");
