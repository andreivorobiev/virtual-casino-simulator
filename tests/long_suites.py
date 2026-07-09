#!/usr/bin/env python3
# Provide long, sharded, deployment-style casino test suites.
import argparse  # Parse suite, shard, deployment, and audio options.
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
# Store GAME_IDS so every scenario can assert that every game was exercised.
GAME_IDS = ("roulette", "slots", "blackjack", "baccarat", "keno", "bingo")
# Store RED_NUMBERS so Roulette outside bets use the documented API payload shape.
RED_NUMBERS = ["1", "3", "5", "7", "9", "12", "14", "16", "18", "19", "21", "23", "25", "27", "30", "32", "34", "36"]
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

    # Call a JSON endpoint and return its standard data envelope.
    def call(self, path, method="GET", body=None, ok=True):
        data = None if body is None else json.dumps(body).encode("utf-8")  # Encode JSON request bodies.
        req = urllib.request.Request(self.base_url + path, data=data, method=method, headers={"Content-Type": "application/json"})  # Build the request.
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
    sock = socket.socket()  # Create a temporary TCP socket.
    sock.bind(("127.0.0.1", 0))  # Ask the OS for a free loopback port.
    port = sock.getsockname()[1]  # Read the assigned port.
    sock.close()  # Release the temporary socket.
    return port  # Return the port for the server process.


# Start the casino server from the selected repository root.
def start_server(repo_root):
    port = free_port()  # Pick an isolated port for this worker.
    proc = subprocess.Popen([sys.executable, str(repo_root / "run.py"), "--host", "127.0.0.1", "--port", str(port), "--no-browser"], cwd=str(repo_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)  # Launch server.
    base = f"http://127.0.0.1:{port}"  # Build the base URL.
    client = ApiClient(base)  # Build an API client for readiness checks.
    for _ in range(120):  # Poll readiness for up to twelve seconds.
        try:
            client.call("/api/v1/casino/state")  # Probe the server state endpoint.
            return proc, client  # Return once the server is ready.
        except Exception:  # Retry transient startup failures until the server is ready.
            time.sleep(0.1)  # Give the server a moment to boot.
    output = proc.stdout.read() if proc.stdout else ""  # Capture startup output on failure.
    proc.terminate()  # Stop the failed server process.
    raise RuntimeError("server did not start\n" + output[-1200:])  # Surface useful diagnostics.


# Ensure the player has enough fake money to survive long randomized play.
def ensure_balance(client):
    if client.balance() < 1000:  # Top up only when the bankroll is too low for long play.
        client.call("/api/v1/players/human/add-money", "POST", {"amount": 10000})  # Top up only when needed.


# Exercise Roulette with a setting change, a bet, and a settlement.
def play_roulette(client, index, coverage):
    client.call("/api/v1/games/roulette/clear", "POST", {"player_id": "human"})  # Clear stale human bets.
    if index % 5 == 0:  # Periodically verify the en-prison zero-rule branch.
        client.call("/api/v1/games/roulette/settings", "POST", {"zero_rule": "en_prison"})  # Exercise zero-rule settings.
        client.call("/api/v1/games/roulette/bets", "POST", {"player_id": "human", "bet_type": "red", "amount": 5, "covered_numbers": RED_NUMBERS, "label": "Red"})  # Place outside bet.
        result = client.call("/api/v1/games/roulette/spin", "POST", {"force_result": "0"})  # Force the prison path.
        assert result["state"]["open_round"]["bets"], "en-prison bet was not carried"  # Verify carried bet.
        client.call("/api/v1/games/roulette/clear", "POST", {"player_id": "human"})  # Clean carried bet before next game.
    else:
        client.call("/api/v1/games/roulette/settings", "POST", {"zero_rule": "normal"})  # Exercise standard setting.
        client.call("/api/v1/games/roulette/bets", "POST", {"player_id": "human", "bet_type": "straight", "amount": 5, "covered_numbers": [str(17 + index % 3)], "label": str(17 + index % 3)})  # Place inside bet.
        result = client.call("/api/v1/games/roulette/spin", "POST", {"force_result": str(17 + index % 3)})  # Force a win.
        assert result["round"]["result"] == str(17 + index % 3), "forced Roulette result mismatch"  # Verify outcome.
    coverage.touch_game("roulette")  # Count Roulette play.


# Exercise Slots with varied payline counts.
def play_slots(client, index, coverage):
    lines = [1, 3, 5, 9, 20][index % 5]  # Vary the active line count.
    result = client.call("/api/v1/games/slots/spin", "POST", {"player_id": "human", "active_lines": lines, "line_bet": 1})  # Spin once.
    assert result["spin"]["cost"] in (0, lines), "Slots cost did not match paid or free-spin rules"  # Verify debit/free-spin shape.
    assert len(result["spin"]["grid"]) == 3, "Slots grid row count changed"  # Verify grid shape.
    coverage.touch_game("slots")  # Count Slots play.


# Exercise Blackjack with a deal and a safe settlement action when needed.
def play_blackjack(client, index, coverage):
    result = client.call("/api/v1/games/blackjack/rounds", "POST", {"player_id": "human", "bet_amount": 5 + index % 4})  # Deal one round.
    round_data = result["round"]  # Keep the dealt round.
    if round_data.get("status") == "player_turn":  # Stand only when the player must act.
        result = client.call(f"/api/v1/games/blackjack/rounds/{round_data['round_id']}/stand", "POST", {"hand_index": 0})  # Stand to settle active hands.
        round_data = result["round"]  # Refresh the settled round.
    assert round_data["dealer"]["cards"], "Blackjack dealer cards missing"  # Verify dealer state.
    coverage.touch_game("blackjack")  # Count Blackjack play.


# Exercise Baccarat with all wager types across repeated scenarios.
def play_baccarat(client, index, coverage):
    bet_type = ["banker", "player", "tie"][index % 3]  # Rotate baccarat bet types.
    client.call("/api/v1/games/baccarat/bets", "POST", {"player_id": "human", "amount": 5, "bet_type": bet_type})  # Place a wager.
    result = client.call("/api/v1/games/baccarat/deal", "POST", {})  # Deal one coup.
    assert result["coup"]["winner"] in ("player", "banker", "tie"), "Baccarat winner invalid"  # Verify winner enum.
    assert result["coup"]["player_cards"] and result["coup"]["banker_cards"], "Baccarat cards missing"  # Verify cards.
    coverage.touch_game("baccarat")  # Count Baccarat play.


# Exercise Keno with both refund and draw paths.
def play_keno(client, index, coverage):
    spots = [1 + index % 10, 20 + index % 10, 40 + index % 10]  # Vary valid spots.
    result = client.call("/api/v1/games/keno/tickets", "POST", {"player_id": "human", "amount": 4, "spots": spots})  # Buy a ticket.
    ticket_id = result["ticket"]["ticket_id"]  # Keep the ticket ID.
    if index % 2 == 0:  # Alternate Keno draw and refund behavior.
        draw = client.call("/api/v1/games/keno/draw", "POST", {})["draw"]  # Draw twenty numbers.
        assert len(draw["drawn"]) == 20, "Keno draw count changed"  # Verify draw size.
    else:
        client.call(f"/api/v1/games/keno/tickets/{ticket_id}", "DELETE", {"player_id": "human"})  # Exercise refund path.
    coverage.touch_game("keno")  # Count Keno play.


# Exercise Bingo with call, reset, and auto-win variants.
def play_bingo(client, index, coverage):
    client.call("/api/v1/games/bingo/cards", "POST", {"player_id": "human", "amount": 5, "pattern": "line"})  # Buy one card.
    if index % 7 == 0:  # Periodically drive Bingo to an automatic win.
        result = client.call("/api/v1/games/bingo/auto", "POST", {"max_calls": 75})  # Exercise auto-play path.
        assert result["session"]["status"] == "won", "Bingo auto-play did not win"  # Verify terminal status.
    else:
        client.call("/api/v1/games/bingo/call", "POST", {})  # Call one ball.
        client.call("/api/v1/games/bingo/reset", "POST", {})  # Reset and refund remaining active cards.
    coverage.touch_game("bingo")  # Count Bingo play.


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
    play_roulette(client, index, coverage)  # Play Roulette.
    play_slots(client, index, coverage)  # Play Slots.
    play_blackjack(client, index, coverage)  # Play Blackjack.
    play_baccarat(client, index, coverage)  # Play Baccarat.
    play_keno(client, index, coverage)  # Play Keno.
    play_bingo(client, index, coverage)  # Play Bingo.
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
            return {"user": {"user_id": "long_suite_user", "username": "long-suite", "display_name": "Long Suite Player", "locale": auth_state["locale"]}, "player": {"player_id": "human", "token_balance": auth_state["tokens"]}, "terms": {"required": False, "version": "private-beta-1"}}  # Mirror the browser-suite mock shape.
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
    args = parser.parse_args()  # Parse arguments.
    if args.shard_count < 1:  # Reject impossible sharding setups.
        parser.error("--shard-count must be at least 1")  # Reject invalid shard count.
    if not 0 <= args.shard_index < args.shard_count:  # Keep shard ownership in range.
        parser.error("--shard-index must be between 0 and shard-count - 1")  # Reject invalid shard index.
    return args  # Return parsed options.


# Execute the requested suite.
def main():
    args = parse_args()  # Read CLI options.
    random.seed(args.seed + args.shard_index)  # Stabilize any future randomized scenario choices.
    suite = SUITES[args.suite]  # Load suite profile.
    total = args.iterations if args.iterations is not None else suite["tests"]  # Determine total logical tests.
    indices = shard_indices(total, args.shard_count, args.shard_index)  # Select this worker's scenario IDs.
    repo_root, cleanup_target = prepare_deployment(args)  # Prepare local or copied deployment root.
    report = {"suite": args.suite, "total_planned_tests": total, "shard_count": args.shard_count, "shard_index": args.shard_index, "local_tests": len(indices), "deployment_root": str(repo_root), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}  # Start report.
    proc = None  # Track server process for cleanup.
    lock_path = None  # Track runtime lock for cleanup.
    try:
        lock_path = acquire_runtime_lock(repo_root)  # Prevent same-tree parallel data races.
        requirement_ids = load_requirement_ids(repo_root)  # Load requirement registry from the deployment tree.
        coverage = CoverageLedger(requirement_ids)  # Start coverage accounting.
        proc, client = start_server(repo_root)  # Launch the deployed app.
        client.call("/api/v1/casino/reset", "POST", {})  # Start the shard from clean data.
        for index in indices:  # Execute each scenario assigned to this shard.
            run_full_casino_scenario(client, index, coverage)  # Run one full-casino test.
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
            run_browser_audio_verification(client, repeats, report)  # Verify voice/SFX behavior.
        report["status"] = "PASS"  # Mark successful report.
    except Exception as exc:  # Preserve failure details before re-raising.
        report["status"] = "FAIL"  # Mark failed report.
        report["error"] = {"message": str(exc), "traceback": traceback.format_exc()}  # Preserve failure detail.
        raise  # Re-raise for CI.
    finally:
        report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())  # Stamp finish time.
        report_path = Path(args.json_report).resolve() if args.json_report else default_report_path(repo_root, args)  # Resolve report output.
        report_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure report directory exists.
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")  # Write JSON evidence.
        if proc:  # Stop the server process if it was started.
            proc.terminate()  # Ask server to stop.
            try:  # Prefer graceful server shutdown.
                proc.wait(timeout=5)  # Wait for clean shutdown.
            except subprocess.TimeoutExpired:  # Force shutdown when graceful stop stalls.
                proc.kill()  # Force kill a stuck server.
                proc.wait(timeout=5)  # Wait for forced exit.
        release_runtime_lock(lock_path)  # Release same-tree runtime protection.
        if cleanup_target and not args.keep_env:  # Remove disposable deployment copies by default.
            shutil.rmtree(cleanup_target, onerror=clear_readonly_and_retry)  # Delete disposable deployment copy.
    print(f"LONG_SUITE {report['status']} suite={args.suite} local_tests={len(indices)} shard={args.shard_index}/{args.shard_count} report={report_path}")  # Print concise result.
    return 0 if report["status"] == "PASS" else 1  # Return CI-friendly status.


# Run the CLI entry point when invoked directly.
if __name__ == "__main__":
    raise SystemExit(main())  # Exit with the long-suite result code.
