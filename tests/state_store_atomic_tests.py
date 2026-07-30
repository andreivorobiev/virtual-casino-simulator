# Import JSON decoding so tests can compare the complete persisted document.
import json
# Import temporary-directory support so tests never touch repository runtime state.
import tempfile
# Import bounded timing to widen concurrency interleavings inside the protected mutation.
import time
# Import unittest as the repository's listener-free focused test framework.
import unittest
# Import a thread pool so concurrent callers exercise the shared atomic boundary.
from concurrent.futures import ThreadPoolExecutor
# Import paths so each test can bind state_store to its disposable data root.
from pathlib import Path
# Import patch helpers so storage selection and timestamps remain deterministic.
from unittest.mock import patch

# Import the module under test so its runtime directory bindings can be isolated.
from casino.core import state_store


# Simulate the public MySQL document boundary without opening a database connection.
class _AtomicProvider:
    # Initialize one provider document and a call ledger for delegation assertions.
    def __init__(self, current):
        # Copy the initial object so tests own an independent expected value.
        self.current = dict(current) if isinstance(current, dict) else current
        # Record every stable provider key received through state_store.update_json.
        self.keys = []

    # Apply one transaction-shaped document mutation and publish only after success.
    def update_document(self, key, mutator, default):
        # Record the key before evaluating the provider-owned transaction.
        self.keys.append(key)
        # Evaluate the lazy default only when the provider document is absent.
        source = default() if self.current is None else self.current
        # Copy the decoded document so a failed mutator cannot alter committed provider state.
        working = json.loads(json.dumps(source))
        # Apply the supplied transition before assigning any new committed state.
        updated = mutator(working)
        # Publish only the complete successful result, mirroring provider commit timing.
        self.current = json.loads(json.dumps(updated))
        # Return an independent decoded copy to the caller.
        return json.loads(json.dumps(self.current))


# Verify player-scoped atomic state updates without routes, games, or listeners.
class PlayerGameStateAtomicTests(unittest.TestCase):
    # Bind every state_store runtime directory to one disposable JSON-provider root.
    def setUp(self):
        # Create a disposable root that is removed after every regression.
        self.temporary_directory = tempfile.TemporaryDirectory()
        # Resolve the temporary root once for readable path assertions.
        self.root = Path(self.temporary_directory.name)
        # Assign the provider data root below the disposable directory.
        self.data_dir = self.root / "data"
        # Assign the game-state root below the provider data root.
        self.game_data_dir = self.data_dir / "games"
        # Assign the log root outside provider documents but inside the disposable directory.
        self.log_dir = self.root / "logs"
        # Patch the imported data root used by provider-key resolution.
        self.data_patch = patch.object(state_store, "DATA_DIR", self.data_dir)
        # Patch the imported game root used by player and legacy paths.
        self.game_patch = patch.object(state_store, "GAME_DATA_DIR", self.game_data_dir)
        # Patch the imported log root used by ensure_dirs.
        self.log_patch = patch.object(state_store, "LOG_DIR", self.log_dir)
        # Force the default provider so focused tests never inspect developer configuration.
        self.provider_patch = patch.object(state_store, "storage_provider_name", return_value="json")
        # Start every directory and provider patch before invoking state_store.
        self.data_patch.start()
        # Start the player-game directory patch.
        self.game_patch.start()
        # Start the disposable log directory patch.
        self.log_patch.start()
        # Start the explicit JSON-provider selection patch.
        self.provider_patch.start()

    # Restore module bindings and delete disposable runtime state after every regression.
    def tearDown(self):
        # Restore provider selection before releasing temporary paths.
        self.provider_patch.stop()
        # Restore the imported log directory.
        self.log_patch.stop()
        # Restore the imported game-state directory.
        self.game_patch.stop()
        # Restore the imported provider data directory.
        self.data_patch.stop()
        # Delete all disposable files after state_store no longer references them.
        self.temporary_directory.cleanup()

    # Prove absent-state defaults are lazy and successful updates retain save-compatible metadata.
    def test_lazy_default_and_success_metadata(self):
        # Count default evaluations so existing documents can prove the factory stays lazy.
        default_calls = []

        # Return one fresh default object while recording the evaluation.
        def default_factory():
            # Record this factory evaluation without sharing the returned state object.
            default_calls.append("called")
            # Return the initial player-scoped counter state.
            return {"count": 0}

        # Increment the current counter and return the complete updated state.
        def increment(current):
            # Prove callers receive the same schema default as load_player_game_state.
            self.assertEqual(state_store.SCHEMA_VERSION, current["schema_version"])
            # Increment the counter inside the provider-owned atomic callback.
            current["count"] += 1
            # Return the complete document required by the mutation contract.
            return current

        # Freeze update metadata so exact persisted equality remains deterministic.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T10:00:00Z"):
            # Create and atomically mutate the absent player state.
            created = state_store.update_player_game_state("demo", "player-1", increment, default_factory)
        # Confirm the absent document evaluated its default exactly once.
        self.assertEqual(["called"], default_calls)
        # Confirm the successful result contains the caller's state transition.
        self.assertEqual(1, created["count"])
        # Confirm schema normalization matches the existing save helper.
        self.assertEqual(state_store.SCHEMA_VERSION, created["schema_version"])
        # Confirm successful updates carry the existing save-compatible timestamp.
        self.assertEqual("2026-07-28T10:00:00Z", created["updated_at"])
        # Resolve the exact player-scoped JSON path for persisted equality.
        path = state_store.player_game_state_path("demo", "player-1")
        # Confirm the complete returned document is the complete persisted document.
        self.assertEqual(created, json.loads(path.read_text(encoding="utf-8")))

        # Fail loudly if an existing document incorrectly evaluates its default factory.
        def forbidden_default():
            # Signal that lazy default behavior regressed.
            raise AssertionError("existing state must not evaluate its default")

        # Freeze the second update timestamp independently.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T10:01:00Z"):
            # Reuse the existing document without calling the forbidden default.
            updated = state_store.update_player_game_state("demo", "player-1", increment, forbidden_default)
        # Confirm the existing state participated in the second atomic mutation.
        self.assertEqual(2, updated["count"])

    # Prove concurrent JSON callers serialize complete state transitions without lost writes.
    def test_json_concurrency_preserves_every_update(self):
        # Define enough distinct updates to expose a load-then-save lost-write regression.
        update_ids = list(range(24))

        # Build one default object for the first caller that reaches the absent document.
        def default_factory():
            # Return independent mutable collections for the initial state.
            return {"count": 0, "seen": []}

        # Apply one distinct update after a short delay that widens thread interleaving.
        def apply_update(update_id):
            # Build the provider-owned mutation closure for this distinct update.
            def mutate(current):
                # Hold the mutation briefly so unlocked implementations overlap.
                time.sleep(0.002)
                # Increment the aggregate counter.
                current["count"] += 1
                # Append the unique update identity.
                current["seen"].append(update_id)
                # Return the complete updated object.
                return current

            # Execute one player-scoped atomic update.
            return state_store.update_player_game_state("demo", "concurrent", mutate, default_factory)

        # Freeze metadata while worker threads execute deterministic state transitions.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T11:00:00Z"):
            # Run more calls than workers so serialization spans multiple scheduling waves.
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Materialize every result so worker exceptions cannot be ignored.
                results = list(executor.map(apply_update, update_ids))
        # Confirm every caller completed successfully.
        self.assertEqual(len(update_ids), len(results))
        # Load the final state through the established player-scoped read helper.
        final_state = state_store.load_player_game_state("demo", "concurrent", default_factory)
        # Confirm no concurrent increment was lost.
        self.assertEqual(len(update_ids), final_state["count"])
        # Confirm every unique transition survived exactly once.
        self.assertEqual(update_ids, sorted(final_state["seen"]))

    # Prove a failed JSON mutation leaves the complete original document byte-identical.
    def test_json_mutator_exception_performs_no_write(self):
        # Seed an existing player-scoped state through the established save helper.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T12:00:00Z"):
            # Persist one recognizable baseline document.
            state_store.save_player_game_state("demo", "rollback", {"count": 7, "nested": {"safe": True}})
        # Resolve the exact persisted path before attempting the failing mutation.
        path = state_store.player_game_state_path("demo", "rollback")
        # Capture original bytes so formatting changes and partial writes are detectable.
        original_bytes = path.read_bytes()

        # Mutate the decoded object and then fail before provider publication.
        def fail_after_mutation(current):
            # Change both a scalar and nested object to test deep rollback behavior.
            current["count"] = 99
            # Change the nested payload before raising.
            current["nested"]["safe"] = False
            # Raise the caller-owned failure that must abort the atomic write.
            raise RuntimeError("stop before write")

        # Confirm the caller's exception propagates without normalization.
        with self.assertRaisesRegex(RuntimeError, "stop before write"):
            # Attempt the failing mutation against the existing document.
            state_store.update_player_game_state("demo", "rollback", fail_after_mutation, lambda: {"count": 0})
        # Confirm the original JSON bytes remain exact after rollback.
        self.assertEqual(original_bytes, path.read_bytes())
        # Confirm no temporary publication file remains after the failed callback.
        self.assertFalse(path.with_suffix(path.suffix + ".tmp").exists())

    # Prove non-human players mutate independent documents through the same path sanitizer.
    def test_non_human_player_states_remain_isolated(self):
        # Return one fresh default counter for every absent player document.
        def default_factory():
            # Keep each player's starting state independently allocated.
            return {"count": 0}

        # Increment one player's current counter.
        def increment(current):
            # Advance only the document selected for this callback.
            current["count"] += 1
            # Return the complete player state.
            return current

        # Freeze metadata while two non-human identities are updated independently.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T12:30:00Z"):
            # Apply two updates to the first non-human player.
            state_store.update_player_game_state("demo", "player:alpha", increment, default_factory)
            # Apply the second update to the same sanitized first-player path.
            state_store.update_player_game_state("demo", "player:alpha", increment, default_factory)
            # Apply one update to a distinct non-human player.
            state_store.update_player_game_state("demo", "player:beta", increment, default_factory)
        # Load the first non-human player's independent state.
        alpha = state_store.load_player_game_state("demo", "player:alpha", default_factory)
        # Load the second non-human player's independent state.
        beta = state_store.load_player_game_state("demo", "player:beta", default_factory)
        # Confirm the first player's two updates were retained.
        self.assertEqual(2, alpha["count"])
        # Confirm the second player received only its own update.
        self.assertEqual(1, beta["count"])
        # Confirm the established sanitizer still produces distinct player paths.
        self.assertNotEqual(
            state_store.player_game_state_path("demo", "player:alpha"),
            state_store.player_game_state_path("demo", "player:beta"),
        )

    # Prove the historical global-human document seeds the first atomic player-scoped update.
    def test_legacy_human_fallback_is_preserved_without_rewriting_legacy_state(self):
        # Seed the historical global game document through the established helper.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T13:00:00Z"):
            # Persist a recognizable legacy human state.
            state_store.save_game_state("demo", {"credits": 40, "rounds": 2})
        # Resolve both the historical and modern player-scoped paths.
        legacy_path = state_store.game_state_path("demo")
        # Resolve the modern player-scoped human path.
        player_path = state_store.player_game_state_path("demo", "human")
        # Capture the legacy bytes before the first player-scoped mutation.
        legacy_bytes = legacy_path.read_bytes()
        # Confirm the modern player-scoped document is genuinely absent.
        self.assertFalse(player_path.exists())

        # Advance the legacy-derived state inside the new atomic boundary.
        def advance(current):
            # Consume the legacy value to prove it was used as the absent-document seed.
            current["credits"] += 5
            # Increment the legacy round counter.
            current["rounds"] += 1
            # Return the complete advanced state.
            return current

        # Freeze the new player document timestamp.
        with patch.object(state_store, "utc_now", return_value="2026-07-28T13:01:00Z"):
            # Atomically create player-scoped human state from the legacy fallback.
            result = state_store.update_player_game_state("demo", "human", advance, lambda: {"credits": 0, "rounds": 0})
        # Confirm the first update began from legacy human state.
        self.assertEqual(45, result["credits"])
        # Confirm the legacy round value was advanced.
        self.assertEqual(3, result["rounds"])
        # Confirm the modern player-scoped document was created.
        self.assertTrue(player_path.exists())
        # Confirm the legacy source remains byte-identical for compatibility and recovery.
        self.assertEqual(legacy_bytes, legacy_path.read_bytes())
        # Confirm subsequent player-scoped reads prefer the newly created document.
        self.assertEqual(result, state_store.load_player_game_state("demo", "human", lambda: {}))

    # Prove MySQL selection delegates the complete mutation and preserves rollback ownership.
    def test_mysql_delegation_and_failed_mutation_preserve_committed_state(self):
        # Seed a fake committed provider document with recognizable nested state.
        provider = _AtomicProvider({"count": 4, "nested": {"safe": True}})

        # Increment one existing provider document inside the delegated callback.
        def increment(current):
            # Increment the committed provider counter.
            current["count"] += 1
            # Return the complete updated document.
            return current

        # Route state_store through the fake MySQL public boundary for this regression.
        with patch.object(state_store, "storage_provider_name", return_value="mysql"):
            # Return the fake provider whenever update_json resolves the selected backend.
            with patch.object(state_store, "get_storage_provider", return_value=provider):
                # Freeze provider-published metadata.
                with patch.object(state_store, "utc_now", return_value="2026-07-28T14:00:00Z"):
                    # Execute one successful delegated mutation.
                    result = state_store.update_player_game_state("demo", "mysql-player", increment, lambda: {"count": 0})
        # Confirm delegation used the stable data-relative provider document key.
        self.assertEqual(["games/demo/mysql-player.json"], provider.keys)
        # Confirm the provider committed the successful mutation.
        self.assertEqual(5, result["count"])
        # Confirm MySQL mode did not create a hybrid local JSON document.
        self.assertFalse(state_store.player_game_state_path("demo", "mysql-player").exists())
        # Capture the complete committed provider state before the failing transaction.
        committed = json.loads(json.dumps(provider.current))

        # Mutate provider-owned decoded state and then fail before provider commit.
        def fail_after_mutation(current):
            # Change the scalar value inside the transaction copy.
            current["count"] = 500
            # Change the nested value inside the transaction copy.
            current["nested"]["safe"] = False
            # Abort the transaction-shaped callback.
            raise RuntimeError("rollback provider update")

        # Route the failing update through the same public provider boundary.
        with patch.object(state_store, "storage_provider_name", return_value="mysql"):
            # Reuse the same committed fake provider.
            with patch.object(state_store, "get_storage_provider", return_value=provider):
                # Confirm the provider-owned failure propagates to the caller.
                with self.assertRaisesRegex(RuntimeError, "rollback provider update"):
                    # Attempt the failing delegated mutation.
                    state_store.update_player_game_state("demo", "mysql-player", fail_after_mutation, lambda: {})
        # Confirm the provider committed state remains exact after callback failure.
        self.assertEqual(committed, provider.current)
        # Confirm both attempts delegated through the same stable document key.
        self.assertEqual(
            ["games/demo/mysql-player.json", "games/demo/mysql-player.json"],
            provider.keys,
        )


# Run this listener-free regression file directly during the source checkpoint.
if __name__ == "__main__":
    # Execute unittest with verbose names so checkpoint evidence is auditable.
    unittest.main(verbosity=2)
