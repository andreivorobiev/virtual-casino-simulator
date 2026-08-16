# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free unit proof for the TEST-148 request-latency baseline."""

# Import syntax-tree inspection for network and selector policy proof.
import ast
# Import module loading so the standalone terminology validator can be exercised without a subprocess.
import importlib.util
# Import callable signature inspection for the optional MySQL callback seam.
import inspect
# Import JSON parsing for atomic evidence assertions.
import json
# Import environment and interpreter access for isolated import proof.
import os
# Import portable paths for exact checkout and source inspection.
from pathlib import Path
# Import strict commit-pattern support for isolated runner-helper execution.
import re
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


# Return one injected failure only when the scheduler collects the future.
class _FailingFuture(_FakeFuture):
    # Raise the stored failure instead of returning a result.
    def result(self):
        # Surface one deterministic worker failure.
        raise RuntimeError("synthetic worker failure")


# Track shutdown behavior for an injected worker failure.
class _FailingExecutor(_FakeExecutor):
    # Publish the most recent failing executor.
    last = None

    # Initialize inherited accounting plus a shutdown marker.
    def __init__(self, max_workers: int) -> None:
        # Initialize bounded pending accounting.
        super().__init__(max_workers)
        # Track whether finally invoked shutdown.
        self.shutdown_called = False
        # Publish this failing instance.
        _FailingExecutor.last = self

    # Submit success futures except for one deterministic index.
    def submit(self, operation, index):
        # Count the new submission.
        self.submitted += 1
        # Count the pending future.
        self.outstanding += 1
        # Record the pending high-water mark.
        self.maximum_outstanding = max(self.maximum_outstanding, self.outstanding)
        # Return a deferred failing future for one index.
        if index == 1:
            # Surface the failure only when result is collected.
            return _FailingFuture(None, self)
        # Execute all other deterministic operations.
        return _FakeFuture(operation(index), self)

    # Mark cleanup and accept cancellation of uncollected futures.
    def shutdown(self, wait=True, cancel_futures=True) -> None:
        # Record the finally-owned shutdown.
        self.shutdown_called = True
        # Treat pending futures as canceled by the requested cleanup policy.
        self.outstanding = 0


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

    # Prove importing the benchmark never imports a runtime, network client, browser, or server.
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
        # Parse executable syntax rather than comments or documentation.
        tree = ast.parse(source)
        # Collect every imported top-level package.
        imported = {
            # Normalize an ordinary import to its root package.
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)  # Inspect the complete benchmark syntax.
            if isinstance(node, ast.Import)  # Select ordinary imports.
            for alias in node.names  # Expand every alias in one import statement.
        }
        # Add every from-import root package.
        imported.update(
            # Normalize a from-import to its root package.
            str(node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)  # Inspect the same complete syntax tree.
            if isinstance(node, ast.ImportFrom)  # Select from-import statements.
        )
        # Reject every network client, browser driver, and server runtime family.
        self.assertTrue(
            imported.isdisjoint({"socket", "urllib", "requests", "httpx", "playwright", "selenium", "gunicorn", "webbrowser"})  # Reject all forbidden packages.
        )
        # Collect every called attribute name for server-primitive rejection.
        called_attributes = {
            # Retain only the terminal attribute name.
            node.func.attr
            for node in ast.walk(tree)  # Inspect every executable call.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)  # Select attribute calls.
        }
        # Reject listener and server lifecycle primitives.
        self.assertTrue(called_attributes.isdisjoint({"bind", "listen", "serve_forever", "make_server", "run_simple"}))
        # Collect every explicit command-line selector.
        selectors = {
            # Retain the first literal selector argument.
            node.args[0].value
            for node in ast.walk(tree)  # Inspect every call expression.
            if isinstance(node, ast.Call)  # Select call expressions.
            and isinstance(node.func, ast.Attribute)  # Require an object method call.
            and node.func.attr == "add_argument"  # Select parser selector declarations.
            and node.args  # Require a positional selector.
            and isinstance(node.args[0], ast.Constant)  # Require one literal selector.
            and isinstance(node.args[0].value, str)  # Keep string selectors only.
        }
        # Permit only the fixed provider, provenance, and external-output selectors.
        self.assertEqual(selectors, {"--provider", "--source-commit", "--output"})
        # Collect every literal fixed application path.
        paths = {
            # Retain one root-relative literal.
            node.value
            for node in ast.walk(tree)  # Inspect every literal.
            if isinstance(node, ast.Constant)  # Select constants.
            and isinstance(node.value, str)  # Retain strings only.
            and node.value.startswith("/")  # Select fixed internal paths.
        }
        # Pin the complete listener-free internal path contract.
        self.assertEqual(
            paths,  # Compare the discovered literal path set.
            {
                "/",  # Permit only the anonymous bootstrap shell.
                "/api/v2/auth/login",  # Permit only the fixed login route.
                "/api/v2/me",  # Permit only the current-user read.
                "/api/v1/games/slots/state",  # Permit only the Slots state read.
                "/api/v1/games/roulette/state",  # Permit only the Roulette state read.
                "/api/v1/casino/state",  # Permit only the aggregate state read.
                "/api/v1/games/boule/spins",  # Permit only the Boule mutation.
            },
        )
        # Collect every absolute URL literal.
        absolute_urls = {
            # Retain one URL literal.
            node.value
            for node in ast.walk(tree)  # Inspect every source literal.
            if isinstance(node, ast.Constant)  # Select constants.
            and isinstance(node.value, str)  # Retain strings only.
            and node.value.startswith(("http://", "https://"))  # Select absolute URLs.
        }
        # Permit only the reserved synthetic origin.
        self.assertEqual(absolute_urls, {benchmark.SYNTHETIC_ORIGIN})
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

    # Prove every read family maps to one exact method and internal path.
    def test_exact_read_route_method_and_path_mappings(self) -> None:
        # Capture listener-free request construction.
        captured = []

        # Provide the minimal request seam used by read operations.
        class Client:
            # Record one exact fixed read.
            def request(self, method, path):
                # Retain only method and path.
                captured.append((method, path))
                # Return one unused sentinel.
                return object()

        # Execute one operation for every read family.
        for route_family in benchmark.READ_ROUTE_FAMILIES:
            # Build the fixed operation.
            operation = benchmark._route_operation(Client(), route_family, 1, "measured")
            # Execute one indexed request.
            operation(0)
        # Pin the complete four-route contract.
        self.assertEqual(
            captured,  # Compare the complete request sequence.
            [
                ("GET", "/api/v2/me"),  # Pin the current-user request.
                ("GET", "/api/v1/games/slots/state"),  # Pin the Slots request.
                ("GET", "/api/v1/games/roulette/state"),  # Pin the Roulette request.
                ("GET", "/api/v1/casino/state"),  # Pin the aggregate request.
            ],
        )

    # Prove the direct client builds one fixed listener-free WSGI request boundary.
    def test_direct_wsgi_contract_has_fixed_paths_auth_and_origin(self) -> None:
        # Capture each application-owned WSGI environment.
        captured = []
        # Build one valid response body.
        body = b'{"ok":true,"data":{}}'

        # Provide one direct WSGI callable without opening a listener.
        def application(environ, start_response):
            # Retain a shallow copy before request-owned streams are released.
            captured.append(dict(environ))
            # Emit exact framing for the fully consumed body.
            start_response("200 OK", [("Content-Length", str(len(body)))])
            # Return one bounded iterable.
            return [body]

        # Bind the direct client and synthetic session proofs.
        client = benchmark.DirectWSGIClient(application)
        # Supply one synthetic bearer only inside the unit.
        client.token = "unit-bearer"
        # Supply one synthetic CSRF proof only inside the unit.
        client.csrf_token = "unit-csrf"
        # Execute one anonymous bootstrap read.
        client.request("GET", "/", authenticated=False)
        # Execute one authenticated fixed read.
        client.request("GET", "/api/v2/me")
        # Execute one authenticated fixed mutation.
        client.request("POST", "/api/v1/games/boule/spins", {"request_id": "unit", "bet": "even", "stake": 1})
        # Require direct callable execution with no listener object.
        self.assertEqual(len(captured), 3)
        # Require exact request method, path, and empty query for every call.
        self.assertEqual(
            [(item["REQUEST_METHOD"], item["PATH_INFO"], item["QUERY_STRING"]) for item in captured],  # Project request routing.
            [("GET", "/", ""), ("GET", "/api/v2/me", ""), ("POST", "/api/v1/games/boule/spins", "")],  # Pin exact routes.
        )
        # Require literal loopback peer and reserved synthetic authority.
        self.assertTrue(all(item["REMOTE_ADDR"] == "127.0.0.1" and item["HTTP_HOST"] == "latency-benchmark.example.invalid" for item in captured))
        # Require no authentication material on the anonymous bootstrap.
        self.assertNotIn("HTTP_AUTHORIZATION", captured[0])
        # Require the bearer on both authenticated requests.
        self.assertEqual([captured[1]["HTTP_AUTHORIZATION"], captured[2]["HTTP_AUTHORIZATION"]], ["Bearer unit-bearer", "Bearer unit-bearer"])
        # Require mutation-only origin and CSRF proof.
        self.assertNotIn("HTTP_ORIGIN", captured[1])
        # Pin the reserved origin on the mutation.
        self.assertEqual(captured[2]["HTTP_ORIGIN"], benchmark.SYNTHETIC_ORIGIN)
        # Pin the synthetic CSRF proof on the mutation.
        self.assertEqual(captured[2]["HTTP_X_CSRF_TOKEN"], "unit-csrf")

    # Prove four complete GET baselines precede every Boule mutation.
    def test_row_collection_orders_all_get_rows_before_boule_controls(self) -> None:
        # Capture every aggregate or control action in order.
        actions = []

        # Return one deterministic valid aggregate row.
        def measure(_client, route_family, concurrency):
            # Retain the measurement identity.
            actions.append(("row", route_family, concurrency))
            # Return one complete positive row.
            return {
                "route_family": route_family,  # Retain the governed family.
                "concurrency": concurrency,  # Retain the governed concurrency.
                "p50_ms": 1.0,  # Supply one positive median.
                "p95_ms": 2.0,  # Supply one ordered tail.
                "throughput_rps": 3.0,  # Supply positive throughput.
                "errors": 0,  # Require no accepted errors.
                "response_bytes": 64,  # Supply a positive aggregate byte count.
            }

        # Record the pre-mutation control boundary.
        def controls(_client):
            # Retain one mutation marker after the reads.
            actions.append(("control", "first"))
            # Return internal-only original control state.
            return {"round_id": "unit"}, 99.0

        # Record the post-cap control boundary.
        def receipt(_client, original_round):
            # Require exact internal round propagation.
            self.assertEqual(original_round, {"round_id": "unit"})
            # Retain the terminal control marker.
            actions.append(("control", "post-cap"))

        # Replace only the row/control seams.
        with mock.patch.object(benchmark, "_measure_row", side_effect=measure), mock.patch.object(
            benchmark, "_boule_controls", side_effect=controls  # Replace the pre-mutation control.
        ), mock.patch.object(benchmark, "_boule_receipt_cap_control", side_effect=receipt):  # Replace the post-cap control.
            # Collect the complete deterministic inventory.
            rows = benchmark._collect_rows(object())
        # Require exactly five routes by four concurrency rows.
        self.assertEqual(len(rows), 20)
        # Locate the first mutation control.
        first_control = actions.index(("control", "first"))
        # Require every preceding action to be one of sixteen GET rows.
        self.assertEqual(first_control, 16)
        # Require every pre-control row to use a read family.
        self.assertTrue(all(action[1] in benchmark.READ_ROUTE_FAMILIES for action in actions[:first_control]))
        # Require the four Boule rows to occur only between the two controls.
        self.assertEqual(actions[first_control + 1 : -1], [("row", "boule_spin", concurrency) for concurrency in benchmark.CONCURRENCY_LEVELS])

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

    # Prove worker failure stops result production and still shuts down the executor.
    def test_scheduler_shuts_down_after_worker_failure(self) -> None:
        # Execute through a deterministic future that fails during collection.
        with self.assertRaisesRegex(RuntimeError, "synthetic worker failure"):
            # Run one bounded row with the failing executor.
            benchmark.rolling_bounded_map(
                lambda index: index,  # Return deterministic successful values.
                8,  # Use the exact warm-up cardinality.
                2,  # Use one governed concurrency.
                executor_factory=_FailingExecutor,  # Inject deferred worker failure.
                wait_function=_fake_wait,  # Release one future per step.
            )
        # Require finally-owned executor cleanup.
        self.assertTrue(_FailingExecutor.last.shutdown_called)
        # Require no pending future to survive cleanup.
        self.assertEqual(_FailingExecutor.last.outstanding, 0)

    # Prove nearest-rank percentiles and exact row accounting.
    def test_measurement_uses_eight_warmups_sixty_four_samples_and_row_wall_time(self) -> None:
        # Build one valid fully framed response.
        body = b'{"ok":true,"data":{"status":"ready"}}'
        # Capture every direct request operation.
        requests = []

        # Provide one deterministic read client.
        class Client:
            # Return one valid response for every exact read.
            def request(self, method, path):
                # Retain the method and path.
                requests.append((method, path))
                # Return exact success framing.
                return benchmark.DirectResponse("200 OK", [("Content-Length", str(len(body)))], body)

        # Track both scheduler invocations.
        scheduler_calls = []

        # Execute operations deterministically without creating workers.
        def bounded(operation, operation_count, concurrency):
            # Retain exact phase cardinality and concurrency.
            scheduler_calls.append((operation_count, concurrency))
            # Execute every operation exactly once.
            results = [operation(index) for index in range(operation_count)]
            # Return the results and exact pending high-water proof.
            return results, concurrency

        # Use thirty-two 1 ms, twenty-nine 2 ms, and three 3 ms samples.
        durations = [1_000_000] * 32 + [2_000_000] * 29 + [3_000_000] * 3
        # Begin the row wall clock at zero.
        ticks = [0]
        # Begin operation timing after the row start.
        current = 10_000_000
        # Append one start/finish pair for every measured operation.
        for duration in durations:
            # Retain the operation start and finish.
            ticks.extend((current, current + duration))
            # Advance to a later monotonic operation start.
            current += 5_000_000
        # End the measured row at exactly one second.
        ticks.append(1_000_000_000)
        # Patch only scheduler and monotonic clock seams.
        with mock.patch.object(benchmark, "rolling_bounded_map", side_effect=bounded), mock.patch.object(
            benchmark.time, "perf_counter_ns", side_effect=ticks  # Supply deterministic time.
        ):  # Enter the deterministic measurement seams.
            # Measure one representative row.
            row = benchmark._measure_row(Client(), "current_user", 4)
        # Require exact warmup then measured scheduling.
        self.assertEqual(scheduler_calls, [(8, 4), (64, 4)])
        # Require exactly seventy-two fixed reads.
        self.assertEqual(requests, [("GET", "/api/v2/me")] * 72)
        # Require nearest-rank median and p95.
        self.assertEqual((row["p50_ms"], row["p95_ms"]), (1.0, 2.0))
        # Require row-wall throughput rather than summed-operation throughput.
        self.assertEqual(row["throughput_rps"], 64.0)
        # Require exact aggregate response bytes.
        self.assertEqual(row["response_bytes"], 64 * len(body))
        # Require an error-free accepted row.
        self.assertEqual(row["errors"], 0)

    # Prove nonpositive wall time and any operation failure produce no accepted row.
    def test_measurement_fails_closed_before_row_or_evidence(self) -> None:
        # Return deterministic scheduler results without invoking operations.
        def bounded(_operation, operation_count, concurrency):
            # Return empty warmup accounting.
            if operation_count == benchmark.WARMUP_OPERATIONS:
                # Return exact warmup cardinality and bounded pending count.
                return [1] * operation_count, concurrency
            # Return synthetic measured tuples.
            return [(1_000_000, 32)] * operation_count, concurrency

        # Force a zero row-wall interval.
        with mock.patch.object(benchmark, "rolling_bounded_map", side_effect=bounded), mock.patch.object(
            benchmark.time, "perf_counter_ns", side_effect=(1, 1)  # Make elapsed time exactly zero.
        ):  # Enter the zero-wall timing seam.
            # Require explicit nonpositive wall rejection.
            with self.assertRaisesRegex(benchmark.RequestLatencyBenchmarkError, "^measured row wall time is invalid$"):
                # Attempt one invalid row.
                benchmark._measure_row(object(), "current_user", 1)
        # Build one operation failure before any complete inventory exists.
        with mock.patch.object(benchmark, "_measure_row", side_effect=benchmark.RequestLatencyBenchmarkError("operation failed")), mock.patch.object(
            benchmark, "_boule_controls"  # Track whether a mutation control was reached.
        ) as boule_controls:  # Enter the pre-mutation failure seam.
            # Require immediate failure with no returned partial evidence.
            with self.assertRaisesRegex(benchmark.RequestLatencyBenchmarkError, "^operation failed$"):
                # Attempt collection.
                benchmark._collect_rows(object())
            # Require no Boule mutation after a failed GET row.
            boule_controls.assert_not_called()

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

    # Prove timed rows require one complete, correctly framed success envelope.
    def test_success_response_requires_dict_data_and_matching_content_length(self) -> None:
        # Build one valid standard success response.
        valid_body = b'{"ok":true,"data":{"status":"ready"}}'
        # Use mixed-case framing to prove case-insensitive header matching.
        valid = benchmark.DirectResponse("200 OK", [("cOnTeNt-LeNgTh", str(len(valid_body)))], valid_body)
        # Require the exact fully consumed byte count.
        self.assertEqual(benchmark._successful_response_bytes(valid), len(valid_body))
        # Build a missing-data success envelope with correct framing.
        missing_data_body = b'{"ok":true}'
        # Build a non-object-data success envelope with correct framing.
        non_dict_data_body = b'{"ok":true,"data":[]}'
        # Build one standard error envelope with correct framing.
        error_body = b'{"ok":false,"error":{"code":"PRIVATE_42"}}'
        # Build malformed JSON with correct framing.
        malformed_body = b'{"ok":true,"data":'
        # Build a non-object JSON value with correct framing.
        non_object_body = b'[]'
        # Enumerate every malformed envelope or framing class with hostile values.
        invalid = (
            # Reject a missing data object.
            benchmark.DirectResponse("200 OK", [("Content-Length", str(len(missing_data_body)))], missing_data_body),
            # Reject a non-object data value.
            benchmark.DirectResponse("200 OK", [("Content-Length", str(len(non_dict_data_body)))], non_dict_data_body),
            # Reject an error envelope on the timed success path.
            benchmark.DirectResponse("200 OK", [("Content-Length", str(len(error_body)))], error_body),
            # Reject malformed JSON without reflecting parser content.
            benchmark.DirectResponse("200 OK", [("Content-Length", str(len(malformed_body)))], malformed_body),
            # Reject a non-object JSON envelope.
            benchmark.DirectResponse("200 OK", [("Content-Length", str(len(non_object_body)))], non_object_body),
            # Reject every non-success status without reflecting its value.
            benchmark.DirectResponse("503 PRIVATE", [("Content-Length", str(len(valid_body)))], valid_body),
            # Reject absent response framing.
            benchmark.DirectResponse("200 OK", [], valid_body),
            # Reject duplicate case-insensitive framing.
            benchmark.DirectResponse("200 OK", [("Content-Length", str(len(valid_body))), ("content-length", str(len(valid_body)))], valid_body),
            # Reject a non-decimal value without reflecting it.
            benchmark.DirectResponse("200 OK", [("Content-Length", "private-42")], valid_body),
            # Reject a mismatched byte count without reflecting it.
            benchmark.DirectResponse("200 OK", [("Content-Length", "999")], valid_body),
        )
        # Require every invalid response to use the same value-free failure.
        for response in invalid:
            # Capture only the fixed benchmark exception.
            with self.assertRaises(benchmark.RequestLatencyBenchmarkError) as raised:
                # Validate the hostile response.
                benchmark._successful_response_bytes(response)
            # Require the fixed diagnostic to contain no body or header value.
            self.assertEqual(str(raised.exception), "request row failed")

    # Prove first, replay, and conflict controls preserve authoritative wallet state.
    def test_boule_controls_preserve_wallet_after_first_settlement(self) -> None:
        # Capture the complete untimed request sequence.
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

        # Provide first settlement, replay, conflict, then current-wallet read.
        class Client:
            # Execute one deterministic response by request order.
            def request(self, method, path, body=None):
                # Retain the exact request for postconditions.
                captured.append((method, path, body))
                # Return the first settled result.
                if len(captured) == 1:
                    # Model the standard first-action envelope.
                    return Response("200 OK", {"ok": True, "data": {"replayed": False, "round": {"round_id": "round"}, "player": {"balance": 99.0}}})
                # Return the exact replayed result and wallet.
                if len(captured) == 2:
                    # Model the standard replay envelope.
                    return Response("200 OK", {"ok": True, "data": {"replayed": True, "round": {"round_id": "round"}, "player": {"balance": 99.0}}})
                # Return the semantic conflict without wallet mutation.
                if len(captured) == 3:
                    # Model the standard conflict envelope.
                    return Response("409 Conflict", {"ok": False, "error": {"code": "CONFLICT"}})
                # Return the authoritative unchanged current wallet.
                return Response("200 OK", {"ok": True, "data": {"player": {"token_balance": 99.0}}})

        # Execute every first/replay/conflict wallet invariant.
        original_round, original_balance = benchmark._boule_controls(Client())
        # Require internal propagation of the exact committed result.
        self.assertEqual((original_round, original_balance), ({"round_id": "round"}, 99.0))
        # Require the exact three mutation controls followed by one wallet read.
        self.assertEqual(
            [(method, path) for method, path, _ in captured],  # Project the fixed request sequence.
            [
                ("POST", "/api/v1/games/boule/spins"),  # Execute the first action.
                ("POST", "/api/v1/games/boule/spins"),  # Execute the identical replay.
                ("POST", "/api/v1/games/boule/spins"),  # Execute the changed-body conflict.
                ("GET", "/api/v2/me"),  # Verify the unchanged wallet.
            ],
        )

    # Prove receipt-cap controls retain replay, conflict, and wallet behavior outside timing.
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
            def request(self, method, path, body=None):
                # Retain the exact request for postconditions.
                captured.append((method, path, body))
                # Return the authoritative wallet before and after the controls.
                if method == "GET":
                    # Model the standard current-user envelope.
                    return Response("200 OK", {"ok": True, "data": {"player": {"token_balance": 88.0}}})
                # Return durable replay for the original body.
                if body["bet"] == "even":
                    # Model the standard successful replay envelope.
                    return Response("200 OK", {"ok": True, "data": {"replayed": True, "round": {"round_id": "original"}, "player": {"balance": 88.0}}})
                # Model the standard conflict envelope for changed content.
                return Response("409 Conflict", {"ok": False, "error": {"code": "CONFLICT"}})

        # Execute both receipt-cap controls outside timed work.
        benchmark._boule_receipt_cap_control(Client(), {"round_id": "original"})
        # Require wallet read, original replay, conflict, then wallet re-read.
        self.assertEqual(
            [(method, path, body) for method, path, body in captured],  # Compare complete controls.
            [
                ("GET", "/api/v2/me", None),  # Capture current post-measurement wallet.
                ("POST", "/api/v1/games/boule/spins", {"request_id": "latency-boule-control", "bet": "even", "stake": 1}),  # Recover the original action.
                ("POST", "/api/v1/games/boule/spins", {"request_id": "latency-boule-control", "bet": "odd", "stake": 1}),  # Prove conflict.
                ("GET", "/api/v2/me", None),  # Recheck the unchanged wallet.
            ],
        )

    # Prove every Boule round or wallet mismatch fails without leaking values.
    def test_boule_control_mismatches_fail_closed(self) -> None:
        # Build one minimal response object.
        class Response:
            # Store one fixed response.
            def __init__(self, status, payload):
                # Retain status for control logic.
                self.status = status
                # Retain the test-owned envelope.
                self._payload = payload

            # Return the test-owned envelope.
            def payload(self):
                # Expose only bounded synthetic data.
                return self._payload

        # Provide a replay whose round and wallet are both wrong.
        class ReplayMismatch:
            # Return deterministic responses by call index.
            def __init__(self):
                # Start before the first request.
                self.index = 0

            # Execute one synthetic response.
            def request(self, method, path, body=None):
                # Advance the request index.
                self.index += 1
                # Return a valid first settlement.
                if self.index == 1:
                    # Model one original settlement.
                    return Response("200 OK", {"ok": True, "data": {"replayed": False, "round": {"round_id": "secret-first"}, "player": {"balance": 99.0}}})
                # Return a mismatched replay.
                return Response("200 OK", {"ok": True, "data": {"replayed": True, "round": {"round_id": "secret-other"}, "player": {"balance": 98.0}}})

        # Require the fixed replay diagnostic.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError) as replay_error:
            # Execute the hostile replay control.
            benchmark._boule_controls(ReplayMismatch())
        # Require no round or wallet value in the error.
        self.assertEqual(str(replay_error.exception), "Boule replay control failed")

        # Provide a valid replay followed by a changed wallet.
        class PostCapMismatch:
            # Track request order.
            def __init__(self):
                # Start before the first wallet read.
                self.index = 0

            # Execute one deterministic post-cap response.
            def request(self, method, path, body=None):
                # Advance request order.
                self.index += 1
                # Return the pre-control current balance.
                if self.index == 1:
                    # Model one current-user projection.
                    return Response("200 OK", {"ok": True, "data": {"player": {"token_balance": 50.0}}})
                # Return exact original replay state.
                if self.index == 2:
                    # Model one durable replay.
                    return Response("200 OK", {"ok": True, "data": {"replayed": True, "round": {"round_id": "original"}, "player": {"balance": 50.0}}})
                # Return the required semantic conflict.
                if self.index == 3:
                    # Model one fixed conflict.
                    return Response("409 Conflict", {"ok": False, "error": {"code": "CONFLICT"}})
                # Return a mutated current wallet.
                return Response("200 OK", {"ok": True, "data": {"player": {"token_balance": 49.0}}})

        # Require the fixed post-cap wallet diagnostic.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError) as cap_error:
            # Execute the hostile post-cap controls.
            benchmark._boule_receipt_cap_control(PostCapMismatch(), {"round_id": "original"})
        # Require no wallet value in the error.
        self.assertEqual(str(cap_error.exception), "Boule receipt-cap wallet control failed")

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
        # Build one duplicate grid entry while preserving cardinality.
        duplicate = self.evidence()
        # Replace the final identity with the first identity.
        duplicate["rows"][-1]["route_family"] = duplicate["rows"][0]["route_family"]
        # Replace its concurrency with the first concurrency.
        duplicate["rows"][-1]["concurrency"] = duplicate["rows"][0]["concurrency"]
        # Require duplicate/missing-grid rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the ambiguous grid.
            benchmark.validate_evidence(duplicate)
        # Build one missing-row packet.
        missing = self.evidence()
        # Remove one governed row.
        missing["rows"].pop()
        # Require wrong-cardinality rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the incomplete packet.
            benchmark.validate_evidence(missing)
        # Replace string provenance with a numeric JSON scalar that has forty digits.
        numeric_source = self.evidence()
        # Preserve the visual hexadecimal width while changing the recursive type.
        numeric_source["source_commit"] = int("1" * 40)
        # Require provenance validation to reject the non-string scalar.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the hostile provenance type.
            benchmark.validate_evidence(numeric_source)
        # Exercise top-level identities with non-string JSON scalar and container types.
        for identity_key, hostile_value in (
            ("schema", 1),  # Replace the schema string with a numeric scalar.
            ("provider", ["json"]),  # Replace the provider string with an unhashable list.
            ("provider", {"name": "json"}),  # Replace the provider with an object.
        ):
            # Build a fresh valid packet before the hostile type replacement.
            hostile_identity = self.evidence()
            # Replace only the selected governed string identity.
            hostile_identity[identity_key] = hostile_value
            # Require one fixed benchmark error rather than a raw type exception.
            with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
                # Validate the hostile top-level identity.
                benchmark.validate_evidence(hostile_identity)
        # Exercise row route identity with non-string JSON values.
        for hostile_route in (1, ["current_user"], {"name": "current_user"}):
            # Build a fresh valid grid before the hostile type replacement.
            hostile_route_packet = self.evidence()
            # Replace only one governed route string.
            hostile_route_packet["rows"][0]["route_family"] = hostile_route
            # Require exact string-domain rejection before set construction.
            with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
                # Validate the hostile route identity.
                benchmark.validate_evidence(hostile_route_packet)
        # Exercise JSON scalar types that compare equal to integer concurrency one.
        for ambiguous_concurrency in (True, 1.0):
            # Build a fresh valid grid before the hostile type replacement.
            hostile_concurrency = self.evidence()
            # Replace only one governed integer with the ambiguous scalar.
            hostile_concurrency["rows"][0]["concurrency"] = ambiguous_concurrency
            # Require exact integer-domain validation before grid equality.
            with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
                # Validate the hostile concurrency type.
                benchmark.validate_evidence(hostile_concurrency)
        # Replace the integer error count with equal-valued JSON scalar variants.
        for ambiguous_errors in (0.0, False):
            # Build a fresh valid packet before the hostile type replacement.
            hostile_errors = self.evidence()
            # Preserve numeric equality while violating the governed recursive type.
            hostile_errors["rows"][0]["errors"] = ambiguous_errors
            # Require a true integer zero rather than Python equality coercion.
            with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
                # Validate the hostile error-count type.
                benchmark.validate_evidence(hostile_errors)
        # Collect every recursive evidence key without rejecting the governed schema name.
        recursive_keys = set(benchmark.EVIDENCE_KEYS) | set(benchmark.ROW_KEYS)
        # Require no identity, auth, request, wager, outcome, path, or exception field.
        for forbidden in ("header", "cookie", "token", "player", "request_id", "wager", "outcome", "exception", "url", "host", "sample"):
            # Reject every forbidden schema key fragment.
            self.assertTrue(all(forbidden not in key.lower() for key in recursive_keys))
        # Serialize the accepted packet for explicit secret-sentinel absence.
        serialized = json.dumps(self.evidence(), sort_keys=True)
        # Require no synthetic private sentinel in accepted output.
        self.assertNotIn("private-sentinel", serialized)
        # Require exact public allowlists.
        self.assertEqual(benchmark.EVIDENCE_KEYS, {"schema", "source_commit", "provider", "rows"})
        # Require exact aggregate-only row fields.
        self.assertEqual(
            benchmark.ROW_KEYS,  # Compare the production row allowlist.
            {"route_family", "concurrency", "p50_ms", "p95_ms", "throughput_rps", "errors", "response_bytes"},  # Pin exact fields.
        )

    # Prove evidence metrics and percentile ordering fail closed.
    def test_evidence_rejects_nonpositive_nonfinite_or_misordered_aggregates(self) -> None:
        # Enumerate every governed positive floating aggregate.
        for key in ("p50_ms", "p95_ms", "throughput_rps"):
            # Enumerate zero, negative, and nonfinite hostile values.
            for value in (0, -1, float("inf"), float("-inf"), float("nan")):
                # Build one fresh valid packet.
                hostile = self.evidence()
                # Replace one aggregate with the hostile value.
                hostile["rows"][0][key] = value
                # Require fixed fail-closed validation.
                with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
                    # Validate the hostile packet.
                    benchmark.validate_evidence(hostile)
        # Build one packet with impossible percentile order.
        misordered = self.evidence()
        # Make the tail lower than the median.
        misordered["rows"][0]["p95_ms"] = 0.5
        # Require explicit percentile-order rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the impossible row.
            benchmark.validate_evidence(misordered)
        # Build one packet with exact positive integers too large for float conversion.
        huge_integer = self.evidence()
        # Retain exact percentile ordering beyond binary floating-point range.
        huge_integer["rows"][0]["p50_ms"] = 10**400
        # Keep the tail exactly one integer unit above the median.
        huge_integer["rows"][0]["p95_ms"] = 10**400 + 1
        # Use the same exact integer domain for throughput validation.
        huge_integer["rows"][0]["throughput_rps"] = 10**400
        # Require successful validation without OverflowError or coercion.
        benchmark.validate_evidence(huge_integer)
        # Build one packet whose integer percentile order is hidden by float conversion.
        precise_misorder = self.evidence()
        # Set the median one exact integer above the binary-float precision boundary.
        precise_misorder["rows"][0]["p50_ms"] = 2**53 + 1
        # Set the tail lower by one while both values coerce to the same float.
        precise_misorder["rows"][0]["p95_ms"] = 2**53
        # Require direct exact-number ordering to reject the row.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the precision-sensitive percentile order.
            benchmark.validate_evidence(precise_misorder)
        # Build one packet with zero returned bytes.
        empty = self.evidence()
        # Replace the positive aggregate byte total.
        empty["rows"][0]["response_bytes"] = 0
        # Require empty-response rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the empty aggregate.
            benchmark.validate_evidence(empty)
        # Build one packet with a hidden accepted error.
        failed = self.evidence()
        # Mark one row as failed.
        failed["rows"][0]["errors"] = 1
        # Require nonzero-error rejection.
        with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
            # Validate the failed aggregate.
            benchmark.validate_evidence(failed)

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

    # Prove checkout provenance is authoritative and caller spoofing fails before setup.
    def test_checkout_provenance_requires_exact_head(self) -> None:
        # Select one exact synthetic checkout identity.
        exact_head = "b" * 40
        # Return one successful bounded Git result.
        completed = subprocess.CompletedProcess(["git"], 0, exact_head + "\n", "")
        # Patch only the read-only Git query.
        with mock.patch.object(benchmark.subprocess, "run", return_value=completed) as run_git:
            # Require exact normalized checkout identity.
            self.assertEqual(benchmark._checkout_head(), exact_head)
        # Require the bounded exact Git command and checkout.
        run_git.assert_called_once_with(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True, timeout=10)
        # Reject a mismatched caller commit before output or provider work.
        with mock.patch.object(benchmark, "_checkout_head", return_value=exact_head), mock.patch.object(
            benchmark, "resolve_output_path"  # Track forbidden output inspection.
        ) as resolve_output:  # Enter the provenance mismatch seam.
            # Require one fixed mismatch failure.
            with self.assertRaisesRegex(benchmark.RequestLatencyBenchmarkError, "^source commit does not match checkout$"):
                # Attempt one spoofed benchmark identity.
                benchmark.run_benchmark("json", "c" * 40, "private-output")
            # Prove the output path was never inspected.
            resolve_output.assert_not_called()
        # Reject a numeric forty-digit caller value before checkout resolution.
        with mock.patch.object(benchmark, "_checkout_head") as checkout_head:
            # Require the exact invalid-source diagnostic.
            with self.assertRaisesRegex(benchmark.RequestLatencyBenchmarkError, "^source commit is invalid$"):
                # Attempt to coerce numeric provenance through the public boundary.
                benchmark.run_benchmark("json", int("1" * 40), "private-output")
            # Prove no checkout, provider, or output work followed the type failure.
            checkout_head.assert_not_called()
        # Enumerate timeout and process-launch provenance failures containing sentinels.
        failures = (
            subprocess.TimeoutExpired(["git", "private-sentinel"], 1, output="private-sentinel"),  # Inject timeout detail.
            OSError("private-sentinel"),  # Inject operating-system detail.
        )
        # Require one fixed value-free diagnostic for each process failure.
        for failure in failures:
            # Inject the hostile process failure.
            with mock.patch.object(benchmark.subprocess, "run", side_effect=failure):
                # Capture only the fixed benchmark error.
                with self.assertRaises(benchmark.RequestLatencyBenchmarkError) as raised:
                    # Resolve checkout identity.
                    benchmark._checkout_head()
                # Require no command or OS detail.
                self.assertEqual(str(raised.exception), "request-latency source commit is unavailable")

    # Prove the central runner accepts absent/equal hosted SHA and rejects all other assertions.
    def test_central_runner_provenance_matches_checkout_head(self) -> None:
        # Parse the central runner without importing its broad test harness.
        central_source = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Build the central runner syntax tree.
        central_tree = ast.parse(central_source)
        # Select only the request-latency provenance helper.
        function = next(
            node  # Return the exact helper definition.
            for node in central_tree.body  # Inspect top-level definitions only.
            if isinstance(node, ast.FunctionDef) and node.name == "request_latency_source_commit"  # Select the helper.
        )
        # Build an isolated one-function module.
        isolated = ast.Module(body=[function], type_ignores=[])
        # Fill location metadata for compilation.
        ast.fix_missing_locations(isolated)
        # Supply only the helper's standard-library globals.
        namespace = {"os": os, "re": re, "subprocess": subprocess, "ROOT": ROOT}
        # Compile and load only the selected helper.
        exec(compile(isolated, str(ROOT / "tests" / "run_tests.py"), "exec"), namespace)
        # Retain the isolated callable.
        resolver = namespace["request_latency_source_commit"]
        # Select one exact synthetic checkout identity.
        exact_head = "e" * 40
        # Return one successful Git result.
        completed = subprocess.CompletedProcess(["git"], 0, exact_head + "\n", "")
        # Prove absent hosted identity falls back to checkout HEAD.
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(subprocess, "run", return_value=completed):
            # Require exact fallback provenance.
            self.assertEqual(resolver(), exact_head)
        # Prove an equal hosted identity is accepted.
        with mock.patch.dict(os.environ, {"GITHUB_SHA": exact_head.upper()}, clear=True), mock.patch.object(
            subprocess, "run", return_value=completed  # Return the exact checkout identity.
        ):  # Enter the matching hosted-provenance environment.
            # Require normalized equality.
            self.assertEqual(resolver(), exact_head)
        # Reject one malformed and one valid-but-stale hosted identity.
        for hosted in ("malformed-private", "f" * 40):
            # Isolate one hostile hosted assertion.
            with mock.patch.dict(os.environ, {"GITHUB_SHA": hosted}, clear=True), mock.patch.object(
                subprocess, "run", return_value=completed  # Keep checkout identity stable.
            ):  # Enter one hostile hosted-provenance environment.
                # Require the fixed mismatch diagnostic.
                with self.assertRaisesRegex(AssertionError, "^request-latency hosted source commit does not match checkout$"):
                    # Resolve the hostile assertion.
                    resolver()

    # Prove child setup applies rate policy and removes every MySQL pool override.
    def test_child_environment_uses_fixed_rate_and_default_pool_settings(self) -> None:
        # Allocate one external runtime root.
        with tempfile.TemporaryDirectory(prefix="request-latency-env-") as temporary:
            # Supply hostile optional pool overrides only inside the patch.
            overrides = {
                "CASINO_MYSQL_POOL_SIZE": "16",  # Override capacity hostilely.
                "CASINO_MYSQL_POOL_WAIT_MS": "10000",  # Override wait hostilely.
                "CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS": "60",  # Override connect timeout hostilely.
            }
            # Restore the caller environment after configuration proof.
            with mock.patch.dict(os.environ, overrides, clear=False):
                # Configure the JSON child without importing Casino runtime packages.
                benchmark._configure_child_environment("json", Path(temporary))
                # Require the exact test-only request allowance.
                self.assertEqual(os.environ["CASINO_RATE_LIMIT_REQUESTS"], "10000")
                # Pin the complete current pool-control contract read by mysql_pool.py.
                self.assertEqual(
                    benchmark.MYSQL_POOL_OVERRIDE_KEYS,  # Compare production scrub keys.
                    (  # Pin the exact ordered pool controls.
                        "CASINO_MYSQL_POOL_SIZE",  # Pin capacity control.
                        "CASINO_MYSQL_POOL_WAIT_MS",  # Pin wait control.
                        "CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS",  # Pin connector deadline control.
                    ),
                )
                # Require every optional pool override to be absent.
                self.assertTrue(all(key not in os.environ for key in benchmark.MYSQL_POOL_OVERRIDE_KEYS))

    # Prove the subprocess environment uses defaults and withholds DDL capabilities.
    def test_provider_child_environment_is_minimized_and_launch_failures_are_private(self) -> None:
        # Allocate one caller-owned external destination.
        with tempfile.TemporaryDirectory(prefix="request-latency-launch-") as temporary:
            # Resolve one external output file.
            output = Path(temporary) / "evidence.json"
            # Supply hostile pool, administrator, migrator, and runtime values.
            hostile = {
                "CASINO_MYSQL_POOL_SIZE": "private-pool",  # Supply a hostile pool capacity.
                "CASINO_MYSQL_POOL_WAIT_MS": "private-wait",  # Supply a hostile wait.
                "CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS": "private-timeout",  # Supply a hostile connector deadline.
                "CASINO_MYSQL_DISPOSABLE_TEST": "1",  # Mark the synthetic service disposable.
                "CASINO_MYSQL_TEST_ADMIN_HOST": "127.0.0.1",  # Supply a retained guard fact.
                "CASINO_MYSQL_TEST_ADMIN_PORT": "3307",  # Supply a retained admin port fact.
                "CASINO_MYSQL_TEST_ADMIN_USER": "private-admin",  # Supply a forbidden admin identity.
                "CASINO_MYSQL_TEST_ADMIN_PASSWORD": "private-admin-secret",  # Supply a forbidden admin secret.
                "CASINO_MYSQL_MIGRATION_HOST": "127.0.0.1",  # Supply a retained migration host fact.
                "CASINO_MYSQL_MIGRATION_PORT": "3307",  # Supply a retained migration port fact.
                "CASINO_MYSQL_MIGRATION_USER": "private-migrator",  # Supply a forbidden migrator identity.
                "CASINO_MYSQL_MIGRATION_PASSWORD": "private-migrator-secret",  # Supply a forbidden migrator secret.
                "CASINO_MYSQL_MIGRATION_DATABASE": "private-migration-db",  # Supply a forbidden migrator target.
                "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY": "private-binding",  # Supply a forbidden binding key.
                "CASINO_MYSQL_HOST": "127.0.0.1",  # Supply the retained runtime host.
                "CASINO_MYSQL_PORT": "3307",  # Supply the retained runtime port.
                "CASINO_MYSQL_USER": "runtime-user",  # Supply the retained DML identity.
                "CASINO_MYSQL_PASSWORD": "runtime-secret",  # Supply the retained DML secret.
                "CASINO_MYSQL_DATABASE": "runtime-db",  # Supply the retained runtime database.
            }
            # Return one successful child result without launching a process.
            completed = subprocess.CompletedProcess(["child"], 0, "", "")
            # Patch the parent environment and process seam.
            with mock.patch.dict(os.environ, hostile, clear=True), mock.patch.object(
                benchmark.subprocess, "run", return_value=completed  # Capture without launching.
            ) as run_child:  # Enter the captured child-launch seam.
                # Launch only through the captured fake.
                benchmark.run_provider_subprocess("mysql", "d" * 40, output)
            # Read the configured child environment without printing values.
            child_environment = run_child.call_args.kwargs["env"]
            # Require all actual pool controls absent.
            self.assertTrue(all(key not in child_environment for key in benchmark.MYSQL_POOL_OVERRIDE_KEYS))
            # Require all administrator and migrator capabilities absent.
            self.assertTrue(all(key not in child_environment for key in benchmark.MYSQL_CHILD_CAPABILITY_KEYS))
            # Require only guarded endpoint facts and disposable marker from privileged roles.
            self.assertEqual(
                {key for key in child_environment if key.startswith("CASINO_MYSQL_TEST_ADMIN_")},  # Project admin role keys.
                {"CASINO_MYSQL_TEST_ADMIN_HOST", "CASINO_MYSQL_TEST_ADMIN_PORT"},  # Permit endpoint facts only.
            )
            # Require only guarded host and port facts from the migration role.
            self.assertEqual(
                {key for key in child_environment if key.startswith("CASINO_MYSQL_MIGRATION_")},  # Project migration keys.
                {"CASINO_MYSQL_MIGRATION_HOST", "CASINO_MYSQL_MIGRATION_PORT"},  # Permit endpoint facts only.
            )
            # Require the complete runtime DML tuple plus disposable marker.
            self.assertTrue(
                {
                    "CASINO_MYSQL_DISPOSABLE_TEST",  # Retain the explicit safety marker.
                    "CASINO_MYSQL_HOST",  # Retain the runtime host.
                    "CASINO_MYSQL_PORT",  # Retain the runtime port.
                    "CASINO_MYSQL_USER",  # Retain the DML identity.
                    "CASINO_MYSQL_PASSWORD",  # Retain the DML secret.
                    "CASINO_MYSQL_DATABASE",  # Retain the runtime database.
                }.issubset(child_environment)  # Require the full runtime tuple.
            )
            # Enumerate timeout and launch failures that carry private command text.
            failures = (
                subprocess.TimeoutExpired(["private-command", str(output)], 1, output="private-output"),  # Inject timeout detail.
                OSError("private-launch"),  # Inject launch detail.
            )
            # Require one fixed value-free launcher error for both failure classes.
            for failure in failures:
                # Patch one hostile process failure.
                with mock.patch.object(benchmark.subprocess, "run", side_effect=failure):
                    # Capture only the fixed benchmark diagnostic.
                    with self.assertRaises(benchmark.RequestLatencyBenchmarkError) as raised:
                        # Attempt the bounded child launch.
                        benchmark.run_provider_subprocess("json", "d" * 40, output)
                    # Require no command, output path, or OS text.
                    self.assertEqual(str(raised.exception), "request-latency benchmark child failed")

    # Prove MySQL refuses non-disposable, remote, split, or malformed endpoints pre-import.
    def test_mysql_child_requires_disposable_matching_loopback_before_wsgi_import(self) -> None:
        # Allocate one external runtime root.
        with tempfile.TemporaryDirectory(prefix="request-latency-mysql-guard-") as temporary:
            # Build one valid endpoint-fact environment with no credentials.
            valid = {
                "CASINO_MYSQL_DISPOSABLE_TEST": "1",  # Authorize only disposable testing.
                "CASINO_MYSQL_HOST": "127.0.0.1",  # Pin the runtime host.
                "CASINO_MYSQL_PORT": "3307",  # Pin the runtime port.
                "CASINO_MYSQL_MIGRATION_HOST": "127.0.0.1",  # Pin the migration host.
                "CASINO_MYSQL_MIGRATION_PORT": "3307",  # Pin the migration port.
                "CASINO_MYSQL_TEST_ADMIN_HOST": "127.0.0.1",  # Pin the admin host.
                "CASINO_MYSQL_TEST_ADMIN_PORT": "3307",  # Pin the admin port.
            }
            # Configure the exact accepted guarded tuple.
            with mock.patch.dict(os.environ, valid, clear=True):
                # Require successful pre-import configuration.
                benchmark._configure_child_environment("mysql", Path(temporary))
                # Require every privileged capability absent after configuration.
                self.assertTrue(all(key not in os.environ for key in benchmark.MYSQL_CHILD_CAPABILITY_KEYS))
            # Enumerate missing marker, remote host, split port, and malformed port cases.
            hostile_cases = (
                {**valid, "CASINO_MYSQL_DISPOSABLE_TEST": "0"},  # Remove disposable authorization.
                {**valid, "CASINO_MYSQL_HOST": "localhost"},  # Reject hostname aliases.
                {**valid, "CASINO_MYSQL_PORT": "3308"},  # Reject split service tuples.
                {**valid, "CASINO_MYSQL_TEST_ADMIN_PORT": "private-port"},  # Reject malformed ports.
            )
            # Require every hostile tuple to fail before child roots are configured.
            for hostile in hostile_cases:
                # Isolate the hostile environment.
                with mock.patch.dict(os.environ, hostile, clear=True):
                    # Require fixed fail-closed refusal.
                    with self.assertRaises(benchmark.RequestLatencyBenchmarkError):
                        # Attempt MySQL child configuration.
                        benchmark._configure_child_environment("mysql", Path(temporary))
                    # Prove runtime state was not selected after refusal.
                    self.assertNotIn("CASINO_DATA_DIR", os.environ)

    # Prove provider cleanup invokes only the provider-owned lifecycle hook.
    def test_provider_cleanup_closes_optional_pool(self) -> None:
        # Track exact close calls.
        closed = []

        # Provide one provider-owned cleanup hook.
        class Provider:
            # Close one synthetic pool.
            def close_pool(self):
                # Retain exactly one cleanup event.
                closed.append("closed")

        # Provide the active-provider accessor.
        class Storage:
            # Return the same synthetic provider.
            @staticmethod
            def get_storage_provider():  # Resolve the pool-owning provider.
                # Expose the provider only to cleanup.
                return Provider()

        # Execute focused provider cleanup.
        benchmark._close_active_provider(Storage)
        # Require exactly one lifecycle call.
        self.assertEqual(closed, ["closed"])
        # Provide a JSON-like provider without a pool hook.
        class JsonStorage:
            # Return one hook-free object.
            @staticmethod
            def get_storage_provider():  # Resolve the hook-free provider.
                # Model a provider with no lifecycle.
                return object()

        # Require hook-free cleanup to remain a no-op.
        benchmark._close_active_provider(JsonStorage)
        # Require no additional cleanup event.
        self.assertEqual(closed, ["closed"])

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
        # Extract the exact provenance helper source boundary.
        provenance_start = source.index("def request_latency_source_commit():")
        # Stop at the next provider runner.
        provenance_end = source.index("def run_request_latency_provider(", provenance_start)
        # Retain only the provenance helper.
        provenance = source[provenance_start:provenance_end]
        # Require checkout HEAD resolution on every call.
        self.assertIn("['git','rev-parse','HEAD']", provenance)
        # Require a present hosted SHA to equal checkout HEAD.
        self.assertIn("hosted_sha!=local_sha", provenance)
        # Reject the old caller-trusting hosted early return.
        self.assertNotIn("return hosted_sha", provenance)
        # Require fixed timeout and launch failure handling.
        self.assertIn("except (subprocess.TimeoutExpired,OSError):", provenance)

    # Prove the terminology gate accepts only an owned direct formatter delegation or an inline token mark.
    def test_token_terminology_money_delegation_is_exact(self) -> None:
        # Resolve the standalone validator from this exact checkout.
        validator_path = ROOT / "scripts" / "validate_token_terminology.py"
        # Build an isolated import specification without changing package state.
        validator_spec = importlib.util.spec_from_file_location("token_terminology_task_555", validator_path)
        # Fail clearly if the standard loader cannot describe the repository script.
        self.assertIsNotNone(validator_spec)
        # Fail clearly if the import specification has no executable loader.
        self.assertIsNotNone(validator_spec.loader)
        # Create the isolated validator module from the checked specification.
        validator = importlib.util.module_from_spec(validator_spec)
        # Execute the validator definitions without invoking its command-line entry point.
        validator_spec.loader.exec_module(validator)
        # Allocate disposable formatter sources so production files remain untouched.
        with tempfile.TemporaryDirectory() as temp_dir:
            # Resolve the temporary repository root through a portable path.
            temporary_root = Path(temp_dir)
            # Create the exact shared-formatter directory expected by the validator.
            core_dir = temporary_root / "web" / "core"
            # Materialize the nested directory before writing controlled sources.
            core_dir.mkdir(parents=True)
            # Keep the authoritative i18n formatter token-marked in every scenario.
            (core_dir / "i18n.js").write_text(f"export const formatMoney = amount => `{validator.TOKEN_MARK}${{amount}}`;\n", encoding="utf-8")
            # Point only this imported validator at the disposable source tree.
            with mock.patch.object(validator, "ROOT", temporary_root):
                # Write the exact direct delegation used by the current shared helper.
                (core_dir / "ui.js").write_text("export const money = amount => formatMoney(amount);\n", encoding="utf-8")
                # Accept argument-preserving delegation because the i18n formatter owns the mark.
                self.assertEqual(validator.check_required_token_mark(), [])
                # Write an unrelated formatter reference that must not satisfy the helper contract.
                (core_dir / "ui.js").write_text("import { formatMoney } from './i18n.js';\nexport const money = amount => amount;\n", encoding="utf-8")
                # Require the fixed path-only diagnostic instead of accepting a substring false positive.
                self.assertEqual(validator.check_required_token_mark(), ["web/core/ui.js: money() must prefix amounts with ◈ or directly delegate to formatMoney()"])
                # Write a self-contained inline token-mark formatter as the supported legacy alternative.
                (core_dir / "ui.js").write_text(f"export const money = amount => `{validator.TOKEN_MARK}${{amount}}`;\n", encoding="utf-8")
                # Preserve compatibility with an inline token-mark helper.
                self.assertEqual(validator.check_required_token_mark(), [])

    # Prove the current governance allocations and module revisions remain exact.
    def test_governance_allocation_is_unique_and_narrow(self) -> None:
        # Parse the canonical requirement source.
        requirements = json.loads((ROOT / "docs" / "requirements" / "requirements.json").read_text(encoding="utf-8"))["requirements"]
        # Require accepted atomic-state, MySQL-pool, conversion, teardown, analytics, wager, and settings slices to total exactly 1065 permanent rows.
        self.assertEqual(len(requirements), 1069)
        # Keep the historical contributor reservation out of the canonical registry so it is never reused.
        self.assertEqual([row for row in requirements if row.get("id") == "TEST-144"], [])
        # Bind every new permanent allocation to its accepted owning module.
        aggregate_allocations = {
            "BINGO-026": "Bingo",  # Preserve the accepted economics owner.
            "ADMIN-029": "Admin",  # Preserve the diagnostic owner.
            "TEST-145": "Tests",  # Preserve the diagnostic evidence owner.
            "ADMIN-030": "Admin",  # Preserve the economics owner.
            "TEST-146": "Tests",  # Preserve the economics evidence owner.
            "SESSION-009": "Core",  # Preserve the session-policy owner.
            "ADMIN-031": "Admin",  # Preserve the Admin session-policy owner.
            "TEST-150": "Tests",  # Preserve the policy evidence owner.
            "LEDGER-031": "Ledger",  # Preserve wallet-timing ownership.
            "TEST-151": "Tests",  # Preserve wallet-timing evidence ownership.
            "API-003": "Contracts",  # Preserve API-doc ownership.
            "TEST-152": "Tests",  # Preserve API-doc evidence ownership.
            "CORE-032": "Application",  # Preserve scoped native transport ownership.
            "AUTH-019": "Core",  # Preserve native bearer/CSRF ownership.
            "SEC-016": "Core",  # Preserve native origin and link ownership.
            "SESSION-013": "Core",  # Preserve native lifecycle ownership.
            "TEST-172": "Tests",  # Preserve mobile-core evidence ownership.
            "STORAGE-013": "Storage",  # Bind immutable action lifecycle claims to storage.
            "MYSQL-009": "MySQL",  # Bind schema-four claim and receipt ownership.
            "TEST-174": "Tests",  # Bind provider parity and migration evidence without reusing TEST-173.
            "STORAGE-014": "Storage",  # Bind corrupt wallet refusal and forensic preservation to storage.
            "TEST-177": "Tests",  # Bind provider-parity wallet corruption recovery evidence.
            "I18N-012": "Application",  # Bind complete Russian lobby-card copy to the catalog.
            "TEST-178": "Tests",  # Bind static and rendered Russian catalog evidence.
            "TOOL-014": "Tooling",  # Bind completed-issue rollout linkage enforcement.
            "TEST-179": "Tests",  # Bind deterministic rollout-link evidence and workflow scope.
            "TOOL-016": "Tooling",  # Bind canonical-inventory and dead-export cleanup governance.
            "TEST-181": "Tests",  # Bind deterministic dead-artifact absence evidence.
            "I18N-013": "Application",  # Bind actionable cumulative Roulette diagnostics to i18n state.
            "TEST-182": "Tests",  # Bind deterministic missing-key diagnostic evidence.
            "TOOL-017": "Tooling",  # Bind fail-closed long-suite and release-candidate compute filtering.
            "TEST-183": "Tests",  # Bind exact context and PR-only optimization evidence.
            "TOOL-018": "Tooling",  # Bind generic descriptor equality and exact-base monotonic version governance.
            "TEST-184": "Tests",  # Bind helper, downgrade, and shared-pin-removal evidence.
            "TEST-185": "Tests",  # Bind five dedicated Browser cases and per-game suite ownership.
            "CORE-033": "Application",  # Bind one escape-by-default browser markup helper.
            "SEC-017": "Core",  # Bind complete Admin migration and monotonic raw-write prevention.
            "TEST-186": "Tests",  # Bind hostile-value, composition, baseline, and Browser evidence.
            "I18N-014": "Application",  # Bind resource-owned shared copy and installed-locale game fallbacks.
            "TEST-187": "Tests",  # Bind complete adapter, resource-parity, and rendered localization evidence.
            "LEDGER-035": "Core",  # Bind Guest Trial wallet teardown to one terminal ledger movement.
            "TEST-188": "Tests",  # Bind replay, reconstruction, and economics-isolation evidence.
            "CW-006": "Casino War",  # Bind committed-marker and terminal-phase publication to the atomic state helper.
            "TEST-189": "Tests",  # Bind the real two-process Casino War stale-state rendezvous evidence.
            "CW-007": "Casino War",  # Bind round and decision preparation plus bounded rollback to atomic state.
            "TEST-199": "Tests",  # Bind two-process preparation, contention, rollback, and lost-response evidence.
            "STORAGE-015": "Core",  # Bind explicit provider-owned wallet residue normalization.
            "LEDGER-036": "Core",  # Bind every durable wallet writer to canonical integer cents.
            "TOOL-019": "Tooling",  # Bind the packaged check/apply operator command.
            "TEST-190": "Tests",  # Bind JSON and MySQL normalization and rollback evidence.
            "KENO-028": "Keno",  # Bind Keno pending-draw commit and finalization to atomic player state.
            "TEST-191": "Tests",  # Bind the real two-process Keno stale-state rendezvous evidence.
            "KENO-029": "Keno",  # Bind Keno ticket purchase and refund to atomic player state.
            "TEST-197": "Tests",  # Bind ticket settlement, rollback, and sibling-state evidence.
            "BAC-027": "Baccarat",  # Bind Baccarat pending-coup commit and finalization to atomic player state.
            "TEST-192": "Tests",  # Bind the real two-process Baccarat stale-state rendezvous evidence.
            "BAC-028": "Baccarat",  # Bind bet placement, refund, and settings to atomic player state.
            "TEST-198": "Tests",  # Bind real wager settlement, rollback, and contention evidence.
            "BJ-033": "Blackjack",  # Bind Blackjack round preparation, transitions, rollback, and finalization to atomic player state.
            "TEST-196": "Tests",  # Bind real two-process Blackjack sibling and same-round serialization evidence.
            "BJ-034": "Blackjack",  # Bind Blackjack settings to the provider-owned latest document.
            "TEST-200": "Tests",  # Bind real stale settings, sibling, disjoint-field, and active-round races.
            "MHVP-007": "Multi-Hand Video Poker",  # Bind all round-state publications to provider-current callbacks.
            "TEST-201": "Tests",  # Bind real sibling and hold/draw process ordering evidence.
            "ROU-073": "Roulette",  # Bind every Roulette state publication to provider-current callbacks.
            "TEST-202": "Tests",  # Bind real Roulette ordering, rollback, and recovery evidence.
            "BINGO-028": "Bingo",  # Bind every Bingo action-state publication to provider-current callbacks.
            "TEST-203": "Tests",  # Bind real Bingo ordering, rollback, and recovery evidence.
            "CS-007": "Caribbean Stud",  # Bind every Caribbean Stud action-state publication to provider-current callbacks.
            "TEST-204": "Tests",  # Bind real Caribbean Stud ordering, rollback, and recovery evidence.
            "FOURCP-003": "Four Card Poker",  # Bind every Four Card Poker action-state publication to provider-current callbacks.
            "TEST-205": "Tests",  # Bind real Four Card Poker ordering, rollback, and recovery evidence.
            "TCP-006": "Three Card Poker",  # Bind every Three Card Poker action-state publication to provider-current callbacks.
            "TEST-206": "Tests",  # Bind real Three Card Poker ordering, rollback, and recovery evidence.
            "CH-007": "Casino Hold'em",  # Bind every Casino Hold'em action-state publication to provider-current callbacks.
            "TEST-207": "Tests",  # Bind real Casino Hold'em ordering, rollback, and recovery evidence.
            "PGP-007": "Pai Gow Poker",  # Bind every Pai Gow Poker action-state publication to provider-current callbacks.
            "TEST-208": "Tests",  # Bind real Pai Gow Poker ordering, rollback, and recovery evidence.
            "THPT-007": "Texas Hold'em Practice Table",  # Bind every practice-table action-state publication to provider-current callbacks.
            "TEST-209": "Tests",  # Bind real practice-table ordering, rollback, and recovery evidence.
            "CRAPS-006": "Craps",  # Bind every Craps action-state publication to provider-current callbacks.
            "TEST-210": "Tests",  # Bind real Craps ordering, rollback, and recovery evidence.
            "AB-006": "Andar Bahar",  # Bind every Andar Bahar action-state publication to provider-current callbacks.
            "TEST-211": "Tests",  # Bind real Andar Bahar ordering, rollback, and recovery evidence.
            "OU7-007": "Over/Under 7",  # Bind settled-history publication to provider-current callbacks.
            "TEST-212": "Tests",  # Bind real Over/Under 7 ordering, sibling, and recovery evidence.
            "BIG-SIX-007": "Big Six Wheel",  # Bind settled-history publication to provider-current callbacks.
            "TEST-213": "Tests",  # Bind real Big Six Wheel ordering and sibling-state evidence.
            "CAA-006": "Crown and Anchor",  # Bind settled-history publication to provider-current callbacks.
            "TEST-214": "Tests",  # Bind real Crown and Anchor ordering and sibling-state evidence.
            "FAN-TAN-006": "Fan-Tan",  # Bind settled-history publication to provider-current callbacks.
            "TEST-215": "Tests",  # Bind real Fan-Tan ordering, sibling, and recovery evidence.
            "AD-006": "Acey-Deucey",  # Bind every round-state publication to provider-current callbacks.
            "TEST-216": "Tests",  # Bind real Acey-Deucey ordering, sibling, and recovery evidence.
            "CHUCK-006": "Chuck-a-Luck",  # Bind settled-round publication to provider-current callbacks.
            "TEST-217": "Tests",  # Bind real Chuck-a-Luck ordering, sibling, and recovery evidence.
            "DWVP-006": "Deuces Wild Video Poker",  # Bind round, hold, replay, and recovery publication to provider-current callbacks.
            "TEST-218": "Tests",  # Bind real Deuces Wild terminal ordering, sibling, and recovery evidence.
            "DBVP-003": "Double Bonus Video Poker",  # Bind deal, draw, replay, and recovery publication to provider-current callbacks.
            "TEST-219": "Tests",  # Bind real Double Bonus terminal ordering, sibling, and recovery evidence.
            "TEST-220": "Tests",  # Bind repeated capacity-two debit and exact lease-return evidence.
            "DT-006": "Dragon Tiger",  # Bind shoe, recovery, terminal, and rollback publication to provider-current callbacks.
            "TEST-221": "Tests",  # Bind real Dragon Tiger terminal ordering, sibling, and recovery evidence.
            "JP-006": "Joker Poker",  # Bind deal, hold, draw, replay, and recovery publication to provider-current callbacks.
            "TEST-222": "Tests",  # Bind real Joker Poker terminal ordering, sibling, and recovery evidence.
            "HILO-006": "Hi-Lo",  # Bind deal, guess, replay, and recovery publication to provider-current callbacks.
            "TEST-223": "Tests",  # Bind real Hi-Lo terminal ordering, sibling, and recovery evidence.
            "JOBVP-006": "Jacks or Better Video Poker",  # Bind deal, hold, draw, replay, and recovery publication to provider-current callbacks.
            "TEST-224": "Tests",  # Bind real Jacks-or-Better terminal ordering, sibling, and recovery evidence.
            "LIR-006": "Let It Ride",  # Bind staged decisions, replay, recovery, markers, and rollback to provider-current callbacks.
            "TEST-225": "Tests",  # Bind real Let It Ride terminal ordering, sibling, and recovery evidence.
            "MSTUD-003": "Mississippi Stud",  # Bind deals, streets, recovery, settlement, archive, and rollback to provider-current callbacks.
            "TEST-226": "Tests",  # Bind real Mississippi Stud terminal ordering, sibling, and recovery evidence.
            "PLINKO-006": "Plinko",  # Bind drop preparation, recovery markers, receipts, history, and rollback to provider-current callbacks.
            "TEST-227": "Tests",  # Bind real Plinko terminal ordering, sibling, and recovery evidence.
            "RD-006": "Red Dog",  # Bind opening, decisions, recovery markers, requests, and rollback to provider-current callbacks.
            "TEST-228": "Tests",  # Bind real Red Dog terminal ordering, sibling, and recovery evidence.
            "SCRATCH-006": "Scratch Cards",  # Bind private card, reveal, settlement, replay, and cleanup state to provider-current callbacks.
            "TEST-229": "Tests",  # Bind real Scratch Cards reveal ordering, sibling, and cleanup evidence.
            "SIC-BO-006": "Sic Bo",  # Bind private dice, recovery markers, settlement, history, and cleanup state to provider-current callbacks.
            "TEST-230": "Tests",  # Bind real Sic Bo preparation ordering, sibling, and cleanup evidence.
            "TEST-175": "Tests",  # Bind the complete catalog economics registry without changing game math.
            "TOKEN-007": "Application",  # Bind wallet UI ordering to the shell.
            "I18N-011": "Application",  # Bind shared localized copy to the shell.
            "AUTO-015": "Autoplay",  # Bind lifecycle reconciliation to the control plane.
            "BINGO-027": "Bingo",  # Bind call and reset semantics to Bingo.
            "PWA-003": "Application",  # Bind update application to the shell.
            "UX-025": "Application",  # Bind shared accessibility behavior to the shell.
            "TOOL-012": "Tooling",  # Bind ticket closure enforcement to tooling.
            "TEST-153": "Tests",  # Bind consolidated regression evidence to tests.
            "UX-026": "Application",  # Bind viewport containment and layout telemetry to the shell.
            "UX-027": "Application",  # Bind action render stability to the shell.
            "TEST-154": "Tests",  # Bind containment-walk evidence to tests.
            "TEST-155": "Tests",  # Bind action-stability evidence to tests.
            "SEC-015": "Core",  # Bind adjustable request policy to the security boundary.
            "ADMIN-032": "Admin",  # Bind owner rate controls to Admin.
            "TEST-156": "Tests",  # Bind rate-policy and deferred-scroll evidence to tests.
            "LEDGER-032": "Ledger",  # Bind all catalog game money to one exactly-once interface.
            "GAMECORE-004": "Core",  # Bind legacy game call shapes to the shared settlement adapter.
            "TEST-157": "Tests",  # Bind the catalog-derived direct-ledger prevention gate.
            "AUDIO-010": "Audio",  # Bind silent defaults and explicit owner overrides to Audio.
            "ADMIN-033": "Admin",  # Bind ordinary-Admin delegation to the dedicated owner workspace.
            "ADMIN-034": "Admin",  # Bind session policy completion to the responsive Admin surface.
            "ADMIN-035": "Admin",  # Bind explicitly confirmed Admin-assisted guest conversion.
            "AUTH-015": "Core",  # Bind enrollment readiness and fail-closed live enablement.
            "AUTH-016": "Core",  # Bind the read-only launch readiness aggregate.
            "OAUTH-011": "Core",  # Bind provider readiness to secret-safe diagnostics.
            "USER-008": "Application",  # Bind personal sound to explicit opt-in behavior.
            "USER-009": "Application",  # Bind My Settings and self-history to the shell.
            "SESSION-010": "Core",  # Bind durable session-policy provenance.
            "SESSION-011": "Core",  # Bind idle enforcement and warning controls.
            "SESSION-012": "Application",  # Bind the safe browser session-warning descriptor.
            "RESET-004": "Core",  # Bind public v2 recovery routes and browser flow.
            "CONVERT-003": "Application",  # Bind the guest conversion UI to existing authority.
            "TEST-158": "Tests",  # Bind account/Admin completion API and Browser evidence.
            "TEST-159": "Tests",  # Bind the exact-source payload and frontend budget checkpoint.
            "TEST-160": "Tests",  # Bind the fail-closed multiprocess safety inventory.
            "TEST-161": "Tests",  # Bind descriptor-owned game-suite discovery.
            "STORAGE-012": "Storage",  # Bind row-scoped insertion and provider-owned bootstrap.
            "TEST-162": "Tests",  # Bind race, replay, rollback, and read-only storage evidence.
            "TEST-163": "Tests",  # Bind central descriptor runtime and generated-contract evidence.
            "LEDGER-033": "Ledger",  # Bind the provider-owned action-index compatibility bridge.
            "TEST-164": "Tests",  # Bind indexed replay and conflict evidence.
            "TOOL-013": "Tooling",  # Bind persistent agent-memory provenance and validation ownership.
            "TEST-165": "Tests",  # Bind requirement shard assembly and drift rejection.
            "TEST-166": "Tests",  # Bind compact shell and Roulette response projections.
            "OAUTH-012": "Core",  # Bind durable provider operations to the OAuth boundary.
            "TEST-167": "Tests",  # Bind default-off provider-control qualification.
            "OAUTH-013": "Core",  # Bind explicit policy-gated social signup to OAuth.
            "AUTH-017": "Core",  # Bind recoverable provider-subject account provisioning.
            "TEST-168": "Tests",  # Bind social-signup API, concurrency, and Browser evidence.
            "LEDGER-034": "Ledger",  # Bind append-only action-journal and compaction ownership.
            "TEST-169": "Tests",  # Bind deterministic action-journal compatibility and scaling evidence.
            "TEST-170": "Tests",  # Bind exact-source performance target enforcement.
            "AUTH-018": "Core",  # Bind account-free verified-email activation to the identity boundary.
            "USER-010": "Application",  # Bind the bilingual pending-verification browser lifecycle.
            "TEST-171": "Tests",  # Bind exactly-once funding and recovery evidence.
            "TEST-193": "Tests",  # Bind Admin conversion wallet, audit, refusal, API, and Browser evidence.
            "AUTH-020": "Core",  # Bind canonical guest teardown ownership to the shared identity transaction.
            "LEDGER-037": "Core",  # Bind terminal debit eligibility to the durable guest claim.
            "TEST-194": "Tests",  # Bind both race orders, recovery, and provider-parity evidence.
            "GUEST-007": "Core",  # Bind shared post-commit conversion analytics convergence.
            "TEST-195": "Tests",  # Bind self-service privacy, recovery, Admin, API, and Browser evidence.
        }
        # Prove every aggregate identifier is present exactly once and cannot collide silently.
        for requirement_id, module in aggregate_allocations.items():
            # Select the sole canonical row for this permanent identifier.
            allocated = [row for row in requirements if row.get("id") == requirement_id]
            # Require one row rather than accepting a missing or duplicated allocation.
            self.assertEqual(len(allocated), 1, requirement_id)
            # Require the accepted module owner for the row.
            self.assertEqual(allocated[0]["module"], module, requirement_id)
        # Count permanent TEST-148 allocations.
        test_148 = [row for row in requirements if row.get("id") == "TEST-148"]
        # Require exactly one permanent allocation after governance is spliced.
        self.assertEqual(len(test_148), 1)
        # Require the tests module ownership.
        self.assertEqual(test_148[0]["module"], "Tests")
        # Count the additive schema-three capacity requirement.
        mysql_007 = [row for row in requirements if row.get("id") == "MYSQL-007"]
        # Require exactly one MySQL-owned capacity allocation.
        self.assertEqual(len(mysql_007), 1)
        # Require the new requirement to remain MySQL-owned.
        self.assertEqual(mysql_007[0]["module"], "MySQL")
        # Count the additive schema rollback-compatibility bridge requirement.
        mysql_008 = [row for row in requirements if row.get("id") == "MYSQL-008"]
        # Require exactly one permanent MySQL bridge allocation.
        self.assertEqual(len(mysql_008), 1)
        # Require the bridge requirement to remain MySQL-owned.
        self.assertEqual(mysql_008[0]["module"], "MySQL")
        # Count the additive release and deployment bridge requirement.
        tool_011 = [row for row in requirements if row.get("id") == "TOOL-011"]
        # Require exactly one permanent tooling bridge allocation.
        self.assertEqual(len(tool_011), 1)
        # Require the bridge requirement to remain Tooling-owned.
        self.assertEqual(tool_011[0]["module"], "Tooling")
        # Count the durable read-only enrollment-policy requirement.
        auth_013 = [row for row in requirements if row.get("id") == "AUTH-013"]
        # Require exactly one permanent enrollment-policy allocation.
        self.assertEqual(len(auth_013), 1)
        # Require the policy requirement to remain Core-owned.
        self.assertEqual(auth_013[0]["module"], "Core")
        # Count the owner-only enrollment-policy transaction requirement.
        auth_014 = [row for row in requirements if row.get("id") == "AUTH-014"]
        # Require exactly one permanent owner-transaction allocation.
        self.assertEqual(len(auth_014), 1)
        # Require the owner-transaction requirement to remain Core-owned.
        self.assertEqual(auth_014[0]["module"], "Core")
        # Require strict provider code and evidence to stay inside the existing AUTH allocation.
        self.assertEqual({"casino/core/storage.py", "tests/storage_tests.py"} <= set(auth_014[0]["implementation_files"]), True)
        # Count the bounded Roulette presentation requirement.
        roulette_072 = [row for row in requirements if row.get("id") == "ROU-072"]
        # Require exactly one permanent Roulette allocation.
        self.assertEqual(len(roulette_072), 1)
        # Require the presentation requirement to remain Roulette-owned.
        self.assertEqual(roulette_072[0]["module"], "Roulette")
        # Count the bounded Slots presentation requirement.
        slot_037 = [row for row in requirements if row.get("id") == "SLOT-037"]
        # Require exactly one permanent Slots allocation.
        self.assertEqual(len(slot_037), 1)
        # Require the presentation requirement to remain Slots-owned.
        self.assertEqual(slot_037[0]["module"], "Slots")
        # Count the shared-wallet celebration requirement after the exact collision guard.
        ux_023 = [row for row in requirements if row.get("id") == "UX-023"]
        # Require exactly one permanent wallet-presentation allocation.
        self.assertEqual(len(ux_023), 1)
        # Require the wallet presentation to remain Application-owned.
        self.assertEqual(ux_023[0]["module"], "Application")
        # Count the semantic game-color application requirement.
        ux_024 = [row for row in requirements if row.get("id") == "UX-024"]
        # Require exactly one permanent semantic game-color allocation.
        self.assertEqual(len(ux_024), 1)
        # Require semantic game colors to remain Application-owned.
        self.assertEqual(ux_024[0]["module"], "Application")
        # Count the sole Browser evidence requirement for semantic game colors.
        test_149 = [row for row in requirements if row.get("id") == "TEST-149"]
        # Require exactly one permanent semantic-color test allocation.
        self.assertEqual(len(test_149), 1)
        # Require the evidence requirement to remain Tests-owned.
        self.assertEqual(test_149[0]["module"], "Tests")
        # Module descriptor equality and monotonicity are governed generically by TEST-184 instead of conflict-prone literals.
