# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own listener-free catalog-expansion registrations for the #727 runner split."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest


# Execute the Color Wheel rules and settlement proof without opening a listener.
def _run_color_wheel_tests():
    """Run the focused Color Wheel payout, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import color_wheel_tests
    # Load exactly the Color Wheel assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(color_wheel_tests.ColorWheelTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("color wheel suite failed")


# Execute the Poker Dice rules and settlement proof without opening a listener.
def _run_poker_dice_tests():
    """Run the focused Poker Dice payout, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import poker_dice_tests
    # Load exactly the Poker Dice assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(poker_dice_tests.PokerDiceTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("poker dice suite failed")


# Execute the Boule rules and settlement proof without opening a listener.
def _run_boule_tests():
    """Run the focused Boule payout, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import boule_tests
    # Load exactly the Boule assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(boule_tests.BouleTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("boule suite failed")


# Execute the Faro rules and settlement proof without opening a listener.
def _run_faro_tests():
    """Run the focused Faro payout, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests.games.faro import test_api as faro_tests
    # Load exactly the Faro assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(faro_tests.FaroTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("faro suite failed")


# Execute the Trente et Quarante rules and settlement proof without opening a listener.
def _run_trente_et_quarante_tests():
    """Run the focused Trente et Quarante payout, retry, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests.games.trente_et_quarante import test_api as trente_et_quarante_tests
    # Load exactly the Trente et Quarante assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(trente_et_quarante_tests.TrenteEtQuaranteTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("trente et quarante suite failed")


# Execute the Pachinko rules and settlement proof without opening a listener.
def _run_pachinko_tests():
    """Run the focused Pachinko pocket, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests.games.pachinko import test_api as pachinko_tests
    # Load exactly the Pachinko assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(pachinko_tests.PachinkoTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("pachinko suite failed")


# Execute the Coin Pusher rules and settlement proof without opening a listener.
def _run_coin_pusher_tests():
    """Run the focused Coin Pusher cascade, retry, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import coin_pusher_tests
    # Load exactly the Coin Pusher assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(coin_pusher_tests.CoinPusherTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("coin pusher suite failed")


# Execute the Marble Race rules and settlement proof without opening a listener.
def _run_marble_race_tests():
    """Run the focused Marble Race payout, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import marble_race_tests
    # Load exactly the Marble Race assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(marble_race_tests.MarbleRaceTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("marble race suite failed")


# Execute the Pattern Draw rules and settlement proof without opening a listener.
def _run_pattern_draw_tests():
    """Run the focused Pattern Draw payout, retry, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import pattern_draw_tests
    # Load exactly the Pattern Draw assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(pattern_draw_tests.PatternDrawTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("pattern draw suite failed")


# Execute the Lucky Grid rules and settlement proof without opening a listener.
def _run_lucky_grid_tests():
    """Run the focused Lucky Grid payout, retry, and house-edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import lucky_grid_tests
    # Load exactly the Lucky Grid assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(lucky_grid_tests.LuckyGridTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("lucky grid suite failed")


# Execute the Daily Draw Lab rules and settlement proof without opening a listener.
def _run_daily_draw_lab_tests():
    """Run the focused Daily Draw Lab payout, retry, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests.games.daily_draw_lab import test_api as daily_draw_lab_tests
    # Load exactly the Daily Draw Lab assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(daily_draw_lab_tests.DailyDrawLabTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("daily draw lab suite failed")


# Execute the Four Card Poker rules and settlement proof without opening a listener.
def _run_four_card_poker_tests():
    """Run Four Card Poker ranking, settlement, replay, recovery, and edge evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests.games.four_card_poker import test_api as four_card_poker_tests
    # Load exactly the Four Card Poker assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(four_card_poker_tests.FourCardPokerTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("four card poker suite failed")


# Register the catalog-expansion area behind the runner's historical execution point.
def run_cases(run_case):
    """Register the twelve catalog-expansion cases in reviewed historical order."""
    # Record Color Wheel payout, retry, and house-edge proof.
    run_case("API-COLOR-WHEEL-001", ["CWHEEL-001", "CWHEEL-002", "TEST-128"], _run_color_wheel_tests)
    # Record Poker Dice payout, retry, and house-edge proof.
    run_case("API-POKER-DICE-001", ["PDICE-001", "PDICE-002", "TEST-129"], _run_poker_dice_tests)
    # Record Boule payout, house-number, retry, and house-edge proof.
    run_case("API-BOULE-001", ["BOULE-001", "BOULE-002", "TEST-130"], _run_boule_tests)
    # Record Faro win, lose, push, split, retry, and house-edge proof.
    run_case("API-FARO-001", ["FARO-001", "FARO-002", "TEST-131"], _run_faro_tests)
    # Record Trente et Quarante row, colour, refait, retry, and house-edge proof.
    run_case("API-TRENTE-ET-QUARANTE-001", ["TEQ-001", "TEQ-002", "TEST-119"], _run_trente_et_quarante_tests)
    # Record Pachinko pocket, push, retry, and house-edge proof.
    run_case("API-PACHINKO-001", ["PACH-001", "PACH-002", "TEST-120"], _run_pachinko_tests)
    # Record Coin Pusher cascade, hold, retry, and house-edge proof.
    run_case("API-COIN-PUSHER-001", ["COINP-001", "COINP-002", "TEST-121"], _run_coin_pusher_tests)
    # Record Marble Race win, podium, retry, and house-edge proof.
    run_case("API-MARBLE-RACE-001", ["MARBLE-001", "MARBLE-002", "TEST-122"], _run_marble_race_tests)
    # Record Pattern Draw line, cross, full, retry, and house-edge proof.
    run_case("API-PATTERN-DRAW-001", ["PATTERN-001", "PATTERN-002", "TEST-123"], _run_pattern_draw_tests)
    # Record Lucky Grid match, retry, and house-edge proof.
    run_case("API-LUCKY-GRID-001", ["LGRID-001", "LGRID-002", "TEST-124"], _run_lucky_grid_tests)
    # Record Daily Draw Lab pick, hit, retry, and house-edge proof.
    run_case("API-DAILY-DRAW-LAB-001", ["DDLAB-001", "DDLAB-002", "TEST-125"], _run_daily_draw_lab_tests)
    # Record Four Card Poker ranking, settlement, replay, recovery, and edge proof.
    run_case("API-FOUR-CARD-POKER-001", ["FOURCP-001", "FOURCP-002", "TEST-126"], _run_four_card_poker_tests)
