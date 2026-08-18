// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for searchable Lobby catalog rendering. (CORE-007, CORE-012)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Lobby view factory.
import { createLobbyView } from "../../web/views/lobby.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/lobby.js`, "utf8");

// Verify catalog cards, search, categories, trust, and route actions survive extraction.
test("CORE-007 preserves the searchable Lobby after extraction", () => {
  // Retain one search control, category action, and game action across rerenders.
  const search = {
    value: "",
    focus: () => {},
    setSelectionRange: () => {},
  };
  const category = { dataset: { catalogCategory: "table" } };
  const openGame = { dataset: { openGame: "roulette" } };
  const view = {
    innerHTML: "",
    querySelector: () => search,
    querySelectorAll: selector => selector === "[data-catalog-category]" ? [category] : [openGame],
  };
  const routes = [];
  // Preserve two descriptors so search and category filtering have real choices.
  const games = [
    {
      id: "roulette", label: "Roulette", description: "Wheel game", tags: ["classic"],
      categories: ["table"], featured: true, wide: false, artClass: "roulette-art",
      symbol: "R", kicker: "Table",
    },
    {
      id: "slots", label: "Slots", description: "Reel game", tags: ["reels"],
      categories: ["slots"], featured: false, wide: false, artClass: "slots-art",
      symbol: "S", kicker: "Slots",
    },
  ];
  // Create the production renderer around deterministic catalog and brand seams.
  const renderLobby = createLobbyView({
    activeBrand: { venue: "Virtual Casino", mark: "VC" },
    getGameDescriptors: () => games,
    getLatestState: () => ({ games: [{ id: "roulette" }, { id: "slots" }], online_player_count: 3 }),
    navigate: route => routes.push(route),
    renderPremiumTag: tag => `<span class="tag">${tag}</span>`,
    safe: value => String(value ?? ""),
    t: (key, values = {}) => `${key}${values.count ?? values.current ?? ""}`,
  });
  // Render the complete catalog and bind its controls.
  renderLobby(view);
  for (const marker of [
    'data-testid="lobby"', "lobby-trust-rail", "catalog-search", "catalog-categories",
    "catalog-capacity", "game-gallery", "card-roulette", "card-slots", "open-roulette",
  ]) {
    // Require every accepted Lobby surface.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  assert.equal(typeof search.oninput, "function");
  assert.equal(typeof category.onclick, "function");
  assert.equal(typeof openGame.onclick, "function");
  // Filter search locally without changing route history.
  search.value = "wheel";
  search.oninput();
  assert.ok(view.innerHTML.includes("card-roulette"));
  assert.equal(view.innerHTML.includes("card-slots"), false);
  // Preserve explicit game navigation through the shared router.
  openGame.onclick();
  assert.deepEqual(routes, ["roulette"]);
});

// Verify the router owns composition while the Lobby owns transient filters.
test("CORE-012 keeps the Lobby view boundary reviewable", () => {
  // Require one import and reject retired state and helper implementations.
  assert.equal((APP_SOURCE.match(/from '.\/views\/lobby\.js'/g) || []).length, 1);
  for (const retired of [
    "let lobbySearch", "let lobbyCategory", "function trustItemHtml(",
    "function lobbyCardHtml(", "function filteredGames(", "function categoryLabel(",
    "function lobbyHtml(", "function renderLobby(",
  ]) {
    // Require each Lobby implementation to live only in the view module.
    assert.equal(APP_SOURCE.includes(retired), false, retired);
  }
  // Preserve stable catalog and route-action identities in the module.
  for (const marker of ["catalog-search", "catalog-categories", "data-open-game", "lobby-trust-rail"]) {
    // Bind each accepted identity to the Lobby view.
    assert.ok(MODULE_SOURCE.includes(marker), marker);
  }
  // Keep every Lobby view line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
