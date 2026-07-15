# Issue #139 Distinct Module Proof

Decision: promote the distinct isolated slice through the serialized #77 catalog integration lane.

Evidence:

- Casino Hold'em has a unique rule nucleus: the player antes, receives two hole cards with a three-card flop, then chooses call or fold before turn/river showdown against a dealer qualification rule.
- The dealer qualification rule, two-times ante call wager, and house-banked settlement make it materially distinct from player-versus-player or practice Texas Hold'em.
- Existing registered games on current `origin/main` do not implement that nucleus:
  - Three Card Poker resolves a three-card player hand, three-card dealer hand, ante/play decision, and optional Pair Plus wager with no shared community board or five-card turn/river showdown.
  - Multi-Hand Video Poker is a solitaire Jacks-or-Better draw game with no dealer, community board, call/fold branch, or dealer qualification.
  - Hi-Lo resolves one higher/lower prediction against a hidden next card.
  - Casino War and Dragon Tiger resolve direct high-card comparisons.
  - Red Dog resolves spread-based odds between two exposed cards.
  - Baccarat resolves Punto Banco totals with drawing rules, not poker hand ranking.
- The implementation reuses shared #96 card and poker primitives from `casino.core.cards` and `casino.core.poker`, but imports no existing game package.
- The canonical descriptor is promoted at sort order 290 after #77 integrated permanent requirements, compatibility metadata, discovery tests, versions, and visual evidence.

Countability: distinct and countable after exact-head #77 shared catalog, manifest, requirement, visual, browser, and Long Suite acceptance.
