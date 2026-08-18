// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Telemetry verification. (ADMIN-008, ADMIN-017)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Telemetry factory for listener-free DOM and request parity.
import { createTelemetryTab } from "../../web/admin/telemetry.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Telemetry source once for route and line-width assertions.
const TELEMETRY_SOURCE = await readFile(`${ROOT}/web/admin/telemetry.js`, "utf8");
// Render nested arrays and ordinary values like the reviewed production tagged-template boundary.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact test markup without introducing source-formatting whitespace.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => {
  // Append each literal segment and rendered substitution in source order.
  return markup + segment + (index < values.length ? renderValue(values[index]) : "");
}, "");

// Build one listener-free Telemetry renderer fixture around a supplied API boundary.
function rendererFor(api) {
  // Record title calls without browser globals.
  const titleCalls = [];
  // Record event-list calls so ordering, copy, hooks, and privacy flags stay observable.
  const eventListCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "unchanged" };
  // Render deterministic fragments while retaining every accepted event-list argument.
  const eventList = (...values) => {
    // Preserve the complete call before returning its compact marker.
    eventListCalls.push(values);
    // Return one stable fragment keyed by the accepted Browser hook.
    return html`<div data-events="${values[3]}">${values[0].length}</div>`;
  };
  // Create the renderer through the production dependency boundary.
  const renderTelemetry = createTelemetryTab({
    api,
    eventList,
    html,
    // Record the accepted title and subtitle call.
    setTitle: (...values) => titleCalls.push(values),
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { eventListCalls, renderTelemetry, titleCalls, view };
}

// Verify populated records preserve request, delegation, privacy, and DOM order.
test("ADMIN-008 preserves populated Admin Telemetry output after extraction", async () => {
  // Record the exact request sequence.
  const apiCalls = [];
  // Assign distinct record arrays so each delegation remains independently observable.
  const records = {
    app: [{ event: "app-one" }, { event: "app-two" }],
    errors: [{ event: "error-one", traceback: "must stay hidden" }],
    client: [{ event: "client-one" }],
  };
  // Return the fixture matching each frozen kind query.
  const fixture = rendererFor(async path => {
    // Preserve each exact path before deriving its fixture kind.
    apiCalls.push(path);
    // Extract only the reviewed kind selector from the exact query.
    const kind = new URL(path, "https://example.invalid").searchParams.get("kind");
    // Return the contract-shaped log envelope.
    return { logs: records[kind] };
  });
  // Execute one exact Telemetry render.
  await fixture.renderTelemetry();
  // Preserve the sequential app, error, and browser request order.
  assert.deepEqual(apiCalls, [
    "/api/v1/admin/logs?kind=app&limit=200",
    "/api/v1/admin/logs?kind=errors&limit=200",
    "/api/v1/admin/logs?kind=client&limit=200",
  ]);
  // Preserve the accepted immediate title and subtitle.
  assert.deepEqual(fixture.titleCalls, [["Telemetry", "Application, error, and browser-client logs."]]);
  // Preserve ordinary application delegation without the technical-detail flag.
  assert.deepEqual(fixture.eventListCalls[0], [
    records.app,
    "No application events",
    "Application activity will appear here as the local service is used.",
    "admin-app-events",
  ]);
  // Preserve privacy-safe server-error delegation as the only flagged stream.
  assert.deepEqual(fixture.eventListCalls[1], [
    records.errors,
    "No error events",
    "No server errors have been recorded for the current day.",
    "admin-error-events",
    true,
  ]);
  // Preserve ordinary browser delegation without the technical-detail flag.
  assert.deepEqual(fixture.eventListCalls[2], [
    records.client,
    "No browser events",
    "Browser activity will appear here after a client sends telemetry.",
    "admin-client-events",
  ]);
  // Preserve the exact compact three-card topology and pane order.
  assert.equal(fixture.view.innerHTML, [
    '<div class="admin-split"><section class="admin-card"><h3>Application events</h3>',
    '<div data-events="admin-app-events">2</div></section>',
    '<section class="admin-card"><h3>Error events</h3>',
    '<div data-events="admin-error-events">1</div></section></div>',
    '<section class="admin-card"><h3>Browser events</h3>',
    '<div data-events="admin-client-events">1</div></section>',
  ].join(""));
});

// Verify empty streams preserve all calm-state copy and stable Browser hooks.
test("ADMIN-017 preserves all Telemetry empty-state delegations", async () => {
  // Return one empty envelope for every exact kind request.
  const fixture = rendererFor(async () => ({ logs: [] }));
  // Render the empty Telemetry state.
  await fixture.renderTelemetry();
  // Preserve three delegations and their stable hooks in pane order.
  assert.deepEqual(fixture.eventListCalls.map(call => call[3]), [
    "admin-app-events",
    "admin-error-events",
    "admin-client-events",
  ]);
  // Preserve technical-detail suppression only for server errors.
  assert.deepEqual(fixture.eventListCalls.map(call => call[4]), [undefined, true, undefined]);
  // Preserve the calm-state detail copy for all three streams.
  assert.deepEqual(fixture.eventListCalls.map(call => call[2]), [
    "Application activity will appear here as the local service is used.",
    "No server errors have been recorded for the current day.",
    "Browser activity will appear here after a client sends telemetry.",
  ]);
});

// Verify request failure behavior remains sequential and leaves the active view untouched.
test("ADMIN-008 preserves Telemetry request failure propagation", async () => {
  // Record requests until the server-error request fails.
  const apiCalls = [];
  // Create one stable failure object for identity-safe propagation.
  const failure = new Error("bounded fixture failure");
  // Reject only the second request like the accepted sequential renderer.
  const fixture = rendererFor(async path => {
    // Preserve the path before choosing its fixture result.
    apiCalls.push(path);
    // Fail at the server-error stream so the browser request never begins.
    if (path.includes("kind=errors")) throw failure;
    // Return one valid application envelope before the failure.
    return { logs: [] };
  });
  // Require the exact failure to escape into the existing dispatcher error boundary.
  await assert.rejects(fixture.renderTelemetry(), error => error === failure);
  // Preserve sequential short-circuiting before the browser-client request.
  assert.deepEqual(apiCalls, [
    "/api/v1/admin/logs?kind=app&limit=200",
    "/api/v1/admin/logs?kind=errors&limit=200",
  ]);
  // Preserve the prior view when the renderer cannot complete all three streams.
  assert.equal(fixture.view.innerHTML, "unchanged");
  // Do not render partial event panes before all requests succeed.
  assert.deepEqual(fixture.eventListCalls, []);
});

// Verify the per-tab source boundary remains compact, frozen, and read-only.
test("ADMIN-017 keeps the Admin Telemetry module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Telemetry factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/telemetry\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Telemetry implementation.
  assert.equal(ADMIN_SOURCE.includes("async function telemetry()"), false);
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'telemetry'\) return telemetry\(\);/g) || []).length, 1);
  // Require each frozen route once inside the extracted module.
  for (const kind of ["app", "errors", "client"]) {
    // Count the exact bounded route for the current reviewed stream.
    assert.equal((TELEMETRY_SOURCE.match(new RegExp(`/api/v1/admin/logs\\?kind=${kind}&limit=200`, "g")) || []).length, 1);
  }
  // Reject mutation helpers and form controls from the read-only module.
  assert.equal(/\bpost\s*\(|\bmethod\s*:\s*['"](?:POST|PATCH|DELETE)|<(?:button|input|select|textarea)\b/i.test(TELEMETRY_SOURCE), false);
  // Keep every Telemetry module source line within the governed review-width ceiling.
  assert.ok(Math.max(...TELEMETRY_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
