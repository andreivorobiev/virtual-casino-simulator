// Statically verify the catalog-integrated issue #136 frontend and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'plinko.js'), 'utf8');
// Read the English game-owned dictionary as UTF-8 text.
const englishSource = await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'plinko.json'), 'utf8');
// Read the Russian game-owned dictionary as UTF-8 text.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'plinko.json'), 'utf8');
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
assert.match(source, /export const PlinkoGame\b/);
// Verify the descriptor-facing game id remains stable.
assert.match(source, /id:\s*'plinko'/);
// Verify the browser readiness selector exists in production markup.
assert.match(source, /data-testid="plinko"/);
// Verify API calls send no caller-owned player identity.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath|player_id/);
// Verify unresolved drop actions retain one identity until success.
assert.match(source, /pendingDrop = pendingDrop \|\| \{ actionId: nextActionId\(\), wager \}/);
// Verify wager blur does not replace the primary action before its click dispatches.
assert.match(source, /wagerInput\.onchange = \(\) => \{ wager = wagerValue\(wagerInput\.value\); \};/);
// Verify the one-click repeat control is rendered after the primary drop button.
assert.match(source, /data-action="drop"[\s\S]*class="plinko-repeat" data-action="repeat"/);
// Verify the repeat guard blocks busy, retry, and empty-history states.
assert.match(source, /if \(busy \|\| pendingDrop \|\| !lastBet\) return;/);
// Verify a settled drop captures the repeatable committed wager.
assert.match(source, /lastBet = \{ wager: payload\.drop\.wager \}/);
// Verify committed path replay comes from response data instead of client randomness.
assert.match(source, /data-path=/);
// Verify no browser randomness is used except action-id generation.
assert.doesNotMatch(source, /Math\.random/);
// Verify this game owns no timer or animation-frame callback.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify reduced motion makes the replay instant.
assert.match(source, /\.plinko-puck\{animation:none!important\}/);
// Verify primary controls meet the minimum touch-target height.
assert.match(source, /min-height:44px/);
// Verify responsive stacking preserves control, stage, then data order.
assert.match(source, /\.plinko-controls\{order:1\}[\s\S]*\.plinko-stage\{order:2[\s\S]*\.plinko-data\{order:3\}/);
// Verify locale subscription and cleanup are both explicit.
assert.match(source, /unsubscribeLocale = onLocaleChange\(\(\) => render\(\)\)/);
// Verify route teardown invokes the retained locale unsubscribe callback.
assert.match(source, /if \(unsubscribeLocale\) unsubscribeLocale\(\)/);
// Verify drop and mount refresh the authenticated wallet.
assert.ok((source.match(/await refreshBalance\(\)/g) || []).length >= 2);
// Reject direct hard-coded English action labels inside generated markup.
assert.doesNotMatch(source, />\s*(Drop puck|Retry drop|Wager)\s*</);
// Verify representative visible and ARIA strings exist in both locales.
for (const key of ['title', 'controls.drop', 'controls.repeat', 'controls.retryDrop', 'stage.bucketAria', 'stage.bucketsAria', 'errors.actionFailed']) {
  // Require a non-empty English value for the probed key.
  assert.ok(english[key]?.trim(), key + ' missing from English');
  // Require a non-empty Russian value for the probed key.
  assert.ok(russian[key]?.trim(), key + ' missing from Russian');
}
