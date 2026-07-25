"""Focused enumeration-safe passwordless magic-link login tests. (#337, MAGIC-001..003)"""

# Import the standard unittest framework used by the repository's focused suites.
import unittest
# Import random UUIDs so repeated/full-suite fixture mailboxes never collide.
import uuid

# Import the canonical identity boundary for account seeding and session verification.
from casino.core import auth
# Import the magic-link login service under test.
from casino.core import magic_link
# Import the purpose-bound token foundation for cross-purpose isolation checks.
from casino.core import one_time_tokens
# Import atomic document mutation for the inactive-account fixture.
from casino.core.state_store import update_json
# Import the standard bounded application error raised by every rejection.
from casino.errors import ValidationError

# Use a digest key long enough to satisfy the service's minimum keyed-digest policy.
TEST_DIGEST_KEY = "magic-link-focused-suite-digest-key-0123456789ab"


# Capture submitted deliveries without touching a provider or the network.
class CaptureMail:
    # Start with no captured deliveries.
    def __init__(self) -> None:
        # Retain every captured submission for assertions.
        self.sent = []

    # Record one submission exactly as the mail foundation would receive it.
    def submit(self, purpose, recipient, *, token, idempotency_key, locale="en-US"):
        # Append the captured delivery for later assertions.
        self.sent.append({"purpose": purpose, "recipient": recipient, "token": token, "locale": locale})
        # Return a provider-neutral acknowledgement.
        return {"status": "captured"}


# Verify the disabled-by-default, enumeration-safe passwordless login lifecycle.
class MagicLinkServiceTests(unittest.TestCase):
    # Build one isolated service plus capture transport for each test.
    def setUp(self) -> None:
        # Capture deliveries instead of submitting them to a provider.
        self.mail = CaptureMail()
        # Namespace every durable identity fixture for this test instance and repeat run.
        self.namespace = uuid.uuid4().hex
        # Construct the service with magic-link enabled unless a test overrides it.
        self.service = magic_link.MagicLinkService(enabled=True, digest_key=TEST_DIGEST_KEY, mail_service=self.mail, audit_sink=lambda event, **fields: None)

    # Seed one active local account and return its normalized mailbox.
    def _seed(self, mailbox: str, password: str = "SeededPassw0rd!23") -> str:
        # Split the listener-free fixture mailbox so the run namespace remains syntactically valid.
        local_part, domain = mailbox.split("@", 1)
        # Build a unique address under the dedicated non-deliverable suite domain.
        isolated_mailbox = f"{local_part}+{self.namespace}@{domain}"
        # Create the canonical account through the identity boundary.
        auth.create_user(isolated_mailbox, password, "Magic Fixture")
        # Return the normalized mailbox used by every binding.
        return auth.normalize_email(isolated_mailbox)

    # Assert one call fails with the single generic login error.
    def _assert_generic(self, call) -> None:
        # Require the uniform public rejection envelope.
        with self.assertRaises(ValidationError) as raised:
            # Invoke the operation that must be rejected.
            call()
        # Require the single non-disclosing reason code.
        self.assertEqual(raised.exception.details, {"reason": "login_link_unavailable"})

    # Require a disabled deployment to accept silently and refuse completion.
    def test_disabled_by_default(self) -> None:
        # Build a service with the release gate closed.
        disabled = magic_link.MagicLinkService(enabled=False, digest_key=TEST_DIGEST_KEY, mail_service=self.mail, audit_sink=lambda event, **fields: None)
        # Seed an eligible account so only the gate can prevent delivery.
        mailbox = self._seed("disabled.case@magic.example.test")
        # Require the identical acknowledgement even while disabled.
        self.assertEqual(disabled.initiate(mailbox), {"status": "accepted"})
        # Require no delivery to have been submitted.
        self.assertEqual(self.mail.sent, [])
        # Require completion to fail closed while disabled.
        self._assert_generic(lambda: disabled.complete("any-token", mailbox))

    # Require identical responses for existing, missing, and malformed mailboxes.
    def test_initiation_is_enumeration_safe(self) -> None:
        # Seed exactly one eligible account.
        mailbox = self._seed("enumeration.real@magic.example.test")
        # Initiate for the real account, an unknown account, and a malformed value.
        responses = [self.service.initiate(mailbox), self.service.initiate("enumeration.missing@magic.example.test"), self.service.initiate("not-an-email")]
        # Require every response to be byte-identical so initiation cannot act as an oracle.
        self.assertEqual(responses, [{"status": "accepted"}] * 3)
        # Require exactly one delivery, addressed only to the eligible account.
        self.assertEqual([item["recipient"] for item in self.mail.sent], [mailbox])
        # Require the delivered link to be bound to the magic-link purpose only.
        self.assertEqual(self.mail.sent[0]["purpose"], "magic_link")

    # Require a successful completion to create a usable session.
    def test_completion_creates_a_session(self) -> None:
        # Seed the eligible account.
        mailbox = self._seed("completion.case@magic.example.test")
        # Begin login so a bearer is delivered.
        self.service.initiate(mailbox)
        # Complete login with the delivered bearer.
        result = self.service.complete(self.mail.sent[0]["token"], mailbox)
        # Require the generic success envelope with session material.
        self.assertEqual(result["status"], "logged_in")
        # Require a real session token to have been issued.
        self.assertTrue(result["session"]["token"])
        # Require the issued session to authenticate as the seeded account.
        session, user = auth.authenticate_token(result["session"]["token"])
        # Require the authenticated identity to match the seeded mailbox.
        self.assertEqual(auth.normalize_email(user["email"]), mailbox)

    # Require replay, wrong subject, and unknown bearers to fail identically.
    def test_replay_and_subject_binding_fail_closed(self) -> None:
        # Seed the eligible account and deliver a bearer.
        mailbox = self._seed("binding.case@magic.example.test")
        self.service.initiate(mailbox)
        # Capture the delivered bearer.
        token = self.mail.sent[0]["token"]
        # Require a bearer presented for another mailbox to be rejected.
        self._assert_generic(lambda: self.service.complete(token, "binding.other@magic.example.test"))
        # Consume the bearer legitimately.
        self.service.complete(token, mailbox)
        # Require replay of the consumed bearer to be rejected.
        self._assert_generic(lambda: self.service.complete(token, mailbox))
        # Require an unknown bearer to be rejected the same way.
        self._assert_generic(lambda: self.service.complete("unknown-bearer-value", mailbox))

    # Require a magic-link bearer to be useless for any other token purpose.
    def test_bearer_is_bound_to_its_own_purpose(self) -> None:
        # Seed the eligible account and deliver a magic-link bearer.
        mailbox = self._seed("purpose.case@magic.example.test")
        self.service.initiate(mailbox)
        # Capture the delivered bearer.
        token = self.mail.sent[0]["token"]
        # Require consuming the bearer under a different purpose to fail rather than succeed.
        with self.assertRaises(Exception):
            # Attempt to spend the magic-link bearer as a password-reset token.
            one_time_tokens.consume("password_reset", token, subject=mailbox, idempotency_key="")
        # Require the bearer to still complete a genuine magic-link login afterwards.
        self.assertEqual(self.service.complete(token, mailbox)["status"], "logged_in")

    # Require an inactive account to be silently ineligible for a login link.
    def test_inactive_account_is_not_eligible(self) -> None:
        # Seed an account and then mark it inactive.
        mailbox = self._seed("inactive.case@magic.example.test")
        # Read the seeded identity so its durable id can be targeted.
        user_id = auth.find_user_by_email(mailbox)["user_id"]
        # Deactivate the account atomically.
        def deactivate(state: dict) -> dict:
            # Iterate the users container to find the seeded identity.
            for record in state.get("users", []):
                # Match the seeded identity.
                if record.get("user_id") == user_id:
                    # Mark the account inactive.
                    record["status"] = "disabled"
            # Return the mutated document.
            return state
        # Persist the inactive fixture.
        update_json(auth.USERS_PATH, deactivate, auth.default_users)
        # Require the identical acknowledgement with no delivery attempted.
        self.assertEqual(self.service.initiate(mailbox), {"status": "accepted"})
        # Require no delivery to an inactive account.
        self.assertEqual(self.mail.sent, [])

    # Require a social-only identity to remain outside the local magic-link boundary.
    def test_social_only_account_is_not_eligible(self) -> None:
        # Seed an account and then model a credential-free externally linked identity.
        mailbox = self._seed("social.case@magic.example.test")
        # Read the seeded identity so its durable id can be targeted.
        user_id = auth.find_user_by_email(mailbox)["user_id"]
        # Remove local credential ownership under the canonical identity transaction.
        def make_social_only(state: dict) -> dict:
            # Iterate the users container to find the seeded identity.
            for record in state.get("users", []):
                # Match the seeded identity.
                if record.get("user_id") == user_id:
                    # Mark the account as provider-owned and remove the local password credential.
                    record.update({"identity_provider": "google", "password_hash": ""})
            # Return the mutated document.
            return state
        # Persist the provider-only fixture.
        update_json(auth.USERS_PATH, make_social_only, auth.default_users)
        # Require the enumeration-safe acknowledgement without creating a local session path.
        self.assertEqual(self.service.initiate(mailbox), {"status": "accepted"})
        # Require no delivery to a credential-free provider identity.
        self.assertEqual(self.mail.sent, [])

    # Require a delivery rejection to leave no usable bearer behind.
    def test_rejected_delivery_revokes_the_unsent_bearer(self) -> None:
        # Model the mail foundation refusing a flooded or failing recipient.
        class RejectingMail:
            # Reject every submission the way a rate-limited provider boundary would.
            def submit(self, purpose, recipient, *, token, idempotency_key, locale="en-US"):
                # Retain the bearer so the test can prove it was revoked afterwards.
                self.last_token = token
                # Raise the delivery rejection.
                raise RuntimeError("recipient rate limited")
        # Build a service whose deliveries are always rejected.
        rejecting = RejectingMail()
        service = magic_link.MagicLinkService(enabled=True, digest_key=TEST_DIGEST_KEY, mail_service=rejecting, audit_sink=lambda event, **fields: None)
        # Seed an eligible account.
        mailbox = self._seed("rejected.delivery@magic.example.test")
        # Require the identical acknowledgement even though delivery failed.
        self.assertEqual(service.initiate(mailbox), {"status": "accepted"})
        # Require the undelivered bearer to have been revoked rather than left valid.
        self._assert_generic(lambda: service.complete(rejecting.last_token, mailbox))
        # Require no active bearer to remain for the mailbox.
        self.assertEqual(magic_link.one_time_tokens.active_count(magic_link.PURPOSE, mailbox), 0)
