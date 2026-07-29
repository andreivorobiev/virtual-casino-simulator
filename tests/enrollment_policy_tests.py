"""Durable enrollment-policy resolution tests. (issue #333, slice 1)"""

# Import unittest so this focused suite runs listener-free alongside the other policy suites.
import unittest
# Import tempfile so each case owns an isolated storage root.
import tempfile
# Import itertools to sweep every environment-flag combination.
import itertools
# Import Path for the isolated provider data root.
from pathlib import Path

# Import the configuration module so the environment baseline can be varied per case.
from casino import config
# Import the module under test.
from casino.core import enrollment_policy
# Import storage so a temporary provider replaces the real data directory.
from casino.core import storage
# Import the validation envelope expected for a rejected mode.
from casino.errors import ValidationError


# Prove the policy resolves durably without changing deployed behaviour.
class EnrollmentPolicyTests(unittest.TestCase):
    # Capture the real flags so every case restores them.
    def setUp(self) -> None:
        # Remember the deployed flag values before any case mutates them.
        self._flags = (config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED)

    # Restore the flags and provider so cases cannot leak into each other.
    def tearDown(self) -> None:
        # Put the original flag values back.
        config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED = self._flags
        # Release any injected provider.
        storage.set_provider_for_tests(None)

    # Verify the resolved capabilities reproduce the environment-derived values exactly.
    def test_every_environment_combination_preserves_deployed_behaviour(self) -> None:
        # Sweep all eight combinations rather than sampling.
        for signup, invitations, enrollment in itertools.product((False, True), repeat=3):
            # Apply this combination to the configuration module.
            config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED = signup, invitations, enrollment
            # Isolate storage so no stored document interferes with the baseline.
            with tempfile.TemporaryDirectory() as tmp:
                # Inject a provider rooted in the temporary directory.
                storage.set_provider_for_tests(storage.JsonStorageProvider(Path(tmp) / "data"))
                # Resolve the capabilities the application will publish.
                resolved = enrollment_policy.capabilities()
                # Require public signup to match the flag the release published directly.
                self.assertEqual(signup, resolved["signup_enabled"], f"signup drift at {(signup, invitations, enrollment)}")
                # Require invitation enrollment to match the exact conjunction app.py used.
                self.assertEqual(invitations and enrollment, resolved["invitation_enrollment_enabled"], f"invitation drift at {(signup, invitations, enrollment)}")

    # Verify the restricted-preview default stays closed when nothing is enabled.
    def test_default_is_closed_with_no_public_method(self) -> None:
        # Disable every environment flag to represent the shipped default.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate storage so the baseline is the only input.
        with tempfile.TemporaryDirectory() as tmp:
            # Inject the temporary provider.
            storage.set_provider_for_tests(storage.JsonStorageProvider(Path(tmp) / "data"))
            # Resolve the capabilities.
            resolved = enrollment_policy.capabilities()
            # Require the closed mode with no public method and no invitation route.
            self.assertEqual((enrollment_policy.MODE_CLOSED, False, False), (resolved["mode"], resolved["signup_enabled"], resolved["invitation_enrollment_enabled"]))
            # Require every self-signup method to be off by default.
            self.assertEqual({"email": False, "google": False, "facebook": False}, resolved["methods"])

    # Verify a stored document governs the resolved policy.
    def test_stored_document_overrides_the_environment_baseline(self) -> None:
        # Leave the environment closed so any change must come from the document.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate storage for the durable write.
        with tempfile.TemporaryDirectory() as tmp:
            # Inject the temporary provider.
            provider = storage.JsonStorageProvider(Path(tmp) / "data")
            # Make it the active provider.
            storage.set_provider_for_tests(provider)
            # Ensure the storage root exists before writing a document.
            provider.ensure_ready()
            # Store a self-signup policy with email enabled through the concurrency-safe primitive.
            provider.update_document(enrollment_policy.POLICY_DOCUMENT_KEY, lambda current: {"schema_version": 1, "mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True, "google": False, "facebook": False}, "invitations_enabled": True}, enrollment_policy.environment_baseline)
            # Resolve the capabilities the application will now publish.
            resolved = enrollment_policy.capabilities()
            # Require the stored policy to govern despite every environment flag being off.
            self.assertEqual((enrollment_policy.MODE_SELF_SIGNUP, True, True), (resolved["mode"], resolved["signup_enabled"], resolved["invitation_enrollment_enabled"]))

    # Verify a truthy non-boolean cannot enable a method.
    def test_only_exact_booleans_enable_a_method(self) -> None:
        # Normalize a document whose flags are truthy strings rather than booleans.
        resolved = enrollment_policy.normalize({"mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": "yes", "google": 1, "facebook": True}})
        # Require the strings and integers to be rejected and only the real boolean accepted.
        self.assertEqual({"email": False, "google": False, "facebook": True}, resolved["methods"])

    # Verify an unrecognized mode fails closed instead of silently widening access.
    def test_unknown_mode_is_rejected(self) -> None:
        # Attempt to normalize a document naming a mode this release does not implement.
        with self.assertRaises(ValidationError):
            # Require the published validation envelope rather than a default.
            enrollment_policy.normalize({"mode": "everyone"})

    # Verify a malformed document falls back to the baseline rather than to open access.
    def test_malformed_document_falls_back_to_baseline(self) -> None:
        # Disable every flag so the baseline is closed.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Normalize a document that is not a mapping at all.
        resolved = enrollment_policy.normalize(["not", "a", "policy"])
        # Require the closed baseline rather than any partially applied state.
        self.assertEqual(enrollment_policy.MODE_CLOSED, resolved["mode"])


# Prove enforcement consults the policy and records every decision. (issue #333, slice 2)
class EnrollmentEnforcementTests(unittest.TestCase):
    # Capture the deployed flags and install an audit collector.
    def setUp(self) -> None:
        # Remember the real flag values.
        self._flags = (config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED)
        # Collect emitted audit events instead of writing to the application log.
        self.events = []
        # Remember the real log function so it can be restored.
        self._info = enrollment_policy.logger.info
        # Redirect the audit sink into the collector.
        enrollment_policy.logger.info = lambda event, **fields: self.events.append((event, fields))

    # Restore the flags, provider, and log function.
    def tearDown(self) -> None:
        # Put the original flags back.
        config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED = self._flags
        # Restore the real log function.
        enrollment_policy.logger.info = self._info
        # Release any injected provider.
        storage.set_provider_for_tests(None)

    # Install an isolated provider so no stored document leaks between cases.
    def _isolate(self, tmp):
        # Point the provider at the temporary directory.
        storage.set_provider_for_tests(storage.JsonStorageProvider(Path(tmp) / "data"))

    # Verify a closed mode denies every governed route and audits each refusal.
    def test_closed_mode_denies_and_audits_every_route(self) -> None:
        # Represent the shipped restricted-preview default.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate storage for this case.
        with tempfile.TemporaryDirectory() as tmp:
            # Install the temporary provider.
            self._isolate(tmp)
            # Evaluate each governed enrollment route.
            for route in (enrollment_policy.ROUTE_SIGNUP, enrollment_policy.ROUTE_INVITATION, enrollment_policy.ROUTE_OAUTH):
                # Require the closed mode to deny it.
                self.assertFalse(enrollment_policy.evaluate(route)["allowed"], f"{route} was allowed while closed")
            # Require one audit event per evaluation with no event lost.
            self.assertEqual(3, len(self.events))
            # Require every recorded decision to be a denial.
            self.assertTrue(all(fields["decision"] == "denied" for _, fields in self.events))

    # Verify the audit event carries no caller-supplied or credential material.
    def test_audit_events_carry_only_allowlisted_fields(self) -> None:
        # Isolate storage so the evaluation is deterministic.
        with tempfile.TemporaryDirectory() as tmp:
            # Install the temporary provider.
            self._isolate(tmp)
            # Evaluate one route to emit a single event.
            enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP)
            # Read the recorded fields.
            _, fields = self.events[0]
            # Require every emitted key to be explicitly allowlisted.
            self.assertTrue(set(fields).issubset(enrollment_policy.AUDIT_FIELDS), f"unexpected audit keys: {set(fields) - enrollment_policy.AUDIT_FIELDS}")

    # Verify an unreviewed reason cannot reach the log.
    def test_unrecognized_reason_is_collapsed(self) -> None:
        # Emit an event carrying a reason outside the reviewed vocabulary.
        enrollment_policy._audit("enrollment_decision", route="signup", reason="totally-new-reason")
        # Read the recorded fields.
        _, fields = self.events[0]
        # Require the unreviewed reason to be replaced rather than logged verbatim.
        self.assertEqual("unknown_route", fields["reason"])

    # Verify enabling one method does not enable another.
    def test_enabling_email_does_not_enable_providers(self) -> None:
        # Leave the environment closed so only the stored document matters.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate storage for the durable write.
        with tempfile.TemporaryDirectory() as tmp:
            # Build and install the provider.
            provider = storage.JsonStorageProvider(Path(tmp) / "data")
            # Make it active.
            storage.set_provider_for_tests(provider)
            # Create the storage root before writing.
            provider.ensure_ready()
            # Store a self-signup policy enabling only email.
            provider.update_document(enrollment_policy.POLICY_DOCUMENT_KEY, lambda current: {"schema_version": 1, "mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True, "google": False, "facebook": False}, "invitations_enabled": False}, enrollment_policy.environment_baseline)
            # Require email signup to be allowed.
            self.assertTrue(enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP)["allowed"])
            # Require a provider method to stay denied despite the open mode.
            self.assertFalse(enrollment_policy.evaluate(enrollment_policy.ROUTE_OAUTH, method="google")["allowed"])
            # Require invitation redemption to stay denied because the capability was not retained.
            self.assertFalse(enrollment_policy.evaluate(enrollment_policy.ROUTE_INVITATION)["allowed"])


# Allow direct execution for focused local runs.
if __name__ == "__main__":
    # Run the focused suite.
    unittest.main()
