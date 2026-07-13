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
    # Execute the MySQL schema and atomic ledger-provider path test without requiring a live service.
    run_case('STORAGE-MYSQL-001',['CORE-017','LEDGER-001','LEDGER-007','LEDGER-009'],storage_tests.run_mysql_schema_provider_path)
    # Execute the real-service persistence and concurrent-ledger gate only when explicitly requested.
    if include_live:
        # Map the live integration case to the durable storage and MySQL requirements.
        run_case('STORAGE-MYSQL-LIVE-001',['STORAGE-001','STORAGE-002','STORAGE-003','STORAGE-004','MYSQL-001','MYSQL-002','MYSQL-003','MYSQL-004','TEST-038'],storage_tests.run_mysql_live_provider_path)

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
            # Complete Roulette for user A through the bound session action.
            roulette_a=api(base,'/api/v1/games/roulette/spin','POST',{'player_id':user_b['player_id'],'force_result':'17'},auth_token=token_a)
            # Place user B's own forced-winning Roulette wager while submitting user A's id.
            roulette_b_bet=api(base,'/api/v1/games/roulette/bets','POST',{'player_id':user_a['player_id'],'amount':10,'bet_type':'straight','covered_numbers':['18'],'label':'18'},auth_token=token_b)['bet']
            # Settle user B's Roulette wager through its authenticated session.
            roulette_b=api(base,'/api/v1/games/roulette/spin','POST',{'player_id':user_a['player_id'],'force_result':'18'},auth_token=token_b)
            # Verify both Roulette actions used session-derived identities and produced payouts.
            assert str(roulette_a['round']['result'])=='17' and roulette_b_bet['player_id']==user_b['player_id'] and str(roulette_b['round']['result'])=='18' and any(row['settlement']['credit']>0 for row in roulette_a['settlements'] if row['bet']['player_id']==user_a['player_id']) and any(row['settlement']['credit']>0 for row in roulette_b['settlements'] if row['bet']['player_id']==user_b['player_id'])
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
            # Read private game history through each normal-user session.
            history_a=api(base,'/api/v1/casino/history',auth_token=token_a)['history']
            # Read user B's independent history view.
            history_b=api(base,'/api/v1/casino/history',auth_token=token_b)['history']
            # Verify history never exposes the other authenticated player's records.
            assert history_a and history_b and all(row['player_id']==user_a['player_id'] for row in history_a) and all(row['player_id']==user_b['player_id'] for row in history_b)
            # Refresh both canonical wallets after all six games have settled.
            wallet_a=api(base,'/api/v2/me',auth_token=token_a)['player']['token_balance']
            # Refresh user B's canonical wallet independently.
            wallet_b=api(base,'/api/v2/me',auth_token=token_b)['player']['token_balance']
            # Verify final ledger balances agree with the canonical wallet refresh for each user.
            ledger_a=api(base,f'/api/v1/players/{user_a["player_id"]}/ledger',auth_token=token_a)['ledger']; ledger_b=api(base,f'/api/v1/players/{user_b["player_id"]}/ledger',auth_token=token_b)['ledger']; assert ledger_a[-1]['balance_after']==wallet_a and ledger_b[-1]['balance_after']==wallet_b
            # Log out both real sessions after the six-game integration path.
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
            admin_paths=[('GET','/api/v1/admin/overview'),('GET','/api/v1/admin/dashboard'),('GET','/api/v1/admin/modules'),('GET','/api/v1/admin/requirements'),('GET','/api/v1/admin/game-states'),('GET','/api/v1/admin/users'),('POST','/api/v1/admin/users'),('GET',f'/api/v1/admin/users/{user_b["user_id"]}'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/deactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/reactivate'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/password-reset'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/terms'),('POST',f'/api/v1/admin/users/{user_b["user_id"]}/locale'),('GET','/api/v1/admin/logs'),('GET','/api/v1/admin/ledger'),('GET','/api/v1/admin/history'),('GET','/api/v1/admin/test-results'),('GET','/api/v1/admin/audio-settings'),('POST','/api/v1/admin/audio-settings'),('GET','/api/v1/admin/autoplay'),('POST','/api/v1/admin/autoplay/stop-all'),('GET','/api/v1/admin/bots'),('GET','/api/v2/admin/users'),('POST','/api/v2/admin/users'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}'),('POST',f'/api/v2/admin/users/{user_b["user_id"]}/password'),('PATCH',f'/api/v2/admin/users/{user_b["user_id"]}/terms'),('GET',f'/api/v2/admin/users/{user_b["user_id"]}/state')]
            # Request each Admin endpoint as a normal user and require a forbidden response.
            for method,path in admin_paths:
                # Send an empty body for mutating routes because authorization must run before validation.
                blocked=api(base,path,method,{} if method in ('POST','PATCH') else None,ok=False,auth_token=token_a); assert blocked['error']['code']=='FORBIDDEN', (method,path,blocked)
            # Verify normal users also cannot invoke shared reset or global logs.
            assert api(base,'/api/v1/casino/reset','POST',{},ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN' and api(base,'/api/v1/casino/logs/recent',ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN'
            # Verify normal users cannot mutate shared bot-controller accounts.
            assert api(base,'/api/v1/bots/bot_roulette_1/enable','POST',{},ok=False,auth_token=token_a)['error']['code']=='FORBIDDEN'
            # Store the durable post-game balance and terms state for restart verification.
            integrity_state.update({'email':'wallet-a@example.local','password':'wallet-a-password','balance':api(base,'/api/v2/me',auth_token=token_a)['player']['token_balance'],'admin_blocked':len(admin_paths),'token_credit_count':len(credits_after)-len(credits_before),'contract_player':added_a,'users':[{'email':'wallet-a@example.local','password':'wallet-a-password','player_id':user_a['player_id'],'balance':wallet_a,'roulette_round':roulette_a['round']['round_id'],'slots_round':slot_a['round_id'],'blackjack_round':blackjack_a['round_id'],'baccarat_round':baccarat_a['coup']['round_id'],'keno_round':keno_a['draw']['round_id'],'bingo_session':bingo_a_session['session_id'],'bingo_completed':False},{'email':'wallet-b@example.local','password':'wallet-b-password','player_id':user_b['player_id'],'balance':wallet_b,'roulette_round':roulette_b['round']['round_id'],'slots_round':slot_b['round_id'],'blackjack_round':blackjack_b['round_id'],'baccarat_round':baccarat_b['coup']['round_id'],'keno_round':keno_b['draw']['round_id'],'bingo_session':bingo_b['session']['session_id'],'bingo_completed':True}],'six_game_history_counts':[len(history_a),len(history_b)]})
        # Execute the real-backend integrity regression as one mapped API case.
        run_case('API-PRIVATE-SESSION-001',['SESSION-003','USER-001','USER-003','USER-005','TOKEN-004','TEST-039'],wallet_auth_integrity)
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
                roulette_state=api(base,'/api/v1/games/roulette/state',auth_token=token)['state']; slots_state=api(base,'/api/v1/games/slots/state',auth_token=token)['state']; blackjack_state=api(base,'/api/v1/games/blackjack/state',auth_token=token)['state']; baccarat_state=api(base,'/api/v1/games/baccarat/state',auth_token=token)['state']; keno_state=api(base,'/api/v1/games/keno/state',auth_token=token)['state']; bingo_state=api(base,'/api/v1/games/bingo/state',auth_token=token)['state']
                # Verify Roulette, Slots, Blackjack, Baccarat, and Keno identifiers survived under the session-derived player.
                assert any(row['round_id']==expected['roulette_round'] for row in roulette_state['last_results']) and slots_state['last_spins'][-1]['round_id']==expected['slots_round'] and expected['blackjack_round'] in blackjack_state['rounds'] and any(row['round_id']==expected['baccarat_round'] for row in baccarat_state['last_coups']) and any(row['round_id']==expected['keno_round'] for row in keno_state['last_draws'])
                # Verify Bingo terminal/refund state survived for the corresponding user.
                assert (any(row['session_id']==expected['bingo_session'] for row in bingo_state['last_sessions']) if expected['bingo_completed'] else bingo_state['active_session'] is None)
                # Read restarted private history and ledger views.
                restarted_history=api(base,'/api/v1/casino/history',auth_token=token)['history']; restarted_ledger=api(base,f'/api/v1/players/{expected["player_id"]}/ledger',auth_token=token)['ledger']
                # Verify restarted history includes the user's Bingo settlement and never leaks another player.
                assert any(row['round_id']==expected['bingo_session'] for row in restarted_history) and all(row['player_id']==expected['player_id'] for row in restarted_history) and all(row['player_id']==expected['player_id'] for row in restarted_ledger)
            # Verify both users produced persisted private history across the six-game gate.
            assert all(count>0 for count in integrity_state['six_game_history_counts'])
        # Record the live restart persistence regression under the same integrity requirements.
        run_case('API-WALLET-RESTART-001',['SESSION-003','USER-001','TOKEN-003','TOKEN-004','TEST-039'],wallet_restart_persistence)
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
            bots=api(base,'/api/v1/bots'); assert bots['bots']; assert bots['capabilities']['roulette']['supports_bots']
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
        run_case('API-CONTROL-001',['BOT-001','BOT-003','AUDIO-001','AUDIO-002','AUTO-001','AUTO-003'],bots_audio_autoplay)
        # Define the roulette function used by this module.
        def roulette():
            # Set p0 to the value needed for the next operation.
            p0=api(base,'/api/v1/players/human')['player']['balance']
            # Set r to the value needed for the next operation.
            r=api(base,'/api/v1/games/roulette/bets','POST',{'player_id':'human','amount':25,'bet_type':'split','covered_numbers':['17','20']}); assert r['bet']['type']=='split'
            # Set p1 to the value needed for the next operation.
            p1=api(base,'/api/v1/players/human')['player']['balance']; assert round(p0-p1,2)==25
            # Set api(base,'/api/v1/games/roulette/spin','POST',{'force_result to the value needed for the next operation.
            api(base,'/api/v1/games/roulette/spin','POST',{'force_result':'17'}); p2=api(base,'/api/v1/players/human')['player']['balance']; assert p2>p1
            # Set rb to the value needed for the next operation.
            rb=api(base,'/api/v1/games/roulette/rebet','POST',{'player_id':'human'}); assert rb['placed']
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/games/roulette/settings','POST',{'zero_rule':'en_prison'})
            # Call an asynchronous API/helper and wait for the result before continuing.
            api(base,'/api/v1/games/roulette/bets','POST',{'player_id':'human','amount':10,'bet_type':'red','covered_numbers':['1','3','5','7','9','12','14','16','18','19','21','23','25','27','30','32','34','36']})
            # Set api(base,'/api/v1/games/roulette/spin','POST',{'force_result to the value needed for the next operation.
            api(base,'/api/v1/games/roulette/spin','POST',{'force_result':'0'}); st=api(base,'/api/v1/games/roulette/state')['state']; assert st['open_round']['bets']
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
                # Refresh the whole browser document to prove the updated balance is not cached shell state.
                page.reload(wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Verify current-user refresh restores the exact ledger-backed balance.
                assert '5,250' in page.get_by_test_id('premium-wallet').inner_text()
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
                    category_labels={'all':'Все игры','cards':'Карточные','draw':'Розыгрыши','instant':'Быстрые','machine':'Автоматы','numbers':'Числа','reels':'Барабаны','roadmaps':'Дорожные карты','social':'Социальные','strategy':'Стратегия','table':'Настольные игры','wheel':'Колесо'}
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
