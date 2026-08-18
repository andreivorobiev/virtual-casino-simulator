// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build enumeration-safe password recovery behind one public route boundary. (RESET-004, SEC-016)

// Create the password-reset renderer and bounded submission handler.
export function createPasswordResetView(dependencies) {
  // Capture the accepted browser, API, locale, and presentation seams.
  const {
    api, cryptoRef, documentRef, getLocaleState, historyRef, holdTransientBearer,
    renderLoginGate, safe, setSession, syncFeedbackReporter, t,
    transientRouteBearer, windowRef,
  } = dependencies;
  // Hold an arrived reset bearer only in module memory across locale rerenders.
  let passwordResetBearerToken = '';

  // Render shared heading, mailbox, message, and back-link fragments.
  function sharedMarkup(message, success, complete) {
    // Preserve recovery identity and mode-specific title/copy.
    const eyebrow = `<p class="eyebrow">${safe(t('recovery.eyebrow', {}, 'shell'))}</p>`;
    const titleKey = complete ? 'recovery.completeTitle' : 'recovery.title';
    const copyKey = complete ? 'recovery.completeCopy' : 'recovery.copy';
    const heading = `<h1>${safe(t(titleKey, {}, 'shell'))}</h1><p class="auth-copy">${safe(t(copyKey, {}, 'shell'))}</p>`;
    // Preserve an explicit mailbox field for both non-enumerating flows.
    const email = `<label>${safe(t('auth.email', {}, 'shell'))}<input id="reset-email" type="email" autocomplete="email" required></label>`;
    const password = complete
      ? `<label>${safe(t('recovery.newPassword', {}, 'shell'))}<input id="reset-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label>`
      : '';
    const actionKey = complete ? 'recovery.complete' : 'recovery.send';
    const action = `<button class="primary" type="submit">${safe(t(actionKey, {}, 'shell'))}</button>`;
    const status = `<p id="reset-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${safe(message)}</p>`;
    const form = `<form id="password-reset-form" class="auth-form">${email}${password}${action}${status}</form>`;
    const back = `<a href="/">${safe(t('recovery.back', {}, 'shell'))}</a>`;
    const testId = complete ? 'password-reset-complete' : 'password-reset-initiate';
    return `<section class="auth-panel" data-testid="${testId}">${eyebrow}${heading}${form}${back}</section>`;
  }

  // Submit the currently rendered initiation or completion flow.
  async function submitReset(event, token) {
    // Keep the public route stable while the bounded request settles.
    event.preventDefault();
    const status = documentRef.getElementById('reset-message');
    const submit = event.currentTarget.querySelector('button[type="submit"]');
    submit.disabled = true;
    try {
      // Complete the bearer-owned replacement when an arrived token exists.
      if (token) {
        await api('/api/v2/auth/password-reset/complete', {
          method: 'POST',
          body: {
            token,
            email: documentRef.getElementById('reset-email').value.trim(),
            new_password: documentRef.getElementById('reset-password').value,
            idempotency_key: cryptoRef.randomUUID(),
          },
        });
        // Drop module bearer state and return to sign-in after terminal acknowledgement.
        passwordResetBearerToken = '';
        historyRef.replaceState({}, '', '/');
        renderLoginGate(t('recovery.completed', {}, 'shell'));
        return;
      }
      // Initiate or reissue recovery with an identical public acknowledgement.
      await api('/api/v2/auth/password-reset/initiate', {
        method: 'POST',
        body: {
          email: documentRef.getElementById('reset-email').value.trim(),
          locale: getLocaleState().locale,
          idempotency_key: cryptoRef.randomUUID(),
        },
      });
      if (status) {
        // Publish no account-existence or delivery state.
        status.textContent = t('recovery.accepted', {}, 'shell');
        status.dataset.success = 'true';
      }
    } catch (_) {
      // Collapse policy, bearer, provider, and delivery failures.
      if (status) status.textContent = t('recovery.unavailable', {}, 'shell');
    } finally {
      // Avoid touching a submit control removed by successful completion navigation.
      if (submit.isConnected) submit.disabled = false;
    }
  }

  // Render recovery initiation or bearer completion without casino routes.
  function renderPasswordResetGate(message = '', success = false) {
    // Clear stale authenticated identity while recovery owns the public outlet.
    setSession(null);
    windowRef.CasinoCurrentUser = null;
    syncFeedbackReporter(null);
    documentRef.body.classList.remove('lobby-active');
    documentRef.body.classList.add('auth-locked');
    const view = documentRef.getElementById('view');
    view.className = 'screen auth-screen';
    // Remove protected-region semantics before rendering the public form.
    for (const attribute of ['tabindex', 'role', 'aria-label', 'data-testid']) {
      // Remove one static shell-owned attribute.
      view.removeAttribute(attribute);
    }
    // Capture one newly arrived bearer without discarding the value on rerender.
    const arrivalToken = transientRouteBearer('/account/reset');
    passwordResetBearerToken = holdTransientBearer(passwordResetBearerToken, arrivalToken);
    const token = passwordResetBearerToken;
    // Scrub browser bearer material before form paint or later logging.
    if (token && new URL(windowRef.location.href).searchParams.has('token')) {
      historyRef.replaceState({}, '', '/account/reset');
    }
    // Render the exact mode and bind one bounded handler.
    view.innerHTML = sharedMarkup(message, success, Boolean(token));
    documentRef.getElementById('password-reset-form').onsubmit = event => submitReset(event, token);
  }

  // Publish only the shell-facing reset renderer.
  return renderPasswordResetGate;
}
