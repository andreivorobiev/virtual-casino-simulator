// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import API helpers so Admin tabs continue using the frozen v1 contract.
import { api, post } from './core/api.js';
// Import UI helpers for escaping user/server text and showing transient status.
import { safe, toast } from './core/ui.js';
// Import voice helpers so the existing Audio & Voice tab keeps its behavior.
import { availableVoices, loadVoiceSettings, saveVoiceSettings, speak } from './core/voice.js';
// Import i18n helpers so Admin can switch language without reloading or remounting.
import { applyTranslations, formatDate, formatMoney, formatNumber, getLocaleSettings, getLocaleState, initI18n, onLocaleChange, resetLocaleSettings, setLocale, t } from './core/i18n.js';

// Store current so refresh and locale rerendering preserve the active Admin tab.
let current = 'dashboard';
// Store view so tab renderers share the same Admin content target.
const view = document.getElementById('adminView');
// Store title so tab renderers can update the current heading.
const title = document.getElementById('adminTitle');
// Store subtitle so tab renderers can update the current explanatory line.
const subtitle = document.getElementById('adminSubtitle');
// Store plannedLanguageLabels so the scalability grid can show readable future slots.
const plannedLanguageLabels = { 'es-ES': 'Spanish', 'zh-CN': 'Chinese', 'hi-IN': 'Hindi', 'ar-SA': 'Arabic', 'pt-BR': 'Portuguese', 'bn-BD': 'Bengali', 'fr-FR': 'French', 'de-DE': 'German', 'ja-JP': 'Japanese', 'ko-KR': 'Korean', 'it-IT': 'Italian', 'tr-TR': 'Turkish', 'vi-VN': 'Vietnamese', 'pl-PL': 'Polish', 'nl-NL': 'Dutch', 'sv-SE': 'Swedish', 'th-TH': 'Thai', 'id-ID': 'Indonesian' };

// Define pre to render escaped JSON diagnostics.
const pre = object => `<pre class="logview">${safe(JSON.stringify(object, null, 2))}</pre>`;
// Define table to render escaped mini tables while preserving existing Admin density.
const table = (heads, rows) => `<table class="mini-table"><tr>${heads.map(head => `<th>${safe(head)}</th>`).join('')}</tr>${rows.join('')}</table>`;
// Define option to render a selected-safe select option.
const option = (value, label, selected) => `<option value="${safe(value)}" ${selected === value ? 'selected' : ''}>${safe(label)}</option>`;

// Define setTitle so each tab can update the Admin heading consistently.
function setTitle(text, helper = '') {
  // Set the heading to the localized tab title.
  title.textContent = text;
  // Set the helper text to the localized tab subtitle.
  subtitle.textContent = helper;
}

// Define activate so sidebar tabs preserve the existing single-view Admin model.
function activate(tab) {
  // Mark only the active tab with the gold style.
  document.querySelectorAll('[data-tab]').forEach(button => button.classList.toggle('gold', button.dataset.tab === tab));
  // Store the active tab for refresh and locale changes.
  current = tab;
  // Render the selected tab.
  load(tab);
}

// Define load so refresh, tabs, and locale changes route through one renderer.
async function load(tab = 'dashboard') {
  // Start protected logic so Admin errors stay inside the content pane.
  try {
    // Branch to the dashboard renderer.
    if (tab === 'dashboard') return dashboard();
    // Branch to the players/bots renderer.
    if (tab === 'players') return playersBots();
    // Branch to the ledger renderer.
    if (tab === 'ledger') return ledger();
    // Branch to the history renderer.
    if (tab === 'history') return history();
    // Branch to the telemetry renderer.
    if (tab === 'telemetry') return telemetry();
    // Branch to the game state renderer.
    if (tab === 'states') return states();
    // Branch to the audio renderer.
    if (tab === 'audio') return audio();
    // Branch to the browser-local language renderer.
    if (tab === 'language') return language();
    // Branch to the autoplay renderer.
    if (tab === 'autoplay') return autoplay();
    // Branch to the requirements renderer.
    if (tab === 'requirements') return requirements();
    // Branch to the test results renderer.
    if (tab === 'tests') return tests();
    // Branch to the system renderer.
    if (tab === 'system') return system();
  // Handle renderer failures by showing a local Admin error card.
  } catch (error) {
    // Render the error without throwing through the browser event loop.
    view.innerHTML = `<div class="admin-card danger"><h2>Admin error</h2><p>${safe(error.message)}</p></div>`;
  }
}

// Define dashboard to show the existing Admin overview cards and recent diagnostics.
async function dashboard() {
  // Set the localized dashboard title and subtitle.
  setTitle(t('dashboard.title', {}, 'admin'), t('dashboard.subtitle', {}, 'admin'));
  // Load the dashboard envelope data through the frozen Admin endpoint.
  const data = await api('/api/v1/admin/dashboard');
  // Store active autoplay sessions using the existing status set.
  const active = (data.autoplay_sessions || []).filter(session => ['running', 'stop_requested', 'paused', 'starting'].includes(session.status));
  // Render the dashboard without changing the existing API shape.
  view.innerHTML = `<div class="admin-card-grid"><div class="admin-card"><b>App</b><h2>${safe(data.app_version)}</h2></div><div class="admin-card"><b>${safe(t('nav.players', {}, 'admin'))}</b><h2>${formatNumber(data.players.length)}</h2></div><div class="admin-card"><b>Bots</b><h2>${formatNumber(data.bots.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.activeAutoplay', {}, 'admin'))}</b><h2>${formatNumber(active.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.errorsToday', {}, 'admin'))}</b><h2>${formatNumber((data.logs.errors || []).length)}</h2></div><div class="admin-card"><b>${safe(t('nav.requirements', {}, 'admin'))}</b><h2>${formatNumber(Object.values(data.requirement_counts || {}).reduce((sum, count) => sum + count, 0))}</h2></div></div><div class="admin-split"><section class="admin-card"><h3>${safe(t('dashboard.recentLedger', {}, 'admin'))}</h3>${table(['Time', 'Player', 'Game', 'Type', 'Amount'], (data.recent_ledger || []).slice(-12).reverse().map(row => `<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(row.game)}</td><td>${safe(row.transaction_type)}</td><td>${formatMoney(row.amount)}</td></tr>`))}</section><section class="admin-card"><h3>${safe(t('dashboard.recentErrors', {}, 'admin'))}</h3>${pre(data.logs.errors || [])}</section></div>`;
}

// Define playersBots to preserve bot controller editing in Admin.
async function playersBots() {
  // Set the localized players/bots title and subtitle.
  setTitle(t('players.title', {}, 'admin'), t('players.subtitle', {}, 'admin'));
  // Load the same dashboard payload used by the prior implementation.
  const data = await api('/api/v1/admin/dashboard');
  // Store capabilities so only bot-compatible games render strategy controls.
  const capabilities = data.bot_capabilities || {};
  // Store game options by filtering for bot-supported games.
  const gameOptions = Object.keys(capabilities).filter(game => capabilities[game].supports_bots);
  // Render players and editable bot controller settings.
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('nav.players', {}, 'admin'))}</h3>${table(['ID', 'Name', 'Type', 'Balance'], (data.players || []).map(player => `<tr><td>${safe(player.player_id)}</td><td>${safe(player.display_name)}</td><td>${safe(player.type)}</td><td>${formatMoney(player.balance)}</td></tr>`))}</section><section class="admin-card"><h3>Bot controllers</h3>${(data.bots || []).map(bot => `<div class="bot-edit" data-bot="${safe(bot.bot_id)}"><div class="row"><b>${safe(bot.display_name)}</b><label><input type="checkbox" class="bot-enabled" ${bot.enabled ? 'checked' : ''}> Enabled</label><span class="badge">${formatMoney(bot.balance)}</span></div>${gameOptions.map(game => `<div class="row"><label>${safe(game)} strategy <select class="bot-strategy" data-game="${safe(game)}">${capabilities[game].strategies.map(strategy => `<option value="${safe(strategy.id)}" ${bot.strategies?.[game] === strategy.id ? 'selected' : ''}>${safe(strategy.label)}</option>`).join('')}</select></label><label>Stake <input class="bot-stake" data-game="${safe(game)}" type="number" min="1" value="${safe(bot.stakes?.[game] || 5)}"></label></div>`).join('')}<button class="save-bot" data-bot="${safe(bot.bot_id)}">Save ${safe(bot.display_name)}</button></div>`).join('')}</section>`;
  // Bind save buttons after rendering each bot edit card.
  view.querySelectorAll('.save-bot').forEach(button => button.onclick = async () => saveBot(button));
}

// Define saveBot to submit one bot controller edit through the existing public endpoint.
async function saveBot(button) {
  // Store the nearest bot edit form for value collection.
  const box = button.closest('.bot-edit');
  // Store the bot id from the button dataset.
  const id = button.dataset.bot;
  // Store strategies so each game strategy selection can be submitted together.
  const strategies = {};
  // Store stakes so each game stake can be submitted together.
  const stakes = {};
  // Collect selected strategy ids by game.
  box.querySelectorAll('.bot-strategy').forEach(select => strategies[select.dataset.game] = select.value);
  // Collect numeric stake values by game.
  box.querySelectorAll('.bot-stake').forEach(input => stakes[input.dataset.game] = Number(input.value || 1));
  // Save the bot settings through the existing bot API.
  await post(`/api/v1/bots/${id}`, { enabled: box.querySelector('.bot-enabled').checked, strategies, stakes });
  // Show the existing success feedback.
  toast('Bot settings saved.', true);
  // Rerender players/bots so server-normalized values are visible.
  playersBots();
}

// Define ledger to show the transaction audit log.
async function ledger() {
  // Set the localized ledger title and subtitle.
  setTitle(t('ledger.title', {}, 'admin'), t('ledger.subtitle', {}, 'admin'));
  // Load ledger rows through the existing Admin endpoint.
  const data = await api('/api/v1/admin/ledger?limit=500');
  // Render ledger rows using the active locale's money formatter.
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('ledger.title', {}, 'admin'))}</h3>${table(['Time', 'Player', 'Game', 'Round', 'Type', 'Amount', 'Before', 'After'], (data.ledger || []).slice().reverse().map(row => `<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(row.game)}</td><td>${safe(row.round_id)}</td><td>${safe(row.transaction_type)}</td><td>${formatMoney(row.amount)}</td><td>${formatMoney(row.balance_before)}</td><td>${formatMoney(row.balance_after)}</td></tr>`))}</section>`;
}

// Define history to show cross-game history rows.
async function history() {
  // Set the existing history title and subtitle.
  setTitle('History', 'Cross-game CSV history rows.');
  // Load history rows through the existing Admin endpoint.
  const data = await api('/api/v1/admin/history?limit=500');
  // Render history diagnostics.
  view.innerHTML = `<section class="admin-card"><h3>History</h3>${pre(data.history || [])}</section>`;
}

// Define telemetry to show server and client logs.
async function telemetry() {
  // Set the existing telemetry title and subtitle.
  setTitle('Telemetry', 'Application, error, and browser-client logs.');
  // Load app logs through the existing Admin endpoint.
  const app = await api('/api/v1/admin/logs?kind=app&limit=200');
  // Load error logs through the existing Admin endpoint.
  const errors = await api('/api/v1/admin/logs?kind=errors&limit=200');
  // Load browser client logs through the existing Admin endpoint.
  const client = await api('/api/v1/admin/logs?kind=client&limit=200');
  // Render the three log panes.
  view.innerHTML = `<div class="admin-split"><section class="admin-card"><h3>App logs</h3>${pre(app.logs)}</section><section class="admin-card"><h3>Error logs</h3>${pre(errors.logs)}</section></div><section class="admin-card"><h3>Client logs</h3>${pre(client.logs)}</section>`;
}

// Define states to show isolated game state files.
async function states() {
  // Set the existing states title and subtitle.
  setTitle('Game States', 'Isolated game state files.');
  // Load game states through the existing Admin endpoint.
  const data = await api('/api/v1/admin/game-states');
  // Render game state diagnostics.
  view.innerHTML = `<section class="admin-card"><h3>States</h3>${pre(data.states)}</section>`;
}

// Define audio to preserve global sound and voice settings.
async function audio() {
  // Set the existing audio title and subtitle.
  setTitle(t('nav.audio', {}, 'admin'), 'Global sound settings for all games.');
  // Load persisted audio settings through the existing Admin endpoint.
  const data = await api('/api/v1/admin/audio-settings');
  // Store settings with a safe empty fallback.
  const settings = data.settings || {};
  // Store browser voices so the voice select can show installed options.
  const voices = availableVoices();
  // Render the existing Audio & Voice controls.
  view.innerHTML = `<section class="admin-card"><h3>Sound and voice</h3><div class="grid3"><label><input id="master_enabled" type="checkbox" ${settings.master_enabled ? 'checked' : ''}> Master sound</label><label><input id="sfx_enabled" type="checkbox" ${settings.sfx_enabled ? 'checked' : ''}> SFX</label><label><input id="voice_enabled" type="checkbox" ${settings.voice_enabled ? 'checked' : ''}> Voice</label></div><div class="grid3"><label>Master volume<input id="master_volume" type="range" min="0" max="1" step="0.05" value="${safe(settings.master_volume)}"></label><label>SFX volume<input id="sfx_volume" type="range" min="0" max="1" step="0.05" value="${safe(settings.sfx_volume)}"></label><label>Voice volume<input id="voice_volume" type="range" min="0" max="1" step="0.05" value="${safe(settings.voice_volume)}"></label></div><label>Voice<select id="preferred_voice_name"><option value="">Auto nice lady</option>${voices.map(voice => `<option value="${safe(voice.name)}" ${settings.preferred_voice_name === voice.name ? 'selected' : ''}>${safe(voice.name)} (${safe(voice.lang)})</option>`).join('')}</select></label><div class="grid3"><label>Rate<input id="voice_rate" type="number" min="0.5" max="1.8" step="0.05" value="${safe(settings.voice_rate)}"></label><label>Pitch<input id="voice_pitch" type="number" min="0.4" max="2" step="0.05" value="${safe(settings.voice_pitch)}"></label><label><input id="auto_nice_lady" type="checkbox" ${settings.auto_nice_lady ? 'checked' : ''}> Prefer nice lady</label></div><div class="grid3"><label><input id="announce_roulette_results" type="checkbox" ${settings.announce_roulette_results ? 'checked' : ''}> Roulette announcements</label><label><input id="announce_blackjack_results" type="checkbox" ${settings.announce_blackjack_results ? 'checked' : ''}> Blackjack announcements</label><label><input id="announce_baccarat_results" type="checkbox" ${settings.announce_baccarat_results ? 'checked' : ''}> Baccarat announcements</label><label><input id="announce_bingo_calls" type="checkbox" ${settings.announce_bingo_calls ? 'checked' : ''}> Bingo calls</label><label><input id="announce_keno_results" type="checkbox" ${settings.announce_keno_results ? 'checked' : ''}> Keno results</label></div><div class="row"><button id="saveAudio" data-testid="admin-save-audio" class="gold">Save audio settings</button><button id="previewVoice" data-testid="admin-preview-voice">Preview voice</button></div></section>`;
  // Bind the audio save action after rendering.
  view.querySelector('#saveAudio').onclick = saveAudio;
  // Bind the voice preview action after rendering.
  view.querySelector('#previewVoice').onclick = previewVoice;
}

// Define saveAudio to persist the existing audio settings payload.
async function saveAudio() {
  // Store boolean setting keys that are read from checkboxes.
  const keys = ['master_enabled', 'sfx_enabled', 'voice_enabled', 'auto_nice_lady', 'announce_roulette_results', 'announce_blackjack_results', 'announce_baccarat_results', 'announce_bingo_calls', 'announce_keno_results'];
  // Store numeric setting keys that are read from ranges or number inputs.
  const nums = ['master_volume', 'sfx_volume', 'voice_volume', 'voice_rate', 'voice_pitch'];
  // Store payload with the selected voice name.
  const payload = { preferred_voice_name: view.querySelector('#preferred_voice_name').value };
  // Add checkbox values to the payload.
  keys.forEach(key => payload[key] = view.querySelector(`#${key}`).checked);
  // Add numeric values to the payload.
  nums.forEach(key => payload[key] = Number(view.querySelector(`#${key}`).value));
  // Persist settings through the existing voice helper.
  await saveVoiceSettings(payload);
  // Show existing save feedback.
  toast('Audio settings saved.', true);
}

// Define previewVoice to speak a short sample with the saved voice settings.
async function previewVoice() {
  // Load latest settings before previewing speech.
  await loadVoiceSettings();
  // Speak the existing Admin preview phrase.
  speak('Welcome to your virtual casino.', 'global');
}

// Define localeOptions to render installed locale options.
function localeOptions(selected) {
  // Store state so manifest locales drive the select list.
  const state = getLocaleState();
  // Return installed locale options with native labels.
  return state.locales.map(locale => option(locale.id, `${locale.nativeLabel} (${locale.id})`, selected)).join('');
}

// Define formatLocaleOptions to render browser and installed format options.
function formatLocaleOptions(selected) {
  // Store state so installed locales stay in sync with the manifest.
  const state = getLocaleState();
  // Store browser option before installed locale options.
  const browser = option('browser', t('language.browserDefault', {}, 'admin'), selected);
  // Return browser plus installed locale options.
  return browser + state.locales.map(locale => option(locale.id, `${locale.nativeLabel} (${locale.id})`, selected)).join('');
}

// Define languageCards to render installed locale readiness cards.
function languageCards(selected) {
  // Store state so installed locale metadata drives the cards.
  const state = getLocaleState();
  // Return one compact card per installed locale.
  return state.locales.map(locale => `<article class="bot-edit" data-locale-card="${safe(locale.id)}"><div class="row"><h3 style="margin-right:auto">${safe(locale.nativeLabel)}</h3><span class="badge">${safe(locale.id === selected ? 'active' : 'ready')}</span></div><p class="muted">${safe(locale.id === 'ru-RU' ? t('language.russianDescription', {}, 'admin') : t('language.englishDescription', {}, 'admin'))}</p><div class="row"><span class="badge">${safe(t('language.uiReady', {}, 'admin'))}</span><span class="badge">${safe(locale.voiceReady ? 'Voice ready' : 'Voice check')}</span><span class="badge">${safe(locale.dir.toUpperCase())}</span></div></article>`).join('');
}

// Define plannedLanguageGrid to render future top-20 language slots.
function plannedLanguageGrid() {
  // Store state so planned locales come from the manifest.
  const state = getLocaleState();
  // Store installed locale labels before future planned labels.
  const installed = state.locales.map(locale => `<span class="badge">${safe(locale.nativeLabel)}</span>`).join('');
  // Store planned locale labels for future expansion.
  const planned = state.plannedLocales.map(locale => `<span class="badge">${safe(plannedLanguageLabels[locale] || locale)}</span>`).join('');
  // Return installed and planned labels in a dense grid.
  return `<div class="grid4">${installed}${planned}</div>`;
}

// Define diagnosticsTable to render current runtime diagnostic values.
function diagnosticsTable(state) {
  // Return diagnostics in the same mini-table style as other Admin views.
  return table([t('language.diagnostics', {}, 'admin'), 'Value'], [`<tr><td>${safe(t('language.resolvedLocale', {}, 'admin'))}</td><td data-testid="admin-locale-state">${safe(state.locale)}</td></tr>`, `<tr><td>${safe(t('language.fallbackLocale', {}, 'admin'))}</td><td>${safe(state.fallbackLocale)}</td></tr>`, `<tr><td>${safe(t('language.loadedDomains', {}, 'admin'))}</td><td>${safe(state.loadedDomains.join(', '))}</td></tr>`, `<tr><td>${safe(t('language.missingKeys', {}, 'admin'))}</td><td>${formatNumber(state.missingKeyCount)}</td></tr>`]);
}

// Define language to render browser-local language and locale controls.
async function language() {
  // Set the localized language title and subtitle.
  setTitle(t('language.title', {}, 'admin'), t('language.subtitle', {}, 'admin'));
  // Store current runtime state for diagnostics and selected values.
  const state = getLocaleState();
  // Store saved settings so controls reflect browser-local preferences.
  const settings = getLocaleSettings();
  // Store selected language using the resolved locale when browser default is active.
  const selectedLanguage = settings.useBrowserLocale ? state.locale : settings.language;
  // Store selected format using browser sentinel when that preference is active.
  const selectedFormat = settings.formatLocale || state.formatLocale;
  // Render language cards, settings, previews, and diagnostics.
  view.innerHTML = `<div class="admin-split"><section class="admin-card"><div class="row"><h3 style="margin-right:auto">${safe(t('language.availableTitle', {}, 'admin'))}</h3><span class="badge">${safe(t('language.readyCount', {}, 'admin'))}</span></div><div class="grid2">${languageCards(selectedLanguage)}</div><h3>${safe(t('language.top20Title', {}, 'admin'))}</h3>${plannedLanguageGrid()}</section><section class="admin-card"><h3>${safe(t('language.localeSettings', {}, 'admin'))}</h3><div class="grid2"><label>${safe(t('language.displayLanguage', {}, 'admin'))}<select id="admin_language" data-testid="admin-language-select">${localeOptions(selectedLanguage)}</select></label><label>${safe(t('language.formatLocale', {}, 'admin'))}<select id="admin_format_locale" data-testid="admin-format-locale-select">${formatLocaleOptions(selectedFormat)}</select></label></div><label><input id="admin_use_browser" type="checkbox" ${settings.useBrowserLocale ? 'checked' : ''}> ${safe(t('language.useBrowser', {}, 'admin'))}</label><label><input id="admin_persist_browser" type="checkbox" checked> ${safe(t('language.persistBrowser', {}, 'admin'))}</label><div class="result-box"><p data-testid="admin-money-preview">${safe(t('language.previewBalance', { amount: formatMoney(5030) }, 'admin'))}</p><p>${safe(t('language.datePreview', {}, 'admin'))}: ${safe(formatDate(new Date(), { dateStyle: 'medium', timeStyle: 'short' }))}</p></div><div class="row"><button id="admin_apply_locale" data-testid="admin-locale-apply" class="gold">${safe(t('language.apply', {}, 'admin'))}</button><button id="admin_save_locale" data-testid="admin-locale-save">${safe(t('language.saveBrowser', {}, 'admin'))}</button><button id="admin_reset_locale" data-testid="admin-locale-reset">${safe(t('language.resetBrowser', {}, 'admin'))}</button><button id="admin_preview_lobby">${safe(t('actions.previewLobby'))}</button></div>${diagnosticsTable(state)}<h3>${safe(t('language.stringPreview', {}, 'admin'))}</h3><div class="bot-edit"><b>English</b><p>Choose your table. All games use fake money only. Ledger-backed outcomes are visible in Admin.</p></div><div class="bot-edit"><b>Русский</b><p>Выберите стол. Все игры используют только условные деньги. Результаты с учётом ledger видны в Admin.</p></div><div class="bot-edit"><b>${safe(t('language.fallback', {}, 'admin'))}</b><p>${safe(t('language.fallbackDescription', {}, 'admin'))}</p></div></section></div>`;
  // Bind language form events after rendering.
  bindLanguageControls();
}

// Define bindLanguageControls to attach Language/Locale button behavior.
function bindLanguageControls() {
  // Store language select for apply and save actions.
  const languageSelect = view.querySelector('#admin_language');
  // Store format select for number/date formatting.
  const formatSelect = view.querySelector('#admin_format_locale');
  // Store browser-default checkbox for locale resolution.
  const browserToggle = view.querySelector('#admin_use_browser');
  // Store persist checkbox for browser-local save behavior.
  const persistToggle = view.querySelector('#admin_persist_browser');
  // Define syncDisabled so browser-default mode communicates that language is resolved.
  const syncDisabled = () => languageSelect.disabled = browserToggle.checked;
  // Bind browser toggle changes to update the language select disabled state.
  browserToggle.onchange = syncDisabled;
  // Apply the initial disabled state.
  syncDisabled();
  // Bind Apply Now to switch in memory and optionally persist to this browser.
  view.querySelector('#admin_apply_locale').onclick = () => saveLocale(languageSelect.value, formatSelect.value, browserToggle.checked, persistToggle.checked);
  // Bind Save Browser Default to persist the selected language and format.
  view.querySelector('#admin_save_locale').onclick = () => saveLocale(languageSelect.value, formatSelect.value, browserToggle.checked, true);
  // Bind Reset to restore browser-default resolution.
  view.querySelector('#admin_reset_locale').onclick = resetLanguage;
  // Bind Preview Lobby to navigate without changing saved settings.
  view.querySelector('#admin_preview_lobby').onclick = () => location.href = '/';
}

// Define saveLocale to switch locale without navigating away from the Admin tab.
async function saveLocale(language, nextFormat, useBrowser, persist) {
  // Switch runtime locale and formatting in place.
  await setLocale(language, { persistLocal: persist, nextFormatLocale: nextFormat, nextUseBrowserLocale: useBrowser });
  // Show localized feedback after the switch has completed.
  toast(t('language.saved', {}, 'admin'), true);
}

// Define resetLanguage to return Admin to browser-default locale resolution.
async function resetLanguage() {
  // Reset runtime and browser-local settings through the i18n helper.
  await resetLocaleSettings();
  // Show localized feedback after reset.
  toast(t('language.saved', {}, 'admin'), true);
}

// Define autoplay to preserve existing Admin autoplay controls.
async function autoplay() {
  // Set the localized autoplay title and subtitle.
  setTitle(t('autoplay.title', {}, 'admin'), t('autoplay.subtitle', {}, 'admin'));
  // Load autoplay sessions through the existing Admin endpoint.
  const data = await api('/api/v1/admin/autoplay');
  // Render sessions and the existing Stop All action.
  view.innerHTML = `<section class="admin-card"><div class="row"><h3 style="margin-right:auto">Sessions</h3><button id="stopAllAuto" data-testid="admin-stop-all-auto" class="danger">${safe(t('autoplay.stopAll', {}, 'admin'))}</button></div>${table(['ID', 'Game', 'Player', 'Status', 'Speed', 'Completed', 'Limit', 'Updated'], (data.sessions || []).slice().reverse().map(session => `<tr><td>${safe(session.autoplay_id)}</td><td>${safe(session.game_id)}</td><td>${safe(session.player_id)}</td><td>${safe(session.status)}</td><td>${safe(session.speed)}</td><td>${safe(session.rounds_completed)}</td><td>${safe(session.round_limit)}</td><td>${safe(session.updated_at)}</td></tr>`))}</section>`;
  // Bind Stop All after rendering.
  view.querySelector('#stopAllAuto').onclick = async () => { await post('/api/v1/admin/autoplay/stop-all', {}); toast('Stop requested for all autoplay sessions.', true); autoplay(); };
}

// Define requirements to show requirement coverage.
async function requirements() {
  // Set the existing requirements title and subtitle.
  setTitle(t('nav.requirements', {}, 'admin'), 'Numbered requirement registry and validation mapping.');
  // Load requirements through the existing Admin endpoint.
  const data = await api('/api/v1/admin/requirements');
  // Render requirement rows.
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('nav.requirements', {}, 'admin'))}</h3>${table(['ID', 'Module', 'Description', 'Status', 'Tests'], (data.requirements || []).map(req => `<tr><td>${safe(req.id)}</td><td>${safe(req.module)}</td><td>${safe(req.description)}</td><td>${safe(req.status)}</td><td>${safe([...(req.api_tests || []), ...(req.browser_tests || [])].join(', '))}</td></tr>`))}</section>`;
}

// Define tests to show latest test results.
async function tests() {
  // Set the existing tests title and subtitle.
  setTitle(t('nav.tests', {}, 'admin'), 'Latest API/browser test results.');
  // Load latest test results through the existing Admin endpoint.
  const data = await api('/api/v1/admin/test-results');
  // Render test diagnostics.
  view.innerHTML = `<section class="admin-card"><h3>Latest results</h3>${pre(data.results)}</section>`;
}

// Define system to show module revisions and raw overview data.
async function system() {
  // Set the localized system title and subtitle.
  setTitle(t('system.title', {}, 'admin'), t('system.subtitle', {}, 'admin'));
  // Load dashboard overview through the existing Admin endpoint.
  const data = await api('/api/v1/admin/dashboard');
  // Render module revisions and raw diagnostics.
  view.innerHTML = `<section class="admin-card"><h3>Module revisions</h3>${table(['Module', 'Revision'], (data.module_revisions || []).map(module => `<tr><td>${safe(module.module)}</td><td>${safe(module.revision)}</td></tr>`))}</section><section class="admin-card"><h3>Raw overview</h3>${pre(data)}</section>`;
}

// Define bindChrome to attach static Admin chrome event handlers.
function bindChrome() {
  // Bind every sidebar tab to the shared activator.
  document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => activate(button.dataset.tab));
  // Bind refresh to rerender the current tab.
  document.getElementById('refreshAdmin').onclick = () => load(current);
  // Bind Back to Casino without inline HTML handlers.
  document.getElementById('backToCasino').onclick = () => location.href = '/';
}

// Define start to initialize i18n before the first Admin render.
async function start() {
  // Load common and Admin dictionaries before rendering text.
  await initI18n({ domains: ['admin'] });
  // Apply declarative translations to static Admin chrome.
  applyTranslations(document);
  // Bind Admin chrome controls after translations are ready.
  bindChrome();
  // Subscribe to locale changes so the current tab rerenders in place.
  onLocaleChange(() => { applyTranslations(document); load(current); });
  // Render the initial dashboard tab.
  load('dashboard');
}

// Start the Admin module.
start();
