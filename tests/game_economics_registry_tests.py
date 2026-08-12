# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-derived economics registry validation and executable production proof gate."""

# Import command-line parsing for the long-suite proof and artifact mode.
import argparse
# Import hashing so registry and production source identities are exact.
import hashlib
# Import dynamic modules so governed proof selectors execute without a copied model.
import importlib
# Import JSON parsing and canonical artifact writing.
import json
# Import environment access for hosted source identity.
import os
# Import paths for repository-owned source and evidence files.
from pathlib import Path
# Import regular expressions for exact machine identifiers and digests.
import re
# Import subprocess execution so each production proof receives its declared isolation boundary.
import subprocess
# Import the active Python runtime for exact child-test execution.
import sys
# Import the standard dependency-free test framework.
import unittest

# Import the canonical runtime catalog instead of maintaining a second game allowlist.
from casino import config
# Import authoritative Roulette engine and rules for exact catalog-wide bet enumeration.
from casino.games.roulette import engine as roulette_engine, rules as roulette_rules


# Resolve the repository root from this test module.
ROOT = Path(__file__).resolve().parents[1]
# Resolve the one governed source registry.
REGISTRY_PATH = ROOT / "tests" / "game_economics_registry.json"
# Resolve the default bounded artifact uploaded by the long-suite workflow.
ARTIFACT_PATH = ROOT / "logs" / "test-runs" / "game-economics-registry.json"
# Restrict classifications to the issue-owned disposition set currently needed by the catalog.
CLASSIFICATIONS = frozenset({"house_side", "intentionally_fair"})
# Require exact lowercase SHA-256 text for source bindings.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Require safe catalog and requirement identifiers without accepting arbitrary free-form text.
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_-]+$")


# Read one JSON object while preserving exact parse failures.
def read_json(path):
    # Parse only UTF-8 repository or test-artifact bytes.
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    # Require one object because arrays cannot carry the governed schema identity.
    if not isinstance(payload, dict):
        # Fail closed on a malformed top-level packet.
        raise AssertionError(f"{path} must contain one JSON object")
    # Return the validated top-level mapping.
    return payload


# Calculate a plain file digest for registry and artifact provenance.
def file_sha256(path):
    # Hash exact bytes so line endings and encoding drift cannot hide.
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# Calculate the ordered engine-plus-settlement digest recorded by one registry entry.
def production_sha256(entry):
    # Create one incremental SHA-256 state for both production owners.
    digest = hashlib.sha256()
    # Preserve engine then settlement order as part of the compatibility boundary.
    for field in ("engine_path", "settlement_path"):
        # Resolve the repository-relative production source.
        path = ROOT / entry[field]
        # Bind the relative path before its bytes so path swaps cannot collide.
        digest.update(entry[field].encode("utf-8") + b"\0")
        # Bind the exact authoritative source bytes.
        digest.update(path.read_bytes())
    # Return lowercase hexadecimal text used by the JSON registry.
    return digest.hexdigest()


# Return canonical catalog ids in runtime registration order.
def catalog_ids():
    # Reuse the exact descriptor list used by application registration.
    return [game["id"] for game in config.GAMES]


# Load all assembled permanent requirement identifiers.
def requirement_ids():
    # Read the generated complete registry because game requirements live in module-owned sources.
    payload = read_json(ROOT / "docs" / "requirements" / "requirements.json")
    # Return one exact identifier set for ownership validation.
    return {row["id"] for row in payload["requirements"]}


# Resolve one `module:Class.method` selector to an exact single unittest case.
def load_proof(selector):
    # Split the importable module from its test object reference.
    module_name, separator, test_name = selector.partition(":")
    # Reject malformed selectors before importing any module.
    if not separator or not module_name or not test_name:
        # Explain the governed selector shape without reflecting arbitrary source content.
        raise AssertionError("proof selector must use module:Class.method")
    # Import the declared proof owner through Python's ordinary module system.
    module = importlib.import_module(module_name)
    # Load only the exact named test rather than trusting broad discovery.
    suite = unittest.defaultTestLoader.loadTestsFromName(test_name, module)
    # Require one and only one executable case per registry selector.
    if suite.countTestCases() != 1:
        # Fail closed when a rename, deletion, or ambiguous selector drifts.
        raise AssertionError(f"proof selector {selector} resolved {suite.countTestCases()} tests")
    # Return the loaded suite and its source module for production-import checks.
    return suite, module


# Validate registry structure, catalog coverage, source bindings, and proof ownership.
def validate_registry(registry):
    # Require the first governed schema revision exactly.
    if registry.get("schema_version") != 1:
        # Reject unknown registry layouts rather than interpreting them loosely.
        raise AssertionError("economics registry schema_version must equal 1")
    # Require explicit play-token input and total-return output semantics.
    if registry.get("wager_unit") != "accepted play-token stake" or registry.get("return_unit") != "total returned play tokens, including any returned stake":
        # Prevent net-vs-gross denominator drift from changing RTP meaning.
        raise AssertionError("economics registry wager or return units drifted")
    # Require a reviewable list with one governed row per catalog game.
    entries = registry.get("entries")
    # Reject absent or non-list registry bodies.
    if not isinstance(entries, list):
        # Surface one stable structural failure.
        raise AssertionError("economics registry entries must be a list")
    # Derive runtime catalog identity from production descriptors.
    expected_ids = catalog_ids()
    # Read declared game ids only after checking each row shape.
    observed_ids = [entry.get("game_id") if isinstance(entry, dict) else None for entry in entries]
    # Require exact count from both the explicit guard and current runtime catalog.
    if registry.get("catalog_game_count") != 46 or len(expected_ids) != 46 or len(entries) != 46:
        # Fail on catalog growth, shrinkage, or stale declared count.
        raise AssertionError("economics registry must cover the exact 46-game catalog")
    # Reject duplicate identifiers before comparing order and membership.
    if len(observed_ids) != len(set(observed_ids)):
        # Keep duplicate registration from satisfying a missing game.
        raise AssertionError("economics registry contains a duplicate game_id")
    # Require exact canonical membership without making review grouping depend on sort order.
    if set(observed_ids) != set(expected_ids):
        # Report bounded lists because game ids are repository-controlled identifiers.
        raise AssertionError(f"economics registry ids {observed_ids} do not match catalog {expected_ids}")
    # Load requirement ownership once for all entries.
    known_requirements = requirement_ids()
    # Validate every catalog-owned proof entry independently.
    for entry in entries:
        # Require safe identifier text before using it in path comparisons.
        game_id = entry.get("game_id")
        # Reject unknown or malformed game ids even if catalog validation were bypassed.
        if not isinstance(game_id, str) or not IDENTIFIER_RE.fullmatch(game_id):
            # Fail closed on unsafe machine identity.
            raise AssertionError("economics registry contains an invalid game_id")
        # Require an accepted disposition for every game.
        classification = entry.get("classification")
        # Reject missing or future classification values until governance adds them explicitly.
        if classification not in CLASSIFICATIONS:
            # Name only the safe catalog id in the diagnostic.
            raise AssertionError(f"{game_id} has an unsupported economics classification")
        # Require numeric bounds while excluding booleans from Python's number hierarchy.
        upper = entry.get("expected_rtp_upper")
        # Reject absent, boolean, non-finite, or nonsensical return bounds.
        if isinstance(upper, bool) or not isinstance(upper, (int, float)) or not 0 <= upper <= 1:
            # Keep invalid proof math from entering evidence.
            raise AssertionError(f"{game_id} has an invalid expected_rtp_upper")
        # Require every settleable house-side game to stay strictly below even return.
        if classification == "house_side" and not upper < 1:
            # Make a player-positive or break-even regression fail the gate.
            raise AssertionError(f"{game_id} is not house-side")
        # Require intentionally fair games to have exact one-return bounds and a permanent decision issue.
        if classification == "intentionally_fair" and (game_id != "fan_tan" or entry.get("decision_issue") != 256 or entry.get("expected_rtp_lower") != 1.0 or upper != 1.0 or entry.get("fair_tolerance") != 0.0):
            # Refuse informal fairness exemptions.
            raise AssertionError(f"{game_id} lacks exact intentional-fairness governance")
        # Require a substantive proof-method explanation.
        if not isinstance(entry.get("proof_method"), str) or len(entry["proof_method"].strip()) < 20:
            # Prevent opaque labels from replacing reviewable method descriptions.
            raise AssertionError(f"{game_id} lacks a governed proof method")
        # Require a nonnegative integer sample count.
        sample_size = entry.get("sample_size")
        # Reject boolean or fractional workload descriptions.
        if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size < 0:
            # Keep workload evidence exact.
            raise AssertionError(f"{game_id} has an invalid sample_size")
        # Require a bounded nonnegative numeric error budget.
        error_budget = entry.get("error_budget")
        # Reject malformed or overbroad error allowances.
        if isinstance(error_budget, bool) or not isinstance(error_budget, (int, float)) or not 0 <= error_budget < 0.1:
            # Prevent sampling tolerance from concealing a player-positive result.
            raise AssertionError(f"{game_id} has an invalid error_budget")
        # Require sampled methods to declare enough deterministic trials for a meaningful gate.
        if sample_size and sample_size < 10000:
            # Reject token sampling that could pass through noise.
            raise AssertionError(f"{game_id} sampled proof is too small")
        # Require one existing permanent product requirement owner.
        requirement_id = entry.get("requirement_id")
        # Reject absent or stale requirement ownership.
        if requirement_id not in known_requirements:
            # Name the safe game identifier only.
            raise AssertionError(f"{game_id} references an unknown requirement")
        # Resolve both production source paths.
        engine_path = ROOT / str(entry.get("engine_path", ""))
        settlement_path = ROOT / str(entry.get("settlement_path", ""))
        # Require the engine to belong to the same catalog game.
        if engine_path != ROOT / "casino" / "games" / game_id / "engine.py" or not engine_path.is_file():
            # Refuse copied probability models under tests or another game.
            raise AssertionError(f"{game_id} engine_path is not its production engine")
        # Require the settlement adapter to belong to the same game and use the supported owner filename.
        if settlement_path.parent != engine_path.parent or settlement_path.name not in {"api.py", "service.py"} or not settlement_path.is_file():
            # Refuse a proof that never binds the authoritative returned-credit adapter.
            raise AssertionError(f"{game_id} settlement_path is not its production adapter")
        # Require exact digest syntax before comparing production bytes.
        source_digest = entry.get("production_sha256")
        # Reject malformed or stale source fingerprints.
        if not isinstance(source_digest, str) or not SHA256_RE.fullmatch(source_digest) or source_digest != production_sha256(entry):
            # Force requalification whenever engine or settlement source changes.
            raise AssertionError(f"{game_id} production source digest is stale")
        # Require at least one unique exact proof selector.
        proof_tests = entry.get("proof_tests")
        # Reject missing, malformed, or duplicated selectors.
        if not isinstance(proof_tests, list) or not proof_tests or not all(isinstance(selector, str) for selector in proof_tests) or len(proof_tests) != len(set(proof_tests)):
            # Fail before any test import.
            raise AssertionError(f"{game_id} proof_tests are invalid")
        # Resolve every proof now so absent or renamed evidence fails even in validate-only mode.
        for selector in proof_tests:
            # Load the exact single test and its owning source module.
            _suite, module = load_proof(selector)
            # Resolve the imported proof module path.
            module_path = Path(module.__file__).resolve()
            # Require repository-owned test source rather than an installed or generated module.
            if ROOT not in module_path.parents:
                # Prevent external models from qualifying production economics.
                raise AssertionError(f"{game_id} proof is outside the repository")
            # Read the proof source for an explicit production-game import/reference.
            proof_source = module_path.read_text(encoding="utf-8")
            # Require the exact production package name somewhere in the executable test source.
            if f"casino.games.{game_id}" not in proof_source:
                # Reject copied math that never imports the authoritative game.
                raise AssertionError(f"{game_id} proof does not reference its production package")
        # Require one substantive rationale after all executable ownership checks.
        if not isinstance(entry.get("rationale"), str) or len(entry["rationale"].strip()) < 40:
            # Prevent unexplained exemptions or inherited bounds.
            raise AssertionError(f"{game_id} lacks a documented economics rationale")
        # Validate any external long-proof artifact path without reading it in source-only mode.
        artifact = entry.get("evidence_artifact")
        # Restrict optional evidence to the standard retained logs directory.
        if artifact is not None and (not isinstance(artifact, str) or not artifact.startswith("logs/test-runs/") or ".." in Path(artifact).parts):
            # Reject arbitrary evidence reads.
            raise AssertionError(f"{game_id} evidence_artifact is outside the governed directory")
    # Return the exact validated entries for execution.
    return entries


# Verify one precomputed exact or long-simulation artifact before accepting its game.
def verify_external_artifact(entry):
    # Skip entries whose complete proof runs entirely through unittest selectors.
    if not entry.get("evidence_artifact"):
        # Return no artifact digest for ordinary entries.
        return None
    # Resolve the repository-contained evidence path.
    path = ROOT / entry["evidence_artifact"]
    # Require the preceding long-proof step to have created the artifact.
    if not path.is_file():
        # Fail closed instead of treating the short regression as complete evidence.
        raise AssertionError(f"{entry['game_id']} long economics artifact is missing")
    # Parse the artifact so malformed JSON cannot qualify.
    payload = read_json(path)
    # Require the artifact's own source identity to match hosted execution when GitHub supplies one.
    expected_source = os.environ.get("GITHUB_SHA")
    # Reject cross-commit artifact reuse in hosted CI.
    if expected_source and payload.get("source_commit") != expected_source:
        # Keep the diagnostic bounded to the safe game id.
        raise AssertionError(f"{entry['game_id']} long artifact source_commit mismatch")
    # Apply game-specific terminal checks without duplicating its probability model.
    if entry["game_id"] == "slots" and (payload.get("requirement") != "SLOT-036" or payload.get("scenario_count") != 6 or len(payload.get("scenarios", [])) != 6 or not all(row.get("upper_99", 1) < entry["expected_rtp_upper"] for row in payload.get("scenarios", []))):
        # Require the complete six-strategy, 99-percent-confidence result.
        raise AssertionError("slots long artifact is incomplete or player-positive")
    # Apply exact Keno coverage checks to its compact proof artifact.
    if entry["game_id"] == "keno" and (payload.get("requirement") != "KENO-027" or payload.get("outcome_count") != 230 or {row.get("picks") for row in payload.get("rows", [])} != set(range(1, 21)) or not all(max(row.get("ideal_rtp_decimal", 1), row.get("worst_low_cent_rtp_decimal", 1), row.get("large_amount_upper_bound_decimal", 1)) < entry["expected_rtp_upper"] for row in payload.get("rows", [])) or payload.get("rng_restored_success_and_failure") is not True):
        # Require every legal pick count and outcome class.
        raise AssertionError("keno exact artifact is incomplete")
    # Return the exact artifact hash for aggregate evidence.
    return file_sha256(path)


# Execute every registry-owned proof and write one bounded aggregate artifact.
def execute_registry(registry, artifact_path=ARTIFACT_PATH):
    # Validate all static, catalog, source, and selector invariants first.
    entries = validate_registry(registry)
    # Collect one sanitized result row per catalog game.
    results = []
    # Execute games in the checked-in review order after exact catalog membership validation.
    for entry in entries:
        # Verify any separately generated exhaustive or long-simulation artifact first.
        external_digest = verify_external_artifact(entry)
        # Execute each selector in a fresh interpreter because game-owned isolation may precede casino.config import.
        for selector in entry["proof_tests"]:
            # Translate the registry separator into unittest's dotted object selector.
            cli_selector = selector.replace(":", ".", 1)
            # Run only the exact selected proof with a bounded timeout and captured output.
            completed = subprocess.run([sys.executable, "-m", "unittest", cli_selector], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180)
            # Reject failure, skip, or an unexpected test count using standard unittest terminal text.
            combined = completed.stdout + completed.stderr
            # Require one completed, non-skipped test and a zero process status.
            if completed.returncode != 0 or "Ran 1 test" not in combined or "skipped=" in combined:
                # Include only the bounded output tail for diagnosis.
                raise AssertionError(f"{entry['game_id']} economics proof failed: {combined[-1200:]}")
        # Append only source identity, method, bound, and pass state.
        results.append({"game_id": entry["game_id"], "classification": entry["classification"], "expected_rtp_upper": entry["expected_rtp_upper"], "production_sha256": entry["production_sha256"], "proof_count": len(entry["proof_tests"]), "external_artifact_sha256": external_digest, "status": "PASS"})
    # Resolve the bounded destination selected by the governed workflow.
    output_path = Path(artifact_path)
    # Require the output to remain under the repository's standard evidence directory.
    if ROOT not in output_path.resolve().parents or "logs" not in output_path.resolve().parts:
        # Refuse arbitrary filesystem writes from a test command.
        raise AssertionError("economics artifact output must stay under repository logs")
    # Create only the task-owned artifact directory after all proofs pass.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Build one compact source-bound aggregate packet.
    artifact = {"schema_version": 1, "requirement": "TEST-175", "source_commit": os.environ.get("GITHUB_SHA", "local-browser-free"), "catalog_game_count": len(results), "catalog_ids": catalog_ids(), "registry_sha256": file_sha256(REGISTRY_PATH), "house_side_count": sum(row["classification"] == "house_side" for row in results), "intentionally_fair_count": sum(row["classification"] == "intentionally_fair" for row in results), "results": results}
    # Write stable sorted UTF-8 JSON for long-suite artifact retention.
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Return the packet for focused tests and CLI reporting.
    return artifact


# Provide one exact production enumeration missing from the historical focused suites.
class ProductionEconomicsProofTests(unittest.TestCase):
    # Prove every Roulette catalog wager remains house-side on every supported wheel.
    def test_roulette_catalog_is_house_side(self):
        # Enumerate both public wheel modes because single zero is the most favorable profile.
        for mode in ("single", "double"):
            # Resolve all equiprobable production outcomes for this wheel.
            outcomes = roulette_rules.roulette_numbers(mode)
            # Inspect every engine-owned wager row in the public catalog.
            for bet in roulette_rules.catalog(mode):
                # Build the exact one-token wager shape consumed by settlement.
                wager = {**bet, "amount": 1.0}
                # Sum total returned credits across the complete wheel.
                returned = sum(roulette_engine.settle_bet(wager, result, "normal")["credit"] for result in outcomes)
                # Require average total return below the original stake.
                self.assertLess(returned / len(outcomes), 1.0, (mode, bet["id"]))


# Cover registry structure and all required fail-closed mutation cases cheaply.
class GameEconomicsRegistryTests(unittest.TestCase):
    # Load a fresh mutable registry copy for each assertion.
    def registry(self):
        # Parse exact governed source bytes on every call.
        return read_json(REGISTRY_PATH)

    # Require the checked registry to match the exact runtime catalog and production sources.
    def test_registry_matches_catalog_and_sources(self):
        # Validate the complete checked-in packet without executing expensive proofs.
        entries = validate_registry(self.registry())
        # Require the one intentional-fairness decision and all other games house-side.
        self.assertEqual((46, 45, ["fan_tan"]), (len(entries), sum(row["classification"] == "house_side" for row in entries), [row["game_id"] for row in entries if row["classification"] == "intentionally_fair"]))

    # Require catalog removal and duplicate registration to fail closed.
    def test_missing_and_duplicate_games_fail(self):
        # Remove one canonical entry to simulate stale catalog coverage.
        missing = self.registry()
        # Delete the final entry without changing declared count.
        missing["entries"].pop()
        # Reject the missing game.
        with self.assertRaisesRegex(AssertionError, "exact 46-game catalog"):
            # Validate the hostile missing packet.
            validate_registry(missing)
        # Duplicate one id while retaining 46 rows.
        duplicate = self.registry()
        # Overwrite the final id with the preceding id.
        duplicate["entries"][-1]["game_id"] = duplicate["entries"][-2]["game_id"]
        # Reject duplicate identity before catalog comparison.
        with self.assertRaisesRegex(AssertionError, "duplicate game_id"):
            # Validate the hostile duplicate packet.
            validate_registry(duplicate)

    # Require absent proof and player-positive classification drift to fail closed.
    def test_absent_proof_and_player_positive_bound_fail(self):
        # Remove every selector from one otherwise valid game.
        absent = self.registry()
        # Clear Roulette proof ownership.
        absent["entries"][0]["proof_tests"] = []
        # Reject missing executable evidence.
        with self.assertRaisesRegex(AssertionError, "proof_tests are invalid"):
            # Validate the hostile absent-proof packet.
            validate_registry(absent)
        # Raise one house-side upper bound to player-positive.
        positive = self.registry()
        # Set Roulette above even return.
        positive["entries"][0]["expected_rtp_upper"] = 1.01
        # Reject the invalid RTP before execution.
        with self.assertRaisesRegex(AssertionError, "invalid expected_rtp_upper"):
            # Validate the hostile player-positive packet.
            validate_registry(positive)

    # Require a synthetic player-positive production settlement to fail its engine-backed proof.
    def test_player_positive_production_payout_fails(self):
        # Preserve the exact production settlement function around the hostile payout mutation.
        original_settle_bet = roulette_engine.settle_bet
        # Replace every settled wager with more than the accepted stake.
        roulette_engine.settle_bet = lambda _wager, _result, _zero_rule: {"credit": 1.01}
        # Restore production behavior even when the expected assertion fires.
        try:
            # Reject the synthetic player-positive payout through the executable production proof.
            with self.assertRaises(AssertionError):
                # Invoke the same exact case registered for Roulette.
                ProductionEconomicsProofTests("test_roulette_catalog_is_house_side").test_roulette_catalog_is_house_side()
        # Always release the hostile function before another registry test runs.
        finally:
            # Restore the exact imported production settlement function.
            roulette_engine.settle_bet = original_settle_bet

    # Require stale production bytes and copied non-production models to fail closed.
    def test_stale_source_and_nonproduction_model_fail(self):
        # Corrupt one exact production digest.
        stale = self.registry()
        # Replace Roulette's binding with a syntactically valid wrong hash.
        stale["entries"][0]["production_sha256"] = "0" * 64
        # Reject stale source identity.
        with self.assertRaisesRegex(AssertionError, "source digest is stale"):
            # Validate the hostile stale packet.
            validate_registry(stale)
        # Point one entry at a test-side copied model.
        copied = self.registry()
        # Replace the engine owner with this test file.
        copied["entries"][0]["engine_path"] = "tests/game_economics_registry_tests.py"
        # Reject the copied probability model before digest checks.
        with self.assertRaisesRegex(AssertionError, "not its production engine"):
            # Validate the hostile non-production packet.
            validate_registry(copied)


# Run validate-only or complete executable proof mode from governed workflows.
def main(argv=None):
    # Define the bounded command-line surface.
    parser = argparse.ArgumentParser(description="Validate or execute the 46-game economics registry")
    # Allow complete proof execution only when explicitly requested by the long suite.
    parser.add_argument("--execute", action="store_true")
    # Allow the workflow to choose a contained aggregate artifact path.
    parser.add_argument("--artifact", default=str(ARTIFACT_PATH))
    # Parse caller arguments without accepting unknown switches.
    args = parser.parse_args(argv)
    # Load the governed registry exactly once for this command.
    registry = read_json(REGISTRY_PATH)
    # Execute every registered proof and emit the artifact when requested.
    if args.execute:
        # Run the complete catalog proof.
        artifact = execute_registry(registry, args.artifact)
        # Emit one compact terminal summary for CI logs.
        print(f"GAME_ECONOMICS_REGISTRY PASS {artifact['catalog_game_count']}/46 registry_sha256={artifact['registry_sha256']}")
        # Return success after the artifact is durable.
        return 0
    # Otherwise validate catalog, source, requirement, and selector bindings only.
    entries = validate_registry(registry)
    # Emit one compact source-validation summary.
    print(f"GAME_ECONOMICS_REGISTRY VALID {len(entries)}/46 registry_sha256={file_sha256(REGISTRY_PATH)}")
    # Return success for source-only validation.
    return 0


# Support `python -m` workflow execution without listener or environment mutation.
if __name__ == "__main__":
    # Exit with the exact bounded command result.
    raise SystemExit(main())
