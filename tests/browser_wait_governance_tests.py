# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound regressions for the Browser wait races found in issue #750."""

# Import JSON parsing for the bounded shared-application failure bundle.
import json
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
# Import disposable directories for first-failure writer adversarial proofs.
import tempfile
# Import standard dependency-free assertions.
import unittest

# Import the state-driven Bingo boundaries used by the real Browser runner.
from tests.browser_readiness import SHARED_APP_DIAGNOSTIC_BYTE_LIMIT, SHARED_APP_PWA_STATES, install_shared_app_readiness_probe, persist_shared_app_first_failure, prepare_admin_feedback_draft, reload_and_wait_for_shared_app_readiness, require_admin_feedback_draft_payload, require_admin_feedback_save_payload, require_bingo_terminal_auto_payload, require_bingo_terminal_reload_payload, sanitize_shared_app_failure_snapshot, save_admin_feedback_triage, wait_for_bingo_terminal_render, wait_for_shared_app_readiness


# Resolve the exact checkout independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Read the governed Browser implementation once for bounded source slices.
RUNNER_SOURCE = (ROOT / "tests" / "runner.py").read_text(encoding="utf-8")
# Read the extracted Roulette owner so its semantic wait remains source-governed after #727 delegation.
ROULETTE_OWNER_SOURCE = (ROOT / "tests" / "cases" / "browser" / "roulette_slots_keno.py").read_text(encoding="utf-8")
# Read the extracted Bingo/Admin owner for its state-driven reload and feedback-save gates.
BINGO_ADMIN_OWNER_SOURCE = (ROOT / "tests" / "cases" / "browser" / "bingo_admin.py").read_text(encoding="utf-8")
# Read the production service worker so diagnostic cache classification cannot drift from its prefix.
SERVICE_WORKER_SOURCE = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
# Read the production PWA controller so the diagnostic state enum cannot drift.
PWA_SOURCE = (ROOT / "web" / "core" / "pwa.js").read_text(encoding="utf-8")
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

    # Require the Slots restoration cell to observe shared bootstrap before its independent module wait. (TEST-053)
    def test_slots_route_restored_waits_for_shared_application_signal(self) -> None:
        # Slice only the persisted-state loop that owns the exact route-restored reload.
        slots_source = ROULETTE_OWNER_SOURCE.partition("for state_name,prepared_state in persisted_states.items():")[2].partition("# Switch through the visible locale control")[0]
        # Require the pre-document listener before the helper that owns exact network-idle reload.
        self.assertLess(slots_source.index("install_shared_app_readiness_probe(page)"), slots_source.index("reload_and_wait_for_shared_app_readiness(page,timeout_ms=WAIT_MS)"))
        # Require the shared reload-plus-signal gate before the independent module-owned selector gate.
        self.assertLess(slots_source.index("reload_and_wait_for_shared_app_readiness(page,timeout_ms=WAIT_MS)"), slots_source.index("page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)"))
        # Require one case-owned bounded failure artifact and a bare rethrow of the original exception.
        self.assertIn("persist_shared_app_first_failure(page,screenshots/'before-failure-slots-route-restored-shared-app.json',failure=error)", slots_source)
        # Reject retry, fallback, trace, or exception-text capture from this exact readiness block.
        route_block = slots_source.partition("if state_name=='route_restored':")[2].partition("else:")[0]
        # Preserve the bare rethrow while rejecting behavior that could hide the first failure.
        self.assertIn("\n                                raise\n", route_block)
        # Keep the route-restored boundary free of any alternate navigation or retry path.
        self.assertFalse(any(term in route_block.lower() for term in ("retry", "fallback", "traceback", "event.detail")))

    # Require live Chromium proofs to stay inside the existing Browser-only Slots owner. (TEST-053)
    def test_shared_application_live_proofs_are_browser_lane_only(self) -> None:
        # Require the disposable proof to be owned by the existing Browser case module.
        self.assertIn("def shared_app_readiness_browser_proof():", ROULETTE_OWNER_SOURCE)
        # Require ready, error, and delayed-navigation paths in that Browser-only proof.
        self.assertTrue(all(token in ROULETTE_OWNER_SOURCE for token in ("shared-ready.test/ready", "shared-ready.test/error", "shared-ready.test/late")))
        # Require unresolved cache and service-worker promises plus bounded capture evidence.
        self.assertTrue(all(token in ROULETTE_OWNER_SOURCE for token in ("keys:()=>new Promise(()=>{})", "getRegistrations:()=>new Promise(()=>{})", "capture_elapsed<2.0", "captured is original")))
        # Require compatibility with the runner-owned Browser.new_page convenience context.
        self.assertIn("proof_page=page", ROULETTE_OWNER_SOURCE); self.assertNotIn("page.context.new_page()", ROULETTE_OWNER_SOURCE)
        # Require both synthetic routes and disposable document overrides to be removed by canonical restoration.
        self.assertGreaterEqual(ROULETTE_OWNER_SOURCE.count("goto(base+'/games/slots',wait_until='networkidle')"), 2)
        # Require the existing permanent Slots case to invoke the proof without a new inventory row.
        self.assertLess(ROULETTE_OWNER_SOURCE.index("shared_app_readiness_browser_proof()", ROULETTE_OWNER_SOURCE.index("def slots_economics_and_presentation():")), ROULETTE_OWNER_SOURCE.index("slots_economics_visual_matrix()", ROULETTE_OWNER_SOURCE.index("def slots_economics_and_presentation():")))
        # Keep the API governance module free of Playwright imports and browser launches.
        governance_source = Path(__file__).read_text(encoding="utf-8").lower()
        # Reject both synchronous and asynchronous Playwright entry points.
        self.assertNotIn("from " + "playwright", governance_source); self.assertNotIn("sync_" + "playwright", governance_source)

    # Prove the init script observes only fixed terminal events without retaining event payloads. (TEST-053)
    def test_shared_application_probe_is_pre_document_and_payload_free(self) -> None:
        # Model the Playwright init-script registration seam.
        class Page:
            # Retain the one script installed for the next document.
            script = None

            # Record the pre-document script without executing Browser code locally.
            def add_init_script(self, script):
                # Preserve the exact script for source assertions.
                self.script = script

        # Install the governed listener through the production helper.
        page = Page(); install_shared_app_readiness_probe(page)
        # Require both governed terminal events and the private marker.
        self.assertIn("casino:shared-app-ready", page.script)
        # Require the error signal to share the same pre-document listener boundary.
        self.assertIn("casino:shared-app-error", page.script)
        # Require a non-enumerable marker rather than storage-backed or document-visible state.
        self.assertIn("__casinoSharedAppReadinessProbe", page.script)
        # Reject raw event details, names, and messages from the marker implementation.
        self.assertNotIn("event.detail", page.script)
        # Reject any event-message retention path.
        self.assertNotIn(".message", page.script)
        # Reject any event-name retention path.
        self.assertNotIn(".name", page.script)

    # Prove the registered source is an invoked program rather than an inert function value. (TEST-053)
    def test_shared_application_probe_source_is_invoked(self) -> None:
        # Model only Playwright's init-script registration seam for structural inspection.
        class Page:
            # Retain the exact registered source.
            script = None

            # Capture one source program without altering it.
            def add_init_script(self, script):
                # Preserve byte identity for the invoked-wrapper assertion.
                self.script = script

        # Register the production init source.
        page = Page(); install_shared_app_readiness_probe(page)
        # Require a complete invoked IIFE wrapper, not merely an arrow-function expression.
        self.assertIsNotNone(re.fullmatch(r"\(\(\) => \{.*\}\)\(\);", page.script, flags=re.DOTALL))

    # Prove reload and terminal observation consume one shared remaining budget without Chromium. (TEST-053)
    def test_shared_application_reload_and_terminal_share_one_deadline(self) -> None:
        # Model a monotonic clock that consumes 100ms before reload and 300ms during navigation.
        class Clock:
            # Retain deterministic current monotonic time.
            current = 0.0
            # Count calls so the pre-reload budget computation consumes its fixed setup interval.
            calls = 0

            # Return the next deterministic monotonic value.
            def __call__(self):
                # Advance only before the helper computes reload's remaining budget.
                self.calls += 1
                # Consume 100ms between deadline creation and reload timeout selection.
                if self.calls == 2: self.current = 0.1
                # Return the deterministic monotonic point.
                return self.current

        # Model the two Playwright seams used by the production helper.
        class Page:
            # Retain the fake clock and observed timeouts.
            def __init__(self, clock):
                # Bind shared deterministic time.
                self.clock = clock
                # Retain reload and terminal timeout values.
                self.reload_timeout = None; self.terminal_timeout = None

            # Consume 300ms of the original deadline during navigation.
            def reload(self, *, wait_until, timeout):
                # Require the exact network-idle route boundary.
                assert wait_until == "networkidle"
                # Retain only the 900ms remainder, not a fresh 1000ms.
                self.reload_timeout = timeout
                # Advance deterministic time through navigation.
                self.clock.current = 0.4

            # Retain the terminal wait's still-smaller remaining budget.
            def wait_for_function(self, _source, *, timeout):
                # Record only the helper-provided remainder.
                self.terminal_timeout = timeout

            # Return the fixed successful marker after semantic readiness.
            def evaluate(self, _source):
                # Publish only the governed ready state.
                return {"status": "ready", "milestone": "shared_app_ready"}

        # Exercise the production deadline helper with one deterministic second.
        clock = Clock(); page = Page(clock); marker = reload_and_wait_for_shared_app_readiness(page, timeout_ms=1000, clock=clock)
        # Require decreasing shared remainders and the exact terminal marker.
        self.assertEqual((page.reload_timeout, page.terminal_timeout, marker), (900, 600, {"status": "ready", "milestone": "shared_app_ready"}))

    # Prove ready passes while error and timeout both fail closed within the supplied budget. (TEST-053)
    def test_shared_application_wait_accepts_only_ready(self) -> None:
        # Model one terminal marker returned after Playwright's bounded wait.
        class Page:
            # Bind the fixed marker returned after the semantic wait.
            def __init__(self, marker, wait_error=None):
                # Retain only the marker and optional transport failure.
                self.marker, self.wait_error = marker, wait_error
                # Record the exact caller-supplied timeout.
                self.timeout = None

            # Resolve the semantic wait or raise the configured transport failure.
            def wait_for_function(self, _source, timeout):
                # Preserve the unchanged WAIT_MS value for assertion.
                self.timeout = timeout
                # Raise only when this fixture models timeout.
                if self.wait_error is not None:
                    # Preserve the hostile transport detail only inside the cause.
                    raise self.wait_error

            # Return the already-sanitized terminal marker.
            def evaluate(self, _source):
                # Publish only the configured allowlisted marker.
                return dict(self.marker)

        # Accept exactly the governed ready milestone under the supplied budget.
        ready_page = Page({"status": "ready", "milestone": "shared_app_ready"})
        # Require the accepted marker and exact unchanged timeout.
        self.assertEqual((wait_for_shared_app_readiness(ready_page, timeout_ms=4321), ready_page.timeout), ({"status": "ready", "milestone": "shared_app_ready"}, 4321))
        # Reject the governed error event without reflecting arbitrary page content.
        with self.assertRaisesRegex(AssertionError, "terminal error signal"):
            # Supply the allowlisted error marker.
            wait_for_shared_app_readiness(Page({"status": "error", "milestone": "shared_app_error"}), timeout_ms=4321)
        # Reject timeout with one stable value-free public diagnostic.
        with self.assertRaisesRegex(AssertionError, "did not arrive within WAIT_MS") as captured:
            # Supply a hostile underlying error to prove it does not become the public message.
            wait_for_shared_app_readiness(Page({}, RuntimeError("secret@example.test token=top-secret")), timeout_ms=4321)
        # Prove the stable error does not reflect the hostile timeout detail.
        self.assertNotIn("secret@example.test", str(captured.exception))

    # Prove first-failure evidence is bounded and strips secrets, PII, raw cache keys, and worker URLs. (TEST-053)
    def test_shared_application_failure_bundle_is_sanitized_and_bounded(self) -> None:
        # Build one hostile page snapshot containing unbounded arrays and private-looking values.
        hostile_snapshot = {"readiness": {"status": "secret@example.test", "milestone": "token=top-secret", "message": "private"}, "document": {"readyState": "complete", "slotsRootCount": 999999, "path": "C:/Users/private"}, "caches": {"count": 999999, "classes": ["casino_shell", "other"] * 100, "keys": ["token=top-secret"] * 100}, "serviceWorkers": {"count": 999999, "registrations": [{"scopeClass": "https://secret.example/private", "scriptClass": "token=top-secret", "state": "private", "scriptURL": "https://secret.example/sw.js?token=top-secret"}] * 100}}
        # Model the single Browser evaluate call used by the evidence helper.
        class Page:
            # Return a detached hostile snapshot so sanitizer behavior cannot mutate the fixture.
            def evaluate(self, _source):
                # Clone through JSON to preserve only ordinary data shapes.
                return json.loads(json.dumps(hostile_snapshot))

        # Create one disposable artifact target for the first-write and no-overwrite assertions.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve the fixed test-local evidence path.
            target = Path(directory) / "first-failure.json"
            # Build one page carrying an oversized request inventory with one hostile raw-looking row.
            page = Page(); page._casino_shared_app_diagnostic_context = {"requests": [{"method": "GET", "path": "/api/v1/games/slots/state", "status": 200, "failure": None, "from_service_worker": False, "relative_ms": 12}] * 100 + [{"method": "TOKEN", "path": "/private?email=secret@example.test", "status": 999999, "failure": "token=top-secret", "from_service_worker": "yes", "relative_ms": 999999}], "capture_failures": {"request_capture", "token=top-secret"}}
            # Persist the first sanitized bundle successfully.
            self.assertTrue(persist_shared_app_first_failure(page, target))
            # Read the exact bytes for size and forbidden-content assertions.
            encoded = target.read_text(encoding="utf-8")
            # Parse the deterministic JSON bundle for structural assertions.
            payload = json.loads(encoded)
            # Require the complete encoded artifact to remain within the governed byte budget.
            self.assertLessEqual(len(encoded.encode("utf-8")), SHARED_APP_DIAGNOSTIC_BYTE_LIMIT)
            # Reject secrets, PII, private paths, raw cache keys, scopes, and script URLs.
            self.assertFalse(any(value in encoded for value in ("secret@example.test", "top-secret", "C:/Users", "https://secret.example", "scriptURL", "keys")))
            # Require hostile counts and repeated inventories to be strictly capped.
            self.assertEqual((payload["document"]["slots_root_count"], payload["caches"]["count"], payload["service_workers"]["count"]), (32, 32, 32))
            # Require at most eight cache classes and service-worker rows.
            self.assertLessEqual(len(payload["caches"]["key_classes"]), 8)
            # Require at most eight sanitized worker rows with only fixed classifications.
            self.assertLessEqual(len(payload["service_workers"]["registrations"]), 8)
            # Require at most 32 source-allowlisted request rows with no query or hostile outcome text.
            self.assertEqual((len(payload["requests"]), {row["path"] for row in payload["requests"]}), (32, {"/api/v1/games/slots/state"}))
            # Require only the fixed request capture-stage class to survive.
            self.assertEqual(payload["capture_failures"], ["request_capture"])
            # Preserve the immutable first bundle when the helper is called again.
            first_bytes = encoded
            # Reject a second write to the same case-owned target.
            self.assertFalse(persist_shared_app_first_failure(Page(), target))
            # Require the first bundle to remain byte-identical.
            self.assertEqual(target.read_text(encoding="utf-8"), first_bytes)

    # Prove cache diagnostics classify only the exact production-owned static-shell prefix. (TEST-053)
    def test_shared_application_failure_cache_class_matches_production(self) -> None:
        # Capture the in-document diagnostic program while returning one harmless fixed snapshot.
        class Page:
            # Retain the exact Browser evaluation source.
            source = None

            # Capture source and return the smallest valid diagnostic object.
            def evaluate(self, source):
                # Preserve the classifier program for production-source comparison.
                self.source = source
                # Avoid introducing raw cache or service-worker values.
                return {"caches": {"classes": []}, "serviceWorkers": {"registrations": []}}

        # Exercise the real persistence seam against one disposable path.
        with tempfile.TemporaryDirectory() as directory:
            # Build the capture page and one fixed evidence target.
            page = Page(); target = Path(directory) / "cache-classifier.json"
            # Require capture and bounded atomic persistence to complete.
            self.assertTrue(persist_shared_app_first_failure(page, target))
        # Pin production ownership to the exact prefix consumed by the service worker.
        self.assertIn("const CACHE_PREFIX = 'casino-static-shell-v';", SERVICE_WORKER_SOURCE)
        # Require diagnostics to use that exact production prefix.
        self.assertIn("startsWith('casino-static-shell-v')", page.source)
        # Reject the previously mismatched classifier.
        self.assertNotIn("startsWith('casino-shell-')", page.source)

    # Prove diagnostic PWA states exactly mirror production's externally observable enum. (TEST-053)
    def test_shared_application_failure_pwa_states_match_production(self) -> None:
        # Capture the in-document diagnostic program while returning one harmless fixed snapshot.
        class Page:
            # Retain the exact Browser evaluation source.
            source = None

            # Capture source and return the smallest valid diagnostic object.
            def evaluate(self, source):
                # Preserve the classifier program for production-source comparison.
                self.source = source
                # Avoid introducing arbitrary PWA or Browser values.
                return {"pwa": {"present": True, "state": "cold-start"}, "caches": {"classes": []}, "serviceWorkers": {"registrations": []}}

        # Parse the exact production DISPLAY_STATES declaration.
        production_match = re.search(r"const DISPLAY_STATES = new Set\(\[([^\]]+)\]\);", PWA_SOURCE)
        # Require the declaration to remain source-readable.
        self.assertIsNotNone(production_match)
        # Extract only quoted fixed state tokens from production source.
        production_states = frozenset(re.findall(r"'([^']+)'", production_match.group(1)))
        # Require the Python sanitizer to mirror production exactly.
        self.assertEqual(SHARED_APP_PWA_STATES, production_states)
        # Exercise real diagnostic-source construction against a disposable target.
        with tempfile.TemporaryDirectory() as directory:
            # Build the capture page and one fixed evidence target.
            page = Page(); target = Path(directory) / "pwa-classifier.json"
            # Require bounded atomic publication to complete.
            self.assertTrue(persist_shared_app_first_failure(page, target))
        # Parse the JavaScript allowlist embedded in the Browser capture program.
        diagnostic_match = re.search(r"pwaState=\[([^\]]+)\]\.includes", page.source)
        # Require the diagnostic state declaration to remain source-readable.
        self.assertIsNotNone(diagnostic_match)
        # Require Browser capture to mirror the same exact production set.
        self.assertEqual(frozenset(re.findall(r"'([^']+)'", diagnostic_match.group(1))), production_states)

    # Prove diagnostic capture, encoding, and writing can never replace the original Browser exception. (TEST-053)
    def test_shared_application_failure_bundle_is_best_effort(self) -> None:
        # Model a hostile Browser capture failure.
        class CaptureFailurePage:
            # Fail before any Browser-owned value reaches the serializer.
            def evaluate(self, _source):
                # Raise one private-looking diagnostic failure.
                raise RuntimeError("secret@example.test capture failed")

        # Model one harmless snapshot for encoder and writer failures.
        class Page:
            # Return the smallest valid diagnostic shape.
            def evaluate(self, _source):
                # Publish one allowlisted terminal error marker.
                return {"readiness": {"status": "error", "milestone": "shared_app_error"}}

        # Reject encoder invocation by raising before any bytes exist.
        def failing_encoder(*_args, **_kwargs):
            # Model an encoder implementation failure.
            raise RuntimeError("encoder failed")

        # Reject writer invocation after bounded encoding.
        def failing_writer(_path, _encoded):
            # Model a filesystem write failure.
            raise RuntimeError("writer failed")

        # Exercise every diagnostics-only failure against a disposable target.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve three independent evidence paths so existence cannot short-circuit later seams.
            capture_target = Path(directory) / "capture.json"; encoder_target = Path(directory) / "encoder.json"; writer_target = Path(directory) / "writer.json"
            # Require capture failure to publish one fixed-schema capture-stage artifact rather than raise.
            self.assertTrue(persist_shared_app_first_failure(CaptureFailurePage(), capture_target))
            # Require the artifact to retain only the fixed browser-capture failure enum.
            self.assertIn("browser_snapshot", json.loads(capture_target.read_text(encoding="utf-8"))["capture_failures"])
            # Require encoder failure to return false rather than raising.
            self.assertFalse(persist_shared_app_first_failure(Page(), encoder_target, encoder=failing_encoder))
            # Require writer failure to return false rather than raising.
            self.assertFalse(persist_shared_app_first_failure(Page(), writer_target, writer=failing_writer))
            # Freeze one exact original exception identity for the bare-rethrow proof.
            original = RuntimeError("original route readiness failure")
            # Model the case's diagnostics-only exception handler.
            def reraises_original():
                try:
                    # Raise the original route failure before evidence capture.
                    raise original
                except RuntimeError as error:
                    # Let the best-effort writer fail without escaping.
                    persist_shared_app_first_failure(Page(), writer_target, failure=error, writer=failing_writer)
                    # Preserve the exact original exception object.
                    raise
            # Capture the rethrown exception for identity comparison.
            with self.assertRaises(RuntimeError) as captured:
                # Exercise the bare-rethrow path.
                reraises_original()
            # Require diagnostics failure to preserve the exact original exception object.
            self.assertIs(captured.exception, original)

    # Prove atomic publication replaces poison, preserves first valid, and cleans failed temps. (TEST-053)
    def test_shared_application_failure_bundle_is_atomic_first_valid(self) -> None:
        # Model one harmless fixed Browser snapshot for every filesystem path.
        class Page:
            # Return only allowlisted terminal and bounded inventory facts.
            def evaluate(self, _source):
                # Publish a complete ready marker without raw Browser values.
                return {"readiness": {"status": "error", "milestone": "shared_app_error", "milestones": [{"name": "listener_installed", "relativeMs": 0}, {"name": "shared_app_error", "relativeMs": 12}]}, "document": {"readyState": "complete", "slotsRootCount": 0}, "caches": {"count": 0, "classes": []}, "serviceWorkers": {"count": 0, "registrations": []}}

        # Model one durability-stage failure.
        def failing_fsync(_descriptor):
            # Raise without exposing any filesystem data.
            raise OSError("fsync failed")

        # Model one atomic replacement-stage failure.
        def failing_replace(_source, _target):
            # Raise without mutating the final target.
            raise OSError("replace failed")

        # Exercise independent publication states inside one disposable directory.
        with tempfile.TemporaryDirectory() as directory:
            # Resolve independent targets for success and each failure stage.
            root = Path(directory); target = root / "first.json"; fsync_target = root / "fsync.json"; replace_target = root / "replace.json"
            # Seed a partial invalid target that must not poison capture.
            target.write_text("{", encoding="utf-8")
            # Require one valid atomic artifact to replace the partial target.
            self.assertTrue(persist_shared_app_first_failure(Page(), target))
            # Retain the complete first-valid bytes for preservation proof.
            valid_bytes = target.read_bytes()
            # Require the first complete current-source artifact to win unchanged.
            self.assertFalse(persist_shared_app_first_failure(Page(), target)); self.assertEqual(target.read_bytes(), valid_bytes)
            # Require fsync failure to publish nothing.
            self.assertFalse(persist_shared_app_first_failure(Page(), fsync_target, fsyncer=failing_fsync)); self.assertFalse(fsync_target.exists())
            # Require replace failure to publish nothing.
            self.assertFalse(persist_shared_app_first_failure(Page(), replace_target, replacer=failing_replace)); self.assertFalse(replace_target.exists())
            # Require every unpublished unique same-directory temp to be cleaned.
            self.assertEqual(list(root.glob(".*.tmp")), [])

    # Prove pure sanitization rejects arbitrary top-level values without Browser access. (TEST-053)
    def test_shared_application_snapshot_sanitizer_fails_closed(self) -> None:
        # Sanitize a wholly malformed object containing private-looking text.
        payload = sanitize_shared_app_failure_snapshot({"readiness": "secret@example.test", "serviceWorkers": ["token=top-secret"]})
        # Require fixed unavailable classifications and empty bounded inventories.
        self.assertEqual((payload["bootstrap"]["status"], payload["bootstrap"]["milestone"], payload["service_workers"]["registrations"]), ("unavailable", "diagnostic_unavailable", []))

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
        # Preserve the premium terminal case identity and its lifecycle-expanded mapping byte-for-byte.
        self.assertEqual(bingo_source.count("run_case('BR-BINGO-001',['BINGO-017','BINGO-018','BINGO-021','BINGO-022','AUTO-013','CORE-034']"), 1)
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
