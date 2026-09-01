# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Prove durable private Bingo purchase-to-session association behavior."""

# Import detached copies for transaction-faithful provider boundaries.
import copy
# Import JSON encoding for recursive public-privacy assertions.
import json
# Import isolated filesystem ownership for restart evidence.
import tempfile
# Import the standard unit-test framework and focused patching seams.
import unittest
from pathlib import Path
from unittest import mock

# Import the provider facade used by temporary JSON restart evidence.
from casino.core import storage
# Import the production Bingo association and lifecycle transitions.
from casino.games.bingo import api, engine
# Import the stable public conflict category asserted by recovery tests.
from casino.errors import ConflictError
# Reuse the accepted disposable MySQL harness without changing its gate.
from tests.storage_conformance.database_harnesses import MySQLHarness
# Reuse the always-local temporary JSON harness.
from tests.storage_conformance.harness import JsonHarness


# Prove the private authoritative association across lifecycle and provider boundaries. (BINGO-029, TEST-265)
class BingoPurchaseSessionAssociationTests(unittest.TestCase):
    """Exercise only private association production, recovery, privacy, and retention."""

    # Build one complete active session with a single funded human card.
    @staticmethod
    def _session(session_id: str = "bingo-session-1") -> dict:
        card = {"card_id": f"card-{session_id}", "player_id": "human", "amount": 5.0, "card": {}, "status": "active", "winner": False, "payout": 0, "source": "manual"}
        return {"session_id": session_id, "player_id": "human", "amount": 5.0, "pattern": "line", "card": card["card"], "cards": [card], "called": [], "status": "active", "created_at": "2026-08-31T00:00:00Z", "winner": None, "winning_card_id": None, "payout": 0, "max_calls": 50}

    # Build the exact prepared marker persisted before any wallet movement.
    @staticmethod
    def _marker(purchase_id: str = "purchase-private-1") -> dict:
        return {"kind": "purchase", "status": "prepared", "purchase_id": purchase_id, "player_id": "human", "amount": 5.0, "pattern": "line"}

    # Build a valid maximum-retention document in provider transaction order.
    @classmethod
    def _retention_boundary_state(cls) -> dict:
        # Retain the oldest-to-newest thousand history-only associations first.
        history = [{"purchase_id": f"purchase-history-{index}", "session_id": f"history-{index}"} for index in range(api.PURCHASE_ASSOCIATION_HISTORY_LIMIT)]
        # Retain the engine's complete fifty-session archive after older history.
        archived = [{"session_id": f"archived-{index}"} for index in range(50)]
        archived_associations = [{"purchase_id": f"purchase-archived-{index}", "session_id": f"archived-{index}"} for index in range(50)]
        # Make the current active purchase the newest durable relationship.
        active = cls._session("active-boundary")
        active_association = {"purchase_id": "purchase-active-boundary", "session_id": active["session_id"]}
        # Return the exact one-active, fifty-archive, and thousand-history ceiling.
        return {"active_session": active, "last_sessions": archived, api.PURCHASE_ASSOCIATIONS_KEY: [*history, *archived_associations, active_association]}

    # Build one in-memory provider update seam that rolls back callback failures.
    @staticmethod
    def _memory_update(box: dict, lose_when=None):
        lost = {"value": False}

        def update(_game_id, _player_id, mutator, _default_factory):
            before = copy.deepcopy(box["state"])
            working = copy.deepcopy(before)
            updated = mutator(working)
            box["state"] = copy.deepcopy(updated)
            result = copy.deepcopy(updated)
            if lose_when is not None and not lost["value"] and lose_when(before, updated):
                lost["value"] = True
                raise RuntimeError("synthetic post-commit response loss")
            return result

        return update

    # Patch provider reads and writes around one authoritative in-memory document.
    @classmethod
    def _provider_patches(cls, box: dict, lose_when=None):
        update = mock.patch.object(api, "update_player_game_state", side_effect=cls._memory_update(box, lose_when))
        read = mock.patch.object(api, "load_player_game_state", side_effect=lambda *_args, **_kwargs: copy.deepcopy(box["state"]))
        return update, read

    # Model successful exactly-once settlement events without touching a wallet provider.
    class _Settlement:
        def __init__(self) -> None:
            self.movements = []

        def apply_once(self, **movement):
            self.movements.append(copy.deepcopy(movement))
            event = {"ledger_id": f"ledger-{len(self.movements)}", "game": "bingo", "player_id": movement["player_id"], "amount": movement["signed_amount"], "transaction_type": movement["transaction_type"], "round_id": movement["round_id"], "details": copy.deepcopy(movement["details"])}
            return event, False

        def find(self, *_args, **_kwargs):
            return None

        def validate_existing(self, *_args, **_kwargs):
            raise AssertionError("unexpected settlement recovery")

    # Run one production document mutation and restart through an accepted provider harness.
    def _exercise_harness(self, harness) -> None:
        unavailable = harness.unavailable_reason()
        if unavailable is not None:
            self.skipTest(unavailable)
        root = getattr(harness, "root", None)
        try:
            provider = harness.create()
            root = getattr(harness, "root", root)
            key = f"games/bingo/association-{harness.name}.json"

            def default_state():
                return {"active_session": {"session_id": "provider-session"}, "last_sessions": []}

            def associate(current):
                api._retain_purchase_session_association(current, "provider-purchase", "provider-session")
                return current

            updated = provider.update_document(key, associate, default_state)
            restarted_close_pool = None
            if harness.name == "json":
                restarted = storage.JsonStorageProvider(Path(root))
            else:
                close_pool = getattr(provider, "close_pool", None)
                if callable(close_pool):
                    close_pool()
                # Reconstruct the production provider over the same target instead of reusing its closed pool.
                restarted = storage.MySQLStorageProvider(provider.config)
                self.assertIsNot(provider, restarted)
                restarted_close_pool = restarted.close_pool
            try:
                observed = restarted.read_document(key, default_state)
                self.assertEqual(updated, observed)
                self.assertEqual("provider-purchase", api._purchase_id_for_session(observed, "provider-session"))
                self.assertNotIn("provider-purchase", json.dumps(api._public_state(observed), sort_keys=True))
            finally:
                # Release the restart-owned pool before the harness drops its synthetic database and accounts.
                if restarted_close_pool is not None:
                    restarted_close_pool()
        except BaseException:
            try:
                harness.destroy()
            except BaseException:
                pass
            raise
        else:
            harness.destroy()
        if root is not None:
            self.assertFalse(Path(root).exists(), "successful association harness left disposable state behind")

    # Require recursive exact-key redaction while preserving similarly named public fields. (TEST-265)
    def test_public_projection_recursively_removes_only_private_keys(self):
        purchase_id = "purchase-private-nested"
        state = {
            "active_session": {
                "session_id": "session-public",
                api.PENDING_ACTION_KEY: {"purchase_id": purchase_id},
                "nested": [{api.PURCHASE_ASSOCIATIONS_KEY: [{"purchase_id": purchase_id, "session_id": "session-public"}]}],
            },
            "last_sessions": [
                {"session_id": "session-archived", "deep": ({api.PENDING_ACTION_KEY: {"purchase_id": purchase_id}},)},
            ],
            api.PURCHASE_ASSOCIATIONS_KEY: [{"purchase_id": purchase_id, "session_id": "session-public"}],
            "_bingo_pending_action_public": "preserved",
            "_bingo_purchase_session_associations_public": "preserved",
        }
        before = copy.deepcopy(state)
        public = api._public_state(state)
        encoded = json.dumps(public, sort_keys=True)
        self.assertNotIn(api.PENDING_ACTION_KEY + '"', encoded)
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY + '"', encoded)
        self.assertNotIn(purchase_id, encoded)
        self.assertEqual("preserved", public["_bingo_pending_action_public"])
        self.assertEqual("preserved", public["_bingo_purchase_session_associations_public"])
        self.assertEqual(before, state)

    # Prove every registered mutating route sanitizes its explicit sibling session projection. (TEST-265)
    def test_registered_mutating_routes_redact_explicit_session_projection(self):
        # Record the real registered handler functions without opening a listener.
        class Router:
            def __init__(self):
                self.handlers = {}

            def get(self, path):
                return self._register("GET", path)

            def post(self, path):
                return self._register("POST", path)

            def _register(self, method, path):
                def decorator(handler):
                    self.handlers[(method, path)] = handler
                    return handler
                return decorator

        router = Router()
        api.register(router)
        purchase_id = "purchase-private-route-leak"
        session = self._session("session-route-public")
        session["nested"] = [
            {api.PENDING_ACTION_KEY: {"purchase_id": purchase_id}},
            {api.PURCHASE_ASSOCIATIONS_KEY: [{"purchase_id": purchase_id, "session_id": session["session_id"]}]},
        ]
        session["_bingo_pending_action_public"] = "preserved"
        session["_bingo_purchase_session_associations_public"] = "preserved"
        state = {"active_session": copy.deepcopy(session), "last_sessions": [], api.PURCHASE_ASSOCIATIONS_KEY: [{"purchase_id": purchase_id, "session_id": session["session_id"]}]}
        player = {"player_id": "human", "type": "human", "balance": 10.0}
        committed_call = {"kind": "call", "status": "committed", "action_id": "route-call", "session_id": session["session_id"], "calls": [1], "terminal": False, "history_claims": []}
        with mock.patch.object(api, "request_player_id", return_value="human"), mock.patch.object(api, "require_amount", return_value=5.0), mock.patch.object(api, "load_player_game_state", side_effect=lambda *_args, **_kwargs: copy.deepcopy(state)), mock.patch.object(api, "resume_pending_action"), mock.patch.object(api, "prepare_purchase", return_value=self._marker(purchase_id)), mock.patch.object(api, "settle_purchase", return_value=copy.deepcopy(session)), mock.patch.object(api, "commit_calls", return_value=committed_call), mock.patch.object(api, "settle_committed_call", return_value=(copy.deepcopy(session), [1], [])), mock.patch.object(api.players, "list_players", return_value=[player]), mock.patch.object(api.players, "get_player", return_value=player):
            responses = (
                router.handlers[("POST", "/api/v1/games/bingo/cards")]({"amount": 5.0}, {}),
                router.handlers[("POST", "/api/v1/games/bingo/call")]({}, {}),
                router.handlers[("POST", "/api/v1/games/bingo/auto")]({"max_calls": 1}, {}),
            )
            empty_auto = router.handlers[("POST", "/api/v1/games/bingo/auto")]({"max_calls": 0}, {})
        for response in responses:
            for projection in (response["state"], response["session"]):
                encoded = json.dumps(projection, sort_keys=True)
                self.assertNotIn(api.PENDING_ACTION_KEY + '"', encoded)
                self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY + '"', encoded)
                self.assertNotIn(purchase_id, encoded)
            self.assertEqual("preserved", response["session"]["_bingo_pending_action_public"])
            self.assertEqual("preserved", response["session"]["_bingo_purchase_session_associations_public"])
        self.assertIsNone(empty_auto["session"])
        self.assertEqual(session, state["active_session"])

    # Validate exact two-field rows, identifier grammar, uniqueness, and the hard total ceiling. (TEST-265)
    def test_association_schema_identifier_and_size_policy_fail_closed(self):
        valid_191 = "a" * 191
        valid = [{"purchase_id": "p", "session_id": valid_191}]
        self.assertEqual(valid, api._validated_purchase_session_associations({api.PURCHASE_ASSOCIATIONS_KEY: valid}))
        invalid_rows = (
            "not-a-list",
            [{}],
            [{"purchase_id": "p"}],
            [{"purchase_id": "p", "session_id": "s", "extra": "x"}],
            [{"purchase_id": "", "session_id": "s"}],
            [{"purchase_id": "p", "session_id": "a" * 192}],
            [{"purchase_id": "purchase:1", "session_id": "s"}],
            [{"purchase_id": "p", "session_id": "séssion"}],
            [{"purchase_id": 1, "session_id": "s"}],
            [{"purchase_id": "same", "session_id": "s1"}, {"purchase_id": "same", "session_id": "s2"}],
            [{"purchase_id": "p1", "session_id": "same"}, {"purchase_id": "p2", "session_id": "same"}],
            [{"purchase_id": f"p-{index}", "session_id": f"s-{index}"} for index in range(api.PURCHASE_ASSOCIATION_MAX_RECORDS + 1)],
        )
        for index, rows in enumerate(invalid_rows):
            with self.subTest(case=index), self.assertRaisesRegex(ConflictError, "association state is invalid"):
                api._validated_purchase_session_associations({api.PURCHASE_ASSOCIATIONS_KEY: rows})
        for invalid_id in ("", "x" * 192, "with space", "with:colon", "with/slash", "é", None, 7):
            with self.subTest(identity=repr(invalid_id)), self.assertRaisesRegex(ConflictError, "identity is invalid"):
                api._retain_purchase_session_association(engine.default_state(), invalid_id, "session-valid")

    # Refuse corrupt rows after session allocation and roll back the complete provider transaction. (TEST-265)
    def test_invalid_association_records_roll_back_session_publication(self):
        marker = self._marker("shape-purchase")
        malformed = [{"purchase_id": "older-purchase", "session_id": "older-session", "extra": "forbidden"}]
        with tempfile.TemporaryDirectory() as temporary:
            provider = storage.JsonStorageProvider(Path(temporary))
            key = "games/bingo/invalid-association.json"
            before = {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker), api.PURCHASE_ASSOCIATIONS_KEY: malformed}
            provider.write_document(key, before)
            real_start = engine.start_session
            update = lambda _game, _player, mutator, default: provider.update_document(key, mutator, default)
            with mock.patch.object(api, "update_player_game_state", side_effect=update), mock.patch.object(api.engine, "start_session", wraps=real_start) as start:
                with self.assertRaisesRegex(ConflictError, "association state is invalid"):
                    api.commit_purchase("human", copy.deepcopy(before), marker, [])
                start.assert_called_once()
            self.assertEqual(before, provider.read_document(key, engine.default_state))

    # Exercise the complete workflow when session publication commits but its response is lost. (TEST-265)
    def test_settle_purchase_recovers_commit_response_loss_without_refund(self):
        self._assert_whole_settle_response_loss("commit")

    # Exercise the complete workflow when marker finalization commits but its response is lost. (TEST-265)
    def test_settle_purchase_recovers_finalize_response_loss_without_refund(self):
        self._assert_whole_settle_response_loss("finalize")

    # Share exact debit, session, association, and refund assertions across both response-loss phases.
    def _assert_whole_settle_response_loss(self, phase: str) -> None:
        marker = self._marker(f"purchase-{phase}-loss")
        box = {"state": {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker)}}
        settlement = self._Settlement()
        starts = {"count": 0}

        def start(current, _player_id, _amount, _pattern, *, bot_players):
            self.assertEqual([], bot_players)
            starts["count"] += 1
            current["active_session"] = self._session(f"session-{phase}-loss")
            return current["active_session"]

        def lose_when(before, after):
            before_pending = before.get(api.PENDING_ACTION_KEY)
            after_pending = after.get(api.PENDING_ACTION_KEY)
            if phase == "commit":
                return isinstance(before_pending, dict) and before_pending.get("status") == "prepared" and isinstance(after_pending, dict) and after_pending.get("status") == "committed"
            return isinstance(before_pending, dict) and before_pending.get("status") == "committed" and after_pending is None

        update_patch, read_patch = self._provider_patches(box, lose_when)
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", return_value=[]), mock.patch.object(api.engine, "start_session", side_effect=start):
            recovered = api.settle_purchase("human", box["state"], marker)
        self.assertEqual(f"session-{phase}-loss", recovered["session_id"])
        self.assertEqual(1, starts["count"])
        self.assertEqual(["BINGO_CARD_PURCHASED"], [movement["transaction_type"] for movement in settlement.movements])
        self.assertEqual([{"purchase_id": marker["purchase_id"], "session_id": recovered["session_id"]}], box["state"][api.PURCHASE_ASSOCIATIONS_KEY])
        self.assertNotIn(api.PENDING_ACTION_KEY, box["state"])

    # Promote only an exact committed legacy marker carrying both durable identities. (TEST-265)
    def test_legacy_promotion_requires_exact_committed_marker_and_session(self):
        session = self._session("legacy-session-1")
        prepared = self._marker("legacy-purchase-1")
        committed = {**prepared, "status": "committed", "session_id": session["session_id"]}
        legacy = {"active_session": copy.deepcopy(session), "last_sessions": [], api.PENDING_ACTION_KEY: copy.deepcopy(committed)}
        box = {"state": copy.deepcopy(legacy)}
        update_patch, read_patch = self._provider_patches(box)
        with update_patch, read_patch:
            finalized = api.finalize_purchase("human", box["state"], committed)
        self.assertEqual(session, finalized)
        self.assertEqual([{"purchase_id": committed["purchase_id"], "session_id": session["session_id"]}], box["state"][api.PURCHASE_ASSOCIATIONS_KEY])
        self.assertNotIn(api.PENDING_ACTION_KEY, box["state"])

        hostile_markers = (
            {key: value for key, value in committed.items() if key != "session_id"},
            {**committed, "status": "prepared"},
            {**committed, "extra": "forbidden"},
            {**committed, "session_id": "missing-session"},
        )
        for index, hostile in enumerate(hostile_markers):
            hostile_state = {"active_session": copy.deepcopy(session), "last_sessions": [], api.PENDING_ACTION_KEY: copy.deepcopy(hostile)}
            hostile_box = {"state": copy.deepcopy(hostile_state)}
            update_patch, read_patch = self._provider_patches(hostile_box)
            with self.subTest(case=index), update_patch, read_patch, self.assertRaises(ConflictError):
                api.finalize_purchase("human", hostile_box["state"], committed)
            self.assertEqual(hostile_state, hostile_box["state"])

    # Reject every tempting amount/time/order/ledger/history inference source. (TEST-265)
    def test_missing_association_is_never_inferred_from_public_or_money_evidence(self):
        session = self._session("coincidental-session")
        marker = {**self._marker("coincidental-purchase"), "status": "committed", "session_id": session["session_id"]}
        state = {
            "active_session": copy.deepcopy(session),
            "last_sessions": [{**copy.deepcopy(session), "display_reference": marker["purchase_id"]}],
            "ledger": [{"round_id": marker["purchase_id"], "amount": -5.0, "timestamp": session["created_at"]}],
            "history": [{"session_id": session["session_id"], "amount": 5.0, "ordinal": 0}],
        }
        box = {"state": copy.deepcopy(state)}
        update_patch, read_patch = self._provider_patches(box)
        with update_patch, read_patch, self.assertRaisesRegex(ConflictError, "association is unavailable"):
            api.finalize_purchase("human", box["state"], marker)
        self.assertEqual(state, box["state"])
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY, box["state"])

    # Compensate only a matching prepared marker with no association and no active session. (TEST-265)
    def test_definitive_failed_session_creation_compensates_without_association(self):
        marker = self._marker("purchase-failed")
        box = {"state": {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker)}}
        settlement = self._Settlement()
        update_patch, read_patch = self._provider_patches(box)
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", return_value=[]), mock.patch.object(api.engine, "start_session", side_effect=RuntimeError("session creation failed")):
            with self.assertRaisesRegex(RuntimeError, "session creation failed"):
                api.settle_purchase("human", box["state"], marker)
        self.assertEqual(["BINGO_CARD_PURCHASED", "BINGO_CARD_REFUND_AFTER_ERROR"], [movement["transaction_type"] for movement in settlement.movements])
        self.assertNotIn(api.PENDING_ACTION_KEY, box["state"])
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY, box["state"])
        self.assertIsNone(box["state"]["active_session"])

    # Keep an exact prepared marker when compensation itself cannot commit. (TEST-265)
    def test_failed_compensation_retains_marker_without_association(self):
        marker = self._marker("purchase-refund-failed")
        box = {"state": {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker)}}

        class RefundFailure(self._Settlement):
            def apply_once(inner_self, **movement):
                if movement["transaction_type"] == "BINGO_CARD_REFUND_AFTER_ERROR":
                    inner_self.movements.append(copy.deepcopy(movement))
                    raise RuntimeError("refund failed")
                return super().apply_once(**movement)

        settlement = RefundFailure()
        update_patch, read_patch = self._provider_patches(box)
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", return_value=[]), mock.patch.object(api.engine, "start_session", side_effect=RuntimeError("session creation failed")):
            with self.assertRaisesRegex(RuntimeError, "refund failed"):
                api.settle_purchase("human", box["state"], marker)
        self.assertEqual(marker, box["state"][api.PENDING_ACTION_KEY])
        self.assertNotIn(api.PURCHASE_ASSOCIATIONS_KEY, box["state"])

    # Refuse corrupt, unreadable, missing, changed, or accepted state before refund/rollback. (TEST-265)
    def test_ambiguous_recovery_never_compensates_or_rolls_back(self):
        marker = self._marker("purchase-ambiguous")
        session = self._session("session-ambiguous")
        hostile_states = (
            {**engine.default_state()},
            {api.PENDING_ACTION_KEY: copy.deepcopy(marker)},
            {"active_session": None, "last_sessions": "corrupt", api.PENDING_ACTION_KEY: copy.deepcopy(marker)},
            {**engine.default_state(), api.PENDING_ACTION_KEY: {**marker, "purchase_id": "different-purchase"}},
            {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker), api.PURCHASE_ASSOCIATIONS_KEY: "corrupt"},
            {"active_session": copy.deepcopy(session), "last_sessions": [], api.PENDING_ACTION_KEY: copy.deepcopy(marker)},
            {**engine.default_state(), api.PENDING_ACTION_KEY: {**marker, "status": "committed", "session_id": "missing-session"}},
        )
        for index, current in enumerate(hostile_states):
            settlement = self._Settlement()
            with self.subTest(case=index), mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", side_effect=RuntimeError("trigger recovery")), mock.patch.object(api, "load_player_game_state", return_value=copy.deepcopy(current)), mock.patch.object(api, "rollback_purchase") as rollback:
                with self.assertRaisesRegex(ConflictError, api.PURCHASE_RECOVERY_CONFLICT):
                    api.settle_purchase("human", copy.deepcopy(current), marker)
                self.assertEqual(["BINGO_CARD_PURCHASED"], [movement["transaction_type"] for movement in settlement.movements])
                rollback.assert_not_called()
        settlement = self._Settlement()
        with mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", side_effect=RuntimeError("trigger recovery")), mock.patch.object(api, "load_player_game_state", side_effect=RuntimeError("read failed")), mock.patch.object(api, "rollback_purchase") as rollback:
            with self.assertRaisesRegex(ConflictError, api.PURCHASE_RECOVERY_CONFLICT):
                api.settle_purchase("human", engine.default_state(), marker)
            self.assertEqual(["BINGO_CARD_PURCHASED"], [movement["transaction_type"] for movement in settlement.movements])
            rollback.assert_not_called()

    # Refuse a finalize-time caller/link mismatch without compensating the accepted purchase. (TEST-265)
    def test_finalize_link_mismatch_never_compensates_or_rolls_back(self):
        marker = self._marker("purchase-link-mismatch")
        accepted = self._session("session-accepted")
        conflicting = self._session("session-conflicting")
        current = {"active_session": conflicting, "last_sessions": [], api.PURCHASE_ASSOCIATIONS_KEY: [{"purchase_id": marker["purchase_id"], "session_id": conflicting["session_id"]}]}
        settlement = self._Settlement()
        with mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api, "seat_competitors", return_value=[]), mock.patch.object(api, "commit_purchase", return_value=accepted), mock.patch.object(api, "finalize_purchase", side_effect=RuntimeError("trigger recovery")), mock.patch.object(api, "load_player_game_state", return_value=copy.deepcopy(current)), mock.patch.object(api, "rollback_purchase") as rollback:
            with self.assertRaisesRegex(ConflictError, api.PURCHASE_RECOVERY_CONFLICT):
                api.settle_purchase("human", engine.default_state(), marker)
            self.assertEqual(["BINGO_CARD_PURCHASED"], [movement["transaction_type"] for movement in settlement.movements])
            rollback.assert_not_called()

    # Preserve the association after reset refunds and active-session cleanup. (TEST-265)
    def test_reset_refund_preserves_association(self):
        session = self._session("bingo-reset-1")
        association = {"purchase_id": "purchase-reset-1", "session_id": session["session_id"]}
        box = {"state": {"active_session": copy.deepcopy(session), "last_sessions": [], api.PURCHASE_ASSOCIATIONS_KEY: [association]}}
        settlement = self._Settlement()
        update_patch, read_patch = self._provider_patches(box)
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api.players, "get_player", return_value={"balance": 10.0}), mock.patch.object(api, "append_history"):
            reset_marker = api.prepare_reset("human", box["state"])
            refunds = api.settle_prepared_reset("human", box["state"], reset_marker)
        self.assertEqual(["BINGO_CARD_REFUND"], [movement["transaction_type"] for movement in settlement.movements])
        self.assertEqual(1, len(refunds))
        self.assertIsNone(box["state"]["active_session"])
        self.assertEqual("purchase-reset-1", api._purchase_id_for_session(box["state"], session["session_id"]))
        self.assertNotIn("purchase-reset-1", json.dumps(api._public_state(box["state"]), sort_keys=True))

    # Enforce one active, fifty archived, and one thousand newest history-only rows. (TEST-265)
    def test_retention_is_exactly_bounded_at_1051(self):
        archived = [{"session_id": f"archived-{index}"} for index in range(50)]
        state = {"active_session": {"session_id": "active-pinned"}, "last_sessions": archived}
        api._retain_purchase_session_association(state, "purchase-active", "active-pinned")
        for index in range(50):
            api._retain_purchase_session_association(state, f"purchase-archived-{index}", f"archived-{index}")
        for index in range(api.PURCHASE_ASSOCIATION_HISTORY_LIMIT + 2):
            api._retain_purchase_session_association(state, f"purchase-history-{index}", f"history-{index}")
        self.assertEqual(api.PURCHASE_ASSOCIATION_MAX_RECORDS, len(state[api.PURCHASE_ASSOCIATIONS_KEY]))
        self.assertEqual("purchase-active", api._purchase_id_for_session(state, "active-pinned"))
        for index in range(50):
            self.assertEqual(f"purchase-archived-{index}", api._purchase_id_for_session(state, f"archived-{index}"))
        self.assertIsNone(api._purchase_id_for_session(state, "history-0"))
        self.assertIsNone(api._purchase_id_for_session(state, "history-1"))
        self.assertEqual("purchase-history-2", api._purchase_id_for_session(state, "history-2"))
        before_replay = copy.deepcopy(state)
        api._retain_purchase_session_association(state, "purchase-active", "active-pinned")
        self.assertEqual(before_replay, state)
        with self.assertRaisesRegex(ConflictError, "identity changed"):
            api._retain_purchase_session_association(state, "purchase-active", "different-session")
        with self.assertRaisesRegex(ConflictError, "identity changed"):
            api._retain_purchase_session_association(state, "different-purchase", "active-pinned")

    # Reapply newest-history retention when terminal archival or reset changes pinned membership. (TEST-265)
    def test_terminal_and_reset_transitions_renormalize_retention_boundary(self):
        # Move the active session into a full archive and evict its oldest predecessor.
        terminal_box = {"state": self._retention_boundary_state()}

        def terminal_call(current):
            session = copy.deepcopy(current["active_session"])
            session["status"] = "no_win"
            session["called"] = [1]
            current["active_session"] = None
            current["last_sessions"].append(copy.deepcopy(session))
            current["last_sessions"] = current["last_sessions"][-50:]
            return session, 1

        update_patch, read_patch = self._provider_patches(terminal_box)
        with update_patch, read_patch, mock.patch.object(api, "new_id", return_value="call-retention-boundary"), mock.patch.object(api.engine, "call_next", side_effect=terminal_call):
            marker = api.commit_calls("human", terminal_box["state"], 1)
        self.assertTrue(marker["terminal"])
        self.assertEqual(api.PURCHASE_ASSOCIATION_MAX_RECORDS - 1, len(terminal_box["state"][api.PURCHASE_ASSOCIATIONS_KEY]))
        self.assertIsNone(api._purchase_id_for_session(terminal_box["state"], "history-0"))
        self.assertEqual("purchase-archived-0", api._purchase_id_for_session(terminal_box["state"], "archived-0"))
        self.assertEqual("purchase-active-boundary", api._purchase_id_for_session(terminal_box["state"], "active-boundary"))

        # Reset the newest active session so it becomes history while preserving all fifty archives.
        reset_box = {"state": self._retention_boundary_state()}
        settlement = self._Settlement()
        update_patch, read_patch = self._provider_patches(reset_box)
        with update_patch, read_patch, mock.patch.object(api, "SETTLEMENT", settlement), mock.patch.object(api.players, "get_player", return_value={"balance": 10.0}), mock.patch.object(api, "append_history"):
            reset_marker = api.prepare_reset("human", reset_box["state"])
            api.settle_prepared_reset("human", reset_box["state"], reset_marker)
        self.assertEqual(api.PURCHASE_ASSOCIATION_MAX_RECORDS - 1, len(reset_box["state"][api.PURCHASE_ASSOCIATIONS_KEY]))
        self.assertIsNone(api._purchase_id_for_session(reset_box["state"], "history-0"))
        self.assertEqual("purchase-active-boundary", api._purchase_id_for_session(reset_box["state"], "active-boundary"))
        self.assertEqual("purchase-archived-0", api._purchase_id_for_session(reset_box["state"], "archived-0"))

    # Always exercise production JSON persistence and restart through the reviewed harness. (TEST-265)
    def test_json_harness_persists_private_association_across_restart(self):
        self._exercise_harness(JsonHarness())

    # Prepare hosted disposable MySQL evidence behind its accepted exact marker and cleanup guard. (TEST-265)
    def test_mysql_harness_persists_private_association_across_restart(self):
        self._exercise_harness(MySQLHarness())

# Execute the focused evidence file directly for local diagnosis.
if __name__ == "__main__":
    unittest.main()
