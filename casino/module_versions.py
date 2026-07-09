# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Set APP_VERSION to the value needed for the next operation.
APP_VERSION = "9.1.1"
# Set RELEASE_NAME to the value needed for the next operation.
RELEASE_NAME = "Repository Bootstrap + Codex Migration Payload"
# Set SOURCE_BASELINE_VERSION to the value needed for the next operation.
SOURCE_BASELINE_VERSION = "9.1.0"
# Set MODULE_REVISIONS to the value needed for the next operation.
MODULE_REVISIONS = {
    # Execute this statement as part of the module's documented control flow.
    "application": "9.1.1",
    # Execute this statement as part of the module's documented control flow.
    "core": "9.1.0",
    # Execute this statement as part of the module's documented control flow.
    "ledger": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "players": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "bot_controller": "1.0.0",
    # Execute this statement as part of the module's documented control flow.
    "autoplay_controller": "1.1.0",
    # Execute this statement as part of the module's documented control flow.
    "audio_voice": "9.1.1",
    # Execute this statement as part of the module's documented control flow.
    "logging": "9.1.0",
    # Execute this statement as part of the module's documented control flow.
    "roulette": "9.1.0",
    # Execute this statement as part of the module's documented control flow.
    "slots": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "blackjack": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "baccarat": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "keno": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "bingo": "9.0.1",
    # Execute this statement as part of the module's documented control flow.
    "admin": "1.1.0",
    # Execute this statement as part of the module's documented control flow.
    "tests": "1.2.0",
    # Execute this statement as part of the module's documented control flow.
    "docs": "1.1.4",
    # Execute this statement as part of the module's documented control flow.
    "contracts": "1.0.0",
    # Execute this statement as part of the module's documented control flow.
    "tooling": "1.1.0",
    # Execute this statement as part of the module's documented control flow.
    "commenting_policy": "1.0.0",
}

# Define the list_module_revisions function used by this module.
def list_module_revisions():
    # Return the computed value to the caller.
    return [{"module": k, "revision": v} for k, v in MODULE_REVISIONS.items()]
