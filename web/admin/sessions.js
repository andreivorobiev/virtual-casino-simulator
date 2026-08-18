// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build registered-session and live request policy behind a dedicated Admin tab. (SESSION-009, ADMIN-031, ADMIN-032)
export function createSessionsTab(dependencies) {
  // Capture the established owner-only policy and presentation helpers.
  const { api, html, safe, setTitle, t, toast, view } = dependencies;

  // Render one bounded numeric policy control.
  function numberControl(label, id, min, max, value, testId) {
    // Preserve all accepted range and automation attributes.
    return html`<label>${safe(label)}<input id="${safe(id)}" type="number" min="${safe(min)}" max="${safe(max)}" value="${safe(value)}" data-testid="${safe(testId)}"></label>`;
  }

  // Persist the owner-authored registered-session policy.
  async function saveSessions() {
    // Build the complete enforcement and timeout payload from visible controls.
    const payload = {
      enabled: view.querySelector('#sessions_enabled').checked,
      idle_timeout_minutes: Number(view.querySelector('#idle_timeout_minutes').value),
      absolute_timeout_hours: Number(view.querySelector('#absolute_timeout_hours').value),
      warning_minutes: Number(view.querySelector('#warning_minutes').value),
      admin_idle_timeout_minutes: Number(view.querySelector('#admin_idle_timeout_minutes').value),
      admin_stricter: view.querySelector('#admin_stricter').checked,
    };
    // Persist through the owner-only route and confirm without exposing internals.
    await api('/api/v2/admin/session-settings', { method: 'POST', body: payload });
    toast(t('sessions.saved', {}, 'admin'), true);
  }

  // Persist the owner-authored live request policy without service restart.
  async function saveRateLimits() {
    // Build the sparse bounded policy from the two operational number fields.
    const payload = {
      requests_per_window: Number(view.querySelector('#requests_per_window').value),
      window_seconds: Number(view.querySelector('#window_seconds').value),
    };
    // Persist through the recovery-safe owner route and confirm activation.
    await api('/api/v2/admin/rate-limits', { method: 'POST', body: payload });
    toast(t('rateLimits.saved', {}, 'admin'), true);
  }

  // Build the registered-session policy card.
  function sessionCard(settings) {
    // Preserve enforcement and stricter-Admin checked projections.
    const enabled = settings.enabled ? 'checked' : '';
    const stricter = settings.admin_stricter ? 'checked' : '';
    const enabledLabel = safe(t('sessions.enabled', {}, 'admin'));
    const enforcement = html`<label class="check-row"><input id="sessions_enabled" type="checkbox" ${enabled} data-testid="admin-sessions-enabled"><span>${enabledLabel}</span></label>`;
    // Build all four bounded timeout controls in accepted order.
    const timeouts = [
      numberControl(
        t('sessions.idle', {}, 'admin'),
        'idle_timeout_minutes', 1, 1440, settings.idle_timeout_minutes, 'admin-sessions-idle',
      ),
      numberControl(
        t('sessions.absolute', {}, 'admin'),
        'absolute_timeout_hours', 1, 24, settings.absolute_timeout_hours, 'admin-sessions-absolute',
      ),
      numberControl(
        t('sessions.warning', {}, 'admin'),
        'warning_minutes', 0, 10, settings.warning_minutes, 'admin-sessions-warning',
      ),
      numberControl(
        t('sessions.adminIdle', {}, 'admin'),
        'admin_idle_timeout_minutes', 1, 1440,
        settings.admin_idle_timeout_minutes, 'admin-sessions-admin-idle',
      ),
    ];
    // Preserve the stricter-Admin control and calm explanatory evidence.
    const stricterLabel = safe(t('sessions.adminStricter', {}, 'admin'));
    const admin = html`<label><input id="admin_stricter" type="checkbox" ${stricter} data-testid="admin-sessions-admin-stricter"> ${stricterLabel}</label>`;
    const help = html`<p class="muted">${safe(t('sessions.help', {}, 'admin'))}</p>`;
    const provenanceText = safe(t('sessions.provenance', {
      time: settings.updated_at || '—',
      actor: settings.updated_by || '—',
    }, 'admin'));
    const provenance = html`<p class="muted" data-testid="admin-sessions-provenance">${provenanceText}</p>`;
    // Preserve the explicit owner save action.
    const action = html`<div class="row"><button id="saveSessions" data-testid="admin-save-sessions" class="gold">${safe(t('sessions.save', {}, 'admin'))}</button></div>`;
    // Return the exact accepted session-policy card order.
    const controls = html`${enforcement}<div class="grid3">${timeouts}</div>${admin}${help}${provenance}${action}`;
    return html`<section class="admin-card" data-testid="admin-sessions-policy"><h3>${safe(t('sessions.heading', {}, 'admin'))}</h3>${controls}</section>`;
  }

  // Build the independently persisted live request policy card.
  function rateLimitCard(settings) {
    // Preserve both bounded policy controls.
    const controls = [
      numberControl(
        t('rateLimits.requests', {}, 'admin'),
        'requests_per_window', 60, 10000, settings.requests_per_window, 'admin-rate-limit-requests',
      ),
      numberControl(
        t('rateLimits.window', {}, 'admin'),
        'window_seconds', 1, 3600, settings.window_seconds, 'admin-rate-limit-window',
      ),
    ];
    // Preserve help copy and explicit live-policy save action.
    const help = html`<p class="muted">${safe(t('rateLimits.help', {}, 'admin'))}</p>`;
    const action = html`<div class="row"><button id="saveRateLimits" data-testid="admin-save-rate-limits" class="gold">${safe(t('rateLimits.save', {}, 'admin'))}</button></div>`;
    // Return the exact accepted request-policy card order.
    return html`<section class="admin-card" data-testid="admin-rate-limits"><h3>${safe(t('rateLimits.heading', {}, 'admin'))}</h3><div class="grid3">${controls}</div>${help}${action}</section>`;
  }

  // Render the owner-facing session and request-rate policies.
  async function sessions() {
    // Set the localized policy heading.
    setTitle(t('sessions.title', {}, 'admin'), t('sessions.subtitle', {}, 'admin'));
    // Load both independently persisted owner documents together.
    const [data, rateData] = await Promise.all([
      api('/api/v2/admin/session-settings'),
      api('/api/v2/admin/rate-limits'),
    ]);
    // Read each policy under a safe empty fallback.
    const sessionSettings = data.settings || {};
    const rateSettings = rateData.settings || {};
    // Replace the tab atomically with distinct policy cards.
    view.innerHTML = html`${sessionCard(sessionSettings)}${rateLimitCard(rateSettings)}`;
    // Bind each owner save action to only its policy boundary.
    view.querySelector('#saveSessions').onclick = saveSessions;
    view.querySelector('#saveRateLimits').onclick = saveRateLimits;
  }

  // Publish only the dispatcher-facing Sessions renderer.
  return sessions;
}
