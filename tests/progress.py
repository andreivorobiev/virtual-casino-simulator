"""Flushed progress, heartbeat, stall, timeout, and cleanup reporting for TEST-010/TEST-042."""

# Import the low-level main-thread interrupt used to stop a timed-out synchronous suite.
import _thread
# Import regular expressions for secret-safe single-line labels.
import re
# Import stdout so callers do not need to pass a stream in normal CI runs.
import sys
# Import threading primitives for the lightweight watchdog and idempotent cleanup.
import threading
# Import a monotonic clock so elapsed durations cannot move backwards.
import time

# Keep every progress label on one sanitized line and exclude shell metacharacters.
SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9_.:/# -]+")


# Normalize a runner-owned phase or test label before writing it to CI logs.
def sanitize_label(value):
    # Replace newlines and unsupported characters without exposing arbitrary raw values.
    cleaned = SAFE_LABEL_RE.sub("?", str(value).replace("\r", " ").replace("\n", " "))
    # Collapse repeated whitespace so every event remains compact and machine-readable.
    return " ".join(cleaned.split())[:120] or "unknown"


# Report progress for one synchronous suite while a daemon watchdog observes its main thread.
class ProgressReporter:
    # Build one reporter with bounded heartbeat cadence and injectable test seams.
    def __init__(self, total, heartbeat_seconds=45.0, stall_seconds=180.0, timeout_seconds=2700.0, stream=None, clock=None, timeout_trigger=None, interrupt_grace_seconds=5.0):
        # Reject empty or negative cadence values that could spin the watchdog.
        if heartbeat_seconds <= 0 or heartbeat_seconds > 60:
            # Keep the public acceptance bound explicit for CLI and unit-test callers.
            raise ValueError("heartbeat_seconds must be greater than 0 and at most 60")
        # Reject stall thresholds that would warn before one heartbeat can be observed.
        if stall_seconds < heartbeat_seconds:
            # Keep warnings meaningful rather than immediately noisy.
            raise ValueError("stall_seconds must be at least heartbeat_seconds")
        # Reject non-positive real timeouts because they cannot supervise useful work.
        if timeout_seconds <= 0:
            # Require callers to choose an explicit positive suite deadline.
            raise ValueError("timeout_seconds must be greater than 0")
        # Store the exact number of named tests or scenarios planned for this suite.
        self.total = max(0, int(total))
        # Store the accepted heartbeat interval used by the watchdog.
        self.heartbeat_seconds = float(heartbeat_seconds)
        # Store the no-progress warning threshold without turning it into a failure.
        self.stall_seconds = float(stall_seconds)
        # Store the hard suite deadline that produces a non-zero timeout exit.
        self.timeout_seconds = float(timeout_seconds)
        # Default to process stdout so GitHub Actions receives the same live stream.
        self.stream = stream or sys.stdout
        # Default to a monotonic clock while allowing deterministic focused tests.
        self.clock = clock or time.monotonic
        # Default to raising KeyboardInterrupt on the synchronous suite's main thread.
        self.timeout_trigger = timeout_trigger or _thread.interrupt_main
        # Allow cleanup-driven I/O failure to unwind normally before interrupting as a fallback.
        self.interrupt_grace_seconds = max(0.0, float(interrupt_grace_seconds))
        # Serialize state changes and stream writes across the runner and watchdog threads.
        self._lock = threading.RLock()
        # Serialize cleanup so timeout and normal-finally paths cannot stop a child twice.
        self._cleanup_lock = threading.Lock()
        # Wake or stop the watchdog without an unbounded sleep.
        self._stop_event = threading.Event()
        # Let the main runner acknowledge timeout before the watchdog sends a fallback interrupt.
        self._timeout_ack_event = threading.Event()
        # Delay watchdog creation until start so focused tests can poll manually.
        self._thread = None
        # Initialize timing state when the reporter is started.
        self._started_at = None
        # Track the last emitted heartbeat separately from test progress.
        self._last_heartbeat_at = None
        # Track the last phase change or terminal test result for stall detection.
        self._last_progress_at = None
        # Track when the currently active test or phase began.
        self._current_started_at = None
        # Keep the current phase available in every heartbeat.
        self._phase = "not-started"
        # Keep the current named test or scenario when one is active.
        self._current_item = None
        # Count terminal named items without changing pass/fail semantics.
        self._completed = 0
        # Emit at most one stall warning until forward progress resumes.
        self._stall_warned = False
        # Record the hard-timeout transition for caller exit-code handling.
        self._timed_out = False
        # Store the caller-provided exact-child cleanup callback when available.
        self._cleanup_callback = None
        # Store cleanup evidence for the normal finally path and JSON artifacts.
        self._cleanup_result = None
        # Store a sanitized cleanup failure type without logging raw environment details.
        self._cleanup_error = None
        # Record whether cleanup has already been attempted.
        self._cleanup_attempted = False

    # Return whether the watchdog reached the configured real timeout.
    @property
    def timed_out(self):  # Expose the watchdog deadline transition.
        # Read the timeout flag under the shared state lock.
        with self._lock:
            # Return the immutable transition state to the suite runner.
            return self._timed_out

    # Return a fixed CI-friendly timeout exit code.
    @property
    def timeout_exit_code(self):  # Expose the stable non-zero timeout status.
        # Use the conventional timeout status without depending on platform signals.
        return 124

    # Return a sanitized cleanup error type when tracked cleanup failed.
    @property
    def cleanup_error(self):  # Expose sanitized exact-child cleanup failure evidence.
        # Read the cleanup outcome after its lock-protected attempt.
        with self._cleanup_lock:
            # Return only the exception type retained by cleanup.
            return self._cleanup_error

    # Acknowledge timeout after cleanup-driven failure reaches the synchronous runner.
    def acknowledge_timeout(self):
        # Release the watchdog's bounded grace wait before it sends a fallback interrupt.
        self._timeout_ack_event.set()

    # Write and immediately flush one structured event to the configured stream.
    def _emit(self, line):
        # Serialize writes so heartbeat and terminal result lines cannot interleave.
        with self._lock:
            # Append one newline to preserve incremental GitHub Actions rendering.
            self.stream.write(line + "\n")
            # Flush explicitly so output does not wait for process or buffer completion.
            self.stream.flush()

    # Format common elapsed and completion fields for every event kind.
    def _fields(self, now):
        # Calculate suite elapsed time from the reporter's monotonic start.
        elapsed = max(0, int(now - self._started_at))
        # Calculate current item or phase elapsed time from its latest start.
        current_elapsed = max(0, int(now - self._current_started_at))
        # Prefer the active item while retaining the current phase when no item is active.
        current = sanitize_label(self._current_item or self._phase)
        # Return stable key-value fields for CI readers and focused formatting tests.
        return f"phase={sanitize_label(self._phase)} current={current} elapsed={elapsed}s current_elapsed={current_elapsed}s completed={self._completed}/{self.total}"

    # Start reporting one suite and optionally launch its background watchdog.
    def start(self, phase, background=True):
        # Capture one monotonic instant for all initial timing fields.
        now = self.clock()
        # Initialize state before any watchdog can poll it.
        with self._lock:
            # Reject accidental reuse because counts and deadlines are suite-local.
            if self._started_at is not None:
                # Fail clearly instead of silently restarting a running reporter.
                raise RuntimeError("progress reporter already started")
            # Store the sanitized initial phase visible in startup heartbeats.
            self._phase = sanitize_label(phase)
            # Seed the suite deadline from the same monotonic instant.
            self._started_at = now
            # Seed heartbeat cadence from suite start.
            self._last_heartbeat_at = now
            # Treat the initial phase announcement as forward progress.
            self._last_progress_at = now
            # Track phase elapsed time before the first named item begins.
            self._current_started_at = now
        # Emit the flushed initial phase line before launching any background work.
        self._emit(f"[PHASE] START {self._fields(now)}")
        # Launch the daemon watchdog only for real suite execution.
        if background:
            # Create one named daemon thread that cannot keep a completed process alive.
            self._thread = threading.Thread(target=self._watch, name="test-progress-watchdog", daemon=True)
            # Start heartbeat, stall, and timeout observation.
            self._thread.start()

    # Transition between named suite phases with terminal and start lines.
    def set_phase(self, phase):
        # Capture one monotonic instant so adjacent phase events share exact counts.
        now = self.clock()
        # Emit a terminal result for the prior phase before replacing it.
        self._emit(f"[PHASE] COMPLETE {self._fields(now)}")
        # Update the new phase and reset no-progress timing.
        with self._lock:
            # Store the sanitized next phase for all later events.
            self._phase = sanitize_label(phase)
            # Clear any prior item because phases change only between named items.
            self._current_item = None
            # Measure phase elapsed time from this transition.
            self._current_started_at = now
            # Treat the phase transition as forward progress.
            self._last_progress_at = now
            # Allow a later stall warning if the new phase stops advancing.
            self._stall_warned = False
        # Emit the next flushed phase start line after updating shared state.
        self._emit(f"[PHASE] START {self._fields(now)}")

    # Announce one named browser test or long-suite scenario before it runs.
    def start_item(self, item):
        # Capture one monotonic instant for current-item timing.
        now = self.clock()
        # Update the active item before emitting its start line.
        with self._lock:
            # Reject overlapping synchronous items because completion counts would be ambiguous.
            if self._current_item is not None:
                # Surface a runner-instrumentation bug without changing test semantics.
                raise RuntimeError("progress item already active")
            # Store only the sanitized static test or scenario label.
            self._current_item = sanitize_label(item)
            # Measure this item's elapsed duration independently of suite elapsed time.
            self._current_started_at = now
            # Treat item start as forward progress for stall detection.
            self._last_progress_at = now
            # Permit one warning if this item later exceeds the stall threshold.
            self._stall_warned = False
        # Flush the named start event before the test body begins.
        self._emit(f"[PROGRESS] START {self._fields(now)}")

    # Announce a terminal result and advance the completed count for one named item.
    def finish_item(self, status):
        # Capture one monotonic instant for the terminal event.
        now = self.clock()
        # Normalize terminal status to a small fixed vocabulary.
        terminal = "PASS" if status == "PASS" else "FAIL"
        # Advance counts while retaining the item label for the emitted terminal line.
        with self._lock:
            # Reject a mismatched terminal event that has no active named item.
            if self._current_item is None:
                # Keep instrumentation errors explicit and local to the runner.
                raise RuntimeError("no progress item is active")
            # Count both pass and fail terminal items as completed executions.
            self._completed += 1
            # Treat the terminal result as forward progress.
            self._last_progress_at = now
            # Reset the warning gate after forward progress.
            self._stall_warned = False
        # Emit the terminal line while the completed item's label remains available.
        self._emit(f"[PROGRESS] {terminal} {self._fields(now)}")
        # Clear the active item only after its terminal line has been flushed.
        with self._lock:
            # Return heartbeat context to the current phase.
            self._current_item = None
            # Measure any following phase-only interval from this completion.
            self._current_started_at = now

    # Register one exact-child cleanup callback after its PID and port are known.
    def set_cleanup(self, callback):
        # Serialize callback replacement with any timeout cleanup attempt.
        with self._cleanup_lock:
            # Reject late registration after cleanup has already run.
            if self._cleanup_attempted:
                # Make a timeout/startup race visible to the caller.
                raise RuntimeError("cleanup already attempted")
            # Store the closure that stops only the tracked child and verifies its port.
            self._cleanup_callback = callback

    # Run tracked cleanup at most once and retain its evidence for the caller.
    def cleanup(self):
        # Serialize watchdog and normal-finally cleanup paths.
        with self._cleanup_lock:
            # Return the retained result when another path already attempted cleanup.
            if self._cleanup_attempted:
                # Preserve idempotency for timeout and finally races.
                return self._cleanup_result
            # Mark cleanup attempted before invoking caller code.
            self._cleanup_attempted = True
            # Skip safely when no tracked child was started.
            if self._cleanup_callback is None:
                # Return no evidence because there was no listener to close.
                return None
            # Convert callback failures into retained sanitized evidence.
            try:
                # Run the exact PID/port cleanup supplied by the suite.
                self._cleanup_result = self._cleanup_callback()
            # Handle cleanup failure without preventing timeout signaling.
            except Exception as exc:
                # Retain only the exception type to avoid leaking raw environment details.
                self._cleanup_error = type(exc).__name__
                # Emit one flushed fixed-format cleanup error.
                self._emit(f"::error::[CLEANUP] FAIL error={self._cleanup_error}")
            # Return exact sanitized cleanup evidence or None on failure.
            return self._cleanup_result

    # Evaluate heartbeat, stall, and timeout transitions at one instant.
    def poll(self, now=None):
        # Use the configured monotonic clock unless a focused test supplies an instant.
        instant = self.clock() if now is None else now
        # Compute transitions under the state lock before running external cleanup.
        with self._lock:
            # Ignore polls before start or after a timeout transition.
            if self._started_at is None or self._timed_out:
                # Report no transition to deterministic focused tests.
                return None
            # Determine whether the real suite deadline has expired.
            timeout_due = instant - self._started_at >= self.timeout_seconds
            # Mark timeout exactly once before releasing the state lock.
            if timeout_due:
                # Publish timeout state for the synchronous caller's exception handler.
                self._timed_out = True
            # Determine whether another periodic heartbeat is due.
            heartbeat_due = instant - self._last_heartbeat_at >= self.heartbeat_seconds
            # Determine whether forward progress has stalled beyond the warning threshold.
            stall_due = instant - self._last_progress_at >= self.stall_seconds and not self._stall_warned
            # Advance heartbeat cadence only when a line will be emitted.
            if heartbeat_due:
                # Anchor the next interval to this actual emitted heartbeat.
                self._last_heartbeat_at = instant
            # Gate stall warnings until the next phase or terminal test progress.
            if stall_due:
                # Avoid repeating the same non-failing warning every watchdog poll.
                self._stall_warned = True
        # Handle the real timeout before lower-severity progress events.
        if timeout_due:
            # Identify the last active phase or item and the exact completed count.
            self._emit(f"::error::[TIMEOUT] {self._fields(instant)} limit={int(self.timeout_seconds)}s")
            # Stop and verify only the tracked test child before interrupting the runner.
            self.cleanup()
            # Give cleanup-driven connection failure a bounded chance to reach runner handlers.
            acknowledged = self._timeout_ack_event.wait(self.interrupt_grace_seconds)
            # Interrupt only a main thread that did not begin normal timeout unwinding.
            if not acknowledged:
                # Raise a fallback main-thread interrupt so normal finally paths can execute.
                self.timeout_trigger()
            # Return the strongest transition for focused tests.
            return "timeout"
        # Emit a lightweight heartbeat at the configured interval.
        if heartbeat_due:
            # Flush elapsed, active context, and completed/total counts immediately.
            self._emit(f"[HEARTBEAT] {self._fields(instant)}")
        # Emit a clearly labeled warning without failing an alive but slow test.
        if stall_due:
            # Use GitHub's warning annotation syntax plus stable progress fields.
            self._emit(f"::warning::[STALL] no test-level progress; {self._fields(instant)} threshold={int(self.stall_seconds)}s")
        # Return the most important non-timeout transition for deterministic tests.
        return "stall" if stall_due else "heartbeat" if heartbeat_due else None

    # Poll until normal completion or timeout asks the watchdog to stop.
    def _watch(self):
        # Use a short bounded wait so stall and timeout deadlines remain prompt.
        while not self._stop_event.wait(min(1.0, self.heartbeat_seconds)):
            # Evaluate all due transitions at the current monotonic instant.
            if self.poll() == "timeout":
                # Stop the daemon after it has requested main-thread termination.
                return

    # Stop the watchdog and emit a terminal phase line for normal or failed completion.
    def close(self, status):
        # Ask the watchdog to stop without waiting for its next cadence interval.
        self._stop_event.set()
        # Join only a distinct live watchdog thread.
        if self._thread is not None and self._thread is not threading.current_thread():
            # Bound the join because this helper must never stall suite cleanup.
            self._thread.join(timeout=2)
        # Skip duplicate phase output when start never completed.
        if self._started_at is None:
            # Return without emitting invalid elapsed fields.
            return
        # Normalize final suite state to a fixed terminal vocabulary.
        terminal = "PASS" if status == "PASS" else "TIMEOUT" if self.timed_out else "FAIL"
        # Capture a final monotonic instant after cleanup and watchdog shutdown.
        now = self.clock()
        # Emit the terminal phase result with final completed/total counts.
        self._emit(f"[PHASE] {terminal} {self._fields(now)}")
