// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for privacy-bounded Feedback triage. (ADMIN-025)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Feedback factory.
import { createFeedbackTab } from "../../web/admin/feedback.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/feedback.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify the inbox and detail workspace preserve their stable privacy-safe controls.
test("ADMIN-025 preserves Feedback inbox and detail after extraction", async () => {
  // Retain one mutable control per selector and one returned report button.
  const controls = new Map();
  const reportButton = { dataset: { feedbackId: "REPORT1" } };
  // Model only DOM seams owned by the Feedback renderer.
  const view = {
    innerHTML: "",
    querySelector: (selector) => {
      // Reuse one ordinary control for binding and value reads.
      if (!controls.has(selector)) controls.set(selector, { value: "", hidden: true });
      return controls.get(selector);
    },
    querySelectorAll: selector => selector === "[data-feedback-id]" ? [reportButton] : [],
  };
  // Return canonical inbox or detail data according to the requested route.
  const api = async (path) => {
    // Return one canonical detail record for the selected report.
    if (path.endsWith("/REPORT1")) {
      return { report: {
        report_id: "REPORT1",
        reference: "FB-0001",
        priority: "P1",
        status: "new",
        category: "bug",
        impact: "blocked",
        reporter_reference: "USR-0000000000000001",
        summary: "Escaped summary",
        actual: "Actual behavior",
        expected: "Expected behavior",
        context: { route: "/roulette" },
        attachments: [],
      } };
    }
    // Return one attachment-free inbox row and governed filter values.
    return {
      priorities: ["P1", "P2", "P3"],
      statuses: ["new", "resolved"],
      categories: ["bug"],
      impacts: ["blocked"],
      reports: [{
        report_id: "REPORT1",
        reference: "FB-0001",
        priority: "P1",
        status: "new",
        category: "bug",
        impact: "blocked",
        reporter_reference: "USR-0000000000000001",
        summary: "Escaped summary",
        route: "/roulette",
        created_at: "2026-08-18T00:00:00Z",
      }],
    };
  };
  // Create the production renderer around deterministic fixture helpers.
  const renderFeedback = createFeedbackTab({
    api,
    emptyState: (title, detail, id) => html`<div data-testid="${id}">${title}${detail}</div>`,
    getLocaleState: () => ({ locales: [{ id: "en-US" }] }),
    html,
    humanLabel: value => String(value),
    isActiveTab: () => true,
    option: (value, label, selected) => html`<option value="${value}" ${selected === value ? "selected" : ""}>${label}</option>`,
    post: async () => ({ cleanup: { deleted: 0 } }),
    safe: value => String(value ?? ""),
    setTitle: () => {},
    t: key => key,
    table: (heads, rows) => html`<table data-heads="${heads.join('|')}">${rows}</table>`,
    toast: () => {},
    view,
  });
  // Execute one canonical inbox render.
  await renderFeedback();
  // Preserve filter, retention, table, and report-navigation identities.
  for (const marker of [
    "admin-feedback-inbox", "feedback-priority-filter", "feedback-created-from-filter",
    "feedback-apply-filters", "feedback-cleanup", "feedback-table-scroll", "data-feedback-id",
  ]) {
    // Require every accepted inbox marker.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  assert.equal(typeof controls.get("#feedback-apply-filters").onclick, "function");
  assert.equal(typeof controls.get("#feedback-cleanup").onclick, "function");
  assert.equal(typeof reportButton.onclick, "function");
  // Follow the server-returned identity into the canonical detail renderer.
  await reportButton.onclick();
  // Preserve escaped report prose, local-only draft, export, and delete controls.
  for (const marker of [
    "admin-feedback-detail", "Escaped summary", "feedback-detail-priority", "feedback-admin-notes",
    "feedback-github-url", "feedback-save", "feedback-draft", "feedback-export", "feedback-delete",
    "feedback-github-draft", "feedback.admin.noScreenshots",
  ]) {
    // Require every accepted detail marker.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
});

// Verify the source boundary remains compact and route-complete.
test("ADMIN-025 keeps the Feedback module boundary reviewable", () => {
  // Require one dispatcher import and reject every retired implementation.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/feedback\.js'/g) || []).length, 1);
  for (const name of ["feedbackReports", "feedbackDetail", "feedbackSelect", "feedbackActionKey"]) {
    // Require each implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false, name);
  }
  // Preserve the exact dispatcher route and all five Feedback endpoints.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'feedback'\) return await feedbackReports\(\);/g) || []).length, 1);
  for (const route of ["/api/v2/admin/feedback/reports", "/github-draft", "/export", "/cleanup"]) {
    // Bind each reviewed route to the new module.
    assert.ok(MODULE_SOURCE.includes(route), route);
  }
  // Keep every Feedback source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
