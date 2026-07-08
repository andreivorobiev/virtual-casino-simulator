// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post } from './api.js';
// Store audioCtx so later code can read or update this value.
let audioCtx=null;
// Store AUDIO_SETTINGS so later code can read or update this value.
let AUDIO_SETTINGS={master_enabled:true,master_volume:.8,sfx_enabled:true,sfx_volume:.7,voice_enabled:true,voice_volume:.85,voice_rate:.95,voice_pitch:1.08,preferred_voice_name:'',auto_nice_lady:true,announce_roulette_results:true,announce_blackjack_results:true,announce_baccarat_results:true,announce_bingo_calls:false,announce_keno_results:false};
// Export this symbol so other modules can use it through the public module boundary.
export function getVoiceSettings(){return {...AUDIO_SETTINGS};}
// Export this symbol so other modules can use it through the public module boundary.
export async function loadVoiceSettings(){try{const d=await api('/api/v1/admin/audio-settings');AUDIO_SETTINGS={...AUDIO_SETTINGS,...(d.settings||{})};return AUDIO_SETTINGS;}catch{return AUDIO_SETTINGS;}}
// Export this symbol so other modules can use it through the public module boundary.
export async function saveVoiceSettings(s){AUDIO_SETTINGS={...AUDIO_SETTINGS,...(s||{})};try{const d=await post('/api/v1/admin/audio-settings',AUDIO_SETTINGS);AUDIO_SETTINGS={...AUDIO_SETTINGS,...(d.settings||{})};}catch{}return AUDIO_SETTINGS;}
// Export this symbol so other modules can use it through the public module boundary.
export function availableVoices(){try{return speechSynthesis.getVoices().map((v,i)=>({index:i,name:v.name,lang:v.lang,default:v.default}));}catch{return [];}}
// Define the canSfx function that implements this UI or API behavior.
function canSfx(){return AUDIO_SETTINGS.master_enabled!==false && AUDIO_SETTINGS.sfx_enabled!==false && Number(AUDIO_SETTINGS.master_volume)>0 && Number(AUDIO_SETTINGS.sfx_volume)>0;}
// Define the sfxVolume function that implements this UI or API behavior.
function sfxVolume(v){return Number(v||.05)*Number(AUDIO_SETTINGS.master_volume||1)*Number(AUDIO_SETTINGS.sfx_volume||1);}
// Export this symbol so other modules can use it through the public module boundary.
export function speak(text, gameId='global'){
  // Start protected logic so failures can be handled safely.
  try{
    // Set if(AUDIO_SETTINGS.master_enabled to the value needed for the next operation.
    if(AUDIO_SETTINGS.master_enabled===false || AUDIO_SETTINGS.voice_enabled===false) return;
    // Store key so later code can read or update this value.
    const key = gameId==='bingo' ? 'announce_bingo_calls' : `announce_${gameId}_results`; if(gameId!=='global' && AUDIO_SETTINGS[key]===false) return;
    // Execute this statement as part of the module's documented control flow.
    if(!('speechSynthesis' in window)) return;
    // Store u so later code can read or update this value.
    const u=new SpeechSynthesisUtterance(text);
    // Store voices so later code can read or update this value.
    const voices=speechSynthesis.getVoices();
    // Store v so later code can read or update this value.
    let v=null;
    // Set if(AUDIO_SETTINGS.preferred_voice_name) v to the value needed for the next operation.
    if(AUDIO_SETTINGS.preferred_voice_name) v=voices.find(x=>x.name===AUDIO_SETTINGS.preferred_voice_name);
    // Set if(!v && AUDIO_SETTINGS.auto_nice_lady! to the value needed for the next operation.
    if(!v && AUDIO_SETTINGS.auto_nice_lady!==false) v=voices.find(x=>/samantha|victoria|karen|ava|zira|jenny|aria|female|susan|hazel|helen/i.test(x.name));
    // Set if(!v) v to the value needed for the next operation.
    if(!v) v=voices[0];
    // Set if(v)u.voice to the value needed for the next operation.
    if(v)u.voice=v;
    // Set u.rate to the value needed for the next operation.
    u.rate=Number(AUDIO_SETTINGS.voice_rate||.95); u.pitch=Number(AUDIO_SETTINGS.voice_pitch||1.08); u.volume=Number(AUDIO_SETTINGS.voice_volume||1)*Number(AUDIO_SETTINGS.master_volume||1);
    // Execute this statement as part of the module's documented control flow.
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  // Explain this executable/data line so future Codex changes preserve intent.
  }catch(_){ }
}
// Export this symbol so other modules can use it through the public module boundary.
export function clickSound(freq=520,duration=.08,volume=.04){
 // Execute this statement as part of the module's documented control flow.
 if(!canSfx()) return;
 // Start protected logic so failures can be handled safely.
 try{ audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)(); const osc=audioCtx.createOscillator(), gain=audioCtx.createGain(); osc.frequency.value=freq; gain.gain.value=sfxVolume(volume); osc.type='triangle'; osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); setTimeout(()=>{try{osc.stop();}catch{}},duration*1000);}catch(_){ }
}
// Export this symbol so other modules can use it through the public module boundary.
export function rouletteRollSound(ms=2500){
 // Execute this statement as part of the module's documented control flow.
 if(!canSfx()) return;
 // Start protected logic so failures can be handled safely.
 try{ audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)(); const ctx=audioCtx; const noise=ctx.createBufferSource(); const buffer=ctx.createBuffer(1, Math.floor(ctx.sampleRate*ms/1000), ctx.sampleRate); const data=buffer.getChannelData(0); for(let i=0;i<data.length;i++) data[i]=(Math.random()*2-1)*Math.max(.05,1-i/data.length); noise.buffer=buffer; const filter=ctx.createBiquadFilter(); filter.type='bandpass'; filter.frequency.value=1800; const gain=ctx.createGain(); gain.gain.value=sfxVolume(.035); noise.connect(filter); filter.connect(gain); gain.connect(ctx.destination); noise.start(); const ticks=setInterval(()=>clickSound(900+Math.random()*700,.025,.025),90); setTimeout(()=>clearInterval(ticks),ms); }catch(_){ }
}
// Export this symbol so other modules can use it through the public module boundary.
export function reelSound(ms=700){ if(!canSfx())return; const ticks=setInterval(()=>clickSound(200+Math.random()*200,.04,.025),70); setTimeout(()=>clearInterval(ticks),ms); }
// Export this symbol so other modules can use it through the public module boundary.
export function voiceSettingsHtml(){return '<p class="muted">Sound and voice settings moved to Admin -> Audio & Voice.</p>';}
// Export this symbol so other modules can use it through the public module boundary.
export function bindVoiceSettings(){/* full settings are admin-owned in v9.1 */}
