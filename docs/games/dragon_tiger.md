# Dragon Tiger isolated game slice

Issue: [#83](https://github.com/andreivorobiev/virtual-casino-simulator/issues/83)

Parents: #66, #73

Shared integration lane: #77

Catalog foundation: #81 / merged PR #110

## Rules profile

This simulator uses one explicit `standard-8d` profile instead of claiming that every venue uses identical Dragon Tiger rules:

- Eight standard 52-card decks are shuffled into one persistent shoe; jokers are excluded.
- Dragon receives the first card and Tiger receives the second. No additional cards are drawn.
- Ranks ascend from Ace low through King high. Suits never break a main-game tie.
- Dragon and Tiger pay net 1:1. Tie pays net 11:1.
- When the ranks tie, a Dragon or Tiger wager has outcome `half_loss` and receives half its stake back, rounded half-up to the ledger's cent precision. This is not a push.
- The v1 slice offers Dragon, Tiger, and Tie only. A same-rank same-suit result still wins the ordinary Tie wager; Suited Tie is outside this issue.

The comparison, rank order, half-loss treatment, and 11:1 Tie price follow the regulator-approved [Singapore Dragon Tiger rules](https://www.gra.gov.sg/docs/default-source/game-rules/mbs/other-games/dragon_tiger_%28mbs%29.pdf?sfvrsn=dae64458_1). Current [Austrian published Pragmatic terms](https://www.evi.gv.at/b/pi/bms-z73) confirm the 1:1, 11:1, and half-return settlement profile, while [Evolution's product page](https://games.evolution.com/live-casino/dragon-tiger/) confirms that its 11:1 Tie is independent of suit.

## Shoe and deterministic model

The named simulator profile uses an Evolution-style shoe lifecycle documented in an [operator-hosted Evolution/Ezugi rules manual](https://cdpdf.hollywoodbets.net/GAMERULES/Evolution%20Ezugi%20New1.pdf): burn three cards once when the eight-deck shoe is created and reserve one deck, or 52 cards, behind the cut. A round already in progress completes before refresh; the next round creates a new shoe when `shuffle_pending` is true. This round-boundary behavior also matches the current [Pragmatic operator rules](https://www.sisal.it/content/dam/new-dam/italy/canali/sisal-it/doc-pdf/casin%C3%B2-live/regolamenti-giochi/d-f/Dragon%20Tiger.pdf). Burn and cut details vary by provider, so they are fixed profile metadata here rather than a universal-rule claim.

The engine reuses `casino.core.cards.shuffled_deck(decks=8)`. Production omits a seed and receives system entropy. Focused tests inject a seed or compatible random source; no public API accepts forced cards or caller-controlled entropy. Compact card codes, the undealt shoe, shoe number, pending-refresh flag, and bounded recent rounds remain player-scoped persisted state so reload cannot change an already dealt outcome.

## Settlement and exactly-once invariants

One `POST /api/v1/games/dragon-tiger/rounds` request is one atomic public action:

1. Resolve the authenticated player and ignore any caller attempt to select another `player_id`.
2. Validate `action_id`, bet, and fake-money wager, then derive one semantic request fingerprint.
3. Reuse the persistent shoe to deal Dragon then Tiger and calculate the immutable settled round.
4. Debit the wager only through `casino/core/ledger.py` and credit any stake return or winnings only through that ledger.
5. Persist the round, shoe progress, and ledger evidence before returning the standard success envelope.

Retrying the same `action_id` with the same semantic input returns the identical round and ledger evidence with `replayed: true`; it must not repeat balance movement or draw new cards. A durable player-scoped action index retains that proof independently from the bounded 50-round display history and the shared ledger scan horizon. Reusing the identity with a different bet or wager fails closed with a conflict. Settlement credits after the initial debit are `2 × wager` for a winning Dragon/Tiger bet, `12 × wager` for a winning Tie, and `0.5 × wager` for a Dragon/Tiger half-loss on a tie.

The game persists `wager_attempting` and `settlement_attempting` before calling the shared ledger. When a retry finds the matching append-only evidence, it resumes normally. When an attempted movement has no evidence—an ambiguity possible because the current JSON provider stores balance and ledger event separately—the action returns a reconciliation conflict and never repeats that movement. This preserves retry safety but is not automatic completion; #77 must either reconcile the action or land a shared atomic/idempotent ledger primitive before claiming unconditional provider-crash recovery.

## Session and API boundary

The additive v1 contract exposes:

- `GET /api/v1/games/dragon-tiger/state` for rules, public shoe metadata, bounded recent rounds, and the authenticated player;
- `POST /api/v1/games/dragon-tiger/rounds` for one settled or safely replayed round.

Both operations use the standard `{ ok: true, data: ... }` or `{ ok: false, error: ... }` envelope. Optional `player_id` values remain compatibility inputs, but the shared `/api/v1/games/*` session resolver takes precedence. The state response never exposes undealt card order.

## Requirement proposal

These permanent IDs are proposed for #77 to add to the central registry. They remain `PLANNED` until real registered-backend tests and required visual evidence pass.

| ID | Proposed requirement | Initial status |
| --- | --- | --- |
| `DT-001` | Dragon Tiger implements the documented standard-8d comparison, payout, half-loss, and persistent-shoe rules with deterministic test seams. | `PLANNED` |
| `DT-002` | The additive v1 state and round APIs are authenticated, session-bound, reload-safe, and preserve standard envelopes. | `PLANNED` |
| `DT-003` | Every wager, return, and payout is ledger-only; identical retries are exactly-once and conflicting action reuse fails closed. | `PLANNED` |
| `DT-004` | The browser surface is EN/RU clean, accessible, responsive, reduced-motion safe, and leaves no timers after teardown. | `PLANNED` |
| `DT-005` | Focused engine/API/frontend tests, the catalog driver, and real-backend visual evidence cover required states and viewports. | `PLANNED` |

The isolated module proposal starts at `1.0.0`. The API is additive and does not change any existing v1 operation or payload.

## Integration handoff for #77

The shared integration owner must:

- add `dragon_tiger: 1.0.0` to `modules/module-manifest.json` from the then-current accepted main branch;
- register `DT-001` through `DT-005`, map focused tests and browser evidence, and regenerate derived requirement documentation;
- add the contract to compatibility matrices and digests;
- add the `dragon_tiger` visual-matrix row and capture only real-backend `after_pass` evidence;
- resolve the shared JSON ledger balance/event atomicity gap (or document the operational reconciliation gate) before unconditional crash-recovery acceptance;
- localize the shared wallet label written by `web/core/ui.js` so ru-RU settlement refreshes cannot leak English shell copy;
- validate catalog discovery for sort order 100, `/games/dragon_tiger`, backend registration, lazy frontend export, i18n domain, readiness selector, and long driver;
- run the complete API, browser, catalog, contract, requirement, version, boundary, comment-density, and long-suite gates.

This isolated slice does not edit the aggregate manifest, shared catalog/router/shell, compatibility inventories, central requirements, visual matrix, or test discovery. Until #77 completes those gates, the draft is not integration acceptance and must remain draft.
