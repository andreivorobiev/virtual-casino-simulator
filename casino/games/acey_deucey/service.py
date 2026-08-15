# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only orchestration for Acey-Deucey."""

# Import deep-copy support for detached optimistic state snapshots.
import copy
# Import canonical JSON encoding for semantic retry fingerprints.
import json
# Import hashing for compact immutable request fingerprints.
import hashlib
# Import regular expressions for bounded action identities.
import re
# Import a reentrant lock for one-process state and ledger serialization.
import threading

# Import only the shared player boundary allowed for game reads.
from casino.core import players
# Import the shared audit clock used by peer modules.
from casino.core.clock import utc_now
# Import the one canonical game-money compatibility boundary.
from casino.core.settlement import GameSettlementGateway
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict, lookup, and validation errors for API boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import this game's pure rules and state helpers.
from casino.games.acey_deucey import engine

# Use one canonical game id for storage, ledger, and payloads.
GAME_ID = engine.GAME_ID
# Bound public action ids to log-safe characters and conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Serialize the supported local single-process action path.
_ACTION_LOCK = threading.RLock()
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_acey_deucey_atomic_baseline"
# Name every state field owned by Acey-Deucey transitions.
_GAME_STATE_KEYS = ("active_round", "recent_rounds", "action_receipts")


# Validate one required client action identity.
def require_action_id(value) -> str:
    # Accept only bounded strings with URL-safe punctuation.
    if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
        # Return the stable public validation message.
        raise ValidationError("action_id must be 1-128 URL-safe characters")
    # Preserve the exact id for byte-for-byte retries.
    return value


# Build one canonical semantic request fingerprint.
def request_fingerprint(payload: dict) -> str:
    # Encode sorted compact JSON so insertion order cannot affect retries.
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    # Return a lowercase digest for persisted comparison.
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Construct the shared settlement gateway while retaining the historical test seam name.
def CoreLedgerGateway(**kwargs):
    # Preserve the old detail key for one compatibility release beside canonical evidence.
    return GameSettlementGateway(GAME_ID, "acey_deucey_action_id", **kwargs)


# Persist player-scoped game documents through the selected storage provider.
class StateRepository:
    # Load one authenticated player's document.
    def load(self, player_id: str) -> dict:
        # Delegate JSON/MySQL selection and defaults to shared state storage.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Apply one transition while the provider owns its cross-process boundary.
    def update(self, player_id: str, mutator) -> dict:
        # Delegate latest-state loading, rollback, and publication atomically.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state)


# Coordinate player state, deterministic cards, and ledger movements.
class AceyDeuceyService:
    # Capture production dependencies while exposing deterministic seams.
    def __init__(self, *, repository=None, ledger_gateway=None, get_player=None, clock=None, seed_factory=None):
        # Use shared persistent state unless a focused test supplies memory storage.
        self.repository = repository or StateRepository()
        # Use the game-local ledger adapter unless tests inject a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Read current player state without mutating balances.
        self._get_player = get_player or players.get_player
        # Use the shared clock unless tests pin time.
        self._clock = clock or utc_now
        # Derive deterministic cards only through injected tests.
        self._seed_factory = seed_factory

    # Capture only the fields owned by Acey-Deucey transitions.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Build one fresh compatibility baseline for absent predecessor fields.
        defaults = engine.default_state()
        # Detach nested rounds and receipts from later engine mutation.
        return {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}

    # Load one document and bind its optimistic game-owned baseline.
    def _load(self, player_id: str) -> dict:
        # Read through the injected repository before provider mutation.
        state = self.repository.load(player_id)
        # Retain the exact game-owned values expected by the next publication.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting operation metadata.
        return state

    # Publish one provider-current compare-and-replace transition.
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a tracked provider read.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Reject fabricated or stale detached documents before storage access.
        if not isinstance(expected, dict):
            # Keep untracked state outside provider bytes.
            raise ConflictError("Acey-Deucey state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Acey-Deucey-owned fields on current state.
        def publish(current: dict) -> dict:
            # Detach provider-current game fields from unrelated siblings.
            observed = self._game_snapshot(current)
            # Accept an identical publication without rewriting siblings.
            if observed == desired:
                # Preserve the complete authoritative provider document.
                return current
            # Reject an operation whose game-owned baseline lost a race.
            if observed != expected:
                # Require recovery from the authoritative winning action.
                raise ConflictError("Acey-Deucey state changed during this action; reload and retry")
            # Replace only the fields governed by this game service.
            for key, value in desired.items():
                # Publish detached values so caller mutation cannot leak later.
                current[key] = copy.deepcopy(value)
            # Return the complete document with every sibling preserved.
            return current

        # Commit through the provider's cross-process mutation boundary.
        authoritative = self.repository.update(player_id, publish)
        # Advance the in-memory baseline to the exact committed result.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(authoritative)

    # Build one public response payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Build the authoritative complete price table once for this response.
        paytable = engine.inside_paytable()
        # Prefer the actionable round and otherwise retain the newest terminal price for old clients.
        pricing_round = state.get("active_round") or next(iter(reversed(state.get("recent_rounds", []))), None)
        # Read the visible spread without trusting an absent or malformed stored round.
        pricing_spread = pricing_round.get("inside_rank_count") if isinstance(pricing_round, dict) else None
        # Preserve the frozen-v1 scalar while making it describe the same current price as the paytable.
        legacy_multiplier = paytable.get(pricing_spread, 2)
        # Return state, player snapshot, and server-owned compatible rules.
        return {
            "game": GAME_ID,  # Identify this isolated module.
            "state": engine.public_state(state),  # Hide unrevealed result cards.
            "player": self._get_player(player_id),  # Publish the bound player's wallet snapshot.
            "rules": {  # Publish the exact proposal rules profile.
                "decks": 1,  # Use one standard deck per deal.
                "wager_timing": "after_boundaries_before_third_card",  # Distinguish from ante-first Red Dog.
                "inside_return_multiplier": legacy_multiplier,  # Retain the deprecated frozen-v1 scalar for the current or latest round.
                "inside_paytable": paytable,  # Publish the spread-priced return so clients never guess a price.
                "house_edge": engine.HOUSE_EDGE,  # State the constant edge the spread pricing holds at every spread. (issue #408)
                "outside_return_multiplier": 0,  # Outside ranks lose the play wager.
                "boundary_tie_return_multiplier": 0,  # Matching either boundary loses the play wager.
                "pair_boundaries_have_no_inside_ranks": True,  # Explain equal-boundary edge cases.
            },
        }

    # Recover committed debit or payout markers after reload.
    def _recover(self, player_id: str, state: dict) -> None:
        # Inspect terminal rounds retained in recent history.
        for round_state in state.get("recent_rounds", []):
            # Recover a missing wager marker only for played rounds.
            if round_state.get("wager_status") == "pending" and round_state.get("play_action_id"):
                # Build the stable wager ledger action id.
                wager_action = f"ad:{round_state['play_action_id']}:wager"
                # Find append-only wager proof for this player.
                event = self._ledger.find(player_id, wager_action)
                # Restore the original private decision when the debit provably never committed.
                if event is None:
                    # Roll back the revealed terminal shape without changing the wallet.
                    engine.restore_uncommitted_play(state, round_state)
                    # Persist cleanup so every endpoint becomes usable again.
                    self._save(player_id, state)
                    # Continue because this history item is now restored as the active round.
                    continue
                # Mark the recovered wager complete.
                round_state["wager_status"] = "complete"
                # Discard rollback material because append-only proof makes the terminal result authoritative.
                round_state.pop("_third_card", None)
                # Store immutable ledger proof id.
                round_state["wager_ledger_id"] = event.get("ledger_id")
                # Persist the recovered marker.
                self._save(player_id, state)
            # Recover a pending payout for strict inside wins.
            if round_state.get("settlement_status") == "pending":
                # Ensure the owed payout exactly once.
                self._ensure_payout(player_id, state, round_state)

    # Ensure one wager debit exists for a settled play.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict) -> tuple[dict, bool]:
        # Build a distinct ledger id beneath the public play action.
        ledger_action_id = f"ad:{round_state['play_action_id']}:wager"
        # Commit or recover the wager debit.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=-round_state["wager"], transaction_type="ACEY_DEUCEY_WAGER_DEBIT", round_id=round_state["round_id"], ledger_action_id=ledger_action_id, fingerprint=round_state["play_fingerprint"], details={"stage": "play_wager", "wager": round_state["wager"], "left_card": round_state["left_card"], "right_card": round_state["right_card"]})
        # Mark debit completion only after proof exists.
        round_state["wager_status"] = "complete"
        # Discard private rollback material after the wager is durably committed.
        round_state.pop("_third_card", None)
        # Store the immutable ledger id for evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the marker for reload safety.
        self._save(player_id, state)
        # Return proof and replay flag.
        return event, replayed

    # Ensure one payout credit exists for a winning play.
    def _ensure_payout(self, player_id: str, state: dict, round_state: dict) -> tuple[dict | None, bool]:
        # Skip losing and passed rounds without zero-value ledger rows.
        if not round_state.get("payout"):
            # Mark settlement complete when no credit is owed.
            round_state["settlement_status"] = "complete"
            # Persist terminal no-credit state.
            self._save(player_id, state)
            # Return no event and no replay.
            return None, False
        # Build a distinct payout action id beneath the public play action.
        ledger_action_id = f"ad:{round_state['play_action_id']}:payout"
        # Commit or recover the returned-token credit.
        event, replayed = self._ledger.apply_once(player_id=player_id, signed_amount=round_state["payout"], transaction_type="ACEY_DEUCEY_PAYOUT_CREDIT", round_id=round_state["round_id"], ledger_action_id=ledger_action_id, fingerprint=round_state["play_fingerprint"], details={"stage": "inside_payout", "wager": round_state["wager"], "left_card": round_state["left_card"], "right_card": round_state["right_card"], "third_card": round_state["third_card"], "outcome": round_state["outcome"]})
        # Mark settlement complete only after proof exists.
        round_state["settlement_status"] = "complete"
        # Store immutable payout proof.
        round_state["settlement_ledger_id"] = event.get("ledger_id")
        # Persist the marker for reload safety.
        self._save(player_id, state)
        # Return proof and replay flag.
        return event, replayed

    # Read reload-safe state for one authenticated player.
    def state(self, player_id: str) -> dict:
        # Serialize recovery with local action handling.
        with _ACTION_LOCK:
            # Load the player-scoped state document.
            state = self._load(player_id)
            # Recover any committed ledger markers.
            self._recover(player_id, state)
            # Return sanitized state and rules.
            return self._payload(player_id, state)

    # Deal or replay two free boundary cards.
    def deal(self, player_id: str, request: dict) -> dict:
        # Require a JSON object body.
        if not isinstance(request, dict):
            # Reject malformed bodies before state access.
            raise ValidationError("Acey-Deucey deal body must be an object")
        # Validate the free-deal action id.
        action_id = require_action_id(request.get("action_id"))
        # Fingerprint the deal stage without caller identity fields.
        fingerprint = request_fingerprint({"stage": "deal"})
        # Serialize state preparation and receipt persistence.
        with _ACTION_LOCK:
            # Load the bound player's latest document.
            state = self._load(player_id)
            # Recover retained markers before enforcing active-round rules.
            self._recover(player_id, state)
            # Load durable action receipts.
            receipts = state.setdefault("action_receipts", {})
            # Replay an existing deal with the same fingerprint.
            existing = engine.round_for_deal_action(state, action_id)
            # Return the same round when this is an exact retry.
            if existing is not None:
                # Reject changed semantic ownership.
                if existing.get("request_fingerprint") != fingerprint:
                    # Preserve the original deal.
                    raise ConflictError("action_id was already used for another Acey-Deucey deal")
                # Restore the durable receipt.
                receipts[action_id] = {"stage": "deal", "round_id": existing["round_id"], "request_fingerprint": fingerprint}
                # Persist the restored receipt.
                self._save(player_id, state)
                # Return the original public round.
                return {"round": engine.public_round(existing), "replayed": True, **self._payload(player_id, state)}
            # Reject action ids retained for pruned or different commands.
            if action_id in receipts:
                # Keep one action id bound to one semantic command.
                raise ConflictError("action_id was already used for another Acey-Deucey action")
            # Require the current boundary deal to be closed first.
            if state.get("active_round") is not None:
                # Prevent overlapping hidden third cards.
                raise ConflictError("Finish the active Acey-Deucey round before dealing again")
            # Derive deterministic cards only from the injected test seam.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Deal two boundaries and one hidden third card.
            left_card, right_card, third_card = engine.deal_cards(seed=seed)
            # Derive a stable route id from session player and action id.
            round_id = engine.round_id_for(player_id, action_id)
            # Build prepared state before any player action.
            round_state = engine.create_round(player_id, action_id, left_card=left_card, right_card=right_card, third_card=third_card, round_id=round_id, created_at=self._clock(), request_fingerprint=fingerprint)
            # Store the active boundary decision.
            state["active_round"] = round_state
            # Store the durable deal receipt.
            receipts[action_id] = {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}
            # Persist the hidden result for reload-safe play.
            self._save(player_id, state)
            # Return public state without revealing the third card.
            return {"round": engine.public_round(round_state), "replayed": False, **self._payload(player_id, state)}
    # Play or replay one wager against an active boundary deal.
    def play(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object body.
        if not isinstance(request, dict):
            # Reject malformed bodies before state access.
            raise ValidationError("Acey-Deucey play body must be an object")
        # Validate the public play action id.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the wager before fingerprinting.
        wager = engine.normalize_wager(request.get("wager"))
        # Bind the play action to round and amount.
        fingerprint = request_fingerprint({"stage": "play", "round_id": round_id, "wager": wager})
        # Serialize reveal and wallet movements.
        with _ACTION_LOCK:
            # Load the bound player's state.
            state = self._load(player_id)
            # Recover previous ledger markers first.
            self._recover(player_id, state)
            # Resolve the round only inside this player document.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session ids identically.
            if round_state is None:
                # Return stable not-found behavior.
                raise NotFoundError("Acey-Deucey round was not found")
            # Load durable receipts.
            receipts = state.setdefault("action_receipts", {})
            # Build expected receipt for this exact play.
            expected_receipt = {"stage": "play", "round_id": round_id, "request_fingerprint": fingerprint}
            # Reject action ids already used for another semantic command.
            if action_id in receipts and receipts[action_id] != expected_receipt:
                # Fail before reveal or ledger movement.
                raise ConflictError("action_id was already used for another Acey-Deucey action")
            # Replay an already-settled exact play.
            if round_state.get("phase") == "settled":
                # Require the original action and fingerprint.
                if round_state.get("play_action_id") != action_id or round_state.get("play_fingerprint") != fingerprint:
                    # Reject a changed terminal retry.
                    raise ConflictError("Acey-Deucey round was already settled by another action")
                # Restore a compatible receipt.
                receipts[action_id] = expected_receipt
                # Recover or replay the debit and optional payout.
                wager_event, wager_replayed = self._ensure_wager(player_id, state, round_state)
                # Recover or replay the payout.
                payout_event, payout_replayed = self._ensure_payout(player_id, state, round_state)
                # Return the stable terminal result.
                return {"round": engine.public_round(round_state), "wager": wager_event, "settlement": payout_event, "replayed": True, "ledger_replayed": wager_replayed or payout_replayed, **self._payload(player_id, state)}
            # Require this exact round to remain active.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent archived or corrupted state from becoming playable.
                raise ConflictError("Only the active Acey-Deucey round can accept a play wager")
            # Reveal and calculate the deterministic terminal state.
            engine.play_round(round_state, wager, action_id, completed_at=self._clock(), request_fingerprint=fingerprint)
            # Store the durable play receipt before wallet movement.
            receipts[action_id] = expected_receipt
            # Archive the terminal result before applying ledger movements.
            engine.archive_round(state, round_state)
            # Persist terminal reveal and pending ledger markers.
            self._save(player_id, state)
            # Protect rollback so a rejected debit cannot strand terminal state.
            try:
                # Apply or recover the required wager debit.
                wager_event, wager_replayed = self._ensure_wager(player_id, state, round_state)
                # Apply or recover the optional winning payout.
                payout_event, payout_replayed = self._ensure_payout(player_id, state, round_state)
            # Restore only a play proven to have no committed wager movement.
            except Exception:
                # Build the exact append-only wager identity beneath this play action.
                wager_action = f"ad:{action_id}:wager"
                # Check proof before removing any terminal recovery state.
                if self._ledger.find(player_id, wager_action) is None:
                    # Restore the free prepared decision and release the uncommitted receipt.
                    engine.restore_uncommitted_play(state, round_state)
                    # Persist rollback before propagating the original ledger error.
                    self._save(player_id, state)
                # Preserve committed movements and the original public error.
                raise
            # Return revealed state and ledger proof.
            return {"round": engine.public_round(round_state), "wager": wager_event, "settlement": payout_event, "replayed": wager_replayed or payout_replayed, **self._payload(player_id, state)}

    # Pass or replay one active boundary deal without wallet movement.
    def pass_round(self, player_id: str, round_id: str, request: dict) -> dict:
        # Require a JSON object body.
        if not isinstance(request, dict):
            # Reject malformed bodies before state access.
            raise ValidationError("Acey-Deucey pass body must be an object")
        # Validate the pass action id.
        action_id = require_action_id(request.get("action_id"))
        # Bind the pass to the target round.
        fingerprint = request_fingerprint({"stage": "pass", "round_id": round_id})
        # Serialize terminal state persistence.
        with _ACTION_LOCK:
            # Load the bound player's state.
            state = self._load(player_id)
            # Recover any retained ledger markers first.
            self._recover(player_id, state)
            # Resolve the player-owned round.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-session ids identically.
            if round_state is None:
                # Return stable not-found behavior.
                raise NotFoundError("Acey-Deucey round was not found")
            # Load durable receipts.
            receipts = state.setdefault("action_receipts", {})
            # Build expected pass receipt.
            expected_receipt = {"stage": "pass", "round_id": round_id, "request_fingerprint": fingerprint}
            # Reject action reuse across commands.
            if action_id in receipts and receipts[action_id] != expected_receipt:
                # Fail before closing another round.
                raise ConflictError("action_id was already used for another Acey-Deucey action")
            # Replay an exact previous pass.
            if round_state.get("phase") == "passed":
                # Require original pass identity.
                if round_state.get("pass_action_id") != action_id or round_state.get("pass_fingerprint") != fingerprint:
                    # Reject changed pass retries.
                    raise ConflictError("Acey-Deucey round was already passed by another action")
                # Restore the compatible receipt.
                receipts[action_id] = expected_receipt
                # Persist the restored receipt.
                self._save(player_id, state)
                # Return the stable passed round.
                return {"round": engine.public_round(round_state), "replayed": True, **self._payload(player_id, state)}
            # Require this exact round to be active.
            if not state.get("active_round") or state["active_round"].get("round_id") != round_id:
                # Prevent closing archived or corrupt state.
                raise ConflictError("Only the active Acey-Deucey round can be passed")
            # Close the round without revealing the third card.
            engine.pass_round(round_state, action_id, completed_at=self._clock(), request_fingerprint=fingerprint)
            # Store the pass receipt.
            receipts[action_id] = expected_receipt
            # Archive the passed round.
            engine.archive_round(state, round_state)
            # Persist terminal state.
            self._save(player_id, state)
            # Return passed state with no ledger proof.
            return {"round": engine.public_round(round_state), "replayed": False, **self._payload(player_id, state)}
