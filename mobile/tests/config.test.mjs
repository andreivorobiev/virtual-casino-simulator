// Import strict assertions for fail-closed mobile configuration tests.
import assert from "node:assert/strict";
// Import the built-in test runner used on every supported CI host.
import test from "node:test";
// Import the shared validator exercised by both build and native runtime.
import { validateMobileConfig } from "../runtime/config.js";

// Verify a public HTTPS backend origin is normalized and accepted.
test("accepts the explicit governed HTTPS backend origin", () => {
  // Validate the only currently governed credential destination.
  const config = validateMobileConfig({ environment: "ci", backendBaseUrl: "https://casino.tiltseven.com", nativeOrigins: ["capacitor://localhost", "https://localhost"] });
  // Confirm normalization preserves the intended public backend origin.
  assert.equal(config.backendBaseUrl, "https://casino.tiltseven.com");
  // Confirm the validator returns only the two public governed fields.
  assert.deepEqual(Object.keys(config), ["environment", "backendBaseUrl", "nativeOrigins"]);
});

// Verify missing backend configuration stops the build and runtime closed.
test("rejects a missing backend origin", () => {
  // Assert the required backend field cannot silently fall back to the WebView origin.
  assert.throws(() => validateMobileConfig({ environment: "ci" }), /backendBaseUrl is required/);
});

// Verify credential-bearing URLs can never enter generated native assets.
test("rejects credentials and unknown secret-like fields", () => {
  // Assert URL user information is rejected before bundling.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://user:pass@casino.tiltseven.com", nativeOrigins: ["capacitor://localhost", "https://localhost"] }), /must not contain credentials/);
  // Assert unknown fields are rejected instead of being copied into generated JSON.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://casino.tiltseven.com", nativeOrigins: ["capacitor://localhost", "https://localhost"], token: "secret" }), /Unsupported mobile configuration key/);
});

// Verify cleartext transport and former development bypasses are both rejected.
test("rejects every cleartext or bypass configuration", () => {
  // Assert ordinary cleartext backend origins are rejected.
  assert.throws(() => validateMobileConfig({ environment: "development", backendBaseUrl: "http://example.invalid", nativeOrigins: ["capacitor://localhost", "https://localhost"] }), /must use HTTPS/);
  // Assert the retired cleartext escape hatch is rejected as an unknown configuration key.
  assert.throws(() => validateMobileConfig({ environment: "development", backendBaseUrl: "http://10.0.2.2:8080", allowInsecureLocalDevelopment: true }), /Unsupported mobile configuration key/);
  // Reject missing, wildcard, duplicated, or unowned native origins.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://casino.tiltseven.com", nativeOrigins: ["*"] }), /exact governed Capacitor origins/);
  // Reject foreign TLS even though transport encryption itself is valid.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://backend.example.invalid", nativeOrigins: ["capacitor://localhost", "https://localhost"] }), /not a governed backend origin/);
});

// Verify frozen API paths cannot be altered with a configured URL prefix.
test("rejects path, query, and fragment changes", () => {
  // Assert path prefixes cannot reinterpret frozen API routes.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://casino.tiltseven.com/base", nativeOrigins: ["capacitor://localhost", "https://localhost"] }), /without a path/);
  // Assert query configuration cannot leak or alter requests.
  assert.throws(() => validateMobileConfig({ environment: "ci", backendBaseUrl: "https://casino.tiltseven.com?mode=test", nativeOrigins: ["capacitor://localhost", "https://localhost"] }), /query string or fragment/);
});
