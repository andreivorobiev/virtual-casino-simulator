# Game Catalog Governance

GitHub issue #81 establishes the one-time integration interface for expanding the simulator from six games to at least twenty. A playable game owns its catalog metadata in `modules/<game-id>.json`; shared runtime, shell, validator, and long-suite files discover that metadata and must not gain a new hardcoded game allowlist.

## Source boundaries

- `modules/<game-id>.json` owns the game id, ordering, canonical browser route, labels, categories, backend registration callable, frontend module/export/readiness metadata, long-suite driver, lobby presentation, contracts, and module revision.
- `modules/module-manifest.json` remains the #104 canonical aggregate version interface. It owns packaged-release context and module revisions; it is not a second game catalog.
- `casino.config.GAMES` is the loaded runtime view of module-owned descriptors. Backend registration, API metadata, frontend registration, validators, and tests consume this view.
- `/api/v1/casino/games` and `/api/v1/casino/state` preserve their existing `games` arrays and add catalog/frontend metadata plus current and target counts.
- `casino/core/request_player.py` and the router bind every `/api/v1/games/*` request to the authenticated player's session before a game handler runs.

## Adding an isolated game

An isolated game slice should:

1. Add `modules/<game-id>.json` with a unique `game.id`, `sort_order`, `/games/<game-id>` route, primary category and category list.
2. Declare `backend.register` as `package.module:callable`; the callable accepts the shared router and registers the game's frozen or additive API surface.
3. Declare `frontend.module`, `frontend.export`, and a stable `frontend.ready_testid`; add locale-owned labels and lobby copy in `translations` when required.
4. Declare `tests.long_driver` as `tests.game_drivers.<game-id>:play`. The driver accepts `(client, index)`, performs one complete ledger-backed game scenario, and returns only after its assertions pass.
5. Keep contracts and source paths in the normal top-level module descriptor fields so catalog validators discover them without duplicated metadata.
6. Bump the game module revision in its descriptor and the #104 aggregate manifest. Report packaged application release impact as `None` unless release-artifact work is explicitly assigned.
7. Run `python scripts/validate_game_catalog.py`, module boundaries, contracts, requirements, versions, API, browser, and the relevant long-suite smoke.

The shared catalog validator rejects duplicate ids, invalid routes/categories, missing canonical revisions, broken backend or driver imports, missing frontend exports/readiness selectors, and absent contracts. Individual game workers should not edit `casino/app.py`, `web/app.js`, validator allowlists, or `tests/long_suites.py` merely to register their game.

## Browser and visual expectations

The shell derives navigation, lobby cards, search text, and categories from catalog metadata. The canonical browser route is `/games/<game-id>` and must restore through direct navigation, reload, Back, and Forward. Each new browser-visible game still requires its own `tests/visual/visual_matrix.json` surface row and after-pass evidence under `docs/visual_design_standard.md`.
