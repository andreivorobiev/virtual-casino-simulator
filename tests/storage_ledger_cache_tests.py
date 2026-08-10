# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Prove the JSON ledger tail cache stays byte-identical to full re-parses. (issue #412)
# Import required dependency so tests can serialize seeded ledger rows exactly like the provider.
import json
# Import required dependency so test data can be written outside the real data directory.
import tempfile
# Import required dependency so bootstrap races can be exercised from two threads.
import threading
# Import required dependency so the cache and bootstrap suites run under the standard runner.
import unittest
# Import required dependency so two bootstrap callers can overlap deterministically.
from concurrent.futures import ThreadPoolExecutor
# Import required dependency so isolated JSON provider paths are platform-safe.
from pathlib import Path

# Import the default player document used by production bootstrap callers.
from casino.core import players
# Import the storage module under test for provider construction and injection.
from casino.core import storage


# Build one realistic seeded ledger event for raw JSONL fixtures.
def _seed_row(ledger_id: str, player_id: str, index: int) -> dict:
    # Return the production event field shape so filtering semantics stay representative.
    return {"ledger_id": ledger_id, "player_id": player_id, "amount": -1.0, "transaction_type": "TEST_SEED", "balance_before": 100.0 + index, "balance_after": 99.0 + index, "game": "storage", "round_id": f"seed_{index}", "details": {"index": index}, "created_at": "2026-07-27T00:00:00.000Z"}


# Serialize one event exactly like JsonStorageProvider._append_jsonl does.
def _seed_line(event: dict) -> bytes:
    # Encode the sorted single-line JSON row with a plain newline terminator.
    return (json.dumps(event, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


# Group cache-equivalence proofs for the incremental JSON ledger reader. (issue #412)
class LedgerCacheEquivalenceTests(unittest.TestCase):
    # Create one isolated data root per test so no shared state leaks between cases.
    def setUp(self):
        # Build a disposable directory removed automatically after the test.
        self._tmp = tempfile.TemporaryDirectory()
        # Register cleanup so Windows handles release even on assertion failures.
        self.addCleanup(self._tmp.cleanup)
        # Store the provider data root used by every provider instance in the test.
        self.data_root = Path(self._tmp.name) / "data"

    # Write raw ledger bytes so fixtures control malformed content precisely.
    def _write_ledger(self, payload: bytes) -> None:
        # Create the provider directory layout before writing the fixture file.
        storage.JsonStorageProvider(self.data_root).ensure_ready()
        # Write the exact fixture bytes without any newline translation.
        (self.data_root / "ledger.jsonl").write_bytes(payload)

    # Append raw bytes to the ledger fixture without newline translation.
    def _append_ledger(self, payload: bytes) -> None:
        # Open the append-only fixture file in binary mode.
        with (self.data_root / "ledger.jsonl").open("ab") as handle:
            # Append the exact bytes used by the scenario.
            handle.write(payload)

    # Build the standard two-player fixture with one malformed and one identity-free line.
    def _seed_standard_ledger(self) -> list[dict]:
        # Build the valid rows interleaved across both players.
        rows = [_seed_row("L1", "p1", 0), _seed_row("L2", "p2", 1), _seed_row("L3", "p1", 2), _seed_row("L4", "p2", 3)]
        # Serialize the first two valid rows before the corrupted region.
        payload = _seed_line(rows[0]) + _seed_line(rows[1])
        # Insert one malformed line that both readers must skip.
        payload += b"{not-valid-json\n"
        # Insert one valid JSON dictionary without a ledger identity that both readers must drop.
        payload += b'{"note": "identity-free row"}\n'
        # Serialize the remaining valid rows after the corrupted region.
        payload += _seed_line(rows[2]) + _seed_line(rows[3])
        # Persist the complete fixture bytes.
        self._write_ledger(payload)
        # Return the valid rows for direct expectations.
        return rows

    # Verify a warmed cached instance matches a freshly-constructed provider for every combination.
    def test_cached_reads_match_fresh_provider(self):
        # Seed the mixed-content fixture shared by both readers.
        rows = self._seed_standard_ledger()
        # Build the instance whose cache will be warmed across repeated reads.
        warmed = storage.JsonStorageProvider(self.data_root)
        # Warm the incremental cache with one initial full parse.
        warmed.read_ledger_recent(None, 1_000_000)
        # Check every requested limit against the cache-free baseline.
        for limit in (1, 100, 1_000_000):
            # Check every player filter used by history views.
            for player_id in (None, "p1", "p2"):
                # Name the combination so a failure identifies the exact case.
                with self.subTest(limit=limit, player_id=player_id):
                    # Read through the warmed instance-level cache.
                    cached = warmed.read_ledger_recent(player_id, limit)
                    # Read through a freshly-constructed provider with an empty cache.
                    fresh = storage.JsonStorageProvider(self.data_root).read_ledger_recent(player_id, limit)
                    # Require byte-identical row sets, order, and filtering.
                    self.assertEqual(fresh, cached)
        # Verify the malformed and identity-free lines were skipped with append order preserved.
        self.assertEqual(["L1", "L3"], [event["ledger_id"] for event in warmed.read_ledger_recent("p1", 100)])
        # Verify the unfiltered view exposes all four valid rows in commit order.
        self.assertEqual([row["ledger_id"] for row in rows], [event["ledger_id"] for event in warmed.read_ledger_recent(None, 100)])

    # Verify an unterminated trailing line keeps warmed and fresh readers identical.
    def test_unterminated_trailing_line_matches_fresh_provider(self):
        # Seed the standard terminated fixture first.
        self._seed_standard_ledger()
        # Build and warm the cached instance over the terminated rows.
        warmed = storage.JsonStorageProvider(self.data_root)
        # Warm the incremental cache before the partial write appears.
        warmed.read_ledger_recent(None, 1_000_000)
        # Append one valid row without its newline to model a crash mid-append.
        self._append_ledger(_seed_line(_seed_row("L5", "p1", 4)).rstrip(b"\n"))
        # Require the warmed reader to include the unterminated row like a full re-parse does.
        self.assertEqual(["L1", "L3", "L5"], [event["ledger_id"] for event in warmed.read_ledger_recent("p1", 100)])
        # Require the warmed and fresh readers to agree while the partial line exists.
        self.assertEqual(storage.JsonStorageProvider(self.data_root).read_ledger_recent(None, 100), warmed.read_ledger_recent(None, 100))
        # Append a terminated row that merges into the unterminated line exactly like a real append would.
        self._append_ledger(_seed_line(_seed_row("L6", "p1", 5)))
        # Read the merged state through the warmed cache.
        cached = warmed.read_ledger_recent(None, 100)
        # Read the merged state through a cache-free provider.
        fresh = storage.JsonStorageProvider(self.data_root).read_ledger_recent(None, 100)
        # Require both readers to agree after the merge corrupted the shared physical line.
        self.assertEqual(fresh, cached)
        # Require the merged physical line to be skipped by both readers as one malformed row.
        self.assertEqual(["L1", "L2", "L3", "L4"], [event["ledger_id"] for event in cached])

    # Verify a second provider instance's append invalidates the first instance's cache by stat.
    def test_external_append_is_visible_to_warmed_instance(self):
        # Build the first provider whose cache will be warmed.
        first = storage.JsonStorageProvider(self.data_root)
        # Seed the default player document so ledger transactions can settle.
        first.bootstrap_players(players.default_players())
        # Warm the first instance's cache over the empty ledger.
        self.assertEqual([], first.read_ledger_recent("human", 100))
        # Build a second independent provider instance over the same directory.
        second = storage.JsonStorageProvider(self.data_root)
        # Append one production ledger row through the second instance only.
        event = second.transact_ledger("human", -5, "TEST_EXTERNAL_DEBIT", "storage", "round_external", {"writer": "second"})
        # Require the first warmed instance to observe the externally appended row.
        self.assertEqual([event["ledger_id"]], [row["ledger_id"] for row in first.read_ledger_recent("human", 100)])
        # Require the unfiltered warmed view to observe the same appended row.
        self.assertEqual([event["ledger_id"]], [row["ledger_id"] for row in first.read_ledger_recent(None, 100)])

    # Verify reset clears the cache so no pre-reset rows survive truncation.
    def test_reset_returns_empty_ledger(self):
        # Seed rows so the cache holds real content before the reset.
        self._seed_standard_ledger()
        # Build the provider whose cache will be warmed then reset.
        provider = storage.JsonStorageProvider(self.data_root)
        # Warm the cache with the seeded rows.
        self.assertEqual(4, len(provider.read_ledger_recent(None, 100)))
        # Reset the provider so the data directory and all caches are cleared.
        provider.reset()
        # Require the unfiltered read to return no rows after the reset.
        self.assertEqual([], provider.read_ledger_recent(None, 100))
        # Require the player-filtered read to return no rows after the reset.
        self.assertEqual([], provider.read_ledger_recent("p1", 5))

    # Verify sequential wallet actions parse only appended lines instead of the whole file.
    def test_sequential_actions_avoid_full_reparse(self):
        # Build the provider that executes the sequential actions.
        provider = storage.JsonStorageProvider(self.data_root)
        # Seed the default player document so debits can settle.
        provider.bootstrap_players(players.default_players())
        # Append ten ordinary rows so a full re-parse would be clearly visible in the counter.
        for index in range(10):
            # Append one production debit row.
            provider.transact_ledger("human", -1, "TEST_WARM_DEBIT", "storage", f"warm_{index}", {"index": index})
        # Warm the cache with one full parse before counting begins.
        self.assertEqual(10, len(provider.read_ledger_recent("human", 1_000_000)))
        # Collect every line decode so full re-parses become measurable without timing.
        decoded_lines = []
        # Keep the production decoder for delegation.
        original_decode = provider._decode_ledger_line
        # Define the counting wrapper installed on this instance only.
        def counting_decode(line):
            # Record the decoded line before delegating.
            decoded_lines.append(line)
            # Delegate to the production decoder unchanged.
            return original_decode(line)
        # Install the counting wrapper for the measured window.
        provider._decode_ledger_line = counting_decode
        # Execute fifty distinct idempotent wallet actions on the warmed instance.
        for index in range(50):
            # Execute one new action identity that must append exactly one row.
            event, replayed = provider.transact_ledger_once("human", -1, "TEST_ONCE_DEBIT", f"perf-key-{index}", "storage", f"once_{index}", {"index": index})
            # Require a fresh commit rather than a replay for every distinct key.
            self.assertFalse(replayed)
        # Read the final state so the last appended row is also decoded once.
        self.assertEqual(60, len(provider.read_ledger_recent("human", 1_000_000)))
        # Require at most one decode per appended row so at most one full-file parse could have happened.
        self.assertLessEqual(len(decoded_lines), 55)


# Group bootstrap provisioning race proofs for the seeded player path. (issue #431)
class BootstrapPlayersRaceTests(unittest.TestCase):
    # Create one isolated data root per test so no shared state leaks between cases.
    def setUp(self):
        # Build a disposable directory removed automatically after the test.
        self._tmp = tempfile.TemporaryDirectory()
        # Register directory cleanup for every outcome.
        self.addCleanup(self._tmp.cleanup)
        # Always clear injected providers even when assertions fail.
        self.addCleanup(storage.set_provider_for_tests, None)

    # Inject one isolated provider under the given subdirectory name.
    def _inject_provider(self, name: str) -> storage.JsonStorageProvider:
        # Build the isolated provider for this scenario.
        provider = storage.JsonStorageProvider(Path(self._tmp.name) / name)
        # Route bootstrap_players through the isolated provider.
        storage.set_provider_for_tests(provider)
        # Return the provider for direct assertions.
        return provider

    # Read the sorted player identifiers currently persisted by the provider.
    def _player_ids(self, provider: storage.JsonStorageProvider) -> list[str]:
        # Load the document and project the identifier column in stored order.
        return [row["player_id"] for row in provider.load_players(players.default_players)["players"]]

    # Verify repeated sequential bootstraps never duplicate or clobber players.
    def test_bootstrap_twice_is_idempotent(self):
        # Inject an isolated provider for the sequential scenario.
        provider = self._inject_provider("sequential")
        # Bootstrap the fresh directory once.
        storage.bootstrap_players(players.default_players)
        # Bootstrap again to model a second process repeating the seed check.
        storage.bootstrap_players(players.default_players)
        # Require exactly the default players with no duplicates.
        self.assertEqual(sorted(["human", "bot_1", "bot_2", "bot_3"]), sorted(self._player_ids(provider)))
        # Mutate one wallet so a later bootstrap would reveal any whole-document clobber.
        provider.update_player("human", lambda row: row.update(balance=123.45))
        # Bootstrap a third time against the populated directory.
        storage.bootstrap_players(players.default_players)
        # Require the mutated balance to survive because seeding never rewrites existing rows.
        self.assertEqual(123.45, next(row["balance"] for row in provider.load_players(players.default_players)["players"] if row["player_id"] == "human"))

    # Verify two overlapped bootstraps on a fresh directory stay duplicate-free and error-free.
    def test_bootstrap_race_from_two_threads(self):
        # Inject an isolated provider for the concurrent scenario.
        provider = self._inject_provider("race")
        # Build a barrier so both threads pass the has-players check as closely as possible.
        barrier = threading.Barrier(2)
        # Define one racing bootstrap participant.
        def race():
            # Hold both threads at the same start line.
            barrier.wait(timeout=10)
            # Run the production bootstrap path under contention.
            storage.bootstrap_players(players.default_players)
        # Run both participants concurrently so any raced exception fails the test.
        with ThreadPoolExecutor(max_workers=2) as pool:
            # Materialize both results so raised exceptions propagate.
            for future in [pool.submit(race), pool.submit(race)]:
                # Surface any provisioning exception from either thread.
                future.result(timeout=30)
        # Read the resulting player identifiers.
        player_ids = self._player_ids(provider)
        # Require no duplicated identifiers from the overlapped provisioning.
        self.assertEqual(len(player_ids), len(set(player_ids)))
        # Require exactly the default player set.
        self.assertEqual(sorted(["human", "bot_1", "bot_2", "bot_3"]), sorted(player_ids))


# Allow direct execution for local debugging without the shared runner.
if __name__ == "__main__":
    # Run the module's tests through the standard unittest entry point.
    unittest.main()
