// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Users verification. (ADMIN-034)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Users factory for listener-free render parity.
import { createUsersTab } from "../../web/admin/users.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read dispatcher and module sources once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const USERS_SOURCE = await readFile(`${ROOT}/web/admin/users.js`, "utf8");
// Render nested arrays and ordinary values like the reviewed production tagged template.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup in source order.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => {
  // Append each literal segment and rendered substitution.
  return markup + segment + (index < values.length ? renderValue(values[index]) : "");
}, "");

// Build one listener-free Users renderer around a supplied API boundary.
function rendererFor(api, isActiveTab = () => true) {
  // Preserve stable action controls for post-render binding.
  const controls = new Map();
  // Model only the DOM seams owned by the renderer.
  const view = {
    innerHTML: "unchanged",
    replaceChildren: () => { view.innerHTML = ""; },
    querySelector: (selector) => {
      // Reuse one plain action control for each selector.
      if (!controls.has(selector)) controls.set(selector, {});
      // Return the stable control.
      return controls.get(selector);
    },
    querySelectorAll: () => [],
  };
  // Create the production renderer with deterministic presentation helpers.
  const renderUsers = createUsersTab({
    activate: () => {},
    api,
    emptyState: (title, detail, hook) => html`<div data-empty="${hook}">${title}|${detail}</div>`,
    formatLocaleOptions: value => `format:${value}`,
    formatMoney: value => `money:${value}`,
    html,
    humanLabel: value => `label:${value}`,
    isActiveTab,
    localeOptions: value => `locale:${value}`,
    option: (value, label, selected) => html`<option value="${value}" data-selected="${selected}">${label}</option>`,
    post: async () => ({}),
    raw: value => value,
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Return observable fixture state.
  return { controls, renderUsers, view };
}

// Return one ordinary managed account fixture.
function managedUser(email) {
  // Preserve the complete row shape consumed by the renderer.
  return {
    user_id: `id-${email}`,
    email,
    display_name: "Managed User",
    status: "active",
    token_balance: 5000,
    token_state: "active",
    terms_status: "accepted",
    language: "en-US",
    format_locale: "browser",
    roles: ["player"],
  };
}

// Verify managed accounts render while every guest identity marker remains excluded.
test("ADMIN-034 keeps Users account-only after extraction", async () => {
  // Build a mixed legacy envelope containing one account and three guest classifiers.
  const data = { users: [
    managedUser("managed@example.test"),
    { ...managedUser("role@example.test"), roles: ["guest"] },
    { ...managedUser("principal@example.test"), principal_type: "guest" },
    { ...managedUser("provider@example.test"), identity_provider: "guest" },
  ] };
  // Render the mixed envelope once.
  const fixture = rendererFor(async () => data);
  await fixture.renderUsers();
  // Preserve the managed account and exclude every temporary visitor.
  assert.ok(fixture.view.innerHTML.includes("managed@example.test"));
  for (const email of ["role@example.test", "principal@example.test", "provider@example.test"]) {
    // Require the guest marker to stay outside ordinary account management.
    assert.equal(fixture.view.innerHTML.includes(email), false, email);
  }
  // Preserve the explicit Guest Trials handoff and account creation hooks.
  assert.ok(fixture.view.innerHTML.includes('data-testid="admin-users-guest-separation"'));
  assert.ok(fixture.view.innerHTML.includes('data-testid="admin-user-create"'));
});

// Verify a superseded same-tab response cannot overwrite newer account state.
test("ADMIN-034 rejects stale Users responses after extraction", async () => {
  // Retain independent resolvers for two concurrent account requests.
  const pending = [];
  // Build a renderer whose API resolves only when the test releases each request.
  const fixture = rendererFor(() => new Promise(resolve => pending.push(resolve)));
  // Start the older and newer render in that order.
  const older = fixture.renderUsers();
  const newer = fixture.renderUsers();
  // Resolve and render the newest account state first.
  pending[1]({ users: [managedUser("new@example.test")] });
  await newer;
  assert.ok(fixture.view.innerHTML.includes("new@example.test"));
  // Resolve the stale request and require the newer output to survive.
  pending[0]({ users: [managedUser("old@example.test")] });
  await older;
  assert.ok(fixture.view.innerHTML.includes("new@example.test"));
  assert.equal(fixture.view.innerHTML.includes("old@example.test"), false);
});

// Verify the per-tab boundary stays compact and route-complete.
test("ADMIN-034 keeps the Users module boundary reviewable", () => {
  // Require one dispatcher import and the exact route.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/users\.js'/g) || []).length, 1);
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'users'\) return users\(\);/g) || []).length, 1);
  // Reject every retired monolith-owned Users implementation.
  for (const name of [
    "users", "userRows", "isManagedAccountUser", "createUser", "saveUserAccount",
    "toggleUser", "resetUserPassword", "updateUserTerms", "saveUserLocale",
  ]) {
    // Require the implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false, name);
  }
  // Bind all frozen account route families to the extracted module.
  for (const route of ["/api/v1/admin/users", "/api/v2/admin/users/", "/password-reset", "/terms", "/locale"]) {
    // Require each reviewed family inside the new module.
    assert.ok(USERS_SOURCE.includes(route), route);
  }
  // Keep every Users source line within the governed review-width ceiling.
  assert.ok(Math.max(...USERS_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
