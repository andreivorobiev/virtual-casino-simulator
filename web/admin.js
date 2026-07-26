// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import API helpers so Admin tabs continue using the frozen v1 contract.
import { api, post } from './core/api.js';
// Import UI helpers for escaping user/server text and showing transient status.
import { safe, toast } from './core/ui.js';
// Import listener-free label helpers so Admin never renders raw all-caps ledger enums.
import { humanLabel, ledgerEventLabel as localizedLedgerEventLabel } from './core/admin_labels.js';
// Import voice helpers so the existing Audio & Voice tab keeps its behavior.
import { availableVoices, loadVoiceSettings, saveVoiceSettings, speak } from './core/voice.js';
// Import i18n helpers so Admin can switch language without reloading or remounting.
import { applyTranslations, formatDate, formatMoney, formatNumber, getLocaleSettings, getLocaleState, initI18n, onLocaleChange, resetLocaleSettings, setLocale, t } from './core/i18n.js';

// Store current so refresh and locale rerendering preserve the active Admin tab.
let current = 'dashboard';
// Store lastUserPassword so Admin can see the latest one-time credential after rerender.
let lastUserPassword = '';
// Preserve low-cardinality Guest Trials filters across locale rerenders and refreshes.
let guestFilters = { locale: '', device: '', status: '', game: '', completed: '', error_category: '', range: '' };
// Preserve governed problem-report filters across detail navigation and refreshes.
let feedbackFilters = { priority: '', status: '', category: '', impact: '', locale: '', route: '', reporter: '', created_from: '', created_to: '' };
// Store view so tab renderers share the same Admin content target.
const view = document.getElementById('adminView');
// Store title so tab renderers can update the current heading.
const title = document.getElementById('adminTitle');
// Store subtitle so tab renderers can update the current explanatory line.
const subtitle = document.getElementById('adminSubtitle');
// Define pre to render escaped JSON diagnostics.
const pre = object => `<pre class="logview">${safe(JSON.stringify(object, null, 2))}</pre>`;
// Define table to render escaped mini tables while preserving existing Admin density.
const table = (heads, rows) => `<table class="mini-table"><tr>${heads.map(head => `<th>${safe(head)}</th>`).join('')}</tr>${rows.join('')}</table>`;
// Define option to render a selected-safe select option.
const option = (value, label, selected) => `<option value="${safe(value)}" ${selected === value ? 'selected' : ''}>${safe(label)}</option>`;

// Define ledgerEventLabel to bind the listener-free classifier to the active Admin locale.
const ledgerEventLabel = (value, game) => localizedLedgerEventLabel(value, game, (key, params) => t(key, params, 'admin'));
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
    // Await private invitation controls so rejected v2 requests stay inside the localized load-error boundary. (INVITE-005)
    if (tab === 'invitations') return await invitations();
    // Await Guest Trials so rejected Admin requests stay inside the localized load-error boundary. (issue #317)
    if (tab === 'guests') return await guests();
    // Await the problem-report inbox so failures stay inside the Admin error boundary.
    if (tab === 'feedback') return await feedbackReports();
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
    view.innerHTML = `<section class="admin-card danger" data-testid="admin-load-error"><h2>${safe(t('common.loadErrorTitle', {}, 'admin'))}</h2><p>${safe(t('common.loadErrorDetail', {}, 'admin'))}</p></section>`;
  }
}

// Render one governed select from a fixed value list.
function feedbackSelect(id, values, selected, emptyLabel, keyPrefix = '') {
  // Build the optional all-values row only for filter controls.
  const emptyOption = emptyLabel ? `<option value="">${safe(emptyLabel)}</option>` : '';
  // Return stable human-readable options without an invalid empty choice in detail forms.
  return `<select id="${safe(id)}">${emptyOption}${values.map(value => option(value, keyPrefix ? t(`${keyPrefix}.${value}`, {}, 'feedback') : humanLabel(value), selected)).join('')}</select>`;
}

// Allocate one strong replay key for each explicit Admin mutation.
function feedbackActionKey() {
  // Remove separators so the key matches the shared service contract.
  return crypto.randomUUID().replaceAll('-', '');
}

// Load and render the attachment-free Admin problem-report inbox. (ADMIN-025, issue #349)
async function feedbackReports() {
  // Set the tab heading through the localized feedback domain.
  setTitle(t('feedback.admin.title', {}, 'feedback'), t('feedback.admin.subtitle', {}, 'feedback'));
  // Build a query containing only non-empty governed filters.
  const query = new URLSearchParams(Object.entries(feedbackFilters).filter(([, value]) => value));
  // Fetch the additive v2 inbox contract.
  const data = await api(`/api/v2/admin/feedback/reports${query.toString() ? `?${query}` : ''}`);
  // Stop a stale response from replacing a newer Admin tab.
  if (!isActiveTab('feedback')) return;
  // Build rows with internal references and a dedicated detail action.
  const rows = (data.reports || []).map(report => `<tr><td><button type="button" class="feedback-link" data-feedback-id="${safe(report.report_id)}">${safe(report.reference)}</button></td><td><span class="badge">${safe(report.priority)}</span></td><td>${safe(t(`feedback.status.${report.status}`, {}, 'feedback'))}</td><td>${safe(t(`feedback.category.${report.category}`, {}, 'feedback'))}</td><td>${safe(t(`feedback.impact.${report.impact}`, {}, 'feedback'))}</td><td>${safe(report.reporter_reference)}</td><td>${safe(report.summary)}</td><td>${safe(report.route)}</td><td>${safe(report.created_at)}</td></tr>`);
  // Render filters, the readable empty state, or the inbox table.
  view.innerHTML = `<section class="admin-card feedback-inbox" data-testid="admin-feedback-inbox"><div class="feedback-filters"><label>${safe(t('feedback.admin.priority', {}, 'feedback'))}${feedbackSelect('feedback-priority-filter', data.priorities || ['P1', 'P2', 'P3'], feedbackFilters.priority, t('feedback.admin.all', {}, 'feedback'))}</label><label>${safe(t('feedback.admin.status', {}, 'feedback'))}${feedbackSelect('feedback-status-filter', data.statuses || [], feedbackFilters.status, t('feedback.admin.all', {}, 'feedback'), 'feedback.status')}</label><label>${safe(t('feedback.admin.category', {}, 'feedback'))}${feedbackSelect('feedback-category-filter', data.categories || [], feedbackFilters.category, t('feedback.admin.all', {}, 'feedback'), 'feedback.category')}</label><label>${safe(t('feedback.admin.impact', {}, 'feedback'))}${feedbackSelect('feedback-impact-filter', data.impacts || [], feedbackFilters.impact, t('feedback.admin.all', {}, 'feedback'), 'feedback.impact')}</label><label>${safe(t('feedback.admin.locale', {}, 'feedback'))}${feedbackSelect('feedback-locale-filter', getLocaleState().locales.map(locale => locale.id), feedbackFilters.locale, t('feedback.admin.all', {}, 'feedback'))}</label><label>${safe(t('feedback.admin.routeFilter', {}, 'feedback'))}<input id="feedback-route-filter" value="${safe(feedbackFilters.route)}" maxlength="120"></label><label>${safe(t('feedback.admin.reporter', {}, 'feedback'))}<input id="feedback-reporter-filter" value="${safe(feedbackFilters.reporter)}" pattern="USR-[A-F0-9]{16}"></label><label>${safe(t('feedback.admin.createdFrom', {}, 'feedback'))}<input id="feedback-created-from-filter" type="datetime-local" value="${safe(feedbackFilters.created_from)}"></label><label>${safe(t('feedback.admin.createdTo', {}, 'feedback'))}<input id="feedback-created-to-filter" type="datetime-local" value="${safe(feedbackFilters.created_to)}"></label><button id="feedback-apply-filters" type="button">${safe(t('feedback.admin.apply', {}, 'feedback'))}</button><button id="feedback-cleanup" type="button">${safe(t('feedback.admin.cleanup', {}, 'feedback'))}</button></div>${rows.length ? `<div class="feedback-table-scroll" tabindex="0" role="region" aria-label="${safe(t('feedback.admin.tableLabel', {}, 'feedback'))}">${table([t('feedback.admin.reference', {}, 'feedback'), t('feedback.admin.priority', {}, 'feedback'), t('feedback.admin.status', {}, 'feedback'), t('feedback.admin.category', {}, 'feedback'), t('feedback.admin.impact', {}, 'feedback'), t('feedback.admin.reporter', {}, 'feedback'), t('feedback.admin.summary', {}, 'feedback'), t('feedback.admin.route', {}, 'feedback'), t('feedback.admin.created', {}, 'feedback')], rows)}</div>` : emptyState(t('feedback.admin.emptyTitle', {}, 'feedback'), t('feedback.admin.emptyCopy', {}, 'feedback'), 'admin-feedback-empty')}</section>`;
  // Apply current filter selections when the Admin requests a refresh.
  view.querySelector('#feedback-apply-filters').onclick = () => { feedbackFilters = { priority: view.querySelector('#feedback-priority-filter').value, status: view.querySelector('#feedback-status-filter').value, category: view.querySelector('#feedback-category-filter').value, impact: view.querySelector('#feedback-impact-filter').value, locale: view.querySelector('#feedback-locale-filter').value, route: view.querySelector('#feedback-route-filter').value, reporter: view.querySelector('#feedback-reporter-filter').value, created_from: view.querySelector('#feedback-created-from-filter').value, created_to: view.querySelector('#feedback-created-to-filter').value }; feedbackReports(); };
  // Resume interrupted deletions and enforce both report and opaque-rate retention ceilings.
  view.querySelector('#feedback-cleanup').onclick = async () => { const result = await post('/api/v2/admin/feedback/cleanup', {}); toast(t('feedback.admin.cleaned', { reports: result.cleanup?.deleted || 0 }, 'feedback'), true); feedbackReports(); };
  // Open detail views only through report identifiers returned by the server.
  view.querySelectorAll('[data-feedback-id]').forEach(button => { button.onclick = () => feedbackDetail(button.dataset.feedbackId); });
}

// Render one canonical internal report with evidence and triage controls.
async function feedbackDetail(reportId) {
  // Fetch the Admin-only detail contract.
  const data = await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`);
  // Stop a stale response from replacing another selected tab.
  if (!isActiveTab('feedback')) return;
  // Read the canonical report object.
  const report = data.report || {};
  // Build metadata-free image previews from server-normalized evidence.
  const evidence = (report.attachments || []).map((attachment, index) => `<figure><img src="data:${safe(attachment.media_type)};base64,${safe(attachment.data)}" alt="${safe(t('feedback.screenshotAlt', { number: index + 1 }, 'feedback'))}"><figcaption>${safe(attachment.width)} × ${safe(attachment.height)} · ${safe(attachment.bytes)} bytes</figcaption></figure>`).join('');
  // Render report prose, controlled workflow fields, internal notes, and manual GitHub linkage.
  view.innerHTML = `<section class="admin-card feedback-detail" data-testid="admin-feedback-detail"><div class="row"><button id="feedback-back" type="button">${safe(t('feedback.admin.back', {}, 'feedback'))}</button><span class="badge">${safe(report.reference)}</span><span class="badge">${safe(t(`feedback.category.${report.category}`, {}, 'feedback'))}</span><span class="badge">${safe(t(`feedback.impact.${report.impact}`, {}, 'feedback'))}</span><span class="badge">${safe(report.reporter_reference)}</span></div><h2>${safe(report.summary)}</h2><div class="admin-split"><section><h3>${safe(t('feedback.admin.actual', {}, 'feedback'))}</h3><p class="feedback-prose">${safe(report.actual)}</p><h3>${safe(t('feedback.admin.expected', {}, 'feedback'))}</h3><p class="feedback-prose">${safe(report.expected)}</p><h3>${safe(t('feedback.admin.context', {}, 'feedback'))}</h3>${table([t('feedback.admin.field', {}, 'feedback'), t('feedback.admin.value', {}, 'feedback')], Object.entries(report.context || {}).map(([key, value]) => `<tr><td>${safe(humanLabel(key))}</td><td>${safe(value)}</td></tr>`))}</section><section class="feedback-triage"><label>${safe(t('feedback.admin.priority', {}, 'feedback'))}${feedbackSelect('feedback-detail-priority', ['P1', 'P2', 'P3'], report.priority, '')}</label><label>${safe(t('feedback.admin.status', {}, 'feedback'))}${feedbackSelect('feedback-detail-status', ['new', 'triaged', 'linked', 'resolved', 'duplicate', 'rejected'], report.status, '', 'feedback.status')}</label><label>${safe(t('feedback.admin.notes', {}, 'feedback'))}<textarea id="feedback-admin-notes" maxlength="4000" rows="7">${safe(report.admin_notes || '')}</textarea></label><label>${safe(t('feedback.admin.githubUrl', {}, 'feedback'))}<input id="feedback-github-url" type="url" value="${safe(report.github_issue_url || '')}" placeholder="https://github.com/andreivorobiev/virtual-casino-simulator/issues/…"></label><p class="muted">${safe(t('feedback.admin.manualOnly', {}, 'feedback'))}</p><button id="feedback-save" class="gold" type="button">${safe(t('feedback.admin.save', {}, 'feedback'))}</button><button id="feedback-draft" type="button">${safe(t('feedback.admin.prepareDraft', {}, 'feedback'))}</button><button id="feedback-export" type="button">${safe(t('feedback.admin.export', {}, 'feedback'))}</button><button id="feedback-delete" class="danger" type="button">${safe(t('feedback.admin.delete', {}, 'feedback'))}</button></section></div><h3>${safe(t('feedback.admin.screenshots', {}, 'feedback'))}</h3><div class="feedback-evidence">${evidence || `<p class="muted">${safe(t('feedback.admin.noScreenshots', {}, 'feedback'))}</p>`}</div><div id="feedback-github-draft" class="feedback-draft" hidden></div></section>`;
  // Return to the filtered inbox without losing filter state.
  view.querySelector('#feedback-back').onclick = feedbackReports;
  // Persist controlled triage fields and redraw from the server response.
  view.querySelector('#feedback-save').onclick = async () => { await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`, { method: 'PATCH', body: { idempotency_key: feedbackActionKey(), priority: view.querySelector('#feedback-detail-priority').value, status: view.querySelector('#feedback-detail-status').value, admin_notes: view.querySelector('#feedback-admin-notes').value, github_issue_url: view.querySelector('#feedback-github-url').value } }); toast(t('feedback.admin.saved', {}, 'feedback'), true); feedbackDetail(reportId); };
  // Prepare a sanitized manual GitHub draft without publishing externally.
  view.querySelector('#feedback-draft').onclick = async () => { const prepared = await post(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}/github-draft`, {}); const draft = prepared.draft || {}; const outlet = view.querySelector('#feedback-github-draft'); outlet.hidden = false; outlet.innerHTML = `<h3>${safe(t('feedback.admin.draftTitle', {}, 'feedback'))}</h3><p class="muted">${safe(t('feedback.admin.manualOnly', {}, 'feedback'))}</p><label>${safe(t('feedback.admin.issueTitle', {}, 'feedback'))}<input id="feedback-draft-title" readonly value="${safe(draft.title || '')}"></label><label>${safe(t('feedback.admin.issueBody', {}, 'feedback'))}<textarea id="feedback-draft-body" readonly rows="14">${safe(draft.body || '')}</textarea></label><p>${safe(t('feedback.admin.labels', {}, 'feedback'))}: ${safe((draft.labels || []).join(', '))}</p><div class="row"><button id="feedback-copy-draft" type="button">${safe(t('feedback.admin.copyDraft', {}, 'feedback'))}</button></div>`; outlet.querySelector('#feedback-copy-draft').onclick = async () => { await navigator.clipboard.writeText(`${draft.title}\n\n${draft.body}`); toast(t('feedback.admin.copied', {}, 'feedback'), true); }; };
  // Download only privacy-safe metadata after the server removes encoded evidence.
  view.querySelector('#feedback-export').onclick = async () => { const exported = await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}/export`); const blob = new Blob([JSON.stringify(exported.export || {}, null, 2)], { type: 'application/json' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${report.reference || 'feedback-report'}.json`; link.click(); URL.revokeObjectURL(link.href); toast(t('feedback.admin.exported', {}, 'feedback'), true); };
  // Require explicit confirmation before starting the recoverable privacy-deletion saga.
  view.querySelector('#feedback-delete').onclick = async () => { if (!window.confirm(t('feedback.admin.deleteConfirm', {}, 'feedback'))) return; await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`, { method: 'DELETE', body: { idempotency_key: feedbackActionKey() } }); toast(t('feedback.admin.deleted', {}, 'feedback'), true); feedbackReports(); };
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
  view.innerHTML = `<div class="admin-card-grid"><div class="admin-card"><b>App</b><h2>${safe(data.app_version)}</h2></div><div class="admin-card"><b>${safe(t('nav.players', {}, 'admin'))}</b><h2>${formatNumber(data.players.length)}</h2></div><div class="admin-card"><b>Bots</b><h2>${formatNumber(data.bots.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.activeAutoplay', {}, 'admin'))}</b><h2>${formatNumber(active.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.errorsToday', {}, 'admin'))}</b><h2>${formatNumber((data.logs.errors || []).length)}</h2></div><div class="admin-card"><b>${safe(t('nav.requirements', {}, 'admin'))}</b><h2>${formatNumber(Object.values(data.requirement_counts || {}).reduce((sum, count) => sum + count, 0))}</h2></div></div><div class="admin-split"><section class="admin-card"><h3>${safe(t('dashboard.recentLedger', {}, 'admin'))}</h3>${(data.recent_ledger || []).length ? table([t('ledger.columns.time', {}, 'admin'), t('ledger.columns.player', {}, 'admin'), t('ledger.columns.game', {}, 'admin'), t('ledger.columns.type', {}, 'admin'), t('ledger.columns.amount', {}, 'admin')], data.recent_ledger.slice(-12).reverse().map(row => `<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(humanLabel(row.game))}</td><td data-testid="admin-ledger-event">${safe(ledgerEventLabel(row.transaction_type, row.game))}</td><td>${formatMoney(row.amount)}</td></tr>`)) : emptyState(t('ledger.emptyTitle', {}, 'admin'), t('ledger.emptyDetail', {}, 'admin'), 'admin-ledger-empty')}</section><section class="admin-card"><h3>${safe(t('dashboard.recentErrors', {}, 'admin'))}</h3>${eventList(data.logs.errors, 'No recent errors', 'The local casino has not recorded any application errors today.', 'admin-errors-empty', true)}</section></div>`;
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
  return users.map(user => `<tr data-testid="admin-user-row" data-user="${safe(user.user_id)}" data-email="${safe(user.email)}" data-status="${safe(user.status)}" data-terms="${safe(user.terms_status)}"><td>${safe(user.email)}</td><td>${safe(user.display_name)}</td><td class="admin-user-access-cell"><div class="admin-user-access-controls" data-testid="admin-user-access-controls"><select class="user-status" data-testid="admin-user-status">${['active', 'inactive', 'suspended', 'locked'].map(status => option(status, humanLabel(status), user.status)).join('')}</select><label class="check-row"><input class="user-admin-role" data-testid="admin-user-role-admin" type="checkbox" ${(user.roles || []).includes('admin') ? 'checked' : ''}> ${safe(t('users.roleAdmin', {}, 'admin'))}</label><button class="save-user-account" data-user="${safe(user.user_id)}" data-testid="admin-user-save-account">${safe(t('users.saveAccount', {}, 'admin'))}</button></div></td><td data-testid="admin-user-token-balance">${formatMoney(user.token_balance)}</td><td>${safe(user.token_state)}</td><td>${safe(user.terms_status)}</td><td><select class="user-language">${localeOptions(user.language || 'en-US')}</select></td><td><select class="user-format">${formatLocaleOptions(user.format_locale || 'browser')}</select></td><td><button class="save-user-locale" data-user="${safe(user.user_id)}" data-testid="admin-user-save-locale">Save locale</button><button class="toggle-user" data-user="${safe(user.user_id)}" data-action="${user.status === 'active' ? 'deactivate' : 'reactivate'}" data-testid="admin-user-toggle">${user.status === 'active' ? 'Deactivate' : 'Reactivate'}</button><button class="reset-user-password" data-user="${safe(user.user_id)}" data-testid="admin-user-reset">Reset password</button><button class="terms-user" data-user="${safe(user.user_id)}" data-accepted="${user.terms_status !== 'accepted'}" data-testid="admin-user-terms">${user.terms_status === 'accepted' ? 'Clear terms' : 'Accept terms'}</button></td></tr>`);
}

// Define isManagedAccountUser so the Users tab stays account-only even if a legacy API payload includes guests.
function isManagedAccountUser(user) {
  // Normalize role values before checking for a disposable guest principal.
  const roles = (user?.roles || [user?.role]).map(role => String(role || '').toLowerCase());
  // Normalize both server-owned identity classifiers before evaluating the fail-closed UI boundary.
  const principalType = String(user?.principal_type || '').toLowerCase();
  const identityProvider = String(user?.identity_provider || '').toLowerCase();
  // Return false for every known guest-trial marker; Guest Trials owns those temporary marketing visitors.
  return principalType !== 'guest' && identityProvider !== 'guest' && user?.guest !== true && !roles.includes('guest');
}

// Define users to render the Admin beta-user management workspace.
async function users() {
  // Set the localized users title and subtitle.
  setTitle(t('users.title', {}, 'admin'), t('users.subtitle', {}, 'admin'));
  // Load users through the Admin user-management endpoint.
  const data = await api('/api/v1/admin/users');
  // Stop stale user-management responses from overwriting a newer active tab.
  if (!isActiveTab('users')) return;
  // Keep the visible table account-only even if an older server returns temporary guest principals.
  const managedUsers = (data.users || []).filter(isManagedAccountUser);
  // Store password notice so rerenders can show the latest one-time credential.
  const passwordNotice = lastUserPassword ? `<div class="result-box" data-testid="admin-user-temp-password">Latest temporary password: ${safe(lastUserPassword)}</div>` : '';
  // Build an explicit handoff card so operators know temporary visitors live in Guest Trials.
  const guestSeparationCard = `<section class="admin-card" data-testid="admin-users-guest-separation"><h3>${safe(t('users.guestSeparationTitle', {}, 'admin'))}</h3><p>${safe(t('users.guestSeparationCopy', {}, 'admin'))}</p><button id="admin_open_guest_trials" type="button" data-testid="admin-open-guest-trials">${safe(t('users.openGuestTrials', {}, 'admin'))}</button></section>`;
  // Build the account-only table inside one named keyboard-scrollable region, or show the calm empty state.
  const managedUserTable = managedUsers.length ? `<div class="admin-users-table-scroll" data-testid="admin-users-managed-table" tabindex="0" role="region" aria-label="${safe(t('users.tableTitle', {}, 'admin'))}">${table(['Email', 'Name', t('users.accessControls', {}, 'admin'), 'Token balance', 'Token state', 'Terms', 'Language', 'Format', 'Actions'], userRows(managedUsers))}</div>` : emptyState(t('users.emptyTitle', {}, 'admin'), t('users.emptyDetail', {}, 'admin'), 'admin-users-empty');
  // Render creation controls and token-state inspection table.
  view.innerHTML = `${guestSeparationCard}<section class="admin-card" data-testid="admin-user-create"><h3>${safe(t('users.createTitle', {}, 'admin'))}</h3><div class="grid3"><label>Email<input id="admin_user_email" data-testid="admin-user-email" type="email" placeholder="beta@example.test"></label><label>Display name<input id="admin_user_name" data-testid="admin-user-name" placeholder="Beta Player"></label><label>Initial tokens<input id="admin_user_tokens" data-testid="admin-user-tokens" type="number" min="0" step="1" value="5000"></label></div><div class="grid3"><label>Temporary password<input id="admin_user_password" data-testid="admin-user-password" type="text" placeholder="Generate if blank"></label><label>${safe(t('users.initialRole', {}, 'admin'))}<select id="admin_user_role" data-testid="admin-user-role"><option value="player">${safe(t('users.rolePlayer', {}, 'admin'))}</option><option value="admin">${safe(t('users.roleAdmin', {}, 'admin'))}</option></select></label><label>Language<select id="admin_user_language" data-testid="admin-user-language">${localeOptions('en-US')}</select></label></div><div class="grid3"><label>Format locale<select id="admin_user_format" data-testid="admin-user-format">${formatLocaleOptions('browser')}</select></label></div><label><input id="admin_user_terms" data-testid="admin-user-terms-initial" type="checkbox"> Terms accepted</label><button id="admin_create_user" data-testid="admin-create-user" class="gold">${safe(t('users.createButton', {}, 'admin'))}</button>${passwordNotice}</section><section class="admin-card" data-testid="admin-users-managed-accounts"><h3>${safe(t('users.tableTitle', {}, 'admin'))}</h3>${managedUserTable}</section>`;
  // Bind the Guest Trials shortcut after rendering the account-management handoff card.
  view.querySelector('#admin_open_guest_trials').onclick = () => activate('guests');
  // Bind the create-user button after rendering.
  view.querySelector('#admin_create_user').onclick = createUser;
  // Bind user action buttons after rendering the table.
  view.querySelectorAll('.toggle-user').forEach(button => button.onclick = () => toggleUser(button));
  // Bind account role/status saves after rendering the table.
  view.querySelectorAll('.save-user-account').forEach(button => button.onclick = () => saveUserAccount(button));
  // Bind password reset buttons after rendering the table.
  view.querySelectorAll('.reset-user-password').forEach(button => button.onclick = () => resetUserPassword(button));
  // Bind terms status buttons after rendering the table.
  view.querySelectorAll('.terms-user').forEach(button => button.onclick = () => updateUserTerms(button));
  // Bind locale save buttons after rendering the table.
  view.querySelectorAll('.save-user-locale').forEach(button => button.onclick = () => saveUserLocale(button));
}

// Render the de-identified Guest Trials telemetry section for account-free visitors. (issue #317)
async function guests() {
  // Set the localized Guest Trials heading and its measurement helper line.
  setTitle(t('nav.guests', {}, 'admin'), t('guests.subtitle', {}, 'admin'));
  // Announce an explicit localized loading state before the Admin-only request resolves.
  view.innerHTML = `<section class="admin-card loading-panel" data-testid="admin-guest-loading" role="status"><h2>${safe(t('guests.loadingTitle', {}, 'admin'))}</h2><p>${safe(t('guests.loadingDetail', {}, 'admin'))}</p></section>`;
  // Encode only published filters while keeping the UI-only range shortcut out of the request.
  const params = new URLSearchParams(Object.entries(guestFilters).filter(([name, value]) => name !== 'range' && value));
  // Convert the selected bounded time window into the contract's inclusive UTC lower bound.
  if (guestFilters.range) params.set('since', new Date(Date.now() - Number(guestFilters.range) * 86400000).toISOString());
  // Load the bounded, non-resumable summary through the Admin-only v2 endpoint.
  const data = await api(`/api/v2/admin/guest-trials?${params.toString()}`);
  // Stop when another tab took over during the async load.
  if (!isActiveTab('guests')) return;
  // Read the summary totals used by the funnel tiles.
  const summary = data.guest_trials || {};
  // Read the milestone funnel and cleanup health with safe defaults.
  const funnel = summary.funnel || {};
  // Read de-identified per-game aggregate rows.
  const games = summary.games || [];
  // Read retention health without exposing runtime paths or exception text.
  const cleanup = summary.cleanup || {};
  // Render filters, funnel, game aggregates, recent rows, detail, and retention health without identity columns.
  view.innerHTML = `<section class="admin-card guest-filter-card" data-testid="admin-guest-filters"><div class="guest-filter-grid"><label>${safe(t('guests.filterLocale', {}, 'admin'))}<select id="guest-filter-locale">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.locale)}${localeOptions(guestFilters.locale)}</select></label><label>${safe(t('guests.filterDevice', {}, 'admin'))}<select id="guest-filter-device">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.device)}${option('desktop', t('guests.deviceDesktop', {}, 'admin'), guestFilters.device)}${option('tablet', t('guests.deviceTablet', {}, 'admin'), guestFilters.device)}${option('mobile', t('guests.deviceMobile', {}, 'admin'), guestFilters.device)}</select></label><label>${safe(t('guests.filterStatus', {}, 'admin'))}<select id="guest-filter-status">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.status)}${option('active', t('guests.statusActive', {}, 'admin'), guestFilters.status)}${option('ended', t('guests.statusEnded', {}, 'admin'), guestFilters.status)}</select></label><button id="guest-cleanup" type="button" data-testid="admin-guest-cleanup">${safe(t('guests.cleanupRun', {}, 'admin'))}</button></div></section><div class="admin-card-grid" data-testid="admin-guest-summary"><div class="admin-card"><b>${safe(t('guests.started', {}, 'admin'))}</b><h2 data-testid="admin-guest-started">${formatNumber(funnel.started || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.engaged', {}, 'admin'))}</b><h2 data-testid="admin-guest-engaged">${formatNumber(funnel.engaged || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.completed', {}, 'admin'))}</b><h2 data-testid="admin-guest-completed">${formatNumber(funnel.completed_round || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.activeNow', {}, 'admin'))}</b><h2 data-testid="admin-guest-active">${formatNumber(summary.active_now || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.ended', {}, 'admin'))}</b><h2 data-testid="admin-guest-ended">${formatNumber(summary.ended_total || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.expired', {}, 'admin'))}</b><h2 data-testid="admin-guest-expired">${formatNumber(summary.expired_total || 0)}</h2></div></div><section class="admin-card" data-testid="admin-guest-games"><h3>${safe(t('guests.gamesTitle', {}, 'admin'))}</h3>${games.length ? table([t('guests.colGame', {}, 'admin'), t('guests.colTrials', {}, 'admin'), t('guests.colOpens', {}, 'admin'), t('guests.colActions', {}, 'admin'), t('guests.colRounds', {}, 'admin')], games.map(row => `<tr><td>${safe(humanLabel(row.game))}</td><td>${formatNumber(row.trials)}</td><td>${formatNumber(row.opens)}</td><td>${formatNumber(row.actions)}</td><td>${formatNumber(row.rounds_completed)}</td></tr>`)) : emptyState(t('guests.gamesEmpty', {}, 'admin'), t('guests.gamesEmptyDetail', {}, 'admin'), 'admin-guest-games-empty')}</section><section class="admin-card" data-testid="admin-guest-recent"><h3>${safe(t('guests.recentTitle', {}, 'admin'))}</h3>${(summary.recent || []).length ? table([t('guests.colId', {}, 'admin'), t('guests.colStarted', {}, 'admin'), t('guests.colLocale', {}, 'admin'), t('guests.colDevice', {}, 'admin'), t('guests.colReason', {}, 'admin'), t('guests.colActions', {}, 'admin'), t('guests.colRounds', {}, 'admin'), t('guests.colDetail', {}, 'admin')], summary.recent.map(row => `<tr data-testid="admin-guest-row"><td>${safe(row.analytics_id)}</td><td>${safe(row.started_at)}</td><td>${safe(row.locale)}</td><td>${safe(row.device)}</td><td>${safe(row.end_reason || t('guests.statusActive', {}, 'admin'))}</td><td>${formatNumber(row.actions || 0)}</td><td>${formatNumber(row.rounds_completed || 0)}</td><td><button class="guest-detail-button" data-id="${safe(row.analytics_id)}" type="button">${safe(t('guests.viewDetail', {}, 'admin'))}</button></td></tr>`)) : emptyState(t('guests.empty', {}, 'admin'), t('guests.emptyDetail', {}, 'admin'), 'admin-guest-empty')}</section><section id="guest-detail" class="admin-card" data-testid="admin-guest-detail" aria-live="polite"><h3>${safe(t('guests.detailTitle', {}, 'admin'))}</h3><p>${safe(t('guests.detailPrompt', {}, 'admin'))}</p></section><section class="admin-card" data-testid="admin-guest-cleanup-status" data-cleanup-failed="${cleanup.last_error === 'cleanup_failed'}"><h3>${safe(t('guests.cleanupTitle', {}, 'admin'))}</h3><p>${safe(t('guests.cleanupStatus', { raw: cleanup.raw_retention_days || 30, aggregate: cleanup.aggregate_retention_days || 400, time: cleanup.last_success_at || t('guests.cleanupNever', {}, 'admin'), failure: cleanup.last_failure_at || t('guests.cleanupNever', {}, 'admin') }, 'admin'))}</p></section>`;
  // Read the complete product metric summary with safe defaults.
  const metrics = summary.metrics || {};
  // Read percentage rates for every named funnel stage.
  const funnelRates = summary.funnel_rates || {};
  // Find the existing filter grid before appending the complete published filters.
  const filterGrid = view.querySelector('.guest-filter-grid');
  // Build catalog-game options from retained aggregate rows while preserving a selected empty result.
  const gameKeys = [...new Set([guestFilters.game, ...games.map(row => row.game)].filter(Boolean))].sort();
  // Append time, game, completion, and sanitized error filters without replacing the basic locale/device/lifecycle controls.
  filterGrid.insertAdjacentHTML('beforeend', `<label>${safe(t('guests.filterRange', {}, 'admin'))}<select id="guest-filter-range">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.range)}${option('1', t('guests.rangeDay', {}, 'admin'), guestFilters.range)}${option('7', t('guests.rangeWeek', {}, 'admin'), guestFilters.range)}${option('30', t('guests.rangeMonth', {}, 'admin'), guestFilters.range)}</select></label><label>${safe(t('guests.filterGame', {}, 'admin'))}<select id="guest-filter-game">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.game)}${gameKeys.map(game => option(game, humanLabel(game), guestFilters.game)).join('')}</select></label><label>${safe(t('guests.filterCompleted', {}, 'admin'))}<select id="guest-filter-completed">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.completed)}${option('yes', t('guests.filterYes', {}, 'admin'), guestFilters.completed)}${option('no', t('guests.filterNo', {}, 'admin'), guestFilters.completed)}</select></label><label>${safe(t('guests.filterError', {}, 'admin'))}<select id="guest-filter-error_category">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.error_category)}${['VALIDATION_ERROR','INSUFFICIENT_FUNDS','CONFLICT','FORBIDDEN','NOT_FOUND','RATE_LIMITED','SERVER_ERROR'].map(category => option(category, humanLabel(category), guestFilters.error_category)).join('')}</select></label>`);
  // Find the compact summary grid before adding full product-measurement cards.
  const summaryGrid = view.querySelector('[data-testid="admin-guest-summary"]');
  // Append duration, breadth, error-free, and fake-token cards explicitly labelled as simulator-only values.
  summaryGrid.insertAdjacentHTML('beforeend', `<div class="admin-card"><b>${safe(t('guests.averageDuration', {}, 'admin'))}</b><h2>${formatNumber(metrics.average_duration_seconds || 0)}s</h2></div><div class="admin-card"><b>${safe(t('guests.medianDuration', {}, 'admin'))}</b><h2>${formatNumber(metrics.median_duration_seconds || 0)}s</h2></div><div class="admin-card"><b>${safe(t('guests.gamesPerTrial', {}, 'admin'))}</b><h2>${formatNumber(metrics.average_games_per_trial || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.roundsPerTrial', {}, 'admin'))}</b><h2>${formatNumber(metrics.average_rounds_per_trial || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.errorFreeRate', {}, 'admin'))}</b><h2>${formatNumber(metrics.error_free_rate_percent || 0)}%</h2></div><div class="admin-card"><b>${safe(t('guests.fakeWagered', {}, 'admin'))}</b><h2>${formatMoney(metrics.wagered || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.fakeReturned', {}, 'admin'))}</b><h2>${formatMoney(metrics.returned || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.fakeNet', {}, 'admin'))}</b><h2>${formatMoney(metrics.net || 0)}</h2></div>`);
  // Define the full nine-stage funnel in the owner-approved product order.
  const funnelStages = ['landing_viewed','trial_started','lobby_reached','first_game_opened','first_action_accepted','first_round_completed','second_game_opened','trial_terminal','account_cta_viewed','account_cta_selected'];
  // Render the complete funnel with both counts and rates before game analytics.
  view.querySelector('[data-testid="admin-guest-games"]').insertAdjacentHTML('beforebegin', `<section class="admin-card" data-testid="admin-guest-funnel"><h3>${safe(t('guests.funnelTitle', {}, 'admin'))}</h3>${table([t('guests.funnelStage', {}, 'admin'), t('guests.funnelCount', {}, 'admin'), t('guests.funnelRate', {}, 'admin')], funnelStages.map(stage => `<tr><td>${safe(t(`guests.funnel.${stage}`, {}, 'admin'))}</td><td>${formatNumber(funnel[stage] || 0)}</td><td>${formatNumber(funnelRates[stage] || 0)}%</td></tr>`))}</section>`);
  // Render complete per-game acceptance metrics separately from the compact compatibility table.
  view.querySelector('[data-testid="admin-guest-games"]').insertAdjacentHTML('afterend', `<section class="admin-card" data-testid="admin-guest-game-detail"><h3>${safe(t('guests.gameMetricsTitle', {}, 'admin'))}</h3>${games.length ? table([t('guests.colGame', {}, 'admin'), t('guests.colStartedRounds', {}, 'admin'), t('guests.colRounds', {}, 'admin'), t('guests.colAbandoned', {}, 'admin'), t('guests.colErrors', {}, 'admin'), t('guests.colFirstAction', {}, 'admin'), t('guests.colWagered', {}, 'admin'), t('guests.colReturned', {}, 'admin'), t('guests.colNet', {}, 'admin'), t('guests.colCategories', {}, 'admin')], games.map(row => `<tr><td>${safe(humanLabel(row.game))}</td><td>${formatNumber(row.rounds_started || 0)}</td><td>${formatNumber(row.rounds_completed || 0)}</td><td>${formatNumber(row.rounds_abandoned || 0)}</td><td>${formatNumber(row.errors || 0)}</td><td>${formatNumber(row.median_first_action_ms || 0)}ms</td><td>${formatMoney(row.wagered || 0)}</td><td>${formatMoney(row.returned || 0)}</td><td>${formatMoney(row.net || 0)}</td><td>${safe(Object.keys(row.action_categories || {}).map(humanLabel).join(', ') || '—')}</td></tr>`)) : emptyState(t('guests.gamesEmpty', {}, 'admin'), t('guests.gamesEmptyDetail', {}, 'admin'))}</section>`);
  // Make wide game, funnel, metric, and session tables named keyboard-scrollable regions.
  view.querySelectorAll('[data-testid="admin-guest-funnel"], [data-testid="admin-guest-games"], [data-testid="admin-guest-game-detail"], [data-testid="admin-guest-recent"]').forEach(region => { region.tabIndex = 0; region.setAttribute('role', 'region'); region.setAttribute('aria-label', region.querySelector('h3')?.textContent || t('nav.guests', {}, 'admin')); });
  // Reload the section when any allowlisted filter changes.
  ['locale', 'device', 'status', 'range', 'game', 'completed', 'error_category'].forEach(name => { view.querySelector(`#guest-filter-${name}`).onchange = event => { guestFilters[name] = event.target.value; void guests(); }; });
  // Bind de-identified detail buttons after rendering retained rows.
  view.querySelectorAll('.guest-detail-button').forEach(button => { button.onclick = () => showGuestDetail(button.dataset.id); });
  // Bind the idempotent retention action through the protected v2 endpoint.
  view.querySelector('#guest-cleanup').onclick = async () => { try { await post('/api/v2/admin/guest-trials/cleanup', {}); toast(t('guests.cleanupComplete', {}, 'admin'), true); } catch (_) { toast(t('guests.cleanupFailed', {}, 'admin')); } await guests(); };
}

// Render disabled-by-default private invitation readiness, issuance, and lifecycle controls. (INVITE-001, INVITE-005)
async function invitations() {
  // Set the localized invitation title and restricted-preview boundary.
  setTitle(t('invitations.title', {}, 'admin'), t('invitations.subtitle', {}, 'admin'));
  // Announce loading before the Admin-only diagnostic resolves.
  view.innerHTML = `<section class="admin-card loading-panel" data-testid="admin-invitation-loading" role="status"><h2>${safe(t('invitations.loadingTitle', {}, 'admin'))}</h2><p>${safe(t('invitations.loadingDetail', {}, 'admin'))}</p></section>`;
  // Load the bounded, recipient-masked lifecycle list through the additive v2 contract.
  const data = await api('/api/v2/admin/invitations?limit=100');
  // Stop a stale request from overwriting a newer selected tab.
  if (!isActiveTab('invitations')) return;
  // Normalize invitation rows defensively before rendering.
  const rows = Array.isArray(data.invitations) ? data.invitations : [];
  // Select one stable status for the readiness card.
  const readiness = !data.enabled ? 'disabled' : data.mail_status !== 'ready' ? 'release-held' : data.redemption_enabled ? 'ready' : 'redemption-held';
  // Render one secret-free readiness card, bounded create form, and keyboard-scrollable lifecycle region.
  view.innerHTML = `<section class="admin-card" data-testid="admin-invitations-${safe(readiness)}"><h2>${safe(t(`invitations.states.${readiness}`, {}, 'admin'))}</h2><p>${safe(t('invitations.boundary', {}, 'admin'))}</p><dl class="guest-detail-grid"><div><dt>${safe(t('invitations.issuance', {}, 'admin'))}</dt><dd>${safe(data.enabled ? t('common.enabled', {}, 'admin') : t('common.disabled', {}, 'admin'))}</dd></div><div><dt>${safe(t('invitations.redemption', {}, 'admin'))}</dt><dd>${safe(data.redemption_enabled ? t('common.enabled', {}, 'admin') : t('common.disabled', {}, 'admin'))}</dd></div><div><dt>${safe(t('invitations.delivery', {}, 'admin'))}</dt><dd>${safe(humanLabel(data.mail_status || 'unavailable'))}</dd></div><div><dt>${safe(t('invitations.recovery', {}, 'admin'))}</dt><dd>${formatNumber(data.recovery_required || 0)}</dd></div></dl></section><section class="admin-card" data-testid="admin-invitation-create"><h3>${safe(t('invitations.createTitle', {}, 'admin'))}</h3><div class="grid3"><label>${safe(t('invitations.recipient', {}, 'admin'))}<input id="invitation-recipient" type="email" autocomplete="off" maxlength="254" data-testid="admin-invitation-recipient"></label><label>${safe(t('invitations.locale', {}, 'admin'))}<select id="invitation-locale" data-testid="admin-invitation-locale">${localeOptions('en-US')}</select></label><button id="invitation-create" type="button" data-testid="admin-invitation-submit" ${data.enabled && data.mail_status === 'ready' ? '' : 'disabled'}>${safe(t('invitations.send', {}, 'admin'))}</button></div><p class="muted">${safe(t('invitations.createHelp', {}, 'admin'))}</p></section><section class="admin-card" data-testid="admin-invitation-list" tabindex="0" role="region" aria-label="${safe(t('invitations.listTitle', {}, 'admin'))}"><h3>${safe(t('invitations.listTitle', {}, 'admin'))}</h3>${rows.length ? table([t('invitations.recipient', {}, 'admin'), t('invitations.status', {}, 'admin'), t('invitations.delivery', {}, 'admin'), t('invitations.locale', {}, 'admin'), t('invitations.updated', {}, 'admin'), t('invitations.actions', {}, 'admin')], rows.map(row => `<tr data-testid="admin-invitation-row" data-status="${safe(row.status)}"><td>${safe(row.recipient_hint || t('invitations.masked', {}, 'admin'))}</td><td>${safe(humanLabel(row.status))}</td><td>${safe(humanLabel(row.delivery_status || 'none'))}</td><td>${safe(row.locale)}</td><td>${safe(row.updated_at || '')}</td><td><button type="button" class="invitation-resend" data-id="${safe(row.invitation_id)}" ${['pending','delivery_failed'].includes(row.status) && data.enabled ? '' : 'disabled'}>${safe(t('invitations.resend', {}, 'admin'))}</button><button type="button" class="invitation-revoke" data-id="${safe(row.invitation_id)}" ${['pending','delivery_failed'].includes(row.status) ? '' : 'disabled'}>${safe(t('invitations.revoke', {}, 'admin'))}</button></td></tr>`)) : emptyState(t('invitations.empty', {}, 'admin'), t('invitations.emptyDetail', {}, 'admin'), 'admin-invitation-empty')}</section>`;
  // Bind create only when the independently gated delivery foundation is ready.
  view.querySelector('#invitation-create').onclick = async () => {
    // Read the transient mailbox only at submit time.
    const recipientInput = view.querySelector('#invitation-recipient');
    // Build one caller-owned replay key without exposing it in the DOM.
    const payload = { recipient: recipientInput.value, locale: view.querySelector('#invitation-locale').value, idempotency_key: crypto.randomUUID() };
    // Disable duplicate clicks until the exact response settles.
    view.querySelector('#invitation-create').disabled = true;
    // Submit through the approved Admin v2 route.
    await post('/api/v2/admin/invitations', payload);
    // Clear the raw mailbox before any after-pass evidence can be captured.
    recipientInput.value = '';
    // Announce success without repeating the recipient.
    toast(t('invitations.created', {}, 'admin'), true);
    // Reload the privacy-safe lifecycle list.
    await invitations();
  };
  // Bind every eligible resend action to one fresh caller idempotency key.
  view.querySelectorAll('.invitation-resend').forEach(button => { button.onclick = async () => { button.disabled = true; await post(`/api/v2/admin/invitations/${encodeURIComponent(button.dataset.id)}/resend`, { idempotency_key: crypto.randomUUID() }); toast(t('invitations.resent', {}, 'admin'), true); await invitations(); }; });
  // Bind emergency revoke independently from issuance readiness.
  view.querySelectorAll('.invitation-revoke').forEach(button => { button.onclick = async () => { button.disabled = true; await post(`/api/v2/admin/invitations/${encodeURIComponent(button.dataset.id)}/revoke`, { idempotency_key: crypto.randomUUID() }); toast(t('invitations.revoked', {}, 'admin'), true); await invitations(); }; });
}

// Render one de-identified Guest Trials analytics detail record. (issue #317)
async function showGuestDetail(analyticsId) {
  // Load only the analytics-id route published by the Admin v2 contract.
  const data = await api(`/api/v2/admin/guest-trials/sessions/${encodeURIComponent(analyticsId)}`);
  // Read the retained aggregate row without assuming optional milestones exist.
  const row = data.guest_trial || {};
  // Read the stable live-region detail outlet.
  const detail = view.querySelector('#guest-detail');
  // Stop if the user changed tabs while the detail request was in flight.
  if (!detail) return;
  // Render bounded lifecycle, locale, device, and per-game counters without identity or credential fields.
  detail.innerHTML = `<h3>${safe(t('guests.detailTitle', {}, 'admin'))}</h3><dl class="guest-detail-grid"><div><dt>${safe(t('guests.colId', {}, 'admin'))}</dt><dd>${safe(row.analytics_id)}</dd></div><div><dt>${safe(t('guests.colLocale', {}, 'admin'))}</dt><dd>${safe(row.locale)}</dd></div><div><dt>${safe(t('guests.colDevice', {}, 'admin'))}</dt><dd>${safe(row.device)}</dd></div><div><dt>${safe(t('guests.colDuration', {}, 'admin'))}</dt><dd>${row.duration_seconds == null ? '—' : formatNumber(row.duration_seconds)}</dd></div><div><dt>${safe(t('guests.colActions', {}, 'admin'))}</dt><dd>${formatNumber(row.actions || 0)}</dd></div><div><dt>${safe(t('guests.colRounds', {}, 'admin'))}</dt><dd>${formatNumber(row.rounds_completed || 0)}</dd></div></dl>`;
  // Read the bounded allowlisted event timeline with a safe empty default.
  const events = Array.isArray(row.events) ? row.events : [];
  // Append fake-token aggregates and the allowlisted server timeline without rendering any auth identifier.
  detail.insertAdjacentHTML('beforeend', `<dl class="guest-detail-grid"><div><dt>${safe(t('guests.colStartingBalance', {}, 'admin'))}</dt><dd>${formatMoney(row.starting_balance || 0)}</dd></div><div><dt>${safe(t('guests.colEndingBalance', {}, 'admin'))}</dt><dd>${row.ending_balance == null ? safe(t('guests.notAvailable', {}, 'admin')) : formatMoney(row.ending_balance)}</dd></div><div><dt>${safe(t('guests.colWagered', {}, 'admin'))}</dt><dd>${formatMoney(row.wagered || 0)}</dd></div><div><dt>${safe(t('guests.colReturned', {}, 'admin'))}</dt><dd>${formatMoney(row.returned || 0)}</dd></div><div><dt>${safe(t('guests.colNet', {}, 'admin'))}</dt><dd>${formatMoney(row.net || 0)}</dd></div><div><dt>${safe(t('guests.colErrors', {}, 'admin'))}</dt><dd>${formatNumber(row.errors || 0)}</dd></div></dl><section data-testid="admin-guest-timeline"><h4>${safe(t('guests.timelineTitle', {}, 'admin'))}</h4>${events.length ? table([t('guests.timelineEvent', {}, 'admin'), t('guests.timelineTime', {}, 'admin'), t('guests.colGame', {}, 'admin'), t('guests.timelineCategory', {}, 'admin'), t('guests.filterError', {}, 'admin'), t('guests.timelineLatency', {}, 'admin')], events.map(event => `<tr><td>${safe(humanLabel(event.event))}</td><td>${safe(event.at)}</td><td>${safe(humanLabel(event.game || ''))}</td><td>${safe(humanLabel(event.action_category || ''))}</td><td>${safe(humanLabel(event.error_category || ''))}</td><td>${safe(humanLabel(event.latency_bucket || ''))}</td></tr>`)) : emptyState(t('guests.timelineEmpty', {}, 'admin'), t('guests.timelineEmptyDetail', {}, 'admin'))}</section>`);
  // Make the detail timeline keyboard-scrollable on narrow Admin viewports.
  detail.querySelector('[data-testid="admin-guest-timeline"]').tabIndex = 0;
}

// Define createUser to submit a new beta user through Admin.
async function createUser() {
  // Store payload from the rendered create-user form.
  const payload = { email: view.querySelector('#admin_user_email').value, display_name: view.querySelector('#admin_user_name').value, initial_tokens: Number(view.querySelector('#admin_user_tokens').value || 0), password: view.querySelector('#admin_user_password').value, role: view.querySelector('#admin_user_role').value, language: view.querySelector('#admin_user_language').value, format_locale: view.querySelector('#admin_user_format').value, terms_accepted: view.querySelector('#admin_user_terms').checked };
  // Create the user through the Admin API.
  const result = await post('/api/v1/admin/users', payload);
  // Store the one-time password so Admin can hand it to the beta user.
  lastUserPassword = result.temporary_password || '';
  // Show user creation feedback.
  toast('User created.', true);
  // Refresh the users table with the new account.
  await users();
}

// Define saveUserAccount to persist Admin role and lifecycle status controls.
async function saveUserAccount(button) {
  // Store the nearest rendered user row for control lookup.
  const row = button.closest('tr[data-user]');
  // Build the role list from the explicit Admin checkbox while preserving player membership.
  const roles = row.querySelector('.user-admin-role').checked ? ['admin'] : ['player'];
  // Build the v2 account payload with the selected lifecycle status.
  const payload = { status: row.querySelector('.user-status').value, roles };
  // Ask for confirmation before changing Admin privileges.
  if (!window.confirm(t('users.roleConfirm', {}, 'admin'))) return;
  // Persist through the protected v2 Admin account contract.
  await api(`/api/v2/admin/users/${encodeURIComponent(button.dataset.user)}`, { method: 'PATCH', body: payload });
  // Show localized account update feedback.
  toast(t('users.accountSaved', {}, 'admin'), true);
  // Refresh the users table after the change.
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
  view.innerHTML = `<section class="admin-card"><h3>${safe(t('ledger.title', {}, 'admin'))}</h3>${(data.ledger || []).length ? table([t('ledger.columns.time', {}, 'admin'), t('ledger.columns.player', {}, 'admin'), t('ledger.columns.game', {}, 'admin'), t('ledger.columns.round', {}, 'admin'), t('ledger.columns.type', {}, 'admin'), t('ledger.columns.amount', {}, 'admin'), t('ledger.columns.before', {}, 'admin'), t('ledger.columns.after', {}, 'admin')], data.ledger.slice().reverse().map(row => `<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(humanLabel(row.game))}</td><td>${safe(row.round_id)}</td><td data-testid="admin-ledger-event">${safe(ledgerEventLabel(row.transaction_type, row.game))}</td><td>${formatMoney(row.amount)}</td><td>${formatMoney(row.balance_before)}</td><td>${formatMoney(row.balance_after)}</td></tr>`)) : emptyState(t('ledger.emptyTitle', {}, 'admin'), t('ledger.emptyDetail', {}, 'admin'), 'admin-ledger-empty')}</section>`;
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

// Render transactional-mail diagnostics independently from Operations and OAuth health. (MAIL-003)
function mailDiagnosticsCard(data) {
  // Constrain backend status to the five contract-published low-cardinality states.
  const status = ['disabled', 'misconfigured', 'release_held', 'ready', 'unavailable'].includes(data?.status) ? data.status : 'unavailable';
  // Constrain the provider label so unexpected backend values never become translation keys.
  const provider = ['disabled', 'postmark', 'unrecognized'].includes(data?.provider) ? data.provider : 'unrecognized';
  // Normalize aggregate lifecycle counts without accepting record identifiers or negative values.
  const summary = data?.delivery_summary && typeof data.delivery_summary === 'object' ? data.delivery_summary : {};
  // Convert each published aggregate to a bounded non-negative display number.
  const count = key => Number.isInteger(summary[key]) && summary[key] >= 0 ? summary[key] : 0;
  // Map only contract-allowlisted reason codes to localized remediation copy.
  const reasons = Array.isArray(data?.reasons) ? data.reasons.filter(reason => ['feature_disabled', 'provider_not_configured', 'canonical_origin_invalid', 'sender_identity_invalid', 'provider_credential_missing', 'digest_key_invalid', 'network_release_held', 'state_recovery_required'].includes(reason)) : [];
  // Normalize the de-identified suppression count independently from lifecycle rows.
  const suppressedRecipients = Number.isInteger(data?.suppressed_recipients) && data.suppressed_recipients >= 0 ? data.suppressed_recipients : 0;
  // Render one explicit non-color state, aggregate-only lifecycle table, and suppression summary.
  return `<section class="admin-card ${['misconfigured', 'unavailable'].includes(status) ? 'danger' : ''}" data-testid="admin-mail-${status}"><div class="row"><div><h2>${safe(t('mail.title', {}, 'admin'))}</h2><p>${safe(t(`mail.detail.${status}`, {}, 'admin'))}</p></div><span class="badge">${safe(t(`mail.state.${status}`, {}, 'admin'))}</span></div>${table([t('mail.field', {}, 'admin'), t('mail.value', {}, 'admin')], [`<tr><td>${safe(t('mail.provider', {}, 'admin'))}</td><td>${safe(t(`mail.provider.${provider}`, {}, 'admin'))}</td></tr>`, `<tr><td>${safe(t('mail.sent', {}, 'admin'))}</td><td>${count('sent')}</td></tr>`, `<tr><td>${safe(t('mail.retryWait', {}, 'admin'))}</td><td>${count('retry_wait')}</td></tr>`, `<tr><td>${safe(t('mail.failed', {}, 'admin'))}</td><td>${count('failed')}</td></tr>`, `<tr><td>${safe(t('mail.uncertain', {}, 'admin'))}</td><td>${count('uncertain')}</td></tr>`])}<div data-testid="admin-mail-suppression-summary"><h3>${safe(t('mail.suppressionTitle', {}, 'admin'))}</h3><p>${safe(t('mail.suppressionCount', { count: suppressedRecipients }, 'admin'))}</p></div>${reasons.length ? `<h3>${safe(t('mail.attention', {}, 'admin'))}</h3><ul>${reasons.map(reason => `<li>${safe(t(`mail.reason.${reason}`, {}, 'admin'))}</li>`).join('')}</ul>` : ''}</section>`;
}

// Replace only the independent mail diagnostic card when its request settles.
function replaceMailDiagnosticsCard(data) {
  // Ignore a delayed response after the user has left Operations.
  if (!isActiveTab('operations')) return;
  // Find the loading/unavailable or prior mail card by its stable prefix.
  const card = view.querySelector('[data-testid^="admin-mail-"]');
  // Replace the mail card without rerendering Operations or OAuth diagnostics.
  if (card) card.outerHTML = mailDiagnosticsCard(data);
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
    view.innerHTML = `<section class="admin-card ${data.ready ? '' : 'danger'}" data-testid="admin-operations-${stateKey}"><div class="row"><div><h2>${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</h2><p>${safe(t(`operations.detail.${stateKey}`, {}, 'admin'))}</p></div><span class="badge" data-testid="admin-operations-state">${safe(t(`operations.symbol.${stateKey}`, {}, 'admin'))} ${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</span></div>${table([t('operations.field', {}, 'admin'), t('operations.value', {}, 'admin')], [`<tr><td>${safe(t('operations.storage', {}, 'admin'))}</td><td>${safe(providerLabel)}</td></tr>`, `<tr><td>${safe(t('operations.appVersion', {}, 'admin'))}</td><td>${safe(data.build.app_version)}</td></tr>`, `<tr><td>${safe(t('operations.buildSha', {}, 'admin'))}</td><td>${safe(buildSha)}</td></tr>`, `<tr><td>${safe(t('operations.lastHeartbeat', {}, 'admin'))}</td><td>${safe(heartbeat)}</td></tr>`])}${reasonLabels.length ? `<h3>${safe(t('operations.attention', {}, 'admin'))}</h3><ul>${reasonLabels.map(label => `<li>${safe(label)}</li>`).join('')}</ul>` : ''}</section>${oauthDiagnosticsCard(null)}${mailDiagnosticsCard(null)}`;
    // Start provider diagnostics only after Operations is visible and handle failure locally.
    api('/api/v2/admin/oauth/providers').then(replaceOAuthDiagnosticsCard).catch(() => replaceOAuthDiagnosticsCard(null));
    // Start secret-free mail diagnostics independently so failure affects only its own card.
    api('/api/v2/admin/mail/readiness').then(replaceMailDiagnosticsCard).catch(() => replaceMailDiagnosticsCard(null));
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
  // Store state so every locked formatter locale stays in sync with the registry.
  const state = getLocaleState();
  // Store browser option before installed locale options.
  const browser = option('browser', t('language.browserDefault', {}, 'admin'), selected);
  // De-duplicate formatter fallbacks such as Shahmukhi Punjabi using the declared Intl identity.
  const formatters = [...state.localeRegistry.reduce((entries, locale) => { if (!entries.has(locale.formatLocale)) entries.set(locale.formatLocale, locale); return entries; }, new Map()).values()];
  // Return browser plus every deterministic formatter option without enabling untranslated UI packs.
  return browser + formatters.map(locale => option(locale.formatLocale, `${locale.nativeLabel} (${locale.formatLocale})`, selected)).join('');
}

// Define languageCards to render installed locale readiness cards.
function languageCards(selected) {
  // Store state so installed locale metadata drives the cards.
  const state = getLocaleState();
  // Return one compact card per installed locale.
  return state.locales.map(locale => `<article class="bot-edit" data-locale-card="${safe(locale.id)}" lang="${safe(locale.id)}" dir="${safe(locale.dir)}"><div class="row"><h3 style="margin-right:auto">${safe(locale.nativeLabel)}</h3><span class="badge">${safe(t(locale.id === selected ? 'language.active' : 'language.ready', {}, 'admin'))}</span></div><p class="muted">${safe(t('language.installedDescription', { label: locale.label, fallback: locale.fallbackChain.join(' → ') }, 'admin'))}</p><div class="row"><span class="badge">${safe(locale.script)}</span><span class="badge">${safe(t(`language.review.${locale.reviewStatus}`, {}, 'admin'))}</span><span class="badge">${safe(t(locale.voiceReady ? 'language.voiceReady' : 'language.voiceCheck', {}, 'admin'))}</span><span class="badge">${safe(locale.dir.toUpperCase())}</span></div></article>`).join('');
}

// Define lockedLanguageGrid to render the complete owner-approved 25-locale registry.
function lockedLanguageGrid() {
  // Store state so every locked identity and readiness value comes from the manifest.
  const state = getLocaleState();
  // Return one generic metadata card per registry identity without claiming translation completion.
  return `<div class="grid2" data-testid="admin-locale-registry">${state.localeRegistry.map(locale => `<article class="bot-edit" data-testid="admin-locale-registry-entry" data-locale-id="${safe(locale.id)}" lang="${safe(locale.id)}" dir="${safe(locale.dir)}"><div class="row"><span class="badge">#${formatNumber(locale.rank)}</span><strong style="margin-right:auto">${safe(locale.nativeLabel)}</strong><span class="badge">${safe(t(locale.uiReady ? 'language.ready' : 'language.metadataOnly', {}, 'admin'))}</span></div><p class="muted">${safe(locale.id)} · ${safe(locale.script)} · ${safe(locale.dir.toUpperCase())} · ${safe(locale.formatLocale)}</p></article>`).join('')}</div>`;
}

// Define diagnosticsTable to render current runtime diagnostic values.
function diagnosticsTable(state) {
  // Return diagnostics in the same mini-table style as other Admin views.
  return table([t('language.diagnostics', {}, 'admin'), 'Value'], [`<tr><td>${safe(t('language.registryVersion', {}, 'admin'))}</td><td>${safe(state.registryVersion)}</td></tr>`, `<tr><td>${safe(t('language.resolvedLocale', {}, 'admin'))}</td><td data-testid="admin-locale-state">${safe(state.locale)}</td></tr>`, `<tr><td>${safe(t('language.fallbackLocale', {}, 'admin'))}</td><td>${safe(state.fallbackLocale)}</td></tr>`, `<tr><td>${safe(t('language.installedLocales', {}, 'admin'))}</td><td data-testid="admin-locale-ready-count">${formatNumber(state.locales.length)} / ${formatNumber(state.localeRegistry.length)}</td></tr>`, `<tr><td>${safe(t('language.registeredDomains', {}, 'admin'))}</td><td>${formatNumber(state.registeredDomains.length)}</td></tr>`, `<tr><td>${safe(t('language.loadedDomains', {}, 'admin'))}</td><td>${safe(state.loadedDomains.join(', '))}</td></tr>`, `<tr><td>${safe(t('language.missingKeys', {}, 'admin'))}</td><td>${formatNumber(state.missingKeyCount)}</td></tr>`]);
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
  view.innerHTML = `<div class="admin-split" data-testid="admin-localization-foundation"><section class="admin-card"><div class="row"><h3 style="margin-right:auto">${safe(t('language.availableTitle', {}, 'admin'))}</h3><span class="badge">${safe(t('language.readyCount', { ready: state.locales.length, total: state.localeRegistry.length }, 'admin'))}</span></div><div class="grid2">${languageCards(selectedLanguage)}</div><h3>${safe(t('language.registryTitle', {}, 'admin'))}</h3>${lockedLanguageGrid()}</section><section class="admin-card"><h3>${safe(t('language.localeSettings', {}, 'admin'))}</h3><div class="grid2 locale-settings-grid"><label>${safe(t('language.displayLanguage', {}, 'admin'))}<select id="admin_language" data-testid="admin-language-select">${localeOptions(selectedLanguage)}</select></label><label>${safe(t('language.formatLocale', {}, 'admin'))}<select id="admin_format_locale" data-testid="admin-format-locale-select">${formatLocaleOptions(selectedFormat)}</select></label></div><label><input id="admin_use_browser" type="checkbox" ${settings.useBrowserLocale ? 'checked' : ''}> ${safe(t('language.useBrowser', {}, 'admin'))}</label><label><input id="admin_persist_browser" type="checkbox" checked> ${safe(t('language.persistBrowser', {}, 'admin'))}</label><div class="result-box"><p data-testid="admin-money-preview">${safe(t('language.previewBalance', { amount: formatMoney(5030) }, 'admin'))}</p><p>${safe(t('language.datePreview', {}, 'admin'))}: ${safe(formatDate(new Date(), { dateStyle: 'medium', timeStyle: 'short' }))}</p></div><div class="row"><button id="admin_apply_locale" data-testid="admin-locale-apply" class="gold">${safe(t('language.apply', {}, 'admin'))}</button><button id="admin_save_locale" data-testid="admin-locale-save">${safe(t('language.saveBrowser', {}, 'admin'))}</button><button id="admin_reset_locale" data-testid="admin-locale-reset">${safe(t('language.resetBrowser', {}, 'admin'))}</button><button id="admin_preview_lobby">${safe(t('actions.previewLobby'))}</button></div>${diagnosticsTable(state)}<h3>${safe(t('language.stringPreview', {}, 'admin'))}</h3><div class="bot-edit"><b>English</b><p>Choose your table. All games use play tokens only. Ledger-backed outcomes are visible in Admin.</p></div><div class="bot-edit"><b>Русский</b><p>Выберите стол. Все игры используют только игровые токены. Результаты с учётом ledger видны в Admin.</p></div><div class="bot-edit"><b>${safe(t('language.fallback', {}, 'admin'))}</b><p>${safe(t('language.fallbackDescription', {}, 'admin'))}</p></div></section></div>`;
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
  await initI18n({ domains: ['admin', 'feedback'] });
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
