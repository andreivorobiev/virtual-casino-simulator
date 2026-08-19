// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for trusted Operations diagnostics. (ADMIN-014, MAIL-003)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Operations factory.
import { createOperationsTab } from "../../web/admin/operations.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/operations.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify Operations health remains independent from OAuth and mail diagnostics.
test("ADMIN-014 preserves independent Operations diagnostics after extraction", async () => {
  // Retain replacement cards for independently settling diagnostics.
  const oauthCard = { outerHTML: "" };
  const mailCard = { outerHTML: "" };
  // Model only DOM seams owned by the renderer.
  const view = {
    innerHTML: "",
    querySelector: selector => selector.includes("oauth") ? oauthCard : mailCard,
  };
  // Return one live Operations envelope and two independent diagnostics.
  const api = async (path) => {
    // Return all three allowlisted provider rows.
    if (path.endsWith("/oauth/providers")) {
      return { providers: [
        { provider: "local", status: "ready", runtime_available: true },
        { provider: "google", status: "disabled", runtime_available: false },
        { provider: "facebook", status: "disabled", runtime_available: false },
      ] };
    }
    // Return aggregate-only mail diagnostics.
    if (path.endsWith("/mail/readiness")) {
      return {
        status: "ready",
        provider: "postmark",
        delivery_summary: { sent: 2, retry_wait: 0, failed: 0, uncertain: 0 },
        suppressed_recipients: 1,
        reasons: [],
      };
    }
    // Return trusted live dependency and heartbeat evidence.
    return {
      ready: true,
      storage_provider: "json",
      reasons: [],
      build: { app_version: "9.70.7", sha: "abc123" },
      last_successful_heartbeat_at: "2026-08-18T00:00:00Z",
    };
  };
  // Create and execute the production renderer.
  const renderOperations = createOperationsTab({
    api,
    formatDate: () => "formatted-time",
    html,
    isActiveTab: () => true,
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    view,
  });
  await renderOperations();
  // Allow both independent diagnostic promises to settle.
  await Promise.resolve();
  // Preserve live Operations while placeholders never reclassify its state.
  assert.ok(view.innerHTML.includes("admin-operations-live"));
  assert.ok(view.innerHTML.includes("admin-operations-state"));
  // Preserve independently replaced provider and mail cards.
  assert.ok(String(oauthCard.outerHTML).includes("admin-oauth-diagnostics"));
  assert.ok(String(mailCard.outerHTML).includes("admin-mail-ready"));
  assert.ok(String(mailCard.outerHTML).includes("admin-mail-suppression-summary"));
});

// Verify the source boundary remains compact and route-complete.
test("MAIL-003 keeps the Operations module boundary reviewable", () => {
  // Require one dispatcher import and reject all retired implementations.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/operations\.js'/g) || []).length, 1);
  for (const name of [
    "operations", "oauthDiagnosticsCard", "replaceOAuthDiagnosticsCard",
    "mailDiagnosticsCard", "replaceMailDiagnosticsCard",
  ]) {
    // Require each implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false, name);
  }
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'operations'\) return operations\(\);/g) || []).length, 1);
  // Require all three independent diagnostic routes inside the extracted module.
  for (const route of ["/api/v2/admin/operations", "/api/v2/admin/oauth/providers", "/api/v2/admin/mail/readiness"]) {
    // Bind each reviewed route to the new module.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Operations source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
