// Exercise the real browser API helper without a listener or credential persistence.
import assert from 'node:assert/strict';
// Read the tracked helper source for data-URL module evaluation.
import { readFile } from 'node:fs/promises';
// Resolve portable repository paths from this test module.
import path from 'node:path';
// Convert the current module URL into a filesystem path.
import { fileURLToPath } from 'node:url';

// Resolve the exact checkout root.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
// Publish one host-only cookie through the browser-compatible document seam.
globalThis.document = { cookie: 'casino_csrf=browser-csrf-proof' };
// Provide browser-session storage so guest-only context proof behavior can be tested without a browser.
const sessionValues = new Map();
// Publish the minimal standards-compatible sessionStorage seam used by the real API helper.
globalThis.sessionStorage = { getItem: key => sessionValues.has(key) ? sessionValues.get(key) : null, setItem: (key, value) => sessionValues.set(key, String(value)), removeItem: key => sessionValues.delete(key) };
// Collect request initializers without making a network request.
const calls = [];
// Provide a standard successful JSON response for every helper call.
globalThis.fetch = async (requestPath, init) => { calls.push({ requestPath, init }); return { ok: true, json: async () => ({ ok: true, data: { accepted: true } }) }; };
// Read the exact tracked browser helper source.
const source = await readFile(path.join(root, 'web', 'core', 'api.js'), 'utf8');
// Import the source as an isolated ES module regardless of package metadata.
const apiModule = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
// Send one state-changing request through the real helper.
await apiModule.post('/api/v2/me/tokens/add', { amount: 1 });
// Require the browser cookie value only in the explicit CSRF header.
assert.equal(calls[0].init.headers['X-CSRF-Token'], 'browser-csrf-proof');
// Require host-only cookies to remain browser-managed.
assert.equal(calls[0].init.credentials, 'include');
// Require no bearer header or persisted credential.
assert.equal(calls[0].init.headers.Authorization, undefined);
// Require registered-session traffic to omit the guest-only browser proof.
assert.equal(calls[0].init.headers['X-Guest-Browser-Nonce'], undefined);
// Send one read-only request through the same helper.
await apiModule.api('/api/v2/me');
// Require GET requests not to send an unnecessary CSRF header.
assert.equal(calls[1].init.headers['X-CSRF-Token'], undefined);
// Require a registered read to omit the guest-only browser proof.
assert.equal(calls[1].init.headers['X-Guest-Browser-Nonce'], undefined);
// Simulate the one-time guest creation result being retained in browser-session storage only.
globalThis.sessionStorage.setItem('casino.guestBrowserNonce', 'guest-browser-proof');
// Send a later protected read through the same real helper.
await apiModule.api('/api/v2/me');
// Require only the explicit guest context proof to accompany the cookie-managed request.
assert.equal(calls[2].init.headers['X-Guest-Browser-Nonce'], 'guest-browser-proof');
// Continue forbidding bearer injection while the guest proof is active.
assert.equal(calls[2].init.headers.Authorization, undefined);
// Destroy the browser-context proof as End trial and browser closure do.
globalThis.sessionStorage.removeItem('casino.guestBrowserNonce');
// Send one final protected read after context loss.
await apiModule.api('/api/v2/me');
// Prove the helper cannot reconstruct or persist the destroyed guest proof.
assert.equal(calls[3].init.headers['X-Guest-Browser-Nonce'], undefined);
