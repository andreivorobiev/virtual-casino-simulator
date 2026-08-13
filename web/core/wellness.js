// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Keep the smallest allowed reminder interval aligned with the server contract. (WELL-001)
export const MIN_WELLNESS_INTERVAL = 10;
// Keep the largest allowed reminder interval aligned with the server contract. (WELL-001)
export const MAX_WELLNESS_INTERVAL = 240;

// Normalize one server timestamp without allowing an invalid value to create an immediate reminder loop.
function sessionStartMilliseconds(session, now) {
  // Prefer the public session descriptor used across reloads and route changes.
  const raw = session?.session?.issued_at || session?.session?.created_at || session?.session_status?.issued_at;
  // Parse the server-owned timestamp into a wall-clock boundary.
  const parsed = Date.parse(String(raw || ''));
  // Fall back to the current clock only when an older compatible payload has no usable timestamp.
  return Number.isFinite(parsed) ? parsed : now();
}

// Read one session-local presentation record without treating corrupt storage as an opt-in choice.
function readLocalState(storage, key) {
  // Parse the bounded record inside a failure boundary for disabled or unavailable session storage.
  try {
    // Decode only the current authenticated session's opaque timing record.
    const record = JSON.parse(storage?.getItem(key) || '{}');
    // Return strict primitive values so malformed records cannot pause or skip reminders.
    return { lastSlot: Number.isInteger(record.lastSlot) && record.lastSlot >= 0 ? record.lastSlot : 0, paused: record.paused === true, intervalMinutes: Number.isInteger(record.intervalMinutes) && record.intervalMinutes >= MIN_WELLNESS_INTERVAL && record.intervalMinutes <= MAX_WELLNESS_INTERVAL ? record.intervalMinutes : null };
  // Degrade to an unpaused, undisplayed session when browser storage is unavailable.
  } catch (_) {
    // Preserve opt-in server authority while discarding only corrupt local presentation state.
    return { lastSlot: 0, paused: false, intervalMinutes: null };
  }
}

// Persist only timing presentation state, never player identity, amounts, or API results.
function writeLocalState(storage, key, state) {
  // Keep storage failure from interrupting gameplay or disabling the visible control.
  try {
    // Serialize the two bounded values needed to prevent duplicate reload reminders.
    storage?.setItem(key, JSON.stringify({ lastSlot: state.lastSlot, paused: state.paused, intervalMinutes: state.intervalMinutes }));
  // Ignore disabled browser storage because the active in-memory schedule remains safe.
  } catch (_) { /* Session storage is an optional reload-deduplication aid. */ }
}

// Create the persistent every-game session wellness controller. (WELL-001, WELL-002, issue #167)
export function createWellnessController(options = {}) {
  // Bind the authenticated API helper without granting the controller any other route authority.
  const apiClient = options.apiClient;
  // Bind the persistent document that owns the topbar control and native dialog.
  const documentRef = options.documentRef || globalThis.document;
  // Bind the current browser window for visibility, timers, and session-local storage.
  const windowRef = options.windowRef || globalThis.window;
  // Bind localization through the shell so the controller owns no resource-loading lifecycle.
  const translate = options.translate || ((key, values) => key.replace(/\{(\w+)\}/g, (_, name) => String(values?.[name] ?? '')));
  // Bind play-token formatting through the existing shell formatter.
  const formatTokens = options.formatTokens || (value => String(value));
  // Bind the wall clock so deterministic tests can cross reminder boundaries without sleeping.
  const now = options.now || (() => Date.now());
  // Bind the timer scheduler so every pending wakeup can be cancelled at session teardown.
  const scheduleTimer = options.setTimer || ((callback, delay) => windowRef.setTimeout(callback, delay));
  // Bind timer cancellation to the same injected clock domain.
  const cancelTimer = options.clearTimer || (handle => windowRef.clearTimeout(handle));
  // Cache the persistent topbar button supplied by index.html.
  const openButton = documentRef?.getElementById('wellness-open');
  // Cache the native dialog supplied by index.html.
  const dialog = documentRef?.getElementById('wellness-dialog');
  // Cache the settings form so server writes remain explicit submit actions.
  const form = documentRef?.getElementById('wellness-form');
  // Track the current controller generation across login, logout, and session replacement.
  let generation = 0;
  // Hold the active server wellness record under opt-in defaults.
  let settings = { enabled: false, break_reminder_enabled: false, reminder_interval_minutes: 30, revision: 0, persisted: false };
  // Hold the last authoritative neutral summary for locale-only rerenders.
  let summary = null;
  // Hold the server-owned session start used for absolute, drift-free cadence boundaries.
  let startedAt = 0;
  // Hold the opaque per-session storage key used only for presentation deduplication.
  let localKey = '';
  // Hold reload-stable pause and last-presented-slot state.
  let localState = { lastSlot: 0, paused: false, intervalMinutes: null };
  // Hold the only pending reminder wakeup.
  let timer = null;
  // Remember a reminder deferred while the document was hidden.
  let pendingVisibleReminder = false;
  // Preserve the invoking control so native dialog closure restores useful keyboard focus.
  let restoreFocus = null;

  // Return one persistent dialog node by id without caching stale route-owned elements.
  const node = id => documentRef?.getElementById(id);

  // Translate a shell wellness string with the established formatting contract.
  const copy = (key, values = {}) => translate(`wellness.${key}`, values);

  // Cancel the one scheduled cadence wakeup before replacing session or settings state.
  function clearSchedule() {
    // Cancel only when a real timer handle is retained.
    if (timer !== null) cancelTimer(timer);
    // Clear the handle so repeated teardown is idempotent.
    timer = null;
  }

  // Compute whole elapsed minutes from the server-owned session boundary.
  function elapsedMinutes() {
    // Clamp clock rollback to zero so no negative or pressure-style time appears.
    return Math.max(0, Math.floor((now() - startedAt) / 60000));
  }

  // Render settings, summary, and action state without changing cadence ownership.
  function render() {
    // Update the persistent topbar label for the active locale.
    if (openButton) { openButton.textContent = copy('open'); openButton.setAttribute('aria-label', copy('open')); }
    // Stop after persistent-control localization when the optional dialog markup is absent.
    if (!dialog) return;
    // Localize the dialog eyebrow alongside every other persistent-shell label.
    node('wellness-eyebrow').textContent = copy('eyebrow');
    // Localize the dialog heading and explanatory copy.
    node('wellness-title').textContent = copy('title');
    // Explain the off-by-default and player-controlled behavior.
    node('wellness-copy').textContent = copy('copy');
    // Publish elapsed time as neutral information rather than a countdown.
    node('wellness-elapsed').textContent = copy('elapsed', { minutes: elapsedMinutes() });
    // Localize every settings label and bounded-range hint.
    node('wellness-enable-label').textContent = copy('enable');
    // Localize the optional stopping-point suggestion control.
    node('wellness-break-label').textContent = copy('breakEnable');
    // Localize the cadence field label.
    node('wellness-interval-label').textContent = copy('interval');
    // Publish the server-aligned allowed cadence range.
    node('wellness-interval-help').textContent = copy('intervalRange', { min: MIN_WELLNESS_INTERVAL, max: MAX_WELLNESS_INTERVAL });
    // Localize explicit durable save behavior.
    node('wellness-save').textContent = copy('save');
    // Localize the neutral summary heading.
    node('wellness-summary-title').textContent = copy('summaryTitle');
    // Localize session-local pause or resume according to current state.
    node('wellness-pause').textContent = copy(localState.paused ? 'resume' : 'pause');
    // Localize the durable stop action without urgency.
    node('wellness-stop').textContent = copy('stop');
    // Localize the ordinary close action.
    node('wellness-dismiss').textContent = copy('dismiss');
    // Keep the screen-reader name synchronized with the visible localized close action.
    node('wellness-dismiss').setAttribute('aria-label', copy('dismiss'));
    // Synchronize the elapsed-reminder checkbox with the authoritative server record.
    node('wellness-enabled').checked = settings.enabled === true;
    // Synchronize the stopping-point suggestion checkbox with the authoritative server record.
    node('wellness-break-enabled').checked = settings.break_reminder_enabled === true;
    // Synchronize the bounded cadence field with the authoritative server record.
    node('wellness-interval').value = String(settings.reminder_interval_minutes || 30);
    // Disable pause and stop when elapsed reminders are already durably disabled.
    node('wellness-pause').disabled = settings.enabled !== true;
    // Disable stop when there is no enabled reminder to stop.
    node('wellness-stop').disabled = settings.enabled !== true;
    // Build neutral summary rows only from the latest server-owned result.
    const rows = summary ? [copy('summaryMovements', { count: summary.movements }), copy('summaryStaked', { amount: formatTokens(summary.staked) }), copy('summaryReturned', { amount: formatTokens(summary.returned) }), copy('summaryNet', { amount: formatTokens(summary.net) })] : [copy('summaryLoading')];
    // Replace the summary list with text-only rows so API data cannot become markup.
    node('wellness-summary').replaceChildren(...rows.map(value => { const item = documentRef.createElement('li'); item.textContent = value; return item; }));
    // Keep the play-token disclaimer visible beside every summary.
    node('wellness-summary-note').textContent = copy('summaryNote');
  }

  // Schedule the next absolute interval boundary without accumulating setTimeout drift.
  function scheduleNext() {
    // Cancel the prior wakeup before deriving a replacement.
    clearSchedule();
    // Stop when the user has not opted in or has paused reminders for this login session.
    if (settings.enabled !== true || localState.paused || !startedAt) return;
    // Convert the validated server cadence into milliseconds.
    const intervalMs = Number(settings.reminder_interval_minutes) * 60000;
    // Determine the currently elapsed complete cadence slot.
    const elapsedSlot = Math.max(0, Math.floor((now() - startedAt) / intervalMs));
    // Open a due reminder once when the current slot was not already presented.
    if (elapsedSlot >= 1 && elapsedSlot > localState.lastSlot) {
      // Defer presentation while hidden so background tabs never steal focus.
      if (documentRef.visibilityState === 'hidden') { pendingVisibleReminder = true; return; }
      // Present the due reminder through the same manual dialog surface.
      void open('reminder', elapsedSlot);
      // Stop because open schedules the following boundary after recording this slot.
      return;
    }
    // Schedule the first boundary strictly after both elapsed and last-presented slots.
    const nextSlot = Math.max(1, elapsedSlot + 1, localState.lastSlot + 1);
    // Bound browser delay while retaining an immediate recheck for very long sessions.
    const delay = Math.max(0, Math.min(startedAt + nextSlot * intervalMs - now(), 2147483647));
    // Wake once to re-evaluate visibility, settings, pause, and absolute elapsed time.
    timer = scheduleTimer(() => { timer = null; scheduleNext(); }, delay);
  }

  // Refresh the neutral active-session summary without inventing fallback totals.
  async function refreshSummary(capturedGeneration) {
    // Read only the authenticated session-owned additive summary route.
    const result = await apiClient('/api/v2/me/wellness/summary');
    // Ignore a response that belongs to a replaced or logged-out session.
    if (capturedGeneration !== generation) return false;
    // Adopt the complete server projection for text-only rendering.
    summary = result;
    // Repaint current locale and values without affecting timer state.
    render();
    // Signal that the exact current session adopted the response.
    return true;
  }

  // Open the shared dialog manually or for one due cadence slot.
  async function open(reason = 'manual', dueSlot = 0) {
    // Stop when no authenticated controller generation owns the persistent control.
    if (!generation || !dialog) return;
    // Preserve the current focus only when it is a real document element.
    restoreFocus = documentRef.activeElement instanceof windowRef.HTMLElement ? documentRef.activeElement : openButton;
    // Record a due slot before asynchronous summary I/O so reload cannot duplicate it.
    if (reason === 'reminder' && dueSlot > localState.lastSlot) { localState.lastSlot = dueSlot; pendingVisibleReminder = false; writeLocalState(windowRef.sessionStorage, localKey, localState); }
    // Capture the current generation across the summary request.
    const capturedGeneration = generation;
    // Clear stale status before announcing this explicit dialog state.
    node('wellness-message').textContent = reason === 'reminder' ? copy('reminder', { minutes: elapsedMinutes() }) : '';
    // Add the optional neutral stopping-point suggestion only when enabled.
    node('wellness-break-suggestion').textContent = reason === 'reminder' && settings.break_reminder_enabled ? copy('breakSuggestion') : '';
    // Render immediately so manual controls never wait on the summary endpoint.
    render();
    // Open the native modal once and let the browser own focus trapping and Escape.
    if (!dialog.open) dialog.showModal();
    // Move focus to the heading for a stable screen-reader entry point.
    node('wellness-title').focus();
    // Refresh totals while preserving the already-open usable settings UI.
    try { await refreshSummary(capturedGeneration); } catch (_) { if (capturedGeneration === generation) { summary = null; node('wellness-message').textContent = copy('summaryError'); render(); } }
    // Schedule the next absolute boundary after current presentation settles.
    if (capturedGeneration === generation) scheduleNext();
  }

  // Close the dialog and restore focus to its exact still-connected invoking control.
  function close() {
    // Close only an actually open native dialog.
    if (dialog?.open) dialog.close();
    // Restore focus only when the original element still belongs to this document.
    if (restoreFocus?.isConnected && !restoreFocus.disabled) restoreFocus.focus();
    // Drop the element reference so later route replacement cannot retain it.
    restoreFocus = null;
  }

  // Persist explicit settings form changes through optimistic concurrency.
  async function save(event) {
    // Keep the native dialog open while the bounded API request settles.
    event?.preventDefault?.();
    // Capture the active session generation across the write.
    const capturedGeneration = generation;
    // Disable repeated submission until the exact authoritative response returns.
    node('wellness-save').disabled = true;
    // Clear stale result copy before the new request.
    node('wellness-message').textContent = '';
    // Submit only the allowlisted server wellness fields.
    try {
      // Request one explicit opt-in configuration update.
      const result = await apiClient('/api/v2/me/wellness', { method: 'PATCH', body: { enabled: node('wellness-enabled').checked, break_reminder_enabled: node('wellness-break-enabled').checked, reminder_interval_minutes: Number(node('wellness-interval').value), revision: settings.revision } });
      // Ignore a response belonging to a cleared or replaced login session.
      if (capturedGeneration !== generation) return;
      // Remember the prior cadence so a changed interval cannot reuse incompatible slot numbering.
      const priorInterval = Number(settings.reminder_interval_minutes);
      // Adopt only the exact returned server record.
      settings = result.wellness;
      // Mark the elapsed position under a newly chosen cadence so saving cannot trigger or skip historical slots.
      if (Number(settings.reminder_interval_minutes) !== priorInterval) localState.lastSlot = Math.max(0, Math.floor((now() - startedAt) / (Number(settings.reminder_interval_minutes) * 60000)));
      // Bind subsequent reload deduplication to the cadence that defined the recorded slot.
      localState.intervalMinutes = Number(settings.reminder_interval_minutes);
      // Clear session-local pause when a new explicit configuration is saved.
      localState.paused = false;
      // Persist the local presentation state without exposing the settings payload.
      writeLocalState(windowRef.sessionStorage, localKey, localState);
      // Publish a calm saved acknowledgement.
      node('wellness-message').textContent = copy('saved');
      // Repaint and reschedule from the unchanged server session boundary.
      render(); scheduleNext();
    // Keep the prior authoritative state when validation, conflict, or transport fails.
    } catch (_) {
      // Publish one localized recoverable error without server detail.
      node('wellness-message').textContent = copy('saveError');
      // Restore the exact prior settings controls.
      render();
    // Always restore submission availability for the current dialog generation.
    } finally {
      // Re-enable only when this session still owns the controller.
      if (capturedGeneration === generation) node('wellness-save').disabled = false;
    }
  }

  // Pause or resume reminders only for the current login session.
  function togglePause() {
    // Stop when durable settings are already disabled.
    if (settings.enabled !== true) return;
    // Toggle the strictly session-local reminder suspension.
    localState.paused = !localState.paused;
    // Persist the pause across same-session reload without changing server preferences.
    writeLocalState(windowRef.sessionStorage, localKey, localState);
    // Publish the resulting state neutrally.
    node('wellness-message').textContent = copy(localState.paused ? 'paused' : 'resumed');
    // Repaint the action label and replace the schedule.
    render(); scheduleNext();
  }

  // Durably stop reminders through the same preference route as the settings form.
  async function stop() {
    // Stop when no enabled reminder exists.
    if (settings.enabled !== true) return;
    // Capture the active session before the durable write.
    const capturedGeneration = generation;
    // Lock both mutation controls while the exact request settles.
    node('wellness-stop').disabled = true; node('wellness-save').disabled = true;
    // Submit only the disabling switch and optimistic revision.
    try {
      // Request a durable opt-out without altering cadence or suggestion preference.
      const result = await apiClient('/api/v2/me/wellness', { method: 'PATCH', body: { enabled: false, revision: settings.revision } });
      // Ignore late success after logout or session replacement.
      if (capturedGeneration !== generation) return;
      // Adopt the exact returned opt-out record.
      settings = result.wellness;
      // Clear session-local pause now that the server switch is authoritative.
      localState.paused = false;
      // Persist deduplication state while leaving no amounts or identity in storage.
      writeLocalState(windowRef.sessionStorage, localKey, localState);
      // Cancel pending reminders immediately.
      clearSchedule(); pendingVisibleReminder = false;
      // Publish a calm durable-stop acknowledgement.
      node('wellness-message').textContent = copy('stopped');
      // Repaint disabled action state.
      render();
    // Keep reminders active when the server did not confirm the opt-out.
    } catch (_) {
      // Publish one recoverable error without claiming reminders stopped.
      node('wellness-message').textContent = copy('saveError');
      // Resume the prior authoritative schedule.
      render(); scheduleNext();
    // Restore settings submission for the current session.
    } finally {
      // Re-enable save when the same session still owns this controller.
      if (capturedGeneration === generation) node('wellness-save').disabled = false;
    }
  }

  // Start the controller from one authenticated server session.
  async function start(session) {
    // Advance generation first so every prior response loses ownership.
    generation += 1;
    // Capture the new generation across the initial settings request.
    const capturedGeneration = generation;
    // Cancel old wakeups and close any old-session dialog before reusing persistent nodes.
    clearSchedule(); close(); pendingVisibleReminder = false; summary = null;
    // Derive the absolute session boundary from public server metadata.
    startedAt = sessionStartMilliseconds(session, now);
    // Build one non-identifying session-local storage key from the server timestamp.
    localKey = `casino.wellness.v1.${startedAt}`;
    // Restore only pause and last-presented cadence slot for this exact login session.
    localState = readLocalState(windowRef.sessionStorage, localKey);
    // Keep the control hidden until the authenticated settings read succeeds.
    if (openButton) openButton.hidden = true;
    // Read the exact authenticated user's opt-in settings.
    try {
      // Call only the additive wellness preference route.
      const result = await apiClient('/api/v2/me/wellness');
      // Ignore a response after logout or another login replacement.
      if (capturedGeneration !== generation) return false;
      // Adopt the returned server record under strict booleans and validated cadence.
      settings = result.wellness;
      // Rebase a slot retained under another tab's old cadence without presenting historical intervals.
      if (localState.intervalMinutes !== null && localState.intervalMinutes !== Number(settings.reminder_interval_minutes)) localState.lastSlot = Math.max(0, Math.floor((now() - startedAt) / (Number(settings.reminder_interval_minutes) * 60000)));
      // Record the authoritative cadence used to interpret the current slot number.
      localState.intervalMinutes = Number(settings.reminder_interval_minutes);
      // Persist cadence binding while retaining only bounded presentation metadata.
      writeLocalState(windowRef.sessionStorage, localKey, localState);
      // Reveal the every-game control for this authenticated shell.
      if (openButton) openButton.hidden = false;
      // Render the active locale and schedule the next absolute boundary.
      render(); scheduleNext();
      // Signal successful ownership-aware start.
      return true;
    // Keep the optional feature unavailable when an older or failed server lacks the route.
    } catch (_) {
      // Hide the control and leave gameplay unaffected.
      if (capturedGeneration === generation && openButton) openButton.hidden = true;
      // Report optional-controller unavailability without throwing through authenticated entry.
      return false;
    }
  }

  // Dispose all session-owned work at logout, expiry, or replacement.
  function dispose() {
    // Advance generation so every outstanding request becomes stale.
    generation += 1;
    // Cancel pending cadence work and hidden-tab delivery.
    clearSchedule(); pendingVisibleReminder = false;
    // Close the native dialog before authenticated shell identity is cleared.
    close();
    // Hide the authenticated-only persistent control.
    if (openButton) openButton.hidden = true;
    // Clear in-memory API projections without altering durable user settings.
    settings = { enabled: false, break_reminder_enabled: false, reminder_interval_minutes: 30, revision: 0, persisted: false }; summary = null; startedAt = 0; localKey = '';
  }

  // Deliver one deferred reminder only after the document becomes visible again.
  function handleVisibility() {
    // Stop unless one due reminder is waiting and the current session still owns the controller.
    if (!pendingVisibleReminder || documentRef.visibilityState === 'hidden' || !generation) return;
    // Re-evaluate the exact current cadence slot before presentation.
    const intervalMs = Number(settings.reminder_interval_minutes) * 60000;
    // Derive the due slot from the absolute server-owned boundary.
    const slot = Math.max(1, Math.floor((now() - startedAt) / intervalMs));
    // Present once through the normal reminder path.
    void open('reminder', slot);
  }

  // Bind the persistent manual-open control once for the application lifetime.
  if (openButton) openButton.addEventListener('click', () => void open('manual'));
  // Bind explicit settings submission once for the application lifetime.
  if (form) form.addEventListener('submit', save);
  // Bind the session-local pause/resume control.
  node('wellness-pause')?.addEventListener('click', togglePause);
  // Bind the durable stop control.
  node('wellness-stop')?.addEventListener('click', () => void stop());
  // Bind both visible close controls to the same focus-restoring boundary.
  node('wellness-dismiss')?.addEventListener('click', close);
  // Restore focus after native Escape closure as well as explicit close.
  dialog?.addEventListener('close', () => { if (restoreFocus?.isConnected && !restoreFocus.disabled) restoreFocus.focus(); restoreFocus = null; });
  // Listen for hidden-tab return without polling in the background.
  documentRef?.addEventListener('visibilitychange', handleVisibility);

  // Expose only shell lifecycle and deterministic inspection needed by app wiring and tests.
  return Object.freeze({ start, dispose, open, close, localize: render, snapshot: () => ({ enabled: settings.enabled === true, breakEnabled: settings.break_reminder_enabled === true, intervalMinutes: settings.reminder_interval_minutes, paused: localState.paused, lastSlot: localState.lastSlot, pendingVisibleReminder, startedAt, scheduled: timer !== null }) });
}
