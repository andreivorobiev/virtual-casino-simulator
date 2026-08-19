// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build locale selection, readiness, and diagnostics behind a dedicated Admin tab. (I18N-005, I18N-014)

// Build shared locale option helpers for Language and other Admin account surfaces.
export function createLocaleOptionHelpers(dependencies) {
  // Capture the manifest state and compact option helpers.
  const { getLocaleState, html, option, t } = dependencies;
  // Render installed UI locale options with native labels.
  function localeOptions(selected) {
    // Keep select options driven only by manifest-ready locales.
    return getLocaleState().locales.map(locale => option(
      locale.id,
      `${locale.nativeLabel} (${locale.id})`,
      selected,
    ));
  }
  // Render browser-default plus every unique formatter locale.
  function formatLocaleOptions(selected) {
    // Read the complete locked registry for deterministic Intl identities.
    const state = getLocaleState();
    // Preserve browser-default as the first option.
    const browser = option('browser', t('language.browserDefault', {}, 'admin'), selected);
    // De-duplicate declared formatter fallbacks without enabling untranslated UI packs.
    const entries = state.localeRegistry.reduce((formats, locale) => {
      // Keep the first registry owner of each formatter identity.
      if (!formats.has(locale.formatLocale)) formats.set(locale.formatLocale, locale);
      // Return the same accumulator for the next registry row.
      return formats;
    }, new Map());
    const formatters = [...entries.values()];
    // Compose browser and formatter options without separator whitespace.
    return html`${browser}${formatters.map(locale => option(
      locale.formatLocale,
      `${locale.nativeLabel} (${locale.formatLocale})`,
      selected,
    ))}`;
  }
  // Publish both shared select helpers.
  return { formatLocaleOptions, localeOptions };
}

// Build the interactive Language & Locale tab.
export function createLanguageTab(dependencies) {
  // Capture the established locale runtime and presentation helpers.
  const {
    formatDate, formatLocaleOptions, formatMoney, formatNumber, getLocaleSettings,
    getLocaleState, html, localeOptions, option, resetLocaleSettings, safe, setLocale,
    setTitle, t, table, toast, view,
  } = dependencies;

  // Render one installed locale readiness card.
  function languageCard(locale, selected) {
    // Preserve active or ready status from resolved locale identity.
    const status = locale.id === selected ? 'language.active' : 'language.ready';
    const heading = html`<div class="row"><h3 style="margin-right:auto">${safe(locale.nativeLabel)}</h3><span class="badge">${safe(t(status, {}, 'admin'))}</span></div>`;
    // Preserve installed fallback-chain explanation.
    const detail = safe(t('language.installedDescription', {
      label: locale.label,
      fallback: locale.fallbackChain.join(' → '),
    }, 'admin'));
    // Preserve script, review, voice, and direction badges.
    const badges = [
      html`<span class="badge">${safe(locale.script)}</span>`,
      html`<span class="badge">${safe(t(`language.review.${locale.reviewStatus}`, {}, 'admin'))}</span>`,
      html`<span class="badge">${safe(t(locale.voiceReady ? 'language.voiceReady' : 'language.voiceCheck', {}, 'admin'))}</span>`,
      html`<span class="badge">${safe(locale.dir.toUpperCase())}</span>`,
    ];
    // Return one compact ready-locale card.
    const description = html`<p class="muted">${detail}</p>`;
    const badgeRow = html`<div class="row">${badges}</div>`;
    return html`<article class="bot-edit" data-locale-card="${safe(locale.id)}" lang="${safe(locale.id)}" dir="${safe(locale.dir)}">${heading}${description}${badgeRow}</article>`;
  }

  // Render installed locale readiness cards.
  function languageCards(selected) {
    // Keep cards driven only by manifest-ready UI locales.
    return getLocaleState().locales.map(locale => languageCard(locale, selected));
  }

  // Render one metadata-only locked-registry card.
  function registryCard(locale) {
    // Preserve rank, native label, and true readiness state.
    const rank = html`<span class="badge">#${formatNumber(locale.rank)}</span>`;
    const name = html`<strong style="margin-right:auto">${safe(locale.nativeLabel)}</strong>`;
    const readiness = safe(t(locale.uiReady ? 'language.ready' : 'language.metadataOnly', {}, 'admin'));
    const status = html`<span class="badge">${readiness}</span>`;
    const heading = html`<div class="row">${rank}${name}${status}</div>`;
    // Preserve immutable registry metadata without claiming translation completion.
    const detail = html`<p class="muted">${safe(locale.id)} · ${safe(locale.script)} · ${safe(locale.dir.toUpperCase())} · ${safe(locale.formatLocale)}</p>`;
    // Return one stable registry entry.
    const identity = html` data-locale-id="${safe(locale.id)}" lang="${safe(locale.id)}" dir="${safe(locale.dir)}"`;
    return html`<article class="bot-edit" data-testid="admin-locale-registry-entry"${identity}>${heading}${detail}</article>`;
  }

  // Render the complete owner-approved locale registry.
  function lockedLanguageGrid() {
    // Preserve registry order and readiness metadata.
    const cards = getLocaleState().localeRegistry.map(registryCard);
    // Return the named two-column registry.
    return html`<div class="grid2" data-testid="admin-locale-registry">${cards}</div>`;
  }

  // Render current runtime diagnostic values.
  function diagnosticsTable(state) {
    // Build one stable row per published diagnostic.
    const readyCount = `${formatNumber(state.locales.length)} / ${formatNumber(state.localeRegistry.length)}`;
    const rows = [
      html`<tr><td>${safe(t('language.registryVersion', {}, 'admin'))}</td><td>${safe(state.registryVersion)}</td></tr>`,
      html`<tr><td>${safe(t('language.resolvedLocale', {}, 'admin'))}</td><td data-testid="admin-locale-state">${safe(state.locale)}</td></tr>`,
      html`<tr><td>${safe(t('language.fallbackLocale', {}, 'admin'))}</td><td>${safe(state.fallbackLocale)}</td></tr>`,
      html`<tr><td>${safe(t('language.installedLocales', {}, 'admin'))}</td><td data-testid="admin-locale-ready-count">${readyCount}</td></tr>`,
      html`<tr><td>${safe(t('language.registeredDomains', {}, 'admin'))}</td><td>${formatNumber(state.registeredDomains.length)}</td></tr>`,
      html`<tr><td>${safe(t('language.loadedDomains', {}, 'admin'))}</td><td>${safe(state.loadedDomains.join(', '))}</td></tr>`,
      html`<tr><td>${safe(t('language.missingKeys', {}, 'admin'))}</td><td>${formatNumber(state.missingKeyCount)}</td></tr>`,
    ];
    // Preserve the shared mini-table shape.
    return table([t('language.diagnostics', {}, 'admin'), 'Value'], rows);
  }

  // Switch locale without navigating away from Admin.
  async function saveLocale(language, nextFormat, useBrowser, persist) {
    // Apply runtime and optional browser-local settings atomically.
    await setLocale(language, {
      persistLocal: persist,
      nextFormatLocale: nextFormat,
      nextUseBrowserLocale: useBrowser,
    });
    // Preserve localized completion feedback.
    toast(t('language.saved', {}, 'admin'), true);
  }

  // Return Admin to browser-default locale resolution.
  async function resetLanguage() {
    // Reset runtime and browser-local settings through the i18n helper.
    await resetLocaleSettings();
    // Preserve localized completion feedback.
    toast(t('language.saved', {}, 'admin'), true);
  }

  // Bind Language & Locale controls after rendering.
  function bindLanguageControls() {
    // Resolve the four preference controls once.
    const languageSelect = view.querySelector('#admin_language');
    const formatSelect = view.querySelector('#admin_format_locale');
    const browserToggle = view.querySelector('#admin_use_browser');
    const persistToggle = view.querySelector('#admin_persist_browser');
    // Communicate browser-resolved language by disabling explicit selection.
    const syncDisabled = () => { languageSelect.disabled = browserToggle.checked; };
    browserToggle.onchange = syncDisabled;
    syncDisabled();
    // Bind apply, save-default, reset, and Preview Lobby actions.
    view.querySelector('#admin_apply_locale').onclick = () => saveLocale(
      languageSelect.value, formatSelect.value, browserToggle.checked, persistToggle.checked,
    );
    view.querySelector('#admin_save_locale').onclick = () => saveLocale(
      languageSelect.value, formatSelect.value, browserToggle.checked, true,
    );
    view.querySelector('#admin_reset_locale').onclick = resetLanguage;
    view.querySelector('#admin_preview_lobby').onclick = () => { location.href = '/'; };
  }

  // Build the installed and locked locale catalog card.
  function catalogCard(state, selectedLanguage) {
    // Preserve ready-count evidence and installed locale cards.
    const title = html`<h3 style="margin-right:auto">${safe(t('language.availableTitle', {}, 'admin'))}</h3>`;
    const readyCount = safe(t('language.readyCount', {
      ready: state.locales.length,
      total: state.localeRegistry.length,
    }, 'admin'));
    const badge = html`<span class="badge">${readyCount}</span>`;
    const heading = html`<div class="row">${title}${badge}</div>`;
    const ready = html`<div class="grid2">${languageCards(selectedLanguage)}</div>`;
    const registryHeading = html`<h3>${safe(t('language.registryTitle', {}, 'admin'))}</h3>`;
    // Return the accepted catalog order.
    return html`<section class="admin-card">${heading}${ready}${registryHeading}${lockedLanguageGrid()}</section>`;
  }

  // Build interactive locale settings, previews, and diagnostics.
  function settingsCard(state, settings, selectedLanguage, selectedFormat) {
    // Preserve language and format selectors.
    const languageLabel = safe(t('language.displayLanguage', {}, 'admin'));
    const languageSelect = html`<label>${languageLabel}<select id="admin_language" data-testid="admin-language-select">${localeOptions(selectedLanguage)}</select></label>`;
    const formatLabel = safe(t('language.formatLocale', {}, 'admin'));
    const formatSelect = html`<label>${formatLabel}<select id="admin_format_locale" data-testid="admin-format-locale-select">${formatLocaleOptions(selectedFormat)}</select></label>`;
    // Preserve browser resolution and persistence controls.
    const browserChecked = settings.useBrowserLocale ? 'checked' : '';
    const browser = html`<label><input id="admin_use_browser" type="checkbox" ${browserChecked}> ${safe(t('language.useBrowser', {}, 'admin'))}</label>`;
    const persist = html`<label><input id="admin_persist_browser" type="checkbox" checked> ${safe(t('language.persistBrowser', {}, 'admin'))}</label>`;
    // Preserve money and date previews.
    const moneyPreview = html`<p data-testid="admin-money-preview">${safe(t('language.previewBalance', { amount: formatMoney(5030) }, 'admin'))}</p>`;
    const datePreview = html`<p>${safe(t('language.datePreview', {}, 'admin'))}: ${safe(formatDate(new Date(), { dateStyle: 'medium', timeStyle: 'short' }))}</p>`;
    const preview = html`<div class="result-box">${moneyPreview}${datePreview}</div>`;
    // Preserve all four explicit locale actions.
    const apply = html`<button id="admin_apply_locale" data-testid="admin-locale-apply" class="gold">${safe(t('language.apply', {}, 'admin'))}</button>`;
    const save = html`<button id="admin_save_locale" data-testid="admin-locale-save">${safe(t('language.saveBrowser', {}, 'admin'))}</button>`;
    const reset = html`<button id="admin_reset_locale" data-testid="admin-locale-reset">${safe(t('language.resetBrowser', {}, 'admin'))}</button>`;
    const lobby = html`<button id="admin_preview_lobby">${safe(t('actions.previewLobby'))}</button>`;
    const actions = html`<div class="row">${apply}${save}${reset}${lobby}</div>`;
    // Preserve English, Russian, and fallback string previews.
    const english = html`<div class="bot-edit"><b>English</b><p>Choose your table. All games use play tokens only. Ledger-backed outcomes are visible in Admin.</p></div>`;
    const russian = html`<div class="bot-edit"><b>Русский</b><p>Выберите стол. Все игры используют только игровые токены. Результаты с учётом ledger видны в Admin.</p></div>`;
    const fallback = html`<div class="bot-edit"><b>${safe(t('language.fallback', {}, 'admin'))}</b><p>${safe(t('language.fallbackDescription', {}, 'admin'))}</p></div>`;
    // Return the exact accepted settings-card order.
    const selectors = html`<div class="grid2 locale-settings-grid">${languageSelect}${formatSelect}</div>`;
    const strings = html`<h3>${safe(t('language.stringPreview', {}, 'admin'))}</h3>${english}${russian}${fallback}`;
    const heading = html`<h3>${safe(t('language.localeSettings', {}, 'admin'))}</h3>`;
    const diagnostics = diagnosticsTable(state);
    return html`<section class="admin-card">${heading}${selectors}${browser}${persist}${preview}${actions}${diagnostics}${strings}</section>`;
  }

  // Render browser-local Language & Locale controls.
  async function language() {
    // Set the localized heading and read current runtime and saved preferences.
    setTitle(t('language.title', {}, 'admin'), t('language.subtitle', {}, 'admin'));
    const state = getLocaleState();
    const settings = getLocaleSettings();
    // Resolve selected language and format controls from saved/browser state.
    const selectedLanguage = settings.useBrowserLocale ? state.locale : settings.language;
    const selectedFormat = settings.formatLocale || state.formatLocale;
    // Replace the tab atomically with catalog and interactive settings cards.
    const catalog = catalogCard(state, selectedLanguage);
    const settingsView = settingsCard(state, settings, selectedLanguage, selectedFormat);
    view.innerHTML = html`<div class="admin-split" data-testid="admin-localization-foundation">${catalog}${settingsView}</div>`;
    // Bind all locale actions after rendering.
    bindLanguageControls();
  }

  // Publish only the dispatcher-facing Language renderer.
  return language;
}
