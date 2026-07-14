// Verify the isolated Red Dog ES module and locale resources without a server.

// Import strict assertions from the Node standard library.
import assert from 'node:assert/strict';
// Import UTF-8 file reading for source and locale parity checks.
import { readFile } from 'node:fs/promises';

// Provide the global expected by the shared i18n module during import.
globalThis.window = {};

// Import the isolated frontend after installing its minimal shared-module global.
const gameModule = await import('../../../../web/games/red_dog.js');
// Read the exported catalog contract.
const game = gameModule.RedDogGame;
// Assert the game id matches the proposed module descriptor.
assert.equal(game.id, 'red_dog');
// Assert catalog mounting remains callable.
assert.equal(typeof game.mount, 'function');
// Assert route changes can release module resources.
assert.equal(typeof game.unmount, 'function');

// Resolve the frontend source relative to this test file.
const frontendUrl = new URL('../../../../web/games/red_dog.js', import.meta.url);
// Resolve the English game dictionary relative to this test file.
const englishUrl = new URL('../../../../web/i18n/en-US/games/red_dog.json', import.meta.url);
// Resolve the Russian game dictionary relative to this test file.
const russianUrl = new URL('../../../../web/i18n/ru-RU/games/red_dog.json', import.meta.url);
// Read the JavaScript source for lifecycle assertions.
const source = await readFile(frontendUrl, 'utf8');
// Parse the English source strings.
const english = JSON.parse(await readFile(englishUrl, 'utf8'));
// Parse the Russian strings.
const russian = JSON.parse(await readFile(russianUrl, 'utf8'));
// Assert both required locales own the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Assert the matching-raise action is translated in both locales.
assert.ok(english['controls.raise'] && russian['controls.raise']);
// Assert card accessibility copy is owned by both locale domains.
assert.ok(english['card.label'] && russian['card.label']);
// Assert the Russian domain contains real Cyrillic copy rather than English fallback only.
assert.match(russian['controls.raise'], /[А-Яа-яЁё]/);
// Assert no raw timer loop can outlive a route change.
assert.doesNotMatch(source, /setTimeout\(|setInterval\(|requestAnimationFrame\(/);
// Assert player-id compatibility helpers are not used by the browser module.
assert.doesNotMatch(source, /withCurrentPlayer|currentPlayerPath/);
// Assert uncertain API actions retain a retry-safe id.
assert.match(source, /retryActionIds/);

// Report one concise success line for worker validation logs.
console.log('Red Dog frontend module tests passed.');
