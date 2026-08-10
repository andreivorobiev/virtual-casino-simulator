// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can call frozen Roulette API endpoints.
import { api, post, del, currentPlayerId, currentPlayerPath, withCurrentPlayer, logClient } from '../core/api.js';
// Import shared UI helpers so the Roulette surface matches the premium shell contract.
import { toast, refreshBalance, renderTokenBalance, tokenAmount, safe, captureGameFocus, restoreGameFocus, syncGameLiveStatus } from '../core/ui.js';
// Import autoplay renderer so Roulette keeps using the shared control-plane session behavior.
import { renderAutoplay } from '../core/autoplay.js';
// Import voice helpers so spin sounds and announcements preserve existing behavior.
import { speak, clickSound, rouletteRollSound } from '../core/voice.js';
// Import bot helpers so bots continue to act through the documented controller path.
import { botPanelHtml, playBotRound } from '../core/bots.js';
// Import i18n helpers so visible Roulette-owned strings refresh without remounting gameplay state.
import { initI18n, onLocaleChange, t } from '../core/i18n.js';
// Import shared motion helpers so spin timers honor reduced motion and route-teardown cleanup. (MOTION-001, MOTION-002)
import { prefersReducedMotion, createMotionTimerScope } from '../core/motion.js';
// Import the seeded generator so decorative landing scatter stays deterministic per committed round.
import { createSeededRandom } from '../core/dice.js';

// Store the i18n resource domain owned by this game module.
const GAME_DOMAIN = 'games/roulette';
// Store the shared autoplay domain so progressive-disclosure labels remain localized.
const AUTOPLAY_DOMAIN = 'core/autoplay';
// Store the shared bots domain so the collapsed controller label remains localized.
const BOTS_DOMAIN = 'core/bots';
// Store the local style element id so repeated mounts do not duplicate Roulette-only CSS.
const PREMIUM_STYLE_ID = 'roulette-premium-style';
// Store chip denominations so the control rail remains stable across rerenders.
const CHIP_VALUES = [1, 5, 25, 100, 500, 1000];
// Store the rendered premium hotspot diameter so inline positions stay centered on their canonical point.
const SPOT_SIZE = 24;
// Store red pockets so wheel, table, and history pills share the same color logic.
const RED_NUMBERS = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
// Store board geometry so click targets and placed chips remain aligned on the fixed table.
const BOARD = { width: 760, height: 560, x0: 170, y0: 82, cw: 132, ch: 34 };
// Export the visible reveal budget that the tracked 3.6-second compatibility curves are sampled against. (ROU-069)
export const SPIN_REVEAL_MS = 3600;
// Export the short autoplay reveal so unattended rounds keep their existing fast cadence.
export const AUTOPLAY_REVEAL_MS = 250;
// Export the bounded non-spinning reveal used when the player asks for reduced motion. (ROU-070)
export const REDUCED_REVEAL_MS = 600;
// Store the quick rim-lift duration that returns the captured ball to its track before a new spin.
const BALL_LIFT_MS = 260;
// Export the radial travel in SVG units from the outer ball track down into a pocket mouth.
export const BALL_POCKET_DEPTH = 24;
// Export the extra whole rotor turns the honest-landing wrapper adds on top of the sampled curve.
export const WHEEL_EXTRA_TURNS = 1;
// Export the extra whole counter-turns the ball wrapper adds so total circuits read as a real launch.
export const BALL_EXTRA_TURNS = 2;
// Export the minimum wrapper travel time so a slow backend can never produce a teleporting landing.
export const MIN_LANDING_MS = 900;
// Store premium Roulette CSS inside the owned module so shared foundation styles stay untouched.
const PREMIUM_STYLE = [
  '.roulette-premium{display:grid;grid-template-rows:auto minmax(0,1fr);gap:12px;height:100%;min-height:0;container-type:inline-size;}', // Keep the complete table route stable inside the shared shell.
  '.roulette-premium .roulette-header{display:grid;align-items:end;min-height:66px;}', // Keep the route title compact and free of internal lifecycle diagnostics.
  '.roulette-premium .roulette-kicker{margin:0 0 2px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.14em;}', // Present the table category as a restrained casino eyebrow.
  '.roulette-premium h1{margin:0;color:var(--gold);font-family:var(--font-display);font-size:46px;line-height:.92;text-shadow:0 2px 22px rgba(255,217,120,.2);}', // Give Roulette a strong but space-conscious route title.
  '.roulette-premium .game-layout{grid-template-columns:340px minmax(0,1fr) 355px;height:100%;min-height:0;}', // Match the governed premium rail widths while leaving the center stage dominant at primary desktop size.
  '.roulette-premium .panel{border-color:var(--gold);box-shadow:inset 0 1px rgba(255,255,255,.035),0 18px 44px rgba(0,0,0,.24);}', // Add consistent gold-edged table furniture depth.
  '.roulette-premium .control-rail,.roulette-premium .details-drawer{padding:13px;background:linear-gradient(155deg,rgba(20,10,34,.97),rgba(20,10,34,.96));scrollbar-color:var(--gold) transparent;}', // Keep supporting rails dark, compact, and subordinate to gameplay.
  '.roulette-premium .game-title{margin:0 0 10px;color:var(--gold);font-size:24px;}', // Make the control heading feel like table signage.
  '.roulette-control-section{margin-top:10px;}', // Space control groups without changing their footprint across phases.
  '.roulette-control-section h3{margin:0 0 6px;color:var(--gold);text-transform:uppercase;font-size:12px;letter-spacing:.08em;}', // Use small gold rail labels instead of debug-like headings.
  '.roulette-settings{display:grid;grid-template-columns:1fr 1fr;gap:7px;}', // Pair table settings to save vertical space.
  '.roulette-settings label{display:grid;gap:5px;min-width:0;padding:8px;border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.035);color:var(--muted);font-size:11px;font-weight:800;}', // Frame settings as compact dealer controls.
  '.roulette-settings select,.roulette-call-input{width:100%;min-width:0;min-height:34px;border-color:var(--border);background:var(--felt);}', // Keep native fields inside the premium surface palette.
  '.roulette-premium .chip-row{gap:5px;}', // Keep all chip values available without an oversized control band.
  '.roulette-premium .chip{width:42px;height:42px;min-height:42px;font-size:10px;box-shadow:0 5px 13px rgba(0,0,0,.42);}', // Give chip selectors a physical table-chip scale.
  '.roulette-fast-grid,.roulette-call-grid,.roulette-secondary-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;}', // Keep secondary choices aligned in predictable lanes.
  '.roulette-fast-grid button,.roulette-call-grid button,.roulette-secondary-actions button{min-height:32px;padding:6px 7px;border-color:rgba(255,255,255,.14);border-radius:8px;background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(255,255,255,.025));font-size:11px;}', // Style utility bets as player controls rather than diagnostics.
  '.roulette-fast-grid button[data-outbtn="red"]{background:linear-gradient(180deg,#b72835,#75141d);}', // Give the red shortcut its casino color cue.
  '.roulette-fast-grid button[data-outbtn="black"]{background:linear-gradient(180deg,#252a28,#080b0a);}', // Give the black shortcut its casino color cue.
  '.roulette-advanced{margin-top:9px;border:1px solid var(--border);border-radius:10px;background:rgba(0,0,0,.14);}', // Contain advanced rules and automation without making them dominate the rail.
  '.roulette-advanced summary{padding:9px 10px;color:var(--gold);cursor:pointer;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.07em;}', // Present optional controls as intentional expandable casino features.
  '.roulette-advanced[open] summary{border-bottom:1px solid var(--border);}', // Separate the advanced heading from its opened contents.
  '.roulette-advanced-body{padding:8px;}', // Keep advanced bet controls comfortably inset.
  '.roulette-call-number{display:grid;gap:5px;margin:8px 0;color:var(--muted);font-size:11px;font-weight:800;}', // Present the call number as a labeled table field.
  '.roulette-control-plane{margin-top:8px;padding:10px;border:1px solid rgba(255,59,107,.32);border-radius:10px;background:linear-gradient(135deg,rgba(20,10,34,.17),rgba(0,0,0,.12));}', // Give bot and autoplay status a quiet control-plane treatment.
  '.roulette-control-plane b{display:block;color:var(--gold);}', // Keep controller headings readable.
  '.roulette-control-plane span{display:block;margin-top:4px;color:var(--muted);font-size:11px;}', // Keep controller details visually secondary.
  '.roulette-premium #botPanel{overflow:visible;}', // Let bot rows expand into the single intentional control-rail scroll region.
  '.roulette-premium #botPanel .mini-table{font-size:10px;}', // Keep bot controller data legible in the compact rail.
  '.roulette-premium .game-stage{display:grid;grid-template-rows:auto minmax(0,1fr);gap:10px;padding:13px;overflow:hidden;background:radial-gradient(circle at 42% 10%,rgba(20,10,34,.25),transparent 42%),linear-gradient(150deg,rgba(20,10,34,.98),rgba(20,10,34,.98));}', // Give the dealer toolbar a fixed row and the complete wheel/table stage the exact remaining desktop height. (UX-026)
  '.roulette-stage-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:58px;padding:0 2px;}', // Reserve the same dealer action bar in every phase without double-counting a margin outside the stage grid.
  '.roulette-stage-toolbar .eyebrow{margin:0;color:var(--muted);font-size:11px;letter-spacing:.08em;}', // Keep localized round metadata understated without altering its rendered case.
  '.roulette-stage-toolbar h2{margin:2px 0 0;color:var(--gold);font-family:var(--font-display);font-size:30px;line-height:1;}', // Make the current phase immediately scannable.
  '.roulette-stage-toolbar button{min-width:112px;min-height:42px;}', // Stabilize the clear and spin controls.
  '.roulette-stage-toolbar .primary{border-color:var(--gold);background:linear-gradient(180deg,#d6323d,#8e1822);box-shadow:0 10px 24px rgba(128,14,24,.28),inset 0 1px rgba(255,255,255,.2);}', // Give the spin action a premium dealer-button finish.
  '.roulette-premium .roulette-stage{grid-template-columns:minmax(300px,360px) minmax(0,1fr);gap:12px;align-items:stretch;height:100%;min-height:0;overflow:hidden;}', // Fit wheel and betting board into the exact remaining desktop stage instead of forcing a clipped fixed minimum. (UX-026)
  '.roulette-premium .wheel-card{position:relative;display:grid;grid-template-rows:minmax(0,1fr) 118px;height:100%;min-height:0;overflow:hidden;border:1px solid var(--gold);border-radius:14px;background:radial-gradient(circle at 50% 34%,rgba(20,10,34,.28),transparent 42%),linear-gradient(180deg,var(--felt),var(--bg));}', // Build a dedicated wheel plinth that contracts with the governed desktop stage.
  '.roulette-premium .wheel-card::before{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(115deg,rgba(255,255,255,.06),transparent 24%,transparent 74%,rgba(218,175,70,.045));}', // Add soft directional table lighting.
  '.roulette-premium .wheel-card.reveal-glow{box-shadow:inset 0 0 64px rgba(244,194,79,.13),0 18px 38px rgba(0,0,0,.36);}', // Illuminate the wheel plinth during the reveal arc.
  '.roulette-premium .wheel-card.result-glow{box-shadow:inset 0 0 70px rgba(244,194,79,.18),0 18px 38px rgba(0,0,0,.36);}', // Hold a warmer settled-state glow without resizing the stage.
  '.roulette-wheel-frame{position:relative;z-index:1;display:grid;place-items:center;min-height:0;padding:14px 8px 4px;perspective:850px;}', // Provide a dimensional viewing angle and stable wheel envelope.
  '.roulette-wheel-frame::after{content:"";position:absolute;left:15%;right:15%;bottom:5%;height:10%;border-radius:50%;background:rgba(0,0,0,.42);filter:blur(14px);z-index:-1;}', // Ground the wheel with a soft table shadow.
  '.roulette-premium .roulette-wheel{width:min(100%,360px);max-width:360px;filter:drop-shadow(0 22px 26px rgba(0,0,0,.58));}', // Make the vector wheel large and weighty without a fragile 3D compositor layer.
  '.roulette-wheel .wheel-rim-highlight{opacity:.68;}', // Add a polished metal reflection to the outer rim.
  '.roulette-wheel .wheel-ball{filter:drop-shadow(0 3px 3px rgba(0,0,0,.75));}', // Separate the ivory ball from the track during motion and settlement.
  '.roulette-premium .wheel-ring.spinning{animation:roulettePremiumWheelSpin 3.6s linear;will-change:transform;}', // Coast the rotor down through its own keyframe curve rather than a front-loaded easing.
  '.roulette-premium .ball-dot.spinning{animation:roulettePremiumBallSpin 3.6s linear;will-change:transform;}', // Counter-rotate the ball on the same self-decelerating curve so it never outruns the rotor into a strobe.
  '.roulette-wheel .wheel-orient,.roulette-wheel .ball-orbit,.roulette-wheel .ball-radial{transform-origin:150px 150px;will-change:transform;}', // Pivot every honest-landing wrapper on the wheel hub so composed rotations stay concentric.
  '.roulette-wheel .ball-trail{opacity:0;transition:opacity .4s;}', // Hide the ivory motion streak until the ball is actually travelling.
  '.roulette-premium .ball-dot.spinning .ball-trail{opacity:.55;}', // Reveal the streak only while the counter-rotation curve is live.
  '.roulette-wheel .ball-radial.descending{animation:roulettePremiumBallDescent var(--rou-descent-ms,1500ms) linear forwards;}', // Drop the ball from the rim into its authoritative pocket with the descent shape carried by sampled stops.
  '.roulette-wheel .ball-dot.settled{animation:rouletteBallSettle .52s cubic-bezier(.2,.8,.2,1);}', // Give the authoritative result a short physical settle rather than an abrupt swap.
  '.roulette-wheel .ball-dot.parked{opacity:.72;}', // Show an unassigned ball without implying a fake result pocket.
  '.roulette-premium.just-settled .fixed-result.win .roulette-result-pocket{animation:rouletteResultBloom .72s cubic-bezier(.2,.8,.2,1);}', // Bloom the settled pocket badge once on the fresh settle render only.
  '.roulette-premium.just-settled .table-cell.result-cell,.roulette-premium.just-settled .outside-cell.result-cell{animation:rouletteCellReveal .9s cubic-bezier(.2,.8,.2,1);}', // Flash the winning felt region once on the fresh settle render only.
  '.roulette-premium.just-settled .roulette-history-pills span.result-cell{animation:roulettePillPop .5s cubic-bezier(.2,.8,.2,1);}', // Pop the newest history pocket once on the fresh settle render only.
  '@media (prefers-reduced-motion: reduce){.roulette-premium .wheel-ring.spinning,.roulette-premium .ball-dot.spinning{animation:none;}.roulette-wheel .ball-dot.settled{animation:none;}.roulette-spin-orbit::after{animation:none;}.roulette-wheel .wheel-orient,.roulette-wheel .ball-orbit,.roulette-wheel .ball-radial{transition:none!important;animation:none!important;}.roulette-wheel .ball-trail{opacity:0!important;}.roulette-premium.just-settled .fixed-result.win .roulette-result-pocket,.roulette-premium.just-settled .table-cell.result-cell,.roulette-premium.just-settled .outside-cell.result-cell,.roulette-premium.just-settled .roulette-history-pills span.result-cell{animation:none;}}', // Present the authoritative pocket without rotation when the player asks for reduced motion.
  '.roulette-premium .fixed-result{position:relative;z-index:2;display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:12px;min-height:100px;margin:0 12px 12px;padding:12px 14px;overflow:hidden;border:1px solid rgba(255,255,255,.1);border-radius:11px;background:linear-gradient(135deg,rgba(0,0,0,.36),rgba(255,255,255,.025));}', // Integrate result presentation into the wheel console.
  '.roulette-result-pocket{display:grid;place-items:center;width:58px;height:58px;border:2px solid rgba(255,238,183,.68);border-radius:50%;color:#fff5d5;font-family:var(--font-display);font-size:26px;font-weight:1000;box-shadow:0 8px 18px rgba(0,0,0,.42),inset 0 0 18px rgba(255,255,255,.12);}', // Present the winning pocket as the primary settlement signal.
  '.roulette-result-copy{display:grid;gap:3px;min-width:0;}', // Keep result headline and supporting value aligned.
  '.roulette-result-copy b{color:var(--gold);font-size:16px;}', // Emphasize the authoritative rolled number.
  '.roulette-result-copy span{color:var(--muted);font-size:11px;line-height:1.35;}', // Keep net and state details compact and readable.
  '.roulette-spin-orbit{position:relative;width:52px;height:52px;border:2px solid var(--border);border-radius:50%;}', // Reserve a motion indicator in the result console while the outcome is hidden.
  '.roulette-spin-orbit::after{content:"";position:absolute;inset:6px;border-top:3px solid var(--gold);border-radius:50%;animation:rouletteOrbit 1s linear infinite;}', // Animate only transform to signal the reveal phase.
  '.roulette-premium .fixed-result.win{border-color:var(--gold);background:linear-gradient(135deg,rgba(117,25,31,.34),rgba(222,177,70,.09));}', // Give the settled result a composed burgundy-and-gold treatment.
  '.roulette-table-shell{display:grid;place-items:start;width:100%;min-width:0;height:100%;min-height:0;overflow:hidden;border-radius:13px;}', // Give continuous board fitting the real remaining height instead of a fixed shell that can escape below the stage. (UX-026)
  '.roulette-premium .roulette-table-board{flex:none;width:760px;height:590px;border:2px solid var(--gold);border-radius:12px;background:radial-gradient(circle at 45% 14%,rgba(255,255,255,.09),transparent 38%),radial-gradient(circle at 50% 115%,rgba(0,0,0,.5),transparent 55%),linear-gradient(145deg,var(--felt2),var(--felt));box-shadow:inset 0 0 60px rgba(0,0,0,.5),inset 0 0 0 6px rgba(255,217,120,.05),0 14px 30px rgba(0,0,0,.28);}', // Give the betting layout deep-pile felt, table lighting, a vignette, and a double gold trim.
  '.roulette-table-board.roulette-board-dimmed{filter:saturate(.72) brightness(.78);}', // Dim the table during the reveal without layout motion.
  '.roulette-premium .table-cell,.roulette-premium .outside-cell{border-color:rgba(255,245,218,.55);border-radius:5px;box-shadow:inset 0 1px rgba(255,255,255,.1),inset 0 -6px 12px rgba(0,0,0,.22);}', // Bevel cell edges like stitched felt lanes while preserving every existing hit target.
  '.roulette-premium .table-cell.red{background:linear-gradient(165deg,#c22433,#7c1220 78%)!important;}', // Skin red pockets with a lacquered two-stop red over the shared important brand fallback.
  '.roulette-premium .table-cell.black{background:linear-gradient(165deg,#2b2f2e,#0a0d0c 78%)!important;}', // Skin black pockets with a graphite two-stop black over the shared important brand fallback.
  '.roulette-premium .table-cell.green{background:linear-gradient(165deg,#0f9152,#065a31 78%)!important;}', // Skin zero pockets with an emerald two-stop green over the shared important brand fallback.
  '.roulette-premium .outside-cell{background:linear-gradient(180deg,rgba(255,255,255,.08),rgba(0,0,0,.26));font-size:12px;letter-spacing:.05em;text-transform:uppercase;}', // Present outside lanes as etched glass plaques with confident lettering.
  '.roulette-premium .table-cell button:hover,.roulette-premium .outside-cell button:hover{box-shadow:inset 0 0 22px rgba(255,218,119,.28),inset 0 0 0 1px rgba(255,218,119,.5);}', // Add a gold-ring felt hover cue.
  '.roulette-premium .bet-chip{border:3px dashed #fff6da;background:radial-gradient(circle,#fffdf4 0 24%,#e4b12f 25% 54%,#8a5c07 55% 72%,#5d3c03 73%);box-shadow:0 5px 12px rgba(0,0,0,.55),inset 0 0 0 2px rgba(90,50,0,.55),inset 0 2px 3px rgba(255,255,255,.6);}', // Layer the wager chip like a real edge-striped casino check without moving its center.
  '.roulette-result-pocket.red{background:linear-gradient(160deg,#c22433,#6d0f1b)!important;}', // Match the settled badge to a red pocket over the shared important brand fallback.
  '.roulette-result-pocket.black{background:linear-gradient(160deg,#333836,#070908)!important;}', // Match the settled badge to a black pocket over the shared important brand fallback.
  '.roulette-result-pocket.green{background:linear-gradient(160deg,#0f9152,#04492a)!important;}', // Match the settled badge to a zero pocket over the shared important brand fallback.
  '.roulette-premium .table-cell.result-cell,.roulette-premium .outside-cell.result-cell{outline:3px solid var(--gold);box-shadow:inset 0 0 26px rgba(255,217,120,.4),0 0 22px rgba(255,217,120,.3);}', // Lock the settled result visibly to the winning table area.
  '.roulette-result-marker{position:absolute;right:5px;bottom:3px;color:var(--gold);font-size:9px;font-weight:1000;}', // Keep the table WIN marker inside its pocket.
  '.roulette-premium .spot{display:grid;place-items:center;width:24px;height:24px;border:0;background:transparent;opacity:1;}', // Provide a reliable touch target while the visible marker stays compact. (UX-025)
  '.roulette-premium .spot::after{content:"";width:15px;height:15px;border:1px solid rgba(255,217,120,.66);border-radius:50%;background:rgba(255,217,120,.38);opacity:.32;}', // Preserve the original unobtrusive marker inside the larger hit area. (UX-025)
  '.roulette-premium .spot:hover::after,.roulette-premium .spot:focus-visible::after{opacity:1;}', // Reveal inside-bet precision on pointer or keyboard intent.
  '.roulette-premium .roulette-table-board.hide-spots .spot{visibility:hidden;pointer-events:none;opacity:0;}', // Remove hidden inside spots from pointer and accessibility actionability instead of leaving invisible controls live.
  '.roulette-premium .bet-chip{animation:rouletteChipPop .18s ease-out;}', // Make placed chips feel physical without layout-changing animation.
  '@keyframes rouletteChipPop{from{transform:scale(.82);opacity:.5;}to{transform:scale(1);opacity:1;}}', // Animate chips with transform and opacity only.
  '@keyframes rouletteOrbit{to{transform:rotate(360deg);}}', // Spin the result-console orbit without triggering layout.
  '@keyframes roulettePremiumWheelSpin{0%{transform:rotate(0deg);}5%{transform:rotate(70.2deg);}10%{transform:rotate(136.8deg);}15%{transform:rotate(199.8deg);}20%{transform:rotate(259.2deg);}25%{transform:rotate(315deg);}30%{transform:rotate(367.2deg);}35%{transform:rotate(415.8deg);}40%{transform:rotate(460.8deg);}45%{transform:rotate(502.2deg);}50%{transform:rotate(540deg);}55%{transform:rotate(574.2deg);}60%{transform:rotate(604.8deg);}65%{transform:rotate(631.8deg);}70%{transform:rotate(655.2deg);}75%{transform:rotate(675deg);}80%{transform:rotate(691.2deg);}85%{transform:rotate(703.8deg);}90%{transform:rotate(712.8deg);}95%{transform:rotate(718.2deg);}100%{transform:rotate(720deg);}}', // Sample a constant-deceleration coast-down so no frame advances more than about two thirds of a pocket.
  '@keyframes roulettePremiumBallSpin{0%{transform:rotate(0deg) scale(1);}5%{transform:rotate(-140.4deg) scale(1);}10%{transform:rotate(-273.6deg) scale(1);}15%{transform:rotate(-399.6deg) scale(1);}20%{transform:rotate(-518.4deg) scale(1);}25%{transform:rotate(-630deg) scale(1);}30%{transform:rotate(-734.4deg) scale(1);}35%{transform:rotate(-831.6deg) scale(1);}40%{transform:rotate(-921.6deg) scale(1);}45%{transform:rotate(-1004.4deg) scale(1);}50%{transform:rotate(-1080deg) scale(1);}55%{transform:rotate(-1148.4deg) scale(1);}60%{transform:rotate(-1209.6deg) scale(1);}65%{transform:rotate(-1263.6deg) scale(1);}70%{transform:rotate(-1310.4deg) scale(1);}75%{transform:rotate(-1350deg) scale(1);}80%{transform:rotate(-1382.4deg) scale(1);}85%{transform:rotate(-1407.6deg) scale(.98);}90%{transform:rotate(-1425.6deg) scale(1.03);}95%{transform:rotate(-1436.4deg) scale(1);}100%{transform:rotate(-1440deg) scale(1);}}', // Coast the ball down over exactly four turns so it lands on its authoritative pocket without an end-of-animation pop.
  '@keyframes rouletteBallSettle{0%{transform:scale(.72);opacity:.35;}58%{transform:scale(1.14);opacity:1;}100%{transform:scale(1);opacity:1;}}', // Ease the ball into its authoritative pocket.
  '@keyframes roulettePremiumBallDescent{0%{transform:translateY(0px);}46%{transform:translateY(0px);}60%{transform:translateY(12px);}70%{transform:translateY(27px);}77%{transform:translateY(18px);}85%{transform:translateY(26px);}91%{transform:translateY(21px);}96%{transform:translateY(24.5px);}100%{transform:translateY(24px);}}', // Sample the rim departure, two pocket-separator bounces, and final capture as translate-only stops.
  '@keyframes rouletteResultBloom{0%{transform:scale(.6);opacity:.2;}55%{transform:scale(1.16);opacity:1;}100%{transform:scale(1);opacity:1;}}', // Scale the settled pocket badge in with transform and opacity only.
  '@keyframes rouletteCellReveal{0%{filter:brightness(2.1);}100%{filter:brightness(1);}}', // Fade the winning-cell flash back to the held outline highlight.
  '@keyframes roulettePillPop{0%{transform:scale(.4);opacity:0;}70%{transform:scale(1.18);opacity:1;}100%{transform:scale(1);opacity:1;}}', // Pop the newest history pill without moving neighbouring pills.
  '.roulette-drawer-title{display:flex;align-items:center;justify-content:space-between;gap:8px;}', // Keep drawer heading and phase badge aligned.
  '.roulette-drawer-title h3{margin:0;color:var(--gold);font-family:var(--font-display);font-size:24px;}', // Treat the bet slip or settlement as premium table furniture.
  '.roulette-phase-badge{padding:4px 8px;border:1px solid var(--border);border-radius:999px;background:rgba(218,175,70,.07);color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em;}', // Add a compact table-state badge.
  '.roulette-premium .stable-list{min-height:92px;max-height:154px;overflow:auto;}', // Reserve slip height while containing long bet histories.
  '.roulette-settlement-card{display:grid;grid-template-columns:1fr auto;align-items:center;min-height:66px;margin:8px 0;padding:11px;border:1px solid var(--gold);border-radius:10px;background:linear-gradient(135deg,rgba(255,217,120,.1),rgba(118,25,31,.14));}', // Integrate settlement value as a compact ledger-backed card.
  '.roulette-settlement-card b{display:block;color:var(--gold);}', // Keep the settlement heading readable.
  '.roulette-settlement-card span{display:block;margin-top:0;color:var(--gold);font-size:15px;font-weight:1000;}', // Elevate the human net above raw log detail.
  '.roulette-spark-bars{display:grid;grid-template-columns:repeat(8,1fr);align-items:end;gap:6px;height:62px;margin:7px 0;padding:8px;border:1px solid rgba(255,255,255,.1);border-radius:9px;background:rgba(0,0,0,.18);}', // Reserve the recent-stats chart inside a compact rail card.
  '.roulette-spark-bars i{display:block;min-height:8px;border-radius:5px 5px 2px 2px;background:linear-gradient(180deg,#e8c760,#8e1822);box-shadow:0 3px 8px rgba(0,0,0,.28);}', // Render live frequency bars with casino gold-to-red depth.
  '.roulette-history-pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px;}', // Keep recent pockets in a stable wrapping row.
  '.roulette-history-pills span{display:grid;place-items:center;width:29px;height:29px;border:1px solid rgba(255,255,255,.14);border-radius:50%;color:var(--text);font-size:10px;}', // Render results as compact physical pocket tokens.
  '.roulette-history-pills span.red{background:linear-gradient(160deg,#c22433,#7c1220)!important;}', // Paint red history pockets with the table's lacquered red.
  '.roulette-history-pills span.black{background:linear-gradient(160deg,#2b2f2e,#0a0d0c)!important;}', // Paint black history pockets with the table's graphite black.
  '.roulette-history-pills span.green{background:linear-gradient(160deg,#0f9152,#065a31)!important;}', // Paint zero history pockets with the table's emerald green.
  '.roulette-history-pills span.result-cell{border-color:#e8c760;background:#e8c760!important;color:#1f1400;font-weight:1000;}', // Highlight the latest settled pocket.
  '.roulette-premium .details-drawer>h3,.roulette-premium .details-drawer>h4{color:var(--gold);text-transform:uppercase;font-size:11px;letter-spacing:.08em;}', // Give secondary drawer sections one quiet hierarchy.
  '.roulette-premium .details-drawer .mini-table{font-size:11px;}', // Keep scoreboard rows compact.
  '.roulette-premium .details-drawer .stat-bars{max-height:110px;overflow:auto;}', // Contain long hot-number output inside the drawer.
  '.roulette-premium .danger{min-width:64px;}', // Keep localized remove controls explicit.
  '@media (min-width:1201px){.roulette-premium .stable-list,.roulette-premium .details-drawer .stat-bars{max-height:none;overflow:visible;}}', // Let drawer data expand into its single governed desktop rail scroll surface.
  '@media (max-width:1800px){.roulette-premium .game-layout{grid-template-columns:220px minmax(0,1fr) 235px;gap:12px;}.roulette-premium .roulette-stage{grid-template-columns:220px minmax(0,1fr);}.roulette-premium .wheel-card{grid-template-columns:1fr;grid-template-rows:minmax(0,1fr) 104px;}.roulette-premium .roulette-wheel{max-width:214px;}.roulette-premium .control-rail,.roulette-premium .details-drawer{padding:10px;}.roulette-premium .game-title,.roulette-drawer-title h3{font-size:20px;}.roulette-control-section{margin-top:7px;}.roulette-advanced{margin-top:6px;}.roulette-advanced summary{padding:7px 8px;}.roulette-premium .stable-list{min-height:70px;}}', // Compact mid-desktop rails while the stage-owned height continuously fits the fixed betting board. (UX-026)
  '@media (min-width:1201px) and (max-width:1500px) and (max-height:820px){.roulette-premium .roulette-header{min-height:54px;}.roulette-premium h1{font-size:40px;}}', // Compress only the compact-desktop header because the board now derives its height from the remaining stage.
  '@media (max-width:1200px){.casino-page:has(.roulette-premium){overflow:auto;}.game-screen:has(.roulette-premium){height:auto;min-height:calc(100vh - 146px);overflow:visible;}.roulette-premium{height:auto;}.roulette-premium .game-layout{grid-template-columns:1fr;grid-template-rows:auto;height:auto;overflow:visible;contain:none;}.roulette-premium .game-stage{grid-template-rows:auto auto;overflow:visible;}.roulette-premium .roulette-stage{grid-template-columns:1fr;height:auto;min-height:590px;overflow:visible;}.roulette-premium .wheel-card{grid-template-columns:300px minmax(0,1fr);grid-template-rows:1fr;height:auto;min-height:300px;}.roulette-premium .roulette-wheel{max-width:286px;}.roulette-table-shell{height:590px;}.roulette-premium .control-rail,.roulette-premium .details-drawer{overflow:visible;}}', // Restore intrinsic document-scrolling geometry only at the shared stacked-layout breakpoint.
  '@media (max-width:900px){.roulette-premium .roulette-stage{grid-template-columns:1fr;}.roulette-premium .wheel-card{grid-template-columns:280px minmax(0,1fr);grid-template-rows:1fr;min-height:290px;}.roulette-premium .roulette-wheel{max-width:270px;}.roulette-table-shell{height:520px;}.roulette-premium h1{font-size:38px;}}', // Recompose the wheel console and fit the complete table on tablet widths.
  '@media (max-width:720px){.roulette-premium .wheel-card{grid-template-columns:1fr;grid-template-rows:minmax(260px,1fr) 110px;}.roulette-table-shell{height:461px;}.roulette-settings{grid-template-columns:1fr;}}', // Keep Roulette functional on small responsive viewports without page overflow.
  '@media (max-width:560px){.roulette-fast-grid,.roulette-call-grid,.roulette-secondary-actions{grid-template-columns:1fr 1fr;}.roulette-table-shell{height:340px;}.roulette-premium .fixed-result{margin-inline:8px;}}', // Scale the fixed hit-map board while retaining every existing selector on narrow screens.
].join(''); // Combine Roulette-only CSS chunks into one style payload.

// Store the route root so async callbacks can rerender the currently mounted view.
let root = null;
// Store the latest Roulette state payload from the frozen API.
let state = null;
// Store the active bet catalog so click handlers can place documented bet types.
let catalog = [];
// Remember which wheel mode owns the cached static catalog so route remounts avoid repeat payloads. (TEST-166)
let catalogMode = null;
// Store the selected chip amount independently of locale and route rerenders.
let chip = 5;
// Store the mounted autoplay element so unmount can stop any local loop.
let autoBox = null;
// Store the spot-overlay preference across rerenders and locale changes.
let showSpots = false;
// Store bot panel markup so route rerenders do not flash an empty bot region.
let botPanelCache = '';
// Store the latest stats payload so locale-only rerenders do not call game APIs.
let lastStats = {};
// Store the latest actual spin result without ever inventing a zero fallback.
let lastSpinResult = null;
// Store the latest result color for result narration and styling.
let lastSpinColor = null;
// Store the latest settled round id for the stage toolbar.
let lastRoundId = null;
// Store the current visual phase so betting, spinning, and settlement regions stay stable.
let uiPhase = 'betting';
// Store human settlement rows from the latest spin for presentation-only settlement rendering.
let lastSettlements = [];
// Store the latest human net based on existing debits plus settlement credits.
let lastHumanNet = 0;
// Store the current spin guard so duplicate spin requests cannot start.
let spinBusy = false;
// Store the i18n unsubscribe callback so unmount does not leak locale listeners.
let localeUnsubscribe = null;
// Store player-opened progressive disclosure ids across spin-driven rerenders.
const openDisclosures = new Set();
// Store the persistent rotor rest angle so the wheel keeps orientation continuity between spins.
let wheelRestAngle = 0;
// Store the ball's current orbital angle measured clockwise from the top of the bowl.
let ballOrbitAngle = 0;
// Store the ball's current radial depth where zero is the outer track and positive values sit in a pocket.
let ballDepth = 0;
// Store the route-owned motion timer scope so spin timers cancel on navigation and reload. (MOTION-002)
let motionScope = null;
// Store a deferred locale repaint request raised while a spin animation owns the live DOM.
let pendingLocaleRender = false;
// Store the round whose settled render is fresh so settle choreography plays once and never on repaints.
let freshSettleRoundId = null;
// Store a monotonically increasing route generation so abandoned async work cannot target a remount.
let mountGeneration = 0;
// Store the one active spin completion so unmount can abort it exactly once.
let activeSpinCompletion = null;
// Store pending motion-promise resolvers so timer cancellation also releases awaiting game code.
const pendingMotionWaiters = new Set();

// Create one exactly-once Roulette completion guard for settle-versus-abort ownership. (ROU-072)
export function createRouletteSpinCompletion({ isCurrent = () => true, onComplete = () => {} } = {}) {
  // Require an ownership predicate so stale continuations cannot silently become current.
  if (typeof isCurrent !== 'function') throw new TypeError('isCurrent must be a function');
  // Require a completion observer so focused tests and callers share one deterministic seam.
  if (typeof onComplete !== 'function') throw new TypeError('onComplete must be a function');
  // Store the terminal outcome only after the first successful completion.
  let outcome = null;
  // Complete once with one reviewed outcome and reject duplicate terminal continuations.
  const complete = value => {
    // Reject repeated settle, abort, or cross-terminal completion.
    if (outcome !== null) return false;
    // Record the terminal result before notifying an observer.
    outcome = value;
    // Notify the bounded observer exactly once.
    onComplete(value);
    // Confirm that this call owned terminal completion.
    return true;
  };
  // Return an immutable surface so callers cannot replace the ownership or completion rules.
  return Object.freeze({
    // Report current ownership only while this action is still pending.
    isCurrent: () => outcome === null && Boolean(isCurrent()),
    // Complete one live action as visibly settled.
    settle: () => complete('settled'),
    // Complete one abandoned or failed action as aborted.
    abort: () => complete('aborted'),
    // Expose the low-cardinality terminal outcome for deterministic cleanup decisions.
    get outcome() { return outcome; },
  });
}

// Create one cancel-releasable Roulette motion wait used by both runtime teardown and fake-clock proof. (ROU-072)
export function createRouletteMotionWait(register) {
  // Require a scheduler registration callback so the wait cannot silently omit timer ownership.
  if (typeof register !== 'function') throw new TypeError('register must be a function');
  // Store whether the promise already reached its only terminal resolution.
  let completed = false;
  // Retain the resolver after promise construction so route disposal can release it.
  let finish = null;
  // Build the promise before exposing its cancellation boundary.
  const promise = new Promise((resolve, reject) => {
    // Resolve exactly once whether the timer fires or route teardown cancels it.
    finish = () => {
      // Reject duplicate timer and teardown completion.
      if (completed) return false;
      // Mark completion before releasing awaiting code.
      completed = true;
      // Resolve the one owned wait.
      resolve();
      // Confirm this call completed the wait.
      return true;
    };
    // Start protected registration so scheduler failures remain observable.
    try {
      // Give the scheduler only the exactly-once resolver.
      register(finish);
    // Reject construction when a live scheduler cannot accept the callback.
    } catch (error) {
      // Mark the wait terminal before rejecting it.
      completed = true;
      // Preserve the scheduler diagnostic for the guarded spin path.
      reject(error);
    }
  });
  // Return immutable promise and cancellation ownership.
  return Object.freeze({
    // Expose the one awaited completion.
    promise,
    // Let route teardown release a canceled timer promise exactly once.
    cancel: () => finish(),
    // Expose terminal state for deterministic fake-clock assertions.
    get completed() { return completed; },
  });
}

// Report one closed-vocabulary Roulette presentation completion to an optional test observer.
function reportRoulettePresentationCompletion(outcome) {
  // Keep production behavior inert unless a focused browser-free test installs the bounded probe.
  try { window.__casinoPresentationProbe?.({ game: 'roulette', outcome }); } catch (_) {}
}

// Refresh the settled wallet only while the captured Roulette action still owns the mounted route.
async function refreshBalanceForCompletion(completion) {
  // Refuse to begin a shared wallet request for an action already invalidated by teardown.
  if (!completion.isCurrent()) return false;
  // Use the authenticated current-user endpoint when the shared shell owns wallet identity.
  if (window.CasinoCurrentUser) {
    // Fetch wallet data without mutating shared shell state inside the awaited operation.
    const currentUser = await api('/api/v2/me');
    // Reject a response that returned after this action was unmounted or superseded.
    if (!completion.isCurrent()) return false;
    // Publish the still-current session payload only after the ownership check.
    window.CasinoCurrentUser = currentUser;
    // Resolve the browser event constructor without assuming it exists in browser-free seams.
    const CurrentUserEvent = window.CustomEvent || globalThis.CustomEvent;
    // Notify the shell only while this action retains ownership.
    if (CurrentUserEvent) window.dispatchEvent(new CurrentUserEvent('casino-current-user', { detail: currentUser }));
    // Render the accepted payload after the same ownership check.
    renderTokenBalance(currentUser);
    // Confirm that the guarded current-user wallet was published.
    return true;
  }
  // Fetch the legacy player wallet without applying it during the awaited operation.
  const data = await api(`/api/v1/players/${encodeURIComponent(currentPlayerId())}`);
  // Reject a legacy response that returned after route teardown or remount.
  if (!completion.isCurrent()) return false;
  // Resolve the shared wallet amount node only after ownership remains current.
  const balance = document.getElementById('balance');
  // Publish the exact two-decimal fake-token balance when the shell exposes its amount node.
  if (balance) balance.textContent = tokenAmount(data.player.balance);
  // Resolve the shared wallet label after the same ownership check.
  const label = document.getElementById('balance-label');
  // Preserve the existing explicit fake-token label for assistive technology.
  if (label) label.textContent = 'Play token balance';
  // Confirm that the guarded legacy wallet was published.
  return true;
}

// Resolve a Roulette-owned localized string from the game domain.
const rt = (key, params = {}) => t(key, params, GAME_DOMAIN);
// Wrap an action handler so a rejected request reaches the player instead of vanishing.
// Every wagering control here posted with no catch, so a rejection (most commonly INSUFFICIENT_FUNDS)
// became an unhandled promise rejection that only reached admin telemetry: the player clicked Bet or
// Spin and nothing visibly happened. Prefer the server's localized error key when it supplies one, and
// fall back to a generic localized message rather than showing raw English. (issue #422)
const guarded = handler => async (...args) => {
  // Start protected execution so no control can fail silently.
  try {
    // Run the original handler unchanged and preserve its resolved value.
    return await handler(...args);
  // Surface any rejection through the shared toast outlet.
  } catch (error) {
    // Prefer a localized key the backend named, then the generic action failure text.
    // Prefer client-owned validation copy, then the shared API helper's localized message. (I18N-011)
    toast(error?.errorKey ? rt(error.errorKey) : (error?.playerSafe ? error.message : rt('errors.actionFailed')));
    // Report the failure for admin telemetry without altering the player-visible message.
    logClient('roulette_action_failed', { code: error?.code || null });
  }
};
// Resolve and escape a localized string before inserting it into HTML.
const text = (key, params = {}) => safe(rt(key, params));
// Resolve and escape one shared-domain label for progressive disclosure controls.
const sharedText = (key, domain) => safe(t(key, {}, domain));
// Return an open attribute when the player left one optional control group expanded.
const disclosureOpen = id => (openDisclosures.has(id) ? ' open' : '');
// Return a disabled attribute while a spin is in progress.
const disabledWhenSpinning = () => (spinBusy ? ' disabled' : '');
// Return a locale-aware numeric amount without a currency or legacy token glyph.
const amountNumber = amount => Number(amount || 0).toLocaleString(document.documentElement.lang || undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// Return an explicit localized play-token amount for Roulette-owned value displays.
const tokenMoney = amount => `${amountNumber(amount)} ${text('units.playTokens')}`;
// Return a signed localized play-token amount for settled net values.
const signedTokenMoney = amount => `${Number(amount || 0) >= 0 ? '+' : '-'}${tokenMoney(Math.abs(Number(amount || 0)))}`;
// Return a compact denomination for physical chip faces whose heading supplies the token context.
const chipMoney = amount => Number(amount || 0).toLocaleString(document.documentElement.lang || undefined, { maximumFractionDigits: 0 });

// Ensure the local premium CSS is available exactly once per document.
function ensurePremiumStyle() {
  // Branch when another mount already installed the Roulette style block.
  if (document.getElementById(PREMIUM_STYLE_ID)) return;
  // Create a style node owned by this module.
  const style = document.createElement('style');
  // Set the id so future mounts can find the existing style block.
  style.id = PREMIUM_STYLE_ID;
  // Set the CSS text without touching the shared stylesheet.
  style.textContent = PREMIUM_STYLE;
  // Attach the style block to the document head before the first render.
  document.head.append(style);
}

// Render the localized placeholder shown while bot controller data loads.
function loadingBotPanelHtml() {
  // Return the control-plane placeholder using Roulette-owned resources.
  return `<div class="roulette-control-plane"><b>${text('bots.loadingTitle')}</b><span>${text('bots.loading')}</span></div>`;
}

// Return the latest actual result entry recorded by the backend state.
function latestResultEntry() {
  // Store the history array so missing state falls back safely.
  const history = state?.last_results || [];
  // Return the final history entry or null when no real spin has occurred.
  return history.length ? history[history.length - 1] : null;
}

// Apply a frozen API payload to local render state without changing contracts.
function applyPayload(payload) {
  // Update game state when the endpoint returned one.
  if (payload?.state) state = payload.state;
  // Update bet catalog when the endpoint returned one.
  if (payload?.catalog) catalog = payload.catalog;
  // Cache shell-visible player rows when the endpoint returned them.
  if (payload?.players) window._lastPlayers = payload.players;
  // Cache stats when the endpoint returned them.
  if (payload?.stats) lastStats = payload.stats;
  // Store the latest real result entry after state has been updated.
  const latest = latestResultEntry();
  // Branch only when a backend result exists so the wheel never defaults to fake zero.
  if (latest) {
    // Store the actual result number from backend history.
    lastSpinResult = latest.result;
    // Store the actual result color from backend history.
    lastSpinColor = latest.color;
    // Store the actual round id from backend history.
    lastRoundId = latest.round_id;
  }
}

// Add the opt-in play projection without changing any default frozen-v1 response.
function compactPath(path) {
  // Preserve existing query parameters when a caller already selected a resource.
  const separator = path.includes('?') ? '&' : '?';
  // Return one explicit projection value that malformed duplicate values cannot activate server-side.
  return `${path}${separator}projection=play`;
}

// Load the large mode-owned bet catalog at most once per active wheel mode.
async function ensureCatalog(mode) {
  // Normalize absent or hostile state to the existing double-zero default.
  const requestedMode = mode === 'single' ? 'single' : 'double';
  // Reuse the current mode's immutable rules catalog across actions and route remounts.
  if (catalog.length && catalogMode === requestedMode) return catalog;
  // Fetch the unchanged frozen catalog endpoint independently from player state.
  const payload = await api(`/api/v1/games/roulette/bet-catalog?mode=${encodeURIComponent(requestedMode)}`);
  // Replace the cached catalog only after one complete successful response.
  catalog = payload.catalog || [];
  // Bind the cache to the exact mode that produced it.
  catalogMode = requestedMode;
  // Return the loaded catalog for focused tests and callers that await readiness.
  return catalog;
}

// Fetch state, catalog, stats, players, and bot presentation for the initial mount.
async function load() {
  // Initialize the localized bot placeholder before the first visible render.
  botPanelCache = loadingBotPanelHtml();
  // Load player-specific state without retransmitting the static bet catalog. (TEST-166)
  const payload = await api(currentPlayerPath(compactPath('/api/v1/games/roulette/state')));
  // Apply the response to local render caches.
  applyPayload(payload);
  // Load the current mode's immutable catalog once before rendering any wager controls.
  await ensureCatalog(payload?.state?.mode);
  // Render the game before slower bot markup resolves.
  render();
  // Refresh bot panel markup through the shared bot controller helper.
  await updateBotPanel();
  // Refresh the shared shell wallet after game state loads.
  await refreshBalance();
}

// Refresh the bot panel inside the exact captured route generation without remounting the whole game.
async function updateBotPanel({ expectedRoot = root, expectedGeneration = mountGeneration } = {}) {
  // Retain the awaited bot markup without publishing it through the mutable global route.
  let nextBotPanel;
  // Protect the rejection path so stale cleanup cannot escape to the generic player-feedback wrapper.
  try {
    // Load bot markup through the shared controller contract.
    nextBotPanel = await botPanelHtml('roulette');
  // Distinguish an abandoned route failure from a genuine current-route failure.
  } catch (error) {
    // Suppress a failure that returned only after teardown or a distinct remount.
    if (root !== expectedRoot || mountGeneration !== expectedGeneration) return false;
    // Preserve existing feedback and telemetry behavior for the still-current route.
    throw error;
  }
  // Reject markup that returned after teardown or after a distinct route generation remounted.
  if (root !== expectedRoot || mountGeneration !== expectedGeneration) return false;
  // Publish the markup cache only while the captured route still owns it.
  botPanelCache = nextBotPanel;
  // Find the bot panel only inside the captured route root.
  const panel = expectedRoot?.querySelector('#botPanel');
  // Replace bot markup only when that exact Roulette route remains mounted.
  if (panel) panel.innerHTML = botPanelCache;
  // Confirm the captured route accepted the refresh.
  return true;
}

// Return the current player-owned open-round bets.
function humanBets() {
  // Filter open bets to the active player while tolerating unloaded state.
  return state?.open_round?.bets?.filter(bet => bet.player_id === currentPlayerId()) || [];
}

// Return the total human stake for a supplied or current bet list.
function humanBetTotal(bets = humanBets()) {
  // Sum numeric bet amounts for total and settlement displays.
  return bets.reduce((total, bet) => total + Number(bet.amount || 0), 0);
}

// Find a bet catalog entry by predicate.
function betBy(predicate) {
  // Return the matching catalog entry or undefined when the bet is unavailable.
  return catalog.find(predicate);
}

// Compare two covered-number lists as unordered string sets so ordering never masks a mismatch. (issue #222)
function sameCovered(a, b) {
  // Normalize the first list to a string set for order-independent comparison.
  const first = new Set((a || []).map(String));
  // Normalize the second list to a string set for order-independent comparison.
  const second = new Set((b || []).map(String));
  // Require identical size and full membership in both directions.
  return first.size === second.size && [...first].every(value => second.has(value));
}

// Resolve an even-money or range outside cell to its canonical covered-number set. (issue #222, ROU-030)
function outsideIdentity(type) {
  // Build the ordered single-zero pocket list once for every derived outside set.
  const pockets = Array.from({ length: 36 }, (_, index) => index + 1);
  // Resolve the red outside cell from the shared red-pocket table.
  if (type === 'red') return { type: 'red', covered: pockets.filter(number => RED_NUMBERS.has(number)).map(String) };
  // Resolve the black outside cell as the complement of the red-pocket table.
  if (type === 'black') return { type: 'black', covered: pockets.filter(number => !RED_NUMBERS.has(number)).map(String) };
  // Resolve the low outside cell to pockets one through eighteen.
  if (type === 'low') return { type: 'low', covered: pockets.filter(number => number <= 18).map(String) };
  // Resolve the high outside cell to pockets nineteen through thirty-six.
  if (type === 'high') return { type: 'high', covered: pockets.filter(number => number >= 19).map(String) };
  // Resolve the even outside cell to even pockets.
  if (type === 'even') return { type: 'even', covered: pockets.filter(number => number % 2 === 0).map(String) };
  // Resolve the odd outside cell to odd pockets.
  if (type === 'odd') return { type: 'odd', covered: pockets.filter(number => number % 2 === 1).map(String) };
  // Return null so an unknown outside type aborts safely.
  return null;
}

// Compute the canonical bet identity a clicked board cell must resolve to before any wager posts. (issue #222)
function expectedIdentity(cellKey) {
  // Split the stable cell key into its kind and argument.
  const [kind, arg] = String(cellKey || '').split(':');
  // Resolve a straight-up number cell to its single covered pocket.
  if (kind === 'num') return { type: 'straight', covered: [String(arg)] };
  // Resolve a dozen cell (1..3) to its twelve-number range.
  if (kind === 'dozen') { const index = Number(arg); return index >= 1 && index <= 3 ? { type: 'dozen', covered: Array.from({ length: 12 }, (_, offset) => String((index - 1) * 12 + offset + 1)) } : null; }
  // Resolve a column cell (1..3) to its twelve-number arithmetic column.
  if (kind === 'column') { const column = Number(arg); return column >= 1 && column <= 3 ? { type: 'column', covered: Array.from({ length: 12 }, (_, offset) => String(column + offset * 3)) } : null; }
  // Resolve an even-money or range outside cell through the shared outside helper.
  if (kind === 'outside') return outsideIdentity(arg);
  // Resolve an inside hotspot to its authoritative catalog covered numbers by stable bet id.
  if (kind === 'spot') { const bet = betBy(entry => entry.id === arg); return bet ? { type: bet.type, covered: (bet.covered_numbers || []).map(String) } : null; }
  // Return null for an unrecognized cell key so the caller aborts safely.
  return null;
}

// Resolve the catalog bet a clicked cell represents while guarding against hit-target drift. (issue #222)
function resolveCellBet(cellKey) {
  // Compute the canonical identity the clicked cell must map to.
  const expected = expectedIdentity(cellKey);
  // Abort when the cell key is unknown or unavailable this round.
  if (!expected) return { bet: null, expected: null };
  // Read the kind so hotspot cells can resolve by their stable catalog id.
  const [kind, arg] = String(cellKey).split(':');
  // Resolve inside hotspots directly by their stable catalog id.
  const bet = kind === 'spot' ? betBy(entry => entry.id === arg) : betBy(entry => entry.type === expected.type && sameCovered(entry.covered_numbers, expected.covered));
  // Return both the resolved catalog bet and the canonical expectation for assertion.
  return { bet, expected };
}

// Build the stable identity attributes every bet cell carries so clicks resolve and verify deterministically. (issue #222)
function cellAttrs(cellKey, type, covered) {
  // Emit the stable cell key plus the authoritative type and covered numbers as data attributes.
  return `data-cell-key="${safe(cellKey)}" data-bet-type="${safe(type)}" data-covered="${safe((covered || []).join(','))}"`;
}

// Place a wager for one clicked board cell after verifying its canonical hit-target identity. (issue #222)
function placeBetForCell(button) {
  // Read the stable cell key embedded on the clicked control.
  const cellKey = button?.dataset?.cellKey;
  // Resolve the catalog bet and its canonical expectation from the stable key.
  const { bet, expected } = resolveCellBet(cellKey);
  // Place the resolved bet while passing the expectation for the pre-POST assertion.
  return placeBet(bet, expected, { cellKey, embeddedType: button?.dataset?.betType, embeddedCovered: (button?.dataset?.covered || '').split(',').filter(Boolean) });
}

// Reset settlement drawer state when the player starts editing a new open round.
function markBettingPhase() {
  // Put the UI back into betting mode while preserving the last real result.
  uiPhase = 'betting';
}

// Place one documented Roulette bet using the existing public API.
async function placeBet(bet, expected = null, source = null, amount = chip) {
  // Branch when a click target no longer maps to a legal catalog bet.
  if (!bet) {
    // Show a localized error without touching wallet or game state.
    toast(rt('errors.betUnavailable'));
    // Stop after reporting the unavailable bet.
    return;
  }
  // Verify the resolved wager matches the clicked cell's canonical identity before any POST. (issue #222, ROU-010/011/030)
  if (expected) {
    // Detect any drift between the resolved bet and the clicked cell's canonical type or covered numbers.
    const typeMismatch = bet.type !== expected.type;
    // Detect covered-number drift so a rebuilt hit target can never post a different region.
    const coveredMismatch = !sameCovered(bet.covered_numbers, expected.covered);
    // Detect a rebuilt DOM node whose embedded identity drifted from its own catalog bet.
    const embeddedMismatch = source && source.embeddedCovered && source.embeddedCovered.length && !sameCovered(bet.covered_numbers, source.embeddedCovered);
    // Abort the wager when the clicked cell no longer maps to a consistent hit target.
    if (typeMismatch || coveredMismatch || embeddedMismatch) {
      // Record the exact mismatch for admin diagnosis without posting a wrong wager.
      logClient('roulette_bet_target_mismatch', { cell_key: source?.cellKey || null, expected, resolved: { type: bet.type, covered_numbers: bet.covered_numbers }, embedded_covered: source?.embeddedCovered || null });
      // Show a localized safety error and abort before touching the wallet.
      toast(rt('errors.betUnavailable'));
      // Stop so a mismatched hit target can never post the wrong bet.
      return;
    }
  }
  // Post the bet through the frozen v1 endpoint.
  const payload = await post(compactPath('/api/v1/games/roulette/bets'), withCurrentPlayer({ amount, bet_type: bet.type, covered_numbers: bet.covered_numbers, label: bet.label }));
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the premium table and drawer.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because bets debit immediately through the ledger.
  await refreshBalance();
  // Play the existing chip feedback sound.
  clickSound(540, .05);
}

// Place a racetrack or call bet through the documented API.
async function placeCall(type) {
  // Read the optional call/final number from the current control rail.
  const number = root.querySelector('#callNumber')?.value || undefined;
  // Post the call bet using the existing v1 payload shape.
  const payload = await post(compactPath('/api/v1/games/roulette/call-bet'), withCurrentPlayer({ amount: chip, call_type: type, number }));
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the premium table and drawer.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because call bets debit immediately through the ledger.
  await refreshBalance();
  // Play the existing call-bet feedback sound.
  clickSound(650, .05);
}

// Clear one human bet by id through the documented refund endpoint.
async function clearBet(id) {
  // Delete the bet through the frozen v1 endpoint.
  const payload = await del(compactPath(`/api/v1/games/roulette/bets/${id}`), withCurrentPlayer());
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the table and bet slip after the refund.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because clearing a bet credits the player.
  await refreshBalance();
}

// Clear all human bets through the documented refund endpoint.
async function clearAll() {
  // Post the clear request through the frozen v1 endpoint.
  const payload = await post(compactPath('/api/v1/games/roulette/clear'), withCurrentPlayer());
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the table and empty bet slip.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because clearing bets credits the player.
  await refreshBalance();
}

// Rebuild the previous human bet template through the documented endpoint.
async function rebet() {
  // Post the rebet request through the frozen v1 endpoint.
  const payload = await post(compactPath('/api/v1/games/roulette/rebet'), withCurrentPlayer());
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender the table and bet slip.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
  // Refresh the wallet because rebet debits immediately through the ledger.
  await refreshBalance();
  // Play the existing rebet feedback sound.
  clickSound(620, .06);
}

// Persist Roulette mode and zero-rule settings through the documented endpoint.
async function settings() {
  // Read the selected wheel mode from the control rail.
  const mode = root.querySelector('#mode')?.value;
  // Read the selected zero rule from the control rail.
  const zeroRule = root.querySelector('#zero')?.value;
  // Post settings without adding or changing any payload fields.
  const payload = await post(compactPath('/api/v1/games/roulette/settings'), withCurrentPlayer({ mode, zero_rule: zeroRule }));
  // Apply returned state, catalog, players, and stats.
  applyPayload(payload);
  // Replace the immutable catalog only when the accepted setting changed wheel mode.
  await ensureCatalog(payload?.state?.mode);
  // Mark the route as actively accepting bets.
  markBettingPhase();
  // Rerender settings, table geometry, and bet targets.
  render();
  // Refresh the bot panel after the rerender.
  await updateBotPanel();
}

// Ensure autoplay has an open bet template before starting an automatic spin.
async function ensureBetForAuto() {
  // Branch when no open bet exists but the backend has a saved template.
  if (humanBets().length === 0 && (state.last_bet_template || []).length) await rebet();
}

// Wait one bounded interval through the route-owned motion scope instead of a raw timer. (MOTION-002)
function waitMotion(ms) {
  // Resolve immediately when the route scope is gone so continuation semantics match the legacy timer path.
  if (!motionScope || motionScope.disposed) return Promise.resolve();
  // Create the cancel-releasable wait through the same primitive covered by focused fake-clock tests.
  const waiter = createRouletteMotionWait(resolve => motionScope.schedule(resolve, ms, { reducedMotion: false }));
  // Track the wait object so teardown can resolve it after canceling the underlying timer.
  pendingMotionWaiters.add(waiter);
  // Release route ownership after either timer or cancellation completes.
  waiter.promise.then(() => pendingMotionWaiters.delete(waiter), () => pendingMotionWaiters.delete(waiter));
  // Return the one promise awaited by the spin flow.
  return waiter.promise;
}

// Release every route-owned motion promise after its underlying timer was cancelled.
function releaseMotionWaiters() {
  // Snapshot the set because each resolver removes itself.
  const waiters = Array.from(pendingMotionWaiters);
  // Resolve every abandoned wait exactly once.
  for (const waiter of waiters) waiter.cancel();
}

// Lift the captured ball back onto the outer track the moment a spin's first frame is live.
function liftBallOffPocket() {
  // Find the radial wrapper in the freshly rendered spinning wheel.
  const radial = root?.querySelector('.ball-radial');
  // Skip safely when the wheel is not mounted.
  if (!radial) return;
  // Arm the short rim-lift transition on the live wrapper.
  radial.style.transition = `transform ${BALL_LIFT_MS}ms cubic-bezier(.3,.1,.4,1)`;
  // Move the ball to track depth so its launch circuits stay concentric with the hub.
  radial.style.transform = 'translateY(0px)';
  // Record track depth so any mid-spin repaint renders the lifted pose rather than the stale pocket.
  ballDepth = 0;
}

// Steer the live wheel and ball wrappers so the ball physically lands on the authoritative pocket. (ROU-053, ROU-054)
function launchHonestLanding(payload, revealMs, revealStartedAt) {
  // Read the authoritative pocket committed by the backend for this exact spin.
  const resultPocket = String(payload?.round?.result ?? '');
  // Store the wheel order currently rendered so index math matches the visible rotor.
  const nums = wheelNums();
  // Locate the winning pocket on the rendered wheel.
  const targetIndex = nums.indexOf(resultPocket);
  // Skip wrapper travel rather than inventing a pocket when the result is not on this wheel. (ROU-051)
  if (targetIndex < 0 || !root) return 0;
  // Find the rotor-orientation wrapper installed by the spinning render.
  const orient = root.querySelector('.wheel-orient');
  // Find the ball's orbital wrapper.
  const orbit = root.querySelector('.ball-orbit');
  // Find the ball's radial-depth wrapper.
  const radial = root.querySelector('.ball-radial');
  // Stop safely when a rerender or route transition removed the animated wheel.
  if (!orient || !orbit || !radial) return 0;
  // Seed decorative pocket scatter from the committed round id so one round always lands the same way.
  const random = createSeededRandom(String(payload?.round?.round_id || 'roulette-round'));
  // Compute the deterministic wrapper targets and travel budget through the tested pure plan.
  const plan = computeLandingPlan({ wheelAngle: wheelRestAngle, ballAngle: ballOrbitAngle, pocketIndex: targetIndex, pocketCount: nums.length, random, revealMs, elapsedMs: performance.now() - revealStartedAt });
  // Stop safely when the plan rejects the pocket rather than inventing a landing. (ROU-051)
  if (!plan) return 0;
  // Read the rotor's committed rest target from the plan.
  const wheelTarget = plan.wheelTarget;
  // Read the ball's committed orbital target from the plan.
  const ballTarget = plan.ballTarget;
  // Read the wrapper travel budget from the plan.
  const travelMs = plan.travelMs;
  // Force one layout read so the browser commits the start frame before target transforms change. (PR #311 pattern)
  orient.getBoundingClientRect();
  // Coast the rotor wrapper to its new rest orientation over the remaining reveal budget.
  orient.style.transition = `transform ${travelMs}ms cubic-bezier(.16,.7,.16,1)`;
  // Commit the rotor wrapper's target angle.
  orient.style.transform = `rotate(${wheelTarget}deg)`;
  // Coast the ball wrapper onto the winning pocket with its own later-peaking deceleration profile.
  orbit.style.transition = `transform ${travelMs}ms cubic-bezier(.22,.61,.12,1)`;
  // Commit the ball wrapper's target angle.
  orbit.style.transform = `rotate(${ballTarget}deg)`;
  // Occupy the second half of the wrapper travel with the pocket descent.
  const descentMs = Math.round(travelMs * .5);
  // Arm the descent only while the route scope is live so a disposed scope degrades the descent instead of throwing.
  if (motionScope && !motionScope.disposed) {
    // Schedule the descent through the route-owned scope so navigation cancels it with the spin. (MOTION-002)
    motionScope.schedule(() => {
      // Clear the lift transition so the sampled descent keyframes own radial motion exclusively.
      radial.style.transition = 'none';
      // Publish the descent duration consumed by the keyframe animation shorthand.
      radial.style.setProperty('--rou-descent-ms', `${descentMs}ms`);
      // Start the sampled rim-departure, separator-bounce, and capture sequence.
      radial.classList.add('descending');
    }, travelMs - descentMs, { reducedMotion: false });
  }
  // Persist the normalized rest pose so the settled rerender continues this exact orientation seamlessly.
  wheelRestAngle = norm360(wheelTarget);
  // Persist the ball's normalized final orbital angle for the same seamless handoff.
  ballOrbitAngle = norm360(ballTarget);
  // Persist the captured pocket depth the descent ends on.
  ballDepth = BALL_POCKET_DEPTH;
  // Return the wrapper travel time so the caller can hold the reveal until the landing completes.
  return travelMs;
}

// Spin the Roulette wheel using the existing engine, bot, ledger, and settlement path.
async function spin(show = true) {
  // Branch when a spin is already in progress.
  if (spinBusy) return;
  // Capture the mounted route identity before any asynchronous work begins.
  const mountedRoot = root;
  // Capture the current generation so a remount cannot inherit this continuation.
  const generation = mountGeneration;
  // Create one exactly-once terminal guard bound to this route generation.
  const completion = createRouletteSpinCompletion({ isCurrent: () => root === mountedRoot && mountGeneration === generation, onComplete: reportRoulettePresentationCompletion });
  // Publish the active completion so unmount can abort it before releasing the route.
  activeSpinCompletion = completion;
  // Store the pre-spin stake after any autoplay rebet completes.
  let stakeBeforeSpin = 0;
  // Mark the spin as busy before rerendering disabled controls.
  spinBusy = true;
  // Start protected spin flow so the busy flag is always released.
  try {
    // Recreate a saved template for autoplay when needed.
    if (show) await ensureBetForAuto();
    // Stop an abandoned continuation before it can inspect or mutate the remounted route.
    if (!completion.isCurrent()) return;
    // Store the human stake after any automatic rebet is in the open round.
    stakeBeforeSpin = humanBetTotal();
    // Move the UI into the spinning phase before the backend result is displayed.
    uiPhase = 'spinning';
    // Clear previous settlement rows while the new spin is resolving.
    lastSettlements = [];
    // Read the live reduced-motion preference once at this atomic action boundary. (MOTION-005)
    const reducedMotion = prefersReducedMotion();
    // Resolve the reveal budget for this spin mode from the same three governed constants every time.
    const revealMs = reducedMotion ? REDUCED_REVEAL_MS : show ? SPIN_REVEAL_MS : AUTOPLAY_REVEAL_MS;
    // Record when the spinning frame goes live so wrapper travel ends exactly with the sampled curves.
    const revealStartedAt = performance.now();
    // Rerender immediately so animation starts before settlement display.
    render();
    // Lift the captured ball onto the track right away so its launch circuits stay concentric.
    if (show && !reducedMotion) liftBallOffPocket();
    // Let compatible bots commit their public Roulette actions before the human spin.
    await playBotRound('roulette');
    // Stop when navigation disposed this spin during the bot-control await.
    if (!completion.isCurrent()) return;
    // Play the existing wheel rolling sound trimmed to the reveal time this spin still has left.
    rouletteRollSound(Math.max(400, revealMs - (performance.now() - revealStartedAt)));
    // Post the spin request through the frozen v1 endpoint without changing payloads.
    const payload = await post(compactPath('/api/v1/games/roulette/spin'), withCurrentPlayer());
    // Reject a late backend response after route disposal without replaying, refunding, or touching a remount.
    if (!completion.isCurrent()) return;
    // Steer the live wrappers toward the authoritative pocket for full-motion human spins.
    const landingMs = show && !reducedMotion ? launchHonestLanding(payload, revealMs, revealStartedAt) : 0;
    // Hold the reveal lock until both the remaining budget and the actual landing travel complete.
    await waitMotion(Math.max(220, revealMs - (performance.now() - revealStartedAt), landingMs));
    // Reject a timer continuation released by teardown before adopting authoritative presentation state.
    if (!completion.isCurrent()) return;
    // Apply returned state, catalog, players, and stats.
    applyPayload(payload);
    // Store the authoritative result from this spin response.
    lastSpinResult = payload.round.result;
    // Store the authoritative color from this spin response.
    lastSpinColor = payload.round.result_color;
    // Store the authoritative round id from this spin response.
    lastRoundId = payload.round.round_id;
    // Mark the upcoming settled render as fresh so its one-shot choreography plays exactly once.
    freshSettleRoundId = payload.round.round_id;
    // Filter settlement rows to the human player for the drawer.
    const human = (payload.settlements || []).filter(row => row.bet.player_id === currentPlayerId());
    // Cache settlement row presentation using existing API values only.
    lastSettlements = human.map(row => ({ label: row.bet.label, amount: Number(row.bet.amount || 0), outcome: row.settlement.outcome, credit: Number(row.settlement.credit || 0) }));
    // Compute a presentation-only human net from already-debited stake and returned credits.
    lastHumanNet = human.reduce((total, row) => total + Number(row.settlement.credit || 0), 0) - stakeBeforeSpin;
    // Move the UI into the settled phase after animation lock-in.
    uiPhase = 'settled';
    // Rerender the table, result panel, stats, and settlement drawer.
    render();
    // Refresh the wallet after settlement credits are applied.
    await refreshBalanceForCompletion(completion);
    // Stop post-settlement feedback when the route was disposed during wallet reconciliation.
    if (!completion.isCurrent()) return;
    // Complete the live presentation exactly once before any optional feedback is scheduled.
    completion.settle();
    // Play the existing result feedback sound.
    clickSound(240, .08);
    // Play the existing follow-up feedback sound through the route-owned timer scope.
    if (motionScope && !motionScope.disposed) motionScope.schedule(() => clickSound(760, .08), 120, { reducedMotion: false });
    // Speak the result only for visible human spins.
    if (show) speak(rt('voice.rolled', { number: payload.round.result }), 'roulette');
  // Suppress a rejection that returned only after this action's route generation was disposed.
  } catch (error) {
    // Stop the outer guarded handler from producing stale toast or telemetry on a remounted route.
    if (!completion.isCurrent()) return;
    // Preserve the existing localized feedback and telemetry path for a genuine live-route failure.
    throw error;
  // Always release the spin guard and settle disabled controls.
  } finally {
    // Complete an error or teardown path as one abort when settlement did not already win.
    completion.abort();
    // Release active ownership only when this action is still the published spin.
    if (activeSpinCompletion === completion) activeSpinCompletion = null;
    // Stop all cleanup DOM work when this action belongs to an abandoned route generation.
    if (root !== mountedRoot || mountGeneration !== generation) return;
    // Release the busy flag even if the API or animation flow fails.
    spinBusy = false;
    // Branch when a failed spin left the UI in the temporary spinning phase.
    if (uiPhase === 'spinning') {
      // Return to betting mode so controls are usable again.
      uiPhase = 'betting';
    }
    // Clear any locale repaint deferred during the animation because the rerender below applies it.
    pendingLocaleRender = false;
    // Rerender the unlocked controls after both success and failure.
    render();
    // Start the one-shot settle choreography on the live DOM so later repaints can never replay or cut it.
    if (freshSettleRoundId !== null && uiPhase === 'settled' && root) root.querySelector('.roulette-premium')?.classList.add('just-settled');
    // Consume the fresh-settle marker after its single choreography start.
    freshSettleRoundId = null;
    // Refresh the bot panel only for the same route identity captured before the spin began.
    await updateBotPanel({ expectedRoot: mountedRoot, expectedGeneration: generation });
  }
}

// Return the color class for one Roulette number.
function numberColorClass(number) {
  // Treat zero pockets as green cells.
  if (String(number) === '0' || String(number) === '00') return 'green';
  // Return red or black based on the canonical red pocket set.
  return RED_NUMBERS.has(Number(number)) ? 'red' : 'black';
}

// Return the wheel pocket color for SVG rendering.
function pocketFill(number) {
  // Return green for zero pockets.
  if (String(number) === '0' || String(number) === '00') return '#087a43';
  // Return premium red or near-black for numbered pockets.
  return RED_NUMBERS.has(Number(number)) ? '#a91622' : '#050505';
}

// Convert polar coordinates into an SVG point.
function polar(cx, cy, radius, angle) {
  // Return the cartesian point for one polar coordinate.
  return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
}

// Build one SVG annular wedge path for a Roulette pocket.
function wedgePath(index, count) {
  // Store the wedge start angle.
  const start = (index / count) * Math.PI * 2 - Math.PI / 2;
  // Store the wedge end angle.
  const end = ((index + 1) / count) * Math.PI * 2 - Math.PI / 2;
  // Store the outer start point.
  const outerStart = polar(150, 150, 122, start);
  // Store the outer end point.
  const outerEnd = polar(150, 150, 122, end);
  // Store the inner end point.
  const innerEnd = polar(150, 150, 84, end);
  // Store the inner start point.
  const innerStart = polar(150, 150, 84, start);
  // Return the closed annular path for this pocket.
  return `M ${outerStart.x} ${outerStart.y} A 122 122 0 0 1 ${outerEnd.x} ${outerEnd.y} L ${innerEnd.x} ${innerEnd.y} A 84 84 0 0 0 ${innerStart.x} ${innerStart.y} Z`;
}

// Return the table-center coordinate for a straight-up number.
function cellCenter(number) {
  // Normalize the input to the string shape used by the catalog.
  const normalized = String(number);
  // Return the single-zero location.
  if (normalized === '0') return state.mode === 'double' ? { x: BOARD.x0 + BOARD.cw * .75, y: BOARD.y0 - 42 } : { x: BOARD.x0 + BOARD.cw * 1.5, y: BOARD.y0 - 42 };
  // Return the double-zero location.
  if (normalized === '00') return { x: BOARD.x0 + BOARD.cw * 2.25, y: BOARD.y0 - 42 };
  // Store numeric number for row and column math.
  const value = Number(normalized);
  // Store the row used by the existing fixed board geometry.
  const row = Math.floor((value - 1) / 3);
  // Store the column used by the existing fixed board geometry.
  const col = (value - 1) % 3;
  // Return the center point for this table cell.
  return { x: BOARD.x0 + col * BOARD.cw + BOARD.cw / 2, y: BOARD.y0 + row * BOARD.ch + BOARD.ch / 2 };
}

// Return the fixed board coordinate for outside bets.
function outsidePos(bet) {
  // Branch for dozen bets that sit under the number grid.
  if (bet.type === 'dozen') {
    // Find the dozen index from the catalog label.
    const idx = ['1st 12', '2nd 12', '3rd 12'].indexOf(bet.label);
    // Return the center of the matching dozen cell.
    return { x: BOARD.x0 + idx * BOARD.cw + BOARD.cw / 2, y: BOARD.y0 + 12 * BOARD.ch + 28 };
  }
  // Branch for column bets that sit under the dozen row.
  if (bet.type === 'column') {
    // Find the column index from the catalog label.
    const idx = ['Column 1', 'Column 2', 'Column 3'].indexOf(bet.label);
    // Return the center of the matching column cell.
    return { x: BOARD.x0 + idx * BOARD.cw + BOARD.cw / 2, y: BOARD.y0 + 12 * BOARD.ch + 78 };
  }
  // Store fixed side-rail locations for even-money outside bets.
  const map = { red: { x: 90, y: 290 }, black: { x: 90, y: 340 }, odd: { x: 90, y: 390 }, even: { x: 90, y: 240 }, low: { x: 90, y: 190 }, high: { x: 90, y: 440 } };
  // Return the outside position or a safe fallback.
  return map[bet.type] || { x: 50, y: 50 };
}

// Return the fixed board coordinate for a catalog bet.
function posForBet(bet) {
  // Store covered numbers so position math can average their cell centers.
  const nums = bet.covered_numbers || [];
  // Return outside layout positions directly.
  if (bet.layout_kind === 'outside') return outsidePos(bet);
  // Route pre-fix persisted bets that lack layout_kind by their outside bet type so legacy live-state chips also land on the outside rail. (issue #222)
  if (bet.layout_kind == null && ['dozen', 'column', 'red', 'black', 'odd', 'even', 'low', 'high'].includes(bet.type)) return outsidePos(bet);
  // Return the street marker location.
  if (bet.type === 'street') {
    // Store the street row from the first covered number.
    const row = Math.floor((Number(nums[0]) - 1) / 3);
    // Return the street marker point.
    return { x: BOARD.x0 - 22, y: BOARD.y0 + row * BOARD.ch + BOARD.ch / 2 };
  }
  // Return the line marker location.
  if (bet.type === 'line') {
    // Store the line row from the first covered number.
    const row = Math.floor((Number(nums[0]) - 1) / 3);
    // Return the line marker point.
    return { x: BOARD.x0 - 22, y: BOARD.y0 + (row + 1) * BOARD.ch };
  }
  // Place every zero-zone special on one evenly spaced boundary rail so 24-pixel precision targets never overlap. (UX-025)
  if (bet.layout_kind === 'zero') {
    // Read the active mode's complete zero-zone catalog in its stable documented order.
    const zeroBets = catalog.filter(candidate => candidate.layout_kind === 'zero');
    // Resolve this target's unique slot on the shared boundary rail.
    const zeroIndex = zeroBets.findIndex(candidate => candidate.id === bet.id);
    // Spread the rail across the full three-column table while retaining one target radius at each edge.
    const zeroSpacing = (BOARD.cw * 3 - SPOT_SIZE) / Math.max(1, zeroBets.length - 1);
    // Return a non-overlapping point centered on the seam between the zero header and numbered grid.
    return { x: BOARD.x0 + SPOT_SIZE / 2 + Math.max(0, zeroIndex) * zeroSpacing, y: BOARD.y0 - SPOT_SIZE / 2 };
  }
  // Return the snake marker location.
  if (bet.type === 'snake') return { x: BOARD.x0 + BOARD.cw * 2.9, y: BOARD.y0 + 12 * BOARD.ch + 40 };
  // Store centers for all covered numbers.
  const centers = nums.map(cellCenter);
  // Return the average center for split, corner, and similar bets.
  return { x: centers.reduce((sum, point) => sum + point.x, 0) / centers.length, y: centers.reduce((sum, point) => sum + point.y, 0) / centers.length };
}

// Aggregate open human bets so stacked chips show one amount per table spot.
function aggregateBets() {
  // Store aggregate rows by type and covered-number set.
  const grouped = new Map();
  // Iterate through open human bets.
  for (const bet of humanBets()) {
    // Store the stable aggregate key.
    const key = `${bet.type}|${bet.covered_numbers.join('/')}`;
    // Read any existing aggregate row.
    const old = grouped.get(key) || { ...bet, amount: 0 };
    // Add this bet amount to the aggregate row.
    old.amount += Number(bet.amount || 0);
    // Store the updated aggregate row.
    grouped.set(key, old);
  }
  // Return the aggregate rows for chip rendering.
  return [...grouped.values()];
}

// Return the correct wheel number order for the selected table mode.
function wheelNums() {
  // Return the American wheel when double-zero mode is active.
  if (state.mode === 'double') return ['0', '28', '9', '26', '30', '11', '7', '20', '32', '17', '5', '22', '34', '15', '3', '24', '36', '13', '1', '00', '27', '10', '25', '29', '12', '8', '19', '31', '18', '6', '21', '33', '16', '4', '23', '35', '14', '2'];
  // Return the European wheel for single-zero mode.
  return ['0', '32', '15', '19', '4', '21', '2', '25', '17', '34', '6', '27', '13', '36', '11', '30', '8', '23', '10', '5', '24', '16', '33', '1', '20', '14', '31', '9', '22', '18', '29', '7', '28', '12', '35', '3', '26'];
}

// Export the clockwise-from-top pocket-center angle so focused tests can verify landing geometry.
export function pocketBaseAngle(index, count) {
  // Convert the pocket index to the same clockwise wedge layout the rotor renders.
  return ((index + .5) / count) * 360;
}

// Export the [0, 360) normalization used by resting wheel poses so tests share the exact fold.
export function norm360(angle) {
  // Fold negative and multi-turn values into one canonical visual orientation.
  return ((angle % 360) + 360) % 360;
}

// Export the deterministic honest-landing computation so tests can prove pocket congruence without a DOM. (ROU-053)
export function computeLandingPlan({ wheelAngle, ballAngle, pocketIndex, pocketCount, random, revealMs, elapsedMs }) {
  // Reject an off-wheel pocket so presentation can never invent a landing. (ROU-051)
  if (!Number.isInteger(pocketIndex) || pocketIndex < 0 || pocketIndex >= pocketCount) return null;
  // Choose the rotor's new rest orientation one-plus clockwise turns ahead with caller-seeded scatter.
  const wheelTarget = wheelAngle + WHEEL_EXTRA_TURNS * 360 + random() * 360;
  // Compute the orbital angle that parks the ball over the winning pocket at that rest orientation.
  const pocketAngle = pocketBaseAngle(pocketIndex, pocketCount) + wheelTarget;
  // Extend the ball's counter-clockwise travel so it reaches the pocket after extra whole circuits.
  const ballTarget = ballAngle - BALL_EXTRA_TURNS * 360 - norm360(ballAngle - pocketAngle);
  // Give the wrappers whatever part of the reveal budget the backend round-trip has not consumed.
  const travelMs = Math.max(MIN_LANDING_MS, revealMs - elapsedMs);
  // Return a frozen plan so callers and tests cannot mutate an accepted trajectory.
  return Object.freeze({ wheelTarget, ballTarget, travelMs });
}

// Render the premium vector wheel while preserving result accuracy.
function wheelSvg() {
  // Store wheel numbers for the selected table mode.
  const nums = wheelNums();
  // Store the selected result only when a real spin result exists.
  const selected = lastSpinResult || latestResultEntry()?.result || null;
  // Store the selected pocket index.
  const selectedIndex = selected ? nums.indexOf(String(selected)) : -1;
  // Derive the resting ball pose from the authoritative result whenever no spin owns the live DOM. (ROU-053, ROU-055)
  if (uiPhase !== 'spinning') {
    // Branch when a real backend result exists so the ball rides its captured pocket.
    if (selectedIndex >= 0) {
      // Align the ball's orbital angle with the winning pocket on the currently oriented rotor.
      ballOrbitAngle = norm360(pocketBaseAngle(selectedIndex, nums.length) + wheelRestAngle);
      // Seat the ball at pocket depth because a settled result is physically captured.
      ballDepth = BALL_POCKET_DEPTH;
    // Handle the no-result case without inventing a pocket. (ROU-051)
    } else {
      // Park the unassigned ball at the top of the bowl.
      ballOrbitAngle = 0;
      // Keep the unassigned ball on the outer track rather than inside any pocket.
      ballDepth = 0;
    }
  }
  // Build colored pocket wedges for the vector wheel.
  const wedges = nums.map((number, index) => `<path d="${wedgePath(index, nums.length)}" fill="${pocketFill(number)}" stroke="rgba(255,245,211,.42)" stroke-width=".9"></path>`).join('');
  // Build one polished metal fret on every pocket boundary so the ring reads as machined separators.
  const frets = nums.map((number, index) => { const angle = (index / nums.length) * Math.PI * 2 - Math.PI / 2; const inner = polar(150, 150, 84.5, angle); const outer = polar(150, 150, 121.5, angle); return `<line x1="${inner.x.toFixed(2)}" y1="${inner.y.toFixed(2)}" x2="${outer.x.toFixed(2)}" y2="${outer.y.toFixed(2)}" stroke="url(#rouletteFret)" stroke-width="1.1" opacity=".8"></line>`; }).join('');
  // Build eight static stator diamonds that deflect the ball between the track and the pocket ring.
  const diamonds = Array.from({ length: 8 }, (_, index) => { const angle = ((index + .5) / 8) * Math.PI * 2 - Math.PI / 2; const point = polar(150, 150, 128.5, angle); const spin = angle * 180 / Math.PI + 90; return `<path d="M ${point.x.toFixed(2)} ${(point.y - 3.2).toFixed(2)} L ${(point.x + 1.9).toFixed(2)} ${point.y.toFixed(2)} L ${point.x.toFixed(2)} ${(point.y + 3.2).toFixed(2)} L ${(point.x - 1.9).toFixed(2)} ${point.y.toFixed(2)} Z" fill="url(#rouletteRim)" stroke="#40230a" stroke-width=".5" transform="rotate(${spin.toFixed(2)} ${point.x.toFixed(2)} ${point.y.toFixed(2)})"></path>`; }).join('');
  // Build pocket labels and selected marker circles.
  const labels = nums.map((number, index) => { const angle = ((index + .5) / nums.length) * Math.PI  * 2 - Math.PI / 2; const point = polar(150, 150, 103, angle); const fill = String(number) === '0' || String(number) === '00' ? '#d8ffe8' : '#fff4df'; const marker = String(number) === String(selected) ? `<circle cx="${point.x}" cy="${point.y}" r="10" fill="#ffd978" opacity=".36"></circle>` : ''; return `${marker}<text x="${point.x}" y="${point.y}" text-anchor="middle" dominant-baseline="middle" font-size="11" font-weight="900" fill="${fill}" transform="rotate(${angle * 180 / Math.PI + 90} ${point.x} ${point.y})">${safe(number)}</text>`; }).join('');
  // Store the spinning class for transform-only animation.
  const spinClass = uiPhase === 'spinning' ? ' spinning' : '';
  // Store the settled or parked ball class without implying an unplayed result.
  const ballStateClass = uiPhase === 'settled' && selectedIndex >= 0 ? ' settled' : selectedIndex < 0 ? ' parked' : '';
  // Return the complete wheel SVG with a data attribute for browser assertions.
  return `<svg class="roulette-wheel" viewBox="0 0 300 300" role="img" aria-label="${text('aria.header')}" data-testid="roulette-wheel" data-selected-result="${safe(selected || 'none')}" data-reduced-motion="${prefersReducedMotion() ? 'true' : 'false'}"><defs><linearGradient id="rouletteRim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff0a9"></stop><stop offset=".2" stop-color="#b87b20"></stop><stop offset=".48" stop-color="#4d2707"></stop><stop offset=".72" stop-color="#d9a541"></stop><stop offset="1" stop-color="#5a2d08"></stop></linearGradient><linearGradient id="rouletteWood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c3f12"></stop><stop offset=".3" stop-color="#59280a"></stop><stop offset=".62" stop-color="#3a1a06"></stop><stop offset=".85" stop-color="#66300d"></stop><stop offset="1" stop-color="#2a1204"></stop></linearGradient><linearGradient id="rouletteFret" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7e3a1"></stop><stop offset=".55" stop-color="#c9973f"></stop><stop offset="1" stop-color="#8a5a16"></stop></linearGradient><linearGradient id="rouletteSheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="rgba(255,255,255,.16)"></stop><stop offset=".45" stop-color="rgba(255,255,255,.03)"></stop><stop offset="1" stop-color="rgba(255,255,255,0)"></stop></linearGradient><linearGradient id="rouletteTrail" x1="150" y1="16" x2="196" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="rgba(255,250,230,.85)"></stop><stop offset="1" stop-color="rgba(255,250,230,0)"></stop></linearGradient><radialGradient id="roulettePocketShade" cx="50%" cy="50%"><stop offset="0" stop-color="rgba(0,0,0,0)"></stop><stop offset=".6" stop-color="rgba(0,0,0,0)"></stop><stop offset=".69" stop-color="rgba(0,0,0,.42)"></stop><stop offset=".76" stop-color="rgba(0,0,0,0)"></stop><stop offset=".96" stop-color="rgba(0,0,0,0)"></stop><stop offset="1" stop-color="rgba(0,0,0,.3)"></stop></radialGradient><radialGradient id="rouletteTrackFill" cx="46%" cy="38%"><stop offset="0" stop-color="#0d2b1e"></stop><stop offset=".8" stop-color="#06130d"></stop><stop offset="1" stop-color="#03231f"></stop></radialGradient><radialGradient id="rouletteBowl" cx="42%" cy="36%"><stop offset="0" stop-color="#9b5a1c"></stop><stop offset=".48" stop-color="#4d2309"></stop><stop offset="1" stop-color="#160b05"></stop></radialGradient><radialGradient id="rouletteHub" cx="40%" cy="34%"><stop offset="0" stop-color="#fff5bd"></stop><stop offset=".26" stop-color="#dca646"></stop><stop offset=".62" stop-color="#6b350d"></stop><stop offset="1" stop-color="#241006"></stop></radialGradient><radialGradient id="rouletteBall" cx="34%" cy="28%"><stop offset="0" stop-color="#ffffff"></stop><stop offset=".54" stop-color="#f5edd7"></stop><stop offset="1" stop-color="#a89d83"></stop></radialGradient></defs><ellipse cx="150" cy="275" rx="118" ry="13" fill="rgba(0,0,0,.42)"></ellipse><circle cx="150" cy="150" r="148" fill="url(#rouletteWood)" stroke="#f4d77b" stroke-width="1.2" data-testid="roulette-wheel-rim"></circle><circle cx="150" cy="150" r="143.5" fill="none" stroke="url(#rouletteRim)" stroke-width="2.6"></circle><circle class="wheel-rim-highlight" cx="145" cy="145" r="140" fill="none" stroke="rgba(255,239,179,.52)" stroke-width="3"></circle><circle cx="150" cy="150" r="138" fill="#2c1307" stroke="#6f3a0d" stroke-width="3"></circle><circle cx="150" cy="150" r="134" fill="url(#rouletteTrackFill)" stroke="#e0b85a" stroke-width="2" data-testid="roulette-ball-track"></circle><circle cx="150" cy="150" r="125" fill="#0a2e20" stroke="rgba(255,244,207,.5)" stroke-width="1.5"></circle>${diamonds}<g class="wheel-orient" data-testid="roulette-wheel-orient" style="transform:rotate(${wheelRestAngle}deg)"><g class="wheel-ring${spinClass}" data-testid="roulette-rotor" data-motion-direction="clockwise">${wedges}<circle cx="150" cy="150" r="122" fill="url(#roulettePocketShade)" pointer-events="none"></circle>${frets}${labels}<circle cx="150" cy="150" r="82" fill="url(#rouletteBowl)" stroke="#d5a648" stroke-width="2"></circle><circle cx="150" cy="150" r="74" fill="none" stroke="rgba(255,231,159,.28)" stroke-width="1"></circle><circle cx="150" cy="150" r="62" fill="#2a1107" stroke="rgba(255,231,159,.46)" stroke-width="1.5"></circle><path d="M150 94 L158 134 L206 150 L158 158 L150 206 L142 158 L94 150 L142 142 Z" fill="url(#rouletteRim)" opacity=".84"></path></g></g><circle cx="150" cy="150" r="40" fill="url(#rouletteHub)" stroke="#f2d77d" stroke-width="2"></circle><g fill="url(#rouletteRim)" stroke="#5a2b08" stroke-width=".7"><circle cx="129" cy="129" r="4.2"></circle><circle cx="171" cy="129" r="4.2"></circle><circle cx="129" cy="171" r="4.2"></circle><circle cx="171" cy="171" r="4.2"></circle></g><circle cx="150" cy="150" r="19" fill="url(#rouletteRim)" stroke="#fff0aa" stroke-width="1.5"></circle><path d="M150 119 L158 145 L150 151 L142 145 Z" fill="#f6d985" stroke="#6e350c" stroke-width="1"></path><circle cx="150" cy="128" r="5" fill="#fff0ad"></circle><ellipse cx="112" cy="96" rx="96" ry="58" fill="url(#rouletteSheen)" transform="rotate(-28 112 96)" pointer-events="none"></ellipse><path d="M142 7 L158 7 L150 22 Z" fill="#f1ca62" stroke="#5a2b08" stroke-width="1.2"></path><g class="ball-orbit" data-testid="roulette-ball-orbit" style="transform:rotate(${ballOrbitAngle}deg)"><g class="ball-radial" data-testid="roulette-ball-radial" style="transform:translateY(${ballDepth}px)"><g class="ball-dot${spinClass}${ballStateClass}" data-testid="roulette-ball" data-motion-direction="counterclockwise"><path class="ball-trail" d="M 150 16 A 134 134 0 0 1 195.8 24" fill="none" stroke="url(#rouletteTrail)" stroke-width="5" stroke-linecap="round"></path><circle cx="152" cy="19" r="7.5" fill="rgba(0,0,0,.42)"></circle><circle class="wheel-ball" cx="150" cy="16" r="7" fill="url(#rouletteBall)" stroke="#fff9e9" stroke-width="1.2"></circle><circle cx="148" cy="14" r="1.8" fill="#ffffff"></circle></g></g></g></svg>`;
}

// Render one absolute-positioned number cell.
function numberCellHtml(number, x, y, width, height) {
  // Store result marker state for real settled results only.
  const isResult = uiPhase === 'settled' && String(number) === String(lastSpinResult);
  // Store the premium result class when this cell matches the actual result.
  const resultClass = isResult ? ' result-cell' : '';
  // Store a compact result marker for the winning number.
  const marker = isResult ? `<i class="roulette-result-marker">${text('table.winMarker')}</i>` : '';
  // Return the absolute table cell with its existing test id plus stable hit-target identity attributes. (issue #222)
  return `<div class="table-cell ${numberColorClass(number)}${resultClass}" style="left:${x}px;top:${y}px;width:${width}px;height:${height}px"><button type="button" data-testid="roulette-num-${safe(number)}" data-num="${safe(number)}" ${cellAttrs(`num:${number}`, 'straight', [number])}${disabledWhenSpinning()}>${safe(number)}${marker}</button></div>`;
}

// Render the fixed Roulette betting table with inside spots and chips.
function tableHtml() {
  // Store rendered cell markup.
  const cells = [];
  // Branch for the double-zero header layout.
  if (state.mode === 'double') {
    // Add the 0 cell.
    cells.push(numberCellHtml('0', BOARD.x0, BOARD.y0 - 62, BOARD.cw * 1.5, 45));
    // Add the 00 cell.
    cells.push(numberCellHtml('00', BOARD.x0 + BOARD.cw * 1.5, BOARD.y0 - 62, BOARD.cw * 1.5, 45));
  // Render the single-zero header layout.
  } else {
    // Add the single 0 cell.
    cells.push(numberCellHtml('0', BOARD.x0, BOARD.y0 - 62, BOARD.cw * 3, 45));
  }
  // Iterate through the fixed number grid.
  for (let row = 0; row < 12; row += 1) {
    // Iterate through the three fixed number columns.
    for (let col = 0; col < 3; col += 1) {
      // Store the table number at this coordinate.
      const number = row * 3 + col + 1;
      // Add the number cell to the board.
      cells.push(numberCellHtml(number, BOARD.x0 + col * BOARD.cw, BOARD.y0 + row * BOARD.ch, BOARD.cw, BOARD.ch));
    }
  }
  // Store even-money outside cells with localized labels.
  const outside = [['low', text('bets.low'), 30, 180, 115, 42], ['even', text('bets.even'), 30, 228, 115, 42], ['red', text('bets.red'), 30, 276, 115, 42], ['black', text('bets.black'), 30, 324, 115, 42], ['odd', text('bets.odd'), 30, 372, 115, 42], ['high', text('bets.high'), 30, 420, 115, 42]];
  // Add each outside cell to the board.
  outside.forEach(([type, label, x, y, width, height]) => { const isResult = uiPhase === 'settled' && type === lastSpinColor; const resultClass = isResult ? ' result-cell' : ''; cells.push(`<div class="outside-cell${resultClass}" style="left:${x}px;top:${y}px;width:${width}px;height:${height}px"><button type="button" data-outside="${type}" data-testid="roulette-outside-${type}" ${cellAttrs(`outside:${type}`, type, (outsideIdentity(type) || {}).covered)}${disabledWhenSpinning()}>${label}</button></div>`); });
  // Add dozen cells below the inside grid.
  ['1st 12', '2nd 12', '3rd 12'].forEach((label, index) => cells.push(`<div class="outside-cell" style="left:${BOARD.x0 + index * BOARD.cw}px;top:${BOARD.y0 + 12 * BOARD.ch + 8}px;width:${BOARD.cw}px;height:36px"><button type="button" data-dozen="${safe(label)}" data-testid="roulette-dozen-${index + 1}" ${cellAttrs(`dozen:${index + 1}`, 'dozen', (expectedIdentity(`dozen:${index + 1}`) || {}).covered)}${disabledWhenSpinning()}>${text(`bets.dozen${index + 1}`)}</button></div>`));
  // Add column cells below the dozen row.
  ['Column 1', 'Column 2', 'Column 3'].forEach((label, index) => cells.push(`<div class="outside-cell" style="left:${BOARD.x0 + index * BOARD.cw}px;top:${BOARD.y0 + 12 * BOARD.ch + 50}px;width:${BOARD.cw}px;height:36px"><button type="button" data-column="${safe(label)}" data-testid="roulette-column-${index + 1}" ${cellAttrs(`column:${index + 1}`, 'column', (expectedIdentity(`column:${index + 1}`) || {}).covered)}${disabledWhenSpinning()}>${text('bets.column')}</button></div>`));
  // Build inside-bet hotspots from the catalog.
  const hotspots = catalog.filter(bet => bet.layout_kind !== 'outside' && bet.type !== 'straight').map(bet => { const point = posForBet(bet); return `<button type="button" class="spot" style="left:${point.x - SPOT_SIZE / 2}px;top:${point.y - SPOT_SIZE / 2}px" title="${safe(bet.label)} ${safe(bet.net_payout)}:1" aria-label="${safe(bet.label)}" data-betid="${safe(bet.id)}" data-testid="roulette-spot-${safe(bet.id)}" ${cellAttrs(`spot:${bet.id}`, bet.type, bet.covered_numbers)}${disabledWhenSpinning()}></button>`; }).join('');
  // Build visible table chips from aggregate human bets.
  const chips = aggregateBets().map(bet => { const point = posForBet(bet); return `<div class="bet-chip" style="left:${point.x - 19}px;top:${point.y - 19}px" title="${safe(bet.label)}">${chipMoney(bet.amount)}</div>`; }).join('');
  // Store dimmed state for spin/reveal.
  const dimmed = uiPhase === 'spinning' ? ' roulette-board-dimmed' : '';
  // Return the full fixed board.
  return `<div class="roulette-table-board${showSpots ? '' : ' hide-spots'}${dimmed}" data-testid="roulette-table">${cells.join('')}${hotspots}${chips}</div>`;
}

// Return the localized label for a backend settlement outcome.
function outcomeLabel(outcome) {
  // Store the resource key for the backend outcome.
  const key = `outcomes.${String(outcome || 'none')}`;
  // Resolve the localized outcome label.
  const label = rt(key);
  // Return the backend value when a specific resource key is not defined.
  return label === key ? String(outcome || '') : label;
}

// Return a localized display label for backend result colors.
function colorLabel(color) {
  // Store the resource key for the backend color value.
  const key = `colors.${String(color || 'none')}`;
  // Resolve the localized color label.
  const label = rt(key);
  // Return the backend value when a specific resource key is not defined.
  return label === key ? String(color || '') : label;
}

// Render the result panel under the wheel.
function resultHtml() {
  // Branch while the animation is intentionally hiding the result.
  if (uiPhase === 'spinning') return `<div id="result" class="fixed-result" data-game-live-status data-testid="roulette-result-region" data-phase="spinning"><span class="roulette-spin-orbit" aria-hidden="true"></span><span class="roulette-result-copy"><b>${text('stage.spinning')}</b><span>${text('result.spinning')}</span></span></div>`;
  // Branch for a settled spin with an actual backend result.
  if (uiPhase === 'settled' && lastSpinResult !== null) {
    // Store the integrated net summary without repeating every settlement log row.
    const settlementSummary = lastSettlements.length ? `${text('settlement.humanNet')}: ${signedTokenMoney(lastHumanNet)}` : text('result.noHumanBets');
    // Return the settled result console with the authoritative pocket as the visual focus.
    return `<div id="result" class="fixed-result win" data-game-live-status data-testid="roulette-result-region" data-phase="settled" data-result-number="${safe(lastSpinResult)}"><span class="roulette-result-pocket ${numberColorClass(lastSpinResult)}">${safe(lastSpinResult)}</span><span class="roulette-result-copy"><b>${text('result.rolled', { number: lastSpinResult })}</b><span>${safe(colorLabel(lastSpinColor))} · ${settlementSummary}</span></span></div>`;
  }
  // Branch for a loaded state with a real previous result.
  if (lastSpinResult !== null) return `<div id="result" class="fixed-result" data-game-live-status data-testid="roulette-result-region" data-phase="betting" data-result-number="${safe(lastSpinResult)}"><span class="roulette-result-pocket ${numberColorClass(lastSpinResult)}">${safe(lastSpinResult)}</span><span class="roulette-result-copy"><b>${text('result.lastResult', { number: lastSpinResult })}</b><span>${text('stage.placeBets')}</span></span></div>`;
  // Return the no-spin state without any fake result.
  return `<div id="result" class="fixed-result" data-game-live-status data-testid="roulette-result-region" data-phase="betting" data-result-number="none"><span class="roulette-result-pocket">—</span><span class="roulette-result-copy"><b>${text('stage.placeBets')}</b><span>${text('result.noSpinYet')}</span></span></div>`;
}

// Render the premium route header without exposing internal lifecycle diagnostics.
function headerHtml() {
  // Return only player-facing table identity while stage and result regions own phase state.
  return `<section class="roulette-header" aria-label="${text('aria.header')}"><div><p class="roulette-kicker">${text('header.kicker')}</p><h1>${text('title')}</h1></div></section>`;
}

// Render the control rail with settings, chips, fast bets, autoplay, and bots.
function controlRailHtml() {
  // Store the template availability state for the rebet button.
  const canRebet = (state.last_bet_template || []).length > 0 && !spinBusy;
  // Store the spot toggle label.
  const spotLabel = showSpots ? text('controls.hideSpots') : text('controls.showSpots');
  // Store the localized shared autoplay heading for its disclosure control.
  const autoplayLabel = sharedText('title', AUTOPLAY_DOMAIN);
  // Store the localized shared bot-controller heading for its disclosure control.
  const botsLabel = sharedText('title', BOTS_DOMAIN);
  // Return the complete left rail.
  return `<section class="panel control-rail" data-testid="roulette-control-rail" tabindex="0" role="region" aria-label="${text('controls.title')}"><h2 class="game-title">${text('controls.title')}</h2><div class="roulette-control-section"><h3>${text('controls.chipStack')}</h3><div class="chip-row">${CHIP_VALUES.map(value => `<button type="button" class="chip ${value === chip ? 'active' : ''}" data-chip="${value}" data-testid="chip-${value}"${disabledWhenSpinning()}>${chipMoney(value)}</button>`).join('')}</div></div><div class="roulette-control-section"><h3>${text('controls.fastBets')}</h3><div class="roulette-fast-grid">${['red', 'black', 'odd', 'even', 'low', 'high'].map(type => `<button type="button" data-outbtn="${type}" ${cellAttrs(`outside:${type}`, type, (outsideIdentity(type) || {}).covered)}${disabledWhenSpinning()}>${text(`bets.${type}`)}</button>`).join('')}</div></div><div class="roulette-secondary-actions roulette-control-section"><button type="button" id="toggleSpots" aria-pressed="${showSpots ? 'true' : 'false'}"${disabledWhenSpinning()}>${spotLabel}</button><button type="button" id="rebet"${canRebet ? '' : ' disabled'}>${text('controls.rebet')}</button></div><details class="roulette-advanced" data-testid="roulette-rules-disclosure" data-roulette-disclosure="rules"${disclosureOpen('rules')}><summary>${text('controls.wheel')} · ${text('controls.zeroRule')}</summary><div class="roulette-advanced-body"><div class="roulette-settings"><label>${text('controls.wheel')}<select id="mode" data-testid="roulette-mode"${disabledWhenSpinning()}><option value="single">${text('settings.wheel.single')}</option><option value="double">${text('settings.wheel.double')}</option></select></label><label>${text('controls.zeroRule')}<select id="zero" data-testid="roulette-zero"${disabledWhenSpinning()}><option value="normal">${text('settings.zeroRule.normal')}</option><option value="la_partage">${text('settings.zeroRule.laPartage')}</option><option value="en_prison">${text('settings.zeroRule.enPrison')}</option></select></label></div></div></details><details class="roulette-advanced" data-testid="roulette-racetrack-disclosure" data-roulette-disclosure="racetrack"${disclosureOpen('racetrack')}><summary>${text('controls.racetrack')}</summary><div class="roulette-advanced-body"><div class="roulette-call-grid">${['snake', 'voisins', 'tiers', 'orphelins', 'jeu_zero', 'neighbors', 'final', 'complete'].map(type => `<button type="button" data-call="${type}"${disabledWhenSpinning()}>${text(`callBets.${type}`)}</button>`).join('')}</div><label class="roulette-call-number">${text('controls.callNumber')}<input id="callNumber" class="roulette-call-input" type="text" value="17"${disabledWhenSpinning()}></label></div></details><details class="roulette-advanced" data-testid="roulette-autoplay-disclosure" data-roulette-disclosure="autoplay"${disclosureOpen('autoplay')}><summary>${autoplayLabel}</summary><div id="auto" class="roulette-advanced-body"></div></details><details class="roulette-advanced" data-testid="roulette-bots-disclosure" data-roulette-disclosure="bots"${disclosureOpen('bots')}><summary>${botsLabel}</summary><div id="botPanel" class="roulette-advanced-body">${botPanelCache}</div></details></section>`;
}

// Render the central wheel and table stage.
function stageHtml() {
  // Store the current phase title.
  const phaseTitle = uiPhase === 'spinning' ? text('stage.spinning') : uiPhase === 'settled' ? text('stage.settled') : text('stage.placeBets');
  // Store the primary button label.
  const primaryLabel = spinBusy ? text('controls.resolving') : text('controls.spin');
  // Store the wheel panel state class.
  const wheelState = uiPhase === 'spinning' ? ' reveal-glow' : uiPhase === 'settled' ? ' result-glow' : '';
  // Store the clear disabled state.
  const clearDisabled = humanBets().length === 0 || spinBusy ? ' disabled' : '';
  // Return the complete central game stage.
  return `<section class="panel game-stage" data-testid="roulette-premium-stage"><div class="roulette-stage-toolbar"><div><p class="eyebrow">${text('header.kicker')}</p><h2>${phaseTitle}</h2></div><div class="row"><button type="button" id="clear"${clearDisabled}>${text('controls.clearBets')}</button><button type="button" id="spin" data-testid="roulette-spin" class="primary"${disabledWhenSpinning()}>${primaryLabel}</button></div></div><div class="roulette-stage"><div class="wheel-card${wheelState}"><div class="roulette-wheel-frame" data-testid="roulette-wheel-frame">${wheelSvg()}</div>${resultHtml()}</div><div class="roulette-table-shell">${tableHtml()}</div></div></section>`;
}

// Render the player balance table for the right drawer.
function scoreboardHtml() {
  // Store player rows from the latest state payload.
  const players = window._lastPlayers || [];
  // Return a compact scoreboard table.
  return `<table class="mini-table" data-testid="roulette-scoreboard"><tr><th>${text('scoreboard.player')}</th><th>${text('scoreboard.balance')}</th></tr>${players.map(player => `<tr><td>${safe(player.display_name)}</td><td>${tokenMoney(player.balance)}</td></tr>`).join('')}</table>`;
}

// Render stat spark bars from live stats data.
function sparkBarsHtml(stats) {
  // Store frequency values from the stats payload.
  const values = Object.values(stats.frequency || {}).map(value => Number(value || 0)).slice(0, 8);
  // Store a fallback sequence when no stats exist yet.
  const bars = values.length ? values : [1, 2, 1, 2, 1, 3, 2, 1];
  // Store the max value so heights can scale safely.
  const max = Math.max(1, ...bars);
  // Return the spark bar row.
  return `<div class="roulette-spark-bars" data-testid="roulette-stats-spark">${bars.map(value => `<i style="height:${Math.max(14, Math.round((value / max) * 54))}px"></i>`).join('')}</div>`;
}

// Render latest-result history pills from stats or state.
function historyPillsHtml(stats) {
  // Store recent results from stats first and backend state as a fallback.
  const latest = (stats.latest || state.last_results || []).slice(-12);
  // Return the latest-result pill row.
  return `<div class="roulette-history-pills" data-testid="roulette-recent-results">${latest.map(entry => { const result = entry.result ?? entry; const resultClass = uiPhase === 'settled' && String(result) === String(lastSpinResult) ? ' result-cell' : ''; return `<span class="${numberColorClass(result)}${resultClass}">${safe(result)}</span>`; }).join('')}</div>`;
}

// Render the settlement or pending drawer card.
function settlementCardHtml() {
  // Branch while a spin is waiting for the pocket reveal.
  if (uiPhase === 'spinning') return `<div class="roulette-settlement-card" data-testid="roulette-settlement-card"><b>${text('settlement.waiting')}</b><span>${text('status.spinning')}</span></div>`;
  // Branch after a settled spin.
  if (uiPhase === 'settled') return `<div class="roulette-settlement-card" data-testid="roulette-settlement-card"><b>${text('settlement.humanNet')}</b><span>${signedTokenMoney(lastHumanNet)}</span></div>`;
  // Return an empty string when the bet slip owns the drawer.
  return '';
}

// Render the right drawer with bet slip, settlement, scoreboard, and stats.
function drawerHtml() {
  // Store human open bets for slip rendering.
  const bets = humanBets();
  // Store the open total for the drawer metric.
  const total = humanBetTotal(bets);
  // Store whether settlement mode owns the drawer heading.
  const settlementMode = uiPhase === 'settled';
  // Store the drawer title.
  const title = settlementMode ? text('settlement.title') : text('betSlip.title');
  // Store the phase badge.
  const badge = uiPhase === 'spinning' ? text('phase.spinning') : uiPhase === 'settled' ? text('phase.settled') : text('phase.betting');
  // Store the slip rows for open bets or settlement rows for settled results.
  const rows = settlementMode ? lastSettlements.map(row => `<div class="bet-item"><span>${safe(row.label)}</span><b>${safe(outcomeLabel(row.outcome))}</b></div>`).join('') : bets.map(bet => `<div class="bet-item"><span>${safe(bet.label)}</span><b class="money">${tokenMoney(bet.amount)}</b><button type="button" class="danger" data-clear="${safe(bet.bet_id)}"${(spinBusy || uiPhase !== 'betting') ? ' disabled' : ''}>${text('controls.remove')}</button></div>`).join('');
  // Store the metric label.
  const metricLabel = uiPhase === 'spinning' ? text('betSlip.lockedTotal') : settlementMode ? text('settlement.humanNet') : text('betSlip.openTotal');
  // Store the metric value.
  const metricValue = settlementMode ? signedTokenMoney(lastHumanNet) : tokenMoney(total);
  // Return the complete right drawer.
  return `<section class="panel details-drawer" data-testid="roulette-bet-slip"><div class="roulette-drawer-title"><h3>${title}</h3><span class="roulette-phase-badge">${badge}</span></div><div class="stat"><span>${metricLabel}</span> <b class="money">${metricValue}</b></div><div class="bet-list stable-list">${rows || `<p class="muted">${text('betSlip.empty')}</p>`}</div>${settlementCardHtml()}<h3>${text('scoreboard.title')}</h3>${scoreboardHtml()}<h3>${text('stats.title')}</h3><div class="row"><span class="badge">${text('stats.rolls', { count: statsCount(lastStats.roll_count) })}</span><span class="badge">${text('stats.red', { count: statsCount(lastStats.colors?.red) })}</span><span class="badge">${text('stats.black', { count: statsCount(lastStats.colors?.black) })}</span><span class="badge">${text('stats.green', { count: statsCount(lastStats.colors?.green) })}</span></div>${sparkBarsHtml(lastStats)}${historyPillsHtml(lastStats)}<h4>${text('stats.hot')}</h4><div class="stat-bars">${(lastStats.hot || []).map(([number, count]) => `<div class="stat-bar"><b>${safe(number)}</b><div class="stat-fill" style="width:${Math.max(5, count / Math.max(1, ...Object.values(lastStats.frequency || {})) * 100)}%"></div><span>${safe(count)}</span></div>`).join('')}</div><h4>${text('stats.cold')}</h4><div class="row">${(lastStats.cold || []).map(([number, count]) => `<span class="badge">${safe(number)}: ${safe(count)}</span>`).join('')}</div></section>`;
}

// Return a stable stat count string for localized stat badges.
function statsCount(value) {
  // Return a numeric count with a zero fallback.
  return String(Number(value || 0));
}

// Wire all event handlers after a full rerender.
function wireControls() {
  // Set the mode select to the current backend state value.
  root.querySelector('#mode').value = state.mode;
  // Set the zero-rule select to the current backend state value.
  root.querySelector('#zero').value = state.zero_rule;
  // Wire mode changes to the existing settings endpoint.
  root.querySelector('#mode').onchange = guarded(settings);
  // Wire zero-rule changes to the existing settings endpoint.
  root.querySelector('#zero').onchange = guarded(settings);
  // Wire chip buttons while preserving selected chip state.
  root.querySelectorAll('[data-chip]').forEach(button => { button.onclick = () => { chip = Number(button.dataset.chip); render(); updateBotPanel(); }; });
  // Wire every bet cell through its stable identity so clicks resolve and verify by canonical covered numbers, not fragile labels. (issue #222)
  root.querySelectorAll('[data-cell-key]').forEach(button => { button.onclick = guarded(() => placeBetForCell(button)); });
  // Wire racetrack and call-bet controls to the call-bet endpoint.
  root.querySelectorAll('[data-call]').forEach(button => { button.onclick = guarded(() => placeCall(button.dataset.call)); });
  // Wire individual bet removal buttons to the clear endpoint.
  root.querySelectorAll('[data-clear]').forEach(button => { button.onclick = guarded(() => clearBet(button.dataset.clear)); });
  // Wire clear-all to the clear endpoint.
  root.querySelector('#clear').onclick = guarded(clearAll);
  // Wire rebet to the rebet endpoint.
  root.querySelector('#rebet').onclick = guarded(rebet);
  // Wire spin to the spin endpoint.
  root.querySelector('#spin').onclick = guarded(() => spin(true));
  // Wire spot visibility without touching game state.
  root.querySelector('#toggleSpots').onclick = () => { showSpots = !showSpots; render(); updateBotPanel(); };
  // Preserve player-opened optional control groups across phase and locale rerenders.
  root.querySelectorAll('[data-roulette-disclosure]').forEach(details => { details.ontoggle = () => { if (details.open) openDisclosures.add(details.dataset.rouletteDisclosure); else openDisclosures.delete(details.dataset.rouletteDisclosure); }; });
  // Render shared autoplay controls through the shared control-plane helper.
  autoBox = renderAutoplay({ id: 'roulette', plan: { type: 'repeat_bet_template' }, onTick: async () => { await ensureBetForAuto(); await spin(false); } });
  // Append autoplay controls into the reserved rail slot.
  root.querySelector('#auto').append(autoBox);
}

// Render the full premium Roulette route without reloading state.
// Store the native design size of the fixed hit-map board that every scale computation starts from. (UX-026)
const TABLE_BOARD_NATIVE_WIDTH = 760;
// Store the native design height matching the absolute cell geometry inside the board. (UX-026)
const TABLE_BOARD_NATIVE_HEIGHT = 590;
// Store the debounce timer for viewport-driven refits so resize storms apply one final measurement.
let boardFitTimer = null;
// Store the bound resize listener so unmount can remove exactly the handler mount added.
let boardFitListener = null;
// Fit the fixed-geometry betting board to its shell continuously so no viewport can clip it. (UX-026)
function fitTableBoard() {
  // Stop when the route is unmounted or the premium table is not on this render.
  const shell = root?.querySelector('.roulette-table-shell');
  // Read the fixed-size board inside the measured shell.
  const board = shell?.querySelector('.roulette-table-board');
  // Stop safely when either element is absent, for example before the first table render.
  if (!shell || !board) return;
  // Measure the shell box that must fully contain the scaled board.
  const availableWidth = shell.clientWidth - 2;
  // Measure the vertical budget the responsive layout granted the shell.
  const availableHeight = shell.clientHeight - 2;
  // Compute one continuous scale bounded by both axes instead of discrete breakpoint guesses.
  const scale = Math.max(0.1, Math.min(1, availableWidth / TABLE_BOARD_NATIVE_WIDTH, availableHeight / TABLE_BOARD_NATIVE_HEIGHT));
  // Compute the explicit centering offset because grid safe-centering start-pins any oversized item box.
  const offsetX = Math.max(0, (shell.clientWidth - TABLE_BOARD_NATIVE_WIDTH * scale) / 2);
  // Anchor the transform to the start-pinned box corner so translate and scale compose deterministically.
  board.style.transformOrigin = 'top left';
  // Apply the measured centering translate and scale so the complete board always renders inside the shell.
  board.style.transform = `translateX(${offsetX.toFixed(2)}px) scale(${scale.toFixed(4)})`;
}
// Schedule one debounced refit after viewport changes settle. (UX-026)
function scheduleBoardFit() {
  // Replace any pending refit so only the final size is measured.
  clearTimeout(boardFitTimer);
  // Delay slightly so responsive grid tracks finish before the measurement.
  boardFitTimer = setTimeout(fitTableBoard, 120);
}
function render() {
  // Stop when the module has not mounted yet.
  if (!root || !state) return;
  // Preserve the focused roulette control through the full-root render. (UX-025)
  const focus = captureGameFocus(root);
  // Replace the route body while preserving JS state caches.
  root.innerHTML = `<section class="roulette-premium" data-testid="roulette-premium">${headerHtml()}<div class="game-layout three-col stable-game" data-testid="roulette-premium-layout">${controlRailHtml()}${stageHtml()}${drawerHtml()}</div></section>`;
  // Wire controls after the DOM has been replaced.
  wireControls();
  // Fit the freshly rendered fixed board into the current shell before the frame paints. (UX-026)
  fitTableBoard();
  // Restore focus and publish the result through document-lifetime accessibility surfaces. (UX-025)
  restoreGameFocus(root, focus); syncGameLiveStatus(root);
}

// Export this symbol so the app shell can mount the Roulette game route.
export const RouletteGame = {
  // Store the game id used by the shell route registry.
  id: 'roulette',
  // Store the visible label used by route metadata.
  label: 'Roulette',
  // Mount Roulette into the shared #view route outlet.
  async mount(node) {
    // Store the route root for future renders.
    root = node;
    // Advance route identity so callbacks from any older mount remain permanently stale.
    mountGeneration += 1;
    // Install Roulette-only premium styles.
    ensurePremiumStyle();
    // Initialize the Roulette resource domain before rendering visible strings.
    await initI18n({ domains: [GAME_DOMAIN, AUTOPLAY_DOMAIN, BOTS_DOMAIN] });
    // Create the route-owned timer scope so every spin timer cancels on navigation or reload. (MOTION-002)
    motionScope = createMotionTimerScope();
    // Reset presentation guards in case a prior mount was torn down mid-spin.
    spinBusy = false;
    // Return the phase to betting because no spin can be live on a fresh mount.
    uiPhase = 'betting';
    // Clear any stale deferred locale repaint from a prior mount.
    pendingLocaleRender = false;
    // Clear any stale terminal guard because a new mount owns future spins.
    activeSpinCompletion = null;
    // Subscribe to locale changes while deferring repaints that would destroy a live spin animation.
    localeUnsubscribe = onLocaleChange(() => { if (spinBusy) { pendingLocaleRender = true; return; } render(); });
    // Refit the fixed board whenever the viewport changes while this route owns the outlet. (UX-026)
    boardFitListener = scheduleBoardFit;
    // Attach the route-owned resize listener that unmount removes symmetrically.
    window.addEventListener('resize', boardFitListener);
    // Load backend state and render the premium Roulette surface.
    await load();
  },
  // Unmount Roulette and clean up local loops/listeners.
  unmount() {
    // Stop autoplay when the route is leaving.
    if (autoBox?._stop) autoBox._stop();
    // Remove the locale listener when mounted.
    if (localeUnsubscribe) localeUnsubscribe();
    // Clear the locale unsubscribe handle.
    localeUnsubscribe = null;
    // Capture whether a spin was resolving so the refund guard below keeps its issue-246 meaning.
    const wasSpinning = spinBusy;
    // Abort the active spin exactly once before invalidating its route identity. (ROU-072)
    if (activeSpinCompletion) activeSpinCompletion.abort();
    // Release the active completion handle so a remount cannot inherit it.
    activeSpinCompletion = null;
    // Advance route identity before releasing any awaiting continuation.
    mountGeneration += 1;
    // Cancel every pending spin timer owned by this route before the view disappears. (MOTION-002)
    if (motionScope) motionScope.dispose();
    // Resolve canceled timer promises so guarded async functions can finish as aborted.
    releaseMotionWaiters();
    // Clear the disposed scope handle so a later mount builds a fresh one.
    motionScope = null;
    // Release the spin guard because a cancelled reveal can never finish its finally block.
    spinBusy = false;
    // Normalize the phase so a remount never resumes a phantom spin presentation.
    if (uiPhase === 'spinning') uiPhase = 'betting';
    // Remove the route-owned refit listener so navigation cannot leak viewport handlers. (UX-026)
    if (boardFitListener) { window.removeEventListener('resize', boardFitListener); boardFitListener = null; }
    // Cancel any pending debounced refit because the board is leaving the document.
    clearTimeout(boardFitTimer);
    // Refund any open, un-spun bets so leaving the table never strands already-debited stakes. (issue #246)
    if (humanBets().length && !wasSpinning) {
      // Fire the documented clear/refund endpoint best-effort; the route is leaving, so do not await or rerender, and refresh only the shared wallet.
      post('/api/v1/games/roulette/clear', withCurrentPlayer()).then(() => refreshBalance()).catch(() => {});
    }
    // Clear the route root to prevent async rerenders after unmount.
    root = null;
  },
};
