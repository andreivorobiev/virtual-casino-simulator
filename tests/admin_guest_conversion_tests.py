# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Admin-assisted Guest Trial conversion evidence. (#701, ADMIN-035, TEST-193)"""

# Import environment access so local and hosted runs share the configured Node runtime.
import os
# Import a child-process boundary for exact ES-module syntax validation.
import subprocess
# Import temporary-directory support for isolated provider-backed identities and wallets.
import tempfile
# Import the standard unittest framework used by governed listener-free API suites.
import unittest
# Import filesystem paths for the isolated JSON provider root.
from pathlib import Path
# Import patching so audit assertions never write shared application-log bytes.
from unittest.mock import patch

# Import the Admin module so the exact audit facade and route are exercised.
from casino import admin
# Import canonical auth, conversion, ledger, and player boundaries under test.
from casino.core import auth, guest_analytics, guest_conversion, ledger, players, storage
# Import the provider-aware atomic document mutation used only for expiry setup.
from casino.core.state_store import update_json, write_json
# Import bounded application failures for exact refusal assertions.
from casino.errors import ForbiddenError, ValidationError


# Prove an Admin can explicitly and idempotently convert only an active guest.
class AdminGuestConversionTests(unittest.TestCase):
    # Install one independent provider and seed canonical actors before each case.
    def setUp(self) -> None:
        # Create a task-owned provider directory that disappears after this case.
        self.temp = tempfile.TemporaryDirectory()
        # Route every identity, session, wallet, and ledger operation through the isolated provider.
        self.provider = storage.JsonStorageProvider(Path(self.temp.name))
        # Install the provider before importing the complete listener-free application router.
        storage.set_provider_for_tests(self.provider)
        # Restore the canonical identity document so process-local path constants cannot retain a prior fixture.
        write_json(auth.USERS_PATH, auth.default_users())
        # Restore the bounded creation window so every case can seed its one guest independently.
        write_json(auth.GUEST_CREATION_LOG_PATH, auth.default_guest_creation_log())
        # Create a durable ordinary Admin accepted by the central and route-level role boundary.
        self.admin = auth.create_user("support-admin@example.test", "SupportAdminPassw0rd!23", "Support Admin", role="admin")
        # Create one active guest with a de-identified analytics identity visible on Guest Trials.
        self.guest = auth.create_guest("admin-conversion-test", True, auth.GUEST_TERMS_VERSION, "en-US", "desktop")["user"]
        # Build the real route table only after provider selection is stable.
        from casino.app import build_router
        # Retain the complete router for direct standard-envelope service assertions.
        self.router = build_router()

    # Release every provider and temporary path after each case.
    def tearDown(self) -> None:
        # Restore normal provider resolution before deleting task-owned bytes.
        storage.set_provider_for_tests(None)
        # Remove the isolated test root.
        self.temp.cleanup()

    # Build one exact valid additive-v2 conversion request.
    def _request(self, **overrides) -> dict:
        # Start with the visible analytics identity and complete target account content.
        request = {"guest_identity": self.guest["guest_analytics_id"], "email": "assisted@example.test", "password": "AssistedPassw0rd!23", "display_name": "Assisted Player", "terms_version": "private-beta-1", "accepted": True, "confirm": True, "idempotency_key": "admin-assisted-conversion-key"}
        # Apply only the test-specific changed values.
        request.update(overrides)
        # Return the complete request.
        return request

    # Dispatch the real Admin route with the durable Admin actor.
    def _convert(self, request: dict | None = None, actor: dict | None = None) -> dict:
        # Submit through the exact listener-free route and current request context.
        return self.router.dispatch("POST", "/api/v2/admin/guest-trials/convert", request or self._request(), context={"user": actor or self.admin})

    # Prove conversion preserves the wallet, player, ledger, result shape, and actor audit.
    def test_admin_conversion_preserves_wallet_and_audits_actor_target_time(self) -> None:
        # Make the guest wallet and ledger history distinguishable from defaults.
        ledger.debit(self.guest["player_id"], 250, "GUEST_PLAY", game="roulette")
        # Capture the authoritative pre-conversion wallet and ledger rows.
        balance_before = players.get_player(self.guest["player_id"])["balance"]
        # Preserve exact ledger identity because conversion itself must not move tokens.
        ledger_before = ledger.read_recent(self.guest["player_id"], 100)
        # Capture all conversion audit calls without writing shared log files.
        with patch.object(guest_conversion.logger, "info", return_value={}) as audit:
            # Execute the explicitly confirmed Admin route.
            result = self._convert()
        # Require the exact self-service result shape and preserved balance.
        self.assertEqual((set(result), result["status"], result["player_preserved"], result["balance"]), ({"status", "replayed", "email", "display_name", "balance", "player_preserved"}, "converted", True, balance_before))
        # Resolve the durable account by its normalized mailbox.
        account = auth.find_user_by_email("assisted@example.test")
        # Require the account to adopt the exact guest player without a second wallet owner.
        self.assertEqual(account["player_id"], self.guest["player_id"])
        # Require conversion to append no debit, credit, refund, or invented ledger movement.
        self.assertEqual(ledger_before, ledger.read_recent(self.guest["player_id"], 100))
        # Require the de-identified Admin row to become terminal instead of offering conversion again.
        self.assertEqual(guest_analytics.detail(self.guest["guest_analytics_id"])["end_reason"], "converted")
        # Select the Admin-specific audit event from the shared conversion audit calls.
        assisted = next(call for call in audit.call_args_list if call.args[0] == "admin_guest_conversion_completed")
        # Require exact actor, guest, account, player, replay, assistance, and timestamp evidence.
        self.assertEqual((assisted.kwargs["actor_user_id"], assisted.kwargs["target_guest_user_id"], assisted.kwargs["target_user_id"], assisted.kwargs["target_player_id"], assisted.kwargs["replayed"], assisted.kwargs["assisted"]), (self.admin["user_id"], self.guest["user_id"], account["user_id"], self.guest["player_id"], False, True))
        # Require a canonical audit instant without accepting a caller-provided timestamp.
        self.assertRegex(assisted.kwargs["at"], r"^\d{4}-\d{2}-\d{2}T")

    # Prove an exact retry replays one account and one wallet owner.
    def test_admin_conversion_is_idempotent(self) -> None:
        # Complete the first Admin-assisted conversion.
        first = self._convert()
        # Replay the exact same operation against the same analytics identity.
        second = self._convert()
        # Require the replay marker and stable result content.
        self.assertEqual((first["email"], second["email"], second["replayed"]), ("assisted@example.test", "assisted@example.test", True))
        # Count only full accounts attached to the preserved player.
        owners = [user for user in auth.load_users().get("users", []) if user.get("player_id") == self.guest["player_id"] and not auth.is_guest(user)]
        # Require one durable account owner after both requests.
        self.assertEqual(len(owners), 1)

    # Prove confirmation, actor authority, and exact request shape fail before mutation.
    def test_confirmation_authority_and_shape_fail_closed(self) -> None:
        # Reject missing explicit confirmation through the standard validation result.
        with self.assertRaisesRegex(ValidationError, "explicit confirmation"):
            # Submit the otherwise valid request with literal false confirmation.
            self._convert(self._request(confirm=False))
        # Create one ordinary account that has no Admin authority.
        player = auth.create_user("ordinary@example.test", "OrdinaryPassw0rd!23", "Ordinary Player")
        # Reject a current non-Admin before resolving the guest identity.
        with self.assertRaises(ForbiddenError):
            # Submit the exact request with the ordinary actor.
            self._convert(actor=player)
        # Add one unsupported request field to exercise the exact runtime allowlist.
        hostile = self._request(extra_player_id="other")
        # Reject contract drift before any account side effect.
        with self.assertRaisesRegex(ValidationError, "request fields"):
            # Submit the unsupported field through the route.
            self._convert(hostile)
        # Require the guest to remain active and the target mailbox to remain unused.
        self.assertEqual((auth.find_user_by_id(self.guest["user_id"])["status"], auth.find_user_by_email("assisted@example.test")), ("active", None))

    # Prove non-guests and expired guest trials are never converted by support.
    def test_non_guest_and_expired_trial_are_refused(self) -> None:
        # Address the current Admin as though it were a guest identity.
        with self.assertRaises(ValidationError) as non_guest:
            # Submit otherwise valid account content for a non-guest target.
            self._convert(self._request(guest_identity=self.admin["user_id"]))
        # Require the same not-a-guest reason used by self-service conversion.
        self.assertEqual(non_guest.exception.details.get("reason"), "not_a_guest")
        # Mark only the seeded guest expired through the provider-aware identity transaction.
        def expire(state: dict) -> dict:
            # Find the exact disposable identity under the document lock.
            for user in state.get("users", []):
                # Match the seeded guest.
                if user.get("user_id") == self.guest["user_id"]:
                    # Publish the terminal expiry state.
                    user["status"] = "expired"
            # Return the complete identity document.
            return state
        # Commit the expiry before attempting Admin conversion.
        update_json(auth.USERS_PATH, expire, auth.default_users)
        # Reject the expired trial before any target account creation.
        with self.assertRaises(ValidationError) as expired:
            # Submit the exact valid request for the expired analytics identity.
            self._convert()
        # Require the shared inactive-guest reason and no account creation.
        self.assertEqual((expired.exception.details.get("reason"), auth.find_user_by_email("assisted@example.test")), ("guest_inactive", None))

    # Prove the browser-owned Admin entrypoint parses under ES-module grammar. (TEST-193)
    def test_admin_frontend_parses_as_an_es_module(self) -> None:
        # Resolve the tracked Admin source from the repository root rather than a process working-directory assumption.
        admin_source = (Path(__file__).resolve().parents[1] / "web" / "admin.js").read_text(encoding="utf-8")
        # Reuse the governed bundled runtime locally while retaining the ordinary hosted Node command.
        node_binary = os.environ.get("CASINO_NODE_BINARY", "node")
        # Parse stdin explicitly as a module because CommonJS-only --check can miss module-specific entrypoint failures.
        result = subprocess.run([node_binary, "--input-type=module", "--check"], input=admin_source, text=True, encoding="utf-8", capture_output=True, timeout=30, check=False)
        # Fail with the bounded parser diagnostic when any malformed try/catch or module syntax reaches the shipped Admin shell.
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-1600:])


# Execute the focused suite directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
