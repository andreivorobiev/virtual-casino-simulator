# Repository start here

This is the root documentation map for the Virtual Casino Simulator. The
filename is retained for compatibility, but this page applies equally to human
contributors, Claude, Codex, and other approved engineering automation.

## Mandatory reading order

Before changing repository or GitHub state, read these files in order:

1. `AGENTS.md` and the closest nested `AGENTS.md` for every file in scope, plus
   `CLAUDE.md` when working through Claude Code.
2. `ENGINEERING_PRACTICES.md` for the common vendor-neutral policy.
3. `docs/engineering_skills.md` for capability and tool routing.
4. `docs/claude_codex_work_division.md` for the Claude-author/Codex-merge model.
5. The assigned GitHub issue, its recent comments, dependencies, and overlapping
   open pull requests.
6. `modules/module-manifest.json` and every affected module manifest.
7. Relevant permanent requirements, contracts, compatibility artifacts, visual
   matrix rows, and specialized policy documents.
8. The task packet, branch ownership, validation plan, and PR template.

GitHub and committed repository artifacts are durable sources of truth. Chat
history and model memory are not. Open PRs are pending proposals; read them for
collision and dependency planning but do not treat them as merged behavior.

## Current release context

- Packaged application release: `0.9.5.30`
- Historical source baseline: `9.1.0`
- Canonical aggregate source: `modules/module-manifest.json`
- Independent source-module revisions: `modules/*.json`

The packaged application release changes only through formal release-artifact
work. Every changed source module updates its independent revision. Never reuse
or overwrite a version owned by an active PR.

## Pending-proposal handling

Open pull requests are pending proposals, not accepted repository state. Before
editing shared generated requirements or module metadata, reconcile every
overlapping PR and choose an explicit dependency order. A later proposal must
either stack on the reviewed exact head or rebase onto the accepted result and
recalculate versions from current `main`. Record transient PR numbers, heads,
and handback state in the affected issue and pull request rather than freezing
them into this evergreen start page.

## How to use the catalog

The generated catalog below links every repository Markdown file except this
root page. The link text is the exact repository path; the description is the
file's first level-one heading. Path groups communicate purpose:

- root files are current repository entry points and release summaries;
- `docs/` contains current policies, guides, game docs, evidence, and historical
  release snapshots;
- `casino/**/AGENTS.md`, `contracts/AGENTS.md`, `tests/AGENTS.md`, and
  `web/AGENTS.md` are scoped instructions;
- `codex/prompts/` and `codex/tasks/` are worker templates, historical packets,
  and handback evidence, not a replacement for current policy;
- module `README.md`, `INTEGRATION.md`, `VALIDATION.md`, and evidence files explain
  local ownership and accepted or proposed evidence;
- `mobile/` contains mobile-shell documentation; and
- `.github/` contains repository contribution templates.

Run `python scripts/generate_docs.py` after adding, deleting, moving, or retitling
a Markdown file. `python scripts/generate_docs.py --check` fails when this catalog
is incomplete or stale.

<!-- BEGIN GENERATED MARKDOWN INDEX -->
## Complete Markdown catalog

Generated from Git's tracked and non-ignored Markdown inventory. Every repository Markdown file except this root index appears exactly once below.

### Repository root

- [`AGENTS.md`](AGENTS.md) — AGENTS.md - Virtual Casino Simulator repository instructions
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Virtual Casino Simulator Architecture
- [`CHANGELOG.md`](CHANGELOG.md) — Changelog
- [`CLAUDE.md`](CLAUDE.md) — Claude repository adapter
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Contributing
- [`ENGINEERING_PRACTICES.md`](ENGINEERING_PRACTICES.md) — Engineering practices
- [`FIRST_PROMPT_FOR_CODEX.md`](FIRST_PROMPT_FOR_CODEX.md) — First prompt for Codex
- [`README.md`](README.md) — Virtual Casino Simulator
- [`RELEASE_NOTES.md`](RELEASE_NOTES.md) — Virtual Casino Simulator v0.9.5.30 Release Notes

### GitHub contribution templates

- [`.github/pull_request_template.md`](.github/pull_request_template.md) — Pull request

### Casino modules and scoped instructions

- [`casino/bots/AGENTS.md`](casino/bots/AGENTS.md) — AGENTS.md - bots module
- [`casino/core/AGENTS.md`](casino/core/AGENTS.md) — AGENTS.md - core module
- [`casino/core/oauth/INTEGRATION.md`](casino/core/oauth/INTEGRATION.md) — Disabled-by-default invite-only OAuth integration for #326
- [`casino/core/oauth/README.md`](casino/core/oauth/README.md) — Disabled-by-default invite-only OAuth runtime
- [`casino/games/acey_deucey/README.md`](casino/games/acey_deucey/README.md) — Acey-Deucey / In-Between game module
- [`casino/games/baccarat/AGENTS.md`](casino/games/baccarat/AGENTS.md) — AGENTS.md - baccarat module
- [`casino/games/big_six_wheel/AGENTS.md`](casino/games/big_six_wheel/AGENTS.md) — AGENTS.md - Big Six Wheel module
- [`casino/games/bingo/AGENTS.md`](casino/games/bingo/AGENTS.md) — AGENTS.md - bingo module
- [`casino/games/blackjack/AGENTS.md`](casino/games/blackjack/AGENTS.md) — AGENTS.md - blackjack module
- [`casino/games/casino_war/evidence/README.md`](casino/games/casino_war/evidence/README.md) — Casino War isolated evidence
- [`casino/games/casino_war/INTEGRATION.md`](casino/games/casino_war/INTEGRATION.md) — Casino War integration record for #77
- [`casino/games/casino_war/README.md`](casino/games/casino_war/README.md) — Casino War isolated slice
- [`casino/games/chuck_a_luck/AGENTS.md`](casino/games/chuck_a_luck/AGENTS.md) — AGENTS.md - Chuck-a-Luck module
- [`casino/games/deuces_wild_video_poker/evidence/README.md`](casino/games/deuces_wild_video_poker/evidence/README.md) — Deuces Wild Video Poker evidence boundary
- [`casino/games/deuces_wild_video_poker/INTEGRATION.md`](casino/games/deuces_wild_video_poker/INTEGRATION.md) — Deuces Wild Video Poker integration proposal
- [`casino/games/deuces_wild_video_poker/README.md`](casino/games/deuces_wild_video_poker/README.md) — Deuces Wild Video Poker
- [`casino/games/dragon_tiger/AGENTS.md`](casino/games/dragon_tiger/AGENTS.md) — AGENTS.md - Dragon Tiger module
- [`casino/games/dragon_tiger/README.md`](casino/games/dragon_tiger/README.md) — Dragon Tiger
- [`casino/games/hi_lo/INTEGRATION.md`](casino/games/hi_lo/INTEGRATION.md) — Hi-Lo integration acceptance for issue #77
- [`casino/games/hi_lo/README.md`](casino/games/hi_lo/README.md) — Hi-Lo game module
- [`casino/games/joker_poker/README.md`](casino/games/joker_poker/README.md) — Joker Poker
- [`casino/games/keno/AGENTS.md`](casino/games/keno/AGENTS.md) — AGENTS.md - keno module
- [`casino/games/let_it_ride/INTEGRATION.md`](casino/games/let_it_ride/INTEGRATION.md) — Let It Ride Integration Record For #77
- [`casino/games/let_it_ride/README.md`](casino/games/let_it_ride/README.md) — Let It Ride
- [`casino/games/multi_hand_video_poker/README.md`](casino/games/multi_hand_video_poker/README.md) — Multi-Hand Video Poker
- [`casino/games/red_dog/evidence/README.md`](casino/games/red_dog/evidence/README.md) — Issue #84 evidence record
- [`casino/games/red_dog/INTEGRATION.md`](casino/games/red_dog/INTEGRATION.md) — Red Dog integration record for #77
- [`casino/games/red_dog/README.md`](casino/games/red_dog/README.md) — Red Dog
- [`casino/games/roulette/AGENTS.md`](casino/games/roulette/AGENTS.md) — AGENTS.md - roulette module
- [`casino/games/scratch_cards/AGENTS.md`](casino/games/scratch_cards/AGENTS.md) — AGENTS.md - Scratch Cards module
- [`casino/games/scratch_cards/README.md`](casino/games/scratch_cards/README.md) — Scratch Cards
- [`casino/games/sic_bo/AGENTS.md`](casino/games/sic_bo/AGENTS.md) — AGENTS.md - Sic Bo module
- [`casino/games/sic_bo/evidence/README.md`](casino/games/sic_bo/evidence/README.md) — Issue #88 browser evidence
- [`casino/games/sic_bo/INTEGRATION.md`](casino/games/sic_bo/INTEGRATION.md) — Sic Bo integration handoff for #77
- [`casino/games/sic_bo/README.md`](casino/games/sic_bo/README.md) — Sic Bo
- [`casino/games/slots/AGENTS.md`](casino/games/slots/AGENTS.md) — AGENTS.md - slots module
- [`casino/games/texas_holdem_practice_table/INTEGRATION.md`](casino/games/texas_holdem_practice_table/INTEGRATION.md) — Texas Hold'em Practice Table integration handoff for #77
- [`casino/games/texas_holdem_practice_table/README.md`](casino/games/texas_holdem_practice_table/README.md) — Texas Hold'em Practice Table
- [`casino/games/texas_holdem_practice_table/VALIDATION.md`](casino/games/texas_holdem_practice_table/VALIDATION.md) — Issue #95 integrated validation evidence
- [`casino/games/three_card_poker/AGENTS.md`](casino/games/three_card_poker/AGENTS.md) — AGENTS.md - Three Card Poker module
- [`casino/games/three_card_poker/README.md`](casino/games/three_card_poker/README.md) — Three Card Poker
- [`casino/operations/README.md`](casino/operations/README.md) — Operations probe foundation

### Agent prompts, task packets, and historical handbacks

- [`codex/prompts/00_repository_bootstrap.md`](codex/prompts/00_repository_bootstrap.md) — Repository Bootstrap Validation Task
- [`codex/prompts/01_first_validation_pr.md`](codex/prompts/01_first_validation_pr.md) — First prompt for Codex
- [`codex/prompts/coordinator.md`](codex/prompts/coordinator.md) — Agent coordinator prompt
- [`codex/prompts/module_admin.md`](codex/prompts/module_admin.md) — Codex task prompt: admin
- [`codex/prompts/module_audio.md`](codex/prompts/module_audio.md) — Codex task prompt: audio
- [`codex/prompts/module_autoplay.md`](codex/prompts/module_autoplay.md) — Codex task prompt: autoplay
- [`codex/prompts/module_baccarat.md`](codex/prompts/module_baccarat.md) — Codex task prompt: baccarat
- [`codex/prompts/module_bingo.md`](codex/prompts/module_bingo.md) — Codex task prompt: bingo
- [`codex/prompts/module_blackjack.md`](codex/prompts/module_blackjack.md) — Codex task prompt: blackjack
- [`codex/prompts/module_bots.md`](codex/prompts/module_bots.md) — Codex task prompt: bots
- [`codex/prompts/module_contracts.md`](codex/prompts/module_contracts.md) — Codex task prompt: contracts
- [`codex/prompts/module_core.md`](codex/prompts/module_core.md) — Codex task prompt: core
- [`codex/prompts/module_docs.md`](codex/prompts/module_docs.md) — Codex task prompt: docs
- [`codex/prompts/module_keno.md`](codex/prompts/module_keno.md) — Codex task prompt: keno
- [`codex/prompts/module_ledger.md`](codex/prompts/module_ledger.md) — Codex task prompt: ledger
- [`codex/prompts/module_roulette.md`](codex/prompts/module_roulette.md) — Codex task prompt: roulette
- [`codex/prompts/module_slots.md`](codex/prompts/module_slots.md) — Codex task prompt: slots
- [`codex/prompts/module_tests.md`](codex/prompts/module_tests.md) — Codex task prompt: tests
- [`codex/prompts/worker_task.md`](codex/prompts/worker_task.md) — Agent worker task prompt
- [`codex/REPOSITORY_BOOTSTRAP_TASK.md`](codex/REPOSITORY_BOOTSTRAP_TASK.md) — Repository Bootstrap Validation Task
- [`codex/tasks/artifacts/current-p1-visual-admin-repair/README.md`](codex/tasks/artifacts/current-p1-visual-admin-repair/README.md) — Current P1 visual and Admin repair evidence
- [`codex/tasks/artifacts/issue-130-joker-poker/README.md`](codex/tasks/artifacts/issue-130-joker-poker/README.md) — Issue #130 Joker Poker Integration Packet
- [`codex/tasks/artifacts/issue-130-joker-poker/validation.md`](codex/tasks/artifacts/issue-130-joker-poker/validation.md) — Validation Notes
- [`codex/tasks/artifacts/issue-132-caribbean-stud/distinct_module_proof.md`](codex/tasks/artifacts/issue-132-caribbean-stud/distinct_module_proof.md) — Issue #132 Distinct Countable Game Proof
- [`codex/tasks/artifacts/issue-132-caribbean-stud/README.md`](codex/tasks/artifacts/issue-132-caribbean-stud/README.md) — Issue #132 Shared Integration Evidence
- [`codex/tasks/artifacts/issue-132-caribbean-stud/validation.md`](codex/tasks/artifacts/issue-132-caribbean-stud/validation.md) — Issue #132 Shared Integration Validation
- [`codex/tasks/artifacts/issue-133-crown-and-anchor/README.md`](codex/tasks/artifacts/issue-133-crown-and-anchor/README.md) — Issue #133 Crown and Anchor Promotion Record
- [`codex/tasks/artifacts/issue-134-let-it-ride/distinct_module_proof.md`](codex/tasks/artifacts/issue-134-let-it-ride/distinct_module_proof.md) — Issue #134 Distinct Module Proof
- [`codex/tasks/artifacts/issue-134-let-it-ride/validation.md`](codex/tasks/artifacts/issue-134-let-it-ride/validation.md) — Issue #134 Validation Notes
- [`codex/tasks/artifacts/issue-135-over-under-7/README.md`](codex/tasks/artifacts/issue-135-over-under-7/README.md) — Issue #135 Over/Under 7 Evidence
- [`codex/tasks/artifacts/issue-136-plinko/README.md`](codex/tasks/artifacts/issue-136-plinko/README.md) — Issue #136 Plinko Integration Evidence
- [`codex/tasks/artifacts/issue-137-fan-tan/ci-liveness-2026-07-14.md`](codex/tasks/artifacts/issue-137-fan-tan/ci-liveness-2026-07-14.md) — CI Liveness Correction - 2026-07-14
- [`codex/tasks/artifacts/issue-137-fan-tan/README.md`](codex/tasks/artifacts/issue-137-fan-tan/README.md) — Issue #137 Fan-Tan Integration Evidence
- [`codex/tasks/artifacts/issue-139-casino-holdem/distinct_module_proof.md`](codex/tasks/artifacts/issue-139-casino-holdem/distinct_module_proof.md) — Issue #139 Distinct Module Proof
- [`codex/tasks/artifacts/issue-139-casino-holdem/README.md`](codex/tasks/artifacts/issue-139-casino-holdem/README.md) — Issue #139 Casino Hold'em Integration Packet
- [`codex/tasks/artifacts/issue-139-casino-holdem/validation.md`](codex/tasks/artifacts/issue-139-casino-holdem/validation.md) — Issue #139 / PR #179 Integration Validation
- [`codex/tasks/artifacts/issue-139-casino-holdem/visual_matrix_proposal.md`](codex/tasks/artifacts/issue-139-casino-holdem/visual_matrix_proposal.md) — Issue #139 Visual Matrix Promotion
- [`codex/tasks/artifacts/issue-140-andar-bahar/distinct_module_proof.md`](codex/tasks/artifacts/issue-140-andar-bahar/distinct_module_proof.md) — Issue #140 Distinct Module Proof
- [`codex/tasks/artifacts/issue-149-acey-deucey/distinctness.md`](codex/tasks/artifacts/issue-149-acey-deucey/distinctness.md) — Issue #149 Distinctness Evidence
- [`codex/tasks/artifacts/issue-149-acey-deucey/validation.md`](codex/tasks/artifacts/issue-149-acey-deucey/validation.md) — Issue #149 isolated validation handoff
- [`codex/tasks/artifacts/issue-72-operations-foundation/README.md`](codex/tasks/artifacts/issue-72-operations-foundation/README.md) — Issue #72 Operations foundation and stacked integration packet
- [`codex/tasks/artifacts/issue-72-operations-foundation/validation.md`](codex/tasks/artifacts/issue-72-operations-foundation/validation.md) — Issue #72 focused validation
- [`codex/tasks/artifacts/issue-85-hi-lo/README.md`](codex/tasks/artifacts/issue-85-hi-lo/README.md) — Issue #85 Hi-Lo handoff and #77 integration evidence
- [`codex/tasks/artifacts/issue-85-hi-lo/validation.md`](codex/tasks/artifacts/issue-85-hi-lo/validation.md) — Issue #85 / #77 integrated validation
- [`codex/tasks/artifacts/issue-91-jacks-or-better-video-poker/README.md`](codex/tasks/artifacts/issue-91-jacks-or-better-video-poker/README.md) — Issue #91 isolated handoff evidence
- [`codex/tasks/artifacts/issue-91-jacks-or-better-video-poker/validation.md`](codex/tasks/artifacts/issue-91-jacks-or-better-video-poker/validation.md) — Issue #91 focused validation
- [`codex/tasks/artifacts/issue-93-three-card-poker/README.md`](codex/tasks/artifacts/issue-93-three-card-poker/README.md) — Issue #93 isolated handoff evidence
- [`codex/tasks/artifacts/issue-93-three-card-poker/validation.md`](codex/tasks/artifacts/issue-93-three-card-poker/validation.md) — Issue #93 focused validation
- [`codex/tasks/artifacts/issue-94-multi-hand-video-poker/README.md`](codex/tasks/artifacts/issue-94-multi-hand-video-poker/README.md) — Issue #94 isolated handoff evidence
- [`codex/tasks/artifacts/issue-94-multi-hand-video-poker/validation.md`](codex/tasks/artifacts/issue-94-multi-hand-video-poker/validation.md) — Issue #94 focused validation
- [`codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/implementation-test-plan.md`](codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/implementation-test-plan.md) — Implementation and Test Plan
- [`codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/README.md`](codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/README.md) — I18n Locale Plan Handback
- [`codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/resource-architecture.md`](codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/resource-architecture.md) — Resource Architecture Proposal
- [`codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/string-inventory.md`](codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/string-inventory.md) — String Inventory Map
- [`codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/README.md`](codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/README.md) — Premium Machine and Draw Game Prerenders
- [`codex/tasks/artifacts/premium-redesign-prerenders/README.md`](codex/tasks/artifacts/premium-redesign-prerenders/README.md) — Premium Casino Redesign Prerenders
- [`codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/README.md`](codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/README.md) — Premium Shell, Lobby, Admin Prerenders
- [`codex/tasks/artifacts/premium-redesign-prerenders/table-games/README.md`](codex/tasks/artifacts/premium-redesign-prerenders/table-games/README.md) — Premium Table Game Prerenders
- [`codex/tasks/auth-mysql-token-admin-users.md`](codex/tasks/auth-mysql-token-admin-users.md) — Codex Task Packet: Admin User Management
- [`codex/tasks/auth-mysql-token-auth-backend.md`](codex/tasks/auth-mysql-token-auth-backend.md) — Codex Task Packet: Auth Backend and Current User APIs
- [`codex/tasks/auth-mysql-token-epic.md`](codex/tasks/auth-mysql-token-epic.md) — Auth, Multi-User, MySQL, Licensing, and Token Model Epic
- [`codex/tasks/auth-mysql-token-frontend-auth.md`](codex/tasks/auth-mysql-token-frontend-auth.md) — Codex Task Packet: Frontend Login, Terms, and Current User Shell
- [`codex/tasks/auth-mysql-token-licensing.md`](codex/tasks/auth-mysql-token-licensing.md) — Codex Task Packet: Licensing and Toy-Simulator Terms
- [`codex/tasks/auth-mysql-token-private-sessions.md`](codex/tasks/auth-mysql-token-private-sessions.md) — Codex Task Packet: Private User Game Sessions
- [`codex/tasks/auth-mysql-token-requirements-contracts.md`](codex/tasks/auth-mysql-token-requirements-contracts.md) — Codex Task Packet: Auth/MySQL Requirements and Contracts
- [`codex/tasks/auth-mysql-token-storage.md`](codex/tasks/auth-mysql-token-storage.md) — Codex Task Packet: Storage Provider and MySQL Schema
- [`codex/tasks/auth-mysql-token-token-model.md`](codex/tasks/auth-mysql-token-token-model.md) — Codex Task Packet: Play Token Terminology
- [`codex/tasks/auth-mysql-token-validation.md`](codex/tasks/auth-mysql-token-validation.md) — Codex Task Packet: Integration Validation
- [`codex/tasks/blackjack-tests-coverage.md`](codex/tasks/blackjack-tests-coverage.md) — Blackjack Tests-First Coverage
- [`codex/tasks/long-parallel-test-suites.md`](codex/tasks/long-parallel-test-suites.md) — Long Parallel Test Suites
- [`codex/tasks/post-implementation-name-alignment.md`](codex/tasks/post-implementation-name-alignment.md) — Post-Implementation Naming Alignment Cleanup Proposal
- [`codex/tasks/premium-implementation-baccarat.md`](codex/tasks/premium-implementation-baccarat.md) — Premium Baccarat Frontend Implementation
- [`codex/tasks/premium-implementation-bingo.md`](codex/tasks/premium-implementation-bingo.md) — Premium Bingo Frontend Implementation
- [`codex/tasks/premium-implementation-blackjack.md`](codex/tasks/premium-implementation-blackjack.md) — Premium Blackjack Frontend Implementation
- [`codex/tasks/premium-implementation-combined-base.md`](codex/tasks/premium-implementation-combined-base.md) — Combined Redesign Implementation Base
- [`codex/tasks/premium-implementation-epic.md`](codex/tasks/premium-implementation-epic.md) — Premium Casino Redesign Implementation Epic
- [`codex/tasks/premium-implementation-foundation.md`](codex/tasks/premium-implementation-foundation.md) — Premium Shared Shell, Lobby, and Visual Foundation Implementation
- [`codex/tasks/premium-implementation-i18n-admin.md`](codex/tasks/premium-implementation-i18n-admin.md) — Premium I18n and Admin Language/Locale Implementation
- [`codex/tasks/premium-implementation-integration-validation.md`](codex/tasks/premium-implementation-integration-validation.md) — Premium Redesign Integration and Visual Validation
- [`codex/tasks/premium-implementation-keno.md`](codex/tasks/premium-implementation-keno.md) — Premium Keno Frontend Implementation
- [`codex/tasks/premium-implementation-roulette.md`](codex/tasks/premium-implementation-roulette.md) — Premium Roulette Frontend Implementation
- [`codex/tasks/premium-implementation-slots.md`](codex/tasks/premium-implementation-slots.md) — Premium Slots Frontend Implementation
- [`codex/tasks/premium-redesign-epic.md`](codex/tasks/premium-redesign-epic.md) — Premium Casino Redesign Prerender Epic
- [`codex/tasks/premium-redesign-i18n-plan.md`](codex/tasks/premium-redesign-i18n-plan.md) — Premium Redesign I18n Resource Plan Task Packet
- [`codex/tasks/premium-redesign-machine-draw-prerenders.md`](codex/tasks/premium-redesign-machine-draw-prerenders.md) — Premium Machine and Draw Game Prerender Task Packet
- [`codex/tasks/premium-redesign-shell-prerenders.md`](codex/tasks/premium-redesign-shell-prerenders.md) — Premium Shell, Lobby, Admin Prerender Task Packet
- [`codex/tasks/premium-redesign-table-game-prerenders.md`](codex/tasks/premium-redesign-table-game-prerenders.md) — Premium Table Game Prerender Task Packet
- [`codex/tasks/TASK_PACKET_TEMPLATE.md`](codex/tasks/TASK_PACKET_TEMPLATE.md) — Agent task packet template

### Contract-scoped instructions

- [`contracts/AGENTS.md`](contracts/AGENTS.md) — AGENTS.md - contracts module

### Policies, guides, game documentation, evidence, and release history

- [`docs/AGENTS.md`](docs/AGENTS.md) — AGENTS.md - docs module
- [`docs/api_contract_freeze.md`](docs/api_contract_freeze.md) — API contract freeze policy
- [`docs/card_poker_primitives.md`](docs/card_poker_primitives.md) — Card and poker primitives
- [`docs/claude_codex_work_division.md`](docs/claude_codex_work_division.md) — Claude and Codex work-division proposal
- [`docs/codex_parallel_workflow.md`](docs/codex_parallel_workflow.md) — Parallel agent workflow
- [`docs/commenting_policy.md`](docs/commenting_policy.md) — Commenting policy
- [`docs/concurrent_browser_qualification.md`](docs/concurrent_browser_qualification.md) — Concurrent browser qualification
- [`docs/coordination/claude.md`](docs/coordination/claude.md) — Claude status
- [`docs/coordination/codex.md`](docs/coordination/codex.md) — Codex status
- [`docs/coordination/README.md`](docs/coordination/README.md) — Agent coordination channel
- [`docs/drafts/ux_design_guidelines_review.md`](docs/drafts/ux_design_guidelines_review.md) — UX design guidelines review packet
- [`docs/drafts/ux_visual_assessment_prompt.md`](docs/drafts/ux_visual_assessment_prompt.md) — UX and visual conformance assessment prompt
- [`docs/drafts/visual_design_guidelines_review.md`](docs/drafts/visual_design_guidelines_review.md) — Visual design guidelines review packet
- [`docs/engineering_skills.md`](docs/engineering_skills.md) — Engineering skills and capability routing
- [`docs/evidence/baccarat/README.md`](docs/evidence/baccarat/README.md) — Baccarat mutation-serialization evidence
- [`docs/evidence/big_six_wheel/README.md`](docs/evidence/big_six_wheel/README.md) — Big Six Wheel evidence status
- [`docs/evidence/bingo/README.md`](docs/evidence/bingo/README.md) — Bingo card-purchase guard evidence
- [`docs/evidence/casino_holdem/README.md`](docs/evidence/casino_holdem/README.md) — Casino Hold'em Evidence
- [`docs/evidence/chuck_a_luck/README.md`](docs/evidence/chuck_a_luck/README.md) — Chuck-a-Luck after-pass evidence
- [`docs/evidence/craps/README.md`](docs/evidence/craps/README.md) — Craps canonical integration evidence
- [`docs/evidence/dragon_tiger/README.md`](docs/evidence/dragon_tiger/README.md) — Dragon Tiger isolated real-backend evidence
- [`docs/evidence/scratch_cards/README.md`](docs/evidence/scratch_cards/README.md) — Scratch Cards evidence status
- [`docs/game_catalog_governance.md`](docs/game_catalog_governance.md) — Game Catalog Governance
- [`docs/game_expansion_integration_sequence.md`](docs/game_expansion_integration_sequence.md) — Game Expansion Integration Sequence
- [`docs/games/acey_deucey.md`](docs/games/acey_deucey.md) — Acey-Deucey
- [`docs/games/andar_bahar.md`](docs/games/andar_bahar.md) — Andar Bahar
- [`docs/games/big_six_wheel.md`](docs/games/big_six_wheel.md) — Big Six Wheel
- [`docs/games/caribbean_stud.md`](docs/games/caribbean_stud.md) — Caribbean Stud
- [`docs/games/casino_holdem.md`](docs/games/casino_holdem.md) — Casino Hold'em
- [`docs/games/chuck_a_luck.md`](docs/games/chuck_a_luck.md) — Chuck-a-Luck game
- [`docs/games/craps.md`](docs/games/craps.md) — Craps isolated game slice
- [`docs/games/crown_and_anchor.md`](docs/games/crown_and_anchor.md) — Crown and Anchor
- [`docs/games/dragon_tiger.md`](docs/games/dragon_tiger.md) — Dragon Tiger
- [`docs/games/fan_tan.md`](docs/games/fan_tan.md) — Fan-Tan
- [`docs/games/joker_poker.md`](docs/games/joker_poker.md) — Joker Poker
- [`docs/games/let_it_ride.md`](docs/games/let_it_ride.md) — Let It Ride
- [`docs/games/over_under_7.md`](docs/games/over_under_7.md) — Over/Under 7
- [`docs/games/plinko.md`](docs/games/plinko.md) — Plinko
- [`docs/games/scratch_cards.md`](docs/games/scratch_cards.md) — Scratch Cards isolated game slice
- [`docs/games/three_card_poker.md`](docs/games/three_card_poker.md) — Three Card Poker isolated game slice
- [`docs/github_codex_migration_plan.md`](docs/github_codex_migration_plan.md) — GitHub and Codex migration plan
- [`docs/github_setup_checklist.md`](docs/github_setup_checklist.md) — GitHub setup checklist
- [`docs/invitation_enrollment.md`](docs/invitation_enrollment.md) — Private invitation enrollment runbook
- [`docs/issue_prioritization.md`](docs/issue_prioritization.md) — Issue prioritization and label policy
- [`docs/legal/privacy.md`](docs/legal/privacy.md) — Private Beta Privacy Notice
- [`docs/legal/README.md`](docs/legal/README.md) — Legal Docs
- [`docs/legal/terms.md`](docs/legal/terms.md) — Private Beta Toy Simulator Terms
- [`docs/local_mysql_setup.md`](docs/local_mysql_setup.md) — Local MySQL 8.4 LTS setup
- [`docs/localization_foundation.md`](docs/localization_foundation.md) — Phase 0 localization foundation
- [`docs/long_test_suites.md`](docs/long_test_suites.md) — Long Casino Test Suites
- [`docs/marketing_customization.md`](docs/marketing_customization.md) — Marketing and brand customization
- [`docs/motion_acceptance_contract.md`](docs/motion_acceptance_contract.md) — Deterministic motion acceptance contract
- [`docs/mysql_connection_pool.md`](docs/mysql_connection_pool.md) — MySQL connection lifecycle
- [`docs/mysql_migrations.md`](docs/mysql_migrations.md) — MySQL migration and DDL-free runtime gate
- [`docs/oauth_invite_only.md`](docs/oauth_invite_only.md) — Invite-only OAuth operations boundary
- [`docs/production_cicd_runbook.md`](docs/production_cicd_runbook.md) — Production CI/CD runbook
- [`docs/production_service.md`](docs/production_service.md) — Production application service
- [`docs/pwa_foundation.md`](docs/pwa_foundation.md) — Offline-safe PWA foundation
- [`docs/recovery.md`](docs/recovery.md) — Encrypted recovery gate
- [`docs/release_artifacts.md`](docs/release_artifacts.md) — Reproducible release artifacts
- [`docs/release_versioning.md`](docs/release_versioning.md) — Release versioning
- [`docs/releases/app/9.1.1/api_contract_freeze.md`](docs/releases/app/9.1.1/api_contract_freeze.md) — API contract freeze policy
- [`docs/releases/app/9.1.1/github_codex_migration_plan.md`](docs/releases/app/9.1.1/github_codex_migration_plan.md) — GitHub and Codex migration plan
- [`docs/releases/app/9.1.1/module_version_matrix.md`](docs/releases/app/9.1.1/module_version_matrix.md) — Module version matrix
- [`docs/releases/app/9.1.1/release_notes.md`](docs/releases/app/9.1.1/release_notes.md) — Changelog
- [`docs/releases/app/9.1.1/requirements_validation_v9_1_0_baseline_redesigned.md`](docs/releases/app/9.1.1/requirements_validation_v9_1_0_baseline_redesigned.md) — Virtual Casino Simulator 9.1.0 Requirements and Validation Report
- [`docs/requirements/requirements.md`](docs/requirements/requirements.md) — Virtual Casino Simulator 9.1.0 Requirements and Validation Report
- [`docs/requirements/requirements_generated.md`](docs/requirements/requirements_generated.md) — Virtual Casino Requirements and Validation
- [`docs/requirements_validation_v9_1.md`](docs/requirements_validation_v9_1.md) — Virtual Casino Simulator 9.1.0 Requirements and Validation Report
- [`docs/requirements_validation_v9_1_redesigned.md`](docs/requirements_validation_v9_1_redesigned.md) — Virtual Casino Simulator 9.1.0 Requirements and Validation Report
- [`docs/restricted_preview_edge.md`](docs/restricted_preview_edge.md) — Restricted-preview edge preparation
- [`docs/restricted_preview_security.md`](docs/restricted_preview_security.md) — Restricted-preview security policy
- [`docs/server_authority_certification.md`](docs/server_authority_certification.md) — Server-Authority and Hostile-Client Certification
- [`docs/transactional_mail_runbook.md`](docs/transactional_mail_runbook.md) — Transactional mail runbook
- [`docs/visual_design_standard.md`](docs/visual_design_standard.md) — Visual Design Standard

### Mobile integration documentation

- [`mobile/ios/App/CapApp-SPM/README.md`](mobile/ios/App/CapApp-SPM/README.md) — CapApp-SPM
- [`mobile/README.md`](mobile/README.md) — Capacitor mobile foundation

### Test-scoped instructions

- [`tests/AGENTS.md`](tests/AGENTS.md) — AGENTS.md - tests module

### Web-scoped instructions

- [`web/AGENTS.md`](web/AGENTS.md) — AGENTS.md - web browser shell
- [`web/assets/fonts/README.md`](web/assets/fonts/README.md) — Native-label font subsets

### site documentation

- [`site/tiltseven/deployment.md`](site/tiltseven/deployment.md) — TiltSeven future publication checklist
- [`site/tiltseven/README.md`](site/tiltseven/README.md) — TiltSeven marketing site
<!-- END GENERATED MARKDOWN INDEX -->
