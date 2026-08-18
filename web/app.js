// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import required dependency so this module can call the frozen API envelope safely.
import { acceptTerms, api, currentUser, guestTrial, holdTransientBearer, logClient, login, oauthLinks, oauthProviders, publicAuthRouteKind, redeemInvitation, startOAuth, unlinkOAuth } from './core/api.js';
// Import required dependency so this module can render shared wallet and premium UI helpers.
import { renderTokenBalance, toast, tokens, safe, renderPremiumTag, createNavigationOwnership } from './core/ui.js';
// Import required dependency so the shell can preserve locale across auth and route changes.
import { getLocaleState, registerI18nDomains, setLocale, t } from './core/i18n.js';
// Import the active brand and its runtime token applier so one config skins the app.
import { activeBrand } from './core/brand.js';
// Import the session-owned wallet celebration controller without adding game or API authority. (UX-023)
import { createWalletCelebration, createWalletCelebrationLifecycle } from './core/celebrate.js';
// Import required dependency so this module can preload global voice settings before games mount.
import { loadVoiceSettings, setPersonalSoundEnabled } from './core/voice.js';
// Import the registered-user problem-report dialog without adding feedback code to the shared shell.
import { syncFeedbackReporter } from './core/feedback.js';
// Import the persistent every-game wellness controller for opt-in session reminders. (WELL-001, WELL-002)
import { createWellnessController } from './core/wellness.js';
// Import the terms gate so required consent leaves the application monolith. (AUTH-011)
import { createTermsView } from './views/terms.js';
// Import invitation redemption so bearer handling leaves the application monolith. (INVITE-003, INVITE-005)
import { createInvitationView } from './views/invitation.js';
// Import password recovery so transient reset bearer state leaves the application monolith. (RESET-004, SEC-016)
import { createPasswordResetView } from './views/reset.js';
// Import pending-email verification so transient bearer and mailbox state leave the application monolith. (AUTH-018, USER-010)
import { createVerificationView } from './views/verification.js';
// Import full-account enrollment so policy and provider actions leave the application monolith. (AUTH-018, OAUTH-013)
import { createSignupView } from './views/signup.js';
// Import personal settings so preference, history, and guest conversion rendering leave the monolith. (USER-009, CONVERT-003)
import { createSettingsView } from './views/settings.js';
// Import Lobby search, categories, trust, and game cards so catalog rendering leaves the monolith. (CORE-007, CORE-012)
import { createLobbyView } from './views/lobby.js';
// Import logged-out entry and provider account controls so auth rendering leaves the monolith. (UX-028, OAUTH-007)
import { createLoginView } from './views/login.js';
// Import the catalog router so app.js remains shell and view composition. (CORE-007, SESSION-013)
import { createAppRouter } from './core/app_router.js';
// Import browser lifecycle startup and compatible session normalization. (PWA-002, UX-026)
import { currentTokenBalance, normalizeCurrentUser, startApplication } from './core/app_bootstrap.js';

// Store frontend descriptors loaded from the same API catalog that registers backend games.
let gameDescriptors = [];
// Track the active route so navigation can show the selected shell item.
let active = null;
// Cache the latest casino state so lobby and status rail values render without extra calls.
let latestState = null;
// Preserve the latest connection result so locale changes never invent a new status.
let shellConnected = false;
// Cache the authenticated current-user payload so wallet and profile UI stay consistent.
let currentSession = null;
// Own every asynchronous shell route so public-account navigation can invalidate stale game work. (SESSION-013)
const shellNavigationOwnership = createNavigationOwnership();
// Hold the current pre-expiration warning timer so session replacement cannot leave a stale alert. (SESSION-012)
let sessionWarningTimer = null;
// Own BFCache-safe wallet controller replacement for the complete application module lifetime.
const walletCelebrationLifecycle = createWalletCelebrationLifecycle({
  // Bind pagehide and pageshow to the current browser document.
  lifecycleTarget: window,
  // Create each authenticated-session controller from the current persistent wallet nodes.
  createController: () => createWalletCelebration({ amountNode: document.getElementById('balance'), walletNode: document.querySelector('.wallet-pill'), documentRef: document, formatAmount: tokens }),
  // Read only the latest normalized current-session amount for BFCache restoration.
  currentBalance: () => currentTokenBalance(currentSession),
  // Restore the exact authoritative display once before a BFCache baseline is seeded.
  settleDisplay: () => renderTokenBalance(currentSession),
  // Remount only while an authenticated, terms-complete session still owns the shell.
  shouldMount: () => Boolean(currentSession && !currentSession.terms?.required),
});
// Hold the router after extracted views have supplied their render callbacks.
let appRouter = null;
// Own one document-lifetime wellness controller while authenticated sessions replace its timer generation.
const wellnessController = createWellnessController({ apiClient: api, documentRef: document, windowRef: window, translate: (key, values) => t(key, values, 'shell'), formatTokens: tokens });
// Bind login, guest entry, OAuth completion, and provider account controls to shell composition seams.
const { beginOAuth, oauthCompletionCopy, renderLoginGate, renderOAuthAccountControls } = createLoginView({
  api,
  documentRef: document,
  enterAuthenticated: session => enterAuthenticated(session),
  getLocaleState,
  getSession: () => currentSession,
  guestTrial,
  historyRef: history,
  isGuestSession,
  locationRef: location,
  login,
  navigate: route => navigate(route),
  oauthLinks,
  oauthProviders,
  safe,
  startOAuth,
  syncFeedbackReporter,
  t,
  unlinkOAuth,
  windowRef: window,
  wireLocaleSelect,
});
// Bind the terms view to the existing shell session and authenticated-entry lifecycle.
const renderTermsGate = createTermsView({
  acceptTerms,
  documentRef: document,
  enterAuthenticated: session => enterAuthenticated(session),
  getLocaleState,
  getSession: () => currentSession,
  normalizeCurrentUser,
  safe,
  setSession: session => { currentSession = session; },
  t,
});
// Bind invitation redemption to the existing public-route and login composition seams.
const renderInvitationGate = createInvitationView({
  cryptoRef: crypto,
  documentRef: document,
  getLocaleState,
  historyRef: history,
  redeemInvitation,
  renderLoginGate: message => renderLoginGate(message),
  safe,
  sessionStorageRef: sessionStorage,
  setSession: session => { currentSession = session; },
  syncFeedbackReporter,
  t,
  transientRouteBearer,
  wireLocaleSelect,
  windowRef: window,
});
// Bind enumeration-safe password recovery to the existing public-route and login seams.
const renderPasswordResetGate = createPasswordResetView({
  api,
  cryptoRef: crypto,
  documentRef: document,
  getLocaleState,
  historyRef: history,
  holdTransientBearer,
  renderLoginGate: message => renderLoginGate(message),
  safe,
  setSession: session => { currentSession = session; },
  syncFeedbackReporter,
  t,
  transientRouteBearer,
  windowRef: window,
});
// Bind verified-email pending flows to the existing public-route and login composition seams.
const { renderEmailVerificationGate, setPendingEnrollmentEmail } = createVerificationView({
  api,
  cryptoRef: crypto,
  documentRef: document,
  getLocaleState,
  historyRef: history,
  renderLoginGate: message => renderLoginGate(message),
  safe,
  sessionStorageRef: sessionStorage,
  setSession: session => { currentSession = session; },
  syncFeedbackReporter,
  t,
  transientRouteBearer,
  wireLocaleSelect,
  windowRef: window,
});
// Bind Signup to the Verification handoff and existing provider-intent composition seams.
const renderSignupGate = createSignupView({
  api,
  beginOAuth: (provider, action) => beginOAuth(provider, action),
  cryptoRef: crypto,
  documentRef: document,
  getLocaleState,
  historyRef: history,
  oauthCompletionCopy,
  oauthProviders,
  renderEmailVerificationGate,
  safe,
  setPendingEnrollmentEmail,
  setSession: session => { currentSession = session; },
  syncFeedbackReporter,
  t,
  wireLocaleSelect,
  windowRef: window,
});
// Bind personal Settings to existing session and logged-out handoff seams.
const renderMySettings = createSettingsView({
  api,
  clearAuthenticatedShellState,
  cryptoRef: crypto,
  documentRef: document,
  getActive: () => active,
  getLocaleState,
  isGuestSession,
  localeOptionsHtml,
  renderLoginGate: message => renderLoginGate(message),
  safe,
  setLocale,
  setPersonalSoundEnabled,
  t,
});
// Bind Lobby to the current catalog, state snapshot, and shared navigation controller.
const renderLobby = createLobbyView({
  activeBrand,
  getGameDescriptors: () => gameDescriptors,
  getLatestState: () => latestState,
  navigate: route => navigate(route),
  renderPremiumTag,
  safe,
  t,
});
// Bind the catalog router to shell-owned state and extracted view renderers.
appRouter = createAppRouter({
  documentRef: document,
  getActive: () => active,
  getCurrentSession: () => currentSession,
  getGameDescriptors: () => gameDescriptors,
  getLocaleState,
  historyRef: history,
  isInvitationRoute,
  locationRef: location,
  logClient,
  navigationOwnership: shellNavigationOwnership,
  renderExpiredSessionGate,
  renderLobby,
  renderMySettings,
  renderPublicAuthRoute,
  safe,
  setActive: route => { active = route; },
  setLocale,
  t,
  updateCurrentUserShell,
  walletLifecycle: walletCelebrationLifecycle,
  windowRef: window,
});

// Convert one public catalog row through the extracted router.
function descriptorFromCatalog(game) { return appRouter.descriptorFromCatalog(game); }
// Resolve the current browser route through the extracted router.
function routeFromLocation() { return appRouter.routeFromLocation(); }
// Render startup route restoration through the extracted router.
function renderInitialRouteRestore() { return appRouter.renderInitialRouteRestore(); }
// Render manifest locale options through the extracted router.
function localeOptionsHtml() { return appRouter.localeOptionsHtml(); }
// Wire a locale selector through the extracted router.
function wireLocaleSelect(select, afterChange) { return appRouter.wireLocaleSelect(select, afterChange); }
// Render current navigation through the extracted router.
function renderNav() { return appRouter.renderNav(); }
// Reveal the active route through the extracted router.
function revealActiveNav() { return appRouter.revealActiveNav(); }
// Preserve the public navigation export while delegating to the extracted router.
export async function navigate(route, options = {}) { return appRouter.navigate(route, options); }

// Report whether the current authenticated principal is a disposable guest trial. (issue #317)
function isGuestSession() {
  // Recognize a guest only by the server-provided role list so shell affordances never guess.
  return Array.isArray(currentSession?.user?.roles) && currentSession.user.roles.includes('guest');
}

// Clear every shell-owned authenticated cache before showing any logged-out gate.
function clearAuthenticatedShellState(options = {}) {
  // Invalidate every pending route operation unless a public-route caller already advanced ownership.
  if (options.invalidateNavigation !== false) shellNavigationOwnership.invalidate();
  // Cancel any warning owned by the session being discarded.
  clearTimeout(sessionWarningTimer);
  // Clear the handle so a later session can schedule independently.
  sessionWarningTimer = null;
  // Dispose reminders before clearing identity so late API responses cannot reopen authenticated UI.
  wellnessController.dispose();
  // Dispose the session-owned celebration before a game or logged-out surface can remount.
  walletCelebrationLifecycle.unmount('session-cleared');
  // Stop observing game-only rails before the authenticated route outlet is replaced.
  appRouter.disconnectGameObserver();
  // Unmount the active game when its lifecycle hook exists so stale rerenders cannot survive sign-out.
  if (active && appRouter.loadedGames.has(active)) appRouter.loadedGames.get(active).unmount?.();
  // Clear the cached current-user payload so wallet and guest affordances cannot remain visible.
  currentSession = null;
  // Clear the public current-user hook used by game helpers and the wallet renderer.
  window.CasinoCurrentUser = null;
  // Drop the active route marker so later entry chooses from the browser URL intentionally.
  active = null;
  // Clear cached casino state so a later authenticated entry reloads a fresh catalog and wallet rail.
  latestState = null;
  // Clear frontend descriptors derived from protected state while the browser is logged out.
  gameDescriptors = [];
  // Hide registered-user reporting whenever authenticated identity has been discarded.
  syncFeedbackReporter(null);
}

// Schedule one localized pre-expiration warning from the server-authored session descriptor. (SESSION-012)
function scheduleSessionWarning() {
  // Cancel the prior session's or prior refresh's timer before deriving a new deadline.
  clearTimeout(sessionWarningTimer);
  // Read only the safe descriptor returned by the current-user API.
  const descriptor = currentSession?.session_status || {};
  // Stop when warning is disabled, absent, or already terminal.
  if (!descriptor.warn_at || Number(descriptor.warning_seconds || 0) <= 0 || Number(descriptor.expires_in_seconds || 0) <= 0) { sessionWarningTimer = null; return; }
  // Compute a bounded client delay from the server-owned UTC instant.
  const delay = Math.max(0, Math.min(Date.parse(descriptor.warn_at) - Date.now(), 2147483647));
  // Schedule informational copy only; the next API remains the authoritative expiry decision.
  sessionWarningTimer = setTimeout(() => toast(t('session.expiryWarning', { minutes: Math.max(1, Math.ceil(Number(descriptor.warning_seconds) / 60)) }, 'shell')), delay);
}

// Clear every shell-owned authenticated cache before showing the logged-out session-expired gate.
function renderExpiredSessionGate() {
  // Reuse the same teardown path that explicit logout uses so refresh and route recovery cannot diverge.
  clearAuthenticatedShellState();
  // Render the normal login/guest-entry gate with the existing localized expired-session copy.
  renderLoginGate(t('pwa.expiredSession', {}, 'shell'));
}

// Keep persistent shell profile and wallet nodes synchronized with the current user.
function updateCurrentUserShell() {
  // Expose the current-user session so legacy game refresh calls keep token formatting.
  window.CasinoCurrentUser = currentSession;
  // Expose problem reporting only to authenticated persistent accounts.
  syncFeedbackReporter(currentSession?.user);
  // Resolve the authoritative amount independently from any transient presentation.
  const amount = currentTokenBalance(currentSession);
  // Settle the exact display once through the active controller, or directly before it is mounted.
  if (walletCelebrationLifecycle.snapshot().mounted) walletCelebrationLifecycle.update(amount, () => renderTokenBalance(currentSession)); else renderTokenBalance(currentSession);
  // Read the logout button reserved by index.html.
  const logoutButton = document.getElementById('logout-btn');
  // Read the registered-user-only token-credit menu from the persistent shell.
  const walletMenu = document.querySelector('.wallet-menu');
  // Read the visible lifecycle disclosure rendered inside the guest wallet.
  const guestNotice = document.getElementById('guest-trial-notice');
  // Read the best available display name for the authenticated user.
  const name = currentSession?.user?.display_name || currentSession?.user?.username || currentSession?.user?.email || 'Player';
  // Label the logout control with the current user for accessibility.
  if (logoutButton) logoutButton.setAttribute('aria-label', t('auth.logout', { name }, 'shell'));
  // Present the disposable-guest affordance on the persistent control: an End-trial label and a testable guest marker. (issue #317)
  if (logoutButton) {
    // Read the guest state once so the label and markers stay consistent.
    const guest = isGuestSession();
    // Show End trial for a guest and restore the profile glyph for any later registered login.
    logoutButton.innerHTML = guest ? safe(t('guest.endTrial', {}, 'shell')) : '<span aria-hidden="true"></span>';
    // Expose the guest identity and action for accessibility and browser evidence without leaking any credential.
    logoutButton.setAttribute('aria-label', guest ? t('guest.endTrial', {}, 'shell') : t('auth.logout', { name }, 'shell'));
    // Stamp a stable guest marker the shell and tests can read.
    logoutButton.setAttribute('data-guest-trial', guest ? 'true' : 'false');
    // Let responsive CSS allocate enough inline space for the localized End-trial label.
    document.body.classList.toggle('guest-trial-active', guest);
    // Remove the top-up affordance for guests because their one-time 10,000-token grant is fixed and disposable.
    if (walletMenu) walletMenu.hidden = guest;
    // Show the inactivity, lifetime, browser-close, and no-recovery boundary throughout guest play.
    if (guestNotice) { guestNotice.hidden = !guest; guestNotice.textContent = guest ? t('guest.expiryWarning', {}, 'shell') : ''; }
    // Let responsive CSS allocate a disclosure row only while the disposable principal is active.
    document.querySelector('.wallet-pill')?.classList.toggle('guest-trial-wallet', guest);
  }
  // Read the language selector in the persistent topbar.
  const localeSelect = document.getElementById('shell-locale-select');
  // Wire the persistent locale selector without remounting games.
  wireLocaleSelect(localeSelect, () => { renderNav(); updateCurrentUserShell(); if (active === 'lobby') navigate('lobby'); });
  // Show the active brand name from the brand config so rebranding stays a one-file change.
  setStatusText('shell-brand-title', activeBrand.name);
  // Render the active brand mark glyph inside the brand badge.
  const brandMark = document.querySelector('.brand-mark');
  // Set the mark only when the static lockup element is present.
  if (brandMark) brandMark.textContent = activeBrand.mark;
  // Keep the compact subtitle aligned with the selected shell locale.
  setStatusText('shell-brand-subtitle', t('brand.subtitle', {}, 'shell'));
  // Localize the visible wallet balance caption.
  setStatusText('balance-label', t(isGuestSession() ? 'guest.balanceLabel' : 'wallet.balanceLabel', {}, 'shell'));
  // Localize the wallet popover field label.
  setStatusText('add-token-label', t('wallet.addTokens', {}, 'shell'));
  // Localize the wallet submit action.
  setStatusText('add-token-btn', t('wallet.add', {}, 'shell'));
  // Localize the wallet menu's accessible name.
  document.getElementById('wallet-menu-summary')?.setAttribute('aria-label', t('wallet.addTokens', {}, 'shell'));
  // Localize the language selector's accessible name.
  localeSelect?.setAttribute('aria-label', t('language.aria', {}, 'shell'));
  // Keep provider identity controls unavailable to disposable guests and current for persistent accounts.
  const accountMenu = document.getElementById('account-menu');
  // Hide the complete account-method surface for account-free guest principals.
  if (accountMenu) accountMenu.hidden = isGuestSession();
  // Refresh boolean-only provider link state without delaying wallet or route rendering.
  if (!isGuestSession()) void renderOAuthAccountControls();
  // Return the rendered token amount for test and toast flows.
  return amount;
}

// Report whether the current URL names the separately approved private invitation redemption surface. (INVITE-005)
function isInvitationRoute() {
  // Match only the canonical path; all other anonymous paths retain the normal private-beta login gate.
  return publicAuthRouteKind(location.pathname) === 'invitation';
}

// Report whether the current URL names the full-account enrollment surface.
function isSignupRoute() {
  // Match only the canonical signup path; all other anonymous paths retain the normal login gate.
  return publicAuthRouteKind(location.pathname) === 'signup';
}

// Report whether the current URL names the verified-email pending enrollment surface. (AUTH-018)
function isEmailVerificationRoute() {
  // Match only the canonical verification path so other anonymous routes retain their established gates.
  return publicAuthRouteKind(location.pathname) === 'verification';
}

// Report whether the current URL names the public password-recovery destination. (RESET-004)
function isPasswordResetRoute() {
  // Match only the canonical path so arbitrary anonymous URLs remain at the login gate.
  return publicAuthRouteKind(location.pathname) === 'reset';
}

// Render one exact public account destination for cold load, history, or warm native link arrival. (SEC-016)
function renderPublicAuthRoute() {
  // Classify the current path through the shared exact route allowlist.
  const route = publicAuthRouteKind(location.pathname);
  // Leave ordinary casino and login routes untouched when no public account gate owns the URL.
  if (!route) return false;
  // Advance navigation ownership before teardown so pending imports, mounts, and failures become stale synchronously.
  shellNavigationOwnership.invalidate();
  // Tear down an authenticated shell exactly once before a warm public link can replace its outlet.
  if (currentSession || active || latestState || gameDescriptors.length) clearAuthenticatedShellState({ invalidateNavigation: false });
  // Render each existing public gate without passing transient bearer material through arguments.
  if (route === 'invitation') renderInvitationGate(); else if (route === 'signup') void renderSignupGate(); else if (route === 'verification') renderEmailVerificationGate(); else renderPasswordResetGate();
  // Report that the public gate owns the route so authenticated navigation cannot overwrite it.
  return true;
}

// Consume a native link bearer from module memory or fall back to the browser URL path. (SEC-016)
function transientRouteBearer(path) {
  // Prefer the native runtime's one-shot reader so query credentials never enter WebView history.
  const nativeBearer = window.CasinoMobileDeepLink?.consumeBearer?.(path) || '';
  // Preserve the established browser route when no native bearer exists.
  return nativeBearer || new URL(location.href).searchParams.get('token') || '';
}

// Enter the authenticated casino shell after login and terms are complete.
async function enterAuthenticated(session) {
  // Dispose any prior session generation before adopting a login, reconnect, or guest identity.
  walletCelebrationLifecycle.unmount('session-replaced');
  // Store the normalized current user for shell rendering.
  currentSession = normalizeCurrentUser(session);
  // Branch to terms acceptance before showing the casino shell.
  if (currentSession.terms?.required) { renderTermsGate(currentSession); return; }
  // Read durable personal preferences before any route can emit sound or render a stale locale. (USER-009)
  try {
    // Load only the authenticated caller's additive v2 settings envelope.
    const preferenceData = await api('/api/v2/me/settings');
    // Read the server-owned settings under a safe default for older compatible deployments.
    const preferences = preferenceData.settings || {};
    // Apply the caller's durable sound preference before games can mount.
    setPersonalSoundEnabled(preferences.sound_enabled === true);
    // Override the active login/browser locale only after the caller explicitly saved a durable preference.
    if (preferences.updated_at && preferences.locale && preferences.locale !== getLocaleState().locale) await setLocale(preferences.locale, { persistLocal: false });
  // Preserve login availability if a compatible older server has no settings surface.
  } catch (_) {
    // Keep the default local sound and locale behavior for a missing optional preference read.
  }
  // Load Admin-owned persisted voice settings only when this authenticated identity may read them.
  if (currentSession.user?.role === 'admin') await loadVoiceSettings();
  // Reveal the casino chrome now that the browser session is authenticated.
  document.body.classList.remove('auth-locked');
  // Update the persistent wallet, logout, and locale controls without celebrating initial load.
  const initialBalance = updateCurrentUserShell();
  // Start optional reload-stable wellness reminders from this exact server session.
  await wellnessController.start(currentSession);
  // Schedule the server-authored warning only after the complete authenticated shell is visible.
  scheduleSessionWarning();
  // Bind one controller to the persistent wallet nodes and this exact authenticated session.
  walletCelebrationLifecycle.mount(initialBalance);
  // Load casino state for status rail and initial lobby counts.
  await refreshShellState();
  // Resolve a bookmarked, reloaded, or already-active route after the catalog is available.
  const initialRoute = active || routeFromLocation();
  // Render the restored route while replacing invalid or legacy location state.
  await navigate(initialRoute, { history: 'replace' });
}

// Refresh the current-user session and choose the correct first screen.
async function refreshCurrentSession() {
  // Let an exact public account route own cold load before an existing vault session can repaint it.
  if (renderPublicAuthRoute()) return false;
  // Start protected current-user loading so anonymous browsers see the login gate.
  try {
    // Read the planned v2 current-user endpoint.
    const session = await currentUser();
    // Enter the authenticated shell or terms step from the returned payload.
    await enterAuthenticated(session);
    // Confirm that authoritative session refresh succeeded for reconnect handling.
    return true;
  // Handle missing or expired sessions by showing the browser login gate.
  } catch (err) {
    // Preserve the existing shell and fail closed on offline, stale, malformed, throttled, or server errors.
    if (err?.code !== 'UNAUTHORIZED') throw err;
    // Clear the current session so no stale wallet can render.
    currentSession = null;
    // Render the exact account-free enrollment path, signup path, or the normal private-beta login gate.
    if (!renderPublicAuthRoute()) renderLoginGate();
    // Report the expired or absent session without exposing backend diagnostics.
    return false;
  }
}

// Update one status text node if that node exists in the current document.
function setStatusText(id, text) {
  // Read the target status element by id.
  const element = document.getElementById(id);
  // Update the text only when the shell outlet exists.
  if (element) element.textContent = text;
}

// Keep the bottom status rail synchronized with the latest API state.
function updateShellStatus(state, connected) {
  // Retain the latest actual connection result for locale-only rerenders.
  shellConnected = connected;
  // Resolve the app version string from API state or fallback text.
  const version = state?.version ? `v${state.version}` : t('status.unavailable', {}, 'shell');
  // Resolve privacy-safe recent presence instead of counting durable player records. (issue #570)
  const players = t('status.online', { count: Number.isInteger(state?.online_player_count) ? state.online_player_count : 0 }, 'shell');
  // Localize the persistent safety rail labels and details.
  setStatusText('status-safe-code', t('status.safeCode', {}, 'shell'));
  // Localize the play-token safety statement.
  setStatusText('status-safe-detail', t('status.safeDetail', {}, 'shell'));
  // Localize the ledger status label.
  setStatusText('status-ledger-code', t('status.ledgerCode', {}, 'shell'));
  // Localize the ledger-backed outcome statement.
  setStatusText('status-ledger-detail', t('status.ledgerDetail', {}, 'shell'));
  // Localize the application version label.
  setStatusText('status-app-code', t('status.appCode', {}, 'shell'));
  // Localize the player-count label.
  setStatusText('status-players-code', t('status.playersCode', {}, 'shell'));
  // Write the version into the persistent status rail.
  setStatusText('status-version', version);
  // Write the player count into the persistent status rail.
  setStatusText('status-players', players);
  // Write the connection state into the persistent status rail.
  setStatusText('connection-status', t(connected ? 'status.connected' : 'status.disconnected', {}, 'shell'));
  // Find the visual connection indicator for online/offline styling.
  const dot = document.getElementById('connection-dot');
  // Toggle the offline class without assuming the status rail is present.
  if (dot) dot.classList.toggle('offline', !connected);
}

// Fetch casino state for shell-level status without changing gameplay APIs.
async function refreshShellState(options = {}) {
  // Start protected API polling so the shell can mark itself disconnected on failure.
  try {
    // Request the additive compact shell projection while legacy callers retain the frozen complete response. (TEST-166)
    const state = await api('/api/v1/casino/state?projection=shell');
    // Cache the state for lobby rendering and later refreshes.
    latestState = state;
    // Rebuild frontend registration from the same public catalog used by backend registration.
    gameDescriptors = (state.games || []).map(game => descriptorFromCatalog(game));
    // Register every game-owned translation domain directly from the live catalog without loading unvisited routes.
    registerI18nDomains(gameDescriptors.map(game => game.i18nDomain));
    // Mark the shell connected and update status values.
    updateShellStatus(state, true);
    // Return state to callers that need initial render data.
    return state;
  // Handle state polling errors without breaking already-mounted games.
  } catch (err) {
    // Mark the shell disconnected when state cannot be read.
    updateShellStatus(null, false);
    // Log quiet polling errors so Admin can see intermittent state failures.
    if (options.quiet) await logClient('shell_state_error', { message: err.message });
    // Rethrow non-quiet initial-load failures so init can show a toast.
    if (!options.quiet) throw err;
    // Return null for quiet polling so setInterval never rejects.
    return null;
  }
}

// Rebuild session, wallet, catalog, and the active route before releasing actions after reconnect. (PWA-002)
async function refreshAfterReconnect() {
  // Preserve a warm native account route without probing and repainting an old vault session over it.
  if (renderPublicAuthRoute()) return { status: 'public-auth-route' };
  // Preserve the current or URL-owned route before session refresh rerenders the shell.
  const restoredRoute = active || routeFromLocation();
  // Revalidate the browser session before trusting any cached wallet or game state.
  const authenticated = await refreshCurrentSession();
  // Keep an expired session at the login boundary with no stale authenticated controls.
  if (!authenticated || !currentSession || currentSession.terms?.required) return { status: 'expired-session' };
  // enterAuthenticated already refreshed shell state and remounted the preserved route authoritatively.
  return { status: restoredRoute === 'lobby' ? 'online' : 'route-restored' };
}

// Start browser lifecycle wiring and publish the native readiness handshake.
void startApplication({
  clearAuthenticatedShellState,
  descriptorFromCatalog,
  documentRef: document,
  getActive: () => active,
  getCurrentSession: () => currentSession,
  getGameDescriptors: () => gameDescriptors,
  getLatestState: () => latestState,
  getShellConnected: () => shellConnected,
  isGuestSession,
  navigate,
  refreshAfterReconnect,
  refreshCurrentSession,
  refreshShellState,
  renderExpiredSessionGate,
  renderInitialRouteRestore,
  renderLoginGate,
  renderNav,
  renderPublicAuthRoute,
  revealActiveNav,
  routeFromLocation,
  setCurrentSession: session => { currentSession = session; },
  setGameDescriptors: descriptors => { gameDescriptors = descriptors; },
  updateCurrentUserShell,
  updateShellStatus,
  walletLifecycle: walletCelebrationLifecycle,
  wellnessController,
  windowRef: window,
}).then(() => {
  // Release native recovery only after authoritative startup completes.
  window.dispatchEvent(new CustomEvent('casino:shared-app-ready'));
}).catch(() => {
  // Signal bounded initialization failure without exposing state details.
  window.dispatchEvent(new CustomEvent('casino:shared-app-error'));
});
