// Statically verify the isolated issue #85 frontend and paired locale resources.

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
const source = await readFile(path.join(root, 'web', 'games', 'hi_lo.js'), 'utf8');
// Read the English game-owned dictionary as UTF-8 text.
const englishSource = await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'hi_lo.json'), 'utf8');
// Read the Russian game-owned dictionary as UTF-8 text.
const russianSource = await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'hi_lo.json'), 'utf8');
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
assert.doesNotMatch(russianSource, /Ã|Ð|Ñ|�/);
// Verify the catalog-owned export is statically discoverable.
assert.match(source, /export const HiLoGame\b/);
// Verify the descriptor-facing game id remains stable.
assert.match(source, /id:\s*'hi_lo'/);
// Verify the browser readiness selector exists in production markup.
assert.match(source, /data-testid="hi-lo"/);
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
// Verify unresolved guesses retain one identity, round, and direction until success.
assert.match(source, /pendingGuess = pendingGuess \|\| \{ actionId: nextActionId\(\), roundId: activeRound\.round_id, guess \}/);
// Verify this game owns no timer or animation-frame callback.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify the one-click repeat-bet control is rendered in production markup.
assert.match(source, /data-action="repeat"/);
// Verify the repeat-bet label exists in both required locales.
assert.ok(english['controls.repeat']?.trim() && russian['controls.repeat']?.trim(), 'controls.repeat missing from a locale');
// Require the rank-price range to preserve exact two-decimal placeholders in both locales.
assert.deepEqual(placeholders(english['rules.correctReturn']), ['max', 'min']);
// Require the active-card price copy to consume exactly one authoritative server multiplier.
assert.deepEqual(placeholders(english['rules.currentReturn']), ['multiplier']);
// Require exact two-decimal formatting before any EN/RU price interpolation.
assert.match(source, /Number\(minMultiplier\)\.toFixed\(2\)[\s\S]*Number\(maxMultiplier\)\.toFixed\(2\)/);
// Require the active visible rank to select only the additive server-owned paytable.
assert.match(source, /activeRank = activeCard \? activeCard\.slice\(0, -1\)[\s\S]*activeMultiplier = paytable\[activeRank\]/);
// Require the current-rank price to render as explicit governed evidence.
assert.match(source, /data-testid="hi-lo-current-return"[\s\S]*Number\(activeMultiplier\)\.toFixed\(2\)/);
// Preserve the frozen-v1 scalar only as the pre-state compatibility fallback.
assert.match(source, /rules\.correct_return_multiplier \|\| 2/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify primary controls meet the minimum touch-target height.
assert.match(source, /min-height:44px/);
// Verify responsive stacking preserves control, stage, then data order.
assert.match(source, /\.hilo-controls\{order:1\}[\s\S]*\.hilo-stage\{order:2[\s\S]*\.hilo-data\{order:3\}/);
// Verify locale subscription and cleanup are both explicit.
assert.match(source, /unsubscribeLocale = onLocaleChange\(\(\) => render\(\)\)/);
// Verify route teardown invokes the retained locale unsubscribe callback.
assert.match(source, /if \(unsubscribeLocale\) unsubscribeLocale\(\)/);
// Verify both ledger-moving actions and mount refresh the authenticated wallet.
assert.ok((source.match(/await refreshBalance\(\)/g) || []).length >= 3);
// Reject direct hard-coded English action labels inside generated markup.
assert.doesNotMatch(source, />\s*(Deal opening card|Higher|Lower|Retry deal)\s*</);
// Verify representative visible and ARIA strings exist in both locales.
for (const key of ['title', 'controls.deal', 'controls.higher', 'controls.lower', 'cards.faceDown', 'cards.cardLabel', 'stage.cardsAria', 'errors.actionFailed']) {
  // Require a non-empty English value for the probed key.
  assert.ok(english[key]?.trim(), key + ' missing from English');
  // Require a non-empty Russian value for the probed key.
  assert.ok(russian[key]?.trim(), key + ' missing from Russian');
}
