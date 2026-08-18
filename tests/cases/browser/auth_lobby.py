# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Complete auth/lobby Browser affinity ownership behind the compatibility runner."""

# Import regular expressions for exact visible-text and route diagnostics retained by the extracted family.
import re


# Execute the complete producer/consumer family under one deterministic shard owner.
def run_cases(run_case,browser_shard_owns_group,skip_browser_affinity,browser_shard_owns,page,base,ROOT,visual_matrix,read_i18n_json,casino_config,assert_condition,shot,catalog_evidence,region_evidence,wallet_evidence,footer_evidence,game_evidence,console_errors,http_errors,provider_requests):
    # Run visible auth, wallet, shell, catalog, and lobby state only on the declared owner.
    if browser_shard_owns_group('auth_lobby'):
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
            # Navigate through the stable same-origin API documentation URL and wait for Swagger initialization.
            docs_response=page.goto(base+'/api-docs',wait_until='networkidle'); page.locator('#swagger-ui .download-url-wrapper').wait_for(timeout=10000)
            # Require the dedicated documentation bytes rather than an application-shell fallback.
            assert docs_response and docs_response.body()==(ROOT/'web'/'api-docs.html').read_bytes()
            # Require Swagger's selector to expose every governed contract exactly once.
            assert page.locator('#swagger-ui .download-url-wrapper select option').count()==len(list((ROOT/'contracts'/'openapi').glob('*.yaml')))
            # Fetch one representative contract through the public namespace and compare exact source bytes.
            contract_evidence=page.evaluate("""async () => { const response=await fetch('/openapi/casino.v1.yaml'); return {ok:response.ok,type:response.headers.get('content-type'),body:await response.text()}; }""")
            # Require same-origin YAML media type and exact repository contract content.
            assert contract_evidence['ok'] and contract_evidence['type'].startswith('application/yaml') and contract_evidence['body']==(ROOT/'contracts'/'openapi'/'casino.v1.yaml').read_text(encoding='utf-8')
            # Return to the anonymous application shell for the later visible Auth cases.
            page.goto(base,wait_until='networkidle')
            # Require the reload to restore the visible anonymous shell before later Auth cases continue.
            page.get_by_test_id('login-gate').wait_for(timeout=5000)
        # Record exact HTML and lazy JavaScript parity through the supported development browser adapter.
        run_case('BR-STATIC-CACHE-001',['CORE-026','TEST-068','API-003','TEST-152'],static_cache_parity)
        # Validate the checked repository-only TiltSeven scaffold without contacting a public host.
        def marketing_site_browser():
            # Define the exact local file used for each governed locale.
            locale_paths={'en-US':ROOT/'site'/'tiltseven'/'index.html','ru-RU':ROOT/'site'/'tiltseven'/'ru'/'index.html'}
            # Define the locale-owned safety text required in visible browser output.
            locale_safety={'en-US':('play tokens','No cash value.'),'ru-RU':('игровыми жетонами','Без денежной ценности.')}
            # Read every governed viewport from the authoritative visual matrix.
            viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the complete desktop, compact, tablet, and mobile inventory.
            assert set(viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Emulate reduced motion before loading either static locale document.
            page.emulate_media(reduced_motion='reduce')
            # Exercise both checked locale documents independently.
            for locale,locale_path in locale_paths.items():
                # Navigate only to repository bytes through a local file URL.
                page.goto(locale_path.resolve().as_uri(),wait_until='load')
                # Require the browser to remain on checked local bytes rather than a network origin.
                assert page.url.startswith('file:') and page.url.endswith(locale_path.name)
                # Wait for the stable marketing landmark before reading copy or geometry.
                page.locator('main[data-testid="marketing-site"]').wait_for(timeout=5000)
                # Require the authored locale, title, shared stylesheet, and local mark to load.
                identity=page.evaluate("""() => ({ lang:document.documentElement.lang, title:document.title, styleSheets:document.styleSheets.length, markComplete:document.querySelector('.brand img')?.complete===true, markWidth:document.querySelector('.brand img')?.naturalWidth||0, scripts:document.scripts.length, forms:document.forms.length })""")
                # Reject a missing resource, wrong locale, executable script, or collecting form.
                assert identity['lang']==locale.split('-')[0] and identity['title'].startswith('TiltSeven') and identity['styleSheets']==1 and identity['markComplete'] and identity['markWidth']>0 and identity['scripts']==0 and identity['forms']==0,identity
                # Read the complete visible copy for exact safety and encoding checks.
                visible_text=page.locator('body').inner_text()
                # Require both locale-owned safety phrases with no replacement character or unresolved template.
                assert all(value in visible_text for value in locale_safety[locale]) and '\uFFFD' not in visible_text and '{{' not in visible_text
                # Require exactly three non-activated links to the separately governed Casino origin.
                assert page.locator('a[href="https://casino.tiltseven.com/"]').count()==3
                # Start keyboard navigation at the document boundary.
                page.evaluate("() => document.activeElement?.blur()"); page.keyboard.press('Tab')
                # Require the skip link to receive visible keyboard focus.
                assert page.locator('.skip-link').evaluate("element => document.activeElement===element && element.getBoundingClientRect().top>=0")
                # Exercise every governed viewport with containment, touch-size, and exact-head evidence.
                for viewport_id,viewport in viewports.items():
                    # Resize to the exact named matrix dimensions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require the document, header, main landmark, and footer to remain horizontally contained.
                    containment=page.evaluate("""() => { const rows=[document.querySelector('.site-header'),document.querySelector('main[data-testid="marketing-site"]'),document.querySelector('.site-footer')]; return { document:document.documentElement.scrollWidth<=window.innerWidth+1, rows:rows.every(row=>row && row.scrollWidth<=row.clientWidth+1), clientWidth:document.documentElement.clientWidth, mainWidth:rows[1]?.getBoundingClientRect().width||0, primaryHeight:document.querySelector('.button.primary')?.getBoundingClientRect().height||0, navHeight:document.querySelector('.site-nav a')?.getBoundingClientRect().height||0 }; }""")
                    # Reject overflow, collapsed content, or sub-44-pixel primary navigation controls.
                    assert containment['document'] and containment['rows'] and containment['mainWidth']>=containment['clientWidth']-2 and containment['primaryHeight']>=44 and containment['navHeight']>=44,containment
                    # Prove the real mobile and desktop preview labels do not obscure the decorative seven chip.
                    preview_geometry=page.evaluate("""() => { const chip=document.querySelector('.seven-chip')?.getBoundingClientRect(); const panel=document.querySelector('.felt-panel')?.getBoundingClientRect(); const gap=chip&&panel?panel.top-chip.bottom:0; return { chipBottom:chip?.bottom||0, panelTop:panel?.top||0, gap, separated:Boolean(chip&&panel&&gap>=16) }; }""")
                    # Fail closed if either governed preview region is missing or lacks a readable separation gap.
                    assert preview_geometry['separated'],{'viewport':viewport_id,**preview_geometry}
                    # Capture one complete self-describing after-pass artifact for this locale and viewport.
                    game_evidence(f'after-pass-marketing-site-{locale.lower()}-{viewport_id}.png','marketing_site',['landing','keyboard_focus','reduced_motion'],locale,viewport_id)
            # Restore normal media, the primary viewport, and the local Casino login page for existing cases.
            page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size({'width':1920,'height':1080})
            # Return to the loopback application without preserving any public-site state.
            page.goto(base,wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000)
        # Record bilingual semantics, safety, accessibility, containment, and eight governed visual artifacts.
        run_case('BR-MARKETING-001',['MARKETING-001','MARKETING-002','TEST-107'],marketing_site_browser)
        # Capture logged-out login evidence for the frontend auth handback.
        shot('auth_login_gate.png')
        # Prove the restricted-preview guest surface keeps protected brand chrome absent and metadata out of the public title. (issue #321)
        def guest_restricted_brand_copy():
            # Enumerate every governed viewport because the issue requires the shared entry surface at all four sizes.
            brand_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the public document title to be the exact approved product name with no release suffix.
            assert page.title()=='TiltSeven'
            # Exercise the unauthenticated restricted-preview entry state in both installed locales.
            for brand_locale in ('en-US','ru-RU'):
                # Switch through the visible guest locale control and wait for the canonical locale state.
                page.get_by_test_id('auth-locale-select').select_option(brand_locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=brand_locale)
                # Read the exact safety acknowledgement from the locale-owned shell resource.
                expected_safety=read_i18n_json(ROOT/'web'/'i18n'/brand_locale/'shell.json')['auth.termsCheck']
                # Require the guest surface to preserve the full fake-money/play-token safety wording.
                assert expected_safety in page.get_by_test_id('login-gate').locator('label.check-row').inner_text()
                # Require the protected authenticated topbar, wallet, and diagnostics provenance to remain absent for guests.
                assert not page.get_by_test_id('premium-topbar').is_visible() and not page.get_by_test_id('premium-wallet').is_visible() and not page.get_by_test_id('shell-status').is_visible()
                # Capture exact-head restricted-preview guest evidence at every governed viewport.
                for viewport_id,viewport in brand_viewports.items():
                    # Resize to the exact named visual-matrix viewport before geometry assertions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Reject page or login-panel horizontal overflow while requiring the current login state to remain visible.
                    assert page.get_by_test_id('login-gate').is_visible() and page.evaluate("() => { const panel=document.querySelector('[data-testid=\"login-gate\"]'); return document.documentElement.scrollWidth <= window.innerWidth + 1 && panel.scrollWidth <= panel.clientWidth + 1; }")
                    # Record self-describing after-pass evidence for both the guest and restricted-preview state identifiers.
                    game_evidence(f'after-pass-shell-brand-guest-restricted-preview-{brand_locale.lower()}-{viewport_id}.png','auth',['login','guest','restricted_preview'],brand_locale,viewport_id)
            # Restore the primary desktop viewport while keeping Russian selected for the existing authentication flow.
            page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
        # Record guest/restricted-preview title, access-boundary, safety-copy, locale, and viewport acceptance.
        run_case('BR-SHELL-BRAND-GUEST-001',['UX-014','TEST-079'],guest_restricted_brand_copy)
        # Define policy-aware OAuth omission, localization, no-request, and visual evidence acceptance. (UX-028)
        def oauth_disabled_browser():
            # Read all four governed Auth viewports from the authoritative visual matrix.
            viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the complete desktop, compact, tablet, and mobile matrix.
            assert set(viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Exercise default action omission in every installed Auth locale.
            for locale in ('en-US','ru-RU'):
                # Switch the visible login gate through its own localized selector.
                page.get_by_test_id('auth-locale-select').select_option(locale)
                # Wait for the synchronous gate rerender and active locale state.
                page.wait_for_function("locale => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === locale",arg=locale)
                # Wait for the policy-owned invite chip to prove asynchronous capability settlement.
                page.get_by_test_id('signup-invite-only').wait_for(timeout=5000)
                # Require unavailable signup and provider actions to be absent rather than disabled.
                assert page.get_by_test_id('signup-entry-link').count()==0 and page.get_by_test_id('oauth-google').count()==0 and page.get_by_test_id('oauth-facebook').count()==0 and page.get_by_test_id('oauth-providers-available').count()==0
                # Expand the invite-only explanation through its real button-owned disclosure.
                page.get_by_test_id('signup-invite-only').click()
                # Require exact expanded semantics and localized explanatory copy.
                assert page.get_by_test_id('signup-invite-only').get_attribute('aria-expanded')=='true' and page.get_by_test_id('signup-invite-only-copy').is_visible() and page.get_by_test_id('signup-invite-only-copy').inner_text()==read_i18n_json(ROOT/'web'/'i18n'/locale/'shell.json')['signup.entryCopy']
                # Collapse the optional explanation before governed fit evidence.
                page.get_by_test_id('signup-invite-only').click()
                # Require no dead controls, no provider action traffic, and one live status owner.
                assert page.locator('[data-testid="login-gate"] :is(button,input,select):disabled').count()==0 and not provider_requests and page.locator('[data-testid="login-gate"] [aria-live]').count()==1
                # Capture exact-head default-policy evidence at every governed viewport.
                for viewport_id,viewport in viewports.items():
                    # Resize to the matrix dimensions before checking layout and capturing evidence.
                    page.set_viewport_size(viewport); page.wait_for_timeout(150)
                    # Require neither the document nor the Auth scroll container/card to overflow horizontally.
                    assert page.evaluate("() => { const screen=document.querySelector('.auth-screen'); const panel=document.querySelector('.auth-panel'); return document.documentElement.scrollWidth <= window.innerWidth + 1 && screen.scrollWidth <= screen.clientWidth + 1 && panel.scrollWidth <= panel.clientWidth + 1; }")
                    # Write policy-aware omission evidence through the shared exact-head helper.
                    game_evidence(f'after-pass-auth-policy-default-{locale}-{viewport_id}.png','auth',['policy_default','invite_only','oauth_actions_omitted'],locale,viewport_id)
            # Override the read-only enrollment endpoint with actionable signup policy.
            page.route('**/api/v2/auth/enrollment-policy',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"enrollment_mode":"self-signup","signup_enabled":true,"signup_methods":{"email":true,"google":true,"facebook":false},"guest_trials_enabled":true,"invitation_enrollment_enabled":true,"guest_conversion_enabled":true,"passkeys_enabled":false,"canonical_identity":"casino_user_id","shared_auth_origin":"tiltseven_first_party"}}'))
            # Publish one sign-in-ready provider and keep the second unavailable.
            page.route('**/api/v2/auth/oauth/providers',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"providers":[{"provider":"google","available":true,"signup_available":false},{"provider":"facebook","available":false,"signup_available":false}]}}'))
            # Exercise available signup and provider actions in both locales.
            for locale in ('en-US','ru-RU'):
                # Trigger fresh policy and provider reads through the visible locale rerender.
                page.get_by_test_id('auth-locale-select').select_option(locale)
                # Wait until the exact available provider and signup actions commit.
                page.get_by_test_id('oauth-providers-available').wait_for(timeout=5000); page.get_by_test_id('signup-entry-link').wait_for(timeout=5000)
                # Require only released actions to exist, with no disabled Facebook substitute.
                assert page.get_by_test_id('oauth-google').is_visible() and page.get_by_test_id('oauth-facebook').count()==0 and page.get_by_test_id('signup-entry-link').is_visible() and page.get_by_test_id('signup-invite-only').count()==0 and page.locator('[data-testid="login-gate"] :is(button,input,select):disabled').count()==0
                # Capture every governed viewport without activating sensitive navigation.
                for viewport_id,viewport in viewports.items():
                    # Resize to the exact matrix dimensions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require the Auth panel and available controls to remain horizontally contained.
                    assert page.evaluate("() => { const panel=document.querySelector('[data-testid=\"login-gate\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && panel.scrollWidth<=panel.clientWidth+1; }")
                    # Record available-provider after-pass evidence without a provider request.
                    game_evidence(f'after-pass-auth-oauth-providers-available-{locale}-{viewport_id}.png','auth',['signup_available','oauth_providers_available'],locale,viewport_id)
            # Replace public provider status with one generic unavailable envelope.
            page.unroute('**/api/v2/auth/oauth/providers')
            # Intercept the next status request as a fixed server failure.
            page.route('**/api/v2/auth/oauth/providers',lambda route: route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"PROVIDER_UNAVAILABLE","message":"Provider is temporarily unavailable"}}'))
            # Exercise generic status-error rendering in both locales.
            for locale in ('en-US','ru-RU'):
                # Trigger a fresh failed status request through the visible locale rerender.
                page.get_by_test_id('auth-locale-select').select_option(locale)
                # Wait for the governed low-cardinality attached error marker.
                page.get_by_test_id('oauth-providers-status-error').wait_for(state='attached',timeout=5000)
                # Require provider actions absent and the sole live owner to expose localized feedback.
                assert page.get_by_test_id('oauth-google').count()==0 and page.get_by_test_id('oauth-facebook').count()==0 and page.locator('[data-testid="login-gate"] [aria-live]').count()==1 and page.get_by_test_id('oauth-callback-message').inner_text()==read_i18n_json(ROOT/'web'/'i18n'/locale/'shell.json')['auth.oauthStatusError']
                # Capture every governed viewport for the generic failure state.
                for viewport_id,viewport in viewports.items():
                    # Resize to exact governed dimensions before capture.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require no page or Auth-panel horizontal spill.
                    assert page.evaluate("() => { const panel=document.querySelector('[data-testid=\"login-gate\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && panel.scrollWidth<=panel.clientWidth+1; }")
                    # Record generic status-error evidence without raw server or provider detail.
                    game_evidence(f'after-pass-auth-oauth-status-error-{locale}-{viewport_id}.png','auth',['oauth_provider_status_error','oauth_actions_omitted'],locale,viewport_id)
            # Restore the real default-held provider endpoint before downstream login acceptance.
            page.unroute('**/api/v2/auth/oauth/providers')
            # Restore the real default-held enrollment policy alongside provider status.
            page.unroute('**/api/v2/auth/enrollment-policy')
            # Remove the intentionally generated 503 from the broad unexpected-response collector.
            http_errors.clear()
            # Trigger one final real policy-aware refresh through a guaranteed locale change.
            page.get_by_test_id('auth-locale-select').select_option('en-US')
            # Wait for invite-only policy and provider omission before downstream Auth tests continue.
            page.get_by_test_id('signup-invite-only').wait_for(timeout=5000); page.wait_for_function("() => !document.querySelector('[data-testid=oauth-providers-available]')")
            # Restore Russian through a second real change so downstream login coverage receives fresh default policy.
            page.get_by_test_id('auth-locale-select').select_option('ru-RU'); page.get_by_test_id('signup-invite-only').wait_for(timeout=5000)
            # Restore the primary viewport while leaving Russian selected for the existing login flow.
            page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
        # Record policy-aware EN/RU action omission, availability, errors, and visual evidence.
        run_case('BR-OAUTH-001',['OAUTH-001','OAUTH-006','OAUTH-007','OAUTH-010','UX-028','TEST-045','TEST-093','TEST-176'],oauth_disabled_browser)
        # Define social-signup policy, consent, localization, and containment acceptance. (OAUTH-013)
        def oauth_signup_browser():
            # Read all governed Auth viewports from the authoritative visual matrix.
            viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the complete visual acceptance matrix.
            assert set(viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Navigate to the real default-held provider signup surface.
            page.goto(base+'/enroll/signup',wait_until='networkidle'); page.get_by_test_id('signup-enrollment').wait_for(timeout=5000); page.get_by_test_id('oauth-signup-disabled').wait_for(timeout=5000)
            # Exercise default-off provider signup in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch through the visible enrollment locale selector.
                page.get_by_test_id('signup-locale').select_option(locale)
                # Wait for the asynchronous localized signup rerender.
                page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale && document.querySelector('[data-testid=\"oauth-signup-disabled\"]')",arg=locale)
                # Require all three acknowledgement controls and both provider controls to remain visible.
                assert all(page.get_by_test_id(testid).is_visible() for testid in ('signup-terms','signup-privacy','signup-play-token','signup-oauth-google','signup-oauth-facebook'))
                # Require both provider signup controls to remain natively and accessibly disabled.
                assert page.get_by_test_id('signup-oauth-google').is_disabled() and page.get_by_test_id('signup-oauth-facebook').is_disabled() and page.get_by_test_id('signup-oauth-google').get_attribute('aria-disabled')=='true' and page.get_by_test_id('signup-oauth-facebook').get_attribute('aria-disabled')=='true'
                # Capture default-held signup at every governed viewport.
                for viewport_id,viewport in viewports.items():
                    # Resize to the exact named viewport before containment checks.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require no document or enrollment-panel horizontal overflow.
                    assert page.evaluate("() => { const panel=document.querySelector('[data-testid=\"signup-enrollment\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && panel.scrollWidth<=panel.clientWidth+1; }")
                    # Record localized after-pass evidence for policy-held provider signup.
                    game_evidence(f'after-pass-auth-oauth-signup-disabled-{locale}-{viewport_id}.png','auth',['oauth_signup_disabled'],locale,viewport_id)
            # Override only public policy and boolean provider status with synthetic no-network readiness.
            page.route('**/api/v2/auth/enrollment-policy',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"enrollment_mode":"self-signup","signup_enabled":false,"signup_methods":{"email":false,"google":true,"facebook":false},"guest_trials_enabled":false,"invitation_enrollment_enabled":false,"guest_conversion_enabled":true,"passkeys_enabled":false,"canonical_identity":"casino_user_id","shared_auth_origin":"tiltseven_first_party"}}'))
            # Publish one signup-ready provider independently from ordinary sign-in state.
            page.route('**/api/v2/auth/oauth/providers',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"providers":[{"provider":"google","available":true,"signup_available":true},{"provider":"facebook","available":false,"signup_available":false}]}}'))
            # Reload the same-origin signup route through only synthetic responses.
            page.goto(base+'/enroll/signup',wait_until='networkidle'); page.get_by_test_id('oauth-signup-available').wait_for(timeout=5000)
            # Require only the independently enabled provider signup control.
            assert not page.get_by_test_id('signup-oauth-google').is_disabled() and page.get_by_test_id('signup-oauth-facebook').is_disabled()
            # Click before acknowledgement to prove provider navigation cannot start.
            page.get_by_test_id('signup-oauth-google').click()
            # Require localized consent feedback and no provider-start request.
            assert page.get_by_test_id('signup-message').inner_text() and not any('/api/v2/auth/oauth/google/start' in request for request in provider_requests)
            # Capture the exact consent-required state at the primary viewport.
            page.set_viewport_size(viewports['desktop_primary']); game_evidence('after-pass-auth-oauth-signup-consent-required.png','auth',['oauth_signup_available','oauth_signup_consent_required'],'ru-RU','desktop_primary')
            # Load one fixed server-owned successful completion marker without a provider callback.
            page.goto(base+'/enroll/signup?oauth_provider=google&oauth_status=signed_up',wait_until='networkidle'); page.get_by_test_id('oauth-signup-available').wait_for(timeout=5000)
            # Require a localized non-sensitive success acknowledgement and scrubbed query.
            assert page.get_by_test_id('signup-message').inner_text() and 'oauth_provider' not in page.url and 'oauth_status' not in page.url
            # Capture the governed successful completion state.
            game_evidence('after-pass-auth-oauth-signup-success.png','auth',['oauth_signup_success'],'ru-RU','desktop_primary')
            # Restore real public endpoints before downstream authentication cases.
            page.unroute('**/api/v2/auth/enrollment-policy'); page.unroute('**/api/v2/auth/oauth/providers')
            # Return to the real default-held login surface and primary viewport.
            page.goto(base,wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000); page.set_viewport_size({'width':1920,'height':1080})
        # Record provider-specific signup policy, consent, EN/RU, and visual-matrix evidence.
        run_case('BR-OAUTH-SIGNUP-001',['OAUTH-013','AUTH-017','TEST-168'],oauth_signup_browser)
        # Define pending verified-email URL-scrubbing, localization, and containment acceptance. (AUTH-018)
        def verified_email_browser():
            # Read the complete governed Auth viewport matrix.
            viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require every desktop, tablet, and mobile acceptance viewport.
            assert set(viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Enter through a synthetic bearer link without submitting it to any backend.
            page.goto(base+'/enroll/verify?token=synthetic-browser-verification-bearer',wait_until='networkidle')
            # Wait for the dedicated account-free pending surface.
            page.get_by_test_id('email-verification-pending').wait_for(timeout=5000)
            # Require immediate bearer scrubbing from the visible URL and browser history entry.
            assert page.url.rstrip('/').endswith('/enroll/verify') and 'token=' not in page.url
            # Exercise the pending surface in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Switch through the visible governed locale control.
                page.get_by_test_id('email-verification-locale').select_option(locale)
                # Wait for locale state and the replacement pending form to settle.
                page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale && document.querySelector('[data-testid=\"email-verification-pending\"]')",arg=locale)
                # Require verify, resend, cancel, recipient, and login controls to remain visible.
                assert all(page.get_by_test_id(testid).is_visible() for testid in ('email-verification-email','email-verification-submit','email-verification-resend','email-verification-cancel','email-verification-login-link'))
                # Require the arrived module-local bearer to keep verification available after rerender.
                assert not page.get_by_test_id('email-verification-submit').is_disabled()
                # Capture every governed viewport without consuming the synthetic bearer.
                for viewport_id,viewport in viewports.items():
                    # Resize to the exact matrix dimensions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Require both document and pending-panel horizontal containment.
                    assert page.evaluate("() => { const panel=document.querySelector('[data-testid=\"email-verification-pending\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && panel.scrollWidth<=panel.clientWidth+1; }")
                    # Record localized after-pass pending-verification evidence.
                    game_evidence(f'after-pass-auth-email-verification-{locale}-{viewport_id}.png','auth',['email_signup_pending','email_verification_link'],locale,viewport_id)
            # Return to the default login route before downstream browser cases.
            page.goto(base,wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000); page.set_viewport_size({'width':1920,'height':1080})
        # Record bearer scrubbing, bilingual controls, and governed responsive containment.
        run_case('BR-VERIFIED-EMAIL-001',['AUTH-018','USER-010','TEST-171'],verified_email_browser)
        # Define exact geometry acceptance for every primary Auth hit target. (issue #283)
        def auth_touch_target_floor():
            # Read every governed viewport from the authoritative visual matrix.
            touch_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the complete desktop, tablet, and mobile viewport set.
            assert set(touch_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Name each default actionable login control and use the clickable parent row for the checkbox glyph.
            auth_targets=[{'name':'guest','selector':'[data-testid="guest-trial-button"]'},{'name':'guest-details','selector':'[data-testid="guest-disclosure-toggle"]'},{'name':'terms-row','selector':'[data-testid="login-terms-check"]','closest':'.check-row'},{'name':'email','selector':'[data-testid="login-email"]'},{'name':'password','selector':'[data-testid="login-password"]'},{'name':'locale','selector':'[data-testid="auth-locale-select"]'},{'name':'submit','selector':'[data-testid="login-submit"]'},{'name':'reset','selector':'[data-testid="password-reset-entry"]'},{'name':'invite-only','selector':'[data-testid="signup-invite-only"]'}]
            # Exercise the real localized Auth surface in both governed locales.
            for locale in ('en-US','ru-RU'):
                # Switch through the visible locale control so the whole gate rerenders normally.
                page.get_by_test_id('auth-locale-select').select_option(locale)
                # Wait for the active locale and replacement DOM to settle.
                page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale && document.querySelector('[data-testid=\"login-email\"]')",arg=locale)
                # Wait for both independently loaded policy actions before measuring their hit geometry.
                page.get_by_test_id('guest-trial-button').wait_for(timeout=5000); page.get_by_test_id('signup-invite-only').wait_for(timeout=5000)
                # Measure and capture every governed viewport for this locale.
                for viewport_id,viewport in touch_viewports.items():
                    # Apply the exact visual-matrix dimensions before reading hit geometry.
                    page.set_viewport_size(viewport); page.wait_for_timeout(120)
                    # Resolve each semantic target, substituting the permitted enlarged parent when configured.
                    diagnostics=page.evaluate("""specs => specs.map(spec => { let element=document.querySelector(spec.selector); if(spec.closest) element=element?.closest(spec.closest); if(!element) return {name:spec.name,missing:true}; const rect=element.getBoundingClientRect(); const style=getComputedStyle(element); return {name:spec.name,width:rect.width,height:rect.height,display:style.display,visibility:style.visibility}; })""",auth_targets)
                    # Require every named target to exist visibly and meet the two-dimensional 42px hit floor.
                    assert len(diagnostics)==len(auth_targets) and all(not item.get('missing') and item['display']!='none' and item['visibility']!='hidden' and item['width']>=41.5 and item['height']>=41.5 for item in diagnostics),diagnostics
                    # Reject page-level or panel-level horizontal overflow at the accepted geometry.
                    assert page.evaluate("() => { const panel=document.querySelector('[data-testid=\"login-gate\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && panel.scrollWidth<=panel.clientWidth+1; }")
                    # Capture self-describing Auth proof for this locale and viewport.
                    game_evidence(f'after-pass-touch-target-auth-{locale.lower()}-{viewport_id}.png','auth',['login','restricted_preview','touch_target_floor'],locale,viewport_id)
            # Restore Russian and the primary desktop size expected by the existing authentication flow.
            page.set_viewport_size(touch_viewports['desktop_primary']); page.get_by_test_id('auth-locale-select').select_option('ru-RU')
            # Wait for the restored Russian gate before handing off to the login case.
            page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'ru-RU' && document.querySelector('[data-testid=\"login-email\"]')")
        # Execute Auth touch-target acceptance under the adopted governance requirements.
        run_case('BR-TOUCH-TARGET-AUTH-001',['UX-018','UX-028','TEST-087','TEST-176'],auth_touch_target_floor)
        # Define the auth_login_gate function used by this module.
        def auth_login_gate():
            # Verify the login panel is visible before casino routes mount.
            assert page.get_by_test_id('login-gate').is_visible()
            # Verify the premium topbar is hidden while logged out.
            assert not page.get_by_test_id('premium-topbar').is_visible()
            # Verify the required toy-simulator terms checkbox is visible.
            assert page.get_by_test_id('login-terms-check').is_visible()
            # Wait for the default policy-aware guest and invite-only decisions to settle.
            page.get_by_test_id('guest-trial-button').wait_for(timeout=5000); page.get_by_test_id('signup-invite-only').wait_for(timeout=5000)
            # Require one concise legal line, one live status owner, and zero disabled interactive elements.
            assert page.locator('#auth-legal-line').count()==1 and page.locator('[data-testid="login-gate"] [aria-live]').count()==1 and page.locator('[data-testid="login-gate"] :is(button,input,select):disabled').count()==0
            # Fill valid credential shapes so shared terms validation runs before the password API.
            page.get_by_test_id('login-email').fill('terms-check@example.invalid'); page.get_by_test_id('login-password').fill('not-a-real-password')
            # Invoke returning-user sign-in without terms through the visible secondary action.
            page.get_by_test_id('login-submit').click()
            # Require the same localized inline validation and exact checkbox focus as guest entry.
            assert page.get_by_test_id('oauth-callback-message').inner_text()==read_i18n_json(ROOT/'web'/'i18n'/'ru-RU'/'shell.json')['auth.termsRequired'] and page.evaluate("() => document.activeElement?.dataset.testid==='login-terms-check'")
            # Clear test-only credential shapes before the later real backend login flow.
            page.get_by_test_id('login-email').fill(''); page.get_by_test_id('login-password').fill('')
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
            # Constrain the gate to the issue-specific 375-by-812 phone viewport.
            page.set_viewport_size({'width':375,'height':812}); page.wait_for_timeout(150)
            # Read the brand, legal, guest, terms, and returning-user geometry after exact policy settlement.
            phone_fit=page.evaluate("() => ({scrollHeight:document.documentElement.scrollHeight,innerHeight,brand:document.querySelector('.auth-entry-header')?.getBoundingClientRect().bottom||0,legal:document.querySelector('#auth-legal-line')?.getBoundingClientRect().bottom||0,guest:document.querySelector('[data-testid=guest-trial-button]')?.getBoundingClientRect().bottom||0,terms:document.querySelector('[data-testid=login-terms-check]')?.closest('label')?.getBoundingClientRect().bottom||0,signin:document.querySelector('.auth-signin')?.getBoundingClientRect().bottom||0})")
            # Require the complete first decision hierarchy without page scroll or below-fold actions.
            assert phone_fit['scrollHeight']<=phone_fit['innerHeight']+1 and max(phone_fit['brand'],phone_fit['legal'],phone_fit['guest'],phone_fit['terms'],phone_fit['signin'])<=phone_fit['innerHeight']+1,phone_fit
            # Capture issue-specific mobile decision-hierarchy evidence outside the standard viewport sidecar matrix.
            shot('after-pass-auth-decision-ru-RU-mobile-375x812.png')
            # Restore the primary viewport for downstream auth coverage.
            page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(150)
            # Open enumeration-safe public recovery through the visible sign-in affordance. (RESET-004)
            page.get_by_test_id('password-reset-entry').click(); page.get_by_test_id('password-reset-initiate').wait_for(timeout=5000)
            # Require recovery to stay outside authenticated casino chrome and retain bounded responsive geometry.
            assert not page.get_by_test_id('premium-topbar').is_visible() and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
            # Capture the public recovery initiation surface without submitting any mailbox value.
            shot('after-pass-password-reset-initiate.png')
            # Return to the login gate so the existing real-backend authentication flow remains unchanged.
            page.goto(base,wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000); page.get_by_test_id('guest-trial-button').wait_for(timeout=5000); page.set_viewport_size({'width':1920,'height':1080})
        run_case('BR-AUTH-LOGIN-001',['AUTH-001','TERMS-001','AUTH-UI-002','RESET-004','UX-028','TEST-071','TEST-158','TEST-176'],auth_login_gate)
        # Reselect the Russian gate through the visible control when this shard skipped the producing cases.
        if not browser_shard_owns('BR-TOUCH-TARGET-AUTH-001'): page.get_by_test_id('auth-locale-select').select_option('ru-RU')
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
            # Open the personal settings surface through the regular authenticated navigation. (USER-008, USER-009)
            page.get_by_test_id('nav-settings').click(); page.get_by_test_id('my-settings').wait_for(timeout=5000)
            # Require newly introduced accounts to keep personal sound off until explicit opt-in.
            assert not page.get_by_test_id('personal-settings-sound').is_checked() and page.get_by_test_id('my-history').is_visible()
            # Persist the explicit sound-off choice through the real optimistic settings route.
            with page.expect_response(lambda response: response.url.endswith('/api/v2/me/settings') and response.request.method=='PATCH') as settings_response_info:
                # Submit only the visible personal locale and sound fields.
                page.get_by_test_id('personal-settings-save').click()
            # Require the standard settings envelope and a contained personal surface.
            assert settings_response_info.value.json()['ok'] is True and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
            # Capture personal settings/history evidence distinct from the Admin Console.
            shot('after-pass-my-settings-sound-off.png')
            # Return to the lobby so later account-provider acceptance starts from its existing route.
            page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
        run_case('BR-AUTH-SHELL-001',['AUTH-UI-001','TOKEN-UI-001','I18N-003','USER-008','USER-009','TEST-158'],auth_shell)
        # Define provider-free authenticated account-method and callback lifecycle visual acceptance. (OAUTH-010)
        def oauth_runtime_browser():
            # Read all four governed viewports from the authoritative matrix.
            oauth_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the full responsive matrix before generating any evidence.
            assert set(oauth_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Require the account popover to remain fully painted inside the active viewport.
            def assert_oauth_account_containment():
                # Check both document overflow and the popover's physical viewport bounds.
                assert page.evaluate("""() => { const popover=document.querySelector('[data-testid="oauth-account-popover"]'); const bounds=popover.getBoundingClientRect(); return document.documentElement.scrollWidth<=window.innerWidth+1 && popover.scrollWidth<=popover.clientWidth+1 && bounds.left>=13 && bounds.right<=window.innerWidth-13 && bounds.top>=0 && bounds.bottom<=window.innerHeight+1 && bounds.width>=Math.min(300,window.innerWidth-28); }""")
            # Install one boolean-only unlinked/available current-user response without provider network access.
            page.route('**/api/v2/me/oauth/providers',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"providers":[{"provider":"google","linked":false,"available":true},{"provider":"facebook","linked":false,"available":false}]}}'))
            # Exercise current-user unlinked state across both installed locales.
            for locale in ('en-US','ru-RU'):
                # Force a different locale first so the requested locale always triggers shell refresh.
                alternate='ru-RU' if locale=='en-US' else 'en-US'
                # Switch through the visible shell selector to rerender account methods.
                page.get_by_test_id('shell-locale-select').select_option(alternate); page.get_by_test_id('shell-locale-select').select_option(locale)
                # Open the native details account surface when it is currently closed.
                if not page.locator('#account-menu').evaluate("element => element.open"): page.get_by_test_id('account-menu').click()
                # Wait for the fixed Google row to become visible only after its native details owner is open.
                page.get_by_test_id('oauth-link-google').wait_for(timeout=5000)
                # Require explicit confirmation and both provider rows before capture.
                assert page.get_by_test_id('oauth-link-confirm').is_visible() and page.get_by_test_id('oauth-link-google').is_visible() and page.get_by_test_id('oauth-link-facebook').is_visible()
                # Focus the native account summary for keyboard-reachability evidence.
                page.get_by_test_id('account-menu').focus()
                # Capture every governed responsive viewport.
                for viewport_id,viewport in oauth_viewports.items():
                    # Resize to the exact matrix dimensions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Prove the complete account surface remains painted inside this viewport.
                    assert_oauth_account_containment()
                    # Require page and account popover containment with all provider actions readable.
                    assert page.evaluate("() => { const popover=document.querySelector('[data-testid=\"oauth-account-popover\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && popover.scrollWidth<=popover.clientWidth+1 && popover.getBoundingClientRect().width>=Math.min(300,window.innerWidth-28); }")
                    # Record unlinked available/release-held state without identity data.
                    region_evidence(f'after-pass-oauth-account-unlinked-{locale}-{viewport_id}.png','[data-testid="oauth-account-popover"]','oauth_account',['unlinked_available','unlinked_release_held','link_confirmation_required'],locale,viewport_id)
            # Replace the unlinked response with one prior-link state using no provider subject.
            page.unroute('**/api/v2/me/oauth/providers')
            # Install a fixed boolean-only linked response.
            page.route('**/api/v2/me/oauth/providers',lambda route: route.fulfill(status=200,content_type='application/json',body='{"ok":true,"data":{"providers":[{"provider":"google","linked":true,"available":true},{"provider":"facebook","linked":false,"available":false}]}}'))
            # Exercise the linked/unlinked mix in both locales.
            for locale in ('en-US','ru-RU'):
                # Trigger a full account-method rerender through the visible locale control.
                alternate='ru-RU' if locale=='en-US' else 'en-US'
                # Switch away and back so the exact target locale owns the final render.
                page.get_by_test_id('shell-locale-select').select_option(alternate); page.get_by_test_id('shell-locale-select').select_option(locale)
                # Wait until the linked Google row renders an unlink action.
                page.wait_for_function("() => document.querySelector('[data-testid=\"oauth-link-google\"] [data-oauth-account-action=\"unlink\"]')")
                # Ensure the account popover remains open after shell locale rerender.
                if not page.locator('#account-menu').evaluate("element => element.open"): page.get_by_test_id('account-menu').click()
                # Capture every governed viewport for boolean linked state.
                for viewport_id,viewport in oauth_viewports.items():
                    # Resize before geometry and capture.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Prove the complete account surface remains painted inside this viewport.
                    assert_oauth_account_containment()
                    # Require every native action to remain visible and contained.
                    assert page.get_by_test_id('oauth-link-google').is_visible() and page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1")
                    # Record linked state without provider subject, email, or canonical user id.
                    region_evidence(f'after-pass-oauth-account-linked-{locale}-{viewport_id}.png','[data-testid="oauth-account-popover"]','oauth_account',['linked'],locale,viewport_id)
            # Intercept the exact unlink mutation with one fixed failure so error isolation is proven without deleting the mocked link.
            page.route('**/api/v2/me/oauth/google/unlink',lambda route: route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"PROVIDER_UNAVAILABLE","message":"Provider is temporarily unavailable"}}'))
            # Exercise a real confirmed unlink click and its localized generic failure in both locales.
            for locale in ('en-US','ru-RU'):
                # Force a locale-owned account rerender before the unlink attempt.
                alternate='ru-RU' if locale=='en-US' else 'en-US'
                # Switch away and back so the intended locale owns every visible row and error message.
                page.get_by_test_id('shell-locale-select').select_option(alternate); page.get_by_test_id('shell-locale-select').select_option(locale)
                # Reopen the account popover after the shell rerender when necessary.
                if not page.locator('#account-menu').evaluate("element => element.open"): page.get_by_test_id('account-menu').click()
                # Select the exact linked-provider unlink control.
                unlink_button=page.locator('[data-testid="oauth-link-google"] [data-oauth-account-action="unlink"]')
                # Require the linked action to be visible before accepting its browser confirmation.
                unlink_button.wait_for(timeout=5000); page.once('dialog',lambda dialog: dialog.accept()); unlink_button.click()
                # Wait until the provider-neutral localized failure message replaces the empty status outlet.
                page.wait_for_function("() => Boolean(document.getElementById('oauth-account-message')?.textContent.trim())",timeout=5000)
                # Require failure to preserve the linked rows without rendering configuration or identity data.
                assert page.locator('[data-testid="oauth-account-popover"]').get_attribute('data-oauth-state')=='linked' and 'CASINO_' not in page.get_by_test_id('oauth-account-popover').inner_text() and '@' not in page.get_by_test_id('oauth-account-popover').inner_text()
                # Capture the confirmed unlink failure at every governed viewport.
                for viewport_id,viewport in oauth_viewports.items():
                    # Resize before the error-message containment assertion.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Prove the complete account surface remains painted inside this viewport.
                    assert_oauth_account_containment()
                    # Require the complete linked popover and its failure status to remain readable without horizontal spill.
                    assert page.locator('#oauth-account-message').is_visible() and page.evaluate("() => { const popover=document.querySelector('[data-testid=\"oauth-account-popover\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && popover.scrollWidth<=popover.clientWidth+1; }")
                    # Record actual unlink-error evidence rather than relabeling a status-load failure.
                    region_evidence(f'after-pass-oauth-account-unlink-error-{locale}-{viewport_id}.png','[data-testid="oauth-account-popover"]','oauth_account',['unlink_error','linked'],locale,viewport_id)
            # Restore normal mutation routing while retaining the provider-free linked status fixture.
            page.unroute('**/api/v2/me/oauth/google/unlink')
            # Reload through one fixed successful callback marker to prove safe outcome cleanup and refresh persistence.
            page.goto(base+'?oauth_provider=google&oauth_status=linked',wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
            # Open the account surface after the authenticated reload.
            page.get_by_test_id('account-menu').click(); page.get_by_test_id('oauth-callback-message').wait_for(timeout=5000)
            # Require browser history to remove the low-cardinality completion query immediately.
            assert 'oauth_provider=' not in page.url and 'oauth_status=' not in page.url
            # Capture successful callback and refresh persistence across locale and viewport.
            for locale in ('en-US','ru-RU'):
                # Trigger localized callback copy through shell rerender.
                alternate='ru-RU' if locale=='en-US' else 'en-US'
                # Switch away and back to the exact final locale.
                page.get_by_test_id('shell-locale-select').select_option(alternate); page.get_by_test_id('shell-locale-select').select_option(locale)
                # Reopen the native account details after DOM-stable shell refresh when needed.
                if not page.locator('#account-menu').evaluate("element => element.open"): page.get_by_test_id('account-menu').click()
                # Require fixed success copy to remain visible after refresh.
                page.get_by_test_id('oauth-callback-message').wait_for(timeout=5000)
                # Capture all four governed viewports.
                for viewport_id,viewport in oauth_viewports.items():
                    # Resize to the matrix dimensions.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Prove the complete account surface remains painted inside this viewport.
                    assert_oauth_account_containment()
                    # Require the callback acknowledgement and account rows to remain contained.
                    assert page.get_by_test_id('oauth-callback-message').is_visible() and page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1")
                    # Record successful callback and same-session refresh evidence.
                    region_evidence(f'after-pass-oauth-callback-success-{locale}-{viewport_id}.png','[data-testid="oauth-account-popover"]','oauth_account',['callback_success','refresh_persisted','linked'],locale,viewport_id)
            # Reload through one fixed failure marker to prove callback-error localization and history cleanup independently from status loading.
            page.goto(base+'?oauth_provider=google&oauth_status=error',wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
            # Open the account surface after the authenticated error-marker reload.
            page.get_by_test_id('account-menu').click(); page.get_by_test_id('oauth-callback-message').wait_for(timeout=5000)
            # Require browser history to remove the low-cardinality error marker immediately.
            assert 'oauth_provider=' not in page.url and 'oauth_status=' not in page.url
            # Exercise the actual callback-error acknowledgement in both installed locales.
            for locale in ('en-US','ru-RU'):
                # Trigger locale-owned callback-error copy through the shared shell rerender.
                alternate='ru-RU' if locale=='en-US' else 'en-US'
                # Switch away and back to make the evidence locale exact.
                page.get_by_test_id('shell-locale-select').select_option(alternate); page.get_by_test_id('shell-locale-select').select_option(locale)
                # Reopen the native details popover when rerendering closed it.
                if not page.locator('#account-menu').evaluate("element => element.open"): page.get_by_test_id('account-menu').click()
                # Require the fixed callback-error message without provider response details.
                page.get_by_test_id('oauth-callback-message').wait_for(timeout=5000); assert page.get_by_test_id('oauth-callback-message').inner_text().strip()
                # Capture the actual callback failure at every governed viewport.
                for viewport_id,viewport in oauth_viewports.items():
                    # Resize before responsive containment proof.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Prove the complete account surface remains painted inside this viewport.
                    assert_oauth_account_containment()
                    # Require the callback error and account rows to remain visible without page-level overflow.
                    assert page.get_by_test_id('oauth-callback-message').is_visible() and page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1")
                    # Record callback-error evidence separately from provider-status loading failures.
                    region_evidence(f'after-pass-oauth-callback-error-{locale}-{viewport_id}.png','[data-testid="oauth-account-popover"]','oauth_account',['callback_error','linked'],locale,viewport_id)
            # Replace current-user status with one fixed failure to exercise graceful account-control isolation.
            page.unroute('**/api/v2/me/oauth/providers')
            # Install one generic provider-status failure with no raw details.
            page.route('**/api/v2/me/oauth/providers',lambda route: route.fulfill(status=503,content_type='application/json',body='{"ok":false,"error":{"code":"PROVIDER_UNAVAILABLE","message":"Provider is temporarily unavailable"}}'))
            # Exercise generic account status failure in both locales.
            for locale in ('en-US','ru-RU'):
                # Trigger a fresh failed current-user status request by rerendering shell locale.
                alternate='ru-RU' if locale=='en-US' else 'en-US'
                # Switch away and back to the intended locale.
                page.get_by_test_id('shell-locale-select').select_option(alternate); page.get_by_test_id('shell-locale-select').select_option(locale)
                # Open the account popover and wait for the generic localized failure copy.
                if not page.locator('#account-menu').evaluate("element => element.open"): page.get_by_test_id('account-menu').click()
                # Wait until the failed request replaces the loading state.
                page.locator('[data-testid="oauth-account-popover"][data-oauth-state="status-error"]').wait_for(timeout=5000)
                # Require the popover to contain no provider configuration or identifier rows.
                assert 'CASINO_' not in page.get_by_test_id('oauth-account-popover').inner_text() and '@' not in page.get_by_test_id('oauth-account-popover').inner_text()
                # Capture the generic error at every governed viewport.
                for viewport_id,viewport in oauth_viewports.items():
                    # Resize before containment proof.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Prove the complete account surface remains painted inside this viewport.
                    assert_oauth_account_containment()
                    # Require the generic failure card to remain usable and contained.
                    assert page.get_by_test_id('oauth-account-popover').is_visible() and page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1")
                    # Record provider-status loading failure without mislabeling unlink or callback behavior.
                    region_evidence(f'after-pass-oauth-account-status-error-{locale}-{viewport_id}.png','[data-testid="oauth-account-popover"]','oauth_account',['status_error'],locale,viewport_id)
            # Restore the real current-user endpoint and clear the intentionally generated 503 diagnostics.
            page.unroute('**/api/v2/me/oauth/providers'); http_errors.clear()
            # Reload the normal authenticated shell without a callback marker or mocked provider state.
            page.goto(base,wait_until='networkidle'); page.get_by_test_id('lobby').wait_for(timeout=5000)
            # Restore the primary desktop viewport for downstream wallet evidence.
            page.set_viewport_size({'width':1920,'height':1080})
        # Record the complete provider-free OAuth lifecycle and visual matrix.
        run_case('BR-OAUTH-RUNTIME-001',['OAUTH-007','OAUTH-008','OAUTH-009','OAUTH-010','AUTH-007','TEST-093'],oauth_runtime_browser)
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
        # Wait until the wallet reflects the real ledger-backed token addition and clears the submitted amount.
        page.wait_for_function("() => document.querySelector('#balance')?.textContent === '5,250.50' && document.querySelector('#add-token-amount')?.value === ''")
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
        run_case('BR-AUTH-LOCALE-001',['I18N-003','AUTH-UI-001'],lambda: route_before_locale and page.get_by_test_id('lobby').is_visible() and page.locator('#balance').inner_text()=='5,250.50')
        # Logout through the shell control to verify the browser returns to the login gate.
        page.get_by_test_id('logout').click(); page.get_by_test_id('login-gate').wait_for(timeout=5000)
        # Probe the current-user endpoint after visible logout so the browser cannot hide a surviving cookie.
        logout_me_status=page.evaluate("async () => { const response=await fetch('/api/v2/me', {credentials:'include'}); return {status:response.status, ok:(await response.json()).ok}; }")
        # Reload the browser document to prove current-user bootstrapping does not resurrect the old session.
        page.reload(wait_until='networkidle'); page.get_by_test_id('login-gate').wait_for(timeout=5000)
        run_case('BR-AUTH-LOGOUT-001',['AUTH-UI-001','SESSION-006'],lambda: logout_me_status['status']==401 and logout_me_status['ok'] is False and page.get_by_test_id('login-gate').is_visible() and not page.get_by_test_id('premium-topbar').is_visible())
        # Re-login after logout so the existing browser suite can continue authenticated.
        page.get_by_test_id('login-email').fill('demo@example.local'); page.get_by_test_id('login-password').fill('password'); page.get_by_test_id('login-terms-check').check(); page.get_by_test_id('login-submit').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
        # Establish the English oracle explicitly because re-authentication correctly restores a previously saved locale preference.
        page.get_by_test_id('shell-locale-select').select_option('en-US')
        # Wait until the shared runtime and mounted shell both own the English locale before asserting English token copy.
        page.wait_for_function("() => window.CasinoI18n && window.CasinoI18n.getLocaleState().locale === 'en-US'")
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
        run_case('BR-SHELL-001',['UX-007','CORE-006','LEDGER-025','TOKEN-001','TOKEN-002'],premium_shell)
        # Define governed touch-target acceptance for authenticated shell, Slots, and Roulette controls. (issue #283)
        def shell_slots_and_roulette_touch_target_floor():
            # Read the exact responsive dimensions from the visual matrix.
            touch_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Name every shell selector covered by the owner-approved floor.
            shell_selectors=['.nav-item','#shell-locale-select','#logout-btn','#catalog-search','.catalog-category','#wallet-menu-summary']
            # Name the reported Slots wager and autoplay controls plus the primary action.
            slots_selectors=['[data-testid="slots-lines"]','[data-testid="slots-line-bet"]','[data-testid="slots-spin"]','[data-testid="slots-auto-speed"]','[data-testid="slots-auto-rounds"]','[data-testid="slots-auto-start"]','[data-testid="slots-auto-stop"]']
            # Name every remaining high-frequency Roulette utility-control group owned by the reopened issue.
            roulette_selectors=['.roulette-fast-grid button','.roulette-call-grid button','#toggleSpots','#rebet']
            # Exercise both installed player-facing locales on the real authenticated route.
            for locale in ('en-US','ru-RU'):
                # Switch the mounted shell through its visible locale selector.
                page.get_by_test_id('shell-locale-select').select_option(locale)
                # Wait for the lobby and locale runtime to finish rerendering.
                page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale && document.querySelector('[data-testid=\"lobby\"]')",arg=locale)
                # Measure every required viewport in this locale.
                for viewport_id,viewport in touch_viewports.items():
                    # Apply the exact governed viewport before auditing shell controls.
                    page.set_viewport_size(viewport); page.wait_for_timeout(120)
                    # Measure every rendered match while preserving the selector that owns it.
                    shell_diagnostics=page.evaluate("""selectors => { const records=[]; for(const selector of selectors){ for(const element of document.querySelectorAll(selector)){ const rect=element.getBoundingClientRect(); const style=getComputedStyle(element); if(style.display==='none'||style.visibility==='hidden'||(rect.width===0&&rect.height===0)) continue; records.push({selector,testid:element.dataset.testid||'',width:rect.width,height:rect.height}); } } return records; }""",shell_selectors)
                    # Require every selector to resolve and every live target to meet the 42px width and height floor.
                    assert {item['selector'] for item in shell_diagnostics}==set(shell_selectors) and all(item['width']>=41.5 and item['height']>=41.5 for item in shell_diagnostics),shell_diagnostics
                    # Reject shell page-level horizontal overflow before collecting after-pass proof.
                    assert page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1")
                    # Capture authenticated Lobby proof for the exact locale and viewport.
                    game_evidence(f'after-pass-touch-target-shell-{locale.lower()}-{viewport_id}.png','shell_lobby',['authenticated','touch_target_floor'],locale,viewport_id)
                    # Open the affected Slots surface through the real bounded navigation.
                    page.get_by_test_id('nav-slots').click(); page.get_by_test_id('slot-grid').wait_for(timeout=5000)
                    # Measure every named Slots control, including disabled Stop, by its real layout box.
                    slots_diagnostics=page.evaluate("""selectors => selectors.map(selector => { const element=document.querySelector(selector); if(!element) return {selector,missing:true}; const rect=element.getBoundingClientRect(); const style=getComputedStyle(element); return {selector,width:rect.width,height:rect.height,display:style.display,visibility:style.visibility}; })""",slots_selectors)
                    # Require all Slots wager, autoplay, and action controls to meet the adopted floor.
                    assert len(slots_diagnostics)==len(slots_selectors) and all(not item.get('missing') and item['display']!='none' and item['visibility']!='hidden' and item['width']>=41.5 and item['height']>=41.5 for item in slots_diagnostics),slots_diagnostics
                    # Reject game-level horizontal overflow at the current governed dimensions.
                    assert page.evaluate("() => document.documentElement.scrollWidth<=window.innerWidth+1")
                    # Capture the affected game surface in its idle touch-target state.
                    game_evidence(f'after-pass-touch-target-slots-{locale.lower()}-{viewport_id}.png','slots',['idle','touch_target_floor'],locale,viewport_id)
                    # Open Roulette through the real navigation before measuring its high-frequency controls.
                    page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-premium').wait_for(timeout=5000)
                    # Reveal the player-operated racetrack controls through their semantic disclosure.
                    page.get_by_test_id('roulette-racetrack-disclosure').locator('summary').click()
                    # Measure every visible fast-bet, call-bet, toggle, and rebet target in its real rendered layout.
                    roulette_diagnostics=page.evaluate("""selectors => { const records=[]; for(const selector of selectors){ for(const element of document.querySelectorAll(selector)){ const rect=element.getBoundingClientRect(); const style=getComputedStyle(element); if(style.display==='none'||style.visibility==='hidden'||(rect.width===0&&rect.height===0)) continue; records.push({selector,width:rect.width,height:rect.height}); } } return records; }""",roulette_selectors)
                    # Require every Roulette selector and each of its live controls to meet the adopted two-dimensional floor.
                    assert {item['selector'] for item in roulette_diagnostics}==set(roulette_selectors) and all(item['width']>=41.5 and item['height']>=41.5 for item in roulette_diagnostics),roulette_diagnostics
                    # Move focus between real fast-bet controls with a keyboard event so focus-visible styling is exercised.
                    page.locator('.roulette-fast-grid button').first.focus(); page.keyboard.press('Tab')
                    # Verify keyboard focus lands on another high-frequency control with a visible production indicator.
                    roulette_focus=page.evaluate("() => { const element=document.activeElement; const style=getComputedStyle(element); return {inside:Boolean(element?.matches('.roulette-fast-grid button')),visible:element?.matches(':focus-visible')===true,outline:style.outlineStyle,width:parseFloat(style.outlineWidth)||0}; }")
                    # Reject missing keyboard focus or an invisible focus ring on the repaired Roulette control set.
                    assert roulette_focus['inside'] and roulette_focus['visible'] and roulette_focus['outline']!='none' and roulette_focus['width']>=1,roulette_focus
                    # Reject document and control-rail horizontal clipping at each governed responsive size.
                    assert page.evaluate("() => { const rail=document.querySelector('[data-testid=\"roulette-control-rail\"]'); return document.documentElement.scrollWidth<=window.innerWidth+1 && rail.scrollWidth<=rail.clientWidth+1; }")
                    # Capture exact-locale and exact-viewport proof for the Roulette touch-target matrix state.
                    game_evidence(f'after-pass-touch-target-roulette-{locale.lower()}-{viewport_id}.png','roulette',['betting','keyboard_focus','touch_target_floor'],locale,viewport_id)
                    # Return to the stable Lobby surface before the next viewport or locale.
                    page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
            # Restore the default locale and primary viewport for downstream shell acceptance.
            page.set_viewport_size(touch_viewports['desktop_primary']); page.get_by_test_id('shell-locale-select').select_option('en-US')
            # Wait for the restored English Lobby before the next case begins.
            page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US' && document.querySelector('[data-testid=\"lobby\"]')")
        # Execute authenticated shell and affected-game touch-target acceptance.
        run_case('BR-TOUCH-TARGET-001',['UX-018','UX-025','TEST-087'],shell_slots_and_roulette_touch_target_floor)
        # Prove the player-facing brand block carries no internal version or release-stage metadata in either locale. (issue #321)
        def shell_brand_copy():
            # Enumerate internal metadata tokens that must never appear in the player brand block.
            forbidden=re.compile(r'v\d|\bbuild\b|\bcommit\b|\bdebug\b|\benvironment\b|\bstaging\b|validation release|релиз|сборк|проверочн|отлад',re.IGNORECASE)
            # Enumerate all required visual-matrix viewport dimensions from their single governed source.
            brand_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Retain each locale/viewport header height so locale switching cannot silently shift the game stage.
            header_heights={}
            # Require the document title to present the exact approved product name without metadata.
            assert page.title()=='TiltSeven' and not forbidden.search(page.title())
            # Read the runtime-applied brand identity, theme metadata, and canonical custom properties from the tested page.
            brand_runtime=page.evaluate("""() => { const root=document.documentElement; const style=getComputedStyle(root); return { id:root.dataset.brand||'', mark:document.querySelector('.brand-mark')?.textContent?.trim()||'', theme:document.querySelector('meta[name="theme-color"]')?.content||'', brand:style.getPropertyValue('--brand').trim(), accent:style.getPropertyValue('--accent').trim(), background:style.getPropertyValue('--bg').trim() }; }""")
            # Require one coherent TiltSeven/Neon Pit runtime instead of accepting only changed static copy.
            assert brand_runtime=={'id':'tiltseven','mark':'7','theme':'#0a0712','brand':'#ff3b6b','accent':'#22e0c3','background':'#0a0712'},brand_runtime
            # Check the localized authenticated brand block in both installed locales.
            for brand_locale in ('en-US','ru-RU'):
                # Switch the shell locale through the visible control and wait for the runtime to settle.
                page.get_by_test_id('shell-locale-select').select_option(brand_locale); page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale",arg=brand_locale)
                # Read the exact canonical subtitle for this locale from the paired resource file.
                expected_subtitle=read_i18n_json(ROOT/'web'/'i18n'/brand_locale/'shell.json')['brand.subtitle']
                # Wait for the asynchronous locale rerender to publish the exact canonical subtitle, which also proves resource-key-free equality.
                page.wait_for_function("expected => document.querySelector('#shell-brand-subtitle')?.textContent.trim() === expected", arg=expected_subtitle, timeout=5000)
                # Read the settled rendered player-facing brand subtitle for the metadata checks.
                rendered_subtitle=page.locator('#shell-brand-subtitle').inner_text().strip()
                # Require the approved product name to remain exact and resource-key-free.
                assert page.locator('#shell-brand-title').inner_text().strip()=='TiltSeven'
                # Require the subtitle to keep the play-token safety cue while carrying no version metadata.
                assert not forbidden.search(rendered_subtitle), rendered_subtitle
                # Require the play-token cue to remain present in the locale's own words.
                assert ('token' in rendered_subtitle.lower()) or ('токен' in rendered_subtitle.lower()), rendered_subtitle
                # Require the separately approved diagnostics rail to retain a concrete release version for #287 provenance.
                assert re.fullmatch(r'v\d+\.\d+\.\d+(?:\.\d+)?',page.locator('#status-version').inner_text().strip())
                # Prove the lobby header remains readable, contained, and unclipped at every governed viewport.
                for viewport_id,viewport in brand_viewports.items():
                    # Resize to the exact matrix viewport and let responsive layout settle before measuring.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Audit the complete brand lockup against its topbar and viewport bounds.
                    brand_geometry=page.evaluate("""() => { const topbar=document.querySelector('[data-testid=\"premium-topbar\"]'); const lockup=document.querySelector('.brand-lockup'); const title=document.querySelector('#shell-brand-title'); const subtitle=document.querySelector('#shell-brand-subtitle'); const topbarBox=topbar.getBoundingClientRect(); const lockupBox=lockup.getBoundingClientRect(); return { topbarHeight:topbarBox.height, contained:lockupBox.left >= topbarBox.left - 1 && lockupBox.right <= topbarBox.right + 1 && lockupBox.top >= topbarBox.top - 1 && lockupBox.bottom <= topbarBox.bottom + 1, viewportContained:lockupBox.left >= -1 && lockupBox.right <= window.innerWidth + 1, titleUnclipped:title.scrollWidth <= title.clientWidth + 1 && title.scrollHeight <= title.clientHeight + 1, subtitleUnclipped:subtitle.scrollWidth <= subtitle.clientWidth + 1 && subtitle.scrollHeight <= subtitle.clientHeight + 1, pageNoOverflow:document.documentElement.scrollWidth <= window.innerWidth + 1 }; }""")
                    # Require every geometry and overflow invariant to pass before evidence can be accepted.
                    assert brand_geometry['contained'] and brand_geometry['viewportContained'] and brand_geometry['titleUnclipped'] and brand_geometry['subtitleUnclipped'] and brand_geometry['pageNoOverflow'],brand_geometry
                    # Record the topbar height for the later cross-locale stability comparison.
                    header_heights[(brand_locale,viewport_id)]=brand_geometry['topbarHeight']
                    # Capture exact-head authenticated lobby evidence with a self-describing sidecar.
                    game_evidence(f'after-pass-shell-brand-authenticated-{brand_locale.lower()}-{viewport_id}.png','shell_lobby',['authenticated','tiltseven_neon_pit'],brand_locale,viewport_id)
                # Open one representative affected game so shared-shell evidence is not limited to the lobby.
                page.get_by_test_id('nav-roulette').click(); page.get_by_test_id('roulette-premium').wait_for(timeout=5000)
                # Capture the same authenticated header across the representative game at all governed sizes.
                for viewport_id,viewport in brand_viewports.items():
                    # Resize to the exact governed viewport before the shared-shell overflow check.
                    page.set_viewport_size(viewport); page.wait_for_timeout(100)
                    # Reject page-level horizontal overflow and require the shared brand lockup to remain visible above Roulette.
                    assert page.locator('.brand-lockup').is_visible() and page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Record one affected game surface alongside the shared lobby acceptance evidence.
                    game_evidence(f'after-pass-roulette-brand-{brand_locale.lower()}-{viewport_id}.png','roulette',['betting','tiltseven_neon_pit'],brand_locale,viewport_id)
                # Return to the lobby before switching locale so the next evidence set starts from the canonical shell route.
                page.get_by_test_id('nav-lobby').click(); page.get_by_test_id('lobby').wait_for(timeout=5000)
            # Compare matching viewport heights so EN/RU switching cannot move the game stage.
            for viewport_id in brand_viewports:
                # Allow only sub-pixel rounding while rejecting a locale-dependent topbar height change.
                assert abs(header_heights[('en-US',viewport_id)]-header_heights[('ru-RU',viewport_id)]) <= 1,(viewport_id,header_heights)
            # Restore the English locale for downstream shell coverage.
            page.get_by_test_id('shell-locale-select').select_option('en-US'); page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US'")
            # Restore the primary desktop viewport for downstream shell interactions.
            page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(100)
        # Execute the version-free brand copy regression.
        run_case('BR-SHELL-BRAND-001',['UX-014','TEST-079'],shell_brand_copy)
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
            # Exercise the production committed-wager renderer against the authenticated browser shell.
            timing=page.evaluate("""async () => { const mod=await import('/core/ui.js'); const player=window.CasinoCurrentUser.player; const before=Number(player.token_balance); const accepted=mod.renderCommittedWagerBalance({player_id:player.player_id,amount:-1,balance_after:before-1}); const rendered=Number(String(document.querySelector('#balance')?.textContent||'').replace(/[^0-9.-]/g,'')); const foreign=mod.renderCommittedWagerBalance({player_id:'foreign',amount:-1,balance_after:0}); await mod.refreshBalance(); return {accepted,rendered,expected:before-1,foreign}; }""")
            # Require exact intermediate rendering, foreign-event refusal, and authoritative refresh recovery.
            assert timing['accepted'] is True and timing['rendered']==timing['expected'] and timing['foreign'] is False,timing
        run_case('BR-TOKEN-WALLET-001',['TOKEN-001','TOKEN-002','LEDGER-025','LEDGER-031','TEST-151'],token_wallet)
        # Define the premium_lobby function used by this module.
        def premium_lobby():
            # Verify the lobby renders one premium card for every current game.
            assert page.locator('[data-testid^="card-"]').count()==len(casino_config.GAMES)
            # Verify the status/trust rail from the approved lobby is visible.
            assert page.get_by_test_id('lobby-trust-rail').is_visible()
            # Verify the premium lobby headline renders in the first route view.
            assert page.get_by_text('The Neon Pit').is_visible()
            # Verify the Roulette card still exposes its route action.
            assert page.get_by_test_id('open-roulette').is_visible()
            # Verify the catalog advertises one authoritative game count with no contradictory roadmap target. (issue #235)
            assert page.get_by_test_id('catalog-capacity').inner_text()==f'{len(casino_config.GAMES)} available'
            # Read the exact state payload used by the shell presence rail. (CORE-016, issue #570)
            presence_state=page.evaluate("async () => (await (await fetch('/api/v1/casino/state')).json()).data")
            # Require the server-owned aggregate while privacy-filtered player rows remain an independent payload concern.
            assert isinstance(presence_state['online_player_count'],int) and presence_state['online_player_count']>=1,presence_state
            # Require the persistent status rail to publish the aggregate rather than stored player count.
            assert page.locator('#status-players').inner_text()==f"{presence_state['online_player_count']} online"
            # Read every governed viewport from the executable visual matrix for wallet evidence. (UX-023)
            celebration_viewports={entry['id']:{'width':entry['width'],'height':entry['height']} for entry in visual_matrix['viewports']}
            # Require the complete desktop, compact, tablet, and mobile viewport contract.
            assert set(celebration_viewports)=={'desktop_primary','desktop_compact','tablet','mobile'}
            # Resolve one numeric wallet value from the exact shared two-decimal display.
            def rendered_wallet_amount():
                # Parse grouping separators without changing the rendered authoritative text.
                return page.evaluate("() => Number(String(document.querySelector('#balance')?.textContent || '').replace(/[^0-9.-]/g, ''))")
            # Execute one real current-user credit through the visible wallet and prove its effect branch.
            def capture_wallet_gain(locale,viewport_id,amount,state,reduced):
                # Capture the exact authoritative value before the server-owned credit.
                before=rendered_wallet_amount()
                # Apply the real media preference before triggering the controller branch.
                page.emulate_media(reduced_motion='reduce' if reduced else 'no-preference')
                # Open the registered-user wallet menu when the prior successful action closed it.
                if page.locator('.wallet-menu').get_attribute('open') is None: page.locator('#wallet-menu-summary').click()
                # Fill the deterministic ordinary or large gain amount.
                page.locator('#add-token-amount').fill(str(amount))
                # Observe the exact current-user mutation while activating the visible action.
                with page.expect_response(lambda response: response.url.endswith('/api/v2/me/tokens/add') and response.request.method=='POST'):
                    # Submit the ledger-backed fake-token credit through the shared shell.
                    page.get_by_test_id('add-tokens').click()
                # Calculate the exact authoritative display expected from that server response.
                expected=round(before+amount,2)
                # Wait until both the private current-user cache and visible wallet publish the same value.
                page.wait_for_function("expected => { const session=window.CasinoCurrentUser||{}; const player=session.player||{}; const value=Number(player.token_balance ?? player.tokens ?? session.token_balance ?? session.tokens?.balance ?? 0); const rendered=Number(String(document.querySelector('#balance')?.textContent||'').replace(/[^0-9.-]/g,'')); return value===expected && rendered===expected; }",arg=expected,timeout=5000)
                # Branch between visible normal motion and intentionally animation-free reduced motion.
                if reduced:
                    # Require the comfort path to allocate no chip, coin layer, marker, or animation class.
                    assert page.evaluate("() => { const wallet=document.querySelector('.wallet-pill'); return !wallet?.hasAttribute('data-wallet-celebration') && !wallet?.classList.contains('wallet-celebration-gain') && !wallet?.classList.contains('wallet-celebration-big') && !document.querySelector('.wallet-gain') && !document.querySelector('.wallet-coin-layer'); }")
                else:
                    # Wait for the exact ordinary or large-gain marker before taking live-motion evidence.
                    page.wait_for_function("state => document.querySelector('.wallet-pill')?.getAttribute('data-wallet-celebration') === state",arg='big-gain' if state=='wallet_big_win' else 'gain',timeout=3000)
                    # Require one gain chip and the magnitude-appropriate bounded coin layer.
                    transient=page.evaluate("() => ({ chips:document.querySelectorAll('.wallet-gain').length, layers:document.querySelectorAll('.wallet-coin-layer').length, coins:document.querySelectorAll('.wallet-coin').length })")
                    # Reject missing, duplicate, or unbounded normal-motion transient presentation.
                    assert transient==({'chips':1,'layers':1,'coins':12} if state=='wallet_big_win' else {'chips':1,'layers':0,'coins':0}),transient
                # Name reduced-motion evidence separately while retaining the exact magnitude state.
                evidence_states=[f'{state}_reduced_motion' if reduced else state]
                # Record one source-bound locale, viewport, magnitude, and motion artifact.
                wallet_evidence(f"after-pass-wallet-celebration-{locale.lower()}-{viewport_id}-{'reduced' if reduced else 'normal'}-{'big' if state=='wallet_big_win' else 'ordinary'}.png",evidence_states,locale,viewport_id)
                # Wait for normal-motion lifecycle completion, while reduced motion is already clean.
                page.wait_for_function("() => { const wallet=document.querySelector('.wallet-pill'); return !wallet?.hasAttribute('data-wallet-celebration') && !document.querySelector('.wallet-gain') && !document.querySelector('.wallet-coin-layer'); }",timeout=4000)
                # Require the exact authoritative value to survive cleanup without a stale rewrite.
                assert rendered_wallet_amount()==expected
            # Exercise both installed locales through the visible shell control.
            for celebration_locale in ('en-US','ru-RU'):
                # Select the exact locale before its complete viewport and motion matrix.
                page.get_by_test_id('shell-locale-select').select_option(celebration_locale)
                # Wait for locale state and lobby remount before opening wallet controls.
                page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale === locale && document.querySelector('[data-testid=\"lobby\"]')",arg=celebration_locale,timeout=5000)
                # Exercise every governed viewport without substituting primary-only evidence.
                for celebration_viewport_id,celebration_viewport in celebration_viewports.items():
                    # Resize to the exact visual-matrix dimensions before each wallet branch.
                    page.set_viewport_size(celebration_viewport); page.wait_for_timeout(80)
                    # Require the persistent wallet and amount to remain visible and horizontally contained.
                    assert page.get_by_test_id('premium-wallet').is_visible() and page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    # Exercise normal and reduced motion independently at this locale and viewport.
                    for celebration_reduced in (False,True):
                        # Capture an ordinary real gain under this exact matrix cell.
                        capture_wallet_gain(celebration_locale,celebration_viewport_id,25,'wallet_gain',celebration_reduced)
                        # Capture a threshold-level large gain under this exact matrix cell.
                        capture_wallet_gain(celebration_locale,celebration_viewport_id,250,'wallet_big_win',celebration_reduced)
            # Restore normal motion, English, and the primary desktop for downstream browser cases.
            page.emulate_media(reduced_motion='no-preference'); page.set_viewport_size(celebration_viewports['desktop_primary']); page.get_by_test_id('shell-locale-select').select_option('en-US')
            # Wait for the canonical English lobby after the matrix completes.
            page.wait_for_function("() => window.CasinoI18n?.getLocaleState().locale === 'en-US' && document.querySelector('[data-testid=\"lobby\"]')")
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
                # Resolve the exact resource-owned trust titles and details for the three previously hardcoded tiles.
                expected_trust=[(lobby_shell_copy[loc]['lobby.trust.localTitle'],lobby_shell_copy[loc]['lobby.trust.localDetail']),(lobby_shell_copy[loc]['lobby.trust.autoplayTitle'],lobby_shell_copy[loc]['lobby.trust.autoplayDetail']),(lobby_shell_copy[loc]['lobby.trust.ledgerTitle'],lobby_shell_copy[loc]['lobby.trust.ledgerDetail'].replace('{count}',str(len(casino_config.GAMES))))]
                # Read the local, autoplay, and ledger tiles while intentionally skipping the dynamic live-presence tile.
                trust_tiles=[page.locator('.trust-item').nth(index) for index in (0,2,3)]
                # Require every named trust tile to match its active-locale resource values exactly.
                assert [(tile.locator('strong').inner_text().strip(),tile.locator('strong + span').inner_text().strip()) for tile in trust_tiles]==expected_trust
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
        run_case('BR-LOBBY-001',['CORE-005','CORE-006','CORE-016','UX-008','UX-023','I18N-004','I18N-014','TEST-069','TEST-187','UX-012','TEST-072'],premium_lobby)
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
            # Build exact expected Russian card copy from the same installed descriptors used by production startup.
            expected_cards={game['id']:game['translations']['ru-RU'] for game in casino_config.GAMES}
            # Require every installed game card to render its exact localized label, kicker, description, and ordered tags.
            for game_id,expected in expected_cards.items():
                # Read only player-facing copy while excluding the Latin art symbol and localized Play action.
                actual=page.evaluate("""gameId => { const card=document.querySelector(`[data-testid=\"card-${gameId}\"]`); const heading=card.querySelector('.game-heading').cloneNode(true); heading.querySelector('.game-symbol')?.remove(); return {label:heading.textContent.trim(),kicker:card.querySelector('.game-kicker').textContent.replace(/^★\\s*/, '').trim(),description:card.querySelector('.game-card-content > p').textContent.trim(),tags:[...card.querySelectorAll('.tag')].map(node=>node.textContent.trim())}; }""",game_id)
                # Compare the complete card projection so runtime fallback to any English descriptor field fails.
                assert actual=={field:expected[field] for field in ('label','kicker','description','tags')},{'game':game_id,'expected':expected,'actual':actual}
                # Reject Latin leakage in localized copy; the current Russian catalog needs no proper-name exception.
                assert not re.search(r'[A-Za-z]', ' '.join([actual['label'],actual['kicker'],actual['description'],*actual['tags']])),{'game':game_id,'actual':actual}
            # Capture the complete localized catalog at every governed viewport before applying filters.
            for viewport_id,width,height in (('desktop_primary',1920,1080),('desktop_compact',1440,900),('tablet',1024,900),('mobile',390,844)):
                # Resize to the exact visual-matrix viewport and let responsive card layout settle.
                page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(80)
                # Require the complete Russian gallery to remain horizontally contained.
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                # Record source-bound evidence for the named localization-complete state.
                game_evidence(f'after-pass-shell-lobby-russian-catalog-complete-{viewport_id}.png','shell_lobby',['russian_catalog_complete'],'ru-RU',viewport_id)
            # Restore the primary desktop viewport before exercising catalog filters.
            page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(80)
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
        run_case('BR-CATALOG-I18N-RU-001',['UX-010','I18N-001','I18N-012','UX-012','TEST-072','TEST-178'],catalog_ru_acceptance)
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
                reachability=page.evaluate("""() => { const region=document.querySelector('[data-testid="lobby-scroll-region"]'); const cards=[...document.querySelectorAll('[data-testid^="card-"]')]; const plays=[...document.querySelectorAll('[data-testid^="open-"]')]; if (!cards.length || !plays.length) return {reachable:false}; const card=cards.at(-1); const play=plays.at(-1); const activeCategory=document.querySelector('[data-catalog-category][aria-pressed="true"]'); const regionRect=region.getBoundingClientRect(); const cardRect=card.getBoundingClientRect(); const playRect=play.getBoundingClientRect(); return {reachable:cardRect.top>=regionRect.top-1 && cardRect.bottom<=regionRect.bottom+1 && playRect.top>=regionRect.top-1 && playRect.bottom<=regionRect.bottom+1,category:activeCategory?.dataset.catalogCategory||'',cardTestId:card.dataset.testid||'',cardTop:cardRect.top,cardBottom:cardRect.bottom,cardHeight:cardRect.height,playTop:playRect.top,playBottom:playRect.bottom,regionTop:regionRect.top,regionBottom:regionRect.bottom,regionHeight:regionRect.height}; }""")
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
                    # Fail closed unless the fixed status footer and every expected visible localized segment are contained and pairwise disjoint. (issue #285)
                    footer_geometry=page.evaluate("""() => { const bar=document.querySelector('[data-testid="shell-status"]'); if (!bar) return {ok:false,reason:'missing_status_bar'}; const barRect=bar.getBoundingClientRect(); const items=[...bar.querySelectorAll('.status-item')].map((item,index) => { const rect=item.getBoundingClientRect(); return {index,left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom,width:rect.width,height:rect.height}; }).filter(item => item.width>0 && item.height>0); const spill=items.some(item => item.left < barRect.left-1 || item.right > barRect.right+1 || item.top < barRect.top-1 || item.bottom > barRect.bottom+1); const collisions=[]; for (let a=0;a<items.length;a+=1) for (let b=a+1;b<items.length;b+=1) { const first=items[a],second=items[b]; if (first.left < second.right-1 && second.left < first.right-1 && first.top < second.bottom-1 && second.top < first.bottom-1) collisions.push([first.index,second.index]); } return {ok:barRect.width>0 && barRect.height>0 && items.length>=2 && !spill && collisions.length===0,bar:{width:barRect.width,height:barRect.height},visibleItems:items,spill,collisions}; }""")
                    # Surface exact geometry diagnostics when localized copy spills or visible status segments collide.
                    assert footer_geometry['ok'],footer_geometry
                    # Capture named bounded footer evidence whose sidecar preserves the passing geometry for this exact locale and viewport.
                    footer_evidence(f'after-pass-shell-status-footer-{locale.lower()}-{viewport_id}.png',['authenticated','status_footer_contained','geometry_verified'],locale,viewport_id,footer_geometry)
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
                    # Clear and dispatch the search input in one browser task so its synchronous rerender cannot detach Playwright's fill target mid-action. (issue #637)
                    page.get_by_test_id('catalog-search').evaluate("(input) => { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }")
                    # Wait for the cleared query to own a non-empty catalog before changing its category. (issue #637)
                    page.wait_for_function("""() => document.querySelector('[data-testid="catalog-search"]')?.value === '' && document.querySelectorAll('[data-testid^="card-"]').length > 0""",timeout=5000)
                    # Select the table category as a visible representative after every category passed behavior checks.
                    page.locator('[data-catalog-category="table"]').click()
                    # Wait for the selected category and its cards to share one completed rerender. (issue #637)
                    page.wait_for_function("""() => document.querySelector('[data-catalog-category="table"]')?.getAttribute('aria-pressed') === 'true' && document.querySelectorAll('[data-testid^="card-"]').length > 0""",timeout=5000)
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
        run_case('BR-LOBBY-RESP-001',['CORE-015','UX-009','UX-012','UX-013','TEST-072','TEST-076','UX-016','TEST-085'],responsive_lobby)
    # Preserve exact case accounting without replaying shard-zero browser state.
    else:
        # Advance the complete contiguous auth/lobby affinity range.
        skip_browser_affinity('auth_lobby')
