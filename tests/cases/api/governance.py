# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free repository governance cases for the API lane."""

# Import subprocess isolation for discovered suites whose imports can redirect shared state.
import subprocess
# Import the active interpreter identity for fresh-process governance suites.
import sys


# Execute every browser-free Python game suite without a central per-game allowlist. (TEST-161)
def _run_complete_game_suite_discovery(root):
    """Run both governed game-suite roots through fresh unittest processes."""
    # Define both governed discovery roots used by complete CI discovery.
    discovery_roots = ("tests/games", "casino/games")
    # Execute each root in a fresh process so test-owned imports and storage settings remain isolated.
    for discovery_root in discovery_roots:
        # Discover every Python suite path while leaving Playwright-owned modules to the Browser-capable CI step.
        suite_files = sorted(path for path in (root / discovery_root).rglob("test_*.py") if path.name != "test_browser.py")
        # Convert tracked paths to dotted unittest module names without a per-game allowlist.
        suite_modules = [".".join(path.relative_to(root).with_suffix("").parts) for path in suite_files]
        # Run the complete browser-free module list through unittest's normal loader.
        result = subprocess.run([sys.executable, "-m", "unittest", *suite_modules], cwd=str(root), capture_output=True, text=True, timeout=600)
        # Fail the mapped case with the child's bounded diagnostic tail when any discovered suite fails.
        if result.returncode != 0:
            # Prefer stderr while retaining stdout-only unittest diagnostics.
            diagnostic = result.stderr or result.stdout
            # Raise one stable area-owned error with only the bounded diagnostic tail.
            raise AssertionError(f"{discovery_root} discovery failed: {diagnostic[-1500:]}")


# Register the governance area through callbacks owned by the compatibility runner.
def run_cases(run_case, run_unit_module, root):
    """Register governance cases in their historical execution order."""
    # Prove the governed source-header migration, vendor exclusion, write safety, and filler ratchet. (issue #441)
    run_case("FILE-HEADER-POLICY-001", ["COMMENT-001", "TOOL-009"], lambda: run_unit_module("tests.file_header_policy_tests", "file header policy suite failed"))
    # Record the exact-source payload and shipped-asset budget checkpoint. (issue #323, TEST-159)
    run_case("PERF-PAYLOAD-BUDGET-001", ["TEST-159"], lambda: run_unit_module("tests.unit.payload_frontend_budget_tests", "payload and frontend budget suite failed"))
    # Record compact shell/Roulette projections and frozen-response compatibility. (issue #323, TEST-166)
    run_case("PERF-PAYLOAD-PROJECTION-001", ["TEST-166"], lambda: run_unit_module("tests.unit.performance_projection_tests", "payload projection suite failed"))
    # Enforce the issue-323 exact-source JSON/MySQL latency decision boundary. (issue #323, TEST-170)
    run_case("PERF-TARGET-GATE-001", ["TEST-170"], lambda: run_unit_module("tests.unit.performance_target_gate_tests", "performance target gate suite failed"))
    # Record the fail-closed process-safety inventory used before any worker-count increase. (issue #323, TEST-160)
    run_case("PERF-MULTIPROCESS-SAFETY-001", ["TEST-160"], lambda: run_unit_module("tests.unit.multiprocess_safety_audit_tests", "multiprocess safety audit suite failed"))
    # Record the descriptor-owned game-suite discovery boundary without migrating game descriptors yet. (issue #434, TEST-161)
    run_case("GOV-GAME-SUITE-DISCOVERY-001", ["TEST-161"], lambda: run_unit_module("tests.game_suite_discovery_tests", "game suite discovery suite failed"))
    # Map current-and-future browser-free suite execution without one registration per game. (issue #434, TEST-161)
    run_case("GOV-GAME-SUITES-001", ["TEST-161"], lambda: _run_complete_game_suite_discovery(root))
    # Record deterministic requirement-source partitioning and aggregate drift rejection. (issue #434, TEST-165)
    run_case("GOV-REQUIREMENT-SHARDS-001", ["TEST-165"], lambda: run_unit_module("tests.requirements_sharding_tests", "requirement sharding suite failed"))
    # Reject stale requirement inventories, placeholder gates, and reviewed production-unused exports. (issue #711)
    run_case("GOV-DEAD-ARTIFACTS-001", ["TOOL-016", "TEST-181"], lambda: run_unit_module("tests.dead_artifact_tests", "dead artifact cleanup suite failed"))
    # Preserve actionable locale, domain, and missing-key evidence at both cumulative Roulette audits. (issue #702)
    run_case("UI-ROULETTE-I18N-DIAGNOSTICS-001", ["I18N-013", "TEST-182"], lambda: run_unit_module("tests.roulette_i18n_diagnostics_tests", "Roulette i18n diagnostics suite failed"))
    # Prove shared shell/Admin copy and every game tx adapter use locale resources as their single source. (I18N-014, TEST-187)
    run_case("UI-I18N-SINGLE-SOURCE-001", ["I18N-014", "TEST-187"], lambda: run_unit_module("tests.i18n_single_source_tests", "Single-source i18n suite failed"))
    # Prove Roulette and Three Card Poker await semantic Browser state instead of fixed timing. (issue #750)
    run_case("UI-BROWSER-WAIT-001", ["TEST-053", "TCP-005"], lambda: run_unit_module("tests.browser_wait_governance_tests", "Browser wait governance suite failed"))
    # Prove docs-only long-suite filtering and exact-head sibling-gate release evidence without weakening contexts. (issue #710)
    run_case("CI-COMPUTE-001", ["TOOL-017", "TEST-183"], lambda: run_unit_module("tests.ci_compute_tests", "CI compute optimization suite failed"))
    # Enforce generic descriptor equality and exact-base monotonic revisions without shared pin literals. (issue #707)
    run_case("GOV-MODULE-VERSIONS-001", ["TOOL-018", "TEST-184"], lambda: run_unit_module("tests.module_version_governance_tests", "module version governance suite failed"))
    # Bind the five newest games to dedicated Browser cases, per-game suites, duration packing, and affected-game selection. (issue #712)
    run_case("GOV-NEWEST-GAME-BROWSER-COVERAGE-001", ["TEST-185"], lambda: run_unit_module("tests.newest_game_browser_coverage_tests", "newest-game Browser coverage suite failed"))
