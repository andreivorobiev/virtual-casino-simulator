// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import required dependency so this module can call the frozen API envelope safely.
import { acceptTerms, addUserTokens, api, currentUser, departGuestTrial, endGuestTrial, guestTrial, holdTransientBearer, logClient, login, logout, oauthLinks, oauthProviders, publicAuthRouteKind, redeemInvitation, startOAuth, unlinkOAuth } from './core/api.js';
// Import required dependency so this module can render shared wallet and premium UI helpers.
import { renderTokenBalance, toast, tokens, safe, renderPremiumTag, installStableRouteRenders, auditLayoutContainment, createNavigationOwnership, mountOwnedRoute, awaitOwnedRouteEffect } from './core/ui.js';
// Import required dependency so the shell can preserve locale across auth and route changes.
import { getLocaleState, initI18n, onLocaleChange, registerI18nDomains, setLocale, t } from './core/i18n.js';
// Import the offline-safe shell controller for exact-version updates and authoritative reconnects. (PWA-001, PWA-002)
import { initPwa } from './core/pwa.js';
// Import the active brand and its runtime token applier so one config skins the app.
import { activeBrand, applyBrand } from './core/brand.js';
// Import the session-owned wallet celebration controller without adding game or API authority. (UX-023)
import { createWalletCelebration, createWalletCelebrationLifecycle } from './core/celebrate.js';
// Import required dependency so this module can preload global voice settings before games mount.
import { loadVoiceSettings, setPersonalSoundEnabled } from './core/voice.js';
// Import the registered-user problem-report dialog without adding feedback code to the shared shell.
import { bindFeedbackDialog, localizeFeedback, syncFeedbackReporter } from './core/feedback.js';
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

// Store frontend descriptors loaded from the same API catalog that registers backend games.
let gameDescriptors = [];
// Store loaded game modules so repeated route changes do not re-import the same module.
const loadedGames = new Map();
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
// Invalidate asynchronous logged-out capability reads whenever locale or route rendering replaces the login gate. (UX-028)
let loginGateGeneration = 0;
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
// Track the active game-rail observer so navigation never leaves duplicate mutation listeners.
let gameRailObserver = null;
// Read one fixed provider-completion marker and immediately remove it from browser history.
const oauthCompletion = readOAuthCompletion();
// Own one document-lifetime wellness controller while authenticated sessions replace its timer generation.
const wellnessController = createWellnessController({ apiClient: api, documentRef: document, windowRef: window, translate: (key, values) => t(key, values, 'shell'), formatTokens: tokens });
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

// Relay game/autoplay toast events through the shell-level toast outlet.
window.addEventListener('casino-toast', event => toast(event.detail?.message || t('autoplay.stopped', {}, 'shell')));
// Keep the shell's private session cache synchronized when game helpers refresh current-user state.
window.addEventListener('casino-current-user', event => {
  // Normalize the exact current-user payload published by the shared wallet helper.
  const nextSession = normalizeCurrentUser(event.detail);
  // Adopt the refreshed session before any queued wallet presentation work can run.
  currentSession = nextSession;
  // Run after refreshBalance performs its single synchronous authoritative wallet render.
  queueMicrotask(() => {
    // Ignore a stale event after logout, another refresh, or authenticated-session replacement.
    if (currentSession !== nextSession) return;
    // Decorate only the exact latest server-settled amount without writing wallet text again.
    walletCelebrationLifecycle.update(currentTokenBalance(nextSession));
  });
});
// Report top-level browser errors through the client log API for admin visibility.
window.addEventListener('error', event => logClient('window_error', { message: event.message, filename: event.filename, lineno: event.lineno, colno: event.colno }));
// Report unhandled promise rejections through the client log API for admin visibility.
window.addEventListener('unhandledrejection', event => logClient('unhandled_rejection', { reason: String(event.reason?.message || event.reason) }));
// Mark a guest page departure so lifecycle cleanup stays observable without ending same-context reloads.
window.addEventListener('pagehide', () => { if (isGuestSession()) void departGuestTrial().catch(() => {}); });
// Reset stale authenticated chrome only while an authenticated shell is mounted, leaving public enrollment pages intact.
window.addEventListener('casino-session-expired', () => { if (currentSession) renderExpiredSessionGate(); });

// Normalize the draft v2 current-user payloads without committing to backend internals.
function normalizeCurrentUser(payload) {
  // Store data so standard API envelopes and direct payloads both work.
  const data = payload?.current_user || payload || {};
  // Store user so profile fields can be read from one place.
  const user = data.user || {};
  // Store player so token fields can be read from one place.
  const player = data.player || {};
  // Store terms so terms-required flags can be read from one place.
  const terms = data.terms || user.terms || {};
  // Store termsRequired so early backend payload drafts remain compatible.
  const termsRequired = typeof terms.required === 'boolean' ? terms.required : user.terms_required === true || data.terms_required === true || terms.accepted === false;
  // Return a normalized current-user session object for shell rendering.
  return { ...data, user, player, terms: { ...terms, required: termsRequired } };
}

// Resolve the same current-user play-token field precedence used by the shared wallet renderer.
function currentTokenBalance(session) {
  // Read the normalized player payload when the current contract supplies one.
  const player = session?.player || {};
  // Read the normalized user payload for compatible early contract shapes.
  const user = session?.user || {};
  // Resolve the established compatible token fields without reading rendered DOM text.
  const value = player.token_balance ?? player.tokens ?? user.token_balance ?? user.tokens ?? session?.token_balance ?? session?.tokens?.balance ?? 0;
  // Return the numeric value consumed by renderTokenBalance and the decoration controller.
  return Number(value || 0);
}

// Convert one public API catalog row into the shell's route and presentation descriptor.
function descriptorFromCatalog(game) {
  // Read locale-owned metadata from the independently owned game descriptor.
  const localized = game.translations?.[getLocaleState().locale] || {};
  // Read nested lobby metadata while tolerating additive future fields.
  const lobby = game.lobby || {};
  // Return the exact shape consumed by navigation, search, cards, and lazy imports.
  return { id: game.id, route: game.route || `/games/${game.id}`, label: localized.label || game.label, category: game.category, categories: game.categories || [game.category], path: game.frontend?.module, exportName: game.frontend?.export, readyTestId: game.frontend?.ready_testid, i18nDomain: game.frontend?.i18n_domain, i18nProbe: game.frontend?.i18n_probe, featured: lobby.featured === true, wide: lobby.wide === true, artClass: lobby.art_class || '', symbol: lobby.symbol || '', kicker: localized.kicker || lobby.kicker || game.category, description: localized.description || lobby.description || '', tags: localized.tags || lobby.tags || [] };
}

// Resolve a human-readable game title for status panels, falling back to the raw route. (issue #254)
function routeLabel(route) {
  // Return the catalog display label when the route names a known game, else the raw route slug.
  return gameDescriptors.find(game => game.id === route)?.label || route;
}

// Resolve a route label before the casino catalog has finished hydrating during startup. (PWA-002)
function routeFallbackLabel(route) {
  // Prefer the live catalog label once casino state has populated game descriptors.
  const catalogLabel = routeLabel(route);
  // Return the catalog label when it has resolved beyond the raw route id.
  if (catalogLabel !== route) return catalogLabel;
  // Build the static shell resource key used by reviewed core game labels.
  const labelKey = `games.${route}.label`;
  // Resolve the already-loaded shell translation domain without waiting for casino state.
  const resourceLabel = t(labelKey, {}, 'shell');
  // Return the localized static label when a resource exists for this game route.
  if (resourceLabel !== labelKey) return resourceLabel;
  // Convert future route slugs into readable fallback words instead of showing a raw identifier.
  return route.split(/[_-]+/).filter(Boolean).map(part => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`).join(' ') || route;
}

// Resolve the route represented by the current browser location for reload and history restoration.
function routeFromLocation() {
  // Restore the distinct authenticated My Settings destination independently from games and Admin.
  if (location.pathname.replace(/\/$/, '') === '/settings') return 'settings';
  // Match canonical reloadable game paths without accepting nested or ambiguous segments.
  const match = location.pathname.match(/^\/games\/([^/]+)\/?$/);
  // Decode the matched id so route comparison uses catalog identifiers.
  if (match) return decodeURIComponent(match[1]);
  // Preserve a compatible hash deep link for older bookmarks when it names a catalog game.
  const hashRoute = location.hash.replace(/^#\/?/, '');
  // Return the hash game only when the loaded catalog recognizes it.
  if (gameDescriptors.some(game => game.id === hashRoute)) return hashRoute;
  // Treat every non-game static path as the lobby shell route.
  return 'lobby';
}

// Show a real game-route restoration surface before slow current-user and casino-state calls complete. (issue #317, PWA-002)
function renderInitialRouteRestore() {
  // Read the browser-owned route before authenticated state can hydrate the game catalog.
  const restoredRoute = routeFromLocation();
  // Leave lobby and the separate invitation enrollment surface on their existing startup paths.
  if (restoredRoute === 'lobby' || isInvitationRoute()) return;
  // Read the route outlet that can otherwise sit visually blank during session revalidation.
  const view = document.getElementById('view');
  // Stop when the shell outlet is unavailable during a malformed static load.
  if (!view) return;
  // Resolve a player-facing game label without depending on the delayed casino-state catalog.
  const gameLabel = routeFallbackLabel(restoredRoute);
  // Keep the authenticated route outlet out of the lobby-only flex containment contract.
  document.body.classList.remove('lobby-active');
  // Apply the same game-screen class used by authoritative navigation.
  view.className = 'screen game-screen';
  // Remove lobby-specific testing identity before rendering the restoration placeholder.
  view.removeAttribute('data-testid');
  // Include the bounded game outlet in keyboard flow while the route is restoring.
  view.tabIndex = 0;
  // Expose the startup placeholder as the same named game region used after navigation.
  view.setAttribute('role', 'region');
  // Name the region consistently with mounted game routes.
  view.setAttribute('aria-label', safe(t('nav.gamesArea', {}, 'shell') || 'Game area'));
  // Render immediate, localized progress instead of a blank route while trial/session state hydrates.
  view.innerHTML = `<div class="panel loading-panel" data-testid="route-restore-loading"><p class="eyebrow">${safe(t('routeRestore.eyebrow', {}, 'shell'))}</p><h2>${safe(t('routeRestore.title', { game: gameLabel }, 'shell'))}</h2><p class="status">${safe(t('routeRestore.copy', {}, 'shell'))}</p></div>`;
}

// Consume only fixed OAuth completion markers without retaining callback query material. (OAUTH-010)
function readOAuthCompletion() {
  // Parse the current same-origin URL through the browser URL implementation.
  const url = new URL(location.href);
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
  history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
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

// Synchronize browser history with one resolved catalog route.
function updateRouteHistory(route, mode = 'push') {
  // Resolve the canonical path from the dedicated settings route, catalog metadata, or lobby root.
  const path = route === 'settings' ? '/settings' : route === 'lobby' ? '/' : gameDescriptors.find(game => game.id === route)?.route || '/';
  // Preserve locale and test query parameters while removing legacy route hashes.
  const url = new URL(location.href);
  // Apply the canonical route path to the current URL.
  url.pathname = path;
  // Clear only the legacy route hash after restoration.
  url.hash = '';
  // Avoid duplicate history entries when navigation resolves to the current URL.
  if (location.pathname === url.pathname && location.hash === url.hash) return;
  // Replace initial or invalid routes and push normal user navigation.
  history[mode === 'replace' ? 'replaceState' : 'pushState']({ route }, '', `${url.pathname}${url.search}`);
}

// Render the locale selector options from the loaded manifest.
function localeOptionsHtml() {
  // Store locales so the selector follows the manifest rather than hard-coded values.
  const locales = getLocaleState().locales || [];
  // Return option markup for every enabled UI locale.
  return locales.map(locale => `<option value="${safe(locale.id)}">${safe(locale.nativeLabel || locale.label || locale.id)}</option>`).join('');
}

// Wire a locale selector while preserving the current auth or route state.
function wireLocaleSelect(select, afterChange) {
  // Stop when the requested selector is not present in the current screen.
  if (!select) return;
  // Fill the selector with manifest locales before setting the active option.
  select.innerHTML = localeOptionsHtml();
  // Select the active locale so refreshes preserve the user's choice.
  select.value = getLocaleState().locale;
  // Switch language in place without resetting the active route or auth step.
  select.onchange = async () => { await setLocale(select.value); afterChange?.(); };
}

// Make intentional game-rail scrolling discoverable to keyboard and assistive-technology users.
function prepareGameScrollRegions(view) {
  // Find the shared control and data rails rendered by the active game module.
  view.querySelectorAll('.control-rail, .details-drawer').forEach(region => {
    // Include the intentional scroll region in the natural keyboard tab order.
    region.tabIndex = 0;
    // Identify each rail as a navigable document region.
    region.setAttribute('role', 'region');
    // Read the first visible heading so the region has a useful accessible name.
    const heading = region.querySelector('h1, h2, h3');
    // Label the region from its own content while retaining a safe fallback.
    region.setAttribute('aria-label', heading?.textContent?.trim() || 'Game panel');
  });
}

// Preserve scroll-region semantics when a game replaces its render tree during phase updates.
function observeGameScrollRegions(view) {
  // Disconnect the previous route observer before watching the newly mounted game.
  gameRailObserver?.disconnect();
  // Apply semantics immediately to the first completed game render.
  prepareGameScrollRegions(view);
  // Reapply semantics after game-owned rerenders replace rail elements.
  gameRailObserver = new MutationObserver(() => prepareGameScrollRegions(view));
  // Watch structural replacements without observing the attributes this helper sets.
  gameRailObserver.observe(view, { childList: true, subtree: true });
}

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
  gameRailObserver?.disconnect();
  // Unmount the active game when its lifecycle hook exists so stale rerenders cannot survive sign-out.
  if (active && loadedGames.has(active)) loadedGames.get(active).unmount?.();
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

// Render a logged-out browser gate before any casino route can mount.
function renderLoginGate(message = '') {
  // Clear the public current-user hook while the browser is logged out.
  window.CasinoCurrentUser = null;
  // Hide the registered-user reporting affordance for logged-out and guest entry screens.
  syncFeedbackReporter(null);
  // Leave lobby-only flex containment before the public authentication screen replaces the route outlet.
  document.body.classList.remove('lobby-active');
  // Mark the document so chrome and game routes stay hidden while logged out.
  document.body.classList.add('auth-locked');
  // Read the main route outlet reserved by index.html.
  const view = document.getElementById('view');
  // Remove authenticated lobby-region semantics before exposing the public login gate.
  view.removeAttribute('tabindex'); view.removeAttribute('role'); view.removeAttribute('aria-label'); view.removeAttribute('data-testid');
  // Apply the auth screen class contract for login and terms flows.
  view.className = 'screen auth-screen';
  // Clear guest-only shell sizing after explicit end, expiry, or browser-proof loss.
  document.body.classList.remove('guest-trial-active');
  // Resolve explicit caller feedback before a fixed provider completion acknowledgement.
  const authMessage = message || oauthCompletionCopy();
  // Claim one generation before asynchronous policy reads can populate this exact login render.
  const generation = ++loginGateGeneration;
  // Render one guest-first decision hierarchy with a single shared terms row and one polite status owner. (UX-028)
  view.innerHTML = `<section class="auth-panel auth-entry" data-testid="login-gate"><header class="auth-entry-header"><div><h1>${safe(t('brand.title', {}, 'shell'))}</h1><p id="auth-legal-line" class="auth-legal-line">${safe(t('auth.legalLine', {}, 'shell'))}</p></div><label class="auth-locale-switch"><span>${safe(t('auth.language', {}, 'shell'))}</span><select id="auth-locale-select" data-testid="auth-locale-select" aria-label="${safe(t('language.aria', {}, 'shell'))}"></select></label></header><div id="auth-guest-slot" class="auth-primary-slot" data-testid="auth-guest-slot" aria-busy="true"><p class="auth-capability-loading">${safe(t('status.loading', {}, 'shell'))}</p></div><label class="check-row auth-terms-row"><input id="login-terms-check" data-testid="login-terms-check" type="checkbox"><span>${safe(t('auth.termsCheck', {}, 'shell'))}</span></label><p id="auth-message" class="auth-message" data-testid="oauth-callback-message" role="status" aria-live="polite" aria-atomic="true">${safe(authMessage)}</p><section class="auth-signin" aria-labelledby="auth-signin-heading"><h2 id="auth-signin-heading">${safe(t('auth.signinHeading', {}, 'shell'))}</h2><form id="login-form" class="auth-form auth-signin-form" novalidate><label>${safe(t('auth.email', {}, 'shell'))}<input id="login-email" data-testid="login-email" type="email" autocomplete="username" required></label><label>${safe(t('auth.password', {}, 'shell'))}<input id="login-password" data-testid="login-password" type="password" autocomplete="current-password" required></label><button class="secondary auth-signin-submit" data-testid="login-submit" type="submit">${safe(t('auth.submit', {}, 'shell'))}</button><a class="auth-reset-link" href="/account/reset" data-testid="password-reset-entry">${safe(t('recovery.forgot', {}, 'shell'))}</a></form></section><div id="auth-tertiary" class="auth-tertiary"><div id="auth-account-slot"></div><div id="auth-provider-slot"></div></div></section>`;
  // Wire the auth-screen locale selector and rerender the gate after switching.
  wireLocaleSelect(document.getElementById('auth-locale-select'), () => renderLoginGate(message));
  // Wire form submission through the v2 auth login endpoint.
  document.getElementById('login-form').onsubmit = handleLoginSubmit;
  // Delegate disclosure activation from the stable gate so async slot replacement cannot detach behavior.
  document.querySelector('[data-testid="login-gate"]').onclick = event => { const button = event.target.closest('[data-auth-disclosure]'); if (button) toggleAuthDisclosure(button); };
  // Clear only the shared terms error after explicit acceptance without disturbing API or session feedback.
  document.getElementById('login-terms-check').onchange = event => { if (event.currentTarget.checked && document.getElementById('auth-message')?.dataset.validation === 'terms') setAuthStatus(''); };
  // Resolve guest and enrollment actions independently so provider latency cannot delay the primary path. (GUEST-001)
  void renderLoginPolicyActions(generation);
  // Resolve provider availability into actions that exist only when they can be used. (OAUTH-007)
  void renderLoginProviderActions(generation);
}

// Replace the shared Auth status through the only live region on the logged-out decision surface. (UX-028)
function setAuthStatus(copy, kind = '') {
  // Resolve the single document-owned outlet from the active login generation.
  const outlet = document.getElementById('auth-message');
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
  const checkbox = document.getElementById('login-terms-check');
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
  const target = document.getElementById(button.getAttribute('aria-controls'));
  // Stop without mutation when malformed markup cannot resolve the owned disclosure.
  if (!target) return;
  // Flip the current semantic expansion state from the button's exact boolean string.
  const expanded = button.getAttribute('aria-expanded') !== 'true';
  // Publish the new state for keyboard and assistive technology users.
  button.setAttribute('aria-expanded', String(expanded));
  // Keep the disclosure out of layout and reading order until requested.
  target.hidden = !expanded;
}

// Render guest and enrollment actions only after the public policy authorizes their exact state. (GUEST-001, UX-028)
async function renderLoginPolicyActions(generation) {
  // Start protected capability loading so a failed policy never creates an unauthorized action.
  try {
    // Read only boolean enrollment capabilities from the public no-state endpoint.
    const policy = await api('/api/v2/auth/enrollment-policy');
    // Ignore a completed read when locale, route, or session entry replaced its owning generation.
    if (generation !== loginGateGeneration || !document.querySelector('[data-testid="login-gate"]')) return;
    // Resolve the dedicated primary slot after ownership is revalidated.
    const guestSlot = document.getElementById('auth-guest-slot');
    // Render the real guest action only when the server advertises exact availability.
    guestSlot.innerHTML = policy.guest_trials_enabled === true ? `<button id="guest-trial-button" class="primary" data-testid="guest-trial-button" type="button">${safe(t('auth.guestCta', {}, 'shell'))}</button><p class="auth-guest-summary" data-testid="guest-trial-copy">${safe(t('auth.guestSummary', {}, 'shell'))}</p><button class="auth-disclosure-button" data-testid="guest-disclosure-toggle" data-auth-disclosure type="button" aria-expanded="false" aria-controls="guest-trial-details">${safe(t('auth.guestDetails', {}, 'shell'))}</button><p id="guest-trial-details" class="auth-disclosure-copy" data-testid="guest-trial-details" hidden>${safe(t('auth.guestInfo', {}, 'shell'))}</p>` : `<span class="auth-chip" data-testid="guest-trial-unavailable">${safe(t('auth.guestUnavailable', {}, 'shell'))}</span>`;
    // Mark the primary slot settled after exact policy-owned markup replaces the loading placeholder.
    guestSlot.setAttribute('aria-busy', 'false');
    // Wire guest creation only when the policy rendered the actionable control.
    document.getElementById('guest-trial-button')?.addEventListener('click', handleGuestTrial);
    // Resolve the separate tertiary account slot without mixing it with provider availability.
    const accountSlot = document.getElementById('auth-account-slot');
    // Render signup only when authorized; otherwise render an explanatory invite-only disclosure chip.
    accountSlot.innerHTML = policy.signup_enabled === true ? `<a class="auth-tertiary-link" href="/enroll/signup" data-testid="signup-entry-link">${safe(t('signup.cta', {}, 'shell'))}</a>` : `<button class="auth-chip auth-chip-button" data-testid="signup-invite-only" data-auth-disclosure type="button" aria-expanded="false" aria-controls="signup-invite-only-copy">${safe(t('signup.inviteOnly', {}, 'shell'))}</button><p id="signup-invite-only-copy" class="auth-disclosure-copy" data-testid="signup-invite-only-copy" hidden>${safe(t('signup.entryCopy', {}, 'shell'))}</p>`;
  // Keep a failed capability request fail-closed while preserving ordinary password sign-in.
  } catch (_) {
    // Ignore stale failure completion after a replacement login generation owns the document.
    if (generation !== loginGateGeneration) return;
    // Resolve the route-owned slot and suppress a late failure after navigation replaced the login document.
    const guestSlot = document.getElementById('auth-guest-slot');
    // Leave the replacement route untouched when the original login slot no longer exists.
    if (!guestSlot) return;
    // Replace the primary placeholder with noninteractive, localized fail-closed copy.
    guestSlot.innerHTML = `<span class="auth-chip" data-testid="auth-capability-unavailable">${safe(t('auth.capabilityUnavailable', {}, 'shell'))}</span>`;
    // Mark the primary capability slot complete even though no mutation action is available.
    guestSlot.setAttribute('aria-busy', 'false');
    // Publish policy failure only when more important caller/session feedback does not already exist.
    if (!document.getElementById('auth-message')?.textContent) setAuthStatus(t('auth.capabilityUnavailable', {}, 'shell'));
  }
}

// Render only independently available providers and omit the complete provider block otherwise. (OAUTH-007, UX-028)
async function renderLoginProviderActions(generation) {
  // Start protected availability loading so local-password and guest entry remain usable on failure.
  try {
    // Fetch only fixed provider ids and boolean availability.
    const result = await oauthProviders();
    // Select exact provider identifiers whose complete runtime and independent network gate are ready.
    const available = new Set((result.providers || []).filter(item => ['google', 'facebook'].includes(item.provider) && item.available === true).map(item => item.provider));
    // Ignore a completed read when locale, route, or session entry replaced its owning generation.
    if (generation !== loginGateGeneration || !document.querySelector('[data-testid="login-gate"]')) return;
    // Resolve the provider-only tertiary slot after exact generation ownership is confirmed.
    const providerSlot = document.getElementById('auth-provider-slot');
    // Ignore route replacement that removed the provider slot after the generation check.
    if (!providerSlot) return;
    // Omit the complete provider region when no provider is actionable.
    providerSlot.innerHTML = available.size ? `<section class="auth-provider-actions" data-testid="oauth-providers-available" aria-label="${safe(t('auth.oauthDivider', {}, 'shell'))}">${['google', 'facebook'].filter(provider => available.has(provider)).map(provider => `<button class="oauth-provider-button" data-testid="oauth-${safe(provider)}" type="button">${safe(t(`auth.oauth${provider === 'google' ? 'Google' : 'Facebook'}`, {}, 'shell'))}</button>`).join('')}</section>` : '';
    // Wire only controls that exist after the server reported that provider available.
    for (const provider of available) document.querySelector(`[data-testid="oauth-${provider}"]`)?.addEventListener('click', () => beginOAuth(provider, 'signin'));
  // Omit provider actions and use the single status owner on availability failure.
  } catch (_) {
    // Ignore stale failure completion after a replacement login generation owns the document.
    if (generation !== loginGateGeneration) return;
    // Resolve the route-owned provider slot and suppress late failures after navigation.
    const providerSlot = document.getElementById('auth-provider-slot');
    // Leave replacement route markup untouched when the original slot no longer exists.
    if (!providerSlot) return;
    // Keep the provider slot action-free while exposing a stable test state outside live semantics.
    providerSlot.innerHTML = '<span data-testid="oauth-providers-status-error" hidden></span>';
    // Publish generic localized provider feedback only when caller/session feedback is not already visible.
    if (!document.getElementById('auth-message')?.textContent) setAuthStatus(t('auth.oauthStatusError', {}, 'shell'));
  }
}

// Request a one-time authorization URL and navigate without logging or persisting it. (OAUTH-008)
async function beginOAuth(provider, action) {
  // Read the active auth/account message outlet for bounded errors.
  const message = action === 'signin' ? document.getElementById('auth-message') : (action === 'signup' ? document.getElementById('signup-message') : document.getElementById('oauth-account-message'));
  // Start protected flow creation so no provider navigation occurs after an API failure.
  try {
    // Read the explicit linking checkbox only for authenticated account linking.
    const confirmation = document.getElementById('oauth-link-confirm');
    // Stop linking until the canonical user explicitly confirms this action.
    if (action === 'link' && !confirmation?.checked) throw new Error(t('auth.oauthConfirmRequired', {}, 'shell'));
    // Require every social-enrollment acknowledgement before provider navigation.
    if (action === 'signup' && (!document.getElementById('signup-terms')?.checked || !document.getElementById('signup-privacy')?.checked || !document.getElementById('signup-play-token')?.checked)) throw new Error(t('signup.consentRequired', {}, 'shell'));
    // Build the explicit signup intent without email, account, role, or wallet targets.
    const signupIntent = action === 'signup' ? { terms_version: 'private-beta-1', accepted_terms: true, accepted_privacy: true, accepted_fake_money: true, locale: document.getElementById('signup-locale')?.value || 'en-US' } : {};
    // Request a short-lived browser-bound flow with a same-origin destination.
    const result = await startOAuth(provider, { action, return_to: '/', ...(action === 'link' ? { confirm_link: true } : {}), ...signupIntent });
    // Navigate directly without copying the sensitive URL into logs or application storage.
    location.assign(result.authorization_url);
  // Show only the server's safe public message in the current auth surface.
  } catch (error) {
    // Keep the page usable and avoid reflecting provider response content.
    if (message) message.textContent = error.message;
  }
}

// Render authenticated provider linking with explicit confirmation and safe unlink. (OAUTH-009, OAUTH-010)
async function renderOAuthAccountControls() {
  // Read the persistent popover reserved by the authenticated shell.
  const popover = document.getElementById('oauth-account-popover');
  // Stop before login, for a guest, or while another auth gate owns the page.
  if (!popover || !currentSession || isGuestSession()) return;
  // Stamp a bounded loading state for assistive and automated lifecycle evidence.
  popover.dataset.oauthState = 'loading';
  // Render a localized loading state without provider configuration details.
  popover.innerHTML = `<h2>${safe(t('auth.oauthAccountTitle', {}, 'shell'))}</h2><p class="oauth-provider-copy">${safe(t('status.loading', {}, 'shell'))}</p>`;
  // Start protected link-status loading so provider errors cannot affect gameplay.
  try {
    // Read boolean availability and ownership for the current canonical user.
    const result = await oauthLinks();
    // Mark the boolean-only linked mix without exposing provider subjects or user ids.
    popover.dataset.oauthState = (result.providers || []).some(item => item.linked === true) ? 'linked' : 'unlinked';
    // Render one fixed provider row with the appropriate link or unlink action.
    const rows = (result.providers || []).filter(item => ['google', 'facebook'].includes(item.provider)).map(item => `<div class="oauth-account-row" data-testid="oauth-link-${safe(item.provider)}"><span>${safe(item.provider === 'google' ? t('auth.oauthGoogleName', {}, 'shell') : t('auth.oauthFacebookName', {}, 'shell'))}</span><button type="button" data-oauth-account-provider="${safe(item.provider)}" data-oauth-account-action="${item.linked ? 'unlink' : 'link'}" ${!item.linked && !item.available ? 'disabled aria-disabled="true"' : ''}>${safe(item.linked ? t('auth.oauthUnlink', {}, 'shell') : t('auth.oauthLink', {}, 'shell'))}</button></div>`).join('');
    // Require explicit consent adjacent to the provider actions.
    popover.innerHTML = `<h2>${safe(t('auth.oauthAccountTitle', {}, 'shell'))}</h2><button type="button" class="secondary" data-testid="my-settings-entry">${safe(t('settings.title', {}, 'shell'))}</button><p class="oauth-provider-copy">${safe(t('auth.oauthAccountCopy', {}, 'shell'))}</p>${oauthCompletion ? `<p class="auth-message" data-testid="oauth-callback-message" role="status">${safe(oauthCompletionCopy())}</p>` : ''}<label class="check-row oauth-link-confirm"><input id="oauth-link-confirm" type="checkbox" data-testid="oauth-link-confirm"><span>${safe(t('auth.oauthLinkConfirm', {}, 'shell'))}</span></label>${rows}<p id="oauth-account-message" class="auth-message" role="status"></p>`;
    // Keep personal settings routing separate from provider-link actions and Admin Console.
    popover.querySelector('[data-testid="my-settings-entry"]').onclick = () => { document.getElementById('account-menu')?.removeAttribute('open'); void navigate('settings'); };
    // Wire each rendered provider action through its explicit operation.
    popover.querySelectorAll('[data-oauth-account-provider]').forEach(button => {
      // Handle link navigation or a separately confirmed unlink transaction.
      button.onclick = async () => {
        // Read the bounded action and provider from server-derived fixed rows.
        const provider = button.dataset.oauthAccountProvider;
        // Start a confirmed provider navigation for an unlinked account.
        if (button.dataset.oauthAccountAction === 'link') return beginOAuth(provider, 'link');
        // Require a browser confirmation before the destructive unlink request.
        if (!window.confirm(t('auth.oauthUnlinkConfirm', {}, 'shell'))) return;
        // Start protected unlink handling so a failed request stays local to the popover.
        try {
          // Remove only this provider's current-user link.
          await unlinkOAuth(provider);
          // Refresh boolean provider rows after a successful unlink.
          await renderOAuthAccountControls();
        // Keep the current account controls usable after a safe server failure.
        } catch (_) {
          // Publish one generic localized message without provider response details.
          const status = document.getElementById('oauth-account-message');
          // Update only the still-mounted account message outlet.
          if (status) status.textContent = t('auth.oauthStatusError', {}, 'shell');
        }
      };
    });
  // Replace the popover with a generic status failure while leaving logout and gameplay usable.
  } catch (_) {
    // Stamp one generic failure state without transport or provider detail.
    popover.dataset.oauthState = 'status-error';
    // Publish no provider configuration or request details.
    popover.innerHTML = `<h2>${safe(t('auth.oauthAccountTitle', {}, 'shell'))}</h2><p class="oauth-provider-copy">${safe(t('auth.oauthStatusError', {}, 'shell'))}</p>`;
  }
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

// Submit the login form to the backend-owned auth endpoint.
async function handleLoginSubmit(event) {
  // Prevent the browser from reloading during the auth flow.
  event.preventDefault();
  // Enforce shared terms before native credential validation so both entry paths focus the same control.
  if (!requireLoginTerms()) return;
  // Preserve native email/password validity after the shared terms decision has passed.
  if (!event.currentTarget.reportValidity()) return;
  // Read the shared message outlet for validation and API errors.
  const message = document.getElementById('auth-message');
  // Start protected login logic so validation errors stay inside the auth panel.
  try {
    // Clear stale validation or session copy before the exact sign-in request begins.
    setAuthStatus('');
    // Read the email from the browser-visible login field.
    const email = document.getElementById('login-email').value.trim();
    // Read the password from the browser-visible login field.
    const password = document.getElementById('login-password').value;
    // Read the active locale so backend sessions can preserve user language.
    const locale = getLocaleState().locale;
    // Call the planned v2 auth endpoint without changing backend internals.
    const session = await login({ email, password, locale, terms_acknowledged: true });
    // Enter the authenticated shell or terms step from the returned payload.
    await enterAuthenticated(session);
  // Handle failed login attempts with local auth-panel feedback.
  } catch (err) {
    // Render the API error without leaving the login gate.
    if (message) message.textContent = err.message;
  }
}

// Start one account-free disposable guest trial from the login surface. (issue #317)
async function handleGuestTrial() {
  // Read the shared message outlet for API errors.
  const message = document.getElementById('auth-message');
  // Start protected guest logic so any rejection stays inside the auth panel.
  try {
    // Enforce the exact same acknowledgement, copy, and focus behavior as password sign-in.
    if (!requireLoginTerms()) return;
    // Clear stale validation or session copy before the exact guest request begins.
    setAuthStatus('');
    // Create the isolated disposable guest session with exact versioned consent metadata.
    const session = await guestTrial({ accepted: true, terms_version: 'private-beta-1', locale: getLocaleState().locale, device: innerWidth < 600 ? 'mobile' : innerWidth < 1100 ? 'tablet' : 'desktop' });
    // Enter the authenticated shell using the same payload shape as a registered login.
    await enterAuthenticated(session);
  // Handle a disabled or failed guest entry with local auth-panel feedback.
  } catch (err) {
    // Map capacity and rate boundaries to concise product copy without exposing raw server codes.
    const copy = err.status === 403 ? t('auth.guestCapacityFull', {}, 'shell') : err.status === 429 ? t('auth.guestRateLimited', {}, 'shell') : err.message;
    // Render the localized failure through the same stable region used by every auth outcome.
    if (message) setAuthStatus(copy);
  }
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

// Load a game module lazily while preserving one module boundary per game.
async function loadGame(desc) {
  // Return a cached module export when this route has already been loaded.
  if (loadedGames.has(desc.id)) return loadedGames.get(desc.id);
  // Start protected import logic so load failures are captured in client logs.
  try {
    // Import the owned game frontend module by its documented route path.
    const mod = await import(desc.path);
    // Read the known game class export from the module namespace.
    const game = mod[desc.exportName];
    // Cache the class so later navigations can mount without importing again.
    loadedGames.set(desc.id, game);
    // Return the game class to the navigation flow.
    return game;
  // Handle dynamic import failures with diagnostics for Admin telemetry.
  } catch (err) {
    // Record the module load error with route context.
    await logClient('game_module_load_error', { game: desc.id, message: err.message, stack: err.stack });
    // Re-throw so navigation can render its friendly failure panel.
    throw err;
  }
}

// Center the active catalog route inside the current navigation viewport.
function revealActiveNav() {
  // Read the navigation outlet that index.html reserves for route buttons.
  const nav = document.getElementById('main-nav');
  // Stop when authentication has not yet exposed the shared navigation.
  if (!nav) return;
  // Read the active catalog route after the navigation layout is measurable.
  const activeItem = nav.querySelector('.nav-item.active');
  // Stop when the current surface has no active game route to reveal.
  if (!activeItem) return;
  // Measure rendered coordinates so topbar columns and localized widths cannot skew offset-based centering.
  const navBounds = nav.getBoundingClientRect();
  // Measure the active route in the same viewport coordinate system as its navigation container.
  const itemBounds = activeItem.getBoundingClientRect();
  // Center the active route by applying its rendered displacement to the current horizontal scroll position.
  nav.scrollLeft += itemBounds.left - navBounds.left - ((navBounds.width - itemBounds.width) / 2);
}

// Render the premium top navigation from the route registry.
function renderNav() {
  // Read the navigation outlet that index.html reserves for route buttons.
  const nav = document.getElementById('main-nav');
  // Build the lobby button with the active shell class when selected.
  const items = [`<button data-route="lobby" class="nav-item ${active === 'lobby' ? 'active' : ''}" data-testid="nav-lobby"><span class="nav-icon" aria-hidden="true">&#8962;</span>${safe(t('nav.lobby', {}, 'shell'))}</button>`];
  // Keep personal preferences separate from privileged Admin policy for every authenticated principal.
  items.push(`<button data-route="settings" class="nav-item ${active === 'settings' ? 'active' : ''}" data-testid="nav-settings">${safe(t('settings.title', {}, 'shell'))}</button>`);
  // Add one button per game so every game remains equally reachable.
  gameDescriptors.forEach(game => items.push(`<button data-route="${game.id}" class="nav-item ${active === game.id ? 'active' : ''}" data-testid="nav-${game.id}">${safe(game.label)}</button>`));
  // Expose the Admin affordance only when the authenticated current-user contract carries the Admin role. (AUTH-008)
  if (currentSession?.user?.role === 'admin') items.push(`<button data-admin="true" class="nav-item admin" data-testid="nav-admin">${safe(t('nav.admin', {}, 'shell'))}</button>`);
  // Replace the nav contents atomically so active state cannot drift.
  nav.innerHTML = items.join('');
  // Expose the bounded menu as one keyboard-focusable horizontal scroll region. (issue #221, CORE-006)
  nav.tabIndex = 0;
  // Identify the menu as a navigable group with a localized accessible name.
  nav.setAttribute('role', 'group');
  // Name the menu so assistive technology announces the bounded games navigation.
  nav.setAttribute('aria-label', safe(t('nav.primaryAria', {}, 'shell') || 'Games navigation'));
  // Let keyboard users pan the bounded menu without a pointer using arrow and edge keys.
  nav.onkeydown = event => {
    // Read the current bounded-menu viewport width for one-page horizontal steps.
    const step = Math.max(160, nav.clientWidth * 0.8);
    // Scroll one step right on ArrowRight so later games become visible.
    if (event.key === 'ArrowRight') { nav.scrollLeft += step; event.preventDefault(); }
    // Scroll one step left on ArrowLeft so earlier games become visible.
    else if (event.key === 'ArrowLeft') { nav.scrollLeft -= step; event.preventDefault(); }
    // Jump to the first route on Home for fast reachability.
    else if (event.key === 'Home') { nav.scrollLeft = 0; event.preventDefault(); }
    // Jump to the last route on End for fast reachability.
    else if (event.key === 'End') { nav.scrollLeft = nav.scrollWidth; event.preventDefault(); }
  };
  // Reveal the active route immediately after each catalog or locale render.
  revealActiveNav();
  // Wire every app route button to the shared navigate function.
  nav.querySelectorAll('[data-route]').forEach(button => { button.onclick = () => navigate(button.dataset.route); });
  // Read the optional Admin button after role-aware navigation rendering.
  const adminButton = nav.querySelector('[data-admin]');
  // Wire the protected Admin page only when the authenticated role exposed its affordance. (AUTH-008)
  if (adminButton) adminButton.onclick = () => { location.href = '/admin'; };
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

// Navigate between lobby and game routes while keeping one mounted game at a time.
export async function navigate(route, options = {}) {
  // Branch when an unauthenticated browser tries to navigate before the auth gate is complete.
  if (!currentSession || currentSession.terms?.required) return;
  // Claim a fresh epoch so this navigation supersedes every earlier pending route operation.
  const navigationTicket = shellNavigationOwnership.claim();
  // Store the requested route for error reporting.
  let targetRoute = route;
  // End any in-flight shell celebration before game teardown or route remount can replace content.
  walletCelebrationLifecycle.interrupt('navigation');
  // Start protected navigation so failures render inside the route outlet.
  try {
    // Store the previous route so mounted games can unmount before route changes.
    const previous = active;
    // Check whether the requested route is one of the registered games.
    const knownGame = gameDescriptors.some(game => game.id === route);
    // Recognize the separate authenticated personal-settings destination.
    const knownSettings = route === 'settings';
    // Fall back to lobby for unknown routes.
    targetRoute = route === 'lobby' || knownSettings || knownGame ? route : 'lobby';
    // Synchronize normal navigation, initial restoration, or invalid-route replacement with browser history.
    if (options.history !== 'none') updateRouteHistory(targetRoute, options.history || (knownGame || knownSettings || route === 'lobby' ? 'push' : 'replace'));
    // Unmount the previously active game when that game supplied cleanup.
    if (previous && loadedGames.has(previous)) loadedGames.get(previous).unmount?.();
    // Store the active route for nav rendering.
    active = targetRoute;
    // Re-render navigation after active route changes.
    renderNav();
    // Read the main route outlet from the document.
    const view = document.getElementById('view');
    // Render the lobby when the target route is lobby.
    if (targetRoute === 'lobby') {
      // Stop observing game-only rails before rendering the lobby surface.
      gameRailObserver?.disconnect();
      // Let the authenticated shell allocate its remaining viewport height to one bounded lobby scroll region. (issue #318)
      document.body.classList.add('lobby-active');
      // Apply the lobby screen class contract for responsive shell styling.
      view.className = 'screen lobby-screen';
      // Include the intentional lobby scroll region in the natural keyboard tab order.
      view.tabIndex = 0;
      // Expose the bounded outlet as an assistive-technology region instead of an unlabeled generic main element.
      view.setAttribute('role', 'region');
      // Localize the scroll region's accessible name whenever the active shell locale rerenders the lobby.
      view.setAttribute('aria-label', safe(t('nav.lobby', {}, 'shell') || 'Lobby'));
      // Give browser acceptance tests a stable selector without coupling them to presentation classes.
      view.setAttribute('data-testid', 'lobby-scroll-region');
      // Render lobby markup and catalog controls from the cached API state.
      renderLobby(view);
      // Stop after lobby render because no game module is mounted.
      return;
    }
    // Render personal settings without importing or mounting a game module.
    if (targetRoute === 'settings') {
      // Stop observing game-owned scroll rails before the personal surface replaces them.
      gameRailObserver?.disconnect();
      // Keep settings out of the lobby-only containment contract.
      document.body.classList.remove('lobby-active');
      // Apply a bounded normal screen class for responsive personal cards.
      view.className = 'screen settings-screen';
      // Identify the settings surface for browser acceptance without presentation coupling.
      view.setAttribute('data-testid', 'settings-screen');
      // Keep the personal surface in the keyboard flow.
      view.tabIndex = 0;
      // Publish a localized accessible region name.
      view.setAttribute('role', 'region'); view.setAttribute('aria-label', safe(t('settings.title', {}, 'shell')));
      // Render caller-owned preferences, history, or guest conversion.
      await renderMySettings(view);
      // Restore a newer public route when settings completed after losing navigation ownership.
      if (!shellNavigationOwnership.owns(navigationTicket)) { renderPublicAuthRoute(); return; }
      // Stop before the game-loader branch.
      return;
    }
    // Restore the regular game shell flow before mounting any non-lobby route.
    document.body.classList.remove('lobby-active');
    // Apply the game screen class contract before mounting a game module.
    view.className = 'screen game-screen';
    // Remove the lobby-only test identity while preserving the shared route-outlet element.
    view.removeAttribute('data-testid');
    // Make the bounded game outlet a keyboard-focusable scroll region so every control stays reachable. (issue #221)
    view.tabIndex = 0; view.setAttribute('role', 'region'); view.setAttribute('aria-label', safe(t('nav.gamesArea', {}, 'shell') || 'Game area'));
    // Render a premium loading panel while the dynamic game module loads.
    view.innerHTML = `<div class="panel loading-panel"><h2>${safe(t('routeRestore.title', { game: routeLabel(targetRoute) }, 'shell'))}</h2></div>`;
    // Resolve the descriptor for the selected game route.
    const desc = gameDescriptors.find(game => game.id === targetRoute);
    // Load and mount the game only while this navigation keeps exact ownership across both awaits.
    const mountedRoute = await mountOwnedRoute({
      // Resolve the selected module through the established cached dynamic loader.
      load: () => loadGame(desc),
      // Mount the resolved game into the same route outlet used by the original app.
      mount: game => game.mount(view),
      // Recheck the captured shell ticket after import, mount, and failure boundaries.
      owns: () => shellNavigationOwnership.owns(navigationTicket),
      // Unmount stale post-mount work and restore only the exact newer public-account route.
      onStale: (game, mountStarted) => { if (mountStarted) game?.unmount?.(); renderPublicAuthRoute(); },
    });
    // Stop before observers or wallet repaint when a newer route invalidated this game navigation.
    if (mountedRoute.stale) return;
    // Prepare shared game rails for intentional keyboard and touch scrolling.
    observeGameScrollRegions(view);
    // Refresh the authenticated token wallet after route mount.
    updateCurrentUserShell();
  // Handle navigation errors with a route-local recovery panel.
  } catch (err) {
    // Never replace a newer public gate with an error produced by stale asynchronous route work.
    if (!shellNavigationOwnership.owns(navigationTicket)) { renderPublicAuthRoute(); return; }
    // Convert any protected-route auth failure into the logged-out recovery gate instead of a stale game error panel.
    if (err?.code === 'UNAUTHORIZED') { renderExpiredSessionGate(); return; }
    // Write diagnostic output so the current operation can be inspected.
    console.error(err);
    // Record the failure while requiring ownership again after diagnostic I/O before any fallback repaint.
    const ownsAfterLog = await awaitOwnedRouteEffect({
      // Publish only the bounded route and error diagnostics used by the existing Admin signal.
      run: () => logClient('navigation_error', { route: targetRoute, message: err.message, stack: err.stack }),
      // Recheck the exact captured ticket after the asynchronous diagnostic completes.
      owns: () => shellNavigationOwnership.owns(navigationTicket),
      // Restore a warm public-account route without painting the stale game error surface.
      onStale: () => renderPublicAuthRoute(),
    });
    // Stop before the route outlet changes when diagnostic completion was stale.
    if (!ownsAfterLog) return;
    // Read the route outlet for the fallback panel.
    const view = document.getElementById('view');
    // Keep a failed game route out of the lobby-only flex containment contract.
    document.body.classList.remove('lobby-active');
    // Remove the lobby-only test identity from the game error surface.
    view.removeAttribute('data-testid');
    // Keep the route outlet in game-screen mode so the error panel has premium shell padding.
    view.className = 'screen game-screen';
    // Render a friendly error state with a lobby recovery action.
    view.innerHTML = `<div class="panel loading-panel"><h2>${safe(t('route.loadFailed', { route: routeLabel(targetRoute) }, 'shell'))}</h2><p class="status">${safe(err.message)}</p><button data-route="lobby">${safe(t('route.backToLobby', {}, 'shell'))}</button></div>`;
    // Wire the fallback button without relying on the top navigation.
    view.querySelector('[data-route="lobby"]')?.addEventListener('click', () => navigate('lobby'));
  }
}

// Initialize shell state, wallet behavior, and the first lobby route.
async function init() {
  // Apply the active brand's design tokens and theme colour before first paint.
  applyBrand(activeBrand);
  // Initialize i18n before any auth or shell markup renders.
  await initI18n({ domains: ['shell', 'feedback'] });
  // Bind the native problem-report dialog after its translation domain is ready.
  bindFeedbackDialog();
  // Register the offline-safe shell and keep server actions locked until reconnect refresh completes.
  initPwa({ onReconnect: refreshAfterReconnect });
  // Publish reusable controller construction separately from authoritative initial data readiness.
  window.dispatchEvent(new CustomEvent('casino:shared-app-controller-ready'));
  // Render an immediate restored-game placeholder before slow session and casino-state calls finish.
  renderInitialRouteRestore();
  // Recalculate active-route visibility whenever responsive navigation layout changes.
  window.addEventListener('resize', revealActiveNav);
  // Read the persistent route outlet once for render-stability and containment wiring. (UX-026, UX-027)
  const routeOutlet = document.getElementById('view');
  // Remember which route/viewport cells already reported overflow so telemetry stays bounded per session. (UX-026)
  const reportedOverflowCells = new Set();
  // Hold the last measurement so only overflow confirmed across two settled audits is reported. (UX-026)
  let pendingOverflowKey = null;
  // Hold the debounce timer that lets animations settle before containment is measured.
  let layoutAuditTimer = null;
  // Measure containment after renders settle, and report confirmed loss through the frozen client-log route. (UX-026)
  const runLayoutAudit = () => {
    // Measure the live route content through the shared bounded auditor.
    const audit = auditLayoutContainment(routeOutlet);
    // Build the route-and-viewport cell identity for dedupe and confirmation.
    const cellKey = `${active || 'none'}|${window.innerWidth}x${window.innerHeight}`;
    // Clear the pending confirmation when the settled DOM is fully contained.
    if (audit.docOverflow <= 4 && !audit.offenders.length) { pendingOverflowKey = null; return; }
    // Arm the confirmation on first sight so one transient animation frame cannot page the owner.
    if (pendingOverflowKey !== cellKey) { pendingOverflowKey = cellKey; layoutAuditTimer = setTimeout(runLayoutAudit, 1200); return; }
    // Report each confirmed cell at most once per session so diagnostics stay low-volume.
    if (reportedOverflowCells.has(cellKey) || reportedOverflowCells.size >= 20) return;
    // Record the confirmed cell before the asynchronous log write.
    reportedOverflowCells.add(cellKey);
    // Publish the bounded overflow evidence to Admin telemetry through the frozen v1 client log.
    void logClient('layout_overflow', { route: active || 'none', viewport: `${window.innerWidth}x${window.innerHeight}`, doc_overflow: audit.docOverflow, offenders: audit.offenders, app_version: latestState?.version || 'unknown' });
  };
  // Schedule one settled containment audit after the latest render or resize. (UX-026)
  const scheduleLayoutAudit = () => { clearTimeout(layoutAuditTimer); layoutAuditTimer = setTimeout(runLayoutAudit, 700); };
  // Preserve player scroll and focus across every same-route rerender in all games and the lobby. (UX-027)
  installStableRouteRenders(routeOutlet, () => active, scheduleLayoutAudit);
  // Re-measure containment when the viewport itself changes size. (UX-026)
  window.addEventListener('resize', scheduleLayoutAudit);
  // Repaint persistent shell text when the locale changes.
  onLocaleChange(() => { localizeFeedback(); wellnessController.localize(); if (currentSession && !currentSession.terms?.required) { gameDescriptors = (latestState?.games || []).map(game => descriptorFromCatalog(game)); renderNav(); updateCurrentUserShell(); updateShellStatus(latestState, shellConnected); if (active === 'lobby') navigate('lobby', { history: 'none' }); } });
  // Restore game routes through browser Back and Forward without remounting stale history entries.
  window.addEventListener('popstate', () => { if (renderPublicAuthRoute()) return; if (currentSession && !currentSession.terms?.required) { document.body.classList.remove('auth-locked'); void navigate(routeFromLocation(), { history: 'none' }); } else renderLoginGate(); });
  // Read the add-token button from the wallet popover.
  const addButton = document.getElementById('add-token-btn');
  // Wire token addition through the planned ledger-backed current-user endpoint.
  addButton.onclick = async () => {
    // Start protected token mutation so validation errors become toasts.
    try {
      // Read the requested play-token amount from the wallet input.
      const amount = Number(document.getElementById('add-token-amount').value || 0);
      // Call the current-user token helper, which returns the updated contract player summary.
      const player = await addUserTokens({ amount });
      // Replace only the canonical player summary while preserving identity and session metadata.
      currentSession = normalizeCurrentUser({ ...currentSession, player });
      // Refresh the token wallet from the updated current-user payload.
      updateCurrentUserShell();
      // Clear the amount before any secondary refresh can race a repeated click. (TOKEN-007)
      document.getElementById('add-token-amount').value = '';
      // Close the wallet immediately after the authoritative mutation succeeds. (TOKEN-007)
      document.querySelector('.wallet-menu')?.removeAttribute('open');
      // Refresh shell state so status rail counts stay current.
      await refreshShellState({ quiet: true });
      // Show positive feedback for the completed token action.
      toast(t('toast.tokensAdded', { amount: tokens(amount) }, 'shell'), true);
    // Handle validation or API errors from the wallet action.
    } catch (err) {
      // Show the error message without interrupting the current route.
      toast(err.message);
    }
  };
  // Read the logout button from the persistent topbar.
  const logoutButton = document.getElementById('logout-btn');
  // Wire logout, or the disposable guest End-trial, through the planned v2 auth endpoints. (issue #317)
  logoutButton.onclick = async () => {
    // Detect a guest so the persistent control ends the trial with no recovery instead of logging out.
    const guestSession = isGuestSession();
    // Resolve the localized success message before teardown clears guest identity.
    const loggedOutMessage = t(guestSession ? 'auth.guestEnded' : 'auth.loggedOut', {}, 'shell');
    // Start protected teardown so the UI only claims logout after the backend session is gone.
    try {
      // Revoke the durable session or disposable guest trial through the backend-owned endpoint.
      await (guestSession ? endGuestTrial() : logout());
      // Clear the complete authenticated shell after successful server-side teardown.
      clearAuthenticatedShellState();
      // Return to the login gate, noting the ended guest trial where applicable.
      renderLoginGate(loggedOutMessage);
    // Keep the authenticated shell honest when the backend did not confirm session teardown.
    } catch (err) {
      // Treat an already-expired session as logged out because there is no live cookie to preserve.
      if (err?.code === 'UNAUTHORIZED') {
        // Clear authenticated chrome because the server has already rejected the old session.
        clearAuthenticatedShellState();
        // Return to the logged-out gate with the normal logout acknowledgement.
        renderLoginGate(loggedOutMessage);
        // Stop before recording a false logout failure.
        return;
      }
      // Show one localized failure instead of pretending the cookie was revoked.
      toast(t('auth.logoutFailed', {}, 'shell'));
      // Record the low-cardinality logout failure for Admin diagnostics without leaking cookie data.
      await logClient('logout_error', { code: err?.code || 'UNKNOWN', message: err?.message || 'Logout failed' });
      // Revalidate the session so the user sees the real state after a failed logout attempt.
      await refreshCurrentSession();
    }
  };
  // Start protected bootstrapping so the app can still show a friendly error toast.
  try {
    // Resolve the current-user session before any casino route can mount.
    await refreshCurrentSession();
  // Handle initial state failures with a visible toast and client log.
  } catch (err) {
    // Show the startup error in the shell toast.
    toast(t('startup.loadFailed', { message: err.message }, 'shell'));
    // Attempt bounded Admin telemetry without replacing the original authority failure.
    try { await logClient('initial_state_error', { message: err.message }); } catch (_) { /* Preserve the original startup failure. */ }
    // Reject readiness so native bootstrap cannot mark a failed current-user refresh green.
    throw err;
  }
  // Poll shell state periodically for connection and player-count status.
  setInterval(() => { if (currentSession && !currentSession.terms?.required) refreshShellState({ quiet: true }); }, 30000);
}

// Start the premium shell controller and publish an explicit native readiness handshake.
void init().then(() => {
  // Release native recovery only after the shared shell and authoritative controller are initialized.
  window.dispatchEvent(new CustomEvent('casino:shared-app-ready'));
}).catch(() => {
  // Signal a bounded initialization failure without exposing configuration or state details.
  window.dispatchEvent(new CustomEvent('casino:shared-app-error'));
});
