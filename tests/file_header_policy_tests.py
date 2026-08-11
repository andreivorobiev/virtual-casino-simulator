# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Prove issue #441's enforced file-header policy, safe writer, and migration boundaries."""

# Import codec constants so byte-order-mark preservation can be asserted exactly.
import codecs
# Import JSON support for temporary monotonic filler-baseline fixtures.
import json
# Import path handling for repository-relative test fixtures.
from pathlib import Path
# Import subprocess support so temporary repositories use Git's real tracked-file semantics.
import subprocess
# Import system-path access so the repository root can expose the scripts namespace.
import sys
# Import temporary-directory support so every policy test is isolated and disposable.
import tempfile
# Import unittest as the repository's browser-free test framework.
import unittest

# Resolve the repository root independently of the process working directory.
ROOT = Path(__file__).resolve().parents[1]
# Make the repository script namespace importable for direct policy-unit testing.
if str(ROOT) not in sys.path:
    # Prepend the repository so a globally installed package cannot shadow the local checker.
    sys.path.insert(0, str(ROOT))

# Import the exact checker API after establishing the repository import boundary.
from scripts import check_file_headers as policy


# Define the exact NOTICE fixture approved by the owner for issue #441.
NOTICE_TEXT = (
    # Preserve the product title used by the real repository notice.
    "Virtual Casino Simulator\n"
    # Preserve the fixed-year copyright source used by the checker.
    "Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors\n\n"
    # Include minimal license prose because only the exact Copyright line is parsed.
    "Licensed under the Apache License, Version 2.0.\n"
)
# Reuse the exact expected copyright line in byte-level assertions.
COPYRIGHT_LINE = "Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors"


# Exercise policy behavior in real temporary Git worktrees rather than mocked inventories.
class FileHeaderPolicyTests(unittest.TestCase):
    """Cover fail-closed checks, bounded writes, preservation, and filler ratcheting."""

    # Create one disposable repository for each test.
    def setUp(self) -> None:
        """Initialize an empty Git repository containing the authoritative NOTICE."""

        # Allocate a unique temporary directory for this test.
        self.temporary_directory = tempfile.TemporaryDirectory()
        # Resolve the directory into a Path used by policy APIs.
        self.root = Path(self.temporary_directory.name).resolve()
        # Initialize Git quietly so tracked-only enumeration uses production behavior.
        self._git("init", "-q")
        # Write the approved notice fixture.
        (self.root / "NOTICE").write_text(NOTICE_TEXT, encoding="utf-8")

    # Remove the disposable repository after every test.
    def tearDown(self) -> None:
        """Release temporary files after assertions complete."""

        # Ask TemporaryDirectory to remove the isolated repository.
        self.temporary_directory.cleanup()

    # Run Git without a shell so test path contents cannot become command syntax.
    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run one successful Git command inside the temporary repository."""

        # Execute the requested Git operation and capture concise diagnostics on failure.
        return subprocess.run(
            # Keep the repository location explicit rather than changing process-global cwd.
            ["git", "-C", str(self.root), *arguments],
            # Decode output as text for useful unittest failures.
            text=True,
            # Capture output so passing tests remain quiet.
            stdout=subprocess.PIPE,
            # Capture standard error alongside standard output.
            stderr=subprocess.PIPE,
            # Fail immediately when a fixture command is invalid.
            check=True,
        )

    # Write one fixture path and optionally add it to Git's index.
    def _source(self, relative: str, content: bytes, *, tracked: bool = True) -> Path:
        """Create a source fixture and optionally make it Git-tracked."""

        # Resolve the requested fixture below the temporary repository root.
        path = self.root / relative
        # Create any parent package/directory structure.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Preserve exact fixture bytes for BOM, newline, and invalid-encoding tests.
        path.write_bytes(content)
        # Add only explicitly tracked fixtures to Git.
        if tracked:
            # Use a repository-relative POSIX path for cross-platform Git behavior.
            self._git("add", "--", path.relative_to(self.root).as_posix())
        # Return the absolute fixture path for direct assertions.
        return path

    # Build the exact Python two-line header with a selected newline style.
    def _python_header(self, newline: str = "\n") -> str:
        """Return the exact expected Python header."""

        # Join the NOTICE-derived copyright and fixed SPDX lines.
        return (
            # Put attribution first.
            f"# {COPYRIGHT_LINE}{newline}"
            # Put the machine-readable license identifier second.
            f"# {policy.SPDX_LINE}{newline}"
        )

    # Build the exact JavaScript two-line header with a selected newline style.
    def _javascript_header(self, newline: str = "\n") -> str:
        """Return the exact expected JavaScript header."""

        # Join the NOTICE-derived copyright and fixed SPDX lines.
        return (
            # Put attribution first.
            f"// {COPYRIGHT_LINE}{newline}"
            # Put the machine-readable license identifier second.
            f"// {policy.SPDX_LINE}{newline}"
        )

    # Verify NOTICE supplies the exact fixed-year ownership line.
    def test_notice_copyright_is_exact_and_unambiguous(self) -> None:
        """Derive one fixed-2026 line and reject drift or ambiguity."""

        # Confirm the valid fixture returns the exact source line.
        self.assertEqual(policy.notice_copyright(self.root), COPYRIGHT_LINE)
        # Replace the fixed year with an unauthorized dynamic year.
        (self.root / "NOTICE").write_text(
            NOTICE_TEXT.replace("Copyright 2026", "Copyright 2027"),  # Replace only the governed year.
            encoding="utf-8",  # Preserve the repository text encoding.
        )
        # Reject the changed convention rather than adopting it silently.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "fixed 2026"):
            # Read the now-invalid notice.
            policy.notice_copyright(self.root)
        # Restore the valid line and add a second ambiguous copyright declaration.
        (self.root / "NOTICE").write_text(
            NOTICE_TEXT + "Copyright 2026 Another Holder\n",  # Introduce a second candidate owner.
            encoding="utf-8",  # Preserve the repository text encoding.
        )
        # Reject multiple candidate ownership lines.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "exactly one"):
            # Read the ambiguous notice.
            policy.notice_copyright(self.root)

    # Verify Git, not a recursive filesystem walk, defines the policy inventory.
    def test_tracked_inventory_excludes_untracked_source(self) -> None:
        """Ignore untracked source and honor an explicit tracked directory boundary."""

        # Create one tracked source beneath the selected directory.
        tracked = self._source("package/tracked.py", b'"""Tracked purpose."""\n')
        # Create one untracked source beside it.
        self._source("package/untracked.py", b'"""Untracked purpose."""\n', tracked=False)
        # Create a tracked source outside the requested boundary.
        self._source("other/outside.js", b"// Outside purpose.\n")
        # Enumerate only Git-tracked files below the package boundary.
        selected = policy.tracked_source_paths(self.root, ("package",))
        # Confirm the one expected canonical path is selected.
        self.assertEqual(selected, (tracked.resolve(),))

    def test_tracked_inventory_excludes_vendored_third_party_source(self) -> None:
        """Keep first-party copyright headers out of vendored JavaScript."""

        first_party = self._source("web/app.js", b"// First-party shell.\n")
        self._source("web/vendor/library.js", b"/*! Upstream license. */\n")
        selected = policy.tracked_source_paths(self.root, ("web",))
        self.assertEqual(selected, (first_party.resolve(),))

    # Verify read-only mode reports policy debt and leaves source bytes untouched.
    def test_check_mode_never_writes(self) -> None:
        """Report a missing header without changing an otherwise purposeful module."""

        # Create a tracked module with a substantive module docstring but no license header.
        path = self._source("module.py", b'"""Explain the module purpose."""\nVALUE = 1\n')
        # Preserve exact original bytes for the no-write assertion.
        original = path.read_bytes()
        # Run repository check mode over the selected path.
        result = policy.run_repository(
            self.root,  # Inspect the isolated repository fixture.
            write=False,  # Keep the policy invocation read-only.
            boundaries=("module.py",),  # Restrict inspection to the tracked module.
        )
        # Confirm one missing-header finding is returned.
        self.assertTrue(any("missing exact" in finding.message for finding in result.findings))
        # Confirm check mode reports no changed files.
        self.assertEqual(result.changed, 0)
        # Confirm exact bytes remain unchanged.
        self.assertEqual(path.read_bytes(), original)

    # Verify the Python writer preserves every sensitive preamble and formatting detail.
    def test_python_write_preserves_bom_crlf_shebang_encoding_docstring_and_tokens(self) -> None:
        """Insert after preamble while preserving BOM, CRLF, docstring, and executable tokens."""

        # Build a BOM-prefixed CRLF module with both legal preamble lines and no final newline.
        original_text = (
            "#!/usr/bin/env python\r\n"  # Preserve the executable interpreter directive.
            "# -*- coding: utf-8 -*-\r\n"  # Preserve the explicit source encoding.
            '"""Explain the executable module."""\r\n'  # Supply human-authored file purpose.
            "VALUE = 7"  # Retain executable content without a final newline.
        )
        # Encode the fixture with its explicit UTF-8 marker.
        original = codecs.BOM_UTF8 + original_text.encode("utf-8")
        # Track the exact byte fixture.
        path = self._source("tool.py", original)
        # Capture executable tokens before header insertion.
        before_fingerprint = policy.python_executable_fingerprint(original_text)
        # Run one explicit path-bounded write.
        result = policy.run_repository(
            self.root,  # Apply policy inside the isolated repository.
            write=True,  # Exercise the explicitly authorized writer.
            boundaries=("tool.py",),  # Bound mutation to the selected Python file.
        )
        # Confirm one file changed and no finding remains.
        self.assertEqual(result, policy.PolicyRun(changed=1, findings=()))
        # Read exact candidate bytes after the successful transaction.
        candidate = path.read_bytes()
        # Confirm the UTF-8 marker remains exact.
        self.assertTrue(candidate.startswith(codecs.BOM_UTF8))
        # Decode the BOM-free candidate for physical placement assertions.
        candidate_text = candidate[len(codecs.BOM_UTF8) :].decode("utf-8")
        # Confirm the header appears after shebang and encoding cookie.
        self.assertTrue(
            candidate_text.startswith(  # Compare the complete governed preamble.
                "#!/usr/bin/env python\r\n"  # Require the shebang to remain first.
                "# -*- coding: utf-8 -*-\r\n"  # Require the encoding cookie to remain second.
                + self._python_header("\r\n")  # Require the exact generated license header.
                + '"""Explain the executable module."""\r\n'  # Keep purpose after licensing.
            )
        )
        # Confirm no LF-only newline was introduced.
        self.assertNotIn("\n", candidate_text.replace("\r\n", ""))
        # Confirm original no-final-newline state remains.
        self.assertFalse(candidate_text.endswith(("\n", "\r")))
        # Confirm executable token spelling and order remain identical.
        self.assertEqual(
            policy.python_executable_fingerprint(candidate_text),  # Fingerprint rewritten source.
            before_fingerprint,  # Compare against the pre-write executable token stream.
        )
        # Run the same bounded writer again to prove idempotence.
        second = policy.run_repository(
            self.root,  # Reuse the isolated repository.
            write=True,  # Exercise a second authorized write pass.
            boundaries=("tool.py",),  # Keep the idempotency probe path-bounded.
        )
        # Confirm no second change occurs.
        self.assertEqual(second, policy.PolicyRun(changed=0, findings=()))
        # Confirm exact candidate bytes remain stable.
        self.assertEqual(path.read_bytes(), candidate)

    # Verify JavaScript preserves its byte envelope and executable text exactly.
    def test_javascript_write_preserves_bom_crlf_shebang_and_executable_bytes(self) -> None:
        """Insert after a JS shebang while preserving all original decoded text."""

        # Build BOM-prefixed CRLF JavaScript with a purpose comment and no final newline.
        original_text = "#!/usr/bin/env node\r\n// Explain this command.\r\nconst value = 9;"
        # Encode exact source bytes.
        original = codecs.BOM_UTF8 + original_text.encode("utf-8")
        # Track the JavaScript fixture.
        path = self._source("command.js", original)
        # Apply the bounded writer.
        result = policy.run_repository(
            self.root,  # Apply policy inside the isolated repository.
            write=True,  # Exercise the bounded JavaScript writer.
            boundaries=("command.js",),  # Restrict mutation to the selected command.
        )
        # Confirm one exact change.
        self.assertEqual(result, policy.PolicyRun(changed=1, findings=()))
        # Read and decode the resulting bytes after the preserved BOM.
        candidate = path.read_bytes()
        # Confirm the marker remains exact.
        self.assertTrue(candidate.startswith(codecs.BOM_UTF8))
        # Decode only the BOM-free payload.
        candidate_text = candidate[len(codecs.BOM_UTF8) :].decode("utf-8")
        # Confirm the header follows the shebang and precedes the original purpose comment.
        expected_prefix = (
            "#!/usr/bin/env node\r\n"  # Require the runtime shebang to remain first.
            + self._javascript_header("\r\n")  # Require the exact JavaScript license header.
            + "// Explain this command.\r\n"  # Keep human purpose after licensing.
        )
        # Assert exact physical placement.
        self.assertTrue(candidate_text.startswith(expected_prefix))
        # Remove the known exact inserted slice to prove the original text is reproduced.
        reconstructed = candidate_text.replace(self._javascript_header("\r\n"), "", 1)
        # Confirm executable and comment bytes outside the insertion remain exact.
        self.assertEqual(reconstructed, original_text)
        # Confirm final-newline absence remains unchanged.
        self.assertFalse(candidate_text.endswith(("\n", "\r")))

    # Verify policy never invents prose for a semantic package marker.
    def test_semantic_marker_init_is_license_only_but_active_init_needs_purpose(self) -> None:
        """Exempt empty/docstring-only markers while requiring active initialization purpose."""

        # Create an empty package marker.
        marker = self._source("marker/__init__.py", b"")
        # Apply a bounded license-header write.
        marker_result = policy.run_repository(
            self.root,  # Apply policy inside the isolated repository.
            write=True,  # Exercise license insertion for a marker package.
            boundaries=("marker/__init__.py",),  # Limit mutation to the marker initializer.
        )
        # Confirm license-only marker handling passes.
        self.assertEqual(marker_result, policy.PolicyRun(changed=1, findings=()))
        # Confirm no generated purpose prose was added.
        self.assertEqual(marker.read_text(encoding="utf-8"), self._python_header())
        # Create active package initialization with the exact header but no purpose.
        active = self._source(
            "active/__init__.py",  # Name the executable package initializer.
            (self._python_header() + "VALUE = 1\n").encode("utf-8"),  # Omit purpose deliberately.
        )
        # Check the active initializer.
        active_result = policy.run_repository(
            self.root,  # Inspect the isolated repository.
            write=False,  # Detect missing purpose without mutation.
            boundaries=("active/__init__.py",),  # Select the active initializer only.
        )
        # Confirm purpose remains an explicit human-authored requirement.
        self.assertTrue(any("missing substantive" in item.message for item in active_result.findings))
        # Replace it with a substantive module docstring and active code.
        active.write_text(
            self._python_header() + '"""Initialize the active package registry."""\nVALUE = 1\n',  # Add purpose.
            encoding="utf-8",  # Preserve the repository text encoding.
        )
        # Confirm the active initializer now passes.
        passing = policy.run_repository(
            self.root,  # Inspect the corrected isolated repository.
            write=False,  # Confirm compliance without mutation.
            boundaries=("active/__init__.py",),  # Select the active initializer only.
        )
        # Assert the clean result.
        self.assertEqual(passing, policy.PolicyRun(changed=0, findings=()))

    # Verify shebangs, encoding cookies, license lines, and filler do not masquerade as purpose.
    def test_transport_license_and_filler_comments_do_not_satisfy_python_purpose(self) -> None:
        """Require human purpose beyond preamble and generated filler."""

        # Build a fully licensed module whose only other comments are transport metadata and exact filler.
        content = (
            "#!/usr/bin/env python\n"  # Supply transport metadata rather than purpose.
            "# coding: utf-8\n"  # Supply encoding metadata rather than purpose.
            + self._python_header()  # Supply the exact governed license lines.
            + "# Execute this statement as part of the module's documented control flow.\n"  # Add exact filler.
            + "VALUE = 1\n"  # Include executable content requiring real purpose.
        )
        # Track the fixture.
        self._source("no_purpose.py", content.encode("utf-8"))
        # Supply an exact baseline so only the purpose finding remains.
        baseline = self.root / "baseline.json"
        # Write the current exact filler debt.
        baseline.write_text(
            json.dumps({"version": 1, "files": {"no_purpose.py": 1}}),  # Record exact filler debt.
            encoding="utf-8",  # Preserve the baseline text encoding.
        )
        # Check the selected module.
        result = policy.run_repository(
            self.root,  # Inspect the isolated repository.
            write=False,  # Report purpose debt without mutation.
            boundaries=("no_purpose.py",),  # Select the deliberately deficient module.
            filler_baseline_path=baseline,  # Supply the approved current filler count.
        )
        # Confirm the missing-purpose finding is present.
        self.assertEqual(
            result.findings,  # Compare the complete finding collection.
            (  # Build the one expected fail-closed result.
                policy.PolicyFinding(  # Express the exact policy violation.
                    "no_purpose.py",  # Identify the deficient tracked file.
                    "missing substantive file-purpose docstring or leading comment",  # Pin the reason.
                ),
            ),
        )

    # Verify partial or conflicting governed markers fail without byte mutation.
    def test_partial_or_misplaced_header_fails_closed(self) -> None:
        """Reject existing governed text instead of normalizing it."""

        # Build a purposeful module with only one governed line in the wrong location.
        original = (
            '"""Explain this module."""\n'  # Start with legitimate human purpose.
            "VALUE = 1\n"  # Place executable content before the governed marker.
            f"# {COPYRIGHT_LINE}\n"  # Add a displaced partial header.
        ).encode("utf-8")  # Preserve the exact unsafe fixture bytes.
        # Track the unsafe fixture.
        path = self._source("partial.py", original)
        # Attempt a bounded write that must remain fail-closed.
        result = policy.run_repository(
            self.root,  # Apply policy inside the isolated repository.
            write=True,  # Attempt the bounded writer against unsafe input.
            boundaries=("partial.py",),  # Select only the partial-header fixture.
        )
        # Confirm the governed-marker conflict is reported.
        self.assertTrue(any("partial, conflicting" in item.message for item in result.findings))
        # Confirm the whole write transaction changed nothing.
        self.assertEqual(result.changed, 0)
        # Confirm exact original bytes remain intact.
        self.assertEqual(path.read_bytes(), original)

    # Verify semantically similar spacing does not satisfy the exact physical-header policy.
    def test_noncanonical_header_spacing_fails_closed(self) -> None:
        """Reject nonexact comment syntax without normalizing existing attribution."""

        # Build purposeful source whose governed text omits the required space after each marker.
        original = (
            f"#{COPYRIGHT_LINE}\n"  # Omit required physical spacing deliberately.
            f"#{policy.SPDX_LINE}\n"  # Repeat the noncanonical spacing for SPDX.
            '"""Explain the module."""\n'  # Retain otherwise valid file purpose.
        ).encode("utf-8")  # Preserve exact noncanonical bytes.
        # Track the noncanonical fixture.
        path = self._source("noncanonical.py", original)
        # Attempt the bounded writer.
        result = policy.run_repository(
            self.root,  # Apply policy inside the isolated repository.
            write=True,  # Attempt normalization that must be refused.
            boundaries=("noncanonical.py",),  # Select only the malformed header.
        )
        # Confirm exact physical text is enforced.
        self.assertTrue(any("physical header text is not exact" in item.message for item in result.findings))
        # Confirm no normalization occurred.
        self.assertEqual(path.read_bytes(), original)

    # Verify a shebang displaced by prior content cannot be silently preserved in the wrong location.
    def test_displaced_shebang_fails_closed(self) -> None:
        """Reject Python and JavaScript shebangs outside physical line one."""

        # Build Python whose shebang is already invalidly displaced.
        python_path = self._source(
            "displaced.py",  # Name the invalid Python fixture.
            b'"""Explain the module."""\n#!/usr/bin/env python\nVALUE = 1\n',  # Displace its shebang.
        )
        # Build JavaScript whose runtime shebang is already invalidly displaced.
        javascript_path = self._source(
            "displaced.js",  # Name the invalid JavaScript fixture.
            b"// Explain the module.\n#!/usr/bin/env node\nconst value = 1;\n",  # Displace its shebang.
        )
        # Preserve both exact sources.
        originals = {
            # Preserve Python bytes.
            python_path: python_path.read_bytes(),
            # Preserve JavaScript bytes.
            javascript_path: javascript_path.read_bytes(),
        }
        # Attempt a bounded selected-set write.
        result = policy.run_repository(
            self.root,  # Apply policy inside the isolated repository.
            write=True,  # Attempt the bounded multi-file writer.
            boundaries=("displaced.py", "displaced.js"),  # Select both unsafe fixtures.
        )
        # Confirm both files report a physical-line-one failure.
        self.assertEqual(
            sum("physical line one" in item.message for item in result.findings),
            2,
        )
        # Confirm neither original was rewritten.
        for path, original in originals.items():
            # Compare one exact unsafe fixture.
            self.assertEqual(path.read_bytes(), original)

    # Verify malformed encoding, syntax, and newline state never produce writes.
    def test_invalid_python_and_mixed_newlines_fail_closed(self) -> None:
        """Preserve exact bytes for undecodable, unparsable, and mixed-newline source."""

        # Create declared-ASCII source containing an invalid non-ASCII byte.
        invalid_encoding = self._source(
            "invalid_encoding.py",
            b"# coding: ascii\n\"\"\"Purpose.\"\"\"\nVALUE = '\xff'\n",
        )
        # Create syntactically invalid but decodable source.
        invalid_syntax = self._source(
            "invalid_syntax.py",
            b'"""Purpose."""\nif True print("broken")\n',
        )
        # Create purposeful source with mixed LF and CRLF newlines.
        mixed_newline = self._source(
            "mixed.py",
            b'"""Purpose."""\r\nVALUE = 1\n',
        )
        # Preserve every original fixture byte sequence.
        originals = {
            # Preserve invalid encoding bytes.
            invalid_encoding: invalid_encoding.read_bytes(),
            # Preserve invalid syntax bytes.
            invalid_syntax: invalid_syntax.read_bytes(),
            # Preserve mixed newline bytes.
            mixed_newline: mixed_newline.read_bytes(),
        }
        # Attempt one bounded multi-file write.
        result = policy.run_repository(
            self.root,
            write=True,
            boundaries=("invalid_encoding.py", "invalid_syntax.py", "mixed.py"),
        )
        # Confirm the transaction reports failures and writes nothing.
        self.assertTrue(result.findings)
        # Confirm changed count remains zero.
        self.assertEqual(result.changed, 0)
        # Confirm all unsafe files retain exact bytes.
        for path, original in originals.items():
            # Compare one preserved fixture.
            self.assertEqual(path.read_bytes(), original)

    # Verify a failing selected file prevents writes to other selected clean files.
    def test_write_transaction_is_all_or_nothing_for_selected_set(self) -> None:
        """Do not write a clean candidate when another selected file fails policy."""

        # Create one purposeful clean module that only needs a header.
        clean = self._source("clean.py", b'"""Explain clean behavior."""\nVALUE = 1\n')
        # Create one active module with no purpose.
        failing = self._source("failing.py", b"VALUE = 2\n")
        # Preserve both byte sequences.
        clean_original = clean.read_bytes()
        # Preserve the failing module bytes too.
        failing_original = failing.read_bytes()
        # Attempt one bounded write across both tracked files.
        result = policy.run_repository(
            self.root,
            write=True,
            boundaries=("clean.py", "failing.py"),
        )
        # Confirm the selected-set transaction fails.
        self.assertTrue(result.findings)
        # Confirm no candidate was committed.
        self.assertEqual(result.changed, 0)
        # Confirm the clean file did not receive a partial transaction header.
        self.assertEqual(clean.read_bytes(), clean_original)
        # Confirm the failing file also remains exact.
        self.assertEqual(failing.read_bytes(), failing_original)

    # Verify an explicit path write cannot modify unselected tracked or untracked files.
    def test_path_bounded_write_changes_only_selected_tracked_file(self) -> None:
        """Restrict write scope even when adjacent tracked and untracked files need headers."""

        # Create the one selected tracked purposeful module.
        selected = self._source("area/selected.py", b'"""Selected purpose."""\nVALUE = 1\n')
        # Create an unselected tracked purposeful module.
        outside = self._source("area/outside.py", b'"""Outside purpose."""\nVALUE = 2\n')
        # Create an untracked purposeful module.
        untracked = self._source(
            "area/untracked.py",
            b'"""Untracked purpose."""\nVALUE = 3\n',
            tracked=False,
        )
        # Preserve both files outside the write boundary.
        outside_original = outside.read_bytes()
        # Preserve the untracked file bytes.
        untracked_original = untracked.read_bytes()
        # Apply the explicit file boundary.
        result = policy.run_repository(
            self.root,
            write=True,
            boundaries=("area/selected.py",),
        )
        # Confirm only the selected source changed.
        self.assertEqual(result, policy.PolicyRun(changed=1, findings=()))
        # Confirm the exact header was added to the selected file.
        self.assertTrue(selected.read_text(encoding="utf-8").startswith(self._python_header()))
        # Confirm the adjacent tracked file remained unchanged.
        self.assertEqual(outside.read_bytes(), outside_original)
        # Confirm the adjacent untracked file remained unchanged.
        self.assertEqual(untracked.read_bytes(), untracked_original)

    # Verify write mode requires a narrower-than-repository path boundary.
    def test_unbounded_write_is_refused(self) -> None:
        """Reject API and CLI attempts to write the entire repository."""

        # Create a valid tracked fixture so the refusal is not caused by an empty inventory.
        self._source("module.py", b'"""Module purpose."""\n')
        # Reject direct API write mode without a boundary.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "explicit --path"):
            # Attempt the forbidden unbounded write.
            policy.run_repository(self.root, write=True)
        # Confirm CLI handling converts the same refusal into a failing exit status.
        self.assertEqual(policy.main(["--write"], root=self.root), 1)

    # Verify exact filler comments are counted while identical string literals are ignored.
    def test_filler_count_is_comment_only_and_exact(self) -> None:
        """Avoid heuristic matching and never count source string contents."""

        # Build source with one exact filler comment, one near-match comment, and one exact string literal.
        text = (
            '"""Explain filler counting."""\n'
            "# Return the computed value to the caller.\n"
            "# Return the computed value to the caller. Extra context.\n"
            'TEXT = "Return the computed value to the caller."\n'
        )
        # Count filler using Python tokens.
        count = policy.filler_count(text, ".py")
        # Confirm only the exact actual comment matches.
        self.assertEqual(count, 1)

    # Verify baseline files enforce exact current debt and monotonic transitions.
    def test_filler_baseline_exactness_and_monotonic_transition(self) -> None:
        """Accept decreases but reject increases, new debt, and stale source counts."""

        # Create a fully licensed purposeful source with one exact filler comment.
        source = self._source(
            "module.py",
            (
                self._python_header()
                + '"""Explain baseline behavior."""\n'
                + "# Return the computed value to the caller.\n"
                + "VALUE = 1\n"
            ).encode("utf-8"),
        )
        # Keep the fixture referenced so static analyzers see intentional creation.
        self.assertTrue(source.is_file())
        # Write an exact current baseline.
        baseline = self.root / "baseline.json"
        # Store one unit of existing filler debt.
        baseline.write_text(
            json.dumps({"version": 1, "files": {"module.py": 1}}),
            encoding="utf-8",
        )
        # Confirm exact source/baseline agreement passes.
        passing = policy.run_repository(
            self.root,
            write=False,
            boundaries=("module.py",),
            filler_baseline_path=baseline,
        )
        # Assert no policy finding remains.
        self.assertEqual(passing, policy.PolicyRun(changed=0, findings=()))
        # Write a stale zero baseline while source still contains one exact filler.
        baseline.write_text(
            json.dumps({"version": 1, "files": {"module.py": 0}}),
            encoding="utf-8",
        )
        # Confirm stale baseline disagreement fails.
        stale = policy.run_repository(
            self.root,
            write=False,
            boundaries=("module.py",),
            filler_baseline_path=baseline,
        )
        # Assert the exact actual/expected values are reported.
        self.assertTrue(any("count 1 does not match baseline 0" in item.message for item in stale.findings))
        # Accept a baseline decrease for an existing path.
        policy.validate_baseline_transition({"module.py": 2}, {"module.py": 1})
        # Accept removal of a zero-debt path.
        policy.validate_baseline_transition({"module.py": 1}, {})
        # Reject an increase on an existing path.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "increased"):
            # Compare a regressing candidate.
            policy.validate_baseline_transition({"module.py": 1}, {"module.py": 2})
        # Reject newly introduced positive debt.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "new.py"):
            # Compare a new positive path against an empty prior baseline.
            policy.validate_baseline_transition({}, {"new.py": 1})

    # Verify malformed baseline structures fail without source mutation.
    def test_invalid_baseline_fails_closed(self) -> None:
        """Reject unsafe baseline paths, counts, and schemas."""

        # Create a purposeful tracked module.
        path = self._source("module.py", b'"""Module purpose."""\n')
        # Preserve exact source bytes.
        original = path.read_bytes()
        # Create a baseline with a parent-traversing key.
        baseline = self.root / "baseline.json"
        # Write the invalid but syntactically valid JSON.
        baseline.write_text(
            json.dumps({"version": 1, "files": {"../module.py": 1}}),
            encoding="utf-8",
        )
        # Reject the unsafe baseline before source inspection.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "invalid filler baseline path"):
            # Attempt a bounded write using the invalid baseline.
            policy.run_repository(
                self.root,
                write=True,
                boundaries=("module.py",),
                filler_baseline_path=baseline,
            )
        # Confirm source bytes remain exact.
        self.assertEqual(path.read_bytes(), original)

    # Verify a purpose-like string does not satisfy JavaScript's leading-comment policy.
    def test_javascript_requires_leading_comment_not_string_literal(self) -> None:
        """Use conservative comment recognition instead of a JavaScript parser guess."""

        # Build licensed JavaScript whose first executable line is a purpose-like string.
        content = (
            self._javascript_header()
            + 'const description = "Explain this JavaScript module.";\n'
        )
        # Track the fixture.
        self._source("module.js", content.encode("utf-8"))
        # Check the selected source.
        result = policy.run_repository(
            self.root,
            write=False,
            boundaries=("module.js",),
        )
        # Confirm executable string text does not count as leading purpose documentation.
        self.assertTrue(any("missing substantive" in item.message for item in result.findings))

    # Verify repository root and parent traversal cannot become write boundaries.
    def test_unsafe_write_boundaries_are_rejected(self) -> None:
        """Reject repository-wide and escaping write scopes before inventory mutation."""

        # Create a valid tracked source.
        path = self._source("module.py", b'"""Module purpose."""\n')
        # Preserve source bytes.
        original = path.read_bytes()
        # Reject an explicit root boundary.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "narrower"):
            # Attempt to name the repository root directly.
            policy.run_repository(self.root, write=True, boundaries=(".",))
        # Reject a parent-traversing boundary.
        with self.assertRaisesRegex(policy.HeaderPolicyError, "escapes"):
            # Attempt to escape the repository.
            policy.run_repository(self.root, write=True, boundaries=("../outside.py",))
        # Confirm the source remains unchanged.
        self.assertEqual(path.read_bytes(), original)


# Run this focused suite directly when invoked as a script.
if __name__ == "__main__":
    # Return unittest's process status to the caller.
    unittest.main()
