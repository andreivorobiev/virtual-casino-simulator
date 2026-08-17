# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own listener-free Keno and Admin-foundation registrations for #727."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest loading and focused class execution.
import unittest


# Execute the Keno drawn-ball rail layout regression without opening a listener.
def _run_keno_ball_rail_tests():
    """Run the focused Keno drawn-ball rail layout evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import keno_ball_rail_tests
    # Load only the focused Keno ball-rail class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(keno_ball_rail_tests.KenoBallRailTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when the ball-rail layout contract regresses.
    if not result.wasSuccessful():
        raise AssertionError("keno ball-rail layout suite failed")


# Execute the exact Keno paytable, engine, route, ledger, and UI policy proof.
def _run_keno_economics_tests():
    """Run the focused Keno economics and compatibility evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests.games.keno import test_economics as keno_economics_tests
    # Load the exact listener-free economics and compatibility suite.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(keno_economics_tests.KenoEconomicsTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any exact proof or current-route equation regresses.
    if not result.wasSuccessful():
        raise AssertionError("Keno economics suite failed")


# Execute the production Admin label rules and surface wiring without a listener.
def _run_admin_ledger_label_tests():
    """Run the focused Admin ledger-label localization evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import admin_ledger_label_tests
    # Load exactly the production-rule, resource-parity, and renderer-wiring assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(admin_ledger_label_tests.AdminLedgerLabelTests)
    # Execute the dependency-free suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("Admin ledger label suite failed")


# Register the Keno and Admin-foundation area at its historical runner boundary.
def run_cases(run_case):
    """Register the three reviewed listener-free cases in historical order."""
    # Record the listener-free Keno drawn-ball rail overflow regression proof.
    run_case("UI-KENO-BALL-RAIL-001", ["KENO-026", "TEST-113"], _run_keno_ball_rail_tests)
    # Record the exact all-domain Keno economics and current-route settlement proof.
    run_case("API-KENO-ECONOMICS-001", ["KENO-027", "TEST-147"], _run_keno_economics_tests)
    # Record enum normalization, locale parity, fallback, and surface-wiring proof.
    run_case("UI-ADMIN-LEDGER-LABELS-001", ["ADMIN-027", "TEST-132"], _run_admin_ledger_label_tests)
