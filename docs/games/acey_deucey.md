# Acey-Deucey

Issue: #149. Parent epic: #66. Game portfolio: #73. Shared integration owner: #77.

Acey-Deucey, also known as In-Between, deals two boundary cards before the player risks play tokens. The player may pass or wager that a private third card will land strictly between the boundary ranks.

## Rules Profile

- One standard deck supplies two exposed boundaries and one prepared private third card.
- The free deal moves no play tokens.
- A strict inside rank returns a spread-priced multiple of the wager. The player wagers after both
  boundaries are public, so a flat return was mispriced: a wide gap lands inside far more often than a
  narrow one, and betting only wide gaps was strictly profitable (issue #408). The return is therefore
  `(1 - house_edge) / P(inside)`, which holds the same house edge at every spread. The server publishes
  the full table as `rules.inside_paytable` and the edge as `rules.house_edge`. Equal or adjacent
  boundaries have no legal inside wager: the service rejects Play before reveal, receipt, state, or
  ledger mutation, and the localized interface leaves Pass as the only available decision.
- Frozen-v1 clients retain the deprecated numeric `rules.inside_return_multiplier` field. It reports
  the same current-or-latest-round price as the authoritative table, while clients that understand
  this compatible patch select `rules.inside_paytable[round.inside_rank_count]`.
- Outside ranks and cards matching either boundary lose the play wager.
- A pass closes the round without ledger movement.
- All copy uses toy-simulator play-token language with no cash value.

## Distinct Module Proof

Hi-Lo exposes one card and asks for a higher/lower prediction. Red Dog takes an ante before its six-deck spread, includes pair and consecutive automatic paths, and offers spread-priced raises. Acey-Deucey exposes two boundaries for free and lets the player pass or make one spread-priced in-between wager before revealing the third card. The free look and free pass are retained; the price of the wager carries the edge instead.

## Catalog Integration

The descriptor at `modules/acey_deucey.json` owns module version `1.1.1`, route `/games/acey_deucey`, sort order `260`, paired EN/RU resources, the frozen-v1 OpenAPI contract, its spread-pricing compatibility record, and `tests.game_drivers.acey_deucey:play`. Permanent requirements `AD-001` through `AD-005` map rules, session/restart behavior, ledger safety, browser localization, and catalog-wide evidence.

Play settlement persists deterministic recovery state before the wager debit. If no matching append-only debit proof exists after an insufficient-funds response or process interruption, reload restores the original private boundary decision and releases only the uncommitted play identity. Once debit proof exists, terminal state remains authoritative and payout recovery continues exactly once.

The visual surface `acey_deucey` covers `ready`, `boundaries_dealt`, `settled`, `passed`, `reduced_motion`, and `route_restored` in both locales at desktop primary, desktop compact, tablet, and mobile viewports. Shared registration remains catalog-driven.
