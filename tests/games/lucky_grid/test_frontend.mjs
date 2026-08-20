// Statically verify the issue #1017 Lucky Grid lifecycle slice and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'lucky_grid.js'), 'utf8');
// Read the formatted route stylesheet as UTF-8 text.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'lucky_grid.css'), 'utf8');
// Parse the English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'lucky_grid.json'), 'utf8'));
// Retain and parse the Russian dictionary for encoding and parity evidence.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'lucky_grid.json'), 'utf8');
// Parse the Russian game-owned dictionary.
const russian = JSON.parse(russianSource);
// Import the immutable board constants after installing the browser global.
const frontend = await import('../../../web/games/lucky_grid.js');

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
// Preserve the exact nine-cell board and three-pick requirement.
assert.deepEqual([frontend.CELLS, frontend.PICKS], [9, 3]);
// Verify route, locale, style, busy state, and request identity delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "requestPrefix: 'lg'", "href: '/games/lucky_grid.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded game-local lifecycle, identity, translation, and opaque-style ownership.
for (const duplicate of ['let root =', 'let revealBusy =', 'localeUnsubscribe', 'function ensureStyles', 'function newRequestId', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(source.includes(duplicate), false, duplicate);
// Reject any remaining inline route stylesheet after extraction.
assert.doesNotMatch(source, /<style|createElement\(['"]style['"]\)/);
// Preserve the exact state endpoint without adding caller-owned player identity.
assert.match(source, /\/api\/v1\/games\/lucky-grid\/state/);
// Preserve the one atomic reveal endpoint and exact request payload fields.
assert.match(source, /\/api\/v1\/games\/lucky-grid\/reveals'[\s\S]*request_id:\s*lifecycle\.nextRequestId\(\),\s*picks:\s*\[\.\.\.picks\],\s*stake/);
// Reject a caller-authored player identity at the frozen API boundary.
assert.doesNotMatch(source, /player_id\s*:/);
// Preserve the exact decorative reveal duration.
assert.match(source, /const REVEAL_MS = 600;/);
// Preserve committed wager rendering and authoritative wallet refresh.
assert.match(source, /renderCommittedWagerBalance[\s\S]*await refreshBalance\(\)/);
// Preserve the route, board, primary action, result, and repeat selectors in markup.
for (const marker of ['data-testid="lucky-grid"', 'data-testid="lucky-grid-board"', 'data-testid="lucky-grid-go"', 'data-testid="lucky-grid-result"', 'data-testid="lucky-grid-repeat"']) assert.ok(source.includes(marker), marker);
// Require representative route, grid, cell state, controls, result, repeat, and responsive rules after extraction.
for (const selector of ['.lucky {', '.lg-grid {', '.lg-cell[aria-pressed="true"] {', '.lg-cell.prize {', '.lg-cell.matched {', '.lg-chip[aria-pressed="true"] {', '.lg-go {', '.lg-result {', '.lg-repeat {', '@media (max-width: 900px)']) assert.ok(stylesheet.includes(selector), selector);
// Preserve the established primary and repeat control heights.
assert.match(stylesheet, /\.lg-go\s*\{[\s\S]*?min-height:\s*48px;/);
assert.match(stylesheet, /\.lg-repeat\s*\{[\s\S]*?min-height:\s*46px;/);
// Preserve the exact three-column board and responsive single-column route.
assert.match(stylesheet, /\.lg-grid\s*\{[\s\S]*?grid-template-columns:\s*repeat\(3, 1fr\);/);
assert.match(stylesheet, /@media \(max-width:\s*900px\)[\s\S]*?\.lucky\s*\{[\s\S]*?grid-template-columns:\s*1fr;/);
// Verify both required locales retain the shared repeat label.
assert.deepEqual([english['controls.repeat'], russian['controls.repeat']], ['Repeat bet', 'Повторить ставку']);
