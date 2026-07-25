"""Explicit, idempotent conversion of a Guest Trial into a durable first-party Casino user. (#378)

A guest trial owns a `player_id` bound to a wallet, ledger, and history. Conversion creates a full local
account that adopts that same `player_id`, so the authoritative wallet, ledger, and game history are
preserved in place with no duplication and no orphaned ownership — there is nothing to migrate because
the player identity never changes; only the user identity is upgraded from guest to account.

Conversion is explicit and terminal: it requires the caller to be the authenticated guest, to supply a
unique mailbox, a policy-compliant password, and current terms acceptance, and it never happens silently.
It is recoverable and idempotent: if the response is lost and the guest retries, the same account is
returned rather than a second account or a duplicated wallet. No OAuth or provider identity is created,
and canonical identity remains the internal Casino user id.
"""

# Import the canonical identity, session, and player boundary.
from casino.core import auth
# Import the player wallet boundary so the preserved balance can be reported.
from casino.core import players
# Import the privacy-safe application audit facade.
from casino.core import logger
# Import the shared UTC clock for contract-compatible timestamps.
from casino.core.clock import utc_now
# Import atomic identity-document mutation for the terminal guest marker.
from casino.core.state_store import update_json
# Import standard bounded application errors.
from casino.errors import ConflictError, ValidationError


# Verify the caller is an active, unconverted guest trial before any account side effect.
def _require_active_guest(guest) -> dict:
    # Reject a missing or non-guest principal so only a guest can convert its own trial.
    if not auth.is_guest(guest or {}):
        # Fail closed without disclosing account internals.
        raise ValidationError("Conversion requires an active guest trial", {"reason": "not_a_guest"})
    # Reject a guest whose trial is no longer active.
    if str((guest or {}).get("status") or "") != "active":
        # Fail closed on an ended or expired trial.
        raise ValidationError("Conversion requires an active guest trial", {"reason": "guest_inactive"})
    # Return the validated guest principal.
    return guest


# Resolve the account this guest was already converted into, if any, for idempotent replay.
def _already_converted(guest) -> dict | None:
    # Read the durable conversion marker written on a completed conversion.
    target_user_id = str((guest or {}).get("converted_to_user_id") or "")
    # Report no prior conversion when the marker is absent.
    if not target_user_id:
        # Signal a first-time conversion.
        return None
    # Look up the account the guest was converted into.
    for user in auth.load_users().get("users", []):
        # Match the durable target account id.
        if user.get("user_id") == target_user_id:
            # Return the already-created account for a byte-stable replay.
            return user
    # Treat a dangling marker as no conversion so a genuine retry can complete.
    return None


# Find any full account that already adopted this guest's player, proving a partial prior attempt.
def _account_on_player(player_id: str) -> dict | None:
    # Scan for a non-guest account already bound to the guest's player.
    for user in auth.load_users().get("users", []):
        # Match a durable account that adopted the same player and is not itself a guest.
        if user.get("player_id") == player_id and not auth.is_guest(user):
            # Return the account created by a prior interrupted attempt.
            return user
    # Report no account has adopted the player yet.
    return None


# Emit one privacy-safe audit event carrying no raw internal identifier in user-facing copy.
def _audit(event: str, **fields) -> None:
    # Record only bounded non-secret provenance fields.
    logger.info(event, **fields)


# Mark the guest record terminal so it leaves the trial lifecycle and can never reconvert.
def _mark_guest_converted(guest_user_id: str, account_user_id: str, when: str) -> None:
    # Mutate only the specific guest record inside the identity document.
    def mutate(user: dict) -> dict:
        # Record the durable conversion link and terminal timestamps.
        user.update({"status": "converted", "converted_to_user_id": account_user_id, "converted_at": when, "updated_at": when})
        # Return the mutated guest record.
        return user
    # Persist the terminal marker through the atomic identity transaction.
    auth.update_user_by_id(guest_user_id, mutate)


# Build the published conversion result without exposing raw internal identifiers in copy.
def _result(account: dict, *, replayed: bool) -> dict:
    # Read the preserved wallet so the caller can confirm the balance carried over.
    wallet = players.get_player(account["player_id"])
    # Publish the account email, display name, preserved balance, and whether this was a replay.
    return {"status": "converted", "replayed": replayed, "email": account["email"], "display_name": account["display_name"], "balance": wallet["balance"], "player_preserved": True}


# Convert an authenticated guest trial into a durable full first-party account.
def convert(guest, email: str, password: str, display_name: str, *, terms_version: str = "", accepted: bool = False, locale: str = "en-US", idempotency_key: str = "") -> dict:
    # Return the already-created account first so a completed conversion replays even once the guest is terminal.
    prior = _already_converted(guest or {})
    # Publish the stable replay result for a completed conversion before any active-guest requirement.
    if prior is not None:
        # Return the byte-stable replay without touching identity state again.
        return _result(prior, replayed=True)
    # Require the caller to be an active guest before any validation that could leak account state.
    _require_active_guest(guest)
    # Read the guest's durable player binding once; conversion preserves it exactly.
    player_id = str(guest.get("player_id") or "")
    # Fail closed when a guest somehow has no bound player, since there is nothing to preserve.
    if not player_id:
        # Reject an unbound guest rather than creating an orphan account.
        raise ValidationError("Guest trial has no wallet to preserve", {"reason": "no_player"})
    # Require explicit current terms acceptance so conversion is never silent or automatic.
    if accepted is not True:
        # Fail closed until the caller explicitly accepts the account terms.
        raise ValidationError("Conversion requires explicit terms acceptance", {"reason": "terms_required"})
    # Enforce the shared enrollment password policy before creating any identity.
    try:
        # Apply the canonical enrollment password rules.
        auth.validate_enrollment_password(str(password or ""))
    # Convert a policy violation into a bounded validation error.
    except Exception:
        # Fail closed without disclosing which rule failed.
        raise ValidationError("Password does not meet the account policy", {"reason": "weak_password"})
    # Normalize the requested mailbox once.
    normalized = auth.normalize_email(str(email or ""))
    # Reject a malformed mailbox before any account side effect.
    if not normalized or normalized.count("@") != 1:
        # Fail closed on an unusable mailbox.
        raise ValidationError("A valid email is required", {"reason": "invalid_email"})
    # Recover a completed-but-unmarked conversion from an interrupted prior attempt.
    existing_account = _account_on_player(player_id)
    # Treat an account already bound to this player as the idempotent target.
    if existing_account is not None:
        # Require the recovered account to match the requested mailbox so a different email cannot hijack it.
        if existing_account.get("email") != normalized:
            # Fail closed on a conflicting retry rather than creating a second account.
            raise ConflictError("Guest wallet is already bound to a different account")
        # Complete the interrupted conversion by writing the terminal guest marker.
        _mark_guest_converted(guest["user_id"], existing_account["user_id"], utc_now())
        # Record the recovered completion for operators.
        _audit("guest_conversion_recovered", account_user_id=existing_account["user_id"], player_id=player_id)
        # Return the stable replay result.
        return _result(existing_account, replayed=True)
    # Create the full local account adopting the guest's existing player so the wallet and ledger persist.
    account = auth.create_user(normalized, str(password), str(display_name or "").strip() or normalized, role="player", player_id=player_id, terms_required=False, locale=locale if locale in ("en-US", "ru-RU") else "en-US")
    # Record the account's explicit terms acceptance on the durable identity.
    auth.accept_terms(account["user_id"], str(terms_version or ""), True)
    # Capture the completion time once for consistent terminal markers.
    when = utc_now()
    # Mark the guest record terminal and linked so it leaves the trial lifecycle and stays out of Admin Users.
    _mark_guest_converted(guest["user_id"], account["user_id"], when)
    # Revoke any resumable guest session so the disposable trial credential can never be reused.
    auth.revoke_sessions_for_user(guest["user_id"])
    # Record the successful conversion with only bounded provenance fields.
    _audit("guest_conversion_completed", guest_user_id=guest["user_id"], account_user_id=account["user_id"], player_id=player_id)
    # Return the completed conversion result.
    return _result(account, replayed=False)
