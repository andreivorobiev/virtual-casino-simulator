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
# Import pure descriptor validation so catalog and future runtime enforcement share one vocabulary.
from casino.core.game_rules import validate_rule_schema
# Import the #104 canonical version interface for module-revision checks.
from casino.module_versions import MODULE_REVISIONS
# Import the listener-free router so registered settings routes can be compared with descriptors.
from casino.router import Router

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
            return None  # Prevent callers from invoking a non-callable descriptor target.
        return value  # Return the callable so route and default checks use the exact validated object.
    except Exception as exc:  # Preserve every discovery failure for one complete validation run.
        errors.append(f"{description} could not load {reference}: {type(exc).__name__}: {exc}")  # Report actionable context.
        return None  # Let callers continue collecting independent catalog defects.


# Register one game without a listener and return its declared POST settings routes.
def registered_settings_routes(game_id, register, errors):
    # Stop after a backend-reference error because there is no callable to inspect.
    if register is None:
        # Return an empty set so later parity checks stay deterministic.
        return set()
    # Create an isolated route registry that never binds a socket or touches player state.
    router = Router()
    try:
        # Execute only route decorators so the validator observes the module's real API surface.
        register(router)
    except Exception as exc:
        # Report an import-time or registration failure with the owning catalog id.
        errors.append(f"{game_id} backend register failed during route discovery: {type(exc).__name__}: {exc}")
        # Return no routes because the discovered surface is incomplete.
        return set()
    # Select only literal POST routes ending in the settings suffix.
    return {route.pattern for route in router.routes if route.method == "POST" and str(route.pattern).endswith("/settings")}


# Validate descriptor ownership for every settings route registered by one game.
def validate_settings_schema(game, register, errors):
    # Read the stable catalog identity once for focused diagnostics.
    game_id = game["id"]
    # Discover settings routes through the same register callable used by production startup.
    settings_routes = registered_settings_routes(game_id, register, errors)
    # Read the optional descriptor that must exist exactly when a settings route exists.
    schema = game.get("rules")
    # Reject a live route without a declarative rule domain.
    if settings_routes and schema is None:
        # Report every undeclared route so a future game cannot ship an unbounded surface.
        for route in sorted(settings_routes):
            # Name the exact route missing its module-owned schema.
            errors.append(f"catalog game {game_id} settings route lacks game.rules: {route}")
        # Stop because no schema or defaults callable can be validated.
        return
    # Leave games with neither a settings route nor a schema unchanged.
    if not settings_routes and schema is None:
        # Return without creating a second allowlist for the other catalog games.
        return
    # Resolve the schema's defaults factory through the same callable boundary as backend metadata.
    defaults_reference = schema.get("defaults", "") if isinstance(schema, dict) else ""
    # Resolve the default factory while preserving all errors for one run.
    defaults_factory = resolve_callable(defaults_reference, f"{game_id} rules defaults", errors)
    # Call only the validated factory and treat failures as descriptor defects.
    if defaults_factory is not None:
        try:
            # Build a fresh default state without reading or writing persisted player data.
            defaults_state = defaults_factory()
        except Exception as exc:
            # Report a factory that cannot safely participate in catalog validation.
            errors.append(f"{game_id} rules defaults could not execute: {type(exc).__name__}: {exc}")
            # Use an empty state so schema validation still reports missing defaults.
            defaults_state = {}
    else:
        # Use an empty state after a callable-resolution error.
        defaults_state = {}
    # Add pure schema, safety-flag, and default-domain diagnostics.
    errors.extend(validate_rule_schema(game_id, schema, defaults_state))
    # Read the declared settings route only after the schema shape was inspected.
    declared_route = schema.get("settings_route") if isinstance(schema, dict) else None
    # Reject a descriptor that names a route the backend does not register.
    if declared_route not in settings_routes:
        # Report the declared route and the discovered set without invoking any handler.
        errors.append(f"catalog game {game_id} rules settings_route is not a registered POST route: {declared_route}")
    # Reject multiple settings routes because one descriptor must own one unambiguous surface.
    if len(settings_routes) > 1:
        # Report the complete deterministic route set for repair.
        errors.append(f"catalog game {game_id} registers multiple POST settings routes: {', '.join(sorted(settings_routes))}")


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
        register = resolve_callable(game.get("backend", {}).get("register", ""), f"{game_id} backend register", errors)  # Validate and retain API discovery.
        validate_settings_schema(game, register, errors)  # Gate every live settings route against its descriptor and defaults.
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
