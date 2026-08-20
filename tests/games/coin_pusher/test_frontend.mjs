// Statically verify the issue #1007 Coin Pusher lifecycle slice and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'coin_pusher.js'), 'utf8');
// Read the formatted route stylesheet as UTF-8 text.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'coin_pusher.css'), 'utf8');
// Parse the English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'coin_pusher.json'), 'utf8'));
// Retain and parse the Russian dictionary for encoding and parity evidence.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'coin_pusher.json'), 'utf8');
// Parse the Russian game-owned dictionary.
const russian = JSON.parse(russianSource);
// Import the immutable payout catalog after installing the browser global.
const frontend = await import('../../../web/games/coin_pusher.js');

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
// Preserve the exact tipping threshold and cascade payout table.
assert.equal(frontend.THRESHOLD, 12);
// Preserve the exact honest coin-count ordering and multipliers.
assert.deepEqual(frontend.CASCADES, [[1, 1.5], [2, 4], [3, 6], [4, 16]]);
// Verify route, locale, style, busy state, and request identity delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "requestPrefix: 'cp'", "href: '/games/coin_pusher.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded game-local lifecycle, identity, translation, and opaque-style ownership.
for (const duplicate of ['let root =', 'let dropBusy =', 'localeUnsubscribe', 'function ensureStyles', 'function newRequestId', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(source.includes(duplicate), false, duplicate);
// Preserve the exact state endpoint without adding caller-owned player identity.
assert.match(source, /\/api\/v1\/games\/coin-pusher\/state/);
// Preserve the one atomic drop endpoint and exact request payload fields.
assert.match(source, /\/api\/v1\/games\/coin-pusher\/drops'[\s\S]*request_id:\s*lifecycle\.nextRequestId\(\),\s*stake/);
// Reject a caller-authored player identity at the frozen API boundary.
assert.doesNotMatch(source, /player_id\s*:/);
// Preserve the exact decorative cascade duration.
assert.match(source, /const DROP_MS = 700;/);
// Preserve committed wager rendering and authoritative wallet refresh.
assert.match(source, /renderCommittedWagerBalance[\s\S]*await refreshBalance\(\)/);
// Preserve the route, tray, drop, result, and repeat selectors in markup.
for (const marker of ['data-testid="coin-pusher"', 'data-testid="coin-pusher-tray"', 'data-testid="coin-pusher-drop"', 'data-testid="coin-pusher-result"', 'data-testid="coin-pusher-repeat"']) assert.ok(source.includes(marker), marker);
// Require representative route, machine, cascade, selection, control, result, repeat, and responsive rules after extraction.
for (const selector of ['.coinp {', '.cp-machine {', '.cp-coin.drop {', '@keyframes cp-fall {', '.cp-chip[aria-pressed="true"] {', '.cp-drop {', '.cp-result {', '.cp-repeat {', '@media (prefers-reduced-motion: reduce)', '@media (max-width: 900px)']) assert.ok(stylesheet.includes(selector), selector);
// Preserve the established drop and repeat control heights.
assert.match(stylesheet, /\.cp-drop\s*\{[\s\S]*?min-height:\s*48px;/);
assert.match(stylesheet, /\.cp-repeat\s*\{[\s\S]*?min-height:\s*46px;/);
// Preserve the responsive single-column transition.
assert.match(stylesheet, /@media \(max-width:\s*900px\)[\s\S]*?\.coinp\s*\{[\s\S]*?grid-template-columns:\s*1fr;/);
// Verify both required locales retain the shared repeat label.
assert.deepEqual([english['controls.repeat'], russian['controls.repeat']], ['Repeat bet', 'Повторить ставку']);
