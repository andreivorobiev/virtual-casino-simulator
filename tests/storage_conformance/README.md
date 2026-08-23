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

The registry always contains the temporary-directory JSON harness plus disposable MySQL and
PostgreSQL harnesses. Each database harness creates one isolated schema, resets mutable state within
that schema between groups, and destroys the schema and generated accounts on every terminal path.
A wholly absent reviewed reachability marker records one explicit skip; a present but incomplete or
invalid marker fails closed before optional-driver import or network access. No harness can skip
behavior after target creation begins.

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
- H: reset and visibility contexts, document-mutation rollback, exact caller-failure preservation,
  and completed reset recovery visibility.
- I: fresh-equivalent reset followed by the small group-A contract again.
- J: declared `casino.errors` domain failures with no native target, credential, SQL, or query detail.

Run the early focused gate with:

```powershell
python -m unittest tests.storage_conformance.test_json_conformance tests.storage_conformance.test_import_boundaries tests.storage_conformance.test_database_harnesses
```

The run prints one provider/group timing section and fails when the provider's hard total budget is
reached. The harness destroys its synthetic target after both passing and failing cases.

The permanent central registration runs with `python tests/run_tests.py --storage`. JSON always
executes. MySQL executes only with the existing exact disposable marker plus complete reviewed
loopback administrator reachability; it creates dedicated synthetic runtime and migration accounts,
uses the accepted migration path once, and bounds its provider pool. PostgreSQL executes only with
`CASINO_POSTGRES_CONFORMANCE_LIVE=CASINO-POSTGRES-1060-LIVE` and the reviewed official binary root
in `CASINO_POSTGRES_TEST_BIN`; it starts one private loopback cluster, applies the accepted migration
catalog, and never selects a persistent service. Both relational harnesses keep credentials out of
reports, reset mutable state within the accepted schema between groups, and verify database,
accounts, process, listener, and filesystem cleanup before returning.
