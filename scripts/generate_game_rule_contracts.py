# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Generate descriptor-owned OpenAPI request bodies for governed game settings routes."""

# Import JSON formatting so enum members retain exact JSON scalar types inside YAML.
import json
# Import pathlib so generation is independent of the caller working directory.
from pathlib import Path
# Import sys so direct script execution can load the repository package.
import sys

# Resolve the repository root from this script location.
ROOT = Path(__file__).resolve().parents[1]
# Add the repository root before importing the canonical catalog.
sys.path.insert(0, str(ROOT))
# Import immutable internal descriptors as the sole rule-contract source.
from casino.config import GAMES

# Mark generated blocks so contract diffs remain reviewable and idempotent.
BEGIN = "      # BEGIN GENERATED GAME RULE REQUEST BODY"
# Mark the end independently so stale or partial generated content fails closed.
END = "      # END GENERATED GAME RULE REQUEST BODY"


# Infer the OpenAPI scalar type for one closed enum vocabulary.
def _enum_type(values: list) -> str:
    # Publish numeric vocabularies as number because JSON int and float members can coexist canonically.
    if all(not isinstance(value, bool) and isinstance(value, (int, float)) for value in values):
        # Return the OpenAPI numeric type for payout and multiplier enums.
        return "number"
    # Publish strict boolean vocabularies as boolean when every member is a real bool.
    if all(isinstance(value, bool) for value in values):
        # Return the OpenAPI boolean type for a closed switch vocabulary.
        return "boolean"
    # Use string for the catalog's remaining closed textual vocabularies.
    return "string"


# Render one exact settings request body from a validated module descriptor.
def render_request_body(game: dict) -> str:
    # Read the descriptor whose structure and defaults already pass the catalog validator.
    schema = game["rules"]
    # Begin the generated block at the POST operation indentation level.
    lines = [BEGIN, "      requestBody:", "        required: false", "        content:", "          application/json:", "            schema:", "              type: object", "              additionalProperties: true", "              properties:"]
    # Emit fields deterministically so descriptor JSON order cannot affect contract bytes.
    for field in sorted(schema["fields"]):
        # Read one validated field domain.
        spec = schema["fields"][field]
        # Start the property block under the generated object schema.
        lines.append(f"                {field}:")
        # Translate the deliberately small runtime vocabulary to OpenAPI primitives.
        if spec["kind"] == "int":
            # Publish whole-number counts as integer.
            lines.append("                  type: integer")
        # Select the finite decimal representation for bounded non-integral rules.
        elif spec["kind"] == "number":
            # Publish bounded decimal settings as number.
            lines.append("                  type: number")
        # Select the strict boolean representation for on/off rules.
        elif spec["kind"] == "bool":
            # Publish strict switches as boolean.
            lines.append("                  type: boolean")
        else:
            # Infer the scalar type from the already-validated non-empty enum.
            lines.append(f"                  type: {_enum_type(spec['values'])}")
        # Publish inclusive lower bounds when the descriptor owns one.
        if "min" in spec:
            # Serialize the exact finite number through JSON syntax accepted by YAML.
            lines.append(f"                  minimum: {json.dumps(spec['min'])}")
        # Publish inclusive upper bounds when the descriptor owns one.
        if "max" in spec:
            # Serialize the exact finite number through JSON syntax accepted by YAML.
            lines.append(f"                  maximum: {json.dumps(spec['max'])}")
        # Publish closed vocabularies without retyping or normalizing their members.
        if "values" in spec:
            # JSON arrays are valid YAML and preserve deterministic compact formatting.
            lines.append(f"                  enum: {json.dumps(spec['values'], separators=(',', ':'))}")
    # Close the generated block with a stable marker and trailing newline supplied by the caller.
    lines.append(END)
    # Return the complete deterministic block.
    return "\n".join(lines)


# Insert or replace one generated request body beneath its exact POST operation id.
def update_contract(text: str, game: dict) -> str:
    # Render the expected block once for insertion or replacement.
    block = render_request_body(game)
    # Replace an existing generated block without touching any hand-owned contract bytes.
    if BEGIN in text or END in text:
        # Require both markers exactly once so partial or duplicated generation cannot pass silently.
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            # Fail with the owning game instead of guessing which bytes to replace.
            raise RuntimeError(f"malformed generated rule request block for {game['id']}")
        # Preserve the prefix and suffix around the complete generated section.
        prefix, remainder = text.split(BEGIN, 1)
        # Drop the previous generated content through the exact end marker.
        _, suffix = remainder.split(END, 1)
        # Return the source with only the generated region replaced.
        return prefix + block + suffix
    # Identify the exact operation id beneath the descriptor-owned settings path.
    operation = f"      operationId: {game['id']}_POST_api_v1_games_{game['id']}_settings\n"
    # Fail closed if contract naming has drifted from the canonical generator convention.
    if text.count(operation) != 1:
        # Name the game whose settings operation cannot be generated safely.
        raise RuntimeError(f"missing unique settings operationId for {game['id']}")
    # Insert the generated block immediately after the stable operation identity.
    return text.replace(operation, operation + block + "\n", 1)


# Return every catalog game that exposes a governed settings route.
def governed_games() -> list[dict]:
    # Filter only internal descriptors carrying a rule schema.
    return [game for game in GAMES if isinstance(game.get("rules"), dict)]


# Check or rewrite every governed game contract against descriptor-owned request bodies.
def synchronize(*, write: bool) -> list[str]:
    # Collect focused drift diagnostics in check mode.
    errors = []
    # Visit each governed game in canonical catalog order.
    for game in governed_games():
        # Resolve the game-owned primary OpenAPI contract.
        path = ROOT / game["contracts"][0]
        # Read the checked contract before deterministic transformation.
        current = path.read_text(encoding="utf-8")
        # Build the exact expected bytes from the descriptor.
        expected = update_contract(current, game)
        # Rewrite only when explicitly requested and bytes differ.
        if write and expected != current:
            # Publish the generated contract with the repository newline convention.
            path.write_text(expected, encoding="utf-8", newline="\n")
        # Report drift in check mode without mutating the worktree.
        elif not write and expected != current:
            # Name the exact contract and repair command.
            errors.append(f"{path.relative_to(ROOT).as_posix()} rule request body is stale; run python scripts/generate_game_rule_contracts.py --write")
    # Return every deterministic drift diagnostic to callers.
    return errors


# Execute the generator or fail-closed check from developer and CI commands.
def main() -> int:
    # Enable writes only through the explicit command-line flag.
    write = "--write" in sys.argv[1:]
    # Synchronize all governed contracts in the requested mode.
    errors = synchronize(write=write)
    # Print each drift on its own line for actionable CI logs.
    for error in errors:
        # Publish the stable repository-relative diagnostic.
        print(f"ERROR: {error}")
    # Report successful writes or checks for local qualification evidence.
    if not errors:
        # Name the mode without listing private or mutable data.
        print("Game rule request contracts synchronized." if write else "Game rule request contracts are current.")
    # Return nonzero whenever check mode found stale generated bytes.
    return 1 if errors else 0


# Run only when invoked as a script.
if __name__ == "__main__":
    # Exit with the fail-closed generator/check result.
    raise SystemExit(main())
