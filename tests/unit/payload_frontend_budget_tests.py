"""Browser-free proof for the Package D0 payload/frontend baseline."""

# Import abstract-syntax inspection for the source-policy gate.
import ast
# Import deep copying for isolated hostile packet mutations.
import copy
# Import one non-EBADF descriptor cleanup error identity.
import errno
# Import gzip decoding for deterministic member verification.
import gzip
# Import in-memory streams for fixed CLI output assertions.
import io
# Import JSON serialization for external TEST-148 fixtures.
import json
# Import nonfinite numeric fixtures.
import math
# Import filesystem operations used by isolated Git fixtures.
import os
# Import local Git subprocess execution for real provenance fixtures.
import subprocess
# Import temporary caller-owned directories outside each checkout.
import tempfile
# Import the standard unit-test framework.
import unittest
# Import focused failure injection without changing production code.
from unittest import mock
# Import canonical filesystem paths.
from pathlib import Path

# Import only the measurement-only module under test.
from tests import payload_frontend_budget as budget


# Run one bounded local Git command for an isolated test repository.
def _git(repo: Path, *arguments: str, payload: bytes | None = None) -> bytes:
    # Execute Git without a shell or network transport.
    result = subprocess.run(
        ["git", *arguments],  # Prefix the fixed local executable.
        cwd=str(repo),  # Bind the command to the disposable repository.
        input=payload,  # Supply only optional local blob bytes.
        capture_output=True,  # Keep ordinary test output quiet.
        timeout=20,  # Bound every local command.
        check=False,  # Report failures through one assertion below.
    )
    # Require the fixture operation to succeed.
    if result.returncode != 0:
        # Raise one test-only assertion without exposing it to governed evidence.
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    # Return raw stdout for exact object identifiers.
    return result.stdout


# Create one real clean Git checkout with every governed asset family.
def _create_repo(parent: Path) -> tuple[Path, str]:
    # Allocate the isolated checkout beneath the caller-owned temporary root.
    repo = parent / "checkout"
    # Create the empty repository directory.
    repo.mkdir()
    # Initialize one ordinary local repository.
    _git(repo, "init", "--quiet")
    # Configure a disposable local author identity.
    _git(repo, "config", "user.email", "d0@example.invalid")
    # Configure the matching disposable author name.
    _git(repo, "config", "user.name", "D0 Test")
    # Define one asset in every required family.
    assets = {
        "web/app.js": b"const shell = true;\n",  # Represent shell JavaScript.
        "web/core/shared.js": b"const shared = true;\n",  # Represent shared JavaScript.
        "web/games/roulette.js": b"const game = true;\n",  # Represent game JavaScript.
        "web/site.css": b"body { color: black; }\n",  # Represent shipped styles.
    }
    # Materialize every tracked asset.
    for relative, payload in assets.items():
        # Resolve the test-owned destination.
        path = repo / Path(relative)
        # Create the owned parent hierarchy.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write the exact binary fixture.
        path.write_bytes(payload)
    # Stage every fixture asset.
    _git(repo, "add", "web")
    # Commit the immutable fixture tree.
    _git(repo, "commit", "--quiet", "-m", "fixture")
    # Resolve the exact fixture commit.
    head = _git(repo, "rev-parse", "HEAD").decode("ascii").strip().lower()
    # Return the clean checkout and exact source.
    return repo, head


# Build one complete valid TEST-148 packet.
def _request_packet(provider: str, source_commit: str) -> dict:
    # Retain the complete deterministic row inventory.
    rows = []
    # Enumerate fixed route positions.
    for route_index, route_family in enumerate(budget.ROUTE_FAMILIES):
        # Enumerate fixed concurrency positions.
        for concurrency in budget.CONCURRENCY_LEVELS:
            # Create a positive byte count with nontrivial division by sixty-four.
            response_bytes = ((route_index + 1) * 1_000) + concurrency
            # Append one exact upstream row.
            rows.append(
                {
                    "route_family": route_family,  # Identify the fixed route.
                    "concurrency": concurrency,  # Identify the fixed concurrency.
                    "p50_ms": 1.25,  # Supply one finite positive median.
                    "p95_ms": 2.5,  # Supply one ordered finite tail.
                    "throughput_rps": 64.0,  # Supply one finite positive rate.
                    "errors": 0,  # Prove the exact integer zero domain.
                    "response_bytes": response_bytes,  # Supply the aggregate bytes.
                }
            )
    # Return the complete strict packet.
    return {
        "schema": budget.REQUEST_SCHEMA,  # Identify TEST-148 evidence.
        "source_commit": source_commit,  # Bind the packet to exact HEAD.
        "provider": provider,  # Identify the isolated provider.
        "rows": rows,  # Retain exactly twenty measurements.
    }


# Write one packet to a caller-owned external path.
def _write_packet(path: Path, packet: dict) -> None:
    # Serialize deterministically without nonstandard numeric values.
    encoded = json.dumps(packet, allow_nan=False, sort_keys=True).encode("utf-8")
    # Write the complete external evidence fixture.
    path.write_bytes(encoded)


# Build one recursively valid D0 output fixture without reading Git.
def _valid_output(source_commit: str = "a" * 40) -> dict:
    # Retain every fixed route row in its expected order.
    routes = []
    # Enumerate output providers.
    for provider in budget.PROVIDERS:
        # Enumerate fixed route families.
        for route_index, route_family in enumerate(budget.ROUTE_FAMILIES):
            # Build one four-cohort response-byte total.
            response_bytes = sum(((route_index + 1) * 1_000) + concurrency for concurrency in budget.CONCURRENCY_LEVELS)
            # Calculate the fixed aggregate operation count.
            operations = budget.OPERATIONS_PER_INPUT_ROW * len(budget.CONCURRENCY_LEVELS)
            # Append one unique strict numeric measurement.
            routes.append(
                {
                    "provider": provider,  # Identify the fixed provider.
                    "route_family": route_family,  # Identify the fixed route.
                    "operations": operations,  # Pin four times sixty-four.
                    "bytes_per_op": response_bytes / operations,  # Divide exactly.
                }
            )
    # Retain one row for every fixed asset family.
    assets = [
        {
            "asset_family": family,  # Identify the fixed family.
            "raw_bytes": index + 1,  # Supply a strict nonnegative integer.
            "deterministic_gzip_bytes": index + 20,  # Supply a strict gzip count.
        }
        for index, family in enumerate(budget.ASSET_FAMILIES)  # Preserve the fixed family order.
    ]
    # Return the complete allowlisted document.
    return {
        "schema": budget.EVIDENCE_SCHEMA,  # Identify D0 evidence.
        "source_commit": source_commit,  # Bind the output to exact source.
        "routes": routes,  # Retain only numeric route measurements.
        "assets": assets,  # Retain only aggregate asset measurements.
    }


# Share one disposable real Git checkout across happy-path tests.
class PayloadFrontendBudgetHappyPathTests(unittest.TestCase):
    """Prove exact deterministic output without runtime or network access."""

    # Create one isolated real checkout before each test.
    def setUp(self):
        # Allocate one caller-owned temporary root.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve the temporary root path.
        self.parent = Path(self.temporary.name)
        # Create the clean Git fixture.
        self.repo, self.head = _create_repo(self.parent)
        # Create one external evidence directory beside the checkout.
        self.external = self.parent / "evidence"
        # Materialize the external directory.
        self.external.mkdir()
        # Resolve the JSON input packet path.
        self.json_path = self.external / "json.json"
        # Resolve the MySQL input packet path.
        self.mysql_path = self.external / "mysql.json"
        # Build the valid JSON provider packet.
        self.json_packet = _request_packet("json", self.head)
        # Build the valid MySQL provider packet.
        self.mysql_packet = _request_packet("mysql", self.head)
        # Write the JSON packet outside the checkout.
        _write_packet(self.json_path, self.json_packet)
        # Write the MySQL packet outside the checkout.
        _write_packet(self.mysql_path, self.mysql_packet)

    # Remove every disposable fixture after each test.
    def tearDown(self):
        # Release the complete temporary hierarchy.
        self.temporary.cleanup()

    # Prove exact source, request, asset, and output composition.
    def test_build_evidence_is_exact_allowlisted_and_deterministic(self):
        # Build the first complete evidence document.
        first = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Build a second independent document from identical immutable inputs.
        second = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Require byte-for-byte deterministic serialization.
        self.assertEqual(budget._serialized_output(first), budget._serialized_output(second))
        # Require the exact top-level allowlist.
        self.assertEqual(set(first), budget.OUTPUT_KEYS)
        # Require exact immutable source provenance.
        self.assertEqual(first["source_commit"], self.head)
        # Require the complete ten-row unique provider/route matrix.
        self.assertEqual(len(first["routes"]), 10)
        # Require every semantic row identity exactly once.
        self.assertEqual(
            len({(row["provider"], row["route_family"]) for row in first["routes"]}),  # Count unique identities.
            10,  # Require two providers by five routes.
        )
        # Require one row for every fixed asset family.
        self.assertEqual([row["asset_family"] for row in first["assets"]], list(budget.ASSET_FAMILIES))
        # Build each exact four-concurrency upstream aggregate.
        expected_aggregates = []
        # Process providers in output order.
        for packet in (self.json_packet, self.mysql_packet):
            # Process route families in output order.
            for route_family in budget.ROUTE_FAMILIES:
                # Sum every fixed concurrency cohort for the family.
                expected_aggregates.append(
                    sum(row["response_bytes"] for row in packet["rows"] if row["route_family"] == route_family)  # Sum exact bytes.
                )
        # Pair emitted rows with the deterministic upstream aggregates.
        for output_row, response_bytes in zip(first["routes"], expected_aggregates, strict=True):
            # Require the fixed two-hundred-fifty-six operation count.
            self.assertEqual(output_row["operations"], 256)
            # Require a strict JSON numeric measurement.
            self.assertIsInstance(output_row["bytes_per_op"], float)
            # Require exact aggregate reconstruction with no rounding.
            self.assertEqual(output_row["bytes_per_op"] * 256, response_bytes)
        # Require every asset family to contain shipped bytes.
        self.assertTrue(all(row["raw_bytes"] > 0 for row in first["assets"]))
        # Require every deterministic gzip total to be positive.
        self.assertTrue(all(row["deterministic_gzip_bytes"] > 0 for row in first["assets"]))
        # Require recursive validation to accept the generated document.
        budget.validate_output(first)
        # Serialize for a broad privacy-key inspection.
        serialized = budget._serialized_output(first).decode("ascii").lower()
        # Reject every forbidden emitted field name.
        for forbidden in (
            "topology",  # Reject an unmeasured topology claim.
            "filename",  # Reject raw filename identity.
            "path",  # Reject raw filesystem identity.
            "url",  # Reject raw route or network identity.
            "token",  # Reject authentication material.
            "cookie",  # Reject session material.
            "wallet",  # Reject player balance detail.
            "wager",  # Reject game action detail.
            "outcome",  # Reject game result detail.
            "timestamp",  # Reject run timing identity.
            "host",  # Reject infrastructure identity.
            "port",  # Reject infrastructure identity.
            "database",  # Reject storage identity.
            "exception",  # Reject raw failure detail.
        ):  # Complete the fixed forbidden-field inventory.
            # Confirm the forbidden field is absent.
            self.assertNotIn(f'"{forbidden}"', serialized)

    # Prove fixed gzip header, content, and repeated bytes.
    def test_deterministic_gzip_has_fixed_header_and_round_trips(self):
        # Define one nontrivial immutable asset.
        payload = b"alpha beta gamma\n" * 10
        # Compress it twice independently.
        first = budget.deterministic_gzip(payload)
        # Repeat the same deterministic operation.
        second = budget.deterministic_gzip(payload)
        # Require byte identity across runs.
        self.assertEqual(first, second)
        # Require the fixed zero-mtime header.
        self.assertEqual(first[:8], b"\x1f\x8b\x08\x00\x00\x00\x00\x00")
        # Require the fixed maximum-level flag and unknown operating system.
        self.assertEqual(first[8:10], b"\x02\xff")
        # Require standard gzip decoding to recover the original bytes.
        self.assertEqual(gzip.decompress(first), payload)
        # Reject mutable bytearray input rather than coercing it.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Exercise the strict input boundary.
            budget.deterministic_gzip(bytearray(payload))

    # Prove external atomic output and repeat determinism.
    def test_atomic_output_is_external_repeatable_and_temp_free(self):
        # Build one valid document.
        evidence = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Resolve one caller-owned external destination.
        output = self.external / "payload.json"
        # Write the first canonical document.
        written = budget.write_evidence_atomic(output, evidence, self.repo)
        # Capture the complete first bytes.
        first_bytes = written.read_bytes()
        # Write the same document a second time.
        budget.write_evidence_atomic(output, evidence, self.repo)
        # Require byte identity after replacement.
        self.assertEqual(output.read_bytes(), first_bytes)
        # Require a newline-terminated canonical document.
        self.assertTrue(first_bytes.endswith(b"\n"))
        # Require no owned temporary residue.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])

    # Prove pre-existing output survives replacement failure.
    def test_atomic_output_preserves_existing_file_on_replace_failure(self):
        # Build one valid document.
        evidence = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Resolve one caller-owned output.
        output = self.external / "payload.json"
        # Seed a byte-exact pre-existing document.
        output.write_bytes(b"retained")
        # Inject one replacement failure after temporary write and fsync.
        with mock.patch.object(budget.os, "replace", side_effect=OSError("SECRET_REPLACE")):
            # Require a fixed value-free programmatic error.
            with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^output write failed$"):
                # Attempt the governed atomic write.
                budget.write_evidence_atomic(output, evidence, self.repo)
        # Require the original caller file to remain exact.
        self.assertEqual(output.read_bytes(), b"retained")
        # Require every owned temporary file to be removed.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])

    # Prove a post-write flush failure preserves prior bytes and removes the temp.
    def test_atomic_output_preserves_existing_file_on_fsync_failure(self):
        # Build one valid document.
        evidence = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Resolve one caller-owned output.
        output = self.external / "payload.json"
        # Seed byte-exact pre-existing content.
        output.write_bytes(b"retained-before-fsync")
        # Inject one bounded durability failure after the temporary write.
        with mock.patch.object(budget.os, "fsync", side_effect=OSError("SECRET_FSYNC")):
            # Require one fixed value-free programmatic failure.
            with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^output write failed$"):
                # Attempt the governed atomic write.
                budget.write_evidence_atomic(output, evidence, self.repo)
        # Require the original destination to remain byte-exact.
        self.assertEqual(output.read_bytes(), b"retained-before-fsync")
        # Require every owned partial temporary file to be removed.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])

    # Prove fdopen failure closes the raw descriptor before temp removal.
    def test_atomic_output_closes_raw_descriptor_when_fdopen_fails(self):
        # Build one valid document.
        evidence = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Resolve one caller-owned output.
        output = self.external / "payload.json"
        # Seed byte-exact pre-existing content.
        output.write_bytes(b"retained-before-fdopen")
        # Retain the real low-level close implementation.
        real_close = os.close
        # Retain the real temporary allocation implementation.
        real_mkstemp = budget.tempfile.mkstemp
        # Capture only the descriptor owned by the atomic output helper.
        owned_descriptors = []

        # Record the helper-owned descriptor without affecting Git subprocess descriptors.
        def capture_owned_descriptor(*args, **kwargs):
            # Allocate the real same-directory temporary file.
            descriptor, name = real_mkstemp(*args, **kwargs)
            # Retain the exact descriptor whose cleanup this test governs.
            owned_descriptors.append(descriptor)
            # Return the unmodified allocation result.
            return descriptor, name

        # Observe real descriptor cleanup while injecting stream-transfer failure.
        with mock.patch.object(budget.tempfile, "mkstemp", side_effect=capture_owned_descriptor):
            # Observe every real close without changing unrelated subprocess behavior.
            with mock.patch.object(budget.os, "close", wraps=real_close) as close_call:
                # Fail only the fdopen ownership transfer after real mkstemp allocation.
                with mock.patch.object(budget.os, "fdopen", side_effect=OSError("SECRET_FDOPEN")):
                    # Require one fixed value-free programmatic failure.
                    with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^output write failed$"):
                        # Attempt the governed atomic write.
                        budget.write_evidence_atomic(output, evidence, self.repo)
        # Require exactly one helper-owned descriptor allocation.
        self.assertEqual(len(owned_descriptors), 1)
        # Require exactly one explicit close of that helper-owned descriptor.
        self.assertEqual(sum(call.args == (owned_descriptors[0],) for call in close_call.call_args_list), 1)
        # Require the original destination to remain byte-exact.
        self.assertEqual(output.read_bytes(), b"retained-before-fdopen")
        # Require every owned temporary file to be removed after handle release.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])

    # Prove non-EBADF close reporting cannot skip owned-temp unlink.
    def test_atomic_output_attempts_unlink_after_raw_close_error(self):
        # Build one valid document.
        evidence = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Resolve one caller-owned output.
        output = self.external / "payload.json"
        # Seed byte-exact pre-existing content.
        output.write_bytes(b"retained-before-close-error")
        # Retain the real low-level close implementation.
        real_close = os.close
        # Retain the real temporary allocation implementation.
        real_mkstemp = budget.tempfile.mkstemp
        # Capture only the descriptor owned by the atomic output helper.
        owned_descriptors = []

        # Record the helper-owned descriptor without affecting Git subprocess descriptors.
        def capture_owned_descriptor(*args, **kwargs):
            # Allocate the real same-directory temporary file.
            descriptor, name = real_mkstemp(*args, **kwargs)
            # Retain the exact descriptor whose cleanup this test governs.
            owned_descriptors.append(descriptor)
            # Return the unmodified allocation result.
            return descriptor, name

        # Release the descriptor but report one synthetic non-EBADF error.
        def close_then_report_error(descriptor: int) -> None:
            # Preserve unrelated subprocess descriptor cleanup exactly.
            if descriptor not in owned_descriptors:
                # Close the unrelated descriptor without injecting the owned-file failure.
                real_close(descriptor)
                # End after preserving the unrelated close.
                return
            # Close the real descriptor so Windows can remove the temp.
            real_close(descriptor)
            # Report a non-EBADF cleanup error with hostile detail.
            raise OSError(errno.EIO, "SECRET_CLOSE_DETAIL")

        # Capture the exact helper-owned descriptor allocation.
        with mock.patch.object(budget.tempfile, "mkstemp", side_effect=capture_owned_descriptor):
            # Fail fdopen so raw descriptor cleanup owns the handle.
            with mock.patch.object(budget.os, "fdopen", side_effect=OSError("SECRET_FDOPEN")):
                # Inject the close error only after real handle release.
                with mock.patch.object(budget.os, "close", side_effect=close_then_report_error):
                    # Require the final fixed cleanup failure.
                    with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^output cleanup failed$") as caught:
                        # Attempt the governed atomic write.
                        budget.write_evidence_atomic(output, evidence, self.repo)
        # Require exactly one helper-owned descriptor allocation.
        self.assertEqual(len(owned_descriptors), 1)
        # Require no raw close detail in the surfaced failure.
        self.assertNotIn("SECRET_CLOSE_DETAIL", str(caught.exception))
        # Require the original destination to remain byte-exact.
        self.assertEqual(output.read_bytes(), b"retained-before-close-error")
        # Require unlink to have removed every owned temporary file.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])

    # Prove invalid evidence fails before any destination or temporary mutation.
    def test_invalid_output_preserves_existing_file_before_destination_touch(self):
        # Build one valid document.
        evidence = budget.build_evidence(self.json_path, self.mysql_path, self.repo)
        # Add one forbidden field that serialization validation must reject.
        evidence["private"] = "SECRET_VALUE"
        # Resolve one caller-owned output.
        output = self.external / "payload.json"
        # Seed byte-exact pre-existing content.
        output.write_bytes(b"retained-before-validation")
        # Require strict recursive validation failure.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Attempt the invalid write.
            budget.write_evidence_atomic(output, evidence, self.repo)
        # Require the destination to remain byte-exact.
        self.assertEqual(output.read_bytes(), b"retained-before-validation")
        # Require no owned temporary allocation.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])


# Validate upstream TEST-148 packets without filesystem fixtures.
class RequestPacketValidationTests(unittest.TestCase):
    """Reject mixed, malformed, coercive, and incomplete request evidence."""

    # Build one valid packet before each mutation test.
    def setUp(self):
        # Retain a fixed exact source identity.
        self.source = "b" * 40
        # Build one valid JSON provider packet.
        self.packet = _request_packet("json", self.source)

    # Assert one mutated packet fails closed.
    def _reject(self, mutation):
        # Copy the valid packet recursively.
        packet = copy.deepcopy(self.packet)
        # Apply the isolated hostile mutation.
        mutation(packet)
        # Require one fixed module error rather than a raw exception.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Validate against the expected provider and source.
            budget.validate_request_packet(packet, "json", self.source)

    # Prove exact top-level strings and allowlists.
    def test_rejects_unknown_fields_and_non_string_identities(self):
        # Define hostile packet mutations.
        mutations = (
            lambda packet: packet.update({"private": "value"}),  # Add one unknown field.
            lambda packet: packet.__setitem__("schema", []),  # Supply an unhashable schema.
            lambda packet: packet.__setitem__("source_commit", int("1" * 40)),  # Supply numeric provenance.
            lambda packet: packet.__setitem__("provider", []),  # Supply an unhashable provider.
            lambda packet: packet.__setitem__("provider", "mysql"),  # Mix providers.
            lambda packet: packet.__setitem__("source_commit", "c" * 40),  # Mix immutable heads.
            lambda packet: packet.__setitem__("rows", {}),  # Replace the fixed collection.
        )
        # Exercise every hostile root shape.
        for mutation in mutations:
            # Identify each case without reflecting the hostile value.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)

    # Prove exact row identities, order, and cardinality.
    def test_rejects_missing_duplicate_reordered_and_coercive_rows(self):
        # Define hostile matrix mutations.
        mutations = (
            lambda packet: packet["rows"].pop(),  # Remove one required row.
            lambda packet: packet["rows"].append(copy.deepcopy(packet["rows"][-1])),  # Add a duplicate.
            lambda packet: packet["rows"].reverse(),  # Reorder the fixed matrix.
            lambda packet: packet["rows"][0].update({"concurrency": True}),  # Use boolean one.
            lambda packet: packet["rows"][0].update({"concurrency": 1.0}),  # Use floating one.
            lambda packet: packet["rows"][0].update({"route_family": []}),  # Use unhashable route.
            lambda packet: packet["rows"][0].update({"route_family": "unknown"}),  # Use unknown route.
            lambda packet: packet["rows"][0].update({"extra": 1}),  # Add a nested private field.
        )
        # Exercise every hostile matrix shape.
        for mutation in mutations:
            # Identify the isolated mutation.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)

    # Prove exact aggregate numeric domains without coercion.
    def test_rejects_hostile_metrics_errors_and_response_bytes(self):
        # Define hostile aggregate mutations.
        mutations = (
            lambda packet: packet["rows"][0].update({"p50_ms": True}),  # Reject boolean metrics.
            lambda packet: packet["rows"][0].update({"p50_ms": 0}),  # Reject zero metrics.
            lambda packet: packet["rows"][0].update({"p50_ms": math.inf}),  # Reject infinity.
            lambda packet: packet["rows"][0].update({"p50_ms": 3, "p95_ms": 2}),  # Reject inverted percentiles.
            lambda packet: packet["rows"][0].update({"throughput_rps": budget.MAX_SAFE_INTEGER + 1}),  # Reject huge rate.
            lambda packet: packet["rows"][0].update({"errors": False}),  # Reject boolean zero.
            lambda packet: packet["rows"][0].update({"errors": 0.0}),  # Reject floating zero.
            lambda packet: packet["rows"][0].update({"errors": 1}),  # Reject nonzero errors.
            lambda packet: packet["rows"][0].update({"response_bytes": True}),  # Reject boolean bytes.
            lambda packet: packet["rows"][0].update({"response_bytes": 1.0}),  # Reject floating bytes.
            lambda packet: packet["rows"][0].update({"response_bytes": 0}),  # Reject zero bytes.
            lambda packet: packet["rows"][0].update({"response_bytes": budget.MAX_SAFE_INTEGER + 1}),  # Reject huge bytes.
        )
        # Exercise every hostile numeric input.
        for mutation in mutations:
            # Identify the isolated mutation.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)

    # Prove valid huge integer comparisons do not coerce through float.
    def test_percentile_ordering_uses_original_numeric_values(self):
        # Set both values above the binary-float exact integer boundary.
        self.packet["rows"][0]["p50_ms"] = (2**53) - 1
        # Keep the tail at the same exact bounded integer.
        self.packet["rows"][0]["p95_ms"] = (2**53) - 1
        # Require the exact bounded packet to remain valid.
        budget.validate_request_packet(self.packet, "json", self.source)


# Validate the complete D0 output recursively.
class OutputValidationTests(unittest.TestCase):
    """Reject schema surprises, rounded bytes, and private nested fields."""

    # Assert one output mutation fails closed.
    def _reject(self, mutation):
        # Build one recursively valid document.
        evidence = _valid_output()
        # Apply the hostile mutation.
        mutation(evidence)
        # Require a fixed module error.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Validate the mutated document.
            budget.validate_output(evidence)

    # Prove the policy constants are not emitted or claimed as measurements.
    def test_topology_is_policy_only_and_not_emitted(self):
        # Require the accepted deployment limitation constants.
        self.assertEqual((budget.ACCEPTED_WORKERS, budget.ACCEPTED_THREADS), (1, 2))
        # Build one valid document.
        evidence = _valid_output()
        # Require no topology field in the exact allowlist.
        self.assertNotIn("topology", budget.OUTPUT_KEYS)
        # Require no topology field in the emitted document.
        self.assertNotIn("topology", evidence)
        # Require the valid document to pass.
        budget.validate_output(evidence)
        # Add a false measured-topology claim.
        evidence["topology"] = {"workers": 1, "threads": 2}
        # Require strict schema rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Validate the expanded document.
            budget.validate_output(evidence)

    # Prove strict top-level and nested allowlists.
    def test_rejects_unknown_missing_and_non_string_identity_fields(self):
        # Define hostile structural mutations.
        mutations = (
            lambda evidence: evidence.update({"private": 1}),  # Add a top-level field.
            lambda evidence: evidence.pop("assets"),  # Remove a required field.
            lambda evidence: evidence.__setitem__("schema", []),  # Use unhashable schema.
            lambda evidence: evidence.__setitem__("source_commit", int("1" * 40)),  # Use numeric source.
            lambda evidence: evidence["routes"][0].update({"concurrency": 1}),  # Add hidden route identity.
            lambda evidence: evidence["routes"][0].update({"provider": []}),  # Use unhashable provider.
            lambda evidence: evidence["routes"][0].update({"route_family": {}}),  # Use object route.
            lambda evidence: evidence["assets"][0].update({"filename": "secret.js"}),  # Add a raw filename.
            lambda evidence: evidence["assets"][0].update({"asset_family": []}),  # Use unhashable asset family.
        )
        # Exercise each hostile structure.
        for mutation in mutations:
            # Identify the isolated mutation.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)

    # Prove operations and byte-per-operation strict numeric domains.
    def test_rejects_non_numeric_nonfinite_rounded_and_huge_route_bytes(self):
        # Define hostile route metric mutations.
        mutations = (
            lambda evidence: evidence["routes"][0].update({"operations": True}),  # Reject boolean operations.
            lambda evidence: evidence["routes"][0].update({"operations": 256.0}),  # Reject floating operations.
            lambda evidence: evidence["routes"][0].update({"operations": 64}),  # Reject one-cohort operations.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": "1/64"}),  # Reject rational strings.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": True}),  # Reject booleans.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": math.nan}),  # Reject NaN.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": math.inf}),  # Reject infinity.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": 0}),  # Reject zero.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": 1.001}),  # Reject inexact reconstruction.
            lambda evidence: evidence["routes"][0].update({"bytes_per_op": budget.MAX_SAFE_INTEGER}),  # Reject huge product.
        )
        # Exercise each hostile metric.
        for mutation in mutations:
            # Identify the isolated mutation.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)

    # Prove exact identity order and cardinality.
    def test_rejects_missing_duplicate_and_reordered_output_rows(self):
        # Define hostile inventory mutations.
        mutations = (
            lambda evidence: evidence["routes"].pop(),  # Remove one route row.
            lambda evidence: evidence["routes"].reverse(),  # Reorder route rows.
            lambda evidence: evidence["assets"].pop(),  # Remove one asset row.
            lambda evidence: evidence["assets"].reverse(),  # Reorder asset rows.
        )
        # Exercise each hostile inventory.
        for mutation in mutations:
            # Identify the isolated mutation.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)

    # Prove exact non-boolean asset integer domains.
    def test_rejects_hostile_asset_byte_types(self):
        # Define hostile asset metric mutations.
        mutations = (
            lambda evidence: evidence["assets"][0].update({"raw_bytes": True}),  # Reject boolean bytes.
            lambda evidence: evidence["assets"][0].update({"raw_bytes": 1.0}),  # Reject floating bytes.
            lambda evidence: evidence["assets"][0].update({"raw_bytes": -1}),  # Reject negative bytes.
            lambda evidence: evidence["assets"][0].update({"raw_bytes": budget.MAX_SAFE_INTEGER + 1}),  # Reject huge bytes.
            lambda evidence: evidence["assets"][0].update({"deterministic_gzip_bytes": []}),  # Reject containers.
        )
        # Exercise each hostile asset metric.
        for mutation in mutations:
            # Identify the isolated mutation.
            with self.subTest(mutation=mutation):
                # Require fail-closed rejection.
                self._reject(mutation)


# Prove exact real-Git asset and tree safety boundaries.
class GitAssetSafetyTests(unittest.TestCase):
    """Reject dirty, ignored, indirect, colliding, or mismatched assets."""

    # Create one isolated real Git checkout before each test.
    def setUp(self):
        # Allocate one temporary root.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve the temporary path.
        self.parent = Path(self.temporary.name)
        # Create the real fixture checkout.
        self.repo, self.head = _create_repo(self.parent)

    # Release the test repository after each case.
    def tearDown(self):
        # Remove the complete temporary hierarchy.
        self.temporary.cleanup()

    # Prove dirty tracked and untracked trees fail before analysis.
    def test_rejects_dirty_tracked_and_untracked_checkout(self):
        # Modify one tracked shipped asset.
        (self.repo / "web" / "app.js").write_bytes(b"dirty")
        # Require tracked dirt rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Inspect the dirty checkout.
            budget._require_clean_checkout(self.repo)
        # Restore the tracked file exactly.
        _git(self.repo, "restore", "web/app.js")
        # Create one untracked non-asset file.
        (self.repo / "UNTRACKED").write_text("dirty", encoding="utf-8")
        # Require untracked dirt rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Inspect the dirty checkout.
            budget._require_clean_checkout(self.repo)

    # Prove ignored shipped-asset candidates fail closed.
    def test_rejects_ignored_shipped_asset(self):
        # Add one explicit ignored asset rule.
        (self.repo / ".gitignore").write_text("web/ignored.js\n", encoding="utf-8")
        # Stage the ignore rule.
        _git(self.repo, "add", ".gitignore")
        # Commit the clean policy fixture.
        _git(self.repo, "commit", "--quiet", "-m", "ignore")
        # Create one ignored shipped-asset-shaped file.
        (self.repo / "web" / "ignored.js").write_bytes(b"ignored")
        # Require ignored candidate rejection even though status is clean.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Inspect the ignored inventory.
            budget._require_clean_checkout(self.repo)

    # Add one exact tree record directly to the Git index.
    def _add_index_record(self, mode: str, object_id: str, relative_path: str) -> None:
        # Stage the exact object and path without worktree dependence.
        _git(self.repo, "update-index", "--add", "--cacheinfo", f"{mode},{object_id},{relative_path}")
        # Commit the hostile immutable tree.
        _git(self.repo, "commit", "--quiet", "-m", "hostile tree")
        # Refresh the exact commit identity.
        self.head = _git(self.repo, "rev-parse", "HEAD").decode("ascii").strip().lower()

    # Prove tracked symlink and submodule modes fail before byte reads.
    def test_rejects_tracked_symlink_and_submodule(self):
        # Write one symlink-target blob into the object database.
        blob = _git(self.repo, "hash-object", "-w", "--stdin", payload=b"target").decode("ascii").strip()
        # Add it as a tracked web symlink.
        self._add_index_record("120000", blob, "web/linked.js")
        # Require immutable tree rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Parse the hostile tracked tree.
            budget._tracked_asset_entries(self.repo, self.head)
        # Create a second clean test repository for a gitlink.
        second_parent = self.parent / "second"
        # Materialize the parent directory.
        second_parent.mkdir()
        # Create the second fixture checkout.
        second_repo, second_head = _create_repo(second_parent)
        # Stage the fixture HEAD as a web submodule entry.
        _git(second_repo, "update-index", "--add", "--cacheinfo", f"160000,{second_head},web/vendor")
        # Commit the hostile gitlink.
        _git(second_repo, "commit", "--quiet", "-m", "gitlink")
        # Resolve the hostile commit.
        hostile_head = _git(second_repo, "rev-parse", "HEAD").decode("ascii").strip().lower()
        # Require gitlink rejection anywhere beneath web.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Parse the hostile tree.
            budget._tracked_asset_entries(second_repo, hostile_head)

    # Prove case-colliding tracked assets cannot receive two identities.
    def test_rejects_case_colliding_assets(self):
        # Write one ordinary JavaScript blob.
        blob = _git(self.repo, "hash-object", "-w", "--stdin", payload=b"duplicate").decode("ascii").strip()
        # Stage the uppercase logical path.
        _git(self.repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},web/DUP.js")
        # Stage the lowercase logical alias.
        _git(self.repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},web/dup.js")
        # Commit both index identities.
        _git(self.repo, "commit", "--quiet", "-m", "case collision")
        # Resolve the hostile commit.
        hostile_head = _git(self.repo, "rev-parse", "HEAD").decode("ascii").strip().lower()
        # Require cross-platform collision rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Parse the colliding tree.
            budget._tracked_asset_entries(self.repo, hostile_head)

    # Prove mixed-case tracked extensions remain inside the complete inventory.
    def test_tracks_uppercase_javascript_and_css_extensions(self):
        # Define one mixed-case shell JavaScript payload.
        javascript_payload = b"const uppercase = true;\n"
        # Define one uppercase stylesheet payload.
        stylesheet_payload = b".uppercase { display: block; }\n"
        # Materialize the mixed-case JavaScript asset.
        (self.repo / "web" / "escape.Js").write_bytes(javascript_payload)
        # Materialize the uppercase CSS asset.
        (self.repo / "web" / "escape.CSS").write_bytes(stylesheet_payload)
        # Stage both real tracked assets.
        _git(self.repo, "add", "web/escape.Js", "web/escape.CSS")
        # Commit the immutable mixed-case tree.
        _git(self.repo, "commit", "--quiet", "-m", "mixed extensions")
        # Resolve the exact commit.
        mixed_head = _git(self.repo, "rev-parse", "HEAD").decode("ascii").strip().lower()
        # Read the complete tracked inventory.
        entries = budget._tracked_asset_entries(self.repo, mixed_head)
        # Retain exact tracked paths.
        tracked_paths = [path.as_posix() for path, _object_id in entries]
        # Require the mixed-case JavaScript asset exactly once.
        self.assertEqual(tracked_paths.count("web/escape.Js"), 1)
        # Require the uppercase CSS asset exactly once.
        self.assertEqual(tracked_paths.count("web/escape.CSS"), 1)
        # Build exact family aggregates.
        rows = {row["asset_family"]: row for row in budget._asset_rows(self.repo, mixed_head)}
        # Read the original shell fixture size.
        original_shell_size = len((self.repo / "web" / "app.js").read_bytes())
        # Require the mixed-case JavaScript bytes in the shell family.
        self.assertEqual(rows["shell_javascript"]["raw_bytes"], original_shell_size + len(javascript_payload))
        # Read the original stylesheet fixture size.
        original_stylesheet_size = len((self.repo / "web" / "site.css").read_bytes())
        # Require the uppercase stylesheet bytes in the stylesheet family.
        self.assertEqual(rows["stylesheets"]["raw_bytes"], original_stylesheet_size + len(stylesheet_payload))

    # Prove worktree bytes must match their exact immutable blob.
    def test_rejects_worktree_blob_mismatch(self):
        # Replace one tracked file without invoking the clean-tree guard.
        (self.repo / "web" / "app.js").write_bytes(b"mismatch")
        # Require the asset reader itself to fail closed.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Build asset rows from the mismatched worktree.
            budget._asset_rows(self.repo, self.head)

    # Prove every intermediate component is checked before Git-backed reading.
    def test_rejects_intermediate_asset_indirection_without_bypassing_git(self):
        # Read the real tracked inventory from the immutable fixture commit.
        entries = budget._tracked_asset_entries(self.repo, self.head)
        # Select the tracked shared asset and its real Git blob.
        shared_path, shared_object = next(
            (path, object_id)  # Return the exact tracked path and blob.
            for path, object_id in entries  # Inspect the real Git inventory.
            if path.as_posix() == "web/core/shared.js"  # Select the shared fixture.
        )
        # Resolve the exact intermediate directory that a reparse point could replace.
        indirect_component = (self.repo / "web" / "core").absolute()
        # Retain the real link detector for every other component.
        real_detector = budget._is_linklike

        # Mark only the intermediate component as indirect.
        def component_detector(path: Path) -> bool:
            # Simulate the platform reporting a symlink or junction on that component.
            if path.absolute() == indirect_component:
                # Report the hostile ancestor.
                return True
            # Preserve real link detection for the leaf, checkout, and other parents.
            return real_detector(path)

        # Patch only the platform-specific reparse predicate.
        with mock.patch.object(budget, "_is_linklike", side_effect=component_detector):
            # Require rejection before reading an otherwise valid real Git blob.
            with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^worktree asset is indirect$"):
                # Verify the tracked path through the complete component walk.
                budget._verified_asset_bytes(self.repo, shared_path, shared_object)


# Prove external path, parser, source-policy, and fixed-failure boundaries.
class BoundaryAndPolicyTests(unittest.TestCase):
    """Keep D0 external, listener-free, privacy-safe, and measurement-only."""

    # Create one real repository and external directory before each test.
    def setUp(self):
        # Allocate one temporary hierarchy.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve the hierarchy root.
        self.parent = Path(self.temporary.name)
        # Create one clean checkout.
        self.repo, self.head = _create_repo(self.parent)
        # Create one caller-owned external directory.
        self.external = self.parent / "external"
        # Materialize the external directory.
        self.external.mkdir()

    # Remove all disposable paths after each test.
    def tearDown(self):
        # Release the complete hierarchy.
        self.temporary.cleanup()

    # Prove input/output containment and traversal fail closed.
    def test_rejects_relative_traversal_and_in_checkout_paths(self):
        # Materialize one ordinary external input.
        external_input = self.external / "input.json"
        # Write one JSON object.
        external_input.write_text("{}", encoding="utf-8")
        # Require the ordinary external input to resolve.
        self.assertEqual(budget.resolve_input_path(external_input, self.repo), external_input.resolve())
        # Define hostile path operations.
        hostile_calls = (
            lambda: budget.resolve_input_path("relative.json", self.repo),  # Reject relative input.
            lambda: budget.resolve_output_path("relative.json", self.repo),  # Reject relative output.
            lambda: budget.resolve_input_path(self.repo / "web" / "app.js", self.repo),  # Reject checkout input.
            lambda: budget.resolve_output_path(self.repo / "output.json", self.repo),  # Reject checkout output.
            lambda: budget.resolve_input_path(self.external / ".." / "external" / "input.json", self.repo),  # Reject input traversal.
            lambda: budget.resolve_output_path(self.external / ".." / "external" / "output.json", self.repo),  # Reject output traversal.
        )
        # Exercise every hostile path.
        for operation in hostile_calls:
            # Identify the isolated operation.
            with self.subTest(operation=operation):
                # Require fixed fail-closed rejection.
                with self.assertRaises(budget.PayloadFrontendBudgetError):
                    # Execute the hostile resolver.
                    operation()

    # Prove symlink aliases are rejected when the platform permits creation.
    def test_rejects_external_symlink_aliases(self):
        # Materialize one ordinary target file.
        target = self.external / "target.json"
        # Write the target bytes.
        target.write_text("{}", encoding="utf-8")
        # Resolve one sibling symlink path.
        link = self.external / "alias.json"
        # Attempt a real filesystem symlink.
        try:
            # Create an alias to the target.
            os.symlink(target, link)
        # Skip only when the host policy cannot create symlinks.
        except OSError:
            # Record the platform limitation explicitly.
            self.skipTest("host cannot create test symlink")
        # Require input alias rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Resolve the linked input.
            budget.resolve_input_path(link, self.repo)
        # Require existing output alias rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Resolve the linked output.
            budget.resolve_output_path(link, self.repo)

    # Prove malformed, duplicate, Unicode, and oversized packets fail privately.
    def test_packet_parser_rejects_hostile_external_bytes(self):
        # Define hostile packet bytes.
        payloads = (
            b"",  # Reject empty evidence.
            b"{",  # Reject malformed JSON.
            b'{"a":1,"a":2}',  # Reject duplicate keys.
            b"\xff",  # Reject invalid UTF-8.
            b"0",  # Reject scalar roots.
            b'{"number":' + (b"9" * 5_000) + b"}",  # Reject over-limit integer decoding.
            (b"[" * 5_000) + b"0" + (b"]" * 5_000),  # Reject recursive parser exhaustion.
            b"x" * (budget.MAX_INPUT_BYTES + 1),  # Reject oversized input.
        )
        # Exercise each hostile packet.
        for index, payload in enumerate(payloads):
            # Resolve one external fixture path.
            path = self.external / f"packet-{index}.json"
            # Write the exact hostile bytes.
            path.write_bytes(payload)
            # Require a fixed module error without raw parser exceptions.
            with self.assertRaises(budget.PayloadFrontendBudgetError) as caught:
                # Load the hostile packet.
                budget.load_request_packet(path, self.repo)
            # Require the caller-owned path to stay private.
            self.assertNotIn(str(path), str(caught.exception))
            # Require no Python parser exception type to escape in text.
            self.assertNotIn("RecursionError", str(caught.exception))
            # Require no integer-parser detail to escape in text.
            self.assertNotIn("digits", str(caught.exception))

    # Prove CLI diagnostics never reflect arguments, paths, or tracebacks.
    def test_cli_failure_is_one_fixed_value_free_line(self):
        # Define one sentinel caller-controlled path.
        sentinel = "SECRET_CALLER_PATH"
        # Capture standard output.
        stdout = io.StringIO()
        # Capture standard error.
        stderr = io.StringIO()
        # Redirect both governed channels.
        with mock.patch.object(budget.sys, "stdout", stdout), mock.patch.object(budget.sys, "stderr", stderr):
            # Run with an invalid relative input.
            status = budget.main(
                [
                    "--json-evidence",  # Select the hostile JSON path.
                    sentinel,  # Supply the private JSON sentinel.
                    "--mysql-evidence",  # Select the hostile MySQL path.
                    sentinel,  # Supply the private MySQL sentinel.
                    "--output",  # Select the hostile output path.
                    sentinel,  # Supply the private output sentinel.
                ]
            )
        # Require one fixed nonzero status.
        self.assertEqual(status, 1)
        # Require no success output.
        self.assertEqual(stdout.getvalue(), "")
        # Require one exact fixed failure line.
        self.assertEqual(stderr.getvalue(), budget.CLI_FAILURE + "\n")
        # Require no caller sentinel.
        self.assertNotIn(sentinel, stderr.getvalue())
        # Require no traceback marker.
        self.assertNotIn("Traceback", stderr.getvalue())

    # Prove source policy excludes runtime, network, browser, server, and target selectors.
    def test_source_policy_is_git_only_and_has_no_runtime_or_network_surface(self):
        # Resolve the exact module source file.
        source_path = Path(budget.__file__)
        # Read the governed source as UTF-8.
        source = source_path.read_text(encoding="utf-8")
        # Parse the full module syntax tree.
        tree = ast.parse(source)
        # Collect every direct import root.
        imports = {
            alias.name.split(".", 1)[0]  # Retain only each import root.
            for node in ast.walk(tree)  # Inspect the full syntax tree.
            if isinstance(node, ast.Import)  # Select direct imports.
            for alias in node.names  # Enumerate each imported name.
        }
        # Collect every from-import root.
        imports.update(
            node.module.split(".", 1)[0]  # Retain only each module root.
            for node in ast.walk(tree)  # Inspect the full syntax tree.
            if isinstance(node, ast.ImportFrom) and node.module  # Select valid from-imports.
        )
        # Define forbidden runtime and transport imports.
        forbidden_imports = {
            "casino",  # Reject application runtime imports.
            "socket",  # Reject listener and transport imports.
            "requests",  # Reject HTTP client imports.
            "urllib",  # Reject standard URL client imports.
            "http",  # Reject standard HTTP imports.
            "playwright",  # Reject browser automation imports.
            "selenium",  # Reject alternate browser automation.
            "gunicorn",  # Reject server topology imports.
        }
        # Require no forbidden import root.
        self.assertTrue(imports.isdisjoint(forbidden_imports))
        # Build the fixed parser.
        parser = budget._parser()
        # Collect only configured option strings.
        options = {
            option  # Retain one long option.
            for action in parser._actions  # Inspect parser actions.
            for option in action.option_strings  # Inspect each option spelling.
            if option.startswith("--")  # Retain only governed long options.
        }
        # Require exactly the three caller-owned file selectors plus ordinary help.
        self.assertEqual(options, {"--help", "--json-evidence", "--mysql-evidence", "--output"})
        # Require no emitted topology field.
        self.assertNotIn("topology", budget.OUTPUT_KEYS)
        # Require no false topology measurement language in schema keys.
        self.assertNotIn("workers", budget.OUTPUT_KEYS)
        # Require the Git boundary to be the only subprocess call site.
        subprocess_calls = [
            node  # Retain one subprocess call.
            for node in ast.walk(tree)  # Inspect the full syntax tree.
            if isinstance(node, ast.Call)  # Select function calls.
            and isinstance(node.func, ast.Attribute)  # Select attribute calls.
            and isinstance(node.func.value, ast.Name)  # Select named modules.
            and node.func.value.id == "subprocess"  # Select the subprocess module.
        ]
        # Require one fixed local subprocess invocation.
        self.assertEqual(len(subprocess_calls), 1)
        # Require the exact read-only metadata verb allowlist.
        self.assertEqual(
            budget.GIT_VERBS,  # Read the runtime-enforced verb set.
            {"rev-parse", "status", "ls-files", "ls-tree", "cat-file"},  # Require metadata verbs only.
        )
        # Collect every internal Git helper call.
        git_calls = [
            node  # Retain one internal call.
            for node in ast.walk(tree)  # Inspect the full syntax tree.
            if isinstance(node, ast.Call)  # Select function calls.
            and isinstance(node.func, ast.Name)  # Select direct helper calls.
            and node.func.id == "_git"  # Select only the Git wrapper.
        ]
        # Retain the statically fixed first verb at each call site.
        callsite_verbs = set()
        # Inspect every internal call.
        for call in git_calls:
            # Require root and one literal argument list.
            self.assertGreaterEqual(len(call.args), 2)
            # Read the Git argument expression.
            arguments = call.args[1]
            # Require a literal list so no dynamic verb can be injected.
            self.assertIsInstance(arguments, ast.List)
            # Require at least one fixed element.
            self.assertTrue(arguments.elts)
            # Read the first fixed verb node.
            verb = arguments.elts[0]
            # Require one string constant verb.
            self.assertIsInstance(verb, ast.Constant)
            # Retain the governed verb.
            callsite_verbs.add(verb.value)
        # Require every current call site to stay within the exact allowlist.
        self.assertEqual(callsite_verbs, set(budget.GIT_VERBS))
        # Resolve one real immutable blob identity for exact-shape execution.
        blob = _git(self.repo, "rev-parse", "HEAD:web/app.js").decode("ascii").strip().lower()
        # Define all six exact approved argument shapes.
        allowed_shapes = (
            ["rev-parse", "HEAD"],  # Resolve exact HEAD.
            ["rev-parse", f"{self.head}^{{tree}}"],  # Resolve the exact commit tree.
            ["status", "--porcelain=v1", "-z", "--untracked-files=all"],  # Inspect complete dirt.
            ["ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--", "web"],  # Inspect ignored web files.
            ["ls-tree", "-r", "-z", "--full-tree", self.head, "--", "web"],  # Inspect the immutable web tree.
            ["cat-file", "blob", blob],  # Read one immutable asset blob.
        )
        # Exercise every approved command through the real wrapper.
        for arguments in allowed_shapes:
            # Identify the exact argument shape.
            with self.subTest(allowed=arguments[0:2]):
                # Require runtime policy approval.
                self.assertTrue(budget._git_arguments_allowed(arguments))
                # Require the real local query to execute.
                self.assertIsInstance(budget._git(self.repo, arguments), bytes)
        # Define representative malformed, option-injected, and network-capable shapes.
        forbidden_shapes = (
            ["fetch", "https://example.invalid/production"],  # Reject a network verb.
            ["remote", "-v"],  # Reject remote metadata.
            ["rev-parse"],  # Reject a missing source selector.
            ["rev-parse", "--show-toplevel"],  # Reject alternate rev-parse options.
            ["rev-parse", f"{self.head}^{{tree}}", "extra"],  # Reject an extra tree argument.
            ["rev-parse", f"{self.head.upper()}^{{tree}}"],  # Reject non-lowercase object identity.
            ["status"],  # Reject a weaker dirt query.
            ["status", "--porcelain=v2", "-z", "--untracked-files=all"],  # Reject alternate status format.
            ["ls-files", "--others", "--", "web"],  # Reject missing ignored-file guards.
            ["ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--", "https://example.invalid"],  # Reject URL pathspec.
            ["ls-tree", "-r", "-z", "--full-tree", self.head, "--", "https://example.invalid"],  # Reject URL tree target.
            ["ls-tree", "-r", "-z", "--full-tree", "a" * 39, "--", "web"],  # Reject abbreviated object identity.
            ["cat-file", "--batch"],  # Reject alternate cat-file mode.
            ["cat-file", "blob", "https://example.invalid"],  # Reject URL object selector.
            ["cat-file", "blob", blob, "extra"],  # Reject extra blob arguments.
        )
        # Reject every alternate shape before subprocess launch.
        for arguments in forbidden_shapes:
            # Identify each forbidden shape.
            with self.subTest(forbidden=arguments[0:2]):
                # Require runtime policy rejection.
                self.assertFalse(budget._git_arguments_allowed(arguments))
                # Require a fixed pre-launch rejection.
                with self.assertRaises(budget.PayloadFrontendBudgetError):
                    # Attempt the forbidden local Git operation.
                    budget._git(self.repo, arguments)

    # Prove the sole Git child is network-inert and caller environment cannot override it.
    def test_git_child_receives_only_fixed_no_network_environment(self):
        # Define hostile inherited Git, remote, provider, and proxy capabilities.
        hostile_environment = {
            "GIT_NO_LAZY_FETCH": "0",  # Attempt to re-enable promisor fetch.
            "GIT_NO_REPLACE_OBJECTS": "0",  # Attempt to enable replacement objects.
            "GIT_TERMINAL_PROMPT": "1",  # Attempt to re-enable prompts.
            "GIT_SSH_COMMAND": "SECRET_REMOTE_COMMAND",  # Attempt to add an SSH transport.
            "GIT_ASKPASS": "SECRET_ASKPASS",  # Attempt to add a credential helper.
            "GIT_DIR": "SECRET_REDIRECT_DIR",  # Attempt to redirect repository metadata.
            "GIT_WORK_TREE": "SECRET_REDIRECT_TREE",  # Attempt to redirect the worktree.
            "GIT_INDEX_FILE": "SECRET_REDIRECT_INDEX",  # Attempt to redirect the index.
            "GIT_OBJECT_DIRECTORY": "SECRET_REDIRECT_OBJECTS",  # Attempt to redirect objects.
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": "SECRET_ALTERNATES",  # Attempt alternate objects.
            "GIT_CONFIG_COUNT": "99",  # Attempt caller config injection.
            "GIT_CONFIG_KEY_1": "core.fsmonitor",  # Attempt daemon configuration.
            "GIT_CONFIG_VALUE_1": "SECRET_DAEMON",  # Attempt a daemon command.
            "HTTPS_PROXY": "https://secret.invalid",  # Attempt to add a network proxy.
            "CASINO_MYSQL_PASSWORD": "SECRET_PROVIDER",  # Attempt to expose provider credentials.
        }
        # Build one successful fixed subprocess result.
        result = mock.Mock(returncode=0, stdout=(self.head + "\n").encode("ascii"))
        # Inject hostile caller environment values.
        with mock.patch.dict(budget.os.environ, hostile_environment, clear=False):
            # Intercept the sole process boundary.
            with mock.patch.object(budget.subprocess, "run", return_value=result) as run_call:
                # Execute one approved exact source query.
                output = budget._git(self.repo, ["rev-parse", "HEAD"])
        # Require the fixed subprocess bytes to return internally.
        self.assertEqual(output, result.stdout)
        # Require exactly one process launch.
        run_call.assert_called_once()
        # Read the exact subprocess keyword arguments.
        keyword_arguments = run_call.call_args.kwargs
        # Read the sanitized child environment.
        child_environment = keyword_arguments["env"]
        # Require every fixed Git hardening value to override hostile input.
        self.assertEqual(
            {key: child_environment[key] for key in budget.GIT_FIXED_ENVIRONMENT},
            budget.GIT_FIXED_ENVIRONMENT,
        )
        # Require no hostile remote/provider/proxy capability to survive.
        for forbidden_key in (
            "GIT_SSH_COMMAND",  # Reject caller SSH transport.
            "GIT_ASKPASS",  # Reject caller prompt helper.
            "GIT_DIR",  # Reject metadata redirection.
            "GIT_WORK_TREE",  # Reject worktree redirection.
            "GIT_INDEX_FILE",  # Reject index redirection.
            "GIT_OBJECT_DIRECTORY",  # Reject object redirection.
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",  # Reject alternate objects.
            "GIT_CONFIG_KEY_1",  # Reject extra caller configuration.
            "GIT_CONFIG_VALUE_1",  # Reject extra caller configuration values.
            "HTTPS_PROXY",  # Reject caller network proxy.
            "CASINO_MYSQL_PASSWORD",  # Reject provider credentials.
        ):
            # Confirm the hostile capability is absent.
            self.assertNotIn(forbidden_key, child_environment)
        # Build the exact allowed environment key set for this host.
        expected_keys = set(budget.GIT_FIXED_ENVIRONMENT) | {
            key  # Retain one present OS execution key.
            for key in budget.GIT_OS_ENVIRONMENT_KEYS  # Inspect the fixed OS allowlist.
            if isinstance(budget.os.environ.get(key), str)  # Retain only present string values.
        }
        # Require no caller environment key beyond the exact allowlist.
        self.assertEqual(set(child_environment), expected_keys)
        # Require the process command to contain only Git plus the approved argument shape.
        self.assertEqual(run_call.call_args.args[0], ["git", "rev-parse", "HEAD"])
        # Require no shell execution.
        self.assertNotIn("shell", keyword_arguments)
        # Poison the parent environment again for one real local query.
        with mock.patch.dict(budget.os.environ, hostile_environment, clear=False):
            # Require exact checkout resolution despite every redirect attempt.
            self.assertEqual(budget.checkout_head(self.repo), self.head)

    # Prove source mismatch and tree dirt fail before evidence consumption.
    def test_build_rejects_source_mismatch_and_dirty_tree(self):
        # Resolve external packet paths.
        json_path = self.external / "json.json"
        # Resolve the MySQL packet path.
        mysql_path = self.external / "mysql.json"
        # Write a stale JSON packet.
        _write_packet(json_path, _request_packet("json", "c" * 40))
        # Write a current MySQL packet.
        _write_packet(mysql_path, _request_packet("mysql", self.head))
        # Require mixed-head rejection.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Build from the incompatible packets.
            budget.build_evidence(json_path, mysql_path, self.repo)
        # Replace the JSON packet with exact source.
        _write_packet(json_path, _request_packet("json", self.head))
        # Dirty the analyzed tree after packet generation.
        (self.repo / "DIRTY").write_text("dirty", encoding="utf-8")
        # Require dirty-tree rejection before output.
        with self.assertRaises(budget.PayloadFrontendBudgetError):
            # Build against the dirty checkout.
            budget.build_evidence(json_path, mysql_path, self.repo)

    # Prove mid-analysis non-asset dirt invalidates the initial clean snapshot.
    def test_build_rejects_mid_analysis_dirty_tree(self):
        # Resolve external packet paths.
        json_path = self.external / "json.json"
        # Resolve the MySQL packet path.
        mysql_path = self.external / "mysql.json"
        # Write the exact JSON provider packet.
        _write_packet(json_path, _request_packet("json", self.head))
        # Write the exact MySQL provider packet.
        _write_packet(mysql_path, _request_packet("mysql", self.head))
        # Retain the real asset analysis function.
        real_asset_rows = budget._asset_rows

        # Introduce one non-asset mutation after verified asset construction.
        def dirty_after_assets(root: Path, source_commit: str) -> list[dict]:
            # Complete the real Git-backed asset analysis first.
            rows = real_asset_rows(root, source_commit)
            # Add one untracked tool-shaped file after the initial clean guard.
            (root / "MID_ANALYSIS_DIRT").write_text("dirty", encoding="utf-8")
            # Return the otherwise valid aggregate.
            return rows

        # Replace only the asset-return boundary to inject the concurrent mutation.
        with mock.patch.object(budget, "_asset_rows", side_effect=dirty_after_assets):
            # Require the final clean-tree guard to reject the evidence.
            with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^analyzed checkout is dirty$"):
                # Attempt a complete build.
                budget.build_evidence(json_path, mysql_path, self.repo)
        # Require no output document to have been created.
        self.assertEqual(list(self.external.glob("payload*.json")), [])

    # Prove a mid-analysis commit invalidates the initial immutable HEAD.
    def test_build_rejects_mid_analysis_head_change(self):
        # Resolve external packet paths.
        json_path = self.external / "json.json"
        # Resolve the MySQL packet path.
        mysql_path = self.external / "mysql.json"
        # Write the exact JSON provider packet.
        _write_packet(json_path, _request_packet("json", self.head))
        # Write the exact MySQL provider packet.
        _write_packet(mysql_path, _request_packet("mysql", self.head))
        # Retain the real asset analysis function.
        real_asset_rows = budget._asset_rows

        # Commit one concurrent non-asset change after asset construction.
        def commit_after_assets(root: Path, source_commit: str) -> list[dict]:
            # Complete the real Git-backed asset analysis first.
            rows = real_asset_rows(root, source_commit)
            # Create one tracked concurrent-change fixture.
            (root / "CONCURRENT").write_text("changed", encoding="utf-8")
            # Stage the concurrent change.
            _git(root, "add", "CONCURRENT")
            # Commit the new HEAD.
            _git(root, "commit", "--quiet", "-m", "concurrent")
            # Return the old-tree aggregate.
            return rows

        # Replace only the asset-return boundary to inject the concurrent commit.
        with mock.patch.object(budget, "_asset_rows", side_effect=commit_after_assets):
            # Require the final exact-head guard to reject the evidence.
            with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^analyzed checkout changed$"):
                # Attempt a complete build.
                budget.build_evidence(json_path, mysql_path, self.repo)
        # Require no output document to have been created.
        self.assertEqual(list(self.external.glob("payload*.json")), [])

    # Prove a late mutation after temp fsync prevents replacement and removes residue.
    def test_write_rechecks_provenance_immediately_before_replace(self):
        # Resolve external packet paths.
        json_path = self.external / "json.json"
        # Resolve the MySQL packet path.
        mysql_path = self.external / "mysql.json"
        # Write the exact JSON provider packet.
        _write_packet(json_path, _request_packet("json", self.head))
        # Write the exact MySQL provider packet.
        _write_packet(mysql_path, _request_packet("mysql", self.head))
        # Build the valid evidence while the tree is clean.
        evidence = budget.build_evidence(json_path, mysql_path, self.repo)
        # Resolve one external destination.
        output = self.external / "payload.json"
        # Seed byte-exact caller content.
        output.write_bytes(b"retained-before-late-dirt")
        # Retain the real durability operation.
        real_fsync = budget.os.fsync

        # Add one concurrent mutation immediately after durable temp write.
        def fsync_then_dirty(descriptor: int) -> None:
            # Flush the real descriptor first.
            real_fsync(descriptor)
            # Dirty the analyzed checkout before replacement.
            (self.repo / "LATE_DIRT").write_text("dirty", encoding="utf-8")

        # Inject the late mutation at the exact pre-replacement boundary.
        with mock.patch.object(budget.os, "fsync", side_effect=fsync_then_dirty):
            # Require the final provenance guard to reject the write.
            with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^analyzed checkout is dirty$"):
                # Attempt the atomic replacement.
                budget.write_evidence_atomic(output, evidence, self.repo)
        # Require prior caller content to remain exact.
        self.assertEqual(output.read_bytes(), b"retained-before-late-dirt")
        # Require every owned temporary file to be removed.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])

    # Prove stale-source and pre-existing dirt fail before output or temp touch.
    def test_write_binds_source_and_clean_tree_before_destination_touch(self):
        # Resolve one external destination.
        output = self.external / "payload.json"
        # Seed byte-exact caller content.
        output.write_bytes(b"retained-before-source-guard")
        # Build one structurally valid document bound to a stale commit.
        stale = _valid_output("d" * 40)
        # Require stale-head rejection.
        with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^analyzed checkout changed$"):
            # Attempt the stale write.
            budget.write_evidence_atomic(output, stale, self.repo)
        # Require prior caller content to remain exact.
        self.assertEqual(output.read_bytes(), b"retained-before-source-guard")
        # Require no temporary allocation.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])
        # Build one structurally valid document bound to current HEAD.
        current = _valid_output(self.head)
        # Dirty the checkout before invoking the writer.
        (self.repo / "PREEXISTING_DIRT").write_text("dirty", encoding="utf-8")
        # Require clean-tree rejection.
        with self.assertRaisesRegex(budget.PayloadFrontendBudgetError, "^analyzed checkout is dirty$"):
            # Attempt the dirty-tree write.
            budget.write_evidence_atomic(output, current, self.repo)
        # Require prior caller content to remain exact again.
        self.assertEqual(output.read_bytes(), b"retained-before-source-guard")
        # Require no temporary allocation after dirty-tree rejection.
        self.assertEqual(list(self.external.glob(f"{budget.TEMPORARY_PREFIX}*.tmp")), [])


# Execute the focused suite directly when requested.
if __name__ == "__main__":
    # Delegate status to unittest without adding a custom runner.
    unittest.main()
