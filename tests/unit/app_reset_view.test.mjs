// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for enumeration-safe password recovery. (RESET-004, SEC-016)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Reset view factory.
import { createPasswordResetView } from "../../web/views/reset.js";
// Import the browser-independent tagged-template fixture for injected view rendering.
import { html, raw } from "./html_template_fixture.mjs";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/reset.js`, "utf8");

// Verify an arrived bearer remains memory-only and completes through generic copy.
test("SEC-016 preserves transient password-reset completion after extraction", async () => {
  // Retain route, form, status, mailbox, password, and submit controls.
  const view = { className: "", innerHTML: "", removeAttribute: () => {} };
  const submit = { disabled: false, isConnected: true };
  const form = { querySelector: () => submit };
  const controls = new Map([
    ["password-reset-form", form],
    ["reset-message", { dataset: {}, textContent: "" }],
    ["reset-email", { value: " owner@example.com " }],
    ["reset-password", { value: "replacement-password" }],
  ]);
  const classes = new Set();
  // Model only document seams owned by the recovery view.
  const documentRef = {
    body: {
      classList: {
        add: value => classes.add(value),
        remove: value => classes.delete(value),
      },
    },
    getElementById: id => id === "view" ? view : controls.get(id),
  };
  const requests = [];
  const replacements = [];
  const loginMessages = [];
  let arrival = "RESET-SECRET";
  // Create the production completion view around deterministic seams.
  const renderReset = createPasswordResetView({
    // Bind the same escape-by-default and reviewed-fragment contract as production.
    html,
    raw,
    api: async (path, options) => { requests.push({ path, options }); },
    cryptoRef: { randomUUID: () => "ACTION-KEY" },
    documentRef,
    getLocaleState: () => ({ locale: "en-US" }),
    historyRef: { replaceState: (_state, _title, path) => replacements.push(path) },
    holdTransientBearer: (held, arrived) => arrived || held,
    renderLoginGate: message => loginMessages.push(message),
    safe: value => String(value ?? ""),
    setSession: () => {},
    syncFeedbackReporter: () => {},
    t: key => key,
    transientRouteBearer: () => { const value = arrival; arrival = ""; return value; },
    windowRef: { CasinoCurrentUser: {}, location: { href: "https://casino.test/account/reset?token=RESET-SECRET" } },
  });
  // Render completion and scrub the browser bearer before submit.
  renderReset();
  assert.ok(view.innerHTML.includes('data-testid="password-reset-complete"'));
  assert.deepEqual(replacements, ["/account/reset"]);
  assert.ok(classes.has("auth-locked"));
  // Submit exact transient bearer and replacement once.
  await form.onsubmit({ preventDefault: () => {}, currentTarget: form });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, "/api/v2/auth/password-reset/complete");
  assert.equal(requests[0].options.body.token, "RESET-SECRET");
  assert.equal(requests[0].options.body.email, "owner@example.com");
  assert.equal(requests[0].options.body.new_password, "replacement-password");
  assert.deepEqual(replacements, ["/account/reset", "/"]);
  assert.deepEqual(loginMessages, ["recovery.completed"]);
});

// Verify the shell owns composition while the view owns recovery bearer state.
test("RESET-004 keeps the Reset view boundary reviewable", () => {
  // Require one import and reject retired state and implementation.
  assert.equal((APP_SOURCE.match(/from '.\/views\/reset\.js'/g) || []).length, 1);
  assert.equal(APP_SOURCE.includes("let passwordResetBearerToken"), false);
  assert.equal(APP_SOURCE.includes("function renderPasswordResetGate("), false);
  // Preserve both exact public endpoints and stable mode identities.
  for (const route of ["/api/v2/auth/password-reset/initiate", "/api/v2/auth/password-reset/complete"]) {
    // Bind each route to the extracted view.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  assert.ok(MODULE_SOURCE.includes("'password-reset-complete'"));
  assert.ok(MODULE_SOURCE.includes("'password-reset-initiate'"));
  // Keep every Reset view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
