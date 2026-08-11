// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for transient account-link rerender handling.
import assert from "node:assert/strict";
// Import filesystem access for exact warm-route controller wiring evidence.
import { readFile } from "node:fs/promises";
// Import the deterministic built-in test runner.
import test from "node:test";

// Provide the browser namespace required by the shared localization module before dynamic import.
globalThis.window = globalThis;
// Import the shared module-held bearer selection helper after the browser-compatible seam exists.
const { holdTransientBearer, publicAuthRouteKind } = await import("../../web/core/api.js");
// Import the exact shared navigation owner and mount boundary used by the application shell.
const { createNavigationOwnership, mountOwnedRoute, awaitOwnedRouteEffect } = await import("../../web/core/ui.js");

// Build one externally resolved promise so navigation ownership can change at exact async boundaries.
function deferred() {
  // Retain the resolver for the deterministic test driver.
  let resolve;
  // Retain the rejecter so stale failure behavior can use the same fixture.
  let reject;
  // Construct the pending promise before returning its controls.
  const promise = new Promise((accept, decline) => { resolve = accept; reject = decline; });
  // Return the exact promise and its one-shot completion controls.
  return { promise, resolve, reject };
}

// Prove browser and native arrivals survive rerender without returning to URL or persistent storage.
test("password reset bearer survives browser and native rerenders", () => {
  // Capture one synthetic browser-query arrival in module memory.
  let browserBearer = holdTransientBearer("", "browser-purpose-bearer");
  // Preserve it when a locale rerender sees the already-scrubbed browser URL.
  browserBearer = holdTransientBearer(browserBearer, "");
  // Require exact in-memory continuity.
  assert.equal(browserBearer, "browser-purpose-bearer");
  // Capture one synthetic native one-shot arrival in the same shared controller.
  let nativeBearer = holdTransientBearer("", "native-purpose-bearer");
  // Preserve it after the native runtime's one-shot reader is empty on rerender.
  nativeBearer = holdTransientBearer(nativeBearer, "");
  // Require exact in-memory continuity without a second native claim.
  assert.equal(nativeBearer, "native-purpose-bearer");
  // Model terminal success clearing the module-owned value.
  nativeBearer = "";
  // Require no residual bearer after terminal completion.
  assert.equal(nativeBearer, "");
});

// Prove warm native account links select the existing public gates before authenticated navigation.
test("warm native account links mount one-shot public auth routes", async () => {
  // Require exact public route classification for invitation, verification, and recovery.
  assert.deepEqual([publicAuthRouteKind("/enroll/invitation"), publicAuthRouteKind("/enroll/verify"), publicAuthRouteKind("/account/reset")], ["invitation", "verification", "reset"]);
  // Reject a game route from the public auth selector.
  assert.equal(publicAuthRouteKind("/games/roulette"), "");
  // Read the shared controller to prove popstate checks the public gate before session navigation.
  const source = await readFile(new URL("../../web/app.js", import.meta.url), "utf8");
  // Require the warm-link event to route through the centralized public renderer first.
  assert.match(source, /addEventListener\('popstate',[^\n]+renderPublicAuthRoute\(\)/);
  // Isolate the public router so authenticated game lifecycle teardown cannot be satisfied elsewhere.
  const publicRouter = source.slice(source.indexOf("function renderPublicAuthRoute"), source.indexOf("function transientRouteBearer"));
  // Require active session, route, state, or descriptors to trigger the centralized unmount boundary once.
  assert.match(publicRouter, /shellNavigationOwnership\.invalidate\(\)[\s\S]+if \(currentSession \|\| active \|\| latestState \|\| gameDescriptors\.length\) clearAuthenticatedShellState\(\{ invalidateNavigation: false \}\)/);
  // Require all three one-shot native destinations to retain their module-held bearer readers.
  assert.ok(["/enroll/invitation", "/enroll/verify", "/account/reset"].every(path => source.includes(`transientRouteBearer('${path}')`)));
  // Isolate the invitation renderer so its warm-route state reset cannot be satisfied by another gate.
  const invitation = source.slice(source.indexOf("function renderInvitationGate"), source.indexOf("async function handleInvitationSubmit"));
  // Require the invitation gate to clear both authenticated session and feedback ownership.
  assert.match(invitation, /currentSession = null; window\.CasinoCurrentUser = null;[\s\S]+syncFeedbackReporter\(null\)/);
  // Isolate reconnect handling so a retained vault session cannot overwrite the warm public gate.
  const reconnect = source.slice(source.indexOf("async function refreshAfterReconnect"), source.indexOf("export async function navigate"));
  // Require public auth ownership to return before current-user refresh.
  assert.match(reconnect, /if \(renderPublicAuthRoute\(\)\) return \{ status: 'public-auth-route' \};[\s\S]+refreshCurrentSession\(\)/);
  // Isolate current-user refresh to prove cold public links and non-auth failures stay fail closed.
  const refresh = source.slice(source.indexOf("async function refreshCurrentSession"), source.indexOf("async function loadGame"));
  // Require a cold public gate before currentUser and restrict stale-shell clearing to exact unauthorized.
  assert.match(refresh, /if \(renderPublicAuthRoute\(\)\) return false;[\s\S]+currentUser\(\)[\s\S]+if \(err\?\.code !== 'UNAUTHORIZED'\) throw err;/);
  // Read the API client so compound native account-switch serialization is source-bound.
  const apiSource = await readFile(new URL("../../web/core/api.js", import.meta.url), "utf8");
  // Require one mutex to cover predecessor preparation through replacement issuance.
  assert.match(apiSource, /if \(nativeAccountSwitchInFlight\)[\s\S]+await globalThis\.CasinoMobileTransport\.prepareAccountSwitch\(\);[\s\S]+return await action\(\)/);
  // Require both registered login and guest creation to use the same exclusive transaction.
  assert.equal((apiSource.match(/runNativeAccountSwitch\(\(\) => post\('\/api\/v2\/auth\/(?:login|guest)'/g) || []).length, 2);
});

// Prove warm public-route ownership prevents deferred game import, mount, and failure repaint. (SESSION-013)
test("warm public route invalidates deferred game navigation", async () => {
  // Create the same monotonic ownership controller used by the shell.
  const ownership = createNavigationOwnership();
  // Capture observable mount and stale-cleanup effects without a browser DOM.
  const effects = { mounts: 0, unmounts: 0, publicRenders: 0 };
  // Build a game whose mount can be paused after it starts.
  const mountBoundary = deferred();
  // Model the exact game lifecycle hooks consumed by mountOwnedRoute.
  const game = { mount: async () => { effects.mounts += 1; await mountBoundary.promise; }, unmount: () => { effects.unmounts += 1; } };
  // Claim the game route before its asynchronous import begins.
  const importTicket = ownership.claim();
  // Pause the dynamic import at a deterministic boundary.
  const importBoundary = deferred();
  // Start the same owned load/mount pipeline used by navigate().
  const importNavigation = mountOwnedRoute({ load: () => importBoundary.promise, mount: loaded => loaded.mount(), owns: () => ownership.owns(importTicket), onStale: (loaded, mountStarted) => { if (mountStarted) loaded?.unmount?.(); effects.publicRenders += 1; } });
  // Model the warm public reset or invitation transition before import completion.
  ownership.invalidate();
  // Finish the stale import with the game module.
  importBoundary.resolve(game);
  // Require the stale import to stop before mount and restore the public gate once.
  assert.deepEqual(await importNavigation, { game, mounted: false, stale: true });
  // Prove no stale game mount ran after the public transition.
  assert.equal(effects.mounts, 0);
  // Claim a later game navigation so the post-mount boundary is exercised independently.
  const mountTicket = ownership.claim();
  // Start loading and mounting immediately, then pause inside the mount implementation.
  const mountNavigation = mountOwnedRoute({ load: async () => game, mount: loaded => loaded.mount(), owns: () => ownership.owns(mountTicket), onStale: (loaded, mountStarted) => { if (mountStarted) loaded?.unmount?.(); effects.publicRenders += 1; } });
  // Yield once so the mount reaches its deferred boundary.
  await Promise.resolve();
  // Model a second warm public link while game mount work is still running.
  ownership.invalidate();
  // Allow the stale mount to finish after the public gate already owns the screen.
  mountBoundary.resolve();
  // Require exact stale classification after the mount boundary.
  assert.deepEqual(await mountNavigation, { game, mounted: false, stale: true });
  // Prove the stale mounted game was unmounted and the public gate restored for both stale boundaries.
  assert.deepEqual(effects, { mounts: 1, unmounts: 1, publicRenders: 2 });
  // Claim one final navigation and pause its loader before rejection.
  const errorTicket = ownership.claim();
  // Build a deferred stale loader failure to model a rejected dynamic import.
  const errorBoundary = deferred();
  // Start the owned pipeline without awaiting so the public route can take ownership first.
  const errorNavigation = mountOwnedRoute({ load: () => errorBoundary.promise, mount: async () => {}, owns: () => ownership.owns(errorTicket), onStale: () => { effects.publicRenders += 1; } });
  // Invalidate the failing route before its import rejection arrives.
  ownership.invalidate();
  // Reject with a diagnostic that must never escape to the shell error painter.
  errorBoundary.reject(new Error("stale import must not repaint"));
  // Require stale failure suppression rather than a rejected navigation promise.
  assert.deepEqual(await errorNavigation, { game: null, mounted: false, stale: true });
  // Verify the public gate remained the final rendered owner after the stale failure.
  assert.equal(effects.publicRenders, 3);
  // Read the application source so the tested helper is proven at every navigate async and catch boundary.
  const source = await readFile(new URL("../../web/app.js", import.meta.url), "utf8");
  // Isolate navigate from initialization so unrelated ownership checks cannot satisfy the regression.
  const navigateSource = source.slice(source.indexOf("export async function navigate"), source.indexOf("// Initialize shell state"));
  // Require a claimed ticket, owned mount helper, settings post-await check, and owned diagnostic boundary.
  assert.match(navigateSource, /const navigationTicket = shellNavigationOwnership\.claim\(\)[\s\S]+await renderMySettings\(view\)[\s\S]+shellNavigationOwnership\.owns\(navigationTicket\)[\s\S]+await mountOwnedRoute\([\s\S]+if \(mountedRoute\.stale\) return;[\s\S]+catch \(err\)[\s\S]+shellNavigationOwnership\.owns\(navigationTicket\)[\s\S]+await awaitOwnedRouteEffect\([\s\S]+if \(!ownsAfterLog\) return;/);
  // Claim an error route before its asynchronous diagnostic begins.
  const diagnosticTicket = ownership.claim();
  // Pause the diagnostic at the exact await that formerly permitted stale error repaint.
  const diagnosticBoundary = deferred();
  // Start the production-owned diagnostic helper and expose one public-route restore counter.
  const diagnostic = awaitOwnedRouteEffect({ run: () => diagnosticBoundary.promise, owns: () => ownership.owns(diagnosticTicket), onStale: () => { effects.publicRenders += 1; } });
  // Model a warm reset or invitation while the diagnostic request is in flight.
  ownership.invalidate();
  // Complete the stale diagnostic after the public gate owns the outlet.
  diagnosticBoundary.resolve();
  // Require the stale continuation to be rejected rather than authorizing an error repaint.
  assert.equal(await diagnostic, false);
  // Prove the public gate was restored once at the post-log ownership boundary.
  assert.equal(effects.publicRenders, 4);
});
