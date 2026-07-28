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
        # Write the candidate release declaration.
        self.write_json(
            "contracts/compatibility/app-0.9.5.26.json",
            {
                "app_version": "0.9.5.26",
                "predecessor": {
                    "app_version": "0.9.5.25",
                    "compatibility_record": "contracts/compatibility/app-0.9.5.25.json",
                    "required_artifact": "release-manifest.json",
                    "source_commit_sha": "9" * 40,
                    "artifact_sha256": "8" * 64,
                    "manifest_sha256": "",
                },
            },
        )
        # Write the retained predecessor compatibility record.
        self.write_json("contracts/compatibility/app-0.9.5.25.json", {"app_version": "0.9.5.25"})

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
        tag = resolve_release_predecessor.predecessor_tag("0.9.5.26", self.root)
        # Require the retained v0.9.5.25 tag rather than release-list ordering.
        self.assertEqual(tag, "v0.9.5.25")

    # Prove redirected compatibility paths fail closed.
    def test_rejects_redirected_predecessor_record(self):
        # Replace the candidate with a path that does not match its predecessor version.
        self.write_json(
            "contracts/compatibility/app-0.9.5.26.json",
            {
                "app_version": "0.9.5.26",
                "predecessor": {
                    "app_version": "0.9.5.25",
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
            resolve_release_predecessor.predecessor_tag("0.9.5.26", self.root)

    # Prove downloaded manifests must bind the declared version, tag, and full commit.
    def test_verifies_exact_downloaded_manifest(self):
        # Write a checksum-bound predecessor manifest shape.
        manifest = self.write_json(
            "previous-manifest.json",
            {
                "app_version": "0.9.5.25",
                "source": {
                    "release_tag": "v0.9.5.25",
                    "commit_sha": "9" * 40,
                },
                "artifact": {
                    "name": "virtual_casino_simulator_package.zip",
                    "sha256": "8" * 64,
                },
            },
        )
        # Pin the exact synthetic manifest bytes in the candidate policy.
        self.pin_manifest_digest(hashlib.sha256(manifest.read_bytes()).hexdigest())
        # Verify the manifest against the candidate compatibility record.
        tag = resolve_release_predecessor.verify_manifest("0.9.5.26", manifest, self.root)
        # Require the same immutable retained tag.
        self.assertEqual(tag, "v0.9.5.25")

    # Prove a same-version manifest under another tag cannot be substituted.
    def test_rejects_cross_tag_manifest(self):
        # Write a manifest whose version is right but immutable tag is wrong.
        manifest = self.write_json(
            "previous-manifest.json",
            {
                "app_version": "0.9.5.25",
                "source": {
                    "release_tag": "v9.5.25",
                    "commit_sha": "9" * 40,
                },
                "artifact": {
                    "name": "virtual_casino_simulator_package.zip",
                    "sha256": "8" * 64,
                },
            },
        )
        # Pin the exact synthetic bytes so only the wrong tag causes rejection.
        self.pin_manifest_digest(hashlib.sha256(manifest.read_bytes()).hexdigest())
        # Require the verifier to reject cross-tag substitution.
        with self.assertRaises(ValueError):
            # Exercise the exact public verifier.
            resolve_release_predecessor.verify_manifest("0.9.5.26", manifest, self.root)

    # Update only the synthetic candidate's retained manifest checksum.
    def pin_manifest_digest(self, digest: str) -> None:
        # Resolve the candidate compatibility record.
        path = self.root / "contracts" / "compatibility" / "app-0.9.5.26.json"
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
