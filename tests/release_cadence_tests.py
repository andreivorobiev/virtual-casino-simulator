# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free TOOL-008/TEST-133 release-intent and batch-decision evidence.

Git histories and asset records are disposable fixtures. Every GitHub boundary is
mocked; this suite never publishes, opens a listener, or contacts production.
"""

import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

from scripts import release_cadence as policy
from scripts import release_publication as boundary


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


class ReleaseCadenceTests(unittest.TestCase):
    def setUp(self):
        self.before = {
            "application": "0.9.5.86", "source_baseline": "9.1.0",
            "modules": {"application": "9.74.1", "docs": "1.116.2", "contracts": "1.63.2",
                        "tests": "1.123.2", "tooling": "1.50.0"},
        }
        self.after = copy.deepcopy(self.before)
        self.after["application"] = "0.9.5.87"
        for name in ("application", "docs", "contracts"):
            parts = self.after["modules"][name].split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            self.after["modules"][name] = ".".join(parts)
        self.previous = {
            "app_version": "0.9.5.86", "source": {"commit_sha": "d" * 40, "release_tag": "v0.9.5.86"},
            "artifact": {"name": "virtual_casino_simulator_package.zip", "sha256": "e" * 64},
            "mysql_schema": {"minimum_version": 2, "expected_version": 5, "apply_policy": "held"},
        }
        self.old_compatibility = {
            "app_version": "0.9.5.86", "source_baseline": "9.1.0",
            "api_compatibility_matrix": "contracts/compatibility/module-api-matrix.json",
            "release_provenance_requirement": "TOOL-003", "release_channel": "restricted-preview-private-invite",
            "access_policy": {"admission": "manual-invite", "public_signup": "disabled", "live_oauth": "disabled"},
            "rollback": copy.deepcopy(policy.ROLLBACK), "modules": copy.deepcopy(self.before["modules"]),
            "notes": "Retained release identity.",
            "predecessor": {
                "app_version": "0.9.5.85", "compatibility_record": "contracts/compatibility/app-0.9.5.85.json",
                "required_artifact": "release-manifest.json", "source_commit_sha": "a" * 40,
                "artifact_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            },
        }
        self.candidate = copy.deepcopy(self.old_compatibility)
        self.candidate.update(app_version="0.9.5.87", modules=copy.deepcopy(self.after["modules"]))
        self.candidate["predecessor"] = {
            "app_version": "0.9.5.86", "compatibility_record": "contracts/compatibility/app-0.9.5.86.json",
            "required_artifact": "release-manifest.json", "source_commit_sha": "d" * 40,
            "artifact_sha256": "e" * 64, "manifest_sha256": hashlib.sha256(encoded(self.previous)).hexdigest(),
        }
        self.catalog = {"schema": "casino-mysql-migration-catalog-v1", "apply_policy": "held",
                        "minimum_runtime_version": 2, "expected_version": 5}
        self.changes = {
            policy.MANIFEST: policy.Change(encoded(self.before), encoded(self.after)),
            "pyproject.toml": policy.Change(b'[project]\nversion = "0.9.5.86"\n', b'[project]\nversion = "0.9.5.87"\n'),
            "web/core/pwa_version.js": policy.Change(b"export const PWA_APP_VERSION = '0.9.5.86';\n", b"export const PWA_APP_VERSION = '0.9.5.87';\n"),
            "contracts/compatibility/app-0.9.5.87.json": policy.Change(None, encoded(self.candidate), None),
        }
        for path in ("README.md", "CODEX_START_HERE.md", "VERSIONING.md", "RELEASE_NOTES.md"):
            self.changes[path] = policy.Change(b"Release 0.9.5.86\n", b"Release 0.9.5.87\n")
        for name in ("application", "docs", "contracts"):
            old = {"module": name, "version": self.before["modules"][name], "paths": [f"{name}/"]}
            new = {**old, "version": self.after["modules"][name]}
            self.changes[f"modules/{name}.json"] = policy.Change(encoded(old), encoded(new))
        self.changes[policy.GENERATED_REQUIREMENTS] = policy.Change(self.generated(self.before), self.generated(self.after))
        self.pull = {"merge_commit_sha": "2" * 40, "merged_at": "2026-08-31T22:00:00Z",
                     "base": {"ref": "main"}, "head": {"ref": "codex/release-v0.9.5.87"},
                     "title": "Release v0.9.5.87", "body": "Release-only: yes\n"}

    def generated(self, manifest):
        rows = [f"Packaged application release: {manifest['application']}", "## Independent module revisions"]
        rows.extend(f"- {name}: {value}" for name, value in manifest["modules"].items())
        return ("\n".join(rows) + "\n## Requirements\n- TOOL-008 remains governed.\n").encode()

    def arguments(self):
        return dict(before_sha="1" * 40, head_sha="2" * 40, first_parent="1" * 40,
                    forced=False, protected=True, before_manifest=self.before, after_manifest=self.after,
                    changes=self.changes, old_compatibility=self.old_compatibility, candidate=self.candidate,
                    catalog=self.catalog, pull_request=self.pull)

    def release(self, version="0.9.5.87", head="2" * 40):
        return {"tag_name": f"v{version}", "target_commitish": head, "draft": False, "prerelease": False,
                "published_at": "2026-08-31T22:00:00Z",
                "assets": [{"name": name, "state": "uploaded", "size": 123} for name in sorted(policy.ASSETS)]}

    def test_code_only_is_noop_without_wrapper_or_release_observations(self):
        arguments = self.arguments()
        arguments.update(after_manifest=self.before, changes=None, pull_request=None, candidate=None)
        self.assertEqual(policy.publication_intent(**arguments).decision, "noop")

    def test_complete_semantic_wrapper_is_eligible(self):
        plan = policy.publication_intent(**self.arguments())
        self.assertEqual((plan.decision, plan.release_tag, plan.predecessor_tag), ("publish", "v0.9.5.87", "v0.9.5.86"))
        self.assertEqual(policy.validate_predecessor(self.candidate, encoded(self.previous), "d" * 40), "v0.9.5.86")

    def test_missing_forced_unprotected_nonlinear_history_fails_even_for_noop(self):
        for field, value in (("before_sha", "0" * 40), ("before_sha", "main"), ("head_sha", "short"),
                             ("forced", True), ("forced", None), ("protected", False), ("first_parent", "3" * 40)):
            arguments = self.arguments()
            arguments.update(after_manifest=self.before, **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_noncanonical_downgrade_skipped_patch_and_reserved_leap_fail(self):
        for value in ("0.9.5.85", "0.9.5.88", "0.9.6.0", "00.9.5.87", "0.9.5.87\n"):
            arguments = self.arguments()
            arguments["after_manifest"] = {**self.after, "application": value}
            with self.subTest(value=value), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_unrelated_paths_and_prior_compatibility_are_never_wrapper_metadata(self):
        for path in ("casino/app.py", "contracts/openapi/core-v1.yaml", "migrations/mysql/catalog.json",
                     "web/games/roulette.js", "scripts/release_cadence.py", ".github/workflows/ci.yml",
                     "docs/releases/whats_new.json", "web/i18n/en-US/shell.json",
                     "contracts/compatibility/app-0.9.5.86.json", "tests/unrelated.py"):
            arguments = self.arguments()
            arguments["changes"] = {**self.changes, path: policy.Change(b"old\n", b"new\n")}
            with self.subTest(path=path), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_release_documents_and_compatibility_notes_are_identity_only(self):
        for path in policy.RELEASE_DOCS:
            if path not in self.changes:
                continue
            arguments = self.arguments()
            original = self.changes[path]
            arguments["changes"] = {**self.changes, path: policy.Change(original.before, original.after + b"Unreviewed claim.\n")}
            with self.subTest(path=path), self.assertRaisesRegex(policy.PolicyError, "wrapper_release_document_behavior"):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        candidate = copy.deepcopy(self.candidate)
        candidate["notes"] = "Unreviewed behavior claim."
        arguments["candidate"] = candidate
        arguments["changes"] = {**self.changes, "contracts/compatibility/app-0.9.5.87.json":
                                policy.Change(None, encoded(candidate), None)}
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_compatibility_notes"):
            policy.publication_intent(**arguments)

    def test_pwa_package_descriptor_and_generated_behavior_fail(self):
        mutations = {
            "web/core/pwa_version.js": b"export const PWA_APP_VERSION = '0.9.5.87';\nactivateProvider();\n",
            "pyproject.toml": b'[project]\nversion = "0.9.5.87"\ndependencies = ["unreviewed"]\n',
            "modules/application.json": encoded({"module": "application", "version": "9.74.2", "paths": ["everything/"]}),
            policy.GENERATED_REQUIREMENTS: self.generated(self.after).replace(b"governed", b"waived"),
        }
        for path, after in mutations.items():
            arguments = self.arguments()
            arguments["changes"] = {**self.changes, path: policy.Change(self.changes[path].before, after)}
            with self.subTest(path=path), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_extra_missing_and_nonpatch_module_bumps_fail(self):
        for name, value in (("tooling", "1.50.1"), ("tests", "1.123.3"),
                            ("application", "9.74.1"), ("docs", "1.117.0")):
            arguments = self.arguments()
            after = copy.deepcopy(self.after)
            after["modules"][name] = value
            arguments["after_manifest"] = after
            with self.subTest(name=name, value=value), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_added_deleted_linked_and_executable_wrapper_files_fail(self):
        for change in (policy.Change(None, b"new", None), policy.Change(b"old", None, after_mode=None),
                       policy.Change(b"old", b"new", after_mode="120000"),
                       policy.Change(b"old", b"new", after_mode="100755")):
            arguments = self.arguments()
            arguments["changes"] = {**self.changes, "README.md": change}
            with self.subTest(change=change), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_test_identity_substitution_requires_tests_bump_and_preserves_assertions(self):
        old = b"def test_identity(self):\n    self.assertEqual('0.9.5.86', 'v0.9.5.85')\n"
        new = b"def test_identity(self):\n    self.assertEqual('0.9.5.87', 'v0.9.5.86')\n"
        changes = {**self.changes, "tests/release_artifact_tests.py": policy.Change(old, new)}
        arguments = self.arguments()
        arguments["changes"] = changes
        with self.assertRaises(policy.PolicyError):
            policy.publication_intent(**arguments)
        self.after["modules"]["tests"] = "1.123.3"
        self.candidate["modules"]["tests"] = "1.123.3"
        changes[policy.MANIFEST] = policy.Change(encoded(self.before), encoded(self.after))
        changes["contracts/compatibility/app-0.9.5.87.json"] = policy.Change(None, encoded(self.candidate), None)
        changes[policy.GENERATED_REQUIREMENTS] = policy.Change(self.generated(self.before), self.generated(self.after))
        changes["modules/tests.json"] = policy.Change(encoded({"module": "tests", "version": "1.123.2"}),
                                                       encoded({"module": "tests", "version": "1.123.3"}))
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
        changes["tests/release_artifact_tests.py"] = policy.Change(old, new.replace(b"assertEqual", b"assertNotEqual"))
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_test_behavior"):
            policy.publication_intent(**arguments)

    def test_review_identity_and_release_declaration_are_mandatory(self):
        for change in ({"merge_commit_sha": "9" * 40}, {"merged_at": None}, {"base": {"ref": "feature"}},
                       {"head": {"ref": "codex/product-change"}}, {"title": "Release v0.9.5.88"},
                       {"body": "Release-only: yes\nRelease-only: yes\n"}, {"body": "Release-only: no"}):
            arguments = self.arguments()
            arguments["pull_request"] = {**self.pull, **change}
            with self.subTest(change=change), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)

    def test_predecessor_corruption_source_archive_and_schema_fail(self):
        for mutate in (lambda row: row["source"].update(commit_sha="f" * 40),
                       lambda row: row["source"].update(release_tag="v0.9.5.85"),
                       lambda row: row["artifact"].update(sha256="f" * 64),
                       lambda row: row["mysql_schema"].update(minimum_version=3),
                       lambda row: row["mysql_schema"].update(apply_policy="enabled")):
            manifest = copy.deepcopy(self.previous)
            mutate(manifest)
            raw = encoded(manifest)
            candidate = copy.deepcopy(self.candidate)
            candidate["predecessor"]["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(policy.PolicyError):
                policy.validate_predecessor(candidate, raw, "d" * 40)
        with self.assertRaises(policy.PolicyError):
            policy.validate_predecessor(self.candidate, encoded(self.previous) + b" ", "d" * 40)

    def test_creation_and_complete_duplicate_reuse_are_distinct(self):
        self.assertEqual(policy.release_state("0.9.5.87", "2" * 40, None, None), "create")
        self.assertEqual(policy.release_state("0.9.5.87", "2" * 40, "2" * 40, self.release()), "reuse")

    def test_partial_draft_failed_upload_and_wrong_identity_never_reuse(self):
        for mutate in (lambda row: row.update(draft=True), lambda row: row.update(prerelease=True),
                       lambda row: row.update(target_commitish="main"), lambda row: row.update(published_at=None),
                       lambda row: row["assets"].pop(), lambda row: row["assets"][0].update(state="new"),
                       lambda row: row["assets"][0].update(size=0)):
            release = self.release()
            mutate(release)
            with self.assertRaises(policy.PolicyError):
                policy.release_state("0.9.5.87", "2" * 40, "2" * 40, release)
        for tag, release in ((None, self.release()), ("2" * 40, None), ("3" * 40, self.release())):
            with self.assertRaises(policy.PolicyError):
                policy.release_state("0.9.5.87", "2" * 40, tag, release)

    def test_only_authoritative_404_can_mean_absence(self):
        self.assertIsNone(policy.api_result(404, None, allow_absent=True))
        for status in (0, 301, 401, 403, 429, 500, 503):
            with self.subTest(status=status), self.assertRaises(policy.PolicyError):
                policy.api_result(status, {}, allow_absent=True)
        with self.assertRaises(policy.PolicyError):
            policy.api_result(404, None)

    def test_annotated_tags_are_peeled_and_ambiguous_records_fail(self):
        tag = "v0.9.5.87"
        raw = f"{'a' * 40}\trefs/tags/{tag}\n{'2' * 40}\trefs/tags/{tag}^{{}}\n".encode()
        self.assertEqual(boundary.peel_tag_output(raw, tag), "2" * 40)
        self.assertEqual(boundary.peel_tag_output(f"{'2' * 40}\trefs/tags/{tag}\n".encode(), tag), "2" * 40)
        self.assertIsNone(boundary.peel_tag_output(b"", tag))
        with self.assertRaises(policy.PolicyError):
            boundary.peel_tag_output(raw + raw, tag)

    def test_api_transport_and_auth_failures_cannot_reach_creation(self):
        for error in (URLError("synthetic-private-detail"), HTTPError("https://api.github.com", 403, "private", {}, None)):
            with mock.patch.dict("os.environ", {"GH_TOKEN": "synthetic-not-a-token"}), \
                 mock.patch.object(boundary, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaisesRegex(policy.PolicyError, "github_observation_failed"):
                    boundary.github_get(f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.87", allow_absent=True)

    def test_checksum_inventory_and_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = {"release-manifest.json": b"{}\n", "virtual_casino_simulator_package.zip": b"synthetic-archive"}
            for name, raw in payloads.items():
                (root / name).write_bytes(raw)
            rows = [f"{hashlib.sha256(raw).hexdigest()}  {name}" for name, raw in payloads.items()]
            (root / "checksums.txt").write_text("\n".join(rows) + "\n", encoding="ascii")
            boundary.verify_checksums(root)
            (root / "release-manifest.json").write_bytes(b"changed")
            with self.assertRaises(policy.PolicyError):
                boundary.verify_checksums(root)
            (root / "checksums.txt").write_text(rows[0] + "\n" + rows[0] + "\n", encoding="ascii")
            with self.assertRaises(policy.PolicyError):
                boundary.verify_checksums(root)

    def test_duplicate_json_keys_do_not_shadow_release_policy(self):
        with self.assertRaises(policy.PolicyError):
            policy.object_json('{"application":"0.9.5.86","application":"0.9.5.87"}')

    def batch_observation(self):
        return {"main_sha": "2" * 40, "released_sha": "d" * 40, "live_sha": "d" * 40,
                "app_version": "0.9.5.86", "predecessor_manifest_sha256": "e" * 64,
                "first_window": "2026-08-31T15:00:00-07:00", "now": "2026-08-31T15:00:00-07:00",
                "last_claimed_window": None, "publication": "idle", "rollout": "idle", "open_wrapper": False}

    def test_batch_no_change_not_due_and_eligible_are_explicit(self):
        observation = self.batch_observation()
        eligible = policy.batch_plan(observation)
        self.assertEqual((eligible["decision"], eligible["candidate_version"]), ("eligible", "0.9.5.87"))
        self.assertEqual(eligible, policy.batch_plan(dict(reversed(list(observation.items())))))
        self.assertEqual(policy.batch_plan({**observation, "main_sha": "d" * 40})["decision"], "no-change")
        self.assertEqual(policy.batch_plan({**observation, "now": "2026-08-31T14:59:59-07:00"})["decision"], "not-due")

    def test_active_failed_unadopted_or_claimed_window_is_blocked(self):
        observation = self.batch_observation()
        for change in ({"publication": "active"}, {"publication": "failed"}, {"rollout": "active"},
                       {"rollout": "failed"}, {"open_wrapper": True}, {"live_sha": "a" * 40},
                       {"last_claimed_window": observation["first_window"]}):
            with self.subTest(change=change):
                self.assertEqual(policy.batch_plan({**observation, **change})["decision"], "blocked")

    def test_next_and_missed_windows_propose_one_batch_not_catchup_releases(self):
        observation = self.batch_observation()
        observation.update(last_claimed_window=observation["first_window"], now="2026-08-31T22:00:00-07:00")
        plan = policy.batch_plan(observation)
        self.assertEqual(plan["decision"], "eligible")
        self.assertEqual(plan["window"], "2026-09-01T04:00:00+00:00")
        self.assertEqual(len(plan["plan_sha256"]), 64)

    def test_batch_rejects_ambiguous_clock_and_unknown_states(self):
        for change in ({"now": "2026-08-31T15:00:00"}, {"publication": "maybe"}, {"open_wrapper": "false"}):
            with self.subTest(change=change), self.assertRaises(policy.PolicyError):
                policy.batch_plan({**self.batch_observation(), **change})

    def test_legacy_publication_aggregate_exhaustive_truth_table(self):
        states = ("success", "failure", "cancelled", "skipped", "")
        for intent, decision, writer in itertools.product(states, ("noop", "publish", ""), states):
            expected = (intent, decision, writer) in {("success", "noop", "skipped"), ("success", "publish", "success")}
            with self.subTest(intent=intent, decision=decision, writer=writer):
                self.assertEqual(policy.publication_result(intent, decision, writer), expected)
                with mock.patch("sys.stdout", new=io.StringIO()), mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(boundary.main(["result", "--intent-result", intent, "--decision", decision,
                                                    "--writer-result", writer]), 0 if expected else 1)

    def test_real_git_wrapper_observation_requires_unique_pr_and_locked_main(self):
        with tempfile.TemporaryDirectory(prefix="casino-cadence-wrapper-") as temporary:
            root = Path(temporary)
            self.git(root, "init", "-b", "main")
            for path, change in self.changes.items():
                if change.before is not None:
                    self.write_fixture(root, path, change.before)
            self.write_fixture(root, "contracts/compatibility/app-0.9.5.86.json", encoded(self.old_compatibility))
            self.write_fixture(root, "migrations/mysql/catalog.json", encoded(self.catalog))
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "synthetic accepted source")
            before = self.git(root, "rev-parse", "HEAD")
            for path, change in self.changes.items():
                self.write_fixture(root, path, change.after)
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "synthetic release wrapper")
            head = self.git(root, "rev-parse", "HEAD")
            event = {"ref": "refs/heads/main", "before": before, "after": head, "forced": False}
            environment = {"GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": boundary.REPOSITORY,
                           "GITHUB_REF": "refs/heads/main", "GITHUB_REF_PROTECTED": "true", "GITHUB_SHA": head,
                           "GITHUB_RUN_ATTEMPT": "1"}
            pull = {**self.pull, "merge_commit_sha": head}
            responses = {
                f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100": [pull],
                f"repos/{boundary.REPOSITORY}/git/ref/heads/main": {"object": {"type": "commit", "sha": head}},
                f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.86": self.release("0.9.5.86", "d" * 40),
                f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.87": None,
            }
            with mock.patch.object(boundary, "github_get", side_effect=lambda path, **_kwargs: responses[path]), \
                 mock.patch.object(boundary, "tag_commit", side_effect=lambda _root, tag: "d" * 40 if tag.endswith(".86") else None), \
                 mock.patch.object(boundary, "manifest_bytes", return_value=encoded(self.previous)):
                plan = boundary.inspect_publication(event, environment, root, under_lock=True)
                self.assertEqual((plan["decision"], plan["release_state"], plan["source_sha"]), ("publish", "create", head))
                responses[f"repos/{boundary.REPOSITORY}/git/ref/heads/main"]["object"]["sha"] = "f" * 40
                with self.assertRaisesRegex(policy.PolicyError, "protected_main_moved"):
                    boundary.inspect_publication(event, environment, root, under_lock=True)
                responses[f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100"] = [pull, pull]
                with self.assertRaisesRegex(policy.PolicyError, "wrapper_pull_ambiguous"):
                    boundary.inspect_publication(event, environment, root)
                with self.assertRaisesRegex(policy.PolicyError, "push_publication_rerun_prohibited"):
                    boundary.inspect_publication(event, {**environment, "GITHUB_RUN_ATTEMPT": "2"}, root)
                responses[f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100"] = []
                with self.assertRaisesRegex(policy.PolicyError, "wrapper_pull_ambiguous"):
                    boundary.inspect_publication(event, environment, root)

    def write_fixture(self, root, path, raw):
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)

    def test_real_git_code_only_push_never_queries_github(self):
        with tempfile.TemporaryDirectory(prefix="casino-cadence-git-") as temporary:
            root = Path(temporary)
            self.git(root, "init", "-b", "main")
            (root / "modules").mkdir()
            (root / policy.MANIFEST).write_bytes(encoded(self.before))
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "synthetic baseline")
            before = self.git(root, "rev-parse", "HEAD")
            (root / "README.md").write_text("Accepted code-only change\n", encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "synthetic code change")
            head = self.git(root, "rev-parse", "HEAD")
            event = {"ref": "refs/heads/main", "before": before, "after": head, "forced": False}
            environment = {"GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": boundary.REPOSITORY,
                           "GITHUB_REF": "refs/heads/main", "GITHUB_REF_PROTECTED": "true", "GITHUB_SHA": head}
            with mock.patch.object(boundary, "github_get", side_effect=AssertionError("unexpected network")):
                self.assertEqual(boundary.inspect_publication(event, environment, root)["decision"], "noop")
                with self.assertRaises(policy.PolicyError):
                    boundary.inspect_publication({**event, "before": "f" * 40}, environment, root)

    def git(self, root, *arguments):
        result = subprocess.run(["git", "-c", "user.name=Release Test", "-c", "user.email=release-test@example.invalid",
                                 "-c", "commit.gpgsign=false", *arguments], cwd=root, check=True,
                                capture_output=True, timeout=20)
        return result.stdout.decode().strip()


if __name__ == "__main__":
    unittest.main()
