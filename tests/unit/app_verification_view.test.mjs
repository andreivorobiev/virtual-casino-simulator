// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for pending-email verification. (AUTH-018, USER-010)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Verification view factory.
import { createVerificationView } from "../../web/views/verification.js";
// Import the browser-independent tagged-template fixture for injected view rendering.
import { html, raw } from "./html_template_fixture.mjs";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/verification.js`, "utf8");

// Verify pending mailbox handoff and bearer-owned activation survive extraction.
test("AUTH-018 preserves email verification after extraction", async () => {
  // Retain route, form, mailbox, locale, status, and action controls.
  const view = { className: "", innerHTML: "", removeAttribute: () => {}, querySelector: selector => actions.get(selector) };
  const form = {};
  const submit = { disabled: false };
  const email = { value: "" };
  const locale = { value: "en-US" };
  const status = { textContent: "" };
  const actions = new Map([
    ['[data-testid="email-verification-resend"]', {}],
    ['[data-testid="email-verification-cancel"]', {}],
  ]);
  const controls = new Map([
    ["email-verification-form", form],
    ["email-verification-submit", submit],
    ["email-verification-email", email],
    ["email-verification-locale", locale],
    ["email-verification-message", status],
  ]);
  const classes = new Set();
  // Model only document seams owned by the verification view.
  const documentRef = {
    body: {
      classList: {
        add: value => classes.add(value),
        remove: (...values) => values.forEach(value => classes.delete(value)),
      },
    },
    getElementById: id => id === "view" ? view : controls.get(id),
  };
  const storage = new Map();
  const removed = [];
  const replacements = [];
  const requests = [];
  const loginMessages = [];
  let arrival = "VERIFY-SECRET";
  // Create the production view around deterministic browser and API seams.
  const verification = createVerificationView({
    // Bind the same escape-by-default and reviewed-fragment contract as production.
    html,
    raw,
    api: async (path, options) => { requests.push({ path, options }); },
    cryptoRef: globalThis.crypto,
    documentRef,
    getLocaleState: () => ({ locale: "en-US" }),
    historyRef: { replaceState: (_state, _title, path) => replacements.push(path) },
    renderLoginGate: message => loginMessages.push(message),
    safe: value => String(value ?? ""),
    sessionStorageRef: {
      getItem: key => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => { storage.delete(key); removed.push(key); },
    },
    setSession: () => {},
    syncFeedbackReporter: () => {},
    t: key => key,
    transientRouteBearer: () => { const value = arrival; arrival = ""; return value; },
    wireLocaleSelect: select => { select.value = "en-US"; },
    windowRef: {},
  });
  // Hand off the Signup mailbox and render the bearer-owned pending state.
  verification.setPendingEnrollmentEmail(" pending@example.com ");
  verification.renderEmailVerificationGate();
  assert.equal(email.value, "pending@example.com");
  assert.deepEqual(replacements, ["/enroll/verify"]);
  assert.ok(view.innerHTML.includes('data-testid="email-verification-pending"'));
  assert.ok(view.innerHTML.includes('data-testid="email-verification-cancel"'));
  assert.ok(classes.has("auth-locked"));
  // Verify with exact transient bearer and token-free caller identity.
  await form.onsubmit({ preventDefault: () => {} });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, "/api/v2/auth/signup/verify");
  assert.equal(requests[0].options.body.token, "VERIFY-SECRET");
  assert.equal(requests[0].options.body.email, "pending@example.com");
  assert.equal(removed.length, 1);
  assert.equal(removed[0].includes("VERIFY-SECRET"), false);
  assert.deepEqual(replacements, ["/enroll/verify", "/"]);
  assert.deepEqual(loginMessages, ["signup.verified"]);
});

// Verify the shell owns composition while the view owns transient verification state.
test("USER-010 keeps the Verification view boundary reviewable", () => {
  // Require one import and reject retired state and implementations.
  assert.equal((APP_SOURCE.match(/from '.\/views\/verification\.js'/g) || []).length, 1);
  for (const retired of [
    "let pendingEnrollmentEmail", "let emailVerificationBearer",
    "function emailVerificationStorageKey(", "function emailVerificationIdempotency(",
    "function renderEmailVerificationGate(",
  ]) {
    // Require each transient implementation to live only in the view module.
    assert.equal(APP_SOURCE.includes(retired), false, retired);
  }
  // Preserve verify, resend, and cancel routes in the extracted module.
  for (const route of ["/api/v2/auth/signup/verify", "/api/v2/auth/signup/resend", "/api/v2/auth/signup/cancel"]) {
    // Bind each public route to the Verification view.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Verification view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
