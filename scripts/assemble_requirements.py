#!/usr/bin/env python3
"""Assemble the checked requirement registry from one spine and per-game shards."""

# Import argument parsing for explicit check, write, and one-time extraction modes.
import argparse
# Import JSON support for deterministic source and aggregate files.
import json
# Import paths so the command works independently of the caller directory.
import pathlib
# Import regular expressions for permanent requirement-prefix parsing.
import re

# Resolve the repository root from this tracked script.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Point to the generated compatibility aggregate consumed by existing tools.
AGGREGATE_PATH = ROOT / "docs" / "requirements" / "requirements.json"
# Point to the non-game requirement source and registry metadata.
SPINE_PATH = ROOT / "docs" / "requirements" / "requirements-spine.json"
# Point to independently owned game requirement shards.
GAME_SHARDS_DIR = ROOT / "docs" / "requirements" / "games"
# Recognize the permanent three-digit suffix without splitting multi-part prefixes.
REQUIREMENT_ID_RE = re.compile(r"^(?P<prefix>[A-Z][A-Z0-9-]*)-\d{3}$")


# Serialize governed JSON with one stable repository-wide representation.
def render_json(value):
    # Preserve Unicode copy while retaining deterministic indentation and final newline.
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


# Read one required JSON object and identify malformed source precisely.
def read_json_object(path):
    # Parse the complete UTF-8 source file.
    value = json.loads(path.read_text(encoding="utf-8"))
    # Reject array or scalar sources before callers inspect fields.
    if not isinstance(value, dict):
        # Name the invalid source path in the fail-closed diagnostic.
        raise ValueError(f"{path.relative_to(pathlib.Path(path.anchor))} must contain a JSON object")
    # Return the validated object without mutating its content.
    return value


# Extract the exact permanent prefix from one requirement id.
def requirement_prefix(requirement_id):
    # Match the complete identifier against the permanent-id grammar.
    match = REQUIREMENT_ID_RE.fullmatch(str(requirement_id))
    # Reject malformed identifiers instead of assigning them to the shared spine silently.
    if match is None:
        # Include the untrusted identifier only in a bounded developer diagnostic.
        raise ValueError(f"invalid requirement id: {requirement_id!r}")
    # Return the complete prefix, including internal hyphens such as BIG-SIX.
    return match.group("prefix")


# Load every game descriptor in stable catalog order.
def load_game_descriptors(root=ROOT):
    # Collect game-owned descriptor facts without importing application code.
    descriptors = []
    # Inspect each module descriptor deterministically.
    for path in sorted((root / "modules").glob("*.json")):
        # Skip the aggregate manifest because it has no independently owned game object.
        if path.stem == "module-manifest":
            # Continue with the next module descriptor.
            continue
        # Parse the module descriptor as tracked JSON.
        descriptor = read_json_object(path)
        # Read the optional game catalog object.
        game = descriptor.get("game")
        # Ignore non-game modules without creating a second allowlist.
        if not isinstance(game, dict):
            # Continue with the next descriptor.
            continue
        # Require the module filename, module field, and game id to agree.
        if descriptor.get("module") != path.stem or game.get("id") != path.stem:
            # Reject ambiguous shard ownership before reading requirements.
            raise ValueError(f"module/game identity mismatch in {path.name}")
        # Normalize the declared ownership prefixes as one immutable tuple.
        prefixes = tuple(descriptor.get("requirements_prefixes", ()))
        # Require at least one unique permanent prefix for every game shard.
        if not prefixes or len(prefixes) != len(set(prefixes)):
            # Name the descriptor whose shard ownership cannot be trusted.
            raise ValueError(f"{path.name} must declare unique requirements_prefixes")
        # Retain only the fields required for deterministic assembly.
        descriptors.append(
            {
                "id": path.stem,  # Preserve the canonical game identity.
                "sort_order": game.get("sort_order"),  # Preserve catalog ordering.
                "prefixes": prefixes,  # Preserve exact owned-prefix ordering.
            }
        )
    # Sort by numeric catalog order and then identity for deterministic ties.
    descriptors.sort(key=lambda item: (item["sort_order"], item["id"]))
    # Return the complete descriptor-derived game ownership inventory.
    return descriptors


# Build a unique prefix-to-game ownership map.
def build_prefix_owners(descriptors):
    # Start with no claimed game prefixes.
    owners = {}
    # Visit every descriptor in catalog order.
    for descriptor in descriptors:
        # Visit each prefix owned by the current game.
        for prefix in descriptor["prefixes"]:
            # Reject cross-game ownership collisions before partitioning source data.
            if prefix in owners:
                # Name both colliding owners for a focused repair.
                raise ValueError(f"requirement prefix {prefix} is owned by both {owners[prefix]} and {descriptor['id']}")
            # Record the unique owner for later partitioning and validation.
            owners[prefix] = descriptor["id"]
    # Return the complete ownership map.
    return owners


# Partition one aggregate registry into a non-game spine and per-game entries.
def partition_registry(registry, descriptors):
    # Require the existing registry array before the one-time extraction writes sources.
    requirements = registry.get("requirements")
    # Reject malformed aggregate data instead of creating incomplete shards.
    if not isinstance(requirements, list):
        # Identify the missing aggregate array.
        raise ValueError("requirements.json must contain a requirements list")
    # Resolve every game-owned prefix exactly once.
    owners = build_prefix_owners(descriptors)
    # Start the shared spine in the existing registry order.
    spine_requirements = []
    # Start one ordered requirement list per catalog game.
    game_requirements = {descriptor["id"]: [] for descriptor in descriptors}
    # Track permanent ids so extraction cannot preserve duplicates.
    seen_ids = set()
    # Partition each existing requirement without changing its object fields.
    for requirement in requirements:
        # Require object entries before reading the permanent id.
        if not isinstance(requirement, dict):
            # Reject scalar or array entries rather than hiding them in the spine.
            raise ValueError("requirements entries must be JSON objects")
        # Read and validate the permanent requirement id.
        requirement_id = requirement.get("id")
        # Resolve the complete ownership prefix.
        prefix = requirement_prefix(requirement_id)
        # Reject duplicate permanent identifiers before source files are created.
        if requirement_id in seen_ids:
            # Name the reused identifier in the diagnostic.
            raise ValueError(f"duplicate requirement id: {requirement_id}")
        # Record the identifier after successful validation.
        seen_ids.add(requirement_id)
        # Resolve an optional game owner from descriptor metadata.
        owner = owners.get(prefix)
        # Keep non-game requirements in the shared spine.
        if owner is None:
            # Preserve the original relative order within the spine.
            spine_requirements.append(requirement)
        # Move game-owned requirements to the matching independent shard.
        else:
            # Preserve the original relative order within the owning game.
            game_requirements[owner].append(requirement)
    # Return both independent source collections.
    return spine_requirements, game_requirements


# Assemble the compatibility aggregate from checked source shards.
def build_aggregate(root=ROOT):
    # Load descriptor-derived ownership and ordering.
    descriptors = load_game_descriptors(root)
    # Build the ownership map for shard-entry validation.
    owners = build_prefix_owners(descriptors)
    # Load the non-game registry metadata and requirements.
    spine_path = root / "docs" / "requirements" / "requirements-spine.json"
    # Parse the checked spine source.
    spine = read_json_object(spine_path)
    # Require the non-game requirement array.
    spine_requirements = spine.get("requirements")
    # Reject malformed spine content before loading game shards.
    if not isinstance(spine_requirements, list):
        # Name the exact invalid field.
        raise ValueError("requirements-spine.json must contain a requirements list")
    # Copy the source entries into the future aggregate without aliasing the parsed list.
    assembled = list(spine_requirements)
    # Track all ids across the spine and game shards.
    seen_ids = set()
    # Validate every spine requirement before game data is appended.
    for requirement in assembled:
        # Resolve and validate the permanent id grammar.
        requirement_id = requirement.get("id") if isinstance(requirement, dict) else None
        # Resolve the prefix so malformed source fails closed.
        prefix = requirement_prefix(requirement_id)
        # Reject a game-owned requirement left in the shared source.
        if prefix in owners:
            # Name the misplaced requirement and expected owner.
            raise ValueError(f"{requirement_id} belongs in game shard {owners[prefix]}")
        # Reject duplicate ids within the spine.
        if requirement_id in seen_ids:
            # Name the duplicated permanent id.
            raise ValueError(f"duplicate requirement id: {requirement_id}")
        # Record the validated id.
        seen_ids.add(requirement_id)
    # Load every game shard in descriptor catalog order.
    for descriptor in descriptors:
        # Resolve the exact independently owned source path.
        shard_path = root / "docs" / "requirements" / "games" / f"{descriptor['id']}.json"
        # Parse the required shard.
        shard = read_json_object(shard_path)
        # Require the shard identity to match its descriptor and filename.
        if shard.get("game") != descriptor["id"]:
            # Reject copy/paste ownership drift.
            raise ValueError(f"{shard_path.name} has mismatched game identity")
        # Require the shard to mirror descriptor-owned prefixes exactly.
        if tuple(shard.get("requirements_prefixes", ())) != descriptor["prefixes"]:
            # Reject stale ownership metadata.
            raise ValueError(f"{shard_path.name} requirements_prefixes are stale")
        # Require an explicit requirement list even for a future empty game shard.
        requirements = shard.get("requirements")
        # Reject malformed shard arrays.
        if not isinstance(requirements, list):
            # Name the invalid shard.
            raise ValueError(f"{shard_path.name} must contain a requirements list")
        # Validate each shard entry against its descriptor-owned prefix set.
        for requirement in requirements:
            # Read the permanent id only from an object entry.
            requirement_id = requirement.get("id") if isinstance(requirement, dict) else None
            # Resolve the exact prefix or fail on malformed input.
            prefix = requirement_prefix(requirement_id)
            # Reject requirements placed in the wrong game shard.
            if owners.get(prefix) != descriptor["id"]:
                # Name the misplaced permanent id and shard.
                raise ValueError(f"{requirement_id} is not owned by {descriptor['id']}")
            # Reject duplicates across all source files.
            if requirement_id in seen_ids:
                # Name the duplicated permanent id.
                raise ValueError(f"duplicate requirement id: {requirement_id}")
            # Record the validated id before adding the entry.
            seen_ids.add(requirement_id)
            # Append the unchanged requirement object in deterministic shard order.
            assembled.append(requirement)
    # Build the exact compatibility shape consumed by existing validators and generators.
    return {
        "source_baseline": spine.get("source_baseline"),  # Preserve historical baseline.
        "created_at": spine.get("created_at"),  # Preserve registry creation metadata.
        "requirements": assembled,  # Publish the deterministic source union.
    }


# Write the one-time source partition and normalized aggregate.
def extract_sources(root=ROOT):
    # Resolve repository-specific paths for testability.
    aggregate_path = root / "docs" / "requirements" / "requirements.json"
    # Resolve the future spine path.
    spine_path = root / "docs" / "requirements" / "requirements-spine.json"
    # Resolve the future shard directory.
    shards_dir = root / "docs" / "requirements" / "games"
    # Reject repeated extraction so checked sources cannot be overwritten from generated output.
    if spine_path.exists() or shards_dir.exists():
        # Require normal source editing after the initial migration.
        raise ValueError("requirement sources already exist; edit shards and use --write")
    # Parse the current compatibility aggregate as the migration source.
    registry = read_json_object(aggregate_path)
    # Load current descriptor ownership.
    descriptors = load_game_descriptors(root)
    # Partition without rewriting requirement objects.
    spine_requirements, game_requirements = partition_registry(registry, descriptors)
    # Create only the dedicated independently owned shard directory.
    shards_dir.mkdir(parents=True)
    # Build the non-game source object with preserved registry metadata.
    spine = {
        "source_baseline": registry.get("source_baseline"),  # Preserve historical baseline.
        "created_at": registry.get("created_at"),  # Preserve creation metadata.
        "requirements": spine_requirements,  # Store only non-game entries.
    }
    # Write the checked non-game source.
    spine_path.write_text(render_json(spine), encoding="utf-8")
    # Write one independently owned source per catalog game.
    for descriptor in descriptors:
        # Build a shard whose ownership metadata mirrors the descriptor.
        shard = {
            "game": descriptor["id"],  # Bind the file to one game identity.
            "requirements_prefixes": list(descriptor["prefixes"]),  # Mirror ownership.
            "requirements": game_requirements[descriptor["id"]],  # Preserve owned entries.
        }
        # Resolve the canonical shard path.
        shard_path = shards_dir / f"{descriptor['id']}.json"
        # Write stable checked JSON.
        shard_path.write_text(render_json(shard), encoding="utf-8")
    # Normalize the compatibility aggregate from the new checked sources.
    aggregate_path.write_text(render_json(build_aggregate(root)), encoding="utf-8")


# Write or check the generated compatibility aggregate.
def synchronize(root=ROOT, write=False):
    # Resolve the compatibility aggregate within the requested root.
    aggregate_path = root / "docs" / "requirements" / "requirements.json"
    # Render the complete checked source union deterministically.
    expected = render_json(build_aggregate(root))
    # Replace the generated aggregate only in explicit write mode.
    if write:
        # Write the complete normalized aggregate.
        aggregate_path.write_text(expected, encoding="utf-8")
        # Return success after the exact write.
        return True
    # Read the tracked aggregate for byte-exact drift comparison.
    current = aggregate_path.read_text(encoding="utf-8")
    # Return whether the compatibility aggregate is current.
    return current == expected


# Parse command-line mode and enforce fail-closed source synchronization.
def main(argv=None):
    # Create the bounded command-line interface.
    parser = argparse.ArgumentParser(description=__doc__)
    # Require exactly one explicit operation.
    mode = parser.add_mutually_exclusive_group()
    # Add the ordinary byte-exact validation mode.
    mode.add_argument("--check", action="store_true", help="fail when the aggregate is stale")
    # Add the normal source-to-aggregate regeneration mode.
    mode.add_argument("--write", action="store_true", help="rewrite the aggregate from sources")
    # Add the one-time migration mode guarded against repetition.
    mode.add_argument("--extract", action="store_true", help="partition the current aggregate once")
    # Parse the supplied or process arguments.
    args = parser.parse_args(argv)
    # Perform one-time extraction only when explicitly requested.
    if args.extract:
        # Create all source shards and normalize the aggregate.
        extract_sources(ROOT)
        # Report successful extraction without printing registry content.
        print("Extracted per-game requirement shards and normalized requirements.json.")
        # Return success after every source write completed.
        return 0
    # Regenerate from existing checked sources only in explicit write mode.
    if args.write:
        # Write the exact source union.
        synchronize(ROOT, write=True)
        # Report the governed output path.
        print("Regenerated docs/requirements/requirements.json from checked sources.")
        # Return success after the write.
        return 0
    # Use fail-closed checking as the safe default and explicit check behavior.
    if not synchronize(ROOT, write=False):
        # Provide the exact repair command without changing files in validation mode.
        print("Requirement aggregate is stale; run python scripts/assemble_requirements.py --write")
        # Return failure so CI blocks the drift.
        return 1
    # Report source and aggregate alignment.
    print("Requirement shard assembly passed.")
    # Return success after byte-exact validation.
    return 0


# Execute the command only when invoked as a script.
if __name__ == "__main__":
    # Return the fail-closed command status to the shell.
    raise SystemExit(main())
