// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the read-only Launch Readiness tab from explicit Admin-shell dependencies. (AUTH-016)
export function createLaunchReadinessTab({ api, html, humanLabel, isActiveTab, safe, setTitle, t, table, view }) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function launchReadiness() {
    // Set the explicit held-launch heading and helper copy before the request begins.
    setTitle(t('launch.title', {}, 'admin'), t('launch.subtitle', {}, 'admin'));
    // Read the owner-only aggregate from its additive v2 contract.
    const data = await api('/api/v2/admin/launch-readiness');
    // Stop a stale launch response from replacing another selected tab.
    if (!isActiveTab('launch')) return;
    // Render the localized status heading as one compact reviewed fragment.
    const statusHeading = html`<h3>${safe(t('launch.status', {}, 'admin'))}: ${safe(humanLabel(data.status))}</h3>`;
    // Render the non-negotiable separate-approval hold without an action control.
    const heldCopy = html`<p>${safe(t('launch.held', {}, 'admin'))}</p>`;
    // Preserve the server-authored gate order while escaping every label and result.
    const rows = (data.checks || []).map(row => html`<tr><td>${safe(humanLabel(row.id))}</td><td>${safe(humanLabel(row.status))}</td></tr>`);
    // Build the exact compact gate table through the shared Admin renderer.
    const gates = table([t('launch.check', {}, 'admin'), t('launch.result', {}, 'admin')], rows);
    // Preserve the accepted read-only card and stable Browser hooks without adding controls.
    view.innerHTML = html`<section class="admin-card" data-testid="admin-launch-readiness" data-status="${safe(data.status)}">${statusHeading}${heldCopy}${gates}</section>`;
  };
}
