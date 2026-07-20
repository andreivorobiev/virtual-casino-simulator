"""Long real-browser Big Six motion qualification for GitHub issue #223."""

# Import JSON serialization for the exact-head qualification summary.
import json
# Import one-way hashing so unique round evidence never serializes raw identifiers.
import hashlib
# Import environment access so the test server uses isolated synthetic storage.
import os
# Import safe recursive cleanup for the harness-owned temporary runtime only.
import shutil
# Import subprocess support for recording the exact tested Git commit.
import subprocess
# Import interpreter path access so the repository test package resolves from direct execution.
import sys
# Import temporary-directory allocation outside repository runtime data.
import tempfile
# Import timing helpers for bounded qualification telemetry.
import time
# Import paths for repository artifacts and harness-owned runtime directories.
from pathlib import Path

# Resolve the repository root from this tests/browser file.
ROOT = Path(__file__).resolve().parents[2]
# Put the repository root first so direct script execution imports the tracked tests package.
sys.path.insert(0, str(ROOT))
# Allocate one unique synthetic runtime root owned exclusively by this process.
RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="casino-big-six-motion-"))
# Redirect all mutable Casino state away from tracked repository fixtures before imports.
os.environ["CASINO_DATA_DIR"] = str(RUNTIME_ROOT / "data")
# Redirect server logs away from tracked or user-owned runtime paths.
os.environ["CASINO_LOG_DIR"] = str(RUNTIME_ROOT / "logs")

# Import Playwright only after isolated runtime paths are configured.
from playwright.sync_api import sync_playwright  # noqa: E402
# Import the repository's tracked loopback server and API helpers after runtime isolation.
from tests.run_tests import DEFAULT_AUTH_EMAIL, DEFAULT_AUTH_PASSWORD, api, login_default_user, start_server, stop_server  # noqa: E402

# Match the frontend's declared minimum full turns for one normal spin.
MIN_SPIN_REVOLUTIONS = 6
# Match the immutable Big Six wheel profile size.
WHEEL_SIZE = 54
# Exercise the issue-mandated consecutive UI count at every governed viewport.
SPINS_PER_VIEWPORT = 100
# Name each governed visual-matrix viewport and its exact CSS-pixel size.
VIEWPORTS = (
    ("desktop_primary", 1920, 1080),
    ("desktop_compact", 1440, 900),
    ("tablet", 1024, 900),
    ("mobile", 390, 844),
)
# Keep generated evidence under the repository's ignored browser artifact directory.
ARTIFACT_DIR = ROOT / "logs" / "test-runs"
# Install one computed-transform recorder before resize, locale, or lifecycle perturbations.
FRAME_PROBE_INSTALL = """
() => {
  // Reject accidental overlapping probes so one action cannot consume another action's frames.
  if (window.__bigSixMotionProbe) { throw new Error('Big Six motion probe already active'); }
  // Retain the pending recorder promise across Python-driven lifecycle operations.
  window.__bigSixMotionProbe = new Promise((resolve, reject) => {
  // Retain timestamp and normalized transform evidence for every presented frame.
  const frames = [];
  // Bound the probe so a frozen control fails instead of hanging qualification.
  const deadline = performance.now() + 5000;
  // Sample one browser animation frame from the live wheel element.
  const sample = (timestamp) => {
    // Resolve the current wheel after settlement-safe DOM replacement.
    const wheel = document.querySelector('[data-wheel]');
    // Resolve the atomic spin control used as the terminal presentation signal.
    const button = document.querySelector('[data-spin]');
    // Fail with a bounded diagnostic if route ownership disappeared unexpectedly.
    if (!wheel || !button) { reject(new Error('Big Six motion elements disappeared')); return; }
    // Parse the current composited transform through the browser matrix implementation.
    const matrix = new DOMMatrixReadOnly(getComputedStyle(wheel).transform);
    // Convert the matrix orientation into a normalized clockwise degree sample.
    const angle = ((Math.atan2(matrix.b, matrix.a) * 180 / Math.PI) + 360) % 360;
    // Resolve the live CSS transition so dropped frames cannot masquerade as reverse rotation.
    const animation = wheel.getAnimations().find(candidate => candidate.playState !== 'finished') || wheel.getAnimations()[0];
    // Read browser-computed eased progress for direction and transform-consistency evidence.
    const progress = animation?.effect?.getComputedTiming()?.progress;
    // Record timing, orientation, animation progress, result hiding, and control locks.
    frames.push({ timestamp, angle, animationProgress: Number.isFinite(progress) ? progress : null, locked: button.disabled, hubText: document.querySelector('.big-six-wheel__hub')?.textContent?.trim() || '', buttonText: button.textContent?.trim() || '', wagersLocked: [...document.querySelectorAll('[data-wager]')].every(control => control.disabled) });
    // Return complete evidence only after settlement restores the spin action.
    if (!button.disabled && frames.length > 1) { resolve(frames); return; }
    // Reject a frozen presentation after the explicit deadline.
    if (performance.now() > deadline) { reject(new Error('Big Six motion probe timed out')); return; }
    // Continue sampling through the browser's next composited frame.
    requestAnimationFrame(sample);
  };
  // Begin sampling from the next composited browser frame.
  requestAnimationFrame(sample);
  });
  // Return immediately so the harness can resize, throttle, freeze, and restore the page.
  return true;
}
"""
# Collect and clear the installed recorder after the atomic action unlocks.
FRAME_PROBE_COLLECT = """
async () => {
  // Require the same installed recorder created before lifecycle perturbation.
  if (!window.__bigSixMotionProbe) { throw new Error('Big Six motion probe was not installed'); }
  // Preserve the promise locally so cleanup cannot change the awaited value.
  const probe = window.__bigSixMotionProbe;
  // Remove the global owner before returning or propagating one bounded probe failure.
  delete window.__bigSixMotionProbe;
  // Return the complete pre- and post-perturbation frame sequence.
  return await probe;
}
"""


# Return one inline cumulative target angle from the mounted wheel element.
def target_angle(page):
    # Read the exact CSS custom property assigned by the game animation controller.
    return page.locator("[data-wheel]").evaluate("wheel => Number.parseFloat(wheel.style.getPropertyValue('--wheel-angle'))")


# Return the canonical pointer orientation for one server-selected result index.
def landing_angle(result_index):
    # Mirror the documented clockwise segment-center geometry without using UI state.
    return (360 - ((result_index + 0.5) * (360 / WHEEL_SIZE))) % 360


# Validate browser animation progress and return sampled forward motion in degrees.
def forward_progress(frames, starting_target, final_target):
    # Require enough composited samples to distinguish real interpolation from a target teleport.
    if len(frames) < 12:
        raise AssertionError(f"Big Six produced only {len(frames)} normal-motion frames")
    # Require a live browser transition across multiple samples instead of a target teleport.
    motion_frames = [frame for frame in frames if frame["animationProgress"] is not None]
    # Reject missing transition evidence even when the terminal transform happens to align.
    if len(motion_frames) < 4:
        raise AssertionError(f"Big Six produced only {len(motion_frames)} live transition samples")
    # Compare every adjacent sample for nondecreasing time and browser animation progress.
    for previous, current in zip(frames, frames[1:]):
        # Reject backward time while accepting same-frame timestamps shared by browser callbacks.
        if current["timestamp"] < previous["timestamp"]:
            raise AssertionError("Big Six frame timestamps moved backward")
    # Reject a genuine browser progress reversal while tolerating sub-frame rounding.
    if any(current["animationProgress"] + 0.002 < previous["animationProgress"] for previous, current in zip(motion_frames, motion_frames[1:])):
        raise AssertionError("Big Six browser transition progress reversed")
    # Calculate the positive cumulative target delta controlled by the frontend.
    target_delta = final_target - starting_target
    # Require every sampled transform to match its browser-computed interpolation progress.
    for frame in motion_frames:
        # Calculate the expected cumulative orientation at this eased transition progress.
        expected_angle = (starting_target + (target_delta * frame["animationProgress"])) % 360
        # Compare normalized matrix and expected orientations across the zero-degree boundary.
        angular_error = ((frame["angle"] - expected_angle + 540) % 360) - 180
        # Reject a transform that diverges from the declared forward cumulative target.
        if abs(angular_error) > 2.0:
            raise AssertionError(f"Big Six transform diverged from transition progress by {angular_error:.3f} degrees")
    # Require every still-locked frame to hide the outcome behind the spinning action copy.
    if any(frame["locked"] and frame["hubText"] != frame["buttonText"] for frame in frames):
        raise AssertionError("Big Six revealed an outcome while the spin remained locked")
    # Require wager controls to stay disabled on every still-locked presentation frame.
    if any(frame["locked"] and not frame["wagersLocked"] for frame in frames):
        raise AssertionError("Big Six wager controls unlocked before settlement")
    # Return the forward target distance represented by the observed progress interval.
    return target_delta * (motion_frames[-1]["animationProgress"] - motion_frames[0]["animationProgress"])


# Assert that every Big Six zone and atomic control can be reached without overlay interception.
def assert_scroll_reachability(page, viewport_id):
    # Cover the visible action, every wager, the wheel, the result, and the terminal history row.
    selectors = ["[data-spin]", *[f'[data-wager="{outcome_id}"]' for outcome_id in ("one", "two", "five", "ten", "twenty", "joker", "crest")], ".big-six-wheel__wheel-shell", ".big-six-wheel__result", ".big-six-wheel__history-row:last-child"]
    # Scroll each representative node through the real page or nested scroll owner.
    for selector in selectors:
        # Resolve the single stable route node for this reachability gate.
        node = page.locator(selector)
        # Require the expected settled route element to exist.
        if node.count() != 1:
            raise AssertionError(f"Big Six reachability selector missing at {viewport_id}: {selector}")
        # Ask the browser to reveal the node through its actual scroll container.
        node.scroll_into_view_if_needed()
        # Read the rendered bounding box after scrolling completes.
        box = node.bounding_box()
        # Reject detached or non-rendered elements.
        if box is None:
            raise AssertionError(f"Big Six element did not render at {viewport_id}: {selector}")
        # Read the current CSS viewport after any intentional earlier resize restoration.
        viewport_height = page.evaluate("() => window.innerHeight")
        # Require the complete target to fit vertically inside the visible viewport.
        if box["y"] < -1 or box["y"] + box["height"] > viewport_height + 1:
            raise AssertionError(f"Big Six element could not scroll fully into {viewport_id}: {selector}")
        # Verify interactive controls are not covered by a footer, header, or sibling overlay.
        if selector == "[data-spin]" or selector.startswith("[data-wager"):
            # Hit-test the control center through the browser's painted stacking order.
            hit_ok = node.evaluate("node => { const box = node.getBoundingClientRect(); const hit = document.elementFromPoint(box.left + (box.width / 2), box.top + (box.height / 2)); return hit === node || node.contains(hit); }")
            # Reject visually present controls that cannot receive pointer input.
            if not hit_ok:
                raise AssertionError(f"Big Six control was covered at {viewport_id}: {selector}")


# Probe the deployed WSGI static path in a listener-free isolated child process.
def run_production_asset_cache_probe():
    # Copy the current process environment without exposing its values in output.
    environment = os.environ.copy()
    # Select the fail-closed production adapter only inside the child process.
    environment["CASINO_DEPLOYMENT_MODE"] = "production"
    # Isolate production-probe state from the browser-test server and repository.
    environment["CASINO_DATA_DIR"] = str(RUNTIME_ROOT / "wsgi-state")
    # Isolate production-probe logs under the same harness-owned temporary root.
    environment["CASINO_LOG_DIR"] = str(RUNTIME_ROOT / "wsgi-logs")
    # Keep the listener-free cache probe independent of a database provider.
    environment["CASINO_STORAGE_PROVIDER"] = "json"
    # Supply a reserved-domain synthetic Admin identity required by production bootstrap.
    environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = "big-six-probe@example.invalid"
    # Supply a synthetic external token-digest key for the isolated production-mode browser probe.
    environment["CASINO_TOKEN_DIGEST_KEY"] = "big-six-probe-token-digest-key-material-2026"
    # Supply an independent synthetic mail digest key required by public startup.
    environment["CASINO_MAIL_DIGEST_KEY"] = "big-six-probe-mail-digest-key-material-2026"
    # Supply a non-default synthetic credential that is never printed or persisted.
    environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = "synthetic-big-six-static-probe-password"
    # Configure one reserved synthetic origin for host and CSRF validation.
    environment["CASINO_CANONICAL_ORIGIN"] = "https://casino.example.invalid"
    # Trust only the direct synthetic loopback proxy address.
    environment["CASINO_TRUSTED_PROXY"] = "127.0.0.1"
    # Enable the same restricted-preview application stage used by the release service.
    environment["CASINO_RESTRICTED_PREVIEW"] = "1"
    # Preserve the strongest governed same-origin session mode.
    environment["CASINO_SESSION_SAMESITE"] = "Strict"
    # Prevent the child interpreter from writing bytecode into the exact checkout.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    # Execute the focused direct WSGI probe without opening a socket.
    result = subprocess.run([sys.executable, "tests/browser/big_six_wheel_wsgi_asset_probe.py"], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30)
    # Fail with a bounded diagnostic instead of echoing child environment or raw output.
    if result.returncode != 0:
        raise AssertionError("production WSGI Big Six asset cache probe failed")
    # Parse the probe's final sanitized JSON line.
    evidence = json.loads(result.stdout.strip().splitlines()[-1])
    # Require the exact deployed adapter policy and current-source marker.
    if evidence != {"status": "pass", "cache_control": "no-store", "current_source_marker": True}:
        raise AssertionError("production WSGI Big Six asset evidence was incomplete")
    # Return only the bounded public policy result for the qualification summary.
    return evidence


# Assert one normal spin through the real authenticated UI and return telemetry.
def run_normal_spin(page, *, viewport_id, spin_index, cdp_session, switch_locale=False, resize_during_spin=False, background_cycle=False, slow_device=False):
    # Apply deterministic four-times CPU throttling before the selected slow-device action.
    if slow_device:
        # Use the pinned Chromium protocol without changing host or user runtime settings.
        cdp_session.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    # Capture the prior settled target so absolute-reset motion cannot pass.
    starting_target = target_angle(page)
    # Observe the exact ledger-backed spin response triggered by the visible button.
    with page.expect_response(lambda response: response.url.endswith("/api/v1/games/big-six-wheel/spins") and response.request.method == "POST") as response_info:
        # Start the atomic action through the real game control.
        page.locator("[data-spin]").click()
    # Decode only the standard response envelope returned to the same UI action.
    response_body = response_info.value.json()
    # Require the real server to accept the synthetic UI wager.
    if response_body.get("ok") is not True:
        raise AssertionError(f"Big Six UI spin failed at {viewport_id}/{spin_index}")
    # Read the authoritative settled round without logging player or request identity.
    round_data = response_body["data"]["round"]
    # Require both the action and every wager input to remain locked during presentation.
    if not page.locator("[data-spin]").is_disabled() or not all(control.is_disabled() for control in page.locator("[data-wager]").all()):
        raise AssertionError("Big Six controls did not lock during the atomic spin")
    # Compare the result hub with the spinning action to prove no outcome leaked early.
    if page.locator(".big-six-wheel__hub").inner_text().strip() != page.locator("[data-spin]").inner_text().strip():
        raise AssertionError("Big Six exposed the server outcome before motion completed")
    # Install frame recording before any locale, viewport, lifecycle, or CPU perturbation.
    page.evaluate(FRAME_PROBE_INSTALL)
    # Switch locale during one live animation to prove state preservation without wheel replacement.
    if switch_locale:
        # Select Russian through the shared authenticated locale control while the spin owns the wheel.
        page.get_by_test_id("shell-locale-select").select_option("ru-RU")
    # Resize during one live animation to prove responsive layout cannot cancel the transform.
    if resize_during_spin:
        # Move temporarily to the governed mobile size while the normal timer remains active.
        page.set_viewport_size({"width": 390, "height": 844})
    # Freeze and resume one live page to cover a stronger-than-background lifecycle pause.
    if background_cycle:
        # Allow the installed recorder to observe ordinary visible motion before suspension.
        page.wait_for_timeout(50)
        # Suspend timers and compositing through Chromium's page-lifecycle protocol.
        cdp_session.send("Page.setWebLifecycleState", {"state": "frozen"})
        # Keep the synthetic tab suspended long enough to cross multiple ordinary frames.
        time.sleep(0.25)
        # Restore the page so its owned animation and settlement timer can continue.
        cdp_session.send("Page.setWebLifecycleState", {"state": "active"})
    # Start protected probe cleanup so CPU throttling never leaks to later actions.
    try:
        # Collect real composited transform frames until settlement unlocks the action.
        frames = page.evaluate(FRAME_PROBE_COLLECT)
    # Restore deterministic browser performance after success or assertion failure.
    finally:
        # Disable the selected slow-device throttle before later spins or cleanup.
        if slow_device:
            # Return Chromium to its ordinary unthrottled execution rate.
            cdp_session.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    # Restore the named viewport after the one intentional in-spin resize.
    if resize_during_spin:
        # Resolve the original governed dimensions from the immutable viewport table.
        _, width, height = next(row for row in VIEWPORTS if row[0] == viewport_id)
        # Return to the current evidence viewport after motion completed safely.
        page.set_viewport_size({"width": width, "height": height})
    # Read the cumulative target retained by the newly settled route render.
    final_target = target_angle(page)
    # Require at least the configured complete turns of forward target movement.
    if final_target - starting_target < (MIN_SPIN_REVOLUTIONS * 360) - 1e-6:
        raise AssertionError("Big Six target reset, reversed, or advanced fewer than six turns")
    # Normalize the final cumulative target for server-index alignment comparison.
    normalized_target = ((final_target % 360) + 360) % 360
    # Require the fixed pointer to center the exact server-selected segment.
    if abs(normalized_target - landing_angle(round_data["result_index"])) > 1e-6:
        raise AssertionError("Big Six final pointer angle disagrees with the server result index")
    # Calculate visible travel from the browser's actual composited matrices.
    sampled_travel = forward_progress(frames, starting_target, final_target)
    # Require multiple visible revolutions even when sampling begins just after request completion.
    if sampled_travel < 1080:
        raise AssertionError(f"Big Six visible motion was frozen or too short: {sampled_travel:.2f} degrees")
    # Calculate the actual browser presentation time from frame timestamps.
    duration_ms = frames[-1]["timestamp"] - frames[0]["timestamp"]
    # Bound normal presentation around the declared 1.4-second transition with slow-device tolerance.
    if duration_ms < 1000 or duration_ms > 3000:
        raise AssertionError(f"Big Six normal-motion duration was {duration_ms:.1f} ms")
    # Require every control to recover after the authoritative settlement is visible.
    if page.locator("[data-spin]").is_disabled() or any(control.is_disabled() for control in page.locator("[data-wager]").all()):
        raise AssertionError("Big Six controls did not recover after settlement")
    # Return sanitized per-spin telemetry without player, round, request, or infrastructure identifiers.
    return {"viewport": viewport_id, "spin": spin_index + 1, "result_index": round_data["result_index"], "duration_ms": duration_ms, "frames": len(frames), "sampled_degrees": sampled_travel, "background_cycle": background_cycle, "slow_device": slow_device, "_round_id": round_data["round_id"]}


# Assert one reduced-motion spin settles immediately but remains understandable and aligned.
def run_reduced_motion_spin(page, viewport_id):
    # Enable the governed platform preference before beginning the atomic action.
    page.emulate_media(reduced_motion="reduce")
    # Capture the cumulative start angle for forward-target verification.
    starting_target = target_angle(page)
    # Record wall-clock duration around the real visible action.
    started = time.perf_counter()
    # Observe the exact real-backend request triggered by the UI.
    with page.expect_response(lambda response: response.url.endswith("/api/v1/games/big-six-wheel/spins") and response.request.method == "POST") as response_info:
        # Activate the same spin control used in normal-motion qualification.
        page.locator("[data-spin]").click()
    # Decode the authoritative response for alignment evidence.
    response_body = response_info.value.json()
    # Wait for zero-delay scheduling to restore the visible action.
    page.wait_for_function("() => document.querySelector('[data-wheel]')?.dataset.reducedMotion === 'true' && document.querySelector('[data-spin]')?.disabled === false")
    # Calculate the complete reduced-motion user-visible duration.
    duration_ms = (time.perf_counter() - started) * 1000
    # Reject a decorative-delay regression under reduced motion.
    if duration_ms > 750:
        raise AssertionError(f"Big Six reduced motion took {duration_ms:.1f} ms")
    # Read the server-aligned cumulative target retained after immediate settlement.
    final_target = target_angle(page)
    # Require logical forward target continuity even though interpolation is suppressed.
    if final_target - starting_target < (MIN_SPIN_REVOLUTIONS * 360) - 1e-6:
        raise AssertionError("Big Six reduced-motion target lost cumulative orientation")
    # Require the final pointer to match the same server-selected index contract.
    if abs((((final_target % 360) + 360) % 360) - landing_angle(response_body["data"]["round"]["result_index"])) > 1e-6:
        raise AssertionError("Big Six reduced-motion pointer alignment failed")
    # Restore normal platform motion before the next viewport or action.
    page.emulate_media(reduced_motion="no-preference")
    # Return bounded reduced-motion telemetry.
    return {"viewport": viewport_id, "duration_ms": duration_ms}


# Run the complete isolated long qualification and return a sanitized summary.
def run_qualification():
    # Create the ignored evidence directory before browser output begins.
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    # Read the exact source commit tested by this worktree.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    # Initialize tracked server state for unconditional cleanup.
    server_process = None
    # Initialize the loopback base only after successful startup.
    base = None
    # Store all sanitized normal and reduced-motion telemetry.
    normal_results = []
    # Store one reduced-motion result per governed viewport.
    reduced_results = []
    # Retain only one-way round-id digests in memory without serializing identifiers.
    round_digests = set()
    # Prove the deployed static path rejects cached-old assets before browser testing begins.
    asset_cache_evidence = run_production_asset_cache_probe()
    try:
        # Start one loopback-only server against the harness-owned temporary data root.
        server_process, base = start_server()
        # Emit one sanitized startup checkpoint without exposing the loopback address or process identity.
        print(json.dumps({"stage": "server-ready", "issue": 223}), flush=True)
        # Reset only this isolated synthetic runtime before browser login.
        api(base, "/api/v1/casino/reset", "POST", {})
        # Refresh the direct helper session after the isolated reset.
        login_default_user(base)
        # Launch the pinned real Chromium runtime through Playwright.
        with sync_playwright() as playwright:
            # Start headless Chromium without touching any user browser profile.
            browser = playwright.chromium.launch(headless=True)
            # Open one isolated page at the primary desktop viewport.
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            # Create one page-scoped Chromium protocol session for lifecycle and CPU qualification.
            cdp_session = page.context.new_cdp_session(page)
            # Bound ordinary page actions while leaving the explicit frame probe its own deadline.
            page.set_default_timeout(10000)
            # Navigate without seeded credentials so the real login gate is exercised.
            page.goto(base, wait_until="networkidle")
            # Fill the local synthetic bootstrap identity through visible controls.
            page.get_by_test_id("login-email").fill(DEFAULT_AUTH_EMAIL)
            # Fill the local synthetic bootstrap password without logging or serializing it.
            page.get_by_test_id("login-password").fill(DEFAULT_AUTH_PASSWORD)
            # Accept the fake-money simulator acknowledgement through the visible checkbox.
            page.get_by_test_id("login-terms-check").check()
            # Submit the real login form and wait for the authenticated lobby.
            page.get_by_test_id("login-submit").click()
            # Require the authenticated shell before navigating to the game.
            page.get_by_test_id("lobby").wait_for()
            # Enter Big Six through the catalog-generated navigation control.
            page.get_by_test_id("nav-big_six_wheel").click()
            # Wait for the game-owned readiness selector.
            page.get_by_test_id("big-six-wheel").wait_for()
            # Reload the canonical game route to prove the browser refetches the module asset.
            with page.expect_response(lambda response: response.url.endswith("/games/big_six_wheel.js")) as asset_response_info:
                # Exercise a real route reload rather than inspecting server configuration only.
                page.reload(wait_until="networkidle")
            # Require the current game route to remount after the asset fetch.
            page.get_by_test_id("big-six-wheel").wait_for()
            # Resolve the exact JavaScript asset response returned during reload.
            asset_response = asset_response_info.value
            # Require the development adapter to return the requested module successfully.
            if not asset_response.ok:
                raise AssertionError("Big Six route reload did not refetch its frontend module")
            # Require the refetched source to contain this fix's cumulative-motion marker.
            if "MIN_SPIN_REVOLUTIONS" not in asset_response.text():
                raise AssertionError("Big Six reloaded asset did not match current cumulative-motion source")
            # Enter one positive wager once and retain it through every repeated spin.
            page.locator('[data-wager="one"]').fill("1")
            # Emit one sanitized authenticated checkpoint before the long motion loop begins.
            print(json.dumps({"stage": "ui-ready", "issue": 223}), flush=True)
            # Exercise every governed viewport independently.
            for viewport_id, width, height in VIEWPORTS:
                # Reset the viewport to its exact matrix dimensions before its consecutive run.
                page.set_viewport_size({"width": width, "height": height})
                # Start each viewport in English so both locale halves are deterministic.
                page.get_by_test_id("shell-locale-select").select_option("en-US")
                # Run the required consecutive normal-motion count through the visible UI.
                for spin_index in range(SPINS_PER_VIEWPORT):
                    # Switch locale during the fiftieth live animation instead of between actions.
                    switch_locale = spin_index == 49
                    # Resize during one desktop-primary animation to exercise responsive continuity.
                    resize_during_spin = viewport_id == "desktop_primary" and spin_index == 24
                    # Freeze and restore one later desktop-primary action without abandoning settlement.
                    background_cycle = viewport_id == "desktop_primary" and spin_index == 74
                    # Throttle one later desktop-primary action to cover a slow rendering device.
                    slow_device = viewport_id == "desktop_primary" and spin_index == 89
                    # Execute and retain sanitized frame/timing telemetry for this spin.
                    result = run_normal_spin(page, viewport_id=viewport_id, spin_index=spin_index, cdp_session=cdp_session, switch_locale=switch_locale, resize_during_spin=resize_during_spin, background_cycle=background_cycle, slow_device=slow_device)
                    # Remove the raw server round identity before sanitized telemetry leaves this process scope.
                    round_id = result.pop("_round_id")
                    # Hash the authoritative round identity so no raw action identifier leaves process memory.
                    round_digest = hashlib.sha256(round_id.encode("utf-8")).hexdigest()
                    # Fail closed if two UI actions resolved to the same server round identity.
                    if round_digest in round_digests:
                        raise AssertionError("Big Six server round identity repeated")
                    # Retain the one-way server-round digest in process memory.
                    round_digests.add(round_digest)
                    # Append the sanitized result to the final aggregate.
                    normal_results.append(result)
                    # Report bounded progress every ten actions so a failure retains its exact run position.
                    if (spin_index + 1) % 10 == 0:
                        # Emit only the governed viewport and completed action count.
                        print(json.dumps({"stage": "normal-motion", "viewport": viewport_id, "completed": spin_index + 1}), flush=True)
                # Require Russian to own the second half and terminal evidence for this viewport.
                if page.get_by_test_id("shell-locale-select").input_value() != "ru-RU":
                    raise AssertionError(f"Big Six locale switch did not persist at {viewport_id}")
                # Collect exact horizontal escapes instead of relying on document scroll width.
                escaped_bounds = page.evaluate("""() => [...document.querySelectorAll('.big-six-wheel, .big-six-wheel__layout, .big-six-wheel__panel, .big-six-wheel__wheel-shell, [data-wager], [data-spin]')].map(node => { const box = node.getBoundingClientRect(); return { className: String(node.className || ''), wager: node.getAttribute('data-wager'), left: box.left, right: box.right, viewport: window.innerWidth }; }).filter(box => box.left < -1 || box.right > box.viewport + 1)""")
                # Reject clipped controls with bounded class, wager, and geometry evidence.
                if escaped_bounds:
                    raise AssertionError(f"Big Six bounds escaped {viewport_id}: {json.dumps(escaped_bounds, ensure_ascii=False)}")
                # Prove every Big Six control and terminal data region is reachable and uncovered.
                assert_scroll_reachability(page, viewport_id)
                # Wait through two paint frames after the final programmatic scroll.
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                # Capture the actual lower-scroll viewport for human reachability review.
                page.screenshot(path=str(ARTIFACT_DIR / f"after-pass-big-six-motion-soak-ru-{viewport_id}-lower.png"), full_page=False, animations="disabled", style="#toast, .status-bar { visibility: hidden !important; }")
                # Center the complete wheel stage through the same real scroll owner.
                page.locator(".big-six-wheel__wheel-shell").evaluate("node => node.scrollIntoView({ block: 'center', inline: 'nearest' })")
                # Wait through two paint frames before capturing the centered stage.
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                # Capture direct human evidence for the wheel, pointer, outcome, and containment.
                page.screenshot(path=str(ARTIFACT_DIR / f"after-pass-big-six-motion-soak-ru-{viewport_id}-stage.png"), full_page=False, animations="disabled", style="#toast, .status-bar { visibility: hidden !important; }")
                # Return to the game heading so the paired top evidence starts canonically.
                page.get_by_test_id("big-six-wheel").locator("h1").scroll_into_view_if_needed()
                # Wait through two paint frames after restoring the canonical top position.
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                # Capture the terminal Russian top viewport without nested-scroll stitching artifacts.
                page.screenshot(path=str(ARTIFACT_DIR / f"after-pass-big-six-motion-soak-ru-{viewport_id}.png"), full_page=False, animations="disabled", style="#toast, .status-bar { visibility: hidden !important; }")
                # Execute one reduced-motion action through the same UI and viewport.
                reduced_results.append(run_reduced_motion_spin(page, viewport_id))
                # Emit one sanitized viewport-complete checkpoint after reduced-motion coverage.
                print(json.dumps({"stage": "viewport-complete", "viewport": viewport_id}), flush=True)
            # Release the page-scoped protocol session after lifecycle and throttling evidence completes.
            cdp_session.detach()
            # Close the isolated browser after its protocol session releases ownership.
            browser.close()
    finally:
        # Stop only the exact tracked loopback child when startup succeeded.
        if server_process is not None and base is not None:
            stop_server(server_process, base)
        # Remove only the unique temporary runtime allocated by this script.
        shutil.rmtree(RUNTIME_ROOT, ignore_errors=True)
    # Require the exact issue-mandated normal-motion total across four viewports.
    if len(normal_results) != SPINS_PER_VIEWPORT * len(VIEWPORTS):
        raise AssertionError("Big Six qualification did not complete every required UI spin")
    # Build one sanitized exact-head aggregate without credentials, sessions, raw ids, or paths.
    summary = {
        "issue": 223,
        "commit": commit,
        "normal_ui_spins": len(normal_results),
        "unique_iteration_digests": len(round_digests),
        "spins_per_viewport": SPINS_PER_VIEWPORT,
        "viewports": [row[0] for row in VIEWPORTS],
        "locales": ["en-US", "ru-RU"],
        "minimum_frames": min(result["frames"] for result in normal_results),
        "minimum_sampled_degrees": min(result["sampled_degrees"] for result in normal_results),
        "normal_duration_ms": {"minimum": min(result["duration_ms"] for result in normal_results), "maximum": max(result["duration_ms"] for result in normal_results)},
        "background_foreground_ui_spins": sum(1 for result in normal_results if result["background_cycle"]),
        "slow_device_ui_spins": sum(1 for result in normal_results if result["slow_device"]),
        "static_asset_cache_policy": asset_cache_evidence,
        "development_asset_cache_parity": "tracked separately by issue #310",
        "scroll_reachability": "all wager controls, primary action, wheel, result, and terminal history row fully visible; interactive centers hit-testable",
        "reduced_motion": reduced_results,
        "failures": [],
        "runtime_cleanup": "tracked PID stopped; loopback port verified closed; temporary synthetic data removed",
    }
    # Write the ignored sanitized summary next to its exact-head screenshots.
    (ARTIFACT_DIR / "after-pass-big-six-motion-soak-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    # Return the summary for concise CLI output and calling tests.
    return summary


# Execute the qualification only when invoked as a standalone long browser gate.
if __name__ == "__main__":
    # Run the complete suite and retain only sanitized aggregate output.
    qualification_summary = run_qualification()
    # Print bounded aggregate evidence without credentials, sessions, or raw action identifiers.
    print(json.dumps(qualification_summary, indent=2, ensure_ascii=False))
