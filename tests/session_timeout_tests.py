"""Focused tests for registered-account idle and absolute session-timeout enforcement. (SESSION-009)"""

# Import timing primitives to build fixed-age session fixtures.
from datetime import timedelta
# Import isolated storage roots so no live identity or session data is touched.
import tempfile
# Import unittest for focused central-runner integration.
import unittest
# Import portable paths for isolated JSON provider documents.
from pathlib import Path
# Import patching so only auth document paths and the policy resolver change during each test.
from unittest.mock import patch

# Import the canonical auth identity and session service under test.
from casino.core import auth
# Import the bounded unauthorized error raised when a session times out.
from casino.errors import UnauthorizedError


# Format one UTC instant offset by a number of seconds into the stored session timestamp shape.
def _stamp(seconds_ago: int) -> str:
    # Subtract the offset from the current UTC time.
    moment = auth.utc_datetime() - timedelta(seconds=seconds_ago)
    # Match the exact millisecond Zulu format the session writer produces.
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


# Prove registered accounts are signed out on idle and absolute limits while fresh sessions slide forward. (SESSION-009)
class SessionTimeoutTests(unittest.TestCase):
    # Allocate isolated identity and session documents for every test.
    def setUp(self) -> None:
        # Create a disposable root outside the configured application data directory.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-session-timeout-")
        # Derive the isolated canonical user document.
        self.users_path = Path(self.temporary.name) / "users.json"
        # Derive the isolated canonical session document.
        self.sessions_path = Path(self.temporary.name) / "sessions.json"
        # Redirect only the auth module's user and session paths.
        self.path_patches = [patch.object(auth, "USERS_PATH", self.users_path), patch.object(auth, "SESSIONS_PATH", self.sessions_path)]
        # Activate both document-path patches before seeding fixtures.
        for path_patch in self.path_patches:
            # Start this exact patch and retain it for symmetric teardown.
            path_patch.start()
        # Seed one ordinary registered player and one admin account.
        self.player = {"user_id": "user_player", "email": "player@example.test", "identity_provider": "local", "roles": ["player"], "role": "player", "status": "active"}
        # Seed an admin so the stricter-admin idle window can be exercised.
        self.admin = {"user_id": "user_admin", "email": "admin@example.test", "identity_provider": "local", "roles": ["admin"], "role": "admin", "status": "active"}
        # Persist the isolated user document.
        auth.save_users({"schema_version": 1, "users": [self.player, self.admin], "reservations": []})
        # Start each test with an empty valid session document.
        auth.save_sessions(auth.default_sessions())

    # Stop patches and delete isolated files after every test.
    def tearDown(self) -> None:
        # Stop patches in reverse order to restore canonical module paths.
        for path_patch in reversed(self.path_patches):
            # Restore the previous module attribute.
            path_patch.stop()
        # Remove the complete temporary directory.
        self.temporary.cleanup()

    # Persist one active local session for the given owner with controlled ages.
    def _seed(self, token: str, user_id: str, created_ago: int, updated_ago: int) -> None:
        # Build a durable active session whose expiry stays far in the future so only the new policy gates it.
        session = {"session_id": f"session-{token}", "user_id": user_id, "token": token, "csrf_token": f"csrf-{token}", "status": "active", "created_at": _stamp(created_ago), "updated_at": _stamp(updated_ago), "expires_at": _stamp(-86_400), "client": "test", "auth_method": "local"}
        # Persist the single seeded session document.
        auth.save_sessions({"schema_version": 1, "sessions": [session]})

    # Idle beyond the resolved idle window revokes the session.
    def test_idle_timeout_revokes(self) -> None:
        # Fix the policy at a 30-minute idle and 12-hour absolute window.
        with patch("casino.core.session_settings.resolve_timeout_seconds", return_value=(1800, 43200)):
            # Seed a session last active 40 minutes ago, past the idle window.
            self._seed("tok-idle", self.player["user_id"], created_ago=3600, updated_ago=2400)
            # Expect the idle session to be rejected as expired.
            with self.assertRaises(UnauthorizedError):
                # Attempt to authenticate the timed-out bearer token.
                auth.authenticate_token("tok-idle")

    # Absolute lifetime beyond the resolved cap revokes even a just-active session.
    def test_absolute_timeout_revokes(self) -> None:
        # Fix the policy at a 30-minute idle and 12-hour absolute window.
        with patch("casino.core.session_settings.resolve_timeout_seconds", return_value=(1800, 43200)):
            # Seed a session created 13 hours ago but active seconds ago.
            self._seed("tok-abs", self.player["user_id"], created_ago=46_800, updated_ago=5)
            # Expect the absolute cap to reject it despite recent activity.
            with self.assertRaises(UnauthorizedError):
                # Attempt to authenticate the aged bearer token.
                auth.authenticate_token("tok-abs")

    # A fresh session authenticates and slides its activity marker forward.
    def test_active_session_authenticates_and_touches(self) -> None:
        # Fix the policy at a 30-minute idle and 12-hour absolute window.
        with patch("casino.core.session_settings.resolve_timeout_seconds", return_value=(1800, 43200)):
            # Seed a session created an hour ago and last active five minutes ago.
            self._seed("tok-ok", self.player["user_id"], created_ago=3600, updated_ago=300)
            # Authenticate the still-valid bearer token.
            session, user = auth.authenticate_token("tok-ok")
            # Confirm the owning identity resolves.
            self.assertEqual(user["user_id"], self.player["user_id"])
            # Confirm the persisted activity marker slid forward from its five-minute-old value.
            stored = [row for row in auth.load_sessions().get("sessions", []) if row["session_id"] == "session-tok-ok"][0]
            # The refreshed marker must be newer than the seeded five-minute-old stamp.
            self.assertGreater(stored["updated_at"], _stamp(300))

    # Admins hit a stricter idle window than ordinary players under the same elapsed inactivity.
    def test_admin_stricter_idle(self) -> None:
        # Return a 15-minute idle for admins and 30-minute idle for players.
        def resolve(is_admin_user: bool):
            # Give privileged accounts the shorter idle window.
            return (900, 43200) if is_admin_user else (1800, 43200)
        # Apply the account-aware policy resolver.
        with patch("casino.core.session_settings.resolve_timeout_seconds", side_effect=resolve):
            # Seed an admin session idle for 20 minutes, past the 15-minute admin window.
            self._seed("tok-admin", self.admin["user_id"], created_ago=3600, updated_ago=1200)
            # Expect the admin session to be rejected under the stricter window.
            with self.assertRaises(UnauthorizedError):
                # Attempt to authenticate the idle admin token.
                auth.authenticate_token("tok-admin")
            # Seed a player session idle for the same 20 minutes, within the 30-minute window.
            self._seed("tok-player", self.player["user_id"], created_ago=3600, updated_ago=1200)
            # The player session must still authenticate under the more lenient window.
            session, user = auth.authenticate_token("tok-player")
            # Confirm the player identity resolves.
            self.assertEqual(user["user_id"], self.player["user_id"])

    # A guest descriptor must use the durable user trial deadline rather than the unrelated session token lifetime. (SESSION-012)
    def test_guest_descriptor_uses_user_trial_expiry(self) -> None:
        # Give the guest a ten-minute trial deadline that is deliberately earlier than the token lifetime.
        guest_expiry = _stamp(-600)
        # Build the disposable principal with its canonical durable trial deadline.
        guest = {"user_id": "guest_descriptor", "identity_provider": "guest", "roles": ["guest"], "role": "guest", "guest_expires_at": guest_expiry}
        # Build a current session whose hard expiry is one day away so it cannot mask a wrong guest source.
        session = {"created_at": _stamp(60), "updated_at": _stamp(0), "expires_at": _stamp(-86_400)}
        # Resolve the read-only client scheduling contract.
        descriptor = auth.session_status_descriptor(session, guest)
        # Require the absolute bound to match the user-owned guest deadline exactly.
        self.assertEqual(descriptor["absolute_expires_at"], guest_expiry)
        # Require the effective expiry not to extend past the trial deadline.
        self.assertLessEqual(descriptor["expires_at"], guest_expiry)


# Run focused evidence directly when invoked by a developer or release validator.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
