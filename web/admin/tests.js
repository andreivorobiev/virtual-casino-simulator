// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Tests tab from explicit Admin-shell dependencies so extraction cannot alter its diagnostics contract. (ADMIN-011, ADMIN-029)
export function createTestsTab({ api, emptyState, html, pre, safe, setTitle, t, view }) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function tests() {
    // Set the localized tests title and subtitle.
    setTitle(t('tests.title', {}, 'admin'), t('tests.subtitle', {}, 'admin'));
    // Load latest test results through the existing Admin endpoint.
    const data = await api('/api/v1/admin/test-results');
    // Normalize the recorded result document so an empty run history is explicit. (ADMIN-029)
    const results = data.results || {};
    // Preserve the readable expandable evidence or localized empty-state branch. (ADMIN-029)
    const content = Object.keys(results).length
      ? html`<details open><summary>${safe(t('tests.resultFields', { count: Object.keys(results).length }, 'admin'))}</summary>${pre(results)}</details>`
      : emptyState(t('tests.emptyTitle', {}, 'admin'), t('tests.emptyDetail', {}, 'admin'), 'admin-tests-empty');
    // Preserve the exact compact section wrapper and heading output.
    view.innerHTML = html`<section class="admin-card"><h3>${safe(t('tests.heading', {}, 'admin'))}</h3>${content}</section>`;
  };
}
