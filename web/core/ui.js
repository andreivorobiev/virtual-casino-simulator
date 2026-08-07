// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can use its public functions or constants.
import { api, post, currentPlayerId, withCurrentPlayer } from './api.js';
// Import the locale-aware formatter so shared game helpers cannot leak English labels in Russian.
import { formatMoney } from './i18n.js';
// Export this symbol so other modules can display play-token amounts consistently.
export const money = n => formatMoney(n);
// Export this symbol so wallet values preserve the ledger's exact two-decimal token precision without relying on a replacement-looking glyph.
export const tokenAmount = n => Number(n || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
// Export this symbol so auth-aware shell code can render play tokens without real-money currency marks.
export const tokens = n => tokenAmount(n);
// Resolve the toast variant from either the legacy boolean flag or an explicit variant name.
// 19 game modules call toast(message,'error'); a bare truthy check rendered those failures in the
// success palette because any non-empty string is truthy. Treat only an explicit success signal as
// success so both spellings are correct and the string form can no longer invert the colour. (#423)
const toastIsSuccess = variant => variant === true || variant === 'ok' || variant === 'success';
// Export this symbol so other modules can use it through the public module boundary.
// The outlet carries its live-region semantics statically in index.html and keeps them for the life of
// the document; swapping role or aria-live at the same moment the text changes is a known way to make
// announcements unreliable, so only the text and palette change here. (#421)
export function toast(message, variant=false){ const t=document.getElementById('toast'); if(!t)return; const ok=toastIsSuccess(variant); t.textContent=message; t.style.background=ok?'#10381f':'#2b1111'; t.style.color=ok?'#c8ffd1':'#ffd3d3'; t.hidden=false; clearTimeout(toast._timer); toast._timer=setTimeout(()=>{t.hidden=true},4500); }
// Capture a stable game control before full-root rendering replaces its DOM node. (UX-025)
export function captureGameFocus(root){
  // Ignore focus outside the route root because shell navigation is persistent.
  if(!root || typeof root.contains!=='function' || !root.contains(document.activeElement)) return null;
  // Read the focused control once before the render destroys it.
  const active=document.activeElement;
  // Prefer stable public selectors that survive localization and value changes.
  let selector=active.id?`#${CSS.escape(active.id)}`:active.dataset.testid?`[data-testid="${CSS.escape(active.dataset.testid)}"]`:active.dataset.cellKey?`[data-cell-key="${CSS.escape(active.dataset.cellKey)}"]`:active.name?`[name="${CSS.escape(active.name)}"]`:null;
  // Fall back to the indexed class identity so unlabeled action buttons stay restorable too. (UX-027)
  if(!selector) selector=stableRouteSelector(root,active);
  // Preserve text selection when the focused element supports it.
  const selection=Number.isInteger(active.selectionStart)?{start:active.selectionStart,end:active.selectionEnd}:null;
  // Return only restorable, non-sensitive presentation state.
  return selector?{selector,selection}:null;
}
// Restore a captured game control after a full-root render without moving focus unexpectedly. (UX-025)
export function restoreGameFocus(root,snapshot){
  // Stop when the prior focus had no stable identity.
  if(!root || typeof root.querySelector!=='function' || !snapshot?.selector) return false;
  // Resolve only within the current game root so selectors cannot escape the route.
  const target=resolveRouteSelector(root,snapshot.selector);
  // Leave focus unchanged when the control no longer exists or cannot receive focus.
  if(!target || typeof target.focus!=='function') return false;
  // Restore the same control without scrolling the game board.
  target.focus({preventScroll:true});
  // Restore the text selection when both the old and new controls support it.
  if(snapshot.selection && typeof target.setSelectionRange==='function') target.setSelectionRange(snapshot.selection.start,snapshot.selection.end);
  // Confirm that restoration completed for browser-free regression tests.
  return true;
}
// Mirror the current game result into one document-lifetime live region. (UX-025)
export function syncGameLiveStatus(root){
  // Locate the persistent outlet that navigation never replaces.
  const outlet=document.getElementById('game-live-status');
  // Read only the game-owned status node explicitly marked for announcement.
  const source=root?.querySelector?.('[data-game-live-status]');
  // Stop when either side of the accessible announcement contract is absent.
  if(!outlet || !source) return false;
  // Normalize whitespace so repeated layout formatting does not create noisy announcements.
  const message=String(source.textContent || '').replace(/\s+/g,' ').trim();
  // Update the persistent status only when the meaningful result changed.
  if(message && outlet.textContent!==message) outlet.textContent=message;
  // Return whether a meaningful status was available.
  return Boolean(message);
}
// Build one stable, route-scoped selector for a live element so scroll and focus state can survive a full-root rerender. (UX-027)
function stableRouteSelector(root, el){
  // Prefer the element id because it is unique and survives localization.
  if(el.id) return `#${CSS.escape(el.id)}`;
  // Prefer the public test identity because acceptance selectors are stability-governed.
  if(el.dataset && el.dataset.testid) return `[data-testid="${CSS.escape(el.dataset.testid)}"]`;
  // Fall back to the first two presentation classes shared by the recreated element, dropping empty tokens so a blank class attribute can never build an invalid selector.
  const classes=typeof el.className==='string'?el.className.trim().split(/\s+/).filter(Boolean).slice(0,2):[];
  // Refuse elements without any stable identity instead of guessing.
  if(!classes.length) return null;
  // Build the class selector once for both matching and disambiguation.
  const selector=`.${classes.map(c=>CSS.escape(c)).join('.')}`;
  // Locate the element's position among identical matches so repeated rails restore independently.
  const index=[...root.querySelectorAll(selector)].indexOf(el);
  // Refuse detached elements that no longer match their own selector.
  if(index<0) return null;
  // Return the selector with its match index for exact reattachment.
  return `${selector}::${index}`;
}
// Resolve one stored route-scoped selector back to a live element after the rerender. (UX-027)
function resolveRouteSelector(root, stored){
  // Split the optional match index from the selector text.
  const [selector,index]=stored.split('::');
  // Match all candidates so indexed selectors restore the same visual rail.
  const matches=[...root.querySelectorAll(selector)];
  // Return the indexed match when present, or the single match, or nothing.
  return index===undefined?matches[0]||null:matches[Number(index)]||null;
}
// Capture the player's viewport state before a full-root rerender replaces the game DOM. (UX-027)
export function captureRouteViewportState(root){
  // Record the route outlet's own scroll offsets because the outlet is the primary game scroll region.
  const snapshot={rootTop:root.scrollTop||0,rootLeft:root.scrollLeft||0,winX:window.scrollX||0,winY:window.scrollY||0,rails:[],focus:captureGameFocus(root)};
  // Walk every element inside the outlet looking for scrolled internal rails.
  for(const el of root.querySelectorAll('*')){
    // Skip elements that have not been scrolled because zero restores itself.
    if(!(el.scrollTop>0||el.scrollLeft>0)) continue;
    // Build a stable identity for the rail before the rerender destroys it.
    const selector=stableRouteSelector(root, el);
    // Record only rails that can be found again after the rerender.
    if(selector) snapshot.rails.push({selector,top:el.scrollTop,left:el.scrollLeft});
  }
  // Return the complete restorable viewport state.
  return snapshot;
}
// Restore the captured viewport state after a full-root rerender rebuilt the game DOM. (UX-027)
export function restoreRouteViewportState(root, snapshot){
  // Ignore absent snapshots so route changes can render without restoration.
  if(!snapshot) return false;
  // Restore each recorded internal rail before the outer offsets so nested layout settles inward-first.
  for(const rail of snapshot.rails){
    // Find the recreated rail through its stored stable identity.
    const el=resolveRouteSelector(root, rail.selector);
    // Restore both scroll axes only when the rail exists again.
    if(el){ el.scrollTop=rail.top; el.scrollLeft=rail.left; }
  }
  // Restore the route outlet's own scroll offsets after content height is available again.
  root.scrollTop=snapshot.rootTop; root.scrollLeft=snapshot.rootLeft;
  // Restore document scroll whenever a full-root render displaced it, including non-zero clamps on stacked game pages. (UX-027)
  if(Math.abs((window.scrollX||0)-snapshot.winX)>2||Math.abs((window.scrollY||0)-snapshot.winY)>2) window.scrollTo(snapshot.winX,snapshot.winY);
  // Restore keyboard focus through the shared stable-control contract without scrolling the board.
  restoreGameFocus(root, snapshot.focus);
  // Report that restoration ran for browser-free regression tests.
  return true;
}
// Track outlets that already intercept rerenders so repeated installation stays idempotent. (UX-027)
const stableRenderRoots=new WeakSet();
// Make every same-route full-root rerender preserve scroll and focus by intercepting outlet innerHTML writes. (UX-027)
export function installStableRouteRenders(root, getRouteId, onAfterRender){
  // Refuse duplicate installation so the native setter is wrapped exactly once.
  if(!root||stableRenderRoots.has(root)) return false;
  // Read the native innerHTML accessor pair from the element prototype chain.
  const native=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
  // Refuse exotic environments without the standard accessor instead of breaking rendering.
  if(!native||typeof native.set!=='function') return false;
  // Remember the route that produced the previous render so route changes reset instead of restore.
  let lastRouteId=null;
  // Remember the last focusable in-route control so a busy render that disables it cannot strand keyboard focus. (UX-027)
  let stickyFocus=null;
  // Advance after every outlet write so deferred restoration from an older render can never overwrite newer state.
  let renderSequence=0;
  // Advance whenever fresh player input reaches the outlet so delayed restoration cannot overwrite that interaction.
  let interactionSequence=0;
  // Distinguish focus restored by this interceptor from a player- or caller-directed focus move that must invalidate pending work.
  let restorationActive=false;
  // Restore one snapshot while suppressing the focus event produced by the restoration itself.
  const restoreSnapshot=(snapshot)=>{
    // Mark the interceptor-owned focus transition before restoring any saved control.
    restorationActive=true;
    // Always release the marker even when a defensive restore fails.
    try{return restoreRouteViewportState(root,snapshot);}finally{restorationActive=false;}
  };
  // Mark one player interaction before route descendants handle it and potentially trigger another render.
  const markInteraction=()=>{ interactionSequence+=1; };
  // Treat an external focus move as authoritative before the next keyboard action reaches the newly focused control.
  const markFocusInteraction=()=>{ if(!restorationActive) interactionSequence+=1; };
  // Observe direct focus moves so a pending restore cannot steal focus between focus() and the following key press.
  root.addEventListener('focusin',markFocusInteraction,{capture:true});
  // Observe keyboard navigation that can intentionally move focus or scroll a contained game surface.
  root.addEventListener('keydown',markInteraction,{capture:true});
  // Observe pointer input before a clicked control can synchronously rerender the route.
  root.addEventListener('pointerdown',markInteraction,{capture:true});
  // Observe wheel input so delayed layout repair never reverses a player's manual scroll.
  root.addEventListener('wheel',markInteraction,{capture:true});
  // Observe touch input so mobile scrolling remains authoritative over deferred restoration.
  root.addEventListener('touchstart',markInteraction,{capture:true});
  // Define the instance-level accessor that wraps only this outlet's writes.
  Object.defineProperty(root,'innerHTML',{
    // Keep the accessor configurable so tests and future shells can uninstall it.
    configurable:true,
    // Delegate reads directly to the native getter.
    get(){ return native.get.call(this); },
    // Preserve viewport state around same-route writes and reset intentionally on route changes.
    set(html){
      // Read the shell-owned route identity at write time.
      const routeId=typeof getRouteId==='function'?getRouteId():null;
      // Claim one render sequence before capture so later writes invalidate this render's deferred restores.
      const sequence=++renderSequence;
      // Bind deferred restoration to the latest player interaction observed before this render began.
      const interaction=interactionSequence;
      // Hold the optional restorable state captured before the write.
      let snapshot=null;
      // Capture preservation state defensively so a measurement fault can never block the render itself.
      try{
        // Capture restorable state only when this write rerenders the same route.
        snapshot=routeId!==null&&routeId===lastRouteId?captureRouteViewportState(this):null;
        // Drop the remembered control whenever the route changes so focus can never leak across games.
        if(routeId!==lastRouteId) stickyFocus=null;
        // Remember the newest identifiable in-route control for later busy-render recovery.
        if(snapshot?.focus) stickyFocus=snapshot.focus;
        // Recover from an earlier render that stranded focus on the document body by reusing the remembered control.
        else if(snapshot&&stickyFocus&&document.activeElement===document.body) snapshot.focus=stickyFocus;
      // Degrade to an unpreserved render rather than letting a capture fault escape into game code.
      }catch(_){ snapshot=null; }
      // Write the new markup through the native setter.
      native.set.call(this,html);
      // Restore preservation state defensively so a restore fault can never escape into game code either.
      try{
        // Restore scroll and focus for in-route rerenders so actions never send the player to the top.
        if(snapshot) restoreSnapshot(snapshot);
        // Start a fresh route at the top so navigation keeps its expected reading position.
        else { this.scrollTop=0; this.scrollLeft=0; }
        // Keep stranded keyboard focus on the focusable game region instead of the document body. (UX-027)
        if(snapshot&&document.activeElement===document.body&&typeof this.focus==='function') this.focus({preventScroll:true});
      // Swallow restoration faults because the fresh markup is already in place and gameplay must continue.
      }catch(_){ }
      // Repeat restoration after browser layout and scroll anchoring settle, because some stacked pages clamp after the synchronous setter returns. (UX-027)
      if(snapshot&&typeof requestAnimationFrame==='function') requestAnimationFrame(()=>{ if(sequence!==renderSequence||interaction!==interactionSequence||routeId!==(typeof getRouteId==='function'?getRouteId():null)) return; try{ restoreSnapshot(snapshot); }catch(_){ } requestAnimationFrame(()=>{ if(sequence!==renderSequence||interaction!==interactionSequence||routeId!==(typeof getRouteId==='function'?getRouteId():null)) return; try{ restoreSnapshot(snapshot); }catch(_){ } }); });
      // Remember the route that owns the markup now present in the outlet.
      lastRouteId=routeId;
      // Notify the shell after every write so cross-cutting checks can observe the settled DOM.
      if(typeof onAfterRender==='function') onAfterRender(this,{routeId,preserved:Boolean(snapshot)});
    }
  });
  // Record the wrapped outlet so repeated installation cannot stack accessors.
  stableRenderRoots.add(root);
  // Report successful installation for browser-free regression tests.
  return true;
}
// Report whether one element carries player-meaningful content that must never be hidden. (UX-026)
function carriesMeaningfulContent(el){
  // Treat interactive controls as always meaningful because hiding them removes gameplay.
  if(el.matches('button,input,select,textarea,a,[tabindex]')) return true;
  // Treat containers of interactive controls as meaningful because clipping them clips the controls.
  if(el.querySelector('button,input,select,textarea,a,[tabindex]')) return true;
  // Treat leaf elements with visible text as meaningful because clipped copy is lost information.
  return el.childElementCount===0&&Boolean(el.textContent&&el.textContent.trim());
}
// Measure whether any meaningful game content escapes the viewport or its clipping container. (UX-026)
export function auditLayoutContainment(root){
  // Read the documentElement once for viewport width and document overflow.
  const de=document.documentElement;
  // Prepare the bounded offender list for diagnostics.
  const offenders=[];
  // Stop measuring detached roots or browser-free environments without failing shell rendering.
  if(!de||!root||typeof root.querySelectorAll!=='function') return {docOverflow:0,offenders};
  // Record document-level horizontal overflow because a sideways-scrolling page is always a defect.
  const docOverflow=Math.max(de.scrollWidth-de.clientWidth,document.body?document.body.scrollWidth-de.clientWidth:0);
  // Recognize intentional horizontal scroll rails so designed scrolling is never reported as loss.
  const isScrollRail=el=>{const s=getComputedStyle(el);return /(auto|scroll)/.test(s.overflowX)&&el.scrollWidth>el.clientWidth+4;};
  // Recognize horizontal clipping ancestors that can silently hide content.
  const clipsX=el=>/(hidden|clip)/.test(getComputedStyle(el).overflowX);
  // Build one short non-sensitive descriptor for diagnostics without serializing markup.
  const describe=el=>{let d=el.tagName.toLowerCase();if(el.id)d+=`#${el.id}`;else if(el.dataset&&el.dataset.testid)d+=`[tid=${el.dataset.testid}]`;else if(typeof el.className==='string'&&el.className.trim())d+=`.${el.className.trim().split(/\s+/).slice(0,2).join('.')}`;return d.slice(0,80);};
  // Walk the rendered route content measuring each candidate exactly once.
  for(const el of root.querySelectorAll('*')){
    // Measure only real rendered elements.
    if(!(el instanceof HTMLElement)) continue;
    // Skip zero-size elements because they present nothing to lose.
    const rect=el.getBoundingClientRect();
    // Ignore elements too small to carry visible content.
    if(rect.width<2||rect.height<2) continue;
    // Skip decorative art so animated table dressing cannot spam diagnostics.
    if(!carriesMeaningfulContent(el)) continue;
    // Walk ancestors to find designed rails or the nearest clipping container.
    let ancestor=el.parentElement,clipper=null,insideRail=false;
    // Stop the walk at the document body boundary.
    while(ancestor&&ancestor!==document.body){
      // Designed rails legitimately scroll horizontally, so their content is reachable.
      if(isScrollRail(ancestor)){insideRail=true;break;}
      // Remember only the nearest clipping ancestor below the route outlet.
      if(!clipper&&clipsX(ancestor)&&ancestor!==root) clipper=ancestor;
      // Continue walking toward the document root.
      ancestor=ancestor.parentElement;
    }
    // Reachable rail content is never an offender.
    if(insideRail) continue;
    // Compute how many pixels of the element are unreachable.
    let lost=0,mode='';
    // Clipped content is measured against its clipping container.
    if(clipper){const cr=clipper.getBoundingClientRect();const l=Math.round(Math.max(rect.right-cr.right,cr.left-rect.left));if(l>8){lost=l;mode=`clipped-by:${describe(clipper)}`;}}
    // Unclipped content is measured against the viewport itself.
    else{const l=Math.round(Math.max(rect.right-de.clientWidth,-rect.left));if(l>8){lost=l;mode='viewport';}}
    // Record the bounded offender descriptor when meaningful pixels are lost.
    if(lost>0) offenders.push({sel:describe(el),lost,mode,w:Math.round(rect.width)});
  }
  // Keep only the three largest offenders so diagnostics stay bounded.
  offenders.sort((a,b)=>b.lost-a.lost);
  // Return the bounded measurement for the shell reporter and browser tests.
  return {docOverflow:Math.max(0,docOverflow),offenders:offenders.slice(0,3)};
}
// Export this symbol so other modules can use it through the public module boundary.
export async function refreshBalance(){
  // Branch when the authenticated shell owns wallet rendering.
  if(window.CasinoCurrentUser){
    // Refresh the canonical current-user payload so game actions cannot leave a stale shell wallet.
    const currentUser=await api('/api/v2/me');
    // Publish the refreshed session payload for shared game and shell helpers.
    window.CasinoCurrentUser=currentUser;
    // Notify the app shell so its private session cache stays aligned with the backend.
    window.dispatchEvent(new CustomEvent('casino-current-user', { detail: currentUser }));
    // Render the current-user play-token balance instead of the legacy v1 wallet.
    renderTokenBalance(currentUser);
    // Return the refreshed player payload for legacy callers that expect a player-like object.
    return currentUser.player || {};
  }
  // Read the current player through the frozen player API.
  const d=await api(`/api/v1/players/${encodeURIComponent(currentPlayerId())}`);
  // Find the shared wallet amount node in the premium shell.
  const el=document.getElementById('balance');
  // Update the wallet amount without duplicating the label text.
  if(el) el.textContent=tokenAmount(d.player.balance);
  // Find the optional wallet label node used by the premium shell.
  const label=document.getElementById('balance-label');
  // Keep the wallet label explicit for screen readers and narrow layouts.
  if(label) label.textContent='Play token balance';
  // Return the player payload for callers that need the current balance.
  return d.player;
}
// Export this symbol so the authenticated shell can render the current-user token balance.
export function renderTokenBalance(currentUser){
  // Read the optional player object from the v2 current-user payload.
  const player=currentUser?.player || {};
  // Read the optional user object from the v2 current-user payload.
  const user=currentUser?.user || {};
  // Prefer explicit token fields while tolerating early backend payload drafts.
  const amount=player.token_balance ?? player.tokens ?? user.token_balance ?? user.tokens ?? currentUser?.token_balance ?? currentUser?.tokens?.balance ?? 0;
  // Find the shared wallet amount node in the premium shell.
  const el=document.getElementById('balance');
  // Update the wallet with a legible number while the shell medallion and label provide token context.
  if(el) el.textContent=tokenAmount(amount);
  // Find the optional wallet label node used by the premium shell.
  const label=document.getElementById('balance-label');
  // Keep the wallet label explicit for authenticated current-user sessions.
  if(label) label.textContent='Play token balance';
  // Return the normalized numeric amount for callers that need testable state.
  return Number(amount || 0);
}
// Render one server-committed wager debit before a game's result presentation completes. (LEDGER-031)
export function renderCommittedWagerBalance(event){
  // Refuse missing, non-object, credit, and zero-value events so settlement rows cannot masquerade as wagers.
  if(!event || typeof event!=='object' || !Number.isFinite(Number(event.amount)) || Number(event.amount)>=0) return false;
  // Read only the storage-authored balance after the accepted debit.
  const amount=Number(event.balance_after);
  // Reject malformed or negative wallet evidence instead of inventing a client-side value.
  if(!Number.isFinite(amount) || amount<0) return false;
  // Normalize the optional ledger owner before matching it to the active browser identity.
  const eventPlayer=String(event.player_id || '');
  // Branch when the authenticated shell owns the canonical current-user payload.
  if(window.CasinoCurrentUser){
    // Read the active shell player without accepting identity from game-owned state.
    const activePlayer=String(window.CasinoCurrentUser?.player?.player_id || '');
    // Refuse a foreign ledger event before it can alter shared wallet presentation.
    if(eventPlayer && activePlayer && eventPlayer!==activePlayer) return false;
    // Copy the current session so stale references cannot mutate the prior authoritative payload.
    const currentUser={...window.CasinoCurrentUser,player:{...(window.CasinoCurrentUser.player || {}),token_balance:amount,balance:amount}};
    // Publish the committed intermediate wallet as the latest shell-owned session view.
    window.CasinoCurrentUser=currentUser;
    // Resolve the event constructor without assuming browser-free seams provide it globally.
    const CurrentUserEvent=window.CustomEvent || globalThis.CustomEvent;
    // Notify the shell cache only when the environment provides the standard event constructor.
    if(CurrentUserEvent) window.dispatchEvent(new CurrentUserEvent('casino-current-user',{detail:currentUser}));
    // Render the exact committed debit balance synchronously before any reveal timer begins.
    renderTokenBalance(currentUser);
    // Confirm that authenticated wallet presentation accepted the ledger event.
    return true;
  }
  // Refuse a foreign legacy-player event before reading the shared wallet node.
  if(eventPlayer && eventPlayer!==String(currentPlayerId())) return false;
  // Resolve the persistent wallet amount owned by the application shell.
  const balance=document.getElementById('balance');
  // Render the exact server-authored balance without a follow-up request that could expose settlement early.
  if(balance) balance.textContent=tokenAmount(amount);
  // Confirm that the valid legacy event was accepted even when the shell node is absent during teardown.
  return true;
}
// Export this symbol so callers can keep using the compatible add-money endpoint for token top-ups.
export async function addFakeMoney(amount){ const d=await post(`/api/v1/players/${encodeURIComponent(currentPlayerId())}/add-money`,withCurrentPlayer({amount})); await refreshBalance(); return d; }
// Export this symbol so other modules can use it through the public module boundary.
export function cardHtml(card){ if(!card)return''; if(card==='??') return '<div class="playing-card back">?</div>'; if(typeof card==='string'){ const suit=card.slice(-1), rank=card.slice(0,-1), red=suit==='\u2665'||suit==='\u2666'; return `<div class="playing-card ${red?'red':''}">${rank}<br>${suit}</div>`;} const red=card.suit==='\u2665'||card.suit==='\u2666'; return `<div class="playing-card ${red?'red':''}">${card.rank}<br>${card.suit}</div>`; }
// Export this symbol so other modules can use it through the public module boundary.
export function safe(s){ return String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
// Export this symbol so later game workers can reuse the approved premium tag markup.
export function renderPremiumTag(label){ return `<span class="tag">${safe(label)}</span>`; }
// Export this symbol so later game workers can reuse compact shell rail metrics.
export function renderShellMetric(label,value){ return `<div class="mini-stat"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`; }
// Export this symbol so later game workers can reuse signed ledger amount formatting.
export function signedMoney(n){ const amount=Number(n||0); return `${amount>=0?'+':'-'}${money(Math.abs(amount))}`; }
