# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free game lifecycle and atomic-state cases for the API lane."""


# Register game lifecycle suites through fresh-process execution owned by the runner.
def run_cases(run_case, run_unit_module):
    """Register game lifecycle cases in their historical execution order."""
    # Record the practice-table solvency, compensation, and self-heal proof. (issue #411)
    run_case("API-THPT-ESCROW-001", ["THPT-006"], lambda: run_unit_module("tests.thpt_escrow_tests", "practice-table escrow suite failed"))
    # Execute fresh-process practice-table ordering plus escrow rollback and lost-response recovery. (issue #795)
    run_case("API-THPT-ATOMIC-001", ["THPT-007", "TEST-209"], lambda: run_unit_module("casino.games.texas_holdem_practice_table.tests.test_api", "practice-table atomic state suite failed"))
    # Execute fresh-process Craps ordering plus wager rollback and proof recovery. (issue #797)
    run_case("API-CRAPS-ATOMIC-001", ["CRAPS-006", "TEST-210"], lambda: run_unit_module("tests.games.craps.test_api", "Craps atomic state suite failed"))
    # Execute fresh-process Andar Bahar ordering plus rejected-wager rollback. (issue #799)
    run_case("API-AB-ATOMIC-001", ["AB-006", "TEST-211"], lambda: run_unit_module("tests.games.andar_bahar.test_api", "Andar Bahar atomic state suite failed"))
    # Execute shared-helper delegation, lifecycle recovery, and fresh-process Over/Under 7 ordering. (issue #865)
    run_case("API-OU7-ATOMIC-001", ["OU7-007", "OU7-008", "GAMECORE-007", "TEST-212", "TEST-237"], lambda: run_unit_module("tests.games.over_under_7.test_api", "Over/Under 7 atomic state and shared-helper suite failed"))
    # Execute shared-helper delegation, historical proof recovery, and distinct-round sibling preservation. (issue #859)
    run_case("API-BIG-SIX-ATOMIC-001", ["BIG-SIX-007", "BIG-SIX-008", "TEST-213", "TEST-234"], lambda: run_unit_module("tests.unit.big_six_wheel_engine_tests", "Big Six Wheel atomic state suite failed"))
    # Execute fresh-process Crown and Anchor ordering plus sibling-state preservation. (issue #805)
    run_case("API-CAA-ATOMIC-001", ["CAA-006", "CAA-007", "GAMECORE-007", "TEST-214", "TEST-238"], lambda: run_unit_module("tests.games.crown_and_anchor.test_api", "Crown and Anchor lifecycle and atomic-state suite failed"))
    # Execute fresh-process Fan-Tan ordering plus sibling-state and ledger recovery proof. (issue #807)
    run_case("API-FAN-TAN-ATOMIC-001", ["FAN-TAN-006", "FAN-TAN-007", "GAMECORE-007", "TEST-215", "TEST-239"], lambda: run_unit_module("tests.games.fan_tan.test_api", "Fan-Tan atomic state and shared-helper suite failed"))
    # Execute fresh-process Acey-Deucey ordering plus sibling-state and recovery proof. (issue #823)
    run_case("API-AD-ATOMIC-001", ["AD-006", "TEST-216"], lambda: run_unit_module("tests.games.acey_deucey.test_api", "Acey-Deucey atomic state suite failed"))
    # Execute fresh-process Chuck-a-Luck ordering plus sibling-state and ledger recovery proof. (issue #825)
    run_case("API-CHUCK-ATOMIC-001", ["CHUCK-006", "CHUCK-007", "GAMECORE-007", "TEST-217", "TEST-236"], lambda: run_unit_module("tests.games.chuck_a_luck.test_engine", "Chuck-a-Luck atomic state and shared-helper suite failed"))
    # Execute fresh-process Deuces Wild terminal ordering plus sibling-state and recovery proof. (issue #827)
    run_case("API-DWVP-ATOMIC-001", ["DWVP-006", "TEST-218"], lambda: run_unit_module("tests.games.deuces_wild_video_poker.test_atomic_state", "Deuces Wild atomic state suite failed"))
    # Execute fresh-process Double Bonus terminal ordering plus sibling-state and recovery proof. (issue #830)
    run_case("API-DBVP-ATOMIC-001", ["DBVP-003", "TEST-219"], lambda: run_unit_module("tests.games.double_bonus_video_poker.test_atomic_state", "Double Bonus atomic state suite failed"))
    # Execute fresh-process Dragon Tiger terminal ordering plus sibling-state and recovery proof. (issue #833)
    run_case("API-DT-ATOMIC-001", ["DT-006", "DT-007", "GAMECORE-007", "TEST-221", "TEST-240"], lambda: (run_unit_module("tests.games.dragon_tiger.test_api", "Dragon Tiger lifecycle and shared-helper suite failed"), run_unit_module("tests.games.dragon_tiger.test_atomic_state", "Dragon Tiger atomic preparation suite failed")))
    # Execute fresh-process Joker Poker terminal ordering plus sibling-state and recovery proof. (issue #835)
    run_case("API-JP-ATOMIC-001", ["JP-006", "TEST-222"], lambda: run_unit_module("tests.games.joker_poker.test_atomic_state", "Joker Poker atomic state suite failed"))
    # Prove Hi-Lo stale terminal guesses publish through one provider-owned state boundary.
    run_case("API-HILO-ATOMIC-001", ["HILO-006", "TEST-223"], lambda: run_unit_module("tests.games.hi_lo.test_atomic_state", "Hi-Lo atomic state suite failed"))
    # Prove Jacks-or-Better rejects stale terminal writers through the real JSON provider.
    run_case("API-JOBVP-ATOMIC-001", ["JOBVP-006", "TEST-224"], lambda: run_unit_module("tests.games.jacks_or_better_video_poker.test_atomic_state", "Jacks-or-Better atomic state suite failed"))
    # Prove Let It Ride rejects stale terminal decisions through the real JSON provider.
    run_case("API-LIR-ATOMIC-001", ["LIR-006", "TEST-225"], lambda: run_unit_module("tests.games.let_it_ride.test_atomic_state", "Let It Ride atomic state suite failed"))
    # Prove Mississippi Stud rejects stale terminal decisions through the real JSON provider.
    run_case("API-MSTUD-ATOMIC-001", ["MSTUD-003", "TEST-226"], lambda: run_unit_module("tests.games.mississippi_stud.test_atomic_state", "Mississippi Stud atomic state suite failed"))
    # Prove Plinko rejects stale terminal drops through the real JSON provider.
    run_case("API-PLINKO-ATOMIC-001", ["PLINKO-006", "TEST-227"], lambda: run_unit_module("tests.games.plinko.test_atomic_state", "Plinko atomic state suite failed"))
    # Prove Red Dog rejects stale terminal decisions through the real JSON provider.
    run_case("API-RD-ATOMIC-001", ["RD-006", "TEST-228"], lambda: run_unit_module("tests.games.red_dog.test_atomic_state", "Red Dog atomic state suite failed"))
    # Prove Scratch Cards rejects stale reveal publications through the real JSON provider.
    run_case("API-SCRATCH-ATOMIC-001", ["SCRATCH-006", "TEST-229"], lambda: run_unit_module("tests.games.scratch_cards.test_atomic_state", "Scratch Cards atomic state suite failed"))
    # Execute both Sic Bo recovery and process-serialization suites without moving process ownership.
    def run_sic_bo_shared_helper_tests():
        """Run both focused Sic Bo lifecycle suites through the runner helper."""
        # Run every deterministic movement, crash-window, history, and source-topology case.
        run_unit_module("tests.games.sic_bo.test_service", "Sic Bo shared-helper service suite failed")
        # Run provider-current lifecycle and real two-process preparation evidence.
        run_unit_module("tests.games.sic_bo.test_atomic_state", "Sic Bo atomic state suite failed")

    # Bind both focused suites to the permanent Sic Bo settlement-migration evidence row. (issue #861)
    run_case("API-SIC-BO-ATOMIC-001", ["SIC-BO-006", "SIC-BO-007", "GAMECORE-007", "TEST-230", "TEST-235"], run_sic_bo_shared_helper_tests)
    # Prove Slots rejects stale spin publications through the real JSON provider.
    run_case("API-SLOT-ATOMIC-001", ["SLOT-038", "TEST-231"], lambda: run_unit_module("tests.games.slots.test_atomic_state", "Slots atomic state suite failed"))
    # Prove Teen Patti rejects stale round publications through the real JSON provider.
    run_case("API-TEEN-PATTI-ATOMIC-001", ["TEENP-003", "TEST-232"], lambda: run_unit_module("tests.games.teen_patti.test_atomic_state", "Teen Patti atomic state suite failed"))
