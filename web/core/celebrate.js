// Shell-level win feedback: animate the wallet on every balance change so token gains feel rewarding
// across all 46 games from one place. Fully non-invasive — it only observes the #balance element.

// Match the shell's two-decimal, grouped token formatting so animated frames read like the settled value.
const formatTokens = n => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// Parse a rendered token string ("12,500.00") back to a number, tolerating grouping separators.
const parseTokens = text => Number(String(text == null ? '' : text).replace(/[^0-9.-]/g, ''));
// Respect the user's reduced-motion preference for every celebratory animation.
const reduceMotion = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Track the last settled balance and an internal write flag so our own tween writes never re-trigger.
let lastBalance = null;
// Guard the observer against reacting to the frames we write during a count-up.
let animating = false;

// Tween the wallet number from one value to the next with an ease-out curve.
function animateCount(el, from, to) {
  // Skip the tween entirely under reduced motion; land on the exact settled value.
  if (reduceMotion() || !Number.isFinite(from)) { el.textContent = formatTokens(to); return; }
  // Scale the duration to the jump size but keep it snappy and bounded.
  const duration = Math.min(900, 380 + Math.abs(to - from) * 0.02);
  // Record the animation start time from the frame clock.
  let start = null;
  // Mark that subsequent textContent writes originate from this tween.
  animating = true;
  // Advance one frame of the eased count.
  const step = now => {
    // Seed the start timestamp on the first frame.
    if (start === null) start = now;
    // Compute normalized progress clamped to the unit interval.
    const p = Math.min(1, (now - start) / duration);
    // Apply a cubic ease-out so the number decelerates into place.
    const eased = 1 - Math.pow(1 - p, 3);
    // Write the interpolated value for this frame.
    el.textContent = formatTokens(from + (to - from) * eased);
    // Continue until the tween completes.
    if (p < 1) { requestAnimationFrame(step); return; }
    // Land exactly on the settled value to avoid rounding drift.
    el.textContent = formatTokens(to);
    // Release the write guard one frame later so the final write is not re-observed.
    requestAnimationFrame(() => { animating = false; });
  };
  // Kick off the frame loop.
  requestAnimationFrame(step);
}

// Flash a brand glow on the wallet and float the gained amount above it.
function celebrateGain(pill, gain) {
  // Choose a stronger treatment for a large jump so big wins feel bigger.
  const big = gain >= 250;
  // Toggle the pulse class, restarting the CSS animation cleanly if one is mid-flight.
  pill.classList.remove('wallet-win', 'wallet-bigwin');
  // Force a reflow so re-adding the class replays the keyframes.
  void pill.offsetWidth;
  // Apply the magnitude-appropriate pulse class.
  pill.classList.add(big ? 'wallet-bigwin' : 'wallet-win');
  // Remove the pulse class once its animation window elapses.
  setTimeout(() => pill.classList.remove('wallet-win', 'wallet-bigwin'), 1100);
  // Skip the floating chip under reduced motion to honour the preference.
  if (reduceMotion()) return;
  // Build the transient "+amount" indicator that rises and fades.
  const chip = document.createElement('span');
  // Style hook for the floating gain chip.
  chip.className = 'wallet-gain';
  // Announce the positive delta with the shared token format and a leading plus.
  chip.textContent = '+' + formatTokens(gain);
  // Attach the chip to the wallet so it is positioned relative to the pill.
  pill.appendChild(chip);
  // Remove the chip after its rise-and-fade animation completes.
  setTimeout(() => chip.remove(), 1200);
}

// Begin observing the shell wallet so any balance change animates and any gain celebrates.
export function initWalletCelebration() {
  // Locate the live wallet amount node rendered by the authenticated shell.
  const el = document.getElementById('balance');
  // Do nothing when the wallet is absent (e.g. the logged-out gate).
  if (!el) return;
  // Resolve the wallet pill that carries the glow and hosts the floating chip.
  const pill = el.closest('.wallet-pill') || el.parentElement;
  // Seed the baseline from whatever the shell has already rendered.
  lastBalance = parseTokens(el.textContent);
  // Watch the amount node for any text mutation the shell performs.
  const observer = new MutationObserver(() => {
    // Ignore the frames our own count-up writes produce.
    if (animating) return;
    // Read the freshly rendered target balance.
    const target = parseTokens(el.textContent);
    // Ignore non-numeric placeholder states such as "Loading...".
    if (!Number.isFinite(target)) return;
    // Capture the prior value and adopt the new one as the baseline.
    const from = lastBalance;
    // Store the settled target before any tween writes occur.
    lastBalance = target;
    // Nothing to do when the value is unchanged.
    if (from === target) return;
    // Animate the number from the prior value to the settled value.
    animateCount(el, from, target);
    // Celebrate only a genuine increase, and only when we had a real prior value.
    if (pill && Number.isFinite(from) && target > from) celebrateGain(pill, target - from);
  });
  // Observe text changes on the amount node and its text descendants.
  observer.observe(el, { childList: true, characterData: true, subtree: true });
}
