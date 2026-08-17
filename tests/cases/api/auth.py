# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free authentication infrastructure cases for the API lane."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest


# Execute the exact one-time-token infrastructure class without opening a listener.
def _run_one_time_token_tests():
    """Run deterministic one-time-token lifecycle and privacy evidence."""
    # Import the focused infrastructure suite only when the mapped API case runs.
    from tests import one_time_token_tests
    # Load exactly the security-focused one-time-token test class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(one_time_token_tests.OneTimeTokenTests)
    # Execute the isolated suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped API case when any focused assertion fails or errors.
    if not result.wasSuccessful():
        # Preserve a stable value-free central diagnostic.
        raise AssertionError("one-time-token infrastructure suite failed")


# Execute the exact transactional-mail infrastructure class without opening a listener.
def _run_transactional_mail_tests():
    """Run disabled-provider, idempotency, privacy, retry, and template evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import mail_tests
    # Load exactly the transactional-mail test class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(mail_tests.MailServiceTests)
    # Execute the isolated provider-free suite with concise standard output.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any focused assertion fails or errors.
    if not result.wasSuccessful():
        # Preserve a stable secret-free central diagnostic.
        raise AssertionError("transactional-mail infrastructure suite failed")


# Execute the exact invitation infrastructure class without opening a listener.
def _run_invitation_tests():
    """Run disabled issuance, enrollment recovery, privacy, and convergence evidence."""
    # Import the focused invitation lifecycle suite lazily so API-only discovery remains lightweight.
    from tests import invitation_tests
    # Load exactly the invitation service acceptance class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(invitation_tests.InvitationServiceTests)
    # Run the focused service suite with the repository's quiet test runner.
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    # Fail the mapped API gate when any lifecycle, privacy, or concurrency assertion fails.
    if not result.wasSuccessful():
        # Raise one bounded failure naming no recipient, bearer, or credential material.
        raise AssertionError("invitation enrollment infrastructure suite failed")


# Execute the exact verified-email activation class without opening a listener.
def _run_verified_email_enrollment_tests():
    """Run pending, cancellation, replay, and recovery saga evidence."""
    # Import the focused provider-free suite only when its mapped case runs.
    from tests import verified_email_enrollment_tests
    # Load exactly the pending, cancellation, replay, and recovery assertions.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(verified_email_enrollment_tests.VerifiedEmailEnrollmentTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the central named case when any exact saga proof failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the mapped failure label stable.
        raise AssertionError("verified email enrollment suite failed")


# Execute the exact password-recovery infrastructure class without opening a listener.
def _run_password_reset_tests():
    """Run enumeration-safe password-recovery lifecycle evidence."""
    # Import the focused recovery suite lazily so API-only discovery stays lightweight.
    from tests import password_reset_tests
    # Load exactly the recovery service acceptance class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(password_reset_tests.PasswordResetServiceTests)
    # Run the focused service suite with the repository's quiet test runner.
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    # Fail the mapped API gate when any enumeration-safety or lifecycle assertion fails.
    if not result.wasSuccessful():
        # Raise one bounded failure naming no recipient, bearer, or credential material.
        raise AssertionError("password recovery infrastructure suite failed")


# Register the authentication area through callbacks owned by the compatibility runner.
def run_cases(run_case, run_oauth_mock_tests, validate_deployment_bootstrap, run_server_authority_tests):
    """Register authentication infrastructure cases in historical execution order."""
    # Centrally discover all mocked and disabled OAuth tests before any listener starts.
    run_case("OAUTH-MOCK-001", ["OAUTH-001", "OAUTH-002", "OAUTH-003", "OAUTH-004", "OAUTH-005", "OAUTH-007", "OAUTH-008", "OAUTH-009", "OAUTH-012", "OAUTH-013", "AUTH-017", "TEST-045", "TEST-093", "TEST-167", "TEST-168"], run_oauth_mock_tests)
    # Record focused deployment-default coverage before starting the normal loopback API server.
    run_case("API-AUTH-DEPLOYMENT-001", ["AUTH-006", "TEST-041"], validate_deployment_bootstrap)
    # Certify the matrix and shared hostile-client boundary before starting a listener.
    run_case("API-SEC-001", [*([f"SEC-{index:03d}" for index in range(1, 10)]), "SEC-014", "TEST-163"], run_server_authority_tests)
    # Record the purpose-bound one-time-token platform proof.
    run_case("API-OTT-001", ["OTT-001", "OTT-002", "TEST-089"], _run_one_time_token_tests)
    # Record the complete listener-free transactional-mail platform proof.
    run_case("API-MAIL-001", ["MAIL-001", "MAIL-002", "MAIL-003", "MAIL-004", "MAIL-005", "MAIL-006", "TEST-090"], _run_transactional_mail_tests)
    # Record the listener-free invitation platform proof under its permanent requirements.
    run_case("API-INVITE-001", ["INVITE-001", "INVITE-002", "INVITE-003", "INVITE-004", "INVITE-005", "INVITE-006", "TEST-091"], _run_invitation_tests)
    # Record no-preverification identity, ledger funding, no-session, cancellation, and recovery proof.
    run_case("API-VERIFIED-EMAIL-001", ["AUTH-018", "USER-010", "TEST-171"], _run_verified_email_enrollment_tests)
    # Record the listener-free password-recovery proof under its permanent requirements.
    run_case("API-RESET-001", ["RESET-001", "RESET-002", "RESET-003", "RESET-004", "TEST-097", "TEST-158"], _run_password_reset_tests)
