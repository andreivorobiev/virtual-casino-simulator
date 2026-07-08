// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, logClient } from './core/api.js';
// Import required dependency so this module can use its public functions or constants.
import { refreshBalance, addFakeMoney, toast } from './core/ui.js';
// Import required dependency so this module can use its public functions or constants.
import { loadVoiceSettings } from './core/voice.js';

// Store gameDescriptors so later code can read or update this value.
const gameDescriptors = [
  // Explain this executable/data line so future Codex changes preserve intent.
  {id:'roulette', label:'Roulette', path:'./games/roulette.js', exportName:'RouletteGame'},
  // Explain this executable/data line so future Codex changes preserve intent.
  {id:'slots', label:'Slots', path:'./games/slots.js', exportName:'SlotsGame'},
  // Explain this executable/data line so future Codex changes preserve intent.
  {id:'keno', label:'Keno', path:'./games/keno.js', exportName:'KenoGame'},
  // Explain this executable/data line so future Codex changes preserve intent.
  {id:'bingo', label:'Bingo', path:'./games/bingo.js', exportName:'BingoGame'},
  // Explain this executable/data line so future Codex changes preserve intent.
  {id:'blackjack', label:'Blackjack', path:'./games/blackjack.js', exportName:'BlackjackGame'},
  // Explain this executable/data line so future Codex changes preserve intent.
  {id:'baccarat', label:'Baccarat', path:'./games/baccarat.js', exportName:'BaccaratGame'},
];
// Store loadedGames so later code can read or update this value.
const loadedGames = new Map();
// Store active so later code can read or update this value.
let active = null;
// Set window.addEventListener('casino-toast', e to the value needed for the next operation.
window.addEventListener('casino-toast', e => toast(e.detail?.message || 'Auto stopped'));
// Set window.addEventListener('error', event to the value needed for the next operation.
window.addEventListener('error', event => logClient('window_error', { message: event.message, filename: event.filename, lineno: event.lineno, colno: event.colno }));
// Set window.addEventListener('unhandledrejection', event to the value needed for the next operation.
window.addEventListener('unhandledrejection', event => logClient('unhandled_rejection', { reason: String(event.reason?.message || event.reason) }));

// Define the loadGame function that implements this UI or API behavior.
async function loadGame(desc){
  // Execute this statement as part of the module's documented control flow.
  if(loadedGames.has(desc.id)) return loadedGames.get(desc.id);
  // Start protected logic so failures can be handled safely.
  try{
    // Store mod so later code can read or update this value.
    const mod = await import(desc.path);
    // Store game so later code can read or update this value.
    const game = mod[desc.exportName];
    // Execute this statement as part of the module's documented control flow.
    loadedGames.set(desc.id, game);
    // Return the computed value to the caller.
    return game;
  // Explain this executable/data line so future Codex changes preserve intent.
  }catch(err){
    // Call an asynchronous API/helper and wait for the result before continuing.
    await logClient('game_module_load_error',{game:desc.id,message:err.message,stack:err.stack});
    // Execute this statement as part of the module's documented control flow.
    throw err;
  }
}
// Define the renderNav function that implements this UI or API behavior.
function renderNav(){
  // Store nav so later code can read or update this value.
  const nav=document.getElementById('main-nav');
  // Set nav.innerHTML to the value needed for the next operation.
  nav.innerHTML=`<button data-route="lobby" class="${active==='lobby'?'active':''}" data-testid="nav-lobby">Lobby</button>`+
    // Set gameDescriptors.map(g to the value needed for the next operation.
    gameDescriptors.map(g=>`<button data-route="${g.id}" class="${active===g.id?'active':''}" data-testid="nav-${g.id}">${g.label}</button>`).join('')+
    // Set `<button data-admin to the value needed for the next operation.
    `<button data-admin="true" data-testid="nav-admin">Admin</button>`;
  // Set nav.querySelectorAll('[data-route]').forEach(b to the value needed for the next operation.
  nav.querySelectorAll('[data-route]').forEach(b=>b.onclick=()=>navigate(b.dataset.route));
  // Set nav.querySelector('[data-admin]').onclick to the value needed for the next operation.
  nav.querySelector('[data-admin]').onclick=()=>{ location.href='/admin'; };
}
// Define the lobbyHtml function that implements this UI or API behavior.
function lobbyHtml(){
 // Store descriptions so later code can read or update this value.
 const descriptions={roulette:'Animated wheel, direct chip placement, inside/outside bets, racetrack specials, bots, zero rules, and last-1000 stats.',slots:'Animated 5-reel slot with reel strips, paylines, wilds, scatters, free spins, and fake progressive.',keno:'Pick 1-20 spots, draw 20 numbers, paytable display, animations, and bot tickets.',bingo:'75-ball American Bingo with patterns, bot cards, call history, and winning pattern highlights.',blackjack:'Hit, stand, double, split, surrender, insurance, even money, and table rule controls.',baccarat:'Punto Banco shoe with burn/cut behavior, Player/Banker/Tie bets, bots, and road history.'};
 // Return the computed value to the caller.
 return `<section class="lobby" data-testid="lobby">${gameDescriptors.map(g=>`<article class="game-card" data-testid="card-${g.id}"><div><h2>${g.label}</h2><p>${descriptions[g.id]}</p></div><button class="primary" data-open-game="${g.id}" data-testid="open-${g.id}">Open ${g.label}</button></article>`).join('')}</section>`;
}
// Export this symbol so other modules can use it through the public module boundary.
export async function navigate(route){
 // Start protected logic so failures can be handled safely.
 try{
   // Store previous so later code can read or update this value.
   const previous = active;
   // Execute this statement as part of the module's documented control flow.
   if(previous && loadedGames.has(previous)) loadedGames.get(previous).unmount?.();
   // Set active to the value needed for the next operation.
   active=route; renderNav();
   // Store view so later code can read or update this value.
   const view=document.getElementById('view');
   // Set if(route to the value needed for the next operation.
   if(route==='lobby' || !gameDescriptors.some(g=>g.id===route)){
     // Set view.innerHTML to the value needed for the next operation.
     view.innerHTML=lobbyHtml();
     // Set view.querySelectorAll('[data-open-game]').forEach(b to the value needed for the next operation.
     view.querySelectorAll('[data-open-game]').forEach(b=>b.onclick=()=>navigate(b.dataset.openGame));
     // Return the computed value to the caller.
     return;
   }
   // Set view.innerHTML to the value needed for the next operation.
   view.innerHTML='<div class="panel"><h2>Loading...</h2></div>';
   // Store desc so later code can read or update this value.
   const desc=gameDescriptors.find(g=>g.id===route);
   // Store game so later code can read or update this value.
   const game=await loadGame(desc);
   // Call an asynchronous API/helper and wait for the result before continuing.
   await game.mount(view);
 // Handle navigation errors so the app can show a friendly failure panel.
 }catch(err){
   // Write diagnostic output so the current operation can be inspected.
   console.error(err);
   // Call an asynchronous API/helper and wait for the result before continuing.
   await logClient('navigation_error',{route,message:err.message,stack:err.stack});
   // Set document.getElementById('view').innerHTML to the value needed for the next operation.
   document.getElementById('view').innerHTML=`<div class="panel"><h2>Could not load ${route}</h2><p class="status">${err.message}</p><button data-route="lobby">Back to lobby</button></div>`;
   // Set document.querySelector('[data-route to the value needed for the next operation.
   document.querySelector('[data-route="lobby"]')?.addEventListener('click',()=>navigate('lobby'));
 }
}
// Define the init function that implements this UI or API behavior.
async function init(){
 // Set document.getElementById('add-money-btn').onclick to the value needed for the next operation.
 document.getElementById('add-money-btn').onclick=async()=>{ try{ await addFakeMoney(Number(document.getElementById('add-money-amount').value||0)); toast('Fake money added.',true);}catch(err){toast(err.message);} };
 // Start protected logic so failures can be handled safely.
 try{ await loadVoiceSettings(); await api('/api/v1/casino/state'); await refreshBalance(); }catch(err){ toast(`Could not load state: ${err.message}`); await logClient('initial_state_error',{message:err.message}); }
 // Execute this statement as part of the module's documented control flow.
 navigate('lobby');
}
// Execute this statement as part of the module's documented control flow.
init();
