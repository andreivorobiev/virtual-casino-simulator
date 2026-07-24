"""Focused play-token receipt derivation tests. (#161, RECEIPT-001, RECEIPT-002)"""

# Import SHA-256 so the additive v2 contract stays pinned to exact reviewed bytes.
import hashlib
# Import JSON parsing for the shipped localization resources and digest inventory.
import json
# Import filesystem paths for locating tracked resources and sources.
import pathlib
# Import regular expressions for harvesting the committed transaction vocabulary.
import re
# Import temporary directories so focused tests never touch repository or user runtime state.
import tempfile
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the authoritative ledger used to seed committed movements.
from casino.core import ledger
# Import the canonical player facade for isolated wallet fixtures.
from casino.core import players
# Import the receipt derivation authority under test.
from casino.core import receipts
# Import provider injection so every test owns its complete durable state.
from casino.core import storage

# Resolve the repository root for resource and source inspection.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Match the committed uppercase transaction vocabulary used across the catalog.
TRANSACTION_RE = re.compile(r'"([A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,5})"')
# Recognize the committed money-movement suffixes that name a ledger transaction type.
MOVEMENT_SUFFIXES = ("DEBIT", "CREDIT", "REFUND", "PLACED", "PURCHASED", "ADDED", "GRANT", "_BET", "ESCROW", "FUNDED", "SETTLEMENT", "PAYOUT", "WAGER")


# Harvest every committed transaction type the catalog actually uses.
def committed_transaction_types() -> set:
    # Collect the distinct vocabulary.
    found = set()
    # Scan the game, bot, and core sources that write ledger movements.
    for directory in ("casino/games", "casino/bots", "casino/core", "casino"):
        # Inspect every tracked Python source beneath the directory.
        for path in (ROOT / directory).glob("**/*.py"):
            # Read the source without executing it.
            text = path.read_text(encoding="utf-8", errors="ignore")
            # Retain only names that end with a money-movement suffix.
            found.update(name for name in TRANSACTION_RE.findall(text) if any(name.endswith(suffix) for suffix in MOVEMENT_SUFFIXES))
    # Return the harvested vocabulary.
    return found


# Verify receipts explain committed movements without inventing or leaking anything.
class ReceiptDerivationTests(unittest.TestCase):
    # Seed two isolated players so every privacy assertion has a real neighbour.
    def setUp(self) -> None:
        # Allocate an automatically cleaned root outside repository runtime state.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-receipts-")
        # Install one isolated JSON provider for players and committed ledger rows.
        storage.set_provider_for_tests(storage.JsonStorageProvider(pathlib.Path(self.temporary.name) / "data"))
        # Create the subject's isolated wallet through the production player facade.
        owner_player = players.create_player("Receipt Owner", "human", 5000)
        # Create an unrelated neighbour wallet used by every privacy assertion.
        other_player = players.create_player("Receipt Other", "human", 5000)
        # Build the authenticated subject shape normally supplied by session resolution.
        self.owner = {"user_id": "receipt_owner", "player_id": owner_player["player_id"], "role": "player", "roles": ["player"], "status": "active"}
        # Build the unrelated authenticated subject without creating auth credentials or secrets.
        self.other = {"user_id": "receipt_other", "player_id": other_player["player_id"], "role": "player", "roles": ["player"], "status": "active"}

    # Release provider injection and isolated files after every assertion.
    def tearDown(self) -> None:
        # Clear the process-global test provider before another suite runs.
        storage.set_provider_for_tests(None)
        # Remove only the TemporaryDirectory-owned state root.
        self.temporary.cleanup()

    # Require the signed amount to decide direction and category for the core cases.
    def test_categories_follow_the_committed_amount(self) -> None:
        # Enumerate representative committed movements with their expected category.
        cases = [("ROULETTE_BET_PLACED", -25.0, receipts.CATEGORY_STAKE), ("SLOTS_SPIN_DEBIT", -5.0, receipts.CATEGORY_STAKE), ("BLACKJACK_SETTLEMENT_CREDIT", 40.0, receipts.CATEGORY_PAYOUT), ("KENO_PAYOUT_CREDIT", 12.5, receipts.CATEGORY_PAYOUT), ("ROULETTE_BET_REFUND", 25.0, receipts.CATEGORY_REFUND), ("TEXAS_HOLDEM_ESCROW_REFUND_CREDIT", 10.0, receipts.CATEGORY_REFUND), ("PLAY_TOKENS_ADDED", 1000.0, receipts.CATEGORY_ADJUSTMENT), ("ADMIN_TOKEN_GRANT", 500.0, receipts.CATEGORY_ADJUSTMENT)]
        # Check every representative movement.
        for transaction_type, amount, expected in cases:
            # Isolate each case so one failure cannot mask the next.
            with self.subTest(transaction_type=transaction_type):
                # Require the expected category.
                self.assertEqual(receipts.classify(transaction_type, amount), expected)

    # Require every committed transaction type in the catalog to receive a usable explanation.
    def test_every_committed_transaction_type_is_explainable(self) -> None:
        # Harvest the vocabulary actually used by the shipped catalog.
        vocabulary = committed_transaction_types()
        # Require the harvest to have found a realistic catalog-sized vocabulary.
        self.assertGreater(len(vocabulary), 50)
        # Explain each committed type in both directions.
        for transaction_type in sorted(vocabulary):
            # Isolate each case so one failure names the offending type.
            with self.subTest(transaction_type=transaction_type):
                # Explain both a debit and credit so signed-direction fallback is covered.
                for amount in (-10.0, 10.0):
                    # Build a receipt for this committed direction.
                    receipt = receipts.explain({"transaction_type": transaction_type, "amount": amount, "game": "roulette", "balance_after": 90.0, "ts": "2026-07-23T00:00:00Z"})
                    # Require a known category rather than an unclassified fallthrough.
                    self.assertIn(receipt["category"], set(receipts.MESSAGE_KEYS))
                    # Require a localization key rather than server-side prose.
                    self.assertTrue(receipt["message_key"].startswith("receipt."))

    # Require a refund issued after an interrupted round to say so rather than reading as a win.
    def test_interrupted_rounds_are_explained_honestly(self) -> None:
        # Build a receipt for a stake returned after a failed round.
        receipt = receipts.explain({"transaction_type": "BLACKJACK_DOUBLE_REFUND_AFTER_ERROR", "amount": 20.0, "game": "blackjack", "balance_after": 120.0, "ts": "2026-07-23T00:00:00Z"})
        # Require the refund category rather than a payout.
        self.assertEqual(receipt["category"], receipts.CATEGORY_REFUND)
        # Require the distinct interrupted-round message rather than the ordinary refund copy.
        self.assertEqual(receipt["message_key"], "receipt.refund_after_error")

    # Require an unknown future transaction type to degrade to a correct generic explanation.
    def test_unknown_transaction_types_degrade_safely(self) -> None:
        # Explain an incoming movement whose type this module has never seen.
        credit = receipts.explain({"transaction_type": "FUTURE_GAME_MYSTERY_MOVEMENT", "amount": 15.0, "game": "future", "balance_after": 115.0, "ts": "2026-07-23T00:00:00Z"})
        # Require a correct incoming classification from the authoritative sign.
        self.assertEqual((credit["category"], credit["direction"]), (receipts.CATEGORY_PAYOUT, "credit"))
        # Explain an outgoing movement of the same unknown type.
        debit = receipts.explain({"transaction_type": "FUTURE_GAME_MYSTERY_MOVEMENT", "amount": -15.0, "game": "future", "balance_after": 85.0, "ts": "2026-07-23T00:00:00Z"})
        # Require a correct outgoing classification.
        self.assertEqual((debit["category"], debit["direction"]), (receipts.CATEGORY_STAKE, "debit"))

    # Require the explained amount and balance to match the committed ledger exactly.
    def test_receipts_never_disagree_with_the_committed_ledger(self) -> None:
        # Commit one real staking movement through the authoritative ledger.
        committed = ledger.debit(self.owner["player_id"], 30, "ROULETTE_BET_PLACED", game="roulette", round_id="round_reconcile_001")
        # Explain the committed row.
        receipt = receipts.explain(committed)
        # Require the unsigned magnitude to match the committed movement.
        self.assertEqual(receipt["amount"], 30.0)
        # Require the direction to reflect the committed sign.
        self.assertEqual(receipt["direction"], "debit")
        # Require the explained balance to be exactly the committed resulting balance.
        self.assertEqual(receipt["balance_after"], committed["balance_after"])

    # Require no raw durable identifier to appear anywhere in a receipt.
    def test_receipts_never_publish_raw_identifiers(self) -> None:
        # Commit a movement bound to a durable round identifier.
        committed = ledger.debit(self.owner["player_id"], 10, "SLOTS_SPIN_DEBIT", game="slots", round_id="round_secret_identifier_12345678")
        # Explain the committed row.
        receipt = receipts.explain(committed)
        # Serialize the whole receipt for leak inspection.
        serialized = json.dumps(receipt)
        # Require the raw round identifier to be absent.
        self.assertNotIn("round_secret_identifier_12345678", serialized)
        # Require the durable player identifier to be absent.
        self.assertNotIn(self.owner["player_id"], serialized)
        # Require the exact public allowlist so internal ledger fields and details cannot escape later.
        self.assertEqual(set(receipt), {"category", "message_key", "game", "amount", "direction", "balance_after", "occurred_at", "reference", "play_tokens_only"})
        # Require only a short correlation reference to be published.
        self.assertEqual(receipt["reference"], "12345678")

    # Require a movement without a round to publish no reference rather than a placeholder.
    def test_movements_without_a_round_publish_no_reference(self) -> None:
        # Explain a top-up that is not bound to any round.
        receipt = receipts.explain({"transaction_type": "PLAY_TOKENS_ADDED", "amount": 1000.0, "game": "", "balance_after": 1000.0, "ts": "2026-07-23T00:00:00Z"})
        # Require an explicit empty reference.
        self.assertEqual(receipt["reference"], "")

    # Require self receipts to exclude another player even with a populated neighbour.
    def test_self_receipts_never_return_another_subject(self) -> None:
        # Commit one movement for each account.
        ledger.debit(self.owner["player_id"], 10, "KENO_TICKET_PURCHASED", game="keno")
        ledger.credit(self.other["player_id"], 999, "SLOTS_PAYOUT_CREDIT", game="slots")
        # Read the owner's own explained movements.
        page = receipts.self_receipts(self.owner, page=1, page_size=50)
        # Require the neighbour's distinctive amount to be absent.
        self.assertNotIn(999.0, [item["amount"] for item in page["receipts"]])
        # Require the owner's own movement to be present.
        self.assertIn(10.0, [item["amount"] for item in page["receipts"]])

    # Require pagination to stay bounded and clamped against hostile inputs.
    def test_self_receipts_pagination_is_bounded(self) -> None:
        # Commit more movements than one page can hold.
        for index in range(12):
            # Commit a distinguishable staking movement.
            ledger.debit(self.owner["player_id"], 1, "SIC_BO_WAGER_DEBIT", game="sic_bo", round_id=f"round_{index:04d}")
        # Request an oversized page.
        oversized = receipts.self_receipts(self.owner, page=1, page_size=9999)
        # Require the page size to clamp to the accepted ceiling.
        self.assertEqual(oversized["page_size"], receipts.MAX_PAGE_SIZE)
        # Request a hostile negative page.
        clamped = receipts.self_receipts(self.owner, page=-3, page_size=5)
        # Require the page index to clamp to the first page.
        self.assertEqual(clamped["page"], 1)
        # Require the clamped page to be full.
        self.assertEqual(len(clamped["receipts"]), 5)
        # Request malformed HTTP-style pagination inputs through the shared parser.
        malformed = receipts.self_receipts(self.owner, page="not-a-page", page_size="not-a-size")
        # Require the documented defaults rather than an internal conversion error.
        self.assertEqual((malformed["page"], malformed["page_size"]), (1, receipts.DEFAULT_PAGE_SIZE))

    # Require a session without a ledger subject to receive an empty page rather than shared data.
    def test_subjectless_sessions_get_an_empty_page(self) -> None:
        # Read receipts for a session carrying no bound player.
        page = receipts.self_receipts({})
        # Require an explicitly empty envelope.
        self.assertEqual((page["receipts"], page["total"]), ([], 0))

    # Require every emitted message key to ship complete EN and RU copy.
    def test_every_message_key_ships_in_both_locales(self) -> None:
        # Collect every key the module can emit, including the interrupted-round variant.
        emitted = set(receipts.MESSAGE_KEYS.values()) | {"receipt.refund_after_error"}
        # Check both shipped locales.
        for locale in ("en-US", "ru-RU"):
            # Isolate each locale so a failure names the offending language.
            with self.subTest(locale=locale):
                # Load the shipped shell resources.
                resources = json.loads((ROOT / "web" / "i18n" / locale / "shell.json").read_text(encoding="utf-8"))
                # Require every emitted key to be translated.
                self.assertEqual(sorted(emitted - set(resources)), [])
                # Require every receipt string to be non-empty.
                for key in emitted:
                    # Require real copy rather than an empty placeholder.
                    self.assertTrue(resources[key].strip())

    # Require the EN and RU copy to use identical placeholders so neither locale drops a value.
    def test_locale_copy_uses_identical_placeholders(self) -> None:
        # Collect every emitted key.
        emitted = sorted(set(receipts.MESSAGE_KEYS.values()) | {"receipt.refund_after_error"})
        # Load both shipped locales.
        english = json.loads((ROOT / "web" / "i18n" / "en-US" / "shell.json").read_text(encoding="utf-8"))
        russian = json.loads((ROOT / "web" / "i18n" / "ru-RU" / "shell.json").read_text(encoding="utf-8"))
        # Compare the placeholder sets for every emitted key.
        for key in emitted:
            # Isolate each key so a failure names the offending string.
            with self.subTest(key=key):
                # Require identical placeholder names in both locales.
                self.assertEqual(set(re.findall(r"\{(\w+)\}", english[key])), set(re.findall(r"\{(\w+)\}", russian[key])))

    # Require every receipt to carry the toy-simulator framing rather than implying cash value.
    def test_receipts_state_play_tokens_only(self) -> None:
        # Explain any committed movement.
        receipt = receipts.explain({"transaction_type": "SLOTS_PAYOUT_CREDIT", "amount": 50.0, "game": "slots", "balance_after": 150.0, "ts": "2026-07-23T00:00:00Z"})
        # Require the explicit no-cash-value marker.
        self.assertTrue(receipt["play_tokens_only"])

    # Require repeated reads to be stable and preserve one receipt per committed movement.
    def test_repeated_reads_preserve_committed_duplicate_movements(self) -> None:
        # Commit two authoritative movements with identical public categories and distinct round references.
        ledger.debit(self.owner["player_id"], 5, "ROULETTE_BET_PLACED", game="roulette", round_id="round_duplicate_00000001")
        # Commit the second movement independently so the receipt view never deduplicates ledger truth.
        ledger.debit(self.owner["player_id"], 5, "ROULETTE_BET_PLACED", game="roulette", round_id="round_duplicate_00000002")
        # Read the same bounded page twice without mutating the ledger.
        first = receipts.self_receipts(self.owner, page=1, page_size=10)
        # Repeat the read to model retry and refresh behavior.
        second = receipts.self_receipts(self.owner, page=1, page_size=10)
        # Require a stable projection with one explanation for each committed movement.
        self.assertEqual(first, second)
        # Require both committed correlation tails to remain present and distinct.
        self.assertEqual([item["reference"] for item in first["receipts"]], ["00000002", "00000001"])

    # Require the additive route shape and exact checked contract to remain aligned.
    def test_v2_route_shape_and_contract_digest_are_current(self) -> None:
        # Import router construction lazily so isolated provider injection is already active.
        from casino.app import build_router
        # Commit one movement for the route-level projection.
        ledger.credit(self.owner["player_id"], 25, "SLOTS_PAYOUT_CREDIT", game="slots", round_id="round_route_receipt_12345678")
        # Build one listener-free route table over the production handlers.
        router = build_router()
        # Read the exact additive v2 endpoint with hostile query strings.
        page = router.dispatch("GET", "/api/v2/me/receipts?page=bad&page_size=bad", {}, {"user": self.owner})
        # Require safe defaults and the one session-derived receipt.
        self.assertEqual((page["page"], page["page_size"], page["total"]), (1, receipts.DEFAULT_PAGE_SIZE, 1))
        # Require the route to publish the expected safe correlation tail.
        self.assertEqual(page["receipts"][0]["reference"], "12345678")
        # Resolve and read the checked shared self-service v2 contract.
        contract_path = ROOT / "contracts" / "openapi" / "user-settings.v2.yaml"
        # Read exact bytes for route anchors and digest verification.
        contract_bytes = contract_path.read_bytes()
        # Decode the contract once for its required receipt route and schemas.
        contract_text = contract_bytes.decode("utf-8")
        # Require the shipped route, envelope, privacy marker, and no raw round identifier field.
        self.assertTrue(all(anchor in contract_text for anchor in ("/me/receipts:", "ReceiptEnvelope:", "play_tokens_only:", "reference:")))
        # Parse the central exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Require the reviewed contract bytes to match the checked digest.
        self.assertEqual(digests["contracts/openapi/user-settings.v2.yaml"], hashlib.sha256(contract_bytes).hexdigest())
