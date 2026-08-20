# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic child-process ownership for game race evidence. (TEST-161)"""

# Import subprocess primitives for exact interpreter workers and bounded shutdown.
import subprocess
# Import stable hashing for the production-shaped JSON control directory identity.
import hashlib
# Import canonical filesystem resolution for exact disposable provider roots.
import os
# Import monotonic time for readiness deadlines that ignore wall-clock changes.
import time
# Import path identities for worker-owned readiness markers.
from pathlib import Path
# Import traceback typing without changing runtime exception handling.
from types import TracebackType
# Import flexible argument typing for the standard Popen boundary.
from typing import Any


# Own every worker and pipe until one race fixture has completely unwound.
class ProcessRacePool:
    """Close and reap every registered child on success or failure."""

    # Start with no child resources owned by this fixture boundary.
    def __init__(self) -> None:
        # Retain processes in launch order for deterministic reverse cleanup.
        self._processes: list[subprocess.Popen[str]] = []
        # Retain initialized disposable JSON roots so each topology is prepared once.
        self._prepared_json_roots: set[tuple[str, str]] = set()

    # Enter the explicit fixture-owned process boundary.
    def __enter__(self) -> "ProcessRacePool":
        # Return this pool so callers can launch through the registered seam.
        return self

    # Reap workers before the surrounding disposable directory is removed.
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> bool:
        # Preserve the primary test failure while still closing every resource.
        self.close(suppress_errors=exception_type is not None)
        # Never suppress an exception raised by the test body.
        return False

    # Launch one worker and immediately bind its ownership to this pool.
    def spawn(self, *arguments: Any, **options: Any) -> subprocess.Popen[str]:
        # Read the exact child environment when this worker uses an isolated provider.
        environment = options.get("env")
        # Prepare stable JSON control parents before simultaneous first provider access.
        if isinstance(environment, dict) and environment.get("CASINO_STORAGE_PROVIDER") == "json":
            # Resolve the explicit disposable data and log identities.
            data_value = environment.get("CASINO_DATA_DIR")
            log_value = environment.get("CASINO_LOG_DIR")
            # Require both fixture-owned roots before preparing private control topology.
            if isinstance(data_value, str) and isinstance(log_value, str):
                # Canonicalize paths exactly as the production provider does.
                data_root = os.path.normcase(os.path.realpath(data_value))
                # Canonicalize the separately writable log root.
                log_root = os.path.normcase(os.path.realpath(log_value))
                # Bind one deduplication key to this exact disposable provider pair.
                root_key = (data_root, log_root)
                # Create topology only before the first contender for this root launches.
                if root_key not in self._prepared_json_roots:
                    # Derive the same private control-directory identity as production.
                    root_digest = hashlib.sha256(data_root.encode("utf-8")).hexdigest()[:16]
                    # Create the task-owned stable control parent before concurrent realpath checks.
                    (Path(log_root) / ".casino-json" / root_digest).mkdir(parents=True, exist_ok=True)
                    # Record exact preparation so later contenders perform no setup race.
                    self._prepared_json_roots.add(root_key)
        # Start through Python's standard shell-free process primitive.
        process = subprocess.Popen(*arguments, **options)
        # Register the child before returning control to assertion code.
        self._processes.append(process)
        # Return the normal Popen interface used by existing race assertions.
        return process

    # Wait for every worker readiness marker or raise one complete diagnostic.
    @staticmethod
    def wait_until_ready(
        process_paths: list[tuple[subprocess.Popen[str], Path]],
        *,
        timeout: float = 10.0,
    ) -> None:
        """Require every marker before the unchanged race release boundary."""

        # Compute one monotonic deadline shared by all contenders.
        deadline = time.monotonic() + timeout
        # Poll only until all markers exist, one child exits, or time expires.
        while not all(path.exists() for _process, path in process_paths):
            # Stop immediately when a worker cannot still claim readiness.
            if any(process.poll() is not None for process, _path in process_paths):
                # Leave polling for the complete fail-closed diagnostic below.
                break
            # Stop when the existing bounded readiness window expires.
            if time.monotonic() >= deadline:
                # Leave polling for the complete fail-closed diagnostic below.
                break
            # Yield briefly without changing contender order or extending the bound.
            time.sleep(0.01)
        # Return only after every exact marker has been published.
        if all(path.exists() for _process, path in process_paths):
            # Preserve the existing successful rendezvous semantics.
            return
        # Collect terminal output only from workers that already exited before readiness.
        terminal_output = {}
        # Drain already-terminal workers with a short bounded pipe-reader allowance.
        for process, _path in process_paths:
            # Leave live contenders untouched for pool-owned cleanup.
            if process.poll() is None:
                # Continue to the next diagnostic record.
                continue
            # Capture the exited worker's exact output when reader threads have converged.
            try:
                # Allow Windows pipe-reader threads to observe the already-terminal child.
                terminal_output[process.pid] = process.communicate(timeout=1)
            # Preserve readiness failure even if a terminal pipe reader is still settling.
            except subprocess.TimeoutExpired:
                # Record a stable diagnostic without extending the race rendezvous.
                terminal_output[process.pid] = ("<pipe-drain-pending>", "<pipe-drain-pending>")
        # Describe every worker without consuming output from a live contender.
        statuses = [
            (
                f"pid={process.pid} ready={path.exists()} "
                f"returncode={process.poll()} marker={path} "
                f"stdout={terminal_output.get(process.pid, ('', ''))[0]!r} "
                f"stderr={terminal_output.get(process.pid, ('', ''))[1]!r}"
            )
            for process, path in process_paths
        ]
        # Fail closed with enough evidence to identify exit, timeout, and marker ownership.
        raise AssertionError("fresh-process readiness failed: " + "; ".join(statuses))

    # Close every pipe and reap every process, including partial launch failures.
    def close(self, *, suppress_errors: bool = False) -> None:
        # Retain the first cleanup error while continuing through every worker.
        first_error: BaseException | None = None
        # Reap in reverse launch order so later contenders release first.
        for process in reversed(self._processes):
            # Finish this child independently so one failure cannot leak its siblings.
            try:
                # Request graceful termination only when the worker is still active.
                if process.poll() is None:
                    # Stop a blocked race worker before its disposable gates disappear.
                    process.terminate()
                # Drain captured output and wait through the bounded shutdown window.
                try:
                    # Close stdout and stderr through communicate's standard ownership path.
                    process.communicate(timeout=5)
                # Escalate only a child that ignored the bounded terminate request.
                except subprocess.TimeoutExpired:
                    # Force the task-owned worker to stop rather than surviving discovery.
                    process.kill()
                    # Reap the killed child and drain its remaining captured output.
                    process.communicate(timeout=5)
            # Preserve cleanup evidence while still closing every remaining child.
            except BaseException as error:
                # Retain only the first failure for deterministic reporting.
                if first_error is None:
                    # Bind the first cleanup failure after all resources are attempted.
                    first_error = error
            # Close any explicit stream that communicate did not already close.
            finally:
                # Inspect each possible pipe without assuming a particular Popen shape.
                for stream in (process.stdin, process.stdout, process.stderr):
                    # Close only a live caller-owned stream.
                    if stream is not None and not stream.closed:
                        # Release the operating-system descriptor deterministically.
                        stream.close()
        # Drop strong references so Windows process handles can close immediately.
        self._processes.clear()
        # Drop disposable topology identities after their children are terminal.
        self._prepared_json_roots.clear()
        # Surface cleanup failure only when it would not mask the primary test error.
        if first_error is not None and not suppress_errors:
            # Re-raise the original cleanup exception with its traceback intact.
            raise first_error
