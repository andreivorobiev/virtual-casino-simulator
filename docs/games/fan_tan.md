# Fan-Tan

Issue: #137. Status: catalog-integrated through the serialized #77 acceptance lane.

Fan-Tan is distinct because its server-authoritative outcome counts a covered pile in groups of four and settles the final residue from one through four. The browser presents the committed count; it cannot choose the pile size, residue, or settlement.

## Rules and settlement

- Each round accepts wagers on one or more residues and a stable `action_id`.
- The backend chooses a covered pile from 49 through 80 and counts complete groups of four.
- A modulo-zero result is the table outcome labeled residue four.
- A correct residue returns the stake plus three-to-one net winnings.
- Exact retries return the committed round without duplicate ledger movement; conflicting reuse fails closed.
- Authenticated session context overrides caller-supplied player identifiers.

All aggregate wager debits and returned-token credits use `casino.core.ledger`. Fan-Tan never mutates balances directly, and player-scoped state plus durable action receipts preserve reload/restart recovery.

## Canonical integration

The descriptor at `modules/fan_tan.json` owns module version `1.0.0`, route `/games/fan_tan`, sort order `240`, paired EN/RU resources, the additive contract, and `tests.game_drivers.fan_tan:play`. Permanent requirements `FAN-TAN-001` through `FAN-TAN-005` map rules, session/restart behavior, ledger safety, browser localization, and catalog-wide evidence.

The visual surface `fan_tan` covers `ready`, `counting`, `settled`, `reduced_motion`, and `route_restored` in both locales at desktop primary, desktop compact, tablet, and mobile viewports. Shared registration remains catalog-driven; no bespoke router, shell, or long-suite allowlist is required.
