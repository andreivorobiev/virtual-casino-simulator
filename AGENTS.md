# AGENTS.md - Virtual Casino Simulator repository instructions

These instructions apply to the whole repository unless a nested `AGENTS.md` gives stricter module-specific rules.

## Project goal

The Virtual Casino Simulator is a local fake-money browser casino with isolated game modules, ledger-based wallet accounting, a bot-control plane, admin telemetry, frozen API contracts, numbered requirements, and repeatable tests.

## Source of truth

GitHub is the source of truth after this payload is pushed. Work must happen through issues, branches, pull requests, required checks, and release artifacts.

## Issue triage and priority rules

- `ENGINEERING_PRACTICES.md` is the vendor-neutral engineering policy entry point.
- `docs/issue_prioritization.md` is authoritative for issue priority and label taxonomy.
- Every open issue must have exactly one of `P1`, `P2`, or `P3`.
- `P4` must not be created or used.
- Priority-only work does not authorize implementation, issue closure, merge, deployment, or provider changes.

## Claude and Codex collaboration

- `CLAUDE.md` is Claude Code's repository adapter; it points back to these instructions and the common vendor-neutral policies.
- `docs/claude_codex_work_division.md` defines the default two-agent allocation and handback model.
- Claude may investigate, implement, validate, and create or update pull requests for assigned scope, but Claude must not merge, enable auto-merge, or push protected branches.
- Codex is the coordinator, shared-integration owner, independent reviewer, and sole executor for every repository merge.
- Codex merge ownership does not replace required owner approval, protected-branch rules, exact-head validation, independent acceptance, release gates, deployment authority, or any other safety boundary.

## Persistent agent memory

- All repository agent roles may read `agents/memory/`.
- Only the `engineering-manager` role may propose memory writes, and only after the associated task is complete.
- Memory writes use a normal branch and pull request, pass repository gates, and receive independent review; no agent self-approves a memory edit.
- Memory must never contain secrets, tokens, credentials, personal data, provider payloads, or values from `.env`.
- A memory fact older than 30 days or citing a path changed after its source commit is stale and must be revalidated before use.
- Memory summarizes repository source but never overrides requirements, contracts, protected-branch rules, or release and deployment authority.

## Required workflow

1. Read the relevant requirement IDs before editing.
2. Read the module manifest before editing a module.
3. Read the API contract before touching endpoints or payloads.
4. Make the smallest module-scoped change possible.
5. Add or update tests mapped to requirements.
6. Update module versions when module source changes.
7. Update docs/release notes for formal releases.
8. Run required validations before finalizing.

## Module-boundary rules

- `casino/games/<game>` may import `casino.core`, `casino.errors`, and its own game package.
- `casino/games/<game>` must not import another game package.
- Game modules must not import `casino.bots.strategies`.
- Bot strategy modules may call public game actions through the bot controller or documented APIs.
- Frontend files under `web/games/<game>.js` must not import another game module.
- Shared frontend code belongs under `web/core/`.

## API contract rules

- `/api/v1` is frozen as a compatibility contract.
- Additive optional changes may remain in v1 only when old clients continue to work.
- Breaking changes require `/api/v2` or an explicit compatibility shim.
- API changes must update `contracts/openapi/`, `contracts/compatibility/`, tests, docs, and module versions.
- All API responses must use the standard `{ ok: true, data: ... }` or `{ ok: false, error: ... }` envelope.

## Requirement rules

- Requirement IDs are permanent and must never be reused.
- Do not delete requirements; mark them superseded or retired.
- Every change must reference impacted requirement IDs in the PR.
- Browser-visible behavior changes require browser tests unless explicitly marked manual.
- API behavior changes require API and contract tests.

## Versioning rules

- Each module is versioned independently in `modules/*.json`.
- The packaged application version changes for every release artifact.
- Patch bumps are for compatible fixes.
- Minor bumps are for compatible additions.
- Major bumps are for breaking module/API changes.

## Money and ledger rules

- Bets, tickets, cards, spins, doubles, splits, insurance, refunds, and winnings must go through `casino/core/ledger.py`.
- Game engines may request settlements but must not mutate player balances directly.
- Ledger events must include player, game, round/session ID where applicable, amount, and details.

## Bot rules

- A bot is a controller for a player account.
- A bot is not part of a game module.
- A bot appears only for games where it has a compatible strategy.
- Bot actions must use the same public actions as human/autoplay actions.

## Autoplay rules

- Autoplay is a control-plane feature, not a game-owned loop.
- Stop must prevent new atomic actions from starting.
- Current committed actions may finish safely.
- Autoplay sessions must be visible in Admin.

## Commenting policy

- Every meaningful executable Python and JavaScript line must have an inline or immediately adjacent comment explaining purpose.
- Closing braces, blank lines, pure punctuation, and generated data do not need comments.
- JSON files cannot contain comments; add adjacent Markdown docs when needed.
- HTML/CSS/YAML/OpenAPI files require clear section-level comments where comments are syntactically legal.
- Do not add uncommented executable Python or JavaScript lines.
- When you touch a file, improve comment clarity in that file.

## Visual UI policy

- `docs/visual_design_standard.md` is authoritative for browser-visible layout, wallet, scrolling, hierarchy, responsive behavior, accessibility, and evidence quality.
- `tests/visual/visual_matrix.json` is the machine-readable inventory of required surfaces, states, locales, viewports, and visual gates.
- Read both files before changing browser-visible UI and name the affected matrix rows in the PR.
- Known-failing or before-state screenshots are not acceptance evidence.

## Required validation commands

Run the relevant subset and prefer the full set before PR handoff:

```bash
python scripts/bootstrap_repo.py
python verify_rules.py
python tests/run_tests.py --api
python tests/run_tests.py --browser
python scripts/validate_game_catalog.py
python scripts/validate_contracts.py
python scripts/validate_module_boundaries.py
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/generate_docs.py --check
python scripts/check_comment_density.py
```

`validate_game_catalog.py` and `generate_docs.py --check` are enforced by CI
(`.github/workflows/ci.yml`, `.github/workflows/docs.yml`); a change that skips them can pass this
list locally and still fail the build.

## Definition of done

A change is done only when requirements, contracts, module versions, tests, docs, and release notes are aligned with the code change.
