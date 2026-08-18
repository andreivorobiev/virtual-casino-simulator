// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the System tab from explicit Admin-shell dependencies while preserving canonical diagnostics. (ADMIN-004, ADMIN-014)
export function createSystemTab({ api, html, isActiveTab, pre, safe, setTitle, t, table, view }) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function system() {
    // Set the localized System title and subtitle before the request begins.
    setTitle(t('system.title', {}, 'admin'), t('system.subtitle', {}, 'admin'));
    // Load canonical module revisions and raw overview data through the frozen Admin endpoint.
    const data = await api('/api/v1/admin/dashboard');
    // Stop a stale response from replacing the content of a newer active Admin tab.
    if (!isActiveTab('system')) return;
    // Preserve canonical server order while escaping each module identity and revision. (TEST-186)
    const rows = (data.module_revisions || []).map(module => html`<tr><td>${safe(module.module)}</td><td>${safe(module.revision)}</td></tr>`);
    // Preserve the exact compact module table followed by the escaped raw overview projection.
    view.innerHTML = html`<section class="admin-card"><h3>Module revisions</h3>${table(['Module', 'Revision'], rows)}</section><section class="admin-card"><h3>Raw overview</h3>${pre(data)}</section>`;
  };
}
