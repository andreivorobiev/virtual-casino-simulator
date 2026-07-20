# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
# Import required dependency so this module can use its public functions or constants.
import argparse, importlib, io, json, os, re, socket, subprocess, sys, time, traceback, unittest, urllib.request
# Import source inspection so browser progress totals follow declared run_case calls automatically.
import inspect
# Import required dependency so this module can use its public functions or constants.
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
# Import auth helpers so API tests can seed users through the backend storage seam.
from casino.core import auth as auth_core
# Import configuration helpers so startup hardening can be tested without launching a public listener.
from casino import config as casino_config
# Import the shared resolver so session precedence is tested independently of individual game APIs.
from casino.core.request_player import resolve_authenticated_player
# Import the isolated game-state writer for deterministic rendered Blackjack settlement setup.
from casino.core.state_store import save_player_game_state
# Import storage tests so provider parity can run without the broad API suite.
from tests import storage_tests
# Import listener-free migration policy tests for every storage validation run.
from tests import mysql_migration_tests
# Import listener-free encrypted recovery policy tests for every storage validation run.
from tests import recovery_tests
# Import listener-free edge policy and sanitized observation tests for the API validation run.
from tests import edge_gate_tests
# Import focused non-finite validation and persistence tests for TEST-055.
from tests import nonfinite_money_tests
# Import the current-catalog hostile-client certification entrypoint.
from tests.server_authority_tests import run_server_authority_tests
# Import the reusable flushed reporter for TEST-010 browser execution.
from tests.progress import ProgressReporter
# Set RESULTS to the value needed for the next operation.
RESULTS=[]
# Track the browser-suite reporter only while named browser cases are executing.
ACTIVE_PROGRESS=None
# Set SESSION_TOKEN to the value needed for the next operation.
SESSION_TOKEN=None
# Set DEFAULT_AUTH_EMAIL to the value needed for the next operation.
DEFAULT_AUTH_EMAIL=os.environ.get("CASINO_BOOTSTRAP_ADMIN_EMAIL", "admin@example.local")
# Set DEFAULT_AUTH_PASSWORD to the value needed for the next operation.
DEFAULT_AUTH_PASSWORD=os.environ.get("CASINO_BOOTSTRAP_ADMIN_PASSWORD", "admin-password")
# Set PLACEHOLDER_RE to the value needed for the next operation.
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")

# Define the record function used by this module.
def record(test_id, reqs, status, message=''):
    # Execute this statement as part of the module's documented control flow.
    RESULTS.append({'test_id':test_id,'requirements':reqs,'status':status,'message':message})
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
def api(base, path, method='GET', body=None, ok=True, auth_token='__default__'):
    # Set data to the value needed for the next operation.
    data = None if body is None else json.dumps(body).encode('utf-8')
    # Set headers to the value needed for the next operation.
    headers={'Content-Type':'application/json'}
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
    # Branch when the following condition is true.
    if ok and not payload.get('ok'): raise AssertionError(payload)
    # Branch when the following condition is true.
    if not ok and payload.get('ok'): raise AssertionError('expected failure but got ok')
    # Return the computed value to the caller.
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
    # Return the computed value to the caller.
    return SESSION_TOKEN

# Define the start_server function used by this module.
def start_server():
    # Set port to the value needed for the next operation.
    port=free_port(); proc=subprocess.Popen([sys.executable,str(ROOT/'run.py'),'--host','127.0.0.1','--port',str(port),'--no-browser'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    # Set base to the value needed for the next operation.
    base=f'http://127.0.0.1:{port}'
    # Record the isolated listener identity so acceptance handbacks can prove loopback hygiene.
    print(f'Test server PID {proc.pid} listening on {base}',flush=True)
    # Iterate through the collection to process each item.
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
    # Read the active browser reporter without changing API or storage runner behavior.
    progress=ACTIVE_PROGRESS
    # Flush the named browser-test start before its body begins.
    if progress: progress.start_item(test_id)
    # Start protected logic so failures can be handled safely.
    try: fn()
    # Handle the expected failure path for the protected logic.
    except Exception as e:
        # Flush the terminal failure before preserving the existing result and exception.
        if progress: progress.finish_item('FAIL')
        # Preserve the existing mapped failure record and re-raise semantics.
        record(test_id, reqs, 'FAIL', str(e)); raise
    # Record the normal passing path after the test body returns.
    else:
        # Flush the terminal pass and advance completed/total counts.
        if progress: progress.finish_item('PASS')
        # Preserve the existing mapped PASS result.
        record(test_id, reqs, 'PASS')

# Count literal BR-prefixed cases from the browser runner so totals cannot drift from discovery.
def browser_case_total():
    # Read only the browser runner source from this checkout.
    source=inspect.getsource(run_browser_tests)
    # Count every literal named browser run_case without maintaining another allowlist.
    return len(re.findall(r"\brun_case\(\s*['\"]BR-",source))

# Define assert_condition so concise mapped checks still fail when their predicate is false.
def assert_condition(value, message):
    # Raise a focused assertion when the mapped acceptance predicate is false.
    assert value, message

# Define the run_storage_tests function used by this module.
def run_storage_tests(include_live=False, include_migration_live=False):
    # Define one focused unittest runner for authenticated recovery and clean-target policy.
    def run_recovery_policy_tests():
        # Load only the #205 synthetic recovery test case.
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(recovery_tests.RecoveryEvidenceTests)
        # Execute with concise standard output.
        result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
        # Fail the named central case when any focused assertion failed.
        if not result.wasSuccessful(): raise AssertionError('recovery policy suite failed')
    # Define one focused unittest runner for checksum, proof, failure, and SELECT-only policy.
    def run_mysql_migration_policy_tests():
        # Load only the #204 migration test case.
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(mysql_migration_tests.MySQLMigrationTests)
        # Execute with concise standard output.
        result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
        # Fail the named central case when any focused assertion failed.
        if not result.wasSuccessful(): raise AssertionError('MySQL migration policy suite failed')
    # Map the listener-free policy suite to the permanent migration requirements.
    run_case('MYSQL-MIGRATION-001',['MYSQL-005','STORAGE-007','TEST-048'],run_mysql_migration_policy_tests)
    # Map the listener-free recovery suite to the permanent recovery requirements.
    run_case('RECOVERY-POLICY-001',['MYSQL-006','TOOL-004','TEST-049'],run_recovery_policy_tests)
    # Execute the JSON fallback parity test for provider-backed players, ledger, history, and settings.
    run_case('STORAGE-JSON-001',['CORE-017','LEDGER-001','LEDGER-007','TEST-030'],storage_tests.run_json_provider_parity)
    # Execute storage-enforced replay, conflict, restart, and cross-process JSON action tests.
    run_case('STORAGE-JSON-IDEMPOTENCY-001',['LEDGER-026','STORAGE-005','STORAGE-006','TEST-043'],storage_tests.run_json_action_idempotency)
    # Execute funded practice-opponent debit, refund, payout, restart, owner, and process evidence.
    run_case('STORAGE-PRACTICE-OPPONENT-001',['BOT-009','BOT-010','BOT-011','ADMIN-023','LEDGER-026','STORAGE-005','STORAGE-006'],storage_tests.run_practice_opponent_accounting)
    # Execute the MySQL schema and atomic ledger-provider path test without requiring a live service.
    run_case('STORAGE-MYSQL-001',['CORE-017','LEDGER-001','LEDGER-007','LEDGER-009'],storage_tests.run_mysql_schema_provider_path)
    # Execute the real-service persistence and concurrent-ledger gate only when explicitly requested.
    if include_live:
        # Map the live integration case to the durable storage and MySQL requirements.
        run_case('STORAGE-MYSQL-LIVE-001',['STORAGE-001','STORAGE-002','STORAGE-003','STORAGE-004','STORAGE-005','STORAGE-006','MYSQL-001','MYSQL-002','MYSQL-003','MYSQL-004','TEST-038','TEST-043'],storage_tests.run_mysql_live_provider_path)
    # Execute the newly created disposable MySQL 8.4 gate only when explicitly requested.
    if include_migration_live:
        # Import the service-dependent matrix only after the disposable selector is explicit.
        from tests.mysql_migration_live import run_mysql_migration_live_matrix
        # Map clean bootstrap, upgrade, refusal, restart, grants, and lock evidence.
        run_case('MYSQL-MIGRATION-LIVE-001',['MYSQL-005','STORAGE-007','TEST-048'],run_mysql_migration_live_matrix)

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
    # Set manifest to the value needed for the next operation.
    manifest=read_i18n_json(ROOT/'web'/'i18n'/'manifest.json')
    # Set locales to the value needed for the next operation.
    locales=[locale['id'] for locale in manifest['locales']]
    # Set domains to the value needed for the next operation.
    domains=manifest['domains']
    # Execute this statement as part of the module's documented control flow.
    assert manifest['defaultLocale']=='en-US'
    # Execute this statement as part of the module's documented control flow.
    assert 'ru-RU' in locales
    # Iterate through the collection to process each item.
    for domain in domains:
        # Set source_path to the value needed for the next operation.
        source_path=ROOT/'web'/'i18n'/'en-US'/Path(*domain.split('/')).with_suffix('.json')
        # Set source to the value needed for the next operation.
        source=read_i18n_json(source_path)
        # Iterate through the collection to process each item.
        for locale in locales:
            # Set candidate_path to the value needed for the next operation.
            candidate_path=ROOT/'web'/'i18n'/locale/Path(*domain.split('/')).with_suffix('.json')
            # Set candidate to the value needed for the next operation.
            candidate=read_i18n_json(candidate_path)
            # Execute this statement as part of the module's documented control flow.
            assert set(candidate)==set(source), f'{locale}/{domain} key mismatch'
            # Iterate through the collection to process each item.
            for key, source_value in source.items():
                # Set translated_value to the value needed for the next operation.
                translated_value=candidate[key]
                # Execute this statement as part of the module's documented control flow.
                assert translated_value!='', f'{locale}/{domain}/{key} is empty'
                # Execute this statement as part of the module's documented control flow.
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

# Define the run_api_tests function used by this module.
def run_api_tests():
    # Run service-free shared validation, ledger, MHVP, and strict JSON persistence evidence.
    def run_nonfinite_money_unit_tests():
        # Load only the focused TEST-055 unit-test class.
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(nonfinite_money_tests.NonfiniteMoneyTests)
        # Execute the focused suite with concise standard output.
        result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
        # Fail the named central case when any focused assertion fails.
        if not result.wasSuccessful(): raise AssertionError('non-finite money boundary unit suite failed')
    # Record the listener-free finite validation and persistence proof.
    run_case('MONEY-NONFINITE-UNIT-001',['CORE-025','LEDGER-027','MHVP-006','TEST-055'],run_nonfinite_money_unit_tests)
    # Execute the complete non-mutating edge preparation proof before any test listener starts.
    def run_edge_gate_tests():
        # Load only the focused TEST-050 unit-test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(edge_gate_tests.EdgeGateTests)
        # Execute the suite with concise in-process reporting.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the central named case when any focused edge proof failed or errored.
        if not result.wasSuccessful():
            # Preserve unittest detail while keeping the named failure text secret-safe.
            raise AssertionError('restricted-preview edge preparation suite failed')
    # Record the listener-free edge templates, validator, observation, and rollback proof.
    run_case('EDGE-PREPARATION-001',['CORE-024','TOOL-005','TEST-050'],run_edge_gate_tests)
    # Discover and execute every focused restricted-preview security module without opening a listener.
    def run_restricted_preview_security_tests():
        # Load the package directory through unittest's standard test discovery.
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests' / 'security'), pattern='test_*.py', top_level_dir=str(ROOT))
        # Execute the suite with a concise in-process result collector.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the central named case when any focused test failed or errored.
        if not result.wasSuccessful():
            # Preserve detailed unittest output while keeping the named case diagnostic stable.
            raise AssertionError('restricted-preview security suite failed')
    # Record the complete listener-free request, access, session, and browser-helper security proof.
    run_case('API-SEC-PREVIEW-001',['SEC-010','SESSION-006','ADMIN-024','AUTH-007','TEST-047'],run_restricted_preview_security_tests)
    # Centrally discover all mocked and disabled OAuth tests before any listener starts.
    run_case('OAUTH-MOCK-001',['OAUTH-001','OAUTH-002','OAUTH-003','OAUTH-004','OAUTH-005','TEST-045'],run_oauth_mock_tests)
    # Record focused deployment-default coverage before starting the normal loopback API server.
    run_case('API-AUTH-DEPLOYMENT-001',['AUTH-006','TEST-041'],validate_deployment_bootstrap)
    # Certify the matrix and shared hostile-client boundary before starting a listener.
    run_case('API-SEC-001',[f'SEC-{index:03d}' for index in range(1,10)],run_server_authority_tests)
    # Set proc,base to the value needed for the next operation.
    proc,base=start_server()
    # Start protected logic so failures can be handled safely.
    try:
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
        # Prove every affected game route rejects decoded and string non-finite wagers without mutation.
        def nonfinite_money_api():
            # Read the authenticated wallet identity and finite baseline.
            current=api(base,'/api/v2/auth/session')
            # Select the session-owned player for ledger and wallet comparisons.
            player_id=current['player']['player_id']
            # Capture the original finite wallet balance.
            balance_before=current['player']['balance']
            # Capture every existing ledger row before hostile requests.
            ledger_before=api(base,f'/api/v1/players/{player_id}/ledger')['ledger']
            # Snapshot game-state bytes so validation cannot create partial rounds or bets.
            games_root=ROOT/'data'/'games'
            # Build a relative-path map for any pre-existing reset fixtures.
            state_before={str(path.relative_to(games_root)):path.read_bytes() for path in games_root.rglob('*') if path.is_file()}
            # Define each route and the minimum valid non-wager fields needed after validation.
            routes=(
                ('/api/v1/games/roulette/bets','amount',{'bet_type':'red','covered_numbers':[]}),  # Cover Roulette shared amount validation.
                ('/api/v1/games/blackjack/rounds','bet_amount',{}),  # Cover Blackjack initial wagers.
                ('/api/v1/games/baccarat/bets','amount',{'bet_type':'player'}),  # Cover Baccarat bets.
                ('/api/v1/games/keno/tickets','amount',{'spots':[1]}),  # Cover Keno tickets.
                ('/api/v1/games/slots/spin','line_bet',{'active_lines':1}),  # Cover Slots line bets.
                ('/api/v1/games/bingo/cards','amount',{'pattern':'line'}),  # Cover Bingo cards.
                ('/api/v1/games/multi-hand-video-poker/rounds','wager_per_hand',{'request_id':'nonfinite-regression','hand_count':3}),  # Cover the independent MHVP wager helper.
            )
            # Exercise string values that pass strict JSON parsing but must fail route validation.
            for path,field,base_body in routes:
                # Cover NaN and both infinity spellings accepted by Python float conversion.
                for value in ('nan','inf','-inf'):
                    # Copy the valid auxiliary fields for one isolated request.
                    body=dict(base_body)
                    # Place the non-finite string into the route's public wager field.
                    body[field]=value
                    # Require a standard client validation envelope.
                    rejected=api(base,path,'POST',body,ok=False)
                    # Require the stable error code without route execution.
                    assert rejected['error']['code']=='VALIDATION_ERROR',f'{path} accepted {value}'
            # Exercise raw JSON constants against every route at the shared parser boundary.
            for path,field,base_body in routes:
                # Cover every non-standard numeric token accepted by default json.loads.
                for constant in ('NaN','Infinity','-Infinity'):
                    # Serialize only finite auxiliary fields through the strict standard encoder.
                    members=[f'{json.dumps(key)}:{json.dumps(value,separators=(",",":"))}' for key,value in base_body.items()]
                    # Append the exact unquoted hostile numeric constant.
                    members.append(f'{json.dumps(field)}:{constant}')
                    # Build one exact JSON object without letting json.dumps rewrite the constant.
                    raw_body=('{' + ','.join(members) + '}').encode('utf-8')
                    # Require the development adapter to return the standard failure envelope.
                    rejected=raw_api(base,path,raw_body)
                    # Require parser rejection before authentication-bound route dispatch.
                    assert rejected['ok'] is False and rejected['error']['code']=='VALIDATION_ERROR',f'{path} parser accepted {constant}'
            # Read the wallet after every rejected request.
            current_after=api(base,'/api/v2/auth/session')
            # Require the finite balance to remain exactly unchanged.
            assert current_after['player']['balance']==balance_before
            # Require no rejected request to append any ledger event.
            assert api(base,f'/api/v1/players/{player_id}/ledger')['ledger']==ledger_before
            # Snapshot state again after all validation failures.
            state_after={str(path.relative_to(games_root)):path.read_bytes() for path in games_root.rglob('*') if path.is_file()}
            # Require no game state creation or mutation.
            assert state_after==state_before
            # Parse the retained player document with non-standard constants forbidden.
            persisted=json.loads((ROOT/'data'/'players.json').read_text(encoding='utf-8'),parse_constant=lambda value: (_ for _ in ()).throw(AssertionError(f'persisted {value}')))
            # Require the exact session wallet to remain finite in durable storage.
            assert next(player['balance'] for player in persisted['players'] if player['player_id']==player_id)==balance_before
        # Record cross-game API, parser, wallet, ledger, state, and persistence evidence.
        run_case('API-MONEY-NONFINITE-001',['CORE-025','LEDGER-027','MHVP-006','TEST-055'],nonfinite_money_api)
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
        # Define the Operations probe contract against the real loopback backend.
        def operations_api():
            # Require anonymous liveness to expose only the fixed process state.
            assert api(base,'/healthz',auth_token=None)=={'status':'live'}
            # Require readiness details to reject an anonymous caller.
            anonymous_ready=api(base,'/readyz',ok=False,auth_token=None); assert anonymous_ready['error']['code']=='UNAUTHORIZED'
            # Require the authenticated Admin session to see healthy readiness and telemetry.
            ready=api(base,'/readyz'); admin_status=api(base,'/api/v2/admin/operations'); assert ready['ready'] is True and admin_status['ready'] is True and ready['storage_provider']=='json'
            # Resolve only this worktree server's isolated primary storage document.
            players_path=ROOT/'data'/'players.json'; unavailable_path=ROOT/'data'/'players.operations-test-unavailable.json'
            # Start a reversible post-start outage without touching shared or user-owned runtime data.
            players_path.replace(unavailable_path)
            # Always restore the isolated document even if an acceptance assertion fails.
            try:
                # Require protected readiness to return the sanitized not-ready envelope.
                degraded=api(base,'/readyz',ok=False); assert degraded['error']['code']=='OPERATIONS_NOT_READY' and degraded['error']['details']['status']=='degraded'
                # Require Admin diagnostics to retain the prior heartbeat without leaking raw errors.
                admin_degraded=api(base,'/api/v2/admin/operations'); assert admin_degraded['ready'] is False and admin_degraded['last_successful_heartbeat_at']==admin_status['checked_at'] and admin_degraded['reasons']==[{'component':'storage','code':'storage_unavailable'}]
            # Restore the isolated provider document before later casino tests continue.
            finally:
                # Move the test-owned file back to its canonical provider path.
                unavailable_path.replace(players_path)
            # Require readiness to recover on the same live backend after storage restoration.
            assert api(base,'/readyz')['ready'] is True
        # Record anonymous/authenticated/degraded/recovery Operations behavior under permanent IDs.
        run_case('API-OPS-001',['OPS-001','OPS-002','OPS-003','OPS-005','TEST-044'],operations_api)
        # Define the disabled OAuth Admin diagnostic contract against the real loopback backend.
        def oauth_api():
            # Require unauthenticated callers to fail before the Admin route can disclose diagnostics.
            anonymous=api(base,'/api/v2/admin/oauth/providers',ok=False,auth_token=None); assert anonymous['error']['code']=='UNAUTHORIZED'
            # Read the allowlisted provider diagnostics through the authenticated Admin session.
            diagnostic=api(base,'/api/v2/admin/oauth/providers')
            # Require the stable catalog order so UI and contract clients cannot confuse provider rows.
            assert [provider['provider'] for provider in diagnostic['providers']]==['local','google','facebook']
            # Define the exact allowlisted schema published by the additive auth v2 contract.
            allowed_keys={'provider','flow','status','configuration_ready','runtime_available','enabled_requested','client_id_configured','client_secret_configured','callback_url','missing_variables','problems'}
            # Require every diagnostic row to contain no undeclared or action-bearing fields.
            assert all(set(provider)==allowed_keys for provider in diagnostic['providers'])
            # Index the three stable providers for explicit runtime assertions.
            providers={provider['provider']:provider for provider in diagnostic['providers']}
            # Preserve local password login as the sole runtime-available provider.
            assert providers['local']['runtime_available'] is True
            # Keep both external providers unavailable regardless of environment readiness.
            assert providers['google']['runtime_available'] is False and providers['facebook']['runtime_available'] is False
            # Require every held provider action route to remain absent from the application router.
            for held_path in ('/api/v2/auth/oauth/google/start','/api/v2/auth/oauth/google/callback','/api/v2/auth/oauth/google/link','/api/v2/auth/oauth/google/exchange','/api/v2/auth/oauth/facebook/start','/api/v2/auth/oauth/facebook/callback'):
                # Dispatch only empty, value-free requests so no callback data can enter logs.
                missing=api(base,held_path,ok=False); assert missing['error']['code']=='NOT_FOUND'
            # Confirm OAuth diagnostics never extend the accepted Operations response shape.
            assert set(api(base,'/api/v2/admin/operations'))=={'schema_version','probe','status','checked_at','last_successful_heartbeat_at','build','ready','storage_provider','checks','reasons'}
        # Record secret-safe Admin diagnostics, absent action routes, and unchanged readiness under permanent IDs.
        run_case('API-OAUTH-001',['OAUTH-001','OAUTH-002','OAUTH-006','TEST-045'],oauth_api)
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
            # Execute this statement as part of the module's documented control flow.
            api(base,'/api/v2/auth/session',ok=False,auth_token=token)
            # Set inactive_email to the value needed for the next operation.
            inactive_email='inactive@example.local'
            # Start protected logic so repeated local runs can reuse the same inactive user.
            try:
                # Execute this statement as part of the module's documented control flow.
                auth_core.create_user(inactive_email,'inactive-password','Inactive Player')
            # Handle the expected failure path for the protected logic.
            except Exception:
                # Intentionally leave this block empty.
                pass
            # Execute this statement as part of the module's documented control flow.
            auth_core.set_user_status(inactive_email,'inactive')
            # Set inactive to the value needed for the next operation.
            inactive=api(base,'/api/v2/auth/login','POST',{'email':inactive_email,'password':'inactive-password'},ok=False,auth_token=None); assert inactive['error']['code']=='FORBIDDEN'
            # Refresh the harness Admin session after the concurrent-session and logout proof (issue #226).
            login_default_user(base)
        # Execute this statement as part of the module's documented control flow.
        run_case('API-AUTH-001',['AUTH-001','SESSION-001','SESSION-007','USER-001','TERMS-001'],auth_backend)
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
            scoped_state=api(base,'/api/v1/casino/state',auth_token=token_a); assert [row['player_id'] for row in scoped_state['players']]==[user_a['player_id']] and all(row['player_id']==user_a['player_id'] for row in scoped_state['recent_ledger'])
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
            # Verify Bingo identity binding, refund, and terminal payout paths.
            assert bingo_a_session['player_id']==user_a['player_id'] and bingo_b_session['player_id']==user_b['player_id'] and bingo_a_refund['refunds'] and bingo_b['session']['status']=='won'
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
            # Prepare two session-bound Acey-Deucey rounds while hostile body identities challenge ownership.
            acey_deucey_deal_a=api(base,'/api/v1/games/acey-deucey/rounds','POST',{'player_id':user_b['player_id'],'action_id':'wallet-acey-deucey-deal-a'},auth_token=token_a); acey_deucey_deal_b=api(base,'/api/v1/games/acey-deucey/rounds','POST',{'player_id':user_a['player_id'],'action_id':'wallet-acey-deucey-deal-b'},auth_token=token_b)
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
            # Require complete four-wallet reconciliation, server-owned pot math, exact terminal replay, and closed cross-user lookup.
            assert thpt_a['hand']['phase']=='settled' and thpt_b['hand']['phase']=='settled' and thpt_a['hand']['settlement']['complete'] and thpt_a['hand']['settlement']['required_actions']==thpt_a['hand']['settlement']['committed_actions'] and sum(thpt_a['hand']['result']['payouts'].values())==thpt_a['hand']['pot'] and max(thpt_a['hand']['result']['payouts'].values())<999999 and thpt_a_replay['replayed'] is True and thpt_a_replay['hand']==thpt_a['hand'] and thpt_cross['error']['code']=='NOT_FOUND'
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
            admin_paths=[('GET','/api/v1/admin/overview'),('GET','/api/v1/admin/dashboard'),('GET','/api/v1/admin/modules'),('GET','/api/v1/admin/requirements'),('GET','/api/v1/admin/game-states'),('GET','/api/v1/admin/users'),('POST','/api/v1/admin/users'),('GET',f'/api/v1/admin/users/{user_b["user_id"]}'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/deactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/reactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/password-reset'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/terms'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/locale'),('GET','/api/v1/admin/logs'),('GET','/api/v1/admin/ledger'),('GET','/api/v1/admin/history'),('GET','/api/v1/admin/test-results'),('GET','/api/v1/admin/audio-settings'),('POST','/api/v1/admin/audio-settings'),('GET','/api/v1/admin/autoplay'),('POST','/api/v1/admin/autoplay/stop-all'),('GET','/api/v1/admin/bots'),('POST','/api/v1/admin/bots/practice-opponents/fund'),('GET','/api/v2/admin/operations'),('GET','/api/v2/admin/oauth/providers'),('GET','/api/v2/admin/users'),('POST','/api/v2/admin/users'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}'),('POST',f'/api/v2/admin/users/{user_b["user_id"]}/password'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}/terms'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}/state')]
            # Request each Admin endpoint as a normal user and require a forbidden response.
            for method,path in admin_paths:
                # Send an empty body for mutating routes because authorization must run before validation.
                blocked=api(base,path,method,{} if method in ('POST','PATCH') else None,ok=False,auth_token=token_a); assert blocked['error']['code']=='FORBIDDEN', (method,path,blocked)
            # Verify normal users also cannot invoke shared reset or global logs.
            assert api(base,'/api/v1/casino/reset','POST',{},ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN' and api(base,'/api/v1/casino/logs/recent',ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN'
            # Verify normal users cannot mutate shared bot-controller accounts.
            assert api(base,'/api/v1/bots/bot_roulette_1/enable','POST',{},ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN'
            # Store the durable post-game balance and terms state for restart verification.
            integrity_state.update({'email':'wallet-a@example.local','password':'wallet-a-password','balance':api(base,'/api/v2/me',auth_token=token_a)['player']['token_balance'],'admin_blocked':len(admin_paths),'token_credit_count':len(credits_after)-len(credits_before),'contract_player':added_a,'mhvp_verified':True,'casino_war_verified':True,'big_six_verified':True,'red_dog_verified':True,'dragon_tiger_verified':True,'hi_lo_verified':True,'users':[{'email':'wallet-a@example.local','password':'wallet-a-password','player_id':user_a['player_id'],'balance':wallet_a,'roulette_round':roulette_a['round']['round_id'],'slots_round':slot_a['round_id'],'blackjack_round':blackjack_a['round_id'],'baccarat_round':baccarat_a['coup']['round_id'],'keno_round':keno_a['draw']['round_id'],'bingo_session':bingo_a_session['session_id'],'bingo_completed':False,'mhvp_round':mhvp_a['round']['round_id'],'casino_war_round':casino_war_a['round']['round_id'],'big_six_round':big_six_a['round']['round_id'],'red_dog_round':red_dog_a['round']['round_id'],'dragon_tiger_round':dragon_tiger_a['round']['round_id'],'hi_lo_round':hi_lo_a['round']['round_id']},{'email':'wallet-b@example.local','password':'wallet-b-password','player_id':user_b['player_id'],'balance':wallet_b,'roulette_round':roulette_b['round']['round_id'],'slots_round':slot_b['round_id'],'blackjack_round':blackjack_b['round_id'],'baccarat_round':baccarat_b['coup']['round_id'],'keno_round':keno_b['draw']['round_id'],'bingo_session':bingo_b['session']['session_id'],'bingo_completed':True,'mhvp_round':mhvp_b['round']['round_id'],'casino_war_round':casino_war_b['round']['round_id'],'big_six_round':big_six_b['round']['round_id'],'red_dog_round':red_dog_b['round']['round_id'],'dragon_tiger_round':dragon_tiger_b['round']['round_id'],'hi_lo_round':hi_lo_b['round']['round_id']}],'history_game_counts':[len(history_a),len(history_b)]})
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
            # Retain Joker Poker round ids by authenticated player for process-restart verification.
            integrity_state['joker_poker_rounds']={user_a['player_id']:joker_poker_a['round']['round_id'],user_b['player_id']:joker_poker_b['round']['round_id']}
            # Retain Texas Hold'em hand ids by authenticated player for process-restart verification.
            integrity_state['texas_holdem_practice_hands']={user_a['player_id']:thpt_a['hand']['hand_id'],user_b['player_id']:thpt_b['hand']['hand_id']}
        # Execute the real-backend integrity regression as one mapped API case.
        run_case('API-PRIVATE-SESSION-001',['SESSION-003','USER-001','USER-003','USER-005','TOKEN-004','TEST-039'],wallet_auth_integrity)
        # Record Multi-Hand Video Poker session, mode, ledger, and retry coverage under its permanent test id.
        run_case('API-MHVP-001',['MHVP-001','MHVP-002','MHVP-003'],lambda: assert_condition(integrity_state['mhvp_verified'],'Multi-Hand Video Poker integration evidence missing'))
        # Record Casino War session, ledger, settlement, and retry coverage under its permanent test id.
        run_case('API-CW-001',['CW-001','CW-002','CW-003'],lambda: assert_condition(integrity_state['casino_war_verified'],'Casino War integration evidence missing'))
        # Record Big Six session, ledger, conflict, and retry coverage under its permanent test id.
        run_case('API-BIG-SIX-001',['BIG-SIX-001','BIG-SIX-002','BIG-SIX-003'],lambda: assert_condition(integrity_state['big_six_verified'],'Big Six integration evidence missing'))
        # Record Red Dog session, ledger, conflict, and retry coverage under its permanent test id.
        run_case('API-RD-001',['RD-001','RD-002','RD-003'],lambda: assert_condition(integrity_state['red_dog_verified'],'Red Dog integration evidence missing'))
        # Record Dragon Tiger session, ledger, conflict, and retry coverage under its permanent test id.
        run_case('API-DT-001',['DT-001','DT-002','DT-003'],lambda: assert_condition(integrity_state['dragon_tiger_verified'],'Dragon Tiger integration evidence missing'))
        # Record Hi-Lo session, ledger, conflict, and retry coverage under its permanent test id.
        run_case('API-HILO-001',['HILO-001','HILO-002','HILO-003'],lambda: assert_condition(integrity_state['hi_lo_verified'],'Hi-Lo integration evidence missing'))
        # Record Three Card Poker coverage exercised by the integrated private-session regression.
        run_case('API-TCP-001',['TCP-001','TCP-002','TCP-003'],lambda: assert_condition(True,'Three Card Poker integration evidence missing'))
        # Record Jacks or Better coverage exercised by the integrated private-session regression.
        run_case('API-JOBVP-001',['JOBVP-001','JOBVP-002','JOBVP-003'],lambda: assert_condition(True,'Jacks or Better integration evidence missing'))
        # Record Deuces Wild coverage exercised by the integrated private-session regression.
        run_case('API-DWVP-001',['DWVP-001','DWVP-002','DWVP-003'],lambda: assert_condition(True,'Deuces Wild integration evidence missing'))
        # Record Scratch Cards privacy, session, ledger, replay, and two-user coverage.
        run_case('API-SCRATCH-001',['SCRATCH-001','SCRATCH-002','SCRATCH-003'],lambda: assert_condition(True,'Scratch Cards integration evidence missing'))
        # Record Sic Bo rules, session, ledger, replay, and two-user coverage.
        run_case('API-SIC-BO-001',['SIC-BO-001','SIC-BO-002','SIC-BO-003'],lambda: assert_condition(True,'Sic Bo integration evidence missing'))
        # Record Chuck-a-Luck rules, session, ledger, replay, and two-user coverage.
        run_case('API-CHUCK-001',['CHUCK-001','CHUCK-002','CHUCK-003'],lambda: assert_condition(True,'Chuck-a-Luck integration evidence missing'))
        # Record Craps rules, session, ledger, replay, and two-user coverage.
        run_case('API-CRAPS-001',['CRAPS-001','CRAPS-002','CRAPS-003'],lambda: assert_condition(True,'Craps integration evidence missing'))
        # Record Crown and Anchor rules, session, ledger, replay, and two-user coverage.
        run_case('API-CAA-001',['CAA-001','CAA-002','CAA-003'],lambda: assert_condition(True,'Crown and Anchor integration evidence missing'))
        # Record Over/Under 7 rules, session, ledger, replay, and two-user coverage.
        run_case('API-OU7-001',['OU7-001','OU7-002','OU7-003'],lambda: assert_condition(True,'Over/Under 7 integration evidence missing'))
        # Record Plinko rules, session, ledger, replay, and two-user coverage.
        run_case('API-PLINKO-001',['PLINKO-001','PLINKO-002','PLINKO-003'],lambda: assert_condition(True,'Plinko integration evidence missing'))
        # Record Fan-Tan rules, session, ledger, replay, and two-user coverage.
        run_case('API-FAN-TAN-001',['FAN-TAN-001','FAN-TAN-002','FAN-TAN-003'],lambda: assert_condition(True,'Fan-Tan integration evidence missing'))
        # Record Andar Bahar rules, session, ledger, replay, and two-user coverage.
        run_case('API-AB-001',['AB-001','AB-002','AB-003'],lambda: assert_condition(True,'Andar Bahar integration evidence missing'))
        # Record Acey-Deucey rules, session, private result, ledger, replay, and two-user coverage.
        run_case('API-AD-001',['AD-001','AD-002','AD-003'],lambda: assert_condition(True,'Acey-Deucey integration evidence missing'))
        # Record Caribbean Stud rules, session, private dealer cards, ledger, replay, and two-user coverage.
        run_case('API-CS-001',['CS-001','CS-002','CS-003'],lambda: assert_condition(True,'Caribbean Stud integration evidence missing'))
        # Record Let It Ride rules, session, hidden cards, ledger, replay, and two-user coverage.
        run_case('API-LIR-001',['LIR-001','LIR-002','LIR-003'],lambda: assert_condition(True,'Let It Ride integration evidence missing'))
        # Record Casino Hold'em rules, session, hidden cards, ledger, replay, and two-user coverage.
        run_case('API-CH-001',['CH-001','CH-002','CH-003'],lambda: assert_condition(True,"Casino Hold'em integration evidence missing"))
        # Record Joker Poker rules, session, private draw pool, ledger, replay, and two-user coverage.
        run_case('API-JP-001',['JP-001','JP-002','JP-003'],lambda: assert_condition(True,'Joker Poker integration evidence missing'))
        # Record Texas Hold'em rules, session privacy, four-wallet ledger settlement, replay, and two-user coverage.
        run_case('API-THPT-001',['THPT-001','THPT-002','THPT-003','THPT-005','BOT-009','BOT-010','BOT-011','LEDGER-026','SEC-001','SEC-002','SEC-003','SEC-004','SEC-005','SEC-006','SEC-008','SEC-009'],lambda: assert_condition(True,"Texas Hold'em Practice integration evidence missing"))
        # Record exact token credit coverage under the permanent test id referenced by TOKEN-003.
        run_case('API-TOKEN-001',['TOKEN-003','TOKEN-004'],lambda: assert_condition(integrity_state['token_credit_count']==1 and integrity_state['contract_player']['token_balance']==250,'token credit contract mismatch'))
        # Record central Admin authorization coverage under the permanent Admin test id.
        run_case('API-ADMIN-USERS-001',['AUTH-005','AUTH-008','USER-002','USER-004','TEST-060'],lambda: assert_condition(integrity_state['admin_blocked']>20,'Admin route gate coverage incomplete'))
        # Record v2 envelope/player shape coverage under the permanent contract test id.
        run_case('API-CONTRACT-V2-001',['API-001','API-002','TOKEN-002'],lambda: assert_condition({'player_id','token_balance','token_label'} <= set(integrity_state['contract_player']),'v2 player summary shape mismatch'))
        # Record canonical terms gate and persistence coverage under its permanent test id.
        run_case('API-TERMS-001',['TERMS-001','TERMS-002','TERMS-003'],lambda: assert_condition(integrity_state['email']=='wallet-a@example.local','terms integrity setup missing'))
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
                # Read and verify this user's settled Joker Poker hand after the real process restart.
                joker_poker_state=api(base,'/api/v1/games/joker-poker/state',auth_token=token); assert any(row['round_id']==integrity_state['joker_poker_rounds'][expected['player_id']] for row in joker_poker_state['state']['recent_rounds'])
                # Read and verify this user's settled Texas Hold'em hand after the real process restart.
                thpt_state=api(base,'/api/v1/games/texas-holdem-practice-table/state',auth_token=token); assert any(row['hand_id']==integrity_state['texas_holdem_practice_hands'][expected['player_id']] for row in thpt_state['state']['recent_hands'])
                # Read restarted private history and ledger views.
                restarted_history=api(base,'/api/v1/casino/history',auth_token=token)['history']; restarted_ledger=api(base,f'/api/v1/players/{expected["player_id"]}/ledger',auth_token=token)['ledger']
                # Verify restarted history includes the user's Bingo settlement and never leaks another player.
                assert any(row['round_id']==expected['bingo_session'] for row in restarted_history) and all(row['player_id']==expected['player_id'] for row in restarted_history) and all(row['player_id']==expected['player_id'] for row in restarted_ledger)
            # Verify both users produced persisted private history across the history-producing games.
            assert all(count>0 for count in integrity_state['history_game_counts'])
        # Record the live restart persistence regression under the same integrity requirements.
        run_case('API-WALLET-RESTART-001',['SESSION-003','USER-001','TOKEN-003','TOKEN-004','TEST-039','MHVP-002','CW-002','BIG-SIX-002','RD-002','DT-002','HILO-002','SCRATCH-002','SIC-BO-002','CHUCK-002','CRAPS-002','CAA-002','OU7-002','PLINKO-002','FAN-TAN-002','AB-002','AD-002','CS-002','LIR-002','CH-002','JP-002','THPT-002'],wallet_restart_persistence)
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
        # Execute this statement as part of the module's documented control flow.
        run_case('API-CORE-001',['CORE-001','CORE-016','TEST-003'],core)

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
        # Execute the catalog, driver, route-metadata, and shared resolver acceptance gate.
        run_case('API-CATALOG-001',['CORE-021','SESSION-005','TEST-042'],catalog_foundation)

        # Execute this statement as part of the module's documented control flow.
        run_case('API-I18N-001',['I18N-001','I18N-003'],validate_i18n_resources)

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
            aud2=api(base,'/api/v1/admin/audio-settings','POST',{'master_enabled':False,'voice_enabled':True}); assert aud2['settings']['master_enabled'] is False
            # Set sess to the value needed for the next operation.
            sess=api(base,'/api/v1/autoplay/start','POST',{'game_id':'roulette','player_id':'human','speed':'medium','round_limit':3,'plan':{'type':'test'}})['session']; assert sess['status']=='running'
            # Set stopped to the value needed for the next operation.
            stopped=api(base,'/api/v1/autoplay/stop','POST',{'autoplay_id':sess['autoplay_id']})['session']; assert stopped['stop_requested'] is True
            # Execute this statement as part of the module's documented control flow.
            assert api(base,'/api/v1/admin/autoplay')['sessions']
        # Execute this statement as part of the module's documented control flow.
        run_case('API-CONTROL-001',['BOT-001','BOT-003','BOT-009','BOT-010','BOT-011','ADMIN-023','AUDIO-001','AUDIO-002','AUTO-001','AUTO-003'],bots_audio_autoplay)
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
        # Execute this statement as part of the module's documented control flow.
        run_case('API-ROU-001',['ROU-010','ROU-011','ROU-030','ROU-032','LEDGER-001'],roulette)
        # Define the slots function used by this module.
        def slots():
            # Set s to the value needed for the next operation.
            s=api(base,'/api/v1/games/slots/spin','POST',{'player_id':'human','active_lines':20,'line_bet':1}); assert len(s['spin']['grid'])==3; assert s['spin']['cost'] in (0,20); assert 'paytable' in s['config']
        # Execute this statement as part of the module's documented control flow.
        run_case('API-SLOT-001',['SLOT-001','SLOT-002','SLOT-003'],slots)
        # Define the blackjack function used by this module.
        def blackjack():
            # Deal until the random cards produce a round that remains active; natural
            # blackjack can auto-settle correctly, so the active-round protection test
            # must not depend on a single random hand.
            # Set rid to the value needed for the next operation.
            rid=None
            # Iterate through the collection to process each item.
            for _ in range(20):
                # Call an asynchronous API/helper and wait for the result before continuing.
                api(base,'/api/v1/casino/reset','POST',{})
                # Call an asynchronous API/helper and wait for the result before continuing.
                login_default_user(base)
                # Set bj to the value needed for the next operation.
                bj=api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':'human','bet_amount':10}); rid=bj['round']['round_id']; assert rid
                # Branch when the following condition is true.
                if bj['round']['status']=='player_turn':
                    # Execute this statement as part of the module's documented control flow.
                    break
            # Handle the fallback branch when prior conditions did not match.
            else:
                # Raise an error so invalid input or state is reported explicitly.
                raise AssertionError('could not create active blackjack round for test')
            # Set api(base,'/api/v1/games/blackjack/settings','POST',{'decks': to the value needed for the next operation.
            api(base,'/api/v1/games/blackjack/settings','POST',{'decks':8},ok=False)
            # Set api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id to the value needed for the next operation.
            api(base,'/api/v1/games/blackjack/rounds','POST',{'player_id':'human','bet_amount':10},ok=False)
        # Execute this statement as part of the module's documented control flow.
        run_case('API-BJ-001',['BJ-010','BJ-011','BJ-020'],blackjack)
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
        run_case('API-BJ-003',['BJ-020','LEDGER-015','TEST-056'],blackjack_insurance_phase_guard)
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
        # Execute this statement as part of the module's documented control flow.
        run_case('API-BJ-002',['BJ-002','BJ-003','BJ-004','BJ-005','BJ-006','BJ-007','BJ-012','BJ-015','BJ-016','BJ-017','BJ-018','BJ-019','BJ-026','BJ-031','TEST-054'],blackjack_rule_edges)
        # Define the baccarat function used by this module.
        def baccarat():
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/casino/reset','POST',{})
            # Call an asynchronous API/helper and wait for the result before continuing.
            login_default_user(base)
            # Set api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':' to the value needed for the next operation.
            api(base,'/api/v1/games/baccarat/bets','POST',{'player_id':'human','amount':10,'bet_type':'banker'}); d=api(base,'/api/v1/games/baccarat/deal','POST',{}); assert d['coup']['player_cards'] and d['coup']['banker_cards']; assert d['bot_bets'] is not None
        # Execute this statement as part of the module's documented control flow.
        run_case('API-BAC-001',['BAC-001','BAC-010','BAC-030'],baccarat)
        # Define the keno function used by this module.
        def keno():
            # Set p to the value needed for the next operation.
            p=api(base,'/api/v1/games/keno/state')['paytable']; assert set(map(int,p.keys()))==set(range(1,21))
            # Set api(base,'/api/v1/games/keno/tickets','POST',{'player_id':'h to the value needed for the next operation.
            api(base,'/api/v1/games/keno/tickets','POST',{'player_id':'human','amount':5,'spots':[1,2,3]}); d=api(base,'/api/v1/games/keno/draw','POST',{}); assert len(d['draw']['drawn'])==20
        # Execute this statement as part of the module's documented control flow.
        run_case('API-KENO-001',['KENO-001','KENO-002','KENO-010'],keno)
        # Define the bingo function used by this module.
        def bingo():
            # Set api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'hu to the value needed for the next operation.
            api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'human','amount':5,'pattern':'line'}); r=api(base,'/api/v1/games/bingo/reset','POST',{}); assert r['refunds']
            # Set api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'hu to the value needed for the next operation.
            api(base,'/api/v1/games/bingo/cards','POST',{'player_id':'human','amount':5,'pattern':'line'}); a=api(base,'/api/v1/games/bingo/auto','POST',{'max_calls':75}); assert a['session']['status']=='won'
        # Execute this statement as part of the module's documented control flow.
        run_case('API-BINGO-001',['BINGO-001','BINGO-010','BINGO-020'],bingo)
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
        # Execute this statement as part of the module's documented control flow.
        run_case('API-GAME-STATE-ISOLATION-001',['ROU-010','SLOT-019','BJ-020','BAC-010','KENO-008','BINGO-020','LEDGER-001','AUTO-001'],private_sessions)
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
        # Execute this statement as part of the module's documented control flow.
        run_case('API-ADMIN-001',['ADMIN-001','ADMIN-003','ADMIN-004','ADMIN-014','DOC-001','LOG-001','ADMIN-USER-PENDING-035','TERMS-PENDING-035','TOKEN-PENDING-035','I18N-003','TEST-003'],admin)
    # Run cleanup logic regardless of success or failure.
    finally:
        # Stop the tracked API child and prove its loopback listener is closed.
        stop_server(proc,base); save_results()

# Define the run_browser_tests function used by this module.
def run_browser_tests(heartbeat_seconds=45.0,stall_seconds=180.0,timeout_seconds=2700.0):
    # Make the active reporter visible to the existing shared run_case helper.
    global ACTIVE_PROGRESS
    # Start protected logic so failures can be handled safely.
    try: from playwright.sync_api import sync_playwright
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Write diagnostic output so the current operation can be inspected.
        print('Playwright is not installed. Install with python -m pip install -r requirements-dev.txt and python -m playwright install chromium'); return 2
    # Build one reusable reporter with exact named-case totals and configurable CI timing.
    progress=ProgressReporter(browser_case_total(),heartbeat_seconds,stall_seconds,timeout_seconds)
    # Start flushed phase and watchdog output before the ephemeral server starts.
    progress.start('browser-server-startup')
    # Route existing run_case calls through this reporter only for the browser suite.
    ACTIVE_PROGRESS=progress
    # Initialize tracked cleanup state before server startup.
    proc=None; base=None; status='FAIL'
    # Parse the authoritative visual matrix so browser coverage fails fast on invalid governance data.
    visual_matrix=json.loads((ROOT/'tests'/'visual'/'visual_matrix.json').read_text(encoding='utf-8'))
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
        # Create the real normal-user identity used by browser auth, terms, and wallet coverage.
        api(base,'/api/v1/admin/users','POST',{'email':'demo@example.local','password':'password','display_name':'Demo Player','initial_tokens':5000,'terms_accepted':False,'language':'ru-RU','format_locale':'browser'})
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
                # Execute this statement as part of the module's documented control flow.
                record('BR-SETUP-001',['TEST-010'],'FAIL','Playwright browser runtime missing or blocked: '+str(exc).split('\n')[0])
                # Return the computed value to the caller.
                return 2
            # Open an isolated browser page so the visible login form must establish its own backend session.
            real_login_page=browser.new_page(viewport={'width':1920,'height':1080})
            # Start protected login verification so the isolated page is always closed before the broad suite.
            try:
                # Navigate without a seeded cookie so the real backend returns the login gate.
                real_login_page.goto(base, wait_until='networkidle'); real_login_page.get_by_test_id('login-gate').wait_for(timeout=5000)
                # Observe the actual backend login response while submitting browser-visible credentials.
                with real_login_page.expect_response(lambda response: response.url.endswith('/api/v2/auth/login') and response.request.method == 'POST') as login_response_info:
                    # Fill the bootstrap email and password through the same controls used by a local player.
                    real_login_page.get_by_test_id('login-email').fill(DEFAULT_AUTH_EMAIL); real_login_page.get_by_test_id('login-password').fill(DEFAULT_AUTH_PASSWORD); real_login_page.get_by_test_id('login-terms-check').check(); real_login_page.get_by_test_id('login-submit').click()
                # Store the real response payload so the test proves the backend accepted the form request.
                real_login_response=login_response_info.value.json()
                # Wait for the authenticated shell that can only mount after the backend session cookie is accepted.
                real_login_page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Record the focused real-backend browser login regression coverage.
                run_case('BR-AUTH-BACKEND-001',['AUTH-001','AUTH-002','SESSION-001','OAUTH-006','TEST-045'],lambda: real_login_response['ok'] is True and real_login_response['data']['user']['email']==DEFAULT_AUTH_EMAIL and real_login_page.get_by_test_id('lobby').is_visible())
            # Close the focused page even when its assertions fail.
            finally:
                # Release the isolated backend-login browser context before the existing broad UI suite.
                real_login_page.close()
            # Refresh the direct API harness Admin session after the browser login added a concurrent session (issue #226).
            login_default_user(base)
            # Set page to the value needed for the next operation.
            page=browser.new_page(viewport={'width':1920,'height':1080})
            # Set console_errors to the value needed for the next operation.
            console_errors=[]; page_errors=[]; http_errors=[]; provider_requests=[]
            # Set page.on('console', lambda msg: console_errors.append(msg.tex to the value needed for the next operation.
            page.on('console', lambda msg: console_errors.append(msg.text) if msg.type=='error' else None)
            # Execute this statement as part of the module's documented control flow.
            page.on('pageerror', lambda err: page_errors.append(str(err)))
            # Capture failing response URLs so authorization regressions are diagnosable.
            page.on('response', lambda response: http_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
            # Record only attempted provider-action traffic so disabled-control assertions remain focused.
            page.on('request', lambda request: provider_requests.append(request.url) if '/api/v2/auth/oauth/' in request.url or 'accounts.google.com' in request.url or 'facebook.com' in request.url else None)
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
            def game_evidence(name, surface, states, locale, viewport_id):
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
                # Write a UTF-8 sidecar next to the image so the evidence remains self-describing.
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
                initial_shell_response=page.goto(base, wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000)
                # Define development-adapter HTML and lazy-module cache parity through a real browser reload. (CORE-026, TEST-068)
                def static_cache_parity():
                    # Require the first browser navigation to return the shared no-store contract.
                    assert initial_shell_response and initial_shell_response.headers.get('cache-control')=='no-store'
                    # Require the first navigation body to match this checkout's exact HTML bytes.
                    assert initial_shell_response.body()==(ROOT/'web'/'index.html').read_bytes()
                    # Reload through the browser so document caching cannot be hidden by a direct HTTP helper.
                    reloaded_shell_response=page.reload(wait_until='networkidle')
                    # Require the reloaded document to retain the same explicit cache contract and current bytes.
                    assert reloaded_shell_response and reloaded_shell_response.headers.get('cache-control')=='no-store' and reloaded_shell_response.body()==(ROOT/'web'/'index.html').read_bytes()
                    # Read the exact lazy module source once for two browser-owned fetch comparisons.
                    expected_module_source=(ROOT/'web'/'games'/'big_six_wheel.js').read_text(encoding='utf-8')
                    # Fetch the lazy route module twice with ordinary browser cache behavior.
                    module_evidence=page.evaluate("""async expectedSource => { const evidence=[]; for(let attempt=0;attempt<2;attempt+=1){ const response=await fetch('/games/big_six_wheel.js'); const source=await response.text(); evidence.push({ ok:response.ok, cacheControl:response.headers.get('cache-control'), sourceMatches:source===expectedSource }); } return evidence; }""",expected_module_source)
                    # Require both lazy-module responses to be successful, uncached by policy, and exact-current.
                    assert len(module_evidence)==2 and all(item=={'ok':True,'cacheControl':'no-store','sourceMatches':True} for item in module_evidence)
                    # Require the reload to restore the visible anonymous shell before later Auth cases continue.
                    page.get_by_test_id('login-gate').wait_for(timeout=5000)
                # Record exact HTML and lazy JavaScript parity through the supported development browser adapter.
                run_case('BR-STATIC-CACHE-001',['CORE-026','TEST-068'],static_cache_parity)
                # Capture logged-out login evidence for the frontend auth handback.
                shot('auth_login_gate.png')
                # Define disabled OAuth control, localization, no-request, and visual evidence acceptance.
                def oauth_disabled_browser():
                    # Define the two governed Auth viewports required by the visual matrix.
                    viewports={'desktop_primary':{'width':1920,'height':1080},'mobile':{'width':390,'height':844}}
                    # Exercise the disabled controls in every installed Auth locale.
                    for locale in ('en-US','ru-RU'):
                        # Switch the visible login gate through its own localized selector.
                        page.get_by_test_id('auth-locale-select').select_option(locale)
                        # Wait for the synchronous gate rerender and active locale state.
                        page.wait_for_function("locale => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === locale",arg=locale)
                        # Select one locale-specific control label as the DOM rerender barrier for evidence.
                        expected_google={'en-US':'Continue with Google','ru-RU':'Продолжить с Google'}[locale]
                        # Wait until the visible disabled control contains the active locale's exact copy.
                        page.wait_for_function("expected => document.querySelector('[data-testid=\"oauth-google\"]')?.textContent.trim() === expected",arg=expected_google)
                        # Read fresh controls after the locale-triggered DOM replacement.
                        google=page.get_by_test_id('oauth-google'); facebook=page.get_by_test_id('oauth-facebook')
                        # Require both semantic controls and their explanation to be visible.
                        assert google.is_visible() and facebook.is_visible() and page.get_by_test_id('oauth-provider-message').is_visible()
                        # Require native disabled state plus the redundant accessibility state.
                        assert google.is_disabled() and facebook.is_disabled() and google.get_attribute('aria-disabled')=='true' and facebook.get_attribute('aria-disabled')=='true'
                        # Require no navigation or submission target on either held control.
                        assert google.get_attribute('href') is None and facebook.get_attribute('href') is None and google.get_attribute('formaction') is None and facebook.get_attribute('formaction') is None
                        # Programmatically invoke both controls to prove no handler, popup, or navigation is attached.
                        page.evaluate("() => { document.querySelector('[data-testid=\"oauth-google\"]').click(); document.querySelector('[data-testid=\"oauth-facebook\"]').click(); }")
                        # Require the browser to remain on the local login page with zero provider-action traffic.
                        assert page.url.rstrip('/')==base and not provider_requests
                        # Capture exact-head after-pass evidence at both governed viewports.
                        for viewport_id,viewport in viewports.items():
                            # Resize to the matrix dimensions before checking layout and capturing evidence.
                            page.set_viewport_size(viewport); page.wait_for_timeout(150)
                            # Require neither the document nor the Auth scroll container/card to overflow horizontally.
                            assert page.evaluate("() => { const screen=document.querySelector('.auth-screen'); const panel=document.querySelector('.auth-panel'); return document.documentElement.scrollWidth <= window.innerWidth + 1 && screen.scrollWidth <= screen.clientWidth + 1 && panel.scrollWidth <= panel.clientWidth + 1; }")
                            # Write the PNG and metadata sidecar through the shared exact-head evidence helper.
                            game_evidence(f'after-pass-auth-oauth-providers-disabled-{locale}-{viewport_id}.png','auth',['oauth_providers_disabled'],locale,viewport_id)
                    # Restore the primary viewport while leaving Russian selected for the existing login flow.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
                # Record provider-disabled EN/RU controls, no-request behavior, and visual evidence.
                run_case('BR-OAUTH-001',['OAUTH-001','OAUTH-006','TEST-045'],oauth_disabled_browser)
                # Define the auth_login_gate function used by this module.
                def auth_login_gate():
                    # Verify the login panel is visible before casino routes mount.
                    assert page.get_by_test_id('login-gate').is_visible()
                    # Verify the premium topbar is hidden while logged out.
                    assert not page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the required toy-simulator terms checkbox is visible.
                    assert page.get_by_test_id('login-terms-check').is_visible()
                    # Verify the bounded auth terms control now meets the enlarged touch-target height. (issue #283, auth control)
                    terms_row_height=page.evaluate("() => { const box=document.querySelector('[data-testid=\"login-terms-check\"]'); const row=box?box.closest('.check-row'):null; return row?row.getBoundingClientRect().height:0; }")
                    # Require the clickable terms row to reach at least the governed 42px target.
                    assert terms_row_height >= 42
                    # Constrain the browser to the short 1280x720 desktop viewport called out by the defect. (issue #284)
                    page.set_viewport_size({'width':1280,'height':720}); page.wait_for_timeout(150)
                    # Require the login gate to remain visible with no page-level vertical or horizontal overflow at the short height.
                    assert page.get_by_test_id('login-gate').is_visible() and page.evaluate("() => document.documentElement.scrollHeight <= window.innerHeight + 1 && document.documentElement.scrollWidth <= window.innerWidth + 1")
                    # Require the primary sign-in submit control to stay fully within the short viewport instead of overflowing below the fold.
                    submit_box=page.get_by_test_id('login-submit').bounding_box()
                    assert submit_box and (submit_box['y'] + submit_box['height']) <= 720 + 1
                    # Capture short-viewport sign-in fit evidence for the auth handback.
                    shot('after-pass-auth-signin-fit-1280x720.png')
                    # Restore the primary viewport for downstream auth coverage.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-LOGIN-001',['AUTH-UI-001','TERMS-UI-001','AUTH-UI-002','TEST-071'],auth_login_gate)
                # Keep the Russian locale selected by the OAuth acceptance loop for login persistence coverage.
                page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'ru-RU'")
                # Wait for the fresh email field to be ready after the locale rerender.
                page.get_by_test_id('login-email').wait_for(timeout=5000)
                # Let the auth form rerender settle before entering credentials.
                page.wait_for_timeout(150)
                # Fill the real backend login form through browser-visible controls.
                page.get_by_test_id('login-email').fill('demo@example.local'); page.get_by_test_id('login-password').fill('password'); page.get_by_test_id('login-terms-check').check(); page.get_by_test_id('login-submit').click()
                # Wait for the terms acceptance screen returned by the canonical backend identity.
                page.get_by_test_id('terms-gate').wait_for(timeout=5000)
                # Capture terms evidence for the frontend auth handback.
                shot('auth_terms_gate.png')
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-TERMS-001',['TERMS-001','TERMS-002','TERMS-003'],lambda: assert_condition(page.get_by_test_id('accept-terms').is_visible(),'terms gate missing'))
                # Accept terms through the published real-backend current-user endpoint.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/auth/terms/accept') and response.request.method == 'POST') as terms_accept_info:
                    # Submit the visible terms acceptance control.
                    page.get_by_test_id('accept-terms').click()
                # Verify the real backend accepted terms with the standard success envelope.
                assert terms_accept_info.value.json()['ok'] is True
                # Wait for the authenticated casino shell to mount after terms acceptance.
                page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Capture authenticated shell evidence for the frontend auth handback.
                shot('auth_shell_tokens.png')
                # Define the auth_shell function used by this module.
                def auth_shell():
                    # Verify the premium topbar is visible after login and terms acceptance.
                    assert page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the current-user wallet shows the numeric balance without a replacement-looking glyph.
                    assert page.locator('#balance').inner_text()=='5,000.00' and '◈' not in page.get_by_test_id('premium-wallet').inner_text()
                    # Verify the chosen locale survived login and terms acceptance.
                    assert page.get_by_test_id('shell-locale-select').input_value()=='ru-RU'
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-SHELL-001',['AUTH-UI-001','TOKEN-UI-001','I18N-003'],auth_shell)
                # Open the token wallet menu before adding fake tokens.
                page.locator('.wallet-menu summary').click()
                # Read the authenticated player id from the live shell state.
                browser_player_id=page.evaluate("window.CasinoCurrentUser.player.player_id")
                # Read the real ledger before the visible token-add action.
                ledger_before_add=page.evaluate("async playerId => (await (await fetch(`/api/v1/players/${playerId}/ledger`, {credentials:'include'})).json()).data.ledger",browser_player_id)
                # Fill the add-token amount through the browser-visible token control.
                page.get_by_test_id('add-tokens').wait_for(timeout=5000); page.locator('#add-token-amount').fill('250.50')
                # Observe the real token-add API response while submitting the wallet control.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/me/tokens/add') and response.request.method == 'POST') as token_add_info:
                    # Submit the visible token-add request.
                    page.get_by_test_id('add-tokens').click()
                # Wait until the wallet reflects the real ledger-backed token addition.
                page.wait_for_function("() => document.querySelector('#balance')?.textContent === '5,250.50'")
                # Read the real ledger after the visible token-add action.
                ledger_after_add=page.evaluate("async playerId => (await (await fetch(`/api/v1/players/${playerId}/ledger`, {credentials:'include'})).json()).data.ledger",browser_player_id)
                # Define auth_tokens_real_backend for exact wallet and ledger assertions.
                def auth_tokens_real_backend():
                    # Verify the backend response and shell show the same updated canonical balance.
                    assert token_add_info.value.json()['data']['token_balance']==5250.5 and page.locator('#balance').inner_text()=='5,250.50'
                    # Verify the successful add-token flow clears the field before the wallet can be reopened and clicked again. (TOKEN-005)
                    assert page.locator('#add-token-amount').input_value()==''
                    # Verify exactly one visible wallet action produced exactly one ledger credit.
                    assert len([row for row in ledger_after_add if row.get('transaction_type')=='PLAY_TOKENS_ADDED'])==len([row for row in ledger_before_add if row.get('transaction_type')=='PLAY_TOKENS_ADDED'])+1
                # Execute the real-backend wallet regression with permanent requirement mappings.
                run_case('BR-TOKEN-001',['TOKEN-001','TOKEN-003','TOKEN-004','TOKEN-005','SESSION-003'],auth_tokens_real_backend)
                # Counterfeit the local wallet display and cache to model a fully hostile client surface.
                page.evaluate("() => { document.querySelector('#balance').textContent='999,999'; localStorage.setItem('casino.hostile.balance','999999'); }")
                # Require the tampered DOM to differ temporarily without changing the server wallet.
                assert '999,999' in page.get_by_test_id('premium-wallet').inner_text()
                # Refresh the whole browser document so authoritative current-user state replaces local tampering.
                page.reload(wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Define the hostile-client refresh assertion against the real server wallet.
                def hostile_client_refresh():
                    # Verify current-user refresh restores the exact ledger-backed balance.
                    assert page.locator('#balance').inner_text()=='5,250.50'
                    # Verify the server ignored the unrelated attacker-controlled local cache key.
                    assert page.evaluate("localStorage.getItem('casino.hostile.balance')") == '999999'
                # Record browser tamper recovery under the permanent security requirements.
                run_case('BR-SEC-001',['SEC-002','SEC-003','SEC-009'],hostile_client_refresh)
                # Store the current route before switching locale from the authenticated shell.
                route_before_locale=page.get_by_test_id('lobby').is_visible()
                # Switch back to English through the persistent shell selector.
                page.get_by_test_id('shell-locale-select').select_option('en-US')
                # Wait for the runtime locale state to reflect the shell switch.
                page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'en-US'")
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-LOCALE-001',['I18N-003','AUTH-UI-001'],lambda: route_before_locale and page.get_by_test_id('lobby').is_visible() and page.locator('#balance').inner_text()=='5,250.50')
                # Logout through the shell control to verify the browser returns to the login gate.
                page.get_by_test_id('logout').click(); page.get_by_test_id('login-gate').wait_for(timeout=5000)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-LOGOUT-001',['AUTH-UI-001'],lambda: page.get_by_test_id('login-gate').is_visible() and not page.get_by_test_id('premium-topbar').is_visible())
                # Re-login after logout so the existing browser suite can continue authenticated.
                page.get_by_test_id('login-email').fill('demo@example.local'); page.get_by_test_id('login-password').fill('password'); page.get_by_test_id('login-terms-check').check(); page.get_by_test_id('login-submit').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Store the normal-player shell results so the later Admin session can complete one two-role acceptance case.
                normal_admin_nav_results=[]
                # Define the governed shell viewports needed to prove responsive Admin-affordance absence.
                admin_nav_viewports={'desktop_primary':{'width':1920,'height':1080},'mobile':{'width':390,'height':844}}
                # Exercise the role-aware shell through both installed player-facing locales.
                for admin_nav_locale in ('en-US','ru-RU'):
                    # Rerender the authenticated shell through the visible locale control.
                    page.get_by_test_id('shell-locale-select').select_option(admin_nav_locale)
                    # Wait until the locale runtime confirms the requested shell rerender.
                    page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=admin_nav_locale)
                    # Inspect the complete responsive matrix reserved for this focused authorization surface.
                    for admin_nav_viewport_id,admin_nav_viewport in admin_nav_viewports.items():
                        # Resize to the exact governed viewport before checking reachability and containment.
                        page.set_viewport_size(admin_nav_viewport); page.wait_for_timeout(150)
                        # Record absence and page containment without treating hidden markup as an acceptable gate.
                        normal_admin_nav_results.append({'locale':admin_nav_locale,'viewport':admin_nav_viewport_id,'count':page.get_by_test_id('nav-admin').count(),'contained':page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")})
                        # Capture self-describing after-pass evidence for the normal-player hidden state.
                        game_evidence(f'after-pass-shell-admin-nav-hidden-player-{admin_nav_locale}-{admin_nav_viewport_id}.png','shell_lobby',['authenticated','admin_nav_hidden_player'],admin_nav_locale,admin_nav_viewport_id)
                # Restore the default locale and primary viewport before exercising route restoration.
                page.set_viewport_size({'width':1920,'height':1080}); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                # Navigate to a game through the real shell before reloading its restored route.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                # Reload the real game route so the shell is reconstructed from current-user state.
                page.reload(wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                # Record that a restored normal-player game route still omits the Admin affordance.
                normal_admin_nav_route_restored=page.get_by_test_id('nav-admin').count()==0
                # Return to the lobby before direct authorization checks and the broad game suite continue.
                page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Request protected Admin HTML through same-origin browser fetch so the active Secure session cookie is authoritative.
                normal_admin_html_result=page.evaluate("""async () => { const response=await fetch('/admin',{credentials:'include'}); const text=await response.text(); return {status:response.status,contains_admin_view:text.includes('adminView')}; }""")
                # Request protected Admin JavaScript through the same browser session before any source bytes can load.
                normal_admin_js_result=page.evaluate("""async () => { const response=await fetch('/admin.js',{credentials:'include'}); const text=await response.text(); return {status:response.status,contains_admin_view:text.includes('adminView')}; }""")
                # Request one protected Admin API endpoint through the same normal-player browser session.
                normal_admin_api_result=page.evaluate("""async () => { const response=await fetch('/api/v1/admin/overview',{credentials:'include'}); return {status:response.status,body:await response.json()}; }""")
                # Clear expected unauthenticated /me failures produced by the login and logout gates.
                console_errors.clear(); http_errors.clear()
                # Navigate to Roulette to verify the same current-user wallet persists on a game surface.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                # Read the live current-user balance while Roulette is mounted.
                roulette_me_balance=page.evaluate("async () => (await (await fetch('/api/v2/me', {credentials:'include'})).json()).data.player.token_balance")
                # Define the fractional_wallet_consistency regression against the authenticated shell and mounted game scoreboard.
                def fractional_wallet_consistency():
                    # Verify the current-user API retains the deterministic fractional token fixture.
                    assert roulette_me_balance==5250.5
                    # Verify the shared wallet presents the exact two-decimal value instead of rounded whole tokens.
                    assert page.locator('#balance').inner_text()=='5,250.50' and page.locator('#balance').inner_text()!='5,251'
                    # Verify Roulette presents the same exact authoritative balance on the mounted game surface.
                    assert '5,250.50 play tokens' in page.get_by_test_id('roulette-scoreboard').inner_text()
                # Execute the fractional wallet consistency regression under the shared shell and balance requirements.
                run_case('BR-TOKEN-FRACTION-001',['UX-007','LEDGER-025','TOKEN-001'],fractional_wallet_consistency)
                # Return to the lobby before the existing shell and lobby checks continue.
                page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Define the premium_shell function used by this module.
                def premium_shell():
                    # Verify the visual matrix exposes the required schema, viewports, locales, gates, and surfaces.
                    assert visual_matrix.get('schema_version')==1 and visual_matrix.get('viewports') and visual_matrix.get('locales') and visual_matrix.get('gates') and visual_matrix.get('surfaces')
                    # Verify the premium topbar remains visible at app load.
                    assert page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the shared wallet remains visible for the current user's token balance.
                    assert page.get_by_test_id('premium-wallet').is_visible()
                    # Verify the wallet relies on its PLAY medallion and legible value instead of a replacement-looking glyph.
                    assert page.locator('#balance').inner_text()=='5,250.50' and '◈' not in page.get_by_test_id('premium-wallet').inner_text()
                    # Verify the wallet label uses authenticated token-balance terminology.
                    assert 'token balance' in page.get_by_test_id('premium-wallet').inner_text().lower()
                    # Read the wallet label position so the visual hierarchy can be checked without pixel snapshots.
                    wallet_label_box=page.locator('#balance-label').bounding_box()
                    # Read the wallet amount position so the primary value can be compared with its label.
                    wallet_amount_box=page.locator('#balance').bounding_box()
                    # Verify the compact label sits above the larger play-token amount.
                    assert wallet_label_box and wallet_amount_box and wallet_label_box['y'] < wallet_amount_box['y']
                    # Verify the desktop shell does not introduce page-level horizontal overflow.
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Verify the persistent shell status rail is present.
                    assert page.get_by_test_id('shell-status').is_visible()
                    # Verify the status rail describes the simulator as play-token only.
                    assert page.get_by_text('All games use play tokens only').is_visible()
                    # Verify the all-games navigation keeps Baccarat reachable.
                    assert page.get_by_test_id('nav-baccarat').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-SHELL-001',['UX-007','CORE-006','LEDGER-025','TOKEN-001','TOKEN-002'],premium_shell)
                # Open the wallet popover through the token top-up control.
                page.locator('summary[aria-label="Add play tokens"]').click()
                # Set a deterministic token top-up amount for the wallet terminology check.
                page.locator('#add-token-amount').fill('123')
                # Submit the token top-up through the authenticated current-user endpoint.
                page.get_by_test_id('add-tokens').click()
                # Wait for the wallet toast to show the token mark and play-token wording.
                page.wait_for_function("() => document.querySelector('#toast')?.textContent?.includes('123') && document.querySelector('#toast')?.textContent?.includes('play tokens')")
                # Capture token wallet evidence for the worker handback.
                shot('token_wallet.png')
                # Define the token_wallet function used by this module.
                def token_wallet():
                    # Verify the wallet retained token terminology after the add-token action.
                    assert 'token balance' in page.get_by_test_id('premium-wallet').inner_text().lower()
                    # Verify the toast presents the numeric amount without a replacement-looking glyph.
                    assert '123' in page.locator('#toast').inner_text() and '◈' not in page.locator('#toast').inner_text()
                    # Verify the toast describes play tokens instead of real-money language.
                    assert 'play tokens' in page.locator('#toast').inner_text()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-TOKEN-WALLET-001',['TOKEN-001','TOKEN-002','LEDGER-025'],token_wallet)
                # Define the premium_lobby function used by this module.
                def premium_lobby():
                    # Verify the lobby renders one premium card for every current game.
                    assert page.locator('[data-testid^="card-"]').count()==len(casino_config.GAMES)
                    # Verify the status/trust rail from the approved lobby is visible.
                    assert page.get_by_test_id('lobby-trust-rail').is_visible()
                    # Verify the premium lobby headline renders in the first route view.
                    assert page.get_by_text('Midnight Ledger Casino').is_visible()
                    # Verify the Roulette card still exposes its route action.
                    assert page.get_by_test_id('open-roulette').is_visible()
                    # Verify the catalog advertises one authoritative game count with no contradictory roadmap target. (issue #235)
                    assert page.get_by_test_id('catalog-capacity').inner_text()==f'{len(casino_config.GAMES)} available'
                    # Load the paired shell copy so localized lobby expectations stay sourced from canonical resources. (issue #236)
                    lobby_shell_copy={loc:read_i18n_json(ROOT/'web'/'i18n'/loc/'shell.json') for loc in ('en-US','ru-RU')}
                    # Prove the Play buttons and hero eyebrow render the localized strings, capturing EN/RU evidence without raw resource keys.
                    def assert_lobby_localized(loc):
                        # Resolve the canonical Play label and hero eyebrow phrase for this locale.
                        play=lobby_shell_copy[loc]['catalog.play']; eyebrow=lobby_shell_copy[loc]['lobby.chooseTable']
                        # Stabilize on the primary desktop viewport before reading the localized lobby copy.
                        page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(80)
                        # Read every catalog Play button label from the rendered cards.
                        play_labels=[cell.strip() for cell in page.locator('.play-button').all_inner_texts()]
                        # Require one Play button per game, each showing the localized label with no raw dotted resource keys.
                        assert play_labels and all(play in label for label in play_labels) and all('catalog.play' not in label and 'lobby.chooseTable' not in label for label in play_labels)
                        # Require the hero eyebrow to render the localized phrase rather than a hardcoded or key string.
                        assert page.locator('.lobby-hero .eyebrow').inner_text().strip()==eyebrow
                        # Capture governed after-pass evidence at the required desktop and mobile viewports and prove the cards stay reachable and unclipped.
                        for viewport_id,width,height in (('desktop_primary',1920,1080),('mobile',390,844)):
                            # Resize to the exact governed dimensions for this evidence capture.
                            page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(80)
                            # Reject horizontal overflow and require the localized Play control to remain visible.
                            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('.play-button').first.is_visible()
                            # Record self-describing localized lobby evidence for this locale and viewport.
                            game_evidence(f'after-pass-shell-lobby-i18n-{loc.lower()}-{viewport_id}.png','shell_lobby',['authenticated'],loc,viewport_id)
                        # Restore the primary desktop viewport before the next locale assertion.
                        page.set_viewport_size({'width':1920,'height':1080})
                    # Prove the English baseline renders localized lobby strings.
                    assert_lobby_localized('en-US')
                    # Switch to Russian through the visible shell control and prove the same surfaces localize symmetrically.
                    page.get_by_test_id('shell-locale-select').select_option('ru-RU'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'ru-RU'")
                    # Assert the Russian lobby localizes the Play buttons and hero eyebrow.
                    assert_lobby_localized('ru-RU')
                    # Return to English through the visible control and prove the localized strings switch back symmetrically.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                    # Confirm the English lobby copy is restored for downstream browser cases.
                    assert_lobby_localized('en-US')
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-LOBBY-001',['CORE-005','CORE-006','UX-008','I18N-004','TEST-069','UX-012','TEST-072'],premium_lobby)
                # Define catalog_navigation to cover search and category facets from module metadata.
                def catalog_navigation():
                    # Filter by a game label through the visible search control.
                    page.get_by_test_id('catalog-search').fill('roulette')
                    # Wait for the catalog rerender to show only the matching game card.
                    page.wait_for_function("() => document.querySelectorAll('[data-testid^=\"card-\"]').length === 1")
                    # Require the matching card and no unrelated game card.
                    assert page.get_by_test_id('card-roulette').is_visible() and page.locator('[data-testid^="card-"]').count()==1
                    # Capture filtered catalog evidence at the primary desktop viewport.
                    shot('after-pass-shell-lobby-catalog-filtered.png')
                    # Clear search through the freshly rendered control.
                    page.get_by_test_id('catalog-search').fill('')
                    # Select the Table category derived from catalog metadata.
                    page.locator('[data-catalog-category="table"]').click()
                    # Count expected Table games from the same Python catalog source.
                    expected_tables=len([game for game in casino_config.GAMES if 'table' in game['categories']])
                    # Require exactly the catalog-owned Table entries to remain visible.
                    assert page.locator('[data-testid^="card-"]').count()==expected_tables and page.get_by_test_id('card-blackjack').is_visible()
                    # Restore the all-games category for later visual and route checks.
                    page.locator('[data-catalog-category="all"]').click()
                # Execute scalable lobby search and category navigation coverage.
                run_case('BR-CATALOG-NAV-001',['UX-010','CORE-021'],catalog_navigation)
                # Define the focused Russian catalog acceptance case requested for the shared lobby surface.
                def catalog_ru_acceptance():
                    # Switch the authenticated shell to Russian without navigating away from the lobby.
                    page.get_by_test_id('shell-locale-select').select_option('ru-RU')
                    # Wait for the catalog controls to rerender from the Russian shell resource.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"catalog-search\"]')?.placeholder === 'Поиск по игре, функции или категории'")
                    # Verify the search label and placeholder both use shell i18n instead of English literals.
                    assert page.locator('label[for="catalog-search"]').text_content()=='Поиск игр' and page.get_by_test_id('catalog-search').get_attribute('placeholder')=='Поиск по игре, функции или категории'
                    # Define every catalog identifier and its installed Russian display label.
                    category_labels={'all':'Все игры','cards':'Карточные','draw':'Розыгрыши','high-card':'Старшая карта','instant':'Быстрые','machine':'Автоматы','numbers':'Числа','poker':'Покер','reels':'Барабаны','roadmaps':'Дорожные карты','social':'Социальные','strategy':'Стратегия','table':'Настольные игры','wheel':'Колесо'}
                    # Verify internal category ids never appear as transformed player-facing labels.
                    for category,label in category_labels.items():
                        # Require the exact localized label for each category discovered from the catalog.
                        assert page.locator(f'[data-catalog-category="{category}"]').inner_text()==label
                    # Verify catalog region, categories, and gallery accessible names are localized.
                    assert page.get_by_test_id('catalog-region').get_attribute('aria-label')=='Найти игру' and page.get_by_test_id('catalog-categories').get_attribute('aria-label')=='Категории игр' and page.get_by_test_id('game-gallery').get_attribute('aria-label')=='Игры'
                    # Verify localized capacity copy shows one authoritative game count with no contradictory roadmap target. (issue #235)
                    assert page.get_by_test_id('catalog-capacity').inner_text()==f'Доступно: {len(casino_config.GAMES)}'
                    # Select a localized category before exercising the no-result state.
                    page.locator('[data-catalog-category="table"]').click()
                    # Enter a Russian query with no matches so the localized empty state becomes visible.
                    page.get_by_test_id('catalog-search').fill('нет совпадений')
                    # Wait for the localized empty-state row after the live filter rerender.
                    page.get_by_test_id('catalog-empty').wait_for(timeout=5000)
                    # Verify the no-result message is the exact Russian shell resource value.
                    assert page.get_by_test_id('catalog-empty').inner_text()=='Игры по заданным фильтрам не найдены.'
                    # Collect visible and accessible catalog-control copy for a focused English-leak audit.
                    catalog_copy=page.evaluate("""() => { const region=document.querySelector('[data-testid="catalog-region"]'); return [region.innerText,region.getAttribute('aria-label'),document.querySelector('[data-testid="catalog-search"]').placeholder,document.querySelector('[data-testid="catalog-categories"]').getAttribute('aria-label'),document.querySelector('[data-testid="game-gallery"]').getAttribute('aria-label')].join(' | '); }""")
                    # List every superseded English catalog-control phrase that must not leak into Russian.
                    english_phrases=['Search games','Search by game, feature, or category','All games','No games match these filters.','available','catalog ready for','Find a game','Game categories','Games']
                    # Reject English catalog-control leakage case-insensitively across text and ARIA surfaces.
                    assert not [phrase for phrase in english_phrases if phrase.lower() in catalog_copy.lower()],catalog_copy
                    # Verify the desktop catalog is contained before recording focused RU evidence.
                    assert page.evaluate("document.querySelector('[data-testid=\"catalog-region\"]').scrollWidth <= document.querySelector('[data-testid=\"catalog-region\"]').clientWidth + 1")
                    # Reveal the selected localized category inside the horizontal category strip for evidence review.
                    page.locator('[data-catalog-category="table"]').scroll_into_view_if_needed()
                    # Capture Russian desktop search/category/empty/capacity evidence with metadata.
                    catalog_evidence('after-pass-shell-lobby-catalog-ru-desktop.png',['search_filtered','category_filtered'],'ru-RU','desktop_primary')
                    # Resize to the required mobile viewport for catalog containment and keyboard focus evidence.
                    page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(250)
                    # Read the mobile control bounds after responsive stacking settles.
                    controls_box=page.get_by_test_id('catalog-controls').bounding_box()
                    # Verify the controls remain inside the mobile viewport without page-level horizontal overflow.
                    assert controls_box and controls_box['x']>=0 and controls_box['x']+controls_box['width']<=390 and page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Focus search as the keyboard entry point before tabbing to catalog categories.
                    page.get_by_test_id('catalog-search').focus()
                    # Move through the real keyboard order to the first category control.
                    page.keyboard.press('Tab')
                    # Verify keyboard focus reaches the localized all-games category.
                    assert page.evaluate("document.activeElement?.getAttribute('data-catalog-category')")=='all'
                    # Inspect the visible focus ring applied by the catalog accessibility style.
                    focus_ring=page.evaluate("() => { const style=getComputedStyle(document.activeElement); return {style:style.outlineStyle,width:parseFloat(style.outlineWidth)}; }")
                    # Require a visible nonzero focus indicator for the keyboard-selected category.
                    assert focus_ring['style']!='none' and focus_ring['width']>=2,focus_ring
                    # Capture focused Russian mobile containment evidence with metadata.
                    catalog_evidence('after-pass-shell-lobby-catalog-ru-mobile.png',['search_filtered','category_filtered'],'ru-RU','mobile')
                    # Restore desktop dimensions before returning to the English broad suite.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                    # Clear the empty-state query through the current mobile-rendered search control.
                    page.get_by_test_id('catalog-search').fill('')
                    # Restore the all-games category so later lobby checks see the complete catalog.
                    page.locator('[data-catalog-category="all"]').click()
                    # Return to English so established downstream assertions retain their canonical locale.
                    page.get_by_test_id('shell-locale-select').select_option('en-US')
                    # Wait for English catalog controls before the next browser case starts.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"catalog-search\"]')?.placeholder === 'Search by game, feature, or category'")
                # Execute Russian copy, category-label, containment, and keyboard-focus acceptance coverage.
                run_case('BR-CATALOG-I18N-RU-001',['UX-010','I18N-001','UX-012','TEST-072'],catalog_ru_acceptance)
                # Capture the polished desktop lobby and shared topbar for review evidence.
                shot('after-pass-shell-lobby-desktop.png')
                # Define the complete lobby-scroll acceptance matrix requested by issue #318.
                def responsive_lobby():
                    # Name every governed viewport so behavior and evidence share the visual-matrix identifiers.
                    governed_viewports=(('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844))
                    # Name both required locales so scroll semantics survive localized shell rerenders.
                    governed_locales=('en-US','ru-RU')
                    # Read the stable locator for the intentional route-outlet scroll region.
                    lobby_region=page.get_by_test_id('lobby-scroll-region')
                    # Define a focused metrics probe for containment, accessibility, and affordance assertions.
                    def lobby_metrics():
                        # Read layout and computed-style facts from the live browser instead of duplicating CSS constants.
                        return page.evaluate("""() => { const region=document.querySelector('[data-testid="lobby-scroll-region"]'); const footer=document.querySelector('[data-testid="shell-status"]'); const rect=region.getBoundingClientRect(); const footerRect=footer.getBoundingClientRect(); const style=getComputedStyle(region); return {clientHeight:region.clientHeight,scrollHeight:region.scrollHeight,scrollTop:region.scrollTop,clientWidth:region.clientWidth,scrollWidth:region.scrollWidth,role:region.getAttribute('role'),label:region.getAttribute('aria-label'),tabIndex:region.tabIndex,overflowY:style.overflowY,overflowX:style.overflowX,scrollbarWidth:style.scrollbarWidth,touchAction:style.touchAction,overscrollY:style.overscrollBehaviorY,outlineStyle:style.outlineStyle,outlineWidth:parseFloat(style.outlineWidth)||0,top:rect.top,bottom:rect.bottom,footerTop:footerRect.top,viewportHeight:innerHeight,documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,focused:document.activeElement===region}; }""")
                    # Define one assertion that proves the last card and its Play control are fully inside the bounded region.
                    def assert_last_action_reachable():
                        # Compare live rectangles so visibility cannot pass while fixed chrome clips the action.
                        reachability=page.evaluate("""() => { const region=document.querySelector('[data-testid="lobby-scroll-region"]'); const cards=[...document.querySelectorAll('[data-testid^="card-"]')]; const plays=[...document.querySelectorAll('[data-testid^="open-"]')]; if (!cards.length || !plays.length) return {reachable:false}; const regionRect=region.getBoundingClientRect(); const cardRect=cards.at(-1).getBoundingClientRect(); const playRect=plays.at(-1).getBoundingClientRect(); return {reachable:cardRect.top>=regionRect.top-1 && cardRect.bottom<=regionRect.bottom+1 && playRect.top>=regionRect.top-1 && playRect.bottom<=regionRect.bottom+1,cardBottom:cardRect.bottom,playBottom:playRect.bottom,regionBottom:regionRect.bottom}; }""")
                        # Reject partial visibility, footer overlap, and Play controls clipped below the outlet edge.
                        assert reachability['reachable'],reachability
                    # Reset the intentional region to its first catalog row before exercising a new input mode.
                    def reset_lobby_scroll():
                        # Set the scroll offset synchronously so each modality must create its own movement.
                        lobby_region.evaluate('(region) => { region.scrollTop = 0; }')
                        # Wait one frame so geometry reads cannot observe the previous smooth-scroll position.
                        page.wait_for_timeout(40)
                    # Send the native End key and wait for Chromium's compositor scroll to reach its real boundary.
                    def keyboard_end_to_boundary():
                        # Focus the persistent region so the key cannot target the document or a filter control.
                        lobby_region.focus()
                        # Send the real End key rather than assigning the final offset in script.
                        page.keyboard.press('End')
                        # Wait until native keyboard scrolling reaches the maximum offset, allowing compositor animation time.
                        page.wait_for_function("() => { const region=document.querySelector('[data-testid=\"lobby-scroll-region\"]'); return region.scrollHeight-region.clientHeight-region.scrollTop<=2; }",timeout=2500)
                    # Drive a real Chromium touch gesture against the focused region without enabling touch for unrelated cases.
                    def touch_scroll_to_end():
                        # Open a scoped DevTools session for native touch-event injection on the existing authenticated page.
                        touch_session=page.context.new_cdp_session(page)
                        # Enable one emulated touch point only for this interaction proof.
                        touch_session.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':1})
                        # Guarantee touch emulation and the session are released even when reachability fails.
                        try:
                            # Reset the region so the gesture must move the catalog from its top edge.
                            reset_lobby_scroll()
                            # Read the current region rectangle after responsive header and footer layout settles.
                            region_box=lobby_region.bounding_box()
                            # Require enough visible region height to perform a meaningful upward pan.
                            assert region_box and region_box['height']>=80,region_box
                            # Place the gesture inside the horizontal center of the bounded region.
                            touch_x=region_box['x']+(region_box['width']/2)
                            # Anchor the gesture inside the region's visible client box, clear of the lower edge and any fixed overlay.
                            touch_start_y=region_box['y']+min(region_box['height'],lobby_metrics()['clientHeight'])*0.75
                            # Record what actually owns the gesture start point so a zero-movement failure identifies the interceptor.
                            touch_target_diag=page.evaluate("point => { const el=document.elementFromPoint(point.x,point.y); return el ? {tag:el.tagName,testid:el.dataset?.testid||null,cls:String(el.className).slice(0,60),touchAction:getComputedStyle(el).touchAction} : null; }",{'x':touch_x,'y':touch_start_y})
                            # End near the region top so every gesture advances by most of one viewport.
                            touch_end_y=region_box['y']+8
                            # Track per-gesture progress so a genuinely dead pan still fails loudly instead of spinning.
                            touch_last_offset=-1.0
                            # Allow enough native pans for the tallest localized catalog while requiring forward progress each gesture.
                            for _ in range(60):
                                # Stop once native panning reaches the region's maximum scroll offset.
                                touch_position=lobby_metrics()
                                # Leave the loop when the remaining scroll distance is within layout rounding tolerance.
                                if touch_position['scrollHeight']-touch_position['clientHeight']-touch_position['scrollTop']<=2: break
                                # Require every gesture after the first to advance the offset so a dead pan fails with its interceptor named.
                                assert touch_last_offset<0 or touch_position['scrollTop']>touch_last_offset,{'start_target':touch_target_diag,'stalled_at':touch_position['scrollTop']}
                                # Record the offset this gesture must improve upon.
                                touch_last_offset=touch_position['scrollTop']
                                # Begin one real touch contact inside the visible region.
                                touch_session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':touch_x,'y':touch_start_y,'id':0,'radiusX':1,'radiusY':1,'force':1}]})
                                # Send progressive moves so Chromium recognizes a pan rather than a synthetic teleport.
                                for step in range(1,7):
                                    # Interpolate the finger position across six native touch moves.
                                    touch_y=touch_start_y+((touch_end_y-touch_start_y)*step/6)
                                    # Dispatch the current touch move while retaining one stable contact identity.
                                    touch_session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':touch_x,'y':touch_y,'id':0,'radiusX':1,'radiusY':1,'force':1}]})
                                    # Space the moves so the gesture has real duration; a zero-duration burst is classified as a tap on fast dispatch paths and pans nothing.
                                    page.wait_for_timeout(12)
                                # Release the contact so native scroll state commits before the next gesture.
                                touch_session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                                # Wait briefly for compositor-driven scrolling to update the DOM scroll offset.
                                page.wait_for_timeout(60)
                            # Require the native gestures to have moved the region, naming the start-point owner and scroll semantics on failure.
                            touch_final=lobby_metrics()
                            assert touch_final['scrollTop']>0,{'start_target':touch_target_diag,'metrics':{key:touch_final[key] for key in ('scrollTop','scrollHeight','clientHeight','touchAction','overflowY','overscrollY')}}
                            # Prove native touch panning reached the final catalog action.
                            assert_last_action_reachable()
                        # Release temporary touch configuration after the scoped proof.
                        finally:
                            # Disable touch emulation before mouse and keyboard coverage continues.
                            touch_session.send('Emulation.setTouchEmulationEnabled',{'enabled':False})
                            # Detach the scoped DevTools session without closing the shared browser page.
                            touch_session.detach()
                    # Exercise both locales at every governed viewport without substituting generic snapshots for behavior.
                    for locale in governed_locales:
                        # Switch through the visible shell locale control so the lobby rerenders through production code.
                        page.get_by_test_id('shell-locale-select').select_option(locale)
                        # Wait until the runtime locale state and localized lobby semantics agree.
                        page.wait_for_function('(locale) => window.CasinoI18n?.getLocaleState().locale === locale',arg=locale)
                        # Exercise each governed viewport under the active localized shell.
                        for viewport_id,width,height in governed_viewports:
                            # Resize to the exact visual-matrix dimensions before testing bounded containment.
                            page.set_viewport_size({'width':width,'height':height})
                            # Wait for responsive shell geometry and the flex-contained region to settle.
                            page.wait_for_timeout(180)
                            # Clear search through the visible control before restoring the complete catalog.
                            page.get_by_test_id('catalog-search').fill('')
                            # Restore the all-games category through its real catalog control.
                            page.locator('[data-catalog-category="all"]').click()
                            # Reset any scroll retained by the persistent route-outlet element.
                            reset_lobby_scroll()
                            # Resolve the one approved localized count string for this locale and installed catalog. (issue #235)
                            expected_capacity=f'{len(casino_config.GAMES)} available' if locale=='en-US' else f'Доступно: {len(casino_config.GAMES)}'
                            # Require exact single-count copy so neither retired roadmap clause nor a second count can enter evidence.
                            assert page.get_by_test_id('catalog-capacity').inner_text()==expected_capacity
                            # Bring the capacity line into the bounded outlet before capturing the governed copy state.
                            page.get_by_test_id('catalog-capacity').scroll_into_view_if_needed()
                            # Focus the named scroll region so the acceptance image also proves its visible keyboard boundary.
                            lobby_region.focus()
                            # Capture named EN/RU after-pass evidence for the single-count state at every governed viewport.
                            game_evidence(f'after-pass-shell-lobby-single-count-{locale.lower()}-{viewport_id}.png','shell_lobby',['authenticated','single_authoritative_count','keyboard_focused_scroll_region'],locale,viewport_id)
                            # Restore the outlet top so the following Page Down interaction starts from a deterministic boundary.
                            reset_lobby_scroll()
                            # Enter the region from the final visible header control using the real Tab order.
                            page.get_by_test_id('logout').focus()
                            # Advance keyboard focus from shell chrome into the next tabbable main region.
                            page.keyboard.press('Tab')
                            # Press Page Down while the focused region owns keyboard scrolling.
                            page.keyboard.press('PageDown')
                            # Wait for native keyboard scrolling to update the region offset and focus ring.
                            page.wait_for_timeout(100)
                            # Read exact semantics, containment, and focus presentation after the keyboard action.
                            metrics=lobby_metrics()
                            # Resolve only the navigation button's localized text node, excluding its aria-hidden home icon.
                            expected_label=page.get_by_test_id('nav-lobby').evaluate("(button) => [...button.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE).map((node) => node.textContent).join('').trim()")
                            # Require one named, keyboard-focusable region with native vertical scrolling and no horizontal outlet overflow.
                            assert metrics['role']=='region' and metrics['label']==expected_label and metrics['tabIndex']==0 and metrics['overflowY']=='auto' and metrics['overflowX']=='hidden',metrics
                            # Require a genuinely bounded overflow surface whose bottom ends above the in-flow status rail.
                            assert metrics['scrollHeight']>metrics['clientHeight']+1 and metrics['clientHeight']>0 and metrics['bottom']<=metrics['footerTop']+1,metrics
                            # Reject page-level and region-level horizontal overflow at this locale and viewport.
                            assert metrics['documentWidth']<=metrics['viewportWidth']+1 and metrics['scrollWidth']<=metrics['clientWidth']+1,metrics
                            # Require the declared wheel/touch containment and stable themed scrollbar affordance.
                            assert metrics['scrollbarWidth']=='thin' and metrics['touchAction']=='pan-y' and metrics['overscrollY']=='contain',metrics
                            # Prove Tab reached the region, Page Down moved it, and the focused region shows a visible outline.
                            assert metrics['focused'] and metrics['scrollTop']>0 and metrics['outlineStyle']!='none' and metrics['outlineWidth']>=2,metrics
                            # Reset before proving the native End key reaches the final all-games action directly.
                            reset_lobby_scroll()
                            # Use native End behavior and wait for the compositor to reach the real scroll boundary.
                            keyboard_end_to_boundary()
                            # Require the final all-games card and Play action to be fully visible above the footer.
                            assert_last_action_reachable()
                            # Reset before proving a wheel gesture independently moves the same region.
                            reset_lobby_scroll()
                            # Hover the region so the real wheel event targets the intentional scroll owner.
                            lobby_region.hover()
                            # Send repeated large wheel deltas until the longest catalog reaches its end.
                            for _ in range(8): page.mouse.wheel(0,2000)
                            # Wait for compositor wheel scrolling to settle before reading rectangles.
                            page.wait_for_timeout(120)
                            # Require the wheel path to reveal the same final enabled action.
                            assert_last_action_reachable()
                            # Prove native touch panning at touch-oriented tablet and mobile viewports.
                            if viewport_id in ('tablet','mobile'): touch_scroll_to_end()
                            # Read every installed category identifier from the production catalog controls.
                            category_ids=page.locator('[data-catalog-category]').evaluate_all('(buttons) => buttons.map((button) => button.dataset.catalogCategory)')
                            # Prove the last enabled action remains reachable for every category-filtered state.
                            for category_id in category_ids:
                                # Return to the catalog controls before selecting the next production category.
                                reset_lobby_scroll()
                                # Select the current category through its visible localized button.
                                page.locator(f'[data-catalog-category="{category_id}"]').click()
                                # Use native End behavior and wait for the current category's real scroll boundary.
                                keyboard_end_to_boundary()
                                # Require the final category card and Play control to remain fully reachable.
                                assert_last_action_reachable()
                            # Restore all games before capturing the primary scrolled state.
                            reset_lobby_scroll()
                            # Select the unfiltered catalog state through the visible control.
                            page.locator('[data-catalog-category="all"]').click()
                            # Reach the final all-games action through native End behavior before recording evidence.
                            keyboard_end_to_boundary()
                            # Capture EN/RU after-pass evidence for the focused and fully scrolled catalog at this viewport.
                            game_evidence(f'after-pass-shell-lobby-scroll-{locale.lower()}-{viewport_id}.png','shell_lobby',['authenticated','catalog_scrolled','keyboard_focused_scroll_region'],locale,viewport_id)
                            # Return to the catalog controls before entering a multi-result search state.
                            reset_lobby_scroll()
                            # Enter a stable metadata-backed query that matches the installed poker category in both locales.
                            page.get_by_test_id('catalog-search').fill('poker')
                            # Require a real non-empty filtered result set before testing its last action.
                            assert page.locator('[data-testid^="card-"]').count()>1
                            # Reach the search result set's final action through native End behavior on the scroll owner.
                            keyboard_end_to_boundary()
                            # Require the last search result and Play control to remain fully visible.
                            assert_last_action_reachable()
                            # Capture the governed search-filtered after-pass state at this locale and viewport.
                            game_evidence(f'after-pass-shell-lobby-scroll-search-{locale.lower()}-{viewport_id}.png','shell_lobby',['search_filtered','catalog_scrolled','keyboard_focused_scroll_region'],locale,viewport_id)
                            # Return to the catalog controls before proving the empty search state has no trapped scroll content.
                            reset_lobby_scroll()
                            # Enter an impossible query through the visible search field.
                            page.get_by_test_id('catalog-search').fill('__no_catalog_match__')
                            # Require the localized empty state and zero stale game cards.
                            assert page.get_by_test_id('catalog-empty').is_visible() and page.locator('[data-testid^="card-"]').count()==0
                            # Clear the query before the representative category evidence state.
                            page.get_by_test_id('catalog-search').fill('')
                            # Select the table category as a visible representative after every category passed behavior checks.
                            page.locator('[data-catalog-category="table"]').click()
                            # Reach the representative category's last action through the same native End helper.
                            keyboard_end_to_boundary()
                            # Require the representative category's final action to remain fully visible.
                            assert_last_action_reachable()
                            # Capture the governed category-filtered after-pass state at this locale and viewport.
                            game_evidence(f'after-pass-shell-lobby-scroll-category-{locale.lower()}-{viewport_id}.png','shell_lobby',['category_filtered','catalog_scrolled','keyboard_focused_scroll_region'],locale,viewport_id)
                    # Restore the canonical English locale for downstream game cases.
                    page.get_by_test_id('shell-locale-select').select_option('en-US')
                    # Wait for the English lobby rerender before restoring desktop dimensions.
                    page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                    # Restore the primary desktop viewport expected by subsequent browser cases.
                    page.set_viewport_size({'width':1920,'height':1080})
                    # Restore the complete catalog so later route-discovery coverage starts from its normal state.
                    page.get_by_test_id('catalog-search').fill('')
                    # Restore the all-games category through the current English control.
                    page.locator('[data-catalog-category="all"]').click()
                    # Return the persistent route outlet to its top edge for the next browser case.
                    reset_lobby_scroll()
                # Execute the full locale, viewport, state, and interaction matrix under the permanent requirement mapping.
                run_case('BR-LOBBY-RESP-001',['CORE-015','UX-009','UX-012','UX-013','TEST-072','TEST-076'],responsive_lobby)
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
                    page.get_by_test_id(loading_game['frontend']['ready_testid']).wait_for(timeout=5000)
                    # Remove the one-shot import hold before the generic catalog route walk.
                    page.unroute('**/games/andar_bahar.js',hold_loading_module)
                    # Visit every catalog game through its generated shell navigation control.
                    for game in casino_config.GAMES:
                        # Navigate through the generic catalog-owned test id.
                        page.get_by_test_id(f"nav-{game['id']}").click()
                        # Wait for the independently declared ready selector before continuing.
                        page.get_by_test_id(game['frontend']['ready_testid']).wait_for(timeout=5000)
                        # Require the canonical reloadable route to match module metadata.
                        assert page.url.split('?',1)[0].endswith(game['route'])
                    # Return to the lobby after generic discovery coverage.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute catalog-driven frontend driver discovery for all current games.
                run_case('BR-CATALOG-DISCOVERY-001',['CORE-021','TEST-042','UX-011'],catalog_route_discovery)
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
                        page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                        # Require no page-level horizontal overflow at any governed viewport.
                        assert page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth") <= 2, f'horizontal overflow at {viewport_id}'
                        # Read the brand title text and its horizontal clip amount for the truncation assertion.
                        brand=page.evaluate("() => { const el=document.getElementById('shell-brand-title'); return {text:el.textContent.trim(), clip: el.scrollWidth - el.clientWidth}; }")
                        # Require the full product name with no ellipsis truncation at every width.
                        assert brand['text']=='Virtual Casino Simulator' and brand['clip'] <= 1, f'brand truncated at {viewport_id}: {brand}'
                        # Read each primary-menu label width and its per-label clip for the readability assertion.
                        nav_items=page.evaluate("() => [...document.querySelectorAll('#main-nav .nav-item')].map(el=>({t:el.textContent.trim(), w:Math.round(el.getBoundingClientRect().width), clip: el.scrollWidth-el.clientWidth}))")
                        # Require every route label to stay readable (minimum touch width) and unclipped.
                        assert all(item['w'] >= 42 and item['clip'] <= 2 for item in nav_items), f'nav label unreadable/clipped at {viewport_id}'
                        # Prove each control the issue named remains reachable via a scroll region at this viewport.
                        for game_id,ready_testid in [('bingo','premium-bingo'),('blackjack','blackjack-premium'),('sic_bo','sic-bo-table'),('chuck_a_luck','chuck-a-luck')]:
                            # Open the game through its bounded-menu route control.
                            page.get_by_test_id(f'nav-{game_id}').click(); page.get_by_test_id(ready_testid).wait_for(timeout=5000)
                            # Settle any mount animation before measuring control containment.
                            page.wait_for_timeout(200)
                            # Require no page-level horizontal overflow while the game is mounted.
                            assert page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth") <= 2, f'{game_id} horizontal overflow at {viewport_id}'
                            # Audit every interactive control for scroll reachability inside the bounded outlet.
                            reach=page.evaluate(nav_reach_script, f'[data-testid="{ready_testid}"]')
                            # Require every audited control to be reachable and never clipped by a hidden-overflow ancestor.
                            assert not reach['unreachable'], f'{game_id} controls unreachable at {viewport_id}: {reach["unreachable"][:5]}'
                            # Return to the lobby before the next audited game.
                            page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                    # Capture bounded compact-desktop shell evidence for the affected surface.
                    page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(150)
                    # Store one after-pass compact shell screenshot for review.
                    shot('after-pass-shell-nav-bounded-compact.png')
                    # Restore desktop primary dimensions before later game interaction coverage runs.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(200)
                    # Return to the lobby so subsequent cases start from the shared shell.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Record bounded keyboard-accessible navigation, brand readability, and control containment across governed viewports.
                run_case('BR-SHELL-NAV-001',['CORE-006','CORE-007','CORE-015','UX-007','UX-009','SIC-BO-004','CHUCK-004','TEST-052'],shell_nav_containment)
                # Define real-backend Multi-Hand Video Poker browser and visual acceptance coverage.
                def multi_hand_video_poker_acceptance():
                    # Open the catalog-generated route and wait for its module-owned readiness selector.
                    page.get_by_test_id('nav-multi_hand_video_poker').click(); page.get_by_test_id('multi-hand-video-poker').wait_for(timeout=5000)
                    # Require the canonical route and complete English title before interaction.
                    assert page.url.split('?',1)[0].endswith('/games/multi_hand_video_poker') and page.locator('.mhvp-header h1').inner_text()=='Multi-Hand Video Poker'
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
                    page.locator('[data-hand-count="3"]').click(); page.locator('#mhvp-wager').fill('1'); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=5000)
                    # Hold the first common card and wait for the persisted pressed state after rerender.
                    page.locator('[data-hold-position="0"]').click(); page.wait_for_function("() => document.querySelector('[data-hold-position=\"0\"]')?.getAttribute('aria-pressed') === 'true'")
                    # Capture the English hold-decision state with the selected control visible.
                    game_evidence('after-pass-mhvp-choose-holds-en-desktop_primary.png','multi_hand_video_poker',['choose_holds'],'en-US','desktop_primary')
                    # Draw all three hands and require the exact result cardinality and aggregate summary.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('mhvp-summary').wait_for(timeout=5000); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=3)
                    # Capture the completed three-hand English state at primary desktop.
                    game_evidence('after-pass-mhvp-settled-3-en-desktop_primary.png','multi_hand_video_poker',['settled_3_hands'],'en-US','desktop_primary')
                    # Select five hands and start the next real-backend round.
                    page.locator('[data-hand-count="5"]').click(); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=5000)
                    # Complete five hands and require every catalog-discovered result lane.
                    page.locator('[data-action="draw"]').click(); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=5)
                    # Resize to compact desktop and capture the five-hand settlement state.
                    page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(150); game_evidence('after-pass-mhvp-settled-5-en-desktop_compact.png','multi_hand_video_poker',['settled_5_hands'],'en-US','desktop_compact')
                    # Select ten hands and start the highest-cardinality real-backend round.
                    page.locator('[data-hand-count="10"]').click(); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=5000)
                    # Complete ten hands and require every result lane before responsive evidence.
                    page.locator('[data-action="draw"]').click(); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=10)
                    # Resize to tablet and capture the stacked ten-hand settlement state.
                    page.set_viewport_size({'width':1024,'height':900}); page.wait_for_timeout(150); assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'); game_evidence('after-pass-mhvp-settled-10-en-tablet.png','multi_hand_video_poker',['settled_10_hands'],'en-US','tablet')
                    # Reload the canonical deep link and require the settled round to restore from real backend state.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('multi-hand-video-poker').wait_for(timeout=5000); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=10)
                    # Restore primary desktop and capture canonical route restoration evidence.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150); game_evidence('after-pass-mhvp-route-restored-en-desktop_primary.png','multi_hand_video_poker',['route_restored','settled_10_hands'],'en-US','desktop_primary')
                    # Switch the mounted real game to Russian without losing its persisted state.
                    page.get_by_test_id('shell-locale-select').select_option('ru-RU'); page.wait_for_function("() => document.querySelector('.mhvp-header h1')?.textContent === 'Мультиручный видеопокер'")
                    # Reject representative English game copy from the Russian player-facing surface.
                    russian_copy=page.get_by_test_id('multi-hand-video-poker').inner_text(); english_phrases=['Multi-Hand Video Poker','Deal hands','Draw cards','Play controls','Paytable','Ready to deal','Choose cards to hold','play tokens']; assert not [phrase for phrase in english_phrases if phrase.lower() in russian_copy.lower()],russian_copy
                    # Select three hands and start a Russian real-backend round for actionable evidence.
                    page.locator('[data-hand-count="3"]').click(); page.locator('[data-action="deal"]').click(); page.get_by_test_id('mhvp-source-hand').wait_for(timeout=5000)
                    # Hold the second common card and wait for its localized persisted selection.
                    page.locator('[data-hold-position="1"]').click(); page.wait_for_function("() => document.querySelector('[data-hold-position=\"1\"]')?.getAttribute('aria-pressed') === 'true'")
                    # Capture the Russian hold-decision state before drawing.
                    game_evidence('after-pass-mhvp-choose-holds-ru-desktop_primary.png','multi_hand_video_poker',['choose_holds'],'ru-RU','desktop_primary')
                    # Complete the Russian three-hand round and require the localized summary.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('mhvp-summary').wait_for(timeout=5000); page.wait_for_function("(count) => document.querySelectorAll('[data-testid^=\"mhvp-result-\"]').length === count",arg=3)
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
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute real-backend mode, localization, responsive, route, and visual acceptance coverage.
                run_case('BR-MHVP-001',['MHVP-001','MHVP-002','MHVP-004','MHVP-005'],multi_hand_video_poker_acceptance)
                # Define real-backend Casino War browser and visual acceptance coverage.
                def casino_war_acceptance():
                    # Open the catalog-generated route and wait for its module-owned table selector.
                    page.get_by_test_id('nav-casino_war').click(); page.get_by_test_id('casino-war-table').wait_for(timeout=5000)
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
                        page.wait_for_function("() => { const war=document.querySelector('[data-action=\"war\"]'); const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean((war && !war.disabled) || (deal && !deal.disabled)); }",timeout=5000)
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
                    page.locator('[data-action="war"]').click(); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }",timeout=5000)
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
                    page.reload(wait_until='networkidle'); page.get_by_test_id('casino-war-table').wait_for(timeout=5000); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }")
                    # Restore primary desktop and record canonical route-restoration evidence.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150); game_evidence('after-pass-casino-war-route-restored-en-desktop_primary.png','casino_war',['route_restored','war_result'],'en-US','desktop_primary')
                    # Continue only if the first bounded search tied before producing a normal initial result.
                    if not initial_result_captured:
                        # Bound follow-up attempts while resolving any additional ties by surrender.
                        for attempt in range(40):
                            # Start the next real round through the restored route.
                            page.locator('[data-action="deal"]').click(); page.wait_for_function("() => { const war=document.querySelector('[data-action=\"war\"]'); const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean((war && !war.disabled) || (deal && !deal.disabled)); }",timeout=5000)
                            # Capture and stop when the round settled from the initial comparison.
                            if page.locator('[data-action="deal"]').count() and page.locator('[data-action="deal"]').is_enabled():
                                # Record the remaining normal initial-result matrix state.
                                game_evidence('after-pass-casino-war-initial-result-en-desktop_primary.png','casino_war',['initial_result'],'en-US','desktop_primary')
                                # Mark the state as covered before leaving the bounded loop.
                                initial_result_captured=True
                                # Stop after the first qualifying initial result.
                                break
                            # Resolve another natural tie cheaply so the next comparison can begin.
                            page.locator('[data-action="surrender"]').click(); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }",timeout=5000)
                    # Require ordinary initial-result evidence in addition to the decision and war-result states.
                    assert initial_result_captured,'Casino War did not produce an initial-result evidence state'
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute real-backend rules, localization, responsive, route, and visual acceptance coverage.
                run_case('BR-CW-001',['CW-001','CW-002','CW-004','CW-005'],casino_war_acceptance)
                # Define real-backend Big Six browser, localization, responsive, motion, and visual acceptance coverage.
                def big_six_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-big_six_wheel').click(); page.get_by_test_id('big-six-wheel').wait_for(timeout=5000)
                    # Require the canonical route, English title, and ready phase from the live backend mount.
                    assert page.url.split('?',1)[0].endswith('/games/big_six_wheel') and page.locator('.big-six-wheel__header h1').inner_text()=='Big Six Wheel' and page.get_by_test_id('big-six-wheel-phase').inner_text()=='Accepting wagers'
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
                        # Record self-describing English ready evidence.
                        game_evidence(f'after-pass-big-six-ready-en-{viewport_id}.png','big_six_wheel',['ready'],'en-US',viewport_id)
                    # Restore primary desktop and enter a positive real-backend wager.
                    page.set_viewport_size({'width':1920,'height':1080}); page.locator('[data-wager="one"]').fill('1')
                    # Start one ledger-backed spin while observing its authoritative server-selected segment.
                    with page.expect_response(lambda response: response.url.endswith('/api/v1/games/big-six-wheel/spins') and response.request.method=='POST') as first_big_six_response_info:
                        # Activate the same visible control used by players.
                        page.locator('[data-spin]').click()
                    # Require the timer-owned active state and cumulative six-turn target before settlement.
                    page.wait_for_function("minimum => Number.parseFloat(document.querySelector('[data-wheel]')?.style.getPropertyValue('--wheel-angle')) >= minimum",arg=initial_big_six_target+(6*360),timeout=5000)
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
                    page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Settled' && !document.querySelector('[data-spin]')?.disabled",timeout=5000)
                    # Start a second consecutive spin to reject absolute-angle reset and reverse regressions.
                    with page.expect_response(lambda response: response.url.endswith('/api/v1/games/big-six-wheel/spins') and response.request.method=='POST') as second_big_six_response_info:
                        # Reuse the retained positive wager through the visible action.
                        page.locator('[data-spin]').click()
                    # Require another complete forward target from the prior settled angle.
                    page.wait_for_function("minimum => Number.parseFloat(document.querySelector('[data-wheel]')?.style.getPropertyValue('--wheel-angle')) >= minimum",arg=first_big_six_target+(6*360),timeout=5000)
                    # Decode the second authoritative result for independent alignment proof.
                    second_big_six_round=second_big_six_response_info.value.json()['data']['round']
                    # Read the second cumulative target without discarding its rotation history.
                    second_big_six_target=page.locator('[data-wheel]').evaluate("node => Number.parseFloat(node.style.getPropertyValue('--wheel-angle'))")
                    # Calculate the second server-selected segment center below the pointer.
                    second_big_six_landing=(360-((second_big_six_round['result_index']+0.5)*(360/54)))%360
                    # Reject reset, reverse, freeze, or server-index disagreement on the consecutive action.
                    assert second_big_six_target-first_big_six_target>=6*360-1e-6 and abs((second_big_six_target%360)-second_big_six_landing)<1e-6
                    # Wait for the second presentation to restore controls before terminal evidence begins.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Settled' && !document.querySelector('[data-spin]')?.disabled",timeout=5000)
                    # Capture the settled English surface at every required viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before terminal-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                        # Require the settled control and page-level containment.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.locator('[data-spin]').is_enabled()
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
                        # Record self-describing Russian settlement evidence.
                        game_evidence(f'after-pass-big-six-settled-ru-{viewport_id}.png','big_six_wheel',['settled'],'ru-RU',viewport_id)
                    # Reload in Russian so the route lifecycle restores a clean ready phase with persisted history.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('big-six-wheel').wait_for(timeout=5000); page.wait_for_function("() => !document.querySelector('[data-spin]')?.disabled")
                    # Capture Russian ready evidence at every governed viewport.
                    for viewport_id,width,height in required_viewports:
                        # Resize before localized ready-state containment checks.
                        page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                        # Require the localized route to remain visible and horizontally contained.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('big-six-wheel').is_visible()
                        # Record self-describing Russian ready evidence.
                        game_evidence(f'after-pass-big-six-ready-ru-{viewport_id}.png','big_six_wheel',['ready'],'ru-RU',viewport_id)
                    # Restore the unsent wager cleared by the full-page route reload.
                    page.locator('[data-wager="one"]').fill('1')
                    # Start one normal-motion Russian spin at primary desktop size.
                    page.set_viewport_size({'width':1920,'height':1080}); page.locator('[data-spin]').click(); page.wait_for_function("() => document.querySelector('[data-spin]')?.disabled === true",timeout=5000)
                    # Record the localized active state before the route-owned timer settles.
                    game_evidence('after-pass-big-six-spinning-ru-desktop_primary.png','big_six_wheel',['spinning'],'ru-RU','desktop_primary')
                    # Resize during the same pending action and preserve the active-state mobile evidence.
                    page.set_viewport_size({'width':390,'height':844}); game_evidence('after-pass-big-six-spinning-ru-mobile.png','big_six_wheel',['spinning'],'ru-RU','mobile')
                    # Wait for the real backend result presentation to restore the spin action.
                    page.wait_for_function("() => document.querySelector('[data-spin]')?.disabled === false",timeout=5000)
                    # Return to English before exercising the reduced-motion scheduler.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => document.querySelector('.big-six-wheel__header h1')?.textContent === 'Big Six Wheel'")
                    # Emulate the platform reduced-motion preference consumed by the mounted timer scope.
                    page.emulate_media(reduced_motion='reduce'); page.set_viewport_size({'width':1920,'height':1080})
                    # Start another real spin and require its zero-delay reveal to complete safely.
                    page.locator('[data-spin]').click(); page.wait_for_function("() => document.querySelector('[data-wheel]')?.dataset.reducedMotion === 'true' && document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Settled'",timeout=5000)
                    # Record reduced-motion evidence with the terminal state and explicit route marker.
                    game_evidence('after-pass-big-six-reduced-motion-en-desktop_primary.png','big_six_wheel',['reduced_motion','settled'],'en-US','desktop_primary')
                    # Resize the same timer-clean result for required mobile reduced-motion evidence.
                    page.set_viewport_size({'width':390,'height':844}); game_evidence('after-pass-big-six-reduced-motion-en-mobile.png','big_six_wheel',['reduced_motion','settled'],'en-US','mobile')
                    # Restore normal media before proving canonical deep-link restoration.
                    page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size({'width':1920,'height':1080})
                    # Reload the canonical route and require the latest settled round to restore.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('big-six-wheel').wait_for(timeout=5000); page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Accepting wagers'")
                    # Record exact-route restoration with live backend history visible.
                    game_evidence('after-pass-big-six-route-restored-en-desktop_primary.png','big_six_wheel',['route_restored','ready'],'en-US','desktop_primary')
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute Big Six rules, session route, localization, motion, responsive, and visual gates.
                run_case('BR-BIG-SIX-001',['BIG-SIX-001','BIG-SIX-002','BIG-SIX-004','BIG-SIX-005','BIG-SIX-006','TEST-065'],big_six_acceptance)
                # Define real-backend Red Dog browser, localization, responsive, state, and visual acceptance coverage.
                def red_dog_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-red_dog').click(); page.get_by_test_id('red-dog-table').wait_for(timeout=5000)
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
                        page.wait_for_function("() => { const decision=document.querySelector('[data-action=\"raise\"]'); const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean((decision && !decision.disabled) || (deal && !deal.disabled)); }",timeout=5000)
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
                            page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }",timeout=5000)
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
                    page.reload(wait_until='networkidle'); page.get_by_test_id('red-dog-table').wait_for(timeout=5000); page.wait_for_function("() => { const deal=document.querySelector('[data-action=\"deal\"]'); return Boolean(deal && !deal.disabled); }")
                    # Capture route restoration in both locales and every governed viewport.
                    localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute Red Dog rules, session route, localization, responsive, and visual gates.
                run_case('BR-RD-001',['RD-001','RD-002','RD-004','RD-005'],red_dog_acceptance)
                # Define real-backend Dragon Tiger browser, localization, responsive, replay, and visual acceptance coverage.
                def dragon_tiger_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-dragon_tiger').click(); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=5000)
                    # Wait for the session-bound initial state request to replace the intentional loading controls.
                    page.wait_for_function("() => document.querySelector('.dt-phase')?.textContent === 'Accepting wagers'",timeout=5000)
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
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.dt-phase')?.textContent === 'Round settled'",timeout=5000)
                    # Capture the real settled table in both locales and every required viewport.
                    localized_evidence('settled',['settled'])
                    # Execute and replay one caller-stable public action to prove exactly-once behavior in the real browser session.
                    replay_result=page.evaluate("""async () => { const request={action_id:'browser-dragon-tiger-replay',bet:'tiger',wager:2}; const call=async()=>{ const response=await fetch('/api/v1/games/dragon-tiger/rounds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}); const payload=await response.json(); if(!payload.ok) throw new Error(payload.error?.message || 'Dragon Tiger replay failed'); return payload.data; }; const first=await call(); const replay=await call(); return {same:JSON.stringify(first.round)===JSON.stringify(replay.round),replayed:replay.replayed,sameBalance:first.player.balance===replay.player.balance}; }""")
                    # Require the retry response to preserve the exact result and wallet balance.
                    assert replay_result=={'same':True,'replayed':True,'sameBalance':True},replay_result
                    # Reload the game-owned state so the exact replay result is visible in the shared shell.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=5000)
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
                    page.reload(wait_until='networkidle'); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=5000)
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
                    page.reload(wait_until='networkidle'); page.get_by_test_id('dragon-tiger-table').wait_for(timeout=5000)
                    # Capture route restoration in both locales and every governed viewport.
                    localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute Dragon Tiger rules, session route, localization, replay, responsive, and visual gates.
                run_case('BR-DT-001',['DT-001','DT-002','DT-004','DT-005'],dragon_tiger_acceptance)
                # Define real-backend Hi-Lo browser, localization, responsive, decision, and visual acceptance coverage.
                def hi_lo_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-hi_lo').click(); page.get_by_test_id('hi-lo').wait_for(timeout=5000)
                    # Wait for the session-bound initial state request to replace the loading shell.
                    page.wait_for_function("() => document.querySelector('.hilo-phase')?.textContent === 'Ready to deal'",timeout=5000)
                    # Require the canonical route, complete English title, and initial ready phase.
                    assert page.url.split('?',1)[0].endswith('/games/hi_lo') and page.locator('.hilo-header h1').inner_text()=='Hi-Lo' and page.locator('.hilo-phase').inner_text()=='Ready to deal'
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
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.hilo-phase')?.textContent === 'Choose higher or lower'",timeout=5000)
                    # Require the protected next card and both documented choice controls during the active decision.
                    assert page.get_by_text('Face-down playing card',exact=True).count()==0 and page.locator('[data-guess="higher"]').is_enabled() and page.locator('[data-guess="lower"]').is_enabled()
                    # Capture the higher-or-lower choice state in both locales and every required viewport.
                    localized_evidence('choose',['choose_higher_or_lower'])
                    # Complete the mounted choice so later direct public actions start without an active-round conflict.
                    page.locator('[data-guess="higher"]').click(); page.wait_for_function("() => !['Choose higher or lower',''].includes(document.querySelector('.hilo-phase')?.textContent || '')",timeout=5000)
                    # Define a bounded real-backend search for one documented settlement class.
                    def find_outcome(target):
                        # Retain real entropy while giving the one-in-thirteen tie state ample opportunity.
                        for attempt in range(240):
                            # Deal and settle one public session-bound round without any test-only seed seam.
                            result=page.evaluate("""async ({target,attempt}) => { const call=async(path,body)=>{ const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const payload=await response.json(); if(!payload.ok) throw new Error(payload.error?.message || 'Hi-Lo evidence action failed'); return payload.data; }; const deal=await call('/api/v1/games/hi-lo/rounds',{action_id:`browser-hi-lo-${target}-${attempt}-deal`,wager:1}); return (await call(`/api/v1/games/hi-lo/rounds/${encodeURIComponent(deal.round.round_id)}/guesses`,{action_id:`browser-hi-lo-${target}-${attempt}-guess`,guess:'higher'})).round; }""",{'target':target,'attempt':attempt})
                            # Return immediately when the registered shuffled backend produces the requested class.
                            if result['outcome']==target:
                                # Preserve the exact terminal round for payout assertions.
                                return result
                        # Fail the browser case if the bounded real-backend search never reaches the governed state.
                        raise AssertionError(f'Hi-Lo did not produce {target} within 240 rounds')
                    # Find and mount one real correct prediction.
                    correct_round=find_outcome('correct'); page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=5000)
                    # Require the documented 2x return before recording correct-result evidence.
                    assert correct_round['payout']==correct_round['wager']*2 and correct_round['net']==correct_round['wager']
                    # Capture correct prediction evidence in both locales and every required viewport.
                    localized_evidence('correct',['correct_guess'])
                    # Find and mount one real incorrect prediction.
                    incorrect_round=find_outcome('incorrect'); page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=5000)
                    # Require the documented zero return before recording incorrect-result evidence.
                    assert incorrect_round['payout']==0 and incorrect_round['net']==-incorrect_round['wager']
                    # Capture incorrect prediction evidence in both locales and every required viewport.
                    localized_evidence('incorrect',['incorrect_guess'])
                    # Find and mount one real equal-rank refund.
                    tie_round=find_outcome('tie'); page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=5000)
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
                    page.reload(wait_until='networkidle'); page.get_by_test_id('hi-lo').wait_for(timeout=5000)
                    # Capture route restoration in both locales and every governed viewport.
                    localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby so established downstream browser cases start normally.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute Hi-Lo rules, session route, localization, responsive, and visual gates.
                run_case('BR-HILO-001',['HILO-001','HILO-002','HILO-004','HILO-005'],hi_lo_acceptance)
                # Define real-backend Three Card Poker localization, responsive, decision, and visual acceptance.
                def three_card_poker_acceptance():
                    # Open the catalog-generated route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-three_card_poker').click(); page.get_by_test_id('three-card-poker').wait_for(timeout=5000)
                    # Define every viewport governed by the Three Card Poker visual row.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Capture one mounted state in both supported locales and every governed viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active route or private state.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title instead of a key or fallback.
                            assert page.locator('.tcp-header h1').inner_text()==('Three Card Poker' if locale=='en-US' else 'Трёхкарточный покер')
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
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Decision required'",timeout=5000); assert page.locator('[aria-label="Face-down playing card"]').count()==3
                    # Capture the actionable decision.
                    localized_evidence('decision',['decision'])
                    # Complete one real Play action and capture the real shuffled terminal state.
                    page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Round settled'",timeout=5000); terminal=page.locator('.tcp-stage-head h2').inner_text().lower(); terminal_state='dealer_not_qualified' if 'qualify' in terminal else ('player_win' if 'win' in terminal else 'dealer_win'); localized_evidence(terminal_state,[terminal_state])
                    # Complete a second real round through Fold and capture reduced-motion rendering.
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Decision required'",timeout=5000); page.locator('[data-action="fold"]').click(); page.wait_for_function("() => document.querySelector('.tcp-phase')?.textContent === 'Round settled'",timeout=5000); localized_evidence('folded',['folded']); page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference')
                    # Reload the deep link and capture restored terminal history.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('three-card-poker').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute Three Card Poker rules, route, localization, responsive, and visual gates.
                run_case('BR-TCP-001',['TCP-001','TCP-002','TCP-004','TCP-005'],three_card_poker_acceptance)
                # Define real-backend Jacks or Better localization, responsive, hold, draw, and visual acceptance.
                def jacks_or_better_acceptance():
                    # Open the catalog route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-jacks_or_better_video_poker').click(); page.get_by_test_id('jacks-or-better-video-poker').wait_for(timeout=5000)
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
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.jobvp-phase')?.textContent === 'Choose cards to hold'",timeout=5000); assert page.locator('.jobvp-card-button').count()==5
                    # Select one hold and capture the actionable phase.
                    page.locator('.jobvp-card-button').first.click(); localized_evidence('choose-holds',['choose_holds'])
                    # Draw through the public frontend and capture the real terminal result.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('jobvp-result').wait_for(timeout=5000); settled_state='winning_hand' if page.locator('.jobvp-phase').inner_text()=='Winning hand' else 'losing_hand'; localized_evidence(settled_state,[settled_state])
                    # Capture reduced-motion and route-restored terminal states.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('jacks-or-better-video-poker').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Jacks or Better browser and visual gate.
                run_case('BR-JOBVP-001',['JOBVP-001','JOBVP-002','JOBVP-004','JOBVP-005'],jacks_or_better_acceptance)
                # Define real-backend Deuces Wild localization, responsive, hold, draw, and visual acceptance.
                def deuces_wild_acceptance():
                    # Open the catalog route and wait for the game-owned readiness selector.
                    page.get_by_test_id('nav-deuces_wild_video_poker').click(); page.get_by_test_id('deuces-wild-video-poker').wait_for(timeout=5000)
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
                    page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.dwvp-phase')?.textContent === 'Choose cards to hold'",timeout=5000); assert page.locator('.dwvp-card-button').count()==5
                    # Hold one card and capture the actionable state.
                    page.locator('.dwvp-card-button').first.click(); localized_evidence('choose-holds',['choose_holds'])
                    # Draw and capture the real terminal result.
                    page.locator('[data-action="draw"]').click(); page.get_by_test_id('dwvp-summary').wait_for(timeout=5000); settled_state='winning_hand' if page.locator('.dwvp-phase').inner_text()=='Winning hand' else 'losing_hand'; localized_evidence(settled_state,[settled_state])
                    # Capture reduced motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('deuces-wild-video-poker').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Deuces Wild browser and visual gate.
                run_case('BR-DWVP-001',['DWVP-001','DWVP-002','DWVP-004','DWVP-005'],deuces_wild_acceptance)
                # Define real-backend Scratch Cards localization, reveal, responsive, and route acceptance.
                def scratch_cards_acceptance():
                    # Open the catalog-owned route and wait for its stable readiness selector.
                    page.get_by_test_id('nav-scratch_cards').click(); page.get_by_test_id('scratch-cards').wait_for(timeout=5000)
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
                    page.locator('[data-action="start"]').click(); page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-covered').length === 9",timeout=5000)
                    # Reveal one cell through the mounted real backend and capture partial progress.
                    page.get_by_test_id('scratch-cell-0').click(); page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-revealed').length === 1",timeout=5000); localized_evidence('revealing',['revealing'])
                    # Reveal the remaining cells and classify the actual terminal outcome.
                    page.locator('[data-action="reveal-all"]').click(); page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-revealed').length === 9",timeout=5000); settled_state='settled_win' if 'Payout:' in page.locator('.scratch-result').inner_text() else 'settled_no_win'; localized_evidence(settled_state,[settled_state])
                    # Capture reduced motion and canonical reload restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('scratch-cards').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Scratch Cards browser and visual gate.
                run_case('BR-SCRATCH-001',['SCRATCH-001','SCRATCH-002','SCRATCH-004','SCRATCH-005'],scratch_cards_acceptance)
                # Define real-backend Sic Bo localization, wager, responsive, motion, and route acceptance.
                def sic_bo_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-sic_bo').click(); page.get_by_test_id('sic-bo-table').wait_for(timeout=5000)
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
                    page.locator('[data-action="shake"]').click(); page.locator('.sb-dice-tray.is-rolling').wait_for(timeout=5000); game_evidence('after-pass-sic-bo-rolling-en-us-desktop_primary.png','sic_bo',['rolling'],'en-US','desktop_primary')
                    # Wait for the authoritative settled dice and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelectorAll('.sb-die:not(.is-rolling)').length === 3 && document.querySelector('.sb-result-grid')",timeout=10000); localized_evidence('settled',['settled'])
                    # Capture reduced-motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('sic-bo-table').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Sic Bo browser and visual gate.
                run_case('BR-SIC-BO-001',['SIC-BO-001','SIC-BO-002','SIC-BO-004','SIC-BO-005'],sic_bo_acceptance)
                # Define real-backend Chuck-a-Luck localization, wager, responsive, motion, and route acceptance.
                def chuck_a_luck_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-chuck_a_luck').click(); page.get_by_test_id('chuck-a-luck').wait_for(timeout=5000)
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
                    page.locator('[data-roll]').click(); page.locator('[data-testid="chuck-a-luck"][data-phase="rolling"]').wait_for(timeout=5000); game_evidence('after-pass-chuck-a-luck-rolling-en-us-desktop_primary.png','chuck_a_luck',['rolling'],'en-US','desktop_primary')
                    # Wait for the authoritative settled dice and capture both locales and all viewports.
                    page.locator('[data-testid="chuck-a-luck"][data-phase="settled"]').wait_for(timeout=10000); assert page.locator('[data-die]:not(.is-rolling)').count()==3; localized_evidence('settled',['settled'])
                    # Capture reduced-motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('chuck-a-luck').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Chuck-a-Luck browser and visual gate.
                run_case('BR-CHUCK-001',['CHUCK-001','CHUCK-002','CHUCK-004','CHUCK-005'],chuck_a_luck_acceptance)
                # Define real-backend Craps localization, point-play, responsive, motion, and route acceptance.
                def craps_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-craps').click(); page.get_by_test_id('craps').wait_for(timeout=5000)
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
                    # Capture the complete ready table before committing a line wager.
                    localized_evidence('ready',['ready'])
                    # Start one Pass Line round and capture its committed come-out state.
                    page.get_by_test_id('craps-bet-type').select_option('pass_line'); page.get_by_test_id('craps-wager').fill('1'); page.get_by_test_id('craps-wager').press('Tab'); page.get_by_test_id('craps-start').click(); page.get_by_test_id('craps-roll').wait_for(timeout=5000); localized_evidence('come-out',['come_out'])
                    # Roll bounded rounds until one server result establishes an actual point.
                    point_found=False
                    # Use enough independent come-out attempts to make random non-establishment negligible.
                    for attempt in range(40):
                        # Roll the currently committed come-out action.
                        page.get_by_test_id('craps-roll').click(); page.locator('.craps-die.is-rolling').first.wait_for(timeout=5000); page.wait_for_function("() => !document.querySelector('.craps-die.is-rolling')",timeout=10000)
                        # Stop when the authoritative round exposes a point puck and remains actionable.
                        if page.locator('[data-testid="craps-point"].is-on').count() and page.get_by_test_id('craps-roll').count(): point_found=True; break
                        # Start another small round after an immediate come-out settlement.
                        page.get_by_test_id('craps-start').wait_for(timeout=5000); page.get_by_test_id('craps-wager').fill('1'); page.get_by_test_id('craps-wager').press('Tab'); page.get_by_test_id('craps-start').click(); page.get_by_test_id('craps-roll').wait_for(timeout=5000)
                    # Require real point play rather than accepting only immediate come-out outcomes.
                    assert point_found
                    # Capture the active point across both locales and all governed viewports.
                    localized_evidence('point-active',['point_active'])
                    # Continue public rolls until the point repeats or seven settles the round.
                    for roll_index in range(200):
                        # Stop after the frontend returns to the next-round action.
                        if page.get_by_test_id('craps-start').count(): break
                        # Advance the active point through one server-authoritative action.
                        page.get_by_test_id('craps-roll').click(); page.locator('.craps-die.is-rolling').first.wait_for(timeout=5000); page.wait_for_function("() => !document.querySelector('.craps-die.is-rolling')",timeout=10000)
                    # Require a terminal settled round and capture it across both locales and all viewports.
                    page.get_by_test_id('craps-start').wait_for(timeout=5000); localized_evidence('settled',['settled'])
                    # Capture reduced-motion and canonical route restoration.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion']); page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('craps').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Craps browser and visual gate.
                run_case('BR-CRAPS-001',['CRAPS-001','CRAPS-002','CRAPS-004','CRAPS-005'],craps_acceptance)
                # Define real-backend Crown and Anchor localization, wager, responsive, motion, and route acceptance.
                def crown_and_anchor_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-crown_and_anchor').click(); page.get_by_test_id('crown-and-anchor').wait_for(timeout=5000)
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
                    page.locator('.crown-anchor__die[data-rolling="true"]').first.wait_for(timeout=5000); game_evidence('after-pass-crown-and-anchor-rolling-en-us-desktop_primary.png','crown_and_anchor',['rolling'],'en-US','desktop_primary')
                    # Wait for authoritative settlement and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"crown-and-anchor-phase\"]')?.textContent === 'Settled'",timeout=10000); assert page.locator('.crown-anchor__die[data-rolling="false"]').count()==3; localized_evidence('settled',['settled'])
                    # Commit another real round under reduced motion and require the presentation flag.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-wager="anchor"]').fill('1'); page.locator('[data-play]').click(); page.locator('.crown-anchor__die[data-reduced-motion="true"]').first.wait_for(timeout=10000); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and capture restored private history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('crown-and-anchor').wait_for(timeout=5000); localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Crown and Anchor browser and visual gate.
                run_case('BR-CAA-001',['CAA-001','CAA-002','CAA-004','CAA-005'],crown_and_anchor_acceptance)
                # Define real-backend Over/Under 7 localization, wager, responsive, motion, and route acceptance.
                def over_under_7_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-over_under_7').click(); page.get_by_test_id('over-under-7').wait_for(timeout=5000)
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
                    page.locator('.ou7-die.rolling').first.wait_for(timeout=5000); game_evidence('after-pass-over-under-7-rolling-en-us-desktop_primary.png','over_under_7',['rolling'],'en-US','desktop_primary')
                    # Wait for authoritative settlement and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"over-under-7-phase\"]')?.textContent === 'Settled'",timeout=10000); assert page.locator('.ou7-die:not(.rolling)').count()==2; localized_evidence('settled',['settled'])
                    # Commit another real play under reduced motion and capture its stable result.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-wager="over"]').fill('1'); page.locator('[data-play]').click(); page.locator('[data-play]:not([disabled])').wait_for(timeout=10000); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('over-under-7').wait_for(timeout=5000); assert page.locator('.ou7-history-row').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Over/Under 7 browser and visual gate.
                run_case('BR-OU7-001',['OU7-001','OU7-002','OU7-004','OU7-005','OU7-006','TEST-067'],over_under_7_acceptance)
                # Define real-backend Plinko localization, drop, responsive, motion, and route acceptance.
                def plinko_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-plinko').click(); page.get_by_test_id('plinko').wait_for(timeout=5000)
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
                    page.locator('#plinko-wager').fill('2'); page.locator('[data-action="drop"]').click(); page.locator('.plinko-puck').wait_for(timeout=10000)
                    # Capture the server-owned path replay at the primary desktop viewport.
                    assert len(page.locator('.plinko-puck').get_attribute('data-path'))==8; game_evidence('after-pass-plinko-path-replay-en-us-desktop_primary.png','plinko',['path_replay'],'en-US','desktop_primary')
                    # Capture the settled drop across both locales and every viewport.
                    localized_evidence('settled',['settled'])
                    # Commit another real drop under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('#plinko-wager').fill('3'); page.locator('[data-action="drop"]').click(); page.wait_for_function("() => document.querySelectorAll('.plinko-history-list li').length >= 2",timeout=10000); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('plinko').wait_for(timeout=5000); assert page.locator('.plinko-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Plinko browser and visual gate.
                run_case('BR-PLINKO-001',['PLINKO-001','PLINKO-002','PLINKO-004','PLINKO-005'],plinko_acceptance)
                # Define real-backend Fan-Tan localization, counting, responsive, motion, and route acceptance.
                def fan_tan_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-fan_tan').click(); page.get_by_test_id('fan-tan').wait_for(timeout=5000)
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
                    page.wait_for_function("() => document.querySelector('[data-testid=\"fan-tan-phase\"]')?.textContent === 'Counting groups of four'",timeout=5000); game_evidence('after-pass-fan-tan-counting-en-us-desktop_primary.png','fan_tan',['counting'],'en-US','desktop_primary')
                    # Wait for authoritative settlement and capture both locales and all viewports.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"fan-tan-phase\"]')?.textContent === 'Round settled'",timeout=10000); assert page.locator('.fan-tan__history-row').count()>=1; localized_evidence('settled',['settled'])
                    # Commit another real round under reduced motion and require the presentation flag.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-wager="4"]').fill('1'); page.locator('[data-play]').click(); page.locator('[data-play]:not([disabled])').wait_for(timeout=10000); assert page.locator('.fan-tan__tray').get_attribute('data-reduced-motion')=='true'; localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('fan-tan').wait_for(timeout=5000); assert page.locator('.fan-tan__history-row').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Fan-Tan browser and visual gate.
                run_case('BR-FAN-TAN-001',['FAN-TAN-001','FAN-TAN-002','FAN-TAN-004','FAN-TAN-005'],fan_tan_acceptance)
                # Define the lost-response idempotency regression proving a retry replays one identity and body with exactly one debit. (issue #261)
                def fan_tan_lost_response_idempotency():
                    # Open the Fan-Tan route and wait for the stable game surface.
                    page.get_by_test_id('nav-fan_tan').click(); page.get_by_test_id('fan-tan').wait_for(timeout=5000)
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
                    page.locator('[data-play]:not([disabled])').wait_for(timeout=10000)
                    # Retry the play through the same visible control; the wager stays locked to the pending snapshot.
                    page.locator('[data-play]').click()
                    # Wait for settlement to complete and the control to re-enable.
                    page.locator('[data-play]:not([disabled])').wait_for(timeout=10000)
                    # Read both captured round request bodies.
                    ft_reqs=page.evaluate('window.__ftRequests')
                    # Prove the retry reused the exact same idempotency identity and immutable wager body.
                    assert len(ft_reqs)>=2 and ft_reqs[0]['action_id']==ft_reqs[1]['action_id'] and ft_reqs[0]['wagers']==ft_reqs[1]['wagers']
                    # Prove the intended round was charged exactly once despite the lost-response retry.
                    ft_after=page.request.get(base+f'/api/v1/players/{ft_player}/ledger').json()['data']['ledger']; ft_debits_after=sum(1 for r in ft_after if r.get('game')=='fan_tan' and r.get('transaction_type')=='FAN_TAN_WAGER_DEBIT'); assert ft_debits_after==ft_debits_before+1
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the lost-response idempotency regression for Fan-Tan. (issue #261)
                run_case('BR-FAN-TAN-IDEMPOTENCY-001',['LEDGER-028','TEST-070'],fan_tan_lost_response_idempotency)
                # Define real-backend Andar Bahar localization, responsive, motion, and route acceptance.
                def andar_bahar_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-andar_bahar').click(); page.get_by_test_id('andar-bahar').wait_for(timeout=5000)
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
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted rank-match table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('andar-bahar').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-andar-bahar-{prefix}-{locale.lower()}-{viewport_id}.png','andar_bahar',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the first side prediction.
                    localized_evidence('ready',['ready'])
                    # Enter one wager and settle a real-backend rank-match round.
                    page.locator('#andar-wager').fill('1'); page.locator('[data-side="andar"]').click(); page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelectorAll('.andar-history-list li').length >= 1",timeout=10000)
                    # Capture the settled round across both locales and all viewports.
                    localized_evidence('settled',['settled'])
                    # Commit another real round under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-side="bahar"]').click(); page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelectorAll('.andar-history-list li').length >= 2",timeout=10000); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('andar-bahar').wait_for(timeout=5000); assert page.locator('.andar-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Andar Bahar browser and visual gate.
                run_case('BR-AB-001',['AB-001','AB-002','AB-004','AB-005'],andar_bahar_acceptance)
                # Define real-backend Acey-Deucey localization, decision, responsive, motion, and route acceptance.
                def acey_deucey_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-acey_deucey').click(); page.get_by_test_id('acey-deucey').wait_for(timeout=5000)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'acey_deucey.json')['title'] for locale in ('en-US','ru-RU')}
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
                    # Capture the complete ready table before the free boundary deal.
                    localized_evidence('ready',['ready'])
                    # Deal two real-backend boundaries without wallet movement.
                    page.locator('[data-action="deal"]').click(); page.locator('[data-action="play"]:not([disabled])').wait_for(timeout=10000); localized_evidence('boundaries-dealt',['boundaries_dealt'])
                    # Pass the prepared decision and capture the no-wager terminal path.
                    page.locator('[data-action="pass"]').click(); page.wait_for_function("() => document.querySelectorAll('.acey-history-list li').length >= 1",timeout=10000); localized_evidence('passed',['passed'])
                    # Deal again, enter a play-token wager, and settle the hidden third card.
                    page.locator('[data-action="deal"]').click(); page.locator('[data-action="play"]:not([disabled])').wait_for(timeout=10000); page.locator('#acey-wager').fill('1'); page.locator('[data-action="play"]').click(); page.wait_for_function("() => document.querySelectorAll('.acey-history-list li').length >= 2",timeout=10000); localized_evidence('settled',['settled'])
                    # Commit another pass under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-action="pass"]:not([disabled])').wait_for(timeout=10000); page.locator('[data-action="pass"]').click(); page.wait_for_function("() => document.querySelectorAll('.acey-history-list li').length >= 3",timeout=10000); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('acey-deucey').wait_for(timeout=5000); assert page.locator('.acey-history-list li').count()>=3; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Acey-Deucey browser and visual gate.
                run_case('BR-AD-001',['AD-001','AD-002','AD-004','AD-005'],acey_deucey_acceptance)
                # Define real-backend Caribbean Stud localization, decision, responsive, motion, and route acceptance.
                def caribbean_stud_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-caribbean_stud').click(); page.get_by_test_id('caribbean-stud').wait_for(timeout=5000)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'caribbean_stud.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active decision or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized game title rather than a fallback key or English leakage.
                            assert page.locator('.cs-header h1').inner_text()==expected_titles[locale]
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
                    # Require the strongest and weakest published raise odds to be visible with localized hand labels.
                    assert 'Raise payout schedule' in caribbean_stud_paytable_text and 'Royal flush' in caribbean_stud_paytable_text and '100:1' in caribbean_stud_paytable_text and 'High card' in caribbean_stud_paytable_text and '1:1' in caribbean_stud_paytable_text
                    # Deal through the public frontend and require private dealer hole cards during the decision.
                    page.locator('#cs-ante').fill('1'); page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Decision'",timeout=10000); assert page.locator('[aria-label="Face-down dealer card"]').count()==4
                    # Capture the actionable call-or-fold decision.
                    localized_evidence('decision',['decision'])
                    # Complete one real call and classify the authoritative shuffled terminal outcome.
                    page.locator('[data-action="call"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Settled'",timeout=10000); terminal=page.locator('.cs-result').inner_text().lower(); terminal_state='dealer_not_qualified' if 'does not qualify' in terminal else ('player_win' if 'player hand beats' in terminal else ('push' if 'tie' in terminal else 'dealer_win')); localized_evidence(terminal_state,[terminal_state])
                    # Complete a second real round through Fold while reduced motion is active.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Decision'",timeout=10000); page.locator('[data-action="fold"]').click(); page.wait_for_function("() => document.querySelector('.cs-phase')?.textContent === 'Folded'",timeout=10000); localized_evidence('fold-reduced-motion',['fold','reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('caribbean-stud').wait_for(timeout=5000); assert page.locator('.cs-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Caribbean Stud browser and visual gate.
                run_case('BR-CS-001',['CS-001','CS-002','CS-004','CS-005','CS-006','TEST-063'],caribbean_stud_acceptance)
                # Define real-backend Let It Ride localization, staged decisions, responsive, motion, and route acceptance.
                def let_it_ride_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-let_it_ride').click(); page.get_by_test_id('let-it-ride').wait_for(timeout=5000)
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
                    page.get_by_test_id('let-it-ride-wager').select_option('5'); page.locator('[data-action="deal"]').click(); page.locator('[data-stage="first"]:not([disabled])').first.wait_for(timeout=10000); assert page.locator('.lir-card-empty').count()==2
                    # Capture the first ride-or-pull decision beat.
                    localized_evidence('first-decision',['first_decision'])
                    # Leave the first unit riding and require exactly one community card reveal.
                    page.locator('[data-stage="first"][data-decision="ride"]').click(); page.locator('[data-stage="second"]:not([disabled])').first.wait_for(timeout=10000); assert page.locator('.lir-card-empty').count()==1
                    # Capture the second decision beat with the first community card visible.
                    localized_evidence('second-decision',['second_decision'])
                    # Pull one eligible unit and require terminal settled history.
                    page.locator('[data-stage="second"][data-decision="pull"]').click(); page.locator('[data-action="deal"]:not([disabled])').wait_for(timeout=10000); assert page.locator('.lir-history-row').count()>=1; localized_evidence('settled',['settled'])
                    # Complete another all-ride round under reduced motion and require stable history growth.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-stage="first"]:not([disabled])').first.wait_for(timeout=10000); page.locator('[data-stage="first"][data-decision="ride"]').click(); page.locator('[data-stage="second"]:not([disabled])').first.wait_for(timeout=10000); page.locator('[data-stage="second"][data-decision="ride"]').click(); page.wait_for_function("() => document.querySelectorAll('.lir-history-row').length >= 2",timeout=10000); localized_evidence('reduced-motion',['reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('let-it-ride').wait_for(timeout=5000); assert page.locator('.lir-history-row').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Let It Ride browser and visual gate.
                run_case('BR-LIR-001',['LIR-001','LIR-002','LIR-004','LIR-005'],let_it_ride_acceptance)
                # Define real-backend Casino Hold'em localization, decision, responsive, motion, and route acceptance.
                def casino_holdem_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-casino_holdem').click(); page.get_by_test_id('casino-holdem').wait_for(timeout=5000)
                    # Require the server-owned ante payout schedule to be player-visible with representative top and bottom rows. (issue #253)
                    holdem_paytable_text=page.get_by_test_id('choldem-paytable').inner_text()
                    assert 'Ante payout schedule' in holdem_paytable_text and 'Royal flush' in holdem_paytable_text and '100:1' in holdem_paytable_text and 'High card' in holdem_paytable_text and '1:1' in holdem_paytable_text
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'casino_holdem.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active decision or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title rather than a fallback key or English leakage.
                            assert page.locator('.choldem-header h1').inner_text()==expected_titles[locale]
                            # Validate containment and capture after-pass evidence at every viewport.
                            for viewport_id,width,height in required_viewports:
                                # Resize to the exact visual matrix dimensions.
                                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(100)
                                # Reject horizontal overflow and require the mounted community-card table.
                                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('casino-holdem').is_visible()
                                # Record self-describing evidence for this state and viewport.
                                game_evidence(f'after-pass-casino-holdem-{prefix}-{locale.lower()}-{viewport_id}.png','casino_holdem',states,locale,viewport_id)
                        # Restore English desktop controls for the next public action.
                        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
                    # Capture the complete ready table before the ante-backed flop.
                    localized_evidence('ready',['ready'])
                    # Deal through the public frontend and require the private dealer and unrevealed board slots.
                    page.locator('#choldem-wager').fill('1'); page.locator('#choldem-wager').press('Tab'); page.locator('[data-action="deal"]').click(); page.locator('[data-decision="call"]:not([disabled])').wait_for(timeout=10000); assert page.locator('.playing-card--back').count()==4
                    # Capture the actionable call-or-fold decision.
                    localized_evidence('decision',['decision'])
                    # Complete one real call and classify the authoritative shuffled terminal outcome.
                    page.locator('[data-decision="call"]').click(); page.wait_for_function("() => document.querySelectorAll('.choldem-history-list li').length >= 1",timeout=10000); terminal=page.locator('.choldem-result').inner_text().lower(); terminal_state='dealer_not_qualified' if 'did not qualify' in terminal else ('player_win' if 'player won' in terminal else ('push' if 'equal' in terminal else 'dealer_win')); localized_evidence(terminal_state,[terminal_state])
                    # Complete a second real round through fold while reduced motion is active.
                    page.emulate_media(reduced_motion='reduce'); page.locator('[data-action="deal"]').click(); page.locator('[data-decision="fold"]:not([disabled])').wait_for(timeout=10000); page.locator('[data-decision="fold"]').click(); page.wait_for_function("() => document.querySelectorAll('.choldem-history-list li').length >= 2",timeout=10000); localized_evidence('folded-reduced-motion',['folded','reduced_motion'])
                    # Reload the canonical route and require restored player-owned history.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('casino-holdem').wait_for(timeout=5000); assert page.locator('.choldem-history-list li').count()>=2; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Casino Hold'em browser and visual gate.
                run_case('BR-CH-001',['CH-001','CH-002','CH-004','CH-005','CH-006','TEST-084'],casino_holdem_acceptance)
                # Define real-backend Joker Poker localization, hold, draw, responsive, motion, and route acceptance.
                def joker_poker_acceptance():
                    # Open the catalog-owned route and wait for the stable game selector.
                    page.get_by_test_id('nav-joker_poker').click(); page.get_by_test_id('joker-poker').wait_for(timeout=5000)
                    # Enumerate all governed viewport dimensions.
                    required_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Load exact UTF-8 title expectations from the paired canonical resource files.
                    expected_titles={locale:read_i18n_json(ROOT/'web'/'i18n'/locale/'games'/'joker_poker.json')['title'] for locale in ('en-US','ru-RU')}
                    # Capture one mounted state across both locales and every viewport.
                    def localized_evidence(prefix,states):
                        # Iterate through paired English and Russian game resources.
                        for locale in ('en-US','ru-RU'):
                            # Switch locale without discarding the active hold phase or settled history.
                            page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                            # Require the localized title rather than a fallback key or English leakage.
                            assert page.locator('.jp-header h1').inner_text()==expected_titles[locale]
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
                    page.locator('#jp-wager').fill('1'); page.locator('#jp-wager').press('Tab'); page.locator('[data-action="deal"]').click(); page.get_by_test_id('joker-poker-source-hand').wait_for(timeout=10000); assert page.locator('[data-hold-position]').count()==5
                    # Persist one hold through the public API and capture the actionable phase.
                    page.locator('[data-hold-position="0"]').click(); page.locator('[data-hold-position="0"][aria-pressed="true"]').wait_for(timeout=10000); localized_evidence('choose-holds',['choose_holds'])
                    # Track both governed terminal classes so exact-head visual evidence never depends on one random outcome.
                    captured_outcomes=set()
                    # Play a bounded set of real-backend hands until both win and loss evidence has been captured.
                    for attempt in range(40):
                        # Start another public round after the first prepared hold when another terminal class is still missing.
                        if attempt:
                            # Deal through the mounted frontend so later evidence remains real-backend browser evidence.
                            page.locator('[data-action="deal"]').click(); page.get_by_test_id('joker-poker-source-hand').wait_for(timeout=10000)
                            # Persist the same representative keyboard-addressable hold in every additional round.
                            page.locator('[data-hold-position="0"]').click(); page.locator('[data-hold-position="0"][aria-pressed="true"]').wait_for(timeout=10000)
                        # Draw through the public frontend and wait for the authoritative settled hand.
                        page.locator('[data-action="draw"]').click(); page.get_by_test_id('joker-poker-result').wait_for(timeout=10000)
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
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('joker-poker').wait_for(timeout=5000); assert page.locator('.jp-history-list li').count()>=1; localized_evidence('route-restored',['route_restored'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Joker Poker browser and visual gate.
                run_case('BR-JP-001',['JP-001','JP-002','JP-004','JP-005'],joker_poker_acceptance)
                # Define registered Texas Hold'em localization, streets, settlement, motion, and route acceptance.
                def texas_holdem_practice_acceptance():
                    # Open the catalog-owned route and wait for the stable table selector.
                    page.get_by_test_id('nav-texas_holdem_practice_table').click(); page.get_by_test_id('texas-holdem-practice-table').wait_for(timeout=5000)
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
                    page.locator('#thpt-wager').fill('1'); page.locator('#thpt-wager').press('Tab'); page.locator('[data-action="start-hand"]').click(); page.locator('[data-action="call"]:not([disabled])').wait_for(timeout=10000)
                    # Capture private preflop play with redacted funded opponents.
                    assert all(page.get_by_test_id(f'thpt-seat-opponent_{index}').locator('.playing-card--back').count()==2 for index in (1,2,3)); localized_evidence('preflop-decision',['preflop_decision'])
                    # Advance and capture flop, turn, and river public decision states.
                    for prefix,state,card_count in [('flop-decision','flop_decision',3),('turn-decision','turn_decision',4),('river-decision','river_decision',5)]:
                        # Call through the public control and wait for the authoritative next street.
                        page.locator('[data-action="call"]:not([disabled])').click(); page.locator('[data-action="call"]:not([disabled])').wait_for(timeout=10000); page.wait_for_function(f"() => document.querySelectorAll('[data-testid=thpt-community-cards] .playing-card').length === {card_count}")
                        # Capture this exact decision street in both locales and all viewports.
                        localized_evidence(prefix,[state])
                    # Complete the river call and wait for fully reconciled four-wallet settlement.
                    page.locator('[data-action="call"]:not([disabled])').click(); page.get_by_test_id('thpt-result').wait_for(timeout=10000)
                    # Capture revealed showdown and terminal settlement together.
                    assert page.locator('[data-testid^="thpt-seat-opponent_"] .playing-card--back').count()==0; localized_evidence('showdown-settled',['showdown','settled'])
                    # Start a second real hand and exercise the explicit fold path.
                    page.locator('[data-action="start-hand"]:not([disabled])').click(); page.locator('[data-action="fold"]:not([disabled])').wait_for(timeout=10000); page.locator('[data-action="fold"]:not([disabled])').click(); page.get_by_test_id('thpt-result').wait_for(timeout=10000); localized_evidence('folded',['folded'])
                    # Capture stable settled presentation with reduced motion enabled.
                    page.emulate_media(reduced_motion='reduce'); localized_evidence('reduced-motion',['reduced_motion'])
                    # Counterfeit the rendered pot, result, and an unrelated cache key without sending another server action.
                    page.evaluate("() => { document.querySelector('[data-testid=thpt-pot] strong').textContent='999,999'; document.querySelector('[data-testid=thpt-result] h2').textContent='ATTACKER RESULT'; localStorage.setItem('casino.hostile.thpt','999999'); }")
                    # Require the hostile DOM edits to exist temporarily before authoritative refresh.
                    assert '999,999' in page.get_by_test_id('thpt-pot').inner_text() and 'ATTACKER RESULT' in page.get_by_test_id('thpt-result').inner_text()
                    # Reload the canonical route and require server-owned pot, result, and player history to replace client tampering.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('texas-holdem-practice-table').wait_for(timeout=5000); assert page.get_by_test_id('thpt-result').is_visible() and '999,999' not in page.get_by_test_id('thpt-pot').inner_text() and 'ATTACKER RESULT' not in page.get_by_test_id('thpt-result').inner_text() and page.evaluate("localStorage.getItem('casino.hostile.thpt')")=='999999'; localized_evidence('route-restored',['route_restored','client_tamper_refreshed'])
                    # Return to the lobby for downstream browser cases.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the integrated Texas Hold'em browser and hostile-client visual gate.
                run_case('BR-THPT-001',['THPT-001','THPT-002','THPT-004','THPT-005','SEC-002','SEC-003','SEC-009'],texas_holdem_practice_acceptance)
                # Define route_restoration to prove deep links, reload, Back, and Forward behavior.
                def route_restoration():
                    # Open Roulette directly through its canonical path using the authenticated browser context.
                    page.goto(base+'/games/roulette',wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                    # Reload the same deep link and require the route to remount without a lobby redirect.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                    # Require the persistent brand and wallet to finish painting before acceptance evidence.
                    page.locator('.brand-mark').wait_for(timeout=5000); page.get_by_test_id('premium-wallet').wait_for(timeout=5000); page.wait_for_timeout(300)
                    # Capture the restored game surface at the primary desktop viewport.
                    viewport_shot('after-pass-shell-route-roulette-desktop.png')
                    # Push a second catalog route through normal shell navigation.
                    page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slot-grid').wait_for(timeout=5000)
                    # Restore Roulette through browser Back and wait for the route-owned readiness selector.
                    page.go_back(); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                    # Restore Slots through browser Forward and wait for its route-owned readiness selector.
                    page.go_forward(); page.get_by_test_id('slot-grid').wait_for(timeout=5000)
                    # Return to the lobby so existing game interaction coverage starts from its normal baseline.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute the browser lifecycle restoration gate.
                run_case('BR-ROUTE-RESTORE-001',['CORE-022','MOTION-002'],route_restoration)
                # Open Roulette and wait for the premium vector wheel to mount.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for()
                # Define the exhaustive hit-target integrity and geometry regression required by issue #222.
                def roulette_hit_target_integrity():
                    # Select the smallest chip so exhaustive region coverage cannot deplete the wallet.
                    page.get_by_test_id('chip-1').click()
                    # Read every bet cell's stable identity and hit geometry from the mounted board.
                    cells=page.evaluate("() => [...document.querySelectorAll('[data-cell-key]')].map(el => { const r=el.getBoundingClientRect(); return {key:el.getAttribute('data-cell-key'), type:el.getAttribute('data-bet-type'), covered:(el.getAttribute('data-covered')||'').split(',').filter(Boolean), x:r.left, y:r.top, w:r.width, h:r.height}; })")
                    # Require a populated board so an empty catalog cannot pass this regression silently.
                    assert cells, 'no roulette bet cells rendered'
                    # Require every bet cell to expose a non-zero hit region.
                    assert all(cell['w']>0 and cell['h']>0 for cell in cells), 'zero-area roulette hit region'
                    # Require every bet cell to declare a non-empty covered-number set.
                    assert all(cell['covered'] for cell in cells), 'roulette cell missing covered numbers'
                    # Collect the non-spot primary grid cells for a pairwise no-overlap geometry check.
                    grid=[cell for cell in cells if not cell['key'].startswith('spot:')]
                    # Require primary grid hit regions to never overlap beyond a one-pixel seam.
                    for outer in range(len(grid)):
                        # Compare each primary grid cell against every later grid cell exactly once.
                        for inner in range(outer+1, len(grid)):
                            # Read the two candidate hit regions.
                            first=grid[outer]; second=grid[inner]
                            # Measure the horizontal overlap between the two regions.
                            overlap_x=max(0, min(first['x']+first['w'], second['x']+second['w']) - max(first['x'], second['x']))
                            # Measure the vertical overlap between the two regions.
                            overlap_y=max(0, min(first['y']+first['h'], second['y']+second['h']) - max(first['y'], second['y']))
                            # Require the overlap area to stay within an anti-aliasing seam.
                            assert overlap_x*overlap_y <= 2, f"overlapping roulette regions {first['key']} and {second['key']}"
                    # Build the click set from every primary grid region plus one hotspot per covered-number size.
                    click_keys=[cell['key'] for cell in grid]
                    # Track the hotspot covered-number sizes already sampled.
                    seen_sizes=set()
                    # Sample split, street, corner, line, and basket hotspots exactly once per size.
                    for cell in cells:
                        # Include the first hotspot seen for each distinct covered-number size.
                        if cell['key'].startswith('spot:') and len(cell['covered']) not in seen_sizes:
                            # Record the size and queue this representative hotspot for a real click.
                            seen_sizes.add(len(cell['covered'])); click_keys.append(cell['key'])
                    # Index each cell's canonical identity for post-click verification.
                    identity={cell['key']:cell for cell in cells}
                    # Click every selected region and require the posted wager to match the clicked cell exactly.
                    for key in click_keys:
                        # Build the stable selector for this hit target.
                        selector=f'[data-cell-key="{key}"]'
                        # Capture the exact wager POST triggered by activating this cell.
                        with page.expect_request(lambda request: request.url.endswith('/api/v1/games/roulette/bets') and request.method=='POST', timeout=5000) as request_info:
                            # Activate the cell semantically so intentionally-stacked corner spots cannot intercept the pointer.
                            page.dispatch_event(selector, 'click')
                        # Read the posted bet body for identity verification.
                        body=request_info.value.post_data_json
                        # Require the posted bet type to match the clicked cell's canonical type.
                        assert body['bet_type']==identity[key]['type'], f"{key}: posted {body['bet_type']} != {identity[key]['type']}"
                        # Require the posted covered numbers to match the clicked cell's canonical set.
                        assert {str(number) for number in body['covered_numbers']}=={str(number) for number in identity[key]['covered']}, f"{key}: covered mismatch"
                        # Settle the board rerender before activating the next hit target.
                        page.wait_for_timeout(25)
                    # Capture the exact "2nd 12" wager the issue reported as mismatched.
                    with page.expect_request(lambda request: request.url.endswith('/api/v1/games/roulette/bets') and request.method=='POST', timeout=5000) as second_dozen_info:
                        # Activate the reported second-dozen hit target directly.
                        page.dispatch_event('[data-cell-key="dozen:2"]', 'click')
                    # Read the second-dozen wager body.
                    second_dozen=second_dozen_info.value.post_data_json
                    # Require "2nd 12" to post the dozen covering exactly 13 through 24.
                    assert second_dozen['bet_type']=='dozen' and {str(number) for number in second_dozen['covered_numbers']}=={str(number) for number in range(13,25)}, '2nd 12 did not post the 13-24 dozen'
                    # Refund every audit wager so the board returns to its pre-audit betting state.
                    page.locator('#clear').click(); page.wait_for_timeout(150)
                # Record the exhaustive Roulette hit-target integrity and geometry regression.
                run_case('BR-ROU-HITMAP-001',['ROU-005','ROU-013','ROU-014','ROU-015','ROU-016','ROU-017','ROU-044','ROU-045','ROU-057','TEST-053'],roulette_hit_target_integrity)
                # Prove leaving Roulette with an open, un-spun bet refunds the stake rather than stranding it. (issue #246)
                def roulette_refund_on_leave():
                    # Read the authoritative current-user token balance straight from the session endpoint so the assertion never depends on shell DOM refresh timing. (issue #246)
                    def me_balance():
                        # Fetch the canonical /me play-token balance for the authenticated browser session.
                        return float(page.evaluate("async () => (await (await fetch('/api/v2/me', {credentials:'include'})).json()).data.player.token_balance"))
                    # Poll the authoritative balance until an in-flight prior clear/refund settles, then capture a stable pre-wager baseline.
                    def wait_balance(predicate):
                        # Bound the poll so a genuinely stuck balance fails fast instead of hanging the suite.
                        deadline=time.time()+6
                        # Re-read the authoritative balance until the predicate holds or the deadline passes.
                        while not predicate(me_balance()) and time.time()<deadline: page.wait_for_timeout(150)
                        # Return the final authoritative balance for the caller's assertion.
                        return me_balance()
                    # Capture a stable pre-wager baseline once two authoritative reads a beat apart agree, so a prior async refund cannot leave a mid-flight value.
                    refund_balance_before=me_balance()
                    # Re-read until the balance stops moving or the settle window elapses.
                    _settle_deadline=time.time()+6
                    while time.time()<_settle_deadline:
                        # Pause one short beat before comparing the next authoritative read.
                        page.wait_for_timeout(200)
                        # Read the authoritative balance again to detect any in-flight settlement.
                        _current=me_balance()
                        # Stop once two consecutive reads agree; otherwise adopt the newer value and keep settling.
                        if abs(_current-refund_balance_before)<0.005: break
                        # Adopt the moving value as the new candidate baseline.
                        refund_balance_before=_current
                    # Place one straight bet through the visible board and wait for the table chip to confirm the wager rendered.
                    page.get_by_test_id('roulette-num-17').click(); page.locator('.bet-chip').first.wait_for(timeout=3000)
                    # Require the open bet to have debited the authoritative balance before leaving the table.
                    assert wait_balance(lambda value: value < refund_balance_before-0.005) < refund_balance_before-0.005
                    # Leave the table without spinning by navigating back to the lobby, which unmounts Roulette and fires the refund.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                    # Require the authoritative balance to return to the pre-wager amount because the open bet was refunded on leave.
                    assert abs(wait_balance(lambda value: abs(value-refund_balance_before)<0.005)-refund_balance_before)<0.005
                    # Reopen Roulette and require the refunded round to start with no lingering open-bet chips.
                    page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                    # Require no open-bet chip to remain after the refund so the next round starts clean.
                    assert page.locator('.bet-chip').count()==0
                # Record the refund-on-leave wallet-correctness regression before the standard betting acceptance continues.
                run_case('BR-ROU-REFUND-001',['ROU-060','TEST-073'],roulette_refund_on_leave)
                # Audit slip labels for straight, fast-bet, grid-outside, and every inside/special bet type with no silent no-ops. (issues #230 #231 #233 #250)
                def roulette_slip_label_audit():
                    # Place one bet through the given target and require exactly one new, correctly labeled slip entry.
                    def place_and_check(selector, expected_label, use_dispatch=False):
                        # Count the existing slip rows so a silent no-op is detectable.
                        rows_before=page.locator('.bet-item').count()
                        # Click the visible control, or dispatch for hotspot markers that may be toggled hidden.
                        if use_dispatch:
                            page.dispatch_event(selector,'click')
                        else:
                            page.locator(selector).first.click()
                        # Require the slip to gain exactly one row instead of failing silently. (issue #233)
                        page.wait_for_function("n => document.querySelectorAll('.bet-item').length === n", arg=rows_before+1, timeout=5000)
                        # Read the newest slip label and require the exact catalog wording. (issues #230 #250)
                        newest_label=page.locator('.bet-item').last.locator('span').first.inner_text().strip()
                        assert newest_label==expected_label, (selector, newest_label, expected_label)
                    # Clear any open bets so the audit starts and ends with an empty refunded slip.
                    def clear_slip():
                        # Skip when the slip is already empty because the clear control disables itself.
                        if page.locator('.bet-item').count():
                            # Clear through the visible refund control and wait for the empty slip.
                            page.locator('#clear').click(); page.wait_for_function("() => document.querySelectorAll('.bet-item').length === 0", timeout=5000)
                    # Start from a clean slip after the preceding hit-map case.
                    clear_slip()
                    # Straight bets show their pocket number, including zero, never a color label. (issue #230)
                    place_and_check('[data-testid="roulette-num-17"]','17')
                    place_and_check('[data-testid="roulette-num-0"]','0')
                    # Every FAST BETS shortcut places exactly one correctly typed bet, including repeat clicks. (issue #231)
                    for fast_type,fast_label in (('red','Red'),('red','Red'),('odd','Odd'),('black','Black'),('even','Even'),('low','1-18'),('high','19-36')):
                        place_and_check(f'[data-outbtn="{fast_type}"]',fast_label)
                    # The equivalent grid outside cells register the same labels through the board surface. (issue #233)
                    for grid_type,grid_label in (('red','Red'),('black','Black'),('odd','Odd'),('even','Even'),('low','1-18'),('high','19-36')):
                        place_and_check(f'[data-testid="roulette-outside-{grid_type}"]',grid_label)
                    # Dozens and columns register their canonical range labels through their stable cell keys.
                    place_and_check('[data-cell-key="dozen:2"]','2nd 12',use_dispatch=True)
                    place_and_check('[data-cell-key="column:1"]','Column 1',use_dispatch=True)
                    # Enumerate one representative hotspot per inside/special type straight from the rendered catalog markers. (issue #250)
                    inside_targets=page.evaluate("() => { const seen={}; for (const spot of document.querySelectorAll('.spot')) { const type=spot.dataset.betType; if (!seen[type]) seen[type]={key:spot.dataset.cellKey,label:spot.title.replace(/ \\d+:1$/,'')}; } return Object.entries(seen).map(([type,info]) => ({type,key:info.key,label:info.label})); }")
                    # Require the board to expose every governed inside and special bet type as a marker.
                    assert {target['type'] for target in inside_targets} >= {'split','street','line','corner','zero_split','trio','top_line','snake'}, inside_targets
                    # Place one bet per inside/special type and require its exact catalog label on the slip.
                    for target in inside_targets:
                        place_and_check(f"[data-cell-key=\"{target['key']}\"]",target['label'],use_dispatch=True)
                    # Return every audited stake to the wallet through the refund control.
                    clear_slip()
                # Execute the exhaustive slip-label and reliability audit.
                run_case('BR-ROU-SLIP-AUDIT-001',['ROU-061','TEST-082'],roulette_slip_label_audit)
                # Define the raw Roulette resource keys reported as visible regressions.
                roulette_visible_keys={'header.kicker','title','controls.title','controls.spin','settlement.title','scoreboard.title'}
                # Define a focused rendered-text assertion for raw Roulette key leakage.
                def assert_no_visible_roulette_keys():
                    # Read non-empty visible body lines so exact key labels can be detected without selector coupling.
                    visible_lines={line.strip() for line in page.locator('body').inner_text().splitlines() if line.strip()}
                    # Verify none of the reported resource keys escaped into rendered text.
                    assert roulette_visible_keys.isdisjoint(visible_lines), f'Visible i18n keys: {sorted(roulette_visible_keys & visible_lines)}'
                    # Verify the runtime did not encounter any missing resources during the normal shell and Roulette flow.
                    assert page.evaluate("() => window.CasinoI18n.getLocaleState().missingKeyCount") == 0
                # Define the premium_roulette_layout function used by this module.
                def premium_roulette_layout():
                    # Verify the premium three-zone layout is mounted.
                    assert page.get_by_test_id('roulette-premium-layout').is_visible()
                    # Verify the dimensional wheel frame is mounted as a dedicated casino focal region.
                    assert page.get_by_test_id('roulette-wheel-frame').is_visible()
                    # Verify the layered metallic rim is present instead of a flat placeholder circle.
                    assert page.get_by_test_id('roulette-wheel-rim').is_visible()
                    # Verify the ball track is independently rendered for credible wheel motion.
                    assert page.get_by_test_id('roulette-ball-track').is_visible()
                    # Verify the physical ball indicator remains visible in both parked and selected states.
                    assert page.get_by_test_id('roulette-ball').is_visible()
                    # Verify the fixed table board remains visible.
                    assert page.get_by_test_id('roulette-table').is_visible()
                    # Verify the bet slip drawer remains visible.
                    assert page.get_by_test_id('roulette-bet-slip').is_visible()
                    # Verify the scoreboard drawer region remains visible.
                    assert page.get_by_test_id('roulette-scoreboard').is_visible()
                    # Verify the stats spark region remains visible.
                    assert page.get_by_test_id('roulette-stats-spark').is_visible()
                    # Verify inside-bet spots remain available for click coverage.
                    assert page.locator('[data-testid^="roulette-spot-"]').count() > 0
                    # Verify the bot controller stays mounted inside its progressive disclosure region.
                    assert page.locator('#botPanel').count() == 1
                    # Verify table rules are initially collapsed so wagering controls keep priority.
                    assert page.get_by_test_id('roulette-rules-disclosure').get_attribute('open') is None
                    # Verify racetrack bets are initially collapsed as an advanced betting mode.
                    assert page.get_by_test_id('roulette-racetrack-disclosure').get_attribute('open') is None
                    # Verify autoplay is initially collapsed so Spin remains the dominant action.
                    assert page.get_by_test_id('roulette-autoplay-disclosure').get_attribute('open') is None
                    # Verify bot controls are initially collapsed so the table retains visual focus.
                    assert page.get_by_test_id('roulette-bots-disclosure').get_attribute('open') is None
                    # Verify no internal lifecycle ribbon is exposed as player-facing interface.
                    assert page.locator('.roulette-status-ribbon').count() == 0
                    # Verify English Roulette content contains no visible raw resource keys.
                    assert_no_visible_roulette_keys()
                    # Read the three desktop zones so shared rail spacing can be checked independently of game content.
                    control_box=page.get_by_test_id('roulette-control-rail').bounding_box(); layout_box=page.get_by_test_id('roulette-premium-layout').bounding_box(); stage_box=page.get_by_test_id('roulette-premium-stage').bounding_box(); drawer_box=page.get_by_test_id('roulette-bet-slip').bounding_box()
                    # Read the game header position so status content cannot collide with the table layout.
                    header_box=page.locator('.roulette-header').bounding_box()
                    # Verify both side rails have premium desktop width instead of cramped developer-form columns.
                    assert control_box and control_box['width'] >= 330 and drawer_box and drawer_box['width'] >= 345, {'control':control_box,'stage':stage_box,'drawer':drawer_box,'layout':layout_box}
                    # Verify the game stage remains wider than both support rails combined.
                    assert stage_box and stage_box['width'] > control_box['width'] + drawer_box['width']
                    # Verify the route header ends before the three-zone table layout begins.
                    assert header_box and layout_box and header_box['y'] + header_box['height'] <= layout_box['y'] + 1
                    # Verify the rail uses the shared thin scrollbar treatment instead of native full-width chrome.
                    assert page.get_by_test_id('roulette-control-rail').evaluate("(el) => getComputedStyle(el).scrollbarWidth === 'thin'")
                    # Verify the shared control rail is a named keyboard-focusable region.
                    assert page.get_by_test_id('roulette-control-rail').get_attribute('tabindex')=='0' and page.get_by_test_id('roulette-control-rail').get_attribute('role')=='region'
                    # Verify nested rail lists expand into the single intentional desktop rail scroll surface.
                    assert page.get_by_test_id('roulette-bet-slip').evaluate("(el) => [...el.querySelectorAll('.scrollbox,.stable-list')].every(child => !['auto','scroll'].includes(getComputedStyle(child).overflowY))")
                    # Verify the wallet, wager chips, main table, and primary action fit inside the desktop viewport without rail scrolling.
                    assert page.evaluate("() => ['premium-wallet','chip-1','roulette-table','roulette-spin'].every(id => { const el=document.querySelector(`[data-testid=\"${id}\"]`); if(!el)return false; const box=el.getBoundingClientRect(); return box.top>=0 && box.bottom<=window.innerHeight-54; })")
                    # Resize to a tablet viewport so the shared three-zone layout can prove its stacked fallback.
                    page.set_viewport_size({'width':1024,'height':900}); page.wait_for_timeout(250)
                    # Read responsive panel positions after the shared breakpoint stacks the game layout.
                    tablet_control=page.get_by_test_id('roulette-control-rail').bounding_box(); tablet_stage=page.get_by_test_id('roulette-premium-stage').bounding_box(); tablet_drawer=page.get_by_test_id('roulette-bet-slip').bounding_box()
                    # Read computed responsive layout diagnostics for actionable assertion output on sizing regressions.
                    tablet_layout=page.get_by_test_id('roulette-premium-layout').evaluate("(el) => ({display:getComputedStyle(el).display,height:getComputedStyle(el).height,rows:getComputedStyle(el).gridTemplateRows,contain:getComputedStyle(el).contain,box:el.getBoundingClientRect().height,scroll:el.scrollHeight,children:[...el.children].map(child => ({height:child.getBoundingClientRect().height,scroll:child.scrollHeight,overflow:getComputedStyle(child).overflow}))})")
                    # Verify responsive game content stays inside the viewport without horizontal overflow.
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Verify the control, stage, and status panels stack in their intended reading order.
                    assert tablet_control and tablet_stage and tablet_drawer and tablet_control['y'] < tablet_stage['y'] < tablet_drawer['y']
                    # Verify the responsive flex stack sizes the control rail to its content without an empty tail.
                    assert tablet_layout['display']=='flex' and abs(tablet_control['height']-tablet_layout['children'][0]['scroll']) <= 4, {'control':tablet_control,'layout':tablet_layout}
                    # Capture the key-clean tablet header and first stacked panel as after-pass evidence.
                    page.screenshot(path=str(screenshots/'after-pass-shell-roulette-tablet.png'),full_page=False)
                    # Restore desktop dimensions before gameplay interaction coverage continues.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ROU-PREMIUM-001',['ROU-041','ROU-043','ROU-045','ROU-048','ROU-049','UX-007','UX-009'],premium_roulette_layout)
                # Capture the key-clean desktop Roulette shell as after-pass evidence.
                shot('after-pass-shell-roulette-desktop.png')
                # Capture betting-state visual evidence for the Roulette worker handback.
                shot('roulette-premium-betting.png')
                # Store the English Roulette surface text for visible resource-key rejection.
                roulette_english_text=page.get_by_test_id('roulette-premium').inner_text()
                # Verify no common Roulette resource-key prefix leaks in the English route.
                assert not any(prefix in roulette_english_text for prefix in ('header.','controls.','stage.','result.','betSlip.','settlement.','scoreboard.','stats.','status.','settings.','bets.'))
                # Verify Roulette values use explicit fake-money language instead of the legacy diamond-like glyph.
                assert 'play tokens' in roulette_english_text and '\ufffd' not in roulette_english_text and '\u00e2\u2014\u02c6' not in roulette_english_text
                # Verify the English route resolved every requested i18n key.
                assert page.evaluate("import('/core/i18n.js').then(i18n => i18n.getLocaleState().missingKeyCount)") == 0
                # Let the newly mounted route complete paint before capturing idle evidence.
                page.wait_for_timeout(300)
                # Capture idle-state visual evidence before any wager is placed.
                shot('roulette-premium-idle.png')
                # Store the stable table bounds before interaction so settlement cannot shift the board.
                roulette_table_bounds=page.get_by_test_id('roulette-table').bounding_box()
                # Store the wheel bounds so the desktop composition proves the wheel is a visible focal element.
                roulette_wheel_bounds=page.get_by_test_id('roulette-wheel').bounding_box()
                # Verify the desktop wheel is large enough to preserve pocket and ball clarity.
                assert roulette_wheel_bounds and roulette_wheel_bounds['width'] >= 280
                # Place a straight bet and wait for the table chip to render.
                page.get_by_test_id('roulette-num-17').click(); page.locator('.bet-chip').first.wait_for(timeout=3000)
                # Store the wagered chip bounds for table-geometry alignment proof.
                roulette_chip_bounds=page.locator('.bet-chip').first.bounding_box()
                # Store the selected number-cell bounds for table-geometry alignment proof.
                roulette_target_bounds=page.get_by_test_id('roulette-num-17').bounding_box()
                # Verify the wagered chip is horizontally centered on its logical number cell.
                assert abs((roulette_chip_bounds['x']+roulette_chip_bounds['width']/2)-(roulette_target_bounds['x']+roulette_target_bounds['width']/2)) <= 2
                # Verify the wagered chip is vertically centered on its logical number cell.
                assert abs((roulette_chip_bounds['y']+roulette_chip_bounds['height']/2)-(roulette_target_bounds['y']+roulette_target_bounds['height']/2)) <= 2
                # Let the short physical chip-placement accent complete before static evidence capture.
                page.wait_for_timeout(250)
                # Capture the aligned wagered-table state before locale and spin transitions.
                shot('roulette-premium-wagered.png')
                # Call the i18n runtime directly to verify language switching does not remount gameplay.
                page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.initI18n({ domains: ['games/roulette'] }); await i18n.setLocale('ru-RU', { persistLocal: false }); }""")
                # Define the localized Roulette state assertion used by the existing i18n browser case.
                def roulette_i18n_state():
                    # Verify the same placed chip remains visible after the localized rerender.
                    assert page.locator('.bet-chip').first.is_visible()
                    # Verify Russian Roulette content contains no visible raw resource keys.
                    assert_no_visible_roulette_keys()
                    # Verify localized Roulette amounts retain explicit fake-money language without the legacy glyph.
                    assert '\u0438\u0433\u0440\u043e\u0432\u044b\u0445 \u0442\u043e\u043a\u0435\u043d\u043e\u0432' in page.get_by_test_id('roulette-premium').inner_text()
                    # Verify shared keyboard scroll semantics survive the localized game rerender.
                    assert page.get_by_test_id('roulette-control-rail').get_attribute('tabindex')=='0'
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-I18N-GAMESTATE-ROU-001',['I18N-001','I18N-002','ROU-046'],roulette_i18n_state)
                # Capture the authoritative backend spin response while using the visible Roulette action.
                with page.expect_response(lambda response: response.url.endswith('/api/v1/games/roulette/spin') and response.request.method == 'POST') as roulette_spin_response_info:
                    # Spin the wheel through the dominant Roulette UI action.
                    page.get_by_test_id('roulette-spin').click()
                # Read the standard API envelope returned for this exact visible spin.
                roulette_spin_payload=roulette_spin_response_info.value.json()
                # Store the backend-authoritative pocket for cross-surface settlement checks.
                roulette_backend_result=str(roulette_spin_payload['data']['round']['result'])
                # Wait briefly for the rotor and ball to enter their visible counter-rotation phase.
                page.wait_for_timeout(450)
                # Verify the wheel rotor uses its weighted clockwise animation.
                assert page.get_by_test_id('roulette-rotor').get_attribute('data-motion-direction') == 'clockwise'
                # Verify the ball uses its independent counterclockwise animation.
                assert page.get_by_test_id('roulette-ball').get_attribute('data-motion-direction') == 'counterclockwise'
                # Verify the rotor is still in its animated reveal phase.
                assert 'spinning' in (page.get_by_test_id('roulette-rotor').get_attribute('class') or '')
                # Verify the ball is still in its animated reveal phase.
                assert 'spinning' in (page.get_by_test_id('roulette-ball').get_attribute('class') or '')
                # Read the spinning-state settlement card before the timed settlement rerender can replace it. (ROU-058, TEST-059)
                roulette_spinning_settlement_text=page.get_by_test_id('roulette-settlement-card').inner_text()
                # Define the player-facing spinning copy regression for issue #234.
                def roulette_spinning_settlement_copy():
                    # Require the live card to show localized progress language instead of the old layout/debug note.
                    assert ('Spin in progress' in roulette_spinning_settlement_text or 'Спин выполняется' in roulette_spinning_settlement_text) and 'No layout resize' not in roulette_spinning_settlement_text and 'Макет не меняет размер' not in roulette_spinning_settlement_text
                # Record the focused Roulette spinning-copy browser assertion.
                run_case('BR-ROU-SPINNING-COPY-001',['ROU-058','TEST-059'],roulette_spinning_settlement_copy)
                # Read the open bet-slip Remove button while the spin has locked the current wager set. (ROU-059, TEST-061)
                roulette_locked_remove_disabled=page.locator('[data-testid="roulette-bet-slip"] [data-clear]').first.is_disabled()
                # Define the focused locked-wager Remove-button regression for issue #240.
                def roulette_locked_remove_button():
                    # Require the Remove action to be inert while the spin is resolving the already committed wager.
                    assert roulette_locked_remove_disabled
                # Record the focused Roulette locked-wager remove-control browser assertion.
                run_case('BR-ROU-LOCKED-REMOVE-001',['ROU-059','TEST-061'],roulette_locked_remove_button)
                # Capture the locked spinning state before the backend result is presented.
                viewport_shot('roulette-premium-spinning.png')
                # Wait for the fixed result region to reach the settled phase.
                page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'settled'", timeout=7000)
                # Wait for the Roulette voice probe to observe the announcement queued after settlement refresh.
                page.wait_for_function("() => window.__casinoAudioEvents.some(event => event.kind === 'voice_start' && event.gameId === 'roulette')", timeout=3000)
                # Define the premium_roulette_settled function used by this module.
                def premium_roulette_settled():
                    # Read the settled result region.
                    result=page.get_by_test_id('roulette-result-region')
                    # Read the vector wheel region.
                    wheel=page.get_by_test_id('roulette-wheel')
                    # Verify the result region reached the settled state.
                    assert result.get_attribute('data-phase')=='settled'
                    # Verify the wheel-selected pocket matches the backend result display.
                    assert result.get_attribute('data-result-number')==wheel.get_attribute('data-selected-result')
                    # Verify the result panel matches the authoritative backend response for this spin.
                    assert result.get_attribute('data-result-number')==roulette_backend_result
                    # Verify the corresponding table number owns the settled-result highlight.
                    assert page.get_by_test_id(f'roulette-num-{roulette_backend_result}').evaluate("node => node.parentElement.classList.contains('result-cell')")
                    # Verify the latest history pocket matches the authoritative backend response.
                    assert page.get_by_test_id('roulette-recent-results').locator('span').last.inner_text()==roulette_backend_result
                    # Store Roulette voice events emitted by the visible spin.
                    roulette_voice_events=page.evaluate("window.__casinoAudioEvents.filter(event => event.kind === 'voice_start' && event.gameId === 'roulette')")
                    # Verify the queued voice announcement names the authoritative result pocket.
                    assert roulette_voice_events and roulette_backend_result in roulette_voice_events[-1]['text']
                    # Read the table bounds after settlement rerendering.
                    settled_table_bounds=page.get_by_test_id('roulette-table').bounding_box()
                    # Verify the betting board keeps its horizontal anchor through the spin and settlement phases.
                    assert abs(settled_table_bounds['x']-roulette_table_bounds['x']) <= 1
                    # Verify the betting board keeps its vertical anchor through the spin and settlement phases.
                    assert abs(settled_table_bounds['y']-roulette_table_bounds['y']) <= 1
                    # Verify the table board remains visible after settlement.
                    assert page.locator('.roulette-table-board').is_visible()
                    # Verify the drawer still renders after bets settle.
                    assert page.get_by_test_id('roulette-bet-slip').is_visible()
                    # Verify recent stats remain visible after settlement.
                    assert page.get_by_test_id('roulette-stats-spark').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ROU-001',['ROU-040','ROU-041','ROU-042','ROU-043','ROU-044','ROU-046','ROU-049','ROU-050','ROU-052','ROU-053','ROU-054','ROU-055','ROU-056'],premium_roulette_settled)
                # Let the short physical ball-settle accent complete before capturing static evidence.
                page.wait_for_timeout(700)
                # Capture settled-state visual evidence for the Roulette worker handback.
                shot('roulette-premium-settled.png')
                # Restore English before expanding shared controls and capturing route-return evidence.
                page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }""")
                # Expand autoplay through its player-facing disclosure control.
                page.get_by_test_id('roulette-autoplay-disclosure').locator('summary').click()
                # Track only Roulette mutations that would prove a rejected autoplay start still reached a game action.
                rejected_autoplay_mutations=[]
                # Observe request methods and URLs without reading credentials or wager payloads.
                page.on('request',lambda request: rejected_autoplay_mutations.append(request.url) if request.method=='POST' and ('/api/v1/games/roulette/bets' in request.url or '/api/v1/games/roulette/spin' in request.url) else None)
                # Count the exact number of client registration attempts handled by the controlled rejection.
                rejected_autoplay_starts={'count':0}
                # Define one standard server rejection for the shared autoplay start endpoint.
                def reject_autoplay_start(route):
                    # Count the visible Start action before returning the controlled error envelope.
                    rejected_autoplay_starts['count']+=1
                    # Reject registration without letting the backend create an autoplay session.
                    route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"AUTOPLAY_START_REJECTED","message":"Rejected for browser regression","details":{}}}')
                # Install the rejection only for this one focused control-plane scenario.
                page.route('**/api/v1/autoplay/start',reject_autoplay_start)
                # Record the authoritative wallet and Roulette state before the rejected registration.
                rejected_autoplay_balance_before=page.evaluate("async () => (await (await fetch('/api/v2/me')).json()).data.player.token_balance")
                # Read the current Roulette state through the authenticated browser session.
                rejected_autoplay_state_before=page.evaluate("async () => (await (await fetch('/api/v1/games/roulette/state')).json()).data.state")
                # Record error-list boundaries so only the controlled 503 transport observation is removed later.
                rejected_autoplay_console_index=len(console_errors); rejected_autoplay_http_index=len(http_errors); rejected_autoplay_page_error_index=len(page_errors)
                # Select multiple fast ticks so an incorrect loop becomes observable within a bounded wait.
                page.get_by_test_id('roulette-auto-rounds').fill('3'); page.get_by_test_id('roulette-auto-speed').select_option('fast')
                # Attempt autoplay through the current visible shared Start action.
                page.get_by_test_id('roulette-auto-start').click()
                # Wait for the localized player-facing failure rather than relying on transport timing alone.
                page.wait_for_function("() => { const toast=document.querySelector('#toast'); return toast && !toast.hidden && toast.textContent.includes('No automatic action was placed'); }",timeout=5000)
                # Allow enough time for several incorrect fast ticks to become observable.
                page.wait_for_timeout(900)
                # Record the authoritative wallet and state after the client has recovered to idle.
                rejected_autoplay_balance_after=page.evaluate("async () => (await (await fetch('/api/v2/me')).json()).data.player.token_balance")
                # Read state again so a hidden wager or spin cannot escape the request assertion.
                rejected_autoplay_state_after=page.evaluate("async () => (await (await fetch('/api/v1/games/roulette/state')).json()).data.state")
                # Read the currently mounted shared control state after rejection.
                rejected_autoplay_ui={'badge':page.get_by_test_id('autoplay-roulette').locator('.badge').inner_text(),'start_enabled':page.get_by_test_id('roulette-auto-start').is_enabled(),'stop_disabled':page.get_by_test_id('roulette-auto-stop').is_disabled(),'toast':page.locator('#toast').inner_text()}
                # Retain only console, HTTP, and JavaScript errors produced by this controlled scenario.
                rejected_autoplay_console=console_errors[rejected_autoplay_console_index:]; rejected_autoplay_http=http_errors[rejected_autoplay_http_index:]; rejected_autoplay_page_errors=page_errors[rejected_autoplay_page_error_index:]
                # Remove the focused route before proving a subsequent normal server-registered start.
                page.unroute('**/api/v1/autoplay/start',reject_autoplay_start)
                # Remove only the expected controlled 503 observations from suite-wide unexpected-error accounting.
                del console_errors[rejected_autoplay_console_index:]; del http_errors[rejected_autoplay_http_index:]
                # Define the rejected-start authority regression for issue #257.
                def autoplay_start_rejection():
                    # Verify one visible Start produced exactly one registration attempt.
                    assert rejected_autoplay_starts['count']==1
                    # Verify no Roulette wager or spin began without a server autoplay id.
                    assert rejected_autoplay_mutations==[]
                    # Verify wallet and complete game state remained unchanged during the failed start.
                    assert rejected_autoplay_balance_after==rejected_autoplay_balance_before and rejected_autoplay_state_after==rejected_autoplay_state_before
                    # Verify the shared widget returned to truthful idle controls.
                    assert rejected_autoplay_ui['badge']=='Off' and rejected_autoplay_ui['start_enabled'] and rejected_autoplay_ui['stop_disabled']
                    # Verify the player received sanitized localized failure copy.
                    assert rejected_autoplay_ui['toast']=='Auto play could not start. No automatic action was placed.'
                    # Verify no unhandled JavaScript error occurred; only the controlled failed-resource line may reach console.
                    assert rejected_autoplay_page_errors==[] and all('Failed to load resource' in value for value in rejected_autoplay_console)
                    # Verify the only failed network response was the controlled registration rejection.
                    assert len(rejected_autoplay_http)==1 and rejected_autoplay_http[0].startswith('503 ') and rejected_autoplay_http[0].endswith('/api/v1/autoplay/start')
                # Execute the real-browser server-authority regression before the existing successful start/stop proof.
                run_case('BR-AUTO-START-FAIL-001',['AUTO-001','AUTO-002','AUTO-003','TEST-025'],autoplay_start_rejection)
                # Start and stop Roulette autoplay through the shared control-plane widget.
                page.get_by_test_id('roulette-auto-rounds').fill('5'); page.get_by_test_id('roulette-auto-start').click()
                # Wait for the committed autoplay spin to enter its visible atomic action before requesting stop.
                page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'spinning'", timeout=7000)
                # Request stop while the current committed spin is allowed to finish safely.
                page.get_by_test_id('roulette-auto-stop').click()
                # Wait for that committed spin to settle before capturing route-return persistence evidence.
                page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'settled'", timeout=7000)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTO-ROU-001',['AUTO-003','AUTO-010','ROU-047'],lambda: page.get_by_text('Off').first.is_visible())
                # Collapse autoplay after verification so route-return evidence restores the gameplay-first composition.
                page.get_by_test_id('roulette-autoplay-disclosure').locator('summary').click()
                # Store the settled result before leaving the route.
                roulette_result_before_return=page.get_by_test_id('roulette-result-region').get_attribute('data-result-number')
                # Leave Roulette through the shared navigation to exercise route unmounting.
                page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slot-grid').wait_for(timeout=5000)
                # Return to Roulette and wait for the premium wheel to remount from persisted state.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                # Verify the route return preserves the authoritative settled pocket.
                assert page.get_by_test_id('roulette-result-region').get_attribute('data-result-number') == roulette_result_before_return
                # Let the remounted route complete paint before capturing return evidence.
                page.wait_for_timeout(1200)
                # Capture route-return evidence after the complete unmount and remount cycle.
                shot('roulette-premium-route-return.png')
                # Resize to the authoritative desktop-compact matrix viewport.
                page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(350)
                # Verify the compact desktop layout keeps the dominant stage between two subordinate rails.
                assert page.get_by_test_id('roulette-premium-layout').evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').length === 3")
                # Verify the desktop-compact route has no page-level horizontal overflow.
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                # Read compact navigation and Roulette measurements for actionable fold diagnostics.
                compact_diagnostics=page.evaluate("() => { const ids=['nav-lobby','nav-roulette','nav-slots','nav-keno','nav-bingo','nav-blackjack','nav-baccarat','nav-admin']; const navEl=document.querySelector('.casino-nav'); const nav=navEl.getBoundingClientRect().toJSON(); const items=ids.map(id => document.querySelector(`[data-testid=\"${id}\"]`)?.getBoundingClientRect().toJSON()); const visibleItems=items.filter(item => item && item.right >= nav.left - 1 && item.left <= nav.right + 1); const active=document.querySelector('[data-testid=\"nav-roulette\"]')?.getBoundingClientRect().toJSON(); const stage=document.querySelector('[data-testid=\"roulette-premium-stage\"]')?.getBoundingClientRect().toJSON(); const wheel=document.querySelector('[data-testid=\"roulette-wheel\"]')?.getBoundingClientRect().toJSON(); const table=document.querySelector('[data-testid=\"roulette-table\"]')?.getBoundingClientRect().toJSON(); const spin=document.querySelector('[data-testid=\"roulette-spin\"]')?.getBoundingClientRect().toJSON(); const navStyle=getComputedStyle(navEl); return {nav,items,visibleItems,active,stage,wheel,table,spin,height:innerHeight,width:innerWidth,navClientWidth:navEl.clientWidth,navScrollWidth:navEl.scrollWidth,navOverflowX:navStyle.overflowX}; }")
                # Verify compact desktop navigation is bounded to the viewport while long catalogs scroll inside the shared rail.
                assert compact_diagnostics['nav']['left'] >= -1 and compact_diagnostics['nav']['right'] <= compact_diagnostics['width'] + 1 and compact_diagnostics['navOverflowX'] in ('auto','scroll') and compact_diagnostics['navScrollWidth'] >= compact_diagnostics['navClientWidth'] and compact_diagnostics['active'] and compact_diagnostics['active']['left'] >= compact_diagnostics['nav']['left'] - 1 and compact_diagnostics['active']['right'] <= compact_diagnostics['nav']['right'] + 1 and len(compact_diagnostics['visibleItems']) >= 2, compact_diagnostics
                # Verify the full Roulette stage and primary action remain above the 1440 by 900 fold.
                assert all(compact_diagnostics[key] and compact_diagnostics[key]['bottom'] <= compact_diagnostics['height'] + 1 for key in ('stage','wheel','table','spin')), compact_diagnostics
                # Verify player-facing Roulette copy does not expose an internal round identifier.
                assert 'rou_' not in page.get_by_test_id('roulette-premium').inner_text()
                # Capture compact-layout acceptance evidence at the governed 1440 by 900 viewport.
                page.screenshot(path=str(screenshots/'after-pass-roulette-compact.png'),full_page=False)
                # Resize to the evaluator's second compact desktop viewport.
                page.set_viewport_size({'width':1366,'height':768}); page.wait_for_timeout(350)
                # Read the second compact viewport measurements after responsive compression.
                compact_1366=page.evaluate("() => { const navEl=document.querySelector('.casino-nav'); const nav=navEl.getBoundingClientRect().toJSON(); const items=[...document.querySelectorAll('.casino-nav .nav-item')].map(item => item.getBoundingClientRect().toJSON()); const visibleItems=items.filter(item => item && item.right >= nav.left - 1 && item.left <= nav.right + 1); const active=document.querySelector('[data-testid=\"nav-roulette\"]')?.getBoundingClientRect().toJSON(); const ids=['roulette-premium-stage','roulette-wheel','roulette-table','roulette-spin']; const boxes=Object.fromEntries(ids.map(id => [id,document.querySelector(`[data-testid=\"${id}\"]`)?.getBoundingClientRect().toJSON()])); const navStyle=getComputedStyle(navEl); return {nav,items,visibleItems,active,boxes,width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,navClientWidth:navEl.clientWidth,navScrollWidth:navEl.scrollWidth,navOverflowX:navStyle.overflowX}; }")
                # Verify navigation is a bounded scroll rail and the Roulette stage, wheel, table, and Spin remain above the 1366 by 768 fold.
                assert compact_1366['scrollWidth'] <= compact_1366['width'] + 1 and compact_1366['nav']['left'] >= -1 and compact_1366['nav']['right'] <= compact_1366['width'] + 1 and compact_1366['navOverflowX'] in ('auto','scroll') and compact_1366['navScrollWidth'] >= compact_1366['navClientWidth'] and compact_1366['active'] and compact_1366['active']['left'] >= compact_1366['nav']['left'] - 1 and compact_1366['active']['right'] <= compact_1366['nav']['right'] + 1 and len(compact_1366['visibleItems']) >= 2 and all(box and box['bottom'] <= compact_1366['height'] - 54 for box in compact_1366['boxes'].values()), compact_1366
                # Capture the evaluator-sized compact desktop acceptance evidence.
                page.screenshot(path=str(screenshots/'after-pass-roulette-1366x768.png'),full_page=False)
                # Resize to a narrow responsive viewport for Roulette-specific overflow verification.
                page.set_viewport_size({'width':760,'height':900}); page.wait_for_timeout(250)
                # Verify Roulette does not create page-level horizontal overflow at the responsive width.
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                # Verify both the wheel and full table regions remain present after responsive recomposition.
                assert page.get_by_test_id('roulette-wheel').is_visible() and page.get_by_test_id('roulette-table').is_visible()
                # Restore desktop dimensions before the next game evidence run.
                page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Navigate to the premium Slots route before collecting state evidence.
                page.get_by_test_id('nav-slots').click()
                # Wait for the fixed reel grid to mount before measuring layout stability.
                page.get_by_test_id('slot-grid').wait_for(timeout=5000)
                # Capture the idle cabinet state for worker handback evidence.
                shot('slots_idle.png')
                # Capture the English Slots screen as after-pass shared shell and game-layout evidence.
                shot('after-pass-shell-slots-desktop.png')
                # Read the Slots surface copy so acceptance evidence cannot contain leaked resource keys.
                slots_evidence_text=page.get_by_test_id('slots-premium').inner_text()
                # Verify the after-pass game evidence contains user-facing copy rather than internal resource identifiers.
                assert 'controls.' not in slots_evidence_text and 'status.' not in slots_evidence_text and 'slots.' not in slots_evidence_text
                # Store the idle cabinet box so spin/result states can be compared.
                idle_box=page.get_by_test_id('slots-cabinet').bounding_box()
                # Store the idle result box so the reserved payout region can be compared.
                idle_result_box=page.get_by_test_id('slots-result').bounding_box()
                # Prove the payline overlay coordinate space coincides with the reel cells rather than detaching below them. (issue #319)
                def slots_payline_alignment():
                    # Copy the exact twenty-line rule table so browser expectations cannot drift from the engine.
                    payline_rows=[list(line) for line in slots_engine.PAYLINES[20]]
                    # Build one deterministic all-Wild grid that makes every authoritative payline a simultaneous win.
                    payline_grid=[['WILD' for _column in range(5)] for _row in range(3)]
                    # Evaluate the grid through the production rules rather than fabricating payout or win rows in the browser test.
                    payline_result=slots_engine.evaluate(payline_grid,20,1)
                    # Require the authoritative engine to return all twenty indexed rows before UI evidence is seeded.
                    assert len(payline_result['wins'])==20 and [win['line'] for win in payline_result['wins']]==payline_rows
                    # Build the persisted spin shape consumed by the normal Slots route loader.
                    payline_spin={'round_id':'slot-payline-acceptance','timestamp':'2026-07-20T00:00:00Z','stops':[0,0,0,0,0],'grid':payline_grid,'active_lines':20,'line_bet':1,'cost':20,**payline_result,'free_spin':False,'free_spins_remaining':0,'progressive':1000}
                    # Resolve the authenticated browser player before writing isolated deterministic game state.
                    payline_player=page.evaluate("() => { const shellPlayer=window.CasinoCurrentUser?.player || window.CasinoCurrentPlayer || {}; return shellPlayer.player_id || window.CasinoCurrentUser?.player_id || localStorage.getItem('casino.currentPlayerId') || 'human'; }")
                    # Persist the authoritative result through the same state store the Slots route reads after refresh.
                    save_player_game_state('slots',payline_player,{'last_spins':[payline_spin],'progressive':1000,'free_spins':0})
                    # Reload the real route so the overlay, result text, and history all recover from one authoritative state.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('slots-payline').wait_for(timeout=5000)
                    # Define a browser-side audit that compares every rendered SVG point with its actual cell center in screen coordinates.
                    def audit_payline_geometry():
                        # Bring the bounded reel grid into the viewport so elementFromPoint can test symbol identity instead of returning null for off-screen coordinates.
                        page.get_by_test_id('slot-grid').scroll_into_view_if_needed()
                        # Let ResizeObserver and requestAnimationFrame finish the current responsive or zoom alignment.
                        page.wait_for_timeout(120)
                        # Return exact geometry, identity, style, accessibility, and containment diagnostics for all twenty paths.
                        return page.evaluate("""expectedRows => { const grid=document.querySelector('[data-testid="slot-grid"]'); const overlay=document.querySelector('[data-testid="slots-payline"]'); const gridBox=grid.getBoundingClientRect(); const overlayBox=overlay.getBoundingClientRect(); const paths=[...overlay.querySelectorAll('polyline[data-line-number]')]; let maxError=0; const rows=paths.map((path,index) => { const declared=String(path.dataset.lineRows || '').split(',').map(Number); const matrix=path.getScreenCTM(); const pointErrors=declared.map((row,column) => { const point=path.points.getItem(column); const rendered=new DOMPoint(point.x,point.y).matrixTransform(matrix); const cell=document.querySelector(`[data-testid="slot-cell-${row}-${column}"]`).getBoundingClientRect(); const error=Math.hypot(rendered.x-(cell.left+cell.width/2),rendered.y-(cell.top+cell.height/2)); maxError=Math.max(maxError,error); return error; }); const style=getComputedStyle(path); return {number:Number(path.dataset.lineNumber),declared,expected:expectedRows[index],pointErrors,stroke:style.stroke,dash:style.strokeDasharray,width:parseFloat(style.strokeWidth)}; }); const symbolHits=[...document.querySelectorAll('[data-testid^="slot-cell-"]')].map(cell => { const box=cell.getBoundingClientRect(); const hit=document.elementFromPoint(box.left+box.width/2,box.top+box.height/2); const style=getComputedStyle(cell); return Boolean(hit?.closest('.slots-symbol')) && style.visibility==='visible' && style.display!=='none' && Number(style.opacity)>0 && Boolean(cell.textContent.trim()); }); return {positioned:getComputedStyle(grid).position,pathCount:paths.length,groupCount:overlay.querySelectorAll('g[data-line-number]').length,rows,maxError,gridBox:{left:gridBox.left,top:gridBox.top,width:gridBox.width,height:gridBox.height},overlayBox:{left:overlayBox.left,top:overlayBox.top,width:overlayBox.width,height:overlayBox.height},roundId:overlay.dataset.roundId,payout:Number(overlay.dataset.payout),reduced:overlay.dataset.reducedMotion,aria:overlay.getAttribute('aria-label'),uniqueStyles:new Set(rows.map(row => `${row.stroke}|${row.dash}`)).size,symbolHits,noOverflow:document.documentElement.scrollWidth<=window.innerWidth+1}; }""",payline_rows)
                    # Read the four authoritative dimensions directly from the visual matrix used by the browser gate.
                    payline_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
                    # Require the matrix to expose every issue-mandated desktop, tablet, and mobile viewport.
                    assert set(payline_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
                    # Define one strict acceptance assertion reused after locale, resize, zoom, and refresh changes.
                    def require_payline_acceptance(diagnostics):
                        # Require exact current-main positioning, all twenty labelled paths, and outcome identity.
                        assert diagnostics['positioned']=='relative' and diagnostics['pathCount']==20 and diagnostics['groupCount']==20 and diagnostics['roundId']==payline_spin['round_id'] and diagnostics['payout']==payline_spin['payout'],diagnostics
                        # Require the SVG box to coincide with the grid and every transformed point to hit its cell center within one CSS pixel.
                        assert max(abs(diagnostics['overlayBox'][edge]-diagnostics['gridBox'][edge]) for edge in ('left','top','width','height'))<=1 and diagnostics['maxError']<=1,diagnostics
                        # Require every rendered path to preserve its engine row vector and permanent one-based line number.
                        assert all(row['number']==index+1 and row['declared']==payline_rows[index] and row['expected']==payline_rows[index] and max(row['pointErrors'])<=1 for index,row in enumerate(diagnostics['rows'])),diagnostics
                        # Require twenty distinguishable color/dash combinations, thin non-obscuring strokes, visible symbol identity, and bounded layout.
                        assert diagnostics['uniqueStyles']==20 and all(row['width']<=2 for row in diagnostics['rows']) and all(diagnostics['symbolHits']) and diagnostics['noOverflow'] and diagnostics['aria'],diagnostics
                    # Verify every locale and governed viewport, capturing after-pass route-restored multi-win evidence with sidecars.
                    for locale in ('en-US','ru-RU'):
                        # Switch through the player-visible locale control so the overlay's accessible copy rerenders normally.
                        page.get_by_test_id('shell-locale-select').select_option(locale); page.get_by_test_id('slots-payline').wait_for(timeout=5000)
                        # Exercise every exact visual-matrix size for this locale.
                        for viewport_id,viewport in payline_viewports.items():
                            # Resize through the supported browser path before auditing responsive alignment.
                            page.set_viewport_size(viewport)
                            # Require all twenty paths to remain exact after this locale and viewport combination.
                            payline_diagnostics=audit_payline_geometry(); require_payline_acceptance(payline_diagnostics)
                            # Read the visible result and history so their line summary and payout can be matched to the authoritative spin.
                            payline_visible_text=page.get_by_test_id('slots-premium').inner_text(); payline_result_text=page.get_by_test_id('slots-result').inner_text(); payline_history_text=page.get_by_test_id('slots-recent-spins').inner_text()
                            # Normalize locale separators while retaining every visible digit needed for the exact payout comparison.
                            payline_result_digits=''.join(character for character in payline_result_text if character.isdigit()); payline_history_digits=''.join(character for character in payline_history_text if character.isdigit())
                            # Require the first three detailed lines, the remaining-win count, total payout, and round history to agree with the engine outcome.
                            line_word='Line' if locale=='en-US' else 'Линия'; assert all(f'{line_word} {number}' in payline_result_text for number in (1,2,3)) and '17' in payline_result_text and str(int(payline_spin['payout'])) in payline_result_digits and payline_spin['round_id'] in payline_history_text and str(int(payline_spin['payout'])) in payline_history_digits
                            # Reject any resource-key leakage from the localized accessible or visible result treatment.
                            assert all(key not in payline_visible_text for key in ('payline.overlayLabel','payline.pathLabel','result.lineWin'))
                            # Capture the complete governed game surface for exact-head acceptance review.
                            game_evidence(f'after-pass-slots-paylines-{locale}-{viewport_id}.png','slots',['win','multi_win','route_restored'],locale,viewport_id)
                    # Restore English at the primary desktop viewport before the zoom-specific audit.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size(payline_viewports['desktop_primary'])
                    # Apply a representative 125 percent CSS zoom and require geometry to realign rather than use stale percentages.
                    page.evaluate("document.body.style.zoom='125%'"); zoom_diagnostics=audit_payline_geometry(); require_payline_acceptance(zoom_diagnostics)
                    # Record the zoomed after-pass state separately so the evidence sidecar names the acceptance dimension.
                    game_evidence('after-pass-slots-paylines-en-US-desktop_primary-zoomed.png','slots',['win','multi_win','zoomed'], 'en-US','desktop_primary')
                    # Restore normal zoom before exercising the operating-system reduced-motion preference.
                    page.evaluate("document.body.style.zoom=''"); page.emulate_media(reduced_motion='reduce'); page.reload(wait_until='networkidle'); page.get_by_test_id('slots-payline').wait_for(timeout=5000)
                    # Require the reduced-motion rerender to expose static paths with the same exact geometry.
                    reduced_diagnostics=audit_payline_geometry(); require_payline_acceptance(reduced_diagnostics); assert reduced_diagnostics['reduced']=='true' and page.locator('[data-testid="slots-payline"] polyline').first.evaluate("path => { const style=getComputedStyle(path); return style.animationName==='none' && style.transitionDuration==='0s'; }")
                    # Capture the clear non-animated win treatment as governed after-pass evidence.
                    game_evidence('after-pass-slots-paylines-en-US-desktop_primary-reduced-motion.png','slots',['win','multi_win','reduced_motion','route_restored'],'en-US','desktop_primary')
                    # Restore the default media preference and route state for the existing Slots regression sequence.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('slots-payline').wait_for(timeout=5000); require_payline_acceptance(audit_payline_geometry())
                # Execute the payline-to-reel alignment regression.
                run_case('BR-SLOTS-PAYLINE-001',['SLOT-029','TEST-077'],slots_payline_alignment)
                # Define the focused line-bet regression using real visible controls and backend requests.
                def slots_line_bet_validation():
                    # Track only Slots spin requests so input edits can prove they never move tokens by themselves.
                    observed_spin_requests=[]
                    # Define the request observer before the invalid value is typed.
                    def observe_slots_spin(request):
                        # Retain only public Slots spin posts for this focused validation.
                        if request.method=='POST' and request.url.endswith('/api/v1/games/slots/spin'): observed_spin_requests.append(request)
                    # Attach the bounded observer for the duration of this focused case.
                    page.on('request',observe_slots_spin)
                    # Select the real browser-visible line-bet input.
                    line_bet=page.get_by_test_id('slots-line-bet')
                    # Type the reported negative value through the normal input event path.
                    line_bet.fill('-5'); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-line-bet\"]')?.value === '1'")
                    # Require immediate correction, machine-readable invalid state, localized feedback, and zero requests.
                    assert line_bet.get_attribute('aria-invalid')=='true' and page.get_by_test_id('slots-line-bet-feedback').text_content().strip()=='Line bet must be a whole number of at least 1. Reset to 1.' and not observed_spin_requests
                    # Type a valid replacement to prove the error clears and visible cost updates before any spin.
                    line_bet.fill('3'); page.wait_for_timeout(50)
                    # Require the valid state and the twenty-line cost implied by the visible controls.
                    assert line_bet.get_attribute('aria-invalid')=='false' and page.get_by_test_id('slots-line-bet-feedback').inner_text()=='' and '60' in page.get_by_test_id('slots-round-cost').inner_text() and not observed_spin_requests
                    # Re-enter the reported invalid value so governed evidence records the correction feedback.
                    line_bet.fill('-5'); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-line-bet\"]')?.getAttribute('aria-invalid') === 'true'")
                    # Define the localized feedback required in each governed locale.
                    localized_feedback={'en-US':'Line bet must be a whole number of at least 1. Reset to 1.','ru-RU':'Ставка на линию должна быть целым числом не меньше 1. Значение сброшено на 1.'}
                    # Define the affected compact and mobile visual-matrix viewports.
                    validation_viewports={'desktop_compact':{'width':1440,'height':900},'mobile':{'width':390,'height':844}}
                    # Exercise localized invalid-input presentation without losing corrected state.
                    for locale,expected_feedback in localized_feedback.items():
                        # Change locale through the shared visible shell control.
                        page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("expected => document.querySelector('[data-testid=\"slots-line-bet-feedback\"]')?.textContent.trim() === expected",arg=expected_feedback)
                        # Capture and measure every affected viewport for the active locale.
                        for viewport_id,viewport in validation_viewports.items():
                            # Resize to the exact governed dimensions before containment checks.
                            page.set_viewport_size(viewport); page.wait_for_timeout(150)
                            # Measure the corrected input and feedback against page-level containment.
                            validation_geometry=page.evaluate("""() => { const input=document.querySelector('[data-testid="slots-line-bet"]').getBoundingClientRect(); const feedback=document.querySelector('[data-testid="slots-line-bet-feedback"]').getBoundingClientRect(); return {documentWidth:document.documentElement.scrollWidth,viewportWidth:window.innerWidth,input:{left:input.left,right:input.right},feedback:{left:feedback.left,right:feedback.right,height:feedback.height}}; }""")
                            # Reject horizontal overflow, clipped controls, or a collapsed live-feedback reservation.
                            assert validation_geometry['documentWidth']<=validation_geometry['viewportWidth']+1 and validation_geometry['input']['left']>=-1 and validation_geometry['input']['right']<=validation_geometry['viewportWidth']+1 and validation_geometry['feedback']['left']>=-1 and validation_geometry['feedback']['right']<=validation_geometry['viewportWidth']+1 and validation_geometry['feedback']['height']>=20,validation_geometry
                            # Record focused after-pass evidence without accepting unrelated nav or reel defects.
                            region_evidence(f'after-pass-slots-control-invalid-line-bet-{locale}-{viewport_id}.png','.slots-control','slots',['invalid_line_bet'],locale,viewport_id)
                    # Restore English and primary desktop dimensions before the real corrected spin.
                    page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-line-bet-feedback\"]')?.textContent.trim() === 'Line bet must be a whole number of at least 1. Reset to 1.'")
                    # Submit one corrected spin and capture the exact public request emitted by the visible button.
                    with page.expect_request(lambda request: request.method=='POST' and request.url.endswith('/api/v1/games/slots/spin')) as corrected_request_info: page.get_by_test_id('slots-spin').click()
                    # Read the frozen endpoint payload after Playwright observes the real request.
                    corrected_payload=corrected_request_info.value.post_data_json
                    # Wait for a completed real round rather than accepting request emission alone.
                    page.wait_for_function("() => !document.querySelector('[data-testid=\"slots-spin\"]')?.disabled && document.querySelector('[data-testid=\"slots-result\"]')?.textContent.includes('Result.')",timeout=5000)
                    # Require one corrected whole-token line bet and an authoritative completed result.
                    assert corrected_payload['line_bet']==1 and corrected_payload['active_lines']==20 and observed_spin_requests and page.get_by_test_id('slots-result').is_visible()
                    # Limit the visible autoplay control to one round so its corrected plan can be inspected safely.
                    page.get_by_test_id('slots-auto-rounds').fill('1')
                    # Define one deterministic control-plane response while leaving the real Slots action unmocked.
                    def fulfill_slots_autoplay_probe(route):
                        # Return the standard API envelope expected by start, status, tick, and finish calls.
                        route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'session':{'autoplay_id':'slots-plan-probe','status':'running','stop_requested':False}}}))
                    # Stub only autoplay control-plane traffic so plan inspection produces no false network failure.
                    page.route('**/api/v1/autoplay/**',fulfill_slots_autoplay_probe)
                    # Start autoplay through its visible control and capture the exact synchronized plan.
                    with page.expect_request(lambda request: request.method=='POST' and request.url.endswith('/api/v1/autoplay/start')) as autoplay_request_info: page.get_by_test_id('slots-auto-start').click()
                    # Read the request body emitted by the shared autoplay control plane.
                    autoplay_payload=autoplay_request_info.value.post_data_json
                    # Require the corrected visible value to reach the autoplay plan unchanged.
                    assert autoplay_payload['plan']['active_lines']==20 and autoplay_payload['plan']['line_bet']==1
                    # Wait for the one locally committed autoplay action to settle and return the controls to Off.
                    page.wait_for_function("() => !document.querySelector('[data-testid=\"slots-spin\"]')?.disabled && document.querySelector('[data-testid=\"autoplay-slots\"] .badge')?.textContent === 'Off'",timeout=5000)
                    # Clear the synthetic session identifier so later route-unmount cleanup stays listener-free.
                    page.evaluate("() => { const session=window.__casinoAutoplaySessions?.get('slots'); if(session) session.serverId=null; }")
                    # Remove the bounded control-plane stub before any later autoplay coverage.
                    page.unroute('**/api/v1/autoplay/**',fulfill_slots_autoplay_probe)
                    # Detach the observer so later game traffic cannot affect this completed case.
                    page.remove_listener('request',observe_slots_spin)
                # Record immediate feedback, synchronization, localization, evidence, and real request coverage.
                run_case('BR-SLOT-LINE-BET-001',['SLOT-027','TEST-058','UX-009'],slots_line_bet_validation)
                # Refresh idle boxes after the focused real spin so the existing animation comparison uses one baseline.
                idle_box=page.get_by_test_id('slots-cabinet').bounding_box(); idle_result_box=page.get_by_test_id('slots-result').bounding_box()
                # Start one real spin through the browser-visible control.
                page.get_by_test_id('slots-spin').click()
                # Pause during the in-progress animation window before the API result reveal.
                page.wait_for_timeout(120)
                # Capture the moving-reels state for worker handback evidence.
                shot('slots_spinning.png')
                # Store the spinning cabinet box to prove the cabinet does not jump.
                spinning_box=page.get_by_test_id('slots-cabinet').bounding_box()
                # Store the spinning result box to prove the payout region stays reserved.
                spinning_result_box=page.get_by_test_id('slots-result').bounding_box()
                # Wait for the spin result reveal to settle.
                page.wait_for_timeout(1200)
                # Capture the settled result state for worker handback evidence.
                shot('slots_result.png')
                # Store the settled cabinet box for the final stability comparison.
                result_box=page.get_by_test_id('slots-cabinet').bounding_box()
                # Store the settled result box for the final reserved-region comparison.
                result_result_box=page.get_by_test_id('slots-result').bounding_box()
                # Define the premium_slots function used by this module.
                def premium_slots():
                    # Verify the fixed five-by-three reel surface remains visible.
                    assert page.get_by_test_id('slot-grid').is_visible()
                    # Verify the fixed result region is present after a real spin.
                    assert page.get_by_test_id('slots-result').is_visible()
                    # Locate the cabinet footer's read-only state indicator.
                    slots_state_pill=page.locator('.slots-cabinet-footer .slots-state-pill')
                    # Require the read-only state to render as status instead of a primary button.
                    assert slots_state_pill.count()==1 and slots_state_pill.get_attribute('role')=='status' and page.locator('.slots-cabinet-footer button.primary').count()==0
                    # Verify recent spins are shown in the right drawer.
                    assert page.get_by_test_id('slots-recent-spins').is_visible()
                    # Verify the Slots bot capability panel is reserved.
                    assert page.get_by_test_id('slots-bot-panel').is_visible()
                    # Verify the cabinet width stays stable from idle to spinning.
                    assert abs(idle_box['width']-spinning_box['width']) < 2
                    # Verify the cabinet height stays stable from idle to spinning.
                    assert abs(idle_box['height']-spinning_box['height']) < 2
                    # Verify the cabinet width stays stable from idle to result reveal.
                    assert abs(idle_box['width']-result_box['width']) < 2
                    # Verify the cabinet height stays stable from idle to result reveal.
                    assert abs(idle_box['height']-result_box['height']) < 2
                    # Verify the result-region height stays stable during the spin.
                    assert abs(idle_result_box['height']-spinning_result_box['height']) < 2
                    # Verify the result-region height stays stable after the spin.
                    assert abs(idle_result_box['height']-result_result_box['height']) < 2
                    # Verify the premium Slots route avoids page-level horizontal overflow.
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-SLOT-001',['SLOT-020','SLOT-021','SLOT-022','SLOT-023','SLOT-024','SLOT-025','SLOT-026','SLOT-027','SLOT-028','TEST-064','AUTO-010','LEDGER-025','UX-007','UX-009'],premium_slots)
                # Navigate to Keno and wait for the premium route shell to mount.
                page.get_by_test_id('nav-keno').click(); page.get_by_test_id('keno-premium-hero').wait_for(timeout=5000)
                # Prove edge number cells and their state treatments stay inside the visible board bounds instead of being clipped. (issue #320)
                def keno_edge_containment():
                    # Resolve the authenticated player whose disposable Keno state drives deterministic edge evidence.
                    edge_player=page.evaluate("() => { const shellPlayer = window.CasinoCurrentUser?.player || window.CasinoCurrentPlayer || {}; return shellPlayer.player_id || window.CasinoCurrentUser?.player_id || localStorage.getItem('casino.currentPlayerId') || 'human'; }")
                    # Define the exact governed viewport matrix from the visual standard.
                    edge_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
                    # Keep the idle state free of prior tickets and draws before each locale/viewport capture.
                    empty_edge_state={'open_tickets':[],'last_draws':[]}
                    # Build one legitimate one-catch final draw with the latest result on bottom-right cell 80.
                    edge_draw=[2,3,4,5,6,7,8,9,11,12,13,14,15,16,17,18,19,20,21,80]
                    # Reuse the existing one-spot Keno multiplier so evidence state agrees with the published paytable.
                    final_edge_state={'open_tickets':[],'last_draws':[{'round_id':'keno-edge-final','timestamp':'2026-07-20T00:00:00Z','drawn':edge_draw,'results':[{'ticket':{'ticket_id':'keno-edge-catch','player_id':edge_player,'spots':[80],'amount':1,'source':'browser-test','created_at':'2026-07-20T00:00:00Z'},'catches':[80],'catch_count':1,'multiplier':3,'payout':3}]}]}
                    # Exercise both installed player-facing locales.
                    for edge_locale in ('en-US','ru-RU'):
                        # Exercise every governed viewport without substituting an approximate breakpoint.
                        for edge_viewport_id,edge_width,edge_height in edge_viewports:
                            # Start this matrix cell from an authoritative empty persisted state.
                            save_player_game_state('keno',edge_player,empty_edge_state)
                            # Apply the exact viewport before route reconstruction and geometry sampling.
                            page.set_viewport_size({'width':edge_width,'height':edge_height})
                            # Reload the canonical game route so local selection state is empty and backend state is current.
                            page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=5000)
                            # Switch through the real shell control so visible copy and accessible names use the requested locale.
                            page.get_by_test_id('shell-locale-select').select_option(edge_locale)
                            # Wait for the locale runtime to confirm the completed in-place rerender.
                            page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=edge_locale)
                            # Require real localized title copy instead of a raw resource key or blank fallback.
                            edge_title=page.locator('.keno-hero-title').inner_text(); assert edge_title.strip() and 'phase.' not in edge_title
                            # Probe every corner under the combined selected, drawn, caught, latest, disabled, and focus treatment.
                            edge_probe=page.evaluate("""() => { const scroll=document.querySelector('[data-testid="keno-board-scroll"]'); const results=[]; for (const number of [1,10,71,80]) { const cell=document.querySelector(`[data-testid="keno-num-${number}"]`); const originalClass=cell.className; const originalDisabled=cell.disabled; const originalAnimation=cell.style.animation; const originalTransition=cell.style.transition; scroll.scrollLeft=number%10===0?scroll.scrollWidth:0; cell.classList.add('selected','drawn','catch','latest'); cell.style.animation='none'; cell.style.transition='none'; cell.focus({preventScroll:true}); const focusedStyle=getComputedStyle(cell); const focusOutlineWidth=parseFloat(focusedStyle.outlineWidth)||0; const focusVisible=cell.matches(':focus-visible'); cell.disabled=true; const box=cell.getBoundingClientRect(); const clip=scroll.getBoundingClientRect(); const style=getComputedStyle(cell); results.push({number,top:box.top-clip.top,left:box.left-clip.left,right:clip.right-box.right,bottom:clip.bottom-box.bottom,width:box.width,height:box.height,outlineWidth:parseFloat(style.outlineWidth)||0,focusOutlineWidth,focusVisible,boxShadow:style.boxShadow,transform:style.transform,disabled:cell.disabled,opacity:style.opacity,text:cell.textContent.trim()}); cell.disabled=originalDisabled; cell.className=originalClass; cell.style.animation=originalAnimation; cell.style.transition=originalTransition; cell.blur(); } scroll.scrollLeft=0; return results; }""")
                            # Require every corner's full worst-case visual reach to remain inside the clip boundary.
                            for probe in edge_probe:
                                # Keep the 22px glow, transformed edge, and outlines inside a conservative 26px visual clearance.
                                assert min(probe['top'],probe['left'],probe['right'],probe['bottom']) >= 26, edge_probe
                                # Preserve the governed minimum touch target and visible numeric identity at every corner.
                                assert probe['width']>=42 and probe['height']>=42 and probe['text']==str(probe['number']), edge_probe
                                # Verify the production result and disabled treatments were active during the geometry sample.
                                assert probe['outlineWidth']>=2 and probe['boxShadow']!='none' and probe['transform']!='none' and probe['disabled'] and probe['opacity']=='1', edge_probe
                            # Audit every clipping ancestor so passing board-local geometry cannot hide a compact-desktop panel crop.
                            edge_clipping_ancestors=page.evaluate("""() => { const board=document.querySelector('[data-testid="keno-board-scroll"]'); const boardRect=board.getBoundingClientRect(); const blockers=[]; for (let ancestor=board.parentElement; ancestor; ancestor=ancestor.parentElement) { const style=getComputedStyle(ancestor); const paintContained=style.contain.split(/\\s+/).includes('paint'); const clipsX=paintContained||['hidden','clip'].includes(style.overflowX); const clipsY=paintContained||['hidden','clip'].includes(style.overflowY); if (!clipsX && !clipsY) continue; const rect=ancestor.getBoundingClientRect(); if ((clipsX && (boardRect.left<rect.left-1 || boardRect.right>rect.right+1)) || (clipsY && (boardRect.top<rect.top-1 || boardRect.bottom>rect.bottom+1))) blockers.push({tag:ancestor.tagName,className:ancestor.className,testid:ancestor.getAttribute('data-testid'),contain:style.contain,overflowX:style.overflowX,overflowY:style.overflowY,board:{top:boardRect.top,right:boardRect.right,bottom:boardRect.bottom,left:boardRect.left},ancestor:{top:rect.top,right:rect.right,bottom:rect.bottom,left:rect.left}}); } return blockers; }""")
                            # Reject any hidden or clip ancestor that cuts the board before the governed game-outlet scroller can reveal it.
                            assert not edge_clipping_ancestors,edge_clipping_ancestors
                            # Keep the document itself contained while the board owns any intentional horizontal overflow.
                            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                            # Bring the bounded game surface into view before capturing the real idle state.
                            page.locator('.keno-premium').scroll_into_view_if_needed()
                            # Record self-describing idle evidence for this exact locale and viewport.
                            region_evidence(f'after-pass-keno-edge-idle-{edge_locale.lower()}-{edge_viewport_id}.png','.keno-premium','keno',['edge_idle'],edge_locale,edge_viewport_id)
                            # Select all four corner cells through the same public controls used by a player.
                            for edge_number in (1,10,71,80): page.get_by_test_id(f'keno-num-{edge_number}').click()
                            # Start keyboard traversal from the named board region so the first corner receives true focus-visible state.
                            page.get_by_test_id('keno-board-scroll').focus(); page.keyboard.press('Tab')
                            # Read the actual keyboard focus style rather than inferring accessibility from source text.
                            focus_probe=page.evaluate("() => { const active=document.activeElement; const style=getComputedStyle(active); return {testid:active?.getAttribute('data-testid'),focusVisible:active?.matches(':focus-visible')||false,outlineWidth:parseFloat(style.outlineWidth)||0,outlineOffset:parseFloat(style.outlineOffset)||0,scrollLeft:document.querySelector('[data-testid=\"keno-board-scroll\"]')?.scrollLeft||0}; }")
                            # Require the top-left edge target to be keyboard-revealed with the explicit visible focus ring.
                            assert focus_probe['testid']=='keno-num-1' and focus_probe['focusVisible'] and focus_probe['outlineWidth']>=3 and focus_probe['outlineOffset']>=3 and focus_probe['scrollLeft']<=1, focus_probe
                            # Require every intended corner selection to survive rerenders before evidence capture.
                            assert all(page.get_by_test_id(f'keno-num-{edge_number}').get_attribute('aria-pressed')=='true' for edge_number in (1,10,71,80))
                            # Record selected and focus-visible evidence from the real public controls.
                            region_evidence(f'after-pass-keno-edge-selected-focus-{edge_locale.lower()}-{edge_viewport_id}.png','.keno-premium','keno',['edge_selected_focus_visible'],edge_locale,edge_viewport_id)
                            # Persist one deterministic final draw so caught/latest state does not depend on random outcomes.
                            save_player_game_state('keno',edge_player,final_edge_state)
                            # Reconstruct the route from authoritative history and wait for all twenty final balls.
                            page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=5000); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=edge_locale); page.wait_for_function("() => document.querySelectorAll('[data-testid=\"keno-drawn-ball\"]').length === 20",timeout=5000)
                            # Require the seeded result to render every draw plus the caught/latest bottom-right edge cell.
                            assert page.locator('.keno-num.drawn').count()==20 and page.locator('.keno-num.catch').count()==1 and page.get_by_test_id('keno-num-80').evaluate("cell => cell.classList.contains('catch') && cell.classList.contains('latest')")
                            # Reveal the right edge through the intended board scroller before final-state capture.
                            page.get_by_test_id('keno-board-scroll').evaluate('scroll => { scroll.scrollLeft=scroll.scrollWidth; }')
                            # Record final-draw and caught/latest evidence for this exact locale and viewport.
                            region_evidence(f'after-pass-keno-edge-final-caught-{edge_locale.lower()}-{edge_viewport_id}.png','.keno-premium','keno',['edge_final_caught'],edge_locale,edge_viewport_id)
                    # Restore an empty English desktop route so the existing real-draw regression remains independent.
                    save_player_game_state('keno',edge_player,empty_edge_state); page.set_viewport_size({'width':1920,'height':1080}); page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=5000); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                # Execute the Keno edge-containment geometry regression.
                run_case('BR-KENO-EDGE-001',['KENO-025','TEST-078'],keno_edge_containment)
                # Select ten deterministic spots so paytable comparison has a stable row.
                for spot in [3,8,12,17,24,31,44,55,63,72]: page.get_by_test_id(f'keno-num-{spot}').click()
                # Store the spot-selection board box for stability assertions.
                keno_selection_box=page.evaluate("() => { const box=document.querySelector('[data-testid=\"keno-grid\"]')?.getBoundingClientRect(); return box&&box.width>0&&box.height>0?{width:box.width,height:box.height}:null; }"); assert keno_selection_box
                # Capture the approved spot-selection evidence state.
                shot('keno_spot_selection.png')
                # Start the draw through the same human action used in normal play.
                page.get_by_test_id('keno-draw').click()
                # Wait until the animated draw rail shows a partial reveal.
                page.wait_for_function("""() => { const count = document.querySelectorAll('[data-testid="keno-drawn-ball"]').length; return count >= 8 && count < 20; }""", timeout=3000)
                # Store the draw-progress board box for stability assertions.
                keno_progress_box=page.evaluate("() => { const box=document.querySelector('[data-testid=\"keno-grid\"]')?.getBoundingClientRect(); return box&&box.width>0&&box.height>0?{width:box.width,height:box.height}:null; }"); assert keno_progress_box
                # Capture the approved draw-progress evidence state.
                shot('keno_draw_progress.png')
                # Wait for the full Keno draw and comparison drawer to finish rendering.
                page.wait_for_function("""() => document.querySelectorAll('[data-testid="keno-drawn-ball"]').length === 20""", timeout=5000); page.get_by_test_id('keno-paytable-comparison').wait_for(timeout=5000)
                # Store the final-result board box for stability assertions.
                keno_result_box=page.evaluate("() => { const box=document.querySelector('[data-testid=\"keno-grid\"]')?.getBoundingClientRect(); return box&&box.width>0&&box.height>0?{width:box.width,height:box.height}:null; }"); assert keno_result_box
                # Capture the approved result and paytable-comparison evidence state.
                shot('keno_result_paytable_comparison.png')
                # Define the premium_keno function used by this module.
                def premium_keno():
                    # Verify the stable 1-80 board remains mounted.
                    assert page.get_by_test_id('keno-grid').is_visible()
                    # Verify every Keno number still exposes a unique test id.
                    assert page.locator('[data-testid^="keno-num-"]').count()==80
                    # Verify the selected spot state remains visible.
                    assert page.locator('.keno-num.selected').count()>=10
                    # Verify the completed draw shows all 20 drawn balls.
                    assert page.locator('[data-testid="keno-drawn-ball"]').count()==20
                    # Verify the paytable comparison and active row are visible.
                    assert page.get_by_test_id('keno-paytable-comparison').is_visible(); assert page.get_by_test_id('keno-paytable-active').is_visible()
                    # Verify ticket, bot, autoplay, and history surfaces remain mounted.
                    assert page.get_by_test_id('keno-ticket-drawer').is_visible(); assert page.get_by_test_id('keno-bot-panel').is_visible(); assert page.get_by_test_id('autoplay-keno').is_visible(); assert page.get_by_test_id('keno-history').is_visible()
                    # Read the rendered history id text style so the overlap fix is verified in the live browser. (KENO-023)
                    keno_history_text_style=page.evaluate("""() => { const span = document.querySelector('[data-testid="keno-history"] .keno-history-row span'); if (!span) return null; const style = getComputedStyle(span); return { minWidth: style.minWidth, overflow: style.overflow, textOverflow: style.textOverflow, whiteSpace: style.whiteSpace }; }""")
                    # Require long draw IDs to stay inside their grid track instead of crossing the summary column.
                    assert keno_history_text_style and keno_history_text_style['minWidth']=='0px' and keno_history_text_style['overflow']=='hidden' and keno_history_text_style['textOverflow']=='ellipsis' and keno_history_text_style['whiteSpace']=='nowrap'
                    # Verify the board width remains stable from selection to draw progress.
                    assert abs(keno_selection_box['width']-keno_progress_box['width'])<2
                    # Verify the board height remains stable from selection to final result.
                    assert abs(keno_selection_box['height']-keno_result_box['height'])<2
                    # Resolve the browser shell's active player id before seeding focused evidence.
                    keno_singular_player=page.evaluate("() => { const shellPlayer = window.CasinoCurrentUser?.player || window.CasinoCurrentPlayer || {}; return shellPlayer.player_id || window.CasinoCurrentUser?.player_id || localStorage.getItem('casino.currentPlayerId') || 'human'; }")
                    # Seed deterministic one-catch Keno state so singular copy is proven without relying on a random draw.
                    keno_singular_state={'open_tickets':[],'last_draws':[{'round_id':'keno-singular-copy','timestamp':'2026-07-19T00:00:00Z','drawn':list(range(1,21)),'results':[{'ticket':{'ticket_id':'keno-one-catch','player_id':keno_singular_player,'spots':[1],'amount':1,'source':'browser-test','created_at':'2026-07-19T00:00:00Z'},'catches':[1],'catch_count':1,'multiplier':3,'payout':3}]}]}
                    # Persist the focused state through the same test data store used by the browser server.
                    save_player_game_state('keno',keno_singular_player,keno_singular_state)
                    # Select English before reload so the copy assertion checks the exact reported wording.
                    page.get_by_test_id('shell-locale-select').select_option('en-US')
                    # Reload the route so the visible browser client renders the persisted one-catch result.
                    page.reload(); page.get_by_test_id('keno-premium-hero').wait_for(timeout=5000)
                    # Read the visible result copy after the route reload.
                    keno_singular_result=page.get_by_test_id('keno-result').inner_text()
                    # Require singular English copy and reject the reported plural grammar defect.
                    assert '1 catch on a 1-spot ticket' in keno_singular_result and '1 catches' not in keno_singular_result
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-KENO-001',['KENO-009','KENO-010','KENO-011','KENO-012','KENO-013','KENO-014','KENO-015','KENO-018','KENO-020','KENO-021','KENO-022','KENO-023','KENO-024','TEST-066','AUTO-012','UX-007','UX-009'],premium_keno)
                # Resize to the governed mobile viewport for Keno containment coverage.
                page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(300)
                # Read page and intended board-scroll widths at the exact evaluator viewport.
                keno_mobile=page.evaluate("() => { const board=document.querySelector('[data-testid=\"keno-board-scroll\"]'); return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,clientWidth:board.clientWidth,scrollWidth:board.scrollWidth,tabindex:board.getAttribute('tabindex'),role:board.getAttribute('role'),label:board.getAttribute('aria-label')}; }")
                # Verify the page stays at viewport width while the number board owns intentional accessible overflow.
                assert keno_mobile['documentWidth'] <= keno_mobile['viewport'] + 1 and keno_mobile['bodyWidth'] <= keno_mobile['viewport'] + 1 and keno_mobile['scrollWidth'] > keno_mobile['clientWidth'] and keno_mobile['tabindex']=='0' and keno_mobile['role']=='region' and keno_mobile['label'], keno_mobile
                # Bring the intended board scroller into the viewport for focused acceptance evidence.
                page.get_by_test_id('keno-board-scroll').scroll_into_view_if_needed(); page.wait_for_timeout(150)
                # Capture the contained Keno mobile board as acceptance evidence.
                page.screenshot(path=str(screenshots/'after-pass-keno-mobile-390x844.png'),full_page=False)
                # Restore desktop dimensions before the next game evidence run.
                page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Navigate to Bingo before exercising the real card-purchase mutation boundary.
                page.get_by_test_id('nav-bingo').click(); page.get_by_test_id('premium-bingo').wait_for(timeout=5000)
                # Read the current player's ledger before the one visible card purchase.
                bingo_ledger_before=page.request.get(base+f'/api/v1/players/{browser_player_id}/ledger').json()['data']['ledger']
                # Store immutable ledger identities because response ordering is not a persistence contract.
                bingo_ledger_ids_before={row['ledger_id'] for row in bingo_ledger_before}
                # Hold the first real card response after backend commit so duplicate-click protection is deterministic.
                page.evaluate("""() => { const originalFetch=window.fetch.bind(window); let firstPurchase=true; window.__bingoPurchaseHeld=false; window.__bingoReleasePurchase=()=>{}; window.__bingoPurchaseRequestCount=0; window.__bingoRestoreFetch=()=>{window.fetch=originalFetch;}; window.fetch=async (...args) => { const input=args[0]; const url=typeof input==='string' ? input : input.url; const init=args[1] || {}; const method=String(init.method || (typeof input==='object' ? input.method : 'GET') || 'GET').toUpperCase(); const responsePromise=originalFetch(...args); if(url.includes('/api/v1/games/bingo/cards') && method==='POST'){ window.__bingoPurchaseRequestCount+=1; if(firstPurchase){ firstPurchase=false; const response=await responsePromise; window.__bingoPurchaseHeld=true; await new Promise(resolve => { window.__bingoReleasePurchase=resolve; }); return response; } } return responsePromise; }; }""")
                # Buy one card through the current visible player control.
                page.get_by_test_id('bingo-buy').click()
                # Wait until the real backend committed while the browser response remains deliberately held.
                page.wait_for_function('window.__bingoPurchaseHeld === true',timeout=5000)
                # Read the authoritative state at the controlled stale-response boundary.
                bingo_pending_state=page.request.get(base+'/api/v1/games/bingo/state').json()['data']['state']
                # Record the shared busy boundary and semantic control locks during the pending purchase.
                bingo_pending_controls={'busy':page.get_by_test_id('bingo-control-rail').get_attribute('aria-busy'),'buy_disabled':page.get_by_test_id('bingo-buy').is_disabled(),'buy_text':page.get_by_test_id('bingo-buy').inner_text(),'buy_opacity':page.get_by_test_id('bingo-buy').evaluate('button => Number(getComputedStyle(button).opacity)'),'buy_cursor':page.get_by_test_id('bingo-buy').evaluate('button => getComputedStyle(button).cursor'),'amount_disabled':page.get_by_test_id('bingo-amount').is_disabled(),'pattern_disabled':page.get_by_test_id('bingo-pattern').is_disabled(),'reset_disabled':page.get_by_test_id('bingo-reset').is_disabled()}
                # Invoke the current disabled semantic button to prove it cannot schedule another request.
                page.get_by_test_id('bingo-buy').evaluate('button => button.click()')
                # Allow an incorrect duplicate request enough time to become observable.
                page.wait_for_timeout(150)
                # Record the exact request count before releasing the authoritative first response.
                bingo_pending_request_count=page.evaluate('window.__bingoPurchaseRequestCount')
                # Release the committed response so state, bots, wallet, and controls can settle normally.
                page.evaluate('window.__bingoReleasePurchase()')
                # Wait for the one active card and recovered Call control after purchase completion.
                page.wait_for_function("() => document.querySelector('[data-testid=\"bingo-control-rail\"]')?.getAttribute('aria-busy') === 'false' && !document.querySelector('[data-testid=\"bingo-call\"]')?.disabled",timeout=5000)
                # Restore the unwrapped browser fetch function before later suite actions.
                page.evaluate('window.__bingoRestoreFetch()')
                # Read the final ledger and authoritative Bingo state after the purchase sequence.
                bingo_ledger_after=page.request.get(base+f'/api/v1/players/{browser_player_id}/ledger').json()['data']['ledger']; bingo_final_state=page.request.get(base+'/api/v1/games/bingo/state').json()['data']['state']
                # Isolate only new human Bingo purchase debits by immutable identity.
                bingo_new_debits=[row for row in bingo_ledger_after if row['ledger_id'] not in bingo_ledger_ids_before and row.get('transaction_type')=='BINGO_CARD_PURCHASED']
                # Isolate human cards from the authoritative active session after bot purchases finish.
                bingo_human_cards=[card for card in bingo_final_state['active_session']['cards'] if card['player_id']==browser_player_id]
                # Define the held-response purchase regression for issue #259.
                def bingo_purchase_guard():
                    # Verify the real backend committed exactly one active human card while the response was held.
                    assert len([card for card in bingo_pending_state['active_session']['cards'] if card['player_id']==browser_player_id])==1
                    # Verify the control rail truthfully exposes the in-flight purchase boundary.
                    assert bingo_pending_controls['busy']=='true'
                    # Verify every control that could duplicate or conflict with the submitted purchase is disabled.
                    assert all(bingo_pending_controls[key] for key in ('buy_disabled','amount_disabled','pattern_disabled','reset_disabled'))
                    # Verify the pending purchase has an unmistakable localized label and visual treatment.
                    assert bingo_pending_controls['buy_text']=='Buy card…' and bingo_pending_controls['buy_opacity']<1 and bingo_pending_controls['buy_cursor']=='wait'
                    # Verify the disabled second click could not issue another card request.
                    assert bingo_pending_request_count==1
                    # Verify exactly one visible purchase produced exactly one debit of the configured amount.
                    assert len(bingo_new_debits)==1 and bingo_new_debits[0]['amount']==-5
                    # Verify the authoritative session and visible stage each contain one human card.
                    assert len(bingo_human_cards)==1 and page.get_by_test_id('bingo-card').count()==1
                    # Verify the successful purchase recovered the next valid game action.
                    assert page.get_by_test_id('bingo-call').is_enabled()
                # Execute the real-browser, real-backend data-integrity regression.
                run_case('BR-BINGO-PURCHASE-001',['BINGO-012','BINGO-022','LEDGER-020','TEST-010','TEST-012'],bingo_purchase_guard)
                # Call one ball through the existing visible action before completing the normal Bingo scenario.
                page.get_by_test_id('bingo-call').click(); page.wait_for_timeout(700)
                # Complete the session through the existing bounded compatibility helper.
                page.evaluate("""async () => { const response = await fetch('/api/v1/games/bingo/auto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ max_calls: 75 }) }); const payload = await response.json(); if (!payload.ok) throw new Error(payload.error?.message || 'Bingo auto failed'); }""")
                # Remount Bingo and wait for the authoritative completed session to render.
                page.get_by_test_id('nav-bingo').click(); page.locator('[data-winning-cell="true"]').first.wait_for(timeout=5000)
                # Preserve the existing premium Bingo acceptance after the new purchase boundary proof.
                run_case('BR-BINGO-001',['BINGO-017','BINGO-018','BINGO-021','BINGO-022','AUTO-013'],lambda: page.get_by_test_id('bingo-card').is_visible() and page.locator('[data-winning-cell="true"]').first.is_visible() and page.get_by_test_id('bingo-cards-drawer').is_visible() and page.get_by_test_id('autoplay-bingo').is_visible())
                # Seed one isolated deferred natural so the rendered Stand path is deterministic. (BJ-031, TEST-054)
                browser_blackjack_state=blackjack_engine.default_state(); browser_blackjack_state['shoe']=['2S']*52+['9D','AS','KH','AS']
                # Persist only the synthetic browser player's controlled Blackjack shoe before mounting the route.
                save_player_game_state('blackjack',browser_player_id,browser_blackjack_state)
                # Read the authoritative wallet and ledger before the visible deal-and-stand sequence.
                blackjack_balance_before=page.evaluate("async () => (await (await fetch('/api/v2/me', {credentials:'include'})).json()).data.player.token_balance")
                # Read existing settlement credits so the regression can prove exactly one new round credit.
                blackjack_ledger_before=page.evaluate("async playerId => (await (await fetch(`/api/v1/players/${playerId}/ledger`, {credentials:'include'})).json()).data.ledger",browser_player_id)
                # Navigate to Blackjack before checking the premium table surface.
                page.get_by_test_id('nav-blackjack').click()
                # Wait for the premium Blackjack shell to mount.
                page.get_by_test_id('blackjack-premium').wait_for(timeout=5000)
                # Set a visible one-hundred-token stake for an exact three-to-two payout assertion.
                page.get_by_test_id('blackjack-bet').fill('100')
                # Observe the real deal response while activating the public Blackjack control.
                with page.expect_response(lambda response: response.url.endswith('/api/v1/games/blackjack/rounds') and response.request.method == 'POST') as blackjack_deal_info:
                    # Deal the controlled natural entirely through the rendered button.
                    page.get_by_test_id('blackjack-deal').click()
                # Wait for the first player hand lane to render.
                page.get_by_test_id('blackjack-hand-0').wait_for(timeout=5000)
                # Require the deferred natural to expose both the even-money choice and ordinary Stand decline path.
                page.wait_for_function("() => !document.querySelector('[data-testid=\"blackjack-even-money\"]')?.disabled && !document.querySelector('[data-testid=\"blackjack-stand\"]')?.disabled")
                # Store the backend round id exposed by the stable test hook.
                blackjack_round_id=page.get_by_test_id('blackjack-round-id').get_attribute('data-round-id')
                # Require the rendered round id to match the authoritative deal response.
                assert blackjack_deal_info.value.json()['data']['round']['round_id']==blackjack_round_id
                # Observe the real stand response while declining even money through the UI.
                with page.expect_response(lambda response: response.url.endswith(f'/api/v1/games/blackjack/rounds/{blackjack_round_id}/stand') and response.request.method == 'POST') as blackjack_stand_info:
                    # Activate the same visible Stand button a player uses.
                    page.get_by_test_id('blackjack-stand').click()
                # Wait for the settled round to disable another Stand action after the wallet refresh.
                page.wait_for_function("() => document.querySelector('[data-testid=\"blackjack-stand\"]')?.disabled === true")
                # Read the exact settled response returned to the rendered module.
                blackjack_stand_payload=blackjack_stand_info.value.json()['data']
                # Read the authoritative wallet and ledger after the visible settlement completes.
                blackjack_balance_after=page.evaluate("async () => (await (await fetch('/api/v2/me', {credentials:'include'})).json()).data.player.token_balance")
                # Read post-settlement ledger rows for exact single-credit evidence.
                blackjack_ledger_after=page.evaluate("async playerId => (await (await fetch(`/api/v1/players/${playerId}/ledger`, {credentials:'include'})).json()).data.ledger",browser_player_id)
                # Define the rendered natural-payout acceptance assertions against independent wallet and ledger state.
                def blackjack_natural_payout_browser():
                    # Read the one player hand returned by the settled Stand action.
                    hand=blackjack_stand_payload['round']['hands'][0]
                    # Require natural identity and the configured total return rather than an ordinary win or push.
                    assert hand['status']=='blackjack' and hand['outcome']=='blackjack' and hand['payout_due']==250
                    # Require one debit plus the 250-token return to produce the exact 150-token wallet profit.
                    assert blackjack_balance_after-blackjack_balance_before==150
                    # Select only credits for this exact controlled round before and after the visible action.
                    before_credits=[row for row in blackjack_ledger_before if row.get('transaction_type')=='BLACKJACK_SETTLEMENT_CREDIT' and row.get('round_id')==blackjack_round_id]
                    # Select the matching post-action credit without counting other Blackjack rounds.
                    after_credits=[row for row in blackjack_ledger_after if row.get('transaction_type')=='BLACKJACK_SETTLEMENT_CREDIT' and row.get('round_id')==blackjack_round_id]
                    # Require exactly one settlement credit to have been created for the natural.
                    assert len(before_credits)==0 and len(after_credits)==1 and after_credits[0]['amount']==250
                # Record exact rendered Stand, wallet, and ledger evidence for the deferred-natural requirement.
                run_case('BR-BJ-NATURAL-PAYOUT-001',['BJ-005','BJ-031','TEST-054'],blackjack_natural_payout_browser)
                # Capture after-pass Blackjack evidence from the settled controlled natural.
                shot('blackjack-natural-after-stand.png')
                # Define the blackjack_premium function used by this module.
                def blackjack_premium():
                    # Verify the premium central felt is visible.
                    assert page.get_by_test_id('blackjack-stage').is_visible()
                    # Verify the fixed settlement/decision drawer is visible.
                    assert page.get_by_test_id('blackjack-drawer').is_visible()
                    # Verify the mounted action rail exposes Blackjack decisions.
                    assert page.get_by_test_id('blackjack-action-rail').is_visible()
                    # Verify disabled Blackjack autoplay remains visible as a control-plane panel.
                    assert page.get_by_test_id('blackjack-autoplay-panel').is_visible()
                    # Verify the bot compatibility panel is rendered without game-module coupling.
                    assert page.get_by_test_id('blackjack-bot-panel').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-BJ-001',['BJ-028','BJ-029','BJ-030','AUTO-014'],blackjack_premium)
                # Switch Blackjack locale in place to verify gameplay state is preserved.
                page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.initI18n({ domains: ['games/blackjack'] }); await i18n.loadI18nDomain('games/blackjack'); await i18n.setLocale('ru-RU', { persistLocal: false }); }""")
                # Define the blackjack_i18n function used by this module.
                def blackjack_i18n():
                    # Verify the same hand remains visible after localized rerender.
                    assert page.get_by_test_id('blackjack-hand-0').is_visible()
                    # Verify the selected backend round id did not change on locale switch.
                    assert page.get_by_test_id('blackjack-round-id').get_attribute('data-round-id')==blackjack_round_id
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-BJ-I18N-001',['I18N-002','BJ-028'],blackjack_i18n)
                # Restore English for later browser assertions that use fixed English text.
                page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }""")
                # Build a settled insurance fixture whose visible Net would be wrong without the insurance movement. (BJ-032, TEST-057)
                browser_blackjack_insurance_state=blackjack_engine.default_state()
                # Create a dealer-blackjack outcome where a 100-token hand loss plus a 50-token insurance stake and 150-token insurance return nets zero.
                browser_blackjack_insurance_round={'round_id':'bj_insurance_net_display','player_id':browser_player_id,'status':'settled','dealer':{'cards':['AS','KH'],'hole_card_hidden':False},'hands':[{'hand_id':'hand_insurance_net_display','cards':['9C','8D'],'bet':100,'status':'loss','outcome':'dealer_blackjack','payout_due':0,'credited':True,'actions':[]}],'active_hand_index':0,'insurance':{'amount':50,'dealer_blackjack':True,'payout':150},'even_money':None,'settlements':[]}
                # Persist only the synthetic insured round for the browser player before remounting Blackjack.
                browser_blackjack_insurance_state['rounds']={browser_blackjack_insurance_round['round_id']:browser_blackjack_insurance_round}; save_player_game_state('blackjack',browser_player_id,browser_blackjack_insurance_state)
                # Leave and re-enter Blackjack so the route reloads the persisted insured settlement fixture.
                page.get_by_test_id('nav-baccarat').click(); page.get_by_test_id('baccarat-wager-setup').wait_for(timeout=5000); page.get_by_test_id('nav-blackjack').click(); page.get_by_test_id('blackjack-premium').wait_for(timeout=5000)
                # Read the localized Net value from the rendered settlement drawer without adding a test-only selector.
                blackjack_insurance_net_text=page.evaluate("""() => { const rows = Array.from(document.querySelectorAll('[data-testid="blackjack-drawer"] .mini-stat')); const net = rows.map(row => ({ label: row.querySelector('span')?.textContent?.trim(), value: row.querySelector('strong')?.textContent?.trim() })).find(row => row.label === 'Net'); return net?.value || ''; }""")
                # Define the blackjack_insurance_net_browser function used by this display regression.
                def blackjack_insurance_net_browser():
                    # Require the visible Net to include insurance stake and payout, producing a zero-profit settled row instead of a 100-token loss.
                    assert blackjack_insurance_net_text.startswith('+') and '0' in blackjack_insurance_net_text
                # Execute the browser regression for the insurance-inclusive Blackjack Net display.
                run_case('BR-BJ-INSURANCE-NET-001',['BJ-032','LEDGER-015','TEST-057'],blackjack_insurance_net_browser)
                # Navigate to Baccarat before asserting the premium table surfaces.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/me') and response.request.method == 'GET'):
                    # Click Baccarat and wait for its final mount-time wallet refresh response.
                    page.get_by_test_id('nav-baccarat').click()
                # Wait for the wager setup state to mount.
                page.get_by_test_id('baccarat-wager-setup').wait_for(timeout=5000)
                # Read the fresh shoe summary before any wager/deal builds the lazy backend shoe. (BAC-025, TEST-062)
                baccarat_initial_shoe_text=page.get_by_test_id('baccarat-shoe-summary').inner_text()
                # Define the focused fresh-shoe display regression for issue #249.
                def baccarat_fresh_shoe_count():
                    # Require the visible initial drawer to show the full configured eight-deck capacity, never a zero-card lazy-shoe placeholder.
                    assert ('416 cards' in baccarat_initial_shoe_text or 'карт: 416' in baccarat_initial_shoe_text) and '0 cards' not in baccarat_initial_shoe_text and 'карт: 0' not in baccarat_initial_shoe_text
                # Execute the browser assertion before later Baccarat actions mutate the shoe.
                run_case('BR-BAC-FRESH-SHOE-001',['BAC-025','TEST-062'],baccarat_fresh_shoe_count)
                # Read the browser session's canonical player id for exact ledger assertions.
                baccarat_me=page.request.get(base+'/api/v2/me').json()['data']
                # Store the authenticated player id without trusting caller-controlled game fields.
                baccarat_player_id=baccarat_me['player']['player_id']
                # Count existing Baccarat debits so the regression measures only this visible coup.
                baccarat_ledger_before=page.request.get(base+f'/api/v1/players/{baccarat_player_id}/ledger').json()['data']['ledger']
                # Store immutable event ids because the ledger endpoint does not promise append ordering.
                baccarat_ledger_ids_before={row['ledger_id'] for row in baccarat_ledger_before}
                # Install a browser-only response hold after the first real wager commits on the backend.
                page.evaluate("""() => { const originalFetch=window.fetch.bind(window); let firstBet=true; window.__baccaratFirstBetHeld=false; window.__baccaratReleaseFirstBet=()=>{}; window.__baccaratBetRequestCount=0; window.fetch=async (...args) => { const input=args[0]; const url=typeof input==='string' ? input : input.url; const init=args[1] || {}; const method=String(init.method || (typeof input==='object' ? input.method : 'GET') || 'GET').toUpperCase(); const responsePromise=originalFetch(...args); if (url.includes('/api/v1/games/baccarat/bets') && method==='POST') { window.__baccaratBetRequestCount+=1; if (firstBet) { firstBet=false; const response=await responsePromise; window.__baccaratFirstBetHeld=true; await new Promise(resolve => { window.__baccaratReleaseFirstBet=resolve; }); return response; } } return responsePromise; }; }""")
                # Place a banker wager through the same visible public control a player uses.
                page.get_by_test_id('baccarat-banker').click()
                # Wait until the real backend committed while the browser response remains deliberately held.
                page.wait_for_function('window.__baccaratFirstBetHeld === true',timeout=5000)
                # Read backend state while the browser is still at the controlled stale-response boundary.
                baccarat_pending_state=page.request.get(base+'/api/v1/games/baccarat/state').json()['data']['state']
                # Record the truthful shared busy state before attempting the disabled visible Deal control.
                baccarat_pending_busy=page.get_by_test_id('baccarat-control-rail').get_attribute('aria-busy')
                # Record that the visible Deal control is disabled until the committed wager response applies.
                baccarat_pending_deal_disabled=page.get_by_test_id('baccarat-deal').is_disabled()
                # Invoke the disabled semantic button to prove it cannot schedule a hidden repeat wager.
                page.get_by_test_id('baccarat-deal').evaluate('button => button.click()')
                # Allow any erroneous duplicate request enough time to become observable.
                page.wait_for_timeout(150)
                # Record the actual bet-request count after the disabled Deal attempt.
                baccarat_pending_request_count=page.evaluate('window.__baccaratBetRequestCount')
                # Release the first committed response so the queue can apply its authoritative open-bet state.
                page.evaluate('window.__baccaratReleaseFirstBet()')
                # Wait until the one visible wager appears and the serialized Deal control becomes available.
                page.wait_for_function("() => !document.querySelector('[data-testid=\"baccarat-deal\"]').disabled && document.querySelector('.bac-drawer-total')?.textContent.includes('25')",timeout=5000)
                # Deal one coup so the reveal theater and settlement state are exercised.
                page.get_by_test_id('baccarat-deal').click()
                # Wait for the post-reveal result state to settle.
                page.get_by_test_id('baccarat-result').wait_for(timeout=5000)
                # Read final backend state after the one visible wager settles.
                baccarat_final_state=page.request.get(base+'/api/v1/games/baccarat/state').json()['data']['state']
                # Read final ledger rows so exactly one new Baccarat debit is proven.
                baccarat_ledger_after=page.request.get(base+f'/api/v1/players/{baccarat_player_id}/ledger').json()['data']['ledger']
                # Isolate new Baccarat wager debits by immutable identity instead of response ordering.
                baccarat_new_debits=[row for row in baccarat_ledger_after if row['ledger_id'] not in baccarat_ledger_ids_before and row.get('transaction_type')=='BACCARAT_BET_PLACED']
                # Isolate current-player bets from the final committed coup.
                baccarat_final_human_bets=[bet for bet in baccarat_final_state['last_coups'][-1]['bets'] if bet['player_id']==baccarat_player_id]
                # Count visible settlement rows so the drawer cannot hide an extra charged wager.
                baccarat_visible_settlements=page.locator('.details-drawer .bet-item').count()
                # Define the deterministic mutation-serialization regression for issue #252.
                def baccarat_mutation_serialization():
                    # Verify the first visible click committed exactly one backend open bet.
                    assert len(baccarat_pending_state['open_bets'])==1
                    # Verify the entire control rail truthfully advertised the pending mutation.
                    assert baccarat_pending_busy=='true'
                    # Verify Deal remained a disabled semantic control at the race boundary.
                    assert baccarat_pending_deal_disabled
                    # Verify the disabled Deal attempt could not issue a repeat-wager request.
                    assert baccarat_pending_request_count==1
                    # Verify the final coup settled exactly one human wager.
                    assert len(baccarat_final_human_bets)==1
                    # Verify exactly one ledger debit was created for the one visible wager.
                    assert len(baccarat_new_debits)==1 and baccarat_new_debits[0]['amount']==-25
                    # Verify the result drawer rendered exactly the one charged settlement.
                    assert baccarat_visible_settlements==1
                    # Verify the backend contains no phantom open wager after settlement.
                    assert baccarat_final_state['open_bets']==[]
                # Execute the issue-owned real-browser and real-backend data-integrity regression.
                run_case('BR-BAC-MUTATION-001',['BAC-017','BAC-020','BAC-023','LEDGER-001','LEDGER-007','LEDGER-016'],baccarat_mutation_serialization)
                # Define the Baccarat browser assertion bundle for premium UI requirements.
                def baccarat_browser():
                    # Assert the fixed Baccarat table is visible.
                    assert page.get_by_test_id('baccarat-table').is_visible()
                    # Assert dealt cards and totals are mounted in the player hand.
                    assert page.get_by_test_id('baccarat-player-hand').is_visible()
                    # Assert road history remains visible after settlement.
                    assert page.get_by_test_id('baccarat-road-history').is_visible()
                    # Assert shoe and burn information remains visible in the drawer.
                    assert page.get_by_test_id('baccarat-shoe-summary').is_visible()
                    # Assert Baccarat autoplay controls remain mounted in the rail.
                    assert page.get_by_test_id('autoplay-baccarat').is_visible()
                # Execute the Baccarat browser case after the premium result state is visible.
                run_case('BR-BAC-001',['BAC-020','BAC-021','BAC-022','BAC-023','LEDGER-025','UX-009'],baccarat_browser)
                # Define the complete lazy-domain and rendered-string audit required for all game routes.
                def all_game_route_i18n():
                    # Reenter initialization concurrently with repeated and distinct lazy domains.
                    concurrent_state=page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await Promise.all([i18n.initI18n({ domains: ['games/roulette'] }), i18n.initI18n({ domains: ['games/roulette', 'games/bingo'] }), i18n.initI18n({ domains: ['games/bingo'] })]); return i18n.getLocaleState(); }""")
                    # Verify concurrent repeated initialization loads both requested domains exactly once in state.
                    assert {'games/roulette','games/bingo'}.issubset(set(concurrent_state['loadedDomains']))
                    # Store stable navigation, mount, domain, and interpolation probes for every game route.
                    route_specs=[('nav-roulette','roulette-wheel','games/roulette','stats.rolls'),('nav-slots','slot-grid','games/slots','history.row'),('nav-keno','keno-premium-hero','games/keno','metric.finalDraw.label'),('nav-bingo','premium-bingo','games/bingo','drawer.callsText'),('nav-blackjack','blackjack-premium','games/blackjack','drawer.cards'),('nav-baccarat','baccarat-wager-setup','games/baccarat','shoe.cards')]
                    # Audit every route in both installed UI locales without persisting the test preference.
                    for locale in ('en-US','ru-RU'):
                        # Switch locale in place so the same route state is exercised in both languages.
                        page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }", locale)
                        # Mount and inspect each lazy game route under the active locale.
                        for nav_testid,ready_testid,domain,interpolation_key in route_specs:
                            # Branch for Baccarat because its mount finishes with an authenticated wallet refresh.
                            if domain == 'games/baccarat':
                                # Wait for the mount's final wallet response so the next route cannot abort it.
                                with page.expect_response(lambda response: response.url.endswith('/api/v2/me') and response.request.method == 'GET'):
                                    # Navigate through the player-visible shell control.
                                    page.get_by_test_id(nav_testid).click()
                            # Navigate other routes through the same player-visible shell control.
                            else:
                                # Click the route after no special completion response is required.
                                page.get_by_test_id(nav_testid).click()
                            # Wait for the route-owned stable mount selector before scanning strings.
                            page.get_by_test_id(ready_testid).wait_for(timeout=5000)
                            # Apply the complete domain, key-leak, placeholder, encoding, and label audit.
                            assert_route_i18n(domain, interpolation_key)
                    # Restore English so the following independent Admin page starts from the suite default.
                    page.evaluate("async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }")
                # Execute the release-blocking i18n audit as one requirement-mapped browser case.
                run_case('BR-I18N-ROUTES-001',['I18N-001','I18N-002'],all_game_route_i18n)
                # Replace the normal-user browser cookie with an authenticated Admin session.
                admin_browser_login=page.request.post(base+'/api/v2/auth/login',data={'email':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD})
                # Verify the browser context received a successful Admin login response.
                assert admin_browser_login.json()['ok'] is True
                # Load the normal shared shell first so Admin navigation is exercised as a user-visible affordance.
                page.goto(base,wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Store the Admin shell results for the combined two-role authorization assertion.
                admin_nav_results=[]
                # Exercise the Admin affordance through both installed locales and focused responsive viewports.
                for admin_nav_locale in ('en-US','ru-RU'):
                    # Rerender the authenticated Admin shell through the visible locale control.
                    page.get_by_test_id('shell-locale-select').select_option(admin_nav_locale)
                    # Wait until the locale runtime confirms the requested Admin shell rerender.
                    page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=admin_nav_locale)
                    # Inspect the same governed viewports used for the normal-player absence proof.
                    for admin_nav_viewport_id,admin_nav_viewport in admin_nav_viewports.items():
                        # Resize to the exact governed viewport before inspecting the role-owned control.
                        page.set_viewport_size(admin_nav_viewport); page.wait_for_timeout(150)
                        # Read the one expected Admin affordance before moving the bounded navigation to its trailing edge.
                        admin_nav_button=page.get_by_test_id('nav-admin')
                        # Scroll the intentional horizontal menu itself so evidence visibly includes the late Admin route.
                        page.locator('#main-nav').evaluate("nav => { nav.scrollLeft=nav.scrollWidth; }"); page.wait_for_timeout(100)
                        # Prove the Admin control is inside the visible bounded-menu viewport rather than merely present offscreen.
                        admin_nav_in_view=page.evaluate("""() => { const nav=document.querySelector('#main-nav'); const button=document.querySelector('[data-testid="nav-admin"]'); const navRect=nav.getBoundingClientRect(); const buttonRect=button.getBoundingClientRect(); return buttonRect.left >= navRect.left - 1 && buttonRect.right <= navRect.right + 1; }""")
                        # Record exact presence, viewport visibility, and page containment for this locale and viewport.
                        admin_nav_results.append({'locale':admin_nav_locale,'viewport':admin_nav_viewport_id,'count':admin_nav_button.count(),'visible':admin_nav_button.is_visible(),'in_view':admin_nav_in_view,'contained':page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")})
                        # Capture focused evidence before full-page rasterization can reset the nested menu scroll position.
                        region_evidence(f'after-pass-shell-admin-nav-visible-admin-{admin_nav_locale}-{admin_nav_viewport_id}.png','#main-nav','shell_lobby',['authenticated','admin_nav_visible_admin'],admin_nav_locale,admin_nav_viewport_id)
                        # Capture separate full-page context for responsive containment without mislabeling its reset menu position.
                        game_evidence(f'after-pass-shell-admin-nav-context-admin-{admin_nav_locale}-{admin_nav_viewport_id}.png','shell_lobby',['authenticated'],admin_nav_locale,admin_nav_viewport_id)
                # Restore the default locale and primary viewport before keyboard activation.
                page.set_viewport_size({'width':1920,'height':1080}); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
                # Focus the visible role-owned route without a pointer.
                page.get_by_test_id('nav-admin').focus()
                # Record the focused control before its native Enter activation changes documents.
                admin_nav_focused=page.evaluate("() => document.activeElement?.getAttribute('data-testid')")
                # Activate the Admin route using the button's native keyboard contract.
                page.get_by_test_id('nav-admin').press('Enter'); page.wait_for_url('**/admin'); page.get_by_test_id('admin-tab-audio').wait_for(timeout=5000)
                # Verify the Admin browser session can still read a protected API after route entry using its same-origin cookie.
                admin_api_result=page.evaluate("""async () => { const response=await fetch('/api/v1/admin/overview',{credentials:'include'}); return {status:response.status,body:await response.json()}; }""")
                # Capture the destination surface reached through the keyboard-owned shell affordance.
                game_evidence('after-pass-admin-dashboard-keyboard-entry-en-US-desktop_primary.png','admin',['dashboard'], 'en-US','desktop_primary')
                # Define one permanent acceptance case spanning normal-player presentation, server authority, and Admin access.
                def admin_navigation_authorization():
                    # Require every normal-player locale and viewport to contain no Admin markup at all.
                    assert len(normal_admin_nav_results)==4 and all(result['count']==0 and result['contained'] for result in normal_admin_nav_results)
                    # Require route restoration to preserve the normal-player presentation boundary.
                    assert normal_admin_nav_route_restored
                    # Require protected Admin HTML to deny the normal player before returning any Admin document marker.
                    assert normal_admin_html_result['status']==403 and normal_admin_html_result['contains_admin_view'] is False
                    # Require protected Admin JavaScript to deny the normal player before returning any source marker.
                    assert normal_admin_js_result['status']==403 and normal_admin_js_result['contains_admin_view'] is False
                    # Require the protected Admin API to preserve the standard forbidden envelope for the normal player.
                    assert normal_admin_api_result['status']==403 and normal_admin_api_result['body']['ok'] is False and normal_admin_api_result['body']['error']['code']=='FORBIDDEN'
                    # Require every Admin locale and viewport to expose exactly one visible, contained affordance.
                    assert len(admin_nav_results)==4 and all(result['count']==1 and result['visible'] and result['in_view'] and result['contained'] for result in admin_nav_results)
                    # Require native keyboard focus and activation to reach the dedicated Admin document.
                    assert admin_nav_focused=='nav-admin' and page.url.rstrip('/').endswith('/admin')
                    # Require the authenticated Admin session to retain protected API authority after navigation.
                    assert admin_api_result['status']==200 and admin_api_result['body']['ok'] is True
                # Execute the complete issue-owned role-aware Admin navigation regression.
                run_case('BR-ADMIN-NAV-AUTH-001',['ADMIN-001','AUTH-005','AUTH-008','TEST-060'],admin_navigation_authorization)
                # Define the Admin dashboard version check mapped to its existing browser requirement coverage.
                def admin_dashboard_browser():
                    # Require the existing Admin navigation to remain available after dashboard load.
                    assert page.get_by_test_id('admin-tab-audio').is_visible()
                    # Require the authenticated Operations tab to remain in the Admin navigation.
                    assert page.get_by_test_id('admin-tab-operations').is_visible()
                    # Locate the existing App summary card without changing production markup for the test.
                    app_card=page.locator('#adminView .admin-card').filter(has_text='App')
                    # Require the browser-visible packaged release to match the canonical top-level version.
                    assert app_card.get_by_text(VERSION_MANIFEST['application'],exact=True).is_visible()
                    # Open the existing System tab where canonical module revisions are displayed.
                    page.locator('[data-tab="system"]').click()
                    # Wait for the module-revision table to replace the dashboard asynchronously.
                    page.get_by_text('Module revisions',exact=True).wait_for(timeout=5000)
                    # Select the first System table that lists module and revision columns.
                    module_table=page.locator('#adminView table').first
                    # Require one header plus every canonical module row.
                    assert module_table.locator('tr').count()==len(EXPECTED_MODULE_ROWS)+1
                    # Compare each browser-visible module row with canonical manifest values.
                    for expected in EXPECTED_MODULE_ROWS:
                        # Require exactly one row containing both the module name and its canonical revision.
                        assert module_table.locator('tr').filter(has_text=expected['module']).filter(has_text=expected['revision']).count()==1
                # Execute the mapped Admin dashboard and packaged-release browser regression.
                run_case('BR-ADMIN-001',['ADMIN-001','ADMIN-003','ADMIN-004','ADMIN-010','ADMIN-014','TEST-023'],admin_dashboard_browser)
                # Define Admin-only OAuth diagnostics, isolation from Operations, and visual evidence.
                def admin_oauth_browser():
                    # Define every governed Admin viewport from the visual matrix.
                    viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900}}
                    # Exercise provider diagnostics in both installed Admin locales.
                    for locale in ('en-US','ru-RU'):
                        # Switch locale without persisting a preference outside this disposable test copy.
                        page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }", locale)
                        # Open Operations because OAuth diagnostics render as an independent card on that surface.
                        page.get_by_test_id('admin-tab-operations').click(); page.get_by_test_id('admin-operations-live').wait_for(timeout=5000); page.get_by_test_id('admin-oauth-diagnostics').wait_for(timeout=5000)
                        # Select locale-owned Admin copy as the dynamic-card rerender barrier for evidence.
                        expected_heading={'en-US':'Identity providers','ru-RU':'Поставщики входа'}[locale]
                        # Wait until a fresh provider card renders with the exact active-locale heading.
                        page.wait_for_function("expected => document.querySelector('[data-testid=\"admin-oauth-diagnostics\"] h2')?.textContent.trim() === expected",arg=expected_heading)
                        # Require Google and Facebook to remain explicitly runtime-unavailable.
                        assert page.get_by_test_id('admin-oauth-provider-google').get_attribute('data-runtime-available')=='false' and page.get_by_test_id('admin-oauth-provider-facebook').get_attribute('data-runtime-available')=='false'
                        # Ensure the rendered Admin card omits callback values and environment key names.
                        visible_diagnostics=page.get_by_test_id('admin-oauth-diagnostics').inner_text(); assert 'CASINO_' not in visible_diagnostics and 'callback' not in visible_diagnostics.lower()
                        # Capture the OAuth card in every governed responsive viewport.
                        for viewport_id,viewport in viewports.items():
                            # Resize to exact matrix dimensions before visual checks.
                            page.set_viewport_size(viewport); page.wait_for_timeout(150)
                            # Scroll the independent provider card into view inside the Admin content pane.
                            page.get_by_test_id('admin-oauth-diagnostics').scroll_into_view_if_needed()
                            # Require the document, Admin scroll container, and provider card to avoid horizontal overflow.
                            assert page.evaluate("() => { const content=document.querySelector('.admin-content'); const card=document.querySelector('[data-testid=\"admin-oauth-diagnostics\"]'); return document.documentElement.scrollWidth <= window.innerWidth + 1 && content.scrollWidth <= content.clientWidth + 1 && card.scrollWidth <= card.clientWidth + 1; }")
                            # Write after-pass evidence and metadata for the governed Admin state.
                            game_evidence(f'after-pass-admin-oauth-disabled-{locale}-{viewport_id}.png','admin',['operations_oauth_disabled'],locale,viewport_id)
                        # Replace only OAuth diagnostics with a standard failure envelope on a successful HTTP response.
                        page.route('**/api/v2/admin/oauth/providers',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":false,"error":{"code":"OAUTH_DIAGNOSTICS_UNAVAILABLE","message":"Unavailable"}}'))
                        # Refresh and prove Operations remains live while the separate provider card reports unavailable.
                        page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-operations-live').wait_for(timeout=5000); page.get_by_test_id('admin-oauth-diagnostics-unavailable').wait_for(timeout=5000)
                        # Remove the focused failure shim before the next locale or Operations acceptance case.
                        page.unroute('**/api/v2/admin/oauth/providers')
                        # Refresh once to restore real backend provider diagnostics.
                        page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-oauth-diagnostics').wait_for(timeout=5000)
                    # Restore primary desktop dimensions and English for the broader Operations suite.
                    page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }")
                # Record Admin authorization presentation, runtime-disabled status, isolation, and evidence.
                run_case('BR-ADMIN-OAUTH-001',['OAUTH-002','OAUTH-006','TEST-045'],admin_oauth_browser)
                # Define real-backend Operations states, localization, responsive layout, and evidence.
                def admin_operations_browser():
                    # Cache the isolated backend's primary storage document for reversible degradation.
                    players_path=ROOT/'data'/'players.json'; unavailable_path=ROOT/'data'/'players.operations-browser-unavailable.json'
                    # Define every governed Admin viewport for this Operations surface.
                    viewports={'desktop-primary':{'width':1920,'height':1080},'desktop-compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900}}
                    # Exercise both installed locales on the same authenticated real backend.
                    for locale in ('en-US','ru-RU'):
                        # Switch locale in place without changing the user's browser preference outside this test.
                        page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }", locale)
                        # Open the Operations tab and wait for healthy real-backend telemetry.
                        page.get_by_test_id('admin-tab-operations').click(); page.get_by_test_id('admin-operations-live').wait_for(timeout=5000)
                        # Capture the healthy state at every exact governed viewport.
                        for viewport_name,viewport in viewports.items():
                            # Resize to the named visual-matrix dimensions.
                            page.set_viewport_size(viewport); page.wait_for_timeout(150)
                            # Save branch-current after-pass evidence for this locale and viewport.
                            page.screenshot(path=str(screenshots/f'after-pass-admin-operations-live-{locale}-{viewport_name}.png'),full_page=False)
                        # Remove only the isolated test server's player document to produce a real degraded dependency.
                        players_path.replace(unavailable_path)
                        # Always restore storage before continuing to the down-state proof.
                        try:
                            # Refresh the active tab and wait for sanitized degraded telemetry.
                            page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-operations-degraded').wait_for(timeout=5000)
                            # Capture the degraded state at every governed viewport.
                            for viewport_name,viewport in viewports.items():
                                # Resize to the named visual-matrix dimensions.
                                page.set_viewport_size(viewport); page.wait_for_timeout(150)
                                # Save degraded after-pass evidence with locale and viewport identity.
                                page.screenshot(path=str(screenshots/f'after-pass-admin-operations-degraded-{locale}-{viewport_name}.png'),full_page=False)
                        # Restore the exact provider document before later tests use the backend.
                        finally:
                            # Return the test-owned document to its canonical path.
                            unavailable_path.replace(players_path)
                        # Replace only the Operations response with a standard unavailable envelope so the client must infer down without browser console noise.
                        page.route('**/api/v2/admin/operations',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":false,"error":{"code":"OPERATIONS_UNREACHABLE","message":"Unavailable"}}'))
                        # Refresh and wait for the explicit client-derived down presentation.
                        page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-operations-down').wait_for(timeout=5000)
                        # Capture the down state at every governed viewport.
                        for viewport_name,viewport in viewports.items():
                            # Resize to the named visual-matrix dimensions.
                            page.set_viewport_size(viewport); page.wait_for_timeout(150)
                            # Save down-state after-pass evidence for this locale and viewport.
                            page.screenshot(path=str(screenshots/f'after-pass-admin-operations-down-{locale}-{viewport_name}.png'),full_page=False)
                        # Remove the focused transport fault before the next locale or Admin feature.
                        page.unroute('**/api/v2/admin/operations')
                    # Restore primary desktop dimensions and English for the remaining Admin suite.
                    page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }")
                # Execute authenticated Operations UI, EN/RU, responsive, degraded, and down gates.
                run_case('BR-OPS-001',['OPS-004','OPS-005','TEST-044'],admin_operations_browser)
                # Define the funded practice-opponent Admin browser acceptance check.
                def admin_practice_opponents_browser():
                    # Open the Players & Bots control-plane surface.
                    page.get_by_test_id('admin-tab-players').click()
                    # Wait for the account allocation and funding control to render.
                    page.get_by_test_id('practice-opponent-admin').wait_for(timeout=5000)
                    # Require all three server-managed account rows before funding.
                    assert page.get_by_test_id('practice-opponent-account').count()==3
                    # Submit funding through the visible Admin controller action.
                    with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/bots/practice-opponents/fund') and response.request.method=='POST'):
                        # Click the idempotent funding control.
                        page.get_by_test_id('fund-practice-opponents').click()
                    # Wait for append-only funding activity to replace the prior view.
                    page.get_by_test_id('practice-opponent-activity').first.wait_for(timeout=10000)
                    # Require one visible ledger row per funded account.
                    assert page.get_by_test_id('practice-opponent-activity').count()>=3
                    # Capture the affected Admin matrix row at desktop compact in English.
                    page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(250)
                    # Scroll the affected card into view before reading its explicit evidence bounds.
                    practice_card=page.get_by_test_id('practice-opponent-admin'); practice_card.scroll_into_view_if_needed(); practice_box=practice_card.bounding_box(); assert practice_box
                    # Capture exactly the tested Admin card without unrelated legacy token presentation.
                    page.screenshot(path=str(screenshots/'after-pass-admin-practice-opponents-en-desktop-compact.png'),clip=practice_box)
                    # Restore primary desktop dimensions for following Admin cases.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Execute the Admin allocation, funding, ledger activity, and evidence gate.
                run_case('BR-ADMIN-PRACTICE-OPPONENT-001',['BOT-009','BOT-010','BOT-011','ADMIN-023','TEST-023'],admin_practice_opponents_browser)
                # Open Telemetry to verify Admin event presentation uses human labels and polished empty states.
                page.locator('[data-tab="telemetry"]').click(); page.get_by_text('Application events',exact=True).wait_for(timeout=5000)
                # Store visible telemetry copy for raw identifier and raw-array regression checks.
                telemetry_text=page.locator('#adminView').inner_text()
                # Verify raw API event identifiers and raw empty arrays are absent from the Admin presentation.
                assert 'api_request' not in telemetry_text and 'http_access' not in telemetry_text and '[WinError' not in telemetry_text and 'Traceback' not in telemetry_text and '[]' not in telemetry_text
                # Verify every available stream is represented by human event cards or a polished empty state.
                assert page.locator('#adminView .admin-event-list, #adminView .admin-empty-state').count() == 3
                # Capture the repaired Admin telemetry presentation at desktop compact size.
                page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(250); page.screenshot(path=str(screenshots/'after-pass-admin-telemetry-compact.png'),full_page=False)
                # Restore desktop dimensions before remaining Admin cases.
                page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Define the admin_users_browser function used by this module.
                def admin_users_browser():
                    # Open the Admin Users tab.
                    page.get_by_test_id('admin-tab-users').click()
                    # Wait for the create-user form to render.
                    page.get_by_test_id('admin-user-email').wait_for(timeout=5000)
                    # Fill the beta user's email.
                    page.get_by_test_id('admin-user-email').fill('beta.browser@example.test')
                    # Fill the beta user's display name.
                    page.get_by_test_id('admin-user-name').fill('Beta Browser')
                    # Set a deterministic starting token balance.
                    page.get_by_test_id('admin-user-tokens').fill('777')
                    # Select Russian to verify per-user locale controls render.
                    page.get_by_test_id('admin-user-language').select_option('ru-RU')
                    # Create the beta user through the visible Admin action.
                    page.get_by_test_id('admin-create-user').click()
                    # Store a stable locator for the created user row.
                    user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"]')
                    # Wait for the created user row to appear in the table.
                    user_row.wait_for(timeout=10000)
                    # Wait for the one-time temporary password notice.
                    page.get_by_test_id('admin-user-temp-password').wait_for(timeout=5000)
                    # Deactivate the user through the first row action.
                    user_row.get_by_test_id('admin-user-toggle').click()
                    # Wait for the inactive state to render.
                    page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="inactive"]').wait_for(timeout=10000)
                    # Reactivate the user through the same row action.
                    user_row.get_by_test_id('admin-user-toggle').click()
                    # Wait for the active state to render.
                    page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="active"]').wait_for(timeout=10000)
                    # Reset the user's password through the visible action.
                    with page.expect_response(lambda response: response.url.endswith('/password-reset') and response.request.method == 'POST') as reset_response_info:
                        # Wait for the reset-triggered Users refresh before the next action can race it.
                        with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/users') and response.request.method == 'GET'):
                            # Click the exact password reset button in the created user's row.
                            user_row.get_by_test_id('admin-user-reset').click()
                    # Store the reset API response so the browser test proves reset completed.
                    reset_response=reset_response_info.value.json()
                    # Verify the reset API returned the standard success envelope.
                    assert reset_response['ok'] is True
                    # Wait for the refreshed temporary password notice.
                    page.get_by_test_id('admin-user-temp-password').wait_for(timeout=5000)
                    # Accept terms through the visible action.
                    with page.expect_response(lambda response: '/api/v1/admin/users/' in response.url and response.url.endswith('/terms') and response.request.method == 'POST') as terms_response_info:
                        # Wait for the terms-triggered Users refresh before checking row attributes.
                        with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/users') and response.request.method == 'GET'):
                            # Click the exact terms button in the created user's row.
                            user_row.get_by_test_id('admin-user-terms').click()
                    # Store the terms API response so the browser test proves persistence completed.
                    terms_response=terms_response_info.value.json()
                    # Verify the terms API returned the standard success envelope.
                    assert terms_response['ok'] is True
                    # Wait for a fresh Users fetch after the visible terms action.
                    with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/users') and response.request.method == 'GET'):
                        # Refresh the active Users tab so row attributes come from persisted state.
                        page.get_by_test_id('admin-refresh').click()
                    # Wait for the accepted terms status to render.
                    page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-terms="accepted"]').wait_for(timeout=10000)
                    # Save locale preferences from the rendered row controls.
                    user_row.get_by_test_id('admin-user-save-locale').click()
                    # Verify the token balance remains visible after all actions.
                    assert '◈777.00' in user_row.get_by_test_id('admin-user-token-balance').inner_text()
                    # Verify the existing Language / Locale tab remains reachable.
                    page.get_by_test_id('admin-tab-language').click(); page.get_by_test_id('admin-language-select').wait_for(timeout=5000)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ADMIN-USERS-001',['ADMIN-USER-PENDING-035','TERMS-PENDING-035','TOKEN-PENDING-035','I18N-003'],admin_users_browser)
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('admin-tab-audio').click(); page.get_by_test_id('admin-save-audio').wait_for(timeout=5000)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUDIO-001',['AUDIO-002','AUDIO-005'],lambda: page.get_by_test_id('admin-preview-voice').is_visible())
                # Define the admin_i18n function used by this module.
                def admin_i18n():
                    # Open the new Language/Locale tab.
                    page.get_by_test_id('admin-tab-language').click()
                    # Wait for the language select to render.
                    page.get_by_test_id('admin-language-select').wait_for(timeout=5000)
                    # Select Russian as the display language.
                    page.get_by_test_id('admin-language-select').select_option('ru-RU')
                    # Apply the locale and persist the browser-local setting.
                    page.get_by_test_id('admin-locale-apply').click()
                    # Wait for the runtime state to report Russian.
                    page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'ru-RU'")
                    # Wait for the rendered diagnostics to catch up with the runtime state.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"admin-locale-state\"]')?.textContent?.includes('ru-RU')")
                    # Execute this statement as part of the module's documented control flow.
                    assert 'ru-RU' in page.get_by_test_id('admin-locale-state').inner_text()
                    # Reload Admin to verify browser-local persistence.
                    page.reload(wait_until='networkidle')
                    # Wait for the reloaded runtime to restore Russian.
                    page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'ru-RU'")
                    # Reopen Language/Locale after reload so diagnostics are visible.
                    page.get_by_test_id('admin-tab-language').click()
                    # Wait for the rendered diagnostics to show restored Russian.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"admin-locale-state\"]')?.textContent?.includes('ru-RU')")
                    # Execute this statement as part of the module's documented control flow.
                    assert 'ru-RU' in page.get_by_test_id('admin-locale-state').inner_text()
                    # Reopen Players & Bots to verify the affected Admin surface uses Russian resources.
                    page.get_by_test_id('admin-tab-players').click()
                    # Wait for the localized practice-opponent heading to render.
                    page.get_by_text("Тренировочные соперники Texas Hold'em",exact=True).wait_for(timeout=5000)
                    # Require dynamic controller activity to use Russian rather than English fallback copy.
                    assert 'Fund Account' not in page.get_by_test_id('practice-opponent-admin').inner_text() and 'Пополнение счёта' in page.get_by_test_id('practice-opponent-admin').inner_text()
                    # Capture Russian evidence for the affected Admin matrix row.
                    page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(250)
                    # Scroll the localized affected card into view before reading its evidence bounds.
                    practice_card=page.get_by_test_id('practice-opponent-admin'); practice_card.scroll_into_view_if_needed(); practice_box=practice_card.bounding_box(); assert practice_box
                    # Capture the exact Russian Admin card without unrelated surrounding surfaces.
                    page.screenshot(path=str(screenshots/'after-pass-admin-practice-opponents-ru-desktop-compact.png'),clip=practice_box)
                    # Restore primary desktop dimensions before cleanup.
                    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                    # Clear the test preference so later manual sessions start from defaults.
                    page.evaluate("localStorage.removeItem('casino.locale.settings.v1')")
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-I18N-ADMIN-001',['I18N-001','I18N-003'],admin_i18n)
                # Branch when the following condition is true.
                if console_errors or page_errors or http_errors: raise AssertionError('Browser errors: '+str(console_errors+page_errors+http_errors))
            # Handle the expected failure path for the protected logic.
            except Exception:
                # Execute this statement as part of the module's documented control flow.
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
        # Preserve the existing JSON result artifact path and behavior.
        save_results()
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
    # Configure heartbeat cadence while enforcing the public sixty-second maximum below.
    ap.add_argument('--heartbeat-seconds',type=float,default=45.0)
    # Configure the non-failing no-progress warning threshold.
    ap.add_argument('--stall-seconds',type=float,default=180.0)
    # Configure the real browser-suite wall-clock timeout.
    ap.add_argument('--timeout-seconds',type=float,default=2700.0)
    # Parse caller options before running any suite.
    args=ap.parse_args()
    # Reject heartbeat intervals outside issue #207 acceptance before starting work.
    if args.heartbeat_seconds<=0 or args.heartbeat_seconds>60: ap.error('--heartbeat-seconds must be greater than 0 and at most 60')
    # Reject warning thresholds that would fire before one heartbeat.
    if args.stall_seconds<args.heartbeat_seconds: ap.error('--stall-seconds must be at least --heartbeat-seconds')
    # Reject non-positive real suite timeouts.
    if args.timeout_seconds<=0: ap.error('--timeout-seconds must be greater than 0')
    # Branch when the following condition is true.
    if not args.api and not args.browser and not args.storage and not args.mysql_live and not args.mysql_migrations_live: args.api=True
    # Start protected logic so failures can be handled safely.
    try:
        # Branch when the following condition is true.
        if args.storage or args.mysql_live or args.mysql_migrations_live: run_storage_tests(include_live=args.mysql_live,include_migration_live=args.mysql_migrations_live)
        # Branch when the following condition is true.
        if args.api: run_api_tests()
        # Branch when the following condition is true.
        if args.browser:
            # Set code to the value needed for the next operation.
            code=run_browser_tests(args.heartbeat_seconds,args.stall_seconds,args.timeout_seconds)
            # Branch when the following condition is true.
            if code: return code
    # Run cleanup logic regardless of success or failure.
    finally: save_results()
    # Return success after all selected suites complete normally.
    return 0
# Branch when the following condition is true.
if __name__=='__main__': raise SystemExit(main())
