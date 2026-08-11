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
// Import the shared strict configuration validator used by the build and native runtime.
import { validateMobileConfig } from "./config.js";

// Preserve the platform fetch implementation before installing the API-origin adapter.
const platformFetch = window.fetch.bind(window);
// Track native lifecycle state so backgrounding can stop new atomic API actions.
let appIsActive = true;
// Track native network state so unavailable connections fail before mutations start.
let networkIsConnected = navigator.onLine;

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

// Translate root-relative API requests to the configured backend without changing frozen paths.
function installApiTransport(config) {
  // Replace fetch only inside the generated mobile bundle, leaving browser behavior untouched.
  window.fetch = async (input, init = {}) => {
    // Normalize Request and string inputs to a URL string for API-path detection.
    const requestedUrl = input instanceof Request ? input.url : String(input);
    // Detect only frozen casino API paths; static assets continue to use the bundled WebView origin.
    const isApiRequest = requestedUrl.startsWith("/api/");
    // Preserve all non-API fetch behavior for bundled locale, style, and game assets.
    if (!isApiRequest) return platformFetch(input, init);
    // Resolve the effective method from Request or init values before enforcing lifecycle gates.
    const method = String(init.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
    // Block every new API request while offline so no money-moving action is queued or retried.
    if (!networkIsConnected) {
      // Tell the player why the requested action cannot start.
      showStatus("Network unavailable. Reconnect before continuing.", "offline");
      // Reject the action immediately without starting a native network request.
      throw new Error("MOBILE_NETWORK_UNAVAILABLE");
    }
    // Block new mutations while backgrounded while allowing an already-started request to finish.
    if (!appIsActive && !["GET", "HEAD", "OPTIONS"].includes(method)) throw new Error("MOBILE_APP_BACKGROUND");
    // Preserve the exact API path and query while replacing only the local WebView origin.
    const backendUrl = new URL(requestedUrl, `${config.backendBaseUrl}/`).toString();
    // Start the configured backend request with the original credentials and request options.
    try {
      // Send the request through the preserved platform fetch implementation.
      const response = await platformFetch(backendUrl, init);
      // Show a recoverable backend message for server-side availability failures.
      if (response.status >= 500) showStatus("Backend unavailable. Try again after service recovers.", "backend");
      // Clear stale connection messages after a successful backend response.
      else clearStatus();
      // Return the unchanged response so existing API envelope handling remains authoritative.
      return response;
    // Handle platform transport failures without exposing diagnostic details to the player.
    } catch (error) {
      // Show a generic availability message without exposing endpoint or exception details.
      showStatus("Backend unavailable. Check the connection and try again.", "backend");
      // Re-throw so existing application error handling receives the original failure.
      throw error;
    }
  };
}

// Keep native network state synchronized with runtime status and recovery events.
async function installNetworkLifecycle() {
  // Read the initial native connectivity state before shared application actions can start.
  const initialStatus = await Network.getStatus();
  // Store the native connectivity result as the runtime source of truth.
  networkIsConnected = initialStatus.connected;
  // Show the fail-closed offline state on cold launch when no network is available.
  if (!networkIsConnected) showStatus("Network unavailable. Reconnect before continuing.", "offline");
  // Subscribe to native connection changes for the lifetime of the WebView.
  await Network.addListener("networkStatusChange", status => {
    // Update the runtime gate before any later API action begins.
    networkIsConnected = status.connected;
    // Show the offline gate when connectivity is lost.
    if (!networkIsConnected) showStatus("Network unavailable. Reconnect before continuing.", "offline");
    // Clear stale offline copy after connectivity returns.
    else clearStatus();
    // Notify shared application code through an additive browser event foundation.
    window.dispatchEvent(new CustomEvent("casino:mobile-network", { detail: { connected: networkIsConnected, connectionType: status.connectionType } }));
  });
}

// Keep background and foreground state synchronized without owning game loops.
async function installAppLifecycle() {
  // Subscribe to native application activity changes.
  await App.addListener("appStateChange", state => {
    // Update the mutation gate before dispatching any lifecycle notification.
    appIsActive = state.isActive;
    // Expose the current lifecycle state to native-only CSS and diagnostics.
    document.documentElement.dataset.mobileAppState = appIsActive ? "active" : "background";
    // Notify shared modules through an additive event while preserving their public actions.
    window.dispatchEvent(new CustomEvent("casino:mobile-app-state", { detail: { isActive: appIsActive } }));
    // Re-read network state on foreground so resumed actions use current connectivity.
    if (appIsActive) void Network.getStatus().then(status => {
      // Refresh the runtime gate from the native network plugin.
      networkIsConnected = status.connected;
      // Show the offline recovery gate when the app resumes without a connection.
      if (!networkIsConnected) showStatus("Network unavailable. Reconnect before continuing.", "offline");
    });
  });
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

// Load the unchanged shared browser application only after native foundations are ready.
function loadSharedApplication() {
  // Create a module script so the existing shared application remains an unmodified source asset.
  const script = document.createElement("script");
  // Preserve ES module semantics used by the existing application and game modules.
  script.type = "module";
  // Point to the bundled copy of the existing shared application entry point.
  script.src = "/app.js";
  // Start the shared application after the native transport and lifecycle gates are installed.
  document.body.append(script);
}

// Install all native foundations in deterministic order before loading the shared product.
async function bootstrapMobileRuntime() {
  // Resolve and validate the environment-specific backend configuration first.
  const config = await loadConfig();
  // Install the API origin adapter before shared application modules can call fetch.
  installApiTransport(config);
  // Install network gating before the first authenticated application request.
  await installNetworkLifecycle();
  // Install background and foreground notification foundations.
  await installAppLifecycle();
  // Install keyboard overlap measurement for native-only responsive CSS.
  await installKeyboardLifecycle();
  // Install safe external-link navigation before shared content becomes interactive.
  installExternalLinkHandling();
  // Mark the document as a native mobile surface for scoped CSS and evidence.
  document.documentElement.dataset.mobileRuntime = "capacitor";
  // Load the unchanged shared casino application after all native guards are ready.
  loadSharedApplication();
}

// Start native bootstrap and keep configuration failures closed to the shared application.
void bootstrapMobileRuntime().catch(() => {
  // Show a safe actionable failure without logging configuration or endpoint values.
  showStatus("App configuration is unavailable. Reinstall or contact the test administrator.", "configuration");
});
