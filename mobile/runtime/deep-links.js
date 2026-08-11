// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Define exact restricted-preview routes and their only permitted query fields.
const ROUTES = new Map([["/enroll/invitation", new Set(["token"])], ["/enroll/verify", new Set(["token"])], ["/account/reset", new Set(["token"])]]);
// Accept only bounded URL-safe bearer characters before authoritative purpose and expiry validation.
const TOKEN_PATTERN = /^[A-Za-z0-9_-]{20,512}$/;

// Validate one universal link and split transient secret material from public navigation.
export function validateDeepLink(rawUrl, canonicalOrigin) {
  // Parse only an absolute app/universal link so relative WebView navigation cannot impersonate OS ownership.
  const candidate = new URL(rawUrl);
  // Require exact HTTPS scheme and authority so custom schemes and lookalikes fail closed.
  if (candidate.protocol !== "https:" || candidate.origin !== new URL(canonicalOrigin).origin || candidate.username || candidate.password) throw new Error("MOBILE_DEEP_LINK_ORIGIN_INVALID");
  // Reject fragments because they can retain ungoverned provider or bearer state.
  if (candidate.hash) throw new Error("MOBILE_DEEP_LINK_FRAGMENT_INVALID");
  // Resolve the exact route allowlist.
  const allowed = ROUTES.get(candidate.pathname);
  // Reject every route not explicitly part of restricted-preview account recovery.
  if (!allowed) throw new Error("MOBILE_DEEP_LINK_PATH_INVALID");
  // Reject unknown or duplicate query keys before reading their values.
  for (const key of candidate.searchParams.keys()) if (!allowed.has(key) || candidate.searchParams.getAll(key).length !== 1) throw new Error("MOBILE_DEEP_LINK_QUERY_INVALID");
  // Resolve transient bearer material only for the three purpose-bound routes.
  const bearer = allowed.has("token") ? candidate.searchParams.get("token") || "" : "";
  // Require exactly one bounded bearer before it can enter module-only memory.
  if (allowed.has("token") && (!TOKEN_PATTERN.test(bearer) || candidate.searchParams.size !== 1)) throw new Error("MOBILE_DEEP_LINK_TOKEN_INVALID");
  // Return the bearer separately so runtime strips it before history or shared routing.
  return Object.freeze({ path: candidate.pathname, bearer, publicLocation: candidate.pathname });
}

// Derive one non-secret replay fingerprint for OS-vault duplicate rejection.
export async function deepLinkFingerprint(validated) {
  // Hash route plus transient bearer or public callback without retaining the raw value.
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${validated.path}\n${validated.bearer || validated.publicLocation}`));
  // Encode the complete fixed-length digest for collision-resistant native storage.
  return Array.from(new Uint8Array(digest)).map(value => value.toString(16).padStart(2, "0")).join("");
}
