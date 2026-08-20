// Verify the #718 Bingo frontend delegates route ownership without changing game behavior.

// Import strict assertions for deterministic lifecycle evidence.
import assert from 'node:assert/strict';
// Import source reads from the standard library.
import { readFile } from 'node:fs/promises';
// Import the dependency-free Node test runner.
import test from 'node:test';
// Import path resolution for Windows and POSIX focused execution.
import path from 'node:path';
// Import URL conversion for a stable repository root.
import { fileURLToPath } from 'node:url';

// Resolve the repository root from this game-specific test directory.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
// Read the production controller for ownership and duplicate-helper assertions.
const source = await readFile(path.join(root, 'web', 'games', 'bingo.js'), 'utf8');
// Read the extracted premium stylesheet for representative selector preservation.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'bingo.css'), 'utf8');

// Require the shared lifecycle and exact stale-session boundaries.
test('CORE-034 shared lifecycle owns the Bingo route', () => {
  // Require route, busy, locale, request, external-style, and session ownership markers.
  for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', "requestPrefix: 'bingo'", "href: '/games/bingo.css'", 'routeSession', 'ownsRoute']) assert.ok(source.includes(marker), marker);
  // Reject both legacy busy flags plus migrated root, locale, and inline-style owners.
  for (const duplicate of ['let root =', 'let callBusy =', 'let purchaseBusy =', 'unsubscribeLocale', 'function ensureStyles', 'const BINGO_CSS', 'const BINGO_DESKTOP_CONTAINMENT_CSS', 'style.textContent', 'onLocaleChange', 'initI18n']) assert.equal(source.includes(duplicate), false, duplicate);
  // Require localized placeholder construction to happen only after lifecycle resource loading.
  assert.ok(source.indexOf('const mounted = await lifecycle.mount(node, render)') < source.indexOf('botPanelCache = loadingBotsHtml();', source.indexOf('async mount(node)')));
  // Require representative premium layout, controls, cards, call bay, repeat, and responsive rules.
  for (const selector of ['.premium-bingo {', '.premium-bingo-hero {', '.premium-bingo .game-stage {', '.premium-bingo-actions {', '.premium-bingo .bingo-card {', '.bingo-daub {', '.premium-bingo-call-bay {', '.premium-bingo-orb.is-calling {', '.premium-bingo-repeat {', '@media (min-width:1101px)', '@media (max-width:1100px)', '@media (max-width:760px)', '@media (prefers-reduced-motion:reduce)']) assert.ok(stylesheet.includes(selector), selector);
});

// Preserve frozen-v1 session identity and shared control-plane dependencies.
test('Bingo module boundaries and public action paths remain intact', () => {
  // Keep shared API, autoplay, bot, voice, and UI dependencies instead of game-owned substitutes.
  for (const dependency of ["from '../core/api.js'", "from '../core/autoplay.js'", "from '../core/bots.js'", "from '../core/voice.js'", "from '../core/ui.js'"]) assert.ok(source.includes(dependency), dependency);
  // Keep session-selected endpoints free of caller-authored player ids.
  for (const endpoint of ['/api/v1/games/bingo/cards', '/api/v1/games/bingo/call', '/api/v1/games/bingo/reset']) assert.ok(source.includes(endpoint), endpoint);
  // Preserve autoplay as a one-call control-plane tick rather than a game-owned loop.
  assert.doesNotMatch(source, /\bsetInterval\s*\(|\brequestAnimationFrame\s*\(/);
});
