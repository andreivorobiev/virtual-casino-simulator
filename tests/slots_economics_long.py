"""Governed real-engine economics proof for SLOT-036."""

# Import JSON so the hosted Long lane publishes machine-readable evidence.
import json
# Import math for finite confidence and reconciliation checks.
import math
# Import the environment for exact hosted source provenance.
import os
# Import deterministic random streams while preserving the production SystemRandom object.
import random
# Import sample standard deviation for predeclared block confidence bounds.
import statistics
# Import unittest for fail-closed hosted execution.
import unittest
# Import paths for the governed artifact location.
from pathlib import Path

# Import the exact shipped Slots engine under qualification.
from casino.games.slots import engine


# Require one million paid spins in every approved scenario.
PAID_SPINS_PER_SCENARIO = 1_000_000
# Close one confidence block only after the final paid spin's complete bonus chain drains.
PAID_SPINS_PER_BLOCK = 10_000
# Bound one paid trigger's complete retrigger chain without truncating accepted evidence.
BONUS_CHAIN_CAP = 10_000
# Use the predeclared two-sided 99-percent normal critical value over one hundred blocks.
CONFIDENCE_Z_99 = 2.576
# Require every real-engine point estimate to remain in the approved broad near-92-percent band.
POINT_ESTIMATE_MINIMUM = 0.88
# Retain sampling headroom while rejecting any material player-positive drift.
POINT_ESTIMATE_MAXIMUM = 0.97
# Require the 99-percent upper confidence bound to remain strictly house-side.
UPPER_CONFIDENCE_LIMIT = 1.0
# Cover the five non-progressive best-play choices at the frozen cent minimum.
NON_PROGRESSIVE_SCENARIOS = [(lines, 0.01) for lines in (1, 3, 5, 9, 20)]
# Cover the only progressive qualifier separately from every nonqualifying strategy.
QUALIFYING_SCENARIO = (engine.PROGRESSIVE_QUALIFYING_LINES, engine.PROGRESSIVE_QUALIFYING_LINE_BET)
# Combine exactly the six owner-approved heavy scenarios.
SCENARIOS = [*NON_PROGRESSIVE_SCENARIOS, QUALIFYING_SCENARIO]
# Resolve the standard Long artifact directory.
ARTIFACT_DIR = Path("logs") / "test-runs"
# Resolve the exact evidence file uploaded by every Long shard.
ARTIFACT_PATH = ARTIFACT_DIR / "slots-economics-split-a.json"


# Add one result's disjoint components to a mutable evidence accumulator.
def add_result(totals, result):
    # Add the exact paid cost while free spins contribute zero.
    totals["cost"] += float(result["cost"])
    # Add the complete engine payout, including any qualifying progressive hit.
    totals["payout"] += float(result["payout"])
    # Add the ordinary payline component independently.
    totals["line_payout"] += float(result["line_payout"])
    # Add the scatter component independently.
    totals["scatter_payout"] += float(result["scatter_payout"])
    # Add the progressive component independently.
    totals["progressive_payout"] += float(result["progressive_hit"])
    # Count every paid and bonus action included in the numerator.
    totals["actions"] += 1


# Execute one deterministic real-engine scenario with complete per-paid-spin bonus drainage.
def run_scenario(active_lines, line_bet, seed):
    # Create fresh state so progressive, bonus, and recent-spin history cannot cross scenarios.
    state = engine.default_state()
    # Build total and current-block accumulators with the same exact component schema.
    totals = {"cost": 0.0, "payout": 0.0, "line_payout": 0.0, "scatter_payout": 0.0, "progressive_payout": 0.0, "actions": 0}
    # Build one independent accumulator for the current confidence block.
    block = {"cost": 0.0, "payout": 0.0, "line_payout": 0.0, "scatter_payout": 0.0, "progressive_payout": 0.0, "actions": 0}
    # Retain one hundred complete paid-cycle block returns.
    block_returns = []
    # Record the largest fully drained feature chain for boundedness evidence.
    maximum_bonus_chain = 0
    # Replace the production CSPRNG only inside this deterministic evidence boundary.
    production_rng = engine._rng
    # Enter a restoration boundary before the first deterministic draw.
    try:
        # Give every line/stake scenario an independent deterministic stream.
        engine._rng = random.Random(seed)
        # Execute exactly the predeclared number of paid spins.
        for paid_index in range(1, PAID_SPINS_PER_SCENARIO + 1):
            # Require the previous paid trigger's full chain to be closed before starting another wager.
            if int(state.get("free_spins", 0)) != 0:
                # Fail closed rather than smearing bonus return into a later paid block.
                raise AssertionError("bonus chain was not drained before the next paid spin")
            # Execute one paid real-engine spin at the scenario's exact legal settings.
            paid_result = engine.spin(state, active_lines, line_bet)
            # Require the action to remain paid and use the requested basis.
            if paid_result["free_spin"] or paid_result["cost"] != round(active_lines * line_bet, 2):
                # Fail closed on any cost or feature-state mismatch.
                raise AssertionError("paid spin did not retain its exact scenario basis")
            # Add the paid action to both complete and block evidence.
            add_result(totals, paid_result)
            # Add the paid action to the current confidence block.
            add_result(block, paid_result)
            # Reset this paid trigger's bounded feature-chain counter.
            bonus_chain = 0
            # Drain every pending and retriggered free spin before the block can close.
            while int(state.get("free_spins", 0)) > 0:
                # Increment before dispatch so a runaway chain fails at the fixed cap.
                bonus_chain += 1
                # Fail closed rather than truncate a bonus numerator.
                if bonus_chain > BONUS_CHAIN_CAP:
                    # Publish the scenario and paid index without state or entropy.
                    raise AssertionError(f"bonus chain exceeded cap at paid spin {paid_index}")
                # Deliberately submit an escalation basis to prove the server-owned paid basis remains locked.
                free_result = engine.spin(state, 1 if active_lines != 1 else 20, engine.MAX_LINE_BET)
                # Require the feature action to retain cost zero and exact earned basis.
                if not free_result["free_spin"] or free_result["cost"] != 0.0 or free_result["active_lines"] != active_lines or free_result["line_bet"] != line_bet:
                    # Fail closed on any free-spin basis escalation.
                    raise AssertionError("free spin did not retain its paid-trigger basis")
                # Require all free spins to leave the progressive untouched.
                if free_result["progressive_eligible"] or free_result["progressive_contribution"] != 0.0 or free_result["progressive_hit"] != 0.0:
                    # Fail closed on any feature-spin progressive leakage.
                    raise AssertionError("free spin touched the progressive")
                # Add the complete bonus return to the paid cycle that triggered it.
                add_result(totals, free_result)
                # Add the same complete bonus return to the current confidence block.
                add_result(block, free_result)
            # Retain the largest fully drained chain without exposing individual outcomes.
            maximum_bonus_chain = max(maximum_bonus_chain, bonus_chain)
            # Close each confidence block only after the boundary paid spin's complete chain drained.
            if paid_index % PAID_SPINS_PER_BLOCK == 0:
                # Require a positive paid-cost denominator for every predeclared block.
                if block["cost"] <= 0:
                    # Fail closed on an invalid denominator.
                    raise AssertionError("confidence block has no paid cost")
                # Store the complete paid-cycle block return.
                block_returns.append(block["payout"] / block["cost"])
                # Reset the block only after all associated feature payout was included.
                block = {"cost": 0.0, "payout": 0.0, "line_payout": 0.0, "scatter_payout": 0.0, "progressive_payout": 0.0, "actions": 0}
        # Require no pending bank after the final paid spin and its complete drain.
        if int(state.get("free_spins", 0)) != 0:
            # Reject truncated final evidence.
            raise AssertionError("final bonus chain remains pending")
    # Restore production entropy identity even when a fail-closed assertion fires.
    finally:
        # Put back the original SystemRandom object by identity.
        engine._rng = production_rng
    # Require exactly one hundred complete confidence blocks.
    if len(block_returns) != PAID_SPINS_PER_SCENARIO // PAID_SPINS_PER_BLOCK:
        # Reject missing or extra confidence evidence.
        raise AssertionError("unexpected confidence block count")
    # Reconcile the complete payout from its three disjoint engine components.
    component_total = totals["line_payout"] + totals["scatter_payout"] + totals["progressive_payout"]
    # Allow only bounded floating addition drift across millions of already-cent-rounded outcomes.
    if not math.isclose(totals["payout"], component_total, rel_tol=0.0, abs_tol=0.05):
        # Fail closed on any missing settlement source.
        raise AssertionError("payout components do not reconcile")
    # Calculate the paid-cost return point estimate.
    point_estimate = totals["payout"] / totals["cost"]
    # Calculate the standard error over complete paid-cycle blocks.
    standard_error = statistics.stdev(block_returns) / math.sqrt(len(block_returns))
    # Calculate the predeclared 99-percent upper confidence bound.
    upper_99 = statistics.mean(block_returns) + CONFIDENCE_Z_99 * standard_error
    # Return sanitized reproducible evidence without raw stops, state, or RNG internals.
    return {
        "active_lines": active_lines,  # Record the exact line-choice scenario.
        "line_bet": line_bet,  # Record the exact normalized stake scenario.
        "progressive_eligible": engine.progressive_eligible(active_lines, line_bet),  # Record eligibility.
        "paid_spins": PAID_SPINS_PER_SCENARIO,  # Record the paid-spin denominator count.
        "bonus_spins": totals["actions"] - PAID_SPINS_PER_SCENARIO,  # Record every drained feature action.
        "maximum_bonus_chain": maximum_bonus_chain,  # Record the largest observed bounded drain.
        "paid_cost": round(totals["cost"], 2),  # Record the paid-cost denominator.
        "payout": round(totals["payout"], 2),  # Record paid and bonus returns together.
        "line_payout": round(totals["line_payout"], 2),  # Record the base-line component.
        "scatter_payout": round(totals["scatter_payout"], 2),  # Record the scatter component.
        "progressive_payout": round(totals["progressive_payout"], 2),  # Record the meter component.
        "rtp": round(point_estimate, 8),  # Record the scenario point estimate.
        "block_count": len(block_returns),  # Record completed post-drain confidence blocks.
        "block_paid_spins": PAID_SPINS_PER_BLOCK,  # Record the paid spins in each block.
        "upper_99": round(upper_99, 8),  # Record the predeclared 99-percent upper bound.
        "bonus_chain_cap": BONUS_CHAIN_CAP,  # Record the fail-closed drain bound.
        "meter_fields": sorted(key for key in state if key.startswith("progressive")),  # Prove constant state.
        "rng_restored": engine._rng is production_rng,  # Prove production entropy was restored.
    }


# Qualify the exact six-scenario Split A economics matrix.
class SlotsEconomicsLongTests(unittest.TestCase):
    # Require real-engine best-play, confidence, component, and bounded-state evidence.
    def test_one_million_paid_spin_matrix(self):
        # Execute every predeclared scenario with an independent deterministic stream.
        scenarios = [run_scenario(lines, line_bet, 471_000 + index) for index, (lines, line_bet) in enumerate(SCENARIOS)]
        # Require the complete five-line non-progressive matrix plus one exact qualifier.
        self.assertEqual(len(scenarios), 6)
        # Require all point estimates to remain near the approved house-side band.
        self.assertTrue(all(POINT_ESTIMATE_MINIMUM <= row["rtp"] <= POINT_ESTIMATE_MAXIMUM for row in scenarios), scenarios)
        # Require every predeclared 99-percent upper bound to remain below player-positive.
        self.assertTrue(all(row["upper_99"] < UPPER_CONFIDENCE_LIMIT for row in scenarios), scenarios)
        # Resolve the best legal non-progressive scenario by measured point estimate.
        best_nonprogressive = max((row for row in scenarios if not row["progressive_eligible"]), key=lambda row: row["rtp"])
        # Require one-line play to remain the disclosed non-progressive best strategy.
        self.assertEqual(best_nonprogressive["active_lines"], 1, scenarios)
        # Require the disclosed non-progressive best-play estimate to stay near the audited 91.85-percent target.
        self.assertTrue(0.90 <= best_nonprogressive["rtp"] <= 0.94, best_nonprogressive)
        # Resolve the only progressive scenario and require the exact twenty-by-one qualifier.
        qualifying = [row for row in scenarios if row["progressive_eligible"]]
        # Require exactly one qualifying strategy across the complete matrix.
        self.assertEqual([(row["active_lines"], row["line_bet"]) for row in qualifying], [(20, 1.0)])
        # Require the exact qualifier estimate to stay near the audited 92.57-percent target.
        self.assertTrue(0.91 <= qualifying[0]["rtp"] <= 0.94, qualifying[0])
        # Require every scenario to restore production entropy and retain constant-size scalar state.
        self.assertTrue(all(row["rng_restored"] and row["meter_fields"] == ["progressive", "progressive_basis"] for row in scenarios), scenarios)
        # Create the governed artifact directory only after every fail-closed assertion passes.
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        # Build exact hosted provenance and predeclared methodology evidence.
        evidence = {
            "schema_version": 1,  # Version the compact evidence envelope.
            "requirement": "SLOT-036",  # Bind the artifact to its permanent requirement.
            "source_commit": os.environ.get("GITHUB_SHA", "local-browser-free"),  # Bind hosted evidence.
            "paid_spins_per_scenario": PAID_SPINS_PER_SCENARIO,  # Record the exact paid workload.
            "scenario_count": len(scenarios),  # Record the predeclared matrix cardinality.
            "method": "paid-cost denominator; every paid spin drains its complete bonus/retrigger chain before block closure",  # Record methodology.
            "confidence": {"blocks": 100, "paid_spins_per_block": PAID_SPINS_PER_BLOCK, "z_99": CONFIDENCE_Z_99, "upper_limit": UPPER_CONFIDENCE_LIMIT},  # Record the fixed confidence policy.
            "best_nonprogressive": {"active_lines": best_nonprogressive["active_lines"], "line_bet": best_nonprogressive["line_bet"], "rtp": best_nonprogressive["rtp"], "upper_99": best_nonprogressive["upper_99"]},  # Record best legal ordinary play.
            "qualifier": {"active_lines": qualifying[0]["active_lines"], "line_bet": qualifying[0]["line_bet"], "rtp": qualifying[0]["rtp"], "upper_99": qualifying[0]["upper_99"]},  # Record exact qualifying play.
            "scenarios": scenarios,  # Preserve every complete scenario result.
        }
        # Write canonical compact evidence for artifact hashing and review.
        ARTIFACT_PATH.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# Run the governed proof when the workflow executes this file directly.
if __name__ == "__main__":
    # Exit nonzero on the first failed economics invariant.
    unittest.main()
