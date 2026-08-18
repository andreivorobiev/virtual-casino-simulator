// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Ledger tab from explicit Admin-shell dependencies so this first per-tab module remains behaviorally identical. (ADMIN-027)
export function createLedgerTab({
  api,
  emptyState,
  formatMoney,
  html,
  humanLabel,
  ledgerEventLabel,
  safe,
  setTitle,
  t,
  table,
  view,
}) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function ledger() {
    // Set the localized ledger title and subtitle.
    setTitle(t('ledger.title', {}, 'admin'), t('ledger.subtitle', {}, 'admin'));
    // Load ledger rows through the existing Admin endpoint.
    const data = await api('/api/v1/admin/ledger?limit=500');
    // Store the reviewed localized table headings in their existing order.
    const heads = [
      t('ledger.columns.time', {}, 'admin'),
      t('ledger.columns.player', {}, 'admin'),
      t('ledger.columns.game', {}, 'admin'),
      t('ledger.columns.round', {}, 'admin'),
      t('ledger.columns.type', {}, 'admin'),
      t('ledger.columns.amount', {}, 'admin'),
      t('ledger.columns.before', {}, 'admin'),
      t('ledger.columns.after', {}, 'admin'),
    ];
    // Normalize missing ledger arrays before applying the existing newest-first order.
    const rows = (data.ledger || []).slice().reverse().map(row => {
      // Render each escaped cell independently so source reflow cannot add output whitespace.
      const cells = [
        html`<td>${safe(row.ts)}</td>`,
        html`<td>${safe(row.player_id)}</td>`,
        html`<td>${safe(humanLabel(row.game))}</td>`,
        html`<td>${safe(row.round_id)}</td>`,
        html`<td data-testid="admin-ledger-event">${safe(ledgerEventLabel(row.transaction_type, row.game))}</td>`,
        html`<td>${formatMoney(row.amount)}</td>`,
        html`<td>${formatMoney(row.balance_before)}</td>`,
        html`<td>${formatMoney(row.balance_after)}</td>`,
      ];
      // Return the exact compact row bytes expected by the existing table helper.
      return html`<tr>${cells}</tr>`;
    });
    // Preserve the localized empty state when the ledger contains no rows.
    const content = rows.length
      ? table(heads, rows)
      : emptyState(t('ledger.emptyTitle', {}, 'admin'), t('ledger.emptyDetail', {}, 'admin'), 'admin-ledger-empty');
    // Preserve the exact compact section wrapper and stable Admin test hooks.
    view.innerHTML = html`<section class="admin-card"><h3>${safe(t('ledger.title', {}, 'admin'))}</h3>${content}</section>`;
  };
}
