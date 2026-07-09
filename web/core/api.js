// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Export this symbol so other modules can use it through the public module boundary.
export async function api(path, options = {}) {
  // Store init so later code can read or update this value.
  const init = { method: options.method || (options.body !== undefined ? 'POST' : 'GET'), headers: { 'Content-Type': 'application/json' } };
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
// Export this symbol so game modules can resolve the active player without hardcoded human state.
export function currentPlayerId() {
  // Return the authenticated shell player when the login shell has exposed one.
  return window.CasinoCurrentUser?.player_id || window.CasinoCurrentPlayer?.player_id || localStorage.getItem('casino.currentPlayerId') || 'human';
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
