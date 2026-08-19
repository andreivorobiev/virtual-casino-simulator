# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused real-backend browser validation for the isolated Chuck-a-Luck slice."""

# Import argument parsing for optional evidence output.
import argparse
# Import JSON serialization for self-describing after-pass evidence sidecars.
import json
# Import environment copying for isolated test-only bootstrap configuration.
import os
# Import cryptographic randomness for a nonlogged disposable test password.
import secrets
# Import sockets for ephemeral port selection and listener cleanup proof.
import socket
# Import subprocess control for the dedicated non-8765 real backend.
import subprocess
# Import the active interpreter path for the companion server launcher.
import sys
# Import temporary directories so no repository data path is touched.
import tempfile
# Import short polling delays for bounded startup and shutdown checks.
import time
# Import URL requests for a lightweight readiness probe.
import urllib.request
# Import filesystem paths for stable launcher and evidence locations.
from pathlib import Path

# Import the real Chromium automation API used by repository browser tests.
from playwright.sync_api import sync_playwright

# Resolve the repository root from this game-owned focused test file.
ROOT = Path(__file__).resolve().parents[3]
# Add the repository root so the shared Browser timing policy is importable during direct execution.
sys.path.insert(0, str(ROOT))
# Import the sole environment-scalable Playwright wait budget. (TEST-053)
from tests.browser_timing import WAIT_MS
# Resolve the companion server launcher without relying on the process working directory.
SERVER_LAUNCHER = Path(__file__).with_name("browser_server.py")
# Preserve the authoritative visual-matrix viewports in stable evidence order.
VIEWPORTS = {
    "desktop_primary": {"width": 1920, "height": 1080},  # Exercise the primary desktop review canvas.
    "desktop_compact": {"width": 1440, "height": 900},  # Exercise the compact desktop review canvas.
    "tablet": {"width": 1024, "height": 900},  # Exercise the governed tablet breakpoint.
    "mobile": {"width": 390, "height": 844},  # Exercise the governed narrow mobile canvas.
}
# Preserve required locale titles for visible-copy verification.
LOCALE_TITLES = {"en-US": "Chuck-a-Luck", "ru-RU": "Чак-а-лак"}
# Map every captured state to the governed viewports exercised for that evidence class.
EVIDENCE_VIEWPORTS = {
    "ready": tuple(VIEWPORTS),  # Capture the complete ready-state viewport matrix.
    "rolling": ("desktop_primary", "mobile"),  # Capture representative desktop and mobile committed rolling states.
    "settled": tuple(VIEWPORTS),  # Capture the complete settled-state viewport matrix.
    "route_restored": ("desktop_primary", "mobile"),  # Capture representative desktop and mobile reload restoration.
    "reduced_motion": ("desktop_primary", "mobile"),  # Capture representative desktop and mobile zero-delay presentation.
}


# Reserve one ephemeral loopback port while explicitly excluding both user-owned runtime ports.
def free_port():
    # Ask the operating system for an unused IPv4 loopback port.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        # Bind only loopback so no firewall or external interface is involved.
        probe.bind(("127.0.0.1", 0))
        # Read the assigned port before releasing the reservation.
        port = probe.getsockname()[1]
    # Retry the extraordinarily unlikely allocation of either protected user runtime port.
    return free_port() if port in {8765, 8877} else port


# Return whether the exact focused listener still accepts connections.
def listener_open(port):
    # Create a short-lived probe socket for deterministic cleanup checks.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        # Avoid blocking the test when the listener is already closed.
        probe.settimeout(0.2)
        # Report only the exact loopback port selected by this test.
        return probe.connect_ex(("127.0.0.1", port)) == 0


# Wait for the real app's static shell to accept HTTP requests.
def wait_for_server(base_url, process):
    # Poll for at most twelve seconds, matching the repository harness budget.
    for _ in range(120):
        # Fail early when the child exits before it can serve the shell.
        if process.poll() is not None:
            # Surface a concise startup diagnostic without exposing environment values.
            raise RuntimeError("Focused Chuck-a-Luck server exited before readiness")
        # Probe the static shell without creating any authenticated runtime action.
        try:
            # Close the readiness response promptly after confirming the listener.
            with urllib.request.urlopen(base_url, timeout=0.5):
                # Return as soon as the real application responds.
                return
        # Ignore connection failures during the bounded startup window.
        except Exception:
            # Yield briefly before the next readiness probe.
            time.sleep(0.1)
    # Fail with a stable diagnostic when startup never completes.
    raise RuntimeError("Focused Chuck-a-Luck server did not become ready")


# Stop the child and prove its exact listener has closed.
def stop_server(process, port):
    # Request normal process termination when the server remains active.
    if process.poll() is None:
        # Send the platform termination signal to the dedicated child only.
        process.terminate()
        # Give the server a short grace period to close its socket.
        try:
            # Wait for normal shutdown without blocking the task indefinitely.
            process.wait(timeout=5)
        # Force only the dedicated child when normal termination misses the deadline.
        except subprocess.TimeoutExpired:
            # Kill the focused child without affecting any other listener.
            process.kill()
            # Reap the killed process before checking its port.
            process.wait(timeout=5)
    # Poll briefly because Windows may release the socket just after process exit.
    for _ in range(50):
        # Return successful cleanup as soon as the exact port is closed.
        if not listener_open(port):
            # Report a positive listener-cleanup result to the caller.
            return True
        # Yield before checking the same focused port again.
        time.sleep(0.1)
    # Report cleanup failure without inspecting or changing unrelated ports.
    return False


# Capture one named full-shell image only when an evidence directory was requested.
def capture(page, evidence_dir, state, locale, viewport):
    # Skip artifact creation during ordinary focused browser checks.
    if evidence_dir is None:
        # Return without changing the repository or temporary runtime.
        return
    # Skip coordinates that remain assertion-covered but are not required as representative image artifacts.
    if viewport not in EVIDENCE_VIEWPORTS[state]:
        # Return without creating an image or sidecar outside the declared evidence set.
        return
    # Ensure the explicitly requested evidence directory exists.
    evidence_dir.mkdir(parents=True, exist_ok=True)
    # Build one protocol-readable artifact name from exact matrix dimensions.
    target = evidence_dir / f"{state}_{locale}_{viewport}.png"
    # Capture the affected game surface while excluding transient shared-shell status overlays.
    page.get_by_test_id("chuck-a-luck").screenshot(path=str(target), animations="disabled", style="#toast, .status-bar { visibility: hidden !important; }")


# Write one protocol-complete metadata record beside every successful evidence image.
def write_evidence_sidecars(evidence_dir):
    # Read the tested source commit only after the complete browser and listener checks pass.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
    # Read the symbolic worker branch that owns the isolated evidence run.
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(ROOT), text=True).strip() or "detached"
    # Visit every state and viewport promised by the focused evidence matrix.
    for state, viewport_ids in EVIDENCE_VIEWPORTS.items():
        # Pair each state with both required locale resources.
        for locale in LOCALE_TITLES:
            # Record each governed viewport using the exact capture filename.
            for viewport_id in viewport_ids:
                # Resolve the PNG that the successful browser pass just produced.
                target = evidence_dir / f"{state}_{locale}_{viewport_id}.png"
                # Fail the evidence run instead of publishing incomplete metadata.
                if not target.exists():
                    # Surface only the missing branch-local artifact path.
                    raise AssertionError(f"Missing Chuck-a-Luck evidence artifact: {target}")
                # Record a repository-relative path for portable PR review.
                relative_path = target.resolve().relative_to(ROOT).as_posix()
                # Build the complete visual-standard identity for this exact image.
                metadata = {
                    "evidence_class": "after_pass",  # Mark the artifact as passing acceptance evidence.
                    "branch": branch,  # Identify the worker branch used for capture.
                    "commit": commit,  # Identify the tested source commit exactly.
                    "surface": "chuck_a_luck",  # Name the proposed visual-matrix surface.
                    "state": state,  # Name the exact state visible in this image.
                    "locale": locale,  # Name the active visible locale.
                    "viewport": {"id": viewport_id, **VIEWPORTS[viewport_id]},  # Record both governed id and dimensions.
                    "path": relative_path,  # Link the sidecar back to its image.
                }
                # Serialize readable UTF-8 metadata next to the passing image.
                target.with_suffix(".json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# Assert localized responsive state across the complete required matrix.
def exercise_matrix(page, evidence_dir, state):
    # Map evidence aliases to the machine phase expected from the game surface.
    expected_phase = "ready" if state == "ready" else "rolling" if state == "rolling" else "settled"
    # Test both required locales without remounting or losing game state.
    for locale, title in LOCALE_TITLES.items():
        # Switch locale through the authenticated shared-shell control.
        page.get_by_test_id("shell-locale-select").select_option(locale)
        # Wait for the game-owned title resource to render in the chosen locale.
        page.wait_for_function("expected => document.querySelector('[data-testid=\"chuck-a-luck\"] h1')?.textContent === expected", arg=title)
        # Exercise every viewport named by the authoritative visual matrix.
        for viewport_id, viewport in VIEWPORTS.items():
            # Resize the real page to the exact matrix dimensions.
            page.set_viewport_size(viewport)
            # Require the isolated game surface to remain mounted and visible.
            assert page.get_by_test_id("chuck-a-luck").is_visible()
            # Require the named evidence state to retain its truthful machine phase at every coordinate.
            assert page.get_by_test_id("chuck-a-luck").get_attribute("data-phase") == expected_phase
            # Forbid page-level horizontal overflow at this locale and viewport.
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            # Require the primary action to retain the minimum governed touch height.
            assert page.locator("[data-roll]").evaluate("element => element.getBoundingClientRect().height >= 42")
            # Save optional after-pass evidence for this exact matrix coordinate.
            capture(page, evidence_dir, state, locale, viewport_id)


# Run the authenticated real-backend interaction and visual checks.
def run_browser_check(evidence_dir=None):
    # Allocate one dedicated listener port that cannot collide with the user's active Casino.
    port = free_port()
    # Build the loopback origin used by both readiness and Chromium.
    base_url = f"http://127.0.0.1:{port}"
    # Create a disposable test-only administrator identity.
    admin_email = "chuck-browser@example.local"
    # Generate a high-entropy credential that is never printed or persisted in source.
    admin_password = secrets.token_urlsafe(32)
    # Copy the current environment before adding process-local test settings.
    environment = os.environ.copy()
    # Select the explicitly local test startup policy.
    environment["CASINO_DEPLOYMENT_MODE"] = "test"
    # Force the disposable JSON provider so inherited MySQL configuration cannot affect external state.
    environment["CASINO_STORAGE_PROVIDER"] = "json"
    # Supply the disposable bootstrap identity only to the child process.
    environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = admin_email
    # Supply the nonlogged disposable password only to the child process.
    environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = admin_password
    # Track the child outside the temporary-context block for guaranteed cleanup.
    process = None
    # Track listener cleanup evidence for final reporting.
    closed = False
    # Store the selected child PID after launch for the validation handoff.
    pid = None
    # Create a runtime tree outside the worktree for all player, ledger, state, and log writes.
    with tempfile.TemporaryDirectory(prefix="chuck-a-luck-browser-") as runtime_root:
        # Resolve the disposable cross-process signal that releases the first committed roll response.
        release_file = Path(runtime_root) / "release-first-roll"
        # Start protected orchestration so every failure still closes the listener.
        try:
            # Launch the real app through the narrow in-memory revision shim.
            process = subprocess.Popen([sys.executable, str(SERVER_LAUNCHER), "--port", str(port), "--runtime-root", runtime_root], cwd=str(ROOT), env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Record the dedicated process id for the listener-cleanup report.
            pid = process.pid
            # Wait until the authenticated application shell can be loaded.
            wait_for_server(base_url, process)
            # Start the repository-standard Chromium automation runtime.
            with sync_playwright() as playwright:
                # Launch headless Chromium for deterministic focused evidence.
                browser = playwright.chromium.launch(headless=True)
                # Create a page at the primary desktop viewport for visible login.
                page = browser.new_page(viewport=VIEWPORTS["desktop_primary"])
                # Navigate directly to the canonical game route to test route restoration through auth.
                page.goto(f"{base_url}/games/chuck_a_luck", wait_until="networkidle")
                # Complete the real backend login through browser-visible controls.
                page.get_by_test_id("login-email").fill(admin_email)
                # Fill the disposable password without logging or screenshotting it.
                page.get_by_test_id("login-password").fill(admin_password)
                # Accept the local simulator terms gate required by the login form.
                page.get_by_test_id("login-terms-check").check()
                # Submit the authenticated session request through the visible primary action.
                page.get_by_test_id("login-submit").click()
                # Wait for descriptor-driven lazy loading of the isolated game module.
                page.get_by_test_id("chuck-a-luck").wait_for(timeout=WAIT_MS * 2)
                # Prove ready-state EN/RU responsiveness across all four viewports.
                exercise_matrix(page, evidence_dir, "ready")
                # Restore primary desktop English before the atomic backend action.
                page.set_viewport_size(VIEWPORTS["desktop_primary"])
                # Select English through the same shared-shell locale control.
                page.get_by_test_id("shell-locale-select").select_option("en-US")
                # Enter one positive play-token wager on the first number.
                page.locator('[data-wager="one"]').fill("2")
                # Collect the first roll response after the test-only server releases its already committed payload.
                roll_responses = []

                # Record only the atomic Chuck-a-Luck action response from the real backend.
                def record_roll_response(response):
                    # Ignore shell, locale, state, and wallet responses.
                    if not (response.url.endswith("/api/v1/games/chuck-a-luck/rolls") and response.request.method == "POST"):
                        # Return without mutating the focused response list.
                        return
                    # Retain the real response for envelope and server-dice assertions.
                    roll_responses.append(response)

                # Subscribe before the visible click so even an unusually fast response cannot be missed.
                page.on("response", record_roll_response)
                # Start one guarded atomic roll from the real browser UI.
                page.locator("[data-roll]").click()
                # Require the browser to remain in its decorative, non-authoritative rolling phase while the real response is deliberately held.
                page.locator('[data-testid="chuck-a-luck"][data-phase="rolling"]').wait_for(timeout=WAIT_MS * 2)
                # Prove rolling-state EN/RU responsiveness across all four viewports against the committed real-backend request.
                exercise_matrix(page, evidence_dir, "rolling")
                # Release the server response only after every rolling assertion and representative image succeeds.
                release_file.write_text("release\n", encoding="utf-8")
                # Pump browser events for at most ten seconds until the released real response arrives.
                for _ in range(200):
                    # Stop polling as soon as the exact filtered response was recorded.
                    if roll_responses:
                        # Leave the bounded response wait immediately.
                        break
                    # Let Playwright process the pending network and page callback events.
                    page.wait_for_timeout(50)
                # Require the released production response before trusting any settled presentation.
                assert roll_responses, "Focused Chuck-a-Luck roll response did not arrive after release"
                # Parse the standard envelope returned by the real backend.
                payload = roll_responses[0].json()
                # Require the standard additive success envelope.
                assert payload["ok"] is True
                # Read the committed server-authoritative round once for reload checks.
                round_row = payload["data"]["round"]
                # Wait until the ordinary motion scope reveals the released committed result.
                page.locator('[data-testid="chuck-a-luck"][data-phase="settled"]').wait_for(timeout=60000)
                # Read the three displayed authoritative face values.
                displayed_dice = [int(value) for value in page.locator("[data-die]").evaluate_all("elements => elements.map(element => element.dataset.face)")]
                # Require the visual result to match the exact real-backend response.
                assert displayed_dice == round_row["dice"]
                # Prove settled-state EN/RU responsiveness across all four viewports.
                exercise_matrix(page, evidence_dir, "settled")
                # Reload the canonical route to prove player-owned state restoration.
                page.reload(wait_until="networkidle")
                # Wait for the restored settled state without issuing another wager.
                page.locator('[data-testid="chuck-a-luck"][data-phase="settled"]').wait_for(timeout=WAIT_MS * 2)
                # Read the restored dice after the real reload.
                restored_dice = [int(value) for value in page.locator("[data-die]").evaluate_all("elements => elements.map(element => element.dataset.face)")]
                # Require the reload to preserve the previously committed outcome.
                assert restored_dice == round_row["dice"]
                # Prove restored-route EN/RU responsiveness across all four viewports without creating another action.
                exercise_matrix(page, evidence_dir, "route_restored")
                # Force the platform reduced-motion preference for the next atomic action.
                page.emulate_media(reduced_motion="reduce")
                # Enter a new wager while preserving the same authenticated player.
                page.locator('[data-wager="two"]').fill("1")
                # Execute another real backend roll under reduced-motion presentation.
                with page.expect_response(lambda response: response.url.endswith("/api/v1/games/chuck-a-luck/rolls") and response.request.method == "POST"):
                    # Start the second atomic action through the visible control.
                    page.locator("[data-roll]").click()
                # Require the zero-delay shared motion callback to reach settlement.
                page.locator('[data-testid="chuck-a-luck"][data-phase="settled"][data-reduced-motion="true"]').wait_for(timeout=WAIT_MS * 2)
                # Capture representative reduced-motion evidence in both locales and two key viewports.
                for locale in LOCALE_TITLES:
                    # Switch locales without remounting the settled game state.
                    page.get_by_test_id("shell-locale-select").select_option(locale)
                    # Capture desktop and mobile reduced-motion states.
                    for viewport_id in ("desktop_primary", "mobile"):
                        # Apply the exact governed viewport size.
                        page.set_viewport_size(VIEWPORTS[viewport_id])
                        # Save optional focused evidence for this state.
                        capture(page, evidence_dir, "reduced_motion", locale, viewport_id)
                # Close Chromium before terminating the dedicated backend.
                browser.close()
        # Always stop the exact listener and remove the disposable runtime tree.
        finally:
            # Stop the child when launch reached process creation.
            closed = True if process is None else stop_server(process, port)
    # Fail the focused check if its dedicated listener did not close.
    assert closed, f"Focused listener {port} did not close"
    # Publish self-describing sidecars only after the browser pass and exact listener cleanup both succeed.
    if evidence_dir is not None:
        # Record branch, source commit, state, locale, viewport, and artifact path for every image.
        write_evidence_sidecars(evidence_dir)
    # Print only public cleanup metadata required by the coordinator handoff.
    print(f"Chuck-a-Luck browser check PASS; port={port}; pid={pid}; closed={str(closed).lower()}; protected_ports_8765_8877=untouched")


# Parse the optional evidence location and run the focused check directly.
def main(argv=None):
    # Define a single optional artifact output without changing default test behavior.
    parser = argparse.ArgumentParser()
    # Accept an explicit directory for branch-local after-pass screenshots.
    parser.add_argument("--evidence-dir")
    # Parse the focused browser arguments.
    args = parser.parse_args(argv)
    # Resolve the requested artifact directory when one was supplied.
    evidence_dir = Path(args.evidence_dir).resolve() if args.evidence_dir else None
    # Run the full real-backend browser check and listener cleanup proof.
    run_browser_check(evidence_dir)


# Execute the focused browser test when invoked as a script.
if __name__ == "__main__":
    # Delegate exit behavior to assertion and Playwright failures.
    main()
