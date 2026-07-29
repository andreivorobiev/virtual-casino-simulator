"""Listener-free unit proof for the TEST-148 request-latency baseline."""

# Import callable signature inspection for the optional MySQL callback seam.
import inspect
# Import JSON parsing for atomic evidence assertions.
import json
# Import environment and interpreter access for isolated import proof.
import os
# Import portable paths for exact checkout and source inspection.
from pathlib import Path
# Import subprocess execution for a fresh import-order probe.
import subprocess
# Import the active interpreter path for the import-order probe.
import sys
# Import caller-external temporary directories for evidence writes.
import tempfile
# Import standard unittest assertions and cleanup.
import unittest
# Import deterministic patching for child and environment tests.
from unittest import mock

# Import the benchmark module whose top level must remain Casino-runtime-free.
from tests import request_latency_benchmark as benchmark
# Import the migration module for source and signature verification only.
from tests import mysql_migration_live

# Resolve the exact checkout independently of the test runner.
ROOT = Path(__file__).resolve().parents[2]


# Provide one immediately readable fake future for scheduler proof.
class _FakeFuture:
    # Bind one deterministic result and its owning fake executor.
    def __init__(self, value, executor) -> None:
        # Retain the submitted operation result.
        self.value = value
        # Retain the executor so the fake waiter can release one pending slot.
        self.executor = executor

    # Return the deterministic operation result.
    def result(self):
        # Return without executing another operation.
        return self.value


# Track submitted and outstanding operations without creating threads.
class _FakeExecutor:
    # Publish the last created executor for post-run assertions.
    last = None

    # Initialize one fixed-capacity fake pool.
    def __init__(self, max_workers: int) -> None:
        # Retain the selected concurrency.
        self.max_workers = max_workers
        # Count all submissions across the row.
        self.submitted = 0
        # Count futures not yet released by the fake waiter.
        self.outstanding = 0
        # Track the maximum outstanding count.
        self.maximum_outstanding = 0
        # Publish this instance for the test.
        _FakeExecutor.last = self

    # Submit one operation immediately while retaining pending accounting.
    def submit(self, operation, index):
        # Count the new submission.
        self.submitted += 1
        # Count the new pending future.
        self.outstanding += 1
        # Record the pending high-water mark.
        self.maximum_outstanding = max(self.maximum_outstanding, self.outstanding)
        # Evaluate the deterministic operation and wrap its result.
        return _FakeFuture(operation(index), self)

    # Accept the production shutdown signature without creating workers.
    def shutdown(self, wait=True, cancel_futures=True) -> None:
        # Require all fake futures to have been released before shutdown.
        if self.outstanding:
            # Surface a fake-scheduler accounting defect.
            raise AssertionError("fake executor still owns pending futures")


# Release one fake future per scheduler wait call.
def _fake_wait(pending, return_when=None):
    # Select one submitted future to complete.
    completed = next(iter(pending))
    # Release exactly one pending slot.
    completed.executor.outstanding -= 1
    # Return the one completion plus the remaining pending set.
    return {completed}, set(pending) - {completed}


# Validate benchmark privacy, scheduler, lifecycle, and selector policy.
class RequestLatencyBenchmarkTests(unittest.TestCase):
    # Build one complete valid evidence packet for mutation tests.
    def evidence(self) -> dict:
        # Build every required route/concurrency row.
        rows = [
            {
                # Preserve the fixed low-cardinality route family.
                "route_family": route,
                # Preserve the fixed concurrency.
                "concurrency": concurrency,
                # Supply a finite median aggregate.
                "p50_ms": 1.0,
                # Supply a finite p95 aggregate.
                "p95_ms": 2.0,
                # Supply a finite throughput aggregate.
                "throughput_rps": 3.0,
                # Require zero accepted errors.
                "errors": 0,
                # Supply only an aggregate byte total.
                "response_bytes": 64,
            }
            for route in benchmark.ROUTE_FAMILIES  # Cover every fixed route family.
            for concurrency in benchmark.CONCURRENCY_LEVELS  # Cover every governed concurrency.
        ]
        # Return the complete top-level allowlist.
        return {
            "schema": benchmark.EVIDENCE_SCHEMA,  # Use the exact schema identity.
            "source_commit": "a" * 40,  # Use exact hexadecimal test provenance.
            "provider": "json",  # Use one approved provider.
            "rows": rows,  # Include the complete aggregate grid.
        }

    # Prove importing the benchmark never imports the WSGI adapter or a socket server.
    def test_import_is_wsgi_lazy_and_listener_free(self) -> None:
        # Build a fresh interpreter probe that inspects loaded modules after import.
        probe = "import sys; import tests.request_latency_benchmark; raise SystemExit(1 if 'casino.wsgi' in sys.modules else 0)"
        # Run the probe from the exact checkout.
        result = subprocess.run(
            [sys.executable, "-c", probe],  # Execute only the import-order probe.
            cwd=str(ROOT),  # Resolve the exact checkout.
            capture_output=True,  # Keep child output out of the test log.
            text=True,  # Decode process management output.
            timeout=15,  # Bound the dependency-free import.
        )
        # Require a runtime-free module import.
        self.assertEqual(result.returncode, 0)
        # Read the benchmark source for listener primitives.
        source = inspect.getsource(benchmark)
        # Reject any socket import or bind/listen call.
        self.assertNotIn("import socket", source)
        # Require the WSGI import to remain inside the configured child runner.
        self.assertGreater(source.index("from casino.wsgi import application"), source.index("_configure_child_environment(provider, runtime_root)"))

    # Prove exact fixed matrix constants and the test-only rate allowance.
    def test_fixed_matrix_and_rate_allowance(self) -> None:
        # Pin the four accepted concurrency values.
        self.assertEqual(benchmark.CONCURRENCY_LEVELS, (1, 2, 4, 8))
        # Pin the fixed warm-up count.
        self.assertEqual(benchmark.WARMUP_OPERATIONS, 8)
        # Pin the exact measured operation count.
        self.assertEqual(benchmark.MEASURED_OPERATIONS, 64)
        # Pin the fixed test-only rate allowance.
        self.assertEqual(benchmark.TEST_RATE_ALLOWANCE, 10_000)
        # Pin the exact five route families.
        self.assertEqual(
            benchmark.ROUTE_FAMILIES,  # Inspect the benchmark-owned sequence.
            ("current_user", "slots_state", "roulette_state", "casino_state", "boule_spin"),  # Pin all five.
        )

    # Prove the rolling scheduler never pre-submits the complete row.
    def test_scheduler_keeps_at_most_concurrency_pending(self) -> None:
        # Execute sixty-four deterministic operations through a four-slot fake pool.
        results, maximum_pending = benchmark.rolling_bounded_map(
            lambda index: index,  # Return the unique operation index.
            64,  # Exercise the exact measured row count.
            4,  # Exercise one governed concurrency.
            executor_factory=_FakeExecutor,  # Inject deterministic pending accounting.
            wait_function=_fake_wait,  # Release one future per rolling step.
        )
        # Require exact operation accounting.
        self.assertEqual(sorted(results), list(range(64)))
        # Require the scheduler-reported high-water mark to equal N.
        self.assertEqual(maximum_pending, 4)
        # Read the fake executor used by the run.
        executor = _FakeExecutor.last
        # Require exactly sixty-four submissions overall.
        self.assertEqual(executor.submitted, 64)
        # Prove the executor never observed more than N pending futures.
        self.assertEqual(executor.maximum_outstanding, 4)

    # Prove every timed Boule operation owns a unique non-control key.
    def test_timed_boule_keys_are_unique_and_separate_from_controls(self) -> None:
        # Capture request bodies without invoking the WSGI application.
        captured = []

        # Provide the minimum client request seam used by the operation builder.
        class Client:
            # Record one fixed-path request.
            def request(self, method, path, body):
                # Retain only the body for key assertions.
                captured.append((method, path, body))
                # Return an unused sentinel.
                return object()

        # Build the measured concurrency-four operation.
        operation = benchmark._route_operation(Client(), "boule_spin", 4, "measured")
        # Generate all sixty-four unique timed requests.
        for index in range(64):
            # Execute only the request-construction seam.
            operation(index)
        # Extract every generated request identity.
        keys = [body["request_id"] for _, _, body in captured]
        # Require exact one-to-one key cardinality.
        self.assertEqual(len(keys), len(set(keys)))
        # Require no timed key to reuse the untimed control identity.
        self.assertNotIn("latency-boule-control", keys)
        # Require the exact public Boule route on every operation.
        self.assertTrue(all(method == "POST" and path == "/api/v1/games/boule/spins" for method, path, _ in captured))

    # Prove receipt-cap controls retain replay and conflict behavior outside timing.
    def test_boule_receipt_cap_control_replays_then_conflicts(self) -> None:
        # Capture both post-cap request bodies in order.
        captured = []

        # Provide one minimal response object matching the direct client seam.
        class Response:
            # Store the fixed status and standard payload.
            def __init__(self, status, payload):
                # Retain the status for the control assertion.
                self.status = status
                # Retain the payload for the control assertion.
                self._payload = payload

            # Return the standard response payload.
            def payload(self):
                # Expose only the test-owned response.
                return self._payload

        # Provide replay success followed by semantic conflict.
        class Client:
            # Execute one deterministic control response.
            def request(self, method, path, body):
                # Retain the exact request for postconditions.
                captured.append((method, path, body))
                # Return durable replay for the original body.
                if body["bet"] == "even":
                    # Model the standard successful replay envelope.
                    return Response("200 OK", {"ok": True, "data": {"replayed": True}})
                # Model the standard conflict envelope for changed content.
                return Response("409 Conflict", {"ok": False, "error": {"code": "CONFLICT"}})

        # Execute both receipt-cap controls outside timed work.
        benchmark._boule_receipt_cap_control(Client())
        # Require exact original then conflicting bodies under one durable key.
        self.assertEqual(
            [body for _, _, body in captured],
            [
                {"request_id": "latency-boule-control", "bet": "even", "stake": 1},
                {"request_id": "latency-boule-control", "bet": "odd", "stake": 1},
            ],
        )

    # Prove the output schema rejects every extra top-level or row field.
    def test_evidence_allowlist_rejects_private_or_extra_fields(self) -> None:
        # Validate one complete allowed packet.
        benchmark.validate_evidence(self.evidence())
        # Add a forbidden identity-bearing top-level field.
        top_extra = self.evidence()
        # Inject one private field that must be rejected.
        top_extra["player_id"] = "forbidden"
        # Require fail-closed rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the hostile packet.
            benchmark.validate_evidence(top_extra)
        # Add a forbidden sample-level field inside one row.
        row_extra = self.evidence()
        # Inject one raw-sample field that must be rejected.
        row_extra["rows"][0]["samples"] = [1.0]
        # Require fail-closed rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the hostile row.
            benchmark.validate_evidence(row_extra)

    # Prove evidence writes atomically only outside the checkout.
    def test_atomic_output_requires_external_caller_path(self) -> None:
        # Allocate a caller-owned directory outside the checkout.
        with tempfile.TemporaryDirectory(prefix="request-latency-unit-") as temporary:
            # Select one external destination.
            output = Path(temporary) / "evidence.json"
            # Write one validated packet atomically.
            written = benchmark.write_evidence_atomic(output, self.evidence())
            # Require exact destination selection.
            self.assertEqual(written, output.resolve())
            # Require the parsed packet to equal the validated source.
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), self.evidence())
            # Require no benchmark-owned temporary file to remain.
            self.assertEqual(list(Path(temporary).glob(".request-latency-*.tmp")), [])
        # Select a forbidden checkout-owned destination.
        inside_checkout = ROOT / "request-latency-forbidden.json"
        # Require containment rejection before any file creation.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Attempt the forbidden write.
            benchmark.write_evidence_atomic(inside_checkout, self.evidence())
        # Require the forbidden destination to remain absent.
        self.assertFalse(inside_checkout.exists())

    # Prove failed atomic replacement preserves prior caller content and cleans its temporary file.
    def test_atomic_replacement_failure_preserves_existing_output(self) -> None:
        # Allocate a caller-owned external directory.
        with tempfile.TemporaryDirectory(prefix="request-latency-atomic-") as temporary:
            # Select one existing destination.
            output = Path(temporary) / "evidence.json"
            # Seed caller-owned prior content.
            output.write_text("prior\n", encoding="utf-8")
            # Force only the final atomic replacement to fail.
            with mock.patch.object(benchmark.os, "replace", side_effect=OSError("synthetic")):
                # Require propagation for the explicit caller.
                with self.assertRaises(OSError):
                    # Attempt the atomic update.
                    benchmark.write_evidence_atomic(output, self.evidence())
            # Require byte-for-byte preservation of caller content.
            self.assertEqual(output.read_text(encoding="utf-8"), "prior\n")
            # Require cleanup of the benchmark-owned temporary file.
            self.assertEqual(list(Path(temporary).glob(".request-latency-*.tmp")), [])

    # Prove child setup applies rate policy and removes every MySQL pool override.
    def test_child_environment_uses_fixed_rate_and_default_pool_settings(self) -> None:
        # Allocate one external runtime root.
        with tempfile.TemporaryDirectory(prefix="request-latency-env-") as temporary:
            # Supply hostile optional pool overrides only inside the patch.
            overrides = {
                "CASINO_MYSQL_POOL_SIZE": "16",
                "CASINO_MYSQL_POOL_WAIT_MS": "10000",
                "CASINO_MYSQL_POOL_MAX_IDLE_SECONDS": "999",
            }
            # Restore the caller environment after configuration proof.
            with mock.patch.dict(os.environ, overrides, clear=False):
                # Configure the JSON child without importing Casino runtime packages.
                benchmark._configure_child_environment("json", Path(temporary))
                # Require the exact test-only request allowance.
                self.assertEqual(os.environ["CASINO_RATE_LIMIT_REQUESTS"], "10000")
                # Require every optional pool override to be absent.
                self.assertTrue(all(key not in os.environ for key in benchmark.MYSQL_POOL_OVERRIDE_KEYS))

    # Prove the MySQL callback is optional, no-argument, and inside guarded cleanup.
    def test_mysql_callback_seam_is_optional_credential_free_and_precleanup(self) -> None:
        # Inspect the public live-matrix signature.
        signature = inspect.signature(mysql_migration_live.run_mysql_migration_live_matrix)
        # Require one optional callback with an unchanged no-argument default.
        self.assertIsNone(signature.parameters["request_latency_callback"].default)
        # Read the exact callback source.
        source = inspect.getsource(mysql_migration_live.run_mysql_migration_live_matrix)
        # Require the runtime DML/grant path to precede the callback invocation.
        self.assertLess(source.index("storage_tests.run_mysql_live_provider_path()"), source.index("request_latency_callback()"))
        # Require the callback invocation to precede the existing cleanup.
        self.assertLess(source.index("request_latency_callback()"), source.index("_cleanup(admin, databases, migrator_user, runtime_user)"))
        # Require an argument-free invocation so no credential crosses the seam.
        self.assertIn("request_latency_callback()", source)

    # Prove ordinary API selection runs only unit proof and benchmarks remain explicit.
    def test_run_tests_keeps_benchmark_behind_explicit_selector(self) -> None:
        # Read the central runner as policy.
        source = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Require ordinary API registration of only the listener-free unit case.
        self.assertIn("REQUEST-LATENCY-UNIT-001", source)
        # Require the explicit provider selector.
        self.assertIn("ap.add_argument('--request-latency',choices=('json','mysql'),default=None)", source)
        # Require the explicit output selector.
        self.assertIn("ap.add_argument('--request-latency-output',default=None)", source)
        # Require JSON execution to depend on the explicit selector.
        self.assertIn("if args.request_latency=='json':", source)
        # Require MySQL execution to remain an optional callback.
        self.assertIn("request_latency_callback=request_latency_callback", source)

    # Prove the current governance allocation remains TEST-148 and tests/docs only.
    def test_governance_allocation_is_unique_and_narrow(self) -> None:
        # Parse the canonical requirement source.
        requirements = json.loads((ROOT / "docs" / "requirements" / "requirements.json").read_text(encoding="utf-8"))["requirements"]
        # Count permanent TEST-148 allocations.
        test_148 = [row for row in requirements if row.get("id") == "TEST-148"]
        # Require exactly one permanent allocation after governance is spliced.
        self.assertEqual(len(test_148), 1)
        # Require the tests module ownership.
        self.assertEqual(test_148[0]["module"], "Tests")
        # Parse the two owned descriptors.
        tests_module = json.loads((ROOT / "modules" / "tests.json").read_text(encoding="utf-8"))
        # Parse the docs descriptor independently.
        docs_module = json.loads((ROOT / "modules" / "docs.json").read_text(encoding="utf-8"))
        # Require the exact shared patch allocation.
        self.assertEqual(tests_module["version"], "1.64.34")
        # Require docs to match generated requirement ownership.
        self.assertEqual(docs_module["version"], "1.64.34")
