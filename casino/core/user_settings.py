"""Per-user personal preferences and self-only activity reads for My Settings. (#352)

This module owns the personal preference record and the self-scoped view of the authoritative
ledger. It never becomes a second history authority: activity is read straight from the accepted
ledger source and simply bounded, paginated, and filtered to the session's own subject. Every
subject is derived from the authenticated session, never from a caller-supplied identifier, and
every mutation is field-allowlisted and revision-checked so a stale client cannot silently
overwrite a newer value.

Guest trials receive defaults and may change them for the life of their session, but nothing is
persisted for them: the guest lifecycle stays disposable and no durable personal record is created.
"""

# Import the shared UTC formatter for contract-compatible timestamps.
from casino.core.clock import utc_now
# Import the authoritative ledger so activity has exactly one source of truth.
from casino.core import ledger
# Import the configured storage provider for atomic document persistence.
from casino.core.storage import get_storage_provider
# Import standard bounded application errors.
from casino.errors import ConflictError, ValidationError

# Name the personal-preferences document owned by this module.
SETTINGS_DOCUMENT_KEY = "settings/users"
# Accept only the locales the shell actually ships so an unsupported value can never be persisted.
SUPPORTED_LOCALES = ("en-US", "ru-RU")
# Fall back to the single canonical default locale for unknown, retired, or malformed values.
DEFAULT_LOCALE = "en-US"
# Enumerate the only preference fields a caller may ever submit.
ALLOWED_FIELDS = frozenset({"locale", "sound_enabled"})
# Bound one page of self-history so a caller can never request an unbounded read.
MAX_PAGE_SIZE = 50
# Return a stable default page size when the caller supplies none.
DEFAULT_PAGE_SIZE = 20
# Read a bounded ledger window large enough to paginate without loading unbounded history.
LEDGER_READ_CEILING = 1000
# Publish only ledger fields that carry no durable identifier or internal audit material.
HISTORY_FIELDS = ("ts", "game", "round_id", "transaction_type", "amount", "balance_after")


# Build the default personal preference record for a subject with nothing stored yet.
def default_settings() -> dict:
    # Return the canonical defaults with the initial revision.
    return {"locale": DEFAULT_LOCALE, "sound_enabled": True, "revision": 0, "updated_at": None}


# Build the empty persisted document shape.
def _default_document() -> dict:
    # Hold one entry per user id.
    return {"users": {}}


# Normalize any stored record into the published settings shape without trusting persisted types.
def _normalize(record) -> dict:
    # Start from the canonical defaults so a partial or malformed record still yields a valid answer.
    settings = default_settings()
    # Leave the defaults untouched when the stored value is not a record.
    if not isinstance(record, dict):
        # Return the defaults for malformed persisted state.
        return settings
    # Accept a stored locale only when it is still supported, otherwise fall back.
    if record.get("locale") in SUPPORTED_LOCALES:
        # Adopt the supported stored locale.
        settings["locale"] = record["locale"]
    # Coerce the stored sound flag to a strict boolean.
    settings["sound_enabled"] = bool(record.get("sound_enabled", True))
    # Adopt a stored revision only when it is a usable non-negative integer.
    if isinstance(record.get("revision"), int) and record["revision"] >= 0:
        # Preserve the concurrency revision.
        settings["revision"] = record["revision"]
    # Adopt a stored timestamp only when it is a string.
    if isinstance(record.get("updated_at"), str):
        # Preserve the last update time.
        settings["updated_at"] = record["updated_at"]
    # Return the normalized published record.
    return settings


# Resolve the durable subject for one authenticated session without trusting caller input.
def _subject(user) -> str:
    # Read the session-bound durable identity.
    user_id = str((user or {}).get("user_id") or "")
    # Refuse to operate without an authenticated subject.
    if not user_id:
        # Fail closed rather than defaulting to a shared record.
        raise ValidationError("Personal settings require an authenticated session", {"reason": "no_subject"})
    # Return the session-derived subject.
    return user_id


# Report whether one session is a disposable guest trial rather than a persistent account.
def _is_guest(user) -> bool:
    # Treat the accepted guest role marker as the single disposable-session signal.
    return str((user or {}).get("role") or "") == "guest" or bool((user or {}).get("guest_analytics_id"))


# Read the personal preferences bound to the authenticated session.
def read_settings(user) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Return non-persisted defaults for a disposable guest trial.
    if _is_guest(user):
        # Publish defaults marked as session-local so clients never expect durability.
        return {**default_settings(), "persisted": False}
    # Read the personal-preferences document through the configured provider.
    document = get_storage_provider().read_document(SETTINGS_DOCUMENT_KEY, _default_document)
    # Tolerate a malformed document by treating it as empty rather than failing the read.
    users = document.get("users") if isinstance(document, dict) else None
    # Resolve this subject's stored record when the container is usable.
    record = users.get(subject) if isinstance(users, dict) else None
    # Publish the normalized durable record.
    return {**_normalize(record), "persisted": True}


# Validate one caller-supplied preference patch against the field allowlist.
def _validated_patch(patch) -> dict:
    # Require an object body.
    if not isinstance(patch, dict):
        # Reject a non-object payload.
        raise ValidationError("Settings update must be an object", {"reason": "malformed"})
    # Reject any field outside the allowlist so unknown keys can never reach storage.
    unknown = sorted(set(patch) - ALLOWED_FIELDS - {"revision"})
    # Fail closed when the caller submitted an unsupported field.
    if unknown:
        # Name only the rejected field keys, never their values.
        raise ValidationError("Settings update contains unsupported fields", {"reason": "unsupported_fields", "fields": unknown})
    # Collect only the validated changes.
    changes = {}
    # Validate the locale when the caller supplied one.
    if "locale" in patch:
        # Reject an unsupported or retired locale rather than silently falling back on write.
        if patch["locale"] not in SUPPORTED_LOCALES:
            # Publish the supported catalog so a client can correct itself.
            raise ValidationError("Locale is not supported", {"reason": "unsupported_locale", "supported": list(SUPPORTED_LOCALES)})
        # Accept the supported locale.
        changes["locale"] = patch["locale"]
    # Validate the sound flag when the caller supplied one.
    if "sound_enabled" in patch:
        # Require a strict boolean so a truthy string cannot flip a preference.
        if not isinstance(patch["sound_enabled"], bool):
            # Reject a non-boolean sound value.
            raise ValidationError("Sound preference must be a boolean", {"reason": "malformed_sound"})
        # Accept the boolean sound flag.
        changes["sound_enabled"] = patch["sound_enabled"]
    # Require at least one real change so an empty write cannot advance the revision.
    if not changes:
        # Reject a patch that carries no supported field.
        raise ValidationError("Settings update contains no supported changes", {"reason": "empty_update"})
    # Return the validated changes.
    return changes


# Apply a validated preference change for the authenticated session.
def update_settings(user, patch) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Validate the caller payload before touching storage.
    changes = _validated_patch(patch)
    # Read the caller's expected revision when it supplied one for optimistic concurrency.
    expected = patch.get("revision") if isinstance(patch, dict) else None
    # Apply guest changes in-session without creating any durable record.
    if _is_guest(user):
        # Return the requested values marked as non-persisted for the disposable session.
        return {**default_settings(), **changes, "persisted": False}
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
        # Enforce optimistic concurrency only when the caller declared an expected revision.
        if expected is not None and expected != current["revision"]:
            # Reject a stale write so a slower client cannot clobber a newer value.
            raise ConflictError("Settings were updated by another session")
        # Build the next record from the current values and the validated changes.
        nxt = {**current, **changes, "revision": current["revision"] + 1, "updated_at": utc_now()}
        # Store the next record for this subject only.
        document["users"][subject] = nxt
        # Publish the stored record to the caller.
        resulting.update(nxt)
        # Return the mutated document for atomic persistence.
        return document

    # Persist the change atomically through the configured provider.
    get_storage_provider().update_document(SETTINGS_DOCUMENT_KEY, mutate, _default_document)
    # Return the newly stored record.
    return {**resulting, "persisted": True}


# Reduce one ledger row to the publishable self-history shape.
def _history_row(row) -> dict:
    # Copy only allowlisted fields so durable identifiers and internal details never escape.
    return {field: row.get(field) for field in HISTORY_FIELDS}


# Read the authenticated session's own bounded, paginated activity.
def self_history(user, *, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE, game: str = "") -> dict:
    # Derive the subject from the session only, never from a caller-supplied identifier.
    _subject(user)
    # Resolve the ledger subject bound to this session.
    player_id = str((user or {}).get("player_id") or "")
    # Clamp the page size into the accepted bounds so a caller cannot request an unbounded read.
    size = max(1, min(int(page_size or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
    # Clamp the page index so a negative or zero page cannot wrap the slice.
    index = max(1, int(page or 1))
    # Return an explicit empty page when the session has no ledger subject at all.
    if not player_id:
        # Publish a stable empty envelope rather than another user's rows.
        return {"events": [], "page": index, "page_size": size, "total": 0, "has_more": False, "game": ""}
    # Read only this player's rows; the provider filter is the authorization boundary.
    rows = ledger.read_recent(player_id, LEDGER_READ_CEILING)
    # Drop any row that is not bound to this subject so a provider change can never leak another player.
    rows = [row for row in rows if str(row.get("player_id") or "") == player_id]
    # Normalize the optional game filter without trusting its type.
    selected = str(game or "").strip()
    # Apply the game filter when the caller supplied one.
    if selected:
        # Keep only rows for the selected game.
        rows = [row for row in rows if str(row.get("game") or "") == selected]
    # Order newest first so pagination stays stable and readable.
    ordered = list(reversed(rows))
    # Record the filtered total before slicing.
    total = len(ordered)
    # Compute the slice start for the requested page.
    start = (index - 1) * size
    # Publish the bounded page with its allowlisted fields only.
    return {"events": [_history_row(row) for row in ordered[start:start + size]], "page": index, "page_size": size, "total": total, "has_more": start + size < total, "game": selected}
