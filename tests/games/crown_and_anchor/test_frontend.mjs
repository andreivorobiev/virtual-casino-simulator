// Verify the isolated Crown and Anchor ES module without shared catalog registration.
// Import assertions from Node's standard library.
import assert from 'node:assert/strict';
// Import path helpers so repository-relative module paths are explicit.
import path from 'node:path';
// Import URL helpers for dynamic ES module loading.
import { pathToFileURL } from 'node:url';

// Provide a minimal document root before importing shared browser modules.
globalThis.document = { documentElement: { lang: 'en-US', dir: 'ltr' }, head: { append() {} }, querySelectorAll() { return []; }, getElementById() { return null; }, createElement() { return { id: '', textContent: '' }; } };
// Provide the browser window global used by shared i18n and motion modules.
globalThis.window = { addEventListener() {}, removeEventListener() {}, dispatchEvent() {} };
// Provide a CustomEvent constructor for shared i18n exports.
globalThis.CustomEvent = class CustomEvent { constructor(type, init) { this.type = type; this.detail = init?.detail; } };
// Provide a deterministic reduced-motion query result.
globalThis.matchMedia = () => ({ matches: true });
// Provide a minimal localStorage used by shared i18n helpers.
globalThis.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
// Provide navigator locale data for shared i18n helpers.
Object.defineProperty(globalThis, 'navigator', { value: { language: 'en-US', languages: ['en-US'], userAgent: 'node' } });
// Provide a no-network fetch fallback for optional resource loading.
globalThis.fetch = async () => ({ ok: false, json: async () => ({}) });
// Provide crypto UUID support for client action id tests.
Object.defineProperty(globalThis, 'crypto', { value: { randomUUID: () => '00000000-0000-4000-8000-000000000133' }, configurable: true });

// Resolve the production frontend module path.
const modulePath = path.resolve('web/games/crown_and_anchor.js');
// Import the isolated production browser module.
const frontend = await import(pathToFileURL(modulePath).href);

// Assert the catalog-facing export has the proposed stable id.
assert.equal(frontend.CrownAndAnchorGame.id, 'crown_and_anchor');
// Assert the catalog-facing mount remains callable.
assert.equal(typeof frontend.CrownAndAnchorGame.mount, 'function');
// Assert the catalog-facing unmount remains callable.
assert.equal(typeof frontend.CrownAndAnchorGame.unmount, 'function');
// Assert issue #97 dice primitives are used through a deterministic preview helper.
assert.equal(frontend.previewFaces('issue-133').length, 3);
// Assert retry-safe client identities receive the game prefix.
assert.equal(frontend.createClientRequestId(), 'caa-00000000-0000-4000-8000-000000000133');
// Track scheduled duration to prove the helper flows through the shared scope.
let scheduledDuration = null;
// Build a tiny timer scope exposing the shared schedule shape.
const timerScope = { schedule(callback, duration) { scheduledDuration = duration; callback(); return Object.freeze({}); } };
// Track whether the scheduled callback fired.
let settled = false;
// Schedule one reveal through the exported lifecycle helper.
frontend.scheduleDiceReveal({ timerScope, onSettled: () => { settled = true; }, duration: 0 });
// Assert the callback fired under the provided scope.
assert.equal(settled, true);
// Assert the helper passed the requested duration to the lifecycle scope.
assert.equal(scheduledDuration, 0);
// Render one deterministic route snapshot for stable theater identity assertions.
const markup = frontend.viewMarkup({ translate: key => key });
// Assert route markup contains the stable ready test id.
assert.match(markup, /data-testid="crown-and-anchor"/);
// Assert every authoritative die receives one stable geometry identity.
for (const index of [0, 1, 2]) assert.match(markup, new RegExp(`data-die="${index}"`));
// Assert every authoritative symbol panel receives one stable geometry identity.
for (const symbol of frontend.SYMBOL_IDS) assert.match(markup, new RegExp(`data-symbol="${symbol}"`));
// Report success for the Python wrapper.
console.log('Crown and Anchor frontend module tests passed.');
