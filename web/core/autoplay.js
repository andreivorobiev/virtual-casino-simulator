// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Shared autoplay controls, session polling, and stop-safe player interactions.
import { api, post, currentPlayerId } from './api.js';
// Import the loaded common dictionary so start failures use player-facing localized copy.
import { t } from './i18n.js';
// Store sessions so later code can read or update this value.
const sessions = window.__casinoAutoplaySessions || new Map();
// Set window.__casinoAutoplaySessions to the value needed for the next operation.
window.__casinoAutoplaySessions = sessions;
// Store delayMs so later code can read or update this value.
const delayMs = speed => ({slow:2200,medium:900,fast:260}[speed] || 900);
// Bound exponential rate-limit pauses so a legitimate long autoplay can resume without hammering the API. (AUTO-015)
const rateLimitDelayMs = attempt => Math.min(15000, 1000 * (2 ** Math.min(attempt, 4)));
// Define the dispatch function that implements this UI or API behavior.
function dispatch(msg){ window.dispatchEvent(new CustomEvent('casino-toast',{detail:{message:msg}})); }
// Define the getSession function that implements this UI or API behavior.
function getSession(id){ if(!sessions.has(id)) sessions.set(id,{id,starting:false,running:false,stopRequested:false,remaining:0,requestedRounds:25,speed:'medium',timer:null,serverId:null,rateLimitRetries:0,boxes:new Set(),onTick:null}); return sessions.get(id); }
// Define the setUi function that implements this UI or API behavior.
function setUi(s){
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
// Identify only the stable API rate-limit response that is safe to retry after its bounded pause. (AUTO-015)
function isRateLimited(error){ return error?.code==='RATE_LIMITED' || error?.status===429; }
// Preserve the authoritative session and exact resume phase while the shared API window recovers. (AUTO-015)
function retryAfterRateLimit(s,error,resume){
  // Let ordinary product, network, and validation failures follow the existing stop path.
  if(!isRateLimited(error)) return false;
  // Compute the current bounded delay before advancing the retry counter.
  const wait=rateLimitDelayMs(s.rateLimitRetries);
  // Count consecutive limiter responses so subsequent retries back off without becoming unbounded.
  s.rateLimitRetries += 1;
  // Replace any older timer so exactly one continuation remains scheduled.
  clearTimeout(s.timer);
  // Resume the precise failed phase without replaying a previously completed game action.
  s.timer=setTimeout(()=>{ s.timer=null; return resume(); },wait);
  // Keep the UI truthfully running because a bounded continuation now exists.
  setUi(s);
  // Tell the caller that the rate-limit response has been safely retained for retry.
  return true;
}
// Define the finishStop function that implements this UI or API behavior.
async function finishStop(s){
  // Start protected lifecycle completion so a temporary limiter response cannot strand a running badge. (AUTO-015)
  try{
    // Complete the authoritative stop before discarding the resumable server identity. (AUTO-015)
    if(s.serverId) await post('/api/v1/autoplay/finish-stop',{autoplay_id:s.serverId});
  // Preserve the authoritative id and retry only finish-stop when the shared window is temporarily full.
  }catch(error){ if(retryAfterRateLimit(s,error,()=>finishStop(s).catch(failure=>dispatch(failure.message)))) return; throw error; }
  // Clear the server identity only after the lifecycle endpoint commits successfully. (AUTO-015)
  s.serverId=null;
  // Reset limiter backoff after the authoritative lifecycle transition succeeds.
  s.rateLimitRetries=0;
  // Set the truthful idle client state after authoritative completion.
  s.starting=false; s.running=false; s.stopRequested=false; clearTimeout(s.timer); s.timer=null; setUi(s);
}
// Record one already-completed game action without ever replaying that ledger-bearing action. (AUTO-015)
async function recordCompletedTick(s){
  // Start protected server bookkeeping so a temporary limiter response retains the completed phase.
  try{
    // Record exactly one server tick for the game action that already completed successfully.
    if(s.serverId) await post('/api/v1/autoplay/tick',{autoplay_id:s.serverId});
  // Retry only bookkeeping after a limiter response because replaying onTick could duplicate a wager.
  }catch(error){ if(retryAfterRateLimit(s,error,()=>recordCompletedTick(s).catch(failure=>dispatch(failure.message)))) return; await stopAfterFailure(s,error); return; }
  // Reset limiter backoff only after both the action and its authoritative tick are complete.
  s.rateLimitRetries=0;
  // Consume exactly one remaining action after its server tick commits.
  s.remaining -= 1; setUi(s);
  // Finish the lifecycle immediately when the requested plan is complete or a stop arrived in flight.
  if(s.stopRequested || s.remaining<=0){ await finishStop(s); return; }
  // Schedule the next new game action at the retained player-selected speed.
  s.timer=setTimeout(()=>loop(s), delayMs(s.speed));
}
// Stop a non-rate-limited failed autoplay without changing its existing fail-closed lifecycle semantics.
async function stopAfterFailure(s,error){
  // Surface the stable player-safe failure copy supplied by the shared API helper.
  dispatch(error.message || 'Auto play stopped.');
  // Keep every mounted badge truthful while authoritative failure cleanup completes.
  s.stopRequested=true; setUi(s);
  // Request an authoritative stop when a server session was already registered.
  if(s.serverId){ try{ await post('/api/v1/autoplay/stop',{autoplay_id:s.serverId}); }catch{} }
  // Finish the authoritative lifecycle before allowing another autoplay registration.
  await finishStop(s);
}
// Define the loop function that implements this UI or API behavior.
async function loop(s){
  if(!s.running) return;
  // Set if(s.serverId){ try{ const d to the value needed for the next operation.
  if(s.serverId){ try{ const d=await api(`/api/v1/autoplay/sessions/${s.serverId}`); if(d.session?.stop_requested || d.session?.status==='stop_requested') s.stopRequested=true; }catch{} }
  // Set if(s.stopRequested || s.remaining< to the value needed for the next operation.
  if(s.stopRequested || s.remaining<=0){ await finishStop(s); return; }
  // Start protected logic so failures can be handled safely.
  try{
    // Set await s.onTick?.({autoplay_id:s.serverId, speed:s.speed, sto to the value needed for the next operation.
    await s.onTick?.({autoplay_id:s.serverId, speed:s.speed, stopRequested:()=>s.stopRequested});
  // Retry the game action only when the limiter rejected it before route mutation.
  }catch(error){ if(retryAfterRateLimit(s,error,()=>loop(s).catch(failure=>dispatch(failure.message)))) return; await stopAfterFailure(s,error); return; }
  // Continue with tick bookkeeping in a separate phase so this completed action cannot be replayed.
  await recordCompletedTick(s);
}
// Export this symbol so other modules can use it through the public module boundary.
export function stopAutoplay(id){ const s=getSession(id); s.stopRequested=true; clearTimeout(s.timer); s.timer=null; setUi(s); if(s.serverId) post('/api/v1/autoplay/stop',{autoplay_id:s.serverId}).catch(error=>dispatch(error.message)); setTimeout(()=>finishStop(s).catch(error=>dispatch(error.message)),30); }
// Export this symbol so other modules can use it through the public module boundary.
export function stopAllAutoplay(){ for(const id of sessions.keys()) stopAutoplay(id); post('/api/v1/autoplay/stop-all',{}).catch(()=>{}); }
// Export this symbol so other modules can use it through the public module boundary.
export function renderAutoplay({id,onTick,plan={},defaultRounds=25,roundsLabel='Rounds'}){
  // Store s so later code can read or update this value.
  const s=getSession(id); s.onTick=onTick; if(!s.running && !s.starting && s.remaining<=0) s.requestedRounds=defaultRounds;
  // Store box so later code can read or update this value.
  const box=document.createElement('div'); box.className='autoplay'; box.id=`${id}Auto`; box.dataset.testid=`autoplay-${id}`;
  // Set box.innerHTML to the value needed for the next operation.
  box.innerHTML=`<div class="row"><h3>Auto play</h3><span class="badge">Off</span></div><div class="row"><label>Speed <select class="speed" data-testid="${id}-auto-speed"><option value="slow">Slow</option><option value="medium">Medium</option><option value="fast">Fast</option></select></label><label>${roundsLabel} <input class="rounds" data-testid="${id}-auto-rounds" type="number" min="1" max="10000" value="${s.requestedRounds}"></label></div><div class="row"><button class="start" data-testid="${id}-auto-start">Start auto</button><button class="stop" data-testid="${id}-auto-stop" disabled>Stop</button></div>`;
  // Restore the retained speed after a game rerender recreates the widget. (AUTO-015)
  box.querySelector('.speed').value=s.speed;
  s.boxes.add(box);
  // Set box.querySelector('.start').onclick to the value needed for the next operation.
  box.querySelector('.start').onclick=async()=>{
    if(s.starting || s.running) return;
    // Set s.remaining to the value needed for the next operation.
    s.remaining=Math.max(1, Number(box.querySelector('.rounds').value||1)); s.requestedRounds=s.remaining;
    // Set s.speed to the value needed for the next operation.
    s.speed=box.querySelector('.speed').value;
    // Set s.stopRequested to the value needed for the next operation.
    s.stopRequested=false; s.rateLimitRetries=0; s.starting=true; s.running=false; setUi(s);
    // Start protected logic so failures can be handled safely.
    try{
      // Reconcile a retained server session before creating a conflicting duplicate. (AUTO-015)
      const active=await api('/api/v1/autoplay/sessions?active=1');
      // Match only the current game and authenticated player scope returned by the server.
      const retained=(active.sessions || []).find(session=>session.game_id===id && ['running','stop_requested'].includes(session.status));
      // Resume the authoritative id and remaining count when a prior widget refresh lost local timing state.
      if(retained){ s.serverId=retained.autoplay_id; s.speed=retained.speed || s.speed; s.remaining=Math.max(0,Number(retained.round_limit || 0)-Number(retained.rounds_completed || 0)); s.requestedRounds=Number(retained.round_limit || s.requestedRounds); s.stopRequested=Boolean(retained.stop_requested); s.starting=false; s.running=!s.stopRequested && s.remaining>0; setUi(s); if(s.running) loop(s); else await finishStop(s); return; }
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
  setUi(s);
  // Set box.addEventListener('DOMNodeRemovedFromDocument',() to the value needed for the next operation.
  box.addEventListener('DOMNodeRemovedFromDocument',()=>s.boxes.delete(box));
  return box;
}
