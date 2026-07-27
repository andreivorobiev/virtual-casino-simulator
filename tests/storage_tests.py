# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
# Import required dependency so tests can inspect provider implementation details.
import inspect
# Import required dependency so thread and process ledger calls can overlap safely.
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
# Import environment access so live provider routing can be scoped and restored safely.
import os
# Import required dependency so test data can be written outside the real data directory.
import tempfile
# Import required dependency so isolated JSON provider paths are platform-safe.
from pathlib import Path

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

    # Accept one transient message without retaining any sensitive field.
    def send(self, message):
        # Count the invocation while deliberately discarding the payload.
        self.calls += 1


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
            # Persist default players through the provider-backed players service.
            players.save_players(players.default_players())
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
            # Persist audio settings through the provider-backed settings service.
            saved = settings.save_audio_settings({"master_enabled": False, "voice_volume": 0.4})
            # Verify settings writes merge with defaults and normalize booleans/floats.
            assert saved["master_enabled"] is False and saved["voice_volume"] == 0.4
            # Read settings back through the provider document store.
            reloaded = settings.audio_settings()
            # Verify settings persisted in the provider document.
            assert reloaded["master_enabled"] is False and reloaded["voice_volume"] == 0.4
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
        provider.save_players(players.default_players())
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
        storage.JsonStorageProvider(recovery_root).save_players(players.default_players())
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
        provider.save_players(players.default_players())
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

    # Load the checksum-verified canonical migration catalog.
    migrations, expected, minimum, catalog_sha256 = mysql_migrations.load_catalog()
    # Join exact driver statements for lightweight structural assertions.
    joined = "\n".join(statement for migration in migrations for statement in migration.statements)
    # Verify every expected application table is present in the canonical migrations.
    assert all(table in joined for table in ("casino_schema_versions", "casino_players", "casino_ledger", "casino_history", "casino_documents"))
    # Verify exact-only schema compatibility is versioned independently at migration two.
    assert expected == minimum == 2 and len(catalog_sha256) == 64
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
    # Read the storage-enforced action transaction implementation source.
    action_source = inspect.getsource(storage.MySQLStorageProvider.transact_ledger_once)
    # Verify action replay lookup occurs after a wallet row lock in one explicit transaction.
    assert "FOR UPDATE" in action_source and "action_scope" in action_source and "action_key" in action_source
    # Verify identity, wallet balance, and ledger event commit in the same provider method.
    assert "UPDATE casino_players" in action_source and "INSERT INTO casino_ledger" in action_source and "connection.commit()" in action_source
    # Read runtime readiness source after migration ownership moved out of the provider.
    runtime_source = inspect.getsource(storage.MySQLStorageProvider.ensure_ready)
    # Require only the read-only compatibility verifier at runtime.
    assert "verify_runtime_compatibility" in runtime_source
    # Reject every DDL or migration-state DML verb from runtime readiness.
    assert all(fragment not in runtime_source.upper() for fragment in ("CREATE ", "ALTER ", "DROP ", "INSERT ", "UPDATE ", "DELETE "))


# Exercise real MySQL persistence, domain documents, and concurrent ledger locking.
def run_mysql_live_provider_path():
    # Import representative provider-backed domains only when live MySQL was requested.
    from casino.bots import profiles
    # Import the data root used to derive stable provider document keys.
    from casino.config import DATA_DIR
    # Import core services whose JSON-shaped state must no longer create hybrid files.
    from casino.core import auth, autoplay, feedback, invitations, ledger, mail, one_time_tokens, players, state_store, storage
    # Import OAuth persistence only inside the explicitly requested disposable MySQL gate.
    from casino.core.oauth.persistence import FLOW_DOCUMENT_KEY, FLOW_SECRET_DOCUMENT_KEY, OAuthFlowRecord, OAuthFlowRepository, PersistentIdentityLinkRepository
    # Import the conflict envelope expected when a destructive player replacement is refused. (#402)
    from casino.errors import ConflictError
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
        # Seed fresh private-beta player rows through the provider abstraction.
        players.save_players(players.default_players())
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
        # Capture the wallet balance before overlapping atomic debits.
        starting_balance = players.get_player("human")["balance"]
        # Execute independent MySQL transactions concurrently against one wallet row.
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Materialize all futures so every debit either commits or fails the test.
            events = list(executor.map(lambda index: ledger.debit("human", 1, "MYSQL_CONCURRENT_DEBIT", "storage", f"mysql_concurrent_{index}", {"index": index}), range(20)))
        # Verify row locking prevented lost updates across concurrent connections.
        assert players.get_player("human")["balance"] == starting_balance - 20
        # Verify each committed transaction produced one unique append-only ledger event.
        assert len({event["ledger_id"] for event in events}) == 20
        # Execute 25 duplicate calls through two independent spawned processes.
        with ProcessPoolExecutor(max_workers=2) as executor:
            # Materialize every duplicate result so cross-process failures surface.
            action_results = list(executor.map(_mysql_action_worker, range(25)))
        # Verify all processes received the same immutable ledger event.
        assert len({ledger_id for _, ledger_id, _ in action_results}) == 1
        # Verify the unique action identity committed exactly once across processes.
        assert sum(1 for _, _, replayed in action_results if replayed is False) == 1
        # Verify the wallet absorbed only one three-token debit from 25 calls.
        assert players.get_player("human")["balance"] == starting_balance - 23
        # Preserve the workflow's default provider selector around the focused token proof.
        previous_provider_name = os.environ.get("CASINO_STORAGE_PROVIDER")
        # Route parent issue and read operations through the injected MySQL provider.
        os.environ["CASINO_STORAGE_PROVIDER"] = "mysql"
        # Start protected live evidence so the workflow selector is always restored.
        try:
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
        # Require the destructive whole-document replacement to fail closed while history exists.
        try:
            # Attempt the replacement that previously truncated the ledger as a silent side effect.
            players.save_players(players.default_players())
            # Fail the case explicitly when the guarded replacement unexpectedly succeeded.
            raise AssertionError("player document replacement must refuse to run over committed ledger history")
        # Accept only the published conflict envelope from the fail-closed guard.
        except ConflictError:
            # Require the ledger to be intact after the refusal so nothing was partially deleted.
            assert any(row["ledger_id"] == guard_debit["ledger_id"] for row in ledger.read_recent("human", 10))
    # Always clear provider injection after the live integration test.
    finally:
        # Restore normal provider selection for later API or browser suites.
        storage.set_provider_for_tests(None)


# Prove player creation never destroys committed money history or reverts concurrent balances. (issue #402)
def run_player_creation_preserves_ledger():
    # Import the public player and ledger services plus storage injection helpers.
    from casino.core import ledger, players, storage
    # Import the conflict type expected when a destructive replacement is refused.
    from casino.errors import ConflictError

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
            # Seed the default player document so a known wallet exists.
            players.save_players(players.default_players())
            # Move money BEFORE the next player is created. The original defect survived CI precisely
            # because every existing fixture seeded players before writing any ledger rows.
            debit = ledger.debit("human", 40, "TEST_CREATE_PLAYER_DEBIT", "storage", "round_create", {})
            # Capture the committed post-transaction balance for the reversion check.
            balance_after_debit = players.get_player("human")["balance"]
            # Verify the debit actually committed before the player write under test.
            assert debit["balance_after"] == balance_after_debit
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

    # Verify the MySQL replacement path now refuses to destroy money history instead of truncating it.
    replace_source = inspect.getsource(storage.MySQLStorageProvider.save_players)
    # Require the destructive unconditional ledger truncation to be gone from the player write path.
    assert "DELETE FROM casino_ledger" not in replace_source, "player document replacement must not truncate the ledger"
    # Require an explicit fail-closed guard so the operation cannot proceed over committed history.
    assert "casino_ledger" in replace_source and "ConflictError" in replace_source
    # Read the public creation path to prove it no longer performs a whole-document rewrite.
    create_source = inspect.getsource(players.create_player)
    # Strip comment text so the check inspects executable statements rather than prose about them.
    create_statements = "\n".join(line.split("#", 1)[0] for line in create_source.splitlines())
    # Require the row-scoped provider call that holds the wallet lock on both providers.
    assert "ensure_player" in create_statements
    # Require the destructive whole-document rewrite to be gone from the executable path.
    assert "save_players" not in create_statements


# Prove client-supplied table rules cannot escape their declared domain into payout math. (issue #404)
def run_table_rule_authority():
    # Import the shared declarative validator under test.
    from casino.core.validation import apply_rule_updates
    # Import the per-game rule domains that the settings routes enforce.
    from casino.games.baccarat.api import RULE_DOMAIN as BACCARAT_RULES
    # Import the blackjack domain alongside it for the same coverage.
    from casino.games.blackjack.api import RULE_DOMAIN as BLACKJACK_RULES
    # Import the validation envelope every rejection must use.
    from casino.errors import ValidationError

    # Collect the hostile values that previously reached settlement math unchecked.
    hostile = [
        # Reject the unbounded natural payout that allowed a one-hand balance mint.
        (BLACKJACK_RULES, "blackjack_payout", 1000000),
        # Reject a negative payout that would invert the settlement direction.
        (BLACKJACK_RULES, "blackjack_payout", -5),
        # Reject the oversized shoe that allocated billions of card strings.
        (BLACKJACK_RULES, "decks", 100000000),
        # Reject a non-numeric shoe size that previously raised an unhandled ValueError.
        (BLACKJACK_RULES, "decks", "x"),
        # Reject a truthy string standing in for a boolean switch.
        (BLACKJACK_RULES, "dealer_hits_soft_17", "yes"),
        # Reject the negative commission that inflated every banker win.
        (BACCARAT_RULES, "banker_commission", -1000),
        # Reject the unbounded tie payout that minted balance on a tie.
        (BACCARAT_RULES, "tie_payout", 1e9),
        # Reject a tie behaviour the engine does not implement.
        (BACCARAT_RULES, "tie_behavior", "lose"),
        # Reject non-finite input before it can reach money arithmetic.
        (BACCARAT_RULES, "banker_commission", float("inf")),
    ]
    # Drive every hostile value through the shared validator.
    for spec, key, value in hostile:
        # Start protected logic so a missing rejection is reported precisely.
        try:
            # Attempt the update against an empty rules mapping.
            apply_rule_updates({key: value}, {}, spec)
            # Fail loudly when the hostile value was accepted.
            raise AssertionError(f"{key} accepted out-of-domain value {value!r}")
        # Accept only the published validation envelope.
        except ValidationError:
            # Continue to the next hostile case.
            pass

    # Verify legitimate published table offers still apply unchanged.
    accepted = apply_rule_updates({"blackjack_payout": 1.5, "decks": 6, "late_surrender": False}, {}, BLACKJACK_RULES)
    # Require each accepted rule to persist with its supplied value.
    assert accepted == {"blackjack_payout": 1.5, "decks": 6, "late_surrender": False}
    # Verify baccarat's published commission and tie payout still apply.
    accepted_baccarat = apply_rule_updates({"banker_commission": 0.05, "tie_payout": 8}, {}, BACCARAT_RULES)
    # Require both baccarat rules to persist with their supplied values.
    assert accepted_baccarat == {"banker_commission": 0.05, "tie_payout": 8}
    # Verify keys the game does not declare are ignored rather than persisted.
    ignored = apply_rule_updates({"house_edge": 0, "blackjack_payout": 1.2}, {}, BLACKJACK_RULES)
    # Require only the declared rule to be written through.
    assert ignored == {"blackjack_payout": 1.2}

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
        # Require the shared declarative validator on the executable path.
        assert "apply_rule_updates" in settings_statements, f"{marker} settings route must validate rules"
        # Require the unvalidated direct assignment to be gone.
        assert "rules[key] = body[key]" not in settings_statements, f"{marker} settings route still assigns raw body values"

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
