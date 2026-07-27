// Statically verify the isolated issue #93 browser module without shared registration.

// Import strict assertions for deterministic failure output.
import assert from 'node:assert/strict';
// Import JSON and source reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module as UTF-8 text.
const source = await readFile(path.join(root, 'web', 'games', 'three_card_poker.js'), 'utf8');
// Read the complete English game-owned resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'three_card_poker.json'), 'utf8'));
// Read the complete Russian game-owned resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'three_card_poker.json'), 'utf8'));

// Return sorted named placeholders from one resource value.
function placeholders(value) {
  // Collect placeholder names without depending on their order in translated grammar.
  return [...String(value).matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map(match => match[1]).sort();
}

// Verify both required locales expose exactly the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every paired resource preserves placeholder names and remains nonblank.
for (const key of Object.keys(english)) {
  // Require non-empty English player-facing copy.
  assert.ok(typeof english[key] === 'string' && english[key].trim(), `English resource is blank: ${key}`);
  // Require non-empty Russian player-facing copy.
  assert.ok(typeof russian[key] === 'string' && russian[key].trim(), `Russian resource is blank: ${key}`);
  // Require interpolation parity so locale switching cannot expose braces or missing values.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), `Placeholder mismatch: ${key}`);
}

// Collect every literal resource key referenced through the game-local text helper.
const literalKeys = [...source.matchAll(/text\('([^']+)'/g)].map(match => match[1]);
// Require all literal lookups to exist in both paired domains.
for (const key of new Set(literalKeys)) {
  // Fail focused validation before a missing English key becomes visible.
  assert.ok(Object.hasOwn(english, key), `Source references missing English key: ${key}`);
  // Fail focused validation before a missing Russian key falls back to English.
  assert.ok(Object.hasOwn(russian, key), `Source references missing Russian key: ${key}`);
}

// Cover the finite dynamic rank, suit, and hand-rank resource families.
for (const key of ['ranks.2', 'ranks.3', 'ranks.4', 'ranks.5', 'ranks.6', 'ranks.7', 'ranks.8', 'ranks.9', 'ranks.10', 'ranks.J', 'ranks.Q', 'ranks.K', 'ranks.A', 'suits.clubs', 'suits.diamonds', 'suits.hearts', 'suits.spades', 'handRanks.high_card', 'handRanks.pair', 'handRanks.flush', 'handRanks.straight', 'handRanks.three_of_a_kind', 'handRanks.straight_flush']) {
  // Require every dynamic English lookup used by canonical backend cards and ranks.
  assert.ok(Object.hasOwn(english, key), `Missing dynamic English key: ${key}`);
  // Require every dynamic Russian lookup so accessible labels never fall back to English.
  assert.ok(Object.hasOwn(russian, key), `Missing dynamic Russian key: ${key}`);
}

// Verify the catalog-owned export is statically discoverable.
assert.match(source, /export const ThreeCardPokerGame\b/);
// Verify the stable module id matches the descriptor proposal.
assert.match(source, /id: 'three_card_poker'/);
// Verify the stable browser readiness selector exists in production markup.
assert.match(source, /data-testid="three-card-poker"/);
// Verify the frontend consumes the shared #96 accessible card renderer.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify the module installs the shared #96 card stylesheet rather than duplicating it.
assert.match(source, /link\.href = '\/core\/cards\.css'/);
// Verify visible and hidden card labels are replaced through locale-owned resources.
assert.match(source, /function localizedCard\b/);
// Verify face-down cards use a paired accessible label without exposing identity.
assert.match(source, /text\('cards\.faceDown'\)/);
// Verify the mounted domain exactly matches the descriptor proposal.
assert.match(source, /const DOMAIN = 'games\/three_card_poker'/);
// Verify the additive v1 API root uses the contract slug.
assert.match(source, /const API_ROOT = '\/api\/v1\/games\/three-card-poker'/);
// Verify reload-safe state is loaded for the authenticated current player.
assert.match(source, /api\(currentPlayerPath\(`\$\{API_ROOT\}\/state`\)\)/);
// Verify deal actions send the documented request id and wagers.
assert.match(source, /request_id: pendingDealRequestId, ante, pair_plus: pairPlus/);
// Verify decisions send the documented action id and Play-or-Fold value.
assert.match(source, /action_id: pendingDecisionActionId, decision/);
// Verify both browser wager inputs expose the public maximum.
assert.equal((source.match(/max="100000"/g) || []).length, 2);
// Verify programmatic wager normalization also clamps to the public maximum.
assert.match(source, /Math\.min\(parsed, 100000\)/);
// Verify unresolved deal retries retain one id until confirmation.
assert.match(source, /pendingDealRequestId = pendingDealRequestId \|\| nextActionId\('tcp-deal'\)/);
// Verify deal retry ids are replaced when the normalized wager payload changes.
assert.match(source, /if \(pendingDealContext !== context\) pendingDealRequestId = null/);
// Verify unresolved decision retries retain a separate id until confirmation.
assert.match(source, /pendingDecisionActionId = pendingDecisionActionId \|\| nextActionId\('tcp-decision'\)/);
// Verify both public actions reject late responses from an unmounted route.
assert.equal((source.match(/if \(generation !== mountGeneration \|\| !root\) return;/g) || []).length, 4);
// Verify compatibility player ids flow only through the shared session-aware adapters.
assert.match(source, /withCurrentPlayer\(\{ request_id:/);
// Verify live locale changes rerender state without remounting.
assert.match(source, /onLocaleChange\(\(\) => render\(\)\)/);
// Verify unmount releases the locale subscription.
assert.match(source, /if \(unsubscribeLocale\) unsubscribeLocale\(\)/);
// Verify unmount discards both unresolved retry lanes before route recovery.
assert.match(source, /pendingDealRequestId = null;[\s\S]*pendingDecisionActionId = null;[\s\S]*root = null;/);
// Verify this module owns no timer that could survive route teardown.
assert.doesNotMatch(source, /\b(?:setTimeout|setInterval|requestAnimationFrame)\b/);
// Verify reduced-motion behavior is included in game-owned styling.
assert.match(source, /prefers-reduced-motion:reduce/);
// Verify the currency-like shared formatter is not used for play-token copy.
assert.doesNotMatch(source, /\bformatMoney\b/);
// Verify raw backend English is never sent directly to the visible toast surface.
assert.doesNotMatch(source, /toast\(error\.message\)/);
// Verify internal round identifiers are absent from rendered stage and history copy.
assert.doesNotMatch(source, /text\('(?:stage|history)\.round'/);
// Verify every bounded history entry has explicit list-item semantics.
assert.match(source, /class="tcp-history-row" role="listitem"/);
// Verify the one-click repeat control is present in the rendered controls.
assert.match(source, /data-action="repeat"/);
// Verify the repeat control resolves its label through the owned locale domain.
assert.match(source, /text\('controls\.repeat'\)/);
// Verify the repeat bet copy exists in both required locales.
assert.equal(typeof english['controls.repeat'], 'string', 'Missing English key: controls.repeat');
// Verify the Russian repeat bet copy exists so the label never falls back to English.
assert.equal(typeof russian['controls.repeat'], 'string', 'Missing Russian key: controls.repeat');

// List representative visible and accessible resources required by the surface.
const requiredKeys = [
  // Cover title and primary decisions.
  'title', 'controls.deal', 'controls.play', 'controls.fold',
  // Cover phase and result language.
  'phases.ready', 'phases.decision', 'phases.settling', 'phases.settled', 'outcomes.complete', 'stage.inProgress', 'stage.completed',
  // Cover card and region accessibility.
  'cards.label', 'cards.faceDown', 'aria.game', 'aria.controls', 'aria.stage', 'aria.history',
  // Cover fake-token and paytable language.
  'tokens.amount', 'paytable.pairPlus', 'paytable.anteBonus',
];
// Require every probed visible or accessible key in both locales.
for (const key of requiredKeys) {
  // Verify English owns the complete resource.
  assert.equal(typeof english[key], 'string', `Missing English key: ${key}`);
  // Verify Russian owns the complete resource.
  assert.equal(typeof russian[key], 'string', `Missing Russian key: ${key}`);
}

// Probe representative English UI phrases that must not be embedded in JavaScript markup.
for (const phrase of [english['controls.deal'], english['controls.decisionHelp'], english['phases.ready'], english['cards.faceDown'], english['errors.generic']]) {
  // Require visible English to remain exclusively in the owned resource file.
  assert.equal(source.includes(phrase), false, `Hard-coded visible English leaked into source: ${phrase}`);
}
