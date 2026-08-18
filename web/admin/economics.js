// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Economics tab from explicit Admin-shell dependencies while preserving its summary and drill-down output. (ADMIN-030)
export function createEconomicsTab({ api, emptyState, html, humanLabel, safe, setTitle, t, table, view }) {
  // Format a payout ratio as a readable percentage or a dash when no wagers anchor it.
  const ratePercent = value => (value === null || value === undefined) ? '—' : `${(value * 100).toFixed(1)}%`;

  // Render one game's payout-rate breakdown and recent bounded evidence.
  async function economicsDetail(game) {
    // Set the detail title while retaining the canonical game label.
    setTitle(t('economics.title', {}, 'admin'), t('economics.detailSubtitle', { game: humanLabel(game) }, 'admin'));
    // Load the single-game detail through the allowlisted route segment.
    const data = await api(`/api/v1/admin/economics/${encodeURIComponent(game)}`);
    // Build the bounded transaction-type rows without changing their server-provided order.
    const byTypeRows = (data.by_transaction_type || []).map(row => {
      // Render each compact cell separately so the exact DOM stays readable in source review.
      const cells = [html`<td>${safe(humanLabel(row.transaction_type))}</td>`, html`<td>${safe(row.count)}</td>`, html`<td>${safe(row.total)}</td>`];
      // Return one compact transaction-type row with no source-formatting whitespace.
      return html`<tr>${cells}</tr>`;
    });
    // Preserve the accepted transaction-type table headings.
    const byTypeHeads = [t('economics.transactionType', {}, 'admin'), t('economics.count', {}, 'admin'), t('economics.netTotal', {}, 'admin')];
    // Preserve the existing empty-state contract when no transaction-type evidence exists.
    const byType = byTypeRows.length ? table(byTypeHeads, byTypeRows) : emptyState(
      // Keep the localized no-activity title, detail, and stable Browser test hook.
      t('economics.noActivity', {}, 'admin'), t('economics.noActivityDetail', {}, 'admin'), 'admin-economics-detail-empty'
    );
    // Build the bounded recent-event rows without exposing unescaped player or transaction values.
    const recentRows = (data.recent || []).map(row => {
      // Render each compact cell separately so hostile player and event values remain escaped.
      const cells = [html`<td>${safe(row.player_id)}</td>`, html`<td>${safe(humanLabel(row.transaction_type))}</td>`, html`<td>${safe(row.amount)}</td>`];
      // Return one compact recent-event row with no source-formatting whitespace.
      return html`<tr>${cells}</tr>`;
    });
    // Preserve the accepted recent-event table headings.
    const recentHeads = [t('economics.player', {}, 'admin'), t('economics.transactionType', {}, 'admin'), t('economics.amount', {}, 'admin')];
    // Preserve the existing empty-state contract when no recent evidence exists.
    const recent = recentRows.length ? table(recentHeads, recentRows) : emptyState(
      // Keep the localized no-recent title, detail, and stable Browser test hook.
      t('economics.noRecent', {}, 'admin'), t('economics.noRecentDetail', {}, 'admin'), 'admin-economics-recent-empty'
    );
    // Build the deterministic Back control separately so compact DOM bytes remain reviewable.
    const back = html`<button id="economics-back" type="button">${safe(t('economics.back', {}, 'admin'))}</button>`;
    // Build the canonical game badge through the shared escape boundary.
    const gameBadge = html`<span class="badge">${safe(humanLabel(game))}</span>`;
    // Add the existing danger badge only for a player-positive result.
    const warningBadge = data.player_positive ? html`<span class="badge danger">${safe(t('economics.playerPositive', {}, 'admin'))}</span>` : '';
    // Join the Back control and badges in the exact established row wrapper.
    const header = html`<div class="row">${back}${gameBadge}${warningBadge}</div>`;
    // Build the localized aggregate summary from the accepted percentage formatting.
    const summary = html`<p>${safe(t('economics.detailSummary', {
      // Keep the payout rate and house edge as localized percentage strings.
      rate: ratePercent(data.payout_rate), edge: ratePercent(data.house_edge),
      // Keep the raw bounded totals and event count in the existing localized formatter input.
      wagered: data.wagered, returned: data.returned, events: data.events,
    }, 'admin'))}</p>`;
    // Build each localized section heading separately to keep the rendered output compact.
    const headings = [html`<h3>${safe(t('economics.byType', {}, 'admin'))}</h3>`, html`<h3>${safe(t('economics.recent', {}, 'admin'))}</h3>`];
    // Render aggregate, type breakdown, and recent events with a deterministic back control.
    view.innerHTML = html`<section class="admin-card" data-testid="admin-economics-detail">${header}${summary}${headings[0]}${byType}${headings[1]}${recent}</section>`;
    // Return to the live summary when the operator activates Back.
    view.querySelector('#economics-back').onclick = () => economics();
  }

  // Render continuous per-game payout-rate telemetry with a drill-down.
  async function economics() {
    // Set the localized economics title and subtitle.
    setTitle(t('economics.title', {}, 'admin'), t('economics.subtitle', {}, 'admin'));
    // Load aggregated payout rates from the owner-visible Admin endpoint.
    const data = await api('/api/v1/admin/economics');
    // Sort active games by wager volume for operator scanning.
    const games = (data.games || []).slice().sort((a, b) => (b.wagered || 0) - (a.wagered || 0));
    // Build escaped summary rows with the existing player-positive warning class and drill-down controls.
    const rows = games.map(row => {
      // Resolve the existing warning class without changing house-side row markup.
      const warning = row.player_positive ? html` class="danger"` : '';
      // Render the game identity and bounded aggregate values through the escape boundary.
      const values = [humanLabel(row.game), row.wagered, row.returned, ratePercent(row.payout_rate), ratePercent(row.house_edge)];
      // Render each aggregate cell independently so source review never changes compact DOM bytes.
      const cells = values.map(value => html`<td>${safe(value)}</td>`);
      // Append the localized status and exact drill-down control after the aggregate cells.
      cells.push(html`<td>${safe(t(row.player_positive ? 'economics.playerPositive' : 'economics.houseSide', {}, 'admin'))}</td>`);
      // Keep the canonical game id escaped in its stable data attribute.
      cells.push(html`<td><button type="button" data-economics-game="${safe(row.game)}">${safe(t('economics.drillDown', {}, 'admin'))}</button></td>`);
      // Return the exact compact summary row.
      return html`<tr${warning}>${cells}</tr>`;
    });
    // Preserve the accepted seven summary table headings.
    const heads = [
      // Keep game, wager, and return labels in their established order.
      t('economics.game', {}, 'admin'), t('economics.wagered', {}, 'admin'), t('economics.returned', {}, 'admin'),
      // Keep ratio, edge, status, and action columns in their established order.
      t('economics.payoutRate', {}, 'admin'), t('economics.houseEdge', {}, 'admin'), t('economics.status', {}, 'admin'), '',
    ];
    // Preserve the existing localized empty state when the bounded ledger window has no games.
    const content = rows.length ? table(heads, rows) : emptyState(
      // Keep the localized empty title, detail, and stable Browser test hook.
      t('economics.emptyTitle', {}, 'admin'), t('economics.emptyDetail', {}, 'admin'), 'admin-economics-empty'
    );
    // Build the localized heading and bounded-window copy independently.
    const heading = html`<h3>${safe(t('economics.heading', {}, 'admin'))}</h3>`;
    // Preserve the muted bounded-window explanation immediately before the table.
    const windowText = html`<p class="muted">${safe(t('economics.window', { count: data.window }, 'admin'))}</p>`;
    // Render the exact summary card around the table or empty-state content.
    view.innerHTML = html`<section class="admin-card" data-testid="admin-economics">${heading}${windowText}${content}</section>`;
    // Bind each drill-down to the exact canonical game id published by the backend.
    view.querySelectorAll('[data-economics-game]').forEach(button => {
      // Open the exact canonical game selected by this row.
      button.onclick = () => economicsDetail(button.dataset.economicsGame);
    });
  }

  // Return the summary renderer so the dispatcher keeps its stable call contract.
  return economics;
}
