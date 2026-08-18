// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Autoplay verification. (AUTO-007, AUTO-008, TEST-025)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Autoplay factory for listener-free DOM and mutation parity.
import { createAutoplayTab } from "../../web/admin/autoplay.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Autoplay source once for endpoint and line-width assertions.
const AUTOPLAY_SOURCE = await readFile(`${ROOT}/web/admin/autoplay.js`, "utf8");
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
  "autoplay.title": "Autoplay",
  "autoplay.subtitle": "Review and stop registered automatic sessions.",
  "autoplay.sessions": "Autoplay sessions",
  "autoplay.stopAll": "Stop all",
  "autoplay.stopRequested": "Stop requested",
  "autoplay.id": "ID",
  "autoplay.game": "Game",
  "autoplay.player": "Player",
  "autoplay.status": "Status",
  "autoplay.speed": "Speed",
  "autoplay.completed": "Completed",
  "autoplay.limit": "Limit",
  "autoplay.updated": "Updated",
};
// Resolve installed-locale copy through the same domain-aware call contract.
const t = key => resources[key] ?? key;
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;

// Build one listener-free renderer fixture around successive server session snapshots.
function rendererFor(sessionSnapshots) {
  // Capture localized title calls without browser globals.
  const titleCalls = [];
  // Record exact API requests made by the renderer.
  const apiCalls = [];
  // Record exact Stop All mutation calls.
  const postCalls = [];
  // Record localized completion notifications.
  const toastCalls = [];
  // Store the stable rendered Stop All control seam.
  const stopButton = { onclick: null };
  // Store the injected Admin view target and its reviewed selector behavior.
  const view = {
    innerHTML: "",
    // Return only the stable Stop All button expected by the renderer.
    querySelector: selector => selector === "#stopAllAuto" ? stopButton : null,
  };
  // Create the renderer through the production dependency boundary.
  const renderAutoplay = createAutoplayTab({
    // Return the next session snapshot while recording the frozen list endpoint.
    api: async path => {
      // Record the request before selecting deterministic fixture data.
      apiCalls.push(path);
      // Clamp repeated refreshes to the final declared snapshot.
      const index = Math.min(apiCalls.length - 1, sessionSnapshots.length - 1);
      // Return the exact Admin response envelope.
      return { sessions: sessionSnapshots[index] };
    },
    html,
    // Record the mutation route and body without a network listener.
    post: async (path, body) => postCalls.push([path, body]),
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    // Record localized success state and its accepted positive flag.
    toast: (...values) => toastCalls.push(values),
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { apiCalls, postCalls, renderAutoplay, stopButton, titleCalls, toastCalls, view };
}

// Verify extraction preserves populated session order, escaping, and compact output.
test("AUTO-007 preserves populated Admin Autoplay DOM output after extraction", async () => {
  // Create two sessions so reverse ordering and unsafe-field escaping are observable.
  const sessions = [
    {
      autoplay_id: "auto<1>",
      game_id: "roulette&red",
      player_id: 'player"one',
      status: "running",
      speed: "fast",
      rounds_completed: 2,
      round_limit: 5,
      updated_at: "2026-08-18T10:00:00Z",
    },
    {
      autoplay_id: "auto-2",
      game_id: "slots",
      player_id: "player-two",
      status: "paused",
      speed: "slow",
      rounds_completed: 1,
      round_limit: 3,
      updated_at: "2026-08-18T10:01:00Z",
    },
  ];
  // Create the listener-free production renderer.
  const fixture = rendererFor([sessions]);
  // Execute one exact Autoplay render.
  await fixture.renderAutoplay();
  // Preserve the exact frozen list route and one-request behavior.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/autoplay"]);
  // Preserve the installed-locale title and subtitle call. (I18N-014)
  assert.deepEqual(fixture.titleCalls, [["Autoplay", "Review and stop registered automatic sessions."]]);
  // Assemble the accepted compact card, localized headings, and newest-first rows independently.
  const expected = [
    '<section class="admin-card"><div class="row"><h3 style="margin-right:auto">Autoplay sessions</h3>',
    '<button id="stopAllAuto" data-testid="admin-stop-all-auto" class="danger">Stop all</button></div>',
    '<table class="mini-table"><tr><th>ID</th><th>Game</th><th>Player</th><th>Status</th>',
    '<th>Speed</th><th>Completed</th><th>Limit</th><th>Updated</th></tr>',
    '<tr><td>auto-2</td><td>slots</td><td>player-two</td><td>paused</td><td>slow</td>',
    '<td>1</td><td>3</td><td>2026-08-18T10:01:00Z</td></tr>',
    '<tr><td>auto&lt;1&gt;</td><td>roulette&amp;red</td><td>player&quot;one</td><td>running</td>',
    '<td>fast</td><td>2</td><td>5</td><td>2026-08-18T10:00:00Z</td></tr></table></section>',
  ].join("");
  // Require byte-identical output with reversed sessions and escaped server fields.
  assert.equal(fixture.view.innerHTML, expected);
  // Require the stable Stop All control to receive one callable handler.
  assert.equal(typeof fixture.stopButton.onclick, "function");
});

// Verify Stop All preserves one mutation, localized confirmation, and one refresh.
test("AUTO-008 preserves the Admin Stop All mutation and refresh sequence", async () => {
  // Create initial and refreshed snapshots around one stopped session.
  const initial = [{ autoplay_id: "auto-3", game_id: "keno", player_id: "player-three", status: "running", speed: "fast", rounds_completed: 3, round_limit: 9, updated_at: "before" }];
  // Create the converged server-owned stopped state.
  const refreshed = [{ ...initial[0], status: "stop_requested", updated_at: "after" }];
  // Create the listener-free production renderer.
  const fixture = rendererFor([initial, refreshed]);
  // Render once before invoking the bound mutation.
  await fixture.renderAutoplay();
  // Invoke the same stable Stop All control used by the browser surface.
  await fixture.stopButton.onclick();
  // Yield once so the deliberately non-blocking refresh can settle like the accepted monolith.
  await new Promise(resolve => setImmediate(resolve));
  // Require exactly one empty-body Stop All request. (AUTO-008)
  assert.deepEqual(fixture.postCalls, [["/api/v1/admin/autoplay/stop-all", {}]]);
  // Require the localized positive confirmation after the mutation succeeds.
  assert.deepEqual(fixture.toastCalls, [["Stop requested", true]]);
  // Require exactly one initial list request and one refresh request.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/autoplay", "/api/v1/admin/autoplay"]);
  // Require the refreshed server state to replace the original rendered status.
  assert.ok(fixture.view.innerHTML.includes("<td>stop_requested</td>"));
  // Require one title update per initial render and refresh.
  assert.equal(fixture.titleCalls.length, 2);
});

// Verify the per-tab source boundary remains small and frozen to both v1 endpoints.
test("TEST-025 keeps the Admin Autoplay module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Autoplay factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/autoplay\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Autoplay implementation.
  assert.equal(ADMIN_SOURCE.includes("async function autoplay()"), false);
  // Require one exact frozen list endpoint inside the extracted module.
  assert.equal((AUTOPLAY_SOURCE.match(/\/api\/v1\/admin\/autoplay'/g) || []).length, 1);
  // Require one exact frozen Stop All endpoint inside the extracted module.
  assert.equal((AUTOPLAY_SOURCE.match(/\/api\/v1\/admin\/autoplay\/stop-all/g) || []).length, 1);
  // Keep every Autoplay module source line within the governed review-width ceiling.
  assert.ok(Math.max(...AUTOPLAY_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
