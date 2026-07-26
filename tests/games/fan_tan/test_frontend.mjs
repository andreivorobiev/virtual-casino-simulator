// Statically verify the isolated issue #137 frontend and paired locale resources.

// Import strict assertions for dependency-free deterministic failures.
import assert from 'node:assert/strict';
// Import UTF-8 source and resource reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import cross-platform path resolution for the repository root.
import path from 'node:path';
// Import URL conversion for stable Windows and POSIX execution.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text.
const source = await readFile(path.join(root, 'web', 'games', 'fan_tan.js'), 'utf8');
// Read the English game-owned dictionary as UTF-8 text.
const englishSource = await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'fan_tan.json'), 'utf8');
// Read the Russian game-owned dictionary as UTF-8 text.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'fan_tan.json'), 'utf8');
// Parse the English dictionary after retaining its encoding evidence.
const english = JSON.parse(englishSource);
// Parse the Russian dictionary after retaining its encoding evidence.
const russian = JSON.parse(russianSource);

// Extract named placeholders so both locales can be compared exactly.
function placeholders(value) {
  // Return stable sorted placeholder names without braces.
  return [...String(value).matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map(match => match[1]).sort();
}

// Verify both required locales expose exactly the same flat keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every translated key preserves the English placeholder contract.
for (const key of Object.keys(english)) {
  // Compare interpolation names independently of natural-language word order.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), key + ' placeholder mismatch');
  // Reject blank visible or accessible copy in either required locale.
  assert.ok(String(english[key]).trim() && String(russian[key]).trim(), key + ' must be non-empty');
}
// Reject common UTF-8 mojibake markers from the Russian resource.
assert.doesNotMatch(russianSource, /Ãƒ|Ã|Ã‘|ï¿½/);
// Verify the catalog-owned export is statically discoverable.
assert.match(source, /export const FanTanGame\b/);
// Verify the descriptor-facing game id remains stable.
assert.match(source, /id:\s*'fan_tan'/);
// Verify the browser readiness selector exists in production markup.
assert.match(source, /data-testid="fan-tan"/);
// Verify the frontend consumes no caller-owned player identity.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath|player_id/);
// Verify managed timer scope owns the reduced-motion counting path.
assert.match(source, /createMotionTimerScope/);
// Verify route teardown disposes the retained motion scope.
assert.match(source, /motionScope\?\.dispose\(\)/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify primary controls meet the minimum touch-target height.
assert.match(source, /min-height:44px/);
// Verify responsive stacking preserves control, stage, then data order.
assert.match(source, /\.fan-tan__controls\{order:1\}[\s\S]*\.fan-tan__stage\{order:2[\s\S]*\.fan-tan__data\{order:3\}/);
// Verify locale subscription and cleanup are both explicit.
assert.match(source, /localeUnsubscribe = onLocaleChange\(\(\) => render\(\)\)/);
// Verify route teardown invokes the retained locale unsubscribe callback.
assert.match(source, /localeUnsubscribe\?\.\(\)/);
// Verify the ledger-moving action refreshes the authenticated wallet.
assert.match(source, /await refreshBalance\(\)/);
// Reject direct hard-coded English action labels inside generated markup.
assert.doesNotMatch(source, />\s*(Count pile|Residue wagers|Paytable)\s*</);
// Verify the one-click repeat control is present in production markup.
assert.match(source, /data-action="repeat"/);
// Verify the repeat control renders its localized label rather than hard-coded copy.
assert.match(source, /translated\('controls\.repeat'\)/);
// Verify both required locales expose the repeat control label.
assert.ok(english['controls.repeat'] && russian['controls.repeat'], 'controls.repeat must exist in both locales');
// Verify the English repeat label matches the shared cross-game copy.
assert.equal(english['controls.repeat'], 'Repeat bet');
// Verify the Russian repeat label matches the shared cross-game copy.
assert.equal(russian['controls.repeat'], 'Повторить ставку');
