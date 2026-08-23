-- Finalize DDL-free runtime grants only after exact schema-five migration success.
\set ON_ERROR_STOP on
\connect virtual_casino

-- Refuse finalization unless every checksum-control and application table exists.
SELECT COUNT(*) = 10 AND COUNT(*) FILTER (WHERE tablename IN ('casino_schema_migrations', 'casino_schema_migration_state', 'casino_players', 'casino_ledger', 'casino_history', 'casino_documents', 'casino_game_action_receipts', 'casino_game_action_claims', 'casino_game_action_epoch_state', 'casino_sessions')) = 10 AS schema_complete FROM pg_catalog.pg_tables WHERE schemaname = 'public' \gset
\if :schema_complete
\else
\echo 'PostgreSQL runtime grants refused: schema is incomplete'
\quit 5
\endif

-- Permit only ordinary application reads and row mutations on reviewed schema objects.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO casino_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO casino_runtime;

-- Keep future migration-created objects least-privilege without granting DDL authority.
ALTER DEFAULT PRIVILEGES FOR ROLE casino_migrate IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO casino_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE casino_migrate IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO casino_runtime;

-- Explicitly remove every schema and database creation capability from runtime.
REVOKE CREATE ON SCHEMA public FROM casino_runtime;
REVOKE CREATE, TEMPORARY ON DATABASE virtual_casino FROM casino_runtime;
