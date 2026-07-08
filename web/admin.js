// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post } from './core/api.js';
// Import required dependency so this module can use its public functions or constants.
import { money, safe, toast } from './core/ui.js';
// Import required dependency so this module can use its public functions or constants.
import { availableVoices, loadVoiceSettings, saveVoiceSettings, speak } from './core/voice.js';
// Store current so later code can read or update this value.
let current='dashboard';
// Store view so later code can read or update this value.
const view=document.getElementById('adminView'), title=document.getElementById('adminTitle'), subtitle=document.getElementById('adminSubtitle');
// Store pre so later code can read or update this value.
const pre=o=>`<pre class="logview">${safe(JSON.stringify(o,null,2))}</pre>`;
// Store table so later code can read or update this value.
const table=(heads,rows)=>`<table class="mini-table"><tr>${heads.map(h=>`<th>${safe(h)}</th>`).join('')}</tr>${rows.join('')}</table>`;
// Define the activate function that implements this UI or API behavior.
function activate(tab){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('gold',b.dataset.tab===tab)); current=tab; load(tab);}
// Set document.querySelectorAll('[data-tab]').forEach(b to the value needed for the next operation.
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>activate(b.dataset.tab));
// Set document.getElementById('refreshAdmin').onclick to the value needed for the next operation.
document.getElementById('refreshAdmin').onclick=()=>load(current);
// Define the load function that implements this UI or API behavior.
async function load(tab='dashboard'){
 // Start protected logic so failures can be handled safely.
 try{
  // Set if(tab to the value needed for the next operation.
  if(tab==='dashboard') return dashboard();
  // Set if(tab to the value needed for the next operation.
  if(tab==='players') return playersBots();
  // Set if(tab to the value needed for the next operation.
  if(tab==='ledger') return ledger();
  // Set if(tab to the value needed for the next operation.
  if(tab==='history') return history();
  // Set if(tab to the value needed for the next operation.
  if(tab==='telemetry') return telemetry();
  // Set if(tab to the value needed for the next operation.
  if(tab==='states') return states();
  // Set if(tab to the value needed for the next operation.
  if(tab==='audio') return audio();
  // Set if(tab to the value needed for the next operation.
  if(tab==='autoplay') return autoplay();
  // Set if(tab to the value needed for the next operation.
  if(tab==='requirements') return requirements();
  // Set if(tab to the value needed for the next operation.
  if(tab==='tests') return tests();
  // Set if(tab to the value needed for the next operation.
  if(tab==='system') return system();
 // Set }catch(e){view.innerHTML to the value needed for the next operation.
 }catch(e){view.innerHTML=`<div class="admin-card danger"><h2>Admin error</h2><p>${safe(e.message)}</p></div>`;}
}
// Define the setTitle function that implements this UI or API behavior.
function setTitle(t,s){title.textContent=t; subtitle.textContent=s||'';}
// Define the dashboard function that implements this UI or API behavior.
async function dashboard(){setTitle('Dashboard','System health, balances, telemetry, and recent events.'); const d=await api('/api/v1/admin/dashboard'); const active=(d.autoplay_sessions||[]).filter(s=>['running','stop_requested','paused','starting'].includes(s.status)); view.innerHTML=`<div class="admin-card-grid"><div class="admin-card"><b>App</b><h2>${safe(d.app_version)}</h2></div><div class="admin-card"><b>Players</b><h2>${d.players.length}</h2></div><div class="admin-card"><b>Bots</b><h2>${d.bots.length}</h2></div><div class="admin-card"><b>Active autoplay</b><h2>${active.length}</h2></div><div class="admin-card"><b>Errors today</b><h2>${(d.logs.errors||[]).length}</h2></div><div class="admin-card"><b>Requirements</b><h2>${Object.values(d.requirement_counts||{}).reduce((a,b)=>a+b,0)}</h2></div></div><div class="admin-split"><section class="admin-card"><h3>Recent ledger</h3>${table(['Time','Player','Game','Type','Amount'],(d.recent_ledger||[]).slice(-12).reverse().map(r=>`<tr><td>${safe(r.ts)}</td><td>${safe(r.player_id)}</td><td>${safe(r.game)}</td><td>${safe(r.transaction_type)}</td><td>${money(r.amount)}</td></tr>`))}</section><section class="admin-card"><h3>Recent errors</h3>${pre(d.logs.errors||[])}</section></div>`;}
// Define the playersBots function that implements this UI or API behavior.
async function playersBots(){setTitle('Players & Bots','Bots are controllers for player accounts. Strategies are assigned here, not inside games.'); const d=await api('/api/v1/admin/dashboard'); const caps=d.bot_capabilities||{}; const gameOptions=Object.keys(caps).filter(g=>caps[g].supports_bots); view.innerHTML=`<section class="admin-card"><h3>Players</h3>${table(['ID','Name','Type','Balance'],(d.players||[]).map(p=>`<tr><td>${safe(p.player_id)}</td><td>${safe(p.display_name)}</td><td>${safe(p.type)}</td><td>${money(p.balance)}</td></tr>`))}</section><section class="admin-card"><h3>Bot controllers</h3>${(d.bots||[]).map(b=>`<div class="bot-edit" data-bot="${b.bot_id}"><div class="row"><b>${safe(b.display_name)}</b><label><input type="checkbox" class="bot-enabled" ${b.enabled?'checked':''}> Enabled</label><span class="badge">${money(b.balance)}</span></div>${gameOptions.map(g=>`<div class="row"><label>${safe(g)} strategy <select class="bot-strategy" data-game="${g}">${caps[g].strategies.map(s=>`<option value="${s.id}" ${b.strategies?.[g]===s.id?'selected':''}>${safe(s.label)}</option>`).join('')}</select></label><label>Stake <input class="bot-stake" data-game="${g}" type="number" min="1" value="${b.stakes?.[g]||5}"></label></div>`).join('')}<button class="save-bot" data-bot="${b.bot_id}">Save ${safe(b.display_name)}</button></div>`).join('')}</section>`; view.querySelectorAll('.save-bot').forEach(btn=>btn.onclick=async()=>{const box=btn.closest('.bot-edit'), id=btn.dataset.bot; const strategies={}, stakes={}; box.querySelectorAll('.bot-strategy').forEach(s=>strategies[s.dataset.game]=s.value); box.querySelectorAll('.bot-stake').forEach(s=>stakes[s.dataset.game]=Number(s.value||1)); await post(`/api/v1/bots/${id}`,{enabled:box.querySelector('.bot-enabled').checked,strategies,stakes}); toast('Bot settings saved.',true); playersBots();});}
// Define the ledger function that implements this UI or API behavior.
async function ledger(){setTitle('Ledger','Money movement audit log.'); const d=await api('/api/v1/admin/ledger?limit=500'); view.innerHTML=`<section class="admin-card"><h3>Ledger</h3>${table(['Time','Player','Game','Round','Type','Amount','Before','After'],(d.ledger||[]).slice().reverse().map(r=>`<tr><td>${safe(r.ts)}</td><td>${safe(r.player_id)}</td><td>${safe(r.game)}</td><td>${safe(r.round_id)}</td><td>${safe(r.transaction_type)}</td><td>${money(r.amount)}</td><td>${money(r.balance_before)}</td><td>${money(r.balance_after)}</td></tr>`))}</section>`;}
// Define the history function that implements this UI or API behavior.
async function history(){setTitle('History','Cross-game CSV history rows.'); const d=await api('/api/v1/admin/history?limit=500'); view.innerHTML=`<section class="admin-card"><h3>History</h3>${pre(d.history||[])}</section>`;}
// Define the telemetry function that implements this UI or API behavior.
async function telemetry(){setTitle('Telemetry','Application, error, and browser-client logs.'); const app=await api('/api/v1/admin/logs?kind=app&limit=200'); const errors=await api('/api/v1/admin/logs?kind=errors&limit=200'); const client=await api('/api/v1/admin/logs?kind=client&limit=200'); view.innerHTML=`<div class="admin-split"><section class="admin-card"><h3>App logs</h3>${pre(app.logs)}</section><section class="admin-card"><h3>Error logs</h3>${pre(errors.logs)}</section></div><section class="admin-card"><h3>Client logs</h3>${pre(client.logs)}</section>`;}
// Define the states function that implements this UI or API behavior.
async function states(){setTitle('Game States','Isolated game state files.'); const d=await api('/api/v1/admin/game-states'); view.innerHTML=`<section class="admin-card"><h3>States</h3>${pre(d.states)}</section>`;}
// Define the audio function that implements this UI or API behavior.
async function audio(){setTitle('Audio & Voice','Global sound settings for all games.'); const d=await api('/api/v1/admin/audio-settings'); const s=d.settings||{}; const voices=availableVoices(); view.innerHTML=`<section class="admin-card"><h3>Sound and voice</h3><div class="grid3"><label><input id="master_enabled" type="checkbox" ${s.master_enabled?'checked':''}> Master sound</label><label><input id="sfx_enabled" type="checkbox" ${s.sfx_enabled?'checked':''}> SFX</label><label><input id="voice_enabled" type="checkbox" ${s.voice_enabled?'checked':''}> Voice</label></div><div class="grid3"><label>Master volume<input id="master_volume" type="range" min="0" max="1" step="0.05" value="${s.master_volume}"></label><label>SFX volume<input id="sfx_volume" type="range" min="0" max="1" step="0.05" value="${s.sfx_volume}"></label><label>Voice volume<input id="voice_volume" type="range" min="0" max="1" step="0.05" value="${s.voice_volume}"></label></div><label>Voice<select id="preferred_voice_name"><option value="">Auto nice lady</option>${voices.map(v=>`<option value="${safe(v.name)}" ${s.preferred_voice_name===v.name?'selected':''}>${safe(v.name)} (${safe(v.lang)})</option>`).join('')}</select></label><div class="grid3"><label>Rate<input id="voice_rate" type="number" min="0.5" max="1.8" step="0.05" value="${s.voice_rate}"></label><label>Pitch<input id="voice_pitch" type="number" min="0.4" max="2" step="0.05" value="${s.voice_pitch}"></label><label><input id="auto_nice_lady" type="checkbox" ${s.auto_nice_lady?'checked':''}> Prefer nice lady</label></div><div class="grid3"><label><input id="announce_roulette_results" type="checkbox" ${s.announce_roulette_results?'checked':''}> Roulette announcements</label><label><input id="announce_blackjack_results" type="checkbox" ${s.announce_blackjack_results?'checked':''}> Blackjack announcements</label><label><input id="announce_baccarat_results" type="checkbox" ${s.announce_baccarat_results?'checked':''}> Baccarat announcements</label><label><input id="announce_bingo_calls" type="checkbox" ${s.announce_bingo_calls?'checked':''}> Bingo calls</label><label><input id="announce_keno_results" type="checkbox" ${s.announce_keno_results?'checked':''}> Keno results</label></div><div class="row"><button id="saveAudio" data-testid="admin-save-audio" class="gold">Save audio settings</button><button id="previewVoice" data-testid="admin-preview-voice">Preview voice</button></div></section>`; view.querySelector('#saveAudio').onclick=async()=>{const keys=['master_enabled','sfx_enabled','voice_enabled','auto_nice_lady','announce_roulette_results','announce_blackjack_results','announce_baccarat_results','announce_bingo_calls','announce_keno_results']; const nums=['master_volume','sfx_volume','voice_volume','voice_rate','voice_pitch']; const payload={preferred_voice_name:view.querySelector('#preferred_voice_name').value}; keys.forEach(k=>payload[k]=view.querySelector('#'+k).checked); nums.forEach(k=>payload[k]=Number(view.querySelector('#'+k).value)); await saveVoiceSettings(payload); toast('Audio settings saved.',true);}; view.querySelector('#previewVoice').onclick=async()=>{await loadVoiceSettings(); speak('Welcome to your virtual casino.','global');};}
// Define the autoplay function that implements this UI or API behavior.
async function autoplay(){setTitle('Autoplay','Active and recent autoplay sessions.'); const d=await api('/api/v1/admin/autoplay'); view.innerHTML=`<section class="admin-card"><div class="row"><h3 style="margin-right:auto">Sessions</h3><button id="stopAllAuto" data-testid="admin-stop-all-auto" class="danger">Stop all autoplay</button></div>${table(['ID','Game','Player','Status','Speed','Completed','Limit','Updated'],(d.sessions||[]).slice().reverse().map(s=>`<tr><td>${safe(s.autoplay_id)}</td><td>${safe(s.game_id)}</td><td>${safe(s.player_id)}</td><td>${safe(s.status)}</td><td>${safe(s.speed)}</td><td>${safe(s.rounds_completed)}</td><td>${safe(s.round_limit)}</td><td>${safe(s.updated_at)}</td></tr>`))}</section>`; view.querySelector('#stopAllAuto').onclick=async()=>{await post('/api/v1/admin/autoplay/stop-all',{}); toast('Stop requested for all autoplay sessions.',true); autoplay();};}
// Define the requirements function that implements this UI or API behavior.
async function requirements(){setTitle('Requirements','Numbered requirement registry and validation mapping.'); const d=await api('/api/v1/admin/requirements'); view.innerHTML=`<section class="admin-card"><h3>Requirements</h3>${table(['ID','Module','Description','Status','Tests'],(d.requirements||[]).map(r=>`<tr><td>${safe(r.id)}</td><td>${safe(r.module)}</td><td>${safe(r.description)}</td><td>${safe(r.status)}</td><td>${safe([...(r.api_tests||[]),...(r.browser_tests||[])].join(', '))}</td></tr>`))}</section>`;}
// Define the tests function that implements this UI or API behavior.
async function tests(){setTitle('Tests','Latest API/browser test results.'); const d=await api('/api/v1/admin/test-results'); view.innerHTML=`<section class="admin-card"><h3>Latest results</h3>${pre(d.results)}</section>`;}
// Define the system function that implements this UI or API behavior.
async function system(){setTitle('System','Routes, modules, and raw overview.'); const d=await api('/api/v1/admin/dashboard'); view.innerHTML=`<section class="admin-card"><h3>Module revisions</h3>${table(['Module','Revision'],(d.module_revisions||[]).map(m=>`<tr><td>${safe(m.module)}</td><td>${safe(m.revision)}</td></tr>`))}</section><section class="admin-card"><h3>Raw overview</h3>${pre(d)}</section>`;}
// Execute this statement as part of the module's documented control flow.
load('dashboard');
