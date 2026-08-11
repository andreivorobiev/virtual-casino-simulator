# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Generate deterministic requirement and documentation indexes from repository sources.
import argparse
import json
import pathlib
# Import subprocess so the documentation index uses Git's canonical tracked/untracked file view.
import subprocess
# Import URL quoting so Markdown links remain valid for any repository path.
import urllib.parse

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Identify the universal root documentation page retained under its compatibility filename.
ROOT_INDEX_PATH = ROOT / "CODEX_START_HERE.md"
# Mark the exact start of the generated Markdown catalog.
INDEX_START = "<!-- BEGIN GENERATED MARKDOWN INDEX -->"
# Mark the exact end of the generated Markdown catalog.
INDEX_END = "<!-- END GENERATED MARKDOWN INDEX -->"
# Name the root index relative to the repository so it is excluded from its own catalog.
ROOT_INDEX_RELATIVE = "CODEX_START_HERE.md"
# Provide readable deterministic headings for each repository path group.
GROUP_LABELS = {
    "root": "Repository root",  # Group current entry points and release summaries.
    ".github": "GitHub contribution templates",  # Group issue and pull-request templates.
    "casino": "Casino modules and scoped instructions",  # Group backend module guidance and evidence.
    "codex": "Agent prompts, task packets, and historical handbacks",  # Group durable agent coordination records.
    "contracts": "Contract-scoped instructions",  # Group API-contract ownership guidance.
    "docs": "Policies, guides, game documentation, evidence, and release history",  # Group the documentation module.
    "mobile": "Mobile integration documentation",  # Group mobile-shell integration guidance.
    "tests": "Test-scoped instructions",  # Group testing ownership guidance.
    "web": "Web-scoped instructions",  # Group browser-shell ownership guidance.
}
# Keep repository-root entry points before path groups, then order every remaining group by path.
GROUP_ORDER = ["root", ".github", "casino", "codex", "contracts", "docs", "mobile", "tests", "web"]

# Define the render_markdown function used by this module.
def render_markdown():
    # Set req to the value needed for the next operation.
    req = json.loads((ROOT / "docs" / "requirements" / "requirements.json").read_text(encoding="utf-8"))
    # Set modules to the value needed for the next operation.
    modules = json.loads((ROOT / "modules" / "module-manifest.json").read_text(encoding="utf-8"))
    # Start the generated document with explicit packaged-release and provenance labels.
    lines = ["# Virtual Casino Requirements and Validation", "", f"Packaged application release: {modules['application']}", "", f"Historical source baseline: {modules['source_baseline']}", "", "## Independent module revisions", ""]
    for name, version in modules.get("modules", {}).items():
        lines.append(f"- {name}: {version}")
    # Set lines + to the value needed for the next operation.
    lines += ["", "## Requirements", ""]
    for requirement in req.get("requirements", []):
        lines.append(f"- **{requirement['id']}** ({requirement.get('module','')}) - {requirement.get('status','')}: {requirement.get('description','')}")
    return "\n".join(lines) + "\n"

# Return every repository Markdown path Git considers tracked or ready to add. (DOC-017, TOOL-006)
def markdown_paths():
    # Ask Git for the canonical tracked plus non-ignored untracked Markdown inventory.
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8")
    # Normalize separators and remove empty output lines before de-duplication.
    discovered = {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}
    # Exclude the root index so it never links to itself.
    discovered.discard(ROOT_INDEX_RELATIVE)
    # Return one deterministic path list for generation and validation.
    return sorted(discovered, key=lambda value: value.casefold())

# Read the first level-one heading so every catalog entry includes useful detail. (DOC-017)
def markdown_title(relative_path: str) -> str:
    # Resolve the repository-relative path without accepting an external location.
    path = ROOT / pathlib.PurePosixPath(relative_path)
    # Fail closed when Git names a path that is not present in this checkout.
    if not path.is_file():
        # Raise a precise path-only error without reading unrelated content.
        raise FileNotFoundError(f"Markdown catalog path is missing: {relative_path}")
    # Iterate through UTF-8 text while tolerating a leading byte-order mark.
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        # Accept only a level-one heading as the file's catalog title.
        if line.startswith("# "):
            # Strip surrounding whitespace while preserving the authored heading text.
            return line[2:].strip()
    # Give heading-less templates an explicit description instead of an empty catalog entry.
    return "No level-one heading; inspect the file directly"

# Convert one path into its deterministic top-level catalog group.
def markdown_group(relative_path: str) -> str:
    # Split the Git-normalized path into portable components.
    parts = pathlib.PurePosixPath(relative_path).parts
    # Place root files together when no directory component exists.
    if len(parts) == 1:
        # Return the reserved root group identifier.
        return "root"
    # Return the top-level directory for every nested file.
    return parts[0]

# Escape a heading so authored brackets cannot break the Markdown link label.
def markdown_label(value: str) -> str:
    # Escape opening and closing brackets used by Markdown link syntax.
    return value.replace("[", "\\[").replace("]", "\\]")

# Render the complete deterministic catalog body. (DOC-017, TOOL-006)
def render_markdown_catalog() -> str:
    # Allocate one path collection per discovered top-level group.
    grouped = {}
    # Classify every Markdown path exactly once.
    for relative_path in markdown_paths():
        # Add the path to its deterministic top-level group.
        grouped.setdefault(markdown_group(relative_path), []).append(relative_path)
    # Start with an authority note inside the generated boundary.
    lines = ["## Complete Markdown catalog", "", "Generated from Git's tracked and non-ignored Markdown inventory. Every repository Markdown file except this root index appears exactly once below.", ""]
    # List known groups first and append any future top-level groups alphabetically.
    ordered_groups = [group for group in GROUP_ORDER if group in grouped] + sorted((group for group in grouped if group not in GROUP_ORDER), key=str.casefold)
    # Render one section for each populated repository group.
    for group in ordered_groups:
        # Use the curated group name or a deterministic fallback for future directories.
        group_title = GROUP_LABELS.get(group, f"{group} documentation")
        # Add the group heading before its exact paths.
        lines.extend([f"### {group_title}", ""])
        # Render group paths alphabetically so diffs remain stable.
        for relative_path in sorted(grouped[group], key=str.casefold):
            # URL-encode only characters unsafe in a relative Markdown destination.
            destination = urllib.parse.quote(relative_path, safe="/._-")
            # Read and escape the authored first heading as the useful description.
            title = markdown_label(markdown_title(relative_path))
            # Add the exact path link and the file's own title.
            lines.append(f"- [`{relative_path}`]({destination}) — {title}")
        # Separate adjacent catalog groups with one blank line.
        lines.append("")
    # Return one newline-terminated generated body.
    return "\n".join(lines).rstrip() + "\n"

# Replace only the generated catalog while preserving the authored root guidance. (TOOL-006)
def render_root_index() -> str:
    # Read the authored root page without normalizing unrelated content.
    current = ROOT_INDEX_PATH.read_text(encoding="utf-8")
    # Require exactly one start marker so generation cannot overwrite an ambiguous document.
    if current.count(INDEX_START) != 1:
        # Raise a precise structural error for the maintainer.
        raise RuntimeError(f"{ROOT_INDEX_RELATIVE} must contain exactly one {INDEX_START} marker")
    # Require exactly one end marker so stale duplicate catalogs fail closed.
    if current.count(INDEX_END) != 1:
        # Raise a precise structural error for the maintainer.
        raise RuntimeError(f"{ROOT_INDEX_RELATIVE} must contain exactly one {INDEX_END} marker")
    # Split authored content at the unique start marker.
    before, remainder = current.split(INDEX_START, 1)
    # Split authored trailing content at the unique end marker.
    _old_catalog, after = remainder.split(INDEX_END, 1)
    # Insert the exact generated catalog between stable markers.
    return before + INDEX_START + "\n" + render_markdown_catalog() + INDEX_END + after

# Define the main function used by this module.
def main():
    # Set parser to the value needed for the next operation.
    parser = argparse.ArgumentParser()
    # Set parser.add_argument("--check", action to the value needed for the next operation.
    parser.add_argument("--check", action="store_true")
    # Set args to the value needed for the next operation.
    args = parser.parse_args()
    # Set out to the value needed for the next operation.
    out = ROOT / "docs" / "requirements" / "requirements_generated.md"
    # Set text to the value needed for the next operation.
    text = render_markdown()
    # Render the root Markdown index from the complete current inventory.
    root_index_text = render_root_index()
    # Branch when validation mode should compare without mutating generated artifacts.
    if args.check:
        # Collect every generated artifact that is absent or differs from canonical inputs.
        stale = []
        # Fail when the generated requirements document is absent or differs.
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            # Record the repository-relative requirements artifact.
            stale.append(out.relative_to(ROOT).as_posix())
        # Fail when the root Markdown catalog differs from the complete inventory.
        if ROOT_INDEX_PATH.read_text(encoding="utf-8") != root_index_text:
            # Record the repository-relative root index artifact.
            stale.append(ROOT_INDEX_RELATIVE)
        # Report every stale artifact in one deterministic failure.
        if stale:
            # Write diagnostic output so the current operation can be inspected.
            print(f"Generated docs are out of date: {', '.join(stale)}; run python scripts/generate_docs.py")
            return 1
        # Report a successful non-mutating generated-document comparison.
        print(f"Generated docs are current: {out.relative_to(ROOT).as_posix()}, {ROOT_INDEX_RELATIVE}")
        # Return without rewriting checked artifacts or normalizing line endings.
        return 0
    # Set out.write_text(text, encoding to the value needed for the next operation.
    out.write_text(text, encoding="utf-8")
    # Write the complete generated catalog into the authored root page.
    ROOT_INDEX_PATH.write_text(root_index_text, encoding="utf-8")
    # Write diagnostic output so the current operation can be inspected.
    print(f"Wrote {out.relative_to(ROOT).as_posix()} and {ROOT_INDEX_RELATIVE}")
    return 0

if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
