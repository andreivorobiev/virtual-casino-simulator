// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build owner enrollment and provider governance behind a dedicated tab boundary. (AUTH-015)
export function createEnrollmentTab(dependencies) {
  // Capture the established policy, readiness, and presentation helpers.
  const {
    api, emptyState, html, humanLabel, isActiveTab, option, post, safe, setTitle, t, table, toast, view,
  } = dependencies;

  // Render one enrollment-method policy checkbox.
  function methodControl(method, policy) {
    // Preserve the durable enabled state as the checked projection.
    const checked = policy.methods?.[method] ? 'checked' : '';
    // Return the exact method-owned control and label.
    return html`<label class="check-row"><input id="enrollment-method-${safe(method)}" type="checkbox" ${checked}><span>${safe(humanLabel(method))}</span></label>`;
  }

  // Render one method-specific readiness row.
  function readinessRow(method, row) {
    // Preserve method and boolean readiness evidence first.
    const status = html`<td>${safe(humanLabel(method))}</td><td>${safe(String(row.enabled))}</td><td>${safe(String(row.ready))}</td>`;
    // Preserve the bounded blocker summary last.
    const blockers = safe((row.blockers || []).map(humanLabel).join(', ') || '—');
    // Return one compact readiness row.
    return html`<tr>${status}<td>${blockers}</td></tr>`;
  }

  // Render one immutable policy-audit row.
  function auditRow(row) {
    // Preserve verified time, actor, and reason evidence.
    return html`<tr><td>${safe(row.at)}</td><td>${safe(row.actor_id)}</td><td>${safe(row.reason)}</td></tr>`;
  }

  // Render one independent provider-login kill switch.
  function providerControl(provider, enabled) {
    // Preserve the durable operational state as the checked projection.
    const checked = enabled ? 'checked' : '';
    // Return the provider-owned control and allowlisted label.
    return html`<label class="check-row"><input id="oauth-operational-${safe(provider)}" type="checkbox" ${checked}><span>${safe(humanLabel(provider))}</span></label>`;
  }

  // Build the enrollment policy control card.
  function policyCard(data, policy) {
    // Render only server-published modes and methods.
    const modes = (data.modes || []).map(mode => option(mode, humanLabel(mode), policy.mode));
    const methods = (data.methods || []).map(method => methodControl(method, policy));
    // Preserve mode, method, and invitation controls in accepted order.
    const modeControl = html`<label>${safe(t('enrollment.mode', {}, 'admin'))}<select id="enrollment-mode">${modes}</select></label>`;
    const methodControls = html`<div class="grid3">${methods}</div>`;
    const invitationChecked = policy.invitations_enabled ? 'checked' : '';
    const invitations = html`<label class="check-row"><input id="enrollment-invitations" type="checkbox" ${invitationChecked}><span>${safe(t('enrollment.invitations', {}, 'admin'))}</span></label>`;
    // Preserve bounded reason and explicit preview/apply actions.
    const reason = html`<label>${safe(t('enrollment.reason', {}, 'admin'))}<input id="enrollment-reason" maxlength="256"></label>`;
    const preview = html`<button id="enrollment-preview" type="button">${safe(t('enrollment.preview', {}, 'admin'))}</button>`;
    const apply = html`<button id="enrollment-apply" type="button" class="gold">${safe(t('enrollment.apply', {}, 'admin'))}</button>`;
    const actions = html`<div class="row">${preview}${apply}</div>`;
    const result = html`<div id="enrollment-preview-result" class="result-box" hidden></div>`;
    // Return the exact accepted policy-card order.
    const heading = html`<h3>${safe(t('enrollment.policyTitle', {}, 'admin'))}</h3>`;
    return html`<section class="admin-card" data-testid="admin-enrollment-policy">${heading}${modeControl}${methodControls}${invitations}${reason}${actions}${result}</section>`;
  }

  // Build method-specific readiness without any launch action.
  function readinessCard(readiness) {
    // Select the reviewed authorization or held copy.
    const status = readiness.live_enablement_authorized
      ? t('enrollment.authorized', {}, 'admin')
      : t('enrollment.held', {}, 'admin');
    // Render the exact readiness table columns.
    const rows = Object.entries(readiness.methods || {})
      .map(([method, row]) => readinessRow(method, row));
    const evidence = table([
      t('enrollment.method', {}, 'admin'),
      t('enrollment.enabled', {}, 'admin'),
      t('enrollment.ready', {}, 'admin'),
      t('enrollment.blockers', {}, 'admin'),
    ], rows);
    // Return the named readiness card used as the provider-controls insertion anchor.
    return html`<section class="admin-card" data-testid="admin-enrollment-readiness"><h3>${safe(t('enrollment.readinessTitle', {}, 'admin'))}</h3><p>${safe(status)}</p>${evidence}</section>`;
  }

  // Build immutable enrollment-policy audit evidence.
  function auditCard(data) {
    // Preserve newest-first policy audit order or the calm empty state.
    const evidence = (data.audit || []).length
      ? table([
        t('enrollment.time', {}, 'admin'),
        t('enrollment.actor', {}, 'admin'),
        t('enrollment.reason', {}, 'admin'),
      ], data.audit.slice().reverse().map(auditRow))
      : emptyState(
        t('enrollment.auditEmpty', {}, 'admin'),
        t('enrollment.auditEmptyDetail', {}, 'admin'),
      );
    // Return the named audit card.
    return html`<section class="admin-card" data-testid="admin-enrollment-audit"><h3>${safe(t('enrollment.auditTitle', {}, 'admin'))}</h3>${evidence}</section>`;
  }

  // Build the independent existing-login provider control plane.
  function providerCard(oauthControls) {
    // Render only server-published providers.
    const controls = Object.entries(oauthControls.providers || {})
      .map(([provider, enabled]) => providerControl(provider, enabled));
    // Preserve bounded reason and explicit preview/apply controls.
    const reason = html`<label>${safe(t('enrollment.reason', {}, 'admin'))}<input id="oauth-operational-reason" maxlength="256"></label>`;
    const preview = html`<button id="oauth-operational-preview" type="button">${safe(t('enrollment.preview', {}, 'admin'))}</button>`;
    const apply = html`<button id="oauth-operational-apply" type="button" class="gold">${safe(t('enrollment.providerOperationsApply', {}, 'admin'))}</button>`;
    const result = html`<div id="oauth-operational-preview-result" class="result-box" hidden></div>`;
    // Return the exact separate provider-control card.
    const heading = html`<h3>${safe(t('enrollment.providerOperationsTitle', {}, 'admin'))}</h3>`;
    const help = html`<p>${safe(t('enrollment.providerOperationsHelp', {}, 'admin'))}</p>`;
    const toggles = html`<div class="grid3">${controls}</div>`;
    const actions = html`<div class="row">${preview}${apply}</div>`;
    return html`<section class="admin-card" data-testid="admin-oauth-operational-controls">${heading}${help}${toggles}${reason}${actions}${result}</section>`;
  }

  // Render owner policy, readiness, rollback inputs, and immutable evidence.
  async function enrollment() {
    // Set the enrollment-governance heading and restricted-preview boundary.
    setTitle(t('enrollment.title', {}, 'admin'), t('enrollment.subtitle', {}, 'admin'));
    // Read policy, readiness, and separately governed provider kill switches together.
    const [data, readiness, oauthControls] = await Promise.all([
      api('/api/v2/admin/enrollment-policy'),
      api('/api/v2/admin/enrollment-readiness'),
      api('/api/v2/admin/oauth/operational-controls'),
    ]);
    // Stop a stale request from replacing another selected tab.
    if (!isActiveTab('enrollment')) return;
    // Read the current durable policy once for controls and rollback input.
    const policy = data.policy || {
      mode: 'closed',
      methods: { email: false, google: false, facebook: false },
      invitations_enabled: false,
    };
    // Render policy, readiness, and audit before inserting the independent provider plane.
    view.innerHTML = html`${policyCard(data, policy)}${readinessCard(readiness)}${auditCard(data)}`;
    view.querySelector('[data-testid="admin-enrollment-readiness"]')
      .insertAdjacentHTML('afterend', providerCard(oauthControls));
    // Build the exact complete signup proposal from visible owner controls.
    const changes = () => ({
      mode: view.querySelector('#enrollment-mode').value,
      methods: Object.fromEntries((data.methods || []).map(method => [
        method,
        view.querySelector(`#enrollment-method-${method}`).checked,
      ])),
      invitations_enabled: view.querySelector('#enrollment-invitations').checked,
    });
    // Preview through the same pure computation used by apply.
    view.querySelector('#enrollment-preview').onclick = async () => {
      // Request bounded impact only.
      const result = await post('/api/v2/admin/enrollment-policy/preview', { changes: changes() });
      // Reveal and populate the existing result outlet.
      const outlet = view.querySelector('#enrollment-preview-result');
      outlet.hidden = false;
      outlet.textContent = JSON.stringify(result.impact || {}, null, 2);
    };
    // Apply only after explicit confirmation and a bounded owner reason.
    view.querySelector('#enrollment-apply').onclick = async () => {
      // Preserve the established browser confirmation boundary.
      if (!window.confirm(t('enrollment.confirm', {}, 'admin'))) return;
      // Commit the exact proposal against the current revision.
      await post('/api/v2/admin/enrollment-policy', {
        changes: changes(),
        confirm: true,
        reason: view.querySelector('#enrollment-reason').value.trim(),
        revision: data.revision,
      });
      // Confirm completion and reload durable policy evidence.
      toast(t('enrollment.saved', {}, 'admin'), true);
      await enrollment();
    };
    // Build the provider proposal independently from signup flags.
    const operationalChanges = () => Object.fromEntries(
      Object.keys(oauthControls.providers || {}).map(provider => [
        provider,
        view.querySelector(`#oauth-operational-${provider}`).checked,
      ]),
    );
    // Preview exact existing-login lockout impact.
    view.querySelector('#oauth-operational-preview').onclick = async () => {
      // Request bounded impact from the owner-only route.
      const result = await post('/api/v2/admin/oauth/operational-controls/preview', {
        changes: operationalChanges(),
      });
      // Reveal and populate the independent result outlet.
      const outlet = view.querySelector('#oauth-operational-preview-result');
      outlet.hidden = false;
      outlet.textContent = JSON.stringify(result.impact || {}, null, 2);
    };
    // Apply only after confirmation; the server still gates every enablement.
    view.querySelector('#oauth-operational-apply').onclick = async () => {
      // Preserve the independent provider confirmation boundary.
      if (!window.confirm(t('enrollment.providerOperationsConfirm', {}, 'admin'))) return;
      // Commit only provider operational switches against their own revision.
      await post('/api/v2/admin/oauth/operational-controls', {
        changes: operationalChanges(),
        confirm: true,
        reason: view.querySelector('#oauth-operational-reason').value.trim(),
        revision: oauthControls.revision,
      });
      // Confirm completion and reload durable control evidence.
      toast(t('enrollment.providerOperationsSaved', {}, 'admin'), true);
      await enrollment();
    };
  }

  // Publish only the dispatcher-facing Enrollment renderer.
  return enrollment;
}
