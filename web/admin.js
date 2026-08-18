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
// Import the Dashboard renderer so summary metrics and diagnostics stay behind a reviewable per-tab boundary. (ADMIN-003, ADMIN-014)
import { createDashboardTab } from './admin/dashboard.js';
// Import the Telemetry renderer so privacy-safe diagnostic panes stay behind a reviewable per-tab boundary. (ADMIN-008, ADMIN-017)
import { createTelemetryTab } from './admin/telemetry.js';
// Import the Players & Bots renderer so wallet and controller operations leave the dispatcher monolith. (ADMIN-005, ADMIN-015)
import { createPlayersTab } from './admin/players.js';
// Import the Users renderer so account lifecycle and stale-response state leave the dispatcher monolith. (ADMIN-034)
import { createUsersTab } from './admin/users.js';
// Import owner-only role delegation so privilege changes leave the dispatcher monolith. (ADMIN-033)
import { createAdministratorsTab } from './admin/administrators.js';
// Import enrollment governance so signup and provider controls leave the dispatcher monolith. (AUTH-015)
import { createEnrollmentTab } from './admin/enrollment.js';
// Import private invitation governance so issuance and lifecycle controls leave the dispatcher monolith. (INVITE-001, INVITE-005)
import { createInvitationsTab } from './admin/invitations.js';
// Import voice helpers so the existing Audio & Voice tab keeps its behavior.
import { availableVoices, loadVoiceSettings, saveVoiceSettings, speak } from './core/voice.js';
// Import i18n helpers so Admin can switch language without reloading or remounting.
import { applyTranslations, formatDate, formatMoney, formatNumber, getLocaleSettings, getLocaleState, initI18n, onLocaleChange, resetLocaleSettings, setLocale, t } from './core/i18n.js';

// Store current so refresh and locale rerendering preserve the active Admin tab.
let current = 'dashboard';
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
// Bind the Dashboard renderer to the accepted metric, ledger, diagnostic, and stale-response boundaries. (ADMIN-003, ADMIN-014)
const dashboard = createDashboardTab({
  api,
  emptyState,
  eventList,
  formatMoney,
  formatNumber,
  html,
  humanLabel,
  isActiveTab,
  ledgerEventLabel,
  safe,
  setTitle,
  t,
  table,
  view,
});
// Bind the Telemetry renderer to the accepted read-only log and event-list boundaries. (ADMIN-008, ADMIN-017)
const telemetry = createTelemetryTab({ api, eventList, html, setTitle, view });
// Bind the Players & Bots renderer to the accepted dashboard, bot-mutation, locale, and ledger presentation boundaries.
const playersBots = createPlayersTab({
  api,
  emptyState,
  formatMoney,
  formatNumber,
  html,
  humanLabel,
  post,
  safe,
  setTitle,
  t,
  table,
  toast,
  view,
});
// Bind the Users renderer to the accepted account, locale, and Guest Trials handoff boundaries.
const users = createUsersTab({
  activate,
  api,
  emptyState,
  formatLocaleOptions,
  formatMoney,
  html,
  humanLabel,
  isActiveTab,
  localeOptions,
  option,
  post,
  raw,
  safe,
  setTitle,
  t,
  table,
  toast,
  view,
});
// Bind the Administrators renderer to the accepted owner-only role-management boundaries.
const administrators = createAdministratorsTab({
  api,
  emptyState,
  html,
  humanLabel,
  isActiveTab,
  option,
  post,
  safe,
  setTitle,
  t,
  table,
  toast,
  view,
});
// Bind Enrollment to its distinct policy, readiness, and provider-control boundaries.
const enrollment = createEnrollmentTab({
  api,
  emptyState,
  html,
  humanLabel,
  isActiveTab,
  option,
  post,
  safe,
  setTitle,
  t,
  table,
  toast,
  view,
});
// Bind Invitations to its privacy-safe lifecycle and delivery-readiness boundaries.
const invitations = createInvitationsTab({
  api,
  emptyState,
  formatNumber,
  html,
  humanLabel,
  isActiveTab,
  localeOptions,
  post,
  safe,
  setTitle,
  t,
  table,
  toast,
  view,
});

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
