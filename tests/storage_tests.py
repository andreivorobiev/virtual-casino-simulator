#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import required dependency so tests can inspect provider implementation details.
import inspect
# Import required dependency so thread and process ledger calls can overlap safely.
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
# Import JSON so live aggregate pool measurements are emitted without connector or identity detail.
import json
# Import environment access so live provider routing can be scoped and restored safely.
import os
# Import regular expressions to extract synthetic bearers from fake provider mail only.
import re
# Import required dependency so test data can be written outside the real data directory.
import tempfile
# Import required dependency so isolated JSON provider paths are platform-safe.
from pathlib import Path
# Import monotonic timing for disposable MySQL 1/2/4/8 aggregate measurements.
import time
# Import bounded patching for strict filesystem-failure normalization proof.
from unittest import mock

# Import required dependency so storage tests can resolve repository files.
ROOT = Path(__file__).resolve().parents[1]
# Use synthetic keyed-digest material unrelated to MySQL credentials for live token evidence.
MYSQL_TOKEN_TEST_KEY = "synthetic-mysql-token-digest-key-material-2026"
# Use independent synthetic mail digest material for cross-process provider evidence.
MYSQL_MAIL_TEST_KEY = "synthetic-mysql-mail-digest-key-material-2026"
# Use one reserved-domain mailbox only inside the disposable MySQL integration database.
MYSQL_INVITATION_RECIPIENT = "mysql-invitation@example.invalid"
# Use one policy-compliant synthetic password only inside the disposable integration database.
MYSQL_INVITATION_PASSWORD = "Synthetic-MySQL-Invite-2026!"
# Use independent synthetic OAuth digest material for cross-process flow, link, and rate evidence.
MYSQL_OAUTH_TEST_KEY = "synthetic-mysql-oauth-digest-key-material-2026"
# Use one synthetic canonical user identifier for disposable MySQL feedback concurrency.
MYSQL_FEEDBACK_USER_ID = "user_mysql_feedback"


# Execute one JSON action call in a separately spawned process.
def _json_action_worker(args):
    # Import storage inside the child process so Windows spawn reconstructs clean module state.
    from casino.core import storage

    # Unpack the serializable action packet passed by the parent test.
    data_root, family, amount, action_key = args
    # Build an independent provider instance pointed at the shared isolated store.
    provider = storage.JsonStorageProvider(Path(data_root))
    # Execute the same action identity through a distinct operating-system process.
    event, replayed = provider.transact_ledger_once("human", amount, f"TEST_{family.upper()}", action_key, "storage", f"round_{family}", {"family": family})
    # Return only serializable proof fields to the parent process.
    return event["ledger_id"], replayed


# Insert one player from an independent process through the public creation service.
def _json_player_create_worker(args):
    # Import player and storage services inside the spawned process.
    from casino.core import players, storage

    # Unpack the isolated data root and deterministic display suffix.
    data_root, suffix = args
    # Route every public player call into the shared isolated JSON store.
    storage.set_provider_for_tests(storage.JsonStorageProvider(Path(data_root)))
    # Start protected work so process-local injection is always released.
    try:
        # Create one independently identified player through the production row-scoped seam.
        created = players.create_player(f"Process Player {suffix}", "guest", 200.0)
        # Return only the durable identifier needed by the parent assertion.
        return created["player_id"]
    # Always clear the process-local provider before the worker exits.
    finally:
        # Restore ordinary provider selection for process teardown.
        storage.set_provider_for_tests(None)


# Bootstrap overlapping player rows from an independent process.
def _json_player_bootstrap_worker(args):
    # Import storage inside the spawned process so no provider state is inherited.
    from casino.core import storage

    # Unpack the shared root and unique row suffix.
    data_root, suffix = args
    # Build one independent provider instance against the shared store.
    provider = storage.JsonStorageProvider(Path(data_root))
    # Submit one shared row and one process-owned row through one batch boundary.
    provider.bootstrap_players({"players": [{"player_id": "bootstrap_process_shared", "display_name": "Shared Process", "type": "guest", "balance": 110.0}, {"player_id": f"bootstrap_process_{suffix}", "display_name": f"Process {suffix}", "type": "guest", "balance": 111.0}]})
    # Return the unique identifier so completion is explicit and serializable.
    return f"bootstrap_process_{suffix}"


# Execute one managed practice-opponent action in a separately spawned process.
def _practice_opponent_worker(args):
    # Import services inside the child process so Windows spawn uses clean module state.
    from casino.bots import practice_opponents
    # Import storage helpers for isolated provider injection in this process.
    from casino.core import storage

    # Unpack the serializable packet shared by all duplicate callers.
    data_root, player_id, action_key = args
    # Point this child exclusively at the temporary shared JSON store.
    storage.set_provider_for_tests(storage.JsonStorageProvider(Path(data_root)))
    # Start protected logic so provider injection is always released.
    try:
        # Execute the same controller debit through the production public seam.
        result = practice_opponents.transact(player_id, 25, "PRACTICE_OPPONENT_ESCROW_DEBIT", action_key, "practice-cross-process", "debit", "reserve_stack", session_owner_id="human-cross-process", component="escrow")
        # Return immutable proof fields to the parent process.
        return result["event"]["ledger_id"], result["replayed"]
    # Always clear process-local provider injection before exit.
    finally:
        # Restore normal provider selection for any later child work.
        storage.set_provider_for_tests(None)


# Execute one MySQL action call in a separately spawned process.
def _mysql_action_worker(index):
    # Import storage inside the child process so each call opens independent connections.
    from casino.core import storage

    # Build an independent provider from inherited secret-safe environment configuration.
    provider = storage.MySQLStorageProvider()
    # Execute one of 25 duplicate calls against the same durable action identity.
    event, replayed = provider.transact_ledger_once("human", -3, "MYSQL_IDEMPOTENT_DEBIT", "mysql-action-debit", "storage", "mysql_action_round", {"family": "debit"})
    # Return proof fields plus the caller index for process-result materialization.
    return index, event["ledger_id"], replayed


# Execute one live MySQL token consume from an independent spawned process. (OTT-001)
def _mysql_token_consume_worker(arguments):
    # Import the inert token service inside the child process.
    from casino.core import one_time_tokens
    # Import storage provider injection so this child ignores the workflow's JSON default.
    from casino.core import storage
    # Import the configured data root so state_store derives the canonical MySQL document key.
    from casino.config import DATA_DIR
    # Import the generic validation envelope used by losing race participants.
    from casino.errors import ValidationError

    # Unpack the synthetic race packet without printing any ephemeral value.
    index, token, subject = arguments
    # Preserve the inherited workflow selector so this child restores it before exit.
    previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
    # Route state_store through the independent MySQL provider for this bounded worker.
    os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
    # Inject an independent MySQL provider because process-local test injection is not inherited.
    storage.set_provider_for_tests(storage.MySQLStorageProvider())
    # Start protected consumption so provider injection is always released.
    try:
        # Build an independent provider-routed service over the canonical auth document.
        service = one_time_tokens.TokenService(
            # Use the normal data-root path so state_store derives the MySQL document key.
            store_path=DATA_DIR / "auth" / "one_time_tokens.json",
            # Use the synthetic test-only keyed digest material.
            digest_key=MYSQL_TOKEN_TEST_KEY,
            # Suppress application log output from bounded race participants.
            audit_sink=lambda level, event, fields: None,
        )
        # Start protected consumption so expected race losers return stable evidence.
        try:
            # Attempt the exact same purpose, bearer, and subject from this process.
            result = service.consume("password_reset", token, subject=subject)
            # Return the caller index, winner flag, and opaque record identifier.
            return index, True, result["token_id"]
        # Convert the generic losing result into serializable evidence.
        except ValidationError as error:
            # Require every loser to receive only the generic public reason.
            assert error.details == one_time_tokens.INVALID_TOKEN_DETAILS
            # Return no identifier for a rejected replay or race loser.
            return index, False, None
    # Always clear process-local provider injection before the worker exits.
    finally:
        # Restore normal provider selection in this spawned process.
        storage.set_provider_for_tests(None)
        # Restore an inherited selector exactly when one existed.
        if previous_provider_name is not None:
            # Replace the bounded MySQL selector with the inherited value.
            os.environ["CASINO_STORAGE_PROVIDER"] = previous_provider_name
        # Remove the temporary selector when the parent process had none.
        else:
            # Delete only the worker-owned environment entry.
            os.environ.pop("CASINO_STORAGE_PROVIDER", None)


# Record a single in-process fake provider call without external network access.
class _MySQLMailTransport:
    # Initialize the bounded call counter.
    def __init__(self):
        # Start with no observed provider attempts.
        self.calls = 0
        # Retain synthetic reserved-domain messages only inside the disposable test process.
        self.messages = []

    # Accept one transient message without retaining any sensitive field.
    def send(self, message):
        # Count the invocation while deliberately discarding the payload.
        self.calls += 1
        # Store a detached copy for provider-path bearer verification without logging it.
        self.messages.append(dict(message))


# Model one abrupt worker loss during disposable MySQL enrollment recovery.
class _MySQLEnrollmentCrash(BaseException):
    # Carry no provider, recipient, or bearer detail.
    pass


# Submit the same transactional-mail request from one independent MySQL process. (MAIL-004)
def _mysql_mail_submit_worker(index):
    # Import the mail service only inside the spawned process.
    from casino.core import mail
    # Import provider injection so this worker owns one independent connection pool.
    from casino.core import storage
    # Import the configured data root used for the canonical provider document key.
    from casino.config import DATA_DIR

    # Preserve the inherited provider selector around this bounded proof.
    previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
    # Route the state-store mutation through MySQL for this worker.
    os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
    # Inject a newly constructed provider that shares only the disposable integration database.
    storage.set_provider_for_tests(storage.MySQLStorageProvider())
    # Allocate one process-local fake transport so the parent can sum actual invocations.
    transport = _MySQLMailTransport()
    # Start protected submission so provider injection is always released.
    try:
        # Build one fully ready service using only synthetic reserved-domain values.
        service = mail.MailService(state_path=DATA_DIR / "mail" / "deliveries.json", enabled=True, network_enabled=True, provider="postmark", digest_key=MYSQL_MAIL_TEST_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=transport)
        # Submit the exact same caller request through every process.
        receipt = service.submit("password_reset", "mysql-mail@example.invalid", token="synthetic-mysql-mail-bearer", idempotency_key="mysql-mail-shared-idempotency")
        # Return only caller index, local call count, opaque delivery id, and safe status.
        return index, transport.calls, receipt["delivery_id"], receipt["status"]
    # Always release process-local provider state and restore the inherited selector.
    finally:
        # Clear the injected provider before the spawned worker exits.
        storage.set_provider_for_tests(None)
        # Restore an inherited provider selection exactly when one existed.
        if previous_provider_name is not None:
            # Replace the bounded test selector with its original value.
            os.environ["CASINO_STORAGE_PROVIDER"] = previous_provider_name
        # Remove only the worker-owned selector when none was inherited.
        else:
            # Delete the temporary MySQL selector.
            os.environ.pop("CASINO_STORAGE_PROVIDER", None)


# Report fixed ready mail diagnostics for redemption-only child processes. (INVITE-002)
class _MySQLInvitationReadyMail:
    # Return only the fixed readiness field consumed by Admin listing paths.
    def readiness(self):
        # Keep the provider/network boundary fully fake in this disposable proof.
        return {"status": "ready"}


# Redeem one invitation idempotently through an independent MySQL process. (INVITE-003)
def _mysql_invitation_redeem_worker(arguments):
    # Import the invitation and token services only inside the spawned process.
    from casino.core import invitations, one_time_tokens, storage
    # Import the configured data root so every child derives identical provider document keys.
    from casino.config import DATA_DIR, GUEST_TERMS_VERSION
    # Import the one generic public error allowed for a losing in-flight observation.
    from casino.errors import ValidationError

    # Unpack the synthetic bearer and caller key without logging either value.
    index, token, caller_key = arguments
    # Preserve the workflow's provider selector around this bounded process proof.
    previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
    # Route every state-store call through the disposable MySQL database.
    os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
    # Inject one independent provider so the child owns its own connections.
    storage.set_provider_for_tests(storage.MySQLStorageProvider())
    # Start protected redemption so provider routing is always restored.
    try:
        # Build the shared purpose-bound token service over the canonical provider document.
        token_service = one_time_tokens.TokenService(store_path=DATA_DIR / "auth" / "one_time_tokens.json", digest_key=MYSQL_TOKEN_TEST_KEY, audit_sink=lambda level, event, fields: None)
        # Build the invitation service with both repository gates enabled only for this disposable test.
        service = invitations.InvitationService(store_path=DATA_DIR / "auth" / "invitations.json", enabled=True, enrollment_enabled=True, digest_key=MYSQL_MAIL_TEST_KEY, token_service=token_service, mail_service=_MySQLInvitationReadyMail(), audit_sink=lambda event, **fields: None)
        # Start protected public redemption so a safe race loser becomes serializable evidence.
        try:
            # Submit the exact same caller-idempotent request through every independent process.
            receipt = service.redeem(token, MYSQL_INVITATION_RECIPIENT, MYSQL_INVITATION_PASSWORD, "MySQL Invited Player", "en-US", GUEST_TERMS_VERSION, True, caller_key)
            # Return only the fixed success state and process index.
            return index, receipt.get("status") == "enrolled"
        # Convert a bounded in-flight conflict into the only permitted public error evidence.
        except ValidationError as error:
            # Require the generic reason with no recipient, account, or token detail.
            assert error.details == invitations.GENERIC_REDEMPTION_DETAILS
            # Report a safely rejected concurrent observation.
            return index, False
    # Always release process-local provider state before exit.
    finally:
        # Clear the injected provider instance.
        storage.set_provider_for_tests(None)
        # Restore an inherited provider selector exactly when one existed.
        if previous_provider_name is not None:
            # Replace the test selector with its original value.
            os.environ["CASINO_STORAGE_PROVIDER"] = previous_provider_name
        # Remove only the test-owned selector when the parent had none.
        else:
            # Delete the bounded process environment entry.
            os.environ.pop("CASINO_STORAGE_PROVIDER", None)


# Submit one problem report through an independent MySQL process. (CORE-027, TEST-094)
def _mysql_feedback_worker(arguments):
    # Import the production feedback service and independent provider only inside the child.
    from casino.core import feedback, storage
    # Import the stable public rate outcome for bounded worker serialization.
    from casino.errors import RateLimitError

    # Unpack mode, caller index, and browser-style action key without logging report prose.
    mode, index, action_key = arguments
    # Preserve the workflow provider selector around this disposable operation.
    previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
    # Route every provider lookup through the disposable MySQL database.
    os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
    # Inject one independent provider and connection pool per spawned process.
    storage.set_provider_for_tests(storage.MySQLStorageProvider())
    # Start protected submission so provider routing is always restored.
    try:
        # Build one synthetic authenticated persistent-user identity.
        user = {"user_id": MYSQL_FEEDBACK_USER_ID, "identity_provider": "local"}
        # Build bounded privacy-safe submission input with no attachment bytes.
        body = {"idempotency_key": action_key, "category": "bug", "impact": "difficult", "summary": "Disposable MySQL feedback proof", "actual": "A synthetic integration state was observed.", "expected": "The synthetic integration state should remain consistent.", "attachments": [], "context": {"route": "/roulette", "locale": "en-US", "viewport_width": 1024, "viewport_height": 900, "browser_family": "Other", "os_family": "Other", "reduced_motion": False}}
        # Convert the expected durable rate limit into one fixed serializable result.
        try:
            # Submit through the same recoverable saga used by the HTTP route.
            receipt = feedback.submit(user, body)
            # Return only opaque identifiers and replay state.
            return index, "accepted", receipt["report_id"], receipt["replayed"]
        # Handle only the governed durable rate outcome for unique-key races.
        except RateLimitError:
            # Return no report identity for a rejected rate slot.
            return index, "limited", None, None
    # Always restore child-process provider routing.
    finally:
        # Clear the injected provider instance.
        storage.set_provider_for_tests(None)
        # Restore an inherited selector exactly when one existed.
        if previous_provider_name is not None:
            # Replace the bounded selector with its inherited value.
            os.environ["CASINO_STORAGE_PROVIDER"] = previous_provider_name
        # Remove the worker-owned selector when the parent had none.
        else:
            # Delete only the scoped environment entry.
            os.environ.pop("CASINO_STORAGE_PROVIDER", None)


# Execute one OAuth persistence operation through an independent MySQL process. (OAUTH-008, OAUTH-009)
def _mysql_oauth_worker(arguments):
    # Import provider-neutral OAuth persistence only inside the spawned process.
    from casino.core.oauth.identity_links import ExternalIdentityLink
    # Import the exact durable flow, rate, and identity-link repositories under test.
    from casino.core.oauth.persistence import OAuthFlowRepository, OAuthRateLimiter, PersistentIdentityLinkRepository
    # Import the shared storage provider and stable losing-race error classes.
    from casino.core import storage
    # Import bounded public conflict and authorization outcomes for serialization.
    from casino.errors import ConflictError, RateLimitError, UnauthorizedError

    # Unpack the serializable worker operation packet without logging proof values.
    mode, index, payload = arguments
    # Preserve the workflow provider selector around this process-isolated operation.
    previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
    # Route every provider document through the disposable MySQL database.
    os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
    # Construct one independent connection-owning provider per process.
    provider = storage.MySQLStorageProvider()
    # Start protected operation dispatch so environment routing always returns to its inherited state.
    try:
        # Claim and consume the same browser-bound OAuth flow exactly once across processes.
        if mode == "claim":
            # Bind one strong-key flow repository to this process's provider.
            repository = OAuthFlowRepository(provider, MYSQL_OAUTH_TEST_KEY)
            # Convert the expected losing race into one bounded serializable result.
            try:
                # Claim the exact state, callback, and browser binding.
                record = repository.claim("google", payload["state"], payload["callback"], payload["owner"])
                # Commit the replay tombstone before reporting the winner.
                repository.complete(record)
                # Return only worker index and stable win state.
                return index, "consumed"
            # Suppress all proof-bearing failure detail from the worker result.
            except UnauthorizedError:
                # Return only the stable losing-race state.
                return index, "rejected"
        # Race provider-subject uniqueness between different canonical user identifiers.
        if mode == "link":
            # Bind one link repository to this process's provider.
            repository = PersistentIdentityLinkRepository(provider)
            # Build a bounded synthetic link with no recipient or provider claim data.
            link = ExternalIdentityLink(provider="facebook", subject="mysql-oauth-subject", user_id=f"mysql-oauth-user-{index}", created_at="2026-07-22T00:00:00.000Z", updated_at="2026-07-22T00:00:00.000Z")
            # Convert the expected compound-uniqueness loser to a fixed marker.
            try:
                # Save the subject under the provider row-lock transaction.
                _stored, created = repository.save(link)
                # Return only whether this worker published the binding.
                return index, "created" if created else "existing"
            # Suppress the conflicting user and subject from results.
            except ConflictError:
                # Return a fixed conflict state.
                return index, "conflict"
        # Race one shared durable limiter bucket across processes.
        if mode == "rate":
            # Bind the same three-attempt allowance to every worker process.
            limiter = OAuthRateLimiter(provider, MYSQL_OAUTH_TEST_KEY, limit=3)
            # Convert expected excess attempts into a bounded marker.
            try:
                # Check and append under the provider's atomic document transaction.
                limiter.check("mysql-browser-binding", "google", "signin")
                # Return only the accepted marker.
                return index, "accepted"
            # Suppress bucket digests and event state from the losing result.
            except RateLimitError:
                # Return only the stable rate-limited marker.
                return index, "limited"
        # Reject unreviewed worker modes inside the disposable test process.
        raise AssertionError("unsupported OAuth worker mode")
    # Restore process-local provider routing regardless of the operation outcome.
    finally:
        # Restore an inherited provider selector when one existed.
        if previous_provider_name is not None:
            # Replace only this process's temporary selector.
            os.environ["CASINO_STORAGE_PROVIDER"] = previous_provider_name
        # Remove the process-local selector when the parent had none.
        else:
            # Delete only this worker's environment entry.
            os.environ.pop("CASINO_STORAGE_PROVIDER", None)


# Simulate a process that commits an action journal entry but loses projection and response.
class _LostResponseJsonProvider:
    # Initialize a delegating provider subclass lazily to avoid import-time casino state.
    @staticmethod
    def build(data_root):  # Build the scoped failure-injecting provider.
        # Import storage only when the failure-injection test runs.
        from casino.core import storage

        # Define a scoped provider subclass that fails its first projection.
        class LostResponseProvider(storage.JsonStorageProvider):
            # Initialize the provider and one-shot failure marker.
            def __init__(self, path):
                # Initialize the normal isolated JSON provider.
                super().__init__(path)
                # Fail only the first projection after the durable action commit.
                self.fail_projection = True

            # Inject a lost response between logical commit and compatible-file projection.
            def _project_committed_action(self, event):
                # Branch on the one-shot failure marker.
                if self.fail_projection:
                    # Disable failure so same-instance recovery would also be possible.
                    self.fail_projection = False
                    # Simulate process termination or a lost response after journal commit.
                    raise RuntimeError("simulated lost response after action commit")
                # Delegate later projections to the production recovery implementation.
                return super()._project_committed_action(event)

        # Return the failure-injecting provider instance.
        return LostResponseProvider(Path(data_root))


# Define the run_json_provider_parity function used by the storage test runner.
def run_json_provider_parity():
    # Import core modules lazily so provider injection is active before calls execute.
    from casino.core import history, ledger, players, settings
    # Import storage helpers used to inject an isolated provider.
    from casino.core import storage

    # Create a temporary workspace so this test never mutates checked-in data files.
    with tempfile.TemporaryDirectory() as tmp:
        # Build an isolated data root for the JSON provider.
        data_root = Path(tmp) / "data"
        # Build a provider that uses the isolated data root.
        provider = storage.JsonStorageProvider(data_root)
        # Inject the isolated provider for all core storage callers.
        storage.set_provider_for_tests(provider)
        # Start protected logic so provider injection is always cleared.
        try:
            # Ensure the isolated storage directories exist.
            provider.ensure_ready()
            # Bootstrap default players through the provider-owned idempotent boundary.
            provider.bootstrap_players(players.default_players())
            # Read the default players back through the public players service.
            loaded = players.list_players()
            # Verify the human default player remains available.
            assert any(player["player_id"] == "human" for player in loaded)
            # Capture the starting fake-money balance.
            before = players.get_player("human")["balance"]
            # Debit through the ledger so the balance mutation uses the provider transaction path.
            debit = ledger.debit("human", 25, "TEST_STORAGE_DEBIT", "storage", "round_json", {"provider": "json"})
            # Verify the ledger event records the expected before/after values.
            assert debit["balance_before"] == before and debit["balance_after"] == before - 25
            # Credit through the ledger so the reverse mutation uses the same provider path.
            credit = ledger.credit("human", 10, "TEST_STORAGE_CREDIT", "storage", "round_json", {"provider": "json"})
            # Verify the credit event records the expected final balance.
            assert credit["balance_after"] == before - 15
            # Read recent ledger rows through the public ledger service.
            rows = ledger.read_recent("human", 10)
            # Verify both provider-written ledger events are visible.
            assert [row["ledger_id"] for row in rows] == [debit["ledger_id"], credit["ledger_id"]]
            # Append a history event through the provider-backed history service.
            history.append_history("storage", "round_json", "human", "test", "JSON parity", 25, "win", 10, credit["balance_after"], {"provider": "json"})
            # Read the history row back through the public history service.
            recent = history.recent_history(5, "storage")
            # Verify history details preserve the CSV-compatible JSON text field.
            assert recent and recent[-1]["details_json"] == '{"provider": "json"}'
            # Read the absent provider document before any owner setting is persisted. (AUDIO-010)
            default_audio = settings.audio_settings()
            # Require every default sound channel and announcement to remain fail-closed. (AUDIO-010)
            assert all(default_audio[key] is False for key in ("master_enabled", "sfx_enabled", "voice_enabled", "announce_roulette_results", "announce_blackjack_results", "announce_baccarat_results", "announce_bingo_calls", "announce_keno_results"))
            # Persist audio settings through the provider-backed settings service.
            saved = settings.save_audio_settings({"master_enabled": True, "voice_enabled": True, "voice_volume": 0.4})
            # Verify settings writes merge with defaults and normalize booleans/floats.
            assert saved["master_enabled"] is True and saved["voice_enabled"] is True and saved["voice_volume"] == 0.4
            # Read settings back through the provider document store.
            reloaded = settings.audio_settings()
            # Verify settings persisted in the provider document.
            assert reloaded["master_enabled"] is True and reloaded["voice_enabled"] is True and reloaded["voice_volume"] == 0.4
            # Name one isolated security-document key for strict provider proof.
            strict_key = "auth/strict_document_test"
            # Resolve its exact local path before any document exists.
            strict_path = provider.document_path(strict_key)
            # Track lazy missing-default evaluation.
            default_calls = []
            # Return one reviewed missing-document default.
            def strict_default():
                # Record the sole lazy evaluation.
                default_calls.append("called")
                # Return one exact object accepted by the test shape predicate.
                return {"schema_version": 1}
            # Read the absent document through the strict provider seam.
            missing = provider.read_document_strict(strict_key, strict_default, lambda value: isinstance(value, dict))
            # Require the reviewed default exactly once and no document creation.
            assert missing == {"schema_version": 1} and default_calls == ["called"] and not strict_path.exists()
            # Persist one valid object through the ordinary provider write abstraction.
            provider.write_document(strict_key, {"schema_version": 1, "mode": "closed"})
            # Require the strict provider seam to return the valid decoded object.
            assert provider.read_document_strict(strict_key, {}, lambda value: isinstance(value, dict)) == {"schema_version": 1, "mode": "closed"}
            # Enumerate invalid UTF-8, truncated JSON, duplicate keys, and invalid object shape.
            hostile_payloads = (
                # Refuse text that cannot decode as UTF-8.
                b"\xff\xfe\xfa",
                # Refuse syntactically truncated JSON.
                b'{"schema_version":1',
                # Refuse duplicate keys instead of last-value-wins interpretation.
                b'{"schema_version":1,"schema_version":2}',
                # Refuse a syntactically valid array under the object predicate.
                b"[]",
            )
            # Exercise every hostile durable byte sequence independently.
            for hostile in hostile_payloads:
                # Write the exact hostile bytes outside the provider abstraction.
                strict_path.write_bytes(hostile)
                # Snapshot every provider and control file after hostile setup.
                before_inventory = {path.relative_to(Path(tmp)).as_posix(): path.read_bytes() for path in Path(tmp).rglob("*") if path.is_file()}
                # Require strict read to use one fixed value-free recovery error.
                try:
                    # Attempt the strict security-document read.
                    provider.read_document_strict(strict_key, {}, lambda value: isinstance(value, dict))
                # Accept only the fixed provider-owned recovery boundary.
                except RuntimeError as exc:
                    # Require no path, payload, parser, or duplicate key detail.
                    assert str(exc) == "Stored document requires operator recovery"
                # Fail if hostile state was accepted or normalized.
                else:
                    # Surface one fixed assertion without hostile content.
                    raise AssertionError("strict JSON document corruption was accepted")
                # Track whether the strict update mutator was invoked.
                mutator_calls = []
                # Define one mutator that must remain unreachable.
                def forbidden_mutator(current):
                    # Record any incorrect invocation.
                    mutator_calls.append(current)
                    # Return a value that must never be written.
                    return {}
                # Require strict update to refuse under the same held document transaction.
                try:
                    # Attempt validator-bound mutation of the hostile document.
                    provider.update_document(strict_key, forbidden_mutator, {}, lambda value: isinstance(value, dict))
                # Accept only the same fixed provider-owned recovery boundary.
                except RuntimeError as exc:
                    # Require no path, payload, parser, or duplicate key detail.
                    assert str(exc) == "Stored document requires operator recovery"
                # Fail if strict update reached or replaced hostile state.
                else:
                    # Surface one fixed assertion without hostile content.
                    raise AssertionError("strict JSON document update accepted corruption")
                # Require the mutator to remain unreachable.
                assert mutator_calls == []
                # Snapshot exact state after both refused operations.
                after_inventory = {path.relative_to(Path(tmp)).as_posix(): path.read_bytes() for path in Path(tmp).rglob("*") if path.is_file()}
                # Require byte-identical state with no backup, temp, or normalization artifact.
                assert after_inventory == before_inventory
            # Restore one readable document for filesystem-failure injection.
            strict_path.write_text('{"schema_version":1}', encoding="utf-8")
            # Capture exact bytes before simulated read failure.
            strict_bytes = strict_path.read_bytes()
            # Track whether an access failure is incorrectly treated as an absent document.
            failure_defaults = []
            # Define a default factory that must remain unreachable on OSError.
            def forbidden_default():
                # Record any incorrect missing-document fallback.
                failure_defaults.append("called")
                # Return a value that must never be observed.
                return {}
            # Replace only path byte reads with a synthetic filesystem failure.
            with mock.patch.object(Path, "read_bytes", side_effect=OSError("synthetic-hidden-path")):
                # Require strict read to collapse filesystem detail.
                try:
                    # Attempt the injected failing read.
                    provider.read_document_strict(strict_key, forbidden_default, lambda value: isinstance(value, dict))
                # Accept only the fixed provider recovery boundary.
                except RuntimeError as exc:
                    # Require one value-free message.
                    assert str(exc) == "Stored document requires operator recovery"
                # Fail if the filesystem error escaped or was ignored.
                else:
                    # Surface one fixed assertion.
                    raise AssertionError("strict JSON filesystem failure was accepted")
            # Track strict-update mutator reachability under read-text failure.
            failed_update_calls = []
            # Replace only path byte reads with a synthetic filesystem failure.
            with mock.patch.object(Path, "read_bytes", side_effect=OSError("synthetic-hidden-path")):
                # Require strict update to collapse filesystem detail.
                try:
                    # Attempt the injected failing validator-bound update.
                    provider.update_document(strict_key, lambda current: failed_update_calls.append(current), forbidden_default, lambda value: isinstance(value, dict))
                # Accept only the fixed provider recovery boundary.
                except RuntimeError as exc:
                    # Require one value-free message.
                    assert str(exc) == "Stored document requires operator recovery"
                # Fail if the filesystem error escaped or mutation continued.
                else:
                    # Surface one fixed assertion.
                    raise AssertionError("strict JSON update filesystem failure was accepted")
            # Require no mutator invocation and exact source bytes after injected failures.
            assert failure_defaults == [] and failed_update_calls == [] and strict_path.read_bytes() == strict_bytes
            # Verify the JSON fallback still creates the familiar local files.
            assert (data_root / "players.json").exists() and (data_root / "ledger.jsonl").exists() and (data_root / "history.csv").exists()
        # Always clear provider injection after the isolated test run.
        finally:
            # Restore normal provider selection for subsequent tests.
            storage.set_provider_for_tests(None)


# Prove JSON action uniqueness across processes, restart, conflict, and lost response.
def run_json_action_idempotency():
    # Import public player defaults and storage providers for isolated setup and verification.
    from casino.core import players, storage
    # Import the conflict type expected for changed action-key reuse.
    from casino.errors import ConflictError

    # Create an isolated data root that cannot touch the user-owned runtime store.
    with tempfile.TemporaryDirectory() as tmp:
        # Build the provider path shared only by child processes in this test.
        data_root = Path(tmp) / "data"
        # Seed the isolated wallet through the production provider shape.
        provider = storage.JsonStorageProvider(data_root)
        # Persist default players before concurrent child processes begin.
        provider.bootstrap_players(players.default_players())
        # Capture the initial fake-money balance for exact-once settlement proof.
        starting_balance = next(row["balance"] for row in provider.load_players(players.default_players)["players"] if row["player_id"] == "human")
        # Define debit, payout, refund, and settlement families with distinct signed amounts.
        families = [("debit", -5, "action-debit"), ("payout", 8, "action-payout"), ("refund", 5, "action-refund"), ("settlement", 2, "action-settlement")]
        # Build at least 25 simultaneous duplicate calls for every money-action family.
        packets = [(str(data_root), family, amount, action_key) for family, amount, action_key in families for _ in range(25)]
        # Execute duplicates through independent processes that share only the storage files.
        with ProcessPoolExecutor(max_workers=8) as executor:
            # Materialize every result so process failures surface as test failures.
            results = list(executor.map(_json_action_worker, packets))
        # Verify each action family returned exactly one immutable ledger ID.
        for index, family in enumerate(families):
            # Slice the 25 results belonging to this family.
            family_results = results[index * 25:(index + 1) * 25]
            # Require every duplicate to return the original committed ledger event.
            assert len({ledger_id for ledger_id, _ in family_results}) == 1
            # Require exactly one new commit and 24 storage-detected replays.
            assert sum(1 for _, replayed in family_results if replayed is False) == 1
        # Reopen the provider to prove restart does not erase action identities.
        restarted = storage.JsonStorageProvider(data_root)
        # Replay one action after provider reconstruction.
        replay_event, replayed = restarted.transact_ledger_once("human", -5, "TEST_DEBIT", "action-debit", "storage", "round_debit", {"family": "debit"})
        # Verify restart replay returns the original debit event.
        assert replayed is True and replay_event["ledger_id"] == results[0][0]
        # Resolve the same action through the provider's canonical point-lookup seam. (LEDGER-033)
        indexed_event = restarted.find_ledger_action("human", "storage", "action-debit")
        # Require the indexed read to return the exact immutable event shape and identity.
        assert indexed_event == replay_event and indexed_event is not replay_event
        # Require an unused key to return a clean miss without scanning ledger history.
        assert restarted.find_ledger_action("human", "storage", "action-missing") is None
        # Reject the same identity when the signed amount changes.
        try:
            # Attempt changed semantic reuse without allowing a second wallet mutation.
            restarted.transact_ledger_once("human", -6, "TEST_DEBIT", "action-debit", "storage", "round_debit", {"family": "debit"})
        # Accept only the standard conflict response.
        except ConflictError:
            # Record successful conflict enforcement by continuing the test.
            pass
        # Fail when changed reuse was incorrectly accepted.
        else:
            # Surface the missing conflict gate.
            raise AssertionError("Changed ledger action reuse did not conflict")
        # Read the final wallet after all duplicate and conflict attempts.
        final_state = restarted.load_players(players.default_players)
        # Extract the human wallet balance.
        final_balance = next(row["balance"] for row in final_state["players"] if row["player_id"] == "human")
        # Verify only the four distinct signed actions changed the wallet.
        assert final_balance == starting_balance + sum(amount for _, amount, _ in families)
        # Verify only four append-only ledger rows exist despite 101 calls.
        assert len(restarted.read_ledger_recent("human", 200)) == 4
        # Start a separate isolated store for lost-response recovery proof.
        recovery_root = Path(tmp) / "recovery-data"
        # Seed the recovery wallet through a normal provider.
        storage.JsonStorageProvider(recovery_root).bootstrap_players(players.default_players())
        # Build the failure-injecting provider that stops after durable action commit.
        failing = _LostResponseJsonProvider.build(recovery_root)
        # Execute the action and expect the injected post-commit failure.
        try:
            # Commit an action identity before simulating process loss.
            failing.transact_ledger_once("human", -7, "TEST_LOST_RESPONSE", "lost-response", "storage", "round_lost", {"family": "debit"})
        # Accept only the injected failure marker.
        except RuntimeError as exc:
            # Verify the failure happened at the intended boundary.
            assert "lost response" in str(exc)
        # Fail when failure injection did not interrupt projection.
        else:
            # Surface the missing crash boundary.
            raise AssertionError("Lost-response failure injection did not run")
        # Reconstruct a normal provider to simulate process restart after the lost response.
        recovered = storage.JsonStorageProvider(recovery_root)
        # Read wallet state before retry so restart recovery cannot depend on client resubmission.
        recovered_state = recovered.load_players(players.default_players)
        # Extract the recovered wallet balance after startup-style state access.
        recovered_before_retry = next(row["balance"] for row in recovered_state["players"] if row["player_id"] == "human")
        # Verify ordinary restart state access projects the committed debit exactly once.
        assert recovered_before_retry == starting_balance - 7
        # Retry the identical action so startup recovery projects and replays the commit.
        recovered_event, recovered_replay = recovered.transact_ledger_once("human", -7, "TEST_LOST_RESPONSE", "lost-response", "storage", "round_lost", {"family": "debit"})
        # Verify the retry was recognized as a replay rather than a second debit.
        assert recovered_replay is True
        # Verify recovery produced one ledger row using the original committed event ID.
        assert recovered.read_ledger_recent("human", 10)[0]["ledger_id"] == recovered_event["ledger_id"]
        # Verify the recovered wallet changed exactly once.
        recovered_balance = next(row["balance"] for row in recovered.load_players(players.default_players)["players"] if row["player_id"] == "human")
        # Require one seven-token debit after restart recovery.
        assert recovered_balance == starting_balance - 7


# Prove funded practice-opponent accounts settle only through durable ledger actions.
def run_practice_opponent_accounting():
    # Import the approved account controller and core storage services lazily.
    from casino.bots import practice_opponents
    # Import player defaults and provider injection for isolated evidence.
    from casino.core import players, storage
    # Import the standard conflict raised by changed action-key reuse.
    from casino.errors import ConflictError

    # Create a temporary store so no user-owned runtime data can be touched.
    with tempfile.TemporaryDirectory() as tmp:
        # Build the isolated provider path shared by parent and child processes.
        data_root = Path(tmp) / "practice-data"
        # Seed canonical human and bot player accounts in the isolated store.
        provider = storage.JsonStorageProvider(data_root)
        # Persist defaults before controller reads or ledger actions begin.
        provider.bootstrap_players(players.default_players())
        # Inject the isolated provider into public services in this process.
        storage.set_provider_for_tests(provider)
        # Start protected logic so provider injection is always cleared.
        try:
            # Record the human balance to prove controller actions never reach it.
            human_before = players.get_player("human")["balance"]
            # Fund all three real bot wallets through fixed ledger identities.
            first_funding = practice_opponents.fund_accounts()
            # Replay the same funding request without minting another token.
            replay_funding = practice_opponents.fund_accounts()
            # Require one commit then one replay for every allocated account.
            assert all(not row["replayed"] for row in first_funding) and all(row["replayed"] for row in replay_funding)
            # Verify each account has its default balance plus one fixed funding credit.
            assert all(players.get_player(player_id)["balance"] == 105_000 for player_id in practice_opponents.PRACTICE_ACCOUNT_IDS)
            # Reserve one opponent stack for the first authenticated owner.
            debit = practice_opponents.transact("bot_1", 50, "PRACTICE_OPPONENT_ESCROW_DEBIT", "practice:human-a:round-1:bot-1:escrow", "round-1", "debit", "reserve_stack", session_owner_id="human-a", component="escrow")
            # Replay the exact reserve command without a second debit.
            debit_replay = practice_opponents.transact("bot_1", 50, "PRACTICE_OPPONENT_ESCROW_DEBIT", "practice:human-a:round-1:bot-1:escrow", "round-1", "debit", "reserve_stack", session_owner_id="human-a", component="escrow")
            # Require immutable event replay and an unchanged bot balance.
            assert debit_replay["replayed"] is True and debit_replay["event"]["ledger_id"] == debit["event"]["ledger_id"] and players.get_player("bot_1")["balance"] == 104_950
            # Reject changed amount reuse before another wallet mutation.
            try:
                # Attempt to reuse the escrow identity with a different exposure.
                practice_opponents.transact("bot_1", 55, "PRACTICE_OPPONENT_ESCROW_DEBIT", "practice:human-a:round-1:bot-1:escrow", "round-1", "debit", "reserve_stack", session_owner_id="human-a", component="escrow")
            # Accept only the storage-enforced semantic conflict.
            except ConflictError:
                # Continue after proving the changed request failed closed.
                pass
            # Fail if the provider accepted a conflicting settlement identity.
            else:
                # Surface missing storage uniqueness as a focused failure.
                raise AssertionError("Changed practice-opponent action reuse did not conflict")
            # Credit the unused stack through a distinct refund identity.
            refund = practice_opponents.transact("bot_1", 20, "PRACTICE_OPPONENT_ESCROW_REFUND", "practice:human-a:round-1:bot-1:refund", "round-1", "credit", "refund_stack", session_owner_id="human-a", component="refund")
            # Credit a showdown payout through a distinct settlement identity.
            payout = practice_opponents.transact("bot_1", 80, "PRACTICE_OPPONENT_PAYOUT", "practice:human-a:round-1:bot-1:payout", "round-1", "credit", "settle_payout", session_owner_id="human-a", component="payout")
            # Require controller audit dimensions on every movement family.
            for result in (debit, refund, payout):
                # Read standardized details from the immutable ledger event.
                details = result["event"]["details"]
                # Verify bot, game, round, owner, action, and component traceability.
                assert details["controller_kind"] == "practice_opponent" and details["bot_id"] == "bot_1" and result["event"]["game"] == practice_opponents.TEXAS_HOLDEM_PRACTICE_GAME and result["event"]["round_id"] == "round-1" and details["session_owner_id"] == "human-a" and details["practice_action_key"] and details["component"]
            # Execute a separate action identity for a second human session owner.
            second_owner = practice_opponents.transact("bot_1", 10, "PRACTICE_OPPONENT_ESCROW_DEBIT", "practice:human-b:round-2:bot-1:escrow", "round-2", "debit", "reserve_stack", session_owner_id="human-b", component="escrow")
            # Prove the second owner has independent round and audit identity.
            assert second_owner["event"]["round_id"] == "round-2" and second_owner["event"]["details"]["session_owner_id"] == "human-b"
            # Reconstruct the provider to prove restart retains action identities.
            restarted = storage.JsonStorageProvider(data_root)
            # Point the service at the reconstructed provider instance.
            storage.set_provider_for_tests(restarted)
            # Replay the first debit after provider reconstruction.
            after_restart = practice_opponents.transact("bot_1", 50, "PRACTICE_OPPONENT_ESCROW_DEBIT", "practice:human-a:round-1:bot-1:escrow", "round-1", "debit", "reserve_stack", session_owner_id="human-a", component="escrow")
            # Require the original immutable event after restart.
            assert after_restart["replayed"] is True and after_restart["event"]["ledger_id"] == debit["event"]["ledger_id"]
            # Build 25 same-action calls for independent operating-system processes.
            packets = [(str(data_root), "bot_2", "practice:human-cross-process:round:bot-2:escrow") for _ in range(25)]
            # Execute every duplicate against the same real funded bot account.
            with ProcessPoolExecutor(max_workers=8) as executor:
                # Materialize results so every child failure reaches this test.
                process_results = list(executor.map(_practice_opponent_worker, packets))
            # Require one ledger id and exactly one new cross-process debit commit.
            assert len({ledger_id for ledger_id, _ in process_results}) == 1 and sum(1 for _, replayed in process_results if replayed is False) == 1
            # Restore the reconstructed provider after child processes finish.
            storage.set_provider_for_tests(storage.JsonStorageProvider(data_root))
            # Read Admin activity from append-only ledger evidence only.
            activity = practice_opponents.recent_activity(100)
            # Require funding, debit, refund, payout, both owners, and cross-process evidence.
            assert len(activity) == 8 and {row["details"].get("session_owner_id") for row in activity} >= {"human-a", "human-b", "human-cross-process"}
            # Prove all human wallets remain untouched by opponent funding and settlement.
            assert players.get_player("human")["balance"] == human_before
        # Always clear provider injection after isolated accounting evidence.
        finally:
            # Restore normal runtime provider selection for later tests.
            storage.set_provider_for_tests(None)


# Define the run_mysql_schema_provider_path function used by the storage test runner.
def run_mysql_schema_provider_path():
    # Import storage helpers lazily so this test does not require a MySQL service.
    from casino.core import mysql_migrations, storage

    # Construct one fully initialized lazy provider for MySQL seam injection without a connection.
    def isolated_provider():
        # Bind planner/reset identity to an exact reserved local fixture target.
        config = storage.MySQLConfig(host="127.0.0.1", port=3306, user="fixture", password="synthetic", database="casino_fixture")
        # Keep the unused lazy pool bounded to one physical session if a regression opens it.
        pool_config = storage.MySQLPoolConfig(capacity=1, checkout_wait_ms=100, connect_timeout_seconds=1)
        # Initialize config, planner guards, reset-local state, readiness, and the unopened pool normally.
        return storage.MySQLStorageProvider(config=config, pool_config=pool_config)

    # Load the checksum-verified canonical migration catalog.
    migrations, expected, minimum, catalog_sha256 = mysql_migrations.load_catalog()
    # Join exact driver statements for lightweight structural assertions.
    joined = "\n".join(statement for migration in migrations for statement in migration.statements)
    # Verify every expected application table is present in the canonical migrations.
    assert all(table in joined for table in ("casino_schema_versions", "casino_players", "casino_ledger", "casino_history", "casino_documents"))
    # Verify the bridge window spans exact schema two through the catalog tail.
    assert (minimum, expected) == (2, migrations[-1].version) and len(catalog_sha256) == 64
    # Require migration application to remain held for this bridge release.
    assert mysql_migrations.schema_contract()["apply_policy"] == "held"
    # Verify wallet and ledger money columns use fixed decimal precision.
    assert "DECIMAL(18,2)" in joined
    # Verify ledger rows depend on player rows through a foreign key.
    assert "FOREIGN KEY (player_id)" in joined
    # Verify fresh schemas enforce one action key per player and action namespace.
    assert "action_scope VARCHAR(64)" in joined and "action_key VARCHAR(191)" in joined and "action_fingerprint VARCHAR(128)" in joined
    # Verify fresh schemas create the canonical unique action index.
    assert "CREATE UNIQUE INDEX uq_casino_ledger_action ON casino_ledger (player_id, action_scope, action_key)" in joined
    # Verify metadata DDL is centralized in the proof-gated runner rather than runtime storage.
    metadata_source = inspect.getsource(mysql_migrations._initialize_metadata)
    # Require both fail-closed control tables in the minimal metadata boundary.
    assert all(table in metadata_source for table in mysql_migrations.CONTROL_TABLES)
    # Read the MySQL transaction implementation source.
    source = inspect.getsource(storage.MySQLStorageProvider.transact_ledger)
    # Verify the MySQL ledger path locks the player row before mutating balance.
    assert "FOR UPDATE" in source
    # Verify the MySQL ledger path starts an explicit transaction.
    assert "start_transaction" in source
    # Verify the MySQL ledger path inserts the ledger row before committing.
    assert "INSERT INTO casino_ledger" in source and "connection.commit()" in source
    # Read the generic document mutation implementation added for security-state transactions.
    document_source = inspect.getsource(storage.MySQLStorageProvider.update_document)
    # Require one explicit transaction and row lock around the entire read-modify-write.
    assert "start_transaction" in document_source and "FOR UPDATE" in document_source
    # Require absent-row materialization, locked update, commit, and rollback behavior.
    assert "INSERT INTO casino_documents" in document_source and "UPDATE casino_documents" in document_source and "connection.commit()" in document_source and "connection.rollback()" in document_source
    # Construct a fully initialized but connection-free provider for bounded seam injection.
    strict_provider = isolated_provider()
    # Return one valid driver-decoded object through the existing read behavior.
    strict_provider.read_document = lambda key, default: {"schema_version": 1}
    # Require strict read to preserve valid MySQL-decoded provider values.
    assert strict_provider.read_document_strict("auth/strict", {}, lambda value: isinstance(value, dict)) == {"schema_version": 1}
    # Return one invalid driver-decoded shape without opening a live connection.
    strict_provider.read_document = lambda key, default: []
    # Require strict MySQL-like shape refusal to use the fixed recovery boundary.
    try:
        # Attempt the invalid strict read.
        strict_provider.read_document_strict("auth/strict", {}, lambda value: isinstance(value, dict))
    # Accept only the fixed provider-owned recovery failure.
    except RuntimeError as exc:
        # Require no payload or connector detail.
        assert str(exc) == "Stored document requires operator recovery"
    # Fail if the invalid shape was returned.
    else:
        # Surface one fixed assertion.
        raise AssertionError("strict MySQL document shape was accepted")
    # Raise one synthetic decoder failure through the existing MySQL read seam.
    strict_provider.read_document = lambda key, default: (_ for _ in ()).throw(ValueError("synthetic-payload-detail"))
    # Require decoder detail to remain value-free.
    try:
        # Attempt the failing strict read.
        strict_provider.read_document_strict("auth/strict", {}, lambda value: isinstance(value, dict))
    # Accept only the fixed provider-owned recovery failure.
    except RuntimeError as exc:
        # Require no payload or connector detail.
        assert str(exc) == "Stored document requires operator recovery"
    # Fail if the decoder exception escaped.
    else:
        # Surface one fixed assertion.
        raise AssertionError("strict MySQL decoder failure escaped")
    # Define one cursor that returns an invalid locked document row.
    class StrictMySQLCursor:
        # Initialize executed statement evidence.
        def __init__(self):
            # Retain exact SQL verbs for no-update proof.
            self.statements = []
        # Record each statement without performing database work.
        def execute(self, statement, parameters):
            # Retain the statement text only.
            self.statements.append(statement)
        # Return the one invalid provider-decoded row after the lock query.
        def fetchone(self):
            # Model a JSON column the driver decoded as an array.
            return {"payload_json": []}
    # Define one connection that records transaction cleanup decisions.
    class StrictMySQLConnection:
        # Initialize one cursor and terminal counters.
        def __init__(self):
            # Own the single fake cursor.
            self.cursor_instance = StrictMySQLCursor()
            # Start without a transaction marker.
            self.started = False
            # Start without commit, rollback, or close.
            self.committed = self.rolled_back = self.closed = False
        # Record explicit transaction start.
        def start_transaction(self):
            # Mark the transaction active.
            self.started = True
        # Return the single fake dictionary cursor.
        def cursor(self, dictionary=False):
            # Preserve the production call shape without changing results.
            return self.cursor_instance
        # Record an impossible successful commit.
        def commit(self):
            # Mark any incorrect commit.
            self.committed = True
        # Record required failure rollback.
        def rollback(self):
            # Mark transaction rollback.
            self.rolled_back = True
        # Record required connection cleanup.
        def close(self):
            # Mark connection close.
            self.closed = True
    # Build one isolated fake connection.
    strict_connection = StrictMySQLConnection()
    # Bypass live readiness without altering the production class.
    strict_provider.ensure_ready = lambda: None
    # Return only the fake row-lock connection.
    strict_provider.connect = lambda: strict_connection
    # Track whether the caller mutator was reached.
    strict_mutator_calls = []
    # Require invalid shape to fail and roll back inside the row transaction.
    try:
        # Invoke the actual MySQL update implementation with strict validation.
        strict_provider.update_document("auth/strict", lambda current: strict_mutator_calls.append(current), {}, lambda value: isinstance(value, dict))
    # Accept only the fixed provider-owned recovery failure.
    except RuntimeError as exc:
        # Require no payload or connector detail.
        assert str(exc) == "Stored document requires operator recovery"
    # Fail if the invalid shape crossed the locked validator.
    else:
        # Surface one fixed assertion.
        raise AssertionError("strict MySQL update accepted invalid shape")
    # Require start, rollback, and close without commit or mutator invocation.
    assert strict_connection.started and strict_connection.rolled_back and strict_connection.closed and not strict_connection.committed and strict_mutator_calls == []
    # Reaching the stubbed transaction proves the active planner guard accepted the exact fixture target.
    assert strict_provider._planner_key() == ("127.0.0.1", 3306, "casino_fixture")
    # Require no durable document UPDATE statement after strict shape refusal.
    assert all(not statement.lstrip().upper().startswith("UPDATE CASINO_DOCUMENTS") for statement in strict_connection.cursor_instance.statements)
    # Read the storage-enforced action transaction implementation source.
    action_source = inspect.getsource(storage.MySQLStorageProvider.transact_ledger_once)
    # Verify action replay lookup occurs after a wallet row lock in one explicit transaction.
    assert "FOR UPDATE" in action_source and "action_scope" in action_source and "action_key" in action_source
    # Verify identity, wallet balance, and ledger event commit in the same provider method.
    assert "UPDATE casino_players" in action_source and "INSERT INTO casino_ledger" in action_source and "connection.commit()" in action_source
    # Read the indexed point-lookup implementation under the same permanent provider gate. (LEDGER-033)
    lookup_source = inspect.getsource(storage.MySQLStorageProvider.find_ledger_action)
    # Require the unique player/scope/key predicate without a player lock or write statement.
    assert "action_scope = %s AND action_key = %s" in lookup_source and "FOR UPDATE" not in lookup_source and "INSERT " not in lookup_source and "UPDATE " not in lookup_source
    # Define one point-lookup cursor that returns an exact driver-style row once.
    class IndexedMySQLCursor:
        # Initialize the configured row and empty SQL evidence.
        def __init__(self, row):
            # Retain the optional exact row returned by fetchone.
            self.row = row
            # Record the query and bound identity for index-shape assertions.
            self.calls = []
        # Record one point lookup without executing an external query.
        def execute(self, statement, parameters):
            # Preserve the exact SQL and canonical identity dimensions.
            self.calls.append((statement, parameters))
        # Return the configured row or miss.
        def fetchone(self):
            # Preserve the driver-style optional row contract.
            return self.row
    # Define one connection that proves read-only cleanup.
    class IndexedMySQLConnection:
        # Initialize one cursor and close marker.
        def __init__(self, row):
            # Own one configured fake cursor.
            self.cursor_instance = IndexedMySQLCursor(row)
            # Start without connection cleanup evidence.
            self.closed = False
        # Return the dictionary cursor expected by the provider.
        def cursor(self, dictionary=False):
            # Require the public-event mapping path.
            assert dictionary is True
            # Return the sole fake cursor.
            return self.cursor_instance
        # Record deterministic connection cleanup.
        def close(self):
            # Mark the read-only connection released.
            self.closed = True
    # Build one exact indexed row with driver-compatible money and details values.
    indexed_row = {"ledger_id": "led_indexed", "ts": "2026-08-10T00:00:00.000Z", "player_id": "human", "game": "storage", "round_id": "round-indexed", "transaction_type": "TEST_INDEXED", "amount": -5, "balance_before": 100, "balance_after": 95, "details_json": '{"ledger_action_key":"action-indexed"}'}
    # Construct another initialized provider without opening a real pool or database.
    indexed_provider = isolated_provider()
    # Bypass schema readiness after the migration source assertions above.
    indexed_provider.ensure_ready = lambda: None
    # Return one hit connection for the first exact lookup.
    hit_connection = IndexedMySQLConnection(indexed_row)
    # Bind the hit connection to the real provider method.
    indexed_provider.connect = lambda: hit_connection
    # Resolve the exact hit through the production point-lookup implementation.
    indexed_event = indexed_provider.find_ledger_action("human", "storage", "action-indexed")
    # Require public shape, canonical SQL bindings, and deterministic connection cleanup.
    assert indexed_event["ledger_id"] == "led_indexed" and hit_connection.cursor_instance.calls[0][1] == ("human", "storage", "action-indexed") and hit_connection.closed
    # Return one miss connection for the absent identity case.
    miss_connection = IndexedMySQLConnection(None)
    # Rebind the provider to the miss connection.
    indexed_provider.connect = lambda: miss_connection
    # Require a clean optional miss and connection cleanup.
    assert indexed_provider.find_ledger_action("human", "storage", "action-missing") is None and miss_connection.closed
    # Close both still-empty lazy pools so fixtures prove no hidden connector allocation.
    strict_provider.close_pool()
    # Close the independent indexed fixture pool as well.
    indexed_provider.close_pool()
    # Read runtime readiness source after migration ownership moved out of the provider.
    runtime_source = inspect.getsource(storage.MySQLStorageProvider.ensure_ready)
    # Require only the read-only compatibility verifier at runtime.
    assert "verify_runtime_compatibility" in runtime_source
    # Reject every DDL or migration-state DML verb from runtime readiness.
    assert all(fragment not in runtime_source.upper() for fragment in ("CREATE ", "ALTER ", "DROP ", "INSERT ", "UPDATE ", "DELETE "))


# Exercise real MySQL persistence, domain documents, and concurrent ledger locking.
def _run_mysql_pool_live_measurements(provider):
    # Store one secret-free aggregate result per governed concurrency level.
    measurements = []
    # Capture pool counters before the bounded measurement packet.
    before_snapshot = provider.pool_snapshot()

    # Execute one request-scoped SELECT through the production pool.
    def execute_probe(index):
        # Capture one request-local monotonic start.
        started_at = time.perf_counter()
        # Start without a lease so failure cleanup is deterministic.
        connection = None
        # Start without a cursor so failure cleanup is deterministic.
        cursor = None
        # Start protected MySQL work so every acquired resource is returned.
        try:
            # Acquire one request-scoped pooled connection.
            connection = provider.connect()
            # Open a connector cursor for one bounded read-only statement.
            cursor = connection.cursor()
            # Execute a constant query containing no caller, player, session, or schema identity.
            cursor.execute("SELECT 1")
            # Require the disposable service to return the expected constant.
            assert cursor.fetchone()[0] == 1
            # Return aggregate elapsed time plus a zero-error marker.
            return (time.perf_counter() - started_at) * 1000.0, 0
        # Convert every connector failure into one aggregate error marker without preserving text.
        except Exception:
            # Return elapsed time and one safe error count.
            return (time.perf_counter() - started_at) * 1000.0, 1
        # Always close cursor and lease resources.
        finally:
            # Close the cursor when creation succeeded.
            if cursor is not None:
                # Release connector cursor resources.
                cursor.close()
            # Return or discard the physical session when checkout succeeded.
            if connection is not None:
                # Route cleanup through the production lease.
                connection.close()

    # Exercise every required concurrency level using the same constant operation.
    for concurrency in (1, 2, 4, 8):
        # Capture aggregate wall-clock start for throughput.
        run_started_at = time.perf_counter()
        # Execute sixteen bounded operations at this concurrency.
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Materialize every result so no worker failure is lost.
            results = list(executor.map(execute_probe, range(16)))
        # Capture aggregate wall-clock duration after every lease returned.
        wall_seconds = time.perf_counter() - run_started_at
        # Sort only request-local elapsed milliseconds for nearest-rank percentiles.
        ordered = sorted(result[0] for result in results)
        # Select the nearest-rank median observation.
        p50_ms = ordered[((50 * len(ordered) + 99) // 100) - 1]
        # Select the nearest-rank ninety-fifth-percentile observation.
        p95_ms = ordered[((95 * len(ordered) + 99) // 100) - 1]
        # Count failures without retaining connector exception text.
        errors = sum(result[1] for result in results)
        # Store only concurrency, aggregate latency, throughput, and error count.
        measurements.append({"concurrency": concurrency, "p50_ms": round(p50_ms, 3), "p95_ms": round(p95_ms, 3), "throughput_rps": round(len(results) / wall_seconds, 3), "errors": errors})
    # Acquire one sanitized lease for cross-request session-state evidence.
    first_connection = provider.connect()
    # Open one cursor to create a synthetic session-local variable.
    first_cursor = first_connection.cursor()
    # Start protected setup so the first lease always returns.
    try:
        # Set one synthetic user variable containing no production identity.
        first_cursor.execute("SET @casino_pool_probe = 1")
    # Always close the first cursor and lease.
    finally:
        # Release the first cursor.
        first_cursor.close()
        # Trigger rollback/reset/liveness cleanup before reuse.
        first_connection.close()
    # Acquire the next request-scoped lease after session reset.
    second_connection = provider.connect()
    # Open one cursor to inspect the synthetic session variable.
    second_cursor = second_connection.cursor()
    # Start protected readback so the second lease always returns.
    try:
        # Read the variable only to prove reset_session removed cross-request state.
        second_cursor.execute("SELECT @casino_pool_probe")
        # Require no synthetic state to cross the request-scoped lease boundary.
        assert second_cursor.fetchone()[0] is None
    # Always close the second cursor and lease.
    finally:
        # Release the second cursor.
        second_cursor.close()
        # Return the verified clean session.
        second_connection.close()
    # Capture aggregate pool counters after every measurement and isolation probe.
    after_snapshot = provider.pool_snapshot()
    # Require all four governed concurrency rows.
    assert [row["concurrency"] for row in measurements] == [1, 2, 4, 8]
    # Require zero live connector errors at every concurrency.
    assert all(row["errors"] == 0 for row in measurements)
    # Require the warm single-concurrency latency targets.
    assert measurements[0]["p50_ms"] <= 100.0 and measurements[0]["p95_ms"] <= 200.0
    # Require the concurrency-four p95 target.
    assert measurements[2]["p95_ms"] <= 250.0
    # Require every throughput row to exceed the recorded pre-pool floor.
    assert all(row["throughput_rps"] > 3.37 for row in measurements)
    # Require physical connections to remain bounded by the configured hard capacity.
    assert after_snapshot["physical_created"] <= after_snapshot["capacity"]
    # Require the measurement packet to finish with no lease or waiter residue.
    assert after_snapshot["in_use"] == 0 and after_snapshot["waiting"] == 0
    # Require no pool exhaustion during the complete live packet.
    assert after_snapshot["timeout_count"] == before_snapshot["timeout_count"]
    # Build one exact-source secret-safe preflight artifact for later browser qualification.
    evidence = {
        # Bind the preflight to the workflow checkout without reading repository-private data.
        "source_commit": str(os.environ.get("GITHUB_SHA", "")).strip().lower(),
        # Preserve only the four aggregate measurement rows.
        "measurements": measurements,
        # Preserve only the fixed-cardinality pool snapshot.
        "pool": after_snapshot,
    }
    # Read the optional external evidence destination selected by an explicit qualification workflow.
    evidence_path_value = str(os.environ.get("CASINO_MYSQL_POOL_EVIDENCE", "")).strip()
    # Persist machine-readable evidence only when the caller selected a destination.
    if evidence_path_value:
        # Require one exact full source identity before writing a reusable preflight.
        assert len(evidence["source_commit"]) == 40 and all(character in "0123456789abcdef" for character in evidence["source_commit"])
        # Resolve the caller-owned external evidence file.
        evidence_path = Path(evidence_path_value).expanduser().resolve()
        # Refuse a generated qualification artifact inside the source checkout.
        assert evidence_path != ROOT and ROOT.resolve() not in evidence_path.parents
        # Create only the external parent selected by the workflow.
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        # Write stable compact JSON without credentials, target details, or connector text.
        evidence_path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")
    # Emit only sanitized aggregate evidence for hosted job logs.
    print("MYSQL_POOL_1_2_4_8 " + json.dumps(evidence, sort_keys=True), flush=True)
    # Return the same sanitized packet to listener-free callers.
    return evidence


# Exercise the configured bounded pool with repeated real wallet-row contention. (STORAGE-010, MYSQL-011, TEST-220)
def _run_mysql_capacity_aligned_debit_cohorts(provider, ledger_module, players_module):
    # Capture the exact pool policy and counters before any contested debit starts.
    before_snapshot = provider.pool_snapshot()
    # Require the disposable gate to stay inside the reviewed process-local capacity range.
    assert 1 <= before_snapshot["capacity"] <= 64
    # Require no lease or waiter residue from the preceding pool measurement packet.
    assert before_snapshot["in_use"] == 0 and before_snapshot["waiting"] == 0
    # Capture the authoritative wallet balance before three repeated cohorts.
    starting_balance = players_module.get_player("human")["balance"]
    # Retain only unique public ledger identifiers across all repeated cohorts.
    ledger_ids = set()
    # Repeat the twenty-debit schedule so one lucky timing pass cannot satisfy the gate.
    for cohort_index in range(3):
        # Match worker concurrency to physical capacity so a row-lock waiter owns the second lease without stranding six checkout waiters.
        with ThreadPoolExecutor(max_workers=before_snapshot["capacity"]) as executor:
            # Execute twenty unique one-token debits through the production ledger boundary.
            events = list(executor.map(lambda index: ledger_module.debit("human", 1, "MYSQL_CONCURRENT_DEBIT", "storage", f"mysql_concurrent_{cohort_index}_{index}", {"cohort": cohort_index, "index": index}), range(20)))
        # Require the current cohort to publish twenty distinct append-only events.
        assert len({event["ledger_id"] for event in events}) == 20
        # Accumulate exact event identities for the repeated-run uniqueness assertion.
        ledger_ids.update(event["ledger_id"] for event in events)
        # Require the wallet to reflect every completed cohort without a lost update.
        assert players_module.get_player("human")["balance"] == starting_balance - (20 * (cohort_index + 1))
        # Capture pool state only after the executor has joined every worker.
        after_cohort = provider.pool_snapshot()
        # Prove every successful worker returned its lease and left no capacity waiter behind.
        assert after_cohort["in_use"] == 0 and after_cohort["waiting"] == 0 and after_cohort["idle"] == after_cohort["capacity"]
        # Prove the capacity-aligned cohort did not hide, swallow, or trigger checkout exhaustion.
        assert after_cohort["timeout_count"] == before_snapshot["timeout_count"]
        # Prove capacity-aligned scheduling introduced no artificial checkout waiter.
        assert after_cohort["wait_count"] == before_snapshot["wait_count"]
        # Prove no uncertain connection cleanup forced a physical discard during the cohort.
        assert after_cohort["discarded"] == before_snapshot["discarded"]
    # Require all three repeated cohorts to preserve sixty unique committed event identities.
    assert len(ledger_ids) == 60
    # Build one secret-free aggregate for hosted acceptance evidence.
    evidence = {"capacity": after_cohort["capacity"], "cohorts": 3, "debits_per_cohort": 20, "committed": len(ledger_ids), "wallet_delta": starting_balance - players_module.get_player("human")["balance"], "pool": after_cohort}
    # Emit only fixed counts and the production pool's existing secret-free telemetry.
    print("MYSQL_POOL_CAPACITY_ALIGNED_DEBITS " + json.dumps(evidence, sort_keys=True), flush=True)
    # Return exact before/after balances for the following cross-process idempotency proof.
    return starting_balance, players_module.get_player("human")["balance"]


# Exercise real MySQL persistence, domain documents, and concurrent ledger locking.
def run_mysql_live_provider_path():
    # Import representative provider-backed domains only when live MySQL was requested.
    from casino.bots import profiles
    # Import release policy used by verified-email enrollment acceptance.
    from casino import config
    # Import the data root used to derive stable provider document keys.
    from casino.config import DATA_DIR
    # Import core services whose JSON-shaped state must no longer create hybrid files.
    from casino.core import auth, autoplay, feedback, guest_analytics, guest_conversion, invitations, ledger, mail, one_time_tokens, pending_enrollment, players, state_store, storage
    # Import the generic token rejection used by the superseded-bearer assertion.
    from casino.errors import ValidationError
    # Import OAuth persistence only inside the explicitly requested disposable MySQL gate.
    from casino.core.oauth.persistence import FLOW_DOCUMENT_KEY, FLOW_SECRET_DOCUMENT_KEY, OAuthFlowRecord, OAuthFlowRepository, PersistentIdentityLinkRepository
    # Import UTC helpers for one bounded flow fixture.
    from datetime import datetime, timedelta, timezone

    # Build the explicitly configured provider without ever reading or displaying its password.
    provider = storage.MySQLStorageProvider()
    # Inject the live provider so all services share the same test target.
    storage.set_provider_for_tests(provider)
    # Start protected logic so later test modes rebuild their normal provider.
    try:
        # Clear the dedicated integration database while preserving its schema.
        provider.reset()
        # Measure the bounded pool on the disposable MySQL service before domain-state concurrency.
        _run_mysql_pool_live_measurements(provider)
        # Seed fresh private-beta player rows through the provider abstraction.
        provider.bootstrap_players(players.default_players())
        # Create a real auth user so users and terms acceptance enter the provider document table.
        user = auth.create_user("mysql.integration@example.test", "mysql-integration-password", "MySQL Integration", terms_required=False)
        # Login so a live session document is persisted alongside the user record.
        login = auth.login(user["email"], "mysql-integration-password", "mysql-live-test")
        # Persist representative player-scoped game state through the generic state-store seam.
        state_store.save_player_game_state("slots", "human", {"spins": [{"round_id": "mysql_restart_round"}]})
        # Persist bot profile state through the real bots module.
        bot = profiles.update_bot("bot_1", {"enabled": False})
        # Persist an autoplay session through the real control-plane module.
        autoplay_session = autoplay.start("slots", "human", "medium", 2, {"type": "mysql-live"}, {})
        # Run the repeated configured-capacity debit gate before cross-process replay evidence. (MYSQL-011, TEST-220)
        _, balance_after_concurrent = _run_mysql_capacity_aligned_debit_cohorts(provider, ledger, players)
        # Execute 25 duplicate calls through two independent spawned processes.
        with ProcessPoolExecutor(max_workers=2) as executor:
            # Materialize every duplicate result so cross-process failures surface.
            action_results = list(executor.map(_mysql_action_worker, range(25)))
        # Verify all processes received the same immutable ledger event.
        assert len({ledger_id for _, ledger_id, _ in action_results}) == 1
        # Verify the unique action identity committed exactly once across processes.
        assert sum(1 for _, _, replayed in action_results if replayed is False) == 1
        # Verify the wallet absorbed only one three-token debit after the repeated concurrency cohorts.
        assert players.get_player("human")["balance"] == balance_after_concurrent - 3
        # Preserve the workflow's default provider selector around the focused token proof.
        previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
        # Route parent issue and read operations through the injected MySQL provider.
        os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
        # Start protected live evidence so the workflow selector is always restored.
        try:
            # Create one real provider-backed guest wallet for stale-teardown ownership parity. (AUTH-020, LEDGER-037, TEST-194)
            mysql_guest_player = players.create_player("MySQL stale teardown guest", "guest", config.GUEST_STARTING_BALANCE)
            # Create the de-identified lifecycle row through the production analytics boundary.
            mysql_guest_analytics = guest_analytics.record_started("en-US", "desktop", config.GUEST_STARTING_BALANCE)
            # Build the canonical disposable identity shape consumed by conversion and teardown.
            mysql_guest = {"user_id": "guest_mysql_stale_teardown", "email": None, "username": None, "display_name": "Guest trial", "role": "guest", "roles": ["guest"], "status": "active", "player_id": mysql_guest_player["player_id"], "password_hash": "", "terms_required": False, "terms_accepted_at": "2026-01-01T00:00:00.000Z", "terms_accepted_version": config.GUEST_TERMS_VERSION, "terms_acceptance_source": "guest_entry", "locale": "en-US", "language": "en-US", "created_at": "2026-01-01T00:00:00.000Z", "updated_at": "2026-01-01T00:00:00.000Z", "identity_provider": "guest", "guest": True, "guest_expires_at": "2036-01-01T00:00:00.000Z", "guest_analytics_id": mysql_guest_analytics}

            # Append the synthetic guest through the provider-owned users transaction.
            def add_mysql_guest(state):
                # Require the canonical document shape before adding live integration state.
                assert isinstance(state, dict) and isinstance(state.get("users"), list)
                # Append exactly one disposable owner of the newly created wallet.
                state["users"].append(mysql_guest)
                # Return the complete provider document for commit.
                return state

            # Persist the guest under the same MySQL row lock used by production admission.
            auth.update_json(auth.USERS_PATH, add_mysql_guest, auth.default_users)
            # Create one disposable session so successful conversion exercises canonical revocation.
            auth.create_session(mysql_guest, "mysql-stale-teardown-guest")
            # Commit a distinguishable legitimate movement before conversion adopts the wallet.
            ledger.debit(mysql_guest["player_id"], 125, "MYSQL_GUEST_PLAY", "roulette", "mysql_guest_play_round", {"proof": "stale_teardown"})
            # Convert through the exact production service and provider-owned users document transaction.
            mysql_conversion = guest_conversion.convert(mysql_guest, "mysql-stale-teardown@example.test", "MySQLStaleTeardownPassw0rd!23", "MySQL Stale Teardown", terms_version="v1", accepted=True, locale="en-US", idempotency_key="mysql-stale-teardown-conversion-0001")
            # Resolve the durable account that adopted the guest wallet.
            mysql_account = auth.find_user_by_email("mysql-stale-teardown@example.test")
            # Create one durable account session after conversion that stale guest teardown must preserve.
            auth.create_session(mysql_account, "mysql-stale-teardown-account")
            # Capture exact provider-backed wallet, ledger, history, and session state after conversion.
            mysql_player_before = dict(players.get_player(mysql_guest["player_id"]))
            # Capture the complete bounded ledger tail for exact no-movement proof.
            mysql_ledger_before = ledger.read_recent(mysql_guest["player_id"], 100)
            # Capture the provider's complete bounded history projection.
            mysql_history_before = provider.recent_history(limit=100)
            # Capture every canonical session after the account session is durable.
            mysql_sessions_before = auth.load_sessions()
            # Submit the exact stale pre-conversion principal through production teardown twice.
            auth.end_guest_trial(dict(mysql_guest), "ended")
            # Replay with a different terminal reason to prove stable converted refusal.
            auth.end_guest_trial(dict(mysql_guest), "expired")
            # Require every adopted-wallet and account-session projection to remain exact.
            assert (players.get_player(mysql_guest["player_id"]), ledger.read_recent(mysql_guest["player_id"], 100), provider.recent_history(limit=100), auth.load_sessions()) == (mysql_player_before, mysql_ledger_before, mysql_history_before, mysql_sessions_before)
            # Require one converted guest marker, one account owner, and zero terminal teardown rows.
            mysql_terminal_guest = auth.find_user_by_id(mysql_guest["user_id"])
            # Select non-guest owners from the canonical provider-backed identity document.
            mysql_owners = [row for row in auth.load_users()["users"] if row.get("player_id") == mysql_guest["player_id"] and not auth.is_guest(row)]
            # Bind provider parity for identity, wallet, and exactly-zero stale money movement.
            assert mysql_terminal_guest["status"] == "converted" and len(mysql_owners) == 1 and mysql_owners[0]["user_id"] == mysql_account["user_id"] and mysql_conversion["balance"] == mysql_player_before["balance"] and not any(row.get("transaction_type") == "GUEST_TRIAL_END" for row in mysql_ledger_before)
            # Build the inert token service over the canonical provider-routed authentication document.
            token_service = one_time_tokens.TokenService(store_path=DATA_DIR / "auth" / "one_time_tokens.json", digest_key=MYSQL_TOKEN_TEST_KEY, audit_sink=lambda level, event, fields: None)
            # Issue one ephemeral bearer for the cross-process exactly-once race.
            token_receipt = token_service.issue("password_reset", "mysql-token-subject@example.invalid")
            # Build twelve bounded independent process packets without writing ephemeral values to evidence.
            token_packets = [(index, token_receipt["token"], "mysql-token-subject@example.invalid") for index in range(12)]
            # Execute the same consume operation through independent MySQL connections and processes.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Materialize every result so child failures surface in the live integration gate.
                token_results = list(executor.map(_mysql_token_consume_worker, token_packets))
            # Require exactly one successful consume across all independent processes.
            assert sum(1 for _, won, _ in token_results if won) == 1
            # Require every successful observation to name the issued opaque record.
            assert {token_id for _, won, token_id in token_results if won} == {token_receipt["token_id"]}
            # Read the provider document after the race for durable state minimization evidence.
            token_document = provider.read_document("auth/one_time_tokens.json", one_time_tokens.default_tokens)
            # Serialize only isolated in-memory state for raw-material absence assertions.
            token_document_text = __import__("json").dumps(token_document, sort_keys=True)
            # Require no raw bearer or subject value in the durable MySQL document.
            assert token_receipt["token"] not in token_document_text and "mysql-token-subject@example.invalid" not in token_document_text
            # Require exactly one consumed timestamp for the issued opaque record.
            assert sum(1 for row in token_document.get("tokens", []) if row.get("token_id") == token_receipt["token_id"] and row.get("consumed_at")) == 1
            # Execute twelve duplicate mail submissions through independent MySQL connections and processes.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Materialize every safe worker result so a child failure surfaces in the live gate.
                mail_results = list(executor.map(_mysql_mail_submit_worker, range(12)))
            # Require exactly one process to cross the fake provider boundary.
            assert sum(call_count for _, call_count, _, _ in mail_results) == 1
            # Require every worker to correlate the same opaque delivery identity.
            assert len({delivery_id for _, _, delivery_id, _ in mail_results}) == 1
            # Require every concurrent observation to remain in-flight or terminally sent, never duplicated or failed.
            assert {status for _, _, _, status in mail_results}.issubset({"sending", "sent"})
            # Read the final provider document through the already injected parent connection.
            mail_document = provider.read_document("mail/deliveries.json", mail.default_state)
            # Serialize only the disposable integration state for raw-material absence assertions.
            mail_document_text = __import__("json").dumps(mail_document, sort_keys=True)
            # Require one durable delivery and no raw recipient, bearer, tokened URL, provider credential, or caller key.
            assert len(mail_document.get("deliveries", {})) == 1 and "mysql-mail@example.invalid" not in mail_document_text and "synthetic-mysql-mail-bearer" not in mail_document_text and "token=" not in mail_document_text and "synthetic-provider-token" not in mail_document_text and "mysql-mail-shared-idempotency" not in mail_document_text
            # Require the single durable claim to reach its terminal sent state.
            assert next(iter(mail_document["deliveries"].values()))["status"] == "sent"
            # Build an independent fake transport for the verified-email MySQL saga.
            enrollment_transport = _MySQLMailTransport()
            # Compose one ready mail boundary over a distinct provider-backed document.
            enrollment_mail = mail.MailService(state_path=DATA_DIR / "mail" / "pending-enrollment-deliveries.json", enabled=True, network_enabled=True, provider="postmark", digest_key=MYSQL_MAIL_TEST_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=enrollment_transport)
            # Reuse the proven token provider while isolating enrollment state by document key.
            enrollment_service = pending_enrollment.PendingEnrollmentService(store_path=DATA_DIR / "auth" / "pending_enrollments.json", enabled=True, digest_key=MYSQL_MAIL_TEST_KEY, token_service=token_service, mail_service=enrollment_mail, audit_sink=lambda event, **fields: None)
            # Begin one account-free provider-backed pending enrollment.
            assert enrollment_service.initiate("mysql-enrollment@example.invalid", MYSQL_INVITATION_PASSWORD, "MySQL Enrollment", "en-US", config.GUEST_TERMS_VERSION, True, "mysql-enrollment-initiate-key-0001", "mysql-enrollment-source-1") == {"status": "verification_pending"}
            # Repeat the recipient under a distinct caller key to prove provider-atomic uniqueness and enumeration safety.
            assert enrollment_service.initiate("mysql-enrollment@example.invalid", "Different-MySQL-Enrollment-2026!", "Different MySQL Enrollment", "ru-RU", config.GUEST_TERMS_VERSION, True, "mysql-enrollment-initiate-key-0002", "mysql-enrollment-source-2") == {"status": "verification_pending"}
            # Require one pending row and one delivery before a successful resend.
            assert enrollment_transport.calls == 1 and len(state_store.read_json(DATA_DIR / "auth" / "pending_enrollments.json", pending_enrollment.default_pending_enrollments)["enrollments"]) == 1
            # Extract the predecessor bearer only from transient fake provider mail.
            predecessor_match = re.search(r"[?&]token=([^\s<]+)", enrollment_transport.messages[0]["text_body"])
            # Require one exact same-origin predecessor bearer.
            assert predecessor_match is not None
            # Remove only the test cooldown to exercise two-phase replacement under MySQL locking.
            with mock.patch.object(config, "EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS", 0):
                # Deliver one provider-backed replacement generation.
                assert enrollment_service.resend("mysql-enrollment@example.invalid", "en-US", "mysql-enrollment-resend-key-0001", "mysql-enrollment-resend-source") == {"status": "verification_pending"}
            # Require exactly one replacement transport call.
            assert enrollment_transport.calls == 2
            # Extract the promoted bearer from the second transient message.
            replacement_match = re.search(r"[?&]token=([^\s<]+)", enrollment_transport.messages[1]["text_body"])
            # Require the replacement to exist without persisting its value.
            assert replacement_match is not None
            # Prove the predecessor is invalid only after successful provider delivery and promotion.
            try:
                # Attempt direct consumption through the purpose-bound token boundary.
                token_service.consume(pending_enrollment.PURPOSE, predecessor_match.group(1), subject="mysql-enrollment@example.invalid")
                # Fail if the superseded predecessor unexpectedly remained active.
                raise AssertionError("superseded enrollment token remained active")
            # Accept only the repository's generic token rejection.
            except ValidationError:
                # Continue after the expected generic rejection.
                pass
            # Verify and activate through the replacement bearer exactly once.
            assert enrollment_service.verify(replacement_match.group(1), "mysql-enrollment@example.invalid", "mysql-enrollment-verify-key-0001", "mysql-enrollment-verify-source") == {"status": "enrolled"}
            # Replay the exact completed verification without duplicate identity, wallet, credit, or session.
            assert enrollment_service.verify(replacement_match.group(1), "mysql-enrollment@example.invalid", "mysql-enrollment-verify-key-0001", "mysql-enrollment-verify-source") == {"status": "enrolled"}
            # Resolve the single active canonical user.
            enrollment_user = auth.find_user_by_email("mysql-enrollment@example.invalid")
            # Require one funded active wallet and no implicit session.
            assert enrollment_user is not None and players.get_player(enrollment_user["player_id"])["balance"] == float(config.ACCOUNT_STARTING_BALANCE) and not any(session.get("user_id") == enrollment_user["user_id"] for session in auth.load_sessions().get("sessions", []))
            # Require exactly one deterministic starting-balance event.
            assert sum(1 for event in ledger.read_recent(enrollment_user["player_id"], 20) if event.get("transaction_type") == "ACCOUNT_STARTING_BALANCE") == 1
            # Build a second provider-backed enrollment whose worker stops after durable provider acceptance.
            crash_transport = _MySQLMailTransport()
            # Compose a distinct mail document so the crash proof has one isolated delivery.
            crash_mail = mail.MailService(state_path=DATA_DIR / "mail" / "pending-enrollment-crash-deliveries.json", enabled=True, network_enabled=True, provider="postmark", digest_key=MYSQL_MAIL_TEST_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=crash_transport)
            # Arm exactly one abrupt provider-recorded stop.
            crash_armed = {"value": True}

            # Stop after the provider receipt is durable but before promotion/finalization.
            def enrollment_crash_hook(phase):
                # Match only the selected durable checkpoint once.
                if crash_armed["value"] and phase == "provider_recorded":
                    # Disarm recovery calls before abrupt termination.
                    crash_armed["value"] = False
                    # Abort outside ordinary Exception cleanup.
                    raise _MySQLEnrollmentCrash()

            # Compose the crash-injected service over the same MySQL token and pending documents.
            crash_service = pending_enrollment.PendingEnrollmentService(store_path=DATA_DIR / "auth" / "pending_enrollments.json", enabled=True, digest_key=MYSQL_MAIL_TEST_KEY, token_service=token_service, mail_service=crash_mail, audit_sink=lambda event, **fields: None, phase_hook=enrollment_crash_hook)
            # Model one worker loss after sent receipt durability.
            try:
                # Begin the second pending enrollment.
                crash_service.initiate("mysql-enrollment-crash@example.invalid", MYSQL_INVITATION_PASSWORD, "MySQL Crash Enrollment", "en-US", config.GUEST_TERMS_VERSION, True, "mysql-enrollment-crash-initiate-0001", "mysql-enrollment-crash-source")
                # Fail if the injected durable boundary did not stop the worker.
                raise AssertionError("enrollment crash boundary did not stop")
            # Continue only after the exact abrupt-stop fixture.
            except _MySQLEnrollmentCrash:
                # Preserve provider documents exactly for recovery.
                pass
            # Extract the durably delivered bearer from transient fake mail.
            crash_match = re.search(r"[?&]token=([^\s<]+)", crash_transport.messages[0]["text_body"])
            # Require one delivered bearer before verification recovery.
            assert crash_match is not None
            # Reconcile promotion/final pending state and complete the emailed bearer.
            assert crash_service.verify(crash_match.group(1), "mysql-enrollment-crash@example.invalid", "mysql-enrollment-crash-verify-0001", "mysql-enrollment-crash-verify-source") == {"status": "enrolled"}
            # Create and cancel one provider-backed pending row.
            assert enrollment_service.initiate("mysql-enrollment-cancel@example.invalid", MYSQL_INVITATION_PASSWORD, "MySQL Cancel Enrollment", "en-US", config.GUEST_TERMS_VERSION, True, "mysql-enrollment-cancel-initiate-0001", "mysql-enrollment-cancel-source") == {"status": "verification_pending"}
            # Extract its current delivered ownership bearer from transient fake mail.
            cancel_match = re.search(r"[?&]token=([^\s<]+)", enrollment_transport.messages[2]["text_body"])
            # Require one cancellation ownership bearer.
            assert cancel_match is not None
            # Terminalize cancellation without account, wallet, or session creation.
            assert enrollment_service.cancel(cancel_match.group(1), "mysql-enrollment-cancel@example.invalid", "mysql-enrollment-cancel-key-0001", "mysql-enrollment-cancel-source") == {"status": "cancelled"} and auth.find_user_by_email("mysql-enrollment-cancel@example.invalid") is None
            # Read the complete provider document for privacy, replay, crash, and cancellation evidence.
            enrollment_document = state_store.read_json(DATA_DIR / "auth" / "pending_enrollments.json", pending_enrollment.default_pending_enrollments)
            # Select terminal rows before retention cleanup.
            enrollment_terminal_rows = [row for row in enrollment_document["enrollments"] if row.get("status") in {"complete", "cancelled"}]
            # Require all three terminal results and immediate credential/profile scrubbing.
            assert len(enrollment_terminal_rows) == 3 and all(not ({"email", "password_hash", "display_name", "locale", "terms_version", "replacement"} & set(row)) for row in enrollment_terminal_rows)
            # Create one active row that retention cleanup must preserve.
            assert enrollment_service.initiate("mysql-enrollment-active@example.invalid", MYSQL_INVITATION_PASSWORD, "MySQL Active Enrollment", "en-US", config.GUEST_TERMS_VERSION, True, "mysql-enrollment-active-initiate-0001", "mysql-enrollment-active-source") == {"status": "verification_pending"}
            # Age only scrubbed terminal rows inside a fixture write before testing provider-atomic pruning.
            enrollment_document = state_store.read_json(DATA_DIR / "auth" / "pending_enrollments.json", pending_enrollment.default_pending_enrollments)
            # Assign one unambiguously expired timestamp to terminal metadata only.
            for enrollment_row in enrollment_document["enrollments"]:
                # Preserve active and in-flight timestamps exactly.
                if enrollment_row.get("status") in {"complete", "cancelled"}:
                    # Age only scrubbed replay metadata.
                    enrollment_row["updated_at"] = "2000-01-01T00:00:00.000Z"
            # Persist the synthetic age fixture through the same provider document abstraction.
            state_store.write_json(DATA_DIR / "auth" / "pending_enrollments.json", enrollment_document)
            # Trigger bounded cleanup in one ordinary provider transaction.
            with mock.patch.object(config, "EMAIL_ENROLLMENT_TERMINAL_RETENTION_SECONDS", 1):
                # Initiate a distinct active row while pruning old terminal metadata.
                assert enrollment_service.initiate("mysql-enrollment-cleanup@example.invalid", MYSQL_INVITATION_PASSWORD, "MySQL Cleanup Trigger", "en-US", config.GUEST_TERMS_VERSION, True, "mysql-enrollment-cleanup-initiate-0001", "mysql-enrollment-cleanup-source") == {"status": "verification_pending"}
            # Read the post-cleanup authoritative provider document.
            enrollment_after_cleanup = state_store.read_json(DATA_DIR / "auth" / "pending_enrollments.json", pending_enrollment.default_pending_enrollments)
            # Require old terminal rows gone and both active rows retained.
            assert sorted(row.get("status") for row in enrollment_after_cleanup["enrollments"]) == ["pending", "pending"]
            # Issue one invitation bearer through the already proven token service without invoking live mail.
            invitation_token = token_service.issue(invitations.PURPOSE, MYSQL_INVITATION_RECIPIENT)
            # Build one invitation service only to derive the domain-separated recipient verifier.
            invitation_service = invitations.InvitationService(store_path=DATA_DIR / "auth" / "invitations.json", enabled=True, enrollment_enabled=True, digest_key=MYSQL_MAIL_TEST_KEY, token_service=token_service, mail_service=_MySQLInvitationReadyMail(), audit_sink=lambda event, **fields: None)
            # Capture one durable instant for the disposable invitation fixture.
            invitation_now = invitation_service.clock()
            # Seed the minimum complete pending invitation state through the provider-backed document seam.
            state_store.write_json(DATA_DIR / "auth" / "invitations.json", {"schema_version": 1, "invitations": [{"invitation_id": "invite_mysql_live", "recipient": MYSQL_INVITATION_RECIPIENT, "recipient_digest": invitation_service._digest("recipient", MYSQL_INVITATION_RECIPIENT), "recipient_hint": "m***@e***.invalid", "status": "pending", "delivery_status": "sent", "delivery_generation": 1, "token_id": invitation_token["token_id"], "mail_delivery_id": "delivery_mysql_live", "locale": "en-US", "invited_by": "user_admin_mysql", "create_idempotency_digest": invitation_service._digest("admin-idempotency", "mysql-live-create-idempotency"), "created_at": invitation_now, "updated_at": invitation_now, "expires_at": invitation_token["expires_at"], "redeemed_at": None, "revoked_at": None, "redemption": None, "history": []}]})
            # Build repeated exact caller packets without publishing the bearer or replay key.
            invitation_packets = [(index, invitation_token["token"], "mysql-invitation-redeem-idempotency") for index in range(8)]
            # Race independent MySQL processes across claim, token consume, identity, wallet, and finalization.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Materialize every bounded result so a child process failure fails this gate.
                invitation_results = list(executor.map(_mysql_invitation_redeem_worker, invitation_packets))
            # Require at least one generic success and no duplicate durable account or wallet.
            assert any(success for _, success in invitation_results)
            # Read canonical provider-backed users after every worker exits.
            invitation_users = auth.load_users()
            # Require exactly one active invitation-owned account and no leaked reservation.
            assert sum(1 for user_row in invitation_users.get("users", []) if user_row.get("invitation_id") == "invite_mysql_live" and user_row.get("status") == "active") == 1 and invitation_users.get("reservations") == []
            # Require exactly one deterministic invitation-owned player wallet.
            assert sum(1 for player_row in players.load_players().get("players", []) if str(player_row.get("player_id", "")).startswith("player_invite_")) == 1
            # Read the terminal invitation state through the shared provider.
            invitation_document = state_store.read_json(DATA_DIR / "auth" / "invitations.json", invitations.default_invitations)
            # Require one terminal redemption and no persisted bearer, password, or caller key.
            invitation_document_text = __import__("json").dumps(invitation_document, sort_keys=True)
            # Verify the exact lifecycle result and privacy boundary.
            assert [row.get("status") for row in invitation_document.get("invitations", [])] == ["redeemed"] and invitation_token["token"] not in invitation_document_text and MYSQL_INVITATION_PASSWORD not in invitation_document_text and "mysql-invitation-redeem-idempotency" not in invitation_document_text
            # Race eight exact feedback retries through independent MySQL connections and processes.
            feedback_replay_packets = [("replay", index, "mysql-feedback-shared-idempotency") for index in range(8)]
            # Materialize every exact retry result.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Execute the complete recoverable service rather than a storage-only shortcut.
                feedback_replay_results = list(executor.map(_mysql_feedback_worker, feedback_replay_packets))
            # Require every process to resolve one opaque winner and exactly one non-replay response.
            assert len({report_id for _, status, report_id, _ in feedback_replay_results if status == "accepted"}) == 1 and sum(1 for _, status, _, replayed in feedback_replay_results if status == "accepted" and replayed is False) == 1
            # Race eight distinct actions against the remaining four durable rate slots.
            feedback_rate_packets = [("rate", index, f"mysql-feedback-unique-{index:02d}") for index in range(8)]
            # Materialize every rate decision across independent connections.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Prove check-and-append serialization through the production service.
                feedback_rate_results = list(executor.map(_mysql_feedback_worker, feedback_rate_packets))
            # Require the shared five-event window to accept four new reports and reject four callers.
            assert sum(1 for _, status, _, _ in feedback_rate_results if status == "accepted") == 4 and sum(1 for _, status, _, _ in feedback_rate_results if status == "limited") == 4
            # Read the final authoritative state through the injected parent provider.
            feedback_document = provider.read_document(feedback.STATE_DOCUMENT, feedback._empty_state)
            # Serialize only disposable state for raw-material absence assertions.
            feedback_document_text = __import__("json").dumps(feedback_document, sort_keys=True)
            # Require five committed reports, five durable rate events, and no raw user id or caller keys.
            assert len(feedback_document.get("reports", [])) == 5 and len(feedback_document.get("rate_events", [])) == 5 and MYSQL_FEEDBACK_USER_ID not in feedback_document_text and "mysql-feedback-" not in feedback_document_text
            # Build one strong-key flow repository over the same disposable MySQL provider.
            oauth_flows = OAuthFlowRepository(provider, MYSQL_OAUTH_TEST_KEY)
            # Create opaque synthetic proofs that never leave this live-test process group.
            oauth_state = "s" * 43
            # Bind the flow to one fixed reserved-domain callback.
            oauth_callback = "https://casino.example.test/api/v2/auth/oauth/google/callback"
            # Bind the flow to one generated-shape browser verifier.
            oauth_owner = "b" * 64
            # Read one creation instant for exact expiry ordering.
            oauth_created = datetime.now(timezone.utc)
            # Render canonical millisecond UTC timestamps without provider-local time.
            oauth_stamp = lambda value: value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
            # Persist one complete pending flow with physically separated metadata and exchange proof documents.
            oauth_flows.create(OAuthFlowRecord(flow_id="oauth_mysql_flow", provider="google", state=oauth_state, nonce="n" * 43, pkce_verifier="v" * 64, callback_uri=oauth_callback, owner_binding=oauth_owner, action="signin", return_to="/", status="pending", created_at=oauth_stamp(oauth_created), expires_at=oauth_stamp(oauth_created + timedelta(minutes=5))))
            # Build twelve identical claim packets for independent MySQL processes.
            oauth_claim_packets = [("claim", index, {"state": oauth_state, "callback": oauth_callback, "owner": oauth_owner}) for index in range(12)]
            # Race claim and replay-tombstone commit across independent connections.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Materialize every result so child process failure fails the live gate.
                oauth_claim_results = list(executor.map(_mysql_oauth_worker, oauth_claim_packets))
            # Require exactly one successful claim/consume and eleven indistinguishable replay losers.
            assert sum(1 for _, status in oauth_claim_results if status == "consumed") == 1 and sum(1 for _, status in oauth_claim_results if status == "rejected") == 11
            # Read metadata and proof documents separately after the race.
            oauth_metadata = provider.read_document(FLOW_DOCUMENT_KEY, {})
            # Read the proof document independently for physical-separation evidence.
            oauth_proofs = provider.read_document(FLOW_SECRET_DOCUMENT_KEY, {})
            # Serialize only in-memory disposable evidence for raw-value absence assertions.
            oauth_metadata_text = __import__("json").dumps(oauth_metadata, sort_keys=True)
            # Require no raw state, callback, browser binding, nonce, or PKCE value in metadata.
            assert all(value not in oauth_metadata_text for value in (oauth_state, oauth_callback, oauth_owner, "n" * 43, "v" * 64))
            # Require terminal consume to remove the separate proof row while retaining the replay tombstone.
            assert oauth_proofs.get("secrets") == [] and [row.get("status") for row in oauth_metadata.get("flows", [])] == ["consumed"]
            # Build competing provider-subject link packets for distinct synthetic canonical users.
            oauth_link_packets = [("link", index, {}) for index in range(8)]
            # Race compound uniqueness across independent MySQL connections.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Materialize all winners and conflicts.
                oauth_link_results = list(executor.map(_mysql_oauth_worker, oauth_link_packets))
            # Require exactly one provider-subject owner and no idempotent false winner.
            assert sum(1 for _, status in oauth_link_results if status == "created") == 1 and sum(1 for _, status in oauth_link_results if status == "conflict") == 7
            # Build eight attempts against one three-event durable rate bucket.
            oauth_rate_packets = [("rate", index, {}) for index in range(8)]
            # Race limiter check-and-append across independent processes.
            with ProcessPoolExecutor(max_workers=4) as executor:
                # Materialize every bounded limiter decision.
                oauth_rate_results = list(executor.map(_mysql_oauth_worker, oauth_rate_packets))
            # Require the shared provider transaction to accept exactly three attempts.
            assert sum(1 for _, status in oauth_rate_results if status == "accepted") == 3 and sum(1 for _, status in oauth_rate_results if status == "limited") == 5
            # Seed malformed identity-link evidence to prove a later mutation cannot normalize it away.
            malformed_oauth_links = {"schema_version": 1, "links": "operator-recovery-required"}
            # Persist the exact malformed document only inside the disposable integration database.
            provider.write_document("auth/oauth_identity_links", malformed_oauth_links)
            # Bind a strict repository to the malformed state.
            malformed_repository = PersistentIdentityLinkRepository(provider)
            # Require mutation to fail without replacing the original evidence.
            try:
                # Attempt no real link value; the malformed collection must fail before model access.
                malformed_repository.delete_for_user("google", "mysql-oauth-user")
            # Accept only the fixed operator-recovery storage failure.
            except RuntimeError:
                # Continue to exact state readback.
                pass
            # Fail the live gate if malformed state was treated as an empty collection.
            else:
                # Surface only a fixed test assertion.
                raise AssertionError("malformed OAuth storage was normalized")
            # Require the exact malformed document to remain durable after the rejected mutation.
            assert provider.read_document("auth/oauth_identity_links", {}) == malformed_oauth_links
        # Always restore the workflow provider selector after the scoped proof.
        finally:
            # Restore an inherited selector exactly when one existed.
            if previous_provider_name is not None:
                # Replace the bounded MySQL selector with the inherited value.
                os.environ["CASINO_STORAGE_PROVIDER"] = previous_provider_name
            # Remove the temporary selector when the parent environment had none.
            else:
                # Delete only the test-owned environment entry.
                os.environ.pop("CASINO_STORAGE_PROVIDER", None)
        # Rebuild the provider to simulate a fresh application process after restart.
        storage.set_provider_for_tests(storage.MySQLStorageProvider())
        # Replay the same action after provider reconstruction.
        restarted_event, restarted_replay = ledger.debit_once("human", 3, "MYSQL_IDEMPOTENT_DEBIT", "mysql-action-debit", "storage", "mysql_action_round", {"family": "debit"})
        # Verify restart returns the original event without a second balance mutation.
        assert restarted_replay is True and restarted_event["ledger_id"] == action_results[0][1]
        # Verify the previously issued session still resolves to its persisted user.
        session, reopened_user = auth.authenticate_token(login["session"]["token"])
        # Verify auth identity and session data survived provider reconstruction.
        assert reopened_user["user_id"] == user["user_id"] and session["user_id"] == user["user_id"]
        # Verify player-scoped game state survived provider reconstruction.
        assert state_store.load_player_game_state("slots", "human", lambda: {})["spins"][0]["round_id"] == "mysql_restart_round"
        # Verify bot profile and autoplay state survived provider reconstruction.
        assert profiles.get_bot("bot_1")["enabled"] is bot["enabled"] and autoplay.get_session(autoplay_session["autoplay_id"])["status"] == "running"
        # Prove on the real service that creating a player never destroys committed money history.
        # The historical defect hid here because every fixture seeded players BEFORE any ledger write,
        # so the truncation inside the player-document replacement was never observed (issue #402).
        guard_debit = ledger.debit("human", 15, "TEST_LIVE_CREATE_PLAYER_DEBIT", "storage", "round_live_create", {})
        # Capture the committed balance so a stale-snapshot rewrite would be detectable.
        guard_balance = players.get_player("human")["balance"]
        # Create a player through the same public service guest trials and signup use.
        guard_player = players.create_player("Live Ledger Guard", "guest", 100.0)
        # Require the previously committed ledger row to still be readable after the player write.
        assert any(row["ledger_id"] == guard_debit["ledger_id"] for row in ledger.read_recent("human", 10)), "player creation destroyed committed MySQL ledger history"
        # Require the earlier wallet mutation to survive rather than being reverted from a snapshot.
        assert players.get_player("human")["balance"] == guard_balance, "player creation reverted a committed MySQL balance"
        # Require the new player row to be durably present alongside the seeded players.
        assert any(row["player_id"] == guard_player["player_id"] for row in players.list_players())
        # Commit one exactly-once action identity before exercising the compatibility document write.
        guard_action, guard_action_replayed = ledger.debit_once("human", 3, "MYSQL_SAVE_PLAYERS_GUARD", "mysql-save-players-guard", "storage", "round_mysql_save_players", {"issue": 431})
        # Require the first action call to commit so the replay proof is meaningful.
        assert guard_action_replayed is False
        # Capture the balance after every pre-existing durable mutation.
        guard_action_balance = players.get_player("human")["balance"]
        # Submit one stale existing row plus one missing row through the explicit bootstrap seam.
        provider.bootstrap_players({"players": [{"player_id": "human", "display_name": "Stale Snapshot", "type": "human", "balance": 999999.0, "created_at": guard_player["created_at"], "updated_at": guard_player["updated_at"], "status": "suspended"}, {"player_id": "mysql_save_players_guard", "display_name": "MySQL Save Players Guard", "type": "guest", "balance": 125.0, "created_at": guard_player["created_at"], "updated_at": guard_player["updated_at"], "status": "active"}]})
        # Require the stale supplied row to leave the committed wallet and lifecycle state unchanged.
        assert players.get_player("human")["balance"] == guard_action_balance and players.get_player("human")["status"] == "active"
        # Require the missing supplied row to be inserted alongside every existing player.
        assert players.get_player("mysql_save_players_guard")["balance"] == 125.0
        # Require the ledger event committed before bootstrap to remain readable.
        assert any(row["ledger_id"] == guard_debit["ledger_id"] for row in ledger.read_recent("human", 100))
        # Replay the pre-existing action identity after the compatibility write.
        replayed_action, replayed = ledger.debit_once("human", 3, "MYSQL_SAVE_PLAYERS_GUARD", "mysql-save-players-guard", "storage", "round_mysql_save_players", {"issue": 431})
        # Require the exact immutable event to replay without a second wallet mutation.
        assert replayed is True and replayed_action["ledger_id"] == guard_action["ledger_id"] and players.get_player("human")["balance"] == guard_action_balance
    # Always clear provider injection after the live integration test.
    finally:
        # Restore normal provider selection for later API or browser suites.
        storage.set_provider_for_tests(None)
        # Close the original live provider after every retained-reference assertion has completed.
        provider.close_pool()


# Prove player creation never destroys committed money history or reverts concurrent balances. (issue #402)
def run_player_creation_preserves_ledger():
    # Import the public player and ledger services plus storage injection helpers.
    from casino.core import ledger, players, storage

    # Create a temporary workspace so this test never mutates checked-in data files.
    with tempfile.TemporaryDirectory() as tmp:
        # Build an isolated data root for the JSON provider.
        data_root = Path(tmp) / "data"
        # Build a provider that uses the isolated data root.
        provider = storage.JsonStorageProvider(data_root)
        # Inject the isolated provider for all core storage callers.
        storage.set_provider_for_tests(provider)
        # Start protected logic so provider injection is always cleared.
        try:
            # Ensure the isolated storage directories exist.
            provider.ensure_ready()
            # Seed the default player document through the provider-owned bootstrap boundary.
            provider.bootstrap_players(players.default_players())
            # Move money BEFORE the next player is created. The original defect survived CI precisely
            # because every existing fixture seeded players before writing any ledger rows.
            debit = ledger.debit("human", 40, "TEST_CREATE_PLAYER_DEBIT", "storage", "round_create", {})
            # Capture the committed post-transaction balance for the reversion check.
            balance_after_debit = players.get_player("human")["balance"]
            # Verify the debit actually committed before the player write under test.
            assert debit["balance_after"] == balance_after_debit
            # Build two independent provider instances so bootstrap contenders use separate thread locks.
            contenders = (storage.JsonStorageProvider(data_root), storage.JsonStorageProvider(data_root))
            # Define one stale existing row plus overlapping and distinct missing bootstrap rows.
            batches = (
                # Preserve the durable human row while adding the first two identifiers.
                {"players": [{"player_id": "human", "display_name": "Stale Human", "type": "human", "balance": 999999.0, "status": "suspended"}, {"player_id": "bootstrap_shared", "display_name": "Shared", "type": "guest", "balance": 100.0}, {"player_id": "bootstrap_first", "display_name": "First", "type": "guest", "balance": 101.0}]},
                # Race the shared identifier while adding one independent identifier.
                {"players": [{"player_id": "bootstrap_shared", "display_name": "Changed Shared", "type": "guest", "balance": 999.0}, {"player_id": "bootstrap_second", "display_name": "Second", "type": "guest", "balance": 102.0}]},
            )
            # Run both bootstrap batches concurrently through the production cross-process boundary.
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Wait for both bounded contenders and surface any failure immediately.
                list(executor.map(lambda pair: pair[0].bootstrap_players(pair[1]), zip(contenders, batches)))
            # Require stale bootstrap input never to overwrite the already debited wallet or status.
            assert players.get_player("human")["balance"] == balance_after_debit and players.get_player("human")["status"] == "active"
            # Require each overlapping or distinct identifier to exist exactly once after the race.
            bootstrapped = [row["player_id"] for row in players.list_players() if row["player_id"].startswith("bootstrap_")]
            # Reject duplicate shared rows and lost independent rows.
            assert sorted(bootstrapped) == ["bootstrap_first", "bootstrap_second", "bootstrap_shared"]
            # Capture exact durable bytes before repeating an already satisfied bootstrap batch.
            bootstrap_bytes = provider.players_path().read_bytes()
            # Repeat the first batch to prove idempotent bootstrap performs no replacement write.
            provider.bootstrap_players(batches[0])
            # Require a byte-identical no-op when every supplied identifier already exists.
            assert provider.players_path().read_bytes() == bootstrap_bytes
            # Start two operating-system processes against the same isolated player document.
            with ProcessPoolExecutor(max_workers=2) as executor:
                # Require both overlapping bootstrap batches to complete without a lost update.
                process_bootstraps = list(executor.map(_json_player_bootstrap_worker, [(str(data_root), "first"), (str(data_root), "second")]))
            # Require both process-owned identifiers to report completion.
            assert sorted(process_bootstraps) == ["bootstrap_process_first", "bootstrap_process_second"]
            # Read every process bootstrap identifier after both independent providers exit.
            process_rows = [row["player_id"] for row in players.list_players() if row["player_id"].startswith("bootstrap_process_")]
            # Require the shared row once and both distinct rows once.
            assert sorted(process_rows) == ["bootstrap_process_first", "bootstrap_process_second", "bootstrap_process_shared"]
            # Start two independent public player creations against the same durable wallet.
            with ProcessPoolExecutor(max_workers=2) as executor:
                # Materialize both identifiers so worker errors cannot be hidden.
                process_created = list(executor.map(_json_player_create_worker, [(str(data_root), "A"), (str(data_root), "B")]))
            # Require both created identifiers to be distinct and durably visible.
            assert len(set(process_created)) == 2 and set(process_created) <= {row["player_id"] for row in players.list_players()}
            # Create a second player through the public service that guest trials and signup both use.
            created = players.create_player("Ledger Guard", "guest", 250.0)
            # Verify creation still returns a usable player row.
            assert created["player_id"] and created["balance"] == 250.0
            # Verify the committed ledger row survived the player write.
            rows = ledger.read_recent("human", 10)
            # Require the exact pre-existing ledger event to still be readable.
            assert any(row["ledger_id"] == debit["ledger_id"] for row in rows), "player creation destroyed committed ledger history"
            # Verify the earlier wallet mutation was not reverted from a stale in-memory snapshot.
            assert players.get_player("human")["balance"] == balance_after_debit, "player creation reverted a committed balance"
            # Verify the newly created player is durably present alongside the original.
            identifiers = {player["player_id"] for player in players.list_players()}
            # Require both the seeded and the newly created player to be readable.
            assert "human" in identifiers and created["player_id"] in identifiers
            # Verify a second creation with the same display name still yields a distinct player row.
            second = players.create_player("Ledger Guard", "guest", 250.0)
            # Require independent identifiers so creation is not silently idempotent on display name.
            assert second["player_id"] != created["player_id"]
        # Always clear provider injection after the isolated test run.
        finally:
            # Restore normal provider selection for subsequent tests.
            storage.set_provider_for_tests(None)

    # Verify the explicit MySQL bootstrap path inserts missing rows without destructive replacement.
    replace_source = inspect.getsource(storage.MySQLStorageProvider.bootstrap_players)
    # Require the destructive unconditional ledger truncation to be gone from the player write path.
    assert "DELETE FROM casino_ledger" not in replace_source, "player document replacement must not truncate the ledger"
    # Require insert-only compatibility semantics for every supplied player row.
    assert "INSERT IGNORE INTO casino_players" in replace_source
    # Require one explicit transaction with rollback protection around the bounded inserts.
    assert "start_transaction" in replace_source and "connection.commit()" in replace_source and "connection.rollback()" in replace_source
    # Read the MySQL load path to prove reads no longer seed or commit player rows.
    load_source = inspect.getsource(storage.MySQLStorageProvider.load_players)
    # Require the public read path to contain no write, seed, or commit statement.
    assert "INSERT" not in load_source and "_seed_players" not in load_source and "connection.commit()" not in load_source

    # Model the narrow MySQL cursor behavior without opening a network connection. (STORAGE-008, issue #431)
    class PlayerInsertCursor:
        # Retain the owning fake connection for transactional row changes.
        def __init__(self, connection):
            # Store the connection that owns statements, rows, and the failure seam.
            self.connection = connection

        # Execute only the bounded insert statement accepted by bootstrap_players.
        def execute(self, statement, parameters):
            # Record every statement so the test can reject hidden table-wide mutations.
            self.connection.statements.append(statement)
            # Count this candidate insert before evaluating the deterministic failure seam.
            self.connection.execute_count += 1
            # Raise on the configured insert so rollback must restore earlier rows.
            if self.connection.fail_on_execute == self.connection.execute_count:
                # Simulate one ordinary connector failure without exposing credentials or SQL values.
                raise RuntimeError("synthetic player insert failure")
            # Require every executed statement to remain the insert-if-missing operation.
            assert statement.startswith("INSERT IGNORE INTO casino_players")
            # Unpack the normalized player fields bound by the production provider.
            player_id, display_name, player_type, balance, created_at, updated_at, status = parameters
            # Insert only an absent identifier so an existing wallet row is never overwritten.
            if player_id not in self.connection.rows:
                # Persist the candidate row in the fake transactional table.
                self.connection.rows[player_id] = (display_name, player_type, balance, created_at, updated_at, status)

    # Model the transaction lifecycle used by the MySQL provider.
    class PlayerInsertConnection:
        # Initialize one fake durable table and optional deterministic failure point.
        def __init__(self, rows, fail_on_execute=None):
            # Copy the initial durable rows so caller-owned fixtures cannot be mutated.
            self.rows = dict(rows)
            # Retain the insert number that should fail, or no failure when absent.
            self.fail_on_execute = fail_on_execute
            # Start with no executed player inserts.
            self.execute_count = 0
            # Record statements for bounded-SQL assertions.
            self.statements = []
            # Start without an active transaction snapshot.
            self.snapshot = None
            # Track every transaction lifecycle decision.
            self.started = self.committed = self.rolled_back = self.closed = False

        # Start one explicit transaction before any supplied row is inserted.
        def start_transaction(self):
            # Record transaction start for the acceptance assertion.
            self.started = True
            # Snapshot durable rows so rollback can prove atomic restoration.
            self.snapshot = dict(self.rows)

        # Return the cursor bound to this transaction.
        def cursor(self):
            # Build one lightweight cursor for the production method.
            return PlayerInsertCursor(self)

        # Commit the complete insert batch.
        def commit(self):
            # Record the terminal success decision.
            self.committed = True

        # Restore the pre-call table after any insert failure.
        def rollback(self):
            # Restore every row from the transaction snapshot.
            self.rows = dict(self.snapshot)
            # Record the terminal rollback decision.
            self.rolled_back = True

        # Close the operation-scoped connection.
        def close(self):
            # Record mandatory cleanup for success and failure paths.
            self.closed = True

    # Preserve one existing wallet row that a stale document must never overwrite.
    existing_row = ("Human", "human", 8123.0, "created", "updated", "active")
    # Build a successful fake connection over the existing durable row.
    success_connection = PlayerInsertConnection({"human": existing_row})
    # Construct the real provider without calling an external database.
    success_provider = storage.MySQLStorageProvider()
    # Replace readiness with an inert seam because schema behavior is tested separately.
    success_provider.ensure_ready = lambda: None
    # Return the successful fake connection for this one provider call.
    success_provider.connect = lambda: success_connection
    # Submit one stale existing player and one genuinely missing player.
    success_provider.bootstrap_players({"players": [{"player_id": "human", "display_name": "Stale Human", "type": "human", "balance": 999999.0, "created_at": "stale", "updated_at": "stale", "status": "suspended"}, {"player_id": "new_player", "display_name": "New Player", "type": "guest", "balance": 250.0, "created_at": "created", "updated_at": "updated", "status": "active"}]})
    # Require transaction, commit, cleanup, and no rollback on the successful batch.
    assert success_connection.started and success_connection.committed and success_connection.closed and not success_connection.rolled_back
    # Require the stale existing wallet row to remain byte-for-byte unchanged.
    assert success_connection.rows["human"] == existing_row
    # Require the missing row to be inserted without deleting any durable row.
    assert success_connection.rows["new_player"][0] == "New Player" and len(success_connection.rows) == 2
    # Require every observed statement to remain bounded and delete-free.
    assert success_connection.statements and all("DELETE FROM" not in statement for statement in success_connection.statements)

    # Build a failing fake connection that rejects the second supplied insert.
    failure_connection = PlayerInsertConnection({"human": existing_row}, fail_on_execute=2)
    # Construct a separate real provider for failure-path isolation.
    failure_provider = storage.MySQLStorageProvider()
    # Replace readiness with the same inert schema seam.
    failure_provider.ensure_ready = lambda: None
    # Return the deterministic failing connection for the next provider call.
    failure_provider.connect = lambda: failure_connection
    # Start protected failure evidence so the expected connector error is observed.
    try:
        # Submit two missing rows so the first insert must be undone when the second fails.
        failure_provider.bootstrap_players({"players": [{"player_id": "first_new", "display_name": "First New", "type": "guest", "balance": 10.0}, {"player_id": "second_new", "display_name": "Second New", "type": "guest", "balance": 20.0}]})
        # Fail explicitly if the provider swallowed the simulated connector error.
        raise AssertionError("bootstrap_players must preserve the original insert failure")
    # Accept only the deterministic connector failure from the fake cursor.
    except RuntimeError as error:
        # Require the original error rather than an unrelated cleanup failure.
        assert str(error) == "synthetic player insert failure"
    # Require rollback and cleanup without a commit after the partial batch failed.
    assert failure_connection.started and failure_connection.rolled_back and failure_connection.closed and not failure_connection.committed
    # Require rollback to restore the exact pre-call player table.
    assert failure_connection.rows == {"human": existing_row}

    # Read the public creation path to prove it no longer performs a whole-document rewrite.
    create_source = inspect.getsource(players.create_player)
    # Strip comment text so the check inspects executable statements rather than prose about them.
    create_statements = "\n".join(line.split("#", 1)[0] for line in create_source.splitlines())
    # Require the explicit row-scoped provider call that holds the wallet lock on both providers.
    assert "insert_player" in create_statements
    # Require the destructive whole-document rewrite to be gone from the executable path.
    assert "save_players" not in create_statements
    # Require the retired ambiguous method to be absent from the provider contract and implementations.
    assert not hasattr(storage.StorageProvider, "save_players") and not hasattr(storage.JsonStorageProvider, "save_players") and not hasattr(storage.MySQLStorageProvider, "save_players")
    # Require the retired empty-check seam to be absent so bootstrap cannot reintroduce a read-before-write race.
    assert not hasattr(storage.StorageProvider, "has_players") and not hasattr(storage.JsonStorageProvider, "has_players") and not hasattr(storage.MySQLStorageProvider, "has_players")


# Prove client-supplied table rules cannot escape their declared domain into payout math. (issue #404)
def run_table_rule_authority():
    # Import the single descriptor-owned request boundary under test.
    from casino.core.game_rules import coerce_request
    # Import the validation envelope every rejection must use.
    from casino.errors import ValidationError

    # Collect the hostile values that previously reached settlement math unchecked.
    hostile = [
        # Reject the unbounded natural payout that allowed a one-hand balance mint.
        ("/api/v1/games/blackjack/settings", "blackjack_payout", 1000000),
        # Reject a negative payout that would invert the settlement direction.
        ("/api/v1/games/blackjack/settings", "blackjack_payout", -5),
        # Reject the oversized shoe that allocated billions of card strings.
        ("/api/v1/games/blackjack/settings", "decks", 100000000),
        # Reject a non-numeric shoe size that previously raised an unhandled ValueError.
        ("/api/v1/games/blackjack/settings", "decks", "x"),
        # Reject a truthy string standing in for a boolean switch.
        ("/api/v1/games/blackjack/settings", "dealer_hits_soft_17", "yes"),
        # Reject the negative commission that inflated every banker win.
        ("/api/v1/games/baccarat/settings", "banker_commission", -1000),
        # Reject the unbounded tie payout that minted balance on a tie.
        ("/api/v1/games/baccarat/settings", "tie_payout", 1e9),
        # Reject a tie behaviour the engine does not implement.
        ("/api/v1/games/baccarat/settings", "tie_behavior", "lose"),
        # Reject non-finite input before it can reach money arithmetic.
        ("/api/v1/games/baccarat/settings", "banker_commission", float("inf")),
    ]
    # Drive every hostile value through the shared validator.
    for route, key, value in hostile:
        # Start protected logic so a missing rejection is reported precisely.
        try:
            # Attempt the update against an empty rules mapping.
            coerce_request(route, {key: value})
            # Fail loudly when the hostile value was accepted.
            raise AssertionError(f"{key} accepted out-of-domain value {value!r}")
        # Accept only the published validation envelope.
        except ValidationError:
            # Continue to the next hostile case.
            pass

    # Verify legitimate published table offers still apply unchanged.
    accepted = coerce_request("/api/v1/games/blackjack/settings", {"blackjack_payout": 1.5, "decks": 6, "late_surrender": False})
    # Require each accepted rule to persist with its supplied value.
    assert accepted == {"blackjack_payout": 1.5, "decks": 6, "late_surrender": False}
    # Verify baccarat's published commission and tie payout still apply.
    accepted_baccarat = coerce_request("/api/v1/games/baccarat/settings", {"banker_commission": 0.05, "tie_payout": 8})
    # Require both baccarat rules to persist with their supplied values.
    assert accepted_baccarat == {"banker_commission": 0.05, "tie_payout": 8}
    # Verify keys the game does not declare are ignored rather than persisted.
    ignored = coerce_request("/api/v1/games/blackjack/settings", {"house_edge": 0, "blackjack_payout": 1.2})
    # Preserve unknown compatibility keys for the handler allowlist to ignore.
    assert ignored == {"house_edge": 0, "blackjack_payout": 1.2}

    # Verify each settings route actually routes through the validator rather than assigning raw body
    # values. Without this, reverting a route to `rules[key] = body[key]` would leave every assertion
    # above still passing, because they only exercise the helper in isolation.
    for module_name, marker in (("casino.games.blackjack.api", "blackjack"), ("casino.games.baccarat.api", "baccarat")):
        # Import the game's route module to read its registration source.
        module = __import__(module_name, fromlist=["register"])
        # Read the registration function that owns the settings route.
        register_source = inspect.getsource(module.register)
        # Isolate the settings handler body from the surrounding route registrations.
        settings_body = register_source.split(f'"/api/v1/games/{marker}/settings"')[1].split("@router.")[0]
        # Strip comments so prose mentioning the old pattern cannot satisfy the check.
        settings_statements = "\n".join(line.split("#", 1)[0] for line in settings_body.splitlines())
        # Require only the descriptor-derived allowlist at the final persistence boundary.
        assert "declared_fields" in settings_statements, f"{marker} settings route must use descriptor fields"
        # Require the retired duplicated validator to stay absent.
        assert "apply_rule_updates" not in settings_statements, f"{marker} settings route still uses retired validation"
        # Require the unvalidated direct assignment to be gone.
        assert "rules[key] = body[key]" not in settings_statements, f"{marker} settings route still assigns raw body values"

    # Read the central dispatch source that must validate before every governed settings handler.
    from casino.router import Router
    # Require the descriptor boundary on the real executable dispatch path.
    dispatch_source = inspect.getsource(Router.dispatch)
    # Prove central request coercion cannot be removed while per-game tests remain green.
    assert "game_rules.coerce_request" in dispatch_source

    # Verify the legacy v1 add-money route now carries the guest freeze and a bounded amount. (#410)
    from casino.app import build_router
    # Read the router construction source that owns every v1 and v2 route handler.
    add_money_source = inspect.getsource(build_router)
    # Isolate the add-money handler body from the surrounding route registrations.
    handler = add_money_source.split('"/api/v1/players/(?P<player_id>[^/]+)/add-money"')[1].split("@router.")[0]
    # Require the session context so the handler can identify a guest at all.
    assert "context" in handler
    # Require the same guest freeze the v2 token route enforces.
    assert "is_guest" in handler and "Guest trial balances cannot be increased" in handler
    # Require the shared bounded money gate rather than a bare float conversion.
    assert "require_amount" in handler
