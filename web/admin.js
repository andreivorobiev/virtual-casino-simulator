// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Import API helpers so Admin tabs continue using the frozen v1 contract.
import { api, post } from './core/api.js';
// Import escape-by-default templates, the staged escaped-text adapter, and transient status. (CORE-033)
import { escaped as safe, html, raw, toast } from './core/ui.js';
// Import listener-free label helpers so Admin never renders raw all-caps ledger enums.
import { humanLabel, ledgerEventLabel as localizedLedgerEventLabel } from './core/admin_labels.js';
// Import the first per-tab renderer so the Admin dispatcher can stay behaviorally stable while the monolith is split. (ADMIN-027)
import { createLedgerTab } from './admin/ledger.js';
// Import the History renderer so diagnostics retain exact output behind a reviewable per-tab boundary. (ADMIN-029)
import { createHistoryTab } from './admin/history.js';
// Import the Tests renderer so latest-result diagnostics retain exact output behind a reviewable per-tab boundary. (ADMIN-011, ADMIN-029)
import { createTestsTab } from './admin/tests.js';
// Import the Requirements renderer so coverage rows retain exact localized output behind a reviewable per-tab boundary. (ADMIN-010, ADMIN-021)
import { createRequirementsTab } from './admin/requirements.js';
// Import the Game States renderer so nested diagnostics retain exact output behind a reviewable per-tab boundary. (ADMIN-009, ADMIN-018, ADMIN-029)
import { createStatesTab } from './admin/states.js';
// Import the Autoplay renderer so session controls retain exact output behind a reviewable per-tab boundary. (AUTO-007, AUTO-008)
import { createAutoplayTab } from './admin/autoplay.js';
// Import the System renderer so canonical module revisions retain exact output behind a reviewable per-tab boundary. (ADMIN-004, ADMIN-014)
import { createSystemTab } from './admin/system.js';
// Import the Economics renderer so payout-rate summary and detail output retain their exact per-tab boundary. (ADMIN-030)
import { createEconomicsTab } from './admin/economics.js';
// Import the Launch Readiness renderer so its held-only visibility contract stays behind a reviewable per-tab boundary. (AUTH-016)
import { createLaunchReadinessTab } from './admin/launch-readiness.js';
// Import voice helpers so the existing Audio & Voice tab keeps its behavior.
import { availableVoices, loadVoiceSettings, saveVoiceSettings, speak } from './core/voice.js';
// Import i18n helpers so Admin can switch language without reloading or remounting.
import { applyTranslations, formatDate, formatMoney, formatNumber, getLocaleSettings, getLocaleState, initI18n, onLocaleChange, resetLocaleSettings, setLocale, t } from './core/i18n.js';

// Store current so refresh and locale rerendering preserve the active Admin tab.
let current = 'dashboard';
// Store lastUserPassword so Admin can see the latest one-time credential after rerender.
let lastUserPassword = '';
// Increment the Users-render revision so an older same-tab response cannot overwrite a newer account mutation.
let usersRenderRevision = 0;
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
const pre = object => html`<pre class="logview">${safe(JSON.stringify(object, null, 2))}</pre>`;
// Define table to render escaped mini tables while preserving existing Admin density.
const table = (heads, rows) => html`<table class="mini-table"><tr>${heads.map(head => html`<th>${safe(head)}</th>`)}</tr>${rows}</table>`;
// Define option to render a selected-safe select option.
const option = (value, label, selected) => html`<option value="${safe(value)}" ${selected === value ? 'selected' : ''}>${safe(label)}</option>`;

// Define ledgerEventLabel to bind the listener-free classifier to the active Admin locale.
const ledgerEventLabel = (value, game) => localizedLedgerEventLabel(value, game, (key, params) => t(key, params, 'admin'));
// Define emptyState to replace raw empty arrays with a calm, actionable Admin message.
const emptyState = (titleText, detailText, testId = '') => html`<div class="admin-empty-state"${testId ? html` data-testid="${safe(testId)}"` : ''}><div><strong>${safe(titleText)}</strong><p>${safe(detailText)}</p></div></div>`;

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
    return html`<article class="admin-event"><strong>${safe(humanLabel(event.event || event.level || 'System event'))}</strong><p>${safe(details || 'Recorded successfully.')}</p><time>${safe(event.ts || 'Time unavailable')}</time></article>`;
  }); // Finish the event-card markup before wrapping the list.
  // Return the complete readable event list.
  return html`<div class="admin-event-list" data-testid="${safe(testId)}">${rows}</div>`;
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

// Bind the Ledger renderer to the shared Admin-shell helpers without exposing mutable globals to the per-tab module. (ADMIN-027)
const ledger = createLedgerTab({ api, emptyState, formatMoney, html, humanLabel, ledgerEventLabel, safe, setTitle, t, table, view });
// Bind the History renderer to the same Admin-shell helpers used by the accepted monolith implementation. (ADMIN-029)
const history = createHistoryTab({ api, emptyState, formatMoney, html, humanLabel, safe, setTitle, t, table, view });
// Bind the Tests renderer to the same Admin-shell helpers used by the accepted monolith implementation. (ADMIN-011, ADMIN-029)
const tests = createTestsTab({ api, emptyState, html, pre, safe, setTitle, t, view });
// Bind the Requirements renderer to the accepted locale, table, and Admin-shell boundaries. (ADMIN-010, ADMIN-021, I18N-014)
const requirements = createRequirementsTab({ api, html, safe, setTitle, t, table, view });
// Bind the Game States renderer to the accepted diagnostics and empty-state helpers. (ADMIN-009, ADMIN-018, ADMIN-029)
const states = createStatesTab({ api, emptyState, html, pre, safe, setTitle, t, table, view });
// Bind the Autoplay renderer to the accepted session, mutation, locale, and toast boundaries. (AUTO-007, AUTO-008, I18N-014)
const autoplay = createAutoplayTab({ api, html, post, safe, setTitle, t, table, toast, view });
// Bind the System renderer to the accepted dashboard, stale-tab, module-table, and diagnostic boundaries. (ADMIN-004, ADMIN-014, TEST-186)
const system = createSystemTab({ api, html, isActiveTab, pre, safe, setTitle, t, table, view });
// Bind the Economics renderer to the accepted summary, drill-down, escaping, and empty-state boundaries. (ADMIN-030, TEST-146)
const economics = createEconomicsTab({ api, emptyState, html, humanLabel, safe, setTitle, t, table, view });
// Bind the Launch Readiness renderer to the accepted read-only route, stale-tab guard, and compact card boundary. (AUTH-016)
const launchReadiness = createLaunchReadinessTab({ api, html, humanLabel, isActiveTab, safe, setTitle, t, table, view });

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
    // Await the owner-only administrator delegation workspace.
    if (tab === 'administrators') return await administrators();
    // Await the owner-only enrollment policy and readiness workspace.
    if (tab === 'enrollment') return await enrollment();
    // Await the read-only launch readiness dashboard.
    if (tab === 'launch') return await launchReadiness();
    // Await the owner-gated session policy so authorization errors stay inside the localized boundary. (SESSION-009)
    if (tab === 'sessions') return await sessions();
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
    // Await the payout-rate economics renderer inside the shared load-error boundary. (ADMIN-030)
    if (tab === 'economics') return await economics();
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
    view.innerHTML = html`<section class="admin-card danger" data-testid="admin-load-error"><h2>${safe(t('common.loadErrorTitle', {}, 'admin'))}</h2><p>${safe(t('common.loadErrorDetail', {}, 'admin'))}</p></section>`;
  }
}

// Render one governed select from a fixed value list.
function feedbackSelect(id, values, selected, emptyLabel, keyPrefix = '') {
  // Build the optional all-values row only for filter controls.
  const emptyOption = emptyLabel ? html`<option value="">${safe(emptyLabel)}</option>` : '';
  // Return stable human-readable options without an invalid empty choice in detail forms.
  return html`<select id="${safe(id)}">${emptyOption}${values.map(value => option(value, keyPrefix ? t(`${keyPrefix}.${value}`, {}, 'feedback') : humanLabel(value), selected))}</select>`;
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
  const rows = (data.reports || []).map(report => html`<tr><td><button type="button" class="feedback-link" data-feedback-id="${safe(report.report_id)}">${safe(report.reference)}</button></td><td><span class="badge">${safe(report.priority)}</span></td><td>${safe(t(`feedback.status.${report.status}`, {}, 'feedback'))}</td><td>${safe(t(`feedback.category.${report.category}`, {}, 'feedback'))}</td><td>${safe(t(`feedback.impact.${report.impact}`, {}, 'feedback'))}</td><td>${safe(report.reporter_reference)}</td><td>${safe(report.summary)}</td><td>${safe(report.route)}</td><td>${safe(report.created_at)}</td></tr>`);
  // Render filters, the readable empty state, or the inbox table.
  view.innerHTML = html`<section class="admin-card feedback-inbox" data-testid="admin-feedback-inbox"><div class="feedback-filters"><label>${safe(t('feedback.admin.priority', {}, 'feedback'))}${feedbackSelect('feedback-priority-filter', data.priorities || ['P1', 'P2', 'P3'], feedbackFilters.priority, t('feedback.admin.all', {}, 'feedback'))}</label><label>${safe(t('feedback.admin.status', {}, 'feedback'))}${feedbackSelect('feedback-status-filter', data.statuses || [], feedbackFilters.status, t('feedback.admin.all', {}, 'feedback'), 'feedback.status')}</label><label>${safe(t('feedback.admin.category', {}, 'feedback'))}${feedbackSelect('feedback-category-filter', data.categories || [], feedbackFilters.category, t('feedback.admin.all', {}, 'feedback'), 'feedback.category')}</label><label>${safe(t('feedback.admin.impact', {}, 'feedback'))}${feedbackSelect('feedback-impact-filter', data.impacts || [], feedbackFilters.impact, t('feedback.admin.all', {}, 'feedback'), 'feedback.impact')}</label><label>${safe(t('feedback.admin.locale', {}, 'feedback'))}${feedbackSelect('feedback-locale-filter', getLocaleState().locales.map(locale => locale.id), feedbackFilters.locale, t('feedback.admin.all', {}, 'feedback'))}</label><label>${safe(t('feedback.admin.routeFilter', {}, 'feedback'))}<input id="feedback-route-filter" value="${safe(feedbackFilters.route)}" maxlength="120"></label><label>${safe(t('feedback.admin.reporter', {}, 'feedback'))}<input id="feedback-reporter-filter" value="${safe(feedbackFilters.reporter)}" pattern="USR-[A-F0-9]{16}"></label><label>${safe(t('feedback.admin.createdFrom', {}, 'feedback'))}<input id="feedback-created-from-filter" type="datetime-local" value="${safe(feedbackFilters.created_from)}"></label><label>${safe(t('feedback.admin.createdTo', {}, 'feedback'))}<input id="feedback-created-to-filter" type="datetime-local" value="${safe(feedbackFilters.created_to)}"></label><button id="feedback-apply-filters" type="button">${safe(t('feedback.admin.apply', {}, 'feedback'))}</button><button id="feedback-cleanup" type="button">${safe(t('feedback.admin.cleanup', {}, 'feedback'))}</button></div>${rows.length ? html`<div class="feedback-table-scroll" tabindex="0" role="region" aria-label="${safe(t('feedback.admin.tableLabel', {}, 'feedback'))}">${table([t('feedback.admin.reference', {}, 'feedback'), t('feedback.admin.priority', {}, 'feedback'), t('feedback.admin.status', {}, 'feedback'), t('feedback.admin.category', {}, 'feedback'), t('feedback.admin.impact', {}, 'feedback'), t('feedback.admin.reporter', {}, 'feedback'), t('feedback.admin.summary', {}, 'feedback'), t('feedback.admin.route', {}, 'feedback'), t('feedback.admin.created', {}, 'feedback')], rows)}</div>` : emptyState(t('feedback.admin.emptyTitle', {}, 'feedback'), t('feedback.admin.emptyCopy', {}, 'feedback'), 'admin-feedback-empty')}</section>`;
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
  const evidence = (report.attachments || []).map((attachment, index) => html`<figure><img src="data:${safe(attachment.media_type)};base64,${safe(attachment.data)}" alt="${safe(t('feedback.screenshotAlt', { number: index + 1 }, 'feedback'))}"><figcaption>${safe(attachment.width)} × ${safe(attachment.height)} · ${safe(attachment.bytes)} bytes</figcaption></figure>`);
  // Render report prose, controlled workflow fields, internal notes, and manual GitHub linkage.
  view.innerHTML = html`<section class="admin-card feedback-detail" data-testid="admin-feedback-detail"><div class="row"><button id="feedback-back" type="button">${safe(t('feedback.admin.back', {}, 'feedback'))}</button><span class="badge">${safe(report.reference)}</span><span class="badge">${safe(t(`feedback.category.${report.category}`, {}, 'feedback'))}</span><span class="badge">${safe(t(`feedback.impact.${report.impact}`, {}, 'feedback'))}</span><span class="badge">${safe(report.reporter_reference)}</span></div><h2>${safe(report.summary)}</h2><div class="admin-split"><section><h3>${safe(t('feedback.admin.actual', {}, 'feedback'))}</h3><p class="feedback-prose">${safe(report.actual)}</p><h3>${safe(t('feedback.admin.expected', {}, 'feedback'))}</h3><p class="feedback-prose">${safe(report.expected)}</p><h3>${safe(t('feedback.admin.context', {}, 'feedback'))}</h3>${table([t('feedback.admin.field', {}, 'feedback'), t('feedback.admin.value', {}, 'feedback')], Object.entries(report.context || {}).map(([key, value]) => html`<tr><td>${safe(humanLabel(key))}</td><td>${safe(value)}</td></tr>`))}</section><section class="feedback-triage"><label>${safe(t('feedback.admin.priority', {}, 'feedback'))}${feedbackSelect('feedback-detail-priority', ['P1', 'P2', 'P3'], report.priority, '')}</label><label>${safe(t('feedback.admin.status', {}, 'feedback'))}${feedbackSelect('feedback-detail-status', ['new', 'triaged', 'linked', 'resolved', 'duplicate', 'rejected'], report.status, '', 'feedback.status')}</label><label>${safe(t('feedback.admin.notes', {}, 'feedback'))}<textarea id="feedback-admin-notes" maxlength="4000" rows="7">${safe(report.admin_notes || '')}</textarea></label><label>${safe(t('feedback.admin.githubUrl', {}, 'feedback'))}<input id="feedback-github-url" type="url" value="${safe(report.github_issue_url || '')}" placeholder="https://github.com/andreivorobiev/virtual-casino-simulator/issues/…"></label><p class="muted">${safe(t('feedback.admin.manualOnly', {}, 'feedback'))}</p><button id="feedback-save" class="gold" type="button">${safe(t('feedback.admin.save', {}, 'feedback'))}</button><button id="feedback-draft" type="button">${safe(t('feedback.admin.prepareDraft', {}, 'feedback'))}</button><button id="feedback-export" type="button">${safe(t('feedback.admin.export', {}, 'feedback'))}</button><button id="feedback-delete" class="danger" type="button">${safe(t('feedback.admin.delete', {}, 'feedback'))}</button></section></div><h3>${safe(t('feedback.admin.screenshots', {}, 'feedback'))}</h3><div class="feedback-evidence">${evidence || html`<p class="muted">${safe(t('feedback.admin.noScreenshots', {}, 'feedback'))}</p>`}</div><div id="feedback-github-draft" class="feedback-draft" hidden></div></section>`;
  // Return to the filtered inbox without losing filter state.
  view.querySelector('#feedback-back').onclick = feedbackReports;
  // Persist controlled triage fields and redraw from the server response.
  view.querySelector('#feedback-save').onclick = async () => { await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`, { method: 'PATCH', body: { idempotency_key: feedbackActionKey(), priority: view.querySelector('#feedback-detail-priority').value, status: view.querySelector('#feedback-detail-status').value, admin_notes: view.querySelector('#feedback-admin-notes').value, github_issue_url: view.querySelector('#feedback-github-url').value } }); toast(t('feedback.admin.saved', {}, 'feedback'), true); feedbackDetail(reportId); };
  // Prepare a sanitized manual GitHub draft without publishing externally.
  view.querySelector('#feedback-draft').onclick = async () => { const prepared = await post(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}/github-draft`, {}); const draft = prepared.draft || {}; const outlet = view.querySelector('#feedback-github-draft'); outlet.hidden = false; outlet.innerHTML = html`<h3>${safe(t('feedback.admin.draftTitle', {}, 'feedback'))}</h3><p class="muted">${safe(t('feedback.admin.manualOnly', {}, 'feedback'))}</p><label>${safe(t('feedback.admin.issueTitle', {}, 'feedback'))}<input id="feedback-draft-title" readonly value="${safe(draft.title || '')}"></label><label>${safe(t('feedback.admin.issueBody', {}, 'feedback'))}<textarea id="feedback-draft-body" readonly rows="14">${safe(draft.body || '')}</textarea></label><p>${safe(t('feedback.admin.labels', {}, 'feedback'))}: ${safe((draft.labels || []).join(', '))}</p><div class="row"><button id="feedback-copy-draft" type="button">${safe(t('feedback.admin.copyDraft', {}, 'feedback'))}</button></div>`; outlet.querySelector('#feedback-copy-draft').onclick = async () => { await navigator.clipboard.writeText(`${draft.title}\n\n${draft.body}`); toast(t('feedback.admin.copied', {}, 'feedback'), true); }; };
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
  view.innerHTML = html`<div class="admin-card-grid"><div class="admin-card"><b>App</b><h2>${safe(data.app_version)}</h2></div><div class="admin-card"><b>${safe(t('nav.players', {}, 'admin'))}</b><h2>${formatNumber(data.players.length)}</h2></div><div class="admin-card"><b>Bots</b><h2>${formatNumber(data.bots.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.activeAutoplay', {}, 'admin'))}</b><h2>${formatNumber(active.length)}</h2></div><div class="admin-card"><b>${safe(t('dashboard.errorsToday', {}, 'admin'))}</b><h2>${formatNumber((data.logs.errors || []).length)}</h2></div><div class="admin-card"><b>${safe(t('nav.requirements', {}, 'admin'))}</b><h2>${formatNumber(Object.values(data.requirement_counts || {}).reduce((sum, count) => sum + count, 0))}</h2></div></div><div class="admin-split"><section class="admin-card"><h3>${safe(t('dashboard.recentLedger', {}, 'admin'))}</h3>${(data.recent_ledger || []).length ? table([t('ledger.columns.time', {}, 'admin'), t('ledger.columns.player', {}, 'admin'), t('ledger.columns.game', {}, 'admin'), t('ledger.columns.type', {}, 'admin'), t('ledger.columns.amount', {}, 'admin')], data.recent_ledger.slice(-12).reverse().map(row => html`<tr><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(humanLabel(row.game))}</td><td data-testid="admin-ledger-event">${safe(ledgerEventLabel(row.transaction_type, row.game))}</td><td>${formatMoney(row.amount)}</td></tr>`)) : emptyState(t('ledger.emptyTitle', {}, 'admin'), t('ledger.emptyDetail', {}, 'admin'), 'admin-ledger-empty')}</section><section class="admin-card"><h3>${safe(t('dashboard.recentErrors', {}, 'admin'))}</h3>${eventList(data.logs.errors, 'No recent errors', 'The local casino has not recorded any application errors today.', 'admin-errors-empty', true)}</section></div>`;
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
  view.innerHTML = html`<section class="admin-card"><h3>${safe(t('nav.players', {}, 'admin'))}</h3>${table([t('players.id', {}, 'admin'), t('players.name', {}, 'admin'), t('players.type', {}, 'admin'), t('players.balance', {}, 'admin')], (data.players || []).map(player => html`<tr><td>${safe(player.player_id)}</td><td>${safe(player.display_name)}</td><td>${safe(player.type)}</td><td>${formatMoney(player.balance)}</td></tr>`))}</section><section class="admin-card"><h3>${safe(t('bots.controllers', {}, 'admin'))}</h3>${(data.bots || []).map(bot => html`<div class="bot-edit" data-bot="${safe(bot.bot_id)}"><div class="row"><b>${safe(bot.display_name)}</b><label><input type="checkbox" class="bot-enabled" ${bot.enabled ? 'checked' : ''}>${safe(t('bots.enabled', {}, 'admin'))}</label><span class="badge">${formatMoney(bot.balance)}</span></div>${gameOptions.map(game => html`<div class="row"><label>${safe(t('bots.strategy', { game }, 'admin'))} <select class="bot-strategy" data-game="${safe(game)}">${capabilities[game].strategies.map(strategy => html`<option value="${safe(strategy.id)}" ${bot.strategies?.[game] === strategy.id ? 'selected' : ''}>${safe(strategy.label)}</option>`)}</select></label><label>${safe(t('bots.stake', {}, 'admin'))} <input class="bot-stake" data-game="${safe(game)}" type="number" min="1" value="${safe(bot.stakes?.[game] || 5)}"></label></div>`)}<button class="save-bot" data-bot="${safe(bot.bot_id)}">${safe(t('bots.save', { name: bot.display_name }, 'admin'))}</button></div>`)}</section><section class="admin-card" data-testid="practice-opponent-admin"><div class="row"><div><h3>${safe(t('players.practiceTitle', {}, 'admin'))}</h3><p>${safe(t('players.practiceSubtitle', {}, 'admin'))}</p></div><button id="fund_practice_opponents" data-testid="fund-practice-opponents">${safe(t('players.fundPractice', {}, 'admin'))}</button></div>${table([t('players.seat', {}, 'admin'), t('players.account', {}, 'admin'), t('players.policy', {}, 'admin'), t('players.balance', {}, 'admin')], practiceAccounts.map(account => html`<tr data-testid="practice-opponent-account"><td>${safe(t('players.opponentSeat', { number: account.seat_id.split('_').pop() }, 'admin'))}</td><td>${safe(account.display_name)} (${safe(account.player_id)})</td><td>${safe(t('players.automaticCaller', {}, 'admin'))}</td><td>${formatNumber(account.balance)} ${safe(t('players.playTokens', {}, 'admin'))}</td></tr>`))}<h3>${safe(t('players.practiceActivity', {}, 'admin'))}</h3>${practiceActivity.length ? table([t('players.time', {}, 'admin'), t('players.account', {}, 'admin'), t('players.round', {}, 'admin'), t('players.action', {}, 'admin'), t('players.amount', {}, 'admin')], practiceActivity.slice().reverse().map(row => html`<tr data-testid="practice-opponent-activity"><td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(row.round_id || '—')}</td><td>${safe(practiceActionLabels[row.details?.controller_action] || humanLabel(row.transaction_type))}</td><td>${formatNumber(row.amount)} ${safe(t('players.playTokens', {}, 'admin'))}</td></tr>`)) : emptyState(t('players.noPracticeActivity', {}, 'admin'), t('players.noPracticeActivityDetail', {}, 'admin'), 'practice-opponent-empty')}</section>`;
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
  // Return one row per beta user with lifecycle, token, terms, and locale controls; roles live only in Administrators.
  return users.map(user => html`<tr data-testid="admin-user-row" data-user="${safe(user.user_id)}" data-email="${safe(user.email)}" data-status="${safe(user.status)}" data-terms="${safe(user.terms_status)}"><td>${safe(user.email)}</td><td>${safe(user.display_name)}</td><td class="admin-user-access-cell"><div class="admin-user-access-controls" data-testid="admin-user-access-controls"><select class="user-status" data-testid="admin-user-status">${['active', 'inactive', 'suspended', 'locked'].map(status => option(status, humanLabel(status), user.status))}</select><button class="save-user-account" data-user="${safe(user.user_id)}" data-testid="admin-user-save-account">${safe(t('users.saveAccount', {}, 'admin'))}</button></div></td><td data-testid="admin-user-token-balance">${formatMoney(user.token_balance)}</td><td>${safe(user.token_state)}</td><td>${safe(user.terms_status)}</td><td><select class="user-language">${localeOptions(user.language || 'en-US')}</select></td><td><select class="user-format">${formatLocaleOptions(user.format_locale || 'browser')}</select></td><td><button class="save-user-locale" data-user="${safe(user.user_id)}" data-testid="admin-user-save-locale">Save locale</button><button class="toggle-user" data-user="${safe(user.user_id)}" data-action="${user.status === 'active' ? 'deactivate' : 'reactivate'}" data-testid="admin-user-toggle">${user.status === 'active' ? 'Deactivate' : 'Reactivate'}</button><button class="reset-user-password" data-user="${safe(user.user_id)}" data-testid="admin-user-reset">Reset password</button><button class="terms-user" data-user="${safe(user.user_id)}" data-accepted="${user.terms_status !== 'accepted'}" data-testid="admin-user-terms">${user.terms_status === 'accepted' ? 'Clear terms' : 'Accept terms'}</button></td></tr>`);
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
  // Claim the latest Users-render revision before starting the asynchronous account read.
  const renderRevision = ++usersRenderRevision;
  // Remove the prior interactive account table immediately so a user cannot edit controls that an in-flight refresh will replace.
  view.replaceChildren();
  // Set the localized users title and subtitle.
  setTitle(t('users.title', {}, 'admin'), t('users.subtitle', {}, 'admin'));
  // Load users through the Admin user-management endpoint.
  const data = await api('/api/v1/admin/users');
  // Stop inactive-tab or superseded same-tab responses from overwriting the newest account state.
  if (!isActiveTab('users') || renderRevision !== usersRenderRevision) return;
  // Keep the visible table account-only even if an older server returns temporary guest principals.
  const managedUsers = (data.users || []).filter(isManagedAccountUser);
  // Store password notice so rerenders can show the latest one-time credential.
  const passwordNotice = lastUserPassword ? html`<div class="result-box" data-testid="admin-user-temp-password">Latest temporary password: ${safe(lastUserPassword)}</div>` : '';
  // Build an explicit handoff card so operators know temporary visitors live in Guest Trials.
  const guestSeparationCard = html`<section class="admin-card" data-testid="admin-users-guest-separation"><h3>${safe(t('users.guestSeparationTitle', {}, 'admin'))}</h3><p>${safe(t('users.guestSeparationCopy', {}, 'admin'))}</p><button id="admin_open_guest_trials" type="button" data-testid="admin-open-guest-trials">${safe(t('users.openGuestTrials', {}, 'admin'))}</button></section>`;
  // Build the account-only table inside one named keyboard-scrollable region, or show the calm empty state.
  const managedUserTable = managedUsers.length ? html`<div class="admin-users-table-scroll" data-testid="admin-users-managed-table" tabindex="0" role="region" aria-label="${safe(t('users.tableTitle', {}, 'admin'))}">${table([t('users.email', {}, 'admin'), t('users.name', {}, 'admin'), t('users.accessControls', {}, 'admin'), t('users.tokenBalance', {}, 'admin'), t('users.tokenState', {}, 'admin'), t('users.terms', {}, 'admin'), t('users.language', {}, 'admin'), t('users.format', {}, 'admin'), t('users.actions', {}, 'admin')], userRows(managedUsers))}</div>` : emptyState(t('users.emptyTitle', {}, 'admin'), t('users.emptyDetail', {}, 'admin'), 'admin-users-empty');
  // Render creation controls and token-state inspection table.
  view.innerHTML = html`${raw(guestSeparationCard)}<section class="admin-card" data-testid="admin-user-create"><h3>${safe(t('users.createTitle', {}, 'admin'))}</h3><div class="grid3"><label>Email<input id="admin_user_email" data-testid="admin-user-email" type="email" placeholder="beta@example.test"></label><label>Display name<input id="admin_user_name" data-testid="admin-user-name" placeholder="Beta Player"></label><label>Initial tokens<input id="admin_user_tokens" data-testid="admin-user-tokens" type="number" min="0" step="1" value="5000"></label></div><div class="grid3"><label>Temporary password<input id="admin_user_password" data-testid="admin-user-password" type="text" placeholder="Generate if blank"></label><label>${safe(t('users.initialRole', {}, 'admin'))}<input id="admin_user_role" data-testid="admin-user-role" value="player" readonly></label><label>Language<select id="admin_user_language" data-testid="admin-user-language">${localeOptions('en-US')}</select></label></div><div class="grid3"><label>Format locale<select id="admin_user_format" data-testid="admin-user-format">${formatLocaleOptions('browser')}</select></label></div><label><input id="admin_user_terms" data-testid="admin-user-terms-initial" type="checkbox"> Terms accepted</label><button id="admin_create_user" data-testid="admin-create-user" class="gold">${safe(t('users.createButton', {}, 'admin'))}</button>${passwordNotice}</section><section class="admin-card" data-testid="admin-users-managed-accounts"><h3>${safe(t('users.tableTitle', {}, 'admin'))}</h3>${managedUserTable}</section>`;
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

// Render owner-only ordinary-Admin delegation separately from general account lifecycle. (ADMIN-033)
async function administrators() {
  // Set an explicit privilege-management boundary in the Admin shell.
  setTitle(t('administrators.title', {}, 'admin'), t('administrators.subtitle', {}, 'admin'));
  // Read the current role revision and immutable audit together.
  const [data, historyData] = await Promise.all([api('/api/v2/admin/administrators'), api('/api/v2/admin/administrators/audit?limit=100')]);
  // Stop a stale role response from replacing another selected tab.
  if (!isActiveTab('administrators')) return;
  // Render eligible grants, current ordinary Admins, protected owners, and bounded audit evidence.
  view.innerHTML = html`<section class="admin-card" data-testid="admin-administrator-grant"><h3>${safe(t('administrators.grantTitle', {}, 'admin'))}</h3><label>${safe(t('administrators.account', {}, 'admin'))}<select id="administrator-target">${(data.eligible_accounts || []).map(account => option(account.user_id, `${account.display_name} (${account.email})`, ''))}</select></label><label>${safe(t('administrators.password', {}, 'admin'))}<input id="administrator-password" type="password" autocomplete="current-password"></label><label>${safe(t('administrators.reason', {}, 'admin'))}<input id="administrator-reason" maxlength="256"></label><button id="administrator-grant" type="button" data-testid="administrator-grant" ${(data.eligible_accounts || []).length ? '' : 'disabled'}>${safe(t('administrators.grant', {}, 'admin'))}</button></section><section class="admin-card" data-testid="admin-administrator-list"><h3>${safe(t('administrators.currentTitle', {}, 'admin'))}</h3>${(data.administrators || []).length ? table([t('administrators.account', {}, 'admin'), t('administrators.role', {}, 'admin'), t('administrators.action', {}, 'admin')], data.administrators.map(account => html`<tr><td>${safe(account.display_name)} (${safe(account.email)})</td><td>${safe((account.roles || []).join(', '))}</td><td>${account.protected_owner ? safe(t('administrators.protected', {}, 'admin')) : html`<button type="button" class="administrator-revoke" data-user="${safe(account.user_id)}">${safe(t('administrators.revoke', {}, 'admin'))}</button>`}</td></tr>`)) : emptyState(t('administrators.empty', {}, 'admin'), t('administrators.emptyDetail', {}, 'admin'))}</section><section class="admin-card" data-testid="admin-administrator-audit"><h3>${safe(t('administrators.auditTitle', {}, 'admin'))}</h3>${(historyData.audit || []).length ? table([t('administrators.time', {}, 'admin'), t('administrators.action', {}, 'admin'), t('administrators.target', {}, 'admin'), t('administrators.reason', {}, 'admin')], historyData.audit.map(row => html`<tr><td>${safe(row.at)}</td><td>${safe(humanLabel(row.action))}</td><td>${safe(row.target_user_id)}</td><td>${safe(row.reason)}</td></tr>`)) : emptyState(t('administrators.auditEmpty', {}, 'admin'), t('administrators.auditEmptyDetail', {}, 'admin'))}</section>`;
  // Apply one reauthenticated role transition and scrub the password immediately afterward.
  const changeRole = async (target, action) => {
    // Read the transient owner step-up and reason at explicit action time only.
    const password = view.querySelector('#administrator-password').value;
    // Read and trim the bounded audit reason.
    const reason = view.querySelector('#administrator-reason').value.trim();
    // Clear the password before awaiting network work so rerenders or evidence cannot retain it.
    view.querySelector('#administrator-password').value = '';
    // Commit through the exact owner-only action endpoint with optimistic revision and replay key.
    await post(`/api/v2/admin/administrators/${encodeURIComponent(target)}/${action}`, { password, reason, revision: data.revision, idempotency_key: crypto.randomUUID() });
    // Confirm the committed transition without reflecting sensitive request content.
    toast(t('administrators.saved', {}, 'admin'), true);
    // Reload from durable identity and audit state.
    await administrators();
  };
  // Bind the selected eligible account grant.
  view.querySelector('#administrator-grant').onclick = () => changeRole(view.querySelector('#administrator-target').value, 'grant');
  // Bind each non-owner revoke to the same reauthentication fields.
  view.querySelectorAll('.administrator-revoke').forEach(button => { button.onclick = () => changeRole(button.dataset.user, 'revoke'); });
}

// Render owner policy, readiness, preview, rollback inputs, and immutable change evidence. (AUTH-015)
async function enrollment() {
  // Set the enrollment-governance heading and restricted-preview boundary.
  setTitle(t('enrollment.title', {}, 'admin'), t('enrollment.subtitle', {}, 'admin'));
  // Read coherent enrollment policy, readiness, and separately governed provider kill switches.
  const [data, readiness, oauthControls] = await Promise.all([api('/api/v2/admin/enrollment-policy'), api('/api/v2/admin/enrollment-readiness'), api('/api/v2/admin/oauth/operational-controls')]);
  // Stop a stale enrollment request from replacing another selected tab.
  if (!isActiveTab('enrollment')) return;
  // Read the current durable policy once for controls and exact rollback input.
  const policy = data.policy || { mode: 'closed', methods: { email: false, google: false, facebook: false }, invitations_enabled: false };
  // Render policy controls, method-specific readiness, and verified audit without any launch action.
  view.innerHTML = html`<section class="admin-card" data-testid="admin-enrollment-policy"><h3>${safe(t('enrollment.policyTitle', {}, 'admin'))}</h3><label>${safe(t('enrollment.mode', {}, 'admin'))}<select id="enrollment-mode">${(data.modes || []).map(mode => option(mode, humanLabel(mode), policy.mode))}</select></label><div class="grid3">${(data.methods || []).map(method => html`<label class="check-row"><input id="enrollment-method-${safe(method)}" type="checkbox" ${policy.methods?.[method] ? 'checked' : ''}><span>${safe(humanLabel(method))}</span></label>`)}</div><label class="check-row"><input id="enrollment-invitations" type="checkbox" ${policy.invitations_enabled ? 'checked' : ''}><span>${safe(t('enrollment.invitations', {}, 'admin'))}</span></label><label>${safe(t('enrollment.reason', {}, 'admin'))}<input id="enrollment-reason" maxlength="256"></label><div class="row"><button id="enrollment-preview" type="button">${safe(t('enrollment.preview', {}, 'admin'))}</button><button id="enrollment-apply" type="button" class="gold">${safe(t('enrollment.apply', {}, 'admin'))}</button></div><div id="enrollment-preview-result" class="result-box" hidden></div></section><section class="admin-card" data-testid="admin-enrollment-readiness"><h3>${safe(t('enrollment.readinessTitle', {}, 'admin'))}</h3><p>${safe(readiness.live_enablement_authorized ? t('enrollment.authorized', {}, 'admin') : t('enrollment.held', {}, 'admin'))}</p>${table([t('enrollment.method', {}, 'admin'), t('enrollment.enabled', {}, 'admin'), t('enrollment.ready', {}, 'admin'), t('enrollment.blockers', {}, 'admin')], Object.entries(readiness.methods || {}).map(([method, row]) => html`<tr><td>${safe(humanLabel(method))}</td><td>${safe(String(row.enabled))}</td><td>${safe(String(row.ready))}</td><td>${safe((row.blockers || []).map(humanLabel).join(', ') || '—')}</td></tr>`))}</section><section class="admin-card" data-testid="admin-enrollment-audit"><h3>${safe(t('enrollment.auditTitle', {}, 'admin'))}</h3>${(data.audit || []).length ? table([t('enrollment.time', {}, 'admin'), t('enrollment.actor', {}, 'admin'), t('enrollment.reason', {}, 'admin')], data.audit.slice().reverse().map(row => html`<tr><td>${safe(row.at)}</td><td>${safe(row.actor_id)}</td><td>${safe(row.reason)}</td></tr>`)) : emptyState(t('enrollment.auditEmpty', {}, 'admin'), t('enrollment.auditEmptyDetail', {}, 'admin'))}</section>`;
  // Insert provider login kill switches as a distinct control plane after signup readiness.
  view.querySelector('[data-testid="admin-enrollment-readiness"]').insertAdjacentHTML('afterend', html`<section class="admin-card" data-testid="admin-oauth-operational-controls"><h3>${safe(t('enrollment.providerOperationsTitle', {}, 'admin'))}</h3><p>${safe(t('enrollment.providerOperationsHelp', {}, 'admin'))}</p><div class="grid3">${Object.entries(oauthControls.providers || {}).map(([provider, enabled]) => html`<label class="check-row"><input id="oauth-operational-${safe(provider)}" type="checkbox" ${enabled ? 'checked' : ''}><span>${safe(humanLabel(provider))}</span></label>`)}</div><label>${safe(t('enrollment.reason', {}, 'admin'))}<input id="oauth-operational-reason" maxlength="256"></label><div class="row"><button id="oauth-operational-preview" type="button">${safe(t('enrollment.preview', {}, 'admin'))}</button><button id="oauth-operational-apply" type="button" class="gold">${safe(t('enrollment.providerOperationsApply', {}, 'admin'))}</button></div><div id="oauth-operational-preview-result" class="result-box" hidden></div></section>`);
  // Build the exact complete proposal from visible owner controls.
  const changes = () => ({ mode: view.querySelector('#enrollment-mode').value, methods: Object.fromEntries((data.methods || []).map(method => [method, view.querySelector(`#enrollment-method-${method}`).checked])), invitations_enabled: view.querySelector('#enrollment-invitations').checked });
  // Preview through the same pure policy computation used by apply.
  view.querySelector('#enrollment-preview').onclick = async () => { const result = await post('/api/v2/admin/enrollment-policy/preview', { changes: changes() }); const outlet = view.querySelector('#enrollment-preview-result'); outlet.hidden = false; outlet.textContent = JSON.stringify(result.impact || {}, null, 2); };
  // Apply only after explicit browser confirmation and a bounded owner reason.
  view.querySelector('#enrollment-apply').onclick = async () => { if (!window.confirm(t('enrollment.confirm', {}, 'admin'))) return; await post('/api/v2/admin/enrollment-policy', { changes: changes(), confirm: true, reason: view.querySelector('#enrollment-reason').value.trim(), revision: data.revision }); toast(t('enrollment.saved', {}, 'admin'), true); await enrollment(); };
  // Build the independent operational-provider proposal without touching signup flags.
  const operationalChanges = () => Object.fromEntries(Object.keys(oauthControls.providers || {}).map(provider => [provider, view.querySelector(`#oauth-operational-${provider}`).checked]));
  // Preview exact existing-login lockout impact through the owner-only v2 route.
  view.querySelector('#oauth-operational-preview').onclick = async () => { const result = await post('/api/v2/admin/oauth/operational-controls/preview', { changes: operationalChanges() }); const outlet = view.querySelector('#oauth-operational-preview-result'); outlet.hidden = false; outlet.textContent = JSON.stringify(result.impact || {}, null, 2); };
  // Apply only after confirmation; the server still requires external readiness for any enablement.
  view.querySelector('#oauth-operational-apply').onclick = async () => { if (!window.confirm(t('enrollment.providerOperationsConfirm', {}, 'admin'))) return; await post('/api/v2/admin/oauth/operational-controls', { changes: operationalChanges(), confirm: true, reason: view.querySelector('#oauth-operational-reason').value.trim(), revision: oauthControls.revision }); toast(t('enrollment.providerOperationsSaved', {}, 'admin'), true); await enrollment(); };
}

// Render the de-identified Guest Trials telemetry section for account-free visitors. (issue #317)
async function guests() {
  // Set the localized Guest Trials heading and its measurement helper line.
  setTitle(t('nav.guests', {}, 'admin'), t('guests.subtitle', {}, 'admin'));
  // Announce an explicit localized loading state before the Admin-only request resolves.
  view.innerHTML = html`<section class="admin-card loading-panel" data-testid="admin-guest-loading" role="status"><h2>${safe(t('guests.loadingTitle', {}, 'admin'))}</h2><p>${safe(t('guests.loadingDetail', {}, 'admin'))}</p></section>`;
  // Encode only published filters while keeping the UI-only range shortcut out of the request.
  const params = new URLSearchParams(Object.entries(guestFilters).filter(([name, value]) => name !== 'range' && value));
  // Convert the selected bounded time window into the contract's inclusive UTC lower bound.
  if (guestFilters.range) params.set('since', new Date(Date.now() - Number(guestFilters.range) * 86400000).toISOString());
  // Load telemetry and the current admission control together so the Admin view is one coherent snapshot.
  const [data, settingsData] = await Promise.all([api(`/api/v2/admin/guest-trials?${params.toString()}`), api('/api/v2/admin/guest-trials/settings')]);
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
  // Read the owner-governed admission switch and fixed current token grant.
  const guestPolicy = settingsData.settings || { enabled: false, starting_balance: 10000 };
  // Render filters, funnel, game aggregates, recent rows, detail, and retention health without identity columns.
  view.innerHTML = html`<section class="admin-card guest-filter-card" data-testid="admin-guest-filters"><div class="guest-filter-grid"><label>${safe(t('guests.filterLocale', {}, 'admin'))}<select id="guest-filter-locale">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.locale)}${localeOptions(guestFilters.locale)}</select></label><label>${safe(t('guests.filterDevice', {}, 'admin'))}<select id="guest-filter-device">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.device)}${option('desktop', t('guests.deviceDesktop', {}, 'admin'), guestFilters.device)}${option('tablet', t('guests.deviceTablet', {}, 'admin'), guestFilters.device)}${option('mobile', t('guests.deviceMobile', {}, 'admin'), guestFilters.device)}</select></label><label>${safe(t('guests.filterStatus', {}, 'admin'))}<select id="guest-filter-status">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.status)}${option('active', t('guests.statusActive', {}, 'admin'), guestFilters.status)}${option('ended', t('guests.statusEnded', {}, 'admin'), guestFilters.status)}</select></label><button id="guest-cleanup" type="button" data-testid="admin-guest-cleanup">${safe(t('guests.cleanupRun', {}, 'admin'))}</button></div></section><div class="admin-card-grid" data-testid="admin-guest-summary"><div class="admin-card"><b>${safe(t('guests.started', {}, 'admin'))}</b><h2 data-testid="admin-guest-started">${formatNumber(funnel.started || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.engaged', {}, 'admin'))}</b><h2 data-testid="admin-guest-engaged">${formatNumber(funnel.engaged || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.completed', {}, 'admin'))}</b><h2 data-testid="admin-guest-completed">${formatNumber(funnel.completed_round || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.activeNow', {}, 'admin'))}</b><h2 data-testid="admin-guest-active">${formatNumber(summary.active_now || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.ended', {}, 'admin'))}</b><h2 data-testid="admin-guest-ended">${formatNumber(summary.ended_total || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.expired', {}, 'admin'))}</b><h2 data-testid="admin-guest-expired">${formatNumber(summary.expired_total || 0)}</h2></div></div><section class="admin-card" data-testid="admin-guest-games"><h3>${safe(t('guests.gamesTitle', {}, 'admin'))}</h3>${games.length ? table([t('guests.colGame', {}, 'admin'), t('guests.colTrials', {}, 'admin'), t('guests.colOpens', {}, 'admin'), t('guests.colActions', {}, 'admin'), t('guests.colRounds', {}, 'admin')], games.map(row => html`<tr><td>${safe(humanLabel(row.game))}</td><td>${formatNumber(row.trials)}</td><td>${formatNumber(row.opens)}</td><td>${formatNumber(row.actions)}</td><td>${formatNumber(row.rounds_completed)}</td></tr>`)) : emptyState(t('guests.gamesEmpty', {}, 'admin'), t('guests.gamesEmptyDetail', {}, 'admin'), 'admin-guest-games-empty')}</section><section class="admin-card" data-testid="admin-guest-recent"><h3>${safe(t('guests.recentTitle', {}, 'admin'))}</h3>${(summary.recent || []).length ? table([t('guests.colId', {}, 'admin'), t('guests.colStarted', {}, 'admin'), t('guests.colLocale', {}, 'admin'), t('guests.colDevice', {}, 'admin'), t('guests.colReason', {}, 'admin'), t('guests.colActions', {}, 'admin'), t('guests.colRounds', {}, 'admin'), t('guests.colDetail', {}, 'admin')], summary.recent.map(row => html`<tr data-testid="admin-guest-row"><td>${safe(row.analytics_id)}</td><td>${safe(row.started_at)}</td><td>${safe(row.locale)}</td><td>${safe(row.device)}</td><td>${safe(row.end_reason || t('guests.statusActive', {}, 'admin'))}</td><td>${formatNumber(row.actions || 0)}</td><td>${formatNumber(row.rounds_completed || 0)}</td><td><button class="guest-detail-button" data-id="${safe(row.analytics_id)}" type="button">${safe(t('guests.viewDetail', {}, 'admin'))}</button>${row.end_reason ? '' : html`<button class="guest-convert-button" data-id="${safe(row.analytics_id)}" type="button">${safe(t('guests.convertSelect', {}, 'admin'))}</button>`}</td></tr>`)) : emptyState(t('guests.empty', {}, 'admin'), t('guests.emptyDetail', {}, 'admin'), 'admin-guest-empty')}</section><section id="guest-detail" class="admin-card" data-testid="admin-guest-detail" aria-live="polite"><h3>${safe(t('guests.detailTitle', {}, 'admin'))}</h3><p>${safe(t('guests.detailPrompt', {}, 'admin'))}</p></section><section class="admin-card" data-testid="admin-guest-cleanup-status" data-cleanup-failed="${cleanup.last_error === 'cleanup_failed'}"><h3>${safe(t('guests.cleanupTitle', {}, 'admin'))}</h3><p>${safe(t('guests.cleanupStatus', { raw: cleanup.raw_retention_days || 30, aggregate: cleanup.aggregate_retention_days || 400, time: cleanup.last_success_at || t('guests.cleanupNever', {}, 'admin'), failure: cleanup.last_failure_at || t('guests.cleanupNever', {}, 'admin') }, 'admin'))}</p></section>`;
  // Insert the owner control before analytics so admission status is immediately visible.
  view.querySelector('[data-testid="admin-guest-filters"]').insertAdjacentHTML('beforebegin', html`<section class="admin-card" data-testid="admin-guest-policy"><h3>${safe(t('guests.policyTitle', {}, 'admin'))}</h3><p>${safe(t('guests.policyCopy', { tokens: formatNumber(guestPolicy.starting_balance || 10000) }, 'admin'))}</p><label class="check-row"><input id="guest-trials-enabled" data-testid="admin-guest-trials-enabled" type="checkbox" ${guestPolicy.enabled ? 'checked' : ''}><span>${safe(t('guests.policyEnabled', {}, 'admin'))}</span></label><button id="guest-policy-save" data-testid="admin-save-guest-policy" type="button">${safe(t('guests.policySave', {}, 'admin'))}</button></section>`);
  // Insert the explicitly confirmed support conversion form after admission policy and before analytics filters.
  view.querySelector('[data-testid="admin-guest-filters"]').insertAdjacentHTML('beforebegin', html`<section class="admin-card" data-testid="admin-guest-conversion"><h3>${safe(t('guests.convertTitle', {}, 'admin'))}</h3><p>${safe(t('guests.convertCopy', {}, 'admin'))}</p><form id="admin-guest-conversion-form" class="grid3"><label>${safe(t('guests.convertIdentity', {}, 'admin'))}<input id="guest-conversion-identity" data-testid="admin-guest-conversion-identity" autocomplete="off" maxlength="191" required></label><label>${safe(t('guests.convertEmail', {}, 'admin'))}<input id="guest-conversion-email" data-testid="admin-guest-conversion-email" type="email" autocomplete="off" maxlength="254" required></label><label>${safe(t('guests.convertDisplayName', {}, 'admin'))}<input id="guest-conversion-display-name" data-testid="admin-guest-conversion-display-name" maxlength="80" required></label><label>${safe(t('guests.convertPassword', {}, 'admin'))}<input id="guest-conversion-password" data-testid="admin-guest-conversion-password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><label class="check-row"><input id="guest-conversion-confirm" data-testid="admin-guest-conversion-confirm" type="checkbox" required><span>${safe(t('guests.convertConfirm', {}, 'admin'))}</span></label><button id="guest-conversion-submit" data-testid="admin-guest-conversion-submit" type="submit">${safe(t('guests.convertSubmit', {}, 'admin'))}</button></form></section>`);
  // Allocate one caller-owned operation key per rendered form so a lost response can be retried without a second account claim.
  const conversionIdempotencyKey = crypto.randomUUID();
  // Read the complete product metric summary with safe defaults.
  const metrics = summary.metrics || {};
  // Read percentage rates for every named funnel stage.
  const funnelRates = summary.funnel_rates || {};
  // Find the existing filter grid before appending the complete published filters.
  const filterGrid = view.querySelector('.guest-filter-grid');
  // Build catalog-game options from retained aggregate rows while preserving a selected empty result.
  const gameKeys = [...new Set([guestFilters.game, ...games.map(row => row.game)].filter(Boolean))].sort();
  // Append time, game, completion, and sanitized error filters without replacing the basic locale/device/lifecycle controls.
  filterGrid.insertAdjacentHTML('beforeend', html`<label>${safe(t('guests.filterRange', {}, 'admin'))}<select id="guest-filter-range">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.range)}${option('1', t('guests.rangeDay', {}, 'admin'), guestFilters.range)}${option('7', t('guests.rangeWeek', {}, 'admin'), guestFilters.range)}${option('30', t('guests.rangeMonth', {}, 'admin'), guestFilters.range)}</select></label><label>${safe(t('guests.filterGame', {}, 'admin'))}<select id="guest-filter-game">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.game)}${gameKeys.map(game => option(game, humanLabel(game), guestFilters.game))}</select></label><label>${safe(t('guests.filterCompleted', {}, 'admin'))}<select id="guest-filter-completed">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.completed)}${option('yes', t('guests.filterYes', {}, 'admin'), guestFilters.completed)}${option('no', t('guests.filterNo', {}, 'admin'), guestFilters.completed)}</select></label><label>${safe(t('guests.filterError', {}, 'admin'))}<select id="guest-filter-error_category">${option('', t('guests.filterAll', {}, 'admin'), guestFilters.error_category)}${['VALIDATION_ERROR','INSUFFICIENT_FUNDS','CONFLICT','FORBIDDEN','NOT_FOUND','RATE_LIMITED','SERVER_ERROR'].map(category => option(category, humanLabel(category), guestFilters.error_category))}</select></label>`);
  // Find the compact summary grid before adding full product-measurement cards.
  const summaryGrid = view.querySelector('[data-testid="admin-guest-summary"]');
  // Append duration, breadth, error-free, and fake-token cards explicitly labelled as simulator-only values.
  summaryGrid.insertAdjacentHTML('beforeend', html`<div class="admin-card"><b>${safe(t('guests.averageDuration', {}, 'admin'))}</b><h2>${formatNumber(metrics.average_duration_seconds || 0)}s</h2></div><div class="admin-card"><b>${safe(t('guests.medianDuration', {}, 'admin'))}</b><h2>${formatNumber(metrics.median_duration_seconds || 0)}s</h2></div><div class="admin-card"><b>${safe(t('guests.gamesPerTrial', {}, 'admin'))}</b><h2>${formatNumber(metrics.average_games_per_trial || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.roundsPerTrial', {}, 'admin'))}</b><h2>${formatNumber(metrics.average_rounds_per_trial || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.errorFreeRate', {}, 'admin'))}</b><h2>${formatNumber(metrics.error_free_rate_percent || 0)}%</h2></div><div class="admin-card"><b>${safe(t('guests.fakeWagered', {}, 'admin'))}</b><h2>${formatMoney(metrics.wagered || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.fakeReturned', {}, 'admin'))}</b><h2>${formatMoney(metrics.returned || 0)}</h2></div><div class="admin-card"><b>${safe(t('guests.fakeNet', {}, 'admin'))}</b><h2>${formatMoney(metrics.net || 0)}</h2></div>`);
  // Define the full nine-stage funnel in the owner-approved product order.
  const funnelStages = ['landing_viewed','trial_started','lobby_reached','first_game_opened','first_action_accepted','first_round_completed','second_game_opened','trial_terminal','account_cta_viewed','account_cta_selected'];
  // Render the complete funnel with both counts and rates before game analytics.
  view.querySelector('[data-testid="admin-guest-games"]').insertAdjacentHTML('beforebegin', html`<section class="admin-card" data-testid="admin-guest-funnel"><h3>${safe(t('guests.funnelTitle', {}, 'admin'))}</h3>${table([t('guests.funnelStage', {}, 'admin'), t('guests.funnelCount', {}, 'admin'), t('guests.funnelRate', {}, 'admin')], funnelStages.map(stage => html`<tr><td>${safe(t(`guests.funnel.${stage}`, {}, 'admin'))}</td><td>${formatNumber(funnel[stage] || 0)}</td><td>${formatNumber(funnelRates[stage] || 0)}%</td></tr>`))}</section>`);
  // Render complete per-game acceptance metrics separately from the compact compatibility table.
  view.querySelector('[data-testid="admin-guest-games"]').insertAdjacentHTML('afterend', html`<section class="admin-card" data-testid="admin-guest-game-detail"><h3>${safe(t('guests.gameMetricsTitle', {}, 'admin'))}</h3>${games.length ? table([t('guests.colGame', {}, 'admin'), t('guests.colStartedRounds', {}, 'admin'), t('guests.colRounds', {}, 'admin'), t('guests.colAbandoned', {}, 'admin'), t('guests.colErrors', {}, 'admin'), t('guests.colFirstAction', {}, 'admin'), t('guests.colWagered', {}, 'admin'), t('guests.colReturned', {}, 'admin'), t('guests.colNet', {}, 'admin'), t('guests.colCategories', {}, 'admin')], games.map(row => html`<tr><td>${safe(humanLabel(row.game))}</td><td>${formatNumber(row.rounds_started || 0)}</td><td>${formatNumber(row.rounds_completed || 0)}</td><td>${formatNumber(row.rounds_abandoned || 0)}</td><td>${formatNumber(row.errors || 0)}</td><td>${formatNumber(row.median_first_action_ms || 0)}ms</td><td>${formatMoney(row.wagered || 0)}</td><td>${formatMoney(row.returned || 0)}</td><td>${formatMoney(row.net || 0)}</td><td>${safe(Object.keys(row.action_categories || {}).map(humanLabel).join(', ') || '—')}</td></tr>`)) : emptyState(t('guests.gamesEmpty', {}, 'admin'), t('guests.gamesEmptyDetail', {}, 'admin'))}</section>`);
  // Make wide game, funnel, metric, and session tables named keyboard-scrollable regions.
  view.querySelectorAll('[data-testid="admin-guest-funnel"], [data-testid="admin-guest-games"], [data-testid="admin-guest-game-detail"], [data-testid="admin-guest-recent"]').forEach(region => { region.tabIndex = 0; region.setAttribute('role', 'region'); region.setAttribute('aria-label', region.querySelector('h3')?.textContent || t('nav.guests', {}, 'admin')); });
  // Reload the section when any allowlisted filter changes.
  ['locale', 'device', 'status', 'range', 'game', 'completed', 'error_category'].forEach(name => { view.querySelector(`#guest-filter-${name}`).onchange = event => { guestFilters[name] = event.target.value; void guests(); }; });
  // Bind de-identified detail buttons after rendering retained rows.
  view.querySelectorAll('.guest-detail-button').forEach(button => { button.onclick = () => showGuestDetail(button.dataset.id); });
  // Bind active-row conversion shortcuts to the visible de-identified analytics id only.
  view.querySelectorAll('.guest-convert-button').forEach(button => { button.onclick = () => { const identity = view.querySelector('#guest-conversion-identity'); identity.value = button.dataset.id; identity.focus(); }; });
  // Submit one explicitly confirmed assisted conversion through the additive Admin v2 route.
  view.querySelector('#admin-guest-conversion-form').onsubmit = async event => {
    // Prevent form navigation so the Guest Trials tab and scroll position remain stable.
    event.preventDefault();
    // Capture transient credential controls only for the bounded request lifecycle.
    const password = view.querySelector('#guest-conversion-password');
    // Read the confirmation control independently so a missing literal true is rejected server-side.
    const confirmation = view.querySelector('#guest-conversion-confirm');
    // Disable the primary action while this exact idempotent request settles.
    const submit = view.querySelector('#guest-conversion-submit'); submit.disabled = true;
    // Start protected submission so credentials are cleared on every result.
    try {
      // Send exact target content plus the stable form operation identity; the server derives the guest locale.
      await post('/api/v2/admin/guest-trials/convert', { guest_identity: view.querySelector('#guest-conversion-identity').value.trim(), email: view.querySelector('#guest-conversion-email').value.trim(), password: password.value, display_name: view.querySelector('#guest-conversion-display-name').value.trim(), terms_version: 'private-beta-1', accepted: true, confirm: confirmation.checked, idempotency_key: conversionIdempotencyKey });
      // Announce the completed support action without repeating identity or mailbox content.
      toast(t('guests.convertComplete', {}, 'admin'), true);
      // Reload the canonical Guest Trials view after successful terminal conversion.
      await guests();
    // Keep bounded failures inside the localized Admin surface.
    } catch (_) {
      // Announce a generic failure without exposing whether the target identity exists.
      toast(t('guests.convertFailed', {}, 'admin'));
      // Re-enable the exact submit control after a failed request.
      submit.disabled = false;
    // Clear credential and confirmation material regardless of network or application outcome.
    } finally {
      // Remove the temporary password from the DOM before any evidence capture.
      if (password.isConnected) password.value = '';
      // Require a new explicit confirmation for any retry.
      if (confirmation.isConnected) confirmation.checked = false;
    }
  };
  // Bind the idempotent retention action through the protected v2 endpoint.
  view.querySelector('#guest-cleanup').onclick = async () => { try { await post('/api/v2/admin/guest-trials/cleanup', {}); toast(t('guests.cleanupComplete', {}, 'admin'), true); } catch (_) { toast(t('guests.cleanupFailed', {}, 'admin')); } await guests(); };
  // Bind the owner-only admission switch without affecting current trial principals.
  view.querySelector('#guest-policy-save').onclick = async () => { try { await post('/api/v2/admin/guest-trials/settings', { enabled: view.querySelector('#guest-trials-enabled').checked }); toast(t('guests.policySaved', {}, 'admin'), true); } catch (_) { toast(t('guests.policyFailed', {}, 'admin')); } await guests(); };
}

// Render disabled-by-default private invitation readiness, issuance, and lifecycle controls. (INVITE-001, INVITE-005)
async function invitations() {
  // Set the localized invitation title and restricted-preview boundary.
  setTitle(t('invitations.title', {}, 'admin'), t('invitations.subtitle', {}, 'admin'));
  // Announce loading before the Admin-only diagnostic resolves.
  view.innerHTML = html`<section class="admin-card loading-panel" data-testid="admin-invitation-loading" role="status"><h2>${safe(t('invitations.loadingTitle', {}, 'admin'))}</h2><p>${safe(t('invitations.loadingDetail', {}, 'admin'))}</p></section>`;
  // Load the bounded, recipient-masked lifecycle list through the additive v2 contract.
  const data = await api('/api/v2/admin/invitations?limit=100');
  // Stop a stale request from overwriting a newer selected tab.
  if (!isActiveTab('invitations')) return;
  // Normalize invitation rows defensively before rendering.
  const rows = Array.isArray(data.invitations) ? data.invitations : [];
  // Select one stable status for the readiness card.
  const readiness = !data.enabled ? 'disabled' : data.mail_status !== 'ready' ? 'release-held' : data.redemption_enabled ? 'ready' : 'redemption-held';
  // Render one secret-free readiness card, bounded create form, and keyboard-scrollable lifecycle region.
  view.innerHTML = html`<section class="admin-card" data-testid="admin-invitations-${safe(readiness)}"><h2>${safe(t(`invitations.states.${readiness}`, {}, 'admin'))}</h2><p>${safe(t('invitations.boundary', {}, 'admin'))}</p><dl class="guest-detail-grid"><div><dt>${safe(t('invitations.issuance', {}, 'admin'))}</dt><dd>${safe(data.enabled ? t('common.enabled', {}, 'admin') : t('common.disabled', {}, 'admin'))}</dd></div><div><dt>${safe(t('invitations.redemption', {}, 'admin'))}</dt><dd>${safe(data.redemption_enabled ? t('common.enabled', {}, 'admin') : t('common.disabled', {}, 'admin'))}</dd></div><div><dt>${safe(t('invitations.delivery', {}, 'admin'))}</dt><dd>${safe(humanLabel(data.mail_status || 'unavailable'))}</dd></div><div><dt>${safe(t('invitations.recovery', {}, 'admin'))}</dt><dd>${formatNumber(data.recovery_required || 0)}</dd></div></dl></section><section class="admin-card" data-testid="admin-invitation-create"><h3>${safe(t('invitations.createTitle', {}, 'admin'))}</h3><div class="grid3"><label>${safe(t('invitations.recipient', {}, 'admin'))}<input id="invitation-recipient" type="email" autocomplete="off" maxlength="254" data-testid="admin-invitation-recipient"></label><label>${safe(t('invitations.locale', {}, 'admin'))}<select id="invitation-locale" data-testid="admin-invitation-locale">${localeOptions('en-US')}</select></label><button id="invitation-create" type="button" data-testid="admin-invitation-submit" ${data.enabled && data.mail_status === 'ready' ? '' : 'disabled'}>${safe(t('invitations.send', {}, 'admin'))}</button></div><p class="muted">${safe(t('invitations.createHelp', {}, 'admin'))}</p></section><section class="admin-card" data-testid="admin-invitation-list" tabindex="0" role="region" aria-label="${safe(t('invitations.listTitle', {}, 'admin'))}"><h3>${safe(t('invitations.listTitle', {}, 'admin'))}</h3>${rows.length ? table([t('invitations.recipient', {}, 'admin'), t('invitations.status', {}, 'admin'), t('invitations.delivery', {}, 'admin'), t('invitations.locale', {}, 'admin'), t('invitations.updated', {}, 'admin'), t('invitations.actions', {}, 'admin')], rows.map(row => html`<tr data-testid="admin-invitation-row" data-status="${safe(row.status)}"><td>${safe(row.recipient_hint || t('invitations.masked', {}, 'admin'))}</td><td>${safe(humanLabel(row.status))}</td><td>${safe(humanLabel(row.delivery_status || 'none'))}</td><td>${safe(row.locale)}</td><td>${safe(row.updated_at || '')}</td><td><button type="button" class="invitation-resend" data-id="${safe(row.invitation_id)}" ${['pending','delivery_failed'].includes(row.status) && data.enabled ? '' : 'disabled'}>${safe(t('invitations.resend', {}, 'admin'))}</button><button type="button" class="invitation-revoke" data-id="${safe(row.invitation_id)}" ${['pending','delivery_failed'].includes(row.status) ? '' : 'disabled'}>${safe(t('invitations.revoke', {}, 'admin'))}</button></td></tr>`)) : emptyState(t('invitations.empty', {}, 'admin'), t('invitations.emptyDetail', {}, 'admin'), 'admin-invitation-empty')}</section>`;
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
  detail.innerHTML = html`<h3>${safe(t('guests.detailTitle', {}, 'admin'))}</h3><dl class="guest-detail-grid"><div><dt>${safe(t('guests.colId', {}, 'admin'))}</dt><dd>${safe(row.analytics_id)}</dd></div><div><dt>${safe(t('guests.colLocale', {}, 'admin'))}</dt><dd>${safe(row.locale)}</dd></div><div><dt>${safe(t('guests.colDevice', {}, 'admin'))}</dt><dd>${safe(row.device)}</dd></div><div><dt>${safe(t('guests.colDuration', {}, 'admin'))}</dt><dd>${row.duration_seconds == null ? '—' : formatNumber(row.duration_seconds)}</dd></div><div><dt>${safe(t('guests.colActions', {}, 'admin'))}</dt><dd>${formatNumber(row.actions || 0)}</dd></div><div><dt>${safe(t('guests.colRounds', {}, 'admin'))}</dt><dd>${formatNumber(row.rounds_completed || 0)}</dd></div></dl>`;
  // Read the bounded allowlisted event timeline with a safe empty default.
  const events = Array.isArray(row.events) ? row.events : [];
  // Append fake-token aggregates and the allowlisted server timeline without rendering any auth identifier.
  detail.insertAdjacentHTML('beforeend', html`<dl class="guest-detail-grid"><div><dt>${safe(t('guests.colStartingBalance', {}, 'admin'))}</dt><dd>${formatMoney(row.starting_balance || 0)}</dd></div><div><dt>${safe(t('guests.colEndingBalance', {}, 'admin'))}</dt><dd>${row.ending_balance == null ? safe(t('guests.notAvailable', {}, 'admin')) : formatMoney(row.ending_balance)}</dd></div><div><dt>${safe(t('guests.colWagered', {}, 'admin'))}</dt><dd>${formatMoney(row.wagered || 0)}</dd></div><div><dt>${safe(t('guests.colReturned', {}, 'admin'))}</dt><dd>${formatMoney(row.returned || 0)}</dd></div><div><dt>${safe(t('guests.colNet', {}, 'admin'))}</dt><dd>${formatMoney(row.net || 0)}</dd></div><div><dt>${safe(t('guests.colErrors', {}, 'admin'))}</dt><dd>${formatNumber(row.errors || 0)}</dd></div></dl><section data-testid="admin-guest-timeline"><h4>${safe(t('guests.timelineTitle', {}, 'admin'))}</h4>${events.length ? table([t('guests.timelineEvent', {}, 'admin'), t('guests.timelineTime', {}, 'admin'), t('guests.colGame', {}, 'admin'), t('guests.timelineCategory', {}, 'admin'), t('guests.filterError', {}, 'admin'), t('guests.timelineLatency', {}, 'admin')], events.map(event => html`<tr><td>${safe(humanLabel(event.event))}</td><td>${safe(event.at)}</td><td>${safe(humanLabel(event.game || ''))}</td><td>${safe(humanLabel(event.action_category || ''))}</td><td>${safe(humanLabel(event.error_category || ''))}</td><td>${safe(humanLabel(event.latency_bucket || ''))}</td></tr>`)) : emptyState(t('guests.timelineEmpty', {}, 'admin'), t('guests.timelineEmptyDetail', {}, 'admin'))}</section>`);
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

// Define saveUserAccount to persist lifecycle status while role changes remain owner-only in Administrators.
async function saveUserAccount(button) {
  // Store the nearest rendered user row for control lookup.
  const row = button.closest('tr[data-user]');
  // Build the v2 account payload with only the selected lifecycle status.
  const payload = { status: row.querySelector('.user-status').value };
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
  view.innerHTML = html`<div class="admin-split"><section class="admin-card"><h3>Application events</h3>${eventList(app.logs, 'No application events', 'Application activity will appear here as the local service is used.', 'admin-app-events')}</section><section class="admin-card"><h3>Error events</h3>${eventList(errors.logs, 'No error events', 'No server errors have been recorded for the current day.', 'admin-error-events', true)}</section></div><section class="admin-card"><h3>Browser events</h3>${eventList(client.logs, 'No browser events', 'Browser activity will appear here after a client sends telemetry.', 'admin-client-events')}</section>`;
}

// Render OAuth diagnostics separately so provider configuration cannot change Operations health.
function oauthDiagnosticsCard(data) {
  // Keep only the three provider identifiers owned by the disabled OAuth catalog.
  const providers = Array.isArray(data?.providers) ? data.providers.filter(provider => ['local', 'google', 'facebook'].includes(provider?.provider)) : [];
  // Render an explicit unavailable state when the independent diagnostic request fails validation.
  if (providers.length !== 3) return html`<section class="admin-card" data-testid="admin-oauth-diagnostics-unavailable"><h2>${safe(t('oauth.title', {}, 'admin'))}</h2><p>${safe(t('oauth.unavailable', {}, 'admin'))}</p></section>`;
  // Build one allowlisted row per provider without rendering callback URLs or environment details.
  const rows = providers.map(provider => {
    // Normalize configuration status so unexpected backend values never become translation keys.
    const configurationStatus = ['ready', 'disabled', 'misconfigured'].includes(provider.status) ? provider.status : 'unknown';
    // Derive runtime copy only from the explicit availability boolean.
    const runtimeStatus = provider.runtime_available === true ? 'available' : 'unavailable';
    // Return a compact localized row with stable browser-test hooks.
    return html`<tr data-testid="admin-oauth-provider-${safe(provider.provider)}" data-runtime-available="${provider.runtime_available === true}"><td>${safe(t(`oauth.provider.${provider.provider}`, {}, 'admin'))}</td><td>${safe(t(`oauth.configuration.${configurationStatus}`, {}, 'admin'))}</td><td>${safe(t(`oauth.runtime.${runtimeStatus}`, {}, 'admin'))}</td></tr>`;
  });
  // Return a separate card so OAuth status never alters live, degraded, or down Operations state.
  return html`<section class="admin-card" data-testid="admin-oauth-diagnostics"><h2>${safe(t('oauth.title', {}, 'admin'))}</h2><p>${safe(t('oauth.subtitle', {}, 'admin'))}</p>${table([t('oauth.field.provider', {}, 'admin'), t('oauth.field.configuration', {}, 'admin'), t('oauth.field.runtime', {}, 'admin')], rows)}</section>`;
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
  return html`<section class="admin-card ${['misconfigured', 'unavailable'].includes(status) ? 'danger' : ''}" data-testid="admin-mail-${status}"><div class="row"><div><h2>${safe(t('mail.title', {}, 'admin'))}</h2><p>${safe(t(`mail.detail.${status}`, {}, 'admin'))}</p></div><span class="badge">${safe(t(`mail.state.${status}`, {}, 'admin'))}</span></div>${table([t('mail.field', {}, 'admin'), t('mail.value', {}, 'admin')], [html`<tr><td>${safe(t('mail.provider', {}, 'admin'))}</td><td>${safe(t(`mail.provider.${provider}`, {}, 'admin'))}</td></tr>`, html`<tr><td>${safe(t('mail.sent', {}, 'admin'))}</td><td>${count('sent')}</td></tr>`, html`<tr><td>${safe(t('mail.retryWait', {}, 'admin'))}</td><td>${count('retry_wait')}</td></tr>`, html`<tr><td>${safe(t('mail.failed', {}, 'admin'))}</td><td>${count('failed')}</td></tr>`, html`<tr><td>${safe(t('mail.uncertain', {}, 'admin'))}</td><td>${count('uncertain')}</td></tr>`])}<div data-testid="admin-mail-suppression-summary"><h3>${safe(t('mail.suppressionTitle', {}, 'admin'))}</h3><p>${safe(t('mail.suppressionCount', { count: suppressedRecipients }, 'admin'))}</p></div>${reasons.length ? html`<h3>${safe(t('mail.attention', {}, 'admin'))}</h3><ul>${reasons.map(reason => html`<li>${safe(t(`mail.reason.${reason}`, {}, 'admin'))}</li>`)}</ul>` : ''}</section>`;
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
    view.innerHTML = html`<section class="admin-card ${data.ready ? '' : 'danger'}" data-testid="admin-operations-${stateKey}"><div class="row"><div><h2>${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</h2><p>${safe(t(`operations.detail.${stateKey}`, {}, 'admin'))}</p></div><span class="badge" data-testid="admin-operations-state">${safe(t(`operations.symbol.${stateKey}`, {}, 'admin'))} ${safe(t(`operations.state.${stateKey}`, {}, 'admin'))}</span></div>${table([t('operations.field', {}, 'admin'), t('operations.value', {}, 'admin')], [html`<tr><td>${safe(t('operations.storage', {}, 'admin'))}</td><td>${safe(providerLabel)}</td></tr>`, html`<tr><td>${safe(t('operations.appVersion', {}, 'admin'))}</td><td>${safe(data.build.app_version)}</td></tr>`, html`<tr><td>${safe(t('operations.buildSha', {}, 'admin'))}</td><td>${safe(buildSha)}</td></tr>`, html`<tr><td>${safe(t('operations.lastHeartbeat', {}, 'admin'))}</td><td>${safe(heartbeat)}</td></tr>`])}${reasonLabels.length ? html`<h3>${safe(t('operations.attention', {}, 'admin'))}</h3><ul>${reasonLabels.map(label => html`<li>${safe(label)}</li>`)}</ul>` : ''}</section>${oauthDiagnosticsCard(null)}${mailDiagnosticsCard(null)}`;
    // Start provider diagnostics only after Operations is visible and handle failure locally.
    api('/api/v2/admin/oauth/providers').then(replaceOAuthDiagnosticsCard).catch(() => replaceOAuthDiagnosticsCard(null));
    // Start secret-free mail diagnostics independently so failure affects only its own card.
    api('/api/v2/admin/mail/readiness').then(replaceMailDiagnosticsCard).catch(() => replaceMailDiagnosticsCard(null));
  // Convert network or server loss into a client-derived down state without raw error text.
  } catch (error) {
    // Avoid replacing a newer tab after a delayed transport failure.
    if (!isActiveTab('operations')) return;
    // Render a clear symbol and recovery instruction so color is not the only status signal.
    view.innerHTML = html`<section class="admin-card danger" data-testid="admin-operations-down"><h2>${safe(t('operations.symbol.down', {}, 'admin'))} ${safe(t('operations.state.down', {}, 'admin'))}</h2><p>${safe(t('operations.detail.down', {}, 'admin'))}</p></section>`;
  }
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
  view.innerHTML = html`<section class="admin-card"><h3>Sound and voice</h3><div class="grid3"><label><input id="master_enabled" type="checkbox" ${settings.master_enabled ? 'checked' : ''}> Master sound</label><label><input id="sfx_enabled" type="checkbox" ${settings.sfx_enabled ? 'checked' : ''}> SFX</label><label><input id="voice_enabled" type="checkbox" ${settings.voice_enabled ? 'checked' : ''}> Voice</label></div><div class="grid3"><label>Master volume<input id="master_volume" type="range" min="0" max="1" step="0.05" value="${safe(settings.master_volume)}"></label><label>SFX volume<input id="sfx_volume" type="range" min="0" max="1" step="0.05" value="${safe(settings.sfx_volume)}"></label><label>Voice volume<input id="voice_volume" type="range" min="0" max="1" step="0.05" value="${safe(settings.voice_volume)}"></label></div><label>Voice<select id="preferred_voice_name"><option value="">Auto nice lady</option>${voices.map(voice => html`<option value="${safe(voice.name)}" ${settings.preferred_voice_name === voice.name ? 'selected' : ''}>${safe(voice.name)} (${safe(voice.lang)})</option>`)}</select></label><div class="grid3"><label>Rate<input id="voice_rate" type="number" min="0.5" max="1.8" step="0.05" value="${safe(settings.voice_rate)}"></label><label>Pitch<input id="voice_pitch" type="number" min="0.4" max="2" step="0.05" value="${safe(settings.voice_pitch)}"></label><label><input id="auto_nice_lady" type="checkbox" ${settings.auto_nice_lady ? 'checked' : ''}> Prefer nice lady</label></div><div class="grid3"><label><input id="announce_roulette_results" type="checkbox" ${settings.announce_roulette_results ? 'checked' : ''}> Roulette announcements</label><label><input id="announce_blackjack_results" type="checkbox" ${settings.announce_blackjack_results ? 'checked' : ''}> Blackjack announcements</label><label><input id="announce_baccarat_results" type="checkbox" ${settings.announce_baccarat_results ? 'checked' : ''}> Baccarat announcements</label><label><input id="announce_bingo_calls" type="checkbox" ${settings.announce_bingo_calls ? 'checked' : ''}> Bingo calls</label><label><input id="announce_keno_results" type="checkbox" ${settings.announce_keno_results ? 'checked' : ''}> Keno results</label></div><div class="row"><button id="saveAudio" data-testid="admin-save-audio" class="gold">Save audio settings</button><button id="previewVoice" data-testid="admin-preview-voice">Preview voice</button></div></section>`;
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

// Render the owner-facing registered-session timeout policy. (SESSION-009, ADMIN-031)
async function sessions() {
  // Set the localized session-policy title and helper text.
  setTitle(t('sessions.title', {}, 'admin'), t('sessions.subtitle', {}, 'admin'));
  // Load the current owner-gated policy document.
  const [data, rateData] = await Promise.all([api('/api/v2/admin/session-settings'), api('/api/v2/admin/rate-limits')]);
  // Read the settings under a safe empty fallback for error-boundary rendering.
  const s = data.settings || {};
  // Read the separately persisted live request policy under the same owner-facing security workspace.
  const r = rateData.settings || {};
  // Render the timeout and live request-rate controls as distinct bounded policy cards.
  view.innerHTML = html`<section class="admin-card" data-testid="admin-sessions-policy"><h3>${safe(t('sessions.heading', {}, 'admin'))}</h3><label class="check-row"><input id="sessions_enabled" type="checkbox" ${s.enabled ? 'checked' : ''} data-testid="admin-sessions-enabled"><span>${safe(t('sessions.enabled', {}, 'admin'))}</span></label><div class="grid3"><label>${safe(t('sessions.idle', {}, 'admin'))}<input id="idle_timeout_minutes" type="number" min="1" max="1440" value="${safe(s.idle_timeout_minutes)}" data-testid="admin-sessions-idle"></label><label>${safe(t('sessions.absolute', {}, 'admin'))}<input id="absolute_timeout_hours" type="number" min="1" max="24" value="${safe(s.absolute_timeout_hours)}" data-testid="admin-sessions-absolute"></label><label>${safe(t('sessions.warning', {}, 'admin'))}<input id="warning_minutes" type="number" min="0" max="10" value="${safe(s.warning_minutes)}" data-testid="admin-sessions-warning"></label><label>${safe(t('sessions.adminIdle', {}, 'admin'))}<input id="admin_idle_timeout_minutes" type="number" min="1" max="1440" value="${safe(s.admin_idle_timeout_minutes)}" data-testid="admin-sessions-admin-idle"></label></div><label><input id="admin_stricter" type="checkbox" ${s.admin_stricter ? 'checked' : ''} data-testid="admin-sessions-admin-stricter"> ${safe(t('sessions.adminStricter', {}, 'admin'))}</label><p class="muted">${safe(t('sessions.help', {}, 'admin'))}</p><p class="muted" data-testid="admin-sessions-provenance">${safe(t('sessions.provenance', { time: s.updated_at || '—', actor: s.updated_by || '—' }, 'admin'))}</p><div class="row"><button id="saveSessions" data-testid="admin-save-sessions" class="gold">${safe(t('sessions.save', {}, 'admin'))}</button></div></section><section class="admin-card" data-testid="admin-rate-limits"><h3>${safe(t('rateLimits.heading', {}, 'admin'))}</h3><div class="grid3"><label>${safe(t('rateLimits.requests', {}, 'admin'))}<input id="requests_per_window" type="number" min="60" max="10000" value="${safe(r.requests_per_window)}" data-testid="admin-rate-limit-requests"></label><label>${safe(t('rateLimits.window', {}, 'admin'))}<input id="window_seconds" type="number" min="1" max="3600" value="${safe(r.window_seconds)}" data-testid="admin-rate-limit-window"></label></div><p class="muted">${safe(t('rateLimits.help', {}, 'admin'))}</p><div class="row"><button id="saveRateLimits" data-testid="admin-save-rate-limits" class="gold">${safe(t('rateLimits.save', {}, 'admin'))}</button></div></section>`;
  // Bind the owner save action after rendering.
  view.querySelector('#saveSessions').onclick = saveSessions;
  // Bind the independent live rate-policy save action after rendering.
  view.querySelector('#saveRateLimits').onclick = saveRateLimits;
}

// Persist the owner-authored session policy through the additive v2 contract.
async function saveSessions() {
  // Build the policy payload from enforcement, warning, bounded lifetime, and stricter-Admin controls.
  const payload = { enabled: view.querySelector('#sessions_enabled').checked, idle_timeout_minutes: Number(view.querySelector('#idle_timeout_minutes').value), absolute_timeout_hours: Number(view.querySelector('#absolute_timeout_hours').value), warning_minutes: Number(view.querySelector('#warning_minutes').value), admin_idle_timeout_minutes: Number(view.querySelector('#admin_idle_timeout_minutes').value), admin_stricter: view.querySelector('#admin_stricter').checked };
  // Persist the bounded settings through the owner-only route.
  await api('/api/v2/admin/session-settings', { method: 'POST', body: payload });
  // Confirm the save without exposing policy internals.
  toast(t('sessions.saved', {}, 'admin'), true);
}

// Persist the owner-authored live application request policy without restarting the service. (SEC-015, ADMIN-032)
async function saveRateLimits() {
  // Build the sparse bounded policy from the two operational number fields.
  const payload = { requests_per_window: Number(view.querySelector('#requests_per_window').value), window_seconds: Number(view.querySelector('#window_seconds').value) };
  // Persist the validated policy through the recovery-safe owner route.
  await api('/api/v2/admin/rate-limits', { method: 'POST', body: payload });
  // Confirm activation without exposing any per-client limiter state.
  toast(t('rateLimits.saved', {}, 'admin'), true);
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
  return state.locales.map(locale => option(locale.id, `${locale.nativeLabel} (${locale.id})`, selected));
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
  return html`${browser}${formatters.map(locale => option(locale.formatLocale, `${locale.nativeLabel} (${locale.formatLocale})`, selected))}`;
}

// Define languageCards to render installed locale readiness cards.
function languageCards(selected) {
  // Store state so installed locale metadata drives the cards.
  const state = getLocaleState();
  // Return one compact card per installed locale.
  return state.locales.map(locale => html`<article class="bot-edit" data-locale-card="${safe(locale.id)}" lang="${safe(locale.id)}" dir="${safe(locale.dir)}"><div class="row"><h3 style="margin-right:auto">${safe(locale.nativeLabel)}</h3><span class="badge">${safe(t(locale.id === selected ? 'language.active' : 'language.ready', {}, 'admin'))}</span></div><p class="muted">${safe(t('language.installedDescription', { label: locale.label, fallback: locale.fallbackChain.join(' → ') }, 'admin'))}</p><div class="row"><span class="badge">${safe(locale.script)}</span><span class="badge">${safe(t(`language.review.${locale.reviewStatus}`, {}, 'admin'))}</span><span class="badge">${safe(t(locale.voiceReady ? 'language.voiceReady' : 'language.voiceCheck', {}, 'admin'))}</span><span class="badge">${safe(locale.dir.toUpperCase())}</span></div></article>`);
}

// Define lockedLanguageGrid to render the complete owner-approved 25-locale registry.
function lockedLanguageGrid() {
  // Store state so every locked identity and readiness value comes from the manifest.
  const state = getLocaleState();
  // Return one generic metadata card per registry identity without claiming translation completion.
  return html`<div class="grid2" data-testid="admin-locale-registry">${state.localeRegistry.map(locale => html`<article class="bot-edit" data-testid="admin-locale-registry-entry" data-locale-id="${safe(locale.id)}" lang="${safe(locale.id)}" dir="${safe(locale.dir)}"><div class="row"><span class="badge">#${formatNumber(locale.rank)}</span><strong style="margin-right:auto">${safe(locale.nativeLabel)}</strong><span class="badge">${safe(t(locale.uiReady ? 'language.ready' : 'language.metadataOnly', {}, 'admin'))}</span></div><p class="muted">${safe(locale.id)} · ${safe(locale.script)} · ${safe(locale.dir.toUpperCase())} · ${safe(locale.formatLocale)}</p></article>`)}</div>`;
}

// Define diagnosticsTable to render current runtime diagnostic values.
function diagnosticsTable(state) {
  // Return diagnostics in the same mini-table style as other Admin views.
  return table([t('language.diagnostics', {}, 'admin'), 'Value'], [html`<tr><td>${safe(t('language.registryVersion', {}, 'admin'))}</td><td>${safe(state.registryVersion)}</td></tr>`, html`<tr><td>${safe(t('language.resolvedLocale', {}, 'admin'))}</td><td data-testid="admin-locale-state">${safe(state.locale)}</td></tr>`, html`<tr><td>${safe(t('language.fallbackLocale', {}, 'admin'))}</td><td>${safe(state.fallbackLocale)}</td></tr>`, html`<tr><td>${safe(t('language.installedLocales', {}, 'admin'))}</td><td data-testid="admin-locale-ready-count">${formatNumber(state.locales.length)} / ${formatNumber(state.localeRegistry.length)}</td></tr>`, html`<tr><td>${safe(t('language.registeredDomains', {}, 'admin'))}</td><td>${formatNumber(state.registeredDomains.length)}</td></tr>`, html`<tr><td>${safe(t('language.loadedDomains', {}, 'admin'))}</td><td>${safe(state.loadedDomains.join(', '))}</td></tr>`, html`<tr><td>${safe(t('language.missingKeys', {}, 'admin'))}</td><td>${formatNumber(state.missingKeyCount)}</td></tr>`]);
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
  view.innerHTML = html`<div class="admin-split" data-testid="admin-localization-foundation"><section class="admin-card"><div class="row"><h3 style="margin-right:auto">${safe(t('language.availableTitle', {}, 'admin'))}</h3><span class="badge">${safe(t('language.readyCount', { ready: state.locales.length, total: state.localeRegistry.length }, 'admin'))}</span></div><div class="grid2">${languageCards(selectedLanguage)}</div><h3>${safe(t('language.registryTitle', {}, 'admin'))}</h3>${lockedLanguageGrid()}</section><section class="admin-card"><h3>${safe(t('language.localeSettings', {}, 'admin'))}</h3><div class="grid2 locale-settings-grid"><label>${safe(t('language.displayLanguage', {}, 'admin'))}<select id="admin_language" data-testid="admin-language-select">${localeOptions(selectedLanguage)}</select></label><label>${safe(t('language.formatLocale', {}, 'admin'))}<select id="admin_format_locale" data-testid="admin-format-locale-select">${formatLocaleOptions(selectedFormat)}</select></label></div><label><input id="admin_use_browser" type="checkbox" ${settings.useBrowserLocale ? 'checked' : ''}> ${safe(t('language.useBrowser', {}, 'admin'))}</label><label><input id="admin_persist_browser" type="checkbox" checked> ${safe(t('language.persistBrowser', {}, 'admin'))}</label><div class="result-box"><p data-testid="admin-money-preview">${safe(t('language.previewBalance', { amount: formatMoney(5030) }, 'admin'))}</p><p>${safe(t('language.datePreview', {}, 'admin'))}: ${safe(formatDate(new Date(), { dateStyle: 'medium', timeStyle: 'short' }))}</p></div><div class="row"><button id="admin_apply_locale" data-testid="admin-locale-apply" class="gold">${safe(t('language.apply', {}, 'admin'))}</button><button id="admin_save_locale" data-testid="admin-locale-save">${safe(t('language.saveBrowser', {}, 'admin'))}</button><button id="admin_reset_locale" data-testid="admin-locale-reset">${safe(t('language.resetBrowser', {}, 'admin'))}</button><button id="admin_preview_lobby">${safe(t('actions.previewLobby'))}</button></div>${diagnosticsTable(state)}<h3>${safe(t('language.stringPreview', {}, 'admin'))}</h3><div class="bot-edit"><b>English</b><p>Choose your table. All games use play tokens only. Ledger-backed outcomes are visible in Admin.</p></div><div class="bot-edit"><b>Русский</b><p>Выберите стол. Все игры используют только игровые токены. Результаты с учётом ledger видны в Admin.</p></div><div class="bot-edit"><b>${safe(t('language.fallback', {}, 'admin'))}</b><p>${safe(t('language.fallbackDescription', {}, 'admin'))}</p></div></section></div>`;
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

// Declare the nested Admin navigation so current and added surfaces remain registry-driven. (ADMIN-031)
const MENU = [
  // Overview owns the landing dashboard.
  { id: 'overview', label: 'nav.section.overview', items: [{ tab: 'dashboard', label: 'nav.dashboard', domain: 'admin' }] },
  // Identity groups accounts, session policy, invitations, and disposable guests.
  { id: 'identity', label: 'nav.section.identity', items: [{ tab: 'users', label: 'nav.users', domain: 'admin' }, { tab: 'administrators', label: 'nav.administrators', domain: 'admin' }, { tab: 'enrollment', label: 'nav.enrollment', domain: 'admin' }, { tab: 'sessions', label: 'nav.sessions', domain: 'admin' }, { tab: 'invitations', label: 'nav.invitations', domain: 'admin' }, { tab: 'guests', label: 'nav.guests', domain: 'admin' }] },
  // Players and economy groups wallet activity, outcomes, rates, and autoplay.
  { id: 'players', label: 'nav.section.players', items: [{ tab: 'players', label: 'nav.players', domain: 'admin' }, { tab: 'ledger', label: 'nav.ledger', domain: 'admin' }, { tab: 'history', label: 'nav.history', domain: 'admin' }, { tab: 'economics', label: 'nav.economics', domain: 'admin' }, { tab: 'autoplay', label: 'nav.autoplay', domain: 'admin' }] },
  // Content and support groups game state, problem reports, audio, and locale.
  { id: 'content', label: 'nav.section.content', items: [{ tab: 'states', label: 'nav.states', domain: 'admin' }, { tab: 'feedback', label: 'feedback.admin.title', domain: 'feedback' }, { tab: 'audio', label: 'nav.audio', domain: 'admin' }, { tab: 'language', label: 'nav.language', domain: 'admin' }] },
  // System and operations groups health, telemetry, requirements, tests, and modules.
  { id: 'system', label: 'nav.section.system', items: [{ tab: 'launch', label: 'nav.launch', domain: 'admin' }, { tab: 'operations', label: 'nav.operations', domain: 'admin' }, { tab: 'telemetry', label: 'nav.telemetry', domain: 'admin' }, { tab: 'requirements', label: 'nav.requirements', domain: 'admin' }, { tab: 'tests', label: 'nav.tests', domain: 'admin' }, { tab: 'system', label: 'nav.system', domain: 'admin' }] },
];

// Render the nested sidebar while preserving exact data-tab and test hooks.
function renderNav() {
  // Resolve the navigation container owned by admin.html.
  const nav = document.getElementById('adminNav');
  // Stop safely if an unexpected legacy shell omits the container.
  if (!nav) return;
  // Build each localized collapsible group from the fixed registry.
  nav.innerHTML = html`${MENU.map(section => {
    // Build item buttons with stable tab, test, and translation attributes.
    const items = section.items.map(item => html`<button data-tab="${item.tab}" data-testid="admin-tab-${item.tab}" data-i18n="${item.label}" data-i18n-domain="${item.domain}">${item.tab}</button>`);
    // Wrap the section heading and its item list in one accessible group.
    return html`<div class="admin-nav-group" data-group="${section.id}"><button type="button" class="admin-nav-section" data-group-toggle="${section.id}" data-testid="admin-section-${section.id}" aria-expanded="true"><span data-i18n="${section.label}" data-i18n-domain="admin">${section.id}</span><span class="admin-nav-chevron" aria-hidden="true">▾</span></button><div class="admin-nav-items">${items}</div></div>`;
  })}`;
}

// Collapse or expand one navigation group.
function toggleGroup(header) {
  // Resolve the owning group from the activated header.
  const group = header.closest('.admin-nav-group');
  // Stop when the header is detached.
  if (!group) return;
  // Flip the visual collapsed state.
  const collapsed = group.classList.toggle('collapsed');
  // Mirror the result through the accessible expanded state.
  header.setAttribute('aria-expanded', String(!collapsed));
}

// Define bindChrome to attach static Admin chrome event handlers.
function bindChrome() {
  // Bind every sidebar tab to the shared activator.
  document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => activate(button.dataset.tab));
  // Bind every group heading to its disclosure behavior.
  document.querySelectorAll('[data-group-toggle]').forEach(header => header.onclick = () => toggleGroup(header));
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
  // Build nested navigation before applying translations to its generated labels.
  renderNav();
  // Apply declarative translations to static and generated Admin chrome.
  applyTranslations(document);
  // Bind Admin chrome controls after translations are ready.
  bindChrome();
  // Subscribe to locale changes so the current tab rerenders in place.
  onLocaleChange(() => { applyTranslations(document); load(current); });
  // Mark and render the initial dashboard tab.
  activate('dashboard');
}

// Start the Admin module.
start();
