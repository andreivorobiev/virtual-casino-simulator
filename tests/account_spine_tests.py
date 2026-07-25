"""Focused listener-free tests for the product account-management spine."""

# Import temporary storage roots for feedback tests that must not touch user data.
import tempfile
# Import unittest so the central API runner can execute this focused suite.
import unittest
# Import portable paths for isolated provider setup.
from pathlib import Path

# Import the registered route table for direct endpoint dispatch.
from casino.app import ROUTER
# Import Admin account management helpers under test.
from casino import admin
# Import the canonical auth identity/session store.
from casino.core import auth
# Import reporter-status service behavior.
from casino.core import feedback
# Import wallet storage reset helpers.
from casino.core import players
# Import storage-provider seams for feedback status isolation.
from casino.core import storage
# Import direct JSON writers for auth/session reset.
from casino.core.state_store import write_json
# Import expected bounded validation and authorization errors.
from casino.errors import ForbiddenError, ValidationError


# Verify product-account policy, Admin roles, passkeys, and reporter status remain bounded.
class ProductAccountSpineTests(unittest.TestCase):
    # Reset global JSON state enough for listener-free account tests.
    def setUp(self) -> None:
        # Reset auth identities so one test's role changes cannot leak into another test.
        write_json(auth.USERS_PATH, auth.default_users())
        # Reset auth sessions so role-revocation assertions start empty.
        write_json(auth.SESSIONS_PATH, auth.default_sessions())
        # Reset wallet records so Admin-created users receive predictable linked players.
        players.save_players(players.default_players())
        # Allocate an isolated feedback provider for reporter-status tests.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-account-spine-")
        # Point feedback at the isolated provider.
        storage.set_provider_for_tests(storage.JsonStorageProvider(Path(self.temporary.name) / "data"))

    # Restore global provider state after every test.
    def tearDown(self) -> None:
        # Release the feedback provider seam.
        storage.set_provider_for_tests(None)
        # Remove the isolated feedback documents.
        self.temporary.cleanup()

    # Build one active Admin identity for role-management tests.
    def _owner_admin(self) -> dict:
        # Create a canonical local Admin account.
        return auth.create_user("owner-admin@example.test", "OwnerAdminPassw0rd!23", "Owner Admin", role="admin", terms_required=False)

    # Build one complete feedback submission body.
    def _report_body(self) -> dict:
        # Return bounded player prose without screenshots for status-list coverage.
        return {"idempotency_key": "accountspinefeedback001", "category": "account", "impact": "minor", "summary": "Account status copy", "actual": "The account page status copy needs review.", "expected": "The account page should show a clear status.", "attachments": [], "context": {"route": "/account", "locale": "en-US", "viewport_width": 1440, "viewport_height": 900, "browser_family": "Chrome", "os_family": "Windows", "reduced_motion": False}}

    # Prove the disabled enrollment policy and signup route fail closed by default.
    def test_enrollment_policy_and_disabled_signup_are_explicit(self) -> None:
        # Read the public policy route without a session.
        policy = ROUTER.dispatch("GET", "/api/v2/auth/enrollment-policy")
        # Require the owner-approved future controls to stay disabled by default.
        self.assertEqual((policy["signup_enabled"], policy["passkeys_enabled"], policy["guest_conversion_enabled"]), (False, False, True))
        # Attempt the public signup mutation with a complete payload.
        with self.assertRaises(ForbiddenError):
            # Dispatch directly with response headers to match the adapter contract.
            ROUTER.dispatch("POST", "/api/v2/auth/signup", {"email": "signup-held@example.test", "password": "SignupHeldPassw0rd!23", "display_name": "Signup Held", "terms_version": "private-beta-1", "accepted": True}, context={"client": "unit", "response_headers": []})
        # Require the failed signup attempt to create no account.
        self.assertIsNone(auth.find_user_by_email("signup-held@example.test"))

    # Prove passkeys are published only as disabled My Settings status.
    def test_passkeys_are_status_only_until_webauthn_is_certified(self) -> None:
        # Create one ordinary user for the current-user context.
        user = auth.create_user("passkey-user@example.test", "PasskeyUserPassw0rd!23", "Passkey User", terms_required=False)
        # Read the disabled passkey status.
        status = ROUTER.dispatch("GET", "/api/v2/me/passkeys", context={"user": user})
        # Require no credentials or ceremony availability.
        self.assertEqual(status["passkeys"], {"enabled": False, "registration_available": False, "authentication_available": False, "credentials": [], "canonical_identity": "casino_user_id"})
        # Require registration to fail closed.
        with self.assertRaises(ForbiddenError):
            # Attempt the future registration route.
            ROUTER.dispatch("POST", "/api/v2/me/passkeys/register", {}, context={"user": user})

    # Prove Admins can promote/demote Admin roles without leaving the product adminless.
    def test_admins_can_manage_admin_roles_and_lifecycle(self) -> None:
        # Seed the current active Admin.
        owner = self._owner_admin()
        # Create one managed player account through the Admin API helper.
        created = admin.create_admin_user({"email": "managed@example.test", "display_name": "Managed User", "password": "ManagedUserPassw0rd!23", "role": "player", "terms_accepted": True})["user"]
        # Promote the managed account to Admin.
        promoted = admin.update_admin_user(created["user_id"], {"roles": ["admin"], "status": "active"})
        # Require the account to carry the Admin role and active lifecycle.
        self.assertEqual((promoted["roles"], promoted["status"], promoted["active"]), (["admin"], "active", True))
        # Suspend the promoted account without conflating it with deletion.
        suspended = admin.update_admin_user(created["user_id"], {"status": "suspended"})
        # Require suspended accounts to remain visible but inactive.
        self.assertEqual((suspended["status"], suspended["active"]), ("suspended", False))
        # Demote the account back to player.
        demoted = admin.update_admin_user(created["user_id"], {"roles": ["player"], "status": "active"})
        # Require the player role to replace Admin authority.
        self.assertEqual(demoted["roles"], ["player"])
        # Reject removing the last active Admin role.
        with self.assertRaises(ValidationError):
            # Attempt to demote the sole remaining owner Admin.
            admin.update_admin_user(owner["user_id"], {"roles": ["player"]})
        # Reject suspending the sole remaining owner Admin.
        with self.assertRaises(ValidationError):
            # Attempt to suspend the sole remaining owner Admin.
            admin.update_admin_user(owner["user_id"], {"status": "suspended"})

    # Prove reporter-visible status follows the registered account and rejects abandoned guests.
    def test_reporter_status_is_account_scoped(self) -> None:
        # Create one durable reporter identity.
        reporter = auth.create_user("reporter@example.test", "ReporterPassw0rd!23", "Reporter", terms_required=False)
        # Submit one problem report through the production service.
        created = feedback.submit(reporter, self._report_body())
        # Read the reporter's own safe status list.
        reports = feedback.list_reporter_reports(reporter)
        # Require only the reporter's own reference and no private detail.
        self.assertEqual([created["reference"]], [row["reference"] for row in reports])
        # Require screenshots and Admin notes to stay absent.
        self.assertFalse({"attachments", "admin_notes", "history"} & set(reports[0]))
        # Build a disposable guest principal.
        guest = {"user_id": "guest_status", "identity_provider": "guest", "roles": ["guest"]}
        # Reject abandoned guest status tracking.
        with self.assertRaises(ValidationError):
            # Attempt to list reports for the guest.
            feedback.list_reporter_reports(guest)
