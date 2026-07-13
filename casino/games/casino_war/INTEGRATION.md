# Casino War integration handoff for #77

This branch intentionally does not add `modules/casino_war.json`, because #110's version validator requires the same change to `modules/module-manifest.json`, and the coordinator reserved that aggregate file and all shared registration/discovery files for #77. After #110 merges, the integration owner should add the descriptor and aggregate revision together.

## Proposed module descriptor

```json
{
  "module": "casino_war",
  "version": "1.0.0",
  "paths": [
    "casino/games/casino_war/",
    "web/games/casino_war.js"
  ],
  "requirements_prefixes": ["CW"],
  "contracts": ["contracts/openapi/casino_war.v1.yaml"],
  "game": {
    "id": "casino_war",
    "sort_order": 70,
    "route": "/games/casino_war",
    "label": "Casino War",
    "category": "table",
    "categories": ["table", "cards", "high-card"],
    "backend": {"register": "casino.games.casino_war.api:register"},
    "frontend": {
      "module": "./games/casino_war.js",
      "export": "CasinoWarGame",
      "ready_testid": "casino-war-table",
      "i18n_domain": "games/casino_war",
      "i18n_probe": "controls.war"
    },
    "tests": {"long_driver": "tests.game_drivers.casino_war:play"},
    "translations": {
      "ru-RU": {
        "label": "Casino War",
        "kicker": "Карточный стол",
        "description": "Сравните карты с дилером, а при ничьей выберите сдачу или войну."
      }
    },
    "lobby": {
      "featured": false,
      "wide": false,
      "art_class": "casino-war-art",
      "symbol": "&#9876;",
      "kicker": "Card table",
      "description": "A fast high-card table with surrender and war decisions on ties.",
      "tags": ["Cards", "Decision", "Ledger-backed"]
    }
  },
  "depends_on": ["core", "ledger", "players"],
  "may_not_depend_on": ["roulette", "slots", "blackjack", "baccarat", "keno", "bingo"]
}
```

The integration owner should confirm final `sort_order`, add `"casino_war": "1.0.0"` to `modules/module-manifest.json`, allocate permanent `CW-*` requirement IDs, and add their mappings to the descriptor and central registry.

## Shared test discovery

Add `tests/game_drivers/casino_war.py` only in the #77 integration lane. Its `play(client, index)` scenario should:

1. Read session-bound state.
2. Start a round with a unique `action_id` and positive play-token wager.
3. If the initial result is a tie, select surrender or war with a second unique `action_id`.
4. Assert the round reaches `settled`, required and committed settlement counts match, and the bound player's ledger contains each `casino_war_action_id` once.
5. Repeat one command with the same action id and assert the balance and ledger row count do not change.

The shared API and browser runners, long-suite discovery, catalog validator, and shell imports must discover this descriptor; do not add Casino War allowlists to them.

## Visual matrix row

Add a `casino_war` surface at route `/games/casino_war` with selector `[data-testid='casino-war-table']` and states:

- `accepting_wager`
- `initial_result`
- `war_decision`
- `war_result`
- `route_restored`

Required locales are `en-US` and `ru-RU`. Required viewports are `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`. Apply `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, and `VIS-EVIDENCE-001`.

After integration, capture real-backend `after_pass` evidence for at least `accepting_wager`, `war_decision`, and `war_result` in both locales across the allocated matrix viewports. This isolated branch cannot produce valid acceptance images because #110/#77 still own catalog routing and the visual matrix.

## Shared-ledger follow-up

The local one-process server is protected by prepared state, ledger action scanning, and a process lock. If public/multi-process deployment work proceeds, the shared storage providers need a unique idempotency-key column/field enforced in the same transaction as balance and ledger insertion. The Casino War adapter already supplies `details.casino_war_action_id`; #77 or a core-ledger follow-up can promote that value to the atomic provider interface without changing game rules or API commands.
