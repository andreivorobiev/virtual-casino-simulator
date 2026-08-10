# Import pathlib so repository-relative source paths can be validated without caller dependence.
import pathlib
# Import regular expressions so fact headings and provenance fields use one fail-closed grammar.
import re

# Resolve the repository root from this validator's stable scripts location.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Bind the first durable facts file that every validation run must inspect.
FACTS_PATH = ROOT / "agents" / "memory" / "repository-facts.md"
# Recognize each independently governed fact entry.
FACT_HEADING_RE = re.compile(r"^## Fact:\s+(.+?)\s*$")
# Accept exactly one repository-relative source path written as inline code.
SOURCE_PATH_RE = re.compile(r"^- Source path:\s+`([^`]+)`\s*$")
# Accept exactly one full Git commit identifier written as inline code.
SOURCE_COMMIT_RE = re.compile(r"^- Source commit:\s+`([0-9a-fA-F]{40})`\s*$")


# Split the Markdown file into fact entries while preserving their line numbers for diagnostics.
def load_entries(text):
    # Collect parsed entries in source order so diagnostics are deterministic.
    entries = []
    # Track the current fact until the next governed heading begins.
    current = None
    # Inspect every source line with a human-readable one-based line number.
    for line_number, line in enumerate(text.splitlines(), start=1):
        # Detect the start of one stable fact entry.
        heading_match = FACT_HEADING_RE.fullmatch(line)
        # Start a new entry when the governed heading grammar matches.
        if heading_match:
            # Preserve the prior entry before replacing the current parse state.
            if current is not None:
                # Append the completed entry for later validation.
                entries.append(current)
            # Record the title, location, and body lines for this new entry.
            current = {"title": heading_match.group(1), "line": line_number, "lines": []}
            # Continue because the heading itself is not entry metadata.
            continue
        # Attach body content only after the first governed fact heading.
        if current is not None:
            # Preserve the exact line and location for focused metadata errors.
            current["lines"].append((line_number, line))
    # Preserve the final entry after the input loop ends.
    if current is not None:
        # Append the last completed parse state.
        entries.append(current)
    # Return every parsed fact to the validator.
    return entries


# Reject absolute, escaping, missing, or non-file source paths.
def validate_source_path(raw_path, entry, errors):
    # Normalize repository Markdown separators before resolving the path.
    normalized = pathlib.PurePosixPath(raw_path)
    # Reject absolute paths and parent traversal before filesystem resolution.
    if normalized.is_absolute() or ".." in normalized.parts:
        # Report the exact fact whose provenance escaped the repository.
        errors.append(f"{entry['title']}: source path must be repository-relative: {raw_path}")
        # Stop because an unsafe path must never be resolved.
        return
    # Resolve the candidate below the trusted repository root.
    candidate = (ROOT / pathlib.Path(*normalized.parts)).resolve()
    # Require the resolved path to remain inside the repository.
    try:
        # Compute a relative path to prove containment.
        candidate.relative_to(ROOT)
    # Convert containment failure into one stable validation error.
    except ValueError:
        # Report the escaping path without reading it.
        errors.append(f"{entry['title']}: source path escapes repository: {raw_path}")
        # Stop before any filesystem inspection outside the repository.
        return
    # Require every cited source to exist as a regular file.
    if not candidate.is_file():
        # Report the missing or non-file provenance target.
        errors.append(f"{entry['title']}: source path does not exist as a file: {raw_path}")


# Validate every stable fact and return a process status suitable for CI.
def main():
    # Collect all violations so one run gives a complete repair list.
    errors = []
    # Refuse a missing facts file instead of silently validating nothing.
    if not FACTS_PATH.is_file():
        # Emit the required path before returning failure.
        print(f"Agent memory validation failed:\n - missing facts file: {FACTS_PATH.relative_to(ROOT)}")
        # Return a nonzero status to fail closed.
        return 1
    # Read the complete UTF-8 facts file for deterministic Markdown parsing.
    text = FACTS_PATH.read_text(encoding="utf-8")
    # Split the file into independently governed entries.
    entries = load_entries(text)
    # Require at least one entry so an empty memory file cannot pass.
    if not entries:
        # Record the missing-entry defect.
        errors.append("repository-facts.md contains no '## Fact:' entries")
    # Validate each fact's exact provenance fields.
    for entry in entries:
        # Collect source-path fields from this entry only.
        source_paths = [(line_number, match.group(1)) for line_number, line in entry["lines"] if (match := SOURCE_PATH_RE.fullmatch(line))]
        # Collect full commit fields from this entry only.
        source_commits = [(line_number, match.group(1)) for line_number, line in entry["lines"] if (match := SOURCE_COMMIT_RE.fullmatch(line))]
        # Require exactly one path so ambiguous provenance fails closed.
        if len(source_paths) != 1:
            # Report the fact and observed count for focused repair.
            errors.append(f"{entry['title']}: expected exactly one Source path, found {len(source_paths)}")
        # Validate the single path only when its cardinality is unambiguous.
        else:
            # Prove the cited path exists and remains inside this repository.
            validate_source_path(source_paths[0][1], entry, errors)
        # Require exactly one full SHA so missing or abbreviated provenance fails closed.
        if len(source_commits) != 1:
            # Report the fact and observed count for focused repair.
            errors.append(f"{entry['title']}: expected exactly one 40-character Source commit, found {len(source_commits)}")
    # Print every violation and return failure when any fact is invalid.
    if errors:
        # Emit a stable heading for CI logs.
        print("Agent memory validation failed:")
        # Print each independent violation on its own line.
        for error in errors:
            # Prefix diagnostics consistently with repository validators.
            print(f" - {error}")
        # Return a nonzero status so CI rejects invalid memory.
        return 1
    # Report the exact validated entry count on success.
    print(f"Agent memory validation passed for {len(entries)} repository facts.")
    # Return success after every entry proves path and SHA provenance.
    return 0


# Execute the validator only when invoked as a script.
if __name__ == "__main__":
    # Propagate the fail-closed result to the caller and CI.
    raise SystemExit(main())
