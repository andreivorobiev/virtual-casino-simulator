// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Own logged-out entry and authenticated provider controls outside the application shell. (UX-028, OAUTH-007)

// Create the Login renderer and its policy-gated entry handlers.
export function createLoginView(dependencies) {
  // Capture browser, API, locale, session, and presentation seams owned by this view.
  const {
    api, documentRef, enterAuthenticated, getLocaleState, getSession, guestTrial,
    historyRef, html, isGuestSession, locationRef, login, navigate, oauthLinks,
    oauthProviders, raw, safe, startOAuth, syncFeedbackReporter, t, unlinkOAuth,
    windowRef, wireLocaleSelect,
  } = dependencies;
  // Invalidate asynchronous capability reads whenever locale or route rendering replaces the gate.
  let loginGateGeneration = 0;
  // Consume one fixed provider-completion marker at module construction time.
  const oauthCompletion = readOAuthCompletion();

  // Consume only fixed OAuth completion markers without retaining callback query material. (OAUTH-010)
  function readOAuthCompletion() {
    // Parse the current same-origin URL through the browser URL implementation.
    const url = new URL(locationRef.href);
    // Read only the bounded provider and outcome values emitted by the server.
    const provider = url.searchParams.get('oauth_provider');
    // Read the fixed completion state independently from every other query field.
    const status = url.searchParams.get('oauth_status');
    // Ignore any unreviewed or partial values without reflecting them into the UI.
    if (!['google', 'facebook'].includes(provider) || !['linked', 'signed_in', 'signed_up', 'cancelled', 'error'].includes(status)) return null;
    // Remove only the fixed completion markers before later logs, reloads, or copied links can retain them.
    url.searchParams.delete('oauth_provider');
    // Remove the bounded status marker alongside its provider.
    url.searchParams.delete('oauth_status');
    // Replace the current history entry while preserving unrelated approved test and locale parameters.
    historyRef.replaceState(historyRef.state, '', `${url.pathname}${url.search}${url.hash}`);
    // Return only the allowlisted low-cardinality completion facts.
    return { provider, status };
  }

  // Resolve localized copy for one server-owned OAuth completion marker.
  function oauthCompletionCopy() {
    // Return no copy when the browser did not arrive from a reviewed completion redirect.
    if (!oauthCompletion) return '';
    // Map first provider enrollment to its dedicated privacy-safe acknowledgement.
    if (oauthCompletion.status === 'signed_up') return t('signup.oauthSuccess', {}, 'shell');
    // Map successful link and sign-in outcomes to the existing privacy-safe acknowledgement.
    if (['linked', 'signed_in'].includes(oauthCompletion.status)) return t('auth.oauthCallbackSuccess', {}, 'shell');
    // Map cancellation separately without reflecting provider error parameters.
    if (oauthCompletion.status === 'cancelled') return t('auth.oauthCallbackCancelled', {}, 'shell');
    // Collapse every reviewed error outcome to one generic retry-safe message.
    return t('auth.oauthCallbackError', {}, 'shell');
  }

  // Replace the shared Auth status through the only live region on the logged-out decision surface. (UX-028)
  function setAuthStatus(copy, kind = '') {
    // Resolve the single document-owned outlet from the active login generation.
    const outlet = documentRef.getElementById('auth-message');
    // Stop when route or session entry has already replaced the login gate.
    if (!outlet) return;
    // Publish only localized product copy through the stable reserved-height region.
    outlet.textContent = copy;
    // Retain one low-cardinality validation owner so acceptance can clear only its own message.
    outlet.dataset.validation = kind;
  }

  // Enforce one terms rule and one focus/error behavior for both guest and password entry. (UX-028)
  function requireLoginTerms() {
    // Read the one shared acknowledgement checkbox from the active login gate.
    const checkbox = documentRef.getElementById('login-terms-check');
    // Continue only after the visitor explicitly accepted the current private-beta terms.
    if (checkbox?.checked === true) return true;
    // Publish the identical localized validation copy regardless of which entry action was invoked.
    setAuthStatus(t('auth.termsRequired', {}, 'shell'), 'terms');
    // Move keyboard and assistive focus to the exact control that needs action.
    checkbox?.focus();
    // Prevent every auth mutation until explicit acceptance exists.
    return false;
  }

  // Toggle one button-owned disclosure without motion or additional live-region output. (UX-028)
  function toggleAuthDisclosure(button) {
    // Read the controlled content id from the semantic disclosure button.
    const target = documentRef.getElementById(button.getAttribute('aria-controls'));
    // Stop without mutation when malformed markup cannot resolve the owned disclosure.
    if (!target) return;
    // Flip the current semantic expansion state from the button's exact boolean string.
    const expanded = button.getAttribute('aria-expanded') !== 'true';
    // Publish the new state for keyboard and assistive technology users.
    button.setAttribute('aria-expanded', String(expanded));
    // Keep the disclosure out of layout and reading order until requested.
    target.hidden = !expanded;
  }

  // Submit the login form to the backend-owned auth endpoint.
  async function handleLoginSubmit(event) {
    // Prevent the browser from reloading during the auth flow.
    event.preventDefault();
    // Enforce shared terms before native credential validation.
    if (!requireLoginTerms()) return;
    // Preserve native email/password validity after the shared terms decision has passed.
    if (!event.currentTarget.reportValidity()) return;
    // Read the shared message outlet for validation and API errors.
    const message = documentRef.getElementById('auth-message');
    // Start protected login logic so validation errors stay inside the auth panel.
    try {
      // Clear stale validation or session copy before the exact sign-in request begins.
      setAuthStatus('');
      // Read bounded credentials and active locale from browser-visible controls.
      const email = documentRef.getElementById('login-email').value.trim();
      const password = documentRef.getElementById('login-password').value;
      const locale = getLocaleState().locale;
      // Call the planned v2 auth endpoint without changing backend internals.
      const session = await login({ email, password, locale, terms_acknowledged: true });
      // Enter the authenticated shell or terms step from the returned payload.
      await enterAuthenticated(session);
    } catch (error) {
      // Render the API error without leaving the login gate.
      if (message) message.textContent = error.message;
    }
  }

  // Start one account-free disposable guest trial from the login surface. (GUEST-001)
  async function handleGuestTrial() {
    // Read the shared message outlet for API errors.
    const message = documentRef.getElementById('auth-message');
    // Start protected guest logic so any rejection stays inside the auth panel.
    try {
      // Enforce the exact same acknowledgement, copy, and focus behavior as password sign-in.
      if (!requireLoginTerms()) return;
      // Clear stale validation or session copy before the exact guest request begins.
      setAuthStatus('');
      // Resolve the bounded viewport class without exposing raw dimensions to the service.
      const device = windowRef.innerWidth < 600 ? 'mobile' : windowRef.innerWidth < 1100 ? 'tablet' : 'desktop';
      // Create the isolated disposable guest session with exact versioned consent metadata.
      const session = await guestTrial({ accepted: true, terms_version: 'private-beta-1', locale: getLocaleState().locale, device });
      // Enter the authenticated shell using the same payload shape as registered login.
      await enterAuthenticated(session);
    } catch (error) {
      // Map capacity and rate boundaries to concise product copy without raw server codes.
      const copy = error.status === 403 ? t('auth.guestCapacityFull', {}, 'shell') : error.status === 429 ? t('auth.guestRateLimited', {}, 'shell') : error.message;
      // Render the localized failure through the same stable region used by every auth outcome.
      if (message) setAuthStatus(copy);
    }
  }

  // Render guest and enrollment actions only after public policy authorizes their exact state. (GUEST-001, UX-028)
  async function renderLoginPolicyActions(generation) {
    // Start protected capability loading so a failed policy never creates an unauthorized action.
    try {
      // Read only boolean enrollment capabilities from the public no-state endpoint.
      const policy = await api('/api/v2/auth/enrollment-policy');
      // Ignore a completed read when locale, route, or session entry replaced its owning generation.
      if (generation !== loginGateGeneration || !documentRef.querySelector('[data-testid="login-gate"]')) return;
      // Resolve the dedicated primary slot after ownership is revalidated.
      const guestSlot = documentRef.getElementById('auth-guest-slot');
      // Render the real guest action only when the server advertises exact availability.
      const guestMarkup = policy.guest_trials_enabled === true
        ? [
          // Render the primary guest mutation before its explanatory copy.
          `<button id="guest-trial-button" class="primary" data-testid="guest-trial-button" type="button">${safe(t('auth.guestCta', {}, 'shell'))}</button>`,
          // Preserve concise guest lifecycle copy beside the action.
          `<p class="auth-guest-summary" data-testid="guest-trial-copy">${safe(t('auth.guestSummary', {}, 'shell'))}</p>`,
          // Keep optional details behind one keyboard-accessible disclosure.
          `<button class="auth-disclosure-button" data-testid="guest-disclosure-toggle" data-auth-disclosure type="button" `
            + `aria-expanded="false" aria-controls="guest-trial-details">${safe(t('auth.guestDetails', {}, 'shell'))}</button>`,
          // Keep the disclosure hidden until the preceding button expands it.
          `<p id="guest-trial-details" class="auth-disclosure-copy" data-testid="guest-trial-details" hidden>${safe(t('auth.guestInfo', {}, 'shell'))}</p>`,
        ].join('')
        : `<span class="auth-chip" data-testid="guest-trial-unavailable">${safe(t('auth.guestUnavailable', {}, 'shell'))}</span>`;
      // Install the reviewed, individually escaped guest fragments through the tagged sink.
      guestSlot.innerHTML = html`${raw(guestMarkup)}`;
      // Mark the primary slot settled after exact policy-owned markup replaces the loading placeholder.
      guestSlot.setAttribute('aria-busy', 'false');
      // Wire guest creation only when the policy rendered the actionable control.
      documentRef.getElementById('guest-trial-button')?.addEventListener('click', handleGuestTrial);
      // Resolve the separate tertiary account slot without mixing it with provider availability.
      const accountSlot = documentRef.getElementById('auth-account-slot');
      // Render signup only when authorized; otherwise render an explanatory invite-only disclosure chip.
      const accountMarkup = policy.signup_enabled === true
        ? `<a class="auth-tertiary-link" href="/enroll/signup" data-testid="signup-entry-link">${safe(t('signup.cta', {}, 'shell'))}</a>`
        : [
          // Render invite-only status as an explanatory disclosure control.
          `<button class="auth-chip auth-chip-button" data-testid="signup-invite-only" data-auth-disclosure type="button" `
            + `aria-expanded="false" aria-controls="signup-invite-only-copy">${safe(t('signup.inviteOnly', {}, 'shell'))}</button>`,
          // Keep enrollment detail out of layout until explicitly requested.
          `<p id="signup-invite-only-copy" class="auth-disclosure-copy" data-testid="signup-invite-only-copy" hidden>${safe(t('signup.entryCopy', {}, 'shell'))}</p>`,
        ].join('');
      // Install the reviewed, individually escaped account fragments through the tagged sink.
      accountSlot.innerHTML = html`${raw(accountMarkup)}`;
    } catch (_) {
      // Ignore stale failure completion after a replacement login generation owns the document.
      if (generation !== loginGateGeneration) return;
      // Resolve the route-owned slot and suppress a late failure after navigation replaced the login document.
      const guestSlot = documentRef.getElementById('auth-guest-slot');
      // Leave the replacement route untouched when the original login slot no longer exists.
      if (!guestSlot) return;
      // Replace the primary placeholder with noninteractive, localized fail-closed copy.
      guestSlot.innerHTML = html`<span class="auth-chip" data-testid="auth-capability-unavailable">${t('auth.capabilityUnavailable', {}, 'shell')}</span>`;
      // Mark the primary capability slot complete even though no mutation action is available.
      guestSlot.setAttribute('aria-busy', 'false');
      // Publish policy failure only when more important caller/session feedback does not already exist.
      if (!documentRef.getElementById('auth-message')?.textContent) setAuthStatus(t('auth.capabilityUnavailable', {}, 'shell'));
    }
  }

  // Request a one-time authorization URL and navigate without logging or persisting it. (OAUTH-008)
  async function beginOAuth(provider, action) {
    // Read the active auth/account message outlet for bounded errors.
    const message = action === 'signin'
      ? documentRef.getElementById('auth-message')
      : (action === 'signup' ? documentRef.getElementById('signup-message') : documentRef.getElementById('oauth-account-message'));
    // Start protected flow creation so no provider navigation occurs after an API failure.
    try {
      // Read the explicit linking checkbox only for authenticated account linking.
      const confirmation = documentRef.getElementById('oauth-link-confirm');
      // Stop linking until the canonical user explicitly confirms this action.
      if (action === 'link' && !confirmation?.checked) throw new Error(t('auth.oauthConfirmRequired', {}, 'shell'));
      // Require every social-enrollment acknowledgement before provider navigation.
      const signupConsent = action !== 'signup' || [
        // Require current terms before social enrollment.
        documentRef.getElementById('signup-terms')?.checked,
        // Require the privacy acknowledgement before social enrollment.
        documentRef.getElementById('signup-privacy')?.checked,
        // Require the fake-money acknowledgement before social enrollment.
        documentRef.getElementById('signup-play-token')?.checked,
      ].every(Boolean);
      // Stop social enrollment when any required acknowledgement is absent.
      if (!signupConsent) throw new Error(t('signup.consentRequired', {}, 'shell'));
      // Build the explicit signup intent without email, account, role, or wallet targets.
      const signupIntent = action === 'signup' ? {
        terms_version: 'private-beta-1',
        accepted_terms: true,
        accepted_privacy: true,
        accepted_fake_money: true,
        locale: documentRef.getElementById('signup-locale')?.value || 'en-US',
      } : {};
      // Request a short-lived browser-bound flow with a same-origin destination.
      const result = await startOAuth(provider, { action, return_to: '/', ...(action === 'link' ? { confirm_link: true } : {}), ...signupIntent });
      // Navigate directly without copying the sensitive URL into logs or application storage.
      locationRef.assign(result.authorization_url);
    } catch (error) {
      // Keep the page usable and avoid reflecting provider response content.
      if (message) message.textContent = error.message;
    }
  }

  // Render only independently available providers and omit the complete block otherwise. (OAUTH-007, UX-028)
  async function renderLoginProviderActions(generation) {
    // Start protected availability loading so local-password and guest entry remain usable on failure.
    try {
      // Fetch only fixed provider ids and boolean availability.
      const result = await oauthProviders();
      // Select exact provider identifiers whose complete runtime and independent network gate are ready.
      const available = new Set((result.providers || []).filter(item => ['google', 'facebook'].includes(item.provider) && item.available === true).map(item => item.provider));
      // Ignore a completed read when locale, route, or session entry replaced its owning generation.
      if (generation !== loginGateGeneration || !documentRef.querySelector('[data-testid="login-gate"]')) return;
      // Resolve the provider-only tertiary slot after exact generation ownership is confirmed.
      const providerSlot = documentRef.getElementById('auth-provider-slot');
      // Ignore route replacement that removed the provider slot after the generation check.
      if (!providerSlot) return;
      // Build fixed provider controls only for exact ready identifiers.
      const buttons = ['google', 'facebook'].filter(provider => available.has(provider)).map(provider => {
        // Resolve provider-specific copy from one allowlisted identifier.
        const label = t(`auth.oauth${provider === 'google' ? 'Google' : 'Facebook'}`, {}, 'shell');
        // Return one fixed provider sign-in action.
        return html`<button class="oauth-provider-button" data-testid="oauth-${provider}" type="button">${label}</button>`;
      });
      // Omit the complete provider region when no provider is actionable.
      const providerLabel = t('auth.oauthDivider', {}, 'shell');
      // Mount the provider section only when at least one provider is actionable.
      providerSlot.innerHTML = html`${available.size
        ? html`<section class="auth-provider-actions" data-testid="oauth-providers-available" aria-label="${providerLabel}">${buttons}</section>`
        : html``}`;
      // Wire only controls that exist after the server reported that provider available.
      for (const provider of available) documentRef.querySelector(`[data-testid="oauth-${provider}"]`)?.addEventListener('click', () => beginOAuth(provider, 'signin'));
    } catch (_) {
      // Ignore stale failure completion after a replacement login generation owns the document.
      if (generation !== loginGateGeneration) return;
      // Resolve the route-owned provider slot and suppress late failures after navigation.
      const providerSlot = documentRef.getElementById('auth-provider-slot');
      // Leave replacement route markup untouched when the original slot no longer exists.
      if (!providerSlot) return;
      // Keep the provider slot action-free while exposing a stable test state outside live semantics.
      providerSlot.innerHTML = html`<span data-testid="oauth-providers-status-error" hidden></span>`;
      // Publish generic localized provider feedback only when caller/session feedback is not already visible.
      if (!documentRef.getElementById('auth-message')?.textContent) setAuthStatus(t('auth.oauthStatusError', {}, 'shell'));
    }
  }

  // Render authenticated provider linking with explicit confirmation and safe unlink. (OAUTH-009, OAUTH-010)
  async function renderOAuthAccountControls() {
    // Read the persistent popover reserved by the authenticated shell.
    const popover = documentRef.getElementById('oauth-account-popover');
    // Stop before login, for a guest, or while another auth gate owns the page.
    if (!popover || !getSession() || isGuestSession()) return;
    // Stamp a bounded loading state for assistive and automated lifecycle evidence.
    popover.dataset.oauthState = 'loading';
    // Render a localized loading state without provider configuration details.
    popover.innerHTML = html`<h2>${t('auth.oauthAccountTitle', {}, 'shell')}</h2><p class="oauth-provider-copy">${t('status.loading', {}, 'shell')}</p>`;
    // Start protected link-status loading so provider errors cannot affect gameplay.
    try {
      // Read boolean availability and ownership for the current canonical user.
      const result = await oauthLinks();
      // Mark the boolean-only linked mix without exposing provider subjects or user ids.
      popover.dataset.oauthState = (result.providers || []).some(item => item.linked === true) ? 'linked' : 'unlinked';
      // Render one fixed provider row with the appropriate link or unlink action.
      const rows = (result.providers || []).filter(item => ['google', 'facebook'].includes(item.provider)).map(item => {
        // Resolve fixed provider name and action copy from locale messages.
        const name = item.provider === 'google' ? t('auth.oauthGoogleName', {}, 'shell') : t('auth.oauthFacebookName', {}, 'shell');
        const action = item.linked ? 'unlink' : 'link';
        const label = item.linked ? t('auth.oauthUnlink', {}, 'shell') : t('auth.oauthLink', {}, 'shell');
        const disabled = !item.linked && !item.available ? 'disabled aria-disabled="true"' : '';
        // Return one bounded provider row without provider subject data.
        return [
          // Open the fixed provider identity row without exposing a subject.
          `<div class="oauth-account-row" data-testid="oauth-link-${safe(item.provider)}"><span>${safe(name)}</span>`,
          // Bind action intent to fixed data attributes consumed below.
          `<button type="button" data-oauth-account-provider="${safe(item.provider)}" data-oauth-account-action="${action}" ${disabled}>${safe(label)}</button></div>`,
        ].join('');
      }).join('');
      // Add completion acknowledgement only when a reviewed marker exists.
      const completion = oauthCompletion ? `<p class="auth-message" data-testid="oauth-callback-message" role="status">${safe(oauthCompletionCopy())}</p>` : '';
      // Require explicit consent adjacent to provider actions.
      const accountMarkup = [
        // Name the account-method section before its actions.
        `<h2>${safe(t('auth.oauthAccountTitle', {}, 'shell'))}</h2>`,
        // Preserve the independent personal-settings entry.
        `<button type="button" class="secondary" data-testid="my-settings-entry">${safe(t('settings.title', {}, 'shell'))}</button>`,
        // Explain provider linking without configuration details.
        `<p class="oauth-provider-copy">${safe(t('auth.oauthAccountCopy', {}, 'shell'))}</p>`,
        // Include the bounded completion acknowledgement when present.
        completion,
        // Require explicit confirmation adjacent to provider actions.
        `<label class="check-row oauth-link-confirm"><input id="oauth-link-confirm" type="checkbox" data-testid="oauth-link-confirm">`
          + `<span>${safe(t('auth.oauthLinkConfirm', {}, 'shell'))}</span></label>`,
        // Append reviewed provider rows and their one status owner.
        `${rows}<p id="oauth-account-message" class="auth-message" role="status"></p>`,
      ].join('');
      // Install reviewed, individually escaped account fragments through the tagged sink.
      popover.innerHTML = html`${raw(accountMarkup)}`;
      // Keep personal settings routing separate from provider-link actions and Admin Console.
      popover.querySelector('[data-testid="my-settings-entry"]').onclick = () => {
        // Close the account menu before the shell takes ownership of Settings.
        documentRef.getElementById('account-menu')?.removeAttribute('open');
        // Route through the existing authenticated navigation controller.
        void navigate('settings');
      };
      // Wire each rendered provider action through its explicit operation.
      popover.querySelectorAll('[data-oauth-account-provider]').forEach(button => {
        // Handle link navigation or a separately confirmed unlink transaction.
        button.onclick = async () => {
          // Read the bounded action and provider from server-derived fixed rows.
          const provider = button.dataset.oauthAccountProvider;
          // Start a confirmed provider navigation for an unlinked account.
          if (button.dataset.oauthAccountAction === 'link') return beginOAuth(provider, 'link');
          // Require a browser confirmation before the destructive unlink request.
          if (!windowRef.confirm(t('auth.oauthUnlinkConfirm', {}, 'shell'))) return;
          // Start protected unlink handling so a failed request stays local to the popover.
          try {
            // Remove only this provider's current-user link.
            await unlinkOAuth(provider);
            // Refresh boolean provider rows after a successful unlink.
            await renderOAuthAccountControls();
          } catch (_) {
            // Publish one generic localized message without provider response details.
            const status = documentRef.getElementById('oauth-account-message');
            // Update only the still-mounted account message outlet.
            if (status) status.textContent = t('auth.oauthStatusError', {}, 'shell');
          }
        };
      });
    } catch (_) {
      // Stamp one generic failure state without transport or provider detail.
      popover.dataset.oauthState = 'status-error';
      // Publish no provider configuration or request details.
      popover.innerHTML = html`<h2>${t('auth.oauthAccountTitle', {}, 'shell')}</h2><p class="oauth-provider-copy">${t('auth.oauthStatusError', {}, 'shell')}</p>`;
    }
  }

  // Render a logged-out browser gate before any casino route can mount.
  function renderLoginGate(message = '') {
    // Clear the public current-user hook while the browser is logged out.
    windowRef.CasinoCurrentUser = null;
    // Hide the registered-user reporting affordance for logged-out and guest entry screens.
    syncFeedbackReporter(null);
    // Leave lobby-only flex containment before the public authentication screen replaces the route outlet.
    documentRef.body.classList.remove('lobby-active');
    // Mark the document so chrome and game routes stay hidden while logged out.
    documentRef.body.classList.add('auth-locked');
    // Read the main route outlet reserved by index.html.
    const view = documentRef.getElementById('view');
    // Remove authenticated lobby-region semantics before exposing the public login gate.
    view.removeAttribute('tabindex');
    view.removeAttribute('role');
    view.removeAttribute('aria-label');
    view.removeAttribute('data-testid');
    // Apply the auth screen class contract for login and terms flows.
    view.className = 'screen auth-screen';
    // Clear guest-only shell sizing after explicit end, expiry, or browser-proof loss.
    documentRef.body.classList.remove('guest-trial-active');
    // Resolve explicit caller feedback before a fixed provider completion acknowledgement.
    const authMessage = message || oauthCompletionCopy();
    // Claim one generation before asynchronous policy reads can populate this exact login render.
    const generation = ++loginGateGeneration;
    // Render one guest-first decision hierarchy with a single shared terms row and status owner. (UX-028)
    const header = [
      // Present brand and legal copy before entry controls.
      `<header class="auth-entry-header"><div><h1>${safe(t('brand.title', {}, 'shell'))}</h1>`,
      `<p id="auth-legal-line" class="auth-legal-line">${safe(t('auth.legalLine', {}, 'shell'))}</p></div>`,
      // Keep locale selection available before authentication.
      `<label class="auth-locale-switch"><span>${safe(t('auth.language', {}, 'shell'))}</span>`,
      `<select id="auth-locale-select" data-testid="auth-locale-select" aria-label="${safe(t('language.aria', {}, 'shell'))}"></select></label></header>`,
    ].join('');
    // Reserve the policy-owned guest action slot without enabling an unverified capability.
    const guestSlot = `<div id="auth-guest-slot" class="auth-primary-slot" data-testid="auth-guest-slot" aria-busy="true">`
      + `<p class="auth-capability-loading">${safe(t('status.loading', {}, 'shell'))}</p></div>`;
    // Render the one acknowledgement shared by password and guest entry.
    const terms = `<label class="check-row auth-terms-row"><input id="login-terms-check" data-testid="login-terms-check" type="checkbox">`
      + `<span>${safe(t('auth.termsCheck', {}, 'shell'))}</span></label>`;
    // Reserve one polite status owner for callback, validation, and API copy.
    const status = `<p id="auth-message" class="auth-message" data-testid="oauth-callback-message" role="status" aria-live="polite" aria-atomic="true">${safe(authMessage)}</p>`;
    // Build the native credential fields inside one validation-owned form.
    const fields = [
      `<label>${safe(t('auth.email', {}, 'shell'))}<input id="login-email" data-testid="login-email" type="email" autocomplete="username" required></label>`,
      `<label>${safe(t('auth.password', {}, 'shell'))}<input id="login-password" data-testid="login-password" type="password" autocomplete="current-password" required></label>`,
    ].join('');
    // Preserve the credential submit and recovery entry after the bounded fields.
    const submit = `<button class="secondary auth-signin-submit" data-testid="login-submit" type="submit">${safe(t('auth.submit', {}, 'shell'))}</button>`;
    const recovery = `<a class="auth-reset-link" href="/account/reset" data-testid="password-reset-entry">${safe(t('recovery.forgot', {}, 'shell'))}</a>`;
    // Compose the password sign-in region under its accessible heading.
    const signin = `<section class="auth-signin" aria-labelledby="auth-signin-heading">`
      + `<h2 id="auth-signin-heading">${safe(t('auth.signinHeading', {}, 'shell'))}</h2>`
      + `<form id="login-form" class="auth-form auth-signin-form" novalidate>${fields}${submit}${recovery}</form></section>`;
    // Reserve independent tertiary slots for account policy and provider readiness.
    const tertiary = '<div id="auth-tertiary" class="auth-tertiary"><div id="auth-account-slot"></div><div id="auth-provider-slot"></div></div>';
    // Mount the complete stable gate before asynchronous capabilities resolve.
    view.innerHTML = html`<section class="auth-panel auth-entry" data-testid="login-gate">${raw(header)}${raw(guestSlot)}${raw(terms)}${raw(status)}${raw(signin)}${raw(tertiary)}</section>`;
    // Wire the auth-screen locale selector and rerender the gate after switching.
    wireLocaleSelect(documentRef.getElementById('auth-locale-select'), () => renderLoginGate(message));
    // Wire form submission through the v2 auth login endpoint.
    documentRef.getElementById('login-form').onsubmit = handleLoginSubmit;
    // Delegate disclosure activation from the stable gate across async slot replacement.
    documentRef.querySelector('[data-testid="login-gate"]').onclick = event => {
      // Resolve only a disclosure control owned by the login gate.
      const button = event.target.closest('[data-auth-disclosure]');
      // Toggle the exact owned disclosure when one was activated.
      if (button) toggleAuthDisclosure(button);
    };
    // Clear only the shared terms error after explicit acceptance.
    documentRef.getElementById('login-terms-check').onchange = event => {
      // Preserve other API/session feedback when terms become accepted.
      if (event.currentTarget.checked && documentRef.getElementById('auth-message')?.dataset.validation === 'terms') setAuthStatus('');
    };
    // Resolve guest and enrollment actions independently from provider latency. (GUEST-001)
    void renderLoginPolicyActions(generation);
    // Resolve provider availability into actions that exist only when they can be used. (OAUTH-007)
    void renderLoginProviderActions(generation);
  }

  // Publish only the seams composed by Signup and the authenticated shell.
  return { beginOAuth, oauthCompletionCopy, renderLoginGate, renderOAuthAccountControls };
}
