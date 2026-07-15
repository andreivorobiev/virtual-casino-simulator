"""Session-bound, ledger-only orchestration for Acey-Deucey."""

# Import canonical JSON encoding for semantic retry fingerprints.
import json
# Import hashing for compact immutable request fingerprints.
import hashlib
# Import regular expressions for bounded action identities.
import re
# Import a reentrant lock for one-process state and ledger serialization.
import threading

# Import only the shared ledger and player boundaries allowed for games.
from casino.core import ledger, players
# Import the shared audit clock used by peer modules.
from casino.core.clock import utc_now
# Import player-scoped game state persistence.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict, lookup, and validation errors for API boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import this game's pure rules and state helpers.
from casino.games.acey_deucey import engine

# Use one canonical game id for storage, ledger, and payloads.
GAME_ID = engine.GAME_ID
# Bound public action ids to log-safe characters and conservative length.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Scan enough local ledger history for crash-recovery evidence.
LEDGER_SCAN_LIMIT = 1_000_000
# Serialize the supported local single-process action path.
_ACTION_LOCK = threading.RLock()


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


# Adapt the shared ledger into game-owned apply-once movement ids.
class CoreLedgerGateway:
    # Capture injectable functions for focused tests.
    def __init__(self, *, debit=ledger.debit, credit=ledger.credit, read_recent=ledger.read_recent):
        # Store the approved debit boundary.
        self._debit = debit
        # Store the approved credit boundary.
        self._credit = credit
        # Store player-scoped ledger lookup.
        self._read_recent = read_recent

    # Find one committed Acey-Deucey ledger action.
    def find(self, player_id: str, ledger_action_id: str):
        # Read only the bound player's recent ledger rows.
        rows = self._read_recent(player_id, LEDGER_SCAN_LIMIT)
        # Search newest-first for the game-owned action detail.
        return next((row for row in reversed(rows) if row.get("game") == GAME_ID and (row.get("details") or {}).get("acey_deucey_action_id") == ledger_action_id), None)

    # Commit or recover one signed movement exactly once.
    def apply_once(self, *, player_id: str, signed_amount: float, transaction_type: str, round_id: str, ledger_action_id: str, fingerprint: str, details: dict) -> tuple[dict, bool]:
        # Protect read-before-write from duplicate local requests.
        with _ACTION_LOCK:
            # Read any existing movement for this stable action.
            existing = self.find(player_id, ledger_action_id)
            # Reuse only an exact semantic match.
            if existing is not None:
                # Compare amount, transaction type, round id, and request fingerprint.
                matches = round(float(existing.get("amount", 0)), 2) == round(float(signed_amount), 2) and existing.get("transaction_type") == transaction_type and existing.get("round_id") == round_id and (existing.get("details") or {}).get("request_fingerprint") == fingerprint
                # Reject action-id reuse for a different movement.
                if not matches:
                    # Fail before any duplicate wallet mutation.
                    raise ConflictError("action_id was already used for a different Acey-Deucey ledger action")
                # Return immutable proof and replay evidence.
                return existing, True
            # Add recovery details required to identify this movement later.
            event_details = {**details, "acey_deucey_action_id": ledger_action_id, "request_fingerprint": fingerprint}
            # Route negative signed amounts through the debit function.
            if signed_amount < 0:
                # Commit the positive debit magnitude.
                event = self._debit(player_id, abs(signed_amount), transaction_type, GAME_ID, round_id, event_details)
            # Route positive signed amounts through the credit function.
            else:
                # Commit the returned-token credit.
                event = self._credit(player_id, signed_amount, transaction_type, GAME_ID, round_id, event_details)
            # Return the new movement and non-replay flag.
            return event, False


# Coordinate player state, deterministic cards, and ledger movements.
class AceyDeuceyService:
    # Capture production dependencies while exposing deterministic seams.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, get_player=None, clock=None, seed_factory=None):
        # Use the game-local ledger adapter unless tests inject a fake.
        self._ledger = ledger_gateway or CoreLedgerGateway()
        # Load one authenticated player's game document.
        self._load_state = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Save one authenticated player's game document.
        self._save_state = state_saver or (lambda player_id, state: save_player_game_state(GAME_ID, player_id, state))
        # Read current player state without mutating balances.
        self._get_player = get_player or players.get_player
        # Use the shared clock unless tests pin time.
        self._clock = clock or utc_now
        # Derive deterministic cards only through injected tests.
        self._seed_factory = seed_factory

    # Save the player-scoped state document.
    def _save(self, player_id: str, state: dict) -> None:
        # Delegate to the injected persistence boundary.
        self._save_state(player_id, state)

    # Build one public response payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return state, player snapshot, and immutable rules.
        return {
            "game": GAME_ID,  # Identify this isolated module.
            "state": engine.public_state(state),  # Hide unrevealed result cards.
            "player": self._get_player(player_id),  # Publish the bound player's wallet snapshot.
            "rules": {  # Publish the exact proposal rules profile.
                "decks": 1,  # Use one standard deck per deal.
                "wager_timing": "after_boundaries_before_third_card",  # Distinguish from ante-first Red Dog.
                "inside_return_multiplier": 2,  # Return stake plus even-money profit.
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
                # Reject missing proof because the service cannot invent a debit after reveal.
                if event is None:
                    # Fail closed before exposing inconsistent terminal state.
                    raise ConflictError("Acey-Deucey wager ledger proof is unavailable")
                # Mark the recovered wager complete.
                round_state["wager_status"] = "complete"
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
            state = self._load_state(player_id)
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
            state = self._load_state(player_id)
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
            state = self._load_state(player_id)
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
            # Apply or recover the required wager debit.
            wager_event, wager_replayed = self._ensure_wager(player_id, state, round_state)
            # Apply or recover the optional winning payout.
            payout_event, payout_replayed = self._ensure_payout(player_id, state, round_state)
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
            state = self._load_state(player_id)
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
