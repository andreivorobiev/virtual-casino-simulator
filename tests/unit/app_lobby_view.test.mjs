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
// Import the browser-independent tagged-template fixture for injected view rendering.
import { html, raw } from "./html_template_fixture.mjs";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const APP_SOURCE = await readFile(`${ROOT}/web/app.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/views/lobby.js`, "utf8");

// Verify catalog cards, search, categories, trust, and route actions survive extraction.
test("CORE-007 preserves the searchable Lobby after extraction", () => {
  // Retain one search control, gallery, category action, and game action across updates.
  const search = {
    value: "",
    selectionStart: 0,
    selectionEnd: 0,
  };
  // Capture gallery-only replacements independently from full Lobby renders.
  const gallery = { innerHTML: "", querySelectorAll: () => [openGame] };
  const category = { dataset: { catalogCategory: "table" } };
  const openGame = { dataset: { openGame: "roulette" } };
  // Count complete outlet writes so search filtering can prove it leaves the input mounted.
  let rootWrites = 0;
  // Retain the latest rendered Lobby markup behind an observable property seam.
  let rootMarkup = "";
  const view = {
    querySelector: selector => selector === '[data-testid="game-gallery"]' ? gallery : search,
    querySelectorAll: selector => selector === "[data-catalog-category]" ? [category] : [openGame],
  };
  // Track each production root replacement without parsing browser markup in Node.
  Object.defineProperty(view, "innerHTML", {
    // Return the latest complete Lobby markup for stable identity assertions.
    get: () => rootMarkup,
    // Record complete replacements separately from debounced gallery writes.
    set: (value) => { rootWrites += 1; rootMarkup = String(value); },
  });
  const routes = [];
  // Capture deterministic timer scheduling without sleeping in the unit suite.
  let pendingSearch = null;
  // Count scheduled and superseded callbacks so rapid edits prove coalescing.
  let scheduledSearches = 0;
  let clearedSearches = 0;
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
    // Bind the same escape-by-default and reviewed-fragment contract as production.
    html,
    raw,
    activeBrand: { venue: "Virtual Casino", mark: "VC" },
    getGameDescriptors: () => games,
    getLatestState: () => ({ games: [{ id: "roulette" }, { id: "slots" }], online_player_count: 3 }),
    navigate: route => routes.push(route),
    renderPremiumTag: tag => `<span class="tag">${tag}</span>`,
    safe: value => String(value ?? ""),
    clearTimeoutFn: () => { clearedSearches += 1; pendingSearch = null; },
    setTimeoutFn: (callback, wait) => {
      // Require the documented short debounce budget at the injected timer seam.
      assert.equal(wait, 100);
      // Retain only the newest callback just like the browser timer queue after cancellation.
      pendingSearch = callback;
      // Return a stable non-null timer identity.
      scheduledSearches += 1;
      return scheduledSearches;
    },
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
  // Queue one partial query before the final edit to prove only the newest search commits.
  search.value = "w";
  search.oninput();
  // Preserve the live input and caret while a second rapid edit supersedes the first timer.
  search.value = "wheel";
  search.selectionStart = search.value.length;
  search.selectionEnd = search.value.length;
  search.oninput();
  assert.deepEqual([scheduledSearches, clearedSearches, rootWrites], [2, 1, 1]);
  assert.equal(view.querySelector('[data-testid="catalog-search"]'), search);
  assert.deepEqual([search.selectionStart, search.selectionEnd], [5, 5]);
  // Commit the latest timer and require only the gallery to change.
  pendingSearch();
  assert.ok(gallery.innerHTML.includes("card-roulette"));
  assert.equal(gallery.innerHTML.includes("card-slots"), false);
  assert.equal(rootWrites, 1);
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
