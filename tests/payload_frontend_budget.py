"""Sanitized Package D0 payload and shipped-asset composition baseline."""

# Import argument parsing for the explicit evidence-consumer command.
import argparse
# Import the one portable already-closed descriptor error identity.
import errno
# Import JSON parsing and canonical serialization for fixed-schema evidence.
import json
# Import finite-number checks for hostile TEST-148 aggregate validation.
import math
# Import filesystem durability and atomic replacement primitives.
import os
# Import strict hexadecimal validation.
import re
# Import fixed gzip trailer packing.
import struct
# Import bounded Git subprocess execution without network access.
import subprocess
# Import fixed success and failure output streams.
import sys
# Import same-directory temporary file allocation.
import tempfile
# Import raw DEFLATE and checksum primitives for deterministic gzip members.
import zlib
# Import canonical filesystem and repository-relative path handling.
from pathlib import Path, PurePosixPath

# Resolve the exact checkout independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Identify the strict measurement-only evidence schema.
EVIDENCE_SCHEMA = "payload-frontend-baseline/v1"
# Identify the only accepted upstream TEST-148 schema.
REQUEST_SCHEMA = "request-latency-baseline/v1"
# Record the accepted deployment worker count as a non-emitted policy limitation.
ACCEPTED_WORKERS = 1
# Record the accepted deployment thread count as a non-emitted policy limitation.
ACCEPTED_THREADS = 2
# Require exact lowercase immutable Git commit identities.
SOURCE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
# Bound JSON numeric inputs to the exact interoperable integer domain.
MAX_SAFE_INTEGER = (2**53) - 1
# Bound caller evidence files before parsing hostile content.
MAX_INPUT_BYTES = 1_048_576
# Pin the TEST-148 operation count represented by every input row.
OPERATIONS_PER_INPUT_ROW = 64
# Pin the four governed input concurrency identities.
CONCURRENCY_LEVELS = (1, 2, 4, 8)
# Pin the complete input route inventory in deterministic order.
ROUTE_FAMILIES = (
    "current_user",  # Retain the authenticated current-user measurement family.
    "slots_state",  # Retain the Slots state measurement family.
    "roulette_state",  # Retain the Roulette state measurement family.
    "casino_state",  # Retain the aggregate Casino state measurement family.
    "boule_spin",  # Retain the idempotent Boule write measurement family.
)
# Pin the two approved isolated provider labels in output order.
PROVIDERS = ("json", "mysql")
# Pin the complete metadata-only local Git verb allowlist.
GIT_VERBS = frozenset({"rev-parse", "status", "ls-files", "ls-tree", "cat-file"})
# Pin only operating-system variables needed to launch the local Git executable.
GIT_OS_ENVIRONMENT_KEYS = (
    "COMSPEC",  # Retain the Windows command interpreter location.
    "PATH",  # Retain local executable resolution.
    "PATHEXT",  # Retain Windows executable suffix resolution.
    "SYSTEMROOT",  # Retain Windows runtime library resolution.
    "TEMP",  # Retain one local temporary directory.
    "TMP",  # Retain the alternate local temporary directory.
    "WINDIR",  # Retain the Windows directory alias.
)
# Pin every Git-specific environment control supplied to the child.
GIT_FIXED_ENVIRONMENT = {
    "GIT_CONFIG_COUNT": "1",  # Supply one fixed command-scope configuration override.
    "GIT_CONFIG_GLOBAL": os.devnull,  # Disable caller global Git configuration.
    "GIT_CONFIG_KEY_0": "core.fsmonitor",  # Select the daemon-capable setting.
    "GIT_CONFIG_NOSYSTEM": "1",  # Disable host system Git configuration.
    "GIT_CONFIG_VALUE_0": "false",  # Disable configured fsmonitor processes.
    "GIT_LITERAL_PATHSPECS": "1",  # Prevent pathspec magic interpretation.
    "GIT_NO_LAZY_FETCH": "1",  # Prevent promisor-object network fetches.
    "GIT_NO_REPLACE_OBJECTS": "1",  # Prevent replacement-object provenance changes.
    "GIT_OPTIONAL_LOCKS": "0",  # Prevent optional metadata lock mutation.
    "GIT_TERMINAL_PROMPT": "0",  # Prevent interactive credential prompts.
}
# Pin the complete shipped-asset family inventory in output order.
ASSET_FAMILIES = (
    "shell_javascript",  # Group top-level shipped shell and worker JavaScript.
    "shared_javascript",  # Group reusable shipped web/core JavaScript.
    "game_javascript",  # Group lazy shipped game JavaScript.
    "stylesheets",  # Group every shipped CSS asset.
)
# Pin the complete TEST-148 packet allowlist.
REQUEST_KEYS = frozenset({"schema", "source_commit", "provider", "rows"})
# Pin the complete TEST-148 row allowlist.
REQUEST_ROW_KEYS = frozenset(
    {
        "route_family",  # Retain one fixed route family.
        "concurrency",  # Retain one fixed benchmark concurrency.
        "p50_ms",  # Validate but do not republish the median.
        "p95_ms",  # Validate but do not republish the tail.
        "throughput_rps",  # Validate but do not republish throughput.
        "errors",  # Require exact zero accepted failures.
        "response_bytes",  # Consume only the aggregate response-byte total.
    }
)
# Pin the complete Package D0 top-level allowlist without unmeasured topology.
OUTPUT_KEYS = frozenset({"schema", "source_commit", "routes", "assets"})
# Pin the complete Package D0 route-row allowlist.
OUTPUT_ROUTE_KEYS = frozenset({"provider", "route_family", "operations", "bytes_per_op"})
# Pin the complete Package D0 asset-row allowlist.
OUTPUT_ASSET_KEYS = frozenset({"asset_family", "raw_bytes", "deterministic_gzip_bytes"})
# Retain one fixed safe CLI failure without reflecting caller-controlled data.
CLI_FAILURE = "payload-frontend baseline failed"
# Prefix only Package D0-owned atomic temporary files.
TEMPORARY_PREFIX = ".payload-frontend-"


# Report one fixed internal validation failure without reflecting private values.
class PayloadFrontendBudgetError(RuntimeError):
    """Stable failure raised by the measurement-only evidence consumer."""


# Validate one exact metadata-only local Git command shape.
def _git_arguments_allowed(arguments: list[str]) -> bool:
    # Reject non-lists, empty commands, and non-string arguments.
    if not isinstance(arguments, list) or not arguments or any(not isinstance(argument, str) for argument in arguments):
        # Report an invalid internal shape.
        return False
    # Accept only exact HEAD resolution.
    if arguments == ["rev-parse", "HEAD"]:
        # Approve the fixed source query.
        return True
    # Accept only one full commit tree resolution.
    if len(arguments) == 2 and arguments[0] == "rev-parse":
        # Require the exact full-hash^{tree} spelling.
        return bool(re.fullmatch(r"[0-9a-f]{40}\^\{tree\}", arguments[1]))
    # Accept only the exact tracked and untracked porcelain query.
    if arguments == ["status", "--porcelain=v1", "-z", "--untracked-files=all"]:
        # Approve the fixed clean-tree query.
        return True
    # Accept only the exact ignored shipped-web inventory.
    if arguments == ["ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--", "web"]:
        # Approve the fixed ignored-file query.
        return True
    # Accept only the exact recursive tracked-web tree query.
    if (
        len(arguments) == 7  # Require the fixed argument count.
        and arguments[:4] == ["ls-tree", "-r", "-z", "--full-tree"]  # Require the exact options.
        and SOURCE_COMMIT_PATTERN.fullmatch(arguments[4])  # Require one full lowercase commit.
        and arguments[5:] == ["--", "web"]  # Require the fixed shipped-web pathspec.
    ):  # Enforce the complete tracked-web query shape.
        # Approve the fixed immutable tree inventory.
        return True
    # Accept only one exact immutable blob read.
    if (
        len(arguments) == 3  # Require the fixed argument count.
        and arguments[:2] == ["cat-file", "blob"]  # Require one exact blob operation.
        and SOURCE_COMMIT_PATTERN.fullmatch(arguments[2])  # Require one full lowercase blob.
    ):  # Enforce the complete immutable-blob query shape.
        # Approve the fixed blob query.
        return True
    # Reject every alternate option, argument, target, and verb.
    return False


# Build the minimal fixed environment for one local metadata-only Git child.
def _git_environment() -> dict[str, str]:
    # Retain only required operating-system execution variables that are strings.
    environment = {
        key: os.environ[key]  # Preserve the exact local execution value.
        for key in GIT_OS_ENVIRONMENT_KEYS  # Inspect only the fixed OS allowlist.
        if isinstance(os.environ.get(key), str)  # Reject missing and non-string values.
    }
    # Add the fixed Git no-network and no-prompt controls.
    environment.update(GIT_FIXED_ENVIRONMENT)
    # Return no caller Git, provider, credential, proxy, or remote variables.
    return environment


# Prevent argparse from reflecting hostile argument text or paths.
class SafeArgumentParser(argparse.ArgumentParser):
    """Argument parser that collapses every invalid invocation."""

    # Replace argparse's value-bearing diagnostic with one fixed exception.
    def error(self, message):
        # Ignore the caller-controlled parser message deliberately.
        del message
        # Raise one value-free failure handled by main.
        raise PayloadFrontendBudgetError(CLI_FAILURE)


# Execute one fixed local Git command with a value-free failure boundary.
def _git(root: Path, arguments: list[str]) -> bytes:
    # Require one exact metadata-only Git command before process launch.
    if not _git_arguments_allowed(arguments):
        # Reject network-capable or malformed internal call sites.
        raise PayloadFrontendBudgetError("source inventory operation is invalid")
    # Start the bounded local metadata query without a shell.
    try:
        # Execute only the supplied internal Git argument list.
        result = subprocess.run(
            ["git", *arguments],  # Prefix the fixed local Git executable.
            cwd=str(root),  # Bind the query to the analyzed checkout.
            env=_git_environment(),  # Supply only fixed no-network local metadata controls.
            capture_output=True,  # Keep paths and Git diagnostics private.
            timeout=20,  # Bound local metadata access.
            check=False,  # Normalize nonzero status below.
        )
    # Collapse process launch and timeout failures.
    except (OSError, subprocess.TimeoutExpired):
        # Suppress command, path, and operating-system detail.
        raise PayloadFrontendBudgetError("source inventory is unavailable") from None
    # Reject every nonzero local Git result.
    if result.returncode != 0:
        # Suppress stdout and stderr completely.
        raise PayloadFrontendBudgetError("source inventory is unavailable")
    # Return only raw stdout to the internal parser.
    return result.stdout


# Resolve the immutable commit checked out in the analyzed worktree.
def checkout_head(root: Path = ROOT) -> str:
    # Query exact HEAD through the fixed local Git boundary.
    raw = _git(root, ["rev-parse", "HEAD"])
    # Decode only the expected ASCII commit identity.
    try:
        # Normalize the single returned commit.
        head = raw.decode("ascii", errors="strict").strip().lower()
    # Reject hostile or malformed metadata encoding.
    except UnicodeError:
        # Keep the failure channel value-free.
        raise PayloadFrontendBudgetError("source identity is invalid") from None
    # Require exactly one lowercase full commit.
    if not SOURCE_COMMIT_PATTERN.fullmatch(head):
        # Refuse a branch, abbreviated hash, or injected text.
        raise PayloadFrontendBudgetError("source identity is invalid")
    # Return the independently resolved commit.
    return head


# Resolve the exact tree object owned by one immutable commit.
def _checkout_tree(root: Path, source_commit: str) -> str:
    # Query the commit tree without inspecting the working filesystem.
    raw = _git(root, ["rev-parse", f"{source_commit}^{{tree}}"])
    # Decode the expected Git object identity.
    try:
        # Normalize the single tree identifier.
        tree = raw.decode("ascii", errors="strict").strip().lower()
    # Reject malformed metadata encoding.
    except UnicodeError:
        # Keep the failure channel fixed.
        raise PayloadFrontendBudgetError("source tree is invalid") from None
    # Require one full object identifier under the repository's SHA-1 format.
    if not SOURCE_COMMIT_PATTERN.fullmatch(tree):
        # Refuse missing or ambiguous tree provenance.
        raise PayloadFrontendBudgetError("source tree is invalid")
    # Return the verified tree identity for internal equality checks.
    return tree


# Require the analyzed checkout to remain one exact clean commit and tree.
def _require_exact_checkout(root: Path, source_commit: str, expected_tree: str | None = None) -> str:
    # Resolve current HEAD independently at the guard boundary.
    current_head = checkout_head(root)
    # Require immutable commit equality without reflecting either value.
    if current_head != source_commit:
        # Refuse mixed-head evidence.
        raise PayloadFrontendBudgetError("analyzed checkout changed")
    # Require a clean tracked and untracked checkout at this boundary.
    _require_clean_checkout(root)
    # Resolve the immutable tree owned by the still-current commit.
    current_tree = _checkout_tree(root, current_head)
    # Compare the tree to the initial analysis tree when supplied.
    if expected_tree is not None and current_tree != expected_tree:
        # Refuse an inconsistent source tree.
        raise PayloadFrontendBudgetError("analyzed checkout changed")
    # Return the verified tree for internal provenance continuity.
    return current_tree


# Identify a filesystem symlink or Windows junction without following it.
def _is_linklike(path: Path) -> bool:
    # Resolve the Python-version-dependent junction predicate.
    junction_predicate = getattr(path, "is_junction", None)
    # Evaluate junction identity only when the runtime exposes it.
    is_junction = bool(junction_predicate()) if callable(junction_predicate) else False
    # Reject either portable symlinks or Windows directory junctions.
    return path.is_symlink() or is_junction


# Reject indirection in every existing ancestor of one external path.
def _require_plain_ancestors(path: Path) -> None:
    # Begin with the destination or its caller-owned parent.
    current = path
    # Inspect each existing path up to the filesystem anchor.
    while True:
        # Reject symlink or junction indirection before resolution.
        if _is_linklike(current):
            # Keep the diagnostic free of the hostile path.
            raise PayloadFrontendBudgetError("external path is indirect")
        # Stop after validating the filesystem anchor.
        if current.parent == current:
            # End the bounded ancestor walk.
            break
        # Advance to the next existing ancestor.
        current = current.parent


# Determine whether one resolved path is the checkout or its descendant.
def _inside_checkout(path: Path, root: Path) -> bool:
    # Resolve the canonical checkout boundary once.
    checkout = root.resolve()
    # Return true for the root itself or any descendant.
    return path == checkout or checkout in path.parents


# Resolve one caller-owned external input evidence file.
def resolve_input_path(input_path: str | Path, root: Path = ROOT) -> Path:
    # Preserve the caller's lexical path for traversal rejection.
    candidate = Path(input_path)
    # Require one explicit absolute path.
    if not candidate.is_absolute():
        # Refuse current-directory-dependent evidence selection.
        raise PayloadFrontendBudgetError("input evidence path is invalid")
    # Reject lexical parent traversal even when it would resolve externally.
    if ".." in candidate.parts:
        # Refuse an ambiguous caller alias.
        raise PayloadFrontendBudgetError("input evidence path is invalid")
    # Reject symlink and junction ancestors before canonical resolution.
    _require_plain_ancestors(candidate)
    # Resolve only an existing evidence file.
    try:
        # Canonicalize the caller-owned evidence path.
        resolved = candidate.resolve(strict=True)
    # Collapse missing, inaccessible, or malformed path failures.
    except (OSError, RuntimeError):
        # Keep the diagnostic value-free.
        raise PayloadFrontendBudgetError("input evidence path is invalid") from None
    # Require an ordinary non-link file.
    if _is_linklike(candidate) or not resolved.is_file():
        # Refuse directory, device, and indirection inputs.
        raise PayloadFrontendBudgetError("input evidence path is invalid")
    # Require evidence storage outside the analyzed checkout.
    if _inside_checkout(resolved, root):
        # Prevent source-controlled or worktree-local evidence consumption.
        raise PayloadFrontendBudgetError("input evidence must be outside the checkout")
    # Return the canonical safe input.
    return resolved


# Resolve one caller-owned external output path without creating directories.
def resolve_output_path(output_path: str | Path, root: Path = ROOT) -> Path:
    # Preserve the lexical destination for traversal rejection.
    candidate = Path(output_path)
    # Require one explicit absolute destination.
    if not candidate.is_absolute():
        # Refuse current-directory-dependent output.
        raise PayloadFrontendBudgetError("output path is invalid")
    # Reject lexical parent traversal before canonicalization.
    if ".." in candidate.parts:
        # Refuse ambiguous output aliases.
        raise PayloadFrontendBudgetError("output path is invalid")
    # Reject symlink or junction indirection in the destination ancestry.
    _require_plain_ancestors(candidate)
    # Require the caller-owned parent directory to exist.
    if not candidate.parent.is_dir():
        # Avoid creating an unrequested directory hierarchy.
        raise PayloadFrontendBudgetError("output directory is unavailable")
    # Canonicalize the nonexisting or existing destination.
    try:
        # Resolve harmless path normalization without requiring the file.
        resolved = candidate.resolve(strict=False)
    # Collapse platform path failures.
    except (OSError, RuntimeError):
        # Keep the diagnostic fixed.
        raise PayloadFrontendBudgetError("output path is invalid") from None
    # Reject checkout-owned output through every resolved alias.
    if _inside_checkout(resolved, root):
        # Keep evidence outside source control.
        raise PayloadFrontendBudgetError("output must be outside the checkout")
    # Reject an existing directory, device, link, or junction.
    if candidate.exists() and (_is_linklike(candidate) or not resolved.is_file()):
        # Protect atomic replacement from a non-file destination.
        raise PayloadFrontendBudgetError("output path is invalid")
    # Return the canonical external destination.
    return resolved


# Reject duplicate object keys while parsing untrusted JSON.
def _unique_object(pairs):
    # Allocate one ordinary object after duplicate validation.
    result = {}
    # Inspect every decoded key/value pair in order.
    for key, value in pairs:
        # Reject duplicate keys before one value can shadow another.
        if key in result:
            # Keep the diagnostic independent of the hostile key.
            raise PayloadFrontendBudgetError("input evidence JSON is invalid")
        # Retain the unique decoded pair.
        result[key] = value
    # Return the uniquely keyed object.
    return result


# Load one bounded external TEST-148 packet.
def load_request_packet(input_path: str | Path, root: Path = ROOT) -> dict:
    # Resolve the caller-owned input through the external path policy.
    resolved = resolve_input_path(input_path, root)
    # Read the bounded evidence bytes without reflecting failures.
    try:
        # Load at most one byte beyond the allowed packet size.
        with resolved.open("rb") as handle:
            # Read a bounded amount so hostile files cannot exhaust memory.
            payload = handle.read(MAX_INPUT_BYTES + 1)
    # Collapse filesystem failures without path or exception text.
    except OSError:
        # Emit only the fixed read boundary.
        raise PayloadFrontendBudgetError("input evidence is unreadable") from None
    # Reject empty or oversized packets.
    if not payload or len(payload) > MAX_INPUT_BYTES:
        # Keep size and path out of the failure channel.
        raise PayloadFrontendBudgetError("input evidence size is invalid")
    # Decode and parse strict JSON with duplicate-key rejection.
    try:
        # Decode UTF-8 strictly before JSON parsing.
        text = payload.decode("utf-8", errors="strict")
        # Parse one complete JSON value with unique objects.
        packet = json.loads(text, object_pairs_hook=_unique_object)
    # Collapse malformed encoding, JSON, and duplicate-key failures.
    except (UnicodeError, ValueError, RecursionError, json.JSONDecodeError, PayloadFrontendBudgetError):
        # Suppress parser position, content, and exception detail.
        raise PayloadFrontendBudgetError("input evidence JSON is invalid") from None
    # Require one object at the packet root.
    if not isinstance(packet, dict):
        # Refuse scalar or collection roots.
        raise PayloadFrontendBudgetError("input evidence JSON is invalid")
    # Return the parsed packet for strict schema validation.
    return packet


# Require one bounded positive JSON number without boolean coercion.
def _positive_metric(value) -> bool:
    # Reject booleans and nonnumeric JSON values.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # Report invalidity to the caller.
        return False
    # Reject nonfinite floating-point values.
    if isinstance(value, float) and not math.isfinite(value):
        # Report invalidity to the caller.
        return False
    # Require positive values inside the exact interoperable domain.
    return 0 < value <= MAX_SAFE_INTEGER


# Validate one complete upstream TEST-148 packet.
def validate_request_packet(packet: dict, expected_provider: str, expected_source: str) -> None:
    # Require the complete top-level allowlist.
    if not isinstance(packet, dict) or set(packet) != REQUEST_KEYS:
        # Reject missing or private upstream fields.
        raise PayloadFrontendBudgetError("request evidence fields are invalid")
    # Require the exact upstream schema string.
    if not isinstance(packet.get("schema"), str) or packet["schema"] != REQUEST_SCHEMA:
        # Reject stale or ambiguous evidence versions.
        raise PayloadFrontendBudgetError("request evidence schema is invalid")
    # Require exact noncoercive source identity equality.
    source_commit = packet.get("source_commit")
    # Reject malformed or mixed-head provenance.
    if not isinstance(source_commit, str) or not SOURCE_COMMIT_PATTERN.fullmatch(source_commit) or source_commit != expected_source:
        # Keep both commit values private on mismatch.
        raise PayloadFrontendBudgetError("request evidence source is invalid")
    # Require the exact expected provider string before any membership operation.
    provider = packet.get("provider")
    # Reject mixed, duplicate, unhashable, or unknown providers.
    if not isinstance(provider, str) or provider != expected_provider or provider not in PROVIDERS:
        # Keep provider content out of the diagnostic.
        raise PayloadFrontendBudgetError("request evidence provider is invalid")
    # Require exactly the fixed five-by-four row inventory.
    rows = packet.get("rows")
    # Reject non-list and wrong-cardinality collections.
    if not isinstance(rows, list) or len(rows) != len(ROUTE_FAMILIES) * len(CONCURRENCY_LEVELS):
        # Fail closed on incomplete or oversized matrices.
        raise PayloadFrontendBudgetError("request evidence rows are invalid")
    # Build the exact expected order emitted by TEST-148.
    expected_order = [(route, concurrency) for route in ROUTE_FAMILIES for concurrency in CONCURRENCY_LEVELS]
    # Retain unique row identities after type checks.
    seen = set()
    # Validate each row against its exact deterministic position.
    for index, row in enumerate(rows):
        # Require one object with the exact upstream allowlist.
        if not isinstance(row, dict) or set(row) != REQUEST_ROW_KEYS:
            # Reject nested private or unknown fields.
            raise PayloadFrontendBudgetError("request evidence row fields are invalid")
        # Read identity fields without coercion.
        route_family = row.get("route_family")
        # Read the fixed concurrency identity.
        concurrency = row.get("concurrency")
        # Require the route string before tuple membership.
        if not isinstance(route_family, str) or route_family not in ROUTE_FAMILIES:
            # Refuse unknown or unhashable route identity.
            raise PayloadFrontendBudgetError("request evidence row identity is invalid")
        # Require a true integer concurrency.
        if isinstance(concurrency, bool) or not isinstance(concurrency, int) or concurrency not in CONCURRENCY_LEVELS:
            # Refuse boolean and floating numeric aliases.
            raise PayloadFrontendBudgetError("request evidence row identity is invalid")
        # Build the now-safe unique identity.
        identity = (route_family, concurrency)
        # Require exact TEST-148 ordering and uniqueness.
        if identity != expected_order[index] or identity in seen:
            # Reject duplicate, missing, or reordered measurements.
            raise PayloadFrontendBudgetError("request evidence row identity is invalid")
        # Record the validated row identity.
        seen.add(identity)
        # Validate timing and throughput fields without republishing them.
        for key in ("p50_ms", "p95_ms", "throughput_rps"):
            # Reject hostile scalar types, nonfinite values, and huge values.
            if not _positive_metric(row.get(key)):
                # Keep the key and value out of the diagnostic.
                raise PayloadFrontendBudgetError("request evidence aggregate is invalid")
        # Require exact percentile ordering without float coercion.
        if row["p95_ms"] < row["p50_ms"]:
            # Reject a mathematically impossible aggregate.
            raise PayloadFrontendBudgetError("request evidence aggregate is invalid")
        # Require exact integer zero errors.
        errors = row.get("errors")
        # Reject boolean, floating, and nonzero aliases.
        if isinstance(errors, bool) or not isinstance(errors, int) or errors != 0:
            # Refuse evidence with any accepted operation failure.
            raise PayloadFrontendBudgetError("request evidence errors are invalid")
        # Read the only consumed aggregate.
        response_bytes = row.get("response_bytes")
        # Require a bounded positive exact integer.
        if isinstance(response_bytes, bool) or not isinstance(response_bytes, int) or not 0 < response_bytes <= MAX_SAFE_INTEGER:
            # Reject floats, booleans, negatives, zero, and huge values.
            raise PayloadFrontendBudgetError("request evidence bytes are invalid")
    # Require exact matrix completeness after validation.
    if seen != set(expected_order):
        # Fail closed on any missing identity.
        raise PayloadFrontendBudgetError("request evidence rows are invalid")


# Build ten unique provider/route byte rows from two validated packets.
def _route_rows(packets: dict[str, dict]) -> list[dict]:
    # Retain only fixed allowlisted route aggregates.
    rows = []
    # Process providers in the fixed output order.
    for provider in PROVIDERS:
        # Read the already validated packet.
        packet = packets[provider]
        # Process route families in the fixed output order.
        for route_family in ROUTE_FAMILIES:
            # Select the four already validated concurrency cohorts for this family.
            selected = [row for row in packet["rows"] if row["route_family"] == route_family]
            # Require the exact fixed cohort count defensively.
            if len(selected) != len(CONCURRENCY_LEVELS):
                # Refuse an ambiguous or incomplete aggregation.
                raise PayloadFrontendBudgetError("route byte inventory is invalid")
            # Sum the exact upstream response-byte aggregates.
            response_bytes = sum(row["response_bytes"] for row in selected)
            # Count the exact operations represented by all four cohorts.
            operations = OPERATIONS_PER_INPUT_ROW * len(CONCURRENCY_LEVELS)
            # Divide by a power of two so every accepted integer has an exact binary result.
            bytes_per_op = response_bytes / operations
            # Require exact reconstruction before adding the measurement.
            if bytes_per_op * operations != response_bytes:
                # Refuse any arithmetic drift rather than round it.
                raise PayloadFrontendBudgetError("route byte arithmetic is invalid")
            # Append only the approved low-cardinality fields.
            rows.append(
                {
                    "provider": provider,  # Identify only JSON or MySQL.
                    "route_family": route_family,  # Identify one fixed route family.
                    "operations": operations,  # Retain all four fixed TEST-148 cohorts.
                    "bytes_per_op": bytes_per_op,  # Retain the exact numeric byte measurement.
                }
            )
    # Return the complete deterministic ten-row inventory.
    return rows


# Classify one tracked shipped asset path into a fixed evidence family.
def _asset_family(path: PurePosixPath) -> str:
    # Normalize only the extension for cross-platform shipped-asset recognition.
    suffix = path.suffix.lower()
    # Group every CSS asset independently of its directory.
    if suffix == ".css":
        # Return the one stylesheet family.
        return "stylesheets"
    # Group lazy game JavaScript under its owned directory.
    if len(path.parts) >= 3 and path.parts[:2] == ("web", "games"):
        # Return the game module family.
        return "game_javascript"
    # Group shared JavaScript under web/core.
    if len(path.parts) >= 3 and path.parts[:2] == ("web", "core"):
        # Return the reusable shared family.
        return "shared_javascript"
    # Group remaining shipped JavaScript as shell assets.
    if suffix == ".js" and path.parts and path.parts[0] == "web":
        # Return the shell and service-worker family.
        return "shell_javascript"
    # Reject any caller misuse outside the tracked JS/CSS inventory.
    raise PayloadFrontendBudgetError("asset classification is invalid")


# Produce one deterministic gzip member with fixed timestamp, level, and OS header.
def deterministic_gzip(payload: bytes) -> bytes:
    # Require immutable byte input.
    if not isinstance(payload, bytes):
        # Refuse implicit text encoding or mutable buffers.
        raise PayloadFrontendBudgetError("asset bytes are invalid")
    # Create a raw DEFLATE compressor at the fixed maximum level.
    compressor = zlib.compressobj(
        level=9,  # Fix compression level.
        method=zlib.DEFLATED,  # Use standard DEFLATE.
        wbits=-zlib.MAX_WBITS,  # Exclude a platform-dependent wrapper.
        memLevel=9,  # Fix compressor memory behavior.
        strategy=zlib.Z_DEFAULT_STRATEGY,  # Fix the compression strategy.
    )
    # Compress and flush the complete asset.
    compressed = compressor.compress(payload) + compressor.flush()
    # Build a fixed gzip header with mtime zero, maximum-level flag, and unknown OS.
    header = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff"
    # Build the standard little-endian checksum and modulo-size trailer.
    trailer = struct.pack("<II", zlib.crc32(payload) & 0xFFFFFFFF, len(payload) & 0xFFFFFFFF)
    # Return one byte-identical gzip member across supported hosts.
    return header + compressed + trailer


# Require a clean analyzed checkout and no ignored shipped asset candidates.
def _require_clean_checkout(root: Path) -> None:
    # Read tracked, staged, and untracked status in an unambiguous NUL format.
    status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    # Reject every dirty tracked or untracked path.
    if status:
        # Keep filenames and status data private.
        raise PayloadFrontendBudgetError("analyzed checkout is dirty")
    # Enumerate ignored web files that ordinary status intentionally omits.
    ignored = _git(root, ["ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--", "web"])
    # Inspect every ignored candidate without reflecting its name.
    for raw_path in ignored.split(b"\x00"):
        # Skip the required terminal empty record.
        if not raw_path:
            # Continue to the next candidate.
            continue
        # Decode repository paths strictly.
        try:
            # Normalize the candidate only for suffix inspection.
            path = PurePosixPath(raw_path.decode("utf-8", errors="strict"))
        # Reject undecodable metadata.
        except UnicodeError:
            # Keep raw bytes out of diagnostics.
            raise PayloadFrontendBudgetError("ignored asset inventory is invalid") from None
        # Reject every ignored shipped-asset-shaped candidate.
        if path.suffix.lower() in {".js", ".css"}:
            # Prevent ignored assets from escaping the tracked inventory.
            raise PayloadFrontendBudgetError("ignored shipped asset is present")


# Parse one exact Git tree into tracked shipped asset entries.
def _tracked_asset_entries(root: Path, source_commit: str) -> list[tuple[PurePosixPath, str]]:
    # Enumerate every tracked object below web from the exact immutable commit.
    raw = _git(root, ["ls-tree", "-r", "-z", "--full-tree", source_commit, "--", "web"])
    # Retain validated path/blob pairs.
    assets = []
    # Track case-folded paths so cross-platform aliases fail closed.
    casefolded = set()
    # Parse each NUL-delimited Git tree record.
    for record in raw.split(b"\x00"):
        # Skip the required terminal empty record.
        if not record:
            # Continue to the next tree entry.
            continue
        # Split fixed metadata from the repository path.
        try:
            # Separate the tree header and path at the first tab.
            header, raw_path = record.split(b"\t", 1)
            # Decode fixed ASCII object metadata.
            mode, object_type, object_id = header.decode("ascii", errors="strict").split(" ")
            # Decode the Git path as strict UTF-8.
            path_text = raw_path.decode("utf-8", errors="strict")
        # Collapse malformed tree records.
        except (ValueError, UnicodeError):
            # Keep object and path bytes private.
            raise PayloadFrontendBudgetError("tracked asset inventory is invalid") from None
        # Parse one repository-relative POSIX path.
        path = PurePosixPath(path_text)
        # Reject absolute, traversal, dot, or backslash aliases.
        if path.is_absolute() or not path.parts or path.parts[0] != "web" or ".." in path.parts or "." in path.parts or "\\" in path_text:
            # Prevent tree escape and platform ambiguity.
            raise PayloadFrontendBudgetError("tracked asset path is invalid")
        # Reject every symlink or submodule below the shipped web root.
        if mode in {"120000", "160000"} or object_type == "commit":
            # Prevent indirection from hiding shipped assets.
            raise PayloadFrontendBudgetError("tracked web indirection is forbidden")
        # Skip ordinary tracked non-JS/CSS assets after indirection validation.
        if path.suffix.lower() not in {".js", ".css"}:
            # Continue to the next tracked object.
            continue
        # Require an ordinary blob and regular file mode.
        if object_type != "blob" or mode not in {"100644", "100755"} or not SOURCE_COMMIT_PATTERN.fullmatch(object_id):
            # Reject non-file shipped asset entries.
            raise PayloadFrontendBudgetError("tracked asset object is invalid")
        # Normalize the path for cross-platform duplicate detection.
        folded = path_text.casefold()
        # Reject case aliases that cannot coexist safely on every target.
        if folded in casefolded:
            # Prevent one asset from receiving two logical identities.
            raise PayloadFrontendBudgetError("tracked asset paths collide")
        # Record the unique case-folded identity.
        casefolded.add(folded)
        # Retain the exact path and blob identity.
        assets.append((path, object_id))
    # Require at least one asset in every fixed family.
    if {_asset_family(path) for path, _object_id in assets} != set(ASSET_FAMILIES):
        # Fail closed when the shipped inventory shape changes.
        raise PayloadFrontendBudgetError("tracked asset families are incomplete")
    # Return every relevant tracked object exactly once.
    return assets


# Read one worktree asset and prove byte equality with its immutable Git blob.
def _verified_asset_bytes(root: Path, path: PurePosixPath, object_id: str) -> bytes:
    # Normalize the lexical checkout path without following reparse points.
    lexical_root = root.absolute()
    # Build the platform worktree path from validated POSIX parts.
    candidate = lexical_root.joinpath(*path.parts)
    # Start the component walk at the asset leaf.
    current = candidate
    # Inspect every lexical component through the checkout root.
    while True:
        # Reject link or junction indirection before canonical resolution.
        if _is_linklike(current):
            # Keep the path out of the diagnostic.
            raise PayloadFrontendBudgetError("worktree asset is indirect")
        # Stop after validating the checkout root itself.
        if current == lexical_root:
            # End the bounded component walk.
            break
        # Reject an impossible walk outside the lexical checkout.
        if current.parent == current or lexical_root not in current.parents:
            # Refuse malformed component ancestry.
            raise PayloadFrontendBudgetError("worktree asset is invalid")
        # Advance to the next lexical parent.
        current = current.parent
    # Resolve the existing worktree file.
    try:
        # Canonicalize the exact shipped asset.
        resolved = candidate.resolve(strict=True)
    # Collapse missing or inaccessible asset failures.
    except (OSError, RuntimeError):
        # Keep path and OS detail private.
        raise PayloadFrontendBudgetError("worktree asset is unavailable") from None
    # Require containment beneath the exact checkout.
    if root.resolve() not in resolved.parents or not resolved.is_file():
        # Reject directories, devices, and outside-root paths.
        raise PayloadFrontendBudgetError("worktree asset is invalid")
    # Read the worktree bytes without text or newline conversion.
    try:
        # Load the exact shipped bytes.
        worktree_bytes = resolved.read_bytes()
    # Collapse read failures.
    except OSError:
        # Keep the path and exception private.
        raise PayloadFrontendBudgetError("worktree asset is unreadable") from None
    # Read the immutable Git blob by verified object identity.
    blob_bytes = _git(root, ["cat-file", "blob", object_id])
    # Require byte-for-byte equality between worktree and commit.
    if worktree_bytes != blob_bytes:
        # Refuse evidence from filtered, stale, or modified bytes.
        raise PayloadFrontendBudgetError("worktree asset does not match source")
    # Return the exact verified shipped bytes.
    return worktree_bytes


# Build four fixed asset-family byte rows from the exact tracked tree.
def _asset_rows(root: Path, source_commit: str) -> list[dict]:
    # Initialize exact integer totals for every fixed family.
    totals = {family: {"raw_bytes": 0, "deterministic_gzip_bytes": 0} for family in ASSET_FAMILIES}
    # Enumerate the exact tracked shipped asset inventory.
    entries = _tracked_asset_entries(root, source_commit)
    # Process every asset exactly once.
    for path, object_id in entries:
        # Resolve the fixed family without emitting the path.
        family = _asset_family(path)
        # Read and verify exact worktree/blob equality.
        payload = _verified_asset_bytes(root, path, object_id)
        # Add exact uncompressed bytes.
        totals[family]["raw_bytes"] += len(payload)
        # Add one deterministic per-file gzip member size.
        totals[family]["deterministic_gzip_bytes"] += len(deterministic_gzip(payload))
    # Emit rows in the fixed family order.
    return [
        {
            "asset_family": family,  # Identify one fixed low-cardinality family.
            "raw_bytes": totals[family]["raw_bytes"],  # Retain exact raw bytes.
            "deterministic_gzip_bytes": totals[family]["deterministic_gzip_bytes"],  # Retain exact gzip bytes.
        }
        for family in ASSET_FAMILIES  # Preserve the fixed evidence order.
    ]


# Validate the complete Package D0 output schema and domains.
def validate_output(evidence: dict) -> None:
    # Require the complete top-level allowlist.
    if not isinstance(evidence, dict) or set(evidence) != OUTPUT_KEYS:
        # Reject missing or private fields.
        raise PayloadFrontendBudgetError("output fields are invalid")
    # Require the exact schema string.
    if not isinstance(evidence.get("schema"), str) or evidence["schema"] != EVIDENCE_SCHEMA:
        # Reject unknown output versions.
        raise PayloadFrontendBudgetError("output schema is invalid")
    # Require exact immutable source provenance.
    source_commit = evidence.get("source_commit")
    # Reject numeric, list, malformed, or abbreviated identities.
    if not isinstance(source_commit, str) or not SOURCE_COMMIT_PATTERN.fullmatch(source_commit):
        # Keep the hostile source value private.
        raise PayloadFrontendBudgetError("output source is invalid")
    # Require exactly two providers by five unique route families.
    routes = evidence.get("routes")
    # Reject malformed or incomplete route collections.
    if not isinstance(routes, list) or len(routes) != len(PROVIDERS) * len(ROUTE_FAMILIES):
        # Fail closed on route inventory drift.
        raise PayloadFrontendBudgetError("output routes are invalid")
    # Build the exact expected route order.
    expected_routes = [(provider, route) for provider in PROVIDERS for route in ROUTE_FAMILIES]
    # Retain unique semantic identities after validation.
    seen_routes = set()
    # Validate each output route row.
    for index, row in enumerate(routes):
        # Require one object with the exact row allowlist.
        if not isinstance(row, dict) or set(row) != OUTPUT_ROUTE_KEYS:
            # Reject nested private or unknown fields.
            raise PayloadFrontendBudgetError("output route fields are invalid")
        # Read exact string identities before comparison.
        provider = row.get("provider")
        # Read the fixed route family.
        route_family = row.get("route_family")
        # Require exact expected identity and order.
        if not isinstance(provider, str) or not isinstance(route_family, str) or (provider, route_family) != expected_routes[index]:
            # Reject duplicates, omissions, and unhashable values.
            raise PayloadFrontendBudgetError("output route identity is invalid")
        # Require each semantic identity exactly once.
        if (provider, route_family) in seen_routes:
            # Reject indistinguishable duplicate rows.
            raise PayloadFrontendBudgetError("output route identity is invalid")
        # Record the validated unique identity.
        seen_routes.add((provider, route_family))
        # Require the exact TEST-148 operation count.
        operations = row.get("operations")
        # Reject boolean, float, and alternate operation counts.
        if (
            isinstance(operations, bool)  # Reject boolean integer aliases.
            or not isinstance(operations, int)  # Require a true integer.
            or operations != OPERATIONS_PER_INPUT_ROW * len(CONCURRENCY_LEVELS)  # Require 256.
        ):  # Enforce the fixed aggregate operation count.
            # Keep the hostile value private.
            raise PayloadFrontendBudgetError("output route operations are invalid")
        # Require one strict finite positive numeric byte value.
        bytes_per_op = row.get("bytes_per_op")
        # Reject booleans, strings, containers, and other non-numbers.
        if isinstance(bytes_per_op, bool) or not isinstance(bytes_per_op, (int, float)):
            # Refuse schema type surprises.
            raise PayloadFrontendBudgetError("output route bytes are invalid")
        # Reject nonfinite floating-point values without coercing integers.
        if isinstance(bytes_per_op, float) and not math.isfinite(bytes_per_op):
            # Refuse NaN and infinity.
            raise PayloadFrontendBudgetError("output route bytes are invalid")
        # Reconstruct the exact input aggregate using the fixed power-of-two divisor.
        response_bytes = bytes_per_op * operations
        # Require a positive exact safe integer reconstruction.
        if (
            bytes_per_op <= 0  # Reject zero and negative measurements.
            or not isinstance(response_bytes, (int, float))  # Require numeric reconstruction.
            or isinstance(response_bytes, float) and not math.isfinite(response_bytes)  # Reject nonfinite results.
            or response_bytes != int(response_bytes)  # Reject fractional reconstruction.
            or not 0 < int(response_bytes) <= MAX_SAFE_INTEGER  # Require the safe positive domain.
        ):  # Enforce exact finite positive byte reconstruction.
            # Reject fractional drift, zero, negatives, and huge values.
            raise PayloadFrontendBudgetError("output route bytes are invalid")
    # Require exactly one row for every fixed asset family.
    assets = evidence.get("assets")
    # Reject malformed or incomplete asset collections.
    if not isinstance(assets, list) or len(assets) != len(ASSET_FAMILIES):
        # Fail closed on asset inventory drift.
        raise PayloadFrontendBudgetError("output assets are invalid")
    # Validate each asset row in fixed order.
    for index, row in enumerate(assets):
        # Require one object with the exact asset allowlist.
        if not isinstance(row, dict) or set(row) != OUTPUT_ASSET_KEYS:
            # Reject filenames, paths, or private nested data.
            raise PayloadFrontendBudgetError("output asset fields are invalid")
        # Require the exact fixed family string.
        if not isinstance(row.get("asset_family"), str) or row["asset_family"] != ASSET_FAMILIES[index]:
            # Reject unknown, duplicate, or unhashable family identities.
            raise PayloadFrontendBudgetError("output asset identity is invalid")
        # Validate both exact byte counts.
        for key in ("raw_bytes", "deterministic_gzip_bytes"):
            # Read the integer count.
            value = row.get(key)
            # Reject booleans, floats, negatives, and huge values.
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SAFE_INTEGER:
                # Keep key and value out of the diagnostic.
                raise PayloadFrontendBudgetError("output asset bytes are invalid")


# Build one complete measurement-only output from two fresh TEST-148 packets.
def build_evidence(  # Build one strict output from two provider packets.
    json_evidence_path: str | Path,  # Select the external JSON packet.
    mysql_evidence_path: str | Path,  # Select the external MySQL packet.
    root: Path = ROOT,  # Bind analysis to one explicit checkout.
) -> dict:  # Return the validated low-cardinality document.
    # Resolve exact checkout provenance before consuming evidence.
    source_commit = checkout_head(root)
    # Resolve and retain the exact initial clean tree identity.
    source_tree = _require_exact_checkout(root, source_commit)
    # Load the fresh JSON provider packet.
    json_packet = load_request_packet(json_evidence_path, root)
    # Load the fresh MySQL provider packet.
    mysql_packet = load_request_packet(mysql_evidence_path, root)
    # Validate the JSON packet against exact source and provider.
    validate_request_packet(json_packet, "json", source_commit)
    # Validate the MySQL packet against the same exact source.
    validate_request_packet(mysql_packet, "mysql", source_commit)
    # Build the complete fixed output.
    evidence = {
        "schema": EVIDENCE_SCHEMA,  # Identify the strict measurement schema.
        "source_commit": source_commit,  # Bind every aggregate to exact clean HEAD.
        "routes": _route_rows({"json": json_packet, "mysql": mysql_packet}),  # Aggregate exact route bytes.
        "assets": _asset_rows(root, source_commit),  # Aggregate exact tracked asset bytes.
    }
    # Validate the completed output recursively before returning it.
    validate_output(evidence)
    # Re-read HEAD, tree, tracked state, and untracked state after analysis.
    _require_exact_checkout(root, source_commit, source_tree)
    # Return only the sanitized allowlisted evidence.
    return evidence


# Serialize validated output into deterministic canonical bytes.
def _serialized_output(evidence: dict) -> bytes:
    # Validate the full recursive schema before serialization.
    validate_output(evidence)
    # Serialize with fixed ASCII escaping, key order, and separators.
    try:
        # Encode one canonical newline-terminated JSON document.
        return (json.dumps(evidence, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    # Collapse unexpected serialization failures.
    except (TypeError, ValueError, UnicodeError):
        # Keep data and exception detail private.
        raise PayloadFrontendBudgetError("output serialization failed") from None


# Atomically write validated output to one caller-owned external destination.
def write_evidence_atomic(  # Write one strict document atomically.
    output_path: str | Path,  # Select the external destination.
    evidence: dict,  # Supply the recursively validated document.
    root: Path = ROOT,  # Re-bind provenance to one explicit checkout.
) -> Path:  # Return the canonical written path.
    # Serialize completely before touching the caller's destination.
    payload = _serialized_output(evidence)
    # Bind the structurally valid source to the current clean checkout before output touch.
    _require_exact_checkout(root, evidence["source_commit"])
    # Resolve the canonical external output.
    output = resolve_output_path(output_path, root)
    # Track only the temporary file allocated by this function.
    temporary_path = None
    # Track raw descriptor ownership until fdopen transfers it.
    raw_descriptor = None
    # Protect cleanup across allocation, write, fsync, and replace failures.
    try:
        # Allocate the temporary file beside the destination for same-filesystem replace.
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=TEMPORARY_PREFIX,  # Identify only Package D0-owned temporary files.
            suffix=".tmp",  # Keep temporary files distinct from evidence.
            dir=str(output.parent),  # Guarantee same-filesystem replacement.
        )
        # Retain raw descriptor ownership before the stream transfer.
        raw_descriptor = descriptor
        # Retain the owned path for cleanup.
        temporary_path = Path(temporary_name)
        # Transfer descriptor ownership to one binary stream.
        handle = os.fdopen(raw_descriptor, "wb")
        # Mark raw ownership transferred only after fdopen succeeds.
        raw_descriptor = None
        # Close the transferred stream after write and durability work.
        with handle:
            # Write the complete canonical payload.
            handle.write(payload)
            # Flush Python buffers to the descriptor.
            handle.flush()
            # Flush the complete file before replacement.
            os.fsync(handle.fileno())
        # Re-check exact source and clean-tree provenance immediately before replacement.
        _require_exact_checkout(root, evidence["source_commit"])
        # Atomically replace the caller-selected destination.
        os.replace(temporary_path, output)
        # Mark the temporary path consumed only after successful replacement.
        temporary_path = None
    # Collapse allocation, write, flush, and replacement failures.
    except OSError:
        # Keep destination, temporary path, and OS detail private.
        raise PayloadFrontendBudgetError("output write failed") from None
    # Remove only the owned temporary file after every failure.
    finally:
        # Record cleanup failure without skipping later cleanup actions.
        cleanup_failed = False
        # Close a descriptor whose stream transfer never completed.
        if raw_descriptor is not None:
            # Attempt exactly one raw descriptor close.
            try:
                # Release the still-owned operating-system handle.
                os.close(raw_descriptor)
            # Treat an already-closed descriptor as successfully released.
            except OSError as exception:
                # Fail only for cleanup errors other than EBADF.
                if exception.errno != errno.EBADF:
                    # Record the handle cleanup failure for final reporting.
                    cleanup_failed = True
        # Check whether an allocated temporary path remains.
        if temporary_path is not None and temporary_path.exists():
            # Attempt removal without reflecting the owned path.
            try:
                # Remove only that exact Package D0-owned file.
                temporary_path.unlink()
            # Collapse cleanup failures into the same value-free boundary.
            except OSError:
                # Record the path cleanup failure for final reporting.
                cleanup_failed = True
        # Report cleanup failure only after attempting both owned resources.
        if cleanup_failed:
            # Refuse to hide incomplete cleanup without leaking raw detail.
            raise PayloadFrontendBudgetError("output cleanup failed") from None
    # Return the canonical written destination.
    return output


# Build the fixed command-line parser without runtime or target selectors.
def _parser() -> SafeArgumentParser:
    # Create one parser with ordinary help but fixed errors.
    parser = SafeArgumentParser(prog="payload-frontend-budget")
    # Accept only one external JSON-provider TEST-148 packet.
    parser.add_argument("--json-evidence", required=True)
    # Accept only one external MySQL-provider TEST-148 packet.
    parser.add_argument("--mysql-evidence", required=True)
    # Accept only one caller-owned external output destination.
    parser.add_argument("--output", required=True)
    # Return the complete fixed parser.
    return parser


# Run the explicit evidence consumer with fixed success and failure channels.
def main(argv=None) -> int:
    # Protect every parse, provenance, input, Git, asset, and write failure.
    try:
        # Parse only the three approved file selectors.
        arguments = _parser().parse_args(argv)
        # Build the complete sanitized evidence without importing Casino runtime.
        evidence = build_evidence(arguments.json_evidence, arguments.mysql_evidence)
        # Write only the validated caller-external output.
        write_evidence_atomic(arguments.output, evidence)
    # Collapse every ordinary failure without traceback, path, or exception text.
    except Exception:
        # Write one fixed failure line to standard error.
        sys.stderr.write(CLI_FAILURE + "\n")
        # Return one fixed nonzero status.
        return 1
    # Write one fixed success line without the output path.
    sys.stdout.write("payload-frontend baseline complete\n")
    # Return success.
    return 0


# Execute only when selected explicitly as a module or script.
if __name__ == "__main__":
    # Delegate process status to the fixed CLI boundary.
    raise SystemExit(main())
