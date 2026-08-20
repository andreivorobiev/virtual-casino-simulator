// Verify the isolated issue #83 frontend without shared catalog registration.

// Import strict assertions for deterministic failures.
import assert from 'node:assert/strict';
// Import UTF-8 file reads for production-source and locale checks.
import { readFile } from 'node:fs/promises';
// Import path helpers for a stable repository root.
import path from 'node:path';
// Import URL conversion for Windows and POSIX execution.
import { fileURLToPath } from 'node:url';

// Provide the browser global assigned by shared i18n during module import.
globalThis.window = {};

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read production source for ownership and timer assertions.
const source = await readFile(path.join(root, 'web', 'games', 'dragon_tiger.js'), 'utf8');
// Read the extracted route stylesheet for responsive and reduced-motion assertions.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'dragon_tiger.css'), 'utf8');
// Read the complete English game-owned dictionary.
const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', 'dragon_tiger.json'), 'utf8'));
// Read the complete Russian game-owned dictionary.
const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', 'dragon_tiger.json'), 'utf8'));
// Import public frontend seams after the minimal browser global exists.
const frontend = await import('../../../web/games/dragon_tiger.js');

// Extract placeholder names from one localized template.
const placeholders = value => [...String(value).matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map(match => match[1]).sort();
// Verify both locales expose exactly the same complete key set.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Verify every translation remains non-empty with matching interpolation slots.
for (const key of Object.keys(english)) {
  // Require player-facing English copy.
  assert.ok(String(english[key]).trim(), `${key} English value is empty`);
  // Require player-facing Russian copy.
  assert.ok(String(russian[key]).trim(), `${key} Russian value is empty`);
  // Require locale interpolation parity.
  assert.deepEqual(placeholders(russian[key]), placeholders(english[key]), `${key} placeholder mismatch`);
}
// Verify the catalog-facing export and lifecycle contract.
assert.equal(frontend.DragonTigerGame.id, 'dragon_tiger');
// Verify the catalog-facing mount remains callable.
assert.equal(typeof frontend.DragonTigerGame.mount, 'function');
// Verify route teardown remains callable.
assert.equal(typeof frontend.DragonTigerGame.unmount, 'function');
// Verify deterministic action-id injection.
assert.equal(frontend.createActionId(() => '00000000-0000-4000-8000-000000000083'), 'dt-00000000-0000-4000-8000-000000000083');
// Build one documented settled state for pure markup verification.
const snapshot = frontend.normalizeStatePayload({ rules: { deck_count: 8, bets: { dragon: { net_odds: 1 }, tiger: { net_odds: 1 }, tie: { net_odds: 11 } } }, state: { shoe: { cards_remaining: 402 }, recent_rounds: [] }, round: { round_id: 'round-1', bet: 'dragon', wager: 5, dragon_card: 'AS', tiger_card: '10H', winner: 'dragon', total_return: 10, net: 5 } });
// Create an injected translator that makes every resolved key observable.
const translate = (key, params = {}) => `RU:${key}${Object.values(params).length ? `:${Object.values(params).join('|')}` : ''}`;
// Render through the pure seam without loading browser resources.
const markup = frontend.viewMarkup({ snapshot, translate, selected: 'tie', wagerValue: 7, isDealing: false, pending: null });
// Verify the exact readiness selector required by the descriptor proposal.
assert.match(markup, /data-testid="dragon-tiger-table"/);
// Verify wager selection is communicated outside color.
assert.match(markup, /data-bet="tie" aria-pressed="true"/);
// Verify visible and ARIA copy use the injected locale seam.
assert.match(markup, /RU:cards\.label/);
// Verify the production nested rules shape reaches localized payout copy.
assert.match(markup, /RU:data\.rule:1\|1\|11/);
// Reject default shared-renderer English card labels.
assert.doesNotMatch(markup, /Ace of spades|Face-down playing card/);
// Verify request-bound dealing localizes hidden cards too.
const dealingMarkup = frontend.viewMarkup({ snapshot, translate, isDealing: true });
// Reject the default English hidden-card accessible name.
assert.doesNotMatch(dealingMarkup, /Face-down playing card/);
// Render the initial GET race window through the pure loading seam.
const loadingMarkup = frontend.viewMarkup({ snapshot, translate, isLoading: true });
// Keep the primary action inert until the session-bound snapshot settles.
assert.match(loadingMarkup, /data-action="deal" disabled/);
// Keep every wager target inert so no request payload can change during initial load.
assert.match(loadingMarkup, /data-bet="dragon"[^>]* disabled/);
// Keep the amount input inert during the same initial-load window.
assert.match(loadingMarkup, /id="dt-wager"[^>]* disabled/);
// Expose localized loading status and action copy instead of claiming wagers are accepted.
assert.match(loadingMarkup, /RU:phases\.loading/);
// Preserve a direct runtime guard even if a synthetic click bypasses disabled markup.
assert.match(source, /if \(initialLoading \|\| lifecycle\.isBusy\(\)\) return/);
// Render a saved exactly-once request after a simulated POST failure.
const retryMarkup = frontend.viewMarkup({ snapshot, translate, pending: { action_id: 'dt-retry', bet: 'tiger', wager: 7 } });
// Keep the retry action enabled so the same action id can reach the server again.
assert.match(retryMarkup, /data-action="deal">RU:controls\.retry/);
// Never regress the retry action into an inert button while configuration stays locked.
assert.doesNotMatch(retryMarkup, /data-action="deal" disabled/);
// Keep the stage aligned with the immutable pending payload rather than an older settled round.
assert.match(retryMarkup, /RU:stage\.selectedBet:RU:bets\.tiger/);
// Verify the shared #96 renderer and stylesheet are consumed.
assert.match(source, /import \{ renderCard \} from '\.\.\/core\/cards\.js'/);
// Require route, locale, style, busy state, and production request identity to delegate to the shared lifecycle.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', "lifecycle.nextRequestId('round')", "requestPrefix: 'dt'", "href: '/games/dragon_tiger.css'"]) assert.ok(source.includes(marker), marker);
// Reject superseded route, busy, locale, identity, and opaque-style ownership.
for (const duplicate of ['let root =', 'let dealing =', 'mountIdentity', 'unsubscribeLocale', 'function ensureGameStyles', 'const GAME_CSS', 'style.textContent', 'onLocaleChange', 'loadI18nDomain', 'function text(']) assert.equal(source.includes(duplicate), false, duplicate);
// Require exact remount ownership before any asynchronous response is adopted.
assert.match(source, /function ownsAction\(session, root\)[\s\S]*routeSession === session && lifecycle\.root\(\) === root/);
// Preserve the frozen dt-UUID seam while allocating production identities through the shared lifecycle.
assert.match(source, /uuidFactory:\s*\(\) => createActionId\(\)[\s\S]*lifecycle\.nextRequestId\('round'\)/);
// Verify the module never uses the legacy glyph-based money formatter.
assert.doesNotMatch(source, /formatMoney/);
// Verify the game owns no timer or animation-frame callback.
assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame/);
// Verify CSS explicitly collapses decorative reduced motion.
assert.match(stylesheet, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.dragon-tiger \*/);
// Preserve the exact desktop hierarchy, control targets, and responsive breakpoints after extraction.
assert.match(stylesheet, /\.dt-layout\s*\{[\s\S]*grid-template-columns:\s*minmax\(220px, \.72fr\) minmax\(520px, 2\.25fr\) minmax\(230px, \.72fr\);/);
assert.match(stylesheet, /\.dt-bet,[\s\S]*\.dt-deal\s*\{[\s\S]*min-height:\s*46px;/);
assert.match(stylesheet, /@media \(max-width: 1200px\)[\s\S]*\.dt-layout\s*\{[\s\S]*grid-template-columns:\s*1fr;/);
