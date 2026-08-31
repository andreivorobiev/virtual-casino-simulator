# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Durable private Bingo purchase-to-session association evidence."""

# Import detached copies for provider-faithful state boundaries.
import copy
# Import JSON encoding for recursive public-omission assertions.
import json
# Import isolated filesystem ownership for restart evidence.
import tempfile
# Import the standard unit-test framework.
import unittest
# Import portable paths for the disposable JSON provider.
from pathlib import Path
# Import focused patching for state, engine, settlement, and history seams.
from unittest import mock

# Import the production provider package used by local JSON persistence.
from casino.core import storage
# Import the production Bingo association and lifecycle transitions.
from casino.games.bingo import api, engine
# Import the public conflict contract for immutable-identity assertions.
from casino.errors import ConflictError
# Reuse the reviewed transaction-faithful MySQL document model without a connector.
from tests.mysql_game_action_provider_tests import _Database, _Provider


# Prove the private authoritative association across lifecycle and provider boundaries. (BINGO-029, TEST-265)
class BingoPurchaseSessionAssociationTests(unittest.TestCase):
    # Build one complete active session with a single funded human card.
    @staticmethod
    def _session(session_id: str = "bingo-session-1") -> dict:
        # Preserve the established card and session fields consumed by reset settlement.
        card = {"card_id": f"card-{session_id}", "player_id": "human", "amount": 5.0, "card": {}, "status": "active", "winner": False, "payout": 0, "source": "manual"}
        # Return a deterministic active session without depending on entropy.
        return {"session_id": session_id, "player_id": "human", "amount": 5.0, "pattern": "line", "card": card["card"], "cards": [card], "called": [], "status": "active", "created_at": "2026-08-31T00:00:00Z", "winner": None, "winning_card_id": None, "payout": 0, "max_calls": 50}

    # Build one in-memory update seam that copies across every provider boundary.
    @staticmethod
    def _memory_update(box: dict):
        # Match the state-store callback signature used by production Bingo transitions.
        def update(_game_id, _player_id, mutator, _default_factory):
            # Give the mutator a detached provider-current document.
            working = copy.deepcopy(box["state"])
            # Apply the complete transition before publishing any bytes.
            updated = mutator(working)
            # Persist and return independent copies like JSON/MySQL decoding.
            box["state"] = copy.deepcopy(updated)
            # Prevent caller mutation from changing authoritative state.
            return copy.deepcopy(updated)
        # Return the provider-compatible update function.
        return update

    # Patch provider reads and writes around one authoritative in-memory document.
    @classmethod
    def _provider_patches(cls, box: dict):
        # Return both bounded patches for one test-owned context stack.
        return (mock.patch.object(api, "update_player_game_state", side_effect=cls._memory_update(box)), mock.patch.object(api, "load_player_game_state", side_effect=lambda *_args, **_kwargs: copy.deepcopy(box["state"])))

    # Model successful exactly-once settlement events without touching a wallet provider.
    class _Settlement:
        # Initialize an ordered audit of requested movement meanings.
        def __init__(self) -> None:
            # Retain every transaction type and signed amount.
            self.movements = []

        # Commit one deterministic immutable event.
        def apply_once(self, **movement):
            # Record the exact production movement supplied by Bingo.
            self.movements.append(copy.deepcopy(movement))
            # Return the established ledger event dimensions and a non-replay marker.
            return ({"ledger_id": f"ledger-{len(self.movements)}", "game": "bingo", "player_id": movement["player_id"], "amount": movement["signed_amount"], "transaction_type": movement["transaction_type"], "round_id": movement["round_id"], "details": copy.deepcopy(movement["details"])}, False)

        # Return no lost-response evidence because this fake never loses a response.
        def find(self, *_args, **_kwargs):
            # Preserve the production no-match meaning.
            return None

        # Reject unexpected recovery validation in this no-loss fake.
        def validate_existing(self, *_args, **_kwargs):
            # Surface an invalid test path immediately.
            raise AssertionError("unexpected settlement recovery")

    # Require commit/finalize response-loss replays to retain one private exact join. (TEST-265)
    def test_commit_and_finalize_replays_retain_one_private_association(self):
        # Seed the exact prepared marker that precedes wallet funding.
        marker = {"kind": "purchase", "status": "prepared", "purchase_id": "purchase-private-1", "player_id": "human", "amount": 5.0, "pattern": "line"}
        # Own one provider-authoritative state document.
        box = {"state": {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker)}}
        # Retain deterministic engine call count across a lost commit response replay.
        starts = {"count": 0}

        # Publish one deterministic session through the established engine seam.
        def start(current, _player_id, _amount, _pattern, *, bot_players):
            # Require the supplied seats to remain detached and empty in this focused proof.
            self.assertEqual([], bot_players)
            # Count entropy allocation so replay cannot create another session.
            starts["count"] += 1
            # Publish the complete accepted session inside the provider callback.
            current["active_session"] = self._session()
            # Return the provider-owned session.
            return current["active_session"]

        # Enter detached provider and deterministic engine boundaries.
        update_patch, read_patch = self._provider_patches(box)
        # Apply both state seams and the exact session creation patch.
        with update_patch, read_patch, mock.patch.object(api.engine, "start_session", side_effect=start):
            # Commit the session and association for the first accepted response.
            session = api.commit_purchase("human", box["state"], marker, [])
            # Replay the same commit as though the provider response was lost.
            replayed_session = api.commit_purchase("human", box["state"], marker, [])
            # Bind the committed marker dimensions used by finalization.
            committed = {**marker, "status": "committed", "session_id": session["session_id"]}
            # Release the transient marker after its private join is durable.
            finalized = api.finalize_purchase("human", box["state"], committed)
            # Freeze state before an already-finalized response-loss replay.
            before_replay = copy.deepcopy(box["state"])
            # Replay finalization without recreating or reordering the association.
            finalized_replay = api.finalize_purchase("human", box["state"], committed)
        # Prove only one session was ever allocated.
        self.assertEqual(1, starts["count"])
        # Require identical session identity across commit and finalize replays.
        self.assertEqual([session, session, session], [replayed_session, finalized, finalized_replay])
        # Require exact byte-shape stability after finalization replay.
        self.assertEqual(before_replay, box["state"])
        # Retain exactly one raw debit/session association after marker cleanup.
        self.assertEqual([{"purchase_id": marker["purchase_id"], "session_id": session["session_id"]}], box["state"][api.PURCHASE_ASSOCIATIONS_KEY])
        # Prove the transient owner was released only after association publication.
        self.assertNotIn(api.PENDING_ACTION_KEY, box["state"])
        # Strip all private association bytes from the common public state projection.
        public_encoded = json.dumps(api._public_state(box["state"]), sort_keys=True)
        # Require recursive omission of both the private key and raw purchase identity.
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY, public_encoded)
        self.assertNotIn(marker["purchase_id"], public_encoded)
        # Keep the established direct session response free of the purchase identity.
        self.assertNotIn(marker["purchase_id"], json.dumps(session, sort_keys=True))

    # Require a failed accepted-session step to refund the debit without creating a join. (TEST-265)
    def test_failed_session_creation_compensates_without_association(self):
        # Seed one prepared purchase owned by the player document.
        marker = {"kind": "purchase", "status": "prepared", "purchase_id": "purchase-failed", "player_id": "human", "amount": 5.0, "pattern": "line"}
        # Own the authoritative pre-session state.
        box = {"state": {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker)}}
        # Record the exact debit and compensation movements.
        settlement = self._Settlement()
        # Enter detached provider boundaries.
        update_patch, read_patch = self._provider_patches(box)
        # Avoid bot money work and inject failure before any session can be accepted.
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", return_value=[]), mock.patch.object(api.engine, "start_session", side_effect=RuntimeError("session creation failed")):
            # Preserve the original engine failure after compensation converges.
            with self.assertRaisesRegex(RuntimeError, "session creation failed"):
                # Exercise the complete debit/session/refund workflow.
                api.settle_purchase("human", box["state"], marker)
        # Require the existing debit and error-refund vocabulary in exact order.
        self.assertEqual(["BINGO_CARD_PURCHASED", "BINGO_CARD_REFUND_AFTER_ERROR"], [movement["transaction_type"] for movement in settlement.movements])
        # Release the failed prepared marker after compensation.
        self.assertNotIn(api.PENDING_ACTION_KEY, box["state"])
        # Never publish an association when no session was accepted.
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY, box["state"])
        # Preserve the empty established session state.
        self.assertIsNone(box["state"]["active_session"])

    # Keep failed compensation recoverable without inventing a session association. (TEST-265)
    def test_failed_compensation_retains_prepared_marker_without_association(self):
        # Seed one prepared purchase whose debit succeeds before session creation fails.
        marker = {"kind": "purchase", "status": "prepared", "purchase_id": "purchase-refund-failed", "player_id": "human", "amount": 5.0, "pattern": "line"}
        # Own the authoritative state that must remain recoverable after refund failure.
        box = {"state": {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker)}}

        # Fail only the compensating movement after retaining the successful debit audit.
        class RefundFailure(self._Settlement):
            # Commit the debit but refuse the error-refund response.
            def apply_once(inner_self, **movement):
                # Surface the exact injected failure at compensation time.
                if movement["transaction_type"] == "BINGO_CARD_REFUND_AFTER_ERROR":
                    # Retain the attempted movement for ordered evidence.
                    inner_self.movements.append(copy.deepcopy(movement))
                    # Abort before any compensation event can be claimed.
                    raise RuntimeError("refund failed")
                # Preserve the successful debit behavior from the base fake.
                return super().apply_once(**movement)

        # Record both the accepted debit and failed compensation attempt.
        settlement = RefundFailure()
        # Enter detached provider boundaries.
        update_patch, read_patch = self._provider_patches(box)
        # Fail session creation and then its required compensating refund.
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", return_value=[]), mock.patch.object(api.engine, "start_session", side_effect=RuntimeError("session creation failed")):
            # Surface the compensation failure so the prepared action remains explicit.
            with self.assertRaisesRegex(RuntimeError, "refund failed"):
                # Exercise the complete recovery boundary.
                api.settle_purchase("human", box["state"], marker)
        # Require the exact debit followed by its failed refund attempt.
        self.assertEqual(["BINGO_CARD_PURCHASED", "BINGO_CARD_REFUND_AFTER_ERROR"], [movement["transaction_type"] for movement in settlement.movements])
        # Keep the prepared marker available because compensation did not converge.
        self.assertEqual(marker, box["state"][api.PENDING_ACTION_KEY])
        # Never claim a debit/session association without an accepted session.
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY, box["state"])
        self.assertIsNone(box["state"]["active_session"])

    # Require reset/refund cleanup to preserve the private terminal association. (TEST-265)
    def test_reset_refund_preserves_association_after_active_session_cleanup(self):
        # Build the exact active session selected for reset.
        session = self._session("bingo-reset-1")
        # Seed its previously committed purchase association.
        association = {"purchase_id": "purchase-reset-1", "session_id": session["session_id"]}
        # Own the complete provider-current document.
        box = {"state": {"active_session": copy.deepcopy(session), "last_sessions": [], api.PURCHASE_ASSOCIATIONS_KEY: [association]}}
        # Record the unchanged card refund movement.
        settlement = self._Settlement()
        # Enter detached provider boundaries.
        update_patch, read_patch = self._provider_patches(box)
        # Isolate reset settlement from external player/history stores.
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api.players, "get_player", return_value={"balance": 10.0}), mock.patch.object(api, "append_history"):
            # Reserve reset ownership against the exact active session.
            marker = api.prepare_reset("human", box["state"])
            # Refund and clear the active session through production finalization.
            refunds = api.settle_prepared_reset("human", box["state"], marker)
        # Require the one established funded-card refund.
        self.assertEqual(["BINGO_CARD_REFUND"], [movement["transaction_type"] for movement in settlement.movements])
        self.assertEqual(1, len(refunds))
        # Clear both active state and transient reset ownership.
        self.assertIsNone(box["state"]["active_session"])
        self.assertNotIn(api.PENDING_ACTION_KEY, box["state"])
        # Preserve the raw association for future authoritative outcome joins.
        self.assertEqual("purchase-reset-1", api._purchase_id_for_session(box["state"], session["session_id"]))
        # Keep reset responses and public state free of the private purchase identity.
        self.assertNotIn("purchase-reset-1", json.dumps(refunds, sort_keys=True))
        self.assertNotIn("purchase-reset-1", json.dumps(api._public_state(box["state"]), sort_keys=True))

    # Bound orphan history while pinning active and retained terminal session joins. (TEST-265)
    def test_retention_is_bounded_without_evicting_visible_session_associations(self):
        # Pin one active and one retained terminal session in public game state.
        state = {"active_session": {"session_id": "active-pinned"}, "last_sessions": [{"session_id": "terminal-pinned"}]}
        # Publish the exact pinned associations first.
        api._retain_purchase_session_association(state, "purchase-active", "active-pinned")
        api._retain_purchase_session_association(state, "purchase-terminal", "terminal-pinned")
        # Add more removed/reset session joins than the bounded historical ceiling.
        for index in range(api.PURCHASE_ASSOCIATION_HISTORY_LIMIT + 2):
            # Use deterministic disjoint identifiers for every historical pair.
            api._retain_purchase_session_association(state, f"purchase-history-{index}", f"session-history-{index}")
        # Keep both visible-session joins plus exactly the historical ceiling.
        self.assertEqual(api.PURCHASE_ASSOCIATION_HISTORY_LIMIT + 2, len(state[api.PURCHASE_ASSOCIATIONS_KEY]))
        # Never evict associations for sessions still retained by game state.
        self.assertEqual("purchase-active", api._purchase_id_for_session(state, "active-pinned"))
        self.assertEqual("purchase-terminal", api._purchase_id_for_session(state, "terminal-pinned"))
        # Evict the oldest orphaned histories while retaining the newest boundary.
        self.assertIsNone(api._purchase_id_for_session(state, "session-history-0"))
        self.assertIsNone(api._purchase_id_for_session(state, "session-history-1"))
        self.assertEqual("purchase-history-2", api._purchase_id_for_session(state, "session-history-2"))
        # Freeze exact replay bytes before checking identity immutability.
        replay_state = copy.deepcopy(state)
        # Make an exact replay a no-op without changing retention order.
        api._retain_purchase_session_association(state, "purchase-active", "active-pinned")
        self.assertEqual(replay_state, state)
        # Refuse rebinding either side of the one-to-one relationship.
        with self.assertRaisesRegex(ConflictError, "identity changed"):
            api._retain_purchase_session_association(state, "purchase-active", "different-session")
        with self.assertRaisesRegex(ConflictError, "identity changed"):
            api._retain_purchase_session_association(state, "different-purchase", "active-pinned")

    # Require JSON and transaction-faithful MySQL documents to survive restart identically. (TEST-265)
    def test_json_and_mysql_document_models_persist_equivalent_private_associations(self):
        # Build one state whose active session pins the new association.
        def default_state():
            # Return a fresh detached default for each provider.
            return {"active_session": {"session_id": "provider-session"}, "last_sessions": []}

        # Add the production association through a provider-owned document mutator.
        def associate(current):
            # Persist the same exact private fact independent of backend representation.
            api._retain_purchase_session_association(current, "provider-purchase", "provider-session")
            # Return the complete document for provider publication.
            return current

        # Own all JSON provider bytes inside a disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Construct the production JSON provider over isolated storage.
            json_provider = storage.JsonStorageProvider(Path(temporary))
            # Publish the association through its locked document transaction.
            json_updated = json_provider.update_document("games/bingo/association-test.json", associate, default_state)
            # Restart with a new provider object over the same durable bytes.
            json_restarted = storage.JsonStorageProvider(Path(temporary))
            # Read the complete restarted JSON document.
            json_observed = json_restarted.read_document("games/bingo/association-test.json", default_state)
        # Construct the reviewed connector-free relational transaction model.
        mysql_database = _Database()
        # Publish through the production MySQL update_document implementation.
        mysql_updated = _Provider(mysql_database).update_document("games/bingo/association-test.json", associate, default_state)
        # Restart with a new provider facade over the same committed relational image.
        mysql_observed = _Provider(mysql_database).read_document("games/bingo/association-test.json", default_state)
        # Require equivalent publication and restart state across both providers.
        self.assertEqual(json_updated, json_observed)
        self.assertEqual(mysql_updated, mysql_observed)
        self.assertEqual(json_observed, mysql_observed)
        # Resolve the exact raw purchase identity after both restart boundaries.
        self.assertEqual("provider-purchase", api._purchase_id_for_session(json_observed, "provider-session"))
        # Keep the same private bytes absent from the common public state shape.
        self.assertNotIn("provider-purchase", json.dumps(api._public_state(mysql_observed), sort_keys=True))


# Execute the focused evidence file directly for local diagnosis.
if __name__ == "__main__":
    # Run concise standard unittest reporting.
    unittest.main()
