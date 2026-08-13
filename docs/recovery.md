# Encrypted recovery gate

Requirements `MYSQL-006`, `TOOL-004`, and `TEST-049` define the repository-side recovery boundary for issue #205. This packet supplies fail-closed tooling, evidence contracts, and synthetic validation only. It does not verify current provider state, configure or purchase a destination, transfer a live backup, restore a live database, alter a VM, or release cutover.

## Recovery layers

- Application rollback repoints only to an immutable predecessor whose manifest accepts the already-applied MySQL schema. It does not reverse schema or data.
- Migration and data recovery use the forward-only #204 catalog plus one exact encrypted logical recovery point. There is no generic down migration, history edit, mark-applied escape hatch, or ambient-target restore.
- The `MYSQL-008` bridge binds recovery context to the actual clean runtime schema: schema `2` must carry the exact two-migration prefix digest and schema `3` must carry the complete three-migration digest. Cross-version prefix/full-chain pairs, schema `1`, future, dirty, applying, gapped, or foreign chains fail closed.
- Full-VM recovery is provider-owned disaster recovery. A completed provider snapshot does not prove application-consistent logical backup or clean-target restore and cannot replace this gate.

## Wallet document corruption

Requirement `STORAGE-014` makes the fake-money wallet document a fail-closed boundary. A missing JSON `players.json` may use the reviewed first-run bootstrap, but invalid UTF-8, invalid or duplicate-key JSON, an invalid player collection, duplicate player identifiers, and non-finite, negative, sub-cent, coerced, or out-of-range balances never select defaults. Wallet reads, bootstrap, player updates, game-action snapshots, debits, credits, refunds, and settlements stop with the fixed `Wallet storage requires operator recovery` diagnostic before balance, ledger, or action-journal mutation. MySQL row decoding uses the same public diagnostic while leaving database state unchanged.

The JSON provider preserves the authoritative corrupt file byte-for-byte and creates one adjacent content-addressed `players.json.corrupt-<sha256>` forensic copy. Repeated reads of identical bytes reuse that exact artifact; the application never repairs, deletes, or replaces either copy automatically. Operators must stop mutation traffic, retain both files, verify the artifact digest, recover `players.json` from an independently verified backup or audited reconstruction, and validate its complete player identities and exact-cent balances offline before atomically restoring it. After restoration, run storage readiness plus focused wallet and ledger checks before reopening traffic. If a verified source is unavailable, or MySQL returns the same recovery diagnostic, keep the service held and use the separately governed backup/restore or provider-repair process; never delete the corrupt document to trigger default wallets.

## Provider evidence interface

Provider status is accepted only as an externally produced, sanitized, signed `casino-provider-backup-evidence-v1` object. Its exact allowlist is `schema`, `completed`, `completed_at`, `verified_at`, `cost_included`, and `evidence_hmac_sha256`. Completion and inclusion in the already approved VM cost must both be true, completion and verification must be ordered, and both must be no more than 24 hours old. Provider, account, instance, backup, address, and object identifiers are prohibited.

The repository never signs provider evidence. The provider read-only verifier owns a distinct key role. Actual current provider evidence remains an external #205 blocker.

## Logical backup boundary

The dump wrapper is a preconfigured executable invoked with an argv containing only its executable path. It receives only the explicit text-to-text mapping stored at the operator-owned `CASINO_RECOVERY_PROCESS_ENV_PATH`; the recovery process does not forward its parent environment. The wrapper must read its own private connection configuration and emit a logical dump on stdout. Credentials and target identifiers never appear in arguments, repository files, evidence, or diagnostics.

The process-environment JSON, key material, signed evidence, and wrapper configuration must be owner- or root-owned outside the release and least-readable; on Linux, use mode `0600` or a stricter equivalent. The staging root must also be owner-private, contain encrypted artifacts only, and reject shared or broadly readable locations.

Plaintext flows only from dump stdout into bounded authenticated encryption memory. No plaintext dump file is created. The artifact format is `casino-aes-256-gcm-chunked-v1`: each at-most-64-KiB record uses AES-256-GCM with a fresh random nonce prefix, monotonic record counter, strict public header, record identity and lengths, and prior-record chain as authenticated data. A separately authenticated terminal record binds count, plaintext size, plaintext digest, and complete ordering chain.

The authenticated public context has exactly five fields: full release Git SHA, canonical application version, #204 MySQL schema version, #204 migration-chain SHA-256, and an opaque source-target HMAC. Extra fields fail closed.

## Destination adapter and trust boundary

`scripts/recovery.py` loads one operator-installed zero-argument adapter factory from `CASINO_RECOVERY_ADAPTER`. The adapter owns destination transport and clean-target observation; the repository assumes no provider and creates no paid service. Adapter configuration, credentials, and destination identifiers stay outside Git.

Every adapter operation must implement its own bounded connection and transfer timeouts in addition to the repository's process watchdog. An adapter without explicit transport bounds is not acceptable for live evidence.

The destination authority uses a key independent from encryption, manifest, provider, and restore evidence. It signs exact ciphertext checksum and length, durable completion, off-instance status, acknowledgement time, and retention. The source manifest must pair with that exact signed acknowledgement, including its digest, timestamp, and retention. The destination also signs exact manifest commit and download receipts. A source manifest key cannot forge destination completion.

Encrypted local staging is removed only after both artifact and manifest acknowledgements. Failed upload or manifest acknowledgement retains encrypted staging for explicit retry or quarantine; partial dump, nonzero dump, and timeout remove the incomplete ciphertext. A successful restore removes its downloaded encrypted staging copy after compatibility proof.

## Retention and alerts

Each destination acknowledgement must commit between 7 and 35 days of retention. The recovery gate alerts and fails closed when:

- provider completion or verification exceeds 24 hours;
- a logical recovery point exceeds 24 hours;
- destination retention is expired;
- any transfer, checksum, keyed digest, header, record tag, terminal chain, manifest, acknowledgement, or receipt is absent or mismatched; or
- backup or restore process timing exceeds its configured whole-stream timeout.

Retention deletion is destination-owned and is not performed by this repository packet.

## Clean-target restore

Restore requires an independently signed `casino-clean-restore-authorization-v1` object. It must bind one opaque target HMAC, an exact empty-state digest, zero existing tables, and explicit `clean_target=true`, `empty_target=true`, `disposable=true`, and `ambient_target=false` semantics. Authorization expires within one hour. The repository never creates, drops, clears, or overwrites a target.

The encrypted artifact is downloaded into encrypted staging, checked against its signed manifest and destination acknowledgement, and fully authenticated without output before the restore wrapper starts. The no-argument restore wrapper then receives only independently authenticated chunks. A changed chunk releases no bytes from that chunk. Any post-start decryption, terminal, pipe, child, timeout, or verification failure kills and reaps the tracked child and returns a mandatory target-quarantine result. Previously emitted authenticated chunks may have changed only the disposable target; that target can never be used for cutover.

After wrapper success, a separately authorized verifier must sign exact artifact, empty-target authorization, release, schema version, migration chain, #204 structural schema digest, and representative synthetic persistence compatibility. RPO is recomputed from manifest completion to signed restore start; RTO is recomputed from signed restore start to completion. Caller-supplied timing integers are not trusted.

## Key roles

Five independent high-entropy roles are mandatory and pairwise reuse is rejected:

1. AES-256 artifact encryption;
2. source recovery-manifest HMAC;
3. destination acknowledgement verification HMAC;
4. provider read-only evidence verification HMAC; and
5. clean-target authorization/result HMAC.

Keys are external base64 values, never command arguments. Configuration objects have fixed redacted representations and raw process, adapter, path, parser, driver, and cryptographic exceptions are not emitted.

## Operator sequence and external holds

1. Install the packaged recovery dependency with `python -m pip install ".[recovery]"` (or the deployment system's equivalent exact declared extra); candidate and publication workflows install this same extra before smoke verification.
2. Install and review a no-argument dump wrapper, restore wrapper, destination adapter with bounded transport timeouts, owner-private encrypted-only staging root, and least-privilege child environment outside Git; keep every key, evidence, environment, and wrapper configuration file owner- or root-owned and mode `0600` or stricter on Linux.
3. Supply exact release/schema context and five independent keys externally.
4. Run `python scripts/recovery.py backup`; store the emitted sanitized signed manifest separately.
5. Run `python scripts/recovery.py check` with current signed provider evidence, the exact manifest, and its destination acknowledgement.
6. Prepare a newly created empty disposable target outside the live environment and obtain independent signed authorization.
7. Run `python scripts/recovery.py restore`; quarantine the target on any nonzero result.
8. Preserve only sanitized evidence containing computed age, RPO, RTO, digests, schema version, release version, and pass/fail state.

Actual current provider verification, a separately approved off-instance destination, a real completed transfer, and a real clean-target restore remain required before #205 can be accepted. No DNS, TLS, firewall, public listener, service, live schema, deployment, #201 cutover, #206, or #209 action is authorized here.
