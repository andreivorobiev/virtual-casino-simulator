# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free conformance and hostile tests for issue #430 Phase0c slice 2."""

# Import immutable-data assignment errors for receipt and snapshot proof.
from dataclasses import FrozenInstanceError
# Import deep copying for the fake provider's side-effect detector.
from copy import deepcopy
# Import a bounded thread pool for compatible concurrent replay proof.
from concurrent.futures import ThreadPoolExecutor
# Import abstract-class inspection for the provider boundary proof.
import inspect
# Import repository paths for the inert route/game activation gate.
from pathlib import Path
# Import unittest for the standalone focused suite.
import unittest

# Import the complete provider-neutral source checkpoint under test.
from casino.core.game_action import (
    # Import the canonical composite wrappers for immutable-state assertions.
    FrozenArray,
    FrozenObject,
    # Import the abstract provider boundary.
    GameActionExecutor,
    # Import immutable action identity values.
    GameActionIdentity,
    # Import signed integer-cent movement values.
    GameActionMovement,
    # Import immutable planner result values.
    GameActionPlan,
    # Import immutable committed receipt values.
    GameActionReceipt,
    # Import provider-neutral lifecycle resolution values.
    GameActionResolution,
    # Import explicit bounded resource declarations.
    GameActionResources,
    # Import immutable provider snapshot values.
    GameActionSnapshot,
    # Import reviewed public bounds for hostile cases.
    MAX_CANONICAL_DEPTH,
    MAX_CANONICAL_INTEGER,
    MAX_CANONICAL_ITEMS,
    MAX_CANONICAL_TEXT,
    MAX_MOVEMENTS,
    MAX_STATE_RESOURCES,
    MAX_WALLET_RESOURCES,
    # Import the pure deterministic plan projection.
    apply_plan_to_snapshot,
    # Import the canonical semantic request digest.
    canonical_fingerprint,
    # Import the shared provider entry validation.
    validate_execution_request,
    # Import resolver entry validation.
    validate_resolution_request,
    # Import the plan/resource validation boundary.
    validate_plan,
)
# Import stable public failures for conflict and malformed-contract proof.
from casino.errors import ConflictError, ValidationError


# Implement an in-memory conformance fake without claiming production persistence.
class _FakeGameActionProvider(GameActionExecutor):
    # Initialize exact provider-owned wallet, state, and receipt projections.
    def __init__(self, *, wallets=None, states=None) -> None:
        # Store ordinary mutable wallet projection only inside the fake provider.
        self.wallets = dict(wallets or {})
        # Store an isolated game-state projection only inside the fake provider.
        self.states = deepcopy(states or {})
        # Store immutable committed receipts by their durable scope keys.
        self.receipts = {}
        # Store immutable winning lifecycle dispositions by durable scope keys.
        self.claims = {}
        # Count provider snapshot reads for mismatch-before-planner assertions.
        self.snapshot_reads = 0
        # Import a same-process lock only for deterministic conformance tests.
        import threading
        # Serialize the fake's lookup/planner/commit sequence.
        self._lock = threading.RLock()

    # Restore fake-owned projections after a hostile planner side effect.
    def _restore(self, *, wallets, states, receipts, claims) -> None:
        # Restore the exact wallet projection.
        self.wallets = wallets
        # Restore the exact game-state projection.
        self.states = states
        # Restore the exact immutable receipt registry.
        self.receipts = receipts
        # Restore the exact immutable lifecycle claim registry.
        self.claims = claims

    # Execute the abstract semantics in memory for contract conformance only.
    def execute_game_action_once(self, *, identity, resources, planner):
        # Validate exact public entry types before any fake provider lookup.
        validate_execution_request(identity=identity, resources=resources, planner=planner)
        # Serialize fake lookup and commit behavior for concurrent replay proof.
        with self._lock:
            # Inspect durable reuse before reading any provider resource.
            existing = self.receipts.get(identity.scope_key)
            # Resolve compatible or conflicting reuse without invoking the planner.
            if existing is not None:
                # Reject any semantic fingerprint or declared-resource mismatch.
                if existing.identity != identity or existing.resources != resources:
                    # Preserve the contract's mismatch-before-planner rule.
                    raise ConflictError("Game action key conflicts with committed semantics")
                # Return the exact immutable committed receipt as a replay.
                return existing, True
            # Inspect a resolver-owned tombstone before reading any provider resource.
            claim = self.claims.get(identity.scope_key)
            # Reject changed semantics or late execution behind an immutable tombstone.
            if claim is not None:
                # Reject fingerprint or resource mismatch without planner/RNG.
                if claim[0] != identity or claim[1] != resources:
                    # Preserve the immutable winning claim.
                    raise ConflictError("Game action key conflicts with durable semantics")
                # Refuse every late action behind a resolver winner.
                raise ConflictError("Game action was durably resolved as uncommitted")
            # Record the first provider resource read only after durable-key lookup.
            self.snapshot_reads += 1
            # Capture exact declared wallet balances.
            wallets = {wallet_id: self.wallets[wallet_id] for wallet_id in resources.wallet_ids}
            # Capture exact declared state values.
            states = {state_key: self.states[state_key] for state_key in resources.state_keys}
            # Freeze the complete provider snapshot before planner execution.
            snapshot_before = GameActionSnapshot.create(resources=resources, wallet_balances=wallets, state_values=states)
            # Preserve all fake provider state to detect and reverse planner side effects.
            saved_wallets = deepcopy(self.wallets)
            # Preserve all fake game state before planner execution.
            saved_states = deepcopy(self.states)
            # Preserve the immutable receipt registry before planner execution.
            saved_receipts = dict(self.receipts)
            # Preserve lifecycle claims before invoking the planner.
            saved_claims = dict(self.claims)
            try:
                # Invoke the new-action planner exactly once.
                plan = planner(snapshot_before)
            except BaseException:
                # Restore fake state if a hostile planner mutated its closure before raising.
                self._restore(wallets=saved_wallets, states=saved_states, receipts=saved_receipts, claims=saved_claims)
                # Preserve the planner's exact focused-test exception.
                raise
            # Detect any fake provider mutation performed through a planner closure.
            if self.wallets != saved_wallets or self.states != saved_states or self.receipts != saved_receipts or self.claims != saved_claims:
                # Restore every fake-owned projection before failing closed.
                self._restore(wallets=saved_wallets, states=saved_states, receipts=saved_receipts, claims=saved_claims)
                # Reject the impure planner before a receipt commit.
                raise ValidationError("Game action planner must be side-effect free")
            # Require the exact immutable plan type.
            if type(plan) is not GameActionPlan:
                # Reject arbitrary plan-like values.
                raise ValidationError("Game action planner returned an invalid plan")
            # Project the plan through the shared pure contract validator.
            snapshot_after = apply_plan_to_snapshot(snapshot_before, plan)
            # Publish each resulting wallet balance to the fake provider.
            for wallet_id, balance_cents in snapshot_after.wallet_balances:
                # Replace only a declared wallet resource.
                self.wallets[wallet_id] = balance_cents
            # Publish each resulting game-state value to the fake provider.
            for state_key, state_value in snapshot_after.state_values:
                # Replace only a declared state resource.
                self.states[state_key] = state_value
            # Construct the immutable committed receipt.
            receipt = GameActionReceipt(
                # Preserve the exact action identity.
                identity=identity,
                # Preserve the exact bounded resource set.
                resources=resources,
                # Preserve the immutable planner input.
                snapshot_before=snapshot_before,
                # Preserve the immutable game result and requested writes.
                plan=plan,
                # Preserve the exact committed projection.
                snapshot_after=snapshot_after,
            )
            # Retain the exact receipt under the durable scope key.
            self.receipts[identity.scope_key] = receipt
            # Publish the immutable execute disposition with its compatible semantics.
            self.claims[identity.scope_key] = (identity, resources, "execute")
            # Return the new committed receipt with replay false.
            return receipt, False

    # Resolve committed, pending, or resolver-first action state without planning.
    def resolve_game_action(self, *, identity, resources):
        # Validate exact provider-neutral resolver inputs.
        validate_resolution_request(identity=identity, resources=resources)
        # Serialize fake lifecycle resolution for deterministic conformance proof.
        with self._lock:
            # Return an immutable committed receipt when execution won first.
            existing = self.receipts.get(identity.scope_key)
            # Resolve a compatible prior receipt without invoking planner behavior.
            if existing is not None:
                # Reject changed identity or resources.
                if existing.identity != identity or existing.resources != resources:
                    # Preserve the committed result.
                    raise ConflictError("Game action key conflicts with committed semantics")
                # Return the complete committed resolution.
                return GameActionResolution(status="committed", receipt=existing)
            # Inspect an earlier resolver-owned tombstone.
            claim = self.claims.get(identity.scope_key)
            # Validate or create the immutable terminal no-result claim.
            if claim is not None:
                # Reject changed identity or resources.
                if claim[0] != identity or claim[1] != resources:
                    # Preserve the existing claim unchanged.
                    raise ConflictError("Game action key conflicts with durable semantics")
            # Append the exact resolver-owned tombstone when this scope is unused.
            else:
                # Preserve identity, resources, and finite disposition.
                self.claims[identity.scope_key] = (identity, resources, "uncommitted")
            # Return the terminal provider-neutral no-result state.
            return GameActionResolution(status="uncommitted")


# Build the shared player-state resource set used by conformance tests.
def _resources(*, wallet_ids=("player-a",), state_keys=("example-state:player-a",)) -> GameActionResources:
    # Return one canonical explicit resource declaration.
    return GameActionResources(wallet_ids=wallet_ids, state_keys=state_keys)


# Build one action identity whose fingerprint binds request and resources.
def _identity(*, resources=None, request=None, action_key="action-1") -> GameActionIdentity:
    # Use the shared resource fixture unless a test supplies another set.
    selected_resources = resources or _resources()
    # Use one deterministic semantic request unless a test supplies another request.
    selected_request = request if request is not None else {"choice": "option-a", "stake_cents": 100}
    # Return the canonical resource-bound identity.
    return GameActionIdentity.create(
        # Scope the fixture to one game.
        game_id="example-game",
        # Scope the fixture to one player/controller.
        player_id="player-a",
        # Use the caller-stable action key selected by the test.
        action_key=action_key,
        # Bind the complete resource declaration.
        resources=selected_resources,
        # Bind the complete semantic request.
        request=selected_request,
    )


# Build one ordinary paid-action plan with signed integer-cent movement rows.
def _paid_plan(snapshot: GameActionSnapshot) -> GameActionPlan:
    # Read the immutable state only through the declared accessor.
    state = snapshot.state_value("example-state:player-a")
    # Require the expected canonical object fixture.
    if type(state) is not FrozenObject:
        # Fail the focused fixture if provider state is malformed.
        raise AssertionError("fixture state was not canonical")
    # Return a debit, payout, and state-update plan.
    return GameActionPlan.create(
        # Preserve only immutable outcome evidence.
        outcome={"round_id": "round-1", "result_codes": [1, 2, 3, 4, 5], "payout_cents": 250},
        # Request one wager debit and one payout credit.
        movements=[
            # Debit the exact wager in signed integer cents.
            GameActionMovement(wallet_id="player-a", amount_cents=-100, reason="wager"),
            # Credit the exact payout in signed integer cents.
            GameActionMovement(wallet_id="player-a", amount_cents=250, reason="payout"),
        ],
        # Replace only the declared immutable game state.
        state_updates={"example-state:player-a": {"bonus_actions": 0, "actions": 1}},
    )


# Prove canonical identity, immutable values, and provider conformance semantics.
class GameActionContractTests(unittest.TestCase):
    # Prove request fingerprints are deterministic and bind declared resources.
    def test_canonical_fingerprint_is_order_independent_and_resource_bound(self):
        # Hash equivalent objects with different insertion order.
        first = canonical_fingerprint({"b": [2, 3], "a": {"x": True}})
        # Hash the same semantics in canonical key order.
        second = canonical_fingerprint({"a": {"x": True}, "b": [2, 3]})
        # Require one unique semantic digest.
        self.assertEqual(first, second)
        # Build two different bounded resource declarations.
        original_resources = _resources()
        # Add a second state resource to the changed declaration.
        changed_resources = _resources(state_keys=("example-state:player-a", "example-state:shared"))
        # Build one identity with the original resource set.
        original = _identity(resources=original_resources)
        # Build one identity with the changed resource set and identical request.
        changed = _identity(resources=changed_resources)
        # Require resource drift to change the semantic fingerprint.
        self.assertNotEqual(original.request_fingerprint, changed.request_fingerprint)
        # Preserve the same durable scope key for conflict-before-planner lookup.
        self.assertEqual(original.scope_key, changed.scope_key)

    # Prove the canonical domain rejects coercions, recursion, and unbounded shapes.
    def test_canonical_fingerprint_rejects_float_nonstring_keys_recursion_and_bounds(self):
        # Build a recursive Python list.
        recursive = []
        # Point the list at itself.
        recursive.append(recursive)
        # Enumerate hostile noncanonical payloads.
        invalid_values = (
            # Reject binary floating-point request semantics.
            {"amount": 1.0},
            # Reject object keys that JSON would stringify.
            {1: "value"},
            # Reject recursive Python containers.
            recursive,
            # Reject a canonical tree wider than the item budget.
            list(range(MAX_CANONICAL_ITEMS + 1)),
        )
        # Exercise each malformed request independently.
        for value in invalid_values:
            # Identify only the focused case index.
            with self.subTest(kind=type(value).__name__):
                # Require one public validation failure.
                with self.assertRaises(ValidationError):
                    # Attempt to fingerprint the hostile request.
                    canonical_fingerprint(value)
        # Build nesting deeper than the reviewed canonical depth.
        deeply_nested = None
        # Add one list wrapper per level.
        for _index in range(MAX_CANONICAL_DEPTH + 2):
            # Wrap the prior value in another array.
            deeply_nested = [deeply_nested]
        # Reject excessive nesting before hashing.
        with self.assertRaises(ValidationError):
            # Attempt to fingerprint the excessive depth.
            canonical_fingerprint(deeply_nested)
        # Reject a direct immutable wrapper containing an out-of-range integer.
        with self.assertRaisesRegex(ValidationError, "^Canonical integer is out of range$"):
            # Attempt to bypass the canonical freezer through direct construction.
            FrozenArray((10**30,))

    # Prove bounded resources require exact sorted unique immutable identities.
    def test_resources_reject_empty_duplicate_unsorted_mutable_and_oversized_sets(self):
        # Enumerate malformed wallet/state resource declarations.
        invalid_factories = (
            # Reject an action with no declared resource.
            lambda: GameActionResources(),
            # Reject mutable wallet resource collections.
            lambda: GameActionResources(wallet_ids=["player-a"]),
            # Reject duplicate wallet identities.
            lambda: GameActionResources(wallet_ids=("player-a", "player-a")),
            # Reject noncanonical ordering.
            lambda: GameActionResources(wallet_ids=("player-b", "player-a")),
            # Reject a wallet resource set above its explicit bound.
            lambda: GameActionResources(wallet_ids=tuple(f"player-{index:02d}" for index in range(MAX_WALLET_RESOURCES + 1))),
            # Reject a state resource set above its explicit bound.
            lambda: GameActionResources(state_keys=tuple(f"state-{index:02d}" for index in range(MAX_STATE_RESOURCES + 1))),
        )
        # Exercise each malformed declaration independently.
        for factory in invalid_factories:
            # Keep the failure case isolated.
            with self.subTest(factory=factory):
                # Require one public validation failure.
                with self.assertRaises(ValidationError):
                    # Construct the hostile declaration.
                    factory()

    # Prove provider snapshots expose immutable exact declared resources only.
    def test_snapshot_is_immutable_and_rejects_undeclared_or_inexact_resources(self):
        # Build one shared resource declaration.
        resources = _resources()
        # Build one immutable provider snapshot.
        snapshot = GameActionSnapshot.create(
            # Bind the expected resources.
            resources=resources,
            # Provide exact integer-cent wallet state.
            wallet_balances={"player-a": 1_000},
            # Provide one ordinary mutable source object.
            state_values={"example-state:player-a": {"actions": 0}},
        )
        # Require the source mapping to become an immutable canonical object.
        self.assertIsInstance(snapshot.state_value("example-state:player-a"), FrozenObject)
        # Reject assignment to a frozen snapshot field.
        with self.assertRaises(FrozenInstanceError):
            # Attempt to replace the immutable wallet tuple.
            snapshot.wallet_balances = ()
        # Reject undeclared wallet reads.
        with self.assertRaisesRegex(ValidationError, "^Wallet resource was not declared$"):
            # Attempt to inspect an undeclared wallet.
            snapshot.wallet_balance("player-b")
        # Reject missing state coverage during snapshot construction.
        with self.assertRaisesRegex(ValidationError, "^Game action state snapshot does not match resources$"):
            # Omit the exact declared state key.
            GameActionSnapshot.create(resources=resources, wallet_balances={"player-a": 1_000}, state_values={})

    # Prove direct durable snapshot reconstruction enforces canonical scalar bounds.
    def test_direct_snapshot_reconstruction_rejects_oversized_scalar_state(self):
        # Declare the exact state-only resource used by each hostile snapshot.
        resources = _resources(wallet_ids=())
        # Enumerate canonical scalar values immediately beyond their public bounds.
        oversized_values = (
            # Exceed the maximum canonical text length by one code point.
            "x" * (MAX_CANONICAL_TEXT + 1),
            # Exceed the maximum canonical integer magnitude by one.
            MAX_CANONICAL_INTEGER + 1,
        )
        # Exercise each hostile direct state value independently.
        for value in oversized_values:
            # Identify only the scalar type in focused diagnostics.
            with self.subTest(value_type=type(value).__name__):
                # Require direct reconstruction to enforce the canonical tree boundary.
                with self.assertRaises(ValidationError):
                    # Construct the snapshot directly instead of using its safe factory.
                    GameActionSnapshot(
                        # Bind the exact declared resources.
                        resources=resources,
                        # Provide the complete empty wallet projection.
                        wallet_balances=(),
                        # Supply the hostile scalar as a directly reconstructed state value.
                        state_values=(("example-state:player-a", value),),
                    )

    # Prove a paid action commits once and compatible replay returns the exact receipt.
    def test_paid_action_commits_signed_cents_once_and_replays_exact_receipt(self):
        # Build one isolated conformance fake.
        provider = _FakeGameActionProvider(wallets={"player-a": 1_000}, states={"example-state:player-a": {"actions": 0}})
        # Build the complete resource declaration.
        resources = _resources()
        # Build the stable semantic action identity.
        identity = _identity(resources=resources)
        # Count planner/RNG-equivalent executions.
        planner_calls = []

        # Wrap the ordinary paid planner with one observable call count.
        def planner(snapshot):
            # Record one planner/RNG-equivalent invocation.
            planner_calls.append(snapshot)
            # Return the ordinary paid plan.
            return _paid_plan(snapshot)

        # Commit the new action.
        receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
        # Mark the first result as newly committed.
        self.assertFalse(replayed)
        # Apply one net positive 150-cent movement.
        self.assertEqual(provider.wallets["player-a"], 1_150)
        # Preserve both signed rows inside the immutable receipt.
        self.assertEqual(tuple(movement.amount_cents for movement in receipt.plan.movements), (-100, 250))
        # Commit the exact resulting state.
        self.assertEqual(receipt.snapshot_after.state_value("example-state:player-a"), FrozenObject((("actions", 1), ("bonus_actions", 0))))
        # Replay the same semantic action with a planner that must never run.
        replay_receipt, replayed = provider.execute_game_action_once(
            # Reuse the exact durable identity.
            identity=identity,
            # Reuse the exact resource set.
            resources=resources,
            # Fail the test if replay invokes a planner.
            planner=lambda _snapshot: self.fail("compatible replay invoked the planner"),
        )
        # Mark the second result as a replay.
        self.assertTrue(replayed)
        # Return the exact original immutable receipt object.
        self.assertIs(replay_receipt, receipt)
        # Keep the wallet projection unchanged on replay.
        self.assertEqual(provider.wallets["player-a"], 1_150)
        # Invoke planner/RNG semantics exactly once.
        self.assertEqual(len(planner_calls), 1)

    # Prove zero-cost actions receive the same durable immutable replay semantics.
    def test_zero_cost_action_commits_and_replays_without_wallet_rows(self):
        # Build one state-only fake provider.
        provider = _FakeGameActionProvider(states={"example-state:player-a": {"bonus_actions": 1}})
        # Declare only the state resource used by the free action.
        resources = _resources(wallet_ids=())
        # Bind a zero-cost bonus request into the stable action identity.
        identity = _identity(resources=resources, request={"bonus_action": True})
        # Count planner executions.
        calls = []

        # Build one zero-cost state-only planner.
        def planner(_snapshot):
            # Record the single new-action planner invocation.
            calls.append("planned")
            # Return no wallet movement and one state replacement.
            return GameActionPlan.create(
                # Preserve the complete zero-cost outcome.
                outcome={"cost_cents": 0, "payout_cents": 0, "round_id": "free-1"},
                # Express zero cost as no ledger movement.
                movements=(),
                # Consume the declared bonus-action state.
                state_updates={"example-state:player-a": {"bonus_actions": 0}},
            )

        # Commit the zero-cost action.
        receipt, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
        # Mark the first result as newly committed.
        self.assertFalse(replayed)
        # Preserve an empty movement tuple.
        self.assertEqual(receipt.plan.movements, ())
        # Replay the exact zero-cost action.
        repeated, replayed = provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
        # Return the original immutable receipt.
        self.assertIs(repeated, receipt)
        # Mark the second result as replayed.
        self.assertTrue(replayed)
        # Invoke the zero-cost planner only once.
        self.assertEqual(calls, ["planned"])

    # Prove semantic and resource mismatch rejects before snapshot or planner/RNG access.
    def test_same_key_mismatch_rejects_before_snapshot_and_planner(self):
        # Build one isolated conformance fake.
        provider = _FakeGameActionProvider(wallets={"player-a": 1_000}, states={"example-state:player-a": {"actions": 0}, "example-state:shared": {}})
        # Build the initially committed resource set.
        resources = _resources()
        # Build the initially committed identity.
        identity = _identity(resources=resources)
        # Commit the initial action.
        provider.execute_game_action_once(identity=identity, resources=resources, planner=_paid_plan)
        # Capture resource-read count after the original commit.
        original_snapshot_reads = provider.snapshot_reads
        # Track any conflict-path planner/RNG invocation.
        conflict_planner_calls = []

        # Define a planner that must remain unreachable.
        def forbidden_planner(_snapshot):
            # Record a contract violation if invoked.
            conflict_planner_calls.append("called")
            # Return a syntactically valid plan only to isolate lookup ordering.
            return GameActionPlan.create(outcome={"unexpected": True})

        # Build a changed semantic request under the same scoped action key.
        changed_identity = _identity(resources=resources, request={"choice": "option-b", "stake_cents": 100})
        # Reject the changed fingerprint before snapshot access.
        with self.assertRaisesRegex(ConflictError, "^Game action key conflicts with committed semantics$"):
            # Attempt conflicting reuse.
            provider.execute_game_action_once(identity=changed_identity, resources=resources, planner=forbidden_planner)
        # Build a changed resource set under the exact original fingerprint.
        changed_resources = _resources(state_keys=("example-state:player-a", "example-state:shared"))
        # Reject changed resources even when a caller presents the old fingerprint.
        with self.assertRaisesRegex(ConflictError, "^Game action key conflicts with committed semantics$"):
            # Attempt conflicting resource reuse.
            provider.execute_game_action_once(identity=identity, resources=changed_resources, planner=forbidden_planner)
        # Prove neither conflict opened a provider snapshot.
        self.assertEqual(provider.snapshot_reads, original_snapshot_reads)
        # Prove neither conflict invoked planner/RNG semantics.
        self.assertEqual(conflict_planner_calls, [])

    # Prove planners cannot mutate snapshots or fake provider state through closures.
    def test_side_effect_free_planner_contract_rejects_snapshot_and_provider_mutation(self):
        # Build one isolated conformance fake.
        provider = _FakeGameActionProvider(wallets={"player-a": 1_000}, states={"example-state:player-a": {"actions": 0}})
        # Build the complete resource declaration.
        resources = _resources()
        # Build one stable identity for the snapshot-mutation case.
        identity = _identity(resources=resources, action_key="snapshot-mutation")

        # Define a planner that attempts to replace frozen snapshot state.
        def mutate_snapshot(snapshot):
            # Trigger frozen-data rejection before returning any plan.
            snapshot.state_values = ()

        # Require the frozen snapshot assignment failure.
        with self.assertRaises(FrozenInstanceError):
            # Execute the hostile snapshot-mutating planner.
            provider.execute_game_action_once(identity=identity, resources=resources, planner=mutate_snapshot)
        # Preserve provider wallet state after the failed planner.
        self.assertEqual(provider.wallets, {"player-a": 1_000})
        # Preserve provider game state after the failed planner.
        self.assertEqual(provider.states, {"example-state:player-a": {"actions": 0}})
        # Leave no receipt after the failed planner.
        self.assertEqual(provider.receipts, {})

        # Define a planner that mutates fake provider state through its closure.
        def mutate_provider(_snapshot):
            # Illegally mutate provider-owned wallet state.
            provider.wallets["player-a"] = 7
            # Return an otherwise valid zero-write plan.
            return GameActionPlan.create(outcome={"unexpected": True})

        # Build a distinct stable identity for closure-side-effect proof.
        closure_identity = _identity(resources=resources, action_key="closure-mutation")
        # Require the fake conformance side-effect detector.
        with self.assertRaisesRegex(ValidationError, "^Game action planner must be side-effect free$"):
            # Execute the hostile provider-mutating planner.
            provider.execute_game_action_once(identity=closure_identity, resources=resources, planner=mutate_provider)
        # Restore exact provider wallet state after rejecting the planner.
        self.assertEqual(provider.wallets, {"player-a": 1_000})
        # Preserve exact provider state after rejecting the planner.
        self.assertEqual(provider.states, {"example-state:player-a": {"actions": 0}})
        # Leave no receipt after either failed planner.
        self.assertEqual(provider.receipts, {})

    # Prove undeclared writes, overdraws, and malformed cents fail before commit.
    def test_plan_validation_rejects_undeclared_resources_overdraw_and_noninteger_cents(self):
        # Build one exact resource snapshot.
        snapshot = GameActionSnapshot.create(
            # Declare one wallet and one state key.
            resources=_resources(),
            # Provide a 100-cent balance.
            wallet_balances={"player-a": 100},
            # Provide one empty state object.
            state_values={"example-state:player-a": {}},
        )
        # Build one movement against an undeclared wallet.
        undeclared_movement = GameActionPlan.create(
            # Preserve one simple outcome.
            outcome={},
            # Request an undeclared debit.
            movements=(GameActionMovement(wallet_id="player-b", amount_cents=-1, reason="wager"),),
        )
        # Reject the undeclared wallet before commit.
        with self.assertRaisesRegex(ValidationError, "^Game action movement resource was not declared$"):
            # Validate the hostile plan.
            validate_plan(snapshot, undeclared_movement)
        # Build one state write against an undeclared key.
        undeclared_state = GameActionPlan.create(outcome={}, state_updates={"example-state:other": {}})
        # Reject the undeclared state key before commit.
        with self.assertRaisesRegex(ValidationError, "^Game action state resource was not declared$"):
            # Validate the hostile plan.
            validate_plan(snapshot, undeclared_state)
        # Build one overdraw plan.
        overdraw = GameActionPlan.create(
            # Preserve one simple outcome.
            outcome={},
            # Debit more than the committed balance.
            movements=(GameActionMovement(wallet_id="player-a", amount_cents=-101, reason="wager"),),
        )
        # Reject the overdraw before commit.
        with self.assertRaisesRegex(ValidationError, "^Game action would overdraw a wallet$"):
            # Validate the hostile plan.
            validate_plan(snapshot, overdraw)
        # Enumerate malformed movement values.
        for value in (True, 1.0, "1", 0):
            # Keep each coercion case isolated.
            with self.subTest(value_type=type(value).__name__):
                # Require exact signed integer cents.
                with self.assertRaises(ValidationError):
                    # Attempt to build the malformed movement.
                    GameActionMovement(wallet_id="player-a", amount_cents=value, reason="wager")
        # Reject a movement list wider than the explicit plan bound.
        with self.assertRaisesRegex(ValidationError, "^Game action movements are invalid$"):
            # Construct an oversized movement tuple.
            GameActionPlan.create(
                # Preserve one simple outcome.
                outcome={},
                # Repeat valid movement objects above the bound.
                movements=tuple(GameActionMovement(wallet_id="player-a", amount_cents=1, reason="credit") for _index in range(MAX_MOVEMENTS + 1)),
            )

    # Prove direct durable plan reconstruction enforces canonical scalar bounds.
    def test_direct_plan_reconstruction_rejects_oversized_outcome_and_state_scalars(self):
        # Enumerate canonical scalar values immediately beyond their public bounds.
        oversized_values = (
            # Exceed the maximum canonical text length by one code point.
            "x" * (MAX_CANONICAL_TEXT + 1),
            # Exceed the maximum canonical integer magnitude by one.
            MAX_CANONICAL_INTEGER + 1,
        )
        # Exercise every hostile scalar through both direct plan surfaces.
        for value in oversized_values:
            # Identify only the scalar type in focused diagnostics.
            with self.subTest(surface="outcome", value_type=type(value).__name__):
                # Require direct outcome reconstruction to enforce canonical bounds.
                with self.assertRaises(ValidationError):
                    # Construct the plan directly with the hostile scalar outcome.
                    GameActionPlan(outcome=value)
            # Exercise the direct state-update surface independently.
            with self.subTest(surface="state_update", value_type=type(value).__name__):
                # Require direct state reconstruction to enforce canonical bounds.
                with self.assertRaises(ValidationError):
                    # Construct one otherwise valid plan with the hostile state scalar.
                    GameActionPlan(
                        # Use an exact valid immutable canonical outcome.
                        outcome=FrozenObject(()),
                        # Supply the hostile scalar in one direct state update.
                        state_updates=(("example-state:player-a", value),),
                    )

    # Prove immutable receipts reject inconsistent projections and assignment.
    def test_receipt_is_immutable_and_rejects_inconsistent_after_snapshot(self):
        # Build one exact resource declaration.
        resources = _resources()
        # Build one exact before snapshot.
        before = GameActionSnapshot.create(
            # Bind the declared resources.
            resources=resources,
            # Provide one wallet balance.
            wallet_balances={"player-a": 100},
            # Provide one state value.
            state_values={"example-state:player-a": {"actions": 0}},
        )
        # Build one valid debit plan.
        plan = GameActionPlan.create(
            # Preserve one simple outcome.
            outcome={"round_id": "round-1"},
            # Debit ten integer cents.
            movements=(GameActionMovement(wallet_id="player-a", amount_cents=-10, reason="wager"),),
        )
        # Build the exact deterministic after snapshot.
        after = apply_plan_to_snapshot(before, plan)
        # Construct one self-consistent immutable receipt.
        receipt = GameActionReceipt(
            # Bind the stable action identity.
            identity=_identity(resources=resources),
            # Bind the exact resources.
            resources=resources,
            # Preserve the planner input.
            snapshot_before=before,
            # Preserve the validated plan.
            plan=plan,
            # Preserve the deterministic committed result.
            snapshot_after=after,
        )
        # Reject receipt field assignment.
        with self.assertRaises(FrozenInstanceError):
            # Attempt to replace the committed plan.
            receipt.plan = GameActionPlan.create(outcome={})
        # Build an inconsistent after snapshot.
        inconsistent = GameActionSnapshot.create(
            # Bind the same declared resources.
            resources=resources,
            # Publish the wrong resulting wallet balance.
            wallet_balances={"player-a": 95},
            # Preserve the original state.
            state_values={"example-state:player-a": {"actions": 0}},
        )
        # Reject a receipt whose projection does not equal its plan.
        with self.assertRaisesRegex(ValidationError, "^Game action receipt result is inconsistent$"):
            # Attempt to construct the inconsistent receipt.
            GameActionReceipt(
                # Bind the stable action identity.
                identity=_identity(resources=resources),
                # Bind the exact resources.
                resources=resources,
                # Preserve the planner input.
                snapshot_before=before,
                # Preserve the validated plan.
                plan=plan,
                # Supply the inconsistent committed projection.
                snapshot_after=inconsistent,
            )

    # Prove two-thread compatible calls converge on one fake committed receipt.
    def test_concurrent_compatible_calls_plan_once_and_share_one_receipt(self):
        # Build one isolated conformance fake.
        provider = _FakeGameActionProvider(wallets={"player-a": 1_000}, states={"example-state:player-a": {"actions": 0}})
        # Build the complete resource declaration.
        resources = _resources()
        # Build the stable semantic action identity.
        identity = _identity(resources=resources)
        # Count planner/RNG-equivalent executions.
        planner_calls = []

        # Define one observable paid planner.
        def planner(snapshot):
            # Record the single admitted planner execution.
            planner_calls.append(snapshot)
            # Return the ordinary paid plan.
            return _paid_plan(snapshot)

        # Exercise only the accepted one-worker/two-thread posture.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit bounded compatible action calls.
            futures = [
                # Submit the same semantic action.
                executor.submit(provider.execute_game_action_once, identity=identity, resources=resources, planner=planner)
                # Repeat for each of the two same-process contenders.
                for _index in range(2)
            ]
            # Collect every completed receipt and replay marker.
            results = [future.result() for future in futures]
        # Invoke planner/RNG semantics exactly once.
        self.assertEqual(len(planner_calls), 1)
        # Mark exactly one result as a new commit.
        self.assertEqual(sum(not replayed for _receipt, replayed in results), 1)
        # Mark the other result as a compatible replay.
        self.assertEqual(sum(replayed for _receipt, replayed in results), 1)
        # Return one exact immutable receipt object to every contender.
        self.assertEqual(len({id(receipt) for receipt, _replayed in results}), 1)
        # Apply money movement exactly once.
        self.assertEqual(provider.wallets["player-a"], 1_150)

    # Prove provider-neutral resolution is finite, immutable, and planner-free.
    def test_resolution_contract_committed_uncommitted_and_conflict_semantics(self):
        # Build one isolated lifecycle conformance fake.
        provider = _FakeGameActionProvider(wallets={"player-a": 1_000}, states={"example-state:player-a": {"actions": 0}})
        # Build exact shared resources.
        resources = _resources()
        # Resolve one unused identity before any executor owns it.
        uncommitted_identity = _identity(resources=resources, action_key="resolver-first")
        # Commit the resolver-owned tombstone without planner behavior.
        uncommitted = provider.resolve_game_action(identity=uncommitted_identity, resources=resources)
        # Return the exact terminal no-result shape.
        self.assertEqual(uncommitted, GameActionResolution(status="uncommitted"))
        # Reject a late executor before snapshot or planner invocation.
        with self.assertRaisesRegex(ConflictError, "^Game action was durably resolved as uncommitted$"):
            # Attempt execution behind the immutable resolver claim.
            provider.execute_game_action_once(identity=uncommitted_identity, resources=resources, planner=lambda _snapshot: self.fail("late executor invoked planner"))
        # Build and execute one distinct action first.
        committed_identity = _identity(resources=resources, action_key="executor-first")
        # Commit one exact paid receipt.
        receipt, replayed = provider.execute_game_action_once(identity=committed_identity, resources=resources, planner=_paid_plan)
        # Require a new commit rather than replay.
        self.assertFalse(replayed)
        # Resolve the original immutable committed result without planner access.
        committed = provider.resolve_game_action(identity=committed_identity, resources=resources)
        # Bind status and receipt exactly.
        self.assertEqual(committed, GameActionResolution(status="committed", receipt=receipt))
        # Build changed semantics under the resolver-owned scope.
        changed = _identity(resources=resources, request={"choice": "changed"}, action_key="resolver-first")
        # Reject changed resolver reuse without rewriting the tombstone.
        with self.assertRaisesRegex(ConflictError, "^Game action key conflicts with durable semantics$"):
            # Attempt changed semantic resolution.
            provider.resolve_game_action(identity=changed, resources=resources)
        # Require committed status to carry one exact receipt.
        with self.assertRaisesRegex(ValidationError, "^Committed game action resolution requires a receipt$"):
            # Attempt a malformed committed lifecycle result.
            GameActionResolution(status="committed")
        # Require uncommitted status never to expose a stale receipt.
        with self.assertRaisesRegex(ValidationError, "^Non-committed game action resolution cannot contain a receipt$"):
            # Attempt to attach committed material to a no-result state.
            GameActionResolution(status="uncommitted", receipt=receipt)

    # Prove the production checkpoint remains abstract and provider/game/route inert.
    def test_boundary_is_abstract_and_source_has_no_provider_route_or_game_imports(self):
        # Require the executor to remain an abstract provider contract.
        self.assertTrue(inspect.isabstract(GameActionExecutor))
        # Reject direct construction without a provider implementation.
        with self.assertRaises(TypeError):
            # Attempt to instantiate the abstract boundary.
            GameActionExecutor()
        # Read this test's imported production module source.
        source = inspect.getsource(inspect.getmodule(GameActionExecutor))
        # Reject storage-provider implementation imports from the contract.
        self.assertNotIn("casino.core.storage", source)
        # Reject game imports from the provider-neutral contract.
        self.assertNotIn("casino.games", source)
        # Reject route imports from the provider-neutral contract.
        self.assertNotIn("casino.api", source)
        # Reject JSON provider implementation names.
        self.assertNotIn("JsonStorageProvider", source)
        # Reject MySQL provider implementation names.
        self.assertNotIn("MySQLStorageProvider", source)
        # Preserve the explicit route/game/API integration exclusion.
        self.assertIn("no route, game, or public API integration", source)

    # Prove the Phase A lifecycle bridge remains absent from every route and game module.
    def test_lifecycle_bridge_has_no_route_or_game_activation(self):
        # Resolve the repository-owned application package from this focused test path.
        casino_root = Path(__file__).resolve().parents[1] / "casino"
        # Enumerate public application wiring and every isolated game source deterministically.
        candidate_paths = tuple(sorted((casino_root / "games").rglob("*.py"))) + (casino_root / "app.py", casino_root / "router.py")
        # Read the exact internal lifecycle method names that must remain inert in Phase A.
        forbidden = ("execute_game_action_once", "resolve_game_action")
        # Inspect every route/game candidate without importing or executing it.
        for path in candidate_paths:
            # Decode repository source as strict UTF-8.
            source = path.read_text(encoding="utf-8")
            # Reject activation of either internal provider boundary outside casino/core.
            self.assertTrue(all(name not in source for name in forbidden), path.relative_to(casino_root.parent).as_posix())

    # Prove public execution validation rejects lookalike values without planner calls.
    def test_execution_boundary_rejects_lookalikes_before_planner(self):
        # Build one valid resource set.
        resources = _resources()
        # Build one valid identity.
        identity = _identity(resources=resources)
        # Track accidental planner execution.
        calls = []

        # Define one callable that must remain uninvoked.
        def planner(_snapshot):
            # Record a boundary-ordering failure if invoked.
            calls.append("called")
            # Return a syntactically valid plan.
            return GameActionPlan.create(outcome={})

        # Enumerate malformed boundary inputs.
        invalid_inputs = (
            # Reject a dictionary lookalike identity.
            {"identity": {}, "resources": resources, "planner": planner},
            # Reject a dictionary lookalike resource declaration.
            {"identity": identity, "resources": {}, "planner": planner},
            # Reject a non-callable planner.
            {"identity": identity, "resources": resources, "planner": None},
        )
        # Exercise each malformed public boundary independently.
        for values in invalid_inputs:
            # Keep each boundary case isolated.
            with self.subTest(field_types=tuple(type(value).__name__ for value in values.values())):
                # Require one public validation failure.
                with self.assertRaises(ValidationError):
                    # Validate the malformed entry tuple.
                    validate_execution_request(**values)
        # Prove validation never invoked planner/RNG semantics.
        self.assertEqual(calls, [])


# Run the focused suite directly when requested by the authoring lane.
if __name__ == "__main__":
    # Execute unittest without repository runner registration.
    unittest.main()
