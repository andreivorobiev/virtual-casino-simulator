// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Define methods that can mutate server-authoritative state.
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
// Name exact credential fields that must never cross from native code into shared JavaScript.
const FORBIDDEN_RESPONSE_FIELDS = new Set(["token", "csrf_token", "guest_browser_nonce"]);

// Build one low-cardinality secret-free failure.
function mobileError(code) {
  // Create the error with no endpoint, account, token, or provider content.
  const error = new Error(code);
  // Publish the stable machine code used by deterministic tests and UI mapping.
  error.code = code;
  // Return the bounded failure object.
  return error;
}

// Create a generation-bound lifecycle authority for process, foreground, and connectivity changes.
export function createLifecycleGate({ now = () => Date.now(), maxValidationAgeMs = 300000 } = {}) {
  // Start disconnected until the native Network plugin provides exact state.
  let connected = false;
  // Start inactive until the native App plugin proves exact foreground state.
  let active = false;
  // Start one monotonic process epoch that never derives from server or vault numbering.
  let epoch = 0;
  // Track the OS-vault credential generation independently from lifecycle invalidation.
  let currentVaultGeneration = 0;
  // Track the most recent authoritative probe without storing any credential.
  let validatedAt = 0;
  // Keep mutations closed until shared session, wallet, game, and route state reconciles after an edge.
  let reconciled = false;
  // Retain exact empty-vault proof so only login or guest issuance can precede shared reconciliation.
  let emptyVaultProven = false;
  // Retain one exact credential transition so surrounding shared refresh can finish under its successor.
  let lastCredentialTransition = null;
  // Track clock movement so rollback invalidates process authority.
  let observedAt = now();

  // Invalidate the current process epoch after every trust-boundary change.
  function invalidate() {
    // Advance the epoch so every earlier in-flight completion stays stale after revalidation.
    epoch += 1;
    // Remove the validation timestamp without touching the native vault.
    validatedAt = 0;
    // Close mutation authority until an exact shared-state reconciliation succeeds.
    reconciled = false;
    // Discard transition lineage because a generic trust edge supersedes it.
    lastCredentialTransition = null;
  }

  // Observe clock rollback and bounded expiry before returning current time.
  function observeClock() {
    // Read the injectable clock exactly once.
    const current = now();
    // Invalidate on rollback or expiry because device time is not authoritative.
    if (current < observedAt || (validatedAt > 0 && current - validatedAt > maxValidationAgeMs)) invalidate();
    // Retain the latest observation for the next comparison.
    observedAt = current;
    // Return the value for validation stamping.
    return current;
  }

  // Store native connectivity and invalidate trust on either edge.
  function setConnected(value) {
    // Normalize the plugin value to one boolean.
    const next = value === true;
    // Invalidate all in-flight work when connectivity changes.
    if (next !== connected) invalidate();
    // Retain the new state after invalidation.
    connected = next;
  }

  // Store native foreground state and invalidate trust on either edge.
  function setActive(value) {
    // Normalize the native lifecycle value.
    const next = value === true;
    // Invalidate all in-flight work when application activity changes.
    if (next !== active) invalidate();
    // Retain the new state after invalidation.
    active = next;
  }

  // Record one exact server probe and its native vault generation.
  function validate(vaultGeneration) {
    // Require a positive integer generation supplied by native secure storage.
    if (!Number.isSafeInteger(vaultGeneration) || vaultGeneration < 0) throw mobileError("MOBILE_SESSION_GENERATION_INVALID");
    // Reject native rollback and close prior authority without replacing the current vault generation.
    if (vaultGeneration < currentVaultGeneration) { invalidate(); throw mobileError("MOBILE_SESSION_GENERATION_ROLLBACK"); }
    // Snapshot the epoch so clock invalidation cannot be overwritten by this direct validation.
    const expectedEpoch = epoch;
    // Observe clock rollback before accepting the new authority.
    const validationTime = observeClock();
    // Reject when observing the clock invalidated the process trust boundary.
    if (epoch !== expectedEpoch) throw mobileError("MOBILE_STALE_COMPLETION");
    // Advance the process epoch when the native vault commits a different credential generation.
    if (vaultGeneration !== currentVaultGeneration) epoch += 1;
    // Retain the native vault generation without overwriting the monotonic process epoch.
    currentVaultGeneration = vaultGeneration;
    // Stamp validation only after both lifecycle and vault authority are current.
    validatedAt = validationTime;
    // Treat direct validation as an explicit fully reconciled test or trusted composition boundary.
    reconciled = true;
    // Direct trusted binding has no in-flight predecessor transition to preserve.
    lastCredentialTransition = null;
  }

  // Capture a request ticket before one authoritative action starts.
  function begin(method, { allowEmptyVaultIssuance = false } = {}) {
    // Apply clock and expiry policy before reading flags.
    const startedAt = observeClock();
    // Reject every new request while backgrounded.
    if (!active) throw mobileError("MOBILE_APP_BACKGROUND");
    // Reject every new request while native connectivity is absent.
    if (!connected) throw mobileError("MOBILE_NETWORK_UNAVAILABLE");
    // Reject every scoped API read or mutation until a current-session probe validates this generation.
    if (validatedAt === 0) throw mobileError("MOBILE_SESSION_REVALIDATION_REQUIRED");
    // Reject mutations after an authenticated probe until shared authoritative state finishes refreshing.
    if (UNSAFE_METHODS.has(method) && !reconciled && !(allowEmptyVaultIssuance && emptyVaultProven)) throw mobileError("MOBILE_SESSION_REFRESH_REQUIRED");
    // Return both independent authorities for stale-completion rejection.
    return Object.freeze({ epoch, vaultGeneration: currentVaultGeneration, observedAt: startedAt });
  }

  // Reject a completion from an earlier account, session, foreground, or network generation.
  function complete(ticket, responseGeneration) {
    // Observe clock rollback or expiry before comparing request authority.
    const completionTime = observeClock();
    // Require the process epoch and both vault generations to match the request start.
    if (!ticket || ticket.epoch !== epoch || ticket.vaultGeneration !== currentVaultGeneration || responseGeneration !== currentVaultGeneration || completionTime < ticket.observedAt || completionTime - ticket.observedAt > maxValidationAgeMs) throw mobileError("MOBILE_STALE_COMPLETION");
  }

  // Bind one intentional native credential transition only if its request ticket stayed current.
  function transition(ticket, responseGeneration, markReconciled = true, markEmptyVault = false) {
    // Require one valid OS-vault generation before considering the completion.
    if (!Number.isSafeInteger(responseGeneration) || responseGeneration < 0) throw mobileError("MOBILE_SESSION_GENERATION_INVALID");
    // Reject native rollback and close prior authority without replacing the current vault generation.
    if (responseGeneration < currentVaultGeneration) { invalidate(); throw mobileError("MOBILE_SESSION_GENERATION_ROLLBACK"); }
    // Retain predecessor authority so a surrounding shared refresh can bind an exact 401 successor.
    const predecessorEpoch = epoch;
    // Retain predecessor vault generation independently from the response generation.
    const predecessorVaultGeneration = currentVaultGeneration;
    // Observe clock rollback or expiry before comparing the request epoch.
    const validationTime = observeClock();
    // Reject lifecycle, account, or credential drift that happened while native work was in flight.
    if (!ticket || ticket.epoch !== epoch || ticket.vaultGeneration !== currentVaultGeneration || validationTime < ticket.observedAt || validationTime - ticket.observedAt > maxValidationAgeMs) throw mobileError("MOBILE_STALE_COMPLETION");
    // Advance the process epoch when native code committed a different vault credential record.
    if (responseGeneration !== currentVaultGeneration) epoch += 1;
    // Bind the newly committed native vault generation without trusting server generation numbering.
    currentVaultGeneration = responseGeneration;
    // Mark the intentional transition as the current authoritative validation.
    validatedAt = validationTime;
    // Reconcile exact issuance/terminal transitions or preserve the probe-only mutation hold.
    reconciled = markReconciled === true;
    // Retain only exact native proof that no predecessor credential remains usable.
    emptyVaultProven = markEmptyVault === true;
    // Preserve exact transition lineage until reconciliation succeeds or another trust edge invalidates it.
    lastCredentialTransition = Object.freeze({ predecessorEpoch, predecessorVaultGeneration, successorEpoch: epoch, successorVaultGeneration: currentVaultGeneration });
  }

  // Assert one request ticket remains current immediately before native network dispatch.
  function assertCurrent(ticket) {
    // Reuse complete authority checks against the ticket's unchanged vault generation.
    complete(ticket, ticket?.vaultGeneration);
  }

  // Snapshot process, vault, and clock authority before an OS-vault session probe starts.
  function beginProbe() {
    // Close existing authority before every probe so a failure can never leave mutations enabled.
    invalidate();
    // Observe clock state without requiring the validation this probe exists to establish.
    const startedAt = observeClock();
    // Reject a probe while backgrounded so process restore begins fail closed.
    if (!active) throw mobileError("MOBILE_APP_BACKGROUND");
    // Reject a probe while native connectivity is absent.
    if (!connected) throw mobileError("MOBILE_NETWORK_UNAVAILABLE");
    // Return the unvalidated probe ticket under current process and vault authority.
    return Object.freeze({ epoch, vaultGeneration: currentVaultGeneration, observedAt: startedAt });
  }

  // Bind a probe result only when no lifecycle, credential, or clock edge occurred in flight.
  function completeProbe(ticket, responseGeneration, authenticated) {
    // Keep every probe mutation-held until shared state refresh, including exact empty-vault 401 state.
    transition(ticket, responseGeneration, false, authenticated !== true);
  }

  // Capture one ticket for the shared authoritative state refresh after a successful probe.
  function beginReconciliation() {
    // Reuse validated read authority because refresh itself may call current-user and state endpoints.
    return begin("GET");
  }

  // Release mutations only when refresh completed under the same process and vault authority.
  function completeReconciliation(ticket) {
    // Accept an exact session transition that already established newer authoritative empty/issued state.
    if (reconciled) return true;
    // Attempt unchanged-ticket completion before considering an exact credential successor.
    try { complete(ticket, currentVaultGeneration); }
    // Accept only the sole credential transition descended from this refresh ticket.
    catch (error) {
      // Reject network, lifecycle, clock, or unrelated credential edges crossed by refresh.
      if (error?.code !== "MOBILE_STALE_COMPLETION" || !lastCredentialTransition || lastCredentialTransition.predecessorEpoch !== ticket?.epoch || lastCredentialTransition.predecessorVaultGeneration !== ticket?.vaultGeneration || lastCredentialTransition.successorEpoch !== epoch || lastCredentialTransition.successorVaultGeneration !== currentVaultGeneration) throw error;
    }
    // Release mutations only after the shared session, wallet, game, and route refresh is current.
    reconciled = true;
    // Consume transition lineage so a later unrelated refresh cannot reuse it.
    lastCredentialTransition = null;
    // Return bounded completion evidence without exposing session state.
    return true;
  }

  // Expose only lifecycle operations and non-secret generation evidence.
  return Object.freeze({ setConnected, setActive, validate, invalidate, begin, assertCurrent, complete, transition, beginProbe, completeProbe, beginReconciliation, completeReconciliation, generation: () => currentVaultGeneration, isValidated: () => validatedAt > 0, isReconciled: () => reconciled });
}

// Coordinate fail-closed cold-start and reconnect recovery without loading shared code twice.
export function createMobileRecoveryCoordinator({ revalidate, load, reconnect }) {
  // Require each injected operation so recovery cannot silently skip an authority boundary.
  if (![revalidate, load, reconnect].every(operation => typeof operation === "function")) throw mobileError("MOBILE_RECOVERY_OPERATION_REQUIRED");
  // Start offline until the native Network plugin publishes its first exact state.
  let connected = false;
  // Start inactive until the native App plugin binds exact initial foreground state.
  let active = false;
  // Advance one coordinator epoch for every availability edge during asynchronous recovery.
  let availabilityEpoch = 0;
  // Track whether the shared application entry point has been appended successfully.
  let loaded = false;
  // Serialize overlapping bootstrap, foreground, and reconnect recovery attempts.
  let inFlight = null;

  // Retain the latest native network state without performing hidden work.
  function setConnected(value) {
    // Normalize the plugin result to the sole accepted connected value.
    const next = value === true;
    // Invalidate every in-flight recovery when native connectivity changes.
    if (next !== connected) availabilityEpoch += 1;
    // Retain the normalized state after advancing the recovery epoch.
    connected = next;
  }

  // Retain native foreground authority and invalidate recovery across either lifecycle edge.
  function setActive(value) {
    // Normalize the plugin result to the sole accepted foreground value.
    const next = value === true;
    // Invalidate every in-flight recovery when background or foreground state changes.
    if (next !== active) availabilityEpoch += 1;
    // Retain the normalized state after advancing the recovery epoch.
    active = next;
  }

  // Recover authority and either load once or refresh an already loaded application.
  async function recover() {
    // Keep the signed shared application absent while native networking is unavailable.
    if (!connected || !active) return false;
    // Share one pending recovery so simultaneous native events cannot duplicate probes or loads.
    if (inFlight) return inFlight;
    // Freeze this exact recovery attempt before any asynchronous boundary runs.
    const attemptEpoch = availabilityEpoch;
    // Reject a recovery result crossed by network or application lifecycle state.
    const requireCurrentAvailability = () => { if (!connected || !active || availabilityEpoch !== attemptEpoch) throw mobileError("MOBILE_RECOVERY_STALE"); };
    // Freeze this exact recovery promise before any asynchronous boundary runs.
    const pending = (async () => {
      // Revalidate OS-vault and server authority before releasing shared application code.
      await revalidate();
      // Reject an offline or background edge that landed while the probe was in flight.
      requireCurrentAvailability();
      // Load the application entry point only after the first successful authority probe.
      if (!loaded) {
        // Complete the injected load before recording the exact-once state.
        await load();
        // Prevent every later recovery event from appending a second entry point.
        loaded = true;
        // Reject an availability edge that landed during the load boundary.
        requireCurrentAvailability();
      } else {
        // Refresh session, wallet, game, and route state after later reconnect or foreground events.
        await reconnect();
        // Reject an availability edge that landed while authoritative refresh was in flight.
        requireCurrentAvailability();
      }
      // Return a bounded recovery result without exposing session state.
      return true;
    })();
    // Publish the attempt before yielding so concurrent callers receive the same promise.
    inFlight = pending;
    // Await the shared attempt while preserving failures for the caller's safe status UI.
    try { return await pending; }
    // Clear only this completed attempt so a later native event can recover from a transient failure.
    finally { if (inFlight === pending) inFlight = null; }
  }

  // Expose only network state, serialized recovery, and non-secret load evidence.
  return Object.freeze({ setConnected, setActive, recover, isLoaded: () => loaded });
}

// Bind one native initial snapshot without overwriting a newer listener event.
export function createLatestNativeObservation(apply) {
  // Require one injected state sink before native listener registration begins.
  if (typeof apply !== "function") throw mobileError("MOBILE_NATIVE_OBSERVER_REQUIRED");
  // Advance for every listener event so older snapshots cannot overwrite it.
  let eventEpoch = 0;
  // Track whether either an exact event or accepted snapshot has initialized authority.
  let bound = false;
  // Serialize every asynchronous state sink so native events retain arrival order.
  let applicationQueue = Promise.resolve();
  // Retain the newest event application so a stale startup snapshot can await its authority.
  let latestEventApplication = null;

  // Capture the event epoch immediately before one asynchronous native snapshot starts.
  function beginSnapshot() {
    // Return a scalar ticket that contains no device or session content.
    return eventEpoch;
  }

  // Apply one listener event as the newest native source of truth.
  async function event(value) {
    // Supersede every in-flight snapshot before applying the event.
    eventEpoch += 1;
    // Close prior bound evidence synchronously until the newest event sink succeeds.
    bound = false;
    // Capture this event epoch so a later event can prevent stale binding after an await.
    const ownEpoch = eventEpoch;
    // Recover queue ordering after a prior sink failure without hiding that prior caller's error.
    const prior = applicationQueue.catch(() => undefined);
    // Queue this event after every earlier accepted application reaches a terminal result.
    const pending = prior.then(async () => {
      // Apply exact native state through the caller-owned lifecycle boundary.
      await apply(value, "event");
      // Mark authority bound only when this successfully applied event remains newest.
      if (ownEpoch === eventEpoch) bound = true;
      // Return bounded completion evidence to listener diagnostics.
      return true;
    });
    // Publish the queue tail before yielding so concurrent events serialize behind it.
    applicationQueue = pending;
    // Publish the newest event application for listener-first bootstrap synchronization.
    latestEventApplication = pending;
    // Propagate this exact state-sink result to the event caller.
    return pending;
  }

  // Apply a snapshot only when no listener event arrived after it began.
  async function completeSnapshot(ticket, value) {
    // Recover queue ordering after a prior sink failure without hiding that prior caller's error.
    const prior = applicationQueue.catch(() => undefined);
    // Queue the snapshot behind every event that arrived before this completion boundary.
    const pending = prior.then(async () => {
      // Preserve a newer event rather than overwriting it with stale snapshot state.
      if (ticket !== eventEpoch) return false;
      // Apply the still-current snapshot through the same state sink.
      await apply(value, "snapshot");
      // Reject binding if an event arrived while the asynchronous snapshot sink was applying.
      if (ticket !== eventEpoch) return false;
      // Mark initial authority bound only after the current state sink completes.
      bound = true;
      // Report accepted snapshot state without exposing its value.
      return true;
    });
    // Publish the queue tail before awaiting so a new event serializes after this snapshot sink.
    applicationQueue = pending;
    // Return the exact current-or-stale classification to the snapshot owner.
    return pending;
  }

  // Await whichever listener event superseded a startup snapshot before releasing bootstrap.
  async function whenBound() {
    // Keep following the newest event when another arrival supersedes one still applying.
    while (!bound && latestEventApplication) {
      // Capture the newest promise so a later event can be detected after this await.
      const pending = latestEventApplication;
      // Propagate an event sink failure rather than guessing native authority.
      await pending;
      // Stop only when no later event replaced the promise and this event bound authority.
      if (latestEventApplication === pending && bound) return true;
    }
    // Reject initialization when neither an accepted snapshot nor event bound authority.
    if (!bound) throw mobileError("MOBILE_NATIVE_OBSERVER_UNBOUND");
    // Return bounded initialization evidence without exposing native state.
    return true;
  }

  // Expose only race-safe observation operations and bounded initialization evidence.
  return Object.freeze({ beginSnapshot, event, completeSnapshot, whenBound, isBound: () => bound });
}

// Derive the exact reviewed WebView authority without relying on custom-scheme URL.origin.
export function exactWebViewAuthority(rawUrl) {
  // Parse the complete runtime location so credentials, ports, and malformed values fail closed.
  const value = new URL(String(rawUrl));
  // Accept only the two platform-owned schemes and exact localhost authority.
  if (!new Set(["capacitor:", "https:"]).has(value.protocol) || value.hostname !== "localhost" || value.username || value.password || value.port) throw mobileError("MOBILE_WEBVIEW_ORIGIN_INVALID");
  // Return the reviewed scheme and hostname while deliberately excluding route state.
  return `${value.protocol}//${value.hostname}`;
}

// Authorize one cold or warm deep-link claim without letting old game work survive navigation.
export async function authorizeDeepLinkArrival({ warm, lifecycle, revalidate, claim, activate, fingerprint }) {
  // Require exact injected authority operations and one digest-only replay identifier.
  if (!lifecycle || typeof lifecycle.invalidate !== "function" || typeof revalidate !== "function" || typeof claim !== "function" || typeof activate !== "function" || !/^[a-f0-9]{64}$/.test(String(fingerprint))) throw mobileError("MOBILE_DEEP_LINK_AUTHORITY_INVALID");
  // Cross a process trust boundary only when shared game code can already own in-flight tickets.
  if (warm === true) {
    // Invalidate old game and wallet completions before asynchronous native work begins.
    lifecycle.invalidate();
    // Revalidate the current vault/session under a fresh ticket before enabling public mutations.
    await revalidate();
  }
  // Claim replay state only after warm-session revalidation succeeds so a failed link stays reopenable.
  await claim(fingerprint);
  // Capture one post-probe shared/public-route reconciliation ticket for a warm process.
  const reconciliation = warm === true ? lifecycle.beginReconciliation() : null;
  // Mount the token-free public route and tear down any authenticated shell exactly once.
  await activate();
  // Release public auth mutations only when warm route activation stayed under current authority.
  if (reconciliation) lifecycle.completeReconciliation(reconciliation);
  // Return a bounded acknowledgement without exposing route or bearer state.
  return true;
}

// Convert one headers collection into a plain allowlisted transport object.
function publicHeaders(headers) {
  // Create a null-prototype object that cannot inherit surprising keys.
  const output = Object.create(null);
  // Copy caller headers except credentials and native-owned integrity material.
  for (const [name, value] of headers.entries()) {
    // Normalize once for secret-boundary comparisons.
    const lower = name.toLowerCase();
    // Reject cookie, bearer, and CSRF fields because only the OS vault may supply them.
    if (["cookie", "authorization", "x-csrf-token", "x-guest-browser-nonce"].includes(lower)) throw mobileError("MOBILE_JAVASCRIPT_CREDENTIAL_FORBIDDEN");
    // Retain only bounded public headers.
    output[name] = value;
  }
  // Return the secret-free descriptor.
  return output;
}

// Reject any native response that still contains credential material after OS-vault capture.
function assertSecretFreeEnvelope(body) {
  // Leave empty and non-JSON bodies to the ordinary response consumer.
  if (!body) return;
  // Parse JSON only for secret-boundary inspection without changing the returned bytes.
  let value;
  // Keep non-JSON server failures compatible with ordinary error handling.
  try { value = JSON.parse(body); } catch (_) { return; }
  // Bound recursive work so an untrusted oversized structure cannot consume the WebView.
  let visited = 0;
  // Inspect each key while ignoring scalar values and never retaining their content.
  const inspect = (current, depth = 0) => {
    // Reject an unreasonable response tree before continuing into it.
    if (depth > 16 || (visited += 1) > 10000) throw mobileError("MOBILE_RESPONSE_SHAPE_INVALID");
    // Stop on scalar values that cannot name a credential field.
    if (!current || typeof current !== "object") return;
    // Inspect arrays by value without treating their numeric positions as field names.
    if (Array.isArray(current)) { current.forEach(child => inspect(child, depth + 1)); return; }
    // Reject every exact forbidden field and recursively inspect remaining values.
    for (const [name, child] of Object.entries(current)) {
      // Fail closed before shared JavaScript receives a native vault credential.
      if (FORBIDDEN_RESPONSE_FIELDS.has(name)) throw mobileError("MOBILE_NATIVE_SECRET_LEAK");
      // Continue through the bounded public envelope.
      inspect(child, depth + 1);
    }
  };
  // Inspect the complete decoded response exactly once.
  inspect(value);
}

// Create one scoped native transport without mutating global fetch or exposing vault credentials.
export function createMobileTransport({ backendOrigin, webViewOrigin, lifecycle, nativePlugin, onReconciliationRequired = () => undefined }) {
  // Require an injected native bridge so this pure module remains independently testable and credential-free.
  if (!nativePlugin || typeof nativePlugin.request !== "function") throw mobileError("MOBILE_NATIVE_PLUGIN_REQUIRED");
  // Require one bounded reconciliation callback rather than silently swallowing refresh authority.
  if (typeof onReconciliationRequired !== "function") throw mobileError("MOBILE_RECONCILIATION_CALLBACK_INVALID");
  // Normalize the HTTPS backend authority used only for native plugin configuration.
  const backend = new URL(backendOrigin);
  // Parse the current Capacitor WebView origin for exact configuration matching.
  const webView = new URL(webViewOrigin);
  // Preserve the exact custom-scheme authority because WHATWG serializes its origin as `null`.
  const normalizedWebViewOrigin = `${webView.protocol}//${webView.hostname}`;
  // Reject any backend that is not one credential-free HTTPS origin.
  if (backend.protocol !== "https:" || backend.username || backend.password || backend.pathname !== "/" || backend.search || backend.hash) throw mobileError("MOBILE_BACKEND_ORIGIN_INVALID");
  // Accept only the two platform-owned Capacitor origin shapes and exact localhost authority.
  if (!new Set(["capacitor:", "https:"]).has(webView.protocol) || webView.hostname !== "localhost" || webView.username || webView.password || webView.port || !["", "/"].includes(webView.pathname) || webView.search || webView.hash) throw mobileError("MOBILE_WEBVIEW_ORIGIN_INVALID");
  // Retain only one in-flight authoritative probe so expired concurrent mutations recover together.
  let revalidationInFlight = null;

  // Configure the native vault/network boundary once without any secret-bearing field.
  async function configure() {
    // Bind backend and WebView origins inside native storage before any API request.
    await nativePlugin.configure({ backendOrigin: backend.origin, webViewOrigin: normalizedWebViewOrigin });
  }

  // Send one Request through OS networking and OS-vault credentials exactly once.
  async function scopedFetch(input, init = undefined) {
    // Resolve string input before Request construction so URL credentials fail with the governed code.
    const inputUrl = input instanceof Request ? null : new URL(String(input), normalizedWebViewOrigin);
    // Reject caller-selected credentials or ports before the platform Request constructor can vary errors.
    if (inputUrl && (inputUrl.username || inputUrl.password || inputUrl.port)) throw mobileError("MOBILE_CROSS_ORIGIN_BLOCKED");
    // Apply standard Request override and body-used semantics before classification.
    const request = input instanceof Request ? new Request(input, init) : new Request(new URL(String(input), normalizedWebViewOrigin), init);
    // Parse the effective request URL once.
    const requested = new URL(request.url);
    // Reject all non-API traffic because bundled assets must use ordinary platform fetch directly.
    if (!requested.pathname.startsWith("/api/")) throw mobileError("MOBILE_NON_API_TRANSPORT_FORBIDDEN");
    // Reject API URLs that try to select an external authority.
    if (requested.username || requested.password || requested.port || (`${requested.protocol}//${requested.hostname}` !== normalizedWebViewOrigin && requested.origin !== backend.origin)) throw mobileError("MOBILE_CROSS_ORIGIN_BLOCKED");
    // Resolve the effective method and lifecycle ticket before reading the body.
    const method = request.method.toUpperCase();
    // Allow only exact public session issuance after native proves the vault is empty.
    const allowEmptyVaultIssuance = method === "POST" && ["/api/v2/auth/login", "/api/v2/auth/guest"].includes(requested.pathname);
    // Capture the exact process/account/session generation for stale-completion rejection.
    let ticket;
    // Capture lifecycle authority without contacting native networking on an expired session.
    try { ticket = lifecycle.begin(method, { allowEmptyVaultIssuance }); }
    // Recover only the exact pre-I/O validation-age failure, never an offline/background/security error.
    catch (error) {
      // Preserve every other failure without retry or hidden network work.
      if (error?.code === "MOBILE_SESSION_REFRESH_REQUIRED") { onReconciliationRequired(); throw error; }
      // Preserve every other failure without retry or hidden network work.
      if (error?.code !== "MOBILE_SESSION_REVALIDATION_REQUIRED") throw error;
      // Coalesce one session probe before recapturing the original request ticket.
      await coalescedRevalidate();
      // Start the caller's original action once under the freshly validated authority.
      try { ticket = lifecycle.begin(method, { allowEmptyVaultIssuance }); }
      // Never auto-send an unsafe action after probe-only authority; request shared reconciliation instead.
      catch (refreshError) { if (refreshError?.code === "MOBILE_SESSION_REFRESH_REQUIRED") onReconciliationRequired(); throw refreshError; }
    }
    // Read the caller body once without mutating the caller-owned Request.
    const body = ["GET", "HEAD"].includes(method) ? "" : await request.clone().text();
    // Reject lifecycle, clock, or account drift that happened while the body was materialized.
    lifecycle.assertCurrent(ticket);
    // Execute through native networking exactly once with no cookie or automatic retry option.
    const result = await nativePlugin.request({ path: `${requested.pathname}${requested.search}`, method, headers: publicHeaders(request.headers), body, generation: ticket.vaultGeneration });
    // Fail closed if a native implementation returns any vault-owned credential field.
    assertSecretFreeEnvelope(String(result.body || ""));
    // Detect the small set of session-changing routes whose native vault commit intentionally advances generation.
    const sessionChanging = ["/api/v2/auth/login", "/api/v2/auth/guest", "/api/v2/auth/logout", "/api/v2/auth/guest/end", "/api/v2/auth/mobile/session/rotate", "/api/v2/auth/mobile/session/revoke"].includes(requested.pathname);
    // Reject a successful issuance or terminal response unless native code committed or cleared the vault.
    if (sessionChanging && Number(result.status) >= 200 && Number(result.status) < 300 && result.sessionChanged !== true) { lifecycle.invalidate(); throw mobileError("MOBILE_SESSION_TRANSITION_INVALID"); }
    // Bind an authoritative 401 vault clear before shared error handling receives the public envelope.
    if (result.sessionChanged === true) {
      // Bind the exact issuance, terminal clear, or authoritative 401 vault transition.
      lifecycle.transition(ticket, Number(result.generation), Number(result.status) !== 401, Number(result.status) === 401 || (Number(result.status) >= 200 && Number(result.status) < 300 && ["/api/v2/auth/logout", "/api/v2/auth/guest/end", "/api/v2/auth/mobile/session/revoke"].includes(requested.pathname)));
      // Start shared reconciliation after an authoritative 401 clear without retrying the completed request.
      if (Number(result.status) === 401) onReconciliationRequired();
    } else {
      // Reject every ordinary completion whose account/session generation changed in flight.
      lifecycle.complete(ticket, result.generation);
    }
    // Rebuild only public response headers returned by the native plugin.
    const headers = new Headers(result.headers || {});
    // Return a standards Response after native code stripped and stored every credential.
    return new Response(String(result.body || ""), { status: Number(result.status), headers });
  }

  // Revalidate the OS-vault session and server state after cold start, resume, reconnect, or clock drift.
  async function revalidate() {
    // Snapshot process, vault, and clock state before the asynchronous OS-vault probe.
    const ticket = lifecycle.beginProbe();
    // Ask native code to probe with the current vault record without exposing it to JavaScript.
    const result = await nativePlugin.probe();
    // Accept only an authenticated 200 or authoritative cleared/absent 401 result from native code.
    if (!result || ![200, 401].includes(Number(result.status)) || result.authenticated !== (Number(result.status) === 200)) throw mobileError("MOBILE_SESSION_PROBE_INVALID");
    // Bind only when no lifecycle, credential, or clock boundary changed while the probe ran.
    lifecycle.completeProbe(ticket, Number(result.generation), result.authenticated === true);
    // Return the identifier-free authenticated state for shell control only.
    return result.authenticated === true;
  }

  // Share one authoritative session probe across concurrent expiry or lifecycle recovery callers.
  async function coalescedRevalidate() {
    // Reuse the exact pending probe so concurrent callers cannot multiply native work.
    if (revalidationInFlight) return revalidationInFlight;
    // Freeze this exact probe before the first asynchronous native boundary.
    const pending = revalidate();
    // Publish the promise before yielding so later callers join it.
    revalidationInFlight = pending;
    // Preserve the original result or error while clearing only this completed attempt.
    try { return await pending; } finally { if (revalidationInFlight === pending) revalidationInFlight = null; }
  }

  // Revoke and verify the old session before clearing the vault for account switching.
  async function prepareAccountSwitch() {
    // Invalidate every earlier request before asynchronous predecessor revocation can begin.
    lifecycle.invalidate();
    // Let native code perform revoke, probe, and atomic vault clear without exposing credentials.
    const result = await nativePlugin.revokeAndClear();
    // Require proof that the predecessor is unusable before advancing process state.
    if (result.revoked !== true || result.cleared !== true) throw mobileError("MOBILE_ACCOUNT_SWITCH_REVOKE_FAILED");
    // Rebind the cleared vault generation so the following public login mutation may start safely.
    await coalescedRevalidate();
  }

  // Claim one digest-only deep-link fingerprint atomically in the OS vault.
  async function claimDeepLink(fingerprint) {
    // Reject malformed caller values before crossing the native bridge.
    if (!/^[a-f0-9]{64}$/.test(String(fingerprint))) throw mobileError("MOBILE_DEEP_LINK_FINGERPRINT_INVALID");
    // Persist only the digest under native bounded replay retention.
    const result = await nativePlugin.claimDeepLink({ fingerprint });
    // Reject a replay from this or an earlier process before navigation.
    if (result.claimed !== true) throw mobileError("MOBILE_DEEP_LINK_REPLAY");
  }

  // Expose only secret-free transport, lifecycle, and account-switch operations.
  return Object.freeze({ configure, fetch: scopedFetch, revalidate: coalescedRevalidate, prepareAccountSwitch, claimDeepLink });
}
