# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure release-intent and three-hour batch policy for TOOL-008 and TEST-133.

Inputs are observations, not authority: the coordinator must refresh GitHub and
live evidence before acting. This module opens no connection and owns no clock,
scheduler, repository writer, publication, or deployment operation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ast
import hashlib
import json
import re


VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
MODULE_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
ASSETS = frozenset({"checksums.txt", "release-manifest.json", "virtual_casino_simulator_package.zip"})
MANIFEST = "modules/module-manifest.json"
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


def object_json(raw):
    """Reject duplicate keys instead of allowing shadow provenance fields."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, TypeError, UnicodeError) as error:
        raise PolicyError("invalid_json") from error
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
    """Compare executable ASTs; assertions, calls, numbers and flow stay exact."""
    class ReplaceIdentity(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value in replacements:
                return ast.copy_location(ast.Constant(replacements[node.value]), node)
            return node

    try:
        before = ReplaceIdentity().visit(ast.parse(change.before))
        after = ast.parse(change.after)
    except (SyntaxError, ValueError, TypeError) as error:
        raise PolicyError("wrapper_test_syntax") from error
    require(ast.dump(before) == ast.dump(after), "wrapper_test_behavior")


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


def publication_intent(*, before_sha, head_sha, first_parent, forced, protected,
                       before_manifest, after_manifest, changes=None,
                       old_compatibility=None, candidate=None, catalog=None, pull_request=None):
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
    require(pull_request.get("merged_at") and pull_request.get("merge_commit_sha") == head_sha and
            pull_request.get("base", {}).get("ref") == "main", "wrapper_merge_identity")
    branch = pull_request.get("head", {}).get("ref", "")
    require(re.fullmatch(r"codex/release-v" + re.escape(new_version) + r"(?:-[a-z0-9][a-z0-9.-]*)?", branch), "wrapper_branch_identity")
    declarations = re.findall(r"(?im)^\s*Release-only:\s*(.*?)\s*$", pull_request.get("body") or "")
    require(declarations == ["yes"], "wrapper_declaration")
    require(re.search(r"(?i)\brelease\b.*\bv" + re.escape(new_version) + r"(?![.\d])", pull_request.get("title") or ""), "wrapper_title_identity")
    validate_wrapper(before_manifest, after_manifest, changes or {}, old_compatibility or {}, candidate or {}, catalog or {})
    return PublicationPlan("publish", new_version, f"v{new_version}", head_sha, before_sha,
                           f"v{candidate['predecessor']['app_version']}")


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


def publication_result(intent_result, decision, writer_result):
    """Keep the legacy required context truthful even when the writer is skipped."""
    return (intent_result, decision, writer_result) in {
        ("success", "noop", "skipped"), ("success", "publish", "success"),
    }


def _instant(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(result.utcoffset() is not None, "batch_time_not_explicit")
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as error:
        raise PolicyError("batch_time_invalid") from error


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
