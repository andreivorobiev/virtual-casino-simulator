"""Durable enrollment-policy resolution tests. (AUTH-013)"""

# Import hashes so the additive v2 contract remains bound to its reviewed bytes.
import hashlib
# Import deep copying for coherently rehashed hostile audit fixtures.
import copy
# Import bounded parallel execution for provider-transaction contention proof.
from concurrent.futures import ThreadPoolExecutor
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
# Import the standard envelopes expected for stale, forbidden, and malformed requests.
from casino.errors import ConflictError, ForbiddenError, ValidationError

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

    # Verify additive public and owner Admin contracts plus compatibility-v4 stay exact.
    def test_additive_v2_contract_and_enforcement_compatibility_are_bound(self) -> None:
        # Read the additive auth contract without importing a YAML dependency.
        contract_path = ROOT / "contracts" / "openapi" / "auth.v2.yaml"
        # Resolve the additive owner Admin contract beside the existing user-management surface.
        admin_contract_path = ROOT / "contracts" / "openapi" / "admin-users.v2.yaml"
        # Decode the reviewed contract text for exact schema anchors.
        contract = contract_path.read_text(encoding="utf-8")
        # Decode the owner Admin contract for exact route and transaction anchors.
        admin_contract = admin_contract_path.read_text(encoding="utf-8")
        # Require the strict response object to declare the new mode before all retained fields.
        self.assertIn("required: [enrollment_mode, signup_enabled, guest_trials_enabled, invitation_enrollment_enabled, guest_conversion_enabled, passkeys_enabled, canonical_identity, shared_auth_origin]", contract)
        # Require the new property to use the complete closed vocabulary.
        self.assertIn("enrollment_mode:\n          type: string\n          enum: [closed, invite-only, self-signup]", contract)
        # Require both enforced public routes and fixed operational logging.
        self.assertIn("enforced_routes: [/api/v2/auth/signup, /api/v2/auth/redeem-invitation]", contract)
        # Require only missing, non-mapping, or unowned-schema documents to preserve the seed.
        self.assertIn("absent-nonmapping-or-unowned-document: deployed-environment-baseline", contract)
        # Require malformed and unknown-mode schema-owned state to preserve bytes for recovery.
        self.assertIn("schema-v1-malformed-document: fixed-operator-recovery-without-read-side-write", contract)
        # Require owned-schema unknown modes to use the same strict recovery boundary.
        self.assertIn("schema-v1-unknown-mode: fixed-operator-recovery-without-read-side-write", contract)
        # Require logging failure to deny before either governed mutation.
        self.assertIn("logging_failure: deny-before-mutation", contract)
        # Bind the separate owner Admin routes and provider-backed actor/change transaction.
        self.assertIn("owner_admin_routes: [/api/v2/admin/enrollment-policy, /api/v2/admin/enrollment-policy/preview]", contract)
        # Require least-privilege platform-owner authority.
        self.assertIn("owner_role: platform_owner", contract)
        # Require previews to bind policy plus audit position rather than policy bytes alone.
        self.assertIn("owner_preview_binding: canonical-policy-plus-audit-count-and-head-sha256", contract)
        # Require a stale preview to stop without policy, audit, or operational-log mutation.
        self.assertIn("owner_stale_preview: fixed-conflict-without-write-or-log", contract)
        # Require immutable actor/change evidence to be provider-backed and hash-linked.
        self.assertIn("immutable_actor_change_audit: provider-backed-hash-linked-policy-transaction", contract)
        # Preserve the no-live-enablement release boundary.
        self.assertIn("live_enablement_authorized: false", contract)
        # Require the v2 contract to avoid publishing or changing any v1 route.
        self.assertNotIn("/api/v1", contract)
        # Require the exact owner GET, preview, and apply route paths.
        self.assertIn("  /admin/enrollment-policy:\n", admin_contract)
        # Require the separate preview route.
        self.assertIn("  /admin/enrollment-policy/preview:\n", admin_contract)
        # Require exact platform-owner language instead of ordinary Admin authority.
        self.assertIn("current active bootstrap-managed platform owner", admin_contract)
        # Require exact boolean confirmation, bounded reason, and ABA-safe revision in apply.
        self.assertIn("enum: [true]", admin_contract)
        # Require the published reason ceiling.
        self.assertIn("maxLength: 256", admin_contract)
        # Require apply to bind the exact lowercase SHA-256 preview revision.
        self.assertIn("required: [revision, confirm, reason]", admin_contract)
        # Require the owner, preview, and apply envelopes to publish their reviewed revisions.
        self.assertIn("required: [policy, previous, previous_revision, revision, impact, audit]", admin_contract)
        # Require one standard stale-preview conflict without alternate-state disclosure.
        self.assertIn("'409':\n          description: The supplied preview revision is stale", admin_contract)
        # Require exact prior and current policy snapshots in immutable audit.
        self.assertIn("required: [audit_version, audit_id, actor_id, reason, at, previous, current, impact, previous_digest, digest]", admin_contract)
        # Parse the explicit restricted-preview compatibility decision.
        compatibility = json.loads((ROOT / "contracts" / "compatibility" / "restricted-preview-security.json").read_text(encoding="utf-8"))
        # Require artifact v4 for the owner Admin transaction revision.
        self.assertEqual(compatibility["version"], 4)
        # Read the complete policy decision without accepting implicit defaults.
        policy = compatibility["enrollment_policy"]
        # Require the retained fallback plus separate schema-owned recovery boundaries.
        self.assertEqual({key: policy[key] for key in ("route", "modes", "environment_seed", "environment_fallback", "absent_nonmapping_or_unowned_document", "schema_v1_malformed_document", "schema_v1_unknown_mode", "public_methods_default_enabled", "admin_write_available", "live_enablement_authorized", "api_v1_unchanged")}, {"route": "/api/v2/auth/enrollment-policy", "modes": ["closed", "invite-only", "self-signup"], "environment_seed": True, "environment_fallback": True, "absent_nonmapping_or_unowned_document": "deployed-environment-baseline", "schema_v1_malformed_document": "fixed-operator-recovery-without-read-side-write", "schema_v1_unknown_mode": "fixed-operator-recovery-without-read-side-write", "public_methods_default_enabled": False, "admin_write_available": True, "live_enablement_authorized": False, "api_v1_unchanged": True})
        # Require enforcement to stop at the two approved public mutations.
        self.assertEqual(policy["enforced_routes"], ["/api/v2/auth/signup", "/api/v2/auth/redeem-invitation"])
        # Require the exact bounded operational logger contract and separate immutable owner audit.
        self.assertEqual(policy["decision_logging"], {"kind": "operational-jsonl", "event": "enrollment_decision", "routes": ["signup", "invitation", "unknown"], "modes": ["closed", "invite-only", "self-signup"], "methods": ["email", "google", "facebook", "unknown"], "decisions": ["allowed", "denied"], "reasons": ["allowed", "mode_closed", "self_signup_disabled", "method_disabled", "invitations_disabled", "unknown_route"], "fail_closed_before_mutation": True, "immutable_actor_change_audit": False, "separate_owner_change_audit": "provider-backed-hash-linked-policy-transaction"})
        # Require the complete least-privilege owner transaction compatibility decision.
        self.assertEqual(policy["admin_write"], {"routes": ["/api/v2/admin/enrollment-policy", "/api/v2/admin/enrollment-policy/preview"], "authority": "current-active-platform-owner", "ordinary_admin_write": False, "confirmation": "exact-true", "reason": "required-printable-1-through-256", "preview_apply_computation": "shared-resolved-capability-function", "preview_revision": "sha256-canonical-policy-plus-verified-audit-count-and-head", "apply_revision_required": True, "stale_preview": "fixed-conflict-no-state-disclosure-no-write-no-operational-log", "strict_document_read": "missing-default-owned-schema-malformed-operator-recovery-no-read-side-write", "rejected_mutation": "no-policy-audit-or-operational-log-write", "rollback": "exact-prior-policy-plus-current-revision", "audit": {"provider_backed": True, "same_document_transaction": True, "append_only": True, "hash_linked": True, "actor": "canonical-opaque-platform-owner-id", "prior_and_current_policy": True}})
        # Read the central exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Bind the reviewed additive contract bytes to their tracked SHA-256.
        self.assertEqual(digests["contracts/openapi/auth.v2.yaml"], hashlib.sha256(contract_path.read_bytes()).hexdigest())
        # Bind the owner Admin contract bytes to the same frozen digest inventory.
        self.assertEqual(digests["contracts/openapi/admin-users.v2.yaml"], hashlib.sha256(admin_contract_path.read_bytes()).hexdigest())


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

    # Prove a malformed owned-schema mode requires recovery before either route mutation.
    def test_unknown_stored_mode_requires_recovery_without_route_mutation(self) -> None:
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
            # Capture the exact hostile policy bytes before strict reads.
            original = provider.document_path(enrollment_policy.POLICY_DOCUMENT_KEY).read_bytes()
            # Guard both downstream mutation seams.
            with mock.patch.object(auth, "create_user") as create_user, mock.patch.object(invitations, "redeem") as redeem:
                # Require signup to stop at the fixed provider recovery boundary.
                with self.assertRaisesRegex(RuntimeError, "^Stored document requires operator recovery$"):
                    # Dispatch a complete request so policy resolution is the only rejection.
                    router.dispatch("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "SyntheticSignupPassw0rd!23", "display_name": "Held", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
                # Require invitation redemption to stop at the same fixed recovery boundary.
                with self.assertRaisesRegex(RuntimeError, "^Stored document requires operator recovery$"):
                    # Dispatch a complete synthetic redemption request.
                    router.dispatch("POST", "/api/v2/auth/redeem-invitation", {"token": "synthetic-token", "email": "invitee@example.invalid", "password": "Synthetic-Invite-2026!", "display_name": "Invitee", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True, "idempotency_key": "synthetic-redeem-key"})
            # Prove neither service mutation began.
            self.assertEqual((create_user.call_count, redeem.call_count), (0, 0))
            # Require exact hostile bytes and no normalized policy write.
            self.assertEqual(provider.document_path(enrollment_policy.POLICY_DOCUMENT_KEY).read_bytes(), original)

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


# Prove owner-only policy control commits policy and immutable audit in one provider transaction. (AUTH-014)
class EnrollmentAdminTransactionTests(unittest.TestCase):
    # Install a closed environment and isolated JSON provider for every transaction case.
    def setUp(self) -> None:
        # Remember the deployed flags for exact restoration.
        self._flags = (config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED)
        # Start from the shipped restricted-preview baseline.
        config.SIGNUP_ENABLED = config.INVITATIONS_ENABLED = config.ENROLLMENT_ENABLED = False
        # Own one temporary root for policy and provider-control artifacts.
        self._tmp = tempfile.TemporaryDirectory()
        # Construct one provider on the caller-owned data root.
        self.provider = storage.JsonStorageProvider(Path(self._tmp.name) / "data")
        # Make the isolated provider authoritative for policy and route reads.
        storage.set_provider_for_tests(self.provider)
        # Initialize storage through the provider's guarded readiness path.
        self.provider.ensure_ready()
        # Define one canonical active platform owner returned by current-state lookup.
        self.owner = {"user_id": "user_0123456789abcdef", "status": "active", "role": "admin", "roles": ["admin", auth.PLATFORM_OWNER_ROLE]}
        # Define one active ordinary Admin without owner authority.
        self.ordinary_admin = {"user_id": "user_fedcba9876543210", "status": "active", "role": "admin", "roles": ["admin"]}

    # Restore globals and remove every isolated provider artifact.
    def tearDown(self) -> None:
        # Release the provider seam before its root disappears.
        storage.set_provider_for_tests(None)
        # Restore every deployed enrollment flag.
        config.SIGNUP_ENABLED, config.INVITATIONS_ENABLED, config.ENROLLMENT_ENABLED = self._flags
        # Remove the complete caller-owned temporary root.
        self._tmp.cleanup()

    # Resolve the exact durable policy-document path without creating it.
    def _policy_path(self) -> Path:
        # Use the provider's canonical document mapping for byte-stability assertions.
        return self.provider.document_path(enrollment_policy.POLICY_DOCUMENT_KEY)

    # Snapshot every provider-owned file for exact read-side no-mutation assertions.
    def _provider_inventory(self) -> dict[str, bytes]:
        # Resolve the complete caller-owned temporary root.
        root = Path(self._tmp.name)
        # Return relative paths and exact bytes for every provider/control file.
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    # Apply one representative opening proposal used by success and rollback cases.
    @staticmethod
    def _opening_changes() -> dict:
        # Return a sparse proposal that opens email signup and invitation redemption only.
        return {"mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True}, "invitations_enabled": True}

    # Apply one proposal against its exact current preview revision.
    def _apply_current(self, changes: dict, reason: str) -> dict:
        # Compute the mutation-free proposal and its ABA-safe current revision.
        preview = enrollment_policy.propose(changes)
        # Commit only if the provider transaction still observes that exact revision.
        return enrollment_policy.update(changes, actor_id=self.owner["user_id"], reason=reason, expected_revision=preview["revision"])

    # Prove preview and apply share one computation and the returned prior policy rolls back exactly.
    def test_preview_apply_and_exact_previous_rollback_share_one_computation(self) -> None:
        # Compute the exact mutation-free owner preview.
        preview = enrollment_policy.propose(self._opening_changes())
        # Require preview to leave the policy document absent.
        self.assertFalse(self._policy_path().exists())
        # Commit the same proposal with one bounded opaque owner and reason.
        applied = enrollment_policy.update(self._opening_changes(), actor_id=self.owner["user_id"], reason="Open reviewed private enrollment", expected_revision=preview["revision"])
        # Require apply to commit exactly the previewed policy and capability impact.
        self.assertEqual((applied["previous"], applied["current"], applied["impact"]), (preview["previous"], preview["policy"], preview["impact"]))
        # Require the public resolver to observe the committed policy.
        self.assertEqual(enrollment_policy.current(), applied["current"])
        # Read and verify the complete provider-backed audit.
        audit_rows = enrollment_policy.change_audit()
        # Require one exact actor/change entry with the transaction receipt identity.
        self.assertEqual(audit_rows, [applied["audit"]])
        # Require the first row to begin at the fixed genesis digest.
        self.assertEqual(applied["audit"]["previous_digest"], enrollment_policy.CHANGE_AUDIT_GENESIS_DIGEST)
        # Require apply to acknowledge the exact preview revision it consumed.
        self.assertEqual(applied["previous_revision"], preview["revision"])
        # Convert the exact prior response directly into an application rollback.
        rollback = enrollment_policy.update(enrollment_policy.changes_for_policy(applied["previous"]), actor_id=self.owner["user_id"], reason="Restore exact prior policy", expected_revision=applied["revision"])
        # Require exact governed-state restoration rather than an environment-derived approximation.
        self.assertEqual(rollback["current"], applied["previous"])
        # Require both immutable entries to remain in order.
        restored_audit = enrollment_policy.change_audit()
        # Require the rollback row to link to the opening row without truncation.
        self.assertEqual((len(restored_audit), restored_audit[1]["previous_digest"]), (2, restored_audit[0]["digest"]))

    # Prove concurrent same-revision callers serialize to one winner and one stale conflict.
    def test_concurrent_same_revision_allows_one_commit_and_rejects_stale_contender(self) -> None:
        # Define one sparse mode/method mutation.
        email_change = {"mode": enrollment_policy.MODE_SELF_SIGNUP, "methods": {"email": True}}
        # Define an independent invitation mutation.
        invitation_change = {"invitations_enabled": True}
        # Capture the one exact revision both owners concurrently present.
        shared_revision = enrollment_policy.propose(email_change)["revision"]
        # Run both updates concurrently against the same provider transaction boundary.
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit the email policy change.
            email_future = executor.submit(enrollment_policy.update, email_change, actor_id=self.owner["user_id"], reason="Enable reviewed email capability", expected_revision=shared_revision)
            # Submit the invitation policy change.
            invitation_future = executor.submit(enrollment_policy.update, invitation_change, actor_id=self.owner["user_id"], reason="Enable reviewed invitation capability", expected_revision=shared_revision)
            # Collect one success and one fixed stale conflict without hiding other failures.
            results = []
            # Count exact conflict-envelope losers.
            conflicts = 0
            # Inspect both futures after the provider serialized them.
            for future in (email_future, invitation_future):
                # Start protected result materialization for the expected loser.
                try:
                    # Retain the one committed receipt.
                    results.append(future.result(timeout=10))
                # Count only the standard stale-preview conflict.
                except ConflictError as exc:
                    # Require one value-free fixed conflict message.
                    self.assertEqual(exc.message, "Enrollment policy preview is stale")
                    # Count this stale contender.
                    conflicts += 1
        # Require exactly one winner and one stale contender.
        self.assertEqual((len(results), conflicts), (1, 1))
        # Require the one successful receipt to consume the shared revision.
        self.assertEqual(results[0]["previous_revision"], shared_revision)
        # Require exactly one immutable entry for the one committed transaction.
        audit_rows = enrollment_policy.change_audit()
        # Require the losing contender to append no audit evidence.
        self.assertEqual(audit_rows, [results[0]["audit"]])

    # Prove an old preview remains stale after change and exact-policy rollback.
    def test_change_then_rollback_invalidates_old_preview_without_side_effects(self) -> None:
        # Capture an opening preview at the legacy no-audit revision.
        old_preview = enrollment_policy.propose(self._opening_changes())
        # Commit the opening change against that exact revision.
        opened = enrollment_policy.update(self._opening_changes(), actor_id=self.owner["user_id"], reason="Open reviewed private enrollment", expected_revision=old_preview["revision"])
        # Restore the exact prior policy against the opening transaction's returned revision.
        restored = enrollment_policy.update(enrollment_policy.changes_for_policy(opened["previous"]), actor_id=self.owner["user_id"], reason="Restore exact prior policy", expected_revision=opened["revision"])
        # Require policy bytes to be semantically identical while the audit-bound revision advanced.
        self.assertEqual(restored["current"], old_preview["previous"])
        # Require the ABA-safe revision to differ from the original preview.
        self.assertNotEqual(restored["revision"], old_preview["revision"])
        # Capture exact durable bytes and audit after the two legitimate commits.
        restored_bytes = self._policy_path().read_bytes()
        # Capture the exact verified audit for no-side-effect comparison.
        restored_audit = enrollment_policy.change_audit()
        # Block the unrelated operational logger to prove stale apply never reaches it.
        with mock.patch.object(enrollment_policy.logger, "info") as audit_log:
            # Require the old preview revision to conflict without disclosing current state.
            with self.assertRaises(ConflictError) as stale:
                # Attempt the old opening proposal after the ABA sequence.
                enrollment_policy.update(self._opening_changes(), actor_id=self.owner["user_id"], reason="Stale ABA attempt", expected_revision=old_preview["revision"])
        # Require the fixed value-free conflict message.
        self.assertEqual(stale.exception.message, "Enrollment policy preview is stale")
        # Require no operational log side effect.
        audit_log.assert_not_called()
        # Require exact policy and audit bytes to remain unchanged.
        self.assertEqual(self._policy_path().read_bytes(), restored_bytes)
        # Require no audit append on stale conflict.
        self.assertEqual(enrollment_policy.change_audit(), restored_audit)

    # Prove every rejected proposal or attribution leaves exact prior bytes and audit unchanged.
    def test_rejected_mutations_preserve_exact_bytes_and_audit(self) -> None:
        # Seed one valid provider document and immutable audit entry.
        self._apply_current({}, "Establish reviewed baseline")
        # Capture exact durable bytes before hostile attempts.
        original = self._policy_path().read_bytes()
        # Enumerate malformed changes, actors, and reasons independently.
        hostile_cases = [
            # Reject a blank reason.
            ({}, self.owner["user_id"], "   "),
            # Reject an oversized reason.
            ({}, self.owner["user_id"], "R" * (enrollment_policy.MAX_CHANGE_REASON_LENGTH + 1)),
            # Reject multiline reason material.
            ({}, self.owner["user_id"], "line one\nline two"),
            # Reject multiline actor material.
            ({}, "owner\nother", "Reviewed reason"),
            # Reject an unknown mode.
            ({"mode": "everyone"}, self.owner["user_id"], "Reviewed reason"),
            # Reject an unknown method.
            ({"methods": {"passkey": True}}, self.owner["user_id"], "Reviewed reason"),
            # Reject a truthy method alias.
            ({"methods": {"email": "yes"}}, self.owner["user_id"], "Reviewed reason"),
            # Reject a truthy invitation alias.
            ({"invitations_enabled": 1}, self.owner["user_id"], "Reviewed reason"),
            # Reject an unsupported authority field.
            ({"roles": ["admin"]}, self.owner["user_id"], "Reviewed reason"),
        ]
        # Exercise every hostile mutation without sharing exception state.
        for changes, actor_id, reason in hostile_cases:
            # Name the rejected shape in focused output without printing its values.
            with self.subTest(change_keys=sorted(changes)):
                # Require a stable validation failure before provider mutation.
                with self.assertRaises(ValidationError):
                    # Attempt the hostile update.
                    enrollment_policy.update(changes, actor_id=actor_id, reason=reason, expected_revision=enrollment_policy.owner_view()["revision"])
                # Require byte-identical durable state after each failure.
                self.assertEqual(self._policy_path().read_bytes(), original)
        # Require no rejected attempt to append actor/change evidence.
        self.assertEqual(len(enrollment_policy.change_audit()), 1)

    # Prove audit or policy tamper blocks every policy consumer before logging or mutation.
    def test_tampered_audit_or_policy_fails_closed_without_repair(self) -> None:
        # Commit one valid owner transaction.
        self._apply_current(self._opening_changes(), "Commit reviewed state")
        # Retain one complete valid document for independent hostile variants.
        valid = self.provider.read_document(enrollment_policy.POLICY_DOCUMENT_KEY, {})
        # Build one listener-free route table for mutation-boundary proof.
        router = _build_router_for_route_test()
        # Enumerate a corrupt digest and a policy/current mismatch independently.
        for corruption in ("digest", "policy"):
            # Name the exact corrupted binding in focused output.
            with self.subTest(corruption=corruption):
                # Start each hostile fixture from the same verified document.
                raw = copy.deepcopy(valid)
                # Corrupt only the stored self-digest in the first variant.
                if corruption == "digest":
                    # Break the hash without changing the policy.
                    raw[enrollment_policy.CHANGE_AUDIT_FIELD][0]["digest"] = "f" * 64
                # Corrupt only the bound current policy in the second variant.
                else:
                    # Diverge the durable policy from the audit row's exact committed state.
                    raw["mode"] = enrollment_policy.MODE_CLOSED
                # Persist the explicit hostile fixture outside the policy module.
                self.provider.write_document(enrollment_policy.POLICY_DOCUMENT_KEY, raw)
                # Capture the exact corrupt bytes before fail-closed access.
                corrupt_bytes = self._policy_path().read_bytes()
                # Block the operational logger and both downstream enrollment mutation seams.
                with mock.patch.object(enrollment_policy.logger, "info") as audit_log, mock.patch.object(auth, "create_user") as create_user, mock.patch.object(invitations, "redeem") as redeem:
                    # Exercise every direct public policy consumer.
                    consumers = (
                        # Read the effective policy directly.
                        ("current", enrollment_policy.current),
                        # Derive public capabilities from that policy.
                        ("capabilities", enrollment_policy.capabilities),
                        # Attempt the signup decision that would otherwise log allowance.
                        ("evaluate", lambda: enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP)),
                    )
                    # Require each consumer to stop on the same fixed recovery boundary.
                    for consumer_name, consumer in consumers:
                        # Preserve the failing consumer identity in focused output.
                        with self.subTest(corruption=corruption, consumer=consumer_name):
                            # Require fail-closed verification before policy use.
                            with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit requires operator recovery$"):
                                # Invoke the selected policy consumer.
                                consumer()
                    # Require public signup to stop before account creation.
                    with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit requires operator recovery$"):
                        # Dispatch one complete signup request over the corrupt policy.
                        router.dispatch("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "SyntheticSignupPassw0rd!23", "display_name": "Held", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
                    # Require invitation redemption to stop before bearer consumption.
                    with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit requires operator recovery$"):
                        # Dispatch one complete invitation request over the corrupt policy.
                        router.dispatch("POST", "/api/v2/auth/redeem-invitation", {"token": "synthetic-token", "email": "invitee@example.invalid", "password": "Synthetic-Invite-2026!", "display_name": "Invitee", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True, "idempotency_key": "synthetic-redeem-key"})
                # Require verification to fail before any operational enrollment log.
                audit_log.assert_not_called()
                # Require neither governed mutation seam to start.
                self.assertEqual((create_user.call_count, redeem.call_count), (0, 0))
                # Require exact corrupt evidence preservation.
                self.assertEqual(self._policy_path().read_bytes(), corrupt_bytes)

    # Prove a coherently rehashed but non-provider audit identity still fails closed.
    def test_rehashed_noncanonical_audit_identity_requires_recovery(self) -> None:
        # Commit one valid owner transaction.
        self._apply_current(self._opening_changes(), "Commit reviewed state")
        # Read the complete raw provider document for hostile fixture construction.
        raw = self.provider.read_document(enrollment_policy.POLICY_DOCUMENT_KEY, {})
        # Select the sole committed audit row.
        row = raw[enrollment_policy.CHANGE_AUDIT_FIELD][0]
        # Replace the opaque hexadecimal suffix with a printable but noncanonical value.
        row["audit_id"] = "enrollaudit_" + ("z" * 16)
        # Rebuild the exact signed payload so the identity check, not a stale hash, rejects it.
        payload = {field: copy.deepcopy(row[field]) for field in enrollment_policy.CHANGE_AUDIT_PAYLOAD_FIELDS}
        # Coherently rehash the hostile payload.
        row["digest"] = enrollment_policy._digest(payload)
        # Persist the explicit hostile fixture outside the policy module.
        self.provider.write_document(enrollment_policy.POLICY_DOCUMENT_KEY, raw)
        # Capture the exact corrupt bytes before fail-closed access.
        corrupt_bytes = self._policy_path().read_bytes()
        # Require owner visibility to reject the non-provider audit identity.
        with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit requires operator recovery$"):
            # Attempt the coherent owner read.
            enrollment_policy.owner_view()
        # Require exact hostile evidence preservation.
        self.assertEqual(self._policy_path().read_bytes(), corrupt_bytes)

    # Prove malformed bytes and non-object JSON fail before fallback, logging, or apply.
    def test_strict_security_read_preserves_malformed_bytes_and_inventory(self) -> None:
        # Build one policy proposal used only to prove preview cannot normalize corruption.
        opening = self._opening_changes()
        # Prime the existing stable and per-document lock identities while the document is absent.
        self.provider.read_document_strict(enrollment_policy.POLICY_DOCUMENT_KEY, enrollment_policy._document_default, enrollment_policy._policy_document_shape)
        # Enumerate truncated JSON, invalid UTF-8, and a malformed owned-schema shape.
        hostile_payloads = (
            # Leave a JSON object syntactically incomplete.
            b'{"schema_version":1',
            # Store bytes that cannot decode as UTF-8 JSON text.
            b"\xff\xfe\xfa",
            # Store a schema-one object whose methods collection has the wrong type.
            b'{"schema_version":1,"mode":"closed","methods":[],"invitations_enabled":false}',
        )
        # Exercise each malformed durable representation independently.
        for hostile in hostile_payloads:
            # Name only the bounded payload length in focused output.
            with self.subTest(payload_bytes=len(hostile)):
                # Ensure the nested auth document directory exists for direct hostile setup.
                self._policy_path().parent.mkdir(parents=True, exist_ok=True)
                # Persist the exact hostile bytes outside the provider abstraction.
                self._policy_path().write_bytes(hostile)
                # Capture every provider/control file after setup and before any strict read.
                original = self._provider_inventory()
                # Block operational logging while every policy consumer is exercised.
                with mock.patch.object(enrollment_policy.logger, "info") as audit_log:
                    # Enumerate all mutation-free policy consumers.
                    consumers = (
                        # Read the current effective policy.
                        enrollment_policy.current,
                        # Resolve the public capability view.
                        enrollment_policy.capabilities,
                        # Evaluate a governed public mutation.
                        lambda: enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP),
                        # Preview one owner proposal.
                        lambda: enrollment_policy.propose(opening),
                        # Read the coherent owner policy and audit view.
                        enrollment_policy.owner_view,
                    )
                    # Require every consumer to stop at the provider-owned fixed boundary.
                    for consumer in consumers:
                        # Refuse malformed bytes without disclosing their value or path.
                        with self.assertRaisesRegex(RuntimeError, "^Stored document requires operator recovery$"):
                            # Invoke the selected strict consumer.
                            consumer()
                    # Require apply to fail before the provider mutator or audit allocation.
                    with self.assertRaisesRegex(RuntimeError, "^Stored document requires operator recovery$"):
                        # Attempt an otherwise valid owner update using one fixed revision token.
                        enrollment_policy.update(opening, actor_id=self.owner["user_id"], reason="Must not normalize corrupt state", expected_revision="0" * 64)
                # Require no operational decision log from any refused consumer.
                audit_log.assert_not_called()
                # Require byte-identical provider state and no corrupt backup, temp, or side residue.
                self.assertEqual(self._provider_inventory(), original)

    # Prove exact audit capacity remains readable and never truncates on refusal.
    def test_audit_capacity_is_bounded_without_truncation_or_normalization(self) -> None:
        # Commit one valid entry at the future patched capacity.
        first = self._apply_current({}, "Establish exact capacity")
        # Capture the exact one-entry provider bytes.
        at_limit_bytes = self._policy_path().read_bytes()
        # Lower the configured capacity to the exact existing row count.
        with mock.patch.object(enrollment_policy, "MAX_CHANGE_AUDIT_ENTRIES", 1):
            # Require the exact-limit policy to remain readable.
            self.assertEqual(enrollment_policy.current()["mode"], enrollment_policy.MODE_CLOSED)
            # Require the exact-limit audit to remain intact.
            self.assertEqual(len(enrollment_policy.change_audit()), 1)
            # Refuse a next apply at the fixed capacity boundary.
            with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit capacity requires operator recovery$"):
                # Attempt another valid owner transaction.
                enrollment_policy.update({}, actor_id=self.owner["user_id"], reason="Must not truncate exact capacity", expected_revision=first["revision"])
            # Require no row deletion, normalization, or byte rewrite.
            self.assertEqual(self._policy_path().read_bytes(), at_limit_bytes)
        # Commit a second valid row after restoring the governed production capacity.
        second = enrollment_policy.update({}, actor_id=self.owner["user_id"], reason="Create hostile over-capacity fixture", expected_revision=first["revision"])
        # Capture the exact two-entry provider bytes.
        over_limit_bytes = self._policy_path().read_bytes()
        # Lower the visible capacity below the stored row count.
        with mock.patch.object(enrollment_policy, "MAX_CHANGE_AUDIT_ENTRIES", 1):
            # Refuse reads of over-capacity audit state.
            with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit requires operator recovery$"):
                # Attempt a public policy read through the audit-bound current seam.
                enrollment_policy.current()
            # Refuse apply before normalization or truncation.
            with self.assertRaisesRegex(RuntimeError, "^Enrollment policy audit requires operator recovery$"):
                # Attempt another otherwise valid owner transaction.
                enrollment_policy.update({}, actor_id=self.owner["user_id"], reason="Must not normalize over capacity", expected_revision=second["revision"])
            # Require exact over-capacity evidence preservation.
            self.assertEqual(self._policy_path().read_bytes(), over_limit_bytes)

    # Prove ordinary Admins cannot read, preview, or apply owner policy state.
    def test_all_admin_policy_routes_require_current_platform_owner(self) -> None:
        # Build one listener-free route table with the complete Admin registrations.
        router = _build_router_for_route_test()
        # Resolve the authenticated context to an ordinary current Admin on every route.
        with mock.patch.object(auth, "find_user_by_id", return_value=self.ordinary_admin):
            # Require the owner read to refuse ordinary Admin access.
            with self.assertRaises(ForbiddenError):
                # Dispatch the read route with only ordinary Admin authority.
                router.dispatch("GET", "/api/v2/admin/enrollment-policy", {}, context={"user": self.ordinary_admin})
            # Require preview to refuse before proposal validation.
            with self.assertRaises(ForbiddenError):
                # Dispatch one otherwise valid preview.
                router.dispatch("POST", "/api/v2/admin/enrollment-policy/preview", {"changes": self._opening_changes()}, context={"user": self.ordinary_admin})
            # Require apply to refuse before confirmation or provider mutation.
            with self.assertRaises(ForbiddenError):
                # Dispatch one otherwise valid confirmed apply.
                router.dispatch("POST", "/api/v2/admin/enrollment-policy", {"changes": self._opening_changes(), "revision": "0" * 64, "confirm": True, "reason": "Unauthorized attempt"}, context={"user": self.ordinary_admin})
        # Require no policy document or audit was created by any denied route.
        self.assertFalse(self._policy_path().exists())

    # Prove stale owner-shaped session context cannot survive canonical demotion or inactivation.
    def test_stale_owner_context_is_denied_by_current_canonical_state(self) -> None:
        # Build one listener-free route table with the complete Admin registrations.
        router = _build_router_for_route_test()
        # Retain the stale session's claimed owner-shaped context.
        stale_context = {"user": dict(self.owner)}
        # Enumerate canonical demotion and inactivation independently.
        canonical_states = (
            # Remove platform-owner authority while retaining active Admin access.
            {"user_id": self.owner["user_id"], "status": "active", "role": "admin", "roles": ["admin"]},
            # Retain the role only on an inactive canonical account.
            {"user_id": self.owner["user_id"], "status": "disabled", "role": "admin", "roles": ["admin", auth.PLATFORM_OWNER_ROLE]},
        )
        # Exercise every current-state denial without sharing mock state.
        for canonical in canonical_states:
            # Name the canonical status and role set in focused output.
            with self.subTest(status=canonical["status"], roles=canonical["roles"]):
                # Resolve the stale session id to the hostile current canonical state.
                with mock.patch.object(auth, "find_user_by_id", return_value=canonical):
                    # Require the owner read to refuse stale authority.
                    with self.assertRaises(ForbiddenError):
                        # Dispatch the read route with stale owner-shaped context.
                        router.dispatch("GET", "/api/v2/admin/enrollment-policy", {}, context=stale_context)
                    # Require preview to refuse stale authority.
                    with self.assertRaises(ForbiddenError):
                        # Dispatch one otherwise valid preview.
                        router.dispatch("POST", "/api/v2/admin/enrollment-policy/preview", {"changes": self._opening_changes()}, context=stale_context)
                    # Require apply to refuse stale authority before provider mutation.
                    with self.assertRaises(ForbiddenError):
                        # Dispatch one otherwise valid confirmed apply.
                        router.dispatch("POST", "/api/v2/admin/enrollment-policy", {"changes": self._opening_changes(), "revision": "0" * 64, "confirm": True, "reason": "Stale owner must not apply"}, context=stale_context)
                # Require no policy document or audit was created by stale authority.
                self.assertFalse(self._policy_path().exists())

    # Prove owner routes preview without writes, commit once, expose audit, and accept exact rollback.
    def test_owner_routes_preview_apply_read_and_exact_rollback(self) -> None:
        # Build one listener-free route table.
        router = _build_router_for_route_test()
        # Resolve every session payload through the canonical current owner.
        with mock.patch.object(auth, "find_user_by_id", return_value=self.owner):
            # Preview one opening proposal.
            preview = router.dispatch("POST", "/api/v2/admin/enrollment-policy/preview", {"changes": self._opening_changes()}, context={"user": {"user_id": self.owner["user_id"]}})
            # Require preview to leave no provider policy document.
            self.assertFalse(self._policy_path().exists())
            # Reject a truthy non-boolean confirmation before mutation.
            with self.assertRaises(ValidationError):
                # Attempt apply with a string confirmation alias.
                router.dispatch("POST", "/api/v2/admin/enrollment-policy", {"changes": self._opening_changes(), "confirm": "true", "reason": "Must not apply"}, context={"user": {"user_id": self.owner["user_id"]}})
            # Require confirmation refusal to remain write-free.
            self.assertFalse(self._policy_path().exists())
            # Prove Admin mutation does not depend on the operational decision logger.
            with mock.patch.object(enrollment_policy.logger, "info", side_effect=OSError("operational-log-unavailable")):
                # Apply the exact previewed proposal with fixed confirmation and reason.
                applied = router.dispatch("POST", "/api/v2/admin/enrollment-policy", {"changes": self._opening_changes(), "revision": preview["revision"], "confirm": True, "reason": "Owner-approved private enrollment"}, context={"user": {"user_id": self.owner["user_id"]}})
            # Require route projection to equal the preview's policy and impact.
            self.assertEqual((applied["policy"], applied["previous"], applied["impact"]), (preview["policy"], preview["previous"], preview["impact"]))
            # Require apply to report both the consumed preview revision and new rollback revision.
            self.assertEqual((applied["previous_revision"], len(applied["revision"])), (preview["revision"], 64))
            # Read the coherent owner view after apply.
            view = router.dispatch("GET", "/api/v2/admin/enrollment-policy", {}, context={"user": {"user_id": self.owner["user_id"]}})
            # Require policy, capabilities, and immutable receipt to come from one committed document.
            self.assertEqual((view["policy"], view["capabilities"], view["audit"]), (applied["policy"], preview["impact"]["after"], [applied["audit"]]))
            # Require owner visibility to expose the same current revision as the apply receipt.
            self.assertEqual(view["revision"], applied["revision"])
            # Apply the exact returned prior policy as one rollback request.
            restored = router.dispatch("POST", "/api/v2/admin/enrollment-policy", {"policy": applied["previous"], "revision": applied["revision"], "confirm": True, "reason": "Application rollback to exact prior policy"}, context={"user": {"user_id": self.owner["user_id"]}})
        # Require exact prior-policy restoration.
        self.assertEqual(restored["policy"], applied["previous"])
        # Require immutable opening and rollback entries to remain provider-backed.
        self.assertEqual(len(enrollment_policy.change_audit()), 2)


# Allow direct execution for focused local runs.
if __name__ == "__main__":
    # Run the focused suite.
    unittest.main()
