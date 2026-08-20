# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Complete Bingo, Blackjack, Baccarat, shared-shell, and Admin Browser affinity ownership."""

# Import Base64 decoding for the Admin diagnostics artifact evidence.
import base64
# Import JSON serialization for exact mocked API envelopes and stored-record checks.
import json
# Import regular expressions for report, locale, and ledger-label assertions.
import re

# Import the sole environment-scalable Playwright wait budget. (TEST-053)
from tests.browser_timing import WAIT_MS


# Execute the reduced table-game, Admin-core, and Admin-presentation families under independent shard owners.
def run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,page,base,ROOT,browser_data_dir,browser_player_id,visual_matrix,save_player_game_state,blackjack_engine,wait_for_bingo_terminal_render,require_bingo_terminal_auto_payload,require_bingo_terminal_reload_payload,guest_analytics,prepare_admin_feedback_draft,save_admin_feedback_triage,collect_normal_admin_navigation,assert_route_i18n,auth_core,DEFAULT_AUTH_EMAIL,DEFAULT_AUTH_PASSWORD,EXPECTED_MODULE_ROWS,VERSION_MANIFEST,read_i18n_json,write_json,shot,region_evidence,game_evidence,console_errors,page_errors,http_errors,screenshots):
    # Resolve each contiguous affinity exactly once so source guards and skip accounting stay reviewable.
    table_games_owner=browser_shard_owns_group('table_games')
    # Keep feedback production and every consuming Admin operational case on one owner.
    feedback_admin_owner=browser_shard_owns_group('feedback_admin')
    # Keep the final Admin audio and localization presentation chain on one owner.
    admin_presentation_owner=browser_shard_owns_group('admin_presentation')
    # Run Bingo, Blackjack, Baccarat, route localization, and wellness only on their declared owner.
    if table_games_owner:
        # Navigate to Bingo before exercising the real card-purchase mutation boundary.
        page.get_by_test_id('nav-bingo').click(); page.get_by_test_id('premium-bingo').wait_for(timeout=WAIT_MS)
        # Read the current player's ledger before the one visible card purchase.
        bingo_ledger_before=page.request.get(base+f'/api/v1/players/{browser_player_id}/ledger').json()['data']['ledger']
        # Store immutable ledger identities because response ordering is not a persistence contract.
        bingo_ledger_ids_before={row['ledger_id'] for row in bingo_ledger_before}
        # Hold the first real card response after backend commit so duplicate-click protection is deterministic.
        page.evaluate("""() => { const originalFetch=window.fetch.bind(window); let firstPurchase=true; window.__bingoPurchaseHeld=false; window.__bingoReleasePurchase=()=>{}; window.__bingoPurchaseRequestCount=0; window.__bingoRestoreFetch=()=>{window.fetch=originalFetch;}; window.fetch=async (...args) => { const input=args[0]; const url=typeof input==='string' ? input : input.url; const init=args[1] || {}; const method=String(init.method || (typeof input==='object' ? input.method : 'GET') || 'GET').toUpperCase(); const responsePromise=originalFetch(...args); if(url.includes('/api/v1/games/bingo/cards') && method==='POST'){ window.__bingoPurchaseRequestCount+=1; if(firstPurchase){ firstPurchase=false; const response=await responsePromise; window.__bingoPurchaseHeld=true; await new Promise(resolve => { window.__bingoReleasePurchase=resolve; }); return response; } } return responsePromise; }; }""")
        # Buy one card through the current visible player control.
        page.get_by_test_id('bingo-buy').click()
        # Wait until the real backend committed while the browser response remains deliberately held.
        page.wait_for_function('window.__bingoPurchaseHeld === true',timeout=WAIT_MS)
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
        page.wait_for_function("() => document.querySelector('[data-testid=\"bingo-control-rail\"]')?.getAttribute('aria-busy') === 'false' && !document.querySelector('[data-testid=\"bingo-call\"]')?.disabled",timeout=WAIT_MS)
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
        # Complete the session through the existing bounded compatibility helper and retain its authoritative response.
        bingo_auto_payload=page.evaluate("""async () => { const response = await fetch('/api/v1/games/bingo/auto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ max_calls: 75 }) }); return await response.json(); }""")
        # Fail closed unless the mutation response contains one archived winning session.
        bingo_terminal=require_bingo_terminal_auto_payload(bingo_auto_payload)
        # Leave Bingo through a deterministic route transition so clicking Bingo must create a fresh mount.
        page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
        # Observe the exact state response consumed by the fresh Bingo route mount.
        with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/bingo/state') and response.request.method=='GET',timeout=WAIT_MS) as bingo_reload_info:
            # Remount Bingo through its real navigation control after route ownership changed.
            page.get_by_test_id('nav-bingo').click()
        # Prove the remount loaded the same authoritative terminal session before inspecting markup.
        bingo_reload_terminal=require_bingo_terminal_reload_payload(bingo_reload_info.value.json(),bingo_terminal['session_id'])
        # Wait on the complete terminal render projection without extending the old five-second budget.
        bingo_terminal_render=wait_for_bingo_terminal_render(page,bingo_reload_terminal)
        # Preserve the existing premium Bingo acceptance after the new purchase boundary proof.
        run_case('BR-BINGO-001',['BINGO-017','BINGO-018','BINGO-021','BINGO-022','AUTO-013'],lambda: bingo_terminal_render['winningCellCount']==bingo_terminal['winning_cell_count'] and page.get_by_test_id('bingo-card').is_visible() and page.locator('[data-winning-cell="true"]').first.is_visible() and page.get_by_test_id('bingo-cards-drawer').is_visible() and page.get_by_test_id('autoplay-bingo').is_visible())
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
        page.get_by_test_id('blackjack-premium').wait_for(timeout=WAIT_MS)
        # Set a visible one-hundred-token stake for an exact three-to-two payout assertion.
        page.get_by_test_id('blackjack-bet').fill('100')
        # Observe the real deal response while activating the public Blackjack control.
        with page.expect_response(lambda response: response.url.endswith('/api/v1/games/blackjack/rounds') and response.request.method == 'POST') as blackjack_deal_info:
            # Deal the controlled natural entirely through the rendered button.
            page.get_by_test_id('blackjack-deal').click()
        # Wait for the first player hand lane to render.
        page.get_by_test_id('blackjack-hand-0').wait_for(timeout=WAIT_MS)
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
        run_case('BR-BJ-001',['BJ-028','BJ-029','BJ-030','AUTO-014'],blackjack_premium)
        # Switch Blackjack locale in place to verify gameplay state is preserved.
        page.evaluate("""async () => { const i18n = await import('/core/i18n.js'); await i18n.initI18n({ domains: ['games/blackjack'] }); await i18n.loadI18nDomain('games/blackjack'); await i18n.setLocale('ru-RU', { persistLocal: false }); }""")
        # Define the blackjack_i18n function used by this module.
        def blackjack_i18n():
            # Verify the same hand remains visible after localized rerender.
            assert page.get_by_test_id('blackjack-hand-0').is_visible()
            # Verify the selected backend round id did not change on locale switch.
            assert page.get_by_test_id('blackjack-round-id').get_attribute('data-round-id')==blackjack_round_id
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
        page.get_by_test_id('nav-baccarat').click(); page.get_by_test_id('baccarat-wager-setup').wait_for(timeout=WAIT_MS); page.get_by_test_id('nav-blackjack').click(); page.get_by_test_id('blackjack-premium').wait_for(timeout=WAIT_MS)
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
        page.get_by_test_id('baccarat-wager-setup').wait_for(timeout=WAIT_MS)
        # Switch the idle table to Russian so the corrected shoe terminology is exact-head browser evidence.
        page.get_by_test_id('shell-locale-select').select_option('ru-RU'); page.wait_for_timeout(100)
        # Define the focused Russian Baccarat copy regression before gameplay changes the visible status list.
        def baccarat_polish_copy():
            # Read the complete mounted table so borrowed English terms cannot hide in a secondary status panel.
            russian_baccarat_text=page.locator('.bac-shell').inner_text()
            # Require the complete localized burn-card wording and reject the former mixed-language token.
            assert '\u0412\u0438\u0434\u043d\u0430 \u0441\u0436\u0438\u0433\u0430\u0435\u043c\u0430\u044f \u043a\u0430\u0440\u0442\u0430' in russian_baccarat_text and ' burn' not in russian_baccarat_text
            # Record the exact idle-state copy at primary desktop for governed human review.
            game_evidence('after-pass-game-polish-baccarat-ru-RU-desktop_primary.png','baccarat',['wagering'],'ru-RU','desktop_primary')
        # Execute the locale-owned wording check before returning to English gameplay.
        run_case('BR-BAC-COPY-001',['BAC-020','I18N-010','TEST-117'],baccarat_polish_copy)
        # Restore English so established Baccarat assertions retain their deterministic labels.
        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_timeout(100)
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
        page.wait_for_function('window.__baccaratFirstBetHeld === true',timeout=WAIT_MS)
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
        page.wait_for_function("() => !document.querySelector('[data-testid=\"baccarat-deal\"]').disabled && document.querySelector('.bac-drawer-total')?.textContent.includes('25')",timeout=WAIT_MS)
        # Deal one coup so the reveal theater and settlement state are exercised.
        page.get_by_test_id('baccarat-deal').click()
        # Wait for the post-reveal result state to settle.
        page.get_by_test_id('baccarat-result').wait_for(timeout=WAIT_MS)
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
            # Produce one visible Slots history row when this isolated shard has no prior spin.
            def drive_slots_interpolation():
                # Skip the action when the current user already owns a rendered spin history row.
                if page.locator('[data-testid="slots-recent-spins"] .slots-history-row').count(): return
                # Spin through the same visible control a player uses.
                page.get_by_test_id('slots-spin').click()
                # Wait for one settled history row and a re-enabled action before auditing text.
                page.wait_for_function("() => Boolean(document.querySelector('[data-testid=\"slots-recent-spins\"] .slots-history-row')) && !document.querySelector('[data-testid=\"slots-spin\"]')?.disabled",timeout=WAIT_MS)
            # Produce one complete Keno draw when this isolated shard has no final-draw metric.
            def drive_keno_interpolation():
                # Skip the action when a prior draw already rendered its complete twenty-ball result.
                if page.get_by_test_id('keno-drawn-ball').count()==20: return
                # Select ten stable spots through public visible number controls.
                for spot in (3,8,12,17,24,31,44,55,63,72): page.get_by_test_id(f'keno-num-{spot}').click()
                # Start one real draw through the current visible control.
                page.get_by_test_id('keno-draw').click()
                # Wait until the route owns a complete final-draw interpolation state.
                page.wait_for_function("() => document.querySelectorAll('[data-testid=\"keno-drawn-ball\"]').length === 20",timeout=WAIT_MS)
            # Declare only route-owned state producers needed by interpolation templates.
            route_interpolation_drivers={'games/slots':drive_slots_interpolation,'games/keno':drive_keno_interpolation}
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
                    page.get_by_test_id(ready_testid).wait_for(timeout=WAIT_MS)
                    # Run only the mounted route's declared visible state producer when required.
                    interpolation_driver=route_interpolation_drivers.get(domain)
                    # Produce the interpolation state inside this same case and shard.
                    if interpolation_driver: interpolation_driver()
                    # Apply the complete domain, key-leak, placeholder, encoding, and label audit.
                    assert_route_i18n(domain, interpolation_key)
            # Restore English so the following independent Admin page starts from the suite default.
            page.evaluate("async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }")
        # Execute the release-blocking i18n audit as one requirement-mapped browser case.
        run_case('BR-I18N-ROUTES-001',['I18N-001','I18N-002'],all_game_route_i18n)
        # Define every-game wellness controls, focus, locale, responsive, reduced-motion, pause, and stop acceptance. (issue #167)
        def session_wellness_browser():
            # Hold one authoritative mocked settings record so browser writes remain deterministic and non-durable.
            wellness_state={'enabled':True,'break_reminder_enabled':True,'reminder_interval_minutes':10,'revision':4,'persisted':True}
            # Count exact settings writes so session-local pause cannot masquerade as a durable API mutation.
            wellness_patches=[]
            # Fulfill settings reads and writes with the standard API envelope and optimistic revision.
            def wellness_settings_route(route):
                # Return the current record for the authenticated controller startup read.
                if route.request.method=='GET': route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'wellness':wellness_state}})); return
                # Parse only the production controller's allowlisted settings body.
                payload=route.request.post_data_json
                # Retain the bounded write for pause-versus-stop evidence.
                wellness_patches.append(dict(payload))
                # Advance the fake authoritative record exactly once.
                wellness_state.update({key:value for key,value in payload.items() if key in {'enabled','break_reminder_enabled','reminder_interval_minutes'}}); wellness_state['revision']+=1
                # Return the updated exact settings projection.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'wellness':wellness_state}}))
            # Fulfill the neutral current-session summary without using caller-authored identity or time.
            def wellness_summary_route(route):
                # Return fixed play-token-only facts through the production response shape.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'movements':2,'staked':10.0,'returned':4.0,'net':-6.0,'since':'2026-08-13T12:00:00.000Z','play_tokens_only':True}}))
            # Install page-local routes so no test preference survives this case.
            page.route('**/api/v2/me/wellness',wellness_settings_route); page.route('**/api/v2/me/wellness/summary',wellness_summary_route)
            # Reload the authenticated shell so the production controller adopts the controlled opt-in state.
            page.reload(wait_until='networkidle'); page.get_by_test_id('wellness-open').wait_for(state='visible',timeout=WAIT_MS)
            # Require the persistent control on a real game route rather than only the lobby.
            page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS); assert page.get_by_test_id('wellness-open').is_visible()
            # Exercise every governed wellness locale and viewport under reduced motion.
            viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}; page.emulate_media(reduced_motion='reduce')
            # Iterate the complete two-locale matrix without persisting the temporary locale choice.
            for locale in ('en-US','ru-RU'):
                # Change locale through the visible shell control and wait for active resource ownership.
                page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                # Exercise every required layout cell with the same persistent game route.
                for viewport_id,viewport in viewports.items():
                    # Apply the exact governed dimensions before opening the native modal.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Open from the visible every-game control and require stable heading focus.
                    page.get_by_test_id('wellness-open').focus(); page.get_by_test_id('wellness-open').click(); page.get_by_test_id('wellness-dialog').wait_for(state='visible'); page.wait_for_function("() => document.activeElement?.id === 'wellness-title'")
                    # Wait for asynchronous summary and locale resources to reach the exact asserted modal state before measuring it. (issue #894)
                    page.wait_for_function("() => { const dialog=document.querySelector('[data-testid=wellness-dialog]'); const dismiss=document.querySelector('[data-testid=wellness-dismiss]'); const summary=document.querySelector('[data-testid=wellness-summary]'); return Boolean(dialog && dismiss && summary && !dialog.innerText.includes('wellness.') && dismiss.getAttribute('aria-label') === dismiss.innerText && summary.querySelectorAll('li').length === 4); }")
                    # Require translated text, neutral facts, complete summary, and horizontal containment.
                    assert 'wellness.' not in page.get_by_test_id('wellness-dialog').inner_text() and page.get_by_test_id('wellness-dismiss').get_attribute('aria-label')==page.get_by_test_id('wellness-dismiss').inner_text() and page.get_by_test_id('wellness-summary').locator('li').count()==4 and page.evaluate("() => { const dialog=document.querySelector('[data-testid=wellness-dialog]'); return document.documentElement.scrollWidth <= window.innerWidth + 1 && dialog.scrollWidth <= dialog.clientWidth + 1; }")
                    # Capture opt-in, neutral-summary, keyboard, and reduced-motion acceptance in this exact cell.
                    game_evidence(f'after-pass-session-wellness-{locale}-{viewport_id}.png','session_wellness',['opted_in','summary','keyboard_focus','reduced_motion','every_game_control'],locale,viewport_id)
                    # Close with Escape so the native dialog must restore the exact invoking control.
                    page.keyboard.press('Escape'); page.get_by_test_id('wellness-dialog').wait_for(state='hidden'); page.wait_for_function("() => document.activeElement?.dataset?.testid === 'wellness-open'")
            # Restore desktop English for behavioral pause and stop checks.
            page.set_viewport_size(viewports['desktop_primary']); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.get_by_test_id('wellness-open').click(); page.get_by_test_id('wellness-dialog').wait_for(state='visible')
            # Pause only the current login session and require no durable settings request.
            page.get_by_test_id('wellness-pause').click(); page.wait_for_function("() => document.querySelector('[data-testid=wellness-message]')?.textContent.includes('paused')"); assert wellness_patches==[]
            # Reload and require session-local pause to survive for the same server session.
            page.get_by_test_id('wellness-dismiss').click(); page.reload(wait_until='networkidle'); page.get_by_test_id('wellness-open').click(); page.get_by_test_id('wellness-dialog').wait_for(state='visible'); assert page.get_by_test_id('wellness-pause').inner_text()=='Resume reminders'
            # Resume locally and require no settings write before the durable stop action.
            page.get_by_test_id('wellness-pause').click(); assert wellness_patches==[]
            # Turn reminders off durably and wait for the exact authoritative UI state.
            page.get_by_test_id('wellness-stop').click(); page.wait_for_function("() => document.querySelector('[data-testid=wellness-message]')?.textContent === 'Reminders are turned off.'")
            # Require one disabling PATCH, no reward UI, and disabled pause/stop controls.
            assert len(wellness_patches)==1 and wellness_patches[0]=={'enabled':False,'revision':4} and page.get_by_test_id('wellness-pause').is_disabled() and page.get_by_test_id('wellness-stop').is_disabled() and 'reward' not in page.get_by_test_id('wellness-dialog').inner_text().lower()
            # Capture the explicit stopped state separately from the opt-in visual matrix.
            game_evidence('after-pass-session-wellness-stopped-en-US-desktop_primary.png','session_wellness',['stopped','summary','every_game_control'],'en-US','desktop_primary')
            # Prove session storage contains only bounded timing state and no player or monetary summary data.
            local_records=page.evaluate("() => Object.fromEntries(Object.entries(sessionStorage).filter(([key]) => key.startsWith('casino.wellness.v1.')))"); assert local_records and all(set(json.loads(value))<= {'lastSlot','paused','intervalMinutes'} for value in local_records.values())
            # Close and remove only this case's deterministic route seams.
            page.get_by_test_id('wellness-dismiss').click(); page.unroute('**/api/v2/me/wellness/summary'); page.unroute('**/api/v2/me/wellness')
        # Execute the permanent hosted browser case under the existing wellness requirements.
        run_case('BR-WELLNESS-001',['WELL-001','WELL-002','TEST-105'],session_wellness_browser)
    # Preserve exact table-game case accounting on non-owning shards.
    else:
        # Advance only the Bingo-through-wellness affinity range.
        skip_browser_affinity('table_games')
    # Run feedback production and its complete Admin consumer chain only on the declared owner.
    if feedback_admin_owner:
        # Install the normal-player session needed by both feedback submission and role-boundary evidence.
        feedback_login=page.request.post(base+'/api/v2/auth/login',data={'email':'demo@example.local','password':'password'})
        # Fail before either producer or consumer can run under an invalid identity.
        if not feedback_login.ok or feedback_login.json().get('ok') is not True: raise AssertionError('feedback/Admin affinity login failed')
        # Mount a canonical English desktop lobby independently from the preceding table-game owner.
        page.set_viewport_size({'width':1920,'height':1080}); page.emulate_media(reduced_motion='no-preference'); page.goto(base,wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS); page.get_by_test_id('shell-locale-select').select_option('en-US')
        # Preserve the stable internal reference created by the player flow for later Admin acceptance.
        feedback_report_reference={'value':''}
        # Define registered-user submission, bilingual layout, image normalization, and retry acceptance. (issue #349)
        def feedback_report_browser():
            # Enumerate the complete governed feedback viewport matrix.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Pin the localized retry copy so controlled server diagnostics never leak into either visible locale.
            retry_messages={'en-US':'The report could not be submitted. Your draft remains open.','ru-RU':'Не удалось отправить отчёт. Черновик остался открытым.'}
            # Use one safe in-memory image for file, preview, and removal evidence.
            png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAI0lEQVR4nGMUqghiIAUwkaSaYVQDcYCJSHVwMKqBGEByKAEA0/YA/Hxc1QQAAAAASUVORK5CYII=')
            # Exercise localized empty, evidence, removal, validation, keyboard, motion, and zoom states everywhere.
            for locale in ('en-US','ru-RU'):
                # Switch through the persistent player-visible locale selector.
                page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                # Capture each governed responsive width from a clean native dialog.
                for viewport_id,viewport in viewports.items():
                    # Apply the exact visual-matrix dimensions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Open one clean draft from the registered-user-only affordance.
                    page.get_by_test_id('report-problem-open').click(); page.get_by_test_id('feedback-dialog').wait_for(state='visible')
                    # Require translated content and both document/dialog horizontal containment.
                    assert 'feedback.' not in page.get_by_test_id('feedback-dialog').inner_text() and page.evaluate("() => { const dialog=document.querySelector('[data-testid=feedback-dialog]'); return document.documentElement.scrollWidth <= window.innerWidth + 1 && dialog.scrollWidth <= dialog.clientWidth + 1; }")
                    # Focus the first governed task control for keyboard evidence.
                    page.get_by_test_id('feedback-category').focus()
                    # Capture the clean, keyboard, and current motion states together because they are concurrently visible.
                    game_evidence(f'after-pass-feedback-empty-{locale}-{viewport_id}.png','feedback_report',['empty','keyboard_focus','reduced_motion'],locale,viewport_id)
                    # Normalize a local screenshot through the real browser controller.
                    page.locator('#report-file-input').set_input_files({'name':'feedback.png','mimeType':'image/png','buffer':png}); page.wait_for_function("() => document.querySelector('[data-testid=feedback-previews] img')")
                    # Capture file/paste/drop contract presentation through the shared normalized evidence state.
                    game_evidence(f'after-pass-feedback-evidence-{locale}-{viewport_id}.png','feedback_report',['file','paste','drop','screenshot_ready'],locale,viewport_id)
                    # Remove the retained in-memory preview through its accessible control.
                    page.locator('[data-testid=feedback-previews] button').click(); assert page.locator('[data-testid=feedback-previews] img').count()==0
                    # Capture the explicit user-controlled removal state.
                    game_evidence(f'after-pass-feedback-removed-{locale}-{viewport_id}.png','feedback_report',['screenshot_removed'],locale,viewport_id)
                    # Trigger native validation without making a network request.
                    page.get_by_test_id('feedback-submit').click(); assert page.get_by_test_id('feedback-summary').evaluate('element => !element.validity.valid')
                    # Capture visible invalid controls under the governed validation state.
                    game_evidence(f'after-pass-feedback-validation-{locale}-{viewport_id}.png','feedback_report',['validation_error'],locale,viewport_id)
                    # Fill a complete disposable draft for controlled retry and terminal visual evidence.
                    page.get_by_test_id('feedback-category').select_option('bug'); page.get_by_test_id('feedback-impact').select_option('minor'); page.get_by_test_id('feedback-summary').fill('Controlled storage retry proof'); page.get_by_test_id('feedback-actual').fill('The controlled test endpoint rejected this attempt.'); page.get_by_test_id('feedback-expected').fill('The draft should remain available for exact retry.')
                    # Record diagnostic boundaries so only this deliberate storage rejection can be consumed.
                    feedback_retry_console_index=len(console_errors); feedback_retry_http_index=len(http_errors); feedback_retry_page_index=len(page_errors)
                    # Intercept only this same-origin route with a fixed storage failure.
                    page.route('**/api/v2/feedback/reports',lambda route: route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"STORAGE_UNAVAILABLE","message":"Report storage is temporarily unavailable"}}'))
                    # Submit and require the dialog to preserve its draft behind exact locale-owned failure copy.
                    page.get_by_test_id('feedback-submit').click(); page.wait_for_function("expected => document.querySelector('#report-message')?.textContent === expected",arg=retry_messages[locale])
                    # Capture the true retryable storage-failure state.
                    game_evidence(f'after-pass-feedback-retry-{locale}-{viewport_id}.png','feedback_report',['retry_storage_failure'],locale,viewport_id)
                    # Replace the failure route with one controlled successful exact replay receipt.
                    page.unroute('**/api/v2/feedback/reports'); page.route('**/api/v2/feedback/reports',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"report_id":"report_visual_only","reference":"RPT-VISUAL01","status":"new","replayed":false}}'))
                    # Retry the unchanged draft and wait for the terminal receipt.
                    page.get_by_test_id('feedback-submit').click(); page.wait_for_function("() => document.querySelector('#report-message')?.textContent.includes('RPT-VISUAL01')")
                    # Capture an honest terminal confirmation for this locale and viewport.
                    game_evidence(f'after-pass-feedback-submitted-{locale}-{viewport_id}.png','feedback_report',['submitted'],locale,viewport_id)
                    # Wait for the native dialog to close after announcement.
                    page.get_by_test_id('feedback-dialog').wait_for(state='hidden',timeout=3000)
                    # Isolate the diagnostics emitted by the one deliberate retryable 503 response.
                    feedback_retry_console=console_errors[feedback_retry_console_index:]; feedback_retry_http=http_errors[feedback_retry_http_index:]; feedback_retry_page=page_errors[feedback_retry_page_index:]
                    # Require exactly the controlled failed-resource observation and no JavaScript failure.
                    assert feedback_retry_page==[] and len(feedback_retry_console)==1 and 'Failed to load resource' in feedback_retry_console[0] and len(feedback_retry_http)==1 and feedback_retry_http[0].startswith('503 ') and feedback_retry_http[0].endswith('/api/v2/feedback/reports'),feedback_retry_console+feedback_retry_page+feedback_retry_http
                    # Restore the real endpoint and remove only the verified controlled diagnostics.
                    page.unroute('**/api/v2/feedback/reports'); del console_errors[feedback_retry_console_index:]; del http_errors[feedback_retry_http_index:]
            # Use the standard desktop-primary zoom proxy at an effective 960 CSS pixels.
            page.set_viewport_size({'width':960,'height':540}); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.get_by_test_id('report-problem-open').click()
            # Require a readable panel width at the 200 percent proxy rather than mere no-overflow.
            assert page.get_by_test_id('feedback-dialog').evaluate('element => element.getBoundingClientRect().width >= 360')
            # Capture the explicit zoom state.
            game_evidence('after-pass-feedback-zoom-200-en-US-desktop_primary.png','feedback_report',['zoom_200'],'en-US','desktop_primary')
            # Close the zoom draft before the real submission.
            page.locator('#report-cancel').click()
            # Restore primary desktop and create one real report for Admin acceptance.
            page.set_viewport_size(viewports['desktop_primary']); page.get_by_test_id('report-problem-open').click()
            # Select controlled category and independently recorded impact.
            page.get_by_test_id('feedback-category').select_option('visual'); page.get_by_test_id('feedback-impact').select_option('difficult')
            # Fill the complete bounded prose contract.
            page.get_by_test_id('feedback-summary').fill('Browser feedback test report'); page.get_by_test_id('feedback-actual').fill('A visual element overlaps its intended region.'); page.get_by_test_id('feedback-expected').fill('The element should remain inside its intended region.')
            # Include one normalized screenshot in the committed report.
            page.locator('#report-file-input').set_input_files({'name':'feedback.png','mimeType':'image/png','buffer':png}); page.wait_for_function("() => document.querySelector('[data-testid=feedback-previews] img')")
            # Submit through the real additive v2 route.
            page.get_by_test_id('feedback-submit').click(); page.wait_for_function("() => /RPT-[A-Z0-9]+/.test(document.querySelector('#report-message')?.textContent || '')")
            # Retain only the internal public reference for the Admin lookup.
            feedback_report_reference['value']=re.search(r'RPT-[A-Z0-9]+',page.locator('#report-message').inner_text()).group(0)
            # Require automatic close after the live-region announcement.
            page.get_by_test_id('feedback-dialog').wait_for(state='hidden',timeout=3000)
        # Execute the player-facing manual-report acceptance case under the unique requirement.
        run_case('BR-FEEDBACK-001',['CORE-027','ADMIN-025','I18N-005','UX-019','TEST-094'],feedback_report_browser)
        # Produce every normal-player Admin-navigation value on the same owning shard as its consumer.
        normal_admin_navigation=collect_normal_admin_navigation()
        # Unpack the bounded two-role authorization values without cross-shard local state.
        normal_admin_nav_results=normal_admin_navigation['results']; admin_nav_viewports=normal_admin_navigation['viewports']; normal_admin_nav_route_restored=normal_admin_navigation['route_restored']; normal_admin_html_result=normal_admin_navigation['html']; normal_admin_js_result=normal_admin_navigation['js']; normal_admin_api_result=normal_admin_navigation['api']
        # Clear only the three expected normal-role 403 observations before Admin coverage continues.
        console_errors.clear(); http_errors.clear()
        # Replace the normal-user browser cookie with an authenticated Admin session.
        admin_browser_login=page.request.post(base+'/api/v2/auth/login',data={'email':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD})
        # Verify the browser context received a successful Admin login response.
        assert admin_browser_login.json()['ok'] is True
        # Load the normal shared shell first so Admin navigation is exercised as a user-visible affordance.
        page.goto(base,wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
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
        page.get_by_test_id('nav-admin').press('Enter'); page.wait_for_url('**/admin'); page.get_by_test_id('admin-tab-audio').wait_for(timeout=WAIT_MS)
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
            # Exercise the production tagged template in the real browser module graph with hostile ordinary text. (CORE-033, SEC-017)
            escaped_probe=page.evaluate("""async () => { const { html }=await import('/core/ui.js'); return String(html`<p>${'<img src=x onerror=alert(1)>&'}</p>`); }""")
            # Require escape-by-default output before inspecting the migrated Admin views.
            assert escaped_probe=='<p>&lt;img src=x onerror=alert(1)&gt;&amp;</p>'
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
            page.get_by_text('Module revisions',exact=True).wait_for(timeout=WAIT_MS)
            # Select the first System table that lists module and revision columns.
            module_table=page.locator('#adminView table').first
            # Require one header plus every canonical module row.
            assert module_table.locator('tr').count()==len(EXPECTED_MODULE_ROWS)+1
            # Reject object coercion and array separators so the migrated table remains byte-shape compatible. (TEST-186)
            assert page.locator('#adminView').evaluate("node => !node.innerHTML.includes('[object Object]') && !node.innerHTML.includes('</tr>,<tr>')")
            # Compare each browser-visible module row with canonical manifest values.
            for expected in EXPECTED_MODULE_ROWS:
                # Require exactly one row containing both the module name and its canonical revision.
                assert module_table.locator('tr').filter(has_text=expected['module']).filter(has_text=expected['revision']).count()==1
        # Execute the mapped Admin dashboard and packaged-release browser regression.
        run_case('BR-ADMIN-001',['ADMIN-001','ADMIN-003','ADMIN-004','ADMIN-010','ADMIN-014','CORE-033','SEC-017','TEST-023','TEST-186'],admin_dashboard_browser)
        # Define responsive diagnostics coverage for nested state, history, tests, and their empty states. (ADMIN-029, TEST-145)
        def admin_diagnostics_browser():
            # Store the exact governed Admin visual matrix.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Bind the deterministic two-field fixture to each authoritative installed locale.
            expected_result_fields={'en-US':'2 result fields','ru-RU':'Полей результата: 2'}
            # Hold the current deterministic response mode for all three diagnostics routes.
            mode={'value':'populated'}
            # Serve nested/flat or empty state data without touching provider files.
            def states_route(route):
                # Select the response from the current visual mode.
                states={'bingo/human':{'path':'games/bingo/human.json','state':{'active_session':{'pattern':'line'}}},'roulette':{'path':'games/roulette.json','state':{'open_bets':[]}}} if mode['value']=='populated' else {}
                # Fulfill the standard success envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'states':states}}))
            # Serve one readable history row or the explicit empty state.
            def history_route(route):
                # Select one contract-shaped row only for the populated mode.
                rows=[{'timestamp':'2026-08-02T00:00:00Z','player_id':'browser-admin','game':'bingo','bet_label':'Line card','bet_type':'card','amount':5,'payout':10,'outcome':'won','balance_after':5005}] if mode['value']=='populated' else []
                # Fulfill the standard success envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'history':rows}}))
            # Serve one bounded result document or the explicit empty state.
            def results_route(route):
                # Select a low-cardinality deterministic test receipt.
                results={'summary':{'passed':3,'failed':0},'source':'exact-head'} if mode['value']=='populated' else {}
                # Fulfill the standard success envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'results':results}}))
            # Install the three deterministic route seams for this one case.
            page.route('**/api/v1/admin/game-states',states_route); page.route('**/api/v1/admin/history?limit=500',history_route); page.route('**/api/v1/admin/test-results',results_route)
            # Guarantee route cleanup even when one governed cell fails.
            try:
                # Exercise both installed locales.
                for locale in ('en-US','ru-RU'):
                    # Switch the shared Admin runtime without persisting the test choice.
                    page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                    # Exercise all four governed viewports.
                    for viewport_id,viewport in viewports.items():
                        # Apply exact visual geometry.
                        page.set_viewport_size(viewport)
                        # Render nested and flat state rows.
                        mode['value']='populated'; page.get_by_test_id('admin-tab-states').click(); page.locator('[data-testid="admin-tab-states"]').wait_for(timeout=WAIT_MS); page.get_by_text('bingo/human',exact=True).wait_for(timeout=WAIT_MS)
                        # Require both state layouts and page containment.
                        assert page.get_by_text('roulette',exact=True).is_visible() and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
                        # Capture nested and legacy state evidence.
                        game_evidence(f'after-pass-admin-diagnostics-states-{locale}-{viewport_id}.png','BR-ADMIN-DIAGNOSTICS-001',['nested_and_flat_states','keyboard_focus'],locale,viewport_id)
                        # Render and capture the state empty contract.
                        mode['value']='empty'; page.get_by_test_id('admin-tab-states').click(); page.get_by_test_id('admin-game-states-empty').wait_for(timeout=WAIT_MS); game_evidence(f'after-pass-admin-diagnostics-states-empty-{locale}-{viewport_id}.png','BR-ADMIN-DIAGNOSTICS-001',['empty_states'],locale,viewport_id)
                        # Render one readable history row.
                        mode['value']='populated'; page.get_by_test_id('admin-tab-history').click(); page.get_by_text('browser-admin',exact=True).wait_for(timeout=WAIT_MS)
                        # Require table copy instead of raw object text.
                        assert page.get_by_text('Line card',exact=True).is_visible()
                        # Capture populated history evidence.
                        game_evidence(f'after-pass-admin-diagnostics-history-{locale}-{viewport_id}.png','BR-ADMIN-DIAGNOSTICS-001',['history_table'],locale,viewport_id)
                        # Render and capture the history empty contract.
                        mode['value']='empty'; page.get_by_test_id('admin-tab-history').click(); page.get_by_test_id('admin-history-empty').wait_for(timeout=WAIT_MS); game_evidence(f'after-pass-admin-diagnostics-history-empty-{locale}-{viewport_id}.png','BR-ADMIN-DIAGNOSTICS-001',['history_empty'],locale,viewport_id)
                        # Render the structured test receipt.
                        mode['value']='populated'; page.get_by_test_id('admin-tab-tests').click(); page.get_by_text(expected_result_fields[locale],exact=True).wait_for(timeout=WAIT_MS)
                        # Capture populated test-result evidence.
                        game_evidence(f'after-pass-admin-diagnostics-tests-{locale}-{viewport_id}.png','BR-ADMIN-DIAGNOSTICS-001',['test_results'],locale,viewport_id)
                        # Render and capture the test-result empty contract.
                        mode['value']='empty'; page.get_by_test_id('admin-tab-tests').click(); page.get_by_test_id('admin-tests-empty').wait_for(timeout=WAIT_MS); game_evidence(f'after-pass-admin-diagnostics-tests-empty-{locale}-{viewport_id}.png','BR-ADMIN-DIAGNOSTICS-001',['test_results_empty'],locale,viewport_id)
            # Remove exactly the routes installed by this case.
            finally:
                # Restore real diagnostic endpoints for later Admin cases.
                page.unroute('**/api/v1/admin/game-states',states_route); page.unroute('**/api/v1/admin/history?limit=500',history_route); page.unroute('**/api/v1/admin/test-results',results_route)
            # Restore default Admin geometry and locale.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }"); page.get_by_test_id('admin-tab-dashboard').click()
        # Execute the governed diagnostics Browser case.
        run_case('BR-ADMIN-DIAGNOSTICS-001',['ADMIN-029','TEST-145'],admin_diagnostics_browser)
        # Define responsive economics coverage for summary, player-positive, zero-wager, detail, and empty states. (ADMIN-030, TEST-146)
        def admin_economics_browser():
            # Store the exact governed Admin visual matrix.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Hold summary mode so the same route can show populated and empty states.
            mode={'value':'populated'}
            # Serve deterministic summary economics under the standard envelope.
            def summary_route(route):
                # Include house-side, player-positive, and zero-wager rows in the populated state.
                games=[{'game':'slots','wagered':100,'returned':92,'events':2,'payout_rate':0.92,'house_edge':0.08,'player_positive':False},{'game':'buggy_game','wagered':100,'returned':150,'events':2,'payout_rate':1.5,'house_edge':-0.5,'player_positive':True},{'game':'credit_only','wagered':0,'returned':10,'events':1,'payout_rate':None,'house_edge':None,'player_positive':False}] if mode['value']=='populated' else []
                # Fulfill the standard summary envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'window':100000,'games':games}}))
            # Serve one deterministic player-positive detail row.
            def detail_route(route):
                # Publish aggregate, type breakdown, and recent evidence.
                detail={'game':'buggy_game','wagered':100,'returned':150,'events':2,'payout_rate':1.5,'house_edge':-0.5,'player_positive':True,'by_transaction_type':[{'transaction_type':'BUGGY_WAGER_DEBIT','count':1,'total':-100},{'transaction_type':'BUGGY_PAYOUT_CREDIT','count':1,'total':150}],'recent':[{'player_id':'browser-admin','transaction_type':'BUGGY_PAYOUT_CREDIT','amount':150}]}
                # Fulfill the standard detail envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':detail}))
            # Install both deterministic economics seams.
            page.route('**/api/v1/admin/economics',summary_route); page.route('**/api/v1/admin/economics/buggy_game',detail_route)
            # Guarantee route cleanup after the governed matrix.
            try:
                # Exercise both installed locales.
                for locale in ('en-US','ru-RU'):
                    # Switch the shared Admin runtime.
                    page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                    # Exercise every governed viewport.
                    for viewport_id,viewport in viewports.items():
                        # Apply exact visual geometry.
                        page.set_viewport_size(viewport)
                        # Render the complete summary.
                        mode['value']='populated'; page.get_by_test_id('admin-tab-economics').click(); page.locator('[data-economics-game="buggy_game"]').wait_for(timeout=WAIT_MS)
                        # Require player-positive and zero-wager formatting plus containment.
                        economics_text=page.get_by_test_id('admin-economics').inner_text(); assert '150.0%' in economics_text and '—' in economics_text and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
                        # Focus the real drill-down control for keyboard evidence.
                        page.locator('[data-economics-game="buggy_game"]').focus()
                        # Capture summary states together.
                        game_evidence(f'after-pass-admin-economics-summary-{locale}-{viewport_id}.png','BR-ADMIN-ECONOMICS-001',['summary','player_positive','zero_wager','keyboard_focus'],locale,viewport_id)
                        # Activate the detail by keyboard and wait for its real renderer.
                        page.locator('[data-economics-game="buggy_game"]').press('Enter'); page.get_by_test_id('admin-economics-detail').wait_for(timeout=WAIT_MS)
                        # Require bounded type and recent evidence.
                        assert page.get_by_text('browser-admin',exact=True).is_visible()
                        # Capture the detail state.
                        game_evidence(f'after-pass-admin-economics-detail-{locale}-{viewport_id}.png','BR-ADMIN-ECONOMICS-001',['detail'],locale,viewport_id)
                        # Render the explicit empty summary.
                        mode['value']='empty'; page.get_by_test_id('admin-tab-economics').click(); page.get_by_test_id('admin-economics-empty').wait_for(timeout=WAIT_MS)
                        # Capture the empty economics state.
                        game_evidence(f'after-pass-admin-economics-empty-{locale}-{viewport_id}.png','BR-ADMIN-ECONOMICS-001',['empty'],locale,viewport_id)
            # Remove exactly the routes installed by this case.
            finally:
                # Restore real economics endpoints for later Admin cases.
                page.unroute('**/api/v1/admin/economics',summary_route); page.unroute('**/api/v1/admin/economics/buggy_game',detail_route)
            # Restore default Admin geometry and locale.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }"); page.get_by_test_id('admin-tab-dashboard').click()
        # Execute the governed economics Browser case.
        run_case('BR-ADMIN-ECONOMICS-001',['ADMIN-030','TEST-146'],admin_economics_browser)
        # Define owner-session policy presentation, clamped persistence, denial, and responsive coverage. (SESSION-009, ADMIN-031, TEST-150)
        def admin_session_policy_browser():
            # Store the exact governed Admin visual matrix.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Hold the provider-shaped policy returned by the deterministic endpoint seam.
            policy={'schema_version':2,'enabled':True,'idle_timeout_minutes':30,'absolute_timeout_hours':12,'admin_stricter':True,'admin_idle_timeout_minutes':15,'warning_minutes':2,'updated_at':'2026-08-09T00:00:00Z','updated_by':'browser-owner'}
            # Hold the provider-shaped live request policy returned beside session controls. (SEC-015, ADMIN-032)
            rate_policy={'schema_version':2,'requests_per_window':1200,'window_seconds':60}
            # Hold whether the next read should model ordinary-Admin denial.
            denied={'value':False}
            # Serve owner reads/writes and one explicit ordinary-Admin forbidden envelope.
            def policy_route(route):
                # Return the standard forbidden envelope for the denial visual state.
                if denied['value']:
                    # Fulfill one canonical 403 response.
                    route.fulfill(status=403,content_type='application/json',body=json.dumps({'ok':False,'error':{'code':'FORBIDDEN','message':'Platform owner role is required'}})); return
                # Apply the same reviewed clamps when the visible owner submits POST.
                if route.request.method=='POST':
                    # Read the submitted JSON body.
                    body=route.request.post_data_json
                    # Clamp all numeric values and preserve a strict boolean.
                    policy.update({'enabled':body.get('enabled') is True,'idle_timeout_minutes':max(1,min(int(body.get('idle_timeout_minutes',policy['idle_timeout_minutes'])),1440)),'absolute_timeout_hours':max(1,min(int(body.get('absolute_timeout_hours',policy['absolute_timeout_hours'])),24)),'admin_idle_timeout_minutes':max(1,min(int(body.get('admin_idle_timeout_minutes',policy['admin_idle_timeout_minutes'])),1440)),'admin_stricter':body.get('admin_stricter') is True,'warning_minutes':max(0,min(int(body.get('warning_minutes',policy['warning_minutes'])),10)),'updated_at':'2026-08-09T00:05:00Z','updated_by':'browser-owner'})
                    # Keep the warning strictly below the clamped idle window, matching provider behavior.
                    policy['warning_minutes']=min(policy['warning_minutes'],max(0,policy['idle_timeout_minutes']-1))
                # Fulfill the owner success envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'settings':policy}}))
            # Serve owner reads and writes for the independently persisted live request policy.
            def rate_policy_route(route):
                # Apply the reviewed live-policy clamps when the owner submits POST.
                if route.request.method=='POST':
                    # Read the submitted JSON body.
                    body=route.request.post_data_json
                    # Clamp both operational fields through the exact backend contract bounds.
                    rate_policy.update({'requests_per_window':max(60,min(int(body.get('requests_per_window',rate_policy['requests_per_window'])),10000)),'window_seconds':max(1,min(int(body.get('window_seconds',rate_policy['window_seconds'])),3600))})
                # Fulfill the owner success envelope.
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'settings':rate_policy}}))
            # Install one route seam covering GET and POST.
            page.route('**/api/v2/admin/session-settings',policy_route)
            # Install the paired live request-policy seam.
            page.route('**/api/v2/admin/rate-limits',rate_policy_route)
            # Guarantee route and expected-diagnostic cleanup.
            try:
                # Exercise both installed locales.
                for locale in ('en-US','ru-RU'):
                    # Switch the shared Admin runtime.
                    page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                    # Exercise every governed viewport.
                    for viewport_id,viewport in viewports.items():
                        # Reset the deterministic policy before this cell.
                        policy.update({'schema_version':2,'enabled':True,'idle_timeout_minutes':30,'absolute_timeout_hours':12,'admin_stricter':True,'admin_idle_timeout_minutes':15,'warning_minutes':2,'updated_at':'2026-08-09T00:00:00Z','updated_by':'browser-owner'}); denied['value']=False
                        # Reset the independent live request policy before this cell.
                        rate_policy.update({'schema_version':2,'requests_per_window':1200,'window_seconds':60})
                        # Apply exact visual geometry and render the owner view.
                        page.set_viewport_size(viewport); page.get_by_test_id('admin-tab-sessions').click(); page.wait_for_function("""() => document.querySelector('[data-testid=\"admin-sessions-enabled\"]')?.checked === true && document.querySelector('[data-testid=\"admin-sessions-idle\"]')?.value === '30' && document.querySelector('[data-testid=\"admin-sessions-absolute\"]')?.value === '12' && document.querySelector('[data-testid=\"admin-sessions-warning\"]')?.value === '2' && document.querySelector('[data-testid=\"admin-sessions-admin-idle\"]')?.value === '15' && document.querySelector('[data-testid=\"admin-sessions-admin-stricter\"]')?.checked === true && document.querySelector('[data-testid=\"admin-sessions-provenance\"]')?.textContent?.trim() && document.querySelector('[data-testid=\"admin-rate-limit-requests\"]')?.value === '1200' && document.querySelector('[data-testid=\"admin-rate-limit-window\"]')?.value === '60'""",timeout=WAIT_MS)
                        # Require the complete owner policy to remain contained.
                        assert page.get_by_test_id('admin-sessions-idle').input_value()=='30' and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
                        # Focus the real save action for keyboard evidence.
                        page.get_by_test_id('admin-save-sessions').focus()
                        # Capture the owner policy and keyboard state.
                        game_evidence(f'after-pass-admin-session-policy-owner-{locale}-{viewport_id}.png','BR-ADMIN-SESSION-POLICY-001',['owner_policy','keyboard_focus'],locale,viewport_id)
                        # Submit values outside reviewed bounds through the real UI control.
                        page.get_by_test_id('admin-sessions-enabled').uncheck(); page.get_by_test_id('admin-sessions-idle').fill('0'); page.get_by_test_id('admin-sessions-absolute').fill('99'); page.get_by_test_id('admin-sessions-warning').fill('99'); page.get_by_test_id('admin-sessions-admin-idle').fill('5000'); page.get_by_test_id('admin-sessions-admin-stricter').uncheck()
                        # Bind the real Save action to completion of its exact owner-policy POST.
                        with page.expect_response(lambda response: response.url.endswith('/api/v2/admin/session-settings') and response.request.method=='POST',timeout=WAIT_MS):
                            # Trigger the asynchronous save while its response observer is armed.
                            page.get_by_test_id('admin-save-sessions').click()
                        # Rerender from the persisted deterministic response.
                        page.get_by_test_id('admin-tab-sessions').click()
                        # Wait for all exact clamped controls instead of the already-visible stale panel.
                        page.wait_for_function("""() => document.querySelector('[data-testid=\"admin-sessions-enabled\"]')?.checked === false && document.querySelector('[data-testid=\"admin-sessions-idle\"]')?.value === '1' && document.querySelector('[data-testid=\"admin-sessions-absolute\"]')?.value === '24' && document.querySelector('[data-testid=\"admin-sessions-warning\"]')?.value === '0' && document.querySelector('[data-testid=\"admin-sessions-admin-idle\"]')?.value === '1440' && document.querySelector('[data-testid=\"admin-sessions-admin-stricter\"]')?.checked === false && document.querySelector('[data-testid=\"admin-sessions-provenance\"]')?.textContent?.includes('browser-owner')""",timeout=WAIT_MS)
                        # Require exact clamped values and boolean persistence.
                        assert not page.get_by_test_id('admin-sessions-enabled').is_checked() and page.get_by_test_id('admin-sessions-idle').input_value()=='1' and page.get_by_test_id('admin-sessions-absolute').input_value()=='24' and page.get_by_test_id('admin-sessions-warning').input_value()=='0' and page.get_by_test_id('admin-sessions-admin-idle').input_value()=='1440' and not page.get_by_test_id('admin-sessions-admin-stricter').is_checked()
                        # Capture clamped and saved policy evidence.
                        game_evidence(f'after-pass-admin-session-policy-saved-{locale}-{viewport_id}.png','BR-ADMIN-SESSION-POLICY-001',['clamped_values','saved'],locale,viewport_id)
                        # Submit out-of-range live rate controls through the real owner UI.
                        page.get_by_test_id('admin-rate-limit-requests').fill('50000'); page.get_by_test_id('admin-rate-limit-window').fill('0')
                        # Bind the real Save action to completion of its exact rate-policy POST.
                        with page.expect_response(lambda response: response.url.endswith('/api/v2/admin/rate-limits') and response.request.method=='POST',timeout=WAIT_MS):
                            # Trigger the independent live rate-policy save.
                            page.get_by_test_id('admin-save-rate-limits').click()
                        # Rerender from both persisted policy responses.
                        page.get_by_test_id('admin-tab-sessions').click()
                        # Wait for exact backend-equivalent clamps rather than accepting stale controls.
                        page.wait_for_function("""() => document.querySelector('[data-testid=\"admin-rate-limit-requests\"]')?.value === '10000' && document.querySelector('[data-testid=\"admin-rate-limit-window\"]')?.value === '1'""",timeout=WAIT_MS)
                        # Require the live policy to display its exact committed values.
                        assert page.get_by_test_id('admin-rate-limit-requests').input_value()=='10000' and page.get_by_test_id('admin-rate-limit-window').input_value()=='1'
                # Record diagnostics before modeling one canonical ordinary-Admin denial.
                denial_http_index=len(http_errors); denial_console_index=len(console_errors); denial_page_index=len(page_errors)
                # Return the canonical forbidden envelope on the next read.
                denied['value']=True; page.get_by_test_id('admin-tab-sessions').click(); page.get_by_test_id('admin-load-error').wait_for(timeout=WAIT_MS)
                # Isolate diagnostics emitted by the deliberate forbidden response.
                denial_http=http_errors[denial_http_index:]; denial_console=console_errors[denial_console_index:]; denial_pages=page_errors[denial_page_index:]
                # Require one exact forbidden response and no JavaScript exception.
                assert denial_pages==[] and len(denial_http)==1 and denial_http[0].startswith('403 ') and denial_http[0].endswith('/api/v2/admin/session-settings'),denial_pages+denial_http
                # Allow only the browser's standard failed-resource console message for the controlled 403.
                assert len(denial_console)<=1 and all('Failed to load resource' in message for message in denial_console),denial_console
                # Capture the non-secret ordinary-Admin denial presentation.
                game_evidence('after-pass-admin-session-policy-denied-en-US-desktop_primary.png','BR-ADMIN-SESSION-POLICY-001',['ordinary_admin_denied'],'en-US','desktop_primary')
                # Remove only diagnostics caused by the controlled 403.
                del http_errors[denial_http_index:]; del console_errors[denial_console_index:]
            # Remove exactly the route installed by this case.
            finally:
                # Restore the real owner-only endpoint.
                page.unroute('**/api/v2/admin/session-settings',policy_route)
                # Restore the real owner-only live request-policy endpoint.
                page.unroute('**/api/v2/admin/rate-limits',rate_policy_route)
            # Restore default Admin geometry, locale, and Dashboard.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }"); page.get_by_test_id('admin-tab-dashboard').click()
        # Execute the governed owner-session policy Browser case.
        run_case('BR-ADMIN-SESSION-POLICY-001',['SESSION-009','SESSION-010','SESSION-011','SESSION-012','ADMIN-031','ADMIN-034','SEC-015','ADMIN-032','TEST-150','TEST-156','TEST-158'],admin_session_policy_browser)
        # Define the localized Admin ledger-label and responsive evidence regression. (issue #74)
        def admin_ledger_labels_browser():
            # Store the exact governed Admin viewports required by the visual matrix.
            admin_ledger_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Exercise both installed Admin locales independently.
            for admin_ledger_locale in ('en-US','ru-RU'):
                # Switch the shared runtime and let the active tab rerender in the requested locale.
                page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",admin_ledger_locale)
                # Inspect Dashboard and full Ledger at every governed viewport.
                for admin_ledger_viewport_id,admin_ledger_viewport in admin_ledger_viewports.items():
                    # Apply exact visual-matrix geometry before rendering either ledger surface.
                    page.set_viewport_size(admin_ledger_viewport)
                    # Open Dashboard and wait for at least one real ledger event from the preceding browser actions.
                    page.locator('[data-tab="dashboard"]').click(); page.locator('[data-testid="admin-ledger-event"]').first.wait_for(timeout=WAIT_MS)
                    # Read every visible localized Dashboard action label.
                    dashboard_labels=page.locator('[data-testid="admin-ledger-event"]').all_inner_texts()
                    # Require readable labels with no raw enum separators or source-style all-caps action phrase.
                    assert dashboard_labels and all('_' not in label and not label.replace('·','').replace(' ','').isupper() for label in dashboard_labels),(admin_ledger_locale,admin_ledger_viewport_id,dashboard_labels)
                    # Require Russian action copy to contain Cyrillic rather than English fallback labels.
                    if admin_ledger_locale=='ru-RU': assert all(re.search(r'[А-Яа-яЁё]',label) for label in dashboard_labels),(admin_ledger_viewport_id,dashboard_labels)
                    # Require the complete page to remain contained at the changed Dashboard table.
                    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),(admin_ledger_locale,admin_ledger_viewport_id,'dashboard')
                    # Capture exact-head Dashboard label evidence for human EN/RU review.
                    game_evidence(f'after-pass-admin-ledger-dashboard-{admin_ledger_locale}-{admin_ledger_viewport_id}.png','admin',['dashboard'],admin_ledger_locale,admin_ledger_viewport_id)
                    # Open the complete Ledger and wait for its independently rendered localized action cells.
                    page.locator('[data-tab="ledger"]').click(); page.locator('[data-testid="admin-ledger-event"]').first.wait_for(timeout=WAIT_MS)
                    # Read every visible localized full-ledger action label.
                    ledger_labels=page.locator('[data-testid="admin-ledger-event"]').all_inner_texts()
                    # Require the full audit surface to enforce the same raw-enum and casing boundary.
                    assert ledger_labels and all('_' not in label and not label.replace('·','').replace(' ','').isupper() for label in ledger_labels),(admin_ledger_locale,admin_ledger_viewport_id,ledger_labels)
                    # Require Russian full-ledger actions to remain locale-backed.
                    if admin_ledger_locale=='ru-RU': assert all(re.search(r'[А-Яа-яЁё]',label) for label in ledger_labels),(admin_ledger_viewport_id,ledger_labels)
                    # Require the changed full Ledger page to remain contained at every governed viewport.
                    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),(admin_ledger_locale,admin_ledger_viewport_id,'ledger')
                    # Capture exact-head full Ledger evidence for human EN/RU review.
                    game_evidence(f'after-pass-admin-ledger-full-{admin_ledger_locale}-{admin_ledger_viewport_id}.png','admin',['ledger'],admin_ledger_locale,admin_ledger_viewport_id)
            # Restore the suite's default Admin locale, viewport, and Dashboard state.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }"); page.locator('[data-tab="dashboard"]').click()
        # Execute the exact-head localized Admin event-label and sixteen-image acceptance case.
        run_case('BR-ADMIN-LEDGER-LABELS-001',['ADMIN-027','TEST-132'],admin_ledger_labels_browser)
        # Define Admin inbox, evidence, triage, manual draft, export, and responsive acceptance. (issue #349)
        def admin_feedback_browser():
            # Open the dedicated Admin feedback surface and wait for its attachment-free list.
            page.get_by_test_id('admin-tab-feedback').click(); page.get_by_test_id('admin-feedback-inbox').wait_for(timeout=WAIT_MS)
            # Locate exactly the report created by the authenticated player flow.
            report_button=page.locator('[data-feedback-id]').filter(has_text=feedback_report_reference['value']); assert report_button.count()==1
            # Capture the exact report identity used to bind every manual-draft response.
            feedback_report_id=report_button.get_attribute('data-feedback-id'); assert isinstance(feedback_report_id,str) and feedback_report_id.startswith('report_')
            # Open canonical detail and require one normalized Admin-only screenshot.
            report_button.click(); page.get_by_test_id('admin-feedback-detail').wait_for(timeout=WAIT_MS); assert page.locator('.feedback-evidence img').count()==1
            # Apply controlled P1 triage, bounded notes, and a link that canonically commits linked status.
            page.locator('#feedback-detail-priority').select_option('P1'); page.locator('#feedback-detail-status').select_option('triaged'); page.locator('#feedback-admin-notes').fill('Confirmed by exact-head browser acceptance.'); page.locator('#feedback-github-url').fill('https://github.com/andreivorobiev/virtual-casino-simulator/issues/349'); save_admin_feedback_triage(page,feedback_report_id,'P1','linked')
            # Prepare the manual-only reporter-free draft without an external publication control.
            prepare_admin_feedback_draft(page,feedback_report_id)
            # Require governed labels, privacy-safe content, and no automatic GitHub route or popup button.
            draft_text=page.locator('#feedback-github-draft').inner_text(); assert 'P1' in draft_text and '@' not in draft_text and 'password' not in draft_text.lower() and page.locator('#feedback-open-github').count()==0
            # Exercise both installed Admin locales at every governed viewport.
            for locale in ('en-US','ru-RU'):
                # Switch through the shared Admin locale runtime.
                page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                # Reopen the feedback inbox after locale rerender.
                page.get_by_test_id('admin-tab-feedback').click(); page.get_by_test_id('admin-feedback-inbox').wait_for(timeout=WAIT_MS)
                # Apply and prove the independent impact filter before responsive evidence.
                page.locator('#feedback-impact-filter').select_option('difficult'); page.locator('#feedback-apply-filters').click(); page.get_by_test_id('admin-feedback-inbox').wait_for(timeout=WAIT_MS)
                # Check every governed Admin layout.
                for viewport_id,viewport in {'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}.items():
                    # Apply exact visual-matrix geometry.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require translated page containment while allowing only the named table region to scroll.
                    diagnostics=page.evaluate("""() => { const inbox=document.querySelector('[data-testid="admin-feedback-inbox"]'); return {text:inbox?.innerText || '',page:document.documentElement.scrollWidth,viewport:innerWidth}; }"""); assert 'feedback.' not in diagnostics['text'] and diagnostics['page']<=diagnostics['viewport']+1,(locale,viewport_id,diagnostics)
                    # Capture the localized filtered inbox and keyboard-scroll surface.
                    game_evidence(f'after-pass-admin-feedback-inbox-{locale}-{viewport_id}.png','admin',['feedback_inbox','feedback_filtered','feedback_keyboard_focus','feedback_reduced_motion'],locale,viewport_id)
                    # Open the retained report from this exact localized responsive list.
                    page.locator('[data-feedback-id]').filter(has_text=feedback_report_reference['value']).click(); page.get_by_test_id('admin-feedback-detail').wait_for(timeout=WAIT_MS)
                    # Capture the true linked triage and evidence-detail state.
                    game_evidence(f'after-pass-admin-feedback-detail-{locale}-{viewport_id}.png','admin',['feedback_detail','feedback_triaged','feedback_manual_linked','feedback_export'],locale,viewport_id)
                    # Prepare the server-sanitized manual-only draft in this locale and viewport.
                    prepare_admin_feedback_draft(page,feedback_report_id)
                    # Capture the manual draft with no external publication action.
                    game_evidence(f'after-pass-admin-feedback-manual-draft-{locale}-{viewport_id}.png','admin',['feedback_manual_draft'],locale,viewport_id)
                    # Return to the exact filtered inbox for the next viewport.
                    page.locator('#feedback-back').click(); page.get_by_test_id('admin-feedback-inbox').wait_for(timeout=WAIT_MS)
            # Restore one detail and capture triage/manual-draft states at primary desktop.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }")
            # Reopen the selected report from the filtered list.
            page.locator('[data-feedback-id]').filter(has_text=feedback_report_reference['value']).click(); page.get_by_test_id('admin-feedback-detail').wait_for(timeout=WAIT_MS); prepare_admin_feedback_draft(page,feedback_report_id)
            # Download the metadata-only export through the real additive v2 route.
            with page.expect_download():
                # Activate the explicit Admin export control.
                page.locator('#feedback-export').click()
            # Use the desktop-primary 200 percent proxy and require a readable detail width.
            page.set_viewport_size({'width':960,'height':540}); assert page.get_by_test_id('admin-feedback-detail').evaluate('element => element.getBoundingClientRect().width >= 360')
            # Capture the governed Admin zoom proxy.
            game_evidence('after-pass-admin-feedback-zoom-200-en-US-desktop_primary.png','admin',['feedback_zoom_200'],'en-US','desktop_primary')
            # Restore primary desktop before controlled storage-error evidence.
            page.set_viewport_size({'width':1920,'height':1080})
            # Record diagnostic boundaries so only the deliberate Admin storage rejection can be consumed.
            feedback_admin_console_index=len(console_errors); feedback_admin_http_index=len(http_errors); feedback_admin_page_index=len(page_errors)
            # Match only the Admin list path with an optional query so report detail and export calls stay real.
            feedback_list_pattern=re.compile(r'/api/v2/admin/feedback/reports(?:\?.*)?$'); page.route(feedback_list_pattern,lambda route: route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"STORAGE_UNAVAILABLE","message":"Problem-report storage requires recovery"}}'))
            # Trigger the active tab's normal refresh path and prove the controlled list request occurred.
            with page.expect_request(feedback_list_pattern): page.locator('#refreshAdmin').click()
            # Require the shared localized Admin error boundary after the injected storage failure.
            page.get_by_test_id('admin-load-error').wait_for(timeout=WAIT_MS)
            # Capture the localized storage-recovery failure without raw state.
            game_evidence('after-pass-admin-feedback-storage-error-en-US-desktop_primary.png','admin',['feedback_storage_error'],'en-US','desktop_primary')
            # Isolate the diagnostics emitted by the one deliberate Admin 503 response.
            feedback_admin_console=console_errors[feedback_admin_console_index:]; feedback_admin_http=http_errors[feedback_admin_http_index:]; feedback_admin_page=page_errors[feedback_admin_page_index:]
            # Require exactly the controlled list rejection and no unhandled JavaScript failure.
            assert feedback_admin_page==[] and len(feedback_admin_console)==1 and 'Failed to load resource' in feedback_admin_console[0] and len(feedback_admin_http)==1 and feedback_admin_http[0].startswith('503 ') and feedback_list_pattern.search(feedback_admin_http[0]),feedback_admin_console+feedback_admin_page+feedback_admin_http
            # Restore the exact filtered-list route and remove only its verified diagnostics.
            page.unroute(feedback_list_pattern); del console_errors[feedback_admin_console_index:]; del http_errors[feedback_admin_http_index:]
            # Restore the suite default for subsequent Admin cases.
            page.set_viewport_size({'width':1920,'height':1080})
        # Execute Admin manual-only triage and evidence acceptance under TEST-094.
        run_case('BR-ADMIN-FEEDBACK-001',['ADMIN-025','I18N-005','UX-019','TEST-094'],admin_feedback_browser)
        # Define Admin-only OAuth diagnostics, isolation from Operations, and visual evidence.
        def admin_oauth_browser():
            # Define every governed Admin viewport from the visual matrix.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Exercise provider diagnostics in both installed Admin locales.
            for locale in ('en-US','ru-RU'):
                # Switch locale without persisting a preference outside this disposable test copy.
                page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }", locale)
                # Open Operations because OAuth diagnostics render as an independent card on that surface.
                page.get_by_test_id('admin-tab-operations').click(); page.get_by_test_id('admin-operations-live').wait_for(timeout=WAIT_MS); page.get_by_test_id('admin-oauth-diagnostics').wait_for(timeout=WAIT_MS)
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
                page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-operations-live').wait_for(timeout=WAIT_MS); page.get_by_test_id('admin-oauth-diagnostics-unavailable').wait_for(timeout=WAIT_MS)
                # Remove the focused failure shim before the next locale or Operations acceptance case.
                page.unroute('**/api/v2/admin/oauth/providers')
                # Refresh once to restore real backend provider diagnostics.
                page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-oauth-diagnostics').wait_for(timeout=WAIT_MS)
            # Restore primary desktop dimensions and English for the broader Operations suite.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }")
        # Record Admin authorization presentation, runtime-disabled status, isolation, and evidence.
        run_case('BR-ADMIN-OAUTH-001',['OAUTH-002','OAUTH-006','TEST-045'],admin_oauth_browser)
        # Define secret-free transactional-mail diagnostics across all governed locales, viewports, and states. (issue #330)
        def admin_mail_browser():
            # Define all four visual-matrix viewports, including the narrow mobile Admin layout.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Build the stable aggregate delivery shape required by the v2 contract.
            empty_summary={'sending':0,'sent':0,'retry_wait':0,'failed':0,'suppressed':0,'uncertain':0,'disabled':0,'release_held':0,'misconfigured':0}
            # Enumerate the exact matrix rows and low-cardinality diagnostic payloads.
            scenarios=[
                # Prove the intentionally disabled repository default.
                ('operations_mail_disabled','disabled','disabled',['feature_disabled'],0),
                # Prove actionable incomplete configuration without secrets.
                ('operations_mail_misconfigured','misconfigured','postmark',['sender_identity_invalid','provider_credential_missing'],0),
                # Prove complete configuration remains visibly held from provider/network release.
                ('operations_mail_release_held','release_held','postmark',['network_release_held'],0),
                # Prove de-identified suppression aggregates without recipient rows.
                ('operations_mail_suppression_summary','release_held','postmark',['network_release_held'],7),
            ]
            # Exercise each state in both governed Admin locales.
            for locale in ('en-US','ru-RU'):
                # Switch locale without modifying an external browser preference.
                page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }", locale)
                # Render each contract-published acceptance state independently.
                for matrix_state,status,provider,reasons,suppressed_count in scenarios:
                    # Clone the aggregate summary so the suppression scenario can carry one bounded count.
                    summary=dict(empty_summary); summary['suppressed']=suppressed_count
                    # Publish only the documented response envelope and low-cardinality values.
                    payload={'ok':True,'data':{'schema_version':'transactional-mail-readiness.v2','provider':provider,'status':status,'checks':{'feature_enabled':status!='disabled','network_release_enabled':False,'canonical_origin_https':status in ('release_held','ready'),'sender_identity_configured':status in ('release_held','ready'),'provider_credential_configured':status in ('release_held','ready'),'digest_key_configured':True},'reasons':reasons,'delivery_summary':summary,'suppressed_recipients':suppressed_count}}
                    # Intercept only the Admin mail diagnostic while Operations and OAuth use the real backend.
                    page.route('**/api/v2/admin/mail/readiness',lambda route,_request,body=json.dumps(payload): route.fulfill(status=200,content_type='application/json',body=body))
                    # Refresh the active Operations surface and wait for the exact explicit state card.
                    page.get_by_test_id('admin-tab-operations').click(); page.get_by_test_id(f'admin-mail-{status}').wait_for(timeout=WAIT_MS)
                    # Wait for the repeated release-held suppression scenario to render its new aggregate before evidence.
                    if matrix_state=='operations_mail_suppression_summary': page.wait_for_function("expected => document.querySelector('[data-testid=\"admin-mail-suppression-summary\"]')?.textContent.includes(expected)",arg=str(suppressed_count))
                    # Read the rendered card once for data-minimization assertions.
                    visible_mail=page.get_by_test_id(f'admin-mail-{status}').inner_text()
                    # Require no environment key, recipient syntax, tokened link, credential, or raw provider response.
                    assert 'CASINO_' not in visible_mail and '@' not in visible_mail and 'token=' not in visible_mail.lower() and '://' not in visible_mail
                    # Require the suppression scenario to expose only its localized aggregate count.
                    if matrix_state=='operations_mail_suppression_summary': assert '7' in page.get_by_test_id('admin-mail-suppression-summary').inner_text()
                    # Capture exact after-pass evidence for every locale and governed viewport.
                    for viewport_id,viewport in viewports.items():
                        # Resize to the exact matrix dimensions before containment checks.
                        page.set_viewport_size(viewport); page.wait_for_timeout(150)
                        # Bring the independent mail card into the bounded Admin scroll region.
                        page.get_by_test_id(f'admin-mail-{status}').scroll_into_view_if_needed()
                        # Require document, Admin content, and card containment without horizontal overflow.
                        assert page.evaluate("status => { const content=document.querySelector('.admin-content'); const card=document.querySelector(`[data-testid=\"admin-mail-${status}\"]`); return document.documentElement.scrollWidth <= window.innerWidth + 1 && content.scrollWidth <= content.clientWidth + 1 && card.scrollWidth <= card.clientWidth + 1; }",status)
                        # Write a paired after-pass screenshot and sidecar for the exact matrix row.
                        game_evidence(f'after-pass-admin-mail-{matrix_state}-{locale}-{viewport_id}.png','admin',[matrix_state],locale,viewport_id)
                    # Remove the focused response before installing the next state.
                    page.unroute('**/api/v2/admin/mail/readiness')
            # Restore the real disabled backend response and primary desktop dimensions.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n = await import('/core/i18n.js'); await i18n.setLocale('en-US', { persistLocal: false }); }"); page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-mail-disabled').wait_for(timeout=WAIT_MS)
        # Record dual-gate states, secret-free aggregate diagnostics, responsive containment, and evidence.
        run_case('BR-ADMIN-MAIL-001',['MAIL-002','MAIL-003','MAIL-005','TEST-090'],admin_mail_browser)
        # Define masked Admin invitation and account-free redemption evidence across every governed locale and viewport. (issue #332)
        def invitation_browser():
            # Define all four visual-matrix viewports used by both invitation surfaces.
            viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Build one complete masked lifecycle row containing no raw recipient or credential material.
            pending_row={'invitation_id':'invite_visual_pending','recipient_hint':'i***@e***.invalid','status':'pending','delivery_status':'sent','locale':'en-US','created_at':'2032-02-03T04:05:06.000Z','updated_at':'2032-02-03T04:05:06.000Z','expires_at':'2032-02-10T04:05:06.000Z','redeemed_at':None,'revoked_at':None,'invited_by':'user_admin_visual','history':[]}
            # Derive one terminal row without adding recipient or account identifiers.
            redeemed_row={**pending_row,'invitation_id':'invite_visual_redeemed','status':'redeemed','redeemed_at':'2032-02-04T04:05:06.000Z','updated_at':'2032-02-04T04:05:06.000Z'}
            # Enumerate exact Admin matrix states and contract-shaped secret-free responses.
            scenarios=[
                ('invitations_disabled',{'enabled':False,'redemption_enabled':False,'mail_status':'disabled','recovery_required':0,'invitations':[]},'admin-invitations-disabled'),
                ('invitations_release_held',{'enabled':True,'redemption_enabled':False,'mail_status':'release_held','recovery_required':0,'invitations':[]},'admin-invitations-release-held'),
                ('invitations_empty',{'enabled':True,'redemption_enabled':True,'mail_status':'ready','recovery_required':0,'invitations':[]},'admin-invitations-ready'),
                ('invitations_pending',{'enabled':True,'redemption_enabled':True,'mail_status':'ready','recovery_required':0,'invitations':[pending_row]},'admin-invitations-ready'),
                ('invitations_redeemed',{'enabled':True,'redemption_enabled':True,'mail_status':'ready','recovery_required':0,'invitations':[redeemed_row]},'admin-invitations-ready'),
            ]
            # Exercise every Admin invitation state in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch locale through the same runtime used by the visible Admin selector.
                page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }",locale)
                # Render each exact contract response independently.
                for matrix_state,data,test_id in scenarios:
                    # Wrap the safe data in the standard success envelope.
                    payload={'ok':True,'data':data}
                    # Intercept only the invitation list endpoint while all other Admin APIs remain real.
                    page.route('**/api/v2/admin/invitations?limit=100',lambda route,_request,body=json.dumps(payload): route.fulfill(status=200,content_type='application/json',body=body))
                    # Open the dedicated tab and wait for the exact readiness card.
                    page.get_by_test_id('admin-tab-invitations').click(); page.get_by_test_id(test_id).wait_for(timeout=WAIT_MS)
                    # Require only masked recipient display and no secret-bearing URL or environment label.
                    visible_invitation=page.get_by_test_id('admin-invitation-list').inner_text(); assert 'i***@e***.invalid' in visible_invitation or not data['invitations']; assert 'CASINO_' not in visible_invitation and 'token=' not in visible_invitation.lower() and '://' not in visible_invitation and 'invitee@' not in visible_invitation
                    # Capture every state at all four governed viewports with containment checks.
                    for viewport_id,viewport in viewports.items():
                        # Resize to the exact matrix dimensions.
                        page.set_viewport_size(viewport); page.wait_for_timeout(120)
                        # Bring the lifecycle region into view inside the Admin scroll surface.
                        page.get_by_test_id('admin-invitation-list').scroll_into_view_if_needed()
                        # Measure page containment plus the bounded lifecycle region's accessibility and scroll ownership.
                        invitation_geometry=page.evaluate("() => { const content=document.querySelector('.admin-content'); const card=document.querySelector('[data-testid=\"admin-invitation-list\"]'); const contentBox=content.getBoundingClientRect(); const cardBox=card.getBoundingClientRect(); const style=getComputedStyle(card); return { viewport:innerWidth, documentScrollWidth:document.documentElement.scrollWidth, contentClientWidth:content.clientWidth, contentScrollWidth:content.scrollWidth, contentBox:contentBox.toJSON(), cardClientWidth:card.clientWidth, cardScrollWidth:card.scrollWidth, cardBox:cardBox.toJSON(), overflowX:style.overflowX, role:card.getAttribute('role'), tabIndex:card.tabIndex, label:card.getAttribute('aria-label') }; }")
                        # Require no page/content overflow while allowing only the named card to own an intentional table scroll.
                        assert invitation_geometry['documentScrollWidth'] <= invitation_geometry['viewport'] + 1 and invitation_geometry['contentScrollWidth'] <= invitation_geometry['contentClientWidth'] + 1 and invitation_geometry['cardBox']['left'] >= invitation_geometry['contentBox']['left'] - 1 and invitation_geometry['cardBox']['right'] <= invitation_geometry['contentBox']['right'] + 1 and invitation_geometry['role']=='region' and invitation_geometry['tabIndex']==0 and invitation_geometry['label'] and (invitation_geometry['cardScrollWidth'] <= invitation_geometry['cardClientWidth'] + 1 or invitation_geometry['overflowX'] in ('auto','scroll')), {'state':matrix_state,'locale':locale,'viewport':viewport_id,'geometry':invitation_geometry}
                        # Capture exact after-pass evidence for this state, locale, and viewport.
                        game_evidence(f'after-pass-admin-{matrix_state}-{locale}-{viewport_id}.png','admin',[matrix_state],locale,viewport_id)
                        # Prove the populated mobile lifecycle table responds to keyboard scrolling without widening the page.
                        if matrix_state=='invitations_pending' and viewport_id=='mobile':
                            # Focus the semantic region before issuing native horizontal navigation keys.
                            page.get_by_test_id('admin-invitation-list').focus()
                            # Advance the native scroll position through keyboard input rather than script-only movement.
                            for _ in range(12): page.keyboard.press('ArrowRight')
                            # Wait for Chromium to commit the asynchronous native scroll after the keyboard events.
                            page.wait_for_function("() => document.querySelector('[data-testid=\"admin-invitation-list\"]')?.scrollLeft > 0",timeout=2000)
                            # Require visible focus, actual horizontal movement, and continued page containment.
                            assert page.evaluate("() => { const card=document.querySelector('[data-testid=\"admin-invitation-list\"]'); return document.activeElement===card && card.scrollLeft>0 && document.documentElement.scrollWidth<=innerWidth+1; }")
                            # Capture the explicit keyboard-scroll matrix state with masked data only.
                            game_evidence(f'after-pass-admin-invitations-keyboard-scroll-{locale}-mobile.png','admin',['invitations_keyboard_scroll'],locale,'mobile')
                            # Restore the region to its leading edge before later evidence.
                            page.evaluate("() => { document.querySelector('[data-testid=\"admin-invitation-list\"]').scrollLeft=0; }")
                            # Capture the complete mobile region under reduced-motion preference.
                            page.emulate_media(reduced_motion='reduce'); game_evidence(f'after-pass-admin-invitations-reduced-motion-{locale}-mobile.png','admin',['invitations_reduced_motion'],locale,'mobile'); page.emulate_media(reduced_motion='no-preference')
                            # Apply the repository's 200-percent content-zoom proxy and wait for responsive reflow.
                            page.set_viewport_size(viewports['desktop_primary']); page.evaluate("() => { document.body.style.zoom='200%'; document.body.style.width='100%'; }"); page.wait_for_timeout(100)
                            # Measure the zoomed shell, header, content, and intentional sidebar/list scroll regions.
                            zoom_geometry=page.evaluate("() => { const shell=document.querySelector('.admin-shell'); const sidebar=document.querySelector('.admin-sidebar'); const top=document.querySelector('.admin-top'); const content=document.querySelector('.admin-content'); const list=document.querySelector('[data-testid=\"admin-invitation-list\"]'); return { viewport:innerWidth, documentScrollWidth:document.documentElement.scrollWidth, bodyScrollWidth:document.body.scrollWidth, shellClientWidth:shell.clientWidth, shellScrollWidth:shell.scrollWidth, sidebarClientWidth:sidebar.clientWidth, sidebarScrollWidth:sidebar.scrollWidth, topClientWidth:top.clientWidth, topScrollWidth:top.scrollWidth, contentClientWidth:content.clientWidth, contentScrollWidth:content.scrollWidth, listClientWidth:list.clientWidth, listScrollWidth:list.scrollWidth }; }")
                            # Require the page, shell, header, and content to remain contained while named regions own any internal scroll.
                            assert zoom_geometry['documentScrollWidth']<=zoom_geometry['viewport']+1 and zoom_geometry['bodyScrollWidth']<=zoom_geometry['viewport']+1 and zoom_geometry['shellScrollWidth']<=zoom_geometry['shellClientWidth']+1 and zoom_geometry['topScrollWidth']<=zoom_geometry['topClientWidth']+1 and zoom_geometry['contentScrollWidth']<=zoom_geometry['contentClientWidth']+1 and zoom_geometry['sidebarScrollWidth']>=zoom_geometry['sidebarClientWidth'] and zoom_geometry['listScrollWidth']>=zoom_geometry['listClientWidth'] and zoom_geometry['topClientWidth']>=320 and zoom_geometry['contentClientWidth']>=320 and zoom_geometry['listClientWidth']>=280, {'locale':locale,'viewport':'desktop_primary','zoom':200,'geometry':zoom_geometry}
                            # Capture the explicit invitation zoom state before restoring normal scale.
                            game_evidence(f'after-pass-admin-invitations-zoom-200-{locale}-desktop_primary.png','admin',['invitations_zoom_200'],locale,'desktop_primary'); page.evaluate("() => { document.body.style.zoom=''; document.body.style.width=''; }")
                    # Remove the focused response before the next state.
                    page.unroute('**/api/v2/admin/invitations?limit=100')
                # Publish one standard API error to prove a bounded localized Admin recovery state.
                page.route('**/api/v2/admin/invitations?limit=100',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":false,"error":{"code":"INVITATION_UNAVAILABLE","message":"Unavailable"}}'))
                # Open and wait for the shared localized Admin load-error card.
                page.get_by_test_id('admin-tab-invitations').click(); page.get_by_test_id('admin-load-error').wait_for(timeout=WAIT_MS)
                # Capture the invitation error state at every governed viewport.
                for viewport_id,viewport in viewports.items(): page.set_viewport_size(viewport); page.wait_for_timeout(100); game_evidence(f'after-pass-admin-invitations-error-{locale}-{viewport_id}.png','admin',['invitations_error'],locale,viewport_id)
                # Remove the error shim before the next locale.
                page.unroute('**/api/v2/admin/invitations?limit=100')
            # Restore primary dimensions before leaving the Admin session.
            page.set_viewport_size(viewports['desktop_primary'])
            # Record diagnostics boundaries so only the controlled anonymous and generic-error responses can be consumed.
            invitation_console_index=len(console_errors); invitation_http_index=len(http_errors); invitation_page_error_index=len(page_errors)
            # Clear the authenticated cookie jar so the account-free public route is exercised honestly.
            page.context.clear_cookies()
            # Exercise the form, consent, generic error, focus, motion, and zoom states in both locales.
            for locale in ('en-US','ru-RU'):
                # Navigate with a synthetic bearer that is never rendered or written to evidence metadata.
                page.goto(base+'/enroll/invitation?token=synthetic-browser-invitation-bearer',wait_until='networkidle'); page.get_by_test_id('invitation-redemption').wait_for(timeout=WAIT_MS)
                # Switch the visible form locale through its own governed selector.
                page.get_by_test_id('invitation-locale').select_option(locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=locale)
                # Capture the empty account-free form and explicit unaccepted-terms state at every viewport.
                for viewport_id,viewport in viewports.items():
                    # Resize before containment and evidence.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require no page-level horizontal overflow.
                    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
                    # Capture the empty form and explicit consent boundary together.
                    game_evidence(f'after-pass-invitation-form-{locale}-{viewport_id}.png','invitation_redemption',['form','terms_unaccepted'],locale,viewport_id)
                # Focus the native submit control so keyboard evidence records the exact target.
                page.get_by_test_id('invitation-submit').focus(); assert page.evaluate("() => document.activeElement?.getAttribute('data-testid')")=='invitation-submit'
                # Capture the keyboard-focus state at primary desktop.
                page.set_viewport_size(viewports['desktop_primary']); game_evidence(f'after-pass-invitation-keyboard-focus-{locale}-desktop_primary.png','invitation_redemption',['keyboard_focus'],locale,'desktop_primary')
                # Enable reduced motion and capture the unchanged complete form.
                page.emulate_media(reduced_motion='reduce'); game_evidence(f'after-pass-invitation-reduced-motion-{locale}-desktop_primary.png','invitation_redemption',['reduced_motion'],locale,'desktop_primary'); page.emulate_media(reduced_motion='no-preference')
                # Apply the repository's 200-percent content-zoom proxy and wait for responsive form reflow.
                page.set_viewport_size(viewports['desktop_primary']); page.evaluate("() => { document.body.style.zoom='200%'; document.body.style.width='100%'; }"); page.wait_for_timeout(100)
                # Measure the page, panel, form, and every visible enrollment field at the exact zoom state.
                public_zoom_geometry=page.evaluate("() => { const panel=document.querySelector('[data-testid=\"invitation-redemption\"]'); const form=document.querySelector('#invitation-form'); const panelBox=panel.getBoundingClientRect(); const formBox=form.getBoundingClientRect(); const controls=[...form.querySelectorAll('input, select, button')].map(control => ({ testId:control.getAttribute('data-testid'), tag:control.tagName.toLowerCase(), clientWidth:control.clientWidth, scrollWidth:control.scrollWidth, box:control.getBoundingClientRect().toJSON() })); return { viewport:innerWidth, documentScrollWidth:document.documentElement.scrollWidth, panelClientWidth:panel.clientWidth, panelScrollWidth:panel.scrollWidth, panelBox:panelBox.toJSON(), formClientWidth:form.clientWidth, formScrollWidth:form.scrollWidth, formBox:formBox.toJSON(), controls }; }")
                # Require page/panel/form containment plus every native field fully painted inside the form.
                assert public_zoom_geometry['documentScrollWidth']<=public_zoom_geometry['viewport']+1 and public_zoom_geometry['panelScrollWidth']<=public_zoom_geometry['panelClientWidth']+1 and public_zoom_geometry['formScrollWidth']<=public_zoom_geometry['formClientWidth']+1 and public_zoom_geometry['panelBox']['left']>=-1 and public_zoom_geometry['panelBox']['right']<=public_zoom_geometry['viewport']+1 and public_zoom_geometry['panelClientWidth']>=320 and public_zoom_geometry['formClientWidth']>=280 and all(control['box']['left']>=public_zoom_geometry['formBox']['left']-1 and control['box']['right']<=public_zoom_geometry['formBox']['right']+1 and (control['tag']=='select' or control['scrollWidth']<=control['clientWidth']+1) for control in public_zoom_geometry['controls']), {'locale':locale,'viewport':'desktop_primary','zoom':200,'geometry':public_zoom_geometry}
                # Capture the explicit zoom acceptance state before restoring scale.
                game_evidence(f'after-pass-invitation-zoom-200-{locale}-desktop_primary.png','invitation_redemption',['zoom_200'],locale,'desktop_primary'); page.evaluate("() => { document.body.style.zoom=''; document.body.style.width=''; }")
                # Return to primary dimensions for the generic-error interaction.
                page.set_viewport_size(viewports['desktop_primary'])
                # Intercept only redemption with the exact generic contract error.
                page.route('**/api/v2/auth/redeem-invitation',lambda route: route.fulfill(status=400,content_type='application/json',body='{"ok":false,"error":{"code":"VALIDATION_ERROR","message":"invitation could not be redeemed","details":{"reason":"invitation_unavailable"}}}'))
                # Fill transient synthetic fields and explicit current terms before submit.
                page.get_by_test_id('invitation-email').fill('visual-invitation@example.invalid'); page.get_by_test_id('invitation-display-name').fill('Invited Player'); page.get_by_test_id('invitation-password').fill('Synthetic-Invite-2026!'); page.get_by_test_id('invitation-terms').check(); page.get_by_test_id('invitation-submit').click()
                # Wait for the localized generic message, then clear all raw transient fields before evidence.
                page.wait_for_function("() => document.querySelector('#invitation-message')?.textContent.trim().length > 0"); page.get_by_test_id('invitation-email').fill(''); page.get_by_test_id('invitation-display-name').fill(''); page.get_by_test_id('invitation-password').fill('')
                # Capture the non-enumerating error at every governed viewport.
                for viewport_id,viewport in viewports.items(): page.set_viewport_size(viewport); page.wait_for_timeout(100); game_evidence(f'after-pass-invitation-generic-error-{locale}-{viewport_id}.png','invitation_redemption',['generic_error'],locale,viewport_id)
                # Remove the generic-error shim before the terminal success response.
                page.unroute('**/api/v2/auth/redeem-invitation')
            # Exercise terminal success independently in both installed locales with identifier-free responses.
            for success_locale in ('en-US','ru-RU'):
                # Open a fresh synthetic form whose bearer is never written to screenshots or sidecars.
                page.goto(base+'/enroll/invitation?token=synthetic-browser-success-bearer',wait_until='networkidle'); page.get_by_test_id('invitation-redemption').wait_for(timeout=WAIT_MS)
                # Select and verify the exact locale before submitting so evidence metadata matches rendered copy.
                page.get_by_test_id('invitation-locale').select_option(success_locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=success_locale)
                # Intercept the terminal response without creating a real account in the browser copy.
                page.route('**/api/v2/auth/redeem-invitation',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"status":"enrolled"}}'))
                # Fill current terms and submit through the visible public form.
                page.get_by_test_id('invitation-email').fill('visual-success@example.invalid'); page.get_by_test_id('invitation-display-name').fill('Invited Player'); page.get_by_test_id('invitation-password').fill('Synthetic-Invite-2026!'); page.get_by_test_id('invitation-terms').check(); page.get_by_test_id('invitation-submit').click(); page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS)
                # Require the bearer to be removed from browser history after success.
                assert page.url.rstrip('/')==base.rstrip('/') and 'token=' not in page.url
                # Capture the identifier-free success return at every governed viewport with truthful locale metadata.
                for viewport_id,viewport in viewports.items(): page.set_viewport_size(viewport); page.wait_for_timeout(100); game_evidence(f'after-pass-invitation-success-{success_locale}-{viewport_id}.png','invitation_redemption',['success_return_to_login'],success_locale,viewport_id)
                # Remove the focused success shim before the next locale or authenticated restoration.
                page.unroute('**/api/v2/auth/redeem-invitation')
            # Restore an authenticated Admin session for the following browser suites.
            page.request.post(base+'/api/v2/auth/login',data={'email':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD}); page.goto(base+'/admin',wait_until='networkidle'); page.get_by_test_id('admin-tab-operations').wait_for(timeout=WAIT_MS)
            # Retain only diagnostics emitted by the controlled account-free invitation journey.
            invitation_expected_console=console_errors[invitation_console_index:]; invitation_expected_http=http_errors[invitation_http_index:]; invitation_expected_page_errors=page_errors[invitation_page_error_index:]
            # Require zero anonymous current-user probes and only the two contract-shaped generic redemption rejections.
            assert len(invitation_expected_http)==2 and sum(value.endswith('/api/v2/me') for value in invitation_expected_http)==0 and sum(value.startswith('400 ') and value.endswith('/api/v2/auth/redeem-invitation') for value in invitation_expected_http)==2, invitation_expected_http
            # Require the browser to report no JavaScript failure and only its standard failed-resource console lines.
            assert invitation_expected_page_errors==[] and len(invitation_expected_console)==len(invitation_expected_http) and all('Failed to load resource' in value for value in invitation_expected_console), invitation_expected_console+invitation_expected_page_errors
            # Remove only the verified controlled diagnostics so every unrelated HTTP or console failure remains fatal.
            del console_errors[invitation_console_index:]; del http_errors[invitation_http_index:]
        # Record the complete Admin/public locale, viewport, state, privacy, keyboard, motion, zoom, and evidence matrix.
        run_case('BR-INVITE-001',['INVITE-001','INVITE-002','INVITE-003','INVITE-005','TEST-091'],invitation_browser)
        # Define real-backend Operations states, localization, responsive layout, and evidence.
        def admin_operations_browser():
            # Cache the isolated backend's primary storage document for reversible degradation.
            players_path=browser_data_dir/'players.json'; unavailable_path=browser_data_dir/'players.operations-browser-unavailable.json'
            # Define every governed Admin viewport for this Operations surface.
            viewports={'desktop-primary':{'width':1920,'height':1080},'desktop-compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900}}
            # Exercise both installed locales on the same authenticated real backend.
            for locale in ('en-US','ru-RU'):
                # Switch locale in place without changing the user's browser preference outside this test.
                page.evaluate("async locale => { const i18n = await import('/core/i18n.js'); await i18n.setLocale(locale, { persistLocal: false }); }", locale)
                # Open the Operations tab and wait for healthy real-backend telemetry.
                page.get_by_test_id('admin-tab-operations').click(); page.get_by_test_id('admin-operations-live').wait_for(timeout=WAIT_MS)
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
                    page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-operations-degraded').wait_for(timeout=WAIT_MS)
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
                page.get_by_test_id('admin-refresh').click(); page.get_by_test_id('admin-operations-down').wait_for(timeout=WAIT_MS)
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
    # Preserve exact feedback/Admin operational case accounting on non-owning shards.
    else:
        # Advance only the feedback-through-operations affinity range.
        skip_browser_affinity('feedback_admin')
    # Run practice-opponent, user, Guest Trials, audio, and localization presentation on their declared Admin owner.
    if admin_presentation_owner:
        # Install an Admin session without depending on the operational Admin affinity owner.
        presentation_login=page.request.post(base+'/api/v2/auth/login',data={'email':DEFAULT_AUTH_EMAIL,'password':DEFAULT_AUTH_PASSWORD})
        # Refuse to render presentation cases without exact protected-route authority.
        if not presentation_login.ok or presentation_login.json().get('ok') is not True: raise AssertionError('Admin presentation affinity login failed')
        # Mount the protected Admin document at its canonical English desktop starting state.
        page.set_viewport_size({'width':1920,'height':1080}); page.emulate_media(reduced_motion='no-preference'); page.goto(base+'/admin',wait_until='networkidle'); page.get_by_test_id('admin-tab-audio').wait_for(timeout=WAIT_MS)
        # Define the funded practice-opponent Admin browser acceptance check.
        def admin_practice_opponents_browser():
            # Open the Players & Bots control-plane surface.
            page.get_by_test_id('admin-tab-players').click()
            # Wait for the account allocation and funding control to render.
            page.get_by_test_id('practice-opponent-admin').wait_for(timeout=WAIT_MS)
            # Require all three server-managed account rows before funding.
            assert page.get_by_test_id('practice-opponent-account').count()==3
            # Submit funding through the visible Admin controller action.
            with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/bots/practice-opponents/fund') and response.request.method=='POST'):
                # Click the idempotent funding control.
                page.get_by_test_id('fund-practice-opponents').click()
            # Wait for append-only funding activity to replace the prior view.
            page.get_by_test_id('practice-opponent-activity').first.wait_for(timeout=WAIT_MS * 2)
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
        page.locator('[data-tab="telemetry"]').click(); page.get_by_text('Application events',exact=True).wait_for(timeout=WAIT_MS)
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
            page.get_by_test_id('admin-user-email').wait_for(timeout=WAIT_MS)
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
            user_row.wait_for(timeout=WAIT_MS * 2)
            # Wait for the one-time temporary password notice.
            page.get_by_test_id('admin-user-temp-password').wait_for(timeout=WAIT_MS)
            # Select a non-active lifecycle state through the account-only Users surface.
            user_row.get_by_test_id('admin-user-status').select_option('suspended')
            # Accept the explicit lifecycle confirmation for this controlled Admin mutation.
            page.once('dialog',lambda dialog: dialog.accept())
            # Wait for both the protected v2 mutation and the account-table refresh it triggers.
            with page.expect_response(lambda response: '/api/v2/admin/users/' in response.url and response.request.method == 'PATCH') as account_response_info:
                # Wait for the mutation-triggered Users refresh before inspecting persisted controls.
                with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/users') and response.request.method == 'GET'):
                    # Save the suspended lifecycle state without any privilege field.
                    user_row.get_by_test_id('admin-user-save-account').click()
            # Store the v2 account mutation response for envelope verification.
            account_response=account_response_info.value.json()
            # Require the standard success envelope from the protected role/lifecycle route.
            assert account_response['ok'] is True
            # Wait for the persisted lifecycle control to re-render from the refreshed account.
            user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="suspended"]')
            # Require the selected control to reflect the canonical persisted account state and no privilege editor to exist.
            user_row.wait_for(timeout=WAIT_MS * 2); assert user_row.get_by_test_id('admin-user-status').input_value()=='suspended' and user_row.get_by_test_id('admin-user-role-admin').count()==0
            # Enumerate every governed Admin viewport for the lifecycle evidence corpus.
            account_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Pin the locale-owned lifecycle action so Russian evidence cannot reuse English copy.
            account_labels={'en-US':{'save':'Save account'},'ru-RU':{'save':'Сохранить аккаунт'}}
            # Capture the persisted lifecycle controls in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch the Admin runtime before re-rendering the Users surface.
                page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                # Reload Users so every role/lifecycle label comes from the selected locale.
                page.get_by_test_id('admin-tab-users').click()
                # Resolve the refreshed synthetic row and bounded scroll owner.
                user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="suspended"]')
                # Wait for the persisted account row before localization and geometry assertions.
                user_row.wait_for(timeout=WAIT_MS)
                # Require the lifecycle save action to use exact locale-owned copy.
                assert user_row.get_by_test_id('admin-user-save-account').inner_text().strip()==account_labels[locale]['save']
                # Require the lifecycle resource keys never to leak into visible Admin copy.
                account_text=page.get_by_test_id('admin-users-managed-accounts').inner_text()
                # Check complete governed keys rather than ordinary words that may appear legitimately.
                assert all(key not in account_text for key in ('users.roleAdmin','users.saveAccount','users.roleConfirm','users.accountSaved'))
                # Exercise every visual-matrix viewport before recording the exact-head corpus.
                for viewport_id,viewport in account_viewports.items():
                    # Apply exact governed dimensions before measuring the changed Admin surface.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Center the exact group with an explicit owner-relative delta because nested table scrollIntoView alignment varies by browser.
                    page.get_by_test_id('admin-users-managed-accounts').evaluate("""section => { const owner=section.querySelector('[data-testid="admin-users-managed-table"]'); const group=section.querySelector('tr[data-email="beta.browser@example.test"] [data-testid="admin-user-access-controls"]'); const ownerRect=owner?.getBoundingClientRect(); const groupRect=group?.getBoundingClientRect(); if (owner && ownerRect && groupRect) owner.scrollLeft += groupRect.left - ownerRect.left - Math.max(0,(owner.clientWidth-groupRect.width)/2); }""")
                    # Wait one frame so the explicit scroll position is painted before containment and evidence capture.
                    page.wait_for_timeout(50)
                    # Measure document, section, scroll-owner, and changed-control containment independently.
                    account_geometry=page.get_by_test_id('admin-users-managed-accounts').evaluate("""section => { const sectionRect=section.getBoundingClientRect(); const owner=section.querySelector('[data-testid="admin-users-managed-table"]'); const ownerRect=owner?.getBoundingClientRect(); const row=section.querySelector('tr[data-email="beta.browser@example.test"]'); const group=row?.querySelector('[data-testid="admin-user-access-controls"]'); const groupRect=group?.getBoundingClientRect(); const save=row?.querySelector('[data-testid="admin-user-save-account"]'); const controls=[row?.querySelector('[data-testid="admin-user-status"]'),save].filter(Boolean); return { documentContained: document.documentElement.scrollWidth <= window.innerWidth + 1, sectionContained: sectionRect.left >= -1 && sectionRect.right <= window.innerWidth + 1, ownerContained: Boolean(ownerRect && ownerRect.left >= sectionRect.left - 1 && ownerRect.right <= sectionRect.right + 1), controlsUsable: controls.length === 2 && controls.every(control => { const rect=control.getBoundingClientRect(); return rect.width > 0 && rect.height >= 18; }), controlsContained: controls.length === 2 && controls.every(control => { const rect=control.getBoundingClientRect(); return Boolean(ownerRect && rect.left >= ownerRect.left - 1 && rect.right <= ownerRect.right + 1); }), privilegeEditorAbsent: !row?.querySelector('[data-testid="admin-user-role-admin"]'), saveTextReadable: Boolean(save && save.scrollWidth <= save.clientWidth + 1), saveMetrics: save ? {clientWidth:save.clientWidth,scrollWidth:save.scrollWidth,clientHeight:save.clientHeight,scrollHeight:save.scrollHeight} : null, ownerRect: ownerRect ? {left:ownerRect.left,right:ownerRect.right,width:ownerRect.width,scrollLeft:owner.scrollLeft,clientWidth:owner.clientWidth} : null, groupRect: groupRect ? {left:groupRect.left,right:groupRect.right,width:groupRect.width} : null, controlRects: controls.map(control => { const rect=control.getBoundingClientRect(); return {testid:control.getAttribute('data-testid'),left:rect.left,right:rect.right,width:rect.width}; }) }; }""")
                    # Fail closed on overflow, clipping, missing controls, or collapsed native inputs.
                    assert all(account_geometry[key] for key in ('documentContained','sectionContained','ownerContained','controlsUsable','controlsContained','privilegeEditorAbsent','saveTextReadable')),{'locale':locale,'viewport':viewport_id,**account_geometry}
                    # Write one exact-head Admin PNG and sidecar for independent EN/RU human review.
                    region_evidence(f'after-pass-admin-account-spine-{locale}-{viewport_id}.png','[data-testid="admin-users-managed-accounts"]','admin',['users','users_account_lifecycle'],locale,viewport_id)
            # Restore the suite-default locale and viewport before reverting the synthetic account.
            page.set_viewport_size(account_viewports['desktop_primary']); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }")
            # Reload Users and resolve the persisted synthetic account after locale evidence.
            page.get_by_test_id('admin-tab-users').click(); user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="suspended"]')
            # Restore the synthetic account to active state before the separate privilege workflow.
            user_row.get_by_test_id('admin-user-status').select_option('active')
            # Accept the explicit confirmation for the controlled lifecycle restoration.
            page.once('dialog',lambda dialog: dialog.accept())
            # Wait for both the v2 restoration mutation and its account-table refresh.
            with page.expect_response(lambda response: '/api/v2/admin/users/' in response.url and response.request.method == 'PATCH'):
                # Wait for the refresh before the original deactivate/reactivate sequence begins.
                with page.expect_response(lambda response: response.url.endswith('/api/v1/admin/users') and response.request.method == 'GET'):
                    # Persist the restored active lifecycle status.
                    user_row.get_by_test_id('admin-user-save-account').click()
            # Resolve the active player row after the protected restoration completes.
            user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="active"]')
            # Require the restored row and continued absence of a privilege editor before delegation.
            user_row.wait_for(timeout=WAIT_MS * 2); assert user_row.get_by_test_id('admin-user-role-admin').count()==0
            # Capture the durable user id for the separate owner-only Administrators workflow.
            created_user_id=user_row.get_attribute('data-user')
            # Open the dedicated privilege-management surface instead of using generic account rows.
            page.get_by_test_id('admin-tab-administrators').click(); page.get_by_test_id('admin-administrator-grant').wait_for(timeout=WAIT_MS)
            # Select the active synthetic account and supply transient step-up evidence.
            page.locator('#administrator-target').select_option(created_user_id); page.locator('#administrator-password').fill(DEFAULT_AUTH_PASSWORD); page.locator('#administrator-reason').fill('Browser delegation acceptance')
            # Commit one owner-reauthenticated Admin grant through the dedicated endpoint.
            with page.expect_response(lambda response: response.url.endswith(f'/api/v2/admin/administrators/{created_user_id}/grant') and response.request.method=='POST') as grant_response_info:
                # Activate the fixed grant control while its exact response observer is armed.
                page.get_by_test_id('administrator-grant').click()
            # Require the standard grant envelope and durable ordinary-Admin list row.
            assert grant_response_info.value.json()['ok'] is True; page.locator(f'.administrator-revoke[data-user="{created_user_id}"]').wait_for(timeout=WAIT_MS * 2)
            # Require one immutable audit row and scrubbed password field after the rerender.
            assert 'Browser delegation acceptance' in page.get_by_test_id('admin-administrator-audit').inner_text() and page.locator('#administrator-password').input_value()==''
            # Open the Administrators workspace in one locale without racing its asynchronous locale rerender.
            def open_administrators_locale(locale):
                # Read the current runtime locale before deciding whether locale notification or an explicit tab activation owns the load.
                current_locale=page.evaluate("() => window.CasinoI18n.getLocaleState().locale")
                # Observe the one canonical Administrators listing request that must complete the requested render.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/admin/administrators') and response.request.method=='GET') as administrators_response_info:
                    # Let a genuine locale transition own the reload, otherwise activate the already-localized tab explicitly.
                    if current_locale!=locale: page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                    # Trigger exactly one load when the locale is already current and no locale notification will fire.
                    else: page.get_by_test_id('admin-tab-administrators').click()
                # Require a successful listing envelope before interacting with its replacement DOM.
                assert administrators_response_info.value.json()['ok'] is True
                # Wait until the asynchronously rendered heading uses the requested locale rather than the prior DOM.
                page.wait_for_function("async () => { const i18n=await import('/core/i18n.js'); return document.querySelector('#adminTitle')?.textContent===i18n.t('administrators.title',{},'admin'); }")
                # Require the replacement workspace and its scrubbed transient-password field.
                page.get_by_test_id('admin-administrator-list').wait_for(timeout=WAIT_MS); assert page.locator('#administrator-password').input_value()==''
            # Capture the complete delegation workspace under every required locale and viewport.
            for locale in ('en-US','ru-RU'):
                # Render the exact locale through one non-racing Administrators load.
                open_administrators_locale(locale)
                # Exercise every governed responsive viewport without allowing horizontal page overflow.
                for viewport_id,viewport in account_viewports.items():
                    # Apply the exact matrix viewport and wait for layout to settle.
                    page.set_viewport_size(viewport); page.wait_for_timeout(75)
                    # Capture exact containment, transient-secret state, and any widest escaping element after the responsive render settles.
                    administrator_geometry=page.evaluate("""() => { const escaping=[...document.querySelectorAll('*')].map(element => { const rect=element.getBoundingClientRect(); return {testid:element.getAttribute('data-testid'),id:element.id,tag:element.tagName,right:Math.round(rect.right),width:Math.round(rect.width)}; }).filter(row => row.right > innerWidth + 1).sort((left,right) => right.right-left.right).slice(0,5); return {scrollWidth:document.documentElement.scrollWidth,innerWidth,passwordEmpty:document.querySelector('#administrator-password')?.value === '',escaping}; }""")
                    # Require all three privilege cards to remain contained and password values to remain absent with actionable evidence.
                    assert administrator_geometry['scrollWidth']<=administrator_geometry['innerWidth']+1 and administrator_geometry['passwordEmpty'],{'locale':locale,'viewport':viewport_id,**administrator_geometry}
                    # Capture exact-head after-pass privilege-management evidence.
                    game_evidence(f'after-pass-admin-administrators-{locale}-{viewport_id}.png','BR-ADMIN-USERS-001',['administrator_list','owner_reauthentication','immutable_audit'],locale,viewport_id)
            # Restore English and desktop geometry through one completed render before revoking the temporary grant.
            page.set_viewport_size(account_viewports['desktop_primary']); open_administrators_locale('en-US')
            # Supply a fresh transient step-up and explicit revoke reason after the grant rerender.
            page.locator('#administrator-password').fill(DEFAULT_AUTH_PASSWORD); page.locator('#administrator-reason').fill('Browser delegation cleanup')
            # Revoke only the temporary ordinary-Admin grant through the dedicated route.
            with page.expect_response(lambda response: response.url.endswith(f'/api/v2/admin/administrators/{created_user_id}/revoke') and response.request.method=='POST') as revoke_response_info:
                # Activate the target-bound revoke control.
                page.locator(f'.administrator-revoke[data-user="{created_user_id}"]').click()
            # Require the standard revoke envelope and a durable audit row without the prior Admin listing.
            assert revoke_response_info.value.json()['ok'] is True; page.wait_for_function("""({ userId }) => document.querySelector('[data-testid="admin-administrator-audit"]')?.textContent.includes('Browser delegation cleanup') && !document.querySelector(`.administrator-revoke[data-user="${userId}"]`)""", arg={'userId':created_user_id}, timeout=WAIT_MS)
            # Return to generic Users for lifecycle, password, terms, and locale actions.
            page.get_by_test_id('admin-tab-users').click(); user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="active"]'); user_row.wait_for(timeout=WAIT_MS)
            # Deactivate the user through the first row action.
            user_row.get_by_test_id('admin-user-toggle').click()
            # Reacquire the row after its status-driven DOM replacement renders.
            user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="inactive"]')
            # Wait for the inactive state to render before reactivation.
            user_row.wait_for(timeout=WAIT_MS * 2)
            # Reactivate the user through the same row action.
            user_row.get_by_test_id('admin-user-toggle').click()
            # Reacquire the row after the reactivation rerender.
            user_row=page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-status="active"]')
            # Wait for the active state to render before later actions reuse the row.
            user_row.wait_for(timeout=WAIT_MS * 2)
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
            page.get_by_test_id('admin-user-temp-password').wait_for(timeout=WAIT_MS)
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
            page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"][data-terms="accepted"]').wait_for(timeout=WAIT_MS * 2)
            # Save locale preferences from the rendered row controls.
            user_row.get_by_test_id('admin-user-save-locale').click()
            # Verify the token balance remains visible after all actions.
            assert '◈777.00' in user_row.get_by_test_id('admin-user-token-balance').inner_text()
            # Enumerate every governed Admin viewport for the account-only handoff evidence.
            users_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Pin locale-owned handoff headings so Russian evidence cannot silently reuse English copy.
            handoff_headings={'en-US':'Guest and marketing trials live separately','ru-RU':'Гостевые и маркетинговые сессии находятся отдельно'}
            # Capture the explicit account/Guest Trials boundary in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch the Admin runtime before rerendering the Users surface.
                page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                # Reload the active Users tab so every new handoff string comes from the selected locale.
                page.get_by_test_id('admin-tab-users').click(); page.get_by_test_id('admin-users-guest-separation').wait_for(timeout=WAIT_MS)
                # Retain a stable locator for geometry, translation, and interaction proof.
                handoff=page.get_by_test_id('admin-users-guest-separation')
                # Require the exact locale-owned heading without leaking any handoff resource key.
                handoff_text=handoff.inner_text()
                # Check only complete governed keys because ordinary English copy may legitimately contain "users.".
                assert handoff.locator('h3').inner_text()==handoff_headings[locale] and all(key not in handoff_text for key in ('users.guestSeparationTitle','users.guestSeparationCopy','users.openGuestTrials'))
                # Require the created account to remain visible while Guest Trials stay absent from managed rows.
                assert page.locator('tr[data-testid="admin-user-row"][data-email="beta.browser@example.test"]').count()==1 and page.locator('tr[data-testid="admin-user-row"][data-email=""]').count()==0
                # Exercise every governed responsive width with a bounded readable handoff region.
                for viewport_id,viewport in users_viewports.items():
                    # Apply the exact visual-matrix dimensions before measuring the changed surface.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Measure page, handoff, table-owner, readable-inline, and control containment independently from screenshot success.
                    handoff_geometry=handoff.evaluate("""element => { const rect=element.getBoundingClientRect(); const tableOwner=document.querySelector('[data-testid="admin-users-managed-table"]'); const tableRect=tableOwner?.getBoundingClientRect(); return { documentContained: document.documentElement.scrollWidth <= window.innerWidth + 1, regionContained: rect.left >= -1 && rect.right <= window.innerWidth + 1, tableOwnerContained: Boolean(tableRect && tableRect.left >= -1 && tableRect.right <= window.innerWidth + 1), readable: rect.width >= Math.min(320, window.innerWidth - 32), controlContained: [...element.querySelectorAll('button')].every(control => { const box=control.getBoundingClientRect(); return box.left >= rect.left - 1 && box.right <= rect.right + 1 && box.width >= 44 && box.height >= 36; }) }; }""")
                    # Fail closed on document overflow, clipped handoff/table ownership, narrow copy, or an unusable control.
                    assert all(handoff_geometry.values()),{'locale':locale,'viewport':viewport_id,**handoff_geometry}
                    # Write one exact-head bounded PNG and sidecar for independent EN/RU human review.
                    region_evidence(f'after-pass-admin-users-separation-{locale}-{viewport_id}.png','[data-testid="admin-users-guest-separation"]','admin',['users'],locale,viewport_id)
                # Follow the visible ownership handoff and require the Guest Trials surface to load.
                page.get_by_test_id('admin-open-guest-trials').click(); page.get_by_test_id('admin-guest-filters').wait_for(timeout=WAIT_MS)
            # Restore the suite-default locale and viewport after governed evidence.
            page.set_viewport_size(users_viewports['desktop_primary']); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }")
            # Open the owner enrollment workspace without changing any live capability.
            page.get_by_test_id('admin-tab-enrollment').click(); page.get_by_test_id('admin-enrollment-policy').wait_for(timeout=WAIT_MS); page.get_by_test_id('admin-enrollment-readiness').wait_for(timeout=WAIT_MS); page.get_by_test_id('admin-oauth-operational-controls').wait_for(timeout=WAIT_MS)
            # Require both independent provider operations to remain disabled under repository defaults.
            assert page.locator('#oauth-operational-google').is_checked() is False and page.locator('#oauth-operational-facebook').is_checked() is False
            # Preview the unchanged closed policy through the real pure-computation endpoint.
            with page.expect_response(lambda response: response.url.endswith('/api/v2/admin/enrollment-policy/preview') and response.request.method=='POST'):
                # Activate only the non-mutating preview control.
                page.locator('#enrollment-preview').click()
            # Require a visible bounded impact result and no launch authorization control.
            page.locator('#enrollment-preview-result:not([hidden])').wait_for(timeout=WAIT_MS); assert page.get_by_test_id('admin-enrollment-policy').locator('button').count()==2
            # Capture enrollment policy/readiness and held launch status across the required matrix.
            for locale in ('en-US','ru-RU'):
                # Switch the Admin locale before rerendering governance workspaces.
                page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                # Reload the enrollment workspace in the selected locale.
                page.get_by_test_id('admin-tab-enrollment').click(); page.get_by_test_id('admin-enrollment-readiness').wait_for(timeout=WAIT_MS); page.get_by_test_id('admin-oauth-operational-controls').wait_for(timeout=WAIT_MS)
                # Exercise every governed responsive viewport for policy and readiness evidence.
                for viewport_id,viewport in users_viewports.items():
                    # Apply exact visual-matrix dimensions and require document containment.
                    page.set_viewport_size(viewport); page.wait_for_timeout(50); assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
                    # Capture the complete owner policy and secret-free readiness state.
                    game_evidence(f'after-pass-admin-enrollment-{locale}-{viewport_id}.png','BR-ADMIN-USERS-001',['enrollment_policy','provider_readiness','provider_operational_controls','live_enablement_held'],locale,viewport_id)
                # Open the read-only launch dashboard after enrollment evidence.
                page.get_by_test_id('admin-tab-launch').click(); page.get_by_test_id('admin-launch-readiness').wait_for(timeout=WAIT_MS)
                # Require held status and the complete absence of any action control.
                assert page.get_by_test_id('admin-launch-readiness').get_attribute('data-status')=='held' and page.get_by_test_id('admin-launch-readiness').locator('button,input,select').count()==0
                # Capture the launch hold at each governed viewport without a mutation affordance.
                for viewport_id,viewport in users_viewports.items():
                    # Apply exact dimensions and require a contained read-only card.
                    page.set_viewport_size(viewport); page.wait_for_timeout(50); assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
                    # Capture exact-head read-only release-gate evidence.
                    game_evidence(f'after-pass-admin-launch-readiness-{locale}-{viewport_id}.png','BR-ADMIN-USERS-001',['launch_readiness','launch_held','read_only'],locale,viewport_id)
            # Verify the existing Language / Locale tab remains reachable.
            page.set_viewport_size(users_viewports['desktop_primary']); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false}); }")
            # Navigate to the existing language surface after the new governance workspaces.
            page.get_by_test_id('admin-tab-language').click(); page.get_by_test_id('admin-language-select').wait_for(timeout=WAIT_MS)
        run_case('BR-ADMIN-USERS-001',['ADMIN-USER-PENDING-035','TERMS-PENDING-035','TOKEN-PENDING-035','I18N-003','USER-004','GUEST-004','ADMIN-026','ADMIN-033','AUTH-015','AUTH-016','OAUTH-011','OAUTH-012','I18N-009','TEST-081','TEST-112','TEST-158','TEST-167'],admin_users_browser)
        # Prove the Admin Guest Trials section reports de-identified account-free telemetry. (issue #317)
        def admin_guest_trials_browser():
            # Define every governed Admin viewport, including the issue-required mobile state.
            guest_admin_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Snapshot the test runtime telemetry so empty-state evidence can remain isolated and reversible.
            original_analytics=guest_analytics.read_json(guest_analytics.TRIALS_PATH,guest_analytics.default_trials)
            # Start with the canonical empty document for exact empty, loading, and error evidence.
            write_json(guest_analytics.TRIALS_PATH,guest_analytics.default_trials())
            # Track seeded principals for canonical teardown after populated-state evidence.
            seeded_guests=[]
            # Start protected Admin verification so seeded principals always end.
            try:
                # Exercise every locale and viewport before any analytics row exists.
                for locale in ('en-US','ru-RU'):
                    # Switch the Admin runtime so loading, error, and empty states use real localized copy.
                    page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                    # Capture each asynchronous state at every governed Admin viewport.
                    for viewport_id,viewport in guest_admin_viewports.items():
                        # Resize before the request starts so evidence proves state-specific containment.
                        page.set_viewport_size(viewport)
                        # Hold the summary request unresolved while the production loading state remains mounted.
                        pending_routes=[]
                        # Match only the Guest Trials summary request, never its detail or cleanup endpoints.
                        summary_pattern='**/api/v2/admin/guest-trials?*'
                        # Retain the intercepted route without continuing it until loading evidence is captured.
                        page.route(summary_pattern,lambda route: pending_routes.append(route))
                        # Open Guest Trials through the visible sidebar action.
                        page.get_by_test_id('admin-tab-guests').click(); page.get_by_test_id('admin-guest-loading').wait_for(timeout=WAIT_MS)
                        # Require the explicit loading state to remain horizontally contained.
                        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1") and pending_routes
                        # Capture exact-head localized loading evidence.
                        game_evidence(f'after-pass-admin-guest-loading-{locale}-{viewport_id}.png','admin',['guest_trials_loading'],locale,viewport_id)
                        # Release the one held request and remove its interceptor before observing the empty response.
                        pending_routes.pop(0).continue_(); page.unroute(summary_pattern); page.get_by_test_id('admin-guest-empty').wait_for(timeout=WAIT_MS)
                        # Capture the genuine zero-row Admin surface.
                        game_evidence(f'after-pass-admin-guest-empty-{locale}-{viewport_id}.png','admin',['guest_trials_empty'],locale,viewport_id)
                        # Record diagnostics boundaries so the intentional failure probe cannot pollute suite-wide error accounting.
                        guest_error_console_index=len(console_errors); guest_error_http_index=len(http_errors); guest_error_page_index=len(page_errors)
                        # Fail the next summary request with a sanitized standard error response.
                        page.route(summary_pattern,lambda route: route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"UNAVAILABLE","message":"Unavailable"}}'))
                        # Reload the current Guest Trials tab through its visible control.
                        page.get_by_test_id('admin-tab-guests').click(); page.get_by_test_id('admin-load-error').wait_for(timeout=WAIT_MS)
                        # Require the recovery state to remain contained without raw response details.
                        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1") and 'UNAVAILABLE' not in page.get_by_test_id('admin-load-error').inner_text()
                        # Capture exact-head localized error evidence before removing the interceptor.
                        game_evidence(f'after-pass-admin-guest-error-{locale}-{viewport_id}.png','admin',['guest_trials_error'],locale,viewport_id)
                        # Retain only the diagnostics produced by this controlled error-state request.
                        guest_expected_console=console_errors[guest_error_console_index:]; guest_expected_http=http_errors[guest_error_http_index:]; guest_expected_page=page_errors[guest_error_page_index:]
                        # Require no unhandled JavaScript error and only the browser's standard failed-resource console line.
                        assert guest_expected_page==[] and all('Failed to load resource' in value for value in guest_expected_console)
                        # Require exactly the controlled Guest Trials summary rejection before consuming it from global accounting.
                        assert len(guest_expected_http)==1 and guest_expected_http[0].startswith('503 ') and '/api/v2/admin/guest-trials?' in guest_expected_http[0]
                        # Remove only the verified controlled diagnostics so unexpected errors elsewhere still fail the suite.
                        del console_errors[guest_error_console_index:]; del http_errors[guest_error_http_index:]
                        # Restore normal routing for populated evidence.
                        page.unroute(summary_pattern)
                # Seed one safe analytics row per locale through the canonical guest service.
                seeded_guests=[auth_core.create_guest('admin-browser-test',True,'private-beta-1',locale,'desktop') for locale in ('en-US','ru-RU')]
                # Add game-open and completed-round counters without storing request or response payloads.
                for seeded_guest in seeded_guests:
                    # Record authenticated lobby reach for the named journey funnel.
                    guest_analytics.record_event(seeded_guest['user']['guest_analytics_id'],'lobby_reached')
                    # Record one visible game-engagement aggregate for the Admin table.
                    guest_analytics.record_event(seeded_guest['user']['guest_analytics_id'],'game_open','slots',latency_ms=25)
                    # Record one server-classified completion and fake-token aggregate for the funnel and game metrics.
                    guest_analytics.record_event(seeded_guest['user']['guest_analytics_id'],'game_action','slots',action='spin',latency_ms=125,wagered=1,returned=2,round_started=True,round_completed=True)
                    # Record one sanitized validation category for the complete error filter without request text.
                    guest_analytics.record_event(seeded_guest['user']['guest_analytics_id'],'game_error','slots',action='spin',latency_ms=20,error_category='VALIDATION_ERROR')
                # Collect one responsive result per locale and viewport.
                admin_guest_results=[]
                # Exercise both installed Admin locales.
                for locale in ('en-US','ru-RU'):
                    # Switch the Admin runtime without persisting beyond the disposable browser copy.
                    page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:false}); }",locale)
                    # Open the dedicated Guest Trials section through its visible sidebar tab.
                    page.get_by_test_id('admin-tab-guests').click(); page.get_by_test_id('admin-guest-summary').wait_for(timeout=WAIT_MS)
                    # Filter to the active locale and desktop-class seeded row.
                    with page.expect_response(lambda response: '/api/v2/admin/guest-trials?' in response.url and f'locale={locale}' in response.url):
                        # Select the active locale filter through its native control.
                        page.locator('#guest-filter-locale').select_option(locale)
                    # Wait for the filtered funnel to replace the prior content.
                    page.get_by_test_id('admin-guest-summary').wait_for(timeout=WAIT_MS)
                    # Filter to the seeded device class through the visible control.
                    with page.expect_response(lambda response: '/api/v2/admin/guest-trials?' in response.url and 'device=desktop' in response.url):
                        # Select the seeded coarse device class through its native control.
                        page.locator('#guest-filter-device').select_option('desktop')
                    # Wait for the device-filtered funnel to replace the prior content.
                    page.get_by_test_id('admin-guest-summary').wait_for(timeout=WAIT_MS)
                    # Apply the bounded thirty-day time range through its visible shortcut.
                    with page.expect_response(lambda response: '/api/v2/admin/guest-trials?' in response.url and 'since=' in response.url):
                        # Select the recent-window filter.
                        page.locator('#guest-filter-range').select_option('30')
                    # Apply the registered game filter.
                    with page.expect_response(lambda response: '/api/v2/admin/guest-trials?' in response.url and 'game=slots' in response.url):
                        # Select the seeded catalog game.
                        page.locator('#guest-filter-game').select_option('slots')
                    # Apply the first-round-completed filter.
                    with page.expect_response(lambda response: '/api/v2/admin/guest-trials?' in response.url and 'completed=yes' in response.url):
                        # Select the affirmative completion state.
                        page.locator('#guest-filter-completed').select_option('yes')
                    # Apply the sanitized server-error filter.
                    with page.expect_response(lambda response: '/api/v2/admin/guest-trials?' in response.url and 'error_category=VALIDATION_ERROR' in response.url):
                        # Select the seeded validation category.
                        page.locator('#guest-filter-error_category').select_option('VALIDATION_ERROR')
                    # Require the complete funnel and game-engagement sections.
                    assert int(page.get_by_test_id('admin-guest-started').inner_text().replace(',','').replace('\xa0',''))>=1
                    # Require the owner-facing admission control and fixed 10,000-token disclosure.
                    assert page.get_by_test_id('admin-guest-policy').is_visible() and page.get_by_test_id('admin-guest-trials-enabled').is_checked() and '10' in page.get_by_test_id('admin-guest-policy').inner_text()
                    # Require the engaged and completed-round milestones to include the seeded row.
                    assert int(page.get_by_test_id('admin-guest-engaged').inner_text().replace(',','').replace('\xa0',''))>=1 and int(page.get_by_test_id('admin-guest-completed').inner_text().replace(',','').replace('\xa0',''))>=1
                    # Require all named funnel rows, detailed game metrics, and fake-token summary cards.
                    assert page.get_by_test_id('admin-guest-funnel').locator('tbody tr, tr').count()>=10 and page.get_by_test_id('admin-guest-game-detail').is_visible() and '1' in page.get_by_test_id('admin-guest-summary').inner_text()
                    # Require one analytics-only row and open its bounded detail.
                    guest_first_row=page.get_by_test_id('admin-guest-row').first; guest_first_row.wait_for(timeout=WAIT_MS)
                    # Read the visible row for identifier privacy checks.
                    guest_row_text=guest_first_row.inner_text()
                    # Require no email or raw auth/player/session identifier pattern.
                    assert 'gtrial_' in guest_row_text and '@' not in guest_row_text and 'player_' not in guest_row_text.lower() and 'session_' not in guest_row_text.lower() and 'user_' not in guest_row_text.lower()
                    # Capture the Admin-assisted conversion request without mutating the seeded browser fixture.
                    assisted_requests=[]
                    # Bound diagnostics produced by the intentional first-attempt service failure.
                    assisted_console_index=len(console_errors); assisted_http_index=len(http_errors); assisted_page_index=len(page_errors)
                    # Fail the first response and fulfill the retry so the browser proves one caller-stable operation identity.
                    page.route('**/api/v2/admin/guest-trials/convert',lambda route: (assisted_requests.append(route.request.post_data_json),route.fulfill(status=503,content_type='application/json',body=json.dumps({'ok':False,'error':{'code':'SERVICE_UNAVAILABLE','message':'temporary failure'}})) if len(assisted_requests)==1 else route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'status':'converted','replayed':True,'email':f'assisted-{locale}@example.test','display_name':'Assisted Browser Guest','balance':10000,'player_preserved':True}}))))
                    # Select this active analytics row through its visible conversion shortcut.
                    guest_first_row.locator('.guest-convert-button').click(); assert page.get_by_test_id('admin-guest-conversion-identity').input_value().startswith('gtrial_')
                    # Fill only transient target-account content into the explicit support form.
                    page.get_by_test_id('admin-guest-conversion-email').fill(f'assisted-{locale}@example.test'); page.get_by_test_id('admin-guest-conversion-display-name').fill('Assisted Browser Guest'); page.get_by_test_id('admin-guest-conversion-password').fill('BrowserAssistedPassw0rd!23')
                    # Require literal confirmation before submitting the first bounded conversion request.
                    page.get_by_test_id('admin-guest-conversion-confirm').check(); page.get_by_test_id('admin-guest-conversion-submit').click(); page.wait_for_function("() => !document.querySelector('[data-testid=\"admin-guest-conversion-submit\"]')?.disabled && document.querySelector('[data-testid=\"admin-guest-conversion-password\"]')?.value === '' && !document.querySelector('[data-testid=\"admin-guest-conversion-confirm\"]')?.checked",timeout=WAIT_MS)
                    # Re-enter only the cleared credential and confirmation before retrying the exact form operation.
                    page.get_by_test_id('admin-guest-conversion-password').fill('BrowserAssistedPassw0rd!23'); page.get_by_test_id('admin-guest-conversion-confirm').check(); page.get_by_test_id('admin-guest-conversion-submit').click(); page.wait_for_function("() => document.querySelector('[data-testid=\"admin-guest-conversion-password\"]')?.value === '' && !document.querySelector('[data-testid=\"admin-guest-conversion-confirm\"]')?.checked",timeout=WAIT_MS)
                    # Stop intercepting after the exact single request has caused the normal Guest Trials rerender.
                    page.unroute('**/api/v2/admin/guest-trials/convert')
                    # Isolate only the diagnostics emitted by the controlled failed first attempt.
                    assisted_console=console_errors[assisted_console_index:]; assisted_http=http_errors[assisted_http_index:]; assisted_page=page_errors[assisted_page_index:]
                    # Require one expected browser resource diagnostic and one matching HTTP rejection with no JavaScript error.
                    assert assisted_page==[] and len(assisted_console)==1 and all('Failed to load resource' in value for value in assisted_console) and len(assisted_http)==1 and assisted_http[0].startswith('503 ') and assisted_http[0].endswith('/api/v2/admin/guest-trials/convert')
                    # Remove only the verified controlled failure so every unexpected later diagnostic still fails the suite.
                    del console_errors[assisted_console_index:]; del http_errors[assisted_http_index:]
                    # Require analytics-only targeting, explicit confirmations, one stable retry key, and cleared credential controls after success.
                    assert len(assisted_requests)==2 and assisted_requests[0]['guest_identity'].startswith('gtrial_') and all(request['confirm'] is True and request['accepted'] is True for request in assisted_requests) and len(assisted_requests[0]['idempotency_key'])>=16 and assisted_requests[0]['idempotency_key']==assisted_requests[1]['idempotency_key'] and page.get_by_test_id('admin-guest-conversion-password').input_value()=='' and not page.get_by_test_id('admin-guest-conversion-confirm').is_checked()
                    # Re-resolve the first filtered row after the conversion-success rerender.
                    guest_first_row=page.get_by_test_id('admin-guest-row').first; guest_first_row.wait_for(timeout=WAIT_MS)
                    # Open the analytics-only detail through the keyboard-focusable action.
                    guest_first_row.locator('.guest-detail-button').focus(); guest_first_row.locator('.guest-detail-button').press('Enter'); page.wait_for_function("() => document.querySelector('[data-testid=\"admin-guest-detail\"] dd')?.textContent.includes('gtrial_')")
                    # Require the allowlisted server event timeline to render without a raw session replay.
                    page.get_by_test_id('admin-guest-timeline').wait_for(timeout=WAIT_MS); assert page.get_by_test_id('admin-guest-timeline').locator('tr').count()>=2
                    # Focus the wide recent table region and exercise native End-key scrolling.
                    recent_region=page.get_by_test_id('admin-guest-recent'); recent_region.focus(); recent_region.press('End')
                    # Require the cleanup health surface and run its fixed server cleanup action once per locale.
                    page.get_by_test_id('admin-guest-cleanup-status').wait_for(timeout=WAIT_MS)
                    with page.expect_response(lambda response: response.url.endswith('/api/v2/admin/guest-trials/cleanup') and response.request.method=='POST'):
                        # Activate the protected cleanup control through the visible Admin surface.
                        page.get_by_test_id('admin-guest-cleanup').click()
                    # Wait for the refreshed Guest Trials funnel after cleanup.
                    page.get_by_test_id('admin-guest-summary').wait_for(timeout=WAIT_MS)
                    # Exercise every exact governed viewport for this locale.
                    for viewport_id,viewport in guest_admin_viewports.items():
                        # Resize the complete Admin document before containment inspection.
                        page.set_viewport_size(viewport); page.wait_for_timeout(150)
                        # Reopen Guest Trials because mobile navigation and refresh can move focus only, never state.
                        page.get_by_test_id('admin-tab-guests').click(); page.get_by_test_id('admin-guest-summary').wait_for(timeout=WAIT_MS)
                        # Reopen the bounded de-identified detail so each viewport artifact actually contains its claimed timeline state.
                        page.get_by_test_id('admin-guest-row').first.locator('.guest-detail-button').click(); page.get_by_test_id('admin-guest-timeline').wait_for(timeout=WAIT_MS)
                        # Require page containment plus intentional horizontal containment on table regions.
                        contained=page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1 && [...document.querySelectorAll('[data-testid=\"admin-guest-funnel\"], [data-testid=\"admin-guest-games\"], [data-testid=\"admin-guest-game-detail\"], [data-testid=\"admin-guest-recent\"]')].every(region => region.scrollWidth >= region.clientWidth)")
                        # Require every filter, clickable checkbox row, and action to meet the approved 42 CSS-pixel floor.
                        targets=page.locator('[data-testid="admin-guest-filters"] select, [data-testid="admin-guest-filters"] button, [data-testid="admin-guest-policy"] label.check-row, [data-testid="admin-guest-policy"] button, [data-testid="admin-guest-conversion"] input:not([type="checkbox"]), [data-testid="admin-guest-conversion"] label.check-row, [data-testid="admin-guest-conversion"] button, .guest-detail-button, .guest-convert-button')
                        # Inspect all rendered Guest Trials interactive controls.
                        target_floor=all((targets.nth(index).bounding_box() or {}).get('height',0)>=41.5 for index in range(targets.count()))
                        # Focus the table region for visible keyboard evidence.
                        page.get_by_test_id('admin-guest-recent').focus()
                        # Capture exact-head EN/RU responsive funnel, games, filters, detail, cleanup, and keyboard evidence.
                        game_evidence(f'after-pass-admin-guest-trials-{locale}-{viewport_id}.png','admin',['guest_trials_funnel','guest_trials_nine_stage_funnel','guest_trials_metrics','guest_trials_fake_tokens','guest_trials_games','guest_trials_filters','guest_trials_assisted_conversion','guest_trials_detail','guest_trials_timeline','guest_trials_cleanup_status','guest_trials_keyboard_scroll'],locale,viewport_id)
                        # Record explicit reduced-motion and 200 percent zoom acceptance once per locale at the primary desktop viewport.
                        if viewport_id=='desktop_primary':
                            # Emulate the operating-system reduced-motion preference on the populated Admin surface.
                            page.emulate_media(reduced_motion='reduce'); assert page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
                            # Capture reduced-motion evidence with the complete populated state still visible.
                            game_evidence(f'after-pass-admin-guest-reduced-motion-{locale}-{viewport_id}.png','admin',['guest_trials_funnel','guest_trials_reduced_motion'],locale,viewport_id)
                            # Apply 200 percent CSS zoom with the equivalent half-width layout constraint.
                            page.evaluate("() => { document.body.style.zoom='200%'; document.body.style.width='50%'; }"); page.wait_for_timeout(100)
                            # Require the funnel and cleanup health to remain visible at the zoomed scale.
                            assert page.get_by_test_id('admin-guest-summary').is_visible() and page.get_by_test_id('admin-guest-cleanup-status').is_visible()
                            # Capture localized 200 percent zoom evidence independently from the viewport matrix.
                            game_evidence(f'after-pass-admin-guest-zoom-200-{locale}-{viewport_id}.png','admin',['guest_trials_funnel','guest_trials_zoom_200'],locale,viewport_id)
                            # Restore normal zoom and motion before the next viewport or unrelated Admin case.
                            page.evaluate("() => { document.body.style.zoom=''; document.body.style.width=''; }"); page.emulate_media(reduced_motion='no-preference')
                        # Record responsive containment and target-floor result.
                        admin_guest_results.append({'locale':locale,'viewport':viewport_id,'contained':contained,'target_floor':target_floor})
                # Require exactly both locales by all four viewports with complete containment and accessible targets.
                assert len(admin_guest_results)==8 and all(result['contained'] and result['target_floor'] for result in admin_guest_results)
            # Irreversibly end seeded principals regardless of browser assertion outcome.
            finally:
                # Revoke each disposable identity and wallet through canonical lifecycle teardown.
                for seeded_guest in seeded_guests: auth_core.end_guest_trial(seeded_guest['user'],'revoked')
                # Restore the exact pre-test de-identified telemetry document after every success or failure.
                write_json(guest_analytics.TRIALS_PATH,original_analytics)
        # Execute the de-identified Guest Trials Admin regression.
        run_case('BR-ADMIN-GUEST-001',['GUEST-001','GUEST-003','GUEST-004','GUEST-005','ADMIN-035','TEST-081','TEST-193'],admin_guest_trials_browser)
        page.get_by_test_id('admin-tab-audio').click(); page.get_by_test_id('admin-save-audio').wait_for(timeout=WAIT_MS)
        run_case('BR-AUDIO-001',['AUDIO-002','AUDIO-005'],lambda: page.get_by_test_id('admin-preview-voice').is_visible())
        # Define the Phase 0 registry, formatter, fallback, discovery, and visual evidence gate.
        def localization_foundation_browser():
            # Open the generic Admin Language/Locale surface.
            page.get_by_test_id('admin-tab-language').click()
            # Wait for the complete locked registry rather than one hard-coded locale control.
            page.get_by_test_id('admin-locale-registry').wait_for(timeout=WAIT_MS)
            # Read the public runtime state used by shell and Admin selectors.
            foundation_state=page.evaluate("() => window.CasinoI18n.getLocaleState()")
            # Require all 25 metadata identities while exposing only complete English and Russian packs.
            assert len(foundation_state['localeRegistry'])==25 and [locale['id'] for locale in foundation_state['locales']]==['en-US','ru-RU']
            # Require the visible selector to exclude every metadata-only locale.
            assert page.get_by_test_id('admin-language-select').locator('option').count()==2
            # Require formatter selection to expose the registry's deterministic Intl identities independently from translations.
            assert page.get_by_test_id('admin-format-locale-select').locator('option').count()>=23
            # Load every bundled script and fullwidth-punctuation subset before evaluating or capturing the native-label registry.
            font_results=page.evaluate("""async () => { const samples=[['Casino Locale CJK','简体中文日本語廣東話香港繁體'],['Casino Locale CJK','（）'],['Casino Locale Devanagari','हिन्दीमराठी'],['Casino Locale Bengali','বাংলা'],['Casino Locale Tamil','தமிழ்'],['Casino Locale Telugu','తెలుగు']]; const rows=[]; for (const [family,text] of samples) { const declaration=`700 18px "${family}"`; const faces=await document.fonts.load(declaration,text); rows.push({family,text,loaded:faces.length>0,ready:document.fonts.check(declaration,text)}); } await document.fonts.ready; return rows; }""")
            # Reject hosted evidence when any required native-script asset is absent or not ready.
            assert all(result['loaded'] and result['ready'] for result in font_results), font_results
            # Validate every locked translation tag and configured formatter with the exact browser Intl runtime.
            intl_results=page.evaluate("() => window.CasinoI18n.getLocaleState().localeRegistry.map(locale => { try { const identity=new Intl.Locale(locale.id).toString(); const number=new Intl.NumberFormat(locale.formatLocale).format(12345.67); const date=new Intl.DateTimeFormat(locale.formatLocale).format(new Date('2032-02-03T04:05:06Z')); return { id: locale.id, identity, number, date, ok: Boolean(identity && number && date) }; } catch (error) { return { id: locale.id, ok: false, error: error.name }; } })")
            # Fail with bounded identity-only diagnostics if any configured browser formatter is unavailable.
            assert all(result['ok'] for result in intl_results), intl_results
            # Ask the real authenticated catalog for every current game-owned translation domain.
            catalog_result=page.evaluate("async () => { const response=await fetch('/api/v1/casino/state'); const payload=await response.json(); const games=payload.data.games; const i18n=await import('/core/i18n.js'); const discovered=i18n.registerI18nDomains(games.map(game => game.frontend.i18n_domain)); return { gameCount: games.length, gameDomains: games.map(game => game.frontend.i18n_domain), discovered }; }")
            # Require every unique live game domain in runtime diagnostics without a static game allowlist.
            assert catalog_result['gameCount']==len(set(catalog_result['gameDomains'])) and set(catalog_result['gameDomains']).issubset(set(catalog_result['discovered']))
            # Enter browser-default mode before proving a later concrete selector choice takes ownership.
            selector_state=page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('browser',{persistLocal:true,nextUseBrowserLocale:true,nextFormatLocale:'browser'}); return await i18n.setLocale('ru-RU',{persistLocal:false}); }")
            # Require an explicit ready locale to exit browser-default resolution without a reload.
            assert selector_state['locale']=='ru-RU' and selector_state['useBrowserLocale'] is False
            # Attempting an unfinished RTL locale must retain the installed English UI and safe LTR root.
            fallback_state=page.evaluate("async () => { const i18n=await import('/core/i18n.js'); const state=await i18n.setLocale('ar',{persistLocal:false,nextUseBrowserLocale:false}); return { locale:state.locale, dir:document.documentElement.dir, lang:document.documentElement.lang }; }")
            # Reject silent English masquerading as Arabic by requiring explicit selectable-readiness fallback.
            assert fallback_state=={'locale':'en-US','dir':'ltr','lang':'en-US'}
            # Define every governed Admin viewport for exact-head localization evidence.
            localization_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
            # Capture the generic registry in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch through the production runtime without persisting beyond the disposable browser copy.
                page.evaluate("async locale => { const i18n=await import('/core/i18n.js'); await i18n.setLocale(locale,{persistLocal:true,nextUseBrowserLocale:false}); }",locale)
                # Wait for the locale-driven Admin rerender to restore the foundation surface.
                page.get_by_test_id('admin-localization-foundation').wait_for(timeout=WAIT_MS)
                # Require all locked entries after each in-place language switch.
                assert page.get_by_test_id('admin-locale-registry-entry').count()==25
                # Reject replacement characters and unresolved interpolation placeholders in visible foundation copy.
                foundation_text=page.get_by_test_id('admin-localization-foundation').inner_text()
                # Preserve clean real copy across all native labels and translated headings.
                assert '�' not in foundation_text and '{ready}' not in foundation_text and '{total}' not in foundation_text
                # Reset both desktop Admin and mobile document scroll owners before evidence capture.
                page.evaluate("() => { const content=document.querySelector('.admin-content'); if (content) content.scrollTop=0; window.scrollTo(0,0); }")
                # Exercise every required viewport with horizontal containment and after-pass evidence.
                for viewport_id,viewport in localization_viewports.items():
                    # Resize to the exact governed dimensions before layout inspection.
                    page.set_viewport_size(viewport); page.wait_for_timeout(150)
                    # Keep each artifact anchored at the foundation heading after responsive ownership changes.
                    page.evaluate("() => { const content=document.querySelector('.admin-content'); if (content) content.scrollTop=0; window.scrollTo(0,0); }")
                    # Reject page-level horizontal overflow on the complete registry surface.
                    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
                    # Save self-describing full-page evidence so all 25 metadata cards remain reviewable with exact-source provenance.
                    game_evidence(f'after-pass-admin-localization-foundation-{locale}-{viewport_id}.png','admin',['localization_locked_registry','localization_selector_persistence','localization_formatter_metadata','localization_catalog_domains','localization_safe_fallback'],locale,viewport_id)
            # Restore the primary viewport and English without leaving a browser preference behind.
            page.set_viewport_size({'width':1920,'height':1080}); page.evaluate("async () => { const i18n=await import('/core/i18n.js'); await i18n.setLocale('en-US',{persistLocal:false,nextUseBrowserLocale:false}); localStorage.removeItem('casino.locale.settings.v1'); }")
        # Record locked registry, browser Intl, safe fallback, catalog discovery, and governed visual evidence.
        run_case('BR-I18N-FOUNDATION-001',['I18N-006','I18N-007','TEST-101'],localization_foundation_browser)
        # Define the admin_i18n function used by this module.
        def admin_i18n():
            # Load canonical Russian Admin copy for exact table-header assertions.
            admin_copy=read_i18n_json(ROOT/'web'/'i18n'/'ru-RU'/'admin.json')
            # Open the new Language/Locale tab.
            page.get_by_test_id('admin-tab-language').click()
            # Wait for the language select to render.
            page.get_by_test_id('admin-language-select').wait_for(timeout=WAIT_MS)
            # Select Russian as the display language.
            page.get_by_test_id('admin-language-select').select_option('ru-RU')
            # Apply the locale and persist the browser-local setting.
            page.get_by_test_id('admin-locale-apply').click()
            # Wait for the runtime state to report Russian.
            page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'ru-RU'")
            # Wait for the rendered diagnostics to catch up with the runtime state.
            page.wait_for_function("() => document.querySelector('[data-testid=\"admin-locale-state\"]')?.textContent?.includes('ru-RU')")
            assert 'ru-RU' in page.get_by_test_id('admin-locale-state').inner_text()
            # Reload Admin to verify browser-local persistence.
            page.reload(wait_until='networkidle')
            # Wait for the reloaded runtime to restore Russian.
            page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'ru-RU'")
            # Reopen Language/Locale after reload so diagnostics are visible.
            page.get_by_test_id('admin-tab-language').click()
            # Wait for the rendered diagnostics to show restored Russian.
            page.wait_for_function("() => document.querySelector('[data-testid=\"admin-locale-state\"]')?.textContent?.includes('ru-RU')")
            assert 'ru-RU' in page.get_by_test_id('admin-locale-state').inner_text()
            # Reopen Players & Bots to verify the affected Admin surface uses Russian resources.
            page.get_by_test_id('admin-tab-players').click()
            # Wait for the localized practice-opponent heading to render.
            page.get_by_text("Тренировочные соперники Texas Hold'em",exact=True).wait_for(timeout=WAIT_MS)
            # Require dynamic controller activity to use Russian rather than English fallback copy.
            assert 'Fund Account' not in page.get_by_test_id('practice-opponent-admin').inner_text() and 'Пополнение счёта' in page.get_by_test_id('practice-opponent-admin').inner_text()
            # Require the players table to use the exact Russian resource-owned headers.
            assert page.locator('#adminView table').first.locator('th').all_inner_texts()==[admin_copy[key] for key in ('players.id','players.name','players.type','players.balance')]
            # Open Users and wait for the account-only managed-user table.
            page.get_by_test_id('admin-tab-users').click(); page.get_by_test_id('admin-users-managed-table').wait_for(timeout=WAIT_MS)
            # Require every managed-user header to match the Russian dictionary exactly.
            assert page.get_by_test_id('admin-users-managed-table').locator('th').all_inner_texts()==[admin_copy[key] for key in ('users.email','users.name','users.accessControls','users.tokenBalance','users.tokenState','users.terms','users.language','users.format','users.actions')]
            # Open Autoplay and wait for its resource-owned heading to replace the prior Users view.
            page.get_by_test_id('admin-tab-autoplay').click(); page.locator('#adminView h3',has_text=admin_copy['autoplay.sessions']).wait_for(timeout=WAIT_MS)
            # Require every autoplay header to match the Russian dictionary exactly.
            assert page.locator('#adminView table').first.locator('th').all_inner_texts()==[admin_copy[key] for key in ('autoplay.id','autoplay.game','autoplay.player','autoplay.status','autoplay.speed','autoplay.completed','autoplay.limit','autoplay.updated')]
            # Open Requirements and wait for its localized heading to replace the prior Autoplay view.
            page.get_by_test_id('admin-tab-requirements').click(); page.locator('#adminView h3',has_text=admin_copy['nav.requirements']).wait_for(timeout=WAIT_MS)
            # Require every requirements header to match the Russian dictionary exactly.
            assert page.locator('#adminView table').first.locator('th').all_inner_texts()==[admin_copy[key] for key in ('requirements.id','requirements.module','requirements.description','requirements.status','requirements.tests')]
            # Return to Players & Bots before capturing the affected Admin visual evidence.
            page.get_by_test_id('admin-tab-players').click(); page.get_by_test_id('practice-opponent-admin').wait_for(timeout=WAIT_MS)
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
        run_case('BR-I18N-ADMIN-001',['I18N-001','I18N-003','I18N-014','TEST-187'],admin_i18n)
    # Preserve exact Admin-presentation case accounting on non-owning shards.
    else:
        # Advance only the audio and localization presentation range.
        skip_browser_affinity('admin_presentation')
