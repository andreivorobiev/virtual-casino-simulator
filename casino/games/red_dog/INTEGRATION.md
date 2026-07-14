# Red Dog integration handoff for #77

This branch intentionally does not add `modules/red_dog.json`. The canonical version interface requires the same integration commit to add `"red_dog": "1.0.0"` to `modules/module-manifest.json`, and issue #77 reserves that aggregate file plus registration, compatibility, requirements, visual-matrix, and shared discovery files. Keeping the descriptor as a proposal prevents this isolated draft from breaking the existing catalog before the integration lane releases it.

## Proposed module descriptor

```json
{
  "module": "red_dog",
  "version": "1.0.0",
  "paths": [
    "casino/games/red_dog/",
    "web/games/red_dog.js",
    "web/i18n/en-US/games/red_dog.json",
    "web/i18n/ru-RU/games/red_dog.json"
  ],
  "requirements_prefixes": ["RD"],
  "contracts": ["contracts/openapi/red_dog.v1.yaml"],
  "game": {
    "id": "red_dog",
    "sort_order": 110,
    "route": "/games/red_dog",
    "label": "Red Dog",
    "category": "table",
    "categories": ["table", "cards", "strategy"],
    "backend": {"register": "casino.games.red_dog.api:register"},
    "frontend": {
      "module": "./games/red_dog.js",
      "export": "RedDogGame",
      "ready_testid": "red-dog-table",
      "i18n_domain": "games/red_dog",
      "i18n_probe": "controls.raise"
    },
    "tests": {"long_driver": "casino.games.red_dog.tests.long_driver:play"},
    "translations": {
      "ru-RU": {
        "label": "Red Dog",
        "kicker": "Карточный стол",
        "description": "Оцените диапазон между двумя картами и решите, оставить ставку или удвоить её."
      }
    },
    "lobby": {
      "featured": false,
      "wide": false,
      "art_class": "red-dog-art",
      "symbol": "RD",
      "kicker": "Card table",
      "description": "Back the third card to land inside the spread, with one optional matching raise.",
      "tags": ["Cards", "Decision", "Ledger-backed"]
    }
  },
  "depends_on": ["core", "ledger", "players"],
  "may_not_depend_on": ["roulette", "slots", "blackjack", "baccarat", "keno", "bingo", "multi_hand_video_poker"]
}
```

The integration owner should confirm sort order 110 against current `main`, add the descriptor and aggregate revision in one commit, and decide whether to retain the game-local driver import or move it to the canonical `tests.game_drivers.red_dog:play` path.

## Proposed permanent requirements

The following identifiers are not allocated until #77 writes the central registry:

- `RD-001`: Six-deck Red Dog implements consecutive pushes, pair handling, spread decisions, and the regulated payout schedule.
- `RD-002`: Additive v1 routes resolve only the authenticated player and keep active or recent rounds reload-safe.
- `RD-003`: Ante, raise, push return, and payout movements are ledger-only and exactly-once under stable action IDs.
- `RD-004`: Complete EN/RU visible and accessible copy remains responsive and timer-clean at every required viewport.
- `RD-005`: Catalog, contract, browser, long-suite, requirement, module, version, and visual evidence are traceable after shared integration.

## Shared test and catalog discovery

After descriptor registration, the catalog-owned API and browser runners should discover the backend, frontend, contract, readiness selector, and game-local long driver without a Red Dog allowlist. The driver:

1. Reads authenticated player state.
2. Starts a low-wager round with a unique action id.
3. Calls without a raise when the opening produces a spread decision.
4. Asserts the terminal state contains the expected two or three cards and complete settlement.

The #77 integration gate must separately prove hostile caller IDs cannot override the session, exact retry does not add ledger rows, conflicting retry payloads fail closed, and every full-casino long scenario discovers Red Dog.

## Proposed visual matrix row

Add a `red_dog` surface at route `/games/red_dog` with selector `[data-testid='red-dog-table']` and states:

- `ready`
- `spread_decision`
- `pair_settled`
- `consecutive_push`
- `third_card_settled`
- `route_restored`

Required locales are `en-US` and `ru-RU`. Required viewports are `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`. Apply `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, and `VIS-CATALOG-001`.

After registration, capture real-backend `after_pass` evidence for ready, spread decision, automatic pair/consecutive settlement, and third-card settlement in both locales across the allocated viewports. The isolated worker evidence record deliberately makes no acceptance claim before that route exists in the authenticated shared shell.

## Shared-ledger follow-up

Prepared player state, ledger action scanning, and a process lock protect the supported local one-process server. A future multi-process deployment still needs a storage-provider idempotency key enforced in the same transaction as balance and ledger insertion. The adapter supplies `details.red_dog_action_id` so shared storage can promote that value without changing the game contract.
