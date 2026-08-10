// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can call the frozen API envelope safely.
import { acceptTerms, addUserTokens, api, currentUser, departGuestTrial, endGuestTrial, guestTrial, logClient, login, logout, oauthLinks, oauthProviders, redeemInvitation, startOAuth, unlinkOAuth } from './core/api.js';
// Import required dependency so this module can render shared wallet and premium UI helpers.
import { renderTokenBalance, toast, tokens, safe, renderPremiumTag, installStableRouteRenders, auditLayoutContainment } from './core/ui.js';
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
// Track the current lobby search without encoding transient filters into game routes.
let lobbySearch = '';
// Track the selected scalable catalog category.
let lobbyCategory = 'all';
// Read one fixed provider-completion marker and immediately remove it from browser history.
const oauthCompletion = readOAuthCompletion();

// Relay game/autoplay toast events through the shell-level toast outlet.
window.addEventListener('casino-toast', event => toast(event.detail?.message || 'Auto stopped'));
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
  if (!['google', 'facebook'].includes(provider) || !['linked', 'signed_in', 'cancelled', 'error'].includes(status)) return null;
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
  // Map successful link and sign-in outcomes to the same privacy-safe acknowledgement.
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
function clearAuthenticatedShellState() {
  // Cancel any warning owned by the session being discarded.
  clearTimeout(sessionWarningTimer);
  // Clear the handle so a later session can schedule independently.
  sessionWarningTimer = null;
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
  // Render the browser login gate with private-beta toy-simulator acknowledgement.
  view.innerHTML = `<section class="auth-panel" data-testid="login-gate"><p class="eyebrow">${safe(t('auth.eyebrow', {}, 'shell'))}</p><h1>${safe(t('auth.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('auth.copy', {}, 'shell'))}</p><form id="login-form" class="auth-form"><label>${safe(t('auth.email', {}, 'shell'))}<input id="login-email" data-testid="login-email" type="email" autocomplete="username" required></label><label>${safe(t('auth.password', {}, 'shell'))}<input id="login-password" data-testid="login-password" type="password" autocomplete="current-password" required></label><label>${safe(t('auth.language', {}, 'shell'))}<select id="auth-locale-select" data-testid="auth-locale-select"></select></label><label class="check-row"><input id="login-terms-check" data-testid="login-terms-check" type="checkbox" required><span>${safe(t('auth.termsCheck', {}, 'shell'))}</span></label><button class="primary" data-testid="login-submit" type="submit">${safe(t('auth.submit', {}, 'shell'))}</button><a href="/account/reset" data-testid="password-reset-entry">${safe(t('recovery.forgot', {}, 'shell'))}</a><p id="auth-message" class="auth-message" data-testid="oauth-callback-message">${safe(authMessage)}</p></form><div class="auth-signup" data-testid="signup-entry"><a class="secondary" href="/enroll/signup" data-testid="signup-entry-link">${safe(t('signup.cta', {}, 'shell'))}</a><p class="auth-guest-copy">${safe(t('signup.entryCopy', {}, 'shell'))}</p></div><div class="auth-guest" data-testid="guest-trial"><button id="guest-trial-button" class="secondary" data-testid="guest-trial-button" type="button" disabled aria-disabled="true">${safe(t('auth.guestCta', {}, 'shell'))}</button><p class="auth-guest-copy" data-testid="guest-trial-copy">${safe(t('auth.guestInfo', {}, 'shell'))}</p></div><section class="oauth-provider-status" data-testid="oauth-providers-disabled" aria-labelledby="oauth-provider-heading"><h2 id="oauth-provider-heading">${safe(t('auth.oauthDivider', {}, 'shell'))}</h2><div class="oauth-provider-grid"><button class="oauth-provider-button" data-testid="oauth-google" type="button" disabled aria-disabled="true">${safe(t('auth.oauthGoogle', {}, 'shell'))}</button><button class="oauth-provider-button" data-testid="oauth-facebook" type="button" disabled aria-disabled="true">${safe(t('auth.oauthFacebook', {}, 'shell'))}</button></div><p class="oauth-provider-copy" data-testid="oauth-provider-message" role="status">${safe(t('auth.oauthUnavailable', {}, 'shell'))}</p></section></section>`;
  // Wire the auth-screen locale selector and rerender the gate after switching.
  wireLocaleSelect(document.getElementById('auth-locale-select'), () => renderLoginGate(message));
  // Wire form submission through the v2 auth login endpoint.
  document.getElementById('login-form').onsubmit = handleLoginSubmit;
  // Wire the account-free guest-trial entry so a visitor can start a disposable session without login. (issue #317)
  const guestButton = document.getElementById('guest-trial-button');
  // Start a guest trial on click only when the configuration-driven button is present.
  if (guestButton) guestButton.onclick = handleGuestTrial;
  // Resolve the durable owner-controlled guest admission switch before enabling anonymous entry. (GUEST-001)
  void applyGuestTrialPolicy();
  // Resolve provider availability after the password and guest controls are already usable.
  void enableAvailableOAuthSignIn();
}

// Apply the public guest-admission capability to the logged-out entry without trusting browser state. (GUEST-001)
async function applyGuestTrialPolicy() {
  // Resolve the stable button and disclosure from the current login render.
  const button = document.getElementById('guest-trial-button');
  // Resolve the copy independently so unavailable state remains explicit to assistive users.
  const copy = document.querySelector('[data-testid="guest-trial-copy"]');
  // Stop if route navigation replaced the login gate before this task began.
  if (!button || !copy) return;
  // Start protected capability loading so any failure leaves anonymous creation disabled.
  try {
    // Read only boolean enrollment capabilities from the public no-state endpoint.
    const policy = await api('/api/v2/auth/enrollment-policy');
    // Enable the native control only for an exact server-published true value.
    button.disabled = policy.guest_trials_enabled !== true;
    // Mirror native state for assistive technology.
    button.setAttribute('aria-disabled', String(button.disabled));
    // Replace the token disclosure only when new guest creation is currently held.
    copy.textContent = button.disabled ? t('auth.guestUnavailable', {}, 'shell') : t('auth.guestInfo', {}, 'shell');
  // Keep a failed capability request fail-closed and understandable without exposing transport details.
  } catch (_) {
    // Preserve disabled native state when the authoritative policy cannot be read.
    button.disabled = true;
    // Preserve matching assistive state.
    button.setAttribute('aria-disabled', 'true');
    // Explain temporary unavailability through localized product copy.
    copy.textContent = t('auth.guestUnavailable', {}, 'shell');
  }
}

// Enable only independently released providers while retaining disabled-by-default login behavior. (OAUTH-007)
async function enableAvailableOAuthSignIn() {
  // Read the provider-status region from the current login render.
  const region = document.querySelector('.oauth-provider-status');
  // Stop when navigation replaced the login screen before the request began.
  if (!region) return;
  // Start protected availability loading so local-password and guest entry remain usable on failure.
  try {
    // Fetch only fixed provider ids and boolean availability.
    const result = await oauthProviders();
    // Select exact provider identifiers whose complete runtime and independent network gate are ready.
    const available = new Set((result.providers || []).filter(item => item.available === true).map(item => item.provider));
    // Configure each reviewed provider button independently.
    for (const provider of ['google', 'facebook']) {
      // Read the provider's stable login control.
      const button = document.querySelector(`[data-testid="oauth-${provider}"]`);
      // Skip a stale render or malformed response without affecting local login.
      if (!button) continue;
      // Enable only an exact provider reported available by the bounded public contract.
      button.disabled = !available.has(provider);
      // Keep assistive state aligned with native disabled behavior.
      button.setAttribute('aria-disabled', String(button.disabled));
      // Navigate only after a server-created one-time flow succeeds.
      button.onclick = button.disabled ? null : () => beginOAuth(provider, 'signin');
    }
    // Mark the visual matrix state according to any fully released provider.
    region.dataset.testid = available.size ? 'oauth-providers-available' : 'oauth-providers-disabled';
    // Explain the private-invite boundary whenever a provider is available.
    region.querySelector('[data-testid="oauth-provider-message"]').textContent = available.size ? t('auth.oauthInviteOnly', {}, 'shell') : t('auth.oauthUnavailable', {}, 'shell');
  // Keep controls disabled and show a stable retry-safe message on status failure.
  } catch (_) {
    // Stamp the governed failure state without exposing transport or configuration details.
    region.dataset.testid = 'oauth-providers-status-error';
    // Preserve all local auth controls and publish one generic localized status.
    region.querySelector('[data-testid="oauth-provider-message"]').textContent = t('auth.oauthStatusError', {}, 'shell');
  }
}

// Request a one-time authorization URL and navigate without logging or persisting it. (OAUTH-008)
async function beginOAuth(provider, action) {
  // Read the active auth/account message outlet for bounded errors.
  const message = action === 'signin' ? document.getElementById('auth-message') : document.getElementById('oauth-account-message');
  // Start protected flow creation so no provider navigation occurs after an API failure.
  try {
    // Read the explicit linking checkbox only for authenticated account linking.
    const confirmation = document.getElementById('oauth-link-confirm');
    // Stop linking until the canonical user explicitly confirms this action.
    if (action === 'link' && !confirmation?.checked) throw new Error(t('auth.oauthConfirmRequired', {}, 'shell'));
    // Request a short-lived browser-bound flow with a same-origin destination.
    const result = await startOAuth(provider, { action, return_to: '/', ...(action === 'link' ? { confirm_link: true } : {}) });
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
  return location.pathname.replace(/\/$/, '') === '/enroll/invitation';
}

// Report whether the current URL names the full-account enrollment surface.
function isSignupRoute() {
  // Match only the canonical signup path; all other anonymous paths retain the normal login gate.
  return location.pathname.replace(/\/$/, '') === '/enroll/signup';
}

// Report whether the current URL names the public password-recovery destination. (RESET-004)
function isPasswordResetRoute() {
  // Match only the canonical path so arbitrary anonymous URLs remain at the login gate.
  return location.pathname.replace(/\/$/, '') === '/account/reset';
}

// Render enumeration-safe recovery initiation or bearer completion without mounting casino routes. (RESET-004)
function renderPasswordResetGate(message = '', success = false) {
  // Clear any stale authenticated shell state before exposing the public recovery form.
  currentSession = null; window.CasinoCurrentUser = null; syncFeedbackReporter(null);
  // Keep protected chrome hidden throughout recovery.
  document.body.classList.remove('lobby-active'); document.body.classList.add('auth-locked');
  // Read the route outlet reserved by the public shell.
  const view = document.getElementById('view');
  // Apply the shared auth layout and remove protected-region semantics.
  view.className = 'screen auth-screen'; view.removeAttribute('tabindex'); view.removeAttribute('role'); view.removeAttribute('aria-label'); view.removeAttribute('data-testid');
  // Read the transient bearer only to choose and submit the completion form.
  const token = new URL(location.href).searchParams.get('token') || '';
  // Render initiation when no bearer is present and completion when the mail link supplied one.
  view.innerHTML = token ? `<section class="auth-panel" data-testid="password-reset-complete"><p class="eyebrow">${safe(t('recovery.eyebrow', {}, 'shell'))}</p><h1>${safe(t('recovery.completeTitle', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('recovery.completeCopy', {}, 'shell'))}</p><form id="password-reset-form" class="auth-form"><label>${safe(t('auth.email', {}, 'shell'))}<input id="reset-email" type="email" autocomplete="email" required></label><label>${safe(t('recovery.newPassword', {}, 'shell'))}<input id="reset-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><button class="primary" type="submit">${safe(t('recovery.complete', {}, 'shell'))}</button><p id="reset-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${safe(message)}</p></form><a href="/">${safe(t('recovery.back', {}, 'shell'))}</a></section>` : `<section class="auth-panel" data-testid="password-reset-initiate"><p class="eyebrow">${safe(t('recovery.eyebrow', {}, 'shell'))}</p><h1>${safe(t('recovery.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('recovery.copy', {}, 'shell'))}</p><form id="password-reset-form" class="auth-form"><label>${safe(t('auth.email', {}, 'shell'))}<input id="reset-email" type="email" autocomplete="email" required></label><button class="primary" type="submit">${safe(t('recovery.send', {}, 'shell'))}</button><p id="reset-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${safe(message)}</p></form><a href="/">${safe(t('recovery.back', {}, 'shell'))}</a></section>`;
  // Submit the currently rendered initiation or completion form through one bounded handler.
  document.getElementById('password-reset-form').onsubmit = async event => {
    // Prevent navigation while the enumeration-safe request is active.
    event.preventDefault();
    // Read the status outlet and submit control for deterministic in-flight behavior.
    const status = document.getElementById('reset-message'); const submit = event.currentTarget.querySelector('button[type="submit"]'); submit.disabled = true;
    // Start protected recovery so public error details never replace generic copy.
    try {
      // Complete the bearer flow when a token is present.
      if (token) {
        // Submit the exact transient bearer, mailbox, replacement, and caller key.
        await api('/api/v2/auth/password-reset/complete', { method: 'POST', body: { token, email: document.getElementById('reset-email').value.trim(), new_password: document.getElementById('reset-password').value, idempotency_key: crypto.randomUUID() } });
        // Remove the bearer from browser history immediately after terminal success.
        history.replaceState({}, '', '/');
        // Return to sign-in with a privacy-safe completion acknowledgement.
        renderLoginGate(t('recovery.completed', {}, 'shell'));
        // Stop this handler after route replacement.
        return;
      }
      // Initiate or reissue recovery with one identical public acknowledgement.
      await api('/api/v2/auth/password-reset/initiate', { method: 'POST', body: { email: document.getElementById('reset-email').value.trim(), locale: getLocaleState().locale, idempotency_key: crypto.randomUUID() } });
      // Publish the identical success copy regardless of account existence or delivery state.
      if (status) { status.textContent = t('recovery.accepted', {}, 'shell'); status.dataset.success = 'true'; }
    // Collapse disabled, malformed, expired, and provider failures into one retry-safe message.
    } catch (_) {
      // Publish one generic recovery failure without reflecting server internals.
      if (status) status.textContent = t('recovery.unavailable', {}, 'shell');
    // Re-enable the still-mounted form after a recoverable request.
    } finally {
      // Avoid touching a control removed by successful completion navigation.
      if (submit.isConnected) submit.disabled = false;
    }
  };
}

// Derive a token-free session key and stable caller idempotency value for reload-safe redemption. (INVITE-003)
async function invitationIdempotency(token) {
  // Hash the transient URL bearer with the browser crypto implementation.
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token));
  // Encode only a short non-secret digest prefix for sessionStorage lookup.
  const key = `casino.invitation.idempotency.${Array.from(new Uint8Array(digest).slice(0, 12)).map(value => value.toString(16).padStart(2, '0')).join('')}`;
  // Read an existing same-browser caller key so a lost response can resume safely.
  const existing = sessionStorage.getItem(key);
  // Return the stable value when the browser already started this exact bearer flow.
  if (existing) return existing;
  // Generate one bounded caller-owned replay key without deriving it from the bearer.
  const created = crypto.randomUUID();
  // Persist only the random caller key under the non-secret digest lookup for this browser session.
  sessionStorage.setItem(key, created);
  // Return the newly created idempotency value.
  return created;
}

// Render the full-account enrollment form while honoring the server-published signup gate.
async function renderSignupGate(message = '', success = false) {
  // Clear any stale authenticated shell identity while the public route is displayed.
  window.CasinoCurrentUser = null;
  // Keep casino chrome locked behind successful signup and login.
  document.body.classList.remove('lobby-active', 'guest-trial-active');
  // Apply the established authentication layout at all governed viewports.
  document.body.classList.add('auth-locked');
  // Reset current session before showing the public form.
  currentSession = null;
  // Hide registered-user feedback while the browser is anonymous.
  syncFeedbackReporter(null);
  // Remove authenticated route semantics from the public outlet.
  view.removeAttribute('tabindex'); view.removeAttribute('role'); view.removeAttribute('aria-label'); view.removeAttribute('data-testid');
  // Render a loading form shell while the policy endpoint resolves.
  view.innerHTML = `<section class="auth-panel" data-testid="signup-enrollment"><p class="eyebrow">${safe(t('signup.eyebrow', {}, 'shell'))}</p><h1>${safe(t('signup.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('status.loading', {}, 'shell'))}</p></section>`;
  // Load policy from the public read-only endpoint.
  const policy = await api('/api/v2/auth/enrollment-policy');
  // Determine whether full public signup may submit.
  const enabled = policy.signup_enabled === true;
  // Render the complete form with a visible disabled state when signup is held.
  view.innerHTML = `<section class="auth-panel" data-testid="signup-enrollment" data-signup-enabled="${enabled ? 'true' : 'false'}"><p class="eyebrow">${safe(t('signup.eyebrow', {}, 'shell'))}</p><h1>${safe(t('signup.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(enabled ? t('signup.copy', {}, 'shell') : t('signup.disabledCopy', {}, 'shell'))}</p><form id="signup-form" class="auth-form"><label>${safe(t('auth.email', {}, 'shell'))}<input id="signup-email" data-testid="signup-email" type="email" autocomplete="email" maxlength="254" required></label><label>${safe(t('invitation.displayName', {}, 'shell'))}<input id="signup-display-name" data-testid="signup-display-name" autocomplete="name" maxlength="80" required></label><label>${safe(t('auth.password', {}, 'shell'))}<input id="signup-password" data-testid="signup-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><label>${safe(t('auth.language', {}, 'shell'))}<select id="signup-locale" data-testid="signup-locale"></select></label><label class="check-row"><input id="signup-terms" data-testid="signup-terms" type="checkbox" required><span>${safe(t('auth.termsCheck', {}, 'shell'))}</span></label><button class="primary" data-testid="signup-submit" type="submit" ${enabled ? '' : 'disabled'}>${safe(t('signup.submit', {}, 'shell'))}</button><p id="signup-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${safe(message)}</p></form><a href="/" data-testid="signup-login-link">${safe(t('invitation.back', {}, 'shell'))}</a></section>`;
  // Populate locale options through the shared locale manifest.
  wireLocaleSelect(document.getElementById('signup-locale'), () => {});
  // Bind submit to the policy-gated signup API.
  document.getElementById('signup-form').onsubmit = async event => {
    // Keep the native form from navigating away.
    event.preventDefault();
    // Read the live status element.
    const status = document.getElementById('signup-message');
    // Start protected signup so validation errors stay local to the form.
    try {
      // Submit the full-account request to the disabled-by-default signup API.
      const result = await api('/api/v2/auth/signup', { method: 'POST', body: { email: document.getElementById('signup-email').value, password: document.getElementById('signup-password').value, display_name: document.getElementById('signup-display-name').value, locale: document.getElementById('signup-locale').value, terms_version: 'private-beta-1', accepted: document.getElementById('signup-terms').checked } });
      // Enter the authenticated shell after the server creates the session.
      await enterAuthenticated(result);
    // Show one localized enrollment failure without leaking backend details.
    } catch (_) {
      // Publish generic failure copy in the form.
      status.textContent = t('signup.failed', {}, 'shell');
    }
  };
}


// Hold the transient invitation bearer in module memory so the URL, history, and referrer stop carrying it. (issue #417 residual)
let invitationBearerToken = '';

// Render the account-free private invitation enrollment form without creating state on page load. (INVITE-003, INVITE-005)
function renderInvitationGate(message = '', success = false) {
  // Read the bearer from the canonical URL exactly once per arrival rather than on every submit.
  const arrivalToken = new URL(location.href).searchParams.get('token') || '';
  // Capture a newly-arrived bearer without clobbering the held value on locale-driven rerenders.
  if (arrivalToken) {
    // Keep the bearer only in module-local memory for the pending redemption.
    invitationBearerToken = arrivalToken;
    // Scrub the bearer from the address bar, session history, and any later referrer immediately on entry.
    history.replaceState({}, '', '/enroll/invitation');
  }
  // Clear any stale authenticated shell identity while the public route is displayed.
  window.CasinoCurrentUser = null;
  // Keep the casino shell and lobby layout locked behind successful enrollment and later login.
  document.body.classList.remove('lobby-active', 'guest-trial-active');
  // Apply the established authentication layout at all governed viewports.
  document.body.classList.add('auth-locked');
  // Resolve the shared public route outlet.
  const view = document.getElementById('view');
  // Remove authenticated region semantics before rendering the account-free form.
  view.removeAttribute('tabindex'); view.removeAttribute('role'); view.removeAttribute('aria-label'); view.removeAttribute('data-testid');
  // Apply the shared accessible auth-screen presentation.
  view.className = 'screen auth-screen';
  // Render explicit restricted-preview, password, locale, and current-terms fields with one generic live result.
  view.innerHTML = `<section class="auth-panel" data-testid="invitation-redemption"><p class="eyebrow">${safe(t('invitation.eyebrow', {}, 'shell'))}</p><h1>${safe(t('invitation.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('invitation.copy', {}, 'shell'))}</p><form id="invitation-form" class="auth-form"><label>${safe(t('invitation.email', {}, 'shell'))}<input id="invitation-email" data-testid="invitation-email" type="email" autocomplete="email" maxlength="254" required></label><label>${safe(t('invitation.displayName', {}, 'shell'))}<input id="invitation-display-name" data-testid="invitation-display-name" autocomplete="name" maxlength="80" required></label><label>${safe(t('invitation.password', {}, 'shell'))}<input id="invitation-password" data-testid="invitation-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><label>${safe(t('invitation.language', {}, 'shell'))}<select id="invitation-locale" data-testid="invitation-locale"></select></label><label class="check-row"><input id="invitation-terms" data-testid="invitation-terms" type="checkbox" required><span>${safe(t('invitation.terms', {}, 'shell'))}</span></label><button class="primary" data-testid="invitation-submit" type="submit">${safe(t('invitation.submit', {}, 'shell'))}</button><p id="invitation-message" class="auth-message" role="status" data-success="${success ? 'true' : 'false'}">${safe(message)}</p></form><a href="/" data-testid="invitation-login-link">${safe(t('invitation.back', {}, 'shell'))}</a></section>`;
  // Populate the locale selector from the governed manifest and rerender in place after a switch.
  wireLocaleSelect(document.getElementById('invitation-locale'), () => renderInvitationGate(message, success));
  // Submit through the recovery-safe public handler.
  document.getElementById('invitation-form').onsubmit = handleInvitationSubmit;
}

// Submit one explicit invitation redemption while keeping every rejection non-enumerating. (INVITE-003)
async function handleInvitationSubmit(event) {
  // Prevent a full page reload that could obscure the caller-idempotent result.
  event.preventDefault();
  // Resolve the generic live status outlet.
  const message = document.getElementById('invitation-message');
  // Prefer the entry-captured module-local bearer; fall back to the URL only for direct deep submissions. (issue #417 residual)
  const token = invitationBearerToken || new URL(location.href).searchParams.get('token') || '';
  // Disable repeated clicks until the exact request settles.
  const submit = document.querySelector('[data-testid="invitation-submit"]');
  // Prevent a second in-flight mutation from this form.
  submit.disabled = true;
  // Start protected redemption so every failure renders the same localized public message.
  try {
    // Build the complete current-terms payload with one reload-stable caller key.
    const payload = { token, email: document.getElementById('invitation-email').value.trim(), password: document.getElementById('invitation-password').value, display_name: document.getElementById('invitation-display-name').value.trim(), locale: getLocaleState().locale, terms_version: 'private-beta-1', accepted: document.getElementById('invitation-terms').checked === true, idempotency_key: await invitationIdempotency(token) };
    // Submit only after the browser has collected every explicit enrollment field.
    await redeemInvitation(payload);
    // Remove the bearer from browser history immediately after terminal success.
    history.replaceState({}, '', '/');
    // Drop the module-local bearer as soon as the redemption settles. (issue #417 residual)
    invitationBearerToken = '';
    // Return to login with an identifier-free success prompt.
    renderLoginGate(t('invitation.success', {}, 'shell'));
  // Collapse disabled, malformed, expired, revoked, replayed, and raced results into one message.
  } catch (_) {
    // Publish no state-specific reason or server text.
    if (message) message.textContent = t('invitation.unavailable', {}, 'shell');
    // Re-enable the same form for recoverable exact-key retry.
    submit.disabled = false;
  }
}

// Render the terms acceptance step when the current session still requires it.
function renderTermsGate(session) {
  // Store the current session so accepted terms can continue into the shell.
  currentSession = session;
  // Leave lobby-only flex containment before the terms screen replaces the route outlet.
  document.body.classList.remove('lobby-active');
  // Mark the document so chrome and game routes stay hidden until terms are accepted.
  document.body.classList.add('auth-locked');
  // Read the main route outlet reserved by index.html.
  const view = document.getElementById('view');
  // Remove authenticated lobby-region semantics before exposing the terms gate.
  view.removeAttribute('tabindex'); view.removeAttribute('role'); view.removeAttribute('aria-label'); view.removeAttribute('data-testid');
  // Apply the auth screen class contract for login and terms flows.
  view.className = 'screen auth-screen';
  // Read the required terms version from the current-user payload.
  const version = session.terms?.version || session.terms?.required_version || 'private-beta';
  // Render a concise toy-simulator terms acknowledgement gate.
  view.innerHTML = `<section class="auth-panel" data-testid="terms-gate"><p class="eyebrow">${safe(t('terms.eyebrow', {}, 'shell'))}</p><h1>${safe(t('terms.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('terms.copy', {}, 'shell'))}</p><p class="auth-copy strong">${safe(t('terms.version', { version }, 'shell'))}</p><button id="accept-terms-btn" class="primary" data-testid="accept-terms" type="button">${safe(t('terms.accept', {}, 'shell'))}</button><p id="auth-message" class="auth-message"></p></section>`;
  // Wire the accept button through the v2 current-user terms endpoint.
  document.getElementById('accept-terms-btn').onclick = handleTermsAccept;
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
  // Read the shared message outlet for validation and API errors.
  const message = document.getElementById('auth-message');
  // Start protected login logic so validation errors stay inside the auth panel.
  try {
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
    // Read the visible shared consent checkbox rather than inferring acceptance from the button click.
    const accepted = document.getElementById('login-terms-check')?.checked === true;
    // Require an affirmative action before any anonymous identity, wallet, or telemetry is created.
    if (!accepted) throw new Error(t('auth.guestTermsRequired', {}, 'shell'));
    // Create the isolated disposable guest session with exact versioned consent metadata.
    const session = await guestTrial({ accepted, terms_version: 'private-beta-1', locale: getLocaleState().locale, device: innerWidth < 600 ? 'mobile' : innerWidth < 1100 ? 'tablet' : 'desktop' });
    // Enter the authenticated shell using the same payload shape as a registered login.
    await enterAuthenticated(session);
  // Handle a disabled or failed guest entry with local auth-panel feedback.
  } catch (err) {
    // Render the API error without leaving the login gate.
    if (message) message.textContent = err.message;
  }
}

// Accept the required private beta toy-simulator terms for the current user.
async function handleTermsAccept() {
  // Read the shared message outlet for API errors.
  const message = document.getElementById('auth-message');
  // Start protected terms logic so API errors stay inside the terms panel.
  try {
    // Read the required terms version from the cached session.
    const version = currentSession?.terms?.version || currentSession?.terms?.required_version || 'private-beta';
    // Call the published v2 current-user terms endpoint.
    const terms = await acceptTerms({ terms_version: version, locale: getLocaleState().locale });
    // Merge the returned contract terms status into the canonical current-user payload.
    currentSession = normalizeCurrentUser({ ...currentSession, terms });
    // Enter the authenticated shell with the updated terms state.
    await enterAuthenticated(currentSession);
  // Handle failed terms acceptance with local auth-panel feedback.
  } catch (err) {
    // Render the API error without leaving the terms gate.
    if (message) message.textContent = err.message;
  }
}

// Refresh the current-user session and choose the correct first screen.
async function refreshCurrentSession() {
  // Start protected current-user loading so anonymous browsers see the login gate.
  try {
    // Read the planned v2 current-user endpoint.
    const session = await currentUser();
    // Enter the authenticated shell or terms step from the returned payload.
    await enterAuthenticated(session);
    // Confirm that authoritative session refresh succeeded for reconnect handling.
    return true;
  // Handle missing or expired sessions by showing the browser login gate.
  } catch (_) {
    // Clear the current session so no stale wallet can render.
    currentSession = null;
    // Render the exact account-free enrollment path, signup path, or the normal private-beta login gate.
    if (isInvitationRoute()) renderInvitationGate(); else if (isSignupRoute()) void renderSignupGate(); else if (isPasswordResetRoute()) renderPasswordResetGate(); else renderLoginGate();
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
  // Center a late-catalog active route inside desktop and mobile horizontal navigation.
  if (activeItem) nav.scrollLeft = Math.max(0, activeItem.offsetLeft - ((nav.clientWidth - activeItem.offsetWidth) / 2));
}

// Render the premium top navigation from the route registry.
async function renderMySettings(view) {
  // Load the caller's durable preferences and account-owned history in parallel when applicable. (USER-009)
  const preferenceData = await api('/api/v2/me/settings');
  // Read the settings under the documented defaults for a newly created account.
  const settings = preferenceData.settings || { locale: 'en-US', sound_enabled: false, revision: 0 };
  // Keep disposable guests out of durable history while still exposing session-local preferences and conversion.
  const historyData = isGuestSession() ? { events: [] } : await api('/api/v2/me/history?page=1&page_size=25');
  // Stop a stale request from replacing a newer route.
  if (active !== 'settings') return;
  // Render one personal surface distinct from owner-only Admin controls.
  view.innerHTML = `<section class="panel settings-panel" data-testid="my-settings"><p class="eyebrow">${safe(t('settings.eyebrow', {}, 'shell'))}</p><h1>${safe(t('settings.title', {}, 'shell'))}</h1><p>${safe(t('settings.copy', {}, 'shell'))}</p><form id="personal-settings-form" class="auth-form"><label>${safe(t('settings.language', {}, 'shell'))}<select id="personal-settings-locale" data-testid="personal-settings-locale"></select></label><label class="check-row"><input id="personal-settings-sound" data-testid="personal-settings-sound" type="checkbox" ${settings.sound_enabled === true ? 'checked' : ''}><span>${safe(t('settings.sound', {}, 'shell'))}</span></label><button class="primary" data-testid="personal-settings-save" type="submit">${safe(t('settings.save', {}, 'shell'))}</button><p id="personal-settings-message" class="auth-message" role="status"></p></form></section>${isGuestSession() ? `<section class="panel settings-panel" data-testid="guest-conversion"><h2>${safe(t('conversion.title', {}, 'shell'))}</h2><p>${safe(t('conversion.copy', {}, 'shell'))}</p><form id="guest-conversion-form" class="auth-form"><label>${safe(t('auth.email', {}, 'shell'))}<input id="conversion-email" type="email" maxlength="254" required></label><label>${safe(t('conversion.displayName', {}, 'shell'))}<input id="conversion-display-name" maxlength="80" required></label><label>${safe(t('conversion.password', {}, 'shell'))}<input id="conversion-password" type="password" minlength="12" maxlength="128" required></label><label class="check-row"><input id="conversion-terms" type="checkbox" required><span>${safe(t('conversion.terms', {}, 'shell'))}</span></label><button class="primary" data-testid="guest-conversion-submit" type="submit">${safe(t('conversion.submit', {}, 'shell'))}</button><p id="guest-conversion-message" class="auth-message" role="status"></p></form></section>` : `<section class="panel settings-panel" data-testid="my-history"><h2>${safe(t('settings.history', {}, 'shell'))}</h2>${(historyData.events || []).length ? `<div class="table-scroll" tabindex="0" role="region" aria-label="${safe(t('settings.history', {}, 'shell'))}"><table class="mini-table"><thead><tr><th>${safe(t('settings.time', {}, 'shell'))}</th><th>${safe(t('settings.game', {}, 'shell'))}</th><th>${safe(t('settings.event', {}, 'shell'))}</th><th>${safe(t('settings.amount', {}, 'shell'))}</th><th>${safe(t('settings.balance', {}, 'shell'))}</th><th>${safe(t('settings.reference', {}, 'shell'))}</th></tr></thead><tbody>${historyData.events.map(event => `<tr><td>${safe(event.ts || '')}</td><td>${safe(event.game || '')}</td><td>${safe(event.transaction_type || '')}</td><td>${safe(event.amount)}</td><td>${safe(event.balance_after)}</td><td>${safe(event.reference || '')}</td></tr>`).join('')}</tbody></table></div>` : `<p class="status">${safe(t('settings.historyEmpty', {}, 'shell'))}</p>`}</section>`}`;
  // Fill the locale select from the governed locale manifest.
  const localeSelect = view.querySelector('#personal-settings-locale');
  // Reuse the shared option renderer before selecting the server-authored value.
  localeSelect.innerHTML = localeOptionsHtml();
  // Preserve the active login/browser locale until a real durable settings write establishes a preference.
  localeSelect.value = settings.updated_at ? settings.locale : getLocaleState().locale;
  // Save one optimistic personal preference revision without touching Admin policy.
  view.querySelector('#personal-settings-form').onsubmit = async event => {
    // Keep the browser on the personal settings route.
    event.preventDefault();
    // Persist only the published locale, sound flag, and current optimistic revision.
    const result = await api('/api/v2/me/settings', { method: 'PATCH', body: { locale: localeSelect.value, sound_enabled: view.querySelector('#personal-settings-sound').checked, revision: settings.revision } });
    // Advance the in-memory optimistic revision so repeated saves cannot reuse a stale token.
    settings.revision = result.settings?.revision ?? settings.revision;
    // Apply the accepted sound preference to the current browser immediately.
    setPersonalSoundEnabled(result.settings?.sound_enabled === true);
    // Apply the accepted locale after the server confirms persistence.
    if (result.settings?.locale) await setLocale(result.settings.locale, { persistLocal: false });
    // Confirm the authoritative save in the still-mounted surface.
    const message = document.getElementById('personal-settings-message');
    // Publish localized success copy when the locale rerender did not replace the node.
    if (message) message.textContent = t('settings.saved', {}, 'shell');
  };
  // Bind explicit guest conversion only for a live disposable guest surface.
  const conversionForm = view.querySelector('#guest-conversion-form');
  // Submit the conversion through its recovery-safe additive v2 route.
  if (conversionForm) conversionForm.onsubmit = async event => {
    // Keep the guest on this surface until the server commits conversion.
    event.preventDefault();
    // Read the stable live result outlet before starting the request.
    const message = view.querySelector('#guest-conversion-message');
    // Submit canonical account identity while preserving the existing guest player and wallet.
    await api('/api/v2/me/convert-guest', { method: 'POST', body: { email: view.querySelector('#conversion-email').value.trim(), display_name: view.querySelector('#conversion-display-name').value.trim(), password: view.querySelector('#conversion-password').value, terms_version: 'private-beta-1', accepted: view.querySelector('#conversion-terms').checked, locale: localeSelect.value, idempotency_key: crypto.randomUUID() } });
    // Report terminal completion before clearing the now-revoked guest shell.
    message.textContent = t('conversion.completed', {}, 'shell');
    // Clear the disposable session and return to login for the durable account.
    clearAuthenticatedShellState();
    // Render an explicit sign-in handoff without retaining form secrets.
    renderLoginGate(t('conversion.completed', {}, 'shell'));
  };
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

// Render one status tile for the lobby trust rail.
function trustItemHtml(code, title, detail) {
  // Return a compact status tile that mirrors the approved lobby prerender.
  return `<div class="trust-item"><span class="round-icon">${safe(code)}</span><span><strong>${safe(title)}</strong><span>${safe(detail)}</span></span></div>`;
}

// Render one premium lobby game card from shared game metadata.
function lobbyCardHtml(game) {
  // Compute the layout modifier classes used by the approved card grid.
  const sizeClass = `${game.featured ? ' featured' : ''}${game.wide ? ' wide' : ''}`;
  // Render all card tags through the shared helper so later workers can reuse the tag contract.
  const tags = game.tags.map(tag => renderPremiumTag(tag)).join('');
  // Return the full card with deterministic art, metadata, and open-game control.
  return `<article class="game-card${sizeClass}" data-testid="card-${game.id}"><div class="card-art ${game.artClass}" aria-hidden="true"></div><span class="game-kicker">${game.featured ? '&#9733; ' : ''}${safe(game.kicker)}</span><div class="game-card-content"><h2 class="game-heading"><span class="game-symbol">${game.symbol}</span>${safe(game.label)}</h2><p>${safe(game.description)}</p><div class="tag-row">${tags}</div><button class="play-button" data-open-game="${game.id}" data-testid="open-${game.id}"><span>${safe(t('catalog.play', {}, 'shell'))}</span><span aria-hidden="true">&#8250;</span></button></div></article>`;
}

// Return catalog descriptors matching the active search and category filters.
function filteredGames() {
  // Normalize user search text for stable case-insensitive matching.
  const query = lobbySearch.trim().toLocaleLowerCase();
  // Filter the catalog across human labels, descriptions, tags, and category metadata.
  return gameDescriptors.filter(game => {
    // Require membership in the selected category unless all categories are active.
    const categoryMatch = lobbyCategory === 'all' || game.categories.includes(lobbyCategory);
    // Build one searchable text surface from module-owned catalog metadata.
    const searchText = [game.label, game.description, ...game.tags, ...game.categories].join(' ').toLocaleLowerCase();
    // Keep only games satisfying both scalable navigation facets.
    return categoryMatch && (!query || searchText.includes(query));
  });
}

// Resolve a player-facing localized label for one internal catalog category identifier.
function categoryLabel(category) {
  // Use the dedicated all-games copy for the synthetic category that is not owned by a game.
  if (category === 'all') return t('catalog.allGames', {}, 'shell');
  // Resolve installed category identifiers through explicit shell locale resources without title-casing internal ids.
  return t(`catalog.category.${category}`, {}, 'shell');
}

// Render the full premium lobby with hero, status rail, and all current games.
function lobbyHtml(state = latestState) {
  // Count the available games from API state while falling back to the frontend registry.
  const gameCount = Array.isArray(state?.games) ? state.games.length : gameDescriptors.length;
  // Read privacy-safe recent presence instead of counting durable player records. (issue #570)
  const onlinePlayerCount = Number.isInteger(state?.online_player_count) ? state.online_player_count : 0;
  // Render the filtered game card collection from the API catalog.
  const visibleGames = filteredGames();
  // Render a helpful empty state when no catalog entry matches both filters.
  const cards = visibleGames.length ? visibleGames.map(game => lobbyCardHtml(game)).join('') : `<p class="catalog-empty" data-testid="catalog-empty">${safe(t('catalog.empty', {}, 'shell'))}</p>`;
  // Derive category navigation from catalog metadata so the 20-game target needs no shell edits.
  const categories = [...new Set(gameDescriptors.flatMap(game => game.categories))].sort();
  // Render one accessible category control per discovered category plus the all-games view.
  const categoryButtons = ['all', ...categories].map(category => `<button type="button" class="catalog-category${lobbyCategory === category ? ' active' : ''}" data-catalog-category="${safe(category)}" aria-pressed="${lobbyCategory === category}">${safe(categoryLabel(category))}</button>`).join('');
  // Render the premium trust rail with play-token, bot, autoplay, and ledger cues.
  const trustRail = [trustItemHtml('SIM', 'Local Simulator', 'All play tokens'), trustItemHtml('LIVE', t('status.online', { count: onlinePlayerCount }, 'shell'), t('lobby.presenceDetail', {}, 'shell')), trustItemHtml('AUTO', 'Autoplay Ready', 'Control-plane automation'), trustItemHtml('LED', 'Ledger-Backed', `${gameCount} games tracked`)].join('');
  // Return the complete lobby markup as one route payload.
  return `<section class="lobby" data-testid="lobby"><section class="lobby-hero" aria-label="Lobby introduction"><div><p class="eyebrow">${safe(t('lobby.chooseTable', {}, 'shell'))}</p><h1 class="hero-title">${safe(activeBrand.venue)}</h1><div class="hero-rule"><span>${safe(activeBrand.mark)}</span></div></div><aside class="trust-rail" data-testid="lobby-trust-rail" aria-label="Casino status">${trustRail}</aside></section><section class="catalog-region" data-testid="catalog-region" aria-label="${safe(t('catalog.controlsAria', {}, 'shell'))}"><section class="catalog-controls" data-testid="catalog-controls"><label class="catalog-search-label" for="catalog-search">${safe(t('catalog.searchLabel', {}, 'shell'))}</label><input id="catalog-search" data-testid="catalog-search" type="search" value="${safe(lobbySearch)}" placeholder="${safe(t('catalog.searchPlaceholder', {}, 'shell'))}"><div class="catalog-categories" data-testid="catalog-categories" aria-label="${safe(t('catalog.categoriesAria', {}, 'shell'))}">${categoryButtons}</div><p class="catalog-capacity" data-testid="catalog-capacity">${safe(t('catalog.capacity', { current: gameCount }, 'shell'))}</p></section><section class="game-gallery" data-testid="game-gallery" aria-label="${safe(t('catalog.galleryAria', {}, 'shell'))}">${cards}</section></section></section>`;
}

// Render lobby markup and wire its catalog-driven controls after every filter change.
function renderLobby(view, focusSearch = false) {
  // Replace the lobby atomically so card and category counts cannot drift.
  view.innerHTML = lobbyHtml(latestState);
  // Read the search input rendered by the current catalog state.
  const search = view.querySelector('[data-testid="catalog-search"]');
  // Update search state and rerender matching cards for each user edit.
  search.oninput = () => { lobbySearch = search.value; renderLobby(view, true); };
  // Wire every discovered category to the same filtered catalog render.
  view.querySelectorAll('[data-catalog-category]').forEach(button => { button.onclick = () => { lobbyCategory = button.dataset.catalogCategory; renderLobby(view); }; });
  // Wire each visible game card to its canonical route.
  view.querySelectorAll('[data-open-game]').forEach(button => { button.onclick = () => navigate(button.dataset.openGame); });
  // Restore search focus and caret after the filter rerender.
  if (focusSearch) { search.focus(); search.setSelectionRange(search.value.length, search.value.length); }
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
    // Load the game class through the module registry.
    const game = await loadGame(desc);
    // Mount the game into the same route outlet used by the original app.
    await game.mount(view);
    // Prepare shared game rails for intentional keyboard and touch scrolling.
    observeGameScrollRegions(view);
    // Refresh the authenticated token wallet after route mount.
    updateCurrentUserShell();
  // Handle navigation errors with a route-local recovery panel.
  } catch (err) {
    // Convert any protected-route auth failure into the logged-out recovery gate instead of a stale game error panel.
    if (err?.code === 'UNAUTHORIZED') { renderExpiredSessionGate(); return; }
    // Write diagnostic output so the current operation can be inspected.
    console.error(err);
    // Record the navigation failure with route context.
    await logClient('navigation_error', { route: targetRoute, message: err.message, stack: err.stack });
    // Read the route outlet for the fallback panel.
    const view = document.getElementById('view');
    // Keep a failed game route out of the lobby-only flex containment contract.
    document.body.classList.remove('lobby-active');
    // Remove the lobby-only test identity from the game error surface.
    view.removeAttribute('data-testid');
    // Keep the route outlet in game-screen mode so the error panel has premium shell padding.
    view.className = 'screen game-screen';
    // Render a friendly error state with a lobby recovery action.
    view.innerHTML = `<div class="panel loading-panel"><h2>Could not load ${safe(routeLabel(targetRoute))}</h2><p class="status">${safe(err.message)}</p><button data-route="lobby">Back to lobby</button></div>`;
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
  onLocaleChange(() => { localizeFeedback(); if (currentSession && !currentSession.terms?.required) { gameDescriptors = (latestState?.games || []).map(game => descriptorFromCatalog(game)); renderNav(); updateCurrentUserShell(); updateShellStatus(latestState, shellConnected); if (active === 'lobby') navigate('lobby', { history: 'none' }); } });
  // Restore game routes through browser Back and Forward without remounting stale history entries.
  window.addEventListener('popstate', () => { if (currentSession && !currentSession.terms?.required) navigate(routeFromLocation(), { history: 'none' }); });
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
    toast(`Could not load state: ${err.message}`);
    // Record the initial load failure for Admin telemetry.
    await logClient('initial_state_error', { message: err.message });
  }
  // Poll shell state periodically for connection and player-count status.
  setInterval(() => { if (currentSession && !currentSession.terms?.required) refreshShellState({ quiet: true }); }, 30000);
}

// Start the premium shell controller.
init();
