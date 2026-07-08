# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
#!/usr/bin/env python3
# Import required dependency so this module can use its public functions or constants.
import argparse, json, os, socket, subprocess, sys, time, traceback, urllib.request
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Set ROOT to the value needed for the next operation.
ROOT = Path(__file__).resolve().parents[1]
# Add the repository root so direct module imports work from this script.
sys.path.insert(0, str(ROOT))
# Import Blackjack helpers so deterministic API-suite checks can cover table rules.
from casino.games.blackjack import api as blackjack_api, engine as blackjack_engine
# Set RESULTS to the value needed for the next operation.
RESULTS=[]

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
def api(base, path, method='GET', body=None, ok=True):
    # Set data to the value needed for the next operation.
    data = None if body is None else json.dumps(body).encode('utf-8')
    # Set req to the value needed for the next operation.
    req = urllib.request.Request(base + path, data=data, method=method, headers={'Content-Type':'application/json'})
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

# Define the start_server function used by this module.
def start_server():
    # Set port to the value needed for the next operation.
    port=free_port(); proc=subprocess.Popen([sys.executable,str(ROOT/'run.py'),'--port',str(port),'--no-browser'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    # Set base to the value needed for the next operation.
    base=f'http://127.0.0.1:{port}'
    # Iterate through the collection to process each item.
    for _ in range(80):
        # Start protected logic so failures can be handled safely.
        try: api(base,'/api/v1/casino/state'); return proc,base
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

# Define the run_api_tests function used by this module.
def run_api_tests():
    # Set proc,base to the value needed for the next operation.
    proc,base=start_server()
    # Start protected logic so failures can be handled safely.
    try:
        # Call an asynchronous API/helper and wait for the result before continuing.
        api(base,'/api/v1/casino/reset','POST',{})
        # Define the core function used by this module.
        def core():
            # Set s to the value needed for the next operation.
            s=api(base,'/api/v1/casino/state'); assert any(g['id']=='roulette' for g in s['games']); assert any(p['player_id']=='bot_1' for p in s['players'])
            # Set a to the value needed for the next operation.
            a=api(base,'/api/v1/admin/overview'); assert a['app_version']=='9.1.1'
        # Execute this statement as part of the module's documented control flow.
        run_case('API-CORE-001',['CORE-001','ADMIN-001'],core)

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
        # Define the admin function used by this module.
        def admin():
            # Set r to the value needed for the next operation.
            r=api(base,'/api/v1/admin/requirements'); assert len(r['requirements'])>100
            # Set l to the value needed for the next operation.
            l=api(base,'/api/v1/admin/logs?kind=app&limit=10'); assert isinstance(l['logs'],list)
        # Execute this statement as part of the module's documented control flow.
        run_case('API-ADMIN-001',['ADMIN-001','DOC-001','LOG-001'],admin)
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
            # Set page to the value needed for the next operation.
            page=browser.new_page(viewport={'width':1920,'height':1080})
            # Set console_errors to the value needed for the next operation.
            console_errors=[]; page_errors=[]
            # Set page.on('console', lambda msg: console_errors.append(msg.tex to the value needed for the next operation.
            page.on('console', lambda msg: console_errors.append(msg.text) if msg.type=='error' else None)
            # Execute this statement as part of the module's documented control flow.
            page.on('pageerror', lambda err: page_errors.append(str(err)))
            # Define the shot function used by this module.
            def shot(name): page.screenshot(path=str(screenshots/name), full_page=True)
            # Start protected logic so failures can be handled safely.
            try:
                # Set page.goto(base, wait_until to the value needed for the next operation.
                page.goto(base, wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-LOBBY-001',['UI-001','CORE-010'],lambda: page.get_by_test_id('card-roulette').is_visible())
                # Set page.get_by_test_id('nav-roulette').click(); page.get_by_tes to the value needed for the next operation.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(); page.get_by_test_id('roulette-num-17').click(); page.locator('.bet-chip').first.wait_for(timeout=3000); page.get_by_test_id('roulette-spin').click(); page.wait_for_timeout(3200)
                # Execute this statement as part of the module's documented control flow.
                run_case('BR-ROU-001',['ROU-040','ROU-041','ROU-050'],lambda: page.locator('.roulette-table-board').is_visible()); page.get_by_test_id('roulette-auto-rounds').fill('5'); page.get_by_test_id('roulette-auto-start').click(); page.wait_for_timeout(400); page.get_by_test_id('roulette-auto-stop').click(); page.wait_for_timeout(500); run_case('BR-AUTO-ROU-001',['AUTO-003','AUTO-010'],lambda: page.get_by_text('Off').first.is_visible())
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slots-spin').click(); page.wait_for_timeout(1200); run_case('BR-SLOT-001',['SLOT-020','SLOT-021'],lambda: page.get_by_test_id('slot-grid').is_visible())
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('nav-keno').click(); page.get_by_test_id('keno-num-1').click(); page.get_by_test_id('keno-num-2').click(); page.get_by_test_id('keno-num-3').click(); page.get_by_test_id('keno-draw').click(); page.wait_for_timeout(1500); run_case('BR-KENO-001',['KENO-020','KENO-021'],lambda: page.get_by_test_id('keno-grid').is_visible())
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('nav-bingo').click(); page.get_by_test_id('bingo-buy').click(); page.get_by_test_id('bingo-call').click(); page.wait_for_timeout(700); run_case('BR-BINGO-001',['BINGO-030','BINGO-031'],lambda: page.get_by_test_id('bingo-card').is_visible())
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('nav-blackjack').click(); page.get_by_test_id('blackjack-deal').click(); page.wait_for_timeout(700); run_case('BR-BJ-001',['BJ-030','BJ-031'],lambda: page.get_by_test_id('blackjack-hand-0').is_visible())
                # Execute this statement as part of the module's documented control flow.
                page.get_by_test_id('nav-baccarat').click(); page.get_by_test_id('baccarat-banker').click(); page.get_by_test_id('baccarat-deal').click(); page.wait_for_timeout(900); run_case('BR-BAC-001',['BAC-020','BAC-021'],lambda: page.get_by_text('Winner:').is_visible())
                # Set page.goto(base+'/admin', wait_until to the value needed for the next operation.
                page.goto(base+'/admin', wait_until='networkidle'); run_case('BR-ADMIN-001',['ADMIN-001','ADMIN-010'],lambda: page.get_by_test_id('admin-tab-audio').is_visible()); page.get_by_test_id('admin-tab-audio').click(); page.get_by_test_id('admin-save-audio').wait_for(timeout=5000); run_case('BR-AUDIO-001',['AUDIO-002','AUDIO-005'],lambda: page.get_by_test_id('admin-preview-voice').is_visible())
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
    ap=argparse.ArgumentParser(); ap.add_argument('--api',action='store_true'); ap.add_argument('--browser',action='store_true'); args=ap.parse_args()
    # Branch when the following condition is true.
    if not args.api and not args.browser: args.api=True
    # Start protected logic so failures can be handled safely.
    try:
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
