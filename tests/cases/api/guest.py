# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free Guest Trial cases for the API lane."""


# Register the Guest Trial area through validators owned by the compatibility runner.
def run_cases(run_case, validate_guest_lifecycle, validate_guest_analytics, validate_guest_contracts):
    """Register Guest Trial cases in historical execution order."""
    # Record listener-free disposable-principal lifecycle and browser-binding proof.
    run_case("API-GUEST-LIFECYCLE-001", ["GUEST-001", "GUEST-002", "GUEST-006", "TEST-080"], validate_guest_lifecycle)
    # Record listener-free telemetry privacy, milestones, and retention proof.
    run_case("API-GUEST-ANALYTICS-001", ["GUEST-003", "TEST-088"], validate_guest_analytics)
    # Record exact additive v2 and restricted-preview compatibility contract proof.
    run_case("API-GUEST-CONTRACT-001", ["GUEST-005", "TEST-088"], validate_guest_contracts)
