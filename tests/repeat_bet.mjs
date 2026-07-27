// Exercise the catalog-wide repeat-bet source contract without opening a browser or listener.
import assert from 'node:assert/strict';
// Read every governed game module and paired locale resource from the exact checkout.
import { readFile } from 'node:fs/promises';
// Resolve portable repository paths from this test module.
import path from 'node:path';
// Convert the current module URL into a filesystem path.
import { fileURLToPath } from 'node:url';

// Resolve the exact checkout root.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Pin the complete approved catalog slice so a game cannot silently lose repeat coverage.
const repeatGames = [
  'acey_deucey', 'andar_bahar', 'big_six_wheel', 'bingo', 'boule',
  'caribbean_stud', 'casino_holdem', 'casino_war', 'chuck_a_luck', 'coin_pusher',
  'color_wheel', 'craps', 'crown_and_anchor', 'daily_draw_lab',
  'deuces_wild_video_poker', 'double_bonus_video_poker', 'dragon_tiger', 'fan_tan',
  'faro', 'four_card_poker', 'hi_lo', 'jacks_or_better_video_poker', 'joker_poker',
  'keno', 'let_it_ride', 'lucky_grid', 'marble_race', 'mississippi_stud',
  'multi_hand_video_poker', 'over_under_7', 'pachinko', 'pai_gow_poker',
  'pattern_draw', 'plinko', 'poker_dice', 'red_dog', 'scratch_cards', 'sic_bo',
  'slots', 'teen_patti', 'texas_holdem_practice_table', 'three_card_poker',
  'trente_et_quarante',
];
// Require exactly the forty-three games that lacked the pre-existing Roulette/Baccarat behavior.
assert.equal(repeatGames.length, 43);
// Reject duplicate identities that could disguise a missing catalog game.
assert.equal(new Set(repeatGames).size, 43);

// Extract one named function body with brace balancing so timer checks stay inside repeat only.
function functionBody(source, game) {
  // Locate either the synchronous or asynchronous repeat function declaration.
  const marker = source.search(/(?:async\s+)?function\s+repeat\s*\(/);
  // Fail with the exact missing game identity when repeat is absent.
  assert.notEqual(marker, -1, `${game}: repeat function missing`);
  // Locate the opening brace after the declaration.
  const opening = source.indexOf('{', marker);
  // Reject malformed declarations before scanning their body.
  assert.notEqual(opening, -1, `${game}: repeat function body missing`);
  // Track nested braces while walking the function source.
  let depth = 0;
  // Inspect each character from the function's opening brace.
  for (let index = opening; index < source.length; index += 1) {
    // Enter one nested block when an opening brace is found.
    if (source[index] === '{') depth += 1;
    // Leave one nested block when a closing brace is found.
    if (source[index] === '}') depth -= 1;
    // Return the complete function as soon as the outer declaration closes.
    if (depth === 0) return source.slice(marker, index + 1);
  }
  // Fail closed when malformed source never closes the function.
  assert.fail(`${game}: repeat function is unterminated`);
}

// Audit every governed game module and both installed locale domains.
for (const game of repeatGames) {
  // Read the exact production module under test.
  const source = await readFile(path.join(root, 'web', 'games', `${game}.js`), 'utf8');
  // Read the installed English game resource.
  const english = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'en-US', 'games', `${game}.json`), 'utf8'));
  // Read the installed Russian game resource.
  const russian = JSON.parse(await readFile(path.join(root, 'web', 'i18n', 'ru-RU', 'games', `${game}.json`), 'utf8'));
  // Preserve Marble Race's established action-domain key while standardizing every other game.
  const repeatKey = game === 'marble_race' ? 'action.repeat' : 'controls.repeat';
  // Require exact English product copy instead of a raw resource key or blank control.
  assert.equal(english[repeatKey], 'Repeat bet', `${game}: English repeat copy`);
  // Require exact Russian product copy instead of an English fallback.
  assert.equal(russian[repeatKey], 'Повторить ставку', `${game}: Russian repeat copy`);
  // Require one semantic button hook through the supported catalog selector patterns.
  assert.match(source, /<button[^>]+(?:data-action="repeat"|data-testid="[^"]*repeat[^"]*"|data-repeat(?:=|[\s>])|id="[^"]*[Rr]epeat[^"]*")/, `${game}: repeat button hook`);
  // Detect additive repeat selectors that were appended after an existing closing style tag.
  const trailingRepeatSelector = source.match(/<\/style>(\.[a-z0-9-]*repeat)\{/i);
  // Require affected modules to move that exact selector into a corrected style element before rendering.
  if (trailingRepeatSelector) {
    // Preserve the exact game-owned selector instead of accepting a generic replacement.
    assert.ok(source.includes(`replace('</style>${trailingRepeatSelector[1]}', '${trailingRepeatSelector[1]}')`), `${game}: repeat CSS correction`);
    // Count the correction helper declaration and its production render call.
    const safeStyleCalls = source.match(/\brepeatSafeStyles?Html\(\)/g) || [];
    // Prevent a dead helper from masking visible raw CSS in the generated route.
    assert.ok(safeStyleCalls.length >= 2, `${game}: repeat CSS correction wiring`);
  }
  // Preserve the fixed feedback lane for Teen Patti's bottom-most repeat control on mobile.
  if (game === 'teen_patti') assert.match(source, /@media \(max-width:640px\)\{\.tp-repeat\{width:calc\(100% - 160px\);max-width:calc\(100% - 160px\);\}\}/, `${game}: mobile feedback clearance`);
  // Extract only the game-owned repeat action for focused safety assertions.
  const repeatBody = functionBody(source, game);
  // Require every repeat action to depend on a previously committed wager snapshot.
  assert.match(repeatBody, /\blastBet\b/, `${game}: committed wager guard`);
  // Require the action to delegate through an existing game action instead of mutating a wallet.
  assert.match(repeatBody, /(?:await\s+|runAction\s*\()/, `${game}: shared action delegation`);
  // Reject parallel timers from the one-click repeat path.
  assert.doesNotMatch(repeatBody, /\b(?:setTimeout|setInterval|requestAnimationFrame)\s*\(/, `${game}: timer-free repeat`);
  // Require a busy, pending, active-round, or equivalent in-flight guard before replay.
  assert.match(repeatBody, /\b\w*(?:busy|pending|rolling|spinning)\w*\b/i, `${game}: in-flight guard`);
  // Count the declaration plus at least one control-dispatch call to the game-owned repeat function.
  const repeatCalls = source.match(/\brepeat\s*\(\s*\)/g) || [];
  // Accept direct property handlers, event listeners, or delegated action dispatch.
  const repeatWired = repeatCalls.length >= 2 || /onclick\s*=\s*(?:\(\)\s*=>\s*)?repeat\b/.test(source) || /addEventListener\(\s*['"]click['"]\s*,\s*repeat\b/.test(source);
  // Require production wiring without coupling the contract to one event style.
  assert.ok(repeatWired, `${game}: repeat click wiring`);
}

// Print one bounded success line for local and hosted diagnostics.
console.log(`Repeat-bet contract passed for ${repeatGames.length} games in en-US and ru-RU.`);
