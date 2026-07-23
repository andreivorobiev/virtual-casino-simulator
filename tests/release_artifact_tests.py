"""Focused TOOL-003 tests for deterministic release and rollback provenance."""

# Import JSON support for fixture manifests and provenance assertions.
import json
# Import hashing for checksum-pinned fixture migration files.
import hashlib
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
# Import the protected predecessor receipt helper for exact fail-closed recovery tests.
from scripts import bootstrap_predecessor


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
        # Define one exact initial fixture migration.
        migration_one = json.dumps({"version": 1, "name": "initial", "description": "fixture", "statements": ["CREATE TABLE fixture_one (id INT)"]}, indent=2) + "\n"
        # Define one exact follow-up fixture migration.
        migration_two = json.dumps({"version": 2, "name": "upgrade", "description": "fixture", "statements": ["ALTER TABLE fixture_one ADD COLUMN value INT"]}, indent=2) + "\n"
        # Build the checksum-pinned fixture catalog from exact UTF-8 bytes.
        migration_catalog = json.dumps({"schema": "casino-mysql-migration-catalog-v1", "minimum_runtime_version": 2, "expected_version": 2, "migrations": [{"version": 1, "name": "initial", "file": "0001_initial.json", "sha256": hashlib.sha256(migration_one.encode("utf-8")).hexdigest()}, {"version": 2, "name": "upgrade", "file": "0002_upgrade.json", "sha256": hashlib.sha256(migration_two.encode("utf-8")).hexdigest()}]}, indent=2) + "\n"
        # Define the minimal required tracked application file inventory.
        self.files = {
            "ARCHITECTURE.md": "# Architecture\n",
            "LICENSE": "Test license\n",
            "NOTICE": "Test notice\n",
            "README.md": "# Fixture\n",
            "RELEASE_NOTES.md": "# Release\n",
            "casino/__init__.py": "\"\"\"Fixture package.\"\"\"\n",
            "casino/app.py": "\"\"\"Fixture app.\"\"\"\n\ndef main():\n    # Return without starting a listener.\n    return None\n",
            "casino/config.py": "\"\"\"Fixture config.\"\"\"\n\n# Expose the canonical fixture release.\nAPP_VERSION = \"9.3.0\"\n",
            "casino/core/recovery.py": "\"\"\"Fixture recovery policy.\"\"\"\n\n# Expose the authenticated chunked recovery format.\nENCRYPTED_STREAM_SCHEMA = \"casino-aes-256-gcm-chunked-v1\"\n",
            "casino/wsgi.py": "\"\"\"Fixture production WSGI adapter.\"\"\"\n\n# Expose a non-listening fixture callable.\ndef application(environ, start_response):\n    # Return a valid empty response for fixture metadata only.\n    start_response('204 No Content', [('Content-Length', '0')])\n    # Yield no response body bytes.\n    return [b'']\n",
            "contracts/compatibility/app-9.3.0.json": "{\"app_version\": \"9.3.0\"}\n",
            "deploy/gunicorn.conf.py": "# Bind the fixture production policy to loopback only.\nbind = '127.0.0.1:8765'\n",
            "deploy/systemd/casino.service": "[Service]\n# Start only the fixture production adapter.\nExecStart=gunicorn casino.wsgi:application\n",
            "modules/module-manifest.json": json.dumps({"application": "9.3.0", "source_baseline": "9.1.0", "modules": {"tooling": "1.7.0"}}) + "\n",
            "pyproject.toml": "[project]\nname = \"virtual-casino-simulator\"\nversion = \"9.3.0\"\nrequires-python = \">=3.10\"\ndependencies = [\"gunicorn>=23,<24\"]\n\n[project.optional-dependencies]\nmysql = [\"mysql-connector-python>=8.4\"]\nrecovery = [\"cryptography>=46,<50\"]\n",
            "run.py": "# Import the fixture application entry point.\nfrom casino.app import main\n",
            "migrations/mysql/0001_initial.json": migration_one,
            "migrations/mysql/0002_action_identity.json": migration_two,
            "migrations/mysql/catalog.json": migration_catalog.replace("0002_upgrade.json", "0002_action_identity.json"),
            "scripts/mysql_migrate.py": "# Fixture deployment-only migration runner.\n",
            "scripts/recovery.py": "# Fixture encrypted recovery runner.\n",
            "web/app.js": "// Fixture static application bundle.\n",
            "web/index.html": "<!doctype html><title>Fixture</title>\n",
        }
        # Reuse the exact repository edge sources so the extracted-copy smoke validates the packaged packet itself.
        for relative_path in (
            # Copy the non-mutating policy validator and read-only observer.
            "scripts/edge_gate.py",
            # Copy the canonical inert edge policy.
            "deploy/edge/restricted-preview.json",
            # Copy the reviewed nginx source without rendering its placeholders.
            "deploy/nginx/casino.conf.template",
            # Copy the reload-only ACME hook source.
            "deploy/acme/casino-renewal-hook.sh.template",
            # Copy the inactive monitor service source.
            "deploy/systemd/casino-edge-monitor.service.template",
            # Copy the inactive monitor timer source.
            "deploy/systemd/casino-edge-monitor.timer.template",
            # Copy the application-and-edge-only rollback source.
            "deploy/rollback/casino-edge-rollback.sh.template",
        ):
            # Read exact source text from the checkout under test.
            self.files[relative_path] = (package_app.ROOT / relative_path).read_text(encoding="utf-8")
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

    # Create isolated exact predecessor and successor inputs for protected recovery tests.
    def recovery_inputs(self):
        # Resolve one disposable recovery root outside every repository runtime directory.
        recovery_root = pathlib.Path(self.temporary.name) / "recovery"
        # Create the isolated directory before writing synthetic public artifact bytes.
        recovery_root.mkdir(parents=True, exist_ok=True)
        # Resolve the stable predecessor archive filename used by TOOL-003.
        archive_path = recovery_root / package_app.ARCHIVE_NAME
        # Write one synthetic archive payload whose exact digest is recorded below.
        archive_path.write_bytes(b"synthetic predecessor archive\n")
        # Assemble the minimum exact rebuilt-predecessor provenance accepted by the helper.
        predecessor = {
            "app_version": "9.2.0",
            "artifact": {"name": package_app.ARCHIVE_NAME, "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()},
            "mysql_schema": {"minimum_version": 2, "expected_version": 2},
            "rollback": {"application_only": True, "database_rollback": "outside-TOOL-003", "eligible": False, "previous": None},
            "source": {"commit_sha": bootstrap_predecessor.PREDECESSOR_COMMIT, "release_tag": "v9.2.0"},
        }
        # Resolve and write the canonical synthetic predecessor manifest.
        predecessor_path = recovery_root / package_app.MANIFEST_NAME
        # Preserve stable JSON bytes for receipt checksum assertions.
        predecessor_path.write_text(json.dumps(predecessor, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # Resolve and write the protected-main successor aggregate identity.
        successor_path = recovery_root / "successor-manifest.json"
        # Supply only the packaged release needed by the recovery boundary.
        successor_path.write_text(json.dumps({"application": "9.3.0"}) + "\n", encoding="utf-8", newline="\n")
        # Resolve the original two-row predecessor checksum inventory.
        checksums_path = recovery_root / "checksums.txt"
        # Render the same lexical row order produced by make_release.py.
        checksums_path.write_text(f"{hashlib.sha256(predecessor_path.read_bytes()).hexdigest()}  {predecessor_path.name}\n{hashlib.sha256(archive_path.read_bytes()).hexdigest()}  {archive_path.name}\n", encoding="utf-8", newline="\n")
        # Resolve the absent write-once recovery receipt target.
        receipt_path = recovery_root / bootstrap_predecessor.RECEIPT_NAME
        # Return every isolated input required by positive and negative tests.
        return predecessor_path, successor_path, checksums_path, receipt_path

    # Rewrite one authenticated archive member and rebind only outer checksum metadata.
    def rewrite_member_and_rebind_manifest(self, archive_path, manifest_path, member_name, replacement, manifest_mutator=None):
        # Read every original member and payload before replacing the archive.
        with zipfile.ZipFile(archive_path, "r") as original:
            # Preserve normalized ZipInfo records and exact payload bytes.
            members = [(item, original.read(item.filename)) for item in original.infolist()]
        # Resolve a sibling rewritten archive path inside the disposable output directory.
        rewritten = archive_path.with_suffix(".rewritten.zip")
        # Write every member with original normalized metadata.
        with zipfile.ZipFile(rewritten, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as output:
            # Recreate the full deterministic member sequence.
            for item, payload in members:
                # Substitute only the selected authenticated member.
                content = replacement if item.filename == member_name else payload
                # Write bytes under preserved normalized metadata.
                output.writestr(item, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        # Replace only the disposable fixture archive.
        rewritten.replace(archive_path)
        # Load the external manifest for outer checksum rebinding.
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Update the selected member inventory so verification reaches internal schema checks.
        for row in manifest["files"]:
            # Match the rewritten member by canonical archive path.
            if row["archive_path"] == member_name:
                # Rebind exact replacement size.
                row["size"] = len(replacement)
                # Rebind exact replacement checksum.
                row["sha256"] = hashlib.sha256(replacement).hexdigest()
        # Allow one test to model a coherently altered schema manifest.
        if manifest_mutator is not None:
            # Apply only the supplied fixture mutation.
            manifest_mutator(manifest)
        # Read final rewritten archive bytes.
        archive_bytes = archive_path.read_bytes()
        # Rebind outer archive size.
        manifest["artifact"]["size"] = len(archive_bytes)
        # Rebind outer archive checksum.
        manifest["artifact"]["sha256"] = hashlib.sha256(archive_bytes).hexdigest()
        # Persist canonical external JSON for the negative test.
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

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

    # Prove a migration edit fails internal catalog verification even after outer checksums are rebound.
    def test_packaged_migration_tampering_is_rejected(self):
        # Build a structurally valid deterministic candidate.
        archive_path, manifest_path = self.build("migration-tamper")
        # Select the second packaged migration member.
        member_name = f"{package_app.ARCHIVE_ROOT}/migrations/mysql/0002_action_identity.json"
        # Replace its bytes with a syntactically valid but unlisted migration.
        replacement = json.dumps({"version": 2, "name": "upgrade", "description": "tampered", "statements": ["SELECT 1"]}, indent=2).encode("utf-8") + b"\n"
        # Rebind outer archive and member inventory only, leaving catalog checksum immutable.
        self.rewrite_member_and_rebind_manifest(archive_path, manifest_path, member_name, replacement)
        # Require internal migration checksum refusal.
        with self.assertRaisesRegex(ValueError, "migration checksum"):
            # Skip smoke because schema verification must fail first.
            package_app.verify_release(archive_path, manifest_path, smoke=False)

    # Prove a coherently altered catalog/manifest cannot weaken the exact compatibility window.
    def test_packaged_catalog_invalid_tail_is_rejected(self):
        # Build a valid candidate before coherent fixture alteration.
        archive_path, manifest_path = self.build("catalog-tamper")
        # Read and alter the packaged catalog to claim version one while retaining two rows.
        catalog = json.loads(self.files["migrations/mysql/catalog.json"])
        # Weaken expected and minimum versions coherently.
        catalog["expected_version"] = 1
        # Match the weakened minimum to avoid the first window check.
        catalog["minimum_runtime_version"] = 1
        # Serialize exact replacement bytes.
        replacement = (json.dumps(catalog, indent=2) + "\n").encode("utf-8")
        # Define the maliciously coherent external schema mutation.
        def mutate_manifest(manifest):
            # Rebind the external catalog checksum.
            manifest["mysql_schema"]["catalog_sha256"] = hashlib.sha256(replacement).hexdigest()
            # Rebind the weakened expected version.
            manifest["mysql_schema"]["expected_version"] = 1
            # Rebind the weakened minimum version.
            manifest["mysql_schema"]["minimum_version"] = 1
        # Rewrite catalog and outer provenance coherently.
        self.rewrite_member_and_rebind_manifest(archive_path, manifest_path, f"{package_app.ARCHIVE_ROOT}/migrations/mysql/catalog.json", replacement, mutate_manifest)
        # Require independent expected-tail enforcement.
        with self.assertRaisesRegex(ValueError, "tail"):
            # Verify without smoke so the internal catalog gate is isolated.
            package_app.verify_release(archive_path, manifest_path, smoke=False)

    # Prove external MySQL schema provenance cannot diverge from unchanged packaged bytes.
    def test_manifest_mysql_schema_mismatch_is_rejected(self):
        # Build one valid candidate.
        archive_path, manifest_path = self.build("manifest-schema-tamper")
        # Load its external provenance record.
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Change only the external expected schema version.
        manifest["mysql_schema"]["expected_version"] = 1
        # Persist canonical tampered manifest bytes.
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # Require archive-derived provenance mismatch failure.
        with self.assertRaisesRegex(ValueError, "does not match archive"):
            # Verify without smoke so schema comparison is isolated.
            package_app.verify_release(archive_path, manifest_path, smoke=False)

    # Prove a retained prior manifest produces testable application rollback mapping.
    def test_previous_manifest_enables_application_rollback(self):
        # Define a complete synthetic prior release identity without external data.
        previous = {
            "app_version": "9.2.0",
            "artifact": {"name": package_app.ARCHIVE_NAME, "sha256": "b" * 64},
            "source": {"commit_sha": "c" * 40},
        }
        # Resolve the retained prior manifest fixture outside candidate output directories.
        previous_path = pathlib.Path(self.temporary.name) / "previous-manifest.json"
        # Write canonical prior JSON bytes for manifest-checksum provenance.
        previous_path.write_text(json.dumps(previous, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # Build a canonical tagged candidate with the retained prior manifest.
        archive_path, manifest_path = self.build("rollback", release_tag="v9.3.0", previous_manifest=previous_path)
        # Verify the artifact with immutable rollback required but without duplicate smoke cost.
        manifest = package_app.verify_release(
            archive_path,
            manifest_path,
            expected_commit=self.commit_sha,
            expected_tag="v9.3.0",
            require_rollback=True,
            smoke=False,
        )
        # Require an eligible application-only mapping to the prior version.
        self.assertTrue(manifest["rollback"]["eligible"])
        # Require database rollback to remain explicitly outside this tooling gate.
        self.assertEqual(manifest["rollback"]["database_rollback"], "outside-TOOL-003")
        # Require the exact prior packaged version in the checksum-bound pointer.
        self.assertEqual(manifest["rollback"]["previous"]["app_version"], "9.2.0")

    # Prove the current private-invite compatibility record binds the exact safe predecessor boundary.
    def test_current_release_compatibility_binds_private_invite_predecessor(self):
        # Load the immutable packaged-release compatibility record governed by TOOL-003.
        compatibility = json.loads((package_app.ROOT / "contracts" / "compatibility" / "app-9.5.0.json").read_text(encoding="utf-8"))
        # Require the canonical release and restricted-preview channel identities.
        self.assertEqual((compatibility["app_version"], compatibility["release_channel"]), ("9.5.0", "restricted-preview-private-invite"))
        # Require the exact prior packaged release and retained manifest filename.
        self.assertEqual(compatibility["predecessor"], {"app_version": "9.4.0", "compatibility_record": "contracts/compatibility/app-9.4.0.json", "required_artifact": "release-manifest.json"})
        # Require application-only rollback while preserving the already-applied MySQL v2 boundary.
        self.assertEqual(compatibility["rollback"], {"scope": "application-only", "database_rollback": "prohibited", "mysql_expected_schema_version": 2, "requires_retained_predecessor_manifest": True})
        # Require all broader enrollment surfaces to remain disabled for this release channel.
        self.assertEqual(compatibility["access_policy"], {"admission": "manual-invite", "public_signup": "disabled", "live_oauth": "disabled"})

    # Prove the protected recovery writes one checksum-bound exact predecessor/successor receipt.
    def test_protected_predecessor_recovery_receipt_is_exact(self):
        # Create clean synthetic inputs for the successful recovery boundary.
        predecessor_path, successor_path, checksums_path, receipt_path = self.recovery_inputs()
        # Use a distinct exact protected-main SHA as the accepted successor identity.
        successor_commit = "d" * 40
        # Create the one-shot recovery assets through the production helper.
        receipt = bootstrap_predecessor.write_recovery_assets(predecessor_path, successor_path, successor_commit, receipt_path, checksums_path)
        # Require exact predecessor and successor source identities in the durable receipt.
        self.assertEqual((receipt["predecessor"]["commit_sha"], receipt["successor"]["commit_sha"]), (bootstrap_predecessor.PREDECESSOR_COMMIT, successor_commit))
        # Require application-only schema-v2 rollback semantics with database rollback prohibited.
        self.assertEqual(receipt["rollback"], {"scope": "application-only", "database_rollback": "prohibited", "mysql_expected_schema_version": 2})
        # Require the created bytes to be represented by exactly one added checksum row.
        self.assertIn(f"{hashlib.sha256(receipt_path.read_bytes()).hexdigest()}  {receipt_path.name}", checksums_path.read_text(encoding="utf-8").splitlines())

    # Prove a rebuilt candidate from any commit other than the exact pre-bump main is rejected.
    def test_protected_predecessor_recovery_rejects_wrong_source(self):
        # Create otherwise valid isolated recovery inputs.
        predecessor_path, successor_path, _, _ = self.recovery_inputs()
        # Load and alter only the predecessor source commit.
        predecessor = json.loads(predecessor_path.read_text(encoding="utf-8"))
        # Replace the authorized commit with a different full SHA.
        predecessor["source"]["commit_sha"] = "e" * 40
        # Persist the syntactically valid but unauthorized manifest.
        predecessor_path.write_text(json.dumps(predecessor, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # Require refusal before any recovery receipt can be built.
        with self.assertRaisesRegex(ValueError, "source identity"):
            # Exercise the exact production provenance validator.
            bootstrap_predecessor.build_receipt(predecessor_path, successor_path, "d" * 40)

    # Prove bootstrap provenance cannot claim a prior rollback or any database rollback authority.
    def test_protected_predecessor_recovery_rejects_unsafe_rollback(self):
        # Create otherwise valid isolated recovery inputs.
        predecessor_path, successor_path, _, _ = self.recovery_inputs()
        # Load the synthetic exact predecessor manifest.
        predecessor = json.loads(predecessor_path.read_text(encoding="utf-8"))
        # Invent rollback eligibility that the first retained predecessor cannot possess.
        predecessor["rollback"]["eligible"] = True
        # Persist the unsafe but syntactically valid predecessor record.
        predecessor_path.write_text(json.dumps(predecessor, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        # Require refusal before receipt or checksum creation.
        with self.assertRaisesRegex(ValueError, "eligibility boundary"):
            # Exercise the production bootstrap validator directly.
            bootstrap_predecessor.build_receipt(predecessor_path, successor_path, "d" * 40)

    # Prove the recovery helper will not replace an existing receipt or accept stale checksums.
    def test_protected_predecessor_recovery_is_write_once_and_checksum_closed(self):
        # Create valid isolated recovery inputs.
        predecessor_path, successor_path, checksums_path, receipt_path = self.recovery_inputs()
        # Replace the original inventory with a syntactically valid stale digest.
        checksums_path.write_text(f"{'0' * 64}  {predecessor_path.name}\n", encoding="utf-8", newline="\n")
        # Require checksum refusal without creating the receipt.
        with self.assertRaisesRegex(ValueError, "checksum inventory"):
            # Exercise the production write boundary against stale inputs.
            bootstrap_predecessor.write_recovery_assets(predecessor_path, successor_path, "d" * 40, receipt_path, checksums_path)
        # Require the failed attempt to leave the exclusive receipt absent.
        self.assertFalse(receipt_path.exists())
        # Create a sentinel receipt to model any prior recovery attempt.
        receipt_path.write_text("sentinel\n", encoding="utf-8", newline="\n")
        # Require write-once refusal before inspecting or replacing its bytes.
        with self.assertRaises(FileExistsError):
            # Exercise the exact production exclusive-output boundary.
            bootstrap_predecessor.write_recovery_assets(predecessor_path, successor_path, "d" * 40, receipt_path, checksums_path)
        # Preserve the existing receipt bytes exactly.
        self.assertEqual(receipt_path.read_text(encoding="utf-8"), "sentinel\n")

    # Prove a fresh extracted copy imports and validates static release identity without a listener.
    def test_clean_extracted_copy_smoke(self):
        # Build the complete minimal fixture application artifact.
        archive_path, manifest_path = self.build("smoke")
        # Run the production verifier with its listener-free clean-copy smoke enabled.
        manifest = package_app.verify_release(archive_path, manifest_path, expected_commit=self.commit_sha, smoke=True)
        # Require the smoke-verified manifest to retain canonical fixture version identity.
        self.assertEqual(manifest["app_version"], "9.3.0")
        # Require release provenance to bind exact-only MySQL schema version two.
        self.assertEqual((manifest["mysql_schema"]["minimum_version"], manifest["mysql_schema"]["expected_version"]), (2, 2))
        # Require both catalog and ordered migration chain checksums.
        self.assertRegex(manifest["mysql_schema"]["catalog_sha256"], r"^[0-9a-f]{64}$")
        # Require the copied recovery tooling dependency to be represented in the release SBOM.
        self.assertIn({"requirement": "cryptography>=46,<50", "scope": "optional:recovery"}, manifest["sbom"]["components"])

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
        # Require both candidate and publication smoke jobs to install the declared recovery extra.
        self.assertEqual(workflow.count('python -m pip install ".[recovery]"'), 2)
        # Isolate the one-time predecessor job from the ordinary immutable publication job.
        predecessor_job = workflow.split("bootstrap-v9-2-predecessor:", 1)[1].split("publish-immutable-release:", 1)[0]
        # Require exact protected-main, owner, pre-bump source, and conflict-refusal gates.
        self.assertIn("github.ref == 'refs/heads/main'", predecessor_job)
        self.assertIn("github.ref_protected == true", predecessor_job)
        self.assertIn("github.actor == github.repository_owner", predecessor_job)
        # Require every gh release command to resolve the repository without ambient checkout state.
        self.assertIn("GH_REPO: ${{ github.repository }}", predecessor_job)
        self.assertIn(bootstrap_predecessor.PREDECESSOR_COMMIT, predecessor_job)
        self.assertIn('test "${tag_status}" -eq 2', predecessor_job)
        self.assertIn("existing-release-tags.txt", predecessor_job)
        # Require actual-byte determinism for the archive, manifest, and checksum inventory.
        self.assertEqual(predecessor_job.count("cmp predecessor-first/"), 3)
        # Require one draft create and one verified non-latest publish with no asset overwrite path.
        self.assertEqual(predecessor_job.count("gh release create"), 1)
        self.assertEqual(predecessor_job.count("gh release edit"), 1)
        self.assertGreaterEqual(predecessor_job.count("--latest=false"), 2)
        self.assertNotIn("gh release upload", predecessor_job)
        self.assertNotIn("gh release delete", predecessor_job)
        self.assertNotIn("git push", predecessor_job)
        self.assertNotIn("--clobber", predecessor_job)
        # Read the canonical release driver that records exact validation provenance.
        release_driver = (package_app.ROOT / "scripts" / "make_release.py").read_text(encoding="utf-8")
        # Require focused #205 recovery evidence before any candidate can be packaged.
        self.assertIn('"tests.recovery_tests"', release_driver)
        # Reject replacement semantics that would make existing release assets mutable.
        self.assertNotIn("--clobber", workflow)


# Run the focused test module directly for local developer diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard runner and result handling.
    unittest.main()
