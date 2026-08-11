# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free regression coverage for recursive Admin game-state diagnostics. (ADMIN-029, TEST-145)"""

# Import JSON so fixture state uses the production document format.
import json
# Import os so storage roots are isolated before casino modules resolve configuration.
import os
# Import tempfile for a disposable provider root.
import tempfile
# Import unittest for the dependency-free runner.
import unittest
# Import patching so the empty-state case can use a missing game-data root.
from unittest.mock import patch
# Import Path for platform-safe fixture paths.
from pathlib import Path

# Create one module-scoped disposable root before importing casino.config.
_TMP = tempfile.TemporaryDirectory(prefix="admin_game_states_")
# Route persistent documents into the disposable root.
os.environ["CASINO_DATA_DIR"] = str(Path(_TMP.name) / "data")
# Route logs into the disposable root as well.
os.environ["CASINO_LOG_DIR"] = str(Path(_TMP.name) / "logs")
# Force JSON storage so no configured MySQL environment can receive test traffic.
os.environ["CASINO_STORAGE_PROVIDER"] = "json"

# Import the resolved game-data root after environment isolation.
from casino.config import GAME_DATA_DIR
# Import the Admin module under test after the provider boundary is fixed.
from casino import admin
# Import auth for current-owner resolution in route tests.
from casino.core import auth
# Import provider controls and the session policy under test.
from casino.core import guest_settings, rate_settings, session_settings, storage
# Import the fixed authorization failure for ordinary Admin denial.
from casino.errors import ForbiddenError


# Group recursive game-state diagnostics coverage.
class AdminGameStatesTests(unittest.TestCase):
    # Prove nested per-player documents and legacy flat state both remain visible.
    def test_nested_and_flat_state_files_are_surfaced(self):
        # Place one nested player document under the canonical game directory.
        nested = GAME_DATA_DIR / "bingo" / "human.json"
        # Create its parent before writing the fixture.
        nested.parent.mkdir(parents=True, exist_ok=True)
        # Persist recognizable nested state.
        nested.write_text(json.dumps({"active_session": {"pattern": "line"}}), encoding="utf-8")
        # Place one legacy flat document beside the nested tree.
        flat = GAME_DATA_DIR / "roulette.json"
        # Ensure the root exists for the flat fixture.
        flat.parent.mkdir(parents=True, exist_ok=True)
        # Persist recognizable flat state.
        flat.write_text(json.dumps({"open_bets": []}), encoding="utf-8")
        # Read the provider-stable Admin aggregation.
        states = admin.game_states()
        # Require the nested file under its unambiguous composite key.
        self.assertIn("bingo/human", states)
        # Require the parsed nested state to survive intact.
        self.assertEqual({"pattern": "line"}, states["bingo/human"]["state"]["active_session"])
        # Require backward-compatible visibility for the flat document.
        self.assertIn("roulette", states)
        # Seeing both layouts proves recursive enumeration without dropping legacy state.
        self.assertGreaterEqual(len(states), 2)

    # Prove a missing game-state root produces the stable empty contract.
    def test_missing_state_directory_returns_empty_mapping(self):
        # Point only the Admin module at a path that has not been created.
        with patch.object(admin, "GAME_DATA_DIR", Path(_TMP.name) / "missing-game-data"):
            # Require the diagnostics contract to return an empty mapping without side effects.
            self.assertEqual({}, admin.game_states())


# Prove the additive session-settings Admin route remains owner-only and provider-backed. (SESSION-009, ADMIN-031)
class AdminSessionSettingsTests(unittest.TestCase):
    # Isolate provider state before every route assertion.
    def setUp(self):
        # Create a fresh JSON provider root for this test.
        self.provider = storage.JsonStorageProvider(Path(_TMP.name) / self._testMethodName)
        # Install the isolated provider through the canonical test seam.
        storage.set_provider_for_tests(self.provider)
        # Define one active bootstrap-managed owner.
        self.owner = {"user_id": "owner-session-settings", "status": "active", "role": "admin", "roles": ["admin", auth.PLATFORM_OWNER_ROLE]}
        # Define one active ordinary Admin without owner authority.
        self.ordinary_admin = {"user_id": "admin-session-settings", "status": "active", "role": "admin", "roles": ["admin"]}

    # Restore provider selection after every route assertion.
    def tearDown(self):
        # Release the isolated provider so other suites choose their own boundary.
        storage.set_provider_for_tests(None)

    # Build the complete listener-free route table only when needed.
    def _router(self):
        # Import lazily so test collection stays dependency-light.
        from casino.app import build_router
        # Return the full application route table.
        return build_router()

    # Prove ordinary Admins cannot read or mutate the global registered-session policy.
    def test_session_settings_routes_require_current_owner(self):
        # Build one listener-free route table.
        router = self._router()
        # Resolve both route attempts to the ordinary current Admin.
        with patch.object(auth, "find_user_by_id", return_value=self.ordinary_admin):
            # Refuse the policy read.
            with self.assertRaises(ForbiddenError):
                # Dispatch the owner-only GET with an ordinary Admin context.
                router.dispatch("GET", "/api/v2/admin/session-settings", {}, context={"user": self.ordinary_admin})
            # Refuse mutation before writing any provider document.
            with self.assertRaises(ForbiddenError):
                # Dispatch the owner-only POST with otherwise valid fields.
                router.dispatch("POST", "/api/v2/admin/session-settings", {"idle_timeout_minutes": 45}, context={"user": self.ordinary_admin})
        # Require denial to leave no stored policy document.
        self.assertEqual(session_settings.DEFAULT_SESSION, self.provider.read_document(session_settings.SESSION_DOCUMENT_KEY, session_settings.DEFAULT_SESSION.copy))

    # Prove owner updates clamp, persist, and read back through the provider document API.
    def test_owner_session_settings_clamp_and_persist(self):
        # Build one listener-free route table.
        router = self._router()
        # Resolve every route to the current owner.
        with patch.object(auth, "find_user_by_id", return_value=self.owner):
            # Apply values outside both reviewed numeric ranges plus an explicit stricter flag.
            saved = router.dispatch("POST", "/api/v2/admin/session-settings", {"idle_timeout_minutes": 0, "absolute_timeout_hours": 99, "admin_idle_timeout_minutes": 5000, "admin_stricter": False}, context={"user": self.owner})
            # Read the stored policy through the owner-only GET.
            loaded = router.dispatch("GET", "/api/v2/admin/session-settings", {}, context={"user": self.owner})
        # Require lower and upper clamps plus the exact boolean setting.
        self.assertEqual((1, 24, 1440, False), (saved["settings"]["idle_timeout_minutes"], saved["settings"]["absolute_timeout_hours"], saved["settings"]["admin_idle_timeout_minutes"], saved["settings"]["admin_stricter"]))
        # Require the route read to equal the exact provider-backed write.
        self.assertEqual(saved, loaded)
        # Reopen the JSON provider to prove restart persistence rather than in-memory caching.
        restarted = storage.JsonStorageProvider(self.provider.data_dir)
        # Require the restarted provider to retain the complete validated document.
        self.assertEqual(saved["settings"], restarted.read_document(session_settings.SESSION_DOCUMENT_KEY, {}))

    # Prove the policy service depends only on the generic provider document interface used by JSON and MySQL.
    def test_session_settings_uses_provider_document_contract(self):
        # Define one minimal in-memory provider double with the shared document API.
        class DocumentProvider:
            # Initialize an empty document registry.
            def __init__(self):
                # Store documents by provider key.
                self.documents = {}

            # Read one document through the shared default factory contract.
            def read_document(self, key, default):
                # Return stored data or a fresh default.
                return dict(self.documents[key]) if key in self.documents else (default() if callable(default) else dict(default))

            # Write one document through the shared provider contract.
            def write_document(self, key, data):
                # Persist an isolated mapping copy.
                self.documents[key] = dict(data)
                # Return the stored mapping as providers do.
                return dict(data)

        # Install the provider-neutral document double.
        provider = DocumentProvider()
        # Route the policy service through the injected provider contract.
        storage.set_provider_for_tests(provider)
        # Persist one partial update.
        saved = session_settings.save_session_settings({"idle_timeout_minutes": 75})
        # Require a later read through the same generic contract to retain the update.
        self.assertEqual((75, saved), (session_settings.session_settings()["idle_timeout_minutes"], provider.documents[session_settings.SESSION_DOCUMENT_KEY]))


# Prove the live application-request policy remains owner-only, bounded, and provider-backed. (SEC-015, ADMIN-032, TEST-156)
class AdminRateLimitSettingsTests(unittest.TestCase):
    # Isolate provider state before every route assertion.
    def setUp(self):
        # Create a fresh JSON provider root for this test.
        self.provider = storage.JsonStorageProvider(Path(_TMP.name) / self._testMethodName)
        # Install the isolated provider through the canonical test seam.
        storage.set_provider_for_tests(self.provider)
        # Define one active bootstrap-managed owner.
        self.owner = {"user_id": "owner-rate-limits", "status": "active", "role": "admin", "roles": ["admin", auth.PLATFORM_OWNER_ROLE]}
        # Define one active ordinary Admin without owner authority.
        self.ordinary_admin = {"user_id": "admin-rate-limits", "status": "active", "role": "admin", "roles": ["admin"]}

    # Restore provider selection after every route assertion.
    def tearDown(self):
        # Release the isolated provider so other suites choose their own boundary.
        storage.set_provider_for_tests(None)

    # Build the complete listener-free route table only when needed.
    def _router(self):
        # Import lazily so test collection stays dependency-light.
        from casino.app import build_router
        # Return the full application route table.
        return build_router()

    # Prove ordinary Admins cannot read or mutate the global application request policy.
    def test_rate_limit_routes_require_current_owner(self):
        # Build one listener-free route table.
        router = self._router()
        # Resolve both route attempts to the ordinary current Admin.
        with patch.object(auth, "find_user_by_id", return_value=self.ordinary_admin):
            # Refuse the policy read.
            with self.assertRaises(ForbiddenError):
                # Dispatch the owner-only GET with an ordinary Admin context.
                router.dispatch("GET", "/api/v2/admin/rate-limits", {}, context={"user": self.ordinary_admin})
            # Refuse mutation before writing any provider document.
            with self.assertRaises(ForbiddenError):
                # Dispatch the owner-only POST with otherwise valid fields.
                router.dispatch("POST", "/api/v2/admin/rate-limits", {"requests_per_window": 900}, context={"user": self.ordinary_admin})
        # Require denial to leave the provider document absent.
        self.assertEqual({}, self.provider.read_document(rate_settings.RATE_LIMIT_DOCUMENT_KEY, {}))

    # Prove owner updates clamp, activate immediately, and survive a provider restart.
    def test_owner_rate_limits_clamp_activate_and_persist(self):
        # Build one listener-free route table.
        router = self._router()
        # Resolve every route to the current owner.
        with patch.object(auth, "find_user_by_id", return_value=self.owner):
            # Apply values outside both reviewed numeric ranges.
            saved = router.dispatch("POST", "/api/v2/admin/rate-limits", {"requests_per_window": 50_000, "window_seconds": 0}, context={"user": self.owner})
            # Read the stored policy through the owner-only GET.
            loaded = router.dispatch("GET", "/api/v2/admin/rate-limits", {}, context={"user": self.owner})
        # Require exact upper and lower clamps.
        self.assertEqual((10_000, 1), (saved["settings"]["requests_per_window"], saved["settings"]["window_seconds"]))
        # Require the live reader and route read to equal the exact committed update.
        self.assertEqual((saved, saved["settings"]), (loaded, rate_settings.rate_limits()))
        # Reopen the JSON provider to prove restart persistence rather than cache-only activation.
        restarted = storage.JsonStorageProvider(self.provider.data_dir)
        # Require the restarted provider to retain the complete validated document.
        self.assertEqual(saved["settings"], restarted.read_document(rate_settings.RATE_LIMIT_DOCUMENT_KEY, {}))


# Prove guest-trial admission is owner-controlled, immediately enforced, and grants 10,000 tokens. (GUEST-001, ADMIN-032, TEST-156)
class AdminGuestTrialSettingsTests(unittest.TestCase):
    # Isolate every provider-backed switch and disposable principal before each case.
    def setUp(self):
        # Create one fresh JSON provider root for policy and guest documents.
        self.provider = storage.JsonStorageProvider(Path(_TMP.name) / self._testMethodName)
        # Install the isolated provider through the canonical storage seam.
        storage.set_provider_for_tests(self.provider)
        # Define one active bootstrap-managed platform owner.
        self.owner = {"user_id": "owner-guest-settings", "status": "active", "role": "admin", "roles": ["admin", auth.PLATFORM_OWNER_ROLE]}
        # Define one active ordinary Admin without owner authority.
        self.ordinary_admin = {"user_id": "admin-guest-settings", "status": "active", "role": "admin", "roles": ["admin"]}

    # Restore provider selection after every guest-policy assertion.
    def tearDown(self):
        # Release the isolated provider so other suites choose their own boundary.
        storage.set_provider_for_tests(None)

    # Build the listener-free route table only after the test provider is installed.
    def _router(self):
        # Import lazily so collection remains dependency-light.
        from casino.app import build_router
        # Return one complete application route table.
        return build_router()

    # Prove an ordinary Admin may inspect but cannot change guest admission.
    def test_guest_trial_settings_write_requires_current_owner(self):
        # Build the listener-free routes.
        router = self._router()
        # Read the policy as an ordinary Admin for a truthful shared Admin screen.
        loaded = router.dispatch("GET", "/api/v2/admin/guest-trials/settings", {}, context={"user": self.ordinary_admin})
        # Require the shipped 10,000-token enabled baseline.
        self.assertEqual((True, 10_000.0), (loaded["settings"]["enabled"], loaded["settings"]["starting_balance"]))
        # Resolve the update attempt against current ordinary-Admin authority.
        with patch.object(auth, "find_user_by_id", return_value=self.ordinary_admin):
            # Refuse mutation before any settings document is written.
            with self.assertRaises(ForbiddenError):
                # Attempt to pause guest creation without owner authority.
                router.dispatch("POST", "/api/v2/admin/guest-trials/settings", {"enabled": False}, context={"user": self.ordinary_admin})
        # Require the denied update to leave no provider document.
        self.assertEqual({}, self.provider.read_document(guest_settings.GUEST_SETTINGS_DOCUMENT_KEY, {}))

    # Prove the owner switch applies without restart and never revokes an already-created trial.
    def test_owner_can_pause_and_resume_new_guest_trials(self):
        # Build the listener-free routes.
        router = self._router()
        # Create one trial under the enabled default before changing admission.
        existing = auth.create_guest("guest-policy-existing", True, auth.GUEST_TERMS_VERSION, "en-US", "desktop")
        # Require the exact fixed 10,000-token grant.
        self.assertEqual(10_000.0, auth.current_user_payload(existing["session"], existing["user"])["player"]["token_balance"])
        # Resolve each settings mutation to the current owner.
        with patch.object(auth, "find_user_by_id", return_value=self.owner):
            # Pause only creation of new trials.
            paused = router.dispatch("POST", "/api/v2/admin/guest-trials/settings", {"enabled": False}, context={"user": self.owner})
            # Require a new direct service request to fail under the saved policy.
            with self.assertRaises(ForbiddenError):
                # Attempt a new trial after the owner pause.
                auth.create_guest("guest-policy-paused", True, auth.GUEST_TERMS_VERSION, "en-US", "desktop")
            # Resume new guest creation without restarting the process.
            resumed = router.dispatch("POST", "/api/v2/admin/guest-trials/settings", {"enabled": True}, context={"user": self.owner})
        # Prove the existing trial still authenticates while admission is paused and after it resumes.
        authenticated = auth.authenticate_token(existing["session"]["token"], existing["browser_nonce"])
        # Require exact pause/resume responses and the original principal identity.
        self.assertEqual((False, True, existing["user"]["user_id"]), (paused["settings"]["enabled"], resumed["settings"]["enabled"], authenticated[1]["user_id"]))
        # End the disposable fixture without leaving active trial state.
        auth.end_guest_trial(existing["user"], "revoked")
        # Reopen the provider to prove the final enabled state survives restart.
        restarted = storage.JsonStorageProvider(self.provider.data_dir)
        # Require the exact canonical stored switch.
        self.assertEqual(True, restarted.read_document(guest_settings.GUEST_SETTINGS_DOCUMENT_KEY, {})["enabled"])


# Run the focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
