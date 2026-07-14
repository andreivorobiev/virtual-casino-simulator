// Statically verify the isolated issue #92 browser module and paired locale resources.

// Import strict assertions for deterministic focused-test failures.
import assert from 'node:assert/strict';
// Import UTF-8 file reads from the Node.js standard library.
import { readFile } from 'node:fs/promises';
// Import path resolution so the test runs consistently on Windows and POSIX.
import path from 'node:path';
// Import URL conversion to derive the repository root without process-directory assumptions.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-owned test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production game module as source so global registration is not required.
const source = await readFile(path.join(root, 'web', 'games', 'deuces_wild_video_poker.js'), 'utf8');
// Read the complete English game-owned translation domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'deuces_wild_video_poker.json'), 'utf8'));
// Read the complete Russian game-owned translation domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'deuces_wild_video_poker.json'), 'utf8'));

// Return the unique interpolation names used by one translated string.
function placeholders(value) {
  // Collect every brace-delimited interpolation name supported by the shared i18n formatter.
  const names = [...String(value).matchAll(/\{([A-Za-z0-9_.-]+)\}/g)].map(match => match[1]);
  // Sort a de-duplicated collection so locale comparisons remain deterministic.
  return [...new Set(names)].sort();
}

// Verify the catalog-owned lazy module export remains statically discoverable.
assert.match(source, /export const DeucesWildVideoPokerGame\b/);
// Verify the stable browser readiness selector remains on the game root.
assert.match(source, /data-testid="deuces-wild-video-poker"/);
// Verify the game cannot nest another main landmark inside the shared shell outlet.
assert.doesNotMatch(source, /<main\b/);
// Verify the central game stage remains a localized named region after removing that landmark.
assert.match(source, /<section class="dwvp-stage" aria-label="\$\{safe\(stageLabel\)\}"/);
// Verify every localized lookup uses the game-owned resource domain.
assert.match(source, /const DOMAIN = 'games\/deuces_wild_video_poker'/);
// Verify mount loads the complete game-owned domain before rendering.
assert.match(source, /await loadI18nDomain\(DOMAIN\)/);
// Verify the localization wrapper forwards keys and parameters through that domain.
assert.match(source, /return t\(key, params, DOMAIN\)/);
// Verify the frontend consumes the shared #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify game-owned presentation loads the shared responsive card stylesheet.
assert.match(source, /@import url\('\/core\/cards\.css'\)/);
// Verify localized rank, suit, and wild labels replace the shared renderer's neutral ARIA label.
assert.match(source, /function localizedCard\b[\s\S]*cards\.cardLabelWild[\s\S]*renderCard\(card, options\)\.replace/);
// Verify no timer or animation-frame callback can survive route unmount.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify the game-owned stylesheet explicitly disables motion when requested.
assert.match(source, /@media\(prefers-reduced-motion:reduce\)/);
// Verify raw server or JavaScript error messages cannot leak into player-visible copy.
assert.doesNotMatch(source, /\b(?:_?error)\s*\.\s*message\b/i);
// Verify failures resolve through one localized game-owned resource key.
assert.match(source, /toast\(text\('errors\.actionFailed'\)\)/);
// Verify invalid wagers are rejected through paired copy before a deal id is allocated.
const wagerValidation = source.indexOf('!Number.isFinite(candidateWager)');
// Locate retry-id allocation after the local validation boundary.
const dealAllocation = source.indexOf("if (!pendingDealActionId) pendingDealActionId = nextActionId('deal')");
// Verify validation precedes persistent action allocation so invalid input stays editable.
assert.ok(wagerValidation >= 0 && dealAllocation > wagerValidation);
// Verify the local invalid-wager path uses game-owned copy instead of server diagnostics.
assert.match(source, /toast\(text\('errors\.invalidWager'\)\)/);

// Locate the deal request so stable retry-key lifetime can be checked in source order.
const dealRequest = source.indexOf('action_id: pendingDealActionId, wager');
// Locate the first post-request deal-key clear operation.
const dealClear = source.indexOf('pendingDealActionId = null', dealRequest);
// Verify one pending deal id is created only when an unresolved request has none.
assert.match(source, /if \(!pendingDealActionId\) pendingDealActionId = nextActionId\('deal'\)/);
// Verify the deal id is passed to the public endpoint and retained until its response succeeds.
assert.ok(dealRequest >= 0 && dealClear > dealRequest);
// Verify hold requests reuse one id for the same round and intended hold selection.
assert.match(source, /pendingHoldActionIds\.get\(retryKey\) \|\| nextActionId\('holds'\)/);
// Verify the reused hold id is sent as the required action_id payload field.
assert.match(source, /action_id: actionId, holds: desiredHolds/);
// Verify draw requests reuse one id while the same round settlement is unresolved.
assert.match(source, /pendingDrawActionIds\.get\(roundItem\.round_id\) \|\| nextActionId\('draw'\)/);
// Verify the reused draw id is sent as the required action_id payload field.
assert.match(source, /withCurrentPlayer\(\{ action_id: actionId \}\)/);

// Verify both required locales expose exactly the same translation keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every game-owned English resource has a nonblank paired Russian value and matching placeholders.
for (const [key, englishValue] of Object.entries(english)) {
  // Require strings so markup cannot receive objects or accidental null values.
  assert.equal(typeof englishValue, 'string', `English resource ${key} must be a string`);
  // Require the paired Russian value to use the same resource shape.
  assert.equal(typeof russian[key], 'string', `Russian resource ${key} must be a string`);
  // Reject blank visible or accessible English copy.
  assert.ok(englishValue.trim(), `English resource ${key} must not be blank`);
  // Reject blank visible or accessible Russian copy.
  assert.ok(russian[key].trim(), `Russian resource ${key} must not be blank`);
  // Require identical parameter names so locale changes cannot expose braces or undefined values.
  assert.deepEqual(placeholders(russian[key]), placeholders(englishValue), `Placeholder mismatch for ${key}`);
  // Reject replacement characters and common UTF-8-as-Latin-1 mojibake lead bytes.
  assert.doesNotMatch(russian[key], /[\uFFFD\u00C2\u00C3\u00D0\u00D1]/, `Russian resource ${key} contains mojibake`);
}

// Probe visible, control, result, and ARIA keys with direct lookups through localization.
for (const key of ['title', 'controls.deal', 'controls.draw', 'stage.readyTitle', 'summary.outcome', 'cards.hold', 'paytable.title']) {
  // Require a direct or dynamically prefixed lookup for every probed player-facing category.
  assert.ok(source.includes(`text('${key}'`) || source.includes(`text(\`${key}`), `Frontend must localize ${key}`);
}
// Verify the card renderer selects the owned wild-card ARIA key before localized interpolation.
assert.match(source, /rank === '2' \? 'cards\.cardLabelWild' : 'cards\.cardLabel'[\s\S]*text\(labelKey,/);
// Verify dynamic rank and suit keys are resolved through the same localization wrapper.
assert.match(source, /text\(`ranks\.\$\{rank\}`\)[\s\S]*text\(`suits\.\$\{suit\}`\)/);
// Verify dynamic outcome keys are resolved through the same localization wrapper.
assert.match(source, /text\(`outcomes\.\$\{resultOutcome\(roundItem\)\}`\)/);
