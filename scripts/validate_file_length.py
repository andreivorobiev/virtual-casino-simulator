# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Enforce the reviewed size tripwire for tracked first-party Python and JavaScript."""

# Import calendar-date parsing for review and revisit metadata.
import datetime
# Import JSON parsing for the review register.
import json
# Import repository-relative path handling.
from pathlib import Path, PurePosixPath
# Import regular expressions for generated-source markers.
import re
# Import Git inventory execution without a shell.
import subprocess


# Resolve the default checkout independently of the caller's current directory.
ROOT = Path(__file__).resolve().parents[1]
# Point to the sole review register for exceptional large sources.
REGISTER_PATH = ROOT / "docs" / "file_length_register.json"
# Trigger review only after a source exceeds the owner-approved line threshold.
LINE_LIMIT = 1200
# Trigger review only after a source exceeds the owner-approved 96-KiB threshold.
BYTE_LIMIT = 96 * 1024
# Force re-review after growth strictly greater than twenty percent.
GROWTH_PERCENT = 20
# Exclude repository data and vendored upstream JavaScript from first-party source policy.
EXCLUDED_PREFIXES = ("data/", "web/vendor/")
# Recognize generated-source declarations only near the file header.
GENERATED_MARKER = re.compile(
    r"(?:@generated|auto-?generated|generated (?:file|source).*do not edit|do not edit.*generated)",
    re.IGNORECASE,
)
# Require every register entry to use the exact audited schema.
ENTRY_FIELDS = frozenset(
    {"path", "lines_at_review", "justification", "reviewed_by", "review_date", "revisit_after"}
)


# Report malformed policy inputs through one stable exception class.
class FileLengthPolicyError(ValueError):
    """Identify register or repository state that cannot be validated safely."""


# Count physical source lines without normalizing or executing source text.
def count_lines(raw):
    """Return the same physical-line count for LF, CRLF, or final-line-without-newline files."""
    # Treat an empty source as zero lines and every other final segment as a physical line.
    return len(raw.splitlines())


# Ask Git for the authoritative tracked Python and JavaScript inventory.
def tracked_source_paths(root):
    """Return safe repository-relative POSIX paths for tracked source only."""
    # Invoke Git directly so shell syntax cannot alter the selected inventory.
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.py", "*.js"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    # Refuse a filesystem-walk fallback when the root is not a readable worktree.
    if result.returncode != 0:
        # Preserve only Git's bounded diagnostic rather than arbitrary repository contents.
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise FileLengthPolicyError(f"Git tracked-file enumeration failed: {diagnostic}")
    # Decode Git's repository path format and discard the final empty NUL segment.
    inventory = [item for item in result.stdout.decode("utf-8").split("\0") if item]
    # Accumulate validated first-party sources in deterministic path order.
    selected = []
    for relative_text in inventory:
        # Normalize Git separators before policy comparisons on Windows.
        relative = relative_text.replace("\\", "/")
        # Skip repository data and upstream vendored source before reading file bytes.
        if any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        # Reject surprising absolute or parent-traversing inventory entries.
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise FileLengthPolicyError(f"unsafe tracked path: {relative_text}")
        # Resolve the tracked path and prove it remains a regular in-root non-link.
        candidate = root / Path(*path.parts)
        try:
            candidate.resolve().relative_to(root.resolve())
        except ValueError as error:
            raise FileLengthPolicyError(f"tracked source escapes repository: {relative}") from error
        if candidate.is_symlink() or not candidate.is_file():
            raise FileLengthPolicyError(f"tracked source is not a regular file: {relative}")
        # Retain the safe normalized path for later byte and line measurement.
        selected.append(relative)
    # Return stable order independently of Git configuration.
    return tuple(sorted(selected))


# Recognize explicitly marked generated sources without scanning executable bodies.
def is_generated_source(raw):
    """Return true only when a generated marker occurs in the first eight lines."""
    # Decode a bounded header losslessly enough for ASCII marker recognition.
    header = raw[:8192].decode("utf-8", errors="replace").splitlines()[:8]
    # Match one approved generated-source declaration in the bounded header.
    return any(GENERATED_MARKER.search(line) for line in header)


# Parse an ISO date while retaining a path-specific diagnostic.
def parse_date(value, path, field):
    """Return an exact ISO calendar date or raise a stable register error."""
    # Require the JSON value to be the canonical ten-character text form.
    if not isinstance(value, str) or len(value) != 10:
        raise FileLengthPolicyError(f"{path} {field} must be an ISO YYYY-MM-DD date")
    try:
        # Reject impossible dates through the standard calendar parser.
        parsed = datetime.date.fromisoformat(value)
    except ValueError as error:
        raise FileLengthPolicyError(f"{path} {field} must be an ISO YYYY-MM-DD date") from error
    # Reject alternative accepted parser spellings by comparing canonical output.
    if parsed.isoformat() != value:
        raise FileLengthPolicyError(f"{path} {field} must be an ISO YYYY-MM-DD date")
    return parsed


# Load and validate the complete review register before evaluating source sizes.
def load_register(register_path):
    """Return entries keyed by path after exact schema and metadata validation."""
    # Require the review register to exist whenever the gate runs.
    if not register_path.is_file():
        raise FileLengthPolicyError("docs/file_length_register.json is missing")
    try:
        # Parse the complete UTF-8 document without accepting comments or trailing syntax.
        document = json.loads(register_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FileLengthPolicyError(f"file-length register is invalid JSON: {error}") from error
    # Require one versioned top-level object so future schema changes fail closed.
    if not isinstance(document, dict) or set(document) != {"schema_version", "entries"}:
        raise FileLengthPolicyError("file-length register must contain only schema_version and entries")
    if document["schema_version"] != 1 or isinstance(document["schema_version"], bool):
        raise FileLengthPolicyError("file-length register schema_version must equal 1")
    if not isinstance(document["entries"], list):
        raise FileLengthPolicyError("file-length register entries must be a list")
    # Build an exact path-keyed mapping after validating every row.
    entries = {}
    ordered_paths = []
    for entry in document["entries"]:
        # Reject optional fields that could create ambiguous policy semantics.
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise FileLengthPolicyError("every file-length register entry must use the exact six-field schema")
        # Require a normalized relative POSIX Python or JavaScript path.
        relative = entry["path"]
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise FileLengthPolicyError("register paths must be non-empty POSIX strings")
        parsed_path = PurePosixPath(relative)
        if parsed_path.is_absolute() or ".." in parsed_path.parts or parsed_path.suffix not in {".py", ".js"}:
            raise FileLengthPolicyError(f"invalid register path: {relative}")
        if relative in entries:
            raise FileLengthPolicyError(f"duplicate register path: {relative}")
        # Require a genuine prior review line count, not a coercible Boolean.
        reviewed_lines = entry["lines_at_review"]
        if not isinstance(reviewed_lines, int) or isinstance(reviewed_lines, bool) or reviewed_lines <= 0:
            raise FileLengthPolicyError(f"{relative} lines_at_review must be a positive integer")
        # Require one substantive paragraph rather than a placeholder or multiline policy fragment.
        justification = entry["justification"]
        if not isinstance(justification, str) or len(justification.strip()) < 80 or "\n" in justification or "\r" in justification:
            raise FileLengthPolicyError(f"{relative} justification must be one substantive paragraph")
        # Require a named accountable reviewer.
        reviewer = entry["reviewed_by"]
        if not isinstance(reviewer, str) or len(reviewer.strip()) < 3:
            raise FileLengthPolicyError(f"{relative} reviewed_by must name the reviewer")
        # Require a coherent review and revisit calendar window.
        review_date = parse_date(entry["review_date"], relative, "review_date")
        revisit_after = parse_date(entry["revisit_after"], relative, "revisit_after")
        if revisit_after <= review_date:
            raise FileLengthPolicyError(f"{relative} revisit_after must be later than review_date")
        # Preserve the validated row without rewriting audit evidence.
        entries[relative] = entry
        ordered_paths.append(relative)
    # Require canonical path ordering to keep reviews and conflicts deterministic.
    if ordered_paths != sorted(ordered_paths):
        raise FileLengthPolicyError("file-length register entries must be sorted by path")
    return entries


# Compare current tracked source measurements with the exact review register.
def validate_file_lengths(root=ROOT, register_path=None):
    """Return deterministic findings; malformed policy input raises before source comparison."""
    # Normalize the caller-provided root and default register location.
    root = Path(root).resolve()
    register = Path(register_path) if register_path is not None else root / "docs" / "file_length_register.json"
    # Validate the complete register before trusting any exception row.
    entries = load_register(register)
    # Measure every tracked non-generated first-party source once.
    measurements = {}
    for relative in tracked_source_paths(root):
        # Read exact bytes so the 96-KiB threshold is encoding-independent.
        raw = (root / Path(*PurePosixPath(relative).parts)).read_bytes()
        # Exclude only explicitly marked generated sources.
        if is_generated_source(raw):
            continue
        # Retain physical lines and exact byte size for deterministic diagnostics.
        measurements[relative] = (count_lines(raw), len(raw))
    # Accumulate every independent failure rather than stopping at the first large file.
    findings = []
    for relative, (lines, size) in sorted(measurements.items()):
        # Classify a source only when either owner-approved threshold is exceeded.
        over_limit = lines > LINE_LIMIT or size > BYTE_LIMIT
        entry = entries.get(relative)
        if over_limit and entry is None:
            findings.append(f"{relative} exceeds the file-length threshold ({lines} lines, {size} bytes) without a register entry")
            continue
        if over_limit and lines * 100 > entry["lines_at_review"] * (100 + GROWTH_PERCENT):
            findings.append(f"{relative} grew more than {GROWTH_PERCENT}% past its reviewed line count ({entry['lines_at_review']} -> {lines})")
    # Reject missing, generated, excluded, or now-small entries as stale audit debt.
    for relative in sorted(entries):
        if relative not in measurements:
            findings.append(f"{relative} register entry does not name a tracked first-party source")
            continue
        lines, size = measurements[relative]
        if lines <= LINE_LIMIT and size <= BYTE_LIMIT:
            findings.append(f"{relative} register entry is stale ({lines} lines, {size} bytes)")
    # Return immutable deterministic findings for CLI and unit callers.
    return tuple(findings)


# Run the read-only repository gate and print bounded actionable diagnostics.
def main():
    """Validate the current checkout and return a conventional process status."""
    try:
        # Keep malformed register state distinct from ordinary source findings.
        findings = validate_file_lengths()
    except FileLengthPolicyError as error:
        print(f"File-length validation failed: {error}")
        return 1
    if findings:
        # Print every path-specific failure in deterministic order.
        print("File-length validation failed:")
        for finding in findings:
            print(f" - {finding}")
        return 1
    # Report both fixed thresholds so successful CI evidence is self-describing.
    print(f"File-length validation passed (lines>{LINE_LIMIT} or bytes>{BYTE_LIMIT} require review).")
    return 0


# Expose a direct executable entrypoint without import-time side effects.
if __name__ == "__main__":
    raise SystemExit(main())
