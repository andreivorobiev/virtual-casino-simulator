// Create a manually advanced timer implementation for exact timing assertions.
export function createFakeClock() {
  let now = 0; // Track deterministic fake time in milliseconds.
  let nextHandle = 1; // Allocate stable numeric timer handles.
  const tasks = new Map(); // Store pending callbacks by handle.
  // Register one callback at an exact fake deadline.
  function setTimeoutFn(callback, delay) {
    const handle = nextHandle; // Capture the next stable handle.
    nextHandle += 1; // Advance handle allocation for the next timer.
    tasks.set(handle, { callback, deadline: now + delay }); // Store the scheduled callback and deadline.
    return handle; // Match the platform timer return contract.
  }
  // Remove one pending fake timer.
  function clearTimeoutFn(handle) {
    tasks.delete(handle); // Make clearing stale handles harmless.
  }
  // Advance fake time and execute all callbacks due in stable handle order.
  function advance(milliseconds) {
    now += milliseconds; // Move the fake clock forward exactly once.
    let executed = true; // Enter the drain loop for callbacks due at this time.
    // Drain callbacks that schedule additional immediately due callbacks.
    while (executed) {
      executed = false; // Assume no due callback remains until one is found.
      const dueTasks = [...tasks.entries()].filter(([, task]) => task.deadline <= now).sort(([left], [right]) => left - right); // Select due callbacks deterministically.
      // Execute each due callback once after removing its timer handle.
      for (const [handle, task] of dueTasks) {
        if (!tasks.delete(handle)) continue; // Skip a timer cancelled by an earlier callback.
        executed = true; // Repeat the drain pass in case this callback schedules more work.
        task.callback(); // Run the callback at the controlled fake time.
      }
    }
  }
  return { setTimeoutFn, clearTimeoutFn, advance, pendingCount: () => tasks.size }; // Expose only deterministic clock controls.
}

// Create a minimal event target for navigation and reload cleanup tests.
export function createLifecycleTarget() {
  const listeners = new Map(); // Store listeners by event name.
  // Register one lifecycle listener.
  function addEventListener(eventName, listener) {
    const eventListeners = listeners.get(eventName) ?? new Set(); // Reuse or create the event listener set.
    eventListeners.add(listener); // Register the callback once through Set semantics.
    listeners.set(eventName, eventListeners); // Persist the listener set for dispatch.
  }
  // Remove one lifecycle listener.
  function removeEventListener(eventName, listener) {
    listeners.get(eventName)?.delete(listener); // Ignore already removed event registrations.
  }
  // Dispatch one lifecycle event to a stable listener snapshot.
  function dispatch(eventName) {
    for (const listener of [...(listeners.get(eventName) ?? [])]) listener(); // Allow listeners to remove themselves safely.
  }
  // Count all currently registered listeners.
  function listenerCount() {
    return [...listeners.values()].reduce((total, eventListeners) => total + eventListeners.size, 0); // Sum listener ownership across events.
  }
  return { addEventListener, removeEventListener, dispatch, listenerCount }; // Expose browser-compatible lifecycle operations.
}

// Create an injectable matchMedia helper with one stable preference result.
export function createMatchMedia(matches) {
  // Require a boolean preference so tests cannot silently depend on coercion.
  if (typeof matches !== "boolean") throw new TypeError("matches must be a boolean");
  return (query) => ({ matches, media: query }); // Echo the query while returning the configured preference.
}
