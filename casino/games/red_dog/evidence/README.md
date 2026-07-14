# Issue #84 evidence record

Evidence class: integration pending. Nothing in this directory is labeled `after_pass`.

## Isolated evidence

- Deterministic engine tests cover consecutive, pair, three-of-a-kind, spread win/loss, call, raise, and payout math.
- Controller tests cover session precedence, exact replay, conflicting action-id reuse, ordered ledger settlement, and reload recovery.
- Frontend contract tests cover EN/RU key and placeholder parity, localized card labels, retained retry IDs, shared card primitives, stable selectors, responsive/reduced-motion CSS, and timer absence.
- The OpenAPI file documents the additive state, deal, call, and raise surface with standard envelopes.
- The game-local long driver uses only public actions and is ready for descriptor discovery.

## Isolated validation on 2026-07-14

The branch was prepared from `origin/main` at `0a1ebc2d7d034bb855ad968215bc61adcd18f4c9`. The following checks passed from the clean worker tree:

- `python -m unittest discover -s casino/games/red_dog/tests -p "test_*.py"` — 21 tests.
- `node casino/games/red_dog/tests/frontend_module_tests.mjs`.
- `node --check web/games/red_dog.js`.
- `python verify_rules.py` — 32 repository rule checks.
- `python scripts/validate_contracts.py`.
- `python scripts/validate_module_boundaries.py`.
- `python scripts/validate_requirements.py` — 420 registered requirements.
- `python scripts/validate_versions.py` — packaged version and 20 existing module revisions.
- `python scripts/validate_game_catalog.py` — seven currently registered games.
- `python scripts/check_comment_density.py` — 99.9 percent with no Red Dog warning.
- `git diff --check`.

The contract, requirement, version, and catalog totals intentionally describe the pre-integration shared registries. They do not claim Red Dog discovery or acceptance.

## Acceptance still owned by #77

Valid browser acceptance requires the descriptor, aggregate version, permanent requirements, compatibility metadata, catalog route, test discovery, visual row, and authenticated shared shell to land together through issue #77. That lane must capture screenshots from the integrated head for both locales at 1920x1080, 1440x900, 1024x900, and 390x844, then record branch, commit, surface, state, locale, viewport, and path in each sidecar.

The expected matrix surface is `red_dog`; expected states are `ready`, `spread_decision`, `pair_settled`, `consecutive_push`, `third_card_settled`, and `route_restored`.
