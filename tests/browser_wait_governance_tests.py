# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound regressions for the Browser wait races found in issue #750."""

# Import paths for exact repository-source inspection.
from pathlib import Path
# Import environment copying for isolated wait-budget parser checks.
import os
# Import regular expressions for the one workflow-level wait override.
import re
# Import subprocess execution for fresh-process environment validation.
import subprocess
# Import the active interpreter for dependency-free timing-policy probes.
import sys
# Import standard dependency-free assertions.
import unittest

# Import the state-driven Bingo boundaries used by the real Browser runner.
from tests.browser_readiness import prepare_admin_feedback_draft, require_admin_feedback_draft_payload, require_admin_feedback_save_payload, require_bingo_terminal_auto_payload, require_bingo_terminal_reload_payload, save_admin_feedback_triage, wait_for_bingo_terminal_render


# Resolve the exact checkout independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Read the governed Browser implementation once for bounded source slices.
RUNNER_SOURCE = (ROOT / "tests" / "runner.py").read_text(encoding="utf-8")
# Read the extracted Roulette owner so its semantic wait remains source-governed after #727 delegation.
ROULETTE_OWNER_SOURCE = (ROOT / "tests" / "cases" / "browser" / "roulette_slots_keno.py").read_text(encoding="utf-8")
# Read the extracted Bingo/Admin owner for its state-driven reload and feedback-save gates.
BINGO_ADMIN_OWNER_SOURCE = (ROOT / "tests" / "cases" / "browser" / "bingo_admin.py").read_text(encoding="utf-8")
# Read the ordinary Browser workflow so its one environment override remains governed.
BROWSER_WORKFLOW_SOURCE = (ROOT / ".github" / "workflows" / "browser-tests.yml").read_text(encoding="utf-8")
# Name every runtime Browser owner that must consume the one shared wait budget.
BROWSER_RUNTIME_SOURCES = (
    ROOT / "tests" / "runner.py",
    ROOT / "tests" / "cases" / "browser" / "auth_backend_pwa.py",
    ROOT / "tests" / "cases" / "browser" / "auth_lobby.py",
    ROOT / "tests" / "cases" / "browser" / "bingo_admin.py",
    ROOT / "tests" / "cases" / "browser" / "guest_lifecycle.py",
    ROOT / "tests" / "cases" / "browser" / "roulette_slots_keno.py",
    ROOT / "tests" / "games" / "chuck_a_luck" / "browser_check.py",
)


# Prove Browser acceptance waits for authoritative state instead of elapsed time.
class BrowserWaitGovernanceTests(unittest.TestCase):
    # Prove one environment-scalable wait budget replaces every historical five/ten-second literal. (TEST-053)
    def test_browser_wait_budget_is_single_source_and_environment_scalable(self):
        # Read every Browser runtime owner without importing Playwright.
        sources = {path: path.read_text(encoding="utf-8") for path in BROWSER_RUNTIME_SOURCES}
        # Require every runtime owner to import the shared timing policy.
        self.assertTrue(all("from tests.browser_timing import WAIT_MS" in source for source in sources.values()))
        # Reject every historical duplicated wait literal from the complete governed tests tree.
        all_test_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "tests").rglob("*.py"))
        # Prove both duplicated budgets are absent from executable and source-bound evidence.
        self.assertNotIn("timeout=" + "5000", all_test_source)
        # Prove doubled waits also derive from the shared knob.
        self.assertNotIn("timeout=" + "10000", all_test_source)
        # Require at least one ordinary and one doubled wait so the policy cannot pass vacuously.
        self.assertTrue(any("timeout=WAIT_MS" in source for source in sources.values()))
        # Require long waits to scale with the same reviewed knob.
        self.assertTrue(any("timeout=WAIT_MS * 2" in source for source in sources.values()))
        # Require exactly one editable workflow-level decimal override without pinning its chosen value.
        self.assertEqual(len(re.findall(r"(?m)^  CASINO_BROWSER_WAIT_MS: [1-9][0-9]*$", BROWSER_WORKFLOW_SOURCE)), 1)
        # Build one clean subprocess environment with an explicit alternative CI budget.
        environment = dict(os.environ)
        # Change only the supported environment knob.
        environment["CASINO_BROWSER_WAIT_MS"] = "7500"
        # Resolve the shared constant in a fresh process so import caching cannot mask the override.
        configured = subprocess.run([sys.executable, "-c", "from tests.browser_timing import WAIT_MS; print(WAIT_MS)"], cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
        # Require the exact alternate millisecond value.
        self.assertEqual((configured.returncode, configured.stdout.strip()), (0, "7500"), configured.stderr)

    # Prove malformed or unsafe Browser wait overrides fail closed with one fixed diagnostic. (TEST-053)
    def test_browser_wait_budget_rejects_hostile_overrides(self):
        # Exercise syntax, Unicode, lower-bound, and upper-bound failures independently.
        for hostile_value in ("", "99", "60001", "+5000", " 5000", "1.5", "٥٠٠٠"):
            # Isolate each hostile override from the parent process.
            environment = dict(os.environ)
            # Install only the current hostile value.
            environment["CASINO_BROWSER_WAIT_MS"] = hostile_value
            # Import the timing policy in a fresh process and capture its fixed diagnostic.
            rejected = subprocess.run([sys.executable, "-c", "import tests.browser_timing"], cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
            # Require failure without reflecting the hostile value in the diagnostic.
            self.assertNotEqual(rejected.returncode, 0)
            # Require the stable value-free policy error.
            self.assertIn("browser wait budget is invalid", rejected.stderr)
            # Reject caller-controlled value reflection for nonempty hostile inputs.
            if hostile_value:
                # Keep CI logs free of untrusted knob content.
                self.assertNotIn(hostile_value, rejected.stderr)

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

    # Build one server-sanitized manual-only Admin feedback draft payload.
    @staticmethod
    def admin_feedback_payload(*, report_id="report_ready", publication_enabled=False):
        # Return the exact standard envelope exposed by the v2 Admin draft route.
        return {"ok": True, "data": {"draft": {"title": "[Bug] Draft readiness", "body": "Manual review body", "labels": ["P1", "bug"], "source_report_id": report_id, "publication_mode": "manual_only", "publication_enabled": publication_enabled}}}

    # Require every Roulette audit wager to complete before a later clear can overtake it.
    def test_roulette_hit_target_waits_for_wager_responses(self) -> None:
        # Slice only the named Roulette case so unrelated request assertions remain unconstrained.
        roulette_source = ROULETTE_OWNER_SOURCE.partition("def roulette_hit_target_integrity():")[2].partition("run_case('BR-ROU-HITMAP-001'")[0]
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
        bingo_source = BINGO_ADMIN_OWNER_SOURCE.partition("if table_games_owner:")[2].partition("# Seed one isolated deferred natural")[0]
        # Preserve the two permanent case ids and their exact existing requirement mappings.
        self.assertEqual(bingo_source.count("run_case('BR-BINGO-PURCHASE-001',['BINGO-012','BINGO-022','LEDGER-020','TEST-010','TEST-012']"), 1)
        # Preserve the premium terminal case identity and mapping byte-for-byte.
        self.assertEqual(bingo_source.count("run_case('BR-BINGO-001',['BINGO-017','BINGO-018','BINGO-021','BINGO-022','AUTO-013']"), 1)
        # Require explicit auto-response and reload-response validation around a lobby transition.
        self.assertIn("require_bingo_terminal_auto_payload(bingo_auto_payload)", bingo_source)
        # Require route ownership to leave Bingo before the state-response-observed remount.
        self.assertIn("page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)", bingo_source)
        # Bind the remount to the authoritative state response consumed by Bingo load().
        self.assertIn("page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/bingo/state')", bingo_source)
        # Require the complete terminal render helper after the exact-session reload check.
        self.assertIn("wait_for_bingo_terminal_render(page,bingo_reload_terminal)", bingo_source)
        # Reject the former same-route fixed winning-cell wait that flaked on shard zero.
        self.assertNotIn("page.get_by_test_id('nav-bingo').click(); page.locator('[data-winning-cell=\"true\"]').first.wait_for(timeout=WAIT_MS)", bingo_source)

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

    # Require every Admin feedback draft interaction to observe the exact authoritative POST.
    def test_admin_feedback_draft_uses_state_driven_readiness(self) -> None:
        # Slice only the named Admin feedback Browser function.
        feedback_source = BINGO_ADMIN_OWNER_SOURCE.partition("def admin_feedback_browser():")[2].partition("run_case('BR-ADMIN-FEEDBACK-001'")[0]
        # Preserve the permanent case id and its exact existing requirement mapping.
        self.assertEqual(BINGO_ADMIN_OWNER_SOURCE.count("run_case('BR-ADMIN-FEEDBACK-001',['ADMIN-025','I18N-005','UX-019','TEST-094']"), 1)
        # Require all three source call sites to use the response-backed helper.
        self.assertEqual(feedback_source.count("prepare_admin_feedback_draft(page,feedback_report_id)"), 3)
        # Require the preceding save to wait for its authoritative response and a replacement route generation.
        self.assertEqual(feedback_source.count("save_admin_feedback_triage(page,feedback_report_id,'P1','linked')"), 1)
        # Require the report identity to come from the exact opened list row.
        self.assertIn("feedback_report_id=report_button.get_attribute('data-feedback-id')", feedback_source)
        # Reject every former single-locator readiness assumption from this case.
        self.assertNotIn("page.locator('#feedback-draft').click(); page.locator('#feedback-github-draft:not([hidden])').wait_for(timeout=WAIT_MS)", feedback_source)

    # Prove the save boundary rejects the already-visible detail until its replacement renders.
    def test_admin_feedback_save_waits_for_replacement_generation(self) -> None:
        # Model deterministic monotonic time across the response and rerender boundary.
        class Clock:
            # Start from a stable zero point.
            value = 0.0

            # Return the current fake monotonic value.
            def __call__(self):
                # Avoid consulting wall-clock time in the focused test.
                return self.value

        # Model the request metadata consumed by the exact response predicate.
        class Request:
            # Publish the documented mutation method.
            method = "PATCH"

        # Model the authoritative updated-report response.
        class Response:
            # Bind request metadata used by the predicate.
            request = Request()
            # Bind the exact governed endpoint.
            url = "http://127.0.0.1/api/v2/admin/feedback/reports/report_ready"

            # Return one canonical committed triage payload.
            @staticmethod
            def json():
                # Publish only the response fields required by the save boundary.
                return {"ok": True, "data": {"report": {"report_id": "report_ready", "priority": "P1", "status": "linked"}}}

        # Model response completion while leaving the old detail generation mounted.
        class ResponseContext:
            # Retain the response and shared clock.
            def __init__(self, clock):
                # Publish the response through Playwright's value interface.
                self.value = Response()
                # Bind the deterministic response clock.
                self.clock = clock

            # Enter the response boundary before the click.
            def __enter__(self):
                # Return this context for parity with Playwright.
                return self

            # Complete the response before the delayed detail fetch replaces the DOM.
            def __exit__(self, _kind, _error, _traceback):
                # Consume part of the single total readiness budget.
                self.clock.value += 0.2

        # Model the already-mounted detail element marked by the helper.
        class DetailLocator:
            # Retain the owning fake page.
            def __init__(self, page):
                # Bind route-generation state to the locator.
                self.page = page

            # Apply the helper's private generation marker.
            def evaluate(self, _source, marker):
                # Mark only the old detail generation.
                self.page.old_marker = marker

        # Model the real Admin save control.
        class SaveLocator:
            # Retain click accounting.
            clicks = 0

            # Dispatch one synthetic save click.
            def click(self):
                # Prove the production save control is activated exactly once.
                self.clicks += 1

        # Model an old visible detail followed by one replacement generation.
        class Page:
            # Bind deterministic state used by every helper seam.
            def __init__(self, clock):
                # Retain the shared clock.
                self.clock = clock
                # Retain the response timeout for total-budget proof.
                self.response_timeout = None
                # Retain the old-generation marker assigned by the helper.
                self.old_marker = None
                # Keep the old generation mounted through the first semantic observation.
                self.replaced = False
                # Retain one shared save control.
                self.control = SaveLocator()
                # Retain bounded semantic yields.
                self.waits = []

            # Resolve only the governed feedback detail test id.
            def get_by_test_id(self, test_id):
                # Reject unexpected locator drift in the helper.
                assert test_id == "admin-feedback-detail"
                # Return the marker-capable old generation.
                return DetailLocator(self)

            # Enter the exact PATCH response boundary.
            def expect_response(self, predicate, timeout):
                # Retain the original total response budget.
                self.response_timeout = timeout
                # Require the synthetic authoritative response to match the production predicate.
                assert predicate(Response())
                # Return the delayed response context.
                return ResponseContext(self.clock)

            # Resolve only the production save control.
            def locator(self, selector):
                # Reject unexpected selector drift in the helper.
                assert selector == "#feedback-save"
                # Return the shared save control.
                return self.control

            # Return the current route generation and committed control state.
            def evaluate(self, _source, expected):
                # Require the semantic observation to stay bound to the exact old marker.
                assert expected["marker"] == self.old_marker
                # Publish exact controls while distinguishing old versus replacement ownership.
                return {"visible": True, "replaced": self.replaced, "priority": "P1", "status": "linked"}

            # Advance to the response-driven replacement after one bounded poll.
            def wait_for_timeout(self, milliseconds):
                # Retain exact polling behavior.
                self.waits.append(milliseconds)
                # Advance the fake clock without sleeping.
                self.clock.value += milliseconds / 1000
                # Replace the old detail generation after yielding once.
                self.replaced = True

        # Build the fake page and deterministic clock.
        clock = Clock(); page = Page(clock)
        # Exercise the complete save-response-plus-replacement helper under one second.
        result = save_admin_feedback_triage(page, "report_ready", "P1", "linked", timeout_seconds=1, clock=clock)
        # Require one click, the original response budget, one poll, and replacement ownership.
        self.assertEqual((page.control.clicks, page.response_timeout, page.waits, result["replaced"]), (1, 1000, [50], True))

    # Prove delayed response generation and delayed rendering share one bounded deadline.
    def test_admin_feedback_draft_waits_for_response_and_complete_render(self) -> None:
        # Model deterministic monotonic time advanced by response and render delays.
        class Clock:
            # Start from a stable zero point.
            value = 0.0

            # Return the current fake monotonic value.
            def __call__(self):
                # Avoid consulting wall-clock time in the focused test.
                return self.value

        # Model the request metadata consumed by the exact response predicate.
        class Request:
            # Publish the documented mutation method.
            method = "POST"

        # Model the standard response object returned by Playwright.
        class Response:
            # Bind request metadata used by the predicate.
            request = Request()
            # Bind the exact governed endpoint.
            url = "http://127.0.0.1/api/v2/admin/feedback/reports/report_ready/github-draft"

            # Return one authoritative server payload.
            @staticmethod
            def json():
                # Reuse the focused fixture through its enclosing test instance.
                return BrowserWaitGovernanceTests.admin_feedback_payload()

        # Model the response context that waits for generation after the click.
        class ResponseContext:
            # Retain the response and fake clock.
            def __init__(self, clock):
                # Publish the response through Playwright's value interface.
                self.value = Response()
                # Bind the clock advanced when response generation completes.
                self.clock = clock

            # Enter the response boundary before the click.
            def __enter__(self):
                # Return this context for parity with Playwright.
                return self

            # Complete the response after a deterministic generation delay.
            def __exit__(self, _kind, _error, _traceback):
                # Consume part of the single total readiness budget.
                self.clock.value += 0.2

        # Model the manual-draft button clicked by the helper.
        class Locator:
            # Retain click accounting.
            clicks = 0

            # Dispatch one synthetic click.
            def click(self):
                # Prove the production control is activated exactly once.
                self.clicks += 1

        # Model incomplete and complete DOM projections after the response.
        class Page:
            # Bind deterministic state used by every helper seam.
            def __init__(self, clock):
                # Retain the shared clock.
                self.clock = clock
                # Retain the exact response timeout for budget assertions.
                self.response_timeout = None
                # Retain one shared manual-draft control.
                self.control = Locator()
                # Queue an incomplete surface followed by the exact server-backed render.
                self.snapshots = [{"visible": True, "title": "[Bug] Draft readiness", "body": None, "copyVisible": False, "externalCount": 0}, {"visible": True, "title": "[Bug] Draft readiness", "body": "Manual review body", "copyVisible": True, "externalCount": 0}]
                # Retain bounded semantic yields.
                self.waits = []

            # Enter an exact response boundary and prove its predicate matches.
            def expect_response(self, predicate, timeout):
                # Retain the original total response budget.
                self.response_timeout = timeout
                # Require the synthetic authoritative response to match the production predicate.
                assert predicate(Response())
                # Return the delayed response context.
                return ResponseContext(self.clock)

            # Resolve only the production manual-draft control.
            def locator(self, selector):
                # Reject unexpected selector drift in the helper.
                assert selector == "#feedback-draft"
                # Return the shared control.
                return self.control

            # Return the next semantic DOM snapshot.
            def evaluate(self, _source):
                # Preserve the complete snapshot after readiness.
                return self.snapshots.pop(0) if len(self.snapshots) > 1 else self.snapshots[0]

            # Advance deterministic time for one bounded render poll.
            def wait_for_timeout(self, milliseconds):
                # Retain exact polling behavior.
                self.waits.append(milliseconds)
                # Advance the fake clock without sleeping.
                self.clock.value += milliseconds / 1000

        # Build the fake page and deterministic clock.
        clock = Clock(); page = Page(clock)
        # Exercise the complete response-plus-render helper under one second.
        result = prepare_admin_feedback_draft(page, "report_ready", timeout_seconds=1, clock=clock)
        # Require one click, the original response budget, one semantic poll, and exact accepted body.
        self.assertEqual((page.control.clicks, page.response_timeout, page.waits, result["body"]), (1, 1000, [50], "Manual review body"))

    # Require malformed, failed, or publication-enabled responses to fail closed.
    def test_admin_feedback_draft_payload_fails_closed(self) -> None:
        # Reject an unsuccessful standard envelope with a stable response-bound diagnostic.
        with self.assertRaisesRegex(AssertionError, "not a successful standard envelope"):
            # Supply the documented failed-envelope shape.
            require_admin_feedback_draft_payload({"ok": False, "error": {"message": "failed"}}, "report_ready")
        # Reject a response for a different report identity.
        with self.assertRaisesRegex(AssertionError, "report identity mismatch"):
            # Bind otherwise valid draft content to a stale report.
            require_admin_feedback_draft_payload(self.admin_feedback_payload(report_id="report_stale"), "report_ready")
        # Reject any server response that enables external publication.
        with self.assertRaisesRegex(AssertionError, "manual-only publication"):
            # Flip only the prohibited publication capability.
            require_admin_feedback_draft_payload(self.admin_feedback_payload(publication_enabled=True), "report_ready")
        # Reject missing review content before DOM polling.
        with self.assertRaisesRegex(AssertionError, "title or body was missing"):
            # Remove only the authoritative response body.
            payload = self.admin_feedback_payload(); payload["data"]["draft"]["body"] = ""
            # Validate the incomplete server response.
            require_admin_feedback_draft_payload(payload, "report_ready")
        # Reject a stale or partially committed triage response before draft preparation.
        with self.assertRaisesRegex(AssertionError, "triage mismatch"):
            # Build one canonical save envelope with the old priority.
            save_payload = {"ok": True, "data": {"report": {"report_id": "report_ready", "priority": "P2", "status": "linked"}}}
            # Require the exact P1 transition requested by the Browser case.
            require_admin_feedback_save_payload(save_payload, "report_ready", "P1", "linked")


# Support direct focused execution during local and hosted diagnosis.
if __name__ == "__main__":
    # Run the dependency-free source-bound suite.
    unittest.main()
