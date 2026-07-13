# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import re
# Import sys so direct validator execution can load the repository catalog.
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Add the repository root before importing the runtime catalog facade.
sys.path.insert(0, str(ROOT))
# Import the canonical game descriptors after resolving this checkout.
from casino.config import GAMES as GAME_CATALOG
# Derive module-boundary ids from the same descriptors used for runtime registration.
GAMES = [game["id"] for game in GAME_CATALOG]
# Set PY_IMPORT_RE to the value needed for the next operation.
PY_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)")
# Set JS_IMPORT_RE to the value needed for the next operation.
JS_IMPORT_RE = re.compile(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]")

# Define the check_python_game_imports function used by this module.
def check_python_game_imports(errors):
    # Iterate through the collection to process each item.
    for game in GAMES:
        # Iterate through the collection to process each item.
        for path in (ROOT / "casino" / "games" / game).rglob("*.py"):
            # Set text to the value needed for the next operation.
            text = path.read_text(encoding="utf-8")
            # Iterate through the collection to process each item.
            for lineno, line in enumerate(text.splitlines(), 1):
                # Set m to the value needed for the next operation.
                m = PY_IMPORT_RE.match(line)
                # Branch when the following condition is true.
                if not m:
                    # Execute this statement as part of the module's documented control flow.
                    continue
                # Set imported to the value needed for the next operation.
                imported = m.group(1)
                # Iterate through the collection to process each item.
                for other in GAMES:
                    # Branch when the following condition is true.
                    if other != game and f"casino.games.{other}" in imported:
                        # Execute this statement as part of the module's documented control flow.
                        errors.append(f"{path}:{lineno} imports other game module {other}")
                # Branch when the following condition is true.
                if "casino.bots.strategies" in imported:
                    # Execute this statement as part of the module's documented control flow.
                    errors.append(f"{path}:{lineno} imports bot strategies directly")

# Define the check_js_game_imports function used by this module.
def check_js_game_imports(errors):
    # Set game_dir to the value needed for the next operation.
    game_dir = ROOT / "web" / "games"
    # Iterate through the collection to process each item.
    for game in GAMES:
        # Set path to the value needed for the next operation.
        path = game_dir / f"{game}.js"
        # Branch when the following condition is true.
        if not path.exists():
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set text to the value needed for the next operation.
        text = path.read_text(encoding="utf-8")
        # Iterate through the collection to process each item.
        for lineno, line in enumerate(text.splitlines(), 1):
            # Set m to the value needed for the next operation.
            m = JS_IMPORT_RE.search(line)
            # Branch when the following condition is true.
            if not m:
                # Execute this statement as part of the module's documented control flow.
                continue
            # Set target to the value needed for the next operation.
            target = m.group(1)
            # Iterate through the collection to process each item.
            for other in GAMES:
                # Branch when the following condition is true.
                if other != game and f"{other}.js" in target:
                    # Execute this statement as part of the module's documented control flow.
                    errors.append(f"{path}:{lineno} imports other game frontend {other}")

# Define the main function used by this module.
def main():
    # Set errors to the value needed for the next operation.
    errors = []
    # Execute this statement as part of the module's documented control flow.
    check_python_game_imports(errors)
    # Execute this statement as part of the module's documented control flow.
    check_js_game_imports(errors)
    # Branch when the following condition is true.
    if errors:
        # Write diagnostic output so the current operation can be inspected.
        print("Module boundary validation failed:")
        # Iterate through the collection to process each item.
        for err in errors:
            # Write diagnostic output so the current operation can be inspected.
            print(f" - {err}")
        # Return the computed value to the caller.
        return 1
    # Write diagnostic output so the current operation can be inspected.
    print("Module boundary validation passed.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
