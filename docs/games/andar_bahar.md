# Andar Bahar

Issue: #140. Parent epic: #66. Game portfolio: #73. Shared integration owner: #77.

Andar Bahar is a distinct catalog game whose server-authoritative deal exposes one joker or match card, alternates cards to Andar and Bahar, and settles the first matching rank through the play-token ledger.

## Rules Profile

- The first card is the joker or match card.
- Cards are dealt alternately to Andar, then Bahar.
- The first side to receive a card with the same rank as the joker card wins.
- Suits do not decide the outcome.
- A correct Andar prediction returns 1.90x the wager; a correct Bahar prediction returns 2.00x.
- Exact first-match placement enumeration gives Andar 429/833 (51.5006%) and Bahar 404/833
  (48.4994%), so the approved prices return 97.8511% and 96.9988% respectively.
- The deprecated frozen-v1 `return_multiplier=2` remains for old clients; new clients use the
  additive `return_multipliers` table for authoritative settlement copy.
- An incorrect side prediction returns 0 play tokens.
- All copy uses toy-simulator play-token language and does not imply cash value, deposits, purchases, withdrawals, prizes, redemption, or transferable value.

## Distinct Module Proof

Andar Bahar is distinct from the current catalog because its mechanic is side prediction on a first rank-match reveal sequence. Baccarat uses Punto Banco totals and drawing rules. Hi-Lo predicts whether one card is higher or lower. Dragon Tiger and Casino War compare two high-card hands. Red Dog prices a spread between two cards.

## Accessibility And Motion

The frontend module renders the joker card, the transparent alternating sequence, localized side labels, localized card labels, and a keyboard-focusable recent-history region. It owns no timers. Reduced-motion users receive the same complete non-animated reveal path, and the scoped CSS disables transitions and animations under `prefers-reduced-motion: reduce`.

## Catalog Integration

The descriptor at `modules/andar_bahar.json` owns module version `1.0.0`, route `/games/andar_bahar`, sort order `250`, paired EN/RU resources, the additive contract, and `tests.game_drivers.andar_bahar:play`. Permanent requirements `AB-001` through `AB-005` map rules, session/restart behavior, ledger safety, browser localization, and catalog-wide evidence.

The visual surface `andar_bahar` covers `ready`, `settled`, `reduced_motion`, and `route_restored` in both locales at desktop primary, desktop compact, tablet, and mobile viewports. Shared registration remains catalog-driven; no bespoke router, shell, or long-suite allowlist is required.
