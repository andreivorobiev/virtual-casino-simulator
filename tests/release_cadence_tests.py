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
        self.before = { "application": "0.9.5.86", "source_baseline": "9.1.0", "modules": {"application": "9.74.1", "docs": "1.116.2", "contracts": "1.63.2",
                        "tests": "1.123.2", "tooling": "1.50.0"}, }
        self.after = copy.deepcopy(self.before)
        self.after["application"] = "0.9.5.87"
        for name in ("application", "docs", "contracts"):
            parts = self.after["modules"][name].split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            self.after["modules"][name] = ".".join(parts)
        self.previous = { "app_version": "0.9.5.86", "source": {"commit_sha": "d" * 40, "release_tag": "v0.9.5.86"},
            "artifact": {"name": "virtual_casino_simulator_package.zip", "sha256": "e" * 64}, "mysql_schema": {"minimum_version": 2, "expected_version": 5, "apply_policy": "held"},
        }
        self.old_compatibility = { "app_version": "0.9.5.86", "source_baseline": "9.1.0", "api_compatibility_matrix": "contracts/compatibility/module-api-matrix.json",
            "release_provenance_requirement": "TOOL-003", "release_channel": "restricted-preview-private-invite",
            "access_policy": {"admission": "manual-invite", "public_signup": "disabled", "live_oauth": "disabled"},
            "rollback": copy.deepcopy(policy.ROLLBACK), "modules": copy.deepcopy(self.before["modules"]), "notes": "Retained release identity.", "predecessor": {
                "app_version": "0.9.5.85", "compatibility_record": "contracts/compatibility/app-0.9.5.85.json",
                "required_artifact": "release-manifest.json", "source_commit_sha": "a" * 40, "artifact_sha256": "b" * 64, "manifest_sha256": "c" * 64, }, }
        self.candidate = copy.deepcopy(self.old_compatibility)
        self.candidate.update(app_version="0.9.5.87", modules=copy.deepcopy(self.after["modules"]))
        self.candidate["predecessor"] = { "app_version": "0.9.5.86", "compatibility_record": "contracts/compatibility/app-0.9.5.86.json",
            "required_artifact": "release-manifest.json", "source_commit_sha": "d" * 40,
            "artifact_sha256": "e" * 64, "manifest_sha256": hashlib.sha256(encoded(self.previous)).hexdigest(), }
        self.source_tree = "5" * 40
        self.source_facts = { "schema": policy.SOURCE_FACTS_SCHEMA, "source_sha": "1" * 40, "tree_sha": self.source_tree,
            "modules": copy.deepcopy(self.after["modules"]), "permanent_requirement_count": 1130, "deployable_file_count": 870}
        self.accepted_deltas = [ {"pull_request": 1094, "merge_sha": "6" * 40}, {"pull_request": 1096, "merge_sha": "7" * 40}, {"pull_request": 1082, "merge_sha": "8" * 40}]
        self.candidate.update( source_facts=copy.deepcopy(self.source_facts), accepted_deltas=copy.deepcopy(self.accepted_deltas), release_facts_sha256=policy.release_facts_sha256(
                self.source_facts, self.accepted_deltas, self.candidate["predecessor"]), notes=policy.render_candidate_notes("0.9.5.87", self.candidate["predecessor"],
                                                self.source_facts, self.accepted_deltas))
        self.catalog = {"schema": "casino-mysql-migration-catalog-v1", "apply_policy": "held", "minimum_runtime_version": 2, "expected_version": 5}
        self.changes = { policy.MANIFEST: policy.Change(encoded(self.before), encoded(self.after)),
            "pyproject.toml": policy.Change(b'[project]\nversion = "0.9.5.86"\n', b'[project]\nversion = "0.9.5.87"\n'),
            "web/core/pwa_version.js": policy.Change(b"export const PWA_APP_VERSION = '0.9.5.86';\n", b"export const PWA_APP_VERSION = '0.9.5.87';\n"),
            "contracts/compatibility/app-0.9.5.87.json": policy.Change(None, encoded(self.candidate), None), }
        document_bytes = { "README.md": b"Packaged application release: `0.9.5.86`\n", "CODEX_START_HERE.md": b"- Packaged application release: `0.9.5.86`\n"
                                   b"- [`RELEASE_NOTES.md`](RELEASE_NOTES.md) - Virtual Casino Simulator v0.9.5.86 Release Notes\n",
            "VERSIONING.md": b"- Packaged application release: `0.9.5.86`\n" b"| Runtime, API, browser shell, Admin | Packaged application release (`0.9.5.86`) |\n",
            "docs/production_cicd_runbook.md": b"Packaged release numbers use the four-part scheme `0.9.5.86`.\nHistorical 0.9.5.86 stays.\n",
            "docs/release_artifacts.md": b"The authenticated compatibility record, not GitHub release-list ordering, selects v0.9.5.86.\nBuild a canonical tagged v0.9.5.86 candidate.\npython scripts/make_release.py --release-tag v0.9.5.86\nFor v0.9.5.86, retain v0.9.5.85.\n",
            "docs/release_versioning.md": b"0.9.5.86\nv0.9.5.86\nHistorical `0.9.5.86` stays.\n",
            "RELEASE_NOTES.md": b"# Virtual Casino Simulator v0.9.5.86 Release Notes\n\nHistorical release evidence.\n"}
        replacements = policy._identity_replacements("0.9.5.86", "0.9.5.87", self.old_compatibility, self.candidate)
        for name in ("application", "docs", "contracts"):
            replacements[self.before["modules"][name]] = self.after["modules"][name]
        for path, before_bytes in document_bytes.items():
            after_bytes = policy._anchored_release_document(path, before_bytes, "0.9.5.86", "0.9.5.87", replacements, "0.9.5.86", self.source_facts, self.accepted_deltas)
            self.changes[path] = policy.Change(before_bytes, after_bytes)
        for name in ("application", "docs", "contracts"):
            old = {"module": name, "version": self.before["modules"][name], "paths": [f"{name}/"]}
            new = {**old, "version": self.after["modules"][name]}
            self.changes[f"modules/{name}.json"] = policy.Change(encoded(old), encoded(new))
        self.changes[policy.GENERATED_REQUIREMENTS] = policy.Change(self.generated(self.before), self.generated(self.after))
        self.wrapper_sha = "3" * 40
        self.tree_sha = "4" * 40
        self.pull = { "number": 1096, "merge_commit_sha": "2" * 40, "merged_at": "2026-08-31T22:00:00Z", "base": {"ref": "main", "sha": "1" * 40,
                     "repo": {"full_name": policy.REPOSITORY, "owner": {"login": policy.REPOSITORY_OWNER, "id": 100, "type": "User"}}},
            "head": {"ref": "codex/release-v0.9.5.87", "sha": self.wrapper_sha, "repo": {"full_name": policy.REPOSITORY}},
            "user": {"login": policy.REPOSITORY_OWNER, "id": 100, "type": "User"}, "title": "Release v0.9.5.87", "body": "Release-only: yes\n",
            "updated_at": "2026-08-31T21:57:00Z", }
    def generated(self, manifest):
        rows = [f"Packaged application release: {manifest['application']}", "## Independent module revisions"]
        rows.extend(f"- {name}: {value}" for name, value in manifest["modules"].items())
        return ("\n".join(rows) + "\n## Requirements\n- TOOL-008 remains governed.\n").encode()
    def candidate_for(self, facts, deltas, modules=None):
        """Rebind one synthetic candidate to independently supplied exact facts."""
        candidate = copy.deepcopy(self.candidate)
        candidate.update(modules=copy.deepcopy(modules or facts["modules"]), source_facts=copy.deepcopy(facts), accepted_deltas=copy.deepcopy(deltas),
                         release_facts_sha256=policy.release_facts_sha256( facts, deltas, candidate["predecessor"]), notes=policy.render_candidate_notes(
                             candidate["app_version"], candidate["predecessor"], facts, deltas))
        return candidate
    def projected_changes(self, changes, candidate, facts, deltas, before_manifest=None, after_manifest=None):
        """Project candidate-authored bytes while keeping every before blob independent."""
        projected = dict(changes)
        projected["contracts/compatibility/app-0.9.5.87.json"] = policy.Change(None, encoded(candidate), None)
        before_manifest, after_manifest = before_manifest or self.before, after_manifest or self.after
        replacements = policy._identity_replacements( before_manifest["application"], after_manifest["application"], self.old_compatibility, candidate)
        for name, before_value in before_manifest["modules"].items():
            after_value = after_manifest["modules"][name]
            if before_value != after_value:
                replacements[before_value] = after_value
        for path in policy.RELEASE_DOCS.intersection(projected):
            change = projected[path]
            after = policy._anchored_release_document( path, change.before, before_manifest["application"], after_manifest["application"],
                replacements, candidate["predecessor"]["app_version"], facts, deltas)
            projected[path] = policy.Change(change.before, after, change.before_mode, change.after_mode)
        return projected
    def arguments(self):
        evidence = self.admission_evidence(self.wrapper_sha, self.tree_sha, self.pull)
        return dict(before_sha="1" * 40, head_sha="2" * 40, first_parent="1" * 40, forced=False, protected=True, before_manifest=self.before, after_manifest=self.after,
                    changes=self.changes, old_compatibility=self.old_compatibility, candidate=self.candidate,
                    catalog=self.catalog, pull_request=self.pull, second_parent=self.wrapper_sha, head_tree=self.tree_sha, wrapper_tree=self.tree_sha, source_tree=self.source_tree,
                    source_facts=copy.deepcopy(self.source_facts), accepted_deltas=copy.deepcopy(self.accepted_deltas), **evidence)
    def admission_evidence(self, wrapper_sha, tree_sha, pull):
        """Build complete synthetic provider evidence for one immutable PR head."""
        reviews = [{ "id": 501, "state": "APPROVED", "commit_id": wrapper_sha, "user": {"login": "release-reviewer", "id": 200, "type": "User"},
            "author_association": "COLLABORATOR", "submitted_at": "2026-08-31T21:55:00Z", }]
        comments = []
        metadata_sha256 = policy.wrapper_premerge_metadata_sha256(pull, tree_sha)
        for index, role in enumerate(policy.OPERATIONAL_ACCEPTANCE_ROLES, start=1):
            comments.append({ "id": 600 + index, "body": policy.operational_receipt(role, wrapper_sha, tree_sha, metadata_sha256),
                "created_at": "2026-08-31T21:56:00Z", "updated_at": "2026-08-31T21:56:00Z", "author_association": "OWNER",
                "user": {"login": policy.REPOSITORY_OWNER, "id": 100, "type": "User"}, })
        runs, jobs, checks, suites = [], {}, {}, {}
        for index, (path, gate_name) in enumerate(policy.REQUIRED_WORKFLOW_GATES.items(), start=1):
            run_id, job_id, suite_id = 700 + index, 800 + index, 900 + index
            runs.append({ "id": run_id, "path": path, "event": "pull_request", "run_attempt": 1, "status": "completed", "conclusion": "success", "head_sha": wrapper_sha,
                "updated_at": "2026-08-31T21:54:00Z", "head_branch": pull["head"]["ref"], "check_suite_id": suite_id, "head_commit": {"id": wrapper_sha, "tree_id": tree_sha},
                "repository": {"full_name": policy.REPOSITORY}, "head_repository": {"full_name": policy.REPOSITORY}, "pull_requests": [], })
            job = { "id": job_id, "name": gate_name, "run_id": run_id, "run_attempt": 1, "head_sha": wrapper_sha, "status": "completed", "conclusion": "success",
                "completed_at": "2026-08-31T21:54:00Z", "check_run_url": f"https://api.github.com/repos/{policy.REPOSITORY}/check-runs/{job_id}", }
            jobs[run_id] = {"total_count": 1, "jobs": [job]}
            checks[job_id] = { "id": job_id, "name": gate_name, "head_sha": wrapper_sha, "status": "completed", "conclusion": "success", "completed_at": "2026-08-31T21:54:00Z",
                "check_suite": {"id": suite_id}, "app": {"id": policy.GITHUB_ACTIONS_APP_ID, "slug": "github-actions"}, }
            suites[suite_id] = { "id": suite_id, "head_sha": wrapper_sha, "head_branch": pull["head"]["ref"], "status": "completed", "conclusion": "success",
                "updated_at": "2026-08-31T21:54:00Z", "app": {"id": policy.GITHUB_ACTIONS_APP_ID, "slug": "github-actions"}, }
        return { "reviews": reviews, "comments": comments, "reviewer_permissions": {200: { "permission": "write", "role_name": "write",
                "user": {"login": "release-reviewer", "id": 200, "type": "User"}, }}, "merge_pull": copy.deepcopy(pull), "head_pulls": [copy.deepcopy(pull)],
            "workflow_runs": {"total_count": len(runs), "workflow_runs": runs}, "workflow_jobs": jobs, "check_runs": checks, "check_suites": suites, }
    def release(self, version="0.9.5.87", head="2" * 40):
        return {"tag_name": f"v{version}", "target_commitish": head, "draft": False, "prerelease": False, "published_at": "2026-08-31T22:00:00Z",
                "assets": [{"name": name, "state": "uploaded", "size": 123} for name in sorted(policy.ASSETS)]}
    def test_code_only_is_noop_without_wrapper_or_release_observations(self):
        arguments = self.arguments()
        arguments.update(after_manifest=self.before, changes=None, pull_request=None, candidate=None)
        self.assertEqual(policy.publication_intent(**arguments).decision, "noop")
    def test_complete_semantic_wrapper_is_eligible(self):
        plan = policy.publication_intent(**self.arguments())
        self.assertEqual((plan.decision, plan.release_tag, plan.predecessor_tag), ("publish", "v0.9.5.87", "v0.9.5.86"))
        self.assertRegex(plan.admission_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(policy.validate_predecessor(self.candidate, encoded(self.previous), "d" * 40), "v0.9.5.86")
    def test_premerge_receipt_digest_survives_only_legitimate_merge_fields(self):
        open_pull = copy.deepcopy(self.pull)
        open_pull.update(merge_commit_sha="5" * 40, merged_at=None)
        before_merge = policy.wrapper_premerge_metadata_sha256(open_pull, self.tree_sha)
        after_merge = policy.wrapper_premerge_metadata_sha256(self.pull, self.tree_sha)
        self.assertEqual(before_merge, after_merge)
        arguments = self.arguments()
        for comment, role in zip(arguments["comments"], policy.OPERATIONAL_ACCEPTANCE_ROLES):
            comment["body"] = policy.operational_receipt( role, self.wrapper_sha, self.tree_sha, before_merge)
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
        arguments["pull_request"]["title"] += " changed"
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_receipt_inventory"):
            policy.publication_intent(**arguments)
    def test_digest_only_outputs_do_not_expose_wrapper_or_unrelated_comment_text(self):
        title_sentinel = "synthetic-title-token-4f6e3a9c@example.invalid"
        body_sentinel = "synthetic-body-token-07d4c1a2"
        comment_sentinel = "synthetic-unrelated-comment-8ac09f"
        arguments = self.arguments()
        arguments["pull_request"].update(title=f"Release v0.9.5.87 {title_sentinel}", body=f"Release-only: yes\n{body_sentinel}\n")
        metadata = policy.wrapper_premerge_metadata_sha256(arguments["pull_request"], self.tree_sha)
        for comment, role in zip(arguments["comments"], policy.OPERATIONAL_ACCEPTANCE_ROLES):
            comment["body"] = policy.operational_receipt(role, self.wrapper_sha, self.tree_sha, metadata)
        arguments["comments"].append({"id": 699, "body": comment_sentinel})
        plan = policy.publication_intent(**arguments)
        serialized = json.dumps(plan.__dict__, sort_keys=True)
        receipt_text = "\n".join(comment["body"] for comment in arguments["comments"][:2])
        for sentinel in (title_sentinel, body_sentinel, comment_sentinel):
            self.assertNotIn(sentinel, serialized)
            self.assertNotIn(sentinel, receipt_text)
        arguments["pull_request"]["body"] += "x"
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_receipt_inventory") as error:
            policy.publication_intent(**arguments)
        self.assertNotIn(body_sentinel, str(error.exception))
    def test_admission_hash_detects_valid_provider_evidence_replacement(self):
        original = policy.publication_intent(**self.arguments()).admission_sha256
        arguments = self.arguments()
        arguments["reviews"][0].update(id=504)
        arguments["reviews"][0]["user"].update(login="replacement-reviewer", id=201)
        arguments["reviewer_permissions"] = {201: copy.deepcopy(arguments["reviewer_permissions"][200])}
        arguments["reviewer_permissions"][201]["user"].update(login="replacement-reviewer", id=201)
        replaced_review = policy.publication_intent(**arguments).admission_sha256
        self.assertNotEqual(replaced_review, original)
        arguments = self.arguments()
        arguments["comments"][0].update(id=699, created_at="2026-08-31T21:58:00Z", updated_at="2026-08-31T21:58:00Z")
        replaced_receipt = policy.publication_intent(**arguments).admission_sha256
        self.assertNotEqual(replaced_receipt, original)
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
                     "web/games/roulette.js", "scripts/release_cadence.py", ".github/workflows/ci.yml", "docs/releases/whats_new.json", "web/i18n/en-US/shell.json",
                     "contracts/compatibility/app-0.9.5.86.json", "tests/unrelated.py"):
            arguments = self.arguments()
            arguments["changes"] = {**self.changes, path: policy.Change(b"old\n", b"new\n")}
            with self.subTest(path=path), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_release_documents_and_compatibility_notes_are_identity_only(self):
        notes = self.changes[policy.RELEASE_NOTES_PATH]
        rendered = policy.render_release_notes("0.9.5.87", "0.9.5.86", self.source_facts, self.accepted_deltas).encode()
        self.assertEqual(notes.after, rendered + notes.before)
        projected = policy._anchored_release_document( "README.md", b"Packaged application release: `0.9.5.86`\n" b"Historical comparison keeps 0.9.5.86 literally.\n",
            "0.9.5.86", "0.9.5.87", {"0.9.5.86": "0.9.5.87"}, "0.9.5.86", self.source_facts, self.accepted_deltas)
        self.assertIn(b"Historical comparison keeps 0.9.5.86 literally.\n", projected)
        for path, before in (("README.md", b"missing\n"), ("README.md", self.changes["README.md"].before * 2),
                             (policy.RELEASE_NOTES_PATH, notes.before + notes.before)):
            with self.subTest(anchor=path), self.assertRaisesRegex(policy.PolicyError, "wrapper_release_document_anchor"):
                policy._anchored_release_document(path, before, "0.9.5.86", "0.9.5.87", {"0.9.5.86": "0.9.5.87"},
                                                  "0.9.5.86", self.source_facts, self.accepted_deltas)
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
        arguments["changes"] = {**self.changes, "contracts/compatibility/app-0.9.5.87.json": policy.Change(None, encoded(candidate), None)}
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_compatibility_notes"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        release_notes = self.changes[policy.RELEASE_NOTES_PATH]
        arguments["changes"] = {**self.changes, policy.RELEASE_NOTES_PATH: policy.Change( release_notes.before, release_notes.after[:-2] + b"changed\n")}
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_release_document_behavior"):
            policy.publication_intent(**arguments)
    def test_pwa_package_descriptor_and_generated_behavior_fail(self):
        mutations = { "web/core/pwa_version.js": b"export const PWA_APP_VERSION = '0.9.5.87';\nactivateProvider();\n",
            "pyproject.toml": b'[project]\nversion = "0.9.5.87"\ndependencies = ["unreviewed"]\n',
            "modules/application.json": encoded({"module": "application", "version": "9.74.2", "paths": ["everything/"]}),
            policy.GENERATED_REQUIREMENTS: self.generated(self.after).replace(b"governed", b"waived"), }
        for path, after in mutations.items():
            arguments = self.arguments()
            arguments["changes"] = {**self.changes, path: policy.Change(self.changes[path].before, after)}
            with self.subTest(path=path), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_extra_missing_and_nonpatch_module_bumps_fail(self):
        for name, value in (("tooling", "1.50.1"), ("tests", "1.123.3"), ("application", "9.74.1"), ("docs", "1.117.0")):
            arguments = self.arguments()
            after = copy.deepcopy(self.after)
            after["modules"][name] = value
            arguments["after_manifest"] = after
            with self.subTest(name=name, value=value), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        malformed = [(f"missing-{field}", {key: copy.deepcopy(value) for key, value in self.source_facts.items() if key != field}) for field in policy.SOURCE_FACT_FIELDS]
        malformed.extend((label, {**self.source_facts, field: value}) for label, field, value in ( ("extra", "extra", 1), ("schema", "schema", "wrong"),
            ("source", "source_sha", "f" * 40), ("tree", "tree_sha", "e" * 40), ("requirements-bool", "permanent_requirement_count", True),
            ("requirements-zero", "permanent_requirement_count", 0), ("requirements-negative", "permanent_requirement_count", -1),
            ("inventory-text", "deployable_file_count", "870"), ("inventory-zero", "deployable_file_count", 0), ))
        malformed.append(("modules", {**self.source_facts, "modules": {"docs": "1.117.0"}}))
        for label, facts in malformed:
            arguments = {**self.arguments(), "source_facts": facts}
            with self.subTest(case=label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        for field, value in (("permanent_requirement_count", 1129), ("deployable_file_count", 869)):
            false_facts = {**self.source_facts, field: value}
            lying = self.candidate_for(false_facts, self.accepted_deltas)
            arguments = {**self.arguments(), "candidate": lying, "changes": self.projected_changes(
                self.changes, lying, false_facts, self.accepted_deltas)}
            with self.subTest(false_fact=field), self.assertRaisesRegex(policy.PolicyError, "wrapper_source_facts"):
                policy.publication_intent(**arguments)
        for checksum in ("0" * 64, "F" * 64, "short"):
            candidate = {**self.candidate, "release_facts_sha256": checksum}
            arguments = {**self.arguments(), "candidate": candidate, "changes": { **self.changes, "contracts/compatibility/app-0.9.5.87.json":
                    policy.Change(None, encoded(candidate), None)}}
            with self.subTest(checksum=checksum), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        for label, deltas in ( ("omitted", self.accepted_deltas[:-1]), ("reordered", list(reversed(self.accepted_deltas))),
                ("unaccepted", [*self.accepted_deltas[:-1], {"pull_request": 9999, "merge_sha": "9" * 40}]), ("duplicate", [*self.accepted_deltas, self.accepted_deltas[0]])):
            arguments = {**self.arguments(), "accepted_deltas": deltas}
            with self.subTest(delta_case=label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_added_deleted_linked_and_executable_wrapper_files_fail(self):
        for change in (policy.Change(None, b"new", None), policy.Change(b"old", None, after_mode=None), policy.Change(b"old", b"new", after_mode="120000"),
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
        facts = copy.deepcopy(self.source_facts)
        facts["modules"] = copy.deepcopy(self.after["modules"])
        candidate = self.candidate_for(facts, self.accepted_deltas, self.after["modules"])
        arguments["source_facts"] = facts
        arguments["candidate"] = candidate
        changes[policy.MANIFEST] = policy.Change(encoded(self.before), encoded(self.after))
        changes[policy.GENERATED_REQUIREMENTS] = policy.Change(self.generated(self.before), self.generated(self.after))
        changes["modules/tests.json"] = policy.Change(encoded({"module": "tests", "version": "1.123.2"}), encoded({"module": "tests", "version": "1.123.3"}))
        changes = self.projected_changes(changes, candidate, facts, self.accepted_deltas, self.before, self.after)
        arguments["changes"] = changes
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
        for hostile in (new.replace(b"assertEqual", b"assertNotEqual"), new + b"# ARBITRARY RELEASE CLAIM\n", new + b"value = 1  # type: ignore[assignment]\n",
                        new.replace(b"    self.assertEqual", b"        self.assertEqual")):
            changes["tests/release_artifact_tests.py"] = policy.Change(old, hostile)
            with self.subTest(hostile=hostile), self.assertRaisesRegex(policy.PolicyError, "wrapper_test_behavior"):
                policy.publication_intent(**arguments)
    def test_review_identity_and_release_declaration_are_mandatory(self):
        for change in ({"merge_commit_sha": "9" * 40}, {"merged_at": None}, {"base": {"ref": "feature"}}, {"base": {"ref": "main", "sha": "9" * 40}},
                       {"head": {"ref": "codex/product-change"}}, {"title": "Release v0.9.5.88"}, {"body": "Release-only: yes\nRelease-only: yes\n"}, {"body": "Release-only: no"}):
            arguments = self.arguments()
            arguments["pull_request"] = {**self.pull, **change}
            with self.subTest(change=change), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_distinct_current_head_provider_approval_is_mandatory(self):
        mutations = [("missing", [])]
        author = copy.deepcopy(self.arguments()["reviews"])
        author[0]["user"]["login"] = policy.REPOSITORY_OWNER
        mutations.append(("author", author))
        stale = copy.deepcopy(self.arguments()["reviews"])
        stale[0]["commit_id"] = "5" * 40
        mutations.append(("stale", stale))
        requested = copy.deepcopy(self.arguments()["reviews"])
        requested.append({**copy.deepcopy(requested[0]), "id": 503, "state": "CHANGES_REQUESTED", "submitted_at": "2026-08-31T21:56:00Z"})
        mutations.append(("requested", requested))
        dismissed = copy.deepcopy(self.arguments()["reviews"])
        dismissed.append({**copy.deepcopy(dismissed[0]), "id": 504, "state": "DISMISSED", "submitted_at": "2026-08-31T21:56:00Z"})
        mutations.append(("dismissed", dismissed))
        bot = copy.deepcopy(self.arguments()["reviews"])
        bot[0]["user"].update(login="github-actions[bot]", type="Bot")
        mutations.append(("bot", bot))
        for label, reviews in mutations:
            arguments = self.arguments()
            arguments["reviews"] = reviews
            with self.subTest(case=label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        for permission in ("read", "triage", "none", None):
            arguments = self.arguments()
            arguments["reviewer_permissions"][200]["permission"] = permission
            with self.subTest(permission=permission), self.assertRaisesRegex( policy.PolicyError, "wrapper_reviewer_permission"):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["reviewer_permissions"][200]["user"]["login"] = "wrong-reviewer"
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_reviewer_permission_identity"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["reviewer_permissions"][200]["user"]["id"] = 201
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_reviewer_permission_identity"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["reviews"][0]["user"].pop("type")
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_approval_invalid"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["reviewer_permissions"][200]["user"].pop("type")
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_reviewer_permission_identity"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["pull_request"]["user"] = {"login": "release-author", "id": 101, "type": "User"}
        arguments["merge_pull"]["user"] = copy.deepcopy(arguments["pull_request"]["user"])
        arguments["head_pulls"][0]["user"] = copy.deepcopy(arguments["pull_request"]["user"])
        arguments["reviews"][0]["user"] = { "login": policy.REPOSITORY_OWNER, "id": 100, "type": "User", }
        arguments["reviewer_permissions"] = { 100: {"permission": "write", "user": copy.deepcopy(arguments["reviews"][0]["user"])} }
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_approval_missing"):
            policy.publication_intent(**arguments)
    def test_latest_review_per_human_and_multiple_approvers_are_supported(self):
        arguments = self.arguments()
        old_request = copy.deepcopy(arguments["reviews"][0])
        old_request.update(id=500, state="CHANGES_REQUESTED", submitted_at="2026-08-31T21:54:00Z")
        arguments["reviews"].insert(0, old_request)
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
        arguments = self.arguments()
        second = copy.deepcopy(arguments["reviews"][0])
        second.update(id=502)
        second["user"].update(login="second-reviewer", id=201)
        arguments["reviews"].append(second)
        arguments["reviewer_permissions"][201] = { "permission": "admin", "user": {"login": "second-reviewer", "id": 201, "type": "User"}, }
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
    def test_extra_nonqualifying_approvals_do_not_displace_a_valid_human(self):
        extras = ( ("bot", {"login": "review-bot[bot]", "id": 201, "type": "Bot"}, "CONTRIBUTOR"), ("author", copy.deepcopy(self.pull["user"]), "OWNER"),
            ("owner", {"login": policy.REPOSITORY_OWNER, "id": 100, "type": "User"}, "OWNER"),
            ("non-collaborator", {"login": "outside-reviewer", "id": 202, "type": "User"}, "CONTRIBUTOR"), )
        for label, user, association in extras:
            arguments = self.arguments()
            extra = copy.deepcopy(arguments["reviews"][0])
            extra.update(id=550, user=user, author_association=association, submitted_at="2026-08-31T21:56:00Z")
            arguments["reviews"].append(extra)
            with self.subTest(case=label):
                self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
        for label, user, association in extras[:3]:
            arguments = self.arguments()
            arguments["reviews"][0].update(user=user, author_association=association)
            arguments["reviewer_permissions"] = {}
            with self.subTest(case=f"sole-{label}"), \
                 self.assertRaisesRegex(policy.PolicyError, "wrapper_approval_missing"):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        conflict = copy.deepcopy(arguments["reviews"][0])
        conflict.update(id=551, state="CHANGES_REQUESTED", user={"login": "review-bot[bot]", "id": 201, "type": "Bot"}, author_association="CONTRIBUTOR",
                        submitted_at="2026-08-31T21:56:00Z")
        arguments["reviews"].append(conflict)
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_review_conflict"):
            policy.publication_intent(**arguments)
    def test_operational_receipts_are_strict_supplemental_evidence(self):
        mutations = []
        missing = copy.deepcopy(self.arguments()["comments"])
        missing.pop()
        mutations.append(("missing", missing))
        edited = copy.deepcopy(self.arguments()["comments"])
        edited[0]["updated_at"] = "2026-08-31T21:57:00Z"
        mutations.append(("edited", edited))
        wrong_head = copy.deepcopy(self.arguments()["comments"])
        wrong_head[0]["body"] = wrong_head[0]["body"].replace(self.wrapper_sha, "5" * 40)
        mutations.append(("wrong-head", wrong_head))
        duplicate = copy.deepcopy(self.arguments()["comments"])
        duplicate[1]["body"] = duplicate[0]["body"]
        mutations.append(("duplicate-role", duplicate))
        for label, mutate in ( ("trailing", lambda body: body + "\nextra"), ("crlf", lambda body: body.replace("\n", "\r\n")), ("leading", lambda body: " " + body),
                ("verdict", lambda body: body.replace("Verdict: ACCEPT", "Verdict: HOLD")), ("digest", lambda body: body[:-1] + ("0" if body[-1] != "0" else "1"))):
            comments = copy.deepcopy(self.arguments()["comments"])
            comments[0]["body"] = mutate(comments[0]["body"])
            mutations.append((label, comments))
        duplicate_id = copy.deepcopy(self.arguments()["comments"])
        duplicate_id[1]["id"] = duplicate_id[0]["id"]
        mutations.append(("duplicate-id", duplicate_id))
        third = copy.deepcopy(self.arguments()["comments"])
        third.append({**copy.deepcopy(third[0]), "id": 699})
        mutations.append(("third-receipt", third))
        late = copy.deepcopy(self.arguments()["comments"])
        late[0].update(created_at="2026-08-31T22:00:01Z", updated_at="2026-08-31T22:00:01Z")
        mutations.append(("late", late))
        naive = copy.deepcopy(self.arguments()["comments"])
        naive[0].update(created_at="2026-08-31T21:56:00", updated_at="2026-08-31T21:56:00")
        mutations.append(("naive-time", naive))
        missing_time = copy.deepcopy(self.arguments()["comments"])
        missing_time[0].pop("created_at")
        mutations.append(("missing-time", missing_time))
        for label, body in (("none-body", None), ("int-body", 7), ("list-body", ["receipt"]), ("dict-body", {"receipt": True})):
            comments = copy.deepcopy(self.arguments()["comments"])
            comments[0]["body"] = body
            mutations.append((label, comments))
        for label, comments in mutations:
            arguments = self.arguments()
            arguments["comments"] = comments
            with self.subTest(case=label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["comments"][0].update(created_at=self.pull["merged_at"], updated_at=self.pull["merged_at"])
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_receipt_after_merge"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["comments"].append({"id": 700, "body": 99})
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
    def test_workflow_inventory_binds_exact_head_tree_suite_app_and_pull(self):
        # Empty run-level PR arrays are legitimate only because commit-to-PR association is mandatory.
        self.assertEqual(policy.publication_intent(**self.arguments()).decision, "publish")
        for field, value in (("run_attempt", 2), ("conclusion", "failure"), ("head_sha", "5" * 40)):
            arguments = self.arguments()
            arguments["workflow_runs"]["workflow_runs"][0][field] = value
            with self.subTest(field=field), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["workflow_runs"]["workflow_runs"][0]["head_commit"]["tree_id"] = "5" * 40
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_workflow_tree"):
            policy.publication_intent(**arguments)
        for mutation in ("missing", "ambiguous"):
            arguments = self.arguments()
            arguments["head_pulls"] = ([] if mutation == "missing" else [copy.deepcopy(self.pull), copy.deepcopy(self.pull)])
            with self.subTest(mutation=mutation), self.assertRaisesRegex( policy.PolicyError, "wrapper_head_pull_association"):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        arguments["workflow_runs"]["workflow_runs"][0]["pull_requests"] = [{ "number": 999, "head": {"sha": self.wrapper_sha}, "base": {"ref": "main"}, }]
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_workflow_pull"):
            policy.publication_intent(**arguments)
        for field, value in (("head_sha", "5" * 40), ("head_branch", "wrong-branch")):
            arguments = self.arguments()
            suite_id = arguments["workflow_runs"]["workflow_runs"][0]["check_suite_id"]
            arguments["check_suites"][suite_id][field] = value
            with self.subTest(suite_field=field), self.assertRaisesRegex( policy.PolicyError, "wrapper_suite_identity"):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        suite_id = arguments["workflow_runs"]["workflow_runs"][0]["check_suite_id"]
        arguments["check_suites"][suite_id]["app"]["id"] = 1
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_suite_app"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        runs = arguments["workflow_runs"]["workflow_runs"]
        first_run = runs[0]
        duplicate_suite = first_run["check_suite_id"]
        for run in runs[1:]:
            arguments["check_suites"].pop(run["check_suite_id"])
            run["check_suite_id"] = duplicate_suite
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_suite_ambiguous"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        check_id = next(iter(arguments["check_runs"]))
        arguments["check_runs"][check_id]["app"]["slug"] = "untrusted-app"
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_check_app"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        runs = arguments["workflow_runs"]["workflow_runs"]
        duplicate_job = arguments["workflow_jobs"][runs[0]["id"]]["jobs"][0]["id"]
        for run in runs[1:]:
            job = arguments["workflow_jobs"][run["id"]]["jobs"][0]
            arguments["check_runs"].pop(job["id"])
            job["id"] = duplicate_job
            job["check_run_url"] = ( f"https://api.github.com/repos/{policy.REPOSITORY}/check-runs/{duplicate_job}")
        last_job = arguments["workflow_jobs"][runs[-1]["id"]]["jobs"][0]
        arguments["check_runs"][duplicate_job]["name"] = last_job["name"]
        arguments["check_runs"][duplicate_job]["check_suite"]["id"] = runs[-1]["check_suite_id"]
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_gate_ambiguous"):
            policy.publication_intent(**arguments)
        arguments = self.arguments()
        run_id = arguments["workflow_runs"]["workflow_runs"][0]["id"]
        arguments["workflow_jobs"][run_id]["jobs"][0]["conclusion"] = "skipped"
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_gate_not_successful"):
            policy.publication_intent(**arguments)
    def test_commit_associations_bind_canonical_repository_author_and_merge_identity(self):
        expected = { "number": self.pull["number"], "merge_commit_sha": self.pull["merge_commit_sha"], "merged_at": self.pull["merged_at"],
            "base": {"ref": "main", "sha": self.pull["base"]["sha"], "repo": policy.REPOSITORY}, "head": {"ref": self.pull["head"]["ref"], "sha": self.pull["head"]["sha"],
                     "repo": policy.REPOSITORY}, "author": {"login": policy.REPOSITORY_OWNER, "id": 100, "type": "User"}, }
        self.assertEqual(policy.pull_association_record(self.pull), expected)
        mutations = ( ("merge-time", lambda row: row.update(merged_at="2026-08-31T21:59:59Z")), ("base-repository", lambda row: row["base"]["repo"].update(full_name="other/repo")),
            ("head-repository", lambda row: row["head"]["repo"].update(full_name="other/repo")), ("author-login", lambda row: row["user"].update(login="other-author")),
            ("author-id", lambda row: row["user"].update(id=101)), ("author-type", lambda row: row["user"].update(type="Bot")), )
        for association_name in ("merge_pull", "head_pulls"):
            for label, mutate in mutations:
                arguments = self.arguments()
                association = (arguments[association_name] if association_name == "merge_pull" else arguments[association_name][0])
                mutate(association)
                with self.subTest(association=association_name, case=label), \
                     self.assertRaisesRegex(policy.PolicyError, "wrapper_pull_canonical_drift"):
                    policy.publication_intent(**arguments)
    def test_workflow_path_forms_are_canonical(self):
        baseline = policy.publication_intent(**self.arguments()).admission_sha256
        for suffix in ("@main", "@refs/heads/main", "@refs/pull/1096/merge"):
            arguments = self.arguments()
            arguments["workflow_runs"]["workflow_runs"][0]["path"] += suffix
            with self.subTest(case=suffix):
                self.assertEqual(policy.publication_intent(**arguments).admission_sha256, baseline)
        base_path = next(iter(policy.REQUIRED_WORKFLOW_GATES))
        for label, value in (("feature", base_path + "@feature"), ("multiple-at", base_path + "@main@other"), ("foreign-pr", base_path + "@refs/pull/1095/merge"),
                             ("zero-pr", base_path + "@refs/pull/0/merge"), ("empty", "")):
            arguments = self.arguments()
            arguments["workflow_runs"]["workflow_runs"][0]["path"] = value
            with self.subTest(case=label), self.assertRaisesRegex( policy.PolicyError, "wrapper_workflow_path"):
                policy.publication_intent(**arguments)
    def test_parent_and_gate_attempt_binding_is_fail_closed(self):
        for label, value in (("missing", None), ("bool", True), ("zero", 0), ("two", 2), ("string", "1")):
            arguments = self.arguments()
            if label == "missing":
                arguments["workflow_runs"]["workflow_runs"][0].pop("run_attempt")
            else:
                arguments["workflow_runs"]["workflow_runs"][0]["run_attempt"] = value
            with self.subTest(case="run-" + label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
        arguments = self.arguments()
        run_id = arguments["workflow_runs"]["workflow_runs"][0]["id"]
        arguments["workflow_jobs"][run_id]["jobs"][0].pop("run_attempt")
        self.assertEqual(policy.publication_intent(**arguments).decision, "publish")
        for label, value in (("null", None), ("bool", True), ("zero", 0), ("two", 2), ("string", "1")):
            arguments = self.arguments()
            run_id = arguments["workflow_runs"]["workflow_runs"][0]["id"]
            arguments["workflow_jobs"][run_id]["jobs"][0]["run_attempt"] = value
            with self.subTest(case="job-" + label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_provider_inventory_caps_and_partial_pages_fail_closed(self):
        cases = []
        reviews = copy.deepcopy(self.arguments())
        reviews["reviews"] = [{**copy.deepcopy(reviews["reviews"][0]), "id": 1000 + index} for index in range(100)]
        cases.append(("reviews-100", reviews))
        comments = copy.deepcopy(self.arguments())
        comments["comments"].extend({"id": 1000 + index, "body": "unrelated"} for index in range(98))
        cases.append(("comments-100", comments))
        runs = copy.deepcopy(self.arguments())
        runs["workflow_runs"]["total_count"] += 1
        cases.append(("runs-partial", runs))
        jobs = copy.deepcopy(self.arguments())
        run_id = jobs["workflow_runs"]["workflow_runs"][0]["id"]
        jobs["workflow_jobs"][run_id]["total_count"] += 1
        cases.append(("jobs-partial", jobs))
        for label, arguments in cases:
            with self.subTest(case=label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_all_admission_evidence_must_be_terminal_before_merge(self):
        cases = []
        approval = self.arguments()
        approval["reviews"][0]["submitted_at"] = "2026-08-31T22:00:01Z"
        cases.append(("approval", approval))
        receipt = self.arguments()
        receipt["comments"][0].update(created_at="2026-08-31T22:00:01Z", updated_at="2026-08-31T22:00:01Z")
        cases.append(("receipt", receipt))
        run = self.arguments()
        run["workflow_runs"]["workflow_runs"][0]["updated_at"] = "2026-08-31T22:00:01Z"
        cases.append(("run", run))
        suite = self.arguments()
        suite_id = suite["workflow_runs"]["workflow_runs"][0]["check_suite_id"]
        suite["check_suites"][suite_id]["updated_at"] = "2026-08-31T22:00:01Z"
        cases.append(("suite", suite))
        job = self.arguments()
        run_id = job["workflow_runs"]["workflow_runs"][0]["id"]
        job["workflow_jobs"][run_id]["jobs"][0]["completed_at"] = "2026-08-31T22:00:01Z"
        cases.append(("job", job))
        check = self.arguments()
        check_id = next(iter(check["check_runs"]))
        check["check_runs"][check_id]["completed_at"] = "2026-08-31T22:00:01Z"
        cases.append(("check", check))
        for label, arguments in cases:
            with self.subTest(case=label), self.assertRaises(policy.PolicyError):
                policy.publication_intent(**arguments)
    def test_additive_provider_owner_fields_do_not_change_admission_digest(self):
        baseline = policy.publication_intent(**self.arguments()).admission_sha256
        arguments = self.arguments()
        arguments["pull_request"]["base"]["repo"]["owner"].update( avatar_url="synthetic-private-avatar", extra={"untrusted": True})
        self.assertEqual(policy.publication_intent(**arguments).admission_sha256, baseline)
    def test_predecessor_corruption_source_archive_and_schema_fail(self):
        for mutate in (lambda row: row["source"].update(commit_sha="f" * 40), lambda row: row["source"].update(release_tag="v0.9.5.85"),
                       lambda row: row["artifact"].update(sha256="f" * 64), lambda row: row["mysql_schema"].update(minimum_version=3),
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
    def test_wrapper_cannot_skip_the_packaged_version_it_replaces(self):
        arguments = self.arguments()
        candidate = copy.deepcopy(self.candidate)
        candidate["predecessor"].update(app_version="0.9.5.84", compatibility_record="contracts/compatibility/app-0.9.5.84.json")
        arguments["candidate"] = candidate
        arguments["changes"] = {**self.changes, "contracts/compatibility/app-0.9.5.87.json": policy.Change(None, encoded(candidate), None)}
        with self.assertRaisesRegex(policy.PolicyError, "wrapper_predecessor_not_replaced_version"):
            policy.publication_intent(**arguments)
    def test_creation_and_complete_duplicate_reuse_are_distinct(self):
        self.assertEqual(policy.release_state("0.9.5.87", "2" * 40, None, None), "create")
        self.assertEqual(policy.release_state("0.9.5.87", "2" * 40, "2" * 40, self.release()), "reuse")
    def test_partial_draft_failed_upload_and_wrong_identity_never_reuse(self):
        for mutate in (lambda row: row.update(draft=True), lambda row: row.update(prerelease=True),
                       lambda row: row.update(target_commitish="main"), lambda row: row.update(published_at=None), lambda row: row.update(published_at=""),
                       lambda row: row.update(published_at="not-a-timestamp"), lambda row: row.update(published_at="2026-08-31T22:00:00"),
                       lambda row: row["assets"].pop(), lambda row: row["assets"][0].update(state="new"), lambda row: row["assets"][0].update(size=0)):
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
        errors = [URLError("synthetic-private-detail")]
        errors.extend(HTTPError("https://api.github.com", status, "private", {}, None) for status in (401, 403, 429, 500, 503))
        for error in errors:
            with mock.patch.dict("os.environ", {"GH_TOKEN": "synthetic-not-a-token"}), \
                 mock.patch.object(boundary, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaisesRegex(policy.PolicyError, "github_observation_failed"):
                    boundary.github_get(f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.87", allow_absent=True)
    def test_only_release_tag_404_can_mean_api_absence(self):
        error = HTTPError("https://api.github.com", 404, "missing", {}, None)
        with mock.patch.dict("os.environ", {"GH_TOKEN": "synthetic-not-a-token"}), \
             mock.patch.object(boundary, "build_opener") as opener:
            opener.return_value.open.side_effect = error
            self.assertIsNone(boundary.github_get( f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.87", allow_absent=True))
            with self.assertRaisesRegex(policy.PolicyError, "github_observation_failed"):
                boundary.github_get( f"repos/{boundary.REPOSITORY}/collaborators/release-reviewer/permission")
            with self.assertRaisesRegex(policy.PolicyError, "github_absence_scope"):
                boundary.github_get( f"repos/{boundary.REPOSITORY}/collaborators/release-reviewer/permission", allow_absent=True)
    def test_malformed_oversized_duplicate_json_and_redirects_fail_closed(self):
        for raw in (b"", b"not-json", b"[] trailing", b"{" + b"x" * boundary.MAX_RECORD_BYTES + b"}"):
            response = mock.MagicMock()
            response.__enter__.return_value.status = 200
            response.__enter__.return_value.read.return_value = raw
            with mock.patch.dict("os.environ", {"GH_TOKEN": "synthetic-not-a-token"}), \
                 mock.patch.object(boundary, "build_opener") as opener:
                opener.return_value.open.return_value = response
                with self.subTest(size=len(raw)), self.assertRaises(policy.PolicyError):
                    boundary.github_get(f"repos/{boundary.REPOSITORY}/pulls/1096")
        response = mock.MagicMock()
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.read.return_value = b'{"id":1,"id":2}'
        with mock.patch.dict("os.environ", {"GH_TOKEN": "synthetic-not-a-token"}), \
             mock.patch.object(boundary, "build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(policy.PolicyError, "duplicate_json_key"):
                boundary.github_get(f"repos/{boundary.REPOSITORY}/pulls/1096")
        request = boundary.Request("https://api.github.com/example", headers={"Authorization": "Bearer secret"})
        with self.assertRaisesRegex(policy.PolicyError, "github_redirect_refused"):
            boundary.SafeRedirect().redirect_request( request, None, 302, "redirect", {}, "https://example.invalid/asset")
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
    def test_hosted_fingerprint_ignores_download_count_but_detects_replacement(self):
        metadata = self.release()
        for index, asset in enumerate(metadata["assets"], start=1):
            asset.update(id=index, node_id=f"asset-{index}", label=None, content_type="application/octet-stream",
                         created_at="2026-08-31T22:00:00Z", updated_at="2026-08-31T22:00:00Z", digest=f"sha256:{index:064x}", download_count=0)
        raw = encoded(self.previous)
        baseline = boundary.hosted_release_fingerprint(metadata, "2" * 40, raw)
        downloaded = copy.deepcopy(metadata)
        downloaded["assets"][0]["download_count"] = 99
        self.assertEqual(boundary.hosted_release_fingerprint(downloaded, "2" * 40, raw), baseline)
        for field, value in (("id", 999), ("size", 999), ("updated_at", "2026-09-01T00:00:00Z"), ("digest", "sha256:" + "f" * 64)):
            replaced = copy.deepcopy(metadata)
            replaced["assets"][0][field] = value
            with self.subTest(field=field):
                self.assertNotEqual(boundary.hosted_release_fingerprint(replaced, "2" * 40, raw), baseline)
    def test_duplicate_json_keys_do_not_shadow_release_policy(self):
        with self.assertRaises(policy.PolicyError):
            policy.object_json('{"application":"0.9.5.86","application":"0.9.5.87"}')
    def batch_observation(self):
        return {"main_sha": "2" * 40, "released_sha": "d" * 40, "live_sha": "d" * 40, "app_version": "0.9.5.86", "predecessor_manifest_sha256": "e" * 64,
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
        for change in ({"publication": "active"}, {"publication": "failed"}, {"rollout": "active"}, {"rollout": "failed"}, {"open_wrapper": True}, {"live_sha": "a" * 40},
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
    def test_post_merge_publication_aggregate_exhaustive_truth_table(self):
        states = ("success", "failure", "cancelled", "skipped", "")
        decisions = ("noop", "publish", "unknown", "not-due", "")
        accepted = {("success", "noop", "skipped", "skipped"), ("success", "publish", "success", "success")}
        for intent, decision, writer, verifier in itertools.product(states, decisions, states, states):
            expected = (intent, decision, writer, verifier) in accepted
            with self.subTest(intent=intent, decision=decision, writer=writer, verifier=verifier):
                self.assertEqual(policy.publication_result(intent, decision, writer, verifier), expected)
                with mock.patch("sys.stdout", new=io.StringIO()), mock.patch("sys.stderr", new=io.StringIO()):
                    self.assertEqual(boundary.main(["result", "--intent-result", intent, "--decision", decision, "--writer-result", writer,
                                                    "--verifier-result", verifier]), 0 if expected else 1)
    def test_source_facts_are_exact_git_objects_not_checkout_state(self):
        with tempfile.TemporaryDirectory(prefix="casino-source-facts-") as temporary:
            root = Path(temporary)
            self.git(root, "init", "-b", "main")
            self.write_fixture(root, policy.MANIFEST, encoded(self.after))
            self.write_fixture(root, "docs/requirements/requirements.json", encoded( {"requirements": [{"id": "TOOL-008"}, {"id": "TEST-133"}]}))
            self.write_fixture(root, "README.md", b"candidate\n")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "accepted pre-wrapper source")
            source = self.git(root, "rev-parse", "HEAD")
            source_tree = self.git(root, "rev-parse", "HEAD^{tree}")
            with mock.patch.object(boundary.package_app, "REQUIRED_FILES", set()):
                facts = boundary.observe_source_facts(root, source, source, self.after)
                self.assertEqual((facts["source_sha"], facts["tree_sha"], facts["modules"], facts["permanent_requirement_count"], facts["deployable_file_count"]),
                                 (source, source_tree, self.after["modules"], 2, 2))
                (root / "README.md").unlink()
                (root / policy.MANIFEST).unlink()
                self.assertEqual(boundary.observe_source_facts(root, source, source, self.after), facts)
                self.git(root, "restore", ".")
                self.write_fixture(root, "docs/ignored.md", b"excluded\n")
                self.write_fixture(root, "tests/ignored.py", b"excluded\n")
                self.git(root, "add", ".")
                self.git(root, "commit", "-m", "excluded candidate files")
                excluded = self.git(root, "rev-parse", "HEAD")
                self.assertEqual(boundary.observe_source_facts( root, source, excluded, self.after)["deployable_file_count"], 2)
                self.write_fixture(root, "contracts/compatibility/app-0.9.5.87.json", b"{}\n")
                self.git(root, "add", ".")
                self.git(root, "commit", "-m", "single candidate compatibility record")
                allowed = self.git(root, "rev-parse", "HEAD")
                self.assertEqual(boundary.observe_source_facts( root, source, allowed, self.after)["deployable_file_count"], 3)
                for label, entry in ( ("credential", ("casino/.env", "100644", "blob", "a" * 40)), ("traversal", ("casino/../escape.py", "100644", "blob", "a" * 40)),
                        ("symlink", ("casino/link", "120000", "blob", "a" * 40)), ("gitlink", ("casino/submodule", "160000", "commit", "a" * 40))):
                    with self.subTest(case=label), self.assertRaisesRegex(policy.PolicyError, "source_facts_inventory"):
                        boundary.deployable_tree_paths([entry])
                duplicate = b"100644 blob " + b"a" * 40 + b"\tREADME.md\0"
                with mock.patch.object(boundary, "git_read", return_value=duplicate * 2), \
                     self.assertRaisesRegex(policy.PolicyError, "source_facts_tree"):
                    boundary.tree_entries(root, source)
    def test_accepted_deltas_require_contiguous_real_two_parent_history(self):
        with tempfile.TemporaryDirectory(prefix="casino-accepted-deltas-") as temporary:
            root = Path(temporary)
            self.git(root, "init", "-b", "main")
            self.git(root, "commit", "--allow-empty", "-m", "predecessor")
            predecessor = self.git(root, "rev-parse", "HEAD")
            merges = []
            for number in (1094, 1096):
                branch = f"feature-{number}"
                self.git(root, "switch", "-c", branch)
                self.git(root, "commit", "--allow-empty", "-m", f"feature {number}")
                self.git(root, "switch", "main")
                self.git(root, "merge", "--no-ff", branch, "-m",
                         f"Merge pull request #{number} from andreivorobiev/{branch}")
                merges.append(self.git(root, "rev-parse", "HEAD"))
            source = merges[-1]
            self.assertEqual(boundary.observe_accepted_deltas(root, predecessor, source), [
                {"pull_request": 1094, "merge_sha": merges[0]},
                {"pull_request": 1096, "merge_sha": merges[1]}])
            raw = boundary.git_read(root, "log", "--first-parent", "--reverse",
                                    "--format=%H%x09%P%x09%s%x00", f"{predecessor}..{source}")
            records = [record for record in raw.split(b"\0") if record]
            for label, hostile in (("malformed", b"malformed\0"),
                                   ("skipped", records[1] + b"\0"),
                                   ("reordered", b"\0".join(reversed(records)) + b"\0")):
                with self.subTest(history=label), self.assertRaises(policy.PolicyError):
                    boundary.accepted_deltas_from_log(hostile, predecessor, source)
            self.git(root, "commit", "--allow-empty", "-m",
                     "Merge pull request #2000 from andreivorobiev/spoof")
            single = self.git(root, "rev-parse", "HEAD")
            with self.assertRaisesRegex(policy.PolicyError, "accepted_delta_parent_count"):
                boundary.observe_accepted_deltas(root, source, single)
            side_heads = []
            for branch in ("octopus-a", "octopus-b"):
                self.git(root, "switch", "-c", branch, source)
                self.write_fixture(root, f"{branch}.txt", branch.encode())
                self.git(root, "add", ".")
                self.git(root, "commit", "-m", branch)
                side_heads.append(self.git(root, "rev-parse", "HEAD"))
            octopus = self.git(root, "commit-tree", self.git(root, "rev-parse", f"{source}^{{tree}}"),
                               "-p", source, "-p", side_heads[0], "-p", side_heads[1], "-m",
                               "Merge pull request #2001 from andreivorobiev/octopus")
            with self.assertRaisesRegex(policy.PolicyError, "accepted_delta_parent_count"):
                boundary.observe_accepted_deltas(root, source, octopus)
            self.git(root, "switch", "-c", "side-predecessor", source)
            self.git(root, "commit", "--allow-empty", "-m", "side predecessor")
            side_predecessor = self.git(root, "rev-parse", "HEAD")
            self.git(root, "switch", "-c", "side-main-feature", source)
            self.git(root, "commit", "--allow-empty", "-m", "side main feature")
            self.git(root, "switch", "-c", "side-main", source)
            self.git(root, "merge", "--no-ff", "side-main-feature", "-m",
                     "Merge pull request #2003 from andreivorobiev/side-main-feature")
            self.git(root, "merge", "--no-ff", "side-predecessor", "-m",
                     "Merge pull request #2002 from andreivorobiev/side-predecessor")
            side_source = self.git(root, "rev-parse", "HEAD")
            with self.assertRaisesRegex(policy.PolicyError, "accepted_delta_first_parent"):
                boundary.observe_accepted_deltas(root, side_predecessor, side_source)
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
            source_tree = self.git(root, "rev-parse", "HEAD^{tree}")
            facts = copy.deepcopy(self.source_facts)
            facts.update(source_sha=before, tree_sha=source_tree)
            candidate = self.candidate_for(facts, self.accepted_deltas)
            changes = self.projected_changes( self.changes, candidate, facts, self.accepted_deltas)
            self.git(root, "switch", "-c", "codex/release-v0.9.5.87")
            for path, change in changes.items():
                self.write_fixture(root, path, change.after)
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "synthetic release wrapper")
            wrapper = self.git(root, "rev-parse", "HEAD")
            wrapper_tree = self.git(root, "rev-parse", "HEAD^{tree}")
            self.git(root, "switch", "main")
            self.git(root, "merge", "--no-ff", "--no-edit", "codex/release-v0.9.5.87")
            head = self.git(root, "rev-parse", "HEAD")
            event = {"ref": "refs/heads/main", "before": before, "after": head, "forced": False}
            environment = {"GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": boundary.REPOSITORY,
                           "GITHUB_REF": "refs/heads/main", "GITHUB_REF_PROTECTED": "true", "GITHUB_SHA": head, "GITHUB_RUN_ATTEMPT": "1"}
            pull = copy.deepcopy(self.pull)
            pull.update(merge_commit_sha=head)
            pull["base"]["sha"] = before
            pull["head"].update(sha=wrapper)
            evidence = self.admission_evidence(wrapper, wrapper_tree, pull)
            responses = { f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100": [pull],
                f"repos/{boundary.REPOSITORY}/commits/{wrapper}/pulls?per_page=100": evidence["head_pulls"], f"repos/{boundary.REPOSITORY}/pulls/{pull['number']}": pull,
                f"repos/{boundary.REPOSITORY}/pulls/{pull['number']}/reviews?per_page=100": evidence["reviews"],
                f"repos/{boundary.REPOSITORY}/collaborators/release-reviewer/permission": evidence["reviewer_permissions"][200],
                f"repos/{boundary.REPOSITORY}/issues/{pull['number']}/comments?per_page=100": evidence["comments"],
                f"repos/{boundary.REPOSITORY}/actions/runs?head_sha={wrapper}&per_page=100": evidence["workflow_runs"],
                f"repos/{boundary.REPOSITORY}/git/ref/heads/main": {"object": {"type": "commit", "sha": head}},
                f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.86": self.release("0.9.5.86", "d" * 40), f"repos/{boundary.REPOSITORY}/releases/tags/v0.9.5.87": None, }
            for run_id, jobs in evidence["workflow_jobs"].items():
                responses[f"repos/{boundary.REPOSITORY}/actions/runs/{run_id}/attempts/1/jobs?per_page=100"] = jobs
            for check_id, check in evidence["check_runs"].items():
                responses[f"repos/{boundary.REPOSITORY}/check-runs/{check_id}"] = check
            for suite_id, suite in evidence["check_suites"].items():
                responses[f"repos/{boundary.REPOSITORY}/check-suites/{suite_id}"] = suite
            with mock.patch.object(boundary, "github_get", side_effect=lambda path, **_kwargs: copy.deepcopy(responses[path])) as getter, \
                 mock.patch.object(boundary, "tag_commit", side_effect=lambda _root, tag: "d" * 40 if tag.endswith(".86") else None), \
                 mock.patch.object(boundary, "manifest_bytes", return_value=encoded(self.previous)), \
                 mock.patch.object(boundary, "observe_source_facts", return_value=facts) as facts_observer, \
                 mock.patch.object(boundary, "observe_accepted_deltas", return_value=self.accepted_deltas) as delta_observer:
                plan = boundary.inspect_publication(event, environment, root, under_lock=True)
                self.assertEqual((plan["decision"], plan["release_state"], plan["source_sha"]), ("publish", "create", head))
                self.assertEqual(facts_observer.call_count, 2)
                self.assertEqual(delta_observer.call_count, 2)
                calls = [call.args[0] for call in getter.call_args_list]
                repeated = [ f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100", f"repos/{boundary.REPOSITORY}/pulls/{pull['number']}",
                    f"repos/{boundary.REPOSITORY}/pulls/{pull['number']}/reviews?per_page=100", f"repos/{boundary.REPOSITORY}/issues/{pull['number']}/comments?per_page=100",
                    f"repos/{boundary.REPOSITORY}/commits/{wrapper}/pulls?per_page=100", f"repos/{boundary.REPOSITORY}/actions/runs?head_sha={wrapper}&per_page=100",
                    f"repos/{boundary.REPOSITORY}/collaborators/release-reviewer/permission", ]
                repeated.extend( f"repos/{boundary.REPOSITORY}/actions/runs/{run_id}/attempts/1/jobs?per_page=100" for run_id in evidence["workflow_jobs"])
                repeated.extend(f"repos/{boundary.REPOSITORY}/check-runs/{check_id}" for check_id in evidence["check_runs"])
                repeated.extend(f"repos/{boundary.REPOSITORY}/check-suites/{suite_id}" for suite_id in evidence["check_suites"])
                self.assertTrue(all(calls.count(path) == 2 for path in repeated))
                self.assertEqual(calls[-1], f"repos/{boundary.REPOSITORY}/git/ref/heads/main")
                getter.side_effect = lambda path, **_kwargs: copy.deepcopy(responses[path])
                drifted_facts = {**facts, "deployable_file_count": facts["deployable_file_count"] + 1}
                facts_observer.side_effect = [facts, drifted_facts]
                with self.assertRaisesRegex(policy.PolicyError, "publication_source_facts_drift"):
                    boundary.inspect_publication(event, environment, root, under_lock=True)
                facts_observer.side_effect = None
                facts_observer.return_value = facts
                delta_observer.side_effect = [self.accepted_deltas, list(reversed(self.accepted_deltas))]
                with self.assertRaisesRegex(policy.PolicyError, "publication_source_facts_drift"):
                    boundary.inspect_publication(event, environment, root, under_lock=True)
                delta_observer.side_effect = None
                delta_observer.return_value = self.accepted_deltas
                baseline = copy.deepcopy(responses)
                def require_final_failure(label, path, mutate, reason):
                    counts = {}
                    def sequenced(observed_path, **_kwargs):
                        counts[observed_path] = counts.get(observed_path, 0) + 1
                        value = copy.deepcopy(baseline[observed_path])
                        if observed_path == path and counts[observed_path] == 2:
                            mutate(value)
                        return value
                    getter.side_effect = sequenced
                    with self.subTest(case=label), self.assertRaisesRegex(policy.PolicyError, reason):
                        boundary.inspect_publication(event, environment, root, under_lock=True)
                    self.assertEqual(counts.get(path), 2)
                    self.assertEqual( counts.get(f"repos/{boundary.REPOSITORY}/git/ref/heads/main", 0), 0)
                reviews_path = f"repos/{boundary.REPOSITORY}/pulls/{pull['number']}/reviews?per_page=100"
                require_final_failure( "replacement-approval", reviews_path, lambda value: value[0].update(id=504, submitted_at="2026-08-31T21:56:00Z"),
                    "publication_admission_drift")
                comments_path = f"repos/{boundary.REPOSITORY}/issues/{pull['number']}/comments?per_page=100"
                require_final_failure( "replacement-receipt", comments_path, lambda value: value[0].update(id=699, created_at="2026-08-31T21:58:00Z",
                                                  updated_at="2026-08-31T21:58:00Z"), "publication_admission_drift")
                runs_path = f"repos/{boundary.REPOSITORY}/actions/runs?head_sha={wrapper}&per_page=100"
                require_final_failure( "replacement-run", runs_path, lambda value: value["workflow_runs"][0].update(updated_at="2026-08-31T21:55:00Z"),
                    "publication_admission_drift")
                require_final_failure( "duplicate-suite-final-snapshot", runs_path, lambda value: [run.update( check_suite_id=value["workflow_runs"][0]["check_suite_id"])
                        for run in value["workflow_runs"]], "wrapper_suite_ambiguous")
                job_paths = { f"repos/{boundary.REPOSITORY}/actions/runs/{run_id}/attempts/1/jobs?per_page=100" for run_id in evidence["workflow_jobs"] }
                duplicate_job = next(iter(evidence["check_runs"]))
                duplicate_check_path = ( f"repos/{boundary.REPOSITORY}/check-runs/{duplicate_job}")
                counts = {}
                def duplicate_final_gate_jobs(observed_path, **_kwargs):
                    counts[observed_path] = counts.get(observed_path, 0) + 1
                    value = copy.deepcopy(baseline[observed_path])
                    if observed_path in job_paths and counts[observed_path] == 2:
                        value["jobs"][0]["id"] = duplicate_job
                        value["jobs"][0]["check_run_url"] = duplicate_check_path.replace( "repos/", "https://api.github.com/repos/", 1)
                    return value
                getter.side_effect = duplicate_final_gate_jobs
                with self.subTest(case="duplicate-gate-final-snapshot"), \
                     self.assertRaisesRegex(policy.PolicyError, "wrapper_gate_ambiguous"):
                    boundary.inspect_publication(event, environment, root, under_lock=True)
                self.assertTrue(all(counts.get(path) == 2 for path in job_paths))
                self.assertEqual( counts.get(f"repos/{boundary.REPOSITORY}/git/ref/heads/main", 0), 0)
                permission_path = f"repos/{boundary.REPOSITORY}/collaborators/release-reviewer/permission"
                require_final_failure( "permission-removed", permission_path, lambda value: value.update(permission="read"), "wrapper_reviewer_permission")
                require_final_failure( "permission-id-drift", permission_path, lambda value: value["user"].update(id=201), "wrapper_reviewer_permission_identity")
                require_final_failure( "permission-type-drift", permission_path, lambda value: value["user"].update(type="Bot"), "wrapper_reviewer_permission_identity")
                def fail_terminal_observation(_value):
                    raise policy.PolicyError("github_observation_failed")
                require_final_failure( "permission-observation-error", permission_path, fail_terminal_observation, "github_observation_failed")
                require_final_failure( "approval-dismissed", reviews_path, lambda value: value[0].update(state="DISMISSED"), "wrapper_approval_missing")
                require_final_failure( "approval-changes-requested", reviews_path, lambda value: value[0].update(state="CHANGES_REQUESTED"), "wrapper_review_conflict")
                require_final_failure( "approval-moved-commit", reviews_path, lambda value: value[0].update(commit_id="f" * 40), "wrapper_approval_missing")
                pull_path = f"repos/{boundary.REPOSITORY}/pulls/{pull['number']}"
                require_final_failure( "canonical-title-drift", pull_path, lambda value: value.update(title=value["title"] + " changed"), "wrapper_receipt_inventory")
                require_final_failure( "canonical-body-drift", pull_path, lambda value: value.update(body=value["body"] + "changed\n"), "wrapper_receipt_inventory")
                require_final_failure( "canonical-head-drift", pull_path, lambda value: value["head"].update(sha="f" * 40), "wrapper_pull_canonical_drift")
                require_final_failure( "canonical-base-drift", pull_path, lambda value: value["base"].update(sha="f" * 40), "wrapper_pull_canonical_drift")
                getter.side_effect = lambda path, **_kwargs: copy.deepcopy(responses[path])
                responses[f"repos/{boundary.REPOSITORY}/git/ref/heads/main"]["object"]["sha"] = "f" * 40
                with self.assertRaisesRegex(policy.PolicyError, "protected_main_moved"):
                    boundary.inspect_publication(event, environment, root, under_lock=True)
                responses[f"repos/{boundary.REPOSITORY}/git/ref/heads/main"]["object"]["sha"] = head
                responses[f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100"] = [pull, pull]
                with self.assertRaisesRegex(policy.PolicyError, "wrapper_pull_ambiguous"):
                    boundary.inspect_publication(event, environment, root)
                with self.assertRaisesRegex(policy.PolicyError, "push_publication_rerun_prohibited"):
                    boundary.inspect_publication(event, {**environment, "GITHUB_RUN_ATTEMPT": "2"}, root)
                responses[f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100"] = []
                with self.assertRaisesRegex(policy.PolicyError, "wrapper_pull_ambiguous"):
                    boundary.inspect_publication(event, environment, root)
                responses[f"repos/{boundary.REPOSITORY}/commits/{head}/pulls?per_page=100"] = [pull]
                responses[f"repos/{boundary.REPOSITORY}/commits/{wrapper}/pulls?per_page=100"] = [pull, pull]
                with self.assertRaisesRegex(policy.PolicyError, "wrapper_head_pull_association"):
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
                                 "-c", "commit.gpgsign=false", *arguments], cwd=root, check=True, capture_output=True, timeout=20)
        return result.stdout.decode().strip()
if __name__ == "__main__":
    unittest.main()
