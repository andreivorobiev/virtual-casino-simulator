// Verify the isolated Casino War ES module and locale resources without a server.

// Import strict assertions from the Node standard library.
import assert from 'node:assert/strict';
// Import UTF-8 file reading for locale parity checks.
import { readFile } from 'node:fs/promises';

// Provide the global expected by the shared i18n module during import.
globalThis.window = {};

// Import the isolated frontend after installing its minimal shared-module global.
const gameModule = await import('../../../../web/games/casino_war.js');
// Read the exported catalog contract.
const game = gameModule.CasinoWarGame;
// Assert the game id matches the proposed module descriptor.
assert.equal(game.id, 'casino_war');
// Assert catalog mounting remains callable.
assert.equal(typeof game.mount, 'function');
// Assert route changes can release module resources.
assert.equal(typeof game.unmount, 'function');

// Resolve the English game dictionary relative to this test file.
const englishUrl = new URL('../../../../web/i18n/en-US/games/casino_war.json', import.meta.url);
// Resolve the Russian game dictionary relative to this test file.
const russianUrl = new URL('../../../../web/i18n/ru-RU/games/casino_war.json', import.meta.url);
// Parse the English source strings.
const english = JSON.parse(await readFile(englishUrl, 'utf8'));
// Parse the Russian strings.
const russian = JSON.parse(await readFile(russianUrl, 'utf8'));
// Assert both required locales own the same keys.
assert.deepEqual(Object.keys(russian).sort(), Object.keys(english).sort());
// Assert the tie-decision primary action is translated in both locales.
assert.ok(english['controls.war'] && russian['controls.war']);

// Report one concise success line for worker validation logs.
console.log('Casino War frontend module tests passed.');
