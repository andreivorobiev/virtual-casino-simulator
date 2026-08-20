# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Opt-in Windows convergence proof for complete game discovery. (TEST-161)"""

# Import CSV parsing for stable tasklist process identifiers.
import csv
# Import garbage collection so completed Popen handles are released before measurement.
import gc
# Import environment and platform identity for the explicit Windows-only gate.
import os
# Import subprocess execution for isolated complete game-discovery runs.
import subprocess
# Import the current interpreter used by the governed repository suite.
import sys
# Import kernel-managed temporary files that avoid parent pipe-reader handles.
import tempfile
# Import the standard unit-test framework for skip and assertion semantics.
import unittest
# Import portable paths for the exact repository and discovery root.
from pathlib import Path


# Enable the expensive local stress proof only through its explicit owner signal.
_STRESS_ENABLED = os.environ.get("CASINO_WINDOWS_GAME_DISCOVERY_STRESS") == "1"


# Return process identifiers for one exact Windows image name.
def _process_ids(image_name: str) -> set[int]:
    # Ask Windows for CSV output so localized column headers are irrelevant.
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    # Retain only well-formed rows whose second field is a numeric PID.
    return {
        int(row[1])
        for row in csv.reader(result.stdout.splitlines())
        if len(row) >= 2 and row[1].isdigit()
    }


# Read this Python process's open Windows handle count without a third-party package.
def _current_handle_count() -> int:
    # Import ctypes only on the guarded Windows execution path.
    import ctypes
    # Import exact Windows scalar and handle types for 64-bit-safe calls.
    from ctypes import wintypes

    # Bind kernel32 once before declaring exact function signatures.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Declare the pointer-sized current-process handle result.
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    # Declare the exact handle and output-pointer parameter types.
    kernel32.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    # Declare the Win32 BOOL result used by the fail-closed check.
    kernel32.GetProcessHandleCount.restype = wintypes.BOOL
    # Read the current process pseudo-handle without 64-bit truncation.
    process_handle = kernel32.GetCurrentProcess()
    # Allocate the unsigned count populated by GetProcessHandleCount.
    handle_count = wintypes.DWORD()
    # Require the operating-system query to succeed before trusting the count.
    if not kernel32.GetProcessHandleCount(process_handle, ctypes.byref(handle_count)):
        # Fail closed when Windows cannot provide the convergence measurement.
        raise OSError(ctypes.get_last_error(), "GetProcessHandleCount failed")
    # Return the exact parent-process handle count.
    return int(handle_count.value)


# Repeat complete discovery and prove its process and descriptor counts converge.
@unittest.skipUnless(os.name == "nt" and _STRESS_ENABLED, "explicit Windows game-discovery stress only")
class WindowsGameDiscoveryResourceTests(unittest.TestCase):
    # Run the governed game directory three times without warnings or owned residue.
    def test_three_complete_discoveries_converge(self) -> None:
        # Resolve the repository that owns this exact checked regression.
        repository_root = Path(__file__).resolve().parents[1]
        # Warm the tasklist path before taking the authoritative process baseline.
        _process_ids("python.exe")
        # Capture every relevant interpreter and browser process before discovery.
        process_baseline = {
            image_name: _process_ids(image_name)
            for image_name in ("python.exe", "node.exe", "chrome.exe", "msedge.exe")
        }
        # Release any completed inventory subprocess objects before counting handles.
        gc.collect()
        # Capture the warmed parent-process handle baseline.
        handle_baseline = _current_handle_count()
        # Retain one exact test count to reject discovery drift between runs.
        discovered_count = None
        # Execute the acceptance sequence exactly three consecutive times.
        for run_number in range(1, 4):
            # Keep discovery output in files so the stress parent owns no reader threads.
            with tempfile.TemporaryFile() as standard_output_file, tempfile.TemporaryFile() as standard_error_file:
                # Run dependency-complete game discovery in a fresh interpreter.
                result = subprocess.run(
                    [
                        sys.executable,
                        "-W",
                        "default::ResourceWarning",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests/games",
                    ],
                    cwd=repository_root,
                    stdout=standard_output_file,
                    stderr=standard_error_file,
                    timeout=300,
                )
                # Rewind captured stdout only after the discovery process is reaped.
                standard_output_file.seek(0)
                # Decode exact stdout with replacement reserved for failure diagnostics.
                standard_output = standard_output_file.read().decode("utf-8", errors="replace")
                # Rewind captured stderr only after the discovery process is reaped.
                standard_error_file.seek(0)
                # Decode exact stderr with replacement reserved for failure diagnostics.
                standard_error = standard_error_file.read().decode("utf-8", errors="replace")
            # Preserve complete stdout and stderr only when one run fails.
            self.assertEqual(
                result.returncode,
                0,
                f"run={run_number} stdout={standard_output!r} stderr={standard_error!r}",
            )
            # Reject every descriptor warning even when Python reports it as unraisable.
            self.assertNotIn("ResourceWarning", standard_output + standard_error)
            # Parse unittest's stable terminal count from stderr.
            count_lines = [line for line in standard_error.splitlines() if line.startswith("Ran ")]
            # Require one exact discovery-count line from the standard runner.
            self.assertEqual(len(count_lines), 1, standard_error)
            # Extract the numeric count from ``Ran N tests`` without locale assumptions.
            current_count = int(count_lines[0].split()[1])
            # Bind the first run's complete discovery inventory.
            if discovered_count is None:
                # Retain the exact count for subsequent equality checks.
                discovered_count = current_count
            # Require every run to execute the identical complete case inventory.
            self.assertEqual(current_count, discovered_count)
            # Release completed subprocess internals before measuring current resources.
            gc.collect()
            # Require every tracked process image to return to its exact baseline set.
            for image_name, baseline_ids in process_baseline.items():
                # Compare stable process identities rather than aggregate counts alone.
                self.assertEqual(
                    _process_ids(image_name),
                    baseline_ids,
                    f"run={run_number} image={image_name}",
                )
            # Release inventory subprocess handles before reading the parent count.
            gc.collect()
            # Allow no accumulating parent handles across the complete discovery run.
            self.assertLessEqual(_current_handle_count(), handle_baseline + 2)


# Run the explicit Windows stress proof directly for local acceptance.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
