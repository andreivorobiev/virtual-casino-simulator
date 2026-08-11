# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
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


# Parse one exact dotted release version into a comparable tuple without trusting its shape.
def _version_key(value) -> tuple | None:
    # Split the candidate version into its dotted parts.
    parts = str(value or "").split(".")
    # Refuse incomplete, over-extended, or non-numeric versions rather than guessing their ordering.
    if len(parts) not in (3, 4) or any(not part.isdigit() for part in parts):
        # Mark the malformed version unusable.
        return None
    # Reject three-part values that already start with the new private-beta epoch.
    if len(parts) == 3 and parts[0] == "0":
        # Mark the incomplete four-part private-beta version unusable.
        return None
    # Preserve legacy three-part releases by treating them as private-beta epoch zero.
    normalized = ["0", *parts] if len(parts) == 3 else parts
    # Build the exact numeric comparison tuple.
    return tuple(int(part) for part in normalized)


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
    # Read the entry collection without allowing a malformed container to raise.
    raw_entries = catalog.get("entries", [])
    # Keep only mapping entries from a real list.
    entries = [entry for entry in raw_entries if isinstance(entry, dict)] if isinstance(raw_entries, list) else []
    # Read the curated cap, falling back to the module default.
    cap = catalog.get("max_merged_entries")
    # Bound a valid configured cap to the contract ceiling.
    bounded_cap = min(cap, DEFAULT_MAX_MERGED_ENTRIES) if isinstance(cap, int) and not isinstance(cap, bool) and cap > 0 else DEFAULT_MAX_MERGED_ENTRIES
    # Publish the normalized catalog.
    return {"entries": entries, "changelog_path": str(catalog.get("changelog_path") or ""), "max_merged_entries": bounded_cap}


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


# Report whether one session is a disposable guest trial rather than a persistent account.
def _is_guest(user) -> bool:
    # Treat either accepted guest marker as the single disposable-session signal.
    return str((user or {}).get("role") or "") == "guest" or bool((user or {}).get("guest_analytics_id"))


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
    # Treat an injected malformed catalog as empty so tests and future callers share fail-closed behavior.
    if not isinstance(resolved, dict):
        # Return no eligible entries for an unusable catalog.
        return []
    # Fall back to the module cap when an injected catalog omits one.
    configured_cap = resolved.get("max_merged_entries")
    # Accept only a positive integer cap and refuse booleans, which are integers in Python.
    cap = min(configured_cap, DEFAULT_MAX_MERGED_ENTRIES) if isinstance(configured_cap, int) and not isinstance(configured_cap, bool) and configured_cap > 0 else DEFAULT_MAX_MERGED_ENTRIES
    # Drop malformed records here too, because a hand-edited curated file must never break a player surface.
    raw_entries = resolved.get("entries", [])
    # Require a list so a mapping or string cannot be interpreted as release entries.
    entries = raw_entries if isinstance(raw_entries, list) else []
    # Keep only records with an exact comparable release version and non-empty localization keys.
    usable = [entry for entry in entries if isinstance(entry, dict) and _version_key(entry.get("version")) is not None and str(entry.get("title_key") or "").strip() and str(entry.get("body_key") or "").strip()]
    # Keep only entries the release coordinator explicitly opted in; a version bump alone is never enough.
    opted_in = [entry for entry in usable if entry.get("show_in_whats_new") is True]
    # Drop entries at or below the acknowledged release so a dismissed tour never returns.
    seen_key = _version_key(last_seen_version)
    # Treat a missing or malformed acknowledgement as first use without ever raising.
    unseen = [entry for entry in opted_in if seen_key is None or _version_key(entry["version"]) > seen_key]
    # Drop entries newer than the running application so an unreleased tour cannot leak early.
    app_key = _version_key(APP_VERSION)
    # Fail closed when the canonical application version itself is unexpectedly malformed.
    current = [entry for entry in unseen if app_key is not None and _version_key(entry["version"]) <= app_key]
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
    # Never persist or display release-tour state for a disposable guest trial.
    guest = _is_guest(user)
    # Resolve which curated entries remain unacknowledged.
    entries = [] if guest else eligible_entries(_last_seen(subject), catalog)
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
        # Tell clients whether acknowledgement can survive this session.
        "persisted": not guest,
    }


# Record that the subject acknowledged the current release without trusting a client-supplied version.
def dismiss(user) -> dict:
    # Derive the subject from the session only.
    subject = _subject(user)
    # Refuse to create durable release-tour state for a disposable guest trial.
    if _is_guest(user):
        # Confirm only a session-local acknowledgement with no timestamp or durable record.
        return {"dismissed": True, "dismissed_at": None, "persisted": False}
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
        # Read the current subject record without trusting its stored shape.
        current = document["users"].get(subject)
        # Preserve an exact current-release acknowledgement so retries are idempotent.
        if isinstance(current, dict) and current.get("last_seen_version") == APP_VERSION and isinstance(current.get("dismissed_at"), str):
            # Reuse the already committed acknowledgement.
            record = current
        else:
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
    return {"dismissed": True, "dismissed_at": resulting.get("dismissed_at"), "persisted": True}
