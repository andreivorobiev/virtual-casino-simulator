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
# Import Unix file-type constants for deterministic ZIP member metadata.
import stat
# Import executable discovery for hosted Linux and local Windows test parity.
import shutil
# Import subprocess execution for the script's listener-free subcommands.
import subprocess
# Import the active Python executable for the poller's embedded verification helpers.
import sys
# Import source indentation cleanup for executable Bash harnesses.
import textwrap
# Import disposable directories so no test writes repository or production state.
import tempfile
# Import unittest for dependency-free focused execution.
import unittest
# Import deterministic archive writing for the real-unzip permission regression.
import zipfile

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

    # Source the production poller into one disposable Bash harness without invoking its CLI.
    def run_sourced_poller(self, script: str, *, environment: dict | None = None, check: bool = True):
        # Persist the caller's listener-free harness under the disposable test root.
        harness = self.root / "poller-harness.sh"
        # Normalize indentation while retaining exact LF shell syntax.
        harness.write_text(textwrap.dedent(script), encoding="utf-8", newline="\n")
        # Select the supplied isolated environment or the ordinary safe default.
        selected_environment = environment or self.environment
        # Execute the harness through the same Bash runtime as the production script tests.
        return subprocess.run(
            [self.bash, bash_path(harness)],
            cwd=ROOT,
            env=selected_environment,
            check=check,
            capture_output=True,
            text=True,
            timeout=30,
        )

    # Exercise the deployment state machine with every external side effect replaced by a disposable seam.
    def run_deployment_scenario(self, scenario: str, *, run_poll_after_drill: bool = False):
        # Create one isolated scenario root so sibling cases cannot satisfy cleanup assertions.
        scenario_root = self.root / scenario
        # Create the production-shaped release and state directories under the disposable root.
        releases_root = scenario_root / "releases"
        # Create the release collection before the poller requests its owned work directory.
        releases_root.mkdir(parents=True)
        # Retain one unrelated sentinel that cleanup must never remove.
        sentinel = releases_root / "operator-owned-sentinel"
        # Write fixed sentinel bytes for exact post-failure preservation proof.
        sentinel.write_text("preserve\n", encoding="utf-8", newline="\n")
        # Create the exact predecessor release root selected before every scenario.
        predecessor_root = releases_root / ("d" * 40)
        # Materialize the predecessor directory for fail-closed existence checks.
        predecessor_root.mkdir()
        # Create one private state root for alarm and selector fixtures.
        state_root = scenario_root / "state"
        # Materialize the poller state directory.
        state_root.mkdir()
        # Bind the synthetic current selector through one test-owned text record.
        selector_record = state_root / "current-root"
        # Store POSIX spelling because the sourced Bash harness reads the record.
        selector_record.write_text(bash_path(predecessor_root) + "\n", encoding="utf-8", newline="\n")
        # Seed one prior release fragment so rollback must restore exact bytes.
        release_env = scenario_root / "release.env"
        # Preserve one recognizable predecessor fragment.
        release_env.write_text("CASINO_BUILD_SHA=" + ("d" * 40) + "\n", encoding="utf-8", newline="\n")
        # Seed an alarm that only a successful complete operation may clear.
        alarm_file = state_root / "alarm"
        # Use the canonical bounded alarm shape.
        alarm_file.write_text("status=alarm\nreason=prior_failure\n", encoding="utf-8", newline="\n")
        # Capture selector, observation, schema, and service actions without touching the host.
        trace = state_root / "trace"
        # Bind one disposable stable-poller path for the final successful install.
        stable_poller = scenario_root / "stable-poller"
        # Bind one disposable lock file for the real exclusive-descriptor path.
        lock_file = scenario_root / "poller.lock"
        # Build a sourceable harness whose high-level dependencies are deterministic fakes.
        harness = r'''
            export CASINO_RELEASES_ROOT="__RELEASES_ROOT__"
            export CASINO_INSTALL_ROOT="__SCENARIO_ROOT__"
            export CASINO_CURRENT_LINK="__SCENARIO_ROOT__/current"
            export CASINO_RELEASE_ENV="__RELEASE_ENV__"
            export CASINO_RELEASE_POLLER_STATE_ROOT="__STATE_ROOT__"
            export CASINO_RELEASE_POLLER_ALARM_FILE="__ALARM_FILE__"
            export CASINO_RELEASE_POLLER_STABLE_PATH="__STABLE_POLLER__"
            export CASINO_RELEASE_POLLER_LOCK_FILE="__LOCK_FILE__"
            export CASINO_PYTHON="__PYTHON__"
            source "__POLLER__"
            log() { printf '%s\n' "$1" >> "__TRACE__"; }
            require_runtime() { :; }
            id() { printf '0\n'; }
            flock() { :; }
            systemctl() { printf 'systemctl:%s\n' "$*" >> "__TRACE__"; }
            install() {
              local arguments=("$@")
              if test "${arguments[0]}" = "-d"; then
                local directory_index=$((${#arguments[@]} - 1))
                command mkdir -p "${arguments[$directory_index]}"
                return 0
              fi
              local source_index=$((${#arguments[@]} - 2))
              local destination_index=$((${#arguments[@]} - 1))
              command cp "${arguments[$source_index]}" "${arguments[$destination_index]}"
            }
            query_release() {
              : > "$1"
              printf 'v0.9.5.79\t%s\t0\thttps://github.com/checksums\thttps://github.com/manifest\thttps://github.com/archive\n' "__CANDIDATE_COMMIT__"
            }
            download_release() {
              command mkdir -p "$2"
              command touch "$2/checksums.txt" "$2/release-manifest.json" "$2/virtual_casino_simulator_package.zip"
            }
            verify_assets() { :; }
            unzip() {
              local destination="$4/virtual_casino_simulator"
              command mkdir -p "${destination}/deploy/pull"
              command cp "__POLLER__" "${destination}/deploy/pull/casino-release-poller.sh"
              printf 'VALUE = 1\n' > "${destination}/probe.py"
            }
            validate_monitor_configuration() { :; }
            write_release_environment() { printf 'CASINO_BUILD_SHA=%s\n' "__CANDIDATE_COMMIT__" > "$3"; }
            compare_release_roots() {
              if command find "$2" -type d -name '__pycache__' -print -quit | command grep -q .; then
                printf 'existing release root does not match the verified archive\n' >&2
                return 1
              fi
              return 0
            }
            check_schema_compatibility() { printf 'schema:%s\n' "$1" >> "__TRACE__"; }
            current_release_root() { command cat "__SELECTOR_RECORD__"; }
            activate_release() {
              printf '%s\n' "$1" > "__SELECTOR_RECORD__"
              printf 'selector:%s\n' "$1" >> "__TRACE__"
            }
            installed_version() { printf '0.9.5.78\n'; }
            installed_commit() { printf '%s\n' "__PREDECESSOR_COMMIT__"; }
            observe_release() {
              printf 'observe:%s:%s\n' "$1" "$2" >> "__TRACE__"
              if test "$1" = "0.9.5.79"; then
                if test "${PYTHONDONTWRITEBYTECODE:-}" != "1"; then
                  command mkdir -p "$(current_release_root)/__pycache__"
                  printf 'synthetic-bytecode\n' > "$(current_release_root)/__pycache__/probe.pyc"
                fi
              fi
              if test "__SCENARIO__" = "candidate-failure" && test "$1" = "0.9.5.79"; then
                return 1
              fi
              if test "__SCENARIO__" = "predecessor-failure" && test "$1" = "0.9.5.78"; then
                return 1
              fi
              return 0
            }
            deploy_latest rollback-drill
            __OPTIONAL_POLL__
        '''
        # Bind every exact path and identity without invoking shell interpolation in Python.
        replacements = {
            "__RELEASES_ROOT__": bash_path(releases_root),
            "__SCENARIO_ROOT__": bash_path(scenario_root),
            "__RELEASE_ENV__": bash_path(release_env),
            "__STATE_ROOT__": bash_path(state_root),
            "__ALARM_FILE__": bash_path(alarm_file),
            "__STABLE_POLLER__": bash_path(stable_poller),
            "__LOCK_FILE__": bash_path(lock_file),
            "__PYTHON__": bash_path(sys.executable),
            "__POLLER__": bash_path(POLLER),
            "__TRACE__": bash_path(trace),
            "__CANDIDATE_COMMIT__": "c" * 40,
            "__SELECTOR_RECORD__": bash_path(selector_record),
            "__PREDECESSOR_COMMIT__": "d" * 40,
            "__SCENARIO__": scenario,
            "__OPTIONAL_POLL__": "deploy_latest deploy" if run_poll_after_drill else ":",
        }
        # Replace only fixed test-owned markers.
        for marker, value in replacements.items():
            # Bind one marker exactly once or fail while authoring the test.
            self.assertIn(marker, harness)
            # Replace every intentional use of the marker with its fixed value.
            harness = harness.replace(marker, value)
        # Execute without automatic failure conversion so fail-closed receipts remain inspectable.
        result = self.run_sourced_poller(harness, check=False)
        # Return the exact disposable evidence paths with the process result.
        return result, releases_root, predecessor_root, selector_record, alarm_file, sentinel, stable_poller, trace

    # Exercise lag-check through main so function-return trap lifetime matches production execution.
    def run_lag_scenario(self, scenario: str, installed_version: str, installed_commit: str, published_epoch: int):
        # Allocate a scenario-specific directory for cleanup and alarm assertions.
        scenario_root = self.root / f"lag-{scenario}"
        # Create the isolated state root consumed by the real alarm helpers.
        state_root = scenario_root / "state"
        # Materialize the state root before the production helper writes into it.
        state_root.mkdir(parents=True)
        # Bind the exact deterministic temporary directory returned by the mktemp seam.
        work_root = scenario_root / "owned-work"
        # Retain one sibling proving cleanup never broadens beyond the captured work root.
        sibling = scenario_root / "operator-sentinel"
        # Persist fixed sibling bytes for exact post-check verification.
        sibling.write_text("preserve\n", encoding="utf-8", newline="\n")
        # Capture the production log decision without invoking the host logger.
        trace = scenario_root / "trace"
        # Bind the real durable alarm path under the disposable state root.
        alarm = state_root / "alarm"
        # Build one sourceable main-path harness with deterministic release metadata and time.
        harness = r'''
            export CASINO_RELEASE_POLLER_STATE_ROOT="__STATE_ROOT__"
            export CASINO_RELEASE_POLLER_ALARM_FILE="__ALARM__"
            export CASINO_RELEASE_POLL_INTERVAL_SECONDS=300
            export CASINO_RELEASE_LAG_INTERVAL_MULTIPLIER=3
            export CASINO_PYTHON="__PYTHON__"
            source "__POLLER__"
            log() { printf '%s\n' "$1" >> "__TRACE__"; }
            require_runtime() { :; }
            mktemp() {
              test "$1" = "-d"
              command mkdir "__WORK_ROOT__"
              printf '%s\n' "__WORK_ROOT__"
            }
            query_release() {
              : > "$1"
              printf 'v0.9.5.80\t%s\t%s\thttps://github.com/checksums\thttps://github.com/manifest\thttps://github.com/archive\n' "__LATEST_COMMIT__" "__PUBLISHED_EPOCH__"
            }
            installed_version() { printf '%s\n' "__INSTALLED_VERSION__"; }
            installed_commit() { printf '%s\n' "__INSTALLED_COMMIT__"; }
            date() {
              test "$1" = "+%s"
              printf '2000\n'
            }
            main_rc=0
            if main check-lag; then
              :
            else
              main_rc=$?
            fi
            printf 'main_rc=%s\n' "${main_rc}"
            test ! -e "__WORK_ROOT__"
            test -f "__SIBLING__"
            printf 'after_main=PASS\n'
        '''
        # Bind one exact candidate commit shared by all deterministic scenarios.
        latest_commit = "a" * 40
        # Replace only fixed test-owned markers with safe fixture values.
        replacements = {
            "__STATE_ROOT__": bash_path(state_root),
            "__ALARM__": bash_path(alarm),
            "__PYTHON__": bash_path(sys.executable),
            "__POLLER__": bash_path(POLLER),
            "__TRACE__": bash_path(trace),
            "__WORK_ROOT__": bash_path(work_root),
            "__LATEST_COMMIT__": latest_commit,
            "__PUBLISHED_EPOCH__": str(published_epoch),
            "__INSTALLED_VERSION__": installed_version,
            "__INSTALLED_COMMIT__": installed_commit,
            "__SIBLING__": bash_path(sibling),
        }
        # Apply every deterministic marker and fail authoring if a marker disappears.
        for marker, value in replacements.items():
            # Require each marker to remain represented in the harness contract.
            self.assertIn(marker, harness)
            # Replace all intentional uses of the fixed marker.
            harness = harness.replace(marker, value)
        # Execute the actual main-to-check_lag call without network, service, or production access.
        result = self.run_sourced_poller(harness)
        # Return exact process, alarm, sibling, work-root, trace, and candidate evidence.
        return result, alarm, sibling, work_root, trace, latest_commit

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

    # Prove lag-check owns cleanup for exactly one main call and preserves all decision alarms.
    def test_lag_check_main_path_cleans_once_without_return_trap_leak(self):
        # Define current, within-window deploy, overdue deploy, and identity-conflict cases.
        scenarios = (
            ("current", "0.9.5.80", "latest", 1500, 0, None, "lag_check=current"),
            ("deploy-within", "0.9.5.79", "previous", 1500, 0, None, "lag_check=deploy"),
            ("deploy-overdue", "0.9.5.79", "previous", 0, 1, "release_delivery_lag", None),
            ("identity-conflict", "0.9.5.80", "different", 1500, 1, "release_identity_conflict", None),
        )
        # Exercise each decision independently so one cleanup cannot satisfy a sibling case.
        for scenario, version, commit_kind, published, expected_rc, alarm_reason, log_fragment in scenarios:
            # Bind the exact installed commit needed for current or conflict behavior.
            installed_commit = "a" * 40 if commit_kind == "latest" else ("b" * 40)
            # Run the production main path through the disposable lag harness.
            result, alarm, sibling, work_root, trace, _latest = self.run_lag_scenario(
                scenario,
                version,
                installed_commit,
                published,
            )
            # Require the harness itself to complete after main returns.
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Bind the exact inner main status for success and fail-closed decisions.
            self.assertIn(f"main_rc={expected_rc}", result.stdout, scenario)
            # Prove execution continued after the function-local cleanup scope ended.
            self.assertIn("after_main=PASS", result.stdout, scenario)
            # Reject the production regression explicitly in both output channels.
            self.assertNotIn("unbound variable", result.stdout + result.stderr, scenario)
            # Require exact captured-work cleanup and sibling preservation.
            self.assertFalse(work_root.exists(), scenario)
            # Preserve the unrelated sibling bytes exactly.
            self.assertEqual(sibling.read_text(encoding="utf-8"), "preserve\n", scenario)
            # Read the optional decision log only when a successful check should emit one.
            trace_text = trace.read_text(encoding="utf-8") if trace.exists() else ""
            # Bind successful decision logging without weakening alarm cases.
            if log_fragment is not None:
                # Require the exact successful current or deploy-within decision.
                self.assertIn(log_fragment, trace_text, scenario)
            # Require success to leave no durable alarm behind.
            if alarm_reason is None:
                # A successful lag check must not invent an alarm.
                self.assertFalse(alarm.exists(), scenario)
            else:
                # A fail-closed decision must persist its exact bounded alarm reason.
                self.assertEqual(alarm.read_text(encoding="utf-8"), f"status=alarm\nreason={alarm_reason}\n", scenario)

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

    # Reproduce the systemd umask failure and prove directory-only normalization restores service traversal.
    @unittest.skipIf(os.name == "nt", "Unix directory modes require the required Linux CI host")
    def test_real_unzip_under_poller_umask_normalizes_only_candidate_directories(self):
        # Bind one files-only archive matching the production package shape that triggered the host failure.
        archive_path = self.root / "candidate.zip"
        # Create deterministic regular-file entries without explicit directory members.
        with zipfile.ZipFile(archive_path, "w") as archive:
            # Add one nested Python file whose bytes and mode must survive normalization.
            info = zipfile.ZipInfo("virtual_casino_simulator/casino/probe.py")
            # Identify the member as Unix-authored so unzip applies its ordinary file mode.
            info.create_system = 3
            # Preserve the production archive's non-executable regular-file mode.
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            # Write fixed bytes for before/after checksum comparison.
            archive.writestr(info, b"VALUE = 1\n")
        # Allocate a disposable extraction parent outside every repository and production path.
        extracted_root = self.root / "extracted"
        # Exercise the host's real unzip, restrictive umask, and checked-in normalizer in one shell process.
        harness = r'''
            umask 0027
            /usr/bin/unzip -q "__ARCHIVE__" -d "__EXTRACTED__"
            candidate="__EXTRACTED__/virtual_casino_simulator"
            before_mode="$(/usr/bin/stat -c '%a' "${candidate}")"
            before_file_mode="$(/usr/bin/stat -c '%a' "${candidate}/casino/probe.py")"
            before_hash="$(/usr/bin/sha256sum "${candidate}/casino/probe.py" | /usr/bin/cut -d' ' -f1)"
            source "__POLLER__"
            normalize_extracted_directories "${candidate}"
            after_mode="$(/usr/bin/stat -c '%a' "${candidate}")"
            nested_mode="$(/usr/bin/stat -c '%a' "${candidate}/casino")"
            after_file_mode="$(/usr/bin/stat -c '%a' "${candidate}/casino/probe.py")"
            after_hash="$(/usr/bin/sha256sum "${candidate}/casino/probe.py" | /usr/bin/cut -d' ' -f1)"
            printf '%s\n' "${before_mode}" "${after_mode}" "${nested_mode}" "${before_file_mode}" "${after_file_mode}" "${before_hash}" "${after_hash}"
        '''
        # Bind only disposable and checked-in paths into the listener-free shell fixture.
        harness = textwrap.dedent(harness).replace("__ARCHIVE__", bash_path(archive_path)).replace("__EXTRACTED__", bash_path(extracted_root)).replace("__POLLER__", bash_path(POLLER))
        # Require the normalization path to complete without service, listener, or network activity.
        result = self.run_sourced_poller(harness)
        # Parse the seven fixed evidence rows without depending on host-specific path spelling.
        rows = result.stdout.splitlines()
        # Prove the production umask reproduces the inaccessible release-root mode.
        self.assertEqual(rows[0], "750")
        # Require both root and nested candidate directories to become traversable.
        self.assertEqual(rows[1:3], ["755", "755"])
        # Preserve the regular file's extracted mode across host unzip implementations.
        self.assertEqual(rows[3], rows[4])
        # Keep the packaged Python file non-executable without overfitting unzip's umask handling.
        self.assertIn(rows[4], {"640", "644"})
        # Prove normalization changes no authenticated regular-file bytes.
        self.assertEqual(rows[5], rows[6])

    # Prove unsafe extracted shapes fail before any directory mode mutation.
    def test_directory_normalization_rejects_unsafe_tree_before_chmod(self):
        # Create one ordinary candidate root that passes the root-level containment check.
        candidate_root = self.root / "unsafe-candidate"
        # Materialize the test-owned root without links or special nodes.
        candidate_root.mkdir()
        # Bind a marker that a hostile-tree result must keep absent.
        chmod_marker = self.root / "chmod-called"
        # Replace only the tree scanner and chmod command to model an authenticated hostile entry portably.
        harness = r'''
            source "__POLLER__"
            log() { printf '%s\n' "$1" >&2; }
            find_unsafe_archive_entry() { printf '%s\n' '__HOSTILE_ENTRY__'; }
            chmod_archive_directories() { printf 'called\n' > "__CHMOD_MARKER__"; }
            normalize_extracted_directories "__CANDIDATE__"
        '''
        # Bind exact disposable paths while retaining the hostile entry only as scanner output.
        harness = textwrap.dedent(harness).replace("__POLLER__", bash_path(POLLER)).replace("__HOSTILE_ENTRY__", bash_path(candidate_root / "link")).replace("__CHMOD_MARKER__", bash_path(chmod_marker)).replace("__CANDIDATE__", bash_path(candidate_root))
        # Require the hostile shape to be handled as a bounded fail-closed result.
        result = self.run_sourced_poller(harness, check=False)
        # Accept only the expected nonzero rejection.
        self.assertNotEqual(result.returncode, 0)
        # Prove no chmod command ran after the scanner reported an unsafe shape.
        self.assertFalse(chmod_marker.exists())
        # Require the generic diagnostic without disclosing the hostile path.
        self.assertIn("archive_tree_unsafe", result.stderr)
        # Keep the modeled entry spelling out of sanitized failure output.
        self.assertNotIn(bash_path(candidate_root / "link"), result.stdout + result.stderr)

    # Prove the documented direct rollback drill resolves monitor identity without service-owned environment injection.
    def test_direct_identity_probe_reads_only_the_root_managed_monitor_file(self):
        # Bind one non-secret synthetic bearer that is long enough for the production policy.
        authorization = "Bearer " + ("unit-test-monitor-token-" * 2)
        # Write both allowlisted settings to the disposable root-managed-file fixture.
        monitor_env = self.root / "edge-monitor.env"
        # Use one fake HTTPS origin so no production request can occur.
        monitor_env.write_text(f"CASINO_EDGE_MONITOR_AUTHORIZATION={authorization}\nCASINO_PUBLIC_ORIGIN=https://fixture.invalid\n", encoding="utf-8", newline="\n")
        # Install a Python startup shim that replaces urllib before the embedded probe imports it.
        site_root = self.root / "python-site"
        # Create the isolated import root.
        site_root.mkdir()
        # Bind deterministic health and readiness responses without opening a listener.
        (site_root / "sitecustomize.py").write_text(
            "# Import JSON for deterministic standard-envelope bytes.\n"
            "import json\n"
            "# Import environment access for exact expected identity assertions.\n"
            "import os\n"
            "# Import urllib so its request seam can be replaced before the poller block imports it.\n"
            "import urllib.request\n"
            "# Provide one context-managed in-memory HTTP response.\n"
            "class Response:\n"
            "    # Retain exact response bytes.\n"
            "    def __init__(self, payload):\n"
            "        self.payload = payload\n"
            "    # Enter without allocating a network resource.\n"
            "    def __enter__(self):\n"
            "        return self\n"
            "    # Exit without suppressing failures.\n"
            "    def __exit__(self, *args):\n"
            "        return False\n"
            "    # Return the complete bounded payload.\n"
            "    def read(self, size):\n"
            "        return self.payload\n"
            "# Return exact public or authenticated envelopes and reject a missing bearer.\n"
            "def fake_urlopen(request, timeout=0):\n"
            "    # Require the fixture origin parsed from the monitor file.\n"
            "    if not request.full_url.startswith('https://fixture.invalid/'):\n"
            "        raise RuntimeError('unexpected origin')\n"
            "    # Build authenticated readiness only after exact header validation.\n"
            "    if request.full_url.endswith('/readyz'):\n"
            "        if request.get_header('Authorization') != os.environ['EXPECTED_AUTHORIZATION']:\n"
            "            raise RuntimeError('authorization missing')\n"
            "        payload = {'ok': True, 'data': {'ready': True, 'build': {'app_version': '0.9.5.79', 'sha': 'e' * 40}}}\n"
            "    else:\n"
            "        payload = {'ok': True, 'data': {'status': 'live'}}\n"
            "    # Encode the standard envelope exactly once.\n"
            "    return Response(json.dumps(payload).encode('utf-8'))\n"
            "# Replace only the request opener inside this child interpreter.\n"
            "urllib.request.urlopen = fake_urlopen\n",
            encoding="utf-8",
            newline="\n",
        )
        # Start from the safe test environment without injected monitor settings.
        environment = dict(self.environment)
        # Remove service-owned authorization so the file fallback is mandatory.
        environment.pop("CASINO_EDGE_MONITOR_AUTHORIZATION", None)
        # Remove service-owned origin so its allowlisted file fallback is also exercised.
        environment.pop("CASINO_PUBLIC_ORIGIN", None)
        # Load only the listener-free urllib fixture before embedded imports.
        environment["PYTHONPATH"] = bash_path(site_root)
        # Keep the expected value in the child-only test fixture without printing it.
        environment["EXPECTED_AUTHORIZATION"] = authorization
        # Bind the root-managed monitor file through the poller's reviewed override.
        environment["CASINO_EDGE_MONITOR_ENV"] = bash_path(monitor_env)
        # Source the script and invoke only its exact live-identity function.
        script = f'source "{bash_path(POLLER)}"\nverify_live_identity 0.9.5.79 {"e" * 40}\n'
        # Require the direct-command path to succeed without systemd EnvironmentFile injection.
        result = self.run_sourced_poller(script, environment=environment)
        # Require secret-free success output.
        self.assertNotIn(authorization, result.stdout + result.stderr)
        # Duplicate the protected row to prove ambiguous files fail closed.
        monitor_env.write_text(f"CASINO_EDGE_MONITOR_AUTHORIZATION={authorization}\nCASINO_EDGE_MONITOR_AUTHORIZATION={authorization}\n", encoding="utf-8", newline="\n")
        # Capture the expected nonzero outcome without reflecting the value.
        hostile = self.run_sourced_poller(script, environment=environment, check=False)
        # Require the duplicate protected assignment to fail before a request.
        self.assertNotEqual(hostile.returncode, 0)
        # Prove even the failure output never includes the bearer.
        self.assertNotIn(authorization, hostile.stdout + hostile.stderr)

    # Prove both readiness failure positions restore the predecessor and complete durable cleanup.
    def test_readiness_failures_restore_predecessor_remove_owned_work_and_alarm(self):
        # Exercise candidate failure and rollback-observation failure independently.
        for scenario in ("candidate-failure", "predecessor-failure"):
            # Run the full disposable rollback-drill state machine.
            result, releases_root, predecessor_root, selector_record, alarm_file, sentinel, _stable, trace = self.run_deployment_scenario(scenario)
            # Require a nonzero fail-closed result for either readiness boundary.
            self.assertNotEqual(result.returncode, 0, scenario)
            # Reject the production regression that masked the durable alarm.
            self.assertNotIn("unbound variable", result.stdout + result.stderr, scenario)
            # Require the exact predecessor selector after rollback.
            self.assertEqual(selector_record.read_text(encoding="utf-8").strip(), bash_path(predecessor_root), scenario)
            # Require one durable generic poll failure without secret or path data.
            self.assertEqual(alarm_file.read_text(encoding="utf-8"), "status=alarm\nreason=poll_failed\n", scenario)
            # Require every exact owned work directory to be gone.
            self.assertEqual(list(releases_root.glob(".poller.*")), [], scenario)
            # Prove cleanup preserved an unrelated direct child.
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n", scenario)
            # Require the candidate selector to have been attempted before the predecessor restore.
            trace_rows = trace.read_text(encoding="utf-8").splitlines()
            # Bind both exact release identities in the selector trace.
            self.assertIn("selector:" + bash_path(releases_root / ("c" * 40)), trace_rows, scenario)
            # Require the final selector event to restore the predecessor.
            self.assertEqual([row for row in trace_rows if row.startswith("selector:")][-1], "selector:" + bash_path(predecessor_root), scenario)

    # Prove a successful direct drill followed by the scheduled poll clears alarms only after convergence.
    def test_rollback_drill_then_poll_converges_without_changing_timer_contract(self):
        # Execute one complete drill and one complete poll in the same disposable host model.
        result, releases_root, _predecessor_root, selector_record, alarm_file, sentinel, stable_poller, trace = self.run_deployment_scenario("success", run_poll_after_drill=True)
        # Require both complete operations to succeed.
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Require the final selector to identify the exact candidate release root.
        self.assertEqual(selector_record.read_text(encoding="utf-8").strip(), bash_path(releases_root / ("c" * 40)))
        # Require the previously seeded alarm to be absent only after successful convergence.
        self.assertFalse(alarm_file.exists())
        # Require the verified candidate to install the next stable poller bytes.
        self.assertEqual(stable_poller.read_bytes(), POLLER.read_bytes())
        # Require no owned work directory residue after either operation.
        self.assertEqual(list(releases_root.glob(".poller.*")), [])
        # Require both candidate observations to leave the immutable release free of interpreter caches.
        self.assertEqual(list((releases_root / ("c" * 40)).rglob("__pycache__")), [])
        # Require no compiled Python bytecode to escape the cache-directory assertion.
        self.assertEqual(list((releases_root / ("c" * 40)).rglob("*.pyc")), [])
        # Preserve the unrelated direct child across both cleanup operations.
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
        # Read deterministic phase evidence.
        trace_rows = trace.read_text(encoding="utf-8").splitlines()
        # Require candidate, predecessor, then final candidate observation ordering.
        observations = [row for row in trace_rows if row.startswith("observe:")]
        # Bind both candidate observations around one predecessor rollback observation.
        self.assertEqual([row.split(":", 2)[1] for row in observations], ["0.9.5.79", "0.9.5.78", "0.9.5.79"])
        # Keep the checked-in timer cadence exact after the state-machine repair.
        self.assertIn("OnUnitActiveSec=5min", POLLER_TIMER.read_text(encoding="utf-8"))

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
        # Require the unit to reinforce the script's direct-command bytecode guard.
        self.assertIn("Environment=PYTHONDONTWRITEBYTECODE=1", service)
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
        # Keep scheduled monitor imports from mutating the selected release root.
        self.assertIn("Environment=PYTHONDONTWRITEBYTECODE=1", edge_service)
        # Require a privileged lag check after every otherwise-green edge observation.
        self.assertIn("ExecStartPost=+/usr/local/libexec/casino-release-poller check-lag", edge_service)

    # Prove immutable-root equality remains strict for unrelated extra files after bytecode writes are prevented.
    def test_release_root_comparison_rejects_unrelated_extra_files(self):
        # Create two initially identical release roots under the disposable fixture.
        candidate = self.root / "candidate"
        # Create the candidate root before writing its packaged fixture.
        candidate.mkdir()
        # Create the retained root independently so the comparison reads two trees.
        retained = self.root / "retained"
        # Materialize the retained release root.
        retained.mkdir()
        # Write one identical packaged file into the candidate.
        (candidate / "module.py").write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
        # Copy the exact packaged bytes into the retained root.
        (retained / "module.py").write_bytes((candidate / "module.py").read_bytes())
        # Invoke the production comparison once before and once after adding an unrelated file.
        harness = r'''
            source "__POLLER__"
            cd "__ROOT__"
            compare_release_roots candidate retained
            printf 'unexpected\n' > retained/operator-extra.txt
            if compare_release_roots candidate retained; then
              exit 91
            fi
        '''
        # Bind only test-owned paths into the inert sourced harness.
        harness = textwrap.dedent(harness).replace("__POLLER__", bash_path(POLLER)).replace("__ROOT__", bash_path(self.root))
        # Require the identical comparison to pass and the unrelated extra file to fail closed.
        result = self.run_sourced_poller(harness, check=False)
        # Accept only the expected handled comparison failure.
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Bind the exact rejection instead of accepting an unrelated shell failure.
        self.assertIn("existing release root does not match the verified archive", result.stderr)

    # Prove verification and provider compatibility gates precede selector mutation.
    def test_activation_order_is_fail_closed_and_provider_compatible(self):
        # Read the pull script as inert text for exact ordering assertions.
        text = POLLER.read_text(encoding="utf-8")
        # Require direct invocations to disable bytecode writes before any Python helper can execute.
        self.assertLess(text.index("export PYTHONDONTWRITEBYTECODE=1"), text.index("decide_versions()"))
        # Locate the first exact checksum/provenance verification.
        verification = text.index('verify_assets "${work_root}" "${latest_tag}" "${latest_commit}"')
        # Locate the preflight failure alarm that covers checksum and provenance rejection.
        alarm_trap = text.index('trap "${cleanup_command}" EXIT')
        # Locate the candidate provider compatibility proof.
        schema_check = text.index('check_schema_compatibility "${candidate_root}"')
        # Locate directory traversal repair after extraction and before candidate execution.
        directory_normalization = text.index('normalize_extracted_directories "${candidate_root}"')
        # Locate the second full verification performed through candidate bytes.
        candidate_verification = text.index('CASINO_VERIFY_ROOT="${candidate_root}" verify_assets')
        # Locate the first production-owned release fragment write.
        environment_install = text.index('install -m 0640 -o root -g root "${work_root}/release.env" "${RELEASE_ENV}"')
        # Locate the atomic selector switch independently.
        selector_switch = text.index('activate_release "${release_root}"', environment_install)
        # Prove both immutable-byte and schema gates precede every production mutation.
        self.assertLess(verification, environment_install)
        # Prove the poll-failure alarm is armed before corrupt bytes reach verification.
        self.assertLess(alarm_trap, verification)
        # Require the armed cleanup path to persist a bounded poll-failure alarm.
        self.assertIn('write_alarm "poll_failed"', text)
        # Require the EXIT path to own an immutable root argument outside function-local lifetime.
        self.assertIn("cleanup_deployment()", text)
        # Require the cleanup implementation to be defined before the deployment function rather than inside it.
        self.assertLess(text.index("cleanup_deployment()"), text.index("deploy_latest()"))
        # Prove schema compatibility is established before release.env mutation.
        self.assertLess(schema_check, environment_install)
        # Require directory-only normalization before any candidate verifier or schema command executes.
        self.assertLess(directory_normalization, candidate_verification)
        # Preserve the candidate verifier before its exact schema check.
        self.assertLess(candidate_verification, schema_check)
        # Prove release.env is staged before the current selector moves.
        self.assertLess(environment_install, selector_switch)
        # Require an error trap to restore the previous selector and fragment.
        self.assertIn("rollback_on_error()", text)
        # Require the documented drill to execute the same rollback implementation.
        self.assertIn('deploy_latest "rollback-drill"', text)
        # Reject migration, grant, database rollback, and global mutation authority.
        for forbidden in ("mysql_migrate.py apply", "SET GLOBAL", "GRANT ", "REVOKE ", "database rollback"):
            # Keep the deployment bridge read-only and application-only.
            self.assertNotIn(forbidden, text)

    # Prove the updater selects one bounded provider check and loads runtime configuration.
    def test_provider_compatibility_check_is_bounded_and_runtime_configured(self):
        # Read the immutable poller and service template without executing either host boundary.
        poller = POLLER.read_text(encoding="utf-8")
        service = POLLER_SERVICE.read_text(encoding="utf-8")
        # Preserve MySQL as the default for the existing TiltSeven deployment.
        self.assertIn('readonly STORAGE_PROVIDER="${CASINO_STORAGE_PROVIDER:-mysql}"', poller)
        # Require the only additional provider to use the read-only PostgreSQL runtime checker.
        self.assertIn('[[ "${STORAGE_PROVIDER}" =~ ^(mysql|postgres)$ ]]', poller)
        self.assertIn('"${root}/scripts/postgres_runtime_check.py"', poller)
        # Retain the exact MySQL schema-two compatibility gate for the existing deployment.
        self.assertIn('"${root}/scripts/mysql_migrate.py" bridge-check-schema2', poller)
        # Make runtime provider credentials available only to the root-owned compatibility poller.
        self.assertIn("EnvironmentFile=/etc/casino/casino.env", service)


# Run the focused suite directly when an operator requests it.
if __name__ == "__main__":
    # Propagate unittest's fail-closed process status.
    unittest.main()
