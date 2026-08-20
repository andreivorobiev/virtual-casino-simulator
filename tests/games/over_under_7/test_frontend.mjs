// Statically verify the isolated issue #135 frontend and paired locale resources.

// Import strict assertions for deterministic failures.
import assert from 'node:assert/strict';
// Import UTF-8 reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import path helpers for repository-root resolution.
import path from 'node:path';
// Import URL conversion for Windows and POSIX execution.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module.
const source = await readFile(path.join(root, 'web', 'games', 'over_under_7.js'), 'utf8');
// Read the extracted game stylesheet for responsive and reduced-motion assertions.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'over_under_7.css'), 'utf8');
// Read the English game-owned dictionary.
const englishSource = await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'over_under_7.json'), 'utf8');
// Read the Russian game-owned dictionary.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'over_under_7.json'), 'utf8');
// Parse the English dictionary.
const english = JSON.parse(englishSource);
// Parse the Russian dictionary.
const russian = JSON.parse(russianSource);

// Extract named placeholders so locale contracts can be compared.
function placeholders(value) {
  // Return sorted placeholder names without braces.
  return [...String(value).matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map(match => match[1]).sort();
}

// Verify both locales expose the same flat keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify placeholders and non-empty values for every key.
for (const key of Object.keys(english)) {
  // Compare placeholder names independent of word order.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), key + ' placeholder mismatch');
  // Reject blank copy in either required locale.
  assert.ok(String(english[key]).trim() && String(russian[key]).trim(), key + ' must be non-empty');
}
// Reject common UTF-8 mojibake markers from Russian resources.
assert.doesNotMatch(russianSource, /Ãƒ|Ã|Ã‘|ï¿½/);
// Verify the catalog-facing export is discoverable.
assert.match(source, /export const OverUnder7Game\b/);
// Verify the descriptor-facing game id remains stable.
assert.match(source, /id:\s*'over_under_7'/);
// Verify the browser readiness selector exists.
assert.match(source, /data-testid="over-under-7"/);
// Verify the #97 motion primitive is used.
assert.match(source, /import \{ createMotionTimerScope \} from '\.\.\/core\/motion\.js'/);
// Verify dice reveal scheduling goes through the motion scope.
assert.match(source, /scheduleDiceReveal[\s\S]*timerScope\.schedule/);
// Require route, locale, style, busy, and request identity to delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "requestPrefix: 'ou7'", 'uuidFactory: () => createActionId()', "href: '/games/over_under_7.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded root, busy, locale-subscription, and opaque style ownership.
for (const duplicate of ['let root =', 'let playPending =', 'localeUnsubscribe', 'function ensureStyles', 'style.textContent', 'onLocaleChange', 'initI18n', 'ROUTE_CSS']) assert.equal(source.includes(duplicate), false, duplicate);
// Require a mount-specific token and lifecycle outlet before adopting asynchronous responses.
assert.match(source, /routeSession !== session \|\| lifecycle\.root\(\) !== ownedRoot/);
// Preserve the frozen ou7-UUID seam while allocating production identities through the shared controller.
assert.match(source, /uuidFactory:\s*\(\) => createActionId\(\)[\s\S]*pendingRequestId = lifecycle\.nextRequestId\(\)/);
// Verify reduced-motion CSS remains external and route-scoped.
assert.match(stylesheet, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.over-under-7 \*/);
// Verify API calls send no caller-owned player identity.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath|player_id\s*:/);
// Verify primary controls meet minimum touch target height.
assert.match(stylesheet, /\.ou7-bet input\s*\{[\s\S]*min-height:\s*44px;/);
// Verify responsive stacking preserves control, stage, then data order.
assert.match(stylesheet, /@media \(max-width: 1200px\)[\s\S]*\.ou7-controls\s*\{[\s\S]*order:\s*1;[\s\S]*\.ou7-stage\s*\{[\s\S]*order:\s*2;[\s\S]*\.ou7-data\s*\{[\s\S]*order:\s*3;/);
// Verify route teardown disposes timers and locale subscription.
assert.match(source, /motionScope\?\.dispose\(\)[\s\S]*lifecycle\.unmount\(\)/);
// Verify wallet refresh follows successful ledger movement.
assert.match(source, /await refreshBalance\(\)/);
// Reject direct hard-coded English labels inside generated markup.
assert.doesNotMatch(source, />\s*(Roll dice|Under 7|Exactly 7|Over 7)\s*</);
// Verify the one-click repeat control is present in generated markup.
assert.match(source, /data-action="repeat"/);
// Verify the repeat label exists in both required locales.
assert.ok(english['controls.repeat']?.trim(), 'controls.repeat missing from English');
// Verify the repeat label exists in the Russian locale.
assert.ok(russian['controls.repeat']?.trim(), 'controls.repeat missing from Russian');
// Verify representative visible and ARIA strings exist in both locales.
for (const key of ['title', 'controls.title', 'action.play', 'stage.aria', 'history.empty', 'error.playFailed']) {
  // Require non-empty English value.
  assert.ok(english[key]?.trim(), key + ' missing from English');
  // Require non-empty Russian value.
  assert.ok(russian[key]?.trim(), key + ' missing from Russian');
}
