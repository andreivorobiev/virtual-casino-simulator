"""Focused governance tests for per-game requirement source assembly."""

# Import JSON support for tracked source-union assertions.
import json
# Import temporary directories for isolated malformed-source fixtures.
import tempfile
# Import unittest for dependency-free focused checks.
import unittest
# Import paths for fixture and repository files.
from pathlib import Path

# Import the source assembler through its public validation seams.
from scripts import assemble_requirements

# Resolve the repository root from this focused test module.
ROOT = Path(__file__).resolve().parents[1]


# Prove the tracked registry and isolated fail-closed ownership behavior.
class RequirementsShardingTests(unittest.TestCase):
    # Require every tracked game source to assemble to the exact compatibility aggregate.
    def test_tracked_aggregate_is_exact_source_union(self):
        # Load descriptor-derived game ownership.
        descriptors = assemble_requirements.load_game_descriptors(ROOT)
        # Require one independently owned source for every catalog game.
        self.assertEqual(
            {descriptor["id"] for descriptor in descriptors},
            {path.stem for path in (ROOT / "docs" / "requirements" / "games").glob("*.json")},
        )
        # Build the semantic source union.
        expected = assemble_requirements.build_aggregate(ROOT)
        # Parse the generated compatibility aggregate.
        current = json.loads(
            (ROOT / "docs" / "requirements" / "requirements.json").read_text(encoding="utf-8")
        )
        # Require exact semantic identity in addition to the command's byte gate.
        self.assertEqual(expected, current)
        # Require byte-exact source synchronization.
        self.assertTrue(assemble_requirements.synchronize(ROOT, write=False))

    # Reject a requirement placed in a shard that does not own its permanent prefix.
    def test_wrong_game_shard_fails_closed(self):
        # Create one isolated repository-shaped fixture.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the disposable root.
            root = Path(temporary_directory)
            # Create required module and requirement directories.
            (root / "modules").mkdir(parents=True)
            # Create the independent game source directory.
            (root / "docs" / "requirements" / "games").mkdir(parents=True)
            # Write one minimal descriptor that owns only FIXTURE.
            (root / "modules" / "fixture.json").write_text(
                json.dumps(
                    {
                        "module": "fixture",
                        "requirements_prefixes": ["FIXTURE"],
                        "game": {"id": "fixture", "sort_order": 1},
                    }
                ),
                encoding="utf-8",
            )
            # Write one valid non-game spine.
            (root / "docs" / "requirements" / "requirements-spine.json").write_text(
                json.dumps(
                    {
                        "source_baseline": "fixture",
                        "created_at": "fixture",
                        "requirements": [],
                    }
                ),
                encoding="utf-8",
            )
            # Put an unrelated prefix into the game-owned shard deliberately.
            (root / "docs" / "requirements" / "games" / "fixture.json").write_text(
                json.dumps(
                    {
                        "game": "fixture",
                        "requirements_prefixes": ["FIXTURE"],
                        "requirements": [
                            {
                                "id": "OTHER-001",
                                "module": "Other",
                                "description": "Invalid fixture ownership.",
                                "status": "PASS",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            # Require the assembler to reject cross-shard ownership drift.
            with self.assertRaisesRegex(ValueError, "OTHER-001 is not owned by fixture"):
                # Attempt assembly from the malformed source fixture.
                assemble_requirements.build_aggregate(root)


# Run focused tests directly when invoked outside the repository runner.
if __name__ == "__main__":
    # Delegate reporting and exit status to unittest.
    unittest.main()
