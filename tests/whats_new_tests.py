# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free What's New authority and UI lifecycle tests. (#165, TOUR-001/002/003, TEST-106)"""

# Import SHA-256 so the additive v2 contract stays pinned to exact reviewed bytes.
import hashlib
# Import JSON parsing for the curated metadata and checked digest inventory.
import json
# Locate the standard or bundled Node runtime for the listener-free UI contract.
import shutil
# Execute the real JavaScript lifecycle without a browser or listener.
import subprocess
# Import temporary directories so tests never touch repository or user runtime state.
import tempfile
# Import the standard unittest framework used by the repository's focused suites.
import unittest
# Import portable paths for isolated storage and checked resources.
from pathlib import Path
# Import patching so malformed catalog reads can be isolated without changing tracked files.
from unittest.mock import patch

# Import the canonical application release used for eligibility and dismissal stamps.
from casino.config import APP_VERSION
# Import provider injection so every test owns its complete durable state.
from casino.core import storage
# Import the What's New eligibility authority under test.
from casino.core import whats_new
# Import the configured provider for direct persistence assertions.
from casino.core.storage import get_storage_provider
# Import the standard bounded application error every subject rejection uses.
from casino.errors import ValidationError

# Resolve checked repository resources independently from the process working directory.
ROOT = Path(__file__).resolve().parents[1]


# Build one isolated curated catalog fixture.
def catalog(entries, cap=3):
    # Return the normalized catalog shape the module consumes.
    return {"entries": entries, "changelog_path": "RELEASE_NOTES.md", "max_merged_entries": cap}


# Build one complete opted-in entry at a selected release.
def entry(version, *, enabled=True):
    # Return the exact release-coordinator-owned entry shape.
    return {"version": version, "show_in_whats_new": enabled, "title_key": "whatsNew.test.title", "body_key": "whatsNew.test.body"}


# Verify authority and optional UI stay curated, private, recoverable, and disabled in shipped metadata.
class WhatsNewTests(unittest.TestCase):
    # Exercise production presentation and asynchronous account isolation through the API governance lane.
    def test_browser_controller_contract(self):
        # Prefer the hosted runtime, falling back to the bundled desktop executable.
        node = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
        # Run deterministic Node tests with a hard bounded process lifetime.
        result = subprocess.run([node, "--test", "tests/unit/whats_new_view.test.mjs"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        # Fail closed on any lifecycle, privacy, or translation regression.
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-6000:])

    # Seed two isolated subjects so dismissal privacy has a populated neighbour.
    def setUp(self) -> None:
        # Allocate an automatically cleaned root outside repository runtime state.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-whats-new-")
        # Install one isolated JSON provider for every tour document read and write.
        storage.set_provider_for_tests(storage.JsonStorageProvider(Path(self.temporary.name) / "data"))
        # Build the registered account shape normally supplied by session resolution.
        self.owner = {"user_id": "whats_new_owner", "player_id": "player_whats_new_owner", "role": "player", "roles": ["player"], "status": "active"}
        # Build an unrelated registered account for cross-subject isolation.
        self.other = {"user_id": "whats_new_other", "player_id": "player_whats_new_other", "role": "player", "roles": ["player"], "status": "active"}

    # Release provider injection and isolated files after every assertion.
    def tearDown(self) -> None:
        # Clear the process-global test provider before another suite runs.
        storage.set_provider_for_tests(None)
        # Remove only the TemporaryDirectory-owned state root.
        self.temporary.cleanup()

    # Require eligibility to follow the exact curated opt-in rather than version churn.
    def test_only_exact_curated_opt_in_is_eligible(self) -> None:
        # Require one explicitly enabled current-release entry to be selected.
        self.assertEqual([item["version"] for item in whats_new.eligible_entries("", catalog([entry(APP_VERSION)]))], [APP_VERSION])
        # Enumerate every value that must not activate a tour.
        for value in (False, None, "true", 1, "yes", [1]):
            # Isolate each invalid opt-in shape.
            with self.subTest(value=value):
                # Require the ambiguous value to select nothing.
                self.assertEqual(whats_new.eligible_entries("", catalog([entry(APP_VERSION, enabled=value)])), [])

    # Require skipped releases to merge into one capped newest-first result.
    def test_skipped_releases_are_capped_and_ordered(self) -> None:
        # Build five complete opted-in entries below or at the running release family.
        entries = [entry(f"9.{minor}.0") for minor in range(1, 6)]
        # Select from a viewer whose acknowledgement predates every fixture.
        selected = whats_new.eligible_entries("9.0.0", catalog(entries, cap=3))
        # Require only the three newest meaningful entries.
        self.assertEqual([item["version"] for item in selected], ["9.5.0", "9.4.0", "9.3.0"])

    # Require future, malformed, incomplete, and badly capped catalogs to fail closed.
    def test_malformed_and_unreleased_entries_never_surface(self) -> None:
        # Enumerate unusable release records.
        malformed = [
            # Reject missing versions.
            {"show_in_whats_new": True, "title_key": "t", "body_key": "b"},
            # Reject incomplete versions.
            entry("0.9.5"),
            # Reject over-extended versions.
            entry("0.9.5.5.1"),
            # Reject non-numeric versions.
            entry("release-current"),
            # Reject entries without a title key.
            {"version": APP_VERSION, "show_in_whats_new": True, "body_key": "b"},
            # Reject entries without a body key.
            {"version": APP_VERSION, "show_in_whats_new": True, "title_key": "t"},
            # Reject future release metadata.
            entry("99.0.0"),
        ]
        # Require every unusable record to be filtered.
        self.assertEqual(whats_new.eligible_entries("", catalog(malformed)), [])
        # Require non-object and non-list catalog shapes to degrade to no entries.
        self.assertEqual(whats_new.eligible_entries("", "not-a-catalog"), [])
        # Require a boolean cap to fall back rather than becoming an accidental one-entry limit.
        selected = whats_new.eligible_entries("", catalog([entry("0.9.5.0"), entry("9.4.0")], cap=True))
        # Require the default cap to preserve both eligible fixtures.
        self.assertEqual(len(selected), 2)
        # Require an oversized configured cap to remain bounded by the published contract ceiling.
        oversized = whats_new.eligible_entries("", catalog([entry(f"9.{minor}.0") for minor in range(1, 6)], cap=99))
        # Require no more than the three contract-bounded entries.
        self.assertEqual(len(oversized), whats_new.DEFAULT_MAX_MERGED_ENTRIES)

    # Require a missing or malformed tracked file to degrade to the empty catalog shape.
    def test_catalog_read_failures_degrade_to_empty(self) -> None:
        # Point the loader at an absent path inside the isolated temporary root.
        with patch.object(whats_new, "WHATS_NEW_PATH", Path(self.temporary.name) / "absent.json"):
            # Require an absent file to publish no eligible entries.
            self.assertEqual(whats_new.load_catalog()["entries"], [])
        # Write malformed JSON only inside the isolated temporary root.
        malformed_path = Path(self.temporary.name) / "malformed.json"
        # Persist intentionally broken bytes for the protected loader.
        malformed_path.write_text("{broken", encoding="utf-8")
        # Point the loader at the isolated malformed file.
        with patch.object(whats_new, "WHATS_NEW_PATH", malformed_path):
            # Require parse failure to publish no eligible entries.
            self.assertEqual(whats_new.load_catalog()["entries"], [])

    # Require a registered dismissal to be durable, subject-scoped, and retry-idempotent.
    def test_dismissal_is_server_stamped_private_and_idempotent(self) -> None:
        # Patch the tracked catalog only in memory so production metadata stays disabled.
        fixture = catalog([entry(APP_VERSION)])
        # Offer the opted-in fixture to both registered subjects.
        with patch.object(whats_new, "load_catalog", return_value=fixture):
            # Require the owner to see the eligible entry before acknowledgement.
            self.assertTrue(whats_new.tour_for(self.owner)["show"])
            # Commit the first server-stamped acknowledgement.
            first = whats_new.dismiss(self.owner)
            # Retry the same acknowledgement.
            second = whats_new.dismiss(self.owner)
            # Require retry to preserve the original committed timestamp.
            self.assertEqual(first, second)
            # Require the acknowledged tour not to return for the owner.
            self.assertFalse(whats_new.tour_for(self.owner)["show"])
            # Require the unrelated subject's eligibility to remain intact.
            self.assertTrue(whats_new.tour_for(self.other)["show"])
        # Read the isolated document directly for the server-owned release stamp.
        document = get_storage_provider().read_document(whats_new.SEEN_DOCUMENT_KEY, dict)
        # Require only the owner record and the canonical running application version.
        self.assertEqual((set(document["users"]), document["users"][self.owner["user_id"]]["last_seen_version"]), ({self.owner["user_id"]}, APP_VERSION))

    # Require guest trials to see no tour and create no durable acknowledgement.
    def test_guest_tour_state_is_disposable(self) -> None:
        # Build the accepted disposable-session markers.
        guest = {"user_id": "guest_whats_new", "player_id": "player_guest_whats_new", "role": "guest", "guest_analytics_id": "analytics-whats-new"}
        # Patch an eligible entry to prove the guest boundary wins over catalog opt-in.
        with patch.object(whats_new, "load_catalog", return_value=catalog([entry(APP_VERSION)])):
            # Require no tour and an explicit non-persisted lifecycle.
            self.assertEqual((whats_new.tour_for(guest)["show"], whats_new.tour_for(guest)["persisted"]), (False, False))
        # Acknowledge for the disposable session.
        result = whats_new.dismiss(guest)
        # Require an explicit non-durable result with no durable timestamp.
        self.assertEqual(result, {"dismissed": True, "dismissed_at": None, "persisted": False})
        # Require no What's New document to have been created.
        self.assertEqual(get_storage_provider().read_document(whats_new.SEEN_DOCUMENT_KEY, lambda: {"users": {}}), {"users": {}})

    # Require published payloads to contain presentation keys but no raw version identifiers.
    def test_payload_exposes_no_raw_version(self) -> None:
        # Patch one eligible current-release entry.
        with patch.object(whats_new, "load_catalog", return_value=catalog([entry(APP_VERSION)])):
            # Build the player-facing payload.
            payload = whats_new.tour_for(self.owner)
        # Serialize once for raw-version leak inspection.
        serialized = json.dumps(payload)
        # Require the canonical release identifier to remain server-private.
        self.assertNotIn(APP_VERSION, serialized)
        # Require the exact bounded response shape.
        self.assertEqual(set(payload), {"show", "entries", "merged_count", "changelog_path", "persisted"})
        # Require entries to contain localization keys only.
        self.assertEqual(set(payload["entries"][0]), {"title_key", "body_key"})

    # Require subjectless calls to fail closed instead of sharing state.
    def test_subjectless_sessions_fail_closed(self) -> None:
        # Require the read to reject a session with no durable subject.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless read.
            whats_new.tour_for({})
        # Require dismissal to reject the same session.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless write.
            whats_new.dismiss({})

    # Require shipped release metadata to match the packaged release and remain opt-out by default.
    def test_shipped_catalog_is_current_translated_and_disabled(self) -> None:
        # Load the tracked curated metadata.
        shipped = json.loads((ROOT / "docs" / "releases" / "whats_new.json").read_text(encoding="utf-8"))
        # Require the catalog to describe only the current packaged release in this server-only slice.
        self.assertEqual([item["version"] for item in shipped["entries"]], [APP_VERSION])
        # Require release-coordinator activation to remain explicitly off until player UI is approved.
        self.assertTrue(all(item.get("show_in_whats_new") is False for item in shipped["entries"]))
        # Load both shipped locales.
        locales = {name: json.loads((ROOT / "web" / "i18n" / name / "shell.json").read_text(encoding="utf-8")) for name in ("en-US", "ru-RU")}
        # Check each presentation key in both shipped locales.
        for item in shipped["entries"]:
            # Require the exact consent-free metadata shape.
            self.assertEqual(set(item), {"version", "show_in_whats_new", "title_key", "body_key"})
            # Check both localization keys.
            for key in (item["title_key"], item["body_key"]):
                # Check both locales independently.
                for locale, resources in locales.items():
                    # Isolate a missing translation precisely.
                    with self.subTest(key=key, locale=locale):
                        # Require real translated copy rather than a missing or empty key.
                        self.assertTrue(resources.get(key, "").strip())

    # Require additive routes and exact contract bytes to stay aligned.
    def test_v2_routes_and_contract_digest_are_current(self) -> None:
        # Import router construction lazily so isolated provider injection is already active.
        from casino.app import build_router
        # Build one listener-free route table over the production handlers.
        router = build_router()
        # Patch one eligible entry for an exact route read.
        with patch.object(whats_new, "load_catalog", return_value=catalog([entry(APP_VERSION)])):
            # Read through the additive session-bound route.
            before = router.dispatch("GET", "/api/v2/me/whats-new", {}, {"user": self.owner})
        # Require the route to offer the injected eligible entry without raw release data.
        self.assertEqual((before["show"], before["merged_count"], before["persisted"]), (True, 1, True))
        # Submit hostile caller-authored version and identity fields; the handler must reject both.
        with self.assertRaises(ValidationError):
            # Attempt to override server-owned dismissal authority.
            router.dispatch("POST", "/api/v2/me/whats-new/dismiss", {"version": "99.0.0", "user_id": self.other["user_id"]}, {"user": self.owner})
        # Dismiss through the exact empty-body contract.
        dismissed = router.dispatch("POST", "/api/v2/me/whats-new/dismiss", {}, {"user": self.owner})
        # Require the route to persist only for the server-owned subject.
        self.assertEqual((dismissed["dismissed"], dismissed["persisted"]), (True, True))
        # Resolve the shared additive v2 contract.
        contract_path = ROOT / "contracts" / "openapi" / "user-settings.v2.yaml"
        # Read exact bytes once for route, schema, and digest verification.
        contract_bytes = contract_path.read_bytes()
        # Decode the contract for required What's New anchors.
        contract_text = contract_bytes.decode("utf-8")
        # Require both routes, bounded payload schemas, and persistence lifecycle.
        self.assertTrue(all(anchor in contract_text for anchor in ("/me/whats-new:", "/me/whats-new/dismiss:", "WhatsNewReadEnvelope:", "WhatsNewDismissEnvelope:", "persisted:")))
        # Parse the exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Require the reviewed contract bytes to match the checked digest.
        self.assertEqual(digests["contracts/openapi/user-settings.v2.yaml"], hashlib.sha256(contract_bytes).hexdigest())
