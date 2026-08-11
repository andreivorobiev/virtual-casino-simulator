// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for native transport and lifecycle policy.
import assert from "node:assert/strict";
// Import the deterministic built-in test runner.
import test from "node:test";
// Import the OS-vault bridge wrapper and generation authority.
import { authorizeDeepLinkArrival, createLatestNativeObservation, createLifecycleGate, createMobileRecoveryCoordinator, createMobileTransport, exactWebViewAuthority } from "../runtime/transport.js";

// Define public backend and Android WebView origins without live network use.
const BACKEND = "https://casino.tiltseven.com";
// Define one exact generated Android Capacitor origin.
const WEBVIEW = "https://localhost";

// Verify an offline process restores authority and loads shared code exactly once after reconnect.
test("recovers offline cold start exactly once after the first authoritative reconnect", async () => {
  // Count each injected authority boundary independently.
  const calls = { revalidate: 0, load: 0, reconnect: 0 };
  // Create one pure coordinator without Capacitor or DOM dependencies.
  const recovery = createMobileRecoveryCoordinator({ revalidate: async () => { calls.revalidate += 1; }, load: async () => { calls.load += 1; }, reconnect: async () => { calls.reconnect += 1; } });
  // Model a process restored offline with a saved native vault record.
  recovery.setConnected(false);
  // Keep shared application code absent and avoid a doomed session probe.
  assert.equal(await recovery.recover(), false); assert.deepEqual(calls, { revalidate: 0, load: 0, reconnect: 0 });
  // Restore connectivity and deliver two overlapping native recovery events.
  recovery.setConnected(true); recovery.setActive(true); await Promise.all([recovery.recover(), recovery.recover()]);
  // Require one authoritative probe and one shared application load.
  assert.deepEqual(calls, { revalidate: 1, load: 1, reconnect: 0 }); assert.equal(recovery.isLoaded(), true);
  // Cross another network edge after the application is already running.
  recovery.setConnected(false); recovery.setConnected(true); await recovery.recover();
  // Revalidate and refresh authoritative state without appending another entry point.
  assert.deepEqual(calls, { revalidate: 2, load: 1, reconnect: 1 });
});

// Verify a transient cold-start probe failure remains retryable without loading shared code.
test("keeps failed cold-start recovery closed until a later successful probe", async () => {
  // Fail the first probe and accept the next one under the same connected process.
  let attempts = 0; let loads = 0;
  // Create one coordinator whose first server authority result is unavailable.
  const recovery = createMobileRecoveryCoordinator({ revalidate: async () => { attempts += 1; if (attempts === 1) throw new Error("unavailable"); }, load: async () => { loads += 1; }, reconnect: async () => {} });
  // Admit native network recovery.
  recovery.setConnected(true); recovery.setActive(true);
  // Reject the first attempt while retaining an unloaded exact-once state.
  await assert.rejects(recovery.recover(), /unavailable/); assert.equal(recovery.isLoaded(), false); assert.equal(loads, 0);
  // Permit a later native event to recover rather than leaving bootstrap permanently dead.
  assert.equal(await recovery.recover(), true); assert.equal(recovery.isLoaded(), true); assert.equal(loads, 1);
});

// Verify network and background edges after a probe cannot release cold or warm application work.
test("rejects availability edges that cross cold load or warm reconnect recovery", async () => {
  // Exercise a cold network edge and a warm background edge under independent coordinators.
  for (const phase of ["cold-network", "warm-background"]) {
    // Count protected application boundaries without native or DOM dependencies.
    let probes = 0; let loads = 0; let reconnects = 0;
    // Retain the coordinator after callbacks are defined so the probe can inject an exact edge.
    let recovery;
    // Build one coordinator whose selected probe crosses an availability boundary before returning.
    recovery = createMobileRecoveryCoordinator({ revalidate: async () => { probes += 1; if ((phase === "cold-network" && probes === 1) || (phase === "warm-background" && probes === 2)) { if (phase === "cold-network") recovery.setConnected(false); else recovery.setActive(false); } }, load: async () => { loads += 1; }, reconnect: async () => { reconnects += 1; } });
    // Start from exact connected foreground state.
    recovery.setConnected(true); recovery.setActive(true);
    // Reject the cold crossed probe before shared application load.
    if (phase === "cold-network") { await assert.rejects(recovery.recover(), /MOBILE_RECOVERY_STALE/); assert.deepEqual([loads, reconnects], [0, 0]); continue; }
    // Load once under an un-crossed initial probe for the warm scenario.
    await recovery.recover(); assert.equal(loads, 1);
    // Reject the later foreground-crossed probe before authoritative reconnect refresh.
    await assert.rejects(recovery.recover(), /MOBILE_RECOVERY_STALE/); assert.deepEqual([loads, reconnects], [1, 0]);
  }
});

// Verify a process restored in the background cannot probe or load until exact foreground state.
test("holds cold background restore until the first foreground recovery", async () => {
  // Count the sole probe and load boundaries.
  let probes = 0; let loads = 0;
  // Build one coordinator representing a connected but background-restored process.
  const recovery = createMobileRecoveryCoordinator({ revalidate: async () => { probes += 1; }, load: async () => { loads += 1; }, reconnect: async () => {} });
  // Bind initial native state before any recovery call.
  recovery.setConnected(true); recovery.setActive(false);
  // Keep both session probe and shared code absent while backgrounded.
  assert.equal(await recovery.recover(), false); assert.deepEqual([probes, loads], [0, 0]);
  // Cross the exact foreground edge and recover once.
  recovery.setActive(true); assert.equal(await recovery.recover(), true);
  // Require exactly one authoritative probe and one shared application load.
  assert.deepEqual([probes, loads], [1, 1]);
});

// Verify every process starts inactive even when networking and stale vault metadata exist.
test("keeps default lifecycle and recovery authority inactive until exact App state", async () => {
  // Create one gate and bind only network plus an otherwise valid vault generation.
  const gate = createLifecycleGate({ now: () => 850 }); gate.setConnected(true); gate.validate(1);
  // Reject both ordinary reads and the dedicated probe while initial foreground state is unknown.
  assert.throws(() => gate.begin("GET"), /MOBILE_APP_BACKGROUND/); assert.throws(() => gate.beginProbe(), /MOBILE_APP_BACKGROUND/);
  // Create one connected recovery coordinator without publishing App foreground state.
  let probes = 0; const recovery = createMobileRecoveryCoordinator({ revalidate: async () => { probes += 1; }, load: async () => {}, reconnect: async () => {} }); recovery.setConnected(true);
  // Keep native probing and shared loading closed until the exact active snapshot or event arrives.
  assert.equal(await recovery.recover(), false); assert.equal(probes, 0);
});

// Verify listener events supersede stale initial and foreground snapshots without state reordering.
test("preserves the newest native event across asynchronous snapshots", async () => {
  // Retain only accepted state values in application order.
  const applied = [];
  // Build the same pure epoch observer used for network, app, and deep-link snapshots.
  const observation = createLatestNativeObservation(async (value, source) => { applied.push([value, source]); });
  // Begin an initial snapshot before a newer listener event arrives.
  const initial = observation.beginSnapshot(); await observation.event("online-event");
  // Reject the stale offline snapshot rather than overwriting the event.
  assert.equal(await observation.completeSnapshot(initial, "offline-snapshot"), false);
  // Begin a foreground network snapshot and supersede it with a disconnect event.
  const foreground = observation.beginSnapshot(); await observation.event("offline-event");
  // Reject the stale reconnect snapshot so observers never receive true after false.
  assert.equal(await observation.completeSnapshot(foreground, "online-snapshot"), false);
  // Require exact event-only order with no stale snapshot application.
  assert.deepEqual(applied, [["online-event", "event"], ["offline-event", "event"]]);
});

// Verify bootstrap awaits a superseding event whose asynchronous state sink has not completed yet.
test("awaits deferred listener application after rejecting a stale startup snapshot", async () => {
  // Hold the event sink so snapshot classification can race ahead of its application.
  let releaseEvent; const deferredEvent = new Promise(resolve => { releaseEvent = resolve; });
  // Retain exact sink order without native plugins.
  const applied = [];
  // Build one observer whose newest event cannot bind until the test releases it.
  const observation = createLatestNativeObservation(async (value, source) => { applied.push([value, source]); if (source === "event") await deferredEvent; });
  // Start the stale snapshot, then publish a newer listener event without awaiting it.
  const snapshot = observation.beginSnapshot(); const eventPending = observation.event("foreground-event"); const snapshotPending = observation.completeSnapshot(snapshot, "background-snapshot");
  // Yield once and prove no authority binds before the listener sink finishes.
  await Promise.resolve(); assert.equal(observation.isBound(), false);
  // Start the same bootstrap barrier used by Network and App initialization.
  const boundPending = observation.whenBound();
  // Release the exact listener sink and wait for every caller-visible classification.
  releaseEvent(); await eventPending; assert.equal(await snapshotPending, false); assert.equal(await boundPending, true);
  // Require one applied current event and no stale snapshot application.
  assert.deepEqual(applied, [["foreground-event", "event"]]);
});

// Verify a new pending event closes older snapshot or event binding until its sink succeeds.
test("does not reuse older bound authority while the newest event is pending", async () => {
  // Exercise prior snapshot-bound and prior event-bound observer states independently.
  for (const priorSource of ["snapshot", "event"]) {
    // Hold only the newest event application.
    let releaseNewest; const deferredNewest = new Promise(resolve => { releaseNewest = resolve; }); let defer = false;
    // Build one observer whose newest selected event waits on the controlled boundary.
    const observation = createLatestNativeObservation(async value => { if (defer && value === "newest") await deferredNewest; });
    // Bind authority through the selected older source.
    if (priorSource === "snapshot") { const ticket = observation.beginSnapshot(); assert.equal(await observation.completeSnapshot(ticket, "initial"), true); } else await observation.event("initial");
    // Start the newer event without awaiting its sink and require synchronous invalidation.
    defer = true; const eventPending = observation.event("newest"); assert.equal(observation.isBound(), false);
    // Start the bootstrap barrier and prove it remains pending before the event applies.
    let settled = false; const boundPending = observation.whenBound().then(value => { settled = value; return value; }); await Promise.resolve(); assert.equal(settled, false);
    // Release the event and require only its successful completion to restore binding.
    releaseNewest(); await eventPending; assert.equal(await boundPending, true); assert.equal(observation.isBound(), true);
  }
});

// Verify a failed listener sink propagates and never masquerades as initialized authority.
test("propagates failed listener application without marking native authority bound", async () => {
  // Fail only the first native listener application.
  let fail = true;
  // Build one observer with an exact recoverable state sink.
  const observation = createLatestNativeObservation(async () => { if (fail) throw new Error("apply failed"); });
  // Supersede one startup snapshot with the failing listener event.
  const snapshot = observation.beginSnapshot(); const failedEvent = observation.event("bad-event"); const staleSnapshot = observation.completeSnapshot(snapshot, "stale-snapshot");
  // Surface the sink failure and preserve the stale snapshot classification.
  await assert.rejects(failedEvent, /apply failed/); assert.equal(await staleSnapshot, false); await assert.rejects(observation.whenBound(), /apply failed/); assert.equal(observation.isBound(), false);
  // Permit a later exact event to recover observer authority after the failed sink.
  fail = false; await observation.event("good-event"); assert.equal(await observation.whenBound(), true);
});

// Verify deferred foreground work never queues a later background invalidation behind it.
test("invalidates immediately when background arrives during foreground network refresh", async () => {
  // Bind one initially active process and retain an old game read ticket.
  const gate = createLifecycleGate({ now: () => 875 }); gate.setConnected(true); gate.setActive(true); gate.validate(1); const oldTicket = gate.begin("GET");
  // Hold foreground network refresh until after the background edge is applied.
  let releaseStatus; const statusPending = new Promise(resolve => { releaseStatus = resolve; });
  // Track applied app edges and accepted foreground refreshes.
  let appEpoch = 0; let refreshes = 0;
  // Build the runtime pattern whose state sink schedules rather than awaits foreground work.
  const observation = createLatestNativeObservation((state, source) => { appEpoch += 1; gate.setActive(state.isActive); if (source === "event" && state.isActive) { const expectedEpoch = appEpoch; void statusPending.then(() => { if (expectedEpoch === appEpoch) refreshes += 1; }); } });
  // Start foreground refresh without waiting for native status and then deliver background.
  await observation.event({ isActive: true }); await observation.event({ isActive: false });
  // Reject new reads immediately while the earlier foreground status remains unresolved.
  assert.throws(() => gate.begin("GET"), /MOBILE_APP_BACKGROUND/);
  // Release stale foreground work and prove it cannot recover the backgrounded process.
  releaseStatus(); await Promise.resolve(); await Promise.resolve(); assert.equal(refreshes, 0); assert.throws(() => gate.complete(oldTicket, 1), /MOBILE_STALE_COMPLETION/);
});

// Verify raw offline and background callbacks invalidate before observer promises can settle.
test("invalidates raw negative lifecycle edges without awaiting observer work", async () => {
  // Exercise native Network and App negative edges under independent lifecycle gates.
  for (const edge of ["network", "app"]) {
    // Bind current read authority and retain its completion ticket.
    const gate = createLifecycleGate({ now: () => 890 }); gate.setConnected(true); gate.setActive(true); gate.validate(1); const oldTicket = gate.begin("GET");
    // Hold observer work to prove raw invalidation does not depend on its promise.
    let releaseObserver; const observerPending = new Promise(resolve => { releaseObserver = resolve; }); const observation = createLatestNativeObservation(async () => { await observerPending; });
    // Model the exact listener callback order used by mobile-runtime.js without awaiting event().
    if (edge === "network") { gate.setConnected(false); void observation.event({ connected: false }); } else { gate.setActive(false); void observation.event({ isActive: false }); }
    // Reject new work and stale completion synchronously before observer release.
    assert.throws(() => gate.begin("GET"), edge === "network" ? /MOBILE_NETWORK_UNAVAILABLE/ : /MOBILE_APP_BACKGROUND/); assert.throws(() => gate.complete(oldTicket, 1), /MOBILE_STALE_COMPLETION/);
    // Release the observer only after immediate authority checks complete.
    releaseObserver(); await observation.whenBound();
  }
});

// Verify launch-snapshot and appUrlOpen duplication produces one token-free navigation.
test("handles a deep-link event during launch snapshot exactly once", async () => {
  // Retain only digest-like fingerprints and public token-free history values.
  const handled = new Set(); const publicHistory = [];
  // Build the same listener-first observation used by the runtime deep-link queue.
  const observation = createLatestNativeObservation(async candidate => { if (handled.has(candidate.fingerprint)) return; handled.add(candidate.fingerprint); publicHistory.push(candidate.publicLocation); });
  // Begin the cold launch snapshot before an equivalent warm event arrives.
  const snapshot = observation.beginSnapshot(); const event = { fingerprint: "c".repeat(64), publicLocation: "/account/reset" }; await observation.event(event);
  // Reject the duplicated snapshot and await exact listener authority.
  assert.equal(await observation.completeSnapshot(snapshot, event), false); await observation.whenBound();
  // Require one navigation whose public location contains no bearer material.
  assert.deepEqual(publicHistory, ["/account/reset"]); assert.doesNotMatch(publicHistory[0], /token|bearer/i);
});

// Verify shared readiness cannot turn green before load settles and later recovery refreshes once.
test("waits for deferred shared readiness and refreshes once after a crossed edge", async () => {
  // Retain one controllable shared-application readiness boundary.
  let releaseLoad; const deferredLoad = new Promise(resolve => { releaseLoad = resolve; });
  // Count exact probe, script-load, and authoritative refresh operations.
  let probes = 0; let loads = 0; let reconnects = 0;
  // Build one coordinator whose sole load waits for the explicit shared ready handshake.
  const recovery = createMobileRecoveryCoordinator({ revalidate: async () => { probes += 1; }, load: async () => { loads += 1; await deferredLoad; }, reconnect: async () => { reconnects += 1; } }); recovery.setConnected(true); recovery.setActive(true);
  // Begin cold recovery and wait until the one load boundary is actually pending.
  const pending = recovery.recover(); while (loads === 0) await Promise.resolve();
  // Cross offline while module readiness is pending, then release the shared handshake.
  recovery.setConnected(false); releaseLoad(); await assert.rejects(pending, /MOBILE_RECOVERY_STALE/);
  // Reconnect and require an authoritative refresh without a duplicate application load.
  recovery.setConnected(true); assert.equal(await recovery.recover(), true); assert.deepEqual([probes, loads, reconnects], [2, 1, 1]);
});

// Verify failed initial state can recover through one already-loaded shared controller.
test("reuses one shared controller after initial state failure", async () => {
  // Count module append, load attempts, and controller-owned recovery separately.
  let scripts = 0; let loadAttempts = 0; let internalReconnects = 0; let controllerLoaded = false;
  // Model the runtime loader whose first initial-state result fails after controller construction.
  const load = async () => { loadAttempts += 1; if (!controllerLoaded) { controllerLoaded = true; scripts += 1; throw new Error("initial state unavailable"); } internalReconnects += 1; };
  // Build one connected foreground recovery coordinator around that exact reusable loader.
  const recovery = createMobileRecoveryCoordinator({ revalidate: async () => {}, load, reconnect: async () => {} }); recovery.setConnected(true); recovery.setActive(true);
  // Reject first readiness without marking the coordinator loaded.
  await assert.rejects(recovery.recover(), /initial state unavailable/); assert.equal(recovery.isLoaded(), false);
  // Recover later through the same controller without appending another script.
  assert.equal(await recovery.recover(), true); assert.deepEqual([scripts, loadAttempts, internalReconnects], [1, 2, 1]); assert.equal(recovery.isLoaded(), true);
});

// Verify real iOS bootstrap derives a reviewed custom-scheme authority instead of URL.origin null.
test("derives exact capacitor authority from the complete runtime location", () => {
  // Require a normal bundled route to reduce to the exact native configuration authority.
  assert.equal(exactWebViewAuthority("capacitor://localhost/index.html?cold=1#route"), "capacitor://localhost");
  // Reject hostile location authority components before plugin configuration.
  assert.throws(() => exactWebViewAuthority("capacitor://user:pass@localhost/index.html"), /MOBILE_WEBVIEW_ORIGIN_INVALID/);
  // Reject alternate local ports that are outside the reviewed native origin.
  assert.throws(() => exactWebViewAuthority("https://localhost:444/index.html"), /MOBILE_WEBVIEW_ORIGIN_INVALID/);
});

// Verify a warm account link invalidates old game work before its replay fingerprint is claimed.
test("revalidates warm deep links before claim and leaves failed claims reopenable", async () => {
  // Bind one connected process and old game ticket to vault generation one.
  const gate = createLifecycleGate({ now: () => 900 }); gate.setConnected(true); gate.setActive(true); gate.validate(1); const oldGameTicket = gate.begin("GET");
  // Count durable replay claims independently from session probes.
  let claims = 0;
  // Revalidate through the same ticketed probe boundary used by native transport.
  const revalidate = async () => { const ticket = gate.beginProbe(); gate.completeProbe(ticket, 1); };
  // Authorize one warm link and claim its digest only after successful revalidation.
  await authorizeDeepLinkArrival({ warm: true, lifecycle: gate, revalidate, claim: async () => { claims += 1; }, activate: async () => {}, fingerprint: "a".repeat(64) });
  // Reject every completion started by the prior game shell and reopen current public mutations.
  assert.throws(() => gate.complete(oldGameTicket, 1), /MOBILE_STALE_COMPLETION/); assert.doesNotThrow(() => gate.begin("POST")); assert.equal(claims, 1);
  // Fail a later warm revalidation before claim so the user may reopen the unconsumed link.
  await assert.rejects(authorizeDeepLinkArrival({ warm: true, lifecycle: gate, revalidate: async () => { throw new Error("probe unavailable"); }, claim: async () => { claims += 1; }, activate: async () => {}, fingerprint: "b".repeat(64) }), /probe unavailable/);
  // Preserve the single first claim because failed authority never consumes replay state.
  assert.equal(claims, 1);
});

// Create one fake native plugin that retains descriptors but no real credentials.
function fakePlugin({ status = 200, generation = 0 } = {}) {
  // Retain every public bridge call for exact assertions.
  const calls = [];
  // Return the injectable plugin surface.
  return { calls, configure: async value => { calls.push(["configure", value]); }, request: async value => { calls.push(["request", value]); return { status, generation, headers: { "Content-Type": "application/json" }, body: '{"ok":true,"data":{}}' }; }, probe: async () => ({ authenticated: status === 200, generation, status }), revokeAndClear: async () => ({ revoked: true, cleared: true }), claimDeepLink: async () => ({ claimed: true }) };
}

// Verify no login, current-user, probe, or rotation envelope can expose vault-owned fields to JavaScript.
test("rejects credentials recursively in native JavaScript-visible envelopes", async () => {
  // Exercise each native credential-bearing server surface through one shared rejection oracle.
  for (const [path, leakedField] of [["/api/v2/auth/login", "token"], ["/api/v2/me", "csrf_token"], ["/api/v2/auth/mobile/session", "guest_browser_nonce"], ["/api/v2/auth/mobile/session/rotate", "token"]]) {
    // Create a fresh validated generation for this exact response.
    const gate = createLifecycleGate({ now: () => 1500 });
    // Permit one native request under generation one.
    gate.setConnected(true); gate.setActive(true); gate.validate(1);
    // Return one deliberately leaked nested credential from the fake native bridge.
    const plugin = fakePlugin({ generation: path.endsWith("/rotate") || path.endsWith("/login") ? 2 : 1 });
    // Override only the request result while retaining the test plugin surface.
    plugin.request = async value => { plugin.calls.push(["request", value]); return { status: 200, generation: path.endsWith("/rotate") || path.endsWith("/login") ? 2 : 1, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ok: true, data: { nested: [{ [leakedField]: "secret" }] } }) }; };
    // Bind the fake bridge to one scoped transport.
    const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
    // Reject before a response object can reach shared application code.
    await assert.rejects(transport.fetch(path, { method: path.endsWith("/rotate") || path.endsWith("/login") ? "POST" : "GET", body: path.endsWith("/rotate") || path.endsWith("/login") ? "{}" : undefined }), /MOBILE_NATIVE_SECRET_LEAK/);
  }
});

// Verify complete Request semantics cross the bridge without JavaScript credentials.
test("preserves Request method, public headers, body, and generation", async () => {
  // Create one connected process and authoritative vault generation.
  const gate = createLifecycleGate({ now: () => 1000 });
  // Mark native connectivity before the server probe.
  gate.setConnected(true); gate.setActive(true);
  // Bind the process to synthetic native generation three.
  gate.validate(3);
  // Capture native bridge descriptors without network access.
  const plugin = fakePlugin({ generation: 3 });
  // Create the scoped transport.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
  // Configure public origins inside the fake native boundary.
  await transport.configure();
  // Build a caller-owned Request with public headers and one body.
  const request = new Request(`${WEBVIEW}/api/v2/me/tokens/add?source=mobile`, { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: '{"amount":5}', credentials: "omit" });
  // Execute exactly once through the bridge.
  await transport.fetch(request);
  // Resolve the only request descriptor after configure.
  const descriptor = plugin.calls.find(row => row[0] === "request")[1];
  // Require frozen path/query, method, body, and generation to remain exact.
  assert.deepEqual([descriptor.path, descriptor.method, descriptor.body, descriptor.generation], ["/api/v2/me/tokens/add?source=mobile", "POST", '{"amount":5}', 3]);
  // Require only public headers to cross the JavaScript/native boundary.
  assert.deepEqual(Object.keys(descriptor.headers).map(value => value.toLowerCase()).sort(), ["accept", "content-type"]);
  // Match standard fetch semantics by proving the supplied Request body was consumed exactly once.
  assert.equal(request.bodyUsed, true);
});

// Verify credential fields, foreign authority, and non-API attempts stop before native code.
test("rejects JavaScript credentials and unowned destinations", async () => {
  // Create a connected validated generation.
  const gate = createLifecycleGate({ now: () => 2000 });
  // Admit native network work and bind generation one.
  gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Capture any prohibited bridge call.
  const plugin = fakePlugin({ generation: 1 });
  // Create the scoped transport.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
  // Reject a foreign authority.
  await assert.rejects(transport.fetch("https://evil.example/api/v2/me"), /MOBILE_CROSS_ORIGIN_BLOCKED/);
  // Reject user information and alternate ports even when the remaining host is allowlisted.
  await assert.rejects(transport.fetch("https://user:pass@localhost/api/v2/me"), /MOBILE_CROSS_ORIGIN_BLOCKED/);
  // Reject a request-level port that would otherwise be lost by host-only comparison.
  await assert.rejects(transport.fetch("https://localhost:444/api/v2/me"), /MOBILE_CROSS_ORIGIN_BLOCKED/);
  // Reject cookie, bearer, and JavaScript CSRF independently.
  for (const headers of [{ Cookie: "casino_session=secret" }, { Authorization: "Bearer secret" }, { "X-CSRF-Token": "secret" }]) await assert.rejects(transport.fetch("/api/v2/me", { headers }), /MOBILE_JAVASCRIPT_CREDENTIAL_FORBIDDEN/);
  // Reject bundled asset use through native authenticated transport.
  await assert.rejects(transport.fetch("/i18n/manifest.json"), /MOBILE_NON_API_TRANSPORT_FORBIDDEN/);
  // Prove no request crossed the native boundary.
  assert.equal(plugin.calls.filter(row => row[0] === "request").length, 0);
});

// Verify the custom Capacitor origin remains exact instead of collapsing to WHATWG `null`.
test("configures and routes the exact capacitor custom-scheme authority", async () => {
  // Create one connected validated native authority.
  const gate = createLifecycleGate({ now: () => 2250 });
  // Bind a synthetic vault generation before one read.
  gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Capture exact configuration and request descriptors.
  const plugin = fakePlugin({ generation: 1 });
  // Build the transport under the iOS custom-scheme origin.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: "capacitor://localhost", lifecycle: gate, nativePlugin: plugin });
  // Configure the native bridge without serializing the authority as `null`.
  await transport.configure();
  // Route one relative API read through the same custom-scheme authority.
  await transport.fetch("/api/v2/me");
  // Require exact custom-scheme configuration and path-only native dispatch.
  assert.deepEqual(plugin.calls[0], ["configure", { backendOrigin: BACKEND, webViewOrigin: "capacitor://localhost" }]);
  // Require the API read to retain its bounded path.
  assert.equal(plugin.calls[1][1].path, "/api/v2/me");
});

// Verify background, expiry, rollback, and stale completion policy.
test("invalidates session and in-flight work across lifecycle generations", () => {
  // Use one deterministic mutable device clock.
  let current = 10000;
  // Create a bounded authority age.
  const gate = createLifecycleGate({ now: () => current, maxValidationAgeMs: 1000 });
  // Mark network connected and validate generation four.
  gate.setConnected(true); gate.setActive(true); gate.validate(4);
  // Capture an action ticket in generation four.
  const ticket = gate.begin("POST");
  // Background then foreground to advance generation and invalidate the ticket.
  gate.setActive(false); gate.setActive(true);
  // Reject completion from the prior generation.
  assert.throws(() => gate.complete(ticket, 4), /MOBILE_STALE_COMPLETION/);
  // Require a fresh probe before another mutation.
  assert.throws(() => gate.begin("POST"), /MOBILE_SESSION_REVALIDATION_REQUIRED/);
  // Revalidate, then advance beyond bounded age.
  gate.validate(7); current += 1001;
  // Reject stale authority.
  assert.throws(() => gate.begin("POST"), /MOBILE_SESSION_REVALIDATION_REQUIRED/);
  // Revalidate then move clock backward.
  gate.validate(9); current -= 500;
  // Reject rollback authority.
  assert.throws(() => gate.begin("POST"), /MOBILE_SESSION_REVALIDATION_REQUIRED/);
});

// Verify local vault generations never repeat when server session generations restart for another account.
test("rejects a late account-A completion after clear and account-B login", () => {
  // Create one deterministic process authority.
  const gate = createLifecycleGate({ now: () => 2500 });
  // Bind account A to local vault generation one.
  gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Start one account-A read before account switching.
  const accountATicket = gate.begin("GET");
  // Model verified clear advancing the local vault generation to two.
  gate.invalidate(); gate.validate(2);
  // Model account B receiving server generation one but local vault generation three.
  const accountBLogin = gate.begin("POST"); gate.validate(3);
  // Require account B's session-changing completion to own generation three.
  assert.equal(accountBLogin.vaultGeneration, 2);
  // Reject the late account-A result even though its server session generation could also be one.
  assert.throws(() => gate.complete(accountATicket, 1), /MOBILE_STALE_COMPLETION/);
  // Require current process authority to remain monotonically advanced for account B.
  assert.equal(gate.generation(), 3);
});

// Verify lifecycle revalidation cannot resurrect a ticket when the vault generation is unchanged.
test("rejects a pre-edge completion after same-vault-generation revalidation", () => {
  // Create one deterministic process authority bound to vault generation one.
  const gate = createLifecycleGate({ now: () => 2750 });
  // Admit work and record the first authoritative session probe.
  gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Capture an action before a network trust-boundary change.
  const staleTicket = gate.begin("GET");
  // Cross both network edges and revalidate the unchanged OS-vault record.
  gate.setConnected(false); gate.setConnected(true); gate.validate(1);
  // Reject the earlier completion even though native response generation still equals one.
  assert.throws(() => gate.complete(staleTicket, 1), /MOBILE_STALE_COMPLETION/);
  // Reject an intentional credential-changing result from the same stale request epoch.
  assert.throws(() => gate.transition(staleTicket, 2), /MOBILE_STALE_COMPLETION/);
  // Preserve the current vault generation when the stale transition is rejected.
  assert.equal(gate.generation(), 1);
  // Permit a ticket created after the fresh probe under the unchanged vault generation.
  const currentTicket = gate.begin("GET");
  // Accept only the fresh process-epoch ticket.
  assert.doesNotThrow(() => gate.complete(currentTicket, 1));
});

// Verify account switch revokes and clears before process generation changes.
test("account switch permits only exact login or guest issuance after empty-vault proof", async () => {
  // Exercise registered login and guest issuance under independent cleared-vault processes.
  for (const path of ["/api/v2/auth/login", "/api/v2/auth/guest"]) {
    // Create a connected validated process for one predecessor account.
    const gate = createLifecycleGate({ now: () => 3000 }); gate.setConnected(true); gate.setActive(true); gate.validate(2);
    // Capture one ordinary old-account completion before switch initiation.
    const oldAccountTicket = gate.begin("GET");
    // Create one native seam whose revoke advances to an exact empty generation three.
    const plugin = fakePlugin({ generation: 2 }); plugin.probe = async () => ({ authenticated: false, generation: 3, status: 401 });
    // Return one successful native credential commit at generation four.
    plugin.request = async value => { plugin.calls.push(["request", value]); return { status: 200, generation: 4, sessionChanged: true, headers: { "Content-Type": "application/json" }, body: '{"ok":true,"data":{"session":{"session_id":"public","generation":1}}}' }; };
    // Create the scoped transport and revoke, verify, and clear within native code.
    const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin }); await transport.prepareAccountSwitch();
    // Reject the old-account completion and retain probe-only unreconciled authority.
    assert.throws(() => gate.complete(oldAccountTicket, 3), /MOBILE_STALE_COMPLETION/); assert.equal(gate.isValidated(), true); assert.equal(gate.isReconciled(), false);
    // Permit only the exact issuance mutation once without a general shared-state refresh.
    await transport.fetch(path, { method: "POST", body: "{}" }); assert.equal(plugin.calls.filter(row => row[0] === "request").length, 1); assert.equal(gate.isReconciled(), true);
  }
});

// Verify an in-flight native session probe cannot overwrite lifecycle or clock invalidation.
test("rejects probes crossed by network, foreground, or clock edges", async () => {
  // Exercise each trust-boundary edge under a fresh deterministic gate and deferred native probe.
  for (const edge of ["network", "foreground", "clock"]) {
    // Retain a mutable clock so rollback can be injected while one probe is in flight.
    let current = 4000;
    // Create one connected validated vault authority.
    const gate = createLifecycleGate({ now: () => current, maxValidationAgeMs: 1000 });
    // Bind initial connectivity and generation one.
    gate.setConnected(true); gate.setActive(true); gate.validate(1);
    // Retain a resolver so the edge happens after probe start and before completion.
    let resolveProbe;
    // Create one fake plugin with a deliberately deferred session probe.
    const plugin = fakePlugin({ generation: 1 });
    // Replace only the probe seam with the controlled pending result.
    plugin.probe = async () => new Promise(resolve => { resolveProbe = resolve; });
    // Bind the deferred bridge to the scoped transport.
    const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
    // Start the probe and allow its async bridge call to capture the resolver.
    const pending = transport.revalidate(); await Promise.resolve();
    // Cross the selected trust boundary while the probe remains unresolved.
    if (edge === "network") { gate.setConnected(false); gate.setConnected(true); }
    // Cross background and foreground boundaries without changing vault credentials.
    if (edge === "foreground") { gate.setActive(false); gate.setActive(true); }
    // Move the observed clock backward so completion cannot restamp stale authority.
    if (edge === "clock") current -= 1;
    // Complete the native probe with the unchanged vault generation.
    resolveProbe({ authenticated: true, generation: 1, status: 200 });
    // Require every crossed probe to reject rather than reopen controls.
    await assert.rejects(pending, /MOBILE_STALE_COMPLETION/);
    // Require a fresh successful probe before protected work can resume.
    plugin.probe = async () => ({ authenticated: true, generation: 1, status: 200 });
    // Restore monotonic time only after the rejected rollback case.
    if (edge === "clock") current += 2;
    // Revalidate under the new lifecycle epoch.
    await transport.revalidate();
    // Reconcile shared state under the fresh probe ticket before mutations reopen.
    const reconciliation = gate.beginReconciliation(); gate.completeReconciliation(reconciliation);
    // Prove protected mutations reopen only after probe and shared reconciliation.
    assert.doesNotThrow(() => gate.begin("POST"));
  }
});

// Verify server failures, malformed results, and vault-generation rollback leave revalidation closed.
test("rejects non-authoritative and rollback probe results", async () => {
  // Exercise a server failure and a lower native generation independently.
  for (const result of [{ authenticated: false, generation: 2, status: 500 }, { authenticated: true, generation: 1, status: 200 }]) {
    // Start from one valid connected generation two.
    const gate = createLifecycleGate({ now: () => 4500 });
    // Bind the prior successful native authority.
    gate.setConnected(true); gate.setActive(true); gate.validate(2);
    // Return the exact hostile probe result without network access.
    const plugin = fakePlugin({ generation: 2 });
    // Replace only the probe seam.
    plugin.probe = async () => result;
    // Bind the fake native bridge.
    const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
    // Reject the result instead of reopening controls.
    await assert.rejects(transport.revalidate(), /MOBILE_SESSION_(?:PROBE_INVALID|GENERATION_ROLLBACK)/);
    // Preserve the last current vault generation while keeping mutation authority closed.
    assert.equal(gate.generation(), 2);
    // Reject unsafe work until a later authoritative probe succeeds.
    assert.throws(() => gate.begin("POST"), /MOBILE_SESSION_REVALIDATION_REQUIRED/);
  }
});

// Verify direct and credential-transition generation rollback both fail closed.
test("rejects lower vault generations without replacing current authority", () => {
  // Create one validated current generation two.
  const gate = createLifecycleGate({ now: () => 4750 });
  // Bind connected native authority.
  gate.setConnected(true); gate.setActive(true); gate.validate(2);
  // Reject a direct lower-generation validation and retain generation two.
  assert.throws(() => gate.validate(1), /MOBILE_SESSION_GENERATION_ROLLBACK/);
  // Require the rollback attempt to close mutation authority.
  assert.equal(gate.generation(), 2); assert.equal(gate.isValidated(), false);
  // Revalidate current generation to create one fresh transition ticket.
  gate.validate(2); const ticket = gate.begin("POST");
  // Reject a lower-generation transition without replacing current vault identity.
  assert.throws(() => gate.transition(ticket, 1), /MOBILE_SESSION_GENERATION_ROLLBACK/);
  // Preserve generation two and close authority again.
  assert.equal(gate.generation(), 2); assert.equal(gate.isValidated(), false);
});

// Verify malformed successful issuance cannot reach shared JavaScript or leave controls open.
test("rejects successful issuance without a committed native vault transition", async () => {
  // Start from one cleared but validated native generation.
  const gate = createLifecycleGate({ now: () => 4900 });
  // Permit the public login mutation under cleared generation zero.
  gate.setConnected(true); gate.setActive(true); gate.validate(0);
  // Return a sanitized 200 without native credential-commit evidence.
  const plugin = fakePlugin({ status: 200, generation: 0 });
  // Bind the malformed fake native bridge.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
  // Reject before shared application code sees a false login success.
  await assert.rejects(transport.fetch("/api/v2/auth/login", { method: "POST", body: "{}" }), /MOBILE_SESSION_TRANSITION_INVALID/);
  // Leave protected mutations closed after the malformed issuance.
  assert.equal(gate.isValidated(), false);
});

// Verify expired mutations share one probe but never auto-send before shared reconciliation.
test("holds expired mutations after probe until a fresh explicit retry", async () => {
  // Use one mutable clock to expire otherwise current vault authority.
  let current = 5000;
  // Bind connected generation one under a short validation age.
  const gate = createLifecycleGate({ now: () => current, maxValidationAgeMs: 10 }); gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Count probes and native action descriptors independently.
  let probes = 0; let mutations = 0; let refreshSignals = 0;
  // Build one fake native bridge that accepts a delayed shared probe.
  const plugin = fakePlugin({ generation: 1 });
  // Count and delay the exact authoritative probe so both callers overlap.
  plugin.probe = async () => { probes += 1; await Promise.resolve(); return { authenticated: true, generation: 1, status: 200 }; };
  // Count each intended mutation without generating a session transition.
  plugin.request = async () => { mutations += 1; return { status: 200, generation: 1, headers: { "Content-Type": "application/json" }, body: '{"ok":true,"data":{"balance":1}}' }; };
  // Bind the fake bridge to one scoped transport and expire validation age.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin, onReconciliationRequired: () => { refreshSignals += 1; } }); current += 11;
  // Start two distinct intended actions while one recovery probe is pending.
  const held = await Promise.allSettled([transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }), transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" })]);
  // Require one shared probe, no action dispatch, and explicit refresh-required results.
  assert.equal(probes, 1); assert.equal(mutations, 0); assert.equal(refreshSignals, 2); assert.ok(held.every(result => result.status === "rejected" && result.reason?.code === "MOBILE_SESSION_REFRESH_REQUIRED"));
  // Model one successful shared session/wallet/game/route reconciliation under current authority.
  const reconciliation = gate.beginReconciliation(); gate.completeReconciliation(reconciliation);
  // Send one fresh explicit player retry after controls reopen.
  await transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }); assert.equal(mutations, 1);
  // Expire again and reject the recovery probe before any later mutation reaches native code.
  current += 11; plugin.probe = async () => { probes += 1; throw new Error("probe failed"); };
  // Preserve the original probe failure without action retry.
  await assert.rejects(transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }), /probe failed/);
  // Prove the failed recovery sent no additional mutation.
  assert.deepEqual([probes, mutations], [2, 1]);
});

// Verify a stale or deferred shared refresh cannot release mutation authority.
test("keeps mutations closed until current reconciliation completes", async () => {
  // Bind one active session and cross a network edge that requires probe plus shared refresh.
  const gate = createLifecycleGate({ now: () => 5150 }); gate.setConnected(true); gate.setActive(true); gate.validate(1); gate.setConnected(false); gate.setConnected(true);
  // Return one authenticated current-vault probe and count every native mutation.
  let mutations = 0; const plugin = fakePlugin({ generation: 1 }); plugin.probe = async () => ({ authenticated: true, generation: 1, status: 200 }); plugin.request = async () => { mutations += 1; return { status: 200, generation: 1, body: '{"ok":true,"data":{}}' }; };
  // Bind the pure native transport and establish probe-only read authority.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin }); await transport.revalidate();
  // Capture a shared refresh ticket but leave reconciliation pending.
  const pendingRefresh = gate.beginReconciliation();
  // Reject a racing player mutation before native I/O rather than queueing or retrying it.
  await assert.rejects(transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }), /MOBILE_SESSION_REFRESH_REQUIRED/); assert.equal(mutations, 0);
  // Complete current shared refresh and allow only a fresh explicit mutation once.
  gate.completeReconciliation(pendingRefresh); await transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }); assert.equal(mutations, 1);
  // Capture another refresh then cross background before it completes.
  gate.invalidate(); gate.completeProbe(gate.beginProbe(), 1, true); const staleRefresh = gate.beginReconciliation(); gate.setActive(false); gate.setActive(true);
  // Reject stale refresh completion and preserve the mutation hold.
  assert.throws(() => gate.completeReconciliation(staleRefresh), /MOBILE_STALE_COMPLETION/); await assert.rejects(transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }), /MOBILE_SESSION_REFRESH_REQUIRED/); assert.equal(mutations, 1);
});

// Verify an ordinary 401 clear cannot reopen unrelated mutations over a stale shell.
test("holds non-issuance mutations after an authoritative ordinary 401", async () => {
  // Bind one active reconciled account at vault generation one.
  const gate = createLifecycleGate({ now: () => 5175 }); gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Return one native 401 clear at generation two and count later mutation attempts.
  let requests = 0; let refreshSignals = 0; const plugin = fakePlugin({ generation: 2 }); plugin.request = async () => { requests += 1; return { status: 401, generation: 2, sessionChanged: true, headers: { "Content-Type": "application/json" }, body: '{"ok":false,"error":{"code":"UNAUTHORIZED","message":"Session required","details":{}}}' }; };
  // Capture the shared refresh ticket before its ordinary current-user read discovers revocation.
  const reconciliation = gate.beginReconciliation();
  // Bind the exact transport and perform the ordinary current-user read under that refresh.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin, onReconciliationRequired: () => { refreshSignals += 1; } }); const response = await transport.fetch("/api/v2/me");
  // Require the public 401 while retaining probe validation but closing general mutations.
  assert.equal(response.status, 401); assert.equal(gate.isValidated(), true); assert.equal(gate.isReconciled(), false); assert.equal(refreshSignals, 1);
  // Reject an unrelated mutation before native I/O until the login gate refresh completes.
  await assert.rejects(transport.fetch("/api/v2/me/tokens/add", { method: "POST", body: "{}" }), /MOBILE_SESSION_REFRESH_REQUIRED/); assert.equal(requests, 1);
  // Reconcile the rendered empty state through the original predecessor ticket with no hidden retry.
  gate.completeReconciliation(reconciliation); assert.equal(gate.isReconciled(), true); assert.equal(requests, 1);
});

// Verify lifecycle edges require a fresh probe before even a read can repaint shared state.
test("revalidates post-edge reads and rejects every completion from the prior epoch", async () => {
  // Bind one connected foreground process and retain an old read ticket.
  const gate = createLifecycleGate({ now: () => 5100 }); gate.setConnected(true); gate.setActive(true); gate.validate(1); const oldRead = gate.begin("GET");
  // Cross a network trust boundary without changing the vault generation.
  gate.setConnected(false); gate.setConnected(true);
  // Count the authoritative probe and the intended native read independently.
  let probes = 0; let reads = 0;
  // Build one fake plugin that returns the current session and one public current-user envelope.
  const plugin = fakePlugin({ generation: 1 }); plugin.probe = async () => { probes += 1; return { authenticated: true, generation: 1, status: 200 }; }; plugin.request = async () => { reads += 1; return { status: 200, generation: 1, headers: { "Content-Type": "application/json" }, body: '{"ok":true,"data":{"user":null}}' }; };
  // Bind the exact transport and perform the intended post-edge read.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin }); await transport.fetch("/api/v2/me");
  // Require one probe before one read and reject prior-epoch repaint authority.
  assert.deepEqual([probes, reads], [1, 1]); assert.throws(() => gate.complete(oldRead, 1), /MOBILE_STALE_COMPLETION/);
});

// Verify a lifecycle edge during body materialization stops before native I/O with no hidden retry.
test("rejects a lifecycle edge during request body read before native dispatch", async () => {
  // Bind one connected foreground process at vault generation one.
  const gate = createLifecycleGate({ now: () => 5200 }); gate.setConnected(true); gate.setActive(true); gate.validate(1);
  // Count every native request attempt.
  let mutations = 0;
  // Create one otherwise valid fake plugin.
  const plugin = fakePlugin({ generation: 1 }); plugin.request = async () => { mutations += 1; return { status: 200, generation: 1, body: '{"ok":true,"data":{}}' }; };
  // Create a caller Request whose body will cross the background boundary before resolving.
  const request = new Request(`${WEBVIEW}/api/v2/me/tokens/add`, { method: "POST", body: "{}" });
  // Retain the platform clone operation so the deterministic test seam is always restored.
  const originalClone = Request.prototype.clone;
  // Replace only clone body materialization during this exact request.
  Request.prototype.clone = function () { return { text: async () => { gate.setActive(false); return "{}"; } }; };
  // Bind the request to the scoped native transport.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
  // Reject before the plugin can observe the mutation descriptor.
  try { await assert.rejects(transport.fetch(request), /MOBILE_STALE_COMPLETION/); } finally { Request.prototype.clone = originalClone; }
  // Prove the intended mutation was never sent or retried.
  assert.equal(mutations, 0);
});

// Verify a terminal native session response advances process authority to the cleared vault generation.
test("terminal guest end binds the cleared vault generation", async () => {
  // Bind one active guest vault generation before terminal teardown.
  const gate = createLifecycleGate({ now: () => 3500 });
  // Admit the terminal mutation under generation five.
  gate.setConnected(true); gate.setActive(true); gate.validate(5);
  // Return the plugin's synthetic one-time clear acknowledgement at generation six.
  const plugin = fakePlugin({ generation: 6 });
  // Model native code clearing the bearer atomically with accepted guest end.
  plugin.request = async value => { plugin.calls.push(["request", value]); return { status: 200, generation: 6, sessionChanged: true, headers: { "Content-Type": "application/json" }, body: '{"ok":true,"data":{"ended":true}}' }; };
  // Bind the plugin to the scoped transport.
  const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin });
  // Complete the terminal route exactly once with no retry.
  await transport.fetch("/api/v2/auth/guest/end", { method: "POST", body: "{}" });
  // Require the process gate to advance onto the cleared vault authority.
  assert.equal(gate.generation(), 6);
});

// Verify every exact session-changing route advances lifecycle generation once and only once.
test("binds each successful session transition exactly once", async () => {
  // Exercise issuance, rotation, and terminal clear routes independently.
  for (const path of ["/api/v2/auth/login", "/api/v2/auth/guest", "/api/v2/auth/mobile/session/rotate", "/api/v2/auth/logout", "/api/v2/auth/guest/end", "/api/v2/auth/mobile/session/revoke"]) {
    // Bind one current process at vault generation one and retain a stale completion ticket.
    const gate = createLifecycleGate({ now: () => 5300 }); gate.setConnected(true); gate.setActive(true); gate.validate(1); const prior = gate.begin("GET");
    // Return one native-committed transition at generation two.
    const plugin = fakePlugin({ generation: 2 }); plugin.request = async value => { plugin.calls.push(["request", value]); return { status: 200, generation: 2, sessionChanged: true, headers: { "Content-Type": "application/json" }, body: '{"ok":true,"data":{}}' }; };
    // Bind and execute the exact session-changing request once.
    const transport = createMobileTransport({ backendOrigin: BACKEND, webViewOrigin: WEBVIEW, lifecycle: gate, nativePlugin: plugin }); await transport.fetch(path, { method: "POST", body: "{}" });
    // Require one bridge call, one generation advance, and rejection of prior-generation completion.
    assert.equal(plugin.calls.filter(row => row[0] === "request").length, 1); assert.equal(gate.generation(), 2); assert.throws(() => gate.complete(prior, 2), /MOBILE_STALE_COMPLETION/);
  }
});
