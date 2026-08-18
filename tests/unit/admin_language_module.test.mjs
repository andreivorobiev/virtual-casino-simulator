// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for manifest-driven Admin locale verification. (I18N-005, I18N-014)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Language factory and shared option helpers.
import { createLanguageTab, createLocaleOptionHelpers } from "../../web/admin/language.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/language.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");
// Render one selected-safe fixture option.
const option = (value, label, selected) => html`<option value="${value}" ${selected === value ? "selected" : ""}>${label}</option>`;
// Preserve one complete ready locale plus one metadata-only registry row.
const localeState = {
  locale: "en-US",
  formatLocale: "en-US",
  registryVersion: "1",
  fallbackLocale: "en-US",
  missingKeyCount: 0,
  registeredDomains: ["admin"],
  loadedDomains: ["admin"],
  locales: [{
    id: "en-US", nativeLabel: "English", label: "English", dir: "ltr", script: "Latn",
    formatLocale: "en-US", rank: 1, fallbackChain: ["en-US"], reviewStatus: "verified",
    voiceReady: true, uiReady: true,
  }],
  localeRegistry: [
    {
      id: "en-US", nativeLabel: "English", label: "English", dir: "ltr", script: "Latn",
      formatLocale: "en-US", rank: 1, fallbackChain: ["en-US"], reviewStatus: "verified",
      voiceReady: true, uiReady: true,
    },
    {
      id: "th-TH", nativeLabel: "ไทย", label: "Thai", dir: "ltr", script: "Thai",
      formatLocale: "th-TH", rank: 2, fallbackChain: ["en-US"], reviewStatus: "planned",
      voiceReady: false, uiReady: false,
    },
  ],
};

// Verify shared account-form options remain manifest-driven after extraction.
test("I18N-005 preserves shared locale option helpers", () => {
  // Build the production helpers around the deterministic registry fixture.
  const helpers = createLocaleOptionHelpers({
    getLocaleState: () => localeState,
    html,
    option,
    t: key => key,
  });
  // Keep UI language choices restricted to installed locales.
  assert.ok(String(helpers.localeOptions("en-US")).includes('value="en-US" selected'));
  assert.equal(String(helpers.localeOptions("en-US")).includes('value="th-TH"'), false);
  // Keep browser-default plus unique registry formatters available.
  const formats = String(helpers.formatLocaleOptions("browser"));
  assert.ok(formats.includes('value="browser" selected'));
  assert.ok(formats.includes('value="en-US"'));
  assert.ok(formats.includes('value="th-TH"'));
});

// Verify the complete Language surface and action hooks survive extraction.
test("I18N-014 preserves Language diagnostics and controls after extraction", async () => {
  // Retain stable controls for post-render binding assertions.
  const controls = new Map();
  // Model only DOM seams owned by the Language renderer.
  const view = {
    innerHTML: "",
    querySelector: (selector) => {
      // Reuse one mutable control per selector.
      if (!controls.has(selector)) controls.set(selector, { checked: false, disabled: false, value: "" });
      return controls.get(selector);
    },
  };
  // Build shared select helpers from the same locale state.
  const helpers = createLocaleOptionHelpers({ getLocaleState: () => localeState, html, option, t: key => key });
  // Create the production renderer around deterministic formatting and settings.
  const renderLanguage = createLanguageTab({
    formatDate: () => "Aug 18, 2026",
    formatLocaleOptions: helpers.formatLocaleOptions,
    formatMoney: () => "5,030.00",
    formatNumber: value => String(value),
    getLocaleSettings: () => ({ useBrowserLocale: true, language: "en-US", formatLocale: "browser" }),
    getLocaleState: () => localeState,
    html,
    localeOptions: helpers.localeOptions,
    option,
    resetLocaleSettings: async () => {},
    safe: value => String(value ?? ""),
    setLocale: async () => {},
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Execute one exact Language render.
  await renderLanguage();
  // Preserve the stable localization, registry, diagnostic, and action identities.
  for (const marker of [
    "admin-localization-foundation", "admin-locale-registry", "admin-locale-registry-entry",
    "admin-language-select", "admin-format-locale-select", "admin-locale-state",
    "admin-locale-ready-count", "admin-locale-apply", "admin-locale-save", "admin-locale-reset",
  ]) {
    // Require every accepted Language surface marker.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  // Preserve browser-resolved language disablement and every action binding.
  assert.equal(controls.get("#admin_language").disabled, false);
  for (const selector of ["#admin_apply_locale", "#admin_save_locale", "#admin_reset_locale", "#admin_preview_lobby"]) {
    // Require each explicit action to be bound after rendering.
    assert.equal(typeof controls.get(selector).onclick, "function", selector);
  }
});

// Verify the dispatcher boundary remains compact and route-complete.
test("I18N-014 keeps the Language module boundary reviewable", () => {
  // Require one dispatcher import and reject every retired implementation.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/language\.js'/g) || []).length, 1);
  for (const name of [
    "language", "languageCards", "lockedLanguageGrid", "diagnosticsTable",
    "bindLanguageControls", "saveLocale", "resetLanguage",
  ]) {
    // Require each implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false, name);
  }
  // Preserve the exact dispatcher route and shared helper binding.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'language'\) return language\(\);/g) || []).length, 1);
  assert.ok(ADMIN_SOURCE.includes("createLocaleOptionHelpers({ getLocaleState, html, option, t })"));
  // Keep every Language source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
