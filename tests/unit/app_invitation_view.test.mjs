// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for private invitation redemption. (INVITE-003, INVITE-005)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Invitation view factory.
import { createInvitationView } from "../../web/views/invitation.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/invitation.js`, "utf8");

// Verify bearer scrubbing and caller-idempotent redemption survive extraction.
test("INVITE-003 preserves private invitation redemption after extraction", async () => {
  // Retain route, form, input, message, and submit controls.
  const view = { className: "", innerHTML: "", removeAttribute: () => {} };
  const controls = new Map([
    ["invitation-form", {}],
    ["invitation-locale", { value: "en-US" }],
    ["invitation-email", { value: " invitee@example.com " }],
    ["invitation-password", { value: "strong-password" }],
    ["invitation-display-name", { value: " Invitee " }],
    ["invitation-terms", { checked: true }],
    ["invitation-message", { textContent: "" }],
  ]);
  const submit = { disabled: false };
  const classes = new Set();
  // Model only document seams owned by the invitation view.
  const documentRef = {
    body: {
      classList: {
        add: value => classes.add(value),
        remove: (...values) => values.forEach(value => classes.delete(value)),
      },
    },
    getElementById: id => id === "view" ? view : controls.get(id),
    querySelector: selector => selector === '[data-testid="invitation-submit"]' ? submit : null,
  };
  // Retain token-free session storage and browser-history evidence.
  const storage = new Map();
  const replacements = [];
  const requests = [];
  const loginMessages = [];
  let arrival = "SECRET-TOKEN";
  // Create the production view around deterministic browser and API seams.
  const renderInvitation = createInvitationView({
    cryptoRef: globalThis.crypto,
    documentRef,
    getLocaleState: () => ({ locale: "en-US" }),
    historyRef: { replaceState: (_state, _title, path) => replacements.push(path) },
    redeemInvitation: async payload => { requests.push(payload); },
    renderLoginGate: message => loginMessages.push(message),
    safe: value => String(value ?? ""),
    sessionStorageRef: {
      getItem: key => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value),
    },
    setSession: () => {},
    syncFeedbackReporter: () => {},
    t: key => key,
    transientRouteBearer: () => { const value = arrival; arrival = ""; return value; },
    wireLocaleSelect: select => { select.value = "en-US"; },
    windowRef: {},
  });
  // Render once and scrub the bearer before any submit.
  renderInvitation();
  assert.deepEqual(replacements, ["/enroll/invitation"]);
  assert.ok(view.innerHTML.includes('data-testid="invitation-redemption"'));
  assert.ok(view.innerHTML.includes('data-testid="invitation-submit"'));
  assert.ok(classes.has("auth-locked"));
  // Redeem through the stable module-held bearer.
  await controls.get("invitation-form").onsubmit({ preventDefault: () => {} });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].token, "SECRET-TOKEN");
  assert.equal(requests[0].email, "invitee@example.com");
  assert.equal(requests[0].accepted, true);
  assert.equal(typeof requests[0].idempotency_key, "string");
  assert.equal(requests[0].idempotency_key.includes("SECRET-TOKEN"), false);
  assert.deepEqual(replacements, ["/enroll/invitation", "/"]);
  assert.deepEqual(loginMessages, ["invitation.success"]);
});

// Verify the shell owns composition while the view owns transient redemption state.
test("INVITE-005 keeps the Invitation view boundary reviewable", () => {
  // Require one import and reject retired state and implementations.
  assert.equal((APP_SOURCE.match(/from '.\/views\/invitation\.js'/g) || []).length, 1);
  assert.equal(APP_SOURCE.includes("let invitationBearerToken"), false);
  assert.equal(APP_SOURCE.includes("function invitationIdempotency("), false);
  assert.equal(APP_SOURCE.includes("function renderInvitationGate("), false);
  assert.equal(APP_SOURCE.includes("function handleInvitationSubmit("), false);
  // Preserve the exact endpoint and public surface markers in the module.
  assert.ok(MODULE_SOURCE.includes("redeemInvitation(payload)"));
  assert.ok(MODULE_SOURCE.includes('data-testid="invitation-redemption"'));
  assert.ok(MODULE_SOURCE.includes("historyRef.replaceState({}, '', '/enroll/invitation')"));
  // Keep every Invitation view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
