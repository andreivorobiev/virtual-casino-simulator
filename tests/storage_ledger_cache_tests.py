# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Prove the JSON ledger tail cache stays byte-identical to full re-parses. (issue #412)
# Import required dependency so tests can serialize seeded ledger rows exactly like the provider.
import json
# Import database-shaped decimals for MySQL point-read fixtures.
from decimal import Decimal
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
# Import the standard fail-closed error used for corrupt money-action journals.
from casino.errors import ConflictError


# Build one canonical CSV history event for incremental cache fixtures.
def _history_row(index: int, game: str = "slots") -> dict:
    # Return every required compatibility column as a CSV-safe scalar.
    return {"timestamp": f"2026-08-19T00:00:{index % 60:02d}Z", "game": game, "round_id": f"history_{index}", "player_id": "human", "bet_type": "straight", "bet_label": f"bet-{index}", "amount": "1.00", "outcome": "win", "payout": "2.00", "balance_after": "5000.00", "details_json": "{}", "schema_version": "8"}


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


# Group append-only money-action journal compatibility and scaling proofs. (LEDGER-034, TEST-169)
class LedgerActionJournalTests(unittest.TestCase):
    # Create one isolated provider root and funded wallet per test.
    def setUp(self):
        # Build a disposable directory removed automatically after each test.
        self._tmp = tempfile.TemporaryDirectory()
        # Register directory cleanup even when a fail-closed assertion raises.
        self.addCleanup(self._tmp.cleanup)
        # Store the isolated provider data root.
        self.data_root = Path(self._tmp.name) / "data"
        # Build the provider under test.
        self.provider = storage.JsonStorageProvider(self.data_root)
        # Seed the standard fake-money wallets before journal actions execute.
        self.provider.bootstrap_players(players.default_players())

    # Prove new actions use two bounded appends and never rewrite action history.
    def test_new_actions_never_rewrite_legacy_snapshot(self):
        # Preserve the provider's ordinary JSON writer for unrelated player projections.
        original_write = self.provider._write_json
        # Count only attempted writes to the retired whole-history action snapshot.
        snapshot_writes = []
        # Define a transparent writer wrapper for this provider instance.
        def counting_write(path, data):
            # Record writes that would reserialize every historical action.
            if path == self.provider.ledger_actions_path():
                # Retain the attempted payload for a useful failure count.
                snapshot_writes.append(data)
            # Delegate player and other compatible document writes unchanged.
            return original_write(path, data)
        # Install the scoped counting wrapper.
        self.provider._write_json = counting_write
        # Commit fifty distinct exactly-once actions to exercise a nontrivial history.
        for index in range(50):
            # Execute one fresh debit under a unique canonical action key.
            event, replayed = self.provider.transact_ledger_once("human", -1, "TEST_JOURNAL_DEBIT", f"journal-{index}", "storage", f"round-{index}", {"index": index})
            # Require every unique identity to commit once.
            self.assertFalse(replayed)
            # Require the returned event to retain its canonical ledger identity.
            self.assertTrue(event["ledger_id"])
        # Require zero whole-history snapshot rewrites across all fifty actions.
        self.assertEqual([], snapshot_writes)
        # Read the durable append-only records without invoking provider parsing.
        journal_lines = self.provider.ledger_action_journal_path().read_bytes().splitlines()
        # Require exactly one commit and one projection marker per action.
        self.assertEqual(100, len(journal_lines))
        # Require a replay to append nothing and preserve the original event.
        before_replay = self.provider.ledger_action_journal_path().stat().st_size
        # Replay the first canonical identity with byte-identical semantics.
        _, replayed = self.provider.transact_ledger_once("human", -1, "TEST_JOURNAL_DEBIT", "journal-0", "storage", "round-0", {"index": 0})
        # Require the action to resolve as an existing commit.
        self.assertTrue(replayed)
        # Require replay to leave the append-only journal byte-identical.
        self.assertEqual(before_replay, self.provider.ledger_action_journal_path().stat().st_size)
        # Compact the settled journal through the production checkpoint seam.
        self.provider._compact_action_journal(self.provider._read_actions_registry())
        # Require retained checkpoint cost to stay within the issue's per-action ceiling.
        self.assertLessEqual(self.provider.ledger_action_journal_path().stat().st_size / 50, 200)
        # Reconstruct a fresh provider so compact references must resolve from ledger bytes.
        restarted = storage.JsonStorageProvider(self.data_root)
        # Replay one compacted action through the canonical exactly-once seam.
        replay_event, replayed = restarted.transact_ledger_once("human", -1, "TEST_JOURNAL_DEBIT", "journal-49", "storage", "round-49", {"index": 49})
        # Require compaction to preserve the original committed identity.
        self.assertTrue(replayed)
        # Require the replayed compact action to retain its ledger identity.
        self.assertTrue(replay_event["ledger_id"])

    # Prove the append-only format remains compatible with a pre-change snapshot.
    def test_legacy_snapshot_replays_without_conversion_write(self):
        # Commit one action so its production event and record fields are canonical.
        event, replayed = self.provider.transact_ledger_once("human", -4, "TEST_LEGACY_DEBIT", "legacy-key", "storage", "legacy-round", {"family": "legacy"})
        # Require the seed action to be a fresh commit.
        self.assertFalse(replayed)
        # Decode the first append-only commit record for fixture conversion.
        commit = json.loads(self.provider.ledger_action_journal_path().read_text(encoding="utf-8").splitlines()[0])
        # Build the exact legacy snapshot shape produced before LEDGER-034.
        legacy = {"schema_version": 1, "next_sequence": 2, "actions": {commit["identity"]: {**commit["action"], "projected": True}}}
        # Persist the compatibility snapshot through the normal atomic writer.
        self.provider._write_json(self.provider.ledger_actions_path(), legacy)
        # Remove the derived test journal so restart depends only on legacy bytes.
        self.provider.ledger_action_journal_path().unlink()
        # Reconstruct a fresh provider like an application restart after upgrade.
        restarted = storage.JsonStorageProvider(self.data_root)
        # Replay the exact old identity through the new combined index reader.
        replay_event, replayed = restarted.transact_ledger_once("human", -4, "TEST_LEGACY_DEBIT", "legacy-key", "storage", "legacy-round", {"family": "legacy"})
        # Require the old commit to remain exactly-once and retain its ledger identity.
        self.assertTrue(replayed)
        # Require the compatibility replay to return the original immutable event.
        self.assertEqual(event["ledger_id"], replay_event["ledger_id"])
        # Require a read-only replay not to create a new journal file.
        self.assertFalse(restarted.ledger_action_journal_path().exists())

    # Prove a warmed provider consumes only another process's appended journal tail.
    def test_external_journal_append_is_visible(self):
        # Warm the first provider's empty action index.
        self.assertIsNone(self.provider.find_ledger_action("human", "storage", "external-key"))
        # Build a second independent provider over the same durable files.
        second = storage.JsonStorageProvider(self.data_root)
        # Commit one action through the second provider while the first cache is warm.
        event, replayed = second.transact_ledger_once("human", -2, "TEST_EXTERNAL_ONCE", "external-key", "storage", "external-round", {"writer": "second"})
        # Require the external action to be a new commit.
        self.assertFalse(replayed)
        # Resolve the external commit through the first provider's incremental tail refresh.
        observed = self.provider.find_ledger_action("human", "storage", "external-key")
        # Require exact immutable event parity without rebuilding the journal format.
        self.assertEqual(event, observed)

    # Prove an interrupted journal append cannot silently rearm a money identity.
    def test_partial_journal_record_fails_closed(self):
        # Write one deliberately unterminated commit fragment under the isolated root.
        self.provider.ledger_action_journal_path().write_bytes(b'{"identity":"partial","op":"commit"')
        # Require any wallet-state read to stop at the operator-recovery boundary.
        with self.assertRaises(ConflictError):
            # Trigger the production recovery path that must validate the journal first.
            self.provider.load_players(players.default_players)

    # Prove interrupted compaction bytes cannot be ignored on restart.
    def test_compaction_temporary_fails_closed(self):
        # Build the exact private sibling pattern used by atomic checkpoint publication.
        temporary = self.provider.ledger_action_journal_path().with_suffix(".jsonl.tmp-interrupted")
        # Write a bounded unpublished record without replacing the durable journal.
        temporary.write_text('{}\n', encoding="utf-8")
        # Require ordinary wallet-state access to preserve both sources for operator recovery.
        with self.assertRaises(ConflictError):
            # Trigger the provider recovery boundary that scans compaction residue.
            self.provider.load_players(players.default_players)


# Group cache-equivalence and point-read proofs for provider read paths. (STORAGE-017)
class ProviderReadPathEfficiencyTests(unittest.TestCase):
    # Create one isolated data root per test.
    def setUp(self):
        # Build a disposable directory removed automatically after each case.
        self._tmp = tempfile.TemporaryDirectory()
        # Register cleanup even when a provider assertion fails.
        self.addCleanup(self._tmp.cleanup)
        # Retain the isolated root shared by warmed and fresh provider instances.
        self.data_root = Path(self._tmp.name) / "data"

    # Prove warmed history reads parse only appended bytes and remain identical to a fresh full read.
    def test_history_tail_cache_reads_only_growth_and_preserves_filters(self):
        # Build one provider and initialize its private directory layout.
        provider = storage.JsonStorageProvider(self.data_root)
        # Append a large cross-game history baseline through the production writer.
        for index in range(120):
            # Alternate games so the per-game index is exercised.
            provider.append_history(_history_row(index, "slots" if index % 2 == 0 else "keno"))
        # Retain each byte region decoded after instrumentation begins.
        decoded_sizes = []
        # Preserve the production region decoder for delegated parsing.
        original_decode = provider._decode_history_region

        # Measure only bytes presented to the standard CSV parser.
        def measured_decode(payload, *, has_header):
            # Record the exact incremental region size.
            decoded_sizes.append(len(payload))
            # Delegate parsing without changing compatibility semantics.
            return original_decode(payload, has_header=has_header)

        # Install the measurement seam on this isolated provider instance.
        provider._decode_history_region = measured_decode
        # Warm the cache over the complete baseline.
        warmed_initial = provider.recent_history(1_000_000)
        # Require every seeded history row in append order.
        self.assertEqual(120, len(warmed_initial))
        # Retain the full-parse byte count for a scale comparison.
        full_parse_bytes = decoded_sizes[-1]
        # Append one external row through an independent provider instance.
        storage.JsonStorageProvider(self.data_root).append_history(_history_row(120, "slots"))
        # Read the warmed filtered view after the external append.
        warmed_slots = provider.recent_history(1_000_000, "slots")
        # Require the appended row to be visible at the tail.
        self.assertEqual("history_120", warmed_slots[-1]["round_id"])
        # Require only the one-row growth region to be decoded after warm-up.
        self.assertLess(decoded_sizes[-1] * 20, full_parse_bytes)
        # Require exact output parity with a cache-free provider.
        self.assertEqual(storage.JsonStorageProvider(self.data_root).recent_history(1_000_000, "slots"), warmed_slots)
        # Reset through the warmed provider so cache invalidation is exercised.
        provider.reset()
        # Require no stale history after reset removed the backing CSV.
        self.assertEqual([], provider.recent_history(10))

    # Prove the JSON point-read returns one detached player without changing compatibility shape.
    def test_json_player_point_read_is_detached_and_exact(self):
        # Build and seed one isolated provider.
        provider = storage.JsonStorageProvider(self.data_root)
        # Seed the canonical players through the idempotent bootstrap path.
        provider.bootstrap_players(players.default_players())
        # Read only the human row through the new point seam.
        selected = provider.get_player("human", players.default_players)
        # Read the complete document only as a golden compatibility oracle.
        expected = next(row for row in provider.load_players(players.default_players)["players"] if row["player_id"] == "human")
        # Require byte-equivalent shape and values.
        self.assertEqual(expected, selected)
        # Mutate the detached result to prove durable state cannot be changed by the caller.
        selected["balance"] = 1.0
        # Require a second point read to preserve the authoritative balance.
        self.assertEqual(expected["balance"], provider.get_player("human", players.default_players)["balance"])
        # Preserve the established missing-player result.
        self.assertIsNone(provider.get_player("missing", players.default_players))

    # Prove the MySQL point-read uses the player primary-key predicate and returns no full-table scan.
    def test_mysql_player_point_read_uses_primary_key_predicate(self):
        # Retain the exact statement and values sent by the provider.
        executed = []

        # Model one dictionary cursor returning a single compatible player row.
        class Cursor:
            # Capture the point query.
            def execute(self, statement, values):
                # Retain exact SQL and parameters for the assertion.
                executed.append((statement, values))

            # Return one requested player row.
            def fetchone(self):
                # Match the database-to-public mapping columns.
                return {"player_id": "human", "display_name": "You", "player_type": "human", "balance": Decimal("5000.00"), "created_at": "2026-08-19T00:00:00Z", "updated_at": "2026-08-19T00:00:00Z", "status": "active"}

        # Model one read-only connection lease.
        class Connection:
            # Return the point cursor while retaining mapping mode.
            def cursor(self, dictionary=False):
                # Record dictionary mapping selection.
                self.dictionary = dictionary
                # Return the deterministic cursor.
                return Cursor()

            # Record exact cleanup.
            def close(self):
                # Mark the lease released.
                self.closed = True

        # Build the fake connection state.
        connection = Connection()
        # Start with no observed close.
        connection.closed = False
        # Construct a provider without allocating a real connection pool.
        provider = object.__new__(storage.MySQLStorageProvider)
        # Bypass schema readiness only for the SQL-shape test.
        provider.ensure_ready = lambda: None
        # Return the deterministic point-read lease.
        provider.connect = lambda: connection
        # Execute the production point-read implementation.
        selected = provider.get_player("human", players.default_players)
        # Require exact identity, an equality predicate, one bound id, and cleanup.
        self.assertEqual(("human", ("human",), True, True), (selected["player_id"], executed[0][1], "WHERE player_id = %s" in executed[0][0], connection.closed))
        # Reject accidental stable-order full-table scan behavior on this path.
        self.assertNotIn("ORDER BY player_id", executed[0][0])


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
