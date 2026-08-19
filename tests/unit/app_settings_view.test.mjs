// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for personal preferences and guest conversion. (USER-009, CONVERT-003)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Settings view factory.
import { createSettingsView } from "../../web/views/settings.js";
// Import the browser-independent tagged-template fixture for injected view rendering.
import { html, raw } from "./html_template_fixture.mjs";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/settings.js`, "utf8");

// Verify registered preferences/history and guest conversion survive extraction.
test("USER-009 preserves personal Settings after extraction", async () => {
  // Retain stable controls for both registered and guest renders.
  const controls = new Map();
  const control = (selector) => {
    // Reuse one ordinary mutable control per selector.
    if (!controls.has(selector)) controls.set(selector, { checked: true, textContent: "", value: "" });
    return controls.get(selector);
  };
  const view = { innerHTML: "", querySelector: selector => control(selector) };
  const messages = new Map([["personal-settings-message", { textContent: "" }]]);
  let guest = false;
  const requests = [];
  const cleared = [];
  const loginMessages = [];
  // Create the production renderer around deterministic API and session seams.
  const renderSettings = createSettingsView({
    // Bind the same escape-by-default and reviewed-fragment contract as production.
    html,
    raw,
    api: async (path, options) => {
      // Return durable settings or one account-owned history event.
      if (!options && path === "/api/v2/me/settings") {
        return { settings: { locale: "en-US", sound_enabled: true, revision: 2, updated_at: "now" } };
      }
      if (!options && path.startsWith("/api/v2/me/history")) {
        return { events: [{
          ts: "2026-08-18T00:00:00Z", game: "roulette", transaction_type: "bet",
          amount: -10, balance_after: 9990, reference: "ROUND-1",
        }] };
      }
      requests.push({ path, options });
      return { settings: { locale: "ru-RU", sound_enabled: false, revision: 3 } };
    },
    clearAuthenticatedShellState: () => cleared.push(true),
    cryptoRef: { randomUUID: () => "ACTION-KEY" },
    documentRef: { getElementById: id => messages.get(id) },
    getActive: () => "settings",
    getLocaleState: () => ({ locale: "en-US" }),
    isGuestSession: () => guest,
    localeOptionsHtml: () => '<option value="en-US">English</option><option value="ru-RU">Русский</option>',
    renderLoginGate: message => loginMessages.push(message),
    safe: value => String(value ?? ""),
    setLocale: async () => {},
    setPersonalSoundEnabled: () => {},
    t: key => key,
  });
  // Render registered preferences and account history.
  await renderSettings(view);
  assert.ok(view.innerHTML.includes('data-testid="my-settings"'));
  assert.ok(view.innerHTML.includes('data-testid="my-history"'));
  assert.ok(view.innerHTML.includes("ROUND-1"));
  // Save a new optimistic personal preference revision.
  controls.get("#personal-settings-locale").value = "ru-RU";
  control("#personal-settings-sound").checked = false;
  await controls.get("#personal-settings-form").onsubmit({ preventDefault: () => {} });
  assert.equal(requests[0].path, "/api/v2/me/settings");
  assert.equal(requests[0].options.body.revision, 2);
  assert.equal(messages.get("personal-settings-message").textContent, "settings.saved");
  // Rerender for a disposable guest and preserve explicit conversion handoff.
  guest = true;
  await renderSettings(view);
  assert.ok(view.innerHTML.includes('data-testid="guest-conversion"'));
  assert.equal(view.innerHTML.includes('data-testid="my-history"'), false);
  control("#conversion-email").value = "guest@example.com";
  control("#conversion-display-name").value = "Guest";
  control("#conversion-password").value = "strong-password";
  control("#conversion-terms").checked = true;
  controls.get("#personal-settings-locale").value = "en-US";
  await controls.get("#guest-conversion-form").onsubmit({ preventDefault: () => {} });
  assert.equal(requests.at(-1).path, "/api/v2/me/convert-guest");
  assert.deepEqual(cleared, [true]);
  assert.deepEqual(loginMessages, ["conversion.completed"]);
});

// Verify the router owns composition while the view owns settings implementation.
test("CONVERT-003 keeps the Settings view boundary reviewable", () => {
  // Require one import and reject the retired inline renderer.
  assert.equal((APP_SOURCE.match(/from '.\/views\/settings\.js'/g) || []).length, 1);
  assert.equal(APP_SOURCE.includes("async function renderMySettings("), false);
  // Preserve exact settings, history, and conversion routes in the view.
  for (const route of ["/api/v2/me/settings", "/api/v2/me/history", "/api/v2/me/convert-guest"]) {
    // Bind each reviewed route to the Settings view.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Settings view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
