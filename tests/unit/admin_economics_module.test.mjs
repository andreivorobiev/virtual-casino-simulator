// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Economics verification. (ADMIN-030, TEST-146)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Economics factory for listener-free summary and detail parity.
import { createEconomicsTab } from "../../web/admin/economics.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Economics source once for endpoint and line-width assertions.
const ECONOMICS_SOURCE = await readFile(`${ROOT}/web/admin/economics.js`, "utf8");
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
// Convert canonical identifiers into an observable human-readable test label.
const humanLabel = value => `Label ${value}`;
// Resolve the installed English resource values needed by the Economics renderer.
function t(key, params = {}) {
  // Interpolate the bounded-window value through the same resource boundary.
  if (key === "economics.window") return `Window ${params.count}`;
  // Interpolate the selected game into the detail subtitle.
  if (key === "economics.detailSubtitle") return `Detail ${params.game}`;
  // Interpolate all accepted detail aggregates into one deterministic sentence.
  if (key === "economics.detailSummary") return `${params.rate}|${params.edge}|${params.wagered}|${params.returned}|${params.events}`;
  // Return stable labels for every remaining Economics resource key.
  return ({
    "economics.title": "Economics",
    "economics.subtitle": "Payout-rate summary",
    "economics.heading": "Game economics",
    "economics.game": "Game",
    "economics.wagered": "Wagered",
    "economics.returned": "Returned",
    "economics.payoutRate": "Payout rate",
    "economics.houseEdge": "House edge",
    "economics.status": "Status",
    "economics.playerPositive": "Player positive",
    "economics.houseSide": "House side",
    "economics.drillDown": "Details",
    "economics.emptyTitle": "No game activity",
    "economics.emptyDetail": "No game rows exist.",
    "economics.back": "Back",
    "economics.byType": "By transaction type",
    "economics.transactionType": "Transaction type",
    "economics.count": "Count",
    "economics.netTotal": "Net total",
    "economics.noActivity": "No activity",
    "economics.noActivityDetail": "No transaction types exist.",
    "economics.recent": "Recent",
    "economics.player": "Player",
    "economics.amount": "Amount",
    "economics.noRecent": "No recent activity",
    "economics.noRecentDetail": "No recent rows exist.",
  })[key] ?? key;
}
// Render the exact compact mini-table owned by the Admin shell.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;
// Render the exact localized Admin empty-state boundary.
const emptyState = (title, detail, testId) => html`<div class="admin-empty-state" data-testid="${safe(testId)}"><div><strong>${safe(title)}</strong><p>${safe(detail)}</p></div></div>`;

// Create a minimal view that exposes the click bindings produced after each render.
function createView() {
  // Hold the currently rendered compact markup.
  let markup = "";
  // Hold the drill-down buttons discovered in the latest summary markup.
  let gameButtons = [];
  // Hold the stable Back control used by detail renders.
  const backButton = { onclick: null };
  // Return only the DOM seams required by the extracted production module.
  return {
    // Expose the latest rendered markup for exact assertions.
    get innerHTML() { return markup; },
    // Discover canonical game ids whenever the renderer replaces the view.
    set innerHTML(value) {
      // Store the exact compact markup bytes.
      markup = String(value);
      // Rebuild the summary button fixtures from canonical unescaped ids used by these tests.
      gameButtons = [...markup.matchAll(/data-economics-game="([a-z0-9_]+)"/g)].map(match => ({ dataset: { economicsGame: match[1] }, onclick: null }));
    },
    // Return the current summary controls for production click binding.
    querySelectorAll(selector) {
      // Require the exact production selector.
      assert.equal(selector, "[data-economics-game]");
      // Return the controls discovered during the latest summary render.
      return gameButtons;
    },
    // Return the deterministic Back control for production click binding.
    querySelector(selector) {
      // Require the exact production selector.
      assert.equal(selector, "#economics-back");
      // Return the stable Back fixture.
      return backButton;
    },
    // Expose the latest summary controls to individual assertions.
    gameButtons: () => gameButtons,
    // Expose the Back control to individual assertions.
    backButton,
  };
}

// Build one listener-free renderer around an exact endpoint response map.
function rendererFor(responses) {
  // Record exact API paths in call order.
  const apiCalls = [];
  // Record localized title calls without browser globals.
  const titleCalls = [];
  // Create the minimal Admin view target.
  const view = createView();
  // Resolve response factories so tests can model repeated summary reads.
  const api = async path => {
    // Record the frozen endpoint before selecting its fixture response.
    apiCalls.push(path);
    // Require every endpoint to be explicitly represented by the test.
    assert.ok(Object.hasOwn(responses, path));
    // Resolve either a static response or a caller-controlled response factory.
    return typeof responses[path] === "function" ? responses[path]() : responses[path];
  };
  // Create the production renderer through its dependency boundary.
  const renderEconomics = createEconomicsTab({
    api,
    emptyState,
    html,
    humanLabel,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return every observable seam for deterministic assertions.
  return { apiCalls, renderEconomics, titleCalls, view };
}

// Verify summary sorting, percentages, escaping, drill-down, and Back behavior.
test("ADMIN-030 preserves populated Economics summary and detail output after extraction", async () => {
  // Publish rows out of wager-volume order, including hostile labels and a zero-wager ratio.
  const summary = {
    window: 100000,
    games: [
      { game: "slots", wagered: 50, returned: 45, payout_rate: 0.9, house_edge: 0.1, player_positive: false },
      { game: "buggy_game", wagered: 200, returned: 300, payout_rate: 1.5, house_edge: -0.5, player_positive: true },
      { game: "credit_only", wagered: 0, returned: 10, payout_rate: null, house_edge: null, player_positive: false },
      { game: "hostile<script>", wagered: 25, returned: 0, payout_rate: 0, house_edge: 1, player_positive: false },
    ],
  };
  // Publish bounded populated detail with hostile player text.
  const detail = {
    wagered: 200,
    returned: 300,
    events: 2,
    payout_rate: 1.5,
    house_edge: -0.5,
    player_positive: true,
    by_transaction_type: [{ transaction_type: "BUGGY_WAGER_DEBIT", count: 1, total: -200 }],
    recent: [{ player_id: "player<script>", transaction_type: "BUGGY_PAYOUT_CREDIT", amount: 300 }],
  };
  // Create the renderer around the frozen summary and detail routes.
  const fixture = rendererFor({
    "/api/v1/admin/economics": summary,
    "/api/v1/admin/economics/buggy_game": detail,
  });
  // Render one populated summary.
  await fixture.renderEconomics();
  // Preserve the exact frozen summary route and localized title call.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/economics"]);
  // Preserve the exact summary title and subtitle.
  assert.deepEqual(fixture.titleCalls, [["Economics", "Payout-rate summary"]]);
  // Require descending wager-volume order without mutating the supplied response.
  assert.ok(fixture.view.innerHTML.indexOf("Label buggy_game") < fixture.view.innerHTML.indexOf("Label slots"));
  // Preserve player-positive styling, rate formatting, and the zero-wager dash.
  assert.match(fixture.view.innerHTML, /<tr class="danger">/);
  // Require both the 150-percent warning ratio and explicit missing-ratio glyph.
  assert.ok(fixture.view.innerHTML.includes("150.0%") && fixture.view.innerHTML.includes("—"));
  // Require hostile game text to remain escaped in label and attribute positions.
  assert.ok(fixture.view.innerHTML.includes("Label hostile&lt;script&gt;") && fixture.view.innerHTML.includes("hostile&lt;script&gt;"));
  // Find and activate the player-positive row's real drill-down binding.
  const drillDown = fixture.view.gameButtons().find(button => button.dataset.economicsGame === "buggy_game");
  // Require the selected canonical game control to exist.
  assert.ok(drillDown);
  // Render the exact selected detail through the installed handler.
  await drillDown.onclick();
  // Preserve the encoded detail route and installed-locale subtitle.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/economics", "/api/v1/admin/economics/buggy_game"]);
  // Preserve the player-positive badge and detail aggregate percentages.
  assert.ok(fixture.view.innerHTML.includes("Player positive") && fixture.view.innerHTML.includes("150.0%|-50.0%|200|300|2"));
  // Require hostile recent player text to remain escaped.
  assert.ok(fixture.view.innerHTML.includes("player&lt;script&gt;") && !fixture.view.innerHTML.includes("player<script>"));
  // Activate Back and await the live summary reload.
  await fixture.view.backButton.onclick();
  // Require Back to fetch the exact summary endpoint again.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/economics", "/api/v1/admin/economics/buggy_game", "/api/v1/admin/economics"]);
  // Require Back to restore the summary test hook.
  assert.ok(fixture.view.innerHTML.includes('data-testid="admin-economics"'));
});

// Verify an empty summary preserves the localized Browser contract.
test("ADMIN-030 preserves the Economics summary empty state", async () => {
  // Create a renderer with no game rows in the bounded window.
  const fixture = rendererFor({ "/api/v1/admin/economics": { window: 100000, games: [] } });
  // Render the empty summary.
  await fixture.renderEconomics();
  // Preserve the stable empty-state test hook and localized copy.
  assert.ok(fixture.view.innerHTML.includes('data-testid="admin-economics-empty"'));
  // Require no drill-down handlers when no game exists.
  assert.deepEqual(fixture.view.gameButtons(), []);
});

// Verify empty detail collections retain both accepted empty-state hooks.
test("ADMIN-030 preserves empty Economics detail collections", async () => {
  // Publish one summary row so its production handler opens the empty detail fixture.
  const summary = { window: 1, games: [{ game: "slots", wagered: 1, returned: 0, payout_rate: 0, house_edge: 1, player_positive: false }] };
  // Publish an empty detail response with an explicit zero-percent rate.
  const detail = { wagered: 1, returned: 0, events: 1, payout_rate: 0, house_edge: 1, player_positive: false, by_transaction_type: [], recent: [] };
  // Create the renderer around both exact endpoints.
  const fixture = rendererFor({ "/api/v1/admin/economics": summary, "/api/v1/admin/economics/slots": detail });
  // Render the summary and activate its sole drill-down.
  await fixture.renderEconomics();
  // Await the installed detail handler so both empty states have rendered.
  await fixture.view.gameButtons()[0].onclick();
  // Preserve the type-breakdown and recent-evidence empty hooks together.
  assert.ok(fixture.view.innerHTML.includes('data-testid="admin-economics-detail-empty"'));
  // Preserve the independent recent-evidence empty hook.
  assert.ok(fixture.view.innerHTML.includes('data-testid="admin-economics-recent-empty"'));
});

// Verify the extracted source boundary remains reviewable and frozen to the two v1 routes.
test("TEST-146 keeps the Admin Economics module boundary reviewable", () => {
  // Require one dispatcher import for the extracted Economics factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/economics\.js'/g) || []).length, 1);
  // Reject both retired monolith-owned Economics implementations.
  assert.equal(ADMIN_SOURCE.includes("async function economics()"), false);
  // Reject the retired monolith-owned percentage formatter.
  assert.equal(ADMIN_SOURCE.includes("const ratePercent"), false);
  // Require one exact summary endpoint inside the extracted module.
  assert.equal((ECONOMICS_SOURCE.match(/api\('\/api\/v1\/admin\/economics'\)/g) || []).length, 1);
  // Require one encoded detail endpoint inside the extracted module.
  assert.equal((ECONOMICS_SOURCE.match(/encodeURIComponent\(game\)/g) || []).length, 1);
  // Keep every Economics module source line within the governed review-width ceiling.
  assert.ok(Math.max(...ECONOMICS_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
