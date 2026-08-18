// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the History tab from explicit Admin-shell dependencies so extraction cannot alter its rendered contract. (ADMIN-029)
export function createHistoryTab({
  api,
  emptyState,
  formatMoney,
  html,
  humanLabel,
  safe,
  setTitle,
  t,
  table,
  view,
}) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function history() {
    // Set the localized history title and subtitle.
    setTitle(t('history.title', {}, 'admin'), t('history.subtitle', {}, 'admin'));
    // Load history rows through the existing Admin endpoint.
    const data = await api('/api/v1/admin/history?limit=500');
    // Normalize rows into the existing newest-first order. (ADMIN-029)
    const rows = (data.history || []).slice().reverse().map(row => {
      // Render each escaped cell independently so source reflow cannot add output whitespace.
      const cells = [
        html`<td>${safe(row.timestamp)}</td>`,
        html`<td>${safe(row.player_id)}</td>`,
        html`<td>${safe(humanLabel(row.game))}</td>`,
        html`<td>${safe(row.bet_label || row.bet_type)}</td>`,
        html`<td>${formatMoney(Number(row.amount))}</td>`,
        html`<td>${formatMoney(Number(row.payout))}</td>`,
        html`<td>${safe(row.outcome)}</td>`,
        html`<td>${formatMoney(Number(row.balance_after))}</td>`,
      ];
      // Return the exact compact row bytes expected by the existing table helper.
      return html`<tr>${cells}</tr>`;
    });
    // Store the localized table headings in their accepted order.
    const heads = [
      t('history.time', {}, 'admin'),
      t('history.player', {}, 'admin'),
      t('history.game', {}, 'admin'),
      t('history.bet', {}, 'admin'),
      t('history.amount', {}, 'admin'),
      t('history.payout', {}, 'admin'),
      t('history.outcome', {}, 'admin'),
      t('history.balance', {}, 'admin'),
    ];
    // Preserve the localized empty state when the endpoint contains no history rows.
    const content = rows.length
      ? table(heads, rows)
      : emptyState(t('history.emptyTitle', {}, 'admin'), t('history.emptyDetail', {}, 'admin'), 'admin-history-empty');
    // Preserve the exact compact section wrapper and heading output.
    view.innerHTML = html`<section class="admin-card"><h3>${safe(t('history.heading', {}, 'admin'))}</h3>${content}</section>`;
  };
}
