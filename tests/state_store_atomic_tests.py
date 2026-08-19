# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
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
# Import the production JSON provider so facade tests exercise provider-owned filesystem locking.
from casino.core.storage import JsonStorageProvider


# Simulate the public MySQL document boundary without opening a database connection.
class _AtomicProvider:
    # Initialize one provider document and a call ledger for delegation assertions.
    def __init__(self, current):
        # Copy the initial object so tests own an independent expected value.
        self.current = dict(current) if isinstance(current, dict) else current
        # Record every stable provider key received through state_store.update_json.
        self.keys = []
        # Record every provider operation so facade parity is explicit.
        self.operations = []

    # Convert one state path into the same stable key used by the production database provider.
    def document_reference(self, path, data_root):
        # Return the portable data-relative key or fail closed for an arbitrary local path.
        return Path(path).resolve().relative_to(Path(data_root).resolve()).as_posix()

    # Return the current provider document or the caller's lazy default.
    def read_document(self, key, default):
        # Record the exact public operation and canonical key.
        self.operations.append(("read", key))
        # Preserve lazy default construction for an absent document.
        source = default() if self.current is None and callable(default) else (default if self.current is None else self.current)
        # Return an independent decoded copy just like a provider round trip.
        return json.loads(json.dumps(source))

    # Report whether the transaction-shaped fake currently owns a document.
    def document_exists(self, key):
        # Record the exact existence operation and canonical key.
        self.operations.append(("exists", key))
        # Return true only when committed provider state exists.
        return self.current is not None

    # Return one document through the strict provider seam and optional predicate.
    def read_document_strict(self, key, default, validator=None):
        # Record the exact strict operation and canonical key.
        self.operations.append(("read_strict", key))
        # Read the detached current or missing-document value without recording a second public call.
        source = default() if self.current is None and callable(default) else (default if self.current is None else self.current)
        # Copy the value so validation cannot mutate committed state.
        value = json.loads(json.dumps(source))
        # Reject a caller-invalid document through the provider's fixed boundary.
        if validator is not None and validator(value) is not True:
            # Match the provider-neutral recovery exception.
            raise RuntimeError("Stored document requires operator recovery")
        # Return the complete detached document.
        return value

    # Publish one complete provider document.
    def write_document(self, key, data):
        # Record the exact write operation and canonical key.
        self.operations.append(("write", key))
        # Persist an independent encoded copy.
        self.current = json.loads(json.dumps(data))

    # Apply one transaction-shaped document mutation and publish only after success.
    def update_document(self, key, mutator, default, validator=None):
        # Record the key before evaluating the provider-owned transaction.
        self.keys.append(key)
        # Record whether state_store selected ordinary or strict provider mutation.
        self.operations.append(("update_strict" if validator is not None else "update", key))
        # Evaluate the lazy default only when the provider document is absent.
        source = default() if self.current is None else self.current
        # Copy the decoded document so a failed mutator cannot alter committed provider state.
        working = json.loads(json.dumps(source))
        # Apply the strict predicate before caller mutation when state_store requested it.
        if validator is not None and validator(working) is not True:
            # Match the fixed provider recovery boundary.
            raise RuntimeError("Stored document requires operator recovery")
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
        # Construct the production JSON provider against the disposable data root.
        self.json_provider = JsonStorageProvider(data_dir=self.data_dir)
        # Force the provider object so focused tests never inspect developer configuration.
        self.provider_patch = patch.object(state_store, "get_storage_provider", return_value=self.json_provider)
        # Start every directory and provider patch before invoking state_store.
        self.data_patch.start()
        # Start the player-game directory patch.
        self.game_patch.start()
        # Start the disposable log directory patch.
        self.log_patch.start()
        # Start the explicit JSON-provider object patch.
        self.provider_patch.start()

    # Restore module bindings and delete disposable runtime state after every regression.
    def tearDown(self):
        # Restore provider resolution before releasing temporary paths.
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

    # Prove every public state_store document operation has provider-neutral results and stable keys. (STORAGE-018, TEST-247)
    def test_document_facade_parity_across_json_and_database_provider_shapes(self):
        # Select one ordinary data document whose exact suffix must remain unchanged.
        path = self.data_dir / "settings" / "facade-parity.json"

        # Exercise the complete public document surface against one selected provider.
        def run_sequence(provider):
            # Route every facade call through the supplied provider object.
            with patch.object(state_store, "get_storage_provider", return_value=provider):
                # Read one absent document through a lazy default.
                absent = state_store.read_json(path, lambda: {"count": 0})
                # Publish the first complete document.
                state_store.write_json(path, {"count": 1})
                # Read the published document through the ordinary seam.
                written = state_store.read_json(path, {})
                # Advance the document through the ordinary atomic seam.
                updated = state_store.update_json(path, lambda current: {"count": current["count"] + 1}, {})
                # Read the result through the strict seam.
                strict = state_store.read_json_strict(path, {}, "facade recovery")
                # Advance the result through the strict atomic seam.
                strict_updated = state_store.update_json_strict(path, lambda current: {"count": current["count"] + 1}, {}, "facade recovery")
            # Return each public result in call order for exact cross-provider comparison.
            return absent, written, updated, strict, strict_updated

        # Run the complete sequence against the production JSON provider.
        json_results = run_sequence(self.json_provider)
        # Remove JSON bytes so the database-shaped fake starts from the same absent state.
        path.unlink()
        # Construct a transaction-shaped database provider with no existing document.
        database_provider = _AtomicProvider(None)
        # Run the identical state_store call sequence through the database-shaped provider.
        database_results = run_sequence(database_provider)
        # Require identical caller-visible behavior across both providers.
        self.assertEqual(json_results, database_results)
        # Bind the exact sequence of delegated provider operations.
        self.assertEqual(
            ["read", "write", "read", "update", "read_strict", "update_strict"],
            [operation for operation, _key in database_provider.operations],
        )
        # Require every database call to use the same portable data-relative document key.
        self.assertEqual(
            ["settings/facade-parity.json"] * 6,
            [key for _operation, key in database_provider.operations],
        )

    # Prove injectable paths remain explicitly JSON-provider-managed and database providers fail closed. (STORAGE-018)
    def test_out_of_data_paths_are_json_managed_and_database_rejected(self):
        # Select one injected service path outside the configured application data root.
        external_path = self.root / "service-fixtures" / "mail.json"
        # Publish the injected file through the active JSON provider facade.
        state_store.write_json(external_path, {"status": "queued"})
        # Confirm the exact requested path was used without a duplicate .json suffix.
        self.assertEqual({"status": "queued"}, json.loads(external_path.read_text(encoding="utf-8")))
        # Confirm the JSON provider did not derive a hybrid path below its ordinary data root.
        self.assertFalse((self.data_dir / "service-fixtures" / "mail.json.json").exists())
        # Construct the database-shaped provider that permits only data-relative keys.
        database_provider = _AtomicProvider(None)
        # Route the same external path through the database boundary.
        with patch.object(state_store, "get_storage_provider", return_value=database_provider):
            # Refuse a local path that cannot be represented by the database document namespace.
            with self.assertRaises(ValueError):
                # Attempt no fallback filesystem read under database selection.
                state_store.read_json(external_path, {})
        # Confirm fail-closed containment occurred before any provider document operation.
        self.assertEqual([], database_provider.operations)

    # Prove strict facade translation preserves evidence and never rewrites caller failures. (STORAGE-018, TEST-247)
    def test_strict_facade_preserves_corrupt_bytes_and_caller_runtime_errors(self):
        # Select one provider-managed security document.
        path = self.data_dir / "auth" / "strict-facade.json"
        # Create its parent without invoking the provider writer that requires valid JSON.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Persist recognizable malformed bytes as operator-recovery evidence.
        path.write_bytes(b'{"broken":')
        # Capture exact source bytes before either strict operation.
        original = path.read_bytes()
        # Translate the provider's fixed strict-read boundary into the caller-owned message.
        with self.assertRaisesRegex(RuntimeError, "facade-specific recovery"):
            # Attempt a strict read without normalizing the malformed document.
            state_store.read_json_strict(path, {}, "facade-specific recovery")
        # Track whether an invalid document ever reaches the caller mutator.
        mutator_calls = []
        # Translate the provider's strict-update boundary before invoking caller code.
        with self.assertRaisesRegex(RuntimeError, "facade-specific recovery"):
            # Attempt a strict update that must fail before the callback.
            state_store.update_json_strict(path, lambda value: mutator_calls.append(value), {}, "facade-specific recovery")
        # Require no caller mutation and exact byte preservation across both failures.
        self.assertEqual(([], original), (mutator_calls, path.read_bytes()))
        # Replace the malformed fixture with one valid strict document.
        state_store.write_json(path, {"safe": True})

        # Raise one deliberate caller-owned RuntimeError after strict provider validation.
        def caller_failure(_current):
            # Preserve this distinct error text through the facade.
            raise RuntimeError("caller transition stopped")

        # Require the caller's failure rather than the storage recovery message.
        with self.assertRaisesRegex(RuntimeError, "caller transition stopped"):
            # Execute the failing callback inside the provider-owned strict transaction.
            state_store.update_json_strict(path, caller_failure, {}, "facade-specific recovery")
        # Confirm rollback kept the last valid document exact.
        self.assertEqual({"safe": True}, state_store.read_json(path, {}))

    # Prove state_store owns no backend selector or duplicate sidecar lock implementation. (STORAGE-018, TEST-247)
    def test_state_store_source_has_one_provider_route_and_no_sidecar_lock(self):
        # Read the exact source so accidental selector or lock reintroduction fails statically.
        source = Path(state_store.__file__).read_text(encoding="utf-8")
        # Require removal of the environment-name routing helper.
        self.assertNotIn("storage_provider_name", source)
        # Require removal of the duplicate state_store sidecar-lock implementation.
        self.assertNotIn("def _file_lock", source)
        # Require every public document operation plus existence to resolve the common provider seam.
        self.assertEqual(6, source.count("provider, document = _provider_document(path)"))

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

        # Return the fake provider whenever state_store resolves the selected backend.
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
