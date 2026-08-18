// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Autoplay tab from explicit Admin-shell dependencies so extraction preserves its control contract. (AUTO-007, AUTO-008)
export function createAutoplayTab({ api, html, post, safe, setTitle, t, table, toast, view }) {
  // Return the existing asynchronous renderer so the dispatcher keeps its stable call contract.
  return async function autoplay() {
    // Set the localized Autoplay title and subtitle. (I18N-014)
    setTitle(t('autoplay.title', {}, 'admin'), t('autoplay.subtitle', {}, 'admin'));
    // Load active and recent sessions through the frozen Admin endpoint.
    const data = await api('/api/v1/admin/autoplay');
    // Resolve the eight localized column headings in their accepted order. (I18N-014)
    const headingKeys = ['id', 'game', 'player', 'status', 'speed', 'completed', 'limit', 'updated'];
    // Convert resource keys to installed-locale headings without exposing fallback identifiers.
    const headings = headingKeys.map(key => t(`autoplay.${key}`, {}, 'admin'));
    // Keep newest sessions first while escaping every server-owned field.
    const rows = (data.sessions || []).slice().reverse().map(session => {
      // Preserve the first four identity and status cells in their accepted compact order.
      const identity = html`<td>${safe(session.autoplay_id)}</td><td>${safe(session.game_id)}</td><td>${safe(session.player_id)}</td>`;
      // Preserve the remaining control-plane values without adding source whitespace to the DOM.
      const progress = html`<td>${safe(session.status)}</td><td>${safe(session.speed)}</td><td>${safe(session.rounds_completed)}</td>`;
      // Return the exact compact row with the round limit and update timestamp last.
      return html`<tr>${identity}${progress}<td>${safe(session.round_limit)}</td><td>${safe(session.updated_at)}</td></tr>`;
    });
    // Preserve the exact localized heading and stable Stop All control above the session table.
    const stop = html`<button id="stopAllAuto" data-testid="admin-stop-all-auto" class="danger">${safe(t('autoplay.stopAll', {}, 'admin'))}</button>`;
    // Preserve the exact compact Autoplay card and session-table output.
    view.innerHTML = html`<section class="admin-card"><div class="row"><h3 style="margin-right:auto">${safe(t('autoplay.sessions', {}, 'admin'))}</h3>${stop}</div>${table(headings, rows)}</section>`;
    // Bind the global stop request after rendering the stable action control.
    view.querySelector('#stopAllAuto').onclick = async () => {
      // Request server-owned stop state for every registered Autoplay session.
      await post('/api/v1/admin/autoplay/stop-all', {});
      // Confirm the request through installed-locale copy without exposing session internals.
      toast(t('autoplay.stopRequested', {}, 'admin'), true);
      // Refresh once so the table converges on the server-owned session registry.
      autoplay();
    };
  };
}
