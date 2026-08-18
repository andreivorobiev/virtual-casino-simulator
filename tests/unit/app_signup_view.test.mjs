// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for policy-gated account enrollment. (AUTH-018, OAUTH-013)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Signup view factory.
import { createSignupView } from "../../web/views/signup.js";
// Import the browser-independent tagged-template fixture for injected view rendering.
import { html, raw } from "./html_template_fixture.mjs";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/signup.js`, "utf8");

// Verify local signup and released provider readiness survive extraction.
test("AUTH-018 preserves policy-gated Signup after extraction", async () => {
  // Retain route, form, input, status, provider-region, and provider controls.
  const view = { innerHTML: "", removeAttribute: () => {} };
  const form = {};
  const controls = new Map([
    ["signup-form", form],
    ["signup-email", { value: " applicant@example.com " }],
    ["signup-display-name", { value: "Applicant" }],
    ["signup-password", { value: "strong-password" }],
    ["signup-locale", { value: "en-US" }],
    ["signup-terms", { checked: true }],
    ["signup-privacy", { checked: true }],
    ["signup-play-token", { checked: true }],
    ["signup-message", { textContent: "" }],
  ]);
  const providerStatus = { textContent: "" };
  const region = { dataset: {}, querySelector: () => providerStatus };
  const providerButtons = new Map([
    ["google", { disabled: true, setAttribute: () => {} }],
    ["facebook", { disabled: true, setAttribute: () => {} }],
  ]);
  const classes = new Set();
  // Model only document seams owned by the Signup view.
  const documentRef = {
    body: {
      classList: {
        add: value => classes.add(value),
        remove: (...values) => values.forEach(value => classes.delete(value)),
      },
    },
    getElementById: id => id === "view" ? view : controls.get(id),
    querySelector: (selector) => {
      // Resolve the provider region or one provider-specific button.
      if (selector === '[data-testid^="oauth-signup-"]') return region;
      const match = selector.match(/signup-oauth-(google|facebook)/);
      return match ? providerButtons.get(match[1]) : null;
    },
  };
  const requests = [];
  const pendingEmails = [];
  const verificationMessages = [];
  const replacements = [];
  // Create the production renderer around a fully enabled policy.
  const renderSignup = createSignupView({
    // Bind the same escape-by-default and reviewed-fragment contract as production.
    html,
    raw,
    api: async (path, options) => {
      // Return public policy for the initial read.
      if (path.endsWith("enrollment-policy")) {
        return { signup_enabled: true, enrollment_mode: "self-signup", signup_methods: { google: true } };
      }
      requests.push({ path, options });
      return {};
    },
    beginOAuth: () => {},
    cryptoRef: { randomUUID: () => "ACTION-KEY" },
    documentRef,
    getLocaleState: () => ({ locale: "en-US" }),
    historyRef: { replaceState: (_state, _title, path) => replacements.push(path) },
    oauthCompletionCopy: () => "",
    oauthProviders: async () => ({ providers: [
      { provider: "google", signup_available: true },
      { provider: "facebook", signup_available: false },
    ] }),
    renderEmailVerificationGate: message => verificationMessages.push(message),
    safe: value => String(value ?? ""),
    setPendingEnrollmentEmail: email => pendingEmails.push(email),
    setSession: () => {},
    syncFeedbackReporter: () => {},
    t: key => key,
    wireLocaleSelect: select => { select.value = "en-US"; },
    windowRef: {},
  });
  // Render local and provider enrollment controls.
  await renderSignup();
  await Promise.resolve();
  assert.ok(view.innerHTML.includes('data-testid="signup-enrollment"'));
  assert.ok(view.innerHTML.includes('data-signup-enabled="true"'));
  assert.ok(view.innerHTML.includes('data-testid="signup-oauth-google"'));
  assert.equal(providerButtons.get("google").disabled, false);
  assert.equal(providerButtons.get("facebook").disabled, true);
  assert.equal(region.dataset.testid, "oauth-signup-available");
  assert.ok(classes.has("auth-locked"));
  // Submit explicit acknowledgements and hand off to Verification.
  await form.onsubmit({ preventDefault: () => {} });
  assert.deepEqual(pendingEmails, ["applicant@example.com"]);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, "/api/v2/auth/signup");
  assert.equal(requests[0].options.body.accepted, true);
  assert.deepEqual(replacements, ["/enroll/verify"]);
  assert.deepEqual(verificationMessages, ["signup.pending"]);
});

// Verify the shell owns composition while the Signup view owns policy rendering.
test("OAUTH-013 keeps the Signup view boundary reviewable", () => {
  // Require one import and reject both retired implementations.
  assert.equal((APP_SOURCE.match(/from '.\/views\/signup\.js'/g) || []).length, 1);
  assert.equal(APP_SOURCE.includes("function renderSignupGate("), false);
  assert.equal(APP_SOURCE.includes("function enableAvailableOAuthSignup("), false);
  // Preserve local policy, signup, and provider readiness routes.
  for (const route of ["/api/v2/auth/enrollment-policy", "/api/v2/auth/signup", "oauthProviders()"] ) {
    // Bind each reviewed capability to the Signup view.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Signup view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
