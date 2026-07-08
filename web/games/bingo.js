// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post } from '../core/api.js';
// Import required dependency so this module can use its public functions or constants.
import { money, toast, refreshBalance, safe } from '../core/ui.js';
// Import required dependency so this module can use its public functions or constants.
import { renderAutoplay } from '../core/autoplay.js';
// Import required dependency so this module can use its public functions or constants.
import { speak, clickSound } from '../core/voice.js';
// Import required dependency so this module can use its public functions or constants.
import { botPanelHtml, playBotRound } from '../core/bots.js';
// Store root so later code can read or update this value.
let root=null,state=null,autoBox=null,amount=5,pattern='line',botPanelCache='<p class="muted">Loading bot controllers...</p>',callBusy=false;
// Define the updateBotPanel function that implements this UI or API behavior.
async function updateBotPanel(){botPanelCache=await botPanelHtml('bingo'); const el=root?.querySelector('#botPanel'); if(el)el.innerHTML=botPanelCache;}
// Define the load function that implements this UI or API behavior.
async function load(){const d=await api('/api/v1/games/bingo/state');state=d.state;render();await updateBotPanel();await refreshBalance();}
// Define the buy function that implements this UI or API behavior.
async function buy(){amount=Number(root.querySelector('#bingoAmount').value||5);pattern=root.querySelector('#bingoPattern').value;const d=await post('/api/v1/games/bingo/cards',{player_id:'human',amount,pattern});state=d.state;await playBotRound('bingo');const s=await api('/api/v1/games/bingo/state');state=s.state;render();await updateBotPanel();await refreshBalance();clickSound(500,.05)}
// Define the call function that implements this UI or API behavior.
async function call(show=true){if(callBusy)return; callBusy=true; try{const d=await post('/api/v1/games/bingo/call',{});state=d.state;render(d.session,d.label);await updateBotPanel();await refreshBalance();clickSound(300,.05);if(show)speak(`Bingo ball ${d.label}`,'bingo');}catch(e){toast(e.message);throw e;} finally {callBusy=false;}}
// Define the reset function that implements this UI or API behavior.
async function reset(){const d=await post('/api/v1/games/bingo/reset',{});state=d.state;render();await updateBotPanel();await refreshBalance();}
// Define the autoTick function that implements this UI or API behavior.
async function autoTick(){if(!state.active_session) await buy(); if(state.active_session) await call(false);}
// Define the cardHtml function that implements this UI or API behavior.
function cardHtml(sess){const card=sess?.card; if(!card)return '<p class="muted">Buy a card to start.</p>'; const called=new Set(sess.called||[]); const winCoords=new Set((sess.winner_card?.winning_coords||[]).map(x=>x.join(','))); let out='<div class="bingo-card" data-testid="bingo-card">'+'BINGO'.split('').map(c=>`<div class="bingo-head">${c}</div>`).join(''); for(let r=0;r<5;r++){for(const c of 'BINGO'){const val=card[c][r];const marked=val==='FREE'||called.has(val);const win=winCoords.has(`${r},${'BINGO'.indexOf(c)}`);out+=`<div class="bingo-cell ${marked?'marked':''} ${win?'win':''}" data-testid="bingo-cell-${r}-${c}">${val}</div>`}} return out+'</div>';}
// Define the render function that implements this UI or API behavior.
function render(sess=state.active_session,lastLabel=''){sess=sess||state.active_session;root.innerHTML=`<div class="game-layout three-col stable-game"><section class="panel control-rail"><h2>Bingo</h2><label>Card amount<input id="bingoAmount" type="number" min="1" value="${amount}" data-testid="bingo-amount"></label><label>Pattern<select id="bingoPattern" data-testid="bingo-pattern"><option value="line">Any line</option><option value="four_corners">Four corners</option><option value="postage_stamp">Postage stamp</option><option value="blackout">Blackout</option></select></label><button id="buy" data-testid="bingo-buy" class="gold">Buy card</button><button id="call" data-testid="bingo-call" class="primary">Call next ball</button><button id="reset">Reset</button><div id="auto"></div><div id="botPanel">${botPanelCache}</div></section><section class="panel game-stage"><h2>Card</h2>${cardHtml(sess)}<div class="result-box fixed-result">${sess?`Status: <b>${sess.status}</b> · Calls: ${(sess.called||[]).length}${lastLabel?` · Last: ${lastLabel}`:''}${sess.winner?`<br>Winner: ${sess.winner} · Payout ${money(sess.payout)}`:''}`:'No active session.'}</div></section><section class="panel details-drawer"><h3>Called balls</h3><div class="called-balls">${(sess?.called||[]).map(n=>`<span class="ball">${label(n)}</span>`).join('')}</div><h3>Cards in play</h3><table class="mini-table">${(sess?.cards||[]).map(c=>`<tr><td>${safe(c.player_id)}</td><td>${safe(c.status)}</td><td>${money(c.amount)}</td></tr>`).join('')}</table><h3>Recent sessions</h3><div class="scrollbox">${(state.last_sessions||[]).slice(-8).reverse().map(s=>`<div class="bet-item"><span>${s.pattern}</span><b>${s.winner||'none'}</b><span>${(s.called||[]).length} calls</span></div>`).join('')}</div></section></div>`;root.querySelector('#bingoPattern').value=pattern;root.querySelector('#buy').onclick=buy;root.querySelector('#call').onclick=()=>call(true);root.querySelector('#reset').onclick=reset;autoBox=renderAutoplay({id:'bingo',plan:{type:'auto_call_stepwise'},onTick:autoTick});root.querySelector('#auto').append(autoBox);}
// Define the label function that implements this UI or API behavior.
function label(n){n=Number(n);return n<=15?'B-'+n:n<=30?'I-'+n:n<=45?'N-'+n:n<=60?'G-'+n:'O-'+n}
// Export this symbol so other modules can use it through the public module boundary.
export const BingoGame={id:'bingo',label:'Bingo',async mount(node){root=node;await load();},unmount(){if(autoBox?._stop)autoBox._stop();root=null;}};
