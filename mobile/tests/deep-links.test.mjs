// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for universal-link validation.
import assert from "node:assert/strict";
// Import the built-in deterministic test runner.
import test from "node:test";
// Import the pure deep-link validator.
import { validateDeepLink } from "../runtime/deep-links.js";

// Define the exact restricted-preview authority.
const ORIGIN = "https://casino.tiltseven.com";
// Define one synthetic high-entropy bearer with no live value.
const TOKEN = "abcdefghijklmnopqrstuvwxyz_0123456789-ABCDE";

// Verify account links preserve only exact allowlisted relative locations.
test("accepts exact HTTPS enrollment and recovery links", () => {
  // Split the enrollment bearer from the token-free public navigation target.
  assert.deepEqual(validateDeepLink(`${ORIGIN}/enroll/verify?token=${TOKEN}`, ORIGIN), { path: "/enroll/verify", bearer: TOKEN, publicLocation: "/enroll/verify" });
  // Apply the same immediate-scrub split to password recovery.
  assert.deepEqual(validateDeepLink(`${ORIGIN}/account/reset?token=${TOKEN}`, ORIGIN), { path: "/account/reset", bearer: TOKEN, publicLocation: "/account/reset" });
});

// Verify every untrusted scheme, authority, route, field, and bearer fails closed.
test("rejects untrusted or ambiguous deep links", () => {
  // Reject relative browser navigation because only OS-delivered absolute HTTPS links enter this boundary.
  assert.throws(() => validateDeepLink(`/account/reset?token=${TOKEN}`, ORIGIN), /Invalid URL/);
  // Reject a custom scheme that can be claimed by another application.
  assert.throws(() => validateDeepLink(`casino://enroll/verify?token=${TOKEN}`, ORIGIN), /ORIGIN_INVALID/);
  // Reject a lookalike HTTPS host.
  assert.throws(() => validateDeepLink(`https://casino.tiltseven.com.evil.example/enroll/verify?token=${TOKEN}`, ORIGIN), /ORIGIN_INVALID/);
  // Reject user information even when URL normalization preserves the canonical host origin.
  assert.throws(() => validateDeepLink(`https://user:pass@casino.tiltseven.com/account/reset?token=${TOKEN}`, ORIGIN), /ORIGIN_INVALID/);
  // Reject a route outside the explicit account-flow allowlist.
  assert.throws(() => validateDeepLink(`${ORIGIN}/games/roulette`, ORIGIN), /PATH_INVALID/);
  // Reject duplicate bearers and unknown state fields.
  assert.throws(() => validateDeepLink(`${ORIGIN}/enroll/verify?token=${TOKEN}&token=${TOKEN}`, ORIGIN), /QUERY_INVALID/);
  // Reject fragments that could retain ungoverned state.
  assert.throws(() => validateDeepLink(`${ORIGIN}/enroll/verify?token=${TOKEN}#secret`, ORIGIN), /FRAGMENT_INVALID/);
  // Reject short or malformed bearer material before server contact.
  assert.throws(() => validateDeepLink(`${ORIGIN}/enroll/verify?token=short`, ORIGIN), /TOKEN_INVALID/);
  // Reject the provider callback root because no exact-root Android verified-link filter is governed in this slice.
  assert.throws(() => validateDeepLink(`${ORIGIN}/?oauth_provider=google&oauth_status=signed_in`, ORIGIN), /PATH_INVALID/);
});
