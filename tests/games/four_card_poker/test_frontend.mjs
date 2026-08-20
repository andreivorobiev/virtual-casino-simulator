// Statically verify the issue #1027 Four Card Poker lifecycle slice and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'four_card_poker.js'), 'utf8');
// Read the formatted route stylesheet as UTF-8 text.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'four_card_poker.css'), 'utf8');
// Parse the English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'four_card_poker.json'), 'utf8'));
// Retain and parse the Russian dictionary for encoding and parity evidence.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'four_card_poker.json'), 'utf8');
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
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', "lifecycle.nextRequestId('deal')", "lifecycle.nextRequestId('decision')", "requestPrefix: 'fcp'", "href: '/games/four_card_poker.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded game-local root, busy, locale, generation, identity, translation, and opaque-style ownership.
for (const duplicate of ['let root =', 'let busy =', 'unsubscribeLocale', 'mountGeneration', 'requestCounter', 'function ensureStyles', 'function nextActionId', 'function text(', 'style.textContent', 'onLocaleChange', 'loadI18nDomain']) assert.equal(source.includes(duplicate), false, duplicate);
// Reject any remaining inline route stylesheet after extraction.
assert.doesNotMatch(source, /<style|createElement\(['"]style['"]\)/);
// Preserve the independently reused shared card stylesheet identity and public path.
assert.match(source, /const CARD_STYLE_ID = 'casino-shared-card-styles';[\s\S]*link\.href = '\/core\/cards\.css';/);
// Preserve the frozen state, deal, and round-scoped decision routes.
assert.match(source, /currentPlayerPath\(`\$\{API_ROOT\}\/state`\)/);
assert.match(source, /post\(`\$\{API_ROOT\}\/rounds`,\s*withCurrentPlayer\(\{ action_id: pendingDealId, ante, aces_up: acesUp \}\)\)/);
assert.match(source, /post\(`\$\{API_ROOT\}\/rounds\/\$\{encodeURIComponent\(round\.round_id\)\}\/decisions`,\s*withCurrentPlayer\(\{ action_id: pendingDecisionId, decision, multiplier \}\)\)/);
// Preserve unresolved deal identity reuse until one authoritative response confirms both wagers.
assert.match(source, /if \(!pendingDealId \|\| pendingDealContext\?\.ante !== ante \|\| pendingDealContext\?\.aces_up !== acesUp\)[\s\S]*pendingDealId = lifecycle\.nextRequestId\('deal'\);[\s\S]*pendingDealContext = \{ ante, aces_up: acesUp \};/);
// Preserve unresolved decision identity reuse for the exact round, decision, and multiplier.
assert.match(source, /if \(!pendingDecisionId \|\| pendingDecisionContext\?\.round_id !== round\.round_id[\s\S]*pendingDecisionId = lifecycle\.nextRequestId\('decision'\);[\s\S]*pendingDecisionContext = \{ round_id: round\.round_id, decision, multiplier \};/);
// Require asynchronous responses to prove exact remount ownership before adopting state or repainting.
assert.match(source, /function ownsAction\(session, root\)[\s\S]*routeSession === session && lifecycle\.root\(\) === root/);
assert.match(source, /const payload = await worker\(\);[\s\S]*if \(!ownsAction\(ownedSession, ownedRoot\)\) return;[\s\S]*adopter\(payload\);/);
// Preserve the three play multipliers, both paytable orders, and public interaction selectors.
assert.match(source, /const PLAY_MULTIPLIERS = \[1, 2, 3\];/);
assert.match(source, /const ANTE_BONUS_ORDER = \['four_of_a_kind', 'straight_flush', 'three_of_a_kind'\];/);
assert.match(source, /const ACES_UP_ORDER = \['four_of_a_kind', 'straight_flush', 'three_of_a_kind', 'flush', 'straight', 'two_pair', 'pair_of_aces'\];/);
for (const marker of ['data-testid="four-card-poker"', 'data-testid="four-card-poker-result"', 'data-ante', 'data-aces', 'data-deal', 'data-action="repeat"', 'data-fold', 'data-play']) assert.ok(source.includes(marker), marker);
// Require representative route, card, decision, wager, paytable, result, repeat, and responsive rules after extraction.
for (const selector of ['.fourcp {', '.fcp-stage {', '.fcp-heading {', '.fcp-row {', '.fcp-cards {', '.fcp-hand {', '.fcp-actions {', '.fcp-btn.play {', '.fcp-btn.fold {', '.fcp-btn.deal {', '.fcp-field input {', '.fcp-pays {', '.fcp-result {', '.fcp-repeat {', '@media (max-width: 900px)']) assert.ok(stylesheet.includes(selector), selector);
// Preserve the exact desktop rail and wager/action touch targets.
assert.match(stylesheet, /\.fourcp\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 1fr\) 300px;/);
assert.match(stylesheet, /\.fcp-btn\s*\{[\s\S]*?min-height:\s*44px;/);
assert.match(stylesheet, /\.fcp-field input\s*\{[\s\S]*?min-height:\s*44px;/);
// Preserve the exact shared repeat label in both required locales.
assert.deepEqual([english['controls.repeat'], russian['controls.repeat']], ['Repeat bet', 'Повторить ставку']);
