// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Name the production host-only double-submit cookie without storing its value globally.
const CSRF_COOKIE = 'casino_csrf';
// Enumerate browser methods that require exact Origin plus CSRF proof.
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

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
  // Build same-origin JSON headers without retaining credentials outside the browser cookie jar.
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  // Attach the host-only double-submit value to every state-changing browser request.
  if (UNSAFE_METHODS.has(method)) headers['X-CSRF-Token'] = cookieValue(CSRF_COOKIE);
  // Store init so later code can read or update this value.
  const init = { method, headers, credentials: 'include' };
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
// Export this symbol so the shell can start an authenticated browser session.
export const login = body => post('/api/v2/auth/login', body);
// Export this symbol so the shell can end the current authenticated browser session.
export const logout = () => post('/api/v2/auth/logout', {});
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
// Export this symbol so other modules can use it through the public module boundary.
export async function logClient(event, details = {}) {
  // Start protected logic so failures can be handled safely.
  try { await post('/api/v1/log/client', { event, details, href: location.href, user_agent: navigator.userAgent }); } catch (_) {}
}
