// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Requirements tab from explicit Admin-shell dependencies so extraction preserves its coverage contract. (ADMIN-010, ADMIN-021)
export function createRequirementsTab({ api, html, safe, setTitle, t, table, view }) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function requirements() {
    // Set the existing localized Requirements title and subtitle. (I18N-014)
    setTitle(t('nav.requirements', {}, 'admin'), t('requirements.subtitle', {}, 'admin'));
    // Load requirement coverage through the frozen Admin endpoint.
    const data = await api('/api/v1/admin/requirements');
    // Resolve the five localized column headings in their accepted order. (I18N-014)
    const headings = ['id', 'module', 'description', 'status', 'tests'].map(key => t(`requirements.${key}`, {}, 'admin'));
    // Preserve source order while escaping every requirement field and combined test identity.
    const rows = (data.requirements || []).map(requirement => {
      // Keep API tests before Browser tests exactly as the accepted monolith did.
      const testIds = [...(requirement.api_tests || []), ...(requirement.browser_tests || [])].join(', ');
      // Split the compact row only at substitution boundaries so rendered bytes stay unchanged.
      const identity = html`<td>${safe(requirement.id)}</td><td>${safe(requirement.module)}</td><td>${safe(requirement.description)}</td>`;
      // Render status and ordered evidence identities without exposing unescaped registry data.
      const coverage = html`<td>${safe(requirement.status)}</td><td>${safe(testIds)}</td>`;
      // Return the exact compact table row expected by the Admin shell.
      return html`<tr>${identity}${coverage}</tr>`;
    });
    // Preserve the exact compact Requirements card and localized heading output.
    view.innerHTML = html`<section class="admin-card"><h3>${safe(t('nav.requirements', {}, 'admin'))}</h3>${table(headings, rows)}</section>`;
  };
}
