// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build full-account enrollment and released provider actions behind one public view. (AUTH-018, OAUTH-013)

// Create the Signup renderer and policy-gated submission handlers.
export function createSignupView(dependencies) {
  // Capture the accepted browser, API, locale, and presentation seams.
  const {
    api, beginOAuth, cryptoRef, documentRef, getLocaleState, historyRef, html,
    oauthCompletionCopy, oauthProviders, renderEmailVerificationGate, safe,
    setPendingEnrollmentEmail, setSession, syncFeedbackReporter, t,
    wireLocaleSelect, windowRef,
  } = dependencies;

  // Render the local-email enrollment form.
  function localSignupForm(enabled, message, success) {
    // Preserve bounded account and locale fields.
    const email = html`<label>${t('auth.email', {}, 'shell')}<input id="signup-email" data-testid="signup-email" type="email" autocomplete="email" maxlength="254" required></label>`;
    const name = html`<label>${t('invitation.displayName', {}, 'shell')}<input id="signup-display-name" data-testid="signup-display-name" autocomplete="name" maxlength="80" required></label>`;
    const passwordInput = html`<input id="signup-password" data-testid="signup-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required>`;
    const password = html`<label>${t('auth.password', {}, 'shell')}${passwordInput}</label>`;
    const locale = html`<label>${t('auth.language', {}, 'shell')}<select id="signup-locale" data-testid="signup-locale"></select></label>`;
    // Preserve three explicit acknowledgements before enrollment.
    const terms = html`<label class="check-row"><input id="signup-terms" data-testid="signup-terms" type="checkbox" required><span>${t('auth.termsCheck', {}, 'shell')}</span></label>`;
    const privacy = html`<label class="check-row"><input id="signup-privacy" data-testid="signup-privacy" type="checkbox"><span>${t('signup.privacyCheck', {}, 'shell')}</span></label>`;
    const tokens = html`<label class="check-row"><input id="signup-play-token" data-testid="signup-play-token" type="checkbox"><span>${t('signup.fakeMoneyCheck', {}, 'shell')}</span></label>`;
    const disabled = enabled ? '' : 'disabled';
    const submit = html`<button class="primary" data-testid="signup-submit" type="submit" ${disabled}>${t('signup.submit', {}, 'shell')}</button>`;
    const status = html`<p id="signup-message" data-testid="signup-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${message}</p>`;
    return html`<form id="signup-form" class="auth-form">${email}${name}${password}${locale}${terms}${privacy}${tokens}${submit}${status}</form>`;
  }

  // Render fail-closed social signup controls before readiness resolves.
  function providerSignupRegion() {
    // Preserve disabled native actions until exact provider readiness is returned.
    const google = html`<button class="oauth-provider-button" data-testid="signup-oauth-google" type="button" disabled aria-disabled="true">${t('auth.oauthGoogle', {}, 'shell')}</button>`;
    const facebook = html`<button class="oauth-provider-button" data-testid="signup-oauth-facebook" type="button" disabled aria-disabled="true">${t('auth.oauthFacebook', {}, 'shell')}</button>`;
    const grid = html`<div class="oauth-provider-grid">${google}${facebook}</div>`;
    const message = html`<p class="oauth-provider-copy" data-testid="oauth-signup-message" role="status">${t('signup.oauthUnavailable', {}, 'shell')}</p>`;
    const heading = html`<h2 id="oauth-signup-heading">${t('signup.oauthDivider', {}, 'shell')}</h2>`;
    return html`<section class="oauth-provider-status" data-testid="oauth-signup-disabled" aria-labelledby="oauth-signup-heading">${heading}${grid}${message}</section>`;
  }

  // Submit one policy-gated local enrollment request.
  async function submitSignup(event) {
    // Keep native navigation from replacing the public route.
    event.preventDefault();
    const status = documentRef.getElementById('signup-message');
    try {
      // Require all browser-owned acknowledgements before credential creation.
      const accepted = [
        documentRef.getElementById('signup-terms').checked,
        documentRef.getElementById('signup-privacy').checked,
        documentRef.getElementById('signup-play-token').checked,
      ].every(Boolean);
      if (!accepted) throw new Error('signup consent required');
      // Hold the transient mailbox only for immediate Verification prefill.
      const pendingEmail = documentRef.getElementById('signup-email').value.trim();
      setPendingEnrollmentEmail(pendingEmail);
      // Submit the account-free pending request with one caller-owned key.
      await api('/api/v2/auth/signup', {
        method: 'POST',
        body: {
          email: pendingEmail,
          password: documentRef.getElementById('signup-password').value,
          display_name: documentRef.getElementById('signup-display-name').value,
          locale: documentRef.getElementById('signup-locale').value,
          terms_version: 'private-beta-1',
          accepted: true,
          idempotency_key: cryptoRef.randomUUID(),
        },
      });
      // Move to account-free Verification without assuming a session.
      historyRef.replaceState({}, '', '/enroll/verify');
      renderEmailVerificationGate(t('signup.pending', {}, 'shell'), true);
    } catch (_) {
      // Publish one generic failure without backend detail.
      status.textContent = t('signup.failed', {}, 'shell');
    }
  }

  // Enable only policy-approved and operationally released providers.
  async function enableAvailableOAuthSignup() {
    // Resolve the currently mounted provider region.
    const region = documentRef.querySelector('[data-testid^="oauth-signup-"]');
    if (!region) return;
    try {
      // Read only provider identifiers and availability booleans.
      const result = await oauthProviders();
      const available = new Set(
        (result.providers || [])
          .filter(item => item.signup_available === true)
          .map(item => item.provider),
      );
      // Configure each reviewed provider independently.
      for (const provider of ['google', 'facebook']) {
        // Resolve the stable provider-specific action.
        const button = documentRef.querySelector(`[data-testid="signup-oauth-${provider}"]`);
        if (!button) continue;
        button.disabled = !available.has(provider);
        button.setAttribute('aria-disabled', String(button.disabled));
        // Start only explicit signup intent after browser acknowledgements.
        button.onclick = button.disabled ? null : () => beginOAuth(provider, 'signup');
      }
      // Stamp and explain the governed matrix state.
      region.dataset.testid = available.size ? 'oauth-signup-available' : 'oauth-signup-disabled';
      const status = region.querySelector('[data-testid="oauth-signup-message"]');
      status.textContent = available.size
        ? t('signup.oauthAvailable', {}, 'shell')
        : t('signup.oauthUnavailable', {}, 'shell');
    } catch (_) {
      // Preserve fail-closed controls after any readiness failure.
      region.dataset.testid = 'oauth-signup-status-error';
      const status = region.querySelector('[data-testid="oauth-signup-message"]');
      status.textContent = t('signup.oauthStatusError', {}, 'shell');
    }
  }

  // Render full-account enrollment under the public policy gate.
  async function renderSignupGate(message = '', success = false) {
    // Resolve fixed provider completion copy unless caller feedback overrides it.
    const signupMessage = message || oauthCompletionCopy();
    // Clear authenticated identity while the public route is displayed.
    windowRef.CasinoCurrentUser = null;
    setSession(null);
    syncFeedbackReporter(null);
    documentRef.body.classList.remove('lobby-active', 'guest-trial-active');
    documentRef.body.classList.add('auth-locked');
    const view = documentRef.getElementById('view');
    // Remove authenticated semantics before policy loading.
    for (const attribute of ['tabindex', 'role', 'aria-label', 'data-testid']) {
      // Remove one static shell-owned attribute.
      view.removeAttribute(attribute);
    }
    // Render a stable loading shell while policy resolves.
    const loadingHeading = html`<p class="eyebrow">${t('signup.eyebrow', {}, 'shell')}</p><h1>${t('signup.title', {}, 'shell')}</h1>`;
    const loadingCopy = html`<p class="auth-copy">${t('status.loading', {}, 'shell')}</p>`;
    view.innerHTML = html`<section class="auth-panel" data-testid="signup-enrollment">${loadingHeading}${loadingCopy}</section>`;
    const policy = await api('/api/v2/auth/enrollment-policy');
    const enabled = policy.signup_enabled === true;
    const socialRequested = policy.enrollment_mode === 'self-signup'
      && ['google', 'facebook'].some(provider => policy.signup_methods?.[provider] === true);
    // Render local and provider controls with explicit policy state.
    const enabledState = enabled || socialRequested ? 'true' : 'false';
    const heading = html`<p class="eyebrow">${t('signup.eyebrow', {}, 'shell')}</p><h1>${t('signup.title', {}, 'shell')}</h1>`;
    const copyKey = enabled || socialRequested ? 'signup.copy' : 'signup.disabledCopy';
    const copy = html`<p class="auth-copy">${t(copyKey, {}, 'shell')}</p>`;
    const back = html`<a href="/" data-testid="signup-login-link">${t('invitation.back', {}, 'shell')}</a>`;
    const local = localSignupForm(enabled, signupMessage, success);
    const providers = providerSignupRegion();
    view.innerHTML = html`<section class="auth-panel" data-testid="signup-enrollment" data-signup-enabled="${enabledState}">${heading}${copy}${local}${providers}${back}</section>`;
    // Bind locale rerender and policy-gated local submit.
    wireLocaleSelect(
      documentRef.getElementById('signup-locale'),
      () => { void renderSignupGate(signupMessage, success); },
    );
    documentRef.getElementById('signup-form').onsubmit = submitSignup;
    // Resolve provider readiness only after the local form is usable.
    void enableAvailableOAuthSignup();
  }

  // Publish only the shell-facing Signup renderer.
  return renderSignupGate;
}
