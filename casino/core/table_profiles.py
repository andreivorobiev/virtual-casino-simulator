"""Per-user, per-game personal table profiles. (#164)

Product direction (issue #164, 2026-07-23) fixes the scope this module enforces:

- Per-game profiles first; only shared display preferences may be global (kept in personal settings, not here).
- First-slice saved fields: preferred chip denominations/layout, default bet size, visible control
  preferences, and autoplay defaults where allowed.
- A profile must never silently save or apply a rule variant that changes game economics. Any such
  variant is out of scope and rejected here.
- Application is opt-in per session; this module only stores and returns the profile, it never forces it.

Every subject is derived from the authenticated session, writes are field-allowlisted and revision-checked,
and a malformed persisted document degrades to defaults and repairs itself on the next write.
"""

# Import the shared UTC clock for contract-compatible timestamps.
from casino.core.clock import utc_now
# Import the configured storage provider for atomic document persistence.
from casino.core.storage import get_storage_provider
# Import standard bounded application errors.
from casino.errors import ConflictError, ValidationError

# Name the personal table-profile document owned by this module.
PROFILE_DOCUMENT_KEY = "settings/table_profiles"
# Enumerate the only profile fields a caller may ever submit; none of these changes game economics.
ALLOWED_FIELDS = frozenset({"chip_denominations", "default_bet", "show_controls", "autoplay_default_rounds"})
# Bound the number of chip denominations so a profile cannot store an unbounded list.
MAX_CHIP_DENOMINATIONS = 8
# Bound a single chip denomination to a sane positive play-token amount.
MAX_CHIP_VALUE = 1_000_000
# Bound the default bet to the same ceiling so a profile cannot encode an absurd stake.
MAX_DEFAULT_BET = 1_000_000
# Bound the stored autoplay default so a profile cannot preconfigure an unbounded run.
MAX_AUTOPLAY_ROUNDS = 100
# Restrict game identifiers to the lower-case ASCII slug shape used by the catalog.
GAME_SLUG_MAX = 40


# Build the default profile for a game the player has never configured.
def default_profile() -> dict:
    # Return conservative defaults with the initial revision.
    return {"chip_denominations": [], "default_bet": 0, "show_controls": True, "autoplay_default_rounds": 0, "revision": 0, "updated_at": None}


# Build the empty persisted document shape.
def _default_document() -> dict:
    # Hold one nested map of games per user id.
    return {"users": {}}


# Normalize any stored record into the published shape without trusting persisted types.
def _normalize(record) -> dict:
    # Start from conservative defaults so a partial or malformed record still yields a valid answer.
    profile = default_profile()
    # Leave the defaults untouched when the stored value is not a record.
    if not isinstance(record, dict):
        # Return the defaults for malformed persisted state.
        return profile
    # Adopt a stored chip layout only when it is a bounded list of positive integers.
    chips = record.get("chip_denominations")
    # Require a usable bounded list before trusting a persisted layout.
    if isinstance(chips, list):
        # Keep only positive integers within the accepted ceiling and the length bound.
        profile["chip_denominations"] = [int(value) for value in chips if isinstance(value, int) and 0 < value <= MAX_CHIP_VALUE][:MAX_CHIP_DENOMINATIONS]
    # Adopt a stored default bet only when it is a bounded non-negative integer.
    if isinstance(record.get("default_bet"), int) and 0 <= record["default_bet"] <= MAX_DEFAULT_BET:
        # Preserve the default bet.
        profile["default_bet"] = record["default_bet"]
    # Coerce the stored control-visibility flag to a strict boolean.
    profile["show_controls"] = bool(record.get("show_controls", True))
    # Adopt a stored autoplay default only when it is a bounded non-negative integer.
    if isinstance(record.get("autoplay_default_rounds"), int) and 0 <= record["autoplay_default_rounds"] <= MAX_AUTOPLAY_ROUNDS:
        # Preserve the autoplay default.
        profile["autoplay_default_rounds"] = record["autoplay_default_rounds"]
    # Adopt a stored revision only when it is a usable non-negative integer.
    if isinstance(record.get("revision"), int) and record["revision"] >= 0:
        # Preserve the concurrency revision.
        profile["revision"] = record["revision"]
    # Adopt a stored timestamp only when it is a string.
    if isinstance(record.get("updated_at"), str):
        # Preserve the last update time.
        profile["updated_at"] = record["updated_at"]
    # Return the normalized published record.
    return profile


# Resolve the durable subject for one authenticated session without trusting caller input.
def _subject(user) -> str:
    # Read the session-bound durable identity.
    user_id = str((user or {}).get("user_id") or "")
    # Refuse to operate without an authenticated subject.
    if not user_id:
        # Fail closed rather than defaulting to a shared record.
        raise ValidationError("Table profiles require an authenticated session", {"reason": "no_subject"})
    # Return the session-derived subject.
    return user_id


# Validate one caller-supplied game slug so it can be a safe document key segment.
def _game_slug(game) -> str:
    # Normalize the candidate slug.
    slug = str(game or "").strip().lower()
    # Require a bounded lower-case ASCII slug of the shape the catalog uses.
    if not slug or len(slug) > GAME_SLUG_MAX or not all(character.isalnum() or character in "_-" for character in slug):
        # Reject an unusable game identifier.
        raise ValidationError("Table profile requires a valid game", {"reason": "invalid_game"})
    # Return the validated slug.
    return slug


# Report whether one session is a disposable guest trial rather than a persistent account.
def _is_guest(user) -> bool:
    # Treat the accepted guest role marker or analytics id as the disposable-session signal.
    return str((user or {}).get("role") or "") == "guest" or bool((user or {}).get("guest_analytics_id"))


# Read the profile bound to the authenticated session for one game.
def read_profile(user, game) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Validate the requested game.
    slug = _game_slug(game)
    # Return non-persisted defaults for a disposable guest trial.
    if _is_guest(user):
        # Publish defaults marked session-local so clients never expect durability.
        return {**default_profile(), "game": slug, "persisted": False}
    # Read the profile document through the configured provider.
    document = get_storage_provider().read_document(PROFILE_DOCUMENT_KEY, _default_document)
    # Tolerate a malformed document by treating it as empty rather than failing the read.
    users = document.get("users") if isinstance(document, dict) else None
    # Resolve this subject's per-game map when the container is usable.
    games = users.get(subject) if isinstance(users, dict) else None
    # Resolve the specific game record when the map is usable.
    record = games.get(slug) if isinstance(games, dict) else None
    # Publish the normalized durable record for this game.
    return {**_normalize(record), "game": slug, "persisted": True}


# Validate one caller-supplied profile patch against the field allowlist and value bounds.
def _validated_patch(patch) -> dict:
    # Require an object body.
    if not isinstance(patch, dict):
        # Reject a non-object payload.
        raise ValidationError("Profile update must be an object", {"reason": "malformed"})
    # Reject any field outside the allowlist so an economics-changing field can never reach storage.
    unknown = sorted(set(patch) - ALLOWED_FIELDS - {"revision"})
    # Fail closed when the caller submitted an unsupported field.
    if unknown:
        # Name only the rejected field keys, never their values.
        raise ValidationError("Profile update contains unsupported fields", {"reason": "unsupported_fields", "fields": unknown})
    # Collect only the validated changes.
    changes = {}
    # Validate the chip layout when supplied.
    if "chip_denominations" in patch:
        # Read the requested layout.
        chips = patch["chip_denominations"]
        # Require a bounded list of positive integers within the accepted ceiling.
        if not isinstance(chips, list) or len(chips) > MAX_CHIP_DENOMINATIONS or not all(isinstance(value, int) and not isinstance(value, bool) and 0 < value <= MAX_CHIP_VALUE for value in chips):
            # Reject a malformed or out-of-range layout.
            raise ValidationError("Chip denominations are invalid", {"reason": "invalid_chips", "max_count": MAX_CHIP_DENOMINATIONS, "max_value": MAX_CHIP_VALUE})
        # Accept the validated layout.
        changes["chip_denominations"] = chips
    # Validate the default bet when supplied.
    if "default_bet" in patch:
        # Read the requested default bet.
        bet = patch["default_bet"]
        # Require a bounded non-negative integer.
        if not isinstance(bet, int) or isinstance(bet, bool) or not (0 <= bet <= MAX_DEFAULT_BET):
            # Reject a malformed or out-of-range default bet.
            raise ValidationError("Default bet is invalid", {"reason": "invalid_default_bet", "max": MAX_DEFAULT_BET})
        # Accept the validated default bet.
        changes["default_bet"] = bet
    # Validate the control-visibility flag when supplied.
    if "show_controls" in patch:
        # Require a strict boolean so a truthy string cannot flip a preference.
        if not isinstance(patch["show_controls"], bool):
            # Reject a non-boolean control flag.
            raise ValidationError("Control visibility must be a boolean", {"reason": "invalid_show_controls"})
        # Accept the boolean control flag.
        changes["show_controls"] = patch["show_controls"]
    # Validate the autoplay default when supplied.
    if "autoplay_default_rounds" in patch:
        # Read the requested autoplay default.
        rounds = patch["autoplay_default_rounds"]
        # Require a bounded non-negative integer so a profile cannot preconfigure an unbounded run.
        if not isinstance(rounds, int) or isinstance(rounds, bool) or not (0 <= rounds <= MAX_AUTOPLAY_ROUNDS):
            # Reject a malformed or out-of-range autoplay default.
            raise ValidationError("Autoplay default is invalid", {"reason": "invalid_autoplay", "max": MAX_AUTOPLAY_ROUNDS})
        # Accept the validated autoplay default.
        changes["autoplay_default_rounds"] = rounds
    # Require at least one real change so an empty write cannot advance the revision.
    if not changes:
        # Reject a patch that carries no supported field.
        raise ValidationError("Profile update contains no supported changes", {"reason": "empty_update"})
    # Return the validated changes.
    return changes


# Apply a validated profile change for the authenticated session and one game.
def update_profile(user, game, patch) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Validate the requested game.
    slug = _game_slug(game)
    # Validate the caller payload before touching storage.
    changes = _validated_patch(patch)
    # Read the caller's expected revision when it supplied one for optimistic concurrency.
    expected = patch.get("revision") if isinstance(patch, dict) else None
    # Apply guest changes in-session without creating any durable record.
    if _is_guest(user):
        # Return the requested values marked non-persisted for the disposable session.
        return {**default_profile(), **changes, "game": slug, "persisted": False}
    # Hold the resulting record so it can be published after the atomic mutation.
    resulting = {}

    # Mutate only this subject's per-game entry inside the shared document.
    def mutate(document):
        # Replace a malformed document rather than failing every future write.
        if not isinstance(document, dict):
            # Start from the empty shape.
            document = _default_document()
        # Replace a malformed user container while preserving the surrounding document.
        if not isinstance(document.get("users"), dict):
            # Reset only the container this module owns.
            document["users"] = {}
        # Replace a malformed per-game map for this subject.
        if not isinstance(document["users"].get(subject), dict):
            # Reset only this subject's game map.
            document["users"][subject] = {}
        # Normalize the current stored record for this subject and game.
        current = _normalize(document["users"][subject].get(slug))
        # Enforce optimistic concurrency only when the caller declared an expected revision.
        if expected is not None and expected != current["revision"]:
            # Reject a stale write so a slower client cannot clobber a newer value.
            raise ConflictError("Table profile was updated by another session")
        # Build the next record from the current values and the validated changes.
        nxt = {**current, **changes, "revision": current["revision"] + 1, "updated_at": utc_now()}
        # Store the next record for this subject and game only.
        document["users"][subject][slug] = nxt
        # Publish the stored record to the caller.
        resulting.update(nxt)
        # Return the mutated document for atomic persistence.
        return document

    # Persist the change atomically through the configured provider.
    get_storage_provider().update_document(PROFILE_DOCUMENT_KEY, mutate, _default_document)
    # Return the newly stored record.
    return {**resulting, "game": slug, "persisted": True}
