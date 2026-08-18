// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for de-identified Guest Trials governance. (CONVERT-003, ADMIN-031)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Guest Trials factory.
import { createGuestsTab } from "../../web/admin/guests.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/guests.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify policy, analytics, conversion, detail, and retention controls survive extraction.
test("CONVERT-003 preserves the complete Guest Trials workspace after extraction", async () => {
  // Retain every queried control and one row action for deterministic binding checks.
  const controls = new Map();
  const detailButton = { dataset: { id: "GUEST-001" } };
  const convertButton = { dataset: { id: "GUEST-001" } };
  // Build a DOM seam that records inserted analytics cards in the visible markup.
  const control = (selector) => {
    // Reuse one ordinary mutable control per selector.
    if (!controls.has(selector)) {
      const node = {
        checked: false,
        disabled: false,
        isConnected: true,
        value: "",
        focus: () => {},
        insertAdjacentHTML: (_position, markup) => { view.innerHTML += String(markup); },
        querySelector: () => ({ tabIndex: -1, textContent: "Guest Trials" }),
        setAttribute: () => {},
      };
      controls.set(selector, node);
    }
    return controls.get(selector);
  };
  // Model only DOM seams owned by the Guest Trials renderer.
  const view = {
    innerHTML: "",
    querySelector: selector => control(selector),
    querySelectorAll: (selector) => {
      // Return stable row actions for their dedicated selectors.
      if (selector === ".guest-detail-button") return [detailButton];
      if (selector === ".guest-convert-button") return [convertButton];
      // Return no-op regions for the combined scroll-region selector.
      if (selector.includes("admin-guest-funnel")) return [control("scroll-region")];
      return [];
    },
  };
  // Return the coherent telemetry, policy, or detail response for each route.
  const api = async (path) => {
    // Return one bounded detail record and allowlisted timeline.
    if (path.includes("/sessions/")) {
      return { guest_trial: {
        analytics_id: "GUEST-001",
        locale: "en-US",
        device: "desktop",
        duration_seconds: 60,
        actions: 3,
        rounds_completed: 1,
        starting_balance: 10000,
        ending_balance: 9990,
        wagered: 10,
        returned: 0,
        net: -10,
        errors: 0,
        events: [{
          event: "first_action_accepted",
          at: "2026-08-18T00:00:00Z",
          game: "roulette",
          action_category: "bet",
          error_category: "",
          latency_bucket: "fast",
        }],
      } };
    }
    // Return the owner-governed admission policy.
    if (path.endsWith("/settings")) return { settings: { enabled: true, starting_balance: 10000 } };
    // Return one complete de-identified telemetry snapshot.
    return { guest_trials: {
      funnel: { started: 1, engaged: 1, completed_round: 1, first_action_accepted: 1 },
      funnel_rates: { first_action_accepted: 100 },
      active_now: 1,
      ended_total: 0,
      expired_total: 0,
      games: [{
        game: "roulette", trials: 1, opens: 1, actions: 3, rounds_completed: 1,
        rounds_started: 1, rounds_abandoned: 0, errors: 0, median_first_action_ms: 12,
        wagered: 10, returned: 0, net: -10, action_categories: { bet: 1 },
      }],
      recent: [{
        analytics_id: "GUEST-001", started_at: "2026-08-18T00:00:00Z", locale: "en-US",
        device: "desktop", end_reason: "", actions: 3, rounds_completed: 1,
      }],
      metrics: { average_duration_seconds: 60, error_free_rate_percent: 100, wagered: 10 },
      cleanup: { raw_retention_days: 30, aggregate_retention_days: 400 },
    } };
  };
  // Create the production renderer around deterministic fixture helpers.
  const renderGuests = createGuestsTab({
    api,
    emptyState: (title, detail, id = "") => html`<div data-testid="${id}">${title}${detail}</div>`,
    formatMoney: value => `${Number(value).toFixed(2)} tokens`,
    formatNumber: value => String(value),
    html,
    humanLabel: value => String(value ?? "").replaceAll("_", " "),
    isActiveTab: () => true,
    localeOptions: selected => html`<option value="en-US" ${selected === "en-US" ? "selected" : ""}>English</option>`,
    option: (value, label, selected) => html`<option value="${value}" ${selected === value ? "selected" : ""}>${label}</option>`,
    post: async () => ({}),
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Execute one complete coherent render.
  await renderGuests();
  // Preserve policy, conversion, filter, funnel, game, session, and retention identities.
  for (const marker of [
    "admin-guest-policy", "admin-guest-conversion", "admin-guest-filters", "admin-guest-summary",
    "admin-guest-funnel", "admin-guest-games", "admin-guest-game-detail", "admin-guest-recent",
    "admin-guest-detail", "admin-guest-cleanup-status", "admin-guest-conversion-form",
  ]) {
    // Require every accepted Guest Trials surface.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  // Preserve conversion, cleanup, policy, detail, and row-selection action bindings.
  assert.equal(typeof controls.get("#admin-guest-conversion-form").onsubmit, "function");
  assert.equal(typeof controls.get("#guest-cleanup").onclick, "function");
  assert.equal(typeof controls.get("#guest-policy-save").onclick, "function");
  assert.equal(typeof detailButton.onclick, "function");
  assert.equal(typeof convertButton.onclick, "function");
  // Follow the server-returned analytics id into the bounded detail view.
  await detailButton.onclick();
  assert.ok(controls.get("#guest-detail").innerHTML.includes("GUEST-001"));
  assert.ok(view.innerHTML.includes("admin-guest-timeline"));
});

// Verify the source boundary remains compact and route-complete.
test("ADMIN-031 keeps the Guest Trials module boundary reviewable", () => {
  // Require one dispatcher import and reject both retired implementations.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/guests\.js'/g) || []).length, 1);
  assert.equal(ADMIN_SOURCE.includes("async function guests("), false);
  assert.equal(ADMIN_SOURCE.includes("async function showGuestDetail("), false);
  // Preserve the exact dispatcher route and protected v2 routes.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'guests'\) return await guests\(\);/g) || []).length, 1);
  for (const route of ["/api/v2/admin/guest-trials?", "/settings", "/convert", "/cleanup", "/sessions/"]) {
    // Bind each reviewed route to the extracted module.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Guest Trials source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
  // Keep the final Admin dispatcher below the ticket's shell-sized target.
  assert.ok(ADMIN_SOURCE.split(/\r?\n/).length <= 500);
});
