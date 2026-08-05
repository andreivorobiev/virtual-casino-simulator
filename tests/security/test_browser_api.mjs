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
// Replace only the relative localization import with a deterministic key-returning seam for data-URL evaluation.
const isolatedSource = source.replace("import { t } from './i18n.js';", "const t = key => key;");
// Import the source as an isolated ES module regardless of package metadata.
const apiModule = await import(`data:text/javascript;base64,${Buffer.from(isolatedSource).toString('base64')}`);
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
// Reset captured calls before exercising explicit registered logout verification.
calls.length = 0;
// Simulate a successful logout followed by an authoritative unauthenticated current-user probe.
globalThis.fetch = async (requestPath, init) => {
  // Capture the exact transport options used by logout and verification.
  calls.push({ requestPath, init });
  // Acknowledge the backend logout request with the standard empty success payload.
  if (requestPath === '/api/v2/auth/logout') return { ok: true, json: async () => ({ ok: true, data: { logged_out: true } }) };
  // Prove the follow-up current-user probe sees no usable session cookie.
  if (requestPath === '/api/v2/me') return { ok: false, status: 401, json: async () => ({ ok: false, error: { code: 'UNAUTHORIZED', message: 'Session is invalid or expired' } }) };
  // Reject any accidental extra request so the test remains exact.
  throw new Error(`Unexpected logout verification request ${requestPath}`);
};
// Require logout to resolve only after the current-user verification is unauthenticated.
await apiModule.logout();
// Require the state-changing logout request to carry the browser CSRF proof.
assert.equal(calls[0].init.headers['X-CSRF-Token'], 'browser-csrf-proof');
// Require the verification probe to read the current-user endpoint after logout.
assert.equal(calls[1].requestPath, '/api/v2/me');
// Require the verification probe to use browser-managed cookies without sending CSRF.
assert.equal(calls[1].init.credentials, 'include');
// Require the verification probe to remain a read-only request.
assert.equal(calls[1].init.method, 'GET');
// Reset captured calls before proving a surviving session fails closed.
calls.length = 0;
// Simulate a backend logout acknowledgement that leaves /api/v2/me authenticated.
globalThis.fetch = async (requestPath, init) => {
  // Capture the request so the fail-closed path can be inspected.
  calls.push({ requestPath, init });
  // Return normal logout success for the first call.
  if (requestPath === '/api/v2/auth/logout') return { ok: true, json: async () => ({ ok: true, data: { logged_out: true } }) };
  // Return a still-authenticated current-user envelope to model the refresh-resurrection bug.
  if (requestPath === '/api/v2/me') return { ok: true, status: 200, json: async () => ({ ok: true, data: { user: { email: 'demo@example.local' } } }) };
  // Reject any accidental extra request so the test remains exact.
  throw new Error(`Unexpected logout verification request ${requestPath}`);
};
// Require the helper to reject instead of letting the shell paint a false logged-out screen.
await assert.rejects(() => apiModule.logout(), error => error.code === 'LOGOUT_STILL_AUTHENTICATED');
// Require the failed verification to have performed exactly the logout call and one current-user probe.
assert.deepEqual(calls.map(call => call.requestPath), ['/api/v2/auth/logout', '/api/v2/me']);
// Collect browser shell events emitted after protected-session expiry.
const sessionExpiredEvents = [];
// Provide a test-local CustomEvent constructor so the browser-only expiry path can run in Node.
globalThis.CustomEvent = class TestCustomEvent {
  // Preserve event type and detail exactly as the app shell consumes them.
  constructor(type, init = {}) { this.type = type; this.detail = init.detail; }
};
// Publish the minimal window seam used by the real helper's session-expiry notification.
globalThis.window = { CustomEvent: globalThis.CustomEvent, dispatchEvent: event => sessionExpiredEvents.push(event) };
// Replace fetch with a stable protected-session failure envelope for the expiry assertions.
globalThis.fetch = async (requestPath, init) => {
  // Continue capturing request initializers while simulating an authoritative 401 response.
  calls.push({ requestPath, init });
  // Return the standard API envelope shape used by server-side unauthorized responses.
  return { ok: false, status: 401, json: async () => ({ ok: false, error: { code: 'UNAUTHORIZED', message: 'Session is invalid or expired' } }) };
};
// Require protected API failures to retain the code while replacing raw server prose with localized player copy.
await assert.rejects(() => apiModule.api('/api/v1/games/slots/state'), error => error.code === 'UNAUTHORIZED' && error.message === 'errors.unauthorized' && !error.message.includes('Session is invalid'));
// Let the intentionally deferred shell notification run after the caller catch path.
await new Promise(resolve => setTimeout(resolve, 0));
// Require one shell notification so stale authenticated chrome can be cleared.
assert.equal(sessionExpiredEvents.length, 1);
// Require the event type to match the app shell listener contract.
assert.equal(sessionExpiredEvents[0].type, 'casino-session-expired');
// Require the event detail to identify only the low-sensitivity route path.
assert.deepEqual(sessionExpiredEvents[0].detail, { path: '/api/v1/games/slots/state' });
// Reset captured events so public auth failures can prove they remain local.
sessionExpiredEvents.length = 0;
// Require login failures to reject with the same safe localized category and no raw server prose.
await assert.rejects(() => apiModule.login({ email: 'player@example.test', password: 'bad' }), error => error.code === 'UNAUTHORIZED' && error.message === 'errors.unauthorized');
// Let any accidental public-auth notification attempt run before asserting absence.
await new Promise(resolve => setTimeout(resolve, 0));
// Prove invalid login stays inside the login panel instead of remounting the expired-session gate.
assert.equal(sessionExpiredEvents.length, 0);
// Require guest-start failures to reject with the same safe localized category and no raw server prose.
await assert.rejects(() => apiModule.guestTrial({ accepted: true, terms_version: 'private-beta-1' }), error => error.code === 'UNAUTHORIZED' && error.message === 'errors.unauthorized');
// Let any accidental guest-auth notification attempt run before asserting absence.
await new Promise(resolve => setTimeout(resolve, 0));
// Prove guest-start rejection stays inside the guest-entry panel.
assert.equal(sessionExpiredEvents.length, 0);
// Remove the CSRF cookie to model a precached or restarted sign-in surface.
globalThis.document.cookie = '';
// Reset captured requests before exercising the one-shot recovery path.
calls.length = 0;
// Count bootstrap calls independently so later unsafe requests can prove the fast path.
let csrfBootstrapCalls = 0;
// Simulate the public bootstrap setting the browser-managed double-submit cookie.
globalThis.fetch = async (requestPath, init) => {
  // Capture both bootstrap and authoritative mutation requests in exact order.
  calls.push({ requestPath, init });
  // Reissue the host-only proof without exposing it in a response payload.
  if (requestPath === '/api/v2/auth/csrf') {
    // Record the one allowed recovery request.
    csrfBootstrapCalls += 1;
    // Model the browser applying Set-Cookie before fetch resolves.
    globalThis.document.cookie = 'casino_csrf=recovered-csrf-proof';
    // Return the public bootstrap acknowledgement without credential material.
    return { ok: true, json: async () => ({ ok: true, data: { csrf_cookie_ready: true } }) };
  }
  // Accept only the intended state-changing requests after recovery.
  if (requestPath === '/api/v2/me/tokens/add') return { ok: true, json: async () => ({ ok: true, data: { accepted: true } }) };
  // Reject accidental traffic so the recovery contract stays exact.
  throw new Error(`Unexpected CSRF recovery request ${requestPath}`);
};
// Require a missing-cookie mutation to recover before sending authoritative work.
await apiModule.post('/api/v2/me/tokens/add', { amount: 1 });
// Prove the bootstrap runs before the mutation rather than retrying after a rejection.
assert.deepEqual(calls.map(call => call.requestPath), ['/api/v2/auth/csrf', '/api/v2/me/tokens/add']);
// Require browser-managed credentials and cache bypass on the public recovery call.
assert.deepEqual(calls[0].init, { credentials: 'include', cache: 'no-store' });
// Require the recovered cookie value on the first authoritative mutation.
assert.equal(calls[1].init.headers['X-CSRF-Token'], 'recovered-csrf-proof');
// Send a second mutation while the recovered proof remains present.
await apiModule.post('/api/v2/me/tokens/add', { amount: 2 });
// Prove the existing-cookie fast path avoids a duplicate bootstrap.
assert.equal(csrfBootstrapCalls, 1);
// Require the second mutation to retain the recovered double-submit proof.
assert.equal(calls[2].init.headers['X-CSRF-Token'], 'recovered-csrf-proof');
// Remove the proof again to exercise fail-closed recovery.
globalThis.document.cookie = '';
// Reset captured calls before the unavailable-bootstrap assertion.
calls.length = 0;
// Return a successful acknowledgement without setting the required cookie.
globalThis.fetch = async (requestPath, init) => {
  // Capture the sole allowed bootstrap attempt.
  calls.push({ requestPath, init });
  // Reject any leaked mutation because recovery must stop before authoritative work.
  if (requestPath !== '/api/v2/auth/csrf') throw new Error(`Mutation escaped failed CSRF recovery: ${requestPath}`);
  // Model a proxy or policy response that fails to apply Set-Cookie.
  return { ok: true, json: async () => ({ ok: true, data: { csrf_cookie_ready: true } }) };
};
// Require the client to fail closed with the stable recovery code.
await assert.rejects(() => apiModule.post('/api/v2/me/tokens/add', { amount: 3 }), error => error.code === 'CSRF_BOOTSTRAP_UNAVAILABLE');
// Prove exactly one recovery call occurred and no mutation was dispatched.
assert.deepEqual(calls.map(call => call.requestPath), ['/api/v2/auth/csrf']);
