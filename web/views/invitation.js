// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build private invitation redemption behind an account-free route boundary. (INVITE-003, INVITE-005)

// Create the invitation renderer and its caller-idempotent redemption handler.
export function createInvitationView(dependencies) {
  // Capture the accepted browser, API, locale, and presentation seams.
  const {
    cryptoRef, documentRef, getLocaleState, historyRef, html, redeemInvitation,
    renderLoginGate, safe, sessionStorageRef, setSession, syncFeedbackReporter,
    t, transientRouteBearer, wireLocaleSelect, windowRef,
  } = dependencies;
  // Hold the transient bearer only in module memory after route scrubbing.
  let invitationBearerToken = '';

  // Derive a token-free lookup and stable caller key for safe retries.
  async function invitationIdempotency(token) {
    // Hash the transient bearer without persisting it.
    const encoded = new TextEncoder().encode(token);
    const digest = await cryptoRef.subtle.digest('SHA-256', encoded);
    // Encode only a short non-secret digest prefix.
    const prefix = Array.from(new Uint8Array(digest).slice(0, 12))
      .map(value => value.toString(16).padStart(2, '0'))
      .join('');
    const key = `casino.invitation.idempotency.${prefix}`;
    // Reuse the same browser caller key after a lost response.
    const existing = sessionStorageRef.getItem(key);
    if (existing) return existing;
    // Generate and retain only a random caller-owned replay identity.
    const created = cryptoRef.randomUUID();
    sessionStorageRef.setItem(key, created);
    return created;
  }

  // Render explicit invitation fields and generic result copy.
  function invitationMarkup(message, success) {
    // Preserve restricted-preview identity and explanation.
    const heading = html`<p class="eyebrow">${t('invitation.eyebrow', {}, 'shell')}</p><h1>${t('invitation.title', {}, 'shell')}</h1>`;
    const copy = html`<p class="auth-copy">${t('invitation.copy', {}, 'shell')}</p>`;
    // Preserve mailbox, display name, password, and locale inputs.
    const email = html`<label>${t('invitation.email', {}, 'shell')}<input id="invitation-email" data-testid="invitation-email" type="email" autocomplete="email" maxlength="254" required></label>`;
    const nameInput = html`<input id="invitation-display-name" data-testid="invitation-display-name" autocomplete="name" maxlength="80" required>`;
    const name = html`<label>${t('invitation.displayName', {}, 'shell')}${nameInput}</label>`;
    const passwordInput = html`<input id="invitation-password" data-testid="invitation-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required>`;
    const password = html`<label>${t('invitation.password', {}, 'shell')}${passwordInput}</label>`;
    const locale = html`<label>${t('invitation.language', {}, 'shell')}<select id="invitation-locale" data-testid="invitation-locale"></select></label>`;
    // Preserve explicit current-terms acceptance and the primary mutation.
    const terms = html`<label class="check-row"><input id="invitation-terms" data-testid="invitation-terms" type="checkbox" required><span>${t('invitation.terms', {}, 'shell')}</span></label>`;
    const submit = html`<button class="primary" data-testid="invitation-submit" type="submit">${t('invitation.submit', {}, 'shell')}</button>`;
    const status = html`<p id="invitation-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${message}</p>`;
    const form = html`<form id="invitation-form" class="auth-form">${email}${name}${password}${locale}${terms}${submit}${status}</form>`;
    const back = html`<a href="/" data-testid="invitation-login-link">${t('invitation.back', {}, 'shell')}</a>`;
    return html`<section class="auth-panel" data-testid="invitation-redemption">${heading}${copy}${form}${back}</section>`;
  }

  // Submit one explicit invitation redemption without enumerating failures.
  async function handleInvitationSubmit(event) {
    // Prevent full navigation and duplicate in-flight submission.
    event.preventDefault();
    const message = documentRef.getElementById('invitation-message');
    const token = invitationBearerToken || transientRouteBearer('/enroll/invitation');
    const submit = documentRef.querySelector('[data-testid="invitation-submit"]');
    submit.disabled = true;
    try {
      // Build the exact current-terms request with a stable caller key.
      const payload = {
        token,
        email: documentRef.getElementById('invitation-email').value.trim(),
        password: documentRef.getElementById('invitation-password').value,
        display_name: documentRef.getElementById('invitation-display-name').value.trim(),
        locale: getLocaleState().locale,
        terms_version: 'private-beta-1',
        accepted: documentRef.getElementById('invitation-terms').checked === true,
        idempotency_key: await invitationIdempotency(token),
      };
      // Submit only after every explicit enrollment field is collected.
      await redeemInvitation(payload);
      historyRef.replaceState({}, '', '/');
      // Drop module-local bearer material after terminal success.
      invitationBearerToken = '';
      renderLoginGate(t('invitation.success', {}, 'shell'));
    } catch (_) {
      // Collapse every unavailable result into one localized message.
      if (message) message.textContent = t('invitation.unavailable', {}, 'shell');
      submit.disabled = false;
    }
  }

  // Render the account-free invitation form without creating state on load.
  function renderInvitationGate(message = '', success = false) {
    // Capture a newly arrived bearer before scrubbing browser history.
    const arrivalToken = transientRouteBearer('/enroll/invitation');
    if (arrivalToken) {
      // Keep bearer material only in this module for the pending redemption.
      invitationBearerToken = arrivalToken;
      historyRef.replaceState({}, '', '/enroll/invitation');
    }
    // Clear authenticated identity and reporting while the public route owns the page.
    setSession(null);
    windowRef.CasinoCurrentUser = null;
    syncFeedbackReporter(null);
    // Keep casino chrome locked behind later successful login.
    documentRef.body.classList.remove('lobby-active', 'guest-trial-active');
    documentRef.body.classList.add('auth-locked');
    const view = documentRef.getElementById('view');
    // Remove authenticated region semantics from the public outlet.
    for (const attribute of ['tabindex', 'role', 'aria-label', 'data-testid']) {
      // Remove one static shell-owned attribute.
      view.removeAttribute(attribute);
    }
    view.className = 'screen auth-screen';
    view.innerHTML = html`${invitationMarkup(message, success)}`;
    // Populate locale choices and preserve current status across locale changes.
    wireLocaleSelect(
      documentRef.getElementById('invitation-locale'),
      () => renderInvitationGate(message, success),
    );
    // Bind one recovery-safe submit handler.
    documentRef.getElementById('invitation-form').onsubmit = handleInvitationSubmit;
  }

  // Publish only the shell-facing invitation renderer.
  return renderInvitationGate;
}
