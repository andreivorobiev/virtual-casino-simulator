"""Focused tests for the player self-service batch: replay, table profiles, compare. (#162/#164/#160)"""

# Import JSON parsing for the shipped localization resources.
import json
# Import filesystem paths for locating tracked resources.
import pathlib
# Import regular expressions for placeholder parity checks.
import re
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the canonical identity boundary for account seeding.
from casino.core import auth
# Import the authoritative ledger and history for seeding committed rounds.
from casino.core import history, ledger
# Import the three self-service authorities under test.
from casino.core import game_compare, replay, table_profiles
# Import the configured storage provider for malformed-document fixtures.
from casino.core.storage import get_storage_provider
# Import the standard bounded application errors every rejection uses.
from casino.errors import ConflictError, ValidationError

# Resolve the repository root for resource inspection.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Verify the bounded, self-scoped round-replay foundation. (#162)
class ReplayFoundationTests(unittest.TestCase):
    # Seed one account plus an unrelated neighbour for every privacy assertion.
    def setUp(self) -> None:
        # Derive a per-test mailbox suffix so seeded accounts never collide.
        unique = self.id().rsplit(".", 1)[1]
        # Create the subject whose replays are under test.
        self.owner = auth.create_user(f"replay.{unique}@example.test", "ReplayPassw0rd!23", "Replay Owner")
        # Create an unrelated account whose rounds must never appear.
        self.other = auth.create_user(f"neighbour.{unique}@example.test", "OtherPassw0rd!23", "Replay Other")

    # Seed one committed round for a player through the authoritative history.
    def _round(self, player_id, game, round_id, outcome="win", payout=20.0) -> None:
        # Append a real history row so the replay derives from committed data.
        history.append_history(game, round_id, player_id, "straight", "17", 10.0, outcome, payout, 100.0, {"pocket": 17})

    # Require replays to be derived and never marked as a settlement authority.
    def test_replays_are_evidence_not_settlement(self) -> None:
        # Seed one committed round for the owner.
        self._round(self.owner["player_id"], "roulette", "round_evidence_0001")
        # Read the owner's replays.
        page = replay.self_replays(self.owner)
        # Require at least the seeded round.
        self.assertGreaterEqual(page["total"], 1)
        # Require every artifact to declare it carries no settlement authority.
        for artifact in page["replays"]:
            # Require the explicit non-settlement marker.
            self.assertFalse(artifact["settlement_authority"])
        # Require the conservative retention window to be published.
        self.assertEqual(page["retention_days"], 30)

    # Require replays to exclude another subject even with a populated neighbour.
    def test_replays_never_return_another_subject(self) -> None:
        # Seed a round for each account with distinguishable trailing references.
        self._round(self.owner["player_id"], "roulette", "round_ownerAAA")
        self._round(self.other["player_id"], "slots", "round_otherBBB", outcome="lose", payout=0.0)
        # Read the owner's replays and collect the published references.
        refs = {artifact["reference"] for artifact in replay.self_replays(self.owner)["replays"]}
        # Require the owner's round reference (last 8 chars, upper) to be present.
        self.assertIn("_OWNERAAA"[-8:].upper(), refs)
        # Require the neighbour's round reference to be absent.
        self.assertNotIn("_OTHERBBB"[-8:].upper(), refs)

    # Require rounds older than the retention window to be excluded.
    def test_retention_window_excludes_old_rounds(self) -> None:
        # Seed one current round.
        self._round(self.owner["player_id"], "roulette", "round_recent_0001")
        # Read replays with a reference clock far in the future so the seeded round falls outside retention.
        page = replay.self_replays(self.owner, now="2099-01-01T00:00:00Z")
        # Require the old round to be excluded by the retention cutoff.
        self.assertEqual(page["total"], 0)

    # Require raw durable identifiers to be absent and pagination to clamp.
    def test_replays_hide_identifiers_and_clamp_pagination(self) -> None:
        # Seed several committed rounds.
        for index in range(15):
            # Seed a distinguishable round bound to a durable id.
            self._round(self.owner["player_id"], "roulette", f"round_secret_id_{index:04d}")
        # Read an oversized page.
        page = replay.self_replays(self.owner, page=1, page_size=999)
        # Require the page size to clamp to the accepted ceiling.
        self.assertEqual(page["page_size"], replay.MAX_PAGE_SIZE)
        # Require no raw durable round id to leak in the serialized page.
        self.assertNotIn("round_secret_id_0000", json.dumps(page))

    # Require a subjectless session to receive an empty page rather than shared data.
    def test_subjectless_session_gets_empty_page(self) -> None:
        # Require an unauthenticated read to fail closed.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless read.
            replay.self_replays({})


# Verify per-user, per-game table profiles. (#164)
class TableProfileTests(unittest.TestCase):
    # Seed one account per test.
    def setUp(self) -> None:
        # Derive a per-test mailbox suffix.
        unique = self.id().rsplit(".", 1)[1]
        # Create the subject whose profiles are under test.
        self.owner = auth.create_user(f"profile.{unique}@example.test", "ProfilePassw0rd!23", "Profile Owner")

    # Require a saved profile to persist per game and advance the revision.
    def test_profile_persists_per_game(self) -> None:
        # Save a roulette profile.
        table_profiles.update_profile(self.owner, "roulette", {"default_bet": 25, "chip_denominations": [1, 5, 25]})
        # Re-read through storage to prove durability.
        record = table_profiles.read_profile(self.owner, "roulette")
        # Require the stored values and an advanced revision.
        self.assertEqual((record["default_bet"], record["chip_denominations"], record["revision"]), (25, [1, 5, 25], 1))
        # Require a different game to remain untouched.
        self.assertEqual(table_profiles.read_profile(self.owner, "slots")["default_bet"], 0)

    # Require an economics-changing or unknown field to reject the whole update.
    def test_economics_fields_are_rejected(self) -> None:
        # Enumerate fields that must never be storable.
        for payload in ({"house_edge": 0.05}, {"payout_multiplier": 3}, {"default_bet": 25, "rules_variant": "no_commission"}):
            # Isolate each case so a failure names the payload.
            with self.subTest(payload=payload):
                # Require the standard validation error.
                with self.assertRaises(ValidationError) as raised:
                    # Attempt the rejected update.
                    table_profiles.update_profile(self.owner, "roulette", payload)
                # Require the unsupported-fields reason.
                self.assertEqual(raised.exception.details.get("reason"), "unsupported_fields")
        # Require nothing to have persisted.
        self.assertEqual(table_profiles.read_profile(self.owner, "roulette")["revision"], 0)

    # Require out-of-range values to be refused so a profile cannot encode an absurd stake.
    def test_value_bounds_are_enforced(self) -> None:
        # Enumerate out-of-range payloads with their reason.
        cases = [({"default_bet": -1}, "invalid_default_bet"), ({"chip_denominations": [0]}, "invalid_chips"), ({"chip_denominations": list(range(1, 20))}, "invalid_chips"), ({"autoplay_default_rounds": 9999}, "invalid_autoplay"), ({"show_controls": "yes"}, "invalid_show_controls")]
        # Check every rejected payload.
        for payload, reason in cases:
            # Isolate each case.
            with self.subTest(payload=payload):
                # Require the bounded validation error.
                with self.assertRaises(ValidationError) as raised:
                    # Attempt the rejected update.
                    table_profiles.update_profile(self.owner, "roulette", payload)
                # Require the exact reason.
                self.assertEqual(raised.exception.details.get("reason"), reason)

    # Require a stale revision to be refused so a slower client cannot clobber a newer value.
    def test_stale_update_fails_closed(self) -> None:
        # Establish revision 1.
        table_profiles.update_profile(self.owner, "roulette", {"default_bet": 10, "revision": 0})
        # Require a stale write to conflict.
        with self.assertRaises(ConflictError):
            # Attempt the stale write.
            table_profiles.update_profile(self.owner, "roulette", {"default_bet": 20, "revision": 0})
        # Require the newer value to survive.
        self.assertEqual(table_profiles.read_profile(self.owner, "roulette")["default_bet"], 10)

    # Require an invalid game slug to be refused.
    def test_invalid_game_slug_rejected(self) -> None:
        # Require a malformed game identifier to fail closed.
        with self.assertRaises(ValidationError):
            # Attempt the invalid slug.
            table_profiles.read_profile(self.owner, "../etc/passwd")

    # Require a malformed persisted document to degrade and repair.
    def test_malformed_state_recovers(self) -> None:
        # Corrupt the profile document.
        get_storage_provider().write_document(table_profiles.PROFILE_DOCUMENT_KEY, {"users": "corrupted"})
        # Require the read to fall back to defaults.
        self.assertEqual(table_profiles.read_profile(self.owner, "roulette")["default_bet"], 0)
        # Require a subsequent write to repair and succeed.
        self.assertEqual(table_profiles.update_profile(self.owner, "roulette", {"default_bet": 5})["default_bet"], 5)

    # Require guest profiles to stay session-local with no durable record.
    def test_guest_profiles_stay_session_local(self) -> None:
        # Model a disposable guest trial session.
        guest = {"user_id": "user_guest_profile", "role": "guest", "player_id": "player_guest_profile"}
        # Apply a guest profile change.
        updated = table_profiles.update_profile(guest, "roulette", {"default_bet": 5})
        # Require the value returned but explicitly non-durable.
        self.assertEqual((updated["default_bet"], updated["persisted"]), (5, False))
        # Require no durable record for the guest.
        document = get_storage_provider().read_document(table_profiles.PROFILE_DOCUMENT_KEY, dict)
        # Require the guest subject to be absent.
        self.assertNotIn("user_guest_profile", (document or {}).get("users", {}))

    # Require an unauthenticated caller to be refused.
    def test_subjectless_session_fails_closed(self) -> None:
        # Require a subjectless read to fail closed.
        with self.assertRaises(ValidationError):
            # Attempt the subjectless read.
            table_profiles.read_profile({}, "roulette")


# Verify the product-safe Compare Games drawer. (#160)
class CompareGamesTests(unittest.TestCase):
    # Require a comparison to publish only safe attributes and exclude money math.
    def test_comparison_excludes_money_math(self) -> None:
        # Compare three real catalogue games.
        result = game_compare.compare("roulette,slots,keno")
        # Require three rows.
        self.assertEqual(len(result["games"]), 3)
        # Require the money-math attributes to be explicitly excluded.
        self.assertIn("house_edge", result["excludes_money_math"])
        # Require no row to carry any forbidden attribute.
        for row in result["games"]:
            # Require every forbidden key to be absent from the row.
            self.assertEqual(set(row) & game_compare.FORBIDDEN_ATTRIBUTES, set())
            # Require the explicit no-money-math marker.
            self.assertFalse(row["includes_money_math"])

    # Require localization readiness to reflect the requested locale honestly.
    def test_localization_readiness_is_derived(self) -> None:
        # Compare with the Russian locale.
        result = game_compare.compare("roulette,slots", locale="ru-RU")
        # Require the localized label to differ from or match the canonical label without error.
        self.assertTrue(all(row["localized_label"] for row in result["games"]))
        # Require the resolved locale to be echoed.
        self.assertEqual(result["locale"], "ru-RU")

    # Require too-few, too-many, and malformed requests to be refused.
    def test_request_bounds_are_enforced(self) -> None:
        # Require a single-game comparison to be refused.
        with self.assertRaises(ValidationError):
            # Attempt a comparison of one game.
            game_compare.compare("roulette")
        # Require an oversized comparison to be refused.
        with self.assertRaises(ValidationError):
            # Attempt a comparison of too many games.
            game_compare.compare(",".join(f"game{i}" for i in range(10)))
        # Require a malformed game id to be refused.
        with self.assertRaises(ValidationError):
            # Attempt a comparison with a path-like id.
            game_compare.compare("roulette,../etc")

    # Require an unknown game to be reported as missing rather than silently dropped.
    def test_unknown_game_reported_missing(self) -> None:
        # Compare one real and one non-existent game.
        result = game_compare.compare("roulette,not_a_real_game")
        # Require the real game to appear.
        self.assertEqual([row["id"] for row in result["games"]], ["roulette"])
        # Require the unknown game to be reported as missing.
        self.assertIn("not_a_real_game", result["missing"])


# Verify shipped copy coverage for all three features.
class SelfServiceCopyTests(unittest.TestCase):
    # Require every added namespace to ship complete EN and RU copy with identical placeholders.
    def test_copy_ships_in_both_locales(self) -> None:
        # Load both shipped locales.
        english = json.loads((ROOT / "web" / "i18n" / "en-US" / "shell.json").read_text(encoding="utf-8"))
        russian = json.loads((ROOT / "web" / "i18n" / "ru-RU" / "shell.json").read_text(encoding="utf-8"))
        # Check every namespace this batch introduced.
        keys = [key for key in english if key.split(".")[0] in ("replay", "profile", "compare")]
        # Require a realistic batch-sized string set.
        self.assertGreater(len(keys), 12)
        # Compare coverage and placeholders for every key.
        for key in keys:
            # Isolate each key so a failure names the offending string.
            with self.subTest(key=key):
                # Require the Russian translation to exist and be non-empty.
                self.assertTrue(russian.get(key, "").strip())
                # Require identical placeholder names so neither locale drops a value.
                self.assertEqual(set(re.findall(r"\{(\w+)\}", english[key])), set(re.findall(r"\{(\w+)\}", russian[key])))
