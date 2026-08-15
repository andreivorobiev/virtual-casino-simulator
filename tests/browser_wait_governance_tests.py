# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound regressions for the Browser wait races found in issue #750."""

# Import paths for exact repository-source inspection.
from pathlib import Path
# Import standard dependency-free assertions.
import unittest

# Import the state-driven Bingo boundaries used by the real Browser runner.
from tests.browser_readiness import require_bingo_terminal_auto_payload, require_bingo_terminal_reload_payload, wait_for_bingo_terminal_render


# Resolve the exact checkout independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Read the governed Browser runner once for bounded source slices.
RUNNER_SOURCE = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")


# Prove Browser acceptance waits for authoritative state instead of elapsed time.
class BrowserWaitGovernanceTests(unittest.TestCase):
    # Build one authoritative auto or reload payload for focused readiness tests.
    @staticmethod
    def bingo_payload(*, include_session=True, session_id="bingo-ready"):
        # Build the exact public winning card projection consumed by Bingo rendering.
        winner_card = {"card_id": "card-ready", "winning_coords": [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]]}
        # Build one terminal archived session with stable identity and geometry.
        session = {"session_id": session_id, "status": "won", "winner_card": winner_card}
        # Build the provider-authoritative terminal state returned by both endpoints.
        state = {"active_session": None, "last_sessions": [session]}
        # Include the mutation-owned session only for the auto response shape.
        data = {"state": state, **({"session": session} if include_session else {})}
        # Return the standard successful response envelope.
        return {"ok": True, "data": data}

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

    # Require the Bingo Browser chain to remount through an observed state response.
    def test_bingo_terminal_gate_uses_authoritative_route_readiness(self) -> None:
        # Slice the exact Bingo producer-consumer chain without constraining later games.
        bingo_source = RUNNER_SOURCE.partition("if browser_shard_owns_group('bingo_admin'):")[2].partition("# Seed one isolated deferred natural")[0]
        # Preserve the two permanent case ids and their exact existing requirement mappings.
        self.assertEqual(bingo_source.count("run_case('BR-BINGO-PURCHASE-001',['BINGO-012','BINGO-022','LEDGER-020','TEST-010','TEST-012']"), 1)
        # Preserve the premium terminal case identity and mapping byte-for-byte.
        self.assertEqual(bingo_source.count("run_case('BR-BINGO-001',['BINGO-017','BINGO-018','BINGO-021','BINGO-022','AUTO-013']"), 1)
        # Require explicit auto-response and reload-response validation around a lobby transition.
        self.assertIn("require_bingo_terminal_auto_payload(bingo_auto_payload)", bingo_source)
        # Require route ownership to leave Bingo before the state-response-observed remount.
        self.assertIn("page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)", bingo_source)
        # Bind the remount to the authoritative state response consumed by Bingo load().
        self.assertIn("page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/bingo/state')", bingo_source)
        # Require the complete terminal render helper after the exact-session reload check.
        self.assertIn("wait_for_bingo_terminal_render(page,bingo_reload_terminal)", bingo_source)
        # Reject the former same-route fixed winning-cell wait that flaked on shard zero.
        self.assertNotIn("page.get_by_test_id('nav-bingo').click(); page.locator('[data-winning-cell=\"true\"]').first.wait_for(timeout=5000)", bingo_source)

    # Prove a delayed terminal render is polled by state rather than accepted by elapsed time.
    def test_bingo_terminal_render_waits_through_delayed_snapshots(self) -> None:
        # Model one monotonic clock advanced only by the fake page's bounded yields.
        class Clock:
            # Start at a deterministic zero point.
            value = 0.0

            # Return the current deterministic monotonic value.
            def __call__(self):
                # Expose the fake time without consulting the wall clock.
                return self.value

        # Model two incomplete renders followed by the complete terminal surface.
        class Page:
            # Retain delayed snapshots and yield durations for exact assertions.
            def __init__(self, clock):
                # Bind the shared fake clock used by the readiness deadline.
                self.clock = clock
                # Queue two loading states and the authoritative terminal render.
                self.snapshots = [{"premium": False}, {"premium": True, "card": True, "drawer": False, "autoplay": True, "winningCellCount": 0, "busy": "false"}, {"premium": True, "card": True, "drawer": True, "autoplay": True, "winningCellCount": 5, "busy": "false"}]
                # Retain every bounded yield requested before readiness.
                self.waits = []

            # Return the next semantic snapshot without interpreting JavaScript in the fixture.
            def evaluate(self, _source):
                # Preserve the terminal snapshot after the queue is exhausted.
                return self.snapshots.pop(0) if len(self.snapshots) > 1 else self.snapshots[0]

            # Advance only the deterministic fake clock for one bounded poll.
            def wait_for_timeout(self, milliseconds):
                # Record the non-blanket wait for diagnostic assertions.
                self.waits.append(milliseconds)
                # Advance the fake monotonic clock by the requested duration.
                self.clock.value += milliseconds / 1000

        # Build authoritative auto evidence before any DOM wait begins.
        descriptor = require_bingo_terminal_auto_payload(self.bingo_payload())
        # Create the delayed page and deterministic clock.
        clock, page = Clock(), None
        # Bind the page after the clock exists.
        page = Page(clock)
        # Wait until the third semantic snapshot reflects the exact terminal geometry.
        result = wait_for_bingo_terminal_render(page, descriptor, timeout_seconds=1, poll_interval_ms=50, clock=clock)
        # Require state-driven completion after two bounded polls, not immediate elapsed-time acceptance.
        self.assertEqual((result["winningCellCount"], page.waits), (5, [50, 50]))

    # Require missing or malformed terminal API state to fail with useful diagnostics.
    def test_bingo_terminal_payloads_fail_closed(self) -> None:
        # Reject an unsuccessful auto envelope before route transition.
        with self.assertRaisesRegex(AssertionError, "not a successful standard envelope"):
            # Supply the exact malformed top-level response.
            require_bingo_terminal_auto_payload({"ok": False, "error": {"message": "failed"}})
        # Reject a winning label whose public geometry is absent.
        with self.assertRaisesRegex(AssertionError, "winning coordinates were missing or malformed"):
            # Remove the winning coordinates from both matching response projections.
            payload = self.bingo_payload(); payload["data"]["session"]["winner_card"]["winning_coords"] = []
            # Validate the malformed mutation response.
            require_bingo_terminal_auto_payload(payload)
        # Reject a reload that recovers a different terminal session identity.
        with self.assertRaisesRegex(AssertionError, "session identity mismatch"):
            # Validate a well-formed but stale different-session response.
            require_bingo_terminal_reload_payload(self.bingo_payload(include_session=False, session_id="bingo-stale"), "bingo-ready")


# Support direct focused execution during local and hosted diagnosis.
if __name__ == "__main__":
    # Run the dependency-free source-bound suite.
    unittest.main()
