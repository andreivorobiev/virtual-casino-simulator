// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for private invitation lifecycle verification. (INVITE-001, INVITE-005)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Invitations factory.
import { createInvitationsTab } from "../../web/admin/invitations.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/invitations.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify readiness and recipient-masked lifecycle evidence survive extraction.
test("INVITE-001 preserves private invitation surfaces after extraction", async () => {
  // Preserve stable action controls for post-render binding.
  const controls = new Map();
  // Model only the DOM seams owned by the renderer.
  const view = {
    innerHTML: "",
    querySelector: (selector) => {
      // Reuse one plain control per selector.
      if (!controls.has(selector)) controls.set(selector, {});
      return controls.get(selector);
    },
    querySelectorAll: () => [],
  };
  // Create the production renderer around one privacy-safe lifecycle row.
  const renderInvitations = createInvitationsTab({
    api: async () => ({
      enabled: true,
      redemption_enabled: true,
      mail_status: "ready",
      recovery_required: 0,
      invitations: [{
        invitation_id: "invite-1",
        recipient_hint: "m***@example.test",
        status: "pending",
        delivery_status: "sent",
        locale: "en-US",
        updated_at: "now",
      }],
    }),
    emptyState: (title, detail, hook) => html`<div data-empty="${hook}">${title}|${detail}</div>`,
    formatNumber: value => `number:${value}`,
    html,
    humanLabel: value => `label:${value}`,
    isActiveTab: () => true,
    localeOptions: value => `locale:${value}`,
    post: async () => ({}),
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Execute one exact lifecycle render.
  await renderInvitations();
  // Preserve ready, create, list, row, resend, and revoke markers.
  for (const marker of [
    "admin-invitations-ready",
    "admin-invitation-create",
    "admin-invitation-list",
    "admin-invitation-row",
    "invitation-resend",
    "invitation-revoke",
  ]) {
    // Require every accepted lifecycle surface.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  // Preserve only the masked recipient hint.
  assert.ok(view.innerHTML.includes("m***@example.test"));
});

// Verify the source boundary remains compact and route-complete.
test("INVITE-005 keeps the Invitations module boundary reviewable", () => {
  // Require one dispatcher import and reject the retired implementation.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/invitations\.js'/g) || []).length, 1);
  assert.equal(ADMIN_SOURCE.includes("async function invitations()"), false);
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'invitations'\) return await invitations\(\);/g) || []).length, 1);
  // Require read, create, resend, and revoke route components in the extracted module.
  for (const route of ["/api/v2/admin/invitations?limit=100", "/resend", "/revoke"]) {
    // Bind each reviewed route component to the new module.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Invitations source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
