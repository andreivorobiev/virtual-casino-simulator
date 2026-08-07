# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
"""Catalog-wide hostile-client and server-authority certification checks."""

# Import JSON support to compare the checked certification artifact with canonical sources.
import json
# Import pathlib so direct execution can resolve the repository root.
from pathlib import Path
# Import regular expressions so probe routes can use literal catalog identifiers.
import re
# Import sys so direct execution can load repository packages.
import sys
# Resolve the repository root from this test module location.
ROOT = Path(__file__).resolve().parents[1]
# Add the repository root before importing production and tooling packages.
sys.path.insert(0, str(ROOT))
# Import the canonical registered-game catalog.
from casino.config import GAMES
# Import the central request router exercised by every browser and native game client.
from casino.router import Router
# Import the exact protected-field set enforced at dispatch.
from casino.core.request_player import PROTECTED_GAME_FIELDS
# Import the deterministic matrix builder used by the contract validator.
from scripts.generate_server_authority_matrix import MATRIX_PATH, MANDATORY_ASSURANCES, build_matrix


# Prove complete catalog coverage, explicit actions, evidence, and protected-field alignment.
def validate_server_authority_matrix() -> None:
    # Load the checked-in artifact without silently regenerating it during tests.
    checked = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    # Rebuild the expected inventory from current catalog and OpenAPI sources.
    expected = build_matrix()
    # Fail closed when a game, contract action, evidence path, or policy field drifts.
    assert checked == expected, "server-authority matrix is stale; run scripts/generate_server_authority_matrix.py"
    # Require exact current-catalog coverage rather than a threshold or allowlist.
    assert [row["game_id"] for row in checked["games"]] == [game["id"] for game in GAMES]
    # Require the central runtime protected fields to match the published compatibility artifact.
    assert set(checked["protected_fields"]) == set(PROTECTED_GAME_FIELDS)
    # Validate every explicit catalog game and action record.
    for row in checked["games"]:
        # Require every mandatory scenario for this game with no omissions.
        assert set(row["assurances"]) == set(MANDATORY_ASSURANCES)
        # Require at least one state-changing action for each playable game.
        assert row["actions"], f"{row['game_id']} has no authority actions"
        # Require the generated row to identify the common source-proven settlement interface.
        assert row["settlement_interface"] == "casino.core.settlement.GameSettlementGateway"
        # Verify every referenced evidence file exists in the repository.
        for evidence in row["evidence"]:
            # Fail with the exact missing path for a focused catalog repair.
            assert (MATRIX_PATH.parents[2] / evidence).exists(), f"missing authority evidence: {evidence}"
        # Validate authority ownership on every explicit action.
        for action in row["actions"]:
            # Require frozen game routes rather than unversioned or shared-control paths.
            assert action["path"].startswith("/api/v1/games/")
            # Require bounded intent plus all downstream server owners.
            assert action["client_intent"] == "openapi_request_schema_and_path_choices_only"
            # Require ordinary server-side validation, outcome, and response projection labels.
            assert all(action[key].startswith(("authenticated_", "server_")) for key in ("server_validation", "engine_outcome", "response_projection"))
            # Bind the financial action owner to the exact source-derived game-row interface.
            assert action["storage_transaction"] == row["settlement_interface"]


# Prove all current games receive identical hostile-field stripping and session precedence.
def validate_catalog_dispatch_boundary() -> None:
    # Exercise one literal probe route per registered game through the real central router.
    for game in GAMES:
        # Create an isolated router so the probe cannot touch runtime data or listeners.
        router = Router()
        # Build a game-prefixed path that receives the same central protection as production routes.
        path = f"/api/v1/games/{game['id'].replace('_', '-')}/__authority_probe"
        # Register a capturing handler that returns only the canonical dispatch inputs.
        router.post(re.escape(path))(lambda body, query, context=None: {"body": body, "query": query, "context": context})
        # Supply every protected field plus legitimate bounded intent and hostile identities.
        hostile_body = {**{field: "attacker-value" for field in PROTECTED_GAME_FIELDS}, "player_id": "body-attacker", "action_id": "authority-probe", "wager": 1}
        # Dispatch under an authenticated player while also attacking the query identity.
        captured = router.dispatch("POST", path + "?player_id=query-attacker", hostile_body, {"bound_player_id": "session-player", "user": {"player_id": "session-player"}})
        # Require the authenticated identity to override body and query values for every game.
        assert captured["body"]["player_id"] == "session-player" and captured["query"]["player_id"] == "session-player"
        # Require allowed action identity and wager intent to survive canonicalization.
        assert captured["body"]["action_id"] == "authority-probe" and captured["body"]["wager"] == 1
        # Require no protected field to reach any game handler.
        assert not (set(captured["body"]) & set(PROTECTED_GAME_FIELDS))


# Run both focused checks from the central API harness and direct developer commands.
def run_server_authority_tests() -> None:
    # Validate the machine-readable catalog and per-action inventory first.
    validate_server_authority_matrix()
    # Validate the hostile-client dispatch boundary across the current catalog.
    validate_catalog_dispatch_boundary()


# Support a direct focused command without starting a listener.
if __name__ == "__main__":
    # Execute the complete focused certification checks.
    run_server_authority_tests()
    # Report success for local checkpoint logs.
    print("Server-authority certification checks passed.")
