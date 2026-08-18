// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the required terms acknowledgement view behind one route boundary. (AUTH-011)

// Create the terms renderer and its accepted mutation handler.
export function createTermsView(dependencies) {
  // Capture the existing API, session, locale, and presentation seams.
  const {
    acceptTerms, documentRef, enterAuthenticated, getLocaleState, getSession, html,
    normalizeCurrentUser, safe, setSession, t,
  } = dependencies;

  // Accept the required private-beta terms for the current user.
  async function handleTermsAccept() {
    // Read the shared message outlet for API errors.
    const message = documentRef.getElementById('auth-message');
    try {
      // Read the required version from the exact cached session.
      const session = getSession();
      const version = session?.terms?.version || session?.terms?.required_version || 'private-beta';
      // Call the published current-user terms endpoint with the active locale.
      const terms = await acceptTerms({
        terms_version: version,
        locale: getLocaleState().locale,
      });
      // Merge returned terms status into the canonical current-user payload.
      const updated = normalizeCurrentUser({ ...session, terms });
      setSession(updated);
      // Enter the authenticated shell with the updated terms state.
      await enterAuthenticated(updated);
    } catch (error) {
      // Keep failures inside the terms panel.
      if (message) message.textContent = error.message;
    }
  }

  // Render the terms acceptance step when the current session requires it.
  function renderTermsGate(session) {
    // Store the current session so acceptance continues into the shell.
    setSession(session);
    // Leave lobby-only containment before replacing the route outlet.
    documentRef.body.classList.remove('lobby-active');
    // Keep chrome and game routes hidden until terms are accepted.
    documentRef.body.classList.add('auth-locked');
    const view = documentRef.getElementById('view');
    // Remove authenticated lobby-region semantics.
    for (const attribute of ['tabindex', 'role', 'aria-label', 'data-testid']) {
      // Remove one static authenticated-shell attribute.
      view.removeAttribute(attribute);
    }
    // Apply the shared public authentication layout.
    view.className = 'screen auth-screen';
    const version = session.terms?.version || session.terms?.required_version || 'private-beta';
    // Render concise toy-simulator acknowledgement copy.
    const eyebrow = html`<p class="eyebrow">${t('terms.eyebrow', {}, 'shell')}</p>`;
    const heading = html`<h1>${t('terms.title', {}, 'shell')}</h1>`;
    const copy = html`<p class="auth-copy">${t('terms.copy', {}, 'shell')}</p>`;
    const versionCopy = html`<p class="auth-copy strong">${t('terms.version', { version }, 'shell')}</p>`;
    const accept = html`<button id="accept-terms-btn" class="primary" data-testid="accept-terms" type="button">${t('terms.accept', {}, 'shell')}</button>`;
    const message = html`<p id="auth-message" class="auth-message"></p>`;
    view.innerHTML = html`<section class="auth-panel" data-testid="terms-gate">${eyebrow}${heading}${copy}${versionCopy}${accept}${message}</section>`;
    // Bind one explicit acceptance operation.
    documentRef.getElementById('accept-terms-btn').onclick = handleTermsAccept;
  }

  // Publish only the shell-facing terms renderer.
  return renderTermsGate;
}
