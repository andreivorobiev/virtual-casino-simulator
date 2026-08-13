// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Provide one shell-owned wallet celebration controller with no game, API, or wallet authority. (UX-023)

// Bound the stronger celebration to reviewed fake-token gains of at least this amount.
const BIG_GAIN_THRESHOLD = 250;
// Bound the decorative coin layer so one update cannot grow the document without limit.
const MAX_COIN_COUNT = 12;
// Bound every normal-motion effect before lifecycle cleanup removes all transient state.
const CELEBRATION_DURATION_MS = 1200;

// Format one already-authoritative numeric wallet value without adding a currency glyph.
function defaultFormatAmount(value) {
  // Preserve the shared shell's grouped two-decimal play-token presentation.
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Require the application-owned balance input to be one finite primitive number.
function finiteBalance(value) {
  // Reject strings, booleans, infinities, and NaN before any display or decorative mutation.
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('wallet balance must be finite');
  // Return the reviewed value without coercion or rounding beyond the display formatter.
  return value;
}

// Clamp injected randomness so deterministic tests and production entropy share safe CSS bounds.
function boundedRandom(random) {
  // Read one caller-supplied sample without accepting a non-finite result.
  const sample = Number(random());
  // Collapse malformed samples to the deterministic lower bound.
  if (!Number.isFinite(sample)) return 0;
  // Keep reviewed style variables inside the unit interval.
  return Math.min(1, Math.max(0, sample));
}

// Create one lifecycle-bound wallet celebration controller for the current authenticated session.
export function createWalletCelebration(options = {}) {
  // Bind the persistent amount node whose text remains application-authoritative.
  const amountNode = options.amountNode;
  // Bind the wallet pill that owns all transient CSS state.
  const walletNode = options.walletNode || amountNode?.closest?.('.wallet-pill') || amountNode?.parentElement || null;
  // Bind document creation so listener-free tests can use a deterministic DOM seam.
  const documentRef = options.documentRef || globalThis.document;
  // Bind the normal timer pair so tests can prove cancellation without sleeping.
  const setTimer = options.setTimer || globalThis.setTimeout.bind(globalThis);
  // Bind timer cancellation to the same injected clock.
  const clearTimer = options.clearTimer || globalThis.clearTimeout.bind(globalThis);
  // Bind motion preference evaluation at update time so live preference changes are respected.
  const prefersReducedMotion = options.prefersReducedMotion || (() => Boolean(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches));
  // Bind randomness so every decorative arc can be deterministic under test.
  const random = options.random || Math.random;
  // Bind the shared two-decimal formatter without giving this module wallet authority.
  const formatAmount = options.formatAmount || defaultFormatAmount;
  // Bind an optional low-cardinality completion observer for deterministic lifecycle proof.
  const onComplete = options.onComplete || (() => {});
  // Reject a malformed mount before listeners, timers, or transient nodes can be created.
  if (!amountNode || !walletNode || !documentRef?.createElement) throw new TypeError('wallet celebration mount is unavailable');

  // Track the latest application-authoritative balance independently from transient DOM state.
  let settledBalance = null;
  // Allocate monotonically increasing action identities inside this session generation only.
  let nextActionId = 0;
  // Track the single live visual action so overlap can terminalize it exactly once.
  let activeAction = null;
  // Track every owned timeout so interruption and disposal can cancel all pending work.
  const timers = new Set();
  // Track every transient node so teardown never relies on a future callback.
  const transientNodes = new Set();
  // Track terminal disposal so a stale controller cannot affect a later authenticated session.
  let disposed = false;

  // Remove all owned wallet markers without touching unrelated wallet or shell classes.
  function clearWalletMarkers() {
    // Remove the reviewed ordinary and large-gain presentation classes.
    walletNode.classList.remove('wallet-celebration-gain', 'wallet-celebration-big');
    // Remove the diagnostic lifecycle marker used by exact-head Browser evidence.
    walletNode.removeAttribute('data-wallet-celebration');
  }

  // Cancel every owned timer before any stale callback can publish cleanup or completion.
  function clearOwnedTimers() {
    // Cancel each exact handle through the clock paired with its allocation.
    for (const timer of timers) clearTimer(timer);
    // Forget canceled handles so snapshot evidence reports zero pending work.
    timers.clear();
  }

  // Remove every transient chip and coin layer synchronously at a lifecycle boundary.
  function clearTransientNodes() {
    // Remove only nodes created by this controller generation.
    for (const node of transientNodes) node.remove();
    // Forget removed nodes so later cleanup cannot touch a remounted document.
    transientNodes.clear();
  }

  // Clear all decorative state while deliberately leaving the wallet number untouched.
  function clearVisualState() {
    // Cancel callback-owned future work first.
    clearOwnedTimers();
    // Remove current-generation transient nodes next.
    clearTransientNodes();
    // Remove only this feature's wallet classes and marker last.
    clearWalletMarkers();
  }

  // Publish one terminal result for an action while suppressing duplicate or stale callbacks.
  function completeAction(action, outcome) {
    // Ignore a callback that no longer owns the active action identity.
    if (!action || action.completed || activeAction !== action) return;
    // Mark completion before user-supplied observation can trigger another lifecycle action.
    action.completed = true;
    // Release the active identity before clearing visual state.
    activeAction = null;
    // Remove timers, nodes, and classes synchronously for every outcome.
    clearVisualState();
    // Publish only bounded action facts without DOM, user, or wallet-object references.
    onComplete({ id: action.id, from: action.from, to: action.to, kind: action.kind, outcome });
  }

  // Interrupt the current action exactly once and synchronously clear its owned resources.
  function interrupt(outcome = 'interrupted') {
    // Capture the action before cleanup releases its identity.
    const action = activeAction;
    // Clear dormant visual state even when no action is active.
    if (!action) { clearVisualState(); return; }
    // Terminalize the owned action through the same exactly-once boundary as natural completion.
    completeAction(action, outcome);
  }

  // Schedule natural completion with an identity guard against canceled callback replay.
  function scheduleCompletion(action) {
    // Allocate one bounded timer for the complete decorative window.
    const timer = setTimer(() => {
      // Remove the fired handle before publishing the terminal snapshot.
      timers.delete(timer);
      // Complete only when this exact action still owns the current session controller.
      completeAction(action, 'settled');
    }, CELEBRATION_DURATION_MS);
    // Retain the handle so route and session teardown can cancel it synchronously.
    timers.add(timer);
  }

  // Append one transient node and retain exact ownership for synchronous cleanup.
  function ownTransient(node, parent) {
    // Hide purely decorative content from the accessibility tree.
    node.setAttribute('aria-hidden', 'true');
    // Mount the node only beneath its reviewed shell parent.
    parent.appendChild(node);
    // Retain the exact node identity for interruption and disposal.
    transientNodes.add(node);
    // Return the mounted node for bounded child construction.
    return node;
  }

  // Create a bounded large-gain coin layer around the current wallet geometry.
  function createCoinLayer() {
    // Read the current wallet rectangle without retaining a live layout object.
    const rectangle = walletNode.getBoundingClientRect();
    // Create one fixed-position owner for every decorative coin.
    const layer = documentRef.createElement('div');
    // Apply the reviewed noninteractive coin-layer style hook.
    layer.className = 'wallet-coin-layer';
    // Anchor the layer near the wallet medallion while avoiding shell overflow ownership.
    layer.style.left = `${rectangle.left + (rectangle.width * 0.18)}px`;
    // Center the layer vertically on the persistent wallet.
    layer.style.top = `${rectangle.top + (rectangle.height / 2)}px`;
    // Mount and own the single layer under the document body.
    ownTransient(layer, documentRef.body);
    // Create exactly the reviewed maximum number of decorative coins.
    for (let index = 0; index < MAX_COIN_COUNT; index += 1) {
      // Create one presentation-only coin node.
      const coin = documentRef.createElement('span');
      // Apply the reviewed coin style hook.
      coin.className = 'wallet-coin';
      // Bound horizontal travel to a symmetric seventy-two-pixel arc.
      const horizontalTravel = ((boundedRandom(random) * 2) - 1) * 72;
      // Publish the reviewed peak displacement without CSS typed multiplication.
      coin.style.setProperty('--wallet-coin-x', `${horizontalTravel}px`);
      // Publish the reviewed landing displacement for broad browser compatibility.
      coin.style.setProperty('--wallet-coin-x-final', `${horizontalTravel * 1.2}px`);
      // Bound upward travel to a twenty-eight-through-ninety-pixel arc.
      coin.style.setProperty('--wallet-coin-y', `${-(28 + (boundedRandom(random) * 62))}px`);
      // Bound rotation to a symmetric two-hundred-twenty-degree range.
      coin.style.setProperty('--wallet-coin-rotation', `${(((boundedRandom(random) * 2) - 1) * 220).toFixed(0)}deg`);
      // Bound launch staggering to the first seventy milliseconds.
      coin.style.setProperty('--wallet-coin-delay', `${(boundedRandom(random) * 70).toFixed(0)}ms`);
      // Attach each coin under the one controller-owned layer.
      layer.appendChild(coin);
    }
  }

  // Create the visible positive-delta chip without modifying the authoritative wallet number.
  function createGainChip(gain) {
    // Create one presentation-only delta node.
    const chip = documentRef.createElement('span');
    // Apply the reviewed transient gain style hook.
    chip.className = 'wallet-gain';
    // Show the exact positive delta with the shared two-decimal play-token formatter.
    chip.textContent = `+${formatAmount(gain)}`;
    // Mount and own the chip beneath the persistent wallet pill.
    ownTransient(chip, walletNode);
  }

  // Start normal-motion gain feedback after the application has settled the exact wallet value.
  function startGain(action) {
    // Classify the gain once so style, evidence, and completion share one reviewed decision.
    const big = action.to - action.from >= BIG_GAIN_THRESHOLD;
    // Store the bounded classification on the action receipt.
    action.kind = big ? 'big-gain' : 'gain';
    // Expose the exact current state for Browser synchronization without exposing wallet data.
    walletNode.setAttribute('data-wallet-celebration', action.kind);
    // Apply exactly one reviewed wallet presentation class.
    walletNode.classList.add(big ? 'wallet-celebration-big' : 'wallet-celebration-gain');
    // Create one positive-delta chip for ordinary and large gains.
    createGainChip(action.to - action.from);
    // Add the bounded coin layer only for the reviewed large-gain threshold.
    if (big) createCoinLayer();
    // Schedule one natural completion for every normal-motion visual action.
    scheduleCompletion(action);
  }

  // Seed one authenticated-session baseline without celebrating the initial wallet render.
  function seed(value) {
    // Reject attempts to reuse a disposed session controller.
    if (disposed) throw new Error('wallet celebration controller is disposed');
    // Clear any unexpected transient state before adopting a fresh baseline.
    interrupt('reseeded');
    // Store the application-authoritative initial balance without touching its DOM text.
    settledBalance = finiteBalance(value);
    // Return the exact baseline for deterministic integration checks.
    return settledBalance;
  }

  // Settle one authoritative balance update and optionally decorate a genuine gain.
  function update(value, settleDisplay = null) {
    // Reject attempts to reuse a disposed session controller.
    if (disposed) throw new Error('wallet celebration controller is disposed');
    // Validate the new server-owned value before interrupting the visible prior action.
    const target = finiteBalance(value);
    // Terminalize an overlapping prior action before this update can allocate resources.
    interrupt('interrupted');
    // Invoke the application-owned exact display writer once when this path owns settlement.
    if (settleDisplay) settleDisplay(target);
    // Capture the previous authoritative baseline before adopting the new value.
    const previous = settledBalance;
    // Adopt the latest target before any callback, route change, or later update can run.
    settledBalance = target;
    // Treat the first unseeded update as an initial render with no celebration.
    if (previous === null) return { outcome: 'initial', value: target };
    // Avoid allocating an action for locale rerenders or other unchanged wallet refreshes.
    if (previous === target) return { outcome: 'unchanged', value: target };
    // Allocate the single action identity for this changed authoritative value.
    const action = { id: ++nextActionId, from: previous, to: target, kind: target > previous ? 'gain' : 'loss', completed: false };
    // Publish the action as current before any immediate reduced-motion completion.
    activeAction = action;
    // Settle losses immediately without adding celebratory presentation.
    if (target < previous) { completeAction(action, 'settled'); return { id: action.id, outcome: 'settled', value: target }; }
    // Settle gains immediately when reduced motion is active, leaving zero transient resources.
    if (prefersReducedMotion()) { completeAction(action, 'settled'); return { id: action.id, outcome: 'settled', value: target }; }
    // Start bounded normal-motion feedback after the exact display has settled.
    startGain(action);
    // Return the active identity without exposing internal DOM or timer handles.
    return { id: action.id, outcome: 'active', value: target };
  }

  // Dispose this authenticated-session controller and make every later call fail closed.
  function dispose(outcome = 'disposed') {
    // Ignore repeated disposal without publishing another completion.
    if (disposed) return;
    // Mark terminal state before interruption can invoke caller observation.
    disposed = true;
    // Terminalize the active action and synchronously remove every owned resource.
    interrupt(outcome);
  }

  // Expose only bounded lifecycle operations and low-cardinality deterministic state.
  return {
    // Seed the initial exact wallet without celebration.
    seed,
    // Process one authoritative update with optional exactly-once display settlement.
    update,
    // Interrupt only the current decoration while retaining the authoritative baseline.
    interrupt,
    // Dispose the complete authenticated-session controller.
    dispose,
    // Return resource counts for listener-free acceptance without exposing handles or nodes.
    snapshot: () => ({ active: activeAction?.kind || null, timers: timers.size, nodes: transientNodes.size, disposed, balance: settledBalance }),
  };
}

// Own controller replacement across authentication, pagehide, and BFCache pageshow lifecycles. (UX-023)
export function createWalletCelebrationLifecycle(options = {}) {
  // Bind the page lifecycle surface exactly once for the complete application module lifetime.
  const lifecycleTarget = options.lifecycleTarget || globalThis.window;
  // Bind the production controller factory so remount uses fresh DOM and session identities.
  const createController = options.createController;
  // Bind the authoritative balance reader used only when BFCache restores a session.
  const currentBalance = options.currentBalance;
  // Bind the authoritative display writer used once before a BFCache remount is seeded.
  const settleDisplay = options.settleDisplay || (() => {});
  // Bind the exact authenticated-state guard so logged-out pageshow never mounts wallet behavior.
  const shouldMount = options.shouldMount || (() => false);
  // Reject an incomplete manager before it can register lifecycle listeners.
  if (!lifecycleTarget?.addEventListener || typeof createController !== 'function' || typeof currentBalance !== 'function') throw new TypeError('wallet celebration lifecycle is unavailable');
  // Hold only the current session generation inside this manager, never in ambient globals.
  let controller = null;
  // Track manager disposal separately from per-session unmount.
  let disposed = false;

  // Dispose and forget the current controller before another session or page can mount.
  function unmount(outcome = 'unmounted') {
    // Dispose only the currently owned generation.
    controller?.dispose(outcome);
    // Forget the disposed identity so later updates cannot call it.
    controller = null;
  }

  // Mount one fresh controller and seed the exact already-rendered authoritative value.
  function mount(value) {
    // Reject application reuse after terminal manager disposal.
    if (disposed) throw new Error('wallet celebration lifecycle is disposed');
    // Dispose a prior authenticated generation before creating a replacement.
    unmount('remounted');
    // Create a controller from the current document and application seams.
    const nextController = createController();
    // Seed before publishing the controller so a failed mount cannot leave a partial identity.
    nextController.seed(finiteBalance(value));
    // Publish only the completely initialized controller.
    controller = nextController;
    // Return the seeded controller for focused integration diagnostics.
    return controller;
  }

  // Forward one update only while a current session generation is mounted.
  function update(value, writer = null) {
    // Ignore hidden-period or logged-out updates without throwing into event listeners.
    if (!controller) return { outcome: 'inactive', value };
    // Delegate exact settlement and decoration to the current generation.
    return controller.update(value, writer);
  }

  // Interrupt only current decoration while retaining the mounted session baseline.
  function interrupt(outcome = 'interrupted') {
    // Leave inactive pages as a no-op.
    controller?.interrupt(outcome);
  }

  // Drop the page-hidden generation so BFCache can never retain a disposed controller reference.
  function handlePageHide() {
    // Dispose and forget the exact current generation synchronously.
    unmount('pagehide');
  }

  // Recreate one current-session controller after a normal or BFCache page restoration.
  function handlePageShow() {
    // Ignore ordinary pageshow when a controller already owns the live authenticated session.
    if (controller || disposed || !shouldMount()) return;
    // Read and validate the latest application-authoritative balance before writing any DOM.
    const value = finiteBalance(currentBalance());
    // Restore the exact wallet display once before adopting it as the new silent baseline.
    settleDisplay(value);
    // Mount a fresh generation so no pre-pagehide handle, node, callback, or state survives.
    mount(value);
  }

  // Dispose the complete manager when the application module itself is intentionally retired.
  function dispose() {
    // Ignore duplicate terminal disposal.
    if (disposed) return;
    // Mark terminal state before unmount can invoke completion observation.
    disposed = true;
    // Dispose and forget the current authenticated generation.
    unmount('disposed');
    // Remove the exact pagehide listener owned by this manager.
    lifecycleTarget.removeEventListener('pagehide', handlePageHide);
    // Remove the exact pageshow listener owned by this manager.
    lifecycleTarget.removeEventListener('pageshow', handlePageShow);
  }

  // Register one symmetric pagehide/pageshow pair for BFCache-safe ownership.
  lifecycleTarget.addEventListener('pagehide', handlePageHide);
  // Register restoration after the teardown listener is already active.
  lifecycleTarget.addEventListener('pageshow', handlePageShow);

  // Expose bounded application integration operations without leaking controller identity.
  return {
    // Mount one authenticated session from its already-rendered balance.
    mount,
    // Update only the current mounted session generation.
    update,
    // Interrupt only transient presentation for route navigation.
    interrupt,
    // Dispose and forget one authenticated session while retaining page listeners.
    unmount,
    // Dispose the complete page lifecycle manager.
    dispose,
    // Return only low-cardinality lifecycle and current resource facts.
    snapshot: () => ({ mounted: Boolean(controller), disposed, controller: controller?.snapshot() || null }),
  };
}
