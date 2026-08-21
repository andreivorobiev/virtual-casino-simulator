# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused listener-free tests for privacy-safe Admin session control."""

# Import a bounded worker pool for idempotent concurrent revocation proof.
from concurrent.futures import ThreadPoolExecutor
# Import JSON so unchanged malformed evidence can be compared structurally.
import json
# Import temporary storage roots so no live identity or session data is touched.
import tempfile
# Import unittest for focused central-runner integration.
import unittest
# Import portable paths for isolated JSON provider documents.
from pathlib import Path
# Import patching so only auth document paths change during each test.
from unittest.mock import patch

# Import the canonical auth identity and session service under test.
from casino.core import auth
# Import direct JSON readers and writers for isolated test fixtures.
from casino.core.state_store import read_json, write_json
# Import the bounded public validation error used by malformed requests.
from casino.errors import ConflictError, ValidationError


# Prove the server-side session-control core is safe, atomic, and account-scoped. (SESSION-008, TEST-143)
class AdminSessionControlTests(unittest.TestCase):
    # Allocate isolated identity and session documents for every test.
    def setUp(self) -> None:
        # Create a disposable root outside the configured application data directory.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-admin-sessions-")
        # Derive the isolated canonical user document.
        self.users_path = Path(self.temporary.name) / "users.json"
        # Derive the isolated canonical session document.
        self.sessions_path = Path(self.temporary.name) / "sessions.json"
        # Redirect only the auth module's user and session paths.
        self.path_patches = [
            # Patch the user document reference for this test process.
            patch.object(auth, "USERS_PATH", self.users_path),
            # Patch the session document reference for this test process.
            patch.object(auth, "SESSIONS_PATH", self.sessions_path),
        ]
        # Activate both document-path patches before seeding fixtures.
        for path_patch in self.path_patches:
            # Start this exact patch and retain it for symmetric teardown.
            path_patch.start()
        # Seed one retained full account that Admin session control may target.
        self.user = self._user("user_account", "account@example.test", "local")
        # Seed a second retained account to prove cross-account isolation.
        self.other_user = self._user("user_other", "other@example.test", "local")
        # Seed one disposable guest identity that must remain outside this Admin area.
        self.guest_user = self._user("user_guest", "guest@example.invalid", "guest", roles=["guest"])
        # Persist the complete isolated user document.
        auth.save_users({"schema_version": 1, "users": [self.user, self.other_user, self.guest_user], "reservations": []})
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

    # Build one minimal canonical identity fixture without creating a wallet.
    def _user(self, user_id: str, email: str, provider: str, roles: list[str] | None = None) -> dict:
        # Return the retained identity shape used by auth target validation.
        return {
            # Persist the canonical user identifier.
            "user_id": user_id,
            # Persist a unique synthetic mailbox.
            "email": email,
            # Persist the identity-provider class used to distinguish guests.
            "identity_provider": provider,
            # Persist the requested role collection or an ordinary player role.
            "roles": list(roles or ["player"]),
            # Preserve the compatible singular role field.
            "role": (roles or ["player"])[0],
            # Keep every fixture active for target-class testing.
            "status": "active",
        }

    # Build one complete secret-bearing durable session fixture.
    def _session(self, session_id: str, user_id: str, *, status: str = "active", updated_at: str = "2026-07-27T18:00:00.000Z", client: str = "Mozilla/5.0 Windows", auth_method: str = "local") -> dict:
        # Return the full stored record whose secrets must never enter Admin results.
        return {
            # Persist the internal session identifier used only to derive an alias.
            "session_id": session_id,
            # Persist the exact owning identity.
            "user_id": user_id,
            # Persist synthetic bearer material to prove it is excluded.
            "token": f"bearer-secret-{session_id}",
            # Persist synthetic CSRF material to prove it is excluded.
            "csrf_token": f"csrf-secret-{session_id}".ljust(32, "x"),
            # Persist the explicit native generation used by first-class providers.
            "generation": 1,
            # Persist the reviewed lifecycle state.
            "status": status,
            # Persist a fixed creation timestamp.
            "created_at": "2026-07-27T17:00:00.000Z",
            # Persist the caller-selected activity timestamp.
            "updated_at": updated_at,
            # Persist a fixed bounded expiry timestamp.
            "expires_at": "2026-07-28T17:00:00.000Z",
            # Persist raw client detail that must be coarsened.
            "client": client,
            # Persist the authentication method class.
            "auth_method": auth_method,
        }

    # Persist the supplied session rows as one canonical document.
    def _save_sessions(self, rows: list[dict]) -> None:
        # Write through the production helper so schema behavior stays representative.
        auth.save_sessions({"schema_version": 1, "sessions": rows})

    # Prove inventory is bounded, ordered, account-scoped, and secret-safe.
    def test_inventory_returns_only_approved_coarse_fields(self) -> None:
        # Seed an older desktop session for the target account.
        older = self._session("session-older", self.user["user_id"], updated_at="2026-07-27T18:00:00.000Z")
        # Seed a newer mobile provider session for the target account.
        newer = self._session("session-newer", self.user["user_id"], updated_at="2026-07-27T19:00:00.000Z", client="Mozilla/5.0 iPhone Mobile", auth_method="google")
        # Seed an unrelated session whose content must not appear.
        unrelated = self._session("session-other", self.other_user["user_id"], client="10.20.30.40")
        # Persist all three records in deliberately non-result order.
        self._save_sessions([older, unrelated, newer])
        # Request only the newest target-account row to prove the bound.
        inventory = auth.list_admin_sessions_for_user(self.user["user_id"], limit=1)
        # Require newest-first bounded selection.
        self.assertEqual(len(inventory), 1)
        # Require only the approved exact result keys.
        self.assertEqual(set(inventory[0]), {"session_alias", "created_at", "last_activity_at", "expires_at", "status", "auth_method", "client_family"})
        # Require fixed reviewed classes and the latest timestamp.
        self.assertEqual((inventory[0]["last_activity_at"], inventory[0]["auth_method"], inventory[0]["client_family"]), ("2026-07-27T19:00:00.000Z", "google", "mobile"))
        # Require the stable one-way alias shape.
        self.assertRegex(inventory[0]["session_alias"], r"^[0-9a-f]{16}$")
        # Serialize the result so every forbidden raw value can be checked together.
        rendered = json.dumps(inventory, sort_keys=True)
        # Require no raw internal identifiers, account identifiers, tokens, CSRF values, clients, or unrelated data.
        for forbidden in ("session-newer", self.user["user_id"], "bearer-secret", "csrf-secret", "iPhone", self.other_user["user_id"], "10.20.30.40"):
            # Assert each sensitive value is absent from the complete public projection.
            self.assertNotIn(forbidden, rendered)

    # Prove targeted and all-session revocation are exact, isolated, and idempotent.
    def test_targeted_and_all_revocation_are_idempotent(self) -> None:
        # Seed two target sessions and one unrelated session.
        first = self._session("session-first", self.user["user_id"])
        # Seed the second target session independently.
        second = self._session("session-second", self.user["user_id"])
        # Seed an unrelated active session that must survive.
        unrelated = self._session("session-unrelated", self.other_user["user_id"])
        # Persist the complete fixture.
        self._save_sessions([first, second, unrelated])
        # Derive the first session's one-way Admin lookup alias.
        first_alias = auth.admin_session_alias(first["session_id"])
        # Revoke the selected active session exactly once.
        self.assertEqual(auth.revoke_admin_session_for_user(self.user["user_id"], first_alias), 1)
        # Prove a retry is a no-op.
        self.assertEqual(auth.revoke_admin_session_for_user(self.user["user_id"], first_alias), 0)
        # Revoke the one remaining active target session.
        self.assertEqual(auth.revoke_all_admin_sessions_for_user(self.user["user_id"]), 1)
        # Prove the all-session retry is also a no-op.
        self.assertEqual(auth.revoke_all_admin_sessions_for_user(self.user["user_id"]), 0)
        # Resolve final state by internal identifier for exact isolation assertions.
        by_id = {session["session_id"]: session for session in auth.load_sessions()["sessions"]}
        # Require both target sessions revoked while the unrelated session remains active.
        self.assertEqual((by_id["session-first"]["status"], by_id["session-second"]["status"], by_id["session-unrelated"]["status"]), ("revoked", "revoked", "active"))

    # Prove concurrent retries commit only one active-to-revoked transition.
    def test_concurrent_targeted_revocation_commits_once(self) -> None:
        # Seed one target session shared by all contenders.
        target = self._session("session-concurrent", self.user["user_id"])
        # Persist the single active target.
        self._save_sessions([target])
        # Derive the target alias once outside worker threads.
        alias = auth.admin_session_alias(target["session_id"])
        # Define one identical idempotent revocation request.
        def revoke_once(_: int) -> int:
            # Return the exact committed-transition count.
            return auth.revoke_admin_session_for_user(self.user["user_id"], alias)
        # Execute four concurrent retries against the production atomic file updater.
        with ThreadPoolExecutor(max_workers=4) as pool:
            # Materialize every bounded result before closing the pool.
            outcomes = list(pool.map(revoke_once, range(4)))
        # Require exactly one committed transition across all retries.
        self.assertEqual(sum(outcomes), 1)
        # Require the target to be durably revoked.
        self.assertEqual(auth.load_sessions()["sessions"][0]["status"], "revoked")

    # Prove guests and missing identities stay outside retained-account session control.
    def test_guest_and_missing_targets_are_rejected(self) -> None:
        # Attempt to list sessions for the disposable guest principal.
        with self.assertRaisesRegex(ValidationError, "Persistent account is required"):
            # Keep guest-trial analytics separated from full account controls.
            auth.list_admin_sessions_for_user(self.guest_user["user_id"])
        # Attempt to revoke sessions for an unknown identity through the same response.
        with self.assertRaisesRegex(ValidationError, "Persistent account is required"):
            # Prevent identity enumeration through mutation differences.
            auth.revoke_all_admin_sessions_for_user("user_missing")

    # Prove malformed session evidence fails closed without any repair write.
    def test_malformed_session_document_is_preserved(self) -> None:
        # Resolve the active isolated JSON provider after the empty first-class seed.
        provider = auth._session_store()
        # Build one canonical credential-derived path for a malformed per-session row.
        row_path = provider._session_row_path("0" * 64)
        # Persist a structurally valid JSON object missing its required owner.
        malformed = {"session_id": "missing-owner", "token_digest": "0" * 64, "status": "active"}
        # Write the exact malformed first-class row directly for corruption evidence.
        row_path.write_text(json.dumps(malformed, sort_keys=True), encoding="utf-8")
        # Snapshot the exact source bytes before the failed mutation.
        before = row_path.read_bytes()
        # Attempt the all-session mutation that must validate every row first.
        with self.assertRaisesRegex(ConflictError, "operator recovery"):
            # Fail before changing or rewriting any row.
            auth.revoke_all_admin_sessions_for_user(self.user["user_id"])
        # Require the complete stored row to remain byte-for-byte unchanged.
        self.assertEqual(row_path.read_bytes(), before)
        # Require read-only inventory to fail through the same recovery boundary.
        with self.assertRaisesRegex(ConflictError, "operator recovery"):
            # Avoid returning a partial inventory from the valid prefix.
            auth.list_admin_sessions_for_user(self.user["user_id"])

    # Prove syntactically invalid JSON remains byte-exact across every session-control operation.
    def test_invalid_json_bytes_fail_closed_without_normalization(self) -> None:
        # Build one truncated JSON document that cannot be decoded.
        invalid_bytes = b'{"schema_version":1,"sessions":['
        # Resolve the isolated provider and one canonical per-session path.
        provider = auth._session_store()
        # Derive the exact keyed row path for the synthetic digest.
        row_path = provider._session_row_path("1" * 64)
        # Persist the exact invalid bytes without invoking a normalizing helper.
        row_path.write_bytes(invalid_bytes)
        # Attempt read-only inventory against the corrupt first-class row.
        with self.assertRaisesRegex(ConflictError, "Session storage requires operator recovery"):
            # Require inventory to fail instead of appearing empty.
            auth.list_admin_sessions_for_user(self.user["user_id"])
        # Require inventory to preserve every original byte.
        self.assertEqual(row_path.read_bytes(), invalid_bytes)
        # Derive one valid alias so targeted mutation reaches strict storage decoding.
        alias = auth.admin_session_alias("session-invalid-json")
        # Attempt targeted revocation against the corrupt document.
        with self.assertRaisesRegex(ConflictError, "Session storage requires operator recovery"):
            # Require targeted mutation to fail before normalization or rewrite.
            auth.revoke_admin_session_for_user(self.user["user_id"], alias)
        # Require targeted mutation to preserve every original byte.
        self.assertEqual(row_path.read_bytes(), invalid_bytes)
        # Attempt all-session revocation against the same corrupt document.
        with self.assertRaisesRegex(ConflictError, "Session storage requires operator recovery"):
            # Require all-session mutation to fail before normalization or rewrite.
            auth.revoke_all_admin_sessions_for_user(self.user["user_id"])
        # Require all-session mutation to preserve every original byte.
        self.assertEqual(row_path.read_bytes(), invalid_bytes)
        # Require the permissive reader's corrupt-backup side effect never to run.
        self.assertEqual(list(row_path.parent.glob("*.corrupt-*")), [])

    # Prove malformed request parameters cannot rewrite session state.
    def test_invalid_alias_and_limit_leave_state_unchanged(self) -> None:
        # Seed one valid active target session.
        self._save_sessions([self._session("session-request-validation", self.user["user_id"])])
        # Snapshot the complete document before request validation.
        before = read_json(self.sessions_path, {})
        # Reject a raw internal identifier in place of a one-way alias.
        with self.assertRaisesRegex(ValidationError, "Session alias is invalid"):
            # Attempt targeted revocation with a forbidden raw value.
            auth.revoke_admin_session_for_user(self.user["user_id"], "session-request-validation")
        # Reject a boolean limit even though bool subclasses int.
        with self.assertRaisesRegex(ValidationError, "Session result limit is invalid"):
            # Attempt an ambiguous unbounded-style inventory request.
            auth.list_admin_sessions_for_user(self.user["user_id"], limit=True)
        # Require neither failed request to mutate the provider document.
        self.assertEqual(read_json(self.sessions_path, {}), before)
