// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post } from './api.js';
// Import required dependency so this module can use its public functions or constants.
import { money, safe } from './ui.js';
// Export this symbol so other modules can use it through the public module boundary.
export async function eligibleBots(gameId){try{return await api(`/api/v1/games/${gameId}/eligible-bots`);}catch{return {bots:[],capabilities:{supports_bots:false,strategies:[]}};}}
// Export this symbol so other modules can use it through the public module boundary.
export async function playBotRound(gameId){try{return await post(`/api/v1/games/${gameId}/bots/play-round`,{});}catch(e){return {actions:[],error:e.message};}}
// Export this symbol so other modules can use it through the public module boundary.
export async function botPanelHtml(gameId){const d=await eligibleBots(gameId); if(!d.capabilities?.supports_bots) return '<div class="result-box muted" data-testid="bot-panel-empty">Bots are not enabled for this game.</div>'; const rows=(d.bots||[]).map(b=>`<tr><td>${safe(b.display_name||b.bot_id)}</td><td>${safe(b.strategy_id||'none')}</td><td>${money(b.stake||0)}</td><td>${money(b.balance||0)}</td></tr>`).join(''); return `<div class="bot-panel" data-testid="bot-panel-${gameId}"><h3>Bot controllers</h3><p class="muted">Bots are separate controllers for player accounts. Strategy assignment lives in Admin.</p><table class="mini-table"><tr><th>Bot</th><th>Strategy</th><th>Stake</th><th>Balance</th></tr>${rows||'<tr><td colspan="4">No eligible bots.</td></tr>'}</table></div>`;}
