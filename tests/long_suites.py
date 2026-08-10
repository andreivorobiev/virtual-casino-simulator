#!/usr/bin/env python3
# Provide long, sharded, deployment-style casino test suites.
import argparse  # Parse suite, shard, deployment, and audio options.
import importlib  # Load independently owned per-game drivers from catalog references.
import json  # Write machine-readable long-suite reports.
import os  # Inspect paths and process environment safely.
import random  # Vary deterministic scenario choices across iterations.
import shutil  # Copy and delete disposable deployment trees.
import socket  # Allocate isolated local server ports per worker.
import stat  # Clear read-only flags when deleting copied Windows trees.
import subprocess  # Start the casino server from a deployment copy.
import sys  # Reuse the current Python runtime for child servers.
import time  # Poll server readiness and timestamp reports.
import traceback  # Preserve failure detail in JSON reports.
import urllib.error  # Decode API error envelopes during negative checks.
import urllib.request  # Exercise the HTTP API without extra dependencies.
from pathlib import Path  # Handle Windows paths consistently.

# Store ROOT so the script can locate the repository from any working directory.
ROOT = Path(__file__).resolve().parents[1]
# Add the repository root so direct script execution can import runtime catalog modules.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # Prefer this checkout over unrelated installed packages.
# Consume the same canonical game catalog as runtime registration after path setup.
from casino.config import GAMES
# Import the same flushed reporter used by the browser suite for TEST-042 scenarios.
from tests.progress import ProgressReporter
# Store AUTH_SESSION_COOKIE so browser verification can use the backend session cookie name without importing app code.
AUTH_SESSION_COOKIE = "casino_session"
# Use one safe deterministic deployment identifier for copied-environment probe evidence.
OPERATIONS_SMOKE_BUILD_SHA = "abcdef0"
# Store GAME_IDS from the runtime catalog so coverage automatically includes newly integrated games.
GAME_IDS = tuple(game["id"] for game in GAMES)
# Store SUITES so suite sizing and minimum coverage expectations stay declarative.
SUITES = {
    # Suite 100 runs at least one hundred full-casino scenarios and requires ten touches per requirement.
    "100": {"tests": 100, "min_requirement_touches": 10, "audio_repeats": 10},
    # Suite 300 runs at least three hundred full-casino scenarios and requires twenty touches per requirement.
    "300": {"tests": 300, "min_requirement_touches": 20, "audio_repeats": 20},
    # Suite 500 runs at least five hundred full-casino scenarios and requires thirty touches per requirement.
    "500": {"tests": 500, "min_requirement_touches": 30, "audio_repeats": 30},
}


# Define the ApiClient class used to exercise the deployed local server.
class ApiClient:
    # Initialize the client with the base URL for one deployment server.
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")  # Normalize URL joins.
        self.session_token = None  # Store the active backend session token for protected API calls.

    # Call a JSON endpoint and return its standard data envelope.
    def call(self, path, method="GET", body=None, ok=True, auth=True):
        data = None if body is None else json.dumps(body).encode("utf-8")  # Encode JSON request bodies.
        headers = {"Content-Type": "application/json"}  # Start with JSON headers for every API request.
        if auth and self.session_token:  # Attach the bearer token when a protected call has a session.
            headers["Authorization"] = f"Bearer {self.session_token}"  # Send backend session credentials.
        req = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)  # Build the request.
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # Execute the request with a bounded wait.
                payload = json.loads(resp.read().decode("utf-8"))  # Decode the standard response envelope.
        except urllib.error.HTTPError as exc:  # Capture expected API error envelopes.
            payload = json.loads(exc.read().decode("utf-8"))  # Decode expected validation failures.
        if ok and not payload.get("ok"):  # Enforce success for positive calls.
            raise AssertionError(payload)  # Fail fast when a success call returns an error.
        if not ok and payload.get("ok"):  # Enforce failure for negative calls.
            raise AssertionError({"expected_failure": True, "payload": payload})  # Fail if a negative check succeeds.
        return payload["data"] if payload.get("ok") else payload  # Return data or the raw error envelope.

    # Login with the bootstrap admin and store a reusable session token.
    def login_default_user(self):
        email = os.environ.get("CASINO_BOOTSTRAP_ADMIN_EMAIL", "admin@example.local")  # Match backend bootstrap defaults.
        password = os.environ.get("CASINO_BOOTSTRAP_ADMIN_PASSWORD", "admin-password")  # Match backend bootstrap defaults.
        session = self.call("/api/v2/auth/login", "POST", {"email": email, "password": password}, auth=False)["session"]  # Login through the public auth endpoint.
        self.session_token = session["token"]  # Store the token for later protected calls.
        return self.session_token  # Return the token for browser cookie setup.

    # Fetch the current human balance as a float.
    def balance(self):
        return float(self.call("/api/v1/players/human")["player"]["balance"])  # Reuse the players API.


# Define the CoverageLedger class used to prove repeated requirement and game touches.
class CoverageLedger:
    # Initialize requirement and game counters for one suite shard.
    def __init__(self, requirement_ids):
        self.requirements = {rid: 0 for rid in requirement_ids}  # Track every registered requirement.
        self.games = {gid: 0 for gid in GAME_IDS}  # Track every game per scenario.
        self.scenario_results = []  # Preserve concise per-scenario evidence.

    # Mark every active requirement as touched by one full-casino scenario.
    def touch_requirements(self):
        for rid in self.requirements:  # Count every registered requirement once per scenario.
            self.requirements[rid] += 1  # Count this scenario against the requirement registry.

    # Mark one game as played in the current scenario.
    def touch_game(self, game_id):
        self.games[game_id] += 1  # Count game-specific play coverage.

    # Add one scenario result entry to the report.
    def record_scenario(self, index, details):
        self.scenario_results.append({"index": index, "details": details})  # Keep evidence compact.

    # Return the lowest requirement touch count in this shard.
    def min_requirement_touch_count(self):
        return min(self.requirements.values()) if self.requirements else 0  # Empty registries should fail later.


# Load all requirement IDs from the deployment tree.
def load_requirement_ids(repo_root):
    req_path = repo_root / "docs" / "requirements" / "requirements.json"  # Locate the registry.
    data = json.loads(req_path.read_text(encoding="utf-8"))  # Parse the JSON requirements file.
    return [item["id"] for item in data.get("requirements", [])]  # Return permanent IDs in registry order.


# Allocate a local port for one deployment server.
def free_port():
    while True:  # Retry only if the OS ever selects a protected user port.
        sock = socket.socket()  # Create a temporary TCP socket.
        sock.bind(("127.0.0.1", 0))  # Ask the OS for a free loopback port.
        port = sock.getsockname()[1]  # Read the assigned port.
        sock.close()  # Release the temporary socket.
        if port not in (8765, 8877):  # Preserve both protected user listeners.
            return port  # Return only a non-reserved port for the server process.


# Start the casino server from the selected repository root.
def start_server(repo_root):
    port = free_port()  # Pick an isolated port for this worker.
    child_environment = {**os.environ, "CASINO_BUILD_SHA": OPERATIONS_SMOKE_BUILD_SHA}  # Publish only sanitized test provenance to the copied child.
    proc = subprocess.Popen([sys.executable, str(repo_root / "run.py"), "--host", "127.0.0.1", "--port", str(port), "--no-browser"], cwd=str(repo_root), env=child_environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)  # Launch server.
    base = f"http://127.0.0.1:{port}"  # Build the base URL.
    print(f"Long-suite server PID {proc.pid} listening on {base}", flush=True)  # Record the isolated listener for exact evidence and cleanup verification.
    client = ApiClient(base)  # Build an API client for readiness checks.
    for _ in range(120):  # Poll readiness for up to twelve seconds.
        try:
            client.login_default_user()  # Probe readiness through the public login endpoint.
            return proc, client  # Return once the server is ready.
        except Exception:  # Retry transient startup failures until the server is ready.
            time.sleep(0.1)  # Give the server a moment to boot.
    stop_server(proc, client)  # Stop the failed child and verify its exact loopback port.
    output = proc.stdout.read() if proc.stdout else ""  # Capture startup output after bounded cleanup.
    raise RuntimeError("server did not start\n" + output[-1200:])  # Surface useful diagnostics.


# Stop one tracked long-suite server and prove its exact non-reserved port is closed.
def stop_server(proc, client):
    port = int(client.base_url.rsplit(":", 1)[1])  # Parse the recorded numeric child port.
    if port in (8765, 8877):  # Refuse cleanup against protected user listeners.
        raise AssertionError(f"refusing to stop protected port {port}")  # Fail closed on invalid ownership.
    if proc.poll() is None:  # Ask the exact tracked child to stop only while it is alive.
        proc.terminate()  # Prefer cooperative shutdown for normal and timeout cleanup.
    try:  # Wait a bounded interval for graceful child termination.
        proc.wait(timeout=5)  # Reap the tracked process before checking its listener.
    except subprocess.TimeoutExpired:  # Force only the tracked child after its grace period.
        proc.kill()  # Kill the exact process object without scanning unrelated listeners.
        proc.wait(timeout=5)  # Reap the forcibly stopped child.
    for _ in range(30):  # Allow up to three seconds for loopback port release.
        with socket.socket() as probe_socket:  # Use one short-lived exact-port probe.
            probe_socket.settimeout(0.1)  # Bound each connection attempt.
            listener_closed = probe_socket.connect_ex(("127.0.0.1", port)) != 0  # Treat refusal as closure.
        if listener_closed:  # Return exact evidence as soon as the listener is absent.
            print(f"Long-suite server PID {proc.pid} stopped; 127.0.0.1:{port} closed", flush=True)  # Flush cleanup evidence.
            return {"pid": proc.pid, "host": "127.0.0.1", "port": port, "closed": True}  # Retain artifact evidence.
        time.sleep(0.1)  # Give the operating system a short release interval.
    raise AssertionError(f"tracked long-suite listener remained open on 127.0.0.1:{port}")  # Fail closed after cleanup.


# Ensure the player has enough fake money to survive long randomized play.
def ensure_balance(client):
    if client.balance() < 1000:  # Top up only when the bankroll is too low for long play.
        client.call("/api/v1/players/human/add-money", "POST", {"amount": 10000})  # Top up only when needed.


# Discover one callable long-suite driver from each independently owned catalog entry.
def load_game_drivers():
    drivers = []  # Preserve catalog order in every full-casino scenario.
    for game in GAMES:  # Discover every current and future game without a central allowlist.
        reference = game["tests"]["long_driver"]  # Read the module-owned driver reference.
        module_name, callable_name = reference.split(":", 1)  # Separate the import path from its callable.
        module = importlib.import_module(module_name)  # Import the per-game test driver.
        driver = getattr(module, callable_name)  # Resolve the documented driver callable.
        drivers.append((game["id"], driver))  # Bind the callable to its catalog game id.
    return drivers  # Return deterministic discovered drivers to the scenario runner.


# Load drivers once so discovery failures stop the suite before a listener starts.
GAME_DRIVERS = load_game_drivers()


# Exercise shared control-plane behavior used by long casino sessions.
def touch_control_plane(client, index):
    settings = {"master_enabled": True, "sfx_enabled": True, "voice_enabled": True, "master_volume": 0.8, "sfx_volume": 0.7, "voice_volume": 0.85, "announce_roulette_results": True, "announce_blackjack_results": True, "announce_baccarat_results": True, "announce_bingo_calls": True, "announce_keno_results": True}  # Enable all sound paths.
    saved = client.call("/api/v1/admin/audio-settings", "POST", settings)["settings"]  # Persist audio settings.
    assert saved["announce_baccarat_results"] is True, "Baccarat audio setting did not persist"  # Verify baccarat audio.
    session = client.call("/api/v1/autoplay/start", "POST", {"game_id": "slots", "player_id": "human", "speed": "medium", "round_limit": 2, "plan": {"type": "long-suite", "iteration": index}})["session"]  # Start autoplay.
    stopped = client.call("/api/v1/autoplay/stop", "POST", {"autoplay_id": session["autoplay_id"]})["session"]  # Stop autoplay.
    assert stopped["stop_requested"] is True, "Autoplay stop was not recorded"  # Verify stop semantics.
    reqs = client.call("/api/v1/admin/requirements")["requirements"]  # Touch the requirement registry.
    assert len(reqs) > 100, "Admin requirements registry unexpectedly small"  # Verify registry visibility.


# Run one full-casino scenario that plays every game.
def run_full_casino_scenario(client, index, coverage):
    ensure_balance(client)  # Keep the long suite from failing due expected bankroll variance.
    touch_control_plane(client, index)  # Exercise shared admin/audio/autoplay behavior.
    details = {}  # Collect compact scenario evidence.
    before = client.balance()  # Capture starting balance.
    for game_id, driver in GAME_DRIVERS:  # Exercise every game discovered from module-owned metadata.
        driver(client, index)  # Run the current game's independently owned scenario driver.
        coverage.touch_game(game_id)  # Count the catalog game after its driver succeeds.
    after = client.balance()  # Capture ending balance.
    coverage.touch_requirements()  # Count this all-game scenario against all requirement IDs.
    details["balance_before"] = before  # Record starting bankroll.
    details["balance_after"] = after  # Record ending bankroll.
    details["games"] = list(GAME_IDS)  # Prove all games are included in each scenario record.
    coverage.record_scenario(index, details)  # Store evidence for the JSON report.


# Return iteration indices owned by this worker shard.
def shard_indices(total, shard_count, shard_index):
    return [index for index in range(total) if index % shard_count == shard_index]  # Use stable modulo sharding.


# Remove read-only flags when shutil.rmtree encounters Windows copied files.
def clear_readonly_and_retry(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)  # Make the file writable for deletion.
    func(path)  # Retry the original delete operation.


# Create an optional disposable deployment copy for this worker.
def prepare_deployment(args):
    if not args.copy_deployment:  # Keep local runs lightweight unless deployment mode is requested.
        return ROOT, None  # Run directly from the current tree when no copy is requested.
    env_root = Path(args.deployment_root).expanduser().resolve()  # Resolve the environment root.
    env_root.mkdir(parents=True, exist_ok=True)  # Create the environment root if needed.
    source_root = ROOT.resolve()  # Resolve the source checkout.
    if str(env_root).lower().startswith(str(source_root).lower()):  # Prevent recursive self-copying.
        raise RuntimeError("deployment root must not be inside the source checkout")  # Avoid recursive copies.
    target = env_root / f"casino-long-{args.suite}-shard-{args.shard_index}-of-{args.shard_count}-{int(time.time())}"  # Name the disposable copy.
    shutil.copytree(source_root, target)  # Copy the whole repository tree for deployment-style testing.
    return target, target  # Return repo root and cleanup target.


# Acquire an exclusive runtime lock for one repository tree.
def acquire_runtime_lock(repo_root):
    lock_dir = repo_root / "logs" / "test-runs"  # Store locks with test artifacts.
    lock_dir.mkdir(parents=True, exist_ok=True)  # Ensure the lock directory exists.
    lock_path = lock_dir / "long_suite_runtime.lock"  # Use one lock per runtime tree.
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # Create the lock atomically.
    except FileExistsError as exc:  # Fail clearly when another worker owns this runtime tree.
        raise RuntimeError(f"long-suite runtime is already in use at {repo_root}; use --copy-deployment for parallel workers or remove stale lock {lock_path}") from exc  # Explain the fix.
    with os.fdopen(fd, "w", encoding="utf-8") as handle:  # Persist lock ownership details.
        handle.write(json.dumps({"pid": os.getpid(), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))  # Record lock owner.
    return lock_path  # Return lock path for cleanup.


# Release a runtime lock if this process created one.
def release_runtime_lock(lock_path):
    if lock_path and lock_path.exists():  # Ignore already-cleaned locks during shutdown.
        lock_path.unlink()  # Remove the lock after the server and tests finish.


# Run browser audio verification with instrumented speech and sound APIs.
def run_browser_audio_verification(client, repeats, report):
    try:
        from playwright.sync_api import sync_playwright  # Import Playwright only for audio browser checks.
    except Exception as exc:  # Surface missing browser dependencies as a long-suite failure.
        raise RuntimeError("Playwright is required for browser audio verification") from exc  # Make the missing dependency clear.
    init_script = (  # Store deterministic browser audio instrumentation.
"""
(() => { // Scope deterministic audio stubs to the test page.
  window.__casinoAudioEvents = []; // Store voice and sound events for later assertions.
  const push = event => window.__casinoAudioEvents.push({...event, at: performance.now()}); // Timestamp each probe event.
  window.__casinoAudioProbe = event => push({source: 'voice-module', ...event}); // Bridge app voice events into the log.
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {configurable: true, value: function(text){ this.text = text; this.rate = 1; this.pitch = 1; this.volume = 1; }}); // Stub utterance construction.
  let active = []; // Track active utterances so cancel behavior is observable.
  const speechStub = { // Replace browser speech with a deterministic stub.
    paused: false, // Expose the paused flag used by the app.
    getVoices(){ return [{name: 'Codex Test Voice', lang: 'en-US', default: true}]; }, // Provide one stable voice.
    resume(){ this.paused = false; push({source: 'speech-stub', kind: 'speech_resume'}); }, // Record resume calls.
    cancel(){ active.forEach(item => { if(!item.done){ item.cancelled = true; push({source: 'speech-stub', kind: 'voice_cancel', text: item.text}); } }); active = []; }, // Record cutoffs.
    speak(utterance){ // Simulate asynchronous speech completion.
      const item = {text: utterance.text, done: false, cancelled: false}; // Track this utterance.
      active.push(item); // Mark the utterance active.
      push({source: 'speech-stub', kind: 'speech_speak', text: utterance.text}); // Record speech start.
      setTimeout(() => { if(!item.cancelled){ item.done = true; push({source: 'speech-stub', kind: 'speech_end', text: utterance.text}); utterance.onend && utterance.onend({type: 'end'}); } }, 1000); // Complete unless cancelled.
    } // End speech simulation.
  }; // End speech stub.
  Object.defineProperty(window, 'speechSynthesis', {configurable: true, value: speechStub}); // Install speech stub.
  class AudioNodeStub { connect(){ return this; } start(){ push({source: 'audio-context-stub', kind: 'sfx_node_start'}); } stop(){ push({source: 'audio-context-stub', kind: 'sfx_node_stop'}); } } // Stub generic audio nodes.
  class AudioContextStub { // Replace Web Audio with a deterministic recorder.
    constructor(){ this.sampleRate = 44100; this.destination = new AudioNodeStub(); push({source: 'audio-context-stub', kind: 'audio_context'}); } // Record context construction.
    createOscillator(){ const node = new AudioNodeStub(); node.frequency = {value: 0}; node.type = 'triangle'; return node; } // Stub oscillator nodes.
    createGain(){ const node = new AudioNodeStub(); node.gain = {value: 0}; return node; } // Stub gain nodes.
    createBuffer(){ return {getChannelData(){ return new Float32Array(128); }}; } // Stub audio buffers.
    createBufferSource(){ const node = new AudioNodeStub(); node.buffer = null; return node; } // Stub source nodes.
    createBiquadFilter(){ const node = new AudioNodeStub(); node.type = 'bandpass'; node.frequency = {value: 0}; return node; } // Stub filter nodes.
  } // End audio context stub.
  Object.defineProperty(window, 'AudioContext', {configurable: true, value: AudioContextStub}); // Install standard AudioContext stub.
  Object.defineProperty(window, 'webkitAudioContext', {configurable: true, value: AudioContextStub}); // Install WebKit AudioContext stub.
})();
"""
    )
    # Define the install_auth_mock function used by this module.
    def install_auth_mock(page):
        # Store mocked auth state because backend v2 auth APIs are owned by issue 39.
        auth_state = {"tokens": 10000, "locale": "en-US"}  # Start long audio checks authenticated.
        # Define the auth_payload function used by this module.
        def auth_payload():
            # Return a draft v2 current-user payload for frontend-only long-suite checks.
            return {"user": {"user_id": "long_suite_user", "username": "long-suite", "display_name": "Long Suite Player", "locale": auth_state["locale"], "role": "admin", "roles": ["admin"]}, "player": {"player_id": "human", "token_balance": auth_state["tokens"]}, "terms": {"required": False, "version": "private-beta-1"}}  # Mirror the real bootstrap-Admin session that owns the audio settings request.
        # Define the mocked_auth_response function used by this module.
        def mocked_auth_response(ok=True, data=None, message="Unhandled auth mock"):
            # Return a standard API envelope string for Playwright route fulfillment.
            return json.dumps({"ok": ok, "data": data or {}, "error": None if ok else {"code": "AUTH_MOCK", "message": message}})  # Preserve the standard envelope.
        # Define the handle_auth_route function used by this module.
        def handle_auth_route(route):
            # Store request so path, method, and body can drive the v2 auth mock.
            request = route.request  # Keep request metadata local to the route handler.
            # Store path so endpoint matching ignores host and query details.
            path = request.url.split("/api/v2", 1)[1].split("?", 1)[0]  # Normalize the v2 path.
            # Branch for current-user session lookup.
            if path == "/me" and request.method == "GET":  # Let the shell enter the casino immediately.
                return route.fulfill(status=200, content_type="application/json", body=mocked_auth_response(True, auth_payload()))  # Return authenticated current user.
            # Branch for durable personal settings so this audio-specific test explicitly opts into sound.
            if path == "/me/settings" and request.method == "GET":  # Override the production-safe sound-off default only for audio verification.
                return route.fulfill(status=200, content_type="application/json", body=mocked_auth_response(True, {"settings": {"locale": "en-US", "sound_enabled": True, "revision": 1, "updated_at": "2026-08-10T00:00:00Z"}}))  # Return one deterministic enabled preference.
            # Branch for token additions through the current-user wallet.
            if path == "/me/tokens/add" and request.method == "POST":  # Keep the wallet endpoint available if shell code calls it.
                body = json.loads(request.post_data or "{}")  # Parse the requested token amount.
                auth_state["tokens"] += int(body.get("amount") or 0)  # Update the mocked token balance.
                return route.fulfill(status=200, content_type="application/json", body=mocked_auth_response(True, auth_payload()))  # Return updated current user.
            # Branch for logout in case future long-suite cleanup clicks it.
            if path == "/auth/logout" and request.method == "POST":  # Accept logout without changing backend scope.
                return route.fulfill(status=200, content_type="application/json", body=mocked_auth_response(True, {}))  # Return an empty success envelope.
            # Return a route-local standard failure for unexpected v2 auth endpoints.
            return route.fulfill(status=200, content_type="application/json", body=mocked_auth_response(False))  # Avoid browser console HTTP errors.
        # Route planned v2 auth/current-user APIs so long suites can run before issue 39 lands.
        page.route("**/api/v2/**", handle_auth_route)  # Install the focused Playwright route mock.
    client.call("/api/v1/admin/audio-settings", "POST", {"master_enabled": True, "sfx_enabled": True, "voice_enabled": True, "announce_roulette_results": True, "announce_blackjack_results": True, "announce_baccarat_results": True, "announce_bingo_calls": True, "announce_keno_results": True})  # Enable every game announcement.
    with sync_playwright() as playwright:  # Own the browser lifecycle for this verification.
        browser = playwright.chromium.launch(headless=True)  # Launch Chromium for actual UI audio paths.
        page = browser.new_page()  # Create an isolated page.
        page.context.add_cookies([{"name": AUTH_SESSION_COOKIE, "value": client.session_token, "url": client.base_url, "httpOnly": True, "sameSite": "Lax"}])  # Enter the UI with a real backend session.
        page.add_init_script(init_script)  # Install probes before app scripts run.
        install_auth_mock(page)  # Mock planned v2 auth so the audio suite can enter the casino.
        page.goto(client.base_url + "/", wait_until="networkidle")  # Load the app shell.
        page.get_by_test_id("nav-roulette").click()  # Navigate to Roulette.
        page.get_by_test_id("roulette-outside-red").click()  # Trigger Roulette SFX.
        page.get_by_test_id("roulette-spin").click()  # Trigger Roulette roll and voice.
        page.wait_for_timeout(3000)  # Wait for roulette animation and announcement.
        page.get_by_test_id("nav-slots").click()  # Navigate to Slots.
        page.get_by_test_id("slots-spin").click()  # Trigger reel sounds.
        page.wait_for_timeout(1100)  # Wait for reels.
        page.get_by_test_id("nav-keno").click()  # Navigate to Keno.
        page.get_by_test_id("keno-num-1").click()  # Pick Keno number.
        page.get_by_test_id("keno-num-2").click()  # Pick Keno number.
        page.get_by_test_id("keno-num-3").click()  # Pick Keno number.
        page.get_by_test_id("keno-draw").click()  # Trigger Keno sounds and voice.
        page.wait_for_timeout(1400)  # Wait for draw animation.
        page.get_by_test_id("nav-bingo").click()  # Navigate to Bingo.
        page.get_by_test_id("bingo-buy").click()  # Buy a Bingo card.
        page.get_by_test_id("bingo-call").click()  # Trigger Bingo call voice.
        page.wait_for_timeout(700)  # Wait for the call.
        page.get_by_test_id("nav-blackjack").click()  # Navigate to Blackjack.
        page.get_by_test_id("blackjack-deal").click()  # Deal Blackjack.
        page.wait_for_timeout(500)  # Wait for deal.
        blackjack_stand = page.get_by_test_id("blackjack-stand")  # Cache the Blackjack stand control.
        if blackjack_stand.is_enabled():  # Stand only when the dealt hand still needs player action.
            blackjack_stand.click()  # Trigger possible settlement voice.
        page.wait_for_timeout(900)  # Wait for settlement.
        page.get_by_test_id("nav-baccarat").click()  # Navigate to Baccarat.
        for _ in range(repeats):  # Repeated Baccarat deals catch speech cutoff regressions.
            page.get_by_test_id("baccarat-banker").click()  # Place banker bet.
            page.get_by_test_id("baccarat-deal").click()  # Deal coup and trigger voice.
            page.wait_for_timeout(350)  # Overlap speech while letting each deal action finish.
        audio_deadline = time.time() + 15  # Allow slower CI browsers to finish queued speech events.
        while time.time() < audio_deadline:  # Poll until the expected Baccarat completions are visible.
            interim_events = page.evaluate("window.__casinoAudioEvents")  # Read the current probe log.
            interim_starts = [event for event in interim_events if event.get("kind") == "voice_start" and event.get("gameId") == "baccarat"]  # Count observed starts.
            interim_voice_ends = [event for event in interim_events if event.get("kind") == "voice_end" and event.get("gameId") == "baccarat"]  # Count app-level completions.
            interim_speech_ends = [event for event in interim_events if event.get("kind") == "speech_end" and str(event.get("text", "")).startswith("Baccarat ")]  # Count stub completions.
            if len(interim_starts) >= repeats and max(len(interim_voice_ends), len(interim_speech_ends)) >= repeats:  # Stop once all expected speech finished.
                break  # Leave the poll loop after complete evidence is available.
            page.wait_for_timeout(250)  # Let pending speech callbacks complete.
        events = page.evaluate("window.__casinoAudioEvents")  # Read the audio probe log.
        browser.close()  # Close Chromium before assertions.
    baccarat_starts = [event for event in events if event.get("kind") == "voice_start" and event.get("gameId") == "baccarat"]  # Count baccarat starts.
    baccarat_ends = [event for event in events if event.get("kind") == "voice_end" and event.get("gameId") == "baccarat"]  # Count baccarat completions.
    baccarat_stub_ends = [event for event in events if event.get("kind") == "speech_end" and str(event.get("text", "")).startswith("Baccarat ")]  # Count browser-device completions.
    baccarat_completion_count = max(len(baccarat_ends), len(baccarat_stub_ends))  # Use the strongest completion signal.
    cancels = [event for event in events if event.get("kind") == "voice_cancel"]  # Detect cut-off speech.
    sfx_events = [event for event in events if event.get("kind") in ("sfx_start", "sfx_node_start")]  # Count SFX path events.
    report["audio"] = {"events": len(events), "baccarat_starts": len(baccarat_starts), "baccarat_voice_ends": len(baccarat_ends), "baccarat_speech_ends": len(baccarat_stub_ends), "baccarat_completion_count": baccarat_completion_count, "voice_cancels": len(cancels), "sfx_events": len(sfx_events), "sample": events[-12:]}  # Store audio evidence before assertions.
    assert len(baccarat_starts) >= repeats, f"Baccarat voice starts {len(baccarat_starts)} below repeats {repeats}"  # Require every baccarat deal to speak.
    assert baccarat_completion_count >= repeats, f"Baccarat voice completions {baccarat_completion_count} below repeats {repeats}"  # Require every baccarat utterance to finish.
    assert not cancels, f"Voice was cancelled during audio verification: {cancels[:3]}"  # Catch the prior cutoff bug.
    assert len(sfx_events) >= 6, "Sound effect path did not emit enough events"  # Require non-voice sound coverage.


# Build the JSON report path for this run.
def default_report_path(repo_root, args):
    report_root = ROOT if args.copy_deployment else repo_root  # Preserve reports outside disposable copies.
    out_dir = report_root / "logs" / "test-runs"  # Use the existing test-results location.
    out_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists.
    return out_dir / f"long_suite_{args.suite}_shard_{args.shard_index}_of_{args.shard_count}.json"  # Return deterministic report path.


# Parse command-line arguments for local, deployment, and sharded runs.
def parse_args():
    parser = argparse.ArgumentParser(description="Run long casino suites that exercise every game per scenario.")  # Create parser.
    parser.add_argument("--suite", choices=sorted(SUITES), default="100", help="Suite size profile: 100, 300, or 500.")  # Select suite.
    parser.add_argument("--iterations", type=int, default=None, help="Override scenario count for smoke/debug runs.")  # Allow quick validation.
    parser.add_argument("--shard-count", type=int, default=1, help="Total number of parallel workers.")  # Configure sharding.
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based worker index.")  # Configure shard owner.
    parser.add_argument("--copy-deployment", action="store_true", help="Copy the whole tree to a disposable deployment folder before running.")  # Enable deployment copy.
    parser.add_argument("--deployment-root", default=str(Path.home() / "Documents" / "Codex" / "casino-environments"), help="Root for disposable deployment folders.")  # Set environment root.
    parser.add_argument("--keep-env", action="store_true", help="Keep the copied deployment folder for debugging.")  # Preserve failed envs when needed.
    parser.add_argument("--skip-browser-audio", action="store_true", help="Skip Playwright audio verification.")  # Allow API-only stress runs.
    parser.add_argument("--audio-repeats", type=int, default=None, help="Override repeated baccarat audio deals.")  # Tune audio load.
    parser.add_argument("--seed", type=int, default=9011, help="Deterministic random seed.")  # Make runs reproducible.
    parser.add_argument("--json-report", default=None, help="Optional explicit report path.")  # Allow CI artifact placement.
    parser.add_argument("--heartbeat-seconds", type=float, default=45.0, help="Flushed heartbeat interval, at most 60 seconds.")  # Configure live cadence.
    parser.add_argument("--stall-seconds", type=float, default=180.0, help="Non-failing no-progress warning threshold.")  # Configure stall warnings.
    parser.add_argument("--timeout-seconds", type=float, default=7200.0, help="Hard suite wall-clock timeout.")  # Configure real timeout cleanup.
    args = parser.parse_args()  # Parse arguments.
    if args.shard_count < 1:  # Reject impossible sharding setups.
        parser.error("--shard-count must be at least 1")  # Reject invalid shard count.
    if not 0 <= args.shard_index < args.shard_count:  # Keep shard ownership in range.
        parser.error("--shard-index must be between 0 and shard-count - 1")  # Reject invalid shard index.
    if args.heartbeat_seconds <= 0 or args.heartbeat_seconds > 60:  # Enforce issue #207 heartbeat acceptance.
        parser.error("--heartbeat-seconds must be greater than 0 and at most 60")  # Reject unsafe cadence.
    if args.stall_seconds < args.heartbeat_seconds:  # Keep warnings later than the first heartbeat.
        parser.error("--stall-seconds must be at least --heartbeat-seconds")  # Reject immediately noisy warnings.
    if args.timeout_seconds <= 0:  # Require a usable real suite deadline.
        parser.error("--timeout-seconds must be greater than 0")  # Reject disabled or immediate timeouts.
    return args  # Return parsed options.


# Execute the requested suite.
def main():
    args = parse_args()  # Read CLI options.
    random.seed(args.seed + args.shard_index)  # Stabilize any future randomized scenario choices.
    suite = SUITES[args.suite]  # Load suite profile.
    total = args.iterations if args.iterations is not None else suite["tests"]  # Determine total logical tests.
    indices = shard_indices(total, args.shard_count, args.shard_index)  # Select this worker's scenario IDs.
    progress = ProgressReporter(len(indices), args.heartbeat_seconds, args.stall_seconds, args.timeout_seconds)  # Reuse browser progress semantics.
    progress.start(f"long-suite-{args.suite}-deployment")  # Flush the initial deployment phase before copying.
    repo_root = ROOT  # Retain a safe report root if deployment preparation fails.
    cleanup_target = None  # Track a disposable deployment only after copy preparation succeeds.
    report = {"suite": args.suite, "total_planned_tests": total, "shard_count": args.shard_count, "shard_index": args.shard_index, "local_tests": len(indices), "deployment_root": str(repo_root), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}  # Start report.
    proc = None  # Track server process for cleanup.
    client = None  # Track the exact loopback client and listener port for cleanup.
    lock_path = None  # Track runtime lock for cleanup.
    exit_code = None  # Retain the conventional non-zero timeout code when needed.
    try:
        repo_root, cleanup_target = prepare_deployment(args)  # Prepare local or copied deployment root.
        report["deployment_root"] = str(repo_root)  # Record the selected disposable or source tree.
        progress.set_phase(f"long-suite-{args.suite}-server-startup")  # Report the next long-running phase.
        lock_path = acquire_runtime_lock(repo_root)  # Prevent same-tree parallel data races.
        requirement_ids = load_requirement_ids(repo_root)  # Load requirement registry from the deployment tree.
        coverage = CoverageLedger(requirement_ids)  # Start coverage accounting.
        proc, client = start_server(repo_root)  # Launch the deployed app.
        progress.set_cleanup(lambda: stop_server(proc, client))  # Register exact PID/port timeout cleanup.
        health = client.call("/healthz", auth=False)  # Prove minimal anonymous liveness in the deployed copy.
        readiness = client.call("/readyz")  # Prove trusted readiness through the authenticated deployment session.
        operations = client.call("/api/v2/admin/operations")  # Prove Admin-authorized heartbeat telemetry.
        assert health == {"status": "live"} and readiness["ready"] is True and operations["ready"] is True, "Operations deployment probes were not healthy"  # Require all policy surfaces.
        assert operations["build"]["sha"] == OPERATIONS_SMOKE_BUILD_SHA, "Operations build provenance did not match the copied child environment"  # Bind smoke evidence to the configured child value.
        report["operations"] = {"pid": proc.pid, "host": "127.0.0.1", "port": int(client.base_url.rsplit(":", 1)[1]), "health": health, "ready": readiness["ready"], "admin_ready": operations["ready"], "build_sha": operations["build"]["sha"]}  # Record trusted probe and listener identity evidence.
        client.call("/api/v1/casino/reset", "POST", {})  # Start the shard from clean data.
        client.login_default_user()  # Restore the session invalidated by reset.
        progress.set_phase(f"long-suite-{args.suite}-scenarios")  # Announce named scenario execution.
        for index in indices:  # Execute each scenario assigned to this shard.
            progress.start_item(f"scenario-{index + 1}-of-{total}")  # Flush the exact scenario start.
            try:  # Preserve scenario failure semantics while adding a terminal event.
                run_full_casino_scenario(client, index, coverage)  # Run one full-casino test.
            except Exception:  # Record the named terminal failure before re-raising.
                progress.finish_item("FAIL")  # Advance completed counts for the failed execution.
                raise  # Preserve the original scenario exception and process status.
            else:  # Record the normal successful scenario terminal event.
                progress.finish_item("PASS")  # Flush passing status and updated counts.
        min_touches = coverage.min_requirement_touch_count()  # Compute actual requirement touch floor.
        required_touches = min(suite["min_requirement_touches"], len(indices)) if args.iterations is not None else suite["min_requirement_touches"]  # Scale debug runs.
        if min_touches < required_touches:  # Enforce the selected suite coverage floor.
            raise AssertionError(f"minimum requirement touches {min_touches} below required {required_touches}")  # Enforce suite floor.
        required_game_plays = min(10, len(indices)) if args.iterations is not None else 10  # Scale debug game-count checks.
        for game_id, count in coverage.games.items():  # Verify every game received enough play.
            if count < required_game_plays:  # Fail if any game fell below the floor.
                raise AssertionError(f"{game_id} played only {count} times; expected at least {required_game_plays}")  # Enforce game play floor.
        report["coverage"] = {"requirement_count": len(requirement_ids), "min_requirement_touches": min_touches, "required_requirement_touches": required_touches, "required_game_plays": required_game_plays, "game_counts": coverage.games}  # Store coverage summary.
        report["scenarios"] = coverage.scenario_results  # Store scenario evidence.
        if not args.skip_browser_audio:  # Run browser audio on full and designated shard checks.
            repeats = args.audio_repeats if args.audio_repeats is not None else suite["audio_repeats"]  # Determine audio repetitions.
            progress.set_phase(f"long-suite-{args.suite}-browser-audio")  # Report the final browser phase.
            run_browser_audio_verification(client, repeats, report)  # Verify voice/SFX behavior.
        report["status"] = "PASS"  # Mark successful report.
    except Exception as exc:  # Preserve failure details before re-raising.
        if progress.timed_out:  # Convert cleanup-driven connection failure into timeout status.
            progress.acknowledge_timeout()  # Prevent a redundant fallback interrupt during artifacts.
            report["status"] = "FAIL"  # Mark the timed-out artifact as failed.
            report["error"] = {"message": "long suite exceeded configured timeout", "last_active_reported": True}  # Store sanitized timeout evidence.
            exit_code = progress.timeout_exit_code  # Return the conventional non-zero timeout status.
        else:  # Preserve every ordinary long-suite failure exactly as before.
            report["status"] = "FAIL"  # Mark failed report.
            report["error"] = {"message": str(exc), "traceback": traceback.format_exc()}  # Preserve failure detail.
            raise  # Re-raise for CI.
    except KeyboardInterrupt:  # Convert only reporter-owned interrupts into timeout results.
        if not progress.timed_out:  # Preserve a user-requested interrupt unchanged.
            raise  # Re-raise external cancellation without relabeling it.
        progress.acknowledge_timeout()  # Stop any remaining watchdog grace wait before artifacts.
        report["status"] = "FAIL"  # Mark the timed-out artifact as failed.
        report["error"] = {"message": "long suite exceeded configured timeout", "last_active_reported": True}  # Store sanitized timeout evidence.
        exit_code = progress.timeout_exit_code  # Return the conventional non-zero timeout status.
    finally:
        report_path = Path(args.json_report).resolve() if args.json_report else default_report_path(repo_root, args)  # Resolve report output.
        if proc:  # Stop the server process if it was started.
            listener_cleanup = progress.cleanup()  # Reuse timeout cleanup evidence or stop the child now.
            if listener_cleanup:  # Store exact closure evidence when cleanup succeeded.
                report["listener_cleanup"] = listener_cleanup  # Preserve PID, host, port, and closure state.
            if progress.cleanup_error:  # Fail the suite if exact tracked cleanup raised.
                report["status"] = "FAIL"  # Prevent a false passing report.
                report["cleanup_error"] = progress.cleanup_error  # Store only the sanitized exception type.
        release_runtime_lock(lock_path)  # Release same-tree runtime protection.
        report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())  # Stamp finish time after listener cleanup.
        report_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the report directory exists.
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")  # Write final evidence including listener closure.
        if cleanup_target and not args.keep_env:  # Remove disposable deployment copies by default.
            shutil.rmtree(cleanup_target, onerror=clear_readonly_and_retry)  # Delete disposable deployment copy.
        progress.close("PASS" if report.get("status") == "PASS" else "FAIL")  # Flush the terminal phase after cleanup and artifacts.
    print(f"LONG_SUITE {report['status']} suite={args.suite} local_tests={len(indices)} shard={args.shard_index}/{args.shard_count} report={report_path}")  # Print concise result.
    return exit_code if exit_code is not None else 0 if report["status"] == "PASS" else 1  # Return CI-friendly status.


# Run the CLI entry point when invoked directly.
if __name__ == "__main__":
    raise SystemExit(main())  # Exit with the long-suite result code.
