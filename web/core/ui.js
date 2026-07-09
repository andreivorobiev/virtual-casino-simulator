// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post } from './api.js';
// Export this symbol so other modules can use it through the public module boundary.
export const money = n => `$${Number(n || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`;
// Export this symbol so other modules can use it through the public module boundary.
export function toast(message, ok=false){ const t=document.getElementById('toast'); if(!t)return; t.textContent=message; t.style.background=ok?'#10381f':'#2b1111'; t.style.color=ok?'#c8ffd1':'#ffd3d3'; t.hidden=false; clearTimeout(toast._timer); toast._timer=setTimeout(()=>{t.hidden=true},4500); }
// Export this symbol so other modules can use it through the public module boundary.
export async function refreshBalance(){
  // Read the human player through the frozen player API.
  const d=await api('/api/v1/players/human');
  // Find the shared wallet amount node in the premium shell.
  const el=document.getElementById('balance');
  // Update the wallet amount without duplicating the label text.
  if(el) el.textContent=money(d.player.balance);
  // Find the optional wallet label node used by the premium shell.
  const label=document.getElementById('balance-label');
  // Keep the wallet label explicit for screen readers and narrow layouts.
  if(label) label.textContent='Human balance';
  // Return the player payload for callers that need the current balance.
  return d.player;
}
// Export this symbol so other modules can use it through the public module boundary.
export async function addFakeMoney(amount){ const d=await post('/api/v1/players/human/add-money',{amount}); await refreshBalance(); return d; }
// Export this symbol so other modules can use it through the public module boundary.
export function cardHtml(card){ if(!card)return''; if(card==='??') return '<div class="playing-card back">?</div>'; if(typeof card==='string'){ const suit=card.slice(-1), rank=card.slice(0,-1), red=suit==='♥'||suit==='♦'; return `<div class="playing-card ${red?'red':''}">${rank}<br>${suit}</div>`;} const red=card.suit==='♥'||card.suit==='♦'; return `<div class="playing-card ${red?'red':''}">${card.rank}<br>${card.suit}</div>`; }
// Export this symbol so other modules can use it through the public module boundary.
export function safe(s){ return String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
// Export this symbol so later game workers can reuse the approved premium tag markup.
export function renderPremiumTag(label){ return `<span class="tag">${safe(label)}</span>`; }
// Export this symbol so later game workers can reuse compact shell rail metrics.
export function renderShellMetric(label,value){ return `<div class="mini-stat"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`; }
// Export this symbol so later game workers can reuse signed ledger amount formatting.
export function signedMoney(n){ const amount=Number(n||0); return `${amount>=0?'+':'-'}${money(Math.abs(amount))}`; }
