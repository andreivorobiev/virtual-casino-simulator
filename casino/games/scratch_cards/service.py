"""Ledger-only, retry-safe orchestration for player-owned Scratch Cards."""

# Import deep-copy support so failed actions cannot mutate a loader-owned state object.
import copy
# Import cryptographic bounded selection for production ticket outcomes.
import secrets
# Import one process-wide reentrant lock for local state and ledger idempotency.
import threading

# Import the only approved play-token mutation service.
from casino.core import ledger
# Import the shared UTC clock for stable purchase and settlement timestamps.
from casino.core.clock import utc_now
# Import player-scoped persistence helpers without changing shared storage code.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import standard conflict, insufficient-funds, and not-found domain errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError
# Import pure Scratch Cards rules and public-state sanitization.
from casino.games.scratch_cards import engine

# Serialize the complete local read-modify-ledger-write path against duplicate requests.
_ACTION_LOCK = threading.RLock()
# Scan a generous player-local window so restart retries find committed action keys.
LEDGER_IDEMPOTENCY_SCAN_LIMIT = 1000000


# Reduce one internal ledger event to correlation fields safe for action responses.
def public_ledger_event(event: dict | None) -> dict | None:
    # Preserve null when this action has no wager or positive payout event.
    if not event:
        # Avoid inventing a zero-value ledger transaction.
        return None
    # Publish only stable transaction evidence and exclude private/internal details.
    public_fields = ("ledger_id", "ts", "amount", "transaction_type", "game", "round_id")
    # Copy available fields without exposing fingerprints, action keys, or covered ticket values.
    return {field: event.get(field) for field in public_fields if field in event}


# Adapt the existing shared ledger into a game-local apply-once action interface.
class CoreLedgerGateway:
    # Find one previously committed action for the authenticated player.
    def find(self, player_id: str, action_key: str) -> dict | None:
        # Read only this player's ledger so cross-session details are never inspected.
        rows = ledger.read_recent(player_id, LEDGER_IDEMPOTENCY_SCAN_LIMIT)
        # Scan newest-first for the deterministic private action identity.
        return next((row for row in reversed(rows) if (row.get("details") or {}).get("idempotency_key") == action_key), None)

    # Commit one debit or credit exactly once for the intended single-process simulator.
    def apply_once(self, *, player_id: str, amount: float, transaction_type: str, card_id: str, action_key: str, details: dict) -> tuple[dict, bool]:
        # Serialize the ledger read-before-write sequence against concurrent duplicates.
        with _ACTION_LOCK:
            # Resolve any committed event before issuing a balance mutation.
            existing = self.find(player_id, action_key)
            # Branch when a retry already committed this action.
            if existing:
                # Validate player, game, and card ownership before returning an event.
                if existing.get("player_id") != player_id or existing.get("game") != engine.GAME_ID or existing.get("round_id") != card_id:
                    # Fail closed rather than returning a colliding ledger row.
                    raise ConflictError("Scratch Card ledger action identity conflicts with another event")
                # Reject one action key reused for a different amount or transaction type.
                if round(float(existing.get("amount", 0)), 2) != round(float(amount), 2) or existing.get("transaction_type") != transaction_type:
                    # Preserve one immutable financial meaning per idempotency key.
                    raise ConflictError("Scratch Card ledger action identity conflicts with an existing event")
                # Read recovered private details once for semantic conflict checks.
                existing_details = existing.get("details") or {}
                # Reject a changed purchase fingerprint even when amounts happen to match.
                if existing_details.get("request_fingerprint") != details.get("request_fingerprint"):
                    # Preserve purchase identity across semantically different requests.
                    raise ConflictError("Scratch Card action identity was already used with different content")
                # Reject a changed public action id on a recovered purchase or payout.
                if existing_details.get("action_id") != details.get("action_id"):
                    # Prevent another reveal command from claiming a committed payout.
                    raise ConflictError("Scratch Card action identity conflicts with the committed ledger event")
                # Return the original atomic event and explicit replay evidence.
                return existing, True
            # Add the private deterministic key before the shared atomic ledger transaction.
            event_details = {**details, "idempotency_key": action_key}
            # Route the signed amount through the existing debit or credit service only.
            event = ledger.debit(player_id, abs(amount), transaction_type, engine.GAME_ID, card_id, event_details) if amount < 0 else ledger.credit(player_id, amount, transaction_type, engine.GAME_ID, card_id, event_details)
            # Return the newly committed event and non-replay evidence.
            return event, False


# Coordinate private ticket state, deterministic entropy, and ledger-only settlement.
class ScratchCardsService:
    # Capture injectable seams so focused tests avoid filesystem, wallet, time, and entropy state.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_saver=None, randbelow=None, clock=None):
        # Use the game-local ledger adapter unless a focused test supplies a fake.
        self.ledger_gateway = ledger_gateway or CoreLedgerGateway()
        # Use player-scoped storage compatible with the shared authenticated resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(engine.GAME_ID, player_id, engine.default_state))
        # Persist private game state without mutating any shared state module.
        self.state_saver = state_saver or (lambda player_id, state: save_player_game_state(engine.GAME_ID, player_id, state))
        # Use cryptographic bounded selection unless a focused test injects a deterministic sequence.
        self.randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins response timing.
        self.clock = clock or utc_now

    # Load an independent state copy so failures do not leak unsaved mutations through test adapters.
    def _load_state(self, player_id: str) -> dict:
        # Deep-copy nested cards, cells, and action records before modification.
        state = copy.deepcopy(self.state_loader(player_id))
        # Replace malformed stored payloads with a safe player-owned default.
        return state if isinstance(state, dict) else engine.default_state()

    # Build one sanitized response around the current private state.
    def _response(self, state: dict, card: dict | None = None, *, replayed: bool = False, wager_event=None, payout_event=None) -> dict:
        # Expose the explicitly targeted card or the state's current card through the masking boundary.
        public_card = engine.public_card(card if card is not None else state.get("current_card"))
        # Return game-owned data ready for the shared standard success envelope.
        return {"card": public_card, "state": engine.public_state(state), "replayed": replayed, "ledger": {"wager": public_ledger_event(wager_event), "payout": public_ledger_event(payout_event)}}

    # Return only the authenticated player's masked reload-safe state.
    def state(self, player_id: str) -> dict:
        # Serialize state reads with in-flight purchase and scratch transitions.
        with _ACTION_LOCK:
            # Load only the session-bound player's private game document.
            state = self._load_state(player_id)
            # Return no ledger rows and no hidden prize data.
            return engine.public_state(state)

    # Start or recover one wager-backed private card.
    def start_card(self, player_id: str, request: dict) -> dict:
        # Require an object payload before reading public fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state or ledger access.
            raise ValidationError("Scratch Card start body must be an object")
        # Validate the purchase retry identity required by the additive v1 contract.
        client_request_id = engine.normalize_action_id(request.get("client_request_id"), "client_request_id")
        # Normalize the selected play-token wager before private state access.
        wager = engine.normalize_wager(request.get("wager"))
        # Compute one semantic fingerprint that detects conflicting request reuse.
        request_fingerprint = engine.purchase_fingerprint(wager)
        # Serialize player-state preparation and ledger recovery as one local action.
        with _ACTION_LOCK:
            # Load one independent private player state document.
            state = self._load_state(player_id)
            # Resolve any current or retained card created by this request identity.
            existing_card = engine.find_purchase(state, client_request_id)
            # Branch when a prior attempt already prepared or completed this purchase.
            if existing_card:
                # Reject the same identity reused with a different normalized wager.
                if existing_card.get("request_fingerprint") != request_fingerprint:
                    # Fail closed before another ledger action can occur.
                    raise ConflictError("client_request_id was already used for a different Scratch Card wager")
                # Return completed purchases immediately without another entropy or ledger call.
                if existing_card.get("status") != "purchasing":
                    # Report the original masked card as a safe replay.
                    return self._response(state, existing_card, replayed=True, wager_event=None)
                # Reuse the persisted pre-debit plan after an interrupted purchase.
                card = existing_card
                # Remember that this request resumed an existing state intent.
                resumed_intent = True
            # Prepare a brand-new private ticket intent before moving play tokens.
            else:
                # Preserve the pre-action state so insufficient funds can remove a noncommitted intent.
                original_state = copy.deepcopy(state)
                # Archive a settled card or reject replacement of an unfinished card.
                engine.archive_current(state)
                # Derive a stable player-scoped card identity from the retry key.
                card_id = engine.card_id_for(player_id, client_request_id)
                # Generate the complete private board once through the injected entropy seam.
                ticket = engine.generate_ticket(wager, self.randbelow)
                # Build the persisted purchase intent without exposing private prizes publicly.
                card = {"card_id": card_id, "client_request_id": client_request_id, "request_fingerprint": request_fingerprint, "player_id": player_id, "status": "purchasing", "wager": wager, "revealed_positions": [], "scratch_actions": {}, "purchased_at": self.clock(), **ticket}
                # Make this prepared ticket the only current actionable card.
                state["current_card"] = card
                # Persist outcome and request mapping before the debit for reload-safe recovery.
                self.state_saver(player_id, state)
                # Mark this as the first execution of the prepared intent.
                resumed_intent = False
            # Build ledger details without private ticket values because player-visible ledger feeds expose details.
            debit_details = {"action_id": client_request_id, "request_fingerprint": request_fingerprint, "card_id": card["card_id"], "wager": wager}
            # Preserve the stable card identity for the deterministic ledger action key.
            card_id = card["card_id"]
            # Start protected debit handling so insufficient funds can remove an uncommitted intent.
            try:
                # Apply exactly one wager debit for this card through the shared ledger.
                debit_event, debit_replayed = self.ledger_gateway.apply_once(player_id=player_id, amount=-wager, transaction_type="SCRATCH_CARD_WAGER_DEBIT", card_id=card_id, action_key=f"scratch:{card_id}:wager", details=debit_details)
            # Roll back only the known no-commit insufficient-funds path.
            except InsufficientFundsError:
                # Restore the exact pre-action state for a newly prepared ticket.
                if not resumed_intent:
                    # Persist removal of the non-funded card intent.
                    self.state_saver(player_id, original_state)
                # Re-raise the canonical domain error for the standard envelope.
                raise
            # Restore a newly proposed board when an older ledger identity conflicts semantically.
            except ConflictError:
                # Roll back only when this call created a state intent not previously retained.
                if not resumed_intent:
                    # Preserve the exact state that existed before the conflicting late retry.
                    self.state_saver(player_id, original_state)
                # Re-raise the immutable ledger-identity conflict.
                raise
            # Fail closed when an expired state record collides with an older committed purchase.
            if debit_replayed and not resumed_intent:
                # Remove the newly proposed board because the original private outcome is no longer retained.
                self.state_saver(player_id, original_state)
                # Preserve exactly-once money behavior without substituting a rerolled ticket.
                raise ConflictError("Scratch Card purchase retry is older than retained game state")
            # Mark the persisted private card ready only after the wager event exists.
            card["status"] = "ready"
            # Preserve the shared ledger identifier for private recovery diagnostics.
            card["wager_ledger_id"] = debit_event.get("ledger_id")
            # Prefer the committed timestamp so retries preserve purchase timing.
            card["purchased_at"] = debit_event.get("ts") or card.get("purchased_at") or self.clock()
            # Persist the funded masked card after recovering committed private details.
            self.state_saver(player_id, state)
            # Return the masked card with exact ledger replay evidence.
            return self._response(state, card, replayed=resumed_intent or debit_replayed, wager_event=debit_event)

    # Reveal one or more positions and settle a completed card at most once.
    def scratch(self, player_id: str, card_id: str, request: dict) -> dict:
        # Require an object payload before reading public fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before private state access.
            raise ValidationError("Scratch Card reveal body must be an object")
        # Validate the retry identity for this exact reveal action.
        action_id = engine.normalize_action_id(request.get("action_id"), "action_id")
        # Validate and sort the requested zero-based positions.
        positions = engine.normalize_positions(request.get("positions"))
        # Compute one semantic fingerprint for conflicting action-id detection.
        action_fingerprint = engine.scratch_fingerprint(card_id, positions)
        # Serialize player state, action replay, and optional payout credit locally.
        with _ACTION_LOCK:
            # Load only the authenticated player's independent private state.
            state = self._load_state(player_id)
            # Resolve the card only inside this player's current or retained state.
            card = engine.find_card(state, card_id)
            # Return the same not-found shape for unknown and other-player card ids.
            if not card:
                # Avoid leaking whether another player owns the supplied digest.
                raise NotFoundError("Scratch Card was not found")
            # Read bounded action replay records from the private card.
            scratch_actions = card.setdefault("scratch_actions", {})
            # Resolve an earlier use of this public action identity.
            existing_action = scratch_actions.get(action_id)
            # Reject the same identity reused for another card-position meaning.
            if existing_action and existing_action.get("fingerprint") != action_fingerprint:
                # Fail closed without revealing or crediting another action.
                raise ConflictError("action_id was already used for different Scratch Card positions")
            # Return a completed or partial replay unless it must resume an interrupted settlement.
            if existing_action and not (card.get("status") == "settling" and card.get("completion_action_id") == action_id):
                # Preserve current reload-safe state while reporting action replay.
                return self._response(state, card, replayed=True)
            # Reject new commands after settlement or during another completion action.
            if not existing_action and card.get("status") in {"settled", "settling"}:
                # Prevent a second action identity from claiming the completed card.
                raise ConflictError("Scratch Card is already settling or settled")
            # Reject a fresh identity that does not authorize any newly covered cell.
            if not existing_action and not (set(positions) - set(card.get("revealed_positions", []))):
                # Keep successful action identities naturally bounded by the nine-cell card.
                raise ConflictError("Scratch Card positions are already revealed")
            # Track whether this call resumed a previously persisted completing action.
            resumed_action = existing_action is not None
            # Record a new partial or completing scratch intent before any payout credit.
            if not existing_action:
                # Union persisted and newly requested positions without hiding earlier progress.
                revealed_positions = sorted(set(card.get("revealed_positions", [])) | set(positions))
                # Store the canonical revealed set for reload-safe partial scratching.
                card["revealed_positions"] = revealed_positions
                # Record the bounded replay identity and semantic content.
                scratch_actions[action_id] = {"fingerprint": action_fingerprint, "positions": positions}
                # Branch when all nine cells now authorize final settlement.
                if len(revealed_positions) == engine.CELL_COUNT:
                    # Persist an explicit payout intent before touching the shared ledger.
                    card["status"] = "settling"
                    # Preserve the completing public action identity for crash recovery.
                    card["completion_action_id"] = action_id
                    # Preserve the exact final action positions for frontend retry after reload.
                    card["completion_positions"] = positions
                # Keep a partially scratched card active without a financial action.
                else:
                    # Publish a stable player-facing phase for reload and UI rendering.
                    card["status"] = "scratching"
                # Persist action identity and reveal progress before returning or crediting.
                self.state_saver(player_id, state)
            # Return a partial reveal immediately because no payout is yet known to the player.
            if card.get("status") != "settling":
                # Expose only newly authorized prize cells through the public masking boundary.
                return self._response(state, card, replayed=resumed_action)
            # Read the deterministic prize already committed with the wager event.
            payout = round(float(card.get("payout", 0.0)), 2)
            # Start with no credit event for a non-winning completed card.
            payout_event = None
            # Track financial replay independently from the scratch action record.
            payout_replayed = False
            # Branch when the revealed match-three card earns a positive prize.
            if payout > 0:
                # Build stable payout details tied to both purchase and completion identities.
                payout_details = {"action_id": card["completion_action_id"], "request_fingerprint": card["request_fingerprint"], "scratch_fingerprint": action_fingerprint, "card_id": card_id, "payout": payout, "winning_multiplier": card["winning_multiplier"]}
                # Apply at most one positive prize credit through the shared ledger.
                payout_event, payout_replayed = self.ledger_gateway.apply_once(player_id=player_id, amount=payout, transaction_type="SCRATCH_CARD_PAYOUT_CREDIT", card_id=card_id, action_key=f"scratch:{card_id}:payout", details=payout_details)
            # Mark the card terminal only after any required payout event has committed.
            card["status"] = "settled"
            # Preserve the shared payout ledger identifier without exposing private details.
            card["payout_ledger_id"] = payout_event.get("ledger_id") if payout_event else None
            # Prefer the committed credit time or the current injected time for a losing card.
            card["settled_at"] = (payout_event or {}).get("ts") or self.clock()
            # Persist the fully revealed terminal card for reload and history.
            self.state_saver(player_id, state)
            # Return all now-authorized prizes and exact replay evidence.
            return self._response(state, card, replayed=resumed_action or payout_replayed, payout_event=payout_event)
