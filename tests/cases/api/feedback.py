# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register the listener-free feedback case for the API lane."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest


# Execute the exact feedback service acceptance class without opening a listener.
def _run_feedback_tests():
    """Run feedback lifecycle, concurrency, retention, and image-safety evidence."""
    # Import the focused suite lazily so unrelated runners do not require image tooling.
    from tests import feedback_tests
    # Load exactly the feedback service acceptance class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(feedback_tests.FeedbackServiceTests)
    # Execute the focused suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped API case when any recovery, privacy, or concurrency proof fails.
    if not result.wasSuccessful():
        # Preserve one stable value-free failure label for the compatibility runner.
        raise AssertionError("manual problem-report service suite failed")


# Register the feedback area behind the compatibility runner's historical execution point.
def run_cases(run_case):
    """Register the feedback case under its permanent requirement ownership."""
    # Map the manual-only slice to its unique permanent test requirement.
    run_case("API-FEEDBACK-001", ["CORE-027", "ADMIN-025", "SEC-011", "I18N-005", "TEST-094"], _run_feedback_tests)
