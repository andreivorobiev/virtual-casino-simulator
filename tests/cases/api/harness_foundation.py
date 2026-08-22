# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own listener-free harness-foundation API registrations for #727."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest loading and focused class execution.
import unittest


# Execute listener-free request-latency policy and scheduler evidence.
def _run_request_latency_unit_tests():
    """Run the bounded request-latency benchmark-policy unit suite."""
    # Import the benchmark-policy suite only when its mapped case runs.
    from tests.unit import request_latency_benchmark_tests
    # Load exactly the bounded request-latency policy class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(request_latency_benchmark_tests.RequestLatencyBenchmarkTests)
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when policy, privacy, callback, or scheduler evidence fails.
    if not result.wasSuccessful():
        raise AssertionError("request-latency baseline unit suite failed")


# Execute the exact-138 planner, barrier, aggregate, and workflow evidence.
def _run_concurrent_browser_138_harness_tests():
    """Run the listener-free 138-context qualification harness suite."""
    # Import the focused harness suite only when its mapped case runs.
    from tests.unit import concurrent_browser_138_tests
    # Load only the exact 138-context harness class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(concurrent_browser_138_tests.ConcurrentBrowser138Tests)
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any planner, barrier, or aggregate proof fails.
    if not result.wasSuccessful():
        raise AssertionError("138-context browser qualification harness unit suite failed")


# Execute the listener-free 50,000-cycle allocation and resume evidence.
def _run_ui_50000_harness_tests():
    """Run the exact UI 50,000-cycle harness policy suite."""
    # Import the focused harness suite only when its mapped case runs.
    from tests.unit import ui_50000_control_schedule_tests, ui_50000_tests
    # Load both the exact allocation/resume class and extracted control-schedule class under the same required API case.
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(ui_50000_tests.UI50000HarnessTests), unittest.defaultTestLoader.loadTestsFromTestCase(ui_50000_control_schedule_tests.UI50000ControlScheduleTests)))
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any harness policy proof fails.
    if not result.wasSuccessful():
        raise AssertionError("50,000-cycle UI harness unit suite failed")


# Execute service-free non-finite money boundary evidence.
def _run_nonfinite_money_unit_tests():
    """Run shared validation, ledger, MHVP, and JSON persistence evidence."""
    # Import the focused money suite only when its mapped case runs.
    from tests import nonfinite_money_tests
    # Load only the strict non-finite money boundary class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(nonfinite_money_tests.NonfiniteMoneyTests)
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when validation or persistence evidence fails.
    if not result.wasSuccessful():
        raise AssertionError("non-finite money boundary unit suite failed")


# Execute Guest Trial terminal-ledger evidence without opening a listener.
def _run_guest_teardown_ledger_tests():
    """Run terminal debit, replay, reconstruction, and provider-parity evidence."""
    # Import the focused money-lifecycle suite only when its mapped case runs.
    from tests import guest_teardown_ledger_tests
    # Load the exact replay, reconstruction, and economics-isolation class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(guest_teardown_ledger_tests.GuestTeardownLedgerTests)
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any wallet-lifecycle assertion fails.
    if not result.wasSuccessful():
        raise AssertionError("Guest Trial terminal-ledger suite failed")


# Register the harness-foundation block at its historical pre-listener boundary.
def run_cases(run_case):
    """Register the five reviewed listener-free cases in historical order."""
    # Record request-latency policy without executing either provider benchmark.
    run_case("REQUEST-LATENCY-UNIT-001", ["TEST-148"], _run_request_latency_unit_tests)
    # Record exact-user allocation, synchronization, privacy, and cleanup policy.
    run_case("BROWSER-138-HARNESS-001", ["AUTH-001", "AUTH-002", "SESSION-001", "SESSION-005", "TEST-039", "TEST-042", "TEST-142", "CORE-021"], _run_concurrent_browser_138_harness_tests)
    # Record exact-source allocation, control classification, and safe resume proof.
    run_case("UI-50000-HARNESS-001", ["TEST-042", "TEST-047", "TEST-092"], _run_ui_50000_harness_tests)
    # Record listener-free finite validation and persistence proof.
    run_case("MONEY-NONFINITE-UNIT-001", ["CORE-025", "LEDGER-027", "MHVP-006", "TEST-055"], _run_nonfinite_money_unit_tests)
    # Record exactly-once Guest terminal debit, parity, replay, and reconstruction.
    run_case("API-GUEST-TEARDOWN-LEDGER-001", ["LEDGER-035", "AUTH-020", "LEDGER-037", "TEST-188", "TEST-194"], _run_guest_teardown_ledger_tests)
