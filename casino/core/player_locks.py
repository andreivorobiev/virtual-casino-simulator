# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Bounded process-local player lock striping for settlement and recovery paths."""

# Hash player identities deterministically so stripe selection is stable across processes and test runs.
import hashlib
# Build reentrant locks because recovery helpers may re-enter the same player's protected path.
import threading


# Keep one bounded lock array instead of retaining an unbounded lock per player identity. (GAMECORE-009)
class PlayerLockStriper:
    """Map player identities onto a fixed set of reentrant process-local locks."""

    # Allocate the fixed stripe set once for the lifetime of this registry.
    def __init__(self, stripe_count: int = 257) -> None:
        # Reject an unusable registry configuration at construction time.
        if not isinstance(stripe_count, int) or isinstance(stripe_count, bool) or stripe_count <= 0:
            # Surface a programmer-facing configuration error before any action can run.
            raise ValueError("stripe_count must be a positive integer")
        # Retain the immutable stripe count for deterministic selection and evidence.
        self._stripe_count = stripe_count
        # Build a bounded tuple of reentrant locks so same-player recovery remains safe.
        self._locks = tuple(threading.RLock() for _index in range(stripe_count))

    # Expose the fixed registry size for boundedness evidence.
    @property
    def stripe_count(self) -> int:
        # Return the immutable number of allocated locks.
        return self._stripe_count

    # Select one deterministic stripe without retaining the player identity.
    def stripe_index(self, player_id: str) -> int:
        # Require the established non-empty player identity before lock acquisition.
        if not isinstance(player_id, str) or not player_id:
            # Reject malformed internal calls without aliasing them onto a shared fallback lock.
            raise ValueError("player_id must be a non-empty string")
        # Hash the complete UTF-8 identity with a domain-separated fixed digest.
        digest = hashlib.blake2b(player_id.encode("utf-8"), digest_size=8, person=b"casino-player").digest()
        # Map the stable unsigned digest onto the bounded stripe array.
        return int.from_bytes(digest, "big") % self._stripe_count

    # Return the reentrant stripe that protects one player's local settlement path.
    def lock_for(self, player_id: str):
        # Select and return the existing stripe without growing registry state.
        return self._locks[self.stripe_index(player_id)]


# Share one bounded registry across games so a player's wallet actions have one process-local order.
_PLAYER_ACTION_LOCKS = PlayerLockStriper()


# Resolve the process-local lock used by game state, recovery, and settlement paths.
def player_action_lock(player_id: str):
    """Return one player's stripe before provider/JSON locks; never acquire a second player stripe."""

    # Lock order is player stripe, then provider transaction or JSON global gate, never the reverse.
    return _PLAYER_ACTION_LOCKS.lock_for(player_id)
