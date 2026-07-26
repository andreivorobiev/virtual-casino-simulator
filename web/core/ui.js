// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post, currentPlayerId, withCurrentPlayer } from './api.js';
// Import the locale-aware formatter so shared game helpers cannot leak English labels in Russian.
import { formatMoney } from './i18n.js';
// Export this symbol so other modules can display play-token amounts consistently.
export const money = n => formatMoney(n);
// Export this symbol so wallet values preserve the ledger's exact two-decimal token precision without relying on a replacement-looking glyph.
export const tokenAmount = n => Number(n || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
// Export this symbol so auth-aware shell code can render play tokens without real-money currency marks.
export const tokens = n => tokenAmount(n);
// Resolve the toast variant from either the legacy boolean flag or an explicit variant name.
// 19 game modules call toast(message,'error'); a bare truthy check rendered those failures in the
// success palette because any non-empty string is truthy. Treat only an explicit success signal as
// success so both spellings are correct and the string form can no longer invert the colour. (#423)
const toastIsSuccess = variant => variant === true || variant === 'ok' || variant === 'success';
// Export this symbol so other modules can use it through the public module boundary.
// The outlet carries its live-region semantics statically in index.html and keeps them for the life of
// the document; swapping role or aria-live at the same moment the text changes is a known way to make
// announcements unreliable, so only the text and palette change here. (#421)
export function toast(message, variant=false){ const t=document.getElementById('toast'); if(!t)return; const ok=toastIsSuccess(variant); t.textContent=message; t.style.background=ok?'#10381f':'#2b1111'; t.style.color=ok?'#c8ffd1':'#ffd3d3'; t.hidden=false; clearTimeout(toast._timer); toast._timer=setTimeout(()=>{t.hidden=true},4500); }
// Export this symbol so other modules can use it through the public module boundary.
export async function refreshBalance(){
  // Branch when the authenticated shell owns wallet rendering.
  if(window.CasinoCurrentUser){
    // Refresh the canonical current-user payload so game actions cannot leave a stale shell wallet.
    const currentUser=await api('/api/v2/me');
    // Publish the refreshed session payload for shared game and shell helpers.
    window.CasinoCurrentUser=currentUser;
    // Notify the app shell so its private session cache stays aligned with the backend.
    window.dispatchEvent(new CustomEvent('casino-current-user', { detail: currentUser }));
    // Render the current-user play-token balance instead of the legacy v1 wallet.
    renderTokenBalance(currentUser);
    // Return the refreshed player payload for legacy callers that expect a player-like object.
    return currentUser.player || {};
  }
  // Read the current player through the frozen player API.
  const d=await api(`/api/v1/players/${encodeURIComponent(currentPlayerId())}`);
  // Find the shared wallet amount node in the premium shell.
  const el=document.getElementById('balance');
  // Update the wallet amount without duplicating the label text.
  if(el) el.textContent=tokenAmount(d.player.balance);
  // Find the optional wallet label node used by the premium shell.
  const label=document.getElementById('balance-label');
  // Keep the wallet label explicit for screen readers and narrow layouts.
  if(label) label.textContent='Play token balance';
  // Return the player payload for callers that need the current balance.
  return d.player;
}
// Export this symbol so the authenticated shell can render the current-user token balance.
export function renderTokenBalance(currentUser){
  // Read the optional player object from the v2 current-user payload.
  const player=currentUser?.player || {};
  // Read the optional user object from the v2 current-user payload.
  const user=currentUser?.user || {};
  // Prefer explicit token fields while tolerating early backend payload drafts.
  const amount=player.token_balance ?? player.tokens ?? user.token_balance ?? user.tokens ?? currentUser?.token_balance ?? currentUser?.tokens?.balance ?? 0;
  // Find the shared wallet amount node in the premium shell.
  const el=document.getElementById('balance');
  // Update the wallet with a legible number while the shell medallion and label provide token context.
  if(el) el.textContent=tokenAmount(amount);
  // Find the optional wallet label node used by the premium shell.
  const label=document.getElementById('balance-label');
  // Keep the wallet label explicit for authenticated current-user sessions.
  if(label) label.textContent='Play token balance';
  // Return the normalized numeric amount for callers that need testable state.
  return Number(amount || 0);
}
// Export this symbol so callers can keep using the compatible add-money endpoint for token top-ups.
export async function addFakeMoney(amount){ const d=await post(`/api/v1/players/${encodeURIComponent(currentPlayerId())}/add-money`,withCurrentPlayer({amount})); await refreshBalance(); return d; }
// Export this symbol so other modules can use it through the public module boundary.
export function cardHtml(card){ if(!card)return''; if(card==='??') return '<div class="playing-card back">?</div>'; if(typeof card==='string'){ const suit=card.slice(-1), rank=card.slice(0,-1), red=suit==='\u2665'||suit==='\u2666'; return `<div class="playing-card ${red?'red':''}">${rank}<br>${suit}</div>`;} const red=card.suit==='\u2665'||card.suit==='\u2666'; return `<div class="playing-card ${red?'red':''}">${card.rank}<br>${card.suit}</div>`; }
// Export this symbol so other modules can use it through the public module boundary.
export function safe(s){ return String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
// Export this symbol so later game workers can reuse the approved premium tag markup.
export function renderPremiumTag(label){ return `<span class="tag">${safe(label)}</span>`; }
// Export this symbol so later game workers can reuse compact shell rail metrics.
export function renderShellMetric(label,value){ return `<div class="mini-stat"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`; }
// Export this symbol so later game workers can reuse signed ledger amount formatting.
export function signedMoney(n){ const amount=Number(n||0); return `${amount>=0?'+':'-'}${money(Math.abs(amount))}`; }
