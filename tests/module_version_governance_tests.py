# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Generic module-version governance evidence for issue #707. (TOOL-018, TEST-184)"""

# Import JSON for temporary manifest and descriptor fixtures.
import json
# Import portable temporary paths without touching repository manifests.
import pathlib
# Import disposable directory ownership for mutation-focused helper evidence.
import tempfile
# Import unit-test assertions.
import unittest

# Import the sanctioned bump helper and generic version validator seams.
from scripts import bump_module_version, validate_versions


# Resolve checked source for conflict-prone literal and workflow-policy checks.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Prove descriptor alignment, helper compatibility, and exact-base downgrade rejection generically.
class ModuleVersionGovernanceTests(unittest.TestCase):
    # Create a minimal isolated manifest pair for one module.
    def make_fixture(self, root, version="1.2.3"):
        # Create the canonical module directory inside the caller-owned disposable root.
        modules = root / "modules"
        modules.mkdir()
        # Write an aggregate with one independently versioned module.
        (modules / "module-manifest.json").write_text(json.dumps({"application": "0.9.5.77", "source_baseline": "9.1.0", "modules": {"sample": version}}, indent=2) + "\n", encoding="utf-8")
        # Write the matching descriptor that the helper must update in the same operation.
        (modules / "sample.json").write_text(json.dumps({"module": "sample", "version": version, "paths": ["sample/"]}, indent=2) + "\n", encoding="utf-8")

    # Require the sanctioned helper to produce a passing monotonic pair without editing a test pin.
    def test_bump_helper_updates_only_generic_sources(self):
        # Isolate all writes in one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Build the smallest valid current and baseline inputs.
            root = pathlib.Path(temporary)
            self.make_fixture(root)
            baseline_path = root / "baseline.json"
            baseline_path.write_text(json.dumps({"modules": {"sample": "1.2.3"}}), encoding="utf-8")
            # Apply the official compatible patch bump.
            self.assertEqual(bump_module_version.bump_module(root, "sample", "patch"), ("1.2.3", "1.2.4"))
            # Load both independently written surfaces after the helper returns.
            manifest = json.loads((root / "modules" / "module-manifest.json").read_text(encoding="utf-8"))
            descriptor = json.loads((root / "modules" / "sample.json").read_text(encoding="utf-8"))
            # Require exact descriptor-to-aggregate equality without a hard-coded repository module value.
            self.assertEqual(descriptor["version"], manifest["modules"]["sample"])
            # Require the generic exact-base comparison to accept the one-step successor.
            errors = []
            validate_versions.validate_module_monotonicity(manifest["modules"], baseline_path, errors)
            self.assertEqual(errors, [])

    # Reject a semantic downgrade and removal against the exact PR base.
    def test_monotonic_baseline_rejects_downgrade_and_removal(self):
        # Store immutable baseline evidence independently of current candidate values.
        with tempfile.TemporaryDirectory() as temporary:
            baseline_path = pathlib.Path(temporary) / "baseline.json"
            baseline_path.write_text(json.dumps({"modules": {"alpha": "2.4.1", "removed": "1.0.0"}}), encoding="utf-8")
            # Compare a downgraded shared module and a missing prior module in one pass.
            errors = []
            validate_versions.validate_module_monotonicity({"alpha": "2.4.0", "new": "1.0.0"}, baseline_path, errors)
            # Require both independent failure classes and permit a newly added module.
            self.assertEqual(errors, ["current manifest removed baseline modules: removed", "module alpha version 2.4.0 is below baseline 2.4.1"])

    # Bind exact CI base selection and removal of all conflict-prone module literal pins.
    def test_ci_uses_exact_base_and_request_latency_has_no_module_pins(self):
        # Read inert CI workflow text without invoking Git or GitHub.
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        # Fetch and read the event's immutable base SHA rather than a moving branch name.
        self.assertIn('git fetch --no-tags --depth=1 origin "${{ github.event.pull_request.base.sha }}"', workflow)
        self.assertIn('git show "${{ github.event.pull_request.base.sha }}:modules/module-manifest.json"', workflow)
        self.assertIn('scripts/validate_versions.py --baseline-manifest "$RUNNER_TEMP/module-manifest-base.json"', workflow)
        # Reject the former repeated descriptor parsing and exact module-version assertions.
        request_oracle = (ROOT / "tests" / "unit" / "request_latency_benchmark_tests.py").read_text(encoding="utf-8")
        self.assertNotIn('_module["version"]', request_oracle)
        self.assertIn("Module descriptor equality and monotonicity are governed generically by TEST-184", request_oracle)
        # Require the sanctioned CLI to regenerate derived docs after its reusable helper writes source manifests.
        bump_source = (ROOT / "scripts" / "bump_module_version.py").read_text(encoding="utf-8")
        self.assertIn('subprocess.check_call([sys.executable, "scripts/generate_docs.py"], cwd=ROOT)', bump_source)


# Run focused diagnostics directly without repository or network mutation.
if __name__ == "__main__":
    # Use unittest's deterministic process status.
    unittest.main()
