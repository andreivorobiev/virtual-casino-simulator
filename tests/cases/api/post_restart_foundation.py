# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own post-restart foundation registrations for the #727 split."""


# Register the complete post-restart foundation block at its historical boundary.
def run_cases(run_case, wallet_restart_persistence, core, catalog_foundation, economics_registry, validate_i18n_resources, bots_audio_autoplay):
    """Register exact persisted-state and platform-foundation callbacks."""
    # Record live wallet and private game-state persistence across the runner-owned restart.
    run_case("API-WALLET-RESTART-001", ["SESSION-003", "USER-001", "TOKEN-003", "TOKEN-004", "TEST-039", "MHVP-002", "CW-002", "BIG-SIX-002", "RD-002", "DT-002", "HILO-002", "SCRATCH-002", "SIC-BO-002", "CHUCK-002", "CRAPS-002", "CAA-002", "OU7-002", "PLINKO-002", "FAN-TAN-002", "AB-002", "AD-002", "CS-002", "LIR-002", "CH-002", "PGP-002", "JP-002", "THPT-002"], wallet_restart_persistence)
    # Record core catalog, bot visibility, and canonical version metadata coverage.
    run_case("API-CORE-001", ["CORE-001", "CORE-016", "TEST-003"], core)
    # Record catalog discovery, route metadata, and authenticated-player resolution coverage.
    run_case("API-CATALOG-001", ["CORE-021", "SESSION-005", "TEST-042"], catalog_foundation)
    # Validate exact catalog economics ownership and production-source bindings.
    run_case("ECONOMICS-REGISTRY-001", ["TEST-175"], economics_registry)
    # Record complete translation-resource validation under its historical API case.
    run_case("API-I18N-001", ["I18N-001", "I18N-003"], validate_i18n_resources)
    # Record collision-free registry, discovery, and translation-readiness evidence.
    run_case("API-I18N-FOUNDATION-001", ["I18N-006", "I18N-007", "TEST-101"], validate_i18n_resources)
    # Record bot, audio, autoplay, and practice-opponent control-plane integration.
    run_case("API-CONTROL-001", ["BOT-001", "BOT-003", "BOT-009", "BOT-010", "BOT-011", "ADMIN-023", "AUDIO-001", "AUDIO-002", "AUDIO-010", "AUTO-001", "AUTO-003"], bots_audio_autoplay)
