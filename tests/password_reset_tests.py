"""Focused enumeration-safe password-recovery service tests. (#334, RESET-001..003)"""

# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the canonical identity boundary for account seeding and verification.
from casino.core import auth
# Import the recovery service under test.
from casino.core import password_reset
# Import atomic document mutation for the credential-free account fixture.
from casino.core.state_store import update_json
# Import the standard bounded application error raised by every rejection.
from casino.errors import ValidationError

# Use a digest key long enough to satisfy the service's minimum keyed-digest policy.
TEST_DIGEST_KEY = "password-reset-focused-suite-digest-key-0123456789"


# Capture submitted deliveries without touching a provider or the network.
class CaptureMail:
    # Start with no captured deliveries.
    def __init__(self) -> None:
        # Retain every captured submission for assertions.
        self.sent = []

    # Record one submission exactly as the mail foundation would receive it.
    def submit(self, purpose: str, recipient: str, *, token: str, idempotency_key: str, locale: str = "en-US") -> dict:
        # Append the captured delivery for later assertions.
        self.sent.append({"purpose": purpose, "recipient": recipient, "token": token, "locale": locale})
        # Return a provider-neutral acknowledgement.
        return {"status": "captured"}


# Verify the disabled-by-default, enumeration-safe recovery lifecycle.
class PasswordResetServiceTests(unittest.TestCase):
    # Build one isolated service plus capture transport for each test.
    def setUp(self) -> None:
        # Capture deliveries instead of submitting them to a provider.
        self.mail = CaptureMail()
        # Construct the service with recovery enabled unless a test overrides it.
        self.service = password_reset.PasswordResetService(enabled=True, digest_key=TEST_DIGEST_KEY, mail_service=self.mail, audit_sink=lambda event, **fields: None)

    # Seed one recoverable local account and return its normalized mailbox.
    def _seed(self, mailbox: str, password: str = "SeededPassw0rd!23") -> str:
        # Create the canonical account through the identity boundary.
        auth.create_user(mailbox, password, "Recovery Fixture")
        # Return the normalized mailbox used by every binding.
        return auth.normalize_email(mailbox)

    # Assert one call fails with the single generic recovery error.
    def _assert_generic(self, call) -> None:
        # Require the uniform public rejection envelope.
        with self.assertRaises(ValidationError) as raised:
            # Invoke the operation that must be rejected.
            call()
        # Require the single non-disclosing reason code.
        self.assertEqual(raised.exception.details, {"reason": "reset_unavailable"})

    # Require a disabled deployment to accept silently and refuse completion.
    def test_disabled_by_default(self) -> None:
        # Build a service with the release gate closed.
        disabled = password_reset.PasswordResetService(enabled=False, digest_key=TEST_DIGEST_KEY, mail_service=self.mail, audit_sink=lambda event, **fields: None)
        # Seed a recoverable account so only the gate can prevent delivery.
        self._seed("disabled.case@example.test")
        # Require the identical acknowledgement even while disabled.
        self.assertEqual(disabled.initiate("disabled.case@example.test"), {"status": "accepted"})
        # Require no delivery to have been submitted.
        self.assertEqual(self.mail.sent, [])
        # Require completion to fail closed while disabled.
        self._assert_generic(lambda: disabled.complete("any-token", "disabled.case@example.test", "BrandNewPassw0rd!"))

    # Require identical responses for existing, missing, and malformed mailboxes.
    def test_initiation_is_enumeration_safe(self) -> None:
        # Seed exactly one recoverable account.
        self._seed("enumeration.real@example.test")
        # Initiate for the real account, an unknown account, and a malformed value.
        responses = [self.service.initiate("enumeration.real@example.test"), self.service.initiate("enumeration.missing@example.test"), self.service.initiate("not-an-email")]
        # Require every response to be byte-identical so initiation cannot act as an oracle.
        self.assertEqual(responses, [{"status": "accepted"}] * 3)
        # Require exactly one delivery, addressed only to the recoverable account.
        self.assertEqual([item["recipient"] for item in self.mail.sent], ["enumeration.real@example.test"])

    # Require a successful completion to replace the credential and revoke sessions.
    def test_completion_replaces_credential_and_revokes_sessions(self) -> None:
        # Seed the recoverable account.
        mailbox = self._seed("completion.case@example.test")
        # Begin recovery so a bearer is delivered.
        self.service.initiate(mailbox)
        # Complete recovery with a policy-compliant password.
        result = self.service.complete(self.mail.sent[0]["token"], mailbox, "ReplacedPassw0rd!9")
        # Require the generic success envelope with a session-revocation count.
        self.assertEqual(result["status"], "reset")
        self.assertIn("sessions_revoked", result)
        # Require the stored credential to verify against the new password.
        self.assertTrue(auth.verify_password("ReplacedPassw0rd!9", auth.find_user_by_email(mailbox)["password_hash"]))

    # Require replay, wrong subject, and unknown bearers to fail identically.
    def test_replay_and_subject_binding_fail_closed(self) -> None:
        # Seed the recoverable account and deliver a bearer.
        mailbox = self._seed("binding.case@example.test")
        self.service.initiate(mailbox)
        # Capture the delivered bearer.
        token = self.mail.sent[0]["token"]
        # Require a bearer bound to another mailbox to be rejected.
        self._assert_generic(lambda: self.service.complete(token, "binding.other@example.test", "OtherPassw0rd!9"))
        # Consume the bearer legitimately.
        self.service.complete(token, mailbox, "FirstReplacement!9")
        # Require replay of the consumed bearer to be rejected.
        self._assert_generic(lambda: self.service.complete(token, mailbox, "SecondReplacement!9"))
        # Require an unknown bearer to be rejected the same way.
        self._assert_generic(lambda: self.service.complete("unknown-bearer-value", mailbox, "ThirdReplacement!9"))

    # Require a weak password to be rejected before the bearer is spent.
    def test_weak_password_does_not_burn_the_bearer(self) -> None:
        # Seed the recoverable account and deliver a bearer.
        mailbox = self._seed("weak.case@example.test")
        self.service.initiate(mailbox)
        # Capture the delivered bearer.
        token = self.mail.sent[0]["token"]
        # Require the weak password to be rejected generically.
        self._assert_generic(lambda: self.service.complete(token, mailbox, "short"))
        # Require the same bearer to still complete with a compliant password.
        self.assertEqual(self.service.complete(token, mailbox, "StrongReplacement!9")["status"], "reset")

    # Require credential-free accounts to be silently non-recoverable.
    def test_credential_free_account_is_not_recoverable(self) -> None:
        # Seed an account and then remove its local credential to model a social-only identity.
        mailbox = self._seed("social.only@example.test")
        # Read the seeded identity so its durable id can be targeted.
        user_id = auth.find_user_by_email(mailbox)["user_id"]
        # Strip the stored verifier atomically.
        def strip(state: dict) -> dict:
            # Clear only the targeted account's credential.
            for record in state.get("users", []):
                # Match the seeded identity.
                if record.get("user_id") == user_id:
                    # Remove the local verifier.
                    record["password_hash"] = ""
            # Return the mutated document.
            return state
        # Persist the credential-free fixture.
        update_json(auth.USERS_PATH, strip, auth.default_users)
        # Require the identical acknowledgement with no delivery attempted.
        self.assertEqual(self.service.initiate(mailbox), {"status": "accepted"})
        self.assertEqual(self.mail.sent, [])

    # Require a rejected delivery to stay silent and leave no usable bearer behind.
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
        service = password_reset.PasswordResetService(enabled=True, digest_key=TEST_DIGEST_KEY, mail_service=rejecting, audit_sink=lambda event, **fields: None)
        # Seed a recoverable account.
        mailbox = self._seed("rejected.delivery@example.test")
        # Require the identical acknowledgement even though delivery failed.
        self.assertEqual(service.initiate(mailbox), {"status": "accepted"})
        # Require the undelivered bearer to have been revoked rather than left valid.
        self._assert_generic(lambda: service.complete(rejecting.last_token, mailbox, "NeverDelivered!9"))
        # Require no active bearer to remain for the mailbox.
        self.assertEqual(password_reset.one_time_tokens.active_count(password_reset.PURPOSE, mailbox), 0)
