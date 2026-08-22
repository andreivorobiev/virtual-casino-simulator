# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own independent Roulette, Slots, and Keno Browser affinity families."""

# Import JSON parsing for exact browser-returned diagnostics and persisted-state fixtures.
import json
# Import regular expressions for visible money-label and localization diagnostics.
import re
# Import monotonic waits retained by the extracted game-state transitions.
import time
# Import disposable directories for browser-only diagnostic publication proofs.
import tempfile
# Import portable paths for disposable browser-only artifact assertions.
from pathlib import Path

# Import the sole environment-scalable Playwright wait budget. (TEST-053)
from tests.browser_timing import WAIT_MS
# Import the pre-document shared-application boundary and sanitized first-failure writer. (TEST-053)
from tests.browser_readiness import install_shared_app_readiness_probe, persist_shared_app_first_failure, reload_and_wait_for_shared_app_readiness


# Execute each game-local producer/consumer family under its deterministic shard owner.
def run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,page,base,ROOT,browser_player_id,visual_matrix,save_player_game_state,roulette_i18n_failure_diagnostic,slots_engine,keno_engine,shot,viewport_shot,region_evidence,game_evidence,console_errors,page_errors,http_errors,evidence_commit,evidence_branch,screenshots):
    # Run only the stateful Roulette producer/consumer chain on its declared owner.
    if browser_shard_owns_group('roulette'):
        # Normalize viewport and motion state before mounting Roulette independently of prior groups.
        page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size({'width':1920,'height':1080})
        # Open Roulette by canonical route so this group does not inherit another game's navigation state.
        page.goto(base+'/games/roulette',wait_until='networkidle'); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
        # Normalize the player locale before the Roulette cases build their own localized state.
        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
        # Define the exhaustive hit-target integrity and geometry regression required by issue #222.
        def roulette_hit_target_integrity():
            # Define an exact clear-settlement guard so mode changes cannot race the asynchronous refund request. (issue #227)
            def clear_roulette_audit_bets():
                # Capture the documented clear response before activating the real rendered control.
                with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/clear') and response.request.method=='POST', timeout=WAIT_MS) as clear_info:
                    # Activate the same clear-all path a player uses rather than mutating test state directly.
                    page.locator('#clear').click()
                # Require the refund request to succeed before attempting a wheel-mode transition.
                assert clear_info.value.ok, 'Roulette audit-bet clear request failed'
                # Require the rerendered control to prove the browser consumed the empty-bet response.
                page.wait_for_function("() => document.querySelector('#clear')?.disabled === true", timeout=WAIT_MS)
            # Select the smallest chip so exhaustive region coverage cannot deplete the wallet.
            page.get_by_test_id('chip-1').click()
            # Read the semantic precision-layer state before changing it. (issue #348)
            spots_visible=page.locator('#toggleSpots').get_attribute('aria-pressed')=='true'
            # Exercise an already-visible layer through a complete hide/show round trip.
            if spots_visible: page.locator('#toggleSpots').click()
            # Expose the precision layer through its real semantic toggle before any pointer-path hit test.
            page.locator('#toggleSpots').click()
            # Require the rerendered control to report the visible inside-spot state truthfully.
            assert page.locator('#toggleSpots').get_attribute('aria-pressed')=='true', 'Roulette inside spots did not enter the visible state'
            # Read every fixed-table bet cell's stable identity and hit geometry without duplicating the control-rail fast-bet aliases. (issue #348)
            cells=page.evaluate("() => [...document.querySelectorAll('[data-testid=roulette-table] [data-cell-key]')].map(el => { const r=el.getBoundingClientRect(); return {key:el.getAttribute('data-cell-key'), type:el.getAttribute('data-bet-type'), covered:(el.getAttribute('data-covered')||'').split(',').filter(Boolean), x:r.left, y:r.top, w:r.width, h:r.height}; })")
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
                # Capture the exact completed wager POST triggered by activating this cell.
                with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/bets') and response.request.method=='POST', timeout=WAIT_MS) as response_info:
                    # Activate the cell through Playwright's real actionability-checked pointer path. (issue #348)
                    page.get_by_test_id('roulette-table').locator(selector).click()
                # Require authoritative wager completion before another bet or clear can overtake it.
                assert response_info.value.ok, f'{key}: Roulette wager request failed'
                # Read the posted bet body for identity verification.
                body=response_info.value.request.post_data_json
                # Require the posted bet type to match the clicked cell's canonical type.
                assert body['bet_type']==identity[key]['type'], f"{key}: posted {body['bet_type']} != {identity[key]['type']}"
                # Require the posted covered numbers to match the clicked cell's canonical set.
                assert {str(number) for number in body['covered_numbers']}=={str(number) for number in identity[key]['covered']}, f"{key}: covered mismatch"
                # Settle the board rerender before activating the next hit target.
                page.wait_for_timeout(25)
            # Capture the exact "2nd 12" wager the issue reported as mismatched.
            with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/bets') and response.request.method=='POST', timeout=WAIT_MS) as second_dozen_info:
                # Activate the reported second-dozen hit target through the real pointer path.
                page.locator('[data-cell-key="dozen:2"]').click()
            # Require the authoritative second-dozen response before reading or clearing its wager.
            assert second_dozen_info.value.ok, '2nd 12 wager request failed'
            # Read the second-dozen wager body.
            second_dozen=second_dozen_info.value.request.post_data_json
            # Require "2nd 12" to post the dozen covering exactly 13 through 24.
            assert second_dozen['bet_type']=='dozen' and {str(number) for number in second_dozen['covered_numbers']}=={str(number) for number in range(13,25)}, '2nd 12 did not post the 13-24 dozen'
            # Refund every audit wager so the board returns to its pre-audit betting state.
            clear_roulette_audit_bets()
            # Resolve the governed disclosure that owns wheel-mode and zero-rule settings.
            rules_disclosure=page.get_by_test_id('roulette-rules-disclosure')
            # Open advanced settings through the visible summary before exercising its native select controls.
            if rules_disclosure.get_attribute('open') is None: rules_disclosure.locator('summary').click()
            # Require the real mode field to become visible rather than bypassing disclosure actionability.
            page.get_by_test_id('roulette-mode').wait_for(state='visible', timeout=WAIT_MS)
            # Audit every zero-zone special in both supported wheel modes so no catalog combination can share a pointer target. (issue #348)
            for wheel_mode,expected_count in (('single',6),('double',10)):
                # Read the current rendered wheel mode before deciding whether an asynchronous settings request is required.
                current_mode=page.get_by_test_id('roulette-mode').input_value()
                # Change modes only when needed so every expected response corresponds to a real state transition.
                if current_mode!=wheel_mode:
                    # Capture the documented settings response that owns the catalog rerender.
                    with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/settings') and response.request.method=='POST', timeout=WAIT_MS) as settings_info:
                        # Select the requested wheel mode through the rendered control.
                        page.get_by_test_id('roulette-mode').select_option(wheel_mode)
                    # Require the mode transition to succeed before reading its zero-zone catalog.
                    assert settings_info.value.ok, f'Roulette {wheel_mode} mode settings request failed'
                # Wait for the independently loaded mode catalog to replace the previous mode's rendered targets. (TEST-166)
                page.wait_for_function("(expected) => document.querySelectorAll('[data-betid][data-bet-type=zero_split],[data-betid][data-bet-type=trio],[data-betid][data-bet-type=first_four],[data-betid][data-bet-type=top_line]').length === expected", arg=expected_count, timeout=WAIT_MS)
                # Require the semantic visibility state to survive the mode-owned rerender.
                assert page.locator('#toggleSpots').get_attribute('aria-pressed')=='true', f'Roulette {wheel_mode} mode hid inside spots after rerender'
                # Read only the mode-specific zero-zone targets and their real pointer rectangles.
                zero_cells=page.evaluate("() => [...document.querySelectorAll('[data-betid][data-bet-type=zero_split],[data-betid][data-bet-type=trio],[data-betid][data-bet-type=first_four],[data-betid][data-bet-type=top_line]')].map(el => { const r=el.getBoundingClientRect(); return {key:el.getAttribute('data-cell-key'), type:el.getAttribute('data-bet-type'), covered:(el.getAttribute('data-covered')||'').split(',').filter(Boolean), x:r.left, y:r.top, w:r.width, h:r.height}; })")
                # Require the complete authoritative single- or double-zero special inventory.
                assert len(zero_cells)==expected_count, f'Roulette {wheel_mode} exposed {len(zero_cells)} of {expected_count} zero-zone controls'
                # Compare every zero-zone pointer rectangle against every later one exactly once.
                for outer in range(len(zero_cells)):
                    # Visit later targets only so a rectangle never compares with itself.
                    for inner in range(outer+1,len(zero_cells)):
                        # Resolve the two physical pointer targets under review.
                        first=zero_cells[outer]; second=zero_cells[inner]
                        # Measure real horizontal overlap between the transformed viewport rectangles.
                        overlap_x=max(0,min(first['x']+first['w'],second['x']+second['w'])-max(first['x'],second['x']))
                        # Measure real vertical overlap between the transformed viewport rectangles.
                        overlap_y=max(0,min(first['y']+first['h'],second['y']+second['h'])-max(first['y'],second['y']))
                        # Reject stacked zero-zone controls before pointer activation can become ambiguous.
                        assert overlap_x*overlap_y<=2, f"Roulette {wheel_mode} overlaps {first['key']} and {second['key']}"
                # Index the mode-owned identities before request-body verification.
                zero_identity={cell['key']:cell for cell in zero_cells}
                # Pointer-click every zero-zone control rather than sampling one covered-number size.
                for key in zero_identity:
                    # Build the stable selector that survives each wager-owned rerender.
                    selector=f'[data-cell-key="{key}"]'
                    # Capture the exact completed wager request emitted by the real pointer activation.
                    with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/bets') and response.request.method=='POST', timeout=WAIT_MS) as zero_response:
                        # Exercise Playwright visibility, stability, hit testing, and pointer dispatch together.
                        page.locator(selector).click()
                    # Require authoritative completion before the next target or mode clear can overtake it.
                    assert zero_response.value.ok, f'{wheel_mode} {key}: Roulette wager request failed'
                    # Read the mode-specific wager body without relying on localized labels.
                    body=zero_response.value.request.post_data_json
                    # Require the backend bet type to match the exact target identity.
                    assert body['bet_type']==zero_identity[key]['type'], f"{wheel_mode} {key}: posted wrong bet type"
                    # Require the backend covered pockets to match the exact target identity.
                    assert {str(number) for number in body['covered_numbers']}=={str(number) for number in zero_identity[key]['covered']}, f"{wheel_mode} {key}: covered mismatch"
                # Refund this mode's complete zero-zone audit before changing the table or continuing the suite.
                clear_roulette_audit_bets()
            # Reacquire the disclosure after mode-owned rerenders so test cleanup targets the current DOM node.
            rules_disclosure=page.get_by_test_id('roulette-rules-disclosure')
            # Restore the documented collapsed state through the visible summary for downstream test isolation.
            if rules_disclosure.get_attribute('open') is not None: rules_disclosure.locator('summary').click()
            # Require advanced settings to be hidden again before handing the shared page to the next case.
            page.get_by_test_id('roulette-mode').wait_for(state='hidden', timeout=WAIT_MS)
        # Record the exhaustive Roulette hit-target integrity and geometry regression.
        run_case('BR-ROU-HITMAP-001',['ROU-002','ROU-005','ROU-007','ROU-011','ROU-012','ROU-013','ROU-014','ROU-015','ROU-016','ROU-017','ROU-044','ROU-045','ROU-057','TEST-053','TEST-092'],roulette_hit_target_integrity)
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
            # Prove the visible Clear bets control refunds an open, unspun wager instead of losing the stake. (issue #229)
            page.get_by_test_id('roulette-num-3').click(); page.locator('.bet-chip').first.wait_for(timeout=3000)
            # Require the open bet to first debit the authoritative balance on placement, proving one consistent escrow model. (issue #232)
            assert wait_balance(lambda value: value < refund_balance_before-0.005) < refund_balance_before-0.005
            # Clear the open bet through the visible Clear bets control rather than spinning or leaving the table.
            page.locator('#clear').click()
            # Require the authoritative balance to return to the pre-wager amount because clearing refunds the stake, never debiting it. (issue #229)
            assert abs(wait_balance(lambda value: abs(value-refund_balance_before)<0.005)-refund_balance_before)<0.005
            # Place one straight bet through the visible board and wait for the table chip to confirm the wager rendered.
            page.get_by_test_id('roulette-num-17').click(); page.locator('.bet-chip').first.wait_for(timeout=3000)
            # Require the open bet to have debited the authoritative balance before leaving the table.
            assert wait_balance(lambda value: value < refund_balance_before-0.005) < refund_balance_before-0.005
            # Leave the table without spinning by navigating back to the lobby, which unmounts Roulette and fires the refund.
            page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
            # Require the authoritative balance to return to the pre-wager amount because the open bet was refunded on leave.
            assert abs(wait_balance(lambda value: abs(value-refund_balance_before)<0.005)-refund_balance_before)<0.005
            # Reopen Roulette and require the refunded round to start with no lingering open-bet chips.
            page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
            # Require no open-bet chip to remain after the refund so the next round starts clean.
            assert page.locator('.bet-chip').count()==0
        # Record the refund-on-leave wallet-correctness regression before the standard betting acceptance continues.
        run_case('BR-ROU-REFUND-001',['ROU-060','ROU-062','TEST-073','TEST-096'],roulette_refund_on_leave)
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
                page.wait_for_function("n => document.querySelectorAll('.bet-item').length === n", arg=rows_before+1, timeout=WAIT_MS)
                # Read the newest slip label and require the exact catalog wording. (issues #230 #250)
                newest_label=page.locator('.bet-item').last.locator('span').first.inner_text().strip()
                assert newest_label==expected_label, (selector, newest_label, expected_label)
            # Clear any open bets so the audit starts and ends with an empty refunded slip.
            def clear_slip():
                # Skip when the slip is already empty because the clear control disables itself.
                if page.locator('.bet-item').count():
                    # Clear through the visible refund control and wait for the empty slip.
                    page.locator('#clear').click(); page.wait_for_function("() => document.querySelectorAll('.bet-item').length === 0", timeout=WAIT_MS)
            # Start from a clean slip after the preceding hit-map case.
            clear_slip()
            # Audit every American-wheel straight pocket so zero, double zero, and all 1-36 labels are authoritative. (issues #230 #250)
            for pocket in ['0','00']+[str(number) for number in range(1,37)]:
                # Require this exact visible pocket to add its number instead of a color or empty label.
                place_and_check(f'[data-testid="roulette-num-{pocket}"]',pocket)
            # Every FAST BETS shortcut places exactly one correctly typed bet, including repeat clicks. (issue #231)
            for fast_type,fast_label in (('red','Red'),('red','Red'),('odd','Odd'),('black','Black'),('even','Even'),('low','1-18'),('high','19-36')):
                place_and_check(f'[data-outbtn="{fast_type}"]',fast_label)
            # The equivalent grid outside cells register the same labels through the board surface. (issue #233)
            for grid_type,grid_label in (('red','Red'),('black','Black'),('odd','Odd'),('even','Even'),('low','1-18'),('high','19-36')):
                place_and_check(f'[data-testid="roulette-outside-{grid_type}"]',grid_label)
            # Audit every dozen cell through its stable catalog identity and canonical ordinal label.
            for dozen,dozen_label in ((1,'1st 12'),(2,'2nd 12'),(3,'3rd 12')):
                # Dispatch against the fixed-board hit target so scaled layouts do not alter identity coverage.
                place_and_check(f'[data-cell-key="dozen:{dozen}"]',dozen_label,use_dispatch=True)
            # Audit every column cell through its stable catalog identity and canonical label.
            for column in (1,2,3):
                # Dispatch against the fixed-board hit target so every governed column is exercised.
                place_and_check(f'[data-cell-key="column:{column}"]',f'Column {column}',use_dispatch=True)
            # Enumerate one representative hotspot per inside/special type straight from the rendered catalog markers. (issue #250)
            inside_targets=page.evaluate("() => { const seen={}; for (const spot of document.querySelectorAll('.spot')) { const type=spot.dataset.betType; if (!seen[type]) seen[type]={key:spot.dataset.cellKey,label:spot.title.replace(/ \\d+:1$/,'')}; } return Object.entries(seen).map(([type,info]) => ({type,key:info.key,label:info.label})); }")
            # Require the board to expose every governed inside and special bet type as a marker.
            assert {target['type'] for target in inside_targets} >= {'split','street','line','corner','zero_split','trio','top_line','snake'}, inside_targets
            # Place one bet per inside/special type and require its exact catalog label on the slip.
            for target in inside_targets:
                place_and_check(f"[data-cell-key=\"{target['key']}\"]",target['label'],use_dispatch=True)
            # Return all direct-surface audit stakes before exercising multi-component call bets.
            clear_slip()
            # Open the racetrack disclosure through its visible summary control.
            page.get_by_test_id('roulette-racetrack-disclosure').locator('summary').click()
            # Exercise every visible racetrack, neighbor, final, and complete-number control. (issue #250)
            for call_type in ('snake','voisins','tiers','orphelins','jeu_zero','neighbors','final','complete'):
                # Capture the authoritative component list returned for this exact visible activation.
                with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/call-bet') and response.request.method=='POST') as call_response_info:
                    # Activate the visible call-bet button instead of bypassing the player interaction path.
                    page.locator(f'[data-call="{call_type}"]').click()
                # Read the standard response envelope after the route has accepted the activation.
                call_payload=call_response_info.value.json()['data']
                # Derive the exact expected slip labels from the server-authoritative placed components.
                expected_call_labels=[component['label'] for component in call_payload['placed']]
                # Reject silent no-ops even when a call type legitimately expands to several rows.
                assert expected_call_labels, call_type
                # Wait until the rerendered slip contains every returned component and no extra row.
                page.wait_for_function("n => document.querySelectorAll('.bet-item').length === n",arg=len(expected_call_labels),timeout=WAIT_MS)
                # Read every rendered component label in stable response order.
                actual_call_labels=[label.strip() for label in page.locator('.bet-item span').all_inner_texts()]
                # Require the visible slip to match the exact authoritative label sequence.
                assert actual_call_labels==expected_call_labels,(call_type,actual_call_labels,expected_call_labels)
                # Refund this call group before the next control so row counts and wallet capacity stay isolated.
                clear_slip()
            # Restore the advanced racetrack disclosure to its governed collapsed baseline for downstream layout acceptance.
            page.get_by_test_id('roulette-racetrack-disclosure').locator('summary').click()
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
            # Read the complete cumulative locale state so a failure names the exact missing resources.
            roulette_locale_state=page.evaluate("() => window.CasinoI18n.getLocaleState()")
            # Verify the runtime did not encounter any missing resources during the normal shell and Roulette flow.
            assert roulette_locale_state['missingKeyCount'] == 0, roulette_i18n_failure_diagnostic(roulette_locale_state)
        # Define the premium_roulette_layout function used by this module.
        def premium_roulette_layout():
            # Require one lifecycle-owned external stylesheet and no retained inline owner.
            assert page.locator('link#roulette-styles[href="/games/roulette.css"]').count()==1 and page.locator('style#roulette-styles').count()==0
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
            # Reproduce the scaled mid-desktop viewport reported in production. (ROU-043, issue #570)
            page.set_viewport_size({'width':1706,'height':900}); page.wait_for_timeout(250)
            # Read transformed table and clipping-shell bounds after the compact breakpoint applies.
            mid_desktop=page.evaluate("() => { const table=document.querySelector('[data-testid=roulette-table]').getBoundingClientRect(); const shell=document.querySelector('.roulette-table-shell').getBoundingClientRect(); const spin=document.querySelector('[data-testid=roulette-spin]').getBoundingClientRect(); return {table:table.toJSON(),shell:shell.toJSON(),spin:spin.toJSON(),width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth}; }")
            # Require every table edge and the primary action to remain visible without page overflow.
            assert mid_desktop['scrollWidth']<=mid_desktop['width']+1 and mid_desktop['table']['left']>=mid_desktop['shell']['left']-1 and mid_desktop['table']['right']<=mid_desktop['shell']['right']+1 and mid_desktop['table']['bottom']<=mid_desktop['shell']['bottom']+1 and mid_desktop['spin']['bottom']<=mid_desktop['height']-54,mid_desktop
            # Capture after-pass evidence at the exact production-reported width.
            page.screenshot(path=str(screenshots/'after-pass-roulette-mid-desktop-contained.png'),full_page=False)
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
        run_case('BR-ROU-PREMIUM-001',['ROU-041','ROU-043','ROU-045','ROU-048','ROU-049','UX-007','UX-009','CORE-034'],premium_roulette_layout)
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
        # Read the module-owned cumulative locale state so a failure preserves exact diagnostics.
        roulette_module_locale_state=page.evaluate("import('/core/i18n.js').then(i18n => i18n.getLocaleState())")
        # Verify the English route resolved every requested i18n key.
        assert roulette_module_locale_state['missingKeyCount'] == 0, roulette_i18n_failure_diagnostic(roulette_module_locale_state)
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
            # Require grammatical Russian range prepositions on both outside-bet controls.
            assert '\u043e\u0442 1 \u0434\u043e 18' in page.get_by_test_id('roulette-premium').inner_text() and '\u043e\u0442 19 \u0434\u043e 36' in page.get_by_test_id('roulette-premium').inner_text()
            # Verify shared keyboard scroll semantics survive the localized game rerender.
            assert page.get_by_test_id('roulette-control-rail').get_attribute('tabindex')=='0'
            # Focus the real spin action, move away, and return by keyboard so focus-visible modality is genuine.
            page.get_by_test_id('roulette-spin').focus(); page.keyboard.press('Shift+Tab'); page.keyboard.press('Tab')
            # Read the actual keyboard-selected control and computed shared fallback outline.
            roulette_focus=page.evaluate("""() => { const active=document.activeElement; const style=getComputedStyle(active); return {testid:active?.getAttribute('data-testid'),visible:active?.matches(':focus-visible')||false,width:parseFloat(style.outlineWidth)||0,offset:parseFloat(style.outlineOffset)||0}; }""")
            # Require the route without a game-owned focus rule to receive the shared high-contrast fallback.
            assert roulette_focus=={'testid':'roulette-spin','visible':True,'width':3,'offset':2},roulette_focus
            # Record exact-head evidence of the fallback on a real localized game control.
            game_evidence('after-pass-game-polish-focus-roulette-ru-RU-desktop_primary.png','roulette',['betting','keyboard_focus'],'ru-RU','desktop_primary')
        run_case('BR-I18N-GAMESTATE-ROU-001',['I18N-001','I18N-002','I18N-010','ROU-046','TEST-117'],roulette_i18n_state)
        # Require the fresh non-Admin shell to remain silent before any explicit audio opt-in. (AUDIO-010)
        assert page.evaluate("() => window.__casinoAudioEvents.length") == 0
        # Define the exact local audio opt-in used by the announcement-specific regression. (AUDIO-010)
        roulette_audio_settings={'master_enabled':True,'sfx_enabled':True,'voice_enabled':True,'announce_roulette_results':True}
        # Fulfill only the helper's test-owned settings write without changing backend owner policy.
        page.route('**/api/v1/admin/audio-settings',lambda route: route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'settings':roulette_audio_settings}})))
        # Apply both the account-owned and Admin-owned explicit opt-ins through the public voice helper.
        page.evaluate("async settings => { const voice=await import('/core/voice.js'); voice.setPersonalSoundEnabled(true); await voice.saveVoiceSettings(settings); }",roulette_audio_settings)
        # Remove the exact route seam before the real spin and all downstream network assertions.
        page.unroute('**/api/v1/admin/audio-settings')
        # Capture the authoritative backend spin response while using the visible Roulette action.
        with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/spin') and response.request.method == 'POST') as roulette_spin_response_info:
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
        # Read the live CSS Animation identities and sampled keyframes from the resolving spin.
        roulette_motion_runtime=page.evaluate("""() => { const read = node => { const style = getComputedStyle(node); const animation = node.getAnimations()[0]; return { name: style.animationName, timing: style.animationTimingFunction, duration: style.animationDuration, keyframes: animation?.effect?.getKeyframes().length ?? 0 }; }; return { rotor: read(document.querySelector('[data-testid="roulette-rotor"]')), ball: read(document.querySelector('[data-testid="roulette-ball"]')) }; }""")
        # Define the hosted runtime proof for the tracked compatibility curves.
        def roulette_motion_curve_runtime():
            # Require the rotor to run the named sampled coast-down without a second easing layer.
            assert roulette_motion_runtime['rotor']=={'name':'roulettePremiumWheelSpin','timing':'linear','duration':'16.5s','keyframes':21}
            # Require the ball to use its corresponding sampled counter-rotation curve.
            assert roulette_motion_runtime['ball']=={'name':'roulettePremiumBallSpin','timing':'linear','duration':'16.5s','keyframes':21}
        # Record the exact live-animation identity before settlement removes the spinning classes.
        run_case('BR-ROU-MOTION-CURVE-001',['ROU-064','ROU-065','ROU-068','ROU-069','ROU-070','TEST-102'],roulette_motion_curve_runtime)
        # Read the spinning-state settlement card before the timed settlement rerender can replace it. (ROU-058, TEST-059)
        roulette_spinning_settlement_text=page.get_by_test_id('roulette-settlement-card').inner_text()
        # Define the player-facing spinning copy regression for issue #234.
        def roulette_spinning_settlement_copy():
            # Require the live card to show localized progress language instead of the old layout/debug note.
            assert ('Spin in progress' in roulette_spinning_settlement_text or 'Спин выполняется' in roulette_spinning_settlement_text) and 'No layout resize' not in roulette_spinning_settlement_text and 'Макет не меняет размер' not in roulette_spinning_settlement_text
        # Record the focused Roulette spinning-copy browser assertion.
        run_case('BR-ROU-SPINNING-COPY-001',['ROU-058','ROU-066','TEST-059'],roulette_spinning_settlement_copy)
        # Read the open bet-slip Remove button while the spin has locked the current wager set. (ROU-059, TEST-061)
        roulette_locked_remove_disabled=page.locator('[data-testid="roulette-bet-slip"] [data-clear]').first.is_disabled()
        # Define the focused locked-wager Remove-button regression for issue #240.
        def roulette_locked_remove_button():
            # Require the Remove action to be inert while the spin is resolving the already committed wager.
            assert roulette_locked_remove_disabled
        # Record the focused Roulette locked-wager remove-control browser assertion.
        run_case('BR-ROU-LOCKED-REMOVE-001',['ROU-059','ROU-063','ROU-066','TEST-061'],roulette_locked_remove_button)
        # Capture the locked spinning state before the backend result is presented.
        viewport_shot('roulette-premium-spinning.png')
        # Wait for the fixed result region to reach the settled phase.
        page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'settled'", timeout=20000)
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
        run_case('BR-ROU-001',['ROU-040','ROU-041','ROU-042','ROU-043','ROU-044','ROU-046','ROU-049','ROU-050','ROU-052','ROU-053','ROU-054','ROU-055','ROU-056','ROU-063','ROU-065','ROU-066','ROU-067','ROU-068','AUDIO-010'],premium_roulette_settled)
        # Let the short physical ball-settle accent complete before capturing static evidence.
        page.wait_for_timeout(700)
        # Capture settled-state visual evidence for the Roulette worker handback.
        shot('roulette-premium-settled.png')
        # Ask the hosted browser to apply the player's reduced-motion preference.
        page.emulate_media(reduced_motion='reduce')
        # Probe only the two genuine mounted motion channels after temporarily restoring their spin class.
        roulette_reduced_motion=page.evaluate("""() => { const rotor=document.querySelector('[data-testid="roulette-rotor"]'); const ball=document.querySelector('[data-testid="roulette-ball"]'); const rotorWasSpinning=rotor.classList.contains('spinning'); const ballWasSpinning=ball.classList.contains('spinning'); rotor.classList.add('spinning'); ball.classList.add('spinning'); const values={rotor:getComputedStyle(rotor).animationName,ball:getComputedStyle(ball).animationName}; rotor.classList.toggle('spinning',rotorWasSpinning); ball.classList.toggle('spinning',ballWasSpinning); return values; }""")
        # Restore the normal media preference before later Roulette interaction cases continue.
        page.emulate_media(reduced_motion='no-preference')
        # Define the reduced-motion runtime portion of the focused browser case.
        def roulette_reduced_motion_runtime():
            # Require both mounted Roulette motion channels to be suppressed by the actual media state.
            assert roulette_reduced_motion=={'rotor':'none','ball':'none'}
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
        page.wait_for_function("() => { const toast=document.querySelector('#toast'); return toast && !toast.hidden && toast.textContent.includes('No automatic action was placed'); }",timeout=WAIT_MS)
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
        page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'settled'", timeout=WAIT_MS * 2)
        run_case('BR-AUTO-ROU-001',['AUTO-003','AUTO-010','ROU-047'],lambda: page.get_by_text('Off').first.is_visible())
        # Collapse autoplay after verification so route-return evidence restores the gameplay-first composition.
        page.get_by_test_id('roulette-autoplay-disclosure').locator('summary').click()
        # Store the settled result before leaving the route.
        roulette_result_before_return=page.get_by_test_id('roulette-result-region').get_attribute('data-result-number')
        # Leave Roulette through the shared navigation to exercise route unmounting.
        page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slot-grid').wait_for(timeout=WAIT_MS)
        # Return to Roulette and wait for the premium wheel to remount from persisted state.
        page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
        # Verify the route return preserves the authoritative settled pocket.
        assert page.get_by_test_id('roulette-result-region').get_attribute('data-result-number') == roulette_result_before_return
        # Let the remounted route complete paint before capturing return evidence.
        page.wait_for_timeout(1200)
        # Capture route-return evidence after the complete unmount and remount cycle.
        shot('roulette-premium-route-return.png')
        # Define the complete exact-head Roulette normal/reduced evidence matrix required by the bounded presentation slice. (ROU-072)
        def roulette_presentation_evidence_matrix():
            # Read all four governed viewport dimensions from the authoritative visual matrix.
            presentation_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the exact desktop-primary, desktop-compact, tablet, and mobile inventory.
            assert set(presentation_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Exercise real normal and true reduced-motion spins as separate media states.
            for motion_mode,reduced_setting in (('normal','no-preference'),('reduced','reduce')):
                # Exercise both supported player locales through the visible shell control.
                for locale in ('en-US','ru-RU'):
                    # Capture every governed responsive layout through a fresh real action.
                    for viewport_id,viewport in presentation_viewports.items():
                        # Apply the exact preference, locale, and viewport before starting the action.
                        page.emulate_media(reduced_motion=reduced_setting); page.set_viewport_size(viewport); page.get_by_test_id('shell-locale-select').select_option(locale); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
                        # Place the smallest visible straight bet so each evidence row drives the real public action.
                        page.get_by_test_id('roulette-num-17').click(); page.locator('.bet-chip').first.wait_for(timeout=3000)
                        # Capture the authoritative response while starting the actual spin.
                        with page.expect_response(lambda response: response.url.partition('?')[0].endswith('/api/v1/games/roulette/spin') and response.request.method=='POST') as presentation_spin_response:
                            # Use the dominant game action rather than a synthetic CSS toggle.
                            page.get_by_test_id('roulette-spin').click()
                        # Wait for the actual mounted spinning presentation.
                        page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'spinning'",timeout=3000)
                        # Let the backend response enter the normal wrapper landing or reduced hold branch.
                        page.wait_for_timeout(140)
                        # Read live classes and computed motion without mutating the DOM under test.
                        diagnostics=page.evaluate("""() => { const root=document.querySelector('[data-testid="roulette-premium"]'); const wheel=document.querySelector('[data-testid="roulette-wheel"]'); const result=document.querySelector('[data-testid="roulette-result-region"]'); const rotor=document.querySelector('[data-testid="roulette-rotor"]'); const ball=document.querySelector('[data-testid="roulette-ball"]'); const orient=document.querySelector('[data-testid="roulette-wheel-orient"]'); const orbit=document.querySelector('[data-testid="roulette-ball-orbit"]'); const radial=document.querySelector('[data-testid="roulette-ball-radial"]'); const motion={rotor:getComputedStyle(rotor).animationName,ball:getComputedStyle(ball).animationName,orient:getComputedStyle(orient).transitionDuration,orbit:getComputedStyle(orbit).transitionDuration,radial:getComputedStyle(radial).transitionDuration}; return {visible:Boolean(root&&root.getClientRects().length),phase:result?.dataset.phase,reduced:wheel?.dataset.reducedMotion,rotorSpinning:rotor?.classList.contains('spinning'),ballSpinning:ball?.classList.contains('spinning'),motion,noOverflow:document.documentElement.scrollWidth<=window.innerWidth+1}; }""")
                        # Require the real action to remain mounted in its in-progress phase and inside the viewport.
                        assert diagnostics['visible'] and diagnostics['phase']=='spinning' and diagnostics['rotorSpinning'] and diagnostics['ballSpinning'] and diagnostics['noOverflow'],diagnostics
                        # Require the live route to report the exact media preference used for this evidence row.
                        assert diagnostics['reduced']==('true' if motion_mode=='reduced' else 'false'),diagnostics
                        # Require normal motion to run both tracked curves and at least one live landing-wrapper transition.
                        if motion_mode=='normal': assert diagnostics['motion']['rotor']!='none' and diagnostics['motion']['ball']!='none' and any(diagnostics['motion'][key]!='0s' for key in ('orient','orbit','radial')),diagnostics
                        # Require reduced motion to suppress both tracked curves and every landing-wrapper transition.
                        if motion_mode=='reduced': assert diagnostics['motion']['rotor']=='none' and diagnostics['motion']['ball']=='none' and all(diagnostics['motion'][key]=='0s' for key in ('orient','orbit','radial')),diagnostics
                        # Capture one source-bound sidecar while the changed branch is actively mounted.
                        game_evidence(f'after-pass-roulette-presentation-{motion_mode}-{locale}-{viewport_id}.png','roulette',['spinning',f'{motion_mode}_motion'],locale,viewport_id)
                        # Read the authoritative result from the exact response used by this evidence row.
                        presentation_result=str(presentation_spin_response.value.json()['data']['round']['result'])
                        # Wait for the actual action to settle before starting the next matrix row.
                        page.wait_for_function("() => document.querySelector('[data-testid=\"roulette-result-region\"]')?.dataset.phase === 'settled'",timeout=20000)
                        # Require result panel and wheel identity to converge on the response after the changed branch completes.
                        assert page.get_by_test_id('roulette-result-region').get_attribute('data-result-number')==presentation_result and page.get_by_test_id('roulette-wheel').get_attribute('data-selected-result')==presentation_result
            # Restore the ordinary English primary-desktop route for downstream Roulette checks.
            page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size(presentation_viewports['desktop_primary']); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.get_by_test_id('roulette-wheel').wait_for(timeout=WAIT_MS)
        # Execute both the legacy curve suppression check and the real sixteen-combination presentation matrix under one permanent case.
        def roulette_reduced_motion_and_presentation():
            # Preserve the existing exact reduced-motion runtime assertion.
            roulette_reduced_motion_runtime()
            # Execute the new real normal/reduced action matrix inside the same permanent owner case.
            roulette_presentation_evidence_matrix()
        # Extend the existing permanent reduced-motion case without adding a new Browser inventory row.
        run_case('BR-ROU-REDUCED-MOTION-001',['ROU-064','ROU-067','ROU-068','ROU-070','ROU-072','TEST-102'],roulette_reduced_motion_and_presentation)
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
    # Preserve exact case accounting when this shard does not own Roulette.
    else:
        # Advance only the contiguous Roulette registrations.
        skip_browser_affinity('roulette')
    # Run the stateful Slots producer/consumer chain on its independent owner.
    if browser_shard_owns_group('slots'):
        # Normalize viewport and motion state before mounting Slots independently of Roulette.
        page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size({'width':1920,'height':1080})
        # Navigate directly to the premium Slots route without consuming Roulette navigation state.
        page.goto(base+'/games/slots',wait_until='networkidle')
        # Wait for the fixed reel grid to mount before measuring layout stability.
        page.get_by_test_id('slot-grid').wait_for(timeout=WAIT_MS)
        # Normalize the player locale before the Slots cases build their own localized state.
        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
        # Capture the idle cabinet state for worker handback evidence.
        shot('slots_idle.png')
        # Capture the English Slots screen as after-pass shared shell and game-layout evidence.
        shot('after-pass-shell-slots-desktop.png')
        # Read the Slots surface copy so acceptance evidence cannot contain leaked resource keys.
        slots_evidence_text=page.get_by_test_id('slots-premium').inner_text()
        # Verify the after-pass game evidence contains user-facing copy rather than internal resource identifiers.
        assert 'controls.' not in slots_evidence_text and 'status.' not in slots_evidence_text and 'slots.' not in slots_evidence_text
        # Define the cross-formatter, localized, responsive play-token label acceptance case. (issue #286)
        def labeled_play_token_amounts():
            # Read all governed dimensions from the authoritative visual matrix instead of duplicating them.
            money_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the matrix to expose the complete issue-mandated desktop, tablet, and mobile set.
            assert set(money_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Bind each governed locale to the full play-token terminology required by the visual standard.
            localized_units={'en-US':'play tokens','ru-RU':'игровых токенов'}
            # Exercise the shared formatters and the real Slots surface in both governed locales.
            for locale,expected_unit in localized_units.items():
                # Switch through the player-visible shell control so the mounted Slots route follows the real locale path.
                page.get_by_test_id('shell-locale-select').select_option(locale)
                # Wait for the shared runtime and the visible round-cost amount to finish rerendering.
                page.wait_for_function("expected => window.CasinoI18n?.getLocaleState().locale === expected.locale && document.querySelector('[data-testid=\"slots-round-cost\"]')?.textContent.trim().endsWith(expected.unit)",arg={'locale':locale,'unit':expected_unit})
                # Invoke both public shared helpers through their browser module boundary at the active locale.
                formatter_values=page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); const ui=await import('/core/ui.js'); return {formatMoney:i18n.formatMoney(1234.5),money:ui.money(1234.5)}; }""")
                # Require both helpers to preserve the decorative diamond while adding the exact full localized label.
                assert all(value.startswith('◈') and value.endswith(f' {expected_unit}') for value in formatter_values.values()), formatter_values
                # Prevent either locale from accepting the other locale's wording by coincidence.
                assert ('play tokens' not in ' '.join(formatter_values.values())) if locale=='ru-RU' else ('игровых токенов' not in ' '.join(formatter_values.values()))
                # Exercise every governed viewport for responsive copy and geometry acceptance.
                for viewport_id,viewport in money_viewports.items():
                    # Resize the real route and allow responsive layout and localized copy to settle.
                    page.set_viewport_size(viewport); page.wait_for_timeout(150)
                    # Audit leaf-level visible play-token amounts so parent container text cannot mask clipping.
                    amount_diagnostics=page.evaluate("""expectedUnit => { const root=document.querySelector('[data-testid="slots-premium"]'); const nodes=[...root.querySelectorAll('*')].filter(element => [...element.childNodes].some(node => node.nodeType===Node.TEXT_NODE && node.textContent.includes('◈'))); const amounts=nodes.map(element => { const rect=element.getBoundingClientRect(); const style=getComputedStyle(element); return {text:element.textContent.trim(),left:rect.left,right:rect.right,width:rect.width,clientWidth:element.clientWidth,scrollWidth:element.scrollWidth,display:style.display,visibility:style.visibility,opacity:Number(style.opacity)}; }).filter(entry => entry.display!=='none' && entry.visibility!=='hidden' && entry.opacity>0 && entry.width>0); return {amounts,pageWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,allLabeled:amounts.every(entry => entry.text.endsWith(expectedUnit)),contained:amounts.every(entry => entry.left>=-1 && entry.right<=innerWidth+1 && entry.scrollWidth<=entry.clientWidth+1)}; }""",expected_unit)
                    # Require at least one real amount and reject missing labels, element clipping, and page overflow.
                    assert amount_diagnostics['amounts'] and amount_diagnostics['allLabeled'] and amount_diagnostics['contained'] and amount_diagnostics['pageWidth']<=amount_diagnostics['viewportWidth']+1, amount_diagnostics
                    # Capture exact-head after-pass evidence for this locale and governed viewport.
                    game_evidence(f'after-pass-labeled-money-slots-{locale.lower()}-{viewport_id}.png','slots',['idle','labeled_play_token_amounts'],locale,viewport_id)
            # Restore the default locale and primary desktop dimensions for the existing Slots regression sequence.
            page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size(money_viewports['desktop_primary'])
            # Wait for the restored visible amount before handing the route to later Slots cases.
            page.wait_for_function("() => document.querySelector('[data-testid=\"slots-round-cost\"]')?.textContent.trim().endsWith('play tokens')")
        # Execute the issue-mapped shared formatter and real Slots acceptance regression.
        run_case('BR-MONEY-LABEL-001',['UX-017','TEST-086'],labeled_play_token_amounts)
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
            payline_spin={'round_id':'slot-payline-acceptance','timestamp':'2026-07-20T00:00:00Z','stops':[0,0,0,0,0],'grid':payline_grid,'active_lines':20,'line_bet':1,'cost':20,**payline_result,'free_spin':False,'free_spins_remaining':0,'progressive_eligible':True,'progressive_before':slots_engine.PROGRESSIVE_SEED,'progressive_contribution':0.2,'progressive_hit':0.0,'progressive':slots_engine.PROGRESSIVE_SEED+0.2}
            # Resolve the authenticated browser player before writing isolated deterministic game state.
            payline_player=browser_player_id
            # Persist the authoritative result through the same state store the Slots route reads after refresh.
            save_player_game_state('slots',payline_player,{'last_spins':[payline_spin],'progressive':slots_engine.PROGRESSIVE_SEED+0.2,'progressive_basis':{'active_lines':slots_engine.PROGRESSIVE_QUALIFYING_LINES,'line_bet':slots_engine.PROGRESSIVE_QUALIFYING_LINE_BET},'free_spins':0})
            # Reload the real route so the overlay, result text, and history all recover from one authoritative state.
            page.reload(wait_until='networkidle'); page.get_by_test_id('slots-payline').wait_for(timeout=WAIT_MS)
            # Define a browser-side audit that compares every rendered SVG point with its actual cell center in screen coordinates.
            def audit_payline_geometry():
                # Center the bounded reel grid so fixed shell actions cannot mask symbol identity during elementFromPoint checks.
                page.get_by_test_id('slot-grid').evaluate("grid => grid.scrollIntoView({block:'center',inline:'nearest'})")
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
                page.get_by_test_id('shell-locale-select').select_option(locale); page.get_by_test_id('slots-payline').wait_for(timeout=WAIT_MS)
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
                    # Require the first three detailed lines, the remaining-win count, and total payout to agree with the engine outcome.
                    line_word='Line' if locale=='en-US' else 'Линия'; history_lines_word='lines' if locale=='en-US' else 'линий'; assert all(f'{line_word} {number}' in payline_result_text for number in (1,2,3)) and '17' in payline_result_text and str(int(payline_spin['payout'])) in payline_result_digits and f"{payline_spin['active_lines']} {history_lines_word}" in payline_history_text and payline_spin['round_id'] not in payline_history_text and str(int(payline_spin['payout'])) in payline_history_digits
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
            page.evaluate("document.body.style.zoom=''"); page.emulate_media(reduced_motion='reduce'); page.reload(wait_until='networkidle'); page.get_by_test_id('slots-payline').wait_for(timeout=WAIT_MS)
            # Exercise true reduced motion across both supported locales and every governed viewport.
            for locale in ('en-US','ru-RU'):
                # Switch through the visible shell so reduced-motion copy and layout follow the supported locale path.
                page.get_by_test_id('shell-locale-select').select_option(locale); page.get_by_test_id('slots-payline').wait_for(timeout=WAIT_MS)
                # Exercise every exact visual-matrix size under reduced motion.
                for viewport_id,viewport in payline_viewports.items():
                    # Resize the mounted route and let its observer realign the static overlay.
                    page.set_viewport_size(viewport)
                    # Require the reduced-motion rerender to expose static paths with the same exact geometry.
                    reduced_diagnostics=audit_payline_geometry(); require_payline_acceptance(reduced_diagnostics); assert reduced_diagnostics['reduced']=='true' and page.locator('[data-testid="slots-payline"] polyline').first.evaluate("path => { const style=getComputedStyle(path); return style.animationName==='none' && style.transitionDuration==='0s'; }")
                    # Capture the clear non-animated win treatment for this exact locale and viewport.
                    game_evidence(f'after-pass-slots-paylines-{locale}-{viewport_id}-reduced-motion.png','slots',['win','multi_win','reduced_motion','route_restored'],locale,viewport_id)
            # Restore the default media preference and route state for the existing Slots regression sequence.
            page.emulate_media(reduced_motion='no-preference'); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size(payline_viewports['desktop_primary']); page.reload(wait_until='networkidle'); page.get_by_test_id('slots-payline').wait_for(timeout=WAIT_MS); require_payline_acceptance(audit_payline_geometry())
        # Execute the payline-to-reel alignment regression.
        run_case('BR-SLOTS-PAYLINE-001',['SLOT-029','I18N-010','TEST-077','TEST-117'],slots_payline_alignment)
        # Exercise the changed Slots action branches across the complete exact-head normal/reduced evidence matrix. (SLOT-037)
        def slots_presentation_evidence_matrix():
            # Read all four governed viewport dimensions from the authoritative visual matrix.
            presentation_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the exact desktop-primary, desktop-compact, tablet, and mobile inventory.
            assert set(presentation_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Exercise real normal and true reduced-motion spins as separate action paths.
            for motion_mode,reduced_setting in (('normal','no-preference'),('reduced','reduce')):
                # Apply the operating-system motion preference before every route action in this group.
                page.emulate_media(reduced_motion=reduced_setting)
                # Exercise both supported player locales through the visible shell control.
                for locale in ('en-US','ru-RU'):
                    # Capture every governed responsive layout through a fresh real spin.
                    for viewport_id,viewport in presentation_viewports.items():
                        # Apply the exact locale and viewport before starting the action.
                        page.set_viewport_size(viewport); page.get_by_test_id('shell-locale-select').select_option(locale); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
                        # Use the smallest bounded fake-money setup for this presentation-only action.
                        page.get_by_test_id('slots-lines').select_option('1'); page.get_by_test_id('slots-line-bet').fill('0.01')
                        # Capture the authoritative response while starting the actual public spin.
                        with page.expect_response(lambda response: response.url.endswith('/api/v1/games/slots/spin') and response.request.method=='POST') as presentation_spin_response:
                            # Use the dominant game action rather than a synthetic motion helper.
                            page.get_by_test_id('slots-spin').click()
                        # Wait for the committed action and its backend result to enter the landing or comfort-hold branch.
                        page.wait_for_function("() => document.querySelector('[data-testid=\"slots-spin\"]')?.disabled === true",timeout=3000); presentation_spin_response.value
                        # Let the real landing setup or reduced hold paint one frame before inspection.
                        page.wait_for_timeout(40)
                        # Read live action classes and computed motion without mutating the DOM under test.
                        diagnostics=page.evaluate("""() => { const root=document.querySelector('[data-testid="slots-premium"]'); const spin=document.querySelector('[data-testid="slots-spin"]'); const cells=[...document.querySelectorAll('.slots-symbol.spinning')]; const layer=document.querySelector('[data-testid="slots-reel-motion"]'); const strips=[...document.querySelectorAll('.slots-reel-strip')]; const reels=[...document.querySelectorAll('.slots-reel')]; const firstStrip=strips[0]; const firstCell=cells[0]; return {visible:Boolean(root&&root.getClientRects().length),disabled:Boolean(spin?.disabled),reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,spinningCells:cells.length,layer:Boolean(layer),stripCount:strips.length,reelCount:reels.length,flying:strips.filter(strip => strip.classList.contains('is-flying')).length,stripTransition:firstStrip?getComputedStyle(firstStrip).transitionDuration:'0s',cellAnimation:firstCell?getComputedStyle(firstCell).animationName:'none',noOverflow:document.documentElement.scrollWidth<=window.innerWidth+1}; }""")
                        # Require the real action to remain mounted in its in-progress phase and inside the viewport.
                        assert diagnostics['visible'] and diagnostics['disabled'] and diagnostics['spinningCells']==15 and diagnostics['noOverflow'],diagnostics
                        # Require the live route to report the exact media preference used for this evidence row.
                        assert diagnostics['reduced']==(motion_mode=='reduced'),diagnostics
                        # Require normal motion to mount all five real landing strips with active travel.
                        if motion_mode=='normal': assert diagnostics['layer'] and diagnostics['stripCount']==5 and diagnostics['reelCount']==5 and diagnostics['flying']>0 and diagnostics['stripTransition']!='0s',diagnostics
                        # Require reduced motion to execute the bounded hold without any decorative strip overlay or cell animation.
                        if motion_mode=='reduced': assert not diagnostics['layer'] and diagnostics['stripCount']==0 and diagnostics['reelCount']==0 and diagnostics['cellAnimation']=='none',diagnostics
                        # Capture one source-bound sidecar while the changed branch is actively mounted.
                        game_evidence(f'after-pass-slots-presentation-{motion_mode}-{locale}-{viewport_id}.png','slots',['spinning',f'{motion_mode}_motion'],locale,viewport_id)
                        # Wait for the real action to settle before starting the next matrix row.
                        page.wait_for_function("() => document.querySelector('[data-testid=\"slots-spin\"]')?.disabled === false",timeout=7000)
            # Restore the ordinary English primary-desktop route for downstream Slots checks.
            page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size(presentation_viewports['desktop_primary']); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
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
            # Resolve exact active-locale eligibility prefixes from authoritative resources rather than stale literals.
            progressive_labels=page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); const marker='__AMOUNT__'; const args={amount:marker,lines:i18n.formatNumber(20),lineBet:'1.00'}; return {eligible:i18n.t('feature.progressive',args,'games/slots').split(marker)[0],ineligible:i18n.t('feature.progressiveIneligible',args,'games/slots').split(marker)[0]}; }""")
            # Preserve the settled result headline before changing any progressive eligibility control.
            settled_headline=page.get_by_test_id('slots-progressive-headline').inner_text()
            # Switch just below the exact qualifier and require dedicated eligibility to update immediately.
            line_bet.fill('0.99'); page.wait_for_function("expected => document.querySelector('[data-testid=\"slots-progressive-status\"]')?.textContent.startsWith(expected)",arg=progressive_labels['ineligible'])
            # Require eligibility changes to preserve the settled payout headline and history.
            assert page.get_by_test_id('slots-progressive-headline').inner_text()==settled_headline and page.get_by_test_id('slots-recent-spins').is_visible()
            # Restore the exact qualifier and require the eligible status without another game action.
            line_bet.fill('1.00'); page.wait_for_function("expected => document.querySelector('[data-testid=\"slots-progressive-status\"]')?.textContent.startsWith(expected)",arg=progressive_labels['eligible'])
            # Require the settled result headline to survive the second control transition.
            assert page.get_by_test_id('slots-progressive-headline').inner_text()==settled_headline
            # Type the reported negative value through the normal input event path.
            line_bet.fill('-5'); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-line-bet\"]')?.value === '0.01'")
            # Require immediate correction, machine-readable invalid state, localized feedback, and zero requests.
            assert line_bet.get_attribute('aria-invalid')=='true' and page.get_by_test_id('slots-line-bet-feedback').text_content().strip()=='Line bet must round to a cent value from 0.01 to 1,000,000 play tokens. Reset to 0.01.' and not observed_spin_requests
            # Type a valid replacement to prove the error clears and visible cost updates before any spin.
            line_bet.fill('3'); page.wait_for_timeout(50)
            # Require the valid state and the twenty-line cost implied by the visible controls.
            assert line_bet.get_attribute('aria-invalid')=='false' and page.get_by_test_id('slots-line-bet-feedback').inner_text()=='' and '60' in page.get_by_test_id('slots-round-cost').inner_text() and not observed_spin_requests
            # Re-enter the reported invalid value so governed evidence records the correction feedback.
            line_bet.fill('-5'); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-line-bet\"]')?.getAttribute('aria-invalid') === 'true'")
            # Define the governed locale vocabulary exercised through the live browser resource loader.
            validation_locales=('en-US','ru-RU')
            # Define the affected compact and mobile visual-matrix viewports.
            validation_viewports={'desktop_compact':{'width':1440,'height':900},'mobile':{'width':390,'height':844}}
            # Exercise localized invalid-input presentation without losing corrected state.
            for locale in validation_locales:
                # Change locale through the shared visible shell control.
                page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("expected => window.CasinoI18n?.getLocaleState().locale === expected",arg=locale)
                # Exercise the invalid input after the locale settles so the current resource owns feedback.
                localized_line_bet=page.get_by_test_id('slots-line-bet'); localized_line_bet.fill('-5')
                # Resolve the exact message from the same active browser resource boundary as the game.
                expected_feedback=page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); return i18n.t('errors.lineBetRange',{},'games/slots'); }""")
                # Require exact localized feedback, correction, invalid state, and no token-moving request.
                page.wait_for_function("expected => document.querySelector('[data-testid=\"slots-line-bet-feedback\"]')?.textContent.trim() === expected",arg=expected_feedback); assert localized_line_bet.input_value()=='0.01' and localized_line_bet.get_attribute('aria-invalid')=='true' and not observed_spin_requests
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
            page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
            # Resolve the restored exact English message through the live resource boundary.
            restored_feedback=page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); return i18n.t('errors.lineBetRange',{},'games/slots'); }""")
            # Require the restored live region to equal that authoritative resource.
            page.wait_for_function("expected => document.querySelector('[data-testid=\"slots-line-bet-feedback\"]')?.textContent.trim() === expected",arg=restored_feedback)
            # Submit one corrected spin and capture the exact public request emitted by the visible button.
            with page.expect_request(lambda request: request.method=='POST' and request.url.endswith('/api/v1/games/slots/spin')) as corrected_request_info: page.get_by_test_id('slots-spin').click()
            # Read the frozen endpoint payload after Playwright observes the real request.
            corrected_payload=corrected_request_info.value.post_data_json
            # Wait for a completed real round rather than accepting request emission alone.
            page.wait_for_function("() => !document.querySelector('[data-testid=\"slots-spin\"]')?.disabled && document.querySelector('[data-testid=\"slots-result\"]')?.textContent.includes('Result.')",timeout=WAIT_MS)
            # Require one corrected minimum-cent line bet and an authoritative completed result.
            assert corrected_payload['line_bet']==0.01 and corrected_payload['active_lines']==20 and observed_spin_requests and page.get_by_test_id('slots-result').is_visible()
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
            assert autoplay_payload['plan']['active_lines']==20 and autoplay_payload['plan']['line_bet']==0.01
            # Wait for the one locally committed autoplay action to settle and return the controls to Off.
            page.wait_for_function("() => !document.querySelector('[data-testid=\"slots-spin\"]')?.disabled && document.querySelector('[data-testid=\"autoplay-slots\"] .badge')?.textContent === 'Off'",timeout=WAIT_MS)
            # Clear the synthetic session identifier so later route-unmount cleanup stays listener-free.
            page.evaluate("() => { const session=window.__casinoAutoplaySessions?.get('slots'); if(session) session.serverId=null; }")
            # Remove the bounded control-plane stub before any later autoplay coverage.
            page.unroute('**/api/v1/autoplay/**',fulfill_slots_autoplay_probe)
            # Detach the observer so later game traffic cannot affect this completed case.
            page.remove_listener('request',observe_slots_spin)
        # Record immediate feedback, synchronization, localization, evidence, and real request coverage.
        run_case('BR-SLOT-LINE-BET-001',['SLOT-027','SLOT-036','TEST-058','UX-009'],slots_line_bet_validation)
        # Prove shared-app readiness and bounded diagnostics in the Chromium-installed Browser lane. (TEST-053)
        def shared_app_readiness_browser_proof():
            # Reuse the runner-owned governed page because Browser.new_page convenience contexts reject child pages.
            proof_page=page
            # Track only bounded route counts needed to delay the second late navigation.
            route_counts={}
            # Fulfill synthetic same-process documents without external network access.
            def fulfill_probe_document(route):
                # Classify the fixed proof path without retaining query or request payloads.
                proof_path=route.request.url.partition('?')[0].rsplit('/',1)[-1]
                # Increment only the three fixed proof counters.
                route_counts[proof_path]=route_counts.get(proof_path,0)+1
                # Delay only the reload of the fixed late-navigation document past its 100ms budget.
                if proof_path=='late' and route_counts[proof_path]>1: time.sleep(0.2)
                # Dispatch the fixed error event only from the error document.
                event_name='casino:shared-app-error' if proof_path=='error' else 'casino:shared-app-ready'
                # Prove the marker existed before the application document dispatched its terminal event.
                body=f"<script>window.markerBeforeDispatch=Boolean(window.__casinoSharedAppReadinessProbe);window.dispatchEvent(new Event('{event_name}'))</script>"
                # Complete the synthetic navigation with no external assets.
                route.fulfill(status=200,content_type='text/html',body=body)
            try:
                # Intercept the fixed synthetic origin entirely inside Chromium.
                proof_page.route('http://shared-ready.test/**',fulfill_probe_document)
                # Install the production pre-document probe before any proof document runs.
                install_shared_app_readiness_probe(proof_page)
                # Establish and reload the ready document under the ordinary Browser budget.
                proof_page.goto('http://shared-ready.test/ready',wait_until='load'); ready=reload_and_wait_for_shared_app_readiness(proof_page,timeout_ms=WAIT_MS)
                # Require both pre-document execution and the exact terminal ready marker.
                assert proof_page.evaluate('window.markerBeforeDispatch') is True and ready=={'status':'ready','milestone':'shared_app_ready'}
                # Establish the error document before exercising the same production reload helper.
                proof_page.goto('http://shared-ready.test/error',wait_until='load')
                # Track fail-closed error observation without retaining exception detail.
                error_failed_closed=False
                try: reload_and_wait_for_shared_app_readiness(proof_page,timeout_ms=WAIT_MS)
                except AssertionError as error: error_failed_closed='terminal error signal' in str(error)
                # Require the real terminal error event to fail closed.
                assert error_failed_closed
                # Establish the document whose reload is deliberately later than the total proof budget.
                proof_page.goto('http://shared-ready.test/late',wait_until='load')
                # Start one bounded measurement around reload plus terminal observation.
                late_started=time.monotonic(); late_failed_closed=False
                try: reload_and_wait_for_shared_app_readiness(proof_page,timeout_ms=100)
                except AssertionError: late_failed_closed=True
                # Reject a second terminal-sized allowance after the deliberately late navigation.
                assert late_failed_closed and time.monotonic()-late_started<1.0
            finally:
                # Remove the synthetic origin handler before restoring the canonical authenticated Slots route.
                proof_page.unroute('http://shared-ready.test/**',fulfill_probe_document)
                # Restore the governed runner-owned page even when a synthetic navigation assertion fails.
                proof_page.goto(base+'/games/slots',wait_until='networkidle'); proof_page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
            # Reuse the governed page for one disposable document whose cache and worker inventories never resolve.
            capture_page=page
            try:
                # Load one self-contained document for the bounded diagnostic evaluation.
                capture_page.goto('data:text/html,<div id="view"></div>',wait_until='load')
                # Replace inventory seams only in this disposable document so canonical navigation clears them.
                capture_page.evaluate("""() => { Object.defineProperty(window,'caches',{value:{keys:()=>new Promise(()=>{})},configurable:true}); Object.defineProperty(navigator,'serviceWorker',{value:{getRegistrations:()=>new Promise(()=>{}),controller:null},configurable:true}); }""")
                # Isolate the synthetic first-failure artifact outside the repository.
                with tempfile.TemporaryDirectory() as directory:
                    # Resolve one disposable fixed evidence path.
                    target=Path(directory)/'shared-app-first-failure.json'
                    # Freeze one original exception object for exact bare-rethrow identity proof.
                    original=RuntimeError('browser-only diagnostic proof')
                    # Retain publication outcome and elapsed time outside the nested handler.
                    persisted=False; capture_elapsed=0.0; captured=None
                    try:
                        try: raise original
                        except RuntimeError as error:
                            # Bound the complete diagnostic call around deliberately unresolved Browser promises.
                            capture_started=time.monotonic(); persisted=persist_shared_app_first_failure(capture_page,target,failure=error); capture_elapsed=time.monotonic()-capture_started
                            # Preserve the exact original exception and traceback.
                            raise
                    except RuntimeError as error: captured=error
                    # Require bounded capture, atomic publication, and original-exception identity.
                    assert persisted and capture_elapsed<2.0 and captured is original
                    # Read the fixed-schema evidence after atomic publication.
                    artifact=json.loads(target.read_text(encoding='utf-8'))
                    # Require both unresolved inventory seams to collapse into fixed capture enums.
                    assert {'cache_capture','service_worker_capture'}<=set(artifact['capture_failures'])
            finally:
                # Canonical navigation destroys the disposable unresolved Promise overrides.
                capture_page.goto(base+'/games/slots',wait_until='networkidle'); capture_page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
        # Define the complete governed Slots economics and visual-state matrix for SLOT-036.
        def slots_economics_visual_matrix():
            # Resolve the authenticated player whose isolated Slots state drives deterministic evidence.
            matrix_player=browser_player_id
            # Read every exact viewport from the authoritative visual matrix.
            matrix_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the complete governed viewport vocabulary before any evidence capture.
            assert set(matrix_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Build one deterministic grid with an ordinary single-line CHERRY win.
            win_grid=[['LEMON','BAR','BELL','SEVEN','CHERRY'],['CHERRY','CHERRY','CHERRY','LEMON','BAR'],['BAR','BELL','SEVEN','CHERRY','LEMON']]
            # Build one deterministic all-SEVEN grid with twenty line wins and one qualifying jackpot.
            multi_grid=[['SEVEN' for _column in range(5)] for _row in range(3)]
            # Build one deterministic three-SCATTER grid that awards the exact four-spin feature.
            bonus_grid=[['SCATTER','SCATTER','SCATTER','BELL','SEVEN'],['LEMON','BAR','BELL','SEVEN','CHERRY'],['BAR','BELL','SEVEN','CHERRY','LEMON']]
            # Build one complete persisted spin from the authoritative engine rules.
            def matrix_spin(round_id,grid,active_lines,line_bet):
                # Evaluate exact line and scatter components through production rules.
                evaluated=slots_engine.evaluate(grid,active_lines,line_bet)
                # Resolve the fixed paid-only progressive qualifier from production rules.
                eligible=slots_engine.progressive_eligible(active_lines,line_bet)
                # Calculate the exact qualifying paid contribution before any same-spin jackpot.
                contribution=round(active_lines*line_bet*slots_engine.PROGRESSIVE_RATE,8) if eligible else 0.0
                # Resolve a five-SEVEN result through the same win evidence used by the production engine.
                progressive_hit=slots_engine.PROGRESSIVE_SEED+contribution if eligible and any(win.get('symbol')=='SEVEN' and win.get('count')==5 for win in evaluated['wins']) else 0.0
                # Reconcile the exact complete result payout with the progressive component.
                payout=round(evaluated['payout']+progressive_hit,2)
                # Reset only a winning qualifier; otherwise retain the contributed scalar meter.
                meter=slots_engine.PROGRESSIVE_SEED if progressive_hit else slots_engine.PROGRESSIVE_SEED+contribution
                # Return the complete state row consumed by the real route loader.
                return {'round_id':round_id,'timestamp':'2026-07-29T00:00:00Z','stops':[0,0,0,0,0],'grid':grid,'requested_active_lines':active_lines,'requested_line_bet':line_bet,'active_lines':active_lines,'line_bet':line_bet,'cost':round(active_lines*line_bet,2),**evaluated,'payout':payout,'free_spin':False,'free_spins_remaining':evaluated['free_spins_awarded'],'progressive_eligible':eligible,'progressive_basis':{'active_lines':slots_engine.PROGRESSIVE_QUALIFYING_LINES,'line_bet':slots_engine.PROGRESSIVE_QUALIFYING_LINE_BET},'progressive_before':slots_engine.PROGRESSIVE_SEED,'progressive_contribution':contribution,'progressive_hit':progressive_hit,'progressive':meter}
            # Build authoritative win, multi-win, and bonus rows once.
            win_spin=matrix_spin('slots-matrix-win',win_grid,1,0.01)
            # Build the simultaneous-payline jackpot row from the exact qualifier.
            multi_spin=matrix_spin('slots-matrix-multi',multi_grid,20,1.0)
            # Build the feature-trigger row from a nonqualifying minimum stake.
            bonus_spin=matrix_spin('slots-matrix-bonus',bonus_grid,1,0.01)
            # Require exact engine and progressive components before they become browser evidence.
            assert win_spin['line_payout']==0.02 and len(multi_spin['wins'])==20 and multi_spin['progressive_eligible'] and multi_spin['progressive_contribution']==0.2 and multi_spin['progressive_hit']==200.2 and multi_spin['progressive']==slots_engine.PROGRESSIVE_SEED and multi_spin['payout']==round(multi_spin['line_payout']+multi_spin['scatter_payout']+multi_spin['progressive_hit'],2) and bonus_spin['free_spins_awarded']==4 and bonus_spin['scatter_payout']==0
            # Build one constant-size default state with the exact qualifier metadata.
            def matrix_state(spins=None,free_spins=0,basis=None,meter=None):
                # Start from the production default so state shape cannot drift.
                prepared=slots_engine.default_state()
                # Replace only deterministic recent-spin evidence for this matrix cell.
                prepared['last_spins']=list(spins or [])
                # Set the feature bank required by the bonus state.
                prepared['free_spins']=free_spins
                # Retain an exact visible meter where a fixture provides one.
                prepared['progressive']=slots_engine.PROGRESSIVE_SEED if meter is None else meter
                # Store a server-owned paid-trigger basis only for an open feature chain.
                if basis: prepared['free_spin_basis']=dict(basis)
                # Return constant-size state with no caller-derived meter map.
                return prepared
            # Map every persisted visual state to its authoritative backend fixture.
            persisted_states={
                'idle':matrix_state(),  # Seed a pristine state for idle evidence.
                'win':matrix_state([win_spin]),  # Seed one exact ordinary winning line.
                'multi_win':matrix_state([multi_spin],meter=multi_spin['progressive']),  # Seed jackpot reset.
                'bonus':matrix_state([bonus_spin],free_spins=4,basis={'active_lines':1,'line_bet':0.01}),  # Seed bonus bank.
                'repeat_available':matrix_state([win_spin]),  # Seed a repeatable completed round.
                'route_restored':matrix_state([multi_spin],meter=multi_spin['progressive']),  # Seed restoration.
            }
            # Fetch the live API config once to prove exact server-owned rules reach the browser route.
            runtime=page.request.get(base+'/api/v1/games/slots/state').json()['data']['config']
            # Read the additive economics block under the frozen v1 envelope.
            economics=runtime['economics']
            # Require exact qualifier, one-meter policy, scatter/free rules, cent domain, and paytable values.
            assert economics['progressive_qualifying_lines']==20 and economics['progressive_qualifying_line_bet']==1.0 and economics['progressive_meter_limit']==1 and economics['progressive_basis_policy']=='single_exact_qualifier'
            # Require exact scatter and feature configuration.
            assert economics['scatter_pays']=={'4':1,'5':5} or economics['scatter_pays']=={4:1,5:5}
            # Require exact four-spin feature and frozen cent bounds.
            assert economics['free_spins_awarded']==4 and economics['line_bet']['api_minimum']==0.01 and economics['line_bet']['api_maximum']==1000000
            # Require the API paytable to equal the detached authoritative engine table.
            assert runtime['paytable']=={symbol:{str(count):multiplier for count,multiplier in table.items()} for symbol,table in slots_engine.PAYTABLE.items()}
            # Exercise both installed localized packs.
            for locale in ('en-US','ru-RU'):
                # Exercise all four exact governed viewport sizes.
                for viewport_id,viewport in matrix_viewports.items():
                    # Apply the exact viewport before route reconstruction.
                    page.set_viewport_size(viewport)
                    # Capture each persisted state from its exact server-owned document.
                    for state_name,prepared_state in persisted_states.items():
                        # Save one detached copy so route reads cannot mutate a later matrix cell.
                        save_player_game_state('slots',matrix_player,json.loads(json.dumps(prepared_state)))
                        # Isolate the route-restored reload behind the shared application's own pre-document terminal signal. (TEST-053)
                        if state_name=='route_restored':
                            # Install the listener before reload so neither a fast ready nor error event can escape observation.
                            install_shared_app_readiness_probe(page)
                            try:
                                # Require reload and the terminal shared-app signal to share the one unchanged Browser deadline.
                                reload_and_wait_for_shared_app_readiness(page,timeout_ms=WAIT_MS)
                                # Preserve the independent module-owned readiness assertion after shared bootstrap succeeds.
                                page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
                            except Exception as error:
                                # Persist at most one bounded sanitized diagnostic bundle for this exact case and boundary.
                                persist_shared_app_first_failure(page,screenshots/'before-failure-slots-route-restored-shared-app.json',failure=error)
                                # Preserve the original readiness or module-mount exception unchanged.
                                raise
                        else:
                            # Keep every non-restoration matrix reload on its established independent module readiness path.
                            page.reload(wait_until='networkidle'); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
                        # Switch through the visible locale control and wait for the runtime rerender.
                        page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_function("expected => window.CasinoI18n?.getLocaleState().locale === expected",arg=locale)
                        # Read the exact backing state/config returned to the mounted browser.
                        backing=page.request.get(base+'/api/v1/games/slots/state').json()['data']
                        # Re-enter the route through normal navigation for the route-restored cell.
                        if state_name=='route_restored':
                            # Leave the game through the shared lobby action.
                            page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                            # Return through the catalog-owned Slots route.
                            page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
                            # Read state again after the real unmount/remount cycle.
                            restored=page.request.get(base+'/api/v1/games/slots/state').json()['data']
                            # Require the same exact round, result, meter, and economics configuration after restoration.
                            assert restored['state']['last_spins'][-1]==backing['state']['last_spins'][-1] and restored['state']['progressive']==backing['state']['progressive'] and restored['config']['economics']==backing['config']['economics']
                        # Read exact localized paytable and eligibility surfaces.
                        visible=page.get_by_test_id('slots-premium').inner_text()
                        # Require exact changed economics tokens without raw resource keys.
                        assert '1000' not in visible and 'paytable.' not in visible and 'feature.' not in visible
                        # Require the one-meter qualifier to remain visible in both localized layouts.
                        assert '20' in visible and ('1.00' in visible or '1,00' in visible)
                        # Render the exact authoritative localized rule strings through the active browser runtime.
                        expected_rules=page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); const amount=i18n.formatMoney(200); const number=i18n.formatNumber; return {scatter:i18n.t('paytable.scatter',{threshold:number(3),freeSpins:number(4),four:number(1),five:number(5)},'games/slots'),progressive:i18n.t('paytable.progressive',{seed:amount,contribution:number(1),lines:number(20),lineBet:'1.00'},'games/slots'),eligible:i18n.t('feature.progressive',{amount,lines:number(20),lineBet:'1.00'},'games/slots'),ineligible:i18n.t('feature.progressiveIneligible',{amount,lines:number(20),lineBet:'1.00'},'games/slots')}; }""")
                        # Determine the exact eligibility state represented by this persisted fixture.
                        expected_eligible=state_name in ('idle','multi_win','route_restored')
                        # Verify either the visible paytable or feature drawer carries exact localized server-owned copy.
                        if page.get_by_test_id('slots-pay-scatter').count():
                            # Require exact scatter and progressive text rather than numeric substrings.
                            assert page.get_by_test_id('slots-pay-scatter').locator('span').inner_text()==expected_rules['scatter'] and page.get_by_test_id('slots-pay-progressive').locator('span').inner_text()==expected_rules['progressive']
                        else:
                            # Require the feature drawer to disclose the exact current eligibility state.
                            assert page.get_by_test_id('slots-progressive-feature-status').inner_text()==expected_rules['eligible' if expected_eligible else 'ineligible']
                        # Require the dedicated control status to match the precise fixture eligibility.
                        assert page.get_by_test_id('slots-progressive-status').inner_text()==expected_rules['eligible' if expected_eligible else 'ineligible']
                        # Read the exact payline identities rendered from the backing result.
                        rendered_lines=[int(value) for value in page.locator('[data-testid="slots-payline"] polyline').evaluate_all("paths => paths.map(path => path.dataset.lineNumber)")] if page.get_by_test_id('slots-payline').count() else []
                        # Require idle to contain no result, paylines, or enabled repeat action.
                        if state_name=='idle':
                            # Prove one disclosed seed, no result history, no lines, and no repeat setup.
                            assert backing['state']['last_spins']==[] and backing['state']['progressive']==slots_engine.PROGRESSIVE_SEED and rendered_lines==[] and page.locator('[data-action="repeat"]').is_disabled()
                        # Require the ordinary win to preserve one exact line identity and payout.
                        elif state_name=='win':
                            # Prove one line-one CHERRY return and its visible result amount.
                            assert backing['state']['last_spins'][-1]['round_id']=='slots-matrix-win' and backing['state']['last_spins'][-1]['payout']==0.02 and rendered_lines==[1] and page.get_by_test_id('slots-result').is_visible() and page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); return i18n.formatMoney(.02); }""") in page.get_by_test_id('slots-result').inner_text()
                        # Require the progressive multi-win to prove exact contribution, hit, payout, and reset.
                        elif state_name=='multi_win':
                            # Resolve the exact persisted jackpot result once.
                            jackpot=backing['state']['last_spins'][-1]
                            # Prove twenty winning line identities and the complete qualifying settlement.
                            assert rendered_lines==list(range(1,21)) and jackpot['progressive_eligible'] and jackpot['progressive_contribution']==0.2 and jackpot['progressive_hit']==200.2 and jackpot['payout']==round(jackpot['line_payout']+jackpot['scatter_payout']+jackpot['progressive_hit'],2)
                            # Prove the backing meter reset while the visible headline retains the won amount.
                            assert backing['state']['progressive']==slots_engine.PROGRESSIVE_SEED and expected_rules['eligible']==page.get_by_test_id('slots-progressive-status').inner_text() and page.get_by_test_id('slots-progressive-headline').inner_text()==page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); return i18n.t('cabinet.progressiveHit',{amount:i18n.formatMoney(200.2)},'games/slots'); }""")
                        # Require the feature state to retain the exact award and trusted paid-trigger basis.
                        elif state_name=='bonus':
                            # Prove four pending feature actions, their exact one-line one-cent basis, and no progressive movement.
                            assert backing['state']['free_spins']==4 and backing['state']['free_spin_basis']=={'active_lines':1,'line_bet':0.01} and backing['state']['last_spins'][-1]['free_spins_awarded']==4 and not backing['state']['last_spins'][-1]['progressive_eligible'] and backing['state']['last_spins'][-1]['progressive_hit']==0
                            # Require the cabinet headline to expose the exact localized four-spin bank.
                            assert page.get_by_test_id('slots-progressive-headline').inner_text()==page.evaluate("""async () => { const i18n=await import('/core/i18n.js'); return i18n.t('cabinet.freeSpins',{count:i18n.formatNumber(4)},'games/slots'); }""")
                        # Require repeat availability to use the exact preceding visible setup.
                        elif state_name=='repeat_available':
                            # Prove one retained result and an enabled current-semantics Repeat control.
                            assert backing['state']['last_spins'][-1]['round_id']=='slots-matrix-win' and page.locator('[data-action="repeat"]').is_enabled() and rendered_lines==[1]
                        # Require route restoration to retain the exact qualifying result and all line identities.
                        elif state_name=='route_restored':
                            # Prove the same exact jackpot round, reset meter, and twenty paylines survived remount.
                            assert backing['state']['last_spins'][-1]['round_id']=='slots-matrix-multi' and backing['state']['progressive']==slots_engine.PROGRESSIVE_SEED and rendered_lines==list(range(1,21))
                        # Require no document-level overflow at any matrix size.
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                        # Require the complete game root, control, cabinet, and data drawer to remain rendered.
                        assert page.get_by_test_id('slot-grid').is_visible() and page.locator('.slots-control').is_visible() and page.locator('.slots-drawer').is_visible()
                        # Capture one exact-head image and sidecar for this persisted state.
                        game_evidence(f'after-pass-slots-economics-{state_name}-{locale}-{viewport_id}.png','slots',[state_name],locale,viewport_id)
                    # Seed idle state for the three interaction-owned visual states.
                    save_player_game_state('slots',matrix_player,matrix_state())
                    # Reload and restore the active locale after the deterministic seed.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS); page.get_by_test_id('shell-locale-select').select_option(locale)
                    # Enter invalid input through the player-visible control.
                    page.get_by_test_id('slots-line-bet').fill('-5'); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-line-bet\"]')?.getAttribute('aria-invalid') === 'true'")
                    # Read state after the invalid edit to prove it caused no hidden game action.
                    invalid_backing=page.request.get(base+'/api/v1/games/slots/state').json()['data']['state']
                    # Require exact correction, localized feedback, nonqualification, and unchanged seed state.
                    assert page.get_by_test_id('slots-line-bet').input_value()=='0.01' and page.get_by_test_id('slots-line-bet-feedback').inner_text().strip() and page.get_by_test_id('slots-progressive-status').inner_text().strip() and invalid_backing['last_spins']==[] and invalid_backing['progressive']==slots_engine.PROGRESSIVE_SEED
                    # Capture the exact invalid-input matrix cell.
                    game_evidence(f'after-pass-slots-economics-invalid_line_bet-{locale}-{viewport_id}.png','slots',['invalid_line_bet'],locale,viewport_id)
                    # Enable the real reduced-motion media preference and rebuild the route.
                    page.emulate_media(reduced_motion='reduce'); page.reload(wait_until='networkidle'); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
                    # Require the real media preference, idle reel cells, and bounded layout under reduced motion.
                    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") and page.get_by_test_id('slot-grid').is_visible() and page.locator('.slots-symbol.spinning').count()==0 and page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Capture the reduced-motion matrix cell.
                    game_evidence(f'after-pass-slots-economics-reduced_motion-{locale}-{viewport_id}.png','slots',['reduced_motion'],locale,viewport_id)
                    # Restore normal motion and apply the governed 125-percent zoom state.
                    page.emulate_media(reduced_motion='no-preference'); page.reload(wait_until='networkidle'); page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS); page.evaluate("document.body.style.zoom='125%'"); page.wait_for_timeout(120)
                    # Require the exact zoom value, page containment, and visible primary action.
                    assert page.evaluate("document.body.style.zoom==='125%'") and page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1') and page.get_by_test_id('slots-spin').is_visible()
                    # Capture the zoomed matrix cell.
                    game_evidence(f'after-pass-slots-economics-zoomed-{locale}-{viewport_id}.png','slots',['zoomed'],locale,viewport_id)
                    # Restore zoom before exercising the real committed spinning state.
                    page.evaluate("document.body.style.zoom=''")
                    # Use the minimum nonqualifying setup so matrix capture cannot materially deplete the wallet.
                    page.get_by_test_id('slots-lines').select_option('1'); page.get_by_test_id('slots-line-bet').fill('0.01')
                    # Begin one real action and wait for the committed in-progress render.
                    page.get_by_test_id('slots-spin').click(); page.wait_for_function("() => document.querySelector('[data-testid=\"slots-spin\"]')?.disabled === true")
                    # Require a real disabled action, all fifteen moving cells, and visible nonqualifying status while pending.
                    assert page.get_by_test_id('slots-spin').is_disabled() and page.locator('.slots-symbol.spinning').count()==15 and page.get_by_test_id('slots-progressive-status').is_visible()
                    # Capture the actual spinning matrix cell before the fixed reveal delay completes.
                    game_evidence(f'after-pass-slots-economics-spinning-{locale}-{viewport_id}.png','slots',['spinning'],locale,viewport_id)
                    # Wait for the real action to finish before the next matrix cell or viewport.
                    page.wait_for_function("() => document.querySelector('[data-testid=\"slots-spin\"]')?.disabled === false",timeout=WAIT_MS)
            # Restore English, primary desktop, normal motion, and normal zoom for downstream cases.
            page.get_by_test_id('shell-locale-select').select_option('en-US'); page.set_viewport_size(matrix_viewports['desktop_primary']); page.emulate_media(reduced_motion='no-preference'); page.evaluate("document.body.style.zoom=''")
        # Execute the existing economics matrix plus the real normal/reduced presentation matrix under one permanent case.
        def slots_economics_and_presentation():
            # Execute disposable real-Chromium readiness and diagnostic proofs in the Browser-only lane.
            shared_app_readiness_browser_proof()
            # Preserve the complete engine, configuration, copy, state, and geometry matrix.
            slots_economics_visual_matrix()
            # Execute the new real normal/reduced action matrix inside the same permanent owner case.
            slots_presentation_evidence_matrix()
        # Extend the existing permanent economics case without adding a new Browser inventory row.
        run_case('BR-SLOT-ECONOMICS-001',['SLOT-010','SLOT-011','SLOT-012','SLOT-013','SLOT-014','SLOT-015','SLOT-016','SLOT-017','SLOT-018','SLOT-019','SLOT-030','SLOT-032','SLOT-034','SLOT-035','SLOT-036','SLOT-037'],slots_economics_and_presentation)
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
            # Read the authoritative latest round so its internal identifier can be rejected from rendered history.
            slots_latest=page.request.get(base+'/api/v1/games/slots/state').json()['data']['state']['last_spins'][-1]
            # Exercise the privacy-safe history row in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch the mounted cabinet through the public locale control.
                page.get_by_test_id('shell-locale-select').select_option(locale); page.wait_for_timeout(100)
                # Read the localized history after the route rerenders.
                slots_history_text=page.get_by_test_id('slots-recent-spins').inner_text()
                # Require the visible row to retain line count while hiding the raw durable round identifier.
                assert slots_latest['round_id'] not in slots_history_text and str(slots_latest['active_lines']) in slots_history_text,slots_history_text
                # Record focused exact-head evidence for the privacy-safe localized drawer.
                game_evidence(f'after-pass-game-polish-slots-{locale}-desktop_primary.png','slots',['idle'],locale,'desktop_primary')
            # Restore English before downstream game navigation.
            page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_timeout(100)
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
        run_case('BR-SLOT-001',['SLOT-020','SLOT-021','SLOT-022','SLOT-023','SLOT-024','SLOT-025','SLOT-026','SLOT-027','SLOT-028','SLOT-030','SLOT-031','SLOT-032','SLOT-033','SLOT-034','SLOT-035','I18N-010','TEST-064','TEST-117','AUTO-010','LEDGER-025','UX-007','UX-009'],premium_slots)
    # Preserve exact case accounting when this shard does not own Slots.
    else:
        # Advance only the contiguous Slots registrations.
        skip_browser_affinity('slots')
    # Run the stateful Keno producer/consumer chain on its independent owner.
    if browser_shard_owns_group('keno'):
        # Normalize viewport and motion state before mounting Keno independently of Slots.
        page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size({'width':1920,'height':1080})
        # Navigate directly to Keno so no Slots route state is required on this shard.
        page.goto(base+'/games/keno',wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
        # Require one lifecycle-owned external stylesheet and no retained inline owner.
        assert page.locator('link#keno-premium-styles[href="/games/keno.css"]').count()==1 and page.locator('style#keno-premium-styles').count()==0
        # Normalize the player locale before Keno builds its complete localized evidence matrix.
        page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
        # Prove edge number cells and their state treatments stay inside the visible board bounds instead of being clipped. (issue #320)
        def keno_edge_containment():
            # Resolve the authenticated player whose disposable Keno state drives deterministic edge evidence.
            edge_player=browser_player_id
            # Define the exact governed viewport matrix from the visual standard.
            edge_viewports=[('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)]
            # Pin the complete eight-state by two-locale by four-viewport evidence count.
            keno_matrix_expected_cells=64
            # Count each exact governed state/locale/viewport cell as its evidence is written.
            keno_matrix_cells=0
            # Keep the idle state free of prior tickets and draws before each locale/viewport capture.
            empty_edge_state={'open_tickets':[],'last_draws':[]}
            # Build one legitimate twenty-catch final draw whose selected range includes edge cell 80.
            edge_draw=list(range(61,81))
            # Resolve the exact top jackpot from the server table instead of a stale Browser fixture.
            edge_jackpot_multiplier=keno_engine.PAYTABLE[20][20]
            # Apply the frozen production payout law to the one-token visual ticket.
            edge_jackpot_payout=round(1.0*edge_jackpot_multiplier,2)
            # Persist one authoritative full-catch jackpot state for result, restore, repeat, and exact-value evidence.
            final_edge_state={'open_tickets':[],'last_draws':[{'round_id':'keno-edge-final','timestamp':'2026-07-20T00:00:00Z','drawn':edge_draw,'results':[{'ticket':{'ticket_id':'keno-edge-catch','player_id':edge_player,'spots':edge_draw,'amount':1,'source':'browser-test','created_at':'2026-07-20T00:00:00Z'},'catches':edge_draw,'catch_count':20,'multiplier':edge_jackpot_multiplier,'payout':edge_jackpot_payout}]}]}
            # Exercise both installed player-facing locales.
            for edge_locale in ('en-US','ru-RU'):
                # Exercise every governed viewport without substituting an approximate breakpoint.
                for edge_viewport_id,edge_width,edge_height in edge_viewports:
                    # Start this matrix cell from an authoritative empty persisted state.
                    save_player_game_state('keno',edge_player,empty_edge_state)
                    # Apply the exact viewport before route reconstruction and geometry sampling.
                    page.set_viewport_size({'width':edge_width,'height':edge_height})
                    # Reload the canonical game route so local selection state is empty and backend state is current.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
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
                    # Use a bounded board crop on desktop because the shared game-outlet scrollport cannot paint an offscreen full-route locator without transparent padding.
                    edge_board_evidence_selector='[data-testid="keno-board-scroll"]' if edge_viewport_id in ('desktop_primary','desktop_compact') else '.keno-premium'
                    # Record self-describing idle evidence for this exact locale and viewport.
                    region_evidence(f'after-pass-keno-edge-idle-{edge_locale.lower()}-{edge_viewport_id}.png',edge_board_evidence_selector,'keno',['edge_idle'],edge_locale,edge_viewport_id)
                    # Count the exact idle edge matrix cell.
                    keno_matrix_cells+=1
                    # Select one real number so the selection cell cannot duplicate the idle state.
                    page.get_by_test_id('keno-num-5').click()
                    # Require the draft selection to be visible and server-authoritative paytable preview to stay mounted.
                    assert page.get_by_test_id('keno-num-5').get_attribute('aria-pressed')=='true' and page.get_by_test_id('keno-paytable-preview').is_visible()
                    # Record the governed non-empty draft selection state.
                    region_evidence(f'after-pass-keno-selection-{edge_locale.lower()}-{edge_viewport_id}.png',edge_board_evidence_selector,'keno',['selection'],edge_locale,edge_viewport_id)
                    # Count the exact selection matrix cell.
                    keno_matrix_cells+=1
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
                    region_evidence(f'after-pass-keno-edge-selected-focus-{edge_locale.lower()}-{edge_viewport_id}.png',edge_board_evidence_selector,'keno',['edge_selected_focus_visible'],edge_locale,edge_viewport_id)
                    # Count the exact selected and focus-visible matrix cell.
                    keno_matrix_cells+=1
                    # Collect the exact public Keno action requests emitted after the amount edit.
                    edge_action_requests=[]
                    # Define the scoped request observer used only for this one matrix action.
                    def capture_edge_action_request(request):
                        # Record ticket and draw POSTs while ignoring unrelated shell traffic.
                        if request.method=='POST' and (request.url.endswith('/api/v1/games/keno/tickets') or request.url.endswith('/api/v1/games/keno/draw')): edge_action_requests.append(request)
                    # Attach the observer before the edit can blur into the public Draw control.
                    page.on('request',capture_edge_action_request)
                    # Use the frozen one-cent amount so the visible action proves browser/server domain agreement.
                    try:
                        # Edit through the real input so blur/change ordering matches the production click path.
                        page.get_by_test_id('keno-amount').fill('0.01')
                        # Start exactly one real public draw from the selected corners.
                        page.get_by_test_id('keno-draw').click()
                        # Wait for the production reveal loop to enter a genuine partial drawing state.
                        page.wait_for_function("""() => { const count=document.querySelectorAll('[data-testid="keno-drawn-ball"]').length; return count>=2 && count<20; }""",timeout=WAIT_MS)
                        # Resolve the drawing PNG target without retaining a locator across the production rerender loop.
                        keno_drawing_target=screenshots/f'after-pass-keno-drawing-{edge_locale.lower()}-{edge_viewport_id}.png'
                        # Atomically read the current partial count and page-relative crop before another reveal rerender can detach the region.
                        keno_drawing_probe=page.evaluate("""() => { const region=document.querySelector('.keno-premium'); const rect=region.getBoundingClientRect(); const drawnCount=document.querySelectorAll('[data-testid="keno-drawn-ball"]').length; return {drawn_count:drawnCount,clip:{x:rect.left+window.scrollX,y:rect.top+window.scrollY,width:rect.width,height:rect.height}}; }""")
                        # Require this exact artifact to remain a genuine partial 2..19-ball drawing with a paintable region.
                        assert 2<=keno_drawing_probe['drawn_count']<20 and keno_drawing_probe['clip']['width']>0 and keno_drawing_probe['clip']['height']>0,keno_drawing_probe
                        # Capture through the page-level clip so the 65ms root replacement cannot detach a screenshot locator.
                        page.screenshot(path=str(keno_drawing_target),clip=keno_drawing_probe['clip'],animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                        # Record the active viewport dimensions beside the governed matrix viewport id.
                        keno_drawing_viewport=page.viewport_size
                        # Record the current focus target without retaining a live element reference.
                        keno_drawing_focused=page.evaluate("() => document.activeElement?.getAttribute('data-testid') || document.activeElement?.getAttribute('data-action') || ''")
                        # Preserve the standard after-pass metadata and disclose the same bounded region selector.
                        keno_drawing_metadata={'evidence_class':'after_pass','branch':evidence_branch,'commit':evidence_commit,'surface':'keno','states':['drawing'],'locale':edge_locale,'viewport':{'id':edge_viewport_id,**keno_drawing_viewport},'path':str(keno_drawing_target.relative_to(ROOT)).replace('\\','/'),'focused_control':keno_drawing_focused,'region_selector':'.keno-premium','drawn_count':keno_drawing_probe['drawn_count']}
                        # Write the drawing sidecar next to the page-level clipped image for independent audit.
                        keno_drawing_target.with_suffix('.json').write_text(json.dumps(keno_drawing_metadata,indent=2,ensure_ascii=False),encoding='utf-8')
                        # Count the exact drawing matrix cell.
                        keno_matrix_cells+=1
                        # Wait for the real action to finish before replacing only its test-owned persisted state.
                        page.wait_for_function("""() => document.querySelectorAll('[data-testid="keno-drawn-ball"]').length === 20 && !document.querySelector('[data-testid="keno-draw"]')?.disabled""",timeout=6000)
                    # Always detach the scoped observer so later matrix actions cannot contaminate this count.
                    finally:
                        # Remove the exact callback registered for this one public action.
                        page.remove_listener('request',capture_edge_action_request)
                    # Resolve the exact ticket and draw requests captured from the single click.
                    edge_ticket_requests=[request for request in edge_action_requests if request.url.endswith('/api/v1/games/keno/tickets')]; edge_draw_requests=[request for request in edge_action_requests if request.url.endswith('/api/v1/games/keno/draw')]
                    # Require one ticket purchase and one draw request, with no blur-time swallowed or duplicate action.
                    assert len(edge_ticket_requests)==1 and len(edge_draw_requests)==1,[(request.method,request.url) for request in edge_action_requests]
                    # Decode the exact frozen-v1 ticket request emitted by the edited input.
                    edge_ticket_body=edge_ticket_requests[0].post_data_json
                    # Require the single request to retain exact amount and selected spots.
                    assert float(edge_ticket_body['amount'])==0.01 and edge_ticket_body['spots']==[1,5,10,71,80],edge_ticket_body
                    # Persist one deterministic final draw so caught/latest state does not depend on random outcomes.
                    save_player_game_state('keno',edge_player,final_edge_state)
                    # Reconstruct the route from authoritative history before reapplying this matrix cell's visible locale.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
                    # Select the evidence locale again because an earlier full-suite durable account preference may intentionally win during reload.
                    page.get_by_test_id('shell-locale-select').select_option(edge_locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=edge_locale)
                    # Require the child server to expose the parent-written authoritative draw through the reconstructed public route.
                    page.wait_for_function("() => document.querySelectorAll('[data-testid=\"keno-drawn-ball\"]').length === 20",timeout=WAIT_MS)
                    # Require the seeded result to render every draw plus all caught cells and the latest bottom-right edge.
                    assert page.locator('.keno-num.drawn').count()==20 and page.locator('.keno-num.catch').count()==20 and page.get_by_test_id('keno-num-80').evaluate("cell => cell.classList.contains('catch') && cell.classList.contains('latest')")
                    # Require the restored live amount and enabled repeat action to match the settled authoritative ticket.
                    assert float(page.get_by_test_id('keno-amount').input_value())==1.0 and not page.locator('[data-action="repeat"]').is_disabled()
                    # Require the exact numeric jackpot magnitude to remain visible rather than collapsing to a generic label.
                    active_paytable_digits=re.sub(r'\D','',page.get_by_test_id('keno-paytable-active').inner_text())
                    # Match the full authoritative multiplier despite locale-owned separators.
                    assert str(keno_engine.PAYTABLE[20][20]) in active_paytable_digits,active_paytable_digits
                    # Require the ideal-versus-realized fake-token disclosure on the result surface.
                    assert page.get_by_test_id('keno-economics-note').is_visible()
                    # Measure the completed drawn-ball rail before scrolling so internal overflow cannot masquerade as clipped page content.
                    rail_probe=page.get_by_test_id('keno-drawn-balls').evaluate("""rail => { const style=getComputedStyle(rail); const box=rail.getBoundingClientRect(); const owner=rail.closest('.keno-stage-panel')?.getBoundingClientRect(); const last=rail.querySelector('[data-testid="keno-drawn-ball"]:last-child')?.getBoundingClientRect(); return {clientWidth:rail.clientWidth,scrollWidth:rail.scrollWidth,scrollLeft:rail.scrollLeft,maxScrollLeft:rail.scrollWidth-rail.clientWidth,minWidth:style.minWidth,maxWidth:style.maxWidth,overflowX:style.overflowX,overflowY:style.overflowY,tabindex:rail.getAttribute('tabindex'),role:rail.getAttribute('role'),label:rail.getAttribute('aria-label'),box:{left:box.left,right:box.right},owner:owner&&{left:owner.left,right:owner.right},last:last&&{left:last.left,right:last.right}}; }""")
                    # Require one named keyboard-reachable horizontal owner bounded inside the stage whether this viewport needs overflow or fits all balls.
                    assert rail_probe['minWidth']=='0px' and rail_probe['overflowX'] in ('auto','scroll') and rail_probe['overflowY']=='hidden' and rail_probe['tabindex']=='0' and rail_probe['role']=='region' and rail_probe['label'],rail_probe
                    # Keep the rail itself inside its clipping ancestor before distinguishing already-visible content from genuine internal overflow.
                    assert rail_probe['owner'] and rail_probe['box']['left']>=rail_probe['owner']['left']-1 and rail_probe['box']['right']<=rail_probe['owner']['right']+1,rail_probe
                    # Record whether the rendered locale and viewport genuinely need the rail's horizontal scroll range.
                    rail_overflows=rail_probe['scrollWidth']>rail_probe['clientWidth']+1
                    # Require overflowing content to own a positive range; otherwise require the final ball to be fully visible without scrolling.
                    assert (rail_overflows and rail_probe['maxScrollLeft']>0 and rail_probe['last']['right']>rail_probe['box']['right']) or (not rail_overflows and rail_probe['maxScrollLeft']<=1 and rail_probe['last']['left']>=rail_probe['box']['left']-1 and rail_probe['last']['right']<=rail_probe['box']['right']+1),rail_probe
                    # Scroll through the public region to the terminal edge and prove the final ball becomes fully reachable.
                    page.get_by_test_id('keno-drawn-balls').evaluate('rail => { rail.scrollLeft=rail.scrollWidth; rail.focus({preventScroll:true}); }')
                    # Read the terminal geometry and focus state after the browser commits the scroll position.
                    rail_terminal=page.get_by_test_id('keno-drawn-balls').evaluate("""rail => { const box=rail.getBoundingClientRect(); const last=rail.querySelector('[data-testid="keno-drawn-ball"]:last-child')?.getBoundingClientRect(); return {scrollLeft:rail.scrollLeft,focused:document.activeElement===rail,box:{left:box.left,right:box.right},last:last&&{left:last.left,right:last.right}}; }""")
                    # Require the final ball to remain visible when everything fits or become visible at the terminal internal-scroll edge.
                    assert rail_terminal['focused'] and ((rail_overflows and rail_terminal['scrollLeft']>0) or (not rail_overflows and rail_terminal['scrollLeft']<=1)) and rail_terminal['last']['left']>=rail_terminal['box']['left']-1 and rail_terminal['last']['right']<=rail_terminal['box']['right']+1,rail_terminal
                    # Reveal the right edge through the intended board scroller before final-state capture.
                    page.get_by_test_id('keno-board-scroll').evaluate('scroll => { scroll.scrollLeft=scroll.scrollWidth; }')
                    # Capture the result rail itself on desktop so the outer game-outlet scrollport cannot pad or hide the exact terminal edge under review.
                    edge_final_evidence_selector='[data-testid="keno-drawn-balls"]' if edge_viewport_id in ('desktop_primary','desktop_compact') else '.keno-premium'
                    # Record final-draw and caught/latest evidence for this exact locale and viewport.
                    region_evidence(f'after-pass-keno-edge-final-caught-{edge_locale.lower()}-{edge_viewport_id}.png',edge_final_evidence_selector,'keno',['edge_final_caught'],edge_locale,edge_viewport_id)
                    # Count the exact final-edge matrix cell.
                    keno_matrix_cells+=1
                    # Record exact settled result evidence with the authoritative multiplier and payout visible.
                    region_evidence(f'after-pass-keno-result-{edge_locale.lower()}-{edge_viewport_id}.png','.keno-premium','keno',['result'],edge_locale,edge_viewport_id)
                    # Count the exact result matrix cell.
                    keno_matrix_cells+=1
                    # Persist the authoritative settled fixture again before testing a distinct route reconstruction.
                    save_player_game_state('keno',edge_player,final_edge_state)
                    # Reconstruct the route independently from the persisted result instead of reusing the result DOM.
                    page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
                    # Reapply the matrix locale because the durable account preference correctly owns each reload in an unfiltered run.
                    page.get_by_test_id('shell-locale-select').select_option(edge_locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=edge_locale)
                    # Require the child server to expose the same parent-written draw after a second independent reconstruction.
                    page.wait_for_function("() => document.querySelectorAll('[data-testid=\"keno-drawn-ball\"]').length === 20",timeout=WAIT_MS)
                    # Read the exact state returned by the frozen public route after reconstruction.
                    restored_edge_state=page.request.get(base+'/api/v1/games/keno/state').json()['data']['state']
                    # Resolve the exact authoritative terminal draw and ticket used by the restored surface.
                    restored_edge_draw=restored_edge_state['last_draws'][-1]; restored_edge_ticket=restored_edge_draw['results'][0]['ticket']
                    # Require exact round, spots, and amount rather than accepting a visually similar route.
                    assert restored_edge_draw['round_id']=='keno-edge-final' and restored_edge_ticket['spots']==edge_draw and float(restored_edge_ticket['amount'])==1.0,restored_edge_state
                    # Require the reconstructed public controls to reflect exactly the restored ticket.
                    assert page.locator('.keno-num.selected').count()==len(edge_draw) and all(page.get_by_test_id(f'keno-num-{edge_number}').get_attribute('aria-pressed')=='true' for edge_number in edge_draw) and float(page.get_by_test_id('keno-amount').input_value())==1.0
                    # Record route-restored evidence only after exact state and live-control assertions pass.
                    region_evidence(f'after-pass-keno-route-restored-{edge_locale.lower()}-{edge_viewport_id}.png','.keno-premium','keno',['route_restored'],edge_locale,edge_viewport_id)
                    # Count the exact route-restored matrix cell.
                    keno_matrix_cells+=1
                    # Bring the enabled Repeat control into view before creating a distinct focus-visible state.
                    repeat_edge_control=page.locator('[data-action="repeat"]'); repeat_edge_control.scroll_into_view_if_needed(); repeat_edge_control.focus()
                    # Read the exact accessible and focus state from the live Repeat control.
                    repeat_edge_probe=repeat_edge_control.evaluate("control => ({focused:document.activeElement===control,disabled:control.disabled,ariaDisabled:control.getAttribute('aria-disabled'),text:control.textContent.trim()})")
                    # Require a visibly focused, enabled, named Repeat control backed by the restored ticket.
                    assert repeat_edge_probe['focused'] and not repeat_edge_probe['disabled'] and repeat_edge_probe['ariaDisabled']!='true' and repeat_edge_probe['text'],repeat_edge_probe
                    # Record repeat-available evidence only after its distinct focus and authoritative state pass.
                    region_evidence(f'after-pass-keno-repeat-available-{edge_locale.lower()}-{edge_viewport_id}.png','.keno-premium','keno',['repeat_available'],edge_locale,edge_viewport_id)
                    # Count the exact repeat-available matrix cell.
                    keno_matrix_cells+=1
            # Require every one of the 64 governed Keno matrix cells to have passed assertions and emitted evidence.
            assert keno_matrix_cells==keno_matrix_expected_cells,(keno_matrix_cells,keno_matrix_expected_cells)
            # Restore an empty English desktop route so the existing real-draw regression remains independent.
            save_player_game_state('keno',edge_player,empty_edge_state); page.set_viewport_size({'width':1920,'height':1080}); page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS); page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
        # Prove restored ticket authority, repeat, autoplay, and aligned history through public controls. (issue #472)
        def keno_economics_route_behavior():
            # Resolve the authenticated player whose isolated state drives this current-route proof.
            behavior_player=browser_player_id
            # Build one settled result whose amount intentionally differs from the Keno default.
            settled_spots=[2,4,6,8,10]
            # Apply the exact production one-cent payout expression for the no-catch fixture.
            settled_state={'open_tickets':[],'last_draws':[{'round_id':'keno-restore-settled','timestamp':'2026-07-20T00:00:00Z','drawn':list(range(21,41)),'results':[{'ticket':{'ticket_id':'keno-restore-ticket','player_id':behavior_player,'spots':settled_spots,'amount':0.07,'source':'browser-test','created_at':'2026-07-20T00:00:00Z'},'catches':[],'catch_count':0,'multiplier':0,'payout':0}]}]}
            # Add a newer open ticket with different authority for the open-ticket restoration branch.
            open_spots=[1,5,9]
            # Persist both sources so the open ticket must win visible restoration precedence.
            open_state={'open_tickets':[{'ticket_id':'keno-open-restore','player_id':behavior_player,'spots':open_spots,'amount':0.11,'source':'browser-test','created_at':'2026-07-20T00:01:00Z'}],'last_draws':settled_state['last_draws']}
            # Reconstruct the route from the state containing both historical and open-ticket values.
            save_player_game_state('keno',behavior_player,open_state); page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
            # Read each open-ticket restoration predicate into one diagnostic probe.
            open_restore_probe={'amount':float(page.get_by_test_id('keno-amount').input_value()),'open_rows':page.get_by_test_id('keno-open-ticket').count(),'selected_count':page.locator('.keno-num.selected').count(),'pressed_spots':[spot for spot in open_spots if page.get_by_test_id(f'keno-num-{spot}').get_attribute('aria-pressed')=='true'],'drawn_count':page.locator('[data-testid="keno-drawn-ball"]').count(),'paytable_comparisons':page.get_by_test_id('keno-paytable-comparison').count(),'new_ticket_controls':page.get_by_test_id('keno-new-ticket').count(),'buy_controls':page.get_by_test_id('keno-buy').count()}
            # Require the newest open human ticket to own the exact live fake-token amount.
            assert open_restore_probe['amount']==0.11,open_restore_probe
            # Require exactly one visible open-ticket row instead of the older result drawer.
            assert open_restore_probe['open_rows']==1,open_restore_probe
            # Require exactly the three authoritative open-ticket spots to remain selected and pressed.
            assert open_restore_probe['selected_count']==len(open_spots) and open_restore_probe['pressed_spots']==open_spots,open_restore_probe
            # Require the older settled draw to remain history only while the open ticket owns the board.
            assert open_restore_probe['drawn_count']==0,open_restore_probe
            # Require selection controls and reject every historical result-mode surface.
            assert open_restore_probe['buy_controls']==1 and open_restore_probe['paytable_comparisons']==0 and open_restore_probe['new_ticket_controls']==0,open_restore_probe
            # Replace the state with settled history only so repeat and autoplay restoration share one authority.
            save_player_game_state('keno',behavior_player,settled_state); page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
            # Require settled history to restore the exact live amount, spots, and repeat availability.
            assert float(page.get_by_test_id('keno-amount').input_value())==0.07 and page.locator('.keno-num.selected').count()==len(settled_spots) and all(page.get_by_test_id(f'keno-num-{spot}').get_attribute('aria-pressed')=='true' for spot in settled_spots) and not page.locator('[data-action="repeat"]').is_disabled()
            # Capture the repeat purchase request emitted by the real visible control.
            with page.expect_response(lambda response: response.url.endswith('/api/v1/games/keno/draw') and response.request.method=='POST') as repeat_draw_response:
                # Capture the ticket purchase paired with the same repeat action.
                with page.expect_request(lambda request: request.url.endswith('/api/v1/games/keno/tickets') and request.method=='POST') as repeat_request:
                    # Start the one-click repeat through the player-facing action.
                    page.locator('[data-action="repeat"]').click()
            # Parse the exact frozen-v1 request body sent by repeat.
            repeat_body=repeat_request.value.post_data_json
            # Require repeat to reuse both exact restored fields.
            assert repeat_body['spots']==settled_spots and float(repeat_body['amount'])==0.07,repeat_body
            # Read the terminal draw response before any seeded state can replace it.
            repeat_draw=repeat_draw_response.value.json()['data']['draw']
            # Resolve the exact human result and round identity returned by the action.
            repeat_result=next(result for result in repeat_draw['results'] if result['ticket']['player_id']==behavior_player)
            # Wait for the exact new round identity to become visible in history.
            page.wait_for_function("""roundId => [...document.querySelectorAll('[data-testid="keno-history"] .keno-history-row span')].some(node => node.textContent.trim()===roundId)""",arg=repeat_draw['round_id'],timeout=7000)
            # Read player-scoped Keno history only after the exact terminal round is visible.
            repeat_history=page.request.get(base+'/api/v1/casino/history?game=keno').json()['data']['history']
            # Resolve the exact aligned history row by current round identity.
            repeat_history_row=next(row for row in repeat_history if row['round_id']==repeat_draw['round_id'])
            # Decode its compatibility-preserved structured details.
            repeat_details=json.loads(repeat_history_row['details_json'])
            # Require exact amount, spots, catches, payout, and outcome alignment.
            assert float(repeat_history_row['amount'])==0.07 and repeat_details['spots']==settled_spots and repeat_details['catches']==repeat_result['catches'] and float(repeat_history_row['payout'])==float(repeat_result['payout']) and repeat_history_row['outcome']==('win' if repeat_result['payout'] else 'loss'),repeat_history_row
            # Read the exact post-repeat state from the current public state route.
            repeat_state=page.request.get(base+'/api/v1/games/keno/state').json()['data']['state']
            # Require exactly one added draw whose settled ticket retains repeat's restored fields.
            assert len(repeat_state['last_draws'])==2 and repeat_state['last_draws'][-1]['results'][0]['ticket']['spots']==settled_spots and float(repeat_state['last_draws'][-1]['results'][0]['ticket']['amount'])==0.07,repeat_state
            # Re-seed the settled fixture so the first autoplay tick starts from a clean reload.
            save_player_game_state('keno',behavior_player,settled_state); page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
            # Configure exactly one fast autoplay round through public controls.
            page.get_by_test_id('keno-auto-rounds').fill('1'); page.get_by_test_id('keno-auto-speed').select_option('fast')
            # Capture the first autoplay purchase request after route restoration.
            with page.expect_response(lambda response: response.url.endswith('/api/v1/games/keno/draw') and response.request.method=='POST',timeout=WAIT_MS * 2) as autoplay_draw_response:
                # Capture the first ticket purchase paired with the one-round autoplay session.
                with page.expect_request(lambda request: request.url.endswith('/api/v1/games/keno/tickets') and request.method=='POST',timeout=WAIT_MS * 2) as autoplay_request:
                    # Start server-authorized autoplay through the mounted control plane.
                    page.get_by_test_id('keno-auto-start').click()
            # Parse the first autoplay action body.
            autoplay_body=autoplay_request.value.post_data_json
            # Require the first tick to reuse exact restored spots and amount without falling back to five.
            assert autoplay_body['spots']==settled_spots and float(autoplay_body['amount'])==0.07,autoplay_body
            # Read the terminal autoplay draw response before checking rendered state.
            autoplay_draw=autoplay_draw_response.value.json()['data']['draw']
            # Resolve the exact first-tick human result.
            autoplay_result=next(result for result in autoplay_draw['results'] if result['ticket']['player_id']==behavior_player)
            # Wait for the exact new round identity and stopped one-round control-plane state.
            page.wait_for_function("""roundId => document.querySelector('[data-testid="autoplay-keno"] .badge')?.textContent==='Off' && [...document.querySelectorAll('[data-testid="keno-history"] .keno-history-row span')].some(node => node.textContent.trim()===roundId)""",arg=autoplay_draw['round_id'],timeout=WAIT_MS * 2)
            # Read player-scoped Keno history after exact autoplay completion.
            autoplay_history=page.request.get(base+'/api/v1/casino/history?game=keno').json()['data']['history']
            # Resolve and decode the exact aligned autoplay history row.
            autoplay_history_row=next(row for row in autoplay_history if row['round_id']==autoplay_draw['round_id']); autoplay_details=json.loads(autoplay_history_row['details_json'])
            # Require exact first-tick amount, spots, catches, payout, and outcome alignment.
            assert float(autoplay_history_row['amount'])==0.07 and autoplay_details['spots']==settled_spots and autoplay_details['catches']==autoplay_result['catches'] and float(autoplay_history_row['payout'])==float(autoplay_result['payout']) and autoplay_history_row['outcome']==('win' if autoplay_result['payout'] else 'loss'),autoplay_history_row
            # Read the exact post-autoplay state from the public route.
            autoplay_state=page.request.get(base+'/api/v1/games/keno/state').json()['data']['state']
            # Require one and only one added draw whose first tick retained restored fields.
            assert len(autoplay_state['last_draws'])==2 and autoplay_state['last_draws'][-1]['results'][0]['ticket']['spots']==settled_spots and float(autoplay_state['last_draws'][-1]['results'][0]['ticket']['amount'])==0.07,autoplay_state
            # Restore an empty state so the following legacy Keno acceptance starts independently.
            save_player_game_state('keno',behavior_player,{'open_tickets':[],'last_draws':[]}); page.reload(wait_until='networkidle'); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
        # Combine the existing edge proof and new economics behavior under their one contiguous owning case.
        def keno_complete_acceptance():
            # Execute all sixty-four exact visual-matrix cells first.
            keno_edge_containment()
            # Execute current-route restoration, Repeat, autoplay, and history behavior second.
            keno_economics_route_behavior()
        # Execute complete Keno geometry, economics, restoration, and interaction acceptance on one shard.
        run_case('BR-KENO-EDGE-001',['KENO-025','KENO-026','KENO-027','TEST-078','TEST-113','TEST-147'],keno_complete_acceptance)
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
        page.wait_for_function("""() => document.querySelectorAll('[data-testid="keno-drawn-ball"]').length === 20""", timeout=WAIT_MS); page.get_by_test_id('keno-paytable-comparison').wait_for(timeout=WAIT_MS)
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
            keno_singular_player=browser_player_id
            # Seed deterministic one-catch Keno state so singular copy is proven without relying on a random draw.
            keno_singular_state={'open_tickets':[],'last_draws':[{'round_id':'keno-singular-copy','timestamp':'2026-07-19T00:00:00Z','drawn':list(range(1,21)),'results':[{'ticket':{'ticket_id':'keno-one-catch','player_id':keno_singular_player,'spots':[1],'amount':1,'source':'browser-test','created_at':'2026-07-19T00:00:00Z'},'catches':[1],'catch_count':1,'multiplier':keno_engine.PAYTABLE[1][1],'payout':round(1.0*keno_engine.PAYTABLE[1][1],2)}]}]}
            # Persist the focused state through the same test data store used by the browser server.
            save_player_game_state('keno',keno_singular_player,keno_singular_state)
            # Select English before reload so the copy assertion checks the exact reported wording.
            page.get_by_test_id('shell-locale-select').select_option('en-US')
            # Reload the route so the visible browser client renders the persisted one-catch result.
            page.reload(); page.get_by_test_id('keno-premium-hero').wait_for(timeout=WAIT_MS)
            # Read the visible result copy after the route reload.
            keno_singular_result=page.get_by_test_id('keno-result').inner_text()
            # Require singular English copy and reject the reported plural grammar defect.
            assert '1 catch on a 1-spot ticket' in keno_singular_result and '1 catches' not in keno_singular_result
        run_case('BR-KENO-001',['KENO-009','KENO-010','KENO-011','KENO-012','KENO-013','KENO-014','KENO-015','KENO-018','KENO-020','KENO-021','KENO-022','KENO-023','KENO-024','TEST-066','AUTO-012','UX-007','UX-009','CORE-034'],premium_keno)
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
    # Preserve exact case accounting when the active shard does not own Keno.
    else:
        # Advance only the contiguous Keno registrations.
        skip_browser_affinity('keno')
