# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own core live-game and Admin registrations for the #727 split."""


# Register the complete live-game and Admin block at its historical boundary.
def run_cases(run_case, roulette, slots, blackjack, blackjack_insurance_phase_guard, blackjack_rule_edges, baccarat, keno, bingo, private_sessions, admin):
    """Register exact core game, isolation, and Admin callbacks."""
    # Record Roulette betting, settlement, rebet, and persisted-rule coverage.
    run_case("API-ROU-001", ["ROU-010", "ROU-011", "ROU-030", "ROU-032", "LEDGER-001"], roulette)
    # Record Slots spin-grid, cost, and paytable coverage.
    run_case("API-SLOT-001", ["SLOT-001", "SLOT-002", "SLOT-003"], slots)
    # Record Blackjack settings and active-round protection coverage.
    run_case("API-BJ-001", ["BJ-010", "BJ-011", "BJ-020", "BJ-034"], blackjack)
    # Record Blackjack insurance phase and wallet-mutation guards.
    run_case("API-BJ-003", ["BJ-020", "LEDGER-015", "TEST-056"], blackjack_insurance_phase_guard)
    # Record deterministic Blackjack rule-edge coverage.
    run_case("API-BJ-002", ["BJ-002", "BJ-003", "BJ-004", "BJ-005", "BJ-006", "BJ-007", "BJ-012", "BJ-015", "BJ-016", "BJ-017", "BJ-018", "BJ-019", "BJ-026", "BJ-031", "TEST-054"], blackjack_rule_edges)
    # Record Baccarat wager, deal, and bot-bet integration coverage.
    run_case("API-BAC-001", ["BAC-001", "BAC-010", "BAC-030"], baccarat)
    # Record Keno paytable, ticket, and draw coverage.
    run_case("API-KENO-001", ["KENO-001", "KENO-002", "KENO-010"], keno)
    # Record Bingo refund and terminal competitive settlement coverage.
    run_case("API-BINGO-001", ["BINGO-001", "BINGO-010", "BINGO-020"], bingo)
    # Record cross-player game-state and ledger isolation coverage.
    run_case("API-GAME-STATE-ISOLATION-001", ["ROU-010", "SLOT-019", "BJ-020", "BAC-010", "KENO-008", "BINGO-020", "LEDGER-001", "AUTO-001"], private_sessions)
    # Record Admin metadata, requirements, logs, users, tokens, terms, and locale coverage.
    run_case("API-ADMIN-001", ["ADMIN-001", "ADMIN-003", "ADMIN-004", "ADMIN-014", "DOC-001", "LOG-001", "ADMIN-USER-PENDING-035", "TERMS-PENDING-035", "TOKEN-PENDING-035", "I18N-003", "TEST-003"], admin)
