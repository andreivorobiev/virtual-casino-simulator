// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Dashboard verification. (ADMIN-003, ADMIN-014)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Dashboard factory for listener-free DOM and stale-response parity.
import { createDashboardTab } from "../../web/admin/dashboard.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Dashboard source once for endpoint and line-width assertions.
const DASHBOARD_SOURCE = await readFile(`${ROOT}/web/admin/dashboard.js`, "utf8");
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
// Resolve the installed English resource values needed by the Dashboard renderer.
const t = key => ({
  // Preserve the localized Dashboard title.
  "dashboard.title": "Dashboard",
  // Preserve the localized Dashboard subtitle.
  "dashboard.subtitle": "Overview and recent diagnostics.",
  // Preserve the localized Players metric label.
  "nav.players": "Players",
  // Preserve the localized active-Autoplay metric label.
  "dashboard.activeAutoplay": "Active autoplay",
  // Preserve the localized error metric label.
  "dashboard.errorsToday": "Errors today",
  // Preserve the localized Requirements metric label.
  "nav.requirements": "Requirements",
  // Preserve the localized recent-ledger heading.
  "dashboard.recentLedger": "Recent ledger",
  // Preserve the localized recent-errors heading.
  "dashboard.recentErrors": "Recent errors",
  // Preserve the localized ledger column headings.
  "ledger.columns.time": "Time",
  "ledger.columns.player": "Player",
  "ledger.columns.game": "Game",
  "ledger.columns.type": "Type",
  "ledger.columns.amount": "Amount",
  // Preserve the localized empty-state copy.
  "ledger.emptyTitle": "No ledger entries",
  "ledger.emptyDetail": "Play activity will appear here.",
})[key] ?? key;
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;
// Prefix deterministic numbers so every formatted metric remains observable.
const formatNumber = value => `N:${value}`;
// Prefix deterministic fake-token amounts so formatting remains observable.
const formatMoney = value => `M:${value}`;
// Convert canonical game identifiers into deterministic visible labels.
const humanLabel = value => `Label ${value}`;
// Convert canonical ledger event identifiers into deterministic visible labels.
const ledgerEventLabel = (value, game) => `Event ${value}/${game}`;

// Build one listener-free renderer fixture around a controllable Dashboard request.
function rendererFor(api, active = () => true) {
  // Record localized title calls without browser globals.
  const titleCalls = [];
  // Record empty-state calls so fallback copy and hooks stay observable.
  const emptyStateCalls = [];
  // Record event-list calls so privacy-safe error delegation stays observable.
  const eventListCalls = [];
  // Store the injected Admin view target.
  const view = { innerHTML: "unchanged" };
  // Render a deterministic empty-state fragment through the accepted signature.
  const emptyState = (...values) => {
    // Preserve every argument before returning the fixture fragment.
    emptyStateCalls.push(values);
    // Return one compact marker that composes like the production reviewed fragment.
    return html`<div data-empty="${safe(values[2])}">${safe(values[0])}|${safe(values[1])}</div>`;
  };
  // Render a deterministic error-list fragment through the accepted signature.
  const eventList = (...values) => {
    // Preserve every argument before returning the fixture fragment.
    eventListCalls.push(values);
    // Return one compact marker that exposes the accepted record count.
    return html`<div data-events="${values[0].length}">Errors</div>`;
  };
  // Create the renderer through the production dependency boundary.
  const renderDashboard = createDashboardTab({
    api,
    emptyState,
    eventList,
    formatMoney,
    formatNumber,
    html,
    humanLabel,
    // Resolve the exact Dashboard activity check through the supplied fixture state.
    isActiveTab: tab => tab === "dashboard" && active(),
    ledgerEventLabel,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { emptyStateCalls, eventListCalls, renderDashboard, titleCalls, view };
}

// Verify extraction preserves populated metrics, ledger ordering, escaping, and error delegation.
test("ADMIN-003 preserves populated Admin Dashboard DOM output after extraction", async () => {
  // Record exact requests made by the Dashboard renderer.
  const apiCalls = [];
  // Publish every metric class plus hostile ordinary values for escaping evidence.
  const data = {
    app_version: "0.9<script>",
    players: [{}, {}],
    bots: [{}],
    autoplay_sessions: [
      { status: "running" },
      { status: "stop_requested" },
      { status: "paused" },
      { status: "starting" },
      { status: "stopped" },
    ],
    logs: { errors: [{ event: "first" }, { event: "second" }] },
    requirement_counts: { PASS: 3, TODO: 2 },
    recent_ledger: [
      { ts: "old<time>", player_id: "p&1", game: "wheel<script>", transaction_type: "bet", amount: 10 },
      { ts: "new", player_id: 'p"2', game: "roulette", transaction_type: "win", amount: 25 },
    ],
  };
  // Create the listener-free production renderer.
  const fixture = rendererFor(async path => {
    // Record the frozen dashboard route before returning its exact data envelope.
    apiCalls.push(path);
    // Return the contract-shaped Admin dashboard data.
    return data;
  });
  // Execute one exact Dashboard render.
  await fixture.renderDashboard();
  // Preserve the exact frozen route and one-request behavior.
  assert.deepEqual(apiCalls, ["/api/v1/admin/dashboard"]);
  // Preserve the installed-locale title and subtitle call.
  assert.deepEqual(fixture.titleCalls, [["Dashboard", "Overview and recent diagnostics."]]);
  // Assemble the accepted compact metric cards independently.
  const metrics = [
    '<div class="admin-card"><b>App</b><h2>0.9&lt;script&gt;</h2></div>',
    '<div class="admin-card"><b>Players</b><h2>N:2</h2></div>',
    '<div class="admin-card"><b>Bots</b><h2>N:1</h2></div>',
    '<div class="admin-card"><b>Active autoplay</b><h2>N:4</h2></div>',
    '<div class="admin-card"><b>Errors today</b><h2>N:2</h2></div>',
    '<div class="admin-card"><b>Requirements</b><h2>N:5</h2></div>',
  ].join("");
  // Assemble the accepted newest-first ledger table independently.
  const ledger = [
    '<table class="mini-table"><tr><th>Time</th><th>Player</th><th>Game</th><th>Type</th><th>Amount</th></tr>',
    '<tr><td>new</td><td>p&quot;2</td><td>Label roulette</td>',
    '<td data-testid="admin-ledger-event">Event win/roulette</td><td>M:25</td></tr>',
    '<tr><td>old&lt;time&gt;</td><td>p&amp;1</td><td>Label wheel&lt;script&gt;</td>',
    '<td data-testid="admin-ledger-event">Event bet/wheel&lt;script&gt;</td><td>M:10</td></tr></table>',
  ].join("");
  // Assemble the accepted compact Dashboard topology independently.
  const expected = [
    `<div class="admin-card-grid">${metrics}</div><div class="admin-split">`,
    `<section class="admin-card"><h3>Recent ledger</h3>${ledger}</section>`,
    '<section class="admin-card"><h3>Recent errors</h3><div data-events="2">Errors</div></section></div>',
  ].join("");
  // Require exact output with no source-reflow whitespace or reordered cards and records.
  assert.equal(fixture.view.innerHTML, expected);
  // Preserve the exact privacy-safe error-list arguments.
  assert.deepEqual(fixture.eventListCalls, [[
    data.logs.errors,
    "No recent errors",
    "The local casino has not recorded any application errors today.",
    "admin-errors-empty",
    true,
  ]]);
  // A populated ledger must not invoke the empty-state renderer.
  assert.deepEqual(fixture.emptyStateCalls, []);
});

// Verify the latest-twelve boundary and localized empty state remain exact.
test("ADMIN-014 preserves Dashboard ledger bounds and empty-state behavior", async () => {
  // Build thirteen records so the oldest entry must be excluded.
  const recentLedger = Array.from({ length: 13 }, (_, index) => ({
    ts: `time-${index}`,
    player_id: `player-${index}`,
    game: `game-${index}`,
    transaction_type: `event-${index}`,
    amount: index,
  }));
  // Create the populated boundary fixture.
  const populated = rendererFor(async () => ({
    app_version: "1",
    players: [],
    bots: [],
    autoplay_sessions: [],
    logs: { errors: [] },
    requirement_counts: {},
    recent_ledger: recentLedger,
  }));
  // Render the thirteen-record fixture.
  await populated.renderDashboard();
  // Keep only twelve ledger rows.
  assert.equal((populated.view.innerHTML.match(/data-testid="admin-ledger-event"/g) || []).length, 12);
  // Keep the newest record first and exclude the oldest record completely.
  assert.ok(populated.view.innerHTML.indexOf(">time-12<") < populated.view.innerHTML.indexOf(">time-1<"));
  assert.equal(populated.view.innerHTML.includes("time-0"), false);
  // Create an empty-ledger boundary fixture.
  const empty = rendererFor(async () => ({
    app_version: "1",
    players: [],
    bots: [],
    autoplay_sessions: [],
    logs: { errors: [] },
    requirement_counts: {},
    recent_ledger: [],
  }));
  // Render the empty-ledger fixture.
  await empty.renderDashboard();
  // Preserve the localized empty-state arguments and stable Browser hook.
  assert.deepEqual(empty.emptyStateCalls, [["No ledger entries", "Play activity will appear here.", "admin-ledger-empty"]]);
  assert.ok(empty.view.innerHTML.includes('data-empty="admin-ledger-empty"'));
});

// Verify a late response cannot replace the content of a newer active tab.
test("ADMIN-014 preserves stale Dashboard response suppression", async () => {
  // Hold the Dashboard request until the fixture has switched away.
  let resolveDashboard;
  // Track whether Dashboard remains the active tab.
  let active = true;
  // Create a deferred request that exposes its resolver to the test.
  const request = new Promise(resolve => { resolveDashboard = resolve; });
  // Create the listener-free renderer around the deferred request.
  const fixture = rendererFor(() => request, () => active);
  // Begin the Dashboard render without awaiting the server response.
  const rendering = fixture.renderDashboard();
  // Simulate navigation to a newer Admin tab before the response resolves.
  active = false;
  // Resolve the stale response with otherwise valid data.
  resolveDashboard({ players: [], bots: [], logs: { errors: [] } });
  // Wait for the renderer to apply its activity guard.
  await rendering;
  // Preserve the prior view bytes when Dashboard is no longer active.
  assert.equal(fixture.view.innerHTML, "unchanged");
  // Preserve the immediate title call made before the request starts.
  assert.equal(fixture.titleCalls.length, 1);
});

// Verify the per-tab source boundary remains compact, frozen, and read-only.
test("ADMIN-003 keeps the Admin Dashboard module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Dashboard factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/dashboard\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned Dashboard implementation.
  assert.equal(ADMIN_SOURCE.includes("async function dashboard()"), false);
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'dashboard'\) return dashboard\(\);/g) || []).length, 1);
  // Require one exact frozen Dashboard endpoint inside the extracted module.
  assert.equal((DASHBOARD_SOURCE.match(/\/api\/v1\/admin\/dashboard'/g) || []).length, 1);
  // Require one stale-tab guard inside the extracted module.
  assert.equal((DASHBOARD_SOURCE.match(/isActiveTab\('dashboard'\)/g) || []).length, 1);
  // Reject mutation helpers and form controls from the read-only module.
  assert.equal(/\bpost\s*\(|<(?:button|input|select|textarea)\b/i.test(DASHBOARD_SOURCE), false);
  // Keep every Dashboard module source line within the governed review-width ceiling.
  assert.ok(Math.max(...DASHBOARD_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
