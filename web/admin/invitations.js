// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build private invitation readiness and lifecycle behind a dedicated tab boundary. (INVITE-001, INVITE-005)
export function createInvitationsTab(dependencies) {
  // Capture the established privacy-safe lifecycle and presentation helpers.
  const {
    api, emptyState, formatNumber, html, humanLabel, isActiveTab, localeOptions,
    post, safe, setTitle, t, table, toast, view,
  } = dependencies;

  // Render one readiness definition-list item.
  function statusItem(label, value) {
    // Preserve the established term/value topology.
    return html`<div><dt>${safe(label)}</dt><dd>${safe(value)}</dd></div>`;
  }

  // Render one recipient-masked invitation lifecycle row.
  function invitationRow(row, enabled) {
    // Preserve privacy-safe recipient, lifecycle, delivery, locale, and update evidence.
    const identity = html`<td>${safe(row.recipient_hint || t('invitations.masked', {}, 'admin'))}</td><td>${safe(humanLabel(row.status))}</td>`;
    const delivery = html`<td>${safe(humanLabel(row.delivery_status || 'none'))}</td><td>${safe(row.locale)}</td><td>${safe(row.updated_at || '')}</td>`;
    const evidence = html`${identity}${delivery}`;
    // Permit resend only for live pending or delivery-failed invitations while issuance is enabled.
    const retryable = ['pending', 'delivery_failed'].includes(row.status);
    const resendDisabled = retryable && enabled ? '' : 'disabled';
    const revokeDisabled = retryable ? '' : 'disabled';
    // Preserve distinct idempotent resend and emergency revoke controls.
    const resend = html`<button type="button" class="invitation-resend" data-id="${safe(row.invitation_id)}" ${resendDisabled}>${safe(t('invitations.resend', {}, 'admin'))}</button>`;
    const revoke = html`<button type="button" class="invitation-revoke" data-id="${safe(row.invitation_id)}" ${revokeDisabled}>${safe(t('invitations.revoke', {}, 'admin'))}</button>`;
    // Return one stable lifecycle row.
    return html`<tr data-testid="admin-invitation-row" data-status="${safe(row.status)}">${evidence}<td>${resend}${revoke}</td></tr>`;
  }

  // Build the secret-free invitation readiness card.
  function readinessCard(data, readiness) {
    // Preserve the four low-cardinality readiness values.
    const issuance = data.enabled ? t('common.enabled', {}, 'admin') : t('common.disabled', {}, 'admin');
    const redemption = data.redemption_enabled
      ? t('common.enabled', {}, 'admin')
      : t('common.disabled', {}, 'admin');
    const items = [
      statusItem(t('invitations.issuance', {}, 'admin'), issuance),
      statusItem(t('invitations.redemption', {}, 'admin'), redemption),
      statusItem(t('invitations.delivery', {}, 'admin'), humanLabel(data.mail_status || 'unavailable')),
      statusItem(t('invitations.recovery', {}, 'admin'), formatNumber(data.recovery_required || 0)),
    ];
    // Preserve the exact state marker and boundary copy.
    const heading = html`<h2>${safe(t(`invitations.states.${readiness}`, {}, 'admin'))}</h2>`;
    const boundary = html`<p>${safe(t('invitations.boundary', {}, 'admin'))}</p>`;
    const details = html`<dl class="guest-detail-grid">${items}</dl>`;
    return html`<section class="admin-card" data-testid="admin-invitations-${safe(readiness)}">${heading}${boundary}${details}</section>`;
  }

  // Build the bounded invitation issuance form.
  function creationCard(data) {
    // Preserve recipient and locale controls without retaining either after submission.
    const recipientLabel = safe(t('invitations.recipient', {}, 'admin'));
    const recipient = html`<label>${recipientLabel}<input id="invitation-recipient" type="email" autocomplete="off" maxlength="254" data-testid="admin-invitation-recipient"></label>`;
    const locale = html`<label>${safe(t('invitations.locale', {}, 'admin'))}<select id="invitation-locale" data-testid="admin-invitation-locale">${localeOptions('en-US')}</select></label>`;
    // Gate issuance on both feature and delivery readiness.
    const disabled = data.enabled && data.mail_status === 'ready' ? '' : 'disabled';
    const action = html`<button id="invitation-create" type="button" data-testid="admin-invitation-submit" ${disabled}>${safe(t('invitations.send', {}, 'admin'))}</button>`;
    // Return the exact accepted form and help copy.
    const heading = html`<h3>${safe(t('invitations.createTitle', {}, 'admin'))}</h3>`;
    const form = html`<div class="grid3">${recipient}${locale}${action}</div>`;
    const help = html`<p class="muted">${safe(t('invitations.createHelp', {}, 'admin'))}</p>`;
    return html`<section class="admin-card" data-testid="admin-invitation-create">${heading}${form}${help}</section>`;
  }

  // Build the keyboard-scrollable privacy-safe lifecycle region.
  function lifecycleCard(rows, enabled) {
    // Render the bounded rows or their calm empty state.
    const content = rows.length
      ? table([
        t('invitations.recipient', {}, 'admin'),
        t('invitations.status', {}, 'admin'),
        t('invitations.delivery', {}, 'admin'),
        t('invitations.locale', {}, 'admin'),
        t('invitations.updated', {}, 'admin'),
        t('invitations.actions', {}, 'admin'),
      ], rows.map(row => invitationRow(row, enabled)))
      : emptyState(
        t('invitations.empty', {}, 'admin'),
        t('invitations.emptyDetail', {}, 'admin'),
        'admin-invitation-empty',
      );
    // Preserve the named keyboard-scrollable region.
    const heading = html`<h3>${safe(t('invitations.listTitle', {}, 'admin'))}</h3>`;
    const label = safe(t('invitations.listTitle', {}, 'admin'));
    return html`<section class="admin-card" data-testid="admin-invitation-list" tabindex="0" role="region" aria-label="${label}">${heading}${content}</section>`;
  }

  // Render disabled-by-default invitation readiness, issuance, and lifecycle controls.
  async function invitations() {
    // Set the localized heading and restricted-preview boundary.
    setTitle(t('invitations.title', {}, 'admin'), t('invitations.subtitle', {}, 'admin'));
    // Announce loading before the Admin-only diagnostic resolves.
    const loadingHeading = html`<h2>${safe(t('invitations.loadingTitle', {}, 'admin'))}</h2>`;
    const loadingDetail = html`<p>${safe(t('invitations.loadingDetail', {}, 'admin'))}</p>`;
    view.innerHTML = html`<section class="admin-card loading-panel" data-testid="admin-invitation-loading" role="status">${loadingHeading}${loadingDetail}</section>`;
    // Load the bounded, recipient-masked lifecycle list.
    const data = await api('/api/v2/admin/invitations?limit=100');
    // Stop a stale request from replacing another selected tab.
    if (!isActiveTab('invitations')) return;
    // Normalize rows and derive the stable readiness state.
    const rows = Array.isArray(data.invitations) ? data.invitations : [];
    const readiness = !data.enabled
      ? 'disabled'
      : data.mail_status !== 'ready'
        ? 'release-held'
        : data.redemption_enabled ? 'ready' : 'redemption-held';
    // Replace the tab atomically in readiness, create, lifecycle order.
    view.innerHTML = html`${readinessCard(data, readiness)}${creationCard(data)}${lifecycleCard(rows, data.enabled)}`;
    // Bind issuance only when delivery readiness enabled its control.
    view.querySelector('#invitation-create').onclick = async () => {
      // Read the transient mailbox and locale only at submit time.
      const recipientInput = view.querySelector('#invitation-recipient');
      const payload = {
        recipient: recipientInput.value,
        locale: view.querySelector('#invitation-locale').value,
        idempotency_key: crypto.randomUUID(),
      };
      // Disable duplicate clicks until the exact response settles.
      view.querySelector('#invitation-create').disabled = true;
      // Submit through the approved Admin v2 route.
      await post('/api/v2/admin/invitations', payload);
      // Clear the raw mailbox before any evidence can be captured.
      recipientInput.value = '';
      // Announce success without repeating the recipient and reload.
      toast(t('invitations.created', {}, 'admin'), true);
      await invitations();
    };
    // Bind every eligible resend to one fresh caller replay key.
    view.querySelectorAll('.invitation-resend').forEach((button) => {
      // Preserve row-owned invitation identity and exact resend route.
      button.onclick = async () => {
        // Disable duplicate clicks until the request settles.
        button.disabled = true;
        await post(`/api/v2/admin/invitations/${encodeURIComponent(button.dataset.id)}/resend`, {
          idempotency_key: crypto.randomUUID(),
        });
        // Announce privacy-safe completion and reload.
        toast(t('invitations.resent', {}, 'admin'), true);
        await invitations();
      };
    });
    // Bind emergency revoke independently from issuance readiness.
    view.querySelectorAll('.invitation-revoke').forEach((button) => {
      // Preserve row-owned invitation identity and exact revoke route.
      button.onclick = async () => {
        // Disable duplicate clicks until the request settles.
        button.disabled = true;
        await post(`/api/v2/admin/invitations/${encodeURIComponent(button.dataset.id)}/revoke`, {
          idempotency_key: crypto.randomUUID(),
        });
        // Announce privacy-safe completion and reload.
        toast(t('invitations.revoked', {}, 'admin'), true);
        await invitations();
      };
    });
  }

  // Publish only the dispatcher-facing Invitations renderer.
  return invitations;
}
