# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free documentation, settings, and receipt API cases."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest


# Execute the complete same-origin Swagger inventory and adapter contract without a listener.
def _run_api_docs_tests():
    """Run documentation inventory, routing, and adapter-contract evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import api_docs_tests
    # Load exactly the documentation inventory and routing assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(api_docs_tests.ApiDocsTests)
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central case when any contract, asset, or routing assertion fails.
    if not result.wasSuccessful():
        # Preserve one stable value-free failure label for the compatibility runner.
        raise AssertionError("same-origin Swagger documentation suite failed")


# Execute the personal-settings, shared pagination, contract, and privacy proof without a listener.
def _run_user_settings_tests():
    """Run personal settings, self-history, pagination, and privacy evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import user_settings_tests
    # Load exactly the self-service foundation assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(user_settings_tests.UserSettingsTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("personal settings and self-history suite failed")


# Execute ledger-derived receipt classification, privacy, contract, and retry proof without a listener.
def _run_receipt_tests():
    """Run self-only receipt derivation, pagination, and replay evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import receipt_tests
    # Load exactly the self-only receipt foundation assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(receipt_tests.ReceiptDerivationTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused receipt assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("play-token receipt derivation suite failed")


# Register the self-service foundation behind the compatibility runner's historical execution point.
def run_cases(run_case):
    """Register documentation, settings, and receipt cases in reviewed order."""
    # Record complete read-only API discovery through the stable documentation URL.
    run_case("API-DOCS-001", ["API-003", "TEST-152"], _run_api_docs_tests)
    # Record the listener-free preference, pagination, contract, and self-only privacy proof.
    run_case("API-SETTINGS-001", ["USER-006", "USER-007", "USER-008", "USER-009", "TEST-103", "TEST-158"], _run_user_settings_tests)
    # Record the committed-ledger explanation, shared pagination, privacy, and exact-contract proof.
    run_case("API-RECEIPT-001", ["RECEIPT-001", "RECEIPT-002", "TEST-104"], _run_receipt_tests)
