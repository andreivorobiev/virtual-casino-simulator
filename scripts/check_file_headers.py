# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Enforce and safely add governed first-party source headers without behavior changes."""

# Import argument parsing so the checker exposes explicit read-only and bounded-write modes.
import argparse
# Import AST support so Python purpose markers and semantic package markers are recognized conservatively.
import ast
# Import codecs so an existing UTF-8 byte-order mark can be preserved exactly.
import codecs
# Import in-memory byte streams so Python's declared source encoding can be detected safely.
import io
# Import JSON support so the monotonic filler baseline has a small auditable format.
import json
# Import path handling so every selected write can be proven to remain inside the repository.
from pathlib import Path
# Import regular expressions for encoding cookies, newline validation, and conservative comment recognition.
import re
# Import subprocess support so Git, rather than a filesystem walk, defines the tracked source inventory.
import subprocess
# Import tokenization so Python comments and executable tokens can be compared without executing source.
import tokenize
# Import immutable result containers so callers can inspect findings without parsing console output.
from typing import NamedTuple


# Resolve the default repository root from this script rather than from the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Require the exact license identifier selected for first-party source files.
SPDX_LINE = "SPDX-License-Identifier: Apache-2.0"
# Require NOTICE to remain the authoritative source for the fixed copyright year and holder text.
COPYRIGHT_PATTERN = re.compile(r"^Copyright 2026 .+$")
# Exclude vendored third-party sources whose upstream license notices must remain authoritative.
EXCLUDED_SOURCE_PREFIXES = ("web/vendor/",)
# Recognize a legal Python encoding cookie only in the first or second physical source line.
PYTHON_ENCODING_COOKIE = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)")
# Recognize all physical newline encodings so mixed-newline files fail closed.
NEWLINE_PATTERN = re.compile(r"\r\n|\r|\n")
# Recognize JavaScript line comments while avoiding assumptions about executable syntax.
JAVASCRIPT_LINE_COMMENT = re.compile(r"^\s*//(.*)$")
# Recognize the beginning of a JavaScript block comment used as a leading purpose marker.
JAVASCRIPT_BLOCK_START = re.compile(r"^\s*/\*(.*)$")
# Define the exact generated filler texts approved for monotonic measurement and later batched removal.
FILLER_TEXTS = frozenset(
    {
        # Track the repository-wide banner that does not explain the file's purpose.
        "AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.",
        # Track the import filler phrase without matching useful human-written import rationale.
        "Import required dependency so this module can use its public functions or constants.",
        # Track the generic execution filler phrase exactly.
        "Execute this statement as part of the module's documented control flow.",
        # Track the generic return filler phrase exactly.
        "Return the computed value to the caller.",
        # Track the generic branching filler phrase exactly.
        "Branch when the following condition is true.",
        # Track the generic iteration filler phrase exactly.
        "Iterate through the collection to process each item.",
        # Track the generic catch-all filler phrase exactly.
        "Explain this executable/data line so future Codex changes preserve intent.",
    }
)
# Match the two generated tautology families whose substituted names made exact-text matching ineffective.
FILLER_FAMILY_PATTERNS = (
    # Match assignment narration while requiring the generator's complete fixed suffix.
    re.compile(r"^Set .+ to the value needed for the next operation\.$"),
    # Match function narration while requiring the generator's complete fixed suffix.
    re.compile(r"^Define the .+ function used by this module\.$"),
)
# Keep the repository's active debt ledger discoverable by every compatibility entry point.
DEFAULT_FILLER_BASELINE = Path("scripts/comment_filler_baseline.json")


# Define the fixed exception type used for all fail-closed policy and source-safety errors.
class HeaderPolicyError(ValueError):
    """Report a source state that the checker cannot safely interpret or rewrite."""


# Store one path-specific policy failure in a stable machine-testable representation.
class PolicyFinding(NamedTuple):
    """Describe one selected file that does not satisfy the source-header policy."""

    # Preserve the repository-relative path for concise operator output.
    path: str
    # Preserve an actionable reason without including source contents or secrets.
    message: str


# Return the complete policy run outcome without mutating it after validation.
class PolicyRun(NamedTuple):
    """Summarize a check or bounded write operation."""

    # Count files whose bytes were changed only after the whole selected set passed.
    changed: int
    # Return every deterministic policy finding in repository path order.
    findings: tuple[PolicyFinding, ...]


# Preserve decoded source metadata needed to reproduce the original byte-level format.
class SourceDocument(NamedTuple):
    """Hold decoded source plus its exact encoding envelope."""

    # Store source text without a UTF-8 byte-order mark.
    text: str
    # Store the codec selected by Python tokenization or the strict JavaScript rule.
    encoding: str
    # Store the original UTF-8 byte-order mark separately for exact preservation.
    bom: bytes
    # Store the one newline style used by the file.
    newline: str


# Load the one authoritative copyright line from NOTICE and reject ambiguous policy input.
def notice_copyright(root: Path) -> str:
    """Return NOTICE's exact fixed-2026 copyright line."""

    # Resolve NOTICE within the explicit repository root supplied by the caller.
    notice_path = root / "NOTICE"
    # Fail closed when the authoritative notice is absent.
    if not notice_path.is_file():
        # Raise a stable operator-facing error rather than guessing copyright ownership.
        raise HeaderPolicyError("NOTICE is missing")
    # Decode NOTICE strictly as UTF-8 because repository policy files use UTF-8.
    notice_text = notice_path.read_text(encoding="utf-8")
    # Select only literal copyright lines so prose cannot accidentally become a source header.
    copyright_lines = [line.strip() for line in notice_text.splitlines() if line.startswith("Copyright ")]
    # Require one unambiguous copyright declaration.
    if len(copyright_lines) != 1:
        # Raise before inspecting or changing any selected source.
        raise HeaderPolicyError("NOTICE must contain exactly one Copyright line")
    # Read the one exact candidate after cardinality validation.
    copyright_line = copyright_lines[0]
    # Enforce the owner-approved fixed year instead of silently adopting a changing year.
    if not COPYRIGHT_PATTERN.fullmatch(copyright_line):
        # Explain the durable fixed-year convention without rewriting NOTICE.
        raise HeaderPolicyError("NOTICE copyright must use the fixed 2026 convention")
    # Return the exact holder text so source headers never duplicate ownership configuration.
    return copyright_line


# Normalize a requested boundary and prove that it cannot escape the repository root.
def _normalize_boundary(root: Path, requested: str) -> str:
    """Return a repository-relative POSIX boundary or fail closed."""

    # Interpret relative boundaries from the repository root and allow explicit in-root absolute paths.
    candidate = Path(requested)
    # Join relative requests to the explicit root before canonical containment checks.
    absolute = candidate if candidate.is_absolute() else root / candidate
    # Resolve existing parents and traversal components before comparing containment.
    resolved = absolute.resolve()
    # Resolve the root once so case-normalized Windows paths compare correctly.
    resolved_root = root.resolve()
    # Reject the root itself as an unbounded write target.
    if resolved == resolved_root:
        # Require the caller to name at least one narrower path for write mode.
        raise HeaderPolicyError("a write boundary must be narrower than the repository root")
    # Convert the canonical candidate back to a repository-relative path.
    try:
        # Use relative_to so drive changes and parent traversal fail rather than being normalized away.
        relative = resolved.relative_to(resolved_root)
    # Convert platform containment failures into one stable policy error.
    except ValueError as error:
        # Chain the original path error for debugging without continuing unsafely.
        raise HeaderPolicyError(f"path boundary escapes the repository: {requested}") from error
    # Return POSIX separators because Git inventories always use forward slashes.
    return relative.as_posix().rstrip("/")


# Ask Git for the tracked Python and JavaScript inventory, then apply optional path boundaries.
def tracked_source_paths(root: Path, boundaries: tuple[str, ...] = ()) -> tuple[Path, ...]:
    """Enumerate only Git-tracked first-party Python and JavaScript paths."""

    # Normalize every caller-supplied boundary before asking Git for inventory data.
    normalized_boundaries = tuple(_normalize_boundary(root, item) for item in boundaries)
    # Run Git without a shell so wildcard text and repository paths cannot become shell syntax.
    result = subprocess.run(
        # Ask Git for a NUL-delimited inventory to preserve unusual but valid tracked filenames.
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.py", "*.js"],
        # Capture inventory bytes for explicit UTF-8 decoding and NUL splitting.
        stdout=subprocess.PIPE,
        # Capture diagnostics so failures can be summarized without leaking arbitrary source content.
        stderr=subprocess.PIPE,
        # Do not let subprocess raise a less-specific exception before policy context is added.
        check=False,
    )
    # Fail closed when the supplied root is not a readable Git worktree.
    if result.returncode != 0:
        # Decode the short Git diagnostic defensively for operator action.
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        # Raise without falling back to a filesystem walk that could include secrets or generated files.
        raise HeaderPolicyError(f"Git tracked-file enumeration failed: {diagnostic}")
    # Decode Git's path format strictly because repository paths are UTF-8.
    inventory = result.stdout.decode("utf-8").split("\0")
    # Accumulate canonical selected paths only after every safety check passes.
    selected: list[Path] = []
    # Inspect inventory entries in Git's deterministic output order.
    for relative_text in inventory:
        # Ignore the empty segment after the final NUL delimiter.
        if not relative_text:
            # Continue without creating a root path entry.
            continue
        # Normalize Git separators for consistent boundary matching on Windows.
        relative_posix = relative_text.replace("\\", "/")
        # Leave third-party vendored source under its upstream ownership and license terms.
        if any(relative_posix.startswith(prefix) for prefix in EXCLUDED_SOURCE_PREFIXES):
            # Skip vendored bytes before any first-party header or purpose checks.
            continue
        # Reject absolute or parent-traversing inventory entries even though Git normally forbids them.
        if relative_posix.startswith("/") or ".." in Path(relative_posix).parts:
            # Treat unexpected Git metadata as unsafe rather than trying to repair it.
            raise HeaderPolicyError(f"unsafe tracked path: {relative_text}")
        # Keep only the two owner-approved first-party source suffixes.
        if Path(relative_posix).suffix not in {".py", ".js"}:
            # Ignore any pathspec edge case outside the approved source types.
            continue
        # Retain a path when no boundary was supplied or it lies at/below an explicit boundary.
        if normalized_boundaries and not any(  # Apply explicit path boundaries only after normalization.
            relative_posix == boundary or relative_posix.startswith(f"{boundary}/")  # Match a file or descendant.
            for boundary in normalized_boundaries  # Inspect every caller-approved boundary.
        ):  # Reject the tracked path when no approved boundary contains it.
            # Skip tracked sources outside the bounded request.
            continue
        # Resolve the selected file for containment, existence, and symlink checks.
        absolute_path = (root / Path(relative_posix)).resolve()
        # Prove that canonical resolution still remains below the repository root.
        try:
            # Convert to a relative path solely as a containment assertion.
            absolute_path.relative_to(root.resolve())
        # Reject symlink traversal or unexpected drive changes.
        except ValueError as error:
            # Preserve the unsafe Git path in a concise error.
            raise HeaderPolicyError(f"tracked path escapes the repository: {relative_text}") from error
        # Reject symlinks because a bounded write must not redirect outside its named file.
        if (root / Path(relative_posix)).is_symlink():
            # Do not follow or rewrite tracked symlink targets.
            raise HeaderPolicyError(f"tracked source is a symlink: {relative_posix}")
        # Require every tracked inventory entry to be an existing regular file.
        if not absolute_path.is_file():
            # Fail before any write so partially checked inventories cannot be changed.
            raise HeaderPolicyError(f"tracked source is missing: {relative_posix}")
        # Append the safe canonical source path.
        selected.append(absolute_path)
    # Sort by repository-relative POSIX path for stable findings and writes.
    return tuple(sorted(selected, key=lambda item: item.relative_to(root.resolve()).as_posix()))


# Decode one source file while retaining byte-order mark, codec, and newline style.
def decode_source(raw: bytes, suffix: str) -> SourceDocument:
    """Decode supported source bytes or fail closed without replacement characters."""

    # Detect and detach an existing UTF-8 byte-order mark for exact re-encoding.
    bom = codecs.BOM_UTF8 if raw.startswith(codecs.BOM_UTF8) else b""
    # Remove only the recognized UTF-8 marker before codec-specific decoding.
    payload = raw[len(bom) :]
    # Use Python's tokenizer to honor a valid first/second-line encoding cookie.
    if suffix == ".py":
        # Ask tokenize to reconcile a byte-order mark with any declared source encoding.
        try:
            # Detect from the original bytes so incompatible BOM/cookie combinations are rejected.
            detected_encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
        # Convert encoding-cookie errors into the policy's stable fail-closed exception.
        except (SyntaxError, LookupError) as error:
            # Preserve the cause for developers while avoiding a lossy fallback decode.
            raise HeaderPolicyError(f"invalid Python source encoding: {error}") from error
        # Normalize UTF-8-with-BOM to a payload codec because the marker is stored separately.
        encoding = "utf-8" if detected_encoding.lower().replace("_", "-") == "utf-8-sig" else detected_encoding
    # Require JavaScript to use strict UTF-8 with an optional preserved marker.
    elif suffix == ".js":
        # Fix the JavaScript codec so browser and tool behavior stays deterministic.
        encoding = "utf-8"
    # Reject accidental use on other source types.
    else:
        # Keep the checker narrowly scoped to the owner-approved inventory.
        raise HeaderPolicyError(f"unsupported source suffix: {suffix}")
    # Decode without replacement so malformed bytes never get normalized by a write.
    try:
        # Convert the BOM-free payload using the detected or required codec.
        text = payload.decode(encoding, errors="strict")
    # Convert codec lookup and byte errors into one stable safety failure.
    except (LookupError, UnicodeDecodeError) as error:
        # Preserve exact original bytes by raising before staging a candidate.
        raise HeaderPolicyError(f"source cannot be decoded safely: {error}") from error
    # Collect every physical newline representation present in the decoded file.
    newline_styles = set(NEWLINE_PATTERN.findall(text))
    # Reject mixed styles because insertion must never normalize existing line endings.
    if len(newline_styles) > 1:
        # Fail before building or writing a candidate.
        raise HeaderPolicyError("mixed newline styles are not safe to rewrite")
    # Preserve the existing style or use LF for a source file that has no physical newline yet.
    newline = next(iter(newline_styles), "\n")
    # Return all data needed for byte-identical encoding outside inserted header bytes.
    return SourceDocument(text=text, encoding=encoding, bom=bom, newline=newline)


# Re-encode a decoded source document with its original codec and byte-order mark.
def encode_source(document: SourceDocument, text: str) -> bytes:
    """Encode source text without changing its original encoding envelope."""

    # Encode strictly so a newly inserted ASCII header cannot hide unrelated codec problems.
    try:
        # Convert text using the source's detected codec.
        payload = text.encode(document.encoding, errors="strict")
    # Convert codec errors into a no-write policy failure.
    except (LookupError, UnicodeEncodeError) as error:
        # Preserve the original source by raising before repository mutation.
        raise HeaderPolicyError(f"source cannot be re-encoded safely: {error}") from error
    # Restore the exact original UTF-8 marker, if present.
    return document.bom + payload


# Return the physical insertion line after any Python shebang and legal encoding cookie.
def _python_insertion_index(lines: list[str]) -> int:
    """Find the safe Python header insertion point."""

    # Reject a displaced interpreter shebang because bounded writing must preserve line-one semantics.
    if any(line.startswith("#!") for line in lines[1:]):
        # Refuse to normalize or move a pre-existing invalid preamble.
        raise HeaderPolicyError("Python shebang must remain on physical line one")
    # Start before the first physical line.
    index = 0
    # Preserve an interpreter shebang as physical line one.
    if lines and lines[0].startswith("#!"):
        # Insert after the shebang unless an encoding cookie also follows.
        index = 1
    # Inspect only the first two physical lines permitted by Python's encoding declaration rules.
    for position, line in enumerate(lines[:2]):
        # Advance past a recognized encoding cookie while leaving all bytes otherwise unchanged.
        if PYTHON_ENCODING_COOKIE.match(line):
            # Keep insertion after the last legal preamble line.
            index = max(index, position + 1)
    # Return the zero-based insertion index.
    return index


# Return the physical insertion line after an optional JavaScript shebang.
def _javascript_insertion_index(lines: list[str]) -> int:
    """Find the safe JavaScript header insertion point."""

    # Reject a displaced runtime shebang because Node recognizes it only at physical line one.
    if any(line.startswith("#!") for line in lines[1:]):
        # Refuse to normalize or move the invalid preamble.
        raise HeaderPolicyError("JavaScript shebang must remain on physical line one")
    # Preserve a Node-style shebang as physical line one.
    return 1 if lines and lines[0].startswith("#!") else 0


# Normalize a source comment to its semantic text for exact header and filler comparisons.
def _comment_text(line: str) -> str:
    """Strip one comment delimiter without altering inner text."""

    # Remove surrounding whitespace before recognizing language comment delimiters.
    stripped = line.strip()
    # Normalize Python and JavaScript line comments.
    if stripped.startswith("#"):
        # Remove one leading Python/shebang marker and adjacent whitespace.
        return stripped[1:].strip()
    # Normalize JavaScript line comments.
    if stripped.startswith("//"):
        # Remove exactly the two slash delimiters and adjacent whitespace.
        return stripped[2:].strip()
    # Normalize a one-line block-comment opening delimiter.
    if stripped.startswith("/*"):
        # Remove the opening marker before optional closing-marker cleanup.
        stripped = stripped[2:].strip()
    # Normalize a block-comment continuation marker.
    if stripped.startswith("*"):
        # Remove one decorative continuation marker.
        stripped = stripped[1:].strip()
    # Normalize a one-line block-comment closing delimiter.
    if stripped.endswith("*/"):
        # Remove the closing marker and adjacent whitespace.
        stripped = stripped[:-2].strip()
    # Return the remaining exact semantic comment text.
    return stripped


# Build the exact two header lines for the selected source language.
def _header_lines(suffix: str, copyright_line: str, newline: str) -> tuple[str, str]:
    """Return exact copyright and SPDX physical lines."""

    # Select the language-appropriate line-comment prefix.
    prefix = "# " if suffix == ".py" else "// "
    # Return lines with the source's existing newline encoding.
    return (
        # Place the NOTICE-derived copyright first.
        f"{prefix}{copyright_line}{newline}",
        # Place the fixed Apache-2.0 identifier second.
        f"{prefix}{SPDX_LINE}{newline}",
    )


# Validate header state and return whether the exact header is already present.
def _has_exact_header(
    lines: list[str],  # Receive physical source lines with newline endings retained.
    insertion_index: int,  # Receive the one language-valid insertion position.
    copyright_line: str,  # Receive the exact NOTICE-derived attribution.
    suffix: str,  # Receive the language suffix for exact physical comment syntax.
) -> bool:  # Return whether the exact complete header is already present.
    """Accept one exact header position and reject partial or conflicting markers."""

    # Record every physical line containing either governed marker.
    governed_positions = [
        # Retain the line index alongside normalized text for exact placement validation.
        (position, _comment_text(line))
        # Enumerate every physical source line.
        for position, line in enumerate(lines)
        # Select governed text only from line comments so string literals never become false headers.
        if line.lstrip().startswith(("#", "//", "/*", "*"))  # Restrict marker detection to comments.
        and (  # Require either governed marker text after confirming comment syntax.
            _comment_text(line).startswith("Copyright ")  # Detect a copyright marker, not prose naming one.
            or _comment_text(line).startswith("SPDX-License-Identifier:")  # Detect an SPDX marker prefix.
        )
    ]
    # Define the only accepted exact governed marker sequence.
    expected = [
        # Require NOTICE text exactly at the insertion point.
        (insertion_index, copyright_line),
        # Require Apache-2.0 text exactly on the following physical line.
        (insertion_index + 1, SPDX_LINE),
    ]
    # Accept a file containing no governed markers so bounded write mode may add them.
    if not governed_positions:
        # Signal that insertion remains necessary.
        return False
    # Reject partial, duplicate, misplaced, or conflicting markers.
    if governed_positions != expected:
        # Avoid guessing whether a human-authored or third-party header may be replaced.
        raise HeaderPolicyError("partial, conflicting, duplicate, or misplaced file header")
    # Select the exact language comment prefix rather than accepting whitespace variants.
    prefix = "# " if suffix == ".py" else "// "
    # Build the only accepted physical header text without its newline terminator.
    exact_physical_lines = (
        # Require exact spacing and NOTICE content on the first governed line.
        f"{prefix}{copyright_line}",
        # Require exact spacing and SPDX content on the second governed line.
        f"{prefix}{SPDX_LINE}",
    )
    # Remove only the physical newline terminator before exact header comparison.
    actual_physical_lines = (
        # Read the exact first governed line.
        lines[insertion_index].rstrip("\r\n"),
        # Read the exact second governed line.
        lines[insertion_index + 1].rstrip("\r\n"),
    )
    # Reject semantically similar but noncanonical spacing or delimiter forms.
    if actual_physical_lines != exact_physical_lines:
        # Keep write mode from silently normalizing a human-authored license block.
        raise HeaderPolicyError("file header markers exist but physical header text is not exact")
    # Confirm that the exact two-line header is already present.
    return True


# Produce a Python token fingerprint that omits comments and non-semantic blank-line tokens.
def python_executable_fingerprint(text: str) -> tuple[tuple[int, str], ...]:
    """Return Python executable tokens for before/after equivalence checks."""

    # Parse the module first so malformed Python never reaches a write candidate.
    try:
        # Compile only to an AST so source is never executed.
        ast.parse(text)
    # Convert syntax failures into a stable policy error.
    except SyntaxError as error:
        # Include location but not arbitrary source content in the diagnostic.
        raise HeaderPolicyError(f"invalid Python syntax at line {error.lineno}") from error
    # Tokenize UTF-8 text because decoding already reconciled the declared source encoding.
    try:
        # Generate tokens from normalized in-memory text.
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        # Exclude comments, encoding markers, and non-semantic blank-line tokens.
        return tuple(
            # Preserve token type and spelling while intentionally ignoring physical line positions.
            (token.type, token.string)
            # Consume the tokenizer exactly once.
            for token in tokens
            # Remove only tokens that header insertion is expected to add or reposition.
            if token.type not in {tokenize.COMMENT, tokenize.NL, tokenize.ENCODING}
        )
    # Convert token stream failures into a no-write safety error.
    except (tokenize.TokenError, IndentationError) as error:
        # Preserve the parser failure as context.
        raise HeaderPolicyError(f"invalid Python token stream: {error}") from error


# Determine whether an __init__.py file is a license-only semantic package marker.
def is_semantic_marker_init(path: Path, text: str) -> bool:
    """Return true for an __init__.py with no executable body beyond a docstring."""

    # Active modules outside package markers always require an explicit purpose marker.
    if path.name != "__init__.py":
        # Decline the marker exemption.
        return False
    # Parse through the shared fingerprint validator so malformed syntax fails identically.
    python_executable_fingerprint(text)
    # Build the AST solely for body-shape inspection.
    module = ast.parse(text)
    # Treat a completely empty package marker as semantic and license-only.
    if not module.body:
        # Grant the owner-approved marker exemption.
        return True
    # Treat one module docstring and no other statement as a semantic marker.
    if len(module.body) == 1 and isinstance(module.body[0], ast.Expr):
        # Read the expression value without evaluating it.
        value = module.body[0].value
        # Accept only a literal string expression.
        return isinstance(value, ast.Constant) and isinstance(value.value, str)
    # Require purpose documentation for any active package initialization.
    return False


# Decide whether normalized comment text belongs to any governed filler template.
def _is_filler_text(text: str) -> bool:
    """Return true for exact filler phrases or complete generated tautology families."""

    # Normalize decorative comment whitespace before comparing policy templates.
    candidate = text.strip()
    # Preserve the original exact-template coverage.
    if candidate in FILLER_TEXTS:
        # Report an exact governed filler phrase.
        return True
    # Match only complete family templates so useful comments sharing one word remain valid.
    return any(pattern.fullmatch(candidate) is not None for pattern in FILLER_FAMILY_PATTERNS)


# Decide whether text is a substantive purpose comment rather than license or governed filler.
def _is_substantive_comment(text: str, copyright_line: str) -> bool:
    """Return true only for nonempty human-purpose comment text."""

    # Normalize decorative whitespace before exact policy comparisons.
    candidate = text.strip()
    # Reject empty comment shells.
    if not candidate:
        # Empty comments cannot explain file purpose.
        return False
    # Reject both governed license lines.
    if candidate in {copyright_line, SPDX_LINE}:
        # License attribution is not file-purpose documentation.
        return False
    # Reject governed filler phrases and complete generated families without fuzzy similarity.
    if _is_filler_text(candidate):
        # Generated filler cannot satisfy the purpose requirement.
        return False
    # Accept any other explicit leading comment as human-authored purpose documentation.
    return True


# Detect a Python module docstring or leading substantive comment.
def _python_has_purpose(path: Path, text: str, copyright_line: str) -> bool:
    """Return whether Python source has an approved purpose marker."""

    # Grant the owner-approved exemption to semantic package marker files.
    if is_semantic_marker_init(path, text):
        # License-only marker packages do not need invented prose.
        return True
    # Parse source after syntax validation for reliable module-docstring detection.
    module = ast.parse(text)
    # Read the standard Python module docstring without executing the module.
    docstring = ast.get_docstring(module, clean=True)
    # Accept a nonempty non-filler module docstring as the strongest purpose marker.
    if docstring and _is_substantive_comment(docstring, copyright_line):
        # Stop after the explicit module-level purpose is established.
        return True
    # Tokenize comments to find substantive documentation before the first executable token.
    tokens = tokenize.generate_tokens(io.StringIO(text).readline)
    # Inspect source tokens in physical order.
    for token in tokens:
        # Evaluate leading comment text while license and filler comments remain excluded.
        if token.type == tokenize.COMMENT:
            # Skip an interpreter shebang because it describes execution, not module purpose.
            if token.string.startswith("#!"):
                # Continue into the actual leading documentation region.
                continue
            # Skip a legal source-encoding cookie because it is transport metadata, not purpose.
            if PYTHON_ENCODING_COOKIE.match(token.string):
                # Continue into the actual leading documentation region.
                continue
            # Accept a substantive leading comment.
            if _is_substantive_comment(_comment_text(token.string), copyright_line):
                # Return before encountering executable code.
                return True
            # Continue past non-purpose shebang, encoding, license, or filler comments.
            continue
        # Ignore whitespace-only token classes before the first statement.
        if token.type in {  # Treat only non-executable structural tokens as skippable.
            tokenize.ENCODING,  # Ignore the tokenizer's synthetic encoding token.
            tokenize.NL,  # Ignore non-terminating physical newlines.
            tokenize.NEWLINE,  # Ignore statement-ending newlines before executable content.
            tokenize.INDENT,  # Ignore indentation structure before the first statement.
            tokenize.DEDENT,  # Ignore matching indentation closure.
            tokenize.ENDMARKER,  # Allow empty modules to reach the no-purpose result.
        }:  # Continue only for the explicitly enumerated structural token types.
            # Continue looking for a leading purpose comment.
            continue
        # Stop when executable or docstring syntax begins because later comments are not file purpose.
        break
    # Report that no accepted Python purpose marker exists.
    return False


# Detect a conservative leading JavaScript line or block purpose comment.
def _javascript_has_purpose(text: str, copyright_line: str) -> bool:
    """Return whether JavaScript starts with a substantive purpose comment."""

    # Split without discarding content because only logical leading-comment order matters here.
    lines = text.splitlines()
    # Skip an optional JavaScript runtime shebang.
    index = 1 if lines and lines[0].startswith("#!") else 0
    # Inspect only the leading blank/comment region before executable text.
    while index < len(lines):
        # Read the current physical line.
        line = lines[index]
        # Skip blank separators around a header or purpose block.
        if not line.strip():
            # Advance to the next leading line.
            index += 1
            # Continue without treating whitespace as executable.
            continue
        # Recognize a JavaScript line comment conservatively.
        line_match = JAVASCRIPT_LINE_COMMENT.match(line)
        # Inspect the normalized line-comment content.
        if line_match:
            # Accept the first substantive leading comment.
            if _is_substantive_comment(line_match.group(1).strip(), copyright_line):
                # Return before executable JavaScript begins.
                return True
            # Continue through license or exact filler line comments.
            index += 1
            # Inspect the next leading line.
            continue
        # Recognize the opening of a JavaScript block comment.
        block_match = JAVASCRIPT_BLOCK_START.match(line)
        # Parse only a syntactically closed leading block.
        if block_match:
            # Accumulate comment content without attempting to parse JavaScript expressions.
            parts: list[str] = []
            # Track whether the block closes before executable text.
            closed = False
            # Consume physical lines until the first closing delimiter.
            while index < len(lines):
                # Normalize block decorations into semantic comment text.
                part = _comment_text(lines[index])
                # Retain nonempty text for substantive-purpose evaluation.
                if part:
                    # Add one semantic block line.
                    parts.append(part)
                # Detect closure in the original physical line.
                if "*/" in lines[index]:
                    # Mark the leading block as safely closed.
                    closed = True
                    # Advance beyond the block before continuing the outer scan.
                    index += 1
                    # Stop consuming this comment.
                    break
                # Advance within the block.
                index += 1
            # Reject an unterminated leading block rather than interpreting executable content.
            if not closed:
                # Fail closed so write mode preserves the original bytes.
                raise HeaderPolicyError("unterminated leading JavaScript block comment")
            # Accept when any block line provides substantive purpose text.
            if any(_is_substantive_comment(part, copyright_line) for part in parts):
                # Return the recognized purpose marker.
                return True
            # Continue past a license-only or filler-only block.
            continue
        # Stop at the first executable JavaScript line.
        break
    # Report that no accepted JavaScript purpose marker exists.
    return False


# Extract governed filler comment counts without heuristic deletion or rewriting.
def filler_count(text: str, suffix: str) -> int:
    """Count owner-approved exact filler texts and complete generated families."""

    # Count Python comment tokens so strings containing filler phrases never match.
    if suffix == ".py":
        # Validate syntax and tokenization before counting comments.
        python_executable_fingerprint(text)
        # Generate the source token stream once for exact comment inspection.
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        # Return the number of governed normalized filler comments.
        return sum(
            # Add one for each governed filler match.
            1
            # Inspect every token.
            for token in tokens
            # Restrict matching to actual Python comment tokens.
            if token.type == tokenize.COMMENT and _is_filler_text(_comment_text(token.string))
        )
    # Count JavaScript physical comment lines conservatively without parsing strings.
    if suffix == ".js":
        # Initialize the exact-match count.
        count = 0
        # Inspect each physical line independently so no executable text is modified or inferred.
        for line in text.splitlines():
            # Normalize only lines that visibly begin as line/block comments.
            stripped = line.lstrip()
            # Skip executable lines even if they contain comment delimiters later.
            if not stripped.startswith(("//", "/*", "*")):
                # Continue without matching string or trailing-comment content.
                continue
            # Count only a full normalized governed filler match.
            if _is_filler_text(_comment_text(line)):
                # Increment the exact-match count.
                count += 1
        # Return the conservative JavaScript count.
        return count
    # Reject accidental calls for unsupported source types.
    raise HeaderPolicyError(f"unsupported source suffix: {suffix}")


# Add the exact header in memory and prove Python executable-token equivalence.
def apply_header_bytes(path: Path, raw: bytes, copyright_line: str) -> bytes:
    """Return an exact safe header candidate or raise without writing."""

    # Decode with strict preservation metadata.
    document = decode_source(raw, path.suffix)
    # Split physical lines while retaining their exact newline endings.
    lines = document.text.splitlines(keepends=True)
    # Select the language-specific safe insertion index.
    insertion_index = (
        # Preserve Python's shebang and encoding preamble.
        _python_insertion_index(lines)
        # Preserve JavaScript's optional runtime shebang.
        if path.suffix == ".py"
        else _javascript_insertion_index(lines)  # Use the JavaScript preamble rule for JS.
    )
    # Return original bytes when the exact header is already present.
    if _has_exact_header(lines, insertion_index, copyright_line, path.suffix):
        # Preserve byte identity for idempotent write mode.
        return raw
    # Build exact header physical lines using the file's existing newline style.
    header = _header_lines(path.suffix, copyright_line, document.newline)
    # Insert the two governed lines without changing any original line text.
    candidate_lines = lines[:insertion_index] + list(header) + lines[insertion_index:]
    # Join only the staged list so original final-newline state remains unchanged.
    candidate_text = "".join(candidate_lines)
    # Prove Python executable tokens are unchanged after comment insertion.
    if path.suffix == ".py":
        # Compare token type/spelling while ignoring comments and physical blank lines.
        if python_executable_fingerprint(document.text) != python_executable_fingerprint(candidate_text):
            # Reject any candidate whose executable meaning may have changed.
            raise HeaderPolicyError("Python executable-token equivalence check failed")
    # Prove JavaScript transformation consists only of the exact inserted slice.
    else:
        # Reconstruct the original text by removing the known inserted header positions.
        reconstructed = "".join(candidate_lines[:insertion_index] + candidate_lines[insertion_index + 2 :])
        # Reject any candidate that cannot reproduce the original decoded source exactly.
        if reconstructed != document.text:
            # Preserve original bytes when the insertion proof fails.
            raise HeaderPolicyError("JavaScript insertion equivalence check failed")
    # Re-encode using the original codec and byte-order mark.
    return encode_source(document, candidate_text)


# Inspect one candidate for exact header, purpose marker, syntax safety, and filler baseline.
def inspect_source_bytes(
    path: Path,  # Receive the canonical selected source path.
    raw: bytes,  # Receive exact source bytes for strict decoding.
    copyright_line: str,  # Receive the NOTICE-derived attribution.
    expected_filler: int,  # Receive the exact current baseline count.
) -> tuple[str, ...]:  # Return all deterministic policy messages for the file.
    """Return deterministic policy messages for one source file."""

    # Decode the candidate strictly before interpreting structure.
    document = decode_source(raw, path.suffix)
    # Split physical lines while retaining preamble placement.
    lines = document.text.splitlines(keepends=True)
    # Select the one valid header position for this language.
    insertion_index = (
        # Use Python's preamble-aware placement.
        _python_insertion_index(lines)
        # Use JavaScript's shebang-aware placement.
        if path.suffix == ".py"
        else _javascript_insertion_index(lines)  # Use the JavaScript preamble rule for JS.
    )
    # Accumulate independent actionable findings for the same file.
    messages: list[str] = []
    # Check exact header state while allowing HeaderPolicyError to fail closed.
    if not _has_exact_header(lines, insertion_index, copyright_line, path.suffix):
        # Report a missing exact header without silently writing in check mode.
        messages.append("missing exact NOTICE-derived copyright and SPDX header")
    # Validate language syntax and purpose marker conservatively.
    has_purpose = (
        # Use AST/token-aware Python purpose recognition.
        _python_has_purpose(path, document.text, copyright_line)
        # Use leading-comment-only JavaScript purpose recognition.
        if path.suffix == ".py"
        else _javascript_has_purpose(document.text, copyright_line)  # Inspect leading JS comments.
    )
    # Report missing purpose while never inventing purpose prose.
    if not has_purpose:
        # Keep the finding actionable for a human-authored follow-up.
        messages.append("missing substantive file-purpose docstring or leading comment")
    # Count every governed filler comment template or generated family.
    actual_filler = filler_count(document.text, path.suffix)
    # Require exact baseline agreement so increases and stale decreases both need an audited baseline update.
    if actual_filler != expected_filler:
        # Report both values without reproducing source contents.
        messages.append(
            f"governed filler count {actual_filler} does not match baseline {expected_filler}"  # Name debt.
        )
    # Return messages in deterministic policy order.
    return tuple(messages)


# Validate and normalize a filler baseline document.
def load_filler_baseline(path: Path) -> dict[str, int]:
    """Load the version-1 exact filler-count baseline."""

    # Require a regular file so directories and device paths cannot be interpreted as policy JSON.
    if not path.is_file():
        # Reject missing baseline inputs explicitly.
        raise HeaderPolicyError(f"filler baseline is missing: {path}")
    # Parse strict UTF-8 JSON without comments or trailing data.
    try:
        # Read and decode the complete baseline.
        payload = json.loads(path.read_text(encoding="utf-8"))
    # Convert syntax and byte failures into one stable policy error.
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        # Preserve the invalid file untouched.
        raise HeaderPolicyError(f"invalid filler baseline JSON: {error}") from error
    # Require the one versioned top-level schema.
    if not isinstance(payload, dict) or set(payload) != {"version", "files"}:
        # Reject ambiguous future or ad-hoc structures.
        raise HeaderPolicyError("filler baseline must contain only version and files")
    # Require the initial schema version exactly.
    if payload["version"] != 1:
        # Force explicit code review before accepting a new schema.
        raise HeaderPolicyError("unsupported filler baseline version")
    # Read the path-to-count mapping after schema validation.
    files = payload["files"]
    # Require a JSON object for deterministic path lookup.
    if not isinstance(files, dict):
        # Reject lists or scalars that cannot enforce per-file monotonicity.
        raise HeaderPolicyError("filler baseline files must be an object")
    # Accumulate normalized values only after validating every entry.
    normalized: dict[str, int] = {}
    # Inspect each configured repository-relative path.
    for relative, count in files.items():
        # Require a nonempty POSIX-style relative path without traversal.
        if (  # Combine every unsafe or ambiguous baseline-key condition.
            not isinstance(relative, str)  # Require a JSON string path.
            or not relative  # Reject an empty repository path.
            or relative.startswith("/")  # Reject POSIX absolute paths.
            or "\\" in relative  # Reject platform-dependent separators.
            or ".." in Path(relative).parts  # Reject parent traversal.
        ):  # Fail when any baseline-key safety condition matches.
            # Reject unsafe or platform-ambiguous keys.
            raise HeaderPolicyError(f"invalid filler baseline path: {relative!r}")
        # Require a real nonnegative integer while rejecting JSON booleans.
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            # Reject counts that cannot be compared monotonically.
            raise HeaderPolicyError(f"invalid filler baseline count for {relative}")
        # Preserve the validated exact count.
        normalized[relative] = count
    # Return keys in deterministic order for stable tests and diagnostics.
    return dict(sorted(normalized.items()))


# Prove that a candidate filler baseline never increases historical debt.
def validate_baseline_transition(previous: dict[str, int], candidate: dict[str, int]) -> None:
    """Reject any filler-baseline increase or new positive debt."""

    # Inspect every candidate path because omissions naturally represent zero remaining debt.
    for relative, candidate_count in candidate.items():
        # Treat an unlisted prior path as a zero-debt source.
        previous_count = previous.get(relative, 0)
        # Reject both increases and newly introduced positive paths.
        if candidate_count > previous_count:
            # Name only the path and counts so no source content enters diagnostics.
            raise HeaderPolicyError(
                f"filler baseline increased for {relative}: {previous_count} -> {candidate_count}"  # Explain debt.
            )


# Execute one repository-wide or path-bounded check/write transaction.
def run_repository(
    root: Path,  # Receive the explicit Git worktree root.
    *,  # Require policy mode and inputs to be named by callers.
    write: bool,  # Select read-only check or transactional bounded write behavior.
    boundaries: tuple[str, ...] = (),  # Restrict selected paths when provided.
    filler_baseline_path: Path | None = None,  # Optionally supply exact current filler debt.
    previous_filler_baseline_path: Path | None = None,  # Optionally prove monotonic baseline movement.
) -> PolicyRun:  # Return changed-file count and deterministic findings.
    """Inspect tracked source and atomically commit only a fully clean bounded write set."""

    # Refuse any write without an explicit narrower-than-root boundary.
    if write and not boundaries:
        # Prevent an accidental repository-wide rewrite outside explicit operator boundaries.
        raise HeaderPolicyError("--write requires at least one explicit --path boundary")
    # Resolve NOTICE once before source inspection or staging.
    copyright_line = notice_copyright(root)
    # Load the current baseline when explicitly supplied; otherwise require zero filler.
    baseline = load_filler_baseline(filler_baseline_path) if filler_baseline_path else {}
    # Require a current baseline before comparing a previous baseline.
    if previous_filler_baseline_path and not filler_baseline_path:
        # Reject an incomplete monotonic transition request.
        raise HeaderPolicyError("--previous-filler-baseline requires --filler-baseline")
    # Validate monotonic movement when a previous baseline is explicitly supplied.
    if previous_filler_baseline_path:
        # Load the prior version with the same strict schema.
        previous_baseline = load_filler_baseline(previous_filler_baseline_path)
        # Reject candidate debt increases before inspecting source.
        validate_baseline_transition(previous_baseline, baseline)
    # Enumerate only tracked files and apply explicit boundaries.
    selected_paths = tracked_source_paths(root, boundaries)
    # Stage candidate bytes without touching the worktree.
    staged: dict[Path, bytes] = {}
    # Accumulate deterministic path-specific findings.
    findings: list[PolicyFinding] = []
    # Inspect every selected path before permitting any write.
    for path in selected_paths:
        # Compute the stable repository-relative path.
        relative = path.relative_to(root.resolve()).as_posix()
        # Read exact original bytes once.
        original = path.read_bytes()
        # Convert unsafe source state into one path-specific finding.
        try:
            # Add an exact header in memory only when bounded write mode is active.
            candidate = apply_header_bytes(path, original, copyright_line) if write else original
            # Inspect the original in check mode or the staged candidate in write mode.
            messages = inspect_source_bytes(
                path,  # Inspect the canonical source path.
                candidate,  # Inspect original or safely staged bytes by mode.
                copyright_line,  # Enforce the NOTICE-derived attribution.
                baseline.get(relative, 0),  # Require exact configured filler debt or zero.
            )  # Complete the per-file policy inspection.
        # Capture fail-closed policy errors without staging a partial write.
        except HeaderPolicyError as error:
            # Add one stable safety finding for this path.
            findings.append(PolicyFinding(relative, str(error)))
            # Continue inspection so the operator receives a complete selected-set report.
            continue
        # Add each independent policy finding in stable order.
        for message in messages:
            # Preserve the relative path alongside the actionable message.
            findings.append(PolicyFinding(relative, message))
        # Stage only candidates whose complete per-file policy check passed.
        if not messages and candidate != original:
            # Retain bytes in memory until every selected file has passed.
            staged[path] = candidate
    # Fail the whole write transaction when any selected file is unsafe or noncompliant.
    if findings:
        # Return findings without writing even individually clean staged candidates.
        return PolicyRun(changed=0, findings=tuple(findings))
    # Commit staged candidates only after the entire selected set passed.
    if write:
        # Write files in deterministic path order.
        for path in sorted(staged, key=lambda item: item.relative_to(root.resolve()).as_posix()):
            # Replace only the explicitly selected tracked file's bytes.
            path.write_bytes(staged[path])
    # Return the exact number of changed files and an empty finding set.
    return PolicyRun(changed=len(staged) if write else 0, findings=())


# Build the narrow source-header command-line interface.
def _parser() -> argparse.ArgumentParser:
    """Return the command-line parser without reading process-global arguments."""

    # Describe both safe operating modes in the help output.
    parser = argparse.ArgumentParser(
        description="Check tracked Python/JavaScript headers or safely write selected paths."  # Explain scope.
    )  # Finish parser construction.
    # Require callers to choose exactly one mode.
    mode = parser.add_mutually_exclusive_group(required=True)
    # Add the read-only repository/path check mode.
    mode.add_argument("--check", action="store_true", help="inspect without writing")
    # Add the explicitly path-bounded write mode.
    mode.add_argument("--write", action="store_true", help="write only selected clean tracked paths")
    # Allow repeated file or directory boundaries.
    parser.add_argument(
        "--path",  # Name the repeated source-boundary option.
        action="append",  # Preserve every explicit boundary.
        default=[],  # Use an empty selection only for check mode.
        help="repository-relative file or directory boundary; repeat as needed",  # Explain safe use.
    )  # Finish path-option registration.
    # Allow an explicit current filler baseline while the repository default handles normal gate execution.
    parser.add_argument("--filler-baseline", type=Path)
    # Allow an explicit prior baseline for monotonic transition validation.
    parser.add_argument("--previous-filler-baseline", type=Path)
    # Return the fully configured parser.
    return parser


# Execute the CLI and emit concise deterministic operator diagnostics.
def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    """Run the checker and return a process exit status."""

    # Parse explicit test arguments or process arguments when omitted.
    arguments = _parser().parse_args(argv)
    # Select the explicit baseline or discover the repository's default debt ledger when present.
    requested_filler_path = arguments.filler_baseline or DEFAULT_FILLER_BASELINE
    # Resolve the selected baseline relative to the repository unless it is already absolute.
    candidate_filler_path = (
        # Preserve an absolute caller-supplied baseline path.
        requested_filler_path
        if requested_filler_path.is_absolute()
        # Resolve the default or relative caller path from the explicit repository root.
        else root / requested_filler_path
    )
    # Keep temporary zero-debt repositories compatible while a present default is always enforced.
    filler_path = (
        candidate_filler_path
        if arguments.filler_baseline is not None or candidate_filler_path.is_file()
        else None
    )
    # Resolve the optional previous baseline with the same repository-relative convention.
    previous_path = (
        # Preserve an absolute baseline path or resolve a relative one from the repository.
        arguments.previous_filler_baseline  # Preserve an already absolute or missing path.
        if arguments.previous_filler_baseline is None  # Accept an omitted transition input.
        or arguments.previous_filler_baseline.is_absolute()  # Accept an explicit absolute input.
        else root / arguments.previous_filler_baseline  # Resolve a relative prior baseline.
    )  # Finish prior-baseline path normalization.
    # Run the policy and convert top-level configuration failures into a clean diagnostic.
    try:
        # Execute the selected check or bounded write transaction.
        result = run_repository(
            root,  # Check the explicit repository selected by the entry point.
            write=arguments.write,  # Select check or bounded-write behavior.
            boundaries=tuple(arguments.path),  # Preserve every explicit path boundary.
            filler_baseline_path=filler_path,  # Apply the optional current debt baseline.
            previous_filler_baseline_path=previous_path,  # Apply optional monotonic comparison.
        )  # Finish the policy transaction.
    # Report configuration/inventory failures without a Python traceback in normal CLI use.
    except HeaderPolicyError as error:
        # Emit one deterministic failure line.
        print(f"FAIL: {error}")
        # Return a failing status.
        return 1
    # Print every path-specific policy finding.
    for finding in result.findings:
        # Keep diagnostics concise and repository-relative.
        print(f"FAIL: {finding.path}: {finding.message}")
    # Return failure when any selected file remains unsafe or noncompliant.
    if result.findings:
        # Signal the check/write failure to automation without having wired CI.
        return 1
    # Report the successful mode and changed-file count.
    print(
        # Distinguish a read-only check from a bounded write in terminal logs.
        f"PASS: {'wrote' if arguments.write else 'checked'} tracked source; "
        f"{result.changed} file(s) changed"  # Include the exact committed file count.
    )  # Finish the concise success diagnostic.
    # Return success after the entire selected set passed.
    return 0


# Run the command-line entry point only when this file is executed directly.
if __name__ == "__main__":
    # Return the explicit policy status to the invoking shell.
    raise SystemExit(main())
