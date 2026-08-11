# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Read-only Compare Games attributes derived from the catalog. (#160)

Product direction (issue #160, 2026-07-23) fixes what this module may and may not expose:

- First-slice attributes must be product/UX-safe: category, ledger-backed status, localization readiness,
  featured placement, and localized labels.
- House edge, expected return, volatility, probability, and payout math are deliberately excluded. Those
  require reviewed "simulator math" wording and product plus counsel review before any release, so this
  module neither computes nor emits them.

This is a pure read over the existing catalog. It never edits the registry, so it does not touch the
serialized game-integration lane, and it fabricates no attribute it cannot honestly derive from catalog data.
"""

# Import the read-only catalog facade the attributes are derived from.
from casino.games.registry import list_games
# Import the standard bounded application error for a malformed request.
from casino.errors import ValidationError

# Bound the number of games one comparison may include so a caller cannot request an unbounded table.
MAX_COMPARE = 6
# Restrict game identifiers to the lower-case ASCII slug shape used by the catalog.
GAME_SLUG_MAX = 40
# Enumerate the money-math attributes this module must never emit until they are separately reviewed.
FORBIDDEN_ATTRIBUTES = frozenset({"house_edge", "expected_return", "rtp", "volatility", "probability", "payout_math"})


# Index the catalog once per call by its stable game id.
def _catalog_index() -> dict:
    # Build a mapping from game id to its catalog record.
    return {str(game.get("id")): game for game in list_games() if game.get("id")}


# Derive whether a catalog record ships a translation for the given locale.
def _localization_ready(record, locale: str) -> bool:
    # Read the translations map defensively.
    translations = record.get("translations")
    # Report readiness only when a non-empty translation exists for the locale.
    return isinstance(translations, dict) and bool((translations.get(locale) or {}).get("label"))


# Build one product-safe comparison row for a catalog record.
def _compare_row(record, locale: str) -> dict:
    # Read the lobby metadata defensively for the featured flag.
    lobby = record.get("lobby") if isinstance(record.get("lobby"), dict) else {}
    # Read the translations map defensively for the localized label.
    translations = record.get("translations") if isinstance(record.get("translations"), dict) else {}
    # Publish only safe, honestly derivable attributes.
    return {
        # Identify the game by its stable catalog id.
        "id": str(record.get("id") or ""),
        # Publish the canonical English label.
        "label": str(record.get("label") or ""),
        # Publish the localized label when the locale ships one, else fall back to the canonical label.
        "localized_label": str((translations.get(locale) or {}).get("label") or record.get("label") or ""),
        # Publish the primary category.
        "category": str(record.get("category") or ""),
        # Publish every category tag so a comparison can group by shared families.
        "categories": [str(tag) for tag in record.get("categories", []) if tag],
        # State that every catalogued game is ledger-backed play-token only; this is a safety attribute, not math.
        "ledger_backed": True,
        # Publish whether the game is featured in the lobby.
        "featured": bool(lobby.get("featured")),
        # Publish whether the game ships the requested locale so a player can compare localization readiness.
        "localization_ready": _localization_ready(record, locale),
        # State explicitly that no money-math attribute is included in this comparison.
        "includes_money_math": False,
    }


# Validate and normalize the requested game slugs.
def _requested_slugs(games) -> list:
    # Accept either a list or a comma-separated string of game ids.
    raw = games if isinstance(games, list) else str(games or "").split(",")
    # Normalize each candidate to a bounded lower-case slug.
    slugs = []
    # Validate each requested game.
    for candidate in raw:
        # Normalize the candidate slug.
        slug = str(candidate or "").strip().lower()
        # Skip an empty segment from a trailing comma.
        if not slug:
            # Move to the next candidate.
            continue
        # Reject an unusable game identifier rather than silently dropping it.
        if len(slug) > GAME_SLUG_MAX or not all(character.isalnum() or character in "_-" for character in slug):
            # Fail closed on a malformed identifier.
            raise ValidationError("Compare requires valid game ids", {"reason": "invalid_game"})
        # Retain the first occurrence only so duplicates do not pad the table.
        if slug not in slugs:
            # Add the validated slug.
            slugs.append(slug)
    # Require at least two games to compare.
    if len(slugs) < 2:
        # Reject a comparison that is not actually a comparison.
        raise ValidationError("Compare requires at least two games", {"reason": "too_few_games"})
    # Reject a request larger than the accepted bound.
    if len(slugs) > MAX_COMPARE:
        # Publish the bound so a client can correct itself.
        raise ValidationError("Compare requests too many games", {"reason": "too_many_games", "max": MAX_COMPARE})
    # Return the validated slug list.
    return slugs


# Build the product-safe comparison for the requested games.
def compare(games, *, locale: str = "en-US") -> dict:
    # Validate and normalize the requested game ids.
    slugs = _requested_slugs(games)
    # Normalize the requested locale to one the catalog can key on.
    resolved_locale = locale if locale in ("en-US", "ru-RU") else "en-US"
    # Index the catalog once.
    catalog = _catalog_index()
    # Resolve which requested games actually exist in the catalog.
    known = [slug for slug in slugs if slug in catalog]
    # Report any requested game that is not in the catalog rather than silently omitting it.
    missing = [slug for slug in slugs if slug not in catalog]
    # Build one safe comparison row per known game.
    rows = [_compare_row(catalog[slug], resolved_locale) for slug in known]
    # Publish the comparison together with the safe attribute list and an explicit money-math exclusion.
    return {"games": rows, "missing": missing, "locale": resolved_locale, "attributes": ["category", "ledger_backed", "featured", "localization_ready"], "excludes_money_math": sorted(FORBIDDEN_ATTRIBUTES)}
