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
// Read Teen Patti's mobile action-rail source.
const teenPattiSource = await readFile(path.join(root, 'web', 'games', 'teen_patti.js'), 'utf8');

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
// Import the exact API helper as an isolated ES module.
const apiModule = await import(`data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`);
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

// Require the persistent shell outlet to expose stable polite atomic live-region semantics.
assert.match(indexSource, /<div id="toast" class="toast" role="status" aria-live="polite" aria-atomic="true" hidden><\/div>/);
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
assert.match(rouletteSource, /toast\(error\?\.errorKey \? rt\(error\.errorKey\) : rt\('errors\.actionFailed'\)\);[\s\S]*?logClient\('roulette_action_failed', \{ code: error\?\.code \|\| null \}\);/);
// Require the mobile Teen Patti action rail to leave the fixed feedback control unobscured.
assert.match(teenPattiSource, /\.tp-actions\{width:calc\(100% - 160px\);max-width:calc\(100% - 160px\);\}/);
