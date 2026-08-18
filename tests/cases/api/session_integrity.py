# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own session and wallet-integrity API registrations for the #727 split."""


# Register the complete shared-integrity block at its historical live-server boundary.
def run_cases(run_case, wallet_auth_integrity, integrity_state, assert_condition):
    """Register exact shared-state predicates without owning backend lifecycle."""
    # Execute the real-backend integrity regression as one mapped API case.
    run_case("API-PRIVATE-SESSION-001", ["SESSION-003", "USER-001", "USER-003", "USER-005", "TOKEN-004", "TEST-039"], wallet_auth_integrity)
    # Record Multi-Hand Video Poker session, mode, ledger, and retry coverage.
    run_case("API-MHVP-001", ["MHVP-001", "MHVP-002", "MHVP-003"], lambda: assert_condition(integrity_state["mhvp_verified"], "Multi-Hand Video Poker integration evidence missing"))
    # Record Casino War session, ledger, settlement, and retry coverage.
    run_case("API-CW-001", ["CW-001", "CW-002", "CW-003"], lambda: assert_condition(integrity_state["casino_war_verified"], "Casino War integration evidence missing"))
    # Record Big Six session, ledger, conflict, and retry coverage.
    run_case("API-BIG-SIX-001", ["BIG-SIX-001", "BIG-SIX-002", "BIG-SIX-003", "BIG-SIX-008"], lambda: assert_condition(integrity_state["big_six_verified"], "Big Six integration evidence missing"))
    # Record Red Dog session, ledger, conflict, and retry coverage.
    run_case("API-RD-001", ["RD-001", "RD-002", "RD-003"], lambda: assert_condition(integrity_state["red_dog_verified"], "Red Dog integration evidence missing"))
    # Record Dragon Tiger session, ledger, conflict, and retry coverage.
    run_case("API-DT-001", ["DT-001", "DT-002", "DT-003", "DT-007"], lambda: assert_condition(integrity_state["dragon_tiger_verified"], "Dragon Tiger integration evidence missing"))
    # Record Hi-Lo session, ledger, conflict, and retry coverage.
    run_case("API-HILO-001", ["HILO-001", "HILO-002", "HILO-003"], lambda: assert_condition(integrity_state["hi_lo_verified"], "Hi-Lo integration evidence missing"))

    # Build one reusable evidence predicate for distinct authenticated-player server ids.
    def game_evidence(key):
        # Compare retained coverage with the authenticated players and require distinct ids.
        return lambda: assert_condition(set(integrity_state[key]) == {user["player_id"] for user in integrity_state["users"]} and len(set(integrity_state[key].values())) == 2, f"{key} integration evidence missing")

    # Record Three Card Poker coverage against retained per-player round ids.
    run_case("API-TCP-001", ["TCP-001", "TCP-002", "TCP-003"], game_evidence("three_card_poker_rounds"))
    # Record Jacks or Better coverage against retained per-player round ids.
    run_case("API-JOBVP-001", ["JOBVP-001", "JOBVP-002", "JOBVP-003"], game_evidence("jacks_or_better_rounds"))
    # Record Deuces Wild coverage against retained per-player round ids.
    run_case("API-DWVP-001", ["DWVP-001", "DWVP-002", "DWVP-003"], game_evidence("deuces_wild_rounds"))
    # Record Scratch Cards coverage against retained per-player card ids.
    run_case("API-SCRATCH-001", ["SCRATCH-001", "SCRATCH-002", "SCRATCH-003"], game_evidence("scratch_cards"))
    # Record Sic Bo coverage against retained per-player round ids.
    run_case("API-SIC-BO-001", ["SIC-BO-001", "SIC-BO-002", "SIC-BO-003", "SIC-BO-007"], game_evidence("sic_bo_rounds"))
    # Record Chuck-a-Luck coverage against retained per-player round ids.
    run_case("API-CHUCK-001", ["CHUCK-001", "CHUCK-002", "CHUCK-003", "CHUCK-007"], game_evidence("chuck_a_luck_rounds"))
    # Record Craps coverage against retained per-player round ids.
    run_case("API-CRAPS-001", ["CRAPS-001", "CRAPS-002", "CRAPS-003"], game_evidence("craps_rounds"))
    # Record Crown and Anchor coverage against retained per-player round ids.
    run_case("API-CAA-001", ["CAA-001", "CAA-002", "CAA-003", "CAA-007"], game_evidence("crown_and_anchor_rounds"))
    # Record Over/Under 7 coverage against retained per-player round ids.
    run_case("API-OU7-001", ["OU7-001", "OU7-002", "OU7-003", "OU7-008"], game_evidence("over_under_7_rounds"))
    # Record Plinko coverage against retained per-player drop ids.
    run_case("API-PLINKO-001", ["PLINKO-001", "PLINKO-002", "PLINKO-003"], game_evidence("plinko_drops"))
    # Record Fan-Tan coverage against retained per-player round ids.
    run_case("API-FAN-TAN-001", ["FAN-TAN-001", "FAN-TAN-002", "FAN-TAN-003", "FAN-TAN-007"], game_evidence("fan_tan_rounds"))
    # Record Andar Bahar coverage against retained per-player round ids.
    run_case("API-AB-001", ["AB-001", "AB-002", "AB-003"], game_evidence("andar_bahar_rounds"))
    # Record Acey-Deucey coverage against retained per-player round ids.
    run_case("API-AD-001", ["AD-001", "AD-002", "AD-003"], game_evidence("acey_deucey_rounds"))
    # Record Caribbean Stud coverage against retained per-player round ids.
    run_case("API-CS-001", ["CS-001", "CS-002", "CS-003"], game_evidence("caribbean_stud_rounds"))
    # Record Let It Ride coverage against retained per-player round ids.
    run_case("API-LIR-001", ["LIR-001", "LIR-002", "LIR-003"], game_evidence("let_it_ride_rounds"))
    # Record Casino Hold'em coverage against retained per-player round ids.
    run_case("API-CH-001", ["CH-001", "CH-002", "CH-003"], game_evidence("casino_holdem_rounds"))
    # Record Pai Gow Poker coverage against retained per-player round ids.
    run_case("API-PGP-001", ["PGP-001", "PGP-002", "PGP-003"], game_evidence("pai_gow_poker_rounds"))
    # Record Joker Poker coverage against retained per-player round ids.
    run_case("API-JP-001", ["JP-001", "JP-002", "JP-003"], game_evidence("joker_poker_rounds"))
    # Record Texas Hold'em coverage against retained per-player hand ids.
    run_case("API-THPT-001", ["THPT-001", "THPT-002", "THPT-003", "THPT-005", "BOT-009", "BOT-010", "BOT-011", "LEDGER-026", "SEC-001", "SEC-002", "SEC-003", "SEC-004", "SEC-005", "SEC-006", "SEC-008", "SEC-009"], game_evidence("texas_holdem_practice_hands"))
    # Record exact token credit coverage under the permanent token test id.
    run_case("API-TOKEN-001", ["TOKEN-003", "TOKEN-004"], lambda: assert_condition(integrity_state["token_credit_count"] == 1 and integrity_state["contract_player"]["token_balance"] == 250, "token credit contract mismatch"))
    # Record central Admin authorization coverage under the permanent Admin test id.
    run_case("API-ADMIN-USERS-001", ["AUTH-005", "AUTH-008", "USER-002", "USER-004", "TEST-060"], lambda: assert_condition(integrity_state["admin_blocked"] > 20, "Admin route gate coverage incomplete"))
    # Record v2 envelope and player-shape coverage under the permanent contract test id.
    run_case("API-CONTRACT-V2-001", ["API-001", "API-002", "TOKEN-002"], lambda: assert_condition({"player_id", "token_balance", "token_label"} <= set(integrity_state["contract_player"]), "v2 player summary shape mismatch"))
    # Record canonical terms gate and persistence coverage under its permanent test id.
    run_case("API-TERMS-001", ["TERMS-001", "TERMS-002", "TERMS-003"], lambda: assert_condition(integrity_state["email"] == "wallet-a@example.local", "terms integrity setup missing"))
