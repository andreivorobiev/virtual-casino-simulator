// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic enrollment-governance verification. (AUTH-015)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Enrollment factory.
import { createEnrollmentTab } from "../../web/admin/enrollment.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/enrollment.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify policy, readiness, audit, and provider controls retain separate surfaces.
test("AUTH-015 preserves enrollment governance surfaces after extraction", async () => {
  // Retain the independently inserted provider-control markup.
  let providerMarkup = "";
  // Preserve stable action controls for listener binding.
  const controls = new Map();
  // Model only DOM seams owned by the renderer.
  const view = {
    innerHTML: "",
    querySelector: (selector) => {
      // Return the readiness insertion anchor separately.
      if (selector === '[data-testid="admin-enrollment-readiness"]') {
        return { insertAdjacentHTML: (_, markup) => { providerMarkup = markup; } };
      }
      // Reuse one action control for every other selector.
      if (!controls.has(selector)) controls.set(selector, {});
      return controls.get(selector);
    },
  };
  // Return contract-shaped data for all three coherent reads.
  const api = async (path) => {
    // Return method readiness independently from durable policy.
    if (path.endsWith("/enrollment-readiness")) {
      return { live_enablement_authorized: false, methods: { email: { enabled: false, ready: false, blockers: ["held"] } } };
    }
    // Return provider kill switches independently from signup methods.
    if (path.endsWith("/oauth/operational-controls")) {
      return { revision: 3, providers: { google: false, facebook: false } };
    }
    // Return durable enrollment policy and immutable audit.
    return {
      revision: 2,
      modes: ["closed", "invite_only"],
      methods: ["email", "google"],
      policy: { mode: "closed", methods: { email: false, google: false }, invitations_enabled: false },
      audit: [{ at: "now", actor_id: "owner-1", reason: "held" }],
    };
  };
  // Create and execute the production renderer.
  const renderEnrollment = createEnrollmentTab({
    api,
    emptyState: (title, detail) => html`<div>${title}|${detail}</div>`,
    html,
    humanLabel: value => `label:${value}`,
    isActiveTab: () => true,
    option: (value, label) => html`<option value="${value}">${label}</option>`,
    post: async () => ({}),
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  await renderEnrollment();
  // Preserve distinct signup policy, readiness, and audit cards.
  for (const marker of ["admin-enrollment-policy", "admin-enrollment-readiness", "admin-enrollment-audit"]) {
    // Require each card in the atomic base render.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  // Preserve the independently inserted provider operational plane.
  assert.ok(providerMarkup.includes("admin-oauth-operational-controls"));
  assert.ok(providerMarkup.includes("oauth-operational-google"));
});

// Verify the source boundary remains compact and route-complete.
test("AUTH-015 keeps the Enrollment module boundary reviewable", () => {
  // Require one dispatcher import and reject the retired implementation.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/enrollment\.js'/g) || []).length, 1);
  assert.equal(ADMIN_SOURCE.includes("async function enrollment()"), false);
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'enrollment'\) return await enrollment\(\);/g) || []).length, 1);
  // Require every frozen read/preview/apply family in the extracted module.
  for (const route of [
    "/api/v2/admin/enrollment-policy",
    "/api/v2/admin/enrollment-readiness",
    "/api/v2/admin/oauth/operational-controls",
  ]) {
    // Bind the route family to the new module.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Enrollment source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
