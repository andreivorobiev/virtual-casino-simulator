#!/usr/bin/env python3
# Validate module-owned game catalog metadata and all discoverable integration hooks.
import importlib  # Resolve backend registration and long-suite driver references.
import json  # Parse installed shell locale resources for catalog-copy governance.
import pathlib  # Resolve catalog-owned frontend and contract paths.
import re  # Confirm frontend exports without executing browser modules.
import sys  # Load the current checkout when the validator runs directly.

# Resolve repository paths independently of the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Prefer the current checkout over unrelated installed packages.
sys.path.insert(0, str(ROOT))

# Import the canonical catalog only after the repository root is available.
from casino.config import GAME_CATALOG_TARGET, GAMES
# Import the #104 canonical version interface for module-revision checks.
from casino.module_versions import MODULE_REVISIONS

# List shell-owned catalog control keys that every installed locale must provide.
CATALOG_COPY_KEYS = {"catalog.allGames", "catalog.categoriesAria", "catalog.controlsAria", "catalog.empty", "catalog.galleryAria", "catalog.capacity", "catalog.searchLabel", "catalog.searchPlaceholder"}
# Load installed shell dictionaries so catalog identifiers can never leak as player-facing labels.
SHELL_RESOURCES = {locale: json.loads((ROOT / "web" / "i18n" / locale / "shell.json").read_text(encoding="utf-8")) for locale in ("en-US", "ru-RU")}


# Resolve a module-and-callable reference and report focused errors.
def resolve_callable(reference, description, errors):
    try:  # Convert import failures into validator diagnostics.
        module_name, callable_name = reference.split(":", 1)  # Separate the import path and callable.
        module = importlib.import_module(module_name)  # Import the catalog-owned Python module.
        value = getattr(module, callable_name)  # Resolve its documented public callable.
        if not callable(value):  # Reject non-callable descriptor targets.
            errors.append(f"{description} is not callable: {reference}")  # Record the exact broken reference.
    except Exception as exc:  # Preserve every discovery failure for one complete validation run.
        errors.append(f"{description} could not load {reference}: {type(exc).__name__}: {exc}")  # Report actionable context.


# Validate every catalog entry and its independent integration surfaces.
def main():
    errors = []  # Collect all catalog drift before returning a status.
    ids = [game["id"] for game in GAMES]  # Preserve ordered catalog ids for duplicate checks.
    discovered_categories = {category for game in GAMES for category in game.get("categories", [])}  # Derive every category from module-owned metadata.
    if not ids:  # Reject an empty runtime that would hide all games.
        errors.append("game catalog is empty")  # Record the missing catalog foundation.
    if len(ids) != len(set(ids)):  # Reject ambiguous runtime and browser routes.
        errors.append("game catalog ids are not unique")  # Record duplicate identity drift.
    if GAME_CATALOG_TARGET < 20:  # Preserve the approved expansion capacity gate.
        errors.append("game catalog target must support at least 20 games")  # Report target regression.
    for game in GAMES:  # Validate every module-owned game without a central allowlist.
        game_id = game["id"]  # Cache the id for concise diagnostics.
        if game_id not in MODULE_REVISIONS:  # Consume #104 revisions instead of inventing fallback versions.
            errors.append(f"catalog game {game_id} has no canonical module revision")  # Report version drift.
        if game.get("route") != f"/games/{game_id}":  # Require stable reloadable route ownership.
            errors.append(f"catalog game {game_id} must use /games/{game_id}")  # Report deep-link drift.
        categories = game.get("categories", [])  # Read scalable lobby facets.
        if not game.get("category") or game.get("category") not in categories:  # Require a primary searchable category.
            errors.append(f"catalog game {game_id} has invalid categories")  # Report navigation metadata drift.
        resolve_callable(game.get("backend", {}).get("register", ""), f"{game_id} backend register", errors)  # Validate API discovery.
        resolve_callable(game.get("tests", {}).get("long_driver", ""), f"{game_id} long driver", errors)  # Validate test discovery.
        frontend = game.get("frontend", {})  # Read browser registration metadata.
        module_path = frontend.get("module", "")  # Read the browser-relative module path.
        relative_module = module_path.removeprefix("./")  # Normalize the web-root-relative path.
        frontend_path = ROOT / "web" / relative_module  # Resolve the frontend source file.
        if not frontend_path.exists():  # Reject missing lazy route modules.
            errors.append(f"catalog game {game_id} frontend is missing: {module_path}")  # Report the exact path.
        else:  # Inspect the existing source only after confirming it exists.
            export_name = frontend.get("export", "")  # Read the documented class export.
            source = frontend_path.read_text(encoding="utf-8")  # Load the browser module for static export validation.
            if not re.search(rf"export\s+(?:class|const|function)\s+{re.escape(export_name)}\b", source):  # Require the exact export.
                errors.append(f"catalog game {game_id} frontend export is missing: {export_name}")  # Report export drift.
        if not frontend.get("ready_testid"):  # Require a generic browser-discovery readiness hook.
            errors.append(f"catalog game {game_id} has no browser ready_testid")  # Report missing driver metadata.
        if not game.get("contracts"):  # Require contract discovery for every playable game.
            errors.append(f"catalog game {game_id} has no contract paths")  # Report missing API governance.
    for locale, resource in SHELL_RESOURCES.items():  # Validate catalog controls in every required visual locale.
        for key in sorted(CATALOG_COPY_KEYS):  # Check fixed control copy separately from discovered category labels.
            if not str(resource.get(key, "")).strip():  # Reject missing or blank localized control values.
                errors.append(f"{locale} shell resource is missing catalog control key {key}")  # Report the exact locale and key.
        for category in sorted(discovered_categories):  # Require display labels for every module-discovered category identifier.
            key = f"catalog.category.{category}"  # Resolve the stable shell-resource key for this internal identifier.
            label = str(resource.get(key, "")).strip()  # Read and normalize the localized display label.
            if not label:  # Reject categories that would fall through to a raw resource key.
                errors.append(f"{locale} shell resource is missing category label {key}")  # Report missing future-game taxonomy.
            elif label.casefold() == category.casefold():  # Reject direct exposure of the internal identifier as display copy.
                errors.append(f"{locale} category label {key} exposes its internal id")  # Report non-localized identifier leakage.
    if errors:  # Fail after returning all actionable catalog errors.
        print("Game catalog validation failed:")  # Print a stable failure heading.
        for error in errors:  # Print each independent drift class.
            print(f" - {error}")  # Prefix diagnostics consistently.
        return 1  # Return a failing process status.
    print(f"Game catalog validation passed for {len(GAMES)} current games and target {GAME_CATALOG_TARGET}.")  # Report discovery coverage.
    return 0  # Return success after every integration hook validates.


# Run the validator only when invoked as a script.
if __name__ == "__main__":
    raise SystemExit(main())  # Exit with the catalog validation result.
