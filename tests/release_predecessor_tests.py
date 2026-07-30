"""Listener-free tests for compatibility-owned immutable predecessor selection."""

# Import JSON serialization for synthetic compatibility and manifest records.
import json
# Import SHA-256 hashing for exact synthetic manifest identity pins.
import hashlib
# Import temporary directories for repository-independent fixtures.
import tempfile
# Import unittest for dependency-free policy evidence.
import unittest
# Import paths for synthetic repository construction.
from pathlib import Path

# Import the tracked resolver under test.
from scripts import resolve_release_predecessor


# Prove rollback selection comes only from the current compatibility record.
class ReleasePredecessorTests(unittest.TestCase):
    # Create an isolated repository-shaped fixture for every test.
    def setUp(self):
        # Own the temporary directory for the complete test lifetime.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve its path once for concise fixture helpers.
        self.root = Path(self.temporary.name)
        # Create the canonical compatibility directory.
        (self.root / "contracts" / "compatibility").mkdir(parents=True)
        # Create the canonical migration catalog directory.
        (self.root / "migrations" / "mysql").mkdir(parents=True)
        # Write the bridge runtime window and held application policy.
        self.write_json("migrations/mysql/catalog.json", {"schema": "casino-mysql-migration-catalog-v1", "minimum_runtime_version": 2, "expected_version": 3, "apply_policy": "held", "migrations": []})
        # Write the candidate release declaration.
        self.write_json(
            "contracts/compatibility/app-0.9.5.40.json",
            {
                "app_version": "0.9.5.40",
                "rollback": {"scope": "application-only", "database_rollback": "prohibited", "mysql_expected_schema_version": 2, "requires_retained_predecessor_manifest": True},
                "predecessor": {
                    "app_version": "0.9.5.39",
                    "compatibility_record": "contracts/compatibility/app-0.9.5.39.json",
                    "required_artifact": "release-manifest.json",
                    "source_commit_sha": "9" * 40,
                    "artifact_sha256": "8" * 64,
                    "manifest_sha256": "",
                },
            },
        )
        # Write the retained predecessor compatibility record.
        self.write_json("contracts/compatibility/app-0.9.5.39.json", {"app_version": "0.9.5.39"})

    # Remove the isolated fixture after every assertion.
    def tearDown(self):
        # Delegate cleanup to TemporaryDirectory.
        self.temporary.cleanup()

    # Write one canonical fixture object.
    def write_json(self, relative: str, value: dict) -> Path:
        # Resolve the fixture path beneath the isolated root.
        path = self.root / relative
        # Write stable JSON bytes for the resolver.
        path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")
        # Return the path for manifest-focused assertions.
        return path

    # Prove the exact retained tag is derived from repository policy.
    def test_resolves_declared_predecessor_tag(self):
        # Pin a syntactically valid manifest digest for resolution-only evidence.
        self.pin_manifest_digest("7" * 64)
        # Resolve the candidate's governed predecessor.
        tag = resolve_release_predecessor.predecessor_tag("0.9.5.40", self.root)
        # Require the retained v0.9.5.39 tag rather than release-list ordering.
        self.assertEqual(tag, "v0.9.5.39")

    # Prove predecessor selection requires the exact no-database-rollback policy tuple.
    def test_rejects_candidate_rollback_policy_drift(self):
        # Resolve and parse the canonical candidate fixture.
        path = self.root / "contracts" / "compatibility" / "app-0.9.5.40.json"
        # Capture the unmodified candidate once.
        baseline = json.loads(path.read_text(encoding="utf-8"))
        # Exercise scope, database authority, retained-manifest, and extra-field drift.
        mutations = (
            # Broaden rollback scope.
            ("scope", "database-and-application"),
            # Permit database rollback.
            ("database_rollback", "permitted"),
            # Waive the retained manifest.
            ("requires_retained_predecessor_manifest", False),
            # Add an unreviewed shadow policy field.
            ("waiver", True),
        )
        # Require every policy mutation to fail before tag selection.
        for field, value in mutations:
            # Copy the complete candidate fixture.
            candidate = json.loads(json.dumps(baseline))
            # Apply exactly one rollback mutation.
            candidate["rollback"][field] = value
            # Persist the hostile candidate policy.
            path.write_text(json.dumps(candidate) + "\n", encoding="utf-8", newline="\n")
            # Require fixed policy refusal.
            with self.subTest(field=field), self.assertRaises(ValueError):
                # Resolve through the public predecessor boundary.
                resolve_release_predecessor.predecessor_tag("0.9.5.40", self.root)
        # Restore the exact baseline for teardown-independent clarity.
        path.write_text(json.dumps(baseline) + "\n", encoding="utf-8", newline="\n")

    # Prove redirected compatibility paths fail closed.
    def test_rejects_redirected_predecessor_record(self):
        # Replace the candidate with a path that does not match its predecessor version.
        self.write_json(
            "contracts/compatibility/app-0.9.5.40.json",
            {
                "app_version": "0.9.5.40",
                "rollback": {"scope": "application-only", "database_rollback": "prohibited", "mysql_expected_schema_version": 2, "requires_retained_predecessor_manifest": True},
                "predecessor": {
                    "app_version": "0.9.5.39",
                    "compatibility_record": "contracts/compatibility/app-0.9.5.11.json",
                    "required_artifact": "release-manifest.json",
                    "source_commit_sha": "9" * 40,
                    "artifact_sha256": "8" * 64,
                    "manifest_sha256": "7" * 64,
                },
            },
        )
        # Require resolution to reject the redirected policy input.
        with self.assertRaises(ValueError):
            # Execute the exact public resolver.
            resolve_release_predecessor.predecessor_tag("0.9.5.40", self.root)

    # Prove downloaded manifests must bind the declared version, tag, and full commit.
    def test_verifies_exact_downloaded_manifest(self):
        # Write a checksum-bound predecessor manifest shape.
        manifest = self.write_json(
            "previous-manifest.json",
            {
                "app_version": "0.9.5.39",
                "source": {
                    "release_tag": "v0.9.5.39",
                    "commit_sha": "9" * 40,
                },
                "artifact": {
                    "name": "virtual_casino_simulator_package.zip",
                    "sha256": "8" * 64,
                },
                "mysql_schema": {"minimum_version": 2, "expected_version": 3, "apply_policy": "held"},
            },
        )
        # Pin the exact synthetic manifest bytes in the candidate policy.
        self.pin_manifest_digest(hashlib.sha256(manifest.read_bytes()).hexdigest())
        # Verify the manifest against the candidate compatibility record.
        tag = resolve_release_predecessor.verify_manifest("0.9.5.40", manifest, self.root)
        # Require the same immutable retained tag.
        self.assertEqual(tag, "v0.9.5.39")

    # Prove a same-version manifest under another tag cannot be substituted.
    def test_rejects_cross_tag_manifest(self):
        # Write a manifest whose version is right but immutable tag is wrong.
        manifest = self.write_json(
            "previous-manifest.json",
            {
                "app_version": "0.9.5.39",
                "source": {
                    "release_tag": "v9.5.39",
                    "commit_sha": "9" * 40,
                },
                "artifact": {
                    "name": "virtual_casino_simulator_package.zip",
                    "sha256": "8" * 64,
                },
                "mysql_schema": {"minimum_version": 2, "expected_version": 3, "apply_policy": "held"},
            },
        )
        # Pin the exact synthetic bytes so only the wrong tag causes rejection.
        self.pin_manifest_digest(hashlib.sha256(manifest.read_bytes()).hexdigest())
        # Require the verifier to reject cross-tag substitution.
        with self.assertRaises(ValueError):
            # Exercise the exact public verifier.
            resolve_release_predecessor.verify_manifest("0.9.5.40", manifest, self.root)

    # Prove exact schema three cannot roll back to an exact-schema-two predecessor.
    def test_rejects_schema_three_to_exact_schema_two_predecessor(self):
        # Read the candidate declaration.
        candidate_path = self.root / "contracts" / "compatibility" / "app-0.9.5.40.json"
        # Parse the complete candidate policy.
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        # Declare database schema three at the rollback boundary.
        candidate["rollback"]["mysql_expected_schema_version"] = 3
        # Persist the candidate policy.
        candidate_path.write_text(json.dumps(candidate) + "\n", encoding="utf-8", newline="\n")
        # Write an exact-schema-two predecessor manifest.
        manifest = self.write_json("previous-manifest.json", {"app_version": "0.9.5.39", "source": {"release_tag": "v0.9.5.39", "commit_sha": "9" * 40}, "artifact": {"name": "virtual_casino_simulator_package.zip", "sha256": "8" * 64}, "mysql_schema": {"minimum_version": 2, "expected_version": 2}})
        # Pin the exact manifest bytes after writing.
        self.pin_manifest_digest(hashlib.sha256(manifest.read_bytes()).hexdigest())
        # Require the cross-window rollback to fail closed.
        with self.assertRaisesRegex(ValueError, "rollback schema is incompatible"):
            # Verify the exact retained predecessor.
            resolve_release_predecessor.verify_manifest("0.9.5.40", manifest, self.root)

    # Prove a future exact-schema-three release may roll back to the bridge window.
    def test_future_schema_three_candidate_accepts_bridge_predecessor(self):
        # Replace the candidate catalog with an exact-schema-three runtime window.
        self.write_json("migrations/mysql/catalog.json", {"schema": "casino-mysql-migration-catalog-v1", "minimum_runtime_version": 3, "expected_version": 3, "apply_policy": "held", "migrations": []})
        # Write the future candidate declaration pointing to the bridge predecessor.
        self.write_json("contracts/compatibility/app-0.9.5.41.json", {"app_version": "0.9.5.41", "rollback": {"scope": "application-only", "database_rollback": "prohibited", "mysql_expected_schema_version": 3, "requires_retained_predecessor_manifest": True}, "predecessor": {"app_version": "0.9.5.40", "compatibility_record": "contracts/compatibility/app-0.9.5.40.json", "required_artifact": "release-manifest.json", "source_commit_sha": "9" * 40, "artifact_sha256": "8" * 64, "manifest_sha256": ""}})
        # Write the bridge predecessor compatibility identity.
        self.write_json("contracts/compatibility/app-0.9.5.40.json", {"app_version": "0.9.5.40"})
        # Write a predecessor manifest whose runtime accepts schema three.
        manifest = self.write_json("bridge-manifest.json", {"app_version": "0.9.5.40", "source": {"release_tag": "v0.9.5.40", "commit_sha": "9" * 40}, "artifact": {"name": "virtual_casino_simulator_package.zip", "sha256": "8" * 64}, "mysql_schema": {"minimum_version": 2, "expected_version": 3, "apply_policy": "held"}})
        # Bind the exact manifest digest into future compatibility.
        future_path = self.root / "contracts" / "compatibility" / "app-0.9.5.41.json"
        # Parse the future candidate record.
        future = json.loads(future_path.read_text(encoding="utf-8"))
        # Pin exact predecessor bytes.
        future["predecessor"]["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        # Persist the completed candidate policy.
        future_path.write_text(json.dumps(future) + "\n", encoding="utf-8", newline="\n")
        # Require exact-schema-three rollback into the bridge runtime to be accepted.
        self.assertEqual(resolve_release_predecessor.verify_manifest("0.9.5.41", manifest, self.root), "v0.9.5.40")

    # Update only the synthetic candidate's retained manifest checksum.
    def pin_manifest_digest(self, digest: str) -> None:
        # Resolve the candidate compatibility record.
        path = self.root / "contracts" / "compatibility" / "app-0.9.5.40.json"
        # Parse its current fixture content.
        value = json.loads(path.read_text(encoding="utf-8"))
        # Replace only the manifest identity pin.
        value["predecessor"]["manifest_sha256"] = digest
        # Persist stable JSON bytes.
        path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")


# Run focused evidence directly for release validation.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
