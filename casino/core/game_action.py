# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-neutral game-action contract checkpoint for issue #430 Phase0c slice 2.

This module defines immutable action identities, declared resources, snapshots, plans,
receipts, and the abstract execution boundary that future storage providers must
implement. It intentionally contains no JSON/MySQL implementation, route integration,
game integration, or production atomicity claim.
"""

# Import postponed annotations so recursive immutable value hints stay readable.
from __future__ import annotations

# Import the abstract-base boundary used by future provider implementations.
from abc import ABC, abstractmethod
# Import callable typing for the side-effect-free planner contract.
from collections.abc import Callable
# Import frozen data classes for immutable provider-neutral contract values.
from dataclasses import dataclass
# Import SHA-256 for canonical semantic request fingerprints.
import hashlib
# Import canonical JSON encoding for provider-independent fingerprints.
import json
# Import regular expressions for bounded internal identities and digests.
import re

# Import stable public validation errors for malformed contract values.
from casino.errors import ValidationError


# Bound every internal identity to the existing storage action-key width.
MAX_IDENTITY_LENGTH = 191
# Bound one action to a small explicit wallet resource set.
MAX_WALLET_RESOURCES = 8
# Bound one action to a small explicit game-state resource set.
MAX_STATE_RESOURCES = 16
# Bound one plan to a finite number of signed wallet movements.
MAX_MOVEMENTS = 32
# Bound canonical request nesting before hashing.
MAX_CANONICAL_DEPTH = 12
# Bound the total canonical request nodes before hashing.
MAX_CANONICAL_ITEMS = 512
# Bound one canonical request string or object key.
MAX_CANONICAL_TEXT = 4_096
# Bound the encoded canonical request before hashing.
MAX_CANONICAL_BYTES = 65_536
# Keep cents inside the conservative signed 64-bit storage domain.
MAX_INTEGER_CENTS = 9_000_000_000_000_000_000
# Apply the same conservative bound to canonical integer payload values.
MAX_CANONICAL_INTEGER = MAX_INTEGER_CENTS
# Accept only portable internal identity characters.
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
# Require one lowercase SHA-256 digest at durable identity boundaries.
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


# Define one immutable canonical JSON array representation.
@dataclass(frozen=True, slots=True)
class FrozenArray:
    # Store canonical array members in their exact order.
    items: tuple

    # Reject direct construction that bypasses the canonical freezer.
    def __post_init__(self) -> None:
        # Require the immutable tuple container used by the contract.
        if type(self.items) is not tuple:
            # Fail closed before a mutable array can enter a plan or receipt.
            raise ValidationError("Canonical array is invalid")
        # Validate every nested member without coercion.
        for item in self.items:
            # Reject any value outside the frozen canonical domain.
            if not _is_frozen_value(item):
                # Publish one fixed value-free canonical error.
                raise ValidationError("Canonical array is invalid")
        # Enforce depth, item, text, and integer bounds on direct construction.
        _validate_frozen_tree(self)


# Define one immutable canonical JSON object representation.
@dataclass(frozen=True, slots=True)
class FrozenObject:
    # Store lexicographically sorted key/value pairs.
    items: tuple

    # Reject direct construction that bypasses canonical ordering and types.
    def __post_init__(self) -> None:
        # Require the immutable tuple container used by the contract.
        if type(self.items) is not tuple:
            # Fail closed before a mutable object can enter a plan or receipt.
            raise ValidationError("Canonical object is invalid")
        # Collect keys for uniqueness and ordering validation.
        keys = []
        # Validate each exact key/value pair.
        for item in self.items:
            # Require a two-item immutable pair.
            if type(item) is not tuple or len(item) != 2:
                # Publish one fixed value-free canonical error.
                raise ValidationError("Canonical object is invalid")
            # Split the canonical key and nested value.
            key, value = item
            # Require a bounded exact string key.
            if type(key) is not str or not key or len(key) > MAX_CANONICAL_TEXT:
                # Reject non-JSON and unbounded keys.
                raise ValidationError("Canonical object is invalid")
            # Reject any value outside the frozen canonical domain.
            if not _is_frozen_value(value):
                # Publish one fixed value-free canonical error.
                raise ValidationError("Canonical object is invalid")
            # Retain the validated key for order and duplicate checks.
            keys.append(key)
        # Require exact lexicographic order and unique keys.
        if keys != sorted(set(keys)):
            # Prevent multiple encodings of the same semantic object.
            raise ValidationError("Canonical object is invalid")
        # Enforce depth, item, text, and integer bounds on direct construction.
        _validate_frozen_tree(self)


# Return whether a value belongs to the immutable canonical JSON domain.
def _is_frozen_value(value) -> bool:
    # Accept JSON null, boolean, integer, and text only as exact scalar types.
    if value is None or type(value) in {bool, int, str}:
        # Confirm the exact scalar type belongs to the contract.
        return True
    # Accept only the two validated immutable composite types.
    return type(value) in {FrozenArray, FrozenObject}


# Enforce complete canonical bounds on an already frozen value tree.
def _validate_frozen_tree(value) -> None:
    # Track the complete node count across this immutable tree.
    budget = [0]
    # Validate the root and every nested member.
    _validate_frozen_node(value, depth=0, budget=budget)


# Recursively validate one already frozen canonical node.
def _validate_frozen_node(value, *, depth: int, budget: list[int]) -> None:
    # Count this scalar or composite node.
    budget[0] += 1
    # Reject values wider than the complete canonical item budget.
    if budget[0] > MAX_CANONICAL_ITEMS:
        # Publish one fixed value-free bound failure.
        raise ValidationError("Canonical payload is too large")
    # Reject nesting deeper than the reviewed contract.
    if depth > MAX_CANONICAL_DEPTH:
        # Publish one fixed value-free bound failure.
        raise ValidationError("Canonical payload is too deep")
    # Accept JSON null and booleans exactly.
    if value is None or type(value) is bool:
        # Finish scalar validation.
        return
    # Validate exact bounded integers.
    if type(value) is int:
        # Reject integers outside the conservative provider storage domain.
        if abs(value) > MAX_CANONICAL_INTEGER:
            # Publish one fixed value-free numeric failure.
            raise ValidationError("Canonical integer is out of range")
        # Finish scalar validation.
        return
    # Validate exact bounded text.
    if type(value) is str:
        # Reject strings that exceed the canonical field budget.
        if len(value) > MAX_CANONICAL_TEXT:
            # Publish one fixed value-free text failure.
            raise ValidationError("Canonical text is too long")
        # Finish scalar validation.
        return
    # Validate every immutable array member.
    if type(value) is FrozenArray:
        # Descend into each ordered canonical member.
        for item in value.items:
            # Validate the nested member under the next depth.
            _validate_frozen_node(item, depth=depth + 1, budget=budget)
        # Finish composite validation.
        return
    # Validate every immutable object key and member.
    if type(value) is FrozenObject:
        # Descend into each canonical object pair.
        for key, item in value.items:
            # Validate the exact bounded object key as a text node.
            _validate_frozen_node(key, depth=depth + 1, budget=budget)
            # Validate the nested object value under the next depth.
            _validate_frozen_node(item, depth=depth + 1, budget=budget)
        # Finish composite validation.
        return
    # Reject all values outside the frozen canonical domain.
    raise ValidationError("Canonical value type is invalid")


# Freeze a JSON-compatible value under bounded deterministic rules.
def freeze_canonical(value):
    # Track total nodes so wide payloads fail before hashing.
    budget = [0]
    # Track active container identities so recursive Python structures fail closed.
    active = set()
    # Freeze the complete value from the root depth.
    return _freeze_canonical(value, depth=0, budget=budget, active=active)


# Recursively freeze one canonical value while enforcing depth and size limits.
def _freeze_canonical(value, *, depth: int, budget: list[int], active: set[int]):
    # Count this scalar or composite node.
    budget[0] += 1
    # Reject values wider than the complete canonical item budget.
    if budget[0] > MAX_CANONICAL_ITEMS:
        # Publish one fixed value-free bound failure.
        raise ValidationError("Canonical payload is too large")
    # Reject nesting deeper than the reviewed contract.
    if depth > MAX_CANONICAL_DEPTH:
        # Publish one fixed value-free bound failure.
        raise ValidationError("Canonical payload is too deep")
    # Preserve JSON null and booleans exactly.
    if value is None or type(value) is bool:
        # Return the immutable scalar unchanged.
        return value
    # Preserve bounded signed integers exactly without bool coercion.
    if type(value) is int:
        # Reject integers outside the conservative provider storage domain.
        if abs(value) > MAX_CANONICAL_INTEGER:
            # Publish one fixed value-free numeric failure.
            raise ValidationError("Canonical integer is out of range")
        # Return the immutable integer unchanged.
        return value
    # Preserve bounded text exactly.
    if type(value) is str:
        # Reject strings that exceed the canonical field budget.
        if len(value) > MAX_CANONICAL_TEXT:
            # Publish one fixed value-free text failure.
            raise ValidationError("Canonical text is too long")
        # Return the immutable string unchanged.
        return value
    # Revalidate already frozen contract values through their constructors.
    if type(value) in {FrozenArray, FrozenObject}:
        # Return an already immutable canonical value.
        return value
    # Freeze exact Python lists as canonical arrays.
    if type(value) is list:
        # Reject recursive containers before descending.
        if id(value) in active:
            # Publish one fixed value-free recursion failure.
            raise ValidationError("Canonical payload is recursive")
        # Mark this container active only for its recursive descent.
        active.add(id(value))
        try:
            # Freeze every array item in the caller's semantic order.
            items = tuple(_freeze_canonical(item, depth=depth + 1, budget=budget, active=active) for item in value)
        finally:
            # Release the container identity after its descendants are complete.
            active.remove(id(value))
        # Return the validated immutable array wrapper.
        return FrozenArray(items)
    # Freeze exact Python dictionaries as canonical objects.
    if type(value) is dict:
        # Reject recursive containers before descending.
        if id(value) in active:
            # Publish one fixed value-free recursion failure.
            raise ValidationError("Canonical payload is recursive")
        # Mark this container active only for its recursive descent.
        active.add(id(value))
        try:
            # Build validated immutable key/value pairs.
            pairs = []
            # Visit keys in deterministic lexical order after exact type validation.
            for key in sorted(value.keys()) if all(type(key) is str for key in value) else ():
                # Reject empty or unbounded JSON object keys.
                if not key or len(key) > MAX_CANONICAL_TEXT:
                    # Publish one fixed value-free key failure.
                    raise ValidationError("Canonical object key is invalid")
                # Freeze the matching nested value.
                nested = _freeze_canonical(value[key], depth=depth + 1, budget=budget, active=active)
                # Retain the canonical pair.
                pairs.append((key, nested))
            # Reject any non-string key that skipped deterministic traversal.
            if len(pairs) != len(value):
                # Publish one fixed value-free key failure.
                raise ValidationError("Canonical object key is invalid")
        finally:
            # Release the container identity after its descendants are complete.
            active.remove(id(value))
        # Return the validated immutable object wrapper.
        return FrozenObject(tuple(pairs))
    # Reject floats, bytes, custom mappings, sets, and all other non-JSON types.
    raise ValidationError("Canonical value type is invalid")


# Convert one frozen canonical value back to ordinary JSON containers.
def _thaw_canonical(value):
    # Preserve exact scalar values.
    if value is None or type(value) in {bool, int, str}:
        # Return the scalar unchanged.
        return value
    # Convert immutable arrays to ordinary JSON lists.
    if type(value) is FrozenArray:
        # Recursively thaw every canonical array member.
        return [_thaw_canonical(item) for item in value.items]
    # Convert immutable objects to insertion-ordered JSON dictionaries.
    if type(value) is FrozenObject:
        # Recursively thaw every canonical object value.
        return {key: _thaw_canonical(item) for key, item in value.items}
    # Treat internal misuse as a fixed contract validation failure.
    raise ValidationError("Canonical value type is invalid")


# Encode one value to the unique bounded canonical JSON byte form.
def canonical_json_bytes(value) -> bytes:
    # Freeze caller containers before deterministic encoding.
    frozen = freeze_canonical(value)
    # Revalidate direct immutable wrappers against complete canonical bounds.
    _validate_frozen_tree(frozen)
    # Encode sorted compact UTF-8 JSON without non-finite numeric support.
    encoded = json.dumps(
        # Convert immutable wrappers to ordinary JSON containers.
        _thaw_canonical(frozen),
        # Preserve the already canonical object key order defensively.
        sort_keys=True,
        # Remove insignificant whitespace from the fingerprint input.
        separators=(",", ":"),
        # Preserve Unicode text through one UTF-8 encoding.
        ensure_ascii=False,
        # Reject non-finite values if future scalar rules ever expand.
        allow_nan=False,
    ).encode("utf-8")
    # Reject an encoded request larger than the contract budget.
    if len(encoded) > MAX_CANONICAL_BYTES:
        # Publish one fixed value-free bound failure.
        raise ValidationError("Canonical payload is too large")
    # Return the unique byte representation.
    return encoded


# Derive one lowercase SHA-256 digest from canonical request semantics.
def canonical_fingerprint(value) -> str:
    # Hash the exact canonical UTF-8 byte representation.
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


# Require one exact portable internal identity token.
def _require_identity(value, *, field: str) -> str:
    # Reject non-string, empty, unbounded, or non-portable identity values.
    if type(value) is not str or not value or len(value) > MAX_IDENTITY_LENGTH or IDENTITY_PATTERN.fullmatch(value) is None:
        # Publish a fixed diagnostic naming only the contract field.
        raise ValidationError(f"{field} is invalid")
    # Return the exact validated value without normalization.
    return value


# Require one canonical sorted unique resource tuple.
def _require_resource_tuple(value, *, field: str, maximum: int) -> tuple[str, ...]:
    # Require the immutable tuple representation.
    if type(value) is not tuple:
        # Reject mutable or coercible resource collections.
        raise ValidationError(f"{field} is invalid")
    # Reject resource sets wider than the declared contract.
    if len(value) > maximum:
        # Publish a fixed bounded-resource diagnostic.
        raise ValidationError(f"{field} is too large")
    # Validate every resource identifier.
    validated = tuple(_require_identity(item, field=field) for item in value)
    # Require caller-supplied canonical order and uniqueness.
    if validated != tuple(sorted(set(validated))):
        # Prevent duplicate or order-dependent resource identities.
        raise ValidationError(f"{field} must be sorted and unique")
    # Return the exact immutable tuple.
    return validated


# Declare every wallet and state resource one action may access.
@dataclass(frozen=True, slots=True)
class GameActionResources:
    # List wallet identities in canonical sorted order.
    wallet_ids: tuple[str, ...] = ()
    # List game-state keys in canonical sorted order.
    state_keys: tuple[str, ...] = ()

    # Enforce finite explicit resources before provider access.
    def __post_init__(self) -> None:
        # Validate the complete wallet resource set.
        _require_resource_tuple(self.wallet_ids, field="Wallet resources", maximum=MAX_WALLET_RESOURCES)
        # Validate the complete state resource set.
        _require_resource_tuple(self.state_keys, field="State resources", maximum=MAX_STATE_RESOURCES)
        # Require at least one declared resource for a meaningful action.
        if not self.wallet_ids and not self.state_keys:
            # Reject resource-free planners that cannot be bounded.
            raise ValidationError("At least one game-action resource is required")

    # Return the canonical request representation bound into action fingerprints.
    def fingerprint_value(self) -> dict:
        # Return only provider-neutral resource identities.
        return {
            # Bind the exact state resource set.
            "state_keys": list(self.state_keys),
            # Bind the exact wallet resource set.
            "wallet_ids": list(self.wallet_ids),
        }


# Identify one caller-stable semantic game action.
@dataclass(frozen=True, slots=True)
class GameActionIdentity:
    # Scope the action to one game namespace.
    game_id: str
    # Scope the action to one authenticated player/controller.
    player_id: str
    # Store the caller-stable idempotency key.
    action_key: str
    # Store the canonical request-and-resource SHA-256 digest.
    request_fingerprint: str

    # Validate direct durable reconstruction without coercion.
    def __post_init__(self) -> None:
        # Validate the game namespace.
        _require_identity(self.game_id, field="Game action game_id")
        # Validate the player/controller identity.
        _require_identity(self.player_id, field="Game action player_id")
        # Validate the caller-stable action key.
        _require_identity(self.action_key, field="Game action action_key")
        # Require an exact lowercase SHA-256 digest.
        if type(self.request_fingerprint) is not str or FINGERPRINT_PATTERN.fullmatch(self.request_fingerprint) is None:
            # Reject spoofable or noncanonical fingerprint values.
            raise ValidationError("Game action request_fingerprint is invalid")

    # Build one identity from canonical request and resource semantics.
    @classmethod
    def create(cls, *, game_id: str, player_id: str, action_key: str, resources: GameActionResources, request) -> GameActionIdentity:
        # Require the exact resource contract before hashing.
        if type(resources) is not GameActionResources:
            # Reject arbitrary resource-like objects.
            raise ValidationError("Game action resources are invalid")
        # Bind the contract version, request, and complete resource set into one digest.
        fingerprint = canonical_fingerprint(
            {
                # Version the semantic fingerprint envelope.
                "contract": "game-action/v1",
                # Preserve the caller's canonical request semantics.
                "request": request,
                # Prevent a resource-set change from reusing an old identity.
                "resources": resources.fingerprint_value(),
            }
        )
        # Return the validated immutable action identity.
        return cls(game_id=game_id, player_id=player_id, action_key=action_key, request_fingerprint=fingerprint)

    # Return the durable scope key providers must inspect before snapshots or planners.
    @property
    def scope_key(self) -> tuple[str, str, str]:
        # Scope reuse to the same game, player/controller, and caller key.
        return (self.game_id, self.player_id, self.action_key)


# Require one exact signed integer-cent value.
def _require_cents(value, *, field: str, allow_zero: bool) -> int:
    # Reject booleans, floats, strings, and arbitrary numeric objects.
    if type(value) is not int:
        # Publish one fixed integer-cent diagnostic.
        raise ValidationError(f"{field} must be integer cents")
    # Reject a zero movement while allowing zero balances.
    if not allow_zero and value == 0:
        # Keep zero-cost actions represented by no movement rather than a fake row.
        raise ValidationError(f"{field} cannot be zero")
    # Reject values outside the conservative signed provider domain.
    if abs(value) > MAX_INTEGER_CENTS:
        # Publish one fixed bounded-cents diagnostic.
        raise ValidationError(f"{field} is out of range")
    # Return the exact integer without normalization.
    return value


# Capture the exact immutable provider-owned state supplied to a planner.
@dataclass(frozen=True, slots=True)
class GameActionSnapshot:
    # Bind the snapshot to the declared resource set.
    resources: GameActionResources
    # Store sorted wallet identity and integer-cent balance pairs.
    wallet_balances: tuple[tuple[str, int], ...]
    # Store sorted state-key and canonical-value pairs.
    state_values: tuple[tuple[str, object], ...]

    # Validate direct reconstruction from a durable provider.
    def __post_init__(self) -> None:
        # Require the exact resource contract type.
        if type(self.resources) is not GameActionResources:
            # Reject arbitrary resource-like objects.
            raise ValidationError("Game action snapshot resources are invalid")
        # Require immutable sorted wallet pairs.
        if type(self.wallet_balances) is not tuple:
            # Reject mutable or coercible wallet collections.
            raise ValidationError("Game action wallet snapshot is invalid")
        # Validate every wallet pair.
        wallet_ids = []
        # Inspect each immutable wallet entry.
        for entry in self.wallet_balances:
            # Require one exact two-item tuple.
            if type(entry) is not tuple or len(entry) != 2:
                # Reject malformed provider snapshots.
                raise ValidationError("Game action wallet snapshot is invalid")
            # Split the wallet identity and balance.
            wallet_id, balance_cents = entry
            # Validate the wallet identity.
            wallet_ids.append(_require_identity(wallet_id, field="Wallet snapshot identity"))
            # Validate the exact integer-cent balance.
            _require_cents(balance_cents, field="Wallet snapshot balance", allow_zero=True)
            # Reject negative committed balances.
            if balance_cents < 0:
                # Prevent planners from observing impossible wallet state.
                raise ValidationError("Wallet snapshot balance cannot be negative")
        # Require exact declared canonical wallet coverage.
        if tuple(wallet_ids) != self.resources.wallet_ids:
            # Reject missing, duplicate, reordered, or undeclared wallets.
            raise ValidationError("Game action wallet snapshot does not match resources")
        # Require immutable sorted state pairs.
        if type(self.state_values) is not tuple:
            # Reject mutable or coercible state collections.
            raise ValidationError("Game action state snapshot is invalid")
        # Validate every state pair.
        state_keys = []
        # Inspect each immutable state entry.
        for entry in self.state_values:
            # Require one exact two-item tuple.
            if type(entry) is not tuple or len(entry) != 2:
                # Reject malformed provider snapshots.
                raise ValidationError("Game action state snapshot is invalid")
            # Split the state key and immutable value.
            state_key, state_value = entry
            # Validate the state identity.
            state_keys.append(_require_identity(state_key, field="State snapshot identity"))
            # Require a pre-frozen canonical state value.
            if not _is_frozen_value(state_value):
                # Reject mutable state escaping into a planner.
                raise ValidationError("Game action state snapshot is invalid")
            # Enforce all canonical scalar, nesting, and item bounds on direct reconstruction.
            _validate_frozen_tree(state_value)
        # Require exact declared canonical state coverage.
        if tuple(state_keys) != self.resources.state_keys:
            # Reject missing, duplicate, reordered, or undeclared state keys.
            raise ValidationError("Game action state snapshot does not match resources")

    # Build one immutable snapshot from ordinary provider dictionaries.
    @classmethod
    def create(cls, *, resources: GameActionResources, wallet_balances: dict, state_values: dict) -> GameActionSnapshot:
        # Require the exact declared resource contract.
        if type(resources) is not GameActionResources:
            # Reject arbitrary resource-like objects.
            raise ValidationError("Game action snapshot resources are invalid")
        # Require ordinary provider dictionaries without custom mapping behavior.
        if type(wallet_balances) is not dict or type(state_values) is not dict:
            # Reject custom mapping side effects at the planner boundary.
            raise ValidationError("Game action snapshot input is invalid")
        # Require exact wallet key coverage before reading values.
        if set(wallet_balances) != set(resources.wallet_ids):
            # Reject missing or undeclared wallet data.
            raise ValidationError("Game action wallet snapshot does not match resources")
        # Require exact state key coverage before reading values.
        if set(state_values) != set(resources.state_keys):
            # Reject missing or undeclared game state.
            raise ValidationError("Game action state snapshot does not match resources")
        # Normalize wallet pairs in the declared canonical order.
        wallets = tuple((wallet_id, _require_cents(wallet_balances[wallet_id], field="Wallet snapshot balance", allow_zero=True)) for wallet_id in resources.wallet_ids)
        # Freeze state values in the declared canonical order.
        states = tuple((state_key, freeze_canonical(state_values[state_key])) for state_key in resources.state_keys)
        # Return the fully validated immutable snapshot.
        return cls(resources=resources, wallet_balances=wallets, state_values=states)

    # Read one declared wallet balance without exposing a mutable mapping.
    def wallet_balance(self, wallet_id: str) -> int:
        # Validate the requested wallet identity.
        _require_identity(wallet_id, field="Wallet snapshot identity")
        # Locate the bounded declared wallet.
        for current_id, balance_cents in self.wallet_balances:
            # Return the exact integer cents for the matching wallet.
            if current_id == wallet_id:
                # Preserve exact integer-cent semantics.
                return balance_cents
        # Reject undeclared reads from a planner.
        raise ValidationError("Wallet resource was not declared")

    # Read one declared immutable state value.
    def state_value(self, state_key: str):
        # Validate the requested state identity.
        _require_identity(state_key, field="State snapshot identity")
        # Locate the bounded declared state entry.
        for current_key, state_value in self.state_values:
            # Return the immutable canonical value for the matching key.
            if current_key == state_key:
                # Preserve the frozen value without copying mutable containers.
                return state_value
        # Reject undeclared reads from a planner.
        raise ValidationError("State resource was not declared")


# Describe one signed wallet movement requested by a plan.
@dataclass(frozen=True, slots=True)
class GameActionMovement:
    # Select one declared wallet resource.
    wallet_id: str
    # Store one non-zero signed integer-cent delta.
    amount_cents: int
    # Record a bounded provider-neutral movement meaning.
    reason: str

    # Validate every movement before provider commit.
    def __post_init__(self) -> None:
        # Validate the wallet identity.
        _require_identity(self.wallet_id, field="Game action movement wallet_id")
        # Require a non-zero signed integer-cent delta.
        _require_cents(self.amount_cents, field="Game action movement amount", allow_zero=False)
        # Validate the movement meaning.
        _require_identity(self.reason, field="Game action movement reason")


# Describe one side-effect-free action result and its requested writes.
@dataclass(frozen=True, slots=True)
class GameActionPlan:
    # Store the complete immutable game outcome.
    outcome: object
    # Store bounded signed wallet movements.
    movements: tuple[GameActionMovement, ...] = ()
    # Store sorted state replacements for declared state keys.
    state_updates: tuple[tuple[str, object], ...] = ()

    # Validate direct immutable plan construction.
    def __post_init__(self) -> None:
        # Require a frozen canonical outcome.
        if not _is_frozen_value(self.outcome):
            # Reject mutable planner outcomes.
            raise ValidationError("Game action outcome is invalid")
        # Enforce all canonical scalar, nesting, and item bounds on direct reconstruction.
        _validate_frozen_tree(self.outcome)
        # Require an immutable bounded movement tuple.
        if type(self.movements) is not tuple or len(self.movements) > MAX_MOVEMENTS:
            # Reject mutable or unbounded movement collections.
            raise ValidationError("Game action movements are invalid")
        # Validate every exact movement type.
        if any(type(movement) is not GameActionMovement for movement in self.movements):
            # Reject arbitrary movement-like objects.
            raise ValidationError("Game action movements are invalid")
        # Require an immutable bounded state-update tuple.
        if type(self.state_updates) is not tuple or len(self.state_updates) > MAX_STATE_RESOURCES:
            # Reject mutable or unbounded state writes.
            raise ValidationError("Game action state updates are invalid")
        # Collect state keys for exact order and uniqueness validation.
        keys = []
        # Validate every state update.
        for entry in self.state_updates:
            # Require one exact immutable key/value pair.
            if type(entry) is not tuple or len(entry) != 2:
                # Reject malformed planner state writes.
                raise ValidationError("Game action state updates are invalid")
            # Split the state key and immutable replacement.
            state_key, state_value = entry
            # Validate the state identity.
            keys.append(_require_identity(state_key, field="Game action state update key"))
            # Require a frozen canonical replacement.
            if not _is_frozen_value(state_value):
                # Reject mutable planner state writes.
                raise ValidationError("Game action state updates are invalid")
            # Enforce all canonical scalar, nesting, and item bounds on direct reconstruction.
            _validate_frozen_tree(state_value)
        # Require canonical order and unique state writes.
        if keys != sorted(set(keys)):
            # Prevent order-dependent or duplicate state replacements.
            raise ValidationError("Game action state updates must be sorted and unique")

    # Build one immutable plan from ordinary game result containers.
    @classmethod
    def create(cls, *, outcome, movements=(), state_updates=None) -> GameActionPlan:
        # Require a concrete list or tuple of exact movement objects.
        if type(movements) not in {list, tuple}:
            # Reject arbitrary iterators with hidden side effects.
            raise ValidationError("Game action movements are invalid")
        # Treat no state updates as an empty provider-neutral mapping.
        normalized_updates = {} if state_updates is None else state_updates
        # Require an ordinary dictionary without custom mapping behavior.
        if type(normalized_updates) is not dict:
            # Reject arbitrary state-update mappings.
            raise ValidationError("Game action state updates are invalid")
        # Freeze and sort every requested state replacement.
        frozen_updates = tuple((key, freeze_canonical(normalized_updates[key])) for key in sorted(normalized_updates) if type(key) is str)
        # Reject non-string keys that were excluded from canonical traversal.
        if len(frozen_updates) != len(normalized_updates):
            # Publish one fixed state-key failure.
            raise ValidationError("Game action state updates are invalid")
        # Return the validated immutable plan.
        return cls(outcome=freeze_canonical(outcome), movements=tuple(movements), state_updates=frozen_updates)


# Validate one plan only against its declared immutable snapshot.
def validate_plan(snapshot: GameActionSnapshot, plan: GameActionPlan) -> None:
    # Require exact contract types rather than lookalike objects.
    if type(snapshot) is not GameActionSnapshot or type(plan) is not GameActionPlan:
        # Reject malformed planner/provider boundaries.
        raise ValidationError("Game action plan boundary is invalid")
    # Seed aggregate wallet deltas for every declared wallet.
    totals = {wallet_id: 0 for wallet_id in snapshot.resources.wallet_ids}
    # Validate and aggregate every signed movement.
    for movement in plan.movements:
        # Reject a movement against an undeclared wallet.
        if movement.wallet_id not in totals:
            # Fail before any provider mutation.
            raise ValidationError("Game action movement resource was not declared")
        # Add the exact signed integer-cent delta.
        totals[movement.wallet_id] += movement.amount_cents
        # Reject an aggregate outside the conservative storage range.
        _require_cents(totals[movement.wallet_id], field="Game action aggregate movement", allow_zero=True)
    # Validate resulting wallet balances without mutating the snapshot.
    for wallet_id, delta_cents in totals.items():
        # Calculate the exact proposed committed balance.
        resulting_balance = snapshot.wallet_balance(wallet_id) + delta_cents
        # Require the resulting balance to remain in the storage domain.
        _require_cents(resulting_balance, field="Game action resulting balance", allow_zero=True)
        # Reject overdraw before any provider mutation.
        if resulting_balance < 0:
            # Publish one fixed provider-neutral balance failure.
            raise ValidationError("Game action would overdraw a wallet")
    # Validate every requested state replacement against declared resources.
    for state_key, _state_value in plan.state_updates:
        # Reject a write against an undeclared state resource.
        if state_key not in snapshot.resources.state_keys:
            # Fail before any provider mutation.
            raise ValidationError("Game action state resource was not declared")


# Apply one validated plan purely to an immutable snapshot.
def apply_plan_to_snapshot(snapshot: GameActionSnapshot, plan: GameActionPlan) -> GameActionSnapshot:
    # Validate all movement and state-write boundaries first.
    validate_plan(snapshot, plan)
    # Copy bounded wallet balances into a temporary ordinary mapping.
    wallet_balances = dict(snapshot.wallet_balances)
    # Apply every signed integer-cent movement in plan order.
    for movement in plan.movements:
        # Add the exact signed delta to the declared wallet.
        wallet_balances[movement.wallet_id] += movement.amount_cents
    # Copy bounded immutable state values into a temporary ordinary mapping.
    state_values = dict(snapshot.state_values)
    # Apply every canonical state replacement.
    for state_key, state_value in plan.state_updates:
        # Replace only the declared state key.
        state_values[state_key] = state_value
    # Return a new immutable snapshot without mutating the planner input.
    return GameActionSnapshot.create(resources=snapshot.resources, wallet_balances=wallet_balances, state_values=state_values)


# Preserve one immutable committed action outcome for paid or zero-cost actions.
@dataclass(frozen=True, slots=True)
class GameActionReceipt:
    # Store the exact semantic action identity.
    identity: GameActionIdentity
    # Store the exact bounded resource set.
    resources: GameActionResources
    # Store the immutable provider snapshot given to the planner.
    snapshot_before: GameActionSnapshot
    # Store the immutable validated plan.
    plan: GameActionPlan
    # Store the immutable committed snapshot.
    snapshot_after: GameActionSnapshot

    # Verify receipt self-consistency during commit or durable reconstruction.
    def __post_init__(self) -> None:
        # Require exact contract types.
        if type(self.identity) is not GameActionIdentity or type(self.resources) is not GameActionResources:
            # Reject malformed receipt identity fields.
            raise ValidationError("Game action receipt identity is invalid")
        # Require exact snapshot and plan contract types.
        if type(self.snapshot_before) is not GameActionSnapshot or type(self.plan) is not GameActionPlan or type(self.snapshot_after) is not GameActionSnapshot:
            # Reject malformed receipt result fields.
            raise ValidationError("Game action receipt result is invalid")
        # Bind both snapshots to the receipt resource declaration.
        if self.snapshot_before.resources != self.resources or self.snapshot_after.resources != self.resources:
            # Reject resource drift inside an immutable receipt.
            raise ValidationError("Game action receipt resources are inconsistent")
        # Recompute the pure expected post-action snapshot.
        expected_after = apply_plan_to_snapshot(self.snapshot_before, self.plan)
        # Require the committed snapshot to equal the exact deterministic plan result.
        if expected_after != self.snapshot_after:
            # Reject a receipt whose state or money projection diverges from its plan.
            raise ValidationError("Game action receipt result is inconsistent")


# Define the provider planner callable accepted by the abstract boundary.
GameActionPlanner = Callable[[GameActionSnapshot], GameActionPlan]


# Define the provider-neutral execution boundary without implementing persistence.
class GameActionExecutor(ABC):
    """Abstract boundary future providers must implement as one durable action.

    Implementations must validate identity/resources first, inspect durable action-key
    reuse before snapshot creation, reject a fingerprint/resource mismatch before the
    planner (and therefore RNG), call the planner at most once for a new action, commit
    its complete immutable receipt, and return the original receipt on compatible replay.
    This abstract checkpoint does not assert that any current production provider meets
    those requirements.
    """

    # Commit or replay one paid or zero-cost game action.
    @abstractmethod
    def execute_game_action_once(
        self,
        *,
        identity: GameActionIdentity,
        resources: GameActionResources,
        planner: GameActionPlanner,
    ) -> tuple[GameActionReceipt, bool]:
        # Concrete providers must supply the reviewed durable boundary later.
        raise NotImplementedError


# Validate the shared entry types before a provider performs any lookup.
def validate_execution_request(*, identity, resources, planner) -> None:
    # Require the exact immutable identity.
    if type(identity) is not GameActionIdentity:
        # Reject arbitrary identity-like objects.
        raise ValidationError("Game action identity is invalid")
    # Require the exact immutable resource declaration.
    if type(resources) is not GameActionResources:
        # Reject arbitrary resource-like objects.
        raise ValidationError("Game action resources are invalid")
    # Require one callable planner without invoking it.
    if not callable(planner):
        # Reject a missing or scalar planner.
        raise ValidationError("Game action planner is invalid")
