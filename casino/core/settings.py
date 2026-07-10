# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from __future__ import annotations
# Import required dependency so this module can use schema version metadata.
from casino.config import SCHEMA_VERSION
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider

# Set AUDIO_DOCUMENT_KEY to the provider document key for audio settings.
AUDIO_DOCUMENT_KEY = "settings/audio"

# Set DEFAULT_AUDIO to the value needed for the next operation.
DEFAULT_AUDIO = {
    # Execute this statement as part of the module's documented control flow.
    "schema_version": SCHEMA_VERSION,
    # Execute this statement as part of the module's documented control flow.
    "master_enabled": True,
    # Execute this statement as part of the module's documented control flow.
    "master_volume": 0.8,
    # Execute this statement as part of the module's documented control flow.
    "sfx_enabled": True,
    # Execute this statement as part of the module's documented control flow.
    "sfx_volume": 0.7,
    # Execute this statement as part of the module's documented control flow.
    "voice_enabled": True,
    # Execute this statement as part of the module's documented control flow.
    "voice_volume": 0.85,
    # Execute this statement as part of the module's documented control flow.
    "voice_rate": 0.95,
    # Execute this statement as part of the module's documented control flow.
    "voice_pitch": 1.08,
    # Execute this statement as part of the module's documented control flow.
    "preferred_voice_name": "",
    # Execute this statement as part of the module's documented control flow.
    "auto_nice_lady": True,
    # Execute this statement as part of the module's documented control flow.
    "announce_roulette_results": True,
    # Execute this statement as part of the module's documented control flow.
    "announce_blackjack_results": True,
    # Execute this statement as part of the module's documented control flow.
    "announce_baccarat_results": True,
    # Execute this statement as part of the module's documented control flow.
    "announce_bingo_calls": False,
    # Execute this statement as part of the module's documented control flow.
    "announce_keno_results": False,
}


# Define the audio_settings function used by this module.
def audio_settings() -> dict:
    # Set state to the provider-backed audio settings document.
    state = get_storage_provider().read_document(AUDIO_DOCUMENT_KEY, DEFAULT_AUDIO.copy)
    # Branch when the following condition is true.
    if not isinstance(state, dict):
        # Set state to the value needed for the next operation.
        state = DEFAULT_AUDIO.copy()
    # Set merged to the value needed for the next operation.
    merged = DEFAULT_AUDIO.copy(); merged.update(state); merged["schema_version"] = SCHEMA_VERSION
    # Return the computed value to the caller.
    return merged


# Define the save_audio_settings function used by this module.
def save_audio_settings(updates: dict) -> dict:
    # Set state to the value needed for the next operation.
    state = audio_settings()
    # Iterate through the collection to process each item.
    for key, val in (updates or {}).items():
        # Branch when the following condition is true.
        if key in DEFAULT_AUDIO:
            # Branch when the following condition is true.
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
    # Return the computed value to the caller.
    return state
