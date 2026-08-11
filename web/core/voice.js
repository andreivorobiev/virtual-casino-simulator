// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Disabled-by-default sound, speech, and per-player audio preference controls.
import { api, post } from './api.js';
// Store audioCtx so later code can read or update this value.
let audioCtx=null;
// Store AUDIO_SETTINGS so later code can read or update this value.
let AUDIO_SETTINGS={master_enabled:false,master_volume:.8,sfx_enabled:false,sfx_volume:.7,voice_enabled:false,voice_volume:.85,voice_rate:.95,voice_pitch:1.08,preferred_voice_name:'',auto_nice_lady:true,announce_roulette_results:false,announce_blackjack_results:false,announce_baccarat_results:false,announce_bingo_calls:false,announce_keno_results:false};
// Keep the authenticated user's personal sound choice separate from platform-wide Admin audio policy. (USER-008)
let PERSONAL_SOUND_ENABLED=false;
// Apply the current account's personal sound preference immediately without mutating Admin settings.
export function setPersonalSoundEnabled(enabled){PERSONAL_SOUND_ENABLED=enabled===true; if(!PERSONAL_SOUND_ENABLED) try{speechSynthesis.cancel?.();}catch(_){} return PERSONAL_SOUND_ENABLED;}
// Export this symbol so other modules can use it through the public module boundary.
export function getVoiceSettings(){return {...AUDIO_SETTINGS};}
// Export this symbol so other modules can use it through the public module boundary.
export async function loadVoiceSettings(){try{const d=await api('/api/v1/admin/audio-settings');AUDIO_SETTINGS={...AUDIO_SETTINGS,...(d.settings||{})};return AUDIO_SETTINGS;}catch{return AUDIO_SETTINGS;}}
// Export this symbol so other modules can use it through the public module boundary.
export async function saveVoiceSettings(s){AUDIO_SETTINGS={...AUDIO_SETTINGS,...(s||{})};try{const d=await post('/api/v1/admin/audio-settings',AUDIO_SETTINGS);AUDIO_SETTINGS={...AUDIO_SETTINGS,...(d.settings||{})};}catch{}return AUDIO_SETTINGS;}
// Export this symbol so other modules can use it through the public module boundary.
export function availableVoices(){try{return speechSynthesis.getVoices().map((v,i)=>({index:i,name:v.name,lang:v.lang,default:v.default}));}catch{return [];}}
// Define the canSfx function that implements this UI or API behavior.
function canSfx(){return PERSONAL_SOUND_ENABLED && AUDIO_SETTINGS.master_enabled!==false && AUDIO_SETTINGS.sfx_enabled!==false && Number(AUDIO_SETTINGS.master_volume)>0 && Number(AUDIO_SETTINGS.sfx_volume)>0;}
// Define the sfxVolume function that implements this UI or API behavior.
function sfxVolume(v){return Number(v||.05)*Number(AUDIO_SETTINGS.master_volume||1)*Number(AUDIO_SETTINGS.sfx_volume||1);}
// Define the audioProbe function so browser tests can observe sound behavior without real speakers.
function audioProbe(event){try{window.__casinoAudioProbe?.({...event,timestamp:Date.now()});}catch(_){ }}
// Export this symbol so other modules can use it through the public module boundary.
export function speak(text, gameId='global'){
  // Start protected logic so failures can be handled safely.
  try{
    // Set if(AUDIO_SETTINGS.master_enabled to the value needed for the next operation.
    if(!PERSONAL_SOUND_ENABLED || AUDIO_SETTINGS.master_enabled===false || AUDIO_SETTINGS.voice_enabled===false) return;
    // Store key so later code can read or update this value.
    const key = gameId==='bingo' ? 'announce_bingo_calls' : `announce_${gameId}_results`; if(gameId!=='global' && AUDIO_SETTINGS[key]===false) return;
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
    // Record voice completion so long-suite browser checks can detect cut-off announcements.
    u.onend=()=>audioProbe({kind:'voice_end',gameId,text});
    // Record speech errors so audio tests can distinguish browser failure from missing events.
    u.onerror=e=>audioProbe({kind:'voice_error',gameId,text,error:String(e?.error||e?.message||'speech error')});
    // Record the start request before handing the utterance to the browser speech queue.
    audioProbe({kind:'voice_start',gameId,text});
    if(speechSynthesis.paused) speechSynthesis.resume?.(); speechSynthesis.speak(u);
  }catch(_){ }
}
// Export this symbol so other modules can use it through the public module boundary.
export function clickSound(freq=520,duration=.08,volume=.04){
 if(!canSfx()) return;
 // Record the effect request for long-suite browser audio verification.
 audioProbe({kind:'sfx_start',freq,duration,volume});
 // Start protected logic so failures can be handled safely.
 try{ audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)(); const osc=audioCtx.createOscillator(), gain=audioCtx.createGain(); osc.frequency.value=freq; gain.gain.value=sfxVolume(volume); osc.type='triangle'; osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); setTimeout(()=>{try{osc.stop();}catch{}},duration*1000);}catch(_){ }
}
// Export this symbol so other modules can use it through the public module boundary.
export function rouletteRollSound(ms=2500){
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
