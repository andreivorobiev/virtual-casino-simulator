// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Admin Users tab behind explicit account-lifecycle dependencies. (ADMIN-034)
export function createUsersTab(dependencies) {
  // Capture the established shell helpers once so the renderer owns no ambient state.
  const {
    activate, api, emptyState, formatLocaleOptions, formatMoney, html, humanLabel, isActiveTab,
    localeOptions, option, post, raw, safe, setTitle, t, table, toast, view,
  } = dependencies;
  // Retain only the latest one-time credential for the current Admin document lifetime.
  let lastUserPassword = '';
  // Reject stale same-tab account responses after a newer refresh begins.
  let usersRenderRevision = 0;

  // Return whether one API record belongs in ordinary account management.
  function isManagedAccountUser(user) {
    // Normalize role values before checking for a disposable guest principal.
    const roles = (user?.roles || [user?.role]).map(role => String(role || '').toLowerCase());
    // Normalize both server-owned identity classifiers before the fail-closed check.
    const principalType = String(user?.principal_type || '').toLowerCase();
    const identityProvider = String(user?.identity_provider || '').toLowerCase();
    // Leave every known guest-trial marker to the dedicated Guest Trials tab.
    return principalType !== 'guest'
      && identityProvider !== 'guest'
      && user?.guest !== true
      && !roles.includes('guest');
  }

  // Render one account-management row without role mutation controls.
  function userRow(user) {
    // Keep account identity cells first in the accepted table order.
    const identity = html`<td>${safe(user.email)}</td><td>${safe(user.display_name)}</td>`;
    // Preserve lifecycle choices and the stable save hook.
    const statusOptions = ['active', 'inactive', 'suspended', 'locked']
      .map(status => option(status, humanLabel(status), user.status));
    // Compose the status selector and save action independently.
    const status = html`<select class="user-status" data-testid="admin-user-status">${statusOptions}</select>`;
    const saveAccount = html`<button class="save-user-account" data-user="${safe(user.user_id)}" data-testid="admin-user-save-account">${safe(t('users.saveAccount', {}, 'admin'))}</button>`;
    // Preserve the accepted access-control wrappers.
    const access = html`<td class="admin-user-access-cell"><div class="admin-user-access-controls" data-testid="admin-user-access-controls">${status}${saveAccount}</div></td>`;
    // Keep token and terms evidence in the accepted column order.
    const account = html`<td data-testid="admin-user-token-balance">${formatMoney(user.token_balance)}</td><td>${safe(user.token_state)}</td><td>${safe(user.terms_status)}</td>`;
    // Preserve per-account language and format selectors.
    const language = html`<td><select class="user-language">${localeOptions(user.language || 'en-US')}</select></td>`;
    const format = html`<td><select class="user-format">${formatLocaleOptions(user.format_locale || 'browser')}</select></td>`;
    const locale = html`${language}${format}`;
    // Derive the established lifecycle action from durable account status.
    const toggleAction = user.status === 'active' ? 'deactivate' : 'reactivate';
    const toggleLabel = user.status === 'active' ? 'Deactivate' : 'Reactivate';
    // Derive the established terms action without exposing a separate role control.
    const termsAccepted = user.terms_status !== 'accepted';
    const termsLabel = user.terms_status === 'accepted' ? 'Clear terms' : 'Accept terms';
    // Keep all accepted account action hooks inside the final table cell.
    const saveLocale = html`<button class="save-user-locale" data-user="${safe(user.user_id)}" data-testid="admin-user-save-locale">Save locale</button>`;
    const toggle = html`<button class="toggle-user" data-user="${safe(user.user_id)}" data-action="${toggleAction}" data-testid="admin-user-toggle">${toggleLabel}</button>`;
    const reset = html`<button class="reset-user-password" data-user="${safe(user.user_id)}" data-testid="admin-user-reset">Reset password</button>`;
    const terms = html`<button class="terms-user" data-user="${safe(user.user_id)}" data-accepted="${termsAccepted}" data-testid="admin-user-terms">${termsLabel}</button>`;
    const actions = html`<td>${saveLocale}${toggle}${reset}${terms}</td>`;
    // Return one compact account-only row with stable classification attributes.
    const rowIdentity = html` data-user="${safe(user.user_id)}" data-email="${safe(user.email)}"`;
    const rowState = html` data-status="${safe(user.status)}" data-terms="${safe(user.terms_status)}"`;
    const rowOpen = html`<tr data-testid="admin-user-row"${rowIdentity}${rowState}>`;
    return html`${rowOpen}${identity}${access}${account}${locale}${actions}</tr>`;
  }

  // Return all managed account rows in server order.
  function userRows(users) {
    // Delegate each record to the reviewable row renderer.
    return users.map(userRow);
  }

  // Build the ordinary account creation card and latest credential notice.
  function creationCard(passwordNotice) {
    // Preserve the first row of identity and token controls.
    const email = html`<label>Email<input id="admin_user_email" data-testid="admin-user-email" type="email" placeholder="beta@example.test"></label>`;
    const displayName = html`<label>Display name<input id="admin_user_name" data-testid="admin-user-name" placeholder="Beta Player"></label>`;
    const tokens = html`<label>Initial tokens<input id="admin_user_tokens" data-testid="admin-user-tokens" type="number" min="0" step="1" value="5000"></label>`;
    const identity = html`<div class="grid3">${email}${displayName}${tokens}</div>`;
    // Preserve the transient password, fixed player role, and language controls.
    const password = html`<label>Temporary password<input id="admin_user_password" data-testid="admin-user-password" type="text" placeholder="Generate if blank"></label>`;
    const role = html`<label>${safe(t('users.initialRole', {}, 'admin'))}<input id="admin_user_role" data-testid="admin-user-role" value="player" readonly></label>`;
    const language = html`<label>Language<select id="admin_user_language" data-testid="admin-user-language">${localeOptions('en-US')}</select></label>`;
    const access = html`<div class="grid3">${password}${role}${language}</div>`;
    // Preserve the format-locale and initial terms controls.
    const format = html`<label>Format locale<select id="admin_user_format" data-testid="admin-user-format">${formatLocaleOptions('browser')}</select></label>`;
    const terms = html`<label><input id="admin_user_terms" data-testid="admin-user-terms-initial" type="checkbox"> Terms accepted</label>`;
    const preferences = html`<div class="grid3">${format}</div>${terms}`;
    // Preserve the stable create action and optional one-time credential notice.
    const action = html`<button id="admin_create_user" data-testid="admin-create-user" class="gold">${safe(t('users.createButton', {}, 'admin'))}</button>${passwordNotice}`;
    // Return the exact accepted creation-card ordering.
    return html`<section class="admin-card" data-testid="admin-user-create"><h3>${safe(t('users.createTitle', {}, 'admin'))}</h3>${identity}${access}${preferences}${action}</section>`;
  }

  // Submit one new beta account through the existing Admin route.
  async function createUser() {
    // Collect the rendered account fields only at explicit submit time.
    const payload = {
      email: view.querySelector('#admin_user_email').value,
      display_name: view.querySelector('#admin_user_name').value,
      initial_tokens: Number(view.querySelector('#admin_user_tokens').value || 0),
      password: view.querySelector('#admin_user_password').value,
      role: view.querySelector('#admin_user_role').value,
      language: view.querySelector('#admin_user_language').value,
      format_locale: view.querySelector('#admin_user_format').value,
      terms_accepted: view.querySelector('#admin_user_terms').checked,
    };
    // Create the account through the frozen Admin route.
    const result = await post('/api/v1/admin/users', payload);
    // Retain the one-time password only for the immediate Admin handoff.
    lastUserPassword = result.temporary_password || '';
    // Preserve the established success feedback and refresh.
    toast('User created.', true);
    await users();
  }

  // Persist lifecycle status while role transitions remain owner-only.
  async function saveUserAccount(button) {
    // Resolve the account row and selected durable lifecycle status.
    const row = button.closest('tr[data-user]');
    const payload = { status: row.querySelector('.user-status').value };
    // Persist through the additive v2 account contract.
    await api(`/api/v2/admin/users/${encodeURIComponent(button.dataset.user)}`, {
      method: 'PATCH',
      body: payload,
    });
    // Preserve localized completion feedback and refresh.
    toast(t('users.accountSaved', {}, 'admin'), true);
    await users();
  }

  // Deactivate or reactivate one beta account through the frozen route.
  async function toggleUser(button) {
    // Submit only the action encoded by the reviewed lifecycle control.
    await post(`/api/v1/admin/users/${button.dataset.user}/${button.dataset.action}`, {});
    // Preserve the established completion feedback and refresh.
    toast('User status updated.', true);
    await users();
  }

  // Generate and display one new temporary password.
  async function resetUserPassword(button) {
    // Request a new one-time credential for the selected account.
    const result = await post(`/api/v1/admin/users/${button.dataset.user}/password-reset`, {});
    // Retain only the newest one-time password for handoff.
    lastUserPassword = result.temporary_password || '';
    // Preserve the established completion feedback and refresh.
    toast('Temporary password generated.', true);
    await users();
  }

  // Set one account's terms acceptance state.
  async function updateUserTerms(button) {
    // Submit the boolean encoded by the reviewed terms control.
    await post(`/api/v1/admin/users/${button.dataset.user}/terms`, {
      accepted: button.dataset.accepted === 'true',
    });
    // Preserve the established completion feedback and refresh.
    toast('Terms status updated.', true);
    await users();
  }

  // Persist per-account locale preferences.
  async function saveUserLocale(button) {
    // Resolve the account row that owns both locale controls.
    const row = button.closest('tr[data-user]');
    // Preserve the exact locale payload and explicit browser-locale override.
    const payload = {
      language: row.querySelector('.user-language').value,
      format_locale: row.querySelector('.user-format').value,
      use_browser_locale: false,
    };
    // Submit through the frozen account-locale route.
    await post(`/api/v1/admin/users/${button.dataset.user}/locale`, payload);
    // Preserve the established completion feedback and refresh.
    toast('User locale saved.', true);
    await users();
  }

  // Render the Admin beta-user management workspace.
  async function users() {
    // Claim the latest same-tab revision before starting the account read.
    const renderRevision = ++usersRenderRevision;
    // Remove stale interactive controls before the replacement request settles.
    view.replaceChildren();
    // Set the localized Users heading.
    setTitle(t('users.title', {}, 'admin'), t('users.subtitle', {}, 'admin'));
    // Load the account-management envelope.
    const data = await api('/api/v1/admin/users');
    // Reject inactive-tab or superseded same-tab responses.
    if (!isActiveTab('users') || renderRevision !== usersRenderRevision) return;
    // Exclude temporary guest principals from ordinary account management.
    const managedUsers = (data.users || []).filter(isManagedAccountUser);
    // Expose only the latest document-lifetime one-time password when present.
    const passwordNotice = lastUserPassword
      ? html`<div class="result-box" data-testid="admin-user-temp-password">Latest temporary password: ${safe(lastUserPassword)}</div>`
      : '';
    // Preserve the explicit handoff to the separate Guest Trials workspace.
    const guestHeading = html`<h3>${safe(t('users.guestSeparationTitle', {}, 'admin'))}</h3>`;
    const guestCopy = html`<p>${safe(t('users.guestSeparationCopy', {}, 'admin'))}</p>`;
    const guestAction = html`<button id="admin_open_guest_trials" type="button" data-testid="admin-open-guest-trials">${safe(t('users.openGuestTrials', {}, 'admin'))}</button>`;
    const guestSeparationCard = html`<section class="admin-card" data-testid="admin-users-guest-separation">${guestHeading}${guestCopy}${guestAction}</section>`;
    // Preserve the account-only table or calm empty state.
    const managedUserTable = managedUsers.length
      ? html`<div class="admin-users-table-scroll" data-testid="admin-users-managed-table" tabindex="0" role="region" aria-label="${safe(t('users.tableTitle', {}, 'admin'))}">${table([
        t('users.email', {}, 'admin'), t('users.name', {}, 'admin'),
        t('users.accessControls', {}, 'admin'), t('users.tokenBalance', {}, 'admin'),
        t('users.tokenState', {}, 'admin'), t('users.terms', {}, 'admin'),
        t('users.language', {}, 'admin'), t('users.format', {}, 'admin'),
        t('users.actions', {}, 'admin'),
      ], userRows(managedUsers))}</div>`
      : emptyState(t('users.emptyTitle', {}, 'admin'), t('users.emptyDetail', {}, 'admin'), 'admin-users-empty');
    // Build the managed-account card separately for reviewable composition.
    const managedAccounts = html`<section class="admin-card" data-testid="admin-users-managed-accounts"><h3>${safe(t('users.tableTitle', {}, 'admin'))}</h3>${managedUserTable}</section>`;
    // Replace the tab atomically in the established handoff, creation, account order.
    view.innerHTML = html`${raw(guestSeparationCard)}${creationCard(passwordNotice)}${managedAccounts}`;
    // Bind the Guest Trials handoff and account-creation action.
    view.querySelector('#admin_open_guest_trials').onclick = () => activate('guests');
    view.querySelector('#admin_create_user').onclick = createUser;
    // Bind every accepted account mutation to its owning row.
    view.querySelectorAll('.toggle-user').forEach(button => { button.onclick = () => toggleUser(button); });
    view.querySelectorAll('.save-user-account').forEach(button => { button.onclick = () => saveUserAccount(button); });
    view.querySelectorAll('.reset-user-password').forEach(button => { button.onclick = () => resetUserPassword(button); });
    view.querySelectorAll('.terms-user').forEach(button => { button.onclick = () => updateUserTerms(button); });
    view.querySelectorAll('.save-user-locale').forEach(button => { button.onclick = () => saveUserLocale(button); });
  }

  // Publish only the dispatcher-facing Users renderer.
  return users;
}
