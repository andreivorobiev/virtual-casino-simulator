// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build personal preferences, history, and guest conversion behind one route view. (USER-009, CONVERT-003)

// Create the personal Settings renderer and mutation handlers.
export function createSettingsView(dependencies) {
  // Capture the accepted API, locale, session, and presentation seams.
  const {
    api, clearAuthenticatedShellState, cryptoRef, documentRef, getActive, html,
    getLocaleState, isGuestSession, localeOptionsHtml, renderLoginGate, safe,
    raw, setLocale, setPersonalSoundEnabled, t,
  } = dependencies;

  // Render the shared personal preference form.
  function settingsForm(settings) {
    // Preserve locale and durable sound preference controls.
    const locale = html`<label>${t('settings.language', {}, 'shell')}<select id="personal-settings-locale" data-testid="personal-settings-locale"></select></label>`;
    const checked = settings.sound_enabled === true ? 'checked' : '';
    const soundInput = html`<input id="personal-settings-sound" data-testid="personal-settings-sound" type="checkbox" ${checked}>`;
    const sound = html`<label class="check-row">${soundInput}<span>${t('settings.sound', {}, 'shell')}</span></label>`;
    const save = html`<button class="primary" data-testid="personal-settings-save" type="submit">${t('settings.save', {}, 'shell')}</button>`;
    const message = html`<p id="personal-settings-message" class="auth-message" role="status"></p>`;
    const heading = html`<p class="eyebrow">${t('settings.eyebrow', {}, 'shell')}</p><h1>${t('settings.title', {}, 'shell')}</h1>`;
    const copy = html`<p>${t('settings.copy', {}, 'shell')}</p>`;
    const form = html`<form id="personal-settings-form" class="auth-form">${locale}${sound}${save}${message}</form>`;
    return html`<section class="panel settings-panel" data-testid="my-settings">${heading}${copy}${form}</section>`;
  }

  // Render the disposable-guest conversion form.
  function guestConversion() {
    // Preserve account identity, transient password, and exact consent controls.
    const email = html`<label>${t('auth.email', {}, 'shell')}<input id="conversion-email" type="email" maxlength="254" required></label>`;
    const name = html`<label>${t('conversion.displayName', {}, 'shell')}<input id="conversion-display-name" maxlength="80" required></label>`;
    const password = html`<label>${t('conversion.password', {}, 'shell')}<input id="conversion-password" type="password" minlength="12" maxlength="128" required></label>`;
    const terms = html`<label class="check-row"><input id="conversion-terms" type="checkbox" required><span>${t('conversion.terms', {}, 'shell')}</span></label>`;
    const submit = html`<button class="primary" data-testid="guest-conversion-submit" type="submit">${t('conversion.submit', {}, 'shell')}</button>`;
    const message = html`<p id="guest-conversion-message" class="auth-message" role="status"></p>`;
    const form = html`<form id="guest-conversion-form" class="auth-form">${email}${name}${password}${terms}${submit}${message}</form>`;
    const heading = html`<h2>${t('conversion.title', {}, 'shell')}</h2>`;
    const copy = html`<p>${t('conversion.copy', {}, 'shell')}</p>`;
    return html`<section class="panel settings-panel" data-testid="guest-conversion">${heading}${copy}${form}</section>`;
  }

  // Render account-owned ledger history or its calm empty state.
  function historyView(historyData) {
    // Preserve exact published columns without expanding event detail.
    const headings = ['time', 'game', 'event', 'amount', 'balance', 'reference']
      .map(key => html`<th>${t(`settings.${key}`, {}, 'shell')}</th>`);
    const rows = (historyData.events || []).map((event) => {
      // Preserve exact public history field order.
      const values = [
        event.ts || '', event.game || '', event.transaction_type || '',
        event.amount, event.balance_after, event.reference || '',
      ];
      return html`<tr>${values.map(value => html`<td>${value}</td>`)}</tr>`;
    });
    const label = t('settings.history', {}, 'shell');
    const content = rows.length
      ? html`<div class="table-scroll" tabindex="0" role="region" aria-label="${label}"><table class="mini-table"><thead><tr>${headings}</tr></thead><tbody>${rows}</tbody></table></div>`
      : html`<p class="status">${t('settings.historyEmpty', {}, 'shell')}</p>`;
    return html`<section class="panel settings-panel" data-testid="my-history"><h2>${label}</h2>${content}</section>`;
  }

  // Bind durable personal settings with optimistic revision control.
  function bindSettingsForm(view, settings, localeSelect) {
    // Persist only published personal settings.
    view.querySelector('#personal-settings-form').onsubmit = async (event) => {
      // Keep the browser on this route while the mutation settles.
      event.preventDefault();
      const result = await api('/api/v2/me/settings', {
        method: 'PATCH',
        body: {
          locale: localeSelect.value,
          sound_enabled: view.querySelector('#personal-settings-sound').checked,
          revision: settings.revision,
        },
      });
      // Advance optimistic revision for any repeated save.
      settings.revision = result.settings?.revision ?? settings.revision;
      setPersonalSoundEnabled(result.settings?.sound_enabled === true);
      // Apply accepted locale only after durable persistence.
      if (result.settings?.locale) {
        await setLocale(result.settings.locale, { persistLocal: false });
      }
      const message = documentRef.getElementById('personal-settings-message');
      if (message) message.textContent = t('settings.saved', {}, 'shell');
    };
  }

  // Bind explicit conversion only for the disposable guest surface.
  function bindGuestConversion(view, localeSelect) {
    // Stop when the registered-user history surface is active.
    const conversionForm = view.querySelector('#guest-conversion-form');
    if (!conversionForm) return;
    conversionForm.onsubmit = async (event) => {
      // Keep the guest on this surface until conversion commits.
      event.preventDefault();
      const message = view.querySelector('#guest-conversion-message');
      // Preserve existing player and wallet behind the exact additive endpoint.
      await api('/api/v2/me/convert-guest', {
        method: 'POST',
        body: {
          email: view.querySelector('#conversion-email').value.trim(),
          display_name: view.querySelector('#conversion-display-name').value.trim(),
          password: view.querySelector('#conversion-password').value,
          terms_version: 'private-beta-1',
          accepted: view.querySelector('#conversion-terms').checked,
          locale: localeSelect.value,
          idempotency_key: cryptoRef.randomUUID(),
        },
      });
      message.textContent = t('conversion.completed', {}, 'shell');
      clearAuthenticatedShellState();
      renderLoginGate(t('conversion.completed', {}, 'shell'));
    };
  }

  // Render durable personal preferences plus role-appropriate account content.
  async function renderMySettings(view) {
    // Read personal settings and account history only when applicable.
    const preferenceData = await api('/api/v2/me/settings');
    const settings = preferenceData.settings || {
      locale: 'en-US', sound_enabled: false, revision: 0,
    };
    const guest = isGuestSession();
    const historyData = guest
      ? { events: [] }
      : await api('/api/v2/me/history?page=1&page_size=25');
    // Stop stale Settings work from replacing a newer route.
    if (getActive() !== 'settings') return;
    view.innerHTML = html`${settingsForm(settings)}${guest ? guestConversion() : historyView(historyData)}`;
    // Fill locale choices from the governed manifest.
    const localeSelect = view.querySelector('#personal-settings-locale');
    localeSelect.innerHTML = html`${raw(localeOptionsHtml())}`;
    localeSelect.value = settings.updated_at
      ? settings.locale
      : getLocaleState().locale;
    // Bind durable save and optional guest conversion.
    bindSettingsForm(view, settings, localeSelect);
    bindGuestConversion(view, localeSelect);
  }

  // Publish only the router-facing Settings renderer.
  return renderMySettings;
}
