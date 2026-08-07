// Statically verify the isolated issue #91 browser, locale, contract, and descriptor hooks.

// Import strict assertions for deterministic focused-test failures.
import assert from 'node:assert/strict';
// Import UTF-8 file reads from the Node standard library.
import { readFile } from 'node:fs/promises';
// Import path resolution for consistent Windows and POSIX execution.
import path from 'node:path';
// Import URL conversion so this test can locate the repository root.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production browser module without executing browser-only APIs.
const source = await readFile(path.join(root, 'web', 'games', 'jacks_or_better_video_poker.js'), 'utf8');
// Read the complete canonical English game resource domain.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'jacks_or_better_video_poker.json'), 'utf8'));
// Read the paired Russian game resource domain.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'jacks_or_better_video_poker.json'), 'utf8'));
// Read the canonical descriptor promoted by the #77 shared integration lane.
const descriptor = JSON.parse(await readFile(path.join(root, 'modules', 'jacks_or_better_video_poker.json'), 'utf8'));
// Read the additive frozen-v1 contract declared by the descriptor.
const contract = await readFile(path.join(root, 'contracts', 'openapi', 'jacks_or_better_video_poker.v1.yaml'), 'utf8');

// Extract sorted placeholder names so both locales interpolate identically.
function placeholders(value) {
  // Return every unique braced placeholder in deterministic order.
  return [...new Set([...String(value).matchAll(/\{([A-Za-z0-9_]+)\}/g)].map(match => match[1]))].sort();
}

// Require exact EN/RU key parity before checking individual visible strings.
const englishKeys = Object.keys(english).sort();
// Sort the Russian keys independently so source ordering cannot hide drift.
const russianKeys = Object.keys(russian).sort();
// Reject missing or extra locale keys.
assert.deepEqual(russianKeys, englishKeys);
// Verify every paired value remains non-empty and placeholder-compatible.
for (const key of englishKeys) {
  // Require a non-empty English string for every game-owned key.
  assert.ok(typeof english[key] === 'string' && english[key].trim(), `English key is blank: ${key}`);
  // Require a non-empty Russian string for every game-owned key.
  assert.ok(typeof russian[key] === 'string' && russian[key].trim(), `Russian key is blank: ${key}`);
  // Reject interpolation drift that could expose raw placeholders in either locale.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), `Placeholder mismatch: ${key}`);
}
// Require visible Russian title and action copy to contain real Cyrillic text.
assert.match(`${russian.title} ${russian['controls.deal']} ${russian['controls.draw']}`, /[\u0400-\u04ff]/u);
// Reject accidental Cyrillic leakage into the canonical English domain.
assert.doesNotMatch(JSON.stringify(english), /[\u0400-\u04ff]/u);

// Verify the catalog-owned export is statically discoverable.
assert.match(source, /export const JacksOrBetterVideoPokerGame\b/);
// Verify the stable browser readiness selector exists in production markup.
assert.match(source, /data-testid="jacks-or-better-video-poker"/);
// Verify every import stays within shared frontend primitives instead of another game.
const imports = [...source.matchAll(/from\s+['"]([^'"]+)['"]/g)].map(match => match[1]);
// Reject game-to-game imports and any unapproved local frontend dependency.
assert.ok(imports.length > 0 && imports.every(target => target.startsWith('../core/')), `Unexpected frontend import: ${imports.join(', ')}`);
// Verify the completed #96 shared card renderer is consumed directly.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Verify card accessibility labels resolve through the paired locale domain.
assert.match(source, /function localizedCard\b/);
// Verify the localized card label replaces the primitive's default English ARIA text.
assert.ok(source.includes('renderCard(card, options).replace(/aria-label="[^"]*"/'));
// Verify the ARIA card label itself is sourced through i18n.
assert.match(source, /text\('cards\.cardLabel'/);

// Verify unresolved deal requests retain one retry key until a response succeeds.
assert.match(source, /pendingDealActionId = pendingDealActionId \|\| nextActionId\('deal'\)/);
// Verify unresolved draw requests retain an independent settlement retry key.
assert.match(source, /pendingDrawActionId = pendingDrawActionId \|\| nextActionId\('draw'\)/);
// Verify both public money actions submit the contract-owned action_id field.
assert.match(source, /action_id: pendingDealActionId/);
// Verify draw settlement submits its own action id rather than recycling the wager key.
assert.match(source, /action_id: pendingDrawActionId/);
// Verify this route owns no timer that could survive unmount or reload.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify the one-click repeat-bet control is present in production markup.
assert.match(source, /data-action="repeat"/);
// Verify both locales expose the repeat-bet control label.
assert.ok(typeof english['controls.repeat'] === 'string' && english['controls.repeat'].trim());
// Verify the paired Russian domain also owns the repeat-bet control label.
assert.ok(typeof russian['controls.repeat'] === 'string' && russian['controls.repeat'].trim());
// Verify game-owned CSS includes a responsive stacking breakpoint.
assert.match(source, /@media\(max-width:1180px\)/);
// Verify game-owned CSS explicitly removes optional motion under user preference.
assert.match(source, /@media\(prefers-reduced-motion:reduce\)/);

// Verify independent module identity and the branded compatible patch revision.
assert.equal(descriptor.module, 'jacks_or_better_video_poker');
// Require the game module to carry the settlement-interface patch revision.
assert.equal(descriptor.version, '1.1.2');
// Preserve the #77 sequencing document's reserved catalog slot.
assert.equal(descriptor.game.sort_order, 170);
// Require the canonical reloadable route derived from the game id.
assert.equal(descriptor.game.route, '/games/jacks_or_better_video_poker');
// Require the backend catalog hook to resolve the isolated registration function.
assert.equal(descriptor.game.backend.register, 'casino.games.jacks_or_better_video_poker.api:register');
// Require lazy frontend discovery to name the implemented browser export.
assert.equal(descriptor.game.frontend.export, 'JacksOrBetterVideoPokerGame');
// Require generic browser discovery to wait for the stable surface selector.
assert.equal(descriptor.game.frontend.ready_testid, 'jacks-or-better-video-poker');
// Require locale loading to use the paired game-owned domain.
assert.equal(descriptor.game.frontend.i18n_domain, 'games/jacks_or_better_video_poker');
// Require long-suite discovery to use the normalized game-specific driver path.
assert.equal(descriptor.game.tests.long_driver, 'tests.game_drivers.jacks_or_better_video_poker:play');
// Require the game-owned contract declaration without mutating compatibility metadata.
assert.deepEqual(descriptor.contracts, ['contracts/openapi/jacks_or_better_video_poker.v1.yaml']);
// Preserve the proposed prefix while leaving permanent allocation to issue #77.
assert.deepEqual(descriptor.requirements_prefixes, ['JOBVP']);

// Verify the additive contract declares every public issue #91 route.
for (const route of ['/state:', '/rounds:', '/rounds/{round_id}/holds:', '/rounds/{round_id}/draw:']) {
  // Require the complete hyphenated API root for each action.
  assert.ok(contract.includes(`/api/v1/games/jacks-or-better-video-poker${route}`), `Missing contract route: ${route}`);
}
// Verify deal requests use the shared action_id naming expected by the browser.
assert.match(contract, /required: \[action_id, coins, coin_value\]/);
// Verify the bounded five-coin configuration remains explicit in the contract.
assert.match(contract, /enum: \[1, 2, 3, 4, 5\]/);
// Verify the game contract uses the standard success and error envelope fields.
assert.match(contract, /required: \[ok, data\]/);
// Verify the standard error envelope remains available for every route.
assert.match(contract, /required: \[ok, error\]/);
