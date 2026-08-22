<!-- Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Storage provider conformance

This package is the executable provider-independent storage contract for `STORAGE-025` and
`TEST-257`. A backend is complete only when one isolated harness registers it and the unchanged
A-J inventory passes without provider branches, capability skips, weakened assertions, or residue.

## Harness contract

Each harness implements `create()`, `reset_fast()`, and `destroy()`, declares whether its target
supports true concurrent execution, and owns a hard total time budget. Every case receives only the
public `StorageProvider` contract. `supports_true_concurrency` may select the size of a real thread
wave; it never removes a call, case, or assertion.

The early Phase-A head registers only the temporary-directory JSON harness. Disposable MySQL and
PostgreSQL registrations join after their accepted provider integration; they must create one
isolated schema, fast-reset it between groups, and destroy the schema and account on every terminal
path. Missing reviewed reachability variables may suppress creation of an unavailable database
harness, but they cannot skip behavior after a harness is registered.

## Unchanged inventory

- A: documents, strict recovery, atomic mutation, path translation, and a payload of at least 1 MiB.
- B: players, duplicate behavior, missing identities, and wallet normalization reports.
- C: ledger arithmetic, rejection atomicity, bounds, ordering, filtering, and economics.
- D: a gapless public player sequence. Because the public event shape intentionally hides internal
  database sequence columns, adjacency means append order plus exact `balance_before` to predecessor
  `balance_after` continuity.
- E: exactly-once application, byte-equivalent replay, lookup, and changed-fingerprint conflict.
- F: history append order, limits, filters, and schema metadata.
- G: real threaded wallet, document, and same-key schedules with exact final state.
- H: reset and visibility contexts plus rollback after a caller fails mid-sequence.
- I: fresh-equivalent reset followed by the small group-A contract again.
- J: declared `casino.errors` domain failures with no native target, credential, SQL, or query detail.

Run the early focused gate with:

```powershell
python -m unittest tests.storage_conformance.test_json_conformance tests.storage_conformance.test_import_boundaries
```

The run prints one provider/group timing section and fails when the provider's hard total budget is
reached. The harness destroys its synthetic target after both passing and failing cases.
