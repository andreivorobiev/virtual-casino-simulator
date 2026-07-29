# Game Catalog Governance

GitHub issue #81 established the one-time integration interface for expanding the simulator from six games to at least twenty. A playable game owns its catalog metadata in `modules/<game-id>.json`; shared runtime, shell, validator, and long-suite files discover that metadata and must not gain a new hardcoded game allowlist.

## Current reconciliation

The v0.9.5.30 release line retains 46 catalog-discovered playable game descriptors, fail-closed affected-game Browser qualification, the route-free shared settlement-adapter foundation, exact 138-browser full-catalog qualification, all-game desktop control-reachability gate, governed Acey-Deucey spread pricing, accepted runtime-inert settings rule-schema and coercion foundations, and deterministic four-shard Browser qualification workflow. Pull-request selection may omit only dedicated cases owned by unaffected catalog games; shared, unknown, protected-main, release, and authorized formal inputs retain complete coverage. The historical `GAME_CATALOG_TARGET = 20` value remains a release-readiness floor and reporting target, not a cap and not an instruction to add another catalog mechanism.

Issues #73, #77, and #66 therefore should not be read as an active command to add duplicate game-registration infrastructure. Their current shared-architecture meaning is:

- #73 remains the game-portfolio umbrella for catalog quality, per-game completion evidence, and any future game expansion beyond the installed set.
- #77 remains the serialized shared-integration lane for collision-prone catalog files, descriptor promotion, requirements/test discovery, compatibility metadata, and acceptance evidence.
- #66 remains the broad program epic that ties game catalog work to multi-user, storage, operations, and release-readiness boundaries.

Count-based completion alone does not close a game leaf or umbrella issue. A game can be descriptor-discovered while still needing richer interaction, reload/recovery, reduced-motion, accessibility, localization, or product-quality evidence on its own issue.

## Source boundaries

- `modules/<game-id>.json` owns the game id, ordering, canonical browser route, labels, categories, backend registration callable, frontend module/export/readiness metadata, long-suite driver, lobby presentation, contracts, and module revision.
- `modules/module-manifest.json` remains the #104 canonical aggregate version interface. It owns packaged-release context and module revisions; it is not a second game catalog.
- `casino.config.GAMES` is the loaded runtime view of module-owned descriptors. Backend registration, API metadata, frontend registration, validators, and tests consume this view.
- `/api/v1/casino/games` and `/api/v1/casino/state` preserve their existing `games` arrays and add catalog/frontend metadata plus current and target counts.
- `casino/core/request_player.py` and the router bind every `/api/v1/games/*` request to the authenticated player's session before a game handler runs.

## Rule-setting descriptors

Any catalog game that registers a `POST` route ending in `/settings` must declare a `game.rules` object in its module descriptor. The catalog validator registers each backend against an in-memory router without opening a listener, then requires exact parity between the discovered route and `rules.settings_route`.

The descriptor contains:

- `settings_route`: the exact frozen game settings route.
- `defaults`: a `module:callable` engine default-state factory.
- `defaults_key`: the nested key containing rules, or an empty string when rules are top-level state.
- `fields`: the settable rule names and their domains.
- `kind`: one of `bool`, `enum`, `int`, or `number`.
- `values`: the non-empty closed vocabulary for an enum.
- `min` and `max`: inclusive finite bounds required together for numeric rules.
- `allocates: true`: marks a value that controls allocation, iteration, or comparable resource use and therefore requires a finite maximum.
- `settles: true`: marks a value used by settlement math and therefore requires an enum or finite lower and upper bounds.
- `default`: an exceptional documented fallback only when existing engine code already supplies that fallback outside its default-state object.

The validator rejects unknown schema keys, unsafe semantic flags, inverted or non-finite bounds, invalid engine defaults, undeclared settings routes, descriptors without matching routes, and multiple settings routes owned by one descriptor. Internal callable references and rule schemas are stripped from the public game catalog.

The v0.9.5.30 release line retains behavior-neutral helpers for internal schema lookup, deterministic declared-field discovery, and pure request coercion. On an exact descriptor-owned settings path, the coercer canonicalizes finite numeric strings and numbers, requires exact booleans and closed enum members, applies inclusive bounds, preserves unknown keys for the existing handler allowlist, and never mutates the caller-owned mapping. On every undeclared path, it returns the original request object unchanged.

The first two #433 slices remain runtime-inert. Existing handler validation is still the request authority because the router does not call the coercion helper. A separately reviewed follow-up must obtain the outstanding product approval, mount descriptor enforcement centrally, remove hand-written rule lists, update frozen-contract documentation, and prove read-side state recovery. Descriptors and pure helpers by themselves must never be treated as runtime enforcement or a change to frozen `/api/v1` behavior.

## #77 shared-file ownership

The #77 owner coordinates changes to the collision surfaces that can break every worker if edited independently:

- `modules/module-manifest.json` and any descriptor promotion that changes the installed catalog.
- `docs/requirements/requirements.json` and its generated view.
- `tests/run_tests.py`, long-suite discovery, visual-matrix registration, compatibility matrices, and catalog validators.
- Shared shell/router/catalog documentation that changes how all games are discovered or navigated.

Individual game workers should stay game-local until #77 explicitly releases a shared-integration slice. They should not create a second hardcoded catalog, edit global navigation allowlists, or allocate permanent requirement IDs outside the approved registry process.

## Adding an isolated game

An isolated game or catalog revision slice should:

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
