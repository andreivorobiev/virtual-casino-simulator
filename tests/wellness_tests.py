"""Focused opt-in session wellness and neutral-copy tests. (#167, WELL-001, WELL-002)"""

# Import SHA-256 so the additive v2 contract stays pinned to exact reviewed bytes.
import hashlib
# Import JSON parsing for the shipped localization resources and digest inventory.
import json
# Import filesystem paths for locating tracked resources.
import pathlib
# Import regular expressions for placeholder parity checks.
import re
# Import temporary directories so focused tests never touch repository runtime state.
import tempfile
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative ledger used to seed committed movements.
from casino.core import ledger
# Import the canonical player facade for isolated wallet fixtures.
from casino.core import players
# Import provider injection so every test owns its complete durable state.
from casino.core import storage
# Import the session wellness authority under test.
from casino.core import wellness
# Import the configured storage provider for malformed-document fixtures.
from casino.core.storage import get_storage_provider
# Import the standard bounded application error every rejection uses.
from casino.errors import ConflictError, ValidationError

# Resolve the repository root for resource inspection.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Enumerate framing the product must never use in wellness copy, per the issue's neutrality rule.
PROHIBITED_EN = ("deposit", "purchase", "buy", "cash", "prize", "redeem", "redemption", "jackpot", "win back", "chase", "recover your", "real money", "reward", "bonus", "streak", "don't miss", "hurry", "last chance")
# Enumerate the same prohibited framing in Russian.
PROHIBITED_RU = ("депозит", "покупк", "купить", "наличн", "приз", "обмен", "джекпот", "отыгра", "реальные деньги", "награда", "бонус", "серия", "успей", "поспеш", "последний шанс")
# Exempt the mandated no-cash-value disclaimer, which denies cash value rather than implying it.
EXEMPT_PHRASES = ("no cash value", "без денежной ценности")


# Verify wellness controls stay opt-in, bounded, reward-free, and neutrally worded.
class SessionWellnessTests(unittest.TestCase):
    # Seed two isolated players so persistence and privacy assertions never touch repository state.
    def setUp(self) -> None:
        # Allocate an automatically cleaned root outside repository runtime state.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-wellness-")
        # Install one isolated JSON provider for settings, players, and committed ledger rows.
        storage.set_provider_for_tests(storage.JsonStorageProvider(pathlib.Path(self.temporary.name) / "data"))
        # Create the subject's isolated wallet through the production player facade.
        owner_player = players.create_player("Wellness Owner", "human", 5000)
        # Create an unrelated neighbour wallet used by the privacy assertion.
        other_player = players.create_player("Wellness Other", "human", 5000)
        # Build the authenticated subject shape normally supplied by session resolution.
        self.owner = {"user_id": "wellness_owner", "player_id": owner_player["player_id"], "role": "player", "roles": ["player"], "status": "active"}
        # Build the unrelated authenticated subject without creating credentials or secrets.
        self.other = {"user_id": "wellness_other", "player_id": other_player["player_id"], "role": "player", "roles": ["player"], "status": "active"}

    # Release provider injection and isolated files after every assertion.
    def tearDown(self) -> None:
        # Clear the process-global test provider before another suite runs.
        storage.set_provider_for_tests(None)
        # Remove only the TemporaryDirectory-owned state root.
        self.temporary.cleanup()

    # Require reminders to be off until a player explicitly opts in.
    def test_reminders_are_opt_in_by_default(self) -> None:
        # Read the untouched subject's configuration.
        record = wellness.read_wellness(self.owner)
        # Require both switches to default off so nothing is imposed on a player.
        self.assertEqual((record["enabled"], record["break_reminder_enabled"]), (False, False))
        # Require a calm default cadence rather than a frequent one.
        self.assertEqual(record["reminder_interval_minutes"], 30)
        # Require registered-account preferences to advertise durable persistence.
        self.assertTrue(record["persisted"])

    # Require an enabled configuration to persist across a fresh read.
    def test_configuration_persists(self) -> None:
        # Opt in with a specific cadence.
        wellness.update_wellness(self.owner, {"enabled": True, "reminder_interval_minutes": 45})
        # Re-read through storage to prove durability.
        record = wellness.read_wellness(self.owner)
        # Require the stored configuration.
        self.assertEqual((record["enabled"], record["reminder_interval_minutes"], record["revision"]), (True, 45, 1))

    # Require stale concurrent writes to fail rather than silently replacing a newer choice.
    def test_stale_revision_is_rejected(self) -> None:
        # Commit the first update against the initial revision.
        first = wellness.update_wellness(self.owner, {"enabled": True, "revision": 0})
        # Require the durable record to advance exactly once.
        self.assertEqual(first["revision"], 1)
        # Attempt another update from the stale initial revision.
        with self.assertRaises(ConflictError):
            # Require the optimistic concurrency boundary to reject it.
            wellness.update_wellness(self.owner, {"break_reminder_enabled": True, "revision": 0})
        # Require the rejected field to remain unchanged.
        self.assertFalse(wellness.read_wellness(self.owner)["break_reminder_enabled"])

    # Require disposable guest preferences to stay explicitly non-durable.
    def test_guest_preferences_never_create_durable_state(self) -> None:
        # Build the disposable guest subject shape used by restricted-preview sessions.
        guest = {"user_id": "guest_wellness", "player_id": self.owner["player_id"], "role": "guest", "guest_analytics_id": "guest-proof"}
        # Apply one valid opt-in choice for the life of the caller's session.
        changed = wellness.update_wellness(guest, {"enabled": True})
        # Require the response to state that the value is not persisted.
        self.assertEqual((changed["enabled"], changed["persisted"]), (True, False))
        # Require a fresh read to return non-durable defaults rather than a stored guest record.
        reread = wellness.read_wellness(guest)
        # Prove no durable preference survived the disposable request.
        self.assertEqual((reread["enabled"], reread["persisted"]), (False, False))

    # Require the cadence floor so reminders can never become countdown pressure.
    def test_reminder_cadence_cannot_become_pressure(self) -> None:
        # Enumerate cadences that must be refused at both ends and by type.
        rejected = [1, 5, 9, 0, -30, 241, 100000, "20", True, 20.5]
        # Check every rejected cadence.
        for interval in rejected:
            # Isolate each case so one failure cannot mask the next.
            with self.subTest(interval=interval):
                # Require the bounded validation error.
                with self.assertRaises(ValidationError) as raised:
                    # Attempt the rejected cadence.
                    wellness.update_wellness(self.owner, {"reminder_interval_minutes": interval})
                # Require the range reason so a client can correct itself.
                self.assertEqual(raised.exception.details.get("reason"), "interval_out_of_range")
        # Require the accepted boundaries themselves to still be settable.
        for interval in (wellness.MIN_INTERVAL_MINUTES, wellness.MAX_INTERVAL_MINUTES):
            # Isolate each boundary.
            with self.subTest(boundary=interval):
                # Require the boundary value to be accepted.
                self.assertEqual(wellness.update_wellness(self.owner, {"reminder_interval_minutes": interval})["reminder_interval_minutes"], interval)

    # Require unknown and privilege fields to reject the whole update.
    def test_unsupported_fields_are_rejected(self) -> None:
        # Submit a legitimate change carrying an unsupported field.
        with self.assertRaises(ValidationError) as raised:
            # Attempt the mixed payload.
            wellness.update_wellness(self.owner, {"enabled": True, "role": "admin"})
        # Require the rejected field to be named without its value.
        self.assertEqual(raised.exception.details.get("fields"), ["role"])
        # Require the legitimate half to have been discarded as well.
        self.assertFalse(wellness.read_wellness(self.owner)["enabled"])

    # Require acknowledging a reminder to grant nothing at all.
    def test_dismissing_a_reminder_is_never_rewarded(self) -> None:
        # Record the balance before acknowledging.
        before = ledger.read_recent(self.owner["player_id"], 100)
        # Acknowledge a reminder.
        result = wellness.acknowledge_reminder(self.owner)
        # Require an explicit statement that nothing was granted.
        self.assertFalse(result["reward_granted"])
        # Require no ledger movement to have been created by the acknowledgement.
        self.assertEqual(len(ledger.read_recent(self.owner["player_id"], 100)), len(before))

    # Require summaries to report committed totals without evaluating them.
    def test_summary_reports_committed_totals_only(self) -> None:
        # Commit a stake and a smaller return.
        ledger.debit(self.owner["player_id"], 100, "ROULETTE_BET_PLACED", game="roulette")
        ledger.credit(self.owner["player_id"], 40, "ROULETTE_SETTLEMENT_CREDIT", game="roulette")
        # Read the neutral summary.
        summary = wellness.session_summary(self.owner)
        # Require the committed staked total.
        self.assertEqual(summary["staked"], 100.0)
        # Require the committed returned total.
        self.assertEqual(summary["returned"], 40.0)
        # Require the plain arithmetic net with no judgement attached.
        self.assertEqual(summary["net"], -60.0)
        # Require the explicit no-cash-value marker.
        self.assertTrue(summary["play_tokens_only"])
        # Require the summary to carry no evaluative verdict field of any kind.
        self.assertEqual(set(summary), {"movements", "staked", "returned", "net", "since", "play_tokens_only"})

    # Require a summary to exclude another player even with a populated neighbour.
    def test_summary_never_includes_another_subject(self) -> None:
        # Commit a large movement for the neighbour only.
        ledger.credit(self.other["player_id"], 5000, "SLOTS_PAYOUT_CREDIT", game="slots")
        # Commit a small movement for the owner.
        ledger.debit(self.owner["player_id"], 7, "SLOTS_SPIN_DEBIT", game="slots")
        # Read the owner's summary.
        summary = wellness.session_summary(self.owner)
        # Require the neighbour's total to be absent.
        self.assertEqual(summary["returned"], 0.0)
        # Require the owner's own stake to be present.
        self.assertEqual(summary["staked"], 7.0)

    # Require a malformed persisted document to degrade to defaults rather than raising.
    def test_malformed_state_recovers(self) -> None:
        # Store truthy malformed fields that must never opt the player in.
        get_storage_provider().write_document(wellness.WELLNESS_DOCUMENT_KEY, {"users": {self.owner["user_id"]: {"enabled": "false", "break_reminder_enabled": 1, "reminder_interval_minutes": 1}}})
        # Require every malformed field to fall back to safe defaults.
        malformed = wellness.read_wellness(self.owner)
        # Prove malformed truthy values cannot enable reminders or bypass the cadence floor.
        self.assertEqual((malformed["enabled"], malformed["break_reminder_enabled"], malformed["reminder_interval_minutes"]), (False, False, wellness.DEFAULT_INTERVAL_MINUTES))
        # Corrupt the wellness document with an unusable container.
        get_storage_provider().write_document(wellness.WELLNESS_DOCUMENT_KEY, {"users": "corrupted"})
        # Require the read to fall back to opt-in defaults.
        self.assertFalse(wellness.read_wellness(self.owner)["enabled"])
        # Require a subsequent write to repair the container and succeed.
        self.assertTrue(wellness.update_wellness(self.owner, {"enabled": True})["enabled"])

    # Require an unauthenticated caller to be refused rather than reading a shared record.
    def test_subjectless_sessions_fail_closed(self) -> None:
        # Require the read to reject a session without a durable identity.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless read.
            wellness.read_wellness({})
        # Require the acknowledgement to reject the same session.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless acknowledgement.
            wellness.acknowledge_reminder({})

    # Require every shipped wellness string to avoid prohibited value and pressure framing.
    def test_shipped_copy_stays_neutral(self) -> None:
        # Check both shipped locales against their own prohibited vocabulary.
        for locale, prohibited in (("en-US", PROHIBITED_EN), ("ru-RU", PROHIBITED_RU)):
            # Load the shipped shell resources.
            resources = json.loads((ROOT / "web" / "i18n" / locale / "shell.json").read_text(encoding="utf-8"))
            # Inspect only the wellness namespace.
            for key, value in resources.items():
                # Skip strings outside this feature.
                if not key.startswith("wellness."):
                    # Move to the next resource.
                    continue
                # Remove the mandated disclaimer before scanning so it cannot mask or trigger a match.
                scanned = value.lower()
                # Strip each approved disclaimer phrase.
                for phrase in EXEMPT_PHRASES:
                    # Remove the exempt phrase from the scanned text.
                    scanned = scanned.replace(phrase, "")
                # Check every prohibited term against the shipped string.
                for term in prohibited:
                    # Isolate each term so a failure names the offending string and word.
                    with self.subTest(locale=locale, key=key, term=term):
                        # Require the prohibited framing to be absent.
                        self.assertNotIn(term, scanned)

    # Require the wellness copy to ship completely in both locales with identical placeholders.
    def test_wellness_copy_ships_in_both_locales(self) -> None:
        # Load both shipped locales.
        english = json.loads((ROOT / "web" / "i18n" / "en-US" / "shell.json").read_text(encoding="utf-8"))
        russian = json.loads((ROOT / "web" / "i18n" / "ru-RU" / "shell.json").read_text(encoding="utf-8"))
        # Collect the wellness namespace from the reference locale.
        keys = sorted(key for key in english if key.startswith("wellness."))
        # Require a realistic feature-sized string set.
        self.assertGreater(len(keys), 10)
        # Compare coverage and placeholders for every key.
        for key in keys:
            # Isolate each key so a failure names the offending string.
            with self.subTest(key=key):
                # Require the Russian translation to exist and be non-empty.
                self.assertTrue(russian.get(key, "").strip())
                # Require identical placeholder names so neither locale drops a value.
                self.assertEqual(set(re.findall(r"\{(\w+)\}", english[key])), set(re.findall(r"\{(\w+)\}", russian[key])))

    # Require the additive routes, active-session summary boundary, and exact contract digest to stay aligned.
    def test_v2_route_shape_and_contract_digest_are_current(self) -> None:
        # Import router construction lazily so isolated provider injection is already active.
        from casino.app import build_router
        # Build one listener-free route table over the production handlers.
        router = build_router()
        # Build the server-owned active-session metadata used as the summary boundary.
        context = {"user": self.owner, "session": {"created_at": "2000-01-01T00:00:00.000Z"}}
        # Read the untouched opt-in configuration through the exact additive v2 route.
        initial = router.dispatch("GET", "/api/v2/me/wellness", {}, context)
        # Require both controls to remain off at the API boundary.
        self.assertEqual((initial["wellness"]["enabled"], initial["wellness"]["break_reminder_enabled"]), (False, False))
        # Update the same authenticated subject without accepting any caller-authored identity.
        changed = router.dispatch("PATCH", "/api/v2/me/wellness", {"enabled": True, "reminder_interval_minutes": 45, "revision": 0}, context)
        # Require the route to publish the stored value and advanced revision.
        self.assertEqual((changed["wellness"]["enabled"], changed["wellness"]["revision"]), (True, 1))
        # Commit one movement after the synthetic active-session boundary.
        ledger.debit(self.owner["player_id"], 10, "ROULETTE_BET_PLACED", game="roulette")
        # Read the neutral current-session summary through the exact additive route.
        summary = router.dispatch("GET", "/api/v2/me/wellness/summary?since=1900-01-01T00:00:00Z", {}, context)
        # Require the server-owned session timestamp to override the hostile caller query.
        self.assertEqual((summary["since"], summary["staked"], summary["play_tokens_only"]), ("2000-01-01T00:00:00.000Z", 10.0, True))
        # Resolve and read the checked shared self-service v2 contract.
        contract_path = ROOT / "contracts" / "openapi" / "user-settings.v2.yaml"
        # Read exact bytes for route anchors and digest verification.
        contract_bytes = contract_path.read_bytes()
        # Decode the contract once for its required wellness routes and schemas.
        contract_text = contract_bytes.decode("utf-8")
        # Require the shipped routes, opt-in fields, session summary, and no-cash-value marker.
        self.assertTrue(all(anchor in contract_text for anchor in ("/me/wellness:", "/me/wellness/summary:", "WellnessSettings:", "break_reminder_enabled:", "play_tokens_only:")))
        # Parse the central exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Require the reviewed contract bytes to match the checked digest.
        self.assertEqual(digests["contracts/openapi/user-settings.v2.yaml"], hashlib.sha256(contract_bytes).hexdigest())
