# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Govern disposable relational registration without opening a listener. (TEST-257)"""

from __future__ import annotations

# Import environment access for restoring reachability and secret-isolation proofs.
import os
# Import portable paths for task-owned partial-cluster cleanup fixtures.
from pathlib import Path
# Import completed-process values for modeled pg_ctl stop/status results.
import subprocess
# Import isolated temporary roots without starting a database process.
import tempfile
# Import unit-test assertions for the listener-free harness gate.
import unittest
# Import restoring patches for optional imports, provider construction, and environment state.
from unittest import mock

# Import fixed harness authorization names and constructors without optional database drivers.
from tests.storage_conformance import database_harnesses


# Carry exact injected policy-failure identity through multi-stage cleanup.
class _HarnessFailure(AssertionError):
    """Represent one source-owned failure with no native target detail."""


# Model one relational provider whose pool close can fail observably.
class _ClosingProvider:
    """Expose only the optional pool lifecycle used by the harness."""

    # Store one optional close failure and invocation count.
    def __init__(self, failure: BaseException | None = None) -> None:
        # Retain the exact injected failure object.
        self.failure = failure
        # Count every close attempt for continuation evidence.
        self.calls = 0

    # Close once or raise the exact injected failure.
    def close_pool(self) -> None:
        """Record one close attempt before its optional failure."""

        # Count the independent provider-cleanup stage.
        self.calls += 1
        # Raise only the caller-owned failure when configured.
        if self.failure is not None:
            # Preserve its exact identity for the harness cleanup owner.
            raise self.failure


class DatabaseHarnessGovernanceTests(unittest.TestCase):
    """Keep absent services inert and reject incomplete live authorization."""

    def test_absent_markers_skip_without_optional_import(self) -> None:
        """Require both database harnesses to stay listener- and driver-free by default."""

        # Remove every ambient variable so absence semantics are deterministic.
        with mock.patch.dict(os.environ, {}, clear=True):
            # Fail if reachability inspection attempts any optional module import.
            with mock.patch.object(database_harnesses.importlib, "import_module", side_effect=AssertionError("optional import attempted")) as loader:
                # Construct both harnesses without allocating a root, process, or connection.
                mysql_harness = database_harnesses.MySQLHarness()
                # Construct PostgreSQL independently so no shared state can imply reachability.
                postgres_harness = database_harnesses.PostgresHarness()
                # Require one fixed value-free absence reason for both registrations.
                self.assertEqual(database_harnesses.ABSENT_REASON, mysql_harness.unavailable_reason())
                # Require PostgreSQL to report the exact same provider-neutral category.
                self.assertEqual(database_harnesses.ABSENT_REASON, postgres_harness.unavailable_reason())
                # Prove marker inspection did not import a connector, migration runner, or provider.
                loader.assert_not_called()
                # Prove PostgreSQL did not allocate any filesystem root before authorization.
                self.assertIsNone(postgres_harness.root)

    def test_present_invalid_markers_fail_before_optional_import(self) -> None:
        """Reject malformed opt-ins instead of converting them into absence skips."""

        # Supply only invalid marker values and no credentials or binary path.
        environment = {
            database_harnesses.MYSQL_MARKER_NAME: "invalid",
            database_harnesses.POSTGRES_MARKER_NAME: "invalid",
        }
        # Isolate the malformed authorization from the developer environment.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Prove invalid authorization never reaches an optional module loader.
            with mock.patch.object(database_harnesses.importlib, "import_module", side_effect=AssertionError("optional import attempted")) as loader:
                # Require one fixed MySQL authorization category.
                with self.assertRaisesRegex(AssertionError, "Disposable MySQL conformance authorization is invalid"):
                    # Inspect the marker without creating any resource.
                    database_harnesses.MySQLHarness().unavailable_reason()
                # Require one fixed PostgreSQL authorization category.
                with self.assertRaisesRegex(AssertionError, "Disposable PostgreSQL conformance authorization is invalid"):
                    # Inspect the independent marker without creating any resource.
                    database_harnesses.PostgresHarness().unavailable_reason()
                # Prove neither failure path imported a driver or migration helper.
                loader.assert_not_called()

    def test_present_mysql_marker_requires_complete_loopback_reachability(self) -> None:
        """Fail closed on partial MySQL configuration without reading a secret value."""

        # Authorize the lane but omit every reviewed administrator field.
        environment = {database_harnesses.MYSQL_MARKER_NAME: database_harnesses.MYSQL_MARKER_VALUE}
        # Remove unrelated variables so no ambient endpoint can satisfy the gate.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Construct without importing mysql.connector.
            harness = database_harnesses.MySQLHarness()
            # Require the exact marker to select execution rather than a skip.
            self.assertIsNone(harness.unavailable_reason())
            # Require incomplete reachability to fail before connection setup.
            with self.assertRaisesRegex(AssertionError, "Disposable MySQL conformance reachability is incomplete"):
                # Validate only the bounded endpoint contract.
                harness._admin_kwargs()

    def test_present_postgres_marker_requires_reviewed_binaries(self) -> None:
        """Fail closed on missing PostgreSQL binaries before importing psycopg."""

        # Authorize the lane but omit the explicit binary root.
        environment = {database_harnesses.POSTGRES_MARKER_NAME: database_harnesses.POSTGRES_MARKER_VALUE}
        # Remove ambient PATH-like configuration from the proof.
        with mock.patch.dict(os.environ, environment, clear=True):
            # Construct without allocating a cluster root.
            harness = database_harnesses.PostgresHarness()
            # Require the exact marker to select execution rather than a skip.
            self.assertIsNone(harness.unavailable_reason())
            # Require an explicit reviewed binary root with no PATH fallback.
            with self.assertRaisesRegex(AssertionError, "Disposable PostgreSQL conformance reachability is incomplete"):
                # Validate only the bounded binary contract.
                harness._validated_bin()
            # Prove validation failure allocated no private filesystem root.
            self.assertIsNone(harness.root)

    def test_provider_factory_environment_is_restored(self) -> None:
        """Keep generated target and credential values out of the ambient process."""

        # Build one sentinel provider without importing any concrete implementation.
        provider = object()
        # Use a dedicated secret-like name and value for restoration evidence.
        environment = {"CASINO_STORAGE_PROVIDER": "postgres", "CASINO_POSTGRES_PASSWORD": "generated-secret"}
        # Start from a deterministic environment with neither value present.
        with mock.patch.dict(os.environ, {}, clear=True):
            # Replace only the public facade's uncached selector factory.
            with mock.patch.object(database_harnesses.storage_facade, "_build_provider", return_value=provider) as factory:
                # Construct through the same bounded helper used by both relational harnesses.
                selected = database_harnesses._provider_from_environment(environment)
            # Require exact provider identity from the selector facade.
            self.assertIs(provider, selected)
            # Require one and only one synchronous selector invocation.
            factory.assert_called_once_with()
            # Prove provider selection did not retain the selected backend name.
            self.assertNotIn("CASINO_STORAGE_PROVIDER", os.environ)
            # Prove provider construction did not retain the generated secret.
            self.assertNotIn("CASINO_POSTGRES_PASSWORD", os.environ)

    # Prove native setup detail is fixed while explicit policy identity is preserved.
    def test_setup_error_translation_is_fixed_and_selective(self) -> None:
        """Sanitize only native infrastructure failures at create boundaries."""

        # Build one fixed wrapper without invoking any database harness.
        @database_harnesses._fixed_setup_errors(database_harnesses.POSTGRES_SETUP_FAILURE)
        def fail_native():
            # Simulate a connector exception containing forbidden values.
            raise RuntimeError("secret target path")
        # Require one fixed value-free setup category.
        with self.assertRaisesRegex(AssertionError, f"^{database_harnesses.POSTGRES_SETUP_FAILURE}$") as observed:
            # Cross the exact decorated create boundary.
            fail_native()
        # Prove no native message is reflected to the caller.
        self.assertNotIn("secret", str(observed.exception))
        # Freeze a distinct source-owned policy failure object.
        policy_failure = _HarnessFailure("policy failure")
        # Build another wrapper around exact policy failure.
        @database_harnesses._fixed_setup_errors(database_harnesses.POSTGRES_SETUP_FAILURE)
        def fail_policy():
            # Raise the source-owned assertion unchanged.
            raise policy_failure
        # Capture object identity rather than matching only text.
        try:
            # Invoke the exact policy path.
            fail_policy()
        except _HarnessFailure as error:
            # Preserve the original policy failure object.
            self.assertIs(policy_failure, error)
        else:
            # Fail if the wrapper suppressed the policy boundary.
            self.fail("policy failure was not raised")

    # Prove MySQL close/drop failures do not skip later identity cleanup.
    def test_mysql_cleanup_continues_and_preserves_first_failure(self) -> None:
        """Run all generated-identity stages after an exact pool-close failure."""

        # Create one listener-free harness and mark partial identity ownership.
        harness = database_harnesses.MySQLHarness()
        # Freeze the first source-owned cleanup failure.
        first_failure = _HarnessFailure("pool close failure")
        # Install a provider that fails before target cleanup.
        provider = _ClosingProvider(first_failure)
        # Retain the provider on the harness exactly as partial create would.
        harness._provider = provider
        # Build one administrator mock with deterministic zero-residue reads.
        admin = mock.Mock()
        # Return one reusable cursor for all cleanup DDL and verification.
        cursor = admin.cursor.return_value
        # Freeze a later target-drop failure that must not stop account cleanup.
        drop_failure = _HarnessFailure("database drop failure")
        # Track one injected failure without affecting later verification statements.
        drop_failed = False
        # Fail only the first generated database drop.
        def execute(statement, _params=None):
            # Mutate only this test-owned closure marker.
            nonlocal drop_failed
            # Raise once at the first generated database cleanup boundary.
            if str(statement).startswith("DROP DATABASE") and not drop_failed:
                # Prevent repeated injection during later calls.
                drop_failed = True
                # Surface the later exact drop failure.
                raise drop_failure
        # Route every cursor statement through the bounded failure injector.
        cursor.execute.side_effect = execute
        # Return exact absent database and account counts.
        cursor.fetchone.side_effect = [(0,), (0,)]
        # Attach the partial-create administrator and ownership marker.
        harness._admin = admin
        # Authorize removal of only the generated identities.
        harness._identities_owned = True
        # Require the first error after every later stage runs.
        try:
            # Execute complete cleanup without any connector import.
            harness.destroy()
        except _HarnessFailure as error:
            # Preserve exact first-error identity.
            self.assertIs(first_failure, error)
        else:
            # Fail if cleanup hid the first source-owned failure.
            self.fail("first cleanup failure was not raised")
        # Require provider close, all three drops, both verifications, and admin close.
        self.assertEqual((1, 5, 1), (provider.calls, cursor.execute.call_count, admin.close.call_count))
        # Prove the later drop boundary was reached despite pool-close failure.
        self.assertTrue(drop_failed)
        # Release deletion ownership only after the zero-residue reads.
        self.assertFalse(harness._identities_owned)
        # Prove terminal cleanup is idempotent.
        harness.destroy()

    # Prove a root-only partial PostgreSQL create remains removable and idempotent.
    def test_postgres_root_only_partial_create_is_removed(self) -> None:
        """Delete a verified private root without process or driver access."""

        # Allocate one correctly prefixed direct-child root.
        root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Construct a listener-free harness around only that partial resource.
        harness = database_harnesses.PostgresHarness()
        # Retain the root exactly as create does before initdb.
        harness._root = root
        # Retain the contained data path for lifecycle parity.
        harness._data_root = root / "data"
        # Destroy without attempting a process stop.
        harness.destroy()
        # Require exact filesystem removal and released handles.
        self.assertFalse(root.exists())
        # Require a second destroy to remain non-destructive.
        harness.destroy()

    # Prove start-then-raise ownership uses fallback and exact shutdown verification.
    def test_postgres_start_attempt_is_cleanup_owned(self) -> None:
        """Clean a possible listener even when pg_ctl start never returned success."""

        # Allocate one verified partial cluster root without launching PostgreSQL.
        root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Construct and populate only cleanup-owned lifecycle fields.
        harness = database_harnesses.PostgresHarness()
        # Retain the exact private root and data directory.
        harness._root, harness._data_root = root, root / "data"
        # Supply a fake binary root and private port for command construction.
        harness._bin, harness._port = root / "bin", 49123
        # Mark an ambiguous start attempt without claiming confirmed startup.
        harness._start_attempted, harness._started = True, False
        # Make graceful stop fail so the reviewed immediate fallback is required.
        live = mock.Mock()
        # Inject one native graceful-stop failure with forbidden detail.
        live._postgres_command.side_effect = RuntimeError("secret start detail")
        # Retain the fake live helper only for cleanup command capture.
        harness._live = live
        # Return fallback success followed by exact data-directory stopped status.
        process_results = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 3)]
        # Keep process and listener probes entirely in memory.
        with mock.patch.object(database_harnesses.subprocess, "run", side_effect=process_results) as runner, mock.patch.object(database_harnesses, "_loopback_listener_closed", return_value=True) as listener:
            # Complete fallback, verification, and root deletion.
            harness.destroy()
        # Require immediate stop plus status and exact listener probe.
        self.assertEqual((2, 1), (runner.call_count, listener.call_count))
        # Require full ownership release only after both proofs.
        self.assertFalse(root.exists())
        # Prove repeated cleanup performs no additional stop or delete.
        harness.destroy()

    # Prove direct launch retains its process handle across readiness failure.
    def test_postgres_partial_direct_launch_is_cleanup_owned(self) -> None:
        """Sanitize readiness failure while retaining exact process/root ownership."""

        # Construct the authorized harness without opening a real listener.
        harness = database_harnesses.PostgresHarness()
        # Build one fake driver that never reaches administrator readiness.
        driver = mock.Mock()
        # Inject native connector detail that must not escape create.
        driver.connect.side_effect = RuntimeError("secret readiness target")
        # Build inert SQL and live-helper modules for the pre-target path.
        sql_owner, live = mock.Mock(), mock.Mock()
        # Reserve one deterministic private port without binding it.
        live._loopback_port.return_value = 49125
        # Model successful initdb before direct process launch.
        live._postgres_command.return_value = None
        # Retain one still-running tracked process object.
        process = mock.Mock()
        # Report the process alive throughout the bounded readiness loop.
        process.poll.return_value = None
        # Return optional modules in the exact create import order.
        modules = {"psycopg": driver, "psycopg.sql": sql_owner, "tests.postgres_migration_live": live}
        # Authorize create and replace every external process/module boundary.
        environment = {database_harnesses.POSTGRES_MARKER_NAME: database_harnesses.POSTGRES_MARKER_VALUE}
        # Keep the reviewed binary path inert because Popen is fully mocked.
        fake_bin = Path(tempfile.gettempdir()) / "postgres-bin-model"
        # Bound readiness immediately after the first failed connector attempt.
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(harness, "_validated_bin", return_value=fake_bin), mock.patch.object(database_harnesses.importlib, "import_module", side_effect=lambda name: modules[name]), mock.patch.object(database_harnesses.subprocess, "Popen", return_value=process) as launcher, mock.patch.object(database_harnesses.time, "monotonic", side_effect=[0.0, 11.0]):
            # Require only the fixed setup category from native readiness failure.
            with self.assertRaisesRegex(AssertionError, f"^{database_harnesses.POSTGRES_SETUP_FAILURE}$") as observed:
                # Execute initdb, direct launch, and bounded readiness.
                harness.create()
        # Reject reflected connector detail.
        self.assertNotIn("secret", str(observed.exception))
        # Require one exact argv-list direct launch with no shell.
        self.assertEqual(1, launcher.call_count)
        # Require the launched handle and start ownership to survive failure.
        self.assertIs(process, harness._process)
        # Model confirmed later process shutdown while preserving real root deletion.
        def stop_partial_launch():
            # Close the private file handle before root removal.
            harness._log_handle.close()
            # Release exact process and log ownership after modeled death.
            harness._process, harness._log_handle = None, None
            # Release both active and attempted start markers.
            harness._started, harness._start_attempted = False, False
        # Replace only process shutdown, never filesystem containment.
        with mock.patch.object(harness, "_stop_cluster", side_effect=stop_partial_launch):
            # Remove the exact task-owned partial root.
            harness.destroy()
        # Require zero partial-launch filesystem residue.
        self.assertIsNone(harness.root)

    # Prove dual stop failure retains ownership and a later destroy can finish safely.
    def test_postgres_dual_stop_failure_retains_retry_ownership(self) -> None:
        """Keep process/root handles until a later verified shutdown succeeds."""

        # Allocate one verified private root without starting a real listener.
        root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Construct a partial harness that may own an active process.
        harness = database_harnesses.PostgresHarness()
        # Populate exact cleanup-owned root, data, binary, and port fields.
        harness._root, harness._data_root, harness._bin, harness._port = root, root / "data", root / "bin", 49124
        # Mark both start attempt and active-process ownership.
        harness._start_attempted, harness._started = True, True
        # Fail every graceful stop attempt without sensitive output.
        live = mock.Mock()
        # Inject the source-owned graceful failure.
        live._postgres_command.side_effect = RuntimeError("native stop detail")
        # Retain the fake command owner.
        harness._live = live
        # Report immediate-stop failure and still-running status.
        failed_results = [subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]
        # Require fixed cleanup failure while ownership and root remain intact.
        with mock.patch.object(database_harnesses.subprocess, "run", side_effect=failed_results), mock.patch.object(database_harnesses, "_loopback_listener_closed", return_value=False):
            # Capture the exact fixed policy boundary.
            with self.assertRaisesRegex(AssertionError, "Disposable PostgreSQL conformance cleanup was incomplete"):
                # Attempt complete cleanup without deleting a possibly active data root.
                harness.destroy()
        # Retain all resources needed for a safe later cleanup attempt.
        self.assertTrue(root.exists())
        # Replace graceful stop with success for the retry.
        live._postgres_command.side_effect = None
        # Return exact stopped status after graceful completion.
        with mock.patch.object(database_harnesses.subprocess, "run", return_value=subprocess.CompletedProcess([], 3)), mock.patch.object(database_harnesses, "_loopback_listener_closed", return_value=True):
            # Retry the idempotent cleanup using retained ownership.
            harness.destroy()
        # Require zero root residue and released start ownership.
        self.assertFalse(root.exists())

    # Prove tracked termination escalates to kill and still requires all shutdown proofs.
    def test_postgres_tracked_process_kill_fallback_is_bounded(self) -> None:
        """Kill only the retained process after a bounded terminate wait."""

        # Allocate one verified partial root without launching PostgreSQL.
        root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Construct exact process-cleanup ownership fields.
        harness = database_harnesses.PostgresHarness()
        # Retain root, data, binary, port, and start ownership.
        harness._root, harness._data_root, harness._bin, harness._port = root, root / "data", root / "bin", 49126
        # Mark a directly launched active process.
        harness._started, harness._start_attempted = True, True
        # Build a live helper whose graceful pg_ctl stop fails.
        live = mock.Mock()
        # Force the immediate pg_ctl fallback before tracked termination.
        live._postgres_command.side_effect = RuntimeError("native graceful stop")
        # Retain the fake live command owner.
        harness._live = live
        # Model one tracked process alive before termination and dead after kill.
        process = mock.Mock()
        # Return alive at fallback selection and dead at final proof.
        process.poll.side_effect = [None, 0]
        # Time out the terminate wait, then complete after kill.
        process.wait.side_effect = [subprocess.TimeoutExpired("postgres", 5), 0]
        # Retain the exact process handle.
        harness._process = process
        # Open one private log handle that terminal cleanup must close.
        harness._log_handle = (root / "postgres.log").open("ab")
        # Return immediate-stop completion followed by nonrunning pg_ctl status.
        process_results = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 3)]
        # Keep every command and listener proof in memory.
        with mock.patch.object(database_harnesses.subprocess, "run", side_effect=process_results), mock.patch.object(database_harnesses, "_loopback_listener_closed", return_value=True):
            # Complete tracked terminate/kill and root cleanup.
            harness.destroy()
        # Require exact terminate, bounded double wait, and kill fallback.
        self.assertEqual((1, 2, 1), (process.terminate.call_count, process.wait.call_count, process.kill.call_count))
        # Require zero filesystem and process-handle residue.
        self.assertFalse(root.exists())
        # Prove terminal cleanup remains idempotent.
        harness.destroy()

    # Prove PostgreSQL close/drop failures never skip stop and root cleanup.
    def test_postgres_cleanup_continues_after_close_and_drop_failure(self) -> None:
        """Preserve first identity while completing independent terminal stages."""

        # Allocate a verified root that final cleanup may safely remove.
        root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Construct a cleanup-only partial harness.
        harness = database_harnesses.PostgresHarness()
        # Freeze the first exact provider-close failure.
        first_failure = _HarnessFailure("provider close failure")
        # Attach the failing provider and verified root.
        provider = _ClosingProvider(first_failure)
        # Retain both owned resources for the cleanup path.
        harness._provider, harness._root, harness._data_root = provider, root, root / "data"
        # Mark active/start ownership so the stop stage must run.
        harness._started, harness._start_attempted = True, True
        # Freeze a later drop failure that must not replace the first.
        later_failure = _HarnessFailure("drop failure")
        # Replace target and process stages with deterministic listener-free owners.
        with mock.patch.object(harness, "_drop_identities", side_effect=later_failure) as dropper, mock.patch.object(harness, "_stop_cluster") as stopper:
            # Make the successful stop mock release exact process ownership.
            stopper.side_effect = lambda: (setattr(harness, "_started", False), setattr(harness, "_start_attempted", False))
            # Require first-failure identity after stop and root removal.
            try:
                # Run every independent cleanup stage.
                harness.destroy()
            except _HarnessFailure as error:
                # Preserve the first provider-close object.
                self.assertIs(first_failure, error)
            else:
                # Fail if cleanup hid the original failure.
                self.fail("first PostgreSQL cleanup failure was not raised")
        # Require close, drop, and stop all to run exactly once.
        self.assertEqual((1, 1, 1), (provider.calls, dropper.call_count, stopper.call_count))
        # Require zero filesystem residue despite both earlier failures.
        self.assertFalse(root.exists())
        # Prove native cleanup detail maps to a fixed category independently.
        native_harness = database_harnesses.PostgresHarness()
        # Install only a provider whose close emits sensitive native text.
        native_harness._provider = _ClosingProvider(RuntimeError("password target path"))
        # Require the fixed value-free cleanup category.
        with self.assertRaisesRegex(AssertionError, f"^{database_harnesses.POSTGRES_CLEANUP_FAILURE}$") as observed:
            # Run the provider-only partial cleanup.
            native_harness.destroy()
        # Reject reflected native details.
        self.assertNotIn("password", str(observed.exception))

    # Prove PostgreSQL database-drop failure cannot skip role drop or verification.
    def test_postgres_identity_cleanup_continues_after_one_drop_failure(self) -> None:
        """Attempt every generated identity operation and preserve the first failure."""

        # Construct a listener-free harness with exact target ownership flags.
        harness = database_harnesses.PostgresHarness()
        # Authorize only cleanup against a modeled active private cluster.
        harness._started, harness._identities_owned = True, True
        # Build a minimal driver-safe SQL composer without importing psycopg.
        sql_owner = mock.Mock()
        # Return distinct inert statements for database and role drops.
        sql_owner.SQL.return_value.format.side_effect = ["DROP DATABASE", "DROP ROLE"]
        # Return identity values consumed only by the mocked formatter.
        sql_owner.Identifier.side_effect = lambda value: value
        # Retain the fake composition owner on the harness.
        harness._sql = sql_owner
        # Build one private administrator and cursor model.
        admin = mock.Mock()
        # Reuse one cursor for termination, drops, and verification.
        cursor = admin.cursor.return_value
        # Freeze an exact database-drop failure.
        drop_failure = _HarnessFailure("database drop failure")
        # Count statements so only the second operation fails.
        statement_index = 0
        # Inject failure at database drop and let later role drop plus verification run.
        def execute(_statement, _parameters=None):
            # Mutate only the test-local operation counter.
            nonlocal statement_index
            # Advance through termination, database, role, and verification.
            statement_index += 1
            # Fail only the database drop at position two.
            if statement_index == 2:
                # Preserve exact source-owned failure identity.
                raise drop_failure
        # Route each cleanup statement through the ordered model.
        cursor.execute.side_effect = execute
        # Report final zero identity residue after the continued role drop.
        cursor.fetchone.return_value = (0, 0)
        # Supply the exact modeled administrator connection.
        with mock.patch.object(harness, "_admin_connection", return_value=admin):
            # Require the first drop failure only after all later operations.
            try:
                # Execute the real identity-cleanup implementation.
                harness._drop_identities()
            except _HarnessFailure as error:
                # Preserve exact first-failure identity.
                self.assertIs(drop_failure, error)
            else:
                # Fail if identity cleanup suppressed its first failure.
                self.fail("database drop failure was not raised")
        # Require termination, both drops, verification, and connector close.
        self.assertEqual((4, 1), (cursor.execute.call_count, admin.close.call_count))
        # Release ownership only because final verification proved zero residue.
        self.assertFalse(harness._identities_owned)

    # Prove the common lifecycle preserves a relational partial-create failure over cleanup.
    def test_postgres_partial_create_preserves_original_failure(self) -> None:
        """Keep the exact create exception while cleanup removes every owned resource."""

        # Import the protected lifecycle runner only inside this focused proof.
        from tests.storage_conformance.test_json_conformance import _run_harness_contract
        # Allocate one verified root that modeled partial create will own.
        root = Path(tempfile.mkdtemp(prefix="storage-conformance-postgres-")).resolve()
        # Construct a real PostgreSQL harness without authorization or optional imports.
        harness = database_harnesses.PostgresHarness()
        # Freeze distinct primary-create and secondary-close failures.
        primary = _HarnessFailure("partial create failure")
        # Attach a later cleanup failure that the runner must not surface.
        provider = _ClosingProvider(_HarnessFailure("secondary cleanup failure"))
        # Model create after root allocation and an ambiguous start attempt.
        def partial_create():
            # Retain root, data, and provider ownership before failure.
            harness._root, harness._data_root, harness._provider = root, root / "data", provider
            # Mark process cleanup ownership as create would before pg_ctl returns.
            harness._started, harness._start_attempted = True, True
            # Raise the exact primary failure object.
            raise primary
        # Model a successful verified stop without a real process.
        def stop_owned_process():
            # Release confirmed and attempted process ownership together.
            harness._started, harness._start_attempted = False, False
        # Install only the two lifecycle seams required for the partial-create schedule.
        with mock.patch.object(harness, "create", side_effect=partial_create), mock.patch.object(harness, "_stop_cluster", side_effect=stop_owned_process):
            # Capture exact primary identity after best-effort cleanup.
            try:
                # Run the same protected lifecycle used by registered providers.
                _run_harness_contract(harness)
            except _HarnessFailure as error:
                # Preserve the original create failure rather than cleanup failure.
                self.assertIs(primary, error)
            else:
                # Fail if the lifecycle suppressed partial-create failure.
                self.fail("partial create failure was not raised")
        # Require the later provider close was attempted once.
        self.assertEqual(1, provider.calls)
        # Require cleanup removed the task-owned root despite its secondary failure.
        self.assertFalse(root.exists())


if __name__ == "__main__":
    # Support direct focused execution without central-runner mutation.
    unittest.main()
