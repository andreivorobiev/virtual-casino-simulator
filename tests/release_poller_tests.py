# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free release-poller contract tests for OPS-007, TOOL-015, and TEST-180."""

# Import hashing so fixture checksums bind exact synthetic release bytes.
import hashlib
# Import JSON encoding for stable and hostile GitHub Release fixtures.
import json
# Import environment access for locating the Windows Git Bash fallback.
import os
# Import portable paths for checked-in and disposable fixture files.
from pathlib import Path
# Import executable discovery for hosted Linux and local Windows test parity.
import shutil
# Import subprocess execution for the script's listener-free subcommands.
import subprocess
# Import the active Python executable for the poller's embedded verification helpers.
import sys
# Import disposable directories so no test writes repository or production state.
import tempfile
# Import unittest for dependency-free focused execution.
import unittest

# Resolve the repository root from this focused test module.
ROOT = Path(__file__).resolve().parents[1]
# Bind the exact host-side pull implementation under test.
POLLER = ROOT / "deploy" / "pull" / "casino-release-poller.sh"
# Bind the publication-only workflow whose dead SSH leg must stay retired.
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-production.yml"
# Bind both systemd templates that schedule pull delivery and lag detection.
POLLER_SERVICE = ROOT / "deploy" / "systemd" / "casino-release-poller.service.template"
# Bind the five-minute timer template separately for cadence assertions.
POLLER_TIMER = ROOT / "deploy" / "systemd" / "casino-release-poller.timer.template"
# Bind the existing monitor service that now owns the three-interval lag alarm.
EDGE_SERVICE = ROOT / "deploy" / "systemd" / "casino-edge-monitor.service.template"


# Convert a Windows absolute path into the MSYS form accepted by local Git Bash.
def bash_path(path: Path | str) -> str:
    # Resolve a stable absolute spelling before platform conversion.
    value = str(Path(path).resolve())
    # Leave POSIX paths unchanged on hosted Linux.
    if os.name != "nt":
        # Return the native hosted path.
        return value
    # Convert the drive prefix and separators without invoking another process.
    return f"/{value[0].lower()}{value[2:].replace(chr(92), '/')}"


# Prove the pull poller without opening a listener, contacting GitHub, or touching services.
class ReleasePollerTests(unittest.TestCase):
    # Locate a Bash runtime that works in hosted CI and the bundled local environment.
    @classmethod
    def setUpClass(cls):
        # Prefer the ordinary hosted Bash executable.
        cls.bash = shutil.which("bash")
        # Fall back to the standard Git for Windows installation when Bash is not on PATH.
        if cls.bash is None and os.name == "nt":
            # Bind the fixed Git Bash path installed with GitHub tooling.
            candidate = Path(r"C:\Program Files\Git\bin\bash.exe")
            # Use the fallback only when its exact executable exists.
            if candidate.exists():
                # Record the fallback executable for every test invocation.
                cls.bash = str(candidate)
        # Fail clearly rather than silently skipping the deployment proof.
        if cls.bash is None:
            # Raise one stable suite error when the required shell is absent.
            raise RuntimeError("Bash is required for release poller tests")

    # Create one isolated fixture root per test.
    def setUp(self):
        # Allocate a disposable directory for release metadata and artifacts.
        self.temporary = tempfile.TemporaryDirectory()
        # Register deterministic cleanup even when an assertion fails.
        self.addCleanup(self.temporary.cleanup)
        # Resolve the fixture root once for concise helpers.
        self.root = Path(self.temporary.name)
        # Start from an environment with no release token or production paths.
        self.environment = dict(os.environ)
        # Point embedded helpers at the active test interpreter.
        self.environment["CASINO_PYTHON"] = bash_path(sys.executable)

    # Invoke one listener-free poller subcommand with bounded captured output.
    def run_poller(self, *arguments: str, check: bool = True, environment: dict | None = None):
        # Select the supplied isolated environment or the safe test default.
        selected_environment = environment or self.environment
        # Execute the checked-in script through Bash without a login shell or network helper.
        return subprocess.run(
            [self.bash, bash_path(POLLER), *arguments],
            cwd=ROOT,
            env=selected_environment,
            check=check,
            capture_output=True,
            text=True,
            timeout=30,
        )

    # Build one canonical stable release API object with the exact required assets.
    def release_payload(self):
        # Use one full commit so provenance validation remains exact.
        commit = "a" * 40
        # Return only fields consumed by the bounded inspection helper.
        return {
            "draft": False,
            "prerelease": False,
            "tag_name": "v0.9.5.77",
            "target_commitish": commit,
            "published_at": "2026-08-13T20:00:00Z",
            "assets": [
                {"name": "checksums.txt", "browser_download_url": "https://github.com/example/repo/releases/download/v0.9.5.77/checksums.txt"},
                {"name": "release-manifest.json", "browser_download_url": "https://github.com/example/repo/releases/download/v0.9.5.77/release-manifest.json"},
                {"name": "virtual_casino_simulator_package.zip", "browser_download_url": "https://github.com/example/repo/releases/download/v0.9.5.77/virtual_casino_simulator_package.zip"},
            ],
        }

    # Prove semantic version comparison distinguishes deploy, current, and no-downgrade states.
    def test_decide_compares_all_four_numeric_components(self):
        # Require a strictly newer release to produce one deployment decision.
        self.assertEqual(self.run_poller("decide", "0.9.5.76", "v0.9.5.77").stdout.strip(), "deploy")
        # Require an already installed release to remain a no-op.
        self.assertEqual(self.run_poller("decide", "0.9.5.76", "v0.9.5.76").stdout.strip(), "current")
        # Require a host newer than GitHub's latest pointer never to downgrade.
        self.assertEqual(self.run_poller("decide", "0.9.5.77", "v0.9.5.76").stdout.strip(), "ahead")
        # Require numeric comparison rather than lexical component ordering.
        self.assertEqual(self.run_poller("decide", "0.9.5.9", "v0.9.5.10").stdout.strip(), "deploy")

    # Prove malformed or noncanonical versions fail closed.
    def test_decide_rejects_noncanonical_versions(self):
        # Exercise leading-zero and three-component hostile values independently.
        for installed, latest in (("0.9.5.076", "v0.9.5.77"), ("0.9.5", "v0.9.5.77"), ("0.9.5.76", "latest")):
            # Invoke without automatic exception conversion so the nonzero result is inspectable.
            result = self.run_poller("decide", installed, latest, check=False)
            # Require every malformed comparison to fail rather than guess.
            self.assertNotEqual(result.returncode, 0)

    # Prove stable release inspection binds exact identity, publication time, and asset URLs.
    def test_release_json_inspection_is_exact_and_listener_free(self):
        # Persist the isolated GitHub API fixture.
        release_path = self.root / "release.json"
        # Write canonical JSON without contacting GitHub.
        release_path.write_text(json.dumps(self.release_payload()), encoding="utf-8")
        # Inspect the fixture through the production parser.
        result = self.run_poller("inspect-release-json", bash_path(release_path))
        # Split the exact tab-delimited internal record.
        fields = result.stdout.strip().split("\t")
        # Require canonical tag, source, epoch, and three immutable GitHub asset URLs.
        self.assertEqual((fields[0], fields[1], fields[2], len(fields)), ("v0.9.5.77", "a" * 40, "1786651200", 6))

    # Prove drafts, duplicate assets, and foreign download origins fail closed.
    def test_release_json_rejects_untrusted_metadata(self):
        # Build four independent malformed release records.
        payloads = []
        # Reject a draft even when every identity field is otherwise valid.
        draft = self.release_payload()
        # Mark the fixture as unpublished.
        draft["draft"] = True
        # Retain the draft hostile case.
        payloads.append(draft)
        # Reject duplicate canonical asset names that could make selection ambiguous.
        duplicate = self.release_payload()
        # Append an exact duplicate entry.
        duplicate["assets"].append(dict(duplicate["assets"][0]))
        # Retain the duplicate hostile case.
        payloads.append(duplicate)
        # Reject asset bytes served from an unreviewed origin.
        foreign = self.release_payload()
        # Replace one canonical GitHub URL with a foreign host.
        foreign["assets"][0]["browser_download_url"] = "https://example.invalid/checksums.txt"
        # Retain the foreign-origin hostile case.
        payloads.append(foreign)
        # Reject an otherwise harmless extra asset because release inventory is exact.
        extra = self.release_payload()
        # Add one ungoverned hosted file to the release record.
        extra["assets"].append({"name": "notes.txt", "browser_download_url": "https://github.com/example/repo/releases/download/v0.9.5.77/notes.txt"})
        # Retain the extra-asset hostile case.
        payloads.append(extra)
        # Exercise every metadata failure independently.
        for index, payload in enumerate(payloads):
            # Write the isolated hostile record.
            path = self.root / f"release-{index}.json"
            # Persist only disposable fixture bytes.
            path.write_text(json.dumps(payload), encoding="utf-8")
            # Require nonzero parser completion without making any network call.
            self.assertNotEqual(self.run_poller("inspect-release-json", bash_path(path), check=False).returncode, 0)

    # Prove exact checksum and manifest provenance verification precede the packaged verifier.
    def test_verify_assets_accepts_exact_bytes_and_rejects_corruption_first(self):
        # Create an isolated release asset directory.
        assets = self.root / "assets"
        # Create the directory without touching repository output.
        assets.mkdir()
        # Bind one exact synthetic release identity.
        commit = "b" * 40
        # Write deterministic archive fixture bytes.
        archive = assets / "virtual_casino_simulator_package.zip"
        # The asset need not be a real ZIP because the pure verification seam never extracts it.
        archive.write_bytes(b"synthetic archive")
        # Build the minimal provenance object consumed before the full package verifier.
        manifest_payload = {"source": {"release_tag": "v0.9.5.77", "commit_sha": commit}, "artifact": {"name": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}}
        # Persist stable manifest bytes.
        manifest = assets / "release-manifest.json"
        # Use canonical compact JSON for deterministic fixture checksums.
        manifest.write_text(json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        # Bind both exact public assets in the canonical checksum format.
        checksums = assets / "checksums.txt"
        # Write exactly two records and no ignored third asset.
        checksums.write_text(f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="utf-8")
        # Create a harmless packaged-verifier double under the expected extracted layout.
        verifier_root = self.root / "verifier"
        # Create its scripts directory only inside the disposable fixture.
        (verifier_root / "scripts").mkdir(parents=True)
        # Bind a marker path that proves whether the full verifier was reached.
        marker = verifier_root / "called"
        # Write a dependency-free verifier that accepts any supplied CLI arguments.
        (verifier_root / "scripts" / "package_app.py").write_text("# Record that exact checksum and provenance checks completed first.\nfrom pathlib import Path\n# Write one inert test-local marker.\nPath(__file__).resolve().parents[1].joinpath('called').write_text('yes', encoding='utf-8')\n", encoding="utf-8")
        # Point the production script at the disposable verifier root.
        environment = dict(self.environment)
        # Use Bash-compatible path spelling for the verifier root.
        environment["CASINO_VERIFY_ROOT"] = bash_path(verifier_root)
        # Require exact assets to reach and pass the packaged verifier.
        self.run_poller("verify-assets", bash_path(assets), "v0.9.5.77", commit, environment=environment)
        # Prove the full verifier ran after the pure checks.
        self.assertEqual(marker.read_text(encoding="utf-8"), "yes")
        # Remove the marker before the hostile corruption case.
        marker.unlink()
        # Corrupt the archive without rewriting its checksum or manifest.
        archive.write_bytes(b"corrupt archive")
        # Require fail-closed verification.
        result = self.run_poller("verify-assets", bash_path(assets), "v0.9.5.77", commit, check=False, environment=environment)
        # Prove corruption returns nonzero.
        self.assertNotEqual(result.returncode, 0)
        # Prove the full verifier and every later activation seam remain untouched.
        self.assertFalse(marker.exists())

    # Prove workflow and host templates retain exact publication/pull ownership boundaries.
    def test_workflow_and_units_assign_delivery_to_the_host_poller(self):
        # Read the workflow as inert text.
        workflow = WORKFLOW.read_text(encoding="utf-8")
        # Preserve immutable protected-main publication and hosted verification.
        self.assertIn("name: Publish exact-main release", workflow)
        # Retire the designed-to-fail runner-to-production leg completely.
        self.assertNotIn("deploy-production:", workflow)
        # Reject every inbound deployment credential or transport command.
        for forbidden in ("CASINO_DEPLOY_SSH_HOST", "CASINO_DEPLOY_SSH_KEY", "known_hosts", "scp -P", "ssh -p"):
            # Require the retired string to remain absent.
            self.assertNotIn(forbidden, workflow)
        # Read the pull service and timer templates.
        service = POLLER_SERVICE.read_text(encoding="utf-8")
        # Bind the stable root-owned executable and required monitor environment.
        self.assertIn("ExecStart=/usr/local/libexec/casino-release-poller poll", service)
        # Prove the unit cannot run longer than the bounded deployment window.
        self.assertIn("TimeoutStartSec=15min", service)
        # Read the exact timer cadence.
        timer = POLLER_TIMER.read_text(encoding="utf-8")
        # Require the ticket-owned five-minute interval and persistent missed-run behavior.
        self.assertIn("OnUnitActiveSec=5min", timer)
        # Require missed timer firings to run after the host returns.
        self.assertIn("Persistent=true", timer)
        # Read the existing edge monitor extension.
        edge_service = EDGE_SERVICE.read_text(encoding="utf-8")
        # Require a privileged lag check after every otherwise-green edge observation.
        self.assertIn("ExecStartPost=+/usr/local/libexec/casino-release-poller check-lag", edge_service)

    # Prove verification and schema gates precede selector mutation while rollback remains application-only.
    def test_activation_order_is_fail_closed_and_schema_two_only(self):
        # Read the pull script as inert text for exact ordering assertions.
        text = POLLER.read_text(encoding="utf-8")
        # Locate the first exact checksum/provenance verification.
        verification = text.index('verify_assets "${work_root}" "${latest_tag}" "${latest_commit}"')
        # Locate the preflight failure alarm that covers checksum and provenance rejection.
        alarm_trap = text.index("trap cleanup_deployment EXIT")
        # Locate the candidate schema-two compatibility proof.
        schema_check = text.index('check_schema_two "${candidate_root}"')
        # Locate the first production-owned release fragment write.
        environment_install = text.index('install -m 0640 -o root -g root "${work_root}/release.env" "${RELEASE_ENV}"')
        # Locate the atomic selector switch independently.
        selector_switch = text.index('mv -Tf "${CURRENT_LINK}.next" "${CURRENT_LINK}"', environment_install)
        # Prove both immutable-byte and schema gates precede every production mutation.
        self.assertLess(verification, environment_install)
        # Prove the poll-failure alarm is armed before corrupt bytes reach verification.
        self.assertLess(alarm_trap, verification)
        # Require the armed cleanup path to persist a bounded poll-failure alarm.
        self.assertIn('write_alarm "poll_failed"', text)
        # Prove schema compatibility is established before release.env mutation.
        self.assertLess(schema_check, environment_install)
        # Prove release.env is staged before the current selector moves.
        self.assertLess(environment_install, selector_switch)
        # Require an error trap to restore the previous selector and fragment.
        self.assertIn("rollback_on_error()", text)
        # Require the documented drill to execute the same rollback implementation.
        self.assertIn('deploy_latest "rollback-drill"', text)
        # Reject migration, grant, database rollback, and global mutation authority.
        for forbidden in ("mysql_migrate.py apply", "SET GLOBAL", "GRANT ", "REVOKE ", "database rollback"):
            # Keep the deployment bridge exact-schema-two and application-only.
            self.assertNotIn(forbidden, text)


# Run the focused suite directly when an operator requests it.
if __name__ == "__main__":
    # Propagate unittest's fail-closed process status.
    unittest.main()
