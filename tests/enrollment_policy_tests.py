"""Durable enrollment-policy resolution tests. (AUTH-013)"""

# Import hashes so the additive v2 contract remains bound to its reviewed bytes.
import hashlib
# Import iteration helpers to sweep every environment-flag combination.
import itertools
# Import JSON decoding for the restricted-preview compatibility decision.
import json
# Import subprocess execution for an isolated dependency-light runner-import proof.
import subprocess
# Import the active interpreter path for the isolated import-only regression.
import sys
# Import temporary storage roots for provider-isolated evidence.
import tempfile
# Import unittest so this focused suite runs listener-free.
import unittest
# Import bounded patching so route seams can be proven without creating accounts or invitations.
from unittest import mock
# Import portable paths for isolated providers and repository contracts.
from pathlib import Path

# Import the configuration module so the environment baseline can be varied per case.
from casino import config
# Import the module under test.
from casino.core import enrollment_policy
# Import the existing account and invitation services only for public-route boundary patching.
from casino.core import auth, invitations
# Import storage so a temporary provider replaces the real data directory.
from casino.core import storage
# Import the validation envelope expected for a rejected mode.
from casino.errors import ForbiddenError, ValidationError

# Resolve the repository root for checked contract evidence.
ROOT = Path(__file__).resolve().parents[1]


# Build the application router only inside focused route tests that have the full dependency set.
def _build_router_for_route_test():
    # Defer the application import so aggregate shard verification can import the central runner without Pillow.
    from casino.app import build_router
    # Return a fresh listener-free route table for the requesting focused test.
    return build_router()


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

    # Verify a stored document governs the resolved read-only policy.
    def test_stored_document_overrides_the_environment_baseline(self) -> None:
        # Leave the environment closed so any change must come from the document fixture.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate storage for the durable fixture write.
        with tempfile.TemporaryDirectory() as tmp:
            # Inject the temporary provider.
            provider = storage.JsonStorageProvider(Path(tmp) / "data")
            # Make it the active provider.
            storage.set_provider_for_tests(provider)
            # Ensure the storage root exists before writing the fixture document.
            provider.ensure_ready()
            # Store a self-signup fixture through the provider's concurrency-safe primitive.
            provider.update_document(enrollment_policy.POLICY_DOCUMENT_KEY, lambda current: {"schema_version": 1, "mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True, "google": False, "facebook": False}, "invitations_enabled": True}, enrollment_policy.environment_baseline)
            # Resolve the capabilities the application will now publish.
            resolved = enrollment_policy.capabilities()
            # Require the stored policy to govern despite every environment flag being off.
            self.assertEqual((enrollment_policy.MODE_SELF_SIGNUP, True, True), (resolved["mode"], resolved["signup_enabled"], resolved["invitation_enrollment_enabled"]))

    # Verify a truthy non-boolean cannot enable a method.
    def test_only_exact_booleans_enable_a_method(self) -> None:
        # Normalize a document whose flags are truthy strings rather than booleans.
        resolved = enrollment_policy.normalize({"schema_version": enrollment_policy.SCHEMA_VERSION, "mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": "yes", "google": 1, "facebook": True}})
        # Require the strings and integers to be rejected and only the real boolean accepted.
        self.assertEqual({"email": False, "google": False, "facebook": True}, resolved["methods"])

    # Verify an unrecognized mode fails closed instead of silently widening access.
    def test_unknown_mode_is_rejected(self) -> None:
        # Attempt to normalize a document naming a mode this release does not implement.
        with self.assertRaises(ValidationError):
            # Require the published validation envelope rather than a default.
            enrollment_policy.normalize({"schema_version": enrollment_policy.SCHEMA_VERSION, "mode": "everyone"})

    # Verify a malformed document falls back to the baseline rather than to open access.
    def test_malformed_document_falls_back_to_baseline(self) -> None:
        # Disable every flag so the baseline is closed.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Normalize a document that is not a mapping at all.
        resolved = enrollment_policy.normalize(["not", "a", "policy"])
        # Require the closed baseline rather than any partially applied state.
        self.assertEqual(enrollment_policy.MODE_CLOSED, resolved["mode"])

    # Verify missing or non-v1 schema markers cannot widen the deployed baseline.
    def test_unowned_schema_versions_preserve_closed_default(self) -> None:
        # Disable every enrollment flag so any accepted override would be an observable widening.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Exercise missing, future, string, and boolean markers independently.
        for marker in (None, 2, "1", True):
            # Name the hostile marker when one exact domain case fails.
            with self.subTest(schema_version=marker):
                # Build the widening document while omitting the marker for the missing-field case.
                candidate = {"mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True}, "invitations_enabled": True}
                # Add every present hostile marker without normalizing its type.
                if marker is not None:
                    # Preserve the exact hostile JSON-shaped value.
                    candidate["schema_version"] = marker
                # Normalize through the public policy boundary.
                resolved = enrollment_policy.normalize(candidate)
                # Require the complete closed/default-off baseline for every unowned shape.
                self.assertEqual((enrollment_policy.MODE_CLOSED, False, False, {"email": False, "google": False, "facebook": False}), (resolved["mode"], resolved["methods"]["email"], resolved["invitations_enabled"], resolved["methods"]))

    # Prove aggregate verification can import the central runner without application or Pillow dependencies.
    def test_central_runner_import_is_dependency_light(self) -> None:
        # Import the central runner under Python's no-site mode so unavailable optional packages cannot be masked.
        probe = subprocess.run([sys.executable, "-S", "-c", "import sys; import tests.run_tests; assert 'casino.app' not in sys.modules; assert 'PIL' not in sys.modules"], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        # Require a clean import without leaking arbitrary subprocess output into the assertion message.
        self.assertEqual(probe.returncode, 0, "dependency-light central runner import failed")

    # Verify the additive response field and compatibility-v3 enforcement policy stay exact.
    def test_additive_v2_contract_and_enforcement_compatibility_are_bound(self) -> None:
        # Read the additive auth contract without importing a YAML dependency.
        contract_path = ROOT / "contracts" / "openapi" / "auth.v2.yaml"
        # Decode the reviewed contract text for exact schema anchors.
        contract = contract_path.read_text(encoding="utf-8")
        # Require the strict response object to declare the new mode before all retained fields.
        self.assertIn("required: [enrollment_mode, signup_enabled, guest_trials_enabled, invitation_enrollment_enabled, guest_conversion_enabled, passkeys_enabled, canonical_identity, shared_auth_origin]", contract)
        # Require the new property to use the complete closed vocabulary.
        self.assertIn("enrollment_mode:\n          type: string\n          enum: [closed, invite-only, self-signup]", contract)
        # Require both enforced routes, fixed operational logging, and the immutable-audit deferral.
        self.assertIn("enforced_routes: [/api/v2/auth/signup, /api/v2/auth/redeem-invitation]", contract)
        # Require absent, malformed-shape, and unowned-schema documents to preserve the deployed seed.
        self.assertIn("absent-malformed-or-unowned-document: deployed-environment-baseline", contract)
        # Require an owned-schema unknown mode to map to safe mutation-route denial.
        self.assertIn("schema-v1-unknown-mode: safe-route-denial", contract)
        # Require logging failure to deny before either governed mutation.
        self.assertIn("logging_failure: deny-before-mutation", contract)
        # Reject any claim that this operational logger supplies immutable actor/change audit.
        self.assertIn("immutable_actor_change_audit: deferred-to-pr-528-admin-write-transaction", contract)
        # Require the v2 contract to avoid publishing or changing any v1 route.
        self.assertNotIn("/api/v1", contract)
        # Parse the explicit restricted-preview compatibility decision.
        compatibility = json.loads((ROOT / "contracts" / "compatibility" / "restricted-preview-security.json").read_text(encoding="utf-8"))
        # Require artifact v3 for the bounded signup-and-redemption enforcement revision.
        self.assertEqual(compatibility["version"], 3)
        # Read the complete policy decision without accepting implicit defaults.
        policy = compatibility["enrollment_policy"]
        # Require the retained durable resolution and default-off boundaries.
        self.assertEqual({key: policy[key] for key in ("route", "modes", "environment_seed", "environment_fallback", "absent_malformed_or_unowned_document", "schema_v1_unknown_mode", "public_methods_default_enabled", "admin_write_available", "live_enablement_authorized", "api_v1_unchanged")}, {"route": "/api/v2/auth/enrollment-policy", "modes": ["closed", "invite-only", "self-signup"], "environment_seed": True, "environment_fallback": True, "absent_malformed_or_unowned_document": "deployed-environment-baseline", "schema_v1_unknown_mode": "safe-route-denial", "public_methods_default_enabled": False, "admin_write_available": False, "live_enablement_authorized": False, "api_v1_unchanged": True})
        # Require enforcement to stop at the two approved public mutations.
        self.assertEqual(policy["enforced_routes"], ["/api/v2/auth/signup", "/api/v2/auth/redeem-invitation"])
        # Require the exact bounded operational logger contract and explicit immutable-audit deferral.
        self.assertEqual(policy["decision_logging"], {"kind": "operational-jsonl", "event": "enrollment_decision", "routes": ["signup", "invitation", "unknown"], "modes": ["closed", "invite-only", "self-signup"], "methods": ["email", "google", "facebook", "unknown"], "decisions": ["allowed", "denied"], "reasons": ["allowed", "mode_closed", "self_signup_disabled", "method_disabled", "invitations_disabled", "unknown_route"], "fail_closed_before_mutation": True, "immutable_actor_change_audit": False, "immutable_audit_deferred_to": "#528 Admin-write transaction"})
        # Read the central exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Bind the reviewed additive contract bytes to their tracked SHA-256.
        self.assertEqual(digests["contracts/openapi/auth.v2.yaml"], hashlib.sha256(contract_path.read_bytes()).hexdigest())


# Prove public enrollment enforcement and operational logging remain bounded. (AUTH-013)
class EnrollmentEnforcementTests(unittest.TestCase):
    # Capture configuration and install a value-inspecting operational log sink.
    def setUp(self) -> None:
        # Remember the deployed flag values for exact restoration.
        self._flags = (config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED)
        # Collect only records deliberately emitted by the policy under test.
        self.events = []
        # Patch the application logger without writing task-owned JSONL residue.
        self.log_patch = mock.patch.object(enrollment_policy.logger, "info", side_effect=lambda event, **fields: self.events.append((event, dict(fields))))
        # Activate the bounded in-memory operational sink.
        self.log_patch.start()

    # Restore every process-global seam after each listener-free case.
    def tearDown(self) -> None:
        # Restore the real JSONL logger.
        self.log_patch.stop()
        # Restore the exact deployed flags.
        config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED = self._flags
        # Release the isolated provider seam.
        storage.set_provider_for_tests(None)

    # Install one isolated durable policy document and return its provider.
    def _policy(self, root: str, *, mode: str, email: bool, invitations_enabled: bool):
        # Construct a provider below the caller-owned temporary root.
        provider = storage.JsonStorageProvider(Path(root) / "data")
        # Make the isolated provider active for policy and route resolution.
        storage.set_provider_for_tests(provider)
        # Create the isolated storage root before writing the policy fixture.
        provider.ensure_ready()
        # Persist one exact owned v1 policy document through the provider lock.
        provider.update_document(enrollment_policy.POLICY_DOCUMENT_KEY, lambda current: {"schema_version": enrollment_policy.SCHEMA_VERSION, "mode": mode, "methods": {"email": email, "google": False, "facebook": False}, "invitations_enabled": invitations_enabled}, enrollment_policy.environment_baseline)
        # Return the provider for optional exact-state assertions.
        return provider

    # Prove every direct hostile audit value is collapsed before it reaches JSONL.
    def test_audit_collapses_arbitrary_oversized_multiline_and_secret_like_values(self) -> None:
        # Build one hostile marker that must never appear in an emitted event or field.
        hostile = ("token=synthetic-secret\n" * 1024)
        # Invoke the private sink boundary directly with hostile values and an unreviewed field.
        enrollment_policy._audit(hostile, route=hostile, mode=hostile, method=hostile, decision=hostile, reason=hostile, bearer=hostile)
        # Require exactly one fixed event.
        self.assertEqual(len(self.events), 1)
        # Read the emitted event and fields without retaining the hostile marker elsewhere.
        event, fields = self.events[0]
        # Require the sole reviewed event name.
        self.assertEqual(event, enrollment_policy.AUDIT_EVENT)
        # Require the exact fixed collapsed record with no extra caller field.
        self.assertEqual(fields, {"route": "unknown", "mode": enrollment_policy.MODE_CLOSED, "method": "unknown", "decision": "denied", "reason": "unknown_route"})
        # Prove no hostile fragment or newline reached the serialized operational record.
        self.assertNotIn("synthetic-secret", json.dumps([event, fields], sort_keys=True))
        # Require every key and value to come from the reviewed low-cardinality contract.
        self.assertTrue(set(fields).issubset(enrollment_policy.AUDIT_FIELDS))

    # Prove an operational logger failure is fixed, value-free, and blocks the decision.
    def test_log_failure_is_fixed_and_fail_closed(self) -> None:
        # Replace the collector with a hostile sink failure carrying secret-like detail.
        with mock.patch.object(enrollment_policy.logger, "info", side_effect=OSError("secret-path\ncredential")):
            # Evaluate the default closed route through the public policy boundary.
            with self.assertRaises(enrollment_policy.EnrollmentAuditError) as raised:
                # Require the logging boundary to fail before returning an enrollment decision.
                enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP)
        # Require one fixed value-free diagnostic.
        self.assertEqual(str(raised.exception), "Enrollment decision logging is unavailable")
        # Prove the hostile sink text did not escape.
        self.assertNotIn("secret", str(raised.exception))

    # Prove invite-only signup denial is not falsely recorded as a closed-mode decision.
    def test_invite_only_signup_uses_truthful_fixed_reason(self) -> None:
        # Leave the environment closed so the exact stored invite-only document owns the result.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate the durable policy and its control files.
        with tempfile.TemporaryDirectory() as tmp:
            # Enable invitations without enabling public email signup.
            self._policy(tmp, mode=enrollment_policy.MODE_INVITE_ONLY, email=False, invitations_enabled=True)
            # Evaluate the public signup gate directly.
            decision = enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP)
        # Require the fixed invite-only reason and reviewed mode.
        self.assertEqual(decision, {"allowed": False, "reason": "self_signup_disabled", "mode": enrollment_policy.MODE_INVITE_ONLY})
        # Require the operational record to tell the same truth.
        self.assertEqual(self.events[-1], (enrollment_policy.AUDIT_EVENT, {"route": enrollment_policy.ROUTE_SIGNUP, "mode": enrollment_policy.MODE_INVITE_ONLY, "decision": "denied", "reason": "self_signup_disabled", "method": "email"}))

    # Prove public signup enforces the resolved policy while preserving its route result.
    def test_signup_route_enforces_policy_before_account_mutation(self) -> None:
        # Leave the process flag closed so only the durable document can authorize the allow case.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Exercise denial and allowance under isolated policy documents.
        with tempfile.TemporaryDirectory() as tmp:
            # Install the exact restricted-preview baseline.
            self._policy(tmp, mode=enrollment_policy.MODE_CLOSED, email=False, invitations_enabled=False)
            # Build a fresh listener-free route table.
            router = _build_router_for_route_test()
            # Prevent any account mutation if the policy denial is accidentally bypassed.
            with mock.patch.object(auth, "create_user") as create_user:
                # Dispatch one complete public signup request.
                with self.assertRaises(ForbiddenError) as denied:
                    # Exercise the existing anonymous route and context shape.
                    router.dispatch("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "SyntheticSignupPassw0rd!23", "display_name": "Held", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
                # Require the existing public denial message.
                self.assertEqual(denied.exception.message, "Full account signup is disabled")
                # Prove no account mutation started.
                create_user.assert_not_called()
            # Replace the same durable document with explicit email self-signup permission.
            self._policy(tmp, mode=enrollment_policy.MODE_SELF_SIGNUP, email=True, invitations_enabled=False)
            # Define one fixed synthetic user result for the existing route sequence.
            synthetic_user = {"user_id": "synthetic-user", "email": "allowed@example.invalid"}
            # Define one fixed synthetic login result for response compatibility.
            synthetic_login = {"session": {"session_id": "synthetic-session"}, "user": synthetic_user}
            # Patch only the existing mutation seams after policy allowance.
            with mock.patch.object(auth, "create_user", return_value=synthetic_user) as create_user, mock.patch.object(auth, "accept_terms") as accept_terms, mock.patch.object(auth, "login", return_value=synthetic_login) as login, mock.patch.object(auth, "session_cookie_headers", return_value=[]):
                # Dispatch the same public signup contract under an allowed durable policy.
                result = router.dispatch("POST", "/api/v2/auth/signup", {"email": "allowed@example.invalid", "password": "SyntheticSignupPassw0rd!23", "display_name": "Allowed", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
            # Require the route to preserve the existing authenticated result.
            self.assertEqual(result, synthetic_login)
            # Require every existing mutation seam to execute exactly once after logging.
            self.assertEqual((create_user.call_count, accept_terms.call_count, login.call_count), (1, 1, 1))

    # Prove invitation redemption enforces policy while retaining one generic denial envelope.
    def test_invitation_route_enforces_policy_and_preserves_generic_denial(self) -> None:
        # Leave every environment source closed so stored policy is authoritative.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Exercise both route decisions in one isolated provider.
        with tempfile.TemporaryDirectory() as tmp:
            # Install a closed policy that must suspend redemption.
            self._policy(tmp, mode=enrollment_policy.MODE_CLOSED, email=False, invitations_enabled=False)
            # Build a fresh listener-free route table.
            router = _build_router_for_route_test()
            # Prevent any bearer inspection or mutation if policy denial is bypassed.
            with mock.patch.object(invitations, "redeem") as redeem:
                # Dispatch a complete but synthetic redemption request.
                with self.assertRaises(ValidationError) as denied:
                    # Use only reserved test material and the exact public request shape.
                    router.dispatch("POST", "/api/v2/auth/redeem-invitation", {"token": "synthetic-token", "email": "invitee@example.invalid", "password": "Synthetic-Invite-2026!", "display_name": "Invitee", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True, "idempotency_key": "synthetic-redeem-key"})
                # Require the existing identifier-free message and reason.
                self.assertEqual((denied.exception.message, denied.exception.details), ("invitation could not be redeemed", invitations.GENERIC_REDEMPTION_DETAILS))
                # Prove the invitation service never observed the bearer.
                redeem.assert_not_called()
            # Install an invite-only policy with the exact invitation capability enabled.
            self._policy(tmp, mode=enrollment_policy.MODE_INVITE_ONLY, email=False, invitations_enabled=True)
            # Define one identifier-free synthetic success receipt.
            receipt = {"redeemed": True}
            # Patch only the existing service seam after policy allowance.
            with mock.patch.object(invitations, "redeem", return_value=receipt) as redeem:
                # Dispatch the identical request under the allowed policy.
                result = router.dispatch("POST", "/api/v2/auth/redeem-invitation", {"token": "synthetic-token", "email": "invitee@example.invalid", "password": "Synthetic-Invite-2026!", "display_name": "Invitee", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True, "idempotency_key": "synthetic-redeem-key"})
            # Require unchanged route success projection.
            self.assertEqual(result, receipt)
            # Require the existing service to receive exactly one allowed call.
            self.assertEqual(redeem.call_count, 1)

    # Prove malformed stored modes preserve each public route's existing safe envelope.
    def test_unknown_stored_mode_cannot_leak_or_start_route_mutation(self) -> None:
        # Leave every environment source closed so the malformed document cannot widen by fallback.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Isolate the malformed durable document.
        with tempfile.TemporaryDirectory() as tmp:
            # Construct and activate one isolated provider.
            provider = storage.JsonStorageProvider(Path(tmp) / "data")
            # Make the provider authoritative for both route evaluations.
            storage.set_provider_for_tests(provider)
            # Create its private roots before the hostile fixture write.
            provider.ensure_ready()
            # Persist an owned schema marker with an unreviewed mode.
            provider.update_document(enrollment_policy.POLICY_DOCUMENT_KEY, lambda current: {"schema_version": enrollment_policy.SCHEMA_VERSION, "mode": "synthetic-unreviewed-mode", "methods": {"email": True}, "invitations_enabled": True}, enrollment_policy.environment_baseline)
            # Build a fresh listener-free route table.
            router = _build_router_for_route_test()
            # Guard both downstream mutation seams.
            with mock.patch.object(auth, "create_user") as create_user, mock.patch.object(invitations, "redeem") as redeem:
                # Require signup to retain its existing disabled envelope.
                with self.assertRaises(ForbiddenError) as signup_error:
                    # Dispatch a complete request so policy resolution is the only rejection.
                    router.dispatch("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "SyntheticSignupPassw0rd!23", "display_name": "Held", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
                # Require invitation redemption to retain its generic envelope.
                with self.assertRaises(ValidationError) as invitation_error:
                    # Dispatch a complete synthetic redemption request.
                    router.dispatch("POST", "/api/v2/auth/redeem-invitation", {"token": "synthetic-token", "email": "invitee@example.invalid", "password": "Synthetic-Invite-2026!", "display_name": "Invitee", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True, "idempotency_key": "synthetic-redeem-key"})
        # Require the exact pre-existing public messages, not the stored mode validation detail.
        self.assertEqual(signup_error.exception.message, "Full account signup is disabled")
        # Require the exact generic invitation message and reason.
        self.assertEqual((invitation_error.exception.message, invitation_error.exception.details), ("invitation could not be redeemed", invitations.GENERIC_REDEMPTION_DETAILS))
        # Prove neither service mutation began.
        self.assertEqual((create_user.call_count, redeem.call_count), (0, 0))

    # Prove a logging failure preserves each route's public denial and prevents mutation.
    def test_route_log_failure_preserves_public_envelopes_and_no_mutation(self) -> None:
        # Build a fresh listener-free route table.
        router = _build_router_for_route_test()
        # Replace the operational sink with hostile failure detail.
        with mock.patch.object(enrollment_policy.logger, "info", side_effect=OSError("secret-log-path")), mock.patch.object(auth, "create_user") as create_user, mock.patch.object(invitations, "redeem") as redeem:
            # Require signup to retain its existing disabled envelope.
            with self.assertRaises(ForbiddenError) as signup_error:
                # Attempt public signup while the decision cannot be recorded.
                router.dispatch("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "SyntheticSignupPassw0rd!23", "display_name": "Held", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
            # Require invitation redemption to retain its generic envelope.
            with self.assertRaises(ValidationError) as invitation_error:
                # Attempt public redemption while the decision cannot be recorded.
                router.dispatch("POST", "/api/v2/auth/redeem-invitation", {"token": "synthetic-token"})
        # Require both existing public messages and no logger detail.
        self.assertEqual(signup_error.exception.message, "Full account signup is disabled")
        # Require the exact generic invitation error.
        self.assertEqual((invitation_error.exception.message, invitation_error.exception.details), ("invitation could not be redeemed", invitations.GENERIC_REDEMPTION_DETAILS))
        # Prove neither governed mutation seam started.
        self.assertEqual((create_user.call_count, redeem.call_count), (0, 0))


# Allow direct execution for focused local runs.
if __name__ == "__main__":
    # Run the focused suite.
    unittest.main()
