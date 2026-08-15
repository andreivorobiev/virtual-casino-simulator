# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process evidence for provider-atomic Blackjack rounds and settings."""

# Import JSON support for exact durable fixture and result inspection.
import json
# Import environment access for isolated child-provider configuration.
import os
# Import subprocess support for fresh independent Python workers.
import subprocess
# Import the active interpreter used by the repository test runner.
import sys
# Import temporary directories for task-owned state and rendezvous files.
import tempfile
# Import bounded polling for child-process readiness.
import time
# Import the standard unit-test framework used by the central runner.
import unittest
# Import portable paths for repository, state, and rendezvous ownership.
from pathlib import Path

# Import production Blackjack rules for canonical fixture cards and state defaults.
from casino.games.blackjack import engine


# Prove every in-scope Blackjack transition uses the latest provider document. (TEST-196, TEST-200)
class BlackjackAtomicStateTests(unittest.TestCase):
    # Build one deterministic active round whose shoe supports two legal hits.
    def _initial_state(self) -> dict:
        # Resolve one canonical suit from production rather than copying card encoding.
        suit = engine.SUITS[0]
        # Start with descriptor-owned table defaults.
        state = engine.default_state()
        # Seed more than the cut threshold so neither worker reshuffles.
        state["shoe"] = [f"4{suit}"] * 58 + [f"3{suit}", f"2{suit}"]
        # Build one active eleven whose first and second hit remain legal.
        rnd = {
            "round_id": "bj-atomic",
            "player_id": "atomic-player",
            "status": "player_turn",
            "created_at": "2026-08-14T00:00:00Z",
            "dealer": {"cards": [f"10{suit}", f"7{suit}"], "hole_card_hidden": True},
            "hands": [{"hand_id": "hand-atomic", "cards": [f"5{suit}", f"6{suit}"], "bet": 10.0, "status": "active", "is_split_hand": False, "actions": []}],
            "active_hand_index": 0,
            "insurance": None,
            "even_money": None,
            "settlements": [],
        }
        # Publish the fixed round under its stable identifier.
        state["rounds"] = {rnd["round_id"]: rnd}
        # Return the complete production state shape.
        return state

    # Run fresh workers only after every one loads the same stale document.
    def _run_workers(self, repository_root: Path, environment: dict, temporary_root: Path, modes: tuple[str, ...]) -> list[str]:
        # Define one dependency-free worker that preloads before its atomic mutation.
        worker_source = """
import sys
import time
from pathlib import Path
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError
from casino.games.blackjack import api, engine
state = load_player_game_state('blackjack', 'atomic-player', engine.default_state)
mode = sys.argv[1]
ready_path = Path(sys.argv[2])
go_path = Path(sys.argv[3])
sequence_path = Path(sys.argv[4])
ready_path.write_text('ready', encoding='utf-8')
deadline = time.monotonic() + 10
while not go_path.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if not go_path.exists():
    raise RuntimeError('Blackjack atomic race release timed out')
if mode == 'hit':
    api.commit_round_transition('atomic-player', state, lambda current: engine.hit(current, 'bj-atomic'))
elif mode == 'settings-decks':
    api.update_table_settings('atomic-player', state, {'decks': 8}, api.declared_fields(api.GAME_ID))
elif mode == 'settings-soft17':
    api.update_table_settings('atomic-player', state, {'dealer_hits_soft_17': True}, api.declared_fields(api.GAME_ID))
elif mode == 'publish-active-round':
    def publish(current):
        current.setdefault('rounds', {})['bj-settings-active'] = {'round_id': 'bj-settings-active', 'status': 'player_turn'}
        return current
    update_player_game_state('blackjack', 'atomic-player', publish, engine.default_state)
    sequence_path.write_text('committed', encoding='utf-8')
elif mode == 'settings-after-active':
    sequence_deadline = time.monotonic() + 10
    while not sequence_path.exists() and time.monotonic() < sequence_deadline:
        time.sleep(0.01)
    if not sequence_path.exists():
        raise RuntimeError('Blackjack active-round publication timed out')
    try:
        api.update_table_settings('atomic-player', state, {'decks': 8}, api.declared_fields(api.GAME_ID))
    except ConflictError:
        print('conflict')
    else:
        raise RuntimeError('Blackjack stale settings request crossed an active round')
else:
    def mark(current):
        current.setdefault('atomic_markers', []).append(mode)
        return current
    update_player_game_state('blackjack', 'atomic-player', mark, engine.default_state)
"""
        # Resolve one release file shared by this exact worker set.
        go_path = temporary_root / ("go-" + "-".join(modes))
        # Resolve one sequencing marker used only by ordered stale-settings evidence.
        sequence_path = temporary_root / ("sequence-" + "-".join(modes))
        # Retain child handles and readiness paths for bounded diagnostics.
        processes = []
        # Start every worker against the same durable player document.
        for index, mode in enumerate(modes):
            # Allocate one unique readiness marker.
            ready_path = temporary_root / f"ready-{index}-{mode}"
            # Launch without a shell so interpreter and arguments remain exact.
            process = subprocess.Popen([sys.executable, "-c", worker_source, mode, str(ready_path), str(go_path), str(sequence_path)], cwd=repository_root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Retain the process with its exact marker.
            processes.append((process, ready_path))
        # Bound the stale-load rendezvous so a failed child cannot hang the suite.
        deadline = time.monotonic() + 10
        # Wait until every child owns its stale pre-release snapshot.
        while not all(ready.exists() for _, ready in processes) and time.monotonic() < deadline:
            # Stop early when any child exits before readiness.
            if any(process.poll() is not None for process, _ in processes):
                # Leave the loop for the explicit diagnostic assertion.
                break
            # Yield briefly without changing release order.
            time.sleep(0.01)
        # Require a complete stale-state rendezvous before mutation.
        self.assertTrue(all(ready.exists() for _, ready in processes))
        # Release every prepared worker exactly once.
        go_path.write_text("go", encoding="utf-8")
        # Collect bounded process diagnostics and exit codes.
        completed = [(*process.communicate(timeout=15), process.returncode) for process, _ in processes]
        # Require every legal transition or sibling update to complete.
        for standard_output, standard_error, return_code in completed:
            # Preserve child output only when the exact assertion fails.
            self.assertEqual(return_code, 0, f"stdout={standard_output!r} stderr={standard_error!r}")
        # Return normalized outcomes for the ordered stale-settings conflict proof.
        return [standard_output.strip() for standard_output, _standard_error, _return_code in completed]

    # Create one isolated provider root and common child environment.
    def _fixture(self, temporary: str, initial_state: dict | None = None) -> tuple[Path, Path, dict]:
        # Resolve the disposable JSON data root.
        data_root = Path(temporary) / "data"
        # Resolve the exact Blackjack player document.
        state_path = data_root / "games" / "blackjack" / "atomic-player.json"
        # Create its parent before publishing the deterministic state.
        state_path.parent.mkdir(parents=True, exist_ok=True)
        # Persist one canonical baseline for all workers.
        state_path.write_text(json.dumps(initial_state if initial_state is not None else self._initial_state()), encoding="utf-8")
        # Resolve this exact checkout for child imports.
        repository_root = Path(__file__).resolve().parents[4]
        # Copy the caller environment before replacing runtime-owned paths.
        environment = os.environ.copy()
        # Select the disposable provider root in every fresh process.
        environment["CASINO_DATA_DIR"] = str(data_root)
        # Keep child logs inside the same task-owned boundary.
        environment["CASINO_LOG_DIR"] = str(Path(temporary) / "logs")
        # Require the JSON provider so the cross-process lock is exercised.
        environment["CASINO_STORAGE_PROVIDER"] = "json"
        # Bind imports to this exact worktree.
        environment["PYTHONPATH"] = str(repository_root)
        # Return all exact fixture identities.
        return repository_root, state_path, environment

    # Prove one stale round transition and unrelated sibling publication both survive.
    def test_hit_preserves_concurrent_sibling_update(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Build exact repository, state, and environment bindings.
            repository_root, state_path, environment = self._fixture(temporary)
            # Race one hit against an unrelated top-level marker after both load stale state.
            self._run_workers(repository_root, environment, Path(temporary), ("hit", "sibling"))
            # Read the final provider-published state after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Resolve the exact transitioned round.
            rnd = final["rounds"]["bj-atomic"]
            # Require the sibling field and sole legal card transition together.
            self.assertEqual((["sibling"], 3, ["hit"], 59), (final["atomic_markers"], len(rnd["hands"][0]["cards"]), rnd["hands"][0]["actions"], len(final["shoe"])))
            # Require the wager and settlement fields to remain exact and uninvented.
            self.assertEqual((10.0, "player_turn", []), (rnd["hands"][0]["bet"], rnd["status"], rnd["settlements"]))

    # Prove concurrent actions on one round serialize into the exact legal card sequence.
    def test_same_round_hits_serialize_without_card_or_wager_loss(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Build exact repository, state, and environment bindings.
            repository_root, state_path, environment = self._fixture(temporary)
            # Race two legal hits after both processes load the same stale eleven.
            self._run_workers(repository_root, environment, Path(temporary), ("hit", "hit"))
            # Read the single authoritative terminal provider document.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Resolve the exact shared round after serialization.
            rnd = final["rounds"]["bj-atomic"]
            # Require two cards, two actions, and two shoe removals with no overwrite.
            self.assertEqual((4, ["hit", "hit"], 58), (len(rnd["hands"][0]["cards"]), rnd["hands"][0]["actions"], len(final["shoe"])))
            # Require the original bet, round phase, and absence of invented settlement.
            self.assertEqual((10.0, "player_turn", []), (rnd["hands"][0]["bet"], rnd["status"], rnd["settlements"]))

    # Prove settings preserve unrelated provider state when both workers loaded stale bytes. (TEST-200)
    def test_settings_preserve_concurrent_sibling_update(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Seed a round-free document with one unrelated marker.
            initial = engine.default_state()
            # Retain the marker through the settings publication race.
            initial["atomic_markers"] = ["seed"]
            # Build exact repository, state, and environment bindings.
            repository_root, state_path, environment = self._fixture(temporary, initial)
            # Race one descriptor-owned update against an unrelated sibling publication.
            self._run_workers(repository_root, environment, Path(temporary), ("settings-decks", "settings-sibling"))
            # Read the single authoritative document after both workers exit.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require the canonical setting and both sibling markers without other rule drift.
            self.assertEqual((8, ["seed", "settings-sibling"], initial["rules"]["blackjack_payout"]), (final["rules"]["decks"], final["atomic_markers"], final["rules"]["blackjack_payout"]))

    # Prove disjoint settings merge through serialized latest-document callbacks. (TEST-200)
    def test_disjoint_settings_updates_merge_without_loss(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Start from exact descriptor-owned defaults with no active round.
            initial = engine.default_state()
            # Make the independently changed boolean explicit in the baseline.
            initial["rules"]["dealer_hits_soft_17"] = False
            # Build exact repository, state, and environment bindings.
            repository_root, state_path, environment = self._fixture(temporary, initial)
            # Race two disjoint centrally declared fields after both processes load stale rules.
            self._run_workers(repository_root, environment, Path(temporary), ("settings-decks", "settings-soft17"))
            # Read the provider-owned merged settings document.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require both canonical values while omitted payout math remains unchanged.
            self.assertEqual((8, True, initial["rules"]["blackjack_payout"]), (final["rules"]["decks"], final["rules"]["dealer_hits_soft_17"], final["rules"]["blackjack_payout"]))

    # Prove a provider-latest active round defeats a stale settings snapshot. (TEST-200)
    def test_provider_latest_active_round_rejects_stale_settings(self) -> None:
        # Own every state and rendezvous byte inside one disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Seed exact rules and one sibling field that the losing request must not alter.
            initial = engine.default_state()
            # Preserve one independent field across ordered publication and refusal.
            initial["atomic_markers"] = ["seed"]
            # Capture the complete baseline before the active-round publisher runs.
            expected = json.loads(json.dumps(initial))
            # Add only the exact round the ordered winner is allowed to publish.
            expected.setdefault("rounds", {})["bj-settings-active"] = {"round_id": "bj-settings-active", "status": "player_turn"}
            # Build exact repository, state, and environment bindings.
            repository_root, state_path, environment = self._fixture(temporary, initial)
            # Force the active round to commit only after both workers own stale snapshots.
            outcomes = self._run_workers(repository_root, environment, Path(temporary), ("publish-active-round", "settings-after-active"))
            # Read the final document after the stale settings worker reports its conflict.
            final = json.loads(state_path.read_text(encoding="utf-8"))
            # Require the ordered loser to return only the expected conflict marker.
            self.assertEqual(["", "conflict"], outcomes)
            # Remove provider-owned envelope metadata before comparing complete game state.
            final.pop("schema_version", None)
            # Remove the provider publication timestamp, which is not Blackjack state.
            final.pop("updated_at", None)
            # Require the complete document to differ only by the winning active round.
            self.assertEqual(expected, final)


# Run the focused module suite directly for developer diagnostics.
if __name__ == "__main__":
    # Delegate status and failure reporting to unittest's standard CLI.
    unittest.main()
