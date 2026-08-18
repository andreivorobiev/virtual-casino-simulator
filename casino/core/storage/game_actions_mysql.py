# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""MySQL game-action schema, transaction, execution, and resolution lifecycle."""

# Import hashing so immutable receipt bytes retain their exact integrity digest.
import hashlib
# Import strict JSON decoding for binary-collated lifecycle fields and ledger detail writes.
import json
# Import decimal arithmetic so wallet rows convert through exact integer cents.
from decimal import Decimal
# Import callable and value typing for the provider-neutral planner boundary.
from typing import Any, Callable

# Import the canonical clock for wallet, state, and ledger projections.
from casino.core.clock import utc_now
# Import provider-neutral action values, codecs, and validation helpers.
from casino.core.game_action import GameActionIdentity, GameActionPlan, GameActionReceipt, GameActionResolution, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, canonical_json_bytes, validate_execution_request, validate_resolution_request
# Import read-only runtime schema verification for exact schema-four eligibility.
from casino.core.mysql_migrations import verify_runtime_compatibility
# Import the strict provider JSON decoder used for locked state documents.
from casino.core.storage.base import _decode_json
# Import the shared reset-epoch range accepted by both storage providers.
from casino.core.storage.reset import _GAME_ACTION_MAX_EPOCH
# Import fixed API error boundaries used by lifecycle validation and recovery.
from casino.errors import ConflictError, NotFoundError, ValidationError


# Own the MySQL game-action lifecycle while pool, reset, and ordinary provider I/O remain in storage.py.
class MySQLGameActionMixin:
    # Require exact clean schema four before exposing the inert lifecycle write bridge.
    def _runtime_schema_state(self, connection):
        # Delegate read-only catalog verification through one overridable test seam.
        return verify_runtime_compatibility(connection)

    # Require exact clean schema four before exposing the inert lifecycle write bridge.
    def _require_game_action_schema(self, connection) -> None:
        # Re-read control metadata on this transaction connection rather than trusting readiness cache.
        state = self._runtime_schema_state(connection)
        # Accept no older compatible schema because claims do not exist before migration four.
        if not state.initialized or state.status != "clean" or state.current_version != 4:
            # Keep ordinary schema-two/three runtime reads available while lifecycle writes fail closed.
            raise ConflictError("MySQL game action lifecycle requires clean schema 4")

    # Lock and validate the singleton MySQL reset epoch inside an active transaction.
    def _mysql_game_action_epoch(self, cursor, *, exclusive: bool = False) -> dict:
        # Select shared lifecycle visibility for actions or exclusive ownership for reset.
        lock_clause = "FOR UPDATE" if exclusive else "FOR SHARE"
        # Read the exact singleton row with the requested transaction lock.
        cursor.execute(f"SELECT state_id, current_epoch, phase FROM casino_game_action_epoch_state WHERE state_id = 1 {lock_clause}")
        # Fetch the sole expected control row.
        row = cursor.fetchone()
        # Require one exact dictionary row from the schema-four singleton.
        if type(row) is not dict or set(row) != {"current_epoch", "phase", "state_id"}:
            # Refuse absent, duplicate-projected, or malformed control state.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Require the fixed singleton identity without coercion.
        if type(row["state_id"]) is not int or row["state_id"] != 1:
            # Preserve the relational row for operator repair.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Require one bounded signed-range epoch shared with JSON.
        if type(row["current_epoch"]) is not int or not 1 <= row["current_epoch"] <= _GAME_ACTION_MAX_EPOCH:
            # Refuse overflow or connector coercion.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Require one finite reset phase.
        if type(row["phase"]) is not str or row["phase"] not in {"ready", "resetting"}:
            # Reject unknown visibility semantics.
            raise ConflictError("MySQL game action lifecycle requires operator recovery")
        # Return the validated row for same-transaction use.
        return row

    # Convert one exact MySQL decimal balance into provider-neutral integer cents.
    def _mysql_game_action_cents(self, value: Any) -> int:
        # Convert through decimal string form to avoid binary floating-point normalization.
        scaled = Decimal(str(value)) * Decimal(100)
        # Require an exact finite integral-cent value.
        if not scaled.is_finite() or scaled != scaled.to_integral_value():
            # Preserve malformed wallet rows for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Validate exact range and nonnegative semantics through a one-wallet snapshot.
            snapshot = GameActionSnapshot.create(resources=GameActionResources(wallet_ids=("wallet",)), wallet_balances={"wallet": int(scaled)}, state_values={})
        # Normalize contract validation into the provider recovery boundary.
        except (ValueError, OverflowError, ValidationError):
            # Preserve the original relational row unchanged.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Return the exact validated integer-cent balance.
        return snapshot.wallet_balance("wallet")

    # Decode one canonical text JSON field from the immutable lifecycle tables.
    def _decode_mysql_game_action_json(self, value: Any) -> Any:
        # Accept only bytes or text from the binary-collated TEXT columns.
        if isinstance(value, bytes):
            # Decode exact UTF-8 without replacement.
            raw = value.decode("utf-8")
        # Preserve driver-returned text exactly.
        elif type(value) is str:
            # Retain the raw text for canonical byte comparison.
            raw = value
        # Reject driver coercion or unexpected JSON-native shapes.
        else:
            # Preserve the row for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reject duplicate object keys while decoding immutable receipt material.
            decoded = json.loads(raw, object_pairs_hook=self._unique_json_object)
        # Normalize malformed UTF-8 or JSON without exposing stored bytes.
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            # Preserve the row for explicit operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None
        # Require the stored text to equal the unique canonical representation byte-for-byte.
        if canonical_json_bytes(decoded).decode("utf-8") != raw:
            # Refuse ambiguous whitespace, ordering, or numeric encodings.
            raise ConflictError("Game action storage requires operator recovery")
        # Return the strictly decoded canonical object.
        return decoded

    # Decode and validate one immutable MySQL receipt row.
    def _mysql_game_action_receipt(self, row: dict) -> GameActionReceipt:
        # Decode the complete canonical resource declaration.
        resources_value = self._decode_mysql_game_action_json(row["resources_json"])
        # Reconstruct exact resources through the provider-neutral validator.
        resources = self._deserialize_game_action_resources(resources_value)
        # Decode the complete canonical receipt graph.
        receipt_value = self._decode_mysql_game_action_json(row["receipt_json"])
        # Hash the exact stored bytes before accepting their semantic content.
        receipt_bytes = row["receipt_json"] if isinstance(row["receipt_json"], bytes) else str(row["receipt_json"]).encode("utf-8")
        # Hash the exact binary-collated text returned by the provider.
        receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()
        # Require the immutable row checksum to match exactly.
        if receipt_digest != row["receipt_sha256"]:
            # Refuse a corrupted or normalized receipt row.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct and self-validate the complete immutable receipt.
        receipt = self._deserialize_game_action_receipt(receipt_value)
        # Require duplicated row identity and resource fields to agree exactly.
        if receipt.identity.scope_key != (row["game_id"], row["player_id"], row["action_key"]) or receipt.identity.request_fingerprint != row["request_fingerprint"] or receipt.resources != resources:
            # Preserve inconsistent immutable lifecycle rows.
            raise ConflictError("Game action storage requires operator recovery")
        # Require every receipt child row to name only the execute disposition.
        if row.get("claim_disposition") != "execute":
            # Refuse a receipt detached from executable ownership.
            raise ConflictError("Game action storage requires operator recovery")
        # Return the exact provider-neutral committed receipt.
        return receipt

    # Read one immutable receipt under the caller's active transaction.
    def _select_mysql_game_action_receipt(self, cursor, identity: GameActionIdentity, reset_epoch: int) -> GameActionReceipt | None:
        # Query the exact primary-key scope and all immutable receipt bytes.
        cursor.execute(
            "SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition FROM casino_game_action_receipts WHERE reset_epoch = %s AND game_id = %s AND player_id = %s AND action_key = %s FOR SHARE",
            (reset_epoch, *identity.scope_key),
        )
        # Read the optional committed row.
        row = cursor.fetchone()
        # Preserve the unused-key result without inventing a receipt.
        if row is None:
            # Return no committed outcome.
            return None
        # Require the selected immutable row to remain in the captured namespace.
        if type(row.get("reset_epoch")) is not int or row["reset_epoch"] != reset_epoch:
            # Refuse connector coercion or cross-epoch row drift.
            raise ConflictError("Game action storage requires operator recovery")
        # Decode and validate the complete immutable row.
        return self._mysql_game_action_receipt(row)

    # Insert or inspect one immutable lifecycle claim under transaction ownership.
    def _claim_mysql_game_action(self, cursor, identity: GameActionIdentity, resources: GameActionResources, disposition: str, reset_epoch: int) -> tuple[str, bool]:
        # Serialize exact resources once for unique and compatibility checks.
        resources_json = canonical_json_bytes(self._serialize_game_action_resources(resources)).decode("utf-8")
        # Attempt one append-only insert without updating an existing winner.
        cursor.execute(
            "INSERT IGNORE INTO casino_game_action_claims (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (reset_epoch, *identity.scope_key, identity.request_fingerprint, resources_json, disposition),
        )
        # Remember whether this transaction inserted the immutable winning row.
        inserted = cursor.rowcount == 1
        # Lock and read the winning primary-key row after duplicate contenders serialize.
        cursor.execute(
            "SELECT reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, disposition FROM casino_game_action_claims WHERE reset_epoch = %s AND game_id = %s AND player_id = %s AND action_key = %s FOR SHARE",
            (reset_epoch, *identity.scope_key),
        )
        # Require the just-inserted or prior winning claim to exist.
        row = cursor.fetchone()
        # Reject impossible disappearance under the same transaction.
        if row is None:
            # Preserve transactional state for rollback.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the winning claim to belong to the captured epoch exactly.
        if type(row.get("reset_epoch")) is not int or row["reset_epoch"] != reset_epoch:
            # Refuse connector coercion or namespace drift.
            raise ConflictError("Game action storage requires operator recovery")
        # Decode exact resources before comparing semantic reuse.
        stored_resources = self._deserialize_game_action_resources(self._decode_mysql_game_action_json(row["resources_json"]))
        # Reject changed identity fingerprint or resources without invoking a planner.
        if row["request_fingerprint"] != identity.request_fingerprint or stored_resources != resources:
            # Keep the original immutable claim unchanged.
            raise ConflictError("Game action key conflicts with durable semantics")
        # Return the finite winning disposition and whether this transaction inserted it.
        return row["disposition"], inserted

    # Capture exact locked MySQL wallet and state resources for one planner.
    def _capture_mysql_game_action_snapshot(self, cursor, resources: GameActionResources) -> GameActionSnapshot:
        # Collect exact integer-cent wallet balances by declared identity.
        wallet_balances = {}
        # Lock wallets in canonical resource order to prevent cross-action deadlocks.
        for wallet_id in resources.wallet_ids:
            # Lock one exact wallet row for the complete lifecycle transaction.
            cursor.execute("SELECT player_id, balance FROM casino_players WHERE player_id = %s FOR UPDATE", (wallet_id,))
            # Read the required wallet row.
            row = cursor.fetchone()
            # Reject missing wallets through the established provider boundary.
            if row is None:
                # Preserve the transaction for rollback by the caller.
                raise NotFoundError(f"Player {wallet_id} was not found")
            # Convert the decimal balance to exact integer cents.
            wallet_balances[wallet_id] = self._mysql_game_action_cents(row["balance"])
        # Collect exact route-free game-state documents.
        state_values = {}
        # Lock states in canonical resource order alongside wallet rows.
        for state_key in resources.state_keys:
            # Create the exact lockable empty document without overwriting prior state.
            cursor.execute(
                "INSERT INTO casino_documents (document_key, payload_json, updated_at) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE document_key = VALUES(document_key)",
                (state_key, "{}", utc_now()),
            )
            # Lock the exact state row for snapshot and later replacement.
            cursor.execute("SELECT payload_json FROM casino_documents WHERE document_key = %s FOR UPDATE", (state_key,))
            # Read the state row established by the insert-or-lock operation.
            row = cursor.fetchone()
            # Reject impossible row disappearance.
            if row is None:
                # Fail closed within the transaction.
                raise ConflictError("Game action state requires operator recovery")
            # Decode the existing provider JSON shape.
            state_values[state_key] = _decode_json(row["payload_json"])
        # Freeze and validate the complete bounded provider snapshot.
        return GameActionSnapshot.create(resources=resources, wallet_balances=wallet_balances, state_values=state_values)

    # Insert exact ledger movements inside the active game-action transaction.
    def _insert_mysql_game_action_ledger(self, cursor, receipt: GameActionReceipt) -> None:
        # Build deterministic movement rows from immutable before/after snapshots.
        for event in self._game_action_ledger_events(receipt):
            # Insert each append-only ledger row with a dedicated compatible action namespace.
            cursor.execute(
                "INSERT INTO casino_ledger (ledger_id, ts, player_id, game, round_id, transaction_type, amount, balance_before, balance_after, action_scope, action_key, action_fingerprint, details_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (event["ledger_id"], event["ts"], event["player_id"], event["game"], event["round_id"], event["transaction_type"], event["amount"], event["balance_before"], event["balance_after"], "game_action", event["ledger_id"], receipt.identity.request_fingerprint, json.dumps(event["details"], sort_keys=True, separators=(",", ":"))),
            )

    # Execute or replay one schema-four MySQL game action in one transaction.
    def execute_game_action_once(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
        planner: Callable[[GameActionSnapshot], GameActionPlan],
    ) -> tuple[GameActionReceipt, bool]:
        # Validate exact provider-neutral types before any connection or row lock.
        validate_execution_request(identity=identity, resources=resources, planner=planner)
        # Reject recursive execution from inside another planner on this provider.
        self._reject_planner_mutation()
        # Fail before pool checkout when this process owns reset bootstrap at capacity one.
        if self._reset_is_active():
            # Preserve claim-zero and planner-zero reset exclusion.
            raise ConflictError("Game action reset is in progress")
        # Ensure ordinary runtime compatibility before opening the action transaction.
        self.ensure_ready()
        # Open one connection for claim, resources, ledger, state, and receipt.
        connection = self.connect()
        try:
            # Start one row-locking lifecycle transaction.
            connection.start_transaction()
            # Require exact clean schema four inside the same lifecycle transaction.
            self._require_game_action_schema(connection)
            # Open a dictionary cursor for immutable row reconstruction.
            cursor = connection.cursor(dictionary=True)
            # Hold shared ownership of one ready reset epoch through the full action transaction.
            epoch_state = self._mysql_game_action_epoch(cursor)
            # Refuse every action while reset bootstrap remains incomplete.
            if epoch_state["phase"] != "ready":
                # Fail before claim insertion, resource access, or planner invocation.
                raise ConflictError("Game action reset is in progress")
            # Capture the exact immutable namespace for every lifecycle row.
            reset_epoch = epoch_state["current_epoch"]
            # Insert or serialize behind the exact lifecycle claim.
            disposition, inserted = self._claim_mysql_game_action(cursor, identity, resources, "execute", reset_epoch)
            # Reject a resolver-owned tombstone before snapshots or planner/RNG.
            if disposition == "uncommitted":
                # Preserve the winning claim and roll back only this caller's no-op work.
                raise ConflictError("Game action was durably resolved as uncommitted")
            # Read a compatible committed receipt after the execute claim lock is held.
            existing = self._select_mysql_game_action_receipt(cursor, identity, reset_epoch)
            # Resolve committed replay without another planner invocation.
            if existing is not None:
                # Reject changed resource or fingerprint reuse before returning the result.
                if existing.identity != identity or existing.resources != resources:
                    # Preserve immutable claim and receipt rows.
                    raise ConflictError("Game action key conflicts with committed semantics")
                # Commit the read-only transaction and release row ownership.
                connection.commit()
                # Return the original immutable committed receipt.
                return existing, True
            # Refuse a prior execute claim whose receipt is absent after lock acquisition.
            if not inserted:
                # Preserve the orphaned claim for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Lock and snapshot every declared wallet and state resource.
            snapshot_before = self._capture_mysql_game_action_snapshot(cursor, resources)
            # Prevent the synchronous planner from mutating this provider through a closure.
            with self._planner_boundary():
                # Invoke the caller planner once while the complete transaction owns resources.
                plan = planner(snapshot_before)
            # Require the exact immutable plan result type.
            if type(plan) is not GameActionPlan:
                # Reject plan-like objects before any committed projection.
                raise ValidationError("Game action planner returned an invalid plan")
            # Compute and validate the exact deterministic committed snapshot.
            snapshot_after = apply_plan_to_snapshot(snapshot_before, plan)
            # Construct the complete immutable receipt before any DML projection.
            receipt = GameActionReceipt(identity=identity, resources=resources, snapshot_before=snapshot_before, plan=plan, snapshot_after=snapshot_after)
            # Publish exact final wallet balances under the retained row locks.
            for wallet_id, balance_cents in receipt.snapshot_after.wallet_balances:
                # Update only the declared wallet row with exact decimal cents.
                cursor.execute("UPDATE casino_players SET balance = %s, updated_at = %s WHERE player_id = %s", (Decimal(balance_cents) / Decimal(100), utc_now(), wallet_id))
                # Require the locked wallet row to remain uniquely present.
                if cursor.rowcount != 1:
                    # Fail the complete transaction closed.
                    raise ConflictError("Game action wallet state requires operator recovery")
            # Append every movement ledger row inside the same transaction.
            self._insert_mysql_game_action_ledger(cursor, receipt)
            # Publish exact final state documents under their retained row locks.
            for state_key, state_value in receipt.snapshot_after.state_values:
                # Replace only one declared state row with canonical JSON.
                cursor.execute("UPDATE casino_documents SET payload_json = %s, updated_at = %s WHERE document_key = %s", (canonical_json_bytes(self._plain_canonical(state_value)).decode("utf-8"), utc_now(), state_key))
                # Require the locked state row to remain uniquely present.
                if cursor.rowcount != 1:
                    # Fail the complete transaction closed.
                    raise ConflictError("Game action state requires operator recovery")
            # Serialize exact receipt and resource bytes for immutable storage.
            resources_json = canonical_json_bytes(self._serialize_game_action_resources(resources)).decode("utf-8")
            # Serialize the complete receipt through the same legacy-compatible codec.
            receipt_json = canonical_json_bytes(self._serialize_game_action_receipt(receipt)).decode("utf-8")
            # Hash the exact receipt bytes stored in the binary-collated column.
            receipt_sha256 = hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
            # Insert the immutable receipt as the final transaction row.
            cursor.execute(
                "INSERT INTO casino_game_action_receipts (reset_epoch, game_id, player_id, action_key, request_fingerprint, resources_json, receipt_json, receipt_sha256, claim_disposition) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'execute')",
                (reset_epoch, *identity.scope_key, identity.request_fingerprint, resources_json, receipt_json, receipt_sha256),
            )
            # Commit claim, wallets, ledger, state, and receipt atomically.
            connection.commit()
            # Return the newly committed immutable receipt.
            return receipt, False
        # Roll back every provider, planner, validation, or database failure.
        except Exception:
            # Discard all uncommitted lifecycle and resource changes.
            connection.rollback()
            # Preserve the original bounded error for callers and tests.
            raise
        finally:
            # Release the transaction connection after commit or rollback.
            connection.close()

    # Resolve one schema-four MySQL action without invoking its planner.
    def resolve_game_action(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
    ) -> GameActionResolution:
        # Validate exact provider-neutral types before any connection or lock attempt.
        validate_resolution_request(identity=identity, resources=resources)
        # Reject lifecycle mutation from inside an active planner on this provider.
        self._reject_planner_mutation()
        # Return finite pending before pool checkout during same-process reset bootstrap.
        if self._reset_is_active():
            # Preserve claim-zero and bounded capacity-one behavior.
            return GameActionResolution(status="pending")
        # Preserve ordinary compatible runtime readiness behavior.
        self.ensure_ready()
        # Open one connection for the finite resolver transaction.
        connection = self.connect()
        # Retain the original session lock-wait policy for pooled-connection restoration.
        original_lock_wait = None
        # Retain the cursor so finally can restore session state after commit or rollback.
        cursor = None
        try:
            # Open a dictionary cursor before the transaction to inspect session policy.
            cursor = connection.cursor(dictionary=True)
            # Read the current pooled-session lock-wait value without exposing it publicly.
            cursor.execute("SELECT @@SESSION.innodb_lock_wait_timeout AS lock_wait")
            # Retain the exact bounded integer for later restoration.
            original_lock_wait = int(cursor.fetchone()["lock_wait"])
            # Bound only this leased session before beginning the resolver transaction.
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 1")
            # End any implicit connector transaction opened by session preflight reads.
            connection.rollback()
            # Start one transaction whose insert races the execute claim.
            connection.start_transaction()
            # Require exact clean schema four inside the bounded resolver transaction.
            self._require_game_action_schema(connection)
            # Hold shared epoch ownership before any immutable lifecycle lookup or insert.
            epoch_state = self._mysql_game_action_epoch(cursor)
            # Treat reset bootstrap as finite pending without a claim.
            if epoch_state["phase"] != "ready":
                # End the read-only transaction before returning no outcome.
                connection.commit()
                # Preserve claim-zero and planner-zero reset behavior.
                return GameActionResolution(status="pending")
            # Capture the exact ready namespace for resolver competition.
            reset_epoch = epoch_state["current_epoch"]
            # Insert or serialize behind the exact lifecycle claim.
            disposition, _inserted = self._claim_mysql_game_action(cursor, identity, resources, "uncommitted", reset_epoch)
            # Return the durable resolver-owned tombstone when it won first.
            if disposition == "uncommitted":
                # Commit the immutable no-result claim.
                connection.commit()
                # Return the terminal provider-neutral state.
                return GameActionResolution(status="uncommitted")
            # Read the execute owner's immutable receipt after its claim lock releases.
            receipt = self._select_mysql_game_action_receipt(cursor, identity, reset_epoch)
            # Refuse an execute claim that became visible without its atomic receipt.
            if receipt is None:
                # Preserve the orphaned claim for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Reject changed compatible fields before returning outcome data.
            if receipt.identity != identity or receipt.resources != resources:
                # Preserve immutable execute history.
                raise ConflictError("Game action key conflicts with committed semantics")
            # Commit the read-only resolution transaction.
            connection.commit()
            # Return the complete immutable committed result.
            return GameActionResolution(status="committed", receipt=receipt)
        # Convert only MySQL lock wait/deadlock errors into a finite pending state.
        except Exception as exc:
            # Read the connector's numeric server error without importing provider classes.
            error_number = getattr(exc, "errno", None)
            # Release all statement and row locks from the timed-out resolver.
            connection.rollback()
            # Report active ownership for bounded lock wait or deadlock selection.
            if error_number in {1205, 1213}:
                # Return no partial receipt while execution remains uncertain.
                return GameActionResolution(status="pending")
            # Preserve every other provider or semantic failure.
            raise
        finally:
            try:
                # Restore the pooled session policy after the transaction has ended.
                if cursor is not None and original_lock_wait is not None:
                    # Reapply only the trusted integer read from this same session.
                    cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", (original_lock_wait,))
            finally:
                # Always return or discard the lease even when session restoration fails.
                connection.close()
