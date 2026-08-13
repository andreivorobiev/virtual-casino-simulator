// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Keep the unsigned 32-bit range explicit so seeded samples normalize to [0, 1).
const UINT32_RANGE = 0x100000000;

// Convert supported seed inputs into one stable unsigned 32-bit value.
function normalizeSeed(seed) {
  // Preserve numeric seeds exactly within JavaScript's safe integer range.
  if (typeof seed === "number" && Number.isSafeInteger(seed)) return seed >>> 0;
  // Reject empty or unsupported seeds before hashing them.
  if (typeof seed !== "string" || seed.length === 0) throw new TypeError("seed must be a safe integer or non-empty string");
  let hash = 0x811c9dc5; // Start the deterministic FNV-1a string hash.
  // Fold every UTF-16 code unit into the seed hash.
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index); // Mix the current code unit into the hash.
    hash = Math.imul(hash, 0x01000193); // Keep multiplication deterministic in 32 bits.
  }
  return hash >>> 0; // Return the normalized unsigned seed.
}

// Validate a positive integer option used by dice helpers.
function requirePositiveInteger(name, value) {
  // Fail fast when a caller supplies an impossible die or dice count.
  if (!Number.isSafeInteger(value) || value < 1) throw new RangeError(`${name} must be a positive safe integer`);
  return value; // Return the validated value for expression-friendly use.
}

// Read one random sample while enforcing the standard [0, 1) generator contract.
function randomSample(random) {
  // Require an injectable function so tests and games share one deterministic seam.
  if (typeof random !== "function") throw new TypeError("random must be a function");
  const sample = Number(random()); // Coerce the generator result once for validation.
  // Reject invalid generators instead of producing biased or out-of-range faces.
  if (!Number.isFinite(sample) || sample < 0 || sample >= 1) throw new RangeError("random must return a finite number in [0, 1)");
  return sample; // Return the validated fractional sample.
}

// Create a compact Mulberry32 generator from a numeric or string seed.
export function createSeededRandom(seed) {
  let state = normalizeSeed(seed); // Store private generator state for this seeded sequence.
  // Return the deterministic hook consumed by the public grouped-dice helper.
  return function seededRandom() {
    state = (state + 0x6d2b79f5) >>> 0; // Advance the sequence by the algorithm constant.
    let value = state; // Copy state before applying the output mixing steps.
    value = Math.imul(value ^ (value >>> 15), value | 1); // Apply the first 32-bit mix.
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61); // Apply the second 32-bit mix.
    return ((value ^ (value >>> 14)) >>> 0) / UINT32_RANGE; // Normalize the mixed word to [0, 1).
  };
}

// Roll an ordered group of independent dice through the same random source.
export function rollDice({ count = 1, sides = 6, random = Math.random } = {}) {
  const validCount = requirePositiveInteger("count", count); // Validate the requested dice count.
  const validSides = requirePositiveInteger("sides", sides); // Validate the shared side count once.
  const rolls = []; // Preserve roll order for game engines and animation renderers.
  // Produce exactly the requested number of rolls from the injected source.
  for (let index = 0; index < validCount; index += 1) {
    rolls.push(Math.floor(randomSample(random) * validSides) + 1); // Append one validated one-based face.
  }
  return rolls; // Return the complete immutable-by-convention result sequence.
}
