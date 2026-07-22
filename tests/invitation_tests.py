"""Focused provider-free and cross-process invitation enrollment acceptance. (TEST-091)"""

# Import independent processes for JSON race proof.
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
# Import mutable UTC arithmetic for deterministic cooldown and expiry behavior.
from datetime import datetime, timedelta, timezone
# Import JSON for durable privacy and lifecycle inspection.
import json
# Import hashing so the checked v2 contract remains pinned to exact source bytes.
import hashlib
# Import regular expressions to extract only the ephemeral synthetic bearer from fake mail.
import re
# Import temporary directories so tests never touch user or repository runtime state.
import tempfile
# Import unittest for repository-standard focused assertions.
import unittest
# Import portable paths for isolated JSON/provider documents.
from pathlib import Path

# Import configuration only for restoring test-adjusted policy globals.
from casino import config
# Import canonical account and invitation services under test.
from casino.core import auth, invitations, one_time_tokens, storage
# Import the approved mail service with an injected provider-free transport.
from casino.core.mail import MailService
# Import the generic public invitation error.
from casino.errors import ConflictError, ValidationError

# Use synthetic digest material unrelated to deployment credentials.
TEST_TOKEN_KEY = "invitation-token-test-key-" + ("t" * 32)
# Use an independent synthetic mail/invitation digest key.
TEST_MAIL_KEY = "invitation-mail-test-key-" + ("m" * 32)
# Use a reserved non-routable mailbox only in transient test memory and isolated state.
TEST_RECIPIENT = "invitee@example.invalid"
# Use one policy-compliant synthetic password that never leaves the test process.
TEST_PASSWORD = "Synthetic-Invite-2026!"
# Resolve the repository root for contract and compatibility assertions.
ROOT = Path(__file__).resolve().parents[1]


# Capture transient mail without provider or network access.
class _Transport:
    # Initialize an empty in-memory message collection.
    def __init__(self):
        # Store only transient synthetic messages for bearer extraction.
        self.messages = []

    # Accept one provider payload in memory.
    def send(self, message: dict) -> None:
        # Retain a detached copy for the current test only.
        self.messages.append(dict(message))


# Report fixed ready diagnostics for process workers that never issue mail.
class _ReadyMail:
    # Return the safe ready state required by service construction paths.
    def readiness(self) -> dict:
        # Publish only the fixed status field used by invitation readiness.
        return {"status": "ready"}


# Provide a mutable repository-compatible clock.
class _Clock:
    # Initialize one deterministic future instant.
    def __init__(self):
        # Store an aware UTC datetime for policy arithmetic.
        self.current = datetime(2032, 2, 3, 4, 5, 6, tzinfo=timezone.utc)

    # Return the current repository timestamp.
    def __call__(self) -> str:
        # Format milliseconds with the shared Z suffix.
        return self.current.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    # Advance the deterministic instant.
    def advance(self, seconds: int) -> None:
        # Replace the current instant with its bounded future value.
        self.current += timedelta(seconds=seconds)


# Redeem one already-issued invitation from an independent process.
def _json_redeem_worker(arguments):
    # Unpack only isolated paths and synthetic request fields.
    root, invitation_path, token_path, users_path, token, idempotency_key = arguments
    # Point the canonical auth document at this test-owned shared path.
    auth.USERS_PATH = Path(users_path)
    # Install one process-local JSON player provider over the shared test root.
    storage.set_provider_for_tests(storage.JsonStorageProvider(Path(root) / "players"))
    # Build an independent token service over the shared token document.
    token_service = one_time_tokens.TokenService(store_path=Path(token_path), digest_key=TEST_TOKEN_KEY, audit_sink=lambda level, event, fields: None)
    # Build an independent invitation service over the shared invitation document.
    service = invitations.InvitationService(store_path=Path(invitation_path), enabled=True, enrollment_enabled=True, digest_key=TEST_MAIL_KEY, token_service=token_service, mail_service=_ReadyMail(), audit_sink=lambda event, **fields: None)
    # Start protected redemption so only expected generic failures become false.
    try:
        # Execute the exact same caller-idempotent recovery request.
        result = service.redeem(token, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, idempotency_key)
        # Report whether this process reached the generic success receipt.
        return result == {"status": "enrolled"}
    # Treat a safe race loser as false for bounded aggregate assertions.
    except ValidationError as error:
        # Require the public generic invitation reason only.
        assert error.details == invitations.GENERIC_REDEMPTION_DETAILS
        # Report a safely rejected in-flight competitor.
        return False
    # Always clear the process-local test provider before worker exit.
    finally:
        # Avoid retaining provider state across any reused process worker.
        storage.set_provider_for_tests(None)


# Exercise disabled defaults, delivery, privacy, recovery, terms, and concurrency without a listener.
class InvitationServiceTests(unittest.TestCase):
    # Build isolated services and persistence before each case.
    def setUp(self):
        # Allocate one automatically cleaned test root.
        self.temp_directory = tempfile.TemporaryDirectory()
        # Resolve the portable root path once.
        self.root = Path(self.temp_directory.name)
        # Place invitation state under the isolated root.
        self.invitation_path = self.root / "auth" / "invitations.json"
        # Place token state beside invitations under the isolated root.
        self.token_path = self.root / "auth" / "one_time_tokens.json"
        # Place canonical user state under the isolated root.
        self.users_path = self.root / "auth" / "users.json"
        # Preserve the production auth path before isolated mutation.
        self.original_users_path = auth.USERS_PATH
        # Redirect canonical user persistence into the test root.
        auth.USERS_PATH = self.users_path
        # Install one isolated JSON player provider.
        storage.set_provider_for_tests(storage.JsonStorageProvider(self.root / "players"))
        # Create the deterministic policy clock.
        self.clock = _Clock()
        # Track deterministic opaque identifier allocation.
        self.sequence = 0
        # Capture privacy-safe invitation audit events in memory.
        self.audit_events = []
        # Capture transient synthetic mail in memory.
        self.transport = _Transport()
        # Build the approved mail foundation with fake ready transport and no network.
        self.mail_service = MailService(state_path=self.root / "mail.json", enabled=True, network_enabled=True, provider="postmark", digest_key=TEST_MAIL_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=self.transport, epoch_clock=lambda: self.clock.current.timestamp())

        # Allocate deterministic opaque identifiers without using fixture credentials.
        def id_factory(prefix):
            # Increment the test-local sequence.
            self.sequence += 1
            # Return a route-compatible opaque identifier.
            return f"{prefix}_test_{self.sequence:04d}"

        # Build the isolated token service with deterministic audit suppression.
        self.token_service = one_time_tokens.TokenService(store_path=self.token_path, digest_key=TEST_TOKEN_KEY, clock=self.clock, id_factory=id_factory, audit_sink=lambda level, event, fields: None)
        # Build the invitation service with both repository gates explicitly enabled only in this test.
        self.service = invitations.InvitationService(store_path=self.invitation_path, enabled=True, enrollment_enabled=True, digest_key=TEST_MAIL_KEY, token_service=self.token_service, mail_service=self.mail_service, clock=self.clock, id_factory=id_factory, audit_sink=lambda event, **fields: self.audit_events.append((event, dict(fields))))

    # Restore global seams and remove isolated state after each case.
    def tearDown(self):
        # Restore the canonical runtime user path.
        auth.USERS_PATH = self.original_users_path
        # Clear the injected player provider.
        storage.set_provider_for_tests(None)
        # Delete only the test-owned temporary root.
        self.temp_directory.cleanup()

    # Issue one invitation and return its transient synthetic bearer.
    def issue(self):
        # Create one invitation through the fully composed fake-ready foundations.
        result = self.service.create(TEST_RECIPIENT, "user_admin_test", locale="en-US", idempotency_key="admin-create-idempotency-0001")
        # Require the intended pending lifecycle.
        self.assertEqual(result["status"], "pending")
        # Require exactly one fake provider message.
        self.assertEqual(len(self.transport.messages), 1)
        # Extract the bearer only from the transient fake message body.
        match = re.search(r"[?&]token=([^\s<]+)", self.transport.messages[0]["text_body"])
        # Require the fixed canonical link to contain one bearer.
        self.assertIsNotNone(match)
        # Return the transient bearer without writing it to any fixture.
        return result, match.group(1)

    # Prove defaults are inert and public/Admin projections remain privacy-safe.
    def test_disabled_defaults_and_privacy_safe_delivery(self):
        # Build a service with both repository gates disabled.
        disabled = invitations.InvitationService(store_path=self.invitation_path, enabled=False, enrollment_enabled=False, digest_key=TEST_MAIL_KEY, token_service=self.token_service, mail_service=self.mail_service, clock=self.clock, audit_sink=lambda event, **fields: None)
        # Reject Admin issuance before any token, mail, account, or wallet state exists.
        with self.assertRaises(Exception):
            # Attempt one disabled issuance using only synthetic data.
            disabled.create(TEST_RECIPIENT, "user_admin_test", locale="en-US", idempotency_key="disabled-create-key-0001")
        # Reject public redemption through one generic envelope while disabled.
        with self.assertRaises(ValidationError) as context:
            # Attempt a fully shaped disabled request.
            disabled.redeem("synthetic-token", TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, "disabled-redeem-key-0001")
        # Require the exact non-disclosing reason.
        self.assertEqual(context.exception.details, invitations.GENERIC_REDEMPTION_DETAILS)
        # Issue through the explicitly enabled isolated service.
        result, bearer = self.issue()
        # Require a masked recipient and no raw mailbox in the Admin result.
        self.assertNotIn(TEST_RECIPIENT, json.dumps(result, sort_keys=True))
        # Require a stable masked hint for operator disambiguation.
        self.assertEqual(result["recipient_hint"], "i***@e***.invalid")
        # Require the transient bearer to be absent from invitation and mail durable state.
        self.assertNotIn(bearer, self.invitation_path.read_text(encoding="utf-8"))
        # Require the transient bearer to be absent from the mail state machine.
        self.assertNotIn(bearer, (self.root / "mail.json").read_text(encoding="utf-8"))
        # Require audit events to exclude raw recipient and bearer material.
        self.assertNotIn(TEST_RECIPIENT, json.dumps(self.audit_events, sort_keys=True))
        # Require audit events to exclude the transient bearer.
        self.assertNotIn(bearer, json.dumps(self.audit_events, sort_keys=True))
        # Require no account or player to exist before redemption.
        self.assertEqual(auth.load_users()["users"], [])
        # Require no invitation-owned player before redemption.
        self.assertFalse(any(player.get("player_id", "").startswith("player_invite_") for player in storage.get_storage_provider().load_players(lambda: {"schema_version": config.SCHEMA_VERSION, "players": []})["players"]))

    # Prove concurrent exact create replays allocate at most one token/mail generation.
    def test_concurrent_create_replay_has_one_delivery_owner(self):
        # Submit the same Admin action concurrently through the shared JSON document lock.
        def submit(_index):
            # Start protected submission so the expected in-progress observation is serializable.
            try:
                # Execute the exact same recipient, locale, actor, and caller key.
                return self.service.create(TEST_RECIPIENT, "user_admin_test", locale="en-US", idempotency_key="admin-concurrent-create-key-0001")["status"]
            # Treat only the fixed in-progress conflict as a safe concurrent result.
            except ConflictError:
                # Return one low-cardinality rejected marker.
                return "in_progress"
        # Race four callers so stale load/save behavior cannot pass accidentally.
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Materialize every result from the bounded race.
            results = list(executor.map(submit, range(4)))
        # Require at least one completed pending result and no unexpected lifecycle value.
        self.assertIn("pending", results)
        # Require exactly one fake provider call despite concurrent exact replays.
        self.assertEqual(len(self.transport.messages), 1)
        # Require one durable invitation and one current token generation.
        durable = json.loads(self.invitation_path.read_text(encoding="utf-8"))
        # Verify the single row reached a safe pending or explicit in-progress state.
        self.assertEqual((len(durable["invitations"]), durable["invitations"][0]["delivery_generation"]), (1, 1))

    # Prove current terms, password policy, exact replay, and terminal identity creation.
    def test_redeem_creates_one_active_local_account_and_replays(self):
        # Issue one valid synthetic invitation.
        _result, bearer = self.issue()
        # Reject stale terms without consuming the bearer.
        with self.assertRaises(ValidationError) as stale_terms:
            # Present a historical terms identifier.
            self.service.redeem(bearer, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-0", True, "redeem-idempotency-key-0001")
        # Require the generic public reason.
        self.assertEqual(stale_terms.exception.details, invitations.GENERIC_REDEMPTION_DETAILS)
        # Reject a weak password without consuming the bearer.
        with self.assertRaises(ValidationError) as weak_password:
            # Present a password below the explicit enrollment policy.
            self.service.redeem(bearer, TEST_RECIPIENT, "weak", "Invited Player", "en-US", "private-beta-1", True, "redeem-idempotency-key-0001")
        # Require the same generic public reason.
        self.assertEqual(weak_password.exception.details, invitations.GENERIC_REDEMPTION_DETAILS)
        # Redeem successfully with explicit current terms.
        first = self.service.redeem(bearer, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, "redeem-idempotency-key-0001")
        # Require the identifier-free success receipt.
        self.assertEqual(first, {"status": "enrolled"})
        # Replay the exact lost-response request idempotently.
        self.assertEqual(self.service.redeem(bearer, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, "redeem-idempotency-key-0001"), first)
        # Reject a changed caller idempotency key after terminal consumption.
        with self.assertRaises(ValidationError) as changed_key:
            # Reuse the consumed bearer with changed caller meaning.
            self.service.redeem(bearer, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, "redeem-idempotency-key-0002")
        # Require the generic public reason.
        self.assertEqual(changed_key.exception.details, invitations.GENERIC_REDEMPTION_DETAILS)
        # Read the single canonical invited account.
        users = [user for user in auth.load_users()["users"] if user.get("invitation_id")]
        # Require exactly one active local player account.
        self.assertEqual(len(users), 1)
        # Require active local identity semantics with no social link.
        self.assertEqual((users[0]["status"], users[0]["identity_provider"], users[0]["terms_accepted_version"]), ("active", "local", "private-beta-1"))
        # Require the account-free reservation to be removed after activation.
        self.assertEqual(auth.load_users()["reservations"], [])
        # Require exactly one deterministic invitation-owned player wallet.
        invited_players = [player for player in storage.get_storage_provider().load_players(lambda: {"schema_version": config.SCHEMA_VERSION, "players": []})["players"] if player.get("player_id", "").startswith("player_invite_")]
        # Require one wallet with the fixed non-cashable starting balance.
        self.assertEqual((len(invited_players), invited_players[0]["balance"]), (1, 5000.0))

    # Prove a lost response after token consumption resumes without a burned bearer or orphan account.
    def test_identity_provisioning_failure_is_recoverable(self):
        # Issue one valid synthetic invitation.
        _result, bearer = self.issue()
        # Preserve the real provisioning function before injecting one bounded failure.
        original = auth.provision_invited_user
        # Count the injected process-stop simulation.
        attempts = {"count": 0}

        # Fail only the first provisioning attempt after token consumption.
        def fail_once(*args, **kwargs):
            # Increment the bounded test-local attempt count.
            attempts["count"] += 1
            # Simulate one stopped worker before any identity side effect.
            if attempts["count"] == 1:
                # Raise a value-free process failure.
                raise RuntimeError("synthetic provisioning stop")
            # Resume through the production provisioning function.
            return original(*args, **kwargs)

        # Install the one-shot failure only inside this test process.
        auth.provision_invited_user = fail_once
        # Ensure the original function is restored after the injected failure.
        try:
            # Observe the generic public error from the interrupted first attempt.
            with self.assertRaises(ValidationError):
                # Start the recoverable redemption.
                self.service.redeem(bearer, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, "recoverable-redeem-key-0001")
            # Retry the exact caller request after the simulated process stop.
            result = self.service.redeem(bearer, TEST_RECIPIENT, TEST_PASSWORD, "Invited Player", "en-US", "private-beta-1", True, "recoverable-redeem-key-0001")
        # Restore the production provisioning function unconditionally.
        finally:
            # Remove the test-only failure injection.
            auth.provision_invited_user = original
        # Require terminal success through idempotent token-consume recovery.
        self.assertEqual(result, {"status": "enrolled"})
        # Require exactly one active invited account after recovery.
        self.assertEqual(sum(1 for user in auth.load_users()["users"] if user.get("invitation_id") and user.get("status") == "active"), 1)

    # Prove independent JSON processes converge on one account, one wallet, and one terminal invitation.
    def test_json_cross_process_redemption_is_idempotent(self):
        # Issue one valid synthetic invitation before worker processes start.
        _result, bearer = self.issue()
        # Build serializable arguments pointing only at the shared isolated documents.
        arguments = (str(self.root), str(self.invitation_path), str(self.token_path), str(self.users_path), bearer, "cross-process-redeem-key-0001")
        # Start two independent processes against the same invitation and caller key.
        with ProcessPoolExecutor(max_workers=2) as executor:
            # Collect both bounded process results.
            results = list(executor.map(_json_redeem_worker, [arguments, arguments]))
        # Require at least one successful response and no process exception.
        self.assertTrue(any(results))
        # Require exactly one durable invited identity.
        self.assertEqual(sum(1 for user in auth.load_users()["users"] if user.get("invitation_id")), 1)
        # Require exactly one deterministic invited player wallet.
        players = storage.get_storage_provider().load_players(lambda: {"schema_version": config.SCHEMA_VERSION, "players": []})["players"]
        # Count only invitation-owned deterministic players.
        self.assertEqual(sum(1 for player in players if player.get("player_id", "").startswith("player_invite_")), 1)
        # Require one terminal redeemed invitation.
        durable = json.loads(self.invitation_path.read_text(encoding="utf-8"))
        # Confirm the complete saga reached the terminal state once.
        self.assertEqual([row["status"] for row in durable["invitations"]], ["redeemed"])

    # Prove malformed invitation state is preserved and never normalized during mutation or cleanup.
    def test_malformed_state_is_preserved_for_operator_recovery(self):
        # Create the isolated state directory before writing malformed structure.
        self.invitation_path.parent.mkdir(parents=True, exist_ok=True)
        # Write structurally invalid but valid JSON state for non-destructive recovery proof.
        self.invitation_path.write_text(json.dumps({"schema_version": config.SCHEMA_VERSION, "invitations": "malformed"}), encoding="utf-8")
        # Capture exact bytes before the failed operation.
        before = self.invitation_path.read_bytes()
        # Reject listing through a value-free operator recovery error.
        with self.assertRaises(RuntimeError):
            # Attempt a read-only projection against malformed state.
            self.service.listing()
        # Require exact durable bytes to remain unchanged.
        self.assertEqual(self.invitation_path.read_bytes(), before)

    # Prove the additive v2 contract, digest, and disabled Workroom boundary remain aligned.
    def test_v2_contract_and_compatibility_boundary(self):
        # Resolve the checked invitation contract and digest inventory.
        contract_path = ROOT / "contracts" / "openapi" / "invitations.v2.yaml"
        # Read the complete contract text for fixed route and frozen-boundary assertions.
        contract_text = contract_path.read_text(encoding="utf-8")
        # Require every approved Admin and public v2 path and no frozen v1 path.
        for route in ("/api/v2/admin/invitations:", "/api/v2/admin/invitations/{invitation_id}/resend:", "/api/v2/admin/invitations/{invitation_id}/revoke:", "/api/v2/admin/invitations/cleanup:", "/api/v2/auth/redeem-invitation:"):
            # Require the exact published route declaration.
            self.assertIn(route, contract_text)
        # Reject any frozen v1 invitation route from the additive artifact.
        self.assertNotIn("/api/v1/", contract_text)
        # Load the compatibility authority record without evaluating runtime configuration.
        compatibility = json.loads((ROOT / "contracts" / "compatibility" / "invitation-enrollment.json").read_text(encoding="utf-8"))
        # Require the exact disabled repository-only Workroom approval.
        self.assertEqual(compatibility["authorization"]["repository_merge_approved_in_workroom_issue"], 24)
        # Require every live, provider, DNS, deployment, and public capability to remain denied.
        self.assertTrue(all(compatibility["authorization"][field] is False for field in ("live_mail_authorized", "live_enrollment_authorized", "provider_or_network_authorized", "dns_authorized", "deployment_authorized", "public_signup_or_exposure_authorized")))
        # Load the checked exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Require the invitation contract digest to match its current exact bytes.
        self.assertEqual(hashlib.sha256(contract_path.read_bytes()).hexdigest(), digests["contracts/openapi/invitations.v2.yaml"])


# Execute this focused file directly for local non-browser validation.
if __name__ == "__main__":
    # Run the standard focused test suite with concise output.
    unittest.main()
