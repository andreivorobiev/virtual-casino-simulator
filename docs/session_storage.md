# First-class session storage

Requirements `SESSION-014`, `STORAGE-019`, `MYSQL-010`, and `TEST-250` replace the shared authentication-session document with provider-owned per-session rows. This is a compatible storage cutover: cookie names, CSRF validation, native bearer rotation, generation counters, expiry policy, session caps, guest teardown, Admin session control, API envelopes, signup policy, and provider selection remain unchanged.

## Durable authority

The authentication service constructs a complete session and delegates lifecycle ownership to `StorageProvider`. Durable rows contain the opaque session id, one domain-separated SHA-256 bearer digest, user id, CSRF proof, generation, status, timestamps, client family input, and authentication method. Plaintext bearer tokens are stripped before every provider write. A raw token is attached only to the detached result returned by creation or rotation, or to a detached row after an exact caller-supplied digest lookup.

JSON storage keeps one strict atomically replaced file per bearer digest under `data/auth/sessions-v2`. Direct authentication reads only that digest-derived file. Compound cap, account revocation, replacement, and sweep operations hold the existing provider-wide cross-process gate while validating the complete bounded registry; corruption or duplicate identity fails closed without seeding or rewriting authority.

MySQL clean schemas `2`, `3`, and `4` use one independently keyed `casino_documents` row per bearer digest under the private `auth/session/v2/row/` namespace. This removes the hot aggregate row without requiring a database migration. Clean schema `5` uses `casino_sessions`, with primary session identity, unique token-digest, user-activity, and expiry indexes. Lifecycle writes use explicit transactions and row locks; reads use the unique or primary index where available.

## Legacy import and recovery

At first session access, each provider runs a one-shot importer for the retired aggregate `auth/sessions.json` document. The importer validates every source row, derives token digests, strips raw tokens, rejects duplicate token or session identities, publishes independent rows, writes a fixed completion marker, and then retires the aggregate inside the provider's atomic boundary. Once the marker exists, a recreated or corrupt aggregate never regains authority.

Malformed keyed rows, invalid importer markers, inconsistent MySQL indexed columns, or ambiguous row counts return the fixed `Session storage requires operator recovery` conflict. Operators must preserve the evidence and restore only independently verified bytes. Automatic fallback, partial salvage, token regeneration, and funded or authenticated default seeding are prohibited.

## Schema and deployment boundary

Migration `0005_first_class_sessions.json` creates the native table, backfills only keyed compatibility rows, and removes those bridge rows after insertion. The catalog remains `apply_policy=held`; this repository change does not invoke migration tooling, alter production grants, select a provider, or touch a live database. A future schema-five activation requires the separately governed backup, quiesce, grant, drift, restart, and rollback-compatibility packet described in [MySQL migration and DDL-free runtime gate](mysql_migrations.md).

Disposable MySQL tests use synthetic loopback-only databases and identities. Listener-free provider-parity tests exercise deterministic caps, lookup, touch, rotation, revocation, expiry, one-shot import, and simultaneous same-user plus different-user login/logout schedules without exposing bearer material.
