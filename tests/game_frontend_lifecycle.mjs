// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Dependency-free shared game-lifecycle and first-adopter evidence for CORE-034 and TEST-248.
// Import strict assertions for exact lifecycle state and source contracts.
import assert from 'node:assert/strict';
// Import file reads for behavior-preserving adoption evidence.
import { readFile } from 'node:fs/promises';
// Provide the browser global expected by the canonical i18n module during Node import.
globalThis.window = {};
// Import the production lifecycle implementation after installing its browser-global seam.
const { createGameLifecycle } = await import('../web/core/game_lifecycle.js');

// Model only the external stylesheet node surface consumed by the lifecycle controller.
class FakeLink {
  // Create one detached link with exact tag and attribute storage.
  constructor() { this.tagName = 'LINK'; this.id = ''; this.rel = ''; this.href = ''; }
  // Return the literal href contract rather than an absolute browser-normalized URL.
  getAttribute(name) { return name === 'href' ? this.href : null; }
}

// Build one deterministic document that retains installed stylesheet nodes by id.
function createDocument() {
  // Retain appended nodes so duplicate installation can be rejected.
  const nodes = [];
  // Publish the exact document methods required by production code.
  return {
    // Expose nodes only for deterministic assertions.
    nodes,
    // Model the document head's append operation.
    head: { appendChild(node) { nodes.push(node); return node; } },
    // Create only the link shape used by the shared controller.
    createElement(tag) { assert.equal(tag, 'link'); return new FakeLink(); },
    // Resolve an installed node by its stable lifecycle owner id.
    getElementById(id) { return nodes.find(node => node.id === id) || null; },
  };
}

// Build deterministic i18n adapters and expose their subscription for locale events.
function createI18n() {
  // Retain exact lazy-domain initialization arguments.
  const initialized = [];
  // Retain the current locale callback without a global browser event.
  let subscriber = null;
  // Count exact subscription cleanup calls.
  let unsubscribeCount = 0;
  // Publish adapters plus bounded diagnostics.
  return {
    // Expose diagnostics to exact assertions.
    initialized,
    // Return the current cleanup count without exporting mutable storage.
    unsubscribeCount: () => unsubscribeCount,
    // Emit a locale change only when one mount owns a subscription.
    emit: () => subscriber?.(),
    // Record the exact requested domain list.
    async initI18n(options) { initialized.push(options); },
    // Own one callback and return its exact disposer.
    onLocaleChange(callback) { subscriber = callback; return () => { if (subscriber === callback) subscriber = null; unsubscribeCount += 1; }; },
    // Make domain and interpolation flow visible without loading locale files.
    t(key, params, domain) { return `${domain}|${key}|${params.count ?? ''}`; },
  };
}

// Create one deterministic lifecycle with a game-owned external stylesheet.
const documentRef = createDocument();
// Create deterministic locale adapters for mount and teardown evidence.
const i18n = createI18n();
// Count locale-triggered repaints without rendering game markup.
let renders = 0;
// Construct the production controller with stable test dependencies.
const lifecycle = createGameLifecycle({ domain: 'games/daily_draw_lab', requestPrefix: 'dd', stylesheet: { id: 'daily-draw-lab-styles', href: '/games/daily_draw_lab.css' }, documentRef, i18n, uuidFactory: () => 'uuid-718' });
// Create one shell-owned route outlet identity.
const outlet = { id: 'outlet-a' };
// Mount through exact production initialization.
assert.equal(await lifecycle.mount(outlet, () => { renders += 1; }), true);
// Prove one route, one domain, and one stylesheet are owned after mount.
assert.deepEqual([lifecycle.root(), lifecycle.isMounted(), lifecycle.isBusy(), i18n.initialized, documentRef.nodes.length], [outlet, true, false, [{ domains: ['games/daily_draw_lab'] }], 1]);
// Prove the stylesheet is external and exact rather than opaque injected text.
assert.deepEqual([documentRef.nodes[0].id, documentRef.nodes[0].rel, documentRef.nodes[0].href], ['daily-draw-lab-styles', 'stylesheet', '/games/daily_draw_lab.css']);
// Prove translation stays bound to the game domain.
assert.equal(lifecycle.tx('pay.hits', { count: 3 }), 'games/daily_draw_lab|pay.hits|3');
// Prove platform UUIDs pass through without client state or hidden prefixes.
assert.equal(lifecycle.nextRequestId(), 'uuid-718');
// Suppress locale repaint while one action owns the busy guard.
lifecycle.setBusy(true);
// Emit a locale change through the exact registered callback.
i18n.emit();
// Require the active action to retain render ownership.
assert.equal(renders, 0);
// Release the busy guard for idle locale repaint.
lifecycle.setBusy(false);
// Emit the next locale change after the action settles.
i18n.emit();
// Require one exact idle repaint.
assert.equal(renders, 1);
// Refuse a second outlet while the first route is live.
await assert.rejects(() => lifecycle.mount({ id: 'outlet-b' }, () => {}), /already mounted/);
// Tear down locale, root, and busy ownership.
lifecycle.unmount();
// Require exact cleanup without deleting the reusable stylesheet.
assert.deepEqual([lifecycle.root(), lifecycle.isMounted(), lifecycle.isBusy(), i18n.unsubscribeCount(), documentRef.nodes.length], [null, false, false, 1, 1]);
// Prove stale locale callbacks cannot repaint after teardown.
i18n.emit();
// Retain the exact prior render count.
assert.equal(renders, 1);
// Remount the same game without adding a second stylesheet.
assert.equal(await lifecycle.mount(outlet, () => { renders += 1; }), true);
// Require exact external-style reuse.
assert.equal(documentRef.nodes.length, 1);
// Release the remounted route and prove idempotent extra teardown.
lifecycle.unmount();
// Invoke duplicate teardown as a shell-safety contract.
lifecycle.unmount();
// Require only the one live remount subscription to have been removed.
assert.equal(i18n.unsubscribeCount(), 2);

// Create a controller whose platform UUID factory is unavailable.
const fallback = createGameLifecycle({ domain: 'games/daily_draw_lab', requestPrefix: 'dd', i18n: createI18n(), documentRef: createDocument(), uuidFactory: () => undefined, now: () => 12, random: () => 0.5 });
// Prove the historical game prefix, clock, and random shape remain stable.
assert.equal(fallback.nextRequestId(), 'dd-12-500000000');
// Prove optional action scoping stays bounded and explicit.
assert.equal(fallback.nextRequestId('draw'), 'dd-draw-12-500000000');
// Reject non-boolean busy substitutes.
assert.throws(() => fallback.setBusy(1), /must be boolean/);
// Reject traversal-shaped domains before DOM or locale work.
assert.throws(() => createGameLifecycle({ domain: '../games/escape' }), /domain is invalid/);
// Reject external or non-game stylesheet paths before DOM work.
assert.throws(() => createGameLifecycle({ domain: 'games/test', stylesheet: { id: 'bad-style', href: 'https://example.invalid/style.css' } }), /stylesheet is invalid/);
// Reject same-origin traversal before a browser can normalize it to an unrelated asset.
assert.throws(() => createGameLifecycle({ domain: 'games/test', stylesheet: { id: 'bad-style', href: '/games/../styles.css' } }), /stylesheet is invalid/);

// Seed one conflicting DOM owner to exercise fail-closed mount cleanup.
const conflictDocument = createDocument();
// Install a non-stylesheet node under the requested lifecycle id.
conflictDocument.nodes.push({ tagName: 'STYLE', id: 'conflict-style', rel: '', getAttribute: () => null });
// Construct one controller whose exact stylesheet ownership must fail.
const conflicted = createGameLifecycle({ domain: 'games/conflicted', stylesheet: { id: 'conflict-style', href: '/games/conflicted.css' }, i18n: createI18n(), documentRef: conflictDocument });
// Refuse the conflict without retaining the attempted route outlet.
await assert.rejects(() => conflicted.mount({ id: 'conflicted-outlet' }, () => {}), /ownership conflict/);
// Prove a failed mount releases all route and action ownership.
assert.deepEqual([conflicted.root(), conflicted.isMounted(), conflicted.isBusy()], [null, false, false]);

// Build one invalid locale adapter that cannot release its subscription.
const invalidDisposerI18n = { initI18n: async () => {}, onLocaleChange: () => null, t: key => key };
// Construct the controller before the invalid adapter attempts any route ownership.
const invalidDisposer = createGameLifecycle({ domain: 'games/invalid-disposer', i18n: invalidDisposerI18n, documentRef: createDocument() });
// Refuse a non-callable disposer rather than leaking a route-owned callback.
await assert.rejects(() => invalidDisposer.mount({ id: 'invalid-disposer-outlet' }, () => {}), /locale disposer is invalid/);
// Prove the invalid subscription result leaves the controller reusable and idle.
assert.deepEqual([invalidDisposer.root(), invalidDisposer.isMounted(), invalidDisposer.isBusy()], [null, false, false]);

// Retain one resolver to model route teardown during asynchronous locale initialization.
let finishInitialization = null;
// Count subscriptions that would indicate stale post-unmount ownership.
let raceSubscriptions = 0;
// Build delayed locale adapters for the mount-generation race.
const delayedI18n = {
  // Pause initialization until the test releases it.
  initI18n: () => new Promise(resolve => { finishInitialization = resolve; }),
  // Record any incorrectly installed stale subscription.
  onLocaleChange: () => { raceSubscriptions += 1; return () => {}; },
  // Provide the required translator without use in this race.
  t: key => key,
};
// Construct a controller without a stylesheet so only generation ownership is tested.
const raced = createGameLifecycle({ domain: 'games/raced', requestPrefix: 'race', i18n: delayedI18n, documentRef: createDocument() });
// Start one asynchronous mount without awaiting it.
const pendingMount = raced.mount({ id: 'raced-outlet' }, () => {});
// Release route ownership before locale initialization completes.
raced.unmount();
// Complete the delayed locale work after teardown.
finishInitialization();
// Require the stale mount to stop without subscribing or reclaiming the outlet.
assert.deepEqual([await pendingMount, raced.isMounted(), raceSubscriptions], [false, false, 0]);

// Read the exact first-adopter source for duplicate-helper deletion evidence.
const dailySource = await readFile(new URL('../web/games/daily_draw_lab.js', import.meta.url), 'utf8');
// Read the formatted external stylesheet for ownership and tooling visibility.
const dailyCss = await readFile(new URL('../web/games/daily_draw_lab.css', import.meta.url), 'utf8');
// Require the game to delegate every lifecycle responsibility named by issue #718.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "href: '/games/daily_draw_lab.css'"]) assert.ok(dailySource.includes(marker), marker);
// Reject the migrated root, busy, locale, style-text, request-id, and translation wrappers.
for (const duplicate of ['let root =', 'let drawBusy =', 'localeUnsubscribe', 'function ensureStyles', 'function newRequestId', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(dailySource.includes(duplicate), false, duplicate);
// Require the previously inline selectors to remain present in the formatted game CSS.
for (const selector of ['.daily {', '.dd-board {', '.dd-num.hit {', '.dd-go {', '.dd-repeat {', '@media (max-width: 900px)']) assert.ok(dailyCss.includes(selector), selector);

// Read the exact second-adopter source for per-slice duplicate-helper deletion evidence.
const faroSource = await readFile(new URL('../web/games/faro.js', import.meta.url), 'utf8');
// Read Faro's formatted external stylesheet for ownership and tooling visibility.
const faroCss = await readFile(new URL('../web/games/faro.css', import.meta.url), 'utf8');
// Require Faro to delegate every lifecycle responsibility named by issue #718.
for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', 'lifecycle.nextRequestId()', "href: '/games/faro.css'"]) assert.ok(faroSource.includes(marker), marker);
// Reject Faro's migrated root, busy, locale, style-text, request-id, and translation wrappers.
for (const duplicate of ['let root =', 'let dealBusy =', 'localeUnsubscribe', 'function ensureStyles', 'function newRequestId', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(faroSource.includes(duplicate), false, duplicate);
// Require every representative Faro selector, animation, and responsive rule to survive extraction.
for (const selector of ['.faro {', '.fr-card.dealing {', '@keyframes fr-flip {', '.fr-ranks {', '.fr-deal {', '.fr-repeat {', '@media (prefers-reduced-motion: reduce)', '@media (max-width: 900px)', '@media (max-width: 430px)']) assert.ok(faroCss.includes(selector), selector);
// Report one stable diagnostic only after every lifecycle and adoption assertion passes.
console.log('game_frontend_lifecycle=PASS');
