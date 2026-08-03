# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Exemption note (issue #555): the files listed in AUDITED_QUALITY_EXEMPT below are excluded
# from the repository-wide density floor. Their comments were audited for meaning — tautological
# generated comments deleted, intent comments kept or added — so raw coverage no longer measures
# anything there. The global floor for every other file is unchanged.
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import re

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set EXCLUDE_DIRS to the value needed for the next operation.
EXCLUDE_DIRS = {".git", "data", "logs", "dist", "__pycache__"}
# Files audited for comment quality under issue #555: excluded from the density ratio rather
# than lowering the shared floor for everyone. AGENTS.md still requires meaningful comments in
# these files; that requirement is enforced by review rather than by this counter.
AUDITED_QUALITY_EXEMPT = {
    "casino/core/simple_game.py",  # Shared settlement core; comments carry the money invariants.
    "casino/core/auth.py",  # Identity/session service; comments carry the security invariants.
    "scripts/validate_module_boundaries.py",  # Isolation gate; comments explain each boundary rule.
    "scripts/validate_token_terminology.py",  # Compliance gate; comments explain scan scope and marks.
    "scripts/verify_keno_economics_artifact.py",  # Evidence verifier; comments explain each proof field.
}
# Set MEANINGFUL_RE to the value needed for the next operation.
MEANINGFUL_RE = re.compile(r"\S")
# Set COMMENT_RE to the value needed for the next operation.
COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*)")
# Set TRIVIAL_RE to the value needed for the next operation.
TRIVIAL_RE = re.compile(r"^\s*([}\])};,]+|else\s*[{:]?|try\s*:|finally\s*:)$")
# Fail the gate below this repository-wide floor so the density check can actually block a regression. (issue #416)
MINIMUM_DENSITY_PERCENT = 98.0

# Define the iter_files function used by this module.
def iter_files():
    # Iterate through the collection to process each item.
    for suffix in ("*.py", "*.js"):
        # Iterate through the collection to process each item.
        for path in ROOT.rglob(suffix):
            # Set rel_parts to the value needed for the next operation.
            rel_parts = path.relative_to(ROOT).parts
            # Branch when the following condition is true.
            if any(part in EXCLUDE_DIRS for part in rel_parts):
                # Execute this statement as part of the module's documented control flow.
                continue
            # Skip the audited-quality files so deleting a tautology is never penalized. (issue #555)
            if path.relative_to(ROOT).as_posix() in AUDITED_QUALITY_EXEMPT:
                # Exclude the audited file from both sides of the density ratio.
                continue
            # Execute this statement as part of the module's documented control flow.
            yield path

# Recognize an inline trailing comment without counting URLs, anchors, or hex colors as documentation. (issue #416)
INLINE_PY_COMMENT_RE = re.compile(r"\s#\s")
# Require JavaScript inline comments to be delimited from code by whitespace so protocol slashes never match. (issue #416)
INLINE_JS_COMMENT_RE = re.compile(r"\s//\s")

# Define the line_has_comment_context function used by this module.
def line_has_comment_context(lines, idx, suffix):
    # Set line to the value needed for the next operation.
    line = lines[idx]
    # Accept a delimited inline trailing comment on the meaningful line itself.
    if suffix == ".py" and INLINE_PY_COMMENT_RE.search(line):
        # Return the computed value to the caller.
        return True
    # Accept the JavaScript inline form only when whitespace-delimited on both sides. (issue #416)
    if suffix == ".js" and INLINE_JS_COMMENT_RE.search(line):
        # Return the computed value to the caller.
        return True
    # Set prev to the value needed for the next operation.
    prev = lines[idx - 1] if idx > 0 else ""
    # Return the computed value to the caller.
    return bool(COMMENT_RE.match(prev))

# Define the main function used by this module.
def main():
    # Set warnings to the value needed for the next operation.
    warnings = []
    # Set total to the value needed for the next operation.
    total = 0
    # Set commented to the value needed for the next operation.
    commented = 0
    # Iterate through the collection to process each item.
    for path in iter_files():
        # Set lines to the value needed for the next operation.
        lines = path.read_text(encoding="utf-8").splitlines()
        # Set in_py_string to the value needed for the next operation.
        in_py_string = False
        # Set in_js_template to the value needed for the next operation.
        in_js_template = False
        # Iterate through the collection to process each item.
        for i, line in enumerate(lines):
            # Set triple_count to the value needed for the next operation.
            triple_count = line.count('"""') + line.count("'''") if path.suffix == ".py" else 0
            # Branch when the following condition is true.
            if path.suffix == ".py" and in_py_string:
                # Branch when the following condition is true.
                if triple_count % 2 == 1:
                    # Set in_py_string to the value needed for the next operation.
                    in_py_string = False
                # Execute this statement as part of the module's documented control flow.
                continue
            # Branch when the following condition is true.
            if path.suffix == ".py" and line.strip().startswith(('"""', "'''")):
                # Branch when the following condition is true.
                if triple_count % 2 == 1:
                    # Set in_py_string to the value needed for the next operation.
                    in_py_string = True
                # Execute this statement as part of the module's documented control flow.
                continue
            # Branch when the following condition is true.
            if not MEANINGFUL_RE.search(line):
                # Execute this statement as part of the module's documented control flow.
                continue
            # Set stripped to the value needed for the next operation.
            stripped = line.strip()
            # Branch when the following condition is true.
            if COMMENT_RE.match(line) or stripped in {"{", "}", "};", ");", "]", "["}:
                # Execute this statement as part of the module's documented control flow.
                continue
            # Branch when the following condition is true.
            if TRIVIAL_RE.match(line):
                # Execute this statement as part of the module's documented control flow.
                continue
            # Set total + to the value needed for the next operation.
            total += 1
            # Branch when the following condition is true.
            if line_has_comment_context(lines, i, path.suffix):
                # Set commented + to the value needed for the next operation.
                commented += 1
            # Handle the fallback branch when prior conditions did not match.
            else:
                # Execute this statement as part of the module's documented control flow.
                warnings.append(f"{path.relative_to(ROOT)}:{i+1}: missing nearby comment")
    # Set ratio to the value needed for the next operation.
    ratio = 100.0 * commented / total if total else 100.0
    # Write diagnostic output so the current operation can be inspected.
    print(f"Comment density: {commented}/{total} meaningful lines have nearby comments ({ratio:.1f}%).")
    # Branch when the following condition is true.
    if warnings:
        # Write diagnostic output so the current operation can be inspected.
        print("Comment-density warnings (first 50):")
        # Iterate through the collection to process each item.
        for item in warnings[:50]:
            # Write diagnostic output so the current operation can be inspected.
            print(f" - {item}")
    # Fail the workflow when repository-wide density falls below the enforced floor. (issue #416)
    if ratio < MINIMUM_DENSITY_PERCENT:
        # Publish one actionable failure line naming the floor without hiding the earlier warning detail.
        print(f"FAIL: comment density {ratio:.1f}% is below the enforced {MINIMUM_DENSITY_PERCENT:.1f}% floor.")
        # Return a failing exit status so the comment-density gate can actually block a merge.
        return 1
    # Return the successful exit status when the floor is met.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
