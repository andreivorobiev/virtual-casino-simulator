"""Browser-free Long Suite driver rounding regressions for issue #406."""

# Import the dependency-free standard test runner.
import unittest

# Import only the catalog-discovered Hi-Lo Long Suite driver under test.
from tests.game_drivers import hi_lo


# Supply deterministic public API responses without starting a server or browser.
class FakeClient:
    # Store a terminal result and every requested route.
    def __init__(self, *, payout=2.64, net=1.27):
        # Preserve the expected terminal amounts for the guess response.
        self.payout = payout
        # Preserve the expected terminal net for the guess response.
        self.net = net
        # Record each public call for route and wager assertions.
        self.calls = []

    # Return one prepared round and one deterministic correct settlement.
    def call(self, path, method, body):
        # Record the public request before selecting its fixture response.
        self.calls.append((path, method, body))
        # Return the opening card and authoritative rank table for the deal.
        if path.endswith("/rounds"):
            # Publish an 8 so the 1.37 wager exercises 1.93x rounding to 2.64.
            return {"round": {"round_id": "hilo_fixture", "current_card": "8H"}, "rules": {"correct_paytable": {"2": 0.96, "3": 1.05, "4": 1.16, "5": 1.28, "6": 1.44, "7": 1.65, "8": 1.93, "9": 1.65, "10": 1.44, "J": 1.28, "Q": 1.16, "K": 1.05, "A": 0.96}}}
        # Return the deterministic terminal correct prediction.
        return {"round": {"phase": "settled", "next_card": "9S", "outcome": "correct", "payout": self.payout, "net": self.net}}


# Verify the discovered driver enforces the authoritative rounded settlement.
class HiLoLongDriverTests(unittest.TestCase):
    # Confirm a correctly rounded fractional wager passes and uses public routes.
    def test_rank_priced_rounding_passes(self):
        # Build the exact 1.37x1.93 rounded fixture.
        client = FakeClient()
        # Execute the production Long Suite driver.
        settled = hi_lo.play(client, 4)
        # Require the expected terminal return and the fractional wager request.
        self.assertEqual((2.64, 1.27, 1.37), (settled["payout"], settled["net"], client.calls[0][2]["wager"]))

    # Confirm one-cent settlement drift fails closed.
    def test_rank_priced_rounding_rejects_drift(self):
        # Build a response whose payout is one cent above the authoritative rounded value.
        client = FakeClient(payout=2.65, net=1.28)
        # Require the Long Suite driver to reject the mismatched settlement.
        with self.assertRaises(AssertionError):
            # Execute the same discovered public driver against the bad response.
            hi_lo.play(client, 5)


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
