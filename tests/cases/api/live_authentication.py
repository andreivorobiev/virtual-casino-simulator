# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own the final live authentication registration for the #727 split."""


# Register the live authentication callback at its historical listener boundary.
def run_cases(run_case, auth_backend):
    """Register the exact authentication backend callback."""
    # Record login, concurrent sessions, account projection, terms, logout, and inactive-user coverage.
    run_case("API-AUTH-001", ["AUTH-001", "SESSION-001", "SESSION-007", "SESSION-012", "USER-001", "TERMS-001"], auth_backend)
