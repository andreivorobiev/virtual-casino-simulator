// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Prove duplicate connectivity events share the real authoritative reconnect operation. (PWA-002, TEST-095)
import assert from 'node:assert/strict';
// Run without a browser, network, timers, or production data.
import test from 'node:test';

// Hold only the semantic DOM state read by the actual PWA controller.
const banner = { dataset: {}, replaceChildren() {} };
// Track one representative server-owned control through failure and success.
const control = { disabled: false, dataset: {}, setAttribute() {}, removeAttribute() {} };
// Track the optional tour's durable action separately from local Not now/Escape behavior.
const dismiss = { disabled: false, dataset: {}, setAttribute() {}, removeAttribute() {} };
// Retain only event names and handlers, never browser identity or payloads.
const listeners = new Map();
// Provide an explicitly online browser shape without Node's read-only navigator property.
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { onLine: true } });
// Supply the minimum event constructor used by production connectivity publication.
globalThis.CustomEvent = class { constructor(type, options) { this.type = type; this.detail = options.detail; } };
// Keep steady-state timers inert so the tests assert the exact terminal state immediately.
globalThis.window = { addEventListener: (name, callback) => listeners.set(name, callback), dispatchEvent() {}, setTimeout: () => 1 };
// Supply only the document surfaces the actual PWA implementation consumes.
globalThis.document = {
  body: { setAttribute() {} }, documentElement: { dataset: {} }, getElementById: () => banner,
  querySelectorAll: selector => {
    // Return only controls actually tagged by the production boundary during restoration.
    if (selector.startsWith('[data-pwa-offline-disabled')) return [control, dismiss].filter(item => item.dataset.pwaOfflineDisabled);
    // The durable tour action participates only when the exact selector is present in production.
    return selector.includes('[data-testid="whats-new-dismiss"]') ? [control, dismiss] : [control];
  }
};
// Keep warm-start bookkeeping inside a disposable in-memory seam.
globalThis.sessionStorage = { getItem: () => null, setItem() {} };
// Import the production implementation after installing browser-shaped dependencies.
const pwa = await import('../../web/core/pwa.js');

// Verify exact promise and callback ownership across redundant online notifications.
test('concurrent reconnect callers share one restore and keep controls disabled', async () => {
  // Count real callback invocations and control their completion without timers.
  let calls = 0, finish;
  // Register one pending authoritative operation with the actual controller.
  pwa.initPwa({ onReconnect: () => { calls += 1; return new Promise(resolve => { finish = resolve; }); } });
  // Begin the same operation twice before either caller can complete.
  const first = pwa.reconnectAuthoritatively(), second = pwa.reconnectAuthoritatively();
  // Require shared result identity rather than merely equivalent eventual output.
  assert.equal(first, second);
  // Enter the registered callback at the controlled microtask boundary.
  await Promise.resolve();
  // Never allow a second overlapping session or game mount.
  assert.equal(calls, 1);
  // Keep server-required actions unavailable before authority completes.
  assert.equal(control.disabled, true);
  // Govern the optional tour's POST by the same server-action boundary.
  assert.equal(dismiss.disabled, true);
  // Simulate an additional native online notification during the same operation.
  listeners.get('online')();
  // Still own exactly one backend refresh.
  assert.equal(calls, 1);
  // Complete with the actual route-restoration protocol.
  finish({ status: 'route-restored' });
  // Both callers observe the same authoritative terminal result.
  assert.deepEqual(await first, { status: 'route-restored' });
  // Release only the PWA-owned disable after success.
  assert.equal(control.disabled, false);
  // Release Got it only with the same authoritative success.
  assert.equal(dismiss.disabled, false);
  // Preserve route-restored rather than overwriting it with a competing online result.
  assert.equal(banner.dataset.state, 'route-restored');
});

// Preserve fail-closed failure while permitting a later explicit reconnect, without automatic replay.
test('failure releases single-flight ownership but never retries automatically', async () => {
  // Count both the failed and the later explicitly requested callbacks.
  let calls = 0;
  // Supply a failure through the real authoritative callback seam.
  pwa.initPwa({ onReconnect: async () => { calls += 1; throw new Error('fixture offline'); } });
  // Failure is returned through the existing bounded status protocol.
  assert.deepEqual(await pwa.reconnectAuthoritatively(), { status: 'reconnect-failed' });
  // Keep server-required controls blocked after failure.
  assert.equal(control.disabled, true);
  // Keep the tour acknowledgement unavailable after failed authority.
  assert.equal(dismiss.disabled, true);
  // No timer or hidden replay can call the handler again.
  assert.equal(calls, 1);
  // Register a succeeding authority for a new explicit connectivity attempt.
  pwa.initPwa({ onReconnect: async () => { calls += 1; return { status: 'online' }; } });
  // An explicit later call starts a new cohort after the failure settled.
  assert.deepEqual(await pwa.reconnectAuthoritatively(), { status: 'online' });
  // Require exactly one callback per explicitly completed cohort.
  assert.equal(calls, 2);
  // Restore only after that independent successful operation.
  assert.equal(control.disabled, false);
  // Restore the tour action with the independently requested successful cohort.
  assert.equal(dismiss.disabled, false);
});
