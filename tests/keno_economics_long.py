"""Governed exact-outcome Long proof for KENO-027."""

# Import JSON so hosted Long publishes a machine-readable exact-proof artifact.
import json
# Import the hosted commit identity without exposing unrelated environment values.
import os
# Import paths for the standard uploaded Long evidence directory.
from pathlib import Path
# Import fail-closed test execution for the governed workflow entrypoint.
import unittest
# Import patching so every production draw class uses bounded deterministic entropy.
from unittest import mock

# Import the shipped Keno engine qualified by this proof.
from casino.games.keno import engine
# Import exact proof helpers shared with the focused browser-free regression.
from tests.games.keno.test_economics import (
    LOW_CENT_AMOUNTS,
    MAX_AMOUNT,
    FailingBalls,
    ScriptedBalls,
    exact_ideal_rtp,
    exact_probability,
    large_amount_rtp_upper_bound,
    production_realized_rtp,
)


# Resolve the standard Long artifact directory uploaded by the shard workflow.
ARTIFACT_DIR = Path("logs") / "test-runs"
# Resolve one requirement-owned machine-readable proof artifact.
ARTIFACT_PATH = ARTIFACT_DIR / "keno-economics-exact.json"


# Return a canonical exact rational string for machine-reviewable evidence.
def fraction_text(value):
    # Render integers without a redundant denominator and other rationals as numerator/denominator.
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


# Build one valid deterministic selected/drawn pair for an exact catch class.
def deterministic_class(picks, catches):
    # Use the first legal values as the selected ticket.
    selected = list(range(1, picks + 1))
    # Keep the requested selected prefix and fill remaining balls outside all selected values.
    drawn = selected[:catches] + list(range(21, 81))[: 20 - catches]
    # Return stable ticket and draw values for the production engine.
    return selected, drawn


# Execute and report the exact 230-class Keno economics proof.
class KenoEconomicsLongTests(unittest.TestCase):
    # Require exact ideal, realized, production-engine, shape, and entropy evidence.
    def test_exact_outcome_and_full_amount_domain(self):
        # Preserve the production SystemRandom object identity around every deterministic draw.
        original_rng = engine._SYSTEM_RANDOM
        # Store sanitized evidence for every legal spot count.
        rows = []
        # Count every production engine outcome class.
        outcome_count = 0
        # Visit every legal pick count.
        for picks in range(1, 21):
            # Require the exact probability row to exhaust the complete draw space.
            self.assertEqual(sum(exact_probability(picks, catches) for catches in range(picks + 1)), 1)
            # Execute each catches class through the real engine draw boundary.
            for catches in range(picks + 1):
                # Build one exact deterministic class.
                selected, drawn = deterministic_class(picks, catches)
                # Start from one fresh compatible state.
                state = engine.default_state()
                # Add a low-cent ticket through the real engine boundary.
                engine.add_ticket(state, "human", selected, 0.03, source="governed-long")
                # Replace only the production entropy seam for this exact action.
                with mock.patch.object(engine, "_SYSTEM_RANDOM", ScriptedBalls(drawn)):
                    # Execute the production draw and capture its one result.
                    result = engine.commit_draw(state)["results"][0]
                # Require production entropy identity after every completed class.
                self.assertIs(engine._SYSTEM_RANDOM, original_rng)
                # Resolve the expected authoritative multiplier.
                expected_multiplier = engine.PAYTABLE[picks].get(catches, 0)
                # Require catches, multiplier, and the frozen float-plus-round payout law.
                self.assertEqual((result["catch_count"], result["multiplier"], result["payout"]), (catches, expected_multiplier, round(0.03 * expected_multiplier, 2)))
                # Count the completed production class.
                outcome_count += 1
            # Calculate every low-cent realized value under the exact production expression.
            low_values = [(amount, production_realized_rtp(picks, amount)) for amount in LOW_CENT_AMOUNTS]
            # Resolve the maximum enumerated low-cent realization and its amount.
            worst_amount, worst_realized = max(low_values, key=lambda item: item[1])
            # Resolve the exact analytic upper bound for every accepted amount at least one token.
            analytic_upper = large_amount_rtp_upper_bound(picks)
            # Require both finite-domain and analytic-domain realizations to remain house-side.
            self.assertLess(max(worst_realized, production_realized_rtp(picks, MAX_AMOUNT), analytic_upper), 1)
            # Resolve the exact ideal return once for both rational and additive decimal evidence.
            ideal_rtp = exact_ideal_rtp(picks)
            # Append sanitized exact-method evidence for this row.
            rows.append(
                {
                    "picks": picks,  # Bind the row to its legal pick count.
                    "outcome_classes": picks + 1,  # Record exact losing and paying class coverage.
                    "ideal_rtp_fraction": fraction_text(ideal_rtp),  # Preserve the exact hypergeometric rational.
                    "ideal_rtp_decimal": float(ideal_rtp),  # Add a concise review-oriented decimal.
                    "worst_low_cent_amount": float(worst_amount),  # Record the enumerated worst stake.
                    "worst_low_cent_rtp_fraction": fraction_text(worst_realized),  # Preserve exact weighted production rounding.
                    "worst_low_cent_rtp_decimal": float(worst_realized),  # Add a concise review-oriented decimal.
                    "large_amount_upper_bound_fraction": fraction_text(analytic_upper),  # Preserve the exact accumulated one-sided bound.
                    "large_amount_upper_bound_decimal": float(analytic_upper),  # Add a concise review-oriented decimal.
                    "jackpot_multiplier": engine.PAYTABLE[picks][picks],  # Record exact visible top award.
                }
            )
        # Require the mathematically complete class count.
        self.assertEqual(outcome_count, 230)
        # Inject a production entropy failure inside the same restoration boundary.
        with self.assertRaises(RuntimeError):
            # Replace only the entropy seam for the failing action.
            with mock.patch.object(engine, "_SYSTEM_RANDOM", FailingBalls()):
                # Execute a valid one-ticket state that reaches the injected failure.
                engine.commit_draw({"open_tickets": [{"ticket_id": "long-failure", "player_id": "human", "spots": [1], "amount": 1}], "last_draws": []})
        # Require production entropy identity after the injected failure.
        self.assertIs(engine._SYSTEM_RANDOM, original_rng)
        # Create the uploaded artifact directory only after every invariant passes.
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        # Build compact governed proof evidence.
        evidence = {
            "schema_version": 1,  # Version the evidence format.
            "requirement": "KENO-027",  # Bind the proof to its permanent requirement.
            "source_commit": os.environ.get("GITHUB_SHA", "local-browser-free"),  # Bind hosted evidence.
            "method": "exact 230-class hypergeometric enumeration; production float-plus-round low-cent oracle; one-sided IEEE-754 bound for amounts at least one play token",  # Disclose the complete method.
            "outcome_count": outcome_count,  # Record exact production class coverage.
            "low_cent_range": {"minimum": 0.01, "maximum": 0.99, "step": 0.01},  # Record finite enumeration.
            "accepted_maximum": float(MAX_AMOUNT),  # Record the frozen maximum.
            "rng_restored_success_and_failure": engine._SYSTEM_RANDOM is original_rng,  # Record identity restoration.
            "rows": rows,  # Preserve every per-pick economics result.
        }
        # Write deterministic sorted JSON for hosted hashing and review.
        ARTIFACT_PATH.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# Execute the governed proof when the workflow invokes this package module.
if __name__ == "__main__":
    # Exit nonzero on the first fail-closed proof violation.
    unittest.main()
