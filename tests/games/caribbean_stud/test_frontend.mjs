// Statically verify the isolated issue #132 frontend and paired resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'caribbean_stud.js'), 'utf8');
// Read the English game-owned dictionary as UTF-8 text.
const englishSource = await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'caribbean_stud.json'), 'utf8');
// Read the Russian game-owned dictionary as UTF-8 text.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'caribbean_stud.json'), 'utf8');
// Parse the English dictionary after retaining encoding evidence.
const english = JSON.parse(englishSource);
// Parse the Russian dictionary after retaining encoding evidence.
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
assert.doesNotMatch(russianSource, /Ã|Ð.|Ñ.|ï¿½/);
// Verify the catalog-owned export is statically discoverable by #77 later.
assert.match(source, /export const CaribbeanStudGame\b/);
// Verify the descriptor-facing game id remains stable.
assert.match(source, /id:\s*'caribbean_stud'/);
// Verify the browser readiness selector exists in production markup.
assert.match(source, /data-testid="caribbean-stud"/);
// Verify the frontend consumes the shared #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify both visible cards and hidden dealer cards receive localized ARIA labels.
assert.match(source, /function localizedCard\b[\s\S]*cards\.faceDown[\s\S]*cards\.cardLabel/);
// Verify card groups avoid the shared primitive's English default label.
assert.match(source, /function localizedCardGroup\b/);
// Verify API calls send no caller-owned player identity.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath|player_id/);
// Verify unresolved actions retain one identity until success.
assert.match(source, /pendingAction = pendingAction \|\| \{ kind, actionId: nextActionId\(kind\), roundId: state\?\.active_round\?\.round_id, ante \}/);
// Verify the frontend uses the backend's call_wager field rather than a stale raise alias.
assert.match(source, /roundItem\?\.call_wager/);
// Verify the frontend owns no timer or animation-frame callback.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify primary controls meet the minimum touch-target height.
assert.match(source, /min-height:44px/);
// Verify responsive stacking preserves control, stage, then data order.
assert.match(source, /\.cs-controls\{order:1\}[\s\S]*\.cs-stage\{order:2[\s\S]*\.cs-data\{order:3\}/);
// Verify the module retains the last committed ante for one-click repeat.
assert.match(source, /let lastBet = null/);
// Verify the non-decision branch renders the one-click repeat control.
assert.match(source, /class="cs-repeat" data-action="repeat"/);
// Verify repeat re-applies the stored ante through the shared deal path and never replays call or fold.
assert.match(source, /async function repeat\(\)[\s\S]*runAction\(deal\)/);
// Verify the repeat control carries game-owned styling with a disabled treatment.
assert.match(source, /\.cs-repeat\{[\s\S]*\.cs-repeat:disabled\{opacity:\.5\}/);
// Verify locale subscription and cleanup are both explicit.
assert.match(source, /unsubscribeLocale = onLocaleChange\(\(\) => render\(\)\)/);
// Verify route teardown invokes the retained locale unsubscribe callback.
assert.match(source, /if \(unsubscribeLocale\) unsubscribeLocale\(\)/);
// Verify deal and call both refresh the authenticated wallet after ledger movements.
assert.ok((source.match(/await refreshBalance\(\)/g) || []).length >= 3);
// Reject direct hard-coded English action labels inside generated markup.
assert.doesNotMatch(source, />\s*(Deal|Call|Fold|Retry deal|Retry call|Retry fold)\s*</);
// Reject visible copy that frames play tokens as real-value funds.
for (const value of Object.values(english)) {
  // Scan every English resource string for forbidden money framing.
  assert.doesNotMatch(String(value), /\b(cash|deposit|withdraw|dollar|purchase)\b/i);
}
// Verify representative visible and ARIA strings exist in both locales.
for (const key of ['title', 'controls.deal', 'controls.call', 'controls.fold', 'controls.repeat', 'cards.faceDown', 'cards.cardLabel', 'handRanks.royal_flush', 'stage.cardsAria', 'errors.actionFailed']) {
  // Require a non-empty English value for the probed key.
  assert.ok(english[key]?.trim(), key + ' missing from English');
  // Require a non-empty Russian value for the probed key.
  assert.ok(russian[key]?.trim(), key + ' missing from Russian');
}
