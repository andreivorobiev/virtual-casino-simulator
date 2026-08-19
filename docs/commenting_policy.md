# Commenting policy

Repository comments document purpose and engineering intent. They are not a syntax transcript and are never generated to meet a density ratio.

## First-party Python and JavaScript headers

Every tracked first-party `.py` and `.js` file carries these two exact lines at its language-valid header position:

```text
Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
SPDX-License-Identifier: Apache-2.0
```

Python uses `# ` and JavaScript uses `// ` prefixes. A shebang remains line one, and a Python encoding cookie remains in its legal first-or-second-line position. The copyright text comes verbatim from `NOTICE`; `LICENSE` remains the authoritative Apache-2.0 license text. Vendored third-party source under `web/vendor/` retains its upstream notices and is excluded from first-party header insertion.

Every active source file also has a substantive module docstring or leading comment that states its purpose. An empty or docstring-only `__init__.py` package marker may remain license-only rather than carrying invented prose.

## Useful comments

Keep comments that explain why code exists, an invariant, a failure mode, a money-safety rule, a deliberate deviation, or issue context. Remove comments that merely repeat an import, assignment, branch, loop, or return. Generated filler and placeholders are prohibited even when a file has few other comments.

HTML, CSS, YAML, OpenAPI, and Markdown use readable section-level comments where their syntax permits them. JSON uses adjacent Markdown documentation because JSON has no comment syntax.

## Enforcement and migration

Run:

```bash
python scripts/check_file_headers.py --check
```

The gate fails closed for a missing, partial, duplicate, conflicting, or misplaced header; a displaced shebang; invalid Python syntax or encoding; missing file purpose; or any known filler template. Alongside the fixed phrases, it recognizes the complete generated families `Set … to the value needed for the next operation.` and `Define the … function used by this module.` without matching useful prose that happens to share one word.

`scripts/comment_filler_baseline.json` records the remaining generated-family debt per tracked file. The #713 baseline starts at 1,027 comments: 672 assignment narrations and 355 function narrations. Normal checks require exact source-to-ledger agreement, while the Comment Density workflow compares the candidate ledger with its merge/base parent and rejects every per-file increase or newly positive path. Cleanup slices may only reduce or remove ledger entries; they may not transfer debt between files.

`--write` is available only with one or more explicit tracked path boundaries and proves Python executable-token equivalence or exact JavaScript reconstruction before writing the entire selected set. `scripts/check_comment_density.py` remains only as a compatibility entry point to this same gate; no density threshold is enforced.
