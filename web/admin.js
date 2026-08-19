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
// Import Audio & Voice settings so global sound controls leave the dispatcher monolith. (AUDIO-001, AUDIO-007)
import { createAudioTab } from './admin/audio.js';
// Import session and request-rate policy controls so owner settings leave the dispatcher monolith. (SESSION-009, ADMIN-031, ADMIN-032)
import { createSessionsTab } from './admin/sessions.js';
// Import trusted Operations diagnostics so dependency, OAuth, and mail health leave the dispatcher monolith. (ADMIN-014, MAIL-003)
import { createOperationsTab } from './admin/operations.js';
// Import shared locale options and the Language tab so localization leaves the dispatcher monolith. (I18N-005, I18N-014)
import { createLanguageTab, createLocaleOptionHelpers } from './admin/language.js';
// Import privacy-bounded report triage so Feedback leaves the dispatcher monolith. (ADMIN-025)
import { createFeedbackTab } from './admin/feedback.js';
// Import Guest Trials policy and telemetry so account-free analytics leave the dispatcher monolith. (CONVERT-003, ADMIN-031)
import { createGuestsTab } from './admin/guests.js';
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
// Bind manifest-driven locale selectors once for Users, Invitations, Guest Trials, and Language.
const { formatLocaleOptions, localeOptions } = createLocaleOptionHelpers({ getLocaleState, html, option, t });

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
// Bind Audio to the accepted voice helpers and Admin settings route.
const audio = createAudioTab({
  api,
  availableVoices,
  html,
  loadVoiceSettings,
  safe,
  saveVoiceSettings,
  setTitle,
  speak,
  t,
  toast,
  view,
});
// Bind Sessions to its two independently persisted owner-only policy routes.
const sessions = createSessionsTab({ api, html, safe, setTitle, t, toast, view });
// Bind Operations to its independent trusted diagnostic routes.
const operations = createOperationsTab({ api, formatDate, html, isActiveTab, safe, setTitle, t, table, view });
// Bind Language to the accepted runtime, browser-local settings, diagnostics, and shared selectors.
const language = createLanguageTab({
  formatDate,
  formatLocaleOptions,
  formatMoney,
  formatNumber,
  getLocaleSettings,
  getLocaleState,
  html,
  localeOptions,
  option,
  resetLocaleSettings,
  safe,
  setLocale,
  setTitle,
  t,
  table,
  toast,
  view,
});
// Bind Feedback to its attachment-free inbox, local-only draft, and privacy-safe export routes.
const feedbackReports = createFeedbackTab({
  api,
  emptyState,
  getLocaleState,
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
// Bind Guest Trials to its de-identified telemetry, owner policy, conversion, and retention routes.
const guests = createGuestsTab({
  api,
  emptyState,
  formatMoney,
  formatNumber,
  html,
  humanLabel,
  isActiveTab,
  localeOptions,
  option,
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
