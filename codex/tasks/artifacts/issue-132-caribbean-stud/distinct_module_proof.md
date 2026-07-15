# Issue #132 Distinct Countable Game Proof

Conclusion: Caribbean Stud is a distinct, countable casino game module proposal.

## Distinctness

- It is a named casino table game with a stable public identity: Caribbean Stud.
- The player competes against a dealer with five-card poker hands, not against a paytable-only draw as in video poker.
- It has a unique ante-first, call-or-fold decision point after seeing the player hand and one dealer upcard.
- It has dealer qualification at ace-king high or better, which is not a rule axis of Baccarat, Blackjack, Casino War, Dragon Tiger, Hi-Lo, Red Dog, Big Six Wheel, Roulette, Slots, Keno, Bingo, or Multi-Hand Video Poker.
- It has a two-stage ledger shape: ante debit first, then optional call debit and returned-token settlement after the decision.

## Countability

The module can be counted as one additional game because it owns:

- game id `caribbean_stud`;
- backend package `casino/games/caribbean_stud`;
- frontend module `web/games/caribbean_stud.js`;
- paired EN/RU locale domain `games/caribbean_stud`;
- additive OpenAPI contract `contracts/openapi/caribbean_stud.v1.yaml`;
- focused tests under `tests/games/caribbean_stud` and catalog driver `tests/game_drivers/caribbean_stud.py`;
- canonical descriptor `modules/caribbean_stud.json`.

## Boundary

Issue #77 accepts Caribbean Stud as one catalog-counted game only after the canonical descriptor, permanent requirements, compatibility metadata, visual row, real-backend browser coverage, and Long Suite discovery pass on one exact head.
