// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic History module verification. (TEST-145)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted History factory for listener-free DOM-output parity.
import { createHistoryTab } from "../../web/admin/history.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted History source once for endpoint and line-width assertions.
const HISTORY_SOURCE = await readFile(`${ROOT}/web/admin/history.js`, "utf8");
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
// Normalize representative game identifiers through the accepted display helper contract.
const humanLabel = value => String(value ?? "").split("_").map(part => part[0].toUpperCase() + part.slice(1)).join(" ");
// Render the existing compact table wrapper around already-rendered row strings.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;
// Format deterministic fake money through the same injected seam used by the renderer.
const formatMoney = value => `$${Number(value).toFixed(2)}`;
// Store the exact English resources required by the History fixture.
const resources = {
  "history.title": "History",
  "history.subtitle": "Cross-game results.",
  "history.heading": "Game history",
  "history.time": "Time",
  "history.player": "Player",
  "history.game": "Game",
  "history.bet": "Bet",
  "history.amount": "Amount",
  "history.payout": "Payout",
  "history.outcome": "Outcome",
  "history.balance": "Balance",
  "history.emptyTitle": "No game history yet",
  "history.emptyDetail": "Completed rounds will appear here.",
};
// Resolve only the reviewed History resources required by this fixture.
const t = key => resources[key] ?? key;

// Build one listener-free renderer fixture for populated or empty endpoint output.
function rendererFor(historyRows) {
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
  const renderHistory = createHistoryTab({
    // Return the selected rows while recording the frozen request path.
    api: async path => {
      // Record the API identity before returning an isolated fixture array.
      apiCalls.push(path);
      // Return the exact history response envelope.
      return { history: historyRows };
    },
    emptyState,
    formatMoney,
    html,
    humanLabel,
    safe,
    // Record localized title and subtitle values.
    setTitle: (...values) => titleCalls.push(values),
    t,
    table,
    view,
  });
  // Return all observable seams for deterministic assertions.
  return { apiCalls, renderHistory, titleCalls, view };
}

// Verify the extracted renderer preserves exact populated markup and newest-first order.
test("ADMIN-029 preserves populated History DOM output after extraction", async () => {
  // Define two rows in chronological endpoint order so reversal is observable.
  const historyRows = [
    { timestamp: "old", player_id: "p1", game: "bingo", bet_label: "Line", amount: 5, payout: 0, outcome: "loss", balance_after: 95 },
    { timestamp: "new<&", player_id: "p<2", game: "keno_game", bet_label: "", bet_type: "spot&6", amount: 10, payout: 25, outcome: "win>", balance_after: 110 },
  ];
  // Create the listener-free production renderer.
  const fixture = rendererFor(historyRows);
  // Execute one exact History render.
  await fixture.renderHistory();
  // Preserve the exact route and one-request behavior.
  assert.deepEqual(fixture.apiCalls, ["/api/v1/admin/history?limit=500"]);
  // Preserve the localized title/subtitle call.
  assert.deepEqual(fixture.titleCalls, [["History", "Cross-game results."]]);
  // Assemble the accepted compact output without adding formatting whitespace.
  const expected = [
    '<section class="admin-card"><h3>Game history</h3><table class="mini-table"><tr>',
    "<th>Time</th><th>Player</th><th>Game</th><th>Bet</th>",
    "<th>Amount</th><th>Payout</th><th>Outcome</th><th>Balance</th></tr>",
    "<tr><td>new&lt;&amp;</td><td>p&lt;2</td><td>Keno Game</td><td>spot&amp;6</td>",
    "<td>$10.00</td><td>$25.00</td><td>win&gt;</td><td>$110.00</td></tr>",
    "<tr><td>old</td><td>p1</td><td>Bingo</td><td>Line</td>",
    "<td>$5.00</td><td>$0.00</td><td>loss</td><td>$95.00</td></tr></table></section>",
  ].join("");
  // Require byte-identical populated DOM output and accepted escaping.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the extracted renderer preserves the exact localized empty state.
test("TEST-145 preserves empty History DOM output after extraction", async () => {
  // Create the listener-free renderer with an empty endpoint array.
  const fixture = rendererFor([]);
  // Execute one exact History render.
  await fixture.renderHistory();
  // Assemble the accepted compact empty-state output.
  const expected = [
    '<section class="admin-card"><h3>Game history</h3>',
    '<div class="admin-empty-state" data-testid="admin-history-empty"><div>',
    "<strong>No game history yet</strong><p>Completed rounds will appear here.</p>",
    "</div></div></section>",
  ].join("");
  // Require byte-identical empty output and stable Browser test hook.
  assert.equal(fixture.view.innerHTML, expected);
});

// Verify the per-tab source boundary remains small and frozen to the v1 endpoint.
test("TEST-145 keeps the History module boundary reviewable", () => {
  // Require one dispatcher import for the extracted History factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/history\.js'/g) || []).length, 1);
  // Reject the retired monolith-owned History implementation.
  assert.equal(ADMIN_SOURCE.includes("async function history()"), false);
  // Require one exact frozen History endpoint inside the extracted module.
  assert.equal((HISTORY_SOURCE.match(/\/api\/v1\/admin\/history\?limit=500/g) || []).length, 1);
  // Keep every History module source line within the governed review-width ceiling.
  assert.ok(Math.max(...HISTORY_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
