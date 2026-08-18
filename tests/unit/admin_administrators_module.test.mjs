// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic owner-only role delegation. (ADMIN-033)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Administrators factory.
import { createAdministratorsTab } from "../../web/admin/administrators.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/administrators.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and its following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Build one listener-free role-management fixture.
function rendererFor(post) {
  // Preserve the transient controls and grant action.
  const controls = new Map([
    ["#administrator-target", { value: "eligible-1" }],
    ["#administrator-password", { value: "owner-password" }],
    ["#administrator-reason", { value: " bounded reason " }],
    ["#administrator-grant", {}],
  ]);
  // Model only the DOM seams owned by this renderer.
  const view = {
    innerHTML: "",
    querySelector: selector => controls.get(selector),
    querySelectorAll: () => [],
  };
  // Return contract-shaped data for both concurrent reads.
  const api = async path => path.includes("/audit")
    ? { audit: [{ at: "now", action: "grant", target_user_id: "eligible-1", reason: "reason" }] }
    : {
      revision: 7,
      eligible_accounts: [{ user_id: "eligible-1", display_name: "Eligible", email: "e@example.test" }],
      administrators: [{
        user_id: "owner-1",
        display_name: "Owner",
        email: "owner@example.test",
        roles: ["owner"],
        protected_owner: true,
      }],
    };
  // Create the production renderer with deterministic presentation helpers.
  const renderAdministrators = createAdministratorsTab({
    api,
    emptyState: (title, detail) => html`<div>${title}|${detail}</div>`,
    html,
    humanLabel: value => `label:${value}`,
    isActiveTab: () => true,
    option: (value, label) => html`<option value="${value}">${label}</option>`,
    post,
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Return every observable seam.
  return { controls, renderAdministrators, view };
}

// Verify role and audit evidence render through the extracted boundary.
test("ADMIN-033 preserves Administrators evidence after extraction", async () => {
  // Render one populated role-management envelope.
  const fixture = rendererFor(async () => ({}));
  await fixture.renderAdministrators();
  // Preserve grant, current-role, audit, and protected-owner markers.
  for (const marker of [
    'data-testid="admin-administrator-grant"',
    'data-testid="admin-administrator-list"',
    'data-testid="admin-administrator-audit"',
    "administrators.protected",
  ]) {
    // Require each accepted fragment in the completed view.
    assert.ok(fixture.view.innerHTML.includes(marker), marker);
  }
});

// Verify the transient owner password is scrubbed before network work begins.
test("ADMIN-033 scrubs reauthentication before role mutation awaits", async () => {
  // Capture the exact mutation while checking the live password control.
  let captured;
  let fixture;
  const post = async (...values) => {
    // Require scrubbing before the injected network boundary executes.
    assert.equal(fixture.controls.get("#administrator-password").value, "");
    // Retain the exact call for payload assertions.
    captured = values;
  };
  // Render and invoke the bound grant action.
  fixture = rendererFor(post);
  await fixture.renderAdministrators();
  await fixture.controls.get("#administrator-grant").onclick();
  // Preserve the exact target/action route and bounded role payload.
  assert.equal(captured[0], "/api/v2/admin/administrators/eligible-1/grant");
  assert.equal(captured[1].password, "owner-password");
  assert.equal(captured[1].reason, "bounded reason");
  assert.equal(captured[1].revision, 7);
  assert.equal(typeof captured[1].idempotency_key, "string");
});

// Verify the source boundary remains compact and route-complete.
test("ADMIN-033 keeps the Administrators module boundary reviewable", () => {
  // Require one dispatcher import and reject the retired implementation.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/administrators\.js'/g) || []).length, 1);
  assert.equal(ADMIN_SOURCE.includes("async function administrators()"), false);
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'administrators'\) return await administrators\(\);/g) || []).length, 1);
  // Require the frozen read and mutation route families in the extracted module.
  assert.ok(MODULE_SOURCE.includes("/api/v2/admin/administrators"));
  assert.ok(MODULE_SOURCE.includes("/api/v2/admin/administrators/audit?limit=100"));
  // Keep every module source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
