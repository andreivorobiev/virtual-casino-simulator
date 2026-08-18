// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the read-only Admin Telemetry tab behind explicit shell dependencies. (ADMIN-008, ADMIN-017)
export function createTelemetryTab(dependencies) {
  // Read the reviewed shell dependencies once so the returned renderer stays listener-free.
  const { api, eventList, html, setTitle, view } = dependencies;
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function telemetry() {
    // Set the accepted Telemetry title and explanatory subtitle before requesting records.
    setTitle('Telemetry', 'Application, error, and browser-client logs.');
    // Load application records first through the frozen Admin logs endpoint.
    const app = await api('/api/v1/admin/logs?kind=app&limit=200');
    // Load server-error records second through the same frozen endpoint.
    const errors = await api('/api/v1/admin/logs?kind=errors&limit=200');
    // Load browser-client records last through the same frozen endpoint.
    const client = await api('/api/v1/admin/logs?kind=client&limit=200');
    // Delegate ordinary application records through the shared readable event-list boundary.
    const appEvents = eventList(
      app.logs,
      'No application events',
      'Application activity will appear here as the local service is used.',
      'admin-app-events',
    );
    // Delegate server errors with technical details suppressed by the shared privacy boundary.
    const errorEvents = eventList(
      errors.logs,
      'No error events',
      'No server errors have been recorded for the current day.',
      'admin-error-events',
      true,
    );
    // Delegate ordinary browser records through the same readable event-list boundary.
    const clientEvents = eventList(
      client.logs,
      'No browser events',
      'Browser activity will appear here after a client sends telemetry.',
      'admin-client-events',
    );
    // Preserve each accepted card as compact markup without source-formatting whitespace.
    const appCard = html`<section class="admin-card"><h3>Application events</h3>${appEvents}</section>`;
    // Preserve the server-error card beside application events.
    const errorCard = html`<section class="admin-card"><h3>Error events</h3>${errorEvents}</section>`;
    // Preserve the browser-event card below the split server-event row.
    const clientCard = html`<section class="admin-card"><h3>Browser events</h3>${clientEvents}</section>`;
    // Compose the exact accepted Telemetry topology in one replacement.
    view.innerHTML = html`<div class="admin-split">${appCard}${errorCard}</div>${clientCard}`;
  };
}
