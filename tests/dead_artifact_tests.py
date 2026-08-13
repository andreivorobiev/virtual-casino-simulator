# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed checks for repository artifacts retired by issue #711. (TOOL-016, TEST-181)"""

# Import pathlib so every assertion uses repository-relative exact paths.
import pathlib
# Import regular expressions for exact JavaScript export detection.
import re
# Import unittest for dependency-free focused execution.
import unittest

# Resolve the repository root from this tracked test module.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Bind each removed export to its owning production module.
REMOVED_EXPORTS = {
    "web/core/autoplay.js": ("stopAllAutoplay",),
    "web/core/cards.js": ("renderCardGroup",),
    "web/core/celebrate.js": ("BIG_GAIN_THRESHOLD", "MAX_COIN_COUNT", "CELEBRATION_DURATION_MS"),
    "web/core/dice.js": ("rollDie",),
    "web/core/motion.js": (
        "DEFAULT_MOTION_LIFECYCLE_EVENTS",
        "MOTION_PHASES",
        "createMotionLifecycle",
        "createMotionTimingProfile",
        "resolveMotionDuration",
    ),
    "web/core/ui.js": ("signedMoney",),
    "web/core/voice.js": ("voiceSettingsHtml", "bindVoiceSettings"),
}


# Prove dead compatibility artifacts and exports cannot silently return.
class DeadArtifactTests(unittest.TestCase):
    # Require one canonical requirements aggregate and no misleading top-level snapshot.
    def test_requirements_inventory_has_one_canonical_json(self) -> None:
        # Reject the obsolete year-old top-level snapshot.
        self.assertFalse((ROOT / "docs" / "requirements.json").exists())
        # Preserve the assembled canonical aggregate used by validation and tooling.
        self.assertTrue((ROOT / "docs" / "requirements" / "requirements.json").is_file())
        # Search tracked text sources for a stale pointer without reading generated compatibility output.
        stale_references = []
        # Inspect the human-owned requirement source and task notes where stale pointers previously lived.
        for path in (ROOT / "docs" / "requirements" / "requirements-spine.json", ROOT / "codex" / "tasks" / "auth-mysql-token-requirements-contracts.md"):
            # Record the exact relative path when obsolete inventory ownership returns.
            if "docs/requirements.json" in path.read_text(encoding="utf-8"):
                stale_references.append(path.relative_to(ROOT).as_posix())
        # Fail with the complete bounded file list rather than a bare count.
        self.assertEqual(stale_references, [])

    # Require the misleading no-op scope checker to remain deleted.
    def test_placeholder_scope_checker_is_absent(self) -> None:
        # Reject a file whose historical behavior printed one placeholder line and exited successfully.
        self.assertFalse((ROOT / "scripts" / "check_pr_scope.py").exists())

    # Require every audited production-unused JavaScript symbol to stay outside the public module surface.
    def test_unused_javascript_exports_are_absent(self) -> None:
        # Collect all forbidden export declarations with path and symbol diagnostics.
        violations = []
        # Inspect each explicitly reviewed module rather than applying a fragile repository-wide heuristic.
        for relative_path, symbols in REMOVED_EXPORTS.items():
            # Read the exact production source once for all symbols in this module.
            source = (ROOT / relative_path).read_text(encoding="utf-8")
            # Check every retired name against function, class, and variable export declarations.
            for symbol in symbols:
                # Match only a real named export declaration and ignore comments or ordinary internal use.
                pattern = rf"\bexport\s+(?:async\s+)?(?:function|class|const|let|var)\s+{re.escape(symbol)}\b"
                # Preserve exact diagnostics when a retired surface is reintroduced.
                if re.search(pattern, source):
                    violations.append(f"{relative_path}:{symbol}")
        # Reject the sorted complete violation inventory.
        self.assertEqual(sorted(violations), [])


# Execute this focused suite directly for ticket evidence.
if __name__ == "__main__":
    # Preserve standard unittest exit behavior for CI and local validation.
    unittest.main()
