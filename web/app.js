// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can call the frozen API envelope safely.
import { acceptTerms, addUserTokens, api, currentUser, endGuestTrial, guestTrial, logClient, login, logout } from './core/api.js';
// Import required dependency so this module can render shared wallet and premium UI helpers.
import { renderTokenBalance, toast, tokens, safe, renderPremiumTag } from './core/ui.js';
// Import required dependency so the shell can preserve locale across auth and route changes.
import { getLocaleState, initI18n, onLocaleChange, setLocale, t } from './core/i18n.js';
// Import required dependency so this module can preload global voice settings before games mount.
import { loadVoiceSettings } from './core/voice.js';

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
// Track the active game-rail observer so navigation never leaves duplicate mutation listeners.
let gameRailObserver = null;
// Track the current lobby search without encoding transient filters into game routes.
let lobbySearch = '';
// Track the selected scalable catalog category.
let lobbyCategory = 'all';

// Relay game/autoplay toast events through the shell-level toast outlet.
window.addEventListener('casino-toast', event => toast(event.detail?.message || 'Auto stopped'));
// Keep the shell's private session cache synchronized when game helpers refresh current-user state.
window.addEventListener('casino-current-user', event => { currentSession = normalizeCurrentUser(event.detail); });
// Report top-level browser errors through the client log API for admin visibility.
window.addEventListener('error', event => logClient('window_error', { message: event.message, filename: event.filename, lineno: event.lineno, colno: event.colno }));
// Report unhandled promise rejections through the client log API for admin visibility.
window.addEventListener('unhandledrejection', event => logClient('unhandled_rejection', { reason: String(event.reason?.message || event.reason) }));

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

// Resolve the route represented by the current browser location for reload and history restoration.
function routeFromLocation() {
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

// Synchronize browser history with one resolved catalog route.
function updateRouteHistory(route, mode = 'push') {
  // Resolve the canonical path from catalog metadata or the lobby root.
  const path = route === 'lobby' ? '/' : gameDescriptors.find(game => game.id === route)?.route || '/';
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

// Keep persistent shell profile and wallet nodes synchronized with the current user.
function updateCurrentUserShell() {
  // Expose the current-user session so legacy game refresh calls keep token formatting.
  window.CasinoCurrentUser = currentSession;
  // Render the fake-token balance with the required token glyph.
  const amount = renderTokenBalance(currentSession);
  // Read the logout button reserved by index.html.
  const logoutButton = document.getElementById('logout-btn');
  // Read the best available display name for the authenticated user.
  const name = currentSession?.user?.display_name || currentSession?.user?.username || currentSession?.user?.email || 'Player';
  // Label the logout control with the current user for accessibility.
  if (logoutButton) logoutButton.setAttribute('aria-label', t('auth.logout', { name }, 'shell'));
  // Present the disposable-guest affordance on the persistent control: an End-trial label and a testable guest marker. (issue #317)
  if (logoutButton) {
    // Read the guest state once so the label and markers stay consistent.
    const guest = isGuestSession();
    // Show End trial for a guest without disturbing the registered-user control's existing content.
    if (guest) logoutButton.textContent = t('guest.endTrial', {}, 'shell');
    // Expose the guest identity and action for accessibility and browser evidence without leaking any credential.
    logoutButton.setAttribute('aria-label', guest ? t('guest.endTrial', {}, 'shell') : t('auth.logout', { name }, 'shell'));
    // Stamp a stable guest marker the shell and tests can read.
    logoutButton.setAttribute('data-guest-trial', guest ? 'true' : 'false');
  }
  // Read the language selector in the persistent topbar.
  const localeSelect = document.getElementById('shell-locale-select');
  // Wire the persistent locale selector without remounting games.
  wireLocaleSelect(localeSelect, () => { renderNav(); if (active === 'lobby') navigate('lobby'); });
  // Localize the persistent brand and wallet labels that remain mounted across routes.
  setStatusText('shell-brand-title', t('brand.title', {}, 'shell'));
  // Keep the compact subtitle aligned with the selected shell locale.
  setStatusText('shell-brand-subtitle', t('brand.subtitle', {}, 'shell'));
  // Localize the visible wallet balance caption.
  setStatusText('balance-label', t('wallet.balanceLabel', {}, 'shell'));
  // Localize the wallet popover field label.
  setStatusText('add-token-label', t('wallet.addTokens', {}, 'shell'));
  // Localize the wallet submit action.
  setStatusText('add-token-btn', t('wallet.add', {}, 'shell'));
  // Localize the wallet menu's accessible name.
  document.getElementById('wallet-menu-summary')?.setAttribute('aria-label', t('wallet.addTokens', {}, 'shell'));
  // Localize the language selector's accessible name.
  localeSelect?.setAttribute('aria-label', t('language.aria', {}, 'shell'));
  // Return the rendered token amount for test and toast flows.
  return amount;
}

// Render a logged-out browser gate before any casino route can mount.
function renderLoginGate(message = '') {
  // Clear the public current-user hook while the browser is logged out.
  window.CasinoCurrentUser = null;
  // Mark the document so chrome and game routes stay hidden while logged out.
  document.body.classList.add('auth-locked');
  // Read the main route outlet reserved by index.html.
  const view = document.getElementById('view');
  // Apply the auth screen class contract for login and terms flows.
  view.className = 'screen auth-screen';
  // Render the browser login gate with private-beta toy-simulator acknowledgement.
  view.innerHTML = `<section class="auth-panel" data-testid="login-gate"><p class="eyebrow">${safe(t('auth.eyebrow', {}, 'shell'))}</p><h1>${safe(t('auth.title', {}, 'shell'))}</h1><p class="auth-copy">${safe(t('auth.copy', {}, 'shell'))}</p><form id="login-form" class="auth-form"><label>${safe(t('auth.email', {}, 'shell'))}<input id="login-email" data-testid="login-email" type="email" autocomplete="username" required></label><label>${safe(t('auth.password', {}, 'shell'))}<input id="login-password" data-testid="login-password" type="password" autocomplete="current-password" required></label><label>${safe(t('auth.language', {}, 'shell'))}<select id="auth-locale-select" data-testid="auth-locale-select"></select></label><label class="check-row"><input id="login-terms-check" data-testid="login-terms-check" type="checkbox" required><span>${safe(t('auth.termsCheck', {}, 'shell'))}</span></label><button class="primary" data-testid="login-submit" type="submit">${safe(t('auth.submit', {}, 'shell'))}</button><p id="auth-message" class="auth-message">${safe(message)}</p></form><div class="auth-guest" data-testid="guest-trial"><button class="secondary" data-testid="guest-trial-button" type="button">${safe(t('auth.guestCta', {}, 'shell'))}</button><p class="auth-guest-copy" data-testid="guest-trial-copy">${safe(t('auth.guestInfo', {}, 'shell'))}</p></div><section class="oauth-provider-status" data-testid="oauth-providers-disabled" aria-labelledby="oauth-provider-heading"><h2 id="oauth-provider-heading">${safe(t('auth.oauthDivider', {}, 'shell'))}</h2><div class="oauth-provider-grid"><button class="oauth-provider-button" data-testid="oauth-google" type="button" disabled aria-disabled="true">${safe(t('auth.oauthGoogle', {}, 'shell'))}</button><button class="oauth-provider-button" data-testid="oauth-facebook" type="button" disabled aria-disabled="true">${safe(t('auth.oauthFacebook', {}, 'shell'))}</button></div><p class="oauth-provider-copy" data-testid="oauth-provider-message" role="status">${safe(t('auth.oauthUnavailable', {}, 'shell'))}</p></section></section>`;
  // Wire the auth-screen locale selector and rerender the gate after switching.
  wireLocaleSelect(document.getElementById('auth-locale-select'), () => renderLoginGate(message));
  // Wire form submission through the v2 auth login endpoint.
  document.getElementById('login-form').onsubmit = handleLoginSubmit;
  // Wire the account-free guest-trial entry so a visitor can start a disposable session without login. (issue #317)
  const guestButton = document.getElementById('guest-trial-button');
  // Start a guest trial on click only when the configuration-driven button is present.
  if (guestButton) guestButton.onclick = handleGuestTrial;
}

// Render the terms acceptance step when the current session still requires it.
function renderTermsGate(session) {
  // Store the current session so accepted terms can continue into the shell.
  currentSession = session;
  // Mark the document so chrome and game routes stay hidden until terms are accepted.
  document.body.classList.add('auth-locked');
  // Read the main route outlet reserved by index.html.
  const view = document.getElementById('view');
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
  // Store the normalized current user for shell rendering.
  currentSession = normalizeCurrentUser(session);
  // Branch to terms acceptance before showing the casino shell.
  if (currentSession.terms?.required) { renderTermsGate(currentSession); return; }
  // Load Admin-owned persisted voice settings only when this authenticated identity may read them.
  if (currentSession.user?.role === 'admin') await loadVoiceSettings();
  // Reveal the casino chrome now that the browser session is authenticated.
  document.body.classList.remove('auth-locked');
  // Update the persistent wallet, logout, and locale controls.
  updateCurrentUserShell();
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
    // Create the isolated disposable guest session through the public guest endpoint.
    const session = await guestTrial();
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
  // Handle missing or expired sessions by showing the browser login gate.
  } catch (_) {
    // Clear the current session so no stale wallet can render.
    currentSession = null;
    // Render the logged-out gate before any route mounts.
    renderLoginGate();
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
function renderNav() {
  // Read the navigation outlet that index.html reserves for route buttons.
  const nav = document.getElementById('main-nav');
  // Build the lobby button with the active shell class when selected.
  const items = [`<button data-route="lobby" class="nav-item ${active === 'lobby' ? 'active' : ''}" data-testid="nav-lobby"><span class="nav-icon" aria-hidden="true">&#8962;</span>${safe(t('nav.lobby', {}, 'shell'))}</button>`];
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
  // Count visible players so the lobby trust rail reflects the local casino state.
  const playerCount = Array.isArray(state?.players) ? state.players.length : 0;
  // Render the filtered game card collection from the API catalog.
  const visibleGames = filteredGames();
  // Render a helpful empty state when no catalog entry matches both filters.
  const cards = visibleGames.length ? visibleGames.map(game => lobbyCardHtml(game)).join('') : `<p class="catalog-empty" data-testid="catalog-empty">${safe(t('catalog.empty', {}, 'shell'))}</p>`;
  // Derive category navigation from catalog metadata so the 20-game target needs no shell edits.
  const categories = [...new Set(gameDescriptors.flatMap(game => game.categories))].sort();
  // Render one accessible category control per discovered category plus the all-games view.
  const categoryButtons = ['all', ...categories].map(category => `<button type="button" class="catalog-category${lobbyCategory === category ? ' active' : ''}" data-catalog-category="${safe(category)}" aria-pressed="${lobbyCategory === category}">${safe(categoryLabel(category))}</button>`).join('');
  // Read the approved target count from the additive API catalog summary.
  const targetCount = state?.catalog?.target_game_count || gameCount;
  // Render the premium trust rail with play-token, bot, autoplay, and ledger cues.
  const trustRail = [trustItemHtml('SIM', 'Local Simulator', 'All play tokens'), trustItemHtml('BOT', `${playerCount} Players`, 'Human and bots'), trustItemHtml('AUTO', 'Autoplay Ready', 'Control-plane automation'), trustItemHtml('LED', 'Ledger-Backed', `${gameCount} games tracked`)].join('');
  // Return the complete lobby markup as one route payload.
  return `<section class="lobby" data-testid="lobby"><section class="lobby-hero" aria-label="Lobby introduction"><div><p class="eyebrow">${safe(t('lobby.chooseTable', {}, 'shell'))}</p><h1 class="hero-title">Midnight Ledger Casino</h1><div class="hero-rule"><span>&#9824;</span></div></div><aside class="trust-rail" data-testid="lobby-trust-rail" aria-label="Casino status">${trustRail}</aside></section><section class="catalog-region" data-testid="catalog-region" aria-label="${safe(t('catalog.controlsAria', {}, 'shell'))}"><section class="catalog-controls" data-testid="catalog-controls"><label class="catalog-search-label" for="catalog-search">${safe(t('catalog.searchLabel', {}, 'shell'))}</label><input id="catalog-search" data-testid="catalog-search" type="search" value="${safe(lobbySearch)}" placeholder="${safe(t('catalog.searchPlaceholder', {}, 'shell'))}"><div class="catalog-categories" data-testid="catalog-categories" aria-label="${safe(t('catalog.categoriesAria', {}, 'shell'))}">${categoryButtons}</div><p class="catalog-capacity" data-testid="catalog-capacity">${safe(t('catalog.capacity', { current: gameCount, target: targetCount }, 'shell'))}</p></section><section class="game-gallery" data-testid="game-gallery" aria-label="${safe(t('catalog.galleryAria', {}, 'shell'))}">${cards}</section></section></section>`;
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
  // Resolve player count text from the state payload.
  const players = t('status.online', { count: Array.isArray(state?.players) ? state.players.length : 0 }, 'shell');
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
    // Read the frozen v1 casino state envelope.
    const state = await api('/api/v1/casino/state');
    // Cache the state for lobby rendering and later refreshes.
    latestState = state;
    // Rebuild frontend registration from the same public catalog used by backend registration.
    gameDescriptors = (state.games || []).map(game => descriptorFromCatalog(game));
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

// Navigate between lobby and game routes while keeping one mounted game at a time.
export async function navigate(route, options = {}) {
  // Branch when an unauthenticated browser tries to navigate before the auth gate is complete.
  if (!currentSession || currentSession.terms?.required) return;
  // Store the requested route for error reporting.
  let targetRoute = route;
  // Start protected navigation so failures render inside the route outlet.
  try {
    // Store the previous route so mounted games can unmount before route changes.
    const previous = active;
    // Check whether the requested route is one of the registered games.
    const knownGame = gameDescriptors.some(game => game.id === route);
    // Fall back to lobby for unknown routes.
    targetRoute = route === 'lobby' || knownGame ? route : 'lobby';
    // Synchronize normal navigation, initial restoration, or invalid-route replacement with browser history.
    if (options.history !== 'none') updateRouteHistory(targetRoute, options.history || (knownGame || route === 'lobby' ? 'push' : 'replace'));
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
      // Apply the lobby screen class contract for responsive shell styling.
      view.className = 'screen lobby-screen';
      // Drop the game-outlet scroll-region semantics so the lobby uses natural document flow.
      view.removeAttribute('tabindex'); view.removeAttribute('role'); view.removeAttribute('aria-label');
      // Render lobby markup and catalog controls from the cached API state.
      renderLobby(view);
      // Stop after lobby render because no game module is mounted.
      return;
    }
    // Apply the game screen class contract before mounting a game module.
    view.className = 'screen game-screen';
    // Make the bounded game outlet a keyboard-focusable scroll region so every control stays reachable. (issue #221)
    view.tabIndex = 0; view.setAttribute('role', 'region'); view.setAttribute('aria-label', safe(t('nav.gamesArea', {}, 'shell') || 'Game area'));
    // Render a premium loading panel while the dynamic game module loads.
    view.innerHTML = `<div class="panel loading-panel"><h2>Loading ${safe(routeLabel(targetRoute))}...</h2></div>`;
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
    // Write diagnostic output so the current operation can be inspected.
    console.error(err);
    // Record the navigation failure with route context.
    await logClient('navigation_error', { route: targetRoute, message: err.message, stack: err.stack });
    // Read the route outlet for the fallback panel.
    const view = document.getElementById('view');
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
  // Initialize i18n before any auth or shell markup renders.
  await initI18n({ domains: ['shell'] });
  // Recalculate active-route visibility whenever responsive navigation layout changes.
  window.addEventListener('resize', revealActiveNav);
  // Repaint persistent shell text when the locale changes.
  onLocaleChange(() => { if (currentSession && !currentSession.terms?.required) { gameDescriptors = (latestState?.games || []).map(game => descriptorFromCatalog(game)); renderNav(); updateCurrentUserShell(); updateShellStatus(latestState, shellConnected); if (active === 'lobby') navigate('lobby', { history: 'none' }); } });
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
      // Refresh shell state so status rail counts stay current.
      await refreshShellState({ quiet: true });
      // Close the wallet popover after a successful token addition.
      document.querySelector('.wallet-menu')?.removeAttribute('open');
      // Clear the amount so an accidental second click cannot silently re-add the same top-up. (issue #247)
      document.getElementById('add-token-amount').value = '';
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
    // Start protected teardown so a stale session still ends locally on any backend error.
    try { await (guestSession ? endGuestTrial() : logout()); } catch (_) {}
    // Clear the current session after the backend teardown attempt completes.
    currentSession = null;
    // Clear the public current-user hook after teardown.
    window.CasinoCurrentUser = null;
    // Reset the active route so a later entry starts at the lobby.
    active = null;
    // Return to the login gate, noting the ended guest trial where applicable.
    renderLoginGate(t(guestSession ? 'auth.loggedOut' : 'auth.loggedOut', {}, 'shell'));
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
