// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for the extracted application router and bootstrap. (CORE-007, PWA-002)
import assert from "node:assert/strict";
// Import repository file access for source-bound composition assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Supply the one browser global published by the shared locale module during import.
globalThis.window = {};
// Import compatible session helpers after the browser-global seam exists.
const { currentTokenBalance, normalizeCurrentUser } = await import("../../web/core/app_bootstrap.js");
// Import the extracted catalog router after the shared UI graph is initialized.
const { createAppRouter } = await import("../../web/core/app_router.js");

// Resolve reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const ROUTER_SOURCE = await readFile(`${ROOT}/web/core/app_router.js`, "utf8");
const BOOTSTRAP_SOURCE = await readFile(`${ROOT}/web/core/app_bootstrap.js`, "utf8");

// Build a router fixture whose pure catalog and location seams need no browser DOM.
function routerFixture() {
  // Retain mutable route state through explicit adapters.
  let active = null;
  const games = [{ id: "roulette", route: "/games/roulette", translations: { "ru-RU": { label: "Рулетка" } }, category: "table", frontend: { module: "./games/roulette.js", export: "RouletteGame" }, lobby: {} }];
  // Create the production router around inert render and lifecycle seams.
  return createAppRouter({
    documentRef: { getElementById: () => null, body: { classList: { remove: () => {} } } },
    getActive: () => active,
    getCurrentSession: () => null,
    getGameDescriptors: () => games.map(game => ({ id: game.id, route: game.route, label: "Рулетка" })),
    getLocaleState: () => ({ locale: "ru-RU", locales: [{ id: "ru-RU", nativeLabel: "Русский <script>" }] }),
    historyRef: {},
    isInvitationRoute: () => false,
    locationRef: { href: "https://casino.test/games/roulette", pathname: "/games/roulette", hash: "" },
    logClient: async () => {},
    navigationOwnership: { claim: () => 1, owns: () => true },
    renderExpiredSessionGate: () => {},
    renderLobby: () => {},
    renderMySettings: async () => {},
    renderPublicAuthRoute: () => false,
    safe: value => String(value ?? ""),
    setActive: value => { active = value; },
    setLocale: async () => {},
    t: key => key,
    updateCurrentUserShell: () => {},
    walletLifecycle: { interrupt: () => {} },
    windowRef: { MutationObserver: class {} },
  });
}

// Verify compatible session normalization remains stable outside app composition.
test("PWA-002 preserves current-user normalization and wallet precedence", () => {
  // Normalize an early compatible terms and token payload.
  const session = normalizeCurrentUser({ user: { terms_required: true, tokens: 12 }, player: { token_balance: 42 } });
  assert.equal(session.terms.required, true);
  assert.equal(currentTokenBalance(session), 42);
  // Preserve direct standard current-user envelopes.
  assert.equal(normalizeCurrentUser({ current_user: { terms: { required: false } } }).terms.required, false);
});

// Verify catalog localization, location restoration, and escaping survive extraction.
test("CORE-007 preserves routing and escaped locale options", () => {
  // Create one production router with Russian catalog metadata.
  const router = routerFixture();
  const descriptor = router.descriptorFromCatalog({ id: "roulette", translations: { "ru-RU": { label: "Рулетка" } }, category: "table", frontend: {}, lobby: {} });
  assert.equal(descriptor.label, "Рулетка");
  assert.equal(router.routeFromLocation(), "roulette");
  // Require the tagged helper to escape hostile ordinary locale text.
  assert.equal(String(router.localeOptionsHtml()), '<option value="ru-RU">Русский &lt;script&gt;</option>');
});

// Verify app.js is now bounded composition around extracted views and router.
test("CORE-007 keeps application composition under the series target", () => {
  // Keep the approximate 600-line series target with small formatting tolerance.
  assert.ok(APP_SOURCE.split(/\r?\n/).length <= 620);
  // Require the extracted router and bootstrap imports exactly once.
  assert.equal((APP_SOURCE.match(/from '.\/core\/app_router\.js'/g) || []).length, 1);
  assert.equal((APP_SOURCE.match(/from '.\/core\/app_bootstrap\.js'/g) || []).length, 1);
  // Reject retired route and initialization implementations from app composition.
  for (const name of ["loadGame", "init"]) assert.equal(APP_SOURCE.includes(`function ${name}(`), false, name);
  // Keep remaining route wrappers as one-line delegation rather than hidden implementations.
  assert.ok(APP_SOURCE.includes("function renderNav() { return appRouter.renderNav(); }"));
  // Bind navigation ownership and authoritative startup to their extracted modules.
  assert.ok(ROUTER_SOURCE.includes("navigationOwnership.claim()"));
  assert.ok(BOOTSTRAP_SOURCE.includes("await refreshCurrentSession()"));
});
