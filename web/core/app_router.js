// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Own catalog routing, lazy game mounts, and route accessibility outside app composition. (CORE-007, SESSION-013)

// Import owned-route and escape-by-default rendering helpers from the shared UI boundary.
import { awaitOwnedRouteEffect, html, mountOwnedRoute } from './ui.js';

// Create one application router around shell-owned state adapters and extracted views.
export function createAppRouter(dependencies) {
  // Capture browser, shell-state, lifecycle, rendering, and diagnostics seams.
  const {
    documentRef, getActive, getCurrentSession, getGameDescriptors, historyRef,
    isInvitationRoute, locationRef, logClient, navigationOwnership,
    renderExpiredSessionGate, renderLobby, renderMySettings, renderPublicAuthRoute,
    safe, setActive, setLocale, t, updateCurrentUserShell, walletLifecycle,
    windowRef,
  } = dependencies;
  // Cache loaded game module exports for the application lifetime.
  const loadedGames = new Map();
  // Track the active game-rail observer so navigation never leaves duplicate listeners.
  let gameRailObserver = null;

  // Convert one public API catalog row into the shell route descriptor.
  function descriptorFromCatalog(game) {
    // Read locale-owned metadata from the independently owned game descriptor.
    const localized = dependencies.getLocaleState().locale ? game.translations?.[dependencies.getLocaleState().locale] || {} : {};
    // Read nested lobby metadata while tolerating additive future fields.
    const lobby = game.lobby || {};
    // Return the exact shape consumed by navigation, search, cards, and lazy imports.
    return {
      id: game.id,
      route: game.route || `/games/${game.id}`,
      label: localized.label || game.label,
      category: game.category,
      categories: game.categories || [game.category],
      path: game.frontend?.module,
      exportName: game.frontend?.export,
      readyTestId: game.frontend?.ready_testid,
      i18nDomain: game.frontend?.i18n_domain,
      i18nProbe: game.frontend?.i18n_probe,
      featured: lobby.featured === true,
      wide: lobby.wide === true,
      artClass: lobby.art_class || '',
      symbol: lobby.symbol || '',
      kicker: localized.kicker || lobby.kicker || game.category,
      description: localized.description || lobby.description || '',
      tags: localized.tags || lobby.tags || [],
    };
  }

  // Resolve a human-readable game title for status panels. (issue #254)
  function routeLabel(route) {
    // Return the catalog display label when known, else the raw route slug.
    return getGameDescriptors().find(game => game.id === route)?.label || route;
  }

  // Resolve a route label before the casino catalog finishes hydrating. (PWA-002)
  function routeFallbackLabel(route) {
    // Prefer the live catalog label once casino state has populated descriptors.
    const catalogLabel = routeLabel(route);
    // Return the catalog label when it has resolved beyond the raw route id.
    if (catalogLabel !== route) return catalogLabel;
    // Resolve the already-loaded static shell translation without waiting for state.
    const labelKey = `games.${route}.label`;
    const resourceLabel = t(labelKey, {}, 'shell');
    // Return the localized static label when a resource exists.
    if (resourceLabel !== labelKey) return resourceLabel;
    // Convert future slugs into readable fallback words.
    return route.split(/[_-]+/).filter(Boolean).map(part => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`).join(' ') || route;
  }

  // Resolve the route represented by the current browser location.
  function routeFromLocation() {
    // Restore the distinct authenticated My Settings destination.
    if (locationRef.pathname.replace(/\/$/, '') === '/settings') return 'settings';
    // Match canonical reloadable game paths without nested segments.
    const match = locationRef.pathname.match(/^\/games\/([^/]+)\/?$/);
    // Decode the matched id so comparison uses catalog identifiers.
    if (match) return decodeURIComponent(match[1]);
    // Preserve a compatible hash deep link only when the catalog recognizes it.
    const hashRoute = locationRef.hash.replace(/^#\/?/, '');
    if (getGameDescriptors().some(game => game.id === hashRoute)) return hashRoute;
    // Treat every non-game static path as the lobby route.
    return 'lobby';
  }

  // Show a real restoration surface before slow session and casino-state calls. (PWA-002)
  function renderInitialRouteRestore() {
    // Read the browser-owned route before authenticated state hydrates the catalog.
    const restoredRoute = routeFromLocation();
    // Leave lobby and invitation startup paths unchanged.
    if (restoredRoute === 'lobby' || isInvitationRoute()) return;
    // Read the route outlet that can otherwise sit blank during revalidation.
    const view = documentRef.getElementById('view');
    // Stop when malformed static load omitted the outlet.
    if (!view) return;
    // Resolve a player-facing game label without delayed state.
    const gameLabel = routeFallbackLabel(restoredRoute);
    // Apply the authenticated game-region semantics to the placeholder.
    documentRef.body.classList.remove('lobby-active');
    view.className = 'screen game-screen';
    view.removeAttribute('data-testid');
    view.tabIndex = 0;
    view.setAttribute('role', 'region');
    view.setAttribute('aria-label', safe(t('nav.gamesArea', {}, 'shell') || 'Game area'));
    // Render localized progress through the escape-by-default boundary.
    const eyebrow = html`<p class="eyebrow">${t('routeRestore.eyebrow', {}, 'shell')}</p>`;
    const heading = html`<h2>${t('routeRestore.title', { game: gameLabel }, 'shell')}</h2>`;
    const status = html`<p class="status">${t('routeRestore.copy', {}, 'shell')}</p>`;
    view.innerHTML = html`<div class="panel loading-panel" data-testid="route-restore-loading">${eyebrow}${heading}${status}</div>`;
  }

  // Synchronize browser history with one resolved catalog route.
  function updateRouteHistory(route, mode = 'push') {
    // Resolve canonical path from settings, lobby, or catalog metadata.
    const path = route === 'settings' ? '/settings' : route === 'lobby' ? '/' : getGameDescriptors().find(game => game.id === route)?.route || '/';
    // Preserve approved query parameters while removing legacy hashes.
    const url = new URL(locationRef.href);
    url.pathname = path;
    url.hash = '';
    // Avoid duplicate history entries for the current URL.
    if (locationRef.pathname === url.pathname && locationRef.hash === url.hash) return;
    // Replace initial/invalid routes and push normal navigation.
    historyRef[mode === 'replace' ? 'replaceState' : 'pushState']({ route }, '', `${url.pathname}${url.search}`);
  }

  // Render locale options from the loaded manifest through the tagged template.
  function localeOptionsHtml() {
    // Return one escaped option fragment for every enabled UI locale.
    return html`${(dependencies.getLocaleState().locales || []).map(locale => html`<option value="${locale.id}">${locale.nativeLabel || locale.label || locale.id}</option>`)}`;
  }

  // Wire a locale selector while preserving current auth or route state.
  function wireLocaleSelect(select, afterChange) {
    // Stop when the selector is absent from the current screen.
    if (!select) return;
    // Fill options before selecting the current locale.
    select.innerHTML = html`${localeOptionsHtml()}`;
    select.value = dependencies.getLocaleState().locale;
    // Switch language in place without resetting active state.
    select.onchange = async () => { await setLocale(select.value); afterChange?.(); };
  }

  // Make intentional game-rail scrolling discoverable to keyboard and assistive technology.
  function prepareGameScrollRegions(view) {
    // Find shared control and data rails rendered by the active game.
    view.querySelectorAll('.control-rail, .details-drawer').forEach(region => {
      // Include the intentional scroll region in natural keyboard order.
      region.tabIndex = 0;
      // Identify each rail as a navigable document region.
      region.setAttribute('role', 'region');
      // Read the first visible heading so the region has a useful name.
      const heading = region.querySelector('h1, h2, h3');
      // Label from owned content with a safe fallback.
      region.setAttribute('aria-label', heading?.textContent?.trim() || 'Game panel');
    });
  }

  // Preserve scroll-region semantics across game-owned rerenders.
  function observeGameScrollRegions(view) {
    // Disconnect the previous route observer before watching the new route.
    gameRailObserver?.disconnect();
    // Apply semantics immediately to the first completed render.
    prepareGameScrollRegions(view);
    // Reapply semantics after structural replacements.
    gameRailObserver = new windowRef.MutationObserver(() => prepareGameScrollRegions(view));
    // Avoid observing attributes written by this helper.
    gameRailObserver.observe(view, { childList: true, subtree: true });
  }

  // Disconnect game-only observation before a non-game shell surface replaces it.
  function disconnectGameObserver() {
    // Stop the active observer when one exists.
    gameRailObserver?.disconnect();
  }

  // Load one catalog-owned frontend module with diagnostic failures.
  async function loadGame(desc) {
    // Return a cached export when this route was already loaded.
    if (loadedGames.has(desc.id)) return loadedGames.get(desc.id);
    // Start protected import logic so failures are captured.
    try {
      // Import the owned frontend module by documented path.
      const mod = await import(desc.path);
      // Read the known game class export from its namespace.
      const game = mod[desc.exportName];
      // Cache the class for later navigation.
      loadedGames.set(desc.id, game);
      // Return the class to the navigation flow.
      return game;
    } catch (error) {
      // Record module load failure with bounded route context.
      await logClient('game_module_load_error', { game: desc.id, message: error.message, stack: error.stack });
      // Re-throw so navigation can render friendly recovery.
      throw error;
    }
  }

  // Center the active route inside the navigation viewport.
  function revealActiveNav() {
    // Read the persistent navigation outlet.
    const nav = documentRef.getElementById('main-nav');
    // Stop before authentication exposes shared navigation.
    if (!nav) return;
    // Read the active catalog route after layout is measurable.
    const activeItem = nav.querySelector('.nav-item.active');
    // Stop when no active route exists.
    if (!activeItem) return;
    // Measure both nodes in the same viewport coordinates.
    const navBounds = nav.getBoundingClientRect();
    const itemBounds = activeItem.getBoundingClientRect();
    // Center the active route from its rendered displacement.
    nav.scrollLeft += itemBounds.left - navBounds.left - ((navBounds.width - itemBounds.width) / 2);
  }

  // Render premium top navigation from the route registry.
  function renderNav() {
    // Read the persistent navigation outlet.
    const nav = documentRef.getElementById('main-nav');
    // Build lobby and personal-settings routes first.
    const active = getActive();
    const lobbyIcon = html`<span class="nav-icon" aria-hidden="true">&#8962;</span>`;
    const items = [html`<button data-route="lobby" class="nav-item ${active === 'lobby' ? 'active' : ''}" data-testid="nav-lobby">${lobbyIcon}${t('nav.lobby', {}, 'shell')}</button>`];
    items.push(html`<button data-route="settings" class="nav-item ${active === 'settings' ? 'active' : ''}" data-testid="nav-settings">${t('settings.title', {}, 'shell')}</button>`);
    // Add one escaped button per game so every game stays reachable.
    getGameDescriptors().forEach(game => items.push(html`<button data-route="${game.id}" class="nav-item ${active === game.id ? 'active' : ''}" data-testid="nav-${game.id}">${game.label}</button>`));
    // Expose Admin only when the current-user contract carries that role. (AUTH-008)
    if (getCurrentSession()?.user?.role === 'admin') items.push(html`<button data-admin="true" class="nav-item admin" data-testid="nav-admin">${t('nav.admin', {}, 'shell')}</button>`);
    // Replace contents atomically so active state cannot drift.
    nav.innerHTML = html`${items}`;
    // Expose the menu as one keyboard-focusable horizontal region.
    nav.tabIndex = 0;
    nav.setAttribute('role', 'group');
    nav.setAttribute('aria-label', safe(t('nav.primaryAria', {}, 'shell') || 'Games navigation'));
    // Let keyboard users pan the bounded menu.
    nav.onkeydown = event => {
      // Read viewport width for one-page horizontal steps.
      const step = Math.max(160, nav.clientWidth * 0.8);
      // Apply reviewed arrow and edge-key navigation.
      if (event.key === 'ArrowRight') { nav.scrollLeft += step; event.preventDefault(); }
      else if (event.key === 'ArrowLeft') { nav.scrollLeft -= step; event.preventDefault(); }
      else if (event.key === 'Home') { nav.scrollLeft = 0; event.preventDefault(); }
      else if (event.key === 'End') { nav.scrollLeft = nav.scrollWidth; event.preventDefault(); }
    };
    // Reveal the active route after each render.
    revealActiveNav();
    // Wire every route button to shared navigation.
    nav.querySelectorAll('[data-route]').forEach(button => { button.onclick = () => navigate(button.dataset.route); });
    // Wire the protected Admin destination only when exposed.
    const adminButton = nav.querySelector('[data-admin]');
    if (adminButton) adminButton.onclick = () => { locationRef.href = '/admin'; };
  }

  // Navigate between Lobby, Settings, and games while keeping one mounted game. (SESSION-013)
  async function navigate(route, options = {}) {
    // Stop unauthenticated or terms-incomplete navigation.
    if (!getCurrentSession() || getCurrentSession().terms?.required) return;
    // Claim a fresh epoch that supersedes every earlier pending route.
    const navigationTicket = navigationOwnership.claim();
    // Store the requested route for diagnostic reporting.
    let targetRoute = route;
    // End in-flight wallet presentation before route teardown.
    walletLifecycle.interrupt('navigation');
    // Start protected navigation so failures render inside the outlet.
    try {
      // Resolve previous and known routes from shell-owned state.
      const previous = getActive();
      const descriptors = getGameDescriptors();
      const knownGame = descriptors.some(game => game.id === route);
      const knownSettings = route === 'settings';
      // Fall back to Lobby for unknown routes.
      targetRoute = route === 'lobby' || knownSettings || knownGame ? route : 'lobby';
      // Synchronize browser history unless the caller owns restoration.
      if (options.history !== 'none') {
        // Choose push for known destinations and replace for invalid input.
        const historyMode = options.history || (knownGame || knownSettings || route === 'lobby' ? 'push' : 'replace');
        updateRouteHistory(targetRoute, historyMode);
      }
      // Unmount the previously active game when it supplied cleanup.
      if (previous && loadedGames.has(previous)) loadedGames.get(previous).unmount?.();
      // Publish the active route before rendering navigation.
      setActive(targetRoute);
      renderNav();
      // Read the persistent route outlet.
      const view = documentRef.getElementById('view');
      // Render Lobby without loading a game module.
      if (targetRoute === 'lobby') {
        // Stop game observation and apply bounded Lobby semantics.
        disconnectGameObserver();
        documentRef.body.classList.add('lobby-active');
        view.className = 'screen lobby-screen';
        view.tabIndex = 0;
        view.setAttribute('role', 'region');
        view.setAttribute('aria-label', safe(t('nav.lobby', {}, 'shell') || 'Lobby'));
        view.setAttribute('data-testid', 'lobby-scroll-region');
        // Render catalog controls from cached state.
        renderLobby(view);
        return;
      }
      // Render personal Settings without importing a game.
      if (targetRoute === 'settings') {
        // Stop game observation and apply bounded Settings semantics.
        disconnectGameObserver();
        documentRef.body.classList.remove('lobby-active');
        view.className = 'screen settings-screen';
        view.setAttribute('data-testid', 'settings-screen');
        view.tabIndex = 0;
        view.setAttribute('role', 'region');
        view.setAttribute('aria-label', safe(t('settings.title', {}, 'shell')));
        // Render caller-owned preferences, history, or conversion.
        await renderMySettings(view);
        // Restore a newer public route when Settings lost ownership.
        if (!navigationOwnership.owns(navigationTicket)) { renderPublicAuthRoute(); return; }
        return;
      }
      // Restore regular game-shell semantics.
      documentRef.body.classList.remove('lobby-active');
      view.className = 'screen game-screen';
      view.removeAttribute('data-testid');
      view.tabIndex = 0;
      view.setAttribute('role', 'region');
      view.setAttribute('aria-label', safe(t('nav.gamesArea', {}, 'shell') || 'Game area'));
      // Render escaped loading copy while the module resolves.
      view.innerHTML = html`<div class="panel loading-panel"><h2>${t('routeRestore.title', { game: routeLabel(targetRoute) }, 'shell')}</h2></div>`;
      // Resolve and mount the selected module only while ownership survives both awaits.
      const desc = descriptors.find(game => game.id === targetRoute);
      const mountedRoute = await mountOwnedRoute({
        // Resolve through the cached dynamic loader.
        load: () => loadGame(desc),
        // Mount into the persistent outlet.
        mount: game => game.mount(view),
        // Recheck the captured ticket across all boundaries.
        owns: () => navigationOwnership.owns(navigationTicket),
        // Unmount stale work and restore only the newer public route.
        onStale: (game, mountStarted) => { if (mountStarted) game?.unmount?.(); renderPublicAuthRoute(); },
      });
      // Stop before observers or wallet repaint when stale.
      if (mountedRoute.stale) return;
      // Prepare shared game rails and refresh authoritative wallet chrome.
      observeGameScrollRegions(view);
      updateCurrentUserShell();
    } catch (error) {
      // Never replace a newer public gate with stale route work.
      if (!navigationOwnership.owns(navigationTicket)) { renderPublicAuthRoute(); return; }
      // Convert protected-route auth failure into the logged-out recovery gate.
      if (error?.code === 'UNAUTHORIZED') { renderExpiredSessionGate(); return; }
      // Write diagnostics for local inspection.
      console.error(error);
      // Require ownership again after asynchronous diagnostic I/O.
      const ownsAfterLog = await awaitOwnedRouteEffect({
        // Publish only bounded route and error diagnostics.
        run: () => logClient('navigation_error', { route: targetRoute, message: error.message, stack: error.stack }),
        // Recheck the captured route ticket.
        owns: () => navigationOwnership.owns(navigationTicket),
        // Restore the newer public-account route on staleness.
        onStale: () => renderPublicAuthRoute(),
      });
      // Stop before outlet mutation when diagnostic completion was stale.
      if (!ownsAfterLog) return;
      // Render escaped friendly recovery inside the game outlet.
      const view = documentRef.getElementById('view');
      documentRef.body.classList.remove('lobby-active');
      view.removeAttribute('data-testid');
      view.className = 'screen game-screen';
      const heading = html`<h2>${t('route.loadFailed', { route: routeLabel(targetRoute) }, 'shell')}</h2>`;
      const status = html`<p class="status">${error.message}</p>`;
      const back = html`<button data-route="lobby">${t('route.backToLobby', {}, 'shell')}</button>`;
      view.innerHTML = html`<div class="panel loading-panel">${heading}${status}${back}</div>`;
      // Wire the fallback without depending on top navigation.
      view.querySelector('[data-route="lobby"]')?.addEventListener('click', () => navigate('lobby'));
    }
  }

  // Publish the reviewed routing and shared locale seams.
  return {
    descriptorFromCatalog,
    disconnectGameObserver,
    loadedGames,
    localeOptionsHtml,
    navigate,
    renderInitialRouteRestore,
    renderNav,
    revealActiveNav,
    routeFromLocation,
    wireLocaleSelect,
  };
}
