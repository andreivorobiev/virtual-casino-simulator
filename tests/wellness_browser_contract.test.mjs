// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic browser-controller contracts.
import assert from 'node:assert/strict';
// Import the built-in test runner so no browser or third-party DOM package is required.
import test from 'node:test';
// Import the production wellness controller under exact runtime semantics.
import { createWellnessController } from '../web/core/wellness.js';

// Define the complete persistent element inventory used by the production wellness controller.
const ELEMENT_IDS = ['wellness-open', 'wellness-dialog', 'wellness-form', 'wellness-eyebrow', 'wellness-title', 'wellness-copy', 'wellness-elapsed', 'wellness-enable-label', 'wellness-break-label', 'wellness-interval-label', 'wellness-interval-help', 'wellness-save', 'wellness-summary-title', 'wellness-pause', 'wellness-stop', 'wellness-dismiss', 'wellness-enabled', 'wellness-break-enabled', 'wellness-interval', 'wellness-summary', 'wellness-summary-note', 'wellness-message', 'wellness-break-suggestion'];

// Model the minimum native element behavior used by the document-lifetime dialog.
class FakeElement {
  // Create one connected focusable element owned by the supplied fake document.
  constructor(id, documentRef) {
    // Preserve the stable DOM id for assertions and event lookup.
    this.id = id;
    // Retain the owning document so focus changes are observable.
    this.ownerDocument = documentRef;
    // Store event listeners by native event name.
    this.listeners = new Map();
    // Default every element to connected and enabled.
    this.isConnected = true; this.disabled = false;
    // Initialize native form and dialog state used by the controller.
    this.checked = false; this.value = ''; this.open = false; this.hidden = false;
    // Initialize text and attribute storage without an HTML parser.
    this.textContent = ''; this.attributes = new Map(); this.children = [];
  }

  // Register one persistent listener exactly as addEventListener would.
  addEventListener(name, callback) {
    // Append the listener without replacing another controller hook.
    this.listeners.set(name, [...(this.listeners.get(name) || []), callback]);
  }

  // Dispatch one event and await any asynchronous test-visible listener work.
  async dispatch(name, detail = {}) {
    // Build the minimal cancelable event passed to form handlers.
    const event = { type: name, target: this, preventDefault() { this.defaultPrevented = true; }, ...detail };
    // Invoke listeners in registration order to match the browser event model.
    for (const callback of this.listeners.get(name) || []) await callback(event);
  }

  // Publish one text or accessibility attribute.
  setAttribute(name, value) {
    // Store string values like the real DOM attribute map.
    this.attributes.set(name, String(value));
  }

  // Move document focus to this exact connected element.
  focus() {
    // Update activeElement through the owning fake document.
    this.ownerDocument.activeElement = this;
  }

  // Open the fake native dialog and move no focus implicitly.
  showModal() {
    // Mark the element open for controller deduplication assertions.
    this.open = true;
  }

  // Close the fake native dialog and dispatch its native close event.
  close() {
    // Mark the element closed before listeners restore focus.
    this.open = false;
    // Invoke synchronous close listeners used by the production controller.
    for (const callback of this.listeners.get('close') || []) callback({ type: 'close', target: this });
  }

  // Replace summary children with freshly created text-only list items.
  replaceChildren(...children) {
    // Retain exact child order for summary assertions.
    this.children = children;
  }
}

// Model the minimum persistent document and visibility lifecycle used by the controller.
class FakeDocument {
  // Create all production wellness ids before controller construction.
  constructor() {
    // Start visible so manual and due reminders can open normally.
    this.visibilityState = 'visible';
    // Store document-level lifecycle listeners.
    this.listeners = new Map();
    // Create the persistent nodes and bind each to this document.
    this.elements = new Map(ELEMENT_IDS.map(id => [id, new FakeElement(id, this)]));
    // Default focus to the persistent topbar wellness button.
    this.activeElement = this.elements.get('wellness-open');
  }

  // Resolve one persistent element by its production id.
  getElementById(id) {
    // Return the exact fake node or null like the native DOM.
    return this.elements.get(id) || null;
  }

  // Create summary list items without adding them to the id index.
  createElement(id) {
    // Return one connected text-capable fake element.
    return new FakeElement(id, this);
  }

  // Register visibility listeners for hidden-tab delivery evidence.
  addEventListener(name, callback) {
    // Append without replacing prior listener state.
    this.listeners.set(name, [...(this.listeners.get(name) || []), callback]);
  }

  // Dispatch a document lifecycle event in registration order.
  async dispatch(name) {
    // Await each listener so asynchronous dialog work settles before assertions.
    for (const callback of this.listeners.get(name) || []) await callback({ type: name, target: this });
  }
}

// Create one map-backed sessionStorage implementation reusable across simulated reloads.
function createStorage(records = new Map()) {
  // Expose only the browser methods consumed by the controller.
  return { getItem: key => records.has(key) ? records.get(key) : null, setItem: (key, value) => records.set(key, String(value)), records };
}

// Create a complete deterministic controller harness around one server session.
function createHarness(options = {}) {
  // Create a fresh persistent document for this simulated page load.
  const documentRef = new FakeDocument();
  // Reuse supplied session storage to model same-session reload deduplication.
  const sessionStorage = options.sessionStorage || createStorage();
  // Track the mutable wall clock in milliseconds.
  const clock = { value: options.now ?? Date.parse('2026-08-13T12:00:00.000Z') };
  // Track pending timer callbacks without sleeping.
  const timers = new Map();
  // Increment deterministic timer handles.
  let nextTimer = 1;
  // Store API calls for no-retry and persistence assertions.
  const calls = [];
  // Hold the authoritative settings record returned by the fake server.
  let settings = { enabled: options.enabled ?? true, break_reminder_enabled: options.breakEnabled ?? true, reminder_interval_minutes: options.interval ?? 10, revision: 0, persisted: true };
  // Build a fake browser window with native-element identity and storage.
  const windowRef = { HTMLElement: FakeElement, sessionStorage, setTimeout: () => { throw new Error('Injected timers must be used'); }, clearTimeout: () => {} };
  // Return exact English or Russian-key-tagged copy for locale rerender assertions.
  let locale = 'en';
  // Resolve the fake API routes with production result shapes.
  const apiClient = async (path, init = {}) => {
    // Record the exact request before returning its authority result.
    calls.push({ path, init });
    // Return the plain neutral summary for its dedicated route.
    if (path.endsWith('/summary')) return { movements: 2, staked: 10, returned: 4, net: -6, since: '2026-08-13T12:00:00.000Z', play_tokens_only: true };
    // Apply an allowlisted settings mutation for save or stop requests.
    if (init.method === 'PATCH') { settings = { ...settings, ...init.body, revision: settings.revision + 1 }; return { wellness: { ...settings } }; }
    // Return a copy so client mutation cannot alter fake server authority.
    return { wellness: { ...settings } };
  };
  // Build the production controller with deterministic clock, API, and DOM seams.
  const controller = createWellnessController({ apiClient, documentRef, windowRef, translate: (key, values = {}) => `${locale}:${key}`.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? '')), formatTokens: value => `T${value}`, now: () => clock.value, setTimer: (callback, delay) => { const id = nextTimer++; timers.set(id, { callback, delay }); return id; }, clearTimer: id => timers.delete(id) });
  // Return mutable fixtures and safe helpers for each focused case.
  return { controller, documentRef, windowRef, sessionStorage, clock, timers, calls, setLocale: value => { locale = value; }, settings: () => ({ ...settings }), session: { session: { issued_at: '2026-08-13T12:00:00.000Z' } } };
}

// Let voided async event work settle without relying on real timers.
async function settle() {
  // Flush several microtask turns used by API promises and async reminder opening.
  await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
}

// Prove absolute cadence, hidden-tab deferral, and same-session reload deduplication.
test('wellness reminder uses the server session boundary exactly once across reload and visibility', async () => {
  // Start one opted-in authenticated page load.
  const first = createHarness();
  // Require the settings read and initial absolute schedule.
  assert.equal(await first.controller.start(first.session), true);
  // Require exactly one ten-minute timer from the server-owned session start.
  assert.equal([...first.timers.values()][0].delay, 600000);
  // Cross the first cadence boundary while the page is hidden.
  first.clock.value += 600000; first.documentRef.visibilityState = 'hidden';
  // Fire the exact pending timer without creating a second real clock.
  [...first.timers.values()][0].callback(); await settle();
  // Require deferred delivery and no background dialog focus theft.
  assert.equal(first.controller.snapshot().pendingVisibleReminder, true); assert.equal(first.documentRef.getElementById('wellness-dialog').open, false);
  // Return the same page to visibility and deliver the due slot once.
  first.documentRef.visibilityState = 'visible'; await first.documentRef.dispatch('visibilitychange'); await settle();
  // Require one open reminder and one recorded cadence slot.
  assert.equal(first.documentRef.getElementById('wellness-dialog').open, true); assert.equal(first.controller.snapshot().lastSlot, 1);
  // Dispose the first page without erasing session-local deduplication.
  first.controller.dispose();
  // Create a reload with the same server session, storage, and elapsed clock.
  const reloaded = createHarness({ sessionStorage: first.sessionStorage, now: first.clock.value });
  // Start the reload and require it not to reopen the already-presented slot.
  await reloaded.controller.start(reloaded.session); await settle();
  // Require a closed dialog and a future schedule rather than duplicate presentation.
  assert.equal(reloaded.documentRef.getElementById('wellness-dialog').open, false); assert.equal(reloaded.controller.snapshot().lastSlot, 1); assert.equal(reloaded.controller.snapshot().scheduled, true);
});

// Prove focus restoration, session-local pause, locale rerender, and durable stop semantics.
test('wellness controls restore focus and separate pause from durable opt-out', async () => {
  // Start one opted-in authenticated controller.
  const harness = createHarness();
  // Load server settings before exercising controls.
  await harness.controller.start(harness.session);
  // Open manually from the persistent topbar button.
  const opener = harness.documentRef.getElementById('wellness-open'); opener.focus(); await opener.dispatch('click'); await settle();
  // Require native modal presentation and heading focus.
  assert.equal(harness.documentRef.getElementById('wellness-dialog').open, true); assert.equal(harness.documentRef.activeElement.id, 'wellness-title');
  // Pause reminders without writing the durable API preference.
  await harness.documentRef.getElementById('wellness-pause').dispatch('click');
  // Require session-local pause and no PATCH call.
  assert.equal(harness.controller.snapshot().paused, true); assert.equal(harness.calls.filter(call => call.init.method === 'PATCH').length, 0);
  // Change locale and rerender without changing timing state.
  harness.setLocale('ru'); harness.controller.localize();
  // Require the persistent control to adopt the active locale and retain pause.
  assert.equal(opener.textContent, 'ru:wellness.open'); assert.equal(harness.documentRef.getElementById('wellness-eyebrow').textContent, 'ru:wellness.eyebrow'); assert.equal(harness.documentRef.getElementById('wellness-dismiss').attributes.get('aria-label'), 'ru:wellness.dismiss'); assert.equal(harness.controller.snapshot().paused, true);
  // Resume through the same control without a server write.
  await harness.documentRef.getElementById('wellness-pause').dispatch('click');
  // Require the schedule to resume for this exact session.
  assert.equal(harness.controller.snapshot().paused, false); assert.equal(harness.controller.snapshot().scheduled, true);
  // Stop reminders through one durable API update.
  await harness.documentRef.getElementById('wellness-stop').dispatch('click'); await settle();
  // Require exact opt-out authority and no remaining timer.
  assert.equal(harness.settings().enabled, false); assert.equal(harness.controller.snapshot().enabled, false); assert.equal(harness.controller.snapshot().scheduled, false); assert.equal(harness.calls.filter(call => call.init.method === 'PATCH').length, 1);
  // Close the dialog and restore the exact persistent opener.
  await harness.documentRef.getElementById('wellness-dismiss').dispatch('click');
  // Require stable keyboard focus after the native modal closes.
  assert.equal(harness.documentRef.activeElement, opener);
});

// Prove explicit settings writes, strict bounded fields, and disposal ownership.
test('wellness settings save adopts exact server state and disposal cancels all work', async () => {
  // Start from the off-by-default server record.
  const harness = createHarness({ enabled: false, breakEnabled: false, interval: 30 });
  // Load the initial authoritative settings.
  await harness.controller.start(harness.session);
  // Populate one explicit opt-in form submission.
  harness.documentRef.getElementById('wellness-enabled').checked = true; harness.documentRef.getElementById('wellness-break-enabled').checked = true; harness.documentRef.getElementById('wellness-interval').value = '45';
  // Submit through the production form listener.
  await harness.documentRef.getElementById('wellness-form').dispatch('submit');
  // Require only allowlisted fields and the exact optimistic revision.
  const patch = harness.calls.find(call => call.init.method === 'PATCH'); assert.deepEqual(patch.init.body, { enabled: true, break_reminder_enabled: true, reminder_interval_minutes: 45, revision: 0 });
  // Require exact returned settings and one active absolute timer.
  assert.deepEqual(harness.settings(), { enabled: true, break_reminder_enabled: true, reminder_interval_minutes: 45, revision: 1, persisted: true }); assert.equal(harness.controller.snapshot().scheduled, true);
  // Dispose at logout and require UI, dialog, timer, and late ownership to clear.
  harness.controller.dispose();
  // Require no authenticated control or pending work after teardown.
  assert.equal(harness.documentRef.getElementById('wellness-open').hidden, true); assert.equal(harness.documentRef.getElementById('wellness-dialog').open, false); assert.equal(harness.controller.snapshot().scheduled, false);
});

// Prove a cross-tab cadence change cannot reinterpret old slot numbers and skip future reminders.
test('wellness reload rebases slot numbering when the authoritative cadence changed', async () => {
  // Start one ten-minute cadence to persist its presentation metadata.
  const first = createHarness({ interval: 10 }); await first.controller.start(first.session); first.controller.dispose();
  // Reload thirty minutes later after another tab changed the durable cadence to forty-five minutes.
  const changed = createHarness({ interval: 45, sessionStorage: first.sessionStorage, now: first.clock.value + 1800000 }); await changed.controller.start(changed.session);
  // Require no historical ten-minute slot to open under the new cadence.
  assert.equal(changed.documentRef.getElementById('wellness-dialog').open, false); assert.equal(changed.controller.snapshot().lastSlot, 0);
  // Require the next exact forty-five-minute boundary, fifteen minutes from the current clock.
  assert.equal([...changed.timers.values()][0].delay, 900000);
});
