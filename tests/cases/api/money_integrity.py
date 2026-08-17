# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Register listener-free storage and settlement integrity cases for the API lane."""


# Register money-integrity suites through fresh-process execution owned by the runner.
def run_cases(run_case, run_unit_module):
    """Register storage and legacy-settlement cases in historical execution order."""
    # Record the semantics-preserving ledger tail-cache and bootstrap-race proof. (issues #412, #431)
    run_case("STORAGE-LEDGER-CACHE-001", ["LEDGER-034", "STORAGE-009", "TEST-135", "TEST-169"], lambda: run_unit_module("tests.storage_ledger_cache_tests", "ledger cache, action journal, and bootstrap race suite failed"))
    # Record the Blackjack and Baccarat exactly-once settlement, clamp, and entropy proof. (issues #403, #404, #420)
    run_case("API-LEGACY-SETTLE-001", ["LEDGER-030", "SEC-012"], lambda: run_unit_module("tests.legacy_settlement_tests", "blackjack and baccarat settlement suite failed"))
    # Record the Roulette and Keno exactly-once settlement, layout, and entropy proof. (issues #403, #222, #420)
    run_case("API-LEGACY-SETTLE-002", ["LEDGER-030", "ROU-071", "SEC-012"], lambda: run_unit_module("tests.roulette_keno_settlement_tests", "roulette and keno settlement suite failed"))
    # Record the competitive bounded Bingo economics proof. (issue #405)
    run_case("API-BINGO-ECONOMICS-001", ["BINGO-025", "BINGO-026"], lambda: run_unit_module("tests.bingo_economics_tests", "bingo economics suite failed"))
