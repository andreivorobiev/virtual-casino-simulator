// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import synchronous localization so structured API failures never expose server-English copy. (I18N-011)
import { t } from './i18n.js';
// Name the production host-only double-submit cookie without storing its value globally.
const CSRF_COOKIE = 'casino_csrf';
// Enumerate browser methods that require exact Origin plus CSRF proof.
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
// Keep the guest browser-context proof in sessionStorage so browser closure destroys it.
const GUEST_NONCE_KEY = 'casino.guestBrowserNonce';
// Keep public authentication attempts from broadcasting a protected-session expiry event.
const SESSION_EXPIRY_PUBLIC_PATHS = ['/api/v2/auth/login', '/api/v2/auth/guest'];
// Route API traffic through the native scoped hook when present while leaving browser and PWA fetch unchanged. (issue #183)
const transportFetch = (input, init) => globalThis.CasinoMobileTransport?.fetch ? globalThis.CasinoMobileTransport.fetch(input, init) : fetch(input, init);
// Detect the native OS-vault transport without reading any credential or platform secret. (MOBILE core issue #183)
const nativeSessionTransport = () => globalThis.CasinoMobileTransport?.managesSession === true;
// Retain the sole native account-switch transaction so login and guest issuance cannot interleave.
let nativeAccountSwitchInFlight = false;

// Revoke one predecessor and issue one replacement as an exclusive native account-switch action. (SESSION-013)
async function runNativeAccountSwitch(action) {
  // Preserve unchanged browser/PWA behavior when no OS-vault transport owns the session.
  if (!nativeSessionTransport()) return action();
  // Reject overlapping login or guest creation before either can mutate the native vault.
  if (nativeAccountSwitchInFlight) {
    // Stop through the existing localized conflict boundary before any predecessor mutation.
    throw playerSafeError('MOBILE_ACCOUNT_SWITCH_IN_PROGRESS', 409);
  }
  // Claim the complete prepare-through-issuance transaction synchronously before yielding.
  nativeAccountSwitchInFlight = true;
  // Run the exact native transaction while always releasing the local mutex afterward.
  try {
    // Revoke, verify, and clear any predecessor before issuing the replacement.
    await globalThis.CasinoMobileTransport.prepareAccountSwitch();
    // Return only the result from the caller's single login or guest action.
    return await action();
  // Release the process-local mutex after success or failure so an explicit later attempt may proceed.
  } finally {
    // Clear only the boolean ownership marker; no session material is retained here.
    nativeAccountSwitchInFlight = false;
  }
}
// Map stable server codes to player-safe localized categories without duplicating endpoint prose. (I18N-011)
const API_ERROR_KEYS = new Map([
  ['INSUFFICIENT_FUNDS', 'errors.insufficientTokens'],
  ['VALIDATION_ERROR', 'errors.validation'],
  ['INVALID_REQUEST', 'errors.validation'],
  ['CONFLICT', 'errors.conflict'],
  ['NOT_FOUND', 'errors.notFound'],
  ['UNAUTHORIZED', 'errors.unauthorized'],
  ['FORBIDDEN', 'errors.forbidden'],
  ['RATE_LIMITED', 'errors.rateLimited'],
  ['OFFLINE', 'errors.offline'],
  ['CSRF_BOOTSTRAP_UNAVAILABLE', 'errors.security'],
]);

// Resolve one structured API error into localized player copy while retaining its stable code separately. (I18N-011)
function localizedApiError(code, status = 0) {
  // Normalize the server code once so prefix families can share safe localized copy.
  const normalized = String(code || '').toUpperCase();
  // Use an exact stable-code mapping when the contract publishes one.
  let key = API_ERROR_KEYS.get(normalized);
  // Treat all insufficient-funds variants consistently across isolated game modules.
  if (!key && normalized.includes('INSUFFICIENT')) key = 'errors.insufficientTokens';
  // Treat validation and malformed-input variants as one player-action category.
  if (!key && (normalized.includes('INVALID') || normalized.includes('VALIDATION'))) key = 'errors.validation';
  // Fall back to transport status only when the server omitted a stable code.
  if (!key && status === 401) key = 'errors.unauthorized';
  // Keep permission failures distinct from authentication expiry.
  if (!key && status === 403) key = 'errors.forbidden';
  // Keep missing resources distinct from generic server failures.
  if (!key && status === 404) key = 'errors.notFound';
  // Keep conflicts distinct so players know to refresh current state.
  if (!key && status === 409) key = 'errors.conflict';
  // Keep throttling distinct so a player does not repeatedly retry a blocked action.
  if (!key && status === 429) key = 'errors.rateLimited';
  // Use one generic localized failure for unknown codes and server errors.
  return t(key || 'errors.actionFailed', {}, 'common');
}

// Build one explicitly player-safe browser error while retaining machine-readable diagnostics separately. (I18N-011)
function playerSafeError(code, status = 0) {
  // Create player copy only through the stable localized category resolver.
  const error = new Error(localizedApiError(code, status));
  // Retain the low-cardinality code for telemetry and caller policy without server prose.
  error.code = code || 'ACTION_FAILED';
  // Retain an optional HTTP status for bounded diagnostics.
  error.status = status;
  // Mark only this module's localized errors as safe for direct player presentation.
  error.playerSafe = true;
  // Return the fully classified browser error.
  return error;
}

// Read one named cookie without exposing the complete cookie string to logs or storage.
function cookieValue(name) {
  // Find only a cookie segment whose decoded name matches the requested public identifier.
  const segment = String(document.cookie || '').split(';').map(value => value.trim()).find(value => value.startsWith(`${name}=`));
  // Return the decoded scalar value or an empty proof when no cookie exists.
  return segment ? decodeURIComponent(segment.slice(name.length + 1)) : '';
}

// Recover a missing double-submit cookie once so a precached or restarted browser session is never stranded on the sign-in form. (issue #224)
async function ensureCsrfCookie() {
  // Native transport loads matching session CSRF only inside the OS vault and never exposes a cookie to JavaScript.
  if (nativeSessionTransport()) return;
  // Keep the fast path allocation-free when the browser already holds a proof.
  if (cookieValue(CSRF_COOKIE)) return;
  // Start protected recovery so a failed bootstrap cannot mask the caller's own error surface.
  try {
    // Ask the public bootstrap route to re-issue the host-only cookie without caching the response.
    await transportFetch('/api/v2/auth/csrf', { credentials: 'include', cache: 'no-store' });
  // Convert transport failures into the fail-closed empty-proof path below.
  } catch (_) { /* the absent-cookie check below reports the stable failure */ }
  // Fail closed with a stable code when the browser still holds no proof after one recovery attempt.
  if (!cookieValue(CSRF_COOKIE)) {
    // Use one generic message so no cookie or policy detail reaches player-facing surfaces.
    const error = playerSafeError('CSRF_BOOTSTRAP_UNAVAILABLE');
    // Stop before the mutation rather than sending an empty proof the server must reject.
    throw error;
  }
}

// Export this symbol so other modules can use it through the public module boundary.
export async function api(path, options = {}) {
  // Resolve the request method once before applying browser integrity policy.
  const method = String(options.method || (options.body !== undefined ? 'POST' : 'GET')).toUpperCase();
  // Fail closed before any authoritative request when the browser is explicitly offline. (PWA-002)
  if (!nativeSessionTransport() && navigator.onLine === false) {
    // Use one generic message because the localized PWA banner owns player-facing explanation.
    const error = playerSafeError('OFFLINE');
    // Stop before fetch so no queued mutation can replay after reconnect.
    throw error;
  }
  // Build same-origin JSON headers without retaining credentials outside the browser cookie jar.
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  // Attach the context proof to every later request without copying it to durable local storage.
  const guestNonce = sessionStorage.getItem(GUEST_NONCE_KEY) || '';
  // Publish the proof only while the originating browser context remains alive.
  if (guestNonce) headers['X-Guest-Browser-Nonce'] = guestNonce;
  // Recover a missing proof before any unsafe request can leave the browser.
  if (UNSAFE_METHODS.has(method)) await ensureCsrfCookie();
  // Attach the host-only double-submit value to every state-changing browser request.
  if (UNSAFE_METHODS.has(method) && !nativeSessionTransport()) headers['X-CSRF-Token'] = cookieValue(CSRF_COOKIE);
  // Store init so later code can read or update this value.
  const init = { method, headers, credentials: nativeSessionTransport() ? 'omit' : 'include', keepalive: options.keepalive === true };
  if (options.body !== undefined) init.body = JSON.stringify(options.body);
  // Retain the response separately so transport rejection can be converted to safe player copy.
  let res;
  // Prevent browser or network implementation details from reaching game-facing catch handlers.
  try { res = await transportFetch(path, init); } catch (_) { throw playerSafeError('OFFLINE'); }
  // Store payload; so later code can read or update this value.
  let payload;
  // Start protected logic so failures can be handled safely.
  try { payload = await res.json(); } catch (_) { throw playerSafeError('BAD_RESPONSE', res.status); }
  if (!res.ok || !payload.ok) {
    // Store e so later code can read or update this value.
    const e = playerSafeError(payload.error?.code, res.status);
    // Set e.details to the value needed for the next operation.
    e.details = payload.error?.details;
    // Detect protected-session expiry without treating login or guest-start rejections as stale sessions.
    const sessionExpired = e.code === 'UNAUTHORIZED' && !SESSION_EXPIRY_PUBLIC_PATHS.some(prefix => String(path).startsWith(prefix));
    // Resolve the browser event constructor through the window object so non-browser test seams stay inert.
    const SessionExpiredEvent = globalThis.window?.CustomEvent || globalThis.CustomEvent;
    // Notify the shell after the caller's catch path settles, so game-local cleanup cannot repaint stale chrome last.
    if (sessionExpired && SessionExpiredEvent) setTimeout(() => globalThis.window?.dispatchEvent?.(new SessionExpiredEvent('casino-session-expired', { detail: { path: String(path) } })), 0);
    throw e;
  }
  return payload.data;
}
// Export this symbol so other modules can use it through the public module boundary.
export const post = (path, body = {}) => api(path, { method: 'POST', body });
// Export this symbol so other modules can use it through the public module boundary.
export const del = (path, body = {}) => api(path, { method: 'DELETE', body });
// Preserve one already-validated transient bearer when a locale or lifecycle rerender has no new arrival. (SEC-016)
export const holdTransientBearer = (current, arrived) => String(arrived || current || '');

// Classify the exact public account route so cold and warm native links share one gate selector. (SEC-016)
export function publicAuthRouteKind(pathname) {
  // Normalize one optional trailing slash without decoding or accepting nested paths.
  const path = String(pathname || '').replace(/\/$/, '');
  // Return only the four existing public account gates; every other path stays unclassified.
  return ({ '/enroll/invitation': 'invitation', '/enroll/signup': 'signup', '/enroll/verify': 'verification', '/account/reset': 'reset' })[path] || '';
}
// Export this symbol so the shell can read the authenticated v2 current-user payload.
export const currentUser = () => api('/api/v2/me');
// Verify logout through a raw current-user probe so the session-expired event does not race the logged-out copy.
async function sessionStillAuthenticatedAfterLogout() {
  // Request authority through browser cookies or the native OS vault without mixing modes.
  const res = await transportFetch('/api/v2/me', { method: 'GET', credentials: nativeSessionTransport() ? 'omit' : 'include', headers: { Accept: 'application/json' } });
  // Store payload so the verification can distinguish a real 401 from a broken response.
  let payload;
  // Parse the standard envelope before deciding whether logout really completed.
  try { payload = await res.json(); } catch (_) {
    // Report malformed verification as an indeterminate logout rather than pretending success.
    const error = new Error('Logout verification returned invalid JSON');
    // Publish a stable low-cardinality code for UI and tests.
    error.code = 'LOGOUT_VERIFY_BAD_JSON';
    // Stop the caller before it clears authenticated chrome.
    throw error;
  }
  // Treat the planned unauthorized envelope as proof that the session is gone.
  if (res.status === 401 && payload?.ok === false) return false;
  // Treat any successful current-user envelope as proof that the session survived logout.
  if (res.ok && payload?.ok === true) return true;
  // Build an indeterminate verification error for server or proxy failures.
  const error = new Error(payload?.error?.message || `Logout verification failed with HTTP ${res.status}`);
  // Preserve the server code when one exists, otherwise publish the transport status.
  error.code = payload?.error?.code || `LOGOUT_VERIFY_${res.status}`;
  // Stop the caller before it clears authenticated chrome.
  throw error;
}
// Export this symbol so the shell can start an authenticated browser session.
export const login = async body => {
  // Keep native predecessor revocation and replacement issuance inside one exclusive transaction.
  return runNativeAccountSwitch(() => post('/api/v2/auth/login', body));
};
// Read boolean-only provider availability for the logged-out sign-in surface. (OAUTH-007)
export const oauthProviders = () => api('/api/v2/auth/oauth/providers');
// Start one browser-bound sign-in or explicitly confirmed authenticated link flow. (OAUTH-008)
export const startOAuth = (provider, body) => post(`/api/v2/auth/oauth/${encodeURIComponent(provider)}/start`, body);
// Read authenticated boolean-only provider-link state without provider subjects. (OAUTH-009)
export const oauthLinks = () => api('/api/v2/me/oauth/providers');
// Remove one current-user provider link after explicit confirmation. (OAUTH-010)
export const unlinkOAuth = provider => post(`/api/v2/me/oauth/${encodeURIComponent(provider)}/unlink`, { confirm_unlink: true });
// Redeem one disabled-by-default private invitation through the additive v2 boundary. (INVITE-003)
export const redeemInvitation = body => post('/api/v2/auth/redeem-invitation', body);
// Export this symbol so the shell can end the current authenticated browser session.
export async function logout() {
  // Ask the backend to revoke the session; only browser mode emits cookie expiry.
  const result = await post('/api/v2/auth/logout', {});
  // Re-read current user outside the normal helper so verification cannot repaint the wrong gate.
  const stillAuthenticated = await sessionStillAuthenticatedAfterLogout();
  // Fail closed when the browser still has a usable session after the logout endpoint returned.
  if (stillAuthenticated) {
    // Explain the mismatch without exposing token or cookie material.
    const error = new Error('Logout did not clear the active browser session');
    // Publish a stable code so browser-free tests can lock the regression.
    error.code = 'LOGOUT_STILL_AUTHENTICATED';
    // Stop the shell from rendering a false logged-out state.
    throw error;
  }
  // Return the backend acknowledgement after the browser independently proved the session is gone.
  return result;
}
// Start one account-free disposable guest trial from the login surface. (issue #317)
export async function guestTrial(body) {
  // Revoke and replace a native predecessor atomically with guest issuance under the local mutex.
  const payload = await runNativeAccountSwitch(() => post('/api/v2/auth/guest', body));
  // Capture the one-time proof before any protected guest request can be sent.
  if (!nativeSessionTransport()) sessionStorage.setItem(GUEST_NONCE_KEY, String(payload.guest_browser_nonce || ''));
  // Remove the transport-only proof from application state and UI inspection surfaces.
  delete payload.guest_browser_nonce;
  // Return the standard current-user payload consumed by the shell.
  return payload;
}
// Irreversibly end the current guest trial with no recovery path. (issue #317)
export async function endGuestTrial() {
  // End the authenticated guest while the browser-context proof is still available.
  const result = await post('/api/v2/auth/guest/end', {});
  // Destroy the context proof after the server has irreversibly revoked the trial.
  sessionStorage.removeItem(GUEST_NONCE_KEY);
  // Return the identifier-free acknowledgement to the shell.
  return result;
}
// Send a best-effort lifecycle marker while preserving sessionStorage across same-context reloads.
export const departGuestTrial = () => api('/api/v2/auth/guest/depart', { method: 'POST', body: {}, keepalive: true });
// Export this symbol so the shell can acknowledge the private beta toy-simulator terms.
export const acceptTerms = body => post('/api/v2/auth/terms/accept', body);
// Export this symbol so the shell can request ledger-backed token additions for the current user.
export const addUserTokens = body => post('/api/v2/me/tokens/add', body);
// Export this symbol so game modules can resolve the active player without hardcoded human state.
export function currentPlayerId() {
  // Store the authenticated shell player when the login shell has exposed one.
  const shellPlayer = window.CasinoCurrentUser?.player || window.CasinoCurrentPlayer || {};
  // Return the authenticated player id, an explicit browser override, or the legacy human fallback.
  return shellPlayer.player_id || window.CasinoCurrentUser?.player_id || localStorage.getItem('casino.currentPlayerId') || 'human';
}
// Export this symbol so v1 GET endpoints can receive the current player as an additive query value.
export function currentPlayerPath(path) {
  // Store separator so paths with existing query strings remain valid.
  const separator = path.includes('?') ? '&' : '?';
  // Return the path with a current-player query parameter.
  return `${path}${separator}player_id=${encodeURIComponent(currentPlayerId())}`;
}
// Export this symbol so action payloads use the current player while preserving explicit overrides.
export function withCurrentPlayer(body = {}) {
  // Return a payload that defaults to the active player without replacing caller-supplied ids.
  return { player_id: currentPlayerId(), ...body };
}
// Reduce a location to origin and path so no query secret can reach admin-visible client logs.
// Every window error and unhandled rejection auto-logs this value, and the invitation route carries a
// single-use enrollment bearer in ?token=..., so the raw href wrote a live credential into telemetry
// that an admin (or anyone reading exfiltrated logs) could redeem. The OAuth flow already strips its
// completion markers for the same reason; this closes the equivalent gap. (issue #417)
function loggableHref() {
  // Start protected parsing so a malformed URL can never break error reporting.
  try {
    // Rebuild from the parsed URL so query and fragment are dropped rather than filtered.
    const url = new URL(location.href);
    // Return only the non-secret-bearing portion of the address.
    return `${url.origin}${url.pathname}`;
  // Fall back to a fixed placeholder rather than risking the raw address.
  } catch (_) {
    // Publish a stable marker so log consumers can distinguish this from a missing field.
    return 'unavailable';
  }
}
// Export this symbol so other modules can use it through the public module boundary.
export async function logClient(event, details = {}) {
  // Start protected logic so failures can be handled safely.
  try { await post('/api/v1/log/client', { event, details, href: loggableHref(), user_agent: navigator.userAgent }); } catch (_) {}
}
