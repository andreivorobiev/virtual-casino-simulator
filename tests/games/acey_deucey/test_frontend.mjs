// Validate Acey-Deucey frontend resources without shared registration.

// Import filesystem reads for local module/resource checks.
import fs from 'node:fs';
// Import strict assertions from the standard library.
import assert from 'node:assert/strict';

// Read the isolated browser module source.
const moduleSource = fs.readFileSync('web/games/acey_deucey.js', 'utf8');
// Read the English game resource file.
const en = JSON.parse(fs.readFileSync('web/i18n/en-US/games/acey_deucey.json', 'utf8'));
// Read the Russian game resource file.
const ru = JSON.parse(fs.readFileSync('web/i18n/ru-RU/games/acey_deucey.json', 'utf8'));
// Compare sorted resource keys for parity.
assert.deepEqual(Object.keys(ru).sort(), Object.keys(en).sort(), 'EN/RU Acey-Deucey resources must have identical keys');
// Verify the module exports the catalog-facing game object.
assert.match(moduleSource, /export const AceyDeuceyGame/, 'AceyDeuceyGame export is required');
// Verify the module points at the game-owned API root.
assert.match(moduleSource, /\/api\/v1\/games\/acey-deucey/, 'Acey-Deucey API root is required');
// Verify the stable readiness selector exists.
assert.match(moduleSource, /data-testid="acey-deucey"/, 'Acey-Deucey readiness selector is required');
// Verify the reduced-motion CSS path is present.
assert.match(moduleSource, /prefers-reduced-motion:reduce/, 'Reduced-motion CSS is required');
// Verify the module has no interval or timeout-owned animation loop.
assert.equal(/set(?:Interval|Timeout)\s*\(/.test(moduleSource), false, 'Acey-Deucey must not own timers');
// Verify Russian copy does not leak common English UI phrases.
for (const phrase of ['Deal boundaries', 'Play wager', 'Return table', 'Ready to deal']) {
  // Check every localized value for the prohibited English phrase.
  assert.equal(Object.values(ru).some(value => String(value).includes(phrase)), false, `Russian resource leaked English phrase: ${phrase}`);
}
