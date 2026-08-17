# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register frontend-presentation cases while the runner owns execution."""

# Import path values for the unchanged runner-owned Node callback inputs.
from pathlib import Path


# Register the frontend-presentation area in its historical execution order.
def run_cases(run_case, run_roulette_motion_tests, run_game_frontend_node_test):
    """Register Roulette motion, game presentation, and wallet timing cases."""
    # Record the listener-free anti-strobe, whole-turn, and reduced-motion proof.
    run_case("UI-ROU-MOTION-001", ["ROU-063", "ROU-064", "ROU-065", "ROU-066", "ROU-067", "ROU-068", "ROU-069", "ROU-070", "TEST-102"], run_roulette_motion_tests)
    # Record deterministic landing, API/timer teardown, exactly-once completion, and clean-remount Roulette proof.
    run_case("UI-ROU-PRESENTATION-001", ["ROU-063", "ROU-064", "ROU-065", "ROU-066", "ROU-067", "ROU-068", "ROU-072"], lambda: run_game_frontend_node_test(Path("tests/games/roulette/test_frontend.mjs"), "Roulette presentation suite failed"))
    # Record deterministic strips, stagger/anticipation, API/landing teardown, and clean-remount Slots proof.
    run_case("UI-SLOT-PRESENTATION-001", ["SLOT-030", "SLOT-031", "SLOT-032", "SLOT-033", "SLOT-034", "SLOT-035", "SLOT-037"], lambda: run_game_frontend_node_test(Path("tests/games/slots/test_frontend.mjs"), "Slots presentation suite failed"))
    # Record the shared committed-debit renderer and catalog-wide presentation-order proof.
    run_case("UI-WALLET-TIMING-001", ["LEDGER-031", "TEST-151"], lambda: run_game_frontend_node_test(Path("tests/wallet_timing.mjs"), "wallet timing suite failed"))
