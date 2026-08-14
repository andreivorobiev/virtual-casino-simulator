# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
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

# Import hashing so caller-stable idempotency keys are stored only as one-way fingerprints.
import hashlib

# Import the canonical identity, session, and player boundary.
from casino.core import auth
# Import de-identified lifecycle closure for every successful conversion path.
from casino.core import guest_analytics
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


# Atomically record account terms acceptance and the terminal guest conversion marker.
def _complete_conversion(guest_user_id: str, account_user_id: str, terms_version: str, when: str, idempotency_hash: str) -> dict:
    # Capture the committed account outside the provider transaction.
    result = {"account": None}
    # Mutate both identities inside their shared JSON/MySQL document transaction.
    def mutate_state(state: dict) -> dict:
        # Reject malformed identity storage rather than replacing recoverable account data.
        if not isinstance(state, dict) or not isinstance(state.get("users"), list):
            # Preserve the original identity document for operator recovery.
            raise RuntimeError("Authentication user storage is malformed")
        # Resolve the exact guest and account records inside the locked document.
        guest = next((user for user in state["users"] if user.get("user_id") == guest_user_id), None)
        # Resolve only the durable target account selected by the conversion.
        account = next((user for user in state["users"] if user.get("user_id") == account_user_id and not auth.is_guest(user)), None)
        # Fail closed when either side of the conversion disappeared.
        if guest is None or account is None:
            # Preserve the original document for a recoverable retry.
            raise ValidationError("Guest conversion identity is unavailable", {"reason": "identity_unavailable"})
        # Reject a concurrent completion that selected a different durable account.
        if guest.get("converted_to_user_id") and guest.get("converted_to_user_id") != account_user_id:
            # Preserve the first committed account owner.
            raise ConflictError("Guest wallet is already bound to a different account")
        # Reject a different operation key after another completion won the terminal marker.
        if guest.get("conversion_idempotency_hash") and guest.get("conversion_idempotency_hash") != idempotency_hash:
            # Preserve the first committed conversion operation.
            raise ConflictError("Guest conversion idempotency key conflicts with the completed operation")
        # Record explicit accepted terms on the durable account in the same transaction.
        account.update({"terms_required": False, "terms_accepted_at": when, "terms_accepted_version": terms_version, "terms_acceptance_source": "guest_conversion", "updated_at": when})
        # Record the durable conversion link and terminal timestamps.
        guest.update({"status": "converted", "converted_to_user_id": account_user_id, "converted_at": when, "conversion_idempotency_hash": idempotency_hash, "updated_at": when})
        # Stamp the canonical schema version before persistence.
        state["schema_version"] = auth.SCHEMA_VERSION
        # Publish a detached account result after the transaction commits.
        result["account"] = dict(account)
        # Return the complete identity document for atomic provider persistence.
        return state
    # Persist terms and terminal identity state as one recoverable provider transaction.
    update_json(auth.USERS_PATH, mutate_state, auth.default_users)
    # Return the committed account with accepted terms metadata.
    return result["account"]


# Build the published conversion result without exposing raw internal identifiers in copy.
def _result(account: dict, *, replayed: bool) -> dict:
    # Read the preserved wallet so the caller can confirm the balance carried over.
    wallet = players.get_player(account["player_id"])
    # Publish the account email, display name, preserved balance, and whether this was a replay.
    return {"status": "converted", "replayed": replayed, "email": account["email"], "display_name": account["display_name"], "balance": wallet["balance"], "player_preserved": True}


# Close de-identified conversion telemetry after durable identity ownership commits. (GUEST-007)
def _close_conversion_analytics(guest: dict, result: dict) -> bool:
    # Read only the server-issued analytics reference from the canonical guest principal.
    analytics_id = str((guest or {}).get("guest_analytics_id") or "")
    # Skip legacy guests without analytics rather than affecting their completed conversion.
    if not analytics_id:
        # Preserve the committed account and wallet as the authoritative outcome.
        return False
    # Keep de-identified product telemetry outside the identity and money commit boundary.
    try:
        # Close the one analytics row idempotently with the exact preserved ending balance.
        guest_analytics.record_ended(analytics_id, "converted", ending_balance=result["balance"])
        # Confirm the analytics service accepted or idempotently replayed the projection.
        return True
    # Defer an unavailable analytics projection without converting success into an account failure.
    except Exception:
        # Best-effort logging must also remain unable to affect the committed conversion result.
        try:
            # Record only the bounded event class, never exception, identity, path, or credential content.
            logger.warning("guest_conversion_analytics_deferred", analytics_id_present=True)
        # Ignore a secondary audit sink failure because exact replay retries analytics closure.
        except Exception:
            # Intentionally preserve the already-committed identity and wallet outcome.
            pass
        # Report the deferred projection only to the internal recovery loop.
        return False


# Publish one conversion result and converge its recoverable analytics projection. (GUEST-007)
def _final_result(guest: dict, account: dict, *, replayed: bool) -> dict:
    # Read the authoritative adopted wallet before recording its de-identified terminal aggregate.
    result = _result(account, replayed=replayed)
    # Attempt analytics closure after durable conversion, including every exact replay path.
    _close_conversion_analytics(guest, result)
    # Return the unchanged public conversion result regardless of telemetry availability.
    return result


# Reconcile committed conversion markers into analytics without repeating identity or wallet work. (GUEST-007)
def reconcile_conversion_analytics() -> int:
    # Read one canonical identity snapshot so guest and account ownership are compared consistently.
    users = auth.load_users().get("users", [])
    # Index only durable non-guest accounts by their server-issued identity.
    accounts = {str(user.get("user_id") or ""): user for user in users if not auth.is_guest(user)}
    # Count rows already terminal or successfully converged for bounded internal evidence.
    reconciled = 0
    # Inspect only disposable identities carrying a committed conversion marker.
    for guest in users:
        # Skip active, ended, malformed, and non-guest identities before reading account state.
        if not auth.is_guest(guest) or guest.get("status") != "converted" or not guest.get("converted_to_user_id"):
            # Continue without creating or changing any identity or wallet record.
            continue
        # Resolve the exact durable account named by the terminal guest marker.
        account = accounts.get(str(guest.get("converted_to_user_id") or ""))
        # Require both identities to retain the same adopted player before analytics convergence.
        if account is None or str(account.get("player_id") or "") != str(guest.get("player_id") or ""):
            # Preserve inconsistent ownership for operator recovery rather than guessing a balance.
            continue
        # Read only the current authoritative wallet aggregate outside identity mutation.
        try:
            # Capture the exact adopted account balance for terminal de-identified reporting.
            balance = players.get_player(account["player_id"])["balance"]
        # Skip an unavailable wallet without affecting Admin reads or conversion ownership.
        except Exception:
            # A later Admin read or explicit replay can retry the projection safely.
            continue
        # Retry only the idempotent analytics projection; this helper never invokes conversion.
        if _close_conversion_analytics(guest, {"balance": balance}):
            # Count only an accepted or idempotently replayed analytics projection.
            reconciled += 1
    # Return a non-public count useful to deterministic recovery tests.
    return reconciled


# Validate one caller-stable conversion idempotency key without retaining its raw value.
def _idempotency_hash(value: str) -> str:
    # Normalize the caller-supplied key before applying contract bounds.
    key = str(value or "").strip()
    # Reject missing, oversized, or non-token keys before reading or mutating identity state.
    if len(key) < 16 or len(key) > 100 or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in key):
        # Return one bounded reason without echoing the supplied key.
        raise ValidationError("Guest conversion idempotency key is invalid", {"reason": "invalid_idempotency_key"})
    # Return a one-way fingerprint suitable for durable replay comparison.
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# Resolve one support-provided guest identity without publishing account, wallet, or session identifiers.
def _guest_for_admin(identity: str) -> dict:
    # Normalize the exact guest or de-identified analytics identity supplied by the operator.
    target = str(identity or "").strip()
    # Reject missing, oversized, or non-token identities before reading canonical account state.
    if not target or len(target) > 191 or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in target):
        # Return one fixed diagnostic without echoing the operator input.
        raise ValidationError("Guest conversion identity is invalid", {"reason": "invalid_guest_identity"})
    # Read the canonical identity document once after overdue guests have been expired.
    for user in auth.load_users().get("users", []):
        # Match either the internal guest id or its Admin-visible de-identified analytics id.
        if target in {str(user.get("user_id") or ""), str(user.get("guest_analytics_id") or "")}:
            # Preserve completed exact replay by allowing the self-service core to validate its terminal marker.
            if auth.is_guest(user) and user.get("converted_to_user_id"):
                # Return the terminal guest only for the bounded replay decision.
                return user
            # Apply the same active-guest boundary used by self-service conversion.
            return _require_active_guest(user)
    # Keep missing identities enumeration-safe and distinct from malformed request syntax.
    raise ValidationError("Conversion requires an active guest trial", {"reason": "guest_unavailable"})


# Convert one active guest on an authenticated Admin's explicit support instruction.
def convert_for_admin(actor, guest_identity: str, email: str, password: str, display_name: str, *, terms_version: str = "", accepted: bool = False, confirm: bool = False, idempotency_key: str = "") -> dict:
    # Require current Admin authority even when a listener-free caller invokes this service directly.
    auth.require_admin(actor or {})
    # Require a literal confirmation so support conversion can never be implicit or inferred from truthy text.
    if confirm is not True:
        # Fail before resolving a guest identity or validating target-account content.
        raise ValidationError("Admin-assisted conversion requires explicit confirmation", {"reason": "confirmation_required"})
    # End every overdue guest before resolving the target so an expired trial cannot be converted by support.
    auth.expire_overdue_guests()
    # Resolve the exact active guest from the support identity.
    guest = _guest_for_admin(guest_identity)
    # Reuse the complete self-service conversion authority and the guest's canonical locale.
    result = convert(guest, email, password, display_name, terms_version=terms_version, accepted=accepted, locale=str(guest.get("locale") or "en-US"), idempotency_key=idempotency_key)
    # Resolve the committed account only after conversion so audit target identity is authoritative.
    account = auth.find_user_by_email(result["email"])
    # Capture one explicit audit instant in addition to the logger's canonical event timestamp.
    audited_at = utc_now()
    # Record actor, guest, account, player, replay, and time without credentials or raw idempotency material.
    _audit("admin_guest_conversion_replayed" if result["replayed"] else "admin_guest_conversion_completed", actor_user_id=str((actor or {}).get("user_id") or ""), target_guest_user_id=str(guest.get("user_id") or ""), target_user_id=str((account or {}).get("user_id") or ""), target_player_id=str(guest.get("player_id") or ""), at=audited_at, replayed=bool(result["replayed"]), assisted=True)
    # Return the exact self-service result shape without adding Admin-only audit fields.
    return result


# Convert an authenticated guest trial into a durable full first-party account.
def convert(guest, email: str, password: str, display_name: str, *, terms_version: str = "", accepted: bool = False, locale: str = "en-US", idempotency_key: str = "") -> dict:
    # Validate and fingerprint the required caller-stable operation key before any replay decision.
    idempotency_hash = _idempotency_hash(idempotency_key)
    # Return the already-created account first so a completed conversion replays even once the guest is terminal.
    prior = _already_converted(guest or {})
    # Publish the stable replay result for a completed conversion before any active-guest requirement.
    if prior is not None:
        # Reject a different operation key when the terminal guest records a completed conversion fingerprint.
        if guest.get("conversion_idempotency_hash") and guest.get("conversion_idempotency_hash") != idempotency_hash:
            # Fail closed instead of treating another operation as the original replay.
            raise ConflictError("Guest conversion idempotency key conflicts with the completed operation")
        # Reject a replay that tries to rename the already-created canonical mailbox.
        if auth.normalize_email(str(email or "")) != prior.get("email"):
            # Preserve the original account identity without accepting conflicting content.
            raise ConflictError("Guest wallet is already bound to a different account")
        # Revoke any surviving disposable session again so exact replay stays fail-closed.
        auth.revoke_sessions_for_user(str(guest.get("user_id") or ""))
        # Return the byte-stable account result without changing conversion identity state.
        return _final_result(guest, prior, replayed=True)
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
        existing_account = _complete_conversion(guest["user_id"], existing_account["user_id"], str(terms_version or ""), utc_now(), idempotency_hash)
        # Revoke any resumable guest session after the atomic identity completion.
        auth.revoke_sessions_for_user(guest["user_id"])
        # Record the recovered completion for operators.
        _audit("guest_conversion_recovered", account_user_id=existing_account["user_id"], player_id=player_id)
        # Return the stable replay result.
        return _final_result(guest, existing_account, replayed=True)
    # Create the full local account adopting the guest's existing player so the wallet and ledger persist.
    try:
        # Create the full local account while atomically preserving one durable owner per player.
        account = auth.create_user(normalized, str(password), str(display_name or "").strip() or normalized, role="player", player_id=player_id, terms_required=False, locale=locale if locale in ("en-US", "ru-RU") else "en-US")
    # Recover a concurrent winner or preserve its conflicting-account rejection.
    except (ConflictError, ValidationError):
        # Re-read the player owner after the failed atomic account claim.
        account = _account_on_player(player_id)
        # Re-raise when no concurrent owner exists or it chose different account content.
        if account is None or account.get("email") != normalized:
            # Preserve the original bounded validation or conflict result.
            raise
        # Atomically record accepted terms and the terminal marker for the concurrent winner.
        account = _complete_conversion(guest["user_id"], account["user_id"], str(terms_version or ""), utc_now(), idempotency_hash)
        # Revoke any resumable guest session after the atomic identity completion.
        auth.revoke_sessions_for_user(guest["user_id"])
        # Record the concurrent recovery without exposing supplied credentials or keys.
        _audit("guest_conversion_concurrent_replay", account_user_id=account["user_id"], player_id=player_id)
        # Return the converged account as an idempotent replay.
        return _final_result(guest, account, replayed=True)
    # Capture the completion time once for consistent terminal markers.
    when = utc_now()
    # Atomically record accepted terms and the terminal guest marker in the shared identity document.
    account = _complete_conversion(guest["user_id"], account["user_id"], str(terms_version or ""), when, idempotency_hash)
    # Revoke any resumable guest session so the disposable trial credential can never be reused.
    auth.revoke_sessions_for_user(guest["user_id"])
    # Record the successful conversion with only bounded provenance fields.
    _audit("guest_conversion_completed", guest_user_id=guest["user_id"], account_user_id=account["user_id"], player_id=player_id)
    # Return the completed conversion result.
    return _final_result(guest, account, replayed=False)
