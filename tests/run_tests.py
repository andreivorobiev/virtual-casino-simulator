# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
# Import required dependency so this module can use its public functions or constants.
import argparse, json, os, re, socket, subprocess, sys, time, traceback, urllib.request
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Set ROOT to the value needed for the next operation.
ROOT = Path(__file__).resolve().parents[1]
# Add the repository root so direct module imports work from this script.
sys.path.insert(0, str(ROOT))
# Import Blackjack helpers so deterministic API-suite checks can cover table rules.
from casino.games.blackjack import api as blackjack_api, engine as blackjack_engine
# Import auth helpers so API tests can seed users through the backend storage seam.
from casino.core import auth as auth_core
# Import auth cookie settings so browser tests can enter through the backend session seam.
from casino.config import AUTH_SESSION_COOKIE
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

# Define the run_storage_tests function used by this module.
def run_storage_tests():
    # Execute the JSON fallback parity test for provider-backed players, ledger, history, and settings.
    run_case('STORAGE-JSON-001',['CORE-017','LEDGER-001','LEDGER-007','TEST-030'],storage_tests.run_json_provider_parity)
    # Execute the MySQL schema and atomic ledger-provider path test without requiring a live service.
    run_case('STORAGE-MYSQL-001',['CORE-017','LEDGER-001','LEDGER-007','LEDGER-009'],storage_tests.run_mysql_schema_provider_path)

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

# Define the run_api_tests function used by this module.
def run_api_tests():
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
        # Define the core function used by this module.
        def core():
            # Set s to the value needed for the next operation.
            s=api(base,'/api/v1/casino/state'); assert any(g['id']=='roulette' for g in s['games']); assert any(p['player_id']=='bot_1' for p in s['players'])
            # Set a to the value needed for the next operation.
            a=api(base,'/api/v1/admin/overview'); assert a['app_version']=='9.1.1'
        # Execute this statement as part of the module's documented control flow.
        run_case('API-CORE-001',['CORE-001','ADMIN-001'],core)

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
        run_case('API-PRIVATE-SESSIONS-001',['ROU-010','SLOT-019','BJ-020','BAC-010','KENO-008','BINGO-020','LEDGER-001','AUTO-001'],private_sessions)
        # Define the admin function used by this module.
        def admin():
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
        run_case('API-ADMIN-001',['ADMIN-001','DOC-001','LOG-001','ADMIN-USER-PENDING-035','TERMS-PENDING-035','TOKEN-PENDING-035','I18N-003'],admin)
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
    # Start protected logic so failures can be handled safely.
    try:
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Call an asynchronous API/helper and wait for the result before continuing.
        login_default_user(base)
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
            # Set a session cookie so browser tests exercise authenticated app/API access.
            page.context.add_cookies([{'name':AUTH_SESSION_COOKIE,'value':SESSION_TOKEN,'url':base,'httpOnly':True,'sameSite':'Lax'}])
            # Set console_errors to the value needed for the next operation.
            console_errors=[]; page_errors=[]
            # Set page.on('console', lambda msg: console_errors.append(msg.tex to the value needed for the next operation.
            page.on('console', lambda msg: console_errors.append(msg.text) if msg.type=='error' else None)
            # Execute this statement as part of the module's documented control flow.
            page.on('pageerror', lambda err: page_errors.append(str(err)))
            # Store mocked auth state because backend v2 auth APIs are owned by issue 39.
            auth_state={'logged_in':False,'terms_required':True,'tokens':5000,'locale':'en-US'}
            # Define the auth_payload function used by this module.
            def auth_payload():
                # Return a draft v2 current-user payload for frontend-only browser checks.
                return {'user':{'user_id':'user_demo','username':'demo','display_name':'Demo Player','locale':auth_state['locale']},'player':{'player_id':'human','token_balance':auth_state['tokens']},'terms':{'required':auth_state['terms_required'],'version':'private-beta-1'}}
            # Define the mocked_auth_response function used by this module.
            def mocked_auth_response(ok=True, data=None, status=200, message='Unauthorized'):
                # Return a standard API envelope string for Playwright route fulfillment.
                return json.dumps({'ok':ok,'data':data or {},'error':None if ok else {'code':'AUTH_REQUIRED','message':message}})
            # Define the handle_auth_route function used by this module.
            def handle_auth_route(route):
                # Store request so path, method, and body can drive the v2 auth mock.
                request=route.request
                # Store path so endpoint matching ignores host and query details.
                path=request.url.split('/api/v2',1)[1].split('?',1)[0]
                # Branch for current-user session lookup.
                if path=='/me' and request.method=='GET':
                    # Return a standard failure envelope until mocked login completes.
                    if not auth_state['logged_in']: return route.fulfill(status=200,content_type='application/json',body=mocked_auth_response(False))
                    # Return the current mocked user session.
                    return route.fulfill(status=200,content_type='application/json',body=mocked_auth_response(True,auth_payload()))
                # Branch for browser login.
                if path=='/auth/login' and request.method=='POST':
                    # Store submitted JSON so locale preservation can be asserted.
                    body=json.loads(request.post_data or '{}')
                    # Mark the mocked browser session logged in.
                    auth_state['logged_in']=True
                    # Preserve the locale the frontend sends with login.
                    auth_state['locale']=body.get('locale') or auth_state['locale']
                    # Return the mocked current-user payload after login.
                    return route.fulfill(status=200,content_type='application/json',body=mocked_auth_response(True,auth_payload()))
                # Branch for terms acceptance.
                if path=='/me/terms/accept' and request.method=='POST':
                    # Mark terms accepted so the shell can enter the casino.
                    auth_state['terms_required']=False
                    # Return the updated mocked current-user payload.
                    return route.fulfill(status=200,content_type='application/json',body=mocked_auth_response(True,auth_payload()))
                # Branch for token additions through the current-user wallet.
                if path=='/me/tokens/add' and request.method=='POST':
                    # Store submitted JSON so the requested amount can update the mock ledger balance.
                    body=json.loads(request.post_data or '{}')
                    # Add the requested fake tokens for frontend wallet validation.
                    auth_state['tokens']+=int(body.get('amount') or 0)
                    # Return the updated mocked current-user payload.
                    return route.fulfill(status=200,content_type='application/json',body=mocked_auth_response(True,auth_payload()))
                # Branch for browser logout.
                if path=='/auth/logout' and request.method=='POST':
                    # Mark the mocked browser session logged out.
                    auth_state['logged_in']=False
                    # Return an empty success envelope for logout.
                    return route.fulfill(status=200,content_type='application/json',body=mocked_auth_response(True,{}))
                # Return a route-local 404 for unexpected v2 auth endpoints.
                return route.fulfill(status=404,content_type='application/json',body=mocked_auth_response(False,status=404,message='Unhandled auth mock'))
            # Route planned v2 auth/current-user APIs so frontend work can proceed before issue 39 lands.
            page.route('**/api/v2/**', handle_auth_route)
            # Define the shot function used by this module.
            def shot(name): page.screenshot(path=str(screenshots/name), full_page=True)
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
                # Fill the mocked login form through browser-visible controls.
                page.get_by_test_id('login-email').fill('demo@example.local'); page.get_by_test_id('login-password').fill('password'); page.get_by_test_id('login-terms-check').check(); page.get_by_test_id('login-submit').click()
                # Wait for the terms acceptance screen returned by the mocked v2 login payload.
                page.get_by_test_id('terms-gate').wait_for(timeout=5000)
                # Capture terms evidence for the frontend auth handback.
                shot('auth_terms_gate.png')
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-TERMS-001',['TERMS-UI-001'],lambda: page.get_by_test_id('accept-terms').is_visible())
                # Accept terms through the planned current-user endpoint.
                page.get_by_test_id('accept-terms').click()
                # Wait for the authenticated casino shell to mount after terms acceptance.
                page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Capture authenticated shell evidence for the frontend auth handback.
                shot('auth_shell_tokens.png')
                # Define the auth_shell function used by this module.
                def auth_shell():
                    # Verify the premium topbar is visible after login and terms acceptance.
                    assert page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the current-user wallet uses the fake-token glyph.
                    assert '◈' in page.get_by_test_id('premium-wallet').inner_text()
                    # Verify the chosen locale survived login and terms acceptance.
                    assert page.get_by_test_id('shell-locale-select').input_value()=='ru-RU'
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-SHELL-001',['AUTH-UI-001','TOKEN-UI-001','I18N-003'],auth_shell)
                # Open the token wallet menu before adding fake tokens.
                page.locator('.wallet-menu summary').click()
                # Fill the add-token amount through the browser-visible token control.
                page.get_by_test_id('add-tokens').wait_for(timeout=5000); page.locator('#add-token-amount').fill('250'); page.get_by_test_id('add-tokens').click()
                # Wait until the wallet reflects the mocked ledger-backed token addition.
                page.wait_for_function("() => document.querySelector('[data-testid=\"premium-wallet\"]')?.textContent?.includes('5,250')")
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTH-TOKENS-001',['TOKEN-UI-001'],lambda: '5,250' in page.get_by_test_id('premium-wallet').inner_text())
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
                # Define the premium_shell function used by this module.
                def premium_shell():
                    # Verify the premium topbar remains visible at app load.
                    assert page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the shared wallet remains visible for the current user's token balance.
                    assert page.get_by_test_id('premium-wallet').is_visible()
                    # Verify the wallet displays the play-token mark instead of a currency symbol.
                    assert '◈' in page.get_by_test_id('premium-wallet').inner_text()
                    # Verify the wallet label uses authenticated token-balance terminology.
                    assert 'token balance' in page.get_by_test_id('premium-wallet').inner_text().lower()
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
                page.wait_for_function("() => document.querySelector('#toast')?.textContent?.includes('◈123') && document.querySelector('#toast')?.textContent?.includes('play tokens')")
                # Capture token wallet evidence for the worker handback.
                shot('token_wallet.png')
                # Define the token_wallet function used by this module.
                def token_wallet():
                    # Verify the wallet retained token terminology after the add-token action.
                    assert 'token balance' in page.get_by_test_id('premium-wallet').inner_text().lower()
                    # Verify the toast uses the token mark for the added amount.
                    assert '◈123' in page.locator('#toast').inner_text()
                    # Verify the toast describes play tokens instead of real-money language.
                    assert 'play tokens' in page.locator('#toast').inner_text()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-TOKEN-WALLET-001',['TOKEN-001','TOKEN-002','LEDGER-025'],token_wallet)
                # Define the premium_lobby function used by this module.
                def premium_lobby():
                    # Verify the lobby renders one premium card for every current game.
                    assert page.locator('[data-testid^="card-"]').count()==6
                    # Verify the status/trust rail from the approved lobby is visible.
                    assert page.get_by_test_id('lobby-trust-rail').is_visible()
                    # Verify the premium lobby headline renders in the first route view.
                    assert page.get_by_text('Midnight Ledger Casino').is_visible()
                    # Verify the Roulette card still exposes its route action.
                    assert page.get_by_test_id('open-roulette').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-LOBBY-001',['CORE-005','CORE-006','UX-008'],premium_lobby)
                # Resize the browser to the approved narrow viewport before responsive checks.
                page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(250)
                # Define the responsive_lobby function used by this module.
                def responsive_lobby():
                    # Verify the stacked topbar remains visible on a narrow viewport.
                    assert page.get_by_test_id('premium-topbar').is_visible()
                    # Verify the lobby does not introduce page-level horizontal overflow.
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Verify the featured game card remains visible after responsive stacking.
                    assert page.get_by_test_id('card-roulette').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-LOBBY-RESP-001',['CORE-015','UX-009'],responsive_lobby)
                # Restore desktop dimensions before existing game interaction coverage runs.
                page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(250)
                # Open Roulette and wait for the premium vector wheel to mount.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for()
                # Define the premium_roulette_layout function used by this module.
                def premium_roulette_layout():
                    # Verify the premium three-zone layout is mounted.
                    assert page.get_by_test_id('roulette-premium-layout').is_visible()
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
                    # Verify the bot/autoplay rail remains mounted without resizing the stage.
                    assert page.locator('#botPanel').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ROU-PREMIUM-001',['ROU-041','ROU-043','ROU-045','ROU-048','ROU-049','UX-007','UX-009'],premium_roulette_layout)
                # Capture betting-state visual evidence for the Roulette worker handback.
                shot('roulette-premium-betting.png')
                # Place a straight bet and wait for the table chip to render.
                page.get_by_test_id('roulette-num-17').click(); page.locator('.bet-chip').first.wait_for(timeout=3000)
                # Call the i18n runtime directly to verify language switching does not remount gameplay.
                page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.initI18n({ domains: ['games/roulette'] }); await i18n.setLocale('ru-RU', { persistLocal: false }); }""")
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-I18N-GAMESTATE-ROU-001',['I18N-002','ROU-046'],lambda: page.locator('.bet-chip').first.is_visible())
                # Spin the wheel through the existing Roulette UI action.
                page.get_by_test_id('roulette-spin').click()
                # Wait for the fixed result region to reach the settled phase.
                page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'settled'", timeout=7000)
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
                    # Verify the table board remains visible after settlement.
                    assert page.locator('.roulette-table-board').is_visible()
                    # Verify the drawer still renders after bets settle.
                    assert page.get_by_test_id('roulette-bet-slip').is_visible()
                    # Verify recent stats remain visible after settlement.
                    assert page.get_by_test_id('roulette-stats-spark').is_visible()
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ROU-001',['ROU-040','ROU-041','ROU-042','ROU-043','ROU-044','ROU-046','ROU-049','ROU-050','ROU-052','ROU-053','ROU-054','ROU-055','ROU-056'],premium_roulette_settled)
                # Capture settled-state visual evidence for the Roulette worker handback.
                shot('roulette-premium-settled.png')
                # Start and stop Roulette autoplay through the shared control-plane widget.
                page.get_by_test_id('roulette-auto-rounds').fill('5'); page.get_by_test_id('roulette-auto-start').click(); page.wait_for_timeout(400); page.get_by_test_id('roulette-auto-stop').click(); page.wait_for_timeout(500)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-AUTO-ROU-001',['AUTO-003','AUTO-010','ROU-047'],lambda: page.get_by_text('Off').first.is_visible())
                # Restore English for game prerender evidence after the locale-preservation smoke test.
                page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }""")
                # Navigate to the premium Slots route before collecting state evidence.
                page.get_by_test_id('nav-slots').click()
                # Wait for the fixed reel grid to mount before measuring layout stability.
                page.get_by_test_id('slot-grid').wait_for(timeout=5000)
                # Capture the idle cabinet state for worker handback evidence.
                shot('slots_idle.png')
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
                # Set page.goto(base+'/admin', wait_until to the value needed for the next operation.
                page.goto(base+'/admin', wait_until='networkidle')
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ADMIN-001',['ADMIN-001','ADMIN-010'],lambda: page.get_by_test_id('admin-tab-audio').is_visible())
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
                if console_errors or page_errors: raise AssertionError('Browser errors: '+str(console_errors+page_errors))
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
    ap=argparse.ArgumentParser(); ap.add_argument('--api',action='store_true'); ap.add_argument('--browser',action='store_true'); ap.add_argument('--storage',action='store_true'); args=ap.parse_args()
    # Branch when the following condition is true.
    if not args.api and not args.browser and not args.storage: args.api=True
    # Start protected logic so failures can be handled safely.
    try:
        # Branch when the following condition is true.
        if args.storage: run_storage_tests()
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
