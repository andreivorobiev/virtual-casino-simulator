# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free delivery-infrastructure cases for the API lane."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest discovery and focused class execution.
import unittest


# Execute the complete non-mutating edge preparation proof before any listener starts.
def _run_edge_gate_tests():
    """Run restricted-preview templates, observation, and rollback evidence."""
    # Import the focused edge suite only when its mapped API case runs.
    from tests import edge_gate_tests
    # Load only the focused TEST-050 unit-test class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(edge_gate_tests.EdgeGateTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any focused edge proof failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the diagnostic secret-safe.
        raise AssertionError("restricted-preview edge preparation suite failed")


# Execute the complete deployment build-provenance proof without repository writes.
def _run_release_env_tests():
    """Run release-environment fragment and service-ordering evidence."""
    # Import the focused provenance suite only when its mapped API case runs.
    from tests import release_env_tests
    # Load only the focused deployment fragment class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(release_env_tests.ReleaseEnvFragmentTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any focused provenance proof failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the diagnostic secret-safe.
        raise AssertionError("deployment build provenance suite failed")


# Execute compatibility-owned predecessor selection without contacting GitHub Releases.
def _run_release_predecessor_tests():
    """Run compatibility-owned rollback selection and manifest binding."""
    # Import the predecessor suite only when its mapped API case runs.
    from tests import release_predecessor_tests
    # Load only the focused predecessor policy class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(release_predecessor_tests.ReleasePredecessorTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any predecessor assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("release predecessor policy suite failed")


# Execute the split monitor bearer and digest proof without opening a listener.
def _run_monitor_config_tests():
    """Run monitor validation, mismatch refusal, and atomic-repair evidence."""
    # Import the monitor suite only when its mapped API case runs.
    from tests import monitor_config_tests
    # Load only the focused root-managed monitor configuration class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(monitor_config_tests.MonitorConfigTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any monitor assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the diagnostic secret-safe.
        raise AssertionError("monitor configuration suite failed")


# Execute the inert production-workflow policy proof without GitHub, SSH, or deployment.
def _run_cicd_deployment_tests():
    """Run immutable-publication and rollback workflow policy evidence."""
    # Import the workflow suite only when its mapped API case runs.
    from tests import cicd_deployment_tests
    # Load only the focused protected-main workflow policy class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(cicd_deployment_tests.CicdDeploymentWorkflowTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any workflow assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("production CI/CD workflow suite failed")


# Execute the listener-free pull-poller comparison and activation-order proofs.
def _run_release_poller_tests():
    """Run pull-delivery comparison, rollback ordering, and lag evidence."""
    # Import the poller suite only when its mapped API case runs.
    from tests import release_poller_tests
    # Load only the focused host-poller contract class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(release_poller_tests.ReleasePollerTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any pull-delivery assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("release poller suite failed")


# Execute listener-free cancellation and sharded qualification policy proofs.
def _run_ci_qualification_tests():
    """Run ordinary-workflow acceleration and gate-job evidence."""
    # Import the workflow suite only when its mapped API case runs.
    from tests import cicd_deployment_tests
    # Load only the focused acceleration policy class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(cicd_deployment_tests.CiQualificationWorkflowTests)
    # Execute the suite with concise in-process reporting.
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    # Fail the mapped gate when any qualification assertion failed or errored.
    if not result.wasSuccessful():
        # Preserve unittest detail while keeping the named failure stable.
        raise AssertionError("qualification acceleration policy suite failed")


# Register the delivery-infrastructure area in its historical execution order.
def run_cases(run_case):
    """Register edge, release, monitor, deployment, poller, and CI policy cases."""
    # Record the listener-free edge templates, validator, observation, and rollback proof.
    run_case("EDGE-PREPARATION-001", ["CORE-024", "TOOL-005", "TOOL-021", "TEST-050", "TEST-258"], _run_edge_gate_tests)
    # Record the listener-free deployment provenance fragment and service-unit ordering proof.
    run_case("DEPLOY-PROVENANCE-001", ["TOOL-007", "TEST-098"], _run_release_env_tests)
    # Record exact compatibility-owned rollback selection and manifest binding.
    run_case("RELEASE-PREDECESSOR-001", ["TOOL-003", "TOOL-008", "TOOL-011", "TEST-133"], _run_release_predecessor_tests)
    # Record listener-free monitor validation, mismatch refusal, and explicit atomic repair.
    run_case("MONITOR-CONFIG-001", ["OPS-006", "TOOL-008", "TEST-133"], _run_monitor_config_tests)
    # Record immutable publication, hosted assets, SSH boundaries, and rollback behavior.
    run_case("DEPLOY-CICD-001", ["TOOL-008", "TOOL-011", "TEST-133"], _run_cicd_deployment_tests)
    # Record listener-free pull comparison, activation order, rollback, and lag evidence.
    run_case("DEPLOY-PULL-001", ["OPS-007", "TOOL-015", "TOOL-021", "TEST-180", "TEST-258"], _run_release_poller_tests)
    # Record safe PR cancellation, exhaustive shards, audio ownership, artifacts, and gate behavior.
    run_case("CI-QUALIFICATION-001", ["TOOL-002", "TEST-036", "TEST-242"], _run_ci_qualification_tests)
