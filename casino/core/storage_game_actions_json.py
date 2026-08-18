# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""JSON game-action serialization, recovery, execution, and resolution lifecycle."""

# Import hashing so ledger movements receive stable scope-derived identifiers.
import hashlib
# Import decimal arithmetic so wallet values remain exact integer cents.
from decimal import Decimal
# Import callable and value typing for the provider-neutral planner boundary.
from typing import Any, Callable

# Import the durable document schema used by JSON wallet snapshots.
from casino.config import SCHEMA_VERSION
# Import the canonical clock for wallet and ledger projections.
from casino.core.clock import utc_now
# Import provider-neutral action values and validation helpers.
from casino.core.game_action import GameActionIdentity, GameActionMovement, GameActionPlan, GameActionReceipt, GameActionResolution, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, validate_execution_request, validate_resolution_request
# Import the provider-neutral codecs shared by JSON and MySQL lifecycle storage.
from casino.core.storage_game_action_codecs import GameActionCodecMixin
# Import the private epoch constants shared with reset lifecycle storage.
from casino.core.storage_reset import _GAME_ACTION_EPOCH_STORAGE_VERSION, _GAME_ACTION_MAX_EPOCH, _GAME_ACTION_STORAGE_VERSION
# Import fixed API error boundaries used by action validation and recovery.
from casino.errors import ConflictError, NotFoundError, ValidationError

# Enumerate the only durable recovery stages accepted from the private journal.
_GAME_ACTION_STAGES = {"prepared", "planned", "wallet_applied", "ledger_applied", "state_applied", "receipt_committed"}


# Own the JSON game-action lifecycle while ordinary provider I/O remains in storage.py.
class JsonGameActionMixin(GameActionCodecMixin):
    # Serialize one exact bounded resource declaration.
    def _serialize_game_action_resources(self, resources: GameActionResources) -> dict:
        # Return the two canonical resource arrays.
        return {
            # Preserve the sorted state resource keys.
            "state_keys": list(resources.state_keys),
            # Preserve the sorted wallet resource identities.
            "wallet_ids": list(resources.wallet_ids),
        }

    # Reconstruct one exact bounded resource declaration.
    def _deserialize_game_action_resources(self, value: Any) -> GameActionResources:
        # Require the exact durable resource field set.
        if type(value) is not dict or set(value) != {"state_keys", "wallet_ids"}:
            # Reject malformed durable resource state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require ordinary JSON arrays before tuple construction.
        if type(value["state_keys"]) is not list or type(value["wallet_ids"]) is not list:
            # Reject coercible or object-shaped resource collections.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reconstruct through the contract's order, identity, and size checks.
            return GameActionResources(wallet_ids=tuple(value["wallet_ids"]), state_keys=tuple(value["state_keys"]))
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one immutable snapshot without leaking provider file layout.
    def _serialize_game_action_snapshot(self, snapshot: GameActionSnapshot) -> dict:
        # Return only canonical wallet and state resource values.
        return {
            # Preserve exact ordered state pairs with plain canonical values.
            "state_values": [[key, self._plain_canonical(value)] for key, value in snapshot.state_values],
            # Preserve exact ordered integer-cent wallet pairs.
            "wallet_balances": [[wallet_id, balance] for wallet_id, balance in snapshot.wallet_balances],
        }

    # Reconstruct one immutable snapshot against an already validated resource set.
    def _deserialize_game_action_snapshot(self, value: Any, resources: GameActionResources) -> GameActionSnapshot:
        # Require the exact durable snapshot field set.
        if type(value) is not dict or set(value) != {"state_values", "wallet_balances"}:
            # Reject malformed durable snapshot state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require ordinary JSON arrays for ordered pairs.
        if type(value["state_values"]) is not list or type(value["wallet_balances"]) is not list:
            # Reject coercible or object-shaped snapshot collections.
            raise ConflictError("Game action storage requires operator recovery")
        # Require exact two-item wallet pairs before dictionary construction.
        if any(type(entry) is not list or len(entry) != 2 for entry in value["wallet_balances"]):
            # Prevent malformed or duplicate-hiding wallet snapshots.
            raise ConflictError("Game action storage requires operator recovery")
        # Require exact two-item state pairs before dictionary construction.
        if any(type(entry) is not list or len(entry) != 2 for entry in value["state_values"]):
            # Prevent malformed or duplicate-hiding state snapshots.
            raise ConflictError("Game action storage requires operator recovery")
        # Read ordered wallet identities before converting to a mapping.
        wallet_ids = tuple(entry[0] for entry in value["wallet_balances"])
        # Read ordered state identities before converting to a mapping.
        state_keys = tuple(entry[0] for entry in value["state_values"])
        # Require exact declared coverage so duplicates cannot disappear in dictionaries.
        if wallet_ids != resources.wallet_ids or state_keys != resources.state_keys:
            # Reject missing, duplicate, reordered, or undeclared durable values.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reconstruct through the contract's canonical snapshot freezer.
            return GameActionSnapshot.create(
                # Bind the exact durable resources.
                resources=resources,
                # Restore exact integer-cent wallet values.
                wallet_balances={entry[0]: entry[1] for entry in value["wallet_balances"]},
                # Restore and refreeze canonical state values.
                state_values={entry[0]: entry[1] for entry in value["state_values"]},
            )
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one immutable validated game-action plan.
    def _serialize_game_action_plan(self, plan: GameActionPlan) -> dict:
        # Return only the canonical outcome and declared writes.
        return {
            # Preserve exact signed integer-cent movements in planner order.
            "movements": [
                {
                    # Preserve the exact movement delta.
                    "amount_cents": movement.amount_cents,
                    # Preserve the bounded provider-neutral reason.
                    "reason": movement.reason,
                    # Preserve the declared wallet identity.
                    "wallet_id": movement.wallet_id,
                }
                for movement in plan.movements
            ],
            # Preserve the complete immutable outcome as ordinary canonical JSON.
            "outcome": self._plain_canonical(plan.outcome),
            # Preserve exact sorted state replacements.
            "state_updates": [[key, self._plain_canonical(value)] for key, value in plan.state_updates],
        }

    # Reconstruct one immutable game-action plan from private durable JSON.
    def _deserialize_game_action_plan(self, value: Any) -> GameActionPlan:
        # Require the exact durable plan field set.
        if type(value) is not dict or set(value) != {"movements", "outcome", "state_updates"}:
            # Reject malformed durable plan state.
            raise ConflictError("Game action storage requires operator recovery")
        # Require ordinary JSON arrays for movements and state updates.
        if type(value["movements"]) is not list or type(value["state_updates"]) is not list:
            # Reject coercible or object-shaped plan collections.
            raise ConflictError("Game action storage requires operator recovery")
        # Require exact two-item state pairs before dictionary construction.
        if any(type(entry) is not list or len(entry) != 2 for entry in value["state_updates"]):
            # Prevent malformed or duplicate-hiding state updates.
            raise ConflictError("Game action storage requires operator recovery")
        # Extract state keys for canonical order and duplicate proof.
        update_keys = tuple(entry[0] for entry in value["state_updates"])
        # Require exact string keys in canonical sorted unique order.
        if any(type(key) is not str for key in update_keys) or update_keys != tuple(sorted(set(update_keys))):
            # Reject ambiguous durable state-update identity.
            raise ConflictError("Game action storage requires operator recovery")
        # Build validated movement contract objects.
        movements = []
        # Inspect every durable movement before plan construction.
        for movement in value["movements"]:
            # Require the exact movement field set.
            if type(movement) is not dict or set(movement) != {"amount_cents", "reason", "wallet_id"}:
                # Reject malformed durable movement state.
                raise ConflictError("Game action storage requires operator recovery")
            try:
                # Reconstruct through exact identity and integer-cent checks.
                movements.append(GameActionMovement(wallet_id=movement["wallet_id"], amount_cents=movement["amount_cents"], reason=movement["reason"]))
            # Normalize contract validation without exposing corrupt values.
            except ValidationError:
                # Preserve the original durable bytes for operator repair.
                raise ConflictError("Game action storage requires operator recovery") from None
        try:
            # Reconstruct the complete immutable plan through the canonical freezer.
            return GameActionPlan.create(
                # Restore the complete outcome.
                outcome=value["outcome"],
                # Restore exact movement order.
                movements=movements,
                # Restore exact canonical state replacements.
                state_updates={entry[0]: entry[1] for entry in value["state_updates"]},
            )
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Serialize one immutable committed receipt.
    def _serialize_game_action_receipt(self, receipt: GameActionReceipt) -> dict:
        # Return the complete provider-neutral receipt graph.
        return {
            # Preserve the exact action identity.
            "identity": self._serialize_game_action_identity(receipt.identity),
            # Preserve the exact immutable plan.
            "plan": self._serialize_game_action_plan(receipt.plan),
            # Preserve the complete bounded resource set.
            "resources": self._serialize_game_action_resources(receipt.resources),
            # Preserve the immutable planner snapshot.
            "snapshot_before": self._serialize_game_action_snapshot(receipt.snapshot_before),
            # Preserve the exact committed projection.
            "snapshot_after": self._serialize_game_action_snapshot(receipt.snapshot_after),
        }

    # Reconstruct and self-validate one immutable committed receipt.
    def _deserialize_game_action_receipt(self, value: Any) -> GameActionReceipt:
        # Require the exact durable receipt field set.
        if type(value) is not dict or set(value) != {"identity", "plan", "resources", "snapshot_after", "snapshot_before"}:
            # Reject malformed durable receipt state.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct the exact durable identity first.
        identity = self._deserialize_game_action_identity(value["identity"])
        # Reconstruct the complete bounded resource declaration.
        resources = self._deserialize_game_action_resources(value["resources"])
        # Reconstruct the immutable planner input.
        snapshot_before = self._deserialize_game_action_snapshot(value["snapshot_before"], resources)
        # Reconstruct the immutable validated plan.
        plan = self._deserialize_game_action_plan(value["plan"])
        # Reconstruct the immutable committed projection.
        snapshot_after = self._deserialize_game_action_snapshot(value["snapshot_after"], resources)
        try:
            # Revalidate pure projection consistency through the contract receipt.
            return GameActionReceipt(identity=identity, resources=resources, snapshot_before=snapshot_before, plan=plan, snapshot_after=snapshot_after)
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None

    # Return the implicit legacy epoch state used before the first successful reset.
    def _empty_game_action_epoch(self) -> dict:
        # Preserve existing epoch-one lifecycle files without an eager rewrite.
        return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "current_epoch": 1, "phase": "ready"}

    # Read and validate the provider-private reset epoch state.
    def _read_game_action_epoch(self) -> dict:
        # Decode the epoch control file or project the compatible legacy epoch-one default.
        state = self._read_game_action_json(self.game_action_epoch_path(), self._empty_game_action_epoch)
        # Require the exact finite singleton state shape.
        if type(state) is not dict or set(state) != {"current_epoch", "phase", "schema_version"}:
            # Preserve malformed control bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the exact private epoch-state schema version.
        if type(state["schema_version"]) is not int or state["schema_version"] != _GAME_ACTION_STORAGE_VERSION:
            # Reject unknown durable epoch semantics.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one bounded non-coercible current epoch.
        if type(state["current_epoch"]) is not int or not 1 <= state["current_epoch"] <= _GAME_ACTION_MAX_EPOCH:
            # Refuse missing, boolean, zero, negative, or overflowing epochs.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one finite reset readiness phase.
        if type(state["phase"]) is not str or state["phase"] not in {"ready", "resetting"}:
            # Reject unknown lifecycle visibility states.
            raise ConflictError("Game action storage requires operator recovery")
        # Return a detached plain state for caller-owned phase transitions.
        return dict(state)

    # Publish one exact provider-private reset epoch state atomically.
    def _write_game_action_epoch(self, *, current_epoch: int, phase: str) -> None:
        # Validate the epoch before writing any control bytes.
        if type(current_epoch) is not int or not 1 <= current_epoch <= _GAME_ACTION_MAX_EPOCH:
            # Fail closed rather than wrapping a durable namespace.
            raise ConflictError("Game action storage requires operator recovery")
        # Accept only the two reviewed visibility phases.
        if phase not in {"ready", "resetting"}:
            # Reject internal phase drift before publication.
            raise ConflictError("Game action storage requires operator recovery")
        # Atomically persist the complete bounded control document.
        self._write_game_action_json(
            self.game_action_epoch_path(),
            {"schema_version": _GAME_ACTION_STORAGE_VERSION, "current_epoch": current_epoch, "phase": phase},
        )

    # Require the current JSON lifecycle namespace to be available for actions.
    def _ready_game_action_epoch(self) -> int:
        # Read the exact durable singleton state under the caller's global gate.
        state = self._read_game_action_epoch()
        # Refuse action visibility during an incomplete reset.
        if state["phase"] != "ready":
            # Preserve reset-owned state without creating a claim.
            raise ConflictError("Game action reset is in progress")
        # Return the bounded current namespace.
        return state["current_epoch"]

    # Return the empty private receipt registry shape for one current epoch.
    def _empty_game_action_receipts(self, reset_epoch: int = 1) -> dict:
        # Preserve the exact legacy container only for the implicit first epoch.
        if reset_epoch == 1:
            # Retain backwards-compatible receipt bytes before any reset.
            return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "receipts": {}}
        # Use the epoch-scoped registry after the first successful reset.
        return {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "receipts_by_epoch": {str(reset_epoch): {}}}

    # Read and fully validate the immutable receipt registry.
    def _read_game_action_receipts(self, reset_epoch: int = 1) -> tuple[dict, dict[str, GameActionReceipt]]:
        # Strictly decode the registry without repairing corrupt bytes.
        registry = self._read_game_action_json(self.game_action_receipts_path(), lambda: self._empty_game_action_receipts(reset_epoch))
        # Recognize the exact legacy epoch-one registry without rewriting it.
        if type(registry) is dict and set(registry) == {"receipts", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_STORAGE_VERSION:
            # Reject legacy bytes after the durable namespace has advanced.
            if reset_epoch != 1 or type(registry["receipts"]) is not dict:
                # Preserve incompatible durable rows for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Read the sole legacy epoch-one receipt mapping.
            receipt_records = registry["receipts"]
            # Validate the complete one-epoch retained registry below.
            retained_receipt_records = ((1, receipt_records),)
        # Recognize only the reviewed epoch-scoped registry shape.
        elif type(registry) is dict and set(registry) == {"receipts_by_epoch", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_EPOCH_STORAGE_VERSION:
            # Require an ordinary epoch mapping.
            if type(registry["receipts_by_epoch"]) is not dict:
                # Reject arrays, scalars, or unknown containers.
                raise ConflictError("Game action storage requires operator recovery")
            # Validate every retained epoch key and nested mapping before current lookup.
            for epoch_key, records in registry["receipts_by_epoch"].items():
                # Accept only canonical positive decimal epochs no newer than current state.
                if type(epoch_key) is not str or not epoch_key.isdigit() or str(int(epoch_key)) != epoch_key or not 1 <= int(epoch_key) <= reset_epoch or type(records) is not dict:
                    # Preserve malformed or future lifecycle history unchanged.
                    raise ConflictError("Game action storage requires operator recovery")
            # Read only the current epoch while retaining older immutable rows.
            receipt_records = registry["receipts_by_epoch"].get(str(reset_epoch), {})
            # Validate every retained epoch so corruption cannot hide outside current lookup.
            retained_receipt_records = tuple((int(epoch_key), records) for epoch_key, records in registry["receipts_by_epoch"].items())
        # Reject every unknown durable registry version or field set.
        else:
            # Preserve malformed bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct every receipt so unrelated corrupt entries cannot remain hidden.
        receipts = {}
        # Inspect every retained epoch and its durable receipt pairs.
        for retained_epoch, records in retained_receipt_records:
            # Validate each complete immutable row in this epoch.
            for scope_key, record in records.items():
                # Require an exact string registry key.
                if type(scope_key) is not str:
                    # Reject coercible or ambiguous scope identities.
                    raise ConflictError("Game action storage requires operator recovery")
                # Reconstruct and self-validate the complete immutable receipt.
                receipt = self._deserialize_game_action_receipt(record)
                # Require the registry key to match the receipt identity exactly.
                if scope_key != self._game_action_scope_key(receipt.identity):
                    # Reject misplaced or shadowed committed identities.
                    raise ConflictError("Game action storage requires operator recovery")
                # Retain only the caller's current namespace for public lookup.
                if retained_epoch == reset_epoch:
                    # Expose this validated current-epoch receipt.
                    receipts[scope_key] = receipt
        # Return both the writable plain registry and immutable validated view.
        return registry, receipts

    # Return the empty append-only lifecycle claim registry shape for one epoch.
    def _empty_game_action_claims(self, reset_epoch: int = 1) -> dict:
        # Preserve the exact legacy container only in epoch one.
        if reset_epoch == 1:
            # Retain backwards-compatible claim bytes before any reset.
            return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "claims": {}}
        # Use the epoch-scoped container after reset advances the namespace.
        return {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "claims_by_epoch": {str(reset_epoch): {}}}

    # Read and fully validate immutable execution and cancellation claims.
    def _read_game_action_claims(self, reset_epoch: int = 1) -> tuple[dict, dict[str, dict]]:
        # Strictly decode the registry so malformed bytes remain available for operator recovery.
        registry = self._read_game_action_json(self.game_action_claims_path(), lambda: self._empty_game_action_claims(reset_epoch))
        # Recognize the exact legacy epoch-one registry without rewriting it.
        if type(registry) is dict and set(registry) == {"claims", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_STORAGE_VERSION:
            # Reject legacy claims outside their only valid epoch.
            if reset_epoch != 1 or type(registry["claims"]) is not dict:
                # Preserve incompatible durable rows for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Read the sole legacy epoch-one claim mapping.
            claim_records = registry["claims"]
            # Validate the complete one-epoch retained registry below.
            retained_claim_records = ((1, claim_records),)
        # Recognize only the reviewed epoch-scoped registry shape.
        elif type(registry) is dict and set(registry) == {"claims_by_epoch", "schema_version"} and registry.get("schema_version") == _GAME_ACTION_EPOCH_STORAGE_VERSION:
            # Require one ordinary retained-epoch mapping.
            if type(registry["claims_by_epoch"]) is not dict:
                # Reject arrays, scalars, or unknown containers.
                raise ConflictError("Game action storage requires operator recovery")
            # Validate every retained epoch before current lookup.
            for epoch_key, records in registry["claims_by_epoch"].items():
                # Accept only canonical positive decimal epochs no newer than current state.
                if type(epoch_key) is not str or not epoch_key.isdigit() or str(int(epoch_key)) != epoch_key or not 1 <= int(epoch_key) <= reset_epoch or type(records) is not dict:
                    # Preserve malformed or future lifecycle history unchanged.
                    raise ConflictError("Game action storage requires operator recovery")
            # Read only the current epoch while retaining earlier immutable tombstones.
            claim_records = registry["claims_by_epoch"].get(str(reset_epoch), {})
            # Validate every retained epoch so hidden corruption remains fail closed.
            retained_claim_records = tuple((int(epoch_key), records) for epoch_key, records in registry["claims_by_epoch"].items())
        # Reject unknown registry versions and shapes.
        else:
            # Preserve malformed bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct every row before allowing any claim lookup.
        claims = {}
        # Validate every retained epoch and its opaque immutable claim rows.
        for retained_epoch, records in retained_claim_records:
            # Inspect every exact scope and record in this epoch.
            for scope_key, record in records.items():
                # Require exact claim fields with a finite disposition.
                if type(scope_key) is not str or type(record) is not dict or set(record) != {"disposition", "identity", "resources"} or record.get("disposition") not in {"execute", "uncommitted"}:
                    # Preserve malformed claim bytes unchanged.
                    raise ConflictError("Game action storage requires operator recovery")
                # Reconstruct identity and resources through the provider-neutral contract.
                identity = self._deserialize_game_action_identity(record["identity"])
                # Reconstruct the canonical declared resource set.
                resources = self._deserialize_game_action_resources(record["resources"])
                # Require the registry key to match its exact three-part identity.
                if scope_key != self._game_action_scope_key(identity):
                    # Reject misplaced or shadowed lifecycle claims.
                    raise ConflictError("Game action storage requires operator recovery")
                # Retain only the caller's current namespace for lifecycle lookup.
                if retained_epoch == reset_epoch:
                    # Expose validated contract objects and the finite disposition.
                    claims[scope_key] = {"identity": identity, "resources": resources, "disposition": record["disposition"]}
        # Return the writable plain registry and validated immutable-semantics view.
        return registry, claims

    # Insert one immutable JSON lifecycle claim or verify exact compatible replay.
    def _commit_game_action_claim(self, identity: GameActionIdentity, resources: GameActionResources, disposition: str, reset_epoch: int = 1) -> str:
        # Require provider-owned finite disposition selection.
        if disposition not in {"execute", "uncommitted"}:
            # Treat internal misuse as fixed storage corruption risk.
            raise ConflictError("Game action storage is invalid")
        # Read and validate all existing claims before appending a new row.
        registry, claims = self._read_game_action_claims(reset_epoch)
        # Derive the unambiguous durable scope key.
        scope_key = self._game_action_scope_key(identity)
        # Inspect prior immutable ownership when another executor or resolver won.
        existing = claims.get(scope_key)
        # Reject changed fingerprint, resources, or disposition without rewriting the winner.
        if existing is not None:
            # Preserve exact semantic conflicts before planner or resource access.
            if existing["identity"] != identity or existing["resources"] != resources:
                # Keep the immutable winning row unchanged.
                raise ConflictError("Game action key conflicts with durable semantics")
            # Report the immutable winning disposition without changing it.
            return existing["disposition"]
        # Append the exact immutable row under its canonical scope.
        # Select the exact current-epoch mutable mapping without exposing older rows.
        claim_records = registry["claims"] if registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION else registry["claims_by_epoch"].setdefault(str(reset_epoch), {})
        # Append only inside the captured reset epoch.
        claim_records[scope_key] = {
            # Preserve the finite lifecycle winner.
            "disposition": disposition,
            # Preserve canonical identity and fingerprint fields.
            "identity": self._serialize_game_action_identity(identity),
            # Preserve canonical declared resources.
            "resources": self._serialize_game_action_resources(resources),
        }
        # Atomically publish the complete append-only registry under the global gate.
        self._write_game_action_json(self.game_action_claims_path(), registry)
        # Report that this caller inserted the selected winning disposition.
        return disposition

    # Return the empty provider-private action state registry shape.
    def _empty_game_action_states(self) -> dict:
        # Version the registry and retain route-free state resources by canonical key.
        return {"schema_version": _GAME_ACTION_STORAGE_VERSION, "states": {}}

    # Read and validate every provider-private action state value.
    def _read_game_action_states(self) -> dict:
        # Strictly decode the registry without repairing corrupt bytes.
        registry = self._read_game_action_json(self.game_action_states_path(), self._empty_game_action_states)
        # Require the exact versioned registry shape.
        if type(registry) is not dict or set(registry) != {"schema_version", "states"}:
            # Reject unknown durable fields or container types.
            raise ConflictError("Game action storage requires operator recovery")
        # Require the exact non-coercible storage version.
        if type(registry["schema_version"]) is not int or registry["schema_version"] != _GAME_ACTION_STORAGE_VERSION:
            # Reject unknown durable schema behavior.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one ordinary mapping of bounded canonical values.
        if type(registry["states"]) is not dict:
            # Reject arrays, scalars, or custom durable state shapes.
            raise ConflictError("Game action storage requires operator recovery")
        # Validate every key and value through a bounded one-state snapshot freezer.
        for state_key, state_value in registry["states"].items():
            # Require an exact portable resource key already admitted by the contract.
            try:
                # Build a one-resource declaration to validate the durable key.
                resources = GameActionResources(state_keys=(state_key,))
                # Freeze and bound the durable value through the snapshot contract.
                GameActionSnapshot.create(resources=resources, wallet_balances={}, state_values={state_key: state_value})
            # Normalize contract validation without exposing corrupt values.
            except ValidationError:
                # Preserve the original durable bytes for operator repair.
                raise ConflictError("Game action storage requires operator recovery") from None
        # Return the validated writable registry.
        return registry

    # Convert one compatible JSON wallet balance to exact integer cents.
    def _json_wallet_cents(self, value: Any) -> int:
        # Accept only the exact numeric JSON types used by existing player documents.
        if type(value) not in {int, float}:
            # Reject booleans, strings, and custom numeric objects.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Convert through decimal text so existing two-decimal JSON values remain exact.
            decimal_value = Decimal(str(value))
            # Multiply by the fixed fake-money precision.
            scaled = decimal_value * 100
        # Normalize invalid and non-finite numeric states.
        except Exception:
            # Preserve the original players document for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Require a finite exact cent value without rounding.
        if not scaled.is_finite() or scaled != scaled.to_integral_value():
            # Reject hidden sub-cent or non-finite wallet state.
            raise ConflictError("Game action wallet state requires operator recovery")
        try:
            # Convert the exact integral decimal into a contract integer.
            balance_cents = int(scaled)
            # Reuse snapshot validation for range and nonnegative checks.
            GameActionSnapshot.create(resources=GameActionResources(wallet_ids=("wallet",)), wallet_balances={"wallet": balance_cents}, state_values={})
        # Normalize contract validation without exposing the value.
        except (ValueError, OverflowError, ValidationError):
            # Preserve the original players document for operator recovery.
            raise ConflictError("Game action wallet state requires operator recovery") from None
        # Return the exact integer-cent balance.
        return balance_cents

    # Convert exact integer cents back to a compatible JSON numeric balance.
    def _json_wallet_value(self, cents: int) -> int | float:
        # Preserve whole-token values as exact JSON integers at every supported magnitude.
        if cents % 100 == 0:
            # Return the exact whole-token integer without binary conversion.
            return cents // 100
        # Convert ordinary fractional balances through the shipped numeric shape.
        candidate = cents / 100
        # Require the compatible JSON number to round-trip to the exact cents.
        if self._json_wallet_cents(candidate) != cents:
            # Reject a projection that current JSON numeric storage cannot represent exactly.
            raise ValidationError("Game action resulting wallet is not JSON-cent exact")
        # Return the verified compatible fractional JSON number.
        return candidate

    # Read the players document strictly for an action-owned wallet snapshot.
    def _read_game_action_players(self) -> dict:
        # Reuse the forensic wallet reader so every action sees the same fail-closed state.
        return self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})

    # Capture one immutable snapshot after durable-key lookup and recovery.
    def _capture_game_action_snapshot(self, resources: GameActionResources) -> GameActionSnapshot:
        # Load the current wallet document strictly under the global gate.
        players = self._read_game_action_players()
        # Build exact integer-cent balances for the declared wallets only.
        wallet_balances = {}
        # Resolve every bounded declared wallet.
        for wallet_id in resources.wallet_ids:
            # Find all exact player rows so duplicate durable identities fail closed.
            matches = [row for row in players["players"] if type(row) is dict and row.get("player_id") == wallet_id]
            # Reject a missing wallet through the established public error shape.
            if not matches:
                # Surface the same not-found boundary as ordinary wallet operations.
                raise NotFoundError(f"Player {wallet_id} was not found")
            # Reject duplicate durable wallet identities.
            if len(matches) != 1:
                # Preserve the ambiguous players document for operator recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Convert the compatible balance to exact integer cents.
            wallet_balances[wallet_id] = self._json_wallet_cents(matches[0].get("balance", 0))
        # Load the provider-private route-free game-state registry.
        state_registry = self._read_game_action_states()
        # Snapshot absent state resources as empty canonical objects.
        state_values = {state_key: state_registry["states"].get(state_key, {}) for state_key in resources.state_keys}
        # Freeze and validate the complete bounded provider snapshot.
        return GameActionSnapshot.create(resources=resources, wallet_balances=wallet_balances, state_values=state_values)

    # Build the fixed durable journal envelope for one stage.
    def _game_action_journal_record(
        self,
        *,
        stage: str,
        identity: GameActionIdentity,
        resources: GameActionResources,
        snapshot_before: GameActionSnapshot,
        receipt: GameActionReceipt | None,
        reset_epoch: int,
    ) -> dict:
        # Return the exact versioned durable recovery fields.
        return {
            # Preserve the action identity reserved before planning.
            "identity": self._serialize_game_action_identity(identity),
            # Preserve the receipt only after a plan is durable.
            "receipt": None if receipt is None else self._serialize_game_action_receipt(receipt),
            # Preserve the complete declared resources.
            "resources": self._serialize_game_action_resources(resources),
            # Bind recovery to the exact reset namespace that created the action.
            "reset_epoch": reset_epoch,
            # Version the epoch-bound private journal format.
            "schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION,
            # Preserve the planner input even before an outcome exists.
            "snapshot_before": self._serialize_game_action_snapshot(snapshot_before),
            # Record the exact recoverable stage.
            "stage": stage,
        }

    # Read and validate the private action journal without modifying its bytes.
    def _read_game_action_journal(self) -> dict | None:
        # Return no journal when the private path is genuinely absent.
        if not self.game_action_journal_path().exists():
            # Report a clean recovery boundary.
            return None
        # Strictly decode the existing journal.
        record = self._read_game_action_json(self.game_action_journal_path(), dict)
        # Resolve the exact current reset namespace before accepting recovery bytes.
        current_epoch = self._read_game_action_epoch()["current_epoch"]
        # Accept only the shipped legacy journal shape in epoch one.
        if type(record) is dict and set(record) == {"identity", "receipt", "resources", "schema_version", "snapshot_before", "stage"} and record.get("schema_version") == _GAME_ACTION_STORAGE_VERSION:
            # Reject a legacy journal after reset has advanced the namespace.
            if current_epoch != 1:
                # Preserve stale recovery bytes for operator inspection.
                raise ConflictError("Game action storage requires operator recovery")
            # Project the compatible implicit legacy epoch.
            reset_epoch = 1
        # Accept the exact epoch-bound journal format only for the current namespace.
        elif type(record) is dict and set(record) == {"identity", "receipt", "reset_epoch", "resources", "schema_version", "snapshot_before", "stage"} and record.get("schema_version") == _GAME_ACTION_EPOCH_STORAGE_VERSION:
            # Require one exact current bounded epoch.
            if type(record["reset_epoch"]) is not int or record["reset_epoch"] != current_epoch:
                # Refuse cross-reset recovery into current mutable state.
                raise ConflictError("Game action storage requires operator recovery")
            # Retain the validated epoch for reconstructed state.
            reset_epoch = record["reset_epoch"]
        # Reject every truncated, future, or unknown journal shape.
        else:
            # Preserve unknown durable journal bytes.
            raise ConflictError("Game action storage requires operator recovery")
        # Require one exact known stage string.
        if type(record["stage"]) is not str or record["stage"] not in _GAME_ACTION_STAGES:
            # Reject unknown recovery behavior without changing bytes.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct identity and resources before accepting any stage.
        identity = self._deserialize_game_action_identity(record["identity"])
        # Reconstruct the exact bounded resource set.
        resources = self._deserialize_game_action_resources(record["resources"])
        # Reconstruct the planner snapshot against the declared resources.
        snapshot_before = self._deserialize_game_action_snapshot(record["snapshot_before"], resources)
        # Require prepared state to contain no outcome receipt.
        if record["stage"] == "prepared":
            # Reject a receipt hidden in a supposedly pre-planner journal.
            if record["receipt"] is not None:
                # Preserve the ambiguous journal for operator recovery.
                raise ConflictError("Game action storage requires operator recovery")
            # Return the validated reconstructed prepared record.
            return {"identity": identity, "receipt": None, "reset_epoch": reset_epoch, "resources": resources, "snapshot_before": snapshot_before, "stage": record["stage"]}
        # Require every post-planner stage to contain one exact receipt.
        if record["receipt"] is None:
            # Reject a recovery stage without its immutable outcome.
            raise ConflictError("Game action storage requires operator recovery")
        # Reconstruct and validate the complete immutable receipt.
        receipt = self._deserialize_game_action_receipt(record["receipt"])
        # Require the receipt to match every duplicated journal identity field.
        if receipt.identity != identity or receipt.resources != resources or receipt.snapshot_before != snapshot_before:
            # Reject internally divergent durable recovery state.
            raise ConflictError("Game action storage requires operator recovery")
        # Return the validated reconstructed journal record.
        return {"identity": identity, "receipt": receipt, "reset_epoch": reset_epoch, "resources": resources, "snapshot_before": snapshot_before, "stage": record["stage"]}

    # Persist one reconstructed journal at a new recovery stage.
    def _write_game_action_journal_stage(self, record: dict, stage: str) -> None:
        # Require a reviewed stage chosen by provider code.
        if stage not in _GAME_ACTION_STAGES:
            # Treat internal misuse as a fixed provider-integrity failure.
            raise ConflictError("Game action storage is invalid")
        # Publish the complete immutable recovery envelope atomically.
        self._write_game_action_json(
            self.game_action_journal_path(),
            self._game_action_journal_record(
                # Preserve the reserved action identity.
                identity=record["identity"],
                # Preserve the immutable planned receipt when present.
                receipt=record["receipt"],
                # Preserve the exact reset namespace across every checkpoint.
                reset_epoch=record["reset_epoch"],
                # Preserve the complete bounded resource set.
                resources=record["resources"],
                # Preserve the exact planner input snapshot.
                snapshot_before=record["snapshot_before"],
                # Advance to the selected recoverable stage.
                stage=stage,
            ),
        )
        # Retain the new stage in the in-memory recovery record.
        record["stage"] = stage

    # Compare and project the exact wallet component of one committed receipt.
    def _apply_game_action_wallets(self, receipt: GameActionReceipt) -> None:
        # Skip the physical players document for a state-only zero-cost action.
        if not receipt.resources.wallet_ids:
            # Finish without creating an unrelated wallet file.
            return
        # Load the complete player document strictly under the global gate.
        players = self._read_game_action_players()
        # Build fast lookup while rejecting duplicate player identities.
        rows_by_id = {}
        # Inspect every compatible player row.
        for row in players["players"]:
            # Ignore malformed unrelated rows exactly as legacy lookups do.
            if type(row) is not dict or type(row.get("player_id")) is not str:
                # Continue until a declared wallet needs strict resolution.
                continue
            # Reject duplicates for any declared wallet.
            if row["player_id"] in rows_by_id and row["player_id"] in receipt.resources.wallet_ids:
                # Preserve ambiguous wallet bytes for operator recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Retain the latest unique row identity.
            rows_by_id[row["player_id"]] = row
        # Convert immutable receipt wallet pairs to bounded lookup maps.
        before = dict(receipt.snapshot_before.wallet_balances)
        # Convert the committed wallet projection to a lookup map.
        after = dict(receipt.snapshot_after.wallet_balances)
        # Collect each declared wallet's current exact balance.
        current = {}
        # Inspect every declared wallet in canonical order.
        for wallet_id in receipt.resources.wallet_ids:
            # Reject a missing committed wallet without guessing recovery state.
            if wallet_id not in rows_by_id:
                # Preserve the journal for operator recovery.
                raise ConflictError("Game action wallet state requires operator recovery")
            # Decode the exact current integer-cent balance.
            current[wallet_id] = self._json_wallet_cents(rows_by_id[wallet_id].get("balance", 0))
        # Return when the complete wallet projection is already committed.
        if current == after:
            # Preserve exact idempotent recovery.
            return
        # Require the complete original snapshot before applying the transition.
        if current != before:
            # Reject mixed or divergent wallet state.
            raise ConflictError("Game action wallet state requires operator recovery")
        # Replace every declared wallet with its exact committed balance.
        for wallet_id in receipt.resources.wallet_ids:
            # Publish only the receipt's deterministic after value.
            rows_by_id[wallet_id]["balance"] = self._json_wallet_value(after[wallet_id])
            # Mark the player row as updated for existing admin compatibility.
            rows_by_id[wallet_id]["updated_at"] = utc_now()
        # Persist the complete compatible player document atomically.
        self._save_players_document(players)

    # Compare and project the exact game-state component of one committed receipt.
    def _apply_game_action_states(self, receipt: GameActionReceipt) -> None:
        # Skip the private state registry for a wallet-only action.
        if not receipt.resources.state_keys:
            # Finish without creating an unrelated state file.
            return
        # Load the complete action-managed state registry strictly.
        registry = self._read_game_action_states()
        # Convert immutable receipt state pairs into lookup maps.
        before = dict(receipt.snapshot_before.state_values)
        # Convert the committed state projection into a lookup map.
        after = dict(receipt.snapshot_after.state_values)
        # Freeze current durable values through a bounded snapshot for exact comparison.
        current_snapshot = GameActionSnapshot.create(
            # Bind the exact state-only resource declaration.
            resources=GameActionResources(state_keys=receipt.resources.state_keys),
            # Supply no wallet values to the state-only snapshot.
            wallet_balances={},
            # Treat absent resources exactly as their original empty-object snapshot.
            state_values={key: registry["states"].get(key, {}) for key in receipt.resources.state_keys},
        )
        # Convert the current immutable state pairs into a lookup map.
        current = dict(current_snapshot.state_values)
        # Return when the complete state projection is already committed.
        if current == after:
            # Preserve exact idempotent recovery.
            return
        # Require the complete original snapshot before applying the transition.
        if current != before:
            # Reject mixed or divergent state instead of compensating.
            raise ConflictError("Game action state requires operator recovery")
        # Replace every declared state resource with its exact committed value.
        for state_key in receipt.resources.state_keys:
            # Publish plain canonical JSON without leaking immutable wrapper types.
            registry["states"][state_key] = self._plain_canonical(after[state_key])
        # Persist the complete provider-private state registry atomically.
        self._write_game_action_json(self.game_action_states_path(), registry)

    # Commit one immutable receipt or verify an already committed identical receipt.
    def _commit_game_action_receipt(self, receipt: GameActionReceipt, reset_epoch: int = 1) -> None:
        # Read and validate every durable receipt before adding a new one.
        registry, receipts = self._read_game_action_receipts(reset_epoch)
        # Derive the unambiguous durable identity key.
        scope_key = self._game_action_scope_key(receipt.identity)
        # Inspect an existing receipt when a failure occurred after its publication.
        existing = receipts.get(scope_key)
        # Reject any immutable receipt divergence at the same scope.
        if existing is not None and existing != receipt:
            # Preserve both journal and receipt bytes for operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Return when the exact immutable receipt is already durable.
        if existing is not None:
            # Preserve idempotent recovery without rewriting registry bytes.
            return
        # Select the exact current-epoch mapping without altering older rows.
        receipt_records = registry["receipts"] if registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION else registry["receipts_by_epoch"].setdefault(str(reset_epoch), {})
        # Add the complete serialized receipt under its epoch-scoped identity.
        receipt_records[scope_key] = self._serialize_game_action_receipt(receipt)
        # Atomically publish the updated immutable receipt registry.
        self._write_game_action_json(self.game_action_receipts_path(), registry)

    # Build deterministic append-only ledger rows for one immutable planned receipt.
    def _game_action_ledger_events(self, receipt: GameActionReceipt) -> tuple[dict, ...]:
        # Track the exact running balance for each declared wallet in planner order.
        balances = dict(receipt.snapshot_before.wallet_balances)
        # Collect one immutable ledger row per nonzero movement.
        events = []
        # Serialize the exact action scope once for deterministic movement identities.
        scope_key = self._game_action_scope_key(receipt.identity)
        # Visit movements in the immutable planner order.
        for index, movement in enumerate(receipt.plan.movements):
            # Read the exact integer-cent balance before this movement.
            before_cents = balances[movement.wallet_id]
            # Compute the exact integer-cent balance after this movement.
            after_cents = before_cents + movement.amount_cents
            # Bind the ledger identity to the complete action scope and movement index.
            ledger_digest = hashlib.sha256(f"{scope_key}:{index}".encode("utf-8")).hexdigest()
            # Construct a compatible ledger event with provider-owned recovery metadata.
            event = {
                # Use one deterministic bounded identifier so crash recovery can detect a prior append.
                "ledger_id": f"gac_{ledger_digest[:60]}",
                # Timestamp the first durable append; replay validates every other immutable field.
                "ts": utc_now(),
                # Preserve the exact affected wallet identity.
                "player_id": movement.wallet_id,
                # Preserve the exact game namespace.
                "game": receipt.identity.game_id,
                # Bind traceability to the caller action key within the legacy field bound.
                "round_id": receipt.identity.action_key[:128],
                # Preserve the provider-neutral movement reason under a distinct namespace.
                "transaction_type": f"game_action_{movement.reason}"[:128],
                # Convert exact cents to the established JSON ledger number shape.
                "amount": self._json_wallet_value(movement.amount_cents),
                # Preserve the exact balance before this movement.
                "balance_before": self._json_wallet_value(before_cents),
                # Preserve the exact balance after this movement.
                "balance_after": self._json_wallet_value(after_cents),
                # Retain immutable action identity evidence without game-specific payloads.
                "details": {
                    # Store the caller-stable action key.
                    "game_action_key": receipt.identity.action_key,
                    # Store the semantic request and resource digest.
                    "game_action_request_fingerprint": receipt.identity.request_fingerprint,
                    # Store the exact movement position for ordered replay proof.
                    "game_action_movement_index": index,
                },
            }
            # Append the exact planned ledger row.
            events.append(event)
            # Advance the wallet-local running balance for later movements.
            balances[movement.wallet_id] = after_cents
        # Return an immutable event sequence for recovery.
        return tuple(events)

    # Append or verify every deterministic ledger row for one planned receipt.
    def _apply_game_action_ledger(self, receipt: GameActionReceipt) -> None:
        # Read all valid append-only rows once under the global action gate.
        existing_rows = {row["ledger_id"]: row for row in self._ledger_rows()}
        # Visit the exact deterministic rows in planner movement order.
        for event in self._game_action_ledger_events(receipt):
            # Resolve an earlier append from a stopped process by deterministic identity.
            existing = existing_rows.get(event["ledger_id"])
            # Verify every immutable field while permitting the original append timestamp.
            if existing is not None:
                # Compare the complete semantic row after substituting the preserved timestamp.
                expected = {**event, "ts": existing.get("ts")}
                # Reject a duplicate identifier whose action semantics diverge.
                if existing != expected:
                    # Preserve the append-only ledger and journal for operator recovery.
                    raise ConflictError("Game action ledger requires operator recovery")
                # Continue without appending a duplicate movement.
                continue
            # Append the new deterministic movement while the global gate remains held.
            self._append_jsonl(self.ledger_path(), event)
            # Retain it for duplicate detection within this receipt.
            existing_rows[event["ledger_id"]] = event

    # Recover one prepared or planned journal before affected state is exposed.
    def _recover_game_action_journal_locked(self, *, inject_failures: bool = False) -> GameActionReceipt | None:
        # Read and validate the private journal without changing corrupt bytes.
        record = self._read_game_action_journal()
        # Return immediately when no action requires recovery.
        if record is None:
            # Report no recovered receipt.
            return None
        # Clear a pre-planner reservation because no outcome or projection exists.
        if record["stage"] == "prepared":
            # Remove the no-op reservation before exposing wallet or state.
            self._remove_game_action_journal()
            # Report that no committed receipt was recovered.
            return None
        # Read the already validated immutable planned receipt.
        receipt = record["receipt"]
        # Publish or validate the immutable execute winner before any projection.
        winning_disposition = self._commit_game_action_claim(receipt.identity, receipt.resources, "execute", record["reset_epoch"])
        # Refuse an impossible planned outcome behind a resolver-owned tombstone.
        if winning_disposition != "execute":
            # Preserve journal and claim bytes for explicit operator recovery.
            raise ConflictError("Game action storage requires operator recovery")
        # Project every declared wallet exactly once.
        self._apply_game_action_wallets(receipt)
        # Inject a process-stop boundary after wallet publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("wallet_applied")
        # Checkpoint the wallet projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "wallet_applied")
        # Append or verify every movement ledger row before publishing game state.
        self._apply_game_action_ledger(receipt)
        # Inject a process-stop boundary after ledger publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("ledger_applied")
        # Checkpoint the append-only ledger projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "ledger_applied")
        # Project every declared state resource exactly once.
        self._apply_game_action_states(receipt)
        # Inject a process-stop boundary after state publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("state_applied")
        # Checkpoint the state projection for restart diagnostics.
        self._write_game_action_journal_stage(record, "state_applied")
        # Commit or verify the immutable receipt registry.
        self._commit_game_action_receipt(receipt, record["reset_epoch"])
        # Inject a process-stop boundary after receipt publication and before stage advance.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("receipt_committed")
        # Checkpoint that every committed projection is now recoverable from its receipt.
        self._write_game_action_journal_stage(record, "receipt_committed")
        # Inject a process-stop boundary immediately before journal cleanup.
        if inject_failures:
            # Invoke only the test-overridable no-op checkpoint.
            self._game_action_checkpoint("cleanup")
        # Remove the journal only after the immutable receipt is durable.
        self._remove_game_action_journal()
        # Return the exact recovered or newly committed receipt.
        return receipt

    # Recover legacy ledger projection and game-action state in one fixed order.
    def _recover_all_json_actions_locked(self) -> None:
        # Complete any shipped logical ledger commit before snapshotting its wallet.
        self._recover_committed_actions()
        # Complete or clear the provider-private game-action journal next.
        self._recover_game_action_journal_locked()

    # Execute or replay one route-free provider-owned JSON game action.
    def execute_game_action_once(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
        planner: Callable[[GameActionSnapshot], GameActionPlan],
    ) -> tuple[GameActionReceipt, bool]:
        # Validate exact contract types before any durable lookup.
        validate_execution_request(identity=identity, resources=resources, planner=planner)
        # Reject recursive provider mutation from inside another planner.
        self._reject_planner_mutation()
        # Serialize same-process callers through the provider instance.
        with self.lock:
            # Serialize every affected JSON projection across instances and processes.
            with self._json_global_gate():
                # Require one ready durable namespace before any journal or resource access.
                reset_epoch = self._ready_game_action_epoch()
                # Complete any shipped logical ledger commit before reading wallets.
                self._recover_committed_actions()
                # Inspect an existing private journal before action-key lookup.
                pending = self._read_game_action_journal()
                # Preserve mismatch-before-mutation semantics for every same-scope journal stage.
                if pending is not None and pending["identity"].scope_key == identity.scope_key:
                    # Reject changed identity or resources before recovery projects any state.
                    if pending["identity"] != identity or pending["resources"] != resources:
                        # Never invoke the planner for conflicting durable key reuse.
                        raise ConflictError("Game action key conflicts with durable semantics")
                # Recover or clear every valid pending stage before receipt lookup.
                self._recover_game_action_journal_locked()
                # Load and validate the complete immutable receipt registry.
                _registry, receipts = self._read_game_action_receipts(reset_epoch)
                # Derive the caller's unambiguous durable scope key.
                scope_key = self._game_action_scope_key(identity)
                # Inspect an earlier committed receipt before any resource snapshot.
                existing = receipts.get(scope_key)
                # Resolve exact replay or conflict without planner/RNG.
                if existing is not None:
                    # Reject fingerprint or resource mismatch before snapshot creation.
                    if existing.identity != identity or existing.resources != resources:
                        # Preserve the committed receipt and fixed conflict semantics.
                        raise ConflictError("Game action key conflicts with committed semantics")
                    # Return the original immutable receipt as a replay.
                    return existing, True
                # Read immutable lifecycle claims only after legacy receipt compatibility.
                _claim_registry, claims = self._read_game_action_claims(reset_epoch)
                # Inspect a resolver or stopped executor winner for this exact scope.
                claim = claims.get(scope_key)
                # Resolve a durable claim before any resource snapshot or planner call.
                if claim is not None:
                    # Reject changed identity or resources against the immutable row.
                    if claim["identity"] != identity or claim["resources"] != resources:
                        # Preserve mismatch-before-planner semantics.
                        raise ConflictError("Game action key conflicts with durable semantics")
                    # Refuse late execution after a resolver-owned uncommitted claim.
                    if claim["disposition"] == "uncommitted":
                        # Keep the tombstone immutable and prevent any resource mutation.
                        raise ConflictError("Game action was durably resolved as uncommitted")
                    # An execute claim without its receipt or journal cannot be repaired safely.
                    raise ConflictError("Game action storage requires operator recovery")
                # Capture exact declared wallet and game state only after durable lookup.
                snapshot_before = self._capture_game_action_snapshot(resources)
                # Build the pre-planner durable reservation.
                prepared = {
                    # Preserve the exact action identity.
                    "identity": identity,
                    # Record that no immutable outcome exists yet.
                    "receipt": None,
                    # Preserve the complete bounded resources.
                    "resources": resources,
                    # Preserve the exact planner input.
                    "snapshot_before": snapshot_before,
                    # Bind every recovery stage to the captured reset namespace.
                    "reset_epoch": reset_epoch,
                    # Mark the pre-planner recovery stage.
                    "stage": "prepared",
                }
                # Durably publish the reservation before invoking planner/RNG.
                self._write_game_action_journal_stage(prepared, "prepared")
                # Inject a process-stop boundary before planner invocation.
                self._game_action_checkpoint("prepared")
                try:
                    # Mark provider mutation forbidden during the synchronous planner.
                    with self._planner_boundary():
                        # Invoke the new-action planner exactly once.
                        plan = planner(snapshot_before)
                    # Require the exact immutable contract plan type.
                    if type(plan) is not GameActionPlan:
                        # Reject arbitrary plan-like values before any projection.
                        raise ValidationError("Game action planner returned an invalid plan")
                    # Compute and validate the exact deterministic committed snapshot.
                    snapshot_after = apply_plan_to_snapshot(snapshot_before, plan)
                    # Construct the complete immutable receipt before publication.
                    receipt = GameActionReceipt(
                        # Bind the exact action identity.
                        identity=identity,
                        # Bind the complete declared resources.
                        resources=resources,
                        # Preserve the immutable planner input.
                        snapshot_before=snapshot_before,
                        # Preserve the complete validated plan.
                        plan=plan,
                        # Preserve the exact deterministic after snapshot.
                        snapshot_after=snapshot_after,
                    )
                # Clear a pre-planner reservation after any planner or validation failure.
                except BaseException:
                    # Remove only the no-mutation prepared journal.
                    self._remove_game_action_journal()
                    # Preserve the caller's original planner or contract exception.
                    raise
                # Attach the immutable receipt to the durable recovery record.
                prepared["receipt"] = receipt
                # Publish the complete planned outcome before any wallet or state write.
                self._write_game_action_journal_stage(prepared, "planned")
                # Inject a process-stop boundary after outcome durability.
                self._game_action_checkpoint("planned")
                # Publish the immutable execute winner after the receipt is recoverable.
                winning_disposition = self._commit_game_action_claim(identity, resources, "execute", reset_epoch)
                # Refuse any impossible resolver win without projecting the plan.
                if winning_disposition != "execute":
                    # Preserve the planned journal and tombstone for operator recovery.
                    raise ConflictError("Game action storage requires operator recovery")
                # Apply and checkpoint every projection through restart-safe recovery.
                committed = self._recover_game_action_journal_locked(inject_failures=True)
                # Require the recovery path to return the just-planned immutable receipt.
                if committed != receipt:
                    # Reject impossible provider divergence without a public result.
                    raise ConflictError("Game action storage requires operator recovery")
                # Return the newly committed receipt with replay false.
                return receipt, False

    # Resolve one JSON action through the same process-wide ownership boundary.
    def resolve_game_action(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
    ) -> GameActionResolution:
        # Validate exact contract types before attempting any provider lock.
        validate_resolution_request(identity=identity, resources=resources)
        # Reject recursive lifecycle resolution from inside a planner.
        self._reject_planner_mutation()
        # Attempt the provider-instance lock without waiting behind active execution.
        lock_acquired = self.lock.acquire(blocking=False)
        # Report active ownership without reading partially projected state.
        if not lock_acquired:
            # Return the provider-neutral finite pending result.
            return GameActionResolution(status="pending")
        try:
            # Attempt both process locks once so resolution never stalls an HTTP worker.
            with self._try_json_global_gate() as gate_acquired:
                # Report active ownership when another process retains either gate.
                if not gate_acquired:
                    # Return no receipt or partial state while execution is in flight.
                    return GameActionResolution(status="pending")
                # Treat reset-owned visibility as finite pending without a claim.
                epoch_state = self._read_game_action_epoch()
                # Keep reset isolation provider-neutral for nonblocking resolution.
                if epoch_state["phase"] != "ready":
                    # Return without journal recovery or immutable lifecycle mutation.
                    return GameActionResolution(status="pending")
                # Capture the exact ready namespace for every later lookup.
                reset_epoch = epoch_state["current_epoch"]
                # Complete any legacy logical money action before inspecting wallets.
                self._recover_committed_actions()
                # Derive the unambiguous durable action scope.
                scope_key = self._game_action_scope_key(identity)
                # Inspect a provider-private journal before committing a resolver claim.
                pending = self._read_game_action_journal()
                # Resolve the same scope through exact fingerprint and resource semantics.
                if pending is not None and pending["identity"].scope_key == identity.scope_key:
                    # Reject changed semantic reuse before any journal recovery mutation.
                    if pending["identity"] != identity or pending["resources"] != resources:
                        # Preserve the active or recoverable journal unchanged.
                        raise ConflictError("Game action key conflicts with durable semantics")
                    # Let the resolver win only while no planner outcome exists.
                    if pending["stage"] == "prepared":
                        # Remove the no-mutation reservation under exclusive ownership.
                        self._remove_game_action_journal()
                        # Append the immutable uncommitted tombstone.
                        winner = self._commit_game_action_claim(identity, resources, "uncommitted", reset_epoch)
                        # Require the resolver to retain its exact winning disposition.
                        if winner != "uncommitted":
                            # Refuse inconsistent lifecycle history.
                            raise ConflictError("Game action storage requires operator recovery")
                        # Return the terminal no-result state.
                        return GameActionResolution(status="uncommitted")
                    # Recover every planned or later stage to its immutable receipt.
                    self._recover_game_action_journal_locked()
                # Recover or clear an unrelated journal before reading shared registries.
                elif pending is not None:
                    # Complete its valid lifecycle under the same global gate.
                    self._recover_game_action_journal_locked()
                # Read committed receipts first for schema-3 JSON compatibility.
                _receipt_registry, receipts = self._read_game_action_receipts(reset_epoch)
                # Inspect the exact caller scope after all recoverable projection work.
                receipt = receipts.get(scope_key)
                # Return a compatible legacy or schema-4 committed result.
                if receipt is not None:
                    # Reject changed identity or resources before returning prior outcome data.
                    if receipt.identity != identity or receipt.resources != resources:
                        # Preserve the immutable committed receipt.
                        raise ConflictError("Game action key conflicts with committed semantics")
                    # Return the complete provider-neutral committed resolution.
                    return GameActionResolution(status="committed", receipt=receipt)
                # Read immutable lifecycle claims after legacy receipt lookup.
                _claim_registry, claims = self._read_game_action_claims(reset_epoch)
                # Inspect an earlier resolver or executor winner.
                claim = claims.get(scope_key)
                # Validate exact compatible claim reuse before returning its state.
                if claim is not None:
                    # Reject changed semantic reuse without rewriting the winner.
                    if claim["identity"] != identity or claim["resources"] != resources:
                        # Preserve mismatch-before-mutation semantics.
                        raise ConflictError("Game action key conflicts with durable semantics")
                    # Return a resolver-owned tombstone as the terminal no-result state.
                    if claim["disposition"] == "uncommitted":
                        # Return no receipt for an action that never committed.
                        return GameActionResolution(status="uncommitted")
                    # An execute claim without a receipt or journal needs operator repair.
                    raise ConflictError("Game action storage requires operator recovery")
                # Atomically append the resolver-owned tombstone as the first claim.
                winner = self._commit_game_action_claim(identity, resources, "uncommitted", reset_epoch)
                # Require this exact resolver to retain the immutable winning state.
                if winner != "uncommitted":
                    # Reject an impossible disposition transition.
                    raise ConflictError("Game action storage requires operator recovery")
                # Return the durable terminal no-result state.
                return GameActionResolution(status="uncommitted")
        finally:
            # Release the provider-instance lock after every finite or exceptional outcome.
            self.lock.release()
