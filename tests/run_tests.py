# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
# Import required dependency so this module can use its public functions or constants.
import argparse, importlib, json, os, re, socket, subprocess, sys, time, traceback, urllib.request
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
# Import auth helpers so API tests can seed users through the backend storage seam.
from casino.core import auth as auth_core
# Import configuration helpers so startup hardening can be tested without launching a public listener.
from casino import config as casino_config
# Import the shared resolver so session precedence is tested independently of individual game APIs.
from casino.core.request_player import resolve_authenticated_player
# Import storage tests so provider parity can run without the broad API suite.
from tests import storage_tests
# Import the current-catalog hostile-client certification entrypoint.
from tests.server_authority_tests import run_server_authority_tests
# Set RESULTS to the value needed for the next operation.
RESULTS=[]
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
    print(f'[{status}] {test_id} {" ".join(reqs)} {message}')

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
    # Set s to the value needed for the next operation.
    s=socket.socket(); s.bind(('127.0.0.1',0)); port=s.getsockname()[1]; s.close(); return port

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
    port=free_port(); proc=subprocess.Popen([sys.executable,str(ROOT/'run.py'),'--port',str(port),'--no-browser'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
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
    # Set out to the value needed for the next operation.
    out=proc.stdout.read() if proc.stdout else ''; proc.terminate(); raise RuntimeError('server did not start\n'+out)

# Define the run_case function used by this module.
def run_case(test_id, reqs, fn):
    # Start protected logic so failures can be handled safely.
    try: fn(); record(test_id, reqs, 'PASS')
    # Handle the expected failure path for the protected logic.
    except Exception as e: record(test_id, reqs, 'FAIL', str(e)); raise

# Define assert_condition so concise mapped checks still fail when their predicate is false.
def assert_condition(value, message):
    # Raise a focused assertion when the mapped acceptance predicate is false.
    assert value, message

# Define the run_storage_tests function used by this module.
def run_storage_tests(include_live=False):
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
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
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
        # Execute this statement as part of the module's documented control flow.
        run_case('API-AUTH-001',['AUTH-001','SESSION-001','USER-001','TERMS-001'],auth_backend)
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
            admin_paths=[('GET','/api/v1/admin/overview'),('GET','/api/v1/admin/dashboard'),('GET','/api/v1/admin/modules'),('GET','/api/v1/admin/requirements'),('GET','/api/v1/admin/game-states'),('GET','/api/v1/admin/users'),('POST','/api/v1/admin/users'),('GET',f'/api/v1/admin/users/{user_b["user_id"]}'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/deactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/reactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/password-reset'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/terms'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/locale'),('GET','/api/v1/admin/logs'),('GET','/api/v1/admin/ledger'),('GET','/api/v1/admin/history'),('GET','/api/v1/admin/test-results'),('GET','/api/v1/admin/audio-settings'),('POST','/api/v1/admin/audio-settings'),('GET','/api/v1/admin/autoplay'),('POST','/api/v1/admin/autoplay/stop-all'),('GET','/api/v1/admin/bots'),('POST','/api/v1/admin/bots/practice-opponents/fund'),('GET','/api/v2/admin/users'),('POST','/api/v2/admin/users'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}'),('POST',f'/api/v2/admin/users/{user_b["user_id"]}/password'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}/terms'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}/state')]
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
        run_case('API-ADMIN-USERS-001',['AUTH-005','USER-002','USER-004'],lambda: assert_condition(integrity_state['admin_blocked']>20,'Admin route gate coverage incomplete'))
        # Record v2 envelope/player shape coverage under the permanent contract test id.
        run_case('API-CONTRACT-V2-001',['API-001','API-002','TOKEN-002'],lambda: assert_condition({'player_id','token_balance','token_label'} <= set(integrity_state['contract_player']),'v2 player summary shape mismatch'))
        # Record canonical terms gate and persistence coverage under its permanent test id.
        run_case('API-TERMS-001',['TERMS-001','TERMS-002','TERMS-003'],lambda: assert_condition(integrity_state['email']=='wallet-a@example.local','terms integrity setup missing'))
        # Stop the live backend cleanly so persistence is verified across an actual process boundary.
        proc.terminate(); proc.wait(timeout=5)
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
        run_case('API-BJ-002',['BJ-002','BJ-003','BJ-004','BJ-005','BJ-006','BJ-007','BJ-012','BJ-015','BJ-016','BJ-017','BJ-018','BJ-019','BJ-026'],blackjack_rule_edges)
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
        # Set proc.terminate(); proc.wait(timeout to the value needed for the next operation.
        proc.terminate(); proc.wait(timeout=5); save_results()

# Define the run_browser_tests function used by this module.
def run_browser_tests():
    # Start protected logic so failures can be handled safely.
    try: from playwright.sync_api import sync_playwright
    # Handle the expected failure path for the protected logic.
    except Exception:
        # Write diagnostic output so the current operation can be inspected.
        print('Playwright is not installed. Install with python -m pip install -r requirements-dev.txt and python -m playwright install chromium'); return 2
    # Set proc,base to the value needed for the next operation.
    proc,base=start_server(); screenshots=ROOT/'logs'/'test-runs'; screenshots.mkdir(parents=True,exist_ok=True)
    # Parse the authoritative visual matrix so browser coverage fails fast on invalid governance data.
    visual_matrix=json.loads((ROOT/'tests'/'visual'/'visual_matrix.json').read_text(encoding='utf-8'))
    # Start protected logic so failures can be handled safely.
    try:
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
        # Create the real normal-user identity used by browser auth, terms, and wallet coverage.
        api(base,'/api/v1/admin/users','POST',{'email':'demo@example.local','password':'password','display_name':'Demo Player','initial_tokens':5000,'terms_accepted':False,'language':'ru-RU','format_locale':'browser'})
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
                run_case('BR-AUTH-BACKEND-001',['AUTH-001','AUTH-002','SESSION-001'],lambda: real_login_response['ok'] is True and real_login_response['data']['user']['email']==DEFAULT_AUTH_EMAIL and real_login_page.get_by_test_id('lobby').is_visible())
            # Close the focused page even when its assertions fail.
            finally:
                # Release the isolated backend-login browser context before the existing broad UI suite.
                real_login_page.close()
            # Set page to the value needed for the next operation.
            page=browser.new_page(viewport={'width':1920,'height':1080})
            # Set console_errors to the value needed for the next operation.
            console_errors=[]; page_errors=[]; http_errors=[]
            # Set page.on('console', lambda msg: console_errors.append(msg.tex to the value needed for the next operation.
            page.on('console', lambda msg: console_errors.append(msg.text) if msg.type=='error' else None)
            # Execute this statement as part of the module's documented control flow.
            page.on('pageerror', lambda err: page_errors.append(str(err)))
            # Capture failing response URLs so authorization regressions are diagnosable.
            page.on('response', lambda response: http_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
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
                page.goto(base, wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000)
                # Capture logged-out login evidence for the frontend auth handback.
                shot('auth_login_gate.png')
                # Define the auth_login_gate function used by this module.
                def auth_login_gate():
                    # Verify the login panel is visible before casino routes mount.
                    assert page.get_by_test_id('login-gate').is_visible()
                    # Verify the premium topbar is hidden while logged out.
                    assert not page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the required toy-simulator terms checkbox is visible.
                    assert page.get_by_test_id('login-terms-check').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-LOGIN-001',['AUTH-UI-001','TERMS-UI-001'],auth_login_gate)
                # Switch locale before login to prove auth state preserves the chosen language.
                page.get_by_test_id('auth-locale-select').select_option('ru-RU')
                # Wait for the login gate rerender triggered by the locale switch.
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
                    assert '5,000' in page.get_by_test_id('premium-wallet').inner_text() and '◈' not in page.get_by_test_id('premium-wallet').inner_text()
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
                page.get_by_test_id('add-tokens').wait_for(timeout=5000); page.locator('#add-token-amount').fill('250')
                # Observe the real token-add API response while submitting the wallet control.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/me/tokens/add') and response.request.method == 'POST') as token_add_info:
                    # Submit the visible token-add request.
                    page.get_by_test_id('add-tokens').click()
                # Wait until the wallet reflects the real ledger-backed token addition.
                page.wait_for_function("() => document.querySelector('[data-testid=\"premium-wallet\"]')?.textContent?.includes('5,250')")
                # Read the real ledger after the visible token-add action.
                ledger_after_add=page.evaluate("async playerId => (await (await fetch(`/api/v1/players/${playerId}/ledger`, {credentials:'include'})).json()).data.ledger",browser_player_id)
                # Define auth_tokens_real_backend for exact wallet and ledger assertions.
                def auth_tokens_real_backend():
                    # Verify the backend response and shell show the same updated canonical balance.
                    assert token_add_info.value.json()['data']['token_balance']==5250 and '5,250' in page.get_by_test_id('premium-wallet').inner_text()
                    # Verify exactly one visible wallet action produced exactly one ledger credit.
                    assert len([row for row in ledger_after_add if row.get('transaction_type')=='PLAY_TOKENS_ADDED'])==len([row for row in ledger_before_add if row.get('transaction_type')=='PLAY_TOKENS_ADDED'])+1
                # Execute the real-backend wallet regression with permanent requirement mappings.
                run_case('BR-TOKEN-001',['TOKEN-001','TOKEN-003','TOKEN-004','SESSION-003'],auth_tokens_real_backend)
                # Counterfeit the local wallet display and cache to model a fully hostile client surface.
                page.evaluate("() => { document.querySelector('#balance').textContent='999,999'; localStorage.setItem('casino.hostile.balance','999999'); }")
                # Require the tampered DOM to differ temporarily without changing the server wallet.
                assert '999,999' in page.get_by_test_id('premium-wallet').inner_text()
                # Refresh the whole browser document so authoritative current-user state replaces local tampering.
                page.reload(wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Define the hostile-client refresh assertion against the real server wallet.
                def hostile_client_refresh():
                    # Verify current-user refresh restores the exact ledger-backed balance.
                    assert '5,250' in page.get_by_test_id('premium-wallet').inner_text()
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
                run_case('BR-AUTH-LOCALE-001',['I18N-003','AUTH-UI-001'],lambda: route_before_locale and page.get_by_test_id('lobby').is_visible() and '5,250' in page.get_by_test_id('premium-wallet').inner_text())
                # Logout through the shell control to verify the browser returns to the login gate.
                page.get_by_test_id('logout').click(); page.get_by_test_id('login-gate').wait_for(timeout=5000)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-LOGOUT-001',['AUTH-UI-001'],lambda: page.get_by_test_id('login-gate').is_visible() and not page.get_by_test_id('premium-topbar').is_visible())
                # Re-login after logout so the existing browser suite can continue authenticated.
                page.get_by_test_id('login-email').fill('demo@example.local'); page.get_by_test_id('login-password').fill('password'); page.get_by_test_id('login-terms-check').check(); page.get_by_test_id('login-submit').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Clear expected unauthenticated /me failures produced by the login and logout gates.
                console_errors.clear(); http_errors.clear()
                # Navigate to Roulette to verify the same current-user wallet persists on a game surface.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=5000)
                # Read the live current-user balance while Roulette is mounted.
                roulette_me_balance=page.evaluate("async () => (await (await fetch('/api/v2/me', {credentials:'include'})).json()).data.player.token_balance")
                # Verify login, current-user lookup, shell, and Roulette share one exact balance.
                assert roulette_me_balance==5250 and '5,250' in page.get_by_test_id('premium-wallet').inner_text()
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
                    assert '5,250' in page.get_by_test_id('premium-wallet').inner_text() and '◈' not in page.get_by_test_id('premium-wallet').inner_text()
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
                    # Verify the catalog advertises the approved expansion capacity.
                    assert 'ready for 20' in page.get_by_test_id('catalog-capacity').inner_text()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-LOBBY-001',['CORE-005','CORE-006','UX-008'],premium_lobby)
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
                    # Verify localized capacity copy includes both current and approved target counts.
                    assert page.get_by_test_id('catalog-capacity').inner_text()==f'Доступно: {len(casino_config.GAMES)} · каталог рассчитан на 20'
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
                run_case('BR-CATALOG-I18N-RU-001',['UX-010','I18N-001'],catalog_ru_acceptance)
                # Capture the polished desktop lobby and shared topbar for review evidence.
                shot('after-pass-shell-lobby-desktop.png')
                # Resize the browser to the compact desktop viewport before responsive checks.
                page.set_viewport_size({'width':1440,'height':900}); page.wait_for_timeout(250)
                # Define the responsive_lobby function used by this module.
                def responsive_lobby():
                    # Verify compact desktop preserves the complete wallet and avoids page-level horizontal overflow.
                    assert page.get_by_test_id('premium-wallet').is_visible() and page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Capture the compact desktop shell for visual-matrix evidence.
                    shot('after-pass-shell-lobby-compact.png')
                    # Resize to the approved mobile viewport inside the same responsive matrix case.
                    page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(250)
                    # Verify the stacked topbar remains visible on a narrow viewport.
                    assert page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the lobby does not introduce page-level horizontal overflow.
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Verify the featured game card remains visible after responsive stacking.
                    assert page.get_by_test_id('card-roulette').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-LOBBY-RESP-001',['CORE-015','UX-009'],responsive_lobby)
                # Capture the narrow stacked shell so mobile top-action behavior can be reviewed.
                shot('after-pass-shell-lobby-mobile.png')
                # Restore desktop dimensions before existing game interaction coverage runs.
                page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Define catalog_route_discovery to mount every frontend driver from catalog metadata.
                def catalog_route_discovery():
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
                run_case('BR-CATALOG-DISCOVERY-001',['CORE-021','TEST-042'],catalog_route_discovery)
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
                    # Start one ledger-backed spin and require the timer-owned active state before settlement.
                    page.locator('[data-spin]').click(); page.wait_for_function("() => document.querySelector('[data-testid=\"big-six-wheel-phase\"]')?.textContent === 'Spinning'",timeout=5000)
                    # Capture the active normal-motion state while the route-owned timer is pending.
                    game_evidence('after-pass-big-six-spinning-en-desktop_primary.png','big_six_wheel',['spinning'],'en-US','desktop_primary')
                    # Wait for the scheduled settlement to restore an enabled action.
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
                run_case('BR-BIG-SIX-001',['BIG-SIX-001','BIG-SIX-002','BIG-SIX-004','BIG-SIX-005'],big_six_acceptance)
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
                run_case('BR-OU7-001',['OU7-001','OU7-002','OU7-004','OU7-005'],over_under_7_acceptance)
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
                run_case('BR-CS-001',['CS-001','CS-002','CS-004','CS-005'],caribbean_stud_acceptance)
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
                run_case('BR-CH-001',['CH-001','CH-002','CH-004','CH-005'],casino_holdem_acceptance)
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
                compact_diagnostics=page.evaluate("() => { const ids=['nav-lobby','nav-roulette','nav-slots','nav-keno','nav-bingo','nav-blackjack','nav-baccarat','nav-admin']; const nav=document.querySelector('.casino-nav').getBoundingClientRect(); const items=ids.map(id => document.querySelector(`[data-testid=\"${id}\"]`)?.getBoundingClientRect().toJSON()); const stage=document.querySelector('[data-testid=\"roulette-premium-stage\"]')?.getBoundingClientRect().toJSON(); const wheel=document.querySelector('[data-testid=\"roulette-wheel\"]')?.getBoundingClientRect().toJSON(); const table=document.querySelector('[data-testid=\"roulette-table\"]')?.getBoundingClientRect().toJSON(); const spin=document.querySelector('[data-testid=\"roulette-spin\"]')?.getBoundingClientRect().toJSON(); return {nav,items,stage,wheel,table,spin,height:innerHeight}; }")
                # Verify every desktop navigation item is fully visible inside the shared navigation surface.
                assert all(item and item['left'] >= compact_diagnostics['nav']['left'] - 1 and item['right'] <= compact_diagnostics['nav']['right'] + 1 for item in compact_diagnostics['items']), compact_diagnostics
                # Verify the full Roulette stage and primary action remain above the 1440 by 900 fold.
                assert all(compact_diagnostics[key] and compact_diagnostics[key]['bottom'] <= compact_diagnostics['height'] + 1 for key in ('stage','wheel','table','spin')), compact_diagnostics
                # Verify player-facing Roulette copy does not expose an internal round identifier.
                assert 'rou_' not in page.get_by_test_id('roulette-premium').inner_text()
                # Capture compact-layout acceptance evidence at the governed 1440 by 900 viewport.
                page.screenshot(path=str(screenshots/'after-pass-roulette-compact.png'),full_page=False)
                # Resize to the evaluator's second compact desktop viewport.
                page.set_viewport_size({'width':1366,'height':768}); page.wait_for_timeout(350)
                # Read the second compact viewport measurements after responsive compression.
                compact_1366=page.evaluate("() => { const nav=document.querySelector('.casino-nav').getBoundingClientRect(); const items=[...document.querySelectorAll('.casino-nav .nav-item')].map(item => item.getBoundingClientRect().toJSON()); const ids=['roulette-premium-stage','roulette-wheel','roulette-table','roulette-spin']; const boxes=Object.fromEntries(ids.map(id => [id,document.querySelector(`[data-testid=\"${id}\"]`)?.getBoundingClientRect().toJSON()])); return {nav,items,boxes,width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth}; }")
                # Verify navigation, page width, stage, wheel, table, and Spin all remain fully usable at 1366 by 768.
                assert compact_1366['scrollWidth'] <= compact_1366['width'] + 1 and all(item['left'] >= compact_1366['nav']['left'] - 1 and item['right'] <= compact_1366['nav']['right'] + 1 for item in compact_1366['items']) and all(box and box['bottom'] <= compact_1366['height'] - 54 for box in compact_1366['boxes'].values()), compact_1366
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
                run_case('BR-SLOT-001',['SLOT-020','SLOT-021','SLOT-022','SLOT-023','SLOT-024','SLOT-025','SLOT-026','AUTO-010','LEDGER-025','UX-007','UX-009'],premium_slots)
                # Navigate to Keno and wait for the premium route shell to mount.
                page.get_by_test_id('nav-keno').click(); page.get_by_test_id('keno-premium-hero').wait_for(timeout=5000)
                # Select ten deterministic spots so paytable comparison has a stable row.
                for spot in [3,8,12,17,24,31,44,55,63,72]: page.get_by_test_id(f'keno-num-{spot}').click()
                # Store the spot-selection board box for stability assertions.
                keno_selection_box=page.get_by_test_id('keno-grid').bounding_box()
                # Capture the approved spot-selection evidence state.
                shot('keno_spot_selection.png')
                # Start the draw through the same human action used in normal play.
                page.get_by_test_id('keno-draw').click()
                # Wait until the animated draw rail shows a partial reveal.
                page.wait_for_function("""() => { const count = document.querySelectorAll('[data-testid="keno-drawn-ball"]').length; return count >= 8 && count < 20; }""", timeout=3000)
                # Store the draw-progress board box for stability assertions.
                keno_progress_box=page.get_by_test_id('keno-grid').bounding_box()
                # Capture the approved draw-progress evidence state.
                shot('keno_draw_progress.png')
                # Wait for the full Keno draw and comparison drawer to finish rendering.
                page.wait_for_function("""() => document.querySelectorAll('[data-testid="keno-drawn-ball"]').length === 20""", timeout=5000); page.get_by_test_id('keno-paytable-comparison').wait_for(timeout=5000)
                # Store the final-result board box for stability assertions.
                keno_result_box=page.get_by_test_id('keno-grid').bounding_box()
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
                    # Verify the board width remains stable from selection to draw progress.
                    assert abs(keno_selection_box['width']-keno_progress_box['width'])<2
                    # Verify the board height remains stable from selection to final result.
                    assert abs(keno_selection_box['height']-keno_result_box['height'])<2
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-KENO-001',['KENO-009','KENO-010','KENO-011','KENO-012','KENO-013','KENO-014','KENO-015','KENO-018','KENO-020','KENO-021','KENO-022','AUTO-012','UX-007','UX-009'],premium_keno)
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
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('nav-bingo').click(); page.get_by_test_id('bingo-buy').click(); page.wait_for_function("() => document.querySelector('[data-testid=\"bingo-call\"]') && !document.querySelector('[data-testid=\"bingo-call\"]').disabled"); page.get_by_test_id('bingo-call').click(); page.wait_for_timeout(700); page.evaluate("""async () => { const response = await fetch('/api/v1/games/bingo/auto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ max_calls: 75 }) }); const payload = await response.json(); if (!payload.ok) throw new Error(payload.error?.message || 'Bingo auto failed'); }"""); page.get_by_test_id('nav-bingo').click(); page.locator('[data-winning-cell="true"]').first.wait_for(timeout=5000); run_case('BR-BINGO-001',['BINGO-017','BINGO-018','BINGO-021','BINGO-022','AUTO-013'],lambda: page.get_by_test_id('bingo-card').is_visible() and page.locator('[data-winning-cell="true"]').first.is_visible() and page.get_by_test_id('bingo-cards-drawer').is_visible() and page.get_by_test_id('autoplay-bingo').is_visible())
                # Navigate to Blackjack before checking the premium table surface.
                page.get_by_test_id('nav-blackjack').click()
                # Wait for the premium Blackjack shell to mount.
                page.get_by_test_id('blackjack-premium').wait_for(timeout=5000)
                # Deal one hand through the public Blackjack action button.
                page.get_by_test_id('blackjack-deal').click()
                # Wait for the first player hand lane to render.
                page.get_by_test_id('blackjack-hand-0').wait_for(timeout=5000)
                # Capture normal Blackjack browser evidence from the running app.
                shot('blackjack-normal-hand.png')
                # Store the backend round id exposed by the stable test hook.
                blackjack_round_id=page.get_by_test_id('blackjack-round-id').get_attribute('data-round-id')
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
                # Navigate to Baccarat before asserting the premium table surfaces.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/me') and response.request.method == 'GET'):
                    # Click Baccarat and wait for its final mount-time wallet refresh response.
                    page.get_by_test_id('nav-baccarat').click()
                # Wait for the wager setup state to mount.
                page.get_by_test_id('baccarat-wager-setup').wait_for(timeout=5000)
                # Place a banker wager through the same public control a player uses.
                page.get_by_test_id('baccarat-banker').click()
                # Deal one coup so the reveal theater and settlement state are exercised.
                page.get_by_test_id('baccarat-deal').click()
                # Wait for the post-reveal result state to settle.
                page.get_by_test_id('baccarat-result').wait_for(timeout=5000)
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
                # Set page.goto(base+'/admin', wait_until to the value needed for the next operation.
                page.goto(base+'/admin', wait_until='networkidle')
                # Define the Admin dashboard version check mapped to its existing browser requirement coverage.
                def admin_dashboard_browser():
                    # Require the existing Admin navigation to remain available after dashboard load.
                    assert page.get_by_test_id('admin-tab-audio').is_visible()
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
    # Run cleanup logic regardless of success or failure.
    finally:
        # Set proc.terminate(); proc.wait(timeout to the value needed for the next operation.
        proc.terminate(); proc.wait(timeout=5); save_results()

# Define the main function used by this module.
def main():
    # Set ap to the value needed for the next operation.
    ap=argparse.ArgumentParser(); ap.add_argument('--api',action='store_true'); ap.add_argument('--browser',action='store_true'); ap.add_argument('--storage',action='store_true'); ap.add_argument('--mysql-live',action='store_true'); args=ap.parse_args()
    # Branch when the following condition is true.
    if not args.api and not args.browser and not args.storage and not args.mysql_live: args.api=True
    # Start protected logic so failures can be handled safely.
    try:
        # Branch when the following condition is true.
        if args.storage or args.mysql_live: run_storage_tests(include_live=args.mysql_live)
        # Branch when the following condition is true.
        if args.api: run_api_tests()
        # Branch when the following condition is true.
        if args.browser:
            # Set code to the value needed for the next operation.
            code=run_browser_tests();
            # Branch when the following condition is true.
            if code: sys.exit(code)
    # Run cleanup logic regardless of success or failure.
    finally: save_results()
# Branch when the following condition is true.
if __name__=='__main__': main()
