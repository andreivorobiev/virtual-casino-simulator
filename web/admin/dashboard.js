// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Admin Dashboard from explicit shell dependencies while preserving its frozen overview contract. (ADMIN-003, ADMIN-014)
export function createDashboardTab(dependencies) {
  // Read the reviewed dependencies once so the returned renderer remains listener-free and deterministic.
  const {
    api, emptyState, eventList, formatMoney, formatNumber, html, humanLabel, isActiveTab,
    ledgerEventLabel, safe, setTitle, t, table, view,
  } = dependencies;
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function dashboard() {
    // Set the localized Dashboard title and subtitle before the request begins.
    setTitle(t('dashboard.title', {}, 'admin'), t('dashboard.subtitle', {}, 'admin'));
    // Load the Dashboard envelope through the frozen v1 Admin endpoint.
    const data = await api('/api/v1/admin/dashboard');
    // Stop a stale Dashboard response from replacing a newer active tab.
    if (!isActiveTab('dashboard')) return;
    // Preserve the accepted active-session status set used by the Autoplay metric.
    const active = (data.autoplay_sessions || []).filter(session => {
      // Count only sessions that are active or still transitioning to or from active work.
      return ['running', 'stop_requested', 'paused', 'starting'].includes(session.status);
    });
    // Preserve the sum of all server-authored requirement status counts.
    const requirementTotal = Object.values(data.requirement_counts || {}).reduce((sum, count) => sum + count, 0);
    // Render the six overview metric cards in their accepted order.
    const metrics = [
      html`<div class="admin-card"><b>App</b><h2>${safe(data.app_version)}</h2></div>`,
      html`<div class="admin-card"><b>${safe(t('nav.players', {}, 'admin'))}</b><h2>${formatNumber(data.players.length)}</h2></div>`,
      html`<div class="admin-card"><b>Bots</b><h2>${formatNumber(data.bots.length)}</h2></div>`,
      html`<div class="admin-card"><b>${safe(t('dashboard.activeAutoplay', {}, 'admin'))}</b><h2>${formatNumber(active.length)}</h2></div>`,
      html`<div class="admin-card"><b>${safe(t('dashboard.errorsToday', {}, 'admin'))}</b><h2>${formatNumber((data.logs.errors || []).length)}</h2></div>`,
      html`<div class="admin-card"><b>${safe(t('nav.requirements', {}, 'admin'))}</b><h2>${formatNumber(requirementTotal)}</h2></div>`,
    ];
    // Keep only the latest twelve ledger records, then show newest first like the accepted Dashboard.
    const ledgerRows = (data.recent_ledger || []).slice(-12).reverse().map(row => {
      // Compose the first three cells separately so source reflow adds no visible whitespace.
      const identityCells = html`<td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(humanLabel(row.game))}</td>`;
      // Preserve the localized event label and formatted fake-token amount in the final two cells.
      const valueCells = html`<td data-testid="admin-ledger-event">${safe(ledgerEventLabel(row.transaction_type, row.game))}</td><td>${formatMoney(row.amount)}</td>`;
      // Return the exact compact row bytes used by the accepted inline renderer.
      return html`<tr>${identityCells}${valueCells}</tr>`;
    });
    // Preserve the populated table or the calm localized empty state without changing its test hook.
    const ledgerContent = ledgerRows.length ? table([
      t('ledger.columns.time', {}, 'admin'),
      t('ledger.columns.player', {}, 'admin'),
      t('ledger.columns.game', {}, 'admin'),
      t('ledger.columns.type', {}, 'admin'),
      t('ledger.columns.amount', {}, 'admin'),
    ], ledgerRows) : emptyState(
      t('ledger.emptyTitle', {}, 'admin'),
      t('ledger.emptyDetail', {}, 'admin'),
      'admin-ledger-empty',
    );
    // Preserve the recent-ledger card around the reviewed table or empty-state fragment.
    const ledgerCard = html`<section class="admin-card"><h3>${safe(t('dashboard.recentLedger', {}, 'admin'))}</h3>${ledgerContent}</section>`;
    // Preserve privacy-safe application-error summaries through the shared event-list boundary.
    const errorEvents = eventList(
      data.logs.errors,
      'No recent errors',
      'The local casino has not recorded any application errors today.',
      'admin-errors-empty',
      true,
    );
    // Preserve the recent-errors card and its localized heading.
    const errorsCard = html`<section class="admin-card"><h3>${safe(t('dashboard.recentErrors', {}, 'admin'))}</h3>${errorEvents}</section>`;
    // Compose the exact compact Dashboard topology without introducing formatting whitespace.
    view.innerHTML = html`<div class="admin-card-grid">${metrics}</div><div class="admin-split">${ledgerCard}${errorsCard}</div>`;
  };
}
