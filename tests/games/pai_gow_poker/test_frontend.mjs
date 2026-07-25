// Statically verify the isolated issue #138 frontend and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'pai_gow_poker.js'), 'utf8');
// Read the English game-owned dictionary as UTF-8 text.
const englishSource = await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'pai_gow_poker.json'), 'utf8');
// Read the Russian game-owned dictionary as UTF-8 text.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'pai_gow_poker.json'), 'utf8');
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
assert.doesNotMatch(russianSource, /Ãƒ|Ã|Ã‘|ï¿½/);
// Verify the catalog-owned export is statically discoverable.
assert.match(source, /export const PaiGowPokerGame\b/);
// Verify the descriptor-facing game id remains stable.
assert.match(source, /id:\s*'pai_gow_poker'/);
// Verify the browser readiness selector exists in production markup.
assert.match(source, /data-testid="pai-gow-poker"/);
// Verify the frontend consumes the shared issue #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify the shared responsive card stylesheet is installed idempotently.
assert.match(source, /CARD_STYLE_ID[\s\S]*getElementById\(CARD_STYLE_ID\)[\s\S]*\/core\/cards\.css/);
// Verify both visible and hidden shared cards receive localized ARIA labels.
assert.match(source, /function localizedCard\b[\s\S]*cards\.faceDown[\s\S]*cards\.cardLabel/);
// Verify API calls send no caller-owned player identity.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath|player_id/);
// Verify unresolved deal actions retain one identity until success.
assert.match(source, /pendingDeal = pendingDeal \|\| \{ actionId: nextActionId\(\), wager \}/);
// Verify unresolved set decisions retain one identity, round, and set choice until success.
assert.match(source, /pendingDecision = pendingDecision \|\| \{ actionId: nextActionId\(\), roundId: activeRound\.round_id, set: choice \}/);
// Verify the low hand is limited to exactly two selected card positions.
assert.match(source, /lowSelection\.length < 2/);
// Verify this game owns no timer or animation-frame callback.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify primary controls meet the minimum touch-target height.
assert.match(source, /min-height:44px/);
// Verify the mobile control copy reserves the accepted fixed-feedback lane.
assert.match(source, /\.pgp-controls \.pgp-help,.pgp-controls \.pgp-error\{width:calc\(100% - 160px\)/);
// Verify the mobile problem-report affordance is bounded to the route-local lane.
assert.match(source, /body:has\(\.pgp-shell\) \.report-problem-fab\{width:144px;max-width:144px/);
// Verify responsive stacking preserves control, stage, then data order.
assert.match(source, /\.pgp-controls\{order:1\}[\s\S]*\.pgp-stage\{order:2[\s\S]*\.pgp-data\{order:3\}/);
// Verify locale subscription and cleanup are both explicit.
assert.match(source, /unsubscribeLocale = onLocaleChange\(\(\) => render\(\)\)/);
// Verify route teardown invokes the retained locale unsubscribe callback.
assert.match(source, /if \(unsubscribeLocale\) unsubscribeLocale\(\)/);
// Verify deal, decision, and mount refresh the authenticated wallet.
assert.ok((source.match(/await refreshBalance\(\)/g) || []).length >= 3);
// Reject direct hard-coded English action labels inside generated markup.
assert.doesNotMatch(source, />\s*(Deal seven cards|Set hand|Set by house way|Retry deal)\s*</);
// Verify representative visible and ARIA strings exist in both locales.
for (const key of ['title', 'controls.deal', 'controls.set', 'controls.houseWay', 'cards.faceDown', 'cards.cardLabel', 'stage.title', 'errors.actionFailed']) {
  // Require a non-empty English value for the probed key.
  assert.ok(english[key]?.trim(), key + ' missing from English');
  // Require a non-empty Russian value for the probed key.
  assert.ok(russian[key]?.trim(), key + ' missing from Russian');
}
