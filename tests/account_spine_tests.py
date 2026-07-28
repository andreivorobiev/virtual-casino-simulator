"""Focused listener-free tests for the product account-management spine."""

# Import a bounded thread pool for concurrent last-active-Admin proof.
from concurrent.futures import ThreadPoolExecutor
# Import a barrier so both Admin mutations pass their public pre-read before the atomic claim.
import threading
# Import timedelta so timeout-policy tests can age server-owned session timestamps deterministically.
from datetime import timedelta
# Import temporary storage roots for feedback tests that must not touch user data.
import tempfile
# Import unittest so the central API runner can execute this focused suite.
import unittest
# Import patching so the concurrency test synchronizes only the canonical identity mutation.
from unittest.mock import patch
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
from casino.errors import ForbiddenError, UnauthorizedError, ValidationError


# Verify product-account policy, Admin roles, passkeys, and reporter status remain bounded.
class ProductAccountSpineTests(unittest.TestCase):
    # Reset global JSON state enough for listener-free account tests.
    def setUp(self) -> None:
        # Reset auth identities so one test's role changes cannot leak into another test.
        write_json(auth.USERS_PATH, auth.default_users())
        # Reset auth sessions so role-revocation assertions start empty.
        write_json(auth.SESSIONS_PATH, auth.default_sessions())
        # Reset the server-authoritative timeout policy so every test begins with approved defaults.
        write_json(auth.SESSION_TIMEOUT_POLICY_PATH, auth.default_session_timeout_policy())
        # Reset wallet records so Admin-created users receive predictable linked players.
        players.save_players(players.default_players())
        # Allocate an isolated feedback provider for reporter-status tests.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-account-spine-")
        # Point feedback at the isolated provider.
        storage.set_provider_for_tests(storage.JsonStorageProvider(Path(self.temporary.name) / "data"))

    # Restore global provider state after every test.
    def tearDown(self) -> None:
        # Restore valid timeout policy even when a corruption test intentionally writes invalid bytes.
        write_json(auth.SESSION_TIMEOUT_POLICY_PATH, auth.default_session_timeout_policy())
        # Release the feedback provider seam.
        storage.set_provider_for_tests(None)
        # Remove the isolated feedback documents.
        self.temporary.cleanup()

    # Build the active platform owner that alone can delegate Admin authority.
    def _owner_admin(self) -> dict:
        # Create the compatible canonical Admin account.
        owner = auth.create_user("owner-admin@example.test", "OwnerAdminPassw0rd!23", "Owner Admin", role="admin", terms_required=False)
        # Attach bootstrap-only owner authority through the canonical privilege mutation.
        return auth.update_user_by_id(owner["user_id"], lambda user: user.update({"role": "admin", "roles": ["admin", auth.PLATFORM_OWNER_ROLE]}))

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

    # Prove only the platform owner can delegate Admin while ordinary lifecycle controls remain bounded.
    def test_platform_owner_controls_admin_roles_and_lifecycle(self) -> None:
        # Seed the current active platform owner.
        owner = self._owner_admin()
        # Create one managed player account through the Admin API helper.
        created = admin.create_admin_user({"email": "managed@example.test", "display_name": "Managed User", "password": "ManagedUserPassw0rd!23", "role": "player", "terms_accepted": True})["user"]
        # Promote the already-active managed account through owner authority.
        promoted = admin.update_admin_user(created["user_id"], {"roles": ["admin"], "status": "active"}, actor=owner)
        # Require the account to carry the Admin role and active lifecycle.
        self.assertEqual((promoted["roles"], promoted["status"], promoted["active"]), (["admin"], "active", True))
        # Create another ordinary player target for denied Admin delegation.
        other = admin.create_admin_user({"email": "other@example.test", "display_name": "Other User", "password": "OtherUserPassw0rd!23", "role": "player", "terms_accepted": True})["user"]
        # Reject role delegation by an ordinary Admin.
        with self.assertRaises(ForbiddenError):
            # Attempt to grant Admin authority from a non-owner actor.
            admin.update_admin_user(other["user_id"], {"roles": ["admin"]}, actor=promoted)
        # Move the second target inactive through the ordinary lifecycle boundary.
        inactive = admin.update_admin_user(other["user_id"], {"status": "inactive"})
        # Require the inactive account to remain retained and visible.
        self.assertEqual((inactive["status"], inactive["active"]), ("inactive", False))
        # Reject a combined or direct Admin grant to an inactive account.
        with self.assertRaises(ValidationError):
            # Attempt owner-authorized privilege assignment before reactivation.
            admin.update_admin_user(other["user_id"], {"roles": ["admin"], "status": "active"}, actor=owner)
        # Suspend the promoted account without conflating it with deletion.
        suspended = admin.update_admin_user(created["user_id"], {"status": "suspended"})
        # Require suspended accounts to remain visible but inactive.
        self.assertEqual((suspended["status"], suspended["active"]), ("suspended", False))
        # Demote and reactivate the account through owner authority.
        demoted = admin.update_admin_user(created["user_id"], {"roles": ["player"], "status": "active"}, actor=owner)
        # Require the player role to replace Admin authority.
        self.assertEqual(demoted["roles"], ["player"])
        # Reject any direct mutation of bootstrap-managed owner authority.
        with self.assertRaises(ForbiddenError):
            # Attempt to demote the platform owner through assignable account roles.
            admin.update_admin_user(owner["user_id"], {"roles": ["player"]}, actor=owner)
        # Reject suspending the last active platform owner.
        with self.assertRaises(ValidationError):
            # Attempt to remove the sole remaining owner recovery path.
            admin.update_admin_user(owner["user_id"], {"status": "suspended"})

    # Prove concurrent demotions preserve the owner even when calls share a stale pre-read.
    def test_concurrent_admin_demotion_preserves_platform_owner(self) -> None:
        # Seed the bootstrap-managed owner account.
        owner = self._owner_admin()
        # Seed a second active account as an ordinary player.
        second_player = admin.create_admin_user({"email": "second-admin@example.test", "display_name": "Second Admin", "password": "SecondAdminPassw0rd!23", "role": "player", "terms_accepted": True})["user"]
        # Grant the second account ordinary Admin authority through the owner.
        second = admin.update_admin_user(second_player["user_id"], {"roles": ["admin"]}, actor=owner)
        # Synchronize both callers after their account-only pre-read and before the identity transaction.
        mutation_barrier = threading.Barrier(2)
        # Retain the production atomic identity updater behind the synchronization seam.
        update_user = auth.update_user_by_id
        # Define one synchronized identity update used only by this test.
        def synchronized_update(*args, **kwargs):
            # Release both contenders only after each public Admin path reaches the canonical update.
            mutation_barrier.wait(timeout=5)
            # Delegate state validation and persistence to the production provider transaction.
            return update_user(*args, **kwargs)
        # Define one demotion contender with a bounded outcome.
        def demote(user_id: str) -> str:
            # Attempt to remove this account's Admin role.
            try:
                # Return the committed outcome when the invariant permits this demotion.
                admin.update_admin_user(user_id, {"roles": ["player"], "status": "active"}, actor=owner)
                # Mark the one accepted mutation.
                return "updated"
            # Treat the owner-target mutation as the required authority rejection.
            except (ForbiddenError, ValidationError):
                # Mark the protected mutation.
                return "blocked"
        # Patch the shared updater so both public Admin calls contend at the atomic boundary.
        with patch.object(auth, "update_user_by_id", side_effect=synchronized_update):
            # Execute both demotions concurrently over the same identity document.
            with ThreadPoolExecutor(max_workers=2) as pool:
                # Materialize both bounded outcomes before leaving the patched boundary.
                outcomes = list(pool.map(demote, (owner["user_id"], second["user_id"])))
        # Require exactly one successful demotion and one invariant rejection.
        self.assertEqual(sorted(outcomes), ["blocked", "updated"])
        # Resolve all active identities that retain effective Admin access.
        remaining = [user for user in auth.load_users().get("users", []) if auth.is_admin(user)]
        # Require only the owner to retain effective Admin access after the race.
        self.assertEqual([(user["user_id"], auth.is_platform_owner(user)) for user in remaining], [(owner["user_id"], True)])

    # Prove bootstrap migration is one-way, session-invalidating, and idempotent.
    def test_bootstrap_admin_is_promoted_to_platform_owner_once(self) -> None:
        # Create the configured bootstrap identity in its legacy Admin-only shape.
        legacy = auth.create_user(auth.AUTH_BOOTSTRAP_ADMIN_EMAIL, "OwnerAdminPassw0rd!23", "Legacy Bootstrap", role="admin", terms_required=False)
        # Create one predecessor session that must lose its pre-owner privilege snapshot.
        predecessor = auth.create_session(legacy, "owner-migration-test")
        # Run the normal process-start bootstrap migration.
        migrated = auth.bootstrap_admin_from_env()
        # Require compatible Admin presentation plus bootstrap-only owner authority.
        self.assertEqual((migrated["role"], migrated["roles"], auth.is_admin(migrated), auth.is_platform_owner(migrated)), ("admin", ["admin", auth.PLATFORM_OWNER_ROLE], True, True))
        # Resolve the retained audit row for the predecessor session.
        revoked_predecessor = next(session for session in auth.load_sessions().get("sessions", []) if session.get("session_id") == predecessor["session_id"])
        # Require the committed privilege change to retain but invalidate the predecessor session.
        self.assertEqual(revoked_predecessor.get("status"), "revoked")
        # Create a fresh session after the one-time migration.
        current = auth.create_session(migrated, "owner-idempotency-test")
        # Re-run bootstrap without another privilege write.
        repeated = auth.bootstrap_admin_from_env()
        # Require stable roles and preservation of the post-migration session.
        self.assertEqual(repeated["roles"], ["admin", auth.PLATFORM_OWNER_ROLE])
        # Require idempotent startup to keep the current owner session active.
        self.assertTrue(any(session.get("session_id") == current["session_id"] for session in auth.load_sessions().get("sessions", [])))

    # Prove additive v2 policy separates ordinary account creation from Admin delegation.
    def test_v2_creation_is_player_only_and_owner_delegation_is_explicit(self) -> None:
        # Seed the bootstrap owner.
        owner = self._owner_admin()
        # Reject direct Admin creation through the additive v2 contract even for the owner.
        with self.assertRaises(ValidationError):
            # Attempt to skip the existing-active-account delegation rule.
            ROUTER.dispatch("POST", "/api/v2/admin/users", {"username": "direct-v2-admin@example.test", "password": "DirectV2AdminPassw0rd!23", "display_name": "Direct V2 Admin", "roles": ["admin"], "locale": "en-US"}, context={"user": owner})
        # Create an ordinary active player through the additive v2 contract.
        created = ROUTER.dispatch("POST", "/api/v2/admin/users", {"username": "delegation-target@example.test", "password": "DelegationTargetPassw0rd!23", "display_name": "Delegation Target", "roles": ["player"], "locale": "en-US"}, context={"user": owner})
        # Grant ordinary Admin authority only through the explicit owner-authorized update.
        promoted = ROUTER.dispatch("PATCH", f"/api/v2/admin/users/{created['user_id']}", {"roles": ["admin"]}, context={"user": owner})
        # Require the target to gain ordinary Admin without bootstrap-owner authority.
        self.assertEqual((promoted["roles"], auth.is_platform_owner(promoted)), (["admin"], False))

    # Prove only the platform owner can persist one bounded timeout policy. (SESSION-009, TEST-146)
    def test_platform_owner_controls_session_timeout_policy(self) -> None:
        # Read the absent/default-equivalent policy through the strict production boundary.
        defaults = auth.load_session_timeout_policy()
        # Require the owner-approved default and bounds-facing values.
        self.assertEqual((defaults["enabled"], defaults["idle_timeout_seconds"], defaults["absolute_timeout_seconds"], defaults["warning_seconds"]), (True, 1_800, 43_200, 120))
        # Seed the sole current platform owner.
        owner = self._owner_admin()
        # Create one ordinary account and grant only normal Admin authority.
        ordinary = auth.create_user("timeout-admin@example.test", "TimeoutAdminPassw0rd!23", "Timeout Admin", terms_required=False)
        # Attach ordinary Admin authority without bootstrap ownership.
        ordinary_admin = auth.update_user_by_id(ordinary["user_id"], lambda user: user.update({"role": "admin", "roles": ["admin"]}))
        # Reject configuration mutation by an ordinary Admin.
        with self.assertRaises(ForbiddenError):
            # Attempt to shorten the idle duration without owner authority.
            auth.update_session_timeout_policy(ordinary_admin, {"idle_timeout_seconds": 600})
        # Commit a complete bounded owner-authorized policy update.
        updated = auth.update_session_timeout_policy(owner, {"enabled": True, "idle_timeout_seconds": 600, "absolute_timeout_seconds": 3_600, "warning_seconds": 60})
        # Require exact effective values and canonical opaque actor metadata.
        self.assertEqual((updated["enabled"], updated["idle_timeout_seconds"], updated["absolute_timeout_seconds"], updated["warning_seconds"], updated["updated_by"]), (True, 600, 3_600, 60, owner["user_id"]))
        # Require one bounded server timestamp without caller-provided audit text.
        self.assertIsInstance(updated["updated_at"], str)
        # Reject booleans-as-durations, out-of-range values, impossible warnings, and unknown fields.
        for invalid in ({"idle_timeout_seconds": True}, {"idle_timeout_seconds": 299}, {"absolute_timeout_seconds": 1_799}, {"warning_seconds": 601}, {"idle_timeout_seconds": 300, "warning_seconds": 300}, {"provider": "browser"}):
            # Keep each invalid mutation outside durable policy state.
            with self.assertRaises(ValidationError):
                # Attempt the bounded owner mutation.
                auth.update_session_timeout_policy(owner, invalid)
        # Require rejected requests to leave the committed valid policy unchanged.
        self.assertEqual(auth.load_session_timeout_policy(), updated)

    # Prove idle and absolute policy changes apply to already-issued persistent sessions. (SESSION-009, TEST-146)
    def test_timeout_policy_applies_immediately_to_existing_sessions(self) -> None:
        # Seed the owner who may change policy.
        owner = self._owner_admin()
        # Create one persistent player and issue its first session under defaults.
        user = auth.create_user("timeout-user@example.test", "TimeoutUserPassw0rd!23", "Timeout User", terms_required=False)
        # Retain the opaque bearer for authoritative authentication attempts.
        idle_session = auth.create_session(user, "timeout-idle-test")
        # Capture one current server timestamp for deterministic aging.
        now = auth.utc_datetime()
        # Age the first session beyond the shortest allowed idle duration while preserving legacy expiry.
        def age_idle(state: dict) -> dict:
            # Locate only the newly issued row.
            for stored in state.get("sessions", []):
                # Match the exact server session identifier.
                if stored.get("session_id") == idle_session["session_id"]:
                    # Preserve a recent absolute creation time.
                    stored["created_at"] = (now - timedelta(seconds=60)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    # Move last activity beyond the five-minute idle boundary.
                    stored["updated_at"] = (now - timedelta(seconds=301)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            # Return the complete session document.
            return state
        # Persist deterministic old activity through the production document seam.
        auth.update_json(auth.SESSIONS_PATH, age_idle, auth.default_sessions)
        # Shorten policy after session creation to prove existing-session application.
        auth.update_session_timeout_policy(owner, {"idle_timeout_seconds": 300, "absolute_timeout_seconds": 1_800, "warning_seconds": 60})
        # Model the host-only browser cookie used when the static shell asks for CSRF bootstrap state.
        cookie_headers = {"Cookie": f"{auth.AUTH_SESSION_COOKIE}={idle_session['token']}"}
        # Require refresh bootstrap to withhold authenticated shell proof after policy timeout.
        self.assertEqual(auth.csrf_token_for_session_cookie(cookie_headers), "")
        # Reject the now-idle session through normal authentication.
        with self.assertRaises(UnauthorizedError):
            # Attempt to authenticate the expired bearer.
            auth.authenticate_token(idle_session["token"])
        # Issue another session and age only its absolute creation timestamp.
        absolute_session = auth.create_session(user, "timeout-absolute-test")
        # Define one absolute-lifetime-only aging mutation.
        def age_absolute(state: dict) -> dict:
            # Locate the second session without changing unrelated rows.
            for stored in state.get("sessions", []):
                # Match the second opaque server identifier.
                if stored.get("session_id") == absolute_session["session_id"]:
                    # Move creation beyond the thirty-minute absolute boundary.
                    stored["created_at"] = (now - timedelta(seconds=1_801)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    # Keep last activity recent so only absolute expiry decides.
                    stored["updated_at"] = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
            # Return the complete session document.
            return state
        # Persist deterministic absolute age.
        auth.update_json(auth.SESSIONS_PATH, age_absolute, auth.default_sessions)
        # Reject the absolute-expired bearer even though activity is recent.
        with self.assertRaises(UnauthorizedError):
            # Attempt to authenticate the absolute-expired session.
            auth.authenticate_token(absolute_session["token"])
        # Issue a third session that remains within both configured policy limits.
        active_session = auth.create_session(user, "timeout-touch-test")
        # Capture one old activity timestamp beyond the bounded touch cadence.
        old_activity = (now - timedelta(seconds=61)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        # Define one still-active session aging mutation.
        def age_active(state: dict) -> dict:
            # Locate only the third session.
            for stored in state.get("sessions", []):
                # Match the exact server session identifier.
                if stored.get("session_id") == active_session["session_id"]:
                    # Preserve a recent creation time inside the absolute bound.
                    stored["created_at"] = (now - timedelta(seconds=120)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    # Age activity enough to require one server-owned touch.
                    stored["updated_at"] = old_activity
            # Return the complete session document.
            return state
        # Persist the still-valid old activity marker.
        auth.update_json(auth.SESSIONS_PATH, age_active, auth.default_sessions)
        # Authenticate normally so the server refreshes activity without browser-supplied time.
        resolved_session, resolved_user = auth.authenticate_token(active_session["token"])
        # Require the expected account and a refreshed request-local activity timestamp.
        self.assertEqual((resolved_user["user_id"], resolved_session["session_id"]), (user["user_id"], active_session["session_id"]))
        # Require the persisted server activity marker to advance from the deterministic old value.
        persisted = next(stored for stored in auth.load_sessions()["sessions"] if stored["session_id"] == active_session["session_id"])
        # Prove the bounded touch was committed and reflected locally.
        self.assertEqual(persisted["updated_at"], resolved_session["updated_at"])
        # Prove the committed timestamp advanced from the deterministic old value.
        self.assertNotEqual(persisted["updated_at"], old_activity)

    # Prove disabling policy preserves legacy expiry while enabled policy covers guest-shaped rows. (SESSION-009, TEST-146)
    def test_timeout_policy_preserves_legacy_and_guest_bounds(self) -> None:
        # Seed the current owner.
        owner = self._owner_admin()
        # Capture one current server time and a future legacy expiry.
        now = auth.utc_datetime()
        # Build one guest-shaped active row with server-owned timestamps.
        row = {"status": "active", "created_at": (now - timedelta(seconds=1_801)).isoformat(timespec="milliseconds").replace("+00:00", "Z"), "updated_at": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "expires_at": (now + timedelta(hours=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")}
        # Apply the shortest absolute policy to the generic guest-compatible session evaluator.
        policy = auth.update_session_timeout_policy(owner, {"idle_timeout_seconds": 300, "absolute_timeout_seconds": 1_800, "warning_seconds": 60})
        # Require the same server policy to reject the guest-shaped row by absolute lifetime.
        self.assertFalse(auth._session_is_active(row, now, policy))
        # Disable the added policy while retaining the established durable expiry.
        disabled = auth.update_session_timeout_policy(owner, {"enabled": False})
        # Require legacy future expiry to remain valid when owner policy is disabled.
        self.assertTrue(auth._session_is_active(row, now, disabled))
        # Require legacy expiry itself to remain authoritative under disabled policy.
        row["expires_at"] = (now - timedelta(seconds=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        # Reject the row once the established expiry is past.
        self.assertFalse(auth._session_is_active(row, now, disabled))

    # Prove malformed timeout policy fails closed and preserves exact operator evidence. (SESSION-009, TEST-146)
    def test_timeout_policy_preserves_malformed_storage(self) -> None:
        # Seed the platform owner used to prove mutation also refuses malformed current state.
        owner = self._owner_admin()
        # Seed one persistent account and valid session before corrupting only policy storage.
        user = auth.create_user("timeout-corrupt@example.test", "TimeoutCorruptPassw0rd!23", "Timeout Corrupt", terms_required=False)
        # Retain the bearer so normal authentication must consult the corrupt policy.
        session = auth.create_session(user, "timeout-corrupt-test")
        # Write syntactically invalid bytes that the strict boundary must not replace or back up.
        original = b'{\"enabled\": true, \"idle_timeout_seconds\":'
        # Persist exact invalid bytes through the isolated JSON-provider path.
        auth.SESSION_TIMEOUT_POLICY_PATH.write_bytes(original)
        # Reject both direct policy reads and authenticated access.
        with self.assertRaises(RuntimeError):
            # Attempt a strict direct read.
            auth.load_session_timeout_policy()
        # Require normal authentication to fail before restoring any shell or game route.
        with self.assertRaises(RuntimeError):
            # Attempt to authenticate while policy intent is unknowable.
            auth.authenticate_token(session["token"])
        # Require the invalid document to remain byte-identical for operator recovery.
        self.assertEqual(auth.SESSION_TIMEOUT_POLICY_PATH.read_bytes(), original)
        # Replace invalid JSON with parseable but structurally invalid policy evidence.
        malformed = b'{"schema_version":"1","enabled":"yes","idle_timeout_seconds":1800}'
        # Persist the exact malformed document without using a normalizing helper.
        auth.SESSION_TIMEOUT_POLICY_PATH.write_bytes(malformed)
        # Reject direct reads of parseable malformed policy state.
        with self.assertRaises(RuntimeError):
            # Attempt validation through the production policy reader.
            auth.load_session_timeout_policy()
        # Reject owner mutation because a partial update must not discard unknown policy intent.
        with self.assertRaises(RuntimeError):
            # Attempt to repair one field without an explicit operator recovery workflow.
            auth.update_session_timeout_policy(owner, {"enabled": False})
        # Require parseable malformed evidence to remain byte-identical after read and mutation attempts.
        self.assertEqual(auth.SESSION_TIMEOUT_POLICY_PATH.read_bytes(), malformed)

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

    # Prove localized Admin access labels stay readable inside responsive grid tracks.
    def test_admin_access_grid_bounds_localized_controls(self) -> None:
        # Resolve the repository stylesheet without starting a browser or listener.
        styles = (Path(__file__).resolve().parents[1] / "web" / "styles.css").read_text(encoding="utf-8")
        # Resolve the governed Browser harness so its owner-relative alignment remains reviewable without Chromium.
        browser_harness = (Path(__file__).resolve().parents[1] / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Require bounded desktop tracks wide enough for the complete Russian role label.
        self.assertIn("grid-template-columns: minmax(112px, 1fr) minmax(180px, 1.5fr) minmax(172px, 1.4fr);", styles)
        # Require every direct grid child to shrink inside its assigned track.
        self.assertIn(".admin-user-access-controls > * {\n  min-width: 0;\n}", styles)
        # Require the mobile breakpoint to wrap the complete group inside the measured scroll owner.
        self.assertIn('"status role"\n      "save save";', styles)
        # Require a one-line role track so translated text cannot collapse into a vertical sliver.
        self.assertIn(".admin-user-access-controls .check-row {\n  grid-area: role;\n  width: 100%;\n  white-space: nowrap;", styles)
        # Require the save action to wrap only at ordinary word boundaries.
        self.assertIn(".admin-user-access-controls .save-user-account {\n  grid-area: save;\n  width: 100%;\n  white-space: normal;\n  overflow-wrap: break-word;", styles)
        # Bound the complete mobile group below the governed scroll owner's measured inline size.
        self.assertIn("grid-template-columns: minmax(104px, 1fr) minmax(152px, 1.45fr);\n    width: 330px;", styles)
        # Require deterministic owner-relative alignment instead of browser-dependent nested table scrollIntoView behavior.
        self.assertIn("owner.scrollLeft += groupRect.left - ownerRect.left - Math.max(0,(owner.clientWidth-groupRect.width)/2)", browser_harness)
        # Require hosted evidence to diagnose role and save copy independently when containment is insufficient.
        self.assertIn("roleTextReadable:", browser_harness)
        # Require the save action's own text box to remain horizontally readable.
        self.assertIn("saveTextReadable:", browser_harness)
