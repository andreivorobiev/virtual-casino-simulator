#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Run the repository's API, Browser, Long, governance, and focused test inventories.
import argparse, base64, hashlib, importlib, io, json, os, re, socket, subprocess, sys, tempfile, threading, time, traceback, unittest, urllib.request
# Import date arithmetic for fixed-window Guest Trials retention tests.
from datetime import datetime, timedelta, timezone
from pathlib import Path
# Set ROOT to the value needed for the next operation.
ROOT = Path(__file__).resolve().parents[1]
# Load canonical packaged and module versions once for API and browser regression checks.
VERSION_MANIFEST = json.loads((ROOT/'modules'/'module-manifest.json').read_text(encoding='utf-8'))
# Build the exact ordered module rows returned by Admin version endpoints.
EXPECTED_MODULE_ROWS = [{'module':module,'revision':revision} for module,revision in VERSION_MANIFEST['modules'].items()]
# Add the repository root so direct module imports work from this script.
sys.path.insert(0, str(ROOT))
# Import Blackjack helpers so deterministic API-suite checks can cover table rules.
from casino.games.blackjack import api as blackjack_api, engine as blackjack_engine
# Import Slots rules so deterministic browser evidence is derived from the authoritative twenty-payline table.
from casino.games.slots import engine as slots_engine
# Import Keno rules so browser fixtures use the same paytable and production rounding as the server.
from casino.games.keno import engine as keno_engine
# Import the canonical catalog so guest compatibility is proved for every released game state route.
from casino.games.registry import list_games as list_catalog_games
# Import auth helpers so API tests can seed users through the backend storage seam.
from casino.core import auth as auth_core
# Import autoplay state so guest teardown can prove no control-plane action survives.
from casino.core import autoplay as autoplay_core
# Import the de-identified guest telemetry service for listener-free privacy and retention tests.
from casino.core import guest_analytics
# Import the authoritative ledger for assisted-conversion continuity evidence.
from casino.core import ledger
# Import configuration helpers so startup hardening can be tested without launching a public listener.
from casino import config as casino_config
# Import the shared resolver so session precedence is tested independently of individual game APIs.
from casino.core.request_player import resolve_authenticated_player
# Import isolated state writers for deterministic game and Guest Trials browser setup.
from casino.core.state_store import save_player_game_state, write_json
# Import stable public error classes for focused guest authorization assertions.
from casino.errors import ForbiddenError, RateLimitError, UnauthorizedError, ValidationError
# Import pure Browser discovery, affinity packing, and shard verification outside the compatibility runner. (TEST-242)
from tests import browser_sharding
# Import the sole environment-scalable Playwright wait budget. (TEST-053)
from tests.browser_timing import WAIT_MS
# Import source-only API registration discovery and exact reviewed inventory validation. (TEST-242)
from tests import api_case_inventory
# Import the complete auth-backend and PWA Browser affinity owner. (TEST-242)
from tests.cases.browser import auth_backend_pwa as browser_auth_backend_pwa
# Import the complete disposable guest-lifecycle Browser affinity owner. (TEST-242)
from tests.cases.browser import guest_lifecycle as browser_guest_lifecycle
# Import the complete auth/lobby Browser affinity owner. (TEST-242)
from tests.cases.browser import auth_lobby as browser_auth_lobby
# Import the complete Roulette, Slots, and Keno Browser affinity owner. (TEST-242)
from tests.cases.browser import roulette_slots_keno as browser_roulette_slots_keno
# Import the final Bingo-through-Admin Browser owner while retaining runner lifecycle control.
from tests.cases.browser import bingo_admin as browser_bingo_admin
# Import listener-free atomic game-state registration ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import game_atomic as api_game_atomic
# Import listener-free storage and settlement integrity ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import money_integrity as api_money_integrity
# Import listener-free Admin policy ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import admin_policy as api_admin_policy
# Import the listener-free game lifecycle registration area for #727's thin-runner series.
from tests.cases.api import game_lifecycle as api_game_lifecycle
# Import listener-free delivery-infrastructure ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import delivery_infrastructure as api_delivery_infrastructure
# Import listener-free harness-foundation ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import harness_foundation as api_harness_foundation
# Import live infrastructure case ownership without transferring listener or reset lifecycle. (TEST-242)
from tests.cases.api import live_infrastructure as api_live_infrastructure
# Import storage and MySQL registration ownership without changing explicit live selectors. (TEST-242)
from tests.cases.api import storage_foundation as api_storage_foundation
# Import live session and wallet-integrity registration ownership behind the runner. (TEST-242)
from tests.cases.api import session_integrity as api_session_integrity
# Import post-restart platform-foundation registration ownership behind the runner. (TEST-242)
from tests.cases.api import post_restart_foundation as api_post_restart_foundation
# Import core live-game and Admin registration ownership behind the runner. (TEST-242)
from tests.cases.api import core_live_games as api_core_live_games
# Import the final live authentication registration behind the runner. (TEST-242)
from tests.cases.api import live_authentication as api_live_authentication
# Import frontend-presentation registration ownership while execution stays in the runner. (TEST-242)
from tests.cases.api import frontend_presentation as api_frontend_presentation
# Import listener-free self-service foundation ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import self_service_foundation as api_self_service_foundation
# Import listener-free specialized-game acceptance ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import specialized_game_acceptance as api_specialized_game_acceptance
# Import listener-free player-foundation ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import player_foundation as api_player_foundation
# Import listener-free GameCore and mobile-foundation ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import gamecore_mobile_foundation as api_gamecore_mobile_foundation
# Import listener-free catalog-expansion ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import catalog_expansion as api_catalog_expansion
# Import listener-free Keno and Admin-foundation ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import keno_admin_foundation as api_keno_admin_foundation
# Import listener-free security and UI-foundation ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import security_ui_foundation as api_security_ui_foundation
# Import the first area-owned API registration group behind the compatibility runner. (TEST-242)
from tests.cases.api import governance as api_governance
# Import live Guest/Admin registration ownership while the runner retains server state. (TEST-242)
from tests.cases.api import admin_guest as api_admin_guest
# Import listener-free authentication infrastructure ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import auth as api_auth
# Import listener-free feedback registration ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import feedback as api_feedback
# Import listener-free Guest Trial registration ownership behind the compatibility runner. (TEST-242)
from tests.cases.api import guest as api_guest
# Import the catalog-derived economics registry for listener-free API-suite governance. (TEST-175)
from tests import game_economics_registry_tests
# Import the current-catalog hostile-client certification entrypoint.
from tests.server_authority_tests import run_server_authority_tests
# Import the reusable flushed reporter for TEST-010 browser execution.
from tests.progress import ProgressReporter
# Import state-driven Bingo reload validation so Browser acceptance never relies on a fixed locator race. (issue #785)
from tests.browser_readiness import prepare_admin_feedback_draft, require_bingo_terminal_auto_payload, require_bingo_terminal_reload_payload, save_admin_feedback_triage, wait_for_bingo_terminal_render
# Set RESULTS to the value needed for the next operation.
RESULTS=[]
# Track the browser-suite reporter only while named browser cases are executing.
ACTIVE_PROGRESS=None
# Hold the active shard's owned literal case ids as a frozenset, or None for unsharded runs. (issue #502)
BROWSER_SHARD_CASES=None
# Count source-order browser run_case positions so guarded affinity skips remain exact.
BROWSER_CASE_SEQ=0
# Restrict browser execution to specific games' dedicated acceptance cases, or None for every game. (issue #468 item 4)
BROWSER_AFFECTED_GAMES=None
# Re-export the reviewed groups while pure ownership data lives in browser_sharding.py. (TEST-242)
BROWSER_CASE_AFFINITY_GROUPS=browser_sharding.BROWSER_CASE_AFFINITY_GROUPS
# Register each extracted Browser owner by its exact source-level delegation alias. (TEST-242)
BROWSER_CASE_AREA_OWNERS={'browser_auth_backend_pwa':browser_auth_backend_pwa.run_cases,'browser_guest_lifecycle':browser_guest_lifecycle.run_cases,'browser_auth_lobby':browser_auth_lobby.run_cases,'browser_roulette_slots_keno':browser_roulette_slots_keno.run_cases,'browser_bingo_admin':browser_bingo_admin.run_cases}
# Set SESSION_TOKEN to the value needed for the next operation.
SESSION_TOKEN=None
# Set DEFAULT_AUTH_EMAIL to the value needed for the next operation.
DEFAULT_AUTH_EMAIL=os.environ.get("CASINO_BOOTSTRAP_ADMIN_EMAIL", "admin@example.local")
# Set DEFAULT_AUTH_PASSWORD to the value needed for the next operation.
DEFAULT_AUTH_PASSWORD=os.environ.get("CASINO_BOOTSTRAP_ADMIN_PASSWORD", "admin-password")
# Set PLACEHOLDER_RE to the value needed for the next operation.
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")

# Define the record function used by this module.
def record(test_id, reqs, status, message='', duration_seconds=None):
    # Build the retained result row shared by every suite runner.
    row={'test_id':test_id,'requirements':reqs,'status':status,'message':message}
    # Attach a measured duration only when the browser runner supplied one. (issue #502)
    if duration_seconds is not None: row['duration_seconds']=duration_seconds
    # Retain the completed result for JSON evidence and the Admin test-results view.
    RESULTS.append(row)
    # Write diagnostic output so the current operation can be inspected.
    print(f'[{status}] {test_id} {" ".join(reqs)} {message}',flush=True)

# Define the save_results function used by this module.
def save_results():
    # Set out to the value needed for the next operation.
    out=ROOT/'logs'/'test-runs'; out.mkdir(parents=True, exist_ok=True)
    # Set summary to the value needed for the next operation.
    summary={'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'passed':sum(1 for r in RESULTS if r['status']=='PASS'),'failed':sum(1 for r in RESULTS if r['status']=='FAIL'),'results':RESULTS}
    # Set (out/'latest_results.json').write_text(json.dumps(summary,in to the value needed for the next operation.
    (out/'latest_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')

# Define the free_port function used by this module.
def free_port():
    # Retry the operating-system allocator if it ever selects a protected user port.
    while True:
        # Bind only loopback while asking the operating system for an ephemeral port.
        s=socket.socket(); s.bind(('127.0.0.1',0)); port=s.getsockname()[1]; s.close()
        # Return only a non-reserved test listener port.
        if port not in (8765,8877): return port

# Define the api function used by this module.
def api(base, path, method='GET', body=None, ok=True, auth_token='__default__', extra_headers=None):
    # Set data to the value needed for the next operation.
    data = None if body is None else json.dumps(body).encode('utf-8')
    # Set headers to the value needed for the next operation.
    headers={'Content-Type':'application/json'}
    # Merge caller-provided test headers without changing authentication defaults.
    headers.update(extra_headers or {})
    # Set token to the value needed for the next operation.
    token=SESSION_TOKEN if auth_token == '__default__' else auth_token
    # Branch when a caller wants an authenticated request.
    if token:
        # Set headers['Authorization'] to the value needed for the next operation.
        headers['Authorization']=f'Bearer {token}'
    # Set req to the value needed for the next operation.
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    # Start protected logic so failures can be handled safely.
    try:
        # Manage this resource with automatic setup and cleanup.
        with urllib.request.urlopen(req, timeout=12) as r: payload=json.loads(r.read().decode('utf-8'))
    # Handle the expected failure path for the protected logic.
    except urllib.error.HTTPError as e:
        # Set payload to the value needed for the next operation.
        payload=json.loads(e.read().decode('utf-8'))
    if ok and not payload.get('ok'): raise AssertionError(payload)
    if not ok and payload.get('ok'): raise AssertionError('expected failure but got ok')
    return payload['data'] if payload.get('ok') else payload

# Send exact JSON bytes so parser-boundary tests can exercise non-standard constants. (CORE-025, TEST-055)
def raw_api(base, path, raw_body, method='POST', auth_token='__default__'):
    # Select the current authenticated token unless the caller supplied an override.
    token=SESSION_TOKEN if auth_token == '__default__' else auth_token
    # Declare the exact byte payload as JSON without normalizing it through json.dumps.
    headers={'Content-Type':'application/json'}
    # Attach bearer authentication when the test targets a protected route.
    if token:
        # Preserve the same authorization boundary as the ordinary API helper.
        headers['Authorization']=f'Bearer {token}'
    # Build the exact loopback request with caller-owned hostile bytes.
    request=urllib.request.Request(base + path,data=raw_body,method=method,headers=headers)
    # Start protected response handling because the expected result is a client error.
    try:
        # Parse any unexpected success through the standard JSON decoder.
        with urllib.request.urlopen(request,timeout=12) as response: payload=json.loads(response.read().decode('utf-8'))
    # Decode the expected HTTP error response without suppressing its envelope.
    except urllib.error.HTTPError as error:
        # Parse only the bounded application response body.
        payload=json.loads(error.read().decode('utf-8'))
    # Return the complete envelope so status semantics remain explicit in assertions.
    return payload

# Define the login_default_user function used by this module.
def login_default_user(base):
    # Make SESSION_TOKEN writable so the harness can reuse the latest login.
    global SESSION_TOKEN
    # Set session to the value needed for the next operation.
    session=api(base,'/api/v2/auth/login','POST',{'email':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD},auth_token=None)['session']
    # Set SESSION_TOKEN to the value needed for the next operation.
    SESSION_TOKEN=session['token']
    return SESSION_TOKEN

# Define the start_server function used by this module.
def start_server():
    # Set port to the value needed for the next operation.
    port=free_port(); proc=subprocess.Popen([sys.executable,str(ROOT/'run.py'),'--host','127.0.0.1','--port',str(port),'--no-browser'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    # Set base to the value needed for the next operation.
    base=f'http://127.0.0.1:{port}'
    # Record the isolated listener identity so acceptance handbacks can prove loopback hygiene.
    print(f'Test server PID {proc.pid} listening on {base}',flush=True)
    for _ in range(80):
        # Start protected logic so failures can be handled safely.
        try: login_default_user(base); return proc,base
        # Handle the expected failure path for the protected logic.
        except Exception: time.sleep(.1)
    # Stop and verify the failed startup child before reading its bounded final output.
    stop_server(proc,base)
    # Set out to the value needed for the next operation.
    out=proc.stdout.read() if proc.stdout else ''; raise RuntimeError('server did not start\n'+out[-1200:])

# Stop one tracked test child and prove its exact loopback port is closed.
def stop_server(proc, base):
    # Parse the known numeric port from the harness-owned loopback base URL.
    port=int(base.rsplit(':',1)[1])
    # Reject protected user ports even though the dynamic allocator cannot normally select them.
    if port in (8765,8877): raise AssertionError(f'refusing to stop protected port {port}')
    # Ask only the tracked child process to terminate when it is still running.
    if proc.poll() is None: proc.terminate()
    # Wait for cooperative shutdown before using the tracked-process force fallback.
    try: proc.wait(timeout=5)
    # Handle a child that did not stop within the bounded grace period.
    except subprocess.TimeoutExpired:
        # Kill only the exact process object returned by the harness.
        proc.kill(); proc.wait(timeout=5)
    # Poll the exact loopback port until the operating system releases the listener.
    for _ in range(50):
        # Create a short-lived probe socket without binding or reserving another port.
        probe=socket.socket()
        # Bound each connection attempt so cleanup cannot hang the suite.
        probe.settimeout(.1)
        # Test only the recorded loopback listener and retain no connection on failure.
        open_listener=probe.connect_ex(('127.0.0.1',port))==0
        # Close the probe immediately regardless of listener state.
        probe.close()
        # Report exact PID/port closure as soon as no listener accepts connections.
        if not open_listener:
            # Emit durable cleanup evidence for the validation handback.
            print(f'Test server PID {proc.pid} stopped; 127.0.0.1:{port} closed',flush=True)
            # Return after the tracked child and port are both clean.
            return {'pid':proc.pid,'host':'127.0.0.1','port':port,'closed':True}
        # Wait briefly before the next bounded listener probe.
        time.sleep(.1)
    # Fail the suite when the tracked port remains open after process cleanup.
    raise AssertionError(f'tracked test listener remained open on 127.0.0.1:{port}')

# Define the run_case function used by this module.
def run_case(test_id, reqs, fn):
    # Advance source-order accounting before any packed ownership decision.
    global BROWSER_CASE_SEQ
    # Count this literal call so guarded affinity skips remain aligned with source.
    BROWSER_CASE_SEQ+=1
    # Skip cases owned by other duration-balanced browser shards without recording or reporting them. (issue #502)
    if BROWSER_SHARD_CASES is not None and test_id not in BROWSER_SHARD_CASES: return
    # Skip a dedicated per-game acceptance case when this run did not target that game, after claiming its sequence position. (issue #468 item 4)
    if browser_case_deselected(test_id): return
    # Read the active browser reporter without changing API or storage runner behavior.
    progress=ACTIVE_PROGRESS
    # Flush the named browser-test start before its body begins.
    if progress: progress.start_item(test_id)
    # Capture duration only inside the active Browser reporter context. (issue #502)
    case_started=time.monotonic() if progress else None
    # Start protected logic so failures can be handled safely.
    try: outcome=fn()
    # Handle the expected failure path for the protected logic.
    except Exception as e:
        # Flush the terminal failure before preserving the existing result and exception.
        if progress: progress.finish_item('FAIL')
        # Preserve the mapped failure, adding duration only for Browser evidence.
        record(test_id, reqs, 'FAIL', str(e), duration_seconds=(round(time.monotonic()-case_started,1) if case_started is not None else None)); raise
    # Record the normal passing path after the test body returns.
    else:
        # Fail predicate-shaped case bodies that quietly returned False instead of asserting. (issue #414)
        if outcome is False:
            # Flush the terminal failure exactly like a raising case body.
            if progress: progress.finish_item('FAIL')
            # Record the predicate failure, adding duration only for Browser evidence.
            record(test_id, reqs, 'FAIL', 'case predicate returned False', duration_seconds=(round(time.monotonic()-case_started,1) if case_started is not None else None))
            # Raise the same failure class a raising case body would produce.
            raise AssertionError(f'{test_id} case predicate returned False')
        # Flush the terminal pass and advance completed/total counts.
        if progress: progress.finish_item('PASS')
        # Preserve the mapped PASS row, adding duration only for Browser evidence.
        record(test_id, reqs, 'PASS', duration_seconds=(round(time.monotonic()-case_started,1) if case_started is not None else None))

# List literal BR-prefixed case ids from the browser runner in deterministic source order.
def browser_case_ids():
    # Discover inline and area-owned registrations at their exact delegation positions.
    case_ids=browser_sharding.discover_browser_case_ids(run_browser_tests,BROWSER_CASE_AREA_OWNERS)
    # Require exact pre-slice count and sorted-ID equality before any Browser startup. (TEST-242)
    return browser_sharding.validate_browser_case_inventory(case_ids,BROWSER_CASE_INVENTORY_PATH)

# Count literal BR-prefixed cases from the browser runner so totals cannot drift from discovery.
def browser_case_total():
    # Count the deterministic literal id list so counting and listing can never disagree.
    return len(browser_case_ids())

# Point at the reviewed pre-slice identity packet required by every #727 extraction. (TEST-242)
BROWSER_CASE_INVENTORY_PATH=Path(__file__).resolve().parent/'browser_case_inventory.json'
# Point API source discovery at the extracted area package. (TEST-242)
API_CASES_ROOT=Path(__file__).resolve().parent/'cases'/'api'
# Point API source discovery at the reviewed count and sorted case-ID baseline. (TEST-242)
API_CASE_INVENTORY_PATH=Path(__file__).resolve().parent/'api_case_inventory.json'
# Point at the reviewed per-case duration profile used by deterministic shard packing. (issue #502)
BROWSER_DURATION_PROFILE_PATH=Path(__file__).resolve().parent/'browser_case_durations.json'
# Re-export strict profile constants so focused hostile tests keep their historical seam.
BROWSER_DURATION_PROFILE_MAX_BYTES=browser_sharding.BROWSER_DURATION_PROFILE_MAX_BYTES
# Preserve the existing maximum duration identity at the compatibility runner boundary.
BROWSER_DURATION_MAX_SECONDS=browser_sharding.BROWSER_DURATION_MAX_SECONDS
# Preserve the fixed hostile-profile diagnostic at the compatibility runner boundary.
BROWSER_DURATION_PROFILE_ERROR=browser_sharding.BROWSER_DURATION_PROFILE_ERROR

# Load and strictly validate the tracked profile before any Browser listener can start.
def browser_case_durations():
    # Delegate strict parsing while retaining the runner's monkeypatchable path seam.
    return browser_sharding.load_browser_case_durations(BROWSER_DURATION_PROFILE_PATH,browser_case_ids())

# Compute one deterministic duration-balanced case-id set per shard. (issue #502)
def browser_shard_case_sets(shard_count):
    # Read the exact literal inventory once in deterministic source order.
    case_ids=browser_case_ids()
    # Load the strictly validated tracked weights.
    durations=browser_case_durations()
    # Delegate pure deterministic packing to the extracted module. (TEST-242)
    return browser_sharding.pack_browser_shards(case_ids,durations,shard_count)

# Report whether this shard executes the named literal case so inline handoffs can compensate.
def browser_shard_owns(case_id):
    # Delegate the pure ownership predicate while the runner retains active state.
    return browser_sharding.shard_owns(BROWSER_SHARD_CASES,case_id)

# Report whether the active shard owns every producer and consumer in one declared group.
def browser_shard_owns_group(group_name):
    # Delegate the pure group predicate while the runner retains active state.
    return browser_sharding.shard_owns_group(BROWSER_SHARD_CASES,group_name)

# Validate every declared affinity group against the deterministic startup partition.
def validate_browser_shard_affinity(shard_count):
    # Read the exact literal browser case inventory from this checkout.
    case_ids=browser_case_ids()
    # Compute the same strict deterministic partition used by worker execution.
    shard_sets=browser_shard_case_sets(shard_count)
    # Delegate fail-closed partition and producer/consumer validation. (TEST-242)
    browser_sharding.validate_browser_shard_affinity(case_ids,shard_sets)

# Advance literal case accounting when an unowned shard skips one guarded affinity body.
def skip_browser_affinity(group_name):
    # Update the shared deterministic sequence counter without recording unowned cases.
    global BROWSER_CASE_SEQ
    # Resolve the current literal inventory and the guarded group's exact positions.
    case_ids=browser_case_ids(); group_case_ids=BROWSER_CASE_AFFINITY_GROUPS[group_name]
    # Require the guarded body to represent the next contiguous source-order cases.
    expected=case_ids[BROWSER_CASE_SEQ:BROWSER_CASE_SEQ+len(group_case_ids)]
    # Fail closed if source movement makes a bulk skip hide unrelated cases.
    if tuple(expected)!=group_case_ids: raise AssertionError(f'browser affinity group {group_name} is not the next contiguous case range')
    # Advance once for each literal run_case call that the unowned guarded body omitted.
    BROWSER_CASE_SEQ+=len(group_case_ids)

# Map each game to its one dedicated deep browser acceptance case so unaffected games can be skipped. (issue #468 item 4)
BROWSER_GAME_ACCEPTANCE_CASES=browser_sharding.BROWSER_GAME_ACCEPTANCE_CASES
# Invert the map once so run_case can resolve a dedicated case's owning game in constant time.
_BROWSER_ACCEPTANCE_CASE_GAME=browser_sharding.BROWSER_ACCEPTANCE_CASE_GAME

# Validate the game->case acceptance map against the exact catalog and literal case inventory before any use.
def validate_browser_affected_games():
    # Read the deterministic literal browser case inventory and the current catalog once.
    case_ids=set(browser_case_ids()); catalog_ids={game['id'] for game in casino_config.GAMES}
    # Delegate pure mapping, affinity, and catalog consistency checks. (TEST-242)
    browser_sharding.validate_browser_affected_games(case_ids,catalog_ids)

# Report whether a case is a dedicated per-game acceptance case excluded by the active affected-game set.
def browser_case_deselected(case_id):
    # Delegate pure detector-owned selection while retaining active runner state.
    return browser_sharding.case_deselected(case_id,BROWSER_AFFECTED_GAMES)

# List the case ids one packed shard actually executes after affected-game deselection.
def browser_selected_case_ids(owned_cases):
    # Read the deterministic literal inventory once.
    case_ids=browser_case_ids()
    # Delegate source-order ownership and detector selection.
    return browser_sharding.selected_case_ids(case_ids,owned_cases,BROWSER_AFFECTED_GAMES)

# Compute the exact case ids expected across shards for an affected-game selection, independent of process state.
def browser_expected_case_ids(affected_games):
    # Delegate source-order expected coverage to the extracted pure helper.
    return browser_sharding.expected_case_ids(browser_case_ids(),affected_games)

# Verify aggregated browser shard results cover the independently expected selection exactly once and pass.
def verify_browser_shards(results_dir, shard_count, affected_games=None):
    # Discover and baseline-check the exact literal inventory before reading shard evidence.
    case_ids=browser_case_ids()
    # Compute deterministic ownership through the same strict duration inputs used by workers.
    expected_owned=browser_shard_case_sets(shard_count)
    # Delegate fail-closed packet, ownership, selection, and exact-union verification. (TEST-242)
    return browser_sharding.verify_browser_shards(results_dir,shard_count,affected_games,case_ids,expected_owned)

# Define assert_condition so concise mapped checks still fail when their predicate is false.
def assert_condition(value, message):
    # Raise a focused assertion when the mapped acceptance predicate is false.
    assert value, message

# Format one bounded Roulette i18n failure with the exact runtime evidence needed for diagnosis. (I18N-013)
def roulette_i18n_failure_diagnostic(state):
    # Normalize a missing or malformed snapshot without hiding the original diagnostic fields.
    snapshot=state if isinstance(state,dict) else {}
    # Return locale, loaded domains, and exact missing keys in one stable assertion message.
    return f"Roulette i18n audit failed: locale={snapshot.get('locale')!r}; loadedDomains={snapshot.get('loadedDomains', [])!r}; missingKeys={snapshot.get('missingKeys', [])!r}"

# Resolve exact request-latency source provenance without accepting a branch name.
def request_latency_source_commit():
    # Start one bounded read-only Git query without trusting caller environment.
    try:
        # Resolve the exact local checkout commit without changing repository state.
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=str(ROOT),capture_output=True,text=True,timeout=10)
    # Normalize timeout and process-launch failures into one value-free diagnostic.
    except (subprocess.TimeoutExpired,OSError):
        # Suppress command, path, and operating-system details.
        raise AssertionError('request-latency source commit is unavailable') from None
    # Normalize the bounded command output.
    local_sha=result.stdout.strip().lower() if result.returncode==0 else ''
    # Require exact immutable provenance before an explicit benchmark begins.
    if not re.fullmatch(r'[0-9a-f]{40}',local_sha): raise AssertionError('request-latency source commit is unavailable')
    # Read the optional hosted identity only after checkout provenance is verified.
    hosted_sha=str(os.environ.get('GITHUB_SHA','')).strip().lower()
    # Reject every present malformed or stale hosted assertion.
    if hosted_sha and (not re.fullmatch(r'[0-9a-f]{40}',hosted_sha) or hosted_sha!=local_sha): raise AssertionError('request-latency hosted source commit does not match checkout')
    # Return the exact checkout commit.
    return local_sha

# Run one explicit provider baseline in a fresh listener-free child.
def run_request_latency_provider(provider,output_path):
    # Import the benchmark lazily only for its explicit selector.
    from tests import request_latency_benchmark
    # Resolve exact source provenance before launching the child.
    source_commit=request_latency_source_commit()
    # Run without passing any provider credential through the callback or child arguments.
    request_latency_benchmark.run_provider_subprocess(provider,source_commit,output_path)

# Define the read_i18n_json function used by this module.
def read_i18n_json(path):
    # Return parsed UTF-8 JSON resources for i18n validation.
    return json.loads(path.read_text(encoding='utf-8'))

# Define the i18n_placeholders function used by this module.
def i18n_placeholders(value):
    # Return placeholder names from string values and ignore non-string metadata.
    return set(PLACEHOLDER_RE.findall(value)) if isinstance(value, str) else set()

# Define the validate_i18n_resources function used by this module.
def validate_i18n_resources():
    # Load the canonical Phase 0 locale registry.
    manifest=read_i18n_json(ROOT/'web'/'i18n'/'manifest.json')
    # Preserve the owner-locked order so priority and evidence tiers cannot drift silently.
    locked_locales=('en-US','zh-Hans','hi-IN','es-419','ar','fr-FR','bn-BD','pt-BR','ru-RU','id-ID','ur-PK','de-DE','ja-JP','pcm-NG','arz-EG','ta-IN','vi-VN','te-IN','ha-NG','tr-TR','pnb-PK','sw-KE','fil-PH','mr-IN','yue-Hant-HK')
    # Read registry entries once for metadata and readiness assertions.
    registry=manifest['locales']
    # Resolve the exact selectable resource packs without treating metadata-only identities as translations.
    ready_locales=[locale['id'] for locale in registry if locale['readiness']=='ready' and locale['uiReady'] is True]
    # Discover game-owned translation domains from the same canonical catalog used by the runtime.
    game_domains=[game['frontend']['i18n_domain'] for game in casino_config.GAMES]
    # Combine base and catalog domains for complete installed-resource parity.
    domains=[*manifest['domains'],*game_domains]
    # Require the explicit Phase 0 schema and default/fallback source locale.
    assert manifest['schemaVersion']==2 and manifest['registryVersion']=='phase-0-locked-25'
    # Preserve source-locale defaults independently from browser detection.
    assert manifest['defaultLocale']=='en-US'
    # Require the exact locked identities, order, and permanent 1-based ranks.
    assert tuple(locale['id'] for locale in registry)==locked_locales
    # Reject missing or duplicate rank metadata.
    assert [locale['rank'] for locale in registry]==list(range(1,26))
    # Keep only the two actually translated resource packs selectable in Phase 0.
    assert ready_locales==['en-US','ru-RU']
    # Preserve all four approved right-to-left identities without activating unfinished resources.
    assert [locale['id'] for locale in registry if locale['dir']=='rtl']==['ar','ur-PK','arz-EG','pnb-PK']
    # Require each identity to carry complete script, formatter, fallback, readiness, and review metadata.
    assert all(locale['script'] and locale['formatLocale'] and locale['reviewStatus'] and locale['readiness'] for locale in registry)
    # Require fallback chains to start at translation identity and end at the installed source locale.
    assert all(locale['fallbackChain'][0]==locale['id'] and locale['fallbackChain'][-1]=='en-US' for locale in registry)
    # Reject aliases that escape the locked registry even though metadata-only aliases are not selectable yet.
    assert set(manifest['aliases'].values()).issubset(set(locked_locales))
    # Keep game domains out of the static manifest so the live catalog remains their authority.
    assert all(not domain.startswith('games/') for domain in manifest['domains'])
    # Require one unique catalog domain per registered game.
    assert len(game_domains)==len(set(game_domains))==len(casino_config.GAMES)
    # Reject resource directories that would falsely imply a planned translation is installed.
    assert all(not (ROOT/'web'/'i18n'/locale['id']).exists() for locale in registry if not locale['uiReady'])
    # Validate key and placeholder parity across every base and catalog domain for installed locales.
    for domain in domains:
        # Resolve the English source dictionary from the resource-relative domain.
        source_path=ROOT/'web'/'i18n'/'en-US'/Path(*domain.split('/')).with_suffix('.json')
        # Read canonical source strings before comparing translations.
        source=read_i18n_json(source_path)
        # Compare only actually installed locale packs.
        for locale in ready_locales:
            # Resolve the installed candidate dictionary at the same domain path.
            candidate_path=ROOT/'web'/'i18n'/locale/Path(*domain.split('/')).with_suffix('.json')
            # Read the candidate dictionary as strict UTF-8 JSON.
            candidate=read_i18n_json(candidate_path)
            # Require exact key parity before any browser can render a raw fallback identifier.
            assert set(candidate)==set(source), f'{locale}/{domain} key mismatch'
            # Validate every translated value and named interpolation contract.
            for key, source_value in source.items():
                # Read the corresponding translated value.
                translated_value=candidate[key]
                # Reject empty translations that would create blank controls.
                assert translated_value!='', f'{locale}/{domain}/{key} is empty'
                # Preserve placeholder names exactly across each installed locale.
                assert i18n_placeholders(translated_value)==i18n_placeholders(source_value), f'{locale}/{domain}/{key} placeholder mismatch'

# Run every service-free OAuth test through central discovery so CI cannot miss the package.
def run_oauth_mock_tests():
    # Discover the focused package from the repository root without importing provider SDKs.
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'/'oauth'),pattern='test_*.py',top_level_dir=str(ROOT))
    # Capture unittest detail so a failure can be reported without printing configuration payloads.
    output=io.StringIO()
    # Execute the complete discovered suite once with concise failure collection.
    result=unittest.TextTestRunner(stream=output,verbosity=1).run(suite)
    # Fail the mapped central case when any focused test fails or errors.
    if not result.wasSuccessful(): raise AssertionError(output.getvalue())

# Define the validate_deployment_bootstrap function used to prove fail-closed public startup behavior.
def validate_deployment_bootstrap():
    # Preserve no-configuration developer startup on the default IPv4 loopback binding.
    casino_config.validate_bootstrap_for_startup('127.0.0.1', {})
    # Preserve no-configuration developer startup on the IPv6 loopback binding.
    casino_config.validate_bootstrap_for_startup('::1', {})
    # Build explicit public configuration from synthetic values that are never printed by the test harness.
    public_environment={
        # Supply a non-local bootstrap identity for the guarded deployment path.
        'CASINO_BOOTSTRAP_ADMIN_EMAIL':'deployment-test@example.invalid',
        # Supply a test-only unique value for the guarded deployment path.
        'CASINO_BOOTSTRAP_ADMIN_PASSWORD':'deployment-test-' + ('x' * 32),
        # Supply a separate test-only keyed-digest secret above the public strength floor.
        'CASINO_TOKEN_DIGEST_KEY':'deployment-token-digest-' + ('y' * 32),
        # Supply an independent test-only mail digest key above the public strength floor.
        'CASINO_MAIL_DIGEST_KEY':'deployment-mail-digest-' + ('z' * 32),
    }
    # Accept a non-loopback binding only after both required settings are explicit and non-default.
    casino_config.validate_bootstrap_for_startup('0.0.0.0', public_environment)
    # Copy the explicit settings before adding a public mode signal on a loopback binding.
    public_mode_environment=dict(public_environment)
    # Mark the loopback process as a production deployment so the explicit guard remains active.
    public_mode_environment[casino_config.DEPLOYMENT_MODE_ENV]='production'
    # Accept explicit public mode on loopback only with hardened bootstrap settings.
    casino_config.validate_bootstrap_for_startup('127.0.0.1', public_mode_environment)
    # Iterate over unsafe public cases that must fail before server or storage startup.
    for unsafe_host, unsafe_environment in (
        # Reject a wildcard listener when no bootstrap configuration is supplied.
        ('0.0.0.0', {}),
        # Reject explicit public mode on loopback when no bootstrap configuration is supplied.
        ('127.0.0.1', {casino_config.DEPLOYMENT_MODE_ENV:'public'}),
        # Reject explicitly supplied values when they still select the known local defaults.
        ('0.0.0.0', {
            # Reuse the local identity constant so the test never copies its value into output.
            'CASINO_BOOTSTRAP_ADMIN_EMAIL':casino_config.LOCAL_BOOTSTRAP_ADMIN_EMAIL,
            # Reuse the local credential constant so the test never copies its value into output.
            'CASINO_BOOTSTRAP_ADMIN_PASSWORD':casino_config.AUTH_BOOTSTRAP_ADMIN_PASSWORD,
            # Reuse the known local digest key so the public guard rejects every developer default.
            'CASINO_TOKEN_DIGEST_KEY':casino_config.LOCAL_TOKEN_DIGEST_KEY,
            # Reuse the known local mail digest key so every developer default is rejected.
            'CASINO_MAIL_DIGEST_KEY':casino_config.LOCAL_MAIL_DIGEST_KEY,
        }),
        # Reject otherwise hardened public bootstrap settings when the token digest key is the known local default.
        ('0.0.0.0', {
            # Supply a non-local bootstrap identity.
            'CASINO_BOOTSTRAP_ADMIN_EMAIL':'deployment-test@example.invalid',
            # Supply a non-local bootstrap credential.
            'CASINO_BOOTSTRAP_ADMIN_PASSWORD':'deployment-test-' + ('x' * 32),
            # Reuse the known local digest key that must never cross the loopback boundary.
            'CASINO_TOKEN_DIGEST_KEY':casino_config.LOCAL_TOKEN_DIGEST_KEY,
            # Supply a valid independent mail digest so this case isolates the token-key rejection.
            'CASINO_MAIL_DIGEST_KEY':'deployment-mail-digest-' + ('z' * 32),
        }),
        # Reject otherwise hardened public settings when the mail digest key is the known local default.
        ('0.0.0.0', {
            # Supply a non-local bootstrap identity.
            'CASINO_BOOTSTRAP_ADMIN_EMAIL':'deployment-test@example.invalid',
            # Supply a non-local bootstrap credential.
            'CASINO_BOOTSTRAP_ADMIN_PASSWORD':'deployment-test-' + ('x' * 32),
            # Supply a valid one-time-token digest key.
            'CASINO_TOKEN_DIGEST_KEY':'deployment-token-digest-' + ('y' * 32),
            # Reuse the known local mail digest key that must never cross the loopback boundary.
            'CASINO_MAIL_DIGEST_KEY':casino_config.LOCAL_MAIL_DIGEST_KEY,
        }),
    # Finish the unsafe-case collection and begin the validation loop.
    ):
        # Start protected logic so the expected fail-closed exception can be asserted.
        try:
            # Validate the unsafe case and fail the test if startup is incorrectly allowed.
            casino_config.validate_bootstrap_for_startup(unsafe_host, unsafe_environment)
        # Handle the required public-startup rejection without recording sensitive configuration.
        except RuntimeError:
            # Continue after observing the expected guard rejection.
            continue
        # Raise a value-free assertion when an unsafe deployment case bypasses the guard.
        raise AssertionError('unsafe public bootstrap configuration was accepted')

# Prove disposable guest consent, isolation, browser binding, authorization, and irreversible teardown. (issue #317)
def validate_guest_lifecycle():
    # Capture the active-user count so rejected consent can be proven side-effect free.
    active_before=sum(1 for user in auth_core.load_users().get('users',[]) if auth_core.is_guest(user) and user.get('status')=='active')
    # Start protected validation so the required rejection is explicit.
    try:
        # Attempt creation without affirmative current-version terms.
        auth_core.create_guest('focused-test',False,'private-beta-1','en-US','desktop')
    # Accept only the published validation failure.
    except ValidationError:
        # Continue after the expected fail-closed result.
        pass
    # Fail if missing consent unexpectedly created a principal.
    else:
        # Raise a stable assertion without including runtime data.
        raise AssertionError('guest creation accepted missing consent')
    # Prove rejected consent did not create an active guest identity.
    assert sum(1 for user in auth_core.load_users().get('users',[]) if auth_core.is_guest(user) and user.get('status')=='active')==active_before
    # Create one valid guest through the same service used by the v2 endpoint.
    guest=auth_core.create_guest('focused-test',True,'private-beta-1','ru-RU','mobile')
    # Read the server-authoritative identity, session, and raw one-time browser proof.
    user,session,nonce=guest['user'],guest['session'],guest['browser_nonce']
    # Prove the disposable principal has no Admin authority, credential, or caller-selected wallet.
    assert auth_core.is_guest(user) and not auth_core.is_admin(user) and not user.get('password_hash')
    # Prove the wallet is a fresh isolated 10,000-play-token balance.
    assert auth_core.current_user_payload(session,user)['player']['token_balance']==10000.0
    # Prove exact consent metadata and supported locale are stored server-side.
    assert user.get('terms_accepted_version')=='private-beta-1' and user.get('terms_acceptance_source')=='guest_entry' and user.get('locale')=='ru-RU'
    # Read the matching durable session before any teardown.
    stored_session=next(row for row in auth_core.load_sessions().get('sessions',[]) if row.get('session_id')==session.get('session_id'))
    # Prove only the nonce digest is stored and the raw proof is absent from persisted session JSON.
    assert stored_session.get('guest_browser_nonce_hash')==hashlib.sha256(nonce.encode('utf-8')).hexdigest() and nonce not in json.dumps(stored_session)
    # Prove the correct browser context authenticates and refreshes activity.
    authenticated_session,authenticated_user=auth_core.authenticate_token(session['token'],nonce)
    # Confirm the resolved principal and session are the original isolated pair.
    assert authenticated_session['session_id']==session['session_id'] and authenticated_user['user_id']==user['user_id']
    # Preserve the configured per-session action ceiling before exercising its atomic boundary.
    original_action_limit=auth_core.GUEST_MAX_ACTIONS
    # Start protected action-limit validation so module configuration is always restored.
    try:
        # Set a one-action ceiling for the isolated focused session.
        auth_core.GUEST_MAX_ACTIONS=1
        # Consume the only allowed mutation attempt.
        assert auth_core.consume_guest_action(authenticated_session,authenticated_user)==1
        # Attempt a second mutation under the same disposable session.
        try:
            # Require the bounded service to fail closed before gameplay starts.
            auth_core.consume_guest_action(authenticated_session,authenticated_user)
        # Accept only the standard sanitized rate-limit response.
        except RateLimitError:
            # Continue after observing the per-session resource ceiling.
            pass
        # Fail if the second anonymous mutation obtains another allowance.
        else:
            # Raise a stable assertion without exposing the configured ceiling.
            raise AssertionError('guest action limit was not enforced')
    # Restore the configured action ceiling even when focused assertions fail.
    finally:
        # Return the auth service to its configured resource policy.
        auth_core.GUEST_MAX_ACTIONS=original_action_limit
    # Preserve the configured per-source creation window before exercising its fail-closed boundary. (issue #555; restored after the #568 shell resolution dropped it)
    original_window_limit=auth_core.GUEST_CREATES_PER_IP
    # Start protected window validation so module configuration is always restored.
    try:
        # Allow exactly one creation per source inside the rolling window.
        auth_core.GUEST_CREATES_PER_IP=1
        # Consume the only allowance for the probed source address.
        limited=auth_core.create_guest('rate-window-probe',True,'private-beta-1','en-US','desktop')
        # Start bounded teardown so the probe guests never linger in shared state.
        try:
            # Attempt one excess creation from the same source address.
            try:
                # Require the shared creation gate to fail closed before any allocation.
                auth_core.create_guest('rate-window-probe',True,'private-beta-1','en-US','desktop')
            # Accept only the standard sanitized rate-limit response.
            except RateLimitError:
                # Continue after observing the per-source creation ceiling.
                pass
            # Fail if the excess anonymous creation obtains another principal.
            else:
                # Raise a stable assertion without exposing the configured ceiling.
                raise AssertionError('guest creation rate limit was not enforced')
            # Prove a distinct source stays unaffected by the exhausted window.
            other=auth_core.create_guest('rate-window-probe-2',True,'private-beta-1','en-US','desktop')
            # Remove the distinct-source probe immediately after the boundary proof.
            auth_core.end_guest_trial(other['user'],'revoked')
            # Read the bounded source log through the provider-aware loader.
            creation_log=auth_core.load_guest_creation_log()
            # Prove the accepted attempt is recorded with its bounded source fields.
            assert any(row.get('client')=='rate-window-probe' and row.get('outcome')=='accepted' and row.get('locale')=='en-US' and row.get('device')=='desktop' for row in creation_log.get('creations',[]))
            # Prove the distinct source record exists and the store honors its bounded tail.
            assert any(row.get('client')=='rate-window-probe-2' for row in creation_log.get('creations',[])) and len(creation_log.get('creations',[]))<=auth_core.MAX_GUEST_CREATION_RECORDS
        # Remove the window probe principal even when focused assertions fail.
        finally:
            # End the probed guest so capacity checks below see only their own state.
            auth_core.end_guest_trial(limited['user'],'revoked')
    # Restore the configured window even when focused assertions fail.
    finally:
        # Return the auth service to its configured per-source creation policy.
        auth_core.GUEST_CREATES_PER_IP=original_window_limit
    # Preserve the configured capacity before exercising its fail-closed boundary.
    original_capacity=auth_core.GUEST_MAX_ACTIVE
    # Start protected capacity validation so module configuration is always restored.
    try:
        # Set the capacity to the exact number of currently active guests.
        auth_core.GUEST_MAX_ACTIVE=sum(1 for stored in auth_core.load_users().get('users',[]) if auth_core.is_guest(stored) and stored.get('status')=='active')
        # Attempt one excess creation at the active-principal boundary.
        try:
            # Supply otherwise valid input so capacity is the only failing gate.
            auth_core.create_guest('focused-capacity-test',True,'private-beta-1','en-US','desktop')
        # Accept only the published forbidden result.
        except ForbiddenError:
            # Continue after observing the bounded-capacity rejection.
            pass
        # Fail if an excess anonymous principal is created.
        else:
            # Raise a stable capacity assertion without runtime counts.
            raise AssertionError('guest capacity limit was not enforced')
    # Restore configuration even when capacity assertions fail.
    finally:
        # Return the auth service to its configured active-principal cap.
        auth_core.GUEST_MAX_ACTIVE=original_capacity
    # Preserve the configured capacity before exercising simultaneous creation at one remaining slot.
    original_capacity=auth_core.GUEST_MAX_ACTIVE
    # Collect only success/failure categories and successful principals, never credentials in diagnostics.
    concurrent_results=[]
    # Synchronize both contenders so the user-store capacity decision is genuinely concurrent.
    creation_barrier=threading.Barrier(2)
    # Define one anonymous creation contender for the focused single-slot race.
    def create_concurrently(client):
        # Wait until both contenders are ready before entering the atomic capacity path.
        creation_barrier.wait(timeout=5)
        # Attempt an otherwise valid guest creation.
        try:
            # Retain the successful guest only for canonical teardown below.
            concurrent_results.append(('created',auth_core.create_guest(client,True,'private-beta-1','en-US','desktop')))
        # Record the exact bounded-capacity rejection without leaking state.
        except ForbiddenError:
            # Preserve only the outcome category needed by the assertion.
            concurrent_results.append(('blocked',None))
    # Start protected concurrent validation so capacity and created guests are always restored.
    try:
        # Allow exactly one more active guest beyond the current baseline.
        auth_core.GUEST_MAX_ACTIVE=sum(1 for stored in auth_core.load_users().get('users',[]) if auth_core.is_guest(stored) and stored.get('status')=='active')+1
        # Create two competing threads for the one remaining anonymous slot.
        contenders=[threading.Thread(target=create_concurrently,args=(f'focused-race-{index}',)) for index in range(2)]
        # Start both contenders before waiting for either result.
        for contender in contenders: contender.start()
        # Require both bounded operations to terminate without a hung lock.
        for contender in contenders: contender.join(timeout=10)
        # Prove exactly one atomic creation and one capacity rejection occurred.
        assert sorted(result[0] for result in concurrent_results)==['blocked','created'] and all(not contender.is_alive() for contender in contenders)
    # Restore capacity and revoke the successful disposable principal even when the race assertion fails.
    finally:
        # Return the auth service to its configured limit.
        auth_core.GUEST_MAX_ACTIVE=original_capacity
        # End only successfully created race principals.
        for outcome,created_guest in concurrent_results:
            # Apply canonical teardown when this contender obtained the one slot.
            if outcome=='created': auth_core.end_guest_trial(created_guest['user'],'revoked')
    # Prove central Admin authorization rejects the guest principal.
    try:
        # Apply the exact Admin guard used by both API versions.
        auth_core.require_admin(user)
    # Accept only the published forbidden result.
    except ForbiddenError:
        # Continue after the expected non-Admin rejection.
        pass
    # Fail if any guest gains Admin authority.
    else:
        # Raise a stable assertion without identity detail.
        raise AssertionError('guest principal passed the Admin guard')
    # Prove a cookie/token without the browser proof is not resumable and triggers irreversible teardown.
    try:
        # Attempt contextless authentication with the otherwise valid bearer token.
        auth_core.authenticate_token(session['token'],'')
    # Accept only the standard unauthenticated result.
    except UnauthorizedError:
        # Continue after observing the required context-loss rejection.
        pass
    # Fail if cookie-only replay resumes the guest.
    else:
        # Raise a stable assertion without credential material.
        raise AssertionError('guest resumed without browser-context proof')
    # Read the terminal identity and wallet after context loss.
    ended_user=auth_core.find_user_by_id(user['user_id'])
    # Prove identity and play-token wallet are irreversibly revoked.
    assert ended_user.get('status')=='ended' and auth_core.current_user_payload(session,ended_user)['player']['status']=='ended' and auth_core.current_user_payload(session,ended_user)['player']['token_balance']==0.0
    # Create a separate guest for inactivity-boundary enforcement.
    inactive_guest=auth_core.create_guest('focused-inactivity-test',True,'private-beta-1','en-US','desktop')
    # Calculate a server timestamp older than the configured inactivity window.
    inactive_at=(datetime.now(timezone.utc)-timedelta(seconds=auth_core.GUEST_INACTIVITY_SECONDS+1)).isoformat(timespec='milliseconds').replace('+00:00','Z')
    # Define the atomic session-age mutation.
    def age_inactive_session(state):
        # Find only the focused inactivity session.
        for stored in state.get('sessions',[]):
            # Match by opaque session id without copying its credential.
            if stored.get('session_id')==inactive_guest['session']['session_id']:
                # Move the server-observed activity marker past the inactivity boundary.
                stored['updated_at']=inactive_at
        # Return the mutated sessions document.
        return state
    # Persist the focused inactivity condition atomically.
    auth_core.update_json(auth_core.SESSIONS_PATH,age_inactive_session,auth_core.default_sessions)
    # Prove the old session cannot authenticate even with its correct browser proof.
    try:
        # Attempt authentication at the inactivity boundary.
        auth_core.authenticate_token(inactive_guest['session']['token'],inactive_guest['browser_nonce'])
    # Accept only the standard terminal unauthenticated result.
    except UnauthorizedError:
        # Continue after observing inactivity teardown.
        pass
    # Fail if inactivity does not end the trial.
    else:
        # Raise a stable assertion without timestamps or credentials.
        raise AssertionError('inactive guest session remained resumable')
    # Prove inactivity used the standard irreversible identity and wallet teardown.
    assert auth_core.find_user_by_id(inactive_guest['user']['user_id']).get('status')=='ended'
    # Create a separate guest for absolute-lifetime enforcement.
    absolute_guest=auth_core.create_guest('focused-absolute-test',True,'private-beta-1','en-US','desktop')
    # Calculate a server timestamp already beyond the absolute lifetime.
    expired_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(timespec='milliseconds').replace('+00:00','Z')
    # Define the atomic guest-expiry mutation.
    def expire_guest_user(state):
        # Find only the focused absolute-lifetime identity.
        for stored in state.get('users',[]):
            # Match by opaque user id without changing any authority field.
            if stored.get('user_id')==absolute_guest['user']['user_id']:
                # Move only the server-owned absolute expiry into the past.
                stored['guest_expires_at']=expired_at
        # Return the mutated user document.
        return state
    # Persist the focused absolute-expiry condition atomically.
    auth_core.update_json(auth_core.USERS_PATH,expire_guest_user,auth_core.default_users)
    # Prove the expired identity cannot authenticate with otherwise valid proofs.
    try:
        # Attempt authentication beyond the absolute lifetime.
        auth_core.authenticate_token(absolute_guest['session']['token'],absolute_guest['browser_nonce'])
    # Accept only the standard terminal unauthenticated result.
    except UnauthorizedError:
        # Continue after observing absolute-expiry teardown.
        pass
    # Fail if absolute expiry does not end the trial.
    else:
        # Raise a stable assertion without timestamps or credentials.
        raise AssertionError('absolute-expiry guest remained resumable')
    # Prove the absolute-lifetime path used canonical teardown.
    assert auth_core.find_user_by_id(absolute_guest['user']['user_id']).get('status')=='ended'
    # Create a final guest for explicit End semantics independent of browser-proof failure.
    explicit_guest=auth_core.create_guest('focused-explicit-end-test',True,'private-beta-1','en-US','desktop')
    # Start one guest-owned control-plane session to prove teardown prevents later atomic actions.
    explicit_autoplay=autoplay_core.start('slots',explicit_guest['user']['player_id'],'medium',5,{}, {})
    # End it through the canonical explicit lifecycle service.
    auth_core.end_guest_trial(explicit_guest['user'],'ended')
    # Prove explicit End revokes both identity and isolated play-token wallet.
    assert auth_core.find_user_by_id(explicit_guest['user']['user_id']).get('status')=='ended' and auth_core.current_user_payload(explicit_guest['session'],auth_core.find_user_by_id(explicit_guest['user']['user_id']))['player']['token_balance']==0.0
    # Prove no guest-owned autoplay registration remains able to start another atomic game action.
    assert autoplay_core.get_session(explicit_autoplay['autoplay_id'])['status']=='stopped' and autoplay_core.get_session(explicit_autoplay['autoplay_id'])['stop_requested'] is True

# Prove guest analytics dimensions, milestones, privacy, and fixed retention windows. (issue #317)
def validate_guest_analytics():
    # Preserve the repository runtime path before using an isolated temporary telemetry document.
    original_path=guest_analytics.TRIALS_PATH
    # Create a temporary directory that is removed automatically after assertions.
    with tempfile.TemporaryDirectory() as temporary_directory:
        # Redirect only the analytics service to isolated focused-test state.
        guest_analytics.TRIALS_PATH=Path(temporary_directory)/'guest_trials.json'
        # Start protected assertions so the canonical runtime path is always restored.
        try:
            # Create one de-identified row with allowlisted dimensions.
            analytics_id=guest_analytics.record_started('ru-RU','mobile')
            # Record authenticated lobby reach without client-authored navigation data.
            guest_analytics.record_event(analytics_id,'lobby_reached')
            # Record a surface open with a coarse latency bucket and no request or response payloads.
            guest_analytics.record_event(analytics_id,'game_open','slots',latency_ms=45)
            # Increment a server-classified completed round with authoritative fake-token aggregates.
            guest_analytics.record_event(analytics_id,'game_action','slots',action='spin',latency_ms=125,wagered=5,returned=8,round_started=True,round_completed=True)
            # Record one sanitized validation failure without message, request, or response content.
            guest_analytics.record_event(analytics_id,'game_error','slots',action='spin',latency_ms=12,error_category='VALIDATION_ERROR')
            # Open a second catalog game so the full journey funnel reaches its seventh stage.
            guest_analytics.record_event(analytics_id,'game_open','roulette',latency_ms=60)
            # Close the row through a bounded lifecycle reason.
            guest_analytics.record_ended(analytics_id,'ended',ending_balance=5003)
            # Read the raw isolated state through the service's atomic reader.
            state=guest_analytics.read_json(guest_analytics.TRIALS_PATH,guest_analytics.default_trials)
            # Serialize only for forbidden-field name checks, never for output.
            serialized=json.dumps(state).lower()
            # Prove no identity, credential, browser, or network field can enter telemetry.
            for forbidden in ('auth_token','browser_nonce','csrf_token','email','ip','player_id','session_id','user_id','user_agent'):
                # Require the forbidden key to be absent from the complete telemetry document.
                assert forbidden not in serialized
            # Read the single raw row and verify bounded dimensions and milestones.
            row=state['trials'][0]
            # Prove locale/device/game/counter semantics without identity linkage.
            assert row['analytics_id']==analytics_id and row['locale']=='ru-RU' and row['device']=='mobile' and row['engaged'] is True and row['rounds_started']==1 and row['rounds_completed']==1 and row['games']['slots']['rounds_completed']==1
            # Prove the full journey, fake-token, error, latency, and bounded timeline semantics.
            assert row['milestones']['lobby_reached'] and row['milestones']['second_game_opened'] and row['milestones']['trial_terminal'] and row['milestones']['account_cta_viewed'] and row['wagered']==5.0 and row['returned']==8.0 and row['net']==3.0 and row['ending_balance']==5003.0 and row['errors']==1 and row['error_categories']=={'VALIDATION_ERROR':1} and len(row['events'])<=guest_analytics.MAX_TIMELINE_EVENTS
            # Read a fully filtered Admin summary from the isolated analytics state.
            summary=guest_analytics.summary(locale='ru-RU',device='mobile',status='ended',game='slots',completed='yes',error_category='VALIDATION_ERROR')
            # Prove nine-stage funnel, rates, product metrics, per-game counters, and filter echoing.
            assert summary['funnel']['landing_viewed']==1 and summary['funnel']['account_cta_viewed']==1 and summary['funnel_rates']['first_round_completed']==100.0 and summary['metrics']['wagered']==5.0 and summary['metrics']['returned']==8.0 and summary['metrics']['net']==3.0 and summary['metrics']['fake_tokens_only'] is True and summary['games'][0]['rounds_started']==1 and summary['games'][0]['errors']==1 and summary['filters']['game']=='slots'
            # Calculate a timestamp outside the thirty-day raw window but inside aggregate retention.
            aged=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat(timespec='milliseconds').replace('+00:00','Z')
            # Define an atomic age mutation for the isolated row.
            def age_row(document):
                # Move only server timestamps required by retention classification.
                document['trials'][0].update({'started_at':aged,'last_event_at':aged,'ended_at':aged})
                # Return the mutated isolated document.
                return document
            # Persist the aged row atomically.
            guest_analytics.update_json(guest_analytics.TRIALS_PATH,age_row,guest_analytics.default_trials)
            # Apply fixed retention and capture identifier-free counts.
            cleanup=guest_analytics.cleanup()
            # Read the cleaned isolated state.
            cleaned=guest_analytics.read_json(guest_analytics.TRIALS_PATH,guest_analytics.default_trials)
            # Prove the raw row was removed, one daily aggregate remains, and cleanup health is populated.
            assert cleanup['raw_removed']==1 and cleaned['trials']==[] and len(cleaned['daily'])==1 and cleaned['cleanup']['last_success_at']
            # Define a malformed aggregate date that exercises failure visibility without identity data.
            def poison_aggregate(document):
                # Replace the daily collection with one invalid date and bounded counters.
                document['daily']=[{'date':'invalid','started':1,'engaged':0,'rounds_completed':0,'ended':0}]
                # Return the malformed isolated document for the focused failure path.
                return document
            # Persist the failure fixture inside the temporary telemetry file only.
            guest_analytics.update_json(guest_analytics.TRIALS_PATH,poison_aggregate,guest_analytics.default_trials)
            # Start protected cleanup so the required failure cannot be mistaken for success.
            try:
                # Apply retention to the malformed date and require parsing to fail.
                guest_analytics.cleanup()
            # Accept the standard value failure while checking its separately persisted health marker.
            except ValueError:
                # Continue after the cleanup service rejected the malformed retained aggregate.
                pass
            # Fail when malformed retention data is silently accepted.
            else:
                # Raise a stable diagnostic without copying source data.
                raise AssertionError('guest cleanup failure was reported as success')
            # Read the failure-marked state without exposing its local path.
            failed_cleanup=guest_analytics.read_json(guest_analytics.TRIALS_PATH,guest_analytics.default_trials)['cleanup']
            # Prove Admin health can observe a timestamp and fixed sanitized category, never exception text.
            assert failed_cleanup['last_failure_at'] and failed_cleanup['last_error']=='cleanup_failed'
            # Define a repair that removes only the temporary malformed aggregate fixture.
            def repair_aggregate(document):
                # Restore the aggregate collection to a valid empty value.
                document['daily']=[]
                # Return the repaired isolated document.
                return document
            # Repair the isolated document before verifying recovery semantics.
            guest_analytics.update_json(guest_analytics.TRIALS_PATH,repair_aggregate,guest_analytics.default_trials)
            # Run one successful cleanup to clear the current error while retaining failure history.
            guest_analytics.cleanup()
            # Read the recovered health state.
            recovered_cleanup=guest_analytics.read_json(guest_analytics.TRIALS_PATH,guest_analytics.default_trials)['cleanup']
            # Prove recovery is observable and the last failure timestamp remains available.
            assert recovered_cleanup['last_success_at'] and recovered_cleanup['last_failure_at']==failed_cleanup['last_failure_at'] and recovered_cleanup['last_error'] is None
        # Restore the canonical runtime analytics path even when an assertion fails.
        finally:
            # Return the module to its original runtime state.
            guest_analytics.TRIALS_PATH=original_path

# Prove the additive v2 guest contracts and restricted-preview compatibility boundary. (issue #317)
def validate_guest_contracts():
    # Read both OpenAPI contracts as UTF-8 source for exact route assertions.
    auth_contract=(ROOT/'contracts'/'openapi'/'auth.v2.yaml').read_text(encoding='utf-8')
    # Read the Admin contract independently so missing files fail this focused case.
    admin_contract=(ROOT/'contracts'/'openapi'/'guest-trials.v2.yaml').read_text(encoding='utf-8')
    # Parse the restricted-preview compatibility policies.
    security_contract=json.loads((ROOT/'contracts'/'compatibility'/'restricted-preview-security.json').read_text(encoding='utf-8'))
    # Parse the guest-specific lifecycle and privacy contract.
    guest_contract=json.loads((ROOT/'contracts'/'compatibility'/'guest-trials-restricted-preview.json').read_text(encoding='utf-8'))
    # Prove public creation and both authenticated lifecycle routes are explicitly published.
    assert all(route in auth_contract for route in ('/auth/guest:','/auth/guest/end:','/auth/guest/depart:','GuestBrowserNonce'))
    # Prove the complete Admin summary/list/detail/settings/conversion/cleanup route family is published under v2.
    assert all(route in admin_contract for route in ('/admin/guest-trials:','/admin/guest-trials/sessions:','/admin/guest-trials/sessions/{analytics_id}:','/admin/guest-trials/settings:','/admin/guest-trials/convert:','/admin/guest-trials/cleanup:'))
    # Prove the full filters, journey, fake-token, action/error/latency, conversion, and bounded timeline schemas are published.
    assert all(term in admin_contract for term in ('GameFilter','CompletedFilter','ErrorCategoryFilter','SinceFilter','UntilFilter','account_cta_selected','ProductMetrics','fake_tokens_only','action_categories','error_categories','latency_buckets','AssistedConversionRequest','confirm:','player_preserved','maxItems: 80'))
    # Preserve the exact anonymous allowlist including private redemption, disabled enrollment, and reviewed provider-latched OAuth routes. (OAUTH-007)
    assert security_contract['anonymous_routes']==['/api/v2/auth/login','/api/v2/auth/guest','/api/v2/auth/redeem-invitation','/api/v2/auth/enrollment-policy','/api/v2/auth/signup','/api/v2/auth/signup/resend','/api/v2/auth/signup/verify','/api/v2/auth/signup/cancel','/api/v2/auth/password-reset/initiate','/api/v2/auth/password-reset/resend','/api/v2/auth/password-reset/complete','/api/v2/auth/oauth/providers','/api/v2/auth/csrf','/api/v2/auth/oauth/{google|facebook}/start','/api/v2/auth/oauth/{google|facebook}/callback','/healthz']
    # Prove launch stays held, the fixed grant and owner admission control are exact, and retention/forbidden fields remain exact.
    assert guest_contract['public_launch_authorized'] is False and guest_contract['entry']['starting_play_tokens']==10000 and guest_contract['entry']['admission_change_requires_restart'] is False and guest_contract['entry']['admission_pause_ends_existing_trials'] is False and guest_contract['wallet']['starting_play_tokens_fixed']==10000 and guest_contract['wallet']['add_tokens_allowed'] is False and guest_contract['lifecycle']['autoplay_stopped_on_end'] is True and guest_contract['entry']['max_game_actions_per_session']==1000 and guest_contract['entry']['max_concurrent_autoplay_sessions']==1 and guest_contract['conversion']['self_service'] is True and guest_contract['conversion']['admin_assisted'] is True and guest_contract['conversion']['explicit_confirmation_required'] is True and guest_contract['conversion']['player_wallet_ledger_preserved'] is True and guest_contract['admin_telemetry']['admission_write_authority']=='current-active-platform-owner' and guest_contract['admin_telemetry']['raw_retention_days']==30 and guest_contract['admin_telemetry']['aggregate_retention_days']==400 and guest_contract['admin_telemetry']['cleanup_failure_visible'] is True and guest_contract['admin_telemetry']['timeline_event_limit']==80 and guest_contract['admin_telemetry']['responsive_error_cohort_minimum']==5 and guest_contract['admin_telemetry']['export_allowed'] is False and 'browser_nonce' in guest_contract['admin_telemetry']['forbidden_fields']
    # Parse the exact digest freeze map.
    digests=json.loads((ROOT/'contracts'/'compatibility'/'contract-digests.json').read_text(encoding='utf-8'))
    # Verify both changed v2 contracts match their frozen exact bytes.
    for path in ('contracts/openapi/auth.v2.yaml','contracts/openapi/guest-trials.v2.yaml'):
        # Compare the tracked SHA-256 to the current contract bytes.
        assert digests[path]==hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

# Prove the live local adapters enforce guest and Admin v2 boundaries with exact envelopes. (issue #317)
def validate_guest_admin_api(base):
    # Attempt anonymous creation with a caller-authored balance outside the exact v2 request contract.
    hostile_creation=api(base,'/api/v2/auth/guest','POST',{'accepted':True,'terms_version':'private-beta-1','locale':'en-US','device':'desktop','balance':999999},ok=False,auth_token=None)
    # Prove unsupported identity or wallet fields fail before a guest principal is minted.
    assert hostile_creation['error']['code']=='VALIDATION_ERROR'
    # Attempt guest-only teardown through the current registered Admin session.
    registered_end=api(base,'/api/v2/auth/guest/end','POST',{},ok=False)
    # Prove guest lifecycle routes cannot change or impersonate a registered-session logout.
    assert registered_end['error']['code']=='FORBIDDEN'
    # Create one isolated guest through the canonical service so the test can retain its bearer token safely in-process.
    guest=auth_core.create_guest('focused-api-test',True,'private-beta-1','en-US','desktop')
    # Read the opaque token and one-time context proof only into local test variables.
    token,nonce=guest['session']['token'],guest['browser_nonce']
    # Build the required guest-only browser proof header.
    guest_headers={'X-Guest-Browser-Nonce':nonce}
    # Track whether the guest became a durable account so teardown never touches its preserved wallet.
    guest_converted=False
    # Start protected assertions so the guest is always irreversibly ended.
    try:
        # Prove the guest can read its bound current-user state through the shared protected adapter.
        current=api(base,'/api/v2/me',auth_token=token,extra_headers=guest_headers)
        # Require the non-Admin guest principal and isolated wallet shape.
        assert current['user']['principal_type']=='guest' and current['player']['token_balance']==10000.0
        # Open Slots through the normal guest-bound game state route.
        guest_state=api(base,'/api/v1/games/slots/state',auth_token=token,extra_headers=guest_headers)
        # Prove server identity replacement returns only the guest-bound wallet.
        assert guest_state['player']['player_id']==guest['user']['player_id']
        # Read every released catalog game's canonical state through the same guest-bound public action.
        guest_catalog_states=[api(base,f"/api/v1/games/{game['id'].replace('_','-')}/state",auth_token=token,extra_headers=guest_headers) for game in list_catalog_games()]
        # Prove the complete current catalog accepts the dedicated guest principal without a game-specific bypass.
        assert len(guest_catalog_states)==len(list_catalog_games()) and all(isinstance(state,dict) for state in guest_catalog_states)
        # Submit one invalid action so error categories are server-derived and sanitized.
        invalid_spin=api(base,'/api/v1/games/slots/spin','POST',{'active_lines':2,'line_bet':1},ok=False,auth_token=token,extra_headers=guest_headers)
        # Require the published validation category without depending on message text.
        assert invalid_spin['error']['code']=='VALIDATION_ERROR'
        # Submit one valid authoritative spin through the released game action.
        valid_spin=api(base,'/api/v1/games/slots/spin','POST',{'active_lines':1,'line_bet':1},auth_token=token,extra_headers=guest_headers)
        # Prove the real game module returned one terminal round and guest-bound player state.
        assert valid_spin['spin']['round_id'] and valid_spin['player']['player_id']==guest['user']['player_id']
        # Preserve the authoritative post-spin balance before testing the forbidden top-up path.
        balance_after_spin=valid_spin['player']['balance']
        # Attempt a guest autoplay registration with a hostile cross-player id and excessive round count.
        guest_autoplay=api(base,'/api/v1/autoplay/start','POST',{'game_id':'slots','player_id':'human','round_limit':999,'speed':'medium'},auth_token=token,extra_headers=guest_headers)['session']
        # Prove the server binds the guest wallet and clamps the disposable resource ceiling.
        assert guest_autoplay['player_id']==guest['user']['player_id'] and guest_autoplay['round_limit']==casino_config.GUEST_AUTOPLAY_MAX_ROUNDS
        # Attempt a second concurrent guest autoplay registration.
        duplicate_autoplay=api(base,'/api/v1/autoplay/start','POST',{'game_id':'slots','round_limit':1,'speed':'medium'},ok=False,auth_token=token,extra_headers=guest_headers)
        # Require the standard conflict result rather than another resource registration.
        assert duplicate_autoplay['error']['code']=='CONFLICT'
        # Stop and finish the Slots session before proving the distinct complete Bingo call ceiling. (BINGO-027)
        api(base,'/api/v1/autoplay/stop','POST',{'autoplay_id':guest_autoplay['autoplay_id']},auth_token=token,extra_headers=guest_headers)
        # Commit the terminal lifecycle state so the one-concurrent-session boundary remains authoritative.
        api(base,'/api/v1/autoplay/finish-stop','POST',{'autoplay_id':guest_autoplay['autoplay_id']},auth_token=token,extra_headers=guest_headers)
        # Request one complete Bingo call plan through the same guest-scoped control-plane route.
        bingo_autoplay=api(base,'/api/v1/autoplay/start','POST',{'game_id':'bingo','round_limit':999,'speed':'medium','plan':{'type':'auto_call_stepwise'}},auth_token=token,extra_headers=guest_headers)['session']
        # Require the governed 75-call cap without broadening any other guest autoplay loop.
        assert bingo_autoplay['round_limit']==casino_config.GUEST_BINGO_AUTOPLAY_MAX_CALLS==75
        # Attempt the registered-user-only play-token credit route with valid guest proofs.
        top_up=api(base,'/api/v2/me/tokens/add','POST',{'amount':1},ok=False,auth_token=token,extra_headers=guest_headers)
        # Prove the disposable starting grant cannot be increased through the normal shell endpoint.
        assert top_up['error']['code']=='FORBIDDEN' and api(base,'/api/v2/me',auth_token=token,extra_headers=guest_headers)['player']['token_balance']==balance_after_spin
        # Exercise the frozen v1 credit route with the same guest proof so the parity fix is behavioral, not source-text-only. (TOKEN-006)
        legacy_top_up=api(base,f"/api/v1/players/{guest['user']['player_id']}/add-money",'POST',{'amount':1},ok=False,auth_token=token,extra_headers=guest_headers)
        # Require the v1 route to preserve the same fixed disposable balance as the v2 route.
        assert legacy_top_up['error']['code']=='FORBIDDEN' and api(base,'/api/v2/me',auth_token=token,extra_headers=guest_headers)['player']['token_balance']==balance_after_spin
        # Submit an out-of-domain Blackjack payout through the real authenticated API boundary. (LEDGER-029)
        hostile_blackjack=api(base,'/api/v1/games/blackjack/settings','POST',{'blackjack_payout':1000000},ok=False,auth_token=token,extra_headers=guest_headers)
        # Require the published validation envelope before the hostile payout can enter persistent game state.
        assert hostile_blackjack['error']['code']=='VALIDATION_ERROR'
        # Submit an out-of-domain Baccarat commission through the same authenticated boundary. (LEDGER-029)
        hostile_baccarat=api(base,'/api/v1/games/baccarat/settings','POST',{'banker_commission':-1000},ok=False,auth_token=token,extra_headers=guest_headers)
        # Require the published validation envelope before the hostile commission can reach settlement math.
        assert hostile_baccarat['error']['code']=='VALIDATION_ERROR'
        # Prove the same guest cannot reach the Admin v2 summary.
        denied=api(base,'/api/v2/admin/guest-trials',ok=False,auth_token=token,extra_headers=guest_headers)
        # Require the central forbidden envelope rather than an empty or partial Admin response.
        assert denied['error']['code']=='FORBIDDEN'
        # Read both regular Admin user lists through the authenticated Admin session.
        account_lists=[api(base,'/api/v1/admin/users')['users'],api(base,'/api/v2/admin/users')['users']]
        # Prove disposable marketing-trial principals are not mixed into account-management tables.
        assert all(guest['user']['user_id'] not in {row.get('user_id') for row in rows} and all(row.get('principal_type')!='guest' and 'guest_analytics_id' not in json.dumps(row).lower() for row in rows) for rows in account_lists)
        # Build every v1 account-detail or mutation route that must reject a Guest Trials principal.
        guest_v1_account_routes=[('GET',f"/api/v1/admin/users/{guest['user']['user_id']}",None),('POST',f"/api/v1/admin/users/{guest['user']['user_id']}/deactivate",{}),('POST',f"/api/v1/admin/users/{guest['user']['user_id']}/reactivate",{}),('POST',f"/api/v1/admin/users/{guest['user']['user_id']}/password-reset",{}),('POST',f"/api/v1/admin/users/{guest['user']['user_id']}/terms",{'accepted':True}),('POST',f"/api/v1/admin/users/{guest['user']['user_id']}/locale",{'language':'ru-RU','format_locale':'ru-RU','use_browser_locale':False})]
        # Build every v2 account-detail or mutation route that must preserve the same ownership boundary.
        guest_v2_account_routes=[('GET',f"/api/v2/admin/users/{guest['user']['user_id']}",None),('PATCH',f"/api/v2/admin/users/{guest['user']['user_id']}",{'display_name':'Not an account'}),('POST',f"/api/v2/admin/users/{guest['user']['user_id']}/password",{'password':'Not-an-account-password-1!'}),('PATCH',f"/api/v2/admin/users/{guest['user']['user_id']}/terms",{'accepted':True,'terms_version':'private-beta-1'}),('GET',f"/api/v2/admin/users/{guest['user']['user_id']}/state",None)]
        # Exercise the complete account-management surface with the authenticated Admin session.
        guest_account_denials=[api(base,path,method,body,ok=False) for method,path,body in guest_v1_account_routes+guest_v2_account_routes]
        # Require every version and mutation family to hide the temporary principal behind the same generic result.
        assert all(result['error']['code']=='NOT_FOUND' for result in guest_account_denials)
        # Re-read the disposable principal after hostile Admin account operations.
        guest_after_denials=api(base,'/api/v2/me',auth_token=token,extra_headers=guest_headers)
        # Prove the rejected account routes did not mutate or end the Guest Trials principal.
        assert guest_after_denials['user']['user_id']==guest['user']['user_id'] and guest_after_denials['user']['principal_type']=='guest'
        # Read the Admin summary through the existing authenticated Admin session.
        admin_summary=api(base,'/api/v2/admin/guest-trials')['guest_trials']
        # Require funnel, game, recent, cleanup, and filter surfaces from the v2 contract.
        assert all(key in admin_summary for key in ('funnel','funnel_rates','metrics','games','recent','cleanup','filters')) and admin_summary['funnel']['lobby_reached']>=1 and admin_summary['metrics']['fake_tokens_only'] is True
        # Apply the complete game, completion, and sanitized error filters through the v2 contract.
        filtered_summary=api(base,'/api/v2/admin/guest-trials?game=slots&completed=yes&error_category=VALIDATION_ERROR')['guest_trials']
        # Require authoritative ledger aggregates, game metrics, and exact filter echoing.
        assert filtered_summary['started_total']>=1 and filtered_summary['metrics']['wagered']>=1 and filtered_summary['games'][0]['game']=='slots' and filtered_summary['games'][0]['errors']>=1 and filtered_summary['filters']['completed']=='yes' and filtered_summary['filters']['error_category']=='VALIDATION_ERROR'
        # Reject malformed bounded-time filters instead of silently widening the Admin result.
        invalid_time=api(base,'/api/v2/admin/guest-trials?since=not-a-time',ok=False)
        # Require the standard validation envelope without reflecting query content.
        assert invalid_time['error']['code']=='VALIDATION_ERROR'
        # Find the test guest's de-identified analytics row without using auth or player identifiers.
        analytics_id=guest['user']['guest_analytics_id']
        # Read the explicit list route through Admin authorization.
        sessions=api(base,'/api/v2/admin/guest-trials/sessions?limit=100')['sessions']
        # Require the unrelated analytics id to be discoverable in the retained Admin list.
        assert any(row.get('analytics_id')==analytics_id for row in sessions)
        # Read the exact analytics-only detail route.
        detail=api(base,f'/api/v2/admin/guest-trials/sessions/{analytics_id}')['guest_trial']
        # Serialize only for forbidden-field assertions and never print the result.
        detail_text=json.dumps(detail).lower()
        # Prove the detail is de-identified and carries only the expected analytics key.
        assert detail['analytics_id']==analytics_id and all(field not in detail_text for field in ('auth_token','browser_nonce','csrf_token','email','player_id','session_id','user_id','user_agent'))
        # Apply fixed retention through the Admin-only v2 route.
        cleanup=api(base,'/api/v2/admin/guest-trials/cleanup','POST',{})['cleanup']
        # Require identifier-free completion fields.
        assert cleanup['raw_removed']>=0 and cleanup['aggregate_removed']>=0 and cleanup['completed_at']
        # Capture the exact guest wallet and ledger before assisted conversion.
        conversion_balance=auth_core.current_user_payload(guest['session'],guest['user'])['player']['token_balance']; conversion_ledger=ledger.read_recent(guest['user']['player_id'],100)
        # Submit one explicitly confirmed Admin-assisted conversion using only the visible analytics id.
        assisted_request={'guest_identity':analytics_id,'email':'api-assisted-guest@example.test','password':'ApiAssistedPassw0rd!23','display_name':'API Assisted Guest','terms_version':'private-beta-1','accepted':True,'confirm':True,'idempotency_key':'api-admin-assisted-conversion-key'}
        # Execute the additive v2 route through the authenticated Admin session.
        converted=api(base,'/api/v2/admin/guest-trials/convert','POST',assisted_request)
        # Mark the fixture converted before any later assertion can trigger teardown.
        guest_converted=True
        # Resolve the durable account to prove exact player adoption and no ledger movement.
        converted_account=auth_core.find_user_by_email('api-assisted-guest@example.test')
        # Require the self-service result shape, exact balance, exact player, and unchanged ledger rows.
        assert set(converted)=={'status','replayed','email','display_name','balance','player_preserved'} and converted['status']=='converted' and converted['player_preserved'] is True and converted['balance']==conversion_balance and converted_account['player_id']==guest['user']['player_id'] and ledger.read_recent(guest['user']['player_id'],100)==conversion_ledger
        # Require the de-identified lifecycle row to become terminal without exposing its account or player owner.
        assert guest_analytics.detail(analytics_id)['end_reason']=='converted'
        # Replay the exact operation to prove the route never creates a second account or wallet.
        replayed=api(base,'/api/v2/admin/guest-trials/convert','POST',assisted_request)
        # Require one stable replay result and one durable account owner for the original player.
        assert replayed['replayed'] is True and replayed['email']==converted['email'] and len([user for user in auth_core.load_users().get('users',[]) if user.get('player_id')==guest['user']['player_id'] and not auth_core.is_guest(user)])==1
    # End the disposable test guest even when an Admin assertion fails.
    finally:
        # Use canonical teardown only while the fixture remains a disposable active guest.
        if not guest_converted: auth_core.end_guest_trial(guest['user'],'revoked')
    # Prove the ended bearer and browser proof cannot resume the trial.
    ended=api(base,'/api/v2/me',ok=False,auth_token=token,extra_headers=guest_headers)
    # Require a terminal authentication or inactive-identity error envelope.
    assert ended['error']['code'] in ('FORBIDDEN','UNAUTHORIZED')

# Define the run_api_tests function used by this module.
def run_api_tests():
    # Discover the compatibility runner and every extracted API-area source without importing case modules. (TEST-242)
    api_source_paths=api_case_inventory.api_case_source_paths(Path(__file__),API_CASES_ROOT)
    # Discover exact permanent non-Browser registrations across the current source topology. (TEST-242)
    current_api_case_ids=api_case_inventory.discover_api_case_ids(api_source_paths)
    # Fail before any listener or provider opens when count, IDs, ordering, or duplication drift. (TEST-242)
    api_case_inventory.validate_api_case_inventory(current_api_case_ids,API_CASE_INVENTORY_PATH)
    # Refuse literal always-true mapped predicates across the compatibility runner and extracted areas. (issue #414)
    runner_source='\n'.join(source_path.read_text(encoding='utf-8') for source_path in api_source_paths)
    # Fail the whole lane immediately when a tautological mapped predicate reappears anywhere in API case source.
    assert re.search(r"assert_condition\(\s*True\s*,",runner_source) is None, 'tautological always-true mapped predicate found in API case source'
    # Delegate listener-free harness-foundation registrations at the pre-listener boundary. (TEST-242)
    api_harness_foundation.run_cases(run_case)
    # Build one reusable subprocess host so bundle suites that redirect data directories at import can never pollute this process or the shared API server environment. (issues #403, #405, #411, #412)
    def run_unit_module(module_name, failure_message):
        # Execute the focused suite with a fresh interpreter exactly like the security probe host.
        result=subprocess.run([sys.executable,'-m','unittest',module_name,'-v'],cwd=str(ROOT),capture_output=True,text=True,timeout=600)
        # Fail the named central case when any focused assertion fails, preserving the child's diagnostic tail.
        if result.returncode!=0: raise AssertionError(f'{failure_message}: {result.stderr[-1500:]}')
    # Register the first extracted API area at the exact historical execution point. (TEST-242)
    api_governance.run_cases(run_case,run_unit_module,ROOT)
    # Delegate the complete listener-free atomic game-state area at its historical point. (TEST-242)
    api_game_atomic.run_cases(run_case,run_unit_module)
    # Delegate the complete listener-free money-integrity area at its historical point. (TEST-242)
    api_money_integrity.run_cases(run_case,run_unit_module)
    # Delegate the complete listener-free Admin policy area at its historical point. (TEST-242)
    api_admin_policy.run_cases(run_case,run_unit_module)
    # Delegate the complete listener-free game lifecycle area at its historical point. (TEST-242)
    api_game_lifecycle.run_cases(run_case,run_unit_module)
    # Delegate the complete listener-free delivery-infrastructure area at its historical point. (TEST-242)
    api_delivery_infrastructure.run_cases(run_case)
    # Execute the bounded Roulette anti-strobe proof without opening a listener or browser.
    def run_roulette_motion_tests():
        # Import the focused suite only when its mapped API case runs.
        from tests import roulette_motion_tests
        # Load exactly the tracked legacy-curve compatibility assertions.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(roulette_motion_tests.RouletteMotionTests)
        # Execute the suite with concise in-process reporting.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the central named case when any curve assertion failed or errored.
        if not result.wasSuccessful():
            # Preserve unittest detail while keeping the named failure stable.
            raise AssertionError('roulette motion compatibility suite failed')
    # Execute one dependency-light Node frontend suite without opening a listener or browser.
    def run_game_frontend_node_test(relative_path, failure_message):
        # Let controlled local environments point at the bundled runtime while hosted CI uses its ordinary node command.
        node_binary=os.environ.get('CASINO_NODE_BINARY','node')
        # Run exactly one game-owned test module through the dependency-free Node test runner.
        result=subprocess.run([node_binary,'--test',str(ROOT/relative_path)],cwd=str(ROOT),capture_output=True,text=True,timeout=120)
        # Fail the named central case with a bounded diagnostic tail when focused behavior regresses.
        if result.returncode!=0: raise AssertionError(f'{failure_message}: {(result.stdout+result.stderr)[-1800:]}')
    # Delegate the complete frontend-presentation area while the runner retains process execution. (TEST-242)
    api_frontend_presentation.run_cases(run_case,run_roulette_motion_tests,run_game_frontend_node_test)
    # Delegate listener-free documentation, settings, and receipt cases at their historical execution point.
    api_self_service_foundation.run_cases(run_case)
    # Delegate listener-free specialized-game and cross-game-polish cases at their historical point.
    api_specialized_game_acceptance.run_cases(run_case)
    # Delegate listener-free player-foundation registrations at their historical execution point. (TEST-242)
    api_player_foundation.run_cases(run_case,run_game_frontend_node_test)
    # Delegate the listener-free GameCore and mobile-foundation block at its historical point. (TEST-242)
    api_gamecore_mobile_foundation.run_cases(run_case)
    # Delegate the listener-free catalog-expansion block at its exact historical point. (TEST-242)
    api_catalog_expansion.run_cases(run_case)
    # Delegate the listener-free Keno and Admin-foundation block at its exact historical point. (TEST-242)
    api_keno_admin_foundation.run_cases(run_case)
    # Delegate the listener-free security and UI-foundation block at its exact historical point. (TEST-242)
    api_security_ui_foundation.run_cases(run_case)
    # Delegate the listener-free authentication infrastructure area at its exact historical point. (TEST-242)
    api_auth.run_cases(run_case,run_oauth_mock_tests,validate_deployment_bootstrap,run_server_authority_tests)
    # Delegate the listener-free feedback area at its exact historical point. (TEST-242)
    api_feedback.run_cases(run_case)
    # Delegate the listener-free Guest Trial area at its exact historical point. (TEST-242)
    api_guest.run_cases(run_case,validate_guest_lifecycle,validate_guest_analytics,validate_guest_contracts)
    # Set proc,base to the value needed for the next operation.
    proc,base=start_server()
    # Start protected logic so failures can be handled safely.
    try:
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
        # Delegate the live Guest/Admin registration without transferring server lifecycle ownership. (TEST-242)
        api_admin_guest.run_cases(run_case,base,validate_guest_admin_api)
        # Delegate the pre-reset non-finite money case without transferring reset ownership. (TEST-242)
        api_live_infrastructure.run_money_boundary_case(run_case,base,api,raw_api,ROOT)
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
        # Delegate the post-reset Operations, OAuth, mail, and invitation cases. (TEST-242)
        api_live_infrastructure.run_service_cases(run_case,base,api,ROOT)
        # Define the auth_backend function used by this module.
        def auth_backend():
            # Set blocked to the value needed for the next operation.
            blocked=api(base,'/api/v1/casino/state',ok=False,auth_token=None); assert blocked['error']['code']=='UNAUTHORIZED'
            # Set login to the value needed for the next operation.
            login=api(base,'/api/v2/auth/login','POST',{'email':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD},auth_token=None); assert login['user']['role']=='admin'
            # Set token to the value needed for the next operation.
            token=login['session']['token']; assert token
            # Verify the published username field remains a compatible alias for the same email credential.
            aliased_login=api(base,'/api/v2/auth/login','POST',{'username':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD},auth_token=None); assert aliased_login['user']['email']==DEFAULT_AUTH_EMAIL
            # Require concurrent same-account logins to retain independent valid sessions (issue #226, SESSION-007).
            assert api(base,'/api/v2/auth/session',auth_token=token)['user']['email']==DEFAULT_AUTH_EMAIL
            # Select the second concurrent session token while its predecessor stays valid.
            second_token=aliased_login['session']['token']; assert second_token and second_token!=token
            # Require the second concurrent session to authenticate independently of the first.
            assert api(base,'/api/v2/auth/session',auth_token=second_token)['user']['email']==DEFAULT_AUTH_EMAIL
            # Continue the compatible auth flow using the most recent session token.
            token=second_token
            # Set session to the value needed for the next operation.
            session=api(base,'/api/v2/auth/session',auth_token=token); assert session['user']['email']==DEFAULT_AUTH_EMAIL
            # Set me to the value needed for the next operation.
            me=api(base,'/api/v2/me',auth_token=token); assert me['player']['player_id']=='human'
            # Set terms to the value needed for the next operation.
            terms=api(base,'/api/v2/me/terms',auth_token=token); assert terms['terms']['accepted'] is True
            # Set out to the value needed for the next operation.
            out=api(base,'/api/v2/auth/logout','POST',{},auth_token=token); assert out['logged_out'] is True
            api(base,'/api/v2/auth/session',ok=False,auth_token=token)
            # Set inactive_email to the value needed for the next operation.
            inactive_email='inactive@example.local'
            # Start protected logic so repeated local runs can reuse the same inactive user.
            try:
                auth_core.create_user(inactive_email,'inactive-password','Inactive Player')
            # Handle the expected failure path for the protected logic.
            except Exception:
                # Intentionally leave this block empty.
                pass
            auth_core.set_user_status(inactive_email,'inactive')
            # Set inactive to the value needed for the next operation.
            inactive=api(base,'/api/v2/auth/login','POST',{'email':inactive_email,'password':'inactive-password'},ok=False,auth_token=None); assert inactive['error']['code']=='FORBIDDEN'
            # Refresh the harness Admin session after the concurrent-session and logout proof (issue #226).
            login_default_user(base)
        # Delegate the final live authentication registration without transferring listener or session ownership.
        api_live_authentication.run_cases(run_case,auth_backend)
        # Store wallet integrity evidence for the later server-restart persistence check.
        integrity_state={}
        # Define wallet_auth_integrity to exercise canonical users, authorization, and token movement through the live backend.
        def wallet_auth_integrity():
            # Create two login-ready canonical users through the authenticated Admin v2 API.
            user_a=api(base,'/api/v2/admin/users','POST',{'username':'wallet-a@example.local','password':'wallet-a-password','display_name':'Wallet A','roles':['player'],'locale':'en-US'})
            # Create the second isolated canonical identity through the same API.
            user_b=api(base,'/api/v2/admin/users','POST',{'username':'wallet-b@example.local','password':'wallet-b-password','display_name':'Wallet B','roles':['player'],'locale':'en-US'})
            # Log in both Admin-created users through the real auth backend.
            login_a=api(base,'/api/v2/auth/login','POST',{'username':'wallet-a@example.local','password':'wallet-a-password'},auth_token=None)
            # Store user A's bearer token for isolated requests.
            token_a=login_a['session']['token']
            # Log in user B independently so session bindings cannot share state.
            login_b=api(base,'/api/v2/auth/login','POST',{'username':'wallet-b@example.local','password':'wallet-b-password'},auth_token=None)
            # Store user B's bearer token for isolated requests.
            token_b=login_b['session']['token']
            # Verify required terms prevent wallet/game mutation before acceptance.
            terms_blocked=api(base,'/api/v2/me/tokens/add','POST',{'amount':1},ok=False,auth_token=token_a); assert terms_blocked['error']['code']=='FORBIDDEN'
            # Accept the published terms route for both canonical identities.
            api(base,'/api/v2/auth/terms/accept','POST',{'terms_version':'private-beta-1','accepted':True},auth_token=token_a)
            # Accept terms for user B without affecting user A metadata.
            api(base,'/api/v2/auth/terms/accept','POST',{'terms_version':'private-beta-1','accepted':True},auth_token=token_b)
            # Read user A's baseline ledger before the requested token credit.
            ledger_before=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']
            # Add exactly 250 play tokens through the authenticated v2 wallet route.
            added_a=api(base,'/api/v2/me/tokens/add','POST',{'amount':250,'reason':'integrity_test'},auth_token=token_a)
            # Add the same isolated balance to user B for two-user game checks.
            added_b=api(base,'/api/v2/me/tokens/add','POST',{'amount':250,'reason':'integrity_test'},auth_token=token_b)
            # Read user A's ledger after the wallet credit.
            ledger_after=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']
            # Count wallet credits before and after so identifier formats cannot hide duplicates.
            credits_before=[row for row in ledger_before if row.get('transaction_type')=='PLAY_TOKENS_ADDED']
            # Select all wallet credits after the request for exact delta validation.
            credits_after=[row for row in ledger_after if row.get('transaction_type')=='PLAY_TOKENS_ADDED']
            # Verify the token endpoint returned the canonical player and exactly one new ledger event.
            assert added_a['player_id']==user_a['player_id'] and added_a['token_balance']==250 and len(credits_after)==len(credits_before)+1 and credits_after[-1]['amount']==250
            # Verify user B received only its own wallet credit.
            assert added_b['player_id']==user_b['player_id'] and added_b['token_balance']==250
            # Read the same balance through current-user state.
            me_a=api(base,'/api/v2/me',auth_token=token_a)
            # Read the authorized Admin surface for the same canonical identity.
            admin_a=api(base,f'/api/v2/admin/users/{user_a["user_id"]}')
            # Verify login/current-user/Admin all resolve the same canonical wallet value after refresh.
            assert me_a['player']['token_balance']==250 and admin_a['token_balance']==250 and api(base,'/api/v2/me',auth_token=token_a)['player']['token_balance']==250
            # Verify normal-user player listing and casino state expose only the bound wallet.
            assert [row['player_id'] for row in api(base,'/api/v1/players',auth_token=token_a)['players']]==[user_a['player_id']]
            # Verify casino state keeps global wallet and ledger rows outside the normal session.
            scoped_state=api(base,'/api/v1/casino/state',auth_token=token_a); assert [row['player_id'] for row in scoped_state['players']]==[user_a['player_id']] and all(row['player_id']==user_a['player_id'] for row in scoped_state['recent_ledger']) and isinstance(scoped_state['online_player_count'],int) and scoped_state['online_player_count']>=1
            # Verify direct cross-player reads fail with the standard forbidden envelope.
            cross_read=api(base,f'/api/v1/players/{user_b["player_id"]}',ok=False,auth_token=token_a); assert cross_read['error']['code']=='FORBIDDEN'
            # Submit user B's id maliciously; middleware must bind the bet to user A instead.
            cross_bet=api(base,'/api/v1/games/roulette/bets','POST',{'player_id':user_b['player_id'],'amount':10,'bet_type':'straight','covered_numbers':['17'],'label':'17'},auth_token=token_a)['bet']
            # Verify the action used user A and did not debit user B.
            assert cross_bet['player_id']==user_a['player_id'] and api(base,'/api/v2/me',auth_token=token_b)['player']['token_balance']==250
            # Complete Roulette for user A while attempting to force a server-owned outcome.
            roulette_a=api(base,'/api/v1/games/roulette/spin','POST',{'player_id':user_b['player_id'],'force_result':'17'},auth_token=token_a)
            # Place user B's own Roulette wager while submitting user A's id.
            roulette_b_bet=api(base,'/api/v1/games/roulette/bets','POST',{'player_id':user_a['player_id'],'amount':10,'bet_type':'straight','covered_numbers':['18'],'label':'18'},auth_token=token_b)['bet']
            # Settle user B's Roulette wager through its authenticated session.
            roulette_b=api(base,'/api/v1/games/roulette/spin','POST',{'player_id':user_a['player_id'],'force_result':'18'},auth_token=token_b)
            # Verify both Roulette actions used session-derived identities and returned server-owned wheel outcomes.
            assert roulette_b_bet['player_id']==user_b['player_id'] and str(roulette_a['round']['result']) in {str(number) for number in range(37)}|{'00'} and str(roulette_b['round']['result']) in {str(number) for number in range(37)}|{'00'} and all(row['bet']['player_id']==user_a['player_id'] for row in roulette_a['settlements']) and all(row['bet']['player_id']==user_b['player_id'] for row in roulette_b['settlements'])
            # Play Slots independently for both users to cover a second game without state leakage.
            slot_a=api(base,'/api/v1/games/slots/spin','POST',{'player_id':user_b['player_id'],'active_lines':1,'line_bet':1},auth_token=token_a)['spin']
            # Play Slots for user B through its own session binding.
            slot_b=api(base,'/api/v1/games/slots/spin','POST',{'player_id':user_a['player_id'],'active_lines':3,'line_bet':1},auth_token=token_b)['spin']
            # Verify each Slots result is stored under the authenticated player regardless of submitted ids.
            assert api(base,f'/api/v1/games/slots/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']['last_spins'][-1]['round_id']==slot_a['round_id']
            # Verify user B reads its own distinct Slots result.
            assert api(base,f'/api/v1/games/slots/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']['last_spins'][-1]['round_id']==slot_b['round_id']
            # Deal Blackjack for user A while submitting user B's player id.
            blackjack_a=api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':user_b['player_id'],'bet_amount':10},auth_token=token_a)['round']
            # Deal Blackjack independently for user B while submitting user A's player id.
            blackjack_b=api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':user_a['player_id'],'bet_amount':10},auth_token=token_b)['round']
            # Verify each authenticated user owns only its own Blackjack round.
            assert blackjack_a['player_id']==user_a['player_id'] and blackjack_b['player_id']==user_b['player_id'] and blackjack_a['round_id'] in api(base,'/api/v1/games/blackjack/state',auth_token=token_a)['state']['rounds'] and blackjack_b['round_id'] in api(base,'/api/v1/games/blackjack/state',auth_token=token_b)['state']['rounds']
            # Place Baccarat wagers for both sessions while submitting the opposite player ids.
            baccarat_a_bet=api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':user_b['player_id'],'amount':10,'bet_type':'banker'},auth_token=token_a)['bet']
            # Place user B's independent Baccarat wager.
            baccarat_b_bet=api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':user_a['player_id'],'amount':10,'bet_type':'player'},auth_token=token_b)['bet']
            # Deal and settle one private Baccarat coup for each authenticated user.
            baccarat_a=api(base,'/api/v1/games/baccarat/deal','POST',{'player_id':user_b['player_id']},auth_token=token_a)
            # Settle user B's separate Baccarat state.
            baccarat_b=api(base,'/api/v1/games/baccarat/deal','POST',{'player_id':user_a['player_id']},auth_token=token_b)
            # Verify Baccarat wager ownership and private coup identifiers.
            assert baccarat_a_bet['player_id']==user_a['player_id'] and baccarat_b_bet['player_id']==user_b['player_id'] and baccarat_a['coup']['round_id']!=baccarat_b['coup']['round_id']
            # Buy Keno tickets for both sessions while submitting the opposite player ids.
            keno_a_ticket=api(base,'/api/v1/games/keno/tickets','POST',{'player_id':user_b['player_id'],'amount':5,'spots':[1,2,3]},auth_token=token_a)['ticket']
            # Buy user B's isolated Keno ticket.
            keno_b_ticket=api(base,'/api/v1/games/keno/tickets','POST',{'player_id':user_a['player_id'],'amount':5,'spots':[4,5,6]},auth_token=token_b)['ticket']
            # Draw and settle Keno independently for each authenticated user.
            keno_a=api(base,'/api/v1/games/keno/draw','POST',{'player_id':user_b['player_id']},auth_token=token_a)
            # Draw user B's separate Keno state.
            keno_b=api(base,'/api/v1/games/keno/draw','POST',{'player_id':user_a['player_id']},auth_token=token_b)
            # Verify ticket ownership and distinct Keno round identifiers.
            assert keno_a_ticket['player_id']==user_a['player_id'] and keno_b_ticket['player_id']==user_b['player_id'] and keno_a['draw']['round_id']!=keno_b['draw']['round_id']
            # Buy a Bingo card for user A and prove reset refunds the bound wallet.
            bingo_a_session=api(base,'/api/v1/games/bingo/cards','POST',{'player_id':user_b['player_id'],'amount':5,'pattern':'line'},auth_token=token_a)['session']
            # Reset user A's private Bingo session to exercise the refund path.
            bingo_a_refund=api(base,'/api/v1/games/bingo/reset','POST',{'player_id':user_b['player_id']},auth_token=token_a)
            # Buy user B's Bingo card through its independent session.
            bingo_b_session=api(base,'/api/v1/games/bingo/cards','POST',{'player_id':user_a['player_id'],'amount':5,'pattern':'line'},auth_token=token_b)['session']
            # Complete user B's Bingo session to exercise payout settlement.
            bingo_b=api(base,'/api/v1/games/bingo/auto','POST',{'player_id':user_a['player_id'],'max_calls':75},auth_token=token_b)
            # Verify Bingo identity binding, refund, and terminal settlement; competitive sessions may now end without a human win. (issue #405)
            assert bingo_a_session['player_id']==user_a['player_id'] and bingo_b_session['player_id']==user_b['player_id'] and bingo_a_refund['refunds'] and bingo_b['session']['status'] in ('won','no_win')
            # Deal user A's three-hand video poker round while submitting user B's player id.
            mhvp_a=api(base,'/api/v1/games/multi-hand-video-poker/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-mhvp-a','hand_count':3,'wager_per_hand':1},auth_token=token_a)
            # Replay user A's exact deal request so the live backend must recover one round and one wager debit.
            mhvp_a_replay=api(base,'/api/v1/games/multi-hand-video-poker/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-mhvp-a','hand_count':3,'wager_per_hand':1},auth_token=token_a)
            # Deal user B's independent five-hand round while submitting user A's player id.
            mhvp_b=api(base,'/api/v1/games/multi-hand-video-poker/rounds','POST',{'player_id':user_a['player_id'],'request_id':'wallet-mhvp-b','hand_count':5,'wager_per_hand':1},auth_token=token_b)
            # Verify session binding, idempotent replay, mode selection, and player isolation before drawing.
            assert mhvp_a['round']['player_id']==user_a['player_id'] and mhvp_b['round']['player_id']==user_b['player_id'] and mhvp_a_replay['replayed'] is True and mhvp_a_replay['round']['round_id']==mhvp_a['round']['round_id'] and mhvp_a['round']['hand_count']==3 and mhvp_b['round']['hand_count']==5 and mhvp_a['round']['round_id']!=mhvp_b['round']['round_id']
            # Persist user A's common holds through the public session-bound action.
            api(base,f'/api/v1/games/multi-hand-video-poker/rounds/{mhvp_a["round"]["round_id"]}/holds','POST',{'player_id':user_b['player_id'],'holds':[0]},auth_token=token_a)
            # Persist a distinct user B hold selection without exposing user A's round.
            api(base,f'/api/v1/games/multi-hand-video-poker/rounds/{mhvp_b["round"]["round_id"]}/holds','POST',{'player_id':user_a['player_id'],'holds':[1]},auth_token=token_b)
            # Draw and settle all three of user A's result lanes through the public endpoint.
            mhvp_a_done=api(base,f'/api/v1/games/multi-hand-video-poker/rounds/{mhvp_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id']},auth_token=token_a)
            # Draw and settle all five of user B's independent result lanes.
            mhvp_b_done=api(base,f'/api/v1/games/multi-hand-video-poker/rounds/{mhvp_b["round"]["round_id"]}/draw','POST',{'player_id':user_a['player_id']},auth_token=token_b)
            # Read each private video poker state while again submitting the opposite identity.
            mhvp_a_state=api(base,f'/api/v1/games/multi-hand-video-poker/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']
            # Read user B's private video poker state through its own authenticated session.
            mhvp_b_state=api(base,f'/api/v1/games/multi-hand-video-poker/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']
            # Verify result cardinality and reload-safe recent rounds stay isolated by session.
            assert len(mhvp_a_done['round']['results'])==3 and len(mhvp_b_done['round']['results'])==5 and mhvp_a_state['recent_rounds'][-1]['round_id']==mhvp_a['round']['round_id'] and mhvp_b_state['recent_rounds'][-1]['round_id']==mhvp_b['round']['round_id']
            # Read both ledgers after settlement to prove aggregate, exactly-once movement.
            mhvp_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; mhvp_ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']
            # Select only user A's video poker events for the completed round.
            mhvp_events_a=[row for row in mhvp_ledger_a if row.get('game')=='multi_hand_video_poker' and row.get('round_id')==mhvp_a['round']['round_id']]
            # Select only user B's video poker events for the completed round.
            mhvp_events_b=[row for row in mhvp_ledger_b if row.get('game')=='multi_hand_video_poker' and row.get('round_id')==mhvp_b['round']['round_id']]
            # Require one aggregate debit and no more than one aggregate credit for each round.
            assert sum(row.get('transaction_type')=='MHVP_WAGER_DEBIT' for row in mhvp_events_a)==1 and sum(row.get('transaction_type')=='MHVP_WAGER_DEBIT' for row in mhvp_events_b)==1 and sum(row.get('transaction_type')=='MHVP_PAYOUT_CREDIT' for row in mhvp_events_a)<=1 and sum(row.get('transaction_type')=='MHVP_PAYOUT_CREDIT' for row in mhvp_events_b)<=1
            # Deal user A's Casino War round while submitting user B's player id.
            casino_war_a=api(base,'/api/v1/games/casino-war/rounds','POST',{'player_id':user_b['player_id'],'wager':2,'action_id':'wallet-cw-start-a'},auth_token=token_a)
            # Replay user A's exact action id so the backend must return the same round without another ante.
            casino_war_a_replay=api(base,'/api/v1/games/casino-war/rounds','POST',{'player_id':user_b['player_id'],'wager':2,'action_id':'wallet-cw-start-a'},auth_token=token_a)
            # Deal user B's independent Casino War round while submitting user A's player id.
            casino_war_b=api(base,'/api/v1/games/casino-war/rounds','POST',{'player_id':user_a['player_id'],'wager':2,'action_id':'wallet-cw-start-b'},auth_token=token_b)
            # Require authenticated player ownership, distinct rounds, and an idempotent start replay.
            assert casino_war_a['round']['player_id']==user_a['player_id'] and casino_war_b['round']['player_id']==user_b['player_id'] and casino_war_a['round']['round_id']!=casino_war_b['round']['round_id'] and casino_war_a_replay['round']['round_id']==casino_war_a['round']['round_id'] and casino_war_a_replay['player']['balance']==casino_war_a['player']['balance']
            # Complete user A's round through surrender when the deterministic live deal produced a tie.
            if casino_war_a['round']['phase']=='war_decision':
                # Exercise the public surrender decision with a stable action id.
                casino_war_a=api(base,f'/api/v1/games/casino-war/rounds/{casino_war_a["round"]["round_id"]}/surrender','POST',{'player_id':user_b['player_id'],'action_id':'wallet-cw-surrender-a'},auth_token=token_a)
            # Complete user B's round through surrender when its independent deal produced a tie.
            if casino_war_b['round']['phase']=='war_decision':
                # Exercise the same decision under user B's independently bound session.
                casino_war_b=api(base,f'/api/v1/games/casino-war/rounds/{casino_war_b["round"]["round_id"]}/surrender','POST',{'player_id':user_a['player_id'],'action_id':'wallet-cw-surrender-b'},auth_token=token_b)
            # Read both private Casino War states while submitting the opposite player ids.
            casino_war_state_a=api(base,f'/api/v1/games/casino-war/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; casino_war_state_b=api(base,f'/api/v1/games/casino-war/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']
            # Require terminal settlement and newest-first private round isolation for both sessions.
            assert casino_war_a['round']['phase']=='settled' and casino_war_b['round']['phase']=='settled' and casino_war_state_a['rounds'][0]['round_id']==casino_war_a['round']['round_id'] and casino_war_state_b['rounds'][0]['round_id']==casino_war_b['round']['round_id']
            # Read both ledgers after Casino War settlement for exactly-once movement proof.
            casino_war_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; casino_war_ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']
            # Select only Casino War rows for each independently completed round.
            casino_war_events_a=[row for row in casino_war_ledger_a if row.get('game')=='casino_war' and row.get('round_id')==casino_war_a['round']['round_id']]; casino_war_events_b=[row for row in casino_war_ledger_b if row.get('game')=='casino_war' and row.get('round_id')==casino_war_b['round']['round_id']]
            # Require one ante, unique stable action ids, and complete prepared settlement counts for each user.
            assert sum(row.get('transaction_type')=='CASINO_WAR_ANTE_DEBIT' for row in casino_war_events_a)==1 and sum(row.get('transaction_type')=='CASINO_WAR_ANTE_DEBIT' for row in casino_war_events_b)==1 and len({(row.get('details') or {}).get('casino_war_action_id') for row in casino_war_events_a})==len(casino_war_events_a) and len({(row.get('details') or {}).get('casino_war_action_id') for row in casino_war_events_b})==len(casino_war_events_b) and casino_war_a['round']['settlement']['complete'] and casino_war_b['round']['settlement']['complete'] and casino_war_a['round']['settlement']['required_actions']==casino_war_a['round']['settlement']['committed_actions'] and casino_war_b['round']['settlement']['required_actions']==casino_war_b['round']['settlement']['committed_actions']
            # Cover every Big Six outcome so each real spin necessarily commits a settlement credit.
            big_six_wagers={'one':1,'two':1,'five':1,'ten':1,'twenty':1,'joker':1,'crest':1}
            # Spin for user A while submitting user B's player id to challenge the shared session resolver.
            big_six_a=api(base,'/api/v1/games/big-six-wheel/spins','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-big-six-a','wagers':big_six_wagers},auth_token=token_a)
            # Replay user A's exact request identity and semantic wager map through the real backend.
            big_six_a_replay=api(base,'/api/v1/games/big-six-wheel/spins','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-big-six-a','wagers':big_six_wagers},auth_token=token_a)
            # Reuse the request identity with changed wagers so conflict detection must fail closed.
            big_six_conflict=api(base,'/api/v1/games/big-six-wheel/spins','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-big-six-a','wagers':{'one':2}},ok=False,auth_token=token_a)
            # Spin independently for user B while again submitting the opposite authenticated identity.
            big_six_b=api(base,'/api/v1/games/big-six-wheel/spins','POST',{'player_id':user_a['player_id'],'client_request_id':'wallet-big-six-b','wagers':big_six_wagers},auth_token=token_b)
            # Read both private Big Six states while submitting hostile query identities.
            big_six_state_a=api(base,f'/api/v1/games/big-six-wheel/state?player_id={user_b["player_id"]}',auth_token=token_a); big_six_state_b=api(base,f'/api/v1/games/big-six-wheel/state?player_id={user_a["player_id"]}',auth_token=token_b)
            # Require session ownership, independent rounds, exact replay, conflict rejection, and isolated history.
            assert big_six_a['round']['player_id']==user_a['player_id'] and big_six_b['round']['player_id']==user_b['player_id'] and big_six_a['round']['round_id']!=big_six_b['round']['round_id'] and big_six_a_replay['replayed'] is True and big_six_a_replay['round']['round_id']==big_six_a['round']['round_id'] and big_six_conflict['error']['code']=='CONFLICT' and big_six_state_a['recent_rounds'][-1]['round_id']==big_six_a['round']['round_id'] and big_six_state_b['recent_rounds'][-1]['round_id']==big_six_b['round']['round_id']
            # Read both ledgers after Big Six settlement for aggregate exactly-once movement proof.
            big_six_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; big_six_ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']
            # Select only Big Six events for each independently completed round.
            big_six_events_a=[row for row in big_six_ledger_a if row.get('game')=='big_six_wheel' and row.get('round_id')==big_six_a['round']['round_id']]; big_six_events_b=[row for row in big_six_ledger_b if row.get('game')=='big_six_wheel' and row.get('round_id')==big_six_b['round']['round_id']]
            # Require one aggregate debit, one covered-outcome credit, and unique deterministic action keys per user.
            assert sum(row.get('transaction_type')=='BIG_SIX_WAGER_DEBIT' for row in big_six_events_a)==1 and sum(row.get('transaction_type')=='BIG_SIX_WAGER_DEBIT' for row in big_six_events_b)==1 and sum(row.get('transaction_type')=='BIG_SIX_SETTLEMENT_CREDIT' for row in big_six_events_a)==1 and sum(row.get('transaction_type')=='BIG_SIX_SETTLEMENT_CREDIT' for row in big_six_events_b)==1 and len({(row.get('details') or {}).get('idempotency_key') for row in big_six_events_a})==len(big_six_events_a) and len({(row.get('details') or {}).get('idempotency_key') for row in big_six_events_b})==len(big_six_events_b)
            # Deal user A's Red Dog opening while submitting user B's player id to challenge session binding.
            red_dog_a=api(base,'/api/v1/games/red-dog/rounds','POST',{'player_id':user_b['player_id'],'wager':2,'action_id':'wallet-red-dog-start-a'},auth_token=token_a)
            # Replay user A's exact command so the backend must return the same logical round and wallet.
            red_dog_a_replay=api(base,'/api/v1/games/red-dog/rounds','POST',{'player_id':user_b['player_id'],'wager':2,'action_id':'wallet-red-dog-start-a'},auth_token=token_a)
            # Reuse the action id with a changed wager so immutable fingerprint validation fails closed.
            red_dog_conflict=api(base,'/api/v1/games/red-dog/rounds','POST',{'player_id':user_b['player_id'],'wager':3,'action_id':'wallet-red-dog-start-a'},ok=False,auth_token=token_a)
            # Deal user B's independent Red Dog opening while submitting user A's player id.
            red_dog_b=api(base,'/api/v1/games/red-dog/rounds','POST',{'player_id':user_a['player_id'],'wager':2,'action_id':'wallet-red-dog-start-b'},auth_token=token_b)
            # Require authenticated ownership, independent rounds, stable replay, unchanged replay balance, and conflict rejection.
            assert red_dog_a['round']['player_id']==user_a['player_id'] and red_dog_b['round']['player_id']==user_b['player_id'] and red_dog_a['round']['round_id']!=red_dog_b['round']['round_id'] and red_dog_a_replay['replayed'] is True and red_dog_a_replay['round']['round_id']==red_dog_a['round']['round_id'] and red_dog_a_replay['player']['balance']==red_dog_a['player']['balance'] and red_dog_conflict['error']['code']=='CONFLICT'
            # Complete user A's normal spread through the no-raise call action when a decision is required.
            if red_dog_a['round']['phase']=='raise_decision':
                # Exercise the public call endpoint under the same hostile caller identity.
                red_dog_a=api(base,f'/api/v1/games/red-dog/rounds/{red_dog_a["round"]["round_id"]}/call','POST',{'player_id':user_b['player_id'],'action_id':'wallet-red-dog-call-a'},auth_token=token_a)
            # Complete user B's normal spread through the matching raise action when a decision is required.
            if red_dog_b['round']['phase']=='raise_decision':
                # Exercise the public raise endpoint under user B's independent session binding.
                red_dog_b=api(base,f'/api/v1/games/red-dog/rounds/{red_dog_b["round"]["round_id"]}/raise','POST',{'player_id':user_a['player_id'],'action_id':'wallet-red-dog-raise-b'},auth_token=token_b)
            # Read both private Red Dog states while again submitting the opposite player identities.
            red_dog_state_a=api(base,f'/api/v1/games/red-dog/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; red_dog_state_b=api(base,f'/api/v1/games/red-dog/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']
            # Require terminal settlement and newest-first private history isolation for both users.
            assert red_dog_a['round']['phase']=='settled' and red_dog_b['round']['phase']=='settled' and red_dog_state_a['rounds'][0]['round_id']==red_dog_a['round']['round_id'] and red_dog_state_b['rounds'][0]['round_id']==red_dog_b['round']['round_id']
            # Read both ledgers after Red Dog settlement for exactly-once movement proof.
            red_dog_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; red_dog_ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']
            # Select only Red Dog rows for each independently completed round.
            red_dog_events_a=[row for row in red_dog_ledger_a if row.get('game')=='red_dog' and row.get('round_id')==red_dog_a['round']['round_id']]; red_dog_events_b=[row for row in red_dog_ledger_b if row.get('game')=='red_dog' and row.get('round_id')==red_dog_b['round']['round_id']]
            # Require one ante debit, unique stable ledger action ids, and complete settlement for each session.
            assert sum(row.get('transaction_type')=='RED_DOG_WAGER_DEBIT' for row in red_dog_events_a)==1 and sum(row.get('transaction_type')=='RED_DOG_WAGER_DEBIT' for row in red_dog_events_b)==1 and len({(row.get('details') or {}).get('red_dog_action_id') for row in red_dog_events_a})==len(red_dog_events_a) and len({(row.get('details') or {}).get('red_dog_action_id') for row in red_dog_events_b})==len(red_dog_events_b) and red_dog_a['round']['settlement']['complete'] and red_dog_b['round']['settlement']['complete'] and red_dog_a['round']['settlement']['required_actions']==red_dog_a['round']['settlement']['committed_actions'] and red_dog_b['round']['settlement']['required_actions']==red_dog_b['round']['settlement']['committed_actions']
            # Deal user A's Dragon Tiger round while submitting user B's player id to challenge session binding.
            dragon_tiger_a=api(base,'/api/v1/games/dragon-tiger/rounds','POST',{'player_id':user_b['player_id'],'bet':'dragon','wager':2,'action_id':'wallet-dragon-tiger-a'},auth_token=token_a)
            # Replay user A's exact Dragon Tiger command to prove the ledger movements remain exactly once.
            dragon_tiger_a_replay=api(base,'/api/v1/games/dragon-tiger/rounds','POST',{'player_id':user_b['player_id'],'bet':'dragon','wager':2,'action_id':'wallet-dragon-tiger-a'},auth_token=token_a)
            # Reuse the action id with a changed wager so immutable request-fingerprint validation fails closed.
            dragon_tiger_conflict=api(base,'/api/v1/games/dragon-tiger/rounds','POST',{'player_id':user_b['player_id'],'bet':'dragon','wager':3,'action_id':'wallet-dragon-tiger-a'},ok=False,auth_token=token_a)
            # Deal user B's independent Dragon Tiger round while submitting user A's player id.
            dragon_tiger_b=api(base,'/api/v1/games/dragon-tiger/rounds','POST',{'player_id':user_a['player_id'],'bet':'tiger','wager':2,'action_id':'wallet-dragon-tiger-b'},auth_token=token_b)
            # Require authenticated ownership, independent results, stable replay, unchanged replay balance, and conflict rejection.
            assert dragon_tiger_a['round']['player_id']==user_a['player_id'] and dragon_tiger_b['round']['player_id']==user_b['player_id'] and dragon_tiger_a['round']['round_id']!=dragon_tiger_b['round']['round_id'] and dragon_tiger_a_replay['replayed'] is True and dragon_tiger_a_replay['round']==dragon_tiger_a['round'] and dragon_tiger_a_replay['player']['balance']==dragon_tiger_a['player']['balance'] and dragon_tiger_conflict['error']['code']=='CONFLICT'
            # Read both private Dragon Tiger states while again submitting the opposite player identities.
            dragon_tiger_state_a=api(base,f'/api/v1/games/dragon-tiger/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; dragon_tiger_state_b=api(base,f'/api/v1/games/dragon-tiger/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']
            # Require newest-first private settled history isolation for both authenticated users.
            assert dragon_tiger_state_a['recent_rounds'][0]['round_id']==dragon_tiger_a['round']['round_id'] and dragon_tiger_state_b['recent_rounds'][0]['round_id']==dragon_tiger_b['round']['round_id']
            # Read both ledgers after Dragon Tiger settlement for exactly-once movement proof.
            dragon_tiger_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; dragon_tiger_ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']
            # Select only Dragon Tiger rows for each independently completed round.
            dragon_tiger_events_a=[row for row in dragon_tiger_ledger_a if row.get('game')=='dragon_tiger' and row.get('round_id')==dragon_tiger_a['round']['round_id']]; dragon_tiger_events_b=[row for row in dragon_tiger_ledger_b if row.get('game')=='dragon_tiger' and row.get('round_id')==dragon_tiger_b['round']['round_id']]
            # Require one wager debit, at most one settlement credit, and unique deterministic action keys per session.
            assert sum(row.get('transaction_type')=='DRAGON_TIGER_WAGER_DEBIT' for row in dragon_tiger_events_a)==1 and sum(row.get('transaction_type')=='DRAGON_TIGER_WAGER_DEBIT' for row in dragon_tiger_events_b)==1 and sum(row.get('transaction_type')=='DRAGON_TIGER_SETTLEMENT_CREDIT' for row in dragon_tiger_events_a)<=1 and sum(row.get('transaction_type')=='DRAGON_TIGER_SETTLEMENT_CREDIT' for row in dragon_tiger_events_b)<=1 and len({(row.get('details') or {}).get('idempotency_key') for row in dragon_tiger_events_a})==len(dragon_tiger_events_a) and len({(row.get('details') or {}).get('idempotency_key') for row in dragon_tiger_events_b})==len(dragon_tiger_events_b)
            # Deal user A's Hi-Lo opening card while submitting user B's player id to challenge session binding.
            hi_lo_a=api(base,'/api/v1/games/hi-lo/rounds','POST',{'player_id':user_b['player_id'],'wager':2,'action_id':'wallet-hi-lo-deal-a'},auth_token=token_a)
            # Replay user A's exact deal so the backend must preserve its hidden result and one wager debit.
            hi_lo_a_replay=api(base,'/api/v1/games/hi-lo/rounds','POST',{'player_id':user_b['player_id'],'wager':2,'action_id':'wallet-hi-lo-deal-a'},auth_token=token_a)
            # Reuse the deal identity with a changed wager so immutable fingerprint validation fails closed.
            hi_lo_conflict=api(base,'/api/v1/games/hi-lo/rounds','POST',{'player_id':user_b['player_id'],'wager':3,'action_id':'wallet-hi-lo-deal-a'},ok=False,auth_token=token_a)
            # Deal user B's independent opening card while again submitting the opposite player id.
            hi_lo_b=api(base,'/api/v1/games/hi-lo/rounds','POST',{'player_id':user_a['player_id'],'wager':2,'action_id':'wallet-hi-lo-deal-b'},auth_token=token_b)
            # Require authenticated ownership, independent rounds, exact replay, conflict rejection, and a protected next card.
            assert hi_lo_a['round']['player_id']==user_a['player_id'] and hi_lo_b['round']['player_id']==user_b['player_id'] and hi_lo_a['round']['round_id']!=hi_lo_b['round']['round_id'] and hi_lo_a_replay['replayed'] is True and hi_lo_a_replay['round']==hi_lo_a['round'] and hi_lo_a_replay['player']['balance']==hi_lo_a['player']['balance'] and hi_lo_conflict['error']['code']=='CONFLICT' and 'next_card' not in hi_lo_a['round'] and 'next_card' not in hi_lo_b['round']
            # Settle user A's active choice through one public higher prediction under the bound session.
            hi_lo_a_done=api(base,f'/api/v1/games/hi-lo/rounds/{hi_lo_a["round"]["round_id"]}/guesses','POST',{'player_id':user_b['player_id'],'guess':'higher','action_id':'wallet-hi-lo-guess-a'},auth_token=token_a)
            # Replay the identical settlement so no refund or payout can be duplicated.
            hi_lo_a_done_replay=api(base,f'/api/v1/games/hi-lo/rounds/{hi_lo_a["round"]["round_id"]}/guesses','POST',{'player_id':user_b['player_id'],'guess':'higher','action_id':'wallet-hi-lo-guess-a'},auth_token=token_a)
            # Settle user B's independent active choice through the other documented direction.
            hi_lo_b_done=api(base,f'/api/v1/games/hi-lo/rounds/{hi_lo_b["round"]["round_id"]}/guesses','POST',{'player_id':user_a['player_id'],'guess':'lower','action_id':'wallet-hi-lo-guess-b'},auth_token=token_b)
            # Read both private Hi-Lo states while supplying hostile query identities.
            hi_lo_state_a=api(base,f'/api/v1/games/hi-lo/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; hi_lo_state_b=api(base,f'/api/v1/games/hi-lo/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']
            # Require terminal private history, revealed result cards, and stable settlement replay for both sessions.
            assert hi_lo_a_done['round']['phase']=='settled' and hi_lo_b_done['round']['phase']=='settled' and hi_lo_a_done['round'].get('next_card') and hi_lo_b_done['round'].get('next_card') and hi_lo_a_done_replay['replayed'] is True and hi_lo_a_done_replay['round']==hi_lo_a_done['round'] and hi_lo_a_done_replay['player']['balance']==hi_lo_a_done['player']['balance'] and hi_lo_state_a['recent_rounds'][-1]['round_id']==hi_lo_a['round']['round_id'] and hi_lo_state_b['recent_rounds'][-1]['round_id']==hi_lo_b['round']['round_id']
            # Read both ledgers after Hi-Lo settlement for exactly-once debit, refund, and payout proof.
            hi_lo_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; hi_lo_ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']
            # Select only Hi-Lo rows for each independently completed round.
            hi_lo_events_a=[row for row in hi_lo_ledger_a if row.get('game')=='hi_lo' and row.get('round_id')==hi_lo_a['round']['round_id']]; hi_lo_events_b=[row for row in hi_lo_ledger_b if row.get('game')=='hi_lo' and row.get('round_id')==hi_lo_b['round']['round_id']]
            # Require one wager debit, at most one returned-token credit, and unique stable action ids per user.
            assert sum(row.get('transaction_type')=='HI_LO_WAGER_DEBIT' for row in hi_lo_events_a)==1 and sum(row.get('transaction_type')=='HI_LO_WAGER_DEBIT' for row in hi_lo_events_b)==1 and sum(row.get('transaction_type') in ('HI_LO_REFUND_CREDIT','HI_LO_PAYOUT_CREDIT') for row in hi_lo_events_a)<=1 and sum(row.get('transaction_type') in ('HI_LO_REFUND_CREDIT','HI_LO_PAYOUT_CREDIT') for row in hi_lo_events_b)<=1 and len({(row.get('details') or {}).get('hi_lo_action_id') for row in hi_lo_events_a})==len(hi_lo_events_a) and len({(row.get('details') or {}).get('hi_lo_action_id') for row in hi_lo_events_b})==len(hi_lo_events_b)
            # Deal independent Three Card Poker rounds while hostile body identities challenge session binding.
            tcp_a=api(base,'/api/v1/games/three-card-poker/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-tcp-deal-a','ante':2,'pair_plus':1},auth_token=token_a); tcp_b=api(base,'/api/v1/games/three-card-poker/rounds','POST',{'player_id':user_a['player_id'],'request_id':'wallet-tcp-deal-b','ante':2,'pair_plus':1},auth_token=token_b)
            # Replay one opening and reject an altered wager under the immutable request fingerprint.
            tcp_a_replay=api(base,'/api/v1/games/three-card-poker/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-tcp-deal-a','ante':2,'pair_plus':1},auth_token=token_a); tcp_conflict=api(base,'/api/v1/games/three-card-poker/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-tcp-deal-a','ante':3,'pair_plus':1},ok=False,auth_token=token_a)
            # Require bound ownership, independent rounds, exact replay, closed conflict, and protected dealer cards.
            assert tcp_a['round']['player_id']==user_a['player_id'] and tcp_b['round']['player_id']==user_b['player_id'] and tcp_a['round']['round_id']!=tcp_b['round']['round_id'] and tcp_a_replay['replayed'] is True and tcp_conflict['error']['code']=='CONFLICT' and tcp_a['round']['dealer_hand']==['??','??','??'] and tcp_b['round']['dealer_hand']==['??','??','??']
            # Settle both rounds through opposite public decisions and replay Play exactly once.
            tcp_a_done=api(base,f'/api/v1/games/three-card-poker/rounds/{tcp_a["round"]["round_id"]}/decisions','POST',{'player_id':user_b['player_id'],'action_id':'wallet-tcp-play-a','decision':'play'},auth_token=token_a); tcp_a_done_replay=api(base,f'/api/v1/games/three-card-poker/rounds/{tcp_a["round"]["round_id"]}/decisions','POST',{'player_id':user_b['player_id'],'action_id':'wallet-tcp-play-a','decision':'play'},auth_token=token_a); tcp_b_done=api(base,f'/api/v1/games/three-card-poker/rounds/{tcp_b["round"]["round_id"]}/decisions','POST',{'player_id':user_a['player_id'],'action_id':'wallet-tcp-fold-b','decision':'fold'},auth_token=token_b)
            # Require terminal revealed hands and stable decision replay for both sessions.
            assert tcp_a_done['round']['phase']=='settled' and tcp_b_done['round']['phase']=='settled' and '??' not in tcp_a_done['round']['dealer_hand'] and '??' not in tcp_b_done['round']['dealer_hand'] and tcp_a_done_replay['replayed'] is True and tcp_a_done_replay['round']==tcp_a_done['round']
            # Require one opening debit, at most one Play debit, and at most one payout credit for the played round.
            tcp_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; tcp_events_a=[row for row in tcp_ledger_a if row.get('game')=='three_card_poker' and row.get('round_id')==tcp_a['round']['round_id']]; assert sum(row.get('transaction_type')=='THREE_CARD_POKER_INITIAL_DEBIT' for row in tcp_events_a)==1 and sum(row.get('transaction_type')=='THREE_CARD_POKER_PLAY_DEBIT' for row in tcp_events_a)<=1 and sum(row.get('transaction_type')=='THREE_CARD_POKER_PAYOUT_CREDIT' for row in tcp_events_a)<=1
            # Deal two session-bound Jacks or Better hands while submitting hostile player identities.
            jobvp_a=api(base,'/api/v1/games/jacks-or-better-video-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-jobvp-deal-a','coins':1,'coin_value':1},auth_token=token_a); jobvp_b=api(base,'/api/v1/games/jacks-or-better-video-poker/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-jobvp-deal-b','coins':1,'coin_value':1},auth_token=token_b)
            # Replay the first deal and reject altered coin settings under the same action identity.
            jobvp_a_replay=api(base,'/api/v1/games/jacks-or-better-video-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-jobvp-deal-a','coins':1,'coin_value':1},auth_token=token_a); jobvp_conflict=api(base,'/api/v1/games/jacks-or-better-video-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-jobvp-deal-a','coins':2,'coin_value':1},ok=False,auth_token=token_a)
            # Require authenticated ownership, independent hands, exact replay, and conflict closure.
            assert jobvp_a['round']['player_id']==user_a['player_id'] and jobvp_b['round']['player_id']==user_b['player_id'] and jobvp_a['round']['round_id']!=jobvp_b['round']['round_id'] and jobvp_a_replay['replayed'] is True and jobvp_conflict['error']['code']=='CONFLICT'
            # Persist different public hold selections for both authenticated sessions.
            api(base,f'/api/v1/games/jacks-or-better-video-poker/rounds/{jobvp_a["round"]["round_id"]}/holds','POST',{'player_id':user_b['player_id'],'holds':[0]},auth_token=token_a); api(base,f'/api/v1/games/jacks-or-better-video-poker/rounds/{jobvp_b["round"]["round_id"]}/holds','POST',{'player_id':user_a['player_id'],'holds':[1]},auth_token=token_b)
            # Draw both final hands and replay user A's settlement exactly once.
            jobvp_a_done=api(base,f'/api/v1/games/jacks-or-better-video-poker/rounds/{jobvp_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id'],'action_id':'wallet-jobvp-draw-a'},auth_token=token_a); jobvp_a_done_replay=api(base,f'/api/v1/games/jacks-or-better-video-poker/rounds/{jobvp_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id'],'action_id':'wallet-jobvp-draw-a'},auth_token=token_a); jobvp_b_done=api(base,f'/api/v1/games/jacks-or-better-video-poker/rounds/{jobvp_b["round"]["round_id"]}/draw','POST',{'player_id':user_a['player_id'],'action_id':'wallet-jobvp-draw-b'},auth_token=token_b)
            # Require terminal five-card hands and stable replay without duplicate settlement.
            assert jobvp_a_done['round']['phase']=='settled' and jobvp_b_done['round']['phase']=='settled' and len(jobvp_a_done['round']['final_hand'])==5 and len(jobvp_b_done['round']['final_hand'])==5 and jobvp_a_done_replay['replayed'] is True and jobvp_a_done_replay['round']==jobvp_a_done['round']
            # Verify the played round contains one wager debit and at most one returned-credit event.
            jobvp_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; jobvp_events_a=[row for row in jobvp_ledger_a if row.get('game')=='jacks_or_better_video_poker' and row.get('round_id')==jobvp_a['round']['round_id']]; assert sum(row.get('transaction_type')=='JOBVP_WAGER_DEBIT' for row in jobvp_events_a)==1 and sum(row.get('transaction_type')=='JOBVP_PAYOUT_CREDIT' for row in jobvp_events_a)<=1
            # Deal independent Deuces Wild hands while hostile body identities challenge session binding.
            dwvp_a=api(base,'/api/v1/games/deuces-wild-video-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-dwvp-deal-a','wager':1},auth_token=token_a); dwvp_b=api(base,'/api/v1/games/deuces-wild-video-poker/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-dwvp-deal-b','wager':1},auth_token=token_b)
            # Replay one exact deal and reject an altered wager under the immutable action fingerprint.
            dwvp_a_replay=api(base,'/api/v1/games/deuces-wild-video-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-dwvp-deal-a','wager':1},auth_token=token_a); dwvp_conflict=api(base,'/api/v1/games/deuces-wild-video-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-dwvp-deal-a','wager':2},ok=False,auth_token=token_a)
            # Require bound ownership, independent rounds, exact replay, and closed conflict behavior.
            assert dwvp_a['round']['player_id']==user_a['player_id'] and dwvp_b['round']['player_id']==user_b['player_id'] and dwvp_a['round']['round_id']!=dwvp_b['round']['round_id'] and dwvp_a_replay['replayed'] is True and dwvp_conflict['error']['code']=='CONFLICT'
            # Persist separate hold actions and complete both public draws.
            api(base,f'/api/v1/games/deuces-wild-video-poker/rounds/{dwvp_a["round"]["round_id"]}/holds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-dwvp-holds-a','holds':[0]},auth_token=token_a); api(base,f'/api/v1/games/deuces-wild-video-poker/rounds/{dwvp_b["round"]["round_id"]}/holds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-dwvp-holds-b','holds':[]},auth_token=token_b); dwvp_a_done=api(base,f'/api/v1/games/deuces-wild-video-poker/rounds/{dwvp_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id'],'action_id':'wallet-dwvp-draw-a'},auth_token=token_a); dwvp_a_done_replay=api(base,f'/api/v1/games/deuces-wild-video-poker/rounds/{dwvp_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id'],'action_id':'wallet-dwvp-draw-a'},auth_token=token_a); dwvp_b_done=api(base,f'/api/v1/games/deuces-wild-video-poker/rounds/{dwvp_b["round"]["round_id"]}/draw','POST',{'player_id':user_a['player_id'],'action_id':'wallet-dwvp-draw-b'},auth_token=token_b)
            # Require terminal five-card hands and stable settlement replay.
            assert dwvp_a_done['round']['phase']=='settled' and dwvp_b_done['round']['phase']=='settled' and len(dwvp_a_done['round']['final_hand'])==5 and len(dwvp_b_done['round']['final_hand'])==5 and dwvp_a_done_replay['replayed'] is True and dwvp_a_done_replay['round']==dwvp_a_done['round']
            # Require one wager debit and at most one payout credit for the replayed round.
            dwvp_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; dwvp_events_a=[row for row in dwvp_ledger_a if row.get('game')=='deuces_wild_video_poker' and row.get('round_id')==dwvp_a['round']['round_id']]; assert sum(row.get('transaction_type')=='DWVP_WAGER_DEBIT' for row in dwvp_events_a)==1 and sum(row.get('transaction_type')=='DWVP_PAYOUT_CREDIT' for row in dwvp_events_a)<=1
            # Start two private Scratch Cards while hostile body identities challenge session binding.
            scratch_a=api(base,'/api/v1/games/scratch-cards/cards','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-scratch-start-a','wager':1},auth_token=token_a); scratch_b=api(base,'/api/v1/games/scratch-cards/cards','POST',{'player_id':user_a['player_id'],'client_request_id':'wallet-scratch-start-b','wager':1},auth_token=token_b)
            # Replay one purchase and reject changed wager meaning under its stable identity.
            scratch_a_replay=api(base,'/api/v1/games/scratch-cards/cards','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-scratch-start-a','wager':1},auth_token=token_a); scratch_conflict=api(base,'/api/v1/games/scratch-cards/cards','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-scratch-start-a','wager':2},ok=False,auth_token=token_a)
            # Require independent masked cards, exact replay, and fail-closed conflict behavior.
            assert scratch_a['card']['card_id']!=scratch_b['card']['card_id'] and scratch_a_replay['replayed'] is True and scratch_conflict['error']['code']=='CONFLICT' and all('prize' not in cell for cell in scratch_a['card']['cells']) and all('prize' not in cell for cell in scratch_b['card']['cells'])
            # Reveal one partial cell for user A and complete user B's independent card.
            scratch_a_partial=api(base,f'/api/v1/games/scratch-cards/cards/{scratch_a["card"]["card_id"]}/scratches','POST',{'player_id':user_b['player_id'],'action_id':'wallet-scratch-partial-a','positions':[0]},auth_token=token_a); scratch_b_done=api(base,f'/api/v1/games/scratch-cards/cards/{scratch_b["card"]["card_id"]}/scratches','POST',{'player_id':user_a['player_id'],'action_id':'wallet-scratch-reveal-b','positions':list(range(9))},auth_token=token_b)
            # Complete and replay user A's reveal through the public API.
            scratch_a_done=api(base,f'/api/v1/games/scratch-cards/cards/{scratch_a["card"]["card_id"]}/scratches','POST',{'player_id':user_b['player_id'],'action_id':'wallet-scratch-reveal-a','positions':list(range(1,9))},auth_token=token_a); scratch_a_done_replay=api(base,f'/api/v1/games/scratch-cards/cards/{scratch_a["card"]["card_id"]}/scratches','POST',{'player_id':user_b['player_id'],'action_id':'wallet-scratch-reveal-a','positions':list(range(1,9))},auth_token=token_a)
            # Require partial persistence, terminal disclosure, and stable replay for both users.
            assert scratch_a_partial['card']['revealed_count']==1 and scratch_a_done['card']['status']=='settled' and scratch_b_done['card']['status']=='settled' and scratch_a_done_replay['replayed'] is True and sum('prize' in cell for cell in scratch_a_done['card']['cells'])==9
            # Require exactly one wager debit and at most one positive payout credit per card.
            scratch_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; scratch_events_a=[row for row in scratch_ledger_a if row.get('game')=='scratch_cards' and row.get('round_id')==scratch_a['card']['card_id']]; assert sum(row.get('transaction_type')=='SCRATCH_CARD_WAGER_DEBIT' for row in scratch_events_a)==1 and sum(row.get('transaction_type')=='SCRATCH_CARD_PAYOUT_CREDIT' for row in scratch_events_a)<=1
            # Settle two session-bound Sic Bo rounds while hostile body identities challenge ownership.
            sic_a=api(base,'/api/v1/games/sic-bo/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-sic-bo-a','wagers':{'small':1}},auth_token=token_a); sic_b=api(base,'/api/v1/games/sic-bo/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-sic-bo-b','wagers':{'big':1}},auth_token=token_b)
            # Replay one exact round and reject changed wager meaning under the same action identity.
            sic_a_replay=api(base,'/api/v1/games/sic-bo/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-sic-bo-a','wagers':{'small':1}},auth_token=token_a); sic_conflict=api(base,'/api/v1/games/sic-bo/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-sic-bo-a','wagers':{'small':2}},ok=False,auth_token=token_a)
            # Require bound ownership, independent authoritative dice, exact replay, and conflict closure.
            assert sic_a['round']['player_id']==user_a['player_id'] and sic_b['round']['player_id']==user_b['player_id'] and sic_a['round']['round_id']!=sic_b['round']['round_id'] and len(sic_a['round']['dice'])==3 and sic_a_replay['replayed'] is True and sic_a_replay['round']['dice']==sic_a['round']['dice'] and sic_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            sic_state_a=api(base,f'/api/v1/games/sic-bo/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; sic_state_b=api(base,f'/api/v1/games/sic-bo/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']; assert sic_state_a['recent_rounds'][-1]['round_id']==sic_a['round']['round_id'] and sic_state_b['recent_rounds'][-1]['round_id']==sic_b['round']['round_id']
            # Require one aggregate wager debit and at most one returned-credit event for the replayed round.
            sic_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; sic_events_a=[row for row in sic_ledger_a if row.get('game')=='sic_bo' and row.get('round_id')==sic_a['round']['round_id']]; assert sum(row.get('transaction_type')=='SIC_BO_WAGER_DEBIT' for row in sic_events_a)==1 and sum(row.get('transaction_type')=='SIC_BO_PAYOUT_CREDIT' for row in sic_events_a)<=1
            # Settle two session-bound Chuck-a-Luck rolls while hostile body identities challenge ownership.
            chuck_a=api(base,'/api/v1/games/chuck-a-luck/rolls','POST',{'player_id':user_b['player_id'],'request_id':'wallet-chuck-a','wagers':{'one':1}},auth_token=token_a); chuck_b=api(base,'/api/v1/games/chuck-a-luck/rolls','POST',{'player_id':user_a['player_id'],'request_id':'wallet-chuck-b','wagers':{'six':1}},auth_token=token_b)
            # Replay one exact roll and reject changed wager meaning under the same request identity.
            chuck_a_replay=api(base,'/api/v1/games/chuck-a-luck/rolls','POST',{'player_id':user_b['player_id'],'request_id':'wallet-chuck-a','wagers':{'one':1}},auth_token=token_a); chuck_conflict=api(base,'/api/v1/games/chuck-a-luck/rolls','POST',{'player_id':user_b['player_id'],'request_id':'wallet-chuck-a','wagers':{'one':2}},ok=False,auth_token=token_a)
            # Require bound ownership, independent authoritative dice, exact replay, and conflict closure.
            assert chuck_a['round']['player_id']==user_a['player_id'] and chuck_b['round']['player_id']==user_b['player_id'] and chuck_a['round']['round_id']!=chuck_b['round']['round_id'] and len(chuck_a['round']['dice'])==3 and chuck_a_replay['replayed'] is True and chuck_a_replay['round']['dice']==chuck_a['round']['dice'] and chuck_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            chuck_state_a=api(base,f'/api/v1/games/chuck-a-luck/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; chuck_state_b=api(base,f'/api/v1/games/chuck-a-luck/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']; assert chuck_state_a['recent_rounds'][-1]['round_id']==chuck_a['round']['round_id'] and chuck_state_b['recent_rounds'][-1]['round_id']==chuck_b['round']['round_id']
            # Require one aggregate wager debit and at most one returned-credit event for the replayed roll.
            chuck_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; chuck_events_a=[row for row in chuck_ledger_a if row.get('game')=='chuck_a_luck' and row.get('round_id')==chuck_a['round']['round_id']]; assert sum(row.get('transaction_type')=='CHUCK_A_LUCK_WAGER_DEBIT' for row in chuck_events_a)==1 and sum(row.get('transaction_type')=='CHUCK_A_LUCK_SETTLEMENT_CREDIT' for row in chuck_events_a)<=1
            # Start two session-bound Craps rounds while hostile body identities challenge ownership.
            craps_a=api(base,'/api/v1/games/craps/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-craps-a','bet_type':'pass_line','wager':1},auth_token=token_a); craps_b=api(base,'/api/v1/games/craps/rounds','POST',{'player_id':user_a['player_id'],'request_id':'wallet-craps-b','bet_type':'dont_pass','wager':1},auth_token=token_b)
            # Replay one exact start and reject changed money meaning under the same request identity.
            craps_a_replay=api(base,'/api/v1/games/craps/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-craps-a','bet_type':'pass_line','wager':1},auth_token=token_a); craps_conflict=api(base,'/api/v1/games/craps/rounds','POST',{'player_id':user_b['player_id'],'request_id':'wallet-craps-a','bet_type':'dont_pass','wager':1},ok=False,auth_token=token_a)
            # Require bound ownership, independent round ids, exact replay, and conflict closure.
            assert craps_a['round']['player_id']==user_a['player_id'] and craps_b['round']['player_id']==user_b['player_id'] and craps_a['round']['round_id']!=craps_b['round']['round_id'] and craps_a_replay['replayed'] is True and craps_a_replay['round']['round_id']==craps_a['round']['round_id'] and craps_conflict['error']['code']=='CONFLICT'
            # Read both private active states with hostile query identities and require isolated rounds.
            craps_state_a=api(base,f'/api/v1/games/craps/state?player_id={user_b["player_id"]}',auth_token=token_a)['state']; craps_state_b=api(base,f'/api/v1/games/craps/state?player_id={user_a["player_id"]}',auth_token=token_b)['state']; assert craps_state_a['active_round']['round_id']==craps_a['round']['round_id'] and craps_state_b['active_round']['round_id']==craps_b['round']['round_id']
            # Settle one Craps round through bounded public server-authoritative roll actions.
            def settle_craps(token,round_id,prefix):
                # Retain the terminal action body for exact archived-action replay.
                terminal_body=None
                # Bound a random point sequence while keeping an impossible overrun visible.
                for roll_index in range(200):
                    # Give every roll a stable action identity.
                    body={'request_id':f'{prefix}-{roll_index}'}
                    # Advance through only the public authenticated action.
                    result=api(base,f'/api/v1/games/craps/rounds/{round_id}/rolls','POST',body,auth_token=token)
                    # Stop after the backend commits a terminal result.
                    if result['round']['phase']=='settled': terminal_body=body; return result,terminal_body
                # Fail clearly if an unexpectedly long point sequence exceeds the guard.
                raise AssertionError('Craps round did not settle within 200 rolls')
            # Settle both users independently and replay user A's terminal action exactly.
            craps_a_done,craps_a_terminal=settle_craps(token_a,craps_a['round']['round_id'],'wallet-craps-a-roll'); craps_b_done,_=settle_craps(token_b,craps_b['round']['round_id'],'wallet-craps-b-roll'); craps_a_terminal_replay=api(base,f'/api/v1/games/craps/rounds/{craps_a["round"]["round_id"]}/rolls','POST',craps_a_terminal,auth_token=token_a)
            # Require exact terminal dice/replay behavior and settled two-user isolation.
            assert craps_a_done['round']['phase']=='settled' and craps_b_done['round']['phase']=='settled' and len(craps_a_done['roll']['dice'])==2 and craps_a_terminal_replay['replayed'] is True and craps_a_terminal_replay['roll']==craps_a_done['roll']
            # Require one wager debit and at most one payout or push refund for the replayed round.
            craps_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; craps_events_a=[row for row in craps_ledger_a if row.get('game')=='craps' and row.get('round_id')==craps_a['round']['round_id']]; assert sum(row.get('transaction_type')=='CRAPS_WAGER_DEBIT' for row in craps_events_a)==1 and sum(row.get('transaction_type') in ('CRAPS_PAYOUT_CREDIT','CRAPS_PUSH_REFUND') for row in craps_events_a)<=1
            # Settle two session-bound Crown and Anchor rounds while hostile body identities challenge ownership.
            crown_a=api(base,'/api/v1/games/crown-and-anchor/rounds','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-crown-a','wagers':{'crown':1}},auth_token=token_a); crown_b=api(base,'/api/v1/games/crown-and-anchor/rounds','POST',{'player_id':user_a['player_id'],'client_request_id':'wallet-crown-b','wagers':{'anchor':1}},auth_token=token_b)
            # Replay one exact round and reject changed wager meaning under the same request identity.
            crown_a_replay=api(base,'/api/v1/games/crown-and-anchor/rounds','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-crown-a','wagers':{'crown':1}},auth_token=token_a); crown_conflict=api(base,'/api/v1/games/crown-and-anchor/rounds','POST',{'player_id':user_b['player_id'],'client_request_id':'wallet-crown-a','wagers':{'crown':2}},ok=False,auth_token=token_a)
            # Require bound ownership, independent authoritative dice, exact replay, and conflict closure.
            assert crown_a['round']['player_id']==user_a['player_id'] and crown_b['round']['player_id']==user_b['player_id'] and crown_a['round']['round_id']!=crown_b['round']['round_id'] and len(crown_a['round']['faces'])==3 and crown_a_replay['replayed'] is True and crown_a_replay['round']['faces']==crown_a['round']['faces'] and crown_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            crown_state_a=api(base,f'/api/v1/games/crown-and-anchor/state?player_id={user_b["player_id"]}',auth_token=token_a); crown_state_b=api(base,f'/api/v1/games/crown-and-anchor/state?player_id={user_a["player_id"]}',auth_token=token_b); assert crown_state_a['recent_rounds'][-1]['round_id']==crown_a['round']['round_id'] and crown_state_b['recent_rounds'][-1]['round_id']==crown_b['round']['round_id']
            # Require one aggregate wager debit and at most one returned-credit event for the replayed round.
            crown_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; crown_events_a=[row for row in crown_ledger_a if row.get('game')=='crown_and_anchor' and row.get('round_id')==crown_a['round']['round_id']]; assert sum(row.get('transaction_type')=='CROWN_AND_ANCHOR_WAGER_DEBIT' for row in crown_events_a)==1 and sum(row.get('transaction_type')=='CROWN_AND_ANCHOR_SETTLEMENT_CREDIT' for row in crown_events_a)<=1
            # Settle two session-bound Over/Under 7 plays while hostile body identities challenge ownership.
            ou7_a=api(base,'/api/v1/games/over-under-7/plays','POST',{'player_id':user_b['player_id'],'action_id':'wallet-ou7-a','wagers':{'under':1}},auth_token=token_a); ou7_b=api(base,'/api/v1/games/over-under-7/plays','POST',{'player_id':user_a['player_id'],'action_id':'wallet-ou7-b','wagers':{'over':1}},auth_token=token_b)
            # Replay one exact play and reject changed wager meaning under the same action identity.
            ou7_a_replay=api(base,'/api/v1/games/over-under-7/plays','POST',{'player_id':user_b['player_id'],'action_id':'wallet-ou7-a','wagers':{'under':1}},auth_token=token_a); ou7_conflict=api(base,'/api/v1/games/over-under-7/plays','POST',{'player_id':user_b['player_id'],'action_id':'wallet-ou7-a','wagers':{'seven':1}},ok=False,auth_token=token_a)
            # Require bound ownership, independent authoritative dice, exact replay, and conflict closure.
            assert ou7_a['round']['player_id']==user_a['player_id'] and ou7_b['round']['player_id']==user_b['player_id'] and ou7_a['round']['round_id']!=ou7_b['round']['round_id'] and len(ou7_a['round']['dice'])==2 and ou7_a_replay['replayed'] is True and ou7_a_replay['round']['dice']==ou7_a['round']['dice'] and ou7_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            ou7_state_a=api(base,f'/api/v1/games/over-under-7/state?player_id={user_b["player_id"]}',auth_token=token_a); ou7_state_b=api(base,f'/api/v1/games/over-under-7/state?player_id={user_a["player_id"]}',auth_token=token_b); assert ou7_state_a['state']['recent_rounds'][-1]['round_id']==ou7_a['round']['round_id'] and ou7_state_b['state']['recent_rounds'][-1]['round_id']==ou7_b['round']['round_id']
            # Require one aggregate wager debit and at most one returned-credit event for the replayed play.
            ou7_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; ou7_events_a=[row for row in ou7_ledger_a if row.get('game')=='over_under_7' and row.get('round_id')==ou7_a['round']['round_id']]; assert sum(row.get('transaction_type')=='OVER_UNDER_7_WAGER_DEBIT' for row in ou7_events_a)==1 and sum(row.get('transaction_type')=='OVER_UNDER_7_SETTLEMENT_CREDIT' for row in ou7_events_a)<=1
            # Settle two session-bound Plinko drops while hostile body identities challenge ownership.
            plinko_a=api(base,'/api/v1/games/plinko/drops','POST',{'player_id':user_b['player_id'],'action_id':'wallet-plinko-a','wager':2},auth_token=token_a); plinko_b=api(base,'/api/v1/games/plinko/drops','POST',{'player_id':user_a['player_id'],'action_id':'wallet-plinko-b','wager':3},auth_token=token_b)
            # Replay one exact drop and reject changed wager meaning under the same action identity.
            plinko_a_replay=api(base,'/api/v1/games/plinko/drops','POST',{'player_id':user_b['player_id'],'action_id':'wallet-plinko-a','wager':2},auth_token=token_a); plinko_conflict=api(base,'/api/v1/games/plinko/drops','POST',{'player_id':user_b['player_id'],'action_id':'wallet-plinko-a','wager':4},ok=False,auth_token=token_a)
            # Require bound ownership, independent committed paths, exact replay, and conflict closure.
            assert plinko_a['drop']['player_id']==user_a['player_id'] and plinko_b['drop']['player_id']==user_b['player_id'] and plinko_a['drop']['drop_id']!=plinko_b['drop']['drop_id'] and len(plinko_a['drop']['path'])==8 and plinko_a_replay['replayed'] is True and plinko_a_replay['drop']['path']==plinko_a['drop']['path'] and plinko_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            plinko_state_a=api(base,f'/api/v1/games/plinko/state?player_id={user_b["player_id"]}',auth_token=token_a); plinko_state_b=api(base,f'/api/v1/games/plinko/state?player_id={user_a["player_id"]}',auth_token=token_b); assert plinko_state_a['state']['recent_drops'][-1]['drop_id']==plinko_a['drop']['drop_id'] and plinko_state_b['state']['recent_drops'][-1]['drop_id']==plinko_b['drop']['drop_id']
            # Require exactly one wager debit and one returned-token credit for the replayed drop.
            plinko_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; plinko_events_a=[row for row in plinko_ledger_a if row.get('game')=='plinko' and row.get('round_id')==plinko_a['drop']['drop_id']]; assert sum(row.get('transaction_type')=='PLINKO_WAGER_DEBIT' for row in plinko_events_a)==1 and sum(row.get('transaction_type')=='PLINKO_PAYOUT_CREDIT' for row in plinko_events_a)==1
            # Settle two session-bound Fan-Tan rounds while hostile body identities challenge ownership.
            fan_tan_a=api(base,'/api/v1/games/fan-tan/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-fan-tan-a','wagers':{'1':1}},auth_token=token_a); fan_tan_b=api(base,'/api/v1/games/fan-tan/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-fan-tan-b','wagers':{'4':1}},auth_token=token_b)
            # Replay one exact round and reject changed wager meaning under the same action identity.
            fan_tan_a_replay=api(base,'/api/v1/games/fan-tan/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-fan-tan-a','wagers':{'1':1}},auth_token=token_a); fan_tan_conflict=api(base,'/api/v1/games/fan-tan/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-fan-tan-a','wagers':{'2':1}},ok=False,auth_token=token_a)
            # Require bound ownership, independent authoritative counts, exact replay, and conflict closure.
            assert fan_tan_a['round']['player_id']==user_a['player_id'] and fan_tan_b['round']['player_id']==user_b['player_id'] and fan_tan_a['round']['round_id']!=fan_tan_b['round']['round_id'] and 49<=fan_tan_a['round']['pile_count']<=80 and fan_tan_a_replay['replayed'] is True and fan_tan_a_replay['round']['pile_count']==fan_tan_a['round']['pile_count'] and fan_tan_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            fan_tan_state_a=api(base,f'/api/v1/games/fan-tan/state?player_id={user_b["player_id"]}',auth_token=token_a); fan_tan_state_b=api(base,f'/api/v1/games/fan-tan/state?player_id={user_a["player_id"]}',auth_token=token_b); assert fan_tan_state_a['state']['recent_rounds'][-1]['round_id']==fan_tan_a['round']['round_id'] and fan_tan_state_b['state']['recent_rounds'][-1]['round_id']==fan_tan_b['round']['round_id']
            # Require one aggregate wager debit and at most one returned-token credit for the replayed round.
            fan_tan_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; fan_tan_events_a=[row for row in fan_tan_ledger_a if row.get('game')=='fan_tan' and row.get('round_id')==fan_tan_a['round']['round_id']]; assert sum(row.get('transaction_type')=='FAN_TAN_WAGER_DEBIT' for row in fan_tan_events_a)==1 and sum(row.get('transaction_type')=='FAN_TAN_SETTLEMENT_CREDIT' for row in fan_tan_events_a)<=1
            # Settle two session-bound Andar Bahar rounds while hostile body identities challenge ownership.
            andar_bahar_a=api(base,'/api/v1/games/andar-bahar/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-andar-bahar-a','wager':1,'side':'andar'},auth_token=token_a); andar_bahar_b=api(base,'/api/v1/games/andar-bahar/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-andar-bahar-b','wager':1,'side':'bahar'},auth_token=token_b)
            # Replay one exact round and reject changed side meaning under the same action identity.
            andar_bahar_a_replay=api(base,'/api/v1/games/andar-bahar/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-andar-bahar-a','wager':1,'side':'andar'},auth_token=token_a); andar_bahar_conflict=api(base,'/api/v1/games/andar-bahar/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-andar-bahar-a','wager':1,'side':'bahar'},ok=False,auth_token=token_a)
            # Require bound ownership, independent authoritative deals, exact replay, and conflict closure.
            assert andar_bahar_a['round']['player_id']==user_a['player_id'] and andar_bahar_b['round']['player_id']==user_b['player_id'] and andar_bahar_a['round']['round_id']!=andar_bahar_b['round']['round_id'] and andar_bahar_a['round']['dealt_cards'][-1]['matched'] is True and andar_bahar_a_replay['replayed'] is True and andar_bahar_a_replay['round']['dealt_cards']==andar_bahar_a['round']['dealt_cards'] and andar_bahar_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            andar_bahar_state_a=api(base,f'/api/v1/games/andar-bahar/state?player_id={user_b["player_id"]}',auth_token=token_a); andar_bahar_state_b=api(base,f'/api/v1/games/andar-bahar/state?player_id={user_a["player_id"]}',auth_token=token_b); assert andar_bahar_state_a['state']['recent_rounds'][-1]['round_id']==andar_bahar_a['round']['round_id'] and andar_bahar_state_b['state']['recent_rounds'][-1]['round_id']==andar_bahar_b['round']['round_id']
            # Require exactly one wager debit and at most one returned-token credit for the replayed round.
            andar_bahar_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; andar_bahar_events_a=[row for row in andar_bahar_ledger_a if row.get('game')=='andar_bahar' and row.get('round_id')==andar_bahar_a['round']['round_id']]; assert sum(row.get('transaction_type')=='ANDAR_BAHAR_WAGER_DEBIT' for row in andar_bahar_events_a)==1 and sum(row.get('transaction_type')=='ANDAR_BAHAR_PAYOUT_CREDIT' for row in andar_bahar_events_a)<=1
            # Prepare one priceable session-owned Acey-Deucey round without assuming random boundaries permit Play.
            def priceable_acey_deucey_deal(token,hostile_player,prefix):
                # Bound free retries so a broken deal or pricing path cannot loop forever.
                for attempt in range(12):
                    # Deal through the authenticated session while retaining the hostile compatibility identity.
                    dealt=api(base,'/api/v1/games/acey-deucey/rounds','POST',{'player_id':hostile_player,'action_id':f'{prefix}-deal-{attempt}'},auth_token=token)
                    # Return the prepared round as soon as at least one strict inside rank has a price.
                    if dealt['round']['inside_rank_count']>0: return dealt
                    # Pass equal or adjacent boundaries without wallet movement before dealing again.
                    passed=api(base,f'/api/v1/games/acey-deucey/rounds/{dealt["round"]["round_id"]}/pass','POST',{'player_id':hostile_player,'action_id':f'{prefix}-pass-{attempt}'},auth_token=token)
                    # Require the pass-only branch to close without revealing the third card.
                    assert passed['round']['phase']=='passed' and not passed['round'].get('third_card')
                # Fail closed when the bounded real-deal sequence never exposes a legal wager.
                raise AssertionError('Acey-Deucey did not deal a priceable spread in 12 attempts')
            # Prepare two session-bound priceable rounds while hostile body identities challenge ownership.
            acey_deucey_deal_a=priceable_acey_deucey_deal(token_a,user_b['player_id'],'wallet-acey-deucey-a'); acey_deucey_deal_b=priceable_acey_deucey_deal(token_b,user_a['player_id'],'wallet-acey-deucey-b')
            # Settle each private prepared round through an independent wagered action.
            acey_deucey_a=api(base,f'/api/v1/games/acey-deucey/rounds/{acey_deucey_deal_a["round"]["round_id"]}/play','POST',{'player_id':user_b['player_id'],'action_id':'wallet-acey-deucey-play-a','wager':1},auth_token=token_a); acey_deucey_b=api(base,f'/api/v1/games/acey-deucey/rounds/{acey_deucey_deal_b["round"]["round_id"]}/play','POST',{'player_id':user_a['player_id'],'action_id':'wallet-acey-deucey-play-b','wager':1},auth_token=token_b)
            # Replay one exact play and reject changed wager meaning under the same action identity.
            acey_deucey_a_replay=api(base,f'/api/v1/games/acey-deucey/rounds/{acey_deucey_deal_a["round"]["round_id"]}/play','POST',{'player_id':user_b['player_id'],'action_id':'wallet-acey-deucey-play-a','wager':1},auth_token=token_a); acey_deucey_conflict=api(base,f'/api/v1/games/acey-deucey/rounds/{acey_deucey_deal_a["round"]["round_id"]}/play','POST',{'player_id':user_b['player_id'],'action_id':'wallet-acey-deucey-play-a','wager':2},ok=False,auth_token=token_a)
            # Require hidden prepared results, bound ownership, independent rounds, exact replay, and conflict closure.
            assert not acey_deucey_deal_a['round'].get('third_card') and acey_deucey_a['round']['player_id']==user_a['player_id'] and acey_deucey_b['round']['player_id']==user_b['player_id'] and acey_deucey_a['round']['round_id']!=acey_deucey_b['round']['round_id'] and acey_deucey_a_replay['replayed'] is True and acey_deucey_a_replay['round']['third_card']==acey_deucey_a['round']['third_card'] and acey_deucey_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            acey_deucey_state_a=api(base,f'/api/v1/games/acey-deucey/state?player_id={user_b["player_id"]}',auth_token=token_a); acey_deucey_state_b=api(base,f'/api/v1/games/acey-deucey/state?player_id={user_a["player_id"]}',auth_token=token_b); assert acey_deucey_state_a['state']['recent_rounds'][-1]['round_id']==acey_deucey_a['round']['round_id'] and acey_deucey_state_b['state']['recent_rounds'][-1]['round_id']==acey_deucey_b['round']['round_id']
            # Require exactly one wager debit and at most one returned-token credit for the replayed round.
            acey_deucey_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; acey_deucey_events_a=[row for row in acey_deucey_ledger_a if row.get('game')=='acey_deucey' and row.get('round_id')==acey_deucey_a['round']['round_id']]; assert sum(row.get('transaction_type')=='ACEY_DEUCEY_WAGER_DEBIT' for row in acey_deucey_events_a)==1 and sum(row.get('transaction_type')=='ACEY_DEUCEY_PAYOUT_CREDIT' for row in acey_deucey_events_a)<=1
            # Prepare two session-bound Caribbean Stud decisions while hostile body identities challenge ownership.
            caribbean_deal_a=api(base,'/api/v1/games/caribbean-stud/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-caribbean-deal-a','ante':1},auth_token=token_a); caribbean_deal_b=api(base,'/api/v1/games/caribbean-stud/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-caribbean-deal-b','ante':1},auth_token=token_b)
            # Settle each private prepared round through an independent fixed call wager.
            caribbean_a=api(base,f'/api/v1/games/caribbean-stud/rounds/{caribbean_deal_a["round"]["round_id"]}/call','POST',{'player_id':user_b['player_id'],'action_id':'wallet-caribbean-call-a'},auth_token=token_a); caribbean_b=api(base,f'/api/v1/games/caribbean-stud/rounds/{caribbean_deal_b["round"]["round_id"]}/call','POST',{'player_id':user_a['player_id'],'action_id':'wallet-caribbean-call-b'},auth_token=token_b)
            # Replay one exact call and reject changed ante meaning under the original deal action identity.
            caribbean_a_replay=api(base,f'/api/v1/games/caribbean-stud/rounds/{caribbean_deal_a["round"]["round_id"]}/call','POST',{'player_id':user_b['player_id'],'action_id':'wallet-caribbean-call-a'},auth_token=token_a); caribbean_conflict=api(base,'/api/v1/games/caribbean-stud/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-caribbean-deal-a','ante':2},ok=False,auth_token=token_a)
            # Require hidden dealer cards before call, bound ownership, independent rounds, exact replay, and conflict closure.
            assert 'dealer_hand' not in caribbean_deal_a['round'] and caribbean_a['round']['player_id']==user_a['player_id'] and caribbean_b['round']['player_id']==user_b['player_id'] and caribbean_a['round']['round_id']!=caribbean_b['round']['round_id'] and caribbean_a_replay['replayed'] is True and caribbean_a_replay['round']['dealer_hand']==caribbean_a['round']['dealer_hand'] and caribbean_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            caribbean_state_a=api(base,f'/api/v1/games/caribbean-stud/state?player_id={user_b["player_id"]}',auth_token=token_a); caribbean_state_b=api(base,f'/api/v1/games/caribbean-stud/state?player_id={user_a["player_id"]}',auth_token=token_b); assert caribbean_state_a['state']['recent_rounds'][-1]['round_id']==caribbean_a['round']['round_id'] and caribbean_state_b['state']['recent_rounds'][-1]['round_id']==caribbean_b['round']['round_id']
            # Require one ante debit, one call debit, and at most one returned-token credit for the replayed round.
            caribbean_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; caribbean_events_a=[row for row in caribbean_ledger_a if row.get('game')=='caribbean_stud' and row.get('round_id')==caribbean_a['round']['round_id']]; assert sum(row.get('transaction_type')=='CARIBBEAN_STUD_ANTE_DEBIT' for row in caribbean_events_a)==1 and sum(row.get('transaction_type')=='CARIBBEAN_STUD_CALL_DEBIT' for row in caribbean_events_a)==1 and sum(row.get('transaction_type')=='CARIBBEAN_STUD_SETTLEMENT_CREDIT' for row in caribbean_events_a)<=1
            # Prepare two session-bound Let It Ride rounds while hostile body identities challenge ownership.
            let_it_ride_deal_a=api(base,'/api/v1/games/let-it-ride/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-let-it-ride-deal-a','wager':1},auth_token=token_a); let_it_ride_deal_b=api(base,'/api/v1/games/let-it-ride/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-let-it-ride-deal-b','wager':1},auth_token=token_b)
            # Pull the first eligible unit for each private round and reveal one community card.
            let_it_ride_first_a=api(base,f'/api/v1/games/let-it-ride/rounds/{let_it_ride_deal_a["round"]["round_id"]}/first-decision','POST',{'player_id':user_b['player_id'],'action_id':'wallet-let-it-ride-first-a','decision':'pull'},auth_token=token_a); let_it_ride_first_b=api(base,f'/api/v1/games/let-it-ride/rounds/{let_it_ride_deal_b["round"]["round_id"]}/first-decision','POST',{'player_id':user_a['player_id'],'action_id':'wallet-let-it-ride-first-b','decision':'pull'},auth_token=token_b)
            # Let the remaining units ride through each independent terminal settlement.
            let_it_ride_a=api(base,f'/api/v1/games/let-it-ride/rounds/{let_it_ride_deal_a["round"]["round_id"]}/second-decision','POST',{'player_id':user_b['player_id'],'action_id':'wallet-let-it-ride-second-a','decision':'ride'},auth_token=token_a); let_it_ride_b=api(base,f'/api/v1/games/let-it-ride/rounds/{let_it_ride_deal_b["round"]["round_id"]}/second-decision','POST',{'player_id':user_a['player_id'],'action_id':'wallet-let-it-ride-second-b','decision':'ride'},auth_token=token_b)
            # Replay one terminal action and reject changed wager meaning under the original opening identity.
            let_it_ride_a_replay=api(base,f'/api/v1/games/let-it-ride/rounds/{let_it_ride_deal_a["round"]["round_id"]}/second-decision','POST',{'player_id':user_b['player_id'],'action_id':'wallet-let-it-ride-second-a','decision':'ride'},auth_token=token_a); let_it_ride_conflict=api(base,'/api/v1/games/let-it-ride/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-let-it-ride-deal-a','wager':2},ok=False,auth_token=token_a)
            # Require hidden community cards before decisions, bound ownership, independent rounds, exact replay, and conflict closure.
            assert let_it_ride_deal_a['round']['community_cards']==[None,None] and let_it_ride_first_a['round']['community_cards'][0] and let_it_ride_first_a['round']['community_cards'][1] is None and let_it_ride_a['round']['player_id']==user_a['player_id'] and let_it_ride_b['round']['player_id']==user_b['player_id'] and let_it_ride_a['round']['round_id']!=let_it_ride_b['round']['round_id'] and let_it_ride_a_replay['replayed'] is True and let_it_ride_a_replay['round']==let_it_ride_a['round'] and let_it_ride_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            let_it_ride_state_a=api(base,f'/api/v1/games/let-it-ride/state?player_id={user_b["player_id"]}',auth_token=token_a); let_it_ride_state_b=api(base,f'/api/v1/games/let-it-ride/state?player_id={user_a["player_id"]}',auth_token=token_b); assert let_it_ride_state_a['state']['rounds'][0]['round_id']==let_it_ride_a['round']['round_id'] and let_it_ride_state_b['state']['rounds'][0]['round_id']==let_it_ride_b['round']['round_id']
            # Require one three-unit debit, one pull refund, and at most one final payout for the replayed round.
            let_it_ride_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; let_it_ride_events_a=[row for row in let_it_ride_ledger_a if row.get('game')=='let_it_ride' and row.get('round_id')==let_it_ride_a['round']['round_id']]; assert sum(row.get('transaction_type')=='LET_IT_RIDE_WAGER_DEBIT' for row in let_it_ride_events_a)==1 and sum(row.get('transaction_type')=='LET_IT_RIDE_REFUND_CREDIT' for row in let_it_ride_events_a)==1 and sum(row.get('transaction_type')=='LET_IT_RIDE_PAYOUT_CREDIT' for row in let_it_ride_events_a)<=1
            # Prepare two session-bound Casino Hold'em rounds while hostile body identities challenge ownership.
            casino_holdem_deal_a=api(base,'/api/v1/games/casino-holdem/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-casino-holdem-deal-a','wager':1},auth_token=token_a); casino_holdem_deal_b=api(base,'/api/v1/games/casino-holdem/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-casino-holdem-deal-b','wager':1},auth_token=token_b)
            # Call both private post-flop rounds through independent session-bound actions.
            casino_holdem_a=api(base,f'/api/v1/games/casino-holdem/rounds/{casino_holdem_deal_a["round"]["round_id"]}/decision','POST',{'player_id':user_b['player_id'],'action_id':'wallet-casino-holdem-decision-a','decision':'call'},auth_token=token_a); casino_holdem_b=api(base,f'/api/v1/games/casino-holdem/rounds/{casino_holdem_deal_b["round"]["round_id"]}/decision','POST',{'player_id':user_a['player_id'],'action_id':'wallet-casino-holdem-decision-b','decision':'call'},auth_token=token_b)
            # Replay one terminal action and reject changed wager meaning under the original opening identity.
            casino_holdem_a_replay=api(base,f'/api/v1/games/casino-holdem/rounds/{casino_holdem_deal_a["round"]["round_id"]}/decision','POST',{'player_id':user_b['player_id'],'action_id':'wallet-casino-holdem-decision-a','decision':'call'},auth_token=token_a); casino_holdem_conflict=api(base,'/api/v1/games/casino-holdem/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-casino-holdem-deal-a','wager':2},ok=False,auth_token=token_a)
            # Require private dealer cards before call, bound ownership, independent rounds, exact replay, and conflict closure.
            assert 'dealer_cards' not in casino_holdem_deal_a['round'] and len(casino_holdem_deal_a['round']['community_cards'])==3 and casino_holdem_a['round']['player_id']==user_a['player_id'] and casino_holdem_b['round']['player_id']==user_b['player_id'] and casino_holdem_a['round']['round_id']!=casino_holdem_b['round']['round_id'] and casino_holdem_a_replay['replayed'] is True and casino_holdem_a_replay['round']==casino_holdem_a['round'] and casino_holdem_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            casino_holdem_state_a=api(base,f'/api/v1/games/casino-holdem/state?player_id={user_b["player_id"]}',auth_token=token_a); casino_holdem_state_b=api(base,f'/api/v1/games/casino-holdem/state?player_id={user_a["player_id"]}',auth_token=token_b); assert casino_holdem_state_a['state']['recent_rounds'][-1]['round_id']==casino_holdem_a['round']['round_id'] and casino_holdem_state_b['state']['recent_rounds'][-1]['round_id']==casino_holdem_b['round']['round_id']
            # Require one ante debit, one call debit, and at most one returned-token credit for the replayed round.
            casino_holdem_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; casino_holdem_events_a=[row for row in casino_holdem_ledger_a if row.get('game')=='casino_holdem' and row.get('round_id')==casino_holdem_a['round']['round_id']]; assert sum(row.get('transaction_type')=='CASINO_HOLDEM_ANTE_DEBIT' for row in casino_holdem_events_a)==1 and sum(row.get('transaction_type')=='CASINO_HOLDEM_CALL_DEBIT' for row in casino_holdem_events_a)==1 and sum(row.get('transaction_type')=='CASINO_HOLDEM_SETTLEMENT_CREDIT' for row in casino_holdem_events_a)<=1
            # Prepare two session-bound Pai Gow Poker rounds while hostile body identities challenge ownership.
            pai_gow_poker_deal_a=api(base,'/api/v1/games/pai-gow-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-pai-gow-poker-deal-a','ante':1},auth_token=token_a); pai_gow_poker_deal_b=api(base,'/api/v1/games/pai-gow-poker/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-pai-gow-poker-deal-b','ante':1},auth_token=token_b)
            # Set both private seven-card hands by the house way through independent session-bound actions.
            pai_gow_poker_a=api(base,f'/api/v1/games/pai-gow-poker/rounds/{pai_gow_poker_deal_a["round"]["round_id"]}/decisions','POST',{'player_id':user_b['player_id'],'action_id':'wallet-pai-gow-poker-decision-a','set':'house_way'},auth_token=token_a); pai_gow_poker_b=api(base,f'/api/v1/games/pai-gow-poker/rounds/{pai_gow_poker_deal_b["round"]["round_id"]}/decisions','POST',{'player_id':user_a['player_id'],'action_id':'wallet-pai-gow-poker-decision-b','set':'house_way'},auth_token=token_b)
            # Replay one terminal action and reject a changed ante meaning under the original opening identity.
            pai_gow_poker_a_replay=api(base,f'/api/v1/games/pai-gow-poker/rounds/{pai_gow_poker_deal_a["round"]["round_id"]}/decisions','POST',{'player_id':user_b['player_id'],'action_id':'wallet-pai-gow-poker-decision-a','set':'house_way'},auth_token=token_a); pai_gow_poker_conflict=api(base,'/api/v1/games/pai-gow-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-pai-gow-poker-deal-a','ante':2},ok=False,auth_token=token_a)
            # Require private dealer cards before setting, seven dealt cards, bound ownership, independent rounds, exact replay, and conflict closure.
            assert 'dealer_high' not in pai_gow_poker_deal_a['round'] and len(pai_gow_poker_deal_a['round']['player_cards'])==7 and pai_gow_poker_a['round']['player_id']==user_a['player_id'] and pai_gow_poker_b['round']['player_id']==user_b['player_id'] and pai_gow_poker_a['round']['round_id']!=pai_gow_poker_b['round']['round_id'] and pai_gow_poker_a_replay['replayed'] is True and pai_gow_poker_a_replay['round']==pai_gow_poker_a['round'] and pai_gow_poker_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            pai_gow_poker_state_a=api(base,f'/api/v1/games/pai-gow-poker/state?player_id={user_b["player_id"]}',auth_token=token_a); pai_gow_poker_state_b=api(base,f'/api/v1/games/pai-gow-poker/state?player_id={user_a["player_id"]}',auth_token=token_b); assert pai_gow_poker_state_a['state']['recent_rounds'][-1]['round_id']==pai_gow_poker_a['round']['round_id'] and pai_gow_poker_state_b['state']['recent_rounds'][-1]['round_id']==pai_gow_poker_b['round']['round_id']
            # Require one ante debit and at most one returned-token credit for the replayed round.
            pai_gow_poker_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; pai_gow_poker_events_a=[row for row in pai_gow_poker_ledger_a if row.get('game')=='pai_gow_poker' and row.get('round_id')==pai_gow_poker_a['round']['round_id']]; assert sum(row.get('transaction_type')=='PAI_GOW_POKER_ANTE_DEBIT' for row in pai_gow_poker_events_a)==1 and sum(row.get('transaction_type')=='PAI_GOW_POKER_SETTLEMENT_CREDIT' for row in pai_gow_poker_events_a)<=1
            # Prepare two session-bound Joker Poker hands while hostile body identities challenge ownership.
            joker_poker_deal_a=api(base,'/api/v1/games/joker-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-joker-poker-deal-a','wager':1},auth_token=token_a); joker_poker_deal_b=api(base,'/api/v1/games/joker-poker/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-joker-poker-deal-b','wager':1},auth_token=token_b)
            # Persist independent hold selections through the public session-bound route.
            api(base,f'/api/v1/games/joker-poker/rounds/{joker_poker_deal_a["round"]["round_id"]}/holds','POST',{'player_id':user_b['player_id'],'holds':[0]},auth_token=token_a); api(base,f'/api/v1/games/joker-poker/rounds/{joker_poker_deal_b["round"]["round_id"]}/holds','POST',{'player_id':user_a['player_id'],'holds':[1]},auth_token=token_b)
            # Draw and settle both private hands under stable terminal action identities.
            joker_poker_a=api(base,f'/api/v1/games/joker-poker/rounds/{joker_poker_deal_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id'],'action_id':'wallet-joker-poker-draw-a','holds':[0]},auth_token=token_a); joker_poker_b=api(base,f'/api/v1/games/joker-poker/rounds/{joker_poker_deal_b["round"]["round_id"]}/draw','POST',{'player_id':user_a['player_id'],'action_id':'wallet-joker-poker-draw-b','holds':[1]},auth_token=token_b)
            # Replay one terminal draw and reject changed wager meaning under the original opening identity.
            joker_poker_a_replay=api(base,f'/api/v1/games/joker-poker/rounds/{joker_poker_deal_a["round"]["round_id"]}/draw','POST',{'player_id':user_b['player_id'],'action_id':'wallet-joker-poker-draw-a','holds':[0]},auth_token=token_a); joker_poker_conflict=api(base,'/api/v1/games/joker-poker/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-joker-poker-deal-a','wager':2},ok=False,auth_token=token_a)
            # Require private draw pools, bound ownership, independent hands, exact replay, and conflict closure.
            assert '_draw_pool' not in joker_poker_deal_a['round'] and joker_poker_a['round']['player_id']==user_a['player_id'] and joker_poker_b['round']['player_id']==user_b['player_id'] and joker_poker_a['round']['round_id']!=joker_poker_b['round']['round_id'] and joker_poker_a_replay['replayed'] is True and joker_poker_a_replay['round']==joker_poker_a['round'] and joker_poker_conflict['error']['code']=='CONFLICT'
            # Read both private states with hostile query identities and require isolated settled history.
            joker_poker_state_a=api(base,f'/api/v1/games/joker-poker/state?player_id={user_b["player_id"]}',auth_token=token_a); joker_poker_state_b=api(base,f'/api/v1/games/joker-poker/state?player_id={user_a["player_id"]}',auth_token=token_b); assert joker_poker_state_a['state']['recent_rounds'][-1]['round_id']==joker_poker_a['round']['round_id'] and joker_poker_state_b['state']['recent_rounds'][-1]['round_id']==joker_poker_b['round']['round_id']
            # Require one wager debit and at most one returned-token payout credit for the replayed hand.
            joker_poker_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; joker_poker_events_a=[row for row in joker_poker_ledger_a if row.get('game')=='joker_poker' and row.get('round_id')==joker_poker_a['round']['round_id']]; assert sum(row.get('transaction_type')=='JOKER_POKER_WAGER_DEBIT' for row in joker_poker_events_a)==1 and sum(row.get('transaction_type')=='JOKER_POKER_PAYOUT_CREDIT' for row in joker_poker_events_a)<=1
            # Build fields a hostile client must never use to author identity, cards, outcome, payout, wallet, phase, or privilege.
            thpt_hostile_fields={'role':'admin','admin':True,'balance':999999,'cards':['AS','AS'],'deck':['AS'],'rng_seed':'attacker-seed','outcome':'attacker-win','payout':999999,'settlement_total':999999,'phase':'settled','turn':'opponent_1'}
            # Start two funded-opponent practice hands while hostile protected fields and body identities challenge server authority.
            thpt_start_a=api(base,'/api/v1/games/texas-holdem-practice-table/hands','POST',{**thpt_hostile_fields,'player_id':user_b['player_id'],'action_id':'wallet-thpt-start-a','base_wager':1},auth_token=token_a); thpt_start_b=api(base,'/api/v1/games/texas-holdem-practice-table/hands','POST',{**thpt_hostile_fields,'player_id':user_a['player_id'],'action_id':'wallet-thpt-start-b','base_wager':1},auth_token=token_b)
            # Replay one opening command and reject changed wallet exposure under the same storage identity.
            thpt_start_a_replay=api(base,'/api/v1/games/texas-holdem-practice-table/hands','POST',{'player_id':user_b['player_id'],'action_id':'wallet-thpt-start-a','base_wager':1},auth_token=token_a); thpt_start_conflict=api(base,'/api/v1/games/texas-holdem-practice-table/hands','POST',{'player_id':user_b['player_id'],'action_id':'wallet-thpt-start-a','base_wager':2},ok=False,auth_token=token_a)
            # Require private opponent cards, protected-field removal, exact clean replay, changed-reuse conflict, and distinct session-owned hands.
            assert all(seat['hole_cards']==['??','??'] for seat in thpt_start_a['hand']['seats'][1:]) and not ({'cards','deck','rng_seed','outcome','payout','settlement_total'} & set(thpt_start_a['hand'])) and thpt_start_a_replay['replayed'] is True and thpt_start_a_replay['hand']==thpt_start_a['hand'] and thpt_start_conflict['error']['code']=='CONFLICT' and thpt_start_a['hand']['hand_id']!=thpt_start_b['hand']['hand_id']
            # Submit a future-street action and require turn/phase validation before any state or wallet transition.
            thpt_stale=api(base,f'/api/v1/games/texas-holdem-practice-table/hands/{thpt_start_a["hand"]["hand_id"]}/actions','POST',{**thpt_hostile_fields,'player_id':user_b['player_id'],'action_id':'wallet-thpt-stale-a','action':'call','expected_phase':'river'},ok=False,auth_token=token_a); thpt_stale_state=api(base,'/api/v1/games/texas-holdem-practice-table/state',auth_token=token_a); assert thpt_stale['error']['code']=='CONFLICT' and thpt_stale_state['state']['active_hand']['phase']=='preflop' and not thpt_stale_state['state']['active_hand']['action_log']
            # Advance both independent hands through every fixed-limit public decision street.
            thpt_a=thpt_start_a; thpt_b=thpt_start_b
            # Exercise preflop, flop, turn, and river with stable per-session action identities.
            for street_index,phase in enumerate(('preflop','flop','turn','river')):
                # Apply user A's call while again submitting user B's hostile identity.
                thpt_a=api(base,f'/api/v1/games/texas-holdem-practice-table/hands/{thpt_start_a["hand"]["hand_id"]}/actions','POST',{**thpt_hostile_fields,'player_id':user_b['player_id'],'action_id':f'wallet-thpt-call-a-{street_index}','action':'call','expected_phase':phase},auth_token=token_a)
                # Apply user B's independent call under its own authenticated session.
                thpt_b=api(base,f'/api/v1/games/texas-holdem-practice-table/hands/{thpt_start_b["hand"]["hand_id"]}/actions','POST',{'player_id':user_a['player_id'],'action_id':f'wallet-thpt-call-b-{street_index}','action':'call','expected_phase':phase},auth_token=token_b)
            # Replay user A's terminal river decision and reject user B's attempt against user A's private hand.
            thpt_a_replay=api(base,f'/api/v1/games/texas-holdem-practice-table/hands/{thpt_start_a["hand"]["hand_id"]}/actions','POST',{'player_id':user_b['player_id'],'action_id':'wallet-thpt-call-a-3','action':'call','expected_phase':'river'},auth_token=token_a); thpt_cross=api(base,f'/api/v1/games/texas-holdem-practice-table/hands/{thpt_start_a["hand"]["hand_id"]}/actions','POST',{'player_id':user_a['player_id'],'action_id':'wallet-thpt-cross-b','action':'call','expected_phase':'river'},ok=False,auth_token=token_b)
            # Require complete four-wallet reconciliation, post-rake pot conservation, exact terminal replay, and closed cross-user lookup.
            assert thpt_a['hand']['phase']=='settled' and thpt_b['hand']['phase']=='settled' and thpt_a['hand']['settlement']['complete'] and thpt_a['hand']['settlement']['required_actions']==thpt_a['hand']['settlement']['committed_actions'] and round(sum(thpt_a['hand']['result']['payouts'].values())+thpt_a['hand']['result']['rake'],2)==round(thpt_a['hand']['pot'],2) and max(thpt_a['hand']['result']['payouts'].values())<999999 and thpt_a_replay['replayed'] is True and thpt_a_replay['hand']==thpt_a['hand'] and thpt_cross['error']['code']=='NOT_FOUND'
            # Read both private states with hostile query identities and require isolated settled history.
            thpt_state_a=api(base,f'/api/v1/games/texas-holdem-practice-table/state?player_id={user_b["player_id"]}',auth_token=token_a); thpt_state_b=api(base,f'/api/v1/games/texas-holdem-practice-table/state?player_id={user_a["player_id"]}',auth_token=token_b); assert thpt_state_a['state']['recent_hands'][0]['hand_id']==thpt_a['hand']['hand_id'] and thpt_state_b['state']['recent_hands'][0]['hand_id']==thpt_b['hand']['hand_id'] and thpt_state_a['state']['rules']['funded_opponents'] is True
            # Require exactly one storage-enforced human escrow and bounded terminal credits for the replayed hand.
            thpt_ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; thpt_events_a=[row for row in thpt_ledger_a if row.get('game')=='texas_holdem_practice_table' and row.get('round_id')==thpt_a['hand']['hand_id']]; assert sum(row.get('transaction_type')=='TEXAS_HOLDEM_ESCROW_DEBIT' for row in thpt_events_a)==1 and sum(row.get('transaction_type')=='TEXAS_HOLDEM_ESCROW_REFUND_CREDIT' for row in thpt_events_a)<=1 and sum(row.get('transaction_type')=='TEXAS_HOLDEM_PAYOUT_CREDIT' for row in thpt_events_a)<=1
            # Read Admin-only opponent activity and require three real escrows with owning-session audit dimensions.
            thpt_admin=api(base,'/api/v1/admin/bots'); thpt_bot_events=[row for row in thpt_admin['practice_opponent_activity'] if row.get('round_id')==thpt_a['hand']['hand_id']]; assert sum(row.get('transaction_type')=='PRACTICE_OPPONENT_ESCROW_DEBIT' for row in thpt_bot_events)==3 and all((row.get('details') or {}).get('session_owner_id')==user_a['player_id'] and (row.get('details') or {}).get('practice_action_key') for row in thpt_bot_events)
            # Read private game history through each normal-user session.
            history_a=api(base,'/api/v1/casino/history',auth_token=token_a)['history']
            # Read user B's independent history view.
            history_b=api(base,'/api/v1/casino/history',auth_token=token_b)['history']
            # Verify history never exposes the other authenticated player's records.
            assert history_a and history_b and all(row['player_id']==user_a['player_id'] for row in history_a) and all(row['player_id']==user_b['player_id'] for row in history_b)
            # Refresh both canonical wallets after every integrated game has settled.
            wallet_a=api(base,'/api/v2/me',auth_token=token_a)['player']['token_balance']
            # Refresh user B's canonical wallet independently.
            wallet_b=api(base,'/api/v2/me',auth_token=token_b)['player']['token_balance']
            # Verify final ledger balances agree with the canonical wallet refresh for each user.
            ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']; assert ledger_a[-1]['balance_after']==wallet_a and ledger_b[-1]['balance_after']==wallet_b
            # Log out both real sessions after the integrated game path.
            api(base,'/api/v2/auth/logout','POST',{},auth_token=token_a); api(base,'/api/v2/auth/logout','POST',{},auth_token=token_b)
            # Verify both logged-out bearer tokens are rejected.
            assert api(base,'/api/v2/me',ok=False,auth_token=token_a)['error']['code']=='UNAUTHORIZED' and api(base,'/api/v2/me',ok=False,auth_token=token_b)['error']['code']=='UNAUTHORIZED'
            # Log both users in again so later cross-user and restart checks use fresh sessions.
            token_a=api(base,'/api/v2/auth/login','POST',{'username':'wallet-a@example.local','password':'wallet-a-password'},auth_token=None)['session']['token']; token_b=api(base,'/api/v2/auth/login','POST',{'username':'wallet-b@example.local','password':'wallet-b-password'},auth_token=None)['session']['token']
            # Start autoplay with a foreign id and verify the authenticated binding wins.
            auto_a=api(base,'/api/v1/autoplay/start','POST',{'game_id':'roulette','player_id':user_b['player_id'],'speed':'medium','round_limit':1},auth_token=token_a)['session']
            # Verify user B cannot mutate user A's server-side autoplay session.
            cross_auto=api(base,'/api/v1/autoplay/stop','POST',{'autoplay_id':auto_a['autoplay_id']},ok=False,auth_token=token_b); assert auto_a['player_id']==user_a['player_id'] and cross_auto['error']['code']=='FORBIDDEN'
            # Enumerate every registered Admin route shape to prove the central role gate fails closed.
            admin_paths=[('GET','/api/v1/admin/overview'),('GET','/api/v1/admin/dashboard'),('GET','/api/v1/admin/modules'),('GET','/api/v1/admin/requirements'),('GET','/api/v1/admin/game-states'),('GET','/api/v1/admin/users'),('POST','/api/v1/admin/users'),('GET',f'/api/v1/admin/users/{user_b["user_id"]}'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/deactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/reactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/password-reset'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/terms'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/locale'),('GET','/api/v1/admin/logs'),('GET','/api/v1/admin/ledger'),('GET','/api/v1/admin/history'),('GET','/api/v1/admin/test-results'),('GET','/api/v1/admin/audio-settings'),('POST','/api/v1/admin/audio-settings'),('GET','/api/v1/admin/autoplay'),('POST','/api/v1/admin/autoplay/stop-all'),('GET','/api/v1/admin/bots'),('POST','/api/v1/admin/bots/practice-opponents/fund'),('GET','/api/v2/admin/operations'),('GET','/api/v2/admin/oauth/providers'),('GET','/api/v2/admin/mail/readiness'),('GET','/api/v2/admin/users'),('POST','/api/v2/admin/users'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}'),('POST',f'/api/v2/admin/users/{user_b["user_id"]}/password'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}/terms'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}/state')]
            # Request each Admin endpoint as a normal user and require a forbidden response.
            for method,path in admin_paths:
                # Send an empty body for mutating routes because authorization must run before validation.
                blocked=api(base,path,method,{} if method in ('POST','PATCH') else None,ok=False,auth_token=token_a); assert blocked['error']['code']=='FORBIDDEN', (method,path,blocked)
            # Verify normal users also cannot invoke shared reset or global logs.
            assert api(base,'/api/v1/casino/reset','POST',{},ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN' and api(base,'/api/v1/casino/logs/recent',ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN'
            # Verify normal users cannot mutate shared bot-controller accounts.
            assert api(base,'/api/v1/bots/bot_roulette_1/enable','POST',{},ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN'
            # Store the durable post-game balance and terms state for restart verification.
            integrity_state.update({'email':'wallet-a@example.local','password':'wallet-a-password','balance':api(base,'/api/v2/me',auth_token=token_a)['player']['token_balance'],'admin_blocked':len(admin_paths),'token_credit_count':len(credits_after)-len(credits_before),'contract_player':added_a,'mhvp_verified':True,'casino_war_verified':True,'big_six_verified':True,'red_dog_verified':True,'dragon_tiger_verified':True,'hi_lo_verified':True,'users':[{'email':'wallet-a@example.local','password':'wallet-a-password','player_id':user_a['player_id'],'balance':wallet_a,'roulette_round':roulette_a['round']['round_id'],'slots_round':slot_a['round_id'],'blackjack_round':blackjack_a['round_id'],'baccarat_round':baccarat_a['coup']['round_id'],'keno_round':keno_a['draw']['round_id'],'bingo_session':bingo_a_session['session_id'],'bingo_completed':False,'bingo_history_owned':True,'mhvp_round':mhvp_a['round']['round_id'],'casino_war_round':casino_war_a['round']['round_id'],'big_six_round':big_six_a['round']['round_id'],'red_dog_round':red_dog_a['round']['round_id'],'dragon_tiger_round':dragon_tiger_a['round']['round_id'],'hi_lo_round':hi_lo_a['round']['round_id']},{'email':'wallet-b@example.local','password':'wallet-b-password','player_id':user_b['player_id'],'balance':wallet_b,'roulette_round':roulette_b['round']['round_id'],'slots_round':slot_b['round_id'],'blackjack_round':blackjack_b['round_id'],'baccarat_round':baccarat_b['coup']['round_id'],'keno_round':keno_b['draw']['round_id'],'bingo_session':bingo_b['session']['session_id'],'bingo_completed':True,'bingo_history_owned':bingo_b['session'].get('winner') in (None,user_b['player_id']),'mhvp_round':mhvp_b['round']['round_id'],'casino_war_round':casino_war_b['round']['round_id'],'big_six_round':big_six_b['round']['round_id'],'red_dog_round':red_dog_b['round']['round_id'],'dragon_tiger_round':dragon_tiger_b['round']['round_id'],'hi_lo_round':hi_lo_b['round']['round_id']}],'history_game_counts':[len(history_a),len(history_b)]})
            # Retain Scratch Card ids by authenticated player for process-restart verification.
            integrity_state['scratch_cards']={user_a['player_id']:scratch_a['card']['card_id'],user_b['player_id']:scratch_b['card']['card_id']}
            # Retain Sic Bo round ids by authenticated player for process-restart verification.
            integrity_state['sic_bo_rounds']={user_a['player_id']:sic_a['round']['round_id'],user_b['player_id']:sic_b['round']['round_id']}
            # Retain Chuck-a-Luck round ids by authenticated player for process-restart verification.
            integrity_state['chuck_a_luck_rounds']={user_a['player_id']:chuck_a['round']['round_id'],user_b['player_id']:chuck_b['round']['round_id']}
            # Retain Craps round ids by authenticated player for process-restart verification.
            integrity_state['craps_rounds']={user_a['player_id']:craps_a['round']['round_id'],user_b['player_id']:craps_b['round']['round_id']}
            # Retain Crown and Anchor round ids by authenticated player for process-restart verification.
            integrity_state['crown_and_anchor_rounds']={user_a['player_id']:crown_a['round']['round_id'],user_b['player_id']:crown_b['round']['round_id']}
            # Retain Over/Under 7 round ids by authenticated player for process-restart verification.
            integrity_state['over_under_7_rounds']={user_a['player_id']:ou7_a['round']['round_id'],user_b['player_id']:ou7_b['round']['round_id']}
            # Retain Plinko drop ids by authenticated player for process-restart verification.
            integrity_state['plinko_drops']={user_a['player_id']:plinko_a['drop']['drop_id'],user_b['player_id']:plinko_b['drop']['drop_id']}
            # Retain Fan-Tan round ids by authenticated player for process-restart verification.
            integrity_state['fan_tan_rounds']={user_a['player_id']:fan_tan_a['round']['round_id'],user_b['player_id']:fan_tan_b['round']['round_id']}
            # Retain Andar Bahar round ids by authenticated player for process-restart verification.
            integrity_state['andar_bahar_rounds']={user_a['player_id']:andar_bahar_a['round']['round_id'],user_b['player_id']:andar_bahar_b['round']['round_id']}
            # Retain Acey-Deucey round ids by authenticated player for process-restart verification.
            integrity_state['acey_deucey_rounds']={user_a['player_id']:acey_deucey_a['round']['round_id'],user_b['player_id']:acey_deucey_b['round']['round_id']}
            # Retain Caribbean Stud round ids by authenticated player for process-restart verification.
            integrity_state['caribbean_stud_rounds']={user_a['player_id']:caribbean_a['round']['round_id'],user_b['player_id']:caribbean_b['round']['round_id']}
            # Retain Let It Ride round ids by authenticated player for process-restart verification.
            integrity_state['let_it_ride_rounds']={user_a['player_id']:let_it_ride_a['round']['round_id'],user_b['player_id']:let_it_ride_b['round']['round_id']}
            # Retain Casino Hold'em round ids by authenticated player for process-restart verification.
            integrity_state['casino_holdem_rounds']={user_a['player_id']:casino_holdem_a['round']['round_id'],user_b['player_id']:casino_holdem_b['round']['round_id']}
            # Retain Pai Gow Poker round ids by authenticated player for process-restart verification.
            integrity_state['pai_gow_poker_rounds']={user_a['player_id']:pai_gow_poker_a['round']['round_id'],user_b['player_id']:pai_gow_poker_b['round']['round_id']}
            # Retain Joker Poker round ids by authenticated player for process-restart verification.
            integrity_state['joker_poker_rounds']={user_a['player_id']:joker_poker_a['round']['round_id'],user_b['player_id']:joker_poker_b['round']['round_id']}
            # Retain Texas Hold'em hand ids by authenticated player for process-restart verification.
            integrity_state['texas_holdem_practice_hands']={user_a['player_id']:thpt_a['hand']['hand_id'],user_b['player_id']:thpt_b['hand']['hand_id']}
            # Retain Three Card Poker round ids by authenticated player so its mapped case pins real evidence. (issue #414)
            integrity_state['three_card_poker_rounds']={user_a['player_id']:tcp_a['round']['round_id'],user_b['player_id']:tcp_b['round']['round_id']}
            # Retain Jacks or Better round ids by authenticated player so its mapped case pins real evidence. (issue #414)
            integrity_state['jacks_or_better_rounds']={user_a['player_id']:jobvp_a['round']['round_id'],user_b['player_id']:jobvp_b['round']['round_id']}
            # Retain Deuces Wild round ids by authenticated player so its mapped case pins real evidence. (issue #414)
            integrity_state['deuces_wild_rounds']={user_a['player_id']:dwvp_a['round']['round_id'],user_b['player_id']:dwvp_b['round']['round_id']}
        # Register the complete shared session/wallet-integrity block before restart evidence.
        api_session_integrity.run_cases(run_case,wallet_auth_integrity,integrity_state,assert_condition)
        # Stop and verify the live backend before persistence is tested across a process boundary.
        stop_server(proc,base)
        # Start a fresh backend process against the same configured provider state.
        proc,base=start_server()
        # Define wallet_restart_persistence to verify canonical identity and ledger state survive restart.
        def wallet_restart_persistence():
            # Iterate through both canonical users after the backend process restart.
            for expected in integrity_state['users']:
                # Log in the Admin-created normal user after the new server process starts.
                login=api(base,'/api/v2/auth/login','POST',{'username':expected['email'],'password':expected['password']},auth_token=None)
                # Store the restarted session token for private state checks.
                token=login['session']['token']
                # Read the canonical current-user state through the restarted backend.
                me=api(base,'/api/v2/me',auth_token=token)
                # Verify exact balance and accepted terms survived the process restart.
                assert me['player']['token_balance']==expected['balance'] and me['terms']['accepted'] is True and me['terms']['required'] is False
                # Read every private game state again after restart.
                roulette_state=api(base,'/api/v1/games/roulette/state',auth_token=token)['state']; slots_state=api(base,'/api/v1/games/slots/state',auth_token=token)['state']; blackjack_state=api(base,'/api/v1/games/blackjack/state',auth_token=token)['state']; baccarat_state=api(base,'/api/v1/games/baccarat/state',auth_token=token)['state']; keno_state=api(base,'/api/v1/games/keno/state',auth_token=token)['state']; bingo_state=api(base,'/api/v1/games/bingo/state',auth_token=token)['state']; mhvp_state=api(base,'/api/v1/games/multi-hand-video-poker/state',auth_token=token)['state']; casino_war_state=api(base,'/api/v1/games/casino-war/state',auth_token=token)['state']; big_six_state=api(base,'/api/v1/games/big-six-wheel/state',auth_token=token); red_dog_state=api(base,'/api/v1/games/red-dog/state',auth_token=token)['state']; dragon_tiger_state=api(base,'/api/v1/games/dragon-tiger/state',auth_token=token)['state']; hi_lo_state=api(base,'/api/v1/games/hi-lo/state',auth_token=token)['state']
                # Verify Roulette, Slots, Blackjack, Baccarat, and Keno identifiers survived under the session-derived player.
                assert any(row['round_id']==expected['roulette_round'] for row in roulette_state['last_results']) and slots_state['last_spins'][-1]['round_id']==expected['slots_round'] and expected['blackjack_round'] in blackjack_state['rounds'] and any(row['round_id']==expected['baccarat_round'] for row in baccarat_state['last_coups']) and any(row['round_id']==expected['keno_round'] for row in keno_state['last_draws'])
                # Verify Bingo terminal/refund state survived for the corresponding user.
                assert (any(row['session_id']==expected['bingo_session'] for row in bingo_state['last_sessions']) if expected['bingo_completed'] else bingo_state['active_session'] is None)
                # Verify the settled video poker round survived and remains private after restart.
                assert any(row['round_id']==expected['mhvp_round'] for row in mhvp_state['recent_rounds'])
                # Verify the settled Casino War round survived and remains private after restart.
                assert any(row['round_id']==expected['casino_war_round'] for row in casino_war_state['rounds'])
                # Verify the settled Big Six round survived and remains private after restart.
                assert any(row['round_id']==expected['big_six_round'] for row in big_six_state['recent_rounds'])
                # Verify the settled Red Dog round survived and remains private after restart.
                assert any(row['round_id']==expected['red_dog_round'] for row in red_dog_state['rounds'])
                # Verify the settled Dragon Tiger round and shoe metadata survived and remain private after restart.
                assert any(row['round_id']==expected['dragon_tiger_round'] for row in dragon_tiger_state['recent_rounds']) and dragon_tiger_state['shoe']['shoe_number']>=1
                # Verify the settled Hi-Lo round survived and remains private after restart.
                assert any(row['round_id']==expected['hi_lo_round'] for row in hi_lo_state['recent_rounds'])
                # Read and verify this user's terminal Scratch Card after the real process restart.
                scratch_state=api(base,'/api/v1/games/scratch-cards/state',auth_token=token); assert scratch_state['current_card']['card_id']==integrity_state['scratch_cards'][expected['player_id']] and scratch_state['current_card']['status']=='settled'
                # Read and verify this user's settled Sic Bo round after the real process restart.
                sic_bo_state=api(base,'/api/v1/games/sic-bo/state',auth_token=token)['state']; assert any(row['round_id']==integrity_state['sic_bo_rounds'][expected['player_id']] for row in sic_bo_state['recent_rounds'])
                # Read and verify this user's settled Chuck-a-Luck roll after the real process restart.
                chuck_state=api(base,'/api/v1/games/chuck-a-luck/state',auth_token=token)['state']; assert any(row['round_id']==integrity_state['chuck_a_luck_rounds'][expected['player_id']] for row in chuck_state['recent_rounds'])
                # Read and verify this user's settled Craps round after the real process restart.
                craps_state=api(base,'/api/v1/games/craps/state',auth_token=token)['state']; assert any(row['round_id']==integrity_state['craps_rounds'][expected['player_id']] for row in craps_state['recent_rounds'])
                # Read and verify this user's settled Crown and Anchor round after the real process restart.
                crown_state=api(base,'/api/v1/games/crown-and-anchor/state',auth_token=token); assert any(row['round_id']==integrity_state['crown_and_anchor_rounds'][expected['player_id']] for row in crown_state['recent_rounds'])
                # Read and verify this user's settled Over/Under 7 play after the real process restart.
                ou7_state=api(base,'/api/v1/games/over-under-7/state',auth_token=token); assert any(row['round_id']==integrity_state['over_under_7_rounds'][expected['player_id']] for row in ou7_state['state']['recent_rounds'])
                # Read and verify this user's settled Plinko drop after the real process restart.
                plinko_state=api(base,'/api/v1/games/plinko/state',auth_token=token); assert any(row['drop_id']==integrity_state['plinko_drops'][expected['player_id']] for row in plinko_state['state']['recent_drops'])
                # Read and verify this user's settled Fan-Tan round after the real process restart.
                fan_tan_state=api(base,'/api/v1/games/fan-tan/state',auth_token=token); assert any(row['round_id']==integrity_state['fan_tan_rounds'][expected['player_id']] for row in fan_tan_state['state']['recent_rounds'])
                # Read and verify this user's settled Andar Bahar round after the real process restart.
                andar_bahar_state=api(base,'/api/v1/games/andar-bahar/state',auth_token=token); assert any(row['round_id']==integrity_state['andar_bahar_rounds'][expected['player_id']] for row in andar_bahar_state['state']['recent_rounds'])
                # Read and verify this user's settled Acey-Deucey round after the real process restart.
                acey_deucey_state=api(base,'/api/v1/games/acey-deucey/state',auth_token=token); assert any(row['round_id']==integrity_state['acey_deucey_rounds'][expected['player_id']] for row in acey_deucey_state['state']['recent_rounds'])
                # Read and verify this user's settled Caribbean Stud round after the real process restart.
                caribbean_state=api(base,'/api/v1/games/caribbean-stud/state',auth_token=token); assert any(row['round_id']==integrity_state['caribbean_stud_rounds'][expected['player_id']] for row in caribbean_state['state']['recent_rounds'])
                # Read and verify this user's settled Let It Ride round after the real process restart.
                let_it_ride_state=api(base,'/api/v1/games/let-it-ride/state',auth_token=token); assert any(row['round_id']==integrity_state['let_it_ride_rounds'][expected['player_id']] for row in let_it_ride_state['state']['rounds'])
                # Read and verify this user's settled Casino Hold'em round after the real process restart.
                casino_holdem_state=api(base,'/api/v1/games/casino-holdem/state',auth_token=token); assert any(row['round_id']==integrity_state['casino_holdem_rounds'][expected['player_id']] for row in casino_holdem_state['state']['recent_rounds'])
                # Read and verify this user's settled Pai Gow Poker round after the real process restart.
                pai_gow_poker_state=api(base,'/api/v1/games/pai-gow-poker/state',auth_token=token); assert any(row['round_id']==integrity_state['pai_gow_poker_rounds'][expected['player_id']] for row in pai_gow_poker_state['state']['recent_rounds'])
                # Read and verify this user's settled Joker Poker hand after the real process restart.
                joker_poker_state=api(base,'/api/v1/games/joker-poker/state',auth_token=token); assert any(row['round_id']==integrity_state['joker_poker_rounds'][expected['player_id']] for row in joker_poker_state['state']['recent_rounds'])
                # Read and verify this user's settled Texas Hold'em hand after the real process restart.
                thpt_state=api(base,'/api/v1/games/texas-holdem-practice-table/state',auth_token=token); assert any(row['hand_id']==integrity_state['texas_holdem_practice_hands'][expected['player_id']] for row in thpt_state['state']['recent_hands'])
                # Read restarted private history and ledger views.
                restarted_history=api(base,'/api/v1/casino/history',auth_token=token)['history']; restarted_ledger=api(base,f'/api/v1/players/{expected["player_id"]}/ledger',auth_token=token)['ledger']
                # Match the restarted user's private history against the competitive Bingo outcome owner. (issue #405)
                bingo_history_visible=any(row['round_id']==expected['bingo_session'] for row in restarted_history)
                # Require human-owned refunds/wins/no-win outcomes to persist, while bot wins stay absent from another user's private history.
                assert bingo_history_visible is expected['bingo_history_owned'] and all(row['player_id']==expected['player_id'] for row in restarted_history) and all(row['player_id']==expected['player_id'] for row in restarted_ledger)
            # Verify both users produced persisted private history across the history-producing games.
            assert all(count>0 for count in integrity_state['history_game_counts'])
        # Define the core function used by this module.
        def core():
            # Load the casino state that publishes packaged and game-module version metadata.
            state=api(base,'/api/v1/casino/state')
            # Preserve the existing core assertions for configured games and visible bot players.
            assert any(game['id']=='roulette' for game in state['games']) and any(player['player_id']=='bot_1' for player in state['players'])
            # Require the public runtime version to match the canonical packaged application release.
            assert state['version']==VERSION_MANIFEST['application']
            # Build expected game revisions from configured games and canonical module metadata.
            expected_game_revisions={game['id']:VERSION_MANIFEST['modules'][game['id']] for game in casino_config.GAMES}
            # Require every published game revision to match the canonical module manifest exactly.
            assert {game['id']:game['revision'] for game in state['games']}==expected_game_revisions

        # Define catalog_foundation to prove every integration surface discovers the same games.
        def catalog_foundation():
            # Load the additive public catalog response through the frozen v1 envelope.
            response=api(base,'/api/v1/casino/games')
            # Compare exact ordered ids with the runtime descriptors used for backend registration.
            expected_ids=[game['id'] for game in casino_config.GAMES]
            # Require current and target counts to remain explicit for the 20-game expansion.
            assert [game['id'] for game in response['games']]==expected_ids and response['catalog']=={'current_game_count':len(expected_ids),'target_game_count':20}
            # Require public frontend routes while keeping backend and test import paths internal.
            assert all(game['route']==f"/games/{game['id']}" and game['frontend']['module'] and 'backend' not in game and 'tests' not in game for game in response['games'])
            # Resolve every independently owned long-suite driver from catalog metadata.
            for game in casino_config.GAMES:
                # Split the module-owned test reference into its import and callable names.
                module_name,callable_name=game['tests']['long_driver'].split(':',1)
                # Require each discovered driver to expose the documented callable.
                assert callable(getattr(importlib.import_module(module_name),callable_name))
            # Prove a malicious payload cannot override a normal authenticated session binding.
            assert resolve_authenticated_player({'bound_player_id':'session-player','user':{'player_id':'session-player'}},{'player_id':'other-player'},{'player_id':'third-player'})=='session-player'
            # Prove Admin-compatible explicit resolution remains available without a normal-user binding.
            assert resolve_authenticated_player({'user':{'role':'admin'}},{'player_id':'human'},{})=='human'

        # Define the bots_audio_autoplay function used by this module.
        def bots_audio_autoplay():
            # Set bots to the value needed for the next operation.
            bots=api(base,'/api/v1/bots'); assert bots['bots']; assert bots['capabilities']['roulette']['supports_bots']; assert len(bots['practice_opponents'])==3
            # Reconcile every server-managed practice account after the game-owned API has already exercised fixed funding.
            funded=api(base,'/api/v1/admin/bots/practice-opponents/fund','POST',{'game_id':'texas_holdem_practice_table'}); assert len(funded['funding'])==3 and all(row['replayed'] is True for row in funded['funding'])
            # Replay fixed funding and require the original ledger events without another credit.
            funded_replay=api(base,'/api/v1/admin/bots/practice-opponents/fund','POST',{'game_id':'texas_holdem_practice_table'}); assert all(row['replayed'] is True for row in funded_replay['funding']) and len(funded_replay['practice_opponent_activity'])>=3
            # Verify the dedicated Admin inspection endpoint publishes allocation and ledger audit rows.
            admin_bots=api(base,'/api/v1/admin/bots'); assert len(admin_bots['practice_opponents'])==3 and len(admin_bots['practice_opponent_activity'])>=3
            # Set elig to the value needed for the next operation.
            elig=api(base,'/api/v1/games/roulette/eligible-bots'); assert isinstance(elig['bots'], list)
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/bots/bot_1/strategy','POST',{'game_id':'roulette','strategy_id':'roulette_random_number','stake':7})
            # Set aud to the value needed for the next operation.
            aud=api(base,'/api/v1/admin/audio-settings'); assert 'master_enabled' in aud['settings']
            # Set aud2 to the value needed for the next operation.
            aud2=api(base,'/api/v1/admin/audio-settings','POST',{'master_enabled':False,'voice_enabled':True}); assert aud2['settings']['master_enabled'] is False and aud2['settings']['voice_enabled'] is True
            # Set sess to the value needed for the next operation.
            sess=api(base,'/api/v1/autoplay/start','POST',{'game_id':'roulette','player_id':'human','speed':'medium','round_limit':3,'plan':{'type':'test'}})['session']; assert sess['status']=='running'
            # Set stopped to the value needed for the next operation.
            stopped=api(base,'/api/v1/autoplay/stop','POST',{'autoplay_id':sess['autoplay_id']})['session']; assert stopped['stop_requested'] is True
            assert api(base,'/api/v1/admin/autoplay')['sessions']
        # Delegate the exact post-restart registration block while retaining every callback and lifecycle seam here.
        api_post_restart_foundation.run_cases(run_case,wallet_restart_persistence,core,catalog_foundation,lambda: game_economics_registry_tests.validate_registry(game_economics_registry_tests.read_json(game_economics_registry_tests.REGISTRY_PATH)),validate_i18n_resources,bots_audio_autoplay)
        # Define the roulette function used by this module.
        def roulette():
            # Set p0 to the value needed for the next operation.
            p0=api(base,'/api/v1/players/human')['player']['balance']
            # Set r to the value needed for the next operation.
            r=api(base,'/api/v1/games/roulette/bets','POST',{'player_id':'human','amount':25,'bet_type':'split','covered_numbers':['17','20']}); assert r['bet']['type']=='split'
            # Set p1 to the value needed for the next operation.
            p1=api(base,'/api/v1/players/human')['player']['balance']; assert round(p0-p1,2)==25
            # Attempt to force a result and require the server to return one legal wheel outcome.
            spin=api(base,'/api/v1/games/roulette/spin','POST',{'force_result':'17'}); p2=api(base,'/api/v1/players/human')['player']['balance']; assert str(spin['round']['result']) in {str(number) for number in range(37)}|{'00'} and p2>=0
            # Set rb to the value needed for the next operation.
            rb=api(base,'/api/v1/games/roulette/rebet','POST',{'player_id':'human'}); assert rb['placed']
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/games/roulette/settings','POST',{'zero_rule':'en_prison'})
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/games/roulette/bets','POST',{'player_id':'human','amount':10,'bet_type':'red','covered_numbers':['1','3','5','7','9','12','14','16','18','19','21','23','25','27','30','32','34','36']})
            # Attempt another forced result and require server-owned settlement plus persisted rules.
            spin=api(base,'/api/v1/games/roulette/spin','POST',{'force_result':'0'}); st=api(base,'/api/v1/games/roulette/state')['state']; assert str(spin['round']['result']) in {str(number) for number in range(37)}|{'00'} and st['zero_rule']=='en_prison'
        # Define the slots function used by this module.
        def slots():
            # Set s to the value needed for the next operation.
            s=api(base,'/api/v1/games/slots/spin','POST',{'player_id':'human','active_lines':20,'line_bet':1}); assert len(s['spin']['grid'])==3; assert s['spin']['cost'] in (0,20); assert 'paytable' in s['config']
        # Define the blackjack function used by this module.
        def blackjack():
            # Reset before proving one successful centrally coerced settings response.
            api(base,'/api/v1/casino/reset','POST',{})
            # Recreate the default authenticated player after the reset boundary.
            login_default_user(base)
            # Publish one declared setting through the frozen v1 route.
            settings_result=api(base,'/api/v1/games/blackjack/settings','POST',{'decks':8})
            # Require the established response envelope and canonical coerced integer.
            assert set(settings_result)=={'game','state','player','players'} and set(settings_result['state'])=={'rules','shoe_count','rounds'} and settings_result['game']=='blackjack' and settings_result['state']['rules']['decks']==8
            # Deal until the random cards produce a round that remains active; natural
            # blackjack can auto-settle correctly, so the active-round protection test
            # must not depend on a single random hand.
            # Set rid to the value needed for the next operation.
            rid=None
            for _ in range(20):
                # Call an asynchronous API/helper and wait for the result before continuing.
                api(base,'/api/v1/casino/reset','POST',{})
                # Call an asynchronous API/helper and wait for the result before continuing.
                login_default_user(base)
                # Set bj to the value needed for the next operation.
                bj=api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':'human','bet_amount':10}); rid=bj['round']['round_id']; assert rid
                if bj['round']['status']=='player_turn':
                    break
            # Handle the fallback branch when prior conditions did not match.
            else:
                # Raise an error so invalid input or state is reported explicitly.
                raise AssertionError('could not create active blackjack round for test')
            # Set api(base,'/api/v1/games/blackjack/settings','POST',{'decks': to the value needed for the next operation.
            api(base,'/api/v1/games/blackjack/settings','POST',{'decks':8},ok=False)
            # Set api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id to the value needed for the next operation.
            api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':'human','bet_amount':10},ok=False)
        # Define blackjack_insurance_phase_guard to prove revealed rounds cannot mutate the wallet through insurance.
        def blackjack_insurance_phase_guard():
            # Start from the canonical table rules so the persisted fixture remains compatible with the public state endpoint.
            insurance_state=blackjack_engine.default_state()
            # Build a completed dealer-natural round whose result and hole card are already public.
            settled_round={'round_id':'bj_insurance_settled','player_id':'human','status':'settled','dealer':{'cards':['AS','KH'],'hole_card_hidden':False},'hands':[{'hand_id':'hand_insurance_settled','cards':['9C','8D'],'bet':10,'status':'loss','outcome':'dealer_blackjack','payout_due':0,'credited':True,'actions':[]}],'active_hand_index':0,'insurance':None,'even_money':None,'settlements':[]}
            # Build a defensive exposed-player-turn fixture so the hole-card predicate is tested independently of status.
            exposed_turn_round={'round_id':'bj_insurance_exposed_turn','player_id':'human','status':'player_turn','dealer':{'cards':['AS','QH'],'hole_card_hidden':False},'hands':[{'hand_id':'hand_insurance_exposed_turn','cards':['9S','7D'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'insurance':None,'even_money':None,'settlements':[]}
            # Build a legal hidden-hole dealer-Ace control so the new guard cannot disable valid insurance.
            legal_round={'round_id':'bj_insurance_legal','player_id':'human','status':'player_turn','dealer':{'cards':['AS','9H'],'hole_card_hidden':True},'hands':[{'hand_id':'hand_insurance_legal','cards':['8S','7C'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'insurance':None,'even_money':None,'settlements':[]}
            # Persist all deterministic fixtures through the production game-state provider before exercising real HTTP routes.
            insurance_state['rounds']={settled_round['round_id']:settled_round,exposed_turn_round['round_id']:exposed_turn_round,legal_round['round_id']:legal_round}; save_player_game_state('blackjack','human',insurance_state)
            # Snapshot the authoritative player balance and ledger before either rejected request.
            balance_before=api(base,'/api/v1/players/human')['player']['balance']; ledger_before=api(base,'/api/v1/players/human/ledger')['ledger']
            # Attempt insurance after completed settlement and require the standard conflict envelope.
            settled_rejection=api(base,f"/api/v1/games/blackjack/rounds/{settled_round['round_id']}/insurance",'POST',{'player_id':'human','amount':5},ok=False)
            # Attempt insurance while the status claims player turn but the dealer hole card is already exposed.
            exposed_rejection=api(base,f"/api/v1/games/blackjack/rounds/{exposed_turn_round['round_id']}/insurance",'POST',{'player_id':'human','amount':5},ok=False)
            # Read back every authoritative surface after both rejected mutation attempts.
            balance_after=api(base,'/api/v1/players/human')['player']['balance']; ledger_after=api(base,'/api/v1/players/human/ledger')['ledger']; state_after=api(base,'/api/v1/games/blackjack/state')['state']
            # Require both phase violations to be conflicts without any balance or append-only ledger mutation.
            assert settled_rejection['error']['code']=='CONFLICT' and exposed_rejection['error']['code']=='CONFLICT' and balance_after==balance_before and len(ledger_after)==len(ledger_before)
            # Require both persisted rounds to remain free of insurance after the hostile requests.
            assert state_after['rounds'][settled_round['round_id']]['insurance'] is None and state_after['rounds'][exposed_turn_round['round_id']]['insurance'] is None
            # Purchase legal insurance through the same public endpoint after proving both rejected attempts were inert.
            legal_result=api(base,f"/api/v1/games/blackjack/rounds/{legal_round['round_id']}/insurance",'POST',{'player_id':'human','amount':5})
            # Read the authoritative wallet and ledger after the legal non-winning insurance debit.
            legal_balance=api(base,'/api/v1/players/human')['player']['balance']; legal_ledger=api(base,'/api/v1/players/human/ledger')['ledger']
            # Require the valid dealer-Ace path to retain its historical one-debit behavior and persisted insurance state.
            assert legal_result['round']['insurance']['amount']==5 and legal_balance==balance_before-5 and len(legal_ledger)==len(ledger_before)+1
        # Execute the insurance phase regression under the game, ledger, and API-test requirements.
        # Define the blackjack_state_with_shoe function used by this module.
        def blackjack_state_with_shoe(*cards):
            # Set state to the default blackjack state for deterministic rule checks.
            state=blackjack_engine.default_state()
            # Set state["shoe"] to enough filler cards plus controlled draw cards.
            state["shoe"]=['2S']*52+list(cards)
            # Return the prepared state to the caller.
            return state
        # Define the blackjack_rule_edges function used by this module.
        def blackjack_rule_edges():
            # Set hidden_round to a public-round fixture with a dealer hole card.
            hidden_round={'dealer':{'cards':['AS','9H'],'hole_card_hidden':True},'hands':[]}
            # Set exposed to the value returned by the public blackjack serializer.
            exposed=blackjack_api.exposed_round(hidden_round); assert exposed['dealer']['cards']==['AS','??']
            # Set ace_total to the computed value for a multi-ace soft hand.
            ace_total=blackjack_engine.hand_total(['AS','AH','9D']); assert ace_total['total']==21 and ace_total['soft']
            # Set hard_ace_total to the computed value once all aces must be hard.
            hard_ace_total=blackjack_engine.hand_total(['AS','AH','9D','KC']); assert hard_ace_total['total']==21 and not hard_ace_total['soft']
            # Set natural_state to a shoe that gives the player a natural blackjack.
            natural_state=blackjack_state_with_shoe('8C','9D','KH','AS')
            # Set natural_round to the auto-settled natural blackjack round.
            natural_round=blackjack_engine.new_round(natural_state,'human',10); assert natural_round['hands'][0]['payout_due']==25
            # Verify the controlled shoe persisted and lost exactly the dealt cards.
            assert len(natural_state['shoe'])==52
            # Set push_state to a shoe that gives both player and dealer blackjacks.
            push_state=blackjack_state_with_shoe('QH','AD','KH','AS')
            # Set push_round to the auto-settled push blackjack round.
            push_round=blackjack_engine.new_round(push_state,'human',10); assert push_round['hands'][0]['payout_due']==10
            # Build the deferred-natural path offered even money against a dealer Ace and non-natural twenty.
            deferred_state=blackjack_state_with_shoe('9D','AS','KH','AS')
            # Deal the controlled natural and require settlement to remain deferred for the visible choice.
            deferred_round=blackjack_engine.new_round(deferred_state,'human',10); assert deferred_round['status']=='player_turn' and deferred_round['hands'][0]['status']=='active'
            # Decline even money through Stand and require the configured three-to-two return.
            blackjack_engine.stand(deferred_state,deferred_round['round_id']); assert deferred_round['hands'][0]['status']=='blackjack' and deferred_round['hands'][0]['outcome']=='blackjack' and deferred_round['hands'][0]['payout_due']==25
            # Start protected logic so a repeated settlement action cannot create another return.
            try: blackjack_engine.stand(deferred_state,deferred_round['round_id']); raise AssertionError('settled natural accepted a repeated stand')
            # Require the settled hand to reject another player action.
            except Exception as exc: assert 'player turn' in str(exc).lower()
            # Build a dealer draw to a multi-card twenty-one after the player receives a natural.
            dealer_twenty_one_state=blackjack_state_with_shoe('5C','5D','AS','KH','AS')
            # Decline even money and prove a two-card natural beats the dealer's three-card twenty-one.
            dealer_twenty_one_round=blackjack_engine.new_round(dealer_twenty_one_state,'human',10); blackjack_engine.stand(dealer_twenty_one_state,dealer_twenty_one_round['round_id']); assert len(dealer_twenty_one_round['dealer']['cards'])==3 and blackjack_engine.hand_total(dealer_twenty_one_round['dealer']['cards'])['total']==21 and dealer_twenty_one_round['hands'][0]['payout_due']==25
            # Build a dealer path that must draw twice and bust after the deferred natural.
            dealer_bust_state=blackjack_state_with_shoe('10H','KC','5D','AS','KH','AS')
            # Require the same configured natural return when the dealer ultimately busts.
            dealer_bust_round=blackjack_engine.new_round(dealer_bust_state,'human',10); blackjack_engine.stand(dealer_bust_state,dealer_bust_round['round_id']); assert blackjack_engine.hand_total(dealer_bust_round['dealer']['cards'])['bust'] and dealer_bust_round['hands'][0]['payout_due']==25
            # Configure the compatible six-to-five table rate on another deferred natural.
            custom_payout_state=blackjack_state_with_shoe('9D','AS','KH','AS'); custom_payout_state['rules']['blackjack_payout']=1.2
            # Require the declined-even-money path to honor the configured rate instead of hard-coding three-to-two.
            custom_payout_round=blackjack_engine.new_round(custom_payout_state,'human',10); blackjack_engine.stand(custom_payout_state,custom_payout_round['round_id']); assert custom_payout_round['hands'][0]['payout_due']==22
            # Build an ordinary three-card twenty-one against a dealer three-card twenty-one.
            ordinary_twenty_one_state=blackjack_state_with_shoe('5C')
            # Store the non-natural hand directly so total-comparison push behavior remains covered.
            ordinary_twenty_one_round={'dealer':{'cards':['AS','5D'],'hole_card_hidden':True},'hands':[{'cards':['10H','5S','6C'],'bet':10,'status':'stand'}],'status':'player_turn'}
            # Require ordinary equal totals to remain a push rather than receiving the natural bonus.
            blackjack_engine.dealer_play(ordinary_twenty_one_state,ordinary_twenty_one_round); assert ordinary_twenty_one_round['hands'][0]['outcome']=='push' and ordinary_twenty_one_round['hands'][0]['payout_due']==10
            # Build a two-card twenty-one marked as a split hand against dealer twenty.
            split_twenty_one_state=blackjack_state_with_shoe('5C')
            # Store the split identity explicitly so it cannot receive the natural payout.
            split_twenty_one_round={'dealer':{'cards':['10S','QH'],'hole_card_hidden':True},'hands':[{'cards':['AS','KH'],'bet':10,'status':'stand','is_split_hand':True}],'status':'player_turn'}
            # Require split twenty-one to settle as an ordinary even-money win.
            blackjack_engine.dealer_play(split_twenty_one_state,split_twenty_one_round); assert split_twenty_one_round['hands'][0]['status']=='settled' and split_twenty_one_round['hands'][0]['outcome']=='win' and split_twenty_one_round['hands'][0]['payout_due']==20
            # Set soft17_state to a table where the dealer must hit soft 17.
            soft17_state=blackjack_state_with_shoe('2C')
            # Set soft17_state rules so dealer soft 17 requires another card.
            soft17_state['rules']['dealer_hits_soft_17']=True
            # Set soft17_round to a settled player hand against dealer soft 17.
            soft17_round={'dealer':{'cards':['AS','6D'],'hole_card_hidden':True},'hands':[{'cards':['10C','7S'],'bet':10,'status':'stand'}],'status':'player_turn'}
            # Execute dealer play and verify a soft-17 hit occurred.
            blackjack_engine.dealer_play(soft17_state,soft17_round); assert len(soft17_round['dealer']['cards'])==3
            # Set double_state to a shoe that lets double down draw exactly one card.
            double_state=blackjack_state_with_shoe('4H')
            # Set double_round to a legal two-card hand with a standing dealer total.
            double_round={'round_id':'bj_double','player_id':'human','dealer':{'cards':['10C','8D'],'hole_card_hidden':True},'hands':[{'hand_id':'hand_double','cards':['5S','6H'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'status':'player_turn'}
            # Store the double round so the engine can look it up by round id.
            double_state['rounds']={'bj_double':double_round}
            # Execute double down and verify one card, doubled bet, and action state.
            blackjack_engine.double_down(double_state,'bj_double'); assert len(double_round['hands'][0]['cards'])==3 and double_round['hands'][0]['bet']==20 and 'double' in double_round['hands'][0]['actions']
            # Set split_limit_state to a table where no additional split hand is allowed.
            split_limit_state=blackjack_state_with_shoe('3C','4D')
            # Set the split limit to one hand so the existing hand already reaches it.
            split_limit_state['rules']['max_split_hands']=1
            # Store a splittable round that should be rejected by the split limit.
            split_limit_state['rounds']={'bj_split_limit':{'round_id':'bj_split_limit','player_id':'human','dealer':{'cards':['10C','8D'],'hole_card_hidden':True},'hands':[{'hand_id':'hand_split_limit','cards':['8S','8H'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'status':'player_turn'}}
            # Start protected logic so the expected split-limit rejection can be asserted.
            try: blackjack_engine.split(split_limit_state,'bj_split_limit'); raise AssertionError('split limit was not enforced')
            # Handle the expected split-limit rejection.
            except Exception as exc: assert 'Maximum split hands' in str(exc)
            # Set das_state to a table where double after split is disabled.
            das_state=blackjack_engine.default_state()
            # Disable double-after-split for the next helper assertion.
            das_state['rules']['double_after_split']=False
            # Verify a split hand cannot double when the table rule disables it.
            assert not blackjack_engine.can_double(das_state,{'cards':['8S','3C'],'is_split_hand':True,'actions':['split']})
            # Set split_aces_state to a shoe that creates one-card split ace hands.
            split_aces_state=blackjack_state_with_shoe('5C','6D')
            # Store a splittable ace pair for the one-card split rule.
            split_aces_state['rounds']={'bj_split_aces':{'round_id':'bj_split_aces','player_id':'human','dealer':{'cards':['10C','8D'],'hole_card_hidden':True},'hands':[{'hand_id':'hand_ace','cards':['AS','AH'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'status':'player_turn'}}
            # Execute the ace split and verify both hands are locked after one drawn card.
            ace_round=blackjack_engine.split(split_aces_state,'bj_split_aces'); assert all(h.get('split_aces_locked') and len(h['cards'])==2 for h in ace_round['hands'])
            # Set surrender_off_state to a table that disables late surrender.
            surrender_off_state=blackjack_state_with_shoe()
            # Disable late surrender for the rejection assertion.
            surrender_off_state['rules']['late_surrender']=False
            # Store a surrenderable round that should be rejected by table rules.
            surrender_off_state['rounds']={'bj_surrender_off':{'round_id':'bj_surrender_off','player_id':'human','dealer':{'cards':['10C','8D'],'hole_card_hidden':True},'hands':[{'hand_id':'hand_surrender_off','cards':['9S','7H'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'status':'player_turn'}}
            # Start protected logic so disabled surrender can be asserted.
            try: blackjack_engine.surrender(surrender_off_state,'bj_surrender_off'); raise AssertionError('disabled surrender was not rejected')
            # Handle the expected disabled-surrender rejection.
            except Exception as exc: assert 'Surrender is disabled' in str(exc)
            # Set surrender_state to a normal table with a surrenderable hand.
            surrender_state=blackjack_state_with_shoe()
            # Store the surrenderable round for the payout assertion.
            surrender_state['rounds']={'bj_surrender':{'round_id':'bj_surrender','player_id':'human','dealer':{'cards':['10C','8D'],'hole_card_hidden':True},'hands':[{'hand_id':'hand_surrender','cards':['9S','7H'],'bet':10,'status':'active','actions':[]}],'active_hand_index':0,'status':'player_turn'}}
            # Execute surrender and verify half the wager is due back.
            surrender_round=blackjack_engine.surrender(surrender_state,'bj_surrender'); assert surrender_round['hands'][0]['payout_due']==5
        # Define the baccarat function used by this module.
        def baccarat():
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/casino/reset','POST',{})
            # Call an asynchronous API/helper and wait for the result before continuing.
            login_default_user(base)
            # Set api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':' to the value needed for the next operation.
            api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':'human','amount':10,'bet_type':'banker'}); d=api(base,'/api/v1/games/baccarat/deal','POST',{}); assert d['coup']['player_cards'] and d['coup']['banker_cards']; assert d['bot_bets'] is not None
        # Define the keno function used by this module.
        def keno():
            # Set p to the value needed for the next operation.
            p=api(base,'/api/v1/games/keno/state')['paytable']; assert set(map(int,p.keys()))==set(range(1,21))
            # Set api(base,'/api/v1/games/keno/tickets','POST',{'player_id':'h to the value needed for the next operation.
            api(base,'/api/v1/games/keno/tickets','POST',{'player_id':'human','amount':5,'spots':[1,2,3]}); d=api(base,'/api/v1/games/keno/draw','POST',{}); assert len(d['draw']['drawn'])==20
        # Define the bingo function used by this module.
        def bingo():
            # Set api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'hu to the value needed for the next operation.
            api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'human','amount':5,'pattern':'line'}); r=api(base,'/api/v1/games/bingo/reset','POST',{}); assert r['refunds']
            # Require a terminal competitive settlement rather than the removed guaranteed human win. (issue #405)
            api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'human','amount':5,'pattern':'line'}); a=api(base,'/api/v1/games/bingo/auto','POST',{'max_calls':75}); assert a['session']['status'] in ('won','no_win')
        # Define the private_sessions function used by this module.
        def private_sessions():
            # Reset state so the multi-player isolation evidence is not mixed with earlier cases.
            api(base,'/api/v1/casino/reset','POST',{})
            # Re-login after reset because reset reseeds auth/session state.
            login_default_user(base)
            # Create the first human account used by the private-session scenario.
            user_a=api(base,'/api/v1/players','POST',{'display_name':'Private A','type':'human','balance':5000})['player']['player_id']
            # Create the second human account used by the private-session scenario.
            user_b=api(base,'/api/v1/players','POST',{'display_name':'Private B','type':'human','balance':5000})['player']['player_id']
            # Place an open Roulette bet for user A.
            rou_a=api(base,'/api/v1/games/roulette/bets','POST',{'player_id':user_a,'amount':10,'bet_type':'red','covered_numbers':['1','3','5','7','9','12','14','16','18','19','21','23','25','27','30','32','34','36']})['bet']['bet_id']
            # Verify user B does not see user A's Roulette bet.
            assert not api(base,f'/api/v1/games/roulette/state?player_id={user_b}')['state']['open_round']['bets']
            # Place and settle a separate Roulette bet for user B.
            api(base,'/api/v1/games/roulette/bets','POST',{'player_id':user_b,'amount':5,'bet_type':'straight','covered_numbers':['17'],'label':'17'})
            # Settle only user B's Roulette state.
            api(base,'/api/v1/games/roulette/spin','POST',{'player_id':user_b,'force_result':'17'})
            # Verify user A's Roulette bet remains open in user A's state.
            assert api(base,f'/api/v1/games/roulette/state?player_id={user_a}')['state']['open_round']['bets'][0]['bet_id']==rou_a
            # Spin Slots once for user A.
            slot_a=api(base,'/api/v1/games/slots/spin','POST',{'player_id':user_a,'active_lines':1,'line_bet':1})['spin']['round_id']
            # Spin Slots once for user B.
            slot_b=api(base,'/api/v1/games/slots/spin','POST',{'player_id':user_b,'active_lines':3,'line_bet':1})['spin']['round_id']
            # Verify each user sees only their own Slots spin history.
            assert api(base,f'/api/v1/games/slots/state?player_id={user_a}')['state']['last_spins'][-1]['round_id']==slot_a
            # Verify user B's Slots state is separate from user A's.
            assert api(base,f'/api/v1/games/slots/state?player_id={user_b}')['state']['last_spins'][-1]['round_id']==slot_b
            # Deal one Blackjack round for user A.
            bj_a=api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':user_a,'bet_amount':10})['round']['round_id']
            # Deal one Blackjack round for user B.
            bj_b=api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':user_b,'bet_amount':10})['round']['round_id']
            # Verify user A sees only user A's Blackjack round.
            assert bj_a in api(base,f'/api/v1/games/blackjack/state?player_id={user_a}')['state']['rounds']
            # Verify user B sees only user B's Blackjack round.
            assert bj_b in api(base,f'/api/v1/games/blackjack/state?player_id={user_b}')['state']['rounds']
            # Place a Baccarat bet for user A and leave it open.
            bac_a=api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':user_a,'amount':10,'bet_type':'banker'})['bet']['bet_id']
            # Verify user B does not see user A's Baccarat bet.
            assert not api(base,f'/api/v1/games/baccarat/state?player_id={user_b}')['state']['open_bets']
            # Place and settle a separate Baccarat coup for user B.
            api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':user_b,'amount':10,'bet_type':'player'})
            # Deal only user B's Baccarat state.
            api(base,'/api/v1/games/baccarat/deal','POST',{'player_id':user_b})
            # Verify user A's Baccarat bet remains open.
            assert api(base,f'/api/v1/games/baccarat/state?player_id={user_a}')['state']['open_bets'][0]['bet_id']==bac_a
            # Buy a Keno ticket for user A and leave it open.
            keno_a=api(base,'/api/v1/games/keno/tickets','POST',{'player_id':user_a,'amount':5,'spots':[1,2,3]})['ticket']['ticket_id']
            # Verify user B does not see user A's Keno ticket.
            assert not api(base,f'/api/v1/games/keno/state?player_id={user_b}')['state']['open_tickets']
            # Buy and draw a separate Keno ticket for user B.
            api(base,'/api/v1/games/keno/tickets','POST',{'player_id':user_b,'amount':5,'spots':[4,5,6]})
            # Draw only user B's Keno state.
            api(base,'/api/v1/games/keno/draw','POST',{'player_id':user_b})
            # Verify user A's Keno ticket remains open.
            assert api(base,f'/api/v1/games/keno/state?player_id={user_a}')['state']['open_tickets'][0]['ticket_id']==keno_a
            # Buy a Bingo card for user A and leave the session active.
            bingo_a=api(base,'/api/v1/games/bingo/cards','POST',{'player_id':user_a,'amount':5,'pattern':'line'})['session']['session_id']
            # Verify user B does not see user A's Bingo session.
            assert api(base,f'/api/v1/games/bingo/state?player_id={user_b}')['state']['active_session'] is None
            # Buy and reset a separate Bingo session for user B.
            api(base,'/api/v1/games/bingo/cards','POST',{'player_id':user_b,'amount':5,'pattern':'line'})
            # Reset only user B's Bingo state.
            api(base,'/api/v1/games/bingo/reset','POST',{'player_id':user_b})
            # Verify user A's Bingo session remains active.
            assert api(base,f'/api/v1/games/bingo/state?player_id={user_a}')['state']['active_session']['session_id']==bingo_a
            # Read user A's ledger rows after multi-game play.
            ledger_a=api(base,f'/api/v1/players/{user_a}/ledger')['ledger']
            # Read user B's ledger rows after multi-game play.
            ledger_b=api(base,f'/api/v1/players/{user_b}/ledger')['ledger']
            # Verify each ledger view contains only the requested player id.
            assert ledger_a and all(row['player_id']==user_a for row in ledger_a)
            # Verify user B ledger view contains only user B rows.
            assert ledger_b and all(row['player_id']==user_b for row in ledger_b)
        # Define the admin function used by this module.
        def admin():
            # Load the Admin overview that publishes packaged release and module revision metadata.
            overview=api(base,'/api/v1/admin/overview')
            # Require Admin's packaged release to match the canonical top-level application version.
            assert overview['app_version']==VERSION_MANIFEST['application']
            # Require Admin overview module revisions to match exact canonical order and values.
            assert overview['module_revisions']==EXPECTED_MODULE_ROWS
            # Require the dedicated module endpoint to publish the same canonical rows.
            assert api(base,'/api/v1/admin/modules')['modules']==EXPECTED_MODULE_ROWS
            # Set r to the value needed for the next operation.
            r=api(base,'/api/v1/admin/requirements'); assert len(r['requirements'])>100
            # Set l to the value needed for the next operation.
            l=api(base,'/api/v1/admin/logs?kind=app&limit=10'); assert isinstance(l['logs'],list)
            # Set created to the Admin-created beta user with ledger-backed starting tokens.
            created=api(base,'/api/v1/admin/users','POST',{'email':'beta.api@example.test','display_name':'Beta API','initial_tokens':1234,'terms_accepted':False,'language':'ru-RU','format_locale':'browser'}); assert created['user']['token_balance']==1234
            # Set user_id to the durable Admin user id for follow-up operations.
            user_id=created['user']['user_id']; assert created['temporary_password']
            # Verify the created user's terms and locale state are visible.
            assert created['user']['terms_status']=='pending' and created['user']['language']=='ru-RU'
            # Set listed to the Admin user listing with token state inspection.
            listed=api(base,'/api/v1/admin/users'); assert any(u['user_id']==user_id and u['token_state']=='active' for u in listed['users'])
            # Set deactivated to the user after Admin deactivation.
            deactivated=api(base,f'/api/v1/admin/users/{user_id}/deactivate','POST',{})['user']; assert deactivated['status']=='inactive' and deactivated['token_state']=='inactive'
            # Set reactivated to the user after Admin reactivation.
            reactivated=api(base,f'/api/v1/admin/users/{user_id}/reactivate','POST',{})['user']; assert reactivated['status']=='active' and reactivated['token_state']=='active'
            # Set reset to the user after Admin password reset.
            reset=api(base,f'/api/v1/admin/users/{user_id}/password-reset','POST',{}) ; assert reset['temporary_password'] and reset['user']['password_reset_required'] is True
            # Set terms to the user after Admin marks terms accepted.
            terms=api(base,f'/api/v1/admin/users/{user_id}/terms','POST',{'accepted':True})['user']; assert terms['terms_status']=='accepted'
            # Set localized to the user after Admin preserves account locale settings.
            localized=api(base,f'/api/v1/admin/users/{user_id}/locale','POST',{'language':'en-US','format_locale':'en-US','use_browser_locale':False})['user']; assert localized['language']=='en-US' and localized['format_locale']=='en-US'
        # Delegate the exact core live-game and Admin registrations before runner-owned teardown.
        api_core_live_games.run_cases(run_case,roulette,slots,blackjack,blackjack_insurance_phase_guard,blackjack_rule_edges,baccarat,keno,bingo,private_sessions,admin)
    # Run cleanup logic regardless of success or failure.
    finally:
        # Stop the tracked API child and prove its loopback listener is closed.
        stop_server(proc,base); save_results()

# Define the run_browser_tests function used by this module.
def run_browser_tests(heartbeat_seconds=45.0,stall_seconds=180.0,timeout_seconds=2700.0,shard_count=1,shard_index=0,affected_games=None):
    # Make the active reporter, shard partition, and affected-game selection visible to the shared run_case helper.
    global ACTIVE_PROGRESS,BROWSER_SHARD_CASES,BROWSER_CASE_SEQ,BROWSER_AFFECTED_GAMES
    # Start protected logic so failures can be handled safely.
    try: from playwright.sync_api import TimeoutError as PlaywrightTimeoutError,sync_playwright
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Write diagnostic output so the current operation can be inspected.
        print('Playwright is not installed. Install with python -m pip install -r requirements-dev.txt and python -m playwright install chromium'); return 2
    # Fail before listener startup when any declared producer/consumer affinity crosses a shard.
    validate_browser_shard_affinity(shard_count)
    # Fail before listener startup when the affected-game acceptance map has drifted from the catalog or inventory.
    validate_browser_affected_games()
    # Restrict execution to the requested games' dedicated acceptance cases before partitioning or counting.
    BROWSER_AFFECTED_GAMES=affected_games
    # Compute the strict duration-balanced partition and select this worker's ownership.
    owned_cases=browser_shard_case_sets(shard_count)[shard_index] if shard_count>1 else None
    # Reset source-order accounting so guarded affinity bodies remain verifiable.
    BROWSER_CASE_SEQ=0
    # Activate packed ownership only for real multi-shard runs.
    BROWSER_SHARD_CASES=owned_cases
    # Build one reusable reporter sized to the cases this shard actually executes after affected-game deselection.
    progress=ProgressReporter(len(browser_selected_case_ids(owned_cases)),heartbeat_seconds,stall_seconds,timeout_seconds)
    # Start flushed phase and watchdog output before the ephemeral server starts.
    progress.start('browser-server-startup')
    # Route existing run_case calls through this reporter only for the browser suite.
    ACTIVE_PROGRESS=progress
    # Initialize tracked cleanup state before server startup.
    proc=None; base=None; status='FAIL'
    # Parse the authoritative visual matrix so browser coverage fails fast on invalid governance data.
    visual_matrix=json.loads((ROOT/'tests'/'visual'/'visual_matrix.json').read_text(encoding='utf-8'))
    # Read the canonical packaged version so PWA assertions cannot retain a stale release literal.
    packaged_version=json.loads((ROOT/'modules'/'module-manifest.json').read_text(encoding='utf-8'))['application']
    # Start protected logic so failures can be handled safely.
    try:
        # Start one loopback-only ephemeral server and retain its exact PID and port.
        proc,base=start_server()
        # Register idempotent timeout/finally cleanup after the exact listener is known.
        progress.set_cleanup(lambda: stop_server(proc,base))
        # Transition from startup to the named browser-test phase.
        progress.set_phase('browser-tests')
        # Set screenshots to the existing artifact path without changing uploads.
        screenshots=ROOT/'logs'/'test-runs'; screenshots.mkdir(parents=True,exist_ok=True)
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
        # Preserve the visible terms/locale setup only on the authenticated-session shard.
        auth_session_owner=browser_shard_owns_group('auth_session')
        # Track public Auth ownership because it must also begin before neutral session bootstrap.
        auth_public_owner=browser_shard_owns_group('auth_public')
        # Seed the lobby-only owner at the fractional balance produced by the independent session chain.
        lobby_shell_owner=browser_shard_owns_group('lobby_shell')
        # Keep neutral bootstrap disabled only while an owned visible Auth family requires the anonymous shell.
        visible_auth_owner=auth_public_owner or auth_session_owner
        # Create one deterministic normal user with owner-specific terms, locale, and wallet prerequisites.
        api(base,'/api/v1/admin/users','POST',{'email':'demo@example.local','password':'password','display_name':'Demo Player','initial_tokens':5000 if auth_session_owner or not lobby_shell_owner else 5250.5,'terms_accepted':not auth_session_owner,'language':'ru-RU' if auth_session_owner else 'en-US','format_locale':'browser' if auth_session_owner else 'en-US'})
        # Define the listener-free real browser-helper security contract for permanent browser discovery.
        def browser_security_contract():
            # Execute the focused wrapper with the active interpreter and no credential output.
            result=subprocess.run([sys.executable,'-m','unittest','tests.security.test_browser_contract'],cwd=ROOT,capture_output=True,text=True,timeout=30)
            # Preserve only bounded diagnostic tails if the helper contract fails.
            if result.returncode != 0: raise AssertionError((result.stderr or result.stdout)[-1200:])
        # Record exact CSRF attachment and bearer-omission behavior in the browser suite.
        run_case('BR-SEC-PREVIEW-001',['SEC-010','SESSION-006','ADMIN-024','AUTH-007','TEST-047'],browser_security_contract)
        # Manage this resource with automatic setup and cleanup.
        with sync_playwright() as p:

            # Start protected logic so failures can be handled safely.
            try:
                # Set browser to the value needed for the next operation.
                browser=p.chromium.launch(headless=True)
            # Handle the expected failure path for the protected logic.
            except Exception as exc:
                record('BR-SETUP-001',['TEST-010'],'FAIL','Playwright browser runtime missing or blocked: '+str(exc).split('\n')[0])
                return 2
            # Delegate the complete real-login and PWA producer/consumer affinity group without transferring Browser-process ownership.
            browser_auth_backend_pwa.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser,base,packaged_version,screenshots,ROOT,DEFAULT_AUTH_EMAIL,DEFAULT_AUTH_PASSWORD,PlaywrightTimeoutError)
            # Delegate the complete disposable guest lifecycle family without transferring Browser-process or shared-session ownership.
            browser_guest_lifecycle.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser,base,screenshots,ROOT,read_i18n_json,auth_core,guest_analytics)
            # Refresh the direct API harness Admin session after the browser login added a concurrent session (issue #226).
            login_default_user(base)
            # Set page to the value needed for the next operation.
            page=browser.new_page(viewport={'width':1920,'height':1080})
            # Set console_errors to the value needed for the next operation.
            console_errors=[]; page_errors=[]; http_errors=[]; provider_requests=[]
            # Set page.on('console', lambda msg: console_errors.append(msg.tex to the value needed for the next operation.
            page.on('console', lambda msg: console_errors.append(msg.text) if msg.type=='error' else None)
            page.on('pageerror', lambda err: page_errors.append(str(err)))
            # Capture failing response URLs so authorization regressions are diagnosable.
            page.on('response', lambda response: http_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
            # Record only attempted provider-action traffic so disabled-control assertions remain focused.
            page.on('request', lambda request: provider_requests.append(request.url) if any(marker in request.url for marker in ('/start','/callback','accounts.google.com','facebook.com')) else None)
            # Install an audio probe before navigation so Roulette voice text can be matched to the authoritative result.
            page.add_init_script("window.__casinoAudioEvents=[]; window.__casinoAudioProbe=(event)=>window.__casinoAudioEvents.push(event);")
            # Define the shot function used by this module.
            def shot(name): page.screenshot(path=str(screenshots/name), full_page=True)
            # Define a viewport capture helper for transform-heavy live game motion evidence.
            def viewport_shot(name): page.screenshot(path=str(screenshots/name), full_page=False)
            # Read the current commit once so visual evidence sidecars identify the tested source exactly.
            evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True).strip()
            # Prefer the pull-request branch supplied by CI and fall back to the local symbolic branch name.
            evidence_branch=os.environ.get('GITHUB_HEAD_REF') or subprocess.check_output(['git','branch','--show-current'],cwd=str(ROOT),text=True).strip() or 'detached'
            # Capture a focused catalog artifact with the metadata required by the visual evidence gate.
            def catalog_evidence(name, states, locale, viewport_id):
                # Resolve the PNG target under the standard browser test artifact directory.
                target=screenshots/name
                # Capture only the localized catalog region so unrelated legacy lobby copy cannot obscure acceptance.
                page.get_by_test_id('catalog-region').screenshot(path=str(target),animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                # Record the active viewport dimensions alongside the named visual-matrix viewport.
                viewport=page.viewport_size
                # Record the current focus target so keyboard evidence remains auditable after the run.
                focused=page.evaluate("() => document.activeElement?.getAttribute('data-catalog-category') || document.activeElement?.getAttribute('data-testid') || ''")
                # Build the complete after-pass evidence metadata required by VIS-EVIDENCE-001.
                metadata={'evidence_class':'after_pass','branch':evidence_branch,'commit':evidence_commit,'surface':'shell_lobby','states':states,'locale':locale,'viewport':{'id':viewport_id,**viewport},'path':str(target.relative_to(ROOT)).replace('\\','/'),'focused_control':focused}
                # Write a UTF-8 sidecar next to the image so the evidence remains self-describing.
                target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
            # Capture one game viewport with the complete metadata required by the visual evidence gate.
            def game_evidence(name, surface, states, locale, viewport_id, diagnostics=None):
                # Resolve the PNG target under the standard browser test artifact directory.
                target=screenshots/name
                # Capture the visible shared shell and game stage without transient status overlays.
                page.screenshot(path=str(target),full_page=True,animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                # Record the active viewport dimensions alongside the named visual-matrix viewport.
                viewport=page.viewport_size
                # Record the current focus target for keyboard and hold-selection evidence.
                focused=page.evaluate("() => document.activeElement?.getAttribute('data-testid') || document.activeElement?.getAttribute('data-action') || document.activeElement?.getAttribute('data-hold-position') || ''")
                # Build the complete after-pass evidence metadata required by VIS-EVIDENCE-001.
                metadata={'evidence_class':'after_pass','branch':evidence_branch,'commit':evidence_commit,'surface':surface,'states':states,'locale':locale,'viewport':{'id':viewport_id,**viewport},'path':str(target.relative_to(ROOT)).replace('\\','/'),'focused_control':focused}
                # Attach bounded computed-style diagnostics only when a specialized evidence case supplies them.
                if diagnostics is not None:
                    # Preserve the sanitized semantic values beside their exact-head screenshot.
                    metadata['diagnostics']=diagnostics
                # Write a UTF-8 sidecar next to the image so the evidence remains self-describing.
                target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
            # Capture live wallet motion without fast-forwarding the finite celebration animations. (UX-023)
            def wallet_evidence(name, states, locale, viewport_id):
                # Resolve the PNG target under the standard browser artifact directory.
                target=screenshots/name
                # Capture the complete shell while allowing the changed wallet animation to remain visible.
                page.screenshot(path=str(target),full_page=True,animations='allow',style='#toast, .status-bar { visibility: hidden !important; }')
                # Record the exact active viewport dimensions beside its governed identifier.
                viewport=page.viewport_size
                # Record the current focus target without requiring the transient effect to accept input.
                focused=page.evaluate("() => document.activeElement?.getAttribute('data-testid') || ''")
                # Bind source, state, locale, viewport, path, and focus to the after-pass artifact.
                metadata={'evidence_class':'after_pass','branch':evidence_branch,'commit':evidence_commit,'surface':'shell_lobby','states':states,'locale':locale,'viewport':{'id':viewport_id,**viewport},'path':str(target.relative_to(ROOT)).replace('\\','/'),'focused_control':focused}
                # Write the exact-head metadata next to the live-motion screenshot.
                target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
            # Capture the visible status-footer region together with the exact accepted geometry diagnostics. (UX-016, TEST-085)
            def footer_evidence(name, states, locale, viewport_id, geometry):
                # Resolve the PNG target under the standard browser test artifact directory.
                target=screenshots/name
                # Capture the governed footer itself without the generic shell helper's intentional status-bar suppression.
                page.get_by_test_id('shell-status').screenshot(path=str(target),animations='disabled',style='#toast { visibility: hidden !important; }')
                # Record the active viewport dimensions alongside the named visual-matrix viewport.
                viewport=page.viewport_size
                # Record the current focus target so the bounded artifact remains self-describing.
                focused=page.evaluate("() => document.activeElement?.getAttribute('data-testid') || ''")
                # Bind the footer crop, locale, viewport, and passing geometry to one after-pass evidence sidecar.
                metadata={'evidence_class':'after_pass','branch':evidence_branch,'commit':evidence_commit,'surface':'shell_lobby','states':states,'locale':locale,'viewport':{'id':viewport_id,**viewport},'path':str(target.relative_to(ROOT)).replace('\\','/'),'focused_control':focused,'region_selector':'[data-testid="shell-status"]','geometry':geometry}
                # Write the exact geometry proof next to its visible footer image for independent artifact audit.
                target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
            # Capture one bounded interaction region without misrepresenting unrelated full-page defects as accepted.
            def region_evidence(name, selector, surface, states, locale, viewport_id):
                # Resolve the PNG target under the standard browser test artifact directory.
                target=screenshots/name
                # Capture only the named interaction region so the artifact proves the behavior under review.
                page.locator(selector).screenshot(path=str(target),animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                # Record the active viewport dimensions alongside the named visual-matrix viewport.
                viewport=page.viewport_size
                # Record the current focus target so keyboard state remains auditable after the run.
                focused=page.evaluate("() => document.activeElement?.getAttribute('data-testid') || document.activeElement?.getAttribute('data-action') || ''")
                # Build the complete after-pass metadata and disclose the intentionally bounded region.
                metadata={'evidence_class':'after_pass','branch':evidence_branch,'commit':evidence_commit,'surface':surface,'states':states,'locale':locale,'viewport':{'id':viewport_id,**viewport},'path':str(target.relative_to(ROOT)).replace('\\','/'),'focused_control':focused,'region_selector':selector}
                # Write a UTF-8 sidecar next to the image so the focused evidence remains self-describing.
                target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
            # Store browser JavaScript that audits visible player-facing strings and localized attributes.
            route_i18n_audit_script=r"""async ({ domain, interpolationKey }) => {
              // Read the public runtime state after the requested route has mounted.
              const state = window.CasinoI18n.getLocaleState();
              // Store the active locale so resource inspection matches rendered text.
              const locale = state.locale;
              // Load every active resource dictionary so any installed key leak is detectable.
              const loadedResources = await Promise.all(state.loadedDomains.map(async loadedDomain => {
                // Fetch the locale-owned dictionary without relying on browser cache state.
                const response = await fetch(`/i18n/${locale}/${loadedDomain}.json`, { cache: 'no-cache' });
                // Return the decoded dictionary or an empty object for a failed fetch.
                return response.ok ? response.json() : {};
              }));
              // Fetch the route dictionary for representative title and interpolation checks.
              const domainResponse = await fetch(`/i18n/${locale}/${domain}.json`, { cache: 'no-cache' });
              // Decode the route dictionary when its resource request succeeds.
              const domainResource = domainResponse.ok ? await domainResponse.json() : {};
              // Combine all loaded dictionary keys into one exact-match leak catalog.
              const installedKeys = new Set(loadedResources.flatMap(resource => Object.keys(resource)));
              // Define visibility using layout boxes plus computed visibility.
              const isVisible = element => Boolean(element && (element.offsetWidth || element.offsetHeight || element.getClientRects().length) && getComputedStyle(element).visibility !== 'hidden');
              // Collect normalized player-visible strings from text and descriptive attributes.
              const entries = [];
              // Walk text nodes so concatenated container text cannot hide an exact raw key.
              const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
              // Visit every rendered text node in document order.
              while (walker.nextNode()) {
                // Read the element that controls visibility for the current text node.
                const parent = walker.currentNode.parentElement;
                // Add each non-empty visible line as an independently auditable value.
                if (isVisible(parent)) entries.push(...walker.currentNode.textContent.split(/\r?\n/).map(value => value.trim()).filter(Boolean));
              }
              // Inspect localized tooltip, placeholder, and accessible-name attributes.
              document.querySelectorAll('*').forEach(element => {
                // Skip hidden elements because this gate targets rendered player surfaces.
                if (!isVisible(element)) return;
                // Check every supported player-facing descriptive attribute.
                ['title', 'placeholder', 'aria-label', 'data-tooltip'].forEach(attribute => {
                  // Normalize the attribute value before leak classification.
                  const value = element.getAttribute(attribute)?.trim();
                  // Add populated values to the shared surface catalog.
                  if (value) entries.push(value);
                });
              });
              // Read combined visible text for representative-label and interpolation matching.
              const bodyText = document.body.innerText;
              // Find exact installed resource keys exposed as player-facing values.
              const rawKeys = [...new Set(entries.filter(value => installedKeys.has(value)))].sort();
              // Find named placeholders that survived interpolation on any visible surface.
              const unresolvedPlaceholders = [...new Set(entries.filter(value => /\{[a-zA-Z0-9_]+\}/.test(value)))].sort();
              // Find Unicode replacement characters produced by broken resource decoding.
              const replacementCharacters = [...new Set(entries.filter(value => value.includes('\uFFFD')))].sort();
              // Find visible null-like sentinel values produced by missing application data.
              const invalidValues = [...new Set(entries.filter(value => /(^|\s)(undefined|null|NaN)(?=$|\s|[.,;:!?])/.test(value)))].sort();
              // Read the route's canonical localized game title.
              const representativeTitle = domainResource.title;
              // Read one route-owned localized template that must render concrete parameters.
              const interpolationTemplate = domainResource[interpolationKey];
              // Escape static template text before constructing the rendered-value pattern.
              const escapeRegex = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              // Replace named template slots with non-placeholder rendered-value matches.
              const interpolationPattern = interpolationTemplate ? new RegExp(interpolationTemplate.split(/\{[a-zA-Z0-9_]+\}/).map(escapeRegex).join('[^\\n{}]+')) : null;
              // Return complete evidence so Python assertions can produce focused failures.
              return {
                // Include locale/domain runtime diagnostics.
                state,
                // Include exact raw-key matches.
                rawKeys,
                // Include unresolved named placeholders.
                unresolvedPlaceholders,
                // Include broken-decoding evidence.
                replacementCharacters,
                // Include null-like visible values.
                invalidValues,
                // Include the expected route title.
                representativeTitle,
                // Report whether the human route title is visible.
                titleVisible: Boolean(representativeTitle && bodyText.includes(representativeTitle)),
                // Include the expected interpolation template for failure output.
                interpolationTemplate,
                // Report whether a concrete rendered interpolation matches the template.
                interpolationVisible: Boolean(interpolationPattern && interpolationPattern.test(bodyText)),
              };
            // Finish the browser audit function after returning structured evidence.
            }"""
            # Define a reusable assertion for one mounted game route and active locale.
            def assert_route_i18n(domain, interpolation_key):
                # Run the complete player-surface audit in the mounted browser page.
                audit=page.evaluate(route_i18n_audit_script, {'domain':domain,'interpolationKey':interpolation_key})
                # Verify the lazy route registered and loaded its own resource domain.
                assert domain in audit['state']['loadedDomains'], f'{domain} not loaded: {audit["state"]}'
                # Verify no lookup fell through to the raw-key fallback anywhere in the accumulated flow.
                assert audit['state']['missingKeyCount']==0, f'{domain} missing keys: {audit["state"]}'
                # Verify visible text, tooltip, placeholder, and accessible labels contain no installed raw keys.
                assert not audit['rawKeys'], f'{domain} visible raw keys: {audit["rawKeys"]}'
                # Verify all visible interpolated strings replaced their named placeholders.
                assert not audit['unresolvedPlaceholders'], f'{domain} unresolved placeholders: {audit["unresolvedPlaceholders"]}'
                # Verify decoded resources contain no Unicode replacement characters on player surfaces.
                assert not audit['replacementCharacters'], f'{domain} replacement characters: {audit["replacementCharacters"]}'
                # Verify player-visible values never degrade to JavaScript/Python null sentinels.
                assert not audit['invalidValues'], f'{domain} invalid values: {audit["invalidValues"]}'
                # Verify each route renders its locale-owned human game title.
                assert audit['titleVisible'], f'{domain} missing representative title: {audit["representativeTitle"]}'
                # Verify one representative localized interpolation is rendered with concrete values.
                assert audit['interpolationVisible'], f'{domain} missing interpolation: {audit["interpolationTemplate"]}'
            # Start protected logic so failures can be handled safely.
            try:
                # Navigate to the casino while unauthenticated to verify the login gate.
                # Initialize the shared player identity before either visible auth coverage or neutral shard bootstrap.
                browser_player_id=None
                # Establish only the minimum authenticated shell needed by non-auth shards.
                if not visible_auth_owner:
                    # Login through the isolated Playwright request context without replaying visible auth cases.
                    shard_fixture_login=page.request.post(base+'/api/v2/auth/login',data={'email':'demo@example.local','password':'password'})
                    # Fail the shard bootstrap before any owned case can consume an invalid session.
                    if not shard_fixture_login.ok or shard_fixture_login.json().get('ok') is not True: raise AssertionError('case-neutral shard login failed')
                    # Mount the authoritative lobby in the same browser context used by owned cases.
                    page.goto(base,wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Resolve the player identity without depending on the shard-zero wallet case.
                    browser_player_id=page.evaluate("window.CasinoCurrentUser.player.player_id")
                # Collect the normal-player half of Admin navigation authorization on the same shard as its consumer.
                def collect_normal_admin_navigation():
                    # Store every governed locale and viewport absence result.
                    normal_results=[]
                    # Define the exact responsive matrix shared with the later Admin-presence half.
                    viewports={'desktop_primary':{'width':1920,'height':1080},'mobile':{'width':390,'height':844}}
                    # Exercise the role-aware normal shell through both installed locales.
                    for locale in ('en-US','ru-RU'):
                        # Rerender the normal-player shell through its visible locale control.
                        page.get_by_test_id('shell-locale-select').select_option(locale)
                        # Wait until locale state confirms the requested shell rerender.
                        page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                        # Inspect the complete responsive matrix reserved for this authorization surface.
                        for viewport_id,viewport in viewports.items():
                            # Resize before checking reachability and containment.
                            page.set_viewport_size(viewport); page.wait_for_timeout(150)
                            # Record complete absence and page containment for the normal role.
                            normal_results.append({'locale':locale,'viewport':viewport_id,'count':page.get_by_test_id('nav-admin').count(),'contained':page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")})
                            # Capture self-describing normal-player absence evidence.
                            game_evidence(f'after-pass-shell-admin-nav-hidden-player-{locale}-{viewport_id}.png','shell_lobby',['authenticated','admin_nav_hidden_player'],locale,viewport_id)
                    # Restore English and the primary viewport before route-restoration proof.
                    page.set_viewport_size({'width':1920,'height':1080}); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                    # Navigate and reload one game route under the same normal-player session.
                    page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS); page.reload(wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
                    # Record that route restoration preserves complete Admin-affordance absence.
                    route_restored=page.get_by_test_id('nav-admin').count()==0
                    # Return to the lobby before direct protected-resource checks.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Probe protected Admin HTML, JavaScript, and API authority with the normal session.
                    html_result=page.evaluate("""async () => { const response=await fetch('/admin',{credentials:'include'}); const text=await response.text(); return {status:response.status,contains_admin_view:text.includes('adminView')}; }""")
                    # Require JavaScript source to remain protected before any Admin bytes load.
                    js_result=page.evaluate("""async () => { const response=await fetch('/admin.js',{credentials:'include'}); const text=await response.text(); return {status:response.status,contains_admin_view:text.includes('adminView')}; }""")
                    # Read the standard protected Admin API envelope with normal-player authority.
                    api_result=page.evaluate("""async () => { const response=await fetch('/api/v1/admin/overview',{credentials:'include'}); return {status:response.status,body:await response.json()}; }""")
                    # Return all producer values together so no cross-shard local can leak.
                    return {'results':normal_results,'viewports':viewports,'route_restored':route_restored,'html':html_result,'js':js_result,'api':api_result}
                # Delegate the complete auth, wallet, shell, catalog, and responsive-lobby affinity family without transferring page ownership.
                browser_auth_lobby.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser_shard_owns,page,base,ROOT,visual_matrix,read_i18n_json,casino_config,assert_condition,shot,catalog_evidence,region_evidence,wallet_evidence,footer_evidence,game_evidence,console_errors,http_errors,provider_requests)
                # Resolve the player identity after every owned auth/lobby path restores the shared authenticated shell.
                browser_player_id=page.evaluate("window.CasinoCurrentUser.player.player_id")
                # Prove semantic game colors remain distinct from shared brand chrome and playing-card suit styling. (UX-024, TEST-149)
                def semantic_game_colors():
                    # Resolve the exact governed viewport dimensions from the visual matrix.
                    color_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
                    # Declare the four real game routes and their stable ready markers.
                    color_routes=(('roulette','roulette-premium'),('color_wheel','color-wheel'),('marble_race','marble-race'),('keno','keno-premium-hero'))
                    # Retain one sanitized computed-style receipt for every required evidence cell.
                    color_receipts=[]
                    # Restore shared shell state even when one semantic assertion fails.
                    try:
                        # Exercise the installed English and Russian locales symmetrically.
                        for color_locale in ('en-US','ru-RU'):
                            # Select the locale through the visible shared-shell control.
                            page.get_by_test_id('shell-locale-select').select_option(color_locale)
                            # Wait until the installed locale owns subsequent game renders.
                            page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=color_locale)
                            # Exercise every viewport governed by the visual standard.
                            for color_viewport_id,color_viewport in color_viewports.items():
                                # Apply the exact governed dimensions before mounting each game.
                                page.set_viewport_size(color_viewport)
                                # Visit all four affected game surfaces through their real shell controls.
                                for color_game,ready_testid in color_routes:
                                    # Open the game through its catalog-owned navigation button.
                                    page.get_by_test_id(f'nav-{color_game}').click()
                                    # Wait for the game's real route surface to own the outlet.
                                    page.get_by_test_id(ready_testid).wait_for(timeout=WAIT_MS)
                                    # Put Keno into its real selected-number state without starting a wager.
                                    if color_game=='keno':
                                        # Resolve the first numbered board control for a deterministic metallic-gold selection.
                                        keno_number=page.get_by_test_id('keno-num-1')
                                        # Select the number only when the route did not preserve it from an earlier cell.
                                        if keno_number.get_attribute('aria-pressed')!='true':
                                            # Activate the real board control so computed style is read from production state.
                                            keno_number.click()
                                    # Read only bounded computed styles and temporary cascade probes from the mounted document.
                                    color_diagnostic=page.evaluate("""gameId => {
                                      // Resolve a rendered node or fail the owning Browser case immediately.
                                      const styleFor = selector => {
                                        // Select the first production node matching the governed selector.
                                        const node = document.querySelector(selector);
                                        // Reject a missing semantic surface instead of substituting a fallback value.
                                        if (!node) throw new Error(`missing semantic color node: ${selector}`);
                                        // Return the browser's authoritative computed style for this rendered node.
                                        return getComputedStyle(node);
                                      };
                                      // Read the shared semantic tokens from the actual document root.
                                      const rootStyle = getComputedStyle(document.documentElement);
                                      // Create an off-screen playing-card probe that exercises the production cascade without changing game state.
                                      const cardProbe = document.createElement('span');
                                      // Apply the exact shared suit classes whose appearance must remain unchanged.
                                      cardProbe.className = 'playing-card red';
                                      // Give the probe a real suit glyph so inherited color and card background both resolve.
                                      cardProbe.textContent = '♥';
                                      // Keep the probe out of screenshots and layout while it remains style-computable.
                                      cardProbe.style.cssText = 'position:fixed;left:-10000px;top:-10000px';
                                      // Attach the probe to the mounted route for production cascade resolution.
                                      document.body.appendChild(cardProbe);
                                      // Capture the unchanged suit foreground and card-face background.
                                      const cardStyle = getComputedStyle(cardProbe);
                                      // Build the bounded common receipt before removing the temporary probe.
                                      const receipt = {
                                        tokens:{metalGold:rootStyle.getPropertyValue('--metal-gold').trim(),metalGoldDeep:rootStyle.getPropertyValue('--metal-gold-deep').trim(),feltGreen:rootStyle.getPropertyValue('--felt-green').trim()},
                                        brand:styleFor('.brand-mark').backgroundImage,
                                        card:{color:cardStyle.color,background:cardStyle.backgroundColor}
                                      };
                                      // Remove the temporary suit probe before evidence capture.
                                      cardProbe.remove();
                                      // Capture Roulette's rendered red and green pockets plus a production-cascade wager-chip probe.
                                      if (gameId === 'roulette') {
                                        // Create a noninteractive off-screen chip under the real premium table cascade.
                                        const chipProbe = document.createElement('span');
                                        // Apply the exact production chip class.
                                        chipProbe.className = 'bet-chip';
                                        // Keep the probe outside layout and screenshot bounds.
                                        chipProbe.style.cssText = 'position:fixed;left:-10000px;top:-10000px';
                                        // Attach it beneath the actual route so the late premium style block participates.
                                        document.querySelector('.roulette-premium').appendChild(chipProbe);
                                        // Preserve the fully resolved metallic chip gradient with the real pocket colors.
                                        receipt.game={red:styleFor('.roulette-premium .table-cell.red').backgroundImage,green:styleFor('.roulette-premium .table-cell.green').backgroundImage,gold:getComputedStyle(chipProbe).backgroundImage};
                                        // Remove the temporary chip before the screenshot is captured.
                                        chipProbe.remove();
                                      }
                                      // Capture Color Wheel's real red, green, and gold betting controls.
                                      if (gameId === 'color_wheel') receipt.game={red:styleFor('.cw-bet.red').backgroundImage,green:styleFor('.cw-bet.green').backgroundImage,gold:styleFor('.cw-bet.gold').backgroundImage};
                                      // Capture Marble Race's rendered red, green, and gold/yellow marbles in catalog order.
                                      if (gameId === 'marble_race') {
                                        // Read all six rendered marble tokens from the actual track.
                                        const marbles = [...document.querySelectorAll('.mr-marble')].map(node => getComputedStyle(node).backgroundColor);
                                        // Preserve the red, green, and gold/yellow entries only.
                                        receipt.game={red:marbles[0],green:marbles[2],gold:marbles[3]};
                                      }
                                      // Capture Keno's real selected number plus a production-cascade catch-state probe.
                                      if (gameId === 'keno') {
                                        // Create one off-screen number using the exact catch classes without changing a draw outcome.
                                        const catchProbe = document.createElement('span');
                                        // Apply the production number and catch classes.
                                        catchProbe.className = 'keno-num catch';
                                        // Keep the probe style-computable but outside layout and screenshots.
                                        catchProbe.style.cssText = 'position:fixed;left:-10000px;top:-10000px';
                                        // Attach the probe under the actual premium Keno board cascade.
                                        document.querySelector('.keno-premium-board').appendChild(catchProbe);
                                        // Preserve the actual selected gold plus resolved catch foreground and felt background.
                                        receipt.game={gold:styleFor('.keno-num.selected').backgroundColor,green:getComputedStyle(catchProbe).backgroundColor,catchText:getComputedStyle(catchProbe).color};
                                        // Remove the temporary catch probe before evidence capture.
                                        catchProbe.remove();
                                      }
                                      // Return only fixed, value-bounded computed-style strings.
                                      return receipt;
                                    }""",color_game)
                                    # Require the shared game tokens to remain exact and independent from brand aliases.
                                    assert color_diagnostic['tokens']=={'metalGold':'#e8c760','metalGoldDeep':'#bf9330','feltGreen':'#087a43'},color_diagnostic
                                    # Require the shared brand mark to retain its rose chrome gradient.
                                    assert 'rgb(255, 59, 107)' in color_diagnostic['brand'] and 'rgb(224, 30, 82)' in color_diagnostic['brand'],color_diagnostic
                                    # Require playing-card suit red and the ivory card face to remain unchanged.
                                    assert color_diagnostic['card']=={'color':'rgb(177, 0, 32)','background':'rgb(251, 247, 233)'},color_diagnostic
                                    # Require Roulette's rendered pockets to preserve true table red and green.
                                    if color_game=='roulette':
                                        # Match both pocket gradients and the resolved metallic-gold wager chip.
                                        assert all(value in color_diagnostic['game']['red'] for value in ('rgb(194, 36, 51)','rgb(124, 18, 32)')) and all(value in color_diagnostic['game']['green'] for value in ('rgb(15, 145, 82)','rgb(6, 90, 49)')) and all(value in color_diagnostic['game']['gold'] for value in ('rgb(232, 199, 96)','rgb(191, 147, 48)')),color_diagnostic
                                    # Require Color Wheel's rendered betting controls to retain real red, green, and gold.
                                    if color_game=='color_wheel':
                                        # Match the leading semantic color of all three production gradients.
                                        assert 'rgb(214, 50, 61)' in color_diagnostic['game']['red'] and 'rgb(15, 156, 76)' in color_diagnostic['game']['green'] and 'rgb(240, 196, 93)' in color_diagnostic['game']['gold'],color_diagnostic
                                    # Require Marble Race's production marbles to retain real red, green, and gold/yellow.
                                    if color_game=='marble_race':
                                        # Compare exact solid fills from the rendered track.
                                        assert color_diagnostic['game']=={'red':'rgb(214, 50, 61)','green':'rgb(15, 156, 76)','gold':'rgb(231, 189, 88)'},color_diagnostic
                                    # Require Keno's selected number to use metallic gold and its catch semantic to bind felt green.
                                    if color_game=='keno':
                                        # Compare the actual selected state and fully resolved catch foreground/background.
                                        assert color_diagnostic['game']=={'gold':'rgb(232, 199, 96)','green':'rgb(8, 122, 67)','catchText':'rgb(244, 238, 255)'},color_diagnostic
                                    # Retain scalar cell identity separately from the nested computed game-color mapping.
                                    color_receipts.append({**color_diagnostic,'game':color_game,'locale':color_locale,'viewport':color_viewport_id,'computed_game_colors':color_diagnostic['game']})
                                    # Capture one exact-head artifact for this real route, locale, and viewport cell.
                                    game_evidence(f'after-pass-game-color-{color_game}-{color_locale.lower()}-{color_viewport_id}.png',color_game,['semantic_game_colors'],color_locale,color_viewport_id,color_diagnostic)
                        # Define the complete four-game, two-locale, four-viewport identity set from governed inputs.
                        expected_color_receipts={(game,locale,viewport) for game,_ready_testid in color_routes for locale in ('en-US','ru-RU') for viewport in color_viewports}
                        # Require scalar identities while retaining every computed game-color mapping under its fixed nested key.
                        assert all(all(isinstance(row[key],str) for key in ('game','locale','viewport')) and isinstance(row['computed_game_colors'],dict) for row in color_receipts),color_receipts
                        # Require all 32 governed identity tuples to be present exactly once.
                        assert len(color_receipts)==32 and {(row['game'],row['locale'],row['viewport']) for row in color_receipts}==expected_color_receipts,color_receipts
                    # Restore shared locale, viewport, and route ownership for later Browser cases.
                    finally:
                        # Restore English through the visible shell selector.
                        page.get_by_test_id('shell-locale-select').select_option('en-US')
                        # Wait for the English runtime to finish its installed-resource swap.
                        page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                        # Restore the primary desktop dimensions.
                        page.set_viewport_size({'width':1920,'height':1080})
                        # Return to the shared lobby route.
                        page.get_by_test_id('nav-lobby').click()
                        # Require the lobby to own the route before the case terminalizes.
                        page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Register one new permanent Browser case with only its authorized product and test requirements.
                run_case('BR-GAME-COLOR-001',['UX-024','TEST-149'],semantic_game_colors)
                # Define catalog_route_discovery to mount every frontend driver from catalog metadata.
                def catalog_route_discovery():
                    # Select a catalog game with a route id that differs from its display label for loader-copy coverage. (UX-011)
                    loading_game=next(game for game in casino_config.GAMES if game['id']=='andar_bahar')
                    # Store the intercepted module route so the test can release it after reading the loading panel.
                    held_loading_route={'route':None}
                    # Define hold_loading_module to pause one first-time module import at the real network boundary.
                    def hold_loading_module(route):
                        # Preserve the Playwright route object so the visible loading state can be inspected before import completion.
                        held_loading_route['route']=route
                    # Hold only the selected module request so the rest of the browser suite remains real-backend.
                    page.route('**/games/andar_bahar.js',hold_loading_module)
                    # Navigate through the normal shell button to render the loading panel before the dynamic import resolves.
                    page.get_by_test_id('nav-andar_bahar').click()
                    # Wait until the route import is paused, proving the loading panel is still on screen.
                    page.wait_for_function("() => document.querySelector('.loading-panel h2')?.textContent.includes('Loading') && document.querySelector('.loading-panel h2')?.textContent.includes('Andar Bahar')")
                    # Read the player-facing loading panel copy for the route-label assertion.
                    loading_panel_copy=page.locator('.loading-panel h2').inner_text()
                    # Require the display label and reject the raw internal slug.
                    assert 'Andar Bahar' in loading_panel_copy and 'andar_bahar' not in loading_panel_copy
                    # Bound the wait for Playwright to hand the paused module request back to Python.
                    loading_route_deadline=time.time()+5
                    # Wait briefly for the held route object so the request can be released deliberately.
                    while held_loading_route['route'] is None and time.time()<loading_route_deadline:
                        # Sleep in short intervals so a missing route fails quickly instead of hanging the suite.
                        time.sleep(0.05)
                    # Require the route hold to be active before releasing the dynamic import.
                    assert held_loading_route['route'] is not None
                    # Release the held module request so the selected route can finish mounting normally.
                    held_loading_route['route'].continue_()
                    # Wait for the selected module's declared ready selector before removing the route handler.
                    page.get_by_test_id(loading_game['frontend']['ready_testid']).wait_for(timeout=WAIT_MS)
                    # Remove the one-shot import hold before the generic catalog route walk.
                    page.unroute('**/games/andar_bahar.js',hold_loading_module)
                    # Visit every catalog game through its generated shell navigation control.
                    for game in casino_config.GAMES:
                        # Navigate through the generic catalog-owned test id.
                        page.get_by_test_id(f"nav-{game['id']}").click()
                        # Wait for the independently declared ready selector before continuing.
                        page.get_by_test_id(game['frontend']['ready_testid']).wait_for(timeout=WAIT_MS)
                        # Require the canonical reloadable route to match module metadata.
                        assert page.url.split('?',1)[0].endswith(game['route'])
                    # Return to the lobby after generic discovery coverage.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute catalog-driven frontend driver discovery for all current games.
                run_case('BR-CATALOG-DISCOVERY-001',['CORE-021','TEST-042','UX-011'],catalog_route_discovery)
                # Define layout_containment_walk to prove no meaningful content escapes the viewport or its clipper on any route. (UX-026)
                def layout_containment_walk():
                    # Start protected coverage so shared viewport and route state is always restored.
                    try:
                        # Walk the full catalog at one narrow-phone and one tall-desktop viewport that historically clipped content.
                        for containment_width,containment_height in ((390,844),(1280,1024)):
                            # Apply the governed containment viewport before mounting each route.
                            page.set_viewport_size({'width':containment_width,'height':containment_height})
                            # Mount every catalog route through its real navigation control.
                            for containment_game in casino_config.GAMES:
                                # Navigate through the generic catalog-owned test id.
                                page.get_by_test_id(f"nav-{containment_game['id']}").click()
                                # Wait for the independently declared ready selector before measuring.
                                page.get_by_test_id(containment_game['frontend']['ready_testid']).wait_for(timeout=WAIT_MS)
                                # Let responsive tracks and route-owned fitting settle before the audit.
                                page.wait_for_timeout(120)
                                # Measure through the same production auditor that powers runtime telemetry.
                                containment_audit=page.evaluate("() => import('/core/ui.js').then(module => module.auditLayoutContainment(document.getElementById('view')))")
                                # Require zero document sideways scroll and zero meaningful clipped or escaped content.
                                assert containment_audit['docOverflow']<=4 and not containment_audit['offenders'],(containment_width,containment_height,containment_game['id'],containment_audit)
                        # Re-prove the fixed Roulette board rect inside its shell at every historically clipping width.
                        for roulette_width,roulette_height in ((320,700),(430,932),(720,900),(1366,768),(1920,1080)):
                            # Apply the regression viewport before mounting Roulette.
                            page.set_viewport_size({'width':roulette_width,'height':roulette_height})
                            # Mount Roulette through its real navigation control.
                            page.get_by_test_id('nav-roulette').click()
                            # Wait for the premium Roulette surface before measuring the board.
                            page.get_by_test_id('roulette-premium').wait_for(timeout=WAIT_MS)
                            # Let the measured continuous fit apply before reading rects.
                            page.wait_for_timeout(150)
                            # Read the board and shell rectangles from the live layout.
                            roulette_fit=page.evaluate("""() => { const shell=document.querySelector('.roulette-table-shell'); const board=document.querySelector('.roulette-table-board'); const stage=document.querySelector('[data-testid=roulette-premium-stage]'); const footer=document.querySelector('.status-bar'); const sr=shell.getBoundingClientRect(); const br=board.getBoundingClientRect(); const gr=stage.getBoundingClientRect(); const fr=footer.getBoundingClientRect(); return {shellLeft:sr.left,shellRight:sr.right,shellBottom:sr.bottom,boardLeft:br.left,boardRight:br.right,boardBottom:br.bottom,stageBottom:gr.bottom,footerTop:fr.top,scale:board.style.transform}; }""")
                            # Require the complete scaled board inside its shell on both axes with a one-pixel rounding tolerance.
                            assert roulette_fit['boardLeft']>=roulette_fit['shellLeft']-1 and roulette_fit['boardRight']<=roulette_fit['shellRight']+1 and roulette_fit['boardBottom']<=roulette_fit['shellBottom']+1,(roulette_width,roulette_height,roulette_fit)
                            # Require governed desktop Roulette stages to finish above the fixed status bar instead of clipping their last betting row.
                            if roulette_width>=1366:
                                # Compare the actual stage and shell bottoms to the footer boundary rather than trusting ancestor overflow styles.
                                assert roulette_fit['shellBottom']<=roulette_fit['stageBottom']+1 and roulette_fit['stageBottom']<=roulette_fit['footerTop']+1,(roulette_width,roulette_height,roulette_fit)
                            # Capture the governed primary-desktop after-state once the complete board has passed containment.
                            if roulette_width==1920:
                                # Preserve viewport evidence with the fixed footer visible as the bottom boundary.
                                page.screenshot(path=str(screenshots/'after-pass-roulette-bottom-contained-1920x1080.png'),full_page=False)
                        # Re-prove the complete Bingo card and call bay inside the center stage at both governed desktop viewports. (issue #611)
                        for bingo_width,bingo_height in ((1440,900),(1920,1080)):
                            # Apply the governed desktop viewport before mounting Bingo.
                            page.set_viewport_size({'width':bingo_width,'height':bingo_height})
                            # Mount Bingo through its real navigation control.
                            page.get_by_test_id('nav-bingo').click()
                            # Wait for the premium Bingo surface before measuring its complete stage.
                            page.get_by_test_id('premium-bingo').wait_for(timeout=WAIT_MS)
                            # Let desktop grid tracks settle before reading bottom-edge containment.
                            page.wait_for_timeout(150)
                            # Read the real card, call bay, stage, outlet, and fixed status-bar boundaries.
                            bingo_fit=page.evaluate("""() => { const rect=selector=>document.querySelector(selector).getBoundingClientRect(); const stage=rect('.premium-bingo .game-stage'); const card=rect('.premium-bingo .bingo-card'); const callBay=rect('.premium-bingo-call-bay'); const footer=rect('.status-bar'); const outlet=document.querySelector('#view.screen.game-screen'); return {stageBottom:stage.bottom,cardBottom:card.bottom,callBottom:callBay.bottom,footerTop:footer.top,outletClientHeight:outlet.clientHeight,outletScrollHeight:outlet.scrollHeight,scrollWidth:document.documentElement.scrollWidth,width:innerWidth}; }""")
                            # Require every primary Bingo surface above the footer with no hidden outlet tail or horizontal document overflow.
                            assert bingo_fit['scrollWidth']<=bingo_fit['width']+1 and bingo_fit['cardBottom']<=bingo_fit['stageBottom']+1 and bingo_fit['callBottom']<=bingo_fit['stageBottom']+1 and bingo_fit['stageBottom']<=bingo_fit['footerTop']+1 and bingo_fit['outletScrollHeight']<=bingo_fit['outletClientHeight']+1,(bingo_width,bingo_height,bingo_fit)
                            # Capture the governed primary-desktop after-state once the complete Bingo stage has passed containment.
                            if bingo_width==1920:
                                # Preserve viewport evidence with the fixed footer visible as the bottom boundary.
                                page.screenshot(path=str(screenshots/'after-pass-bingo-bottom-contained-1920x1080.png'),full_page=False)
                    # Restore shared viewport and route ownership for later Browser cases.
                    finally:
                        # Restore the primary desktop dimensions.
                        page.set_viewport_size({'width':1920,'height':1080})
                        # Return to the shared lobby route.
                        page.get_by_test_id('nav-lobby').click()
                        # Require the lobby to own the route before the case terminalizes.
                        page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Register the permanent containment case with only its authorized product and test requirements.
                run_case('BR-LAYOUT-CONTAIN-001',['UX-026','TEST-154'],layout_containment_walk)
                # Define action_scroll_focus_stability to prove in-game actions never reload, renavigate, or reset the reading position. (UX-027)
                def action_scroll_focus_stability():
                    # Start protected coverage so shared viewport and route state is always restored.
                    try:
                        # Use a desktop viewport where Blackjack owns scrollable internal rails.
                        page.set_viewport_size({'width':1440,'height':860})
                        # Mount Blackjack through its real navigation control.
                        page.get_by_test_id('nav-blackjack').click()
                        # Wait for the Blackjack surface before arranging scroll state.
                        page.get_by_test_id('blackjack-deal').wait_for(timeout=WAIT_MS)
                        # Stamp a document-lifetime marker that any reload or renavigation would destroy.
                        page.evaluate("() => { window.__uxStabilityMarker='held'; }")
                        # Record the pre-action route for the no-navigation assertion.
                        stability_url=page.url
                        # Scroll the control rail to a deep position a reset would visibly destroy.
                        page.evaluate("() => { const rail=document.querySelector('#view .control-rail'); rail.scrollTop=260; }")
                        # Save the table rules through the real control so a full-root busy rerender cycle runs.
                        page.evaluate("() => { document.getElementById('saveRules').click(); }")
                        # Wait for the localized success toast that follows the settled rerender.
                        page.wait_for_function("() => !document.getElementById('toast').hidden")
                        # Let the trailing enabled-state rerender and focus recovery settle.
                        page.wait_for_timeout(400)
                        # Read every stability signal in one settled evaluation.
                        stability=page.evaluate("""() => { const view=document.getElementById('view'); const rail=view.querySelector('.control-rail'); return {marker:window.__uxStabilityMarker,railTop:rail?rail.scrollTop:null,focusInside:view.contains(document.activeElement)||document.activeElement===view,href:location.href}; }""")
                        # Require the document to have survived without a reload.
                        assert stability['marker']=='held',stability
                        # Require the route to remain unchanged by the action.
                        assert stability['href']==stability_url,stability
                        # Require the internal rail to keep its deep scroll position within anchoring tolerance.
                        assert stability['railTop'] is not None and abs(stability['railTop']-260)<=80,stability
                        # Require keyboard focus to stay inside the game region instead of the document body.
                        assert stability['focusInside'],stability
                        # Reuse the mobile document-scroll composition for the clamp-rescue assertion.
                        page.set_viewport_size({'width':390,'height':844})
                        # Mount Roulette because its stacked route exposed the reported delayed document-scroll clamp.
                        page.get_by_test_id('nav-roulette').click()
                        # Wait for the chip controls before arranging document scroll.
                        page.wait_for_selector('#view [data-chip]',timeout=WAIT_MS)
                        # Scroll the document deep toward the play controls.
                        page.evaluate("() => window.scrollTo(0,Math.max(0,document.documentElement.scrollHeight-window.innerHeight))")
                        # Record the deep scroll offset the rerender must not clamp to the top.
                        roulette_scroll=page.evaluate("() => Math.round(window.scrollY)")
                        # Schedule the delayed top clamp before a synchronous Roulette chip-selection full-root rerender so frame ordering is deterministic.
                        page.evaluate("() => { requestAnimationFrame(() => window.scrollTo(0,0)); document.querySelector('#view [data-chip=\"5\"]').click(); }")
                        # Let the settled rerender and any anchoring adjustment finish.
                        page.wait_for_timeout(500)
                        # Read the post-action document offset.
                        roulette_after=page.evaluate("() => Math.round(window.scrollY)")
                        # Require a meaningful pre-action offset so the clamp assertion stays honest.
                        assert roulette_scroll>120,(roulette_scroll,roulette_after)
                        # Require the rerender not to throw the player back to the top of the document.
                        assert roulette_after>60,(roulette_scroll,roulette_after)
                    # Restore shared viewport and route ownership for later Browser cases.
                    finally:
                        # Restore the primary desktop dimensions.
                        page.set_viewport_size({'width':1920,'height':1080})
                        # Return to the shared lobby route.
                        page.get_by_test_id('nav-lobby').click()
                        # Require the lobby to own the route before the case terminalizes.
                        page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Register the permanent action-stability case with only its authorized product and test requirements.
                run_case('BR-ACTION-STABILITY-001',['UX-027','TEST-155'],action_scroll_focus_stability)
                # Define the governed ready-state visual proof for the twelve catalog-expansion games. (issue #73)
                def catalog_expansion_visuals():
                    # Preserve the controller-owned expansion order so missing or duplicate registrations fail closed.
                    expansion_ids=('color_wheel','poker_dice','boule','faro','trente_et_quarante','pachinko','coin_pusher','marble_race','pattern_draw','lucky_grid','daily_draw_lab','four_card_poker')
                    # Resolve each registered descriptor instead of duplicating route, ready-test, or locale-domain metadata.
                    expansion_games=[next(game for game in casino_config.GAMES if game['id']==game_id) for game_id in expansion_ids]
                    # Require one unique registry entry for every approved expansion game.
                    assert len(expansion_games)==12 and len({game['id'] for game in expansion_games})==12
                    # Exercise both governed locales because each expansion route owns an independent resource domain.
                    for locale in ('en-US','ru-RU'):
                        # Select the locale through the real player-shell control.
                        page.get_by_test_id('shell-locale-select').select_option(locale)
                        # Wait until the public locale state confirms the requested rerender.
                        page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                        # Exercise every governed visual-matrix viewport for each expansion route.
                        for viewport_id,width,height in (('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)):
                            # Apply the exact governed viewport before mounting a route.
                            page.set_viewport_size({'width':width,'height':height})
                            # Walk the registered expansion games without bypassing shell navigation.
                            for game in expansion_games:
                                # Open the game through the catalog-owned route control.
                                page.get_by_test_id(f"nav-{game['id']}").click()
                                # Wait for the module-owned readiness marker before visual or localization assertions.
                                page.get_by_test_id(game['frontend']['ready_testid']).wait_for(timeout=WAIT_MS)
                                # Let the stable ready layout settle without exercising game mechanics.
                                page.wait_for_timeout(100)
                                # Require the canonical reloadable route declared by the module descriptor.
                                assert page.url.split('?',1)[0].endswith(game['route']),{'game':game['id'],'route':page.url}
                                # Audit every visible player-facing string against the route's loaded resource domain.
                                localization=page.evaluate(route_i18n_audit_script,{'domain':game['frontend']['i18n_domain'],'interpolationKey':game['frontend']['i18n_probe']})
                                # Require route-domain loading, zero missing keys, and no raw or malformed localized output.
                                assert game['frontend']['i18n_domain'] in localization['state']['loadedDomains'] and localization['state']['missingKeyCount']==0 and not localization['rawKeys'] and not localization['unresolvedPlaceholders'] and not localization['replacementCharacters'] and not localization['invalidValues'] and localization['titleVisible'],{'game':game['id'],'locale':locale,'localization':localization}
                                # Measure ready-state containment, operability, and fixed feedback-control clearance.
                                geometry=page.evaluate("""readyTestId => { const root=document.querySelector(`[data-testid="${readyTestId}"]`); const fixed=document.querySelector('.report-problem-fab:not([hidden])')?.getBoundingClientRect(); const intersects=rect=>fixed&&rect.left<fixed.right&&rect.right>fixed.left&&rect.top<fixed.bottom&&rect.bottom>fixed.top; const visible=node=>{const style=getComputedStyle(node);return style.display!=='none'&&style.visibility!=='hidden'&&node.getClientRects().length>0;}; const hits=[]; for(const node of root?.querySelectorAll('button,input,select,a[href],[role="button"]')||[]){if(visible(node)&&intersects(node.getBoundingClientRect()))hits.push(node.getAttribute('data-testid')||node.getAttribute('data-action')||node.tagName.toLowerCase());} for(const node of root?.querySelectorAll('h1,h2,h3,h4,p,li,label,legend,span,strong')||[]){if(!visible(node))continue;const range=document.createRange();range.selectNodeContents(node);if([...range.getClientRects()].some(intersects))hits.push(`${node.tagName.toLowerCase()}:${node.textContent.trim()}`);} const box=root?.getBoundingClientRect(); const enabled=[...(root?.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),a[href],[role="button"]')||[])].filter(visible); return {documentFits:document.documentElement.scrollWidth<=window.innerWidth+1,gameVisible:Boolean(root&&visible(root)),readableInlineSize:Math.round(box?.width||0),enabledControls:enabled.length,feedbackOverlaps:[...new Set(hits)]}; }""",game['frontend']['ready_testid'])
                                # Require a visible, operable, horizontally contained route with no feedback-button collision.
                                assert geometry['documentFits'] and geometry['gameVisible'] and geometry['readableInlineSize']>=280 and geometry['enabledControls']>0 and not geometry['feedbackOverlaps'],{'game':game['id'],'locale':locale,'viewport':viewport_id,'geometry':geometry}
                                # Capture one governed after-pass PNG and provenance sidecar for this route/locale/viewport.
                                game_evidence(f"after-pass-catalog-expansion-{game['id']}-{locale}-{viewport_id}.png",game['id'],['ready'],locale,viewport_id)
                    # Restore English before returning to the canonical lobby state.
                    page.get_by_test_id('shell-locale-select').select_option('en-US')
                    # Wait for the English shell rerender before restoring desktop geometry.
                    page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                    # Restore the primary desktop viewport expected by later browser cases.
                    page.set_viewport_size({'width':1920,'height':1080})
                    # Return to the lobby after all governed expansion artifacts are complete.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the expansion matrix under each game-specific permanent test allocation.
                run_case('BR-CATALOG-EXPANSION-001',['CWHEEL-001','CWHEEL-002','PDICE-001','PDICE-002','BOULE-001','BOULE-002','FARO-001','FARO-002','TEQ-001','TEQ-002','PACH-001','PACH-002','COINP-001','COINP-002','MARBLE-001','MARBLE-002','PATTERN-001','PATTERN-002','LGRID-001','LGRID-002','DDLAB-001','DDLAB-002','FOURCP-001','FOURCP-002','TEST-119','TEST-120','TEST-121','TEST-122','TEST-123','TEST-124','TEST-125','TEST-126','TEST-128','TEST-129','TEST-130','TEST-131'],catalog_expansion_visuals)
                # Read the authoritative wallet rendered by the shared shell as a numeric play-token balance. (issue #712, TEST-185)
                def newest_game_wallet_value():
                    # Strip grouping separators while retaining the exact fractional amount.
                    return page.evaluate("() => Number(String(document.querySelector('#balance')?.textContent || '').replace(/[^0-9.-]/g, ''))")
                # Require one simple settled-round game to wager, settle, refresh its wallet, and recover its repeat state after reload.
                def newest_simple_game_acceptance(game_id, ready_testid, endpoint_suffix, action, result_testid, repeat_testid):
                    # Enter the catalog-owned route and wait for its stable module marker.
                    page.get_by_test_id(f'nav-{game_id}').click(); page.get_by_test_id(ready_testid).wait_for(timeout=WAIT_MS * 2)
                    # Capture the pre-action wallet so a stale rendered value cannot satisfy settlement evidence accidentally.
                    before=newest_game_wallet_value()
                    # Observe the one real mutation response while the supplied control callback starts the wager.
                    with page.expect_response(lambda response: response.request.method=='POST' and endpoint_suffix in response.url,timeout=WAIT_MS * 2) as response_info: action()
                    # Read the standard API envelope and bind the rendered wallet to its authoritative player payload.
                    payload=response_info.value.json()['data']; expected=float(payload['player']['balance'])
                    # Wait for terminal controls and the exact response-owned wallet to become visible.
                    page.get_by_test_id(repeat_testid).wait_for(state='visible',timeout=WAIT_MS * 2); page.wait_for_function("expected => Number(String(document.querySelector('#balance')?.textContent || '').replace(/[^0-9.-]/g, '')) === expected",arg=expected,timeout=WAIT_MS * 2)
                    # Wait for the game-owned presentation to finish after the wallet refresh, then require its terminal status and repeat action.
                    page.wait_for_function("ids => { const result=document.querySelector(`[data-testid=\"${ids.result}\"]`); const repeat=document.querySelector(`[data-testid=\"${ids.repeat}\"]`); return Boolean(result?.textContent?.trim()) && Boolean(repeat) && !repeat.disabled; }",arg={'result':result_testid,'repeat':repeat_testid},timeout=WAIT_MS * 2)
                    # Re-read the settled controls so this assertion remains bound to the visible terminal frame.
                    assert page.get_by_test_id(result_testid).inner_text().strip() and page.get_by_test_id(repeat_testid).is_enabled()
                    # Require the action to have produced an authoritative wallet observation, allowing a legitimate push to equal the prior balance.
                    assert isinstance(before,(int,float)) and newest_game_wallet_value()==expected
                    # Reload the canonical deep link and require server-owned repeat and wallet recovery without a second mutation.
                    page.reload(wait_until='networkidle'); page.get_by_test_id(ready_testid).wait_for(timeout=WAIT_MS * 2); page.wait_for_function("expected => Number(String(document.querySelector('#balance')?.textContent || '').replace(/[^0-9.-]/g, '')) === expected",arg=expected,timeout=WAIT_MS * 2)
                    # Require the route, repeat control, and authoritative wallet to survive the reload.
                    assert page.url.split('?',1)[0].endswith(f'/games/{game_id}') and page.get_by_test_id(repeat_testid).is_enabled() and newest_game_wallet_value()==expected
                    # Return to the lobby so every dedicated case begins from the same shell state.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Exercise Faro through its real deal endpoint and reload-safe recent-round state.
                def faro_browser_acceptance():
                    # Bind exact external-style and ready-layout evidence before the real deal mutates the cards.
                    def deal_once():
                        # Restore the governed primary desktop viewport and route top after preceding shared cases.
                        page.set_viewport_size({'width':1920,'height':1080}); page.evaluate('window.scrollTo(0,0)'); page.wait_for_timeout(100)
                        # Require one exact external game-owned stylesheet rather than injected opaque CSS.
                        style_link=page.locator('link#faro-styles'); assert style_link.count()==1 and style_link.get_attribute('href')=='/games/faro.css'
                        # Prove the migrated asset loaded by binding the unchanged desktop route and rank-grid layout.
                        assert page.get_by_test_id('faro').evaluate("el => { const route=getComputedStyle(el); const ranks=getComputedStyle(el.querySelector('.fr-ranks')); return route.display==='grid' && route.gridTemplateColumns.split(' ').length===2 && ranks.display==='grid' && ranks.gridTemplateColumns.split(' ').length===7; }")
                        # Capture after-pass second-adopter evidence before the real settled action mutates the cards.
                        page.locator('#view').screenshot(path=str(screenshots/'after-pass-faro-lifecycle-desktop.png'),animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                        # Use the default rank and five-token chip for one real settled deal.
                        page.get_by_test_id('faro-deal').click()
                    # Bind the deal response, terminal wallet, and recovered repeat control.
                    newest_simple_game_acceptance('faro','faro','/api/v1/games/faro/deals',deal_once,'faro-result','faro-repeat')
                # Record Faro's dedicated affected-game acceptance case.
                run_case('BR-FARO-001',['FARO-001','FARO-002','CORE-034','TEST-185','TEST-248'],faro_browser_acceptance)
                # Exercise Trente et Quarante through its real coup endpoint and reload-safe recent-round state.
                def trente_et_quarante_browser_acceptance():
                    # Use the default rouge bet and five-token chip for one real settled coup.
                    newest_simple_game_acceptance('trente_et_quarante','trente-et-quarante','/api/v1/games/trente-et-quarante/coups',lambda: page.get_by_test_id('teq-deal').click(),'teq-result','teq-repeat')
                # Record Trente et Quarante's dedicated affected-game acceptance case.
                run_case('BR-TEQ-001',['TEQ-001','TEQ-002','TEST-185'],trente_et_quarante_browser_acceptance)
                # Exercise Pachinko through its real drop endpoint and reload-safe recent-round state.
                def pachinko_browser_acceptance():
                    # Use the default five-token chip for one real server-owned pin path.
                    newest_simple_game_acceptance('pachinko','pachinko','/api/v1/games/pachinko/drops',lambda: page.get_by_test_id('pachinko-drop').click(),'pachinko-result','pachinko-repeat')
                # Record Pachinko's dedicated affected-game acceptance case.
                run_case('BR-PACHINKO-001',['PACH-001','PACH-002','TEST-185'],pachinko_browser_acceptance)
                # Exercise Daily Draw Lab through a marked number, real draw, and reload-safe recent-round state.
                def daily_draw_lab_browser_acceptance():
                    # Mark number one before invoking the otherwise shared settled-round helper.
                    def draw_once():
                        # Require exactly one external game-owned stylesheet rather than injected opaque CSS.
                        style_link=page.locator('link#daily-draw-lab-styles'); assert style_link.count()==1 and style_link.get_attribute('href')=='/games/daily_draw_lab.css'
                        # Prove the migrated asset loaded by binding the unchanged desktop grid and number-board layout.
                        assert page.get_by_test_id('daily-draw-lab').evaluate("el => { const route=getComputedStyle(el); const board=getComputedStyle(el.querySelector('.dd-board')); return route.display==='grid' && route.gridTemplateColumns.split(' ').length===2 && board.display==='grid' && board.gridTemplateColumns.split(' ').length===6; }")
                        # Capture after-pass first-adopter evidence before the real settled action mutates its board.
                        page.screenshot(path=str(screenshots/'after-pass-daily-draw-lab-lifecycle-desktop.png'),full_page=False)
                        # Select one legal number and start the real draw.
                        page.locator('[data-number="1"]').click(); page.get_by_test_id('daily-draw-lab-go').click()
                    # Bind the draw response, terminal wallet, and recovered repeat control.
                    newest_simple_game_acceptance('daily_draw_lab','daily-draw-lab','/api/v1/games/daily-draw-lab/draws',draw_once,'daily-draw-lab-result','daily-draw-lab-repeat')
                # Record Daily Draw Lab's dedicated affected-game acceptance case.
                run_case('BR-DAILY-DRAW-LAB-001',['DDLAB-001','DDLAB-002','CORE-034','TEST-185','TEST-248'],daily_draw_lab_browser_acceptance)
                # Exercise Four Card Poker's two-step real deal and decision lifecycle.
                def four_card_poker_browser_acceptance():
                    # Enter the catalog-owned route and wait for the stable game root.
                    page.get_by_test_id('nav-four_card_poker').click(); page.get_by_test_id('four-card-poker').wait_for(timeout=WAIT_MS * 2)
                    # Set a small legal ante and explicitly dispatch change before starting the round.
                    page.locator('[data-ante]').fill('2'); page.locator('[data-ante]').dispatch_event('change')
                    # Start one real deal and wait for the player decision stage.
                    with page.expect_response(lambda response: response.request.method=='POST' and response.url.endswith('/api/v1/games/four-card-poker/rounds'),timeout=WAIT_MS * 2): page.locator('[data-deal]').click()
                    # Require the one-times play option before committing the terminal decision.
                    page.locator('[data-play="1"]').wait_for(timeout=WAIT_MS * 2)
                    # Observe the real terminal response while choosing one-times play.
                    with page.expect_response(lambda response: response.request.method=='POST' and '/api/v1/games/four-card-poker/rounds/' in response.url and response.url.endswith('/decisions'),timeout=WAIT_MS * 2) as response_info: page.locator('[data-play="1"]').click()
                    # Bind the rendered wallet to the terminal response's authoritative player value.
                    expected=float(response_info.value.json()['data']['player']['balance']); page.wait_for_function("expected => Number(String(document.querySelector('#balance')?.textContent || '').replace(/[^0-9.-]/g, '')) === expected",arg=expected,timeout=WAIT_MS * 2)
                    # Require the settled result and enabled repeat action.
                    page.get_by_test_id('four-card-poker-result').wait_for(timeout=WAIT_MS * 2); assert page.locator('[data-action="repeat"]').is_enabled()
                    # Reload and require the exact settled route, wallet, and repeat state to recover without another wager.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('four-card-poker').wait_for(timeout=WAIT_MS * 2); page.wait_for_function("expected => Number(String(document.querySelector('#balance')?.textContent || '').replace(/[^0-9.-]/g, '')) === expected",arg=expected,timeout=WAIT_MS * 2)
                    # Prove both authoritative terminal result and repeat controls survived the reload.
                    assert page.get_by_test_id('four-card-poker-result').inner_text().strip() and page.locator('[data-action="repeat"]').is_enabled() and newest_game_wallet_value()==expected
                    # Return to the lobby for the next independent Browser case.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Record Four Card Poker's dedicated affected-game acceptance case.
                run_case('BR-FOUR-CARD-POKER-001',['FOURCP-001','FOURCP-002','TEST-185'],four_card_poker_browser_acceptance)
                # Prove every catalog game keeps its enabled controls vertically reachable in the fixed-height shell. (issue #221, CORE-015, UX-004, TEST-139)
                def control_reachability():
                    # Pin the two governed desktop viewports where clipped controls were originally reported.
                    reach_viewports=(('desktop_primary',1920,1080),('desktop_compact',1440,900))
                    # Collect every offending surface before failing so one hosted run reports the complete catalog.
                    unreachable_report={}
                    # Restore the governed English shell before walking routes and capturing reviewable evidence.
                    page.get_by_test_id('shell-locale-select').select_option('en-US')
                    # Wait until the public locale state owns the next route render.
                    page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                    # Sweep the authoritative registry rather than maintaining a second catalog list.
                    for reach_game in casino_config.GAMES:
                        # Return through the real shell lobby before mounting each registered game.
                        page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=8000)
                        # Enter the game through its catalog-owned navigation control.
                        page.get_by_test_id(f"nav-{reach_game['id']}").click()
                        # Wait for the descriptor-declared ready marker before measuring the complete route outlet.
                        page.get_by_test_id(reach_game['frontend']['ready_testid']).wait_for(timeout=WAIT_MS * 2)
                        # Measure and capture both required desktop surfaces.
                        for reach_viewport_id,reach_width,reach_height in reach_viewports:
                            # Apply the exact governed viewport and let responsive layout settle.
                            page.set_viewport_size({'width':reach_width,'height':reach_height}); page.wait_for_timeout(160)
                            # Inspect every enabled route control while excluding Chromium geometry retained inside collapsed disclosures.
                            reach=page.evaluate("""() => { const root=document.querySelector('#view'); const visible=node=>{const style=getComputedStyle(node);return style.display!=='none'&&style.visibility!=='hidden'&&node.getClientRects().length>0;}; const inCollapsedDisclosure=node=>Boolean(node.closest('details:not([open])'))&&!node.closest('summary'); const clipsY=el=>{const overflow=getComputedStyle(el).overflowY;return overflow==='hidden'||overflow==='clip';}; const scrollsY=el=>{const overflow=getComputedStyle(el).overflowY;return (overflow==='auto'||overflow==='scroll')&&el.scrollHeight>el.clientHeight+1;}; const label=node=>node.getAttribute('data-testid')||node.getAttribute('data-action')||node.getAttribute('aria-label')||(node.textContent||'').trim().slice(0,24)||node.tagName.toLowerCase(); const enabled=[...(root?.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),a[href],[role="button"]')||[])].filter(node=>visible(node)&&!inCollapsedDisclosure(node)); const unreachable=[]; for(const node of enabled){const rect=node.getBoundingClientRect();let ancestor=node.parentElement;let blocked=false;let reachableByScroll=false;while(ancestor&&ancestor!==document.documentElement){if(scrollsY(ancestor)){reachableByScroll=true;break;}if(clipsY(ancestor)){const bounds=ancestor.getBoundingClientRect();if(rect.bottom>bounds.bottom+1||rect.top<bounds.top-1){blocked=true;break;}}ancestor=ancestor.parentElement;}if(!blocked&&!reachableByScroll&&(rect.bottom>window.innerHeight+1||rect.top<-1)){const documentScrolls=document.scrollingElement&&document.scrollingElement.scrollHeight>window.innerHeight+1;if(!documentScrolls)blocked=true;}if(blocked)unreachable.push(label(node));}return {enabledControls:enabled.length,unreachableControls:[...new Set(unreachable)]};}""")
                            # Reject an empty route so missing game controls cannot produce a vacuous pass.
                            assert reach['enabledControls']>0,{'game':reach_game['id'],'viewport':reach_viewport_id,'reach':reach}
                            # Preserve the complete bounded failure set for one actionable hosted result.
                            if reach['unreachableControls']: unreachable_report[f"{reach_game['id']}@{reach_viewport_id}"]=reach['unreachableControls'][:8]
                            # Emit exact-commit after-pass evidence for independent human review of every governed surface.
                            game_evidence(f"after-pass-control-reach-{reach_game['id']}-en-{reach_viewport_id}.png",reach_game['id'],['ready','control_reachability'],'en-US',reach_viewport_id)
                    # Fail after the full sweep so the artifact and error identify every clipped route.
                    assert not unreachable_report,unreachable_report
                    # Restore the canonical lobby and primary viewport for the next independent case.
                    page.set_viewport_size({'width':1920,'height':1080}); page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute one shard-owned full-catalog case under the reserved permanent test mapping.
                run_case('BR-CONTROL-REACH-001',['CORE-015','UX-004','TEST-139'],control_reachability)
                # Define catalog-wide repeat control, localization, real action, and visual acceptance. (UX-022, TEST-137)
                def catalog_repeat_bet():
                    # Pin the exact forty-three games that lacked the pre-existing Roulette and Baccarat behavior.
                    repeat_ids=('acey_deucey','andar_bahar','big_six_wheel','bingo','boule','caribbean_stud','casino_holdem','casino_war','chuck_a_luck','coin_pusher','color_wheel','craps','crown_and_anchor','daily_draw_lab','deuces_wild_video_poker','double_bonus_video_poker','dragon_tiger','fan_tan','faro','four_card_poker','hi_lo','jacks_or_better_video_poker','joker_poker','keno','let_it_ride','lucky_grid','marble_race','mississippi_stud','multi_hand_video_poker','over_under_7','pachinko','pai_gow_poker','pattern_draw','plinko','poker_dice','red_dog','scratch_cards','sic_bo','slots','teen_patti','texas_holdem_practice_table','three_card_poker','trente_et_quarante')
                    # Resolve every route and readiness marker from the authoritative catalog.
                    repeat_games=[next(game for game in casino_config.GAMES if game['id']==game_id) for game_id in repeat_ids]
                    # Reject missing or duplicate descriptors before any visible evidence can pass.
                    assert len(repeat_games)==43 and len({game['id'] for game in repeat_games})==43
                    # Select every supported repeat-button identity without coupling games to one CSS class.
                    repeat_selector='button[data-action="repeat"],button[data-testid*="repeat"],button[data-repeat],button[id*="Repeat"],button[id*="repeat"]'
                    # Pin exact visible copy in both installed locales.
                    locale_copy={'en-US':'Repeat bet','ru-RU':'\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c \u0441\u0442\u0430\u0432\u043a\u0443'}
                    # Audit every route in both locales at a governed compact desktop viewport.
                    page.set_viewport_size({'width':1440,'height':900})
                    # Count real route renders so the hosted audit cannot silently classify every control as phase-gated.
                    rendered_repeat_controls=0
                    # Exercise every repeat control after a real locale change.
                    for locale in ('en-US','ru-RU'):
                        # Select the locale through the player-visible shell control.
                        page.get_by_test_id('shell-locale-select').select_option(locale)
                        # Wait until the runtime locale owns the next route render.
                        page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                        # Walk the complete approved catalog slice.
                        for game in repeat_games:
                            # Navigate through the catalog-owned route control.
                            page.get_by_test_id(f"nav-{game['id']}").click()
                            # Wait for the independently declared game readiness marker.
                            game_root=page.get_by_test_id(game['frontend']['ready_testid']); game_root.wait_for(timeout=WAIT_MS)
                            # Resolve the one visible repeat button inside the mounted route outlet, because some readiness markers intentionally identify only the visual stage.
                            repeat_button=page.locator('#view').locator(repeat_selector)
                            # Read the phase-dependent count without requiring a settled-only control on an untouched idle route.
                            repeat_count=repeat_button.count()
                            # Reject duplicate controls while allowing a game to defer its one semantic action until settlement.
                            assert repeat_count in (0,1),{'game':game['id'],'locale':locale,'repeatCount':repeat_count}
                            # Require a real operable initial state when the repeat action is intentionally phase-gated.
                            if repeat_count==0:
                                # Inspect only the mounted route outlet so shell navigation cannot satisfy game operability.
                                initial_state=page.evaluate("""() => { const root=document.querySelector('#view'); const visible=node=>{const style=getComputedStyle(node);return style.display!=='none'&&style.visibility!=='hidden'&&node.getClientRects().length>0;}; const enabled=[...(root?.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),a[href],[role="button"]')||[])].filter(visible); return {routeVisible:Boolean(root&&visible(root)),enabledControls:enabled.length}; }""")
                                # Fail closed if a supposedly phase-gated game is not actually ready for the player to start.
                                assert initial_state['routeVisible'] and initial_state['enabledControls']>0,{'game':game['id'],'locale':locale,'initialState':initial_state}
                                # Continue because listener-free UI-REPEAT-BET-001 owns the hidden phase markup, copy, wiring, and safety contract.
                                continue
                            # Count one runtime-rendered control for the aggregate fail-closed proof.
                            rendered_repeat_controls+=1
                            # Resolve and scroll atomically so an expected state-hydration rerender cannot detach a Playwright element handle mid-action.
                            page.evaluate("""selector => document.querySelector('#view')?.querySelector(selector)?.scrollIntoView({block:'center',inline:'nearest'})""",repeat_selector)
                            # Require installed-locale copy on the real control.
                            assert repeat_button.is_visible() and repeat_button.inner_text().strip()==locale_copy[locale],{'game':game['id'],'locale':locale,'copy':repeat_button.inner_text()}
                            # Measure touch size, document containment, and fixed feedback-control clearance.
                            geometry=page.evaluate("""selector => { const root=document.querySelector('#view'); const button=root?.querySelector(selector); const rect=button?.getBoundingClientRect(); const feedback=document.querySelector('.report-problem-fab:not([hidden])')?.getBoundingClientRect(); const overlaps=Boolean(rect&&feedback&&rect.left<feedback.right&&rect.right>feedback.left&&rect.top<feedback.bottom&&rect.bottom>feedback.top); return {visible:Boolean(rect&&rect.width>0&&rect.height>0),width:Math.round(rect?.width||0),height:Math.round(rect?.height||0),left:Math.round(rect?.left||0),right:Math.round(rect?.right||0),viewportWidth:innerWidth,documentFits:document.documentElement.scrollWidth<=window.innerWidth+1,feedbackOverlap:overlaps}; }""",repeat_selector)
                            # Reject hidden, undersized, clipped, overflowing, or feedback-obscured controls.
                            assert geometry['visible'] and geometry['width']>=80 and geometry['height']>=40 and geometry['left']>=-1 and geometry['right']<=geometry['viewportWidth']+1 and geometry['documentFits'] and not geometry['feedbackOverlap'],{'game':game['id'],'locale':locale,'geometry':geometry}
                    # Require at least one real localized route render in each locale in addition to the complete listener-free catalog contract.
                    assert rendered_repeat_controls>=2,{'renderedRepeatControls':rendered_repeat_controls}
                    # Restore English before executing one real backend-funded repeat.
                    page.get_by_test_id('shell-locale-select').select_option('en-US')
                    # Wait for English before reading request payloads from the representative route.
                    page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                    # Open Color Wheel because its fixed color and stake form one compact, auditable repeat configuration.
                    page.get_by_test_id('nav-color_wheel').click(); page.get_by_test_id('color-wheel').wait_for(timeout=WAIT_MS)
                    # Capture the first real settlement request while using the primary action.
                    with page.expect_request(lambda request: request.url.endswith('/api/v1/games/color-wheel/spins') and request.method=='POST') as first_request_info:
                        # Start one normally configured spin through the visible primary button.
                        page.get_by_test_id('color-wheel-spin').click()
                    # Preserve only the non-secret wager configuration and exactly-once identity.
                    first_payload=first_request_info.value.post_data_json
                    # Wait until the decorative spin finishes and repeat becomes enabled.
                    page.wait_for_function("() => !document.querySelector('[data-testid=\"color-wheel-repeat\"]')?.disabled",timeout=WAIT_MS * 2)
                    # Capture the second real settlement request while using only one repeat click.
                    with page.expect_request(lambda request: request.url.endswith('/api/v1/games/color-wheel/spins') and request.method=='POST') as repeated_request_info:
                        # Trigger exactly one repeat through the localized secondary action.
                        page.get_by_test_id('color-wheel-repeat').click()
                    # Preserve the repeated request for exact configuration comparison.
                    repeated_payload=repeated_request_info.value.post_data_json
                    # Require the repeat to preserve color and stake while minting a fresh action identity.
                    assert repeated_payload['color']==first_payload['color'] and repeated_payload['stake']==first_payload['stake'] and repeated_payload['request_id']!=first_payload['request_id'],{'first':first_payload,'repeat':repeated_payload}
                    # Wait for the second settlement and busy-state cleanup before visual evidence.
                    page.wait_for_function("() => !document.querySelector('[data-testid=\"color-wheel-repeat\"]')?.disabled",timeout=WAIT_MS * 2)
                    # Enumerate the exact EN/RU and four-viewport matrix on the route whose real repeat action just passed.
                    evidence_rows=(('en-US','color_wheel','desktop_primary',1920,1080),('en-US','color_wheel','desktop_compact',1440,900),('en-US','color_wheel','tablet',1024,900),('en-US','color_wheel','mobile',390,844),('ru-RU','color_wheel','desktop_primary',1920,1080),('ru-RU','color_wheel','desktop_compact',1440,900),('ru-RU','color_wheel','tablet',1024,900),('ru-RU','color_wheel','mobile',390,844))
                    # Capture each representative route with exact-source sidecar provenance.
                    for locale,game_id,viewport_id,width,height in evidence_rows:
                        # Switch through the real player locale selector before mounting the route.
                        page.get_by_test_id('shell-locale-select').select_option(locale)
                        # Wait for the active locale to own the route render.
                        page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                        # Apply the exact governed viewport.
                        page.set_viewport_size({'width':width,'height':height})
                        # Resolve catalog metadata for the representative route.
                        game=next(item for item in repeat_games if item['id']==game_id)
                        # Open the route through its catalog-owned navigation control.
                        page.get_by_test_id(f'nav-{game_id}').click(); game_root=page.get_by_test_id(game['frontend']['ready_testid']); game_root.wait_for(timeout=WAIT_MS)
                        # Resolve the repeat control dynamically so evidence remains stable across route hydration rerenders.
                        repeat_button=page.locator('#view').locator(repeat_selector)
                        # Scroll atomically without retaining an element handle that a normal hydration rerender may detach.
                        page.evaluate("""selector => document.querySelector('#view')?.querySelector(selector)?.scrollIntoView({block:'center',inline:'nearest'})""",repeat_selector)
                        # Require one enabled localized repeat action in the exact evidence frame.
                        assert repeat_button.count()==1 and repeat_button.is_enabled() and repeat_button.inner_text().strip()==locale_copy[locale]
                        # Capture the complete game surface with the governed repeat-ready state.
                        game_evidence(f'after-pass-repeat-bet-{game_id}-{locale}-{viewport_id}.png',game_id,['repeat_available'],locale,viewport_id)
                    # Restore English, primary desktop, and lobby ownership for later cases.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'"); page.set_viewport_size({'width':1920,'height':1080}); page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Record catalog-wide rendering plus one exact real-backend repeat and eight governed artifacts.
                run_case('BR-REPEAT-BET-001',['UX-022','TEST-137'],catalog_repeat_bet)
                # Store the browser audit that proves every game control is reachable inside a scroll region at one viewport. (issue #221)
                nav_reach_script=r"""(rootSel) => {
                  // Resolve the mounted game root or fall back to the shared route outlet.
                  const root = document.querySelector(rootSel) || document.getElementById('view');
                  // Collect every interactive control the player must be able to operate.
                  const controls = [...root.querySelectorAll('button, input, select, [role=button], a[href]')];
                  // Track controls that cannot be brought fully into the viewport.
                  const unreachable = [];
                  // Inspect each control after scrolling it into the bounded scroll region.
                  for (const el of controls) {
                    // Read the resolved style so hidden controls are excluded from reachability.
                    const cs = getComputedStyle(el);
                    // Skip controls that are intentionally not displayed in the current phase.
                    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                    // Skip detached controls that have no layout box in this phase.
                    if (el.offsetParent === null && cs.position !== 'fixed') continue;
                    // Scroll the control into the center of any bounded scroll ancestor and the outlet.
                    el.scrollIntoView({block:'center', inline:'center'});
                    // Measure the control after scrolling to prove it is not clipped by a hidden-overflow ancestor.
                    const r = el.getBoundingClientRect();
                    // Require a real layout box and full containment within the current viewport.
                    const ok = r.width > 0 && r.height > 0 && r.top >= -2 && r.bottom <= window.innerHeight + 2 && r.left >= -2 && r.right <= window.innerWidth + 2;
                    // Record any control that remains clipped or off-screen after scrolling.
                    if (!ok) unreachable.push((el.getAttribute('data-testid') || el.className || el.tagName));
                  }
                  // Return the audited count and any unreachable controls for the assertion.
                  return {count: controls.length, unreachable};
                }"""
                # Define the bounded-nav, brand, and control-containment regression required by issue #221.
                def shell_nav_containment():
                    # Exercise every governed matrix viewport for the shell and the four previously clipped games.
                    for width,height,viewport_id in [(1920,1080,'desktop_primary'),(1440,900,'desktop_compact'),(1024,900,'tablet'),(390,844,'mobile')]:
                        # Apply the governed viewport before measuring shell and game layout.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Return to the lobby so the shell chrome is measured in a stable state.
                        page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                        # Require no page-level horizontal overflow at any governed viewport.
                        assert page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth") <= 2, f'horizontal overflow at {viewport_id}'
                        # Read the brand title text and its horizontal clip amount for the truncation assertion.
                        brand=page.evaluate("() => { const el=document.getElementById('shell-brand-title'); return {text:el.textContent.trim(), clip: el.scrollWidth - el.clientWidth}; }")
                        # Require the full product name with no ellipsis truncation at every width.
                        assert brand['text']=='TiltSeven' and brand['clip'] <= 1, f'brand truncated at {viewport_id}: {brand}'
                        # Read each primary-menu label width and its per-label clip for the readability assertion.
                        nav_items=page.evaluate("() => [...document.querySelectorAll('#main-nav .nav-item')].map(el=>({t:el.textContent.trim(), w:Math.round(el.getBoundingClientRect().width), clip: el.scrollWidth-el.clientWidth}))")
                        # Require every route label to stay readable (minimum touch width) and unclipped.
                        assert all(item['w'] >= 42 and item['clip'] <= 2 for item in nav_items), f'nav label unreadable/clipped at {viewport_id}'
                        # Prove each control the issue named remains reachable via a scroll region at this viewport.
                        for game_id,ready_testid in [('bingo','premium-bingo'),('blackjack','blackjack-premium'),('sic_bo','sic-bo-table'),('chuck_a_luck','chuck-a-luck')]:
                            # Open the game through its bounded-menu route control.
                            page.get_by_test_id(f'nav-{game_id}').click(); page.get_by_test_id(ready_testid).wait_for(timeout=WAIT_MS)
                            # Settle any mount animation before measuring control containment.
                            page.wait_for_timeout(200)
                            # Require no page-level horizontal overflow while the game is mounted.
                            assert page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth") <= 2, f'{game_id} horizontal overflow at {viewport_id}'
                            # Audit every interactive control for scroll reachability inside the bounded outlet.
                            reach=page.evaluate(nav_reach_script, f'[data-testid="{ready_testid}"]')
                            # Require every audited control to be reachable and never clipped by a hidden-overflow ancestor.
                            assert not reach['unreachable'], f'{game_id} controls unreachable at {viewport_id}: {reach["unreachable"][:5]}'
                            # Return to the lobby before the next audited game.
                            page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Capture bounded compact-desktop shell evidence for the affected surface.
                    page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(150)
                    # Store one after-pass compact shell screenshot for review.
                    shot('after-pass-shell-nav-bounded-compact.png')
                    # Restore desktop primary dimensions before later game interaction coverage runs.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(200)
                    # Return to the lobby so subsequent cases start from the shared shell.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Record bounded keyboard-accessible navigation, brand readability, and control containment across governed viewports.
                run_case('BR-SHELL-NAV-001',['CORE-006','CORE-007','CORE-015','UX-007','UX-009','SIC-BO-004','CHUCK-004','TEST-052'],shell_nav_containment)
                # Define real-backend Multi-Hand Video Poker browser and visual acceptance coverage.
                def multi_hand_video_poker_acceptance():
                    # Open the catalog-generated route and wait for its module-owned readiness selector.
                    page.get_by_test_id('nav-multi_hand_video_poker').click(); page.get_by_test_id('multi-hand-video-poker').wait_for(timeout=WAIT_MS)
                    # Require the canonical route and complete English title before interaction.
                    assert page.url.split('?',1)[0].endswith('/games/multi_hand_video_poker') and page.locator('.mhvp-header h1').inner_text()=='Multi-Hand Video Poker'
                    # Require the visible push row to state one returned credit rather than one-to-one profit odds.
                    assert '1× returned' in page.locator('.mhvp-data').inner_text()
                    # Reject raw resource identifiers from the initial player-facing surface.
                    visible_lines={line.strip() for line in page.locator('body').inner_text().splitlines() if line.strip()}
                    # Require representative owned resource keys to stay internal.
                    assert not ({'controls.deal','controls.draw','phases.ready','stage.readyTitle','units.playTokens'} & visible_lines),visible_lines
                    # Define all named viewports required by the Multi-Hand visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture the localized English ready state at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize to the exact visual-matrix dimensions before containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require the full page and mounted game surface to avoid horizontal overflow.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('multi-hand-video-poker').is_visible()
                        # Record self-describing English ready-state after-pass evidence.
                        game_evidence(f'after-pass-mhvp-ready-en-{viewport_id}.png','multi_hand_video_poker',['ready'],'en-US',viewport_id)
                    # Restore primary desktop dimensions for hold and multi-mode interaction evidence.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
                    # Select the required three-hand mode and start one real-backend wagered round.
                    page.locator('[data-hand-count="3"]').click(); page.locator('#mhvp-wager').fill('1'); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=WAIT_MS)
                    # Hold the first common card and wait for the persisted pressed state after rerender.
                    page.locator('[data-hold-position="0"]').click(); page.wait_for_function("() => document.querySelector('[data-hold-position=\"0\"]')?.getAttribute('aria-pressed') === 'true'")
                    # Capture the English hold-decision state with the selected control visible.
                    game_evidence('after-pass-mhvp-choose-holds-en-desktop_primary.png','multi_hand_video_poker',['choose_holds'],'en-US','desktop_primary')
                    # Draw all three hands and require the exact result cardinality and aggregate summary.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('mhvp-summary').wait_for(timeout=WAIT_MS); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=3)
                    # Capture the completed three-hand English state at primary desktop.
                    game_evidence('after-pass-mhvp-settled-3-en-desktop_primary.png','multi_hand_video_poker',['settled_3_hands'],'en-US','desktop_primary')
                    # Select five hands and start the next real-backend round.
                    page.locator('[data-hand-count="5"]').click(); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=WAIT_MS)
                    # Complete five hands and require every catalog-discovered result lane.
                    page.locator('[data-action="draw"]').click(); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=5)
                    # Resize to compact desktop and capture the five-hand settlement state.
                    page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(150); game_evidence('after-pass-mhvp-settled-5-en-desktop_compact.png','multi_hand_video_poker',['settled_5_hands'],'en-US','desktop_compact')
                    # Select ten hands and start the highest-cardinality real-backend round.
                    page.locator('[data-hand-count="10"]').click(); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=WAIT_MS)
                    # Complete ten hands and require every result lane before responsive evidence.
                    page.locator('[data-action="draw"]').click(); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=10)
                    # Resize to tablet and capture the stacked ten-hand settlement state.
                    page.set_viewport_size({'width':1024,'height':900}); page.wait_for_timeout(150); assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'); game_evidence('after-pass-mhvp-settled-10-en-tablet.png','multi_hand_video_poker',['settled_10_hands'],'en-US','tablet')
                    # Reload the canonical deep link and require the settled round to restore from real backend state.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('multi-hand-video-poker').wait_for(timeout=WAIT_MS); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=10)
                    # Restore primary desktop and capture canonical route restoration evidence.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150); game_evidence('after-pass-mhvp-route-restored-en-desktop_primary.png','multi_hand_video_poker',['route_restored','settled_10_hands'],'en-US','desktop_primary')
                    # Switch the mounted real game to Russian without losing its persisted state.
                    page.get_by_test_id('shell-locale-select').select_option('ru-RU'); page.wait_for_function("() => document.querySelector('.mhvp-header h1')?.textContent === 'Мультиручный видеопокер'")
                    # Require the Russian paytable to preserve the same total-return meaning.
                    assert '\u0432\u043e\u0437\u0432\u0440\u0430\u0442 1×' in page.locator('.mhvp-data').inner_text()
                    # Reject representative English game copy from the Russian player-facing surface.
                    russian_copy=page.get_by_test_id('multi-hand-video-poker').inner_text(); english_phrases=['Multi-Hand Video Poker','Deal hands','Draw cards','Play controls','Paytable','Ready to deal','Choose cards to hold','play tokens']; assert not [phrase for phrase in english_phrases if phrase.lower() in russian_copy.lower()],russian_copy
                    # Select three hands and start a Russian real-backend round for actionable evidence.
                    page.locator('[data-hand-count="3"]').click(); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=WAIT_MS)
                    # Hold the second common card and wait for its localized persisted selection.
                    page.locator('[data-hold-position="1"]').click(); page.wait_for_function("() => document.querySelector('[data-hold-position=\"1\"]')?.getAttribute('aria-pressed') === 'true'")
                    # Capture the Russian hold-decision state before drawing.
                    game_evidence('after-pass-mhvp-choose-holds-ru-desktop_primary.png','multi_hand_video_poker',['choose_holds'],'ru-RU','desktop_primary')
                    # Complete the Russian three-hand round and require the localized summary.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('mhvp-summary').wait_for(timeout=WAIT_MS); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=3)
                    # Capture Russian settled-state evidence at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize to the exact visual-matrix dimensions before localized containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require the Russian game to remain visible without page-level horizontal overflow.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('mhvp-summary').is_visible()
                        # Record self-describing Russian three-hand settlement evidence.
                        game_evidence(f'after-pass-mhvp-settled-3-ru-{viewport_id}.png','multi_hand_video_poker',['settled_3_hands'],'ru-RU',viewport_id)
                    # Restore primary desktop and English locale for established downstream browser cases.
                    page.set_viewport_size({'width':1920,'height':1080}); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => document.querySelector('.mhvp-header h1')?.textContent === 'Multi-Hand Video Poker'")
                    # Return to the lobby so route restoration and existing game interactions start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute real-backend mode, localization, responsive, route, and visual acceptance coverage.
                run_case('BR-MHVP-001',['MHVP-001','MHVP-002','MHVP-004','MHVP-005','I18N-010','TEST-117'],multi_hand_video_poker_acceptance)
                # Define real-backend Casino War browser and visual acceptance coverage.
                def casino_war_acceptance():
                    # Open the catalog-generated route and wait for its module-owned table selector.
                    page.get_by_test_id('nav-casino_war').click(); page.get_by_test_id('casino-war-table').wait_for(timeout=WAIT_MS)
                    # Require the canonical route and complete English title before interaction.
                    assert page.url.split('?',1)[0].endswith('/games/casino_war') and page.locator('.cw-header h1').inner_text()=='Casino War'
                    # Reject representative raw resource identifiers from the initial player-facing surface.
                    visible_lines={line.strip() for line in page.locator('.casino-war').inner_text().splitlines() if line.strip()}
                    # Require owned resource keys to remain internal after dynamic domain loading.
                    assert not ({'controls.deal','controls.war','phase.ready','stage.noRound','tokens.amount'} & visible_lines),visible_lines
                    # Define every named viewport required by the Casino War visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture the English accepting-wager state at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize to the exact visual-matrix dimensions before containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require the complete page and mounted table to avoid horizontal overflow.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('casino-war-table').is_visible()
                        # Record self-describing English accepting-wager evidence.
                        game_evidence(f'after-pass-casino-war-accepting-en-{viewport_id}.png','casino_war',['accepting_wager'],'en-US',viewport_id)
                    # Restore primary desktop dimensions before real-backend deal discovery.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
                    # Track whether a normal initial result has already been captured before the required tie.
                    initial_result_captured=False
                    # Search bounded real deals for the naturally occurring tie needed by the decision surface.
                    tie_found=False
                    # Deal enough six-deck comparisons that missing a tie is vanishingly unlikely while remaining bounded.
                    for attempt in range(120):
                        # Start one real ledger-backed round through the mounted frontend.
                        page.locator('[data-action="deal"]').click()
                        # Wait until the rerender exposes either a tie decision or the next-round control.
                        page.wait_for_function("() => { const war=document.querySelector('[data-action=\"war\"]'); const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean((war && !war.disabled) || (deal && !deal.disabled)); }",timeout=WAIT_MS)
                        # Stop on the first naturally dealt initial tie.
                        if page.locator('[data-action="war"]').count() and page.locator('[data-action="war"]').is_enabled():
                            # Preserve the successful discovery for the bounded-loop assertion.
                            tie_found=True
                            # Leave the tie unresolved so both decision buttons remain evidence-visible.
                            break
                        # Capture one ordinary initial result without duplicating the remaining loop attempts.
                        if not initial_result_captured:
                            # Record the settled initial comparison before starting another round.
                            game_evidence('after-pass-casino-war-initial-result-en-desktop_primary.png','casino_war',['initial_result'],'en-US','desktop_primary')
                            # Mark the matrix state as covered.
                            initial_result_captured=True
                    # Require the real backend to produce the decision state within the bounded search.
                    assert tie_found,'Casino War did not produce a real tie within 120 rounds'
                    # Capture the English tie-decision state at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before decision-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require both tie actions and page-level containment at this viewport.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('[data-action="surrender"]').is_visible() and page.locator('[data-action="war"]').is_visible()
                        # Record self-describing English war-decision evidence.
                        game_evidence(f'after-pass-casino-war-decision-en-{viewport_id}.png','casino_war',['war_decision'],'en-US',viewport_id)
                    # Switch the unresolved real round to Russian without discarding its state.
                    page.get_by_test_id('shell-locale-select').select_option('ru-RU'); page.wait_for_function("() => document.querySelector('.cw-phase')?.textContent !== 'Decision required'")
                    # Reject representative English game copy from the Russian mounted surface.
                    russian_copy=page.locator('.casino-war').inner_text(); english_phrases=['Deal cards','Deal next round','Surrender','Go to war','Table rules','play tokens','Decision required']; assert not [phrase for phrase in english_phrases if phrase.lower() in russian_copy.lower()],russian_copy
                    # Capture the Russian tie-decision state at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before localized decision-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require both localized actions and page-level containment at this viewport.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('[data-action="surrender"]').is_visible() and page.locator('[data-action="war"]').is_visible()
                        # Record self-describing Russian war-decision evidence.
                        game_evidence(f'after-pass-casino-war-decision-ru-{viewport_id}.png','casino_war',['war_decision'],'ru-RU',viewport_id)
                    # Restore primary desktop before committing the ledger-backed war decision.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
                    # Choose war through the real frontend and wait for the terminal next-round control.
                    page.locator('[data-action="war"]').click(); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }",timeout=WAIT_MS)
                    # Capture the Russian war result at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before localized terminal-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require the terminal next-round control and page-level containment.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('[data-action="deal"]').is_visible()
                        # Record self-describing Russian war-result evidence.
                        game_evidence(f'after-pass-casino-war-result-ru-{viewport_id}.png','casino_war',['war_result'],'ru-RU',viewport_id)
                    # Switch the settled war result back to English for the second locale evidence set.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => document.querySelector('.cw-phase')?.textContent === 'Round settled'")
                    # Capture the English war result at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before English terminal-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(150)
                        # Require the terminal next-round control and page-level containment.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('[data-action="deal"]').is_visible()
                        # Record self-describing English war-result evidence.
                        game_evidence(f'after-pass-casino-war-result-en-{viewport_id}.png','casino_war',['war_result'],'en-US',viewport_id)
                    # Reload the canonical deep link and require the settled war round to restore.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('casino-war-table').wait_for(timeout=WAIT_MS); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }")
                    # Restore primary desktop and record canonical route-restoration evidence.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150); game_evidence('after-pass-casino-war-route-restored-en-desktop_primary.png','casino_war',['route_restored','war_result'],'en-US','desktop_primary')
                    # Continue only if the first bounded search tied before producing a normal initial result.
                    if not initial_result_captured:
                        # Bound follow-up attempts while resolving any additional ties by surrender.
                        for attempt in range(40):
                            # Start the next real round through the restored route.
                            page.locator('[data-action="deal"]').click(); page.wait_for_function("() => { const war=document.querySelector('[data-action=\"war\"]'); const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean((war && !war.disabled) || (deal && !deal.disabled)); }",timeout=WAIT_MS)
                            # Capture and stop when the round settled from the initial comparison.
                            if page.locator('[data-action="deal"]').count() and page.locator('[data-action="deal"]').is_enabled():
                                # Record the remaining normal initial-result matrix state.
                                game_evidence('after-pass-casino-war-initial-result-en-desktop_primary.png','casino_war',['initial_result'],'en-US','desktop_primary')
                                # Mark the state as covered before leaving the bounded loop.
                                initial_result_captured=True
                                # Stop after the first qualifying initial result.
                                break
                            # Resolve another natural tie cheaply so the next comparison can begin.
                            page.locator('[data-action="surrender"]').click(); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }",timeout=WAIT_MS)
                    # Require ordinary initial-result evidence in addition to the decision and war-result states.
                    assert initial_result_captured,'Casino War did not produce an initial-result evidence state'
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute real-backend rules, localization, responsive, route, and visual acceptance coverage.
                run_case('BR-CW-001',['CW-001','CW-002','CW-004','CW-005'],casino_war_acceptance)
                # Define real-backend Big Six browser, localization, responsive, motion, and visual acceptance coverage.
                def big_six_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-big_six_wheel').click(); page.get_by_test_id('big-six-wheel').wait_for(timeout=WAIT_MS)
                    # Require the canonical route, English title, and ready phase from the live backend mount.
                    assert page.url.split('?',1)[0].endswith('/games/big_six_wheel') and page.locator('.big-six-wheel__header h1').inner_text()=='Big Six Wheel' and page.get_by_test_id('big-six-wheel-phase').inner_text()=='Accepting wagers'
                    # Require the complete code-native stage to remain painted inside its panel and every hidden ancestor.
                    def assert_big_six_stage_complete(viewport_id):
                        # Inspect the wheel shell, wheel, pointer, and hub without scrolling or changing later evidence.
                        failures=page.evaluate("""viewportId => { const failures=[]; const stage=document.querySelector('.big-six-wheel__stage'); const contained=['.big-six-wheel__wheel-shell','.big-six-wheel__pointer','.big-six-wheel__hub']; const painted={'.big-six-wheel__wheel':'.big-six-wheel__wheel-shell'}; const paintMinRatio=.8; if(!stage)return [{viewport:viewportId,selector:'.big-six-wheel__stage',reason:'stage missing'}]; const stageRect=stage.getBoundingClientRect(); const outside=(rect,owner)=>rect.left<owner.left-1||rect.right>owner.right+1||rect.top<owner.top-1||rect.bottom>owner.bottom+1; const visible=(node,style,rect)=>node.getClientRects().length&&style.display!=='none'&&style.visibility!=='hidden'&&rect.width>0&&rect.height>0; for(const selector of contained){const node=document.querySelector(selector); if(!node){failures.push({viewport:viewportId,selector,reason:'essential node missing'});continue;} const style=getComputedStyle(node); const rect=node.getBoundingClientRect(); if(!visible(node,style,rect)){failures.push({viewport:viewportId,selector,reason:'essential node not painted'});continue;} if(outside(rect,stageRect))failures.push({viewport:viewportId,selector,reason:'essential node escaped stage'}); let ancestor=node.parentElement; while(ancestor&&ancestor!==document.body){const ancestorStyle=getComputedStyle(ancestor);const ancestorRect=ancestor.getBoundingClientRect();const overflowY=ancestorStyle.overflowY==='visible'?ancestorStyle.overflow:ancestorStyle.overflowY;const overflowX=ancestorStyle.overflowX==='visible'?ancestorStyle.overflow:ancestorStyle.overflowX;const clippedY=(rect.top<ancestorRect.top-1||rect.bottom>ancestorRect.bottom+1)&&['hidden','clip'].includes(overflowY);const clippedX=(rect.left<ancestorRect.left-1||rect.right>ancestorRect.right+1)&&['hidden','clip'].includes(overflowX);if(clippedY||clippedX){failures.push({viewport:viewportId,selector,reason:'essential node clipped by hidden ancestor'});break;}ancestor=ancestor.parentElement;}} for(const [selector,ownerSelector] of Object.entries(painted)){const node=document.querySelector(selector);const owner=document.querySelector(ownerSelector);if(!node){failures.push({viewport:viewportId,selector,reason:'essential node missing'});continue;}if(!owner){failures.push({viewport:viewportId,selector:ownerSelector,reason:'visual owner missing'});continue;}const style=getComputedStyle(node);const rect=node.getBoundingClientRect();const ownerRect=owner.getBoundingClientRect();if(!visible(node,style,rect)){failures.push({viewport:viewportId,selector,reason:'essential node not painted'});continue;}const centerInside=rect.left+rect.width/2>=ownerRect.left-1&&rect.left+rect.width/2<=ownerRect.right+1&&rect.top+rect.height/2>=ownerRect.top-1&&rect.top+rect.height/2<=ownerRect.bottom+1;const coversOwner=rect.width>=ownerRect.width*paintMinRatio&&rect.height>=ownerRect.height*paintMinRatio;if(!centerInside||!coversOwner)failures.push({viewport:viewportId,selector,reason:'essential node does not cover visual owner'});}return failures;}""",viewport_id)
                        # Fail the named governed viewport with bounded public selector evidence.
                        assert not failures,failures
                    # Read the initial cumulative target before the first real motion-qualified spin.
                    initial_big_six_target=page.locator('[data-wheel]').evaluate("node => Number.parseFloat(node.style.getPropertyValue('--wheel-angle'))")
                    # Define every named viewport required by the Big Six visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture the English ready surface and containment at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize to the exact matrix dimensions before checking horizontal containment.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                        # Require a visible complete surface without page-level horizontal overflow.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('big-six-wheel').is_visible()
                        # Reject missing or clipped wheel, pointer, or hub before labeling evidence as passing.
                        assert_big_six_stage_complete(viewport_id)
                        # Record self-describing English ready evidence.
                        game_evidence(f'after-pass-big-six-ready-en-{viewport_id}.png','big_six_wheel',['ready'],'en-US',viewport_id)
                    # Restore primary desktop and enter a positive real-backend wager.
                    page.set_viewport_size({'width':1920,'height':1080}); page.locator('[data-wager="one"]').fill('1')
                    # Start one ledger-backed spin while observing its authoritative server-selected segment.
                    with page.expect_response(lambda response: response.url.endswith('/api/v1/games/big-six-wheel/spins') and response.request.method=='POST') as first_big_six_response_info:
                        # Activate the same visible control used by players.
                        page.locator('[data-spin]').click()
                    # Require the timer-owned active state and cumulative six-turn target before settlement.
                    page.wait_for_function("minimum => Number.parseFloat(document.querySelector('[data-wheel]')?.style.getPropertyValue('--wheel-angle')) >= minimum",arg=initial_big_six_target+(6*360),timeout=WAIT_MS)
                    # Decode the first standard response envelope for independent pointer-alignment proof.
                    first_big_six_round=first_big_six_response_info.value.json()['data']['round']
                    # Read the cumulative target mutated on the already-painted wheel element.
                    first_big_six_target=page.locator('[data-wheel]').evaluate("node => Number.parseFloat(node.style.getPropertyValue('--wheel-angle'))")
                    # Calculate the canonical segment-center orientation from server-owned result data.
                    first_big_six_landing=(360-((first_big_six_round['result_index']+0.5)*(360/54)))%360
                    # Require exact forward target continuity and final server-index alignment.
                    assert first_big_six_target-initial_big_six_target>=6*360-1e-6 and abs((first_big_six_target%360)-first_big_six_landing)<1e-6
                    # Require the outcome to remain hidden and every wager control to remain locked during motion.
                    assert page.locator('[data-spin]').is_disabled() and all(control.is_disabled() for control in page.locator('[data-wager]').all()) and page.locator('.big-six-wheel__hub').inner_text().strip()==page.locator('[data-spin]').inner_text().strip()
                    # Sample the composited wheel twice so a target teleport cannot satisfy the active state.
                    first_big_six_frame=page.locator('[data-wheel]').evaluate("node => getComputedStyle(node).transform"); page.wait_for_timeout(100); second_big_six_frame=page.locator('[data-wheel]').evaluate("node => getComputedStyle(node).transform")
                    # Require real browser interpolation between the two active presentation frames.
                    assert first_big_six_frame!='none' and second_big_six_frame!='none' and first_big_six_frame!=second_big_six_frame
                    # Capture the active normal-motion state while the route-owned timer is pending.
                    game_evidence('after-pass-big-six-spinning-en-desktop_primary.png','big_six_wheel',['spinning'],'en-US','desktop_primary')
                    # Wait for the scheduled settlement to restore an enabled action.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Settled' && !document.querySelector('[data-spin]')?.disabled",timeout=WAIT_MS)
                    # Start a second consecutive spin to reject absolute-angle reset and reverse regressions.
                    with page.expect_response(lambda response: response.url.endswith('/api/v1/games/big-six-wheel/spins') and response.request.method=='POST') as second_big_six_response_info:
                        # Reuse the retained positive wager through the visible action.
                        page.locator('[data-spin]').click()
                    # Require another complete forward target from the prior settled angle.
                    page.wait_for_function("minimum => Number.parseFloat(document.querySelector('[data-wheel]')?.style.getPropertyValue('--wheel-angle')) >= minimum",arg=first_big_six_target+(6*360),timeout=WAIT_MS)
                    # Decode the second authoritative result for independent alignment proof.
                    second_big_six_round=second_big_six_response_info.value.json()['data']['round']
                    # Read the second cumulative target without discarding its rotation history.
                    second_big_six_target=page.locator('[data-wheel]').evaluate("node => Number.parseFloat(node.style.getPropertyValue('--wheel-angle'))")
                    # Calculate the second server-selected segment center below the pointer.
                    second_big_six_landing=(360-((second_big_six_round['result_index']+0.5)*(360/54)))%360
                    # Reject reset, reverse, freeze, or server-index disagreement on the consecutive action.
                    assert second_big_six_target-first_big_six_target>=6*360-1e-6 and abs((second_big_six_target%360)-second_big_six_landing)<1e-6
                    # Wait for the second presentation to restore controls before terminal evidence begins.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Settled' && !document.querySelector('[data-spin]')?.disabled",timeout=WAIT_MS)
                    # Capture the settled English surface at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before terminal-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                        # Require the settled control and page-level containment.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('[data-spin]').is_enabled()
                        # Require the complete settled stage at this governed viewport.
                        assert_big_six_stage_complete(viewport_id)
                        # Record self-describing English settlement evidence.
                        game_evidence(f'after-pass-big-six-settled-en-{viewport_id}.png','big_six_wheel',['settled'],'en-US',viewport_id)
                    # Switch the restored settlement to Russian without discarding player-owned state.
                    page.get_by_test_id('shell-locale-select').select_option('ru-RU'); page.wait_for_function("() => document.querySelector('.big-six-wheel__header h1')?.textContent !== 'Big Six Wheel'")
                    # Reject representative English game copy from the Russian mounted surface.
                    russian_copy=page.locator('.big-six-wheel').inner_text(); english_phrases=['Accepting wagers','Spin wheel','Wagers','Wheel profile','Recent spins','play tokens','Settled']; assert not [phrase for phrase in english_phrases if phrase.lower() in russian_copy.lower()],russian_copy
                    # Capture the settled Russian surface at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before localized terminal-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                        # Require the localized route to remain visible and horizontally contained.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('big-six-wheel').is_visible()
                        # Require the complete localized settled stage before writing evidence.
                        assert_big_six_stage_complete(viewport_id)
                        # Record self-describing Russian settlement evidence.
                        game_evidence(f'after-pass-big-six-settled-ru-{viewport_id}.png','big_six_wheel',['settled'],'ru-RU',viewport_id)
                    # Reload in Russian so the route lifecycle restores a clean ready phase with persisted history.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('big-six-wheel').wait_for(timeout=WAIT_MS); page.wait_for_function("() => !document.querySelector('[data-spin]')?.disabled")
                    # Capture Russian ready evidence at every governed viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before localized ready-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                        # Require the localized route to remain visible and horizontally contained.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('big-six-wheel').is_visible()
                        # Require the complete localized ready stage before writing evidence.
                        assert_big_six_stage_complete(viewport_id)
                        # Record self-describing Russian ready evidence.
                        game_evidence(f'after-pass-big-six-ready-ru-{viewport_id}.png','big_six_wheel',['ready'],'ru-RU',viewport_id)
                    # Restore the unsent wager cleared by the full-page route reload.
                    page.locator('[data-wager="one"]').fill('1')
                    # Start one normal-motion Russian spin at primary desktop size.
                    page.set_viewport_size({'width':1920,'height':1080}); page.locator('[data-spin]').click(); page.wait_for_function("() => document.querySelector('[data-spin]')?.disabled === true",timeout=WAIT_MS)
                    # Record the localized active state before the route-owned timer settles.
                    game_evidence('after-pass-big-six-spinning-ru-desktop_primary.png','big_six_wheel',['spinning'],'ru-RU','desktop_primary')
                    # Resize during the same pending action and preserve the active-state mobile evidence.
                    page.set_viewport_size({'width':390,'height':844}); game_evidence('after-pass-big-six-spinning-ru-mobile.png','big_six_wheel',['spinning'],'ru-RU','mobile')
                    # Wait for the real backend result presentation to restore the spin action.
                    page.wait_for_function("() => document.querySelector('[data-spin]')?.disabled === false",timeout=WAIT_MS)
                    # Return to English before exercising the reduced-motion scheduler.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => document.querySelector('.big-six-wheel__header h1')?.textContent === 'Big Six Wheel'")
                    # Emulate the platform reduced-motion preference consumed by the mounted timer scope.
                    page.emulate_media(reduced_motion='reduce'); page.set_viewport_size({'width':1920,'height':1080})
                    # Start another real spin and require its zero-delay reveal to complete safely.
                    page.locator('[data-spin]').click(); page.wait_for_function("() => document.querySelector('[data-wheel]')?.dataset.reducedMotion === 'true' && document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Settled'",timeout=WAIT_MS)
                    # Record reduced-motion evidence with the terminal state and explicit route marker.
                    game_evidence('after-pass-big-six-reduced-motion-en-desktop_primary.png','big_six_wheel',['reduced_motion','settled'],'en-US','desktop_primary')
                    # Resize the same timer-clean result for required mobile reduced-motion evidence.
                    page.set_viewport_size({'width':390,'height':844}); game_evidence('after-pass-big-six-reduced-motion-en-mobile.png','big_six_wheel',['reduced_motion','settled'],'en-US','mobile')
                    # Restore normal media before proving canonical deep-link restoration.
                    page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size({'width':1920,'height':1080})
                    # Reload the canonical route and require the latest settled round to restore.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('big-six-wheel').wait_for(timeout=WAIT_MS); page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Accepting wagers'")
                    # Record exact-route restoration with live backend history visible.
                    game_evidence('after-pass-big-six-route-restored-en-desktop_primary.png','big_six_wheel',['route_restored','ready'],'en-US','desktop_primary')
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute Big Six rules, session route, localization, motion, responsive, and visual gates.
                run_case('BR-BIG-SIX-001',['BIG-SIX-001','BIG-SIX-002','BIG-SIX-004','BIG-SIX-005','BIG-SIX-006','TEST-065'],big_six_acceptance)
                # Define real-backend Red Dog browser, localization, responsive, state, and visual acceptance coverage.
                def red_dog_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-red_dog').click(); page.get_by_test_id('red-dog-table').wait_for(timeout=WAIT_MS)
                    # Require the canonical route, complete English title, and initial ready phase.
                    assert page.url.split('?',1)[0].endswith('/games/red_dog') and page.locator('.rd-header h1').inner_text()=='Red Dog' and page.locator('.rd-phase').inner_text()=='Accepting wagers'
                    # Define every named viewport required by the Red Dog visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Define a helper that captures one live state in both supported locales and every governed viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through the two complete game-owned locale domains.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale through the authenticated shared shell without discarding game state.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("locale => document.querySelector('[data-testid=\"shell-locale-select\"]')?.value === locale",arg=locale)
                            # Allow the asynchronous game-domain rerender to complete before visible-copy checks.
                            page.wait_for_timeout(100)
                            # Reject representative English game copy from every Russian evidence state.
                            if locale=='ru-RU':
                                # Read only the mounted Red Dog surface for locale ownership verification.
                                russian_copy=page.locator('.red-dog').inner_text()
                                # Name representative visible English resources that must never leak into Russian.
                                english_phrases=['Accepting wagers','Deal opening cards','Deal next round','Keep wager and draw','Match wager and draw','Table rules','play tokens','Round settled']
                                # Require the Russian game domain to replace every representative English phrase.
                                assert not [phrase for phrase in english_phrases if phrase.lower() in russian_copy.lower()],russian_copy
                            # Capture the current localized state at every exact visual-matrix dimension.
                            for viewport_id,width,height in required_viewports:
                                # Resize before horizontal containment and evidence checks.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Require the complete mounted table to stay visible without page-level horizontal overflow.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('red-dog-table').is_visible()
                                # Record self-describing after-pass evidence for this locale, state, and viewport.
                                game_evidence(f'after-pass-red-dog-{prefix}-{locale.lower()}-{viewport_id}.png','red_dog',states,locale,viewport_id)
                        # Restore English and primary desktop dimensions for deterministic control labels and actions.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready state in both locales and every required viewport.
                    localized_evidence('ready',['ready'])
                    # Track each probabilistic live-backend state required by the visual matrix.
                    spread_captured=False; pair_captured=False; consecutive_captured=False; third_captured=False
                    # Bound real shuffled-shoe attempts while retaining a vanishingly small miss probability.
                    for attempt in range(240):
                        # Start one real ledger-backed opening from the currently enabled terminal or ready state.
                        page.locator('[data-action="deal"]').click()
                        # Wait until either the spread decision or an automatically settled next-round action appears.
                        page.wait_for_function("() => { const decision=document.querySelector('[data-action=\"raise\"]'); const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean((decision && !decision.disabled) || (deal && !deal.disabled)); }",timeout=WAIT_MS)
                        # Read the session-bound public state to classify the real shuffled result without a test seam.
                        outcome=page.evaluate("async () => (await (await fetch('/api/v1/games/red-dog/state')).json()).data.state.rounds[0].outcome")
                        # Handle a normal spread before starting another opening.
                        if page.locator('[data-action="raise"]').count() and page.locator('[data-action="raise"]').is_enabled():
                            # Capture the unresolved spread decision once in both locales at all viewports.
                            if not spread_captured:
                                # Record the complete decision matrix while both public actions remain available.
                                localized_evidence('spread-decision',['spread_decision'])
                                # Mark the required decision state complete.
                                spread_captured=True
                            # Exercise the matching raise control on the first third-card flow and call thereafter.
                            decision='raise' if not third_captured else 'call'
                            # Complete the chosen real frontend action through its session-bound API route.
                            page.locator(f'[data-action="{decision}"]').click()
                            # Wait for terminal settlement to restore the next-round action.
                            page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }",timeout=WAIT_MS)
                            # Capture one terminal third-card result once in both locales and all viewports.
                            if not third_captured:
                                # Record the completed third-card matrix after the real matching raise.
                                localized_evidence('third-card-settled',['third_card_settled'])
                                # Mark the required third-card terminal state complete.
                                third_captured=True
                        # Capture either legal pair terminal outcome under the shared pair-settled matrix state.
                        elif outcome in ('pair_push','three_of_a_kind') and not pair_captured:
                            # Record the automatic pair settlement in both locales at all viewports.
                            localized_evidence('pair-settled',['pair_settled'])
                            # Mark the pair-state requirement complete.
                            pair_captured=True
                        # Capture the no-third-card consecutive push terminal outcome once.
                        elif outcome=='consecutive_push' and not consecutive_captured:
                            # Record the automatic consecutive push in both locales at all viewports.
                            localized_evidence('consecutive-push',['consecutive_push'])
                            # Mark the consecutive-state requirement complete.
                            consecutive_captured=True
                        # Stop the bounded search as soon as every governed live state has evidence.
                        if spread_captured and pair_captured and consecutive_captured and third_captured:
                            # Leave the search immediately after the full evidence set is complete.
                            break
                    # Require the shuffled real backend to have produced every governed Red Dog state.
                    assert spread_captured and pair_captured and consecutive_captured and third_captured,'Red Dog did not produce every required live state within 240 rounds'
                    # Reload the canonical deep link and require private terminal history to restore.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('red-dog-table').wait_for(timeout=WAIT_MS); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }")
                    # Capture route restoration in both locales and every governed viewport.
                    localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute Red Dog rules, session route, localization, responsive, and visual gates.
                run_case('BR-RD-001',['RD-001','RD-002','RD-004','RD-005'],red_dog_acceptance)
                # Define real-backend Dragon Tiger browser, localization, responsive, replay, and visual acceptance coverage.
                def dragon_tiger_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-dragon_tiger').click(); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=WAIT_MS)
                    # Wait for the session-bound initial state request to replace the intentional loading controls.
                    page.wait_for_function("() => document.querySelector('.dt-phase')?.textContent === 'Accepting wagers'",timeout=WAIT_MS)
                    # Require the canonical route, complete English title, and initial ready phase.
                    assert page.url.split('?',1)[0].endswith('/games/dragon_tiger') and page.locator('.dt-header h1').inner_text()=='Dragon Tiger' and page.locator('.dt-phase').inner_text()=='Accepting wagers'
                    # Define every named viewport required by the Dragon Tiger visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Define a helper that captures one registered live state in both supported locales and every governed viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through the two complete game and shell locale domains.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale through the authenticated shared shell without discarding game state.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("locale => document.querySelector('[data-testid=\"shell-locale-select\"]')?.value === locale",arg=locale)
                            # Allow the asynchronous game-domain and persistent-shell rerenders to complete.
                            page.wait_for_timeout(100)
                            # Verify the mounted game title belongs to the selected locale.
                            assert page.locator('.dt-header h1').inner_text()==('Dragon Tiger' if locale=='en-US' else 'Дракон — Тигр')
                            # Inspect shared-shell and game copy for the Russian acceptance gate.
                            if locale=='ru-RU':
                                # Read the persistent shell that remains visible in Dragon Tiger evidence.
                                shell_copy=page.get_by_test_id('premium-topbar').inner_text()+'\n'+page.get_by_test_id('shell-status').inner_text()
                                # Reject the exact hard-coded English shell phrases found in isolated evidence.
                                assert not [phrase for phrase in ('PLAY TOKEN BALANCE','Ledger-backed outcomes','Connected','All games use play tokens only') if phrase.lower() in shell_copy.lower()],shell_copy
                                # Require localized wallet, ledger, and connection text in the shared shell.
                                assert all(phrase.lower() in shell_copy.lower() for phrase in ('Баланс игровых токенов','Результаты записываются в журнал','Подключено'))
                                # Read only the mounted Dragon Tiger surface for locale ownership verification.
                                russian_copy=page.locator('.dragon-tiger').inner_text()
                                # Reject representative English game copy from every Russian evidence state.
                                assert not [phrase for phrase in ('Accepting wagers','Round settled','Deal cards','Deal next round','Table information','Recent rounds','play tokens') if phrase.lower() in russian_copy.lower()],russian_copy
                            # Capture the current localized state at every exact visual-matrix dimension.
                            for viewport_id,width,height in required_viewports:
                                # Resize before horizontal containment and active-route navigation checks.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Require the complete mounted table to stay visible without page-level horizontal overflow.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('dragon-tiger-table').is_visible()
                                # Measure the catalog navigation and its active Dragon Tiger route after responsive layout.
                                nav_bounds=page.evaluate("() => { const nav=document.querySelector('.casino-nav').getBoundingClientRect(); const active=document.querySelector('[data-testid=\"nav-dragon_tiger\"]').getBoundingClientRect(); return {nav:{left:nav.left,right:nav.right},active:{left:active.left,right:active.right},label:document.querySelector('[data-testid=\"nav-dragon_tiger\"]').textContent.trim()}; }")
                                # Require the complete localized active label and its bounds to remain inside the visible navigation.
                                assert nav_bounds['label']==('Dragon Tiger' if locale=='en-US' else 'Дракон и Тигр') and nav_bounds['active']['left']>=nav_bounds['nav']['left']-1 and nav_bounds['active']['right']<=nav_bounds['nav']['right']+1,nav_bounds
                                # Record self-describing after-pass evidence for this locale, state, and viewport.
                                game_evidence(f'after-pass-dragon-tiger-{prefix}-{locale.lower()}-{viewport_id}.png','dragon_tiger',states,locale,viewport_id)
                        # Restore English and primary desktop dimensions for deterministic control labels and actions.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready state in both locales and every required viewport.
                    localized_evidence('ready',['ready'])
                    # Execute one real frontend round through the registered session-bound handler.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.dt-phase')?.textContent === 'Round settled'",timeout=WAIT_MS)
                    # Capture the real settled table in both locales and every required viewport.
                    localized_evidence('settled',['settled'])
                    # Execute and replay one caller-stable public action to prove exactly-once behavior in the real browser session.
                    replay_result=page.evaluate("""async () => { const request={action_id:'browser-dragon-tiger-replay',bet:'tiger',wager:2}; const call=async()=>{ const response=await fetch('/api/v1/games/dragon-tiger/rounds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}); const payload=await response.json(); if(!payload.ok) throw new Error(payload.error?.message || 'Dragon Tiger replay failed'); return payload.data; }; const first=await call(); const replay=await call(); return {same:JSON.stringify(first.round)===JSON.stringify(replay.round),replayed:replay.replayed,sameBalance:first.player.balance===replay.player.balance}; }""")
                    # Require the retry response to preserve the exact result and wallet balance.
                    assert replay_result=={'same':True,'replayed':True,'sameBalance':True},replay_result
                    # Reload the game-owned state so the exact replay result is visible in the shared shell.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=WAIT_MS)
                    # Capture exact-replay evidence from the restored registered backend state.
                    localized_evidence('exact-replay',['exact_replay'])
                    # Search bounded real shuffled rounds for the governed Dragon/Tiger half-loss tie state.
                    tie_round=None
                    # Retain real entropy while making the approximately one-in-thirteen tie state effectively certain.
                    for attempt in range(200):
                        # Submit one public Dragon wager with a unique stable action identity.
                        candidate=page.evaluate("""async attempt => { const response=await fetch('/api/v1/games/dragon-tiger/rounds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:`browser-dragon-tiger-tie-${attempt}`,bet:'dragon',wager:2})}); const payload=await response.json(); if(!payload.ok) throw new Error(payload.error?.message || 'Dragon Tiger tie search failed'); return payload.data.round; }""",attempt)
                        # Retain the first legal tie half-loss result.
                        if candidate['winner']=='tie' and candidate['outcome']=='half_loss':
                            # Preserve the governed result for a bounded-search assertion.
                            tie_round=candidate
                            # Stop as soon as the required real-backend state exists.
                            break
                    # Require the registered shuffled backend to produce the tie state within the bounded search.
                    assert tie_round is not None,'Dragon Tiger did not produce a tie half-loss within 200 rounds'
                    # Reload so the newest tie result is mounted through the production state endpoint.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=WAIT_MS)
                    # Require visible state to match the retained tie and half-return settlement.
                    assert page.locator('.dt-stage h2').inner_text()=='The cards tie' and tie_round['total_return']==1 and tie_round['net']==-1
                    # Capture the real tie half-loss in both locales and every required viewport.
                    localized_evidence('tie-half-loss',['tie_half_loss'])
                    # Emulate the governed reduced-motion preference on the timer-free settled table.
                    page.emulate_media(reduced_motion='reduce')
                    # Capture reduced-motion evidence in both locales and every required viewport.
                    localized_evidence('reduced-motion',['reduced_motion'])
                    # Restore the default media preference for downstream browser cases.
                    page.emulate_media(reduced_motion='no-preference')
                    # Reload the canonical deep link and require private terminal history to restore.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=WAIT_MS)
                    # Capture route restoration in both locales and every governed viewport.
                    localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute Dragon Tiger rules, session route, localization, replay, responsive, and visual gates.
                run_case('BR-DT-001',['DT-001','DT-002','DT-004','DT-005'],dragon_tiger_acceptance)
                # Define real-backend Hi-Lo browser, localization, responsive, decision, and visual acceptance coverage.
                def hi_lo_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-hi_lo').click(); page.get_by_test_id('hi-lo').wait_for(timeout=WAIT_MS)
                    # Wait for the session-bound initial state request to replace the loading shell.
                    page.wait_for_function("() => document.querySelector('.hilo-phase')?.textContent === 'Ready to deal'",timeout=WAIT_MS)
                    # Require the canonical route, complete English title, and initial ready phase.
                    assert page.url.split('?',1)[0].endswith('/games/hi_lo') and page.locator('.hilo-header h1').inner_text()=='Hi-Lo' and page.locator('.hilo-phase').inner_text()=='Ready to deal'
                    # Require the exact authoritative range as two-decimal player-facing tokens.
                    hi_lo_rules=page.locator('.hilo-rules').inner_text(); assert '0.96x' in hi_lo_rules and '1.93x' in hi_lo_rules
                    # Define every named viewport required by the Hi-Lo visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Define a helper that captures one registered live state in both supported locales and every governed viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through the complete English and Russian game domains.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale through the authenticated shared shell without discarding game state.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("locale => document.querySelector('[data-testid=\"shell-locale-select\"]')?.value === locale",arg=locale)
                            # Allow the game-domain rerender to complete before reading localized copy.
                            page.wait_for_timeout(100)
                            # Verify the mounted game title belongs to the selected locale.
                            assert page.locator('.hilo-header h1').inner_text()==('Hi-Lo' if locale=='en-US' else 'Больше — меньше')
                            # Require the same exact server-owned price range in both governed locales.
                            localized_rules=page.locator('.hilo-rules').inner_text(); assert '0.96x' in localized_rules and '1.93x' in localized_rules,{'locale':locale,'rules':localized_rules}
                            # Inspect the mounted Russian game for representative English-copy leakage.
                            if locale=='ru-RU':
                                # Read only the game-owned surface so shell brand names do not create false positives.
                                russian_copy=page.locator('.hilo-shell').inner_text()
                                # Reject representative English game labels from every Russian evidence state.
                                assert not [phrase for phrase in ('Ready to deal','Choose higher or lower','Correct prediction','Round complete','Wager returned','Deal opening card','Play controls','Recent rounds','play tokens') if phrase.lower() in russian_copy.lower()],russian_copy
                            # Capture the current localized state at every exact visual-matrix dimension.
                            for viewport_id,width,height in required_viewports:
                                # Resize before horizontal containment and active-route navigation checks.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Require the complete mounted table to stay visible without page-level horizontal overflow.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('hi-lo').is_visible()
                                # Measure the catalog navigation and its active Hi-Lo route after responsive layout.
                                nav_bounds=page.evaluate("() => { const nav=document.querySelector('.casino-nav').getBoundingClientRect(); const activeElement=document.querySelector('[data-testid=\"nav-hi_lo\"]'); const active=activeElement.getBoundingClientRect(); return {nav:{left:nav.left,right:nav.right},active:{left:active.left,right:active.right},label:activeElement.textContent.trim()}; }")
                                # Require the localized active label and its bounds to remain inside the visible navigation.
                                assert nav_bounds['label']==('Hi-Lo' if locale=='en-US' else 'Больше или меньше') and nav_bounds['active']['left']>=nav_bounds['nav']['left']-1 and nav_bounds['active']['right']<=nav_bounds['nav']['right']+1,nav_bounds
                                # Record self-describing after-pass evidence for this locale, state, and viewport.
                                game_evidence(f'after-pass-hi-lo-{prefix}-{locale.lower()}-{viewport_id}.png','hi_lo',states,locale,viewport_id)
                        # Restore English and primary desktop dimensions for deterministic controls and API searches.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready state in both locales and every required viewport.
                    localized_evidence('ready',['ready'])
                    # Deal one real opening card through the mounted frontend control.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.hilo-phase')?.textContent === 'Choose higher or lower'",timeout=WAIT_MS)
                    # Require the protected next card and both documented choice controls during the active decision.
                    assert page.get_by_text('Face-down playing card',exact=True).count()==0 and page.locator('[data-guess="higher"]').is_enabled() and page.locator('[data-guess="lower"]').is_enabled()
                    # Read the active card and its authoritative price through the same authenticated frozen-v1 response.
                    active_price=page.evaluate("""async () => { const payload=await (await fetch('/api/v1/games/hi-lo/state')).json(); if(!payload.ok) throw new Error(payload.error?.message || 'Hi-Lo state failed'); const card=payload.data.state.active_round.current_card; return payload.data.rules.correct_paytable[card.slice(0,-1)]; }""")
                    # Require the visible decision copy to show that exact server price with two decimal places.
                    assert f'{active_price:.2f}x' in page.get_by_test_id('hi-lo-current-return').inner_text()
                    # Capture the higher-or-lower choice state in both locales and every required viewport.
                    localized_evidence('choose',['choose_higher_or_lower','rank_priced_choice'])
                    # Complete the mounted choice so later direct public actions start without an active-round conflict.
                    page.locator('[data-guess="higher"]').click(); page.wait_for_function("() => !['Choose higher or lower',''].includes(document.querySelector('.hilo-phase')?.textContent || '')",timeout=WAIT_MS)
                    # Define a bounded real-backend search for one documented settlement class.
                    def find_outcome(target):
                        # Retain real entropy while giving the one-in-thirteen tie state ample opportunity.
                        for attempt in range(240):
                            # Deal and settle one public session-bound round without any test-only seed seam.
                            result=page.evaluate("""async ({target,attempt}) => { const call=async(path,body)=>{ const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const payload=await response.json(); if(!payload.ok) throw new Error(payload.error?.message || 'Hi-Lo evidence action failed'); return payload.data; }; const deal=await call('/api/v1/games/hi-lo/rounds',{action_id:`browser-hi-lo-${target}-${attempt}-deal`,wager:1}); return await call(`/api/v1/games/hi-lo/rounds/${encodeURIComponent(deal.round.round_id)}/guesses`,{action_id:`browser-hi-lo-${target}-${attempt}-guess`,guess:'higher'}); }""",{'target':target,'attempt':attempt})
                            # Return immediately when the registered shuffled backend produces the requested class.
                            if result['round']['outcome']==target:
                                # Preserve the exact terminal round and authoritative rule table for payout assertions.
                                return result
                        # Fail the browser case if the bounded real-backend search never reaches the governed state.
                        raise AssertionError(f'Hi-Lo did not produce {target} within 240 rounds')
                    # Find and mount one real correct prediction.
                    correct_result=find_outcome('correct'); correct_round=correct_result['round']; page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=WAIT_MS)
                    # Select the exact total-return price published for the visible current-card rank.
                    correct_price=correct_result['rules']['correct_paytable'][correct_round['current_card'][:-1]]
                    # Require ledger-rounded rank pricing before recording correct-result evidence.
                    assert correct_round['payout']==round(correct_round['wager']*correct_price,2) and correct_round['net']==round(correct_round['payout']-correct_round['wager'],2)
                    # Capture correct prediction evidence in both locales and every required viewport.
                    localized_evidence('correct',['correct_guess'])
                    # Find and mount one real incorrect prediction.
                    incorrect_round=find_outcome('incorrect')['round']; page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=WAIT_MS)
                    # Require the documented zero return before recording incorrect-result evidence.
                    assert incorrect_round['payout']==0 and incorrect_round['net']==-incorrect_round['wager']
                    # Capture incorrect prediction evidence in both locales and every required viewport.
                    localized_evidence('incorrect',['incorrect_guess'])
                    # Find and mount one real equal-rank refund.
                    tie_round=find_outcome('tie')['round']; page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=WAIT_MS)
                    # Require the documented 1x refund and zero net before recording tie evidence.
                    assert tie_round['payout']==tie_round['wager'] and tie_round['net']==0
                    # Capture equal-rank refund evidence in both locales and every required viewport.
                    localized_evidence('tie-refund',['tie_refund'])
                    # Emulate the governed reduced-motion preference on the timer-free terminal table.
                    page.emulate_media(reduced_motion='reduce')
                    # Capture reduced-motion evidence in both locales and every required viewport.
                    localized_evidence('reduced-motion',['reduced_motion'])
                    # Restore the default media preference for downstream browser cases.
                    page.emulate_media(reduced_motion='no-preference')
                    # Reload the canonical deep link and require private terminal history to restore.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=WAIT_MS)
                    # Capture route restoration in both locales and every governed viewport.
                    localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute Hi-Lo rules, session route, localization, responsive, and visual gates.
                run_case('BR-HILO-001',['HILO-001','HILO-002','HILO-004','HILO-005'],hi_lo_acceptance)
                # Define real-backend Three Card Poker localization, responsive, decision, and visual acceptance.
                def three_card_poker_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-three_card_poker').click(); page.get_by_test_id('three-card-poker').wait_for(timeout=WAIT_MS)
                    # Define every viewport governed by the Three Card Poker visual row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one mounted state in both supported locales and every governed viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Resolve the exact locale-owned heading before requesting the asynchronous switch.
                            expected_title='Three Card Poker' if locale=='en-US' else 'Трёхкарточный покер'
                            # Switch locale without discarding the active route or private state.
                            page.get_by_test_id('shell-locale-select').select_option(locale)
                            # Wait for installed game resources to repaint instead of assuming a fixed network duration.
                            page.wait_for_function("(expected) => document.querySelector('.tcp-header h1')?.textContent === expected",arg=expected_title,timeout=WAIT_MS)
                            # Require the localized title instead of a key or fallback.
                            assert page.locator('.tcp-header h1').inner_text()==expected_title
                            # Capture every registered matrix dimension after checking containment.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact governed viewport.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject page-level overflow and require the complete game surface.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('three-card-poker').is_visible()
                                # Record self-describing after-pass evidence.
                                game_evidence(f'after-pass-three-card-poker-{prefix}-{locale.lower()}-{viewport_id}.png','three_card_poker',states,locale,viewport_id)
                        # Restore English desktop controls for the next deterministic action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready table before placing a wager.
                    localized_evidence('ready',['ready'])
                    # Deal through the frontend and require hidden dealer cards during the decision.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Decision required'",timeout=WAIT_MS); assert page.locator('[aria-label="Face-down playing card"]').count()==3
                    # Capture the actionable decision.
                    localized_evidence('decision',['decision'])
                    # Complete one real Play action and capture the real shuffled terminal state.
                    page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Round settled'",timeout=WAIT_MS); terminal=page.locator('.tcp-stage-head h2').inner_text().lower(); terminal_state='dealer_not_qualified' if 'qualify' in terminal else ('player_win' if 'win' in terminal else 'dealer_win'); localized_evidence(terminal_state,[terminal_state])
                    # Complete a second real round through Fold and capture reduced-motion rendering.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Decision required'",timeout=WAIT_MS); page.locator('[data-action="fold"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Round settled'",timeout=WAIT_MS); localized_evidence('folded',['folded']); page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference')
                    # Reload the deep link and capture restored terminal history.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('three-card-poker').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute Three Card Poker rules, route, localization, responsive, and visual gates.
                run_case('BR-TCP-001',['TCP-001','TCP-002','TCP-004','TCP-005'],three_card_poker_acceptance)
                # Define real-backend Jacks or Better localization, responsive, hold, draw, and visual acceptance.
                def jacks_or_better_acceptance():
                    # Open the catalog route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-jacks_or_better_video_poker').click(); page.get_by_test_id('jacks-or-better-video-poker').wait_for(timeout=WAIT_MS)
                    # Define every viewport governed by the visual matrix.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one mounted state in both locales and all viewports.
                    def localized_evidence(prefix,states):
                        # Iterate through complete English and Russian resource domains.
                        for locale in ('en-US','ru-RU'):
                            # Switch the shared locale while preserving the private hand.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require a real localized title rather than a fallback key.
                            assert page.locator('.jobvp-header h1').inner_text()==('Jacks or Better Video Poker' if locale=='en-US' else 'Видеопокер «Валеты или старше»')
                            # Capture exact matrix dimensions after containment checks.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the registered viewport.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the complete mounted game.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('jacks-or-better-video-poker').is_visible()
                                # Record self-describing after-pass evidence.
                                game_evidence(f'after-pass-jacks-or-better-{prefix}-{locale.lower()}-{viewport_id}.png','jacks_or_better_video_poker',states,locale,viewport_id)
                        # Restore English desktop controls for the next action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready machine before wagering.
                    localized_evidence('ready',['ready'])
                    # Deal through the mounted frontend and require five selectable cards.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.jobvp-phase')?.textContent === 'Choose cards to hold'",timeout=WAIT_MS); assert page.locator('.jobvp-card-button').count()==5
                    # Select one hold and capture the actionable phase.
                    page.locator('.jobvp-card-button').first.click(); localized_evidence('choose-holds',['choose_holds'])
                    # Draw through the public frontend and capture the real terminal result.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('jobvp-result').wait_for(timeout=WAIT_MS); settled_state='winning_hand' if page.locator('.jobvp-phase').inner_text()=='Winning hand' else 'losing_hand'; localized_evidence(settled_state,[settled_state])
                    # Capture reduced-motion and route-restored terminal states.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('jacks-or-better-video-poker').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Jacks or Better browser and visual gate.
                run_case('BR-JOBVP-001',['JOBVP-001','JOBVP-002','JOBVP-004','JOBVP-005'],jacks_or_better_acceptance)
                # Define real-backend Deuces Wild localization, responsive, hold, draw, and visual acceptance.
                def deuces_wild_acceptance():
                    # Open the catalog route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-deuces_wild_video_poker').click(); page.get_by_test_id('deuces-wild-video-poker').wait_for(timeout=WAIT_MS)
                    # Define every viewport governed by the visual matrix.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture the mounted state in both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through English and Russian resource domains.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the private hand.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require a real localized title instead of a fallback key.
                            assert page.locator('.dwvp-header h1').inner_text()==('Deuces Wild Video Poker' if locale=='en-US' else 'Видеопокер «Двойки — дикие»')
                            # Capture exact registered dimensions after containment checks.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the governed viewport.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject page overflow and require the complete mounted game.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('deuces-wild-video-poker').is_visible()
                                # Record self-describing after-pass evidence.
                                game_evidence(f'after-pass-deuces-wild-{prefix}-{locale.lower()}-{viewport_id}.png','deuces_wild_video_poker',states,locale,viewport_id)
                        # Restore English desktop controls for the next action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready table before wagering.
                    localized_evidence('ready',['ready'])
                    # Deal through the frontend and require five selectable cards.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.dwvp-phase')?.textContent === 'Choose cards to hold'",timeout=WAIT_MS); assert page.locator('.dwvp-card-button').count()==5
                    # Hold one card and capture the actionable state.
                    page.locator('.dwvp-card-button').first.click(); localized_evidence('choose-holds',['choose_holds'])
                    # Draw and capture the real terminal result.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('dwvp-summary').wait_for(timeout=WAIT_MS); settled_state='winning_hand' if page.locator('.dwvp-phase').inner_text()=='Winning hand' else 'losing_hand'; localized_evidence(settled_state,[settled_state])
                    # Capture reduced motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('deuces-wild-video-poker').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Deuces Wild browser and visual gate.
                run_case('BR-DWVP-001',['DWVP-001','DWVP-002','DWVP-004','DWVP-005'],deuces_wild_acceptance)
                # Define real-backend Scratch Cards localization, reveal, responsive, and route acceptance.
                def scratch_cards_acceptance():
                    # Open the catalog-owned route and wait for its stable readiness selector.
                    page.get_by_test_id('nav-scratch_cards').click(); page.get_by_test_id('scratch-cards').wait_for(timeout=WAIT_MS)
                    # Enumerate every governed viewport for both required locales.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one real mounted state across locales and viewports.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the private card.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game-owned title rather than a resource key.
                            assert page.locator('.scratch-header h1').inner_text()==('Scratch Cards' if locale=='en-US' else 'Скретч-карты')
                            # Validate containment and capture after-pass evidence at each viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the governed matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted surface.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('scratch-cards').is_visible()
                                # Record self-describing evidence for this exact state and viewport.
                                game_evidence(f'after-pass-scratch-cards-{prefix}-{locale.lower()}-{viewport_id}.png','scratch_cards',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the ready surface before wagering.
                    localized_evidence('ready',['ready'])
                    # Start one card and require all nine covered cells.
                    page.locator('[data-action="start"]').click(); page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-covered').length === 9",timeout=WAIT_MS)
                    # Reveal one cell through the mounted real backend and capture partial progress.
                    page.get_by_test_id('scratch-cell-0').click(); page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-revealed').length === 1",timeout=WAIT_MS); localized_evidence('revealing',['revealing'])
                    # Reveal the remaining cells and classify the actual terminal outcome.
                    page.locator('[data-action="reveal-all"]').click(); page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-revealed').length === 9",timeout=WAIT_MS); settled_state='settled_win' if 'Payout:' in page.locator('.scratch-result').inner_text() else 'settled_no_win'; localized_evidence(settled_state,[settled_state])
                    # Capture reduced motion and canonical reload restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('scratch-cards').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Scratch Cards browser and visual gate.
                run_case('BR-SCRATCH-001',['SCRATCH-001','SCRATCH-002','SCRATCH-004','SCRATCH-005'],scratch_cards_acceptance)
                # Define real-backend Sic Bo localization, wager, responsive, motion, and route acceptance.
                def sic_bo_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-sic_bo').click(); page.get_by_test_id('sic-bo-table').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding selected wagers or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key.
                            assert page.locator('.sb-header h1').inner_text()==('Sic Bo' if locale=='en-US' else 'Сик Бо')
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('sic-bo-table').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-sic-bo-{prefix}-{locale.lower()}-{viewport_id}.png','sic_bo',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before selecting a wager.
                    localized_evidence('ready',['ready'])
                    # Select one canonical position and capture the visible selected state.
                    page.locator('[data-bet-id="small"]').click(); assert page.locator('[data-bet-id="small"]').get_attribute('aria-pressed')=='true'; localized_evidence('wagers-selected',['wagers_selected'])
                    # Start the public round and capture the decorative server-wait phase at desktop.
                    page.locator('[data-action="shake"]').click(); page.locator('.sb-dice-tray.is-rolling').wait_for(timeout=WAIT_MS); game_evidence('after-pass-sic-bo-rolling-en-us-desktop_primary.png','sic_bo',['rolling'],'en-US','desktop_primary')
                    # Wait for the authoritative settled dice and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelectorAll('.sb-die:not(.is-rolling)').length === 3 && document.querySelector('.sb-result-grid')",timeout=WAIT_MS * 2); localized_evidence('settled',['settled'])
                    # Capture reduced-motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('sic-bo-table').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Sic Bo browser and visual gate.
                run_case('BR-SIC-BO-001',['SIC-BO-001','SIC-BO-002','SIC-BO-004','SIC-BO-005'],sic_bo_acceptance)
                # Define real-backend Chuck-a-Luck localization, wager, responsive, motion, and route acceptance.
                def chuck_a_luck_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-chuck_a_luck').click(); page.get_by_test_id('chuck-a-luck').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding wagers or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key.
                            assert page.locator('.cal-header h1').inner_text()==('Chuck-a-Luck' if locale=='en-US' else 'Чак-а-лак')
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('chuck-a-luck').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-chuck-a-luck-{prefix}-{locale.lower()}-{viewport_id}.png','chuck_a_luck',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before choosing a face wager.
                    localized_evidence('ready',['ready'])
                    # Enter one canonical face wager and require the aggregate amount to become actionable.
                    page.locator('[data-wager="one"]').fill('1'); assert not page.locator('[data-roll]').is_disabled()
                    # Start the public roll and capture the decorative server-wait phase at desktop.
                    page.locator('[data-roll]').click(); page.locator('[data-testid="chuck-a-luck"][data-phase="rolling"]').wait_for(timeout=WAIT_MS); game_evidence('after-pass-chuck-a-luck-rolling-en-us-desktop_primary.png','chuck_a_luck',['rolling'],'en-US','desktop_primary')
                    # Wait for the authoritative settled dice and capture both locales and all viewports.
                    page.locator('[data-testid="chuck-a-luck"][data-phase="settled"]').wait_for(timeout=WAIT_MS * 2); assert page.locator('[data-die]:not(.is-rolling)').count()==3; localized_evidence('settled',['settled'])
                    # Capture reduced-motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('chuck-a-luck').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Chuck-a-Luck browser and visual gate.
                run_case('BR-CHUCK-001',['CHUCK-001','CHUCK-002','CHUCK-004','CHUCK-005'],chuck_a_luck_acceptance)
                # Define real-backend Craps localization, point-play, responsive, motion, and route acceptance.
                def craps_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-craps').click(); page.get_by_test_id('craps').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active or settled round.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key.
                            assert page.locator('.craps-header h1').inner_text()==('Craps' if locale=='en-US' else 'Крэпс')
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('craps').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-craps-{prefix}-{locale.lower()}-{viewport_id}.png','craps',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Roll once and wait for durable server-owned progress before presentation settles.
                    def roll_and_wait_for_commit():
                        # Capture the committed roll count so the wait cannot pass on pre-click markup.
                        prior_roll_count=int(page.locator('.craps-metrics .craps-metric').nth(3).locator('strong').inner_text().replace(',',''))
                        # Trigger the same public roll action exercised by a player.
                        page.get_by_test_id('craps-roll').click()
                        # Require the rendered server-owned round to contain one additional committed roll.
                        page.wait_for_function("prior => Number(document.querySelectorAll('.craps-metrics .craps-metric strong')[3]?.textContent.replace(/[^0-9.-]/g, '')) > prior",arg=prior_roll_count,timeout=WAIT_MS * 2)
                        # Wait for decorative frames to finish before inspecting point or terminal state.
                        page.wait_for_function("() => !document.querySelector('.craps-die.is-rolling')",timeout=WAIT_MS * 2)
                    # Capture the complete ready table before committing a line wager.
                    localized_evidence('ready',['ready'])
                    # Start one Pass Line round and capture its committed come-out state.
                    page.get_by_test_id('craps-bet-type').select_option('pass_line'); page.get_by_test_id('craps-wager').fill('1'); page.get_by_test_id('craps-wager').press('Tab'); page.get_by_test_id('craps-start').click(); page.get_by_test_id('craps-roll').wait_for(timeout=WAIT_MS); localized_evidence('come-out',['come_out'])
                    # Roll bounded rounds until one server result establishes an actual point.
                    point_found=False
                    # Use enough independent come-out attempts to make random non-establishment negligible.
                    for attempt in range(40):
                        # Roll the currently committed come-out action.
                        roll_and_wait_for_commit()
                        # Stop when the authoritative round exposes a point puck and remains actionable.
                        if page.locator('[data-testid="craps-point"].is-on').count() and page.get_by_test_id('craps-roll').count(): point_found=True; break
                        # Start another small round after an immediate come-out settlement.
                        page.get_by_test_id('craps-start').wait_for(timeout=WAIT_MS); page.get_by_test_id('craps-wager').fill('1'); page.get_by_test_id('craps-wager').press('Tab'); page.get_by_test_id('craps-start').click(); page.get_by_test_id('craps-roll').wait_for(timeout=WAIT_MS)
                    # Require real point play rather than accepting only immediate come-out outcomes.
                    assert point_found
                    # Capture the active point across both locales and all governed viewports.
                    localized_evidence('point-active',['point_active'])
                    # Continue public rolls until the point repeats or seven settles the round.
                    for roll_index in range(200):
                        # Stop after the frontend returns to the next-round action.
                        if page.get_by_test_id('craps-start').count(): break
                        # Advance the active point through one server-authoritative action.
                        roll_and_wait_for_commit()
                    # Require a terminal settled round and capture it across both locales and all viewports.
                    page.get_by_test_id('craps-start').wait_for(timeout=WAIT_MS); localized_evidence('settled',['settled'])
                    # Capture reduced-motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('craps').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Craps browser and visual gate.
                run_case('BR-CRAPS-001',['CRAPS-001','CRAPS-002','CRAPS-004','CRAPS-005'],craps_acceptance)
                # Define real-backend Crown and Anchor localization, wager, responsive, motion, and route acceptance.
                def crown_and_anchor_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-crown_and_anchor').click(); page.get_by_test_id('crown-and-anchor').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'crown_and_anchor.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding wagers or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key.
                            assert page.locator('.crown-anchor__header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Probe every non-control theater node against the route-owned stage after responsive layout settles.
                                stage_failures=page.evaluate("""() => { const stage=document.querySelector('.crown-anchor__stage'); const selectors=['[data-die="0"]','[data-die="1"]','[data-die="2"]','[data-symbol="crown"]','[data-symbol="anchor"]','[data-symbol="heart"]','[data-symbol="diamond"]','[data-symbol="club"]','[data-symbol="spade"]']; if(!stage)return['stage']; const owner=stage.getBoundingClientRect(); return selectors.filter(selector=>{ const node=document.querySelector(selector); if(!node)return true; const style=getComputedStyle(node); const rect=node.getBoundingClientRect(); const painted=node.getClientRects().length&&style.display!=='none'&&style.visibility!=='hidden'&&rect.width>0&&rect.height>0; const contained=rect.left>=owner.left-1&&rect.right<=owner.right+1&&rect.top>=owner.top-1&&rect.bottom<=owner.bottom+1; return !painted||!contained; }); }""")
                                # Reject a missing, unpainted, or escaped die/result panel before labeling this viewport after-pass.
                                assert not stage_failures,f'Crown and Anchor stage incomplete at {viewport_id}: {stage_failures}'
                                # Reject horizontal overflow and require the mounted table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('crown-and-anchor').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-crown-and-anchor-{prefix}-{locale.lower()}-{viewport_id}.png','crown_and_anchor',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before choosing a symbol wager.
                    localized_evidence('ready',['ready'])
                    # Enter one canonical symbol wager and start the real-backend round.
                    page.locator('[data-wager="crown"]').fill('1'); page.locator('[data-play]').click()
                    # Capture the committed dice reveal while its managed timer remains active.
                    page.locator('.crown-anchor__die[data-rolling="true"]').first.wait_for(timeout=WAIT_MS); game_evidence('after-pass-crown-and-anchor-rolling-en-us-desktop_primary.png','crown_and_anchor',['rolling'],'en-US','desktop_primary')
                    # Wait for authoritative settlement and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"crown-and-anchor-phase\"]')?.textContent === 'Settled'",timeout=WAIT_MS * 2); assert page.locator('.crown-anchor__die[data-rolling="false"]').count()==3; localized_evidence('settled',['settled'])
                    # Commit another real round under reduced motion and require the presentation flag.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-wager="anchor"]').fill('1'); page.locator('[data-play]').click(); page.locator('.crown-anchor__die[data-reduced-motion="true"]').first.wait_for(timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and capture restored private history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('crown-and-anchor').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Crown and Anchor browser and visual gate.
                run_case('BR-CAA-001',['CAA-001','CAA-002','CAA-004','CAA-005'],crown_and_anchor_acceptance)
                # Define real-backend Over/Under 7 localization, wager, responsive, motion, and route acceptance.
                def over_under_7_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-over_under_7').click(); page.get_by_test_id('over-under-7').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'over_under_7.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding wagers or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.ou7-header h1').inner_text()==expected_titles[locale]
                            # Prove the wager list and paytable share one canonical net-odds convention with matching numbers. (issue #255)
                            ou7_net_suffix=read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'over_under_7.json')['odds.net'].split('{odds}')[1]
                            ou7_payrows=[cell.strip() for cell in page.locator('.ou7-payrow').all_inner_texts()]
                            ou7_betrows=[cell.strip() for cell in page.locator('.ou7-bet').all_inner_texts()]
                            # Require rendered rows on both surfaces and reject unresolved localization placeholders.
                            assert ou7_payrows and ou7_betrows and all('{' not in cell for cell in ou7_payrows+ou7_betrows)
                            # Every paytable row must advertise the net convention drawn from the paired resource file, retiring the total-return multiplier copy.
                            assert all(ou7_net_suffix in cell for cell in ou7_payrows)
                            # The net odds numbers on the paytable must match the wager-list odds exactly across the localized surfaces.
                            assert re.findall(r'(\d+):1',' '.join(ou7_payrows)) and sorted(re.findall(r'(\d+):1',' '.join(ou7_payrows)))==sorted(re.findall(r'(\d+):1',' '.join(ou7_betrows)))
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('over-under-7').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-over-under-7-{prefix}-{locale.lower()}-{viewport_id}.png','over_under_7',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before choosing a proposition wager.
                    localized_evidence('ready',['ready'])
                    # Enter one under-seven wager and start the real-backend dice play.
                    page.locator('[data-wager="under"]').fill('1'); page.locator('[data-play]').click()
                    # Capture the managed dice-reveal phase at the primary desktop viewport.
                    page.locator('.ou7-die.rolling').first.wait_for(timeout=WAIT_MS); game_evidence('after-pass-over-under-7-rolling-en-us-desktop_primary.png','over_under_7',['rolling'],'en-US','desktop_primary')
                    # Wait for authoritative settlement and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"over-under-7-phase\"]')?.textContent === 'Settled'",timeout=WAIT_MS * 2); assert page.locator('.ou7-die:not(.rolling)').count()==2; localized_evidence('settled',['settled'])
                    # Commit another real play under reduced motion and capture its stable result.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-wager="over"]').fill('1'); page.locator('[data-play]').click(); page.locator('[data-play]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('over-under-7').wait_for(timeout=WAIT_MS); assert page.locator('.ou7-history-row').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Over/Under 7 browser and visual gate.
                run_case('BR-OU7-001',['OU7-001','OU7-002','OU7-004','OU7-005','OU7-006','TEST-067'],over_under_7_acceptance)
                # Define real-backend Plinko localization, drop, responsive, motion, and route acceptance.
                def plinko_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-plinko').click(); page.get_by_test_id('plinko').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'plinko.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding wager or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.plinko-header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted pegboard.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('plinko').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-plinko-{prefix}-{locale.lower()}-{viewport_id}.png','plinko',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the first wagered drop.
                    localized_evidence('ready',['ready'])
                    # Enter one wager and start the real-backend committed-path replay.
                    page.locator('#plinko-wager').fill('2'); page.locator('[data-action="drop"]').click(); page.locator('.plinko-puck').wait_for(timeout=WAIT_MS * 2)
                    # Capture the server-owned path replay at the primary desktop viewport.
                    assert len(page.locator('.plinko-puck').get_attribute('data-path'))==8; game_evidence('after-pass-plinko-path-replay-en-us-desktop_primary.png','plinko',['path_replay'],'en-US','desktop_primary')
                    # Capture the settled drop across both locales and every viewport.
                    localized_evidence('settled',['settled'])
                    # Commit another real drop under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('#plinko-wager').fill('3'); page.locator('[data-action="drop"]').click(); page.wait_for_function("() => document.querySelectorAll('.plinko-history-list li').length >= 2",timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('plinko').wait_for(timeout=WAIT_MS); assert page.locator('.plinko-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Plinko browser and visual gate.
                run_case('BR-PLINKO-001',['PLINKO-001','PLINKO-002','PLINKO-004','PLINKO-005'],plinko_acceptance)
                # Define real-backend Fan-Tan localization, counting, responsive, motion, and route acceptance.
                def fan_tan_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-fan_tan').click(); page.get_by_test_id('fan-tan').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'fan_tan.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding wagers or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.fan-tan__header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted counted-pile table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('fan-tan').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-fan-tan-{prefix}-{locale.lower()}-{viewport_id}.png','fan_tan',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before choosing a residue wager.
                    localized_evidence('ready',['ready'])
                    # Enter one residue wager and start the real-backend counted-pile round.
                    page.locator('[data-wager="1"]').fill('1'); page.locator('[data-play]').click()
                    # Capture the managed counting phase at the primary desktop viewport.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"fan-tan-phase\"]')?.textContent === 'Counting groups of four'",timeout=WAIT_MS); game_evidence('after-pass-fan-tan-counting-en-us-desktop_primary.png','fan_tan',['counting'],'en-US','desktop_primary')
                    # Wait for authoritative settlement and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"fan-tan-phase\"]')?.textContent === 'Round settled'",timeout=WAIT_MS * 2); assert page.locator('.fan-tan__history-row').count()>=1; localized_evidence('settled',['settled'])
                    # Commit another real round under reduced motion and require the presentation flag.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-wager="4"]').fill('1'); page.locator('[data-play]').click(); page.locator('[data-play]:not([disabled])').wait_for(timeout=WAIT_MS * 2); assert page.locator('.fan-tan__tray').get_attribute('data-reduced-motion')=='true'; localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('fan-tan').wait_for(timeout=WAIT_MS); assert page.locator('.fan-tan__history-row').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Fan-Tan browser and visual gate.
                run_case('BR-FAN-TAN-001',['FAN-TAN-001','FAN-TAN-002','FAN-TAN-004','FAN-TAN-005'],fan_tan_acceptance)
                # Define the lost-response idempotency regression proving a retry replays one identity and body with exactly one debit. (issue #261)
                def fan_tan_lost_response_idempotency():
                    # Open the Fan-Tan route and wait for the stable game surface.
                    page.get_by_test_id('nav-fan_tan').click(); page.get_by_test_id('fan-tan').wait_for(timeout=WAIT_MS)
                    # Read the authenticated player id for exact ledger assertions.
                    ft_me=page.request.get(base+'/api/v2/me').json()['data']; ft_player=ft_me['player']['player_id']
                    # Count existing Fan-Tan wager debits so the regression measures only this intended round.
                    ft_before=page.request.get(base+f'/api/v1/players/{ft_player}/ledger').json()['data']['ledger']; ft_debits_before=sum(1 for r in ft_before if r.get('game')=='fan_tan' and r.get('transaction_type')=='FAN_TAN_WAGER_DEBIT')
                    # Install a fetch wrapper that records round request bodies and simulates one lost response after the backend commits.
                    page.evaluate("""() => { const original=window.fetch.bind(window); let firstHeld=false; window.__ftRequests=[]; window.fetch=async (...args)=>{ const input=args[0]; const url=typeof input==='string'?input:input.url; const init=args[1]||{}; const method=String(init.method||(typeof input==='object'?input.method:'GET')||'GET').toUpperCase(); if(url.includes('/api/v1/games/fan-tan/rounds')&&method==='POST'){ let body=null; try{ body=JSON.parse(init.body); }catch(_){} window.__ftRequests.push(body); if(!firstHeld){ firstHeld=true; try{ await original(...args); }catch(_){} throw new TypeError('simulated lost response'); } } return original(...args); }; }""")
                    # Set a residue wager through the visible control.
                    page.locator('[data-wager="1"]').fill('5')
                    # Submit the play; the backend commits while the browser sees a simulated lost response.
                    page.locator('[data-play]').click()
                    # Wait for the ambiguous-failure recovery to re-enable the play control.
                    page.locator('[data-play]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                    # Retry the play through the same visible control; the wager stays locked to the pending snapshot.
                    page.locator('[data-play]').click()
                    # Wait for settlement to complete and the control to re-enable.
                    page.locator('[data-play]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                    # Read both captured round request bodies.
                    ft_reqs=page.evaluate('window.__ftRequests')
                    # Prove the retry reused the exact same idempotency identity and immutable wager body.
                    assert len(ft_reqs)>=2 and ft_reqs[0]['action_id']==ft_reqs[1]['action_id'] and ft_reqs[0]['wagers']==ft_reqs[1]['wagers']
                    # Prove the intended round was charged exactly once despite the lost-response retry.
                    ft_after=page.request.get(base+f'/api/v1/players/{ft_player}/ledger').json()['data']['ledger']; ft_debits_after=sum(1 for r in ft_after if r.get('game')=='fan_tan' and r.get('transaction_type')=='FAN_TAN_WAGER_DEBIT'); assert ft_debits_after==ft_debits_before+1
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the lost-response idempotency regression for Fan-Tan. (issue #261)
                run_case('BR-FAN-TAN-IDEMPOTENCY-001',['LEDGER-028','TEST-070'],fan_tan_lost_response_idempotency)
                # Define real-backend Andar Bahar localization, responsive, motion, and route acceptance.
                def andar_bahar_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-andar_bahar').click(); page.get_by_test_id('andar-bahar').wait_for(timeout=WAIT_MS)
                    # Require both authoritative prices as exact two-decimal visible English tokens before evidence.
                    andar_rules=page.locator('.andar-rules').inner_text(); assert '1.90x' in andar_rules and '2.00x' in andar_rules
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'andar_bahar.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding wager choice or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.andar-header h1').inner_text()==expected_titles[locale]
                            # Require exact owner-approved price tokens in both governed locale renderings.
                            localized_rules=page.locator('.andar-rules').inner_text(); assert '1.90x' in localized_rules and '2.00x' in localized_rules,{'locale':locale,'rules':localized_rules}
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted rank-match table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('andar-bahar').is_visible()
                                # Measure the fixed feedback affordance and shell wallet against game-owned visible content.
                                clearance=page.evaluate("""() => { const root=document.querySelector('[data-testid="andar-bahar"]'); const feedback=document.querySelector('.report-problem-fab:not([hidden])')?.getBoundingClientRect(); const wallet=document.querySelector('.wallet-pill:not([hidden])')?.getBoundingClientRect(); const rootRect=root?.getBoundingClientRect(); const intersects=(a,b)=>a&&b&&a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top; const visible=node=>{const style=getComputedStyle(node);return style.display!=='none'&&style.visibility!=='hidden'&&node.getClientRects().length>0;}; const hits=[]; for(const node of root?.querySelectorAll('button,input,select,h1,h2,h3,p,li,label,legend,span,strong')||[]){if(!visible(node))continue; const rect=node.matches('h1,h2,h3,p,li,label,legend,span,strong')?(()=>{const range=document.createRange();range.selectNodeContents(node);return [...range.getClientRects()].find(item=>intersects(item,feedback));})():node.getBoundingClientRect(); if(rect&&intersects(rect,feedback))hits.push(node.getAttribute('data-action')||node.getAttribute('data-side')||node.tagName.toLowerCase());} return {feedbackHits:[...new Set(hits)],walletOverlapsGame:intersects(wallet,rootRect)}; }""")
                                # Reject the original phone collision while proving normal-flow wallet chrome stays outside the game.
                                assert not clearance['walletOverlapsGame'] and (viewport_id!='mobile' or not clearance['feedbackHits']),{'locale':locale,'viewport':viewport_id,'clearance':clearance}
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-andar-bahar-{prefix}-{locale.lower()}-{viewport_id}.png','andar_bahar',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the first side prediction.
                    localized_evidence('ready',['ready'])
                    # Enter one wager and settle a real-backend rank-match round.
                    page.locator('#andar-wager').fill('1'); page.locator('[data-side="andar"]').click(); page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelectorAll('.andar-history-list li').length >= 1",timeout=WAIT_MS * 2)
                    # Capture the settled round across both locales and all viewports.
                    localized_evidence('settled',['settled'])
                    # Commit another real round under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-side="bahar"]').click(); page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelectorAll('.andar-history-list li').length >= 2",timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('andar-bahar').wait_for(timeout=WAIT_MS); assert page.locator('.andar-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Andar Bahar browser and visual gate.
                run_case('BR-AB-001',['AB-001','AB-002','AB-004','AB-005'],andar_bahar_acceptance)
                # Define real-backend Acey-Deucey localization, decision, responsive, motion, and route acceptance.
                def acey_deucey_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-acey_deucey').click(); page.get_by_test_id('acey-deucey').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'acey_deucey.json')['title'] for locale in ('en-US','ru-RU')}
                    # Load the English pass-only guidance for exact zero-spread UI evidence.
                    no_inside_copy=read_i18n_json(ROOT/'web'/'i18n'/'en-US'/'games'/'acey_deucey.json')['controls.noInside']
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active decision or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.acey-header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted in-between table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('acey-deucey').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-acey-deucey-{prefix}-{locale.lower()}-{viewport_id}.png','acey_deucey',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Deal through any pass-only boundaries until the backend publishes one legal spread price.
                    def deal_until_priceable():
                        # Bound retries so a broken pricing response fails instead of looping.
                        for _attempt in range(12):
                            # Deal one free real-backend boundary pair and await its decision controls.
                            page.locator('[data-action="deal"]:not([disabled])').click(); page.locator('[data-action="pass"]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                            # Read the exact server-owned spread, table price, and compatibility scalar.
                            pricing=page.evaluate("""async () => { const payload=await (await fetch('/api/v1/games/acey-deucey/state')).json(); if(!payload.ok) throw new Error(payload.error?.message || 'Acey-Deucey state failed'); const row=payload.data.state.active_round; const spread=row.inside_rank_count; return {spread,multiplier:payload.data.rules.inside_paytable[String(spread)],legacy:payload.data.rules.inside_return_multiplier}; }""")
                            # Accept a positive spread only when UI and both public price fields agree.
                            if pricing['spread']>0:
                                # Require enabled wager controls and one exact displayed total-return price.
                                assert page.locator('[data-action="play"]').is_enabled() and page.locator('#acey-wager').is_enabled()
                                # Preserve the deprecated scalar as the same current-round value.
                                assert pricing['multiplier'] is not None and pricing['legacy']==pricing['multiplier']
                                # Require localized rules copy to display the exact server-owned price.
                                assert f"{pricing['multiplier']}x" in page.locator('.acey-data li').nth(1).inner_text()
                                # Return the accepted price for downstream evidence.
                                return pricing
                            # Equal or adjacent ranks must disable Play and the wager input.
                            assert page.locator('[data-action="play"]').is_disabled() and page.locator('#acey-wager').is_disabled()
                            # Require explicit pass-only localized guidance instead of a silent disabled control.
                            assert page.locator('.acey-help').inner_text()==no_inside_copy
                            # Pass without wallet movement and await the next free-deal control.
                            page.locator('[data-action="pass"]').click(); page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                        # Fail closed when no priceable server round appears inside the bounded search.
                        raise AssertionError('Acey-Deucey did not publish a priceable spread in 12 deals')
                    # Capture the complete ready table before the free boundary deal.
                    localized_evidence('ready',['ready'])
                    # Deal two real-backend boundaries and prove the exact spread price before wallet movement.
                    deal_until_priceable(); localized_evidence('boundaries-dealt',['boundaries_dealt'])
                    # Pass the prepared decision and capture the no-wager terminal path.
                    page.locator('[data-action="pass"]').click(); page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('passed',['passed'])
                    # Deal again, enter a play-token wager, and settle the hidden third card.
                    deal_until_priceable(); page.locator('#acey-wager').fill('1'); page.locator('[data-action="play"]').click(); page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('settled',['settled'])
                    # Commit another pass under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-action="pass"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.locator('[data-action="pass"]').click(); page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('acey-deucey').wait_for(timeout=WAIT_MS); assert page.locator('.acey-history-list li').count()>=3; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Acey-Deucey browser and visual gate.
                run_case('BR-AD-001',['AD-001','AD-002','AD-004','AD-005'],acey_deucey_acceptance)
                # Define real-backend Caribbean Stud localization, decision, responsive, motion, and route acceptance.
                def caribbean_stud_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-caribbean_stud').click(); page.get_by_test_id('caribbean-stud').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'caribbean_stud.json')['title'] for locale in ('en-US','ru-RU')}
                    # Load the locale-owned Call heading so screenshots cannot accept stale Raise terminology.
                    expected_paytable_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'caribbean_stud.json')['paytable.title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active decision or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.cs-header h1').inner_text()==expected_titles[locale]
                            # Require the paytable heading to match the public Call action in the active locale.
                            assert page.locator('.cs-data h2').nth(1).inner_text()==expected_paytable_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted poker table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('caribbean-stud').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-caribbean-stud-{prefix}-{locale.lower()}-{viewport_id}.png','caribbean_stud',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the ante-backed deal.
                    localized_evidence('ready',['ready'])
                    # Read the English return-table panel before any deal mutates the round. (CS-006, TEST-063)
                    caribbean_stud_paytable_text=page.locator('.cs-data').inner_text()
                    # Require the strongest and weakest published Call returns to be visible with localized hand labels.
                    assert 'Call payout schedule' in caribbean_stud_paytable_text and 'Royal flush' in caribbean_stud_paytable_text and '100:1' in caribbean_stud_paytable_text and 'High card' in caribbean_stud_paytable_text and '1:1' in caribbean_stud_paytable_text
                    # Deal through the public frontend and require private dealer hole cards during the decision.
                    page.locator('#cs-ante').fill('1'); page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Decision'",timeout=WAIT_MS * 2); assert page.locator('[aria-label="Face-down dealer card"]').count()==4
                    # Capture the actionable call-or-fold decision.
                    localized_evidence('decision',['decision'])
                    # Complete one real call and classify the authoritative shuffled terminal outcome.
                    page.locator('[data-action="call"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Settled'",timeout=WAIT_MS * 2); terminal=page.locator('.cs-result').inner_text().lower(); terminal_state='dealer_not_qualified' if 'does not qualify' in terminal else ('player_win' if 'player hand beats' in terminal else ('push' if 'tie' in terminal else 'dealer_win')); localized_evidence(terminal_state,[terminal_state])
                    # Complete a second real round through Fold while reduced motion is active.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Decision'",timeout=WAIT_MS * 2); page.locator('[data-action="fold"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Folded'",timeout=WAIT_MS * 2); localized_evidence('fold-reduced-motion',['fold','reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('caribbean-stud').wait_for(timeout=WAIT_MS); assert page.locator('.cs-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Caribbean Stud browser and visual gate.
                run_case('BR-CS-001',['CS-001','CS-002','CS-004','CS-005','CS-006','I18N-010','TEST-063','TEST-117'],caribbean_stud_acceptance)
                # Define real-backend Let It Ride localization, staged decisions, responsive, motion, and route acceptance.
                def let_it_ride_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-let_it_ride').click(); page.get_by_test_id('let-it-ride').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'let_it_ride.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active round or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.lir-header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Measure document containment and retain bounded offender diagnostics for any regression.
                                containment=page.evaluate("() => ({scrollWidth:document.documentElement.scrollWidth,viewportWidth:window.innerWidth,offenders:[...document.querySelectorAll('.let-it-ride *')].filter(node=>node.getBoundingClientRect().right>window.innerWidth+1||node.getBoundingClientRect().left< -1).slice(0,8).map(node=>({tag:node.tagName,className:node.className,right:node.getBoundingClientRect().right,width:node.getBoundingClientRect().width}))})")
                                # Reject horizontal overflow and require the mounted staged poker table.
                                assert containment['scrollWidth']<=containment['viewportWidth']+1 and page.get_by_test_id('let-it-ride').is_visible(), (locale,viewport_id,containment)
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-let-it-ride-{prefix}-{locale.lower()}-{viewport_id}.png','let_it_ride',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the three-unit opening wager.
                    localized_evidence('ready',['ready'])
                    # Deal through the public frontend and require both community cards to remain hidden.
                    page.get_by_test_id('let-it-ride-wager').select_option('5'); page.locator('[data-action="deal"]').click(); page.locator('[data-stage="first"]:not([disabled])').first.wait_for(timeout=WAIT_MS * 2); assert page.locator('.lir-card-empty').count()==2
                    # Capture the first ride-or-pull decision beat.
                    localized_evidence('first-decision',['first_decision'])
                    # Leave the first unit riding and require exactly one community card reveal.
                    page.locator('[data-stage="first"][data-decision="ride"]').click(); page.locator('[data-stage="second"]:not([disabled])').first.wait_for(timeout=WAIT_MS * 2); assert page.locator('.lir-card-empty').count()==1
                    # Capture the second decision beat with the first community card visible.
                    localized_evidence('second-decision',['second_decision'])
                    # Pull one eligible unit and require terminal settled history.
                    page.locator('[data-stage="second"][data-decision="pull"]').click(); page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); assert page.locator('.lir-history-row').count()>=1; localized_evidence('settled',['settled'])
                    # Complete another all-ride round under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-stage="first"]:not([disabled])').first.wait_for(timeout=WAIT_MS * 2); page.locator('[data-stage="first"][data-decision="ride"]').click(); page.locator('[data-stage="second"]:not([disabled])').first.wait_for(timeout=WAIT_MS * 2); page.locator('[data-stage="second"][data-decision="ride"]').click(); page.wait_for_function("() => document.querySelectorAll('.lir-history-row').length >= 2",timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('let-it-ride').wait_for(timeout=WAIT_MS); assert page.locator('.lir-history-row').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Let It Ride browser and visual gate.
                run_case('BR-LIR-001',['LIR-001','LIR-002','LIR-004','LIR-005'],let_it_ride_acceptance)
                # Define real-backend Casino Hold'em localization, decision, responsive, motion, and route acceptance.
                def casino_holdem_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-casino_holdem').click(); page.get_by_test_id('casino-holdem').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 copy expectations from the paired canonical resource files.
                    holdem_resources={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'casino_holdem.json') for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active decision or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title rather than a fallback key or English leakage.
                            assert page.locator('.choldem-header h1').inner_text()==holdem_resources[locale]['title']
                            # Read all ten rendered schedule rows after the locale rerender. (issue #253)
                            paytable=page.get_by_test_id('choldem-paytable'); paytable_labels=paytable.locator('li span').all_inner_texts(); paytable_odds=paytable.locator('li strong').all_inner_texts()
                            # Require the localized title, strongest and weakest labels, complete row count, and server-derived net odds.
                            assert paytable.locator('h2').inner_text()==holdem_resources[locale]['paytable.title'] and len(paytable_labels)==10 and len(paytable_odds)==10 and paytable_labels[0]==holdem_resources[locale]['ranksMade.royal_flush'] and paytable_odds[0]=='100:1' and paytable_labels[-1]==holdem_resources[locale]['ranksMade.high_card'] and paytable_odds[-1]=='1:1'
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted community-card table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('casino-holdem').is_visible() and paytable.is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-casino-holdem-{prefix}-{locale.lower()}-{viewport_id}.png','casino_holdem',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the ante-backed flop.
                    localized_evidence('ready',['ready'])
                    # Deal through the public frontend and require the private dealer and unrevealed board slots.
                    page.locator('#choldem-wager').fill('1'); page.locator('#choldem-wager').press('Tab'); page.locator('[data-action="deal"]').click(); page.locator('[data-decision="call"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); assert page.locator('.playing-card--back').count()==4
                    # Capture the actionable call-or-fold decision.
                    localized_evidence('decision',['decision'])
                    # Complete one real call and classify the authoritative shuffled terminal outcome.
                    page.locator('[data-decision="call"]').click(); page.wait_for_function("() => document.querySelectorAll('.choldem-history-list li').length >= 1",timeout=WAIT_MS * 2); terminal=page.locator('.choldem-result').inner_text().lower(); terminal_state='dealer_not_qualified' if 'did not qualify' in terminal else ('player_win' if 'player won' in terminal else ('push' if 'equal' in terminal else 'dealer_win')); localized_evidence(terminal_state,[terminal_state])
                    # Complete a second real round through fold while reduced motion is active.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-decision="fold"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.locator('[data-decision="fold"]').click(); page.wait_for_function("() => document.querySelectorAll('.choldem-history-list li').length >= 2",timeout=WAIT_MS * 2); localized_evidence('folded-reduced-motion',['folded','reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('casino-holdem').wait_for(timeout=WAIT_MS); assert page.locator('.choldem-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Casino Hold'em browser and visual gate.
                run_case('BR-CH-001',['CH-001','CH-002','CH-004','CH-005','CH-006','TEST-084'],casino_holdem_acceptance)
                # Define real-backend Pai Gow Poker localization, setting, responsive, motion, and route acceptance.
                def pai_gow_poker_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-pai_gow_poker').click(); page.get_by_test_id('pai-gow-poker').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'pai_gow_poker.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active hand or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title rather than a fallback key or English leakage.
                            assert page.locator('.pgp-header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Measure game controls and rendered copy against the fixed problem-report affordance.
                                feedback_geometry=page.evaluate("""() => { const button=document.querySelector('.report-problem-fab:not([hidden])'); const fixed=button?.getBoundingClientRect(); const hits=[]; const intersects=rect=>fixed&&rect.left<fixed.right&&rect.right>fixed.left&&rect.top<fixed.bottom&&rect.bottom>fixed.top; for(const node of document.querySelectorAll('.pgp-shell input,.pgp-shell button')){if(intersects(node.getBoundingClientRect()))hits.push(`${node.tagName.toLowerCase()}.${node.className}`);} for(const node of document.querySelectorAll('.pgp-shell h1,.pgp-shell h2,.pgp-shell h3,.pgp-shell p,.pgp-shell li,.pgp-shell label,.pgp-shell legend,.pgp-summary span,.pgp-summary strong')){const range=document.createRange(); range.selectNodeContents(node); if([...range.getClientRects()].some(intersects))hits.push(`${node.tagName.toLowerCase()}:${node.textContent.trim()}`);} return {documentFits:document.documentElement.scrollWidth<=window.innerWidth+1,feedbackOverlaps:hits.length,overlapIdentities:hits}; }""")
                                # Reject page overflow, fixed-feedback occlusion, and an incomplete mounted table.
                                assert feedback_geometry=={'documentFits':True,'feedbackOverlaps':0,'overlapIdentities':[]} and page.get_by_test_id('pai-gow-poker').is_visible(),{'feedbackGeometry':feedback_geometry,'locale':locale,'viewport':viewport_id}
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-pai-gow-poker-{prefix}-{locale.lower()}-{viewport_id}.png','pai_gow_poker',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the ante-backed deal.
                    localized_evidence('ready',['ready'])
                    # Deal through the public frontend and require seven selectable cards with the private dealer hidden.
                    page.locator('#pgp-wager').fill('1'); page.locator('#pgp-wager').press('Tab'); page.locator('[data-action="deal"]').click(); page.locator('[data-action="house-way"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); setting_counts={'playerTiles':page.locator('[data-testid="pai-gow-poker"] .pgp-tiles .pgp-tile').count(),'privateDealerCards':page.locator('[data-testid="pai-gow-poker"] .pgp-cards .playing-card--back').count()}; assert setting_counts=={'playerTiles':7,'privateDealerCards':7},setting_counts
                    # Capture the actionable hand-setting stage.
                    localized_evidence('setting',['setting'])
                    # Collect every authoritative win, loss, and push presentation through bounded public play.
                    captured_terminal_states=set()
                    # Bound random production deals so a missing terminal class fails closed instead of hanging.
                    for terminal_attempt in range(30):
                        # Set the prepared hand by the public house-way action.
                        page.locator('[data-action="house-way"]').click()
                        # Wait until settlement re-enables the next canonical deal action.
                        page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                        # Read the server-owned latest outcome instead of classifying localized presentation copy.
                        terminal_state=page.evaluate("async () => (await (await fetch('/api/v1/games/pai-gow-poker/state')).json()).data.state.recent_rounds.slice(-1)[0].outcome")
                        # Capture the first governed corpus for each distinct terminal result.
                        if terminal_state not in captured_terminal_states:
                            # Record all locale and viewport combinations while this authoritative result is mounted.
                            localized_evidence(terminal_state,[terminal_state])
                            # Retain the result identity so repeated random outcomes do not duplicate evidence.
                            captured_terminal_states.add(terminal_state)
                        # Stop once all three published outcome paths have been exercised.
                        if captured_terminal_states=={'win','loss','push'}:
                            break
                        # Deal another real round when one terminal class remains unobserved.
                        page.locator('[data-action="deal"]').click()
                        # Wait for the next prepared hand before continuing bounded public play.
                        page.locator('[data-action="house-way"]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                    # Require complete terminal coverage rather than accepting one random outcome.
                    assert captured_terminal_states=={'win','loss','push'}
                    # Complete a second real round by the house way while reduced motion is active.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-action="house-way"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.locator('[data-action="house-way"]').click(); page.wait_for_function("() => document.querySelectorAll('.pgp-history-list li').length >= 2",timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('pai-gow-poker').wait_for(timeout=WAIT_MS); assert page.locator('.pgp-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Pai Gow Poker browser and visual gate.
                run_case('BR-PGP-001',['PGP-001','PGP-002','PGP-004','PGP-005'],pai_gow_poker_acceptance)
                # Define real-backend Joker Poker localization, hold, draw, responsive, motion, and route acceptance.
                def joker_poker_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-joker_poker').click(); page.get_by_test_id('joker-poker').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'joker_poker.json')['title'] for locale in ('en-US','ru-RU')}
                    # Load exact total-return wording so both rendered paytables reject profit-odds ambiguity.
                    expected_returns={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'joker_poker.json')['paytable.multiplier'].replace('{value}','1') for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active hold phase or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title rather than a fallback key or English leakage.
                            assert page.locator('.jp-header h1').inner_text()==expected_titles[locale]
                            # Require the visible push row to state one returned credit rather than one-to-one profit odds.
                            assert expected_returns[locale] in page.locator('.jp-data').inner_text()
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the complete mounted machine.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('joker-poker').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-joker-poker-{prefix}-{locale.lower()}-{viewport_id}.png','joker_poker',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready machine before the ledger-backed deal.
                    localized_evidence('ready',['ready'])
                    # Commit the wager edit before clicking the rerendered deal control.
                    page.locator('#jp-wager').fill('1'); page.locator('#jp-wager').press('Tab'); page.locator('[data-action="deal"]').click(); page.get_by_test_id('joker-poker-source-hand').wait_for(timeout=WAIT_MS * 2); assert page.locator('[data-hold-position]').count()==5
                    # Persist one hold through the public API and capture the actionable phase.
                    page.locator('[data-hold-position="0"]').click(); page.locator('[data-hold-position="0"][aria-pressed="true"]').wait_for(timeout=WAIT_MS * 2); localized_evidence('choose-holds',['choose_holds'])
                    # Track both governed terminal classes so exact-head visual evidence never depends on one random outcome.
                    captured_outcomes=set()
                    # Play a bounded set of real-backend hands until both win and loss evidence has been captured.
                    for attempt in range(40):
                        # Start another public round after the first prepared hold when another terminal class is still missing.
                        if attempt:
                            # Deal through the mounted frontend so later evidence remains real-backend browser evidence.
                            page.locator('[data-action="deal"]').click(); page.get_by_test_id('joker-poker-source-hand').wait_for(timeout=WAIT_MS * 2)
                            # Persist the same representative keyboard-addressable hold in every additional round.
                            page.locator('[data-hold-position="0"]').click(); page.locator('[data-hold-position="0"][aria-pressed="true"]').wait_for(timeout=WAIT_MS * 2)
                        # Draw through the public frontend and wait for the authoritative settled hand.
                        page.locator('[data-action="draw"]').click(); page.get_by_test_id('joker-poker-result').wait_for(timeout=WAIT_MS * 2)
                        # Classify the visible result into the two visual-matrix terminal states.
                        settled_state='losing_hand' if page.locator('.jp-result header strong').inner_text()=='No win' else 'winning_hand'
                        # Capture each terminal class once across both locales and all governed viewports.
                        if settled_state not in captured_outcomes: localized_evidence(settled_state,[settled_state]); captured_outcomes.add(settled_state)
                        # Stop immediately after both exact-head terminal evidence classes exist.
                        if captured_outcomes=={'losing_hand','winning_hand'}: break
                    # Fail closed rather than accepting a partial visual row after the bounded real-backend attempts.
                    assert captured_outcomes=={'losing_hand','winning_hand'}, captured_outcomes
                    # Capture the stable terminal hand under reduced motion.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('joker-poker').wait_for(timeout=WAIT_MS); assert page.locator('.jp-history-list li').count()>=1; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Joker Poker browser and visual gate.
                run_case('BR-JP-001',['JP-001','JP-002','JP-004','JP-005','I18N-010','TEST-117'],joker_poker_acceptance)
                # Define real-backend Double Bonus localization, hold, draw, responsive, motion, and route acceptance.
                def double_bonus_video_poker_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-double_bonus_video_poker').click(); page.get_by_test_id('double-bonus-video-poker').wait_for(timeout=WAIT_MS)
                    # Enumerate every viewport governed by the Double Bonus visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 expectations from both canonical locale resources.
                    resources={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'double_bonus_video_poker.json') for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every governed viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian resources without discarding the active hand.
                        for locale in ('en-US','ru-RU'):
                            # Switch the shared locale and wait for the game-owned rerender.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require exact localized title and phase copy rather than fallback keys or stale English.
                            phase_key='settled' if 'settled' in states or 'route_restored' in states or 'reduced_motion' in states else 'draw' if 'choose_holds' in states else 'idle'; assert page.locator('.db-header h1').inner_text()==resources[locale]['title'] and page.get_by_test_id('double-bonus-video-poker-phase').inner_text()==resources[locale][f'phase.{phase_key}']
                            # Validate containment, visible controls, and after-pass evidence at each exact viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the registered evidence dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Collect document-fit and fixed-feedback overlap geometry for native controls and rendered text ranges.
                                card_geometry=page.evaluate("() => { const button=document.querySelector('.report-problem-fab:not([hidden])'); const fixed=button?.getBoundingClientRect(); const hits=[]; const intersects=rect=>fixed&&rect.left<fixed.right&&rect.right>fixed.left&&rect.top<fixed.bottom&&rect.bottom>fixed.top; for(const node of document.querySelectorAll('.db-card input,.db-card button')){if(intersects(node.getBoundingClientRect()))hits.push(`${node.tagName.toLowerCase()}.${node.className}`);} for(const node of document.querySelectorAll('.db-card h3,.db-card label,.db-card .db-pays span')){const range=document.createRange(); range.selectNodeContents(node); if([...range.getClientRects()].some(intersects))hits.push(`${node.tagName.toLowerCase()}:${node.textContent.trim()}`);} return {documentFits:document.documentElement.scrollWidth<=window.innerWidth+1,feedbackOverlaps:hits.length,overlapIdentities:hits}; }")
                                # Collect mounted-content predicates separately from the responsive geometry.
                                mounted_geometry={'gameVisible':page.get_by_test_id('double-bonus-video-poker').is_visible(),'paytableRows':page.locator('.db-pays div').count(),'paytableVisible':page.locator('.db-paytable').is_visible()}
                                # Reject page overflow, obscured paytable content, and incomplete mounted state with exact diagnostics.
                                assert card_geometry=={'documentFits':True,'feedbackOverlaps':0,'overlapIdentities':[]} and mounted_geometry=={'gameVisible':True,'paytableRows':11,'paytableVisible':True},{'cardGeometry':card_geometry,'mountedGeometry':mounted_geometry,'locale':locale,'viewport':viewport_id}
                                # Record self-describing exact-head evidence for this state and viewport.
                                game_evidence(f'after-pass-double-bonus-video-poker-{prefix}-{locale.lower()}-{viewport_id}.png','double_bonus_video_poker',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready machine before the ledger-backed deal.
                    localized_evidence('ready',['ready'])
                    # Commit a bounded wager and deal through the public frontend.
                    page.locator('[data-bet]').fill('1'); page.locator('[data-bet]').press('Tab'); page.locator('[data-deal]').click(); page.get_by_test_id('double-bonus-video-poker-hand').wait_for(timeout=WAIT_MS * 2); assert page.locator('[data-hold]').count()==5
                    # Select one visible hold and capture the actionable draw state.
                    page.locator('[data-hold="0"]').click(); page.locator('[data-hold="0"][aria-pressed="true"]').wait_for(timeout=WAIT_MS * 2); localized_evidence('choose-holds',['choose_holds'])
                    # Draw through the public frontend and require one authoritative settled result.
                    page.locator('[data-draw]').click(); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS * 2); assert page.get_by_test_id('double-bonus-video-poker-result').is_visible(); localized_evidence('settled',['settled'])
                    # Capture the stable terminal table under reduced-motion media emulation.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['settled','reduced_motion'])
                    # Reload the canonical game route and require restored player-owned terminal state.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('double-bonus-video-poker').wait_for(timeout=WAIT_MS); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['settled','route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Double Bonus browser and governed visual gate.
                run_case('BR-DBVP-001',['DBVP-001','DBVP-002','TEST-114'],double_bonus_video_poker_acceptance)
                # Define real-backend Mississippi Stud localization, progressive-reveal, settlement, motion, and route acceptance.
                def mississippi_stud_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-mississippi_stud').click(); page.get_by_test_id('mississippi-stud').wait_for(timeout=WAIT_MS)
                    # Enumerate every viewport governed by the Mississippi Stud visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 expectations from both canonical locale resources.
                    resources={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'mississippi_stud.json') for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every governed viewport.
                    def localized_evidence(prefix,states,expected_street=None,expected_revealed=None):
                        # Iterate through paired English and Russian resources without discarding the active round.
                        for locale in ('en-US','ru-RU'):
                            # Switch the shared locale and wait for the game-owned rerender.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require exact localized phase copy rather than fallback keys or stale English.
                            if expected_street is None and 'ready' in states:
                                # Pin the ready prompt before the ledger-backed deal.
                                assert page.get_by_test_id('mississippi-stud-result').inner_text()==resources[locale]['result.idle']
                            elif expected_street is not None:
                                # Pin the localized street label for the current progressive reveal.
                                assert page.locator('.ms-street').inner_text()==resources[locale]['label.street'].replace('{street}',str(expected_street))
                            else:
                                # Require one localized terminal outcome after the authoritative settlement.
                                assert any(page.get_by_test_id('mississippi-stud-result').inner_text().startswith(resources[locale][f'outcome.{outcome}']) for outcome in ('win','push','lose'))
                            # Validate containment, visible controls, and after-pass evidence at each exact viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the registered evidence dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Collect document-fit and fixed-feedback overlap geometry for native controls and rendered text ranges.
                                card_geometry=page.evaluate("() => { const button=document.querySelector('.report-problem-fab:not([hidden])'); const fixed=button?.getBoundingClientRect(); const hits=[]; const intersects=rect=>fixed&&rect.left<fixed.right&&rect.right>fixed.left&&rect.top<fixed.bottom&&rect.bottom>fixed.top; for(const node of document.querySelectorAll('.msstud input,.msstud button')){if(intersects(node.getBoundingClientRect()))hits.push(`${node.tagName.toLowerCase()}.${node.className}`);} for(const node of document.querySelectorAll('.msstud h3,.msstud h4,.msstud label,.msstud .ms-pays span,.msstud .ms-street,.msstud .ms-result')){const range=document.createRange(); range.selectNodeContents(node); if([...range.getClientRects()].some(intersects))hits.push(`${node.tagName.toLowerCase()}:${node.textContent.trim()}`);} const root=document.querySelector('.msstud')?.getBoundingClientRect(); return {documentFits:document.documentElement.scrollWidth<=window.innerWidth+1,feedbackOverlaps:hits.length,overlapIdentities:hits,readableInlineSize:Math.round(root?.width||0)}; }")
                                # Collect mounted-content predicates separately from responsive geometry.
                                mounted_geometry={'gameVisible':page.get_by_test_id('mississippi-stud').is_visible(),'paytableRows':page.locator('.ms-pays div').count(),'paytableVisible':page.locator('.ms-pays').is_visible(),'communityCards':page.locator('.ms-row').nth(1).locator('.playing-card').count() if page.locator('.ms-row').count()>1 else 0}
                                # Reject page overflow, fixed-feedback occlusion, narrow slivers, and incomplete mounted state with exact diagnostics.
                                assert card_geometry['documentFits'] and card_geometry['feedbackOverlaps']==0 and card_geometry['readableInlineSize']>=300 and mounted_geometry['gameVisible'] and mounted_geometry['paytableRows']==9 and mounted_geometry['paytableVisible'] and (expected_revealed is None or mounted_geometry['communityCards']==expected_revealed),{'cardGeometry':card_geometry,'mountedGeometry':mounted_geometry,'locale':locale,'viewport':viewport_id}
                                # Record self-describing exact-head evidence for this state and viewport.
                                game_evidence(f'after-pass-mississippi-stud-{prefix}-{locale.lower()}-{viewport_id}.png','mississippi_stud',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready machine before the ledger-backed deal.
                    localized_evidence('ready',['ready'])
                    # Commit a bounded ante and deal through the public frontend.
                    page.locator('[data-ante]').fill('1'); page.locator('[data-ante]').press('Tab'); page.locator('[data-deal]').click(); page.get_by_text('Street 1 of 3',exact=True).wait_for(timeout=WAIT_MS * 2)
                    # Capture the first decision before any community card is exposed.
                    localized_evidence('street-one-decision',['street_one_decision'],1,0)
                    # Bet the first street and require exactly one revealed community card.
                    page.locator('[data-bet="1"]').click(); page.get_by_text('Street 2 of 3',exact=True).wait_for(timeout=WAIT_MS * 2); localized_evidence('street-two-decision',['street_two_decision'],2,1)
                    # Bet the second street and require exactly two revealed community cards.
                    page.locator('[data-bet="1"]').click(); page.get_by_text('Street 3 of 3',exact=True).wait_for(timeout=WAIT_MS * 2); localized_evidence('street-three-decision',['street_three_decision'],3,2)
                    # Settle through the public frontend and capture the complete terminal hand under reduced motion.
                    page.locator('[data-bet="1"]').click(); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.emulate_media(reduced_motion='reduce'); localized_evidence('settled-reduced-motion',['settled','reduced_motion'],None,3)
                    # Reload the canonical route and require restored player-owned terminal state.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('mississippi-stud').wait_for(timeout=WAIT_MS); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'],None,3)
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Mississippi Stud browser and governed visual gate.
                run_case('BR-MSTUD-001',['MSTUD-001','MSTUD-002','TEST-115'],mississippi_stud_acceptance)
                # Define real-backend Teen Patti localization, decision, settlement, privacy, motion, and route acceptance.
                def teen_patti_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-teen_patti').click(); page.get_by_test_id('teen-patti').wait_for(timeout=WAIT_MS)
                    # Enumerate every viewport governed by the Teen Patti visual-matrix row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 expectations from both canonical locale resources.
                    resources={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'teen_patti.json') for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every governed viewport.
                    def localized_evidence(prefix,states,expected_result_key=None,terminal_outcomes=(),expected_cards=None):
                        # Iterate through paired English and Russian resources without discarding the active round.
                        for locale in ('en-US','ru-RU'):
                            # Switch the shared locale and wait for the game-owned rerender.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Read the current localized result once for exact state classification.
                            result_text=page.locator('.tp-result').inner_text()
                            # Require exact ready or decision copy when the state has one fixed resource.
                            if expected_result_key is not None:
                                # Pin the expected localized resource rather than fallback keys or stale English.
                                assert result_text.startswith(resources[locale][expected_result_key]),{'result':result_text,'expected':resources[locale][expected_result_key],'locale':locale}
                            # Require one allowed localized authoritative terminal outcome when the result is deal-dependent.
                            elif terminal_outcomes:
                                # Match only canonical localized outcome prefixes before the appended hand and net details.
                                assert any(result_text.startswith(resources[locale][f'outcome.{outcome}']) for outcome in terminal_outcomes),{'result':result_text,'outcomes':terminal_outcomes,'locale':locale}
                            # Validate containment, visible controls, and after-pass evidence at each exact viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the registered evidence dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Collect document-fit and fixed-feedback overlap geometry for native controls and rendered text ranges.
                                card_geometry=page.evaluate("() => { const button=document.querySelector('.report-problem-fab:not([hidden])'); const fixed=button?.getBoundingClientRect(); const hits=[]; const intersects=rect=>fixed&&rect.left<fixed.right&&rect.right>fixed.left&&rect.top<fixed.bottom&&rect.bottom>fixed.top; for(const node of document.querySelectorAll('.teenp input,.teenp button')){if(intersects(node.getBoundingClientRect()))hits.push(`${node.tagName.toLowerCase()}.${node.className}`);} for(const node of document.querySelectorAll('.teenp h3,.teenp h4,.teenp label,.teenp .tp-pays span,.teenp .tp-rank,.teenp .tp-result')){const range=document.createRange(); range.selectNodeContents(node); if([...range.getClientRects()].some(intersects))hits.push(`${node.tagName.toLowerCase()}:${node.textContent.trim()}`);} const root=document.querySelector('.teenp')?.getBoundingClientRect(); return {documentFits:document.documentElement.scrollWidth<=window.innerWidth+1,feedbackOverlaps:hits.length,overlapIdentities:hits,readableInlineSize:Math.round(root?.width||0)}; }")
                                # Collect mounted-content predicates separately from responsive geometry.
                                mounted_geometry={'gameVisible':page.get_by_test_id('teen-patti').is_visible(),'paytableRows':page.locator('.tp-pays div').count(),'paytableVisible':page.locator('.tp-pays').is_visible(),'rankingVisible':page.locator('.tp-rank').is_visible(),'cards':page.locator('.teenp .playing-card').count()}
                                # Reject page overflow, fixed-feedback occlusion, narrow slivers, incomplete references, and wrong privacy state with exact diagnostics.
                                assert card_geometry['documentFits'] and card_geometry['feedbackOverlaps']==0 and card_geometry['readableInlineSize']>=300 and mounted_geometry['gameVisible'] and mounted_geometry['paytableRows']==3 and mounted_geometry['paytableVisible'] and mounted_geometry['rankingVisible'] and (expected_cards is None or mounted_geometry['cards']==expected_cards),{'cardGeometry':card_geometry,'mountedGeometry':mounted_geometry,'locale':locale,'viewport':viewport_id}
                                # Record self-describing exact-head evidence for this state and viewport.
                                game_evidence(f'after-pass-teen-patti-{prefix}-{locale.lower()}-{viewport_id}.png','teen_patti',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the ledger-backed deal.
                    localized_evidence('ready',['ready'],'result.idle',expected_cards=0)
                    # Commit a bounded ante and deal through the public frontend.
                    page.locator('[data-ante]').fill('1'); page.locator('[data-ante]').press('Tab'); page.locator('[data-deal]').click(); page.locator('[data-play]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                    # Capture the private decision state with exactly three player cards and no dealer reveal.
                    localized_evidence('decision',['decision'],'result.decide',expected_cards=3)
                    # Play through the public action and require a complete six-card showdown.
                    page.locator('[data-play]').click(); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('play-settled',['play_settled'],terminal_outcomes=('player_win','dealer_win','push','dealer_not_qualified'),expected_cards=6)
                    # Deal another round and fold through the public action without exposing the dealer.
                    page.locator('[data-deal]').click(); page.locator('[data-fold]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.locator('[data-fold]').click(); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('folded',['folded'],'outcome.folded',expected_cards=3)
                    # Complete a real showdown with reduced motion enabled.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-deal]').click(); page.locator('[data-play]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.locator('[data-play]').click(); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS * 2); localized_evidence('reduced-motion',['reduced_motion'],terminal_outcomes=('player_win','dealer_win','push','dealer_not_qualified'),expected_cards=6)
                    # Reload the canonical game route and require restored player-owned terminal state.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('teen-patti').wait_for(timeout=WAIT_MS); page.locator('[data-deal]:not([disabled])').wait_for(timeout=WAIT_MS); localized_evidence('route-restored',['route_restored'],terminal_outcomes=('player_win','dealer_win','push','dealer_not_qualified'),expected_cards=6)
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Teen Patti browser and governed visual gate.
                run_case('BR-TEEN-PATTI-001',['TEENP-001','TEENP-002','TEST-116'],teen_patti_acceptance)
                # Define registered Texas Hold'em localization, streets, settlement, motion, and route acceptance.
                def texas_holdem_practice_acceptance():
                    # Open the catalog-owned route and wait for the stable table selector.
                    page.get_by_test_id('nav-texas_holdem_practice_table').click(); page.get_by_test_id('texas-holdem-practice-table').wait_for(timeout=WAIT_MS)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'texas_holdem_practice_table.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one authoritative table state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active hand or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title rather than a fallback key or English leakage.
                            assert page.locator('.thpt-header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the complete mounted table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('texas-holdem-practice-table').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-texas-holdem-practice-{prefix}-{locale.lower()}-{viewport_id}.png','texas_holdem_practice_table',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before any wallet reservation.
                    localized_evidence('ready',['ready'])
                    # Commit one low fixed-limit unit and start through the public browser action.
                    page.locator('#thpt-wager').fill('1'); page.locator('#thpt-wager').press('Tab'); page.locator('[data-action="start-hand"]').click(); page.locator('[data-action="call"]:not([disabled])').wait_for(timeout=WAIT_MS * 2)
                    # Capture private preflop play with redacted funded opponents.
                    assert all(page.get_by_test_id(f'thpt-seat-opponent_{index}').locator('.playing-card--back').count()==2 for index in (1,2,3)); localized_evidence('preflop-decision',['preflop_decision'])
                    # Advance and capture flop, turn, and river public decision states.
                    for prefix,state,card_count in [('flop-decision','flop_decision',3),('turn-decision','turn_decision',4),('river-decision','river_decision',5)]:
                        # Call through the public control and wait for the authoritative next street.
                        page.locator('[data-action="call"]:not([disabled])').click(); page.locator('[data-action="call"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.wait_for_function(f"() => document.querySelectorAll('[data-testid=thpt-community-cards] .playing-card').length === {card_count}")
                        # Capture this exact decision street in both locales and all viewports.
                        localized_evidence(prefix,[state])
                    # Complete the river call and wait for fully reconciled four-wallet settlement.
                    page.locator('[data-action="call"]:not([disabled])').click(); page.get_by_test_id('thpt-result').wait_for(timeout=WAIT_MS * 2)
                    # Capture revealed showdown and terminal settlement together.
                    assert page.locator('[data-testid^="thpt-seat-opponent_"] .playing-card--back').count()==0; localized_evidence('showdown-settled',['showdown','settled'])
                    # Start a second real hand and exercise the explicit fold path.
                    page.locator('[data-action="start-hand"]:not([disabled])').click(); page.locator('[data-action="fold"]:not([disabled])').wait_for(timeout=WAIT_MS * 2); page.locator('[data-action="fold"]:not([disabled])').click(); page.get_by_test_id('thpt-result').wait_for(timeout=WAIT_MS * 2); localized_evidence('folded',['folded'])
                    # Capture stable settled presentation with reduced motion enabled.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion'])
                    # Counterfeit the rendered pot, result, and an unrelated cache key without sending another server action.
                    page.evaluate("() => { document.querySelector('[data-testid=thpt-pot] strong').textContent='999,999'; document.querySelector('[data-testid=thpt-result] h2').textContent='ATTACKER RESULT'; localStorage.setItem('casino.hostile.thpt','999999'); }")
                    # Require the hostile DOM edits to exist temporarily before authoritative refresh.
                    assert '999,999' in page.get_by_test_id('thpt-pot').inner_text() and 'ATTACKER RESULT' in page.get_by_test_id('thpt-result').inner_text()
                    # Reload the canonical route and require server-owned pot, result, and player history to replace client tampering.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('texas-holdem-practice-table').wait_for(timeout=WAIT_MS); assert page.get_by_test_id('thpt-result').is_visible() and '999,999' not in page.get_by_test_id('thpt-pot').inner_text() and 'ATTACKER RESULT' not in page.get_by_test_id('thpt-result').inner_text() and page.evaluate("localStorage.getItem('casino.hostile.thpt')")=='999999'; localized_evidence('route-restored',['route_restored','client_tamper_refreshed'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the integrated Texas Hold'em browser and hostile-client visual gate.
                run_case('BR-THPT-001',['THPT-001','THPT-002','THPT-004','THPT-005','SEC-002','SEC-003','SEC-009'],texas_holdem_practice_acceptance)
                # Define route_restoration to prove deep links, reload, Back, and Forward behavior.
                def route_restoration():
                    # Open Roulette directly through its canonical path using the authenticated browser context.
                    page.goto(base+'/games/roulette',wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
                    # Reload the same deep link and require the route to remount without a lobby redirect.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
                    # Require the persistent brand and wallet to finish painting before acceptance evidence.
                    page.locator('.brand-mark').wait_for(timeout=WAIT_MS); page.get_by_test_id('premium-wallet').wait_for(timeout=WAIT_MS); page.wait_for_timeout(300)
                    # Capture the restored game surface at the primary desktop viewport.
                    viewport_shot('after-pass-shell-route-roulette-desktop.png')
                    # Push a second catalog route through normal shell navigation.
                    page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slot-grid').wait_for(timeout=WAIT_MS)
                    # Restore Roulette through browser Back and wait for the route-owned readiness selector.
                    page.go_back(); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
                    # Restore Slots through browser Forward and wait for its route-owned readiness selector.
                    page.go_forward(); page.get_by_test_id('slot-grid').wait_for(timeout=WAIT_MS)
                    # Return to the lobby so existing game interaction coverage starts from its normal baseline.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                # Execute the browser lifecycle restoration gate.
                run_case('BR-ROUTE-RESTORE-001',['CORE-022','MOTION-002'],route_restoration)
                # Delegate the complete Roulette, autoplay, Slots, and Keno affinity chain without transferring shared page ownership.
                browser_roulette_slots_keno.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,page,base,ROOT,visual_matrix,save_player_game_state,roulette_i18n_failure_diagnostic,slots_engine,keno_engine,shot,viewport_shot,region_evidence,game_evidence,console_errors,page_errors,http_errors,evidence_commit,evidence_branch,screenshots)
                # Delegate the complete Bingo-through-Admin affinity chain without transferring shared Browser lifecycle.
                browser_bingo_admin.run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,page,base,ROOT,browser_player_id,visual_matrix,save_player_game_state,blackjack_engine,wait_for_bingo_terminal_render,require_bingo_terminal_auto_payload,require_bingo_terminal_reload_payload,guest_analytics,prepare_admin_feedback_draft,save_admin_feedback_triage,collect_normal_admin_navigation,assert_route_i18n,auth_core,DEFAULT_AUTH_EMAIL,DEFAULT_AUTH_PASSWORD,EXPECTED_MODULE_ROWS,VERSION_MANIFEST,read_i18n_json,write_json,shot,region_evidence,game_evidence,console_errors,page_errors,http_errors,screenshots)
                if console_errors or page_errors or http_errors: raise AssertionError('Browser errors: '+str(console_errors+page_errors+http_errors))
            # Handle the expected failure path for the protected logic.
            except Exception:
                shot('browser_failure.png'); raise
            # Run cleanup logic regardless of success or failure.
            finally: browser.close()
        # Mark the suite passing only after every named browser case and browser close succeeds.
        status='PASS'
    # Convert cleanup-driven timeout failures into a stable non-zero timeout status.
    except Exception:
        # Acknowledge only the reporter-owned deadline before normal finally cleanup.
        if progress.timed_out:
            # Prevent a redundant fallback interrupt while artifacts are written.
            progress.acknowledge_timeout()
            # Return the conventional timeout code after the finally block completes.
            return progress.timeout_exit_code
        # Preserve every non-timeout browser failure unchanged.
        raise
    # Convert the watchdog fallback interrupt into a stable non-zero timeout status.
    except KeyboardInterrupt:
        # Return the conventional timeout code only for the reporter-owned deadline.
        if progress.timed_out:
            # Stop any remaining watchdog grace wait before artifact cleanup.
            progress.acknowledge_timeout()
            # Return after the shared finally block closes the tracked listener.
            return progress.timeout_exit_code
        # Preserve external user interrupts unchanged.
        raise
    # Run cleanup logic regardless of success or failure.
    finally:
        # Stop the tracked browser child once and retain its exact closure evidence.
        progress.cleanup()
        # Convert cleanup failure into a failed suite without hiding an active exception.
        if progress.cleanup_error: status='FAIL'
        # Stop the watchdog and flush the terminal phase result after cleanup.
        progress.close(status)
        # Prevent later API or storage cases from inheriting browser instrumentation.
        ACTIVE_PROGRESS=None
        # Prevent later API or storage cases from inheriting browser shard ownership.
        BROWSER_SHARD_CASES=None
        # Prevent later API or storage cases from inheriting the affected-game restriction.
        BROWSER_AFFECTED_GAMES=None
        # Preserve the existing JSON result artifact path and behavior.
        save_results()
        # Retain one shard-unique, self-describing result file so aggregate verification needs no external selection input.
        if shard_count>1: (ROOT/'logs'/'test-runs'/f'browser_results_shard_{shard_index}_of_{shard_count}.json').write_text(json.dumps({'shard_index':shard_index,'shard_count':shard_count,'owned_cases':sorted(owned_cases or []),'affected_games':(sorted(affected_games) if affected_games else None),'results':RESULTS},indent=2),encoding='utf-8')
    # Return success only when browser execution and tracked listener cleanup both passed.
    return 0 if status=='PASS' else 1

# Define the main function used by this module.
def main():
    # Build the dependency-free command-line parser for existing suite selectors and progress timing.
    ap=argparse.ArgumentParser()
    # Preserve the existing API suite selector.
    ap.add_argument('--api',action='store_true')
    # Preserve the existing browser suite selector.
    ap.add_argument('--browser',action='store_true')
    # Preserve the existing storage suite selector.
    ap.add_argument('--storage',action='store_true')
    # Preserve the existing live MySQL selector.
    ap.add_argument('--mysql-live',action='store_true')
    # Add the explicit disposable MySQL 8.4 migration selector.
    ap.add_argument('--mysql-migrations-live',action='store_true')
    # Select one explicit listener-free request-latency provider baseline.
    ap.add_argument('--request-latency',choices=('json','mysql'),default=None)
    # Select the caller-owned external aggregate evidence destination.
    ap.add_argument('--request-latency-output',default=None)
    # Configure heartbeat cadence while enforcing the public sixty-second maximum below.
    ap.add_argument('--heartbeat-seconds',type=float,default=45.0)
    # Configure the non-failing no-progress warning threshold.
    ap.add_argument('--stall-seconds',type=float,default=180.0)
    # Configure the real browser-suite wall-clock timeout.
    ap.add_argument('--timeout-seconds',type=float,default=2700.0)
    # Split the browser suite into deterministic duration-balanced shards for parallel workers.
    ap.add_argument('--shard-count',type=int,default=1)
    # Select this worker's zero-based packed Browser shard.
    ap.add_argument('--shard-index',type=int,default=0)
    # Verify aggregated per-shard result files from a directory instead of running any suite.
    ap.add_argument('--verify-browser-shards',default=None)
    # Restrict browser execution to a comma-separated set of affected game ids, or omit for the full catalog. (issue #468 item 4)
    ap.add_argument('--games',default=None)
    # Parse caller options before running any suite.
    args=ap.parse_args()
    # Require an external output only with the explicit request-latency selector.
    if bool(args.request_latency)!=bool(args.request_latency_output): ap.error('--request-latency and --request-latency-output must be supplied together')
    # Require the existing disposable migration lifecycle for a MySQL baseline.
    if args.request_latency=='mysql' and not args.mysql_migrations_live: ap.error('--request-latency mysql requires --mysql-migrations-live')
    # Keep the JSON baseline separate from MySQL migration and live-service selectors.
    if args.request_latency=='json' and (args.mysql_live or args.mysql_migrations_live): ap.error('--request-latency json cannot be combined with MySQL live selectors')
    # Resolve the affected-game restriction once so the runner and the aggregate verifier agree on the expected set.
    affected_games=None
    if args.games is not None:
        # Accept a comma-separated list, ignoring surrounding whitespace and empty entries.
        affected_games={token.strip() for token in args.games.split(',') if token.strip()}
        # Reject an empty selection so an accidental blank never silently skips every dedicated case.
        if not affected_games: ap.error('--games must name at least one game id')
        # Reject unknown ids so a typo fails loudly instead of quietly under-testing.
        unknown=affected_games-{game['id'] for game in casino_config.GAMES}
        if unknown: ap.error(f'--games contains unknown game ids: {sorted(unknown)}')
    # Reject heartbeat intervals outside issue #207 acceptance before starting work.
    if args.heartbeat_seconds<=0 or args.heartbeat_seconds>60: ap.error('--heartbeat-seconds must be greater than 0 and at most 60')
    # Reject warning thresholds that would fire before one heartbeat.
    if args.stall_seconds<args.heartbeat_seconds: ap.error('--stall-seconds must be at least --heartbeat-seconds')
    # Reject non-positive real suite timeouts.
    if args.timeout_seconds<=0: ap.error('--timeout-seconds must be greater than 0')
    # Reject impossible browser shard setups before any suite starts.
    if args.shard_count<1: ap.error('--shard-count must be at least 1')
    # Keep shard ownership within the configured worker range.
    if not 0<=args.shard_index<args.shard_count: ap.error('--shard-index must be between 0 and shard-count - 1')
    # Keep sharding meaningful for the exact literal browser case sequence.
    if args.shard_count>browser_case_total(): ap.error('--shard-count must not exceed the literal browser case total')
    # Keep shard selection scoped to the browser suite and aggregate verification only.
    if args.shard_count>1 and not (args.browser or args.verify_browser_shards): ap.error('--shard-count applies only to --browser or --verify-browser-shards')
    # Run aggregate shard verification alone using the detector-owned expected selection.
    if args.verify_browser_shards: return verify_browser_shards(args.verify_browser_shards,args.shard_count,affected_games)
    if not args.api and not args.browser and not args.storage and not args.mysql_live and not args.mysql_migrations_live and not args.request_latency: args.api=True
    # Start protected logic so failures can be handled safely.
    try:
        # Build the credential-free MySQL callback only for the explicit benchmark selector.
        request_latency_callback=(lambda: run_case('REQUEST-LATENCY-MYSQL-001',['TEST-148'],lambda: run_request_latency_provider('mysql',args.request_latency_output))) if args.request_latency=='mysql' else None
        # Delegate the complete storage/MySQL area while preserving explicit live selectors and callback wiring.
        if args.storage or args.mysql_live or args.mysql_migrations_live: api_storage_foundation.run_cases(run_case,include_live=args.mysql_live,include_migration_live=args.mysql_migrations_live,request_latency_callback=request_latency_callback)
        # Run the JSON provider only through its explicit benchmark selector.
        if args.request_latency=='json': run_case('REQUEST-LATENCY-JSON-001',['TEST-148'],lambda: run_request_latency_provider('json',args.request_latency_output))
        if args.api: run_api_tests()
        if args.browser:
            # Set code to the value needed for the next operation.
            code=run_browser_tests(args.heartbeat_seconds,args.stall_seconds,args.timeout_seconds,args.shard_count,args.shard_index,affected_games)
            if code: return code
    # Run cleanup logic regardless of success or failure.
    finally: save_results()
    # Return success after all selected suites complete normally.
    return 0
if __name__=='__main__': raise SystemExit(main())
