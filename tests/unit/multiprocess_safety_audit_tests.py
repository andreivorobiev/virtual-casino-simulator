# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free hostile proof for the #323 Package C process-safety checkpoint."""

# Import syntax-tree parsing for isolated structural fixtures.
import ast
# Import output redirection for the fixed command-line privacy boundary.
import contextlib
# Import in-memory text streams for exact stdout and stderr assertions.
import io
# Import JSON parsing errors for hostile serialization and manifest fixtures.
import json
# Import portable paths for the exact checkout and disposable source trees.
from pathlib import Path
# Import disposable directories for malformed and unreachable source fixtures.
import tempfile
# Import standard unit-test assertions.
import unittest
# Import bounded patching for clean-tree and failure injection.
from unittest import mock

# Import the static audit without importing Casino runtime modules.
from scripts import audit_multiprocess_safety as audit


# Build one parsed source record without importing the fixture.
def parsed_module(path: str, source: str) -> dict:
    # Return the repository-relative identity and parsed syntax tree.
    return {"path": path, "tree": ast.parse(source, filename=path)}


# Prove exhaustive structural inventory and fail-closed semantic classification.
class MultiprocessSafetyInventoryTests(unittest.TestCase):
    # Build one exact-current inventory from tracked source without requiring archive Git metadata.
    @classmethod
    def setUpClass(cls) -> None:  # Build shared exact-current structural evidence.
        # Bind the isolated Package C source tree without changing process working directory.
        cls.repo_root = Path(__file__).resolve().parents[2]
        # Supply one valid synthetic commit because release validation uses a Git-free exact-HEAD archive.
        cls.commit = "0" * 40
        # Bind provenance to the synthetic identity while retaining all source-byte analysis.
        with mock.patch.object(audit, "source_commit", return_value=cls.commit):
            # Permit both a normal checkout and the exact tracked release archive fixture.
            with mock.patch.object(audit, "require_clean_tree"):
                # Build one immutable structural packet for current-source assertions.
                cls.inventory = audit.build_inventory(cls.repo_root, cls.commit)

    # Prove all 46 registered games receive one conservative reachable persistence disposition.
    def test_all_registered_games_are_reachably_classified_and_blocked(self) -> None:
        # Read the complete governed game inventory.
        games = self.inventory["games"]
        # Pin exact deployed catalog coverage.
        self.assertEqual(len(games), audit.EXPECTED_GAME_COUNT)
        # Reject duplicate or omitted game identities.
        self.assertEqual(len({row["game_id"] for row in games}), audit.EXPECTED_GAME_COUNT)
        # Pin the exact current persistence families after Roulette retires direct saves.
        self.assertEqual(
            {row["state_model"] for row in games},  # Compare every current model.
            {"player_document_load_save", "shared_simple_game_load_save", "provider_atomic_player_document"},  # Pin accepted families.
        )
        # Pin the exact current family cardinalities after Jacks-or-Better retires direct publication.
        self.assertEqual(
            {
                model: sum(row["state_model"] == model for row in games)  # Count one model.
                for model in {"player_document_load_save", "shared_simple_game_load_save", "provider_atomic_player_document"}  # Cover all models.
            },
            {"player_document_load_save": 8, "shared_simple_game_load_save": 11, "provider_atomic_player_document": 27},  # Pin current counts.
        )
        # Resolve Casino War after preparation and rollback retire its final direct publication.
        casino_war = next(row for row in games if row["game_id"] == "casino_war")
        # Require the authoritative Casino War read used for response and interruption recovery.
        self.assertGreater(casino_war["load_call_sites"], 0)
        # Require every reachable Casino War publication to avoid direct whole-document saves.
        self.assertEqual(casino_war["save_call_sites"], 0)
        # Bind preparation, rollback, reconciliation, and terminal state to atomic updates.
        self.assertGreater(casino_war["atomic_update_call_sites"], 0)
        # Name completed state publication without claiming state-and-money atomicity.
        self.assertEqual(casino_war["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked because state and money remain separate boundaries.
        self.assertEqual(casino_war["multiworker_status"], "blocked")
        # Resolve Roulette after bet, refund, spin, terminal, and settings paths retire direct publication.
        roulette = next(row for row in games if row["game_id"] == "roulette")
        # Require the authoritative Roulette reads used by payload and recovery paths.
        self.assertGreater(roulette["load_call_sites"], 0)
        # Require every reachable Roulette publication to avoid stale whole-document saves.
        self.assertEqual(roulette["save_call_sites"], 0)
        # Bind preparation, reconciliation, spin, terminal, and settings transitions to atomic updates.
        self.assertGreater(roulette["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(roulette["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(roulette["multiworker_status"], "blocked")
        # Resolve Bingo after purchase, call, settlement, and reset retire every direct publication.
        bingo = next(row for row in games if row["game_id"] == "bingo")
        # Require authoritative Bingo reads for response and recovery paths.
        self.assertGreater(bingo["load_call_sites"], 0)
        # Require every reachable Bingo publication to avoid stale whole-document saves.
        self.assertEqual(bingo["save_call_sites"], 0)
        # Bind purchase, call, settlement, and reset transitions to atomic updates.
        self.assertGreater(bingo["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(bingo["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(bingo["multiworker_status"], "blocked")
        # Resolve Caribbean Stud after deal, decision, settlement, and rollback retire every direct publication.
        caribbean_stud = next(row for row in games if row["game_id"] == "caribbean_stud")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(caribbean_stud["load_call_sites"], 0)
        # Require every reachable Caribbean Stud publication to avoid stale whole-document saves.
        self.assertEqual(caribbean_stud["save_call_sites"], 0)
        # Bind optimistic deal, decision, settlement, and rollback publication to provider updates.
        self.assertGreater(caribbean_stud["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(caribbean_stud["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(caribbean_stud["multiworker_status"], "blocked")
        # Resolve Four Card Poker after deal, decision, settlement, and rollback retire every direct publication.
        four_card_poker = next(row for row in games if row["game_id"] == "four_card_poker")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(four_card_poker["load_call_sites"], 0)
        # Require every reachable Four Card Poker publication to avoid stale whole-document saves.
        self.assertEqual(four_card_poker["save_call_sites"], 0)
        # Bind optimistic deal, decision, settlement, and rollback publication to provider updates.
        self.assertGreater(four_card_poker["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(four_card_poker["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(four_card_poker["multiworker_status"], "blocked")
        # Resolve Three Card Poker after deal, decision, recovery, and rollback retire every direct publication.
        three_card_poker = next(row for row in games if row["game_id"] == "three_card_poker")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(three_card_poker["load_call_sites"], 0)
        # Require every reachable Three Card Poker publication to avoid stale whole-document saves.
        self.assertEqual(three_card_poker["save_call_sites"], 0)
        # Bind optimistic deal, decision, settlement, and rollback publication to provider updates.
        self.assertGreater(three_card_poker["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(three_card_poker["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(three_card_poker["multiworker_status"], "blocked")
        # Resolve Casino Hold'em after deal, decision, recovery, and rollback retire every direct publication.
        casino_holdem = next(row for row in games if row["game_id"] == "casino_holdem")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(casino_holdem["load_call_sites"], 0)
        # Require every reachable Casino Hold'em publication to avoid stale whole-document saves.
        self.assertEqual(casino_holdem["save_call_sites"], 0)
        # Bind optimistic deal, decision, settlement, and rollback publication to provider updates.
        self.assertGreater(casino_holdem["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(casino_holdem["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(casino_holdem["multiworker_status"], "blocked")
        # Resolve Pai Gow Poker after deal, set, recovery, and rollback retire every direct publication.
        pai_gow_poker = next(row for row in games if row["game_id"] == "pai_gow_poker")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(pai_gow_poker["load_call_sites"], 0)
        # Require every reachable Pai Gow Poker publication to avoid stale whole-document saves.
        self.assertEqual(pai_gow_poker["save_call_sites"], 0)
        # Bind optimistic deal, set, settlement, and rollback publication to provider updates.
        self.assertGreater(pai_gow_poker["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(pai_gow_poker["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate transactions.
        self.assertEqual(pai_gow_poker["multiworker_status"], "blocked")
        # Resolve the practice table after escrow, action, recovery, and archive retire direct publication.
        practice_table = next(row for row in games if row["game_id"] == "texas_holdem_practice_table")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(practice_table["load_call_sites"], 0)
        # Require every reachable practice-table publication to avoid stale whole-document saves.
        self.assertEqual(practice_table["save_call_sites"], 0)
        # Bind preparation, markers, actions, archive, compensation, and healing to provider updates.
        self.assertGreater(practice_table["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(practice_table["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while four wallets remain separate boundaries.
        self.assertEqual(practice_table["multiworker_status"], "blocked")
        # Resolve Craps after round, roll, marker, archive, and rollback publication become atomic.
        craps = next(row for row in games if row["game_id"] == "craps")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(craps["load_call_sites"], 0)
        # Require every reachable Craps publication to avoid stale whole-document saves.
        self.assertEqual(craps["save_call_sites"], 0)
        # Bind preparation, rolls, recovery markers, archive, and rollback to provider updates.
        self.assertGreater(craps["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(craps["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(craps["multiworker_status"], "blocked")
        # Resolve Andar Bahar after round, receipt, recovery, marker, and rollback publication become atomic.
        andar_bahar = next(row for row in games if row["game_id"] == "andar_bahar")
        # Require authoritative reads for response, replay, and interruption recovery.
        self.assertGreater(andar_bahar["load_call_sites"], 0)
        # Require every reachable Andar Bahar publication to avoid stale whole-document saves.
        self.assertEqual(andar_bahar["save_call_sites"], 0)
        # Bind preparation, receipts, recovery markers, terminal history, and rollback to provider updates.
        self.assertGreater(andar_bahar["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(andar_bahar["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(andar_bahar["multiworker_status"], "blocked")
        # Resolve Over/Under 7 after settled-history publication becomes atomic.
        over_under_7 = next(row for row in games if row["game_id"] == "over_under_7")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(over_under_7["load_call_sites"], 0)
        # Require every reachable history publication to avoid stale whole-document saves.
        self.assertEqual(over_under_7["save_call_sites"], 0)
        # Bind terminal journal publication to provider-current callbacks.
        self.assertGreater(over_under_7["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(over_under_7["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(over_under_7["multiworker_status"], "blocked")
        # Resolve Big Six Wheel after settled-history publication becomes atomic.
        big_six_wheel = next(row for row in games if row["game_id"] == "big_six_wheel")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(big_six_wheel["load_call_sites"], 0)
        # Require every reachable history publication to avoid stale whole-document saves.
        self.assertEqual(big_six_wheel["save_call_sites"], 0)
        # Bind terminal journal publication to provider-current callbacks.
        self.assertGreater(big_six_wheel["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(big_six_wheel["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(big_six_wheel["multiworker_status"], "blocked")
        # Resolve Crown and Anchor after settled-history publication becomes atomic.
        crown_and_anchor = next(row for row in games if row["game_id"] == "crown_and_anchor")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(crown_and_anchor["load_call_sites"], 0)
        # Require every reachable history publication to avoid stale whole-document saves.
        self.assertEqual(crown_and_anchor["save_call_sites"], 0)
        # Bind terminal journal publication to provider-current callbacks.
        self.assertGreater(crown_and_anchor["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(crown_and_anchor["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(crown_and_anchor["multiworker_status"], "blocked")
        # Resolve Fan-Tan after settled-history publication becomes atomic.
        fan_tan = next(row for row in games if row["game_id"] == "fan_tan")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(fan_tan["load_call_sites"], 0)
        # Require every reachable history publication to avoid stale whole-document saves.
        self.assertEqual(fan_tan["save_call_sites"], 0)
        # Bind terminal journal publication to provider-current callbacks.
        self.assertGreater(fan_tan["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(fan_tan["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(fan_tan["multiworker_status"], "blocked")
        # Resolve Acey-Deucey after every round and receipt publication becomes atomic.
        acey_deucey = next(row for row in games if row["game_id"] == "acey_deucey")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(acey_deucey["load_call_sites"], 0)
        # Require every reachable round publication to avoid stale whole-document saves.
        self.assertEqual(acey_deucey["save_call_sites"], 0)
        # Bind prepared, terminal, recovery, and rollback state to atomic callbacks.
        self.assertGreater(acey_deucey["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(acey_deucey["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(acey_deucey["multiworker_status"], "blocked")
        # Resolve Chuck-a-Luck after every settled-round publication becomes atomic.
        chuck_a_luck = next(row for row in games if row["game_id"] == "chuck_a_luck")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(chuck_a_luck["load_call_sites"], 0)
        # Require every reachable round publication to avoid stale whole-document saves.
        self.assertEqual(chuck_a_luck["save_call_sites"], 0)
        # Bind terminal and recovery state to provider-current callbacks.
        self.assertGreater(chuck_a_luck["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(chuck_a_luck["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while state and money remain separate boundaries.
        self.assertEqual(chuck_a_luck["multiworker_status"], "blocked")
        # Resolve Keno after draw and ticket transitions retire every direct state publication.
        keno = next(row for row in games if row["game_id"] == "keno")
        # Require the authoritative Keno read used for response and interruption recovery.
        self.assertGreater(keno["load_call_sites"], 0)
        # Require every reachable Keno publication to avoid direct whole-document saves.
        self.assertEqual(keno["save_call_sites"], 0)
        # Bind draw, ticket purchase, and refund transitions to provider-atomic call sites.
        self.assertGreater(keno["atomic_update_call_sites"], 0)
        # Name Keno's completed state-publication migration without claiming money atomicity.
        self.assertEqual(keno["state_model"], "provider_atomic_player_document")
        # Keep Keno fail closed for a second worker because state and money still use separate boundaries.
        self.assertEqual(keno["multiworker_status"], "blocked")
        # Resolve Baccarat after coup, bet, refund, and settings transitions retire every direct publication.
        baccarat = next(row for row in games if row["game_id"] == "baccarat")
        # Require the authoritative Baccarat read used for responses and interruption recovery.
        self.assertGreater(baccarat["load_call_sites"], 0)
        # Require every reachable Baccarat publication to avoid direct whole-document saves.
        self.assertEqual(baccarat["save_call_sites"], 0)
        # Bind coup, bet, refund, and settings transitions to reachable provider-atomic call sites.
        self.assertGreater(baccarat["atomic_update_call_sites"], 0)
        # Name the completed state-publication migration without claiming money atomicity.
        self.assertEqual(baccarat["state_model"], "provider_atomic_player_document")
        # Keep Baccarat fail closed for a second worker because state and money remain separate boundaries.
        self.assertEqual(baccarat["multiworker_status"], "blocked")
        # Resolve Blackjack after settings retire its final direct state publication.
        blackjack = next(row for row in games if row["game_id"] == "blackjack")
        # Require the read path used for response, recovery, and settings compatibility.
        self.assertGreater(blackjack["load_call_sites"], 0)
        # Require every reachable Blackjack publication to avoid direct whole-document saves.
        self.assertEqual(blackjack["save_call_sites"], 0)
        # Bind rounds, recovery, finalization, and settings to provider-atomic updates.
        self.assertGreater(blackjack["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming state-and-money atomicity.
        self.assertEqual(blackjack["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked because state and money remain separate boundaries.
        self.assertEqual(blackjack["multiworker_status"], "blocked")
        # Resolve Multi-Hand Video Poker after all seven direct publications move behind callbacks.
        multi_hand = next(row for row in games if row["game_id"] == "multi_hand_video_poker")
        # Require the authoritative read used for public state and recovery payloads.
        self.assertGreater(multi_hand["load_call_sites"], 0)
        # Require preparation, rollback, holds, draw, and settlement markers to avoid direct saves.
        self.assertEqual(multi_hand["save_call_sites"], 0)
        # Bind every reachable state mutation to the provider-atomic repository method.
        self.assertGreater(multi_hand["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(multi_hand["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(multi_hand["multiworker_status"], "blocked")
        # Resolve Deuces Wild after every round, hold, replay, and recovery publication becomes atomic.
        deuces_wild = next(row for row in games if row["game_id"] == "deuces_wild_video_poker")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(deuces_wild["load_call_sites"], 0)
        # Require every reachable game-state publication to avoid stale whole-document saves.
        self.assertEqual(deuces_wild["save_call_sites"], 0)
        # Bind preparation, holds, terminal history, recovery markers, and rollback to provider updates.
        self.assertGreater(deuces_wild["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(deuces_wild["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(deuces_wild["multiworker_status"], "blocked")
        # Resolve Double Bonus after every deal, draw, replay, and recovery publication becomes atomic.
        double_bonus = next(row for row in games if row["game_id"] == "double_bonus_video_poker")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(double_bonus["load_call_sites"], 0)
        # Require every reachable game-state publication to avoid stale whole-document saves.
        self.assertEqual(double_bonus["save_call_sites"], 0)
        # Bind preparation, terminal history, receipts, recovery markers, and rollback to provider updates.
        self.assertGreater(double_bonus["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(double_bonus["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(double_bonus["multiworker_status"], "blocked")
        # Resolve Dragon Tiger after shoe, recovery, terminal, and rollback publication becomes atomic.
        dragon_tiger = next(row for row in games if row["game_id"] == "dragon_tiger")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(dragon_tiger["load_call_sites"], 0)
        # Require every reachable game-state publication to avoid stale whole-document saves.
        self.assertEqual(dragon_tiger["save_call_sites"], 0)
        # Bind preparation, terminal history, recovery markers, and rollback to provider updates.
        self.assertGreater(dragon_tiger["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(dragon_tiger["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(dragon_tiger["multiworker_status"], "blocked")
        # Resolve Joker Poker after every deal, hold, draw, replay, and recovery publication becomes atomic.
        joker_poker = next(row for row in games if row["game_id"] == "joker_poker")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(joker_poker["load_call_sites"], 0)
        # Require every reachable game-state publication to avoid stale whole-document saves.
        self.assertEqual(joker_poker["save_call_sites"], 0)
        # Bind preparation, holds, terminal history, receipts, recovery markers, and rollback to provider updates.
        self.assertGreater(joker_poker["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(joker_poker["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(joker_poker["multiworker_status"], "blocked")
        # Resolve Hi-Lo after every deal, guess, replay, and recovery publication becomes atomic.
        hi_lo = next(row for row in games if row["game_id"] == "hi_lo")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(hi_lo["load_call_sites"], 0)
        # Require every reachable game-state publication to avoid stale whole-document saves.
        self.assertEqual(hi_lo["save_call_sites"], 0)
        # Bind preparation, terminal history, receipts, recovery markers, and rollback to provider updates.
        self.assertGreater(hi_lo["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(hi_lo["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(hi_lo["multiworker_status"], "blocked")
        # Resolve Jacks-or-Better after every deal, hold, draw, replay, and marker publication becomes atomic.
        jacks_or_better = next(row for row in games if row["game_id"] == "jacks_or_better_video_poker")
        # Require authoritative reads for response, replay, and ledger recovery.
        self.assertGreater(jacks_or_better["load_call_sites"], 0)
        # Require every reachable game-state publication to avoid stale whole-document saves.
        self.assertEqual(jacks_or_better["save_call_sites"], 0)
        # Bind preparation, holds, terminal history, recovery markers, and rollback to provider updates.
        self.assertGreater(jacks_or_better["atomic_update_call_sites"], 0)
        # Name completed state serialization without claiming wallet-state atomicity.
        self.assertEqual(jacks_or_better["state_model"], "provider_atomic_player_document")
        # Keep production second-worker activation blocked while money is a separate transaction.
        self.assertEqual(jacks_or_better["multiworker_status"], "blocked")
        # Require bounded live call-graph evidence for every game.
        self.assertTrue(all(row["reachable_definitions"] > 0 for row in games))
        # Refuse second-worker authorization for every game.
        self.assertTrue(all(row["multiworker_status"] == "blocked" for row in games))
        # Pin the missing cross-process state-and-money boundary rationale.
        self.assertTrue(
            all(  # Require one exact reason across the catalog.
                row["reason"] == "state_and_money_not_committed_by_one_cross_process_boundary"  # Match reason.
                for row in games  # Inspect every registered game.
            )
        )

    # Prove every required control-plane surface uses live call sites rather than source markers.
    def test_required_components_are_structural_and_conservative(self) -> None:
        # Index components by stable sanitized identity.
        components = {row["component"]: row for row in self.inventory["components"]}
        # Pin the complete Package C control-plane inventory.
        self.assertEqual(
            set(components),  # Compare all component identities.
            {
                "auth_sessions",  # Include session persistence.
                "request_rate_limiter",  # Include rate-limit state.
                "operations_heartbeat",  # Include Operations state.
                "autoplay_registry",  # Include autoplay state.
                "bot_controller",  # Include bot game state.
            },
        )
        # Require the live auth paths to expose their current mixed atomic/direct writes.
        self.assertEqual(
            (  # Compare semantic model and decision together.
                components["auth_sessions"]["state_model"],  # Read current model.
                components["auth_sessions"]["multiworker_status"],  # Read current disposition.
            ),
            ("mixed_atomic_and_direct_document_writes", "blocked"),  # Pin fail-closed semantics.
        )
        # Require at least one live atomic and one live direct auth mutation.
        self.assertGreater(components["auth_sessions"]["atomic_call_sites"], 0)
        # Require the unsafe live auth path to remain explicit.
        self.assertGreater(components["auth_sessions"]["direct_write_call_sites"], 0)
        # Require all declared bot ownership rather than a Roulette sample.
        self.assertEqual(
            components["bot_controller"]["owned_games"],  # Read complete bot ownership.
            ["baccarat", "bingo", "keno", "roulette"],  # Pin every owned game.
        )
        # Require bounded reachability evidence for auth, autoplay, and bot paths.
        self.assertTrue(
            all(  # Require proof for every call-graph component.
                components[name]["reachable_definitions"] > 0  # Require a live definition.
                for name in {"auth_sessions", "autoplay_registry", "bot_controller"}  # Cover three graphs.
            )
        )
        # Require exact derived auth mutator ownership.
        self.assertEqual(
            components["auth_sessions"]["mutating_entrypoints"],  # Read published auth mutators.
            sorted(audit.AUTH_SESSION_ROOTS),  # Compare reviewed complete ownership.
        )
        # Require exact derived auth read-only ownership.
        self.assertEqual(
            components["auth_sessions"]["read_only_entrypoints"],  # Read published auth readers.
            sorted(audit.AUTH_SESSION_READ_ONLY_ROOTS),  # Compare reviewed read-only ownership.
        )
        # Require exact derived autoplay mutator ownership.
        self.assertEqual(
            components["autoplay_registry"]["mutating_entrypoints"],  # Read lifecycle mutators.
            sorted(audit.AUTOPLAY_ROOTS),  # Compare reviewed lifecycle ownership.
        )
        # Require exact derived autoplay read-only ownership.
        self.assertEqual(
            components["autoplay_registry"]["read_only_entrypoints"],  # Read lifecycle readers.
            sorted(audit.AUTOPLAY_READ_ONLY_ROOTS),  # Compare reviewed read ownership.
        )
        # Require exact derived bot mutator ownership.
        self.assertEqual(
            components["bot_controller"]["mutating_entrypoints"],  # Read bot mutators.
            sorted(audit.BOT_ROOTS),  # Compare every public bot dispatcher.
        )
        # Require no unclassified public bot read-only path.
        self.assertEqual(
            components["bot_controller"]["read_only_entrypoints"],  # Read bot readers.
            sorted(audit.BOT_READ_ONLY_ROOTS),  # Compare reviewed empty ownership.
        )
        # Refuse a second worker for every required component.
        self.assertTrue(all(row["multiworker_status"] == "blocked" for row in components.values()))

    # Prove module object discovery is name-agnostic across core, app, WSGI, and games.
    def test_module_objects_cover_public_lowercase_services_and_provider_singletons(self) -> None:
        # Index every module object by portable path and exact symbol.
        rows = {
            (row["path"], row["symbol"]): row  # Index one module object.
            for row in self.inventory["module_state"]  # Inspect complete module state.
        }
        # Pin the application router even though its public name does not end in SERVICE.
        self.assertEqual(rows[("casino/app.py", "ROUTER")]["multiworker_status"], "blocked")
        # Pin the lowercase WSGI application singleton.
        self.assertEqual(rows[("casino/wsgi.py", "application")]["multiworker_status"], "blocked")
        # Pin the reviewed settlement adapter singleton.
        self.assertEqual(
            rows[("casino/core/settlement.py", "_DEFAULT_ADAPTER")]["state_model"],  # Read adapter model.
            "stateless_settlement_adapter",  # Pin reviewed semantics.
        )
        # Resolve the six explicit game adapter instances introduced by settlement convergence.
        game_adapters = {
            (row["path"], row["symbol"])  # Preserve adapter ownership.
            for row in self.inventory["module_state"]  # Inspect complete module state.
            if row["state_model"] == "stateless_settlement_adapter"  # Select reviewed adapters.
            and row["path"].startswith("casino/games/")  # Exclude the shared default adapter.
        }
        # Pin every current explicit game adapter so additions require review.
        self.assertEqual(
            game_adapters,
            {
                ("casino/games/baccarat/api.py", "SETTLEMENT"),  # Pin Baccarat ownership.
                ("casino/games/bingo/api.py", "SETTLEMENT"),  # Pin Bingo ownership.
                ("casino/games/blackjack/api.py", "SETTLEMENT"),  # Pin Blackjack ownership.
                ("casino/games/keno/api.py", "SETTLEMENT"),  # Pin Keno ownership.
                ("casino/games/roulette/api.py", "SETTLEMENT"),  # Pin Roulette ownership.
                ("casino/games/slots/api.py", "SETTLEMENT"),  # Pin Slots ownership.
            },
        )
        # Pin both lazy provider cache symbols.
        self.assertEqual(
            {
                rows[("casino/core/storage.py", "_PROVIDER")]["state_model"],  # Read runtime provider.
                rows[("casino/core/storage.py", "_TEST_PROVIDER")]["state_model"],  # Read test provider.
            },
            {"per_process_provider_cache", "test_provider_injection"},  # Pin both reviewed models.
        )
        # Resolve all deployed game service singleton rows.
        game_services = {
            (row["path"], row["symbol"])  # Preserve service ownership.
            for row in self.inventory["module_state"]  # Inspect complete module state.
            if row["state_model"] == "game_service_singleton"  # Select constructed game services.
        }
        # Pin the four current module-owned game service objects.
        self.assertEqual(
            game_services,  # Compare all discovered game services.
            {
                ("casino/games/big_six_wheel/api.py", "SERVICE"),  # Pin Big Six service.
                ("casino/games/crown_and_anchor/api.py", "SERVICE"),  # Pin Crown service.
                ("casino/games/fan_tan/api.py", "SERVICE"),  # Pin Fan Tan service.
                ("casino/games/scratch_cards/api.py", "SERVICE"),  # Pin Scratch service.
            },
        )

    # Prove instance-held locks, counters, cursors, caches, and pool state are not invisible.
    def test_instance_state_covers_mysql_security_operations_and_storage(self) -> None:
        # Index mutable instance surfaces by portable class identity.
        rows = {
            (row["path"], row["class"], row["attribute"]): row  # Index one instance surface.
            for row in self.inventory["instance_state"]  # Inspect complete instance state.
        }
        # Pin the process-bound MySQL condition, idle set, metrics, and cursor inventory.
        for key in {
            ("casino/core/mysql_pool.py", "MySQLConnectionPool", "_condition"),  # Pin pool condition.
            ("casino/core/mysql_pool.py", "MySQLConnectionPool", "_idle"),  # Pin idle connections.
            ("casino/core/mysql_pool.py", "MySQLConnectionPool", "_metrics"),  # Pin pool metrics.
            ("casino/core/mysql_pool.py", "MySQLConnectionLease", "_cursors"),  # Pin lease cursors.
        }:  # Inspect each required pool surface.
            # Require each process-owned pool surface to be present and explicitly compatible.
            self.assertEqual(rows[key]["multiworker_status"], "compatible")
        # Require the rate-limiter registry and lock to remain visible blockers.
        for attribute in {"clients", "lock"}:
            # Pin each exact security surface.
            self.assertEqual(
                rows[("casino/core/security.py", "RateLimiter", attribute)]["multiworker_status"],  # Read status.
                "blocked",  # Pin conservative decision.
            )
        # Require Operations heartbeat value and synchronization to remain visible blockers.
        for attribute in {"_heartbeat_lock", "_last_successful_heartbeat_at"}:
            # Pin each exact Operations surface.
            self.assertEqual(
                rows[("casino/operations/service.py", "OperationsProbeService", attribute)][  # Read row.
                    "multiworker_status"  # Read exact disposition.
                ],
                "blocked",  # Pin conservative decision.
            )

    # Prove arbitrary public, lowercase, registry, and conditional module objects fail closed.
    def test_unknown_module_objects_are_name_agnostic_and_conditional(self) -> None:
        # Parse a hostile runtime with no recognized singleton naming convention.
        module = parsed_module(
            "casino/runtime.py",  # Assign one portable hostile identity.
            """
REGISTRY = {}
COUNTER = 0
runtime = MutableCoordinator()
if ENABLED:
    conditional = MutableCoordinator()
PUBLIC_OBJECT = MutableCoordinator()

def bump():
    global COUNTER
    COUNTER += 1
""",
        )
        # Inventory the hostile module without importing it.
        rows = audit._module_state_inventory([module], set())
        # Index rows by exact hostile symbol.
        by_symbol = {row["symbol"]: row for row in rows}
        # Require every arbitrary declaration to be discovered.
        self.assertEqual(
            set(by_symbol),  # Compare every discovered hostile symbol.
            {"REGISTRY", "COUNTER", "runtime", "conditional", "PUBLIC_OBJECT"},  # Pin objects and scalar.
        )
        # Refuse compatibility for every unknown object or unlocked registry.
        self.assertTrue(all(row["multiworker_status"] == "blocked" for row in rows))
        # Pin conditional and lowercase declarations to the conservative singleton model.
        self.assertEqual(by_symbol["conditional"]["state_model"], "process_local_singleton_or_cache")
        # Pin the unmutated registry name to mutable module state.
        self.assertEqual(by_symbol["REGISTRY"]["state_model"], "mutable_module_container")
        # Pin a mutated scalar that would otherwise look immutable at initialization.
        self.assertEqual(by_symbol["COUNTER"]["state_model"], "mutated_module_scalar_or_object")
        # Refuse a second worker for the process-local scalar.
        self.assertEqual(by_symbol["COUNTER"]["multiworker_status"], "blocked")

    # Prove every new public state mutator fails root reconciliation until explicitly reviewed.
    def test_unlisted_public_state_mutator_fails_closed(self) -> None:
        # Parse declared mutation/read paths plus one hostile omitted public mutator.
        module = parsed_module(
            "casino/core/fixture.py",  # Assign one portable component identity.
            """
def declared_mutator():
    update_json(SESSIONS_PATH, mutate)

def declared_reader():
    read_json(SESSIONS_PATH, {})

def strict_reader():
    read_json_strict(SESSIONS_PATH, {}, "fixed")

def new_live_mutator():
    write_json(SESSIONS_PATH, snapshot)

def _private_dead_helper():
    write_json(SESSIONS_PATH, dead_snapshot)
""",
        )
        # Derive every public entrypoint that reaches the owned session document.
        discovered = audit._public_state_entrypoints(
            [module],  # Restrict discovery to the hostile component.
            read_calls={"read_json", "read_json_strict"},  # Classify ordinary and strict reads.
            mutation_calls={"update_json", "update_json_strict", "write_json"},  # Classify mutations.
            document_symbol="SESSIONS_PATH",  # Require exact owned document calls.
        )
        # Require the hostile public mutator to be visible while the private dead helper is excluded.
        self.assertEqual(
            discovered,  # Compare complete structural discovery.
            {
                "mutating": ["declared_mutator", "new_live_mutator"],  # Pin both public mutators.
                "read_only": ["declared_reader", "strict_reader"],  # Pin both public readers.
            },
        )
        # Reject a declaration that omits the newly discovered public mutator.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^entrypoint inventory unavailable$"):
            # Reconcile against an intentionally stale mutator set.
            audit._reconcile_state_entrypoints(  # Reconcile the exact complete disposition.
                discovered,  # Supply structural discovery.
                {"declared_mutator"},  # Omit the hostile live mutator.
                {"declared_reader", "strict_reader"},  # Preserve exact read-only dispositions.
            )
        # Accept only an exact complete disposition.
        self.assertEqual(
            audit._reconcile_state_entrypoints(
                discovered,  # Supply structural discovery.
                {"declared_mutator", "new_live_mutator"},  # Declare every public mutator.
                {"declared_reader", "strict_reader"},  # Declare every public reader.
            ),
            discovered,  # Require deterministic reconciled evidence.
        )

    # Prove unreachable synchronous and asynchronous helpers cannot forge live call evidence.
    def test_reachable_calls_exclude_dead_helpers_comments_and_false_branches(self) -> None:
        # Parse one live atomic path plus multiple marker-only and unreachable direct writes.
        module = parsed_module(
            "casino/core/fixture.py",  # Assign one portable fixture identity.
            '''
def live_entry():
    """write_json(SESSIONS_PATH, leaked_marker)"""
    marker = "write_json(SESSIONS_PATH, leaked_marker)"
    update_json(SESSIONS_PATH, mutate)
    if False:
        write_json(SESSIONS_PATH, leaked_false_branch)

def dead_helper():
    write_json(SESSIONS_PATH, leaked_dead_helper)

async def dead_async_helper():
    write_json(SESSIONS_PATH, leaked_dead_async)
''',
        )
        # Traverse only the declared live entrypoint.
        reachable = audit._reachable_facts([module], {"live_entry"})
        # Count only executable document calls reachable from that entrypoint.
        counts = audit._document_call_counts(reachable["calls"], "SESSIONS_PATH")
        # Prove every dead or textual marker is excluded.
        self.assertEqual(counts, {"atomic": 1, "read": 0, "write": 0})
        # Permit compatibility only for the reachable atomic-only fixture.
        self.assertEqual(audit._document_semantics(counts), ("provider_atomic_document", "compatible"))
        # Pin the one reachable definition rather than all three declared helpers.
        self.assertEqual(reachable["definition_count"], 1)

    # Prove a reachable safe marker cannot mask a parallel reachable unsafe path.
    def test_mixed_reachable_document_paths_are_blocked(self) -> None:
        # Parse one entrypoint with both provider-atomic and direct whole-document mutation.
        module = parsed_module(
            "casino/core/fixture.py",  # Assign one portable fixture identity.
            """
def live_entry():
    update_json(SESSIONS_PATH, mutate)
    write_json(SESSIONS_PATH, snapshot)
""",
        )
        # Traverse the one exact live entrypoint.
        reachable = audit._reachable_facts([module], {"live_entry"})
        # Count its two reachable document mutation families.
        counts = audit._document_call_counts(reachable["calls"], "SESSIONS_PATH")
        # Pin one exact safe and one exact unsafe call site.
        self.assertEqual(counts, {"atomic": 1, "read": 0, "write": 1})
        # Refuse compatibility for the mixed live path.
        self.assertEqual(
            audit._document_semantics(counts),  # Read semantic disposition.
            ("mixed_atomic_and_direct_document_writes", "blocked"),  # Pin mixed-path blocker.
        )

    # Prove game classification follows reachable registration paths and rejects dead-marker models.
    def test_game_semantics_use_reachable_registration_paths(self) -> None:
        # Parse one live player-document path plus a dead SimpleWagerGame helper.
        module = parsed_module(
            "casino/games/fixture/api.py",  # Assign one portable game identity.
            """
def register():
    live_handler()

def live_handler():
    state = load_player_game_state("fixture", "player")
    save_player_game_state("fixture", "player", state)

def dead_helper():
    SimpleWagerGame()
""",
        )
        # Classify the fixture through the real per-game semantic boundary.
        rows = audit._game_inventory(
            [{"game_id": "fixture", "backend": "casino.games.fixture.api"}],  # Define governed fixture.
            [module],  # Supply its bounded source.
        )
        # Require the dead helper not to create an overlapping persistence model.
        self.assertEqual(rows[0]["state_model"], "player_document_load_save")
        # Prove only registration and its called live handler are reachable.
        self.assertEqual(rows[0]["reachable_definitions"], 2)
        # Parse one complete provider-atomic player-document path with no direct save.
        atomic_only = parsed_module(
            "casino/games/fixture/api.py",  # Assign the same portable game identity.
            """
def register():
    state = load_player_game_state("fixture", "player")
    update_player_game_state("fixture", "player", mutate)
""",
        )
        # Classify atomic-only publication without requiring a stale whole-document save.
        atomic_rows = audit._game_inventory(
            [{"game_id": "fixture", "backend": "casino.games.fixture.api"}],  # Define governed fixture.
            [atomic_only],  # Supply its provider-atomic source.
        )
        # Require precise atomic classification while retaining the conservative worker blocker.
        self.assertEqual((atomic_rows[0]["state_model"], atomic_rows[0]["save_call_sites"], atomic_rows[0]["multiworker_status"]), ("provider_atomic_player_document", 0, "blocked"))
        # Parse a marker-only fixture whose persistence call exists only in an uncalled helper.
        dead_only = parsed_module(
            "casino/games/fixture/api.py",  # Assign the same portable game identity.
            """
def register():
    return None

def dead_helper():
    load_player_game_state("fixture", "player")
    save_player_game_state("fixture", "player", {})
""",
        )
        # Reject the fixture because no live persistence family is reachable.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "game inventory unavailable"):
            # Attempt classification through the exact registration root.
            audit._game_inventory(
                [{"game_id": "fixture", "backend": "casino.games.fixture.api"}],  # Define governed fixture.
                [dead_only],  # Supply marker-only source.
            )

    # Prove tracked and untracked dirt independently block provenance before source reads.
    def test_clean_tree_guard_rejects_tracked_and_untracked_changes(self) -> None:
        # Exercise both porcelain forms through the sanitized Git seam.
        for dirty_status in (" M casino/runtime.py\n", "?? casino/new_runtime.py\n"):
            # Replace only the Git result with the hostile dirty-tree marker.
            with mock.patch.object(audit, "_git", return_value=dirty_status):
                # Require the same fixed value-free cleanliness error.
                with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^analyzed tree is not clean$"):
                    # Inspect the disposable repository identity.
                    audit.require_clean_tree(Path("ignored"))
        # Prove an empty porcelain result passes without source-path output.
        with mock.patch.object(audit, "_git", return_value=""):
            # Run the exact clean-tree boundary.
            audit.require_clean_tree(Path("ignored"))

    # Prove malformed source, malformed manifests, and unreadable files use fixed internal errors.
    def test_source_and_manifest_failures_are_value_free(self) -> None:
        # Create one minimal repository-shaped disposable tree.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the disposable root.
            root = Path(temporary_directory)
            # Create the required source and descriptor directories.
            for directory in ("casino", "scripts", "modules"):
                # Materialize one exact repository directory.
                (root / directory).mkdir()
            # Write one valid audit placeholder.
            (root / "scripts" / "audit_multiprocess_safety.py").write_text("VALUE = 1\n", encoding="utf-8")
            # Write one valid descriptor placeholder.
            (root / "modules" / "fixture.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
            # Write malformed production Python containing a sentinel path-like value.
            (root / "casino" / "fixture.py").write_text("def SECRET_C:\\\\sentinel(:\n", encoding="utf-8")
            # Reject malformed source without echoing the syntax or path.
            with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^source inventory unavailable$"):
                # Parse the disposable source inventory.
                audit._source_records(root)
            # Replace the production source with valid syntax.
            (root / "casino" / "fixture.py").write_text("VALUE = 1\n", encoding="utf-8")
            # Replace the descriptor with malformed JSON containing a sentinel.
            (root / "modules" / "fixture.json").write_text('{"SECRET":"C:\\\\sentinel"', encoding="utf-8")
            # Reject malformed JSON without echoing its content.
            with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^manifest inventory unavailable$"):
                # Parse the disposable manifest inventory.
                audit._source_records(root)
        # Inject an unreadable source failure carrying a secret path.
        with mock.patch.object(Path, "read_bytes", side_effect=OSError("C:\\secret\\source.py")):
            # Require the same fixed source error.
            with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^source inventory unavailable$"):
                # Read one hostile path through the sanitized file seam.
                audit._read_bytes(Path("C:\\secret\\source.py"))

    # Prove the standalone boundary emits no traceback, path, content, or exception text.
    def test_cli_failures_are_fixed_and_sanitized(self) -> None:
        # Exercise representative parsing, encoding, serialization, and file-system failures.
        failures = (
            json.JSONDecodeError("SECRET_BODY", "SECRET_DOCUMENT", 0),  # Inject malformed JSON.
            UnicodeDecodeError("utf-8", b"SECRET_BYTES", 0, 1, "SECRET_REASON"),  # Inject bad bytes.
            SyntaxError("SECRET_SOURCE", ("C:\\secret\\source.py", 7, 4, "SECRET_LINE")),  # Inject syntax.
            OSError("C:\\secret\\unreadable.py"),  # Inject unreadable source.
        )
        # Verify every internal failure collapses to the exact CLI contract.
        for failure in failures:
            # Capture stdout and stderr without touching the real console.
            stdout, stderr = io.StringIO(), io.StringIO()
            # Inject the hostile failure before evidence exists.
            with mock.patch.object(audit, "build_inventory", side_effect=failure):
                # Redirect both streams around the standalone entrypoint.
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    # Run one sanitized CLI attempt.
                    status = audit.main()
            # Require one fixed failure status.
            self.assertEqual(status, 1)
            # Require no partial evidence.
            self.assertEqual(stdout.getvalue(), "")
            # Require only the fixed value-free error line.
            self.assertEqual(stderr.getvalue(), audit.CLI_FAILURE_MESSAGE + "\n")
            # Reject exception details and traceback text.
            self.assertNotIn("SECRET", stderr.getvalue())
            # Reject absolute-path vocabulary.
            self.assertNotIn("C:\\", stderr.getvalue())
            # Reject traceback framing.
            self.assertNotIn("Traceback", stderr.getvalue())
        # Capture a serialization failure after a structurally valid build.
        stdout, stderr = io.StringIO(), io.StringIO()
        # Return an inert inventory and fail only deterministic JSON rendering.
        with mock.patch.object(audit, "build_inventory", return_value={"safe": True}):
            # Inject a value-bearing serializer failure.
            with mock.patch.object(audit.json, "dumps", side_effect=ValueError("SECRET_RENDER")):
                # Redirect both streams around the standalone entrypoint.
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    # Run the serialization failure path.
                    status = audit.main()
        # Require the same fixed failure status.
        self.assertEqual(status, 1)
        # Require no partial evidence.
        self.assertEqual(stdout.getvalue(), "")
        # Require the same fixed stderr contract.
        self.assertEqual(stderr.getvalue(), audit.CLI_FAILURE_MESSAGE + "\n")

    # Prove explicit provenance cannot diverge from checkout HEAD.
    def test_explicit_source_commit_is_exact_and_checkout_bound(self) -> None:
        # Reject an abbreviated source identity.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "source provenance unavailable"):
            # Attempt evidence construction with an abbreviated commit.
            audit.build_inventory(self.repo_root, self.commit[:12])
        # Reject non-string caller provenance without coercion.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "source provenance unavailable"):
            # Attempt evidence construction with a numeric commit.
            audit.build_inventory(self.repo_root, 1)
        # Construct a different syntactically valid source identity.
        mismatch = "0" * 40 if self.commit != "0" * 40 else "1" * 40
        # Reject a full caller identity that does not equal checkout HEAD.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "source provenance unavailable"):
            # Attempt evidence construction with the mismatched identity.
            audit.build_inventory(self.repo_root, mismatch)

    # Prove evidence is recursively sanitized and exactly reconciled.
    def test_evidence_is_relative_sanitized_and_reconciled(self) -> None:
        # Serialize the exact structural packet.
        rendered = json.dumps(self.inventory, sort_keys=True)
        # Reject the absolute checkout path.
        self.assertNotIn(str(self.repo_root), rendered)
        # Reject common secret, host, and player identity fields.
        for forbidden in ("password", "token", "cookie", "email", "player_id", "host"):
            # Assert forbidden field vocabulary is absent.
            self.assertNotIn(f'"{forbidden}"', rendered.lower())
        # Require exact checkout provenance.
        self.assertEqual(self.inventory["source_commit"], self.commit)
        # Require a complete SHA-256 digest for every analyzed source and manifest byte.
        self.assertRegex(self.inventory["analyzed_tree_sha256"], r"^[0-9a-f]{64}$")
        # Keep the checkpoint explicitly non-authorizing.
        self.assertEqual(self.inventory["decision"], "second_worker_blocked")
        # Read the compact summary.
        summary = self.inventory["summary"]
        # Reconcile every evidence family count.
        self.assertEqual(summary["catalog_game_count"], len(self.inventory["games"]))
        # Reconcile module-state count.
        self.assertEqual(summary["module_state_count"], len(self.inventory["module_state"]))
        # Reconcile instance-state count.
        self.assertEqual(summary["instance_state_count"], len(self.inventory["instance_state"]))
        # Reconcile component count.
        self.assertEqual(summary["component_count"], len(self.inventory["components"]))
        # Recompute detailed blocker rows.
        detailed = (
            self.inventory["module_state"]  # Include module objects.
            + self.inventory["instance_state"]  # Include instance surfaces.
            + self.inventory["components"]  # Include control-plane surfaces.
            + self.inventory["games"]  # Include every game.
        )
        # Require the summary blocker count to equal exact detail.
        self.assertEqual(
            summary["blocker_count"],  # Read published blocker count.
            sum(row["multiworker_status"] == "blocked" for row in detailed),  # Recompute detail.
        )
        # Require the summary compatible count to equal exact detail.
        self.assertEqual(
            summary["compatible_count"],  # Read published compatible count.
            sum(row["multiworker_status"] == "compatible" for row in detailed),  # Recompute detail.
        )


# Run the focused suite when invoked directly.
if __name__ == "__main__":
    # Delegate reporting and exit behavior to unittest.
    unittest.main()
