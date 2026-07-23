"""Focused version-aware What's New eligibility tests. (#165, TOUR-001, TOUR-002)"""

# Import JSON parsing for the curated metadata and shipped resources.
import json
# Import filesystem paths for locating tracked resources.
import pathlib
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the canonical application release the module stamps dismissals with.
from casino.config import APP_VERSION
# Import the canonical identity boundary for account seeding.
from casino.core import auth
# Import the What's New eligibility authority under test.
from casino.core import whats_new
# Import the standard bounded application error every rejection uses.
from casino.errors import ValidationError

# Resolve the repository root for resource inspection.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Build one isolated curated catalog fixture.
def catalog(entries, cap=3):
    # Return the normalized catalog shape the module consumes.
    return {"entries": entries, "changelog_path": "RELEASE_NOTES.md", "max_merged_entries": cap}


# Verify tour eligibility follows curated opt-in rather than version churn.
class WhatsNewTests(unittest.TestCase):
    # Seed one account per test so dismissals never collide.
    def setUp(self) -> None:
        # Derive a per-test mailbox suffix.
        unique = self.id().rsplit(".", 1)[1]
        # Create the subject whose tour state is under test.
        self.owner = auth.create_user(f"tour.{unique}@example.test", "TourPassw0rd!23", "Tour Owner")

    # Require an opted-in curated entry to be eligible for a first-time viewer.
    def test_curated_entry_is_eligible(self) -> None:
        # Build a catalog with one opted-in entry at the running release.
        fixture = catalog([{"version": APP_VERSION, "show_in_whats_new": True, "title_key": "t", "body_key": "b"}])
        # Require the entry to be selected for a viewer who has seen nothing.
        self.assertEqual([entry["version"] for entry in whats_new.eligible_entries("", fixture)], [APP_VERSION])

    # Require a version bump without the explicit opt-in to trigger nothing.
    def test_version_bump_alone_never_triggers_a_tour(self) -> None:
        # Build a catalog whose entries were never opted in by the release coordinator.
        fixture = catalog([{"version": APP_VERSION, "show_in_whats_new": False, "title_key": "t", "body_key": "b"}, {"version": "9.4.0", "title_key": "t", "body_key": "b"}])
        # Require no entry to be eligible despite both versions being current or older.
        self.assertEqual(whats_new.eligible_entries("", fixture), [])

    # Require a truthy-but-not-true opt-in value to be refused so only an explicit flag counts.
    def test_opt_in_must_be_exactly_true(self) -> None:
        # Enumerate values that are truthy but are not the explicit opt-in.
        for value in ("true", 1, "yes", [1]):
            # Isolate each case so a failure names the offending value.
            with self.subTest(value=value):
                # Build a catalog carrying the ambiguous flag.
                fixture = catalog([{"version": APP_VERSION, "show_in_whats_new": value, "title_key": "t", "body_key": "b"}])
                # Require no entry to be eligible.
                self.assertEqual(whats_new.eligible_entries("", fixture), [])

    # Require a dismissed release never to reappear.
    def test_dismissed_release_does_not_return(self) -> None:
        # Build a catalog with one opted-in entry at the running release.
        fixture = catalog([{"version": APP_VERSION, "show_in_whats_new": True, "title_key": "t", "body_key": "b"}])
        # Require nothing to be eligible once that release is acknowledged.
        self.assertEqual(whats_new.eligible_entries(APP_VERSION, fixture), [])

    # Require several skipped releases to merge into one capped tour rather than stacking.
    def test_skipped_releases_merge_into_one_capped_tour(self) -> None:
        # Build five opted-in entries spanning several releases below the running one.
        entries = [{"version": f"9.{minor}.0", "show_in_whats_new": True, "title_key": "t", "body_key": "b"} for minor in range(1, 6)]
        # Select with a cap of three.
        selected = whats_new.eligible_entries("9.0.0", catalog(entries, cap=3))
        # Require exactly the cap to be returned rather than every skipped release.
        self.assertEqual(len(selected), 3)
        # Require the most recent meaningful entries, newest first.
        self.assertEqual([entry["version"] for entry in selected], ["9.5.0", "9.4.0", "9.3.0"])

    # Require an entry newer than the running application to stay hidden.
    def test_unreleased_entries_never_leak_early(self) -> None:
        # Build a catalog containing a future release.
        fixture = catalog([{"version": "99.0.0", "show_in_whats_new": True, "title_key": "t", "body_key": "b"}])
        # Require the unreleased entry to be excluded.
        self.assertEqual(whats_new.eligible_entries("", fixture), [])

    # Require a malformed or absent curated catalog to degrade to no tour.
    def test_malformed_catalog_degrades_to_no_tour(self) -> None:
        # Require a non-object catalog to yield nothing rather than raising.
        self.assertEqual(whats_new.eligible_entries("", catalog([])), [])
        # Require entries missing a version to be dropped.
        self.assertEqual(whats_new.eligible_entries("", catalog([{"show_in_whats_new": True}])), [])

    # Require the player payload to carry localization keys and never a raw version key.
    def test_payload_never_exposes_raw_version_keys(self) -> None:
        # Build the tour payload for the seeded subject.
        payload = whats_new.tour_for(self.owner)
        # Serialize the payload for leak inspection.
        serialized = json.dumps(payload)
        # Require the running version string to be absent from the player payload.
        self.assertNotIn(APP_VERSION, serialized)
        # Require every published entry to carry only localization keys.
        for entry in payload["entries"]:
            # Require the exact key-only entry shape.
            self.assertEqual(set(entry), {"title_key", "body_key"})

    # Require dismissal to persist and be stamped from the server's canonical version.
    def test_dismissal_persists_and_is_server_stamped(self) -> None:
        # Read the tour before dismissing.
        before = whats_new.tour_for(self.owner)
        # Require the shipped catalog to actually offer a tour so the test proves something.
        self.assertTrue(before["show"])
        # Dismiss the tour without supplying any version.
        result = whats_new.dismiss(self.owner)
        # Require the dismissal to be confirmed.
        self.assertTrue(result["dismissed"])
        # Require the tour to be gone on the next read.
        self.assertFalse(whats_new.tour_for(self.owner)["show"])

    # Require one subject's dismissal to leave another subject's tour intact.
    def test_dismissal_is_scoped_to_the_subject(self) -> None:
        # Seed an unrelated account.
        other = auth.create_user("tour.neighbour@example.test", "OtherPassw0rd!23", "Tour Other")
        # Dismiss only the owner's tour.
        whats_new.dismiss(self.owner)
        # Require the neighbour to still be offered the tour.
        self.assertTrue(whats_new.tour_for(other)["show"])

    # Require an unauthenticated caller to be refused rather than reading shared state.
    def test_subjectless_sessions_fail_closed(self) -> None:
        # Require the read to reject a session without a durable identity.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless read.
            whats_new.tour_for({})
        # Require the dismissal to reject the same session.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless dismissal.
            whats_new.dismiss({})

    # Require the shipped curated catalog to reference only translated keys in both locales.
    def test_shipped_catalog_keys_are_translated(self) -> None:
        # Load the tracked curated metadata.
        shipped = json.loads((ROOT / "docs" / "releases" / "whats_new.json").read_text(encoding="utf-8"))
        # Load both shipped locales.
        locales = {name: json.loads((ROOT / "web" / "i18n" / name / "shell.json").read_text(encoding="utf-8")) for name in ("en-US", "ru-RU")}
        # Check every curated entry.
        for entry in shipped["entries"]:
            # Check both localization keys the entry references.
            for key in (entry["title_key"], entry["body_key"]):
                # Check both shipped locales.
                for name, resources in locales.items():
                    # Isolate each case so a failure names the missing key and language.
                    with self.subTest(key=key, locale=name):
                        # Require real translated copy rather than a missing or empty key.
                        self.assertTrue(resources.get(key, "").strip())

    # Require the tour to stay clear of terms and privacy consent, which are separate flows.
    def test_tour_never_carries_consent(self) -> None:
        # Load the tracked curated metadata.
        shipped = json.loads((ROOT / "docs" / "releases" / "whats_new.json").read_text(encoding="utf-8"))
        # Inspect every curated entry for a consent-bearing field.
        for entry in shipped["entries"]:
            # Isolate each entry so a failure names the offending release.
            with self.subTest(version=entry["version"]):
                # Require only the curated presentation fields.
                self.assertEqual(set(entry) - {"version", "show_in_whats_new", "title_key", "body_key"}, set())
