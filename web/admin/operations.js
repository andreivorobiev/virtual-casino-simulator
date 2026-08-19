// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build trusted Operations, OAuth, and mail diagnostics behind a dedicated Admin tab. (ADMIN-014, MAIL-003)
export function createOperationsTab(dependencies) {
  // Capture the established diagnostic and presentation helpers.
  const { api, formatDate, html, isActiveTab, safe, setTitle, t, table, view } = dependencies;

  // Render one compact two-column diagnostic row.
  function diagnosticRow(label, value) {
    // Preserve localized labels and already-bounded diagnostic values.
    return html`<tr><td>${safe(label)}</td><td>${safe(value)}</td></tr>`;
  }

  // Render OAuth diagnostics independently from Operations health.
  function oauthDiagnosticsCard(data) {
    // Keep only the three provider identifiers owned by the disabled catalog.
    const providers = Array.isArray(data?.providers)
      ? data.providers.filter(provider => ['local', 'google', 'facebook'].includes(provider?.provider))
      : [];
    // Render explicit unavailable state when the independent response fails validation.
    if (providers.length !== 3) {
      // Preserve the named unavailable card and calm copy.
      const heading = html`<h2>${safe(t('oauth.title', {}, 'admin'))}</h2>`;
      const detail = html`<p>${safe(t('oauth.unavailable', {}, 'admin'))}</p>`;
      return html`<section class="admin-card" data-testid="admin-oauth-diagnostics-unavailable">${heading}${detail}</section>`;
    }
    // Build one allowlisted row without callback URLs or environment details.
    const rows = providers.map((provider) => {
      // Normalize configuration and runtime values to published translation keys.
      const configurationStatus = ['ready', 'disabled', 'misconfigured'].includes(provider.status)
        ? provider.status
        : 'unknown';
      const runtimeStatus = provider.runtime_available === true ? 'available' : 'unavailable';
      // Preserve stable provider and runtime test hooks.
      const identity = html` data-testid="admin-oauth-provider-${safe(provider.provider)}" data-runtime-available="${provider.runtime_available === true}"`;
      const providerCell = html`<td>${safe(t(`oauth.provider.${provider.provider}`, {}, 'admin'))}</td>`;
      const configuration = html`<td>${safe(t(`oauth.configuration.${configurationStatus}`, {}, 'admin'))}</td>`;
      const runtime = html`<td>${safe(t(`oauth.runtime.${runtimeStatus}`, {}, 'admin'))}</td>`;
      // Return one compact localized row.
      return html`<tr${identity}>${providerCell}${configuration}${runtime}</tr>`;
    });
    // Preserve the separate provider card and exact table columns.
    const evidence = table([
      t('oauth.field.provider', {}, 'admin'),
      t('oauth.field.configuration', {}, 'admin'),
      t('oauth.field.runtime', {}, 'admin'),
    ], rows);
    const heading = html`<h2>${safe(t('oauth.title', {}, 'admin'))}</h2>`;
    const detail = html`<p>${safe(t('oauth.subtitle', {}, 'admin'))}</p>`;
    return html`<section class="admin-card" data-testid="admin-oauth-diagnostics">${heading}${detail}${evidence}</section>`;
  }

  // Replace only the independent OAuth card when its request settles.
  function replaceOAuthDiagnosticsCard(data) {
    // Ignore delayed diagnostics after the user leaves Operations.
    if (!isActiveTab('operations')) return;
    // Replace the loading, unavailable, or populated card in place.
    const card = view.querySelector('[data-testid^="admin-oauth-diagnostics"]');
    if (card) card.outerHTML = oauthDiagnosticsCard(data);
  }

  // Render transactional-mail diagnostics independently from other health. (MAIL-003)
  function mailDiagnosticsCard(data) {
    // Constrain backend state and provider values to published identifiers.
    const status = ['disabled', 'misconfigured', 'release_held', 'ready', 'unavailable'].includes(data?.status)
      ? data.status
      : 'unavailable';
    const provider = ['disabled', 'postmark', 'unrecognized'].includes(data?.provider)
      ? data.provider
      : 'unrecognized';
    // Normalize aggregate counts without accepting record identifiers or negatives.
    const summary = data?.delivery_summary && typeof data.delivery_summary === 'object'
      ? data.delivery_summary
      : {};
    const count = key => Number.isInteger(summary[key]) && summary[key] >= 0 ? summary[key] : 0;
    // Retain only contract-allowlisted remediation reasons.
    const allowedReasons = [
      'feature_disabled', 'provider_not_configured', 'canonical_origin_invalid',
      'sender_identity_invalid', 'provider_credential_missing', 'digest_key_invalid',
      'network_release_held', 'state_recovery_required',
    ];
    const reasons = Array.isArray(data?.reasons)
      ? data.reasons.filter(reason => allowedReasons.includes(reason))
      : [];
    // Normalize the de-identified suppression count independently.
    const suppressedRecipients = Number.isInteger(data?.suppressed_recipients)
      && data.suppressed_recipients >= 0
      ? data.suppressed_recipients
      : 0;
    // Build the explicit state header with a non-color badge.
    const stateCopy = html`<div><h2>${safe(t('mail.title', {}, 'admin'))}</h2><p>${safe(t(`mail.detail.${status}`, {}, 'admin'))}</p></div>`;
    const stateBadge = html`<span class="badge">${safe(t(`mail.state.${status}`, {}, 'admin'))}</span>`;
    const state = html`<div class="row">${stateCopy}${stateBadge}</div>`;
    // Build aggregate-only lifecycle evidence.
    const evidence = table([
      t('mail.field', {}, 'admin'),
      t('mail.value', {}, 'admin'),
    ], [
      diagnosticRow(t('mail.provider', {}, 'admin'), t(`mail.provider.${provider}`, {}, 'admin')),
      diagnosticRow(t('mail.sent', {}, 'admin'), count('sent')),
      diagnosticRow(t('mail.retryWait', {}, 'admin'), count('retry_wait')),
      diagnosticRow(t('mail.failed', {}, 'admin'), count('failed')),
      diagnosticRow(t('mail.uncertain', {}, 'admin'), count('uncertain')),
    ]);
    // Preserve de-identified suppression summary and optional remediation list.
    const suppressionHeading = html`<h3>${safe(t('mail.suppressionTitle', {}, 'admin'))}</h3>`;
    const suppressionCount = html`<p>${safe(t('mail.suppressionCount', { count: suppressedRecipients }, 'admin'))}</p>`;
    const suppression = html`<div data-testid="admin-mail-suppression-summary">${suppressionHeading}${suppressionCount}</div>`;
    const attention = reasons.length
      ? html`<h3>${safe(t('mail.attention', {}, 'admin'))}</h3><ul>${reasons.map(reason => html`<li>${safe(t(`mail.reason.${reason}`, {}, 'admin'))}</li>`)}</ul>`
      : '';
    // Return the exact independent mail card.
    const danger = ['misconfigured', 'unavailable'].includes(status) ? 'danger' : '';
    return html`<section class="admin-card ${danger}" data-testid="admin-mail-${status}">${state}${evidence}${suppression}${attention}</section>`;
  }

  // Replace only the independent mail card when its request settles.
  function replaceMailDiagnosticsCard(data) {
    // Ignore delayed diagnostics after the user leaves Operations.
    if (!isActiveTab('operations')) return;
    // Replace the loading, unavailable, or populated card in place.
    const card = view.querySelector('[data-testid^="admin-mail-"]');
    if (card) card.outerHTML = mailDiagnosticsCard(data);
  }

  // Render trusted dependency and heartbeat telemetry for Admin users.
  async function operations() {
    // Set localized Operations chrome before the request.
    setTitle(t('operations.title', {}, 'admin'), t('operations.subtitle', {}, 'admin'));
    // Convert network loss into explicit down state without raw error text.
    try {
      // Load only Operations before classifying live or degraded.
      const data = await api('/api/v2/admin/operations');
      // Stop a stale response from replacing another selected tab.
      if (!isActiveTab('operations')) return;
      // Select fixed state and provider labels.
      const stateKey = data.ready ? 'live' : 'degraded';
      const providerLabel = t(`operations.provider.${data.storage_provider}`, {}, 'admin');
      const reasonLabels = (data.reasons || [])
        .map(reason => t(`operations.reason.${reason.code}`, {}, 'admin'));
      // Normalize optional build and heartbeat evidence.
      const buildSha = data.build?.sha || t('operations.unavailable', {}, 'admin');
      const heartbeat = data.last_successful_heartbeat_at
        ? formatDate(new Date(data.last_successful_heartbeat_at), {
          dateStyle: 'medium',
          timeStyle: 'medium',
        })
        : t('operations.unavailable', {}, 'admin');
      // Build the non-color state heading and trusted evidence table.
      const stateCopy = html`<div><h2>${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</h2><p>${safe(t(`operations.detail.${stateKey}`, {}, 'admin'))}</p></div>`;
      const stateLabel = safe(t(`operations.state.${stateKey}`, {}, 'admin'));
      const stateSymbol = safe(t(`operations.symbol.${stateKey}`, {}, 'admin'));
      const stateBadge = html`<span class="badge" data-testid="admin-operations-state">${stateSymbol} ${stateLabel}</span>`;
      const heading = html`<div class="row">${stateCopy}${stateBadge}</div>`;
      const evidence = table([
        t('operations.field', {}, 'admin'),
        t('operations.value', {}, 'admin'),
      ], [
        diagnosticRow(t('operations.storage', {}, 'admin'), providerLabel),
        diagnosticRow(t('operations.appVersion', {}, 'admin'), data.build.app_version),
        diagnosticRow(t('operations.buildSha', {}, 'admin'), buildSha),
        diagnosticRow(t('operations.lastHeartbeat', {}, 'admin'), heartbeat),
      ]);
      // Preserve optional localized attention reasons.
      const attention = reasonLabels.length
        ? html`<h3>${safe(t('operations.attention', {}, 'admin'))}</h3><ul>${reasonLabels.map(label => html`<li>${safe(label)}</li>`)}</ul>`
        : '';
      // Render Operations first with independent diagnostic placeholders.
      const danger = data.ready ? '' : 'danger';
      const operationsCard = html`<section class="admin-card ${danger}" data-testid="admin-operations-${stateKey}">${heading}${evidence}${attention}</section>`;
      view.innerHTML = html`${operationsCard}${oauthDiagnosticsCard(null)}${mailDiagnosticsCard(null)}`;
      // Start provider and mail diagnostics independently after Operations is visible.
      api('/api/v2/admin/oauth/providers')
        .then(replaceOAuthDiagnosticsCard)
        .catch(() => replaceOAuthDiagnosticsCard(null));
      api('/api/v2/admin/mail/readiness')
        .then(replaceMailDiagnosticsCard)
        .catch(() => replaceMailDiagnosticsCard(null));
    } catch (error) {
      // Avoid replacing a newer tab after delayed transport failure.
      if (!isActiveTab('operations')) return;
      // Preserve a clear symbol and recovery instruction.
      const heading = html`<h2>${safe(t('operations.symbol.down', {}, 'admin'))} ${safe(t('operations.state.down', {}, 'admin'))}</h2>`;
      const detail = html`<p>${safe(t('operations.detail.down', {}, 'admin'))}</p>`;
      view.innerHTML = html`<section class="admin-card danger" data-testid="admin-operations-down">${heading}${detail}</section>`;
    }
  }

  // Publish only the dispatcher-facing Operations renderer.
  return operations;
}
