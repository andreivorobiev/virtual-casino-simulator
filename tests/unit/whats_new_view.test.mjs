// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Exercise production tour lifecycle without a browser, listener, or durable identity. (TOUR-003, TEST-106)
import assert from 'node:assert/strict';
// Use the dependency-free test runner for deterministic async boundaries.
import test from 'node:test';
// Read tracked dictionaries for real localization and fallback evidence.
import { readFileSync } from 'node:fs';
// Import the implementation rather than copying presentation logic.
import { createWhatsNewController, localizedTour } from '../../web/views/whats_new.js';

// Load both governed dictionaries with existing curated release copy.
const dictionaries = Object.fromEntries(['en-US', 'ru-RU'].map(locale => [locale, JSON.parse(readFileSync(new URL(`../../web/i18n/${locale}/shell.json`, import.meta.url), 'utf8'))]));
// Build one exact capped server payload with three existing localization-key pairs.
const payload = () => ({ show: true, persisted: true, entries: ['0_9_5_86', '0_9_5_82', '0_9_5_81'].map(key => ({ title_key: `whatsNew.entry.${key}.title`, body_key: `whatsNew.entry.${key}.body` })), merged_count: 3, changelog_path: 'RELEASE_NOTES.md' });
// Represent a terms-complete account without a credential or durable identifier.
const session = { user: { role: 'player' }, terms: { required: false } };

// Model semantic DOM operations only; the hosted Browser case proves native modal behavior.
class Node {
  // Retain the exact tree, attributes, and listeners used by the controller.
  constructor(document, tag) { this.document = document; this.tag = tag; this.children = []; this.attributes = {}; this.listeners = {}; this.isConnected = false; }
  // Keep attribute strings inert.
  setAttribute(key, value) { this.attributes[key] = value; }
  // Attach children in semantic reading order.
  append(...nodes) { for (const node of nodes) { node.parent = this; node.isConnected = this.isConnected; this.children.push(node); } }
  // Record native-event callbacks for explicit delivery.
  addEventListener(name, callback) { this.listeners[name] = callback; }
  // Track top-layer visibility without claiming to simulate focus trapping.
  showModal() { this.open = true; }
  // Close only this surface.
  close() { this.open = false; }
  // Detach without changing another shell control.
  remove() { this.isConnected = false; this.parent.children = this.parent.children.filter(node => node !== this); }
  // Record the requested keyboard target.
  focus() { this.document.activeElement = this; }
}

// Create an isolated document, locale event target, and controllable transport.
function fixture(handler = async (_path, options) => options ? { dismissed: true, persisted: true } : payload()) {
  // Observe API requests without logging identities.
  const calls = [], events = {};
  // Switch only dictionary selection during locale tests.
  let locale = 'en-US';
  // Traverse the owned semantic tree for narrow selectors.
  const all = node => [node, ...node.children.flatMap(all)];
  // Allocate elements from the same document.
  const document = { createElement: tag => new Node(document, tag) };
  // Create the persistent shell root.
  document.body = new Node(document, 'body');
  // Mark it connected before controls are attached.
  document.body.isConnected = true;
  // Provide the cold-load focus fallback.
  const nav = document.createElement('button');
  // Bind the production test hook.
  nav.setAttribute('data-testid', 'nav-lobby');
  // Keep the fallback outside route-local optional UI.
  document.body.append(nav);
  // Model initial cold-load focus.
  document.activeElement = document.body;
  // Support only the selectors the production helper actually uses.
  document.querySelector = selector => all(document.body).find(node => selector === 'dialog[open]' ? node.tag === 'dialog' && node.open : selector === `[data-testid="${node.attributes['data-testid']}"]`) || null;
  // Resolve through installed resources with deliberate English fallback.
  const translate = key => dictionaries[locale]?.[key] ?? dictionaries['en-US'][key] ?? key;
  // Capture exact request arguments before invoking the test transport.
  const apiClient = (...args) => { calls.push(args); return handler(...args); };
  // Construct the real controller over isolated dependencies.
  const controller = createWhatsNewController({ apiClient, documentRef: document, windowRef: { addEventListener: (name, fn) => { events[name] = fn; } }, translate });
  // Expose assertions and locale events without copying implementation behavior.
  return { controller, calls, document, nav, events, node: id => document.querySelector(`[data-testid="${id}"]`), locale: value => { locale = value; events['casino-locale-changed'](); } };
}

// Prove real dictionaries, missing-locale fallback, and the one approved changelog destination.
test('complete merged copy resolves EN/RU and fallback without raw keys', () => {
  // Check both installed locales and a missing locale through the same fallback chain.
  for (const locale of ['en-US', 'ru-RU', 'missing']) {
    // Resolve the complete three-entry model.
    const result = localizedTour(payload(), key => dictionaries[locale]?.[key] ?? dictionaries['en-US'][key] ?? key);
    // Preserve all entries in server order.
    assert.equal(result.entries.length, 3);
    // Refuse visible resource identifiers.
    assert.ok(result.entries.every(entry => !entry.title.includes('whatsNew.') && !entry.body.includes('whatsNew.')));
    // Link only the fixed repository changelog.
    assert.equal(result.changelog, 'https://github.com/andreivorobiev/virtual-casino-simulator/blob/main/RELEASE_NOTES.md');
  }
});

// Reject disabled, malformed, partial, oversized, and unlocalized metadata.
test('invalid catalogs fail closed and unsafe paths are omitted', () => {
  // Enumerate independent contract violations.
  const invalid = [null, {}, { ...payload(), show: false }, { ...payload(), persisted: false }, { ...payload(), merged_count: 2 }, { ...payload(), entries: [] }, { ...payload(), entries: [...payload().entries, payload().entries[0]], merged_count: 4 }, { ...payload(), entries: [{ title_key: 'auth.email', body_key: 'auth.password' }], merged_count: 1 }];
  // Every violation rejects the whole tour.
  for (const candidate of invalid) assert.equal(localizedTour(candidate, key => dictionaries['en-US'][key] ?? key), null);
  // Missing translations cannot render as identifiers.
  assert.equal(localizedTour(payload(), key => key), null);
  // Excessive copy cannot produce unbounded DOM.
  assert.equal(localizedTour(payload(), () => 'x'.repeat(2001)), null);
  // An otherwise valid payload cannot supply executable navigation.
  assert.equal(localizedTour({ ...payload(), changelog_path: 'javascript:alert(1)' }, key => dictionaries['en-US'][key]).changelog, null);
});

// Confirm durable dismissal only after the server's acknowledgement.
test('saved dismissal sends an empty body and restores shell focus', async () => {
  // Open the real controller.
  const f = fixture();
  // Require one eligible dialog.
  assert.equal(await f.controller.start(session), true);
  // Start keyboard focus on explicit acknowledgement.
  assert.equal(f.document.activeElement, f.node('whats-new-dismiss'));
  // Invoke the production click handler.
  await f.node('whats-new-dismiss').onclick();
  // Send no subject, release, consent, or other caller field.
  assert.deepEqual(f.calls[1], ['/api/v2/me/whats-new/dismiss', { method: 'POST', body: {} }]);
  // Remove the acknowledged dialog.
  assert.equal(f.node('whats-new-dialog'), null);
  // Return focus to the persistent fallback.
  assert.equal(f.document.activeElement, f.nav);
});

// Keep transport failures out of player copy and permit honest local deferral.
test('failed save remains localized and Escape never retries', async () => {
  // Fail only explicit acknowledgement.
  const f = fixture(async (_path, options) => { if (options) throw new Error('private transport detail'); return payload(); });
  // Open and attempt one save.
  await f.controller.start(session);
  // Drain the exact action handler.
  await f.node('whats-new-dismiss').onclick();
  // Expose only reviewed localized failure copy.
  assert.equal(f.node('whats-new-error').textContent, dictionaries['en-US']['whatsNew.saveError']);
  // Re-enable an explicit user attempt without replaying automatically.
  assert.equal(f.node('whats-new-dismiss').disabled, false);
  // Observe the native cancel interception.
  let prevented = false;
  // Deliver Escape to the production handler.
  f.node('whats-new-dialog').listeners.cancel({ preventDefault: () => { prevented = true; } });
  // Require local closure without a second POST.
  assert.ok(prevented);
  // Leave no stale top-layer surface.
  assert.equal(f.node('whats-new-dialog'), null);
  // Exactly one read and one explicit save occurred.
  assert.equal(f.calls.length, 2);
});

// Repaint copy without replacing a keyboard user's focused control.
test('locale transition preserves dialog and focus identity', async () => {
  // Open in English.
  const f = fixture();
  // Start the current account.
  await f.controller.start(session);
  // Retain DOM identity before switching locale.
  const dialog = f.node('whats-new-dialog'), button = f.node('whats-new-dismiss');
  // Deliver the post-resource-load locale event.
  f.locale('ru-RU');
  // Preserve one modal.
  assert.equal(f.node('whats-new-dialog'), dialog);
  // Preserve the focused control.
  assert.equal(f.document.activeElement, button);
  // Use Russian copy from the actual shipped resource.
  assert.equal(button.textContent, 'Понятно');
});

// Keep keyboard focus inside the optional modal, including an outstanding save.
test('Tab wraps at visible enabled boundaries while a save retains usable focus', async () => {
  // Hold the explicit save to inspect its disabled-control state deterministically.
  let finish;
  // Keep the normal eligibility response and a separately controlled acknowledgement.
  const f = fixture((_path, options) => options ? new Promise(resolve => { finish = resolve; }) : Promise.resolve(payload()));
  // Mount the production dialog with its actual control order.
  await f.controller.start(session);
  // Deliver one keyboard boundary without reproducing the production handler.
  const tab = shiftKey => { let prevented = false; f.node('whats-new-dialog').listeners.keydown({ key: 'Tab', shiftKey, preventDefault: () => { prevented = true; } }); return prevented; };
  // Forward traversal from the final action must wrap to the keyboard-readable list.
  assert.equal(tab(false), true);
  // Retain focus inside the modal rather than the document body or browser chrome.
  assert.equal(f.document.activeElement, f.node('whats-new-entries'));
  // Reverse traversal at the first action must wrap to the enabled save.
  assert.equal(tab(true), true);
  // Confirm the exact active control before the request starts.
  assert.equal(f.document.activeElement, f.node('whats-new-dismiss'));
  // Begin one explicit save and keep it unresolved.
  const pending = f.node('whats-new-dismiss').onclick();
  // Disable the save without leaving a dead focus target.
  assert.equal(f.document.activeElement, f.node('whats-new-later'));
  // Busy-state traversal must omit the now-disabled submit button.
  assert.equal(tab(false), true);
  // Wrap directly to the still-usable first control.
  assert.equal(f.document.activeElement, f.node('whats-new-entries'));
  // Resolve the request so no asynchronous test work leaks.
  finish({ dismissed: true, persisted: true });
  // Drain its exact continuation.
  await pending;
});

// Restore keyboard focus even when a locale render replaced the original shell target.
test('local deferral resolves a fresh shell focus target after locale rerender', async () => {
  // Capture the initial cold-load navigation fallback.
  const f = fixture();
  // Open before replacing the shell's locale-owned button.
  await f.controller.start(session);
  // Remove the original fallback exactly as renderNav does during a locale change.
  f.nav.remove();
  // Create the replacement persistent navigation control.
  const replacement = f.document.createElement('button');
  // Keep the established semantic shell identity.
  replacement.setAttribute('data-testid', 'nav-lobby');
  // Attach the new live focus target.
  f.document.body.append(replacement);
  // Close locally without sending a durable acknowledgement.
  f.node('whats-new-later').onclick();
  // Restore focus to the new live control, not the detached predecessor or body.
  assert.equal(f.document.activeElement, replacement);
  // Local deferral does not add an API mutation.
  assert.equal(f.calls.length, 1);
});

// Keep anonymous, consent-gated, and disposable sessions outside durable tour APIs.
test('guest and terms gates never request eligibility', async () => {
  // Cover every disallowed session form.
  for (const subject of [null, {}, { user: {}, terms: { required: true } }, { user: { role: 'guest' } }, { user: { role: 'player', guest_analytics_id: 'disposable' } }]) {
    // Isolate calls for each principal.
    const f = fixture();
    // No dialog is eligible.
    assert.equal(await f.controller.start(subject), false);
    // No account API is contacted.
    assert.equal(f.calls.length, 0);
  }
});

// Logout invalidates unresolved eligibility without sleeping or timing assumptions.
test('late reads cannot reopen a disposed account', async () => {
  // Hold one exact transport boundary.
  let resolve;
  // Use a controllable promise instead of a timer.
  const f = fixture(() => new Promise(done => { resolve = done; }));
  // Start the pending optional read.
  const pending = f.controller.start(session);
  // Simulate session teardown.
  f.controller.dispose();
  // Return valid data only after teardown.
  resolve(payload());
  // Ignore the old generation.
  assert.equal(await pending, false);
  // Preserve the logged-out shell.
  assert.equal(f.node('whats-new-dialog'), null);
});

// A repeated click and stale save cannot affect a replacement account's dialog.
test('single-flight save cannot close a replacement generation', async () => {
  // Hold acknowledgement while allowing reads.
  let resolve;
  // Observe every single-flight request.
  const f = fixture((_path, options) => options ? new Promise(done => { resolve = done; }) : Promise.resolve(payload()));
  // Start the predecessor session.
  await f.controller.start(session);
  // Begin one save.
  const first = f.node('whats-new-dismiss').onclick();
  // A repeated click cannot submit again.
  await f.node('whats-new-dismiss').onclick();
  // Replace the session before resolving its predecessor's action.
  await f.controller.start(session);
  // Record the new owner.
  const replacement = f.node('whats-new-dialog');
  // Complete the stale acknowledgement.
  resolve({ dismissed: true, persisted: true });
  // Drain its continuation.
  await first;
  // Preserve the new modal untouched.
  assert.equal(f.node('whats-new-dialog'), replacement);
  // Require two reads and only one save.
  assert.equal(f.calls.length, 3);
});

// Optional endpoint failure or another dialog cannot block shell entry.
test('unavailable endpoint and another open dialog preserve the shell', async () => {
  // Model a compatible server missing the optional endpoint.
  const failed = fixture(async () => { throw new Error('missing optional endpoint'); });
  // Failure is not an authentication failure.
  assert.equal(await failed.controller.start(session), false);
  // Mount an unrelated dialog in a fresh shell.
  const f = fixture(), other = f.document.createElement('dialog');
  // Mark its native top-layer ownership.
  other.open = true;
  // Retain its existing attachment.
  f.document.body.append(other);
  // Defer release copy rather than covering another task.
  assert.equal(await f.controller.start(session), false);
  // Preserve the other dialog.
  assert.equal(other.open, true);
});
