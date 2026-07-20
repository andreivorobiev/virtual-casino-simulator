"""Browser-client CSRF and guest context-proof contract wrapper for TEST-047 and TEST-080."""

# Import executable discovery for local and CI Node runtimes.
import shutil
# Import portable paths for the focused module.
import pathlib
# Import subprocess execution for the real browser API helper.
import subprocess
# Import unittest assertions and skips.
import unittest

# Resolve the exact checkout root.
ROOT = pathlib.Path(__file__).resolve().parents[2]


# Validate browser request-integrity behavior through the tracked JavaScript helper.
class BrowserSecurityContractTests(unittest.TestCase):
    # Send state-changing and read-only requests through the real API module.
    def test_browser_helper_attaches_only_scoped_integrity_proofs(self):
        # Discover Node from PATH before considering the bundled Windows runtime.
        node = shutil.which("node")
        # Resolve the bundled runtime used by the desktop workspace when PATH is minimal.
        bundled = pathlib.Path("C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
        # Select the bundled executable only when ordinary discovery failed and it exists.
        if not node and bundled.is_file():
            # Use the exact absolute bundled executable path.
            node = str(bundled)
        # Skip only when the platform has no JavaScript runtime at all.
        if not node:
            # Preserve Linux CI as the required browser-client execution gate.
            self.skipTest("Node is unavailable")
        # Execute the focused real-module contract without a listener.
        result = subprocess.run([node, "tests/security/test_browser_api.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=20)
        # Require every browser request assertion to pass.
        self.assertEqual(result.returncode, 0, msg=result.stderr[-1200:])


# Run this focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
