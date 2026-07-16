"""Focused TOOL-003 tests for deterministic release and rollback provenance."""

# Import JSON support for fixture manifests and provenance assertions.
import json
# Import portable paths for disposable release source trees.
import pathlib
# Import temporary directory support so tests never touch user runtime data.
import tempfile
# Import unittest for repository-standard focused test execution.
import unittest
# Import ZIP inspection for negative private-content assertions.
import zipfile

# Import the release implementation under test from the repository scripts namespace.
from scripts import package_app


# Exercise deterministic packaging, exclusion, verification, and rollback behavior.
class ReleaseArtifactTests(unittest.TestCase):
    # Create one minimal clean application source tree before each test.
    def setUp(self):
        # Allocate a disposable filesystem root owned only by this test.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-release-test-")
        # Register cleanup immediately so failed assertions cannot retain fixture files.
        self.addCleanup(self.temporary.cleanup)
        # Resolve the fixture repository root beneath the disposable directory.
        self.root = pathlib.Path(self.temporary.name) / "source"
        # Create the fixture root before writing canonical source files.
        self.root.mkdir(parents=True)
        # Define the minimal required tracked application file inventory.
        self.files = {
            "ARCHITECTURE.md": "# Architecture\n",
            "LICENSE": "Test license\n",
            "NOTICE": "Test notice\n",
            "README.md": "# Fixture\n",
            "RELEASE_NOTES.md": "# Release\n",
            "casino/__init__.py": "\"\"\"Fixture package.\"\"\"\n",
            "casino/app.py": "\"\"\"Fixture app.\"\"\"\n\ndef main():\n    # Return without starting a listener.\n    return None\n",
            "casino/config.py": "\"\"\"Fixture config.\"\"\"\n\n# Expose the canonical fixture release.\nAPP_VERSION = \"9.2.0\"\n",
            "contracts/compatibility/app-9.2.0.json": "{\"app_version\": \"9.2.0\"}\n",
            "modules/module-manifest.json": json.dumps({"application": "9.2.0", "source_baseline": "9.1.0", "modules": {"tooling": "1.7.0"}}) + "\n",
            "pyproject.toml": "[project]\nname = \"virtual-casino-simulator\"\nversion = \"9.2.0\"\nrequires-python = \">=3.10\"\n\n[project.optional-dependencies]\nmysql = [\"mysql-connector-python>=8.4\"]\n",
            "run.py": "# Import the fixture application entry point.\nfrom casino.app import main\n",
            "scripts/mysql_schema.sql": "-- Fixture schema.\n",
            "web/app.js": "// Fixture static application bundle.\n",
            "web/index.html": "<!doctype html><title>Fixture</title>\n",
        }
        # Write every fixture file beneath its canonical repository-relative path.
        for relative_path, contents in self.files.items():
            # Resolve the current fixture file without using host-specific paths in data.
            target = self.root / pathlib.PurePosixPath(relative_path)
            # Create any required parent directories within the disposable source tree.
            target.parent.mkdir(parents=True, exist_ok=True)
            # Write normalized UTF-8 fixture text.
            target.write_text(contents, encoding="utf-8", newline="\n")
        # Add declared validation dependencies for deterministic SBOM coverage.
        (self.root / "requirements-dev.txt").write_text("pytest>=8.0\n", encoding="utf-8", newline="\n")
        # Use one immutable full source identity across equivalent test builds.
        self.commit_sha = "a" * 40
        # Use one fixed source timestamp across equivalent test builds.
        self.commit_epoch = 1_700_000_000

    # Build a fixture release with optional tag and prior rollback provenance.
    def build(self, output_name, release_tag=None, previous_manifest=None):
        # Resolve an isolated candidate output directory for this build.
        output = pathlib.Path(self.temporary.name) / output_name
        # Build from the explicit tracked fixture inventory rather than filesystem traversal.
        return package_app.build_release(
            self.root,
            output,
            list(self.files),
            self.commit_sha,
            self.commit_epoch,
            release_tag=release_tag,
            validations=["python tests.release_artifact_tests"],
            previous_manifest=previous_manifest,
        )

    # Prove equal clean source inputs yield equal archive and manifest bytes.
    def test_repeated_builds_are_byte_reproducible(self):
        # Build the first candidate from the fixed clean source identity.
        first_archive, first_manifest = self.build("first")
        # Build the equivalent candidate in a different output directory.
        second_archive, second_manifest = self.build("second")
        # Require identical normalized ZIP bytes across output locations.
        self.assertEqual(first_archive.read_bytes(), second_archive.read_bytes())
        # Require identical checksum-bound provenance bytes across output locations.
        self.assertEqual(first_manifest.read_bytes(), second_manifest.read_bytes())

    # Prove untracked private content is never considered by tracked-file packaging.
    def test_untracked_private_content_is_excluded(self):
        # Create a credential-like file that is deliberately absent from the tracked list.
        untracked = self.root / "casino" / ".env"
        # Write a synthetic non-secret sentinel solely inside the disposable fixture.
        untracked.write_text("SYNTHETIC_TEST_ONLY=1\n", encoding="utf-8", newline="\n")
        # Build using only the explicit tracked source paths.
        archive_path, _ = self.build("untracked")
        # Inspect the final member set without extracting it.
        with zipfile.ZipFile(archive_path, "r") as archive:
            # Require the private-looking untracked path to be absent.
            self.assertNotIn("virtual_casino_simulator/casino/.env", archive.namelist())

    # Prove tracked development evidence beneath a runtime root is safely omitted.
    def test_tracked_evidence_directory_is_excluded(self):
        # Define a repository-owned evidence document beneath an allowed application root.
        relative_path = "casino/games/fixture/evidence/README.md"
        # Resolve its disposable fixture path.
        target = self.root / pathlib.PurePosixPath(relative_path)
        # Create the nested evidence directory inside the disposable source tree.
        target.parent.mkdir(parents=True, exist_ok=True)
        # Write a synthetic evidence marker that must not enter the deployable archive.
        target.write_text("# Development evidence only\n", encoding="utf-8", newline="\n")
        # Select release files from the tracked inventory including the evidence path.
        selected = package_app.select_release_files(self.root, [*self.files, relative_path])
        # Require the evidence document to be omitted without weakening credential rejection.
        self.assertNotIn(relative_path, selected)

    # Prove a credential-like tracked path beneath an allowed root fails closed.
    def test_forbidden_tracked_private_content_is_rejected(self):
        # Define a synthetic key-like tracked file under an otherwise allowed runtime root.
        relative_path = "casino/id_ed25519.pem"
        # Resolve its disposable fixture path.
        target = self.root / pathlib.PurePosixPath(relative_path)
        # Write a non-secret sentinel without using real key material.
        target.write_text("SYNTHETIC TEST SENTINEL\n", encoding="utf-8", newline="\n")
        # Require the selector to reject rather than silently omit the suspicious tracked file.
        with self.assertRaisesRegex(ValueError, "credential-like"):
            # Evaluate the full tracked list including the forbidden sentinel.
            package_app.select_release_files(self.root, [*self.files, relative_path])

    # Prove checksum verification detects any post-build archive substitution.
    def test_archive_tampering_is_rejected(self):
        # Build a structurally valid deterministic candidate.
        archive_path, manifest_path = self.build("tamper")
        # Change the archive bytes after the checksum-bound manifest is written.
        archive_path.write_bytes(archive_path.read_bytes() + b"tamper")
        # Require independent verification to fail before extraction or smoke.
        with self.assertRaisesRegex(ValueError, "checksum"):
            # Skip smoke because checksum rejection must occur first.
            package_app.verify_release(archive_path, manifest_path, smoke=False)

    # Prove a retained prior manifest produces testable application rollback mapping.
    def test_previous_manifest_enables_application_rollback(self):
        # Define a complete synthetic prior release identity without external data.
        previous = {
            "app_version": "9.1.1",
            "artifact": {"name": package_app.ARCHIVE_NAME, "sha256": "b" * 64},
            "source": {"commit_sha": "c" * 40},
        }
        # Resolve the retained prior manifest fixture outside candidate output directories.
        previous_path = pathlib.Path(self.temporary.name) / "previous-manifest.json"
        # Write canonical prior JSON bytes for manifest-checksum provenance.
        previous_path.write_text(json.dumps(previous, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # Build a canonical tagged candidate with the retained prior manifest.
        archive_path, manifest_path = self.build("rollback", release_tag="v9.2.0", previous_manifest=previous_path)
        # Verify the artifact with immutable rollback required but without duplicate smoke cost.
        manifest = package_app.verify_release(
            archive_path,
            manifest_path,
            expected_commit=self.commit_sha,
            expected_tag="v9.2.0",
            require_rollback=True,
            smoke=False,
        )
        # Require an eligible application-only mapping to the prior version.
        self.assertTrue(manifest["rollback"]["eligible"])
        # Require database rollback to remain explicitly outside this tooling gate.
        self.assertEqual(manifest["rollback"]["database_rollback"], "outside-TOOL-003")
        # Require the exact prior packaged version in the checksum-bound pointer.
        self.assertEqual(manifest["rollback"]["previous"]["app_version"], "9.1.1")

    # Prove a fresh extracted copy imports and validates static release identity without a listener.
    def test_clean_extracted_copy_smoke(self):
        # Build the complete minimal fixture application artifact.
        archive_path, manifest_path = self.build("smoke")
        # Run the production verifier with its listener-free clean-copy smoke enabled.
        manifest = package_app.verify_release(archive_path, manifest_path, expected_commit=self.commit_sha, smoke=True)
        # Require the smoke-verified manifest to retain canonical fixture version identity.
        self.assertEqual(manifest["app_version"], "9.2.0")

    # Prove repository workflow text keeps branch builds separate from immutable publication.
    def test_workflow_publication_is_fail_closed(self):
        # Read the actual release workflow governed by TOOL-003.
        workflow = (package_app.ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        # Require pull requests to receive candidate validation coverage.
        self.assertIn("pull_request:", workflow)
        # Require immutable publication to originate only from a release event.
        self.assertIn("github.event_name == 'release'", workflow)
        # Require the release tag or ref to be protected before publication.
        self.assertIn("github.ref_protected == true", workflow)
        # Require a separately enabled repository-level publication switch.
        self.assertIn("ENABLE_IMMUTABLE_RELEASE_PUBLISH", workflow)
        # Reject replacement semantics that would make existing release assets mutable.
        self.assertNotIn("--clobber", workflow)


# Run the focused test module directly for local developer diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard runner and result handling.
    unittest.main()
