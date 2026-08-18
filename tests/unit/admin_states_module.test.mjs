// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Game States verification. (TEST-145)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Game States factory for listener-free DOM-output parity.
import { createStatesTab } from "../../web/admin/states.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Game States source once for endpoint and line-width assertions.
const STATES_SOURCE = await readFile(`${ROOT}/web/admin/states.js`, "utf8");
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
// Store exact English resources used by the listener-free fixture.
const resources = {
  "states.title": "Game states",
  "states.subtitle": "Inspect isolated game state files.",
  "states.heading": "State documents",
  "states.state": "State",
  "states.keys": "Keys",
  "states.detail": "Detail",
  "states.view": "View state",
  "states.emptyTitle": "No game states yet",
  "states.emptyDetail": "Play a game to create isolated state.",
};
// Resolve installed-locale copy through the same domain-aware call contract.
const t = key => resources[key] ?? key;
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;

// Build one listener-free renderer fixture around the selected state registry.
function rendererFor(states) {
  // Capture localized title calls without browser globals.
  const titleCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "" };
  // Record exact API requests made by the renderer.
  const apiCalls = [];
  // Return the stable empty-state markup used by the production helper.
  const emptyState = (title, detail, testId) => {
    // Preserve exact compact markup and the stable Browser evidence hook.
    return html`<div class="admin-empty-state" data-testid="${safe(testId)}"><div><strong>${safe(title)}</strong><p>${safe(detail)}</p></div></div>`;
  };
  // Create the renderer through the production dependency boundary.
  const renderStates = createStatesTab({
    // Return the selected registry while recording the frozen endpoint.
    api: async path => {
      // Record the request before returning deterministic fixture data.
      apiCalls.push(path);
      // Return the exact Admin response envelope.
      return { states };
    },
    emptyState,
    html,
    pre,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { apiCalls, renderStates, titleCalls, view };
}

// Verify the extracted renderer preserves populated nested-state output.
test("ADMIN-009 preserves populated Game States DOM output after extraction", async () => {
  // Create one unsafe identity with two nested keys for escaping and count coverage.
  const states = { "bingo/<player>&": { state: { phase: 'called "7"', drawn: [1, 7] } } };
  // Create the listener-free production renderer.
  const fixture = rendererFor(states);
  // Execute one exact Game States render.
  await fixture.renderStates();
  // Preserve the exact frozen route and one-request behavior.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/game-states"]);
  // Preserve the localized title and subtitle call.
  assert.deepEqual(fixture.titleCalls, [["Game states", "Inspect isolated game state files."]]);
  // Assemble the accepted compact table and escaped detail output independently.
  const expected = [
    '<section class="admin-card"><h3>State documents</h3><table class="mini-table"><tr>',
    "<th>State</th><th>Keys</th><th>Detail</th></tr><tr><td>bingo/&lt;player&gt;&amp;</td><td>2</td><td>",
    "<details><summary>View state</summary><pre class=\"logview\">{\n  &quot;phase&quot;: &quot;called \\&quot;7\\&quot;&quot;,",
    "\n  &quot;drawn&quot;: [\n    1,\n    7\n  ]\n}</pre></details></td></tr></table></section>",
  ].join("");
  // Require byte-identical populated DOM output, safe identity, and escaped JSON detail.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the extracted renderer preserves the exact localized empty state.
test("ADMIN-029 preserves empty Game States DOM output after extraction", async () => {
  // Create the renderer with no returned state registry.
  const fixture = rendererFor(undefined);
  // Execute one exact Game States render.
  await fixture.renderStates();
  // Assemble the accepted compact empty-state output.
  const expected = [
    '<section class="admin-card"><h3>State documents</h3>',
    '<div class="admin-empty-state" data-testid="admin-game-states-empty"><div>',
    "<strong>No game states yet</strong><p>Play a game to create isolated state.</p>",
    "</div></div></section>",
  ].join("");
  // Require byte-identical empty output and stable Browser evidence hook.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the per-tab source boundary remains small and frozen to the v1 endpoint.
test("TEST-145 keeps the Game States module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Game States factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/states\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Game States implementation.
  assert.equal(ADMIN_SOURCE.includes("async function states()"), false);
  // Require one exact frozen Game States endpoint inside the extracted module.
  assert.equal((STATES_SOURCE.match(/\/api\/v1\/admin\/game-states/g) || []).length, 1);
  // Keep every Game States module source line within the governed review-width ceiling.
  assert.ok(Math.max(...STATES_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
