// Exercise the exact frontend safety helpers without starting a browser or network listener.
import assert from 'node:assert/strict';
// Read tracked source files so the proof stays coupled to production code and markup.
import { readFile } from 'node:fs/promises';
// Resolve portable repository paths from this test module.
import path from 'node:path';
// Convert the current module URL into a filesystem path.
import { fileURLToPath } from 'node:url';

// Resolve the exact checkout root.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Read the production API helper that owns client-error telemetry.
const apiSource = await readFile(path.join(root, 'web', 'core', 'api.js'), 'utf8');
// Read the shared feedback helper that owns toast palette semantics.
const uiSource = await readFile(path.join(root, 'web', 'core', 'ui.js'), 'utf8');
// Read the shared card renderer so duplicate escaping implementations cannot return. (CORE-033)
const cardsSource = await readFile(path.join(root, 'web', 'core', 'cards.js'), 'utf8');
// Read the persistent shell markup that owns live-region semantics.
const indexSource = await readFile(path.join(root, 'web', 'index.html'), 'utf8');
// Read shared styles that own the Slots reduced-motion channel.
const sharedStyles = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
// Read the affected game modules for exact reduced-motion and layout contracts.
const baccaratSource = await readFile(path.join(root, 'web', 'games', 'baccarat.js'), 'utf8');
// Read Bingo's affected animation source.
const bingoSource = await readFile(path.join(root, 'web', 'games', 'bingo.js'), 'utf8');
// Read Keno's affected animation source.
const kenoSource = await readFile(path.join(root, 'web', 'games', 'keno.js'), 'utf8');
// Read Roulette's guarded action wiring source.
const rouletteSource = await readFile(path.join(root, 'web', 'games', 'roulette.js'), 'utf8');
// Read Teen Patti's external stylesheet for its mobile feedback-clearance contract.
const teenPattiStyles = await readFile(path.join(root, 'web', 'games', 'teen_patti.css'), 'utf8');
// Read the shared autoplay lifecycle for reconciliation and server-tick contracts.
const autoplaySource = await readFile(path.join(root, 'web', 'core', 'autoplay.js'), 'utf8');
// Read the extracted Language tab that owns formatter option composition. (CORE-033)
const adminLanguageSource = await readFile(path.join(root, 'web', 'admin', 'language.js'), 'utf8');
// Read the extracted Sessions tab that owns request-rate policy controls. (SEC-015, ADMIN-032)
const adminSessionsSource = await readFile(path.join(root, 'web', 'admin', 'sessions.js'), 'utf8');
// Read the extracted Guest Trials tab that owns the admission policy controls. (GUEST-001, GUEST-004)
const adminGuestsSource = await readFile(path.join(root, 'web', 'admin', 'guests.js'), 'utf8');
// Read the extracted Login view that owns anonymous account-entry policy. (UX-028)
const loginSource = await readFile(path.join(root, 'web', 'views', 'login.js'), 'utf8');
// Read the extracted application bootstrap that owns layout stabilization and telemetry. (UX-026, UX-027)
const appBootstrapSource = await readFile(path.join(root, 'web', 'core', 'app_bootstrap.js'), 'utf8');
// Read the shared audio helper so its fail-closed fallback remains silent before settings load. (AUDIO-010)
const voiceSource = await readFile(path.join(root, 'web', 'core', 'voice.js'), 'utf8');
// Read Blackjack focus and announcement integration.
const blackjackSource = await readFile(path.join(root, 'web', 'games', 'blackjack.js'), 'utf8');
// Read Color Wheel's external route stylesheet for the older-game accessibility contract.
const colorWheelStyles = await readFile(path.join(root, 'web', 'games', 'color_wheel.css'), 'utf8');
// Read Four Card Poker's extracted route stylesheet for the same accessibility contract.
const fourCardPokerStyles = await readFile(path.join(root, 'web', 'games', 'four_card_poker.css'), 'utf8');

// Publish the minimal browser seams required by the real API helper.
globalThis.document = { cookie: 'casino_csrf=frontend-safety-proof', getElementById: () => null };
// Preserve session-only guest proof behavior without durable storage.
const sessionValues = new Map();
// Publish a standards-compatible sessionStorage seam.
globalThis.sessionStorage = { getItem: key => sessionValues.get(key) ?? null, setItem: (key, value) => sessionValues.set(key, String(value)), removeItem: key => sessionValues.delete(key) };
// Publish the online and user-agent values consumed by the real helper through Node's read-only global seam.
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { onLine: true, userAgent: 'frontend-safety-test' } });
// Publish a token-bearing invitation address so sanitization is exercised on production input shape.
globalThis.location = { href: 'https://casino.tiltseven.com/enroll/invitation?token=do-not-log#private' };
// Collect request initializers without sending any network traffic.
const calls = [];
// Return a normal API envelope for every captured request.
globalThis.fetch = async (requestPath, init) => { calls.push({ requestPath, init }); return { ok: true, json: async () => ({ ok: true, data: {} }) }; };
// Replace only the static locale import with a deterministic translation seam for the data-URL module.
const executableApiSource = apiSource.replace("import { t } from './i18n.js';", "const t = key => key;");
// Import the exact API logic with its one external dependency replaced by the focused seam.
const apiModule = await import(`data:text/javascript;base64,${Buffer.from(executableApiSource).toString('base64')}`);
// Send one client-log event through the public helper.
await apiModule.logClient('frontend_safety_probe', { safe: true });
// Require the event to use the frozen client-log endpoint.
assert.equal(calls[0].requestPath, '/api/v1/log/client');
// Parse the exact serialized request body emitted by the helper.
const loggedPayload = JSON.parse(calls[0].init.body);
// Require telemetry to preserve only the non-secret origin and path.
assert.equal(loggedPayload.href, 'https://casino.tiltseven.com/enroll/invitation');
// Reject query, fragment, and bearer material anywhere in the serialized event.
assert.equal(calls[0].init.body.includes('do-not-log'), false);
// Replace the address with malformed input to exercise the fail-closed branch.
globalThis.location.href = 'not a valid absolute url';
// Send a second client-log event through the same helper.
await apiModule.logClient('frontend_safety_malformed_probe');
// Require malformed input to publish only the stable non-sensitive marker.
assert.equal(JSON.parse(calls[1].init.body).href, 'unavailable');

// Replace relative imports with inert test seams while retaining the exact tracked toast implementation.
const executableUiSource = uiSource
  // Remove only complete static import statements from the module prelude.
  .replace(/^import .*;\r?\n/gm, '')
  // Provide the imported formatter and API symbols without invoking them in this focused proof.
  .replace('// Export this symbol so other modules can display play tokens consistently.', "const api=async()=>({}); const post=async()=>({}); const currentPlayerId=()=>''; const withCurrentPlayer=body=>body; const formatMoney=value=>String(value);\n// Export this symbol so other modules can display play tokens consistently.")
  // Export the internal classifier so its complete variant table can be asserted directly.
  .concat('\nexport { toastIsSuccess };\n');
// Import the transformed exact implementation without executing unrelated UI functions.
const uiModule = await import(`data:text/javascript;base64,${Buffer.from(executableUiSource).toString('base64')}`);
// Exercise ordinary hostile text through the escape-by-default tagged template boundary. (CORE-033)
assert.equal(String(uiModule.html`<p data-value="${'\"><img src=x onerror=alert(1)>'}">${'<script>&'}</p>`), '<p data-value="&quot;&gt;&lt;img src=x onerror=alert(1)&gt;">&lt;script&gt;&amp;</p>');
// Require nested fragment arrays to flatten without commas while independently escaping their text. (CORE-033)
assert.equal(String(uiModule.html`<ul>${[uiModule.html`<li>${'A&B'}</li>`, uiModule.html`<li>${'<two>'}</li>`]}</ul>`), '<ul><li>A&amp;B</li><li>&lt;two&gt;</li></ul>');
// Require reviewed nested attribute fragments to preserve markup while escaping their value. (CORE-033)
assert.equal(String(uiModule.html`<div${uiModule.html` data-testid="${'row'}"`}></div>`), '<div data-testid="row"></div>');
// Require the explicit raw escape hatch to preserve only caller-reviewed markup. (CORE-033)
assert.equal(String(uiModule.html`<div>${uiModule.raw('<strong data-safe="1">Reviewed</strong>')}</div>`), '<div><strong data-safe="1">Reviewed</strong></div>');
// Require the migration adapter to reuse the canonical escape implementation without double escaping. (CORE-033)
assert.equal(String(uiModule.html`<p>${uiModule.escaped('<Admin>')}</p>`), '<p>&lt;Admin&gt;</p>');
// Require the legacy card helper to escape caller-owned rank text through the same implementation. (CORE-033)
assert.match(uiModule.cardHtml({ rank: '<img>', suit: '♥' }), /&lt;img&gt;/);
// Require the dedicated card renderer to import the canonical helper instead of defining a competing encoder. (CORE-033)
assert.match(cardsSource, /import \{ safe \} from '\.\/ui\.js';/);
// Reject any return of the retired card-local escape implementation. (CORE-033)
assert.doesNotMatch(cardsSource, /function escapeHtml\(/);
// Require the formatter selector to compose its reviewed option fragments through the tagged template. (CORE-033)
assert.match(adminLanguageSource, /return html`\$\{browser\}\$\{formatters\.map\(locale => option\(/);
// Reject string coercion that would make the outer template escape every generated option as text. (CORE-033)
assert.doesNotMatch(adminLanguageSource, /return browser \+ formatters\.map\(/);
// Build the persistent toast outlet used by every palette assertion.
const toastOutlet = { textContent: '', style: {}, hidden: true };
// Route only the shared toast identity to the focused outlet.
globalThis.document.getElementById = id => id === 'toast' ? toastOutlet : null;
// Preserve the native timer functions before replacing the long display delay.
const nativeSetTimeout = globalThis.setTimeout;
// Preserve the native clear helper for restoration.
const nativeClearTimeout = globalThis.clearTimeout;
// Replace the display timer with a non-blocking deterministic seam.
globalThis.setTimeout = () => 1;
// Replace timer clearing with an inert deterministic seam.
globalThis.clearTimeout = () => {};
// Require every documented success spelling and only those spellings to select success.
assert.deepEqual([true, 'ok', 'success', false, 'error', 'warning', 1].map(uiModule.toastIsSuccess), [true, true, true, false, false, false, false]);
// Render the historically inverted string error variant.
uiModule.toast('Failure', 'error');
// Require string errors to use the error background and foreground.
assert.deepEqual([toastOutlet.style.background, toastOutlet.style.color], ['#2b1111', '#ffd3d3']);
// Render the legacy boolean success variant.
uiModule.toast('Success', true);
// Require legacy success callers to retain the success palette.
assert.deepEqual([toastOutlet.style.background, toastOutlet.style.color], ['#10381f', '#c8ffd1']);
// Restore the native timer functions after the deterministic proof.
globalThis.setTimeout = nativeSetTimeout;
// Restore native timer clearing after the deterministic proof.
globalThis.clearTimeout = nativeClearTimeout;

// Replace the autoplay imports with controlled listener-free seams while retaining exact production control flow. (AUTO-015)
const executableAutoplaySource = autoplaySource
  // Route the API imports to deterministic globals owned by this focused proof.
  .replace("import { api, post, currentPlayerId } from './api.js';", "const api=(...args)=>globalThis.__autoplayApi(...args); const post=(...args)=>globalThis.__autoplayPost(...args); const currentPlayerId=()=>\"proof-player\";")
  // Replace translation with a stable inert seam because no copy assertion is needed here.
  .replace("import { t } from './i18n.js';", "const t=key=>key;")
  // Export only internal lifecycle seams needed to prove phase-safe limiter recovery.
  .concat('\nexport { getSession, loop };\n');
// Publish the minimal window surface consumed during autoplay module initialization.
globalThis.window = { __casinoAutoplaySessions: new Map(), dispatchEvent: () => true };
// Publish the CustomEvent constructor required by the production toast dispatcher.
globalThis.CustomEvent = class { constructor(type, init){ this.type=type; this.detail=init?.detail; } };
// Collect deterministic timers so retry phases can be advanced without sleeping.
const autoplayTimers = [];
// Replace timer scheduling with a seam that retains callback and delay for exact assertions.
globalThis.setTimeout = (callback, wait) => { autoplayTimers.push({ callback, wait }); return autoplayTimers.length; };
// Keep timer cancellation inert because the proof advances only the current retained callback.
globalThis.clearTimeout = () => {};
// Return an authoritative running session for each pre-action reconciliation request.
globalThis.__autoplayApi = async () => ({ session: { status: 'running', stop_requested: false } });
// Count ledger-bearing game actions separately from lifecycle bookkeeping requests.
let autoplayActions = 0;
// Count tick-bookkeeping attempts so the first completed action can face a later limiter rejection.
let autoplayTickPosts = 0;
// Build a stable structured limiter error matching the shared API helper contract.
const rateLimited = () => Object.assign(new Error('Wait before trying again.'), { code: 'RATE_LIMITED', status: 429 });
// Reject the first bookkeeping attempt, then accept the exact retry.
globalThis.__autoplayPost = async requestPath => { assert.equal(requestPath, '/api/v1/autoplay/tick'); autoplayTickPosts += 1; if(autoplayTickPosts===1) throw rateLimited(); return { session: { rounds_completed: 1 } }; };
// Import the transformed exact autoplay implementation with no browser or network listener.
const autoplayModule = await import(`data:text/javascript;base64,${Buffer.from(executableAutoplaySource).toString('base64')}`);
// Create one retained running session through the production session factory.
const autoplaySession = autoplayModule.getSession('rate-limit-proof');
// Bind the exact authoritative lifecycle and remaining-count state used by a live loop.
Object.assign(autoplaySession, { running: true, serverId: 'autoplay-proof', remaining: 2, speed: 'fast' });
// Reject the first game action before mutation, then allow its phase-safe retry to complete once.
autoplaySession.onTick = async () => { autoplayActions += 1; if(autoplayActions===1) throw rateLimited(); };
// Start the production loop and let its first pre-action limiter response schedule recovery.
await autoplayModule.loop(autoplaySession);
// Require pre-action rejection to preserve the action count and schedule the first bounded pause.
assert.deepEqual([autoplayActions, autoplayTickPosts, autoplaySession.remaining, autoplayTimers[0].wait], [1, 0, 2, 1000]);
// Advance the retained pre-action callback so the game action succeeds exactly once.
await autoplayTimers.shift().callback();
// Require the later bookkeeping rejection not to consume remaining count or replay immediately.
assert.deepEqual([autoplayActions, autoplayTickPosts, autoplaySession.remaining, autoplayTimers[0].wait], [2, 1, 2, 2000]);
// Advance only the retained bookkeeping callback after the game action has already completed.
await autoplayTimers.shift().callback();
// Require bookkeeping retry to decrement once and schedule the next new action without duplication.
assert.deepEqual([autoplayActions, autoplayTickPosts, autoplaySession.remaining, autoplayTimers[0].wait], [2, 2, 1, 260]);
// Restore native timer functions after the autoplay recovery proof.
globalThis.setTimeout = nativeSetTimeout;
// Restore native timer clearing after the autoplay recovery proof.
globalThis.clearTimeout = nativeClearTimeout;

// Require the persistent shell outlet to expose stable polite atomic live-region semantics.
assert.match(indexSource, /<div id="toast" class="toast" role="status" aria-live="polite" aria-atomic="true" hidden><\/div>/);
// Require the document-lifetime game result outlet that survives route-owned full-root renders. (UX-025)
assert.match(indexSource, /<div id="game-live-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true"><\/div>/);
// Require all five governed games to preserve focus and publish current result status. (UX-025)
for (const source of [rouletteSource, kenoSource, bingoSource, blackjackSource, baccaratSource]) assert.match(source, /captureGameFocus\(root\)[\s\S]*restoreGameFocus\(root, focus\)[\s\S]*syncGameLiveStatus\(root\)/);
// Require Roulette precision controls to keep a 24-pixel hit area around the compact marker. (UX-025)
assert.match(rouletteSource, /const SPOT_SIZE = 24;[\s\S]*\.spot\{display:grid;place-items:center;width:24px;height:24px/);
// Require shared and route-local controls called out by UX-025 to preserve 44-pixel touch targets.
assert.match(sharedStyles, /button\s*\{\s*min-height:\s*44px;/); assert.match(baccaratSource, /\.bac-rail-card select\{min-height:44px\}[\s\S]*\.bac-repeat-grid button\{min-height:44px/); assert.match(colorWheelStyles, /\.cw-chip\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/); assert.match(fourCardPokerStyles, /\.fcp-field input\s*\{[\s\S]*?min-height:\s*44px;/);
// Require structured API failures to ignore raw server messages while preserving diagnostic fields. (I18N-011)
assert.match(apiSource, /playerSafeError\(payload\.error\?\.code, res\.status\)[\s\S]*e\.details = payload\.error\?\.details/);
// Require autoplay to reconcile authoritative sessions and separate game action from rate-limited tick retry. (AUTO-015)
assert.match(autoplaySource, /api\('\/api\/v1\/autoplay\/sessions\?active=1'\)[\s\S]*rounds_completed/); assert.match(autoplaySource, /await s\.onTick[\s\S]*await recordCompletedTick\(s\)/); assert.match(autoplaySource, /retryAfterRateLimit\(s,error,\(\)=>recordCompletedTick\(s\)\.catch/);
// Require Bingo to disclose abandonment and default to one complete call plan. (BINGO-027)
assert.match(bingoSource, /confirm\(tr\('reset\.confirmAbandon'[\s\S]*defaultRounds: TOTAL_BALLS, roundsLabel: tr\('autoplay\.calls'\)/);
// Require the shared Slots animation to stop under the platform reduced-motion preference.
assert.match(sharedStyles, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.slot-symbol\.spinning\s*\{\s*animation:\s*none;/);
// Require Baccarat reveal animation to stop under reduced motion.
assert.match(baccaratSource, /@media \(prefers-reduced-motion:reduce\)\{\.bac-card\.revealing\{animation:none;transform:none;opacity:1;\}\}/);
// Require every Bingo-owned animation and transition to stop under reduced motion.
assert.match(bingoSource, /@media \(prefers-reduced-motion:reduce\)\{\[class\*="bingo"\]\{animation:none!important;transition:none!important;\}\}/);
// Require Keno's latest-number animation to stop under reduced motion.
assert.match(kenoSource, /@media \(prefers-reduced-motion:reduce\)\{\.keno-grid button\.latest\{animation:none;transform:none;\}\}/);
// Enumerate every Roulette action whose rejection must remain player-visible.
const guardedActions = ["#mode').onchange = guarded(settings)", "#zero').onchange = guarded(settings)", "button.onclick = guarded(() => placeBetForCell(button))", "button.onclick = guarded(() => placeCall(button.dataset.call))", "button.onclick = guarded(() => clearBet(button.dataset.clear))", "#clear').onclick = guarded(clearAll)", "#rebet').onclick = guarded(rebet)", "#spin').onclick = guarded(() => spin(true))"];
// Require every governed action to stay behind the shared failure guard.
for (const action of guardedActions) assert.equal(rouletteSource.includes(action), true, action);
// Require the guard to emit both localized feedback and low-cardinality telemetry.
assert.match(rouletteSource, /toast\(error\?\.errorKey \? rt\(error\.errorKey\) : \(error\?\.playerSafe \? error\.message : rt\('errors\.actionFailed'\)\)\);[\s\S]*?logClient\('roulette_action_failed', \{ code: error\?\.code \|\| null \}\);/);
// Require the mobile Teen Patti action rail to leave the fixed feedback control unobscured.
assert.match(teenPattiStyles, /\.tp-actions,\s*\.tp-repeat\s*\{\s*width:\s*calc\(100% - 160px\);\s*max-width:\s*calc\(100% - 160px\);\s*\}/);

// Require the browser-free guards of the render-stability helpers to fail closed without a DOM. (UX-027)
assert.equal(uiModule.installStableRouteRenders(null, () => 'lobby'), false);
// Require the containment auditor to return an inert empty measurement without a real document. (UX-026)
assert.deepEqual(uiModule.auditLayoutContainment(null), { docOverflow: 0, offenders: [] });
// Require the viewport restore helper to ignore absent snapshots so route changes stay reset-only. (UX-027)
assert.equal(uiModule.restoreRouteViewportState({}, null), false);
// Require same-route render restoration to repeat after browser anchoring settles and to invalidate stale callbacks. (UX-027, TEST-155)
assert.match(uiSource, /let renderSequence=0;[\s\S]*?requestAnimationFrame\(\(\)=>\{[\s\S]*?requestAnimationFrame\(\(\)=>\{/);
// Require external focus plus fresh keyboard, pointer, wheel, or touch input to invalidate both deferred restoration callbacks. (UX-027, TEST-155)
assert.match(uiSource, /let interactionSequence=0;[\s\S]*?let restorationActive=false;[\s\S]*?addEventListener\('focusin',markFocusInteraction,[\s\S]*?addEventListener\('keydown',markInteraction,[\s\S]*?addEventListener\('pointerdown',markInteraction,[\s\S]*?addEventListener\('wheel',markInteraction,[\s\S]*?addEventListener\('touchstart',markInteraction,[\s\S]*?interaction!==interactionSequence[\s\S]*?interaction!==interactionSequence/);
// Require the shell to install the route-outlet interceptor exactly once with its consolidated post-render callback. (UX-027)
assert.match(appBootstrapSource, /installStableRouteRenders\(routeOutlet, getActive, afterRouteRender\);/);
// Require the owner console to load and save the two bounded live rate-policy fields. (SEC-015, ADMIN-032)
assert.match(adminSessionsSource, /\/api\/v2\/admin\/rate-limits[\s\S]*?admin-rate-limit-requests[\s\S]*?admin-rate-limit-window[\s\S]*?saveRateLimits/);
// Require every sound channel and game announcement to start disabled in the frontend fallback. (AUDIO-010)
assert.match(voiceSource, /AUDIO_SETTINGS=\{master_enabled:false,[\s\S]*?sfx_enabled:false,[\s\S]*?voice_enabled:false,[\s\S]*?announce_roulette_results:false,[\s\S]*?announce_blackjack_results:false,[\s\S]*?announce_baccarat_results:false,[\s\S]*?announce_bingo_calls:false,[\s\S]*?announce_keno_results:false\}/);
// Require the Admin Guest Trials surface to publish and save the owner admission switch. (GUEST-001, GUEST-004)
assert.equal(adminGuestsSource.match(/\/api\/v2\/admin\/guest-trials\/settings/g)?.length, 2);
// Require both stable admission-control identities in the extracted policy card.
assert.match(adminGuestsSource, /admin-guest-trials-enabled[\s\S]*?admin-save-guest-policy/);
// Require anonymous entry to exist only after the public provider-backed policy explicitly allows it. (GUEST-001, GUEST-002, UX-028)
assert.match(loginSource, /async function renderLoginPolicyActions[\s\S]*?policy\.guest_trials_enabled === true[\s\S]*?`<button id="guest-trial-button"/);
// Require the login template to retain the dedicated policy-owned guest slot.
assert.match(loginSource, /id="auth-guest-slot"/);
// Require unavailable provider actions to be omitted instead of rendering permanently disabled controls. (OAUTH-007, UX-028)
assert.doesNotMatch(loginSource, /data-testid="oauth-providers-disabled"/);
// Require password and guest entry to share the same terms validator and single status owner. (UX-028)
assert.match(loginSource, /function requireLoginTerms\(\)[\s\S]*?setAuthStatus\(t\('auth\.termsRequired'[\s\S]*?async function handleLoginSubmit[\s\S]*?if \(!requireLoginTerms\(\)\) return;[\s\S]*?async function handleGuestTrial[\s\S]*?if \(!requireLoginTerms\(\)\) return;/);
// Require settled containment loss to reach Admin telemetry through the frozen client-log helper. (UX-026)
assert.match(appBootstrapSource, /logClient\('layout_overflow',[\s\S]*?route: getActive\(\) \|\| 'none',[\s\S]*?viewport:/);
// Require Roulette to center and scale its fixed board through the measured continuous fit. (UX-026)
assert.match(rouletteSource, /translateX\(\$\{offsetX\.toFixed\(2\)\}px\) scale\(\$\{scale\.toFixed\(4\)\}\)/);
