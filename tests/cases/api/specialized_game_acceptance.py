# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free specialized-game acceptance cases for the API lane."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest


# Execute the Double Bonus Video Poker engine and settlement proof without opening a listener.
def _run_double_bonus_video_poker_tests():
    """Run Double Bonus engine, settlement, replay, recovery, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import double_bonus_video_poker_tests
    # Load exactly the Double Bonus engine and service assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(double_bonus_video_poker_tests.DoubleBonusVideoPokerTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused Double Bonus assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("double bonus video poker suite failed")


# Execute the Mississippi Stud engine and settlement proof without opening a listener.
def _run_mississippi_stud_tests():
    """Run Mississippi Stud engine, street settlement, replay, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import mississippi_stud_tests
    # Load exactly the Mississippi Stud engine and service assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(mississippi_stud_tests.MississippiStudTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused Mississippi Stud assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("mississippi stud suite failed")


# Execute the Teen Patti engine, authenticated routes, and settlement proof without opening a listener.
def _run_teen_patti_tests():
    """Run Teen Patti ranking, settlement, replay, recovery, route, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import teen_patti_tests
    # Load exactly the Teen Patti engine, service, and direct-route assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(teen_patti_tests.TeenPattiTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused Teen Patti assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("teen patti suite failed")


# Execute corrected cross-game copy and shared keyboard-focus evidence without opening a listener.
def _run_game_polish_tests():
    """Run return semantics, privacy, localization, and keyboard-focus evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import game_polish_tests
    # Load exactly the copy and focus assertions allocated to TEST-117.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(game_polish_tests.GamePolishTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused copy or focus assertion failed.
    if not result.wasSuccessful():
        # Preserve one stable diagnostic while unittest retains assertion detail.
        raise AssertionError("cross-game copy and focus suite failed")


# Execute the listener-free Slots economics, route, ledger-equation, and copy regressions.
def _run_slots_economics_tests():
    """Run module-owned Slots economics acceptance without a browser or listener."""
    # Import the bounded SLOT-036 test module only when its mapped case runs.
    from tests.games.slots import test_economics
    # Load exactly the module-owned economics assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_economics.SlotsEconomicsTests)
    # Run through the shared fail-closed unittest result collector.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named API case when any focused invariant failed or errored.
    if not result.wasSuccessful():
        # Raise one stable harness error after unittest printed exact diagnostics.
        raise AssertionError("Slots economics suite failed")


# Register the specialized-game area behind the compatibility runner's historical execution point.
def run_cases(run_case):
    """Register specialized-game and cross-game-polish cases in reviewed order."""
    # Record Double Bonus paytable, settlement, replay, recovery, and house-edge proof.
    run_case("API-DOUBLE-BONUS-VIDEO-POKER-001", ["DBVP-001", "DBVP-002", "TEST-114"], _run_double_bonus_video_poker_tests)
    # Record Mississippi Stud paytable, three-street settlement, replay, recovery, and edge proof.
    run_case("API-MISSISSIPPI-STUD-001", ["MSTUD-001", "MSTUD-002", "TEST-115"], _run_mississippi_stud_tests)
    # Record Teen Patti ranking, settlement, replay, recovery, route, and edge proof.
    run_case("API-TEEN-PATTI-001", ["TEENP-001", "TEENP-002", "TEST-116"], _run_teen_patti_tests)
    # Record return semantics, identifier privacy, Russian terminology, and focus proof.
    run_case("UI-GAME-POLISH-001", ["I18N-010", "UX-020", "TEST-117"], _run_game_polish_tests)
    # Record the complete browser-free Slots economics acceptance.
    run_case("API-SLOT-ECONOMICS-001", ["SLOT-036"], _run_slots_economics_tests)
