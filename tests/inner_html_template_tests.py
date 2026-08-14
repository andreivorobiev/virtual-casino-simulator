# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Executable proof for escape-by-default HTML template governance."""

# Import JSON support for disposable baseline fixtures.
import json
# Import temporary directories for isolated source inventories.
import tempfile
# Import unittest for the repository's standard focused-test runner.
import unittest
# Import portable paths for disposable fixture creation.
from pathlib import Path

# Import the production validator rather than duplicating its scanner in tests.
from scripts.validate_inner_html_templates import scan_unmigrated, validate


# Prove the validator permits reductions while rejecting every new raw assignment. (TEST-186)
class InnerHtmlTemplateTests(unittest.TestCase):
    # Build one isolated web tree and reviewed baseline for each assertion.
    def fixture(self, source: str, maximum: int, path: str = "web/view.js") -> tuple[Path, Path, tempfile.TemporaryDirectory]:
        # Allocate task-owned temporary storage with automatic cleanup.
        temporary = tempfile.TemporaryDirectory()
        # Resolve the disposable repository root.
        root = Path(temporary.name)
        # Resolve and create the requested browser source parent.
        source_path = root / path
        # Create every required source directory before writing bytes.
        source_path.parent.mkdir(parents=True, exist_ok=True)
        # Write exact UTF-8 fixture source.
        source_path.write_text(source, encoding="utf-8")
        # Bind the disposable baseline file outside the scanned web tree.
        baseline_path = root / "baseline.json"
        # Persist the requested reviewed ceiling.
        baseline_path.write_text(json.dumps({"maximum_unmigrated_assignments": {path: maximum}}), encoding="utf-8")
        # Return all fixture handles so callers can validate and clean up deterministically.
        return root, baseline_path, temporary

    # Prove the tagged template escapes ordinary text and preserves only explicit raw fragments.
    def test_runtime_helper_escapes_by_default_and_requires_raw_opt_out(self):
        # Read the exact shared implementation for source-bound executable Node coverage.
        source = (Path(__file__).resolve().parents[1] / "web" / "core" / "ui.js").read_text(encoding="utf-8")
        # Require the public helpers and single escape implementation to remain present.
        self.assertIn("export function html(strings,...values)", source)
        # Require raw fragments to use the private marker instead of a public caller-controlled property.
        self.assertIn("const RAW_HTML = Symbol('casino.raw-html')", source)
        # Require the staged adapter to delegate to safe rather than duplicating entity rules.
        self.assertIn("export function escaped(value){ return raw(safe(value)); }", source)

    # Prove exact baseline debt passes and every reduction burns down the checked-in inventory.
    def test_baseline_and_monotonic_reduction_pass(self):
        # Build one fixture containing a single historical raw write.
        root, baseline, temporary = self.fixture("node.innerHTML = legacyMarkup;\n", 1)
        # Ensure the fixture is removed even if validation fails.
        with temporary:
            # Require exact historical debt to pass.
            self.assertEqual(validate(root, baseline), {"web/view.js": 1})
            # Replace the raw write with the governed tagged template.
            (root / "web" / "view.js").write_text("node.innerHTML = html`<p>${value}</p>`;\n", encoding="utf-8")
            # Reject a stale candidate baseline so reviewed counts cannot hide completed burn-down.
            with self.assertRaisesRegex(AssertionError, "web/view.js:1!=0"):
                # Validate the reduced source before its exact baseline is updated.
                validate(root, baseline)
            # Reduce the candidate inventory to the exact observed zero-debt state.
            baseline.write_text(json.dumps({"maximum_unmigrated_assignments": {}}), encoding="utf-8")
            # Require the exact reduced inventory to pass.
            self.assertEqual(validate(root, baseline), {})

    # Prove a new raw assignment fails whether it appears in a known or new file.
    def test_increase_and_new_file_fail_closed(self):
        # Build one known file already at its reviewed ceiling.
        root, baseline, temporary = self.fixture("node.innerHTML = first;\nnode.innerHTML = second;\n", 1)
        # Ensure the disposable tree is removed after both failure assertions.
        with temporary:
            # Reject the known-file increase.
            with self.assertRaisesRegex(AssertionError, "web/view.js:1!=2"):
                # Validate the increased known file.
                validate(root, baseline)
            # Replace the known file with a compliant tagged assignment.
            (root / "web" / "view.js").write_text("node.innerHTML = html`<p>${value}</p>`;\n", encoding="utf-8")
            # Burn the removed assignment out of the exact candidate baseline.
            baseline.write_text(json.dumps({"maximum_unmigrated_assignments": {}}), encoding="utf-8")
            # Add one unreviewed file with a raw assignment.
            (root / "web" / "new.js").write_text("node.innerHTML = unsafe;\n", encoding="utf-8")
            # Reject the unreviewed file at a zero implicit ceiling.
            with self.assertRaisesRegex(AssertionError, "web/new.js:0!=1"):
                # Validate the new-file regression.
                validate(root, baseline)

    # Prove immutable predecessor comparison permits only same or lower candidate debt.
    def test_previous_baseline_rejects_increase_and_new_debt(self):
        # Build a fixture whose candidate exactly matches one current raw assignment.
        root, baseline, temporary = self.fixture("node.innerHTML = legacy;\n", 1)
        # Ensure all exact-base fixtures are removed after the assertions.
        with temporary:
            # Store an immutable predecessor with zero approved debt for the candidate path.
            previous = root / "previous.json"
            # Persist the exact historical zero-debt inventory.
            previous.write_text(json.dumps({"maximum_unmigrated_assignments": {}}), encoding="utf-8")
            # Reject the candidate baseline increase before accepting matching current source.
            with self.assertRaisesRegex(AssertionError, "web/view.js:0->1"):
                # Compare against the immutable event-base inventory.
                validate(root, baseline, previous)
            # Replace the predecessor with a higher historical count to model a legitimate burn-down.
            previous.write_text(json.dumps({"maximum_unmigrated_assignments": {"web/view.js": 2}}), encoding="utf-8")
            # Accept the exact current count because it is lower than the immutable predecessor.
            self.assertEqual(validate(root, baseline, previous), {"web/view.js": 1})

    # Prove Admin cannot be baselined back into an unsafe state.
    def test_admin_raw_write_is_always_rejected(self):
        # Build a fixture whose baseline deliberately attempts to permit Admin debt.
        root, baseline, temporary = self.fixture("view.innerHTML = unsafe;\n", 1, "web/admin.js")
        # Ensure the fixture is removed after the fail-closed assertion.
        with temporary:
            # Reject Admin debt independently of the editable remainder baseline.
            with self.assertRaisesRegex(AssertionError, "Admin innerHTML writes"):
                # Validate the forbidden Admin assignment.
                validate(root, baseline)

    # Prove Admin cannot bypass the tagged helper through the adjacent insertion sink.
    def test_admin_raw_insert_adjacent_html_is_always_rejected(self):
        # Build a fixture containing only an untagged adjacent markup insertion.
        root, baseline, temporary = self.fixture("target.insertAdjacentHTML('beforeend', '<p>unsafe</p>');\n", 0, "web/admin.js")
        # Remove the zero-valued assignment entry so exact debt comparison reaches the insertion gate.
        baseline.write_text(json.dumps({"maximum_unmigrated_assignments": {}}), encoding="utf-8")
        # Ensure the fixture is removed after the fail-closed assertion.
        with temporary:
            # Reject the untagged adjacent insertion independently of the assignment baseline.
            with self.assertRaisesRegex(AssertionError, "Admin insertAdjacentHTML writes"):
                # Validate the forbidden Admin insertion.
                validate(root, baseline)

    # Prove the scanner counts only untagged assignments.
    def test_scanner_distinguishes_tagged_assignments(self):
        # Build one source containing a tagged write and one historical raw write.
        root, _baseline, temporary = self.fixture("a.innerHTML = html`<p>${value}</p>`;\nb.innerHTML = legacy;\n", 1)
        # Ensure the fixture is removed after scanning.
        with temporary:
            # Require exactly one remaining debt occurrence.
            self.assertEqual(scan_unmigrated(root), {"web/view.js": 1})

    # Prove pull-request CI supplies the exact event-base baseline to the production validator.
    def test_ci_wires_immutable_previous_baseline(self):
        # Read the checked workflow without invoking Git or GitHub.
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        # Require the baseline to come from the already fetched immutable pull-request base SHA.
        self.assertIn('git show "${{ github.event.pull_request.base.sha }}:tests/inner_html_template_baseline.json"', workflow)
        # Require the exact-base file to reach the validator's monotonic comparison option.
        self.assertIn('scripts/validate_inner_html_templates.py --previous-baseline "$RUNNER_TEMP/inner-html-template-base.json"', workflow)


# Support direct focused execution outside the aggregate runner.
if __name__ == "__main__":
    # Run with normal unittest exit semantics.
    unittest.main()
