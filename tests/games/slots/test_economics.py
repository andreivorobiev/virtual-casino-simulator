"""Slots economics regression tests for the RTP rebalance (issue #456).

Before the rebalance, slots best-play RTP was ~400-515% (base game ~180-224%,
free spins +220-290% because ~55% of spins ended up free, progressive +12-14%).
This suite drives the REAL engine.spin over a cheap seeded Monte-Carlo run and
asserts the total return is now house-side (< 1.0, target ~92%) and that the
free-spin feature is a bounded bonus rather than the majority of all spins.
"""

# Import random so the CSPRNG can be replaced with a seeded, reproducible generator.
import random
# Import the dependency-free standard unit-test runner.
import unittest
# Import the pure slots engine under test.
from casino.games.slots import engine


# Run a reproducible RTP simulation directly against the production spin() settlement.
def _simulate(spins, active_lines, seed):
    # Swap the module CSPRNG for a seeded generator so the measured RTP is deterministic.
    engine._rng = random.Random(seed)
    # Begin from a fresh player state so the progressive pool starts at PROGRESSIVE_SEED.
    state = engine.default_state()
    # Track total paid wager and total returned payout across the run.
    wagered = 0.0
    returned = 0.0
    # Count paid versus free spins so the free-spin amplification can be checked.
    paid_spins = 0
    free_spins = 0
    # Play the requested number of spins through the real engine.
    for _ in range(spins):
        # Settle one spin at the given line count and a unit line bet.
        result = engine.spin(state, active_lines=active_lines, line_bet=1.0)
        # Accumulate every credited payout, including free-spin and progressive winnings.
        returned += result["payout"]
        # A zero-cost spin is a free spin funded by an earlier scatter trigger.
        if result["cost"] == 0:
            # Count the free spin without adding to the wagered denominator.
            free_spins += 1
        # Otherwise this is a paid spin that debited the wager.
        else:
            # Count the paid spin and add its cost to the wagered total.
            paid_spins += 1
            # Accumulate the real debited wager for the RTP denominator.
            wagered += result["cost"]
        # Drop the rolling history so the state dict stays small and the loop stays cheap.
        state["last_spins"] = []
    # Return the measured total RTP and the free-to-paid spin ratio.
    return {"rtp": returned / wagered, "free_ratio": free_spins / paid_spins}


# Cover the rebalanced slots economics: house-side RTP and a bounded free-spin bonus.
class SlotsEconomicsTests(unittest.TestCase):
    # Run one shared seeded simulation for the whole class so the suite stays fast.
    @classmethod
    def setUpClass(cls):
        # Preserve the production CSPRNG instance so seeded runs never leak into other suites.
        cls._original_rng = engine._rng
        # Simulate 100k default five-line spins once; deterministic total RTP is ~92.7% at this seed.
        cls.stats = _simulate(100_000, active_lines=5, seed=5)

    # Restore the untouched module CSPRNG after the class completes.
    @classmethod
    def tearDownClass(cls):
        # Put the original SystemRandom instance back so downstream tests keep real entropy.
        engine._rng = cls._original_rng

    # Verify the paytable now yields a genuine house edge instead of the pre-#456 4-5x payout.
    def test_total_rtp_is_house_side(self):
        # Require the measured total RTP to stay strictly below 1.0 (the core house-edge invariant).
        self.assertLess(self.stats["rtp"], 1.0)
        # Require the rebalance not to have over-nerfed the game into an unplayable return.
        self.assertGreater(self.stats["rtp"], 0.80)

    # Verify free spins are a modest bonus rather than the majority of all spins.
    def test_free_spins_are_a_bounded_bonus(self):
        # Free spins were ~1.25x paid spins before #456; require them to be a small fraction now.
        self.assertLess(self.stats["free_ratio"], 0.60)
        # The per-trigger award must stay well under the old 8 so the retrigger cascade converges.
        self.assertLessEqual(engine.FREE_SPINS_AWARDED, 6)
        # The progressive seed must be reduced from the old 1000 so the flat jackpot cannot dominate RTP.
        self.assertLess(engine.PROGRESSIVE_SEED, 1000.0)

    # Verify the all-Wild payline invariant relied on by the browser payline acceptance test still holds.
    def test_wild_five_of_a_kind_still_pays(self):
        # A five-Wild line must keep a positive multiplier so every payline can win.
        self.assertGreater(engine.PAYTABLE["WILD"][5], 0)
        # Build the deterministic all-Wild grid used by the payline acceptance evidence.
        grid = [["WILD"] * 5 for _ in range(3)]
        # Evaluate the grid across the full twenty-line table through the production rules.
        result = engine.evaluate(grid, 20, 1)
        # Require all twenty indexed paylines to register as wins.
        self.assertEqual(len(result["wins"]), 20)


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest's standard command-line runner.
    unittest.main()
