// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for deterministic Admin Players & Bots verification. (ADMIN-005, ADMIN-015)
import assert from "node:assert/strict";
// Import repository file access for exact source-boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the extracted Players & Bots factory for listener-free request and mutation parity.
import { createPlayersTab } from "../../web/admin/players.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the Admin dispatcher source once for boundary assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the extracted Players & Bots source once for route and line-width assertions.
const PLAYERS_SOURCE = await readFile(`${ROOT}/web/admin/players.js`, "utf8");
// Render nested arrays and ordinary values like the reviewed production tagged-template boundary.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact test markup without introducing source-formatting whitespace.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => {
  // Append each literal segment and rendered substitution in source order.
  return markup + segment + (index < values.length ? renderValue(values[index]) : "");
}, "");
// Preserve already-safe fixture values without changing their bytes.
const safe = value => String(value ?? "");
// Return deterministic localized fixture copy while exposing interpolation parameters.
const translate = (key, params = {}) => params.number ? `${key}:${params.number}` : key;

// Build one listener-free Players & Bots renderer with observable action controls.
function rendererFor({ api, post, saveBox = null }) {
  // Record title calls without browser globals.
  const titleCalls = [];
  // Retain the current funding control across each renderer refresh.
  const fundingButton = {};
  // Retain one optional bot save control for mutation coverage.
  const saveButton = saveBox ? {
    dataset: { bot: "bot-1" },
    closest: () => saveBox,
  } : null;
  // Provide only the DOM seams owned by the extracted renderer.
  const view = {
    innerHTML: "unchanged",
    querySelector: selector => selector === "#fund_practice_opponents" ? fundingButton : null,
    querySelectorAll: selector => selector === ".save-bot" && saveButton ? [saveButton] : [],
  };
  // Create the production renderer with deterministic formatting helpers.
  const renderPlayers = createPlayersTab({
    api,
    emptyState: (title, detail, hook) => html`<div data-empty="${hook}">${title}|${detail}</div>`,
    formatMoney: value => `money:${value}`,
    formatNumber: value => `number:${value}`,
    html,
    humanLabel: value => `label:${value}`,
    post,
    safe,
    setTitle: (...values) => titleCalls.push(values),
    t: translate,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Return every observable fixture seam.
  return { fundingButton, renderPlayers, saveButton, titleCalls, view };
}

// Return one contract-shaped populated dashboard fixture.
function populatedDashboard() {
  // Preserve the same collections consumed by the production renderer.
  return {
    players: [{ player_id: "player-1", display_name: "Player One", type: "human", balance: 25 }],
    bots: [{
      bot_id: "bot-1",
      display_name: "Bot One",
      enabled: true,
      balance: 15,
      strategies: { roulette: "red" },
      stakes: { roulette: 5 },
    }],
    bot_capabilities: {
      roulette: { supports_bots: true, strategies: [{ id: "red", label: "Red" }] },
      keno: { supports_bots: false, strategies: [] },
    },
    practice_opponents: [{ seat_id: "seat_1", display_name: "Caller", player_id: "caller-1", balance: 40 }],
    practice_opponent_activity: [{
      ts: "2026-08-18T00:00:00Z",
      player_id: "caller-1",
      round_id: "round-1",
      transaction_type: "credit",
      amount: 10,
      details: { controller_action: "fund_account" },
    }],
  };
}

// Verify populated output preserves requests, hooks, ordering, and controller controls.
test("ADMIN-005 preserves populated Players & Bots output after extraction", async () => {
  // Record the exact read route.
  const apiCalls = [];
  // Create one populated renderer fixture.
  const fixture = rendererFor({
    api: async path => {
      // Preserve the route before returning its dashboard envelope.
      apiCalls.push(path);
      // Return a fresh fixture so mutations cannot leak between assertions.
      return populatedDashboard();
    },
    post: async () => ({}),
  });
  // Execute one exact Players & Bots render.
  await fixture.renderPlayers();
  // Preserve the frozen dashboard route and localized title call.
  assert.deepEqual(apiCalls, ["/api/v1/admin/dashboard"]);
  assert.deepEqual(fixture.titleCalls, [["players.title", "players.subtitle"]]);
  // Preserve player, bot, account, activity, and funding Browser hooks.
  for (const marker of [
    'data-bot="bot-1"',
    'data-testid="practice-opponent-admin"',
    'data-testid="practice-opponent-account"',
    'data-testid="practice-opponent-activity"',
    'data-testid="fund-practice-opponents"',
  ]) {
    // Require every established marker in the completed view.
    assert.ok(fixture.view.innerHTML.includes(marker), marker);
  }
  // Preserve the filtered bot-capable game control and exclude unsupported games.
  assert.ok(fixture.view.innerHTML.includes('data-game="roulette"'));
  assert.equal(fixture.view.innerHTML.includes('data-game="keno"'), false);
});

// Verify the practice-opponent funding action keeps its exact mutation and refresh sequence.
test("ADMIN-015 preserves practice-opponent funding after extraction", async () => {
  // Record read and mutation calls independently.
  const apiCalls = [];
  const postCalls = [];
  // Create one renderer around deterministic dashboard responses.
  const fixture = rendererFor({
    api: async path => {
      // Preserve both the initial read and post-mutation refresh.
      apiCalls.push(path);
      // Return the same valid envelope for each render.
      return populatedDashboard();
    },
    post: async (...values) => postCalls.push(values),
  });
  // Render once so the action control receives its production handler.
  await fixture.renderPlayers();
  // Invoke the bound funding action and await its refresh.
  await fixture.fundingButton.onclick();
  // Preserve the exact frozen mutation route and governed practice-table payload.
  assert.deepEqual(postCalls, [["/api/v1/admin/bots/practice-opponents/fund", {
    game_id: "texas_holdem_practice_table",
  }]]);
  // Preserve exactly one refresh after the successful mutation.
  assert.deepEqual(apiCalls, ["/api/v1/admin/dashboard", "/api/v1/admin/dashboard"]);
});

// Verify bot configuration preserves its exact payload and post-save refresh.
test("ADMIN-015 preserves bot controller updates after extraction", async () => {
  // Model one rendered controller card with two supported games.
  const saveBox = {
    querySelectorAll: selector => selector === ".bot-strategy"
      ? [{ dataset: { game: "roulette" }, value: "red" }]
      : [{ dataset: { game: "roulette" }, value: "7" }],
    querySelector: selector => selector === ".bot-enabled" ? { checked: false } : null,
  };
  // Record the exact write boundary.
  const postCalls = [];
  // Create one renderer around deterministic dashboard responses.
  const fixture = rendererFor({
    api: async () => populatedDashboard(),
    post: async (...values) => postCalls.push(values),
    saveBox,
  });
  // Render once so the save control receives its production handler.
  await fixture.renderPlayers();
  // Invoke the save action and await its dashboard refresh.
  await fixture.saveButton.onclick();
  // Preserve the exact route and controller payload shape.
  assert.deepEqual(postCalls, [["/api/v1/bots/bot-1", {
    enabled: false,
    strategies: { roulette: "red" },
    stakes: { roulette: 7 },
  }]]);
});

// Verify the per-tab source boundary remains compact and route-complete.
test("ADMIN-005 keeps the Players & Bots module boundary reviewable", () => {
  // Require one dispatcher import for the extracted factory.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/players\.js'/g) || []).length, 1);
  // Reject all retired monolith-owned Players & Bots implementations.
  for (const name of ["playersBots", "fundPracticeOpponents", "saveBot"]) {
    // Require the named implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false);
  }
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'players'\) return playersBots\(\);/g) || []).length, 1);
  // Require each frozen route exactly once inside the extracted module.
  for (const route of [
    "/api/v1/admin/dashboard",
    "/api/v1/admin/bots/practice-opponents/fund",
    "/api/v1/bots/${id}",
  ]) {
    // Count the exact reviewed route for the current boundary.
    assert.equal(PLAYERS_SOURCE.split(route).length - 1, 1, route);
  }
  // Keep every Players & Bots source line within the governed review-width ceiling.
  assert.ok(Math.max(...PLAYERS_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
