# Crown and Anchor

Crown and Anchor is integrated as the distinct issue #133 symbol-dice table. The rules profile uses three six-sided symbol dice with the faces Crown, Anchor, Heart, Diamond, Club, and Spade. A player may cover any subset of symbols in one atomic round. One hit pays 1:1 net, two hits pay 2:1 net, and three hits pay 3:1 net on that covered symbol, with returned stake included in the settlement credit.

All play-token movement is routed through `casino.core.ledger`; the game engine never mutates a player balance directly. The API uses session-bound identity from request context and ignores body or query `player_id` values. Exact retries recover the committed wager, dice, and settlement while conflicting reuse fails closed.

## Canonical #77 integration

The descriptor at `modules/crown_and_anchor.json` owns module version `1.0.0`, route `/games/crown_and_anchor`, sort order `210`, paired EN/RU resources, additive contract discovery, and `tests.game_drivers.crown_and_anchor:play`. Permanent requirements `CAA-001` through `CAA-005` map rules, session/restart behavior, ledger safety, browser localization, and catalog-wide evidence.

The visual surface `crown_and_anchor` covers `ready`, `rolling`, `settled`, `reduced_motion`, and `route_restored` in both locales at desktop primary, desktop compact, tablet, and mobile viewports. Shared registration remains catalog-driven; no bespoke router, shell, or long-suite allowlist is required.
