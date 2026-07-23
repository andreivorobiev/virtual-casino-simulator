"""Focused personal-preference and self-only activity tests. (#352, USER-006, USER-007)"""

# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the canonical identity boundary for account seeding.
from casino.core import auth
# Import the authoritative ledger used to seed self-history fixtures.
from casino.core import ledger
# Import the personal-settings authority under test.
from casino.core import user_settings
# Import the configured storage provider for malformed-document fixtures.
from casino.core.storage import get_storage_provider
# Import the standard bounded application errors every rejection uses.
from casino.errors import ConflictError, ValidationError


# Verify personal preferences and self-history stay bounded, validated, and privately scoped.
class UserSettingsTests(unittest.TestCase):
    # Seed two distinct accounts so every privacy assertion has a real neighbour.
    def setUp(self) -> None:
        # Derive a per-test mailbox suffix so seeded accounts never collide across the shared store.
        unique = self.id().rsplit(".", 1)[1]
        # Create the subject whose settings and history are under test.
        self.owner = auth.create_user(f"owner.{unique}@example.test", "OwnerPassw0rd!23", "Settings Owner")
        # Create an unrelated account whose data must never appear.
        self.other = auth.create_user(f"other.{unique}@example.test", "OtherPassw0rd!23", "Settings Other")

    # Require a fresh account to read canonical defaults rather than failing.
    def test_defaults_apply_before_anything_is_stored(self) -> None:
        # Read the untouched subject's preferences.
        settings = user_settings.read_settings(self.owner)
        # Require the canonical default locale, sound, and starting revision.
        self.assertEqual((settings["locale"], settings["sound_enabled"], settings["revision"]), ("en-US", True, 0))
        # Require the record to be marked durable for a persistent account.
        self.assertTrue(settings["persisted"])

    # Require a saved preference to survive a fresh read from storage.
    def test_saved_preferences_persist_and_advance_the_revision(self) -> None:
        # Apply a supported locale and a sound change.
        updated = user_settings.update_settings(self.owner, {"locale": "ru-RU", "sound_enabled": False})
        # Require the stored values and an advanced revision.
        self.assertEqual((updated["locale"], updated["sound_enabled"], updated["revision"]), ("ru-RU", False, 1))
        # Re-read through storage to prove durability rather than trusting the write's return value.
        reread = user_settings.read_settings(self.owner)
        # Require the re-read record to match exactly.
        self.assertEqual((reread["locale"], reread["sound_enabled"], reread["revision"]), ("ru-RU", False, 1))

    # Require one subject's preferences to stay invisible to another account.
    def test_preferences_are_scoped_to_the_session_subject(self) -> None:
        # Change only the owner's preferences.
        user_settings.update_settings(self.owner, {"locale": "ru-RU"})
        # Require the unrelated account to still read untouched defaults.
        self.assertEqual(user_settings.read_settings(self.other)["locale"], "en-US")

    # Require unsupported locales, non-boolean sound, unknown fields, and empty patches to be rejected.
    def test_invalid_updates_are_rejected_without_persisting(self) -> None:
        # Enumerate every rejected payload shape with its expected reason.
        rejected = [({"locale": "xx-XX"}, "unsupported_locale"), ({"locale": None}, "unsupported_locale"), ({"sound_enabled": "yes"}, "malformed_sound"), ({"role": "admin"}, "unsupported_fields"), ({}, "empty_update")]
        # Check every rejected payload.
        for payload, reason in rejected:
            # Isolate each case so one failure cannot mask the next.
            with self.subTest(payload=payload):
                # Require the standard bounded validation error.
                with self.assertRaises(ValidationError) as raised:
                    # Attempt the rejected update.
                    user_settings.update_settings(self.owner, payload)
                # Require the exact non-disclosing reason code.
                self.assertEqual(raised.exception.details.get("reason"), reason)
        # Require nothing to have been persisted by any rejected attempt.
        self.assertEqual(user_settings.read_settings(self.owner)["revision"], 0)

    # Require a privilege field submitted alongside a valid change to reject the whole update.
    def test_privilege_fields_can_never_ride_along_with_a_valid_change(self) -> None:
        # Submit a legitimate locale change carrying a privilege escalation attempt.
        with self.assertRaises(ValidationError) as raised:
            # Attempt the mixed payload.
            user_settings.update_settings(self.owner, {"locale": "ru-RU", "role": "admin", "user_id": self.other["user_id"]})
        # Require the rejected field names to be reported without their values.
        self.assertEqual(raised.exception.details.get("fields"), ["role", "user_id"])
        # Require the legitimate half of the payload to have been discarded as well.
        self.assertEqual(user_settings.read_settings(self.owner)["locale"], "en-US")

    # Require a stale revision to be refused so a slower client cannot clobber a newer value.
    def test_stale_updates_fail_closed(self) -> None:
        # Establish revision 1.
        user_settings.update_settings(self.owner, {"locale": "ru-RU", "revision": 0})
        # Require a second write still declaring revision 0 to conflict.
        with self.assertRaises(ConflictError):
            # Attempt the stale write.
            user_settings.update_settings(self.owner, {"sound_enabled": False, "revision": 0})
        # Require the newer stored value to have survived untouched.
        self.assertEqual(user_settings.read_settings(self.owner)["locale"], "ru-RU")
        # Require a write at the current revision to still succeed.
        self.assertEqual(user_settings.update_settings(self.owner, {"sound_enabled": False, "revision": 1})["revision"], 2)

    # Require a malformed persisted document to degrade to defaults rather than raising.
    def test_malformed_state_is_preserved_and_recoverable(self) -> None:
        # Corrupt the personal-settings document with an unusable container.
        get_storage_provider().write_document(user_settings.SETTINGS_DOCUMENT_KEY, {"users": "corrupted"})
        # Require the read to fall back to canonical defaults.
        self.assertEqual(user_settings.read_settings(self.owner)["locale"], "en-US")
        # Require a subsequent write to repair only this module's container and succeed.
        self.assertEqual(user_settings.update_settings(self.owner, {"locale": "ru-RU"})["locale"], "ru-RU")

    # Require guest trials to change settings in session without creating a durable record.
    def test_guest_settings_stay_session_local(self) -> None:
        # Model a disposable guest trial session.
        guest = {"user_id": "user_guest_case", "role": "guest", "player_id": "player_guest_case"}
        # Require the guest read to be marked non-persisted.
        self.assertFalse(user_settings.read_settings(guest)["persisted"])
        # Apply a guest preference change.
        updated = user_settings.update_settings(guest, {"locale": "ru-RU"})
        # Require the requested value to be returned but explicitly non-durable.
        self.assertEqual((updated["locale"], updated["persisted"]), ("ru-RU", False))
        # Require no durable record to have been created for the guest.
        document = get_storage_provider().read_document(user_settings.SETTINGS_DOCUMENT_KEY, dict)
        # Require the guest subject to be absent from persisted state.
        self.assertNotIn("user_guest_case", (document or {}).get("users", {}))

    # Require self-history to return only the session's own rows even with hostile inputs.
    def test_self_history_never_returns_another_subject(self) -> None:
        # Seed one ledger event for each account.
        ledger.credit(self.owner["player_id"], 100, "OWNER_EVENT", game="roulette")
        ledger.credit(self.other["player_id"], 250, "OTHER_EVENT", game="slots")
        # Read the owner's own history while supplying a hostile foreign identifier.
        page = user_settings.self_history(self.owner, page=1, page_size=50, game="")
        # Collect the transaction types actually returned.
        types = {row["transaction_type"] for row in page["events"]}
        # Require the owner's event to be present.
        self.assertIn("OWNER_EVENT", types)
        # Require the unrelated account's event to be absent.
        self.assertNotIn("OTHER_EVENT", types)
        # Require no durable identifier to be published in any row.
        for row in page["events"]:
            # Require the allowlisted field set exactly.
            self.assertEqual(set(row), set(user_settings.HISTORY_FIELDS))

    # Require pagination to stay bounded, ordered, and stable across pages.
    def test_history_pagination_is_bounded_and_stable(self) -> None:
        # Seed more events than one page can hold.
        for index in range(25):
            # Record a distinguishable event for the owner.
            ledger.credit(self.owner["player_id"], 1, f"EVENT_{index:02d}", game="keno")
        # Read the first page with an oversized request to prove clamping.
        first = user_settings.self_history(self.owner, page=1, page_size=500)
        # Require the page size to be clamped to the accepted ceiling.
        self.assertEqual(first["page_size"], user_settings.MAX_PAGE_SIZE)
        # Read a small first page to check ordering and continuation.
        page_one = user_settings.self_history(self.owner, page=1, page_size=10)
        # Read the second page.
        page_two = user_settings.self_history(self.owner, page=2, page_size=10)
        # Require both pages to be full.
        self.assertEqual((len(page_one["events"]), len(page_two["events"])), (10, 10))
        # Require the pages to be disjoint so nothing is repeated or skipped.
        self.assertEqual(set(row["transaction_type"] for row in page_one["events"]) & set(row["transaction_type"] for row in page_two["events"]), set())
        # Require newest-first ordering on the first page.
        self.assertEqual(page_one["events"][0]["transaction_type"], "EVENT_24")
        # Require the continuation flag to be honest.
        self.assertTrue(page_one["has_more"])

    # Require a negative or zero page index to clamp rather than wrapping the slice.
    def test_hostile_pagination_inputs_clamp(self) -> None:
        # Seed a single event.
        ledger.credit(self.owner["player_id"], 5, "CLAMP_EVENT", game="bingo")
        # Request a negative page and a zero page size.
        page = user_settings.self_history(self.owner, page=-5, page_size=0)
        # Require the page index to clamp to the first page.
        self.assertEqual(page["page"], 1)
        # Require the clamped page to still return the subject's own row.
        self.assertEqual([row["transaction_type"] for row in page["events"]], ["CLAMP_EVENT"])

    # Require the game filter to narrow results without escaping the subject boundary.
    def test_history_game_filter_stays_within_the_subject(self) -> None:
        # Seed events across two games for the owner and one for the neighbour.
        ledger.credit(self.owner["player_id"], 10, "OWNER_ROULETTE", game="roulette")
        ledger.credit(self.owner["player_id"], 10, "OWNER_SLOTS", game="slots")
        ledger.credit(self.other["player_id"], 10, "OTHER_SLOTS", game="slots")
        # Filter the owner's history to one game.
        page = user_settings.self_history(self.owner, game="slots")
        # Require only the owner's matching event.
        self.assertEqual([row["transaction_type"] for row in page["events"]], ["OWNER_SLOTS"])
        # Require the echoed filter to match the applied one.
        self.assertEqual(page["game"], "slots")

    # Require an unauthenticated caller to be refused rather than reading a shared record.
    def test_missing_subject_fails_closed(self) -> None:
        # Require the read to reject a session without a durable identity.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless read.
            user_settings.read_settings({})
        # Require the update to reject the same session.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless update.
            user_settings.update_settings({}, {"locale": "ru-RU"})
