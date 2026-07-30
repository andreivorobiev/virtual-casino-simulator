"""Durable enrollment-policy resolution tests. (AUTH-013)"""

# Import hashes so the additive v2 contract remains bound to its reviewed bytes.
import hashlib
# Import iteration helpers to sweep every environment-flag combination.
import itertools
# Import JSON decoding for the restricted-preview compatibility decision.
import json
# Import temporary storage roots for provider-isolated evidence.
import tempfile
# Import unittest so this focused suite runs listener-free.
import unittest
# Import portable paths for isolated providers and repository contracts.
from pathlib import Path

# Import the configuration module so the environment baseline can be varied per case.
from casino import config
# Import the module under test.
from casino.core import enrollment_policy
# Import storage so a temporary provider replaces the real data directory.
from casino.core import storage
# Import the validation envelope expected for a rejected mode.
from casino.errors import ValidationError

# Resolve the repository root for checked contract evidence.
ROOT = Path(__file__).resolve().parents[1]


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

    # Verify the additive response field and compatibility-v2 policy stay exact.
    def test_additive_v2_contract_and_read_only_compatibility_are_bound(self) -> None:
        # Read the additive auth contract without importing a YAML dependency.
        contract_path = ROOT / "contracts" / "openapi" / "auth.v2.yaml"
        # Decode the reviewed contract text for exact schema anchors.
        contract = contract_path.read_text(encoding="utf-8")
        # Require the strict response object to declare the new mode before all retained fields.
        self.assertIn("required: [enrollment_mode, signup_enabled, guest_trials_enabled, invitation_enrollment_enabled, guest_conversion_enabled, passkeys_enabled, canonical_identity, shared_auth_origin]", contract)
        # Require the new property to use the complete closed vocabulary.
        self.assertIn("enrollment_mode:\n          type: string\n          enum: [closed, invite-only, self-signup]", contract)
        # Require the v2 contract to avoid publishing or changing any v1 route.
        self.assertNotIn("/api/v1", contract)
        # Parse the explicit restricted-preview compatibility decision.
        compatibility = json.loads((ROOT / "contracts" / "compatibility" / "restricted-preview-security.json").read_text(encoding="utf-8"))
        # Require artifact v2 and the exact read-only/default-off/no-live-authority policy.
        self.assertEqual(compatibility["version"], 2)
        # Require the complete policy decision without accepting implicit defaults.
        self.assertEqual(compatibility["enrollment_policy"], {"route": "/api/v2/auth/enrollment-policy", "modes": ["closed", "invite-only", "self-signup"], "environment_seed": True, "environment_fallback": True, "public_methods_default_enabled": False, "admin_write_available": False, "live_enablement_authorized": False, "api_v1_unchanged": True})
        # Read the central exact-byte digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Bind the reviewed additive contract bytes to their tracked SHA-256.
        self.assertEqual(digests["contracts/openapi/auth.v2.yaml"], hashlib.sha256(contract_path.read_bytes()).hexdigest())


# Allow direct execution for focused local runs.
if __name__ == "__main__":
    # Run the focused suite.
    unittest.main()
