// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for owner session-policy verification. (SESSION-009, ADMIN-031, ADMIN-032)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Sessions factory.
import { createSessionsTab } from "../../web/admin/sessions.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/sessions.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify session and request-rate policies remain distinct after extraction.
test("SESSION-009 preserves Admin session policy surfaces after extraction", async () => {
  // Preserve stable save controls for listener binding.
  const controls = new Map();
  // Model only the DOM seams owned by the renderer.
  const view = {
    innerHTML: "",
    querySelector: (selector) => {
      // Reuse one plain control per selector.
      if (!controls.has(selector)) controls.set(selector, {});
      return controls.get(selector);
    },
  };
  // Return each independently persisted owner policy.
  const api = async path => path.endsWith("/rate-limits")
    ? { settings: { requests_per_window: 600, window_seconds: 60 } }
    : { settings: {
      enabled: true,
      idle_timeout_minutes: 30,
      absolute_timeout_hours: 12,
      warning_minutes: 5,
      admin_idle_timeout_minutes: 15,
      admin_stricter: true,
      updated_at: "now",
      updated_by: "owner-1",
    } };
  // Create and execute the production renderer.
  const renderSessions = createSessionsTab({
    api,
    html,
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    toast: () => {},
    view,
  });
  await renderSessions();
  // Preserve distinct policy cards, inputs, provenance, and save actions.
  for (const marker of [
    "admin-sessions-policy", "admin-rate-limits", "admin-sessions-enabled",
    "admin-sessions-idle", "admin-sessions-absolute", "admin-sessions-warning",
    "admin-sessions-admin-idle", "admin-sessions-admin-stricter", "admin-sessions-provenance",
    "admin-rate-limit-requests", "admin-rate-limit-window", "admin-save-sessions",
    "admin-save-rate-limits",
  ]) {
    // Require every accepted policy surface.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
});

// Verify the source boundary remains compact and route-complete.
test("ADMIN-032 keeps the Sessions module boundary reviewable", () => {
  // Require one dispatcher import and reject retired implementations.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/sessions\.js'/g) || []).length, 1);
  for (const name of ["sessions", "saveSessions", "saveRateLimits"]) {
    // Require each implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false, name);
  }
  // Preserve the exact dispatcher route.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'sessions'\) return await sessions\(\);/g) || []).length, 1);
  // Require both owner policy routes inside the extracted module.
  assert.ok(MODULE_SOURCE.includes("/api/v2/admin/session-settings"));
  assert.ok(MODULE_SOURCE.includes("/api/v2/admin/rate-limits"));
  // Keep every Sessions source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
