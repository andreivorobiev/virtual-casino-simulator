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
// Store lastUserPassword so Admin can see the latest one-time credential after rerender.
let lastUserPassword = '';
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

// Define humanLabel to turn API event enums into concise Admin-facing labels.
const humanLabel = value => String(value || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
// Define emptyState to replace raw empty arrays with a calm, actionable Admin message.
const emptyState = (titleText, detailText, testId = '') => `<div class="admin-empty-state"${testId ? ` data-testid="${safe(testId)}"` : ''}><div><strong>${safe(titleText)}</strong><p>${safe(detailText)}</p></div></div>`;

// Define eventList to present telemetry records with readable event labels and stable empty states.
function eventList(events, emptyTitle, emptyDetail, testId, hideTechnicalDetails = false) {
  // Store only object records so malformed diagnostics never leak as raw values.
  const records = Array.isArray(events) ? events.filter(event => event && typeof event === 'object') : [];
  // Return the polished empty state when this event stream has no records.
  if (!records.length) return emptyState(emptyTitle, emptyDetail, testId);
  // Build newest records first with internal event enums converted to human labels.
  const rows = records.slice().reverse().map(event => {
    // Store display details without repeating raw event, level, timestamp, or traceback fields.
    const details = hideTechnicalDetails ? 'An application error was recorded. Review the local service log for technical details.' : Object.entries(event).filter(([key]) => !['event', 'level', 'ts', 'traceback'].includes(key)).map(([key, value]) => `${humanLabel(key)}: ${typeof value === 'object' ? JSON.stringify(value) : value}`).join(' | ');
    // Return one accessible event summary row.
    return `<article class="admin-event"><strong>${safe(humanLabel(event.event || event.level || 'System event'))}</strong><p>${safe(details || 'Recorded successfully.')}</p><time>${safe(event.ts || 'Time unavailable')}</time></article>`;
  }).join(''); // Finish the event-card markup before wrapping the list.
  // Return the complete readable event list.
  return `<div class="admin-event-list" data-testid="${safe(testId)}">${rows}</div>`;
}

// Define isActiveTab to guard async tab renders against visible sidebar state.
function isActiveTab(tab) {
  // Return whether the requested tab is currently highlighted in the Admin sidebar.
  return document.querySelector(`[data-tab="${tab}"]`)?.classList.contains('gold');
}

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
    // Branch to the Admin beta-user renderer.
    if (tab === 'users') return users();
    // Branch to the ledger renderer.
    if (tab === 'ledger') return ledger();
    // Branch to the history renderer.
    if (tab === 'history') return history();
    // Branch to the telemetry renderer.
    if (tab === 'telemetry') return telemetry();
    // Branch to the authenticated Operations renderer.
    if (tab === 'operations') return operations();
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
    // Render a human recovery state without exposing raw transport or server diagnostics.
    view.innerHTML = `<section class="admin-card danger" data-testid="admin-load-error"><h2>Unable to load this Admin view</h2><p>The requested information is temporarily unavailable. Check that the local casino service is running, then use Refresh to try again.</p></section>`;
  }
}

// Define dashboard to show the existing Admin overview cards and recent diagnostics.
async function dashboard() {
  // Set the localized dashboard title and subtitle.
  setTitle(t('dashboard.title', {}, 'admin'), t('dashboard.subtitle', {}, 'admin'));
  // Load the dashboard envelope data through the frozen Admin endpoint.
  const data = await api('/api/v1/admin/dashboard');
  // Stop stale dashboard responses from overwriting a newer active tab.
  if (!isActiveTab('dashboard')) return;
  // Store active autoplay sessions using the existing status set.
  const active = (data.autoplay_sessions || []).filter(session => ['running', 'stop_requested', 'paused', 'starting'].includes(session.status));
  // Render the dashboard without changing the existing API shape.
  view.innerHTML = `<div class="admin-card-grid"><div class="admin-card"><b>App</b><h2>${safe(data.app_version)}</h2></div><div class="admin-card"><b>${safe(t('nav.players', {}, 'admin'))}</b><h2>${formatNumber(data.players.length)}</h2></div><div class="admin-card"><b>Bots</b><h2>${formatNumber(data.bots.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.activeAutoplay', {}, 'admin'))}</b><h2>${formatNumber(active.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.errorsToday', {}, 'admin'))}</b><h2>${formatNumber((data.logs.errors || []).length)}</h2></div><div class="admin-card"><b>${safe(t('nav.requirements', {}, 'admin'))}</b><h2>${formatNumber(Object.values(data.requirement_counts || {}).reduce((sum, count) => sum + count, 0))}</h2></div></div><div class="admin-split"><section class="admin-card"><h3>${safe(t('dashboard.recentLedger', {}, 'admin'))}</h3>${(data.recent_ledger || []).length ? table(['Time', 'Player', 'Game', 'Type', 'Amount'], data.recent_ledger.slice(-12).reverse().map(row => `<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(humanLabel(row.game))}</td><td>${safe(humanLabel(row.transaction_type))}</td><td>${formatMoney(row.amount)}</td></tr>`)) : emptyState('No recent token activity', 'Ledger events will appear here after a wager, payout, refund, or token adjustment.', 'admin-ledger-empty')}</section><section class="admin-card"><h3>${safe(t('dashboard.recentErrors', {}, 'admin'))}</h3>${eventList(data.logs.errors, 'No recent errors', 'The local casino has not recorded any application errors today.', 'admin-errors-empty', true)}</section></div>`;
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
  // Read the fixed funded-account allocation published by the Admin service.
  const practiceAccounts = data.practice_opponents || [];
  // Read append-only practice-opponent ledger activity for audit presentation.
  const practiceActivity = data.practice_opponent_activity || [];
  // Map stable controller action ids to localized Admin audit labels.
  const practiceActionLabels = {
    fund_account: t('players.actionFund', {}, 'admin'), // Localize one-time account seeding.
    reserve_stack: t('players.actionReserve', {}, 'admin'), // Localize the maximum hand escrow debit.
    refund_stack: t('players.actionRefund', {}, 'admin'), // Localize unused escrow return.
    settle_payout: t('players.actionPayout', {}, 'admin'), // Localize terminal opponent winnings.
  };
  // Render players and editable bot controller settings.
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('nav.players', {}, 'admin'))}</h3>${table(['ID', 'Name', 'Type', 'Balance'], (data.players || []).map(player => `<tr><td>${safe(player.player_id)}</td><td>${safe(player.display_name)}</td><td>${safe(player.type)}</td><td>${formatMoney(player.balance)}</td></tr>`))}</section><section class="admin-card"><h3>Bot controllers</h3>${(data.bots || []).map(bot => `<div class="bot-edit" data-bot="${safe(bot.bot_id)}"><div class="row"><b>${safe(bot.display_name)}</b><label><input type="checkbox" class="bot-enabled" ${bot.enabled ? 'checked' : ''}> Enabled</label><span class="badge">${formatMoney(bot.balance)}</span></div>${gameOptions.map(game => `<div class="row"><label>${safe(game)} strategy <select class="bot-strategy" data-game="${safe(game)}">${capabilities[game].strategies.map(strategy => `<option value="${safe(strategy.id)}" ${bot.strategies?.[game] === strategy.id ? 'selected' : ''}>${safe(strategy.label)}</option>`).join('')}</select></label><label>Stake <input class="bot-stake" data-game="${safe(game)}" type="number" min="1" value="${safe(bot.stakes?.[game] || 5)}"></label></div>`).join('')}<button class="save-bot" data-bot="${safe(bot.bot_id)}">Save ${safe(bot.display_name)}</button></div>`).join('')}</section><section class="admin-card" data-testid="practice-opponent-admin"><div class="row"><div><h3>${safe(t('players.practiceTitle', {}, 'admin'))}</h3><p>${safe(t('players.practiceSubtitle', {}, 'admin'))}</p></div><button id="fund_practice_opponents" data-testid="fund-practice-opponents">${safe(t('players.fundPractice', {}, 'admin'))}</button></div>${table([t('players.seat', {}, 'admin'), t('players.account', {}, 'admin'), t('players.policy', {}, 'admin'), t('players.balance', {}, 'admin')], practiceAccounts.map(account => `<tr data-testid="practice-opponent-account"><td>${safe(t('players.opponentSeat', { number: account.seat_id.split('_').pop() }, 'admin'))}</td><td>${safe(account.display_name)} (${safe(account.player_id)})</td><td>${safe(t('players.automaticCaller', {}, 'admin'))}</td><td>${formatNumber(account.balance)} ${safe(t('players.playTokens', {}, 'admin'))}</td></tr>`))}<h3>${safe(t('players.practiceActivity', {}, 'admin'))}</h3>${practiceActivity.length ? table([t('players.time', {}, 'admin'), t('players.account', {}, 'admin'), t('players.round', {}, 'admin'), t('players.action', {}, 'admin'), t('players.amount', {}, 'admin')], practiceActivity.slice().reverse().map(row => `<tr data-testid="practice-opponent-activity"><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(row.round_id || '—')}</td><td>${safe(practiceActionLabels[row.details?.controller_action] || humanLabel(row.transaction_type))}</td><td>${formatNumber(row.amount)} ${safe(t('players.playTokens', {}, 'admin'))}</td></tr>`)) : emptyState(t('players.noPracticeActivity', {}, 'admin'), t('players.noPracticeActivityDetail', {}, 'admin'), 'practice-opponent-empty')}</section>`;
  // Bind save buttons after rendering each bot edit card.
  view.querySelectorAll('.save-bot').forEach(button => button.onclick = async () => saveBot(button));
  // Bind the explicit idempotent funding action after the practice section renders.
  view.querySelector('#fund_practice_opponents').onclick = fundPracticeOpponents;
}

// Define fundPracticeOpponents to seed every server-managed wallet through the ledger.
async function fundPracticeOpponents() {
  // Submit the fixed issue-scoped game allocation to the protected Admin route.
  await post('/api/v1/admin/bots/practice-opponents/fund', { game_id: 'texas_holdem_practice_table' });
  // Show localized completion feedback without exposing ledger internals.
  toast(t('players.practiceFunded', {}, 'admin'), true);
  // Reload balances and append-only activity from the backend.
  await playersBots();
}

// Define userRows to render Admin user-management rows.
function userRows(users) {
  // Return one row per beta user with token, status, terms, and locale controls.
  return users.map(user => `<tr data-testid="admin-user-row" data-user="${safe(user.user_id)}" data-email="${safe(user.email)}" data-status="${safe(user.status)}" data-terms="${safe(user.terms_status)}"><td>${safe(user.email)}</td><td>${safe(user.display_name)}</td><td>${safe(user.status)}</td><td data-testid="admin-user-token-balance">${formatMoney(user.token_balance)}</td><td>${safe(user.token_state)}</td><td>${safe(user.terms_status)}</td><td><select class="user-language">${localeOptions(user.language || 'en-US')}</select></td><td><select class="user-format">${formatLocaleOptions(user.format_locale || 'browser')}</select></td><td><button class="save-user-locale" data-user="${safe(user.user_id)}" data-testid="admin-user-save-locale">Save locale</button><button class="toggle-user" data-user="${safe(user.user_id)}" data-action="${user.status === 'active' ? 'deactivate' : 'reactivate'}" data-testid="admin-user-toggle">${user.status === 'active' ? 'Deactivate' : 'Reactivate'}</button><button class="reset-user-password" data-user="${safe(user.user_id)}" data-testid="admin-user-reset">Reset password</button><button class="terms-user" data-user="${safe(user.user_id)}" data-accepted="${user.terms_status !== 'accepted'}" data-testid="admin-user-terms">${user.terms_status === 'accepted' ? 'Clear terms' : 'Accept terms'}</button></td></tr>`);
}

// Define users to render the Admin beta-user management workspace.
async function users() {
  // Set the localized users title and subtitle.
  setTitle(t('users.title', {}, 'admin'), t('users.subtitle', {}, 'admin'));
  // Load users through the Admin user-management endpoint.
  const data = await api('/api/v1/admin/users');
  // Stop stale user-management responses from overwriting a newer active tab.
  if (!isActiveTab('users')) return;
  // Store password notice so rerenders can show the latest one-time credential.
  const passwordNotice = lastUserPassword ? `<div class="result-box" data-testid="admin-user-temp-password">Latest temporary password: ${safe(lastUserPassword)}</div>` : '';
  // Render creation controls and token-state inspection table.
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('users.createTitle', {}, 'admin'))}</h3><div class="grid3"><label>Email<input id="admin_user_email" data-testid="admin-user-email" type="email" placeholder="beta@example.test"></label><label>Display name<input id="admin_user_name" data-testid="admin-user-name" placeholder="Beta Player"></label><label>Initial tokens<input id="admin_user_tokens" data-testid="admin-user-tokens" type="number" min="0" step="1" value="5000"></label></div><div class="grid3"><label>Temporary password<input id="admin_user_password" data-testid="admin-user-password" type="text" placeholder="Generate if blank"></label><label>Language<select id="admin_user_language" data-testid="admin-user-language">${localeOptions('en-US')}</select></label><label>Format locale<select id="admin_user_format" data-testid="admin-user-format">${formatLocaleOptions('browser')}</select></label></div><label><input id="admin_user_terms" data-testid="admin-user-terms-initial" type="checkbox"> Terms accepted</label><button id="admin_create_user" data-testid="admin-create-user" class="gold">${safe(t('users.createButton', {}, 'admin'))}</button>${passwordNotice}</section><section class="admin-card"><h3>${safe(t('users.tableTitle', {}, 'admin'))}</h3>${table(['Email', 'Name', 'Status', 'Token balance', 'Token state', 'Terms', 'Language', 'Format', 'Actions'], userRows(data.users || []))}</section>`;
  // Bind the create-user button after rendering.
  view.querySelector('#admin_create_user').onclick = createUser;
  // Bind user action buttons after rendering the table.
  view.querySelectorAll('.toggle-user').forEach(button => button.onclick = () => toggleUser(button));
  // Bind password reset buttons after rendering the table.
  view.querySelectorAll('.reset-user-password').forEach(button => button.onclick = () => resetUserPassword(button));
  // Bind terms status buttons after rendering the table.
  view.querySelectorAll('.terms-user').forEach(button => button.onclick = () => updateUserTerms(button));
  // Bind locale save buttons after rendering the table.
  view.querySelectorAll('.save-user-locale').forEach(button => button.onclick = () => saveUserLocale(button));
}

// Define createUser to submit a new beta user through Admin.
async function createUser() {
  // Store payload from the rendered create-user form.
  const payload = { email: view.querySelector('#admin_user_email').value, display_name: view.querySelector('#admin_user_name').value, initial_tokens: Number(view.querySelector('#admin_user_tokens').value || 0), password: view.querySelector('#admin_user_password').value, language: view.querySelector('#admin_user_language').value, format_locale: view.querySelector('#admin_user_format').value, terms_accepted: view.querySelector('#admin_user_terms').checked };
  // Create the user through the Admin API.
  const result = await post('/api/v1/admin/users', payload);
  // Store the one-time password so Admin can hand it to the beta user.
  lastUserPassword = result.temporary_password || '';
  // Show user creation feedback.
  toast('User created.', true);
  // Refresh the users table with the new account.
  await users();
}

// Define toggleUser to deactivate or reactivate a beta account.
async function toggleUser(button) {
  // Post the requested status transition for this user.
  await post(`/api/v1/admin/users/${button.dataset.user}/${button.dataset.action}`, {});
  // Show status-change feedback.
  toast('User status updated.', true);
  // Refresh the users table after the change.
  await users();
}

// Define resetUserPassword to generate a new one-time password.
async function resetUserPassword(button) {
  // Reset the user's password through the Admin API.
  const result = await post(`/api/v1/admin/users/${button.dataset.user}/password-reset`, {});
  // Store the one-time password so Admin can hand it to the beta user.
  lastUserPassword = result.temporary_password || '';
  // Show reset feedback.
  toast('Temporary password generated.', true);
  // Refresh the users table while preserving the password notice.
  await users();
}

// Define updateUserTerms to set a user's terms acceptance status.
async function updateUserTerms(button) {
  // Post the requested terms status through the Admin API.
  await post(`/api/v1/admin/users/${button.dataset.user}/terms`, { accepted: button.dataset.accepted === 'true' });
  // Show terms update feedback.
  toast('Terms status updated.', true);
  // Refresh the users table after the change.
  await users();
}

// Define saveUserLocale to persist per-user locale preferences.
async function saveUserLocale(button) {
  // Store the nearest rendered user row for control lookup.
  const row = button.closest('tr[data-user]');
  // Store the locale payload from row controls.
  const payload = { language: row.querySelector('.user-language').value, format_locale: row.querySelector('.user-format').value, use_browser_locale: false };
  // Persist the locale preferences through the Admin API.
  await post(`/api/v1/admin/users/${button.dataset.user}/locale`, payload);
  // Show locale update feedback.
  toast('User locale saved.', true);
  // Refresh the users table after the change.
  await users();
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
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('ledger.title', {}, 'admin'))}</h3>${(data.ledger || []).length ? table(['Time', 'Player', 'Game', 'Round', 'Type', 'Amount', 'Before', 'After'], data.ledger.slice().reverse().map(row => `<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(humanLabel(row.game))}</td><td>${safe(row.round_id)}</td><td>${safe(humanLabel(row.transaction_type))}</td><td>${formatMoney(row.amount)}</td><td>${formatMoney(row.balance_before)}</td><td>${formatMoney(row.balance_after)}</td></tr>`)) : emptyState('No ledger events yet', 'Token activity will appear here after players begin using the casino.', 'admin-ledger-empty')}</section>`;
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
  view.innerHTML = `<div class="admin-split"><section class="admin-card"><h3>Application events</h3>${eventList(app.logs, 'No application events', 'Application activity will appear here as the local service is used.', 'admin-app-events')}</section><section class="admin-card"><h3>Error events</h3>${eventList(errors.logs, 'No error events', 'No server errors have been recorded for the current day.', 'admin-error-events', true)}</section></div><section class="admin-card"><h3>Browser events</h3>${eventList(client.logs, 'No browser events', 'Browser activity will appear here after a client sends telemetry.', 'admin-client-events')}</section>`;
}

// Render OAuth diagnostics separately so provider configuration cannot change Operations health.
function oauthDiagnosticsCard(data) {
  // Keep only the three provider identifiers owned by the disabled OAuth catalog.
  const providers = Array.isArray(data?.providers) ? data.providers.filter(provider => ['local', 'google', 'facebook'].includes(provider?.provider)) : [];
  // Render an explicit unavailable state when the independent diagnostic request fails validation.
  if (providers.length !== 3) return `<section class="admin-card" data-testid="admin-oauth-diagnostics-unavailable"><h2>${safe(t('oauth.title', {}, 'admin'))}</h2><p>${safe(t('oauth.unavailable', {}, 'admin'))}</p></section>`;
  // Build one allowlisted row per provider without rendering callback URLs or environment details.
  const rows = providers.map(provider => {
    // Normalize configuration status so unexpected backend values never become translation keys.
    const configurationStatus = ['ready', 'disabled', 'misconfigured'].includes(provider.status) ? provider.status : 'unknown';
    // Derive runtime copy only from the explicit availability boolean.
    const runtimeStatus = provider.runtime_available === true ? 'available' : 'unavailable';
    // Return a compact localized row with stable browser-test hooks.
    return `<tr data-testid="admin-oauth-provider-${safe(provider.provider)}" data-runtime-available="${provider.runtime_available === true}"><td>${safe(t(`oauth.provider.${provider.provider}`, {}, 'admin'))}</td><td>${safe(t(`oauth.configuration.${configurationStatus}`, {}, 'admin'))}</td><td>${safe(t(`oauth.runtime.${runtimeStatus}`, {}, 'admin'))}</td></tr>`;
  });
  // Return a separate card so OAuth status never alters live, degraded, or down Operations state.
  return `<section class="admin-card" data-testid="admin-oauth-diagnostics"><h2>${safe(t('oauth.title', {}, 'admin'))}</h2><p>${safe(t('oauth.subtitle', {}, 'admin'))}</p>${table([t('oauth.field.provider', {}, 'admin'), t('oauth.field.configuration', {}, 'admin'), t('oauth.field.runtime', {}, 'admin')], rows)}</section>`;
}

// Replace only the independent OAuth card when its separate request settles.
function replaceOAuthDiagnosticsCard(data) {
  // Ignore a delayed diagnostic response after the user has left Operations.
  if (!isActiveTab('operations')) return;
  // Find either the loading/unavailable placeholder or the prior populated card.
  const card = view.querySelector('[data-testid^="admin-oauth-diagnostics"]');
  // Replace the provider card without rerendering or reclassifying Operations health.
  if (card) card.outerHTML = oauthDiagnosticsCard(data);
}

// Define operations to render trusted dependency and heartbeat telemetry for Admin users.
async function operations() {
  // Set localized Operations chrome before the request so transport failures retain context.
  setTitle(t('operations.title', {}, 'admin'), t('operations.subtitle', {}, 'admin'));
  // Start protected loading so transport failure becomes an explicit non-color state.
  try {
    // Load only Operations before rendering its live, degraded, or down classification.
    const data = await api('/api/v2/admin/operations');
    // Stop a stale response from replacing a newer Admin tab.
    if (!isActiveTab('operations')) return;
    // Select readable state copy and a symbol so color is never the only signal.
    const stateKey = data.ready ? 'live' : 'degraded';
    // Map fixed provider identifiers to localized operator-facing labels.
    const providerLabel = t(`operations.provider.${data.storage_provider}`, {}, 'admin');
    // Map only allowlisted reason codes to localized operator guidance.
    const reasonLabels = (data.reasons || []).map(reason => t(`operations.reason.${reason.code}`, {}, 'admin'));
    // Use explicit unavailable copy when optional build provenance or heartbeat state is absent.
    const buildSha = data.build?.sha || t('operations.unavailable', {}, 'admin');
    // Format the trusted heartbeat timestamp without exposing raw transport diagnostics.
    const heartbeat = data.last_successful_heartbeat_at ? formatDate(new Date(data.last_successful_heartbeat_at), { dateStyle: 'medium', timeStyle: 'medium' }) : t('operations.unavailable', {}, 'admin');
    // Render live or degraded diagnostics with stable test hooks for EN/RU visual evidence.
    view.innerHTML = `<section class="admin-card ${data.ready ? '' : 'danger'}" data-testid="admin-operations-${stateKey}"><div class="row"><div><h2>${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</h2><p>${safe(t(`operations.detail.${stateKey}`, {}, 'admin'))}</p></div><span class="badge" data-testid="admin-operations-state">${safe(t(`operations.symbol.${stateKey}`, {}, 'admin'))} ${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</span></div>${table([t('operations.field', {}, 'admin'), t('operations.value', {}, 'admin')], [`<tr><td>${safe(t('operations.storage', {}, 'admin'))}</td><td>${safe(providerLabel)}</td></tr>`, `<tr><td>${safe(t('operations.appVersion', {}, 'admin'))}</td><td>${safe(data.build.app_version)}</td></tr>`, `<tr><td>${safe(t('operations.buildSha', {}, 'admin'))}</td><td>${safe(buildSha)}</td></tr>`, `<tr><td>${safe(t('operations.lastHeartbeat', {}, 'admin'))}</td><td>${safe(heartbeat)}</td></tr>`])}${reasonLabels.length ? `<h3>${safe(t('operations.attention', {}, 'admin'))}</h3><ul>${reasonLabels.map(label => `<li>${safe(label)}</li>`).join('')}</ul>` : ''}</section>${oauthDiagnosticsCard(null)}`;
    // Start provider diagnostics only after Operations is visible and handle failure locally.
    api('/api/v2/admin/oauth/providers').then(replaceOAuthDiagnosticsCard).catch(() => replaceOAuthDiagnosticsCard(null));
  // Convert network or server loss into a client-derived down state without raw error text.
  } catch (error) {
    // Avoid replacing a newer tab after a delayed transport failure.
    if (!isActiveTab('operations')) return;
    // Render a clear symbol and recovery instruction so color is not the only status signal.
    view.innerHTML = `<section class="admin-card danger" data-testid="admin-operations-down"><h2>${safe(t('operations.symbol.down', {}, 'admin'))} ${safe(t('operations.state.down', {}, 'admin'))}</h2><p>${safe(t('operations.detail.down', {}, 'admin'))}</p></section>`;
  }
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
  view.innerHTML = `<div class="admin-split"><section class="admin-card"><div class="row"><h3 style="margin-right:auto">${safe(t('language.availableTitle', {}, 'admin'))}</h3><span class="badge">${safe(t('language.readyCount', {}, 'admin'))}</span></div><div class="grid2">${languageCards(selectedLanguage)}</div><h3>${safe(t('language.top20Title', {}, 'admin'))}</h3>${plannedLanguageGrid()}</section><section class="admin-card"><h3>${safe(t('language.localeSettings', {}, 'admin'))}</h3><div class="grid2"><label>${safe(t('language.displayLanguage', {}, 'admin'))}<select id="admin_language" data-testid="admin-language-select">${localeOptions(selectedLanguage)}</select></label><label>${safe(t('language.formatLocale', {}, 'admin'))}<select id="admin_format_locale" data-testid="admin-format-locale-select">${formatLocaleOptions(selectedFormat)}</select></label></div><label><input id="admin_use_browser" type="checkbox" ${settings.useBrowserLocale ? 'checked' : ''}> ${safe(t('language.useBrowser', {}, 'admin'))}</label><label><input id="admin_persist_browser" type="checkbox" checked> ${safe(t('language.persistBrowser', {}, 'admin'))}</label><div class="result-box"><p data-testid="admin-money-preview">${safe(t('language.previewBalance', { amount: formatMoney(5030) }, 'admin'))}</p><p>${safe(t('language.datePreview', {}, 'admin'))}: ${safe(formatDate(new Date(), { dateStyle: 'medium', timeStyle: 'short' }))}</p></div><div class="row"><button id="admin_apply_locale" data-testid="admin-locale-apply" class="gold">${safe(t('language.apply', {}, 'admin'))}</button><button id="admin_save_locale" data-testid="admin-locale-save">${safe(t('language.saveBrowser', {}, 'admin'))}</button><button id="admin_reset_locale" data-testid="admin-locale-reset">${safe(t('language.resetBrowser', {}, 'admin'))}</button><button id="admin_preview_lobby">${safe(t('actions.previewLobby'))}</button></div>${diagnosticsTable(state)}<h3>${safe(t('language.stringPreview', {}, 'admin'))}</h3><div class="bot-edit"><b>English</b><p>Choose your table. All games use play tokens only. Ledger-backed outcomes are visible in Admin.</p></div><div class="bot-edit"><b>Русский</b><p>Выберите стол. Все игры используют только игровые токены. Результаты с учётом ledger видны в Admin.</p></div><div class="bot-edit"><b>${safe(t('language.fallback', {}, 'admin'))}</b><p>${safe(t('language.fallbackDescription', {}, 'admin'))}</p></div></section></div>`;
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
  // Stop a stale System response from replacing a newer active Admin tab.
  if (!isActiveTab('system')) return;
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

// Inject Admin-scoped responsive styles so mobile viewports collapse the desktop sidebar and stack cards. (issue #281)
function injectResponsiveAdminStyles() {
  // Avoid inserting the responsive rules more than once across locale rerenders.
  if (document.getElementById('admin-responsive-styles')) return;
  // Create a dedicated style element owned by the Admin module.
  const style = document.createElement('style');
  // Identify the injected style so repeated calls stay idempotent.
  style.id = 'admin-responsive-styles';
  // Define a mobile breakpoint that unclips Admin and stacks its desktop three-zone composition. (issue #281)
  style.textContent = '@media (max-width:900px){' +
    // Collapse the fixed 280px sidebar column so the main content is no longer squeezed to a strip.
    '.admin-shell{grid-template-columns:1fr;height:auto;min-height:100vh;}' +
    // Turn the vertical sidebar into a horizontal tab rail that wraps rather than using a native scrollbar.
    '.admin-sidebar{flex-direction:row;flex-wrap:wrap;gap:6px;border-right:0;border-bottom:1px solid rgba(255,255,255,.12);}' +
    // Keep the brand and each tab from shrinking so labels stay readable in the horizontal rail.
    '.admin-sidebar>*{flex:0 0 auto;white-space:nowrap;}' +
    // Hide the sidebar divider that only makes sense in the vertical desktop layout.
    '.admin-sidebar hr{display:none;}' +
    // Stop the main region from clipping content so the page can scroll to every card.
    '.admin-main{overflow:visible;}' +
    // Let the content region grow with the document instead of owning a nested clip.
    '.admin-content{overflow:visible;padding:12px;}' +
    // Stack dashboard metric cards into a single readable column.
    '.admin-card-grid{grid-template-columns:1fr;}' +
    // Stack any two-column or three-column Admin panels on narrow screens.
    '.admin-split,.three-col{grid-template-columns:1fr;}' +
  '}';
  // Attach the responsive rules after the shared stylesheet so they win the cascade without editing styles.css.
  document.head.appendChild(style);
}

// Define start to initialize i18n before the first Admin render.
async function start() {
  // Ensure Admin is usable at mobile viewports before the first render. (issue #281)
  injectResponsiveAdminStyles();
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
