// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build pending-email verification, resend, and cancellation behind one public route. (AUTH-018, USER-010)

// Create the email-verification renderer and transient state boundary.
export function createVerificationView(dependencies) {
  // Capture the accepted browser, API, locale, and presentation seams.
  const {
    api, cryptoRef, documentRef, getLocaleState, historyRef, html, renderLoginGate,
    safe, sessionStorageRef, setSession, syncFeedbackReporter, t,
    transientRouteBearer, wireLocaleSelect, windowRef,
  } = dependencies;
  // Retain a just-submitted mailbox only for immediate pending-screen prefill.
  let pendingEnrollmentEmail = '';
  // Retain an arrived verification bearer only after scrubbing browser history.
  let emailVerificationBearer = '';

  // Store a mailbox for the immediate transition from Signup to Verification.
  function setPendingEnrollmentEmail(email) {
    // Keep the value only in module memory and normalize surrounding whitespace.
    pendingEnrollmentEmail = String(email || '').trim();
  }

  // Derive one action-specific token-free lookup key.
  async function emailVerificationStorageKey(token, action = 'verify') {
    // Hash the transient bearer without persisting it.
    const digest = await cryptoRef.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(token),
    );
    const domain = action === 'cancel' ? 'cancel' : 'verify';
    // Encode only a non-secret digest prefix.
    const prefix = Array.from(new Uint8Array(digest).slice(0, 12))
      .map(value => value.toString(16).padStart(2, '0'))
      .join('');
    return `casino.email-verification.${domain}.idempotency.${prefix}`;
  }

  // Derive one reload-safe caller key without persisting the bearer.
  async function emailVerificationIdempotency(token, action = 'verify') {
    // Reuse a caller key after a lost response in this browser session.
    const key = await emailVerificationStorageKey(token, action);
    const existing = sessionStorageRef.getItem(key);
    if (existing) return existing;
    // Persist only a random caller-owned replay identity.
    const created = cryptoRef.randomUUID();
    sessionStorageRef.setItem(key, created);
    return created;
  }

  // Render the pending verification form and generic status surface.
  function verificationMarkup(message, success) {
    // Preserve pending-enrollment explanation.
    const heading = html`<p class="eyebrow">${t('signup.verifyEyebrow', {}, 'shell')}</p><h1>${t('signup.verifyTitle', {}, 'shell')}</h1>`;
    const copy = html`<p class="auth-copy">${t('signup.verifyCopy', {}, 'shell')}</p>`;
    // Preserve mailbox and locale controls without bearer interpolation.
    const emailInput = html`<input id="email-verification-email" data-testid="email-verification-email" type="email" autocomplete="email" maxlength="254" required>`;
    const email = html`<label>${t('auth.email', {}, 'shell')}${emailInput}</label>`;
    const locale = html`<label>${t('auth.language', {}, 'shell')}<select id="email-verification-locale" data-testid="email-verification-locale"></select></label>`;
    // Enable ownership-bearing actions only while a bearer is held.
    const disabled = emailVerificationBearer ? '' : 'disabled';
    const verify = html`<button class="primary" data-testid="email-verification-submit" type="submit" ${disabled}>${t('signup.verifySubmit', {}, 'shell')}</button>`;
    const resend = html`<button class="secondary" data-testid="email-verification-resend" type="button">${t('signup.resend', {}, 'shell')}</button>`;
    const cancel = html`<button class="secondary" data-testid="email-verification-cancel" type="button" ${disabled}>${t('signup.cancel', {}, 'shell')}</button>`;
    const status = html`<p id="email-verification-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${message}</p>`;
    const form = html`<form id="email-verification-form" class="auth-form">${email}${locale}${verify}${resend}${cancel}${status}</form>`;
    const back = html`<a href="/" data-testid="email-verification-login-link">${t('invitation.back', {}, 'shell')}</a>`;
    return html`<section class="auth-panel" data-testid="email-verification-pending">${heading}${copy}${form}${back}</section>`;
  }

  // Complete the exact purpose-bound verification request.
  async function submitVerification(event) {
    // Prevent navigation that could repeat or expose bearer state.
    event.preventDefault();
    const submit = documentRef.getElementById('email-verification-submit');
    const status = documentRef.getElementById('email-verification-message');
    submit.disabled = true;
    try {
      // Submit transient bearer, recipient, and reload-stable caller key only.
      await api('/api/v2/auth/signup/verify', {
        method: 'POST',
        body: {
          token: emailVerificationBearer,
          email: documentRef.getElementById('email-verification-email').value.trim(),
          idempotency_key: await emailVerificationIdempotency(emailVerificationBearer),
        },
      });
      // Remove only the terminal verification replay key and transient state.
      sessionStorageRef.removeItem(await emailVerificationStorageKey(emailVerificationBearer));
      emailVerificationBearer = '';
      pendingEnrollmentEmail = '';
      historyRef.replaceState({}, '', '/');
      renderLoginGate(t('signup.verified', {}, 'shell'));
    } catch (_) {
      // Collapse malformed, expired, consumed, cancelled, and raced results.
      status.textContent = t('signup.verifyUnavailable', {}, 'shell');
      submit.disabled = false;
    }
  }

  // Request enumeration-safe replacement delivery.
  async function resendVerification(renderEmailVerificationGate) {
    // Resolve the generic status outlet before the request.
    const status = documentRef.getElementById('email-verification-message');
    try {
      // Request replacement under one random action key.
      await api('/api/v2/auth/signup/resend', {
        method: 'POST',
        body: {
          email: documentRef.getElementById('email-verification-email').value.trim(),
          locale: documentRef.getElementById('email-verification-locale').value,
          idempotency_key: cryptoRef.randomUUID(),
        },
      });
      // Drop the now-stale bearer until the replacement link arrives.
      emailVerificationBearer = '';
      renderEmailVerificationGate(t('signup.resent', {}, 'shell'), true);
    } catch (_) {
      // Publish no recipient or provider state.
      status.textContent = t('signup.verifyUnavailable', {}, 'shell');
    }
  }

  // Cancel the bearer-owned pending enrollment without enumeration.
  async function cancelVerification() {
    // Resolve the generic status outlet before the request.
    const status = documentRef.getElementById('email-verification-message');
    try {
      // Revoke only the current generation after bearer ownership proof.
      await api('/api/v2/auth/signup/cancel', {
        method: 'POST',
        body: {
          token: emailVerificationBearer,
          email: documentRef.getElementById('email-verification-email').value.trim(),
          idempotency_key: await emailVerificationIdempotency(emailVerificationBearer, 'cancel'),
        },
      });
      // Remove terminal replay state and all pending module values.
      sessionStorageRef.removeItem(
        await emailVerificationStorageKey(emailVerificationBearer, 'cancel'),
      );
      emailVerificationBearer = '';
      pendingEnrollmentEmail = '';
      historyRef.replaceState({}, '', '/');
      renderLoginGate(t('signup.cancelled', {}, 'shell'));
    } catch (_) {
      // Preserve one generic failure without changing route state.
      status.textContent = t('signup.verifyUnavailable', {}, 'shell');
    }
  }

  // Render verified-email pending, resend, cancellation, and completion controls.
  function renderEmailVerificationGate(message = '', success = false) {
    // Capture a newly arrived bearer once before removing browser history.
    const arrivalToken = transientRouteBearer('/enroll/verify');
    if (arrivalToken) {
      // Retain bearer material only for this pending verification.
      emailVerificationBearer = arrivalToken;
      historyRef.replaceState({}, '', '/enroll/verify');
    }
    // Clear authenticated identity while this account-free route is mounted.
    setSession(null);
    windowRef.CasinoCurrentUser = null;
    syncFeedbackReporter(null);
    documentRef.body.classList.remove('lobby-active', 'guest-trial-active');
    documentRef.body.classList.add('auth-locked');
    const view = documentRef.getElementById('view');
    // Remove authenticated semantics and apply the shared auth layout.
    for (const attribute of ['tabindex', 'role', 'aria-label', 'data-testid']) {
      // Remove one static shell-owned attribute.
      view.removeAttribute(attribute);
    }
    view.className = 'screen auth-screen';
    view.innerHTML = html`${verificationMarkup(message, success)}`;
    // Prefill only module-memory mailbox state after markup installation.
    documentRef.getElementById('email-verification-email').value = pendingEnrollmentEmail;
    wireLocaleSelect(
      documentRef.getElementById('email-verification-locale'),
      () => renderEmailVerificationGate(message, success),
    );
    // Bind exact verify, resend, and cancellation actions.
    documentRef.getElementById('email-verification-form').onsubmit = submitVerification;
    view.querySelector('[data-testid="email-verification-resend"]').onclick = () => (
      resendVerification(renderEmailVerificationGate)
    );
    view.querySelector('[data-testid="email-verification-cancel"]').onclick = cancelVerification;
  }

  // Publish renderer plus the narrow Signup-to-Verification mailbox seam.
  return { renderEmailVerificationGate, setPendingEnrollmentEmail };
}
