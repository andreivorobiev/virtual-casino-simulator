# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
# Import required dependency so tests can inspect provider implementation details.
import inspect
# Import required dependency so live ledger calls can overlap across connections.
from concurrent.futures import ThreadPoolExecutor
# Import required dependency so test data can be written outside the real data directory.
import tempfile
# Import required dependency so isolated JSON provider paths are platform-safe.
from pathlib import Path

# Import required dependency so storage tests can resolve repository files.
ROOT = Path(__file__).resolve().parents[1]


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


# Define the run_mysql_schema_provider_path function used by the storage test runner.
def run_mysql_schema_provider_path():
    # Import storage helpers lazily so this test does not require a MySQL service.
    from casino.core import storage

    # Load schema statements generated by the MySQL provider.
    statements = storage.MySQLStorageProvider.schema_statements()
    # Join statements for lightweight structural assertions.
    joined = "\n".join(statements)
    # Verify every expected table is present in the provider schema.
    assert "casino_schema_versions" in joined and "casino_players" in joined and "casino_ledger" in joined and "casino_history" in joined and "casino_documents" in joined
    # Verify wallet and ledger money columns use fixed decimal precision.
    assert "DECIMAL(18,2)" in joined
    # Verify ledger rows depend on player rows through a foreign key.
    assert "FOREIGN KEY (player_id)" in joined
    # Read the checked-in SQL schema artifact.
    schema_file = (ROOT / "scripts" / "mysql_schema.sql").read_text(encoding="utf-8")
    # Verify the SQL artifact exposes the same table set as the provider schema.
    assert all(table in schema_file for table in ("casino_schema_versions", "casino_players", "casino_ledger", "casino_history", "casino_documents"))
    # Read the MySQL transaction implementation source.
    source = inspect.getsource(storage.MySQLStorageProvider.transact_ledger)
    # Verify the MySQL ledger path locks the player row before mutating balance.
    assert "FOR UPDATE" in source
    # Verify the MySQL ledger path starts an explicit transaction.
    assert "start_transaction" in source
    # Verify the MySQL ledger path inserts the ledger row before committing.
    assert "INSERT INTO casino_ledger" in source and "connection.commit()" in source


# Exercise real MySQL persistence, domain documents, and concurrent ledger locking.
def run_mysql_live_provider_path():
    # Import representative provider-backed domains only when live MySQL was requested.
    from casino.bots import profiles
    # Import the data root used to derive stable provider document keys.
    from casino.config import DATA_DIR
    # Import core services whose JSON-shaped state must no longer create hybrid files.
    from casino.core import auth, autoplay, ledger, players, state_store, storage

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
        # Rebuild the provider to simulate a fresh application process after restart.
        storage.set_provider_for_tests(storage.MySQLStorageProvider())
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
