// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post } from '../core/api.js';
// Import required dependency so this module can use its public functions or constants.
import { money, toast, refreshBalance, safe } from '../core/ui.js';
// Import required dependency so this module can use its public functions or constants.
import { renderAutoplay } from '../core/autoplay.js';
// Import required dependency so this module can use its public functions or constants.
import { speak, clickSound, reelSound } from '../core/voice.js';
// Store root so later code can read or update this value.
let root=null,state=null,config=null,autoBox=null,lastSpin=null,spinning=false;
// Define the load function that implements this UI or API behavior.
async function load(){const d=await api('/api/v1/games/slots/state');state=d.state;config=d.config;render();await refreshBalance();}
// Define the cellWin function that implements this UI or API behavior.
function cellWin(r,c){ if(!lastSpin?.wins) return false; return lastSpin.wins.some(w=>Array.isArray(w.line)&&w.line[c]===r); }
// Define the spin function that implements this UI or API behavior.
async function spin(show=true){ if(spinning) return; spinning=true; reelSound(900); render(); const active_lines=Number(root.querySelector('#lines')?.value||5); const line_bet=Number(root.querySelector('#lineBet')?.value||1); const d=await post('/api/v1/games/slots/spin',{player_id:'human',active_lines,line_bet}); await new Promise(r=>setTimeout(r, show?900:200)); state=d.state;config=d.config;lastSpin=d.spin;spinning=false;render();await refreshBalance();clickSound(d.spin.payout>0?860:260,.08); if(show&&d.spin.payout>0)speak(`Slots paid ${d.spin.payout} dollars`,'slots');}
// Define the paytableHtml function that implements this UI or API behavior.
function paytableHtml(){return `<div class="paytable">${Object.entries(config?.paytable||{}).map(([sym,row])=>`<div class="payrow"><b>${safe(sym)}</b><br>${Object.entries(row).map(([c,m])=>`${c}=${m}x`).join(' · ')}</div>`).join('')}<div class="payrow"><b>SCATTER</b><br>3=5x · 4=20x · 5=100x<br>3+ awards 8 free spins</div><div class="payrow"><b>Progressive</b><br>5 SEVEN on an active line wins the meter.</div></div>`}
// Define the render function that implements this UI or API behavior.
function render(){const grid=lastSpin?.grid||state?.last_spins?.slice(-1)[0]?.grid||[['CHERRY','LEMON','BAR','BELL','SEVEN'],['BAR','WILD','CHERRY','LEMON','BELL'],['LEMON','BAR','SCATTER','CHERRY','WILD']];root.innerHTML=`<div class="game-layout three-col"><section class="panel"><h2>Slots</h2><div class="grid2"><label>Active paylines<select id="lines" data-testid="slots-lines">${[1,3,5,9,20].map(n=>`<option value="${n}" ${lastSpin?.active_lines===n?'selected':''}>${n}</option>`).join('')}</select></label><label>Line bet<input id="lineBet" data-testid="slots-line-bet" type="number" min="1" value="${lastSpin?.line_bet||1}"></label></div><button id="spin" data-testid="slots-spin" class="primary">SPIN</button><div id="auto"></div><div class="stat"><b>Progressive</b> <span class="money">${money(state?.progressive||1000)}</span><br><b>Free spins</b> ${state?.free_spins||0}</div></section><section class="panel"><h2>Reels</h2><div class="slot-grid" data-testid="slot-grid">${grid.map((row,r)=>row.map((s,c)=>`<div class="slot-symbol ${spinning?'spinning':''} ${cellWin(r,c)?'win':''}" data-testid="slot-cell-${r}-${c}">${icon(s)}</div>`).join('')).join('')}</div><div class="result-box">${lastSpin?`<b>Cost:</b> ${money(lastSpin.cost)} · <b>Payout:</b> ${money(lastSpin.payout)}<br>${(lastSpin.wins||[]).map(w=>w.kind==='scatter'?`Scatter ${w.scatter_count}: ${money(w.payout)}`:`Line ${w.line_index+1}: ${w.count} ${w.symbol} pays ${money(w.payout)}`).join('<br>')||'No win.'}`:'Spin to play.'}</div></section><section class="panel"><h3>Paytable</h3>${paytableHtml()}<h3>Recent spins</h3><div class="scrollbox">${(state?.last_spins||[]).slice(-12).reverse().map(s=>`<div class="bet-item"><span>${safe(s.round_id)}</span><b>${money(s.payout)}</b><span>${s.active_lines} lines</span></div>`).join('')}</div></section></div>`;root.querySelector('#spin').onclick=()=>spin(true);autoBox=renderAutoplay({id:'slots',onTick:async()=>spin(false)});root.querySelector('#auto').append(autoBox);}
// Define the icon function that implements this UI or API behavior.
function icon(s){return {CHERRY:'🍒',LEMON:'🍋',BAR:'BAR',BELL:'🔔',SEVEN:'7️⃣',WILD:'★',SCATTER:'◇'}[s]||safe(s)}
// Export this symbol so other modules can use it through the public module boundary.
export const SlotsGame={id:'slots',label:'Slots',async mount(node){root=node;await load();},unmount(){if(autoBox?._stop)autoBox._stop();root=null;}};
