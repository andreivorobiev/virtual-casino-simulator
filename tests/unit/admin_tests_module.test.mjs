// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Tests-tab verification. (TEST-145)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Tests factory for listener-free DOM-output parity.
import { createTestsTab } from "../../web/admin/tests.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Tests source once for endpoint and line-width assertions.
const TESTS_SOURCE = await readFile(`${ROOT}/web/admin/tests.js`, "utf8");
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
// Render escaped structured diagnostics through the accepted Admin helper contract.
const pre = object => html`<pre class="logview">${safe(JSON.stringify(object, null, 2))}</pre>`;
// Store the exact English resources required by the Tests fixture.
const resources = {
  "tests.title": "Tests",
  "tests.subtitle": "Latest verification results.",
  "tests.heading": "Test results",
  "tests.emptyTitle": "No test results yet",
  "tests.emptyDetail": "Run verification to populate this panel.",
};
// Resolve the reviewed resources and one count-bearing summary required by this fixture.
const t = (key, params = {}) => key === "tests.resultFields" ? `${params.count} result fields` : (resources[key] ?? key);

// Build one listener-free renderer fixture for populated or empty result documents.
function rendererFor(results) {
  // Capture title calls without requiring browser globals.
  const titleCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "" };
  // Record the exact API paths requested by the renderer.
  const apiCalls = [];
  // Return the stable empty-state markup used by the production helper.
  const emptyState = (title, detail, testId) => {
    // Preserve exact compact markup and the stable browser evidence hook.
    return html`<div class="admin-empty-state" data-testid="${safe(testId)}"><div><strong>${safe(title)}</strong><p>${safe(detail)}</p></div></div>`;
  };
  // Create the renderer through the production dependency boundary.
  const renderTests = createTestsTab({
    // Return the selected document while recording the frozen request path.
    api: async path => {
      // Record the API identity before returning the exact results envelope.
      apiCalls.push(path);
      // Return the deterministic result document.
      return { results };
    },
    emptyState,
    html,
    pre,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    view,
  });
  // Return all observable seams for deterministic assertions.
  return { apiCalls, renderTests, titleCalls, view };
}

// Verify the extracted renderer preserves exact populated structured-result output.
test("ADMIN-011 preserves populated Tests DOM output after extraction", async () => {
  // Create one deterministic exact-head-style result document with four top-level fields.
  const results = { summary: { passed: 3, failed: 0 }, source: "exact<head", ok: true, note: "A&B" };
  // Create the listener-free production renderer.
  const fixture = rendererFor(results);
  // Execute one exact Tests render.
  await fixture.renderTests();
  // Preserve the exact route and one-request behavior.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/test-results"]);
  // Preserve the localized title/subtitle call.
  assert.deepEqual(fixture.titleCalls, [["Tests", "Latest verification results."]]);
  // Build the accepted escaped preformatted result using an explicit independent fixture.
  const escapedResult = [
    "{\n  &quot;summary&quot;: {\n    &quot;passed&quot;: 3,\n    &quot;failed&quot;: 0\n  },",
    "\n  &quot;source&quot;: &quot;exact&lt;head&quot;,\n  &quot;ok&quot;: true,",
    "\n  &quot;note&quot;: &quot;A&amp;B&quot;\n}",
  ].join("");
  // Assemble the exact pre-extraction compact section around the escaped result bytes.
  const expected = [
    '<section class="admin-card"><h3>Test results</h3><details open>',
    "<summary>4 result fields</summary><pre class=\"logview\">",
    escapedResult,
    "</pre></details></section>",
  ].join("");
  // Require byte-identical populated DOM output and safe structured details.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the extracted renderer preserves the exact localized empty state.
test("ADMIN-029 preserves empty Tests DOM output after extraction", async () => {
  // Create the listener-free renderer with an empty result document.
  const fixture = rendererFor({});
  // Execute one exact Tests render.
  await fixture.renderTests();
  // Assemble the accepted compact empty-state output.
  const expected = [
    '<section class="admin-card"><h3>Test results</h3>',
    '<div class="admin-empty-state" data-testid="admin-tests-empty"><div>',
    "<strong>No test results yet</strong><p>Run verification to populate this panel.</p>",
    "</div></div></section>",
  ].join("");
  // Require byte-identical empty output and stable Browser test hook.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the per-tab source boundary remains small and frozen to the v1 endpoint.
test("TEST-145 keeps the Tests module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Tests factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/tests\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Tests implementation.
  assert.equal(ADMIN_SOURCE.includes("async function tests()"), false);
  // Require one exact frozen Tests endpoint inside the extracted module.
  assert.equal((TESTS_SOURCE.match(/\/api\/v1\/admin\/test-results/g) || []).length, 1);
  // Keep every Tests module source line within the governed review-width ceiling.
  assert.ok(Math.max(...TESTS_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
