# Scratch Cards isolated game slice

Issue: [#87](https://github.com/andreivorobiev/virtual-casino-simulator/issues/87)

Parents: #66 and #73. Shared integration owner: #77. Catalog foundation: #81.

## Requirement traceability

Issue #87 does not yet have a coordinator-allocated permanent requirement block. This worker does not invent or add permanent IDs. The descriptor's `SCRATCH` prefix is a provisional integration proposal only; #77 must allocate the final game-specific block before acceptance.

Existing impacted requirements read before implementation are:

- Module/API: `CORE-008`, `CORE-009`, `CORE-010`, `CORE-011`, `CORE-012`, `CORE-021`, `CORE-022`, and `API-001`.
- Session/privacy: `AUTH-001`, `AUTH-004`, `SESSION-005`, `USER-003`, and `TOKEN-004`.
- Ledger: `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, and `LEDGER-023`.
- UI/i18n: `I18N-001`, `I18N-002`, `UX-001`, `UX-006`, `UX-009`, and `UX-010`.
- Discovery/tests: `TEST-012`, `TEST-039`, and `TEST-042`.

#77 should allocate five permanent Scratch Cards acceptance dimensions covering rules, authenticated reload-safe API state, ledger/retry safety, EN/RU responsive UI, and catalog/contract/browser/long-suite/visual evidence. No candidate ID numbers are claimed here.

## Explicit rules profile

One card contains nine prize cells. Revealing all nine wins when exactly three cells display the same prize amount; the credited payout equals that matched prize. A loss contains three pairs and three single prizes, so it cannot accidentally contain a third match.

The server-owned toy profile uses these outcome weights:

| Result | Weight | Prize |
| --- | ---: | ---: |
| No win | 70% | 0x wager |
| Match | 18% | 1x wager |
| Match | 7% | 2x wager |
| Match | 3% | 5x wager |
| Match | 1% | 10x wager |
| Match | 1% | 25x wager |

The theoretical return is 82%. This is an explicit local-simulator profile, not a real-money product or fairness certification. The public API accepts no seed, forced outcome, prize board, or payout.

## Deterministic and private model

- Production uses `secrets.randbelow`; focused tests inject a bounded deterministic source.
- The complete prize board is prepared once and persisted before the wager debit.
- The persisted purchase intent retains the private board across a post-debit crash; player-visible wager details never repeat covered values.
- `public_card()` emits a prize only for an explicitly revealed position and omits covered prize values, multipliers, entropy rolls, request fingerprints, and action records. Player-visible ledger details retain only non-outcome retry metadata and never contain the covered board.
- Player state retains one current card, partial revealed positions, bounded scratch-action replay records, and twenty recent settled cards.

## Session, ledger, and exactly-once design

The API accepts the shared router context and gives `resolved_player_id` or `bound_player_id` absolute precedence over body/query compatibility fields. All state, ledger scans, card IDs, and recent history are scoped to that resolved player. Unknown and other-player card IDs share the same not-found response.

Starting a card:

1. Normalize the approved play-token wager and required `client_request_id`.
2. Derive a player-scoped card ID and semantic request fingerprint.
3. Persist the full private card as a `purchasing` intent.
4. Apply one `SCRATCH_CARD_WAGER_DEBIT` with action key `scratch:<card_id>:wager` through `casino/core/ledger.py`.
5. Recover the pre-debit private ticket intent after any interrupted save and publish a fully masked `ready` card.

Scratching and settlement:

1. Normalize the required `action_id` and unique zero-based positions.
2. Persist action fingerprint and the union of revealed positions.
3. On the ninth reveal, persist `settling` plus the completion identity before any credit.
4. If the card wins, apply one `SCRATCH_CARD_PAYOUT_CREDIT` with action key `scratch:<card_id>:payout`.
5. Persist terminal state and expose all nine prizes, payout, outcome, and net.

Identical retries return existing state while their private card remains retained. An older committed purchase identity whose board aged out fails closed without rerolling or moving tokens. Reusing an action identity with changed meaning also fails closed. A losing card never creates a zero-value ledger event. The read-before-write adapter uses one process lock because this repository is a local single-process simulator; multi-process deployment would require a storage-level unique idempotency constraint.

## Browser and primitive decisions

The surface uses semantic prize-cell buttons, stable ARIA names, a polite phase/result region, controls-stage-data hierarchy, paired flat EN/RU resources, game-owned responsive styles, and no game-owned timer. Decorative hover transitions are removed under `prefers-reduced-motion: reduce`, and unmount releases locale subscription and cached player state synchronously.

The #96 card renderer is intentionally not used because scratch tickets are not standard playing cards. The #97 motion timer scope is also unnecessary because reveal persistence is direct and timer-free; this avoids creating a parallel timing primitive.

## #77 integration handoff

The issue-owned descriptor artifact at `codex/tasks/artifacts/issue-87-scratch-cards/scratch_cards.module.proposal.json` proposes `scratch_cards` version `1.0.0`, canonical route `/games/scratch_cards`, existing categories `instant` and `machine`, and reserved sort order `130`. It intentionally remains outside `modules/` so this draft cannot auto-install the game before #77 integration.

#77 must still:

- add `scratch_cards: 1.0.0` to `modules/module-manifest.json` from the then-current accepted base;
- allocate and register permanent game-specific requirement IDs plus generated documentation;
- add the OpenAPI contract to compatibility matrix and digest metadata;
- add the central visual row and any central test-discovery/version revisions;
- run the real copied-deployment catalog/API/browser/long-suite gate;
- capture exact-head `after_pass` EN/RU evidence at all four required viewports.

Proposed visual row: surface `scratch_cards`, route `/games/scratch_cards`, selector `[data-testid='scratch-cards']`, states `ready`, `revealing`, `settled_win`, `settled_no_win`, `reduced_motion`, and `route_restored`; both locales; desktop primary, desktop compact, tablet, and mobile; the standard copy, token-language, layout, hierarchy, responsive, evidence, and catalog gates.

No shared manifest, central requirement registry, compatibility inventory, visual matrix, shell, router, test runner, or generated documentation is changed by this slice.
