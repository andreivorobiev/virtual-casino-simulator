// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build de-identified Guest Trials policy, telemetry, conversion, and retention controls. (CONVERT-003, ADMIN-031)

// Preserve the complete allowlisted filter shape across locale rerenders.
const INITIAL_FILTERS = Object.freeze({
  locale: '',
  device: '',
  status: '',
  game: '',
  completed: '',
  error_category: '',
  range: '',
});
// Preserve the full owner-approved milestone order.
const FUNNEL_STAGES = Object.freeze([
  'landing_viewed',
  'trial_started',
  'lobby_reached',
  'first_game_opened',
  'first_action_accepted',
  'first_round_completed',
  'second_game_opened',
  'trial_terminal',
  'account_cta_viewed',
  'account_cta_selected',
]);
// Preserve only sanitized error categories published by the analytics contract.
const ERROR_CATEGORIES = Object.freeze([
  'VALIDATION_ERROR',
  'INSUFFICIENT_FUNDS',
  'CONFLICT',
  'FORBIDDEN',
  'NOT_FOUND',
  'RATE_LIMITED',
  'SERVER_ERROR',
]);

// Build the interactive Guest Trials tab.
export function createGuestsTab(dependencies) {
  // Capture the accepted API, locale, rendering, and notification seams.
  const {
    api, emptyState, formatMoney, formatNumber, html, humanLabel, isActiveTab,
    localeOptions, option, post, safe, setTitle, t, table, toast, view,
  } = dependencies;
  // Retain low-cardinality filters within one Admin page lifetime.
  let guestFilters = { ...INITIAL_FILTERS };

  // Render one compact summary card.
  function summaryCard(labelKey, value, testId = '') {
    // Add a stable identity only to the established primary six metrics.
    const identity = testId ? html` data-testid="${safe(testId)}"` : '';
    return html`<div class="admin-card"><b>${safe(t(labelKey, {}, 'admin'))}</b><h2${identity}>${value}</h2></div>`;
  }

  // Render the three basic filters and retention action.
  function baseFilters() {
    // Preserve manifest-driven locale selection.
    const all = t('guests.filterAll', {}, 'admin');
    const localeOptionsView = html`${option('', all, guestFilters.locale)}${localeOptions(guestFilters.locale)}`;
    const locale = html`<label>${safe(t('guests.filterLocale', {}, 'admin'))}<select id="guest-filter-locale">${localeOptionsView}</select></label>`;
    // Preserve the fixed device classifier options.
    const devices = [
      option('', all, guestFilters.device),
      option('desktop', t('guests.deviceDesktop', {}, 'admin'), guestFilters.device),
      option('tablet', t('guests.deviceTablet', {}, 'admin'), guestFilters.device),
      option('mobile', t('guests.deviceMobile', {}, 'admin'), guestFilters.device),
    ];
    const device = html`<label>${safe(t('guests.filterDevice', {}, 'admin'))}<select id="guest-filter-device">${devices}</select></label>`;
    // Preserve active and terminal lifecycle choices.
    const statuses = [
      option('', all, guestFilters.status),
      option('active', t('guests.statusActive', {}, 'admin'), guestFilters.status),
      option('ended', t('guests.statusEnded', {}, 'admin'), guestFilters.status),
    ];
    const status = html`<label>${safe(t('guests.filterStatus', {}, 'admin'))}<select id="guest-filter-status">${statuses}</select></label>`;
    const cleanup = html`<button id="guest-cleanup" type="button" data-testid="admin-guest-cleanup">${safe(t('guests.cleanupRun', {}, 'admin'))}</button>`;
    return html`<section class="admin-card guest-filter-card" data-testid="admin-guest-filters"><div class="guest-filter-grid">${locale}${device}${status}${cleanup}</div></section>`;
  }

  // Render the accepted primary Guest Trials summary.
  function summaryCards(summary, funnel) {
    // Preserve each published aggregate and stable selector.
    const cards = [
      summaryCard('guests.started', formatNumber(funnel.started || 0), 'admin-guest-started'),
      summaryCard('guests.engaged', formatNumber(funnel.engaged || 0), 'admin-guest-engaged'),
      summaryCard('guests.completed', formatNumber(funnel.completed_round || 0), 'admin-guest-completed'),
      summaryCard('guests.activeNow', formatNumber(summary.active_now || 0), 'admin-guest-active'),
      summaryCard('guests.ended', formatNumber(summary.ended_total || 0), 'admin-guest-ended'),
      summaryCard('guests.expired', formatNumber(summary.expired_total || 0), 'admin-guest-expired'),
    ];
    return html`<div class="admin-card-grid" data-testid="admin-guest-summary">${cards}</div>`;
  }

  // Render compact per-game compatibility metrics.
  function compactGames(games) {
    // Preserve the calm empty state when no retained game rows exist.
    const rows = games.map((row) => {
      // Preserve the exact compact aggregate column order.
      const values = [
        humanLabel(row.game),
        formatNumber(row.trials),
        formatNumber(row.opens),
        formatNumber(row.actions),
        formatNumber(row.rounds_completed),
      ];
      return html`<tr>${values.map(value => html`<td>${safe(value)}</td>`)}</tr>`;
    });
    const content = games.length ? table([
      t('guests.colGame', {}, 'admin'),
      t('guests.colTrials', {}, 'admin'),
      t('guests.colOpens', {}, 'admin'),
      t('guests.colActions', {}, 'admin'),
      t('guests.colRounds', {}, 'admin'),
    ], rows) : emptyState(
      t('guests.gamesEmpty', {}, 'admin'),
      t('guests.gamesEmptyDetail', {}, 'admin'),
      'admin-guest-games-empty',
    );
    return html`<section class="admin-card" data-testid="admin-guest-games"><h3>${safe(t('guests.gamesTitle', {}, 'admin'))}</h3>${content}</section>`;
  }

  // Render one de-identified recent session row.
  function recentRow(row) {
    // Preserve detail navigation and active-only conversion selection.
    const detail = html`<button class="guest-detail-button" data-id="${safe(row.analytics_id)}" type="button">${safe(t('guests.viewDetail', {}, 'admin'))}</button>`;
    const convert = row.end_reason ? '' : html`<button class="guest-convert-button" data-id="${safe(row.analytics_id)}" type="button">${safe(t('guests.convertSelect', {}, 'admin'))}</button>`;
    const reason = row.end_reason || t('guests.statusActive', {}, 'admin');
    const values = [
      row.analytics_id, row.started_at, row.locale, row.device, reason,
      formatNumber(row.actions || 0), formatNumber(row.rounds_completed || 0), html`${detail}${convert}`,
    ];
    return html`<tr data-testid="admin-guest-row">${values.map(value => html`<td>${value}</td>`)}</tr>`;
  }

  // Render retained sessions or their accepted empty state.
  function recentSessions(summary) {
    // Preserve the complete eight-column recent-session contract.
    const heads = [
      'colId', 'colStarted', 'colLocale', 'colDevice',
      'colReason', 'colActions', 'colRounds', 'colDetail',
    ].map(key => t(`guests.${key}`, {}, 'admin'));
    const recent = summary.recent || [];
    const content = recent.length ? table(heads, recent.map(recentRow)) : emptyState(
      t('guests.empty', {}, 'admin'),
      t('guests.emptyDetail', {}, 'admin'),
      'admin-guest-empty',
    );
    return html`<section class="admin-card" data-testid="admin-guest-recent"><h3>${safe(t('guests.recentTitle', {}, 'admin'))}</h3>${content}</section>`;
  }

  // Render the initial detail prompt and retention health card.
  function detailAndCleanup(cleanup) {
    // Preserve the stable live-region detail outlet.
    const detailHeading = html`<h3>${safe(t('guests.detailTitle', {}, 'admin'))}</h3>`;
    const detailPrompt = html`<p>${safe(t('guests.detailPrompt', {}, 'admin'))}</p>`;
    const detail = html`<section id="guest-detail" class="admin-card" data-testid="admin-guest-detail" aria-live="polite">${detailHeading}${detailPrompt}</section>`;
    // Summarize retention health without runtime paths or exception text.
    const status = safe(t('guests.cleanupStatus', {
      raw: cleanup.raw_retention_days || 30,
      aggregate: cleanup.aggregate_retention_days || 400,
      time: cleanup.last_success_at || t('guests.cleanupNever', {}, 'admin'),
      failure: cleanup.last_failure_at || t('guests.cleanupNever', {}, 'admin'),
    }, 'admin'));
    const failed = cleanup.last_error === 'cleanup_failed';
    const healthHeading = html`<h3>${safe(t('guests.cleanupTitle', {}, 'admin'))}</h3>`;
    const health = html`<section class="admin-card" data-testid="admin-guest-cleanup-status" data-cleanup-failed="${failed}">${healthHeading}<p>${status}</p></section>`;
    return html`${detail}${health}`;
  }

  // Render the owner-governed admission switch.
  function policyCard(guestPolicy) {
    // Preserve current fixed token-grant explanation.
    const copy = safe(t('guests.policyCopy', {
      tokens: formatNumber(guestPolicy.starting_balance || 10000),
    }, 'admin'));
    const checked = guestPolicy.enabled ? html` checked` : '';
    const toggleInput = html`<input id="guest-trials-enabled" data-testid="admin-guest-trials-enabled" type="checkbox"${checked}>`;
    const toggle = html`<label class="check-row">${toggleInput}<span>${safe(t('guests.policyEnabled', {}, 'admin'))}</span></label>`;
    const save = html`<button id="guest-policy-save" data-testid="admin-save-guest-policy" type="button">${safe(t('guests.policySave', {}, 'admin'))}</button>`;
    return html`<section class="admin-card" data-testid="admin-guest-policy"><h3>${safe(t('guests.policyTitle', {}, 'admin'))}</h3><p>${copy}</p>${toggle}${save}</section>`;
  }

  // Render the explicitly confirmed support conversion form.
  function conversionCard() {
    // Preserve the bounded identity, account, and transient credential controls.
    const identityInput = html`<input id="guest-conversion-identity" data-testid="admin-guest-conversion-identity" autocomplete="off" maxlength="191" required>`;
    const emailInput = html`<input id="guest-conversion-email" data-testid="admin-guest-conversion-email" type="email" autocomplete="off" maxlength="254" required>`;
    const displayInput = html`<input id="guest-conversion-display-name" data-testid="admin-guest-conversion-display-name" maxlength="80" required>`;
    const passwordRules = html` autocomplete="new-password" minlength="12" maxlength="128" required`;
    const passwordInput = html`<input id="guest-conversion-password" data-testid="admin-guest-conversion-password" type="password"${passwordRules}>`;
    const fields = [
      html`<label>${safe(t('guests.convertIdentity', {}, 'admin'))}${identityInput}</label>`,
      html`<label>${safe(t('guests.convertEmail', {}, 'admin'))}${emailInput}</label>`,
      html`<label>${safe(t('guests.convertDisplayName', {}, 'admin'))}${displayInput}</label>`,
      html`<label>${safe(t('guests.convertPassword', {}, 'admin'))}${passwordInput}</label>`,
    ];
    // Preserve explicit confirmation and one primary submit action.
    const confirmInput = html`<input id="guest-conversion-confirm" data-testid="admin-guest-conversion-confirm" type="checkbox" required>`;
    const confirmation = html`<label class="check-row">${confirmInput}<span>${safe(t('guests.convertConfirm', {}, 'admin'))}</span></label>`;
    const submit = html`<button id="guest-conversion-submit" data-testid="admin-guest-conversion-submit" type="submit">${safe(t('guests.convertSubmit', {}, 'admin'))}</button>`;
    const form = html`<form id="admin-guest-conversion-form" class="grid3">${fields}${confirmation}${submit}</form>`;
    const heading = html`<h3>${safe(t('guests.convertTitle', {}, 'admin'))}</h3>`;
    const copy = html`<p>${safe(t('guests.convertCopy', {}, 'admin'))}</p>`;
    return html`<section class="admin-card" data-testid="admin-guest-conversion">${heading}${copy}${form}</section>`;
  }

  // Render time, game, completion, and sanitized error filters.
  function extendedFilters(games) {
    // Preserve bounded time-window shortcuts.
    const all = t('guests.filterAll', {}, 'admin');
    const ranges = [
      option('', all, guestFilters.range),
      option('1', t('guests.rangeDay', {}, 'admin'), guestFilters.range),
      option('7', t('guests.rangeWeek', {}, 'admin'), guestFilters.range),
      option('30', t('guests.rangeMonth', {}, 'admin'), guestFilters.range),
    ];
    const range = html`<label>${safe(t('guests.filterRange', {}, 'admin'))}<select id="guest-filter-range">${ranges}</select></label>`;
    // Build game options from retained aggregates plus any current selection.
    const gameKeys = [...new Set([guestFilters.game, ...games.map(row => row.game)].filter(Boolean))].sort();
    const gameOptions = [option('', all, guestFilters.game), ...gameKeys.map(game => (
      option(game, humanLabel(game), guestFilters.game)
    ))];
    const game = html`<label>${safe(t('guests.filterGame', {}, 'admin'))}<select id="guest-filter-game">${gameOptions}</select></label>`;
    // Preserve explicit completed-round filtering.
    const completionOptions = [
      option('', all, guestFilters.completed),
      option('yes', t('guests.filterYes', {}, 'admin'), guestFilters.completed),
      option('no', t('guests.filterNo', {}, 'admin'), guestFilters.completed),
    ];
    const completed = html`<label>${safe(t('guests.filterCompleted', {}, 'admin'))}<select id="guest-filter-completed">${completionOptions}</select></label>`;
    // Preserve only allowlisted server error categories.
    const errors = [
      option('', all, guestFilters.error_category),
      ...ERROR_CATEGORIES.map(category => option(category, humanLabel(category), guestFilters.error_category)),
    ];
    const error = html`<label>${safe(t('guests.filterError', {}, 'admin'))}<select id="guest-filter-error_category">${errors}</select></label>`;
    return html`${range}${game}${completed}${error}`;
  }

  // Render complete product-measurement summary cards.
  function metricCards(metrics) {
    // Preserve fake-token labels and percentage/unit suffixes.
    return [
      summaryCard('guests.averageDuration', `${formatNumber(metrics.average_duration_seconds || 0)}s`),
      summaryCard('guests.medianDuration', `${formatNumber(metrics.median_duration_seconds || 0)}s`),
      summaryCard('guests.gamesPerTrial', formatNumber(metrics.average_games_per_trial || 0)),
      summaryCard('guests.roundsPerTrial', formatNumber(metrics.average_rounds_per_trial || 0)),
      summaryCard('guests.errorFreeRate', `${formatNumber(metrics.error_free_rate_percent || 0)}%`),
      summaryCard('guests.fakeWagered', formatMoney(metrics.wagered || 0)),
      summaryCard('guests.fakeReturned', formatMoney(metrics.returned || 0)),
      summaryCard('guests.fakeNet', formatMoney(metrics.net || 0)),
    ];
  }

  // Render the complete milestone funnel with counts and rates.
  function funnelCard(funnel, funnelRates) {
    // Preserve localized stage labels in owner-approved order.
    const rows = FUNNEL_STAGES.map((stage) => {
      // Preserve localized milestone label, count, and percentage.
      const values = [
        t(`guests.funnel.${stage}`, {}, 'admin'),
        formatNumber(funnel[stage] || 0),
        `${formatNumber(funnelRates[stage] || 0)}%`,
      ];
      return html`<tr>${values.map(value => html`<td>${safe(value)}</td>`)}</tr>`;
    });
    const heads = [
      t('guests.funnelStage', {}, 'admin'),
      t('guests.funnelCount', {}, 'admin'),
      t('guests.funnelRate', {}, 'admin'),
    ];
    return html`<section class="admin-card" data-testid="admin-guest-funnel"><h3>${safe(t('guests.funnelTitle', {}, 'admin'))}</h3>${table(heads, rows)}</section>`;
  }

  // Render complete per-game acceptance metrics.
  function gameDetailCard(games) {
    // Preserve every published game metric and fake-token aggregate.
    const rows = games.map((row) => {
      // Format allowlisted action-category keys without raw enum casing.
      const categories = Object.keys(row.action_categories || {}).map(humanLabel).join(', ') || '—';
      const values = [
        humanLabel(row.game),
        formatNumber(row.rounds_started || 0),
        formatNumber(row.rounds_completed || 0),
        formatNumber(row.rounds_abandoned || 0),
        formatNumber(row.errors || 0),
        `${formatNumber(row.median_first_action_ms || 0)}ms`,
        formatMoney(row.wagered || 0),
        formatMoney(row.returned || 0),
        formatMoney(row.net || 0),
        categories,
      ];
      return html`<tr>${values.map(value => html`<td>${safe(value)}</td>`)}</tr>`;
    });
    const heads = [
      'colGame', 'colStartedRounds', 'colRounds', 'colAbandoned', 'colErrors',
      'colFirstAction', 'colWagered', 'colReturned', 'colNet', 'colCategories',
    ].map(key => t(`guests.${key}`, {}, 'admin'));
    const content = games.length ? table(heads, rows) : emptyState(
      t('guests.gamesEmpty', {}, 'admin'),
      t('guests.gamesEmptyDetail', {}, 'admin'),
    );
    return html`<section class="admin-card" data-testid="admin-guest-game-detail"><h3>${safe(t('guests.gameMetricsTitle', {}, 'admin'))}</h3>${content}</section>`;
  }

  // Apply keyboard-scroll region semantics to every wide analytics surface.
  function bindScrollRegions() {
    // Name each region from its heading while preserving a localized fallback.
    view.querySelectorAll(
      '[data-testid="admin-guest-funnel"], [data-testid="admin-guest-games"], '
      + '[data-testid="admin-guest-game-detail"], [data-testid="admin-guest-recent"]',
    ).forEach((region) => {
      // Make the region keyboard reachable on narrow viewports.
      region.tabIndex = 0;
      region.setAttribute('role', 'region');
      region.setAttribute('aria-label', region.querySelector('h3')?.textContent || t('nav.guests', {}, 'admin'));
    });
  }

  // Bind allowlisted filter, detail, and conversion-selection actions.
  function bindNavigationActions() {
    // Reload whenever one published filter changes.
    Object.keys(INITIAL_FILTERS).forEach((name) => {
      // Persist the selected value before requesting a coherent fresh snapshot.
      view.querySelector(`#guest-filter-${name}`).onchange = (event) => {
        guestFilters[name] = event.target.value;
        void guests();
      };
    });
    // Bind de-identified detail navigation.
    view.querySelectorAll('.guest-detail-button').forEach((button) => {
      // Use only the server-returned analytics identity.
      button.onclick = () => showGuestDetail(button.dataset.id);
    });
    // Bind active-row conversion shortcuts to the visible analytics id.
    view.querySelectorAll('.guest-convert-button').forEach((button) => {
      // Populate and focus only the de-identified support field.
      button.onclick = () => {
        const identity = view.querySelector('#guest-conversion-identity');
        identity.value = button.dataset.id;
        identity.focus();
      };
    });
  }

  // Bind one explicitly confirmed assisted-conversion operation.
  function bindConversion(conversionIdempotencyKey) {
    // Keep one caller-owned key stable across a lost-response retry of this rendered form.
    view.querySelector('#admin-guest-conversion-form').onsubmit = async (event) => {
      // Prevent navigation so the tab and scroll position remain stable.
      event.preventDefault();
      const password = view.querySelector('#guest-conversion-password');
      const confirmation = view.querySelector('#guest-conversion-confirm');
      const submit = view.querySelector('#guest-conversion-submit');
      // Disable the primary action while this exact request settles.
      submit.disabled = true;
      try {
        // Send exact account fields; the server derives the guest locale.
        await post('/api/v2/admin/guest-trials/convert', {
          guest_identity: view.querySelector('#guest-conversion-identity').value.trim(),
          email: view.querySelector('#guest-conversion-email').value.trim(),
          password: password.value,
          display_name: view.querySelector('#guest-conversion-display-name').value.trim(),
          terms_version: 'private-beta-1',
          accepted: true,
          confirm: confirmation.checked,
          idempotency_key: conversionIdempotencyKey,
        });
        // Announce completion without identity or mailbox content.
        toast(t('guests.convertComplete', {}, 'admin'), true);
        await guests();
      } catch (_) {
        // Announce a generic failure without confirming target existence.
        toast(t('guests.convertFailed', {}, 'admin'));
        submit.disabled = false;
      } finally {
        // Remove transient credentials from connected DOM controls.
        if (password.isConnected) password.value = '';
        // Require a new explicit confirmation for any retry.
        if (confirmation.isConnected) confirmation.checked = false;
      }
    };
  }

  // Bind retention cleanup and owner-only admission policy actions.
  function bindPolicyActions() {
    // Run idempotent retention cleanup and refresh either outcome.
    view.querySelector('#guest-cleanup').onclick = async () => {
      try {
        // Invoke only the protected Guest Trials cleanup route.
        await post('/api/v2/admin/guest-trials/cleanup', {});
        toast(t('guests.cleanupComplete', {}, 'admin'), true);
      } catch (_) {
        // Keep bounded failures inside the localized Admin surface.
        toast(t('guests.cleanupFailed', {}, 'admin'));
      }
      await guests();
    };
    // Change the owner-only admission switch without affecting current principals.
    view.querySelector('#guest-policy-save').onclick = async () => {
      try {
        // Submit only the exact enabled state.
        await post('/api/v2/admin/guest-trials/settings', {
          enabled: view.querySelector('#guest-trials-enabled').checked,
        });
        toast(t('guests.policySaved', {}, 'admin'), true);
      } catch (_) {
        // Preserve generic failure feedback.
        toast(t('guests.policyFailed', {}, 'admin'));
      }
      await guests();
    };
  }

  // Render and bind the complete coherent telemetry snapshot.
  function renderSnapshot(summary, guestPolicy) {
    // Read all optional aggregates with safe defaults.
    const funnel = summary.funnel || {};
    const games = summary.games || [];
    const cleanup = summary.cleanup || {};
    // Install the base surfaces atomically.
    view.innerHTML = html`${baseFilters()}${summaryCards(summary, funnel)}${compactGames(games)}${recentSessions(summary)}${detailAndCleanup(cleanup)}`;
    const filters = view.querySelector('[data-testid="admin-guest-filters"]');
    // Insert owner controls before analytics in the accepted order.
    filters.insertAdjacentHTML('beforebegin', policyCard(guestPolicy));
    filters.insertAdjacentHTML('beforebegin', conversionCard());
    // Extend filter and metric grids without replacing compatibility surfaces.
    view.querySelector('.guest-filter-grid').insertAdjacentHTML('beforeend', extendedFilters(games));
    view.querySelector('[data-testid="admin-guest-summary"]').insertAdjacentHTML(
      'beforeend',
      html`${metricCards(summary.metrics || {})}`,
    );
    // Insert full funnel and game metrics around the compact game table.
    const compact = view.querySelector('[data-testid="admin-guest-games"]');
    compact.insertAdjacentHTML('beforebegin', funnelCard(funnel, summary.funnel_rates || {}));
    compact.insertAdjacentHTML('afterend', gameDetailCard(games));
    // Bind all interaction groups after every surface is installed.
    bindScrollRegions();
    bindNavigationActions();
    bindConversion(crypto.randomUUID());
    bindPolicyActions();
  }

  // Render the de-identified Guest Trials telemetry section.
  async function guests() {
    // Set the localized heading and announce loading before the request resolves.
    setTitle(t('nav.guests', {}, 'admin'), t('guests.subtitle', {}, 'admin'));
    const loadingTitle = html`<h2>${safe(t('guests.loadingTitle', {}, 'admin'))}</h2>`;
    const loadingDetail = html`<p>${safe(t('guests.loadingDetail', {}, 'admin'))}</p>`;
    view.innerHTML = html`<section class="admin-card loading-panel" data-testid="admin-guest-loading" role="status">${loadingTitle}${loadingDetail}</section>`;
    // Encode only published filters while keeping the UI-only range shortcut local.
    const entries = Object.entries(guestFilters).filter(([name, value]) => name !== 'range' && value);
    const params = new URLSearchParams(entries);
    // Convert the bounded time window to the contract's inclusive UTC lower bound.
    if (guestFilters.range) {
      params.set('since', new Date(Date.now() - Number(guestFilters.range) * 86400000).toISOString());
    }
    // Load analytics and current admission control as one coherent snapshot.
    const [data, settingsData] = await Promise.all([
      api(`/api/v2/admin/guest-trials?${params.toString()}`),
      api('/api/v2/admin/guest-trials/settings'),
    ]);
    // Stop when another tab took over during the async load.
    if (!isActiveTab('guests')) return;
    // Render safe defaults for absent optional response sections.
    renderSnapshot(
      data.guest_trials || {},
      settingsData.settings || { enabled: false, starting_balance: 10000 },
    );
  }

  // Render one de-identified Guest Trials analytics detail record.
  async function showGuestDetail(analyticsId) {
    // Load only the analytics-id route published by the Admin v2 contract.
    const data = await api(`/api/v2/admin/guest-trials/sessions/${encodeURIComponent(analyticsId)}`);
    const row = data.guest_trial || {};
    // Stop if the user changed tabs while the request was in flight.
    const detail = view.querySelector('#guest-detail');
    if (!detail) return;
    // Render bounded lifecycle, locale, device, and per-game counters.
    const lifecycle = [
      ['colId', row.analytics_id],
      ['colLocale', row.locale],
      ['colDevice', row.device],
      ['colDuration', row.duration_seconds == null ? '—' : formatNumber(row.duration_seconds)],
      ['colActions', formatNumber(row.actions || 0)],
      ['colRounds', formatNumber(row.rounds_completed || 0)],
    ].map(([key, value]) => html`<div><dt>${safe(t(`guests.${key}`, {}, 'admin'))}</dt><dd>${safe(value)}</dd></div>`);
    detail.innerHTML = html`<h3>${safe(t('guests.detailTitle', {}, 'admin'))}</h3><dl class="guest-detail-grid">${lifecycle}</dl>`;
    // Preserve fake-token aggregates without any auth identity.
    const balance = row.ending_balance == null ? t('guests.notAvailable', {}, 'admin') : formatMoney(row.ending_balance);
    const totals = [
      ['colStartingBalance', formatMoney(row.starting_balance || 0)],
      ['colEndingBalance', balance],
      ['colWagered', formatMoney(row.wagered || 0)],
      ['colReturned', formatMoney(row.returned || 0)],
      ['colNet', formatMoney(row.net || 0)],
      ['colErrors', formatNumber(row.errors || 0)],
    ].map(([key, value]) => html`<div><dt>${safe(t(`guests.${key}`, {}, 'admin'))}</dt><dd>${safe(value)}</dd></div>`);
    // Render the bounded allowlisted event timeline.
    const events = Array.isArray(row.events) ? row.events : [];
    const eventRows = events.map((event) => {
      // Preserve only published event, game, category, error, and latency values.
      const values = [
        humanLabel(event.event),
        event.at,
        humanLabel(event.game || ''),
        humanLabel(event.action_category || ''),
        humanLabel(event.error_category || ''),
        humanLabel(event.latency_bucket || ''),
      ];
      return html`<tr>${values.map(value => html`<td>${safe(value || '')}</td>`)}</tr>`;
    });
    const eventHeads = [
      'timelineEvent', 'timelineTime', 'colGame',
      'timelineCategory', 'filterError', 'timelineLatency',
    ].map(key => t(`guests.${key}`, {}, 'admin'));
    const timeline = events.length ? table(eventHeads, eventRows) : emptyState(
      t('guests.timelineEmpty', {}, 'admin'),
      t('guests.timelineEmptyDetail', {}, 'admin'),
    );
    const timelineSection = html`<section data-testid="admin-guest-timeline"><h4>${safe(t('guests.timelineTitle', {}, 'admin'))}</h4>${timeline}</section>`;
    detail.insertAdjacentHTML('beforeend', html`<dl class="guest-detail-grid">${totals}</dl>${timelineSection}`);
    // Make the timeline keyboard-scrollable on narrow Admin viewports.
    detail.querySelector('[data-testid="admin-guest-timeline"]').tabIndex = 0;
  }

  // Publish only the dispatcher-facing Guest Trials renderer.
  return guests;
}
