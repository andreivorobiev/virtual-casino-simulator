# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free Admin policy and diagnostics cases for the API lane."""


# Register Admin policy suites through fresh-process execution owned by the runner.
def run_cases(run_case, run_unit_module):
    """Register Admin policy and Guest-admission cases in historical execution order."""
    # Record recursive nested/legacy Admin state discovery and empty-state safety. (ADMIN-029, TEST-145)
    run_case("API-ADMIN-GAME-STATES-001", ["ADMIN-029", "TEST-145"], lambda: run_unit_module("tests.admin_game_states_tests.AdminGameStatesTests", "Admin diagnostics suite failed"))
    # Record bounded payout-rate arithmetic, exclusion, malformed-row, and detail evidence. (ADMIN-030, TEST-146)
    run_case("API-ADMIN-ECONOMICS-001", ["ADMIN-030", "TEST-146"], lambda: run_unit_module("tests.admin_economics_tests", "Admin economics suite failed"))
    # Record owner-only clamped provider-backed session-policy routes and persistence. (SESSION-009, ADMIN-031, TEST-150)
    run_case("API-ADMIN-SESSION-POLICY-001", ["SESSION-009", "SESSION-010", "SESSION-011", "SESSION-012", "ADMIN-031", "ADMIN-034", "TEST-150", "TEST-158"], lambda: run_unit_module("tests.admin_game_states_tests.AdminSessionSettingsTests", "Admin session policy suite failed"))
    # Run the owner-only live rate-policy provider and route contract. (SEC-015, ADMIN-032, TEST-156)
    run_case("API-ADMIN-RATE-LIMITS-001", ["SEC-015", "ADMIN-032", "TEST-156"], lambda: run_unit_module("tests.admin_game_states_tests.AdminRateLimitSettingsTests", "Admin rate-limit policy suite failed"))
    # Prove 10,000-token guest grants plus owner pause/resume enforcement without restart. (GUEST-001)
    run_case("API-GUEST-ADMISSION-001", ["GUEST-001", "GUEST-004", "GUEST-005", "TEST-080"], lambda: run_unit_module("tests.admin_game_states_tests.AdminGuestTrialSettingsTests", "Guest admission policy suite failed"))
