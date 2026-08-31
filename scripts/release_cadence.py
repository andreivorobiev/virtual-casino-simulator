# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure release-intent and three-hour batch policy for TOOL-008 and TEST-133.

Inputs are observations, not authority: the coordinator must refresh GitHub and
live evidence before acting. This module opens no connection and owns no clock,
scheduler, repository writer, publication, or deployment operation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re


VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
MODULE_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
ASSETS = frozenset({"checksums.txt", "release-manifest.json", "virtual_casino_simulator_package.zip"})
MANIFEST = "modules/module-manifest.json"
REPOSITORY = "andreivorobiev/virtual-casino-simulator"
REPOSITORY_OWNER = "andreivorobiev"
GITHUB_ACTIONS_APP_ID = 15368
REQUIRED_WORKFLOW_GATES = {
    ".github/workflows/ci.yml": "ci",
    ".github/workflows/contract-tests.yml": "contract_tests",
    ".github/workflows/module-boundaries.yml": "module_boundaries",
    ".github/workflows/comment-density.yml": "comment_density",
    ".github/workflows/docs.yml": "docs",
    # This is a stable status context only; it never supplies review approval.
    ".github/workflows/codex-review.yml": "codex_review_placeholder",
    ".github/workflows/long-suite-100.yml": "long_suite_100",
    ".github/workflows/browser-tests.yml": "browser_tests",
    ".github/workflows/release.yml": "Build unpublished candidate",
}
OPERATIONAL_ACCEPTANCE_ROLES = ("Senior B", "Worker10")
OPERATIONAL_RECEIPT_HEADER = "Release admission receipt v1"
RELEASE_DOCS = frozenset({
    "README.md", "CODEX_START_HERE.md", "VERSIONING.md", "RELEASE_NOTES.md",
    "docs/production_cicd_runbook.md", "docs/release_artifacts.md",
    "docs/release_versioning.md", "docs/production_service.md",
})
GENERATED_REQUIREMENTS = "docs/requirements/requirements_generated.md"
REQUIREMENT_REGISTRIES = frozenset({
    "docs/requirements/requirements-spine.json", "docs/requirements/requirements.json",
})
RELEASE_TESTS = frozenset({"tests/release_artifact_tests.py", "tests/release_predecessor_tests.py"})
WRAPPER_MODULES = frozenset({"application", "docs", "contracts", "tests"})
ROLLBACK = {
    "scope": "application-only", "database_rollback": "prohibited",
    "mysql_expected_schema_version": 2, "requires_retained_predecessor_manifest": True,
}


class PolicyError(ValueError):
    """A fixed, secret-free reason to stop before publication authority."""


def require(condition, reason):
    """Keep failures bounded; never echo observed PR, API, or file contents."""
    if not condition:
        raise PolicyError(reason)


def json_value(raw):
    """Decode bounded JSON while rejecting duplicate shadow fields at every depth."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except PolicyError:
        raise
    except (ValueError, TypeError, UnicodeError) as error:
        raise PolicyError("invalid_json") from error
    return value


def object_json(raw):
    """Decode one canonical object rather than a scalar or list."""
    value = json_value(raw)
    require(isinstance(value, dict), "json_object_required")
    return value


def version(value, pattern=VERSION):
    require(isinstance(value, str) and pattern.fullmatch(value), "invalid_version")
    return tuple(int(part) for part in value.split("."))


def next_patch(value):
    parts = version(value)
    return ".".join(map(str, (*parts[:-1], parts[-1] + 1)))


def identity(value, pattern=COMMIT):
    require(isinstance(value, str) and pattern.fullmatch(value), "invalid_identity")
    return value


def timestamp(value, reason):
    """Parse one explicit provider timestamp without accepting local-time ambiguity."""
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(result.utcoffset() is not None, reason)
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as error:
        raise PolicyError(reason) from error


@dataclass(frozen=True)
class Change:
    """One exact Git-tree change; absent before bytes mean an added file."""

    before: bytes | None
    after: bytes | None
    before_mode: str | None = "100644"
    after_mode: str | None = "100644"


@dataclass(frozen=True)
class PublicationPlan:
    decision: str
    app_version: str
    release_tag: str
    source_sha: str
    before_sha: str
    predecessor_tag: str = ""
    admission_sha256: str = ""


def validate_predecessor(candidate, manifest_bytes, tag_commit):
    """Bind retained bytes, source, artifact and schema-two rollback together."""
    predecessor = candidate.get("predecessor")
    require(isinstance(predecessor, dict), "predecessor_missing")
    required = {"app_version", "compatibility_record", "required_artifact",
                "source_commit_sha", "artifact_sha256", "manifest_sha256"}
    require(set(predecessor) == required, "predecessor_fields")
    previous_version = predecessor["app_version"]
    require(version(previous_version) < version(candidate.get("app_version")), "predecessor_order")
    require(predecessor["compatibility_record"] == f"contracts/compatibility/app-{previous_version}.json", "predecessor_path")
    require(predecessor["required_artifact"] == "release-manifest.json", "predecessor_artifact")
    require(candidate.get("rollback") == ROLLBACK, "rollback_policy")
    identity(predecessor["source_commit_sha"])
    identity(predecessor["artifact_sha256"], DIGEST)
    identity(predecessor["manifest_sha256"], DIGEST)
    require(hashlib.sha256(manifest_bytes).hexdigest() == predecessor["manifest_sha256"], "predecessor_manifest_checksum")
    manifest = object_json(manifest_bytes)
    source = manifest.get("source", {})
    artifact = manifest.get("artifact", {})
    require(manifest.get("app_version") == previous_version, "predecessor_version")
    require(source.get("release_tag") == f"v{previous_version}", "predecessor_tag")
    require(source.get("commit_sha") == predecessor["source_commit_sha"] == tag_commit, "predecessor_source")
    require(artifact.get("name") == "virtual_casino_simulator_package.zip" and
            artifact.get("sha256") == predecessor["artifact_sha256"], "predecessor_archive")
    schema = manifest.get("mysql_schema", {})
    low, high = schema.get("minimum_version"), schema.get("expected_version")
    require(type(low) is int and type(high) is int and 1 <= low <= 2 <= high, "predecessor_schema")
    require(schema.get("apply_policy") == "held", "predecessor_apply_policy")
    return f"v{previous_version}"


def _identity_replacements(old_version, new_version, old_compatibility, new_compatibility):
    """Only exact literal identity substitutions may appear in wrapper tests."""
    pairs = {
        old_version: new_version,
        next_patch(old_version): next_patch(new_version),
    }
    for key in ("app_version", "source_commit_sha", "artifact_sha256", "manifest_sha256"):
        previous = old_compatibility["predecessor"][key]
        current = new_compatibility["predecessor"][key]
        if previous != current:
            pairs[previous] = current
    for old, new in tuple(pairs.items()):
        if VERSION.fullmatch(old):
            pairs[f"v{old}"] = f"v{new}"
            pairs[f"contracts/compatibility/app-{old}.json"] = f"contracts/compatibility/app-{new}.json"
    return pairs


def _replace_identities(text, replacements):
    """Apply identity replacements simultaneously so chained versions cannot cascade."""
    pattern = re.compile("|".join(re.escape(value) for value in sorted(replacements, key=len, reverse=True)))
    return pattern.sub(lambda match: replacements[match[0]], text)


def _test_identity_only(change, replacements):
    """Permit only simultaneous literal substitutions; every other byte stays exact."""
    try:
        expected = _replace_identities(change.before.decode("utf-8"), replacements).encode()
    except (UnicodeError, ValueError, TypeError) as error:
        raise PolicyError("wrapper_test_syntax") from error
    require(expected == change.after, "wrapper_test_behavior")


def _registry_provenance_only(change, candidate, replacements):
    """A release can align provenance, never change requirement meaning/status."""
    before, after = object_json(change.before), object_json(change.after)
    expected = json.loads(json.dumps(before))
    for record in expected.get("requirements", []):
        if record.get("id") not in {"TOOL-003", "TOOL-011"}:
            continue
        if record.get("changed_in") in replacements:
            record["changed_in"] = replacements[record["changed_in"]]
        # Notes are prose, but their only permitted wrapper change is exact identity alignment.
        record["notes"] = _replace_identities(record.get("notes", ""), replacements)
        if record.get("id") == "TOOL-003":
            path = f"contracts/compatibility/app-{candidate}.json"
            record["implementation_files"] = [*record.get("implementation_files", []), path]
    require(after == expected or after == before, "wrapper_requirement_behavior")


def validate_wrapper(before_manifest, after_manifest, changes, old_compatibility, candidate, catalog):
    """Enforce a closed semantic release-wrapper shape, not a filename waiver."""
    old_version, new_version = before_manifest.get("application"), after_manifest.get("application")
    require(new_version == next_patch(old_version), "release_requires_compatible_patch")
    required_paths = {
        MANIFEST, "pyproject.toml", "web/core/pwa_version.js", "README.md",
        "CODEX_START_HERE.md", "VERSIONING.md", "RELEASE_NOTES.md", GENERATED_REQUIREMENTS,
        f"contracts/compatibility/app-{new_version}.json",
    }
    require(required_paths <= changes.keys(), "wrapper_identity_incomplete")
    modules_before, modules_after = before_manifest.get("modules"), after_manifest.get("modules")
    require(isinstance(modules_before, dict) and isinstance(modules_after, dict), "wrapper_modules_missing")
    require(modules_before.keys() == modules_after.keys(), "wrapper_module_topology")
    touched_modules = {"application", "docs", "contracts"}
    if RELEASE_TESTS.intersection(changes):
        touched_modules.add("tests")
    expected_manifest = json.loads(json.dumps(before_manifest))
    expected_manifest["application"] = new_version
    for name in touched_modules:
        parts = version(modules_before.get(name), MODULE_VERSION)
        expected = ".".join(map(str, (*parts[:-1], parts[-1] + 1)))
        require(modules_after.get(name) == expected, "wrapper_module_patch")
        expected_manifest["modules"][name] = expected
        path = f"modules/{name}.json"
        require(path in changes, "wrapper_module_descriptor_missing")
        descriptor = changes[path]
        old, new = object_json(descriptor.before), object_json(descriptor.after)
        require(old.get("module") == name and old.get("version") == modules_before[name], "wrapper_module_baseline")
        old["version"] = expected
        require(old == new, "wrapper_module_descriptor_behavior")
    require(expected_manifest == after_manifest, "wrapper_manifest_behavior")
    require(candidate.get("app_version") == new_version and candidate.get("modules") == modules_after, "wrapper_compatibility_identity")
    require(candidate.get("predecessor", {}).get("app_version") == old_version and
            candidate["predecessor"].get("compatibility_record") == f"contracts/compatibility/app-{old_version}.json",
            "wrapper_predecessor_not_replaced_version")
    expected_keys = {"app_version", "source_baseline", "api_compatibility_matrix",
                     "release_provenance_requirement", "release_channel", "access_policy",
                     "predecessor", "rollback", "modules", "notes"}
    require(set(candidate) == expected_keys, "wrapper_compatibility_fields")
    for field in expected_keys - {"app_version", "predecessor", "modules", "notes"}:
        require(candidate[field] == old_compatibility.get(field), "wrapper_compatibility_policy")
    require(candidate["rollback"] == ROLLBACK, "wrapper_rollback_policy")
    require(candidate["source_baseline"] == after_manifest.get("source_baseline"), "wrapper_source_baseline")
    require(catalog.get("schema") == "casino-mysql-migration-catalog-v1" and
            catalog.get("apply_policy") == "held", "wrapper_catalog_policy")
    low, high = catalog.get("minimum_runtime_version"), catalog.get("expected_version")
    require(type(low) is int and type(high) is int and 1 <= low <= 2 <= high, "wrapper_schema")
    replacements = _identity_replacements(old_version, new_version, old_compatibility, candidate)
    for name in touched_modules:
        replacements[modules_before[name]] = modules_after[name]
    require(candidate.get("notes") == _replace_identities(old_compatibility.get("notes", ""), replacements),
            "wrapper_compatibility_notes")
    for path, change in changes.items():
        require(change.after is not None and change.after_mode == "100644", "wrapper_file_type")
        if path == f"contracts/compatibility/app-{new_version}.json":
            require(change.before is None and change.before_mode is None, "wrapper_compatibility_not_new")
            require(object_json(change.after) == candidate, "wrapper_compatibility_bytes")
            continue
        require(change.before is not None and change.before_mode == change.after_mode, "wrapper_file_removed_or_added")
        if path == MANIFEST or path in {f"modules/{name}.json" for name in touched_modules}:
            continue
        if path in RELEASE_DOCS:
            before_text = change.before.decode("utf-8")
            require(_replace_identities(before_text, replacements).encode() == change.after,
                    "wrapper_release_document_behavior")
        elif path == "pyproject.toml":
            old = change.before.decode("utf-8")
            pattern = re.compile(r'(?m)^version = "' + re.escape(old_version) + r'"$')
            expected, count = pattern.subn(f'version = "{new_version}"', old)
            require(count == 1 and expected.encode() == change.after, "wrapper_package_behavior")
        elif path == "web/core/pwa_version.js":
            old = f"export const PWA_APP_VERSION = '{old_version}';".encode()
            new = f"export const PWA_APP_VERSION = '{new_version}';".encode()
            require(change.before.count(old) == 1 and change.before.replace(old, new) == change.after, "wrapper_pwa_behavior")
        elif path == GENERATED_REQUIREMENTS:
            old = change.before.decode("utf-8")
            expected = old.replace(f"Packaged application release: {old_version}\n", f"Packaged application release: {new_version}\n", 1)
            for name in touched_modules:
                expected = expected.replace(f"- {name}: {modules_before[name]}\n", f"- {name}: {modules_after[name]}\n", 1)
            require(expected.encode() == change.after, "wrapper_generated_behavior")
        elif path in RELEASE_TESTS:
            _test_identity_only(change, replacements)
        elif path in REQUIREMENT_REGISTRIES:
            _registry_provenance_only(change, new_version, replacements)
        else:
            raise PolicyError("wrapper_unrelated_path")


def wrapper_premerge_metadata_sha256(pull_request, tree_sha):
    """Hash only exact wrapper metadata available before the merge occurs."""
    identity(tree_sha)
    record = {
        "repository": REPOSITORY,
        "number": pull_request.get("number"),
        "base": {"ref": pull_request.get("base", {}).get("ref"),
                 "sha": pull_request.get("base", {}).get("sha"),
                 "repo": pull_request.get("base", {}).get("repo", {}).get("full_name"),
                 "owner": {"login": pull_request.get("base", {}).get("repo", {}).get("owner", {}).get("login"),
                           "id": pull_request.get("base", {}).get("repo", {}).get("owner", {}).get("id"),
                           "type": pull_request.get("base", {}).get("repo", {}).get("owner", {}).get("type")}},
        "head": {"ref": pull_request.get("head", {}).get("ref"),
                 "sha": pull_request.get("head", {}).get("sha"),
                 "repo": pull_request.get("head", {}).get("repo", {}).get("full_name"),
                 "tree": tree_sha},
        "author": {"login": pull_request.get("user", {}).get("login"),
                   "id": pull_request.get("user", {}).get("id"),
                   "type": pull_request.get("user", {}).get("type")},
        "title": pull_request.get("title"), "body": pull_request.get("body"),
    }
    require(type(record["number"]) is int and record["number"] > 0 and
            isinstance(record["title"], str) and isinstance(record["body"], str),
            "wrapper_metadata_invalid")
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_pull_association(association, pull_request):
    """Bind a commit association record to the separately fetched canonical PR."""
    require(isinstance(association, dict) and isinstance(pull_request, dict),
            "wrapper_pull_canonical")
    require(association.get("number") == pull_request.get("number") and
            association.get("merge_commit_sha") == pull_request.get("merge_commit_sha") and
            association.get("merged_at") == pull_request.get("merged_at") and
            association.get("base", {}).get("ref") == pull_request.get("base", {}).get("ref") and
            association.get("base", {}).get("sha") == pull_request.get("base", {}).get("sha") and
            association.get("base", {}).get("repo", {}).get("full_name") ==
            pull_request.get("base", {}).get("repo", {}).get("full_name") and
            association.get("head", {}).get("ref") == pull_request.get("head", {}).get("ref") and
            association.get("head", {}).get("sha") == pull_request.get("head", {}).get("sha") and
            association.get("head", {}).get("repo", {}).get("full_name") ==
            pull_request.get("head", {}).get("repo", {}).get("full_name") and
            association.get("user", {}).get("login") == pull_request.get("user", {}).get("login") and
            association.get("user", {}).get("id") == pull_request.get("user", {}).get("id") and
            association.get("user", {}).get("type") == pull_request.get("user", {}).get("type"),
            "wrapper_pull_canonical_drift")


def pull_association_record(association):
    """Project only the validated, bounded commit-to-PR association identity."""
    return {
        "number": association["number"], "merge_commit_sha": association["merge_commit_sha"],
        "merged_at": association["merged_at"],
        "base": {"ref": association["base"]["ref"], "sha": association["base"]["sha"],
                 "repo": association["base"]["repo"]["full_name"]},
        "head": {"ref": association["head"]["ref"], "sha": association["head"]["sha"],
                 "repo": association["head"]["repo"]["full_name"]},
        "author": {"login": association["user"]["login"], "id": association["user"]["id"],
                   "type": association["user"]["type"]},
    }


def operational_receipt(role, head_sha, tree_sha, metadata_sha256):
    """Return the exact supplemental role-receipt body; it is not an approval."""
    require(role in OPERATIONAL_ACCEPTANCE_ROLES, "wrapper_receipt_role")
    identity(head_sha)
    identity(tree_sha)
    identity(metadata_sha256, DIGEST)
    return (f"{OPERATIONAL_RECEIPT_HEADER}\n"
            f"Operational role: {role}\n"
            "Verdict: ACCEPT\n"
            "Scope: supplemental only; not GitHub review approval or release authorization\n"
            f"Head: {head_sha}\n"
            f"Tree: {tree_sha}\n"
            f"Metadata-SHA256: {metadata_sha256}")


def validate_operational_receipts(comments, pull_request, head_sha, tree_sha, merged_at):
    """Require two exact unedited owner-posted role receipts, re-observed unchanged."""
    require(isinstance(comments, list) and len(comments) < 100, "wrapper_receipt_observation")
    metadata_sha256 = wrapper_premerge_metadata_sha256(pull_request, tree_sha)
    expected = {operational_receipt(role, head_sha, tree_sha, metadata_sha256)
                for role in OPERATIONAL_ACCEPTANCE_ROLES}
    receipts = [comment for comment in comments if isinstance(comment, dict) and
                isinstance(comment.get("body"), str) and
                comment["body"].startswith(OPERATIONAL_RECEIPT_HEADER)]
    require(len(receipts) == len(expected), "wrapper_receipt_inventory")
    require({comment.get("body") for comment in receipts} == expected, "wrapper_receipt_inventory")
    identifiers = [comment.get("id") for comment in receipts]
    require(all(type(identifier) is int and identifier > 0 for identifier in identifiers) and
            len(set(identifiers)) == len(identifiers), "wrapper_receipt_identity")
    for comment in receipts:
        require(comment.get("created_at") and comment.get("created_at") == comment.get("updated_at"),
                "wrapper_receipt_edited")
        require(timestamp(comment["created_at"], "wrapper_receipt_time") < merged_at,
                "wrapper_receipt_after_merge")
        require(comment.get("author_association") == "OWNER" and
                comment.get("user", {}).get("login") == REPOSITORY_OWNER and
                comment.get("user", {}).get("id") ==
                pull_request.get("base", {}).get("repo", {}).get("owner", {}).get("id") and
                comment.get("user", {}).get("type") == "User",
                "wrapper_receipt_author")


def validate_current_head_approvals(pull_request, reviews, wrapper_sha, merged_at):
    """Return one latest valid approval per non-owner human reviewer."""
    identity(wrapper_sha)
    require(isinstance(reviews, list) and len(reviews) < 100, "wrapper_review_observation")
    author = pull_request.get("user", {}).get("login")
    author_id = pull_request.get("user", {}).get("id")
    require(isinstance(author, str) and author and
            type(author_id) is int and author_id > 0 and
            pull_request.get("user", {}).get("type") == "User", "wrapper_author_identity")
    owner = pull_request.get("base", {}).get("repo", {}).get("owner", {})
    owner_id = owner.get("id")
    require(owner.get("login") == REPOSITORY_OWNER and owner.get("type") == "User" and
            type(owner_id) is int and owner_id > 0,
            "wrapper_owner_identity")
    identifiers = [review.get("id") for review in reviews if isinstance(review, dict)]
    require(len(identifiers) == len(reviews) and
            all(type(identifier) is int and identifier > 0 for identifier in identifiers) and
            len(set(identifiers)) == len(identifiers), "wrapper_review_identity")
    effective = {}
    for review in reviews:
        state, commit = review.get("state"), review.get("commit_id")
        if commit != wrapper_sha or state not in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            continue
        reviewer = review.get("user", {}).get("login")
        reviewer_id = review.get("user", {}).get("id")
        reviewer_type = review.get("user", {}).get("type")
        require(isinstance(reviewer, str) and 0 < len(reviewer) <= 100 and
                (reviewer_type == "Bot" or LOGIN.fullmatch(reviewer)) and
                type(reviewer_id) is int and reviewer_id > 0 and
                reviewer_type in {"User", "Bot"} and
                isinstance(review.get("submitted_at"), str), "wrapper_approval_invalid")
        submitted = timestamp(review["submitted_at"], "wrapper_approval_time")
        require(submitted <= merged_at, "wrapper_approval_after_merge")
        candidate = {"state": state, "login": reviewer, "id": reviewer_id,
                     "type": reviewer_type,
                     "review_id": review["id"],
                     "submitted_at": review["submitted_at"],
                     "association": review["author_association"]}
        current = effective.get(reviewer_id)
        if current is None or (submitted, candidate["review_id"]) > (
                                   timestamp(current["submitted_at"], "wrapper_approval_time"),
                                   current["review_id"]):
            effective[reviewer_id] = candidate
    approvals = {}
    for reviewer_id, review in effective.items():
        if review["state"] == "CHANGES_REQUESTED":
            raise PolicyError("wrapper_review_conflict")
        if review["state"] == "DISMISSED":
            continue
        if (review["type"] != "User" or review["login"] in {author, REPOSITORY_OWNER} or
                reviewer_id in {author_id, owner_id} or
                review["association"] not in {"COLLABORATOR", "MEMBER"}):
            continue
        review.pop("state")
        review.pop("type")
        approvals[reviewer_id] = review
    require(bool(approvals), "wrapper_approval_missing")
    return [approvals[identifier] for identifier in sorted(approvals)]


def validate_reviewer_permissions(approvals, observations):
    """Return the reviewers that retain provider-visible write authority."""
    require(isinstance(observations, dict) and
            set(observations) == {approval["id"] for approval in approvals},
            "wrapper_reviewer_permission_inventory")
    qualifying = []
    for approval in approvals:
        login, reviewer_id = approval["login"], approval["id"]
        require(isinstance(login, str) and LOGIN.fullmatch(login), "wrapper_reviewer_login")
        observation = observations[reviewer_id]
        require(isinstance(observation, dict) and
                observation.get("user", {}).get("login") == login and
                observation.get("user", {}).get("id") == reviewer_id and
                observation.get("user", {}).get("type") == "User",
                "wrapper_reviewer_permission_identity")
        if observation.get("permission") in {"write", "admin"}:
            qualifying.append(approval)
        else:
            require(observation.get("permission") in {"read", "triage", "none"},
                    "wrapper_reviewer_permission")
    require(bool(qualifying), "wrapper_reviewer_permission")
    return qualifying


def normalize_workflow_path(value, pull_number=None):
    """Accept the live bare path or GitHub's documented default-branch suffix."""
    require(isinstance(value, str), "wrapper_workflow_path")
    for path in REQUIRED_WORKFLOW_GATES:
        if value == path:
            return path
        if value in {f"{path}@main", f"{path}@refs/heads/main"}:
            return path
        if type(pull_number) is int and value == f"{path}@refs/pull/{pull_number}/merge":
            return path
    raise PolicyError("wrapper_workflow_path")


def validate_workflow_evidence(pull_request, head_pulls, runs_page, jobs_by_run,
                               check_runs_by_job, check_suites, wrapper_sha, wrapper_tree, merged_at):
    """Bind one official attempt-one successful gate run to every expected workflow."""
    identity(wrapper_sha)
    identity(wrapper_tree)
    require(isinstance(runs_page, dict), "wrapper_workflow_observation")
    runs, total = runs_page.get("workflow_runs"), runs_page.get("total_count")
    require(isinstance(runs, list) and type(total) is int and total == len(runs) and
            total == len(REQUIRED_WORKFLOW_GATES) and total < 100, "wrapper_workflow_inventory")
    number = pull_request.get("number")
    branch = pull_request.get("head", {}).get("ref")
    require(type(number) is int and number > 0 and isinstance(branch, str) and branch,
            "wrapper_pull_identity")
    require(isinstance(head_pulls, list) and len(head_pulls) < 100,
            "wrapper_head_pull_observation")
    require(len(head_pulls) == 1 and head_pulls[0].get("number") == number and
            head_pulls[0].get("merge_commit_sha") == pull_request.get("merge_commit_sha") and
            head_pulls[0].get("head", {}).get("sha") == wrapper_sha and
            head_pulls[0].get("head", {}).get("ref") == branch and
            head_pulls[0].get("base", {}).get("ref") == "main" and
            head_pulls[0].get("base", {}).get("sha") == pull_request.get("base", {}).get("sha"),
            "wrapper_head_pull_association")
    validate_pull_association(head_pulls[0], pull_request)
    by_path = {}
    run_ids = set()
    for run in runs:
        require(isinstance(run, dict), "wrapper_workflow_invalid")
        run_id, raw_path = run.get("id"), run.get("path")
        path = normalize_workflow_path(raw_path, number)
        require(type(run_id) is int and run_id > 0 and run_id not in run_ids,
                "wrapper_workflow_ambiguous")
        run_ids.add(run_id)
        require(path not in by_path,
                "wrapper_workflow_ambiguous")
        require(run.get("event") == "pull_request" and type(run.get("run_attempt")) is int and
                run.get("run_attempt") == 1 and
                run.get("status") == "completed" and run.get("conclusion") == "success",
                "wrapper_workflow_not_successful")
        require(timestamp(run.get("updated_at"), "wrapper_workflow_time") <= merged_at,
                "wrapper_workflow_after_merge")
        require(run.get("head_sha") == wrapper_sha and run.get("head_branch") == branch,
                "wrapper_workflow_head")
        require(run.get("head_commit", {}).get("id") == wrapper_sha and
                run.get("head_commit", {}).get("tree_id") == wrapper_tree,
                "wrapper_workflow_tree")
        require(run.get("repository", {}).get("full_name") == REPOSITORY and
                run.get("head_repository", {}).get("full_name") == REPOSITORY,
                "wrapper_workflow_repository")
        require(type(run.get("check_suite_id")) is int and run["check_suite_id"] > 0,
                "wrapper_workflow_suite")
        associated = run.get("pull_requests")
        require(isinstance(associated, list) and len(associated) <= 1,
                "wrapper_workflow_pull")
        if associated:
            require(associated[0].get("number") == number and
                    associated[0].get("head", {}).get("sha") == wrapper_sha and
                    associated[0].get("base", {}).get("ref") == "main",
                    "wrapper_workflow_pull")
        by_path[path] = run
    require(set(by_path) == set(REQUIRED_WORKFLOW_GATES) and
            isinstance(jobs_by_run, dict) and set(jobs_by_run) == run_ids,
            "wrapper_workflow_inventory")
    suite_id_list = [run["check_suite_id"] for run in by_path.values()]
    require(len(suite_id_list) == len(REQUIRED_WORKFLOW_GATES) and
            all(type(suite_id) is int and suite_id > 0 for suite_id in suite_id_list),
            "wrapper_suite_identity")
    suite_ids = set(suite_id_list)
    require(len(suite_ids) == len(suite_id_list),
            "wrapper_suite_ambiguous")
    require(isinstance(check_suites, dict) and set(check_suites) == suite_ids,
            "wrapper_suite_inventory")
    for run in by_path.values():
        suite = check_suites[run["check_suite_id"]]
        require(isinstance(suite, dict) and suite.get("id") == run["check_suite_id"] and
                suite.get("head_sha") == wrapper_sha and suite.get("head_branch") == branch,
                "wrapper_suite_identity")
        require(suite.get("status") == "completed" and suite.get("conclusion") == "success",
                "wrapper_suite_not_successful")
        require(timestamp(suite.get("updated_at"), "wrapper_suite_time") <= merged_at,
                "wrapper_suite_after_merge")
        app = suite.get("app", {})
        require(app.get("id") == GITHUB_ACTIONS_APP_ID and app.get("slug") == "github-actions",
                "wrapper_suite_app")
    gate_jobs = {}
    for path, run in by_path.items():
        page = jobs_by_run[run["id"]]
        require(isinstance(page, dict), "wrapper_job_observation")
        jobs, total = page.get("jobs"), page.get("total_count")
        require(isinstance(jobs, list) and type(total) is int and total == len(jobs) and total < 100,
                "wrapper_job_inventory")
        gates = [job for job in jobs if isinstance(job, dict) and
                 job.get("name") == REQUIRED_WORKFLOW_GATES[path]]
        require(len(gates) == 1, "wrapper_gate_ambiguous")
        gate = gates[0]
        require(type(gate.get("id")) is int and gate["id"] > 0,
                "wrapper_gate_identity")
        require(gate["id"] not in gate_jobs, "wrapper_gate_ambiguous")
        require(gate.get("run_id") == run["id"] and
                ("run_attempt" not in gate or
                 (type(gate["run_attempt"]) is int and gate["run_attempt"] == 1)) and
                gate.get("head_sha") == wrapper_sha, "wrapper_gate_identity")
        require(gate.get("status") == "completed" and gate.get("conclusion") == "success",
                "wrapper_gate_not_successful")
        require(timestamp(gate.get("completed_at"), "wrapper_gate_time") <= merged_at,
                "wrapper_gate_after_merge")
        require(gate.get("check_run_url") ==
                f"https://api.github.com/repos/{REPOSITORY}/check-runs/{gate.get('id')}",
                "wrapper_gate_check_url")
        gate_jobs[gate["id"]] = (gate, run)
    require(len(gate_jobs) == len(REQUIRED_WORKFLOW_GATES),
            "wrapper_gate_ambiguous")
    require(isinstance(check_runs_by_job, dict) and set(check_runs_by_job) == set(gate_jobs),
            "wrapper_check_inventory")
    for job_id, (gate, run) in gate_jobs.items():
        check = check_runs_by_job[job_id]
        require(isinstance(check, dict) and check.get("id") == job_id and
                check.get("name") == gate.get("name") and check.get("head_sha") == wrapper_sha,
                "wrapper_check_identity")
        require(check.get("status") == "completed" and check.get("conclusion") == "success",
                "wrapper_check_not_successful")
        require(timestamp(check.get("completed_at"), "wrapper_check_time") <= merged_at,
                "wrapper_check_after_merge")
        require(check.get("check_suite", {}).get("id") == run["check_suite_id"],
                "wrapper_check_suite")
        app = check.get("app", {})
        require(app.get("id") == GITHUB_ACTIONS_APP_ID and app.get("slug") == "github-actions",
                "wrapper_check_app")


def admission_fingerprint(pull_request, head_tree, approvals, reviewer_permissions,
                          comments, merge_pull, head_pulls, workflow_runs, workflow_jobs,
                          check_runs, check_suites):
    """Hash validated provider identities so a lock recheck detects replacement evidence."""
    receipts = [comment for comment in comments if isinstance(comment.get("body"), str) and
                comment["body"].startswith(OPERATIONAL_RECEIPT_HEADER)]
    runs = []
    number = pull_request["number"]
    ordered_runs = sorted(workflow_runs["workflow_runs"], key=lambda item: (
        normalize_workflow_path(item.get("path"), number), item.get("id", 0)))
    for run in ordered_runs:
        normalized_path = normalize_workflow_path(run["path"], number)
        gate_name = REQUIRED_WORKFLOW_GATES[normalized_path]
        gate = next(job for job in workflow_jobs[run["id"]]["jobs"] if job.get("name") == gate_name)
        check = check_runs[gate["id"]]
        suite = check_suites[run["check_suite_id"]]
        runs.append({
            "path": normalized_path,
            "run_id": run["id"],
            "attempt": run["run_attempt"], "status": run["status"], "conclusion": run["conclusion"],
            "updated_at": run["updated_at"],
            "head_sha": run["head_sha"], "head_branch": run["head_branch"],
            "tree_sha": run["head_commit"]["tree_id"],
            "suite": {"id": suite["id"], "status": suite["status"],
                      "conclusion": suite["conclusion"], "updated_at": suite["updated_at"],
                      "app_id": suite["app"]["id"]},
            "job": {"id": gate["id"], "name": gate["name"], "status": gate["status"],
                    "conclusion": gate["conclusion"], "completed_at": gate["completed_at"]},
            "check": {"id": check["id"], "status": check["status"],
                      "conclusion": check["conclusion"], "completed_at": check["completed_at"],
                      "app_id": check["app"]["id"]},
        })
    record = {
        "pull": {"number": pull_request["number"], "merge_commit_sha": pull_request["merge_commit_sha"],
                 "repository": REPOSITORY, "merged_at": pull_request["merged_at"],
                 "base_ref": pull_request["base"]["ref"], "base_sha": pull_request["base"]["sha"],
                 "base_repo": pull_request["base"]["repo"]["full_name"],
                 "owner": {"login": pull_request["base"]["repo"]["owner"]["login"],
                           "id": pull_request["base"]["repo"]["owner"]["id"],
                           "type": pull_request["base"]["repo"]["owner"]["type"]},
                 "head_ref": pull_request["head"]["ref"], "head_sha": pull_request["head"]["sha"],
                 "head_repo": pull_request["head"]["repo"]["full_name"],
                 "head_tree": head_tree, "author": pull_request["user"]["login"],
                 "author_id": pull_request["user"]["id"], "author_type": pull_request["user"]["type"],
                 "updated_at_observation": pull_request.get("updated_at"),
                 "premerge_metadata_sha256": wrapper_premerge_metadata_sha256(pull_request, head_tree),
                 "title_sha256": hashlib.sha256(pull_request["title"].encode()).hexdigest(),
                 "body_sha256": hashlib.sha256(pull_request["body"].encode()).hexdigest()},
        "approvals": [{**approval,
                       "permission": reviewer_permissions[approval["id"]].get("permission")}
                      for approval in approvals],
        "head_pull_association": pull_association_record(head_pulls[0]),
        "merge_pull_association": pull_association_record(merge_pull),
        "receipts": sorted(({
            "id": comment["id"],
            "body_sha256": hashlib.sha256(comment["body"].encode()).hexdigest(),
            "created_at": comment["created_at"], "updated_at": comment["updated_at"],
        } for comment in receipts), key=lambda item: item["id"]),
        "runs": runs,
    }
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def publication_intent(*, before_sha, head_sha, first_parent, forced, protected,
                       before_manifest, after_manifest, changes=None,
                       old_compatibility=None, candidate=None, catalog=None, pull_request=None,
                       second_parent=None, head_tree=None, wrapper_tree=None, reviews=None,
                       comments=None, head_pulls=None, workflow_runs=None,
                       workflow_jobs=None, check_runs=None, check_suites=None,
                       reviewer_permissions=None, merge_pull=None):
    """Unchanged versions are successful no-ops; version changes need proof."""
    identity(before_sha)
    identity(head_sha)
    require(before_sha != "0" * 40 and head_sha != "0" * 40, "push_history_missing")
    require(forced is False and protected is True, "push_not_protected_linear")
    require(first_parent == before_sha and head_sha != before_sha, "push_not_single_main_update")
    old_version, new_version = before_manifest.get("application"), after_manifest.get("application")
    version(old_version)
    version(new_version)
    if old_version == new_version:
        return PublicationPlan("noop", new_version, f"v{new_version}", head_sha, before_sha)
    require(isinstance(pull_request, dict), "wrapper_review_missing")
    identity(second_parent)
    identity(head_tree)
    identity(wrapper_tree)
    require(pull_request.get("merged_at") and pull_request.get("merge_commit_sha") == head_sha and
            pull_request.get("base", {}).get("ref") == "main" and
            pull_request.get("base", {}).get("sha") == before_sha and
            pull_request.get("base", {}).get("repo", {}).get("full_name") == REPOSITORY,
            "wrapper_merge_identity")
    merged_at = timestamp(pull_request["merged_at"], "wrapper_merge_time")
    timestamp(pull_request.get("updated_at"), "wrapper_updated_time")
    require(pull_request.get("head", {}).get("sha") == second_parent and
            pull_request.get("head", {}).get("repo", {}).get("full_name") == REPOSITORY and
            head_tree == wrapper_tree, "wrapper_head_tree_identity")
    validate_pull_association(merge_pull, pull_request)
    branch = pull_request.get("head", {}).get("ref", "")
    require(re.fullmatch(r"codex/release-v" + re.escape(new_version) + r"(?:-[a-z0-9][a-z0-9.-]*)?", branch), "wrapper_branch_identity")
    declarations = re.findall(r"(?im)^\s*Release-only:\s*(.*?)\s*$", pull_request.get("body") or "")
    require(declarations == ["yes"], "wrapper_declaration")
    require(re.search(r"(?i)\brelease\b.*\bv" + re.escape(new_version) + r"(?![.\d])", pull_request.get("title") or ""), "wrapper_title_identity")
    approvals = validate_current_head_approvals(pull_request, reviews, second_parent, merged_at)
    qualifying_approvals = validate_reviewer_permissions(approvals, reviewer_permissions)
    validate_operational_receipts(comments, pull_request, second_parent, wrapper_tree, merged_at)
    validate_workflow_evidence(pull_request, head_pulls, workflow_runs,
                               workflow_jobs, check_runs, check_suites,
                               second_parent, wrapper_tree, merged_at)
    validate_wrapper(before_manifest, after_manifest, changes or {}, old_compatibility or {}, candidate or {}, catalog or {})
    admission_sha256 = admission_fingerprint(
        pull_request, wrapper_tree, qualifying_approvals, reviewer_permissions, comments,
        merge_pull, head_pulls, workflow_runs, workflow_jobs, check_runs, check_suites)
    return PublicationPlan("publish", new_version, f"v{new_version}", head_sha, before_sha,
                           f"v{candidate['predecessor']['app_version']}", admission_sha256)


def release_state(app_version, source_sha, tag_commit, release):
    """Only complete exact-head publication is reusable; partial state is held."""
    version(app_version)
    identity(source_sha)
    if tag_commit is None and release is None:
        return "create"
    require(tag_commit == source_sha, "immutable_tag_conflict_or_partial")
    require(isinstance(release, dict), "immutable_release_missing")
    require(release.get("tag_name") == f"v{app_version}" and
            release.get("target_commitish") == source_sha, "immutable_release_identity")
    require(release.get("draft") is False and release.get("prerelease") is False and
            isinstance(release.get("published_at"), str), "immutable_release_unpublished")
    timestamp(release["published_at"], "immutable_release_unpublished")
    assets = release.get("assets")
    require(isinstance(assets, list) and len(assets) == len(ASSETS), "immutable_release_assets")
    require(all(isinstance(asset, dict) and asset.get("state") == "uploaded" and
                type(asset.get("size")) is int and asset["size"] > 0 for asset in assets), "immutable_release_assets")
    require({asset.get("name") for asset in assets} == ASSETS, "immutable_release_assets")
    return "reuse"


def api_result(status, payload, *, allow_absent=False):
    """404 is distinct from rate limits, authentication, transport and JSON errors."""
    if status == 404 and allow_absent:
        return None
    require(status == 200, "github_observation_failed")
    require(isinstance(payload, (dict, list)), "github_response_invalid")
    return payload


def publication_result(intent_result, decision, writer_result, verifier_result):
    """Keep the post-merge aggregate truthful through read-only verification."""
    return (intent_result, decision, writer_result, verifier_result) in {
        ("success", "noop", "skipped", "skipped"),
        ("success", "publish", "success", "success"),
    }


def _instant(value):
    return timestamp(value, "batch_time_invalid")


def batch_plan(observation):
    """Return evidence only; eligibility never creates or reserves a release."""
    required = {"main_sha", "released_sha", "live_sha", "app_version", "predecessor_manifest_sha256",
                "first_window", "now", "last_claimed_window", "publication", "rollout", "open_wrapper"}
    require(isinstance(observation, dict) and set(observation) == required, "batch_input_fields")
    for field in ("main_sha", "released_sha", "live_sha"):
        identity(observation[field])
    identity(observation["predecessor_manifest_sha256"], DIGEST)
    candidate = next_patch(observation["app_version"])
    now, first = _instant(observation["now"]), _instant(observation["first_window"])
    require(observation["publication"] in {"idle", "active", "failed"} and
            observation["rollout"] in {"idle", "active", "failed"} and
            type(observation["open_wrapper"]) is bool, "batch_state_invalid")
    interval = timedelta(hours=3)
    window = first + max(0, (now - first) // interval) * interval
    claimed = _instant(observation["last_claimed_window"]) if observation["last_claimed_window"] is not None else None
    if observation["publication"] != "idle" or observation["rollout"] != "idle" or observation["open_wrapper"]:
        decision, reason = "blocked", "publication_or_rollout_not_idle"
    elif observation["live_sha"] != observation["released_sha"]:
        decision, reason = "blocked", "published_release_not_live"
    elif claimed is not None and claimed >= window:
        decision, reason = "blocked", "window_already_claimed"
    elif now < first:
        decision, reason = "not-due", "before_first_window"
    elif observation["main_sha"] == observation["released_sha"]:
        decision, reason = "no-change", "accepted_main_already_released"
    else:
        decision, reason = "eligible", "new_accepted_main"
    evidence = {
        "schema": "casino-release-batch-plan-v1", "decision": decision, "reason": reason,
        "window": window.isoformat(), "candidate_version": candidate,
        "observations": json.loads(json.dumps(observation)),
    }
    evidence["plan_sha256"] = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return evidence
