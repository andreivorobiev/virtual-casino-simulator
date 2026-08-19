# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own the complete disposable guest-lifecycle Browser affinity family."""

# Serialize visual evidence metadata and the mocked policy envelope.
import json
# Read the exact CI source identity for governed guest evidence sidecars.
import os
# Resolve the exact commit and branch without transferring runner lifecycle ownership.
import subprocess

# Import the sole environment-scalable Playwright wait budget. (TEST-053)
from tests.browser_timing import WAIT_MS


# Execute or skip the complete guest producer/consumer group without splitting its shard ownership.
def run_cases(run_case, browser_shard_owns_group, skip_browser_affinity, browser, base, screenshots, ROOT, read_i18n_json, auth_core, guest_analytics):
    """Run all three guest-lifecycle cases as one affinity-owned unit."""
    # Execute every disposable guest setup, transition, and teardown only on the declared owner.
    if browser_shard_owns_group('guest_lifecycle'):
        # Define exact visual-matrix viewports for disposable guest entry and lifecycle evidence. (issue #317)
        guest_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
        # Read exact source identity once for focused guest evidence sidecars.
        guest_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True).strip()
        # Prefer the CI head ref while retaining a safe detached fallback.
        guest_evidence_branch=os.environ.get('GITHUB_HEAD_REF') or subprocess.check_output(['git','branch','--show-current'],cwd=str(ROOT),text=True).strip() or 'detached'
        # Capture one complete guest surface with VIS-EVIDENCE-001 metadata.
        def guest_evidence(guest_page,name,surface,states,locale,viewport_id):
            # Resolve the standard artifact path beneath the browser-test output directory.
            target=screenshots/name
            # Capture the complete responsive surface without transient toast content.
            guest_page.screenshot(path=str(target),full_page=True,animations='disabled',style='#toast { visibility: hidden !important; }')
            # Read the exact active viewport dimensions for the sidecar.
            viewport=guest_page.viewport_size
            # Read the focused control so keyboard acceptance remains auditable.
            focused=guest_page.evaluate("() => document.activeElement?.getAttribute('data-testid') || ''")
            # Build exact-head after-pass metadata for the named visual-matrix row.
            metadata={'evidence_class':'after_pass','branch':guest_evidence_branch,'commit':guest_evidence_commit,'surface':surface,'states':states,'locale':locale,'viewport':{'id':viewport_id,**viewport},'path':str(target.relative_to(ROOT)).replace('\\','/'),'focused_control':focused}
            # Write the self-describing UTF-8 sidecar next to the image.
            target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        # Collect one result row per locale and governed viewport.
        guest_results=[]
        # Initialize the admission-UI result before the owner exercises the mocked disabled-policy surface.
        guest_policy_disabled_result=True
        # Exercise truthful policy omission once on the shard that owns guest lifecycle Browser evidence. (UX-028)
        # Create one isolated context so the mocked read-only policy cannot affect real guest creation cases.
        guest_policy_context=browser.new_context(viewport=guest_viewports['desktop_primary'])
        # Open one page for the disabled-capability render.
        guest_policy_page=guest_policy_context.new_page()
        # Return a complete standard public policy envelope with only guest admission paused.
        guest_policy_page.route('**/api/v2/auth/enrollment-policy',lambda route: route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'data':{'enrollment_mode':'closed','signup_enabled':False,'signup_methods':{'email':False,'google':False,'facebook':False},'guest_trials_enabled':False,'invitation_enrollment_enabled':False,'guest_conversion_enabled':True,'passkeys_enabled':False,'canonical_identity':'casino_user_id','shared_auth_origin':'tiltseven_first_party'}})))
        # Start protected inspection so the isolated browser context always closes.
        try:
            # Navigate to the real login shell and wait for the mocked policy-owned unavailable chip.
            guest_policy_page.goto(base,wait_until='networkidle'); guest_policy_page.get_by_test_id('guest-trial-unavailable').wait_for(timeout=WAIT_MS)
            # Require the unauthorized mutation control to be absent with no disabled interactive substitute.
            guest_policy_disabled_result=guest_policy_page.get_by_test_id('guest-trial-button').count()==0 and guest_policy_page.get_by_test_id('guest-trial-unavailable').is_visible() and guest_policy_page.locator('[data-testid="login-gate"] :is(button,input,select):disabled').count()==0
        # Destroy the mocked context before real guest creation begins.
        finally:
            # Close page, routes, cookies, and storage together.
            guest_policy_context.close()
        # Exercise both installed locales through their browser-visible selector.
        for guest_locale in ('en-US','ru-RU'):
            # Exercise every governed viewport from the visual matrix.
            for guest_viewport_id,guest_viewport in guest_viewports.items():
                # Create a fresh browser context so no account or guest credential can leak between cases.
                guest_context=browser.new_context(viewport=guest_viewport,reduced_motion='reduce')
                # Open the account-free entry surface inside the isolated context.
                guest_page=guest_context.new_page()
                # Start protected guest verification so context and temporary credentials always close.
                try:
                    # Navigate without a seeded cookie so the real backend returns the login gate.
                    guest_page.goto(base,wait_until='networkidle'); guest_page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS); guest_page.get_by_test_id('guest-trial-button').wait_for(timeout=WAIT_MS)
                    # Select the tested locale through the browser-visible login control.
                    guest_page.get_by_test_id('auth-locale-select').select_option(guest_locale)
                    # Wait until translated disposable terms copy replaces the prior locale.
                    guest_page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=guest_locale)
                    # Prove a button click without affirmative consent creates no session or route transition.
                    guest_page.get_by_test_id('guest-trial-button').click(); guest_page.wait_for_timeout(100)
                    # Require the localized shared validation message, unchanged login surface, and exact checkbox focus.
                    assert guest_page.get_by_test_id('login-gate').is_visible() and guest_page.locator('#auth-message').inner_text().strip()==read_i18n_json(ROOT/'web'/'i18n'/guest_locale/'shell.json')['auth.termsRequired'] and guest_page.evaluate("() => document.activeElement?.dataset.testid==='login-terms-check'")
                    # Require the lifecycle disclosure to be collapsed and button-owned before interaction.
                    assert guest_page.get_by_test_id('guest-disclosure-toggle').get_attribute('aria-expanded')=='false' and guest_page.get_by_test_id('guest-trial-details').is_hidden()
                    # Expand the real disclosure without animation or a second live announcement.
                    guest_page.get_by_test_id('guest-disclosure-toggle').click()
                    # Require the unchanged complete lifecycle wording and exact expanded semantics.
                    assert guest_page.get_by_test_id('guest-disclosure-toggle').get_attribute('aria-expanded')=='true' and guest_page.get_by_test_id('guest-trial-details').inner_text()==read_i18n_json(ROOT/'web'/'i18n'/guest_locale/'shell.json')['auth.guestInfo'] and guest_page.evaluate("() => getComputedStyle(document.querySelector('[data-testid=guest-trial-details]')).animationName==='none'")
                    # Collapse optional lifecycle detail before fit evidence and downstream actions.
                    guest_page.get_by_test_id('guest-disclosure-toggle').click()
                    # Require one live owner and no permanently disabled interactive element in the settled default gate.
                    assert guest_page.locator('[data-testid="login-gate"] [aria-live]').count()==1 and guest_page.locator('[data-testid="login-gate"] :is(button,input,select):disabled').count()==0
                    # Require brand, legal line, guest, terms, and returning-user block above the 375-by-812 fold.
                    if guest_viewport_id=='mobile':
                        # Read the complete accepted mobile geometry from the browser after policy settlement.
                        mobile_fit=guest_page.evaluate("() => ({scrollHeight:document.documentElement.scrollHeight,innerHeight,guest:document.querySelector('[data-testid=guest-trial-button]')?.getBoundingClientRect().bottom||0,terms:document.querySelector('[data-testid=login-terms-check]')?.closest('label')?.getBoundingClientRect().bottom||0,signin:document.querySelector('.auth-signin')?.getBoundingClientRect().bottom||0,legal:document.querySelector('#auth-legal-line')?.getBoundingClientRect().bottom||0})")
                        # Reject document scroll or any required decision extending below the exact phone viewport.
                        assert mobile_fit['scrollHeight']<=mobile_fit['innerHeight']+1 and max(mobile_fit['guest'],mobile_fit['terms'],mobile_fit['signin'],mobile_fit['legal'])<=mobile_fit['innerHeight']+1,mobile_fit
                    # Require the complete login surface to stay inside the page viewport.
                    assert guest_page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
                    # Capture localized unaccepted-consent and disclosure evidence.
                    guest_evidence(guest_page,f'after-pass-guest-auth-unaccepted-{guest_locale}-{guest_viewport_id}.png','auth',['guest','guest_terms_unaccepted','guest_disclosure','reduced_motion'],guest_locale,guest_viewport_id)
                    # Accept the visible versioned terms through the native checkbox.
                    guest_page.get_by_test_id('login-terms-check').check()
                    # Capture the explicit accepted state separately from the required unaccepted state.
                    guest_evidence(guest_page,f'after-pass-guest-auth-accepted-{guest_locale}-{guest_viewport_id}.png','auth',['guest','guest_terms_accepted','guest_disclosure','reduced_motion'],guest_locale,guest_viewport_id)
                    # Observe real guest creation after affirmative consent.
                    with guest_page.expect_response(lambda response: response.url.endswith('/api/v2/auth/guest') and response.request.method=='POST') as guest_response_info:
                        # Start the disposable session through the visible account-free action.
                        guest_page.get_by_test_id('guest-trial-button').click()
                    # Store the real standard envelope for principal and wallet assertions.
                    guest_payload=guest_response_info.value.json()
                    # Wait for the authenticated lobby after sessionStorage has captured the one-time proof.
                    guest_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Read current-user state through the frontend helper that attaches the browser proof.
                    guest_current=guest_page.evaluate("async () => (await import('/core/api.js')).currentUser()")
                    # Open personal settings to prove guest conversion is visible but separate from Admin enrollment policy. (CONVERT-003)
                    guest_page.get_by_test_id('nav-settings').click(); guest_page.get_by_test_id('guest-conversion').wait_for(timeout=WAIT_MS)
                    # Require a complete conversion form and sound-off default without submitting identifying data.
                    guest_conversion_visible=guest_page.get_by_test_id('guest-conversion-submit').is_visible() and not guest_page.get_by_test_id('personal-settings-sound').is_checked()
                    # Require the personal/convert cards to remain inside the active responsive viewport.
                    assert guest_conversion_visible and guest_page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
                    # Capture the localized conversion offer without creating a durable account.
                    guest_evidence(guest_page,f'after-pass-guest-conversion-{guest_locale}-{guest_viewport_id}.png','shell_lobby',['guest_conversion_form','personal_sound_default_off'],guest_locale,guest_viewport_id)
                    # Return to the lobby before authorization and game-entry checks.
                    guest_page.get_by_test_id('nav-lobby').click(); guest_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Prove the guest cannot access the centrally protected Admin API with its valid proof.
                    guest_admin_code=guest_page.evaluate("async () => { try { await (await import('/core/api.js')).api('/api/v2/admin/guest-trials'); return 'ALLOWED'; } catch (error) { return error.code; } }")
                    # Read the persistent guest marker and localized End control.
                    guest_marker=guest_page.locator('#logout-btn').get_attribute('data-guest-trial')
                    # Require the registered-user token-credit menu to be absent from the guest experience.
                    guest_wallet_top_up_hidden=guest_page.locator('.wallet-menu').is_hidden()
                    # Require the active shell to keep its exact expiry and no-recovery disclosure visible.
                    guest_expiry_notice=guest_page.get_by_test_id('guest-trial-notice').is_visible() and bool(guest_page.get_by_test_id('guest-trial-notice').inner_text().strip())
                    # Open one released catalog game through the same visible action used by registered players.
                    guest_page.get_by_test_id('open-slots').click(); guest_page.get_by_test_id('slots-premium').wait_for(timeout=WAIT_MS)
                    # Record that a real game module mounted under the guest-bound player identity with reduced motion active.
                    guest_game_entered=guest_page.get_by_test_id('slots-premium').is_visible() and guest_page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
                    # Return through the shared navigation before exercising same-context refresh.
                    guest_page.get_by_test_id('nav-lobby').click(); guest_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Reload inside the same browser context to prove refresh preserves sessionStorage and access.
                    guest_page.reload(wait_until='networkidle'); guest_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
                    # Require no responsive page spill after the same-context reload.
                    assert guest_page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
                    # Focus the irreversible lifecycle control for keyboard evidence.
                    guest_page.locator('#logout-btn').focus()
                    # Capture localized active and same-context-refresh evidence.
                    guest_evidence(guest_page,f'after-pass-guest-shell-active-{guest_locale}-{guest_viewport_id}.png','shell_lobby',['guest_trial_active','guest_trial_expiry_warning','guest_trial_top_up_unavailable','guest_trial_same_context_refresh','guest_trial_reduced_motion'],guest_locale,guest_viewport_id)
                    # Capture the primary desktop shell at an explicit 200 percent CSS zoom with an equivalent half-width layout viewport.
                    if guest_viewport_id=='desktop_primary':
                        # Apply the established repository zoom technique while constraining layout width to the effective browser-zoom viewport.
                        guest_page.evaluate("() => { document.body.style.zoom='200%'; document.body.style.width='50%'; }"); guest_page.wait_for_timeout(100)
                        # Require the expiry disclosure and irreversible lifecycle control to remain visible at 200 percent zoom.
                        assert guest_page.get_by_test_id('guest-trial-notice').is_visible() and guest_page.locator('#logout-btn').is_visible()
                        # Capture the localized zoom acceptance separately from the normal responsive viewport matrix.
                        guest_evidence(guest_page,f'after-pass-guest-shell-zoom-200-{guest_locale}-{guest_viewport_id}.png','shell_lobby',['guest_trial_active','guest_trial_zoom_200'],guest_locale,guest_viewport_id)
                        # Restore the normal CSS viewport before ending the disposable trial.
                        guest_page.evaluate("() => { document.body.style.zoom=''; document.body.style.width=''; }")
                    # End the trial through the visible control and observe the canonical backend response.
                    with guest_page.expect_response(lambda response: response.url.endswith('/api/v2/auth/guest/end') and response.request.method=='POST') as guest_end_info:
                        # Activate the focused native button by keyboard.
                        guest_page.locator('#logout-btn').press('Enter')
                    # Store the identifier-free teardown acknowledgement.
                    guest_end_payload=guest_end_info.value.json()
                    # Require immediate return to the login gate.
                    guest_page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS)
                    # Reload to prove the explicitly ended trial cannot recover.
                    guest_page.reload(wait_until='networkidle'); guest_page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS)
                    # Capture the localized terminal redirect after the disposable session is irreversibly revoked.
                    guest_evidence(guest_page,f'after-pass-guest-auth-ended-{guest_locale}-{guest_viewport_id}.png','auth',['guest_trial_ended'],guest_locale,guest_viewport_id)
                    # Record the complete result without retaining any credential or raw browser proof.
                    guest_results.append({'locale':guest_locale,'viewport':guest_viewport_id,'created':guest_payload['ok'] is True,'role':guest_payload['data']['user'].get('role'),'balance':guest_current['player']['token_balance'],'conversion_visible':guest_conversion_visible,'marker':guest_marker,'top_up_hidden':guest_wallet_top_up_hidden,'expiry_notice':guest_expiry_notice,'game_entered':guest_game_entered,'admin_code':guest_admin_code,'ended':guest_end_payload['ok'] is True,'contained':guest_page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")})
                # Close the entire isolated context even if one viewport fails.
                finally:
                    # Destroy its cookies and sessionStorage without touching other browser work.
                    guest_context.close()
        # Prove browser-context loss makes a preserved cookie non-resumable in both locales. (issue #317)
        guest_close_results=[]
        # Run one primary-viewport close proof per locale because layout is already covered above.
        for guest_locale in ('en-US','ru-RU'):
            # Create the original browser context that owns sessionStorage proof material.
            original_context=browser.new_context(viewport=guest_viewports['desktop_primary'])
            # Open the disposable entry surface.
            original_page=original_context.new_page()
            # Navigate, localize, consent, and create the guest session.
            original_page.goto(base,wait_until='networkidle'); original_page.get_by_test_id('auth-locale-select').select_option(guest_locale); original_page.get_by_test_id('login-terms-check').check(); original_page.get_by_test_id('guest-trial-button').click(); original_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
            # Preserve only browser cookies to simulate browser restart without sessionStorage.
            preserved_cookies=original_context.cookies()
            # Close the original context so its browser proof is destroyed.
            original_context.close()
            # Create a distinct replacement context and restore only the cookie jar.
            replacement_context=browser.new_context(viewport=guest_viewports['desktop_primary'])
            # Install the preserved cookies without any sessionStorage proof.
            replacement_context.add_cookies(preserved_cookies)
            # Open a new page and allow the shell's current-user request to fail closed.
            replacement_page=replacement_context.new_page(); replacement_page.goto(base,wait_until='networkidle'); replacement_page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS)
            # Record the no-recovery result without retaining cookie values.
            guest_close_results.append(replacement_page.get_by_test_id('login-gate').is_visible())
            # Destroy the replacement context and its now-revoked cookie.
            replacement_context.close()
        # Initialize self-service conversion evidence before the owner performs the real terminal handoff.
        guest_conversion_analytics_result=True
        # Execute one real self-service conversion in a browser while the owning shard has the API server. (GUEST-007, TEST-195)
        # Create one isolated desktop context for the terminal conversion handoff.
        conversion_context=browser.new_context(viewport=guest_viewports['desktop_primary'],reduced_motion='reduce')
        # Open the account-free entry surface for the real self-service request.
        conversion_page=conversion_context.new_page()
        # Keep the converted account fixture contained even if a browser assertion fails.
        try:
            # Enter one disposable trial through the visible consent and guest controls.
            conversion_page.goto(base,wait_until='networkidle'); conversion_page.get_by_test_id('login-terms-check').check()
            # Observe the real guest creation before opening its personal settings.
            with conversion_page.expect_response(lambda response: response.url.endswith('/api/v2/auth/guest') and response.request.method=='POST'):
                # Start the browser-owned guest trial.
                conversion_page.get_by_test_id('guest-trial-button').click()
            # Wait for the authenticated shell and open the self-service conversion form.
            conversion_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS); conversion_page.get_by_test_id('nav-settings').click(); conversion_page.get_by_test_id('guest-conversion').wait_for(timeout=WAIT_MS)
            # Use one deterministic fixture mailbox that is unique inside the disposable Browser data root.
            conversion_email='browser-self-conversion-analytics@example.test'
            # Fill only the ordinary account fields accepted by the visible conversion form.
            conversion_page.locator('#conversion-email').fill(conversion_email); conversion_page.locator('#conversion-display-name').fill('Browser Converted Player'); conversion_page.locator('#conversion-password').fill('BrowserConvertPassw0rd!23'); conversion_page.locator('#conversion-terms').check()
            # Observe the real conversion response before the shell clears its disposable credential.
            with conversion_page.expect_response(lambda response: response.url.endswith('/api/v2/me/convert-guest') and response.request.method=='POST') as conversion_response_info:
                # Submit through the browser-visible self-service action.
                conversion_page.get_by_test_id('guest-conversion-submit').click()
            # Require the explicit sign-in handoff after successful account adoption.
            conversion_page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS)
            # Decode only the standard public result envelope for status and ending-balance proof.
            conversion_payload=conversion_response_info.value.json()
            # Resolve the durable account from its normalized public mailbox.
            conversion_account=auth_core.find_user_by_email(conversion_email)
            # Resolve the terminal guest only through its durable conversion link.
            conversion_guest=next(row for row in auth_core.load_users().get('users',[]) if row.get('converted_to_user_id')==conversion_account['user_id'])
            # Read the de-identified Admin projection after browser conversion committed.
            conversion_trial=guest_analytics.detail(conversion_guest['guest_analytics_id'])
            # Read active rows through the same filtered summary consumed by Guest Trials actions.
            conversion_active_ids={row['analytics_id'] for row in guest_analytics.summary(status='active',recent_limit=100)['recent']}
            # Bind browser completion, exact ending balance, one terminal event, and removal from active actions.
            guest_conversion_analytics_result=conversion_payload['ok'] is True and conversion_payload['data']['status']=='converted' and conversion_trial['end_reason']=='converted' and conversion_trial['ending_balance']==conversion_payload['data']['balance'] and len([event for event in conversion_trial['events'] if event.get('event')=='trial_terminal'])==1 and conversion_guest['guest_analytics_id'] not in conversion_active_ids
        # Always destroy cookies, sessionStorage, and transient form content together.
        finally:
            # Close the complete isolated conversion context.
            conversion_context.close()
        # Record the full locale, viewport, consent, lifecycle, authorization, refresh, and browser-close matrix.
        run_case('BR-GUEST-TRIAL-001',['GUEST-001','GUEST-002','GUEST-006','UX-028','USER-008','USER-009','CONVERT-003','TEST-081','TEST-158','TEST-176'],lambda: guest_policy_disabled_result and len(guest_results)==8 and all(result['created'] and result['role']=='guest' and result['balance']==10000.0 and result['conversion_visible'] and result['marker']=='true' and result['top_up_hidden'] and result['expiry_notice'] and result['game_entered'] and result['admin_code']=='FORBIDDEN' and result['ended'] and result['contained'] for result in guest_results) and all(guest_close_results))
        # Record the separately named same-context refresh and browser-context loss acceptance.
        run_case('BR-GUEST-REFRESH-001',['GUEST-002','TEST-081'],lambda: len(guest_results)==8 and all(result['ended'] for result in guest_results) and all(guest_close_results))
        # Record the real self-service conversion and de-identified Admin lifecycle convergence.
        run_case('BR-GUEST-CONVERT-ANALYTICS-001',['GUEST-007','TEST-195'],lambda: guest_conversion_analytics_result)
    # Preserve deterministic case positions when this shard does not own the complete family.
    else:
        # Advance all three permanent identities without opening any guest page or browser context.
        skip_browser_affinity('guest_lifecycle')
