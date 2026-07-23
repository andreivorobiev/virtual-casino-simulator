"""Version-aware What's New tour eligibility for curated release entries. (#165)

Product direction (issue #165, 2026-07-23) fixes three rules this module exists to enforce:

1. Tour content is curated release metadata in the repository, not logic. Entries live in
   `docs/releases/whats_new.json` and carry localization keys only, so the release coordinator owns
   the copy and engineering owns none of it.
2. A module version bump never triggers a tour on its own. An entry appears only when it carries an
   explicit `show_in_whats_new: true` opt-in.
3. A player who skipped several releases sees one merged tour capped to the most recent meaningful
   entries with a link to the full changelog, never a stack of tours.

Raw version keys are internal. The player payload carries localization keys and a count, and
dismissal is stamped server-side from the canonical application version, so a client never has to
send or render a version string. Terms and privacy consent are deliberately out of scope here and
remain their own flows.
"""

# Import JSON parsing for the curated release metadata.
import json
# Import filesystem paths for locating the tracked metadata.
from pathlib import Path

# Import the canonical application release used to stamp dismissals.
from casino.config import APP_VERSION
# Import the shared UTC formatter for contract-compatible timestamps.
from casino.core.clock import utc_now
# Import the configured storage provider for atomic dismissal persistence.
from casino.core.storage import get_storage_provider
# Import standard bounded application errors.
from casino.errors import ValidationError

# Resolve the repository root without depending on the process working directory.
ROOT_DIR = Path(__file__).resolve().parents[2]
# Point at the curated release metadata owned by the release coordinator.
WHATS_NEW_PATH = ROOT_DIR / "docs" / "releases" / "whats_new.json"
# Name the dismissal document owned by this module.
SEEN_DOCUMENT_KEY = "settings/whats_new"
# Cap merged entries when the curated metadata does not specify its own limit.
DEFAULT_MAX_MERGED_ENTRIES = 3


# Parse one dotted release version into a comparable tuple without trusting its shape.
def _version_key(value) -> tuple:
    # Split the candidate version into its dotted parts.
    parts = str(value or "").split(".")
    # Build a numeric tuple, treating any non-numeric part as zero so comparison never raises.
    return tuple(int(part) if part.isdigit() else 0 for part in parts[:3]) + (0,) * max(0, 3 - len(parts))


# Load the curated release metadata, tolerating an absent or malformed file.
def load_catalog() -> dict:
    # Start protected read so a malformed curated file can never break the shell.
    try:
        # Parse the tracked metadata.
        catalog = json.loads(WHATS_NEW_PATH.read_text(encoding="utf-8"))
    # Treat a missing or unparsable catalog as simply having no tour to show.
    except Exception:
        # Return an empty catalog rather than raising into a player surface.
        return {"entries": [], "changelog_path": "", "max_merged_entries": DEFAULT_MAX_MERGED_ENTRIES}
    # Reject a catalog that is not an object.
    if not isinstance(catalog, dict):
        # Return the empty catalog shape.
        return {"entries": [], "changelog_path": "", "max_merged_entries": DEFAULT_MAX_MERGED_ENTRIES}
    # Keep only well-formed entry records.
    entries = [entry for entry in catalog.get("entries", []) if isinstance(entry, dict) and entry.get("version")]
    # Read the curated cap, falling back to the module default.
    cap = catalog.get("max_merged_entries")
    # Publish the normalized catalog.
    return {"entries": entries, "changelog_path": str(catalog.get("changelog_path") or ""), "max_merged_entries": cap if isinstance(cap, int) and cap > 0 else DEFAULT_MAX_MERGED_ENTRIES}


# Resolve the durable subject for one authenticated session without trusting caller input.
def _subject(user) -> str:
    # Read the session-bound durable identity.
    user_id = str((user or {}).get("user_id") or "")
    # Refuse to operate without an authenticated subject.
    if not user_id:
        # Fail closed rather than defaulting to a shared record.
        raise ValidationError("What's New requires an authenticated session", {"reason": "no_subject"})
    # Return the session-derived subject.
    return user_id


# Read the release this subject has already acknowledged.
def _last_seen(subject: str) -> str:
    # Read the dismissal document through the configured provider.
    document = get_storage_provider().read_document(SEEN_DOCUMENT_KEY, lambda: {"users": {}})
    # Tolerate a malformed document by treating it as empty.
    users = document.get("users") if isinstance(document, dict) else None
    # Resolve this subject's stored record when the container is usable.
    record = users.get(subject) if isinstance(users, dict) else None
    # Return the acknowledged version or an empty marker for a first-time viewer.
    return str(record.get("last_seen_version") or "") if isinstance(record, dict) else ""


# Select the curated entries a subject has not yet acknowledged.
def eligible_entries(last_seen_version: str, catalog=None) -> list:
    # Use the tracked catalog unless an isolated test supplied one.
    resolved = catalog if catalog is not None else load_catalog()
    # Fall back to the module cap when an injected catalog omits one.
    cap = resolved.get("max_merged_entries") if isinstance(resolved.get("max_merged_entries"), int) else DEFAULT_MAX_MERGED_ENTRIES
    # Drop malformed records here too, because a hand-edited curated file must never break a player surface.
    usable = [entry for entry in resolved.get("entries", []) if isinstance(entry, dict) and entry.get("version")]
    # Keep only entries the release coordinator explicitly opted in; a version bump alone is never enough.
    opted_in = [entry for entry in usable if entry.get("show_in_whats_new") is True]
    # Drop entries at or below the acknowledged release so a dismissed tour never returns.
    unseen = [entry for entry in opted_in if not last_seen_version or _version_key(entry["version"]) > _version_key(last_seen_version)]
    # Drop entries newer than the running application so an unreleased tour cannot leak early.
    current = [entry for entry in unseen if _version_key(entry["version"]) <= _version_key(APP_VERSION)]
    # Order newest first so the cap keeps the most recent meaningful entries.
    ordered = sorted(current, key=lambda entry: _version_key(entry["version"]), reverse=True)
    # Return one merged, capped set rather than a stack of separate tours.
    return ordered[:cap]


# Build the player-facing tour payload for one authenticated session.
def tour_for(user) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Load the curated catalog once.
    catalog = load_catalog()
    # Resolve which curated entries remain unacknowledged.
    entries = eligible_entries(_last_seen(subject), catalog)
    # Publish localization keys only so no raw version key ever reaches a player surface.
    return {
        # Show the tour only when at least one curated entry is eligible.
        "show": bool(entries),
        # Publish only the curated localization keys for each merged entry.
        "entries": [{"title_key": str(entry.get("title_key") or ""), "body_key": str(entry.get("body_key") or "")} for entry in entries],
        # Publish how many releases were merged so copy can say "since you were last here".
        "merged_count": len(entries),
        # Publish the changelog location so a player can read the full history.
        "changelog_path": catalog["changelog_path"],
    }


# Record that the subject acknowledged the current release without trusting a client-supplied version.
def dismiss(user) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Hold the resulting record so it can be published after the atomic mutation.
    resulting = {}

    # Mutate only this subject's entry inside the shared document.
    def mutate(document):
        # Replace a malformed document rather than failing every future dismissal.
        if not isinstance(document, dict):
            # Start from the empty shape.
            document = {"users": {}}
        # Replace a malformed container while preserving the surrounding document.
        if not isinstance(document.get("users"), dict):
            # Reset only the container this module owns.
            document["users"] = {}
        # Stamp the canonical running release rather than any caller-supplied value.
        record = {"last_seen_version": APP_VERSION, "dismissed_at": utc_now()}
        # Store the acknowledgement for this subject only.
        document["users"][subject] = record
        # Publish the stored record to the caller.
        resulting.update(record)
        # Return the mutated document for atomic persistence.
        return document

    # Persist the acknowledgement atomically through the configured provider.
    get_storage_provider().update_document(SEEN_DOCUMENT_KEY, mutate, lambda: {"users": {}})
    # Confirm the dismissal without echoing the raw version back to the player surface.
    return {"dismissed": True, "dismissed_at": resulting.get("dismissed_at")}
