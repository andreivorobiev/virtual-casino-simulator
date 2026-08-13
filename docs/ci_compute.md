# Pull-request compute routing

`TOOL-017` keeps the historical required status contexts stable while avoiding work that cannot add evidence for a documentation-only pull request.

## Long Suite 100

The `Long Suite 100` workflow first asks the GitHub changed-files API for every path in the pull request. `scripts/long_suite_scope.py` returns `SKIP` only when the nonempty path set is entirely documentation or release metadata. Empty responses, unknown paths, malformed output, API failures, and non-pull-request events fail closed to `RUN`.

When the decision is `SKIP`, all four shard jobs remain skipped and the exact `long_suite_100` aggregate job succeeds from the explicit scope result. When the decision is `RUN`, every shard must succeed before that same aggregate job succeeds. Branch protection therefore keeps one unchanged required context and cannot confuse omitted compute with missing evidence.

## Unpublished release candidates

An unpublished candidate built for a GitHub pull request consumes exact-head results from the sibling `ci`, `contract_tests`, `module_boundaries`, and `docs` required contexts. It still packages the candidate and runs copied-release smoke coverage. The optimized mode rejects local, manual, protected-main, release-event, tagged, and rollback-manifest invocations; those paths retain the complete canonical validation sequence.

## Acceptance evidence

Issue #710 closes only from a documentation-only pull request where the scope job reports `SKIP`, all four Long Suite workers are skipped, the unchanged `long_suite_100` aggregate context is green, and the unpublished candidate succeeds without repeating sibling validators. The exact hosted run identifiers and timings belong on the issue before closure so this runbook remains independent of transient workflow IDs.
