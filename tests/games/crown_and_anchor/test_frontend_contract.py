"""Focused Crown and Anchor frontend/resource contract tests."""

# Import JSON parsing for paired locale resources.
import json
# Import subprocess so the Node frontend module test can run from Python validators.
import subprocess
# Import unittest so this focused module can run directly.
import unittest
# Import pathlib helpers for repository-relative paths.
from pathlib import Path

# Point to the repository root from this focused test module.
ROOT = Path(__file__).resolve().parents[3]
# Point to the English Crown and Anchor resource file.
EN_RESOURCE = ROOT / "web" / "i18n" / "en-US" / "games" / "crown_and_anchor.json"
# Point to the Russian Crown and Anchor resource file.
RU_RESOURCE = ROOT / "web" / "i18n" / "ru-RU" / "games" / "crown_and_anchor.json"
# Point to the isolated Node module test.
NODE_TEST = ROOT / "tests" / "games" / "crown_and_anchor" / "test_frontend.mjs"
# Point to the bundled Node executable used when PATH lacks node.
NODE_EXE = Path("C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")


# Cover resource parity and executable frontend contract.
class CrownAndAnchorFrontendContractTests(unittest.TestCase):
    # Verify English and Russian resources expose identical keys.
    def test_locale_keys_match(self):
        # Load the English source dictionary.
        en = json.loads(EN_RESOURCE.read_text(encoding="utf-8"))
        # Load the Russian localized dictionary.
        ru = json.loads(RU_RESOURCE.read_text(encoding="utf-8"))
        # Assert no keys are missing in either locale.
        self.assertEqual(set(en), set(ru))
        # Assert common raw-key leakage targets are localized.
        self.assertNotIn("action.play", ru.values())

    # Verify the ES module exports and reduced-motion scheduling through Node.
    def test_node_frontend_module_contract(self):
        # Run the game-owned Node contract test without central test discovery edits.
        result = subprocess.run([str(NODE_EXE), str(NODE_TEST)], cwd=ROOT, text=True, capture_output=True, check=False)
        # Assert the Node process succeeded and report stderr when it does not.
        self.assertEqual(result.returncode, 0, result.stderr)


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest's standard command-line runner.
    unittest.main()
