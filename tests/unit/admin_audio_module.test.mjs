// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import strict assertions for global Admin audio verification. (AUDIO-001, AUDIO-007)
import assert from "node:assert/strict";
// Import repository file access for exact boundary assertions.
import { readFile } from "node:fs/promises";
// Import the dependency-free Node test runner.
import test from "node:test";
// Import URL conversion for repository-relative paths.
import { fileURLToPath } from "node:url";
// Import the extracted Audio factory.
import { createAudioTab } from "../../web/admin/audio.js";

// Resolve and read the reviewed source boundaries once.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
const MODULE_SOURCE = await readFile(`${ROOT}/web/admin/audio.js`, "utf8");
// Render nested arrays and ordinary values deterministically.
const renderValue = value => Array.isArray(value) ? value.map(renderValue).join("") : String(value ?? "");
// Compose compact fixture markup.
const html = (strings, ...values) => strings.reduce((markup, segment, index) => (
  // Append one literal segment and following substitution.
  markup + segment + (index < values.length ? renderValue(values[index]) : "")
), "");

// Verify every accepted Audio & Voice control survives extraction.
test("AUDIO-001 preserves Admin audio controls after extraction", async () => {
  // Preserve stable save and preview controls.
  const controls = new Map();
  // Model only the DOM seams owned by the renderer.
  const view = {
    innerHTML: "",
    querySelector: (selector) => {
      // Reuse one plain control per selector.
      if (!controls.has(selector)) controls.set(selector, {});
      return controls.get(selector);
    },
  };
  // Create the production renderer around one persisted settings document.
  const renderAudio = createAudioTab({
    api: async () => ({ settings: {
      master_enabled: true,
      sfx_enabled: true,
      voice_enabled: true,
      master_volume: 1,
      sfx_volume: 0.8,
      voice_volume: 0.7,
      preferred_voice_name: "Voice One",
      voice_rate: 1,
      voice_pitch: 1,
      auto_nice_lady: true,
      announce_roulette_results: true,
      announce_blackjack_results: true,
      announce_baccarat_results: true,
      announce_bingo_calls: true,
      announce_keno_results: true,
    } }),
    availableVoices: () => [{ name: "Voice One", lang: "en-US" }],
    html,
    loadVoiceSettings: async () => {},
    safe: value => String(value ?? ""),
    saveVoiceSettings: async () => {},
    setTitle: () => {},
    speak: () => {},
    t: key => key,
    toast: () => {},
    view,
  });
  // Execute one exact settings render.
  await renderAudio();
  // Preserve all established settings identities and action hooks.
  for (const marker of [
    "master_enabled", "sfx_enabled", "voice_enabled", "master_volume", "sfx_volume",
    "voice_volume", "preferred_voice_name", "voice_rate", "voice_pitch", "auto_nice_lady",
    "announce_roulette_results", "announce_blackjack_results", "announce_baccarat_results",
    "announce_bingo_calls", "announce_keno_results", "admin-save-audio", "admin-preview-voice",
  ]) {
    // Require every accepted Audio & Voice control.
    assert.ok(view.innerHTML.includes(marker), marker);
  }
  // Preserve installed voice selection and locale evidence.
  assert.ok(view.innerHTML.includes('value="Voice One" selected'));
  assert.ok(view.innerHTML.includes("Voice One (en-US)"));
});

// Verify the source boundary remains compact and helper-complete.
test("AUDIO-007 keeps the Audio module boundary reviewable", () => {
  // Require one dispatcher import and reject retired implementations.
  assert.equal((ADMIN_SOURCE.match(/from '.\/admin\/audio\.js'/g) || []).length, 1);
  for (const name of ["audio", "saveAudio", "previewVoice"]) {
    // Require each implementation to live only in the extracted module.
    assert.equal(ADMIN_SOURCE.includes(`function ${name}(`), false, name);
  }
  // Preserve the exact dispatcher route and settings endpoint.
  assert.equal((ADMIN_SOURCE.match(/if \(tab === 'audio'\) return audio\(\);/g) || []).length, 1);
  assert.ok(MODULE_SOURCE.includes("/api/v1/admin/audio-settings"));
  // Preserve voice persistence and preview helper use.
  for (const helper of ["saveVoiceSettings", "loadVoiceSettings", "speak("]) {
    // Bind each reviewed helper to the extracted module.
    assert.ok(MODULE_SOURCE.includes(helper), helper);
  }
  // Keep every Audio source line within the governed review-width ceiling.
  assert.ok(Math.max(...MODULE_SOURCE.split(/\r?\n/).map(line => line.length)) <= 200);
});
