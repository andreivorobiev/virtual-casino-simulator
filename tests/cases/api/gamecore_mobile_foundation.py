# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own listener-free GameCore and mobile-foundation registrations for #727."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest loading and focused class execution.
import unittest


# Execute the shared simple-game settlement-core proof without opening a listener.
def _run_simple_game_core_tests():
    """Run the focused simple-game settlement-core evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import simple_game_tests
    # Load only the focused settlement-core class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(simple_game_tests.SimpleGameCoreTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any focused settlement proof failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("simple-game settlement core suite failed")


# Execute the shared helper's real cross-process provider-current publication proof.
def _run_simple_game_atomic_tests():
    """Run the focused provider-atomic shared-helper evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import simple_game_atomic_tests
    # Load the exact provider-atomic shared-helper class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(simple_game_atomic_tests.SimpleGameAtomicStateTests)
    # Execute the bounded child-process proof with concise reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when either terminal round or its sibling is lost.
    if not result.wasSuccessful():
        raise AssertionError("simple-game provider-atomic suite failed")


# Execute the route-free signed-action settlement-adapter proof without a listener.
def _run_settlement_adapter_tests():
    """Run the focused settlement adapter and compatibility gateway evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import settlement_core_tests
    # Load the low-level adapter contract first.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(settlement_core_tests.SettlementAdapterTests)
    # Add the compatibility gateway contract used by every migrated game cohort.
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(settlement_core_tests.GameSettlementGatewayTests))
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any adapter proof failed or errored.
    if not result.wasSuccessful():
        raise AssertionError("settlement adapter suite failed")


# Prove every registered game remains behind the canonical settlement boundary.
def _run_catalog_settlement_boundary_tests():
    """Run the exact catalog-derived source-boundary evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import settlement_core_tests
    # Load exactly the catalog-derived source-boundary test.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(settlement_core_tests.CatalogSettlementBoundaryTests)
    # Preserve the quiet historical runner used by this prevention gate.
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    # Fail the named case when any game regresses to a direct ledger path.
    if not result.wasSuccessful():
        raise AssertionError("catalog settlement boundary suite failed")


# Execute the route-free provider-neutral game-action contract proof.
def _run_game_action_contract_tests():
    """Run immutable game-action contract and hostile conformance evidence."""
    # Import the focused suite only when either mapped API case runs.
    from tests import game_action_contract_tests
    # Load the complete immutable-contract and hostile conformance class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(game_action_contract_tests.GameActionContractTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail either named case when any contract or conformance proof failed.
    if not result.wasSuccessful():
        raise AssertionError("game-action contract suite failed")


# Execute the complete host-runnable mobile security and lifecycle suite.
def _run_mobile_core_security_tests():
    """Run native transport, session, lifecycle, link, and source evidence."""
    # Import the focused suite only when its mapped API case runs.
    from tests import mobile_core_security_tests
    # Load the complete native transport, session, config, link, and source class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(mobile_core_security_tests.MobileCoreSecurityTests)
    # Execute once with concise output and no listener or network access.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the named case when any host-runnable proof fails.
    if not result.wasSuccessful():
        raise AssertionError("mobile core security suite failed")


# Register the GameCore and mobile-foundation area at its historical boundary.
def run_cases(run_case):
    """Register the seven reviewed listener-free cases in historical order."""
    # Record exactly-once simple-game wager, replay, conflict, and recovery proof.
    run_case("API-GAMECORE-001", ["GAMECORE-001", "GAMECORE-002", "GAMECORE-007", "TEST-127", "TEST-235", "TEST-236", "TEST-237", "TEST-238", "TEST-239", "TEST-240"], _run_simple_game_core_tests)
    # Record provider-current merge, concurrency, and catalog-adoption evidence.
    run_case("API-GAMECORE-005", ["GAMECORE-005", "GAMECORE-006", "GAMECORE-007", "STORAGE-017", "TEST-233", "TEST-234", "TEST-235", "TEST-236", "TEST-237", "TEST-238", "TEST-239", "TEST-240", "TEST-245"], _run_simple_game_atomic_tests)
    # Record signed settlement routing, replay, conflict, and recovery proof.
    run_case("API-GAMECORE-002", ["GAMECORE-003", "LEDGER-033", "TEST-164"], _run_settlement_adapter_tests)
    # Record the catalog-wide canonical settlement-boundary prevention gate.
    run_case("API-GAMECORE-004", ["LEDGER-032", "GAMECORE-004", "GAMECORE-008", "TEST-157", "TEST-241"], _run_catalog_settlement_boundary_tests)
    # Record bounded game-action identity, planner order, and receipt semantics.
    run_case("API-GAMECORE-003", ["CORE-031"], _run_game_action_contract_tests)
    # Record provider-neutral terminal resolution and no-planner replay semantics.
    run_case("API-GAME-ACTION-LIFECYCLE-001", ["CORE-031", "STORAGE-013", "TEST-174"], _run_game_action_contract_tests)
    # Record native transport, session, lifecycle, link, and source-policy proof.
    run_case("API-MOBILE-CORE-001", ["CORE-032", "AUTH-019", "SEC-016", "SESSION-013", "TEST-172"], _run_mobile_core_security_tests)
