# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Named cross-provider settlement parity gate for final storage package assembly."""

# Import exact decimal arithmetic for provider-independent wallet observations.
from decimal import Decimal
# Import disposable directories so JSON evidence never touches user-owned data.
import tempfile
# Import standard unittest assertions for the named parity case.
import unittest

# Import player defaults so the JSON provider receives one valid reviewed wallet document.
from casino.core import players
# Import immutable action values shared by both concrete provider executions.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionResolution, GameActionResources
# Import the final public JSON provider through the historical compatibility path.
from casino.core.storage import JsonStorageProvider
# Import the public conflict boundary required for changed settlement reuse.
from casino.errors import ConflictError
# Reuse the connector-free transactional MySQL model that executes production provider SQL.
from tests.mysql_game_action_provider_tests import _Database, _Provider


# Build the exact wallet and state resources used by both providers.
def _resources() -> GameActionResources:
    # Return one canonical wallet plus one route-free game-state key.
    return GameActionResources(wallet_ids=("human",), state_keys=("slots:human",))


# Build one provider-neutral semantic settlement identity.
def _identity(*, stake_cents: int = 100) -> GameActionIdentity:
    # Bind the same caller key, request, and resource set for both providers.
    return GameActionIdentity.create(game_id="slots", player_id="human", action_key="provider-parity-settlement", resources=_resources(), request={"stake_cents": stake_cents})


# Return the deterministic paid settlement executed against each provider.
def _settlement_plan(_snapshot) -> GameActionPlan:
    # Debit the wager, credit the payout, and publish one terminal state in exact order.
    return GameActionPlan.create(outcome={"round_id": "provider-parity-round"}, movements=(GameActionMovement(wallet_id="human", amount_cents=-100, reason="wager"), GameActionMovement(wallet_id="human", amount_cents=250, reason="payout")), state_updates={"slots:human": {"spins": 1, "status": "settled"}})


# Execute the same settlement, replay, resolution, and conflict schedule on one provider.
def _exercise_settlement(provider, observe_committed_state) -> dict:
    # Recreate exact immutable inputs so providers cannot share mutable fixture state.
    resources = _resources()
    # Bind one exact caller-owned action identity.
    identity = _identity()
    # Count planner calls across commit, replay, resolution, and conflict.
    planner_calls = []

    # Record the immutable planner input before returning the shared plan.
    def planner(snapshot):
        # Retain the exact snapshot for the once-only assertion.
        planner_calls.append(snapshot)
        # Return the provider-neutral settlement plan.
        return _settlement_plan(snapshot)

    # Execute the new settlement through the provider-owned atomic boundary.
    receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
    # Require one new commit and exactly one planner invocation.
    assert replayed is False and len(planner_calls) == 1
    # Replay through the same public boundary with an unreachable planner.
    replay_receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("replay invoked planner")))
    # Require immutable replay without another wallet, state, or ledger projection.
    assert replayed is True and replay_receipt == receipt and len(planner_calls) == 1
    # Resolve the committed settlement without replaying its mutation.
    assert provider.resolve_game_action(identity=identity, resources=resources) == GameActionResolution(status="committed", receipt=receipt)
    # Snapshot committed provider state before hostile same-key reuse.
    committed_state = observe_committed_state()
    # Change only request semantics under the already committed action scope.
    changed_identity = _identity(stake_cents=200)
    # Reject changed reuse before planner or any provider mutation.
    try:
        # Attempt the conflicting execution with an unreachable planner.
        provider.execute_game_action_once(identity=changed_identity, resources=resources, planner=lambda _snapshot: (_ for _ in ()).throw(AssertionError("conflict invoked planner")))
    # Accept only the stable provider-neutral conflict boundary.
    except ConflictError:
        # Continue after the required fail-closed result.
        pass
    # Fail when a provider accepts changed settlement semantics.
    else:
        # Surface one fixed parity failure.
        raise AssertionError("changed settlement reuse was accepted")
    # Require conflict to preserve exact committed state.
    assert observe_committed_state() == committed_state
    # Return only provider-neutral result and committed projections.
    return {"receipt": receipt, "planner_calls": len(planner_calls), "state": committed_state}


# Prove one paid settlement has identical durable semantics on JSON and MySQL providers.
class StorageProviderSettlementParityTests(unittest.TestCase):
    """Execute one shared settlement schedule against both concrete provider boundaries."""

    # Require paid settlement, replay, resolution, and conflict parity without a live connector.
    def test_paid_settlement_semantics_match_json_and_mysql(self):
        # Allocate one disposable filesystem root for the production JSON provider.
        with tempfile.TemporaryDirectory(prefix="storage-provider-parity-") as temporary_root:
            # Construct the production JSON provider over the isolated root.
            json_provider = JsonStorageProvider(temporary_root)
            # Build one valid default wallet document.
            json_state = players.default_players()
            # Select the exact wallet shared with the MySQL model.
            human = next(player for player in json_state["players"] if player["player_id"] == "human")
            # Match the MySQL fixture's exact ten-token starting balance.
            human["balance"] = 10.0
            # Seed the isolated provider before the shared settlement schedule.
            json_provider.bootstrap_players(json_state)

            # Return the JSON provider's exact committed wallet, ledger, and private state projection.
            def observe_json() -> dict:
                # Read the current wallet document through the production provider.
                current = json_provider.load_players(players.default_players)
                # Select the exact action-owned wallet row.
                current_human = next(player for player in current["players"] if player["player_id"] == "human")
                # Read the action-owned private state registry after recovery convergence.
                action_states = json_provider._read_game_action_states()["states"]
                # Return canonical cents, movement count, and terminal state only.
                return {"balance_cents": int(Decimal(str(current_human["balance"])) * 100), "ledger_count": len(json_provider.read_ledger_recent("human", 10)), "state": action_states["slots:human"]}

            # Execute the complete shared schedule against JSON.
            json_result = _exercise_settlement(json_provider, observe_json)
            # Construct the connector-free relational image used by production MySQL SQL.
            mysql_database = _Database()
            # Construct the production MySQL provider test seam over that image.
            mysql_provider = _Provider(mysql_database)

            # Return the MySQL model's exact committed wallet, ledger, and document projection.
            def observe_mysql() -> dict:
                # Decode the canonical route-free state document after transaction commit.
                state_value = mysql_provider._decode_mysql_game_action_json(mysql_database.documents["slots:human"])
                # Return canonical cents, movement count, and terminal state only.
                return {"balance_cents": int(mysql_database.players["human"]["balance"] * 100), "ledger_count": len(mysql_database.ledger), "state": state_value}

            # Execute the identical schedule against production MySQL SQL.
            mysql_result = _exercise_settlement(mysql_provider, observe_mysql)
            # Require byte-independent providers to publish the same immutable receipt.
            self.assertEqual(json_result["receipt"], mysql_result["receipt"])
            # Require identical committed wallet, ledger, and state projections.
            self.assertEqual(json_result["state"], mysql_result["state"])
            # Bind the exact expected settlement delta and movement count.
            self.assertEqual({"balance_cents": 1150, "ledger_count": 2, "state": {"spins": 1, "status": "settled"}}, json_result["state"])
            # Require one planner call on each provider and zero calls on replay/conflict.
            self.assertEqual((1, 1), (json_result["planner_calls"], mysql_result["planner_calls"]))


# Execute the focused module directly for local diagnosis.
if __name__ == "__main__":
    # Run with concise standard unittest reporting.
    unittest.main()
