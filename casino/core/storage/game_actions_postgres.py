# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""PostgreSQL exactly-once game-action execution and resolution lifecycle."""

# Import hashing so immutable receipt semantics retain an application-owned digest.
import hashlib
# Import exact decimal arithmetic for native wallet and ledger projections.
from decimal import Decimal
# Import caller operation typing for the provider-neutral planner contract.
from typing import Any, Callable

# Import the canonical clock for wallet, state, and ledger writes.
from casino.core.clock import utc_now
# Import immutable action values and validation helpers.
from casino.core.game_action import GameActionIdentity, GameActionPlan, GameActionReceipt, GameActionResolution, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, canonical_json_bytes, validate_execution_request, validate_resolution_request
# Import the provider-neutral decoder accepted for psycopg JSONB mappings and model rows.
from casino.core.storage.base import _decode_json
# Import shared provider-neutral receipt codecs and ledger projection helpers.
from casino.core.storage.game_actions_json import JsonGameActionMixin
# Import the shared bounded reset-epoch ceiling.
from casino.core.storage.reset import _GAME_ACTION_MAX_EPOCH
# Import fixed application error boundaries retained across provider implementations.
from casino.errors import ConflictError, NotFoundError, ValidationError

# Keep PostgreSQL lifecycle corruption behind one value-free recovery category.
_POSTGRES_GAME_ACTION_RECOVERY_ERROR = "Game action storage requires operator recovery"
# Add PostgreSQL-native exactly-once action ownership to the shared receipt codecs.
class PostgresGameActionMixin(JsonGameActionMixin):
    # Require exact clean schema five inside the active lifecycle transaction.
    def _require_postgres_game_action_schema(self, connection) -> None:
        # Re-read checksum-bound control metadata on this transaction connection.
        state = self._runtime_schema_state(connection)
        # Accept only the complete PostgreSQL catalog containing claims and reset ownership.
        if not state.initialized or state.status != "clean" or state.current_version != 5:
            # Preserve all lifecycle and resource rows for explicit operator recovery.
            raise ConflictError("PostgreSQL game action lifecycle requires the clean schema 5 prefix")

    # Lock and validate the singleton reset namespace inside an active transaction.
    def _postgres_game_action_epoch(self, cursor) -> dict:
        # Delegate the fixed shared-lock statement and validation to the provider owner.
        state = self._reset_epoch(cursor, exclusive=False)
        # Require an exact bounded epoch independently from the provider implementation.
        if type(state) is not dict or type(state.get("current_epoch")) is not int or not 1 <= state["current_epoch"] <= _GAME_ACTION_MAX_EPOCH:
            # Preserve malformed lifecycle authority for operator inspection.
            raise ConflictError("PostgreSQL game action lifecycle requires operator recovery")
        # Return the validated provider-owned singleton.
        return state

    # Convert one PostgreSQL numeric wallet value into exact integer cents.
    def _postgres_game_action_cents(self, value: Any) -> int:
        # Convert through decimal string form without binary floating-point arithmetic.
        scaled = Decimal(str(value)) * Decimal(100)
        # Require one finite exact integral-cent value.
        if not scaled.is_finite() or scaled != scaled.to_integral_value():
            # Preserve malformed wallet authority for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Reuse the contract's exact balance range and nonnegative validation.
            snapshot = GameActionSnapshot.create(resources=GameActionResources(wallet_ids=("wallet",)), wallet_balances={"wallet": int(scaled)}, state_values={})
        # Normalize invalid connector values into the fixed wallet boundary.
        except (ValueError, OverflowError, ValidationError):
            # Preserve the source row without reflecting its value.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Return the exact validated integer-cent balance.
        return snapshot.wallet_balance("wallet")

    # Decode and bound one PostgreSQL JSONB lifecycle value.
    def _decode_postgres_game_action_json(self, value: Any) -> Any:
        # Decode connector strings, bytes, or already-decoded JSONB containers uniformly.
        try:
            # Preserve the provider-neutral strict JSON boundary for modeled text rows.
            decoded = _decode_json(value)
            # Re-encode through canonical limits to reject hostile depth, width, or scalar types.
            canonical_json_bytes(decoded)
        # Collapse malformed JSONB and canonical contract failures without stored detail.
        except (TypeError, ValueError, ValidationError, RecursionError):
            # Preserve the exact immutable row for operator recovery.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR) from None
        # Return the validated ordinary JSON value.
        return decoded

    # Decode and validate one immutable PostgreSQL receipt row.
    def _postgres_game_action_receipt(self, row: dict) -> GameActionReceipt:
        # Require the exact selected dict-row field inventory.
        expected = {"reset_epoch", "game_id", "player_id", "action_key", "request_fingerprint", "resources_json", "receipt_json", "receipt_sha256", "claim_disposition"}
        # Reject missing, additional, or non-mapping row shapes.
        if type(row) is not dict or set(row) != expected:
            # Preserve ambiguous receipt authority for operator recovery.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Decode and reconstruct the exact resource declaration.
        resources = self._deserialize_game_action_resources(self._decode_postgres_game_action_json(row["resources_json"]))
        # Decode the complete immutable receipt graph from JSONB.
        receipt_value = self._decode_postgres_game_action_json(row["receipt_json"])
        # Hash the canonical application JSON bytes rather than PostgreSQL's JSONB text format.
        receipt_digest = hashlib.sha256(canonical_json_bytes(receipt_value)).hexdigest()
        # Require the application-owned immutable checksum to match exactly.
        if receipt_digest != row["receipt_sha256"]:
            # Refuse corrupted or semantically changed receipt authority.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Reconstruct and self-validate the complete immutable receipt.
        receipt = self._deserialize_game_action_receipt(receipt_value)
        # Bind all duplicated row identity and semantic fields to the receipt.
        if receipt.identity.scope_key != (row["game_id"], row["player_id"], row["action_key"]) or receipt.identity.request_fingerprint != row["request_fingerprint"] or receipt.resources != resources:
            # Preserve split immutable authority without returning a partial receipt.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Require every receipt to belong to an immutable execute claim.
        if row["claim_disposition"] != "execute":
            # Refuse a receipt detached from executable ownership.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Return the exact provider-neutral committed receipt.
        return receipt

    # Read one immutable receipt under the caller's active transaction.
    def _select_postgres_game_action_receipt(self, cursor, identity: GameActionIdentity, reset_epoch: int) -> GameActionReceipt | None:
        # Query the exact epoch-scoped primary key and immutable receipt graph.
        cursor.execute(
            "SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition FROM casino_game_action_receipts WHERE reset_epoch = %s AND game_id = %s AND player_id = %s AND action_key = %s FOR SHARE",
            (reset_epoch, *identity.scope_key),
        )
        # Read the optional committed row.
        row = cursor.fetchone()
        # Preserve the unused-key result without inventing authority.
        if row is None:
            # Return no committed outcome.
            return None
        # Require the selected row to remain in the captured namespace.
        if type(row) is not dict or type(row.get("reset_epoch")) is not int or row["reset_epoch"] != reset_epoch:
            # Refuse connector coercion or cross-epoch drift.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Decode and validate the complete immutable row.
        return self._postgres_game_action_receipt(row)

    # Insert or inspect one immutable PostgreSQL lifecycle claim.
    def _claim_postgres_game_action(self, cursor, identity: GameActionIdentity, resources: GameActionResources, disposition: str, reset_epoch: int) -> tuple[str, bool]:
        # Serialize exact resources once for storage and compatibility checks.
        resources_json = canonical_json_bytes(self._serialize_game_action_resources(resources)).decode("utf-8")
        # Attempt one append-only insert while leaving any existing winner unchanged.
        cursor.execute(
            "INSERT INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, CAST(%s AS JSONB), %s) ON CONFLICT (reset_epoch, game_id, player_id, action_key) DO NOTHING",
            (reset_epoch, *identity.scope_key, identity.request_fingerprint, resources_json, disposition),
        )
        # Require PostgreSQL's exact inserted-or-conflicted affected-row domain.
        if cursor.rowcount not in {0, 1}:
            # Refuse ambiguous connector results inside the transaction.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Remember whether this transaction inserted the immutable winner.
        inserted = cursor.rowcount == 1
        # Lock and read the winning row after conflicting inserts serialize.
        cursor.execute(
            "SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition FROM casino_game_action_claims WHERE reset_epoch = %s AND game_id = %s AND player_id = %s AND action_key = %s FOR SHARE",
            (reset_epoch, *identity.scope_key),
        )
        # Require the new or prior winning claim to exist.
        row = cursor.fetchone()
        # Validate the exact immutable claim field inventory.
        expected = {"reset_epoch", "game_id", "player_id", "action_key", "request_fingerprint", "resources_json", "disposition"}
        # Reject disappearance, cross-epoch drift, or additional authority fields.
        if type(row) is not dict or set(row) != expected or type(row["reset_epoch"]) is not int or row["reset_epoch"] != reset_epoch:
            # Preserve transactional state for rollback and operator recovery.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Reconstruct the exact durable resource declaration.
        stored_resources = self._deserialize_game_action_resources(self._decode_postgres_game_action_json(row["resources_json"]))
        # Reject changed fingerprint or resources before any planner or resource read.
        if row["request_fingerprint"] != identity.request_fingerprint or stored_resources != resources:
            # Keep the original immutable claim unchanged.
            raise ConflictError("Game action key conflicts with durable semantics")
        # Require one finite immutable winning disposition.
        if row["disposition"] not in {"execute", "uncommitted"}:
            # Preserve malformed claim authority for operator repair.
            raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
        # Return the winning disposition and whether this transaction inserted it.
        return row["disposition"], inserted

    # Capture exact locked PostgreSQL wallet and state resources for one planner.
    def _capture_postgres_game_action_snapshot(self, cursor, resources: GameActionResources) -> GameActionSnapshot:
        # Collect exact integer-cent wallet balances by declared identity.
        wallet_balances = {}
        # Lock wallets in canonical order to prevent cross-action deadlocks.
        for wallet_id in resources.wallet_ids:
            # Lock one exact wallet row for the complete action transaction.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (wallet_id,))
            # Read the required wallet row.
            row = cursor.fetchone()
            # Reject a missing wallet through the established provider boundary.
            if row is None:
                # Preserve the transaction for rollback by the caller.
                raise NotFoundError(f"Player {wallet_id} was not found")
            # Require exact dictionary identity before trusting its balance.
            if type(row) is not dict or set(row) != {"player_id", "balance"} or row["player_id"] != wallet_id:
                # Preserve inconsistent wallet authority for recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Convert the numeric balance to exact integer cents.
            wallet_balances[wallet_id] = self._postgres_game_action_cents(row["balance"])
        # Collect exact route-free game-state documents.
        state_values = {}
        # Lock states in canonical order alongside wallet rows.
        for state_key in resources.state_keys:
            # Create a lockable empty JSONB document without replacing prior authority.
            cursor.execute("INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, CAST(%s AS JSONB), %s) ON CONFLICT (document_key) DO NOTHING", (state_key, "{}", utc_now()))
            # Lock the exact state row for snapshot and later replacement.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (state_key,))
            # Read the row established by insert-or-select.
            row = cursor.fetchone()
            # Require one exact dict-row payload projection.
            if type(row) is not dict or set(row) != {"payload_json"}:
                # Refuse impossible disappearance or ambiguous state.
                raise ConflictError("Game action state requires operator recovery")
            # Decode the existing provider JSONB value.
            state_values[state_key] = self._decode_postgres_game_action_json(row["payload_json"])
        # Freeze and validate the complete bounded planner snapshot.
        return GameActionSnapshot.create(resources=resources, wallet_balances=wallet_balances, state_values=state_values)

    # Insert exact deterministic ledger movements inside the active transaction.
    def _insert_postgres_game_action_ledger(self, cursor, receipt: GameActionReceipt) -> None:
        # Visit the provider-neutral deterministic events in movement order.
        for event in self._game_action_ledger_events(receipt):
            # Insert one append-only ledger row with PostgreSQL JSONB details.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSONB))",
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], Decimal(str(event["amount"])), Decimal(str(event["balance_before"])), Decimal(str(event["balance_after"])), "game_action", event["ledger_id"], receipt.identity.request_fingerprint, self._canonical_json(event["details"])),
            )

    # Execute or replay one PostgreSQL game action in one atomic transaction.
    def execute_game_action_once(self, *, identity: GameActionIdentity, resources: GameActionResources, planner: Callable[[GameActionSnapshot], GameActionPlan]) -> tuple[GameActionReceipt, bool]:
        # Validate exact provider-neutral types before connection or row locking.
        validate_execution_request(identity=identity, resources=resources, planner=planner)
        # Reject recursive execution from inside another planner on this provider.
        self._reject_planner_mutation()
        # Fail before checkout when this process owns reset bootstrap.
        if self._game_action_reset_is_active():
            # Preserve claim-zero and planner-zero reset exclusion.
            raise ConflictError("Game action reset is in progress")
        # Own claim, resources, ledger, state, and receipt in one host transaction.
        with self._database_cursor(commit=True) as (connection, cursor):
            # Re-verify exact clean schema five on this transaction connection.
            self._require_postgres_game_action_schema(connection)
            # Hold shared ownership of one reset epoch through the full action.
            epoch_state = self._postgres_game_action_epoch(cursor)
            # Refuse action planning while reset bootstrap remains incomplete.
            if epoch_state["phase"] != "ready":
                # Fail before claim insertion, resource access, or planner invocation.
                raise ConflictError("Game action reset is in progress")
            # Capture the exact immutable namespace for every lifecycle row.
            reset_epoch = epoch_state["current_epoch"]
            # Insert or serialize behind the exact lifecycle claim.
            disposition, inserted = self._claim_postgres_game_action(cursor, identity, resources, "execute", reset_epoch)
            # Reject a resolver-owned tombstone before snapshots or planner/RNG.
            if disposition == "uncommitted":
                # Preserve the winning immutable claim.
                raise ConflictError("Game action was durably resolved as uncommitted")
            # Read a compatible committed receipt after the claim lock is held.
            existing = self._select_postgres_game_action_receipt(cursor, identity, reset_epoch)
            # Resolve committed replay without another planner invocation.
            if existing is not None:
                # Reject changed resource or fingerprint semantics before return.
                if existing.identity != identity or existing.resources != resources:
                    # Preserve immutable claim and receipt rows.
                    raise ConflictError("Game action key conflicts with committed semantics")
                # Return the original immutable committed receipt after host commit.
                return existing, True
            # Refuse a prior execute claim whose receipt is absent after lock acquisition.
            if not inserted:
                # Preserve the orphaned claim for operator recovery.
                raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
            # Lock and snapshot every declared wallet and state resource.
            snapshot_before = self._capture_postgres_game_action_snapshot(cursor, resources)
            # Prevent the synchronous planner from mutating this provider through a closure.
            with self._planner_boundary():
                # Invoke the caller planner exactly once under all retained row locks.
                plan = planner(snapshot_before)
            # Require the exact immutable plan result type.
            if type(plan) is not GameActionPlan:
                # Reject plan-like objects before any committed projection.
                raise ValidationError("Game action planner returned an invalid plan")
            # Compute and validate the exact deterministic committed snapshot.
            snapshot_after = apply_plan_to_snapshot(snapshot_before, plan)
            # Construct the complete immutable receipt before projection DML.
            receipt = GameActionReceipt(identity=identity, resources=resources, snapshot_before=snapshot_before, plan=plan, snapshot_after=snapshot_after)
            # Publish exact final wallet balances under retained row locks.
            for wallet_id, balance_cents in receipt.snapshot_after.wallet_balances:
                # Update only the declared wallet with exact decimal cents.
                cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (Decimal(balance_cents) / Decimal(100), utc_now(), wallet_id))
                # Require the locked wallet row to remain uniquely present.
                if cursor.rowcount != 1:
                    # Fail the complete action transaction closed.
                    raise ConflictError("Game action wallet state requires operator recovery")
            # Append every movement ledger row inside the same transaction.
            self._insert_postgres_game_action_ledger(cursor, receipt)
            # Publish exact final state documents under retained row locks.
            for state_key, state_value in receipt.snapshot_after.state_values:
                # Replace one declared JSONB document through a bound canonical payload.
                cursor.execute("UPDATE casino_documents SET payload_json = CAST(%s AS JSONB), updated_at = %s WHERE document_key = %s", (canonical_json_bytes(self._plain_canonical(state_value)).decode("utf-8"), utc_now(), state_key))
                # Require the locked state row to remain uniquely present.
                if cursor.rowcount != 1:
                    # Fail the complete action transaction closed.
                    raise ConflictError("Game action state requires operator recovery")
            # Serialize exact resource and receipt bytes for immutable storage.
            resources_json = canonical_json_bytes(self._serialize_game_action_resources(resources)).decode("utf-8")
            # Serialize the complete receipt through the shared durable codec.
            receipt_json = canonical_json_bytes(self._serialize_game_action_receipt(receipt)).decode("utf-8")
            # Hash the exact canonical application receipt bytes.
            receipt_sha256 = hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
            # Insert the immutable receipt as the final action row.
            cursor.execute(
                "INSERT INTO casino_game_action_receipts (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition) VALUES (%s, %s, %s, %s, %s, CAST(%s AS JSONB), CAST(%s AS JSONB), %s, 'execute')",
                (reset_epoch, *identity.scope_key, identity.request_fingerprint, resources_json, receipt_json, receipt_sha256),
            )
            # Return the newly committed immutable receipt.
            return receipt, False

    # Resolve one PostgreSQL action without invoking its planner.
    def resolve_game_action(self, *, identity: GameActionIdentity, resources: GameActionResources) -> GameActionResolution:
        # Validate exact provider-neutral types before connection or lock attempts.
        validate_resolution_request(identity=identity, resources=resources)
        # Reject lifecycle mutation from inside an active planner.
        self._reject_planner_mutation()
        # Return finite pending before checkout during same-process reset bootstrap.
        if self._game_action_reset_is_active():
            # Preserve claim-zero and bounded capacity-one behavior.
            return GameActionResolution(status="pending")
        # Own the complete resolver race in one committed host transaction.
        with self._database_cursor(commit=True) as (connection, cursor):
            # Bound row-lock waits only for this transaction through SET LOCAL.
            cursor.execute("SET LOCAL lock_timeout = '1000ms'")
            try:
                # Require exact clean schema five on the resolver connection.
                self._require_postgres_game_action_schema(connection)
                # Hold shared epoch ownership before lifecycle lookup or insertion.
                epoch_state = self._postgres_game_action_epoch(cursor)
                # Treat reset bootstrap as finite pending without a claim.
                if epoch_state["phase"] != "ready":
                    # Return no outcome after the host commits the read-only transaction.
                    return GameActionResolution(status="pending")
                # Capture the exact ready namespace for resolver competition.
                reset_epoch = epoch_state["current_epoch"]
                # Insert or serialize behind the exact lifecycle claim.
                disposition, _inserted = self._claim_postgres_game_action(cursor, identity, resources, "uncommitted", reset_epoch)
                # Return the durable resolver-owned tombstone when it won first.
                if disposition == "uncommitted":
                    # Return the terminal provider-neutral state after host commit.
                    return GameActionResolution(status="uncommitted")
                # Read the execute owner's immutable receipt after its claim lock releases.
                receipt = self._select_postgres_game_action_receipt(cursor, identity, reset_epoch)
                # Refuse an execute claim visible without its atomic receipt.
                if receipt is None:
                    # Preserve the orphaned claim for operator recovery.
                    raise ConflictError(_POSTGRES_GAME_ACTION_RECOVERY_ERROR)
                # Reject changed compatible fields before returning outcome data.
                if receipt.identity != identity or receipt.resources != resources:
                    # Preserve immutable execute history.
                    raise ConflictError("Game action key conflicts with committed semantics")
                # Return the complete immutable committed result after host commit.
                return GameActionResolution(status="committed", receipt=receipt)
            except BaseException as error:
                # Convert only PostgreSQL lock timeout or deadlock categories to pending.
                if self._is_game_action_lock_contention(error):
                    # End the failed transaction before normal context-manager completion.
                    connection.rollback()
                    # Return no partial receipt while execution ownership remains uncertain.
                    return GameActionResolution(status="pending")
                # Preserve every provider, semantic, and caller-owned failure unchanged.
                raise
