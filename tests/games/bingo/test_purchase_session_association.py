# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Durable private Bingo purchase-to-session association evidence."""

# Import detached copies for provider-faithful state boundaries.
import copy
# Import cleanup registration that still runs remaining guards when one cleanup raises.
from contextlib import ExitStack
# Import JSON encoding for recursive public-omission assertions.
import json
# Import environment access for disposable-target guards and selector restoration.
import os
# Import isolated filesystem ownership for restart evidence.
import tempfile
# Import the standard unit-test framework.
import unittest
# Import portable paths for the disposable JSON provider.
from pathlib import Path
# Import focused patching for state, engine, settlement, and history seams.
from unittest import mock

# Import the production player, provider, and state seams used by live proof.
from casino.core import players, state_store, storage
# Import the production Bingo association and lifecycle transitions.
from casino.games.bingo import api, engine
# Import the public conflict contract for immutable-identity assertions.
from casino.errors import ConflictError
# Reuse the reviewed transaction-faithful MySQL document model without a connector.
from tests.mysql_game_action_provider_tests import _Database, _Provider


# Require the parent live matrix's exact disposable identities before provider construction. (TEST-265)
def _require_disposable_mysql_matrix() -> None:
    # Require the explicit opt-in consumed by the parent migration harness.
    if os.environ.get("CASINO_MYSQL_DISPOSABLE_TEST") != "1":
        # Refuse before optional-driver import or provider construction.
        raise AssertionError("Disposable MySQL Bingo test is not explicitly enabled")
    # Require every administrative, migration, and runtime host to be literal loopback.
    hosts = [os.environ.get(name) for name in ("CASINO_MYSQL_TEST_ADMIN_HOST", "CASINO_MYSQL_MIGRATION_HOST", "CASINO_MYSQL_HOST")]
    # Reject missing, aliased, whitespace-bearing, or remote endpoints.
    if hosts != ["127.0.0.1", "127.0.0.1", "127.0.0.1"]:
        # Preserve the parent harness's loopback-only invariant.
        raise AssertionError("Disposable MySQL Bingo endpoints must be exact loopback")
    # Read all ports without defaults so absent values cannot appear equal.
    raw_ports = [os.environ.get(name) for name in ("CASINO_MYSQL_TEST_ADMIN_PORT", "CASINO_MYSQL_MIGRATION_PORT", "CASINO_MYSQL_PORT")]
    # Require present ASCII-decimal values before parsing.
    if any(not isinstance(value, str) or not value.isascii() or not value.isdecimal() for value in raw_ports):
        # Refuse malformed or absent port tuples.
        raise AssertionError("Disposable MySQL Bingo ports are invalid")
    # Parse each explicit value once.
    ports = [int(value) for value in raw_ports]
    # Require a valid equal TCP port for all three roles.
    if any(port < 1 or port > 65535 for port in ports) or len(set(ports)) != 1:
        # Refuse split or out-of-range service tuples.
        raise AssertionError("Disposable MySQL Bingo ports do not match")
    # Reuse the parent harness's exact `_204` identifier grammar without connecting.
    from tests.mysql_migration_live import _identifier
    # Validate both database identifiers independently.
    runtime_database = _identifier(os.environ.get("CASINO_MYSQL_DATABASE", ""))
    migration_database = _identifier(os.environ.get("CASINO_MYSQL_MIGRATION_DATABASE", ""))
    # Require runtime and migration to select the same disposable target.
    if runtime_database != migration_database:
        # Refuse a split database tuple.
        raise AssertionError("Disposable MySQL Bingo databases do not match")
    # Validate both role identities independently through the parent grammar.
    runtime_user = _identifier(os.environ.get("CASINO_MYSQL_USER", ""))
    migration_user = _identifier(os.environ.get("CASINO_MYSQL_MIGRATION_USER", ""))
    # Preserve distinct DML and DDL authority.
    if runtime_user == migration_user:
        # Refuse privilege-boundary collapse.
        raise AssertionError("Disposable MySQL Bingo users must be distinct")
    # Require complete, distinct synthetic role secrets without exposing values.
    runtime_password = os.environ.get("CASINO_MYSQL_PASSWORD", "")
    migration_password = os.environ.get("CASINO_MYSQL_MIGRATION_PASSWORD", "")
    # Reject missing or shared role credentials.
    if not runtime_password or not migration_password or runtime_password == migration_password:
        # Preserve the parent matrix's role separation.
        raise AssertionError("Disposable MySQL Bingo credentials are invalid")
    # Require complete administrator cleanup authority without logging it.
    if not os.environ.get("CASINO_MYSQL_TEST_ADMIN_USER") or not os.environ.get("CASINO_MYSQL_TEST_ADMIN_PASSWORD"):
        # Refuse before callback-owned data can exist.
        raise AssertionError("Disposable MySQL Bingo administrator is incomplete")


# Restore exact provider-selector presence after every cleanup outcome. (TEST-265)
def _restore_storage_selector(previous: str | None) -> None:
    # Restore exact absence when the enclosing matrix had no selector.
    if previous is None:
        # Remove only the callback-owned selector.
        os.environ.pop("CASINO_STORAGE_PROVIDER", None)
    else:
        # Restore the inherited selector byte-for-byte.
        os.environ["CASINO_STORAGE_PROVIDER"] = previous


# Replace one real state-update response with a loss only after transaction commit. (TEST-265)
def _lose_first_update_response(original_update):
    # Track exactly one hidden successful response.
    lost = {"value": False}

    # Delegate every mutation to the real provider-owned state-store boundary.
    def update(*args, **kwargs):
        # Wait until the complete production transaction returns successfully.
        result = original_update(*args, **kwargs)
        # Hide only the first committed response.
        if not lost["value"]:
            # Preserve every later replay response.
            lost["value"] = True
            # Surface one fixed value-free transport category.
            raise RuntimeError("synthetic post-commit response loss")
        # Return later provider responses unchanged.
        return result

    # Return the one-shot production wrapper.
    return update


# Construct and inject one callback-owned provider under an existing cleanup stack. (TEST-265)
def _install_mysql_provider(cleanup: ExitStack):
    # Construct only after the caller registered selector restoration and provider clearing.
    provider = storage.MySQLStorageProvider()
    # Close this pool even when injection or later evidence fails.
    cleanup.callback(provider.close_pool)
    # Route production calls through the new provider.
    storage.set_provider_for_tests(provider)
    # Return the injected provider for direct bootstrap and ledger observations.
    return provider


# Run #1087 inside the existing guarded disposable MySQL 8.4 matrix. (BINGO-029, TEST-265)
def run_bingo_purchase_session_association_live() -> None:
    # Refuse unmarked, remote, mismatched, or malformed targets before provider construction.
    _require_disposable_mysql_matrix()
    # Preserve the enclosing workflow's provider selector exactly.
    previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
    # Register every cleanup before mutating process-global provider state.
    with ExitStack() as cleanup:
        # Restore the selector last even when pool or provider clearing raises.
        cleanup.callback(_restore_storage_selector, previous_provider_name)
        # Clear partial or complete provider injection on every exit path.
        cleanup.callback(storage.set_provider_for_tests, None)
        # Select MySQL only inside the protected callback scope.
        os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
        # Construct and inject a fresh runtime provider under registered cleanup.
        provider = _install_mysql_provider(cleanup)
        # Ensure default wallets exist without replacing prior live-matrix rows.
        provider.bootstrap_players(players.default_players())
        # Create one isolated wallet for the success/replay/reset lifecycle.
        player = players.create_player("Bingo Association Live", "guest", 100.0)
        # Retain its opaque identity only in process memory.
        player_id = player["player_id"]
        # Load a fresh player-scoped Bingo document.
        state = state_store.load_player_game_state(api.GAME_ID, player_id, engine.default_state)
        # Reserve one real purchase identity before its ledger debit.
        marker = api.prepare_purchase(player_id, state, 5.0, "line")
        # Capture the starting balance for exact debit/refund assertions.
        balance_before = players.get_player(player_id)["balance"]
        # Apply the stable human debit through the real settlement gateway.
        debit, debit_replayed = api._apply_movement(api._human_purchase_movement(marker))
        # Require a first commit and exactly one five-token wallet movement.
        assert debit_replayed is False
        assert round(players.get_player(player_id)["balance"], 2) == round(balance_before - 5.0, 2)
        # Replay the immutable debit identity through the same production provider.
        debit_again, debit_again_replayed = api._apply_movement(api._human_purchase_movement(marker))
        # Require one ledger identity and no second debit.
        assert debit_again_replayed is True and debit_again["ledger_id"] == debit["ledger_id"]
        assert round(players.get_player(player_id)["balance"], 2) == round(balance_before - 5.0, 2)

        # Preserve the real state-store function before hiding a committed response.
        original_update = api.update_player_game_state
        # Lose the first successful commit response without replacing transaction logic.
        with mock.patch.object(api, "update_player_game_state", side_effect=_lose_first_update_response(original_update)):
            # Require only the synthetic response-loss category.
            try:
                # Publish session and association together in one real MySQL transaction.
                api.commit_purchase(player_id, state, marker, [])
            except RuntimeError as exc:
                # Reject production/provider failures disguised as the synthetic seam.
                assert str(exc) == "synthetic post-commit response loss"
            else:
                # Fail if the wrapper did not hide the committed response.
                raise AssertionError("Bingo commit response was not lost")
        # Reload provider-authoritative state after response loss.
        committed_state = state_store.load_player_game_state(api.GAME_ID, player_id, engine.default_state)
        # Require the durable committed marker and accepted session.
        pending = committed_state[api.PENDING_ACTION_KEY]
        assert pending["kind"] == "purchase" and pending["status"] == "committed" and pending["purchase_id"] == marker["purchase_id"]
        # Require one exact private relationship before replay.
        expected_association = [{"purchase_id": marker["purchase_id"], "session_id": pending["session_id"]}]
        assert committed_state[api.PURCHASE_ASSOCIATIONS_KEY] == expected_association
        # Replay commit through another real row-locking transaction.
        session = api.commit_purchase(player_id, state, marker, [])
        # Require the same session, one association, and no wallet movement.
        assert session["session_id"] == pending["session_id"] and state[api.PURCHASE_ASSOCIATIONS_KEY] == expected_association
        assert round(players.get_player(player_id)["balance"], 2) == round(balance_before - 5.0, 2)

        # Bind finalization to exact durable purchase/session identities.
        committed_marker = {**marker, "status": "committed", "session_id": session["session_id"]}
        # Lose the first successful marker-cleanup response after transaction commit.
        with mock.patch.object(api, "update_player_game_state", side_effect=_lose_first_update_response(original_update)):
            # Require only the synthetic response-loss category.
            try:
                # Clear the transient marker only after association verification.
                api.finalize_purchase(player_id, state, committed_marker)
            except RuntimeError as exc:
                # Reject any provider-side failure.
                assert str(exc) == "synthetic post-commit response loss"
            else:
                # Fail if the wrapper did not hide the committed response.
                raise AssertionError("Bingo finalize response was not lost")
        # Read the committed marker-free state after response loss.
        finalized_state = state_store.load_player_game_state(api.GAME_ID, player_id, engine.default_state)
        # Require exact marker cleanup and association retention.
        assert api.PENDING_ACTION_KEY not in finalized_state and finalized_state[api.PURCHASE_ASSOCIATIONS_KEY] == expected_association
        # Replay finalization after the marker is already gone.
        finalized_session = api.finalize_purchase(player_id, state, committed_marker)
        # Require the same session and no duplicate association or debit.
        assert finalized_session["session_id"] == session["session_id"] and state[api.PURCHASE_ASSOCIATIONS_KEY] == expected_association
        assert round(players.get_player(player_id)["balance"], 2) == round(balance_before - 5.0, 2)

        # Close the first injected provider before process-equivalent reconstruction.
        storage.set_provider_for_tests(None)
        # Build and inject another provider under the same cleanup stack.
        restarted_provider = _install_mysql_provider(cleanup)
        # Reload the player document after provider reconstruction.
        restarted_state = state_store.load_player_game_state(api.GAME_ID, player_id, engine.default_state)
        # Prove marker cleanup and association persistence across restart.
        assert restarted_state[api.PURCHASE_ASSOCIATIONS_KEY] == expected_association and api.PENDING_ACTION_KEY not in restarted_state
        # Reserve reset/refund ownership against the same active session.
        reset_marker = api.prepare_reset(player_id, restarted_state)
        # Refund the real funded card and clear active state.
        refunds = api.settle_prepared_reset(player_id, restarted_state, reset_marker)
        # Require one refund and complete wallet restoration.
        assert len(refunds) == 1 and round(players.get_player(player_id)["balance"], 2) == round(balance_before, 2)
        # Require terminal cleanup without discarding the association.
        assert restarted_state["active_session"] is None and api.PENDING_ACTION_KEY not in restarted_state
        assert restarted_state[api.PURCHASE_ASSOCIATIONS_KEY] == expected_association
        # Query real hosted rows instead of inferring row count from balance.
        ledger_tail = storage.get_storage_provider().read_ledger_recent(player_id, 100)
        # Select the exact purchase debit and reset refund.
        purchase_rows = [row for row in ledger_tail if row.get("transaction_type") == "BINGO_CARD_PURCHASED" and row.get("round_id") == marker["purchase_id"]]
        reset_rows = [row for row in ledger_tail if row.get("transaction_type") == "BINGO_CARD_REFUND" and row.get("round_id") == session["session_id"]]
        # Require exactly one row of each type with established signs.
        assert len(purchase_rows) == 1 and len(reset_rows) == 1
        assert round(float(purchase_rows[0]["amount"]), 2) == -5.0 and round(float(reset_rows[0]["amount"]), 2) == 5.0
        # Serialize only the common public state projection.
        public_state = json.dumps(api._public_state(restarted_state), sort_keys=True)
        # Require recursive omission of the private key and raw purchase identity.
        assert api.PURCHASE_ASSOCIATIONS_KEY not in public_state and marker["purchase_id"] not in public_state

        # Create another isolated player for legacy BINGO-028 upgrade evidence.
        legacy_player = players.create_player("Bingo Legacy Association Live", "guest", 100.0)
        # Build one exact session without amount/time/order inference.
        legacy_state = engine.default_state()
        legacy_session = engine.start_session(legacy_state, legacy_player["player_id"], 5.0, "line", bot_players=[])
        # Bind the legacy marker directly to its stored session identity.
        legacy_marker = {"kind": "purchase", "status": "committed", "purchase_id": "bingo_legacy_purchase_204", "player_id": legacy_player["player_id"], "amount": 5.0, "pattern": "line", "session_id": legacy_session["session_id"]}
        # Preserve the exact pre-BINGO-029 state without an association key.
        legacy_state[api.PENDING_ACTION_KEY] = copy.deepcopy(legacy_marker)
        # Seed the disposable player document through the production transaction seam.
        state_store.update_player_game_state(api.GAME_ID, legacy_player["player_id"], lambda _current: copy.deepcopy(legacy_state), engine.default_state)
        # Reconstruct the provider before upgrade.
        storage.set_provider_for_tests(None)
        # Register and inject the legacy-restart provider.
        _install_mysql_provider(cleanup)
        # Load the exact legacy state through the restarted provider.
        legacy_loaded = state_store.load_player_game_state(api.GAME_ID, legacy_player["player_id"], engine.default_state)
        # Derive and persist only the committed marker/session pair before cleanup.
        legacy_finalized = api.finalize_purchase(legacy_player["player_id"], legacy_loaded, legacy_marker)
        # Require the selected session, one association, and marker removal.
        assert legacy_finalized["session_id"] == legacy_session["session_id"]
        assert legacy_loaded[api.PURCHASE_ASSOCIATIONS_KEY] == [{"purchase_id": legacy_marker["purchase_id"], "session_id": legacy_session["session_id"]}]
        assert api.PENDING_ACTION_KEY not in legacy_loaded

        # Create another player for legacy-finalize conflict rollback evidence.
        conflict_player = players.create_player("Bingo Conflict Association Live", "guest", 100.0)
        # Rebind the same session shape to a separate player document.
        conflict_state = copy.deepcopy(legacy_state)
        conflict_state["active_session"]["player_id"] = conflict_player["player_id"]
        conflict_state["active_session"]["cards"][0]["player_id"] = conflict_player["player_id"]
        conflict_marker = {**legacy_marker, "player_id": conflict_player["player_id"]}
        conflict_state[api.PENDING_ACTION_KEY] = copy.deepcopy(conflict_marker)
        # Seed a different owner for the exact referenced session.
        conflict_state[api.PURCHASE_ASSOCIATIONS_KEY] = [{"purchase_id": "different_purchase_204", "session_id": legacy_session["session_id"]}]
        # Publish the fixture in its own real document transaction.
        state_store.update_player_game_state(api.GAME_ID, conflict_player["player_id"], lambda _current: copy.deepcopy(conflict_state), engine.default_state)
        # Freeze durable state before the rejected transition.
        conflict_before = state_store.load_player_game_state(api.GAME_ID, conflict_player["player_id"], engine.default_state)
        # Require identity conflict without document publication.
        try:
            # Attempt finalization with the exact committed marker/session.
            api.finalize_purchase(conflict_player["player_id"], copy.deepcopy(conflict_before), conflict_marker)
        except ConflictError as exc:
            # Refuse any unrelated error category.
            assert "association identity changed" in str(exc)
        else:
            # Fail if conflicting ownership was accepted.
            raise AssertionError("Bingo association conflict was accepted")
        # Require byte-equivalent decoded state after rollback.
        conflict_after = state_store.load_player_game_state(api.GAME_ID, conflict_player["player_id"], engine.default_state)
        assert conflict_after == conflict_before

        # Create a final player for post-debit transaction-local conflict evidence.
        rollback_player = players.create_player("Bingo Commit Rollback Live", "guest", 100.0)
        # Load fresh state and reserve the exact prepared marker.
        rollback_state = state_store.load_player_game_state(api.GAME_ID, rollback_player["player_id"], engine.default_state)
        rollback_marker = api.prepare_purchase(rollback_player["player_id"], rollback_state, 5.0, "line")
        # Select the session identity that start_session will create inside the failing transaction.
        conflicting_session_id = "bingo_conflict_session_204"
        # Seed a prior different-purchase owner for that soon-created session.
        prior_association = {"purchase_id": "different_purchase_204", "session_id": conflicting_session_id}

        # Add only the intentional conflict while retaining the prepared marker.
        def seed_conflict(current):
            # Require the exact prepared owner and no active session.
            assert current[api.PENDING_ACTION_KEY]["purchase_id"] == rollback_marker["purchase_id"] and current["active_session"] is None
            # Publish the preexisting association.
            current[api.PURCHASE_ASSOCIATIONS_KEY] = [copy.deepcopy(prior_association)]
            # Return the complete fixture.
            return current

        # Commit the fixture through a real MySQL document transaction.
        state_store.update_player_game_state(api.GAME_ID, rollback_player["player_id"], seed_conflict, engine.default_state)
        # Freeze exact document and wallet state before settlement.
        rollback_before = state_store.load_player_game_state(api.GAME_ID, rollback_player["player_id"], engine.default_state)
        rollback_balance_before = players.get_player(rollback_player["player_id"])["balance"]
        # Preserve production seams while observing recovery ordering.
        original_load = api.load_player_game_state
        original_apply = api._apply_movement
        original_engine_id = api.engine.new_id
        # Capture the first provider-authoritative state after commit failure.
        observed_rollback = {}
        # Record real money movement order.
        movement_types = []

        # Observe recovery state without changing it.
        def observe_load(*args, **kwargs):
            # Read through the real provider.
            loaded = original_load(*args, **kwargs)
            # Retain only the first compensation decision state.
            observed_rollback.setdefault("state", copy.deepcopy(loaded))
            # Return the authoritative state unchanged.
            return loaded

        # Observe movement types while delegating real settlement.
        def observe_apply(movement):
            # Record the established meaning only.
            movement_types.append(movement["transaction_type"])
            # Execute through the real gateway.
            return original_apply(movement)

        # Force only the new session identity; preserve card entropy.
        def deterministic_engine_id(prefix):
            # Return the pre-conflicted identity for session creation.
            if prefix == "bingo":
                # Bind the conflict to the exact transaction-local session.
                return conflicting_session_id
            # Preserve production generation for every other identity.
            return original_engine_id(prefix)

        # Execute debit, transaction-local session mutation, conflict rollback, and compensation.
        with mock.patch.object(api, "load_player_game_state", side_effect=observe_load), mock.patch.object(api, "_apply_movement", side_effect=observe_apply), mock.patch.object(api.engine, "new_id", side_effect=deterministic_engine_id), mock.patch.object(api, "seat_competitors", return_value=[]):
            # Require the association conflict to remain caller-visible.
            try:
                # Exercise the complete production settlement workflow.
                api.settle_purchase(rollback_player["player_id"], rollback_state, rollback_marker)
            except ConflictError as exc:
                # Refuse unrelated provider or engine failures.
                assert "association identity changed" in str(exc)
            else:
                # Fail if the conflicting session was accepted.
                raise AssertionError("Bingo commit association conflict was accepted")
        # Prove start_session and pending-status mutations rolled back together.
        assert observed_rollback["state"] == rollback_before
        assert observed_rollback["state"]["active_session"] is None
        assert observed_rollback["state"][api.PENDING_ACTION_KEY] == rollback_before[api.PENDING_ACTION_KEY]
        assert observed_rollback["state"][api.PURCHASE_ASSOCIATIONS_KEY] == [prior_association]
        # Require exactly one debit followed by one matching compensation.
        assert movement_types == ["BINGO_CARD_PURCHASED", "BINGO_CARD_REFUND_AFTER_ERROR"]
        # Read final state after compensation and prepared-marker rollback.
        rollback_after = state_store.load_player_game_state(api.GAME_ID, rollback_player["player_id"], engine.default_state)
        # Require only marker removal and the ordinary update timestamp change.
        expected_after = copy.deepcopy(rollback_before)
        expected_after.pop(api.PENDING_ACTION_KEY, None)
        expected_after["updated_at"] = rollback_after["updated_at"]
        assert rollback_after == expected_after and rollback_after["active_session"] is None
        # Require full wallet restoration.
        assert round(players.get_player(rollback_player["player_id"])["balance"], 2) == round(rollback_balance_before, 2)
        # Query direct hosted ledger evidence for this purchase identity.
        rollback_ledger = storage.get_storage_provider().read_ledger_recent(rollback_player["player_id"], 100)
        # Select exact debit and error-refund rows.
        rollback_debits = [row for row in rollback_ledger if row.get("transaction_type") == "BINGO_CARD_PURCHASED" and row.get("round_id") == rollback_marker["purchase_id"]]
        rollback_refunds = [row for row in rollback_ledger if row.get("transaction_type") == "BINGO_CARD_REFUND_AFTER_ERROR" and row.get("round_id") == rollback_marker["purchase_id"]]
        # Require one row of each type and opposite signed amounts.
        assert len(rollback_debits) == 1 and len(rollback_refunds) == 1
        assert round(float(rollback_debits[0]["amount"]), 2) == -5.0 and round(float(rollback_refunds[0]["amount"]), 2) == 5.0
        # Replay both immutable movement identities after compensation converges.
        replayed_debit, debit_was_replayed = api._apply_movement(api._human_purchase_movement(rollback_marker))
        replayed_refund, refund_was_replayed = api._apply_movement(api._purchase_refund_movement(rollback_marker, {"player_id": rollback_player["player_id"], "amount": 5.0}))
        # Require original ledger identities and no wallet movement.
        assert debit_was_replayed and refund_was_replayed
        assert replayed_debit["ledger_id"] == rollback_debits[0]["ledger_id"] and replayed_refund["ledger_id"] == rollback_refunds[0]["ledger_id"]
        assert round(players.get_player(rollback_player["player_id"])["balance"], 2) == round(rollback_balance_before, 2)
        # Re-query to prove replay appended no rows.
        replay_ledger = storage.get_storage_provider().read_ledger_recent(rollback_player["player_id"], 100)
        assert len([row for row in replay_ledger if row.get("round_id") == rollback_marker["purchase_id"] and row.get("transaction_type") in {"BINGO_CARD_PURCHASED", "BINGO_CARD_REFUND_AFTER_ERROR"}]) == 2
        # Emit only bounded value-free evidence.
        print("BINGO-PURCHASE-SESSION-MYSQL-LIVE PASS transaction=1 replay=1 restart=1 reset=1 legacy=1 rollback=1 compensation=1 ledger=1 privacy=1")


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

    # Build one complete synthetic guard tuple without provisioning or contacting a service.
    @staticmethod
    def _live_environment() -> dict:
        # Return only test-owned values accepted by the parent `_204` identifier grammar.
        return {"CASINO_MYSQL_DISPOSABLE_TEST": "1", "CASINO_MYSQL_TEST_ADMIN_HOST": "127.0.0.1", "CASINO_MYSQL_MIGRATION_HOST": "127.0.0.1", "CASINO_MYSQL_HOST": "127.0.0.1", "CASINO_MYSQL_TEST_ADMIN_PORT": "3306", "CASINO_MYSQL_MIGRATION_PORT": "3306", "CASINO_MYSQL_PORT": "3306", "CASINO_MYSQL_DATABASE": "casino_base_204", "CASINO_MYSQL_MIGRATION_DATABASE": "casino_base_204", "CASINO_MYSQL_USER": "casino_runtime_204", "CASINO_MYSQL_MIGRATION_USER": "casino_migrator_204", "CASINO_MYSQL_PASSWORD": "synthetic-runtime", "CASINO_MYSQL_MIGRATION_PASSWORD": "synthetic-migrator", "CASINO_MYSQL_TEST_ADMIN_USER": "root", "CASINO_MYSQL_TEST_ADMIN_PASSWORD": "synthetic-admin", "CASINO_STORAGE_PROVIDER": "json"}

    # Prove every malformed target refuses before provider construction or injection. (TEST-265)
    def test_live_guard_refuses_incomplete_remote_and_colliding_targets(self):
        # Start every adversarial case from one complete synthetic tuple.
        valid = self._live_environment()
        # Collect disjoint invalid environments with value-free case labels.
        cases = []
        # Remove each required guard field independently.
        for name in valid:
            # Provider selector absence is supported and is not a malformed target.
            if name == "CASINO_STORAGE_PROVIDER":
                # Keep the selector-absence path for cleanup tests instead.
                continue
            # Remove exactly one required field from an otherwise complete tuple.
            missing = {key: value for key, value in valid.items() if key != name}
            # Preserve a fixed label that reveals no supplied value.
            cases.append((f"missing-{name}", missing))
        # Prove equality of three absent ports can never bypass the guard.
        cases.append(("all-ports-missing", {key: value for key, value in valid.items() if not key.endswith("_PORT")}))
        # Reject wrong markers, host aliases, malformed ports, and invalid/disjoint role identities.
        overrides = [("marker", {"CASINO_MYSQL_DISPOSABLE_TEST": "0"}), ("remote-host", {"CASINO_MYSQL_HOST": "192.0.2.1"}), ("host-alias", {"CASINO_MYSQL_TEST_ADMIN_HOST": "localhost"}), ("port-text", {"CASINO_MYSQL_PORT": "port"}), ("port-space", {"CASINO_MYSQL_PORT": " 3306"}), ("port-sign", {"CASINO_MYSQL_PORT": "+3306"}), ("port-nonascii", {"CASINO_MYSQL_PORT": "３３０６"}), ("port-zero", {"CASINO_MYSQL_PORT": "0"}), ("port-overflow", {"CASINO_MYSQL_PORT": "65536"}), ("port-split", {"CASINO_MYSQL_PORT": "3307"}), ("database-shape", {"CASINO_MYSQL_DATABASE": "casino-base_204"}), ("database-suffix", {"CASINO_MYSQL_DATABASE": "casino_base"}), ("database-split", {"CASINO_MYSQL_DATABASE": "casino_other_204"}), ("user-shape", {"CASINO_MYSQL_USER": "runtime-user_204"}), ("user-suffix", {"CASINO_MYSQL_MIGRATION_USER": "casino_migrator"}), ("user-collision", {"CASINO_MYSQL_USER": valid["CASINO_MYSQL_MIGRATION_USER"]}), ("password-collision", {"CASINO_MYSQL_PASSWORD": valid["CASINO_MYSQL_MIGRATION_PASSWORD"]})]
        # Materialize each override without mutating the valid fixture.
        cases.extend((name, {**valid, **override}) for name, override in overrides)
        # Exercise the complete callback entry, not only the helper, with provider construction mocked.
        for name, environment in cases:
            # Keep each guard failure independently attributable.
            with self.subTest(case=name), mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(storage, "MySQLStorageProvider") as constructor, mock.patch.object(storage, "set_provider_for_tests") as inject:
                # Require fail-closed refusal before a provider can exist.
                with self.assertRaises(AssertionError):
                    run_bingo_purchase_session_association_live()
                # Prove no connector-owning object or provider selection was attempted.
                constructor.assert_not_called()
                inject.assert_not_called()
                # Preserve the enclosing selector on guard refusal.
                self.assertEqual(environment.get("CASINO_STORAGE_PROVIDER"), os.environ.get("CASINO_STORAGE_PROVIDER"))
        # Accept a complete synthetic tuple without constructing a provider.
        with mock.patch.dict(os.environ, valid, clear=True), mock.patch.object(storage, "MySQLStorageProvider") as constructor:
            # Exercise only validation; no service is provisioned or contacted.
            _require_disposable_mysql_matrix()
            constructor.assert_not_called()

    # Prove constructor, injection, body, and cleanup failures cannot leak provider selection. (TEST-265)
    def test_live_callback_restores_selector_across_all_provider_failure_boundaries(self):
        # Exercise both an explicit outer JSON selector and exact prior absence.
        for previous_selector in (None, "json"):
            # Inject one failure at each cleanup-sensitive boundary.
            for failure in ("constructor", "injection", "body", "pool-cleanup", "provider-clear"):
                # Build a complete synthetic target without opening it.
                environment = self._live_environment()
                # Model exact selector absence when required by this case.
                if previous_selector is None:
                    # Remove only the synthetic outer selector.
                    environment.pop("CASINO_STORAGE_PROVIDER")
                # Use a provider-shaped mock whose first body operation always stops the live schedule.
                provider = mock.Mock()
                provider.bootstrap_players.side_effect = RuntimeError("synthetic body failure")
                # Record every injection and clear attempt independently of real caches.
                injections = []

                # Model the selected injection or cleanup failure without touching a real provider cache.
                def inject(value):
                    # Retain exact object/None order for cleanup assertions.
                    injections.append(value)
                    # Fail only the requested injection boundary.
                    if value is provider and failure == "injection":
                        # Surface a fixed synthetic failure.
                        raise RuntimeError("synthetic injection failure")
                    # Fail only the requested provider-clear boundary.
                    if value is None and failure == "provider-clear":
                        # Require selector restoration despite this cleanup error.
                        raise RuntimeError("synthetic provider clear failure")

                # Model a pool-close failure while retaining the clear/restoration assertions.
                if failure == "pool-cleanup":
                    # ExitStack must continue to later cleanup callbacks after this error.
                    provider.close_pool.side_effect = RuntimeError("synthetic pool cleanup failure")
                # Keep each failure/selector pair independently attributable.
                with self.subTest(failure=failure, previous=previous_selector), mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(storage, "MySQLStorageProvider", return_value=provider) as constructor, mock.patch.object(storage, "set_provider_for_tests", side_effect=inject):
                    # Fail construction only after selector restoration was registered.
                    if failure == "constructor":
                        # No provider object becomes callback-owned in this case.
                        constructor.side_effect = RuntimeError("synthetic constructor failure")
                    # Preserve a failure while still requiring all applicable cleanup guards.
                    with self.assertRaises(RuntimeError):
                        run_bingo_purchase_session_association_live()
                    # Restore the exact inherited value or absence despite any cleanup exception.
                    self.assertEqual(previous_selector, os.environ.get("CASINO_STORAGE_PROVIDER"))
                    # Constructor failure must still attempt cache clearing without closing an unconstructed pool.
                    if failure == "constructor":
                        # Require the registered clear callback even before injection exists.
                        self.assertEqual([None], injections)
                        provider.close_pool.assert_not_called()
                    else:
                        # Close every constructed provider and clear partial/complete injection.
                        self.assertEqual([provider, None], injections)
                        provider.close_pool.assert_called_once_with()

    # Refuse malformed/private-extra records after start_session mutates transaction-local JSON state. (TEST-265)
    def test_invalid_association_records_roll_back_complete_session_publication(self):
        # Bind one prepared purchase to each isolated provider document.
        marker = {"kind": "purchase", "status": "prepared", "purchase_id": "shape-purchase", "player_id": "human", "amount": 5.0, "pattern": "line"}
        # Build one valid pair for duplicate and extra-field corruption fixtures.
        pair = {"purchase_id": "older-purchase", "session_id": "older-session"}
        # Cover collection shape, missing fields, duplicate ownership, and forbidden payload growth.
        malformed = ("not-a-list", [{"purchase_id": "older-purchase"}], [copy.deepcopy(pair), copy.deepcopy(pair)], [{**pair, "extra": "must-not-persist"}])
        # Own every JSON byte inside a disposable directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Use the production JSON provider's atomic document replacement and rollback semantics.
            provider = storage.JsonStorageProvider(Path(temporary))
            # Preserve the real engine transition so each refusal happens after session mutation.
            real_start = engine.start_session
            # Exercise each malformed record shape independently.
            for index, records in enumerate(malformed):
                # Seed one complete prepared document with deliberate private corruption.
                before = {**engine.default_state(), api.PENDING_ACTION_KEY: copy.deepcopy(marker), api.PURCHASE_ASSOCIATIONS_KEY: copy.deepcopy(records)}
                key = f"games/bingo/invalid-association-{index}.json"
                provider.write_document(key, before)
                # Route the real Bingo callback through a production provider transaction.
                with self.subTest(case=index), mock.patch.object(api, "update_player_game_state", side_effect=lambda _game, _player, mutator, default, key=key: provider.update_document(key, mutator, default)), mock.patch.object(api.engine, "start_session", wraps=real_start) as start:
                    # Require strict association validation to abort the complete publication.
                    with self.assertRaisesRegex(ConflictError, "association state is invalid"):
                        api.commit_purchase("human", copy.deepcopy(before), marker, [])
                    # Prove transaction-local session creation actually occurred before rejection.
                    start.assert_called_once()
                # Require every original byte-shape field and prepared marker to remain durable.
                self.assertEqual(before, provider.read_document(key, engine.default_state))

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

    # Upgrade only an exact legacy committed marker/session pair across JSON restart. (TEST-265)
    def test_legacy_committed_marker_restart_derives_exact_association_before_cleanup(self):
        # Build one authoritative session retained by a legacy BINGO-028 document.
        session = self._session("legacy-session-1")
        # Bind the legacy transient marker to that exact session without a new association key.
        marker = {"kind": "purchase", "status": "committed", "purchase_id": "legacy-purchase-1", "player_id": "human", "amount": 5.0, "pattern": "line", "session_id": session["session_id"]}
        # Preserve the precise pre-BINGO-029 state shape selected for upgrade.
        legacy = {"active_session": copy.deepcopy(session), "last_sessions": [], api.PENDING_ACTION_KEY: copy.deepcopy(marker)}

        # Adapt one real provider document transaction to the Bingo state-store callback shape.
        def provider_update(provider, key):
            # Return one game/player-neutral update adapter over the exact test document.
            return lambda _game_id, _player_id, mutator, default_factory: provider.update_document(key, mutator, default_factory)

        # Own every restart and conflict byte inside one disposable filesystem directory.
        with tempfile.TemporaryDirectory() as temporary:
            # Seed the exact legacy state through the production JSON provider.
            initial_provider = storage.JsonStorageProvider(Path(temporary))
            initial_provider.write_document("games/bingo/legacy-association.json", legacy)
            # Reconstruct the provider to model an application upgrade/restart before recovery.
            restarted_provider = storage.JsonStorageProvider(Path(temporary))
            # Let finalization derive and persist only the exact marker/session association.
            with mock.patch.object(api, "update_player_game_state", side_effect=provider_update(restarted_provider, "games/bingo/legacy-association.json")):
                # Recover the committed legacy purchase and release its transient marker.
                finalized = api.finalize_purchase("human", copy.deepcopy(legacy), marker)
            # Restart again before observing the upgraded durable state.
            replay_provider = storage.JsonStorageProvider(Path(temporary))
            # Read the complete post-upgrade document from durable bytes.
            upgraded = replay_provider.read_document("games/bingo/legacy-association.json", engine.default_state)
            # Require exact session recovery without changing public game state.
            self.assertEqual(session, finalized)
            self.assertEqual(session, upgraded["active_session"])
            # Persist the one derived pair before removing the legacy owner.
            self.assertEqual([{"purchase_id": marker["purchase_id"], "session_id": session["session_id"]}], upgraded[api.PURCHASE_ASSOCIATIONS_KEY])
            self.assertNotIn(api.PENDING_ACTION_KEY, upgraded)
            # Replay finalization after a second restart without reordering or duplicating state.
            before_replay = copy.deepcopy(upgraded)
            with mock.patch.object(api, "update_player_game_state", side_effect=provider_update(replay_provider, "games/bingo/legacy-association.json")):
                # Use the original exact marker as a lost-finalize-response retry.
                replayed = api.finalize_purchase("human", upgraded, marker)
            # Return the same session and preserve byte-stable durable state.
            self.assertEqual(session, replayed)
            self.assertEqual(before_replay, upgraded)
            self.assertEqual(before_replay, replay_provider.read_document("games/bingo/legacy-association.json", engine.default_state))

            # Seed a separate legacy marker whose session is already owned by another purchase.
            conflict = {**copy.deepcopy(legacy), api.PURCHASE_ASSOCIATIONS_KEY: [{"purchase_id": "different-purchase", "session_id": session["session_id"]}]}
            replay_provider.write_document("games/bingo/legacy-conflict.json", conflict)
            # Attempt finalization through a fresh provider object so rollback must be durable.
            conflict_provider = storage.JsonStorageProvider(Path(temporary))
            with mock.patch.object(api, "update_player_game_state", side_effect=provider_update(conflict_provider, "games/bingo/legacy-conflict.json")):
                # Refuse rebinding and keep the exact recovery marker available.
                with self.assertRaisesRegex(ConflictError, "identity changed"):
                    api.finalize_purchase("human", copy.deepcopy(conflict), marker)
            # Preserve the complete conflicting legacy document after transaction failure.
            self.assertEqual(conflict, conflict_provider.read_document("games/bingo/legacy-conflict.json", engine.default_state))

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
