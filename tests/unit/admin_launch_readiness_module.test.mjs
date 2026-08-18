// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Launch Readiness verification. (AUTH-016)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Launch Readiness factory for listener-free held-state parity.
import { createLaunchReadinessTab } from "../../web/admin/launch-readiness.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Launch Readiness source once for endpoint and line-width assertions.
const LAUNCH_SOURCE = await readFile(`${ROOT}/web/admin/launch-readiness.js`, "utf8");
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
// Resolve the installed English resource values needed by the Launch Readiness renderer.
const t = key => ({
  // Preserve the localized Admin title.
  "launch.title": "Launch readiness",
  // Preserve the localized explanatory subtitle.
  "launch.subtitle": "Read-only launch prerequisites.",
  // Preserve the localized status heading.
  "launch.status": "Launch status",
  // Preserve the explicit external-approval hold copy.
  "launch.held": "Launch remains held.",
  // Preserve the first gate-table heading.
  "launch.check": "Check",
  // Preserve the second gate-table heading.
  "launch.result": "Result",
})[key] ?? key;
// Convert canonical readiness identifiers into deterministic visible labels.
const humanLabel = value => `Label ${value}`;
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;

// Build one listener-free renderer fixture around a controllable readiness request.
function rendererFor(api, active = () => true) {
  // Record localized title calls without browser globals.
  const titleCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "unchanged" };
  // Create the renderer through the production dependency boundary.
  const renderLaunchReadiness = createLaunchReadinessTab({
    api,
    html,
    humanLabel,
    // Resolve the exact Launch activity check through the supplied fixture state.
    isActiveTab: tab => tab === "launch" && active(),
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { renderLaunchReadiness, titleCalls, view };
}

// Verify extraction preserves endpoint, ordering, escaping, localized copy, and the held-only DOM.
test("AUTH-016 preserves populated Launch Readiness output after extraction", async () => {
  // Record the exact request made by the Launch Readiness renderer.
  const apiCalls = [];
  // Publish hostile values so every visible and attribute escape remains observable.
  const data = {
    status: "held<script>",
    checks: [
      { id: "enrollment&policy", status: "ready" },
      { id: 'provider"release', status: "held<external>" },
    ],
  };
  // Create the listener-free production renderer.
  const fixture = rendererFor(async path => {
    // Record the additive v2 route before returning its contract-shaped data.
    apiCalls.push(path);
    // Return the exact readiness response fixture.
    return data;
  });
  // Execute one exact Launch Readiness render.
  await fixture.renderLaunchReadiness();
  // Preserve the exact route and one-request behavior.
  assert.deepEqual(apiCalls, ["/api/v2/admin/launch-readiness"]);
  // Preserve the installed-locale title and subtitle call.
  assert.deepEqual(fixture.titleCalls, [["Launch readiness", "Read-only launch prerequisites."]]);
  // Assemble the accepted compact card independently in server-authored gate order.
  const expected = [
    '<section class="admin-card" data-testid="admin-launch-readiness" data-status="held&lt;script&gt;">',
    '<h3>Launch status: Label held&lt;script&gt;</h3><p>Launch remains held.</p>',
    '<table class="mini-table"><tr><th>Check</th><th>Result</th></tr>',
    '<tr><td>Label enrollment&amp;policy</td><td>Label ready</td></tr>',
    '<tr><td>Label provider&quot;release</td><td>Label held&lt;external&gt;</td></tr>',
    '</table></section>',
  ].join("");
  // Require exact compact output with no formatting whitespace or reordered gates.
  assert.equal(fixture.view.innerHTML, expected);
  // Keep the visibility-only surface free from every interactive form control.
  assert.equal(/<(?:button|input|select|textarea)\b/i.test(fixture.view.innerHTML), false);
});

// Verify a late response cannot replace the content of a newer active tab.
test("AUTH-016 preserves stale Launch Readiness response suppression", async () => {
  // Hold the readiness request until the fixture has switched away from Launch.
  let resolveReadiness;
  // Track whether Launch remains the active tab.
  let active = true;
  // Create a deferred request that exposes its resolver to the test.
  const request = new Promise(resolve => { resolveReadiness = resolve; });
  // Create the listener-free renderer around the deferred request.
  const fixture = rendererFor(() => request, () => active);
  // Begin the Launch render without awaiting the server response.
  const rendering = fixture.renderLaunchReadiness();
  // Simulate navigation to a newer Admin tab before readiness resolves.
  active = false;
  // Resolve the stale response with otherwise valid held-state data.
  resolveReadiness({ status: "held", checks: [{ id: "release", status: "held" }] });
  // Wait for the renderer to apply its activity guard.
  await rendering;
  // Preserve the prior view bytes when Launch is no longer active.
  assert.equal(fixture.view.innerHTML, "unchanged");
  // Preserve the immediate title call made before the request starts.
  assert.equal(fixture.titleCalls.length, 1);
});

// Verify the per-tab source boundary remains small, read-only, and frozen to the additive v2 route.
test("AUTH-016 keeps the Launch Readiness module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Launch Readiness factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/launch-readiness\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Launch Readiness implementation.
  assert.equal(ADMIN_SOURCE.includes("async function launchReadiness()"), false);
  // Require one exact additive v2 endpoint inside the extracted module.
  assert.equal((LAUNCH_SOURCE.match(/\/api\/v2\/admin\/launch-readiness'/g) || []).length, 1);
  // Require one stale-tab guard inside the extracted module.
  assert.equal((LAUNCH_SOURCE.match(/isActiveTab\('launch'\)/g) || []).length, 1);
  // Reject mutation helpers and form controls from the visibility-only module.
  assert.equal(/\bpost\s*\(|<(?:button|input|select|textarea)\b/i.test(LAUNCH_SOURCE), false);
  // Keep every Launch Readiness module source line within the governed review-width ceiling.
  assert.ok(Math.max(...LAUNCH_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
