// Import strict assertions for fail-closed mobile configuration tests.
import assert from "node:assert/strict";
// Import the built-in test runner used on every supported CI host.
import test from "node:test";
// Import the shared validator exercised by both build and native runtime.
import { validateMobileConfig } from "../runtime/config.js";

// Verify a public HTTPS backend origin is normalized and accepted.
test("accepts an explicit HTTPS backend origin", () => {
  // Validate a reserved non-routable example origin with no secret material.
  const config = validateMobileConfig({ environment: "ci", backendBaseUrl: "https://backend.example.invalid" });
  // Confirm normalization preserves the intended public backend origin.
  assert.equal(config.backendBaseUrl, "https://backend.example.invalid");
  // Confirm insecure development remains disabled by default.
  assert.equal(config.allowInsecureLocalDevelopment, false);
});

// Verify missing backend configuration stops the build and runtime closed.
test("rejects a missing backend origin", () => {
  // Assert the required backend field cannot silently fall back to the WebView origin.
  assert.throws(() => validateMobileConfig({ environment: "ci" }), /backendBaseUrl is required/);
});

// Verify credential-bearing URLs can never enter generated native assets.
test("rejects credentials and unknown secret-like fields", () => {
  // Assert URL user information is rejected before bundling.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://user:pass@example.invalid" }), /must not contain credentials/);
  // Assert unknown fields are rejected instead of being copied into generated JSON.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://backend.example.invalid", token: "secret" }), /Unsupported mobile configuration key/);
});

// Verify cleartext transport is limited to explicit local development hosts.
test("limits HTTP to explicit local development", () => {
  // Assert ordinary cleartext backend origins are rejected.
  assert.throws(() => validateMobileConfig({ environment: "development", backendBaseUrl: "http://example.invalid" }), /must use HTTPS/);
  // Validate Android emulator loopback only when the explicit development flag is set.
  const config = validateMobileConfig({ environment: "development", backendBaseUrl: "http://10.0.2.2:8080", allowInsecureLocalDevelopment: true });
  // Confirm the local-development exception is recorded for evidence.
  assert.equal(config.allowInsecureLocalDevelopment, true);
});

// Verify frozen API paths cannot be altered with a configured URL prefix.
test("rejects path, query, and fragment changes", () => {
  // Assert path prefixes cannot reinterpret frozen API routes.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://backend.example.invalid/base" }), /without a path/);
  // Assert query configuration cannot leak or alter requests.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://backend.example.invalid?mode=test" }), /query string or fragment/);
});
