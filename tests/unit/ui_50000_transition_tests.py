# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused TEST-092 transition-boundary proofs for the formal UI harness."""

import asyncio  # Execute asynchronous harness transitions without launching a browser.
import unittest  # Register the focused transition proofs with the required API gate.
from collections import Counter  # Track only real control activations at the public pointer boundary.
from unittest import mock  # Replace Playwright seams with deterministic public-interface fakes.

from tests import ui_50000  # Exercise the exact production harness helpers owned by TEST-092.


# Prove formal UI transitions serialize server responses and rendered generations.
class UI50000TransitionTests(unittest.TestCase):
    # Prove Bingo skips a true purchase-ready no-op and otherwise requires response-owned generation replacement. (TEST-092, issue #1052)
    def test_bingo_reset_confirmation_tracks_rendered_active_called_state(self):
        # Execute one browser-free rendered state and return its exact public interaction trace.
        async def run_scenario(buy_ready, call_ready, called_ball_count, emit_dialog=True, response_ok=True):
            events = []  # Record only actionability, dialog, response, detachment, and fresh-generation boundaries.

            class FakeHandle:  # Model the exact pre-reset Buy DOM generation.
                pass  # Identity alone is sufficient for the detachment predicate.

            class FakeLocator:  # Model one public Bingo locator collection.
                def __init__(self, selector):
                    self.selector = selector  # Preserve the public selector for deterministic readiness lookup.
                    self.first = self  # Match Playwright's first-locator interface.

                async def count(self):
                    events.append(f"count:{self.selector}")  # Record rendered called-ball inspection.
                    return called_ball_count  # Return the scenario's public call-history count.

                async def element_handle(self):
                    events.append(f"handle:{self.selector}")  # Capture the stale Buy generation before Reset.
                    return FakeHandle()  # Return one immutable old-node identity.

            class FakeDialog:  # Model the native destructive confirmation.
                type = "confirm"  # Expose the exact Playwright dialog type.

                async def accept(self):
                    events.append("dialog:accept")  # Record real confirmation before Reset completes.

            class FakeResponse:  # Model one exact reset response.
                ok = response_ok  # Preserve the scenario's accepted or rejected server boundary.

            class FakeResponseInfo:  # Model Playwright's async expect_response context.
                async def __aenter__(self):
                    events.append("response:armed")  # Require response observation before pointer dispatch.
                    return self  # Return the context-owned response future facade.

                async def __aexit__(self, *_args):
                    events.append("response:captured")  # Record request completion before replacement inspection.

                @property
                def value(self):
                    async def resolve():
                        return FakeResponse()  # Resolve the configured public response.
                    return resolve()  # Match Playwright's awaitable value property.

            class FakePage:  # Provide only the public browser seams owned by the helper.
                def __init__(self):
                    self.dialog_handler = None  # Start without leaked dialog authority.

                def locator(self, selector):
                    events.append(f"locator:{selector}")  # Record generation and state queries.
                    return FakeLocator(selector)  # Return one stable locator facade.

                def once(self, event_name, handler):
                    self.event_name = event_name  # Preserve the exact native event identity.
                    self.dialog_handler = handler  # Retain the one-shot callback until pointer dispatch.
                    events.append("dialog:registered")  # Record authority before the destructive click.

                def remove_listener(self, event_name, handler):
                    self.event_name = event_name  # Preserve the exact native event identity being revoked.
                    if self.dialog_handler is handler:  # Revoke only an unconsumed handler from this invocation.
                        self.dialog_handler = None  # Prevent authority from leaking to another dialog.
                    events.append("dialog:removed")  # Record deterministic cleanup on success and error paths.

                def expect_response(self, predicate, timeout):
                    events.append(("expect", timeout, predicate(type("Response", (), {"url": "http://test/api/v1/games/bingo/reset", "request": type("Request", (), {"method": "POST"})()})())))  # Prove the exact endpoint predicate and unchanged bound.
                    return FakeResponseInfo()  # Return the async observation context.

                async def wait_for_function(self, expression, arg, timeout):
                    events.append(("detached", "isConnected" in expression, isinstance(arg, FakeHandle), timeout))  # Require old-generation disconnection under the established deadline.

            page = FakePage()  # Create one isolated fake browser page.

            async def fake_locator_ready(locator):
                events.append(f"is-ready:{locator.selector}")  # Record readiness on Buy or Call.
                if locator.selector == '[data-testid="bingo-buy"]':  # Resolve the purchase-ready no-op state.
                    return buy_ready  # Return the scenario's fresh-card readiness.
                return call_ready  # Return active Call readiness for confirmation ownership.

            async def fake_click_control(_page, selector, _activated_counts, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
                events.append(f"click:{selector}")  # Record the real Reset pointer boundary.
                if page.dialog_handler is not None and emit_dialog:  # Emit only an explicitly authorized confirmation in the configured scenario.
                    handler = page.dialog_handler  # Capture the one-shot callback.
                    page.dialog_handler = None  # Consume it before callback execution.
                    await handler(FakeDialog())  # Require the destructive prompt to be accepted.

            async def fake_wait_any_enabled(_page, selectors, timeout_ms=ui_50000.ACTION_TIMEOUT_MS):
                events.append(f"wait:{'|'.join(selectors)}")  # Record authoritative actionability boundaries.
                return selectors[0]  # Model the first public selector becoming actionable.

            with mock.patch.object(ui_50000, "locator_ready", side_effect=fake_locator_ready), mock.patch.object(ui_50000, "click_control", side_effect=fake_click_control), mock.patch.object(ui_50000, "wait_any_enabled", side_effect=fake_wait_any_enabled):  # Isolate deterministic ordering from Playwright.
                try:  # Preserve mismatch and rejected-response evidence for explicit no-leak assertions.
                    result = await ui_50000.bingo_reset_to_purchase(page, Counter())  # Exercise the exact production helper.
                except AssertionError as exc:  # Capture only the expected fail-closed public mismatch.
                    result = exc  # Return the exact exception without weakening helper behavior.
            self.assertIsNone(page.dialog_handler)  # Reject confirmation authority leaking beyond this reset.
            return result, events, getattr(page, "event_name", None)  # Return the truthful action result and trace.

        no_op_result, no_op_events, event_name = asyncio.run(run_scenario(True, False, 0))  # Model the purchase-ready state that exposed the formal stale-node race.
        self.assertFalse(no_op_result)  # Require an exact no-op without a Reset activation.
        self.assertEqual(no_op_events, ['wait:[data-testid="bingo-buy"]|[data-testid="bingo-reset"]', 'locator:[data-testid="bingo-buy"]', 'is-ready:[data-testid="bingo-buy"]'])  # Forbid Reset, response, or generation work when Buy is already fresh.
        self.assertIsNone(event_name)  # Forbid dialog authority in the no-op path.
        reset_result, reset_events, event_name = asyncio.run(run_scenario(False, True, 1))  # Model one called active session requiring abandonment confirmation.
        self.assertTrue(reset_result)  # Require one real generation-replacing Reset.
        self.assertEqual(reset_events, ['wait:[data-testid="bingo-buy"]|[data-testid="bingo-reset"]', 'locator:[data-testid="bingo-buy"]', 'is-ready:[data-testid="bingo-buy"]', 'handle:[data-testid="bingo-buy"]', 'wait:[data-testid="bingo-reset"]', 'locator:[data-testid="bingo-call"]', 'locator:[data-testid="bingo-called-ball"]', 'is-ready:[data-testid="bingo-call"]', 'count:[data-testid="bingo-called-ball"]', 'dialog:registered', ("expect", ui_50000.ACTION_TIMEOUT_MS, True), 'response:armed', 'click:[data-testid="bingo-reset"]', 'dialog:accept', 'response:captured', 'dialog:removed', ("detached", True, True, ui_50000.ACTION_TIMEOUT_MS), 'wait:[data-testid="bingo-buy"]'])  # Pin response-before-click, listener cleanup, and old-detach-before-fresh readiness exactly.
        self.assertEqual(event_name, "dialog")  # Bind destructive authority only to the expected native event.
        safe_result, safe_events, event_name = asyncio.run(run_scenario(False, True, 0))  # Model a refundable uncalled active card.
        self.assertTrue(safe_result)  # Require the same exact response and replacement boundary.
        self.assertNotIn("dialog:registered", safe_events)  # Keep safe reset free of confirmation authority.
        self.assertIsNone(event_name)  # Prove no native event listener was installed.
        missing_result, missing_events, event_name = asyncio.run(run_scenario(False, True, 1, emit_dialog=False))  # Model an expected destructive prompt that never appears.
        self.assertIsInstance(missing_result, AssertionError)  # Fail closed instead of treating a missing prompt as acceptance.
        self.assertIn("confirmation mismatch", str(missing_result))  # Preserve the bounded public mismatch diagnostic.
        self.assertIn("dialog:removed", missing_events)  # Revoke unconsumed authority before raising.
        self.assertEqual(event_name, "dialog")  # Prove the revoked listener was scoped to the expected native event.
        rejected_result, rejected_events, event_name = asyncio.run(run_scenario(False, True, 1, response_ok=False))  # Model one explicit server rejection after real confirmation.
        self.assertIsInstance(rejected_result, AssertionError)  # Fail closed instead of inspecting a replacement after rejection.
        self.assertIn("reset request failed", str(rejected_result))  # Preserve the bounded rejected-response diagnostic.
        self.assertIn("dialog:removed", rejected_events)  # Revoke confirmation authority even when the response fails.
        self.assertFalse(any(isinstance(event, tuple) and event[0] == "detached" for event in rejected_events))  # Forbid generation acceptance after a rejected reset.
        self.assertNotIn('wait:[data-testid="bingo-buy"]', rejected_events[rejected_events.index("response:captured") + 1:])  # Forbid fresh-generation readiness after rejection.
        self.assertEqual(event_name, "dialog")  # Prove rejected-response cleanup revokes only the expected native event.


if __name__ == "__main__":
    unittest.main()  # Support direct focused execution during local diagnosis.
