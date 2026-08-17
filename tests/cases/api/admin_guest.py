# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register the live Guest/Admin case for the API lane."""


# Register the Guest/Admin area through live-server state owned by the compatibility runner.
def run_cases(run_case, base, validate_guest_admin_api):
    """Register the Guest/Admin case at its historical authenticated point."""
    # Bind the shared server URL only when the central runner executes this case.
    action = lambda: validate_guest_admin_api(base)
    # Record protected-route, Admin denial/reporting, cleanup, and no-resumption proof.
    run_case("API-ADMIN-GUEST-001", ["GUEST-001", "GUEST-003", "GUEST-004", "GUEST-006", "TEST-080", "TEST-088"], action)
