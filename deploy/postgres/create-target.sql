-- Create the fixed PostgreSQL roles and database for the new OCI preview only.
\set ON_ERROR_STOP on
\getenv casino_runtime_password CASINO_POSTGRES_PASSWORD
\getenv casino_migration_password CASINO_POSTGRES_MIGRATION_PASSWORD

-- Refuse missing, short, or reused secrets before any role or database mutation.
SELECT length(:'casino_runtime_password') >= 32 AND length(:'casino_migration_password') >= 32 AND :'casino_runtime_password' <> :'casino_migration_password' AS secrets_valid \gset
\if :secrets_valid
\else
\echo 'PostgreSQL target creation refused: secret policy failed'
\quit 3
\endif

-- Require all three fixed target identities to be absent so reruns fail closed.
SELECT NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname IN ('casino_runtime', 'casino_migrate')) AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'virtual_casino') AS target_absent \gset
\if :target_absent
\else
\echo 'PostgreSQL target creation refused: target already exists'
\quit 4
\endif

-- Create separate ordinary login roles with no cluster-wide administration powers.
CREATE ROLE casino_migrate LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'casino_migration_password';
CREATE ROLE casino_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'casino_runtime_password';

-- Create one migration-owned database so only the migration role can own schema objects.
CREATE DATABASE virtual_casino OWNER casino_migrate ENCODING 'UTF8' TEMPLATE template0;

-- Remove default database access before granting only the two reviewed identities.
REVOKE ALL ON DATABASE virtual_casino FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE virtual_casino TO casino_migrate;
GRANT CONNECT ON DATABASE virtual_casino TO casino_runtime;

-- Enter the new database and remove public schema creation authority.
\connect virtual_casino
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO casino_migrate;
GRANT USAGE ON SCHEMA public TO casino_runtime;
