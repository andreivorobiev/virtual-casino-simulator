// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post, currentPlayerId } from './api.js';
// Import the loaded common dictionary so start failures use player-facing localized copy.
import { t } from './i18n.js';
// Store sessions so later code can read or update this value.
const sessions = window.__casinoAutoplaySessions || new Map();
// Set window.__casinoAutoplaySessions to the value needed for the next operation.
window.__casinoAutoplaySessions = sessions;
// Store delayMs so later code can read or update this value.
const delayMs = speed => ({slow:2200,medium:900,fast:260}[speed] || 900);
// Define the dispatch function that implements this UI or API behavior.
function dispatch(msg){ window.dispatchEvent(new CustomEvent('casino-toast',{detail:{message:msg}})); }
// Define the getSession function that implements this UI or API behavior.
function getSession(id){ if(!sessions.has(id)) sessions.set(id,{id,starting:false,running:false,stopRequested:false,remaining:0,speed:'medium',timer:null,serverId:null,boxes:new Set(),onTick:null}); return sessions.get(id); }
// Define the setUi function that implements this UI or API behavior.
function setUi(s){
  // Execute this statement as part of the module's documented control flow.
  for(const box of s.boxes){
    // Store badge so later code can read or update this value.
    const badge=box.querySelector('.badge'), start=box.querySelector('.start'), stop=box.querySelector('.stop'), rounds=box.querySelector('.rounds'), speed=box.querySelector('.speed');
    // Set if(badge) badge.textContent to the value needed for the next operation.
    if(badge) badge.textContent=s.starting?'Starting...':(s.running?(s.stopRequested?'Stopping...':`Running ${s.remaining}`):'Off');
    // Set if(start) start.disabled to the value needed for the next operation.
    if(start) start.disabled=s.starting || s.running;
    // Set if(stop) stop.disabled to the value needed for the next operation.
    if(stop) stop.disabled=s.starting || !s.running;
    // Set if(rounds) rounds.disabled to the value needed for the next operation.
    if(rounds) rounds.disabled=s.starting || s.running;
    // Set if(speed) speed.disabled to the value needed for the next operation.
    if(speed) speed.disabled=s.starting || s.running;
  }
}
// Define the finishStop function that implements this UI or API behavior.
async function finishStop(s){
  // Execute this statement as part of the module's documented control flow.
  if(s.serverId){ try{ await post('/api/v1/autoplay/finish-stop',{autoplay_id:s.serverId}); }catch{} }
  // Set s.running to the value needed for the next operation.
  s.starting=false; s.running=false; s.stopRequested=false; clearTimeout(s.timer); s.timer=null; setUi(s);
}
// Define the loop function that implements this UI or API behavior.
async function loop(s){
  // Execute this statement as part of the module's documented control flow.
  if(!s.running) return;
  // Set if(s.serverId){ try{ const d to the value needed for the next operation.
  if(s.serverId){ try{ const d=await api(`/api/v1/autoplay/sessions/${s.serverId}`); if(d.session?.stop_requested || d.session?.status==='stop_requested') s.stopRequested=true; }catch{} }
  // Set if(s.stopRequested || s.remaining< to the value needed for the next operation.
  if(s.stopRequested || s.remaining<=0){ await finishStop(s); return; }
  // Start protected logic so failures can be handled safely.
  try{
    // Set await s.onTick?.({autoplay_id:s.serverId, speed:s.speed, sto to the value needed for the next operation.
    await s.onTick?.({autoplay_id:s.serverId, speed:s.speed, stopRequested:()=>s.stopRequested});
    // Execute this statement as part of the module's documented control flow.
    if(s.serverId){ try{ await post('/api/v1/autoplay/tick',{autoplay_id:s.serverId}); }catch{} }
    // Set s.remaining - to the value needed for the next operation.
    s.remaining -= 1; setUi(s);
  // Explain this executable/data line so future Codex changes preserve intent.
  }catch(e){ dispatch(e.message || 'Auto play stopped.'); if(s.serverId){ try{ await post('/api/v1/autoplay/stop',{autoplay_id:s.serverId}); }catch{} } await finishStop(s); return; }
  // Set if(s.stopRequested || s.remaining< to the value needed for the next operation.
  if(s.stopRequested || s.remaining<=0){ await finishStop(s); return; }
  // Set s.timer to the value needed for the next operation.
  s.timer=setTimeout(()=>loop(s), delayMs(s.speed));
}
// Export this symbol so other modules can use it through the public module boundary.
export function stopAutoplay(id){ const s=getSession(id); s.stopRequested=true; clearTimeout(s.timer); s.timer=null; setUi(s); if(s.serverId) post('/api/v1/autoplay/stop',{autoplay_id:s.serverId}).catch(()=>{}); setTimeout(()=>finishStop(s),30); }
// Export this symbol so other modules can use it through the public module boundary.
export function stopAllAutoplay(){ for(const id of sessions.keys()) stopAutoplay(id); post('/api/v1/autoplay/stop-all',{}).catch(()=>{}); }
// Export this symbol so other modules can use it through the public module boundary.
export function renderAutoplay({id,onTick,plan={}}){
  // Store s so later code can read or update this value.
  const s=getSession(id); s.onTick=onTick;
  // Store box so later code can read or update this value.
  const box=document.createElement('div'); box.className='autoplay'; box.id=`${id}Auto`; box.dataset.testid=`autoplay-${id}`;
  // Set box.innerHTML to the value needed for the next operation.
  box.innerHTML=`<div class="row"><h3>Auto play</h3><span class="badge">Off</span></div><div class="row"><label>Speed <select class="speed" data-testid="${id}-auto-speed"><option value="slow">Slow</option><option selected value="medium">Medium</option><option value="fast">Fast</option></select></label><label>Rounds <input class="rounds" data-testid="${id}-auto-rounds" type="number" min="1" max="10000" value="25"></label></div><div class="row"><button class="start" data-testid="${id}-auto-start">Start auto</button><button class="stop" data-testid="${id}-auto-stop" disabled>Stop</button></div>`;
  // Execute this statement as part of the module's documented control flow.
  s.boxes.add(box);
  // Set box.querySelector('.start').onclick to the value needed for the next operation.
  box.querySelector('.start').onclick=async()=>{
    // Execute this statement as part of the module's documented control flow.
    if(s.starting || s.running) return;
    // Set s.remaining to the value needed for the next operation.
    s.remaining=Math.max(1, Number(box.querySelector('.rounds').value||1));
    // Set s.speed to the value needed for the next operation.
    s.speed=box.querySelector('.speed').value;
    // Set s.stopRequested to the value needed for the next operation.
    s.stopRequested=false; s.serverId=null; s.starting=true; s.running=false; setUi(s);
    // Start protected logic so failures can be handled safely.
    try{
      // Register server authority before any ledger-bearing game tick can begin.
      const d=await post('/api/v1/autoplay/start',{game_id:id,player_id:currentPlayerId(),speed:s.speed,round_limit:s.remaining,plan});
      // Reject malformed success payloads rather than starting without an autoplay identity.
      if(!d.session?.autoplay_id) throw new Error('AUTOPLAY_ID_MISSING');
      // Retain the server identity used by tick and stop requests.
      s.serverId=d.session.autoplay_id;
      // Transition from truthful Starting state only after registration succeeds.
      s.starting=false; s.running=true; setUi(s);
    // Recover to a truthful idle state when registration is rejected or unreachable.
    }catch(e){
      // Clear every client-run field so no timer or stale server identity can survive failure.
      s.serverId=null; s.starting=false; s.running=false; s.stopRequested=false; s.remaining=0; clearTimeout(s.timer); s.timer=null;
      // Restore Start and keep Stop unavailable before reporting the failure.
      setUi(s);
      // Surface sanitized localized copy without exposing raw network or server details.
      dispatch(t('errors.autoplayStartFailed',{},'common'));
      // Stop before loop so no game action can be placed without server authority.
      return;
    }
    // Begin client ticks only after a valid server autoplay id is retained.
    loop(s);
  };
  // Set box.querySelector('.stop').onclick to the value needed for the next operation.
  box.querySelector('.stop').onclick=()=>stopAutoplay(id);
  // Set box._stop to the value needed for the next operation.
  box._stop=()=>stopAutoplay(id);
  // Execute this statement as part of the module's documented control flow.
  setUi(s);
  // Set box.addEventListener('DOMNodeRemovedFromDocument',() to the value needed for the next operation.
  box.addEventListener('DOMNodeRemovedFromDocument',()=>s.boxes.delete(box));
  // Return the computed value to the caller.
  return box;
}
