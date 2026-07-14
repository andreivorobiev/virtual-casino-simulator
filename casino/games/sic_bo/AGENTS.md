# AGENTS.md - Sic Bo module

Scope future changes to the isolated `sic_bo` game unless the #77 integration owner explicitly releases shared catalog files.

## Rules

- Read the root `AGENTS.md`, this module's `README.md`, and `INTEGRATION.md` before editing.
- Preserve the documented 50-position Massachusetts Sic Bo profile or version and document an intentional rules change.
- Keep this package independent of every other game package.
- Route every wager and returned-credit movement through `casino/core/ledger.py`; never mutate a balance directly.
- Preserve stable `action_id` conflict detection, ledger action keys, prepared state, and reload recovery.
- Treat authenticated request context as authoritative; caller-supplied player IDs never override it.
- Keep authoritative dice generation on the server with injectable deterministic test seams.
- Reuse the shared #97 motion scope for browser reveal timing and dispose it on every route exit.
- Keep every visible and accessible frontend string in the paired EN/RU game domains.
- Reference issue #88 and existing cross-cutting requirement IDs until #77 allocates permanent Sic Bo IDs.
- Preserve dense adjacent-purpose comments for every meaningful executable Python and JavaScript line.

## Validation

Run the focused engine/service/API/frontend suites, the game driver smoke, repository rules, contracts, module boundaries, requirements, versions, and comment density. Shared catalog registration, central browser discovery, the visual-matrix row, and acceptance screenshots remain #77-owned.
