// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Define the platform preference queried by every reduced-motion decision.
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

// Cover reload, history navigation, and hash-route navigation by default.
export const DEFAULT_MOTION_LIFECYCLE_EVENTS = Object.freeze(["pagehide", "beforeunload", "popstate", "hashchange"]);

// Read the current platform preference through an injectable matchMedia seam.
export function prefersReducedMotion(matchMedia = globalThis.matchMedia) {
  // Treat unsupported environments as motion-capable without throwing.
  if (typeof matchMedia !== "function") return false;
  return Boolean(matchMedia.call(globalThis, REDUCED_MOTION_QUERY)?.matches); // Normalize the media-query result to a boolean.
}

// Resolve a requested animation duration against an explicit or platform preference.
export function resolveMotionDuration(duration, { reducedMotion, matchMedia } = {}) {
  // Reject negative, infinite, or nonnumeric durations before scheduling.
  if (!Number.isFinite(duration) || duration < 0) throw new RangeError("duration must be a finite non-negative number");
  // Require explicit overrides to be booleans so configuration mistakes remain visible.
  if (reducedMotion !== undefined && typeof reducedMotion !== "boolean") throw new TypeError("reducedMotion must be a boolean when provided");
  const shouldReduce = reducedMotion ?? prefersReducedMotion(matchMedia); // Prefer a caller override, then query the platform.
  return shouldReduce ? 0 : duration; // Collapse decorative timing while preserving asynchronous scheduling.
}

// Publish the complete presentation-only lifecycle vocabulary shared by animated games. (MOTION-004)
export const MOTION_PHASES = Object.freeze(["idle", "locking", "running", "settling", "settled", "failed", "aborted"]);

// Define the only legal forward and recovery transitions for authoritative-result presentation. (MOTION-004)
const MOTION_PHASE_TRANSITIONS = Object.freeze({
  idle: Object.freeze(["locking"]), // Start one atomic presentation from the actionable idle phase.
  locking: Object.freeze(["running", "failed", "aborted"]), // Permit startup, bounded failure, or cancellation after controls lock.
  running: Object.freeze(["settling", "failed", "aborted"]), // Require an authoritative result before presentation can settle.
  settling: Object.freeze(["settled", "failed", "aborted"]), // Finish, fail, or cancel the committed presentation exactly once.
  settled: Object.freeze(["locking", "idle"]), // Allow the next atomic action or an explicit idle reset.
  failed: Object.freeze(["idle"]), // Require explicit recovery before another action can begin.
  aborted: Object.freeze(["idle"]), // Require explicit recovery after navigation or user cancellation.
});

// Validate one named phase before it enters lifecycle state or diagnostics. (MOTION-004)
function requireMotionPhase(phase) {
  // Reject unknown or non-string phase names so internal states cannot silently diverge.
  if (typeof phase !== "string" || !MOTION_PHASES.includes(phase)) throw new RangeError(`unknown motion phase: ${String(phase)}`);
  return phase; // Return the validated value for compact constructor use.
}

// Build one immutable named timing profile with deterministic reduced-motion resolution. (MOTION-005)
export function createMotionTimingProfile({ normal, fast = normal, reduced = 0 } = {}) {
  // Validate every budget through the same finite non-negative duration contract.
  const normalDuration = resolveMotionDuration(normal, { reducedMotion: false });
  const fastDuration = resolveMotionDuration(fast, { reducedMotion: false });
  const reducedDuration = resolveMotionDuration(reduced, { reducedMotion: false });
  // Prevent a nominal fast mode from taking longer than the normal presentation.
  if (fastDuration > normalDuration) throw new RangeError("fast motion duration must not exceed normal duration");
  // Prevent the comfort path from taking longer than the already-shortened fast mode.
  if (reducedDuration > fastDuration) throw new RangeError("reduced motion duration must not exceed fast duration");
  // Resolve one mode while honoring a live platform preference unless explicitly overridden.
  function resolve(mode = "normal", { reducedMotion, matchMedia } = {}) {
    // Require explicit preference overrides to remain boolean.
    if (reducedMotion !== undefined && typeof reducedMotion !== "boolean") throw new TypeError("reducedMotion must be a boolean when provided");
    const shouldReduce = reducedMotion ?? prefersReducedMotion(matchMedia); // Re-read the live preference at each action boundary.
    // Return the comfort budget before interpreting the normal or fast presentation mode.
    if (shouldReduce) return reducedDuration;
    // Return the reviewed normal duration for the default presentation mode.
    if (mode === "normal") return normalDuration;
    // Return the reviewed shortened duration for an explicitly supported fast mode.
    if (mode === "fast") return fastDuration;
    throw new RangeError(`unknown motion timing mode: ${String(mode)}`); // Reject silent mode fallback.
  }
  // Freeze budgets and the resolver so callers cannot mutate an accepted timing contract.
  return Object.freeze({ normal: normalDuration, fast: fastDuration, reduced: reducedDuration, resolve });
}

// Create one explicit presentation lifecycle that never chooses or mutates an authoritative result. (MOTION-004)
export function createMotionLifecycle({ initialPhase = "idle", onTransition = () => {} } = {}) {
  let phase = requireMotionPhase(initialPhase); // Store one validated current phase.
  // Restrict construction to inactive states so no action begins without an ownership token.
  if (!["idle", "settled", "failed", "aborted"].includes(phase)) throw new RangeError("initial motion phase must be inactive");
  // Require an observer callback so transition telemetry remains deterministic.
  if (typeof onTransition !== "function") throw new TypeError("onTransition must be a function");
  let generation = 0; // Allocate monotonically increasing action identities.
  let activeToken = null; // Retain only the token for the current atomic presentation.
  let authoritativeResult; // Preserve the exact server-owned result reference after commit.
  let disposed = false; // Prevent route-abandoned lifecycle reuse.

  // Return an immutable low-cardinality view of current presentation state.
  function snapshot() {
    // Expose the authoritative object by identity without copying, deriving, or modifying it.
    return Object.freeze({ phase, generation, active: activeToken !== null, authoritativeResult });
  }

  // Move through one reviewed phase edge and notify the observer after state is current.
  function transition(nextPhase) {
    const validatedNextPhase = requireMotionPhase(nextPhase); // Validate the destination before reading the transition graph.
    // Reject skipped, reversed, or duplicate lifecycle phases.
    if (!MOTION_PHASE_TRANSITIONS[phase].includes(validatedNextPhase)) throw new Error(`illegal motion transition: ${phase} -> ${validatedNextPhase}`);
    phase = validatedNextPhase; // Commit the phase before observers inspect the snapshot.
    onTransition(snapshot()); // Publish only the immutable presentation state.
  }

  // Report whether a caller still owns the current action generation.
  function owns(token) {
    return !disposed && token !== null && token === activeToken; // Reject disposed, absent, stale, and forged tokens.
  }

  // Begin one action and return its opaque ownership token.
  function begin() {
    // Prevent new motion work after the owning route or view is disposed.
    if (disposed) throw new Error("motion lifecycle is disposed");
    // Reject overlap while a prior atomic presentation still owns the lifecycle.
    if (activeToken !== null) throw new Error("motion lifecycle already has an active action");
    // Require explicit recovery after failure or cancellation.
    if (phase === "failed" || phase === "aborted") throw new Error(`motion lifecycle must reset after ${phase}`);
    generation += 1; // Advance the action identity before publishing the locking phase.
    activeToken = Object.freeze({ generation }); // Create an opaque identity token that callers cannot rewrite.
    authoritativeResult = undefined; // Clear only presentation state from the completed prior action.
    transition("locking"); // Lock controls before any asynchronous work starts.
    return activeToken; // Return ownership for guarded future transitions.
  }

  // Enter the running presentation phase for the current action.
  function run(token) {
    // Ignore stale asynchronous callbacks instead of letting them alter a newer action.
    if (!owns(token)) return false;
    transition("running"); // Require the reviewed locking-to-running edge.
    return true; // Confirm that the current action advanced.
  }

  // Bind one already-authoritative result and enter settlement presentation.
  function commit(token, result) {
    // Ignore stale results that arrive after abort, recovery, or a newer action.
    if (!owns(token)) return false;
    // Reject an absent result because presentation must never invent a fallback outcome.
    if (result === undefined) throw new TypeError("authoritative result is required");
    // Require the action to be visibly running before accepting its authoritative result.
    if (phase !== "running") throw new Error(`cannot commit authoritative result during ${phase}`);
    authoritativeResult = result; // Retain the exact result reference without mutation or projection.
    transition("settling"); // Reveal only after the authoritative result is bound.
    return true; // Confirm that this action entered settlement.
  }

  // Complete settlement for the current authoritative result.
  function settle(token) {
    // Ignore stale callbacks from an older or cancelled generation.
    if (!owns(token)) return false;
    activeToken = null; // Release ownership before observers inspect the terminal state.
    transition("settled"); // Complete the only legal settling-to-settled edge.
    return true; // Confirm that settlement completed.
  }

  // End the active presentation through one bounded failure state.
  function fail(token) {
    // Ignore stale failure callbacks that no longer own the current action.
    if (!owns(token)) return false;
    activeToken = null; // Release the failed action before observers inspect the terminal state.
    transition("failed"); // Enter the explicit failure phase from any active phase that permits it.
    return true; // Confirm that the failure applied to the current action.
  }

  // End the active presentation through one explicit cancellation state.
  function abort(token) {
    // Ignore stale cancellation callbacks that no longer own the current action.
    if (!owns(token)) return false;
    activeToken = null; // Release the cancelled action before observers inspect the terminal state.
    transition("aborted"); // Enter the explicit cancellation phase from the active graph.
    return true; // Confirm that cancellation applied to the current action.
  }

  // Recover a completed, failed, or aborted lifecycle to its actionable idle state.
  function reset() {
    // Prevent any recovery mutation after the owning route or view is disposed.
    if (disposed) throw new Error("motion lifecycle is disposed");
    // Prevent reset from racing an active atomic presentation.
    if (activeToken !== null) throw new Error("cannot reset an active motion lifecycle");
    // Make repeated idle recovery harmless.
    if (phase === "idle") return false;
    authoritativeResult = undefined; // Release the prior presentation result before observers inspect recovery.
    transition("idle"); // Use the reviewed terminal-to-idle recovery edge.
    return true; // Confirm that recovery changed state.
  }

  // Dispose the lifecycle so route-abandoned callbacks can never change presentation state.
  function dispose() {
    // Make repeated teardown calls harmless.
    if (disposed) return false;
    // Mark any active presentation aborted before invalidating its token.
    if (activeToken !== null) abort(activeToken);
    disposed = true; // Permanently reject future ownership and action starts.
    activeToken = null; // Ensure no opaque token remains current after teardown.
    return true; // Confirm that teardown occurred.
  }

  // Expose only the deterministic presentation operations and immutable state reader.
  return Object.freeze({
    begin, // Start one non-overlapping atomic presentation.
    run, // Advance its visible motion after controls lock.
    commit, // Bind the exact authoritative result before reveal.
    settle, // Complete visible settlement once.
    fail, // Enter explicit recoverable failure.
    abort, // Enter explicit recoverable cancellation.
    reset, // Recover terminal state to idle.
    dispose, // Permanently invalidate route-owned callbacks.
    snapshot, // Read immutable current state.
  });
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
