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

REPOSITORY = "andreivorobiev/virtual-casino-simulator"
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
            result = json.loads(raw)
            return policy.api_result(response.status, result)
    except HTTPError as error:
        return policy.api_result(error.code, None, allow_absent=allow_absent)
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
    # Never accept ambiguous PR association as evidence of a reviewed wrapper.
    pulls = github_get(f"repos/{REPOSITORY}/commits/{head}/pulls?per_page=100")
    policy.require(isinstance(pulls, list) and len(pulls) < 100, "wrapper_pull_observation")
    matches = [pull for pull in pulls if isinstance(pull, dict) and
               pull.get("merge_commit_sha") == head and pull.get("merged_at") and
               pull.get("base", {}).get("ref") == "main"]
    policy.require(len(matches) == 1, "wrapper_pull_ambiguous")
    candidate = tree_object(root, head, f"contracts/compatibility/app-{current['application']}.json")
    arguments.update(
        changes=changed_files(root, before, head), pull_request=matches[0], candidate=candidate,
        old_compatibility=tree_object(root, before, f"contracts/compatibility/app-{old['application']}.json"),
        catalog=tree_object(root, head, "migrations/mysql/catalog.json"),
    )
    plan = policy.publication_intent(**arguments)
    if under_lock:
        current_main = github_get(f"repos/{REPOSITORY}/git/ref/heads/main")
        policy.require(current_main.get("object", {}).get("type") == "commit" and
                       current_main["object"].get("sha") == head, "protected_main_moved")
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
    return {**asdict(plan), "release_state": state}


def inspect_hosted_release(tag, head, root=ROOT):
    """Release events verify existing immutable bytes; they never upload assets."""
    policy.identity(head)
    policy.require(tag == f"v{tree_object(root, head, policy.MANIFEST)['application']}", "hosted_tag_alignment")
    candidate = tree_object(root, head, f"contracts/compatibility/app-{tag[1:]}.json")
    metadata = github_get(f"repos/{REPOSITORY}/releases/tags/{tag}")
    policy.require(policy.release_state(tag[1:], head, tag_commit(root, tag), metadata) == "reuse", "hosted_release_unpublished")
    hosted_manifest_identity(manifest_bytes(tag), candidate, head)
    previous = candidate["predecessor"]
    previous_tag = f"v{previous['app_version']}"
    metadata = github_get(f"repos/{REPOSITORY}/releases/tags/{previous_tag}")
    commit = tag_commit(root, previous_tag)
    policy.require(policy.release_state(previous["app_version"], previous["source_commit_sha"], commit, metadata) == "reuse", "predecessor_not_published")
    policy.validate_predecessor(candidate, manifest_bytes(previous_tag), commit)
    return {"app_version": tag[1:], "release_tag": tag, "source_sha": head, "predecessor_tag": previous_tag}


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
            policy.require(policy.publication_result(args.intent_result, args.decision, args.writer_result), "publication_aggregate_failed")
            print("Protected-main publication result passed.")
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
