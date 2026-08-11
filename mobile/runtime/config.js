// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Define the only configuration keys allowed into the signed mobile web bundle.
const ALLOWED_KEYS = new Set(["environment", "backendBaseUrl", "nativeOrigins"]);
// Enumerate the only signed Capacitor origins supported by the two generated platforms.
const NATIVE_ORIGINS = new Set(["https://localhost", "capacitor://localhost"]);
// Pin OS-vault credentials to the only currently governed production API authority.
const BACKEND_ORIGINS = new Set(["https://casino.tiltseven.com"]);

// Export strict validation so the build and runtime enforce the same fail-closed contract.
export function validateMobileConfig(value) {
  // Reject arrays, null, and primitive values before reading configuration fields.
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Mobile configuration must be a JSON object.");
  // Reject unknown keys so credentials or accidental secret-bearing fields cannot be bundled.
  for (const key of Object.keys(value)) if (!ALLOWED_KEYS.has(key)) throw new Error(`Unsupported mobile configuration key: ${key}`);
  // Require a short environment label for evidence and build provenance.
  if (typeof value.environment !== "string" || !/^[a-z][a-z0-9-]{0,31}$/.test(value.environment)) throw new Error("environment must be a lowercase label.");
  // Require an explicit backend URL instead of falling back to the native WebView origin.
  if (typeof value.backendBaseUrl !== "string" || value.backendBaseUrl.length === 0) throw new Error("backendBaseUrl is required.");
  // Parse the backend value with the platform URL implementation.
  const backend = new URL(value.backendBaseUrl);
  // Reject embedded credentials because native configuration is not a secret store.
  if (backend.username || backend.password) throw new Error("backendBaseUrl must not contain credentials.");
  // Reject query strings and fragments so only a stable backend origin is configured.
  if (backend.search || backend.hash) throw new Error("backendBaseUrl must not contain a query string or fragment.");
  // Reject path prefixes so frozen API paths retain their exact /api/v1 and /api/v2 meanings.
  if (backend.pathname !== "/") throw new Error("backendBaseUrl must be an origin without a path.");
  // Require HTTPS in every build because the native vault must never send credentials over cleartext.
  if (backend.protocol !== "https:") throw new Error("backendBaseUrl must use HTTPS.");
  // Reject every unreviewed TLS authority so signed configuration cannot redirect vault credentials.
  if (!BACKEND_ORIGINS.has(backend.origin)) throw new Error("backendBaseUrl is not a governed backend origin.");
  // Require the complete exact platform-origin set so signed native request identity cannot drift.
  if (!Array.isArray(value.nativeOrigins) || value.nativeOrigins.length !== NATIVE_ORIGINS.size || new Set(value.nativeOrigins).size !== NATIVE_ORIGINS.size || value.nativeOrigins.some(origin => !NATIVE_ORIGINS.has(origin))) throw new Error("nativeOrigins must contain only the exact governed Capacitor origins.");
  // Return only normalized, public configuration values for bundling and runtime use.
  return Object.freeze({ environment: value.environment, backendBaseUrl: backend.origin, nativeOrigins: Object.freeze([...value.nativeOrigins].sort()) });
}
