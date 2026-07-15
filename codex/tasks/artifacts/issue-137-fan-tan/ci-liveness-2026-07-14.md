# CI Liveness Correction - 2026-07-14

PR #174 head `7c2f09a40a0e91290c8e10f4dc8bcd970229e272` had seven green checks and one failed `long_suite_100` check.

Inspected GitHub Actions run `29375690471`, job `87228544326`. The failure occurred in the existing long-suite browser audio verification, before any Fan-Tan-specific shared integration exists:

```text
AssertionError: Baccarat voice starts 9 below repeats 10
```

This Fan-Tan lane owns only Fan-Tan backend/frontend/resources, focused Fan-Tan tests, the parked issue artifact descriptor, and the game-owned OpenAPI proposal. It must not edit Baccarat, shared long-suite harnesses, central discovery, shared catalog/router files, or #77-owned integration surfaces. This artifact records the liveness inspection and intentionally leaves the unrelated Baccarat audio flake for the owning/shared lane.
