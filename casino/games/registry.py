# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import copy support so public API metadata cannot mutate runtime registration entries.
import copy
# Import dynamic module support so per-game descriptors own backend registration.
import importlib
# Import the canonical catalog and expansion target from the shared configuration facade.
from casino.config import GAMES, GAME_CATALOG_TARGET
# Import required dependency so this module can use its public functions or constants.
from casino.module_versions import MODULE_REVISIONS

# Define the list_games function used by this module.
def list_games():
    # Collect additive public catalog metadata without exposing backend or test import paths.
    out = []
    # Iterate through canonical catalog entries in their configured order.
    for game in GAMES:
        # Copy the public metadata deeply so nested frontend and lobby values remain immutable.
        item = copy.deepcopy({key: value for key, value in game.items() if key not in {"backend", "tests", "contracts", "paths"}})
        # Require every configured game to have a canonical module revision instead of masking drift.
        item["revision"] = MODULE_REVISIONS[game["id"]]
        # Preserve the legacy kind field as an alias for the primary catalog category.
        item["kind"] = item.get("category")
        # Add the compatible public record to the API response.
        out.append(item)
    # Return the computed value to the caller.
    return out

# Define catalog_summary so API and tests can report current and target catalog capacity.
def catalog_summary():
    # Return additive counts without changing the existing games array contract.
    return {"current_game_count": len(GAMES), "target_game_count": GAME_CATALOG_TARGET}

# Define register_games so backend API registration is driven by per-game descriptors.
def register_games(router):
    # Register every catalog game without adding imports to the shared application module.
    for game in GAMES:
        # Read the module-and-callable reference owned by this game descriptor.
        reference = game["backend"]["register"]
        # Split the validated reference into an importable module and public callable name.
        module_name, callable_name = reference.split(":", 1)
        # Import only the current game's API module through the standard module loader.
        module = importlib.import_module(module_name)
        # Resolve the documented registration callable from the imported module.
        register = getattr(module, callable_name)
        # Attach this game's API routes to the shared router.
        register(router)
