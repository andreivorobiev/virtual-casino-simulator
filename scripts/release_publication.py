# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Observe exact release intent without publishing or contacting a host.

This TOOL-008 boundary performs bounded Git reads and GitHub GETs, then delegates
decisions to the pure cadence policy. Its CLI only emits evidence/Actions outputs;
the separately permissioned workflow owns creation and never infers absence from
an authentication, rate-limit, transport, or malformed-response failure.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))
from scripts import release_cadence as policy
from scripts import package_app

REPOSITORY = policy.REPOSITORY
MAX_RECORD_BYTES = 4 * 1024 * 1024


class SafeRedirect(HTTPRedirectHandler):
    """Public asset redirects carry no credential and stay on GitHub asset hosts."""

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        target = urlsplit(new_url)
        allowed = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
        policy.require(target.scheme == "https" and target.hostname in allowed and
                       not request.has_header("Authorization"), "github_redirect_refused")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def github_get(path, *, allow_absent=False):
    """Use only a fixed repository API, never caller-controlled URLs or writes."""
    policy.require(path.startswith(f"repos/{REPOSITORY}/"), "github_repository_scope")
    if allow_absent:
        prefix = f"repos/{REPOSITORY}/releases/tags/v"
        policy.require(path.startswith(prefix) and "?" not in path and "/" not in path[len(prefix):],
                       "github_absence_scope")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    policy.require(bool(token), "github_read_token_missing")
    request = Request(f"https://api.github.com/{path}", headers={
        "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "casino-release-intent",
    }, method="GET")
    try:
        with build_opener(SafeRedirect()).open(request, timeout=30) as response:
            raw = response.read(MAX_RECORD_BYTES + 1)
            policy.require(len(raw) <= MAX_RECORD_BYTES, "github_record_too_large")
            result = policy.json_value(raw)
            return policy.api_result(response.status, result)
    except HTTPError as error:
        return policy.api_result(error.code, None, allow_absent=allow_absent)
    except policy.PolicyError:
        raise
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise policy.PolicyError("github_observation_failed") from error


def manifest_bytes(tag):
    """Read one public immutable manifest; never send the API token to assets."""
    policy.require(tag.startswith("v"), "release_tag_invalid")
    policy.version(tag[1:])
    request = Request(f"https://github.com/{REPOSITORY}/releases/download/{tag}/release-manifest.json",
                      headers={"User-Agent": "casino-release-intent"}, method="GET")
    try:
        with build_opener(SafeRedirect()).open(request, timeout=30) as response:
            raw = response.read(MAX_RECORD_BYTES + 1)
            policy.require(response.status == 200 and len(raw) <= MAX_RECORD_BYTES, "hosted_manifest_unavailable")
            return raw
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise policy.PolicyError("hosted_manifest_unavailable") from error


def git_read(root, *arguments):
    """Read Git's exact objects; never use shell expansion or checkout mutation."""
    try:
        result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=True, timeout=30)
        return result.stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise policy.PolicyError("git_observation_failed") from error


def tree_file(root, commit, path):
    """Return authoritative blob bytes/mode, including explicit absence."""
    policy.identity(commit)
    record = git_read(root, "ls-tree", "-z", commit, "--", path)
    if not record:
        return None, None
    policy.require(record.count(b"\0") == 1, "git_tree_ambiguous")
    metadata, found_path = record[:-1].split(b"\t", 1)
    mode, kind, blob = metadata.decode("ascii").split(" ")
    policy.require(kind == "blob" and found_path.decode("utf-8") == path, "git_tree_not_file")
    payload = git_read(root, "cat-file", "blob", blob)
    policy.require(len(payload) <= MAX_RECORD_BYTES, "git_record_too_large")
    return payload, mode


def tree_object(root, commit, path):
    raw, mode = tree_file(root, commit, path)
    policy.require(raw is not None and mode == "100644", "git_record_missing_or_unsafe")
    return policy.object_json(raw)


def changed_files(root, before, head):
    names = git_read(root, "diff", "--name-only", "-z", "--no-renames", before, head, "--")
    result = {}
    for raw_path in names.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8")
        old, old_mode = tree_file(root, before, path)
        new, new_mode = tree_file(root, head, path)
        result[path] = policy.Change(old, new, old_mode, new_mode)
    return result


def tree_entries(root, commit):
    """Return one exact recursive Git-tree inventory without filesystem discovery."""
    policy.identity(commit)
    raw = git_read(root, "ls-tree", "-r", "-z", commit)
    policy.require(len(raw) <= MAX_RECORD_BYTES, "source_facts_tree")
    entries, seen = [], set()
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise policy.PolicyError("source_facts_tree") from error
        policy.require(path not in seen, "source_facts_tree")
        policy.identity(object_id)
        seen.add(path)
        entries.append((path, mode, kind, object_id))
    return entries


def deployable_tree_paths(entries):
    """Apply package policy to immutable Git entries without statting the checkout."""
    selected = []
    for path, mode, kind, _object_id in sorted(entries):
        if not package_app.is_allowlisted(path):
            continue
        reason = package_app.forbidden_reason(path)
        if reason == "forbidden runtime, test, or evidence directory":
            continue
        policy.require(reason is None, "source_facts_inventory")
        policy.require(kind == "blob" and mode in {"100644", "100755"},
                       "source_facts_inventory")
        selected.append(path)
    policy.require(package_app.REQUIRED_FILES <= set(selected), "source_facts_inventory")
    return selected


def observe_source_facts(root, source_sha, candidate_sha, after_manifest):
    """Derive closed release facts from exact Git objects and package policy."""
    policy.identity(source_sha)
    policy.identity(candidate_sha)
    source_tree = git_read(root, "rev-parse", f"{source_sha}^{{tree}}").decode("ascii").strip()
    policy.identity(source_tree)
    candidate_manifest = tree_object(root, candidate_sha, policy.MANIFEST)
    policy.require(candidate_manifest == after_manifest, "source_facts_manifest")
    modules = candidate_manifest.get("modules")
    requirements = tree_object(root, candidate_sha, "docs/requirements/requirements.json")
    rows = requirements.get("requirements")
    policy.require(isinstance(rows, list) and rows, "source_facts_requirements")
    requirement_ids = []
    for row in rows:
        requirement_id = row.get("id") if isinstance(row, dict) else None
        policy.require(isinstance(requirement_id, str) and
                       re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", requirement_id),
                       "source_facts_requirements")
        requirement_ids.append(requirement_id)
    policy.require(len(requirement_ids) == len(set(requirement_ids)), "source_facts_requirements")
    entries = tree_entries(root, candidate_sha)
    deployable = deployable_tree_paths(entries)
    return {
        "schema": policy.SOURCE_FACTS_SCHEMA,
        "source_sha": source_sha,
        "tree_sha": source_tree,
        "modules": modules,
        "permanent_requirement_count": len(rows),
        "deployable_file_count": len(deployable),
    }


def accepted_deltas_from_log(raw, predecessor_sha, source_sha):
    """Require an exact contiguous two-parent mainline from predecessor to source."""
    policy.identity(predecessor_sha)
    policy.identity(source_sha)
    policy.require(len(raw) <= MAX_RECORD_BYTES, "accepted_delta_observation")
    deltas, expected_first_parent = [], predecessor_sha
    for record in raw.split(b"\0"):
        record = record.strip(b"\r\n")
        if not record:
            continue
        try:
            raw_sha, raw_parents, raw_subject = record.split(b"\t", 2)
            commit = raw_sha.decode("ascii")
            parents = raw_parents.decode("ascii").split()
            subject = raw_subject.decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise policy.PolicyError("accepted_delta_observation") from error
        policy.identity(commit)
        policy.require(len(parents) == 2, "accepted_delta_parent_count")
        for parent in parents:
            policy.identity(parent)
        policy.require(parents[0] == expected_first_parent, "accepted_delta_first_parent")
        match = re.fullmatch(r"Merge pull request #([1-9][0-9]*) from andreivorobiev/[A-Za-z0-9._/-]+", subject)
        policy.require(match is not None, "accepted_delta_observation")
        deltas.append({"pull_request": int(match.group(1)), "merge_sha": commit})
        expected_first_parent = commit
    policy.require(bool(deltas) and expected_first_parent == source_sha,
                   "accepted_delta_source_linkage")
    return policy.validate_accepted_deltas(deltas)


def observe_accepted_deltas(root, predecessor_sha, source_sha):
    """Project verified first-parent merge identities without trusting PR prose."""
    policy.identity(predecessor_sha)
    policy.identity(source_sha)
    common = git_read(root, "merge-base", predecessor_sha, source_sha).decode("ascii").strip()
    policy.require(common == predecessor_sha, "accepted_delta_predecessor")
    raw = git_read(
        root, "log", "--first-parent", "--reverse", "--format=%H%x09%P%x09%s%x00",
        f"{predecessor_sha}..{source_sha}")
    return accepted_deltas_from_log(raw, predecessor_sha, source_sha)


def peel_tag_output(raw, tag):
    """Honor annotated-tag peeled commits without confusing tag-object hashes."""
    direct, peeled = f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"
    refs = {}
    for line in raw.decode("ascii").splitlines():
        fields = line.split("\t")
        policy.require(len(fields) == 2 and fields[1] in {direct, peeled} and fields[1] not in refs, "tag_observation_invalid")
        refs[fields[1]] = policy.identity(fields[0])
    if not refs:
        return None
    policy.require(direct in refs, "tag_observation_partial")
    return refs.get(peeled, refs[direct])


def tag_commit(root, tag):
    policy.version(tag.removeprefix("v"))
    raw = git_read(root, "ls-remote", "--tags", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    return peel_tag_output(raw, tag)


def hosted_manifest_identity(raw, candidate, head):
    """Check reuse identity before the unchanged complete archive/smoke verifier."""
    manifest = policy.object_json(raw)
    source = manifest.get("source", {})
    policy.require(manifest.get("app_version") == candidate["app_version"] and
                   source.get("release_tag") == f"v{candidate['app_version']}" and
                   source.get("commit_sha") == head, "hosted_release_identity")
    rollback = manifest.get("rollback", {})
    policy.require(rollback.get("eligible") is True and rollback.get("application_only") is True and
                   rollback.get("database_rollback") == "outside-TOOL-003" and
                   rollback.get("mysql_schema_version") == 2, "hosted_rollback_policy")
    previous, pinned = rollback.get("previous", {}), candidate["predecessor"]
    for field, pointer in (("app_version", "app_version"), ("source_commit_sha", "commit_sha"),
                           ("artifact_sha256", "artifact_sha256"), ("manifest_sha256", "manifest_sha256")):
        policy.require(previous.get(pointer) == pinned[field], "hosted_predecessor_identity")
    return manifest


def hosted_release_fingerprint(metadata, commit, manifest):
    """Hash stable hosted identity fields while excluding mutable download counts."""
    assets = metadata.get("assets") if isinstance(metadata, dict) else None
    policy.require(isinstance(assets, list), "hosted_release_assets")
    observed_assets = []
    for asset in assets:
        policy.require(isinstance(asset, dict), "hosted_release_assets")
        observed_assets.append({key: asset.get(key) for key in (
            "id", "node_id", "name", "label", "state", "content_type", "size",
            "created_at", "updated_at", "digest",
        )})
    observation = {
        "tag_name": metadata.get("tag_name"),
        "target_commitish": metadata.get("target_commitish"),
        "draft": metadata.get("draft"),
        "prerelease": metadata.get("prerelease"),
        "published_at": metadata.get("published_at"),
        "commit": commit,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "assets": sorted(observed_assets, key=lambda asset: (asset.get("name") or "", asset.get("id") or 0)),
    }
    return hashlib.sha256(json.dumps(observation, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def observe_admission(head, second_parent, *, expected_number=None):
    """Fetch one complete bounded provider snapshot for the exact merged wrapper."""
    pulls = github_get(f"repos/{REPOSITORY}/commits/{head}/pulls?per_page=100")
    policy.require(isinstance(pulls, list) and len(pulls) < 100, "wrapper_pull_observation")
    policy.require(len(pulls) == 1, "wrapper_pull_ambiguous")
    matches = [pull for pull in pulls if isinstance(pull, dict) and
               pull.get("merge_commit_sha") == head and pull.get("merged_at") and
               pull.get("base", {}).get("ref") == "main"]
    policy.require(len(matches) == 1, "wrapper_pull_ambiguous")
    number = matches[0].get("number")
    policy.require(type(number) is int and number > 0 and
                   (expected_number is None or number == expected_number), "wrapper_pull_identity")
    pull = github_get(f"repos/{REPOSITORY}/pulls/{number}")
    policy.validate_pull_association(matches[0], pull)
    reviews = github_get(f"repos/{REPOSITORY}/pulls/{number}/reviews?per_page=100")
    merged_at = policy.timestamp(pull.get("merged_at"), "wrapper_merge_time")
    approvals = policy.validate_current_head_approvals(pull, reviews, second_parent, merged_at)
    comments = github_get(f"repos/{REPOSITORY}/issues/{number}/comments?per_page=100")
    head_pulls = github_get(f"repos/{REPOSITORY}/commits/{second_parent}/pulls?per_page=100")
    policy.require(isinstance(head_pulls, list) and len(head_pulls) < 100,
                   "wrapper_head_pull_observation")
    workflow_runs = github_get(f"repos/{REPOSITORY}/actions/runs?head_sha={second_parent}&per_page=100")
    policy.require(isinstance(workflow_runs, dict) and
                   isinstance(workflow_runs.get("workflow_runs"), list),
                   "wrapper_workflow_observation")
    workflow_jobs, check_runs, check_suites = {}, {}, {}
    for run in workflow_runs["workflow_runs"]:
        policy.require(isinstance(run, dict) and type(run.get("id")) is int,
                       "wrapper_workflow_invalid")
        run_id = run["id"]
        suite_id = run.get("check_suite_id")
        if type(suite_id) is int and suite_id not in check_suites:
            check_suites[suite_id] = github_get(f"repos/{REPOSITORY}/check-suites/{suite_id}")
        page = github_get(f"repos/{REPOSITORY}/actions/runs/{run_id}/attempts/1/jobs?per_page=100")
        workflow_jobs[run_id] = page
        jobs = page.get("jobs") if isinstance(page, dict) else None
        policy.require(isinstance(jobs, list), "wrapper_job_observation")
        try:
            expected_gate = policy.REQUIRED_WORKFLOW_GATES[
                policy.normalize_workflow_path(run.get("path"), number)]
        except policy.PolicyError:
            expected_gate = None
        for job in jobs:
            if isinstance(job, dict) and job.get("name") == expected_gate and type(job.get("id")) is int:
                job_id = job["id"]
                check_runs[job_id] = github_get(f"repos/{REPOSITORY}/check-runs/{job_id}")
    # Fetch live reviewer permissions last within the snapshot to minimize revocation drift.
    reviewer_permissions = {}
    for approval in approvals:
        reviewer_permissions[approval["id"]] = github_get(
            f"repos/{REPOSITORY}/collaborators/{approval['login']}/permission")
    return {
        "pull_request": pull, "merge_pull": matches[0], "reviews": reviews,
        "reviewer_permissions": reviewer_permissions,
        "comments": comments, "head_pulls": head_pulls, "workflow_runs": workflow_runs,
        "workflow_jobs": workflow_jobs, "check_runs": check_runs, "check_suites": check_suites,
    }


def inspect_publication(event, environment, root=ROOT, *, under_lock=False):
    """Classify an exact main push and observe create/reuse state, with no writes."""
    policy.require(environment.get("GITHUB_EVENT_NAME") == "push" and
                   environment.get("GITHUB_REPOSITORY") == REPOSITORY and
                   environment.get("GITHUB_REF") == "refs/heads/main" and
                   event.get("ref") == "refs/heads/main", "push_scope_invalid")
    head, before = event.get("after"), event.get("before")
    policy.identity(head)
    policy.identity(before)
    policy.require(environment.get("GITHUB_SHA") == head and
                   git_read(root, "rev-parse", "HEAD").decode().strip() == head, "checkout_identity")
    policy.require(not git_read(root, "status", "--porcelain", "--untracked-files=no"), "checkout_tracked_dirty")
    parents = git_read(root, "show", "-s", "--format=%P", head).decode().split()
    policy.require(len(parents) in {1, 2}, "push_history_invalid")
    old = tree_object(root, before, policy.MANIFEST)
    current = tree_object(root, head, policy.MANIFEST)
    arguments = dict(before_sha=before, head_sha=head, first_parent=parents[0],
                     forced=event.get("forced"), protected=environment.get("GITHUB_REF_PROTECTED") == "true",
                     before_manifest=old, after_manifest=current)
    if old.get("application") == current.get("application"):
        result = asdict(policy.publication_intent(**arguments))
        return {**result, "release_state": "noop"}
    # A failed publication is an incident to classify, not permission for blind rerun mutation.
    policy.require(environment.get("GITHUB_RUN_ATTEMPT") == "1", "push_publication_rerun_prohibited")
    second_parent = parents[1] if len(parents) == 2 else None
    policy.require(isinstance(second_parent, str), "wrapper_merge_parent")
    head_tree = git_read(root, "rev-parse", f"{head}^{{tree}}").decode().strip()
    source_tree = git_read(root, "rev-parse", f"{before}^{{tree}}").decode().strip()
    wrapper_tree = (git_read(root, "rev-parse", f"{second_parent}^{{tree}}").decode().strip()
                    if second_parent else None)
    observed = observe_admission(head, second_parent)
    number = observed["pull_request"]["number"]
    candidate = tree_object(root, head, f"contracts/compatibility/app-{current['application']}.json")
    source_facts = observe_source_facts(root, before, head, current)
    accepted_deltas = observe_accepted_deltas(
        root, candidate.get("predecessor", {}).get("source_commit_sha"), before)
    arguments.update(
        changes=changed_files(root, before, head), candidate=candidate,
        old_compatibility=tree_object(root, before, f"contracts/compatibility/app-{old['application']}.json"),
        catalog=tree_object(root, head, "migrations/mysql/catalog.json"),
        second_parent=second_parent, head_tree=head_tree, wrapper_tree=wrapper_tree,
        source_tree=source_tree, source_facts=source_facts, accepted_deltas=accepted_deltas,
        **observed,
    )
    plan = policy.publication_intent(**arguments)
    predecessor = candidate["predecessor"]
    retained_record = tree_object(root, head, predecessor["compatibility_record"])
    policy.require(retained_record.get("app_version") == predecessor["app_version"], "retained_record_identity")
    predecessor_release = github_get(f"repos/{REPOSITORY}/releases/tags/{plan.predecessor_tag}")
    predecessor_commit = tag_commit(root, plan.predecessor_tag)
    policy.require(policy.release_state(predecessor["app_version"], predecessor["source_commit_sha"],
                                        predecessor_commit, predecessor_release) == "reuse", "predecessor_not_published")
    policy.validate_predecessor(candidate, manifest_bytes(plan.predecessor_tag), predecessor_commit)
    existing = github_get(f"repos/{REPOSITORY}/releases/tags/{plan.release_tag}", allow_absent=True)
    state = policy.release_state(plan.app_version, head, tag_commit(root, plan.release_tag), existing)
    if state == "reuse":
        hosted_manifest_identity(manifest_bytes(plan.release_tag), candidate, head)
    if under_lock:
        # Re-fetch every mutable admission record; exact main is the final provider read.
        final_observed = observe_admission(head, second_parent, expected_number=number)
        final_source_facts = observe_source_facts(root, before, head, current)
        final_accepted_deltas = observe_accepted_deltas(
            root, candidate["predecessor"]["source_commit_sha"], before)
        policy.require(final_source_facts == source_facts and
                       final_accepted_deltas == accepted_deltas,
                       "publication_source_facts_drift")
        final_arguments = {
            **arguments, **final_observed,
            "source_facts": final_source_facts,
            "accepted_deltas": final_accepted_deltas,
        }
        final_plan = policy.publication_intent(**final_arguments)
        policy.require(final_plan == plan, "publication_admission_drift")
        current_main = github_get(f"repos/{REPOSITORY}/git/ref/heads/main")
        policy.require(current_main.get("object", {}).get("type") == "commit" and
                       current_main["object"].get("sha") == head, "protected_main_moved")
    return {**asdict(plan), "release_state": state}


def inspect_hosted_release(tag, head, root=ROOT):
    """Observe stable hosted identity for direct or supplemental read-only verification."""
    policy.identity(head)
    policy.require(tag == f"v{tree_object(root, head, policy.MANIFEST)['application']}", "hosted_tag_alignment")
    candidate = tree_object(root, head, f"contracts/compatibility/app-{tag[1:]}.json")
    metadata = github_get(f"repos/{REPOSITORY}/releases/tags/{tag}")
    current_commit = tag_commit(root, tag)
    policy.require(policy.release_state(tag[1:], head, current_commit, metadata) == "reuse", "hosted_release_unpublished")
    current_manifest = manifest_bytes(tag)
    hosted_manifest_identity(current_manifest, candidate, head)
    previous = candidate["predecessor"]
    previous_tag = f"v{previous['app_version']}"
    previous_metadata = github_get(f"repos/{REPOSITORY}/releases/tags/{previous_tag}")
    previous_commit = tag_commit(root, previous_tag)
    policy.require(policy.release_state(previous["app_version"], previous["source_commit_sha"],
                                        previous_commit, previous_metadata) == "reuse",
                   "predecessor_not_published")
    previous_manifest = manifest_bytes(previous_tag)
    policy.validate_predecessor(candidate, previous_manifest, previous_commit)
    fingerprints = {
        "current": hosted_release_fingerprint(metadata, current_commit, current_manifest),
        "predecessor": hosted_release_fingerprint(previous_metadata, previous_commit, previous_manifest),
    }
    return {"app_version": tag[1:], "release_tag": tag, "source_sha": head,
            "predecessor_tag": previous_tag, "predecessor_sha": previous_commit,
            "observation_sha256": hashlib.sha256(
                json.dumps(fingerprints, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def verify_checksums(directory):
    """Authenticate exactly the two canonical asset records; no path expansion."""
    directory = Path(directory)
    for name in policy.ASSETS:
        policy.require((directory / name).is_file() and not (directory / name).is_symlink(), "hosted_asset_missing_or_linked")
    rows = (directory / "checksums.txt").read_text(encoding="ascii").splitlines()
    policy.require(len(rows) == 2, "hosted_checksum_inventory")
    expected = {"release-manifest.json", "virtual_casino_simulator_package.zip"}
    seen = set()
    for row in rows:
        match = re.fullmatch(r"([0-9a-f]{64})  (release-manifest\.json|virtual_casino_simulator_package\.zip)", row)
        policy.require(match is not None and match[2] not in seen, "hosted_checksum_inventory")
        seen.add(match[2])
        digest = hashlib.sha256()
        with (directory / match[2]).open("rb") as asset:
            for chunk in iter(lambda: asset.read(1024 * 1024), b""):
                digest.update(chunk)
        policy.require(digest.hexdigest() == match[1], "hosted_checksum_mismatch")
    policy.require(seen == expected, "hosted_checksum_inventory")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect = subparsers.add_parser("inspect", help="Emit Actions outputs for this exact protected-main push")
    inspect.add_argument("--under-lock", action="store_true", help="Also require current protected main to remain exact")
    hosted = subparsers.add_parser("inspect-hosted", help="Observe an already published immutable release")
    hosted.add_argument("--tag", required=True)
    hosted.add_argument("--commit", required=True)
    result = subparsers.add_parser("result", help="Evaluate the required publication aggregate")
    result.add_argument("--intent-result", required=True)
    result.add_argument("--decision", required=True)
    result.add_argument("--writer-result", required=True)
    result.add_argument("--verifier-result", required=True)
    checksum = subparsers.add_parser("verify-checksums", help="Read and verify downloaded canonical assets")
    checksum.add_argument("--directory", required=True, type=Path)
    batch = subparsers.add_parser("batch-plan", help="Print pure plan evidence from explicit observations")
    batch.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            event = policy.object_json(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes())
            for key, value in inspect_publication(event, os.environ, under_lock=args.under_lock).items():
                print(f"{key}={value}")
        elif args.command == "inspect-hosted":
            for key, value in inspect_hosted_release(args.tag, args.commit).items():
                print(f"{key}={value}")
        elif args.command == "result":
            policy.require(policy.publication_result(args.intent_result, args.decision,
                                                     args.writer_result, args.verifier_result),
                           "publication_aggregate_failed")
        elif args.command == "verify-checksums":
            verify_checksums(args.directory)
            print("Hosted canonical checksums passed.")
        else:
            print(json.dumps(policy.batch_plan(policy.object_json(args.input.read_bytes())), sort_keys=True, indent=2))
    except (policy.PolicyError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        reason = str(error) if isinstance(error, policy.PolicyError) else "invalid_observation"
        print(f"Release intent held: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
