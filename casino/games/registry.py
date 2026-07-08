# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
from casino.config import GAMES
# Import required dependency so this module can use its public functions or constants.
from casino.module_versions import MODULE_REVISIONS

# Define the list_games function used by this module.
def list_games():
    # Set out to the value needed for the next operation.
    out=[]
    # Iterate through the collection to process each item.
    for g in GAMES:
        # Set x to the value needed for the next operation.
        x=dict(g)
        # Set x["revision"] to the value needed for the next operation.
        x["revision"] = MODULE_REVISIONS.get(g["id"], "0.0.0")
        # Execute this statement as part of the module's documented control flow.
        out.append(x)
    # Return the computed value to the caller.
    return out
