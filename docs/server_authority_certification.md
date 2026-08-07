# Server-Authority and Hostile-Client Certification

Issue #191 treats every browser, PWA, Android, and iOS client as an untrusted presentation and intent-capture surface. The authenticated server session selects the player; game services validate legal actions; engines select random outcomes and payouts; storage and the ledger own financial commits; and responses project the resulting authoritative receipt.

## Machine-readable inventory

`contracts/compatibility/server-authority-matrix.json` is generated from the canonical registered catalog, each module-owned OpenAPI v1 contract, and each checked-in game implementation. It explicitly lists every state-changing method/path pair for each currently registered game (the exact total is `catalog_game_count` in that generated artifact) and assigns its client-intent, server-validation, engine-outcome, shared settlement interface, and response-projection owners.

Run `python scripts/generate_server_authority_matrix.py` after an authorized catalog or contract mutation. `python scripts/validate_contracts.py` and `API-SEC-001` fail closed when the checked artifact differs from the catalog, a game lacks a mutation action, evidence disappears, or the protected-field policy drifts.

Issue #430 additionally requires every catalog game to prove `casino.core.settlement.GameSettlementGateway` as its financial boundary. Matrix generation fails when a registered module neither imports the gateway nor delegates through `SimpleWagerGame`, and `API-GAMECORE-004` rejects direct game imports or calls to ledger mutation functions.

Texas Hold'em Practice Table extends the accepted certification with its state-changing hand and decision routes, focused session/turn/outcome/ledger/replay evidence, funded-opponent Admin audit, authoritative client-refresh behavior, and catalog-driven Long Suite coverage.

## Hostile request boundary

`casino.core.request_player.sanitize_game_intent` removes caller-authored privilege, wallet, result, payout, RNG, card/deck/dice/reel/wheel, bonus, and round-control fields before any `/api/v1/games/` handler runs. The router then overwrites both body and query `player_id` values with the authenticated session binding. Documented wager, choice, hold, action identity, and route identifiers remain bounded intent and are revalidated by the owning game service or engine.

The former Roulette `force_result` HTTP seam is removed. Roulette now always asks its server engine for the result; hostile `force_result` payloads are ignored by the common boundary. Deterministic outcome injection remains an internal unit-test concern rather than a client-reachable feature.

## Permanent evidence

- `API-SEC-001` rebuilds the current catalog/action inventory and probes every registered game through the real router with conflicting identities and all protected fields.
- `API-PRIVATE-SESSION-001` exercises two authenticated users across the full registered catalog, including legal action, private state, wallet, ledger, conflict, replay, and Admin isolation evidence as applicable.
- `API-WALLET-RESTART-001` proves committed game state and wallet receipts survive a real process restart.
- `tests/storage_tests.py` proves exact replay, changed-meaning conflict, lost-response recovery, and at least 25 concurrent duplicates for debit, payout, refund, and settlement families. The live provider case remains opt-in and uses only an already configured test database.
- `BR-SEC-001` tampers with the rendered wallet and unrelated local storage, then proves an authenticated refresh restores the ledger-backed value without trusting the client cache.
- Existing per-game API, browser, contract, catalog, and Long Suite 100 evidence remains the detailed rules and action evidence linked from each matrix row.

## Acceptance interpretation

Green checks prove the checked commit satisfies the repository-local certification framework for the current registered catalog. They do not authorize public exposure, merge, deployment, provider changes, or advancement of held lanes; those remain separate owner decisions.
