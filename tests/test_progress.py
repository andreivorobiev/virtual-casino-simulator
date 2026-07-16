"""Focused deterministic tests for issue #207 progress reporting under TEST-010/TEST-042."""

# Import an in-memory text stream for exact formatting assertions.
import io
# Import the dependency-free unit-test framework used by focused repository checks.
import unittest

# Import the reusable CI progress reporter and its label sanitizer.
from tests.progress import ProgressReporter, sanitize_label


# Record every explicit flush so incremental-output behavior is directly testable.
class FlushTrackingStream(io.StringIO):
    # Initialize text storage and a flush counter.
    def __init__(self):
        # Initialize the normal in-memory stream behavior.
        super().__init__()
        # Count each explicit flush performed by the reporter.
        self.flush_count = 0

    # Record one flush while preserving the base stream contract.
    def flush(self):
        # Increment the observable flush count before delegating.
        self.flush_count += 1
        # Preserve standard StringIO flush behavior.
        return super().flush()


# Supply a deterministic monotonic clock without sleeping.
class FakeClock:
    # Start the fake clock at a caller-selected instant.
    def __init__(self, initial=0.0):
        # Store the current floating-point monotonic time.
        self.now = float(initial)

    # Return the current deterministic instant.
    def __call__(self):
        # Match the callable clock interface expected by ProgressReporter.
        return self.now


# Verify formatting, cadence, stall, timeout, and cleanup behavior without real listeners.
class ProgressReporterTests(unittest.TestCase):
    # Build one manual-poll reporter and its observable dependencies.
    def make_reporter(self, heartbeat=45, stall=90, timeout=300):
        # Create a deterministic clock at suite time zero.
        clock = FakeClock()
        # Create a stream that records every immediate flush.
        stream = FlushTrackingStream()
        # Record timeout-trigger calls without interrupting this test process.
        triggers = []
        # Construct the reporter with deterministic clock and timeout seams.
        reporter = ProgressReporter(total=2, heartbeat_seconds=heartbeat, stall_seconds=stall, timeout_seconds=timeout, stream=stream, clock=clock, timeout_trigger=lambda: triggers.append("timeout"), interrupt_grace_seconds=0)
        # Start reporting without a background thread so tests control every poll.
        reporter.start("browser suite", background=False)
        # Return all observable test seams.
        return reporter, clock, stream, triggers

    # Ensure static labels cannot inject multiline or shell-like log content.
    def test_progress_formatting_is_sanitized_and_counted(self):
        # Build one reporter with a two-item completion denominator.
        reporter, clock, stream, _triggers = self.make_reporter()
        # Start one deliberately malformed label to exercise sanitization.
        reporter.start_item("BR-ONE\nsecret=$(value)")
        # Advance time before completing the item.
        clock.now = 7
        # Complete the named test successfully.
        reporter.finish_item("PASS")
        # Read all structured output for exact field checks.
        output = stream.getvalue()
        # Verify newlines and shell metacharacters were normalized out of the label.
        self.assertEqual("BR-ONE secret?value?", sanitize_label("BR-ONE\nsecret=$(value)"))
        # Verify start and terminal events include stable completion counts and elapsed time.
        self.assertIn("[PROGRESS] START", output)
        self.assertIn("[PROGRESS] PASS", output)  # Require a named terminal result.
        self.assertIn("elapsed=7s", output)  # Require sanitized elapsed time.
        self.assertIn("completed=1/2", output)  # Require completed/total counts.

    # Ensure every emitted event explicitly flushes for incremental GitHub Actions logs.
    def test_each_progress_event_flushes_immediately(self):
        # Build one reporter and capture the flush count after its phase start.
        reporter, _clock, stream, _triggers = self.make_reporter()
        # Record the phase-start flush as the baseline.
        initial_flushes = stream.flush_count
        # Emit one named start and terminal result.
        reporter.start_item("BR-FLUSH-001")
        # Complete the item so a second progress event is written.
        reporter.finish_item("PASS")
        # Require one explicit flush for each newly emitted progress line.
        self.assertEqual(initial_flushes + 2, stream.flush_count)

    # Verify heartbeats never appear early and do appear at the configured cadence.
    def test_heartbeat_cadence_reports_elapsed_and_counts(self):
        # Build a reporter with a forty-five-second heartbeat.
        reporter, clock, stream, _triggers = self.make_reporter(heartbeat=45, stall=90)
        # Start one long-running named browser test.
        reporter.start_item("BR-SLOW-001")
        # Poll immediately before the configured heartbeat boundary.
        clock.now = 44
        # Verify no progress event is due one second early.
        self.assertIsNone(reporter.poll())
        # Poll exactly at the accepted heartbeat boundary.
        clock.now = 45
        # Verify the reporter identifies a heartbeat transition.
        self.assertEqual("heartbeat", reporter.poll())
        # Read the incrementally written heartbeat line.
        output = stream.getvalue()
        # Require active context, elapsed time, and completed/total counts.
        self.assertIn("[HEARTBEAT]", output)
        self.assertIn("current=BR-SLOW-001", output)  # Require active test context.
        self.assertIn("elapsed=45s", output)  # Require heartbeat elapsed time.
        self.assertIn("completed=0/2", output)  # Require heartbeat completion counts.

    # Verify a slow but alive test receives one warning without being failed.
    def test_stall_warning_is_non_terminal_and_resets_after_progress(self):
        # Build a reporter whose stall threshold is two heartbeat intervals.
        reporter, clock, stream, _triggers = self.make_reporter(heartbeat=45, stall=90)
        # Start one item and advance to the stall threshold.
        reporter.start_item("BR-STALL-001")
        # Move the deterministic clock to ninety seconds.
        clock.now = 90
        # Verify the strongest due transition is the stall warning.
        self.assertEqual("stall", reporter.poll())
        # Poll again without progress to prove the warning is not duplicated.
        clock.now = 135
        # Verify only the normal heartbeat remains due.
        self.assertEqual("heartbeat", reporter.poll())
        # Complete the slow test successfully to prove the warning was non-terminal.
        reporter.finish_item("PASS")
        # Count exactly one warning and one successful terminal result.
        output = stream.getvalue()
        # Require one clearly labeled GitHub warning annotation.
        self.assertEqual(1, output.count("::warning::[STALL]"))
        # Require the slow test to retain its normal passing semantics.
        self.assertIn("[PROGRESS] PASS", output)

    # Verify a real timeout invokes cleanup once and requests a non-zero exit.
    def test_timeout_reports_last_item_and_runs_idempotent_cleanup(self):
        # Build a reporter with a short deterministic suite timeout.
        reporter, clock, stream, triggers = self.make_reporter(heartbeat=30, stall=60, timeout=120)
        # Record exact cleanup calls and return sanitized listener evidence.
        cleanup_calls = []
        # Register the fake exact-child cleanup callback.
        reporter.set_cleanup(lambda: cleanup_calls.append("cleanup") or {"pid": 42, "port": 54321, "closed": True})
        # Start the last active named test before timeout.
        reporter.start_item("BR-TIMEOUT-001")
        # Advance exactly to the hard suite deadline.
        clock.now = 120
        # Verify the reporter takes the timeout transition.
        self.assertEqual("timeout", reporter.poll())
        # Call cleanup again to prove the normal finally path is idempotent.
        evidence = reporter.cleanup()
        # Require one cleanup attempt and one timeout trigger.
        self.assertEqual(["cleanup"], cleanup_calls)
        # Require the injected main-thread termination request.
        self.assertEqual(["timeout"], triggers)
        # Require retained exact listener-closure evidence.
        self.assertEqual({"pid": 42, "port": 54321, "closed": True}, evidence)
        # Require timeout output to identify the last active item and exact counts.
        output = stream.getvalue()
        # Check the error annotation and the conventional non-zero timeout status.
        self.assertIn("::error::[TIMEOUT]", output)
        # Check the last active browser test is named in the timeout line.
        self.assertIn("current=BR-TIMEOUT-001", output)
        # Check no terminal items were falsely counted as completed.
        self.assertIn("completed=0/2", output)
        # Check callers can return a stable non-zero timeout exit code.
        self.assertEqual(124, reporter.timeout_exit_code)

    # Verify constructor validation enforces the public sixty-second heartbeat maximum.
    def test_heartbeat_interval_cannot_exceed_sixty_seconds(self):
        # Require an invalid cadence to fail before any watchdog thread starts.
        with self.assertRaises(ValueError):
            # Attempt to create a reporter outside the accepted issue #207 bound.
            ProgressReporter(total=1, heartbeat_seconds=61, stall_seconds=90, timeout_seconds=120)


# Run the focused tests when this file is invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal dependency-free command-line runner.
    unittest.main()
