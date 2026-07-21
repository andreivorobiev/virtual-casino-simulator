// Progressive-web-app client controller: registration, connectivity, and update states. (issue #182)
// It keeps the app fully usable in a normal browser, never blocks gameplay, and surfaces explicit
// online, offline, update-available, and update-failed states through a small shell banner.

// Import localized copy so every connectivity and update message respects the active locale.
import { t } from './i18n.js';

// Track the active service-worker registration for update coordination.
let registration = null;
// Track whether an update is waiting so the banner can offer a non-coercive reload.
let updateWaiting = false;
// Track whether the user explicitly applied an update so only that path reloads the page.
let applyingUpdate = false;

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
    // Expose a stable test hook.
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

// Render one connectivity or update state into the shell banner.
function showState(state) {
  // Resolve the banner element.
  const banner = bannerElement();
  // Map each state to its localized message and action.
  if (state === 'offline') {
    // Explain that the app is offline and server actions are paused.
    banner.textContent = t('pwa.offline', {}, 'shell');
    // Mark the banner with the current state for styling and tests.
    banner.dataset.state = 'offline';
    // Reveal the banner.
    banner.hidden = false;
  } else if (state === 'update') {
    // Offer a non-coercive reload to apply the ready update.
    banner.innerHTML = '';
    // Add the localized update message.
    const message = document.createElement('span');
    // Set the update-available copy.
    message.textContent = t('pwa.updateReady', {}, 'shell');
    // Add a reload control the user may ignore.
    const button = document.createElement('button');
    // Tag the reload control for tests.
    button.setAttribute('data-testid', 'pwa-update-reload');
    // Label the reload control.
    button.textContent = t('pwa.reload', {}, 'shell');
    // Apply the update only when the user chooses to.
    button.onclick = () => applyUpdate();
    // Compose the update banner.
    banner.append(message, button);
    // Mark the update state.
    banner.dataset.state = 'update';
    // Reveal the banner.
    banner.hidden = false;
  } else if (state === 'update-failed') {
    // Explain that the update could not be applied and the app is still usable.
    banner.textContent = t('pwa.updateFailed', {}, 'shell');
    // Mark the failure state.
    banner.dataset.state = 'update-failed';
    // Reveal the banner.
    banner.hidden = false;
  } else {
    // Hide the banner when the app is back online with no pending update.
    banner.hidden = true;
    // Clear the state marker.
    banner.dataset.state = 'online';
  }
}

// Ask the waiting worker to activate, then reload once it takes control.
function applyUpdate() {
  // Do nothing when no update is actually waiting.
  if (!registration || !registration.waiting) return;
  // Guard the reload against update failures so the app stays usable.
  try {
    // Mark that the next controller change is a user-requested update so it may reload.
    applyingUpdate = true;
    // Instruct the waiting worker to skip waiting and activate.
    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
  // Show a non-blocking failure state if the update cannot be applied.
  } catch (error) {
    // Present the update-failed state without breaking the running app.
    showState('update-failed');
  }
}

// Broadcast the current connectivity so games can disable server-only actions with a clear reason.
function broadcastConnectivity() {
  // Read the browser's current online status.
  const online = navigator.onLine !== false;
  // Publish the status for shell and game modules that gate server actions.
  window.dispatchEvent(new CustomEvent('casino-connectivity', { detail: { online } }));
  // Show the offline banner while offline, or clear it while online without a pending update.
  showState(online ? (updateWaiting ? 'update' : 'online') : 'offline');
}

// Register the service worker and wire connectivity and update handling; safe to call once on boot.
export function initPwa() {
  // Reflect the initial connectivity immediately so an offline cold start is explicit.
  broadcastConnectivity();
  // Update the banner whenever connectivity changes.
  window.addEventListener('online', broadcastConnectivity);
  // Update the banner whenever the browser goes offline.
  window.addEventListener('offline', broadcastConnectivity);
  // Skip service-worker features gracefully in browsers that do not support them.
  if (!('serviceWorker' in navigator)) return;
  // Register once the document has finished loading, handling the already-loaded case since boot is async.
  const startRegistration = async () => {
    // Guard registration so a failure never blocks the normal browser experience.
    try {
      // Register the shell service worker at the application root scope.
      registration = await navigator.serviceWorker.register('/sw.js');
      // Surface an update that is already waiting from a previous visit.
      if (registration.waiting) { updateWaiting = true; broadcastConnectivity(); }
      // Watch for a newly installing worker to detect a ready update.
      registration.addEventListener('updatefound', () => {
        // Track the installing worker's state transitions.
        const installing = registration.installing;
        // Do nothing when no worker is installing.
        if (!installing) return;
        // Announce an update once it finishes installing while a controller already exists.
        installing.addEventListener('statechange', () => {
          // A worker that reaches installed with an existing controller is a ready update.
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            // Record the waiting update and refresh the banner.
            updateWaiting = true;
            // Show the non-coercive update banner.
            broadcastConnectivity();
          }
        });
      });
      // Reload exactly once, and only when the user explicitly applied an update.
      let reloaded = false;
      // Listen for the controlling worker change; the initial clients.claim control must not reload.
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        // Reload only for a user-applied update, never for the first-visit claim.
        if (applyingUpdate && !reloaded) { reloaded = true; window.location.reload(); }
      });
    // Ignore registration failures so the app remains fully usable as a normal web page.
    } catch (error) {
      // Leave the app running without offline support when registration is unavailable.
    }
  };
  // Register now when the document already finished loading, otherwise wait for the load event.
  if (document.readyState === 'complete') {
    // Start registration immediately since the load event has already fired.
    startRegistration();
  } else {
    // Defer registration to the load event so it never competes with first paint.
    window.addEventListener('load', startRegistration, { once: true });
  }
}
