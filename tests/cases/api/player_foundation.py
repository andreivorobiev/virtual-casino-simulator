#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own listener-free player-foundation registrations for the #727 runner split."""

import sys
import unittest
from pathlib import Path


def run_cases(run_case, run_game_frontend_node_test):
    """Register the historical player-foundation block without owning runner lifecycle."""

    # Execute the opt-in wellness, current-session summary, concurrency, and neutral-copy proof.
    def run_wellness_tests():
        # Import the focused suite only when its mapped API case runs.
        from tests import wellness_tests

        # Load and run the exact session-wellness foundation assertions.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(wellness_tests.SessionWellnessTests)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve unittest detail while keeping the named failure stable.
        if not result.wasSuccessful():
            raise AssertionError('session wellness foundation suite failed')
        # Keep Node subprocess execution supplied by the compatibility runner.
        run_game_frontend_node_test(
            Path('tests/wellness_browser_contract.test.mjs'),
            'session wellness browser controller suite failed',
        )

    # Record the deterministic timer, reload, visibility, focus, pause, stop, and locale proof.
    run_case('API-WELLNESS-001', ['WELL-001', 'WELL-002', 'TEST-105'], run_wellness_tests)

    # Execute the curated server-only What's New eligibility proof without opening a listener.
    def run_whats_new_tests():
        # Load only the focused What's New foundation assertions.
        from tests import whats_new_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(whats_new_tests.WhatsNewTests)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve unittest detail while keeping the named failure text secret-safe.
        if not result.wasSuccessful():
            raise AssertionError("what's new foundation suite failed")

    # Record curated opt-in, disabled-catalog, privacy, idempotency, route, and contract proof.
    run_case('API-TOUR-001', ['TOUR-001', 'TOUR-002', 'TEST-106'], run_whats_new_tests)

    # Execute the inactive Challenge Points policy kernel without a listener or provider.
    def run_challenge_policy_tests():
        # Import only the synthetic policy evidence after the named case is selected.
        from tests import challenge_policy_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            challenge_policy_tests.ChallengePolicyTests
        )
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the registered case on any authority, replay, attempt, or wallet-separation regression.
        if not result.wasSuccessful():
            raise AssertionError('Challenge Points policy foundation suite failed')

    # Bind the permanent Challenge policy requirements to one exact listener-free case.
    run_case(
        'CHALLENGE-POLICY-001',
        ['CHALLENGE-001', 'CHALLENGE-002', 'CHALLENGE-003', 'TEST-263'],
        run_challenge_policy_tests,
    )

    # Execute the complete player self-service batch proof without opening a listener.
    def run_self_service_batch_tests():
        # Import the focused classes only when the mapped case executes.
        from tests import self_service_batch_tests

        loader = unittest.defaultTestLoader
        suite = unittest.TestSuite()
        # Preserve the replay, profile, compare, copy, and contract class order.
        for cls in (
            self_service_batch_tests.ReplayFoundationTests,
            self_service_batch_tests.TableProfileTests,
            self_service_batch_tests.CompareGamesTests,
            self_service_batch_tests.SelfServiceCopyTests,
            self_service_batch_tests.SelfServiceApiContractTests,
        ):
            suite.addTests(loader.loadTestsFromTestCase(cls))
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve unittest detail while keeping the named failure text secret-safe.
        if not result.wasSuccessful():
            raise AssertionError('player self-service batch suite failed')

    # Record the listener-free replay, table-profile, and compare proof.
    run_case(
        'API-SELF-SERVICE-BATCH-001',
        ['REPLAY-001', 'REPLAY-002', 'PROFILE-001', 'PROFILE-002', 'COMPARE-001', 'TEST-108', 'TEST-109', 'TEST-110'],
        run_self_service_batch_tests,
    )

    # Execute the complete guest-to-account conversion proof without opening a listener.
    def run_guest_conversion_tests():
        # Load only the focused conversion class.
        from tests import guest_conversion_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(guest_conversion_tests.GuestConversionTests)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve unittest detail while keeping the named failure text secret-safe.
        if not result.wasSuccessful():
            raise AssertionError('guest conversion suite failed')

    # Record explicit, wallet-preserving conversion plus idempotent analytics convergence.
    run_case(
        'API-CONVERT-001',
        ['CONVERT-001', 'CONVERT-002', 'CONVERT-003', 'GUEST-007', 'TEST-111', 'TEST-158', 'TEST-195'],
        run_guest_conversion_tests,
    )

    # Execute the Admin-assisted conversion service and route contract proof. (#701)
    def run_admin_guest_conversion_tests():
        # Import the focused suite lazily after shared test storage is ready.
        from tests import admin_guest_conversion_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            admin_guest_conversion_tests.AdminGuestConversionTests
        )
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named case on any wallet, audit, lifecycle, or authorization regression.
        if not result.wasSuccessful():
            raise AssertionError('Admin-assisted guest conversion suite failed')

    # Map explicit support confirmation plus unchanged analytics convergence behavior.
    run_case(
        'API-ADMIN-GUEST-CONVERT-001',
        ['ADMIN-035', 'GUEST-007', 'TEST-193', 'TEST-195'],
        run_admin_guest_conversion_tests,
    )

    # Execute the product account-spine proof without opening a listener.
    def run_account_spine_tests():
        # Load only the focused product account-spine class.
        from tests import account_spine_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(account_spine_tests.ProductAccountSpineTests)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve unittest detail while keeping the named failure text secret-safe.
        if not result.wasSuccessful():
            raise AssertionError('product account-spine suite failed')

    # Record disabled signup/passkeys, owner-only Admin delegation, and reporter-status proof.
    run_case(
        'API-ACCOUNT-SPINE-001',
        ['AUTH-010', 'AUTH-012', 'AUTH-015', 'AUTH-016', 'ADMIN-028', 'ADMIN-033', 'OAUTH-011', 'OAUTH-012', 'RESET-004', 'FEEDBACK-005', 'I18N-009', 'TEST-112', 'TEST-138', 'TEST-158', 'TEST-167'],
        run_account_spine_tests,
    )

    # Execute the privacy-safe Admin session-control core without opening a listener.
    def run_admin_session_control_tests():
        # Load only the focused session inventory and revocation class.
        from tests import admin_session_control_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            admin_session_control_tests.AdminSessionControlTests
        )
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve unittest detail while keeping the named failure text secret-safe.
        if not result.wasSuccessful():
            raise AssertionError('Admin session-control suite failed')

    # Record bounded inventory, aliases, atomic revocation, and fail-closed storage proof.
    run_case(
        'API-ADMIN-SESSIONS-001',
        ['SESSION-006', 'SESSION-007', 'SESSION-008', 'ADMIN-028', 'TEST-143'],
        run_admin_session_control_tests,
    )

    # Execute the repository-only static marketing-site proof without a listener.
    def run_marketing_site_tests():
        # Import the semantic, resource, accessibility, module, matrix, and boundary suite.
        from tests import marketing_site_tests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(marketing_site_tests.MarketingSiteTests)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Preserve detailed unittest output while keeping the named failure stable.
        if not result.wasSuccessful():
            raise AssertionError('TiltSeven repository-scaffold suite failed')

    # Record the bilingual, no-network, no-publication, and visual-ownership proof.
    run_case(
        'STATIC-MARKETING-001',
        ['MARKETING-001', 'MARKETING-002', 'MARKETING-003', 'TEST-107'],
        run_marketing_site_tests,
    )
