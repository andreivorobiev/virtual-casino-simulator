// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Requirements-tab verification. (ADMIN-010, ADMIN-021)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Requirements factory for listener-free DOM-output parity.
import { createRequirementsTab } from "../../web/admin/requirements.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Requirements source once for endpoint and line-width assertions.
const REQUIREMENTS_SOURCE = await readFile(`${ROOT}/web/admin/requirements.js`, "utf8");
// Render nested arrays and ordinary values like the reviewed production tagged-template boundary.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact test markup without introducing source-formatting whitespace.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => {
  // Append each literal segment and its rendered substitution in source order.
  return markup + segment + (index < values.length ? renderValue(values[index]) : "");
}, "");
// Escape the exact five HTML-sensitive characters used by the production boundary.
const safe = value => String(value ?? "").replace(/[&<>'"]/g, character => ({
  // Preserve the production entity for ampersands.
  "&": "&amp;",
  // Preserve the production entity for opening angle brackets.
  "<": "&lt;",
  // Preserve the production entity for closing angle brackets.
  ">": "&gt;",
  // Preserve the production entity for apostrophes.
  "'": "&#39;",
  // Preserve the production entity for quotation marks.
  '"': "&quot;",
})[character]);
// Store exact English resources used by the listener-free fixture. (I18N-014)
const resources = {
  "nav.requirements": "Requirements",
  "requirements.subtitle": "Coverage across the product and test suite.",
  "requirements.id": "ID",
  "requirements.module": "Module",
  "requirements.description": "Description",
  "requirements.status": "Status",
  "requirements.tests": "Tests",
};
// Resolve installed-locale copy through the same domain-aware call contract.
const t = key => resources[key] ?? key;
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;

// Build one listener-free renderer fixture around the selected requirement records.
function rendererFor(requirements) {
  // Capture localized title calls without browser globals.
  const titleCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "" };
  // Record exact API requests made by the renderer.
  const apiCalls = [];
  // Create the renderer through the production dependency boundary.
  const renderRequirements = createRequirementsTab({
    // Return the selected registry while recording the frozen endpoint.
    api: async path => {
      // Record the request before returning deterministic fixture data.
      apiCalls.push(path);
      // Return the exact Admin response envelope.
      return { requirements };
    },
    html,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { apiCalls, renderRequirements, titleCalls, view };
}

// Verify the extracted renderer preserves the exact populated Requirements output.
test("ADMIN-010 preserves Requirements DOM output after extraction", async () => {
  // Create one record with unsafe text and both API and Browser evidence identities.
  const records = [{ id: "REQ<1", module: "Core & UI", description: 'Use "safe" output', status: "PASS", api_tests: ["API-1"], browser_tests: ["BR-2"] }];
  // Create the listener-free production renderer.
  const fixture = rendererFor(records);
  // Execute one exact Requirements render.
  await fixture.renderRequirements();
  // Preserve the exact frozen route and one-request behavior.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/requirements"]);
  // Preserve the installed-locale title and subtitle call. (I18N-014)
  assert.deepEqual(fixture.titleCalls, [["Requirements", "Coverage across the product and test suite."]]);
  // Assemble the accepted compact card and table output independently.
  const expected = [
    '<section class="admin-card"><h3>Requirements</h3><table class="mini-table"><tr>',
    "<th>ID</th><th>Module</th><th>Description</th><th>Status</th><th>Tests</th></tr>",
    "<tr><td>REQ&lt;1</td><td>Core &amp; UI</td><td>Use &quot;safe&quot; output</td>",
    "<td>PASS</td><td>API-1, BR-2</td></tr></table></section>",
  ].join("");
  // Require byte-identical populated DOM output and ordered test identities.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify missing requirement arrays preserve the accepted empty table output.
test("ADMIN-021 preserves empty Requirements table output after extraction", async () => {
  // Create the renderer with no returned records.
  const fixture = rendererFor(undefined);
  // Execute one exact Requirements render.
  await fixture.renderRequirements();
  // Preserve the compact header-only table used by the accepted monolith.
  const expected = [
    '<section class="admin-card"><h3>Requirements</h3><table class="mini-table"><tr>',
    "<th>ID</th><th>Module</th><th>Description</th><th>Status</th><th>Tests</th></tr>",
    "</table></section>",
  ].join("");
  // Require byte-identical empty registry output.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the per-tab source boundary remains small and frozen to the v1 endpoint.
test("ADMIN-021 keeps the Requirements module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Requirements factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/requirements\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Requirements implementation.
  assert.equal(ADMIN_SOURCE.includes("async function requirements()"), false);
  // Require one exact frozen Requirements endpoint inside the extracted module.
  assert.equal((REQUIREMENTS_SOURCE.match(/\/api\/v1\/admin\/requirements/g) || []).length, 1);
  // Keep every Requirements module source line within the governed review-width ceiling.
  assert.ok(Math.max(...REQUIREMENTS_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
