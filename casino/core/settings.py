# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Durable platform settings accessed through the configured storage provider.
from __future__ import annotations
# Import required dependency so this module can use schema version metadata.
from casino.config import SCHEMA_VERSION
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider

# Set AUDIO_DOCUMENT_KEY to the provider document key for audio settings.
AUDIO_DOCUMENT_KEY = "settings/audio"

# Set DEFAULT_AUDIO to the value needed for the next operation.
DEFAULT_AUDIO = {
    "schema_version": SCHEMA_VERSION,
    "master_enabled": False,
    "master_volume": 0.8,
    "sfx_enabled": False,
    "sfx_volume": 0.7,
    "voice_enabled": False,
    "voice_volume": 0.85,
    "voice_rate": 0.95,
    "voice_pitch": 1.08,
    "preferred_voice_name": "",
    "auto_nice_lady": True,
    "announce_roulette_results": False,
    "announce_blackjack_results": False,
    "announce_baccarat_results": False,
    "announce_bingo_calls": False,
    "announce_keno_results": False,
}


# Define the audio_settings function used by this module.
def audio_settings() -> dict:
    # Set state to the provider-backed audio settings document.
    state = get_storage_provider().read_document(AUDIO_DOCUMENT_KEY, DEFAULT_AUDIO.copy)
    if not isinstance(state, dict):
        # Set state to the value needed for the next operation.
        state = DEFAULT_AUDIO.copy()
    # Set merged to the value needed for the next operation.
    merged = DEFAULT_AUDIO.copy(); merged.update(state); merged["schema_version"] = SCHEMA_VERSION
    return merged


# Define the save_audio_settings function used by this module.
def save_audio_settings(updates: dict) -> dict:
    # Set state to the value needed for the next operation.
    state = audio_settings()
    for key, val in (updates or {}).items():
        if key in DEFAULT_AUDIO:
            if key.endswith("_enabled") or key.startswith("announce_") or key == "auto_nice_lady":
                # Set state[key] to the value needed for the next operation.
                state[key] = bool(val)
            # Branch when the prior condition failed and this condition is true.
            elif key.endswith("_volume") or key in ("voice_rate", "voice_pitch"):
                # Set state[key] to the value needed for the next operation.
                state[key] = max(0, min(2, float(val)))
            # Branch when the prior condition failed and this condition is true.
            elif key == "preferred_voice_name":
                # Set state[key] to the value needed for the next operation.
                state[key] = str(val or "")
    # Persist the audio settings document through the active storage provider.
    get_storage_provider().write_document(AUDIO_DOCUMENT_KEY, state)
    return state
