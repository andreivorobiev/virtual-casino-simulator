// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Game States tab from explicit Admin-shell dependencies so extraction preserves its diagnostics contract. (ADMIN-009, ADMIN-018, ADMIN-029)
export function createStatesTab({ api, emptyState, html, pre, safe, setTitle, t, table, view }) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function states() {
    // Set the localized state-diagnostics title and subtitle.
    setTitle(t('states.title', {}, 'admin'), t('states.subtitle', {}, 'admin'));
    // Load game states through the frozen Admin endpoint.
    const data = await api('/api/v1/admin/game-states');
    // Normalize per-game and per-player state documents into stable insertion-order rows. (ADMIN-029)
    const entries = Object.entries(data.states || {});
    // Resolve the three localized column headings in their accepted order.
    const headings = ['state', 'keys', 'detail'].map(key => t(`states.${key}`, {}, 'admin'));
    // Preserve each escaped state identity, nested-key count, and expandable JSON detail.
    const rows = entries.map(([key, info]) => {
      // Count only keys in the nested state object, matching the accepted diagnostic projection.
      const keyCount = Object.keys(info.state || {}).length;
      // Build the trusted detail fragment without adding source-formatting whitespace to the DOM.
      const detail = html`<details><summary>${safe(t('states.view', {}, 'admin'))}</summary>${pre(info.state)}</details>`;
      // Return the exact compact state row with every server-owned identity escaped.
      return html`<tr><td>${safe(key)}</td><td>${safe(keyCount)}</td><td>${detail}</td></tr>`;
    });
    // Preserve expandable content or the exact localized empty-state branch. (ADMIN-029)
    const content = entries.length
      ? table(headings, rows)
      : emptyState(t('states.emptyTitle', {}, 'admin'), t('states.emptyDetail', {}, 'admin'), 'admin-game-states-empty');
    // Preserve the exact compact Game States card and localized heading output.
    view.innerHTML = html`<section class="admin-card"><h3>${safe(t('states.heading', {}, 'admin'))}</h3>${content}</section>`;
  };
}
