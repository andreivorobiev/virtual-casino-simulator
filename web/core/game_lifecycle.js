// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Shared browser-game lifecycle ownership for issue #718 and requirement CORE-034.
// Import the canonical locale runtime so games do not reimplement domain translation or subscription cleanup.
import { initI18n, onLocaleChange, t } from './i18n.js';

// Accept only bounded identifiers that remain safe in request ids and DOM ownership markers.
const IDENTIFIER_RE = /^[a-z][a-z0-9-]{0,63}$/;
// Accept only canonical lazy game domains with bounded path segments.
const GAME_DOMAIN_RE = /^games\/[a-z0-9_-]+(?:\/[a-z0-9_-]+)*$/;
// Accept only one same-origin route-local CSS asset without traversal or query ambiguity.
const GAME_STYLESHEET_RE = /^\/games\/[a-z0-9_-]+\.css$/;
// Retain the production i18n adapters as one immutable default dependency set.
const DEFAULT_I18N = Object.freeze({ initI18n, onLocaleChange, t });

// Create one route-owned lifecycle controller for an isolated browser game.
export function createGameLifecycle(options = {}) {
  // Read the required localization domain once so every translation call has one owner.
  const domain = String(options.domain || '');
  // Read the bounded request prefix used only when UUID support is unavailable.
  const requestPrefix = String(options.requestPrefix || 'game');
  // Retain an optional external stylesheet descriptor for route-local presentation.
  const stylesheet = options.stylesheet || null;
  // Accept injected adapters so dependency-free tests can exercise exact lifecycle behavior.
  const i18n = options.i18n || DEFAULT_I18N;
  // Use the active document by default while allowing a deterministic test document.
  const documentRef = options.documentRef || globalThis.document;
  // Prefer an injected UUID factory before consulting the browser crypto API.
  const uuidFactory = options.uuidFactory || (() => globalThis.crypto?.randomUUID?.());
  // Accept a deterministic clock for fallback request-identity evidence.
  const now = options.now || (() => Date.now());
  // Accept a deterministic random source for fallback request-identity evidence.
  const random = options.random || (() => Math.random());
  // Reject a missing or traversal-shaped localization domain before any DOM or network work.
  if (!GAME_DOMAIN_RE.test(domain)) throw new TypeError('game lifecycle domain is invalid');
  // Reject request prefixes that cannot form a bounded opaque identifier.
  if (!IDENTIFIER_RE.test(requestPrefix)) throw new TypeError('game lifecycle request prefix is invalid');
  // Require the three exact locale operations consumed by the controller.
  if (typeof i18n.initI18n !== 'function' || typeof i18n.onLocaleChange !== 'function' || typeof i18n.t !== 'function') throw new TypeError('game lifecycle i18n adapters are invalid');
  // Reject incomplete stylesheet descriptors rather than mounting an unstyled route.
  if (stylesheet && (!IDENTIFIER_RE.test(String(stylesheet.id || '')) || !GAME_STYLESHEET_RE.test(String(stylesheet.href || '')))) throw new TypeError('game lifecycle stylesheet is invalid');

  // Store the currently owned route outlet without exporting mutable state.
  let outlet = null;
  // Store the exact busy state shared by actions and locale repaint suppression.
  let busy = false;
  // Retain the current locale subscription disposer for exact unmount cleanup.
  let localeUnsubscribe = null;
  // Increment the generation whenever mount ownership changes across asynchronous initialization.
  let generation = 0;

  // Install or validate one external game stylesheet without injecting opaque CSS text.
  function ensureStylesheet() {
    // Skip DOM work when the game owns no route-local stylesheet.
    if (!stylesheet) return null;
    // Fail before mutation when a document is unavailable or incomplete.
    if (!documentRef || !documentRef.head || typeof documentRef.createElement !== 'function' || typeof documentRef.getElementById !== 'function') throw new TypeError('game lifecycle document is unavailable');
    // Reuse the exact stylesheet installed by an earlier mount.
    const existing = documentRef.getElementById(stylesheet.id);
    // Validate reused ownership instead of accepting a conflicting style or link element.
    if (existing) {
      // Read the existing tag name in a browser- and test-stable form.
      const tagName = String(existing.tagName || '').toLowerCase();
      // Read the literal attribute so absolute URL normalization cannot hide a different resource.
      const href = existing.getAttribute?.('href');
      // Require the same external stylesheet contract on every remount.
      if (tagName !== 'link' || String(existing.rel || '').toLowerCase() !== 'stylesheet' || href !== stylesheet.href) throw new Error('game lifecycle stylesheet ownership conflict');
      // Return the already installed exact node.
      return existing;
    }
    // Create one same-origin stylesheet link owned by this route.
    const link = documentRef.createElement('link');
    // Assign the stable id before insertion so concurrent discovery sees complete ownership.
    link.id = stylesheet.id;
    // Declare stylesheet semantics explicitly.
    link.rel = 'stylesheet';
    // Bind the reviewed same-origin game asset path.
    link.href = stylesheet.href;
    // Append the external resource once to the document head.
    documentRef.head.appendChild(link);
    // Return the installed link for deterministic tests and diagnostics.
    return link;
  }

  // Translate one key through the game-owned lazy domain.
  function tx(key, params = {}) {
    // Delegate interpolation and fallback handling to the canonical i18n runtime.
    return i18n.t(key, params, domain);
  }

  // Generate one caller-stable opaque identity for an exactly-once action attempt.
  function nextRequestId(kind = '') {
    // Normalize the optional action kind without permitting separators or unbounded text.
    const actionKind = String(kind || '');
    // Reject malformed kinds before a request can reach the shared API helper.
    if (actionKind && !IDENTIFIER_RE.test(actionKind)) throw new TypeError('game lifecycle request kind is invalid');
    // Prefer a platform UUID so ordinary browsers retain collision-resistant identities.
    const uuid = uuidFactory();
    // Return the platform identity when one is available.
    if (uuid) return String(uuid);
    // Scope the deterministic fallback to the game and optional action kind.
    const scope = actionKind ? `${requestPrefix}-${actionKind}` : requestPrefix;
    // Build the established time-and-random fallback without exposing player or game state.
    return `${scope}-${now()}-${Math.floor(random() * 1e9)}`;
  }

  // Mount one game outlet and establish locale and stylesheet ownership before loading game state.
  async function mount(node, render) {
    // Require one render callback for locale changes.
    if (!node || typeof render !== 'function') throw new TypeError('game lifecycle mount arguments are invalid');
    // Refuse a second live outlet so one controller cannot repaint two routes.
    if (outlet) throw new Error('game lifecycle is already mounted');
    // Capture a fresh generation before asynchronous resource loading begins.
    const ownedGeneration = ++generation;
    // Adopt the exact shell-owned route outlet.
    outlet = node;
    // Reset stale action state before any mount-owned work starts.
    busy = false;
    // Start protected resource initialization so every failure releases outlet ownership.
    try {
      // Install or validate the route-local stylesheet before visible rendering.
      ensureStylesheet();
      // Load the exact game domain through the shared fallback chain.
      await i18n.initI18n({ domains: [domain] });
      // Stop cleanly when navigation unmounted this route during asynchronous initialization.
      if (generation !== ownedGeneration || outlet !== node) return false;
      // Subscribe one repaint callback after resources are ready.
      const unsubscribe = i18n.onLocaleChange(() => {
        // Repaint only the current idle route; the action owner will render its terminal locale state.
        if (generation === ownedGeneration && outlet === node && !busy) render();
      });
      // Reject adapters that cannot release the exact route-owned subscription.
      if (typeof unsubscribe !== 'function') throw new TypeError('game lifecycle locale disposer is invalid');
      // Retain the validated disposer only after subscription succeeds completely.
      localeUnsubscribe = unsubscribe;
      // Report successful ownership so the game may load authoritative session state.
      return true;
    // Release only this generation when style or localization initialization fails.
    } catch (error) {
      // Clear route and action ownership when no newer owner replaced this mount.
      if (generation === ownedGeneration && outlet === node) {
        // Remove a subscription when its adapter threw only after installing one.
        localeUnsubscribe?.();
        // Clear the disposer for a later independent mount.
        localeUnsubscribe = null;
        // Release the exact failed outlet.
        outlet = null;
        // Release the action guard with the failed mount.
        busy = false;
      }
      // Propagate the original failure to the shell's game loader.
      throw error;
    }
  }

  // Release every route-owned lifecycle resource without removing reusable external CSS.
  function unmount() {
    // Invalidate every pending initialization or locale callback first.
    generation += 1;
    // Remove the exact locale subscription when initialization completed.
    localeUnsubscribe?.();
    // Clear the disposer so repeated teardown remains idempotent.
    localeUnsubscribe = null;
    // Release the shell outlet so stale asynchronous work cannot repaint another route.
    outlet = null;
    // Release the action guard for the next independent mount.
    busy = false;
  }

  // Publish only bounded operations and read-only state accessors.
  return Object.freeze({
    // Return the currently owned route outlet or null after teardown.
    root: () => outlet,
    // Report whether this controller currently owns a route outlet.
    isMounted: () => outlet !== null,
    // Report the exact action guard state.
    isBusy: () => busy,
    // Update the action guard with strict boolean input.
    setBusy: value => {
      // Reject truthy substitutes that could keep locale behavior ambiguous.
      if (typeof value !== 'boolean') throw new TypeError('game lifecycle busy state must be boolean');
      // Store the exact caller-owned action state.
      busy = value;
      // Return the stored value for concise deterministic assertions.
      return busy;
    },
    // Expose domain-bound translation without a game-local wrapper.
    tx,
    // Expose bounded request identity generation without a game-local wrapper.
    nextRequestId,
    // Expose the guarded asynchronous mount transition.
    mount,
    // Expose idempotent teardown for shell navigation.
    unmount,
  });
}
