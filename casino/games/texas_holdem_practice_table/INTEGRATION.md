# Texas Hold'em Practice Table integration handoff for #77

This isolated issue #95 branch intentionally does not create `modules/texas_holdem_practice_table.json`. Current `casino/config.py` discovers every live descriptor containing a `game` object, while version and catalog validators require the same module revision in the forbidden aggregate manifest. The #77 owner must materialize the following proposal and aggregate revision together after rebasing onto the then-accepted `main`.

## Proposed module descriptor

```json
{
  "module": "texas_holdem_practice_table",
  "version": "1.0.0",
  "paths": [
    "casino/games/texas_holdem_practice_table/",
    "web/games/texas_holdem_practice_table.js",
    "web/i18n/en-US/games/texas_holdem_practice_table.json",
    "web/i18n/ru-RU/games/texas_holdem_practice_table.json"
  ],
  "requirements_prefixes": ["THPT"],
  "contracts": ["contracts/openapi/texas_holdem_practice_table.v1.yaml"],
  "game": {
    "id": "texas_holdem_practice_table",
    "sort_order": 200,
    "route": "/games/texas_holdem_practice_table",
    "label": "Texas Hold'em Practice Table",
    "category": "table",
    "categories": ["table", "cards", "poker", "strategy"],
    "backend": {"register": "casino.games.texas_holdem_practice_table.api:register"},
    "frontend": {
      "module": "./games/texas_holdem_practice_table.js",
      "export": "TexasHoldemPracticeTableGame",
      "ready_testid": "texas-holdem-practice-table",
      "i18n_domain": "games/texas_holdem_practice_table",
      "i18n_probe": "controls.startHand"
    },
    "tests": {"long_driver": "tests.game_drivers.texas_holdem_practice_table:play"},
    "translations": {
      "ru-RU": {
        "label": "Тренировочный стол техасского холдема",
        "kicker": "Покерный стол",
        "description": "Разыграйте фиксированную партию техасского холдема против трёх серверных соперников."
      }
    },
    "lobby": {
      "featured": false,
      "wide": true,
      "art_class": "texas-holdem-practice-table-art",
      "symbol": "TH",
      "kicker": "Poker table",
      "description": "Fixed-limit Texas Hold'em practice against three server-managed opponents.",
      "tags": ["Cards", "Poker", "Strategy", "Ledger-backed"]
    }
  },
  "depends_on": ["core", "ledger", "players"],
  "may_not_depend_on": ["roulette", "slots", "blackjack", "baccarat", "keno", "bingo", "multi_hand_video_poker", "casino_war", "big_six_wheel", "red_dog", "dragon_tiger", "hi_lo"]
}
```

The descriptor starts at module version `1.0.0`, uses the already reserved sort order `200`, and does not change packaged application version `9.1.1`. Those reservations are not permission to overwrite newer shared revisions. During serialized intake, #77 must also add any sibling game accepted after this proposal was refreshed rather than treating this `may_not_depend_on` list as a stale allowlist.

## Proposed permanent requirements

The central owner should allocate these as `PLANNED` and promote them only after real-backend acceptance:

1. `THPT-001`: fixed-ante Texas Hold'em rules, shared-card dealing, shared-poker showdown, and one human versus three server-managed opponents.
2. `THPT-002`: authenticated player isolation, active-hand privacy, reload-safe decisions, history, and canonical route restoration.
3. `THPT-003`: one ledger escrow debit plus retry-safe refund/payout settlement under unique action IDs.
4. `THPT-004`: complete EN/RU visible and ARIA copy with responsive, accessible, reduced-motion-safe browser behavior.
5. `THPT-005`: catalog, contract, API, browser, long-driver, version, requirement, and visual-evidence discovery.

Proposed focused IDs are `API-THPT-001` and `BR-THPT-001`; they are not permanent until the central registry owner records them.

## Shared bot-controller boundary

This isolated package does not import or edit `casino.bots`. It supplies three server-managed practice seats with virtual table stacks, and every automatic decision enters the same `engine.apply_action` validation path as the human. Only the authenticated human's reserved tokens move through the shared ledger.

That provides the issue-scoped human-versus-server practice experience without claiming shared bot-plane acceptance. Opponent antes and calls are virtual practice contributions, not debits from bot player accounts, so this draft also does **not** claim the platform all-wager ledger rule for those seats. To satisfy `BOT-001` through `BOT-007` and all-wager acceptance, #77 and the bots owner must add or approve a compatible Texas Hold'em capability/strategy, funded player-account controllers, Admin exposure, public-action routing, and bot-ledger audit. The game branch must not solve that shared control-plane work.

## Visual matrix proposal

Add a `texas_holdem_practice_table` surface at route `/games/texas_holdem_practice_table` with selector `[data-testid='texas-holdem-practice-table']` and states:

- `ready`
- `preflop_decision`
- `flop_decision`
- `turn_decision`
- `river_decision`
- `showdown`
- `settled`
- `route_restored`

Required locales are `en-US` and `ru-RU`. Required viewports are `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`. Apply `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, and `VIS-CATALOG-001`.

Real `after_pass` evidence cannot be produced from this unregistered slice. After #77 materializes the descriptor and matrix row, capture both locales at every viewport, all decision streets, showdown, a folded result, reduced-motion behavior, and direct/reload/Back/Forward route restoration.

## Shared integration checklist

The #77 owner must:

1. Rebase this draft onto the then-accepted `main` in the serialized intake order.
2. Materialize the descriptor and add `texas_holdem_practice_table: 1.0.0` to `modules/module-manifest.json` in the same integration commit.
3. Allocate `THPT-001..005`, test IDs, central mappings, and generated docs.
4. Add the contract compatibility matrix entry and SHA-256 digest.
5. Add the visual row and central real-backend API/browser/long-suite discovery.
6. Apply shared application/tests/docs/contracts version bumps from then-current values.
7. Decide the shared bot-controller capability boundary described above.
8. Capture named EN/RU `after_pass` evidence from the exact integrated head.
9. Prove standard envelopes and authenticated binding through the registered HTTP server, not only an isolated router.
10. Repeat two-user state/wallet isolation and replay/restart recovery against the real configured store and ledger.

Do not add game-specific allowlists to the shared shell, registry, validators, or runners; catalog discovery must consume the descriptor.

## Durable idempotency follow-up

Prepared state, append-only ledger scanning, and a process-local lock provide normal duplicate-request safety while the supported single-process local simulator remains running. They do not make the shared JSON balance update and ledger append crash-atomic. Cross-process or public deployment also needs a shared storage-level unique action key committed atomically with balance and ledger insertion. Those shared ledger/storage capabilities are outside issue #95 and must remain explicit blockers rather than overstated guarantees.
