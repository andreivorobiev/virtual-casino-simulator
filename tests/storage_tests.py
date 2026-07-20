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
    from casino.core import auth, autoplay, ledger, mail, one_time_tokens, players, state_store, storage

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
    # Always clear provider injection after the live integration test.
    finally:
        # Restore normal provider selection for later API or browser suites.
        storage.set_provider_for_tests(None)
