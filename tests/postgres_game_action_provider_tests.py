# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic transaction-model tests for PostgreSQL game-action storage."""

# Import syntax inspection for fixed-literal SQL governance.
import ast
# Import context managers for provider-owned transaction and planner seams.
from contextlib import contextmanager
# Import deep copies so failed model transactions leave no residue.
from copy import deepcopy
# Import exact PostgreSQL-compatible fake-money values.
from decimal import Decimal
# Import JSON for JSONB-like decoded model values and canonical provider text.
import json
# Import portable paths for listener-free live-source binding.
from pathlib import Path
# Import source inspection for append-only lifecycle assertions.
import inspect
# Import thread synchronization for deterministic concurrent ownership tests.
import threading
# Import immutable migration-state stand-ins for schema-five checks.
from types import SimpleNamespace
# Import the standalone focused test framework.
import unittest

# Import provider-neutral action contracts used by every modeled call.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionResolution, GameActionResources
# Import the provider-neutral executor contract implemented by the concrete provider.
from casino.core.game_action import GameActionExecutor
# Import the PostgreSQL lifecycle implementation under test.
from casino.core.storage.game_actions_postgres import PostgresGameActionMixin
# Import the concrete provider only to prove the accepted mixin composition seam.
from casino.core.storage.postgres_provider import PostgresStorageProvider
# Import stable public conflict and planner-purity boundaries.
from casino.errors import ConflictError, ValidationError


# Represent only the two provider-classified PostgreSQL lock failures.
class _LockContention(RuntimeError):
    # Keep the fake category free of connector or target diagnostics.
    pass


# Store one committed relational image shared by modeled connections.
class _Database:
    # Initialize the minimum schema-five rows needed by game actions.
    def __init__(self) -> None:
        # Seed one exact player wallet.
        self.players = {"human": {"player_id": "human", "balance": Decimal("10.00")}}
        # Store route-free JSONB documents by resource identity.
        self.documents = {}
        # Store immutable claims by epoch-prefixed action scope.
        self.claims = {}
        # Store immutable receipts by epoch-prefixed action scope.
        self.receipts = {}
        # Store deterministic append-only ledger rows by identity.
        self.ledger = {}
        # Store the singleton reset namespace and visibility phase.
        self.epoch = {"state_id": 1, "current_epoch": 1, "phase": "ready"}
        # Serialize modeled row-locking transactions over the shared image.
        self.lock = threading.RLock()
        # Inject one bounded resolver lock failure before claim mutation.
        self.lock_contention_once = False
        # Inject one final receipt publication failure after every mutable projection.
        self.receipt_failure_once = False

    # Return one detached transaction image.
    def snapshot(self) -> dict:
        # Copy every relation so rollback remains complete.
        return deepcopy({"players": self.players, "documents": self.documents, "claims": self.claims, "receipts": self.receipts, "ledger": self.ledger, "epoch": self.epoch})

    # Publish one successful complete transaction image.
    def commit(self, state: dict) -> None:
        # Replace all related tables atomically under the model lock.
        self.players, self.documents, self.claims, self.receipts, self.ledger, self.epoch = (state[name] for name in ("players", "documents", "claims", "receipts", "ledger", "epoch"))


# Model only connection behavior consumed by the host transaction seam.
class _Connection:
    # Bind one isolated transaction to the shared committed database.
    def __init__(self, database: _Database) -> None:
        # Retain the shared relational target.
        self.database = database
        # Start from one detached committed image.
        self.state = database.snapshot()
        # Track explicit rollback used by finite resolver contention.
        self.rollbacks = 0
        # Track one successful host commit.
        self.commits = 0
        # Track deterministic lease cleanup.
        self.closed = False

    # Publish the complete current image.
    def commit(self) -> None:
        # Replace committed relations atomically.
        self.database.commit(self.state)
        # Count the exact successful boundary.
        self.commits += 1

    # Discard all transaction-local changes.
    def rollback(self) -> None:
        # Reload the current committed image after failure.
        self.state = self.database.snapshot()
        # Count the exact cleanup boundary.
        self.rollbacks += 1

    # Mark the deterministic lease closed.
    def close(self) -> None:
        # Retain close evidence for assertions.
        self.closed = True


# Interpret the bounded SQL emitted by the PostgreSQL mixin.
class _Cursor:
    # Bind one dict-row cursor to the active model transaction.
    def __init__(self, connection: _Connection) -> None:
        # Retain the active connection image.
        self.connection = connection
        # Initialize no result row.
        self.result = None
        # Initialize no affected rows.
        self.rowcount = 0

    # Return the active transaction image.
    def _state(self) -> dict:
        # Preserve one direct alias only inside this modeled transaction.
        return self.connection.state

    # Decode one bound canonical JSON string like psycopg JSONB adaptation.
    @staticmethod
    def _jsonb(value):
        # Return ordinary decoded containers for production decoder coverage.
        return json.loads(value) if type(value) is str else deepcopy(value)

    # Execute one reviewed fixed production statement.
    def execute(self, statement: str, params=()) -> None:
        # Normalize whitespace only for deterministic dispatch.
        sql = " ".join(statement.split())
        # Clear the previous result and affected-row count.
        self.result, self.rowcount = None, 0
        # Apply the transaction-local resolver wait policy without session mutation.
        if sql == "SET LOCAL lock_timeout = '1000ms'":
            # Stop after accepting the exact fixed bound.
            return
        # Insert one immutable lifecycle claim with ON CONFLICT no-op semantics.
        if sql.startswith("INSERT INTO casino_game_action_claims"):
            # Surface one classified lock error before any transaction mutation.
            if self.connection.database.lock_contention_once:
                # Consume the one-shot contention event.
                self.connection.database.lock_contention_once = False
                # Raise only the fixed modeled category.
                raise _LockContention("modeled lock contention")
            # Split every exact bound claim value.
            reset_epoch, game_id, player_id, action_key, fingerprint, resources_json, disposition = params
            # Build the epoch-prefixed immutable key.
            key = (reset_epoch, game_id, player_id, action_key)
            # Insert only when no prior winner exists.
            if key not in self._state()["claims"]:
                # Preserve one JSONB-like decoded resources mapping.
                self._state()["claims"][key] = {"reset_epoch": reset_epoch, "game_id": game_id, "player_id": player_id, "action_key": action_key, "request_fingerprint": fingerprint, "resources_json": self._jsonb(resources_json), "disposition": disposition}
                # Report one inserted winner.
                self.rowcount = 1
            # Stop after insert-or-conflict.
            return
        # Select the immutable winning claim under a shared row lock.
        if sql.startswith("SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition FROM casino_game_action_claims"):
            # Return a detached dict-row projection.
            self.result = deepcopy(self._state()["claims"].get(tuple(params)))
            # Stop after the point lookup.
            return
        # Select the immutable receipt under a shared row lock.
        if sql.startswith("SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition"):
            # Return a detached dict-row projection.
            self.result = deepcopy(self._state()["receipts"].get(tuple(params)))
            # Stop after the point lookup.
            return
        # Lock one exact wallet row.
        if sql.startswith("SELECT player_id, balance FROM casino_players"):
            # Return the optional detached wallet mapping.
            self.result = deepcopy(self._state()["players"].get(params[0]))
            # Stop after the wallet lookup.
            return
        # Create one lockable empty state document without replacement.
        if sql.startswith("INSERT INTO casino_documents"):
            # Split the exact document values.
            state_key, payload_json, _updated_at = params
            # Preserve any existing state authority.
            self._state()["documents"].setdefault(state_key, self._jsonb(payload_json))
            # Stop after insert-or-conflict.
            return
        # Lock one exact state document.
        if sql.startswith("SELECT payload_json FROM casino_documents"):
            # Read the required document value.
            payload = self._state()["documents"].get(params[0])
            # Return the exact dict-row projection when present.
            self.result = None if payload is None else {"payload_json": deepcopy(payload)}
            # Stop after the state lookup.
            return
        # Replace one locked wallet balance.
        if sql.startswith("UPDATE casino_players SET balance"):
            # Split exact balance, timestamp, and wallet identity.
            balance, _updated_at, wallet_id = params
            # Replace only an existing locked row.
            if wallet_id in self._state()["players"]:
                # Publish the exact Decimal projection transaction-locally.
                self._state()["players"][wallet_id]["balance"] = balance
                # Report one changed row.
                self.rowcount = 1
            # Stop after the wallet projection.
            return
        # Append one exact deterministic ledger event.
        if sql.startswith("INSERT INTO casino_ledger"):
            # Bind fields in the production statement order.
            names = ("ledger_id", "ts", "player_id", "game", "round_id", "transaction_type", "amount", "balance_before", "balance_after", "action_scope", "action_key", "action_fingerprint", "details_json")
            # Build the stored event mapping.
            row = dict(zip(names, params))
            # Reject a duplicate deterministic ledger identity.
            if row["ledger_id"] in self._state()["ledger"]:
                # Surface a fixture-equivalent uniqueness failure.
                raise AssertionError("duplicate ledger identity")
            # Decode the JSONB details field like psycopg.
            row["details_json"] = self._jsonb(row["details_json"])
            # Append the immutable event.
            self._state()["ledger"][row["ledger_id"]] = row
            # Report one inserted row.
            self.rowcount = 1
            # Stop after ledger append.
            return
        # Replace one locked state document.
        if sql.startswith("UPDATE casino_documents SET payload_json"):
            # Split exact JSONB payload, timestamp, and state identity.
            payload_json, _updated_at, state_key = params
            # Replace only an existing locked row.
            if state_key in self._state()["documents"]:
                # Publish the decoded JSONB value transaction-locally.
                self._state()["documents"][state_key] = self._jsonb(payload_json)
                # Report one changed row.
                self.rowcount = 1
            # Stop after state projection.
            return
        # Insert one immutable committed receipt.
        if sql.startswith("INSERT INTO casino_game_action_receipts"):
            # Surface one caller-owned failure after wallet, ledger, and state writes.
            if self.connection.database.receipt_failure_once:
                # Consume the one-shot late transaction failure.
                self.connection.database.receipt_failure_once = False
                # Require the host transaction to roll back every earlier projection.
                raise RuntimeError("modeled receipt failure")
            # Split every explicit bound value; execute ownership is a SQL literal.
            reset_epoch, game_id, player_id, action_key, fingerprint, resources_json, receipt_json, receipt_sha256 = params
            # Build the epoch-prefixed receipt key.
            key = (reset_epoch, game_id, player_id, action_key)
            # Reject duplicate immutable receipt publication.
            if key in self._state()["receipts"]:
                # Surface a fixture-equivalent uniqueness failure.
                raise AssertionError("duplicate receipt")
            # Preserve all immutable fields as JSONB-like containers.
            self._state()["receipts"][key] = {"reset_epoch": reset_epoch, "game_id": game_id, "player_id": player_id, "action_key": action_key, "request_fingerprint": fingerprint, "resources_json": self._jsonb(resources_json), "receipt_json": self._jsonb(receipt_json), "receipt_sha256": receipt_sha256, "claim_disposition": "execute"}
            # Report one inserted row.
            self.rowcount = 1
            # Stop after receipt append.
            return
        # Reject any unexpected production SQL so behavior cannot be skipped.
        raise AssertionError(f"unexpected SQL category: {sql.split(' ', 3)[:3]}")

    # Return the current optional dict row.
    def fetchone(self):
        # Preserve one ordinary DB-API fetch result.
        return self.result


# Compose the production mixin with provider-owned host seams.
class _Provider(PostgresGameActionMixin):
    # Initialize one isolated model provider.
    def __init__(self, database: _Database, *, schema_version: int = 5) -> None:
        # Retain the shared committed target.
        self.database = database
        # Retain the exact runtime schema selected by each case.
        self.schema_version = schema_version
        # Track same-process reset ownership.
        self.reset_active = False
        # Track planner purity per thread.
        self.planner_local = threading.local()
        # Retain every modeled connection for boundary assertions.
        self.connections = []

    # Return exact compact canonical JSON for JSONB adaptation.
    @staticmethod
    def _canonical_json(value) -> str:
        # Preserve sorted deterministic provider serialization.
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    # Return the schema-five migration verifier result for this connection.
    def _runtime_schema_state(self, _connection):
        # Model only initialized clean state at the selected version.
        return SimpleNamespace(initialized=True, status="clean", current_version=self.schema_version)

    # Return the provider-owned shared reset row lock result.
    def _reset_epoch(self, cursor: _Cursor, *, exclusive: bool) -> dict:
        # Forbid lifecycle code from requesting exclusive reset ownership.
        if exclusive:
            # Surface a production/mixin seam defect.
            raise AssertionError("game actions requested exclusive reset ownership")
        # Return a detached exact singleton row from the active transaction.
        return deepcopy(cursor.connection.state["epoch"])

    # Report only this target's process-local reset ownership.
    def _game_action_reset_is_active(self) -> bool:
        # Return the deterministic reset registry projection.
        return self.reset_active

    # Classify only the fixed modeled lock category.
    @staticmethod
    def _is_game_action_lock_contention(error: BaseException) -> bool:
        # Exclude arbitrary planner and application failures.
        return isinstance(error, _LockContention)

    # Reject every same-provider lifecycle call from a planner.
    def _reject_planner_mutation(self) -> None:
        # Refuse re-entry while the current thread owns planner purity.
        if getattr(self.planner_local, "active", False):
            # Match the provider-neutral public validation boundary.
            raise ValidationError("Game action planner must be side-effect free")

    # Mark the exact synchronous planner interval.
    @contextmanager
    def _planner_boundary(self):
        # Reject nested planner ownership in the fixture too.
        self._reject_planner_mutation()
        # Activate thread-local purity before transferring control.
        self.planner_local.active = True
        try:
            # Transfer control to the caller-owned planner.
            yield
        finally:
            # Clear planner ownership after success or failure.
            self.planner_local.active = False

    # Own one complete serializable model transaction.
    @contextmanager
    def _database_cursor(self, *, commit: bool = False):
        # Serialize the same row-lock scope PostgreSQL would serialize by resource.
        with self.database.lock:
            # Construct one isolated connection image.
            connection = _Connection(self.database)
            # Retain the lease for assertions.
            self.connections.append(connection)
            # Construct one dict-row cursor.
            cursor = _Cursor(connection)
            try:
                # Transfer the complete transaction to the mixin.
                yield connection, cursor
                # Publish only requested successful mutations.
                if commit:
                    # Commit claim, projection, ledger, and receipt together.
                    connection.commit()
                else:
                    # End read-only transactions without publication.
                    connection.rollback()
            except BaseException:
                # Discard every partial relation on any caller failure.
                connection.rollback()
                # Preserve original exception identity and traceback.
                raise
            finally:
                # Close every modeled lease exactly once.
                connection.close()


# Build one exact paid action resource declaration.
def _resources() -> GameActionResources:
    # Bind one wallet and one route-free state document.
    return GameActionResources(wallet_ids=("human",), state_keys=("slots:human",))


# Build one exact resource-bound semantic identity.
def _identity(*, action_key="action-1", request=None, resources=None) -> GameActionIdentity:
    # Select the caller declaration or the ordinary paid fixture.
    selected = _resources() if resources is None else resources
    # Bind request and resources into the canonical fingerprint.
    return GameActionIdentity.create(game_id="slots", player_id="human", action_key=action_key, resources=selected, request=request or {"stake_cents": 100})


# Return one deterministic debit-and-payout plan.
def _plan(_snapshot) -> GameActionPlan:
    # Preserve exact movement order and final state.
    return GameActionPlan.create(outcome={"round_id": "round-1"}, movements=(GameActionMovement(wallet_id="human", amount_cents=-100, reason="wager"), GameActionMovement(wallet_id="human", amount_cents=250, reason="payout")), state_updates={"slots:human": {"spins": 1}})


# Exercise production PostgreSQL lifecycle code against the listener model.
class PostgresGameActionProviderTests(unittest.TestCase):
    # Allocate one clean schema-five store per case.
    def setUp(self) -> None:
        # Construct the committed relational image.
        self.database = _Database()
        # Construct the production mixin host seam.
        self.provider = _Provider(self.database)

    # Prove executor-first commit, replay, resolution, and JSONB receipt validation.
    def test_execute_replay_and_resolution_are_exactly_once(self):
        # Build exact shared semantics.
        resources, identity = _resources(), _identity()
        # Track planner invocations across execution and replay.
        calls = []
        # Define one observable deterministic planner.
        def planner(snapshot):
            # Retain the immutable snapshot once.
            calls.append(snapshot)
            # Return the exact paid plan.
            return _plan(snapshot)
        # Execute one new action.
        receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=planner)
        # Require one fresh result and one planner call.
        self.assertEqual((False, 1), (replayed, len(calls)))
        # Commit exact wallet, state, ledger, claim, and receipt projections.
        self.assertEqual((Decimal("11.5"), {"spins": 1}, 2, 1, 1), (self.database.players["human"]["balance"], self.database.documents["slots:human"], len(self.database.ledger), len(self.database.claims), len(self.database.receipts)))
        # Replay through an unreachable planner.
        replay_receipt, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("replay invoked planner"))
        # Return the exact immutable receipt without another projection.
        self.assertEqual((receipt, True, 2), (replay_receipt, replayed, len(self.database.ledger)))
        # Resolve the executor-owned result without a planner parameter.
        self.assertEqual(GameActionResolution(status="committed", receipt=receipt), self.provider.resolve_game_action(identity=identity, resources=resources))

    # Prove resolver-first tombstones and semantic conflicts precede resource access.
    def test_resolver_first_blocks_execution_and_changed_semantics(self):
        # Build exact resolver-first semantics.
        resources, identity = _resources(), _identity(action_key="resolver-first")
        # Commit one immutable no-result claim.
        self.assertEqual(GameActionResolution(status="uncommitted"), self.provider.resolve_game_action(identity=identity, resources=resources))
        # Preserve exact committed state before rejected operations.
        before = self.database.snapshot()
        # Reject later execution without planner invocation.
        with self.assertRaisesRegex(ConflictError, "^Game action was durably resolved as uncommitted$"):
            # Attempt execution behind the resolver tombstone.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("late planner ran"))
        # Build changed request semantics under the same action key.
        changed = _identity(action_key="resolver-first", request={"stake_cents": 200})
        # Reject the changed reuse without resource projection.
        with self.assertRaisesRegex(ConflictError, "^Game action key conflicts with durable semantics$"):
            # Resolve the incompatible request.
            self.provider.resolve_game_action(identity=changed, resources=resources)
        # Keep the immutable winner and all mutable relations unchanged.
        self.assertEqual(before, self.database.snapshot())

    # Prove planner failure and re-entry preserve original state and error identity.
    def test_planner_failure_and_reentry_roll_back_complete_transaction(self):
        # Build one fresh action scope.
        resources, identity = _resources(), _identity(action_key="planner-failure")
        # Preserve the exact committed baseline.
        before = self.database.snapshot()
        # Allocate one caller-owned failure object.
        failure = RuntimeError("planned failure")
        # Require the exact object to escape the provider seam.
        with self.assertRaises(RuntimeError) as captured:
            # Raise after claim and resource acquisition.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: (_ for _ in ()).throw(failure))
        # Preserve caller exception identity and full rollback.
        self.assertIs(captured.exception, failure)
        # Keep every relation byte-semantically unchanged.
        self.assertEqual(before, self.database.snapshot())
        # Build a second scope for hostile planner re-entry.
        reentry = _identity(action_key="planner-reentry")
        # Reject nested lifecycle access before opening a second transaction.
        with self.assertRaisesRegex(ValidationError, "^Game action planner must be side-effect free$"):
            # Attempt resolver re-entry from the active planner.
            self.provider.execute_game_action_once(identity=reentry, resources=resources, planner=lambda _snapshot: (self.provider.resolve_game_action(identity=reentry, resources=resources), _plan(_snapshot))[1])
        # Roll back the outer claim and empty state seed too.
        self.assertEqual(before, self.database.snapshot())
        # Build a third scope for failure at the final receipt publication boundary.
        late_failure = _identity(action_key="receipt-failure")
        # Inject the failure after wallet, ledger, and state projection statements.
        self.database.receipt_failure_once = True
        # Preserve the exact late failure after host rollback.
        with self.assertRaisesRegex(RuntimeError, "^modeled receipt failure$"):
            # Execute the otherwise valid paid action.
            self.provider.execute_game_action_once(identity=late_failure, resources=resources, planner=_plan)
        # Roll back claim, wallet, ledger, state, and absent receipt together.
        self.assertEqual(before, self.database.snapshot())
        # Permit the resolver to win after no execution authority was published.
        self.assertEqual(GameActionResolution(status="uncommitted"), self.provider.resolve_game_action(identity=late_failure, resources=resources))

    # Prove finite contention/reset pending and fail-closed schema gating create no claims.
    def test_pending_and_schema_boundaries_are_claim_zero(self):
        # Build one bounded action scope.
        resources, identity = _resources(), _identity(action_key="pending")
        # Inject one provider-classified resolver contention.
        self.database.lock_contention_once = True
        # Return finite pending after explicit rollback.
        self.assertEqual(GameActionResolution(status="pending"), self.provider.resolve_game_action(identity=identity, resources=resources))
        # Preserve claim-zero and one explicit rollback.
        self.assertEqual(({}, 1), (self.database.claims, self.provider.connections[-1].rollbacks))
        # Activate same-process reset ownership.
        self.provider.reset_active = True
        # Return resolver pending before another connection.
        self.assertEqual(GameActionResolution(status="pending"), self.provider.resolve_game_action(identity=identity, resources=resources))
        # Reject executor reset overlap before planner or connection.
        with self.assertRaisesRegex(ConflictError, "^Game action reset is in progress$"):
            # Keep the action planner unreachable.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("reset planner ran"))
        # Clear local reset ownership and expose a durable resetting phase.
        self.provider.reset_active = False
        # Publish exact database-side reset bootstrap visibility.
        self.database.epoch["phase"] = "resetting"
        # Return finite resolver pending without inserting a claim.
        self.assertEqual(GameActionResolution(status="pending"), self.provider.resolve_game_action(identity=identity, resources=resources))
        # Reject executor before claim and planner under resetting visibility.
        with self.assertRaisesRegex(ConflictError, "^Game action reset is in progress$"):
            # Attempt execution during bootstrap.
            self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: self.fail("phase planner ran"))
        # Preserve claim-zero across every unavailable boundary.
        self.assertEqual({}, self.database.claims)
        # Construct a clean predecessor model.
        predecessor = _Provider(_Database(), schema_version=4)
        # Reject lifecycle DML on an incomplete catalog.
        with self.assertRaisesRegex(ConflictError, "requires the clean schema 5 prefix"):
            # Attempt resolver use before migration five.
            predecessor.resolve_game_action(identity=identity, resources=resources)

    # Prove zero-cost state actions and reset epochs retain isolated immutable history.
    def test_zero_cost_and_epoch_reuse_preserve_namespaces(self):
        # Declare a state-only action with no fake ledger movement.
        resources = GameActionResources(state_keys=("keno:human",))
        # Bind exact zero-cost request semantics.
        identity = _identity(action_key="state-only", request={"view": "opened"}, resources=resources)
        # Execute a state-only planner.
        first, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: GameActionPlan.create(outcome={"ok": True}, state_updates={"keno:human": {"views": 1}}))
        # Commit state without inventing money or ledger rows.
        self.assertEqual((False, {"views": 1}, {}), (replayed, self.database.documents["keno:human"], self.database.ledger))
        # Advance to a fresh ready reset namespace while retaining immutable history.
        self.database.epoch = {"state_id": 1, "current_epoch": 2, "phase": "ready"}
        # Clear only mutable state like provider reset phase one.
        self.database.documents = {}
        # Reuse the exact caller key as fresh epoch-two work.
        second, replayed = self.provider.execute_game_action_once(identity=identity, resources=resources, planner=lambda _snapshot: GameActionPlan.create(outcome={"ok": True}, state_updates={"keno:human": {"views": 2}}))
        # Require new execution and distinguish its projection.
        self.assertEqual((False, {"views": 2}), (replayed, self.database.documents["keno:human"]))
        # Retain both immutable receipts under disjoint epoch prefixes.
        self.assertEqual({1, 2}, {key[0] for key in self.database.receipts})
        # Keep complete immutable receipts distinct by their snapshots.
        self.assertNotEqual(first.snapshot_after, second.snapshot_after)

    # Prove concurrent same-key contenders invoke one planner and replay one receipt.
    def test_concurrent_execution_has_one_planner(self):
        # Import the bounded worker executor only for this contention case.
        from concurrent.futures import ThreadPoolExecutor
        # Build one shared immutable request.
        resources, identity = _resources(), _identity(action_key="concurrent")
        # Count planner ownership under an independent lock.
        calls, call_lock = [], threading.Lock()
        # Define one observable planner.
        def planner(snapshot):
            # Serialize only the test-owned counter.
            with call_lock:
                # Retain one planner observation.
                calls.append(snapshot)
            # Return the deterministic paid plan.
            return _plan(snapshot)
        # Submit eight callers against one durable action key.
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Collect every fresh-or-replayed result.
            results = list(executor.map(lambda _index: self.provider.execute_game_action_once(identity=identity, resources=resources, planner=planner), range(8)))
        # Invoke planner once and replay the other seven callers.
        self.assertEqual((1, 1, 7), (len(calls), sum(not replayed for _receipt, replayed in results), sum(replayed for _receipt, replayed in results)))
        # Return one equal immutable receipt to every caller.
        self.assertEqual(1, len({receipt for receipt, _replayed in results}))

    # Prove fixed literal SQL, append-only lifecycle, and provider-owned hook boundaries.
    def test_source_uses_literal_parameterized_append_only_sql(self):
        # Read the exact production module source.
        source = inspect.getsource(inspect.getmodule(PostgresGameActionMixin))
        # Parse all execute calls for interpolation-proof SQL ownership.
        tree = ast.parse(source)
        # Visit each function call in the production module.
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            # Skip calls other than cursor execution.
            if not isinstance(call.func, ast.Attribute) or call.func.attr != "execute":
                # Continue to the next syntax node.
                continue
            # Require every executed SQL expression to be a fixed string literal.
            self.assertTrue(call.args and isinstance(call.args[0], ast.Constant) and type(call.args[0].value) is str)
        # Normalize source for append-only lifecycle checks.
        upper = source.upper()
        # Reject lifecycle UPDATE and DELETE statements.
        for table in ("CASINO_GAME_ACTION_CLAIMS", "CASINO_GAME_ACTION_RECEIPTS"):
            # Reject mutable immutable-history SQL.
            self.assertNotIn(f"UPDATE {table}", upper)
            # Reject immutable-history deletion SQL.
            self.assertNotIn(f"DELETE FROM {table}", upper)
        # Require PostgreSQL-native conflict and JSONB semantics.
        self.assertIn("ON CONFLICT (RESET_EPOCH, GAME_ID, PLAYER_ID, ACTION_KEY) DO NOTHING", upper)
        # Require every dynamic SQL value to remain a bound placeholder.
        self.assertIn("CAST(%S AS JSONB)", upper)
        # Require only provider-owned lock/reset hooks.
        self.assertIn("_GAME_ACTION_RESET_IS_ACTIVE", upper)
        # Require the exact native contention classifier hook.
        self.assertIn("_IS_GAME_ACTION_LOCK_CONTENTION", upper)
        # Collect every imported module name without treating explanatory comments as code.
        imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        # Include from-import module owners in the same code-only inventory.
        imports.extend(node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
        # Forbid connector ownership in the mixin.
        self.assertFalse(any(name == "psycopg" or name.startswith("psycopg.") for name in imports))
        # Forbid direct driver escape in executable attribute access.
        self.assertFalse(any(isinstance(node, ast.Attribute) and node.attr == "_driver" for node in ast.walk(tree)))
        # Bind the concrete PostgreSQL provider to the native lifecycle mixin.
        self.assertTrue(issubclass(PostgresStorageProvider, PostgresGameActionMixin))
        # Bind the same concrete provider to the public executor contract.
        self.assertTrue(issubclass(PostgresStorageProvider, GameActionExecutor))
        # Read the explicit live helper as inert source without importing psycopg.
        live_source = (Path(__file__).resolve().parent / "postgres_game_action_live.py").read_text(encoding="utf-8")
        # Locate fresh execution, first pool close, reconstruction, and planner-zero replay markers.
        fresh_index = live_source.index("paid_receipt, paid_replayed = selected.execute_game_action_once")
        close_index = live_source.index("selected.close_pool()", fresh_index)
        restart_index = live_source.index("selected = PostgresStorageProvider(config, pool_config)", close_index)
        replay_index = live_source.index("replay_receipt, replayed = selected.execute_game_action_once", restart_index)
        # Require the explicit live gate to prove same-target provider restart before replay.
        self.assertTrue(fresh_index < close_index < restart_index < replay_index)


# Support direct focused execution in local and CI validation.
if __name__ == "__main__":
    # Run the focused suite with standard unittest output.
    unittest.main()
