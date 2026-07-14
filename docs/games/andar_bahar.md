# Andar Bahar Proposal Slice

Issue: #140. Parent epic: #66. Game portfolio: #73. Shared integration owner: #77.

This draft slice proves Andar Bahar as a distinct countable module candidate without registering it in the shared catalog. The module descriptor remains parked at `codex/tasks/artifacts/issue-140-andar-bahar/andar_bahar.module.proposal.json` until #77 owns integration into `modules/`, shared routing, visual matrix, long-suite discovery, and permanent requirement IDs.

## Rules Profile

- The first card is the joker or match card.
- Cards are dealt alternately to Andar, then Bahar.
- The first side to receive a card with the same rank as the joker card wins.
- Suits do not decide the outcome.
- A correct side prediction returns 2x the wager: stake plus even-money winnings.
- An incorrect side prediction returns 0 play tokens.
- All copy uses toy-simulator play-token language and does not imply cash value, deposits, purchases, withdrawals, prizes, redemption, or transferable value.

## Distinct Module Proof

Andar Bahar is distinct from the current catalog because its mechanic is side prediction on a first rank-match reveal sequence. Baccarat uses Punto Banco totals and drawing rules. Hi-Lo predicts whether one card is higher or lower. Dragon Tiger and Casino War compare two high-card hands. Red Dog prices a spread between two cards. Andar Bahar is therefore a separate card-showdown module candidate, pending #77 integration acceptance.

## Accessibility And Motion

The frontend module renders the joker card, the transparent alternating sequence, localized side labels, localized card labels, and a keyboard-focusable recent-history region. It owns no timers. Reduced-motion users receive the same complete non-animated reveal path, and the scoped CSS disables transitions and animations under `prefers-reduced-motion: reduce`.

## Validation Scope

Focused validation lives under `tests/games/andar_bahar/` and manually registers the game-owned API routes against the shared router. The suite verifies deterministic dealing, session-bound player identity, exactly-once ledger retry behavior, no body/query `player_id` override, resource parity, and frontend timer/reduced-motion constraints.
