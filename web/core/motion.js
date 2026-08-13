// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Define the platform preference queried by every reduced-motion decision.
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

// Cover reload, history navigation, and hash-route navigation by default.
const DEFAULT_MOTION_LIFECYCLE_EVENTS = Object.freeze(["pagehide", "beforeunload", "popstate", "hashchange"]);

// Read the current platform preference through an injectable matchMedia seam.
export function prefersReducedMotion(matchMedia = globalThis.matchMedia) {
  // Treat unsupported environments as motion-capable without throwing.
  if (typeof matchMedia !== "function") return false;
  return Boolean(matchMedia.call(globalThis, REDUCED_MOTION_QUERY)?.matches); // Normalize the media-query result to a boolean.
}

// Resolve a requested animation duration against an explicit or platform preference.
function resolveMotionDuration(duration, { reducedMotion, matchMedia } = {}) {
  // Reject negative, infinite, or nonnumeric durations before scheduling.
  if (!Number.isFinite(duration) || duration < 0) throw new RangeError("duration must be a finite non-negative number");
  // Require explicit overrides to be booleans so configuration mistakes remain visible.
  if (reducedMotion !== undefined && typeof reducedMotion !== "boolean") throw new TypeError("reducedMotion must be a boolean when provided");
  const shouldReduce = reducedMotion ?? prefersReducedMotion(matchMedia); // Prefer a caller override, then query the platform.
  return shouldReduce ? 0 : duration; // Collapse decorative timing while preserving asynchronous scheduling.
}

// Create one disposable timer scope for a route, view, or animation lifecycle.
export function createMotionTimerScope({
  setTimeoutFn = globalThis.setTimeout, // Accept an injected scheduler for deterministic tests.
  clearTimeoutFn = globalThis.clearTimeout, // Accept the matching injected cancellation function.
  matchMedia, // Accept an injected preference query for non-browser tests.
  reducedMotion, // Accept a stable scope-wide preference override.
  lifecycleTarget = globalThis.window, // Bind cleanup to the current browser window by default.
  lifecycleEvents = DEFAULT_MOTION_LIFECYCLE_EVENTS, // Bind the standard route and reload exit signals.
} = {}) { // Finish destructuring the optional scope configuration.
  // Require timer functions so deterministic clocks can replace platform timers safely.
  if (typeof setTimeoutFn !== "function" || typeof clearTimeoutFn !== "function") throw new TypeError("timer functions must be callable");
  // Validate a scope-wide reduced-motion override once at construction.
  if (reducedMotion !== undefined && typeof reducedMotion !== "boolean") throw new TypeError("reducedMotion must be a boolean when provided");
  const events = Array.from(lifecycleEvents); // Snapshot lifecycle events so later caller mutation cannot change cleanup.
  // Require every lifecycle event to be a non-empty event name.
  if (events.some((eventName) => typeof eventName !== "string" || eventName.length === 0)) throw new TypeError("lifecycle events must be non-empty strings");
  const activeEntries = new Set(); // Track every pending callback owned by this scope.
  const tokenEntries = new Map(); // Map public cancellation tokens to private timer entries.
  let disposed = false; // Prevent callbacks or new work after route teardown.

  // Cancel one private entry and remove all references to it.
  function cancelEntry(entry) {
    // Report a no-op when the entry already ran or was cancelled.
    if (!activeEntries.has(entry)) return false;
    activeEntries.delete(entry); // Remove the timer from the active scope first.
    tokenEntries.delete(entry.token); // Release the public-token mapping.
    clearTimeoutFn(entry.handle); // Cancel the underlying platform or fake-clock handle.
    return true; // Tell callers that a pending callback was cancelled.
  }

  // Cancel one timer by its opaque public token.
  function cancel(token) {
    const entry = tokenEntries.get(token); // Resolve the private timer entry without exposing its handle.
    return entry ? cancelEntry(entry) : false; // Cancel known tokens and safely ignore stale tokens.
  }

  // Cancel all callbacks currently owned by this route or view.
  function cancelAll() {
    const entries = Array.from(activeEntries); // Snapshot entries because cancellation mutates the set.
    // Cancel every pending timer through the shared cleanup path.
    for (const entry of entries) cancelEntry(entry);
    return entries.length; // Return the number of callbacks that were pending.
  }

  // Remove lifecycle listeners after disposing or abandoning a scope.
  function removeLifecycleListeners() {
    // Skip listener work for non-browser or deliberately detached targets.
    if (typeof lifecycleTarget?.removeEventListener !== "function") return;
    // Remove the exact handler registered for every configured lifecycle event.
    for (const eventName of events) lifecycleTarget.removeEventListener(eventName, handleLifecycleExit);
  }

  // Dispose the scope when navigation or reload begins.
  function handleLifecycleExit() {
    dispose(); // Reuse explicit teardown so every exit path has identical cleanup.
  }

  // Permanently stop this scope and prevent stale callbacks after teardown.
  function dispose() {
    // Make repeated teardown calls harmless for overlapping route/reload events.
    if (disposed) return 0;
    disposed = true; // Guard callbacks before cancelling their platform handles.
    const cancelledCount = cancelAll(); // Cancel every callback that has not started.
    removeLifecycleListeners(); // Release browser event listener references.
    return cancelledCount; // Expose cleanup evidence to consumers and tests.
  }

  // Schedule one callback using reduced-motion-aware timing.
  function schedule(callback, duration, options = {}) {
    // Prevent new animation work from entering a disposed route scope.
    if (disposed) throw new Error("motion timer scope is disposed");
    // Require a callable callback before allocating timer state.
    if (typeof callback !== "function") throw new TypeError("callback must be a function");
    const effectiveDuration = resolveMotionDuration(duration, { // Resolve timing at schedule time so live preferences are honored.
      reducedMotion: options.reducedMotion ?? reducedMotion, // Allow one-call overrides before the scope default.
      matchMedia: options.matchMedia ?? matchMedia, // Allow deterministic preference hooks per scheduled action.
    });
    const entry = { handle: undefined, token: undefined }; // Create private state before invoking an injected scheduler.
    const token = Object.freeze({ cancel: () => cancelEntry(entry) }); // Give consumers an opaque self-cancelling handle.
    entry.token = token; // Connect private entry cleanup to the public token.
    activeEntries.add(entry); // Register ownership before the timer can fire.
    tokenEntries.set(token, entry); // Enable scope-level cancellation by token.
    // Run the callback only while its owning route scope remains active.
    const run = () => {
      // Ignore callbacks already cancelled by teardown or explicit cancellation.
      if (!activeEntries.delete(entry)) return;
      tokenEntries.delete(token); // Release token state before user code executes.
      // Execute only while the scope is live, guarding even unusual synchronous schedulers.
      if (!disposed) callback();
    };
    // Protect scope state when an injected or platform scheduler rejects the request.
    try {
      entry.handle = setTimeoutFn(run, effectiveDuration); // Schedule through the deterministic timing seam.
    } catch (error) { // Handle scheduler failures without leaking scope ownership.
      activeEntries.delete(entry); // Roll back active ownership after scheduler failure.
      tokenEntries.delete(token); // Roll back the cancellation mapping after scheduler failure.
      throw error; // Preserve the scheduler's original diagnostic.
    }
    return token; // Return the opaque cancellation token to the caller.
  }

  // Attach automatic navigation and reload cleanup when a browser-like target exists.
  if (typeof lifecycleTarget?.addEventListener === "function") {
    // Register the same teardown handler for every configured lifecycle event.
    for (const eventName of events) lifecycleTarget.addEventListener(eventName, handleLifecycleExit);
  }

  // Expose the minimal lifecycle API needed by dice, wheel, and future animated games.
  return Object.freeze({
    schedule, // Schedule one reduced-motion-aware callback.
    cancel, // Cancel one callback by token.
    cancelAll, // Cancel all callbacks without disposing the scope.
    dispose, // Cancel all callbacks and permanently tear down the scope.
    get activeCount() { return activeEntries.size; }, // Report current pending callback ownership.
    get disposed() { return disposed; }, // Report whether route teardown has completed.
  });
}
