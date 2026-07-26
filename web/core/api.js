// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Name the production host-only double-submit cookie without storing its value globally.
const CSRF_COOKIE = 'casino_csrf';
// Enumerate browser methods that require exact Origin plus CSRF proof.
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
// Keep the guest browser-context proof in sessionStorage so browser closure destroys it.
const GUEST_NONCE_KEY = 'casino.guestBrowserNonce';
// Keep public authentication attempts from broadcasting a protected-session expiry event.
const SESSION_EXPIRY_PUBLIC_PATHS = ['/api/v2/auth/login', '/api/v2/auth/guest'];

// Read one named cookie without exposing the complete cookie string to logs or storage.
function cookieValue(name) {
  // Find only a cookie segment whose decoded name matches the requested public identifier.
  const segment = String(document.cookie || '').split(';').map(value => value.trim()).find(value => value.startsWith(`${name}=`));
  // Return the decoded scalar value or an empty proof when no cookie exists.
  return segment ? decodeURIComponent(segment.slice(name.length + 1)) : '';
}

// Export this symbol so other modules can use it through the public module boundary.
export async function api(path, options = {}) {
  // Resolve the request method once before applying browser integrity policy.
  const method = String(options.method || (options.body !== undefined ? 'POST' : 'GET')).toUpperCase();
  // Fail closed before any authoritative request when the browser is explicitly offline. (PWA-002)
  if (navigator.onLine === false) {
    // Use one generic message because the localized PWA banner owns player-facing explanation.
    const error = new Error('Server action unavailable while offline');
    // Publish a stable low-cardinality code for callers and tests without implying success.
    error.code = 'OFFLINE';
    // Stop before fetch so no queued mutation can replay after reconnect.
    throw error;
  }
  // Build same-origin JSON headers without retaining credentials outside the browser cookie jar.
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  // Attach the context proof to every later request without copying it to durable local storage.
  const guestNonce = sessionStorage.getItem(GUEST_NONCE_KEY) || '';
  // Publish the proof only while the originating browser context remains alive.
  if (guestNonce) headers['X-Guest-Browser-Nonce'] = guestNonce;
  // Attach the host-only double-submit value to every state-changing browser request.
  if (UNSAFE_METHODS.has(method)) headers['X-CSRF-Token'] = cookieValue(CSRF_COOKIE);
  // Store init so later code can read or update this value.
  const init = { method, headers, credentials: 'include', keepalive: options.keepalive === true };
  // Branch when the following condition is true.
  if (options.body !== undefined) init.body = JSON.stringify(options.body);
  // Store res so later code can read or update this value.
  const res = await fetch(path, init);
  // Store payload; so later code can read or update this value.
  let payload;
  // Start protected logic so failures can be handled safely.
  try { payload = await res.json(); } catch (_) { throw new Error(`Bad JSON from ${path}`); }
  // Branch when the following condition is true.
  if (!res.ok || !payload.ok) {
    // Store e so later code can read or update this value.
    const e = new Error(payload.error?.message || `API error ${res.status}`);
    // Set e.code to the value needed for the next operation.
    e.code = payload.error?.code;
    // Set e.details to the value needed for the next operation.
    e.details = payload.error?.details;
    // Detect protected-session expiry without treating login or guest-start rejections as stale sessions.
    const sessionExpired = e.code === 'UNAUTHORIZED' && !SESSION_EXPIRY_PUBLIC_PATHS.some(prefix => String(path).startsWith(prefix));
    // Resolve the browser event constructor through the window object so non-browser test seams stay inert.
    const SessionExpiredEvent = globalThis.window?.CustomEvent || globalThis.CustomEvent;
    // Notify the shell after the caller's catch path settles, so game-local cleanup cannot repaint stale chrome last.
    if (sessionExpired && SessionExpiredEvent) setTimeout(() => globalThis.window?.dispatchEvent?.(new SessionExpiredEvent('casino-session-expired', { detail: { path: String(path) } })), 0);
    // Execute this statement as part of the module's documented control flow.
    throw e;
  }
  // Return the computed value to the caller.
  return payload.data;
}
// Export this symbol so other modules can use it through the public module boundary.
export const post = (path, body = {}) => api(path, { method: 'POST', body });
// Export this symbol so other modules can use it through the public module boundary.
export const del = (path, body = {}) => api(path, { method: 'DELETE', body });
// Export this symbol so the shell can read the authenticated v2 current-user payload.
export const currentUser = () => api('/api/v2/me');
// Verify logout through a raw current-user probe so the session-expired event does not race the logged-out copy.
async function sessionStillAuthenticatedAfterLogout() {
  // Request the authoritative current-user envelope using only browser-managed cookies.
  const res = await fetch('/api/v2/me', { method: 'GET', credentials: 'include', headers: { Accept: 'application/json' } });
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
export const login = body => post('/api/v2/auth/login', body);
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
  // Ask the backend to revoke the active session and expire both auth cookies.
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
  // Create the disposable principal only after the caller supplies explicit consent metadata.
  const payload = await post('/api/v2/auth/guest', body);
  // Capture the one-time proof before any protected guest request can be sent.
  sessionStorage.setItem(GUEST_NONCE_KEY, String(payload.guest_browser_nonce || ''));
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
