// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Own the offline-safe progressive-web-app shell without enabling deployment or public exposure. (PWA-001, PWA-002)
// Import localized copy so every lifecycle message follows the active shell locale.
import { t } from './i18n.js';
// Import the single browser and worker cache identity instead of retaining a second release pin.
import { PWA_APP_VERSION } from './pwa_version.js';

// Preserve the established read-only page-side export for tests and diagnostics.
export { PWA_APP_VERSION };
// Name the session marker that distinguishes a cold shell boot from a same-context warm boot.
const WARM_START_KEY = 'casino.pwa.warmStart';
// Bound controls whose actions require an authoritative server response while offline.
const SERVER_CONTROL_SELECTOR = [
  '#login-gate button', '#login-gate input', '#terms-gate button', '#terms-gate input',
  '[data-testid="invitation-redemption"] button', '[data-testid="invitation-redemption"] input', '[data-testid="invitation-redemption"] select',
  '.game-screen button', '.game-screen input', '.game-screen select', '.game-screen textarea',
  '.wallet-menu button', '.wallet-menu input', '#feedback-dialog button', '#feedback-dialog input', '#feedback-dialog select', '#feedback-dialog textarea',
  '#wellness-dialog button', '#wellness-dialog input',
].join(',');
// Enumerate display-only lifecycle states accepted by the bounded shell status renderer.
const DISPLAY_STATES = new Set(['cold-start', 'warm-start', 'offline', 'reconnecting', 'online', 'route-restored', 'update', 'update-failed', 'stale-client', 'expired-session', 'reconnect-failed']);

// Track the active service-worker registration for update coordination.
let registration = null;
// Track whether an update is waiting so the banner can retain the update action across locale changes.
let updateWaiting = false;
// Track whether the user explicitly applied an update so initial clients.claim never reloads the page.
let applyingUpdate = false;
// Track the active connectivity state independently from navigator timing.
let offline = navigator.onLine === false;
// Track the latest rendered lifecycle state for diagnostics and deterministic evidence.
let currentState = offline ? 'offline' : 'online';
// Store the application-owned authoritative refresh callback used after reconnect.
let reconnectHandler = null;
// Coalesce duplicate online notifications while one authoritative route restore owns the shell.
let reconnectTask = null;
// Prevent duplicate listener and service-worker registration when boot is called more than once.
let initialized = false;
// Hold the bounded update timeout so a failed activation can become visible without a reload loop.
let updateTimeout = null;

// Report the PWA controller's event-backed connectivity boundary without relying on navigator timing.
export function isPwaOffline() {
  // Return only the normalized state maintained by initial detection and browser connectivity events.
  return offline;
}

// Resolve the shell banner element, creating it once beneath the persistent status bar.
function bannerElement() {
  // Reuse the existing banner when it was already inserted.
  let banner = document.getElementById('pwa-banner');
  // Create the banner the first time a state must be shown.
  if (!banner) {
    // Build a polite live region so assistive technology announces connectivity changes.
    banner = document.createElement('div');
    // Identify the banner for later updates and tests.
    banner.id = 'pwa-banner';
    // Expose a stable visual-matrix hook.
    banner.setAttribute('data-testid', 'pwa-banner');
    // Announce changes without stealing focus.
    banner.setAttribute('role', 'status');
    // Keep announcements polite so they never interrupt play.
    banner.setAttribute('aria-live', 'polite');
    // Start hidden until a state needs to be shown.
    banner.hidden = true;
    // Attach the banner to the document body so it survives route changes.
    document.body.appendChild(banner);
  }
  // Return the resolved banner element.
  return banner;
}

// Resolve localized copy for one allowlisted lifecycle state.
function stateMessage(state) {
  // Map stable internal state names to locale-owned resource keys.
  const keys = {
    'cold-start': 'pwa.coldStart',
    'warm-start': 'pwa.warmStart',
    offline: 'pwa.offline',
    reconnecting: 'pwa.reconnecting',
    online: 'pwa.online',
    'route-restored': 'pwa.routeRestored',
    'update-failed': 'pwa.updateFailed',
    'stale-client': 'pwa.staleClient',
    'expired-session': 'pwa.expiredSession',
    'reconnect-failed': 'pwa.reconnectFailed',
  };
  // Return translated text without reflecting untrusted state strings into the UI.
  return t(keys[state] || 'pwa.updateFailed', {}, 'shell');
}

// Render one connectivity, restoration, or update state into the shell banner.
export function renderPwaState(state) {
  // Reject unknown display states so callers cannot inject copy or markup.
  if (!DISPLAY_STATES.has(state)) return;
  // Resolve the persistent banner element.
  const banner = bannerElement();
  // Record the state for accessibility tests and diagnostic evidence.
  currentState = state;
  // Clear earlier message and action nodes before rendering the next state.
  banner.replaceChildren();
  // Add the update action only for a confirmed waiting worker.
  if (state === 'update') {
    // Build the localized update message.
    const message = document.createElement('span');
    // Populate the update copy through the shell locale bundle.
    message.textContent = t('pwa.updateReady', {}, 'shell');
    // Build the explicit non-coercive update control.
    const button = document.createElement('button');
    // Expose a stable selector for the update action.
    button.setAttribute('data-testid', 'pwa-update-reload');
    // Render the localized action label.
    button.textContent = t('pwa.reload', {}, 'shell');
    // Apply the update only after the user activates the control.
    button.onclick = () => applyUpdate();
    // Compose the update state without HTML interpolation.
    banner.append(message, button);
  } else {
    // Render every other state as plain localized text.
    banner.textContent = stateMessage(state);
  }
  // Publish the bounded state for CSS, tests, and assistive diagnostics.
  banner.dataset.state = state;
  // Reveal every explicit state; normal steady-state hiding is handled separately.
  banner.hidden = false;
}

// Hide the lifecycle banner after a successful steady-state refresh.
function hideState() {
  // Resolve the banner so its state remains inspectable even when hidden.
  const banner = bannerElement();
  // Record the authoritative steady state.
  currentState = 'online';
  // Mark the banner online while removing it from layout and interaction.
  banner.dataset.state = 'online';
  // Hide the nonessential steady-state banner.
  banner.hidden = true;
}

// Restore only controls disabled by the PWA boundary, preserving application-owned disabled states.
function restoreServerControls() {
  // Find controls tagged when the offline boundary disabled them.
  document.querySelectorAll('[data-pwa-offline-disabled="true"]').forEach(control => {
    // Restore the control because it was enabled before the offline transition.
    control.disabled = false;
    // Remove the PWA marker so later application renders retain ownership.
    delete control.dataset.pwaOfflineDisabled;
    // Remove the redundant accessibility state now that the native control is enabled.
    control.removeAttribute('aria-disabled');
  });
}

// Disable all currently rendered server-required controls without changing local navigation.
function disableServerControls() {
  // Visit only bounded authentication, wallet, feedback, and game action controls.
  document.querySelectorAll(SERVER_CONTROL_SELECTOR).forEach(control => {
    // Preserve application-owned disabled states rather than claiming them for reconnect restoration.
    if (control.disabled) return;
    // Mark the control so only PWA-owned changes are later restored.
    control.dataset.pwaOfflineDisabled = 'true';
    // Use native disabled behavior to prevent keyboard, pointer, and scripted form submission.
    control.disabled = true;
    // Mirror the native state for assistive technologies that inspect attributes directly.
    control.setAttribute('aria-disabled', 'true');
  });
}

// Apply the current server-action boundary after route renders and connectivity transitions.
export function synchronizeServerControls() {
  // Keep server actions disabled while offline or while authoritative reconnect has not completed.
  if (offline || currentState === 'reconnecting' || currentState === 'reconnect-failed') disableServerControls();
  // Restore only PWA-owned disables after a successful authoritative refresh.
  else restoreServerControls();
}

// Publish a normalized connectivity event for modules that need read-only status.
function publishConnectivity(state) {
  // Emit only the boolean network boundary and bounded lifecycle state.
  window.dispatchEvent(new CustomEvent('casino-connectivity', { detail: { online: !offline, state } }));
}

// Enter the offline boundary immediately and fail closed for all server-required actions.
function handleOffline() {
  // Record the browser connectivity boundary before any UI mutation.
  offline = true;
  // Render the localized offline explanation.
  renderPwaState('offline');
  // Disable all currently mounted server-required controls.
  synchronizeServerControls();
  // Notify modules without implying any action succeeded.
  publishConnectivity('offline');
}

// Refresh session, wallet, game state, and route before releasing controls after reconnect.
export function reconnectAuthoritatively() {
  // Share the exact pending result instead of starting overlapping session and route hydration.
  if (reconnectTask) return reconnectTask;
  // Publish ownership before invoking callbacks that can synchronously emit another online event.
  reconnectTask = Promise.resolve().then(performReconnect).finally(() => {
    // Permit a later explicit connectivity attempt after success or failure, never auto-retry.
    reconnectTask = null;
  });
  // Return one operation to every caller in this connectivity cohort.
  return reconnectTask;
}

// Perform the existing fail-closed refresh exactly once for the current reconnect cohort.
async function performReconnect() {
  // Keep actions disabled until the application proves authoritative state.
  offline = false;
  // Present the reconnecting state while the backend callback runs.
  renderPwaState('reconnecting');
  // Apply the reconnecting control boundary before starting network work.
  synchronizeServerControls();
  // Notify modules that the network returned but state is not authoritative yet.
  publishConnectivity('reconnecting');
  // Start protected refresh logic so a network flap never releases stale actions.
  try {
    // Ask the application shell to refresh the session, wallet, game state, and current route.
    const result = reconnectHandler ? await reconnectHandler() : { status: 'online' };
    // Keep an expired session at the login boundary without restoring authenticated controls.
    if (result?.status === 'expired-session') {
      // Render the localized session-expired state.
      renderPwaState('expired-session');
      // Restore public login controls because the application removed stale authenticated state.
      restoreServerControls();
      // Publish the bounded terminal reconnect state.
      publishConnectivity('expired-session');
      // Return the application result for deterministic browser validation.
      return result;
    }
    // Restore controls only after every authoritative refresh step succeeded.
    restoreServerControls();
    // Render route-restoration confirmation when the callback remounted a game route.
    renderPwaState(result?.status === 'route-restored' ? 'route-restored' : 'online');
    // Publish the successful authoritative state.
    publishConnectivity(result?.status === 'route-restored' ? 'route-restored' : 'online');
    // Hide the positive state after a bounded interval while keeping it available to assistive announcements.
    window.setTimeout(() => { if (!offline && !updateWaiting && ['online', 'route-restored'].includes(currentState)) hideState(); }, 2200);
    // Return the application result for callers and tests.
    return result;
  // Keep controls fail-closed when the network is nominally online but authoritative refresh fails.
  } catch (error) {
    // Render a localized retry-safe failure without reflecting server diagnostics.
    renderPwaState('reconnect-failed');
    // Preserve the fail-closed server-action boundary.
    synchronizeServerControls();
    // Publish the bounded failure state for modules and diagnostics.
    publishConnectivity('reconnect-failed');
    // Return a low-cardinality result instead of throwing an unhandled browser rejection.
    return { status: 'reconnect-failed' };
  }
}

// Resolve the waiting worker even when the user clicks during the installing-to-waiting transition. (PWA-003)
async function resolveWaitingWorker() {
  // Return the already-waiting worker without allocating listeners.
  if (registration?.waiting) return registration.waiting;
  // Capture the installing worker because registration.waiting may lag its state transition.
  const installing = registration?.installing;
  // Stop when registration has no applicable update worker.
  if (!installing) return null;
  // Return a bounded state observer so a failed install cannot strand the Apply button forever.
  return new Promise(resolve => {
    // Finish once and remove the observer before resolving.
    const finish = worker => { installing.removeEventListener('statechange', changed); window.clearTimeout(timeout); resolve(worker); };
    // Resolve the installed worker through registration.waiting when the browser has promoted it.
    const changed = () => { if (installing.state === 'installed') finish(registration.waiting || installing); else if (['redundant','activated'].includes(installing.state)) finish(null); };
    // Bound the transitional wait so update failure remains visible and retryable.
    const timeout = window.setTimeout(() => finish(null), 4000);
    // Observe only this update worker's lifecycle.
    installing.addEventListener('statechange', changed);
    // Handle a worker that completed between capture and listener registration.
    changed();
  });
}

// Ask the waiting worker to activate, then reload once it takes control.
async function applyUpdate() {
  // Resolve an installing worker before deciding the update is unavailable. (PWA-003)
  const worker = await resolveWaitingWorker();
  // Show a failure without reloading when no update is actually waiting.
  if (!worker) { renderPwaState('update-failed'); return; }
  // Guard worker messaging so the current application remains usable on failure.
  try {
    // Mark that the next controller change is user-requested and may reload.
    applyingUpdate = true;
    // Fail visibly if activation does not complete within one bounded interval.
    updateTimeout = window.setTimeout(() => { applyingUpdate = false; renderPwaState('update-failed'); }, 12000);
    // Instruct the waiting worker to activate.
    worker.postMessage({ type: 'SKIP_WAITING' });
  // Preserve the current application when the browser rejects worker messaging.
  } catch (error) {
    // Clear the applying flag so a later unrelated controller change cannot reload.
    applyingUpdate = false;
    // Present the localized failure state.
    renderPwaState('update-failed');
  }
}

// Compare the controlling worker's version with the canonical page version.
function requestControllerVersion() {
  // Read the current controller without assuming registration timing.
  const controller = navigator.serviceWorker.controller;
  // Request version proof only from an active controller.
  if (controller) controller.postMessage({ type: 'GET_VERSION' });
}

// Observe one installation whether it began before or after registration listener wiring. (PWA-003)
function observeInstallingWorker(installing) {
  // Stop when the registration has no installation in progress.
  if (!installing) return;
  // Present the player-controlled update boundary once this worker is installed beside an existing controller.
  const revealWhenInstalled = () => {
    // Ignore transitional and terminal states that do not represent a waiting update.
    if (installing.state !== 'installed' || !navigator.serviceWorker.controller) return;
    // Retain the waiting state across connectivity rerenders.
    updateWaiting = true;
    // Present the non-coercive update action.
    renderPwaState('update');
  };
  // Observe future state changes for a worker that is still installing.
  installing.addEventListener('statechange', revealWhenInstalled);
  // Inspect the current state immediately because installation may have completed before listener wiring.
  revealWhenInstalled();
}

// Register the service worker and wire update/version handling after first paint.
async function registerWorker() {
  // Start protected registration so unsupported hosting never blocks normal browser use.
  try {
    // Register the canonical-versioned script URL at root scope.
    registration = await navigator.serviceWorker.register(`/sw.js?v=${encodeURIComponent(PWA_APP_VERSION)}`, { scope: '/', type: 'module', updateViaCache: 'none' });
    // Surface an update already waiting from a previous visit.
    if (registration.waiting) { updateWaiting = true; renderPwaState('update'); }
    // Watch one new installation without forcing activation.
    registration.addEventListener('updatefound', () => {
      // Observe the newly exposed worker through the shared race-safe state boundary.
      observeInstallingWorker(registration.installing);
    });
    // Observe an installation that started before register() resolved or updatefound wiring completed.
    observeInstallingWorker(registration.installing);
    // Recheck the waiting slot after listener wiring so no installation-to-waiting edge is missed.
    if (registration.waiting) { updateWaiting = true; renderPwaState('update'); }
    // Ask the active controller to prove its canonical version.
    requestControllerVersion();
  // Keep the normal browser application usable and expose update failure without raw diagnostics.
  } catch (error) {
    // Present a bounded localized failure only when service workers are supported but registration failed.
    renderPwaState('update-failed');
  }
}

// Initialize the offline-safe shell exactly once during application boot.
export function initPwa(options = {}) {
  // Update the application callback even when initialization already happened.
  reconnectHandler = typeof options.onReconnect === 'function' ? options.onReconnect : reconnectHandler;
  // Stop after callback refresh when listeners and registration are already active.
  if (initialized) return;
  // Mark initialization before any synchronous event can re-enter boot.
  initialized = true;
  // Expose a stable shell identity for governed screenshots.
  document.body.setAttribute('data-testid', 'pwa-shell');
  // Read and advance the same-context warm-start marker without durable tracking.
  const startState = sessionStorage.getItem(WARM_START_KEY) === 'true' ? 'warm-start' : 'cold-start';
  // Record the lifecycle class for deterministic cold/warm evidence.
  document.documentElement.dataset.pwaStart = startState;
  // Mark later same-context loads as warm without crossing a browser close.
  sessionStorage.setItem(WARM_START_KEY, 'true');
  // Allow locale changes and browser evidence to request only allowlisted display states.
  window.addEventListener('casino-pwa-display-state', event => renderPwaState(event.detail?.state));
  // Enter or leave the offline boundary when browser connectivity changes.
  window.addEventListener('offline', handleOffline);
  // Require an authoritative refresh before releasing controls after reconnect.
  window.addEventListener('online', () => { void reconnectAuthoritatively(); });
  // Apply the initial browser connectivity boundary.
  if (offline) handleOffline(); else hideState();
  // Skip service-worker features gracefully in unsupported browsers.
  if (!('serviceWorker' in navigator)) return;
  // Detect stale controlling workers through a low-cardinality version response.
  navigator.serviceWorker.addEventListener('message', event => {
    // Ignore every message outside the exact version protocol.
    if (event.data?.type !== 'PWA_VERSION') return;
    // Present stale-client status when page and controller canonical versions differ.
    if (event.data.version !== PWA_APP_VERSION) renderPwaState('stale-client');
  });
  // Reload exactly once after a user-applied worker takes control.
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    // Request version proof for an initial clients.claim without reloading.
    if (!applyingUpdate) { requestControllerVersion(); return; }
    // Clear the activation timeout before navigating.
    if (updateTimeout) window.clearTimeout(updateTimeout);
    // Prevent a second controller change from causing a reload loop.
    applyingUpdate = false;
    // Reload the current route so the new static shell and authoritative backend state are fetched together.
    window.location.reload();
  });
  // Register after load when possible without losing an already-fired load event.
  if (document.readyState === 'complete') void registerWorker();
  // Defer registration until the document load event otherwise.
  else window.addEventListener('load', () => { void registerWorker(); }, { once: true });
  // Publish a read-only diagnostic surface without exposing mutation or provider controls.
  window.CasinoPwa = Object.freeze({ version: PWA_APP_VERSION, state: () => currentState, reconnect: reconnectAuthoritatively });
}
