// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build global Audio & Voice settings behind a dedicated Admin tab boundary. (AUDIO-001, AUDIO-007)
export function createAudioTab(dependencies) {
  // Capture the established audio persistence, voice, and presentation helpers.
  const {
    api, availableVoices, html, loadVoiceSettings, safe, saveVoiceSettings,
    setTitle, speak, t, toast, view,
  } = dependencies;

  // Render one checkbox setting with its accepted text label.
  function checkSetting(id, label, checked) {
    // Preserve the persisted boolean as the checked projection.
    const selected = checked ? 'checked' : '';
    // Return the exact compact control.
    return html`<label><input id="${safe(id)}" type="checkbox" ${selected}> ${safe(label)}</label>`;
  }

  // Render one bounded range setting.
  function rangeSetting(id, label, value) {
    // Preserve the accepted common volume range.
    return html`<label>${safe(label)}<input id="${safe(id)}" type="range" min="0" max="1" step="0.05" value="${safe(value)}"></label>`;
  }

  // Render one bounded numeric voice setting.
  function numberSetting(id, label, min, max, value) {
    // Preserve the accepted shared voice-step precision.
    return html`<label>${safe(label)}<input id="${safe(id)}" type="number" min="${safe(min)}" max="${safe(max)}" step="0.05" value="${safe(value)}"></label>`;
  }

  // Persist the existing audio settings payload.
  async function saveAudio() {
    // Collect all established boolean setting keys from checkboxes.
    const keys = [
      'master_enabled', 'sfx_enabled', 'voice_enabled', 'auto_nice_lady',
      'announce_roulette_results', 'announce_blackjack_results',
      'announce_baccarat_results', 'announce_bingo_calls', 'announce_keno_results',
    ];
    // Collect all established numeric setting keys from ranges and inputs.
    const nums = ['master_volume', 'sfx_volume', 'voice_volume', 'voice_rate', 'voice_pitch'];
    // Start with the installed voice selection.
    const payload = { preferred_voice_name: view.querySelector('#preferred_voice_name').value };
    // Add boolean and numeric values without changing the accepted payload shape.
    keys.forEach((key) => { payload[key] = view.querySelector(`#${key}`).checked; });
    nums.forEach((key) => { payload[key] = Number(view.querySelector(`#${key}`).value); });
    // Persist through the existing recovery-safe voice helper.
    await saveVoiceSettings(payload);
    // Preserve the established completion feedback.
    toast('Audio settings saved.', true);
  }

  // Speak one short sample with the latest persisted voice settings.
  async function previewVoice() {
    // Reload current settings before resolving the installed voice.
    await loadVoiceSettings();
    // Preserve the established Admin preview phrase and global channel.
    speak('Welcome to your virtual casino.', 'global');
  }

  // Render global sound and voice settings.
  async function audio() {
    // Set the existing Audio heading and helper copy.
    setTitle(t('nav.audio', {}, 'admin'), 'Global sound settings for all games.');
    // Load persisted settings and installed browser voices.
    const data = await api('/api/v1/admin/audio-settings');
    const settings = data.settings || {};
    const voices = availableVoices();
    // Build the three master enablement controls.
    const enablement = [
      checkSetting('master_enabled', 'Master sound', settings.master_enabled),
      checkSetting('sfx_enabled', 'SFX', settings.sfx_enabled),
      checkSetting('voice_enabled', 'Voice', settings.voice_enabled),
    ];
    // Build the three common volume controls.
    const volumes = [
      rangeSetting('master_volume', 'Master volume', settings.master_volume),
      rangeSetting('sfx_volume', 'SFX volume', settings.sfx_volume),
      rangeSetting('voice_volume', 'Voice volume', settings.voice_volume),
    ];
    // Render installed voice options after the automatic selection.
    const voiceOptions = voices.map((voice) => {
      // Preserve the exact selected voice identity.
      const selected = settings.preferred_voice_name === voice.name ? 'selected' : '';
      // Return one installed voice name and locale pair.
      return html`<option value="${safe(voice.name)}" ${selected}>${safe(voice.name)} (${safe(voice.lang)})</option>`;
    });
    const voice = html`<label>Voice<select id="preferred_voice_name"><option value="">Auto nice lady</option>${voiceOptions}</select></label>`;
    // Build rate, pitch, and preferred-voice controls.
    const voiceShape = [
      numberSetting('voice_rate', 'Rate', 0.5, 1.8, settings.voice_rate),
      numberSetting('voice_pitch', 'Pitch', 0.4, 2, settings.voice_pitch),
      checkSetting('auto_nice_lady', 'Prefer nice lady', settings.auto_nice_lady),
    ];
    // Build game announcement controls in their accepted order.
    const announcements = [
      checkSetting('announce_roulette_results', 'Roulette announcements', settings.announce_roulette_results),
      checkSetting('announce_blackjack_results', 'Blackjack announcements', settings.announce_blackjack_results),
      checkSetting('announce_baccarat_results', 'Baccarat announcements', settings.announce_baccarat_results),
      checkSetting('announce_bingo_calls', 'Bingo calls', settings.announce_bingo_calls),
      checkSetting('announce_keno_results', 'Keno results', settings.announce_keno_results),
    ];
    // Preserve distinct save and preview actions.
    const save = html`<button id="saveAudio" data-testid="admin-save-audio" class="gold">Save audio settings</button>`;
    const preview = html`<button id="previewVoice" data-testid="admin-preview-voice">Preview voice</button>`;
    const actions = html`<div class="row">${save}${preview}</div>`;
    // Replace the tab atomically without source-formatting whitespace.
    const controls = html`<div class="grid3">${enablement}</div><div class="grid3">${volumes}</div>${voice}<div class="grid3">${voiceShape}</div><div class="grid3">${announcements}</div>${actions}`;
    view.innerHTML = html`<section class="admin-card"><h3>Sound and voice</h3>${controls}</section>`;
    // Bind persistence and preview after rendering.
    view.querySelector('#saveAudio').onclick = saveAudio;
    view.querySelector('#previewVoice').onclick = previewVoice;
  }

  // Publish only the dispatcher-facing Audio renderer.
  return audio;
}
