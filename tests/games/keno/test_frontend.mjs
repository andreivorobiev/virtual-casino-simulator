// Verify the #718 Keno frontend delegates shared ownership without changing ticket behavior.

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
const source = await readFile(path.join(root, 'web', 'games', 'keno.js'), 'utf8');
// Read the extracted premium stylesheet for representative selector preservation.
const stylesheet = await readFile(path.join(root, 'web', 'games', 'keno.css'), 'utf8');

// Require the shared lifecycle and exact stale-session boundaries.
test('CORE-034 shared lifecycle owns the Keno route', () => {
  // Require route, busy, locale, external-style, motion, and stale-session ownership markers.
  for (const marker of ['createGameLifecycle', 'lifecycle.mount(node, render)', 'lifecycle.unmount()', 'lifecycle.root()', 'lifecycle.isBusy()', 'lifecycle.setBusy(true)', "requestPrefix: 'keno'", "href: '/games/keno.css'", 'createMotionTimerScope', 'routeSession', 'ownsRoute']) assert.ok(source.includes(marker), marker);
  // Reject migrated route, draw-busy, locale-subscription, raw-timer, and inline-style owners.
  for (const duplicate of ['let root =', 'let drawBusy =', 'localeUnsubscribe', 'function ensureStyles', 'style.textContent', 'onLocaleChange', 'initI18n', 'loadI18nDomain', 'setTimeout']) assert.equal(source.includes(duplicate), false, duplicate);
  // Require representative hero, controls, board, balls, result, repeat, and responsive rules.
  for (const selector of ['.keno-premium {', '.keno-hero {', '.keno-layout {', '.keno-command-grid {', '.keno-premium-board {', '.keno-ball-rail {', '.keno-result-copy {', '.keno-repeat {', '@media (min-width:1201px)', '@media (max-width:1200px)', '@media (max-width:560px)', '@media (prefers-reduced-motion:reduce)']) assert.ok(stylesheet.includes(selector), selector);
});

// Preserve frozen-v1 actions and shared control-plane dependencies.
test('Keno module boundaries and public action paths remain intact', () => {
  // Keep shared API, autoplay, bot, voice, UI, and motion dependencies instead of game-owned substitutes.
  for (const dependency of ["from '../core/api.js'", "from '../core/autoplay.js'", "from '../core/bots.js'", "from '../core/voice.js'", "from '../core/ui.js'", "from '../core/motion.js'"]) assert.ok(source.includes(dependency), dependency);
  // Keep the documented ticket and draw endpoints free of caller-authored route identities.
  for (const endpoint of ['/api/v1/games/keno/tickets', '/api/v1/games/keno/draw']) assert.ok(source.includes(endpoint), endpoint);
  // Preserve autoplay as a control-plane action rather than a game-owned interval.
  assert.doesNotMatch(source, /\bsetInterval\s*\(|\brequestAnimationFrame\s*\(/);
});
