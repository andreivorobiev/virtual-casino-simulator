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


# Prove the owner-only write path validates, audits, and returns a reversible previous state. (slice 3)
class EnrollmentAdminWriteTests(unittest.TestCase):
    # Isolate storage, flags, and the audit sink for every case.
    def setUp(self) -> None:
        # Remember the deployed flags.
        self._flags = (config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED)
        # Start from the shipped closed default so any opening must come from the write path.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Own a temporary storage root for the durable document.
        self._tmp = tempfile.TemporaryDirectory()
        # Build the isolated provider.
        provider = storage.JsonStorageProvider(Path(self._tmp.name) / "data")
        # Make it active.
        storage.set_provider_for_tests(provider)
        # Create the storage root before any document write.
        provider.ensure_ready()
        # Collect audit events rather than writing to the application log.
        self.events = []
        # Remember the real log function.
        self._info = enrollment_policy.logger.info
        # Redirect the sink.
        enrollment_policy.logger.info = lambda event, **fields: self.events.append((event, fields))

    # Restore every global this case replaced.
    def tearDown(self) -> None:
        # Restore the flags.
        config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED = self._flags
        # Restore the log function.
        enrollment_policy.logger.info = self._info
        # Release the provider.
        storage.set_provider_for_tests(None)
        # Remove the temporary root.
        self._tmp.cleanup()

    # Verify a change persists, audits, and reports what actually moved.
    def test_change_persists_audits_and_reports_impact(self) -> None:
        # Open public email signup from the closed default.
        result = enrollment_policy.update({"mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True}}, actor_id="owner-1", reason="open private beta")
        # Require the durable read to reflect the change.
        self.assertTrue(enrollment_policy.capabilities()["signup_enabled"])
        # Require the previous state to be returned for rollback.
        self.assertEqual(enrollment_policy.MODE_CLOSED, result["previous"]["mode"])
        # Require the impact summary to name the capabilities that moved.
        self.assertIn("signup_enabled", result["impact"]["changed"])
        # Require exactly one audit event naming the actor.
        self.assertEqual(1, len(self.events))
        # Require the actor and previous mode to be recorded.
        self.assertEqual(("owner-1", enrollment_policy.MODE_CLOSED), (self.events[0][1]["actor_id"], self.events[0][1]["previous_mode"]))

    # Verify the returned previous state restores the original policy exactly.
    def test_previous_state_round_trips_as_a_rollback(self) -> None:
        # Capture the shipped default.
        original = enrollment_policy.current()
        # Apply a change.
        result = enrollment_policy.update({"mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True}}, actor_id="owner-1", reason="open")
        # Roll back using exactly the previous document the write path returned.
        enrollment_policy.update({"mode": result["previous"]["mode"], "methods": result["previous"]["methods"], "invitations_enabled": result["previous"]["invitations_enabled"]}, actor_id="owner-1", reason="rollback")
        # Require the resolved policy to match the original in every governed field.
        restored = enrollment_policy.current()
        # Compare the fields the policy actually governs.
        self.assertEqual((original["mode"], original["methods"], original["invitations_enabled"]), (restored["mode"], restored["methods"], restored["invitations_enabled"]))

    # Verify a change without a reason is refused.
    def test_reason_is_required(self) -> None:
        # Attempt a change with a blank reason.
        with self.assertRaises(ValidationError):
            # Require the validation envelope rather than an unexplained change.
            enrollment_policy.update({"mode": enrollment_policy.MODE_CLOSED}, actor_id="owner-1", reason="   ")

    # Verify an unsupported field cannot be smuggled into the policy document.
    def test_unsupported_fields_are_refused(self) -> None:
        # Attempt to set a field outside the governed shape.
        with self.assertRaises(ValidationError):
            # Require the change to fail closed.
            enrollment_policy.update({"mode": enrollment_policy.MODE_CLOSED, "roles": ["admin"]}, actor_id="owner-1", reason="probe")

    # Verify an unknown method name is refused rather than silently dropped.
    def test_unknown_method_is_refused(self) -> None:
        # Attempt to enable a method this release does not implement.
        with self.assertRaises(ValidationError):
            # Require the change to name the legal methods and fail closed.
            enrollment_policy.update({"methods": {"passkey": True}}, actor_id="owner-1", reason="probe")

    # Verify an invalid mode leaves the stored policy untouched.
    def test_failed_change_leaves_policy_unchanged(self) -> None:
        # Capture the state before the attempt.
        before = enrollment_policy.current()
        # Attempt a change naming an unknown mode.
        with self.assertRaises(ValidationError):
            # The mutator must raise before anything is persisted.
            enrollment_policy.update({"mode": "everyone"}, actor_id="owner-1", reason="probe")
        # Require the stored policy to be exactly what it was.
        self.assertEqual(before, enrollment_policy.current())


# Allow direct execution for focused local runs.
if __name__ == "__main__":
    # Run the focused suite.
    unittest.main()
