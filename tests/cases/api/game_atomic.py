# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free atomic game-state cases for the API lane."""


# Register atomic game-state suites through fresh-process execution owned by the runner.
def run_cases(run_case, run_unit_module):
    """Register atomic game-state cases in their historical execution order."""
    # Execute Casino War reconciliation, preparation, contention, rollback, and lost-response evidence. (issues #704, #771)
    run_case("API-CW-ATOMIC-001", ["CW-006", "CW-007", "TEST-189", "TEST-199"], lambda: run_unit_module("casino.games.casino_war.tests.test_api", "Casino War atomic state suite failed"))
    # Execute the real two-process Keno draw, ticket-purchase, ticket-refund, and rollback races. (issues #754, #767)
    run_case("API-KENO-ATOMIC-001", ["KENO-028", "KENO-029", "TEST-191", "TEST-197"], lambda: run_unit_module("casino.games.keno.tests.test_atomic_state", "Keno atomic state suite failed"))
    # Execute real two-process Baccarat coup, wager, refund, settings, and recovery races. (issues #756, #769)
    run_case("API-BAC-ATOMIC-001", ["BAC-027", "BAC-028", "TEST-192", "TEST-198"], lambda: run_unit_module("casino.games.baccarat.tests.test_atomic_state", "Baccarat atomic state suite failed"))
    # Execute real two-process Blackjack round, settings, and stale active-round races. (issues #758, #773)
    run_case("API-BJ-ATOMIC-001", ["BJ-033", "BJ-034", "TEST-196", "TEST-200"], lambda: run_unit_module("casino.games.blackjack.tests.test_atomic_state", "Blackjack atomic state suite failed"))
    # Execute real two-process Multi-Hand Video Poker state and hold/draw ordering races. (issue #775)
    run_case("API-MHVP-ATOMIC-001", ["MHVP-007", "TEST-201"], lambda: run_unit_module("tests.games.multi_hand_video_poker.test_atomic_state", "Multi-Hand Video Poker atomic state suite failed"))
    # Execute real two-process Roulette wager, settings, spin, rollback, and lost-response evidence. (issue #777)
    run_case("API-ROU-ATOMIC-001", ["ROU-073", "TEST-202"], lambda: run_unit_module("tests.games.roulette.test_atomic_state", "Roulette atomic state suite failed"))
    # Execute fresh-process Bingo call ordering plus purchase, refund, payout, and reset recovery evidence. (issue #779)
    run_case("API-BINGO-ATOMIC-001", ["BINGO-028", "TEST-203"], lambda: run_unit_module("tests.games.bingo.test_atomic_state", "Bingo atomic state suite failed"))
    # Execute private Bingo purchase/session association, recovery, retention, privacy, and provider-parity evidence. (issue #1087)
    run_case("API-BINGO-PURCHASE-ASSOCIATION-001", ["BINGO-029", "TEST-265"], lambda: run_unit_module("tests.bingo_purchase_session_association_tests", "Bingo purchase-session association suite failed"))
    # Execute fresh-process Caribbean Stud decision ordering plus rollback and lost-response recovery. (issue #781)
    run_case("API-CS-ATOMIC-001", ["CS-007", "TEST-204"], lambda: run_unit_module("tests.games.caribbean_stud.test_api", "Caribbean Stud atomic state suite failed"))
    # Execute fresh-process Four Card Poker decision ordering plus rollback and lost-response recovery. (issue #783)
    run_case("API-FOUR-CARD-POKER-ATOMIC-001", ["FOURCP-003", "TEST-205"], lambda: run_unit_module("tests.games.four_card_poker.test_api", "Four Card Poker atomic state suite failed"))
    # Execute fresh-process Three Card Poker decision ordering plus rollback and lost-response recovery. (issue #786)
    run_case("API-TCP-ATOMIC-001", ["TCP-006", "TEST-206"], lambda: run_unit_module("tests.games.three_card_poker.test_api", "Three Card Poker atomic state suite failed"))
    # Execute fresh-process Casino Hold'em decision ordering plus rollback and lost-response recovery. (issue #788)
    run_case("API-CH-ATOMIC-001", ["CH-007", "TEST-207"], lambda: run_unit_module("tests.games.casino_holdem.test_api", "Casino Hold'em atomic state suite failed"))
    # Execute fresh-process Pai Gow Poker set ordering plus rollback and lost-response recovery. (issue #793)
    run_case("API-PGP-ATOMIC-001", ["PGP-007", "TEST-208"], lambda: run_unit_module("tests.games.pai_gow_poker.test_api", "Pai Gow Poker atomic state suite failed"))
