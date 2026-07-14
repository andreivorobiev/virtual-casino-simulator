# Crown and Anchor

Crown and Anchor is implemented here as an isolated issue #133 module proposal. The rules profile uses three six-sided symbol dice with the faces Crown, Anchor, Heart, Diamond, Club, and Spade. A player may cover any subset of symbols in one atomic round. One hit pays 1:1 net, two hits pay 2:1 net, and three hits pay 3:1 net on that covered symbol, with returned stake included in the settlement credit.

All play-token movement is routed through `casino.core.ledger`; the game engine never mutates a player balance directly. The API uses session-bound identity from request context and ignores body or query `player_id` values. Shared catalog, requirements, version, visual-matrix, and long-suite acceptance remain owned by issue #77.

