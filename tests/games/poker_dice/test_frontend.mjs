// Statically verify the issue #1003 Poker Dice lifecycle slice and paired locale resources.

// Import strict assertions for dependency-free deterministic failures.
import assert from 'node:assert/strict';
// Import UTF-8 source and resource reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import cross-platform path resolution for the repository root.
import path from 'node:path';
// Import URL conversion for stable Windows and POSIX execution.
import { fileURLToPath } from 'node:url';

// Provide the browser global assigned by shared i18n during module import.
globalThis.window = {};

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text.
const source = await readFile(path.join(root, 'web', 'games', 'poker_dice.js'), 'utf8');
// Read the formatted route stylesheet as UTF-8 text.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'poker_dice.css'), 'utf8');
// Parse the English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'poker_dice.json'), 'utf8'));
// Retain and parse the Russian dictionary for encoding and parity evidence.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'poker_dice.json'), 'utf8');
// Parse the Russian game-owned dictionary.
const russian = JSON.parse(russianSource);
// Import the public immutable face and paytable seams after installing the browser global.
const frontend = await import('../../../web/games/poker_dice.js');

// Extract named placeholders so both locales can be compared exactly.
function placeholders(value) {
  // Return stable sorted placeholder names without braces.
  return [...String(value).matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map(match => match[1]).sort();
}

// Verify both required locales expose exactly the same flat keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every translated key preserves placeholders and non-empty visible copy.
for (const key of Object.keys(english)) {
  // Compare interpolation names independently of natural-language word order.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), key + ' placeholder mismatch');
  // Reject blank visible or accessible copy in either required locale.
  assert.ok(String(english[key]).trim() && String(russian[key]).trim(), key + ' must be non-empty');
}
// Reject common UTF-8 mojibake markers from the Russian resource.
assert.doesNotMatch(russianSource, /Ãƒ|Ã|Ã‘|ï¿½/);
// Preserve the exact six rendered poker-rank faces.
assert.deepEqual(frontend.FACES, ['9', '10', 'J', 'Q', 'K', 'A']);
// Preserve the exact honest paytable ordering and multipliers.
assert.deepEqual(frontend.PAYTABLE, [['five_of_a_kind', 80], ['four_of_a_kind', 15], ['full_house', 5], ['straight', 4], ['three_of_a_kind', 2]]);
// Verify route, locale, style, busy state, and request identity delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "requestPrefix: 'pd'", "href: '/games/poker_dice.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded game-local lifecycle, identity, translation, and opaque-style ownership.
for (const duplicate of ['let root =', 'let rollBusy =', 'localeUnsubscribe', 'function ensureStyles', 'function newRequestId', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(source.includes(duplicate), false, duplicate);
// Preserve the exact state and settlement endpoints without adding caller-owned player identity.
assert.match(source, /\/api\/v1\/games\/poker-dice\/state/);
// Preserve the one atomic roll endpoint and request payload fields.
assert.match(source, /\/api\/v1\/games\/poker-dice\/rolls'[\s\S]*request_id:\s*lifecycle\.nextRequestId\(\),\s*stake/);
// Reject a caller-authored player identity at the frozen API boundary.
assert.doesNotMatch(source, /player_id\s*:/);
// Preserve committed wager rendering and authoritative wallet refresh.
assert.match(source, /renderCommittedWagerBalance[\s\S]*await refreshBalance\(\)/);
// Preserve the route, die, action, result, and repeat selectors in formatted CSS or markup.
for (const marker of ['data-testid="poker-dice"', 'data-testid="poker-dice-die"', 'data-testid="poker-dice-roll"', 'data-testid="poker-dice-result"', 'data-testid="poker-dice-repeat"']) assert.ok(source.includes(marker), marker);
// Require representative layout, animation, control, result, repeat, and responsive selectors after extraction.
for (const selector of ['.poker-dice {', '.pd-dice {', '.pd-die.rolling {', '@keyframes pd-tumble {', '.pd-roll {', '.pd-result {', '.pd-repeat {', '@media (prefers-reduced-motion: reduce)', '@media (max-width: 900px)']) assert.ok(stylesheet.includes(selector), selector);
// Preserve the existing primary and repeat control heights.
assert.match(stylesheet, /\.pd-roll\s*\{[\s\S]*?min-height:\s*48px;/);
// Preserve the reduced-motion suppression for the rolling dice.
assert.match(stylesheet, /prefers-reduced-motion:\s*reduce[\s\S]*?\.pd-die\.rolling\s*\{[\s\S]*?animation:\s*none;/);
// Verify both required locales retain the shared repeat label.
assert.deepEqual([english['controls.repeat'], russian['controls.repeat']], ['Repeat bet', 'Повторить ставку']);
