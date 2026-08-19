# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own the complete auth-backend and PWA Browser affinity family."""

# Serialize evidence metadata and bounded timeout diagnostics exactly as the historical runner did.
import json
# Read the exact CI head identity without changing the caller's browser environment.
import os
# Normalize bounded Playwright diagnostics without exposing uncontrolled whitespace.
import re
# Resolve source provenance for governed Browser evidence sidecars.
import subprocess
# Issue one credential-free public-shell request outside authenticated Browser cookies.
import urllib.request

# Import the sole environment-scalable Playwright wait budget. (TEST-053)
from tests.browser_timing import WAIT_MS


# Execute or skip the complete producer/consumer group without splitting its shard ownership.
def run_cases(run_case, browser_shard_owns_group, skip_browser_affinity, browser, base, packaged_version, screenshots, ROOT, DEFAULT_AUTH_EMAIL, DEFAULT_AUTH_PASSWORD, PlaywrightTimeoutError):
    """Run all three auth-backend/PWA cases as one affinity-owned unit."""
    # Execute the real-login and PWA producer/consumer body only on its declared owner.
    if browser_shard_owns_group('auth_backend_pwa'):
        # Open an isolated browser page so the visible login form must establish its own backend session.
        real_login_page=browser.new_page(viewport={'width':1920,'height':1080})
        # Retain only sanitized service-worker install diagnostics emitted by the narrowed PWA worker.
        pwa_worker_diagnostics=[]
        # Observe console output before first navigation so an early install rejection cannot escape the acceptance record.
        real_login_page.context.on('console',lambda message: pwa_worker_diagnostics.append(message.text) if message.text.startswith('PWA_INSTALL_FAILURE ') else None)
        # Start protected login verification so the isolated page is always closed before the broad suite.
        try:
            # Navigate without a seeded cookie so the real backend returns the login gate.
            real_login_page.goto(base, wait_until='networkidle'); real_login_page.get_by_test_id('login-gate').wait_for(timeout=WAIT_MS)
            # Observe the actual backend login response while submitting browser-visible credentials.
            with real_login_page.expect_response(lambda response: response.url.endswith('/api/v2/auth/login') and response.request.method == 'POST') as login_response_info:
                # Fill the bootstrap email and password through the same controls used by a local player.
                real_login_page.get_by_test_id('login-email').fill(DEFAULT_AUTH_EMAIL); real_login_page.get_by_test_id('login-password').fill(DEFAULT_AUTH_PASSWORD); real_login_page.get_by_test_id('login-terms-check').check(); real_login_page.get_by_test_id('login-submit').click()
            # Store the real response payload so the test proves the backend accepted the form request.
            real_login_response=login_response_info.value.json()
            # Wait for the authenticated shell that can only mount after the backend session cookie is accepted.
            real_login_page.get_by_test_id('lobby').wait_for(timeout=WAIT_MS)
            # Record the focused real-backend browser login regression coverage.
            run_case('BR-AUTH-BACKEND-001',['AUTH-001','AUTH-002','SESSION-001','OAUTH-006','TEST-045'],lambda: real_login_response['ok'] is True and real_login_response['data']['user']['email']==DEFAULT_AUTH_EMAIL and real_login_page.get_by_test_id('lobby').is_visible())
            # Prove the narrowed installable and offline-safe PWA foundation without native-install claims. (PWA-001, PWA-002, TEST-095)
            def pwa_installable_shell():
                # Build the exact credential-free static-shell request used by the service worker.
                public_shell_request=urllib.request.Request(base+'/index.html',headers={'X-Casino-Public-Shell':'1'})
                # Read the public response headers without sharing authenticated browser cookies.
                with urllib.request.urlopen(public_shell_request,timeout=12) as public_shell_response:
                    # Require valid HTML while proving this public cache-fill response cannot bootstrap a CSRF cookie.
                    assert public_shell_response.status==200 and public_shell_response.headers.get_content_type()=='text/html' and not public_shell_response.headers.get_all('Set-Cookie'),dict(public_shell_response.headers.items())
                # Exercise the actual authenticated application page so worker, cache, session, and route storage share one production-shaped context.
                pwa_page=real_login_page
                # Define every governed viewport for exact visual-matrix evidence.
                pwa_viewports={'desktop_primary':{'width':1920,'height':1080},'desktop_compact':{'width':1440,'height':900},'tablet':{'width':1024,'height':900},'mobile':{'width':390,'height':844}}
                # Map visual-matrix state IDs to the controller's bounded display protocol.
                pwa_states={'cold_start':'cold-start','warm_start':'warm-start','offline':'offline','reconnecting':'reconnecting','update_available':'update','update_failed':'update-failed','stale_client':'stale-client','expired_session':'expired-session','route_restored':'route-restored'}
                # Read exact source identity once for every PWA evidence sidecar.
                pwa_evidence_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True).strip()
                # Prefer the CI head branch and retain a safe detached fallback.
                pwa_evidence_branch=os.environ.get('GITHUB_HEAD_REF') or subprocess.check_output(['git','branch','--show-current'],cwd=str(ROOT),text=True).strip() or 'detached'
                # Capture one complete PWA shell state with self-describing metadata.
                def pwa_evidence(name,state,locale,viewport_id):
                    # Resolve the exact evidence path beneath the standard browser artifact directory.
                    target=screenshots/name
                    # Render only one allowlisted state through the production status renderer.
                    pwa_page.evaluate("state => window.dispatchEvent(new CustomEvent('casino-pwa-display-state',{detail:{state}}))",pwa_states[state])
                    # Wait until the bounded status renderer exposes the requested state.
                    pwa_page.wait_for_function("state => document.querySelector('[data-testid=pwa-banner]')?.dataset.state===state",arg=pwa_states[state],timeout=3000)
                    # Audit banner containment, readable size, copy, and page overflow before capture.
                    geometry=pwa_page.evaluate("""() => { const banner=document.querySelector('[data-testid=pwa-banner]'); const box=banner.getBoundingClientRect(); return { visible:!banner.hidden, left:box.left, right:box.right, top:box.top, bottom:box.bottom, width:box.width, height:box.height, viewportWidth:innerWidth, overflowX:Math.max(0,document.documentElement.scrollWidth-document.documentElement.clientWidth), text:banner.innerText.trim() }; }""")
                    # Reject hidden, clipped, undersized, overflowing, or raw-key evidence.
                    assert geometry['visible'] and geometry['left']>=-1 and geometry['right']<=geometry['viewportWidth']+1 and geometry['width']>=300 and geometry['height']>=42 and geometry['overflowX']<=1 and geometry['text'] and 'pwa.' not in geometry['text'],geometry
                    # Capture the complete shell without unrelated transient toast or footer overlays.
                    pwa_page.screenshot(path=str(target),full_page=True,animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                    # Bind evidence to exact source, matrix state, locale, viewport, and narrowed platform boundary.
                    metadata={'evidence_class':'after_pass','branch':pwa_evidence_branch,'commit':pwa_evidence_commit,'surface':'pwa_shell','states':[state],'locale':locale,'viewport':{'id':viewport_id,**pwa_viewports[viewport_id]},'path':str(target.relative_to(ROOT)).replace('\\','/'),'geometry':geometry,'platform_foundation':['android_chrome','ios_safari_home_screen'],'native_install_evidence':False}
                    # Write the exact metadata beside its image for artifact and provenance audit.
                    target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
                # Guarantee offline reset, registration cleanup, cache cleanup, and page closure.
                try:
                    # Use the already-authenticated first-load shell as the genuine cold client without racing installation through a redundant navigation.
                    assert pwa_page.evaluate("() => document.documentElement.dataset.pwaStart")=='cold-start'
                    # Await the production registration's fully activated worker before issuing competing manifest, icon, or reload traffic.
                    registration_identity=pwa_page.evaluate("""async () => { const timeout=new Promise(resolve => setTimeout(async () => { const registrations=await navigator.serviceWorker.getRegistrations(); const worker=registrations[0]?.installing||registrations[0]?.waiting||registrations[0]?.active; resolve({ready:false,state:worker?.state||'missing',scriptUrl:worker?.scriptURL||''}); },20000)); const active=navigator.serviceWorker.ready.then(registration => ({ready:Boolean(registration.active),state:registration.active?.state||'',scriptUrl:registration.active?.scriptURL||''})); return await Promise.race([active,timeout]); }""")
                    # Require atomic shell installation and activation at the canonical script before a controlled navigation is attempted.
                    assert registration_identity=={'ready':True,'state':'activated','scriptUrl':f'{base}/sw.js?v={packaged_version}'},{'registration':registration_identity,'workerDiagnostics':pwa_worker_diagnostics[-4:]}
                    # Reload only after activation so the navigation is deterministically controlled even when the initial clients.claim event raced first paint.
                    pwa_page.reload(wait_until='domcontentloaded'); pwa_page.get_by_test_id('lobby').wait_for(timeout=8000)
                    # Wait synchronously for the controlled reload and canonical page identity without an async polling predicate.
                    pwa_page.wait_for_function("(version) => Boolean(navigator.serviceWorker.controller) && window.CasinoPwa?.version===version",arg=packaged_version,timeout=8000)
                    # Require the same-context reload to classify as warm rather than a fresh install claim.
                    assert pwa_page.evaluate("() => document.documentElement.dataset.pwaStart")=='warm-start'
                    # Read the manifest link and both Android/iOS browser-foundation meta contracts.
                    head_meta=pwa_page.evaluate("""() => { const link=document.querySelector('link[rel="manifest"]'); const apple=document.querySelector('link[rel="apple-touch-icon"]'); return { manifestHref:link?.getAttribute('href')||null, themeColor:document.querySelector('meta[name="theme-color"]')?.content||null, viewport:document.querySelector('meta[name="viewport"]')?.content||'', appleCapable:document.querySelector('meta[name="apple-mobile-web-app-capable"]')?.content||null, appleIcon:apple?.getAttribute('href')||null, appleSize:apple?.getAttribute('sizes')||null }; }""")
                    # Require standards-valid linked metadata without claiming a native install.
                    assert head_meta=={'manifestHref':'/manifest.webmanifest','themeColor':'#0a0712','viewport':'width=device-width,initial-scale=1,viewport-fit=cover','appleCapable':'yes','appleIcon':'/assets/pwa-icon-192.png','appleSize':'192x192'},head_meta
                    # Fetch the manifest and validate complete any-purpose and maskable PNG rows.
                    manifest=pwa_page.evaluate("async () => (await (await fetch('/manifest.webmanifest')).json())")
                    # Index the exact icon contract for concise assertions.
                    icon_rows={(row['src'],row['sizes'],row['purpose'],row['type']) for row in manifest['icons']}
                    # Require standalone metadata and every reviewed PNG size/purpose pair.
                    assert manifest['name']=='TiltSeven' and manifest['display']=='standalone' and manifest['scope']=='/' and manifest['theme_color']=='#0a0712' and icon_rows=={('/assets/pwa-icon-192.png','192x192','any','image/png'),('/assets/pwa-icon-512.png','512x512','any','image/png'),('/assets/pwa-maskable-192.png','192x192','maskable','image/png'),('/assets/pwa-maskable-512.png','512x512','maskable','image/png')},manifest
                    # Require every icon response to be a nonempty PNG from the exact manifest paths.
                    icon_responses=pwa_page.evaluate("async icons => Promise.all(icons.map(async icon => { const response=await fetch(icon.src); return { src:icon.src, ok:response.ok, type:response.headers.get('content-type'), bytes:(await response.arrayBuffer()).byteLength }; }))",manifest['icons'])
                    # Reject missing, mislabeled, or placeholder icon responses.
                    assert all(row['ok'] and row['type']=='image/png' and row['bytes']>4000 for row in icon_responses),icon_responses
                    # Read the controlling worker identity without opening CacheStorage through a competing page transaction.
                    worker_identity=pwa_page.evaluate("async () => { const active=(await navigator.serviceWorker.getRegistrations()).find(reg => reg.active)?.active; return { pageVersion:window.CasinoPwa?.version||'', controller:Boolean(navigator.serviceWorker.controller), scriptUrl:active?.scriptURL||'' }; }")
                    # Require the active root worker and page to share the canonical packaged version.
                    assert worker_identity['pageVersion']==packaged_version and worker_identity['controller'] and worker_identity['scriptUrl'].endswith(f'/sw.js?v={packaged_version}'),worker_identity
                    # Fetch an authoritative API path and prove it does not enter any worker cache.
                    pwa_page.evaluate("async () => { await fetch('/api/v1/casino/state',{credentials:'include'}); }")
                    # Enter true offline mode and require native fail-closed controls plus a pre-fetch API rejection.
                    pwa_page.context.set_offline(True); pwa_page.evaluate("() => window.dispatchEvent(new Event('offline'))")
                    # Wait for the controller to expose the offline boundary.
                    pwa_page.wait_for_function("() => window.CasinoPwa?.state()==='offline' && document.querySelector('[data-testid=pwa-banner]')?.dataset.state==='offline'",timeout=3000)
                    # Require the wallet mutation to be natively disabled while local navigation remains available.
                    assert pwa_page.locator('#wallet-menu-summary').is_enabled() and pwa_page.locator('#add-token-btn').is_disabled()
                    # Call the public API helper offline and retain only its stable failure code.
                    offline_result=pwa_page.evaluate("async () => { try { const mod=await import('/core/api.js'); await mod.addUserTokens({amount:1}); return {ok:true}; } catch(error){ return {ok:false,code:error.code||'',message:error.message}; } }")
                    # Require a fail-closed error before any queued or replayable mutation.
                    assert offline_result['ok'] is False and offline_result['code']=='OFFLINE',offline_result
                    # Bound failure-only page exceptions captured during offline shell reconstruction.
                    pwa_page_errors=[]
                    # Bound failure-only console errors captured during offline shell reconstruction.
                    pwa_console_errors=[]
                    # Normalize one diagnostic value without retaining local origins, roots, newlines, or unbounded text.
                    def pwa_diagnostic_text(value):
                        # Replace the ephemeral server origin before the diagnostic can enter an artifact.
                        text=str(value).replace(base,'<origin>')
                        # Replace the local checkout path before the diagnostic can enter an artifact.
                        text=text.replace(str(ROOT),'<root>')
                        # Collapse whitespace and retain only a bounded diagnostic prefix.
                        return re.sub(r'\s+',' ',text).strip()[:240]
                    # Retain at most eight sanitized page errors around the failed predicate.
                    def capture_pwa_page_error(error):
                        # Append one bounded error only while the reviewed cardinality remains available.
                        if len(pwa_page_errors)<8: pwa_page_errors.append(pwa_diagnostic_text(error))
                    # Retain at most eight sanitized error-level console messages around the failed predicate.
                    def capture_pwa_console_error(message):
                        # Ignore non-error console traffic and bound the retained diagnostic cardinality.
                        if message.type=='error' and len(pwa_console_errors)<8: pwa_console_errors.append(pwa_diagnostic_text(message.text))
                    # Observe page exceptions only across the exact offline navigation and readiness boundary.
                    pwa_page.on('pageerror',capture_pwa_page_error)
                    # Observe error-level console output only across the exact offline navigation and readiness boundary.
                    pwa_page.on('console',capture_pwa_console_error)
                    # Bound listener cleanup around the unchanged offline navigation and readiness wait.
                    try:
                        # Navigate while truly offline so only the cached index and exact static module allowlist can reconstruct the shell.
                        pwa_page.goto(f'{base}/games/roulette',wait_until='domcontentloaded',timeout=WAIT_MS * 2)
                        # Preserve one eight-second wait while proving only reconstructed-document readiness.
                        try:
                            # Require the reconstructed PWA controller, cached shell, and localization runtime before dispatching the new document's event.
                            pwa_page.wait_for_function("() => Boolean(window.CasinoPwa) && document.body?.dataset.testid==='pwa-shell' && Boolean(window.CasinoI18n)",timeout=8000)
                        # Add evidence only when the existing readiness wait times out.
                        except PlaywrightTimeoutError:
                            # Inspect bounded predicate, document, worker, cache, and passive module-resource state without retrying readiness.
                            try: pwa_timeout_state=pwa_page.evaluate("""async () => { const pwaPresent=Boolean(window.CasinoPwa); const pwaState=window.CasinoPwa?.state?.()??null; const shellMarker=document.body?.dataset?.testid??null; const i18nPresent=Boolean(window.CasinoI18n); const controller=navigator.serviceWorker.controller; const cacheNames=(await caches.keys()).filter(name => name.startsWith('casino-static-shell-v')).slice(0,4); const cachedResponse=await caches.match('/core/celebrate.js'); const celebrateResources=performance.getEntriesByType('resource').filter(entry => { try { return new URL(entry.name).pathname==='/core/celebrate.js'; } catch (_) { return false; } }); const celebrateResource=celebrateResources.at(-1); const falsePredicates=[]; if (!pwaPresent) falsePredicates.push('pwaPresent'); if (shellMarker!=='pwa-shell') falsePredicates.push('shellMarker'); if (!i18nPresent) falsePredicates.push('i18nPresent'); return {falsePredicates,pwaPresent,pwaState,shellMarker,i18nPresent,documentReadyState:document.readyState,online:navigator.onLine,controllerPresent:Boolean(controller),controllerScript:controller?new URL(controller.scriptURL).pathname:null,controllerState:controller?.state??null,relevantCacheNames:cacheNames,relevantCachePresent:cacheNames.length>0,celebrateCached:Boolean(cachedResponse),celebrateResourceObserved:Boolean(celebrateResource),celebrateResourceCount:Math.min(celebrateResources.length,4),celebrateResourceCompleted:Boolean(celebrateResource?.responseEnd)}; }""")
                            # Normalize a diagnostic-evaluation failure without hiding the original readiness failure.
                            except Exception as diagnostic_error: pwa_timeout_state={'diagnosticError':pwa_diagnostic_text(diagnostic_error)}
                            # Bind the bounded page and console observations to the exact timeout snapshot.
                            pwa_timeout_state['pageErrors']=pwa_page_errors
                            # Bind only bounded error-level console observations to the exact timeout snapshot.
                            pwa_timeout_state['consoleErrors']=pwa_console_errors
                            # Fail with the same Playwright timeout class and sanitized low-cardinality evidence.
                            raise PlaywrightTimeoutError('PWA offline readiness timeout diagnostic '+json.dumps(pwa_timeout_state,sort_keys=True,separators=(',',':'))) from None
                        # Dispatch exactly one offline event to the reconstructed window whose listeners now exist.
                        pwa_page.evaluate("() => window.dispatchEvent(new Event('offline'))")
                        # Read the synchronously committed reconstructed-document state without adding another wait.
                        reconstructed_offline_state=pwa_page.evaluate("() => { const panel=document.querySelector('[data-testid=game-offline-panel]'); return {pwaState:window.CasinoPwa?.state?.()??null,shellMarker:document.body?.dataset?.testid??null,i18nPresent:Boolean(window.CasinoI18n),offlinePanelPresent:Boolean(panel),restoreLoadingPresent:Boolean(document.querySelector('[data-testid=route-restore-loading]')),panelText:panel?.innerText.trim()||''}; }")
                        # Require an honest localized game boundary instead of the former dead loading panel.
                        assert reconstructed_offline_state['pwaState']=='offline' and reconstructed_offline_state['shellMarker']=='pwa-shell' and reconstructed_offline_state['i18nPresent'] and reconstructed_offline_state['offlinePanelPresent'] and not reconstructed_offline_state['restoreLoadingPresent'] and reconstructed_offline_state['panelText'] and 'routeOffline.' not in reconstructed_offline_state['panelText'],reconstructed_offline_state
                        # Bind the new game-route surface to the governed compact PWA offline evidence cell.
                        pwa_page.set_viewport_size(pwa_viewports['desktop_compact'])
                        # Capture the exact offline route and localized panel through the existing evidence helper.
                        pwa_evidence('after-pass-pwa-offline-game-route-en-us-desktop-compact.png','offline','en-US','desktop_compact')
                    # Always remove diagnostic listeners so the successful path retains no later output or state.
                    finally:
                        # Release the page-error listener installed only for this readiness boundary.
                        pwa_page.remove_listener('pageerror',capture_pwa_page_error)
                        # Release the console listener installed only for this readiness boundary.
                        pwa_page.remove_listener('console',capture_pwa_console_error)
                    # Prove a direct authoritative API request is unavailable rather than served from the worker cache.
                    direct_offline_api=pwa_page.evaluate("async () => { try { await fetch('/api/v1/casino/state',{credentials:'include'}); return true; } catch (_) { return false; } }")
                    # Reject any offline API replay or cached authoritative response.
                    assert direct_offline_api is False
                    # Restore connectivity and require authoritative session, wallet, catalog, and same-route refresh before controls return.
                    pwa_page.context.set_offline(False); pwa_page.evaluate("() => window.dispatchEvent(new Event('online'))")
                    # Require the authoritative reconnect callback to remount the same route.
                    try:
                        # Wait for the exact terminal state, route, and game-owned ready marker together.
                        pwa_page.wait_for_function("() => window.CasinoPwa?.state()==='route-restored' && location.pathname==='/games/roulette' && Boolean(document.querySelector('[data-testid=roulette-premium]'))",timeout=12000)
                    # Add bounded page-state evidence only when the unchanged reconnect predicate times out.
                    except PlaywrightTimeoutError:
                        # Read only low-cardinality lifecycle and route facts without exposing session or response data.
                        reconnect_timeout_state=pwa_page.evaluate("""async () => { const resources=performance.getEntriesByType('resource'); const rouletteResources=resources.filter(entry => { try { return new URL(entry.name).pathname==='/games/roulette.js'; } catch (_) { return false; } }); const misplacedResources=resources.filter(entry => { try { return new URL(entry.name).pathname==='/core/games/roulette.js'; } catch (_) { return false; } }); const rouletteResource=rouletteResources.at(-1); const view=document.getElementById('view'); return {pwaState:window.CasinoPwa?.state?.()??null,path:location.pathname,online:navigator.onLine,premiumPresent:Boolean(document.querySelector('[data-testid=roulette-premium]')),loginPresent:Boolean(document.querySelector('[data-testid=login-gate]')),restorePresent:Boolean(document.querySelector('[data-testid=route-restore-loading]')),loadFailurePresent:Boolean(view?.querySelector('[data-route=lobby]')),loadingPanelPresent:Boolean(view?.querySelector('.loading-panel')),viewTestId:view?.dataset?.testid??null,bannerState:document.querySelector('[data-testid=pwa-banner]')?.dataset?.state??null,bannerHidden:Boolean(document.querySelector('[data-testid=pwa-banner]')?.hidden),appScriptPath:new URL(document.querySelector('script[type=module]')?.src||location.href).pathname,rouletteResourceCount:Math.min(rouletteResources.length,4),rouletteResourceCompleted:Boolean(rouletteResource?.responseEnd),misplacedRouletteResourceCount:Math.min(misplacedResources.length,4)}; }""")
                        # Preserve the same failure class with deterministic diagnostics for the exact predicate.
                        raise PlaywrightTimeoutError('PWA reconnect timeout diagnostic '+json.dumps(reconnect_timeout_state,sort_keys=True,separators=(',',':'))) from None
                    # Dispatch one synthetic mismatched worker version and read the synchronously committed listener result in the same task.
                    stale_client_state=pwa_page.evaluate("() => { navigator.serviceWorker.dispatchEvent(new MessageEvent('message',{data:{type:'PWA_VERSION',version:'0.0.0'}})); return window.CasinoPwa?.state()||''; }")
                    # Require the real message listener to commit stale-client status without an asynchronous reconnect race.
                    assert stale_client_state=='stale-client',stale_client_state
                    # Return to the shell root before generating the governed visual corpus.
                    pwa_page.goto(f'{base}/?locale=en-US',wait_until='domcontentloaded'); pwa_page.get_by_test_id('lobby').wait_for(timeout=8000)
                    # Generate exact EN/RU evidence for every state at every governed viewport.
                    for pwa_locale in ('en-US','ru-RU'):
                        # Reload through the locale query so visible copy and sidecar metadata share one source.
                        pwa_page.goto(f'{base}/?locale={pwa_locale}',wait_until='domcontentloaded'); pwa_page.get_by_test_id('lobby').wait_for(timeout=8000)
                        # Wait until the active locale exactly matches the evidence label.
                        pwa_page.wait_for_function("locale => window.CasinoI18n?.getLocaleState().locale===locale",arg=pwa_locale,timeout=WAIT_MS)
                        # Visit every governed viewport in stable matrix order.
                        for pwa_viewport_id,pwa_viewport in pwa_viewports.items():
                            # Resize before state render so responsive layout and wrapping are final.
                            pwa_page.set_viewport_size(pwa_viewport)
                            # Capture every authorized lifecycle state independently.
                            for pwa_state in pwa_states:
                                # Write one exact-state image and sidecar pair.
                                pwa_evidence(f'after-pass-pwa-{pwa_state}-{pwa_locale.lower()}-{pwa_viewport_id}.png',pwa_state,pwa_locale,pwa_viewport_id)
                    # End the authenticated session through the real API helper before expired-session reconnect proof.
                    pwa_page.evaluate("async () => { const mod=await import('/core/api.js'); await mod.logout(); }")
                    # Trigger one offline-to-online transition after server-side logout.
                    pwa_page.context.set_offline(True); pwa_page.evaluate("() => window.dispatchEvent(new Event('offline'))"); pwa_page.context.set_offline(False); pwa_page.evaluate("() => window.dispatchEvent(new Event('online'))")
                    # Require stale authenticated UI to be replaced by login and the explicit expired-session state.
                    pwa_page.wait_for_function("() => window.CasinoPwa?.state()==='expired-session' && Boolean(document.querySelector('[data-testid=login-gate]'))",timeout=WAIT_MS * 2)
                # Always release worker, cache, connectivity, and page state for downstream browser cases.
                finally:
                    # Restore the context network before cleanup requests.
                    pwa_page.context.set_offline(False)
                    # Remove only Casino service-worker registrations and caches created by this focused case.
                    pwa_page.evaluate("async () => { const regs=await navigator.serviceWorker.getRegistrations(); await Promise.all(regs.map(reg => reg.unregister())); const names=await caches.keys(); await Promise.all(names.filter(name => name.startsWith('casino-static-shell-v')).map(name => caches.delete(name))); }")
                    # Leave the authenticated application page open for the outer deterministic page cleanup.
                    assert not pwa_page.is_closed()
            # Execute the narrowed PWA foundation regression and exact-head evidence corpus.
            run_case('BR-PWA-001',['PWA-001','PWA-002','TEST-095'],pwa_installable_shell)
            # Prove one explicit update converges every controlled same-origin tab without a second click. (PWA-003)
            def pwa_multitab_one_click_update():
                # Use a distinct prior script URL while serving the same governed worker body so Chromium performs a real update lifecycle.
                previous_worker_version=f'{packaged_version}-previous'
                # Isolate registration, CacheStorage, navigation, and controller ownership from the broader authenticated browser context.
                update_context=browser.new_context(viewport={'width':1440,'height':900},service_workers='allow')
                # Retain every opened page for exact controller convergence and bounded cleanup.
                update_pages=[]
                # Guarantee registration, cache, and tab cleanup even when one lifecycle assertion fails.
                try:
                    # Open API docs first because it does not register the application worker on its own.
                    docs_page=update_context.new_page(); update_pages.append(docs_page); docs_page.goto(f'{base}/api-docs',wait_until='domcontentloaded')
                    # Install and activate one prior-URL worker, then wait until the seed client is controlled.
                    prior_identity=docs_page.evaluate("""async version => { const registration=await navigator.serviceWorker.register(`/sw.js?v=${encodeURIComponent(version)}`,{scope:'/',type:'module',updateViaCache:'none'}); await navigator.serviceWorker.ready; if (!navigator.serviceWorker.controller) await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true})); return {active:registration.active?.scriptURL||'',controller:navigator.serviceWorker.controller?.scriptURL||'',waiting:Boolean(registration.waiting)}; }""",previous_worker_version)
                    # Require a settled prior controller without an update already waiting.
                    assert prior_identity=={'active':f'{base}/sw.js?v={previous_worker_version}','controller':f'{base}/sw.js?v={previous_worker_version}','waiting':False},prior_identity
                    # Open the public signup client while the prior worker controls the same-origin tab population.
                    signup_page=update_context.new_page(); update_pages.append(signup_page); signup_page.goto(f'{base}/enroll/signup',wait_until='domcontentloaded')
                    # Open the Casino shell so its production PWA boot deterministically registers the canonical worker.
                    casino_page=update_context.new_page(); update_pages.append(casino_page); casino_page.goto(f'{base}/?locale=en-US',wait_until='domcontentloaded')
                    # Wait until Chromium exposes the canonical worker in the waiting slot while the prior controller remains active.
                    docs_page.wait_for_function("version => navigator.serviceWorker.getRegistration('/').then(registration => Boolean(registration?.waiting) && new URL(registration.waiting.scriptURL).searchParams.get('v')===version)",arg=packaged_version,timeout=20000)
                    # Require production PWA initialization and the real waiting-worker banner before clicking.
                    casino_page.wait_for_function("() => window.CasinoPwa?.state()==='update' && document.querySelector('[data-testid=pwa-update-reload]')",timeout=8000)
                    # Count controller changes after all three old-controller clients exist and before the single apply action.
                    for update_page in update_pages:
                        # Install one passive per-page counter without changing registration or navigation behavior.
                        update_page.evaluate("() => { sessionStorage.setItem('__casinoPwaControllerChanges','0'); navigator.serviceWorker.addEventListener('controllerchange',()=>{ sessionStorage.setItem('__casinoPwaControllerChanges',String(Number(sessionStorage.getItem('__casinoPwaControllerChanges')||'0')+1)); },{capture:true}); }")
                    # Snapshot the authentic waiting boundary and exact one-button cardinality.
                    before_update=casino_page.evaluate("""async version => { const registration=await navigator.serviceWorker.getRegistration('/'); return {active:registration?.active?.scriptURL||'',waiting:registration?.waiting?.scriptURL||'',controller:navigator.serviceWorker.controller?.scriptURL||'',state:window.CasinoPwa?.state()||'',buttons:document.querySelectorAll('[data-testid=pwa-update-reload]').length,expected:version}; }""",packaged_version)
                    # Require the prior controller, canonical waiting worker, update state, and one visible apply control.
                    assert before_update['active'].endswith(f'/sw.js?v={previous_worker_version}') and before_update['controller'].endswith(f'/sw.js?v={previous_worker_version}') and before_update['waiting'].endswith(f'/sw.js?v={packaged_version}') and before_update['state']=='update' and before_update['buttons']==1,before_update
                    # Click exactly once and bind the navigation to the controllerchange-owned reload.
                    with casino_page.expect_navigation(wait_until='domcontentloaded',timeout=20000):
                        # Use the player-visible production control without invoking private controller methods.
                        casino_page.get_by_test_id('pwa-update-reload').click()
                    # Require every previously controlled same-origin page to adopt the canonical controller.
                    for update_page in update_pages:
                        # Wait on each real Navigator.serviceWorker controller rather than shared registration state alone.
                        update_page.wait_for_function("version => new URL(navigator.serviceWorker.controller?.scriptURL||location.href).searchParams.get('v')===version",arg=packaged_version,timeout=12000)
                    # Read the settled registration, one-reload navigation, banner residue, and exact per-client controller changes.
                    final_update=casino_page.evaluate("""async () => { const registration=await navigator.serviceWorker.getRegistration('/'); const banner=document.querySelector('[data-testid=pwa-banner]'); return {active:registration?.active?.scriptURL||'',waiting:Boolean(registration?.waiting),controller:navigator.serviceWorker.controller?.scriptURL||'',pageVersion:window.CasinoPwa?.version||'',navigation:performance.getEntriesByType('navigation')[0]?.type||'',buttons:document.querySelectorAll('[data-testid=pwa-update-reload]').length,bannerVisible:Boolean(banner && !banner.hidden),controllerChanges:Number(sessionStorage.getItem('__casinoPwaControllerChanges')||'0')}; }""")
                    # Read the unchanged API-docs and signup documents' controller-change observations.
                    peer_updates=[update_page.evaluate("() => ({controller:navigator.serviceWorker.controller?.scriptURL||'',changes:Number(sessionStorage.getItem('__casinoPwaControllerChanges')||'0')})") for update_page in (docs_page,signup_page)]
                    # Require one stable canonical worker, no waiting/banner residue, exactly one Casino reload, and all three clients changed once.
                    assert final_update['active'].endswith(f'/sw.js?v={packaged_version}') and not final_update['waiting'] and final_update['controller'].endswith(f'/sw.js?v={packaged_version}') and final_update['pageVersion']==packaged_version and final_update['navigation']=='reload' and final_update['buttons']==0 and not final_update['bannerVisible'] and final_update['controllerChanges']==1 and all(row['controller'].endswith(f'/sw.js?v={packaged_version}') and row['changes']==1 for row in peer_updates),{'final':final_update,'peers':peer_updates}
                    # Resolve the governed after-pass artifact path for the real multi-tab convergence boundary.
                    update_target=screenshots/'after-pass-pwa-multitab-one-click-en-us-desktop-compact.png'
                    # Capture the stable post-update Casino shell without unrelated transient UI.
                    casino_page.screenshot(path=str(update_target),full_page=True,animations='disabled',style='#toast, .status-bar { visibility: hidden !important; }')
                    # Bind the artifact to exact source, existing matrix states, locale, viewport, and per-client controller facts.
                    update_metadata={'evidence_class':'after_pass','branch':os.environ.get('GITHUB_HEAD_REF') or subprocess.check_output(['git','branch','--show-current'],cwd=str(ROOT),text=True).strip() or 'detached','commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),text=True).strip(),'surface':'pwa_shell','states':['update_available','route_restored'],'locale':'en-US','viewport':{'id':'desktop_compact','width':1440,'height':900},'path':str(update_target.relative_to(ROOT)).replace('\\','/'),'tabs':['casino','api_docs','signup'],'apply_clicks':1,'navigation_type':final_update['navigation'],'waiting_residue':final_update['waiting'],'controller_changes':[final_update['controllerChanges'],*[row['changes'] for row in peer_updates]]}
                    # Write self-describing exact-head evidence beside the screenshot.
                    update_target.with_suffix('.json').write_text(json.dumps(update_metadata,indent=2,ensure_ascii=False),encoding='utf-8')
                # Always remove this case's registrations, caches, and tabs without touching other browser contexts.
                finally:
                    # Choose any surviving page as the same-origin cleanup owner.
                    cleanup_page=next((page for page in update_pages if not page.is_closed()),None)
                    # Remove only Casino service-worker registrations and caches when a page reached the origin.
                    if cleanup_page: cleanup_page.evaluate("async () => { const registrations=await navigator.serviceWorker.getRegistrations(); await Promise.all(registrations.map(registration => registration.unregister())); const names=await caches.keys(); await Promise.all(names.filter(name => name.startsWith('casino-static-shell-v')).map(name => caches.delete(name))); }")
                    # Close the isolated context once so every page and listener is released together.
                    update_context.close()
            # Execute the real three-client update regression under the same producer/consumer shard affinity.
            run_case('BR-PWA-UPDATE-001',['PWA-003','TEST-095','TEST-153'],pwa_multitab_one_click_update)
        # Close the focused page even when its assertions fail.
        finally:
            # Release the isolated backend-login browser context before the existing broad UI suite.
            real_login_page.close()
    # Preserve deterministic case positions when this shard does not own the guarded body.
    else:
        # Advance all three literal cases without running their browser-owned setup or teardown.
        skip_browser_affinity('auth_backend_pwa')
