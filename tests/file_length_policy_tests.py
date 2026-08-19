# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free evidence for the source file-length audit standard. (TOOL-020, TEST-244)"""

# Import JSON rendering for isolated review-register fixtures.
import json
# Import disposable directory ownership for source-policy mutation cases.
import pathlib
# Import Git commands for exact tracked-file inventory fixtures.
import subprocess
# Import temporary-directory cleanup.
import tempfile
# Import unit-test assertions.
import unittest

# Import the production policy seams rather than duplicating its decisions.
from scripts import validate_file_length


# Resolve the checked repository for the exact current-baseline acceptance case.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Exercise every owner-approved pass and failure class without touching repository source.
class FileLengthPolicyTests(unittest.TestCase):
    # Create a disposable Git worktree with the required register parent.
    def make_root(self):
        """Return a caller-owned temporary directory and initialized repository root."""
        # Keep the TemporaryDirectory owner alive until the caller explicitly cleans it.
        temporary = tempfile.TemporaryDirectory()
        # Materialize the repository root inside the isolated system directory.
        root = pathlib.Path(temporary.name)
        # Initialize Git quietly because only its tracked inventory is under test.
        subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
        # Create the canonical documentation parent for the review register.
        (root / "docs").mkdir()
        # Return both cleanup ownership and the concrete root.
        return temporary, root

    # Build one valid register row with caller-selected path and reviewed size.
    def entry(self, path, lines_at_review):
        """Return exact six-field audit metadata for one fixture source."""
        # Use substantive one-paragraph rationale so fixtures exercise the real schema.
        return {
            "path": path,
            "lines_at_review": lines_at_review,
            "justification": "This isolated fixture deliberately exceeds the governed threshold so the validator can prove exact registration, growth, and stale-entry behavior without touching repository source.",
            "reviewed_by": "Policy Test Reviewer",
            "review_date": "2026-08-19",
            "revisit_after": "2026-11-19",
        }

    # Write canonical sorted register data inside a disposable root.
    def write_register(self, root, entries):
        """Persist one deterministic fixture register and return its path."""
        # Point to the production-relative register location.
        path = root / "docs" / "file_length_register.json"
        # Serialize sorted fixture entries with stable indentation and a final newline.
        document = {"schema_version": 1, "entries": entries}
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        # Track the register so the fixture resembles an ordinary checkout.
        subprocess.run(["git", "-C", str(root), "add", "docs/file_length_register.json"], check=True, capture_output=True)
        return path

    # Add one source file to the exact Git-owned policy inventory.
    def track_source(self, root, relative, text):
        """Write and track a source fixture using repository-relative POSIX naming."""
        # Convert the normalized fixture path to the host filesystem.
        path = root / pathlib.Path(*pathlib.PurePosixPath(relative).parts)
        # Create any area owner directories before the file write.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Preserve caller-selected text exactly as UTF-8 fixture bytes.
        path.write_text(text, encoding="utf-8", newline="")
        # Add only the named source to Git's tracked inventory.
        subprocess.run(["git", "-C", str(root), "add", relative], check=True, capture_output=True)
        return path

    # Prove protected main's register exactly covers every current offender.
    def test_current_repository_baseline_passes_and_retires_completed_split_rows(self):
        # Run the complete production gate against checked source.
        self.assertEqual(validate_file_length.validate_file_lengths(ROOT), ())
        # Inspect validated rows to bind the reviewed baseline cardinality and retired monolith paths.
        entries = validate_file_length.load_register(ROOT / "docs" / "file_length_register.json")
        self.assertEqual(len(entries), 18)
        # Require the four completed #727-#730 monolith paths to remain below threshold and absent from debt.
        self.assertTrue({"tests/run_tests.py", "casino/core/storage.py", "web/admin.js", "web/app.js"}.isdisjoint(entries))

    # Reject both independent owner-approved threshold classes without review metadata.
    def test_unregistered_line_and_byte_thresholds_fail_closed(self):
        # Isolate the line-threshold failure from repository files.
        temporary, root = self.make_root()
        try:
            # Track a 1,201-line source with no register exception.
            self.track_source(root, "large_lines.py", "# fixture line\n" * 1201)
            # Track a one-line JavaScript source beyond the 96-KiB byte threshold.
            self.track_source(root, "large_bytes.js", "// " + ("x" * (validate_file_length.BYTE_LIMIT + 1)))
            # Provide an exact empty register so only source findings are under test.
            self.write_register(root, [])
            findings = validate_file_length.validate_file_lengths(root)
            # Require distinct actionable findings for line- and byte-driven offenders.
            self.assertEqual(len(findings), 2)
            self.assertIn("large_bytes.js exceeds the file-length threshold", findings[0])
            self.assertIn("large_lines.py exceeds the file-length threshold", findings[1])
        finally:
            # Remove every disposable Git and source byte even after assertion failure.
            temporary.cleanup()

    # Accept registered debt at exactly twenty-percent growth and reject the next line.
    def test_growth_ratchet_is_strictly_greater_than_twenty_percent(self):
        # Isolate both growth boundaries in one tracked source fixture.
        temporary, root = self.make_root()
        try:
            # Use 1,100 reviewed lines so exact twenty-percent growth is 1,320 lines and over threshold.
            source = self.track_source(root, "reviewed.py", "# reviewed line\n" * 1320)
            self.write_register(root, [self.entry("reviewed.py", 1100)])
            # Permit exact twenty-percent growth because the ticket rejects only more than twenty percent.
            self.assertEqual(validate_file_length.validate_file_lengths(root), ())
            # Add one physical line without changing review metadata.
            source.write_text("# reviewed line\n" * 1321, encoding="utf-8", newline="")
            findings = validate_file_length.validate_file_lengths(root)
            self.assertEqual(findings, ("reviewed.py grew more than 20% past its reviewed line count (1100 -> 1321)",))
        finally:
            # Remove the entire disposable repository after the two boundary checks.
            temporary.cleanup()

    # Reject a review row immediately after its source returns below both thresholds.
    def test_registered_source_below_both_thresholds_is_stale(self):
        # Isolate stale-debt evidence from the checked repository register.
        temporary, root = self.make_root()
        try:
            # Track a small source that no longer needs an exception.
            self.track_source(root, "small.py", "# compact source\n" * 10)
            self.write_register(root, [self.entry("small.py", 1300)])
            # Require exact stale diagnostics with current measurements.
            findings = validate_file_length.validate_file_lengths(root)
            self.assertEqual(findings, ("small.py register entry is stale (10 lines, 170 bytes)",))
        finally:
            # Delete the disposable stale fixture.
            temporary.cleanup()

    # Exclude only reviewed data, vendored, and explicit generated-source categories.
    def test_exclusions_require_expected_path_or_header_markers(self):
        # Create one isolated tracked inventory containing every exclusion class.
        temporary, root = self.make_root()
        try:
            # Data sources remain outside first-party hand-written policy.
            self.track_source(root, "data/generated.py", "# ordinary data source\n" * 1300)
            # Vendored JavaScript keeps upstream ownership and size decisions.
            self.track_source(root, "web/vendor/upstream.js", "// upstream\n" * 1300)
            # An exact header marker excludes generated source anywhere else.
            self.track_source(root, "generated.py", "# @generated - do not edit\n" + ("# generated body\n" * 1300))
            self.write_register(root, [])
            # Require all three exclusions to stay out of findings.
            self.assertEqual(validate_file_length.validate_file_lengths(root), ())
        finally:
            # Remove all disposable excluded bytes.
            temporary.cleanup()

    # Reject malformed, duplicate, and noncanonical audit metadata before source evaluation.
    def test_register_schema_and_order_fail_closed(self):
        # Create a disposable root whose tracked sources need no exception.
        temporary, root = self.make_root()
        try:
            # Track both paths so order validation is the first register failure.
            self.track_source(root, "a.py", "# a\n")
            self.track_source(root, "b.py", "# b\n")
            # Reverse otherwise valid rows to prove canonical path ordering is mandatory.
            register = self.write_register(root, [self.entry("b.py", 1300), self.entry("a.py", 1300)])
            with self.assertRaisesRegex(validate_file_length.FileLengthPolicyError, "entries must be sorted by path"):
                validate_file_length.validate_file_lengths(root, register)
            # Duplicate one canonical row to prove ambiguity is rejected independently.
            self.write_register(root, [self.entry("a.py", 1300), self.entry("a.py", 1300)])
            with self.assertRaisesRegex(validate_file_length.FileLengthPolicyError, "duplicate register path"):
                validate_file_length.validate_file_lengths(root)
        finally:
            # Remove the malformed disposable register and Git metadata.
            temporary.cleanup()


# Provide focused direct execution for CI adapters and developer diagnostics.
if __name__ == "__main__":
    unittest.main()
