"""Real-browser isolated-surface verification for issue #87 without claiming backend acceptance."""

# Import a partial helper so the static server can be rooted at the repository.
from functools import partial
# Import the standard library HTTP server for one loopback-only ephemeral listener.
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
# Import JSON support for mocked standard-envelope API responses.
import json
# Import process identity for explicit listener evidence.
import os
# Import pathlib so static paths resolve independently of the caller directory.
from pathlib import Path
# Import sockets for final listener-closure verification.
import socket
# Import threading so the static server can run beside synchronous browser automation.
import threading
# Import URL parsing for request-path routing.
from urllib.parse import urlparse

# Import Playwright from the bundled workspace runtime.
from playwright.sync_api import sync_playwright

# Resolve the repository root from this game-specific test path.
ROOT = Path(__file__).resolve().parents[3]
# Define every visual-standard viewport used by the isolated overflow smoke.
VIEWPORTS = {
    # Preserve the authoritative primary desktop dimensions.
    "desktop_primary": {"width": 1920, "height": 1080},
    # Preserve the authoritative compact desktop dimensions.
    "desktop_compact": {"width": 1440, "height": 900},
    # Preserve the authoritative tablet dimensions.
    "tablet": {"width": 1024, "height": 900},
    # Preserve the authoritative mobile dimensions.
    "mobile": {"width": 390, "height": 844},
}


# Silence static HTTP logs so validation output contains only named evidence.
class QuietHandler(SimpleHTTPRequestHandler):
    # Map the production web-root i18n URL into this repository-root static harness.
    def translate_path(self, path):
        # Read the request path without locale query parameters.
        request_path = urlparse(path).path
        # Branch when shared i18n uses its production absolute resource root.
        if request_path.startswith("/i18n/"):
            # Serve the same file from the repository's web root.
            return str(ROOT / "web" / request_path.lstrip("/"))
        # Delegate module, harness, and other static files to the rooted base handler.
        return super().translate_path(path)

    # Ignore routine request logging from the local test harness.
    def log_message(self, _format, *args):
        # Return without emitting paths or noisy access lines.
        return


# Build one masked or settled public card for mocked browser rendering only.
def public_card(wager, revealed, status, pending_client_request_id=None):
    # Store a deterministic private winning board inside the mock callback only.
    prizes = [wager, wager, wager, wager * 2, wager * 2, wager * 5, wager * 5, wager * 10, wager * 10]
    # Build server-shaped public cells with covered prizes omitted completely.
    cells = [{"position": position, "revealed": position in revealed, **({"prize": prizes[position]} if position in revealed else {})} for position in range(9)]
    # Build the common masked card fields used in every browser phase.
    card = {"card_id": "scr_0123456789abcdef01234567", "status": status, "wager": wager, "cells": cells, "revealed_count": len(revealed), "cell_count": 9, "purchased_at": "2026-07-14T00:00:00Z"}
    # Publish the exact retry identity only for a crash-interrupted purchase fixture.
    if status == "purchasing" and pending_client_request_id:
        # Mirror the production reload field without exposing any private prize.
        card["pending_client_request_id"] = pending_client_request_id
    # Publish terminal payout data only after every cell is revealed.
    if status == "settled":
        # Add the deterministic winning outcome used by the UI smoke.
        card.update({"payout": wager, "net": 0.0, "outcome": "win", "settled_at": "2026-07-14T00:00:01Z"})
    # Return the masked browser fixture.
    return card


# Build one complete state payload around an optional current card.
def state_payload(card=None):
    # Return the exact public state fields consumed by the game module.
    return {"game": "scratch_cards", "current_card": card, "recent_cards": [], "wager_options": [1.0, 2.0, 5.0, 10.0], "rules": {"cell_count": 9, "match_count": 3}}


# Install one page-local fake backend that preserves standard envelopes and masked values.
def install_backend(page, initial_state=None):
    # Store current public state per browser page.
    backend = {"state": initial_state or state_payload(), "start_requests": []}

    # Fulfill one API request through the isolated deterministic browser fixture.
    def handle(route, request):
        # Parse only the request path for stable endpoint matching.
        path = urlparse(request.url).path
        # Return authenticated current-user data for shared wallet refreshes.
        if path == "/api/v2/me":
            # Build one current-user payload with play-token balance.
            data = {"user": {"id": "browser-user"}, "player": {"player_id": "browser-player", "token_balance": 1000}}
        # Return the current masked Scratch Cards state.
        elif path == "/api/v1/games/scratch-cards/state":
            # Reuse the page-local public state without hidden values.
            data = backend["state"]
        # Start one deterministic masked card through the standard action shape.
        elif path == "/api/v1/games/scratch-cards/cards":
            # Parse the public action body without trusting a player id for fixture selection.
            body = json.loads(request.post_data or "{}")
            # Retain exact public purchase content for reload-identity assertions.
            backend["start_requests"].append(body)
            # Build a fully covered card at the requested wager.
            card = public_card(float(body["wager"]), set(), "ready")
            # Persist the masked card for later state and reveal requests.
            backend["state"] = state_payload(card)
            # Return standard game-owned action data with no real ledger fixture.
            data = {"card": card, "state": backend["state"], "replayed": False, "ledger": {"wager": None, "payout": None}}
        # Persist one partial or complete reveal action.
        elif path.endswith("/scratches"):
            # Parse the normalized position set posted by the real browser module.
            body = json.loads(request.post_data or "{}")
            # Read already visible positions from public page-local state.
            existing = {cell["position"] for cell in backend["state"]["current_card"]["cells"] if cell["revealed"]}
            # Union the requested reveal positions for reload-safe fixture behavior.
            revealed = existing | set(body["positions"])
            # Select terminal state only after every position is public.
            status = "settled" if len(revealed) == 9 else "scratching"
            # Preserve the wager already committed by the mocked start action.
            wager = backend["state"]["current_card"]["wager"]
            # Build a response that still omits every covered prize.
            card = public_card(wager, revealed, status)
            # Persist the new masked state for future actions.
            backend["state"] = state_payload(card)
            # Return the standard game-owned action shape.
            data = {"card": card, "state": backend["state"], "replayed": False, "ledger": {"wager": None, "payout": None}}
        # Fail unexpected API paths so the test cannot silently miss integration drift.
        else:
            # Return a standard not-found envelope for diagnosis.
            route.fulfill(status=404, content_type="application/json", body=json.dumps({"ok": False, "error": {"code": "NOT_FOUND", "message": "fixture path not found"}}))
            # Stop after fulfilling the unexpected path.
            return
        # Fulfill successful requests through the canonical ok/data envelope.
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True, "data": data}))

    # Intercept only API calls while static modules and locale JSON use the loopback server.
    page.route("**/api/**", handle)
    # Return page-local request evidence to focused lifecycle checks.
    return backend


# Assert one locale and viewport render without keys, clipping, or layout drift.
def verify_surface(browser, base_url, locale, viewport_id):
    # Create one isolated page at the authoritative viewport dimensions.
    page = browser.new_page(viewport=VIEWPORTS[viewport_id])
    # Install the deterministic masked API fixture before navigation.
    install_backend(page)
    # Enable reduced motion so the CSS accessibility branch is exercised.
    page.emulate_media(reduced_motion="reduce")
    # Navigate to the isolated browser harness with manifest-driven locale selection.
    page.goto(f"{base_url}/tests/games/scratch_cards/harness.html?locale={locale}", wait_until="networkidle")
    # Wait for locale, state, module, and shared wallet work to complete.
    page.wait_for_selector("[data-testid='scratch-cards']")
    # Resolve the localized title expected for this page.
    expected_title = "Scratch Cards" if locale == "en-US" else "Скретч-карты"
    # Read the visible title once for localized failure diagnostics.
    actual_title = page.locator("h1").inner_text()
    # Verify the visible game title is fully localized.
    assert actual_title == expected_title, f"unexpected title at {locale} {viewport_id}: {actual_title!r}"
    # Verify no raw resource-key prefix is visible.
    visible_text = page.locator("[data-testid='scratch-cards']").inner_text()
    # Reject common key prefixes, undefined values, and replacement characters.
    assert not any(marker in visible_text for marker in ("controls.", "stage.", "undefined", "null", "�"))
    # Verify page-level horizontal overflow is absent.
    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    # Fail the named viewport if any game-owned content widens the page.
    assert overflow is False, f"horizontal overflow at {locale} {viewport_id}"
    # Start one real-browser masked card through the module's public action.
    page.locator("[data-action='start']").click()
    # Wait for all nine semantic covered cells.
    page.wait_for_selector("[data-testid='scratch-cell-8']")
    # Wait for post-commit wallet refresh and the final enabled render.
    page.wait_for_function("document.querySelector('[data-testid=\"scratch-cell-0\"]')?.disabled === false")
    # Verify covered buttons expose no prize text or numeric token amount.
    assert page.locator(".scratch-cell.is-covered .scratch-prize").count() == 0
    # Verify the completed start action moves keyboard focus to the first safe reveal control.
    start_focus = page.evaluate("({tag:document.activeElement?.tagName,action:document.activeElement?.dataset?.action,position:document.activeElement?.dataset?.scratchPosition,focusId:document.activeElement?.dataset?.focusId})")
    # Require the first covered cell and include exact active-element evidence on failure.
    assert start_focus.get("position") == "0", f"unexpected post-start focus: {start_focus}"
    # Verify the first cell has a localized nonempty accessible name.
    first_name = page.locator("[data-testid='scratch-cell-0']").get_attribute("aria-label")
    # Reject raw key leakage in the accessible name.
    assert first_name and "stage." not in first_name
    # Verify reduced-motion CSS removes decorative transitions.
    transition_duration = page.locator("[data-testid='scratch-cell-0']").evaluate("element => getComputedStyle(element).transitionDuration")
    # Require a zero-duration transition under the emulated preference.
    assert transition_duration == "0s"
    # Reveal one cell through its semantic button.
    page.locator("[data-testid='scratch-cell-0']").click()
    # Wait for the server-authorized prize to appear.
    page.wait_for_selector("[data-testid='scratch-cell-0'].is-revealed")
    # Verify exactly one prize is public after the partial action.
    assert page.locator(".scratch-cell.is-revealed .scratch-prize").count() == 1
    # Verify focus advances deterministically after the initiating cell becomes disabled.
    reveal_focus = page.evaluate("({tag:document.activeElement?.tagName,action:document.activeElement?.dataset?.action,position:document.activeElement?.dataset?.scratchPosition,focusId:document.activeElement?.dataset?.focusId})")
    # Require the next covered cell and include exact active-element evidence on failure.
    assert reveal_focus.get("position") == "1", f"unexpected post-reveal focus: {reveal_focus}"
    # Reveal every remaining position through the stable primary action.
    page.locator("[data-action='reveal-all']").click()
    # Wait for the terminal winning phase and all nine prizes.
    page.wait_for_function("document.querySelectorAll('.scratch-cell.is-revealed .scratch-prize').length === 9")
    # Verify the current card reports a localized terminal result.
    assert page.locator(".scratch-result").inner_text().strip()
    # Measure panel layout for desktop dominance or narrow stacking order.
    layout = page.evaluate("""() => { const controls=document.querySelector('.scratch-controls').getBoundingClientRect(); const stage=document.querySelector('.scratch-stage').getBoundingClientRect(); const details=document.querySelector('.scratch-details').getBoundingClientRect(); return {controlsWidth:controls.width,stageWidth:stage.width,detailsWidth:details.width,controlsTop:controls.top,stageTop:stage.top,detailsTop:details.top}; }""")
    # Require the stage to exceed both support rails combined at desktop primary.
    if viewport_id == "desktop_primary":
        # Enforce the authoritative visual hierarchy gate.
        assert layout["stageWidth"] > layout["controlsWidth"] + layout["detailsWidth"]
    # Require controls, stage, and data to stack in journey order on tablet and mobile.
    if viewport_id in {"tablet", "mobile"}:
        # Enforce control-first document scrolling order.
        assert layout["controlsTop"] < layout["stageTop"] < layout["detailsTop"]
    # Unmount explicitly so locale subscription and cached state cleanup run in-browser.
    page.evaluate("window.ScratchCardsHarness.game.unmount()")
    # Close the isolated page after lifecycle verification.
    page.close()


# Assert a full browser remount reuses the server-published pending purchase identity.
def verify_purchase_recovery(browser, base_url):
    # Create one isolated desktop page for the lifecycle-specific recovery path.
    page = browser.new_page(viewport=VIEWPORTS["desktop_compact"])
    # Build a fully masked purchasing card with one durable retry identity.
    pending_card = public_card(5.0, set(), "purchasing", "persisted-start-87")
    # Install the initial reload state and capture exact outgoing purchase requests.
    backend = install_backend(page, state_payload(pending_card))
    # Navigate like a fresh route mount with no in-memory pendingStartId.
    page.goto(f"{base_url}/tests/games/scratch_cards/harness.html?locale=en-US", wait_until="networkidle")
    # Wait until automatic recovery returns a funded ready card with actionable cells.
    page.wait_for_function("document.querySelector('[data-testid=\"scratch-cell-0\"]')?.disabled === false")
    # Verify recovery issued exactly one purchase request.
    assert len(backend["start_requests"]) == 1
    # Read the exact request sent by the newly mounted frontend.
    request = backend["start_requests"][0]
    # Require the persisted identity and wager instead of a new browser-generated action.
    assert (request.get("client_request_id"), request.get("wager")) == ("persisted-start-87", 5.0)
    # Unmount explicitly so lifecycle cleanup is exercised after recovery.
    page.evaluate("window.ScratchCardsHarness.game.unmount()")
    # Close the focused recovery page.
    page.close()


# Run the complete loopback-only browser smoke and prove listener cleanup.
def main():
    # Bind a static server only to loopback on an operating-system-selected ephemeral port.
    handler = partial(QuietHandler, directory=str(ROOT))
    # Create the ephemeral listener without touching reserved port 8765.
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    # Allow request worker threads to end automatically during shutdown.
    server.daemon_threads = True
    # Read the selected ephemeral port for evidence and navigation.
    port = server.server_address[1]
    # Start the local static server beside synchronous browser automation.
    thread = threading.Thread(target=server.serve_forever, name="scratch-cards-browser", daemon=True)
    # Begin serving only after listener identity is fully known.
    thread.start()
    # Print exact PID and port as required listener evidence.
    print(f"SCRATCH_BROWSER_LISTENER pid={os.getpid()} port={port} host=127.0.0.1")
    # Build the loopback origin used by every isolated browser page.
    base_url = f"http://127.0.0.1:{port}"
    # Start protected browser work so the listener always closes.
    try:
        # Launch the bundled headless browser through Playwright.
        with sync_playwright() as playwright:
            # Launch Chromium without a visible interactive window.
            browser = playwright.chromium.launch(headless=True)
            # Verify the crash/reload purchase path once with exact request evidence.
            verify_purchase_recovery(browser, base_url)
            # Exercise both locales at every authoritative viewport.
            for locale in ("en-US", "ru-RU"):
                # Exercise desktop primary, compact, tablet, and mobile layouts.
                for viewport_id in VIEWPORTS:
                    # Verify the complete isolated surface at this locale and viewport.
                    verify_surface(browser, base_url, locale, viewport_id)
            # Close the headless browser before releasing the static listener.
            browser.close()
    # Always stop the test listener even if a browser assertion fails.
    finally:
        # Stop accepting loopback requests and wait for the server loop.
        server.shutdown()
        # Release the underlying ephemeral socket.
        server.server_close()
        # Join the server thread so no background work survives the test.
        thread.join(timeout=5)
        # Create one short-lived probe socket for closure evidence.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bound the final connection attempt so cleanup cannot hang.
        probe.settimeout(1)
        # Verify the formerly selected port refuses new connections.
        closed = probe.connect_ex(("127.0.0.1", port)) != 0
        # Release the probe socket immediately.
        probe.close()
        # Print explicit closure evidence for the issue handoff.
        print(f"SCRATCH_BROWSER_LISTENER_CLOSED pid={os.getpid()} port={port} closed={str(closed).lower()}")
        # Fail the test if the exact listener remains reachable.
        assert closed, f"scratch browser listener {port} remained open"
    # Report the complete locale and viewport matrix after successful cleanup.
    print("Scratch Cards isolated browser checks passed for purchase reload plus 2 locales x 4 viewports.")


# Execute the focused browser smoke only when invoked directly.
if __name__ == "__main__":
    # Run through explicit process assertions and cleanup handling.
    main()
