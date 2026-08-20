# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Regression tests for deterministic game-race process ownership. (TEST-161)"""

# Import the active interpreter for real child-process cleanup evidence.
import sys
# Import environment copying for disposable JSON control-root setup evidence.
import os
# Import disposable paths for readiness-marker isolation.
import tempfile
# Import the standard unit-test framework used by repository discovery.
import unittest
# Import portable path objects for worker rendezvous identities.
from pathlib import Path

# Import the shared process pool exercised by every fresh-process game race.
from tests.process_race import ProcessRacePool


# Prove bounded readiness diagnostics and cleanup across every exit path.
class ProcessRacePoolTests(unittest.TestCase):
    # Reap a blocked worker and close both capture pipes when an assertion aborts the body.
    def test_context_failure_reaps_worker_and_closes_pipes(self) -> None:
        # Retain the process outside the context for post-cleanup assertions.
        process = None
        # Model an assertion failure after a child has started but before release.
        with self.assertRaisesRegex(AssertionError, "fixture stopped"):
            # Own the worker through the same explicit context used by game races.
            with ProcessRacePool() as process_pool:
                # Launch one child that would otherwise outlive its failed test.
                process = process_pool.spawn(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    stdout=-1,
                    stderr=-1,
                    text=True,
                )
                # Abort before the normal communicate success path.
                raise AssertionError("fixture stopped")
        # Require the test-owned worker to be terminal after context cleanup.
        self.assertIsNotNone(process.returncode)
        # Require both captured descriptors to be closed deterministically.
        self.assertTrue(process.stdout.closed and process.stderr.closed)

    # Report every worker identity when a child exits before claiming readiness.
    def test_readiness_failure_reports_marker_and_return_code(self) -> None:
        # Own one missing marker in an isolated disposable directory.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve the marker the child deliberately never creates.
            marker = Path(temporary) / "missing-ready"
            # Launch one child that exits before the readiness claim.
            process = process_pool.spawn(
                [sys.executable, "-c", "raise SystemExit(7)"],
                stdout=-1,
                stderr=-1,
                text=True,
            )
            # Require bounded failure evidence to name both marker and child result.
            with self.assertRaisesRegex(
                AssertionError,
                r"ready=False returncode=7 marker=.*missing-ready",
            ):
                # Exercise the same readiness boundary as real game contenders.
                process_pool.wait_until_ready([(process, marker)], timeout=5)

    # Accept a marker published by a live child without consuming its output early.
    def test_readiness_success_preserves_normal_communication(self) -> None:
        # Own the marker and process inside one disposable fixture boundary.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Resolve the exact marker supplied to the child.
            marker = Path(temporary) / "ready"
            # Publish readiness and one normal stdout result from a fresh interpreter.
            process = process_pool.spawn(
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; import sys; "
                    "Path(sys.argv[1]).write_text('ready', encoding='utf-8'); print('PASS')",
                    str(marker),
                ],
                stdout=-1,
                stderr=-1,
                text=True,
            )
            # Wait through the shared bounded readiness seam.
            process_pool.wait_until_ready([(process, marker)], timeout=5)
            # Collect the unchanged worker result through the normal caller path.
            standard_output, standard_error = process.communicate(timeout=5)
            # Require exact successful output and no hidden diagnostic.
            self.assertEqual((process.returncode, standard_output.strip(), standard_error), (0, "PASS", ""))

    # Prepare one stable JSON control topology before contenders enter production locks.
    def test_json_workers_share_precreated_control_root(self) -> None:
        # Own both provider roots inside one disposable fixture boundary.
        with tempfile.TemporaryDirectory() as temporary, ProcessRacePool() as process_pool:
            # Copy the caller environment before selecting isolated JSON storage.
            environment = os.environ.copy()
            # Bind exact task-owned data, log, and provider identities.
            environment.update(
                {
                    "CASINO_STORAGE_PROVIDER": "json",
                    "CASINO_DATA_DIR": str(Path(temporary) / "data"),
                    "CASINO_LOG_DIR": str(Path(temporary) / "logs"),
                }
            )
            # Launch one harmless child through the production-shaped fixture setup.
            process = process_pool.spawn(
                [sys.executable, "-c", "print('PASS')"],
                env=environment,
                stdout=-1,
                stderr=-1,
                text=True,
            )
            # Collect the normal child result before inspecting fixture topology.
            standard_output, standard_error = process.communicate(timeout=5)
            # Require the child to retain its exact normal behavior.
            self.assertEqual((process.returncode, standard_output.strip(), standard_error), (0, "PASS", ""))
            # Resolve the private parent shared by every production JSON control root.
            control_parent = Path(environment["CASINO_LOG_DIR"]) / ".casino-json"
            # Require exactly one stable per-data-root directory before any race access.
            self.assertEqual(len(list(control_parent.iterdir())), 1)


# Run focused ownership evidence directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
