// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Own browser lifecycle wiring and application startup outside shell composition. (PWA-002, UX-026)

// Import shell-owned API actions used by persistent browser controls.
import { addUserTokens, departGuestTrial, endGuestTrial, logClient, logout } from './api.js';
// Import active brand initialization for first paint.
import { activeBrand, applyBrand } from './brand.js';
// Import problem-report lifecycle helpers for the persistent shell.
import { bindFeedbackDialog, localizeFeedback } from './feedback.js';
// Import locale initialization and change subscriptions.
import { initI18n, onLocaleChange, t } from './i18n.js';
// Import the offline-safe reconnect controller and route-render control synchronizer.
import { initPwa, synchronizeServerControls } from './pwa.js';
// Import containment, stable-render, feedback, and formatting helpers.
import { auditLayoutContainment, installStableRouteRenders, toast, tokens } from './ui.js';

// Normalize compatible current-user payloads without committing to backend internals.
export function normalizeCurrentUser(payload) {
  // Store standard envelopes and direct payloads through one shape.
  const data = payload?.current_user || payload || {};
  // Store user, player, and terms through compatible defaults.
  const user = data.user || {};
  const player = data.player || {};
  const terms = data.terms || user.terms || {};
  // Preserve early terms-required payload shapes.
  const required = typeof terms.required === 'boolean'
    ? terms.required
    : user.terms_required === true || data.terms_required === true || terms.accepted === false;
  // Return the normalized session consumed by shell rendering.
  return { ...data, user, player, terms: { ...terms, required } };
}

// Resolve the same play-token precedence used by the wallet renderer.
export function currentTokenBalance(session) {
  // Read normalized player and compatible user payloads.
  const player = session?.player || {};
  const user = session?.user || {};
  // Resolve established compatible token fields without rendered DOM text.
  const value = player.token_balance ?? player.tokens ?? user.token_balance ?? user.tokens ?? session?.token_balance ?? session?.tokens?.balance ?? 0;
  // Return the numeric value consumed by wallet presentation.
  return Number(value || 0);
}

// Own one server-authored pre-expiration warning without retaining session identity. (SESSION-012)
export function createSessionWarningController({ clearTimer, now, notify, setTimer }) {
  // Invalidate callbacks even when a host has already queued a timer while it is being cleared.
  let generation = 0;
  // Retain only the active host timer handle.
  let timer = null;

  // Cancel the current session generation before logout or replacement can expose stale copy.
  function dispose() {
    // Advance first so an already-queued callback cannot notify for the discarded session.
    generation += 1;
    // Clear only a timer this controller owns.
    if (timer !== null) clearTimer(timer);
    // Release the host handle after cancellation.
    timer = null;
  }

  // Schedule from the normalized server descriptor, never a browser-derived expiry estimate.
  function schedule(descriptor = {}) {
    // Replace any prior session or refresh before validating the new descriptor.
    dispose();
    // Stop when warning is disabled, absent, or already terminal.
    if (!descriptor.warn_at || Number(descriptor.warning_seconds || 0) <= 0 || Number(descriptor.expires_in_seconds || 0) <= 0) return false;
    // Preserve the existing host-safe delay clamp around the server-owned UTC instant.
    const delay = Math.max(0, Math.min(Date.parse(descriptor.warn_at) - now(), 2147483647));
    // Bind the callback to only this accepted descriptor generation.
    const ticket = generation;
    // Schedule localized informational copy; the next API remains authoritative for expiry.
    timer = setTimer(() => {
      // Ignore a callback retained by a replaced or disposed host timer queue.
      if (ticket !== generation) return;
      // Publish only the bounded display value already derived from server-authored seconds.
      notify(Math.max(1, Math.ceil(Number(descriptor.warning_seconds) / 60)));
    }, delay);
    // Report only whether one timer was accepted, never its host handle.
    return true;
  }

  // Expose lifecycle operations without session, clock, or timer mutation authority.
  return { dispose, schedule };
}

// Start global lifecycle listeners and initialize the authenticated shell once.
export async function startApplication(dependencies) {
  // Capture state adapters, controllers, and extracted routing seams.
  const {
    clearAuthenticatedShellState, descriptorFromCatalog, documentRef, getActive,
    getCurrentSession, getGameDescriptors, getLatestState, getShellConnected,
    isGuestSession, navigate, prepareRouteAfterRender, refreshAfterReconnect, refreshCurrentSession,
    refreshShellState, renderExpiredSessionGate, renderInitialRouteRestore,
    renderLoginGate, renderNav, renderPublicAuthRoute, revealActiveNav,
    routeFromLocation, setCurrentSession, setGameDescriptors,
    updateCurrentUserShell, updateShellStatus, walletLifecycle,
    wellnessController, windowRef,
  } = dependencies;

  // Relay game/autoplay toast events through the shell outlet.
  windowRef.addEventListener('casino-toast', event => toast(event.detail?.message || t('autoplay.stopped', {}, 'shell')));
  // Synchronize the private session cache when game helpers refresh current-user state.
  windowRef.addEventListener('casino-current-user', event => {
    // Normalize and adopt the exact payload before queued presentation work.
    const nextSession = normalizeCurrentUser(event.detail);
    setCurrentSession(nextSession);
    // Decorate only the exact latest server-settled amount.
    queueMicrotask(() => {
      // Ignore stale events after logout or replacement.
      if (getCurrentSession() !== nextSession) return;
      // Update celebration without writing wallet text again.
      walletLifecycle.update(currentTokenBalance(nextSession));
    });
  });
  // Report top-level browser errors through bounded client diagnostics.
  windowRef.addEventListener('error', event => logClient('window_error', { message: event.message, filename: event.filename, lineno: event.lineno, colno: event.colno }));
  // Report unhandled promise rejections through bounded client diagnostics.
  windowRef.addEventListener('unhandledrejection', event => logClient('unhandled_rejection', { reason: String(event.reason?.message || event.reason) }));
  // Mark guest page departure without ending same-context reloads.
  windowRef.addEventListener('pagehide', () => { if (isGuestSession()) void departGuestTrial().catch(() => {}); });
  // Reset stale authenticated chrome only while a session owns the shell.
  windowRef.addEventListener('casino-session-expired', () => { if (getCurrentSession()) renderExpiredSessionGate(); });
  // Replace any direct game-route startup loader as soon as the PWA boundary confirms offline state. (PWA-002)
  windowRef.addEventListener('casino-connectivity', event => {
    // Leave reconnecting and online transitions to the authoritative reconnect callback.
    if (event.detail?.state !== 'offline') return;
    // Re-evaluate only the current URL so offline startup cannot imply that a game module is still loading.
    renderInitialRouteRestore();
  });

  // Apply brand design tokens before first paint.
  applyBrand(activeBrand);
  // Initialize locale resources before auth or shell markup renders.
  await initI18n({ domains: ['shell', 'feedback'] });
  // Bind the problem-report dialog after its locale domain is ready.
  bindFeedbackDialog();
  // Register offline-safe shell reconnect handling.
  initPwa({ onReconnect: refreshAfterReconnect });
  // Publish reusable controller construction before authoritative readiness.
  windowRef.dispatchEvent(new CustomEvent('casino:shared-app-controller-ready'));
  // Render immediate route restoration during session hydration.
  renderInitialRouteRestore();
  // Recalculate active-route visibility across responsive layout changes.
  windowRef.addEventListener('resize', revealActiveNav);
  // Read the persistent route outlet for render stability and containment.
  const routeOutlet = documentRef.getElementById('view');
  // Retain bounded overflow telemetry state for this browser session.
  const reportedOverflowCells = new Set();
  let pendingOverflowKey = null;
  let layoutAuditTimer = null;
  // Measure settled layout twice before publishing bounded telemetry. (UX-026)
  const runLayoutAudit = () => {
    // Measure the live route through the shared auditor.
    const audit = auditLayoutContainment(routeOutlet);
    // Build one route-and-viewport cell identity.
    const cellKey = `${getActive() || 'none'}|${windowRef.innerWidth}x${windowRef.innerHeight}`;
    // Clear pending confirmation for fully contained layout.
    if (audit.docOverflow <= 4 && !audit.offenders.length) { pendingOverflowKey = null; return; }
    // Arm one delayed confirmation for a new overflow cell.
    if (pendingOverflowKey !== cellKey) { pendingOverflowKey = cellKey; layoutAuditTimer = setTimeout(runLayoutAudit, 1200); return; }
    // Keep reports bounded and de-duplicated.
    if (reportedOverflowCells.has(cellKey) || reportedOverflowCells.size >= 20) return;
    reportedOverflowCells.add(cellKey);
    // Publish only reviewed low-cardinality layout evidence.
    void logClient('layout_overflow', {
      route: getActive() || 'none',
      viewport: `${windowRef.innerWidth}x${windowRef.innerHeight}`,
      doc_overflow: audit.docOverflow,
      offenders: audit.offenders,
      app_version: getLatestState()?.version || 'unknown',
    });
  };
  // Debounce one settled audit after renders and resize.
  const scheduleLayoutAudit = () => { clearTimeout(layoutAuditTimer); layoutAuditTimer = setTimeout(runLayoutAudit, 700); };
  // Coordinate every route-outlet replacement through the existing stable-render hook.
  const afterRouteRender = (view, render) => {
    // Reapply game scroll-region semantics without a standing subtree observer.
    prepareRouteAfterRender(view, render);
    // Reapply the current fail-closed offline boundary to newly rendered server controls.
    synchronizeServerControls();
    // Schedule containment measurement after all synchronous post-render decoration commits.
    scheduleLayoutAudit();
  };
  // Preserve scroll and focus across same-route rerenders. (UX-027)
  installStableRouteRenders(routeOutlet, getActive, afterRouteRender);
  // Re-measure containment after viewport changes.
  windowRef.addEventListener('resize', scheduleLayoutAudit);
  // Repaint persistent shell text when locale changes.
  onLocaleChange(() => {
    // Localize shared feedback and wellness surfaces first.
    localizeFeedback();
    wellnessController.localize();
    // Repaint authenticated shell state only for a terms-complete session.
    const session = getCurrentSession();
    if (!session || session.terms?.required) return;
    // Rebuild localized descriptors from the latest authoritative catalog.
    setGameDescriptors((getLatestState()?.games || []).map(game => descriptorFromCatalog(game)));
    renderNav();
    updateCurrentUserShell();
    updateShellStatus(getLatestState(), getShellConnected());
    // Repaint Lobby in place without adding browser history.
    if (getActive() === 'lobby') void navigate('lobby', { history: 'none' });
  });
  // Restore routes through browser Back and Forward.
  windowRef.addEventListener('popstate', () => {
    // Let exact public-account routes own the browser first.
    if (renderPublicAuthRoute()) return;
    // Restore authenticated routing when a usable session exists.
    const session = getCurrentSession();
    if (session && !session.terms?.required) {
      documentRef.body.classList.remove('auth-locked');
      void navigate(routeFromLocation(), { history: 'none' });
      return;
    }
    // Fall back to the logged-out entry gate.
    renderLoginGate();
  });
  // Wire ledger-backed token top-up through the persistent wallet control.
  const addButton = documentRef.getElementById('add-token-btn');
  addButton.onclick = async () => {
    // Keep validation and API failures inside a bounded toast.
    try {
      // Read the requested play-token amount from the wallet input.
      const amountInput = documentRef.getElementById('add-token-amount');
      const amount = Number(amountInput.value || 0);
      // Apply the ledger-backed mutation and replace only the canonical player summary.
      const player = await addUserTokens({ amount });
      setCurrentSession(normalizeCurrentUser({ ...getCurrentSession(), player }));
      // Refresh authoritative wallet chrome before clearing local controls.
      updateCurrentUserShell();
      amountInput.value = '';
      documentRef.querySelector('.wallet-menu')?.removeAttribute('open');
      // Refresh the status rail and acknowledge the completed action.
      await refreshShellState({ quiet: true });
      toast(t('toast.tokensAdded', { amount: tokens(amount) }, 'shell'), true);
    } catch (error) {
      // Show the safe API message without interrupting the current route.
      toast(error.message);
    }
  };
  // Wire durable logout or disposable guest teardown through one control.
  const logoutButton = documentRef.getElementById('logout-btn');
  logoutButton.onclick = async () => {
    // Detect guest teardown and resolve success copy before clearing identity.
    const guestSession = isGuestSession();
    const loggedOutMessage = t(guestSession ? 'auth.guestEnded' : 'auth.loggedOut', {}, 'shell');
    // Keep the authenticated shell honest until server teardown succeeds.
    try {
      // Revoke the durable session or disposable trial.
      await (guestSession ? endGuestTrial() : logout());
      clearAuthenticatedShellState();
      renderLoginGate(loggedOutMessage);
    } catch (error) {
      // Treat an already-expired session as logged out.
      if (error?.code === 'UNAUTHORIZED') {
        clearAuthenticatedShellState();
        renderLoginGate(loggedOutMessage);
        return;
      }
      // Preserve authenticated state after an unconfirmed failure.
      toast(t('auth.logoutFailed', {}, 'shell'));
      await logClient('logout_error', { code: error?.code || 'UNKNOWN', message: error?.message || 'Logout failed' });
      await refreshCurrentSession();
    }
  };
  // Resolve authoritative current-user state before declaring readiness.
  try {
    // Hydrate the authenticated shell or logged-out gate.
    await refreshCurrentSession();
  } catch (error) {
    // Show and record the startup failure without replacing its authority.
    toast(t('startup.loadFailed', { message: error.message }, 'shell'));
    try { await logClient('initial_state_error', { message: error.message }); } catch (_) { /* Preserve the startup failure. */ }
    // Reject native readiness when authoritative refresh failed.
    throw error;
  }
  // Poll shell state periodically only for a usable authenticated session.
  setInterval(() => {
    // Avoid protected polling before login or terms completion.
    const session = getCurrentSession();
    if (session && !session.terms?.required) void refreshShellState({ quiet: true });
  }, 30000);
}
