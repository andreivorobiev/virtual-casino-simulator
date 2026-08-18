// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for the extracted login and provider-account view. (UX-028, OAUTH-007)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Login view factory.
import { createLoginView } from "../../web/views/login.js";
// Import the browser-independent tagged-template fixture for injected view rendering.
import { html, raw } from "./html_template_fixture.mjs";

// Resolve and read reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/login.js`, "utf8");

// Build the minimal document surface owned by logged-out entry.
function loginDocument() {
  // Track body classes without a browser layout engine.
  const classes = new Set();
  // Retain mounted markup and attribute cleanup calls.
  const view = { className: "", innerHTML: "", removeAttribute: () => {} };
  // Retain event handlers installed on stable controls.
  const form = { reportValidity: () => true };
  const checkbox = { checked: true, focus: () => {} };
  const gate = {};
  const guestButton = { addEventListener: (_name, handler) => { guestButton.onclick = handler; } };
  const providerButton = { addEventListener: (_name, handler) => { providerButton.onclick = handler; } };
  // Model mutable asynchronous slots and the one live status owner.
  const controls = new Map([
    ["view", view],
    ["auth-locale-select", {}],
    ["login-form", form],
    ["login-terms-check", checkbox],
    ["auth-message", { dataset: {}, textContent: "" }],
    ["auth-guest-slot", { innerHTML: "", setAttribute: () => {} }],
    ["auth-account-slot", { innerHTML: "" }],
    ["auth-provider-slot", { innerHTML: "" }],
    ["guest-trial-button", guestButton],
    ["login-email", { value: " player@example.com " }],
    ["login-password", { value: "secret" }],
  ]);
  // Resolve only selectors exercised by the extracted view.
  const documentRef = {
    body: { classList: { add: value => classes.add(value), remove: (...values) => values.forEach(value => classes.delete(value)) } },
    getElementById: id => controls.get(id) || null,
    querySelector: selector => selector === '[data-testid="login-gate"]' ? gate : selector.includes("oauth-google") ? providerButton : null,
  };
  // Return fixtures so assertions can inspect installed behavior.
  return { checkbox, classes, controls, documentRef, form, gate, providerButton, view };
}

// Verify policy/provider readiness and password entry survive extraction.
test("UX-028 preserves guest-first Login behavior after extraction", async () => {
  // Build one browser-like login fixture.
  const fixture = loginDocument();
  const sessions = [];
  const loginCalls = [];
  const replacements = [];
  // Create the production renderer around ready guest, signup, and Google capabilities.
  const { renderLoginGate } = createLoginView({
    // Bind the same escape-by-default and reviewed-fragment contract as production.
    html,
    raw,
    api: async () => ({ guest_trials_enabled: true, signup_enabled: true }),
    documentRef: fixture.documentRef,
    enterAuthenticated: session => sessions.push(session),
    getLocaleState: () => ({ locale: "en-US" }),
    getSession: () => null,
    guestTrial: async () => ({ user: { roles: ["guest"] } }),
    historyRef: { state: {}, replaceState: (_state, _title, path) => replacements.push(path) },
    isGuestSession: () => false,
    locationRef: { href: "https://casino.test/?oauth_provider=google&oauth_status=signed_in", assign: () => {} },
    login: async request => { loginCalls.push(request); return { user: { email: request.email } }; },
    navigate: () => {},
    oauthLinks: async () => ({ providers: [] }),
    oauthProviders: async () => ({ providers: [{ provider: "google", available: true }] }),
    safe: value => String(value ?? ""),
    startOAuth: async () => ({ authorization_url: "https://provider.test/flow" }),
    syncFeedbackReporter: () => {},
    t: key => key,
    unlinkOAuth: async () => {},
    windowRef: { innerWidth: 1280, CasinoCurrentUser: {}, confirm: () => true },
    wireLocaleSelect: () => {},
  });
  // Render the stable entry gate and let both capability reads settle.
  renderLoginGate();
  await Promise.resolve();
  await Promise.resolve();
  assert.ok(fixture.view.innerHTML.includes('data-testid="login-gate"'));
  assert.ok(fixture.controls.get("auth-guest-slot").innerHTML.includes('data-testid="guest-trial-button"'));
  assert.ok(fixture.controls.get("auth-provider-slot").innerHTML.includes('data-testid="oauth-google"'));
  assert.deepEqual(replacements, ["/"]);
  // Submit accepted credentials through the extracted handler.
  await fixture.form.onsubmit({ preventDefault: () => {}, currentTarget: fixture.form });
  assert.equal(loginCalls.length, 1);
  assert.equal(loginCalls[0].email, "player@example.com");
  assert.equal(loginCalls[0].terms_acknowledged, true);
  assert.equal(sessions.length, 1);
});

// Verify the shell owns composition while Login owns all auth rendering state.
test("OAUTH-007 keeps the Login view boundary reviewable", () => {
  // Require one module import and reject every retired implementation from the shell.
  assert.equal((APP_SOURCE.match(/from '.\/views\/login\.js'/g) || []).length, 1);
  for (const name of ["renderLoginGate", "renderLoginPolicyActions", "renderLoginProviderActions", "renderOAuthAccountControls", "beginOAuth"]) {
    // Reject shell-owned function declarations while allowing composed callback references.
    assert.equal(APP_SOURCE.includes(`function ${name}(`), false, name);
    assert.ok(MODULE_SOURCE.includes(`function ${name}(`), name);
  }
  // Preserve the exact public policy and provider API seams.
  for (const seam of ["/api/v2/auth/enrollment-policy", "oauthProviders()", "oauthLinks()", "startOAuth("]) assert.ok(MODULE_SOURCE.includes(seam), seam);
  // Keep every Login view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
