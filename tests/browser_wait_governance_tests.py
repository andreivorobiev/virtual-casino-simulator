# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound regressions for the Browser wait races found in issue #750."""

# Import paths for exact repository-source inspection.
from pathlib import Path
# Import standard dependency-free assertions.
import unittest


# Resolve the exact checkout independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Read the governed Browser runner once for bounded source slices.
RUNNER_SOURCE = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")


# Prove Browser acceptance waits for authoritative state instead of elapsed time.
class BrowserWaitGovernanceTests(unittest.TestCase):
    # Require every Roulette audit wager to complete before a later clear can overtake it.
    def test_roulette_hit_target_waits_for_wager_responses(self) -> None:
        # Slice only the named Roulette case so unrelated request assertions remain unconstrained.
        roulette_source = RUNNER_SOURCE.partition("def roulette_hit_target_integrity():")[2].partition("run_case('BR-ROU-HITMAP-001'")[0]
        # Reject the former request-only wait that permitted late response adoption after clear.
        self.assertNotIn("expect_request(lambda request: request.url.partition('?')[0].endswith('/api/v1/games/roulette/bets')", roulette_source)
        # Require the primary-grid, second-dozen, and zero-zone loops to await exact responses.
        self.assertEqual(roulette_source.count("expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/bets')"), 3)
        # Require every response path to reject an unsuccessful wager before continuing.
        self.assertGreaterEqual(roulette_source.count(".value.ok"), 4)
        # Preserve posted-body verification through the completed response's original request.
        self.assertGreaterEqual(roulette_source.count(".value.request.post_data_json"), 3)

    # Require Three Card Poker to observe the requested locale rather than sleeping a fixed interval.
    def test_three_card_poker_waits_for_exact_localized_heading(self) -> None:
        # Slice only the named game acceptance function.
        poker_source = RUNNER_SOURCE.partition("def three_card_poker_acceptance():")[2].partition("run_case('BR-TCP-001'")[0]
        # Bind the expected English or Russian title before switching resources.
        self.assertIn("expected_title='Three Card Poker' if locale=='en-US' else 'Трёхкарточный покер'", poker_source)
        # Require a bounded semantic wait for the exact title text.
        self.assertIn("document.querySelector('.tcp-header h1')?.textContent === expected", poker_source)
        # Preserve an explicit final equality assertion after the semantic wait.
        self.assertIn("page.locator('.tcp-header h1').inner_text()==expected_title", poker_source)
        # Reject the former fixed-delay locale switch in this game case.
        self.assertNotIn("select_option(locale); page.wait_for_timeout(100)", poker_source)


# Support direct focused execution during local and hosted diagnosis.
if __name__ == "__main__":
    # Run the dependency-free source-bound suite.
    unittest.main()
