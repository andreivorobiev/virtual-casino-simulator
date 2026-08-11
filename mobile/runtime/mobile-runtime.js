// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import the native application lifecycle bridge used to pause new actions while backgrounded.
import { App } from "@capacitor/app";
// Import the system browser bridge used to keep external pages outside the casino WebView.
import { Browser } from "@capacitor/browser";
// Import the keyboard bridge used to expose overlap state to responsive CSS.
import { Keyboard } from "@capacitor/keyboard";
// Import the native network bridge used to expose offline and reconnect state.
import { Network } from "@capacitor/network";
// Import the Capacitor bridge factory at the native entry point rather than the pure transport module.
import { registerPlugin } from "@capacitor/core";
// Import the shared strict configuration validator used by the build and native runtime.
import { validateMobileConfig } from "./config.js";
// Import the Request-correct exact-origin transport, recovery coordinator, and process authority.
import { authorizeDeepLinkArrival, createLatestNativeObservation, createLifecycleGate, createMobileRecoveryCoordinator, createMobileTransport, exactWebViewAuthority } from "./transport.js";
// Import the strict universal-link validator that rejects unowned routes and authorities.
import { deepLinkFingerprint, validateDeepLink } from "./deep-links.js";

// Preserve the platform fetch implementation before installing the API-origin adapter.
const platformFetch = window.fetch.bind(window);
// Create one process-local gate that begins offline and session-unvalidated on every cold launch.
const lifecycleGate = createLifecycleGate();
// Retain the scoped transport only after configuration and native network state are validated.
let mobileTransport = null;
// Retain the serialized recovery boundary after native transport configuration succeeds.
let mobileRecovery = null;
// Retain the latest native network state across bootstrap ordering and listener callbacks.
let latestNetworkConnected = false;
// Retain the race-safe network observer for initial and foreground snapshots.
let networkObservation = null;
// Prevent defensive direct callers from appending the shared entry point more than once.
let sharedApplicationLoaded = false;
// Retain the one module/controller load promise so failed readiness never appends a second script.
let sharedApplicationControllerPromise = null;
// Retain the first shared initialization outcome independently from reusable controller load.
let sharedApplicationInitialOutcomePromise = null;
// Serialize direct load callers outside the recovery coordinator without caching a failed attempt.
let sharedApplicationLoadInFlight = null;
// Consume the initial application result once before later attempts use authoritative reconnect.
let sharedApplicationInitialOutcomeConsumed = false;
// Bind the sole OS-vault-backed plugin at the native composition boundary.
const secureTransportPlugin = registerPlugin("CasinoSecureTransport");

// Create or retrieve the native-only status region used for actionable connection messages.
function statusRegion() {
  // Reuse the existing region so repeated state changes never duplicate visible UI.
  const existing = document.getElementById("mobile-native-status");
  // Return the existing region when the bootstrap has already created it.
  if (existing) return existing;
  // Create a live status region outside shared browser application source.
  const region = document.createElement("div");
  // Assign a stable id for tests and repeated state updates.
  region.id = "mobile-native-status";
  // Assign the native-only banner class defined by the mobile runtime stylesheet.
  region.className = "mobile-native-status";
  // Announce meaningful connection changes without interrupting the user.
  region.setAttribute("role", "status");
  // Keep the status region hidden until a problem requires user action.
  region.hidden = true;
  // Add the region before shared application content is loaded.
  document.body.prepend(region);
  // Return the created region to the caller.
  return region;
}

// Display a concise native-only connectivity or configuration message.
function showStatus(message, kind = "warning") {
  // Resolve the shared native-only live region.
  const region = statusRegion();
  // Set player-facing copy without exposing configuration or diagnostic details.
  region.textContent = message;
  // Expose a stable status kind for accessible visual treatment.
  region.dataset.kind = kind;
  // Reveal the actionable status message.
  region.hidden = false;
}

// Hide the transient native-only connection message after recovery.
function clearStatus() {
  // Resolve the shared native-only live region.
  const region = statusRegion();
  // Hide stale recovery copy after the connection is usable again.
  region.hidden = true;
  // Remove stale copy so screen readers do not revisit an obsolete message.
  region.textContent = "";
}

// Install a scoped API hook without replacing the platform's global fetch implementation.
async function installApiTransport(config) {
  // Derive the exact custom-scheme authority because WHATWG URL.origin is null on iOS Capacitor.
  const webViewAuthority = exactWebViewAuthority(window.location.href);
  // Bind the public backend and exact Capacitor origin inside native secure transport.
  mobileTransport = createMobileTransport({ backendOrigin: config.backendBaseUrl, webViewOrigin: webViewAuthority, lifecycle: lifecycleGate, nativePlugin: secureTransportPlugin, onReconciliationRequired: () => {
    // Show the held state immediately without queueing or retrying the player's intended action.
    showStatus("Session refresh required. Try again after reconnect completes.", "security");
    // Start one coalesced authoritative refresh for a later explicit player retry.
    void recoverMobileRuntime();
  } });
  // Bind the native plugin to public origins before any request can consult the OS vault.
  await mobileTransport.configure();
  // Publish only the frozen scoped hook consumed by shared API code; never expose token or cookie state.
  window.CasinoMobileTransport = Object.freeze({ fetch: mobileTransport.fetch, managesSession: true, prepareAccountSwitch: mobileTransport.prepareAccountSwitch });
}

// Attempt one serialized authority recovery while preserving a recoverable fail-closed shell.
async function recoverMobileRuntime() {
  // Keep bootstrap held until transport configuration and native network state both exist.
  if (!mobileRecovery) return false;
  // Bind the coordinator to the newest native connectivity result before probing.
  mobileRecovery.setConnected(latestNetworkConnected);
  // Preserve the offline banner without invoking a doomed session probe.
  if (!latestNetworkConnected) return false;
  // Attempt the exact shared recovery boundary without exposing diagnostics or credentials.
  try {
    // Revalidate and then load or reconnect through the serialized coordinator.
    const recovered = await mobileRecovery.recover();
    // Remove stale native status copy only after complete recovery.
    if (recovered) clearStatus();
    // Return the bounded state to deterministic bootstrap tests and callers.
    return recovered;
  } catch (_) {
    // Keep shared actions unavailable while allowing a later reconnect or foreground event to retry.
    showStatus("Session unavailable. Reconnect or reopen before continuing.", "security");
    // Return a bounded failure rather than misclassifying a transient probe as invalid configuration.
    return false;
  }
}

// Keep native network state synchronized with session and authoritative PWA recovery.
async function installNetworkLifecycle() {
  // Build one state sink that dispatches accepted edges before asynchronous recovery begins.
  networkObservation = createLatestNativeObservation(async (status, source) => {
    // Retain the normalized plugin state across recovery callbacks.
    latestNetworkConnected = status.connected === true;
    // Update the runtime gate before any later API action begins.
    lifecycleGate.setConnected(latestNetworkConnected);
    // Keep the optional recovery coordinator synchronized after transport setup.
    mobileRecovery?.setConnected(latestNetworkConnected);
    // Show the offline gate when connectivity is lost.
    if (!status.connected) showStatus("Network unavailable. Reconnect before continuing.", "offline");
    // Notify observers before any online recovery await so a later offline edge cannot be reordered.
    window.dispatchEvent(new CustomEvent("casino:mobile-network", { detail: { connected: status.connected, connectionType: status.connectionType } }));
    // Start recovery only for a live event; bootstrap owns the accepted initial snapshot.
    if (source === "event" && latestNetworkConnected) void recoverMobileRuntime();
  });
  // Subscribe before reading a snapshot so no edge can disappear between observation boundaries.
  await Network.addListener("networkStatusChange", status => {
    // Invalidate immediately on disconnect before any queued observer sink can yield.
    if (status.connected !== true) {
      // Retain exact offline state before a caller can start another scoped request.
      latestNetworkConnected = false;
      // Close every lifecycle ticket synchronously at the raw native event boundary.
      lifecycleGate.setConnected(false);
      // Invalidate any recovery attempt synchronously before observer serialization.
      mobileRecovery?.setConnected(false);
    }
    // Apply this event through the epoch guard and preserve its promise for Capacitor diagnostics.
    void networkObservation.event(status).catch(() => showStatus("Native network state is unavailable.", "security"));
  });
  // Capture the listener epoch immediately before the asynchronous initial snapshot.
  const snapshot = networkObservation.beginSnapshot();
  // Read native connectivity only after the listener is active.
  const initialStatus = await Network.getStatus();
  // Apply the snapshot only when no newer listener event superseded it.
  await networkObservation.completeSnapshot(snapshot, initialStatus);
  // Await any newer listener application before releasing bootstrap from fail-closed networking.
  await networkObservation.whenBound();
}

// Keep background and foreground state synchronized without owning game loops.
async function installAppLifecycle() {
  // Advance immediately for every applied app-state edge so deferred foreground work can be superseded.
  let appStateEpoch = 0;
  // Refresh foreground network and session authority without delaying a later background invalidation.
  const refreshForeground = async expectedAppEpoch => {
    // Capture network event epoch before the asynchronous foreground connectivity snapshot.
    const networkSnapshot = networkObservation.beginSnapshot();
    // Re-read native connectivity after foreground while the network listener remains active.
    const status = await Network.getStatus();
    // Apply only when no disconnect or reconnect event superseded this snapshot.
    const accepted = await networkObservation.completeSnapshot(networkSnapshot, status);
    // Reject recovery when a background or newer foreground edge landed during the snapshot.
    if (expectedAppEpoch !== appStateEpoch || document.documentElement.dataset.mobileAppState !== "active") return;
    // Recover only from an accepted current snapshot; a newer online event already owns recovery.
    if (accepted && latestNetworkConnected && mobileTransport) void recoverMobileRuntime();
  };
  // Build one state sink shared by initial snapshot and every later native event.
  const appObservation = createLatestNativeObservation(async (state, source) => {
    // Supersede every earlier deferred foreground refresh before crossing any asynchronous boundary.
    appStateEpoch += 1;
    // Update the mutation gate before dispatching any lifecycle notification.
    lifecycleGate.setActive(state.isActive);
    // Invalidate serialized recovery before any background-crossed probe can release shared code.
    mobileRecovery?.setActive(state.isActive);
    // Expose the current lifecycle state to native-only CSS and diagnostics.
    document.documentElement.dataset.mobileAppState = state.isActive ? "active" : "background";
    // Notify shared modules through an additive event while preserving their public actions.
    window.dispatchEvent(new CustomEvent("casino:mobile-app-state", { detail: { isActive: state.isActive } }));
    // Ignore foreground recovery for the initial snapshot because bootstrap performs it after all guards.
    if (source !== "event" || !state.isActive) return;
    // Capture this foreground epoch before scheduling its non-blocking network/session refresh.
    const expectedAppEpoch = appStateEpoch;
    // Keep the listener sink synchronous so a following background event invalidates requests immediately.
    void refreshForeground(expectedAppEpoch).catch(() => showStatus("Session unavailable. Reconnect or reopen before continuing.", "security"));
  });
  // Subscribe before reading initial state so no app edge can disappear during bootstrap.
  await App.addListener("appStateChange", state => {
    // Invalidate immediately on background before any deferred foreground task can retain authority.
    if (state.isActive !== true) {
      // Close every process ticket synchronously at the raw native event boundary.
      lifecycleGate.setActive(false);
      // Invalidate any recovery attempt synchronously before observer serialization.
      mobileRecovery?.setActive(false);
    }
    // Apply this event through the epoch guard and preserve listener responsiveness.
    void appObservation.event(state).catch(() => showStatus("Native application state is unavailable.", "security"));
  });
  // Capture the listener epoch immediately before the asynchronous initial snapshot.
  const snapshot = appObservation.beginSnapshot();
  // Read exact initial foreground state only after listener registration succeeds.
  const initialState = await App.getState();
  // Apply the snapshot only when no newer app-state event superseded it.
  await appObservation.completeSnapshot(snapshot, initialState);
  // Await any newer listener application before releasing bootstrap from fail-closed lifecycle state.
  await appObservation.whenBound();
}

// Install exact-origin universal-link handling for restricted-preview account flows.
async function installDeepLinkHandling(config) {
  // Retain transient purpose-bound bearers only in this module's process memory.
  const transientBearers = new Map();
  // Retain successfully handled fingerprints so duplicate launch and event delivery stays invisible.
  const handledFingerprints = new Set();
  // Serialize link handling so two native arrivals cannot reorder history or one-shot bearers.
  let linkQueue = Promise.resolve();
  // Navigate one validated link through existing client routing without retaining it in native logs.
  const navigate = async rawUrl => {
    // Resolve only an exact allowlisted relative location or fail closed without navigation.
    const validated = validateDeepLink(rawUrl, config.backendBaseUrl);
    // Derive one digest-only fingerprint without persisting bearer or route content.
    const fingerprint = await deepLinkFingerprint(validated);
    // Treat a duplicate launch/event delivery as already handled without another claim or remount.
    if (handledFingerprints.has(fingerprint)) return;
    // Invalidate warm work, revalidate, claim replay, and activate one token-free public route atomically.
    await authorizeDeepLinkArrival({ warm: sharedApplicationLoaded, lifecycle: lifecycleGate, revalidate: mobileTransport.revalidate, claim: mobileTransport.claimDeepLink, fingerprint, activate: async () => {
      // Mark the fingerprint only after native replay claim and any warm revalidation succeed.
      handledFingerprints.add(fingerprint);
      // Retain a purpose bearer only in module memory until shared code consumes it once.
      if (validated.bearer) transientBearers.set(validated.path, validated.bearer);
      // Replace the current entry immediately with a token-free owned location.
      history.replaceState({ mobileDeepLink: true }, "", validated.publicLocation);
      // Notify the already-loaded shared router so it tears down authenticated game state synchronously.
      window.dispatchEvent(new PopStateEvent("popstate"));
    } });
  };
  // Enqueue one link while preserving queue progress after a rejected hostile arrival.
  const enqueue = candidate => {
    // Chain the candidate after every earlier link reaches a terminal result.
    const pending = linkQueue.then(() => navigate(candidate));
    // Preserve queue continuity without hiding this candidate's rejection from its caller.
    linkQueue = pending.catch(() => undefined);
    // Return the exact candidate result for snapshot or event handling.
    return pending;
  };
  // Build one listener-first observation that drops a launch snapshot superseded by a newer event.
  const linkObservation = createLatestNativeObservation(async candidate => { if (candidate?.url) await enqueue(candidate.url); });
  // Register warm-link handling before requesting the cold-launch snapshot.
  await App.addListener("appUrlOpen", event => {
    // Serialize, validate, and safely classify this native event without exposing its URL.
    void linkObservation.event(event).catch(() => showStatus("This link is invalid or expired.", "security"));
  });
  // Capture the listener epoch immediately before the asynchronous launch snapshot.
  const snapshot = linkObservation.beginSnapshot();
  // Read the cold-launch URL only after event handling is active.
  const launch = await App.getLaunchUrl();
  // Apply a non-superseded launch snapshot through the same serialized queue.
  try { await linkObservation.completeSnapshot(snapshot, launch); } catch (_) { showStatus("This link is invalid or expired.", "security"); }
  // Await any newer link event so bootstrap cannot overtake its token-free navigation boundary.
  try { await linkObservation.whenBound(); } catch (_) { showStatus("This link is invalid or expired.", "security"); }
  // Publish a one-shot bearer reader without exposing enumeration or storage operations.
  window.CasinoMobileDeepLink = Object.freeze({ consumeBearer: path => { const bearer = transientBearers.get(path) || ""; transientBearers.delete(path); return bearer; } });
}

// Expose native keyboard overlap state through CSS variables without altering shared layouts.
async function installKeyboardLifecycle() {
  // Subscribe to keyboard-show events after native measurement is available.
  await Keyboard.addListener("keyboardWillShow", info => {
    // Expose the measured height for native-only responsive layout adjustments.
    document.documentElement.style.setProperty("--mobile-keyboard-height", `${info.keyboardHeight}px`);
    // Mark keyboard-open state for focused native layout rules.
    document.documentElement.dataset.mobileKeyboard = "open";
  });
  // Subscribe to keyboard-hide events so stale overlap offsets are removed.
  await Keyboard.addListener("keyboardWillHide", () => {
    // Reset the measured overlap after the keyboard closes.
    document.documentElement.style.setProperty("--mobile-keyboard-height", "0px");
    // Mark keyboard-closed state for focused native layout rules.
    document.documentElement.dataset.mobileKeyboard = "closed";
  });
}

// Keep external HTTP navigation in the system browser instead of replacing the casino WebView.
function installExternalLinkHandling() {
  // Capture link activation before shared handlers can navigate the native WebView away.
  document.addEventListener("click", event => {
    // Resolve the nearest anchor so nested icon and text clicks behave consistently.
    const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
    // Ignore non-link interactions.
    if (!anchor) return;
    // Resolve the link against the bundled WebView origin.
    const destination = new URL(anchor.href, window.location.href);
    // Preserve local bundled routes and non-HTTP schemes for existing application handling.
    if (!["http:", "https:"].includes(destination.protocol) || destination.origin === window.location.origin) return;
    // Prevent the external destination from replacing the signed application surface.
    event.preventDefault();
    // Open the external destination with the platform browser plugin.
    void Browser.open({ url: destination.toString() });
  // Register the capture handler so external navigation cannot replace the signed WebView first.
  }, true);
}

// Load and validate public environment configuration before any shared application code executes.
async function loadConfig() {
  // Load the generated configuration from the signed local web bundle only.
  const response = await platformFetch("/mobile-config.json", { cache: "no-store", credentials: "omit" });
  // Fail closed when the bundle is missing its generated environment configuration.
  if (!response.ok) throw new Error("Mobile configuration is unavailable.");
  // Parse the generated public JSON configuration.
  const value = await response.json();
  // Return the same strictly validated structure enforced during the build.
  return validateMobileConfig(value);
}

// Append the shared module once and await its reusable controller separately from initial data readiness.
function ensureSharedApplicationController() {
  // Reuse the one controller load across failed readiness and later recovery attempts.
  if (sharedApplicationControllerPromise) return sharedApplicationControllerPromise;
  // Create a module script so the existing shared application remains an unmodified source asset.
  const script = document.createElement("script");
  // Preserve ES module semantics used by the existing application and game modules.
  script.type = "module";
  // Point to the bundled copy of the existing shared application entry point.
  script.src = "/app.js";
  // Retain the one initial application outcome without creating an unhandled rejected promise.
  let resolveInitialOutcome;
  // Build the initial result before module execution can dispatch ready or failure.
  sharedApplicationInitialOutcomePromise = new Promise(resolve => { resolveInitialOutcome = resolve; });
  // Build one controller promise before appending the sole shared entry point.
  sharedApplicationControllerPromise = new Promise((resolve, reject) => {
    // Retain module evaluation separately from shared asynchronous initialization readiness.
    let moduleLoaded = false;
    // Retain explicit controller construction separately from script evaluation.
    let controllerReady = false;
    // Resolve only after module evaluation and the reusable reconnect controller both exist.
    const complete = () => {
      // Preserve the pending state until both independent controller boundaries complete.
      if (!moduleLoaded || !controllerReady) return;
      // Reject a malformed shared handshake rather than allowing reconnect to be silently skipped.
      if (typeof window.CasinoPwa?.reconnect !== "function") { reject(new Error("Shared application recovery is unavailable.")); return; }
      // Return non-secret evidence that the sole shared controller is reusable.
      resolve(true);
    };
    // Record the explicit reusable-controller handshake and retry the joint boundary.
    const onControllerReady = () => { controllerReady = true; complete(); };
    // Resolve the initial data-readiness result without invalidating the reusable controller.
    const onReady = () => { resolveInitialOutcome(true); };
    // Preserve controller reuse after a data failure, but reject when controller construction itself failed.
    const onFailure = () => { resolveInitialOutcome(false); if (!controllerReady) reject(new Error("Shared application controller failed to initialize.")); };
    // Observe controller construction before module execution can dispatch it.
    window.addEventListener("casino:shared-app-controller-ready", onControllerReady, { once: true });
    // Observe the initial authoritative data readiness signal.
    window.addEventListener("casino:shared-app-ready", onReady, { once: true });
    // Observe the bounded initial failure signal.
    window.addEventListener("casino:shared-app-error", onFailure, { once: true });
    // Record completed module evaluation before checking the shared readiness handshake.
    script.addEventListener("load", () => { moduleLoaded = true; complete(); }, { once: true });
    // Reject a missing or invalid bundled module without exposing raw resource diagnostics.
    script.addEventListener("error", () => { resolveInitialOutcome(false); reject(new Error("Shared application module failed to load.")); }, { once: true });
    // Start the shared application after native transport and lifecycle gates are installed.
    document.body.append(script);
  });
  // Return the sole controller promise so later recovery never appends or reevaluates shared code.
  return sharedApplicationControllerPromise;
}

// Refresh through the required shared controller without optional success.
async function reconnectSharedApplication() {
  // Reject a missing shared recovery controller instead of treating refresh as successful.
  if (typeof window.CasinoPwa?.reconnect !== "function") throw new Error("Shared application recovery is unavailable.");
  // Refresh authoritative session, wallet, game, and route state through the existing controller.
  await window.CasinoPwa.reconnect();
}

// Run one shared load or reconnect under the exact post-probe reconciliation ticket.
async function reconcileSharedApplication(operation) {
  // Capture validated read authority before shared state can cross asynchronous boundaries.
  const ticket = lifecycleGate.beginReconciliation();
  // Complete the injected initial load or authoritative reconnect exactly once.
  await operation();
  // Release mutations only if process, vault, clock, and lifecycle authority stayed current.
  lifecycleGate.completeReconciliation(ticket);
  // Return bounded completion evidence to the recovery coordinator.
  return true;
}

// Load the shared application once, then recover failed initial data through the same controller.
async function loadSharedApplication() {
  // Return bounded success after one complete initial or recovered authoritative load.
  if (sharedApplicationLoaded) return true;
  // Share one current attempt without permanently caching its failure.
  if (sharedApplicationLoadInFlight) return sharedApplicationLoadInFlight;
  // Build the exact current load or recovery attempt.
  const pending = (async () => {
    // Append and construct the controller at most once across every attempt.
    await ensureSharedApplicationController();
    // Consume the one initial authoritative data result before using reconnect.
    if (!sharedApplicationInitialOutcomeConsumed) {
      // Mark the initial result claimed so a failure advances later attempts to reconnect.
      sharedApplicationInitialOutcomeConsumed = true;
      // Await the initial current-user/state boundary separately from module readiness.
      const ready = await sharedApplicationInitialOutcomePromise;
      // Reject a failed initial read without discarding the reusable controller.
      if (!ready) throw new Error("Shared application initial state is unavailable.");
    } else {
      // Reuse the same controller for a later authoritative recovery attempt.
      await reconnectSharedApplication();
    }
    // Mark warm route ownership only after initial data or later reconnect succeeds.
    sharedApplicationLoaded = true;
    // Return non-secret completion evidence to the recovery coordinator.
    return true;
  })();
  // Publish the pending attempt before yielding so direct overlapping callers coalesce.
  sharedApplicationLoadInFlight = pending;
  // Preserve the result while allowing a later event to retry after failure.
  try { return await pending; } finally { if (sharedApplicationLoadInFlight === pending) sharedApplicationLoadInFlight = null; }
}

// Install all native foundations in deterministic order before loading the shared product.
async function bootstrapMobileRuntime() {
  // Resolve and validate the environment-specific backend configuration first.
  const config = await loadConfig();
  // Install network gating before the first authenticated application request.
  await installNetworkLifecycle();
  // Install the API origin adapter before shared application modules can call fetch.
  await installApiTransport(config);
  // Build one exact-once recovery boundary after the native plugin is configured.
  mobileRecovery = createMobileRecoveryCoordinator({ revalidate: mobileTransport.revalidate, load: () => reconcileSharedApplication(loadSharedApplication), reconnect: () => reconcileSharedApplication(reconnectSharedApplication) });
  // Bind initial connectivity that may have arrived before coordinator construction.
  mobileRecovery.setConnected(latestNetworkConnected);
  // Install background and foreground notification foundations.
  await installAppLifecycle();
  // Install verified universal-link routing before shared application navigation begins.
  await installDeepLinkHandling(config);
  // Install keyboard overlap measurement for native-only responsive CSS.
  await installKeyboardLifecycle();
  // Install safe external-link navigation before shared content becomes interactive.
  installExternalLinkHandling();
  // Mark the document as a native mobile surface for scoped CSS and evidence.
  document.documentElement.dataset.mobileRuntime = "capacitor";
  // Revalidate and load now when online, or let the first successful reconnect load exactly once.
  await recoverMobileRuntime();
}

// Start native bootstrap and keep configuration failures closed to the shared application.
void bootstrapMobileRuntime().catch(() => {
  // Show a safe actionable failure without logging configuration or endpoint values.
  showStatus("App configuration is unavailable. Reinstall or contact the test administrator.", "configuration");
});
