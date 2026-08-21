# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused TEST-251 safety and aggregate-shape tests for the Gunicorn load smoke."""

# Import JSON parsing for atomic aggregate report checks.
import json
# Import environment and platform patching for listener-free boundary tests.
import os
# Import disposable external directories for report ownership tests.
import tempfile
# Import standard unittest assertions and execution.
import unittest
# Import deterministic patching support for environment-only qualification seams.
from unittest.mock import patch
# Import portable paths for external destination construction.
from pathlib import Path

# Import the production-stack qualification module without executing its CLI.
from tests import gunicorn_load_smoke


# Verify fail-closed authorization, telemetry, output, and serving-stack ownership.
class GunicornLoadSmokeTests(unittest.TestCase):
    # Confirm the exact marker and external report root are mandatory.
    def test_boundary_requires_marker_and_external_report(self):
        # Allocate one caller-external destination owned only by this test.
        with tempfile.TemporaryDirectory() as temporary:
            # Resolve a report below the disposable external root.
            report = Path(temporary) / "load.json"
            # Remove the issue marker to prove default refusal.
            with patch.dict(os.environ, {}, clear=True):
                # Require refusal before any process construction.
                with self.assertRaises(gunicorn_load_smoke.GunicornLoadSmokeError):
                    # Validate only the listener-free boundary.
                    gunicorn_load_smoke.validate_boundaries("json", gunicorn_load_smoke.CI_USERS, report)
            # Supply only the exact issue marker for a valid JSON target.
            with patch.dict(os.environ, {gunicorn_load_smoke.DISPOSABLE_MARKER: "1"}, clear=True):
                # Require the external report to be accepted exactly.
                self.assertEqual(report.resolve(), gunicorn_load_smoke.validate_boundaries("json", gunicorn_load_smoke.CI_USERS, report))
                # Refuse a report beneath the source checkout.
                with self.assertRaises(gunicorn_load_smoke.GunicornLoadSmokeError):
                    # Point at a never-created repository-local path.
                    gunicorn_load_smoke.validate_boundaries("json", gunicorn_load_smoke.CI_USERS, gunicorn_load_smoke.ROOT / "load.json")

    # Confirm MySQL adds a second exact disposable-target marker.
    def test_mysql_boundary_requires_database_marker(self):
        # Allocate one valid external output path.
        with tempfile.TemporaryDirectory() as temporary:
            # Build the external path without writing it.
            report = Path(temporary) / "mysql.json"
            # Supply the issue marker but omit database authorization.
            with patch.dict(os.environ, {gunicorn_load_smoke.DISPOSABLE_MARKER: "1"}, clear=True):
                # Require refusal before connector or listener construction.
                with self.assertRaises(gunicorn_load_smoke.GunicornLoadSmokeError):
                    # Validate only the MySQL authorization boundary.
                    gunicorn_load_smoke.validate_boundaries("mysql", gunicorn_load_smoke.CI_USERS, report)
            # Supply both exact disposable markers.
            with patch.dict(os.environ, {gunicorn_load_smoke.DISPOSABLE_MARKER: "1", "CASINO_MYSQL_DISPOSABLE_TEST": "1"}, clear=True):
                # Accept only the external destination after both markers pass.
                self.assertEqual(report.resolve(), gunicorn_load_smoke.validate_boundaries("mysql", gunicorn_load_smoke.FORMAL_USERS, report))

    # Confirm the production-stack child keeps runtime DML authority but no administrator or migrator capability.
    def test_mysql_service_environment_is_minimized_and_load_bounded(self):
        # Seed every forbidden capability to prove projection removes rather than merely omits it.
        hostile = {key: "private-secret" for key in gunicorn_load_smoke.MYSQL_CHILD_CAPABILITY_KEYS}
        # Preserve one synthetic runtime DML identity that the disposable child requires.
        hostile.update({"CASINO_MYSQL_USER": "runtime-user", "CASINO_MYSQL_PASSWORD": "runtime-secret"})
        # Isolate the exact source mapping around environment construction.
        with patch.dict(os.environ, hostile, clear=True):
            # Allocate a disposable absolute runtime root without opening a listener.
            with tempfile.TemporaryDirectory() as temporary:
                # Build only the child environment for structural assertions.
                environment = gunicorn_load_smoke.service_environment(Path(temporary), 18765, "mysql")
        # Require every administrator and migrator capability to be absent from the worker.
        self.assertFalse(set(gunicorn_load_smoke.MYSQL_CHILD_CAPABILITY_KEYS) & set(environment))
        # Require the runtime DML identity to survive without exposing its value in evidence.
        self.assertIn("CASINO_MYSQL_USER", environment)
        # Bind the production stack, pool, and fixed synthetic request allowance.
        self.assertEqual(("production", "mysql", "1", "32", "16", "10000", "10000", "60"), (environment["CASINO_DEPLOYMENT_MODE"], environment["CASINO_STORAGE_PROVIDER"], environment["CASINO_GUNICORN_WORKERS"], environment["CASINO_GUNICORN_THREADS"], environment["CASINO_MYSQL_POOL_SIZE"], environment["CASINO_MYSQL_POOL_WAIT_MS"], environment["CASINO_RATE_LIMIT_REQUESTS"], environment["CASINO_RATE_LIMIT_WINDOW_SECONDS"]))
        # Require the shared-MySQL child to reuse the preceding benchmark's one synthetic bootstrap identity.
        self.assertEqual((gunicorn_load_smoke.request_latency_benchmark.SYNTHETIC_EMAIL, gunicorn_load_smoke.request_latency_benchmark.SYNTHETIC_PASSWORD), (environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"], environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"]))
        # Require both sequential children to address the same persisted authentication namespaces.
        self.assertEqual((gunicorn_load_smoke.request_latency_benchmark.SYNTHETIC_TOKEN_DIGEST_KEY, gunicorn_load_smoke.request_latency_benchmark.SYNTHETIC_MAIL_DIGEST_KEY), (environment["CASINO_TOKEN_DIGEST_KEY"], environment["CASINO_MAIL_DIGEST_KEY"]))
        # Require one complete hash-only synthetic monitor verifier.
        self.assertEqual(64, len(environment["CASINO_EDGE_MONITOR_TOKEN_SHA256"]))
        # Keep both hosted queue waits explicit, finite, and long enough for the reviewed 100-to-32 fan-in.
        self.assertEqual((120, 180), (gunicorn_load_smoke.LOAD_REQUEST_TIMEOUT_SECONDS, gunicorn_load_smoke.LOAD_BARRIER_TIMEOUT_SECONDS))
        # Bound routine login concurrency independently from the complete 32-session round population.
        self.assertEqual(8, gunicorn_load_smoke.CI_LOGIN_WORKERS)

    # Confirm provider-specific Admin telemetry is strict and rebuilt.
    def test_pool_telemetry_variants_are_exact(self):
        # Accept only the explicit JSON unavailable variant.
        self.assertEqual({"available": False}, gunicorn_load_smoke.validate_pool_telemetry("json", {"ok": True, "data": {"storage_pool": {"available": False}}}))
        # Build one clean terminal MySQL aggregate.
        mysql_pool = {"available": True, "capacity": 16, "in_use": 0, "idle": 16, "waiting": 0, "saturation_count": 9, "timeout_count": 0}
        # Require the exact allowlisted object to survive validation unchanged.
        self.assertEqual(mysql_pool, gunicorn_load_smoke.validate_pool_telemetry("mysql", {"ok": True, "data": {"storage_pool": mysql_pool}}))
        # Reject a secret-bearing undeclared telemetry key.
        hostile = {**mysql_pool, "dsn": "mysql://admin:secret@private"}
        # Keep provider detail behind the fixed error category.
        with self.assertRaises(gunicorn_load_smoke.GunicornLoadSmokeError):
            # Validate the hostile otherwise-shaped response.
            gunicorn_load_smoke.validate_pool_telemetry("mysql", {"ok": True, "data": {"storage_pool": hostile}})

    # Confirm reports are stable aggregate JSON and atomically replace prior bytes.
    def test_atomic_report_contains_only_supplied_aggregate(self):
        # Allocate one external test-owned report root.
        with tempfile.TemporaryDirectory() as temporary:
            # Select the report file without creating it first.
            report_path = Path(temporary) / "nested" / "load.json"
            # Build one synthetic aggregate with no identity fields.
            report = {"schema": 1, "status": "PASS", "users": 32, "errors": 0}
            # Publish through the production atomic writer.
            gunicorn_load_smoke.write_report(report_path, report)
            # Require exact semantic round-trip and no temporary residue.
            self.assertEqual(report, json.loads(report_path.read_text(encoding="utf-8")))
            # Require the same-directory temporary name to be absent after replacement.
            self.assertFalse(report_path.with_name(report_path.name + ".tmp").exists())

    # Confirm the qualification owns Gunicorn and never imports the development HTTP server.
    def test_source_uses_only_production_listener(self):
        # Read the exact module text for serving-stack ownership assertions.
        source = Path(gunicorn_load_smoke.__file__).read_text(encoding="utf-8")
        # Require the accepted production lifecycle helper.
        self.assertIn("production_service_smoke.start_service", source)
        # Reject the development adapter from the complete qualification source.
        self.assertNotIn("ThreadingHTTPServer", source)
        # Require one thread barrier for synchronized post-authentication rounds.
        self.assertIn("threading.Barrier(users)", source)
        # Require the synchronized rendezvous to consume the reviewed bounded timeout constant.
        self.assertIn("barrier.wait(timeout=LOAD_BARRIER_TIMEOUT_SECONDS)", source)
        # Require routine logins to materialize under the reviewed bounded authentication worker pool.
        self.assertIn("ThreadPoolExecutor(max_workers=CI_LOGIN_WORKERS)", source)
        # Require every routine and formal action to traverse the same synchronized public-round worker.
        self.assertIn("executor.submit(run_authenticated_round, base_url, session, index, barrier)", source)
        # Reject the former worker path that could strand successful logins behind a failed peer's round barrier.
        self.assertNotIn("executor.submit(run_user", source)

    # Confirm the formal production-stack gate owns an independent runner and explicit dispatch input.
    def test_formal_workflow_isolated_from_browser_138(self):
        # Read the tracked workflow as inert declarative text.
        workflow = (gunicorn_load_smoke.ROOT / ".github" / "workflows" / "browser-tests.yml").read_text(encoding="utf-8")
        # Require exactly one dispatch input and one job identity for the new formal gate.
        self.assertEqual(2, workflow.count("gunicorn_load_100:"))
        # Isolate the complete production-stack job from the unrelated browser qualification job.
        job = workflow.split("\n  gunicorn_load_100:\n", 1)[1]
        # Require explicit owner dispatch rather than ordinary pull-request execution.
        self.assertIn("inputs.gunicorn_load_100 == true", job)
        # Bind the exact formal population and one caller-external aggregate.
        self.assertIn("CASINO_1040_LOAD_USERS: 100", job)
        self.assertIn("CASINO_1040_LOAD_REPORT: ${{ runner.temp }}/casino-gunicorn-load-100.json", job)
        # Require a separate terminal artifact that cannot be confused with the 138-browser report.
        self.assertIn("gunicorn-load-100-${{ github.sha }}", job)
        # Require the existing browser job to remain free of the production-stack population controls.
        browser_job = workflow.split("\n  concurrent_browser_138:\n", 1)[1].split("\n  gunicorn_load_100:\n", 1)[0]
        # Reject coupling that previously consumed both formal process budgets on one hosted runner.
        self.assertNotIn("CASINO_1040_LOAD_USERS", browser_job)


# Run this focused suite directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's ordinary result handling.
    unittest.main()
