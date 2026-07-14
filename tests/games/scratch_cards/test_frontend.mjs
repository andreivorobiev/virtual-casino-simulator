// Statically and functionally verify the isolated issue #87 frontend module.

// Import strict assertions for deterministic frontend verification.
import assert from 'node:assert/strict';
// Import filesystem helpers to inspect complete source and paired locale resources.
import { readFile } from 'node:fs/promises';
// Import the dependency-free built-in test runner.
import test from 'node:test';

// Provide the minimal browser global assigned by imported shared frontend helpers.
globalThis.window = {};
// Import pure exported helpers and the catalog-facing game contract after the browser global exists.
const { ScratchCardsGame, coveredPositions, createActionId } = await import('../../../web/games/scratch_cards.js');


// Verify the descriptor-facing export and deterministic injected retry identity.
test('issue 87 frontend exposes stable module and action identity', () => {
  // Verify the lazy module owns the expected catalog id.
  assert.equal(ScratchCardsGame.id, 'scratch_cards');
  // Inject one deterministic UUID without ambient browser crypto.
  const actionId = createActionId('scratch-start', () => '00000000-0000-4000-8000-000000000087');
  // Verify the resulting action identity is stable and game-specific.
  assert.equal(actionId, 'scratch-start-00000000-0000-4000-8000-000000000087');
});


// Verify the public masked-card helper returns only covered positions in stable order.
test('issue 87 covered position helper preserves masked order', () => {
  // Build one mixed public cell list without any private board data.
  const card = { cells: [{ position: 0, revealed: true, prize: 2 }, { position: 1, revealed: false }, { position: 2, revealed: false }] };
  // Verify only covered positions remain and preserve server order.
  assert.deepEqual(coveredPositions(card), [1, 2]);
  // Verify an absent current card produces an empty action set.
  assert.deepEqual(coveredPositions(null), []);
});


// Verify complete locale parity, key coverage, and encoding cleanliness.
test('issue 87 EN and RU resources have exact clean coverage', async () => {
  // Read the complete English game-owned dictionary.
  const english = JSON.parse(await readFile(new URL('../../../web/i18n/en-US/games/scratch_cards.json', import.meta.url), 'utf8'));
  // Read the complete Russian game-owned dictionary.
  const russian = JSON.parse(await readFile(new URL('../../../web/i18n/ru-RU/games/scratch_cards.json', import.meta.url), 'utf8'));
  // Read frontend source so every literal translation lookup can be validated.
  const source = await readFile(new URL('../../../web/games/scratch_cards.js', import.meta.url), 'utf8');
  // Verify every visible key exists in both locales.
  assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
  // Collect every static text lookup used by the browser module.
  const usedKeys = [...source.matchAll(/text\('([^']+)'/g)].map(match => match[1]);
  // Verify every static lookup resolves in the English dictionary.
  assert.deepEqual(usedKeys.filter(key => !(key in english)), []);
  // Verify every static lookup resolves in the Russian dictionary.
  assert.deepEqual(usedKeys.filter(key => !(key in russian)), []);
  // Reject common UTF-8-as-legacy mojibake markers and replacement characters.
  assert.doesNotMatch(JSON.stringify(russian), /�|Ð|Ñ|Â|â/);
  // Reject real-money wording from player-visible English copy.
  assert.doesNotMatch(Object.values(english).join(' '), /\b(?:cash|dollars?|deposit|withdraw|purchase|money)\b/i);
});


// Verify semantic controls, ARIA localization, and timer-free lifecycle ownership.
test('issue 87 source keeps accessible reveals timer-free', async () => {
  // Read the complete frontend source for static policy checks.
  const source = await readFile(new URL('../../../web/games/scratch_cards.js', import.meta.url), 'utf8');
  // Verify the catalog readiness selector is owned by the game surface.
  assert.match(source, /data-testid="scratch-cards"/);
  // Verify every reveal cell is a semantic button with pressed-state communication.
  assert.match(source, /<button type="button" class="scratch-cell/);
  // Verify the game stage does not nest another main landmark inside the shell outlet.
  assert.doesNotMatch(source, /<main\b/);
  // Verify covered and revealed accessible names come from locale keys.
  assert.match(source, /stage\.coveredAria/);
  // Verify game code creates no raw or parallel timing primitive.
  assert.doesNotMatch(source, /setTimeout|setInterval|requestAnimationFrame|createMotionTimerScope/);
  // Verify reduced-motion styling removes all decorative transitions and animations.
  assert.match(source, /prefers-reduced-motion:reduce/);
  // Verify a fresh mount adopts the server-published pending purchase identity.
  assert.match(source, /pendingStartId = card\.pending_client_request_id/);
  // Verify late async continuations are gated by one mount-generation ownership helper.
  assert.match(source, /function ownsMount\(generation\)/);
  // Verify wallet refresh has separate post-commit error semantics.
  assert.match(source, /refreshWalletSafely/);
  // Verify no hard-coded English primary action appears inside rendered markup.
  assert.doesNotMatch(source, />Start card</);
});
