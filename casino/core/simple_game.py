# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared exactly-once wager-and-settle core for catalog games. (#73 expansion)

Every ledger-backed game repeats the same subtle money contract: draw server entropy, debit a wager,
settle deterministically, credit any return, and stay retry-safe across a lost response or a crashed
process. Re-implementing that per game multiplies the surface for money bugs. This core owns it once so a
game module supplies only its pure rules — a bet validator and a deterministic resolver — and inherits a
proven exactly-once settlement path.

The contract this core guarantees:

- One caller-stable request_id maps to one round; a retry replays the identical committed outcome.
- Server entropy is committed inside the wager ledger proof, so settlement is deterministic even when a
  crash forces recovery from the ledger alone.
- The wager debit and the settlement credit are each applied exactly once, guarded by ledger proof plus a
  request fingerprint, so the same identity can never move two different amounts.
- A request_id reused with different wager content fails closed as a conflict rather than double-spending.
"""

import hashlib
import re
import secrets
import threading

from casino.core import players
from casino.core.clock import utc_now
# Import the canonical game-money compatibility gateway owned by SettlementAdapter. (GAMECORE-004)
from casino.core.settlement import GameSettlementGateway
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.errors import ConflictError, ValidationError

# Bound request identifiers to conservative URL-safe characters and length.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize state, ledger proof, debit, settlement, and persistence per process.
_SETTLEMENT_LOCK = threading.RLock()
# Bound the retained per-player recent-round history so state stays compact.
RECENT_ROUND_LIMIT = 25


# Validate the caller-stable identity used for network and crash retries.
def require_request_id(value) -> str:
    # Require a bounded URL-safe string so the value is safe in logs, JSON, and hashes.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the exact validated identity for stable hashing and comparison.
    return value


# Derive one deterministic round identity from the game, player, and request id.
def round_id_for(game_id: str, player_id: str, request_id: str) -> str:
    # Return a bounded hex digest so the round id never carries caller-controlled structure.
    return hashlib.sha256(f"{game_id}\0{player_id}\0{request_id}".encode("utf-8")).hexdigest()[:24]


# Coordinate authenticated state, server entropy, and exactly-once ledger settlement for one game.
class SimpleWagerGame:
    # Configure the core with one game's identity, rules, and injectable test seams.
    def __init__(self, *, game_id, wager_transaction_type, settlement_transaction_type, entropy, resolve, validate_bet, public_bet_catalog=None, ledger_gateway=None, state_loader=None, state_updater=None, entropy_source=None, clock=None, get_player=None, request_id_resolver=None, round_id_factory=None, action_key_builder=None, wager_details_builder=None, wager_proof_reader=None, settlement_details_builder=None, public_round_builder=None, recent_round_limit=RECENT_ROUND_LIMIT, legacy_action_detail_key="idempotency_key", lifecycle=None) -> None:
        # Retain the fixed game identity used across every ledger and state dimension.
        self.game_id = str(game_id)
        # Retain the two aggregate transaction-type names used for recovery-stable proof.
        self.wager_transaction_type = str(wager_transaction_type)
        self.settlement_transaction_type = str(settlement_transaction_type)
        # Retain the pure callable that draws the game's server entropy from a random function.
        self._entropy = entropy
        # Retain the pure deterministic resolver mapping a validated bet plus entropy to a settlement.
        self._resolve = resolve
        # Retain the pure bet validator that normalizes caller input into an authoritative wager.
        self._validate_bet = validate_bet
        # Retain the optional public bet catalog builder for the state payload.
        self._public_bet_catalog = public_bet_catalog or (lambda: {})
        # Bind every production movement to SettlementAdapter while retaining the old detail key for one release.
        self._ledger_gateway = ledger_gateway or GameSettlementGateway(self.game_id, legacy_action_detail_key)
        # Use player-scoped production reads unless a test injects a detached loader.
        self._state_loader = state_loader or (lambda player_id: load_player_game_state(self.game_id, player_id, self._default_state))
        # Publish every settled-round append against provider-current state instead of a detached snapshot.
        self._state_updater = state_updater or (lambda player_id, mutator: update_player_game_state(self.game_id, player_id, mutator, self._default_state))
        # Use a cryptographic bounded random source unless a test pins entropy.
        self._entropy_source = entropy_source or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins settlement time.
        self._clock = clock or utc_now
        # Use the shared player read unless a test injects a wallet accessor.
        self._get_player = get_player or players.get_player
        # Preserve the standard request_id contract unless a legacy public route supplies an adapter.
        self._request_id_resolver = request_id_resolver or (lambda request: require_request_id(request.get("request_id")))
        # Preserve the standard game-scoped digest unless a legacy game has an established round identity.
        self._round_id_factory = round_id_factory or round_id_for
        # Preserve the standard wager/settlement action suffixes unless a legacy game names payout differently.
        self._action_key_builder = action_key_builder or (lambda round_id, action: f"{round_id}:{action}")
        # Preserve the canonical wager-proof detail shape unless a legacy ledger row needs compatible fields.
        self._wager_details_builder = wager_details_builder or self._default_wager_details
        # Preserve canonical proof recovery while allowing an established ledger shape to be decoded.
        self._wager_proof_reader = wager_proof_reader or self._default_wager_proof
        # Preserve canonical settlement details unless a legacy ledger contract needs compatible fields.
        self._settlement_details_builder = settlement_details_builder or self._default_settlement_details
        # Preserve the standard public round while allowing a game to retain its frozen response shape.
        self._public_round_builder = public_round_builder or self._default_public_round
        # Retain one optional game-owned lifecycle adapter for prepared-state compatibility.
        self._lifecycle = lifecycle
        # Retain one explicit positive history bound so adapted games preserve their established capacity.
        self._recent_round_limit = int(recent_round_limit)
        # Reject an invalid history policy at construction rather than truncating committed state unpredictably.
        if self._recent_round_limit <= 0:
            # Surface a programmer-facing configuration error before any action can move a wallet.
            raise ValueError("recent_round_limit must be positive")

    # Build the canonical wager proof used by every unadapted shared-helper game.
    @staticmethod
    def _default_wager_details(*, request_id, wager, entropy, settled_at, **_context) -> dict:
        # Return the exact pre-adapter proof shape for compatibility with existing ledger rows.
        return {"request_id": request_id, "wager": wager, "entropy": entropy, "settled_at": settled_at}

    # Decode one canonical committed wager proof without consulting tentative action state.
    @staticmethod
    def _default_wager_proof(*, details, **_context) -> dict:
        # Return only the authoritative inputs needed to reconstruct deterministic settlement.
        return {"wager": details.get("wager"), "entropy": details.get("entropy"), "settled_at": details.get("settled_at")}

    # Build the canonical settlement proof used by every unadapted shared-helper game.
    @staticmethod
    def _default_settlement_details(*, request_id, entropy, total_return, settlement, **_context) -> dict:
        # Return the exact pre-adapter settlement detail shape for stable audit rows.
        return {"request_id": request_id, "entropy": entropy, "total_return": total_return, "outcome": settlement.get("outcome")}

    # Build the canonical public round used by every unadapted shared-helper game.
    @staticmethod
    def _default_public_round(*, round_id, wager, wager_total, entropy, total_return, settlement, settled_at, **_context) -> dict:
        # Return the exact pre-adapter public response and persisted round shape.
        return {"round_id": round_id, "wager": wager, "wager_total": wager_total, "entropy": entropy, "total_return": total_return, "outcome": settlement.get("outcome"), "detail": settlement.get("detail", {}), "net": round(total_return - wager_total, 2), "settled_at": settled_at}

    # Build the empty per-player game document.
    def _default_state(self) -> dict:
        # Hold only this game's compact recent-round history.
        return {"game": self.game_id, "recent_rounds": []}

    # Build one deterministic ledger movement identity for a wager or settlement action.
    def _action_key(self, round_id: str, action: str) -> str:
        # Delegate to the standard or explicitly configured stable action-key builder.
        return self._action_key_builder(round_id, action)

    # Invoke one required method on an explicitly configured prepared-state lifecycle adapter.
    def _lifecycle_call(self, method: str, **context):
        # Skip lifecycle work for ordinary shared-simple games so their behavior remains byte-compatible.
        if self._lifecycle is None:
            # Report the absence of an adapter result to the caller.
            return None
        # Resolve the named stage without accepting a silently incomplete adapter.
        callback = getattr(self._lifecycle, method, None)
        # Reject a partial adapter before continuing a money-sensitive transition.
        if not callable(callback):
            # Surface a programmer-facing integration error rather than skipping recovery state.
            raise TypeError(f"SimpleWagerGame lifecycle is missing {method}")
        # Execute the game-owned state transition with only bounded authoritative context.
        return callback(**context)

    # Build the public state payload for one authenticated player.
    def state(self, player_id: str) -> dict:
        current = self._state_loader(player_id)
        return {"game": self.game_id, "state": current, "player": self._get_player(player_id), "bet_catalog": self._public_bet_catalog()}

    # Locate a prior round in state for replay detection.
    def _find_round(self, state: dict, request_id: str):
        for round_row in state.get("recent_rounds", []):
            if round_row.get("request_id") == request_id:
                return round_row
        return None

    # Publish one committed round without replacing a concurrent round or unrelated sibling field. (GAMECORE-005)
    def _publish_round(self, player_id: str, stored_round: dict) -> dict:
        # Bind immutable request identity before entering provider-owned mutable state.
        request_id = stored_round["request_id"]
        # Bind the request fingerprint used to reject changed-meaning reuse.
        fingerprint = stored_round["request_fingerprint"]

        # Merge the committed round into the exact current provider document.
        def publish(current: dict) -> dict:
            # Locate a same-request publication that may have won in another process.
            existing = self._find_round(current, request_id)
            # Treat an exact prior publication as an idempotent state replay.
            if existing is not None:
                # Reject a same request identity whose semantic wager changed.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail closed before replacing any provider-current state.
                    raise ConflictError(f"{self.game_id} request_id conflicts with a prior round")
                # Require state identity to agree with the ledger-derived committed round.
                if existing.get("round_id") != stored_round.get("round_id") or existing.get("public") != stored_round.get("public"):
                    # Refuse malformed or divergent state rather than concealing it as a replay.
                    raise ConflictError(f"{self.game_id} committed round conflicts with state")
                # Preserve the complete provider document byte-for-byte except provider-owned stamps.
                return current
            # Preserve an established game marker or restore it when an old document omitted the field.
            current.setdefault("game", self.game_id)
            # Prepend this distinct committed round to provider-current history and retain concurrent rows.
            current["recent_rounds"] = ([stored_round] + current.get("recent_rounds", []))[:self._recent_round_limit]
            # Return the complete provider-current document for atomic publication.
            return current

        # Execute the merge through the configured JSON/MySQL atomic document boundary.
        committed = self._state_updater(player_id, publish)
        # Re-read the exact committed row from provider-returned authority.
        published = self._find_round(committed, request_id)
        # Reject an updater that returned no exact publication.
        if published is None:
            # Fail closed instead of fabricating a successful state response.
            raise ConflictError(f"{self.game_id} committed round publication is missing")
        # Return the exact provider-owned stored round used by response and ledger reconstruction.
        return published

    # Execute or replay one atomic wager, entropy draw, and settlement for a player.
    def play(self, player_id: str, request: dict) -> dict:
        # Require the caller-stable retry identity before any state or ledger access.
        request_id = self._request_id_resolver(request or {})
        # Validate and normalize the caller's bet into an authoritative wager plus its total stake.
        wager, wager_total, fingerprint = self._validate_bet(request or {})
        # Reject a non-positive aggregate stake before touching the wallet.
        if wager_total <= 0:
            # Fail closed on an empty or malformed wager.
            raise ValidationError(f"{self.game_id} requires a positive wager")
        # Derive the deterministic round identity for this player and request.
        round_id = self._round_id_factory(self.game_id, player_id, request_id)
        # Serialize state cache, ledger proof, entropy, settlement, and persistence locally.
        with _SETTLEMENT_LOCK:
            # Load the player's current document once inside the lock.
            state = self._state_loader(player_id)
            # Resolve any prior round created by this exact request.
            existing = self._find_round(state, request_id)
            # Handle a replay of a previously settled round.
            if existing is not None:
                # Reject a request id reused with different wager content.
                if existing.get("request_fingerprint") != fingerprint:
                    # Fail closed rather than settling two outcomes under one identity.
                    raise ConflictError(f"{self.game_id} request_id conflicts with a prior round")
                # Rebuild the ledger events for the replayed round from committed proof.
                ledger_events = self._round_ledger(player_id, existing)
                # Return the identical replayed round with explicit replay evidence.
                return {"round": existing["public"], "replayed": True, "ledger": ledger_events, **self.state(player_id)}
            # Persist or recover optional game-owned preparation before any ledger movement.
            lifecycle_context = self._lifecycle_call("prepare", player_id=player_id, request=request or {}, request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=wager, wager_total=wager_total)
            # Preserve preparation replay evidence even if finalization returns a replacement context.
            lifecycle_replayed = bool((lifecycle_context or {}).get("replayed"))
            # Re-read terminal state after preparation because another process may have completed this action.
            if self._lifecycle is not None:
                # Load provider-current state after the lifecycle callback's atomic preparation.
                prepared_state = self._state_loader(player_id)
                # Resolve a same-request terminal round that won during the original read/preparation gap.
                prepared_existing = self._find_round(prepared_state, request_id)
                # Return the exact provider winner without repeating entropy or money work.
                if prepared_existing is not None:
                    # Reject a same identity whose semantic wager differs from provider authority.
                    if prepared_existing.get("request_fingerprint") != fingerprint:
                        # Fail closed before reading or returning another action's ledger proof.
                        raise ConflictError(f"{self.game_id} request_id conflicts with a prior round")
                    # Rebuild exact terminal movement evidence for the provider-owned round.
                    prepared_ledger = self._round_ledger(player_id, prepared_existing)
                    # Return the immutable winner with explicit state replay evidence.
                    return {"round": prepared_existing["public"], "replayed": True, "ledger": prepared_ledger, **self.state(player_id)}
            # Require configured lifecycle preparation to publish authoritative entropy and timing.
            if self._lifecycle is not None:
                # Reject a malformed lifecycle result before any wager can move tokens.
                if not isinstance(lifecycle_context, dict) or lifecycle_context.get("entropy") is None or not isinstance(lifecycle_context.get("settled_at"), str) or not lifecycle_context.get("settled_at"):
                    # Surface an integration error rather than drawing or timestamping behind prepared state.
                    raise TypeError("SimpleWagerGame lifecycle preparation is incomplete")
                # Reuse the exact entropy persisted or recovered by the lifecycle adapter.
                tentative_entropy = lifecycle_context["entropy"]
                # Reuse the prepared lifecycle timestamp for deterministic recovery.
                tentative_settled_at = lifecycle_context["settled_at"]
            else:
                # Draw tentative server entropy that becomes authoritative only if this request writes the wager proof.
                tentative_entropy = self._entropy(self._entropy_source)
                # Capture one tentative settlement timestamp alongside the entropy for exact crash-recovery replay.
                tentative_settled_at = self._clock()
            # Build the audit details that commit the wager, entropy, and public timestamp for deterministic recovery.
            wager_details = self._wager_details_builder(request_id=request_id, player_id=player_id, round_id=round_id, fingerprint=fingerprint, wager=wager, wager_total=wager_total, entropy=tentative_entropy, settled_at=tentative_settled_at, lifecycle_context=lifecycle_context)
            # Apply or recover the aggregate wager debit and retain its authoritative committed proof.
            try:
                # Commit or recover the aggregate wager through the one shared gateway boundary.
                wager_event, wager_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=-wager_total, transaction_type=self.wager_transaction_type, round_id=round_id, action_key=self._action_key(round_id, "wager"), request_fingerprint=fingerprint, details=wager_details)
            # Preserve the original action error after lifecycle-owned safe cleanup or retention.
            except Exception as error:
                # Start without committed proof when the wager failed before provider publication.
                committed_wager_event = None
                # Probe exact action proof only when a lifecycle adapter owns prepared cleanup.
                if self._lifecycle is not None:
                    # Read the immutable action using the same dimensions as the attempted wager.
                    try:
                        # Distinguish a lost response from a genuinely uncommitted wager.
                        committed_wager_event = self._ledger_gateway.find(player_id=player_id, round_id=round_id, transaction_type=self.wager_transaction_type, action_key=self._action_key(round_id, "wager"), request_fingerprint=fingerprint)
                    # Treat a conflicting proof as non-authorizing for this prepared request.
                    except ConflictError:
                        # Preserve the original conflict while allowing action-owned preparation cleanup.
                        committed_wager_event = None
                    # Let the adapter clear only an uncommitted preparation or retain committed recovery state.
                    self._lifecycle_call("wager_failed", player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=wager, wager_total=wager_total, lifecycle_context=lifecycle_context, committed_event=committed_wager_event, error=error)
                # Re-raise the original ledger or provider failure through the established API envelope.
                raise
            # Read only the committed proof because a retry's tentative entropy must never replace the first draw.
            committed_wager_details = wager_event.get("details") or {}
            # Decode the committed proof through the canonical or configured compatibility reader.
            committed_proof = self._wager_proof_reader(details=committed_wager_details, event=wager_event, request_id=request_id, player_id=player_id, round_id=round_id, fingerprint=fingerprint, proposed_wager=wager, lifecycle_context=lifecycle_context)
            # Recover the exact normalized wager recorded with the debit.
            committed_wager = committed_proof.get("wager")
            # Recover the exact entropy recorded before the first debit.
            entropy = committed_proof.get("entropy")
            # Recover the exact public timestamp recorded before the first debit.
            settled_at = committed_proof.get("settled_at")
            # Fail closed if a malformed proof cannot reconstruct the identical authoritative round.
            if committed_wager != wager or entropy is None or not isinstance(settled_at, str) or not settled_at:
                # Reject incomplete or inconsistent proof rather than redrawing or fabricating settlement state.
                raise ConflictError(f"{self.game_id} committed wager proof is incomplete")
            # Publish optional committed-wager recovery markers before calculating settlement intent.
            self._lifecycle_call("wager_committed", player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=committed_wager, wager_total=wager_total, entropy=entropy, settled_at=settled_at, lifecycle_context=lifecycle_context, wager_event=wager_event, replayed=wager_replayed)
            # Resolve the deterministic outcome from the committed wager and committed entropy.
            settlement = self._resolve(committed_wager, entropy)
            total_return = round(float(settlement.get("total_return", 0)), 2)
            # Publish optional deterministic result intent before any returned-credit movement.
            self._lifecycle_call("settlement_resolved", player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=committed_wager, wager_total=wager_total, entropy=entropy, total_return=total_return, settlement=settlement, settled_at=settled_at, lifecycle_context=lifecycle_context)
            # Start with no replayed settlement event for a losing round.
            settlement_replayed = False
            # Branch when the deterministic outcome returns any value to the wallet.
            if total_return > 0:
                # Build the settlement audit details from the committed round.
                settlement_details = self._settlement_details_builder(request_id=request_id, player_id=player_id, round_id=round_id, fingerprint=fingerprint, wager=committed_wager, wager_total=wager_total, entropy=entropy, total_return=total_return, settlement=settlement, settled_at=settled_at, lifecycle_context=lifecycle_context)
                # Commit the single aggregate credit exactly once.
                settlement_event, settlement_replayed = self._ledger_gateway.apply_once(player_id=player_id, amount=total_return, transaction_type=self.settlement_transaction_type, round_id=round_id, action_key=self._action_key(round_id, "settlement"), request_fingerprint=fingerprint, details=settlement_details)
                # Publish optional payout proof only after the credit exists immutably.
                self._lifecycle_call("settlement_committed", player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=committed_wager, wager_total=wager_total, entropy=entropy, total_return=total_return, settlement=settlement, settled_at=settled_at, lifecycle_context=lifecycle_context, settlement_event=settlement_event, replayed=settlement_replayed)
            # Freeze optional terminal lifecycle fields before building one cross-process-stable public round.
            finalized_context = self._lifecycle_call("finalize", player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, wager=committed_wager, wager_total=wager_total, entropy=entropy, total_return=total_return, settlement=settlement, settled_at=settled_at, lifecycle_context=lifecycle_context)
            # Adopt a lifecycle adapter's authoritative terminal context when it returns one.
            if finalized_context is not None:
                # Carry provider-owned terminal timestamps and evidence into the public round builder.
                lifecycle_context = finalized_context
            # Build the public round through the default or explicitly configured compatibility adapter.
            public_round = self._public_round_builder(request_id=request_id, player_id=player_id, round_id=round_id, fingerprint=fingerprint, wager=committed_wager, wager_total=wager_total, entropy=entropy, total_return=total_return, settlement=settlement, settled_at=settled_at, lifecycle_context=lifecycle_context)
            # Build the compact stored round with replay and fingerprint bookkeeping.
            stored_round = {"request_id": request_id, "request_fingerprint": fingerprint, "round_id": round_id, "total_return": total_return, "public": public_round}
            # Atomically merge the committed round into provider-current history.
            published_round = self._publish_round(player_id, stored_round)
            # Rebuild ledger proof from the exact provider-owned round identity.
            ledger_events = self._round_ledger(player_id, published_round)
            # Return the committed provider round while preserving the established response envelope.
            return {"round": published_round["public"], "replayed": lifecycle_replayed or wager_replayed or settlement_replayed, "ledger": ledger_events, **self.state(player_id)}

    # Rebuild the committed ledger events for one round from stored proof.
    def _round_ledger(self, player_id: str, stored_round: dict) -> dict:
        round_id = stored_round["round_id"]
        fingerprint = stored_round["request_fingerprint"]
        wager_event = self._ledger_gateway.find(player_id=player_id, round_id=round_id, transaction_type=self.wager_transaction_type, action_key=self._action_key(round_id, "wager"), request_fingerprint=fingerprint)
        # Start with no settlement proof for a losing round.
        settlement_event = None
        # Find a credit proof only when the round returned value.
        if stored_round.get("total_return", 0) > 0:
            settlement_event = self._ledger_gateway.find(player_id=player_id, round_id=round_id, transaction_type=self.settlement_transaction_type, action_key=self._action_key(round_id, "settlement"), request_fingerprint=fingerprint)
        return {"wager": wager_event, "settlement": settlement_event}
