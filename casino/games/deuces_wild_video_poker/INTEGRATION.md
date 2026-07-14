# Deuces Wild Video Poker integration proposal

Issue: [#92](https://github.com/andreivorobiev/virtual-casino-simulator/issues/92)

Parent program: #66

Game expansion parent: #73

Shared integration owner: #77

This document describes the isolated game slice and its future integration needs. It does not allocate permanent requirements, edit shared acceptance files, or claim that the game is catalog-accepted, release-ready, or approved to merge.

## Isolated descriptor proposal

- Module and game id: `deuces_wild_video_poker`.
- Initial independent module revision: `1.0.0`.
- Reserved catalog order: `180`.
- Canonical browser route: `/games/deuces_wild_video_poker`.
- Additive API root: `/api/v1/games/deuces-wild-video-poker`.
- Browser export and readiness selector: `DeucesWildVideoPokerGame` and `deuces-wild-video-poker`.
- Locale domain: `games/deuces_wild_video_poker`.
- Catalog-discovered long driver: `tests.game_drivers.deuces_wild_video_poker:play`.
- Existing localized categories: `machine`, `cards`, `poker`, and `strategy`; no new shell category is proposed.

The API contract requires an `action_id` on deal, hold, and draw requests. A repeated action with the same canonical payload must replay its durable result. Reusing the same id for a conflicting payload must fail closed. Compatibility `player_id` inputs never override the authenticated session-bound player.

## Proposed permanent requirement block

The following identifiers are proposals for #77 allocation. They are not entries in the permanent requirement registry and must not be reported as `PASS` until the integration owner adds them and maps real-backend acceptance evidence.

| Proposed ID | Proposed requirement | Existing requirement mapping |
| --- | --- | --- |
| `DWVP-001` | Deuces Wild deals five cards, permits one hold-and-draw decision, treats every deuce as wild, and evaluates the documented full-pay outcomes deterministically. | `CARD-001`, `POKER-001`, `POKER-002` |
| `DWVP-002` | Authenticated sessions own isolated reload-safe active and recent rounds, and the canonical route restores without exposing another player's state. | `CORE-018`, `CORE-021`, `CORE-022`, `AUTH-001`, `AUTH-004`, `SESSION-005`, `USER-003`, `TOKEN-004` |
| `DWVP-003` | Every round uses one ledger wager debit and at most one payout credit; identical action retries recover, conflicting reuse fails closed, and insufficient funds cannot leave an actionable round. | `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023`, `MYSQL-002` |
| `DWVP-004` | The game exposes complete English and Russian visible and accessible copy and remains usable across all required viewports with reduced motion and no stale timers. | `CARD-002`, `I18N-001`, `I18N-002`, `TOKEN-001`, `UX-001` through `UX-004`, `UX-006`, `MOTION-001`, `MOTION-002` |
| `DWVP-005` | Catalog, additive contract, module revision, focused tests, authenticated browser coverage, discovered long driver, and visual evidence remain traceable from one accepted head. | `CORE-008`, `CORE-009`, `CORE-011`, `CORE-012`, `CORE-021`, `TEST-039`, `TEST-042` |

`USER-003`, `TOKEN-001`, `TEST-039`, and every proposed `DWVP` entry remain planned until their own acceptance boundaries are satisfied. The existing `MHVP-001` through `MHVP-005` identifiers belong only to Multi-Hand Video Poker and are not reused here.

## Proposed visual-matrix row

Only #77 may add the shared row. The proposed values are:

- Surface id: `deuces_wild_video_poker`.
- Route: `/games/deuces_wild_video_poker`.
- Selector: `[data-testid='deuces-wild-video-poker']`.
- States: `ready`, `choose_holds`, `settled`, `reduced_motion`, and `route_restored`.
- Locales: `en-US` and `ru-RU`.
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`.
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, and `VIS-CATALOG-001`.

If the accepted layout introduces an intentional paytable or history scroll region, #77 must also apply `VIS-SCROLL-001` and `VIS-SCROLL-002`. The existing `shell_lobby` row must show the new catalog card through its `search_filtered` and `category_filtered` states.

## Exact shared integration blockers

The isolated worker must leave these files to #77:

1. `modules/module-manifest.json`: add the accepted `deuces_wild_video_poker` revision and recalculate any shared module revisions from the then-current main branch. Without this entry, `scripts/validate_game_catalog.py` reports `catalog game deuces_wild_video_poker has no canonical module revision`, while `scripts/validate_versions.py` reports both `module manifests missing from aggregate manifest: deuces_wild_video_poker` and `configured games missing canonical module revisions: deuces_wild_video_poker`.
2. `docs/requirements/requirements.json`, `docs/requirements/requirements.md`, and `docs/requirements/requirements_generated.md`: allocate the permanent block, map accepted tests, and regenerate rather than hand-edit generated output.
3. `contracts/compatibility/module-api-matrix.json` and `contracts/compatibility/contract-digests.json`: register the additive contract and its accepted digest.
4. `tests/visual/visual_matrix.json`: add the proposed row only after the exact states and evidence paths are available.
5. Shared API/browser runners and long-suite discovery: change them only if catalog-driven discovery is insufficient; otherwise record the game-specific tests and driver evidence without adding a duplicate allowlist.
6. Shared `application`, `tests`, `docs`, and `contracts` module revisions: compute them at integration time. This proposal reserves no future shared version number.

Because the runtime catalog publishes each descriptor's revision through `modules/module-manifest.json`, the full shared shell and casino catalog cannot provide formal acceptance while that aggregate revision is absent. Focused engine, isolated-router API, frontend, locale-parity, boundary, comment-density, and syntax checks remain valid worker evidence but do not remove this #77 blocker.

## Integration handoff

When #77 explicitly releases this game, rebase the draft branch onto the latest accepted `main`, preserve the game-local commits, add only the shared acceptance commit owned by #77, and run the complete integration gate from that exact head. The pull request remains draft until the coordinator separately accepts the shared evidence; green checks alone do not grant merge approval.
