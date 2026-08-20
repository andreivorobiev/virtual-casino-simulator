// Statically verify the issue #1019 Color Wheel lifecycle slice and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'color_wheel.js'), 'utf8');
// Read the formatted route stylesheet as UTF-8 text.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'color_wheel.css'), 'utf8');
// Parse the English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'color_wheel.json'), 'utf8'));
// Retain and parse the Russian dictionary for encoding and parity evidence.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'color_wheel.json'), 'utf8');
// Parse the Russian game-owned dictionary.
const russian = JSON.parse(russianSource);
// Import the immutable segment and color catalogs after installing the browser global.
const frontend = await import('../../../web/games/color_wheel.js');

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
// Preserve the exact twenty-segment sequence and four selectable colors.
assert.deepEqual(frontend.SEGMENTS, ['red', 'black', 'red', 'black', 'green', 'red', 'black', 'red', 'black', 'gold', 'red', 'black', 'red', 'black', 'green', 'red', 'black', 'red', 'black', 'green']);
assert.deepEqual(frontend.COLORS, ['red', 'black', 'green', 'gold']);
// Verify route, locale, style, busy state, and request identity delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "requestPrefix: 'cw'", "href: '/games/color_wheel.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded game-local lifecycle, identity, translation, and opaque-style ownership.
for (const duplicate of ['let root =', 'let spinBusy =', 'localeUnsubscribe', 'function ensureStyles', 'function newRequestId', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(source.includes(duplicate), false, duplicate);
// Reject any remaining inline route stylesheet after extraction.
assert.doesNotMatch(source, /<style|createElement\(['"]style['"]\)/);
// Preserve the exact state endpoint without adding caller-owned player identity.
assert.match(source, /\/api\/v1\/games\/color-wheel\/state/);
// Preserve the one atomic spin endpoint and exact request payload fields.
assert.match(source, /\/api\/v1\/games\/color-wheel\/spins'[\s\S]*request_id:\s*lifecycle\.nextRequestId\(\),\s*color:\s*selectedColor,\s*stake/);
// Reject a caller-authored player identity at the frozen API boundary.
assert.doesNotMatch(source, /player_id\s*:/);
// Preserve the exact decorative duration and minimum forward turns.
assert.match(source, /const SPIN_MS = 3200;/);
assert.match(source, /const MIN_TURNS = 5;/);
// Preserve cumulative forward rotation rather than resetting each spin.
assert.match(source, /const base = wheelAngle - \(wheelAngle % 360\);[\s\S]*return base \+ MIN_TURNS \* 360 \+ target;/);
// Preserve committed wager rendering and authoritative wallet refresh.
assert.match(source, /renderCommittedWagerBalance[\s\S]*await refreshBalance\(\)/);
// Preserve the route, wheel, primary action, result, and repeat selectors in markup.
for (const marker of ['data-testid="color-wheel"', 'data-testid="color-wheel-disc"', 'data-testid="color-wheel-spin"', 'data-testid="color-wheel-result"', 'data-testid="color-wheel-repeat"']) assert.ok(source.includes(marker), marker);
// Require representative route, wheel, color, control, result, repeat, and responsive rules after extraction.
for (const selector of ['.color-wheel {', '.cw-wheel {', '.cw-pointer {', '.cw-bet.red {', '.cw-bet.black {', '.cw-bet.green {', '.cw-bet.gold {', '.cw-bet[aria-pressed="true"] {', '.cw-chip[aria-pressed="true"] {', '.cw-spin {', '.cw-result {', '.cw-repeat {', '@media (max-width: 900px)', '@media (max-width: 640px)']) assert.ok(stylesheet.includes(selector), selector);
// Preserve the exact animation duration and primary/repeat control heights.
assert.match(stylesheet, /\.cw-wheel\s*\{[\s\S]*?transition:\s*transform 3\.2s cubic-bezier\(\.15, \.6, \.15, 1\);/);
assert.match(stylesheet, /\.cw-spin\s*\{[\s\S]*?min-height:\s*48px;/);
assert.match(stylesheet, /\.cw-repeat\s*\{[\s\S]*?min-height:\s*46px;/);
// Preserve the exact desktop rail and narrow-screen feedback reservation.
assert.match(stylesheet, /\.color-wheel\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 1fr\) 300px;/);
assert.match(stylesheet, /@media \(max-width:\s*640px\)[\s\S]*?\.cw-panel\s*\{[\s\S]*?padding-right:\s*160px;/);
// Verify both required locales retain the shared repeat label.
assert.deepEqual([english['controls.repeat'], russian['controls.repeat']], ['Repeat bet', 'Повторить ставку']);
