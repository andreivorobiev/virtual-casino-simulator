"""Diagnostic real-browser smoke for issue #92, never formal after-pass evidence."""

# Import deep-copy support so the in-memory persistence adapter has reload semantics.
from copy import deepcopy
# Import cookie parsing for a minimal authenticated browser-session boundary.
from http.cookies import SimpleCookie
# Import the standard loopback HTTP server without starting the shared application.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# Import JSON encoding for API envelopes and locale fixtures.
import json
# Import process identity for the required listener cleanup record.
import os
# Import repository-relative path handling for actual browser assets.
from pathlib import Path
# Import sockets for proving the ephemeral listener is closed after the test.
import socket
# Import reentrant locking and a background server thread for isolated persistence.
import threading
# Import short polling delays used only while verifying listener closure.
import time
# Import the dependency-free test runner used by focused game checks.
import unittest
# Import URL parsing so static and API routes ignore query strings safely.
from urllib.parse import urlparse

# Import the shared additive-v1 router used by the production game adapter.
from casino.router import Router
# Import standard API errors for authentic response envelopes and fake ledger bounds.
from casino.errors import CasinoError, InsufficientFundsError
# Import the actual game API and engine under this issue's isolated ownership.
from casino.games.deuces_wild_video_poker import api as game_api, engine

# Resolve the repository root without depending on the caller's current directory.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
# Restrict every diagnostic listener and request to local loopback.
LOOPBACK_HOST = "127.0.0.1"
# Preserve the user's live Casino port by explicitly rejecting it even after port-zero selection.
PROTECTED_LIVE_PORT = 8765
# Name the test-only cookie that binds browser requests to one fake session player.
SESSION_COOKIE = "dwvp_diagnostic_session"
# Allow only the two locale-specific fake session players used by this diagnostic.
SESSION_PLAYERS = frozenset({"browser-en", "browser-ru"})

# Build one minimal route outlet that imports the actual locale and game modules.
DIAGNOSTIC_INDEX = (
"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deuces Wild diagnostic browser harness</title>
  <style>
    /* Keep the diagnostic route readable without importing shared shell styles. */
    html,body{margin:0;min-width:0;background:#061a12;color:#f7f3e8;font:16px/1.4 system-ui,sans-serif}
    /* Give the actual game module a bounded responsive route outlet. */
    #app{box-sizing:border-box;max-width:1440px;margin:0 auto;padding:16px;min-width:0}
  </style>
</head>
<body>
  <!-- Mount only the game-owned browser surface under test. -->
  <main id="app"></main>
  <!-- Retain the shared toast target so unexpected action failures remain observable. -->
  <div id="toast" role="status" hidden></div>
  <script type="module">
    // Import the actual shared locale runtime used by the application shell.
    import { initI18n } from '/core/i18n.js';
    // Import the actual issue #92 lazy game module rather than a copied fixture.
    import { DeucesWildVideoPokerGame } from '/games/deuces_wild_video_poker.js';
    // Supply a hostile caller id so the HTTP session binding can prove precedence.
    window.CasinoCurrentPlayer = { player_id: 'hostile-browser-player' };
    // Initialize the requested URL locale before game-owned resources are rendered.
    await initI18n({ domains: ['games/deuces_wild_video_poker'] });
    // Mount through the production lazy-module contract into the test route outlet.
    await DeucesWildVideoPokerGame.mount(document.getElementById('app'));
    // Expose a cleanup hook without changing the production module lifecycle.
    window.__dwvpDiagnosticUnmount = () => DeucesWildVideoPokerGame.unmount();
    // Mark the page ready only after state and wallet refresh requests have completed.
    window.__dwvpDiagnosticReady = true;
  </script>
</body>
</html>
"""
)

# Map browser paths to the actual game, shared primitives, and paired locale files.
STATIC_FILES = {
    "/games/deuces_wild_video_poker.js": REPOSITORY_ROOT / "web/games/deuces_wild_video_poker.js",  # Serve the real game module.
    "/core/api.js": REPOSITORY_ROOT / "web/core/api.js",  # Serve the real session-aware fetch helper.
    "/core/ui.js": REPOSITORY_ROOT / "web/core/ui.js",  # Serve the real shared UI helper.
    "/core/cards.js": REPOSITORY_ROOT / "web/core/cards.js",  # Serve the approved #96 card renderer.
    "/core/cards.css": REPOSITORY_ROOT / "web/core/cards.css",  # Serve the approved responsive card styles.
    "/core/i18n.js": REPOSITORY_ROOT / "web/core/i18n.js",  # Serve the real paired-locale runtime.
    "/i18n/manifest.json": REPOSITORY_ROOT / "web/i18n/manifest.json",  # Serve canonical locale metadata.
    "/i18n/en-US/common.json": REPOSITORY_ROOT / "web/i18n/en-US/common.json",  # Serve English common fallback copy.
    "/i18n/ru-RU/common.json": REPOSITORY_ROOT / "web/i18n/ru-RU/common.json",  # Serve Russian common fallback copy.
    "/i18n/en-US/games/deuces_wild_video_poker.json": REPOSITORY_ROOT / "web/i18n/en-US/games/deuces_wild_video_poker.json",  # Serve owned English copy.
    "/i18n/ru-RU/games/deuces_wild_video_poker.json": REPOSITORY_ROOT / "web/i18n/ru-RU/games/deuces_wild_video_poker.json",  # Serve owned Russian copy.
}


# Provide thread-safe in-memory state, wallet, and append-only ledger ports.
class InMemoryCasino:
    # Initialize isolated fake persistence without touching repository data paths.
    def __init__(self):
        # Serialize direct wallet reads with game-service ledger actions.
        self._lock = threading.RLock()
        # Store reload-safe state documents by game and authenticated player.
        self._states = {}
        # Give each fake session an independent play-token balance.
        self._balances = {player_id: 1000.0 for player_id in SESSION_PLAYERS}
        # Retain append-only ledger events for service recovery and assertions.
        self._events = []
        # Increment stable ledger identifiers inside this one diagnostic process.
        self._event_number = 0
        # Increment deterministic audit timestamps without reading wall-clock time.
        self._clock_number = 0

    # Load one player-game document as a persistence provider would after reload.
    def load_state(self, game_id, player_id, default_factory):
        # Serialize reads against state writes from the HTTP worker thread.
        with self._lock:
            # Read the stored document or create a fresh engine-owned default.
            state = self._states.get((game_id, player_id), default_factory())
            # Return a copy so callers must save every durable mutation explicitly.
            return deepcopy(state)

    # Save one complete player-game document without external filesystem effects.
    def save_state(self, game_id, player_id, state):
        # Serialize writes against reload and diagnostic assertion reads.
        with self._lock:
            # Persist a deep copy to model a real serialization boundary.
            self._states[(game_id, player_id)] = deepcopy(state)

    # Return one authenticated player's current fake-money wallet payload.
    def get_player(self, player_id):
        # Serialize wallet reads against debit and credit actions.
        with self._lock:
            # Create a conservative balance only for an unexpected bound test identity.
            balance = self._balances.setdefault(player_id, 1000.0)
            # Return the same shape consumed by the actual game and wallet helpers.
            return {"player_id": player_id, "balance": round(balance, 2)}

    # Read bounded append-only proof for the service's retry recovery scan.
    def read_ledger(self, player_id, limit):
        # Serialize scans against ledger appends.
        with self._lock:
            # Select only events owned by the authenticated player.
            owned = [event for event in self._events if event["player_id"] == player_id]
            # Return newest bounded proof without exposing mutable fake storage.
            return deepcopy(owned[-limit:])

    # Commit one game wager through the injected ledger-only debit port.
    def debit(self, player_id, amount, transaction_type, game_id, round_id, details):
        # Delegate signed movement creation to the common append-only helper.
        return self._move(player_id, -round(float(amount), 2), transaction_type, game_id, round_id, details)

    # Commit one returned-credit payout through the injected ledger-only credit port.
    def credit(self, player_id, amount, transaction_type, game_id, round_id, details):
        # Delegate signed movement creation to the common append-only helper.
        return self._move(player_id, round(float(amount), 2), transaction_type, game_id, round_id, details)

    # Append one strictly shaped ledger event and update the fake wallet atomically.
    def _move(self, player_id, signed_amount, transaction_type, game_id, round_id, details):
        # Serialize balance validation, movement, and append-only proof.
        with self._lock:
            # Read the current authenticated player's wallet balance.
            balance_before = self._balances.setdefault(player_id, 1000.0)
            # Reject a debit that would exceed the available fake-money balance.
            if signed_amount < 0 and balance_before < abs(signed_amount):
                # Raise the same public boundary as the shared production ledger.
                raise InsufficientFundsError()
            # Calculate the exact two-decimal wallet balance after movement.
            balance_after = round(balance_before + signed_amount, 2)
            # Increment a stable local ledger sequence.
            self._event_number += 1
            # Build every field validated by the actual issue #92 service.
            event = {
                "ledger_id": f"dwvp-browser-ledger-{self._event_number}",  # Identify append-only diagnostic proof.
                "player_id": player_id,  # Bind proof to the authenticated session player.
                "game": game_id,  # Bind proof to the isolated game id.
                "round_id": round_id,  # Bind proof to the stable game round.
                "transaction_type": transaction_type,  # Distinguish wager debit from payout credit.
                "amount": signed_amount,  # Store the signed token movement expected by recovery.
                "balance_before": balance_before,  # Preserve the audit starting balance.
                "balance_after": balance_after,  # Preserve the audit ending balance.
                "details": deepcopy(details),  # Preserve the service's idempotency fingerprint.
            }
            # Commit the new balance beside its append-only proof.
            self._balances[player_id] = balance_after
            # Retain an immutable-style copy for later service recovery.
            self._events.append(deepcopy(event))
            # Return a separate copy to model a storage-adapter response.
            return deepcopy(event)

    # Return monotonically increasing deterministic timestamps for round lifecycle fields.
    def clock(self):
        # Serialize timestamp allocation across HTTP action requests.
        with self._lock:
            # Increment the bounded diagnostic timestamp sequence.
            self._clock_number += 1
            # Return an ISO timestamp accepted by the production game service.
            return f"2026-07-14T00:00:{self._clock_number:02d}.000Z"

    # Return a copy of one stored state for post-browser session assertions.
    def state_for(self, player_id):
        # Serialize assertion reads against any last HTTP persistence write.
        with self._lock:
            # Return the authenticated player's stored game state when present.
            return deepcopy(self._states.get((engine.GAME_ID, player_id)))

    # Return one player's append-only events for diagnostic assertions.
    def events_for(self, player_id):
        # Reuse the complete bounded reader with the practical diagnostic limit.
        return self.read_ledger(player_id, 100)


# Resolve a deterministic content type for every explicitly served real asset.
def content_type(path):
    # Serve JavaScript modules with their browser-recognized MIME type.
    if path.endswith(".js"):
        # Return a UTF-8 JavaScript content type.
        return "text/javascript; charset=utf-8"
    # Serve style imports with the required CSS MIME type.
    if path.endswith(".css"):
        # Return a UTF-8 stylesheet content type.
        return "text/css; charset=utf-8"
    # Serve locale resources and API-like fixtures as JSON.
    if path.endswith(".json"):
        # Return a UTF-8 JSON content type.
        return "application/json; charset=utf-8"
    # Fall back to plain binary bytes for an unexpected explicit asset extension.
    return "application/octet-stream"


# Build one HTTP handler bound to the actual game router and in-memory ports.
def handler_for(router, backend, http_errors):
    # Define a closure-owned handler so no shared application globals are changed.
    class DiagnosticHandler(BaseHTTPRequestHandler):
        # Suppress default access logging so only listener evidence reaches test output.
        def log_message(self, _format, *_args):
            # Return without writing nondeterministic HTTP log timestamps.
            return

        # Resolve the fake authenticated player from a same-origin session cookie.
        def _bound_player(self):
            # Parse the request cookie header through the standard cookie implementation.
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            # Read the diagnostic session value when the browser supplied it.
            morsel = cookies.get(SESSION_COOKIE)
            # Extract the candidate without trusting arbitrary cookie values.
            candidate = morsel.value if morsel is not None else ""
            # Return only an explicitly provisioned authenticated test player.
            return candidate if candidate in SESSION_PLAYERS else "browser-anonymous"

        # Send one complete response and record every non-success status.
        def _send_bytes(self, status, payload, media_type):
            # Record status failures for the final no-HTTP-errors assertion.
            if status >= 400:
                # Preserve the method, path, and status without response-body secrets.
                http_errors.append(f"{self.command} {self.path} -> {status}")
            # Emit the selected HTTP status.
            self.send_response(status)
            # Identify response bytes for browser module and JSON parsing.
            self.send_header("Content-Type", media_type)
            # Prevent browser caching from hiding repeat resource requests.
            self.send_header("Cache-Control", "no-store")
            # Publish the exact response length before writing bytes.
            self.send_header("Content-Length", str(len(payload)))
            # Complete the response header section.
            self.end_headers()
            # Write content only when the response is not empty.
            if payload:
                # Send all encoded response bytes to the browser.
                self.wfile.write(payload)

        # Serialize a standard success or error envelope as UTF-8 JSON.
        def _send_json(self, status, payload):
            # Preserve paired-locale characters while encoding the API document.
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            # Send the JSON document through the common response boundary.
            self._send_bytes(status, encoded, "application/json; charset=utf-8")

        # Parse one JSON action body without introducing form or multipart behavior.
        def _read_json(self):
            # Read the declared body size defensively.
            length = int(self.headers.get("Content-Length") or 0)
            # Return an empty object for read-only or empty action requests.
            if length == 0:
                # Match the shared handler's normalized empty-body behavior.
                return {}
            # Read the exact body bytes supplied by the browser fetch helper.
            raw = self.rfile.read(length)
            # Decode and parse the expected UTF-8 JSON request.
            return json.loads(raw.decode("utf-8"))

        # Dispatch a browser request through the actual game Router and service.
        def _handle_api(self):
            # Parse the route path while preserving the raw query for Router dispatch.
            path = urlparse(self.path).path
            # Resolve the only session-authorized player for this request.
            player_id = self._bound_player()
            # Start standard API error handling around actual game dispatch.
            try:
                # Read JSON only for mutation requests.
                body = self._read_json() if self.command == "POST" else {}
                # Serve the shared wallet refresh shape from the same bound fake player.
                if path.startswith("/api/v1/players/"):
                    # Ignore the hostile path id and return only session-bound wallet state.
                    data = {"player": backend.get_player(player_id)}
                # Route game endpoints through the actual additive-v1 adapter.
                else:
                    # Provide an authenticated binding that overrides body and query ids.
                    context = {"bound_player_id": player_id, "user": {"player_id": player_id}}
                    # Dispatch through the shared Router with the untouched request URL.
                    data = router.dispatch(self.command, self.path, body, context)
                # Wrap successful actual-service data in the frozen standard envelope.
                self._send_json(200, {"ok": True, "data": data})
            # Preserve public game errors and their declared HTTP status.
            except CasinoError as error:
                # Return the standard failure envelope without changing the error contract.
                self._send_json(error.status, {"ok": False, "error": {"code": error.code, "message": error.message, "details": error.details}})
            # Surface an unexpected diagnostic harness error as an observable HTTP failure.
            except Exception as error:
                # Return a bounded diagnostic message so Playwright records the failure.
                self._send_json(500, {"ok": False, "error": {"code": "DIAGNOSTIC_ERROR", "message": str(error), "details": {}}})

        # Serve the diagnostic route outlet and explicitly mapped real assets.
        def _serve_static(self):
            # Parse the static path independently from locale query parameters.
            path = urlparse(self.path).path
            # Serve the single diagnostic HTML route.
            if path in {"/", "/index.html"}:
                # Encode the test-only route outlet as UTF-8 HTML.
                payload = DIAGNOSTIC_INDEX.encode("utf-8")
                # Return the page without using the shared application listener.
                self._send_bytes(200, payload, "text/html; charset=utf-8")
                # Stop after the route outlet response is complete.
                return
            # Return an empty successful favicon response if Chromium requests one.
            if path == "/favicon.ico":
                # Avoid an irrelevant browser-console 404 in the diagnostic.
                self._send_bytes(204, b"", "image/x-icon")
                # Stop after the optional icon response is complete.
                return
            # Resolve only an explicitly permitted actual repository asset.
            target = STATIC_FILES.get(path)
            # Reject every path outside the game and required shared assets.
            if target is None or not target.is_file():
                # Return a visible failure so missing module dependencies fail the smoke.
                self._send_bytes(404, b"not found", "text/plain; charset=utf-8")
                # Stop after the missing-resource response is complete.
                return
            # Read the exact current repository file bytes.
            payload = target.read_bytes()
            # Serve the asset using a strict browser-compatible content type.
            self._send_bytes(200, payload, content_type(path))

        # Route GET requests to actual APIs or explicit real assets.
        def do_GET(self):
            # Detect API paths without interpreting untrusted query values.
            if urlparse(self.path).path.startswith("/api/"):
                # Dispatch the read through the actual game adapter.
                self._handle_api()
                # Stop after the API envelope is complete.
                return
            # Serve the diagnostic page or one explicitly mapped dependency.
            self._serve_static()

        # Route POST requests through the actual game adapter.
        def do_POST(self):
            # Dispatch the mutation and standard envelope response.
            self._handle_api()

    # Return the closure-bound handler class for one ephemeral server instance.
    return DiagnosticHandler


# Start one non-live ephemeral loopback listener and record its exact identity.
def start_harness(router, backend):
    # Collect every server-side HTTP status failure for post-browser assertions.
    http_errors = []
    # Build a handler that cannot reach shared application state.
    handler = handler_for(router, backend, http_errors)
    # Retry port-zero allocation only if the protected live port is ever selected.
    for _attempt in range(10):
        # Ask the operating system for an available loopback ephemeral port.
        server = ThreadingHTTPServer((LOOPBACK_HOST, 0), handler)
        # Read the selected port before starting its background thread.
        port = int(server.server_address[1])
        # Keep the server only when it cannot collide with the user's live session.
        if port != PROTECTED_LIVE_PORT:
            # Stop retrying after a safe ephemeral allocation.
            break
        # Close an accidentally protected allocation before selecting another port.
        server.server_close()
    # Fail explicitly if repeated operating-system allocations selected the live port.
    else:
        # Raise before any background listener exists.
        raise RuntimeError("Could not allocate a non-8765 diagnostic port")
    # Allow individual request handlers to exit with the bounded diagnostic process.
    server.daemon_threads = True
    # Run the isolated HTTP loop without blocking the Playwright test thread.
    thread = threading.Thread(target=server.serve_forever, name="dwvp-diagnostic-http", daemon=True)
    # Begin accepting loopback browser requests.
    thread.start()
    # Record the required PID and exact non-live port in direct test output.
    print(f"DWVP_DIAGNOSTIC_LISTENER_START pid={os.getpid()} host={LOOPBACK_HOST} port={port}", flush=True)
    # Return every lifecycle object needed for deterministic teardown.
    return server, thread, port, http_errors


# Poll briefly until a closed loopback listener refuses new connections.
def listener_is_closed(port):
    # Allow a bounded number of retries for the server thread to release its socket.
    for _attempt in range(40):
        # Create a short-lived IPv4 TCP probe.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            # Bound each connection attempt so teardown cannot hang.
            probe.settimeout(0.05)
            # Treat any connection refusal as proof the listener is closed.
            if probe.connect_ex((LOOPBACK_HOST, port)) != 0:
                # Return immediately after closure is observed.
                return True
        # Yield briefly before checking a still-open socket again.
        time.sleep(0.025)
    # Report failure when the listener accepted connections throughout the bound window.
    return False


# Attach error collectors to one real browser page before navigation.
def watch_page(page, browser_errors):
    # Record error-level console messages without treating ordinary logs as failures.
    def on_console(message):
        # Preserve only messages that indicate executable browser failure.
        if message.type == "error":
            # Record the console text for a focused assertion diagnostic.
            browser_errors.append(f"console: {message.text}")

    # Record uncaught JavaScript exceptions from module loading or event handlers.
    def on_page_error(error):
        # Preserve the browser exception without interrupting cleanup callbacks.
        browser_errors.append(f"pageerror: {error}")

    # Record network failures that never produced an HTTP response.
    def on_request_failed(request):
        # Preserve the failed URL and browser-reported reason.
        browser_errors.append(f"requestfailed: {request.url} {request.failure}")

    # Record non-success HTTP responses visible to the browser.
    def on_response(response):
        # Ignore success, redirects, and the intentional empty favicon response.
        if response.status >= 400:
            # Preserve the failing resource URL and status code.
            browser_errors.append(f"response: {response.status} {response.url}")

    # Subscribe before navigation so module-load failures cannot be missed.
    page.on("console", on_console)
    # Subscribe to uncaught browser execution errors.
    page.on("pageerror", on_page_error)
    # Subscribe to connection and request-abort failures.
    page.on("requestfailed", on_request_failed)
    # Subscribe to observable HTTP error statuses.
    page.on("response", on_response)


# Exercise the actual game module through a real browser and isolated real API adapter.
class DeucesWildVideoPokerDiagnosticBrowserTests(unittest.TestCase):
    # Open one authenticated locale page with optional narrow and reduced-motion settings.
    def open_page(self, browser, base_url, player_id, locale, viewport, browser_errors, *, reduced_motion=False):
        # Create an isolated browser context for one authenticated fake user.
        context = browser.new_context(viewport=viewport)
        # Bind subsequent same-origin API requests to the selected session player.
        context.add_cookies([{"name": SESSION_COOKIE, "value": player_id, "url": base_url}])
        # Create the actual page after authentication state is installed.
        page = context.new_page()
        # Emulate the user's reduced-motion preference before styles are evaluated.
        if reduced_motion:
            # Activate the standard reduced-motion media feature.
            page.emulate_media(reduced_motion="reduce")
        # Attach failure collectors before loading any real module asset.
        watch_page(page, browser_errors)
        # Navigate to the diagnostic route while selecting the requested display locale.
        page.goto(f"{base_url}/?locale={locale}", wait_until="networkidle")
        # Wait until mount, state load, locale load, and wallet refresh all complete.
        page.wait_for_function("window.__dwvpDiagnosticReady === true")
        # Return both lifecycle objects so the caller can unmount and close explicitly.
        return context, page

    # Cover English mount, deal, hold, draw, and terminal settlement UI.
    def exercise_english(self, browser, base_url, strings, browser_errors):
        # Open the desktop English page as its own authenticated fake player.
        context, page = self.open_page(browser, base_url, "browser-en", "en-US", {"width": 1280, "height": 900}, browser_errors)
        # Ensure browser resources are released even if an assertion fails.
        try:
            # Verify the locale runtime publishes correct document metadata.
            self.assertEqual("en-US", page.locator("html").get_attribute("lang"))
            # Verify the owned localized heading is visibly mounted.
            self.assertTrue(page.get_by_role("heading", name=strings["title"], exact=True).is_visible())
            # Verify the initial phase uses owned English resource copy.
            self.assertEqual(strings["phases.ready"], page.locator(".dwvp-phase").inner_text())
            # Enter an over-limit wager to exercise local validation before action allocation.
            page.locator("#dwvp-wager").fill("100001")
            # Attempt the invalid deal through the visible primary control.
            page.get_by_role("button", name=strings["controls.deal"], exact=True).click()
            # Wait for paired game-owned validation feedback outside the rerendered route root.
            page.get_by_text(strings["errors.invalidWager"], exact=True).wait_for()
            # Verify no source hand or ledger-backed action was created for invalid input.
            self.assertEqual(0, page.locator("[data-hold-position]").count())
            # Verify the wager remains editable instead of becoming pinned until reload.
            self.assertTrue(page.locator("#dwvp-wager").is_enabled())
            # Correct the same control to a valid one-token wager without reloading.
            page.locator("#dwvp-wager").fill("1")
            # Start one actual ledger-backed deal through the browser control.
            page.get_by_role("button", name=strings["controls.deal"], exact=True).click()
            # Wait until all five source-card action buttons are available.
            page.wait_for_selector("[data-hold-position]")
            # Verify the actual deterministic backend returned a complete source hand.
            self.assertEqual(5, page.locator("[data-hold-position]").count())
            # Build the localized first-card hold action name from the resource placeholder.
            hold_label = strings["cards.hold"].replace("{position}", "1")
            # Verify the visible card action exposes the localized ARIA name.
            self.assertEqual(hold_label, page.locator('[data-hold-position="0"]').get_attribute("aria-label"))
            # Verify the shared card primitive receives an owned localized accessible label.
            card_label = page.locator('[data-hold-position="0"] [role="img"]').get_attribute("aria-label")
            # Confirm the English card label is complete and contains no replacement glyph.
            self.assertTrue(card_label and " of " in card_label and "�" not in card_label)
            # Toggle the first card through the actual holds API.
            page.locator('[data-hold-position="0"]').click()
            # Build the localized release action expected after persistence.
            release_label = strings["cards.release"].replace("{position}", "1")
            # Wait until the actual reload-safe hold response rerenders the card.
            page.get_by_role("button", name=release_label, exact=True).wait_for()
            # Verify selection state is conveyed beyond color.
            self.assertEqual("true", page.locator('[data-hold-position="0"]').get_attribute("aria-pressed"))
            # Verify the localized held marker is visibly rendered.
            self.assertIn(strings["cards.held"], page.locator('[data-hold-position="0"]').inner_text())
            # Complete the hand through the actual draw and ledger payout path.
            page.get_by_role("button", name=strings["controls.draw"], exact=True).click()
            # Wait for terminal summary rendering after archived state returns.
            page.wait_for_selector('[data-testid="dwvp-summary"]')
            # Verify settled cards are non-interactive final content.
            self.assertEqual(0, page.locator("[data-hold-position]").count())
            # Verify all five final cards remain visibly rendered.
            self.assertEqual(5, page.locator(".dwvp-final-card").count())
            # Verify the terminal summary region exposes its owned accessible name.
            self.assertEqual(strings["summary.title"], page.locator('[data-testid="dwvp-summary"]').get_attribute("aria-label"))
            # Verify persisted-settlement guidance is visible after the actual draw.
            self.assertIn(strings["stage.settledPrompt"], page.locator('[data-testid="deuces-wild-video-poker"]').inner_text())
            # Verify the terminal phase resolves to one of the three localized aggregate outcomes.
            self.assertIn(page.locator(".dwvp-phase").inner_text(), {strings["phases.win"], strings["phases.push"], strings["phases.loss"]})
        # Always unmount and close the English browser context.
        finally:
            # Release the actual game module's locale subscription when possible.
            page.evaluate("window.__dwvpDiagnosticUnmount?.()")
            # Close all page resources owned by this locale context.
            context.close()

    # Cover Russian visible/ARIA copy, narrow layout, and reduced-motion behavior.
    def exercise_russian(self, browser, base_url, strings, english_strings, browser_errors):
        # Open a compact Russian page with the platform reduced-motion preference active.
        context, page = self.open_page(browser, base_url, "browser-ru", "ru-RU", {"width": 390, "height": 844}, browser_errors, reduced_motion=True)
        # Ensure browser resources are released even if an assertion fails.
        try:
            # Verify the locale runtime publishes Russian document metadata.
            self.assertEqual("ru-RU", page.locator("html").get_attribute("lang"))
            # Verify the owned Russian heading is visibly mounted.
            self.assertTrue(page.get_by_role("heading", name=strings["title"], exact=True).is_visible())
            # Verify the initial phase uses the paired Russian resource.
            self.assertEqual(strings["phases.ready"], page.locator(".dwvp-phase").inner_text())
            # Read the computed responsive grid after the narrow media query applies.
            columns = page.locator(".dwvp-layout").evaluate("node => getComputedStyle(node).gridTemplateColumns")
            # Verify controls, stage, and paytable collapse to one narrow column.
            self.assertEqual(1, len(columns.split()))
            # Verify the page does not introduce horizontal viewport overflow.
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            # Verify Chromium exposes the requested reduced-motion media state.
            self.assertTrue(page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
            # Start a second actual deal under the independent Russian session.
            page.get_by_role("button", name=strings["controls.deal"], exact=True).click()
            # Wait for the localized five-card hold surface.
            page.wait_for_selector("[data-hold-position]")
            # Verify the source-hand region receives paired Russian ARIA copy.
            self.assertEqual(strings["stage.sourceHand"], page.locator('[data-testid="dwvp-hand"]').get_attribute("aria-label"))
            # Build the localized first-card action name from its placeholder resource.
            hold_label = strings["cards.hold"].replace("{position}", "1")
            # Verify hold interaction uses Russian accessible copy.
            self.assertEqual(hold_label, page.locator('[data-hold-position="0"]').get_attribute("aria-label"))
            # Read the owned localized card description from the shared card primitive.
            card_label = page.locator('[data-hold-position="0"] [role="img"]').get_attribute("aria-label")
            # Verify Russian card copy neither falls back to English syntax nor corrupts glyphs.
            self.assertTrue(card_label and " of " not in card_label and "�" not in card_label)
            # Select the first card through the actual holds API.
            page.locator('[data-hold-position="0"]').click()
            # Build the expected Russian release action after persistence.
            release_label = strings["cards.release"].replace("{position}", "1")
            # Wait for the localized selected-state action to rerender.
            page.get_by_role("button", name=release_label, exact=True).wait_for()
            # Read reduced-motion style properties from the selected shared card.
            motion = page.locator('[data-hold-position="0"] .playing-card').evaluate("node => ({transition:getComputedStyle(node).transitionDuration,animation:getComputedStyle(node).animationName,transform:getComputedStyle(node).transform})")
            # Verify all decorative card transitions are disabled.
            self.assertEqual("0s", motion["transition"])
            # Verify no keyframe animation is active.
            self.assertEqual("none", motion["animation"])
            # Verify the shared selected-card lift is removed for reduced motion.
            self.assertEqual("none", motion["transform"])
            # Complete the Russian hand through the actual draw endpoint.
            page.get_by_role("button", name=strings["controls.draw"], exact=True).click()
            # Wait for the localized terminal settlement summary.
            page.wait_for_selector('[data-testid="dwvp-summary"]')
            # Verify terminal summary ARIA copy comes from the Russian resource.
            self.assertEqual(strings["summary.title"], page.locator('[data-testid="dwvp-summary"]').get_attribute("aria-label"))
            # Verify the completed hand region receives Russian ARIA copy.
            self.assertEqual(strings["stage.finalHand"], page.locator('[data-testid="dwvp-hand"]').get_attribute("aria-label"))
            # Read all game-owned visible text after settlement.
            russian_text = page.locator('[data-testid="deuces-wild-video-poker"]').inner_text()
            # Verify the Russian page contains its owned settlement guidance.
            self.assertIn(strings["stage.settledPrompt"], russian_text)
            # Verify representative owned English strings do not leak into the Russian surface.
            self.assertNotIn(english_strings["title"], russian_text)
            # Verify the localized surface contains no Unicode replacement glyphs.
            self.assertNotIn("�", russian_text)
            # Recheck horizontal containment after the denser summary becomes visible.
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        # Always unmount and close the Russian browser context.
        finally:
            # Release the actual game module's locale subscription when possible.
            page.evaluate("window.__dwvpDiagnosticUnmount?.()")
            # Close all page resources owned by this locale context.
            context.close()

    # Run the complete diagnostic and prove its non-live listener is cleaned up.
    def test_real_browser_diagnostic(self):
        # Import Playwright lazily so focused non-browser suites can collect without it.
        try:
            # Import the synchronous runtime and its typed launch error.
            from playwright.sync_api import Error as PlaywrightError, sync_playwright
        # Mark the diagnostic unavailable when the optional dependency is absent.
        except ImportError as error:
            # Report a focused skip without weakening non-browser validation.
            self.skipTest(f"Playwright is not installed: {error}")
        # Load actual English copy for exact visible and accessible assertions.
        english_strings = json.loads(STATIC_FILES["/i18n/en-US/games/deuces_wild_video_poker.json"].read_text(encoding="utf-8"))
        # Load actual Russian copy for exact visible and accessible assertions.
        russian_strings = json.loads(STATIC_FILES["/i18n/ru-RU/games/deuces_wild_video_poker.json"].read_text(encoding="utf-8"))
        # Create isolated in-memory persistence, wallet, and ledger ports.
        backend = InMemoryCasino()
        # Create a fresh shared Router without importing the shared application registry.
        router = Router()
        # Build the actual service against only in-memory diagnostic adapters.
        service = game_api.DeucesWildVideoPokerService(
            load_state=backend.load_state,  # Inject reload-safe in-memory state reads.
            save_state=backend.save_state,  # Inject reload-safe in-memory state writes.
            debit=backend.debit,  # Inject append-only fake-money wager debits.
            credit=backend.credit,  # Inject append-only fake-money payout credits.
            read_ledger=backend.read_ledger,  # Inject retry-recovery ledger scans.
            get_player=backend.get_player,  # Inject authenticated wallet reads.
            clock=backend.clock,  # Inject deterministic lifecycle timestamps.
            seed_factory=lambda _action_id: "issue-92-browser-diagnostic",  # Inject one deterministic complete card plan.
        )
        # Register only the actual issue #92 additive-v1 routes.
        game_api.register(router, service=service)
        # Start the isolated non-8765 loopback harness.
        server, server_thread, port, http_errors = start_harness(router, backend)
        # Build the same-origin diagnostic base URL from the selected ephemeral port.
        base_url = f"http://{LOOPBACK_HOST}:{port}"
        # Collect browser console, execution, network, and response failures.
        browser_errors = []
        # Track the launched browser so cleanup handles launch and assertion failures.
        browser = None
        # Start protected browser execution with mandatory server teardown.
        try:
            # Own the Playwright driver lifecycle for this single diagnostic.
            with sync_playwright() as playwright:
                # Attempt to launch the installed bundled Chromium browser.
                try:
                    # Launch a real headless Chromium process without shared browser state.
                    browser = playwright.chromium.launch(headless=True)
                # Distinguish a missing browser binary from a browser-test failure.
                except PlaywrightError as error:
                    # Read the stable launch diagnostic once for availability detection.
                    diagnostic = str(error)
                    # Skip only when Playwright explicitly reports an absent executable.
                    if "Executable doesn't exist" in diagnostic:
                        # Report that the optional Chromium payload is unavailable.
                        self.skipTest(f"Playwright Chromium is not installed: {diagnostic.splitlines()[0]}")
                    # Re-raise every other launch failure for real diagnosis.
                    raise
                # Exercise desktop English gameplay through actual modules and endpoints.
                self.exercise_english(browser, base_url, english_strings, browser_errors)
                # Exercise compact Russian gameplay and accessibility behavior.
                self.exercise_russian(browser, base_url, russian_strings, english_strings, browser_errors)
                # Close Chromium after both locale contexts have closed.
                browser.close()
                # Clear the reference so the outer cleanup does not close twice.
                browser = None
            # Verify no hostile caller-controlled player state was ever created.
            self.assertIsNone(backend.state_for("hostile-browser-player"))
            # Verify both authenticated sessions reached terminal reload-safe state.
            for player_id in sorted(SESSION_PLAYERS):
                # Preserve the authenticated identity in assertion diagnostics.
                with self.subTest(player_id=player_id):
                    # Read the session's stored state after its real browser draw.
                    state = backend.state_for(player_id)
                    # Verify exactly one completed round was archived per locale session.
                    self.assertEqual(1, len(state["recent_rounds"]))
                    # Read append-only ledger proof produced by the actual service.
                    events = backend.events_for(player_id)
                    # Verify every browser session committed its wager through the ledger port.
                    self.assertGreaterEqual(len(events), 1)
                    # Verify the first movement is the required aggregate wager debit.
                    self.assertEqual("DWVP_WAGER_DEBIT", events[0]["transaction_type"])
                    # Verify every movement remains bound to the issue #92 game id.
                    self.assertTrue(all(event["game"] == engine.GAME_ID for event in events))
            # Verify the browser observed no console, execution, network, or HTTP errors.
            self.assertEqual([], browser_errors)
            # Verify the loopback handler produced no failing HTTP status.
            self.assertEqual([], http_errors)
        # Always stop Chromium and the isolated loopback listener.
        finally:
            # Close Chromium if an assertion or availability path left it open.
            if browser is not None:
                # Release the browser process before stopping its backing listener.
                browser.close()
            # Stop accepting new diagnostic HTTP connections.
            server.shutdown()
            # Close the loopback listening socket.
            server.server_close()
            # Wait briefly for the background server loop to exit.
            server_thread.join(timeout=5)
            # Probe the exact prior port until it refuses new connections.
            closed = listener_is_closed(port)
            # Record listener teardown evidence with the same PID and port.
            print(f"DWVP_DIAGNOSTIC_LISTENER_STOP pid={os.getpid()} host={LOOPBACK_HOST} port={port} closed={str(closed).lower()}", flush=True)
            # Fail if the serving thread survived explicit shutdown.
            self.assertFalse(server_thread.is_alive(), "diagnostic HTTP thread did not stop")
            # Fail if the exact ephemeral port still accepts connections.
            self.assertTrue(closed, f"diagnostic listener remained open on {LOOPBACK_HOST}:{port}")


# Run only this diagnostic when invoked directly by the bounded issue #92 worker.
if __name__ == "__main__":
    # Exit through unittest's standard result and skip handling.
    unittest.main()
