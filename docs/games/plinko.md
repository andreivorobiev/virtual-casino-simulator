# Plinko

Issue: #136. Status: catalog-integrated through the serialized #77 acceptance lane.

Plinko is distinct because its server-authoritative outcome is an eight-step left/right peg path ending in one of nine multiplier buckets. The browser only replays the committed path; it cannot choose the bucket or settlement.

## Rules and settlement

- Each drop accepts one play-token wager and a stable `action_id`.
- The backend commits eight left/right decisions and derives the bucket from the number of right decisions.
- The published multiplier table determines returned play tokens and net result.
- Exact retries return the committed drop without duplicate ledger movement; conflicting reuse fails closed.
- Authenticated session context overrides caller-supplied player identifiers.

All wager debits and returned-token credits use `casino.core.ledger`. Plinko never mutates balances directly, and player-scoped state plus durable action receipts preserve reload/restart recovery.

## Canonical integration

The descriptor at `modules/plinko.json` owns module version `1.0.0`, route `/games/plinko`, sort order `230`, paired EN/RU resources, the additive contract, and `tests.game_drivers.plinko:play`. Permanent requirements `PLINKO-001` through `PLINKO-005` map rules, session/restart behavior, ledger safety, browser localization, and catalog-wide evidence.

The visual surface `plinko` covers `ready`, `path_replay`, `settled`, `reduced_motion`, and `route_restored` in both locales at desktop primary, desktop compact, tablet, and mobile viewports. Shared registration remains catalog-driven; no bespoke router, shell, or long-suite allowlist is required.
