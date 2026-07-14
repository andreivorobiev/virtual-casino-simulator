# Sic Bo integration handoff for #77

This isolated branch intentionally does not add `modules/sic_bo.json`. Current main immediately loads every game descriptor under `modules/`, while canonical revision lookup requires the matching `modules/module-manifest.json` entry. The user reserved that aggregate manifest and all central catalog acceptance files for #77, so the descriptor and revision must land together.

## Proposed module descriptor

```json
{
  "module": "sic_bo",
  "version": "1.0.0",
  "paths": [
    "casino/games/sic_bo/",
    "web/games/sic_bo.js",
    "web/i18n/en-US/games/sic_bo.json",
    "web/i18n/ru-RU/games/sic_bo.json"
  ],
  "requirements_prefixes": ["SIC-BO"],
  "contracts": ["contracts/openapi/sic_bo.v1.yaml"],
  "game": {
    "id": "sic_bo",
    "sort_order": 140,
    "route": "/games/sic_bo",
    "label": "Sic Bo",
    "category": "table",
    "categories": ["table", "numbers", "strategy"],
    "backend": {"register": "casino.games.sic_bo.api:register"},
    "frontend": {
      "module": "./games/sic_bo.js",
      "export": "SicBoGame",
      "ready_testid": "sic-bo-table",
      "i18n_domain": "games/sic_bo",
      "i18n_probe": "controls.shake"
    },
    "tests": {"long_driver": "tests.game_drivers.sic_bo:play"},
    "translations": {
      "ru-RU": {
        "label": "Сик Бо",
        "kicker": "Стол с костями",
        "description": "Три кости, 50 позиций для ставок и расчёт игровых жетонов через журнал.",
        "tags": ["Кости", "Числа", "Журнал жетонов"]
      }
    },
    "lobby": {
      "featured": false,
      "wide": false,
      "art_class": "sic-bo-art",
      "symbol": "3D6",
      "kicker": "Dice table",
      "description": "Three server-rolled dice, 50 classic betting positions, and retry-safe ledger settlement.",
      "tags": ["Dice", "Numbers", "Ledger-backed"]
    }
  },
  "depends_on": ["core", "ledger", "players"],
  "may_not_depend_on": ["roulette", "slots", "blackjack", "baccarat", "keno", "bingo", "multi_hand_video_poker", "casino_war", "big_six_wheel", "red_dog", "dragon_tiger", "hi_lo"]
}
```

The descriptor uses only existing shell category IDs, so it does not require new global EN/RU category strings. #77 must add `"sic_bo": "1.0.0"` to `modules/module-manifest.json` atomically with the descriptor and recalculate shared application/tests/docs/contracts revisions from then-current `main`.

## Proposed requirement block

Issue #88 currently has no permanent game-specific allocation. The #77 requirements owner should allocate, review, and register this proposed block; the isolated worker does not claim it is authoritative:

- `SIC-BO-001`: complete 50-position rules, three-die totals, triple exclusions, and documented paytable.
- `SIC-BO-002`: authenticated player-scoped, reload-safe state and canonical route restoration.
- `SIC-BO-003`: aggregate ledger-only wager/payout settlement with stable action IDs and conflict-safe retries.
- `SIC-BO-004`: EN/RU visible and accessible browser copy, responsive hierarchy, reduced motion, and timer cleanup.
- `SIC-BO-005`: catalog-discovered API/browser/long-suite/visual evidence across the approved matrix.

## Shared integration work

#77 must own all of the following after rebasing onto the accepted predecessor:

1. Add the proposed descriptor and aggregate game revision together.
2. Register permanent requirements and regenerate requirement documentation.
3. Add `contracts/compatibility/module-api-matrix.json` ownership plus the final contract digest.
4. Add a `sic_bo` visual row at `/games/sic_bo`, selector `[data-testid='sic-bo-table']`, and states `ready`, `wagers_selected`, `rolling`, `settled`, `reduced_motion`, and `route_restored`.
5. Discover the existing `tests.game_drivers.sic_bo:play` driver without adding a hardcoded allowlist.
6. Run real-backend catalog/API/browser/Long Suite 100, both locales, all four standard viewports, and named `after_pass` evidence.

The reserved sort order places Sic Bo after Scratch Cards (`130`) and before Chuck-a-Luck (`150`). This is catalog presentation order, not merge authorization. Current `main` contains predecessor descriptors through Hi-Lo while the central sequence still lists Sic Bo as reserved; the coordinator must explicitly release Sic Bo integration later.

## Multi-process follow-up

The local one-process server is protected by prepared state, a process lock, and deterministic ledger-action scans. Any later multi-process/public deployment must promote `details.sic_bo_action_id` into a storage-enforced unique idempotency key committed atomically with the balance and ledger row. That follow-up does not change the game API or rules.
