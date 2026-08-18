// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin System verification. (ADMIN-004, ADMIN-014, TEST-186)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted System factory for listener-free DOM and stale-response parity.
import { createSystemTab } from "../../web/admin/system.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted System source once for endpoint and line-width assertions.
const SYSTEM_SOURCE = await readFile(`${ROOT}/web/admin/system.js`, "utf8");
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
// Resolve the two installed English resource values owned by the System title boundary.
const t = key => ({ "system.title": "System", "system.subtitle": "Routes, modules, and raw overview." })[key] ?? key;
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;
// Render escaped JSON diagnostics through the same compact pre boundary.
const pre = object => html`<pre class="logview">${safe(JSON.stringify(object, null, 2))}</pre>`;

// Build one listener-free renderer fixture around a controllable dashboard request.
function rendererFor(api, active = () => true) {
  // Record localized title calls without browser globals.
  const titleCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "unchanged" };
  // Create the renderer through the production dependency boundary.
  const renderSystem = createSystemTab({
    api,
    html,
    // Resolve the exact System activity check through the supplied fixture state.
    isActiveTab: tab => tab === "system" && active(),
    pre,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { renderSystem, titleCalls, view };
}

// Verify extraction preserves canonical module order, escaping, and raw overview output.
test("ADMIN-004 preserves populated Admin System DOM output after extraction", async () => {
  // Record exact requests made by the System renderer.
  const apiCalls = [];
  // Create hostile module values so escaping remains observable.
  const data = {
    application: "0.9.5.81",
    module_revisions: [
      { module: "core<main>", revision: "10.8.0&stable" },
      { module: 'admin"ui', revision: "1.20.6" },
    ],
  };
  // Create the listener-free production renderer.
  const fixture = rendererFor(async path => {
    // Record the frozen dashboard route before returning its exact data envelope.
    apiCalls.push(path);
    // Return the contract-shaped Admin dashboard data.
    return data;
  });
  // Execute one exact System render.
  await fixture.renderSystem();
  // Preserve the exact frozen route and one-request behavior.
  assert.deepEqual(apiCalls, ["/api/v1/admin/dashboard"]);
  // Preserve the installed-locale title and subtitle call.
  assert.deepEqual(fixture.titleCalls, [["System", "Routes, modules, and raw overview."]]);
  // Assemble the accepted compact cards and server-ordered rows independently.
  const expectedPrefix = [
    '<section class="admin-card"><h3>Module revisions</h3>',
    '<table class="mini-table"><tr><th>Module</th><th>Revision</th></tr>',
    '<tr><td>core&lt;main&gt;</td><td>10.8.0&amp;stable</td></tr>',
    '<tr><td>admin&quot;ui</td><td>1.20.6</td></tr></table></section>',
    '<section class="admin-card"><h3>Raw overview</h3><pre class="logview">',
  ].join("");
  // Require exact card/table bytes before the independently escaped JSON body.
  assert.ok(fixture.view.innerHTML.startsWith(expectedPrefix));
  // Require raw diagnostics to remain escaped rather than executable HTML.
  assert.ok(fixture.view.innerHTML.includes('&quot;core&lt;main&gt;&quot;'));
  // Reject object coercion and nested-array separators like the Browser acceptance case.
  assert.equal(fixture.view.innerHTML.includes("[object Object]"), false);
  // Preserve the reviewed module row order from the server response.
  assert.ok(fixture.view.innerHTML.indexOf("core&lt;main&gt;") < fixture.view.innerHTML.indexOf("admin&quot;ui"));
});

// Verify a late response cannot replace the content of a newer active tab.
test("ADMIN-014 preserves stale System response suppression", async () => {
  // Hold the dashboard request until the fixture has switched away from System.
  let resolveDashboard;
  // Track whether System remains the active tab.
  let active = true;
  // Create a deferred request that exposes its resolver to the test.
  const request = new Promise(resolve => { resolveDashboard = resolve; });
  // Create the listener-free renderer around the deferred request.
  const fixture = rendererFor(() => request, () => active);
  // Begin the System render without awaiting the server response.
  const rendering = fixture.renderSystem();
  // Simulate navigation to a newer Admin tab before the dashboard response resolves.
  active = false;
  // Resolve the stale response with otherwise valid data.
  resolveDashboard({ module_revisions: [{ module: "core", revision: "10.8.0" }] });
  // Wait for the renderer to apply its activity guard.
  await rendering;
  // Preserve the prior view bytes when System is no longer active.
  assert.equal(fixture.view.innerHTML, "unchanged");
  // Preserve the immediate title call made before the request starts.
  assert.equal(fixture.titleCalls.length, 1);
});

// Verify the per-tab source boundary remains small and frozen to the v1 dashboard route.
test("TEST-186 keeps the Admin System module boundary reviewable", () => {
  // Require one dispatcher import for the extracted System factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/system\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned System implementation.
  assert.equal(ADMIN_SOURCE.includes("async function system()"), false);
  // Require one exact frozen dashboard endpoint inside the extracted module.
  assert.equal((SYSTEM_SOURCE.match(/\/api\/v1\/admin\/dashboard'/g) || []).length, 1);
  // Require one stale-tab guard inside the extracted module.
  assert.equal((SYSTEM_SOURCE.match(/isActiveTab\('system'\)/g) || []).length, 1);
  // Keep every System module source line within the governed review-width ceiling.
  assert.ok(Math.max(...SYSTEM_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
