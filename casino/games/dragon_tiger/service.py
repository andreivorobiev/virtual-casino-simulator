"""Reload-safe, ledger-only orchestration for Dragon Tiger rounds."""

# Import deep-copy support for rollback before an uncommitted wager.
import copy
# Import action-ID validation for bounded public retry identities.
import re
# Import process-local locks for single-server exactly-once reconciliation.
import threading

# Import the only approved wallet mutation service and player reader.
from casino.core import ledger, players
# Import the shared UTC clock for deterministic settlement timestamps.
from casino.core.clock import utc_now
# Import player-scoped persistent state helpers.
from casino.core.state_store import load_player_game_state, save_player_game_state
# Import public conflict and validation errors.
from casino.errors import ConflictError, InsufficientFundsError, ValidationError
# Import only this game's pure rules engine.
from casino.games.dragon_tiger import engine

# Require eight to 128 safe action-ID characters.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
# Scan all practical local ledger history for restart recovery.
LEDGER_SCAN_LIMIT = 1_000_000
# Serialize ledger read-before-write operations in this local process.
_LEDGER_LOCK = threading.RLock()
# Serialize state preparation and reconciliation in this local process.
_ACTION_LOCK = threading.RLock()


# Validate one required public retry identity.
def require_action_id(value) -> str:
    # Accept only an exact contract string without trimming caller data.
    action_id = value if isinstance(value, str) else ""
    # Reject missing, short, oversized, or unsafe values.
    if not ACTION_ID_PATTERN.fullmatch(action_id):
        # Explain the contract without echoing caller data.
        raise ValidationError("Dragon Tiger action_id must be 8-128 letters, numbers, dots, colons, underscores, or hyphens")
    # Return the validated identity unchanged.
    return action_id


# Persist player-scoped game documents through the shared provider abstraction.
class StateRepository:
    # Load one authenticated player's document.
    def load(self, player_id: str) -> dict:
        # Delegate JSON/MySQL selection and schema metadata to shared state storage.
        return load_player_game_state(engine.GAME_ID, player_id, engine.default_state)

    # Save one authenticated player's document.
    def save(self, player_id: str, state: dict) -> None:
        # Delegate atomic file replacement or provider storage.
        save_player_game_state(engine.GAME_ID, player_id, state)


# Adapt the shared ledger to stable apply-once game actions.
class CoreLedgerGateway:
    # Find one previously committed action for this authenticated player.
    def find(self, player_id: str, action_key: str) -> dict | None:
        # Read only the player's own append-only history.
        events = ledger.read_recent(player_id, LEDGER_SCAN_LIMIT)
        # Search newest-first for the stable game action key.
        return next((event for event in reversed(events) if (event.get("details") or {}).get("idempotency_key") == action_key), None)

    # Verify that prior ledger proof matches the retried semantic action.
    def validate_existing(self, event: dict, *, amount: float, transaction_type: str, round_id: str, fingerprint: str) -> None:
        # Reject a key reused for a different signed movement.
        if round(float(event.get("amount", 0)), 2) != round(float(amount), 2):
            # Fail closed instead of returning unrelated wallet movement.
            raise ConflictError("Dragon Tiger ledger action conflicts with an existing amount")
        # Reject a key reused for another event type or round.
        if event.get("transaction_type") != transaction_type or event.get("round_id") != round_id or event.get("game") != engine.GAME_ID:
            # Keep action keys one game movement only.
            raise ConflictError("Dragon Tiger ledger action conflicts with an existing event")
        # Read structured details defensively.
        details = event.get("details") or {}
        # Reject conflicting request content even when amounts match.
        if details.get("request_fingerprint") != fingerprint:
            # Preserve one semantic request per public action ID.
            raise ConflictError("Dragon Tiger action_id was already used with different round settings")

    # Commit or recover one deterministic debit or credit.
    def apply_once(self, *, player_id: str, amount: float, transaction_type: str, round_id: str, action_key: str, fingerprint: str, details: dict) -> tuple[dict, bool]:
        # Serialize lookup and mutation in the local single-server process.
        with _LEDGER_LOCK:
            # Find prior append-only proof before touching the balance.
            existing = self.find(player_id, action_key)
            # Reuse a compatible committed event on retry.
            if existing:
                # Validate all stable semantic fields.
                self.validate_existing(existing, amount=amount, transaction_type=transaction_type, round_id=round_id, fingerprint=fingerprint)
                # Return original proof and replay status.
                return existing, True
            # Add deterministic identity fields to the committed details.
            event_details = {**details, "idempotency_key": action_key, "request_fingerprint": fingerprint}
            # Route negative amounts through the shared debit function.
            if amount < 0:
                # Commit the atomic wager debit.
                event = ledger.debit(player_id, abs(amount), transaction_type, engine.GAME_ID, round_id, event_details)
            # Route positive amounts through the shared credit function.
            else:
                # Commit the atomic returned stake and winnings.
                event = ledger.credit(player_id, amount, transaction_type, engine.GAME_ID, round_id, event_details)
            # Return new proof and non-replay status.
            return event, False


# Coordinate prepared state, deterministic dealing, and ledger recovery.
class DragonTigerService:
    # Capture injectable ports for deterministic focused tests.
    def __init__(self, *, repository=None, ledger_gateway=None, player_reader=None, shoe_factory=None, clock=None):
        # Use shared persistent state unless a test supplies memory storage.
        self.repository = repository or StateRepository()
        # Use the shared ledger adapter unless a test supplies a recorder.
        self.ledger = ledger_gateway or CoreLedgerGateway()
        # Use the shared player reader unless a test supplies a fixture.
        self.player_reader = player_reader or players.get_player
        # Use secure production shuffle unless a test supplies a full deterministic shoe.
        self.shoe_factory = shoe_factory or engine.standard_shoe
        # Use the shared UTC clock unless a test pins time.
        self.clock = clock or utc_now

    # Build immutable wager ledger details sufficient for crash reconstruction.
    def _wager_details(self, prepared: dict) -> dict:
        # Return all rule-result data needed after state loss.
        return {
            "action_id": prepared["action_id"],  # Preserve public retry identity.
            "bet": prepared["bet"],  # Preserve normalized bet.
            "wager": prepared["wager"],  # Preserve committed amount.
            "dragon_card": prepared["dragon_card"],  # Preserve first card.
            "tiger_card": prepared["tiger_card"],  # Preserve second card.
            "winner": prepared["winner"],  # Preserve descriptive result.
            "outcome": prepared["outcome"],  # Preserve settlement class.
            "total_return": prepared["total_return"],  # Preserve calculated credit.
            "net": prepared["net"],  # Preserve net result.
            "created_at": prepared["created_at"],  # Preserve stable timing.
            "shoe_number": prepared["shoe_number"],  # Preserve shoe context.
            "profile": engine.PROFILE_ID,  # Preserve named rules provenance.
        }

    # Build settlement details for one optional credit.
    def _settlement_details(self, prepared: dict) -> dict:
        # Return audit context without private shoe order.
        return {
            "action_id": prepared["action_id"],  # Link the public action.
            "bet": prepared["bet"],  # Record selected main bet.
            "wager": prepared["wager"],  # Record original debit.
            "winner": prepared["winner"],  # Record rank-only result.
            "outcome": prepared["outcome"],  # Record settlement class.
            "total_return": prepared["total_return"],  # Record credit amount.
        }

    # Store one recovered prepared action before possible credit movement.
    def _store_prepared(self, player_id: str, state: dict, prepared: dict) -> None:
        # Store the private action by retry identity.
        state.setdefault("prepared_actions", {})[prepared["action_id"]] = prepared
        # Preserve creation order without duplicate entries.
        if prepared["action_id"] not in state.setdefault("prepared_order", []):
            # Append only a missing action identity.
            state["prepared_order"].append(prepared["action_id"])
        # Persist before any remaining ledger movement.
        self.repository.save(player_id, state)

    # Reconcile one prepared action through wager and optional settlement proof.
    def _reconcile(self, player_id: str, state: dict, prepared: dict, *, include_recent: bool = True) -> dict:
        # Derive stable action identities from the deterministic round ID.
        wager_key = f"{prepared['round_id']}:wager"
        # Read the durable pre-movement stage before deciding whether a retry may write.
        stage = prepared.get("status", "prepared")
        # Fail closed when a prior debit attempt has no append-only proof.
        if stage == "wager_attempting":
            # Search for proof that the attempted debit completed atomically enough to recover.
            wager_event = self.ledger.find(player_id, wager_key)
            # Never repeat an ambiguous shared-ledger movement without evidence.
            if wager_event is None:
                # Require shared-ledger or Admin reconciliation before this action can continue.
                raise ConflictError("Dragon Tiger wager outcome is uncertain and requires ledger reconciliation")
            # Validate recovered proof against the exact semantic action.
            self.ledger.validate_existing(wager_event, amount=-prepared["wager"], transaction_type="DRAGON_TIGER_WAGER_DEBIT", round_id=prepared["round_id"], fingerprint=prepared["request_fingerprint"])
            # Mark the recovered movement as a replay.
            wager_replayed = True
        # Recover known wager proof after the debit stage completed.
        elif stage in {"wager_committed", "settlement_attempting"}:
            # Require the append-only debit proof promised by the persisted stage.
            wager_event = self.ledger.find(player_id, wager_key)
            # Reject corrupt or partially lost stage/evidence combinations.
            if wager_event is None:
                # Fail closed instead of drawing or debiting again.
                raise ConflictError("Dragon Tiger wager evidence is unavailable and requires ledger reconciliation")
            # Validate the recovered movement before trusting its result details.
            self.ledger.validate_existing(wager_event, amount=-prepared["wager"], transaction_type="DRAGON_TIGER_WAGER_DEBIT", round_id=prepared["round_id"], fingerprint=prepared["request_fingerprint"])
            # Mark the known movement as a replay.
            wager_replayed = True
        # Begin one new debit only from the never-attempted prepared stage.
        elif stage == "prepared":
            # Persist intent before calling a shared ledger whose balance/event writes are not one file transaction.
            prepared["status"] = "wager_attempting"
            # Make an ambiguous provider failure fail closed on every later retry.
            self._store_prepared(player_id, state, prepared)
            # Commit or recover the single wager debit.
            wager_event, wager_replayed = self.ledger.apply_once(player_id=player_id, amount=-prepared["wager"], transaction_type="DRAGON_TIGER_WAGER_DEBIT", round_id=prepared["round_id"], action_key=wager_key, fingerprint=prepared["request_fingerprint"], details=self._wager_details(prepared))
        # Reject unknown private state rather than making a wallet movement.
        else:
            # Keep corrupted stage values from bypassing retry safety.
            raise ConflictError("Dragon Tiger prepared action stage is invalid")
        # Rebuild from committed proof so post-debit retries cannot change cards.
        canonical = engine.prepared_from_ledger(player_id=player_id, action_id=prepared["action_id"], fingerprint=prepared["request_fingerprint"], round_id=prepared["round_id"], details=wager_event.get("details") or {}, fallback_created_at=wager_event.get("ts") or prepared["created_at"])
        # Preserve a prior settlement-attempt marker or record completed wager proof.
        canonical["status"] = "settlement_attempting" if stage == "settlement_attempting" else "wager_committed"
        # Persist canonical committed result before a possible credit.
        self._store_prepared(player_id, state, canonical)
        # Start with no settlement event for full losses.
        settlement_event = None
        # Track whether an existing credit was recovered.
        settlement_replayed = False
        # Credit only positive returned stake or winnings.
        if canonical["total_return"] > 0:
            # Derive a separate stable settlement action key.
            settlement_key = f"{canonical['round_id']}:settlement"
            # Recover proof rather than repeating an ambiguous prior credit attempt.
            if stage == "settlement_attempting":
                # Search for the append-only evidence associated with the attempted credit.
                settlement_event = self.ledger.find(player_id, settlement_key)
                # Never repeat a possibly completed credit when its evidence is absent.
                if settlement_event is None:
                    # Require explicit reconciliation for this safely blocked action.
                    raise ConflictError("Dragon Tiger settlement outcome is uncertain and requires ledger reconciliation")
                # Validate recovered credit proof against the immutable wager result.
                self.ledger.validate_existing(settlement_event, amount=canonical["total_return"], transaction_type="DRAGON_TIGER_SETTLEMENT_CREDIT", round_id=canonical["round_id"], fingerprint=canonical["request_fingerprint"])
                # Report that the settlement came from prior proof.
                settlement_replayed = True
            # Begin one new credit only after persisting its pre-movement stage.
            else:
                # Record intent before calling the shared balance/event storage boundary.
                canonical["status"] = "settlement_attempting"
                # Make an ambiguous credit failure fail closed on later retry.
                self._store_prepared(player_id, state, canonical)
                # Commit or recover the at-most-one settlement credit.
                settlement_event, settlement_replayed = self.ledger.apply_once(player_id=player_id, amount=canonical["total_return"], transaction_type="DRAGON_TIGER_SETTLEMENT_CREDIT", round_id=canonical["round_id"], action_key=settlement_key, fingerprint=canonical["request_fingerprint"], details=self._settlement_details(canonical))
        # Prefer immutable wager timing for stable retry responses.
        settled_at = wager_event.get("ts") or canonical["created_at"] or self.clock()
        # Convert private action data into the exact public contract.
        round_item = engine.settled_round(canonical, settled_at)
        # Group immutable movement proof for durable action-key replay.
        ledger_evidence = {"wager": wager_event, "settlement": settlement_event}
        # Archive the settled round and remove private action state.
        engine.record_round(state, round_item, ledger_evidence, include_recent=include_recent)
        # Persist terminal state after all required movements commit.
        self.repository.save(player_id, state)
        # Return public round, proof, and replay status.
        return {"round": round_item, "ledger": ledger_evidence, "replayed": wager_replayed or settlement_replayed}

    # Recover all persisted actions before serving state or starting another round.
    def _recover_all(self, player_id: str, state: dict) -> None:
        # Snapshot order because reconciliation removes completed entries.
        for action_id in list(state.get("prepared_order", [])):
            # Resolve the corresponding private action defensively.
            prepared = state.get("prepared_actions", {}).get(action_id)
            # Ignore stale order entries while cleaning them below.
            if not prepared:
                # Remove a stale recovery identity.
                state["prepared_order"] = [item for item in state.get("prepared_order", []) if item != action_id]
                # Continue to the next prepared action.
                continue
            # Finish only a previously persisted player action.
            self._reconcile(player_id, state, prepared)

    # Build the shared GET/POST base payload.
    def _payload(self, player_id: str, state: dict) -> dict:
        # Return exact public state, current player, and fixed rules.
        return {"game": engine.GAME_ID, "state": engine.public_state(state), "player": self.player_reader(player_id), "rules": engine.rules_payload()}

    # Return reload-safe state after recovering interrupted actions.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against concurrent duplicate requests.
        with _ACTION_LOCK:
            # Load only this authenticated player's state.
            state = self.repository.load(player_id)
            # Finish actions already requested before interruption.
            self._recover_all(player_id, state)
            # Return the exact public state contract.
            return self._payload(player_id, state)

    # Execute or replay one single-bet Dragon Tiger round.
    def play(self, player_id: str, request: dict) -> dict:
        # Require an object before reading request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state access.
            raise ValidationError("Dragon Tiger round body must be an object")
        # Accept only the documented action plus the ignored v1 compatibility identity.
        if any(key not in {"action_id", "bet", "wager", "player_id"} for key in request):
            # Keep undocumented inputs out of semantic retry processing.
            raise ValidationError("Dragon Tiger round body contains unsupported fields")
        # Validate the public retry identity.
        action_id = require_action_id(request.get("action_id"))
        # Normalize the single main bet.
        bet = engine.normalize_bet(request.get("bet"))
        # Normalize the wager at ledger precision.
        wager = engine.normalize_wager(request.get("wager"))
        # Build semantic conflict-detection proof.
        fingerprint = engine.request_fingerprint(bet, wager)
        # Derive the stable player-scoped round ID.
        round_id = engine.round_id_for(player_id, action_id)
        # Serialize preparation, ledger lookup, and state persistence.
        with _ACTION_LOCK:
            # Load a detached document so failed preparation cannot leak mutations.
            state = copy.deepcopy(self.repository.load(player_id))
            # Recover earlier persisted actions before accepting a new one.
            self._recover_all(player_id, state)
            # Replay a settled response from bounded state first.
            existing_action = engine.find_action_record(state, action_id)
            # Read the immutable public round from the durable action record.
            existing_round = existing_action.get("round") if existing_action else None
            # Handle a normal duplicate request.
            if existing_round:
                # Reject the same action ID with different normalized input.
                if engine.request_fingerprint(existing_round["bet"], existing_round["wager"]) != fingerprint:
                    # Preserve one semantic action per identity.
                    raise ConflictError("Dragon Tiger action_id was already used with different round settings")
                # Recover ledger proof for the replay response.
                wager_event = (existing_action.get("ledger") or {}).get("wager") or self.ledger.find(player_id, f"{round_id}:wager")
                # Recover optional settlement proof.
                settlement_event = (existing_action.get("ledger") or {}).get("settlement") or self.ledger.find(player_id, f"{round_id}:settlement")
                # Return stable public data without drawing again.
                return {**self._payload(player_id, state), "round": existing_round, "ledger": {"wager": wager_event, "settlement": settlement_event}, "replayed": True}
            # Resolve a private prepared retry when present.
            prepared = state.setdefault("prepared_actions", {}).get(action_id)
            # Reject conflicting reuse of persisted private state.
            if prepared and prepared.get("request_fingerprint") != fingerprint:
                # Keep the action identity immutable.
                raise ConflictError("Dragon Tiger action_id was already used with different round settings")
            # Preserve the pre-round shoe and state for uncommitted debit rollback.
            prior_state = copy.deepcopy(state)
            # Recover even when bounded state was lost or pruned by reading stable debit proof first.
            committed_wager = self.ledger.find(player_id, f"{round_id}:wager")
            # Track whether recovery came from ledger proof without a durable state index.
            ledger_only_recovery = prepared is None and committed_wager is not None
            # Rebuild the original result without consuming another shoe card.
            if prepared is None and committed_wager:
                # Validate the prior debit against this normalized retry.
                self.ledger.validate_existing(committed_wager, amount=-wager, transaction_type="DRAGON_TIGER_WAGER_DEBIT", round_id=round_id, fingerprint=fingerprint)
                # Reconstruct cards and settlement from immutable ledger details.
                prepared = engine.prepared_from_ledger(player_id=player_id, action_id=action_id, fingerprint=fingerprint, round_id=round_id, details=committed_wager.get("details") or {}, fallback_created_at=committed_wager.get("ts") or self.clock())
                # Persist recovered private state before an optional credit.
                self._store_prepared(player_id, state, prepared)
            # Deal and persist one new deterministic result when no proof exists.
            if prepared is None:
                # Prepare cards, comparison, and settlement entirely before ledger mutation.
                prepared = engine.prepare_action(state, player_id=player_id, action_id=action_id, bet=bet, wager=wager, fingerprint=fingerprint, round_id=round_id, created_at=self.clock(), shoe_factory=self.shoe_factory)
                # Persist prepared shoe/result state before the wager debit.
                self.repository.save(player_id, state)
            # Reconcile the prepared action through the ledger.
            try:
                # Commit or recover the debit and possible credit.
                result = self._reconcile(player_id, state, prepared, include_recent=not ledger_only_recovery)
            # Roll back only when no wager movement committed.
            except InsufficientFundsError:
                # A rejected shared debit is definitive and cannot have changed the balance.
                if self.ledger.find(player_id, f"{round_id}:wager") is None:
                    # Restore shoe and prepared state so a later funded action can proceed normally.
                    self.repository.save(player_id, prior_state)
                # Preserve the shared insufficient-funds response.
                raise
            # Preserve fail-closed movement stages for every ambiguous provider failure.
            except Exception:
                # Read the current private stage after any pre-ledger intent save.
                current = state.get("prepared_actions", {}).get(action_id) or {}
                # Check append-only proof in case failure followed a successful debit.
                if current.get("status") not in {"wager_attempting", "settlement_attempting"} and self.ledger.find(player_id, f"{round_id}:wager") is None:
                    # Restore shoe and action state after validation or insufficient funds failure.
                    self.repository.save(player_id, prior_state)
                # Re-raise the original domain or provider error.
                raise
            # Return POST additions beside the shared base payload.
            return {**self._payload(player_id, state), **result}
