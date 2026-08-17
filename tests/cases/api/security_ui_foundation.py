# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own listener-free security and UI-foundation registrations for #727."""

# Import repository-path discovery for the restricted-preview security suite.
from pathlib import Path
# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest

# Resolve the repository root without importing the compatibility runner.
ROOT = Path(__file__).resolve().parents[3]


# Execute the complete disabled passwordless magic-link proof without opening a listener.
def _run_magic_link_tests():
    """Run the focused disabled passwordless-login lifecycle evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import magic_link_tests
    # Load only the focused magic-link class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(magic_link_tests.MagicLinkServiceTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case while unittest retains exact assertion detail.
    if not result.wasSuccessful():
        raise AssertionError("passwordless magic-link suite failed")


# Discover every focused restricted-preview security module without opening a listener.
def _run_restricted_preview_security_tests():
    """Run request, access, session, and browser-helper security evidence."""
    # Load the package directory through unittest's standard deterministic discovery.
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests" / "security"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    # Execute the suite with a concise in-process result collector.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case while discovery retains exact failing-test diagnostics.
    if not result.wasSuccessful():
        raise AssertionError("restricted-preview security suite failed")


# Execute exact frontend safety helpers and tracked-source contracts without a listener.
def _run_frontend_safety_tests():
    """Run security, feedback, motion, and runtime-state source evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import frontend_safety_tests
    # Load exactly the browser-free frontend-safety class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(frontend_safety_tests.FrontendSafetyTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case while unittest retains exact assertion detail.
    if not result.wasSuccessful():
        raise AssertionError("frontend safety suite failed")


# Execute the escape-by-default helper and monotonic innerHTML baseline proof.
def _run_inner_html_template_tests():
    """Run helper, scanner, reduction, and fail-closed template evidence."""
    # Import the focused governance suite only when its mapped API case runs.
    from tests import inner_html_template_tests
    # Load exactly the innerHTML template-governance class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(inner_html_template_tests.InnerHtmlTemplateTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any helper or baseline assertion regresses.
    if not result.wasSuccessful():
        raise AssertionError("innerHTML template governance suite failed")


# Execute the complete listener-free catalog repeat-bet contract.
def _run_repeat_bet_tests():
    """Run catalog, localization, delegation, guard, and timer evidence."""
    # Import the focused repeat-bet suite only when its mapped API case runs.
    from tests import repeat_bet_tests
    # Load exactly the catalog-wide repeat-bet class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(repeat_bet_tests.RepeatBetTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any governed game contract regresses.
    if not result.wasSuccessful():
        raise AssertionError("repeat-bet suite failed")


# Register the security and UI-foundation area at its historical runner boundary.
def run_cases(run_case):
    """Register the five reviewed listener-free cases in historical order."""
    # Record the disabled passwordless-login lifecycle proof.
    run_case("API-MAGIC-LINK-001", ["MAGIC-001", "MAGIC-002", "MAGIC-003", "TEST-118"], _run_magic_link_tests)
    # Record restricted-preview request, access, session, and browser-helper security proof.
    run_case("API-SEC-PREVIEW-001", ["SEC-010", "SESSION-006", "ADMIN-024", "AUTH-007", "TEST-047"], _run_restricted_preview_security_tests)
    # Record invitation-log, toast, motion, Roulette, mobile, runtime, and autoplay recovery proof.
    run_case("FRONTEND-SAFETY-001", ["SEC-013", "SEC-015", "UX-021", "UX-027", "CORE-028", "ROU-043", "TEENP-002", "MOTION-010", "AUTO-015", "AUDIO-010", "ADMIN-032", "TEST-136", "TEST-153", "TEST-155", "TEST-156"], _run_frontend_safety_tests)
    # Record the canonical escape boundary, Admin migration, and monotonic remainder gate.
    run_case("GOV-INNER-HTML-001", ["CORE-033", "SEC-017", "TEST-186"], _run_inner_html_template_tests)
    # Record all localized one-click repeat foundations under permanent ownership.
    run_case("UI-REPEAT-BET-001", ["UX-022", "TEST-137"], _run_repeat_bet_tests)
