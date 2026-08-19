// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build owner-only ordinary-Admin delegation behind a dedicated tab boundary. (ADMIN-033)
export function createAdministratorsTab(dependencies) {
  // Capture the established role-management and presentation helpers.
  const {
    api, emptyState, html, humanLabel, isActiveTab, option, post, safe, setTitle, t, table, toast, view,
  } = dependencies;

  // Render one current Admin row while preserving protected-owner behavior.
  function administratorRow(account) {
    // Preserve visible identity and role columns.
    const identity = html`<td>${safe(account.display_name)} (${safe(account.email)})</td>`;
    const roles = html`<td>${safe((account.roles || []).join(', '))}</td>`;
    // Render static protected-owner copy or the reviewed revoke control.
    const action = account.protected_owner
      ? safe(t('administrators.protected', {}, 'admin'))
      : html`<button type="button" class="administrator-revoke" data-user="${safe(account.user_id)}">${safe(t('administrators.revoke', {}, 'admin'))}</button>`;
    // Return one compact role row.
    return html`<tr>${identity}${roles}<td>${action}</td></tr>`;
  }

  // Render one immutable role-audit row.
  function auditRow(row) {
    // Keep time and action evidence first.
    const event = html`<td>${safe(row.at)}</td><td>${safe(humanLabel(row.action))}</td>`;
    // Keep target and bounded reason evidence last.
    const target = html`<td>${safe(row.target_user_id)}</td><td>${safe(row.reason)}</td>`;
    // Return one compact audit row.
    return html`<tr>${event}${target}</tr>`;
  }

  // Render owner-only ordinary-Admin delegation separately from account lifecycle.
  async function administrators() {
    // Set the explicit privilege-management heading.
    setTitle(t('administrators.title', {}, 'admin'), t('administrators.subtitle', {}, 'admin'));
    // Read the current role revision and immutable audit together.
    const [data, historyData] = await Promise.all([
      api('/api/v2/admin/administrators'),
      api('/api/v2/admin/administrators/audit?limit=100'),
    ]);
    // Stop a stale response from replacing another selected tab.
    if (!isActiveTab('administrators')) return;
    // Build eligible-account options in server order.
    const eligible = data.eligible_accounts || [];
    const eligibleOptions = eligible.map(account => option(
      account.user_id,
      `${account.display_name} (${account.email})`,
      '',
    ));
    // Preserve each transient grant input as a separate reviewable fragment.
    const accountInput = html`<label>${safe(t('administrators.account', {}, 'admin'))}<select id="administrator-target">${eligibleOptions}</select></label>`;
    const passwordInput = html`<label>${safe(t('administrators.password', {}, 'admin'))}<input id="administrator-password" type="password" autocomplete="current-password"></label>`;
    const reasonInput = html`<label>${safe(t('administrators.reason', {}, 'admin'))}<input id="administrator-reason" maxlength="256"></label>`;
    // Disable grants when no ordinary account is eligible.
    const disabled = eligible.length ? '' : 'disabled';
    const grantAction = html`<button id="administrator-grant" type="button" data-testid="administrator-grant" ${disabled}>${safe(t('administrators.grant', {}, 'admin'))}</button>`;
    // Compose the grant card in the accepted input order.
    const grantHeading = html`<h3>${safe(t('administrators.grantTitle', {}, 'admin'))}</h3>`;
    const grantCard = html`<section class="admin-card" data-testid="admin-administrator-grant">${grantHeading}${accountInput}${passwordInput}${reasonInput}${grantAction}</section>`;
    // Build the current role list or its calm empty state.
    const current = (data.administrators || []).length
      ? table([
        t('administrators.account', {}, 'admin'),
        t('administrators.role', {}, 'admin'),
        t('administrators.action', {}, 'admin'),
      ], data.administrators.map(administratorRow))
      : emptyState(t('administrators.empty', {}, 'admin'), t('administrators.emptyDetail', {}, 'admin'));
    const currentCard = html`<section class="admin-card" data-testid="admin-administrator-list"><h3>${safe(t('administrators.currentTitle', {}, 'admin'))}</h3>${current}</section>`;
    // Build the immutable audit list or its calm empty state.
    const audit = (historyData.audit || []).length
      ? table([
        t('administrators.time', {}, 'admin'),
        t('administrators.action', {}, 'admin'),
        t('administrators.target', {}, 'admin'),
        t('administrators.reason', {}, 'admin'),
      ], historyData.audit.map(auditRow))
      : emptyState(
        t('administrators.auditEmpty', {}, 'admin'),
        t('administrators.auditEmptyDetail', {}, 'admin'),
      );
    const auditCard = html`<section class="admin-card" data-testid="admin-administrator-audit"><h3>${safe(t('administrators.auditTitle', {}, 'admin'))}</h3>${audit}</section>`;
    // Replace the tab atomically in grant, current-role, audit order.
    view.innerHTML = html`${grantCard}${currentCard}${auditCard}`;
    // Apply one reauthenticated role transition and scrub the password immediately.
    const changeRole = async (target, action) => {
      // Read the transient owner step-up and bounded reason at action time only.
      const password = view.querySelector('#administrator-password').value;
      const reason = view.querySelector('#administrator-reason').value.trim();
      // Clear the password before awaiting network work.
      view.querySelector('#administrator-password').value = '';
      // Commit through the owner-only endpoint with optimistic revision and replay key.
      await post(`/api/v2/admin/administrators/${encodeURIComponent(target)}/${action}`, {
        password,
        reason,
        revision: data.revision,
        idempotency_key: crypto.randomUUID(),
      });
      // Confirm the transition without reflecting sensitive request content.
      toast(t('administrators.saved', {}, 'admin'), true);
      // Reload durable role and audit state.
      await administrators();
    };
    // Bind the selected eligible account grant.
    view.querySelector('#administrator-grant').onclick = () => changeRole(
      view.querySelector('#administrator-target').value,
      'grant',
    );
    // Bind every non-owner revoke to the same reauthentication fields.
    view.querySelectorAll('.administrator-revoke').forEach((button) => {
      // Preserve the row-owned target id and exact action.
      button.onclick = () => changeRole(button.dataset.user, 'revoke');
    });
  }

  // Publish only the dispatcher-facing Administrators renderer.
  return administrators;
}
