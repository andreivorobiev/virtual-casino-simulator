"""Optional session wellness reminders, break controls, and neutral session summaries. (#167)

Everything here is opt-in and off by default. The module deliberately offers no reward, streak,
bonus, or token movement for engaging with a reminder, and it never evaluates a player's results:
summaries report committed play-token totals and elapsed time as plain numbers, and every piece of
player-visible wording lives in the shell resources so the neutral-copy rule is enforced against
shipped text rather than against strings scattered through Python.

Reminder intervals are bounded at both ends. A floor exists so the product cannot be configured
into countdown pressure, and a ceiling exists so a reminder a player enabled still actually arrives.
"""

# Import the shared UTC formatter for contract-compatible timestamps.
from casino.core.clock import utc_now
# Import the authoritative ledger so summaries report committed movements only.
from casino.core import ledger
# Import the shared self-history ceiling so every personal ledger read stays identically bounded.
from casino.core import self_history as activity
# Import the configured storage provider for atomic document persistence.
from casino.core.storage import get_storage_provider
# Import standard bounded application errors.
from casino.errors import ConflictError, ValidationError

# Name the wellness document owned by this module.
WELLNESS_DOCUMENT_KEY = "settings/wellness"
# Enumerate the only wellness fields a caller may ever submit.
ALLOWED_FIELDS = frozenset({"enabled", "reminder_interval_minutes", "break_reminder_enabled"})
# Keep reminders off until a player explicitly opts in.
DEFAULT_ENABLED = False
# Use a calm default cadence rather than a frequent, pressuring one.
DEFAULT_INTERVAL_MINUTES = 30
# Refuse an interval short enough to function as countdown pressure.
MIN_INTERVAL_MINUTES = 10
# Refuse an interval so long that an enabled reminder would never arrive.
MAX_INTERVAL_MINUTES = 240
# Build the default wellness record for a player who has never configured reminders.
def default_wellness() -> dict:
    # Return the opt-in defaults with the initial revision.
    return {"enabled": DEFAULT_ENABLED, "reminder_interval_minutes": DEFAULT_INTERVAL_MINUTES, "break_reminder_enabled": DEFAULT_ENABLED, "revision": 0, "updated_at": None}


# Build the empty persisted document shape.
def _default_document() -> dict:
    # Hold one entry per user id.
    return {"users": {}}


# Normalize any stored record into the published shape without trusting persisted types.
def _normalize(record) -> dict:
    # Start from the opt-in defaults so partial or malformed state still yields a valid answer.
    wellness = default_wellness()
    # Leave the defaults untouched when the stored value is not a record.
    if not isinstance(record, dict):
        # Return the defaults for malformed persisted state.
        return wellness
    # Inspect both stored switches without allowing truthy malformed values to opt a player in.
    for flag in ("enabled", "break_reminder_enabled"):
        # Adopt only a strict stored boolean.
        if isinstance(record.get(flag), bool):
            # Preserve the valid stored choice.
            wellness[flag] = record[flag]
    # Adopt a stored interval only when it is still inside the accepted bounds.
    stored = record.get("reminder_interval_minutes")
    # Require a usable in-range integer before trusting a persisted cadence.
    if isinstance(stored, int) and MIN_INTERVAL_MINUTES <= stored <= MAX_INTERVAL_MINUTES:
        # Preserve the configured cadence.
        wellness["reminder_interval_minutes"] = stored
    # Adopt a stored revision only when it is a usable non-negative integer.
    if isinstance(record.get("revision"), int) and record["revision"] >= 0:
        # Preserve the concurrency revision.
        wellness["revision"] = record["revision"]
    # Adopt a stored timestamp only when it is a string.
    if isinstance(record.get("updated_at"), str):
        # Preserve the last update time.
        wellness["updated_at"] = record["updated_at"]
    # Return the normalized published record.
    return wellness


# Resolve the durable subject for one authenticated session without trusting caller input.
def _subject(user) -> str:
    # Read the session-bound durable identity.
    user_id = str((user or {}).get("user_id") or "")
    # Refuse to operate without an authenticated subject.
    if not user_id:
        # Fail closed rather than defaulting to a shared record.
        raise ValidationError("Session wellness requires an authenticated session", {"reason": "no_subject"})
    # Return the session-derived subject.
    return user_id


# Report whether one subject is a disposable guest trial rather than a persistent account.
def _is_guest(user) -> bool:
    # Treat the accepted guest markers as the single disposable-session signal.
    return str((user or {}).get("role") or "") == "guest" or bool((user or {}).get("guest_analytics_id"))


# Read the wellness preferences bound to the authenticated session.
def read_wellness(user) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Return non-persisted defaults for a disposable guest trial.
    if _is_guest(user):
        # Publish explicit persistence metadata so a client never promises durable guest settings.
        return {**default_wellness(), "min_interval_minutes": MIN_INTERVAL_MINUTES, "max_interval_minutes": MAX_INTERVAL_MINUTES, "persisted": False}
    # Read the wellness document through the configured provider.
    document = get_storage_provider().read_document(WELLNESS_DOCUMENT_KEY, _default_document)
    # Tolerate a malformed document by treating it as empty rather than failing the read.
    users = document.get("users") if isinstance(document, dict) else None
    # Resolve this subject's stored record when the container is usable.
    record = users.get(subject) if isinstance(users, dict) else None
    # Publish the normalized record together with the accepted cadence bounds.
    return {**_normalize(record), "min_interval_minutes": MIN_INTERVAL_MINUTES, "max_interval_minutes": MAX_INTERVAL_MINUTES, "persisted": True}


# Validate one caller-supplied wellness patch against the field allowlist and cadence bounds.
def _validated_patch(patch) -> dict:
    # Require an object body.
    if not isinstance(patch, dict):
        # Reject a non-object payload.
        raise ValidationError("Wellness update must be an object", {"reason": "malformed"})
    # Reject any field outside the allowlist so unknown keys can never reach storage.
    unknown = sorted(set(patch) - ALLOWED_FIELDS - {"revision"})
    # Fail closed when the caller submitted an unsupported field.
    if unknown:
        # Name only the rejected field keys, never their values.
        raise ValidationError("Wellness update contains unsupported fields", {"reason": "unsupported_fields", "fields": unknown})
    # Collect only the validated changes.
    changes = {}
    # Validate both switches when supplied.
    for flag in ("enabled", "break_reminder_enabled"):
        # Skip a switch the caller did not send.
        if flag in patch:
            # Require a strict boolean so a truthy string cannot enable a reminder.
            if not isinstance(patch[flag], bool):
                # Reject a non-boolean switch.
                raise ValidationError("Wellness switches must be booleans", {"reason": "malformed_switch", "field": flag})
            # Accept the boolean switch.
            changes[flag] = patch[flag]
    # Validate the reminder cadence when supplied.
    if "reminder_interval_minutes" in patch:
        # Read the requested cadence.
        interval = patch["reminder_interval_minutes"]
        # Refuse a non-integer, sub-floor, or above-ceiling cadence so reminders cannot become pressure.
        if not isinstance(interval, int) or isinstance(interval, bool) or not (MIN_INTERVAL_MINUTES <= interval <= MAX_INTERVAL_MINUTES):
            # Publish the accepted bounds so a client can correct itself.
            raise ValidationError("Reminder interval is outside the accepted range", {"reason": "interval_out_of_range", "min": MIN_INTERVAL_MINUTES, "max": MAX_INTERVAL_MINUTES})
        # Accept the bounded cadence.
        changes["reminder_interval_minutes"] = interval
    # Require at least one real change so an empty write cannot advance the revision.
    if not changes:
        # Reject a patch that carries no supported field.
        raise ValidationError("Wellness update contains no supported changes", {"reason": "empty_update"})
    # Return the validated changes.
    return changes


# Apply a validated wellness change for the authenticated session.
def update_wellness(user, patch) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Validate the caller payload before touching storage.
    changes = _validated_patch(patch)
    # Read the caller's expected revision when it supplied one for optimistic concurrency.
    expected = patch.get("revision") if isinstance(patch, dict) else None
    # Keep disposable guest changes non-durable and explicit about that lifecycle.
    if _is_guest(user):
        # Return only the validated session-local values without creating a durable account record.
        return {**default_wellness(), **changes, "min_interval_minutes": MIN_INTERVAL_MINUTES, "max_interval_minutes": MAX_INTERVAL_MINUTES, "persisted": False}
    # Hold the resulting record so it can be published after the atomic mutation.
    resulting = {}

    # Mutate only this subject's entry inside the shared document.
    def mutate(document):
        # Replace a malformed document rather than failing every future write.
        if not isinstance(document, dict):
            # Start from the empty shape.
            document = _default_document()
        # Replace a malformed container while preserving the surrounding document.
        if not isinstance(document.get("users"), dict):
            # Reset only the container this module owns.
            document["users"] = {}
        # Normalize the current stored record for this subject.
        current = _normalize(document["users"].get(subject))
        # Reject a stale revision so two sessions cannot silently overwrite one another.
        if expected is not None and expected != current["revision"]:
            # Use the standard conflict envelope without revealing stored values.
            raise ConflictError("Wellness settings were updated by another session")
        # Build the next record from the current values and the validated changes.
        nxt = {**current, **changes, "revision": current["revision"] + 1, "updated_at": utc_now()}
        # Store the next record for this subject only.
        document["users"][subject] = nxt
        # Publish the stored record to the caller.
        resulting.update(nxt)
        # Return the mutated document for atomic persistence.
        return document

    # Persist the change atomically through the configured provider.
    get_storage_provider().update_document(WELLNESS_DOCUMENT_KEY, mutate, _default_document)
    # Publish the stored record together with the accepted cadence bounds.
    return {**resulting, "min_interval_minutes": MIN_INTERVAL_MINUTES, "max_interval_minutes": MAX_INTERVAL_MINUTES, "persisted": True}


# Summarize the authenticated session's own committed play-token activity without evaluating it.
def session_summary(user, *, since: str = "") -> dict:
    # Derive the subject from the session only, never from a caller-supplied identifier.
    _subject(user)
    # Resolve the ledger subject bound to this session.
    player_id = str((user or {}).get("player_id") or "")
    # Publish an explicit empty summary when the session has no ledger subject.
    if not player_id:
        # Return a stable zeroed envelope rather than another player's totals.
        return {"movements": 0, "staked": 0.0, "returned": 0.0, "net": 0.0, "since": str(since or ""), "play_tokens_only": True}
    # Read only this player's committed movements.
    rows = ledger.read_recent(player_id, activity.LEDGER_READ_CEILING)
    # Drop any row not bound to this subject so a provider change can never leak another player.
    owned = [row for row in rows if str(row.get("player_id") or "") == player_id]
    # Apply the optional start boundary using the committed timestamps.
    bounded = [row for row in owned if not since or str(row.get("ts") or "") >= str(since)] if since else owned
    # Total the committed outgoing movements as staked play tokens.
    staked = sum(-float(row.get("amount") or 0) for row in bounded if float(row.get("amount") or 0) < 0)
    # Total the committed incoming movements as returned play tokens.
    returned = sum(float(row.get("amount") or 0) for row in bounded if float(row.get("amount") or 0) > 0)
    # Publish plain committed totals with no evaluative language or judgement.
    return {"movements": len(bounded), "staked": round(staked, 2), "returned": round(returned, 2), "net": round(returned - staked, 2), "since": str(since or ""), "play_tokens_only": True}


# Record that a player acknowledged a reminder without granting anything in return.
def acknowledge_reminder(user) -> dict:
    # Derive the subject so an unauthenticated caller cannot record an acknowledgement.
    _subject(user)
    # Return only the acknowledgement time; no token, streak, bonus, or reward is ever issued.
    return {"acknowledged_at": utc_now(), "reward_granted": False}
