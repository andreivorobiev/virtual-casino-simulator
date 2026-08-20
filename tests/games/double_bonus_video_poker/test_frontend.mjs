// Statically verify the issue #1025 Double Bonus lifecycle slice and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'double_bonus_video_poker.js'), 'utf8');
// Read the formatted route stylesheet as UTF-8 text.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'double_bonus_video_poker.css'), 'utf8');
// Parse the English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'double_bonus_video_poker.json'), 'utf8'));
// Retain and parse the Russian dictionary for encoding and parity evidence.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'double_bonus_video_poker.json'), 'utf8');
// Parse the Russian game-owned dictionary.
const russian = JSON.parse(russianSource);

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
// Verify route, locale, style, busy state, and request identity delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', "lifecycle.nextRequestId('deal')", "lifecycle.nextRequestId('draw')", "requestPrefix: 'dbvp'", "href: '/games/double_bonus_video_poker.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded game-local root, busy, locale, generation, identity, translation, and opaque-style ownership.
for (const duplicate of ['let root =', 'let busy =', 'unsubscribeLocale', 'mountGeneration', 'requestCounter', 'function ensureStyles', 'function nextActionId', 'function text(', 'style.textContent', 'onLocaleChange', 'loadI18nDomain']) assert.equal(source.includes(duplicate), false, duplicate);
// Reject any remaining inline route stylesheet after extraction.
assert.doesNotMatch(source, /<style|createElement\(['"]style['"]\)/);
// Preserve the independently reused shared card stylesheet identity and public path.
assert.match(source, /const CARD_STYLE_ID = 'casino-shared-card-styles';[\s\S]*link\.href = '\/core\/cards\.css';/);
// Preserve the frozen state, deal, and round-scoped draw routes.
assert.match(source, /currentPlayerPath\(`\$\{API_ROOT\}\/state`\)/);
assert.match(source, /post\(`\$\{API_ROOT\}\/rounds`,\s*withCurrentPlayer\(\{ action_id: pendingDealId, bet \}\)\)/);
assert.match(source, /post\(`\$\{API_ROOT\}\/rounds\/\$\{encodeURIComponent\(round\.round_id\)\}\/decisions`,\s*withCurrentPlayer\(\{ action_id: pendingDrawId, hold \}\)\)/);
// Preserve unresolved deal identity reuse until one authoritative response confirms the round.
assert.match(source, /if \(!pendingDealId \|\| pendingDealBet !== bet\)[\s\S]*pendingDealId = lifecycle\.nextRequestId\('deal'\);[\s\S]*pendingDealBet = bet;/);
// Preserve unresolved draw identity reuse for the exact round and sorted hold selection.
assert.match(source, /if \(!pendingDrawId \|\| pendingDrawContext\?\.round_id !== round\.round_id[\s\S]*pendingDrawId = lifecycle\.nextRequestId\('draw'\);[\s\S]*pendingDrawContext = \{ round_id: round\.round_id, hold: holdKey \};/);
// Require asynchronous responses to prove exact remount ownership before adopting state or repainting.
assert.match(source, /function ownsAction\(session, root\)[\s\S]*routeSession === session && lifecycle\.root\(\) === root/);
assert.match(source, /const payload = await worker\(\);[\s\S]*if \(!ownsAction\(ownedSession, ownedRoot\)\) return;[\s\S]*adopter\(payload\);/);
// Preserve the eleven ordered paytable tiers, five card positions, and one-click repeat control.
assert.match(source, /const PAYTABLE_ORDER = \['royal_flush', 'straight_flush', 'four_aces', 'four_2s_4s', 'four_5s_ks', 'full_house', 'flush', 'straight', 'three_of_a_kind', 'two_pair', 'jacks_or_better'\];/);
for (const marker of ['data-testid="double-bonus-video-poker"', 'data-testid="double-bonus-video-poker-result"', 'data-testid="double-bonus-video-poker-hand"', 'data-bet', 'data-deal', 'data-action="repeat"', 'data-hold', 'data-draw']) assert.ok(source.includes(marker), marker);
// Require representative route, hand, hold, action, wager, paytable, result, repeat, and responsive rules after extraction.
for (const selector of ['.dbvp {', '.db-header {', '.db-stage {', '.db-hand {', '.db-holdbtn[aria-pressed="true"] {', '.db-actions {', '.db-btn.draw {', '.db-btn.deal {', '.db-field input {', '.db-pays {', '.db-result {', '.db-repeat {', '@media (max-width: 1200px)', '@media (max-width: 900px)']) assert.ok(stylesheet.includes(selector), selector);
// Preserve the exact desktop rail, action touch target, paytable reservation, and feedback-control width.
assert.match(stylesheet, /\.dbvp\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 1fr\) 300px;/);
assert.match(stylesheet, /\.db-btn\s*\{[\s\S]*?min-height:\s*44px;/);
assert.match(stylesheet, /@media \(max-width:\s*1200px\)[\s\S]*?\.db-card > \.db-pays[\s\S]*?width:\s*calc\(100% - 160px\);/);
assert.match(stylesheet, /body:has\(\.dbvp\) \.report-problem-fab\s*\{[\s\S]*?width:\s*144px;/);
// Preserve the exact shared repeat label in both required locales.
assert.deepEqual([english['controls.repeat'], russian['controls.repeat']], ['Repeat bet', 'Повторить ставку']);
