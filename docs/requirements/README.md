# Requirement source ownership

`requirements.json` remains the compatibility aggregate consumed by existing validators,
documentation generators, and release tooling. It is generated; do not edit it directly.

- `requirements-spine.json` owns repository-wide and non-game requirements.
- `games/<game-id>.json` owns requirements whose permanent prefixes are declared by
  `modules/<game-id>.json`.
- `python scripts/assemble_requirements.py --write` rebuilds the aggregate.
- `python scripts/assemble_requirements.py --check` fails closed on source or byte drift.

Every new game receives its own shard. Existing requirement IDs remain permanent, and moving
an entry between source files never changes its identifier or historical fields.

Issue #434 established this source boundary; existing focused runner cases remain valid
supplemental evidence, but a new game no longer needs a central Python-suite registration.
