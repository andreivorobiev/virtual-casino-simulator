// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for required terms rendering. (AUTH-011)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Terms view factory.
import { createTermsView } from "../../web/views/terms.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/terms.js`, "utf8");

// Verify required consent remains versioned and enters the authenticated shell once.
test("AUTH-011 preserves required terms acceptance after extraction", async () => {
  // Retain the route outlet, message, and action control.
  const view = { className: "", innerHTML: "", removeAttribute: () => {} };
  const message = { textContent: "" };
  const button = {};
  const classes = new Set();
  // Model only document seams owned by this view.
  const documentRef = {
    body: {
      classList: {
        add: value => classes.add(value),
        remove: value => classes.delete(value),
      },
    },
    getElementById: id => id === "view" ? view : id === "auth-message" ? message : button,
  };
  // Retain the canonical current-session object through accepted getters and setters.
  let session = { user: { id: "USR-1" }, terms: { required: true, version: "private-beta-1" } };
  const accepted = [];
  const entered = [];
  // Create the production view around deterministic API and presentation seams.
  const renderTerms = createTermsView({
    acceptTerms: async payload => { accepted.push(payload); return { required: false, version: payload.terms_version }; },
    documentRef,
    enterAuthenticated: async value => { entered.push(value); },
    getLocaleState: () => ({ locale: "en-US" }),
    getSession: () => session,
    normalizeCurrentUser: value => value,
    safe: value => String(value ?? ""),
    setSession: value => { session = value; },
    t: (key, values = {}) => key === "terms.version" ? `${key}:${values.version}` : key,
  });
  // Render one required consent gate.
  renderTerms(session);
  assert.ok(view.innerHTML.includes('data-testid="terms-gate"'));
  assert.ok(view.innerHTML.includes("private-beta-1"));
  assert.ok(view.innerHTML.includes('data-testid="accept-terms"'));
  assert.ok(classes.has("auth-locked"));
  // Accept exact versioned consent and enter the shell once.
  await button.onclick();
  assert.deepEqual(accepted, [{ terms_version: "private-beta-1", locale: "en-US" }]);
  assert.equal(session.terms.required, false);
  assert.equal(entered.length, 1);
});

// Verify the shell owns composition while the view owns its implementation.
test("AUTH-011 keeps the Terms view boundary reviewable", () => {
  // Require one import and reject retired inline implementations.
  assert.equal((APP_SOURCE.match(/from '.\/views\/terms\.js'/g) || []).length, 1);
  assert.equal(APP_SOURCE.includes("function renderTermsGate("), false);
  assert.equal(APP_SOURCE.includes("function handleTermsAccept("), false);
  // Preserve both accepted endpoint and stable UI identities in the module.
  assert.ok(MODULE_SOURCE.includes("acceptTerms({"));
  assert.ok(MODULE_SOURCE.includes('data-testid="terms-gate"'));
  assert.ok(MODULE_SOURCE.includes('data-testid="accept-terms"'));
  // Keep every Terms view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
