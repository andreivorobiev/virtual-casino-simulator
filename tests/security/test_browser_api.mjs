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
// Send one read-only request through the same helper.
await apiModule.api('/api/v2/me');
// Require GET requests not to send an unnecessary CSRF header.
assert.equal(calls[1].init.headers['X-CSRF-Token'], undefined);
